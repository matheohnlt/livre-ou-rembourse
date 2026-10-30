"""Réglages du projet « Livré ou Remboursé » : chemins, seed, périodes et paramètres métier.

Tout réglage vit ici et nulle part ailleurs : un seuil ou un prix écrit en dur dans le code
est une erreur.
"""
from pathlib import Path

# --- Chemins (toujours relatifs à la racine du dépôt) ---------------------------------
RACINE = Path(__file__).resolve().parents[1]
ARCHIVE_BRUTE = RACINE / "data" / "raw" / "olist.zip"  # archive Kaggle, jamais modifiée
BASE = RACINE / "data" / "olist.db"  # base SQLite reconstruite par backend.data
DOSSIER_SQL = RACINE / "backend" / "sql"
DOSSIER_MODELES = RACINE / "models"
FICHIER_MODELE = DOSSIER_MODELES / "modele.joblib"
FICHIER_METRIQUES = DOSSIER_MODELES / "metriques.json"

SEED = 42

# --- Périodes (split temporel) ---------------------------------------------------------
# Avant 2017 : trop peu de commandes. Après août 2018 : l'issue des commandes n'est pas
# encore connue dans les données (fin des données le 17/10/2018).
DATE_DEBUT = "2017-01-01"
DATE_DEBUT_TEST = "2018-01-01"  # entraînement : 2017 ; test : janvier à août 2018
DATE_FIN = "2018-09-01"  # exclue

# --- Paramètres métier de la garantie (hypothèses de l'assureur, voir note de cadrage) ---
BON_ACHAT = 15.0  # R$ offerts en cas de sinistre, en plus du remboursement des frais de port
PRIX_UNIQUE = 4.0  # R$ : baseline, le même prix pour toutes les commandes
NIVEAUX_PRIX = (2.0, 4.0, 8.0)  # R$ : les 3 prix affichés selon le risque
CHARGEMENT = 0.30  # marge et frais de l'assureur ajoutés au coût attendu d'un sinistre
