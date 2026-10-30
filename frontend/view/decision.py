"""Écran Décision (« Devis ») : au paiement, propose-t-on la garantie à cette commande ?"""
import streamlit as st

from backend import service

MODE_REEL = "Une commande réelle de 2018"
MODE_LIBRE = "Saisie libre"


def _choisir_commande() -> dict:
    """Point de départ : une commande réelle du test 2018, ou une commande typique à modifier."""
    mode = st.radio("Point de départ", [MODE_REEL, MODE_LIBRE], horizontal=True)
    if mode == MODE_LIBRE:
        return service.commande_type()
    commandes = service.lister_commandes_demo()
    libelles = dict(zip(commandes["commande_id"], commandes["libelle"]))
    commande_id = st.selectbox("Commande (vendeur → client · distance · poids · catégorie)",
                               commandes["commande_id"], format_func=libelles.get)
    return service.caracteristiques_commande(commande_id)


def _borner(valeur, minimum, maximum, si_manquant):
    """Valeur de départ d'un curseur : remplace un manquant et reste dans l'échelle du curseur
    (certaines commandes réelles dépassent l'échelle, par exemple 1 795 R$ de frais de port)."""
    if valeur is None or valeur != valeur:  # valeur != valeur : vrai seulement pour NaN
        valeur = si_manquant
    return min(max(valeur, minimum), maximum)


def _modifier(commande: dict) -> dict:
    """Curseurs pour faire varier la commande : c'est le cœur de la démo."""
    commande = dict(commande)
    commande["distance_km"] = float(st.slider("Distance vendeur → client (km)", 0, 4000,
                                              int(_borner(commande["distance_km"], 0, 4000, 400)), step=10))
    commande["delai_promis_jours"] = st.slider("Délai de livraison promis (jours)", 3, 60,
                                               int(_borner(commande["delai_promis_jours"], 3, 60, 23)))
    commande["frais_port"] = st.slider("Frais de port (R$)", 0.0, 150.0,
                                       float(_borner(commande["frais_port"], 0.0, 150.0, 18.0)), step=0.5)
    poids_kg = _borner(commande["poids_total_g"] / 1000 if commande["poids_total_g"] else None, 0.0, 40.0, 0.7)
    commande["poids_total_g"] = 1000 * st.slider("Poids total (kg)", 0.0, 40.0, float(round(poids_kg, 1)), step=0.1)
    commande["nb_articles"] = st.slider("Nombre d'articles", 1, 10, int(_borner(commande["nb_articles"], 1, 10, 1)))
    commande["meme_etat"] = int(st.checkbox("Vendeur et client dans le même État", value=bool(commande["meme_etat"])))
    regions = service.lister_regions()
    region = commande["region_client"] if commande["region_client"] in regions else "Sudeste"
    commande["region_client"] = st.selectbox("Région du client (pour la règle d'équité seulement)", regions,
                                             index=regions.index(region))
    types = service.lister_types_paiement()
    commande["type_paiement"] = st.selectbox("Mode de paiement", types, index=types.index(commande["type_paiement"]))
    return commande


def _afficher_resultat(commande: dict, devis: dict) -> None:
    col1, col2, col3 = st.columns(3)
    col1.metric("Risque de retard", f"{devis['proba']:.1%}")
    col2.metric("Remboursement si retard", f"{devis['indemnite']:.2f} R$", help="Frais de port + bon d'achat")
    col3.metric("Coût attendu (avec marge)", f"{devis['cout_attendu']:.2f} R$",
                delta=f"{devis['cout_attendu'] - devis['prix']:+.2f} R$ vs prix", delta_color="inverse")
    if devis["proposee"]:
        st.success(f"✅ Garantie proposée à {devis['prix']:.0f} R$ : {devis['raison']}.")
    else:
        st.error(f"❌ Garantie non proposée : {devis['raison']}.")
    st.caption(f"Règle : on propose si le coût attendu ≤ {devis['seuil_region']:.2f} R$, seuil de la région "
               f"{commande['region_client']} (le prix de {devis['prix']:.0f} R$, relevé si la région dépasserait "
               "20 % de refus).")
    if commande.get("issue_reelle"):
        st.info(f"Ce qui s'est réellement passé : commande **{commande['issue_reelle']}**. "
                f"Profil : **{commande['segment']}**.")


def afficher() -> None:
    st.subheader("Proposer la garantie « Livré ou Remboursé » à cette commande ?")
    st.caption("Au paiement, l'outil estime le risque de retard et décide d'afficher ou non la garantie à 4 R$. "
               "Seules des informations connues au paiement sont utilisées.")
    commande = _choisir_commande()
    colonne_saisie, colonne_resultat = st.columns([1, 1])
    with colonne_saisie:
        commande = _modifier(commande)
    with colonne_resultat:
        _afficher_resultat(commande, service.calculer_devis(commande))
