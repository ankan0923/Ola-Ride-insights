"""
Ola Ride Insights - Streamlit analytics app
Run with:  streamlit run app.py

Pages: Overview, Overall, Vehicle Type, Revenue, Cancellation, Ratings, SQL Queries,
SQL Playground, Power BI Dashboard, Insights & Anomalies, Recommendations,
Forecast, Data Explorer, About & Data Quality.
"""
from __future__ import annotations

import html
import io
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

import ola_logic as L

st.set_page_config(page_title="OLA Ride Insights", page_icon=":material/local_taxi:",
                   layout="wide", initial_sidebar_state="expanded")

APP_DIR = Path(__file__).resolve().parent
ASSETS = next((p for p in (APP_DIR / "logo", APP_DIR / "Logo", APP_DIR / "logos", APP_DIR / "assets") if p.is_dir()),
              APP_DIR / "logo")
DASH_DIR = APP_DIR / "dashboard_images"       # saved Power BI dashboard images live here
IMG_TYPES = ["png", "jpg", "jpeg", "webp"]
MAX_IMG_MB = 10
MAX_IMAGES = 12
LIME, CYAN, ORANGE, VIOLET, PINK, GREEN, YELLOW = (
    "#D4F03C", "#38BDF8", "#FB923C", "#A78BFA", "#F472B6", "#34D399", "#FACC15")
COLORWAY = [LIME, CYAN, ORANGE, VIOLET, PINK, GREEN, YELLOW]
px.defaults.template = "plotly_dark"
px.defaults.color_discrete_sequence = COLORWAY
px.defaults.color_continuous_scale = ["#121B2E", LIME]

