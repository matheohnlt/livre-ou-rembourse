"""Entraînement complet : `python -m backend.train`.

1. Reconstruit la base SQLite si elle n'existe pas.
2. Choisit le modèle sur la VALIDATION (appris de janvier à septembre 2017, jugé d'octobre à
   décembre 2017), avec la métrique métier : le bénéfice de l'assureur.
3. Mesure la stabilité par validation croisée temporelle sur 2017.
4. Réentraîne le modèle choisi sur tout 2017, puis l'évalue UNE SEULE FOIS sur 2018.
5. Sauvegarde le modèle, les métriques et les prédictions du test dans models/.
"""
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from backend import model as M
from backend.config import (
    BASE,
    CHARGEMENT,
    DATE_DEBUT_TEST,
    DATE_DEBUT_VALIDATION,
    DOSSIER_MODELES,
    FICHIER_METRIQUES,
    FICHIER_MODELE,
    PART_REFUS_MAX_PAR_REGION,
    PRIX_GARANTIE,
    SEED,
    SEUIL_DISTANCE_REFUS_KM,
)
from backend.data import charger_archive_dans_sqlite, lire_table_analyse

FICHIER_PREDICTIONS = DOSSIER_MODELES / "predictions_test.csv"


def decider_avec_modele(modele, table: pd.DataFrame, part_refus_max: float = PART_REFUS_MAX_PAR_REGION):
    """Probabilité, coût attendu et décision (proposer ou non) pour chaque commande."""
    proba = M.predire_probabilite(modele, table)
    cout = M.calculer_cout_attendu(proba, table["indemnite"], CHARGEMENT)
    proposee = M.decider_eligibilite(cout, PRIX_GARANTIE, table["region_client"], part_refus_max)
    return proba, cout, proposee


def choisir_modele(entrainement: pd.DataFrame) -> tuple[str, list]:
    """Compare les candidats sur la validation interne à 2017. Le test n'est jamais regardé ici."""
    apprentissage, validation = M.separer_periodes(entrainement, DATE_DEBUT_VALIDATION)
    resultats = []
    for nom in M.CANDIDATS:
        modele = M.entrainer(nom, apprentissage)
        proba, _, proposee = decider_avec_modele(modele, validation)
        resultat = M.evaluer_strategie(proposee, validation[M.CIBLE], validation["indemnite"])
        resultats.append({"modele": nom, "roc_auc": M.mesurer_classement(validation[M.CIBLE], proba)["roc_auc"],
                          "benefice": resultat["benefice"]})
    reference = M.evaluer_strategie(np.ones(len(validation), bool), validation[M.CIBLE], validation["indemnite"])
    resultats.append({"modele": "proposer à tous (sans modèle)", "roc_auc": 0.5, "benefice": reference["benefice"]})
    meilleur = max((r for r in resultats if r["modele"] in M.CANDIDATS), key=lambda r: r["benefice"])
    return meilleur["modele"], resultats


def valider_dans_le_temps(nom: str, entrainement: pd.DataFrame, nb_plis: int = 4) -> dict:
    """Validation croisée temporelle sur 2017 : on apprend toujours sur le passé, on juge sur la suite."""
    ordonne = entrainement.sort_values("date_achat").reset_index(drop=True)
    scores = []
    for indices_passe, indices_futur in TimeSeriesSplit(n_splits=nb_plis).split(ordonne):
        modele = M.entrainer(nom, ordonne.iloc[indices_passe])
        futur = ordonne.iloc[indices_futur]
        scores.append(M.mesurer_classement(futur[M.CIBLE], M.predire_probabilite(modele, futur))["roc_auc"])
    return {"roc_auc_moyenne": float(np.mean(scores)), "roc_auc_ecart_type": float(np.std(scores)), "plis": scores}


def comparer_strategies(test: pd.DataFrame, proposee_modele, distance_mediane: float) -> dict:
    """Bénéfice sur le test de chaque stratégie, avec la même hypothèse de souscription."""
    sinistre, indemnite, region = test[M.CIBLE], test["indemnite"], test["region_client"]
    distance = test["distance_km"].fillna(distance_mediane)
    proposee_regle = M.decider_eligibilite(distance, SEUIL_DISTANCE_REFUS_KM, region)
    # Contrôle : refuser AU HASARD autant de commandes que le modèle. Si le modèle ne faisait
    # pas mieux que ce contrôle, il ne servirait à rien.
    generateur = np.random.default_rng(SEED)
    proposee_hasard = generateur.permutation(np.asarray(proposee_modele))
    return {
        "proposer à tous (situation actuelle)": M.evaluer_strategie(np.ones(len(test), bool), sinistre, indemnite),
        f"règle : refuser au-delà de {SEUIL_DISTANCE_REFUS_KM} km": M.evaluer_strategie(proposee_regle, sinistre, indemnite),
        "contrôle : refus au hasard (même nombre)": M.evaluer_strategie(proposee_hasard, sinistre, indemnite),
        "modèle, sans plafond par région": M.evaluer_strategie(
            M.decider_eligibilite(M.calculer_cout_attendu(test["proba"], indemnite), PRIX_GARANTIE, region, 1.0),
            sinistre, indemnite),
        "modèle, plafond de refus par région (recommandé)": M.evaluer_strategie(proposee_modele, sinistre, indemnite),
    }


