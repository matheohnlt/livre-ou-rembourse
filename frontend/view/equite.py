"""Écran Équité (pour le DPO) : le modèle exclut-il certaines régions ?"""
import streamlit as st

from backend import service


def afficher() -> None:
    st.subheader("Est-ce équitable ? Aucune région n'est exclue")
    st.markdown(
        "L'État du client **n'est pas** une variable du modèle. Mais la distance et le délai promis suffisent "
        "à repérer les régions éloignées : **sans précaution, le modèle refuserait plus de 8 commandes sur 10 "
        "dans le Nord et le Nord-Est.** La règle d'équité plafonne donc les refus dans chaque région."
    )
    defaut = service.parametres_par_defaut()
    plafond = st.slider("Refus maximum par région", 0.05, 1.0, defaut["part_refus_max"], step=0.05, key="plafond_equite")
    resultat = service.simuler(part_refus_max=plafond)

    tableau = resultat["equite"][["region", "commandes", "taux_sinistre", "part_refusee_sans_plafond", "part_refusee"]].copy()
    tableau.columns = ["Région", "Commandes 2018", "Taux de retard", "Refusées sans la règle", "Refusées avec la règle"]
    st.dataframe(tableau.style.format({"Commandes 2018": "{:,.0f}", "Taux de retard": "{:.1%}",
                                       "Refusées sans la règle": "{:.0%}", "Refusées avec la règle": "{:.0%}"}),
                 hide_index=True)
    st.bar_chart(tableau.set_index("Région")[["Refusées sans la règle", "Refusées avec la règle"]],
                 y_label="Part des commandes refusées", stack=False)

    col1, col2 = st.columns(2)
    col1.metric("Coût de l'équité pour l'assureur (8 mois)", f"{resultat['cout_equite']:,.0f} R$".replace(",", " "))
    col2.metric("Bénéfice restant avec la règle",
                f"{resultat['strategies'].iloc[2]['benefice']:,.0f} R$".replace(",", " "))

    st.markdown("**Ce que la règle change concrètement :** le seuil de refus est relevé dans les régions éloignées. "
                "L'assureur y accepte des commandes qu'il sait moins rentables.")
    seuils = service.seuils_par_region()
    seuils.columns = ["Région", "On refuse si le coût attendu dépasse (R$)"]
    st.dataframe(seuils.style.format({"On refuse si le coût attendu dépasse (R$)": "{:.2f}"}), hide_index=True)
    st.caption("À vérifier en production : la part de refus par région chaque mois, et l'absence d'écart par "
               "État à l'intérieur d'une même région.")
