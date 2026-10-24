# Fuel prices in France, 2019-2025

Individual project, EFREI 2026 (Data Analysis & Visualization, Prof. Mano Mathew), by Nathan Gazin (Data Engineering, nathan.gazin@efrei.net).

A Streamlit app that tells one story: French pump prices spiked in 2022 and have come down since, but the gaps between départements and between road and motorway stations have grown since 2019.

- Deployed app: (link to add after deployment)
- Demo video: (link to add)
- Dataset and links: see `DATASET.md`

## Run

Tested with Python 3.12 in a fresh virtual environment. The pre-aggregated tables (5 MB) are already in `data/processed/tables/`, so the app runs straight away:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Push this folder to a public GitHub repository, including `data/processed/` (5 MB).
2. On https://share.streamlit.io, choose "Create app", select the repository, set the main file to `app.py` and Python to 3.12.
3. Deploy, then paste the app URL at the top of this README.

To rebuild everything from the source (about 6 minutes):

```bash
python scripts/download_data.py
python scripts/build_tables.py
```

## Data

- Dataset: Prix des carburants en France, flux annuel (yearly fuel price archives): https://www.data.gouv.fr/fr/datasets/prix-des-carburants-en-france-flux-annuel/
- License: Licence Ouverte / Open Licence v2.0 (Etalab)
- Period: 2019 to 2025, about 32 million price records from 14,000 stations
- Département outlines: `assets/departements.geojson`, from [france-geojson](https://github.com/gregoiredavid/france-geojson) (derived from IGN Admin Express, Licence Ouverte)

## Cleaning

- Coordinates divided by 100,000 (PTV_GEODECIMAL to WGS84)
- Prices stored in thousandths of a euro (older archives) converted to €/L
- Removed: invalid dates or prices, unknown fuels, prices outside 0.30 to 4.00 €/L, and duplicates (same station, fuel and timestamp)
- Département derived from the postcode (2A/2B for Corsica, three digits overseas)
- Station register checked for missing, swapped and out-of-range coordinates
- Each station's price is averaged per week before averaging across stations, so every station counts the same however often it updates its prices

## The app

The sidebar shows the student card. The page then runs through:

1. The data: where it comes from, the processing steps and the errors found
2. The shock: weekly price by fuel, with an index toggle (first week = 100)
3. The shield: close-up on the 2022 fuel rebate
4. The decline: average price per year
5. The widening gaps: gap trends, region heatmap, département map, ranking, station map, road vs motorway
6. Takeaways and limitations
7. The data in detail: three tabs with CSV downloads

Every chart has a one-line finding above it and a "How to read it" note below. All figures are computed from the data. The app currently shows diesel for all of France.

## Structure

```
app.py                    the Streamlit page
utils/config.py           paths, years, source, student card, events, regions, labels
utils/io.py               download, streaming XML parser, loading
utils/prep.py             cleaning and weighted aggregations
utils/viz.py              Plotly charts in a shared style
scripts/download_data.py  import pipeline
scripts/build_tables.py   pre-aggregation
```