def entrainer_et_evaluer() -> dict:
    """Enchaîne toutes les étapes et renvoie les métriques (aussi sauvegardées en JSON)."""
    if not BASE.exists():
        charger_archive_dans_sqlite()
    table = M.preparer_variables(lire_table_analyse())
    entrainement, test = M.separer_periodes(table, DATE_DEBUT_TEST)

    nom, selection = choisir_modele(entrainement)
    stabilite = valider_dans_le_temps(nom, entrainement)

    modele = M.entrainer(nom, entrainement)
    test = test.copy()
    test["proba"], test["cout_attendu"], test["proposee"] = decider_avec_modele(modele, test)

    metriques = {
        "modele_retenu": nom,
        "selection_sur_validation": selection,
        "validation_croisee_temporelle_2017": stabilite,
        "test": {
            "periode": [str(test["date_achat"].min().date()), str(test["date_achat"].max().date())],
            "commandes": int(len(test)),
            "classement": M.mesurer_classement(test[M.CIBLE], test["proba"]),
            "strategies": comparer_strategies(test, test["proposee"], entrainement["distance_km"].median()),
            "calibration": M.tableau_calibration(test[M.CIBLE], test["proba"]).to_dict(orient="records"),
            "equite": M.tableau_equite(test["region_client"], test["proposee"], test[M.CIBLE]).to_dict(orient="records"),
            "importance": M.calculer_importance(modele, test).to_dict(orient="records"),
        },
        "parametres": {"prix_garantie": PRIX_GARANTIE, "chargement": CHARGEMENT,
                       "part_refus_max_par_region": PART_REFUS_MAX_PAR_REGION},
    }

    DOSSIER_MODELES.mkdir(parents=True, exist_ok=True)
    joblib.dump({"modele": modele, "nom": nom, "variables": M.VARIABLES}, FICHIER_MODELE)
    FICHIER_METRIQUES.write_text(json.dumps(metriques, indent=2, ensure_ascii=False), encoding="utf-8")
    colonnes = ["commande_id", "date_achat", "etat_client", "region_client", "etat_vendeur", "categorie",
                "distance_km", "delai_promis_jours", "frais_port", "indemnite", "proba", "cout_attendu",
                "proposee", M.CIBLE]
    test[colonnes].to_csv(FICHIER_PREDICTIONS, index=False)
    return metriques


def afficher_resume(metriques: dict) -> None:
    """Résumé lisible dans le terminal."""
    print(f"Modèle retenu (sur la validation 2017) : {metriques['modele_retenu']}")
    for ligne in metriques["selection_sur_validation"]:
        print(f"  {ligne['modele']:32} ROC-AUC {ligne['roc_auc']:.3f}  bénéfice validation {ligne['benefice']:9,.0f} R$")
    stabilite = metriques["validation_croisee_temporelle_2017"]
    print(f"Validation croisée temporelle 2017 : ROC-AUC {stabilite['roc_auc_moyenne']:.3f} ± {stabilite['roc_auc_ecart_type']:.3f}")
    classement = metriques["test"]["classement"]
    print(f"\nTest {metriques['test']['periode'][0]} -> {metriques['test']['periode'][1]} "
          f"({metriques['test']['commandes']:,} commandes) : ROC-AUC {classement['roc_auc']:.3f}, "
          f"PR-AUC {classement['pr_auc']:.3f} (hasard : {classement['taux_sinistre']:.3f})")
    for nom, resultat in metriques["test"]["strategies"].items():
        print(f"  {nom:50} proposée à {resultat['part_proposee']:6.1%}  bénéfice {resultat['benefice']:9,.0f} R$  "
              f"S/P {resultat['ratio_sinistres_primes']:.2f}")


if __name__ == "__main__":
    afficher_resume(entrainer_et_evaluer())