CSS = """
<style>
.block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1400px;}
h1, h2, h3 {letter-spacing: -0.01em;}
.hero {padding: 28px 32px; border-radius: 18px; background: linear-gradient(120deg, #121B2E 0%, #0F2236 100%);
       border: 1px solid #22304A; margin-bottom: 18px; display: flex; align-items: center;
       justify-content: space-between; gap: 24px;}
.hero-img {background: #F4F7FB; border-radius: 16px; padding: 8px; flex: 0 0 auto;}
.hero-img img {height: 104px; width: auto; display: block;}
.hero .tag {font-size: 12px; font-weight: 600; letter-spacing: .14em; text-transform: uppercase; color: #9FB0CC;}
.hero h1 {margin: 6px 0 4px 0; font-size: 40px; color: #F4F7FB;}
.hero p {margin: 0; color: #C3CFE3; font-size: 16px;}
.kpi {background: #121B2E; border: 1px solid #22304A; border-radius: 14px; padding: 16px 18px; margin-bottom: 12px;}
.kpi .kpi-l {font-size: 12px; font-weight: 500; letter-spacing: .05em; color: #9FB0CC; text-transform: uppercase;}
.kpi .kpi-v {font-size: 30px; font-weight: 700; color: #F4F7FB; margin-top: 4px;}
.kpi .kpi-s {font-size: 13px; color: #9FB0CC; margin-top: 2px;}
.kpi.good .kpi-v {color: #D4F03C;} .kpi.bad .kpi-v {color: #FB923C;}
.rec {background: #121B2E; border: 1px solid #22304A; border-radius: 14px; padding: 18px 20px; margin-bottom: 14px;}
.rec .pill {display: inline-block; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 999px; letter-spacing: .06em;}
.pill.High {background: #FB923C; color: #0B1220;} .pill.Medium {background: #FACC15; color: #0B1220;}
.pill.Low {background: #38BDF8; color: #0B1220;}
.rec h4 {margin: 8px 0 6px 0; font-size: 18px; color: #F4F7FB;}
.rec .row {font-size: 14px; color: #C3CFE3; margin: 4px 0;} .rec .row b {color: #F4F7FB;}
.note {background: #1B2438; border-left: 4px solid #FACC15; border-radius: 8px; padding: 12px 16px; color: #E5EAF3; font-size: 14px;}
.vcard {background: #121B2E; border: 1px solid #22304A; border-radius: 14px; padding: 14px 8px; text-align: center; margin-bottom: 12px;}
.vcard .vimg {background: #F4F7FB; border-radius: 12px; width: 64px; height: 64px; margin: 0 auto 10px auto;
              display: flex; align-items: center; justify-content: center;}
.vcard .vimg img {width: 44px; height: 44px; object-fit: contain;}
.vcard .vn {font-size: 14px; font-weight: 600; color: #F4F7FB;}
.vcard .vv {font-size: 22px; font-weight: 700; color: #D4F03C; margin-top: 2px;}
.vcard .vs {font-size: 12px; color: #9FB0CC; margin-top: 2px;}
.rbadge {display: inline-flex; background: #F4F7FB; border-radius: 8px; padding: 3px; margin-right: 10px; vertical-align: middle;}
.rbadge img {width: 28px; height: 28px; object-fit: contain;}
.sidelogo {background: #F4F7FB; border-radius: 12px; padding: 6px 10px; text-align: center; margin-top: 8px;}
.sidelogo img {height: 44px; width: auto;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# UI helpers
# ----------------------------------------------------------------------------
def _assets_stamp() -> float:
    try:
        return max([ASSETS.stat().st_mtime] + [f.stat().st_mtime for f in ASSETS.iterdir()])
    except OSError:
        return 0.0


@st.cache_data(show_spinner=False)
def _asset_uri(name: str, max_px: int, stamp: float) -> str:
    path = L.find_image(L.list_images(ASSETS), name, exact=False)
    return (L.image_data_uri(path, max_px) or "") if path else ""


ALLOWED_PICTURES = {"olalogo", "intercity", "sedan"}      # Ola logo + the car pictures; vehicle types come from images()


def asset_uri(name: str, max_px: int = 200) -> str:
    """Ola logo or a car picture from the logo folder; any other file name is ignored on purpose."""
    key = L._norm(name.rsplit(".", 1)[0] if name.lower().endswith(L.IMG_EXT) else name)
    return _asset_uri(name, max_px, _assets_stamp()) if key in ALLOWED_PICTURES else ""


@st.cache_data(show_spinner=False)
def _images(sig: int, stamp: float, _full: pd.DataFrame) -> dict:
    return L.vehicle_image_map(_full, ASSETS)


def images(sig: int, _full: pd.DataFrame) -> dict:
    return _images(sig, _assets_stamp(), _full)


def hero(title: str, sub: str, tag: str = "Ride-sharing & mobility analytics", img: str = "") -> None:
    uri = asset_uri(img, 240) if img else ""
    pic = f'<div class="hero-img"><img src="{html.escape(uri, quote=True)}" alt=""></div>' if uri else ""
    st.markdown(f'<div class="hero"><div><div class="tag">{html.escape(tag)}</div>'
                f'<h1>{html.escape(title)}</h1><p>{html.escape(sub)}</p></div>{pic}</div>', unsafe_allow_html=True)


def card(label: str, value: str, sub: str = "", tone: str = "") -> str:
    return (f'<div class="kpi {tone}"><div class="kpi-l">{html.escape(label)}</div>'
            f'<div class="kpi-v">{html.escape(str(value))}</div>'
            f'<div class="kpi-s">{html.escape(sub)}</div></div>')


def kpi_row(items: list) -> None:
    cols = st.columns(len(items))
    for col, (label, value, sub, tone) in zip(cols, items):
        col.markdown(card(label, value, sub, tone), unsafe_allow_html=True)


def style(fig, height: int = 380, legend: bool = True):
    grid = "rgba(128,128,128,0.25)"
    fig.update_layout(
        height=height + (50 if legend else 0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=64, b=120 if legend else 30), showlegend=legend,
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="left", x=0, title=None),
        title=dict(x=0, xanchor="left", y=0.97, yanchor="top", font=dict(size=16)),
        font=dict(family="Inter, sans-serif"))
    fig.update_xaxes(gridcolor=grid, zerolinecolor=grid, automargin=True)
    fig.update_yaxes(gridcolor=grid, zerolinecolor=grid, automargin=True)
    return fig


def show(fig, height: int = 380, legend: bool = True) -> None:
    st.plotly_chart(style(fig, height, legend))


def section(title: str, sub: str = "") -> None:
    st.markdown(f"### {title}")
    if sub:
        st.caption(sub)


def vehicle_cards(vs: pd.DataFrame, imgs: dict, value_fn, sub_fn) -> None:
    rows = list(vs.to_dict("records"))
    if not rows:
        return
    cols = st.columns(len(rows))
    for col, r in zip(cols, rows):
        uri = imgs.get(r["Vehicle_Type"], "")
        pic = (f'<div class="vimg"><img src="{html.escape(uri, quote=True)}" alt="{html.escape(str(r["Vehicle_Type"]))}"></div>'
               if uri else "")
        col.markdown(f'<div class="vcard">{pic}<div class="vn">{html.escape(str(r["Vehicle_Type"]))}</div>'
                     f'<div class="vv">{html.escape(str(value_fn(r)))}</div>'
                     f'<div class="vs">{html.escape(str(sub_fn(r)))}</div></div>', unsafe_allow_html=True)


def table(data: pd.DataFrame, imgs: dict, **kw) -> None:
    """st.dataframe that adds a vehicle picture column when the table has Vehicle_Type."""
    if imgs and "Vehicle_Type" in data.columns:
        d = data.copy()
        d.insert(0, "Vehicle", d["Vehicle_Type"].map(imgs))
        st.dataframe(d, hide_index=True, column_config={"Vehicle": st.column_config.ImageColumn("Vehicle", width="small")}, **kw)
    else:
        st.dataframe(data, hide_index=True, **kw)


@st.cache_data(show_spinner=False)
def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


# ----------------------------------------------------------------------------
# Data loading
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading and cleaning data...")
def load_path(path: str, mtime: float) -> pd.DataFrame:
    return L.load_csv(path)


@st.cache_data(show_spinner="Cleaning the uploaded file...")
def load_bytes(data: bytes) -> pd.DataFrame:
    return L.load_csv(io.BytesIO(data))


@st.cache_resource(show_spinner="Building the SQL engine...")
def get_conn(signature: str, _df: pd.DataFrame):
    return L.make_connection(_df)


def find_default_csv() -> Path | None:
    preferred = APP_DIR / "ola_cleaned.csv"
    if preferred.exists():
        return preferred
    for p in sorted(APP_DIR.glob("*.csv")):
        return p
    return None


def get_data() -> pd.DataFrame:
    with st.sidebar.expander("Data source", expanded=False):
        up = st.file_uploader("Upload Ola CSV (raw or cleaned)", type=["csv"])
        st.caption("A raw file is cleaned automatically.")
    try:
        if up is not None:
            return load_bytes(up.getvalue())
        p = find_default_csv()
        if p is not None:
            return load_path(str(p), p.stat().st_mtime)
    except ValueError as exc:
        st.error(f"Could not read the data: {exc}")
        st.stop()
    st.title("OLA Ride Insights")
    st.info("Put `ola_cleaned.csv` next to `app.py`, or upload the Ola CSV from the sidebar "
            "(Data source).")
    st.stop()


def sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.markdown("### Filters")
    dmin, dmax = df["Ride_Date"].min().date(), df["Ride_Date"].max().date()
    rng = st.sidebar.date_input("Date range", value=(dmin, dmax), min_value=dmin, max_value=dmax)
    start, end = (rng[0], rng[1]) if isinstance(rng, (tuple, list)) and len(rng) == 2 else (dmin, dmax)
    vehicles = sorted(df["Vehicle_Type"].dropna().unique())
    sel_v = st.sidebar.multiselect("Vehicle type", vehicles, default=vehicles)
    statuses = sorted(df["Booking_Status"].dropna().unique())
    sel_s = st.sidebar.multiselect("Booking status", statuses, default=statuses)
    out = df[(df["Ride_Date"].dt.date >= start) & (df["Ride_Date"].dt.date <= end)
             & df["Vehicle_Type"].isin(sel_v) & df["Booking_Status"].isin(sel_s)]
    st.sidebar.caption(f"{len(out):,} of {len(df):,} bookings selected")
    if out.empty:
        st.warning("No bookings match these filters. Widen the filters in the sidebar.")
        st.stop()
    return out


# ----------------------------------------------------------------------------
# Pages
# ----------------------------------------------------------------------------
def page_overview(df, full, conn):
    k = L.kpis(df)
    hero("OLA Ride Insights",
         f"{k['total']:,} bookings from {df['Ride_Date'].min():%d %b %Y} to {df['Ride_Date'].max():%d %b %Y}: "
         "demand, revenue, cancellations and ratings in one place.", img="intercity.png")
    kpi_row([("Total rides", f"{k['total']:,}", f"{k['unique_customers']:,} customers", ""),
             ("Success rate", L.pct(k["success_rate"]), f"{k['success']:,} completed bookings", "good"),
             ("Cancellation rate", L.pct(k["cancel_rate"]), f"{k['cancelled']:,} cancelled rides", "bad"),
             ("Driver not found", L.pct(k["not_found_rate"]), f"{k['not_found']:,} bookings", "bad")])
    kpi_row([("Revenue", L.inr(k["revenue"]), "successful rides only", "good"),
             ("Average fare", f"₹{k['avg_fare']:,.0f}", f"avg {k['avg_distance']:.1f} km per ride", ""),
             ("Value lost", L.inr(k["lost_value"]), "cancelled and unserved bookings", "bad"),
             ("Average rating", f"{k['avg_driver_rating']:.2f}", f"drivers; customers {k['avg_customer_rating']:.2f}", "")])

    daily = L.daily_series(df)
    c1, c2 = st.columns([2, 1])
    with c1:
        fig = px.area(daily, x="Ride_Date", y=["success", "cancelled"], title="Daily bookings: successful vs cancelled",
                      labels={"value": "Rides", "Ride_Date": "", "variable": ""})
        show(fig)
    with c2:
        st_df = df["Booking_Status"].value_counts().rename_axis("Status").reset_index(name="Rides")
        fig = px.pie(st_df, names="Status", values="Rides", hole=0.58, title="Booking status")
        show(fig, legend=True)

    section("What stands out")
    for r in L.recommendations(df)[:3]:
        st.markdown(f"- **{r['title']}.** {r['evidence']}")
    st.caption("Open Recommendations for the full action list and Forecast for the long-term view.")


def page_overall(df, full, conn):
    hero("Overall", "Ride volume over time and the booking status breakdown.")
    won = df[df["Booking_Status"] == L.SUCCESS]
    busiest = df.groupby("Hour").size().sort_values(ascending=False)
    kpi_row([("Pickup areas", f"{df['Pickup_Location'].nunique():,}", "distinct pickup locations", ""),
             ("Drop areas", f"{df['Drop_Location'].nunique():,}", "distinct drop locations", ""),
             ("Average ride distance", f"{won['Ride_Distance'].mean():.1f} km" if len(won) else "-", "successful rides", ""),
             ("Busiest hour", f"{int(busiest.index[0])}:00", f"{int(busiest.iloc[0]):,} bookings", "")])
    daily = L.daily_series(df)
    daily["7-day average"] = daily["rides"].rolling(7, min_periods=1).mean()
    fig = go.Figure()
    fig.add_bar(x=daily["Ride_Date"], y=daily["rides"], name="Daily bookings", marker_color="#2A3B5C")
    fig.add_scatter(x=daily["Ride_Date"], y=daily["7-day average"], name="7-day average",
                    line=dict(color=LIME, width=3))
    fig.update_layout(title="Ride volume over time")
    show(fig)

    c1, c2 = st.columns(2)
    with c1:
        s = df["Booking_Status"].value_counts().rename_axis("Status").reset_index(name="Rides")
        s["Share"] = (s["Rides"] / s["Rides"].sum() * 100).round(1)
        show(px.bar(s, x="Status", y="Rides", text="Share", title="Booking status breakdown (labels: % share)"))
    with c2:
        hr = df.groupby("Hour").size().rename("Bookings").reset_index()
        show(px.bar(hr, x="Hour", y="Bookings", title="Bookings by hour of day"))

    c3, c4 = st.columns(2)
    with c3:
        wd = df.groupby("Weekday").size().reindex(L.WEEKDAYS).dropna().rename("Bookings").reset_index()
        show(px.bar(wd, x="Weekday", y="Bookings", title="Bookings by weekday"))
    with c4:
        tb = df.groupby("Time_Bucket").size().rename("Bookings").reset_index()
        show(px.pie(tb, names="Time_Bucket", values="Bookings", hole=0.5, title="Share by time of day"))

    m = L.hour_weekday_matrix(df)
    fig = px.imshow(m, aspect="auto", labels=dict(x="Hour of day", y="Weekday", color="Bookings"),
                    title="When demand peaks: weekday by hour")
    show(fig, height=360, legend=False)


def page_vehicle(df, full, conn):
    hero("Vehicle Type", "Distance, revenue, cancellations and ratings for each vehicle type.", img="sedan.png")
    imgs = images(len(full), full)
    vs = L.vehicle_summary(df)
    vehicle_cards(vs, imgs, lambda r: f"{int(r['Bookings']):,}", lambda r: f"bookings, {r['Cancel %']:.1f}% cancelled")
    c1, c2 = st.columns(2)
    with c1:
        top5 = vs.sort_values("Total distance (km)", ascending=False).head(5)
        show(px.bar(top5, x="Vehicle_Type", y="Total distance (km)", text_auto=".3s",
                    title="Top 5 vehicle types by ride distance"), legend=False)
    with c2:
        show(px.bar(vs.sort_values("Avg distance (km)", ascending=False), x="Vehicle_Type", y="Avg distance (km)",
                    text_auto=".1f", title="Average ride distance (km)"), legend=False)
    c3, c4 = st.columns(2)
    with c3:
        show(px.bar(vs.sort_values("Cancel %", ascending=False), x="Vehicle_Type", y="Cancel %", text_auto=".1f",
                    title="Cancellation rate (%)"), legend=False)
    with c4:
        show(px.bar(vs.sort_values("Revenue per km", ascending=False), x="Vehicle_Type", y="Revenue per km",
                    text_auto=".1f", title="Revenue per km (₹)"), legend=False)
    section("Vehicle type summary")
    table(vs, imgs)


def page_revenue(df, full, conn):
    hero("Revenue", "Revenue by payment method, top customers and distance patterns (successful rides).", img="ola_logo")
    ok = df[df["Booking_Status"] == L.SUCCESS]
    if ok.empty:
        st.info("No successful rides in the current selection.")
        return
    k = L.kpis(df)
    kpi_row([("Revenue", L.inr(k["revenue"]), "successful rides", "good"),
             ("Average fare", f"₹{k['avg_fare']:,.0f}", "", ""),
             ("Average distance", f"{k['avg_distance']:.1f} km", "", ""),
             ("Cash share", L.pct((ok["Payment_Method"] == "Cash").mean()), "of successful rides", "")])
    c1, c2 = st.columns(2)
    with c1:
        pm = ok.groupby("Payment_Method")["Booking_Value"].sum().rename("Revenue").reset_index()
        show(px.bar(pm.sort_values("Revenue", ascending=False), x="Payment_Method", y="Revenue", text_auto=".3s",
                    title="Revenue by payment method"), legend=False)
    with c2:
        show(px.pie(pm, names="Payment_Method", values="Revenue", hole=0.55, title="Payment method share of revenue"))
    c3, c4 = st.columns(2)
    with c3:
        top = (ok.groupby("Customer_ID")["Booking_Value"].sum().sort_values(ascending=False).head(5)
               .rename("Total booking value").reset_index())
        show(px.bar(top, x="Total booking value", y="Customer_ID", orientation="h", text_auto=".3s",
                    title="Top 5 customers by total booking value").update_yaxes(autorange="reversed"), legend=False)
    with c4:
        loc = ok.groupby("Pickup_Location")["Booking_Value"].sum().sort_values(ascending=False).head(10).rename("Revenue").reset_index()
        show(px.bar(loc, x="Revenue", y="Pickup_Location", orientation="h",
                    title="Top 10 pickup locations by revenue").update_yaxes(autorange="reversed"), legend=False)
    section("Ride distance distribution per day")
    c5, c6 = st.columns(2)
    with c5:
        dd = ok.groupby("Ride_Date")["Ride_Distance"].mean().rename("Avg distance (km)").reset_index()
        show(px.line(dd, x="Ride_Date", y="Avg distance (km)", title="Average ride distance per day"), legend=False)
    with c6:
        show(px.box(ok, x="Weekday", y="Ride_Distance", category_orders={"Weekday": L.WEEKDAYS},
                    title="Ride distance spread by weekday (km)"), legend=False)
    rev = L.daily_series(df)
    show(px.bar(rev, x="Ride_Date", y="revenue", title="Daily revenue (₹)"), legend=False)


def page_cancellation(df, full, conn):
    hero("Cancellation", "Why bookings fail, when, where and what it costs.", img="ola_logo")
    k = L.kpis(df)
    kpi_row([("Cancelled by customers", f"{k['cust_cancel']:,}", "", "bad"),
             ("Cancelled by drivers", f"{k['drv_cancel']:,}", "", "bad"),
             ("Driver not found", f"{k['not_found']:,}", "", "bad"),
             ("Value lost", L.inr(k["lost_value"]), "all unsuccessful bookings", "bad")])
    c1, c2 = st.columns(2)
    with c1:
        rc = L.reason_counts(df, "Canceled_Rides_by_Customer")
        if len(rc):
            show(px.bar(rc, x="Rides", y="Reason", orientation="h", text_auto=True,
                        title="Customer cancellation reasons").update_yaxes(autorange="reversed"), legend=False)
        else:
            st.info("No customer cancellations in this selection.")
    with c2:
        rd = L.reason_counts(df, "Canceled_Rides_by_Driver")
        if len(rd):
            show(px.bar(rd, x="Rides", y="Reason", orientation="h", text_auto=True,
                        title="Driver cancellation reasons").update_yaxes(autorange="reversed"), legend=False)
        else:
            st.info("No driver cancellations in this selection.")
    c3, c4 = st.columns(2)
    with c3:
        h = L.hourly_cancellation(df)
        h["Cancel rate %"] = h["Cancel rate"] * 100
        show(px.line(h, x="Hour", y="Cancel rate %", markers=True, title="Cancellation rate by hour (%)"), legend=False)
    with c4:
        nf = df[df["Booking_Status"] == "Driver Not Found"]["Pickup_Location"].value_counts().head(10)
        nf = nf.rename_axis("Pickup location").reset_index(name="Unserved bookings")
        show(px.bar(nf, x="Unserved bookings", y="Pickup location", orientation="h",
                    title="Where no driver was found (top 10)").update_yaxes(autorange="reversed"), legend=False)


def page_ratings(df, full, conn):
    hero("Ratings", "Driver and customer ratings on completed rides.", img="ola_logo")
    ok = df[df["Booking_Status"] == L.SUCCESS]
    if ok.empty:
        st.info("No successful rides in the current selection.")
        return
    k = L.kpis(df)
    low = (ok["Driver_Ratings"] < 3.5).mean()
    kpi_row([("Average driver rating", f"{k['avg_driver_rating']:.2f}", "", ""),
             ("Average customer rating", f"{k['avg_customer_rating']:.2f}", "", ""),
             ("Drivers rated below 3.5", L.pct(low), "of rated rides", "bad"),
             ("Rated rides", f"{len(ok):,}", "", "")])
    imgs = images(len(full), full)
    vr = ok.groupby("Vehicle_Type").agg(driver=("Driver_Ratings", "mean"), customer=("Customer_Rating", "mean")).reset_index()
    vehicle_cards(vr, imgs, lambda r: f"{r['driver']:.2f}", lambda r: f"driver, customer {r['customer']:.2f}")
    c1, c2 = st.columns(2)
    with c1:
        show(px.histogram(ok, x="Driver_Ratings", nbins=20, title="Driver ratings distribution"), legend=False)
    with c2:
        show(px.histogram(ok, x="Customer_Rating", nbins=20, title="Customer ratings distribution"), legend=False)
    vs = ok.groupby("Vehicle_Type").agg(driver=("Driver_Ratings", "mean"), customer=("Customer_Rating", "mean")).reset_index()
    c3, c4 = st.columns(2)
    with c3:
        long = vs.melt(id_vars="Vehicle_Type", var_name="Rating of", value_name="Average rating")
        fig = px.bar(long, x="Vehicle_Type", y="Average rating", color="Rating of", barmode="group",
                     title="Average rating by vehicle type")
        fig.update_yaxes(range=[3, 5])
        show(fig)
    with c4:
        fig = px.scatter(vs, x="driver", y="customer", text="Vehicle_Type",
                         labels={"driver": "Avg driver rating", "customer": "Avg customer rating"},
                         title="Customer vs driver ratings by vehicle type")
        fig.update_traces(textposition="top center", marker=dict(size=14))
        show(fig, legend=False)
    sample = ok.sample(min(4000, len(ok)), random_state=1)
    fig = px.density_heatmap(sample, x="Driver_Ratings", y="Customer_Rating", nbinsx=20, nbinsy=20,
                             title="Customer vs driver rating (where rides cluster)")
    show(fig, legend=False)


def _sql_runner(conn, queries: dict, key: str, imgs: dict):
    name = st.selectbox("Choose a question", list(queries), key=f"sel_{key}")
    q = queries[name]
    st.code(q, language="sql")
    try:
        res, secs, trunc = L.run_sql(conn, q)
    except ValueError as exc:
        st.error(str(exc))
        return
    st.caption(f"{len(res):,} rows in {secs * 1000:.0f} ms" + (" (showing first rows)" if trunc else ""))
    table(res, imgs)
    st.download_button("Download result (CSV)", res.to_csv(index=False).encode("utf-8"),
                       file_name=f"{key}_result.csv", mime="text/csv", key=f"dl_{key}")


EXAMPLES = {**L.PROJECT_QUERIES, **L.BUSINESS_QUERIES}


def _load_example():
    name = st.session_state.get("sql_example")
    if name in EXAMPLES:
        st.session_state["sql_text"] = EXAMPLES[name]


def render_playground(conn, imgs: dict):
    st.session_state.setdefault("sql_text", f"SELECT Vehicle_Type, COUNT(*) AS bookings\nFROM {L.TABLE_NAME}\nGROUP BY Vehicle_Type\nORDER BY bookings DESC;")
    st.session_state.setdefault("sql_history", [])
    left, right = st.columns([3, 1])
    with right:
        st.selectbox("Load an example", ["(choose)"] + list(EXAMPLES), key="sql_example", on_change=_load_example)
        with st.expander("Table columns", expanded=True):
            cols = conn.execute(f"PRAGMA table_info({L.TABLE_NAME})").fetchall()
            st.dataframe(pd.DataFrame(cols, columns=["#", "column", "type", "notnull", "default", "pk"])[["column", "type"]],
                         hide_index=True, height=320)
    with left:
        st.text_area("SQL query", key="sql_text", height=230)
        run = st.button("Run query", type="primary", key="sql_run")
        st.caption(f"Write your own SELECT on the table `{L.TABLE_NAME}`. Read-only: one statement, 5,000 rows and 10 seconds at most. "
                   "Engine: SQLite (use strftime instead of MySQL date functions).")
    if run:
        try:
            res, secs, trunc = L.run_sql(conn, st.session_state["sql_text"])
            st.session_state["sql_result"] = (res, secs, trunc)
            hist = st.session_state["sql_history"]
            hist.insert(0, st.session_state["sql_text"])
            st.session_state["sql_history"] = hist[:8]
            st.session_state["sql_error"] = ""
        except ValueError as exc:
            st.session_state["sql_error"] = str(exc)
    if st.session_state.get("sql_error"):
        st.error(st.session_state["sql_error"])
    if "sql_result" in st.session_state and not st.session_state.get("sql_error"):
        res, secs, trunc = st.session_state["sql_result"]
        st.success(f"{len(res):,} rows in {secs * 1000:.0f} ms" + (" (first 5,000 shown)" if trunc else ""))
        table(res, imgs)
        c1, c2 = st.columns([1, 3])
        with c1:
            st.download_button("Download CSV", res.to_csv(index=False).encode("utf-8"),
                               file_name="query_result.csv", mime="text/csv", key="sql_dl")
        numeric = [c for c in res.columns[1:] if pd.api.types.is_numeric_dtype(res[c])]
        if len(res.columns) >= 2 and numeric and 1 < len(res) <= 200:
            with c2:
                chart_it = st.checkbox("Chart this result", key="sql_chart")
            if chart_it:
                show(px.bar(res, x=res.columns[0], y=numeric[0], title=f"{numeric[0]} by {res.columns[0]}"), legend=False)
    if st.session_state["sql_history"]:
        with st.expander("Recent queries"):
            for h in st.session_state["sql_history"]:
                st.code(h, language="sql")


def page_sql(df, full, conn):
    hero("SQL Queries", "Project questions, business questions and a playground for your own queries, on the full dataset.", img="ola_logo")
    imgs = images(len(full), full)
    t1, t2, t3 = st.tabs(["Project questions (10)", "Business questions (10)", "SQL Playground"])
    with t1:
        _sql_runner(conn, L.PROJECT_QUERIES, "project", imgs)
    with t2:
        _sql_runner(conn, L.BUSINESS_QUERIES, "business", imgs)
    with t3:
        render_playground(conn, imgs)
    st.caption("SQL runs on SQLite built from the cleaned CSV. The same SQL works in MySQL "
               "(use HOUR(Date) instead of the Hour column if you prefer).")


def valid_powerbi_url(url: str) -> bool:
    try:
        p = urlparse(url.strip())
    except ValueError:
        return False
    host = (p.hostname or "").lower()
    return p.scheme == "https" and (host == "powerbi.com" or host.endswith(".powerbi.com")) and "..." not in url


def secret_embed_url() -> str:
    try:
        v = st.secrets.get("POWERBI_EMBED_URL", "")
        if v:
            return str(v)
    except Exception:
        pass
    return os.environ.get("POWERBI_EMBED_URL", "")


def page_powerbi(df, full, conn):
    hero("Power BI Dashboard", "Embed your published report or show screenshots of your dashboard pages.", img="ola_logo")
    url = st.text_input("Power BI 'Publish to web' embed URL", value=secret_embed_url(),
                        placeholder="https://app.powerbi.com/view?r=...")
    with st.container(border=True):
        st.markdown("**How to embed your report**")
        st.markdown("1. Publish the `.pbix` from Power BI Desktop to your workspace.\n"
                    "2. In Power BI Service open the report, then **File > Embed report > Publish to web (public)** "
                    "and copy the link.\n"
                    "3. Paste it above, or add `POWERBI_EMBED_URL = \"...\"` to `.streamlit/secrets.toml` "
                    "(or the app's Secrets on Streamlit Cloud) so it loads automatically.")
    st.markdown('<div class="note"><b>Privacy:</b> Publish to web makes the report public to anyone with the link. '
                'Use it only for this non-sensitive project data.</div>', unsafe_allow_html=True)
    st.write("")
    if url.strip():
        if valid_powerbi_url(url):
            components.iframe(url.strip(), height=720, scrolling=True)
            st.markdown(f"[Open the report in a new tab]({url.strip()})")
        else:
            st.error("That does not look like a Power BI link. It should start with https://app.powerbi.com/")
    else:
        st.info("Paste your embed link above to show the dashboard here.")
    st.divider()
    render_dashboard_gallery()


def _check_image(data: bytes):
    """Return 'png' / 'jpeg' / 'webp' for a genuine image, else None (blocks non-image uploads)."""
    try:
        from PIL import Image
        with Image.open(io.BytesIO(data)) as im:
            fmt = (im.format or "").lower()
            im.verify()
        return fmt if fmt in ("png", "jpeg", "webp") else None
    except Exception:
        return None


def saved_dashboard_images() -> list:
    if not DASH_DIR.is_dir():
        return []
    out = []
    for p in sorted(DASH_DIR.iterdir()):
        if p.is_file() and p.suffix.lower().lstrip(".") in IMG_TYPES and p.stat().st_size <= MAX_IMG_MB * 1024 * 1024:
            out.append({"name": p.stem, "data": p.read_bytes(), "saved": True})
    return out[:MAX_IMAGES]


def save_gallery_to_folder(gallery: list) -> int:
    DASH_DIR.mkdir(exist_ok=True)
    count = 0
    for g in gallery:
        fmt = _check_image(g["data"])
        if fmt is None:
            continue
        ext = {"png": ".png", "jpeg": ".jpg", "webp": ".webp"}[fmt]
        base = re.sub(r"[^A-Za-z0-9._-]+", "_", g["name"]).strip("._")[:60] or "dashboard"
        path = DASH_DIR / (base + ext)
        k = 1
        while path.exists():
            path = DASH_DIR / f"{base}_{k}{ext}"
            k += 1
        path.write_bytes(g["data"])
        count += 1
    return count


def render_dashboard_gallery() -> None:
    section("Dashboard images", "Upload several screenshots or exports of your Power BI pages and view them as tabs or a grid.")
    gallery = st.session_state.setdefault("pbi_gallery", [])
    n = st.session_state.setdefault("pbi_up_n", 0)
    saved = saved_dashboard_images()
    files = st.file_uploader(f"Upload dashboard images (select many at once; png, jpg, webp; up to {MAX_IMG_MB} MB each)",
                             type=IMG_TYPES, accept_multiple_files=True, key=f"pbi_up_{n}")
    if files:
        problems, have = [], {(g["name"], len(g["data"])) for g in gallery}
        for f in files:
            data = f.getvalue()
            if len(data) > MAX_IMG_MB * 1024 * 1024:
                problems.append(f"{f.name}: larger than {MAX_IMG_MB} MB, skipped.")
            elif _check_image(data) is None:
                problems.append(f"{f.name}: not a valid png, jpg or webp image, skipped.")
            elif (Path(f.name).stem, len(data)) in have:
                continue
            elif len(gallery) + len(saved) >= MAX_IMAGES:
                problems.append(f"Limit of {MAX_IMAGES} images reached; {f.name} was skipped.")
            else:
                gallery.append({"name": Path(f.name).stem, "data": data, "saved": False})
                have.add((Path(f.name).stem, len(data)))
        st.session_state["pbi_problems"] = problems
        st.session_state["pbi_up_n"] = n + 1           # new empty uploader; the files now live in the gallery
        st.rerun()
    for msg in st.session_state.pop("pbi_problems", []):
        st.warning(msg)

    items = saved + gallery
    if not items:
        st.info("No dashboard images yet. Upload one or more screenshots above.")
        return
    c1, c2 = st.columns([1, 3])
    with c1:
        view = st.radio("View as", ["Tabs", "Grid"], horizontal=True, key="pbi_view")
    with c2:
        st.caption(f"{len(items)} image(s): {len(saved)} saved in the project folder, {len(gallery)} uploaded this session.")
    if view == "Tabs":
        for tab, g in zip(st.tabs([g["name"][:30] for g in items]), items):
            with tab:
                st.image(g["data"], caption=g["name"])
    else:
        cols = st.columns(2)
        for i, g in enumerate(items):
            cols[i % 2].image(g["data"], caption=g["name"])

    with st.expander("Manage images"):
        if gallery:
            rn = st.session_state.get("pbi_rm_n", 0)
            pick = st.multiselect("Choose uploaded images", list(range(len(gallery))),
                                  format_func=lambda i: gallery[i]["name"], key=f"pbi_rm_{rn}")
            b1, b2, b3 = st.columns(3)
            if b1.button("Remove selected", key="pbi_rm_btn") and pick:
                st.session_state["pbi_gallery"] = [g for i, g in enumerate(gallery) if i not in pick]
                st.session_state["pbi_rm_n"] = rn + 1
                st.rerun()
            if b2.button("Remove all uploads", key="pbi_clear_btn"):
                st.session_state["pbi_gallery"] = []
                st.session_state["pbi_rm_n"] = rn + 1
                st.rerun()
            if b3.button("Save uploads to project folder", key="pbi_save_btn"):
                try:
                    done = save_gallery_to_folder(gallery)
                    st.session_state["pbi_gallery"] = []
                    st.success(f"Saved {done} image(s) to {DASH_DIR.name}/. They will load every time the app starts.")
                except OSError as exc:
                    st.error(f"Could not save the images: {exc}")
            st.caption("Uploads last for this browser session. Save them to the project folder to keep them, "
                       "and include that folder when you deploy.")
        else:
            st.caption(f"Images in the {DASH_DIR.name}/ folder load automatically. Delete a file from that folder to remove it.")


def page_insights(df, full, conn):
    hero("Insights & Anomalies", "Unusual days, pricing, hours and customers, plus the long-term forecast and a data explorer.")
    imgs = images(len(full), full)
    t1, t2, t3, t4, t5, t6, t7 = st.tabs(["Daily spikes", "Pricing", "Cancellation hours", "Suspicious customers",
                                          "Ratings & fares", "Forecast", "Data Explorer"])
    with t1:
        daily = L.daily_series(df)
        c1, c2 = st.columns([1, 3])
        with c1:
            metric = st.selectbox("Metric", ["rides", "revenue", "cancel_rate"], key="in_metric")
            thr = st.slider("Sensitivity (z-score)", 1.0, 3.5, 2.0, 0.1, key="in_thr")
        z = L.zscore_flags(daily, metric, thr)
        bad = z[z["anomaly"]]
        with c2:
            fig = px.line(z, x="Ride_Date", y=metric, title=f"Daily {metric}: unusual days highlighted")
            fig.add_scatter(x=bad["Ride_Date"], y=bad[metric], mode="markers", name="Unusual day",
                            marker=dict(color=ORANGE, size=12))
            show(fig)
        st.dataframe(bad[["Ride_Date", metric, "z_score"]].assign(z_score=bad["z_score"].round(3)), hide_index=True)
        ts = L.trend_stats(daily, "rides")
        if ts:
            st.caption(f"Trend check: daily rides change by {ts['pct_per_day'] * 100:+.3f}% a day "
                       f"(t = {ts['t_stat']:.2f}, {'significant' if ts['significant'] else 'not significant'}).")
    with t2:
        ppk = L.price_per_km_table(df)
        vehicle_cards(ppk, imgs, lambda r: f"₹{r['Revenue per km']:.1f}/km", lambda r: r["Flag"])
        show(px.bar(ppk, x="Vehicle_Type", y="Revenue per km", color="Flag", text_auto=".1f",
                    color_discrete_map={"Review pricing": ORANGE, "Normal": CYAN}, title="Revenue per km by vehicle type (₹)"))
        table(ppk, imgs)
    with t3:
        h = L.hourly_cancellation(df)
        h["Cancel rate %"] = (h["Cancel rate"] * 100).round(2)
        h["Unusual"] = h["z_score"].abs() >= 2
        show(px.bar(h, x="Hour", y="Cancel rate %", color="Unusual",
                    color_discrete_map={True: ORANGE, False: CYAN}, title="Cancellation rate by hour"))
        st.dataframe(h[h["Unusual"]][["Hour", "Bookings", "Cancelled", "Cancel rate %", "z_score"]].round(2), hide_index=True)
    with t4:
        n = st.slider("Minimum cancelled bookings", 2, 6, 3, key="in_min_cancel")
        sc = L.suspicious_customers(df, n)
        st.caption(f"{len(sc):,} customers with at least {n} cancelled bookings (possible abuse or fraud; review manually).")
        sc_show = sc.assign(**{"Cancel share": (sc["Cancel share"] * 100).round(1)}).rename(columns={"Cancel share": "Cancel share %"})
        st.dataframe(sc_show, hide_index=True)
    with t5:
        c1, c2 = st.columns(2)
        with c1:
            g = L.rating_gaps(df)
            st.metric("Rides where driver and customer ratings differ by 1.5+", f"{len(g):,}")
            table(g.head(200), imgs)
        with c2:
            f = L.fare_outliers(df)
            st.metric("Unusually high fares (above Q3 + 1.5 x IQR)", f"{len(f):,}")
            table(f.head(200), imgs)
    with t6:
        tab_forecast(df)
    with t7:
        tab_explorer(df)


def page_recommendations(df, full, conn):
    hero("Business Recommendations", "Actions ranked by priority, each backed by numbers from the selected data.")
    recs = L.recommendations(df)
    imgs = images(len(full), full)
    for r in recs:
        uri = imgs.get(r.get("vehicle", ""), "")
        badge = f'<span class="rbadge"><img src="{html.escape(uri, quote=True)}" alt=""></span>' if uri else ""
        st.markdown(
            f'<div class="rec"><span class="pill {html.escape(r["priority"])}">{html.escape(r["priority"].upper())}</span>'
            f'<h4>{badge}{html.escape(r["title"])}</h4>'
            f'<div class="row"><b>Evidence:</b> {html.escape(r["evidence"])}</div>'
            f'<div class="row"><b>Action:</b> {html.escape(r["action"])}</div>'
            f'<div class="row"><b>Impact:</b> {html.escape(r["impact"])}</div></div>', unsafe_allow_html=True)
    section("Impact calculator", "What if the company recovers part of its lost bookings?")
    k = L.kpis(df)
    c1, c2 = st.columns(2)
    with c1:
        rec_pct = st.slider("Share of lost bookings recovered", 0, 50, 10, 5, format="%d%%")
    gain = k["lost_value"] * rec_pct / 100
    with c2:
        st.metric("Extra booking value in this period", L.inr(gain), f"+{gain / k['revenue'] * 100:.1f}% vs current revenue" if k["revenue"] else "")
    md = "# Ola Ride Insights: business recommendations\n\n" + "\n\n".join(
        f"## {i + 1}. {r['title']} ({r['priority']})\n- Evidence: {r['evidence']}\n- Action: {r['action']}\n- Impact: {r['impact']}"
        for i, r in enumerate(recs))
    st.download_button("Download recommendations (Markdown)", md.encode("utf-8"),
                       file_name="ola_recommendations.md", mime="text/markdown")


def tab_forecast(df):
    st.markdown("#### Forecast: where does the business end up in 5 to 10 years?")
    base = L.baseline(df)
    daily = L.daily_series(df)
    ts = L.trend_stats(daily, "rides")
    st.markdown(
        f'<div class="note"><b>Read this first.</b> The data covers only {base["days"]} days, so it cannot show real growth or '
        'seasonality. This page is a <b>scenario projection</b>: it takes the current monthly run-rate and compounds '
        'the assumptions you choose. The growth numbers below are assumptions, not predictions from the data.</div>',
        unsafe_allow_html=True)
    st.write("")
    if ts:
        verdict = "no significant trend" if not ts["significant"] else "a statistically significant trend"
        st.caption(f"Within the data: daily rides move {ts['pct_per_day'] * 100:+.3f}% per day ({verdict}). "
                   "So 'if things continue this way' means a flat run-rate.")

    kpi_row([("Monthly bookings", f"{base['rides']:,.0f}", "current run-rate", ""),
             ("Monthly revenue", L.inr(base["monthly_revenue"]), "successful rides", "good"),
             ("Unsuccessful bookings", L.pct(base["unsuccess_rate"]), "cancelled + no driver", "bad"),
             ("Average fare", f"₹{base['avg_fare']:,.0f}", "", "")])

    section("Your scenario")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        g = st.slider("Ride growth per year", -10, 30, 8, 1, format="%d%%", key="fc_g") / 100
    with c2:
        f = st.slider("Fare growth per year", 0, 12, 4, 1, format="%d%%", key="fc_f") / 100
    with c3:
        top = max(1, int(round(base["unsuccess_rate"] * 100)))
        target = st.slider("Unsuccessful bookings target", 0, top,
                           min(top, int(round(base["unsuccess_rate"] * 65))), 1, format="%d%%", key="fc_t") / 100
    with c4:
        ramp = st.slider("Years to reach target", 1, 10, 3, key="fc_r")
    horizon = st.radio("Horizon", [5, 10], index=1, horizontal=True, format_func=lambda y: f"{y} years", key="fc_h")

    scenarios = L.default_scenarios(base)
    scenarios["Your scenario"] = dict(ride_growth=g, fare_growth=f, target_unsuccess=target, ramp_years=float(ramp))
    results = {n: L.project(base, years=10, **p)[1] for n, p in scenarios.items()}

    yr = results["Your scenario"]
    end = yr[yr["Year"] == horizon].iloc[0]
    flat = results[list(scenarios)[0]]
    flat_end = flat[flat["Year"] == horizon].iloc[0]
    kpi_row([(f"Revenue in year {horizon}", L.inr(end["Revenue"]), f"vs {L.inr(flat_end['Revenue'])} if flat", "good"),
             (f"Total revenue, {horizon} years", L.inr(end["Cumulative revenue"]),
              f"{L.inr(end['Cumulative revenue'] - flat_end['Cumulative revenue'])} more than flat", "good"),
             (f"Bookings in year {horizon}", f"{end['Bookings']:,.0f}", f"vs {flat_end['Bookings']:,.0f} if flat", ""),
             (f"Lost revenue in year {horizon}", L.inr(end["Lost revenue"]), f"vs {L.inr(flat_end['Lost revenue'])} if flat", "bad")])

    long = pd.concat([r.assign(Scenario=n) for n, r in results.items()])
    long = long[long["Year"] <= horizon]
    c1, c2 = st.columns(2)
    with c1:
        show(px.line(long, x="Year", y="Cumulative revenue", color="Scenario", markers=True,
                     title="Cumulative revenue by scenario (₹)"))
    with c2:
        show(px.bar(long, x="Year", y="Revenue", color="Scenario", barmode="group", title="Revenue per year (₹)"))
    show(px.line(long, x="Year", y="Lost revenue", color="Scenario", markers=True,
                 title="Revenue lost to cancellations and unserved bookings, per year (₹)"))

    section("Year-by-year table (your scenario)")
    t = yr[yr["Year"] <= horizon].copy()
    t["Unsuccessful rate"] = (t["Unsuccessful rate"] * 100).round(1)
    t = t.rename(columns={"Unsuccessful rate": "Unsuccessful % (end of year)"})
    for col in ["Bookings", "Successful rides", "Revenue", "Lost revenue", "Cumulative revenue"]:
        t[col] = t[col].round(0)
    st.dataframe(t, hide_index=True)
    st.download_button("Download forecast (CSV)", t.to_csv(index=False).encode("utf-8"),
                       file_name="ola_forecast.csv", mime="text/csv", key="fc_dl")
    st.caption("Method: monthly bookings compound at the ride growth rate; revenue = bookings x success rate x average fare; "
               "fares compound at the fare growth rate; the unsuccessful rate moves in a straight line to your target. "
               "Replace the sliders with your company's own assumptions before presenting any figure as a forecast.")


def tab_explorer(df):
    st.markdown("#### Data Explorer")
    st.caption("Search, filter and download the cleaned data.")
    c1, c2 = st.columns([2, 3])
    with c1:
        q = st.text_input("Search Booking ID, customer or location", key="ex_q")
    with c2:
        default_cols = ["Date", "Booking_ID", "Booking_Status", "Customer_ID", "Vehicle_Type", "Pickup_Location",
                        "Drop_Location", "Booking_Value", "Payment_Method", "Ride_Distance", "Driver_Ratings", "Customer_Rating"]
        cols = st.multiselect("Columns", list(df.columns), default=[c for c in default_cols if c in df.columns], key="ex_cols")
    view = df
    if q.strip():
        mask = np.zeros(len(df), dtype=bool)
        for c in ["Booking_ID", "Customer_ID", "Pickup_Location", "Drop_Location"]:
            mask |= df[c].astype(str).str.contains(q.strip(), case=False, regex=False).to_numpy()
        view = df[mask]
    st.caption(f"{len(view):,} rows match (showing the first 2,000).")
    st.dataframe(view[cols].head(2000) if cols else view.head(2000), hide_index=True)
    sig = f"{q}|{','.join(cols)}|{len(view)}"
    if st.button("Prepare CSV download", key="ex_prep"):
        st.session_state["ex_csv"] = (sig, to_csv_bytes(view[cols] if cols else view))
    ready = st.session_state.get("ex_csv")
    if ready and ready[0] == sig:
        st.download_button("Download filtered data (CSV)", ready[1], file_name="ola_filtered.csv",
                           mime="text/csv", key="ex_dl")
    with st.expander("Summary statistics"):
        st.dataframe(view.describe().round(2))


def page_about(df, full, conn):
    hero("About & Data Quality", "How the data was cleaned and how this app works.", img="ola_logo")
    st.markdown(
        "**Project:** Ola Ride Insights: SQL, Power BI and Streamlit analysis of ride-sharing data.\n\n"
        "**Pipeline:** raw CSV, then cleaning in pandas, then SQL queries (SQLite here; MySQL for the project database), "
        "then a Power BI dashboard, then this Streamlit app.\n\n"
        "**Cleaning steps:** the text `null` became a real missing value; dates and numbers were typed correctly; "
        "blank reason and payment columns were labelled `Not Applicable` / `No Payment`; the placeholder distance of 0 on "
        "cancelled bookings was set to missing; duplicate Booking IDs were removed; Hour, Day, Weekday, Is_Weekend and "
        "Time_Bucket were added.")
    section("Missing values left on purpose")
    miss = df.isna().sum()
    miss = miss[miss > 0].rename("Missing rows").reset_index().rename(columns={"index": "Column"})
    miss["Share of rows"] = (miss["Missing rows"] / len(df) * 100).round(1).astype(str) + "%"
    miss["Why"] = "Booking did not become a ride, so no value exists. Kept empty so averages stay correct."
    st.dataframe(miss, hide_index=True)
    section("Data dictionary")
    dd = pd.DataFrame({"Column": df.columns, "Type": [str(t) for t in df.dtypes],
                       "Example": [str(df[c].dropna().iloc[0]) if df[c].notna().any() else "" for c in df.columns]})
    st.dataframe(dd, hide_index=True, height=420)


PAGES = {
    "Overview": page_overview,
    "Overall": page_overall,
    "Vehicle Type": page_vehicle,
    "Revenue": page_revenue,
    "Cancellation": page_cancellation,
    "Ratings": page_ratings,
    "SQL Queries": page_sql,
    "Power BI Dashboard": page_powerbi,
    "Insights & Anomalies": page_insights,
    "Recommendations": page_recommendations,
    "About & Data Quality": page_about,
}


def make_page(fn, slug, df, full, conn):
    def _run():
        fn(df, full, conn)
    _run.__name__ = f"page_{slug}"
    _run.__qualname__ = f"page_{slug}"
    return _run


def main() -> None:
    st.sidebar.divider()                      # the page menu is drawn above this by st.navigation
    full = get_data()
    df = sidebar_filters(full)
    conn = get_conn(f"{len(full)}-{full['Date'].min()}-{full['Date'].max()}", full)
    pages = []
    for i, (title, fn) in enumerate(PAGES.items()):
        slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
        pages.append(st.Page(make_page(fn, slug, df, full, conn), title=title, url_path=slug, default=(i == 0)))
    st.navigation(pages).run()
    logo = asset_uri("ola_logo.png")
    if logo:
        st.sidebar.markdown(f'<div class="sidelogo"><img src="{html.escape(logo, quote=True)}" alt="Ola"></div>',
                            unsafe_allow_html=True)
    st.sidebar.caption("Built with Python, SQL, Power BI and Streamlit.")
    st.sidebar.caption("DEGINED BY - ⍻⍿икαи")

if __name__ == "__main__":
    main()
