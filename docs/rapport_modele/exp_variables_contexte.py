"""Test des variables de contexte. Évalué UNIQUEMENT sur 2017 (fenêtres F1 et F2)."""
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from backend import model as M
from backend.config import DATE_DEBUT_TEST, SEED
from exp_quick_wins import FENETRES, NUM_REDUIT, CAT, mesurer, pipeline

ENSEMBLES = {
    "base (9 var.)": NUM_REDUIT,
    "+ taux 30 j": NUM_REDUIT + ["taux_retard_30j"],
    "+ trajet (marge, délai, taux)": NUM_REDUIT + ["marge_delai_jours", "delai_habituel_trajet", "taux_retard_trajet"],
    "+ tout": NUM_REDUIT + ["taux_retard_30j", "marge_delai_jours", "delai_habituel_trajet", "taux_retard_trajet"],
}
MODELES = {
    "logistique": lambda: LogisticRegression(max_iter=3000),
    "forêt": lambda: RandomForestClassifier(n_estimators=300, min_samples_leaf=100, max_features="sqrt",
                                            random_state=SEED, n_jobs=-1),
    "boosting": lambda: HistGradientBoostingClassifier(learning_rate=0.05, max_iter=300, min_samples_leaf=100,
                                                       l2_regularization=1.0, random_state=SEED),
}


def main():
    table = pd.read_pickle(sys.argv[1])
    annee_2017 = table[table["date_achat"] < pd.Timestamp(DATE_DEBUT_TEST)]
    lignes = []
    for nom_f, (debut, fin) in FENETRES.items():
        app = annee_2017[annee_2017["date_achat"] < pd.Timestamp(debut)]
        val = annee_2017[(annee_2017["date_achat"] >= pd.Timestamp(debut)) & (annee_2017["date_achat"] < pd.Timestamp(fin))]
        for nom_m, fabrique in MODELES.items():
            for nom_e, num in ENSEMBLES.items():
                cols = num + CAT
                modele = pipeline(fabrique(), num).fit(app[cols], app[M.CIBLE])
                proba = modele.predict_proba(val[cols])[:, 1]
                r = mesurer(val[M.CIBLE].to_numpy(), proba, val)
                lignes.append({"fenetre": nom_f, "modele": nom_m, "variables": nom_e, **r})
                print(f"{nom_f:15} {nom_m:11} {nom_e:30} AUC {r['roc_auc']:.3f}  PR {r['pr_auc']:.3f}  "
                      f"p̄ {r['proba_moy']:.3f}/{r['taux_obs']:.3f}  bénéf {r['benefice']:6.0f}", flush=True)
    pd.DataFrame(lignes).to_csv(sys.argv[2], index=False)


if __name__ == "__main__":
    main()
