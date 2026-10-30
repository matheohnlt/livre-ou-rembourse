"""Tests du service (la seule porte du frontend) : une décision cohérente pour une commande."""
import pytest

from backend import service


def test_petite_commande_locale_proposee_et_commande_incomplete_refusee(modele_entraine):
    commande = service.commande_type()
    commande.update(distance_km=50.0, meme_etat=1, frais_port=10.0, poids_total_g=500.0, region_client="Sudeste")
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
    attendu = service.metriques()["test"]["strategies"]["modèle, plafond de refus par région (recommandé)"]["benefice"]
    assert simulation["Modèle, avec plafond par région"] == pytest.approx(attendu)
