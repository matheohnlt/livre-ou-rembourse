"""Écran Simulateur (pour le DAF) : et si nos hypothèses étaient différentes ?"""
import streamlit as st

from backend import service


def afficher() -> None:
    st.subheader("Combien ça rapporte ? Et si nos hypothèses changent ?")
    st.caption("Rejoue la décision sur les 53 344 commandes de janvier à août 2018, que le modèle n'a jamais vues. "
               "Les sinistres sont les retards réellement observés.")
    defaut = service.parametres_par_defaut()
    col1, col2, col3 = st.columns(3)
    prix = col1.slider("Prix de la garantie (R$)", 1.0, 10.0, defaut["prix"], step=0.5)
    bon_achat = col2.slider("Bon d'achat offert en cas de retard (R$)", 0.0, 40.0, defaut["bon_achat"], step=1.0)
    chargement = col3.slider("Marge et frais de l'assureur", 0.0, 0.6, defaut["chargement"], step=0.05)
    col4, col5 = st.columns(2)
    souscription = col4.slider("Part des clients qui achètent la garantie (hypothèse)", 0.05, 0.6,
                               defaut["taux_souscription"], step=0.05)
    plafond = col5.slider("Refus maximum par région (équité)", 0.05, 1.0, defaut["part_refus_max"], step=0.05)

    resultat = service.simuler(prix, bon_achat, chargement, plafond, souscription)
    strategies = resultat["strategies"].set_index("strategie")
    sans_modele = strategies.loc["Proposer à tous (sans modèle)"]
    recommande = strategies.loc["Modèle, avec plafond par région"]

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Bénéfice avec le modèle (8 mois)", f"{recommande['benefice']:,.0f} R$".replace(",", " "),
                 delta=f"{recommande['benefice'] - sans_modele['benefice']:+,.0f} R$ vs proposer à tous".replace(",", " "))
    col_b.metric("Sinistres payés pour 100 R$ encaissés", f"{100 * recommande['ratio_sinistres_primes']:.0f} R$",
                 delta=f"{100 * (recommande['ratio_sinistres_primes'] - sans_modele['ratio_sinistres_primes']):+.0f} R$",
                 delta_color="inverse")
    col_c.metric("Commandes à qui la garantie est proposée", f"{recommande['part_proposee']:.0%}")

    st.bar_chart(strategies["benefice"], y_label="Bénéfice (R$)", x_label="")
    tableau = strategies[["part_proposee", "garanties_vendues", "primes", "sinistres", "benefice", "ratio_sinistres_primes"]].copy()
    tableau.columns = ["Proposée à", "Garanties vendues", "Primes (R$)", "Sinistres (R$)", "Bénéfice (R$)", "Sinistres / primes"]
    st.dataframe(tableau.style.format({"Proposée à": "{:.0%}", "Garanties vendues": "{:,.0f}", "Primes (R$)": "{:,.0f}",
                                       "Sinistres (R$)": "{:,.0f}", "Bénéfice (R$)": "{:,.0f}", "Sinistres / primes": "{:.2f}"}))
    st.caption(f"Coût de la règle d'équité avec ces hypothèses : {resultat['cout_equite']:,.0f} R$ de bénéfice en moins."
               .replace(",", " ")
               + " La part de clients qui achètent est une hypothèse : elle change les montants, pas le classement.")
