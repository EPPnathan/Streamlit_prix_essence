from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

YEARS = list(range(2019, 2026))

ANNUAL_URL = "https://donnees.roulez-eco.fr/opendata/annee/{year}"

SOURCE = {
    "titre": "Prix des carburants en France - Flux annuel",
    "producteur": "French Ministry of the Economy (prix-carburants.gouv.fr)",
    "portail": "https://www.data.gouv.fr/fr/datasets/prix-des-carburants-en-france-flux-annuel/",
    "telechargement": "https://www.prix-carburants.gouv.fr/rubrique/opendata/",
    "licence": "Licence Ouverte / Open Licence v2.0 (Etalab)",
}

PROFILE = {
    "name": "Nathan Gazin",
    "program": "Data Engineering",
    "year": "2026",
    "email": "nathan.gazin@efrei.net",
    "linkedin": "https://www.linkedin.com/in/nathan-gazin/",
    "course": "Data Analysis & Visualization",
    "professor": "Mano Mathew",
    "professor_linkedin": "https://www.linkedin.com/in/manomathew/",
}
LOGO_PATH = ROOT / "assets" / "efrei_logo.svg"

TABLES_DIR = PROCESSED_DIR / "tables"
DEPARTEMENTS_GEOJSON = ROOT / "assets" / "departements.geojson"

FUELS = ["Gazole", "SP95", "E10", "SP98", "E85", "GPLc"]
FUEL_LABELS = {"Gazole": "Diesel", "SP95": "SP95", "E10": "E10", "SP98": "SP98",
               "E85": "E85", "GPLc": "LPG"}

EVENTS = [
    ("2020-03-17", "1st lockdown"),
    ("2022-02-24", "Invasion of Ukraine"),
]
PERIODS = [
    ("2022-04-01", "2022-12-31", "Fuel rebate"),
]
REMISE_STEPS = [
    ("2022-04-01", "2022-08-31", "−18 c€"),
    ("2022-09-01", "2022-11-15", "−30 c€"),
    ("2022-11-16", "2022-12-31", "−10 c€"),
]

METRO_BBOX = {"lat": (41.0, 51.5), "lon": (-5.5, 10.0)}

_REGIONS = {
    "Auvergne-Rhône-Alpes": "01 03 07 15 26 38 42 43 63 69 73 74",
    "Bourgogne-Franche-Comté": "21 25 39 58 70 71 89 90",
    "Brittany": "22 29 35 56",
    "Centre-Val de Loire": "18 28 36 37 41 45",
    "Corsica": "2A 2B",
    "Grand Est": "08 10 51 52 54 55 57 67 68 88",
    "Hauts-de-France": "02 59 60 62 80",
    "Île-de-France": "75 77 78 91 92 93 94 95",
    "Normandy": "14 27 50 61 76",
    "Nouvelle-Aquitaine": "16 17 19 23 24 33 40 47 64 79 86 87",
    "Occitanie": "09 11 12 30 31 32 34 46 48 65 66 81 82",
    "Pays de la Loire": "44 49 53 72 85",
    "Provence-Alpes-Côte d'Azur": "04 05 06 13 83 84",
    "Overseas": "971 972 973 974 976",
}
DEP_TO_REGION = {dep: reg for reg, deps in _REGIONS.items() for dep in deps.split()}
