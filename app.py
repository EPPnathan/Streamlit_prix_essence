from __future__ import annotations

import base64

import pandas as pd
import streamlit as st

from utils.config import FUEL_LABELS, LOGO_PATH, METRO_BBOX, PROFILE, SOURCE, TABLES_DIR
from utils.io import load_tables
from utils.prep import (coord_status, filter_weekly, period_mean, weighted_mean,
                        yearly_indicators)
from utils.viz import (annual_chart, choropleth_chart, gaps_chart, line_chart, map_chart,
                       quality_bar, ranking_chart, region_heatmap, remise_chart, route_box,
                       show)

st.set_page_config(page_title="Fuel prices in France", layout="wide")

MAIN_FUELS = ["Gazole", "E10", "SP95", "SP98"]
RULES = {
    "date_ou_prix_invalide": "Invalid date or price",
    "prix_aberrant": "Price outside [0.30, 4.00] €/L",
    "doublons": "Duplicates",
}
FUEL = "Gazole"
FUEL_NAME = "diesel"
FUEL_LABEL = "Diesel"
LITRES = 50


def _link(url: str) -> str:
    label = url.removeprefix("https://").removeprefix("www.").rstrip("/")
    return f"[{label}]({url})"


def student_card() -> None:
    p = PROFILE
    with st.sidebar:
        if LOGO_PATH.exists():
            mime = "svg+xml" if LOGO_PATH.suffix == ".svg" else "png"
            data = base64.b64encode(LOGO_PATH.read_bytes()).decode()
            st.markdown(
                f'<div style="background:#ffffff;padding:12px 14px;border-radius:8px">'
                f'<img src="data:image/{mime};base64,{data}" alt="EFREI logo" '
                f'style="width:100%;display:block"></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown("### EFREI Paris")
        st.markdown(f"## {p['name']}")
        st.markdown(f"{p['program']}  \n{p['year']}")
        contacts = [f"Email: {p['email']}" if p.get("email") else "",
                    f"LinkedIn: {_link(p['linkedin'])}" if p.get("linkedin") else "",
                    f"GitHub: {_link(p['github'])}" if p.get("github") else ""]
        st.markdown("  \n".join(c for c in contacts if c))
        st.divider()
        st.markdown(f"**{p['course']}**")
        prof_link = (f"  \nLinkedIn: {_link(p['professor_linkedin'])}"
                     if p.get("professor_linkedin") else "")
        st.markdown(f"Prof: {p['professor']}{prof_link}")


@st.cache_data(show_spinner="Loading data…")
def get_data() -> dict:
    return load_tables()


def how_to_read(text: str) -> None:
    st.caption(f"How to read it: {text}")


if not (TABLES_DIR / "weekly.parquet").exists():
    st.error("Data not found. Run `python scripts/download_data.py`, then "
             "`python scripts/build_tables.py`.")
    st.stop()

tables = get_data()
weekly = tables["weekly"]
names = dict(zip(tables["dep_names"].departement, tables["dep_names"].nom))


def dep_label(code: str) -> str:
    return f"{names.get(code, code)} ({code})"


student_card()

start, end = weekly["semaine"].min(), weekly["semaine"].max()
regions = []
route = "All"
years = list(range(start.year, end.year + 1))
ind = yearly_indicators(weekly, FUEL, regions, route)
yr = ind.loc[[y for y in ind.index if y in years]]

st.title("Fuel prices in France, 2019-2025")
st.markdown("#### The crisis is over, the gaps are not")

last_y = yr.index.max()
last = yr.loc[last_y]
st.markdown(
    f"In {last_y}, a {LITRES} L tank of {FUEL_NAME} cost **{last.prix_min * LITRES:.2f} €** on "
    f"average in the cheapest département, {dep_label(last.dep_min)}, and "
    f"**{last.prix_max * LITRES:.2f} €** in the most expensive, {dep_label(last.dep_max)}. "
    f"On the motorway, drivers paid another {last.surcout_autoroute / 100 * LITRES:.2f} € on average."
)
st.markdown(
    "Between 2019 and 2025, French pump prices peaked in 2022, were cushioned by a "
    "government rebate at the pump, then slowly came down. Over the same years, **the gaps "
    "between areas and between types of station grew**, so where you fill up matters more "
    "now than it did in 2019."
)
st.markdown("The story in four parts: 1. the shock · 2. the shield · 3. the decline · "
            "4. the widening gaps. Unless stated otherwise, the charts cover diesel for all of France.")
st.divider()

st.header("The data: where it comes from and how it was cleaned")
st.markdown(
    f"French law requires every filling station to report its prices. The Ministry of the "
    f"Economy publishes these records on [data.gouv.fr]({SOURCE['portail']}) under the "
    f"{SOURCE['licence']}, as one XML archive per year (20 to 30 MB zipped, about 330 MB "
    "unzipped). This project uses 2019 to 2025."
)
st.markdown(
    "1. **Download** the seven yearly archives (`scripts/download_data.py`).\n"
    "2. **Read the XML one station at a time**, so a whole file never has to fit in "
    "memory.\n"
    "3. **Clean the prices**: drop invalid dates and prices, prices outside 0.30 to 4.00 €/L, "
    "and duplicates (same station, fuel and timestamp).\n"
    "4. **Clean the stations**: convert coordinates to GPS, derive the département from the "
    "postcode (2A/2B for Corsica, three digits overseas), and label each station as road or "
    "motorway.\n"
    "5. **Aggregate** (`scripts/build_tables.py`): average each station's price per week, "
    "then average across stations. A station that updates its prices twice a day counts as "
    "much as one that updates them once a week."
)

q = tables["quality"]
raw, kept = q.lignes_brutes.sum(), q.lignes_finales.sum()
st.markdown(f"**The price records are reliable: {kept / raw:.2%} of the "
            f"{raw / 1e6:.1f} million rows survive cleaning.**")
long = (q.melt(id_vars="annee", value_vars=list(RULES), var_name="regle", value_name="lignes")
          .assign(regle=lambda d: d.regle.map(RULES)))
show(quality_bar(long))
how_to_read("each group of bars is a year and each color a cleaning rule. Almost every "
            "removed row had an invalid date or price (3,000 to 5,000 a year); out-of-range "
            "prices and duplicates number in the hundreds at most.")

status = coord_status(tables["stations"], METRO_BBOX).value_counts()
st.markdown(
    f"The station register is messier: {status.get('Missing', 0)} stations have no "
    f"coordinates, {status.get('Latitude/longitude swapped', 0)} have their latitude and "
    f"longitude swapped, {status.get('Outside France', 0)} are placed outside France and "
    f"{status.get('Coordinates (0, 0)', 0)} sit at (0, 0). They are left off the maps."
)
st.caption(f"Source: [{SOURCE['titre']}]({SOURCE['portail']}) · {SOURCE['licence']}")
st.divider()

st.header("1. The shock: prices take off")
ts = weighted_mean(filter_weekly(weekly, start, end, regions, route, MAIN_FUELS),
                   ["semaine", "carburant"])
if ts.empty:
    st.warning("No data for this selection.")
    st.stop()
sel = ts[ts.carburant == FUEL]
low, top = sel.loc[sel.prix.idxmin()], sel.loc[sel.prix.idxmax()]
st.markdown(
    f"**{FUEL_LABEL} went from {low.prix:.2f} €/L at its lowest (week of "
    f"{low.semaine:%d %b %Y}) to {top.prix:.2f} €/L at its peak (week of "
    f"{top.semaine:%d %b %Y}), a rise of {top.prix / low.prix - 1:.0%}.**"
)
as_index = st.toggle("Show as an index (first week = 100)",
                     help="Puts every fuel on the same base so you can compare how much "
                          "each one rose.")
show(line_chart(ts, start, end, index=as_index))
how_to_read("one line per fuel, showing the average price each week in €/L. Dotted lines "
            "mark the first lockdown and the invasion of Ukraine; the grey band covers the "
            "fuel rebate, from April to December 2022. In index mode, each fuel starts at 100 "
            "in the first week, which makes the rises comparable.")
piv = ts.pivot(index="semaine", columns="carburant", values="prix")
y22 = piv[piv.index.year == 2022]
n_weeks = int((y22["Gazole"] > y22["E10"]).sum()) if {"Gazole", "E10"} <= set(piv.columns) else 0
if n_weeks:
    st.markdown(
        f"Diesel is normally cheaper than petrol in France, yet **it cost more than E10 for "
        f"{n_weeks} weeks in 2022**. At the time, Europe bought a large share of its diesel "
        "from Russia, and that market was especially tight after the invasion of Ukraine."
    )
st.divider()

st.header("2. The shield: the rebate shows up week by week")
ts22 = weighted_mean(filter_weekly(weekly, "2022-01-01", "2023-03-31", regions, route,
                                   ["Gazole", "E10"]), ["semaine", "carburant"])


def _price_at(df: pd.DataFrame, fuel: str, day: str) -> float:
    s = df[df.carburant == fuel].set_index("semaine")["prix"]
    return float(s.iloc[s.index.get_indexer([pd.Timestamp(day)], method="nearest")[0]])


if {"Gazole", "E10"} <= set(ts22.carburant):
    drop = (_price_at(ts22, "Gazole", "2022-04-04") - _price_at(ts22, "Gazole", "2022-03-28")) * 100
    jump = (_price_at(ts22, "E10", "2023-01-02") - _price_at(ts22, "E10", "2022-12-26")) * 100
    st.markdown(
        f"**On 1 April 2022, diesel fell {abs(drop):.0f} c€/L in a single week. When the rebate "
        f"ended on 1 January 2023, E10 rose {jump:.0f} c€/L.** The rebate (18 c€, then 30 c€, "
        "then 10 c€ per litre) softened the shock without removing it."
    )
    show(remise_chart(ts22))
    how_to_read("diesel and E10 from January 2022 to March 2023. The three grey bands are the "
                "steps of the rebate (−18, −30, then −10 c€/L). Prices are what drivers paid "
                "at the pump, after the rebate.")
st.divider()

st.header("3. The decline: prices come back down")
annual = yr[["prix"]].dropna()
if len(annual) >= 2:
    peak_y, first_y = annual.prix.idxmax(), annual.index.min()
    p_last, p_peak, p_first = annual.prix[last_y], annual.prix[peak_y], annual.prix[first_y]
    st.markdown(
        f"**The yearly average for {FUEL_NAME} is down {1 - p_last / p_peak:.0%} from its "
        f"{peak_y} peak. In {last_y} it was still {abs(p_last / p_first - 1):.0%} "
        f"{'higher' if p_last >= p_first else 'lower'} than in {first_y}.**"
    )
    show(annual_chart(annual, FUEL_LABEL))
    how_to_read(f"one bar per year. The grey bar ({first_y}) is the reference, carried across "
                "by the dashed line. Prices are in current euros: part of the rise since 2019 "
                "is general inflation, which is not corrected here.")
st.divider()

st.header("4. The gaps widen")
dep_gap, auto_gap = yr["ecart_dep"].dropna(), yr["surcout_autoroute"].dropna()
if len(dep_gap) >= 2 and len(auto_gap) >= 2:
    record = (", the highest of the period" if auto_gap.idxmax() == auto_gap.index[-1] else "")
    st.markdown(
        f"**Between {dep_gap.index[0]} and {dep_gap.index[-1]}, the gap between expensive and "
        f"cheap départements went from {dep_gap.iloc[0]:.1f} to {dep_gap.iloc[-1]:.1f} c€/L "
        f"({dep_gap.iloc[-1] / dep_gap.iloc[0] - 1:+.0%}), and the motorway premium from "
        f"{auto_gap.iloc[0]:.1f} to {auto_gap.iloc[-1]:.1f} c€/L{record}.**"
    )
    show(gaps_chart(yr, FUEL_LABEL))
    how_to_read("the orange line is the average premium at motorway stations over road "
                "stations. The blue line is the price at the 9th-decile département minus the "
                "price at the 1st-decile one, so an outlier such as Corsica does not move it. "
                "In 2022, the year of the rebate, the motorway premium briefly shrank.")

w_reg = filter_weekly(weekly, start, end, None, route, [FUEL])
w_reg = w_reg[~w_reg.region.isin(["Overseas", "Other"])].assign(annee=w_reg.semaine.dt.year)
if not w_reg.empty:
    reg = weighted_mean(w_reg, ["annee", "region"]).pivot(index="region", columns="annee",
                                                          values="prix")
    nat = weighted_mean(w_reg, ["annee"]).set_index("annee")["prix"]
    dev = ((reg - nat) * 100).sort_values(reg.columns[-1])
    if dev.shape[1] >= 2 and len(dev) >= 3:
        y0, y1 = dev.columns[0], dev.columns[-1]
        cheap = dev.index[0]
        dear = dev.index[-2] if dev.index[-1] == "Corsica" else dev.index[-1]
        st.markdown(
            f"**The same pattern shows up region by region: {cheap} went from "
            f"{dev.loc[cheap, y0]:+.1f} to {dev.loc[cheap, y1]:+.1f} c€/L against the national "
            f"average, and {dear} from {dev.loc[dear, y0]:+.1f} to {dev.loc[dear, y1]:+.1f} "
            "c€/L.**"
        )
        show(region_heatmap(dev, FUEL_LABEL))
        how_to_read("one row per region and one column per year. Each cell is the gap to the "
                    "national average in c€/L: blue when the region is cheaper, red when it "
                    "is more expensive. Corsica is so far above the others that its row "
                    "saturates the scale.")

st.subheader("Where does a full tank cost the most?")
year = st.select_slider("Year shown", options=years, value=years[-1],
                        help="Drives the département map, the ranking, the station map and "
                             "the road vs motorway comparison.")
dep_df = filter_weekly(weekly, f"{year}-01-01", f"{year}-12-31", regions, route, [FUEL])
by_dep = weighted_mean(dep_df, ["departement"])
if len(by_dep) >= 2:
    hi, lo = by_dep.loc[by_dep.prix.idxmax()], by_dep.loc[by_dep.prix.idxmin()]
    st.markdown(
        f"**In {year}, drivers in {dep_label(hi.departement)} paid "
        f"{(hi.prix - lo.prix) * 100:.0f} c€/L more for {FUEL_NAME} than drivers in "
        f"{dep_label(lo.departement)}, or {(hi.prix - lo.prix) * LITRES:.2f} € more for a "
        f"{LITRES} L tank.**"
    )
    geo_df = by_dep.merge(tables["dep_names"], on="departement")
    if not geo_df.empty:
        show(choropleth_chart(geo_df, tables["geo"], period_mean(dep_df),
                              f"Average price by département in {year}: {FUEL_LABEL}"))
        how_to_read("each département is shaded by its average price for the year, from light "
                    "red (cheaper) to dark red (more expensive). Hover over a département to "
                    "see its price, its gap to the average and its rank. Overseas départements "
                    "are not shown. Switch the year to compare with 2019.")
    n = st.slider("Départements per group", 5, 20, 10)
    show(ranking_chart(by_dep, period_mean(dep_df),
                       f"Most and least expensive départements in {year}: {FUEL_LABEL}", n))
    how_to_read("the cheapest départements are in blue and the most expensive in orange; the "
                "dashed line is the national average. The slider sets how many départements "
                "each group shows.")

sy = tables["station_year"]
st_df = (sy[(sy.carburant == FUEL) & (sy.annee == year)]
         .merge(tables["stations"].drop(columns="annee"), on="station_id"))
in_metro = (st_df.latitude.between(*METRO_BBOX["lat"])
            & st_df.longitude.between(*METRO_BBOX["lon"]))
if in_metro.any():
    show(map_chart(st_df[in_metro], f"Average price by station in {year}: {FUEL_LABEL}"))
    how_to_read("each dot is a station, from light blue (cheaper) to dark blue (more "
                "expensive). Stations without valid coordinates or outside mainland France "
                "are not shown.")

if {"Road", "Motorway"} <= set(st_df.type_route):
    st.subheader("Paying for convenience: motorway stations")
    qt = st_df.groupby("type_route").prix_moyen.quantile([0.25, 0.5, 0.75]).unstack()
    gap = qt.loc["Motorway", 0.5] - qt.loc["Road", 0.5]
    no_overlap = qt.loc["Motorway", 0.25] > qt.loc["Road", 0.75]
    st.markdown(
        f"**In {year}, the median motorway station charged {gap * 100:.0f} c€/L more for "
        f"{FUEL_NAME} than the median road station, or {gap * LITRES:.2f} € more per tank."
        + (" Three quarters of motorway stations were more expensive than three quarters of "
           "road stations." if no_overlap else "") + "**"
    )
    show(route_box(st_df[st_df.type_route.isin(["Road", "Motorway"])],
                   f"Station prices on roads and motorways, {year}: {FUEL_LABEL}"))
    how_to_read("each box sums up the average prices of one type of station. The middle line "
                "is the median, the box holds the middle half of the stations, and the "
                "whiskers reach toward the more extreme values.")
st.divider()

st.header("Takeaways")
if len(annual) >= 2 and len(dep_gap) >= 2 and len(auto_gap) >= 2:
    st.success(
        f"1. **The shock has passed.** The yearly average for {FUEL_NAME} is down "
        f"{1 - p_last / p_peak:.0%} since {peak_y}.\n"
        "2. **The rebate cushioned the shock while it lasted.** Its start shows up in that "
        "week's prices, and drivers paid the difference as soon as it ended.\n"
        f"3. **The gaps grew.** From {dep_gap.index[0]} to {dep_gap.index[-1]}, the gap between "
        f"départements went from {dep_gap.iloc[0]:.1f} to {dep_gap.iloc[-1]:.1f} c€/L and the "
        f"motorway premium from {auto_gap.iloc[0]:.1f} to {auto_gap.iloc[-1]:.1f} c€/L.\n"
        f"4. **For a {LITRES} L tank in {last_y}**, the cheapest and the most expensive "
        f"département were {(last.prix_max - last.prix_min) * LITRES:.2f} € apart."
    )
st.markdown(
    "- **Drivers** can save by choosing where they fill up; the gaps between départements "
    "and between road and motorway stations give the size of the saving.\n"
    "- **Policymakers**: a flat rebate gives everyone the same discount, whatever they pay "
    "locally. Help aimed at the most expensive areas, or at people who depend most on their "
    "car, would be fairer.\n"
    "- **Next steps**: adjust for inflation, compare with crude oil prices and median income "
    "by département, and look for the causes of the gaps (local competition, number of "
    "stations, delivery costs)."
)
st.info(
    "**Limitations**\n"
    "- Stations report their own prices, so some updates arrive late or not at all.\n"
    "- The data does not include station names or brands, so retailers cannot be compared.\n"
    "- Prices are in current euros and are not adjusted for inflation.\n"
    "- The département comes from the postcode, so a few stations near a border may be "
    "assigned to the neighbouring one.\n"
    "- These findings describe the gaps. They do not establish their causes."
)
st.divider()

st.header("The data in detail")
st.caption("Each tab can be downloaded as a CSV file.")


def _download(df: pd.DataFrame, name: str, key: str) -> None:
    st.download_button(f"Download as CSV ({len(df):,} rows)",
                       df.to_csv(index=False).encode("utf-8"), file_name=f"{name}.csv",
                       mime="text/csv", key=key)


w = filter_weekly(weekly, start, end, regions, route)
tab_week, tab_dep, tab_station = st.tabs(["Weekly prices", "By département", "By station"])
with tab_week:
    weekly_table = weighted_mean(w, ["semaine", "carburant"])
    weekly_table = (weekly_table.assign(carburant=weekly_table.carburant.astype(str).map(FUEL_LABELS))
                    .pivot(index="semaine", columns="carburant", values="prix").round(3)
                    .rename_axis(index="week", columns=None).reset_index())
    st.dataframe(weekly_table, hide_index=True, width="stretch")
    _download(weekly_table, "weekly_prices", "dl_week")
with tab_dep:
    dep = weighted_mean(w[w.carburant == FUEL].assign(year=w.semaine.dt.year),
                        ["year", "departement"])
    dep = dep.pivot(index="departement", columns="year", values="prix").round(3)
    dep.columns = dep.columns.astype(str)
    dep = (dep.reset_index().merge(tables["dep_names"], on="departement", how="left")
              .rename(columns={"nom": "name"}))
    dep = dep[["departement", "name"] + [c for c in dep.columns if c not in ("departement", "name")]]
    st.dataframe(dep, hide_index=True, width="stretch")
    _download(dep, f"departements_{FUEL_NAME}", "dl_dep")
with tab_station:
    stations = (sy[(sy.carburant == FUEL) & sy.annee.isin(years)]
                .merge(tables["stations"].drop(columns="annee"), on="station_id"))
    stations = (stations[["annee", "station_id", "ville", "cp", "departement", "region",
                          "type_route", "prix_moyen", "n_semaines"]]
                .rename(columns={"annee": "year", "ville": "city", "cp": "postcode",
                                 "type_route": "station_type", "prix_moyen": "avg_price",
                                 "n_semaines": "weeks_reported"})
                .round({"avg_price": 3}))
    st.dataframe(stations.head(1000), hide_index=True, width="stretch")
    _download(stations, f"stations_{FUEL_NAME}", "dl_station")
