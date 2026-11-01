"""Quick wins : retrait de 2 variables + calibration. Évalué UNIQUEMENT sur 2017.

Deux fenêtres de validation (on apprend sur le passé, on juge sur la suite) :
  F1 : apprentissage janv.-juin 2017 -> validation juil.-sept. 2017
  F2 : apprentissage janv.-sept. 2017 -> validation oct.-déc. 2017 (la validation officielle)
Le test 2018 n'est pas lu.
"""
import json
import sys

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from backend import model as M
from backend.config import CHARGEMENT, DATE_DEBUT_TEST, PRIX_GARANTIE, SEED
from backend.data import lire_table_analyse

RETIREES = ["volume_total_cm3", "nb_mensualites"]
NUM_COMPLET = M.VARIABLES_NUMERIQUES
NUM_REDUIT = [v for v in NUM_COMPLET if v not in RETIREES]
CAT = M.VARIABLES_CATEGORIELLES


def pipeline(estimateur, num):
    prep = ColumnTransformer([
        ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), num),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CAT),
    ])
    return make_pipeline(prep, estimateur)


def foret():
    return RandomForestClassifier(n_estimators=300, min_samples_leaf=100, max_features="sqrt",
                                  random_state=SEED, n_jobs=-1)


def logistique():
    return LogisticRegression(max_iter=2000)


def calibre(base, methode):
    # Plis temporels : chaque calibrateur est appris sur des commandes POSTÉRIEURES à celles
    # qui ont servi au modèle. ensemble=True : moyenne des modèles calibrés de chaque pli.
    return CalibratedClassifierCV(base, method=methode, cv=TimeSeriesSplit(n_splits=3))


VARIANTES = {
    "A  forêt, 11 variables (actuel)": lambda: (pipeline(foret(), NUM_COMPLET), NUM_COMPLET),
    "B  forêt, 9 variables": lambda: (pipeline(foret(), NUM_REDUIT), NUM_REDUIT),
    "C  forêt, 9 var. + isotonique": lambda: (calibre(pipeline(foret(), NUM_REDUIT), "isotonic"), NUM_REDUIT),
    "D  forêt, 9 var. + sigmoïde": lambda: (calibre(pipeline(foret(), NUM_REDUIT), "sigmoid"), NUM_REDUIT),
    "E  logistique, 11 variables": lambda: (pipeline(logistique(), NUM_COMPLET), NUM_COMPLET),
    "F  logistique, 9 variables": lambda: (pipeline(logistique(), NUM_REDUIT), NUM_REDUIT),
    "G  logistique, 9 var. + isotonique": lambda: (calibre(pipeline(logistique(), NUM_REDUIT), "isotonic"), NUM_REDUIT),
}

FENETRES = {"F1 juil.-sept.": ("2017-07-01", "2017-10-01"), "F2 oct.-déc.": ("2017-10-01", "2018-01-01")}


def mesurer(y, proba, val):
    classement = M.mesurer_classement(y, proba)
    cout = M.calculer_cout_attendu(proba, val["indemnite"], CHARGEMENT)
    proposee = M.decider_eligibilite(cout, PRIX_GARANTIE, val["region_client"])
    strat = M.evaluer_strategie(proposee, y, val["indemnite"])
    calib = M.tableau_calibration(y, proba)
    haut = calib.iloc[-1]
    return {
        "roc_auc": classement["roc_auc"], "pr_auc": classement["pr_auc"], "brier": classement["brier"],
        "proba_moy": float(np.mean(proba)), "taux_obs": float(np.mean(y)),
        "ecart_decile10": float(haut["taux_observe"] - haut["proba_moyenne"]),
        "ece": float(np.average(np.abs(calib["taux_observe"] - calib["proba_moyenne"]), weights=calib["commandes"])),
        "benefice": strat["benefice"], "part_proposee": strat["part_proposee"], "sp": strat["ratio_sinistres_primes"],
    }


def main():
    table = M.preparer_variables(lire_table_analyse())
    annee_2017 = table[table["date_achat"] < pd.Timestamp(DATE_DEBUT_TEST)].sort_values("date_achat")
    lignes = []
    for nom_f, (debut, fin) in FENETRES.items():
        app = annee_2017[annee_2017["date_achat"] < pd.Timestamp(debut)]
        val = annee_2017[(annee_2017["date_achat"] >= pd.Timestamp(debut)) & (annee_2017["date_achat"] < pd.Timestamp(fin))]
        ref = M.evaluer_strategie(np.ones(len(val), bool), val[M.CIBLE], val["indemnite"])["benefice"]
        for nom_v, fabrique in VARIANTES.items():
            modele, num = fabrique()
            cols = num + CAT
            modele.fit(app[cols], app[M.CIBLE])
            proba = modele.predict_proba(val[cols])[:, 1]
            r = mesurer(val[M.CIBLE].to_numpy(), proba, val)
            lignes.append({"fenetre": nom_f, "variante": nom_v, "n_app": len(app), "n_val": len(val),
                           "benef_proposer_tous": ref, **r})
            print(f"{nom_f:15} {nom_v:36} AUC {r['roc_auc']:.3f}  PR {r['pr_auc']:.3f}  "
                  f"Brier {r['brier']:.4f}  p̄ {r['proba_moy']:.3f}/{r['taux_obs']:.3f}  "
                  f"ECE {r['ece']:.4f}  bénéf {r['benefice']:8.0f}  prop {r['part_proposee']:.1%}", flush=True)
    pd.DataFrame(lignes).to_csv(sys.argv[1], index=False)


if __name__ == "__main__":
    main()
