"""Variables « trajet » : ce que l'on sait, au moment du paiement, des livraisons passées sur le
même trajet (État du vendeur -> État du client).

Règle anti-fuite : pour une commande achetée pendant le mois M, on n'utilise qu'une
photographie prise le 1er jour du mois M :
- délai réel habituel : médiane des commandes LIVRÉES avant le 1er jour de M ;
- taux de retard : commandes dont la date PROMISE est passée avant le 1er jour de M (leur issue
  est alors connue : livrées à temps, ou en retard).

Trois variables :
- `delai_habituel_trajet` : délai réel médian (jours) entre l'achat et la livraison ;
- `marge_delai_jours` : délai promis au client moins ce délai habituel. Une marge faible ou
  négative signifie qu'Olist promet moins que ce que le trajet prend d'habitude ;
- `taux_retard_trajet` : taux de retard passé du trajet, lissé vers le taux global pour les
  trajets peu fréquentés.

Équité : ces variables résument l'historique d'un couple d'États. Elles renseignent donc
indirectement sur la région, comme la distance. La règle de 20 % de refus par région reste
appliquée à la décision (voir backend/model.py).
"""
import sqlite3
from contextlib import closing
from pathlib import Path

import numpy as np
import pandas as pd

from backend.config import BASE, LISSAGE_TAUX_TRAJET, MIN_COMMANDES_TRAJET
from backend.data import lire_requete

VARIABLES_TRAJET = ["marge_delai_jours", "delai_habituel_trajet", "taux_retard_trajet"]


def lire_historique(base: Path = BASE) -> pd.DataFrame:
    """Toutes les commandes expédiées, avec leur issue (retard ou non) et leur délai réel."""
    with closing(sqlite3.connect(base)) as con:
        historique = pd.read_sql(lire_requete("04_historique_trajets.sql"), con)
    for colonne in ("jour_achat", "jour_promis", "jour_livre"):
        historique[colonne] = pd.to_datetime(historique[colonne])
    # Même définition que la cible : livrée après la date promise (au jour près) ou jamais livrée.
    historique["sinistre"] = (historique["jour_livre"].isna()
                              | (historique["jour_livre"] > historique["jour_promis"])).astype(int)
    historique["delai_reel"] = (historique["jour_livre"] - historique["jour_achat"]).dt.days
    historique["trajet"] = nommer_trajet(historique["etat_vendeur"], historique["etat_client"])
    return historique


def nommer_trajet(etat_vendeur, etat_client) -> pd.Series:
    return pd.Series(etat_vendeur, dtype="string").str.cat(pd.Series(etat_client, dtype="string").values, sep=">")


def photographier_trajets(historique: pd.DataFrame, date_photo, min_commandes: int = MIN_COMMANDES_TRAJET,
                          lissage: float = LISSAGE_TAUX_TRAJET) -> tuple[pd.DataFrame, dict]:
    """Statistiques par trajet connues au début du jour `date_photo`.

    Renvoie (table par trajet, valeurs par défaut pour un trajet inconnu).
    """
    date_photo = pd.Timestamp(date_photo)
    livrees = historique[historique["jour_livre"] < date_photo]
    echues = historique[historique["jour_promis"] < date_photo]  # issue connue à date_photo
    delai_global = float(livrees["delai_reel"].median())
    taux_global = float(echues["sinistre"].mean())

    delai = livrees.groupby("trajet")["delai_reel"].agg(["median", "count"])
    retard = echues.groupby("trajet")["sinistre"].agg(["sum", "count"])
    trajets = delai.index.union(retard.index)
    photo = pd.DataFrame(index=trajets)
    # Trop peu de livraisons sur le trajet : la médiane n'est pas fiable, on prend la médiane globale.
    photo["delai_habituel_trajet"] = delai["median"].where(delai["count"] >= min_commandes).reindex(trajets)
    photo["delai_habituel_trajet"] = photo["delai_habituel_trajet"].fillna(delai_global)
    # Lissage : un trajet avec peu de commandes est rapproché du taux global.
    somme, nombre = retard["sum"].reindex(trajets).fillna(0), retard["count"].reindex(trajets).fillna(0)
    photo["taux_retard_trajet"] = (somme + lissage * taux_global) / (nombre + lissage)
    defaut = {"delai_habituel_trajet": delai_global, "taux_retard_trajet": taux_global}
    return photo, defaut


def ajouter_variables_trajet(table: pd.DataFrame, base: Path = BASE, historique: pd.DataFrame | None = None) -> pd.DataFrame:
    """Ajoute les trois variables trajet à la table d'analyse, avec une photographie par mois d'achat."""
    if historique is None:
        historique = lire_historique(base)
    table = table.copy()
    mois = table["date_achat"].dt.to_period("M").dt.to_timestamp()
    trajet = nommer_trajet(table["etat_vendeur"], table["etat_client"]).to_numpy()
    for colonne in ("delai_habituel_trajet", "taux_retard_trajet"):
        table[colonne] = np.nan
    for debut_mois in mois.unique():
        lignes = (mois == debut_mois).to_numpy()
        photo, defaut = photographier_trajets(historique, debut_mois)
        for colonne in ("delai_habituel_trajet", "taux_retard_trajet"):
            valeurs = pd.Series(trajet[lignes]).map(photo[colonne]).fillna(defaut[colonne])
            table.loc[lignes, colonne] = valeurs.to_numpy()
    table["marge_delai_jours"] = calculer_marge(table["delai_promis_jours"], table["delai_habituel_trajet"])
    return table


def calculer_marge(delai_promis_jours, delai_habituel_trajet):
    """Marge du délai promis : délai annoncé au client moins le délai habituel du trajet."""
    return np.asarray(delai_promis_jours, dtype=float) - np.asarray(delai_habituel_trajet, dtype=float)
