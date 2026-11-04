"""Tests de l'analyse de robustesse : le second découpage reste temporel et sans chevauchement."""
from backend import model as M
from backend.config import (
    DATE_DEBUT,
    DATE_DEBUT_TEST,
    DATE_DEBUT_TEST_ROBUSTESSE,
    DATE_DEBUT_VALIDATION_ROBUSTESSE,
    DATE_FIN,
)


def test_les_dates_de_robustesse_sont_dans_l_ordre():
    assert DATE_DEBUT < DATE_DEBUT_TEST <= DATE_DEBUT_VALIDATION_ROBUSTESSE < DATE_DEBUT_TEST_ROBUSTESSE < DATE_FIN


def test_le_decoupage_de_robustesse_n_utilise_que_le_passe(table_analyse):
    entrainement, test = M.separer_periodes(table_analyse, DATE_DEBUT_TEST_ROBUSTESSE)
    assert entrainement["date_achat"].max() < test["date_achat"].min()
    assert 0.60 <= len(entrainement) / len(table_analyse) <= 0.75
