"""Le modèle (probabilité de sinistre au paiement), la décision (proposer ou non la garantie)
et les mesures (classement, calibration, bénéfice, équité).

Aucune fonction ne lit de variable globale modifiable : tout passe en paramètre, et les
réglages par défaut viennent de backend/config.py.
"""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from backend.config import (
    BON_ACHAT,
    CHARGEMENT,
    PART_REFUS_MAX_PAR_ETAT,
    PRIX_GARANTIE,
    REGIONS,
    SEED,
    TAUX_SOUSCRIPTION,
)
from backend.trajets import VARIABLES_TRAJET

# Variables connues AU PAIEMENT. Exclues volontairement (essais sur la VALIDATION 2017) :
# - l'État du client et du vendeur, et les coordonnées GPS : équité (voir data_quality_card.md) ;
# - le mois et le jour d'achat : ils apprennent les pics de 2017 qui ne se répètent pas ;
# - l'historique de retard du vendeur et la catégorie : aucun gain en validation ;
# - le volume et le nombre de mensualités : sans effet sur les deux fenêtres de validation,
#   retirés pour simplifier ;
# - le taux de retard des 30 derniers jours : connu avec un mois de retard (l'issue d'une commande
#   n'est connue qu'à sa date promise), il arrive après les crises et dégrade le bénéfice.
# Ajoutées : les trois variables « trajet » (backend/trajets.py), +0,04 de ROC-AUC en validation.
VARIABLES_NUMERIQUES = [
    "delai_promis_jours",
    "distance_km",
    "meme_etat",
    "frais_port",
    "prix_total",
    "poids_total_g",
    "nb_articles",
    "nb_vendeurs",
    *VARIABLES_TRAJET,
]
VARIABLES_CATEGORIELLES = ["type_paiement"]
VARIABLES = VARIABLES_NUMERIQUES + VARIABLES_CATEGORIELLES
CIBLE = "sinistre"
CANDIDATS = ["logistique", "foret_100", "boosting"]


# --- Préparation ------------------------------------------------------------------------

def preparer_variables(table: pd.DataFrame, bon_achat: float = BON_ACHAT) -> pd.DataFrame:
    """Ajoute les colonnes dérivées : même État (vendeur et client), indemnité, région du client."""
    table = table.copy()
    table["meme_etat"] = (table["etat_client"] == table["etat_vendeur"]).astype(int)
    table["indemnite"] = table["frais_port"] + bon_achat
    etat_vers_region = {etat: region for region, etats in REGIONS.items() for etat in etats}
    table["region_client"] = table["etat_client"].map(etat_vers_region).fillna("inconnue")
    return table


