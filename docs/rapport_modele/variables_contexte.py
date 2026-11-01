"""Nouvelles variables « de contexte », calculées SANS FUITE : pour une commande payée le jour J,
on n'utilise que des issues de commandes déjà connues au début du jour J.

1. taux_retard_30j : part des commandes en retard parmi celles dont la date de livraison
   PROMISE tombe dans les 30 jours avant J (de J-30 à J-1). Pour ces commandes, l'issue est
   connue au jour J : soit elles ont été livrées au plus tard à la date promise, soit elles sont
   en retard. Pas de biais de sélection (on ne filtre pas sur « déjà livrée »).

2. delai_habituel_trajet / marge_delai_jours : délai réel médian (achat -> livraison) sur le
   même trajet (État du vendeur -> État du client), calculé sur les commandes LIVRÉES avant le
   1er jour du mois d'achat (photographie mensuelle). Marge = délai promis - délai habituel.

3. taux_retard_trajet : taux de retard historique du même trajet, parmi les commandes dont la
   date promise est passée avant le 1er jour du mois d'achat, lissé vers le taux global
   (a priori de 50 commandes) pour les trajets peu fréquentés.
"""
import sqlite3
from contextlib import closing

import numpy as np
import pandas as pd

from backend.config import BASE

MIN_COMMANDES_TRAJET = 30
LISSAGE = 50
FENETRE_JOURS = 30


def lire_historique(base=BASE) -> pd.DataFrame:
    """Toutes les commandes expédiées (même filtre que la table d'analyse), toutes périodes."""
    requete = """
        SELECT c.order_id AS commande_id,
               date(c.order_purchase_timestamp) AS jour_achat,
               date(c.order_estimated_delivery_date) AS jour_promis,
               date(c.order_delivered_customer_date) AS jour_livre,
               v.seller_state AS etat_vendeur, cl.customer_state AS etat_client
        FROM commandes c
        JOIN articles a ON a.order_id = c.order_id AND a.order_item_id = 1
        JOIN vendeurs v ON v.seller_id = a.seller_id
        JOIN clients cl ON cl.customer_id = c.customer_id
        WHERE c.order_status IN ('delivered', 'shipped')
          AND NOT (c.order_status = 'delivered' AND c.order_delivered_customer_date IS NULL)
    """
    with closing(sqlite3.connect(base)) as con:
        h = pd.read_sql(requete, con)
    for col in ("jour_achat", "jour_promis", "jour_livre"):
        h[col] = pd.to_datetime(h[col])
    h["sinistre"] = (h["jour_livre"].isna() | (h["jour_livre"] > h["jour_promis"])).astype(int)
    h["delai_reel"] = (h["jour_livre"] - h["jour_achat"]).dt.days
    h["trajet"] = h["etat_vendeur"] + ">" + h["etat_client"]
    return h


def taux_retard_recent(historique: pd.DataFrame, jours: pd.Series) -> pd.Series:
    """Pour chaque jour J : taux de retard des commandes dont la date promise est dans [J-30, J-1]."""
    par_jour = historique.groupby("jour_promis")["sinistre"].agg(["sum", "count"])
    calendrier = pd.date_range(par_jour.index.min(), jours.max() + pd.Timedelta(days=1), freq="D")
    par_jour = par_jour.reindex(calendrier, fill_value=0)
    # Fenêtre glissante qui SE TERMINE la veille : shift(1) exclut le jour J lui-même.
    somme = par_jour["sum"].rolling(FENETRE_JOURS, min_periods=1).sum().shift(1)
    nombre = par_jour["count"].rolling(FENETRE_JOURS, min_periods=1).sum().shift(1)
    taux = (somme / nombre).where(nombre >= 100)
    return jours.map(taux)


def photos_mensuelles_trajets(historique: pd.DataFrame, mois: list) -> pd.DataFrame:
    """Pour chaque mois M : délai médian et taux de retard par trajet, connus au 1er jour de M."""
    lignes = []
    for debut in mois:
        livrees = historique[historique["jour_livre"] < debut]
        echues = historique[historique["jour_promis"] < debut]  # issue connue au 1er du mois
        taux_global = echues["sinistre"].mean()
        delai = livrees.groupby("trajet")["delai_reel"].agg(["median", "count"])
        delai_global = livrees["delai_reel"].median()
        retard = echues.groupby("trajet")["sinistre"].agg(["sum", "count"])
        photo = pd.DataFrame({"trajet": sorted(set(delai.index) | set(retard.index))}).set_index("trajet")
        photo["delai_habituel_trajet"] = delai["median"].where(delai["count"] >= MIN_COMMANDES_TRAJET)
        photo["delai_habituel_trajet"] = photo["delai_habituel_trajet"].fillna(delai_global)
        photo["taux_retard_trajet"] = (
            (retard["sum"].reindex(photo.index).fillna(0) + LISSAGE * taux_global)
            / (retard["count"].reindex(photo.index).fillna(0) + LISSAGE))
        photo["mois"] = debut
        lignes.append(photo.reset_index())
        lignes.append(pd.DataFrame({"trajet": ["__defaut__"], "delai_habituel_trajet": [delai_global],
                                    "taux_retard_trajet": [taux_global], "mois": [debut]}))
    return pd.concat(lignes, ignore_index=True)


def ajouter_variables_contexte(table: pd.DataFrame, base=BASE) -> pd.DataFrame:
    historique = lire_historique(base)
    table = table.copy()
    jour = table["date_achat"].dt.normalize()
    table["taux_retard_30j"] = taux_retard_recent(historique, jour).to_numpy()

    mois = table["date_achat"].dt.to_period("M").dt.to_timestamp()
    photos = photos_mensuelles_trajets(historique, sorted(mois.unique()))
    trajet = table["etat_vendeur"] + ">" + table["etat_client"]
    cle = pd.DataFrame({"trajet": trajet.to_numpy(), "mois": mois.to_numpy()})
    fusion = cle.merge(photos, on=["trajet", "mois"], how="left")
    defaut = cle.merge(photos[photos["trajet"] == "__defaut__"].drop(columns="trajet"), on="mois", how="left")
    for col in ("delai_habituel_trajet", "taux_retard_trajet"):
        table[col] = fusion[col].fillna(defaut[col]).to_numpy()
    table["marge_delai_jours"] = table["delai_promis_jours"] - table["delai_habituel_trajet"]
    return table
