"""Écran Le modèle : performances, variables importantes et limites, écrites en clair."""
import streamlit as st

from backend import service

NOMS_LISIBLES = {
    "logistique": "Régression logistique",
    "foret_50": "Forêt aléatoire (50 commandes par feuille)",
    "foret_100": "Forêt aléatoire (100 commandes par feuille)",
    "foret_200": "Forêt aléatoire (200 commandes par feuille)",
}

LIMITES = [
    "**Le modèle classe bien, mais il sous-estime le niveau du risque en 2018** (7 % prédit contre 8,7 % observé) : "
    "la marge de 30 % absorbe une partie de cet écart.",
    "**Il ne prévoit pas les crises** : en février-mars 2018, les retards ont triplé. Il faut surveiller le taux "
    "de retard chaque mois et réentraîner le modèle.",
    "**La part de clients qui achètent la garantie (20 %) est une hypothèse** : elle change les montants, pas le "
    "classement des stratégies.",
    "**Une ROC-AUC de 0,64 est modeste** : un retard dépend aussi de ce que les données ne voient pas "
    "(grèves, transporteur, météo).",
    "**Données de 2017-2018** : à réentraîner sur des données récentes avant tout usage réel.",
]


def afficher() -> None:
    resume = service.resume_modele()
    st.subheader(f"Le modèle retenu : {NOMS_LISIBLES.get(resume['modele_retenu'], resume['modele_retenu'])}")
    st.caption("Choisi sur une validation interne à 2017 (appris de janvier à septembre, jugé d'octobre à décembre) "
               "avec le bénéfice de l'assureur. Le test 2018 n'a été regardé qu'une seule fois, à la fin.")

    classement = resume["classement"]
    validation = resume["validation_croisee"]
    col1, col2, col3 = st.columns(3)
    col1.metric("ROC-AUC sur le test 2018", f"{classement['roc_auc']:.2f}", help="0,5 = hasard, 1 = parfait")
    col2.metric("PR-AUC sur le test 2018", f"{classement['pr_auc']:.3f}",
                delta=f"hasard : {classement['taux_sinistre']:.3f}", delta_color="off")
    col3.metric("ROC-AUC en validation croisée 2017",
                f"{validation['roc_auc_moyenne']:.2f} ± {validation['roc_auc_ecart_type']:.2f}")

    st.markdown("**Ce qui compte pour le client : le bénéfice sur le test 2018 (53 344 commandes)**")
    strategies = resume["strategies"][["strategie", "part_proposee", "benefice", "ratio_sinistres_primes"]].copy()
    strategies.columns = ["Stratégie", "Proposée à", "Bénéfice (R$)", "Sinistres / primes"]
    st.dataframe(strategies.style.format({"Proposée à": "{:.0%}", "Bénéfice (R$)": "{:,.0f}",
                                          "Sinistres / primes": "{:.2f}"}), hide_index=True)
    st.caption("Le contrôle « refus au hasard » refuse autant de commandes que le modèle : s'il faisait aussi bien, "
               "le modèle ne servirait à rien.")

    with st.expander("Comment le modèle a été choisi (validation 2017)"):
        selection = resume["selection"].copy()
        selection["modele"] = selection["modele"].map(lambda nom: NOMS_LISIBLES.get(nom, nom))
        selection.columns = ["Modèle", "ROC-AUC validation", "Bénéfice validation (R$)"]
        st.dataframe(selection.style.format({"ROC-AUC validation": "{:.3f}", "Bénéfice validation (R$)": "{:,.0f}"}),
                     hide_index=True)
        st.caption("La forêt et la logistique sont presque à égalité : l'écart de bénéfice est faible.")

    col_gauche, col_droite = st.columns(2)
    with col_gauche:
        st.markdown("**Variables les plus utilisées** (importance par permutation)")
        importance = resume["importance"].set_index("variable")["importance"].sort_values(ascending=False)
        st.bar_chart(importance, y_label="Baisse de ROC-AUC si on mélange la variable", x_label="")
        st.caption("Une variable importante est utilisée par le modèle : ce n'est pas une cause.")
    with col_droite:
        st.markdown("**Calibration** : risque prédit contre retards observés, par tranche")
        calibration = resume["calibration"].set_index("tranche")[["proba_moyenne", "taux_observe"]]
        calibration.columns = ["Risque prédit", "Retards observés"]
        st.line_chart(calibration, y_label="Part de commandes en retard", x_label="Tranche de risque (1 = la plus sûre)")

    st.markdown("**Ce que le modèle ne sait pas faire**")
    for limite in LIMITES:
        st.markdown(f"- {limite}")
    st.markdown("**Usage prévu** : décider d'afficher ou non la garantie au paiement. "
                "**À éviter** : refuser une livraison ou modifier un prix de vente sur la base de ce score.")
