from __future__ import annotations

import pandas as pd

from utils.config import FUELS


def departement_from_cp(cp: pd.Series) -> pd.Series:
    cp = cp.astype("string").str.strip().str.zfill(5)
    dep = cp.str[:2]
    dep = dep.mask(cp.str[:2] == "97", cp.str[:3])
    corse = cp.str[:2] == "20"
    dep = dep.mask(corse & (cp.str[:3].isin(["200", "201"])), "2A")
    dep = dep.mask(corse & ~(cp.str[:3].isin(["200", "201"])), "2B")
    return dep


def clean_stations(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["latitude"] = df["latitude"] / 100_000
    df["longitude"] = df["longitude"] / 100_000
    df["departement"] = departement_from_cp(df["cp"])
    df["type_route"] = df["pop"].map({"R": "Road", "A": "Motorway"}).fillna("Unknown")
    df["ville"] = df["ville"].str.strip().str.upper()
    return df.drop(columns=["pop"])


def clean_prices(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    report = {"lignes_brutes": len(df)}
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["prix"] = pd.to_numeric(df["prix"], errors="coerce")
    df.loc[df["prix"] > 100, "prix"] = df["prix"] / 1000

    report["date_ou_prix_invalide"] = int(df[["date", "prix"]].isna().any(axis=1).sum())
    df = df.dropna(subset=["date", "prix"])

    report["carburant_inconnu"] = int((~df["carburant"].isin(FUELS)).sum())
    df = df[df["carburant"].isin(FUELS)]

    aberrant = ~df["prix"].between(0.3, 4.0)
    report["prix_aberrant"] = int(aberrant.sum())
    df = df[~aberrant]

    dup = df.duplicated(["station_id", "carburant", "date"])
    report["doublons"] = int(dup.sum())
    df = df[~dup]

    report["lignes_finales"] = len(df)
    df["carburant"] = df["carburant"].astype("category")
    df["prix"] = df["prix"].astype("float32")
    return df.reset_index(drop=True), report


def coord_status(st: pd.DataFrame, bbox: dict) -> pd.Series:
    lat, lon = st["latitude"], st["longitude"]
    in_lat, in_lon = lat.between(*bbox["lat"]), lon.between(*bbox["lon"])
    overseas = st["departement"].str.len() == 3
    status = pd.Series("Valid", index=st.index)
    status[~overseas & ~(in_lat & in_lon)] = "Outside France"
    status[~overseas & lat.between(*bbox["lon"]) & lon.between(*bbox["lat"])] = "Latitude/longitude swapped"
    status[(lat == 0) & (lon == 0)] = "Coordinates (0, 0)"
    status[lat.isna() | lon.isna()] = "Missing"
    status[overseas & status.eq("Valid")] = "Overseas (not checked)"
    return status


def filter_weekly(weekly: pd.DataFrame, start, end, regions=None, route=None,
                  fuels=None) -> pd.DataFrame:
    m = weekly["semaine"].between(pd.Timestamp(start), pd.Timestamp(end))
    if regions:
        m &= weekly["region"].isin(regions)
    if route and route != "All":
        m &= weekly["type_route"] == route
    if fuels:
        m &= weekly["carburant"].isin(fuels)
    return weekly[m]


def weighted_mean(df: pd.DataFrame, by) -> pd.DataFrame:
    g = df.groupby(by, observed=True)[["somme_prix", "n_stations"]].sum()
    g["prix"] = g["somme_prix"] / g["n_stations"]
    return g.reset_index()


def period_mean(df: pd.DataFrame) -> float:
    n = df["n_stations"].sum()
    return float(df["somme_prix"].sum() / n) if n else float("nan")


def yearly_indicators(weekly: pd.DataFrame, fuel: str, regions=None,
                      route=None) -> pd.DataFrame:
    w = filter_weekly(weekly, weekly["semaine"].min(), weekly["semaine"].max(),
                      regions, None, [fuel])
    w = w.assign(annee=w["semaine"].dt.year)
    w_route = w if not route or route == "All" else w[w["type_route"] == route]

    out = weighted_mean(w_route, ["annee"]).set_index("annee")[["prix"]]

    dep = weighted_mean(w_route[w_route["departement"].str.len() == 2],
                        ["annee", "departement"])
    piv = dep.pivot(index="annee", columns="departement", values="prix")
    enough = piv.notna().sum(axis=1) >= 5
    out["ecart_dep"] = ((piv.quantile(0.9, axis=1) - piv.quantile(0.1, axis=1)) * 100
                        ).where(enough)
    out["dep_min"], out["dep_max"] = piv.idxmin(axis=1), piv.idxmax(axis=1)
    out["prix_min"], out["prix_max"] = piv.min(axis=1), piv.max(axis=1)

    rt = weighted_mean(w, ["annee", "type_route"]).pivot(
        index="annee", columns="type_route", values="prix")
    if {"Motorway", "Road"} <= set(rt.columns):
        out["surcout_autoroute"] = (rt["Motorway"] - rt["Road"]) * 100
    else:
        out["surcout_autoroute"] = float("nan")
    return out
