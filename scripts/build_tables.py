from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.config import DEP_TO_REGION, PROCESSED_DIR, TABLES_DIR, YEARS
from utils.io import load_stations


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    stations = load_stations(YEARS)
    stations["region"] = stations["departement"].map(DEP_TO_REGION).fillna("Other")
    stations.to_parquet(TABLES_DIR / "stations.parquet", index=False)
    dims = stations.set_index("station_id")[["departement", "region", "type_route"]]

    weekly_parts, station_year_parts = [], []
    for year in YEARS:
        px = pd.read_parquet(PROCESSED_DIR / f"prix_{year}.parquet")
        px["semaine"] = px["date"].dt.to_period("W-SUN").dt.start_time

        sw = (px.groupby(["station_id", "carburant", "semaine"], observed=True)["prix"]
                .mean().reset_index())
        sw = sw.join(dims, on="station_id")

        weekly_parts.append(
            sw.groupby(["semaine", "departement", "region", "type_route", "carburant"],
                       observed=True)["prix"]
              .agg(somme_prix="sum", n_stations="count").reset_index()
        )
        sy = (sw.groupby(["station_id", "carburant"], observed=True)["prix"]
                .agg(prix_moyen="mean", n_semaines="count").reset_index())
        sy["annee"] = year
        station_year_parts.append(sy)
        print(f"[{year}] {len(sw):,} station-week prices", flush=True)

    weekly = (pd.concat(weekly_parts)
                .groupby(["semaine", "departement", "region", "type_route", "carburant"],
                         observed=True)[["somme_prix", "n_stations"]]
                .sum().reset_index())
    weekly = weekly[weekly["semaine"] >= pd.Timestamp(f"{YEARS[0]}-01-01")]
    weekly.to_parquet(TABLES_DIR / "weekly.parquet", index=False)

    station_year = pd.concat(station_year_parts, ignore_index=True)
    station_year["prix_moyen"] = station_year["prix_moyen"].astype("float32")
    station_year.to_parquet(TABLES_DIR / "station_year.parquet", index=False)

    print(f"weekly: {len(weekly):,} rows | station_year: {len(station_year):,} rows")


if __name__ == "__main__":
    main()
