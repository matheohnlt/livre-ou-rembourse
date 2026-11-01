"""Écran Équité (pour le DPO) : le modèle exclut-il certains États ou certaines régions ?"""
import streamlit as st

from backend import service

FORMAT_PARTS = {"Taux de retard": "{:.1%}", "Refusées sans la règle": "{:.0%}",
                "Refusées, plafond par région": "{:.0%}", "Refusées, plafond par État": "{:.0%}"}


def afficher() -> None:
    st.subheader("Est-ce équitable ? Aucun État n'est exclu")
    st.markdown(
        "L'État du client **n'est pas** une variable du modèle. Mais la distance, le délai promis et l'historique "
        "des trajets suffisent à repérer les États où les retards sont fréquents : **sans précaution, le modèle "
        "refuserait la grande majorité des commandes du Nord et du Nord-Est.** Un plafond par région ne suffit "
        "pas : les refus se concentreraient sur quelques États d'une même région. La règle d'équité plafonne "
        "donc les refus **dans chaque État**."
    )
    defaut = service.parametres_par_defaut()
    plafond = st.slider("Refus maximum par État", 0.05, 1.0, defaut["part_refus_max"], step=0.05, key="plafond_equite")
    resultat = service.simuler(part_refus_max=plafond)

    col1, col2 = st.columns(2)
    col1.metric("Coût de l'équité pour l'assureur (8 mois)", f"{resultat['cout_equite']:,.0f} R$".replace(",", " "))
    col2.metric("Bénéfice restant avec la règle",
                f"{resultat['strategies'].iloc[3]['benefice']:,.0f} R$".replace(",", " "))

    st.markdown("**Par région**")
    regions = resultat["equite"][["region", "commandes", "taux_sinistre", "part_refusee_sans_plafond",
                                  "part_refusee_plafond_region", "part_refusee"]].copy()
    regions.columns = ["Région", "Commandes 2018", "Taux de retard", "Refusées sans la règle",
                       "Refusées, plafond par région", "Refusées, plafond par État"]
    st.dataframe(regions.style.format({"Commandes 2018": "{:,.0f}", **FORMAT_PARTS}), hide_index=True)

    st.markdown("**Par État** : avec un simple plafond par région, certains États seraient bien plus refusés que "
                "les autres.")
    etats = resultat["equite_par_etat"][["etat", "region", "commandes", "taux_sinistre", "part_refusee_sans_plafond",
                                         "part_refusee_plafond_region", "part_refusee"]].copy()
    etats.columns = ["État", "Région", "Commandes 2018", "Taux de retard", "Refusées sans la règle",
                     "Refusées, plafond par région", "Refusées, plafond par État"]
    st.dataframe(etats.style.format({"Commandes 2018": "{:,.0f}", **FORMAT_PARTS}), hide_index=True)
    st.bar_chart(etats.set_index("État")[["Refusées, plafond par région", "Refusées, plafond par État"]],
                 y_label="Part des commandes refusées", stack=False)

    st.markdown("**Ce que la règle change concrètement :** le seuil de refus est relevé dans les États où les "
                "retards sont fréquents. L'assureur y accepte des commandes qu'il sait moins rentables.")
    seuils = service.seuils_par_etat()
    seuils.columns = ["État", "Région", "On refuse si le coût attendu dépasse (R$)"]
    st.dataframe(seuils.style.format({"On refuse si le coût attendu dépasse (R$)": "{:.2f}"}), hide_index=True)
    st.caption("À vérifier en production : la part de refus par État chaque mois. Les petits États (moins de "
               "100 commandes) ont des parts de refus instables d'un mois à l'autre.")
