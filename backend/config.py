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
DATE_DEBUT_VALIDATION = "2017-10-01"  # choix du modèle : appris de janvier à septembre 2017, jugé d'octobre à décembre 2017
DATE_DEBUT_TEST = "2018-01-01"  # entraînement final : 2017 ; test (regardé une seule fois) : janvier à août 2018
DATE_FIN = "2018-09-01"  # exclue
# Analyse de robustesse (retour du COMEX) : même chaîne, mais coupure plus tardive. L'apprentissage
# inclut la crise de février-mars 2018 (environ 67 % des commandes) et le test porte sur avril-août 2018.
# Le découpage principal ci-dessus ne change pas : voir `python -m backend.robustesse`.
DATE_DEBUT_VALIDATION_ROBUSTESSE = "2018-01-01"
DATE_DEBUT_TEST_ROBUSTESSE = "2018-04-01"

# --- Paramètres métier de la garantie (hypothèses de l'assureur, voir note de cadrage) ---
PRIX_GARANTIE = 4.0  # R$ : prix unique de la garantie, le même pour toutes les commandes proposées
BON_ACHAT = 15.0  # R$ offerts en cas de sinistre, en plus du remboursement des frais de port
CHARGEMENT = 0.30  # marge et frais de l'assureur : on propose si coût attendu x 1,3 <= prix
PART_REFUS_MAX_PAR_REGION = 0.20  # équité : au plus 20 % de refus dans chaque région

# Part des clients qui achètent la garantie quand elle leur est proposée. HYPOTHÈSE : non
# observable dans les données. Elle multiplie tous les bénéfices sans changer le classement
# des stratégies ; le simulateur Streamlit permet de la faire varier.
TAUX_SOUSCRIPTION = 0.20

# Baseline « règle métier » : refuser les commandes au-delà de cette distance (même plafond par région).
SEUIL_DISTANCE_REFUS_KM = 2000

# Bonus non supervisé : nombre de segments du K-means (choix expliqué dans docs/model_card.md).
NB_SEGMENTS = 5

# Régions du Brésil, pour la vérification d'équité (l'État n'est PAS une variable du modèle).
REGIONS = {
    "Norte": ("AC", "AP", "AM", "PA", "RO", "RR", "TO"),
    "Nordeste": ("AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"),
    "Centro-Oeste": ("DF", "GO", "MT", "MS"),
    "Sudeste": ("ES", "MG", "RJ", "SP"),
    "Sul": ("PR", "RS", "SC"),
}
