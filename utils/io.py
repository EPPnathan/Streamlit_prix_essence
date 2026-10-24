from __future__ import annotations

import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import requests

from utils.config import ANNUAL_URL, DEPARTEMENTS_GEOJSON, PROCESSED_DIR, RAW_DIR, TABLES_DIR


def download_year(year: int, force: bool = False) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"PrixCarburants_annuel_{year}.zip"
    if path.exists() and not force:
        return path
    tmp = path.with_suffix(".part")
    with requests.get(ANNUAL_URL.format(year=year), stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    tmp.replace(path)
    return path


def _to_float(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except ValueError:
        return None


def parse_year(zip_path) -> tuple[pd.DataFrame, pd.DataFrame]:
    stations, prices = [], []
    with zipfile.ZipFile(zip_path) as zf:
        xml_name = next(n for n in zf.namelist() if n.endswith(".xml"))
        with zf.open(xml_name) as fh:
            for _, elem in ET.iterparse(fh, events=("end",)):
                if elem.tag != "pdv":
                    continue
                pdv_id = int(elem.get("id"))
                stations.append({
                    "station_id": pdv_id,
                    "latitude": _to_float(elem.get("latitude")),
                    "longitude": _to_float(elem.get("longitude")),
                    "cp": elem.get("cp"),
                    "pop": elem.get("pop"),
                    "adresse": elem.findtext("adresse"),
                    "ville": elem.findtext("ville"),
                    "services": "|".join(s.text or "" for s in elem.iter("service")),
                })
                for p in elem.iter("prix"):
                    prices.append((pdv_id, p.get("nom"), p.get("maj"), p.get("valeur")))
                elem.clear()

    df_st = pd.DataFrame(stations)
    df_px = pd.DataFrame(prices, columns=["station_id", "carburant", "date", "prix"])
    return df_st, df_px


def save_year(year: int, df_st: pd.DataFrame, df_px: pd.DataFrame) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df_st.to_parquet(PROCESSED_DIR / f"stations_{year}.parquet", index=False)
    df_px.to_parquet(PROCESSED_DIR / f"prix_{year}.parquet", index=False)


def load_tables() -> dict:
    tables = {name: pd.read_parquet(TABLES_DIR / f"{name}.parquet")
              for name in ("weekly", "station_year", "stations")}
    report = json.loads((PROCESSED_DIR / "quality_report.json").read_text(encoding="utf-8"))
    tables["quality"] = (pd.DataFrame(report).T.rename_axis("annee")
                           .reset_index().sort_values("annee"))
    tables["geo"] = json.loads(DEPARTEMENTS_GEOJSON.read_text(encoding="utf-8"))
    tables["dep_names"] = pd.DataFrame(
        [f["properties"] for f in tables["geo"]["features"]]
    ).rename(columns={"code": "departement"})
    return tables


def load_prices(years: list[int]) -> pd.DataFrame:
    return pd.concat(
        (pd.read_parquet(PROCESSED_DIR / f"prix_{y}.parquet") for y in years),
        ignore_index=True,
    )


def load_stations(years: list[int]) -> pd.DataFrame:
    df = pd.concat(
        (pd.read_parquet(PROCESSED_DIR / f"stations_{y}.parquet").assign(annee=y) for y in years),
        ignore_index=True,
    )
    return df.sort_values("annee").drop_duplicates("station_id", keep="last")
