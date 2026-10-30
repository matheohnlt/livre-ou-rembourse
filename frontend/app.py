"""Frontend Streamlit : affichage et saisie uniquement. Toute la logique est dans backend.service.

Lancement (depuis la racine du dépôt) : python -m streamlit run frontend/app.py
"""
import streamlit as st

from backend import service
from frontend.view import decision, equite, exploration, model_card_view, simulateur

st.set_page_config(page_title="Livré ou Remboursé", page_icon="📦", layout="wide")
st.title("📦 Livré ou Remboursé")
st.caption(
    "AssurColis (assurtech fictive) × marketplace Olist · démonstrateur de formation. "
    "Données réelles Olist 2017-2018 (Kaggle, CC BY-NC-SA 4.0)."
)

if not service.modele_disponible():
    st.error("Modèle absent. Lancer d'abord : `python -m backend.train`")
    st.stop()

onglets = st.tabs(["🛒 Devis", "💰 Simulateur", "🗺️ Exploration", "⚖️ Équité", "🧠 Le modèle"])
with onglets[0]:
    decision.afficher()
with onglets[1]:
    simulateur.afficher()
with onglets[2]:
    exploration.afficher()
with onglets[3]:
    equite.afficher()
with onglets[4]:
    model_card_view.afficher()
