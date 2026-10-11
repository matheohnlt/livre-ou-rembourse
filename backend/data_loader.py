from pathlib import Path
import warnings
import xml.etree.ElementTree as ET
import zipfile
import duckdb
import requests

warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")

DATA_DIR = Path("data/raw")
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path("data/database.duckdb")

# 1. Connexion DuckDB et création des tables relationnelles
con = duckdb.connect(str(DB_PATH))

con.execute("""
CREATE TABLE IF NOT EXISTS stations (
    id_station VARCHAR PRIMARY KEY,
    latitude DOUBLE,
    longitude DOUBLE,
    code_postal VARCHAR,
    type_route VARCHAR,
    adresse VARCHAR,
    ville VARCHAR
);

CREATE TABLE IF NOT EXISTS prix_carburants (
    id_station VARCHAR,
    carburant_nom VARCHAR,
    valeur_prix DOUBLE,
    date_maj TIMESTAMP
);
""")


def telecharger_et_extraire(url: str, nom_fichier_zip: str) -> Path:
    zip_dest = DATA_DIR / nom_fichier_zip
    print(f"Téléchargement : {url}")
    rep = requests.get(url, stream=True, timeout=60)
    rep.raise_for_status()

    with open(zip_dest, "wb") as f:
        for chunk in rep.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)

    with zipfile.ZipFile(zip_dest, "r") as z:
        z.extractall(DATA_DIR)
        xml_name = z.namelist()[0]

    return DATA_DIR / xml_name


def parser_et_inserer_xml(fichier_xml: Path):
    print(f"Insertion des données depuis {fichier_xml.name}...")
    stations_batch = []
    prix_batch = []

    context = ET.iterparse(str(fichier_xml), events=("end",))

    for _, elem in context:
        if elem.tag == "pdv":
            id_station = elem.get("id")
            lat = (
                float(elem.get("latitude")) / 100000
                if elem.get("latitude")
                else None
            )
            lon = (
                float(elem.get("longitude")) / 100000
                if elem.get("longitude")
                else None
            )
            cp = elem.get("cp")
            pop = elem.get("pop")

            adr = (
                elem.findtext("adresse") if elem.find("adresse") is not None else ""
            )
            ville = (
                elem.findtext("ville") if elem.find("ville") is not None else ""
            )

            stations_batch.append((id_station, lat, lon, cp, pop, adr, ville))

            for prix in elem.findall("prix"):
                nom = prix.get("nom")
                valeur = float(prix.get("valeur")) if prix.get("valeur") else None
                maj = prix.get("maj")
                if valeur and maj:
                    prix_batch.append((id_station, nom, valeur, maj))

            if len(stations_batch) >= 5000:
                con.executemany(
                    "INSERT OR IGNORE INTO stations VALUES (?, ?, ?, ?, ?, ?, ?)",
                    stations_batch,
                )
                con.executemany(
                    "INSERT INTO prix_carburants VALUES (?, ?, ?, ?)", prix_batch
                )
                stations_batch.clear()
                prix_batch.clear()

            elem.clear()

    if stations_batch:
        con.executemany(
        "INSERT OR IGNORE INTO stations (id_station, latitude, longitude, code_postal, type_route, adresse, ville) VALUES (?, ?, ?, ?, ?, ?, ?)",
    stations_batch,
                        )
    if prix_batch:
        con.executemany(
        "INSERT INTO prix_carburants (id_station, carburant_nom, valeur_prix, date_maj) VALUES (?, ?, ?, ?)",
    prix_batch,
                        )

    print(f"Chargement terminé pour {fichier_xml.name}")


# 2. Boucle sur les archives annuelles souhaitées
annees = ["2023", "2024", "2025"]

for annee in annees:
    url = f"https://donnees.roulez-eco.fr/opendata/annee/{annee}"
    fichier_xml = telecharger_et_extraire(url, f"carburants_{annee}.zip")
    parser_et_inserer_xml(fichier_xml)

# 3. Récupération du flux instantané actuel
url_inst = "https://donnees.roulez-eco.fr/opendata/instantane"
xml_inst = telecharger_et_extraire(url_inst, "carburants_instantane.zip")
parser_et_inserer_xml(xml_inst)

print("Base DuckDB totalement synchronisée.")