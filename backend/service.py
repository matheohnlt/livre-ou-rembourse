"""SEULE interface appelée par le frontend. Aucun import de Streamlit ici : on pourrait
remplacer Streamlit par une autre interface sans toucher au backend.

Tous les calculs (probabilité, coût attendu, décision, bénéfice, équité) sont faits ici ou
dans backend.model ; le frontend ne fait qu'afficher et faire saisir.
"""
import json
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd

from backend import model as M
from backend.config import (
    BON_ACHAT,
    CHARGEMENT,
    FICHIER_METRIQUES,
    FICHIER_MODELE,
    PART_REFUS_MAX_PAR_REGION,
    PRIX_GARANTIE,
    REGIONS,
    SEED,
    TAUX_SOUSCRIPTION,
)
from backend.train import FICHIER_PREDICTIONS

MESSAGE_MODELE_ABSENT = "Modèle absent. Lancer d'abord : python -m backend.train"


# --- Chargement des résultats de l'entraînement ------------------------------------------

def modele_disponible() -> bool:
    """Vrai si `python -m backend.train` a déjà été lancé."""
    return FICHIER_MODELE.exists() and FICHIER_METRIQUES.exists() and FICHIER_PREDICTIONS.exists()


@lru_cache(maxsize=1)
def _artefacts() -> dict:
    if not FICHIER_MODELE.exists():
        raise FileNotFoundError(MESSAGE_MODELE_ABSENT)
    # joblib = pickle : on ne charge que le fichier produit par notre propre backend.train.
    return joblib.load(FICHIER_MODELE)


@lru_cache(maxsize=1)
def metriques() -> dict:
    """Toutes les métriques sauvegardées par l'entraînement."""
    if not FICHIER_METRIQUES.exists():
        raise FileNotFoundError(MESSAGE_MODELE_ABSENT)
    return json.loads(FICHIER_METRIQUES.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _predictions_test() -> pd.DataFrame:
    if not FICHIER_PREDICTIONS.exists():
        raise FileNotFoundError(MESSAGE_MODELE_ABSENT)
    return pd.read_csv(FICHIER_PREDICTIONS, parse_dates=["date_achat"])


def parametres_par_defaut() -> dict:
    """Les hypothèses métier de config.py, pour initialiser les curseurs."""
    return {
        "prix": PRIX_GARANTIE,
        "bon_achat": BON_ACHAT,
        "chargement": CHARGEMENT,
        "part_refus_max": PART_REFUS_MAX_PAR_REGION,
        "taux_souscription": TAUX_SOUSCRIPTION,
    }


# --- Écran Devis : une commande, une décision ----------------------------------------------

def lister_commandes_demo(nb_par_decision: int = 100) -> pd.DataFrame:
    """Un échantillon fixe de commandes 2018 (moitié proposées, moitié refusées), avec un libellé lisible."""
    predictions = _predictions_test()
    echantillon = pd.concat(
        groupe.sample(min(nb_par_decision, len(groupe)), random_state=SEED)
        for _, groupe in predictions.groupby("proposee")
    ).sort_values("date_achat")
    libelle = (
        echantillon["etat_vendeur"] + " → " + echantillon["etat_client"]
        + " · " + echantillon["distance_km"].round(0).astype("Int64").astype(str) + " km"
        + " · " + (echantillon["poids_total_g"] / 1000).round(1).astype(str) + " kg"
        + " · " + echantillon["categorie"]
    )
    return pd.DataFrame({"commande_id": echantillon["commande_id"], "libelle": libelle.values})


def caracteristiques_commande(commande_id: str) -> dict:
    """Ce que l'on sait de la commande au paiement, plus ce qui s'est passé ensuite (pour la démo)."""
    ligne = _predictions_test().set_index("commande_id").loc[commande_id]
    # .item() : types Python simples (int, float, str) plutôt que des types NumPy.
    caracteristiques = {variable: getattr(ligne[variable], "item", lambda: ligne[variable])() for variable in M.VARIABLES}
    caracteristiques.update({
        "region_client": ligne["region_client"],
        "etat_client": ligne["etat_client"],
        "etat_vendeur": ligne["etat_vendeur"],
        "categorie": ligne["categorie"],
        "segment": ligne["segment"],
        "issue_reelle": "en retard ou jamais livrée" if ligne[M.CIBLE] == 1 else "livrée à l'heure",
    })
    return caracteristiques


def commande_type() -> dict:
    """Une commande « typique » (valeurs médianes du test 2018), point de départ de la saisie libre."""
    test = _predictions_test()
    caracteristiques = {variable: float(test[variable].median()) for variable in M.VARIABLES_NUMERIQUES}
    caracteristiques.update({
        "meme_etat": 0,
        "type_paiement": "credit_card",
        "region_client": "Sudeste",
        "issue_reelle": None,
        "segment": None,
    })
    return caracteristiques


def seuils_par_region() -> pd.DataFrame:
    """Seuil de coût attendu au-delà duquel la garantie est refusée, par région."""
    seuils = metriques()["decision"]["seuils_par_region"]
    return pd.DataFrame({"region": list(seuils), "seuil": list(seuils.values())})


def lister_regions() -> list:
    """Les régions du Brésil, dans l'ordre de config.py."""
    return list(REGIONS)


def lister_types_paiement() -> list:
    """Les modes de paiement connus du modèle."""
    return sorted(_predictions_test()["type_paiement"].dropna().unique().tolist())


def calculer_devis(caracteristiques: dict) -> dict:
    """Probabilité de sinistre, coût attendu et décision pour UNE commande.

    La décision applique le seuil de coût de la région du client (règle d'éligibilité avec le
    plafond de refus par région, voir backend/model.py).
    """
    manquantes = set(M.VARIABLES) - set(caracteristiques)
    if manquantes:
        raise ValueError(f"Variables manquantes : {sorted(manquantes)}")
    ligne = pd.DataFrame([{variable: caracteristiques[variable] for variable in M.VARIABLES}])
    proba = float(M.predire_probabilite(_artefacts()["modele"], ligne)[0])
    indemnite = float(caracteristiques["frais_port"]) + BON_ACHAT
    cout_attendu = float(M.calculer_cout_attendu(proba, indemnite))
    seuil = metriques()["decision"]["seuils_par_region"].get(caracteristiques.get("region_client"), PRIX_GARANTIE)
    proposee = cout_attendu <= seuil
    if cout_attendu <= PRIX_GARANTIE:
        raison = "rentable : le coût attendu est couvert par le prix"
    elif proposee:
        raison = "non rentable, mais proposée grâce à la règle d'équité de sa région"
    else:
        raison = "refusée : coût attendu trop élevé, même avec la règle d'équité"
    return {
        "proba": proba,
        "indemnite": indemnite,
        "cout_attendu": cout_attendu,
        "prix": PRIX_GARANTIE,
        "seuil_region": float(seuil),
        "proposee": bool(proposee),
        "raison": raison,
    }


# --- Écrans Simulateur et Équité --------------------------------------------------------------

def simuler(prix: float = PRIX_GARANTIE, bon_achat: float = BON_ACHAT, chargement: float = CHARGEMENT,
            part_refus_max: float = PART_REFUS_MAX_PAR_REGION, taux_souscription: float = TAUX_SOUSCRIPTION) -> dict:
    """Rejoue la décision sur les 53 344 commandes du test 2018 avec d'autres hypothèses.
    Les probabilités du modèle ne changent pas ; seuls l'indemnité, le seuil et la règle changent.
    """
    test = _predictions_test()
    indemnite = test["frais_port"] + bon_achat
    cout_attendu = M.calculer_cout_attendu(test["proba"], indemnite, chargement)
    sans_plafond = M.decider_eligibilite(cout_attendu, prix, test["region_client"], 1.0)
    avec_plafond = M.decider_eligibilite(cout_attendu, prix, test["region_client"], part_refus_max)
    tous = np.ones(len(test), dtype=bool)

    def evaluer(proposee):
        return M.evaluer_strategie(proposee, test[M.CIBLE], indemnite, prix, taux_souscription)

    strategies = pd.DataFrame([
        {"strategie": "Proposer à tous (sans modèle)", **evaluer(tous)},
        {"strategie": "Modèle, sans plafond par région", **evaluer(sans_plafond)},
        {"strategie": "Modèle, avec plafond par région", **evaluer(avec_plafond)},
    ])
    equite = M.tableau_equite(test["region_client"], avec_plafond, test[M.CIBLE]).merge(
        M.tableau_equite(test["region_client"], sans_plafond, test[M.CIBLE])[["region", "part_refusee"]],
        on="region", suffixes=("", "_sans_plafond"),
    )
    return {"strategies": strategies, "equite": equite,
            "cout_equite": float(strategies.loc[1, "benefice"] - strategies.loc[2, "benefice"])}


# --- Écran Exploration --------------------------------------------------------------------

def evolution_mensuelle() -> pd.DataFrame:
    """Taux de sinistre par mois d'achat, de janvier 2017 à août 2018."""
    return pd.DataFrame(metriques()["exploration"]["par_mois"])


def risque_par_etat() -> pd.DataFrame:
    """Taux de sinistre, délai promis et position moyenne des clients, par État."""
    return pd.DataFrame(metriques()["exploration"]["par_etat"]).sort_values("taux_sinistre", ascending=False)


def resume_exploration() -> dict:
    """Chiffres clés : volume, taux de sinistre, lien avec les mauvais avis."""
    exploration = metriques()["exploration"]
    return {"commandes": exploration["commandes"], "taux_sinistre": exploration["taux_sinistre_global"],
            **exploration["mauvais_avis"]}


def portraits_segments() -> pd.DataFrame:
    """Les 5 personas du K-means (bonus non supervisé)."""
    return pd.DataFrame(metriques()["segments"]["portrait"])


def choix_nombre_segments() -> pd.DataFrame:
    """Inertie et silhouette pour k de 2 à 8."""
    return pd.DataFrame(metriques()["segments"]["choix_k"])


# --- Écran Le modèle ------------------------------------------------------------------------

def resume_modele() -> dict:
    """Ce que l'écran « Le modèle » affiche : sélection, stabilité, test, calibration, importance."""
    m = metriques()
    strategies = pd.DataFrame([{"strategie": nom, **valeurs} for nom, valeurs in m["test"]["strategies"].items()])
    return {
        "modele_retenu": m["modele_retenu"],
        "selection": pd.DataFrame(m["selection_sur_validation"]),
        "validation_croisee": m["validation_croisee_temporelle_2017"],
        "periode_test": m["test"]["periode"],
        "commandes_test": m["test"]["commandes"],
        "classement": m["test"]["classement"],
        "strategies": strategies,
        "calibration": pd.DataFrame(m["test"]["calibration"]),
        "importance": pd.DataFrame(m["test"]["importance"]),
        "parametres": m["parametres"],
    }
