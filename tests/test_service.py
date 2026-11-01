"""Tests du service (la seule porte du frontend) : une décision cohérente pour une commande."""
import pytest

from backend import service


def test_petite_commande_locale_proposee_et_commande_incomplete_refusee(modele_entraine):
    commande = service.commande_type()
    commande.update(distance_km=50.0, meme_etat=1, frais_port=10.0, poids_total_g=500.0, etat_client="SP")
    devis = service.calculer_devis(commande)
    assert 0 < devis["proba"] < 1
    assert devis["indemnite"] == pytest.approx(10.0 + 15.0)  # frais de port + bon d'achat
    assert devis["proposee"]

    del commande["distance_km"]
    with pytest.raises(ValueError):
        service.calculer_devis(commande)


def test_le_simulateur_retrouve_les_chiffres_de_l_entrainement(modele_entraine):
    # Avec les hypothèses par défaut, rejouer la décision doit redonner exactement le bénéfice
    # calculé par backend.train : sinon, l'appli et le README afficheraient des chiffres différents.
    simulation = service.simuler()["strategies"].set_index("strategie")["benefice"]
    strategies = service.metriques()["test"]["strategies"]
    assert simulation["Modèle, plafond par État (recommandé)"] == pytest.approx(
        strategies["modèle, plafond de refus par État (recommandé)"]["benefice"])
    assert simulation["Modèle, plafond par région"] == pytest.approx(
        strategies["modèle, plafond de refus par région"]["benefice"])


def test_aucun_etat_ne_depasse_le_plafond_de_refus(modele_entraine):
    equite = service.simuler()["equite_par_etat"]
    plafond = service.parametres_par_defaut()["part_refus_max"]
    assert (equite["part_refusee"] <= plafond + 1e-9).all()