def separer_periodes(table: pd.DataFrame, date_coupure: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split temporel : les commandes avant la date de coupure, puis à partir de cette date."""
    coupure = pd.Timestamp(date_coupure)
    return table[table["date_achat"] < coupure], table[table["date_achat"] >= coupure]


# --- Modèles ----------------------------------------------------------------------------

def construire_modele(nom: str):
    """Renvoie un pipeline non entraîné. Les médianes et l'encodage sont appris sur les
    données d'entraînement seulement : pas de fuite vers la validation ou le test.
    """
    preparation = ColumnTransformer(
        [
            ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), VARIABLES_NUMERIQUES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), VARIABLES_CATEGORIELLES),
        ]
    )
    if nom == "logistique":
        estimateur = LogisticRegression(max_iter=3000)
    elif nom == "boosting":
        estimateur = HistGradientBoostingClassifier(
            learning_rate=0.05, max_iter=300, min_samples_leaf=100, l2_regularization=1.0, random_state=SEED,
        )
    elif nom.startswith("foret_"):
        estimateur = RandomForestClassifier(
            n_estimators=300,
            min_samples_leaf=int(nom.split("_")[1]),
            max_features="sqrt",
            random_state=SEED,
            n_jobs=-1,
        )
    else:
        raise ValueError(f"Modèle inconnu : {nom}")
    return make_pipeline(preparation, estimateur)


def entrainer(nom: str, table: pd.DataFrame):
    """Entraîne le modèle `nom` sur la table donnée."""
    return construire_modele(nom).fit(table[VARIABLES], table[CIBLE])


def predire_probabilite(modele, table: pd.DataFrame) -> np.ndarray:
    """Probabilité de sinistre de chaque commande."""
    return modele.predict_proba(table[VARIABLES])[:, 1]


# --- La décision : proposer ou non la garantie ---------------------------------------------

def calculer_cout_attendu(proba, indemnite, chargement: float = CHARGEMENT) -> np.ndarray:
    """Coût attendu d'une commande pour l'assureur (probabilité × indemnité), avec sa marge."""
    return np.asarray(proba, dtype=float) * np.asarray(indemnite, dtype=float) * (1 + chargement)


def decider_eligibilite(score, seuil: float, groupe, part_refus_max: float = PART_REFUS_MAX_PAR_ETAT) -> np.ndarray:
    """Renvoie True quand la garantie est proposée.

    Règle : on refuse quand le score dépasse le seuil (pour le modèle : coût attendu > prix).
    Équité : dans chaque groupe (l'État du client), si plus de `part_refus_max` des commandes sont
    refusées, on re-propose la garantie aux commandes refusées les moins risquées jusqu'à
    respecter le plafond.
    """
    score = np.asarray(score, dtype=float)
    groupe = np.asarray(groupe)
    proposee = score <= seuil
    for nom_groupe in np.unique(groupe):
        indices = np.flatnonzero(groupe == nom_groupe)
        refusees = indices[~proposee[indices]]
        excedent = len(refusees) - int(np.floor(part_refus_max * len(indices)))
        if excedent > 0:
            moins_risquees = refusees[np.argsort(score[refusees])][:excedent]
            proposee[moins_risquees] = True
    return proposee


def calculer_seuils_par_groupe(cout_attendu, groupe, prix: float = PRIX_GARANTIE,
                               part_refus_max: float = PART_REFUS_MAX_PAR_ETAT) -> dict:
    """Traduit la règle d'éligibilité en un seuil de coût par groupe (l'État du client),
    utilisable pour une seule commande : on refuse si coût attendu > seuil de son État. Le seuil
    vaut le prix, sauf dans les États où cela ferait plus de `part_refus_max` de refus : il est
    alors relevé.
    """
    donnees = pd.DataFrame({"cout": np.asarray(cout_attendu, dtype=float), "groupe": np.asarray(groupe)})
    seuils = {}
    for nom_groupe, sous_table in donnees.groupby("groupe"):
        couts = np.sort(sous_table["cout"].to_numpy())[::-1]  # du plus cher au moins cher
        nb_refus_max = int(np.floor(part_refus_max * len(couts)))
        if nb_refus_max >= len(couts) or couts[nb_refus_max] <= prix:
            seuils[nom_groupe] = float(prix)
        else:
            seuils[nom_groupe] = float(couts[nb_refus_max])  # au-delà : les nb_refus_max plus chers
    return seuils


def evaluer_strategie(proposee, sinistre, indemnite, prix: float = PRIX_GARANTIE,
                      taux_souscription: float = TAUX_SOUSCRIPTION) -> dict:
    """Résultat de l'assureur : parmi les commandes à qui la garantie est proposée, une part
    `taux_souscription` l'achète (hypothèse). Les sinistres sont ceux réellement observés.
    """
    proposee = np.asarray(proposee, dtype=bool)
    cout_sinistres = np.asarray(sinistre, dtype=float) * np.asarray(indemnite, dtype=float)
    primes = taux_souscription * prix * proposee.sum()
    sinistres = taux_souscription * cout_sinistres[proposee].sum()
    return {
        "part_proposee": float(proposee.mean()),
        "garanties_vendues": float(taux_souscription * proposee.sum()),
        "primes": float(primes),
        "sinistres": float(sinistres),
        "benefice": float(primes - sinistres),
        "ratio_sinistres_primes": float(sinistres / primes) if primes else float("nan"),
    }


# --- Les mesures ------------------------------------------------------------------------

def mesurer_classement(sinistre, proba) -> dict:
    """ROC-AUC, PR-AUC (à comparer au taux de sinistre, sa valeur au hasard) et score de Brier."""
    return {
        "roc_auc": float(roc_auc_score(sinistre, proba)),
        "pr_auc": float(average_precision_score(sinistre, proba)),
        "taux_sinistre": float(np.mean(sinistre)),
        "brier": float(brier_score_loss(sinistre, proba)),
    }


def tableau_calibration(sinistre, proba, nb_tranches: int = 10) -> pd.DataFrame:
    """Par tranche de risque prédit : probabilité moyenne prédite contre taux de sinistre observé."""
    donnees = pd.DataFrame({"proba": proba, "sinistre": sinistre})
    donnees["tranche"] = pd.qcut(donnees["proba"], nb_tranches, labels=False, duplicates="drop") + 1
    return donnees.groupby("tranche").agg(
        commandes=("sinistre", "size"),
        proba_moyenne=("proba", "mean"),
        taux_observe=("sinistre", "mean"),
    ).reset_index()


def tableau_equite(groupe, proposee, sinistre, nom: str = "region") -> pd.DataFrame:
    """Par groupe (région ou État du client) : nombre de commandes, part refusée, taux de sinistre observé."""
    donnees = pd.DataFrame({nom: np.asarray(groupe), "refusee": ~np.asarray(proposee, dtype=bool),
                            "sinistre": np.asarray(sinistre)})
    return donnees.groupby(nom).agg(
        commandes=("refusee", "size"),
        part_refusee=("refusee", "mean"),
        taux_sinistre=("sinistre", "mean"),
    ).reset_index()


def calculer_importance(modele, table: pd.DataFrame, nb_repetitions: int = 5) -> pd.DataFrame:
    """Importance par permutation, mesurée sur le TEST avec la ROC-AUC.
    Rappel : une variable importante est utilisée par le modèle, ce n'est pas une cause.
    """
    resultat = permutation_importance(
        modele, table[VARIABLES], table[CIBLE], scoring="roc_auc",
        n_repeats=nb_repetitions, random_state=SEED, n_jobs=-1,
    )
    return (
        pd.DataFrame({"variable": VARIABLES, "importance": resultat.importances_mean, "ecart_type": resultat.importances_std})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )
