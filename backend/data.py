"""Accès aux données : archive Kaggle -> SQLite (schéma en SQL) -> table d'analyse (en SQL).

Commande : `python -m backend.data` reconstruit la base et affiche un résumé.
"""
import sqlite3
import zipfile
from contextlib import closing
from pathlib import Path

import numpy as np
import pandas as pd

from backend.config import ARCHIVE_BRUTE, BASE, DATE_DEBUT, DATE_FIN, DOSSIER_SQL

# Fichier CSV de l'archive -> table SQLite créée par 01_creation_tables.sql
TABLES = {
    "olist_orders_dataset.csv": "commandes",
    "olist_order_items_dataset.csv": "articles",
    "olist_products_dataset.csv": "produits",
    "product_category_name_translation.csv": "categories",
    "olist_sellers_dataset.csv": "vendeurs",
    "olist_customers_dataset.csv": "clients",
    "olist_geolocation_dataset.csv": "geolocalisation",
    "olist_order_payments_dataset.csv": "paiements",
    "olist_order_reviews_dataset.csv": "avis",
}

# Les codes postaux commencent parfois par 0 : on les lit comme du texte pour les garder.
COLONNES_TEXTE = {
    "seller_zip_code_prefix": str,
    "customer_zip_code_prefix": str,
    "geolocation_zip_code_prefix": str,
}

RAYON_TERRE_KM = 6371.0


def lire_requete(nom_fichier: str) -> str:
    """Renvoie le texte d'une requête versionnée dans backend/sql/."""
    return (DOSSIER_SQL / nom_fichier).read_text(encoding="utf-8")


def charger_archive_dans_sqlite(archive: Path = ARCHIVE_BRUTE, base: Path = BASE) -> dict:
    """Crée les tables (en SQL) et y charge les 9 CSV de l'archive, sans la décompresser.

    Renvoie le nombre de lignes chargées par table.
    """
    if not archive.exists():
        raise FileNotFoundError(f"Archive introuvable : {archive}. Voir le README, partie Données.")
    base.parent.mkdir(parents=True, exist_ok=True)
    nb_lignes = {}
    with closing(sqlite3.connect(base)) as con, zipfile.ZipFile(archive) as zip_brut:
        con.executescript(lire_requete("01_creation_tables.sql"))
        for fichier_csv, table in TABLES.items():
            # utf-8-sig : le fichier des catégories commence par un caractère invisible (BOM).
            with zip_brut.open(fichier_csv) as flux:
                donnees = pd.read_csv(flux, dtype=COLONNES_TEXTE, encoding="utf-8-sig")
            donnees.to_sql(table, con, if_exists="append", index=False)
            nb_lignes[table] = len(donnees)
        con.commit()
    return nb_lignes


def calculer_distance_km(lat1, lng1, lat2, lng2):
    """Distance à vol d'oiseau (formule de haversine), en km. Accepte des nombres ou des colonnes."""
    lat1, lng1, lat2, lng2 = (np.radians(x) for x in (lat1, lng1, lat2, lng2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lng2 - lng1) / 2) ** 2
    return 2 * RAYON_TERRE_KM * np.arcsin(np.sqrt(a))


def lire_table_analyse(base: Path = BASE, date_debut: str = DATE_DEBUT, date_fin: str = DATE_FIN) -> pd.DataFrame:
    """Construit la table d'analyse (une ligne par commande) avec la requête SQL versionnée,
    puis ajoute la distance vendeur -> client, que SQLite ne sait pas calculer.
    """
    if not base.exists():
        raise FileNotFoundError(f"Base introuvable : {base}. Lancer d'abord : python -m backend.data")
    with closing(sqlite3.connect(base)) as con:
        table = pd.read_sql(
            lire_requete("02_table_analyse.sql"),
            con,
            params={"date_debut": date_debut, "date_fin": date_fin},
        )
    table["date_achat"] = pd.to_datetime(table["date_achat"])
    table["distance_km"] = calculer_distance_km(
        table["lat_vendeur"], table["lng_vendeur"], table["lat_client"], table["lng_client"]
    )
    return table


def lire_derniers_avis(base: Path = BASE) -> pd.DataFrame:
    """La note la plus récente de chaque commande (exploration seulement, jamais dans le modèle)."""
    if not base.exists():
        raise FileNotFoundError(f"Base introuvable : {base}. Lancer d'abord : python -m backend.data")
    with closing(sqlite3.connect(base)) as con:
        return pd.read_sql(lire_requete("03_dernier_avis.sql"), con)


if __name__ == "__main__":
    lignes = charger_archive_dans_sqlite()
    for nom_table, nombre in lignes.items():
        print(f"{nom_table:16} {nombre:>9,} lignes".replace(",", " "))
    analyse = lire_table_analyse()
    print(f"\nTable d'analyse : {len(analyse):,} commandes, {analyse.shape[1]} colonnes".replace(",", " "))
    print(f"Taux de sinistre : {analyse['sinistre'].mean():.1%}")
