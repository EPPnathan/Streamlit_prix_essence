from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.config import EVENTS, FUEL_LABELS, PERIODS, REMISE_STEPS

FUEL_COLORS = {
    "Diesel": "#2a78d6",
    "E10": "#eb6834",
    "SP95": "#1baf7a",
    "SP98": "#eda100",
    "E85": "#e87ba4",
    "LPG": "#008300",
}
ROUTE_COLORS = {"Road": "#2a78d6", "Motorway": "#eb6834"}
SEQ_BLUE = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281", "#0d366b"]
SEQ_RED = ["#fde5e4", "#f9b8b5", "#f28a87", "#e34948", "#b8302f", "#8a1f1f", "#5c1010"]
DIVERGING = ["#1c5cab", "#86b6ef", "#f0efec", "#f28a87", "#b8302f"]
MUTED = "#898781"

PRICE_AXIS = "Average price (€/L)"


def _with_labels(df: pd.DataFrame) -> pd.DataFrame:
    return df.assign(carburant=df["carburant"].astype(str).map(FUEL_LABELS))


def _base_layout(fig: go.Figure, title: str, height: int = 420) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=16)),
        height=height,
        margin=dict(l=10, r=10, t=70, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, title=None),
        hoverlabel=dict(namelength=-1),
    )
    return fig


