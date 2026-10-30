"""Tests sur les données : chargement complet, une ligne par commande, cible propre, pas de fuite."""
import pandas as pd
import pytest

from backend.config import DATE_DEBUT, DATE_FIN
from backend.data import calculer_distance_km

# Colonnes qui ne sont connues qu'APRÈS le paiement : elles ne doivent jamais entrer dans la table.
COLONNES_INTERDITES = (
    "order_delivered_customer_date",
    "order_delivered_carrier_date",
    "order_status",
    "review_score",
    "review_comment_message",
)


def test_les_9_tables_sont_chargees_en_entier(base_test):
    _, nb_lignes = base_test
    assert len(nb_lignes) == 9
    assert nb_lignes["commandes"] == 99_441  # nombre de lignes du CSV d'origine
    assert nb_lignes["articles"] == 112_650


def test_une_ligne_par_commande(table_analyse):
    # Si un JOIN multiplie les lignes (articles, paiements), ce test échoue.
    assert table_analyse["commande_id"].is_unique


def test_cible_binaire_et_taux_plausible(table_analyse):
    assert set(table_analyse["sinistre"].unique()) == {0, 1}
    assert 0.03 < table_analyse["sinistre"].mean() < 0.15


def test_aucune_variable_connue_apres_le_paiement(table_analyse):
    presentes = [col for col in COLONNES_INTERDITES if col in table_analyse.columns]
    assert presentes == []


def test_commandes_dans_la_periode(table_analyse):
    assert table_analyse["date_achat"].min() >= pd.Timestamp(DATE_DEBUT)
    assert table_analyse["date_achat"].max() < pd.Timestamp(DATE_FIN)


def test_coordonnees_dans_le_bresil_et_valeurs_impossibles_corrigees(table_analyse):
    # Les points GPS hors du Brésil et les poids nuls sont des erreurs : la requête SQL les écarte.
    lat = table_analyse["lat_client"].dropna()
    assert lat.between(-34.0, 5.3).all()
    assert not (table_analyse["poids_total_g"] == 0).any()
    assert (table_analyse["nb_mensualites"] >= 1).all()
    assert table_analyse["type_paiement"].notna().all()


def test_distance_sao_paulo_rio():
    # São Paulo -> Rio de Janeiro : environ 360 km à vol d'oiseau.
    distance = calculer_distance_km(-23.55, -46.63, -22.91, -43.17)
    assert distance == pytest.approx(360, abs=10)
    assert calculer_distance_km(-23.55, -46.63, -23.55, -46.63) == pytest.approx(0)
