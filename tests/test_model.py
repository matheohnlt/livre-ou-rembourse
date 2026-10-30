"""Tests de la logique métier : coût attendu, décision d'éligibilité, plafond d'équité, bénéfice, segments."""
import numpy as np
import pandas as pd
import pytest

from backend import model as M
from backend.segmentation import nommer_segments


def test_cout_attendu_avec_la_marge():
    # 10 % de risque, 30 R$ d'indemnité, 30 % de marge : 0,1 × 30 × 1,3 = 3,9 R$.
    assert M.calculer_cout_attendu([0.10], [30.0], chargement=0.30)[0] == pytest.approx(3.9)


def test_on_refuse_seulement_quand_le_cout_depasse_le_prix():
    cout = np.array([1.0, 3.9, 4.0, 4.1, 9.0])
    proposee = M.decider_eligibilite(cout, seuil=4.0, region=["A"] * 5, part_refus_max=1.0)
    assert proposee.tolist() == [True, True, True, False, False]


def test_le_plafond_de_refus_par_region_est_respecte():
    # Région A : 10 commandes, toutes non rentables. Avec 20 % de refus au plus, on n'en refuse
    # que 2, et ce sont les PLUS risquées (coûts 10 et 9).
    cout = np.arange(1.0, 11.0) + 4.0  # de 5 à 14 R$, toutes au-dessus du prix de 4 R$
    proposee = M.decider_eligibilite(cout, seuil=4.0, region=["A"] * 10, part_refus_max=0.20)
    assert (~proposee).sum() == 2
    assert set(cout[~proposee]) == {13.0, 14.0}


def test_le_plafond_ne_touche_pas_une_region_sous_le_plafond():
    cout = np.array([1.0, 1.0, 1.0, 1.0, 9.0, 9.0])
    region = ["A", "A", "A", "A", "A", "B"]
    proposee = M.decider_eligibilite(cout, seuil=4.0, region=region, part_refus_max=0.20)
    # A : 1 refus sur 5 (20 %) -> gardé. B : 1 refus sur 1 (100 %) -> re-proposé.
    assert proposee.tolist() == [True, True, True, True, False, True]


def test_benefice_calcule_sur_les_seules_commandes_proposees():
    # 4 commandes, 2 proposées. Parmi elles, un sinistre de 20 R$. 50 % des clients achètent.
    resultat = M.evaluer_strategie(
        proposee=[True, True, False, False],
        sinistre=[1, 0, 1, 1],
        indemnite=[20.0, 20.0, 20.0, 20.0],
        prix=4.0,
        taux_souscription=0.5,
    )
    assert resultat["primes"] == pytest.approx(0.5 * 4.0 * 2)  # 4 R$
    assert resultat["sinistres"] == pytest.approx(0.5 * 20.0)  # 10 R$
    assert resultat["benefice"] == pytest.approx(-6.0)


def test_aucune_variable_interdite_dans_le_modele():
    # Équité et fuite : l'État, les coordonnées GPS et les dates de livraison sont exclus.
    interdites = {"etat_client", "etat_vendeur", "region_client", "lat_client", "lng_client",
                  "lat_vendeur", "lng_vendeur", "sinistre", "commande_id", "vendeur_id"}
    assert interdites.isdisjoint(M.VARIABLES)


def test_les_segments_ont_des_noms_distincts():
    # Portrait fictif de 5 segments : chaque règle doit désigner un segment différent.
    portrait = pd.DataFrame({
        "segment": [0, 1, 2, 3, 4],
        "part_meme_etat": [0.0, 1.0, 0.1, 0.3, 0.0],
        "nb_articles": [1.0, 1.0, 1.2, 3.8, 1.0],
        "poids_g": [600, 650, 6500, 2900, 500],
        "distance_km": [1400, 90, 570, 450, 540],
    })
    noms = nommer_segments(portrait)
    assert len(set(noms.values())) == 5
    assert noms[1].startswith("Le voisin") and noms[0].startswith("Le grand voyageur")
