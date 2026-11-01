"""Tests des variables « trajet » : elles ne doivent utiliser que le passé (aucune fuite)."""
import pandas as pd
import pytest

from backend.trajets import ajouter_variables_trajet, calculer_marge, photographier_trajets


def _historique():
    # Trajet SP>RJ : 40 commandes livrées en 10 jours avant le 1er mars, toutes à l'heure ;
    # puis, en mars, 40 commandes livrées en 30 jours, toutes en retard.
    lignes = []
    for i in range(40):
        achat = pd.Timestamp("2017-01-01") + pd.Timedelta(days=i)
        lignes.append({"jour_achat": achat, "jour_promis": achat + pd.Timedelta(days=15),
                       "jour_livre": achat + pd.Timedelta(days=10), "sinistre": 0, "delai_reel": 10})
    for i in range(40):
        achat = pd.Timestamp("2017-02-20") + pd.Timedelta(days=i % 5)
        lignes.append({"jour_achat": achat, "jour_promis": pd.Timestamp("2017-03-05"),
                       "jour_livre": pd.Timestamp("2017-03-25"), "sinistre": 1, "delai_reel": 30})
    historique = pd.DataFrame(lignes)
    historique["trajet"] = "SP>RJ"
    return historique


def test_la_photo_n_utilise_que_les_issues_connues_a_sa_date():
    historique = _historique()
    photo, _ = photographier_trajets(historique, "2017-03-01", min_commandes=30, lissage=0)
    # Au 1er mars, les commandes en retard ne sont ni livrées ni échues : on ne les voit pas encore.
    assert photo.loc["SP>RJ", "delai_habituel_trajet"] == 10
    assert photo.loc["SP>RJ", "taux_retard_trajet"] == 0

    photo, _ = photographier_trajets(historique, "2017-04-01", min_commandes=30, lissage=0)
    assert photo.loc["SP>RJ", "taux_retard_trajet"] == pytest.approx(0.5)


def test_une_commande_de_mars_utilise_la_photo_du_1er_mars():
    table = pd.DataFrame({"date_achat": pd.to_datetime(["2017-03-28"]), "etat_vendeur": ["SP"],
                          "etat_client": ["RJ"], "delai_promis_jours": [12]})
    resultat = ajouter_variables_trajet(table, historique=_historique())
    # Les retards de mars ne doivent pas encore être visibles pour une commande achetée en mars.
    assert resultat.loc[0, "delai_habituel_trajet"] == 10
    assert resultat.loc[0, "marge_delai_jours"] == 2


def test_trajet_inconnu_prend_les_valeurs_globales():
    table = pd.DataFrame({"date_achat": pd.to_datetime(["2017-03-28"]), "etat_vendeur": ["AC"],
                          "etat_client": ["RR"], "delai_promis_jours": [20]})
    resultat = ajouter_variables_trajet(table, historique=_historique())
    assert resultat.loc[0, "delai_habituel_trajet"] == 10
    assert resultat[["delai_habituel_trajet", "taux_retard_trajet", "marge_delai_jours"]].notna().all(axis=None)


def test_marge():
    assert calculer_marge([20, 8], [12, 10]).tolist() == [8.0, -2.0]
