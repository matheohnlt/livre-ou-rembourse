"""Écran Exploration : le besoin (retards et avis), la carte du risque et les 5 personas."""
import streamlit as st

from backend import service

# Couleur des points de la carte selon le taux de sinistre de l'État (affichage seulement).
VERT, ORANGE, ROUGE = "#2e7d32", "#ef6c00", "#c62828"


def _afficher_chiffres_cles() -> None:
    resume = service.resume_exploration()
    col1, col2, col3 = st.columns(3)
    col1.metric("Commandes expédiées étudiées", f"{resume['commandes']:,}".replace(",", " "))
    col2.metric("En retard ou jamais livrées", f"{resume['taux_sinistre']:.1%}")
    col3.metric("Mauvais avis (1-2 ★) quand la commande est en retard", f"{resume['avec_sinistre']:.0%}",
                delta=f"contre {resume['sans_sinistre']:.0%} à l'heure", delta_color="off")


def _afficher_evolution() -> None:
    st.markdown("**Le risque n'est pas stable : novembre 2017 (Black Friday) et février-mars 2018 (crise).**")
    evolution = service.evolution_mensuelle().set_index("mois")
    st.line_chart(evolution["taux_sinistre"], y_label="Part des commandes en retard", x_label="Mois d'achat")


def _afficher_carte() -> None:
    st.markdown("**Où sont les retards ?** Taille du point = nombre de commandes ; couleur = taux de retard.")
    etats = service.risque_par_etat().dropna(subset=["lat", "lng"]).copy()
    etats["couleur"] = etats["taux_sinistre"].apply(lambda t: ROUGE if t > 0.12 else ORANGE if t > 0.08 else VERT)
    etats["taille"] = 20000 + 3 * etats["commandes"]
    st.map(etats, latitude="lat", longitude="lng", size="taille", color="couleur")
    st.caption("Vert : moins de 8 % de retards · orange : 8 à 12 % · rouge : plus de 12 %.")
    tableau = etats[["etat_client", "commandes", "taux_sinistre", "delai_promis_jours"]].copy()
    tableau.columns = ["État", "Commandes", "Taux de retard", "Délai promis médian (jours)"]
    st.dataframe(tableau.style.format({"Taux de retard": "{:.1%}", "Commandes": "{:,.0f}"}), hide_index=True)


def _afficher_personas() -> None:
    st.markdown("**Les 5 profils de commandes (K-means, appris sur 2017).** "
                "Le retard n'a pas servi à former les groupes : on le regarde après.")
    portraits = service.portraits_segments()
    tableau = portraits[["nom", "part_commandes", "distance_km", "delai_promis_jours", "frais_port", "poids_g",
                         "taux_sinistre", "taux_sinistre_test", "part_refusee_test"]].copy()
    tableau.columns = ["Profil", "Part des commandes", "Distance médiane (km)", "Délai promis (j)", "Frais de port (R$)",
                       "Poids médian (g)", "Retards 2017", "Retards 2018", "Garantie refusée 2018"]
    st.dataframe(tableau.style.format({"Part des commandes": "{:.0%}", "Distance médiane (km)": "{:,.0f}",
                                       "Frais de port (R$)": "{:.2f}", "Poids médian (g)": "{:,.0f}",
                                       "Retards 2017": "{:.1%}", "Retards 2018": "{:.1%}",
                                       "Garantie refusée 2018": "{:.0%}"}), hide_index=True)
    st.caption("À retenir : le « grand voyageur » est peu risqué, car Olist lui promet déjà un long délai. "
               "Les colis lourds sont souvent refusés non parce qu'ils sont plus souvent en retard, mais parce "
               "qu'un retard coûterait cher (frais de port élevés remboursés).")
    with st.expander("Pourquoi 5 profils ? (méthode du coude et silhouette)"):
        choix = service.choix_nombre_segments().set_index("k")
        col1, col2 = st.columns(2)
        col1.line_chart(choix["inertie"], y_label="Inertie", x_label="Nombre de profils k")
        col2.line_chart(choix["silhouette"], y_label="Silhouette", x_label="Nombre de profils k")
        st.caption("Pas de coude net et une silhouette moyenne (0,31 pour k = 5) : les groupes se touchent. "
                   "k = 5 est un choix métier : il isole le « grand voyageur », que k = 3 ou 4 mélangent.")


def afficher() -> None:
    st.subheader("Pourquoi une garantie retard ? Où est le risque ?")
    _afficher_chiffres_cles()
    _afficher_evolution()
    _afficher_carte()
    _afficher_personas()
