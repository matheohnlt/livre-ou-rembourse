"""Analyse de robustesse, suite à une question du COMEX : les conclusions tiennent-elles si l'on
coupe plus tard dans le temps ?

Découpage principal : apprentissage sur 2017, test sur janvier-août 2018.
Découpage de robustesse : apprentissage de janvier 2017 à mars 2018 (crise de février-mars incluse,
environ 67 % des commandes), test sur avril-août 2018. Le split reste temporel : un découpage au
hasard mélangerait le futur dans l'apprentissage.

Lancer : python -m backend.robustesse
"""
import pandas as pd

from backend import model as M
from backend.config import (
    BASE,
    DATE_DEBUT_TEST,
    DATE_DEBUT_TEST_ROBUSTESSE,
    DATE_DEBUT_VALIDATION,
    DATE_DEBUT_VALIDATION_ROBUSTESSE,
)
from backend.data import charger_archive_dans_sqlite, lire_table_analyse
from backend.train import choisir_modele, comparer_strategies, decider_avec_modele

DECOUPAGES = {
    "principal (test janvier-août 2018)": (DATE_DEBUT_VALIDATION, DATE_DEBUT_TEST),
    "robustesse (test avril-août 2018)": (DATE_DEBUT_VALIDATION_ROBUSTESSE, DATE_DEBUT_TEST_ROBUSTESSE),
}


def evaluer_decoupage(table: pd.DataFrame, date_validation: str, date_test: str) -> dict:
    """Même chaîne que train.py : choix du modèle sur la validation, puis un seul passage sur le test."""
    entrainement, test = M.separer_periodes(table, date_test)
    _, validation = M.separer_periodes(entrainement, date_validation)
    nom, selection = choisir_modele(entrainement, date_validation)
    modele = M.entrainer(nom, entrainement)
    test = test.copy()
    test["proba"], _, test["proposee"] = decider_avec_modele(modele, test)
    return {
        "modele": nom,
        "part_apprentissage": len(entrainement) / len(table),
        "taux_sinistre_validation": float(validation[M.CIBLE].mean()),
        "taux_sinistre_test": float(test[M.CIBLE].mean()),
        "roc_auc_test": M.mesurer_classement(test[M.CIBLE], test["proba"])["roc_auc"],
        "selection": selection,
        "strategies": comparer_strategies(test, test["proposee"], entrainement["distance_km"].median()),
    }


def comparer_decoupages() -> dict:
    if not BASE.exists():
        charger_archive_dans_sqlite()
    table = M.preparer_variables(lire_table_analyse())
    return {nom: evaluer_decoupage(table, *dates) for nom, dates in DECOUPAGES.items()}


def afficher(resultats: dict) -> None:
    for nom, r in resultats.items():
        print(f"\nDécoupage {nom} : {r['part_apprentissage']:.0%} des commandes en apprentissage, "
              f"modèle retenu {r['modele']}")
        print(f"  Validation : {r['taux_sinistre_validation']:.1%} de sinistres")
        for ligne in r["selection"]:
            print(f"    {ligne['modele']:32} bénéfice validation {ligne['benefice']:9,.0f} R$")
        print(f"  Test : {r['taux_sinistre_test']:.1%} de sinistres, ROC-AUC {r['roc_auc_test']:.3f}")
        for strategie, resultat in r["strategies"].items():
            print(f"    {strategie:50} bénéfice {resultat['benefice']:9,.0f} R$  "
                  f"S/P {resultat['ratio_sinistres_primes']:.2f}")


if __name__ == "__main__":
    afficher(comparer_decoupages())
