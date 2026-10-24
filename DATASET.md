# Dataset

## Source

- Name: Prix des carburants en France - Flux annuel (yearly fuel price archives)
- Publisher: French Ministry of the Economy (prix-carburants.gouv.fr)
- Portal page: https://www.data.gouv.fr/fr/datasets/prix-des-carburants-en-france-flux-annuel/
- Download page: https://www.prix-carburants.gouv.fr/rubrique/opendata/
- Yearly archives used: `https://donnees.roulez-eco.fr/opendata/annee/<year>` for 2019 to 2025
- License: Licence Ouverte / Open Licence v2.0 (Etalab)

Every filling station in France must report its prices by law. Each yearly archive is a zipped XML file (20 to 30 MB zipped, about 330 MB unzipped) with one entry per station: postcode, city, coordinates, road or motorway, services, and every price update for each fuel.

## What is included in this folder

The raw archives (186 MB in total) are not included. `scripts/download_data.py` downloads them again.

The app only needs the pre-aggregated tables, which are included (5 MB):

| File | Content |
|---|---|
| `data/processed/tables/weekly.parquet` | week × département × station type × fuel: sum of prices and number of stations |
| `data/processed/tables/station_year.parquet` | yearly average price per station and fuel |
| `data/processed/tables/stations.parquet` | station register: coordinates, postcode, city, département, region, station type |
| `data/processed/quality_report.json` | rows removed by each cleaning rule, per year |

## Other data

- Département outlines: `assets/departements.geojson`, simplified version from https://github.com/gregoiredavid/france-geojson (derived from IGN Admin Express, Licence Ouverte)
