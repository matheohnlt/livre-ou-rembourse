"""Bonus non supervisé : K-means sur le profil logistique des commandes (distance, délai promis,
frais de port, poids, nombre d'articles, même État), pour décrire des « personas » de commandes.

Le sinistre ne sert PAS à former les groupes : on le regarde après, pour décrire chaque segment.
"""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
from sklearn.metrics import silhouette_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from backend.config import NB_SEGMENTS, SEED

VARIABLES_SEGMENTATION = ["distance_km", "delai_promis_jours", "frais_port", "poids_total_g", "nb_articles", "meme_etat"]
# Variables très asymétriques (quelques valeurs énormes) : passées au logarithme avant de standardiser.
VARIABLES_LOG = ["distance_km", "frais_port", "poids_total_g"]


def preparer_matrice(table: pd.DataFrame) -> pd.DataFrame:
    """Sélectionne les variables du portrait et applique log(1 + x) aux variables asymétriques."""
    matrice = table[VARIABLES_SEGMENTATION].astype(float).copy()
    for colonne in VARIABLES_LOG:
        matrice[colonne] = np.log1p(matrice[colonne])
    return matrice


def entrainer_segmentation(table: pd.DataFrame, nb_segments: int = NB_SEGMENTS):
    """Médiane pour les manquants, standardisation (le K-means repose sur des distances), K-means."""
    pipeline = make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        KMeans(n_clusters=nb_segments, n_init=10, random_state=SEED),
    )
    return pipeline.fit(preparer_matrice(table))


def attribuer_segments(segmentation, table: pd.DataFrame) -> np.ndarray:
    """Numéro de segment de chaque commande."""
    return segmentation.predict(preparer_matrice(table))


def comparer_nombres_de_segments(table: pd.DataFrame, valeurs_k=range(2, 9), taille_echantillon: int = 5000) -> pd.DataFrame:
    """Inertie (méthode du coude) et silhouette pour chaque k. La silhouette est calculée sur un
    échantillon, car elle compare les commandes deux à deux.
    """
    preparation = make_pipeline(SimpleImputer(strategy="median"), StandardScaler())
    matrice = preparation.fit_transform(preparer_matrice(table))
    echantillon = np.random.default_rng(SEED).choice(len(matrice), min(taille_echantillon, len(matrice)), replace=False)
    lignes = []
    for k in valeurs_k:
        kmeans = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit(matrice)
        lignes.append({"k": k, "inertie": float(kmeans.inertia_),
                       "silhouette": float(silhouette_score(matrice[echantillon], kmeans.labels_[echantillon]))})
    return pd.DataFrame(lignes)


def decrire_segments(table: pd.DataFrame, segments) -> pd.DataFrame:
    """Portrait de chaque segment : taille, valeurs médianes, taux de sinistre (regardé APRÈS)."""
    donnees = table.assign(segment=np.asarray(segments))
    resume = donnees.groupby("segment").agg(
        commandes=("segment", "size"),
        distance_km=("distance_km", "median"),
        delai_promis_jours=("delai_promis_jours", "median"),
        frais_port=("frais_port", "median"),
        poids_g=("poids_total_g", "median"),
        nb_articles=("nb_articles", "mean"),
        part_meme_etat=("meme_etat", "mean"),
        taux_sinistre=("sinistre", "mean"),
    ).reset_index()
    resume["part_commandes"] = resume["commandes"] / resume["commandes"].sum()
    return resume


def nommer_segments(resume: pd.DataFrame) -> dict:
    """Donne un nom métier à chaque segment, avec des règles fixes sur son portrait : les noms ne
    dépendent pas du numéro que le K-means a attribué au hasard.
    """
    restants = resume.set_index("segment")
    noms = {}
    regles = [
        ("Le voisin (même État)", "part_meme_etat"),
        ("Le gros panier (plusieurs articles)", "nb_articles"),
        ("Le colis lourd", "poids_g"),
        ("Le grand voyageur (très longue distance)", "distance_km"),
    ]
    for nom, colonne in regles:
        segment = restants[colonne].idxmax()
        noms[int(segment)] = nom
        restants = restants.drop(segment)
    for segment in restants.index:
        noms[int(segment)] = "Le petit colis entre États"
    return noms
