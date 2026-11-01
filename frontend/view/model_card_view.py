"""Écran Le modèle : performances, variables importantes et limites, écrites en clair."""
import streamlit as st

from backend import service

NOMS_LISIBLES = {
    "logistique": "Régression logistique",
    "foret_100": "Forêt aléatoire (100 commandes par feuille)",
    "boosting": "Gradient boosting (HistGradientBoosting)",
}

LIMITES = [
    "**Il ne prévoit pas les crises** : en février-mars 2018, les retards ont triplé. Il faut surveiller le taux "
    "de retard chaque mois et réentraîner le modèle.",
    "**Il surestime le risque des commandes les plus risquées** (22 % prédit contre 17,6 % observé pour la tranche "
    "la plus risquée) : en moyenne, il prédit 9,0 % de retards pour 8,7 % observés.",
    "**Les variables « trajet » renseignent indirectement sur l'État du client** : sans précaution, les refus se "
    "concentreraient sur quelques États (jusqu'à 66 % en Espírito Santo). C'est pourquoi le plafond de 20 % de "
    "refus s'applique à chaque État.",
    "**La part de clients qui achètent la garantie (20 %) est une hypothèse** : elle change les montants, pas le "
    "classement des stratégies.",
    "**Une ROC-AUC de 0,67 reste modeste** : un retard dépend aussi de ce que les données ne voient pas "
    "(grèves, transporteur, météo).",
    "**Données de 2017-2018** : à réentraîner sur des données récentes avant tout usage réel.",
]


def afficher() -> None:
    resume = service.resume_modele()
    st.subheader(f"Le modèle retenu : {NOMS_LISIBLES.get(resume['modele_retenu'], resume['modele_retenu'])}")
    st.caption("Choisi sur deux validations internes à 2017 (jugées de juillet à septembre et d'octobre à décembre, "
               "en apprenant sur les mois précédents), avec la ROC-AUC moyenne. Le test 2018 n'a été regardé "
               "qu'une seule fois, à la fin.")

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
        selection.columns = ["Modèle", "ROC-AUC validation (moyenne)", "Bénéfice validation (R$, moyenne)"]
        st.dataframe(selection.style.format({"ROC-AUC validation (moyenne)": "{:.3f}",
                                             "Bénéfice validation (R$, moyenne)": "{:,.0f}"}), hide_index=True)
        st.caption("Le bénéfice ne départage pas les modèles : avec le plafond de 20 % de refus par État, "
                   "les écarts sont faibles et changent de sens d'une fenêtre à l'autre. Le choix se fait donc "
                   "sur la ROC-AUC.")

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