def show(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch", theme="streamlit")


def line_chart(df: pd.DataFrame, start, end, index: bool = False) -> go.Figure:
    df = _with_labels(df).sort_values("semaine")
    y_label, hover = PRICE_AXIS, "%{y:.3f} €/L"
    if index:
        df = df.assign(prix=df["prix"] / df.groupby("carburant")["prix"].transform("first") * 100)
        y_label, hover = "Index (first week = 100)", "%{y:.0f}"
    fig = px.line(
        df, x="semaine", y="prix", color="carburant", color_discrete_map=FUEL_COLORS,
        labels={"semaine": "Week", "prix": y_label, "carburant": "Fuel"},
    )
    fig.update_traces(line=dict(width=2), hovertemplate=hover)
    if index:
        fig.add_hline(y=100, line=dict(color=MUTED, width=1, dash="dash"))
    for p_start, p_end, label in PERIODS:
        if pd.Timestamp(p_end) < pd.Timestamp(start) or pd.Timestamp(p_start) > pd.Timestamp(end):
            continue
        fig.add_vrect(x0=p_start, x1=p_end, fillcolor=MUTED, opacity=0.15, line_width=0,
                      annotation_text=label, annotation_position="bottom left",
                      annotation_font=dict(size=11, color=MUTED))
    for day, label in EVENTS:
        day = pd.Timestamp(day)
        if not (pd.Timestamp(start) <= day <= pd.Timestamp(end)):
            continue
        fig.add_vline(x=day, line=dict(color=MUTED, width=1, dash="dot"))
        fig.add_annotation(x=day, y=1, yref="paper", text=label, showarrow=False,
                           textangle=-90, xanchor="right", yanchor="top",
                           font=dict(size=11, color=MUTED))
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(title=None)
    return _base_layout(fig, "Weekly price by fuel")


def remise_chart(df: pd.DataFrame) -> go.Figure:
    fig = px.line(
        _with_labels(df), x="semaine", y="prix", color="carburant",
        color_discrete_map=FUEL_COLORS,
        labels={"semaine": "Week", "prix": PRICE_AXIS, "carburant": "Fuel"},
    )
    fig.update_traces(line=dict(width=2), hovertemplate="%{y:.3f} €/L")
    for i, (p_start, p_end, label) in enumerate(REMISE_STEPS):
        fig.add_vrect(x0=p_start, x1=p_end, fillcolor=MUTED, opacity=0.08 + 0.06 * (i == 1),
                      line_width=0, annotation_text=label, annotation_position="top left",
                      annotation_font=dict(size=12, color=MUTED))
    day = pd.Timestamp(EVENTS[1][0])
    fig.add_vline(x=day, line=dict(color=MUTED, width=1, dash="dot"))
    fig.add_annotation(x=day, y=0, yref="paper", text=EVENTS[1][1], showarrow=False,
                       textangle=-90, xanchor="right", yanchor="bottom",
                       font=dict(size=11, color=MUTED))
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(title=None)
    return _base_layout(fig, "2022 close-up: diesel and E10 during the fuel rebate")


def annual_chart(df: pd.DataFrame, fuel: str) -> go.Figure:
    ref = df["prix"].iloc[0]
    colors = [MUTED if y == df.index[0] else FUEL_COLORS.get(fuel, "#2a78d6") for y in df.index]
    fig = go.Figure(go.Bar(
        x=df.index.astype(str), y=df["prix"], marker_color=colors, marker_line_width=0,
        text=[f"{p:.2f}" for p in df["prix"]], textposition="outside",
        hovertemplate="%{x}: %{y:.3f} €/L<extra></extra>",
    ))
    fig.add_hline(y=ref, line=dict(color=MUTED, width=1, dash="dash"),
                  annotation_text=f"{df.index[0]} level", annotation_position="top left",
                  annotation_font_color=MUTED)
    fig.update_yaxes(title=PRICE_AXIS, range=[df["prix"].min() * 0.85, df["prix"].max() * 1.06])
    fig.update_xaxes(title=None, type="category")
    return _base_layout(fig, f"Average price per year: {fuel}", height=380)


def gaps_chart(df: pd.DataFrame, fuel: str) -> go.Figure:
    series = {"surcout_autoroute": ("Motorway premium", "#eb6834"),
              "ecart_dep": ("Gap between départements (9th − 1st decile)", "#2a78d6")}
    fig = go.Figure()
    for col, (name, color) in series.items():
        s = df[col].dropna()
        if s.empty:
            continue
        fig.add_trace(go.Scatter(
            x=s.index, y=s, name=name, mode="lines+markers+text",
            line=dict(color=color, width=2), marker=dict(size=8, color=color),
            text=[f"{v:.1f}" if i in (0, len(s) - 1) else "" for i, v in enumerate(s)],
            textposition="top center", hovertemplate="%{x}: %{y:.1f} c€/L",
        ))
    fig.update_yaxes(title="Gap (c€/L)", rangemode="tozero")
    fig.update_xaxes(title=None, dtick=1)
    fig.update_layout(hovermode="x unified")
    return _base_layout(fig, f"How the price gaps changed: {fuel}", height=400)


def region_heatmap(dev: pd.DataFrame, fuel: str) -> go.Figure:
    lim = float(dev.drop(index="Corsica", errors="ignore").abs().max().max())
    fig = px.imshow(
        dev, aspect="auto", text_auto=".1f", zmin=-lim, zmax=lim,
        color_continuous_scale=DIVERGING,
        labels=dict(x="Year", y="Region", color="c€/L vs average"),
    )
    fig.update_traces(hovertemplate="%{y}, %{x}: %{z:+.1f} c€/L vs average<extra></extra>")
    fig.update_xaxes(dtick=1, title=None)
    fig.update_yaxes(title=None)
    return _base_layout(fig, f"Gap to the national average by region: {fuel}", height=520)


def ranking_chart(df: pd.DataFrame, national: float, title: str, n: int = 10) -> go.Figure:
    df = df.sort_values("prix")
    sel = pd.concat([df.head(n).assign(groupe="Cheapest"),
                     df.tail(n).assign(groupe="Most expensive")]).drop_duplicates("departement")
    fig = px.bar(
        sel, x="prix", y="departement", color="groupe", orientation="h",
        color_discrete_map={"Cheapest": "#2a78d6", "Most expensive": "#eb6834"},
        labels={"prix": PRICE_AXIS, "departement": "Département", "groupe": ""},
        hover_data={"prix": ":.3f", "groupe": False},
    )
    fig.add_vline(x=national, line=dict(color=MUTED, width=1, dash="dash"),
                  annotation_text=f"Average {national:.3f} €/L",
                  annotation_position="top", annotation_font_color=MUTED)
    fig.update_xaxes(range=[sel["prix"].min() - 0.03, sel["prix"].max() + 0.01])
    fig.update_yaxes(type="category", categoryorder="array",
                     categoryarray=sel["departement"].tolist())
    fig.update_traces(marker_line_width=0)
    return _base_layout(fig, title, height=max(420, 22 * len(sel)))


def choropleth_chart(df: pd.DataFrame, geojson: dict, national: float,
                     title: str) -> go.Figure:
    df = df.assign(ecart=(df["prix"] - national) * 100,
                   rang=df["prix"].rank(ascending=False, method="min").astype(int))
    lo, hi = df["prix"].quantile([0.05, 0.95])
    fig = px.choropleth_map(
        df, geojson=geojson, locations="departement", featureidkey="properties.code",
        color="prix", color_continuous_scale=SEQ_RED, range_color=(lo, hi),
        hover_name="nom",
        hover_data={"departement": True, "prix": ":.3f", "ecart": ":+.1f", "rang": True},
        labels={"prix": "€/L", "departement": "Code", "ecart": "Gap to average (c€/L)",
                "rang": f"Rank (1 = most expensive of {len(df)})"},
        zoom=4.4, center=dict(lat=46.6, lon=2.4), map_style="carto-positron", opacity=0.9,
    )
    fig.update_traces(marker_line_width=0.5, marker_line_color="#ffffff")
    fig.update_layout(coloraxis_colorbar=dict(title="€/L"))
    return _base_layout(fig, title, height=620)


def map_chart(df: pd.DataFrame, title: str) -> go.Figure:
    lo, hi = df["prix_moyen"].quantile([0.05, 0.95])
    fig = px.scatter_map(
        df, lat="latitude", lon="longitude", color="prix_moyen",
        color_continuous_scale=SEQ_BLUE, range_color=(lo, hi), hover_name="ville",
        hover_data={"departement": True, "type_route": True, "prix_moyen": ":.3f",
                    "latitude": False, "longitude": False},
        labels={"prix_moyen": "€/L", "departement": "Dept.", "type_route": "Type"},
        zoom=4.6, center=dict(lat=46.6, lon=2.4), map_style="carto-positron",
    )
    fig.update_traces(marker=dict(size=5, opacity=0.8))
    fig.update_layout(coloraxis_colorbar=dict(title="€/L"))
    return _base_layout(fig, title, height=620)


def route_box(df: pd.DataFrame, title: str) -> go.Figure:
    fig = px.box(
        df, x="type_route", y="prix_moyen", color="type_route",
        color_discrete_map=ROUTE_COLORS, points=False,
        labels={"type_route": "Station type", "prix_moyen": PRICE_AXIS},
    )
    fig.update_layout(showlegend=False)
    return _base_layout(fig, title, height=420)


def quality_bar(df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df, x="annee", y="lignes", color="regle", barmode="group",
        color_discrete_sequence=["#2a78d6", "#eb6834", "#1baf7a"],
        labels={"annee": "Year", "lignes": "Rows removed", "regle": "Rule"},
    )
    fig.update_xaxes(type="category")
    return _base_layout(fig, "Price records removed during cleaning", height=380)
