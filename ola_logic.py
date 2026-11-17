"""
ola_logic.py - data, SQL, insight and forecast logic for the Ola Ride Insights app.

Pure pandas / numpy / sqlite3 (no Streamlit), so every function can be tested on
its own. app.py only handles the user interface.
"""
from __future__ import annotations

import base64
import io
import re
import sqlite3
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import numpy as np
import pandas as pd

SUCCESS = "Success"
CANCEL_STATUSES = ("Canceled by Customer", "Canceled by Driver")
NOT_APPLICABLE = "Not Applicable"
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
TABLE_NAME = "ola_rides"

REQUIRED_COLUMNS = [
    "Date", "Booking_ID", "Booking_Status", "Customer_ID", "Vehicle_Type",
    "Pickup_Location", "Drop_Location", "Booking_Value", "Ride_Distance",
]
LABEL_FILL = {
    "Canceled_Rides_by_Customer": NOT_APPLICABLE,
    "Canceled_Rides_by_Driver": NOT_APPLICABLE,
    "Incomplete_Rides": NOT_APPLICABLE,
    "Incomplete_Rides_Reason": NOT_APPLICABLE,
    "Payment_Method": "No Payment",
}
NUMERIC_COLS = ["V_TAT", "C_TAT", "Booking_Value", "Ride_Distance",
                "Driver_Ratings", "Customer_Rating"]


# --------------------------------------------------------------------------
# Formatting helpers
# --------------------------------------------------------------------------
def inr(x) -> str:
    """Format a rupee amount in Indian units (Cr = crore, L = lakh)."""
    if x is None or pd.isna(x):
        return "-"
    a = abs(float(x))
    sign = "-" if x < 0 else ""
    if a >= 1e7:
        return f"{sign}₹{a / 1e7:,.2f} Cr"
    if a >= 1e5:
        return f"{sign}₹{a / 1e5:,.2f} L"
    return f"{sign}₹{a:,.0f}"


def pct(x, digits: int = 1) -> str:
    return "-" if x is None or pd.isna(x) else f"{x * 100:.{digits}f}%"


def safe_div(a, b):
    return float(a) / float(b) if b else 0.0


# --------------------------------------------------------------------------
# Loading and cleaning (works for the raw CSV or the already-cleaned CSV)
# --------------------------------------------------------------------------
def clean_raw(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the project's cleaning steps. Safe to run on already-clean data."""
    df = df.copy()
    df.columns = [str(c).strip().replace(" ", "_") for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    df = df.replace("null", np.nan)                     # text "null" -> real NaN
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    if "Time" in df.columns:
        df["Time"] = df["Time"].astype("string")
    for c in NUMERIC_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    for c, label in LABEL_FILL.items():
        if c in df.columns:
            df[c] = df[c].fillna(label)
    # Distance 0 on rides that never happened is a placeholder, not a real distance
    df.loc[df["Booking_Status"] != SUCCESS, "Ride_Distance"] = np.nan
    df = df.drop_duplicates(subset="Booking_ID")

    df["Ride_Date"] = df["Date"].dt.normalize()
    df["Hour"] = df["Date"].dt.hour
    df["Day"] = df["Date"].dt.day
    df["Weekday"] = df["Date"].dt.day_name()
    df["Is_Weekend"] = df["Date"].dt.dayofweek >= 5
    df["Time_Bucket"] = pd.cut(
        df["Hour"], [-1, 5, 11, 16, 20, 23],
        labels=["Night", "Morning", "Afternoon", "Evening", "Late Night"],
    ).astype(str)
    return df.reset_index(drop=True)


def load_csv(path_or_buffer) -> pd.DataFrame:
    return clean_raw(pd.read_csv(path_or_buffer, na_values=["null"]))


# --------------------------------------------------------------------------
# KPIs and common aggregates
# --------------------------------------------------------------------------
def kpis(df: pd.DataFrame) -> dict:
    ok = df[df["Booking_Status"] == SUCCESS]
    total = len(df)
    cust = int((df["Booking_Status"] == "Canceled by Customer").sum())
    drv = int((df["Booking_Status"] == "Canceled by Driver").sum())
    nf = int((df["Booking_Status"] == "Driver Not Found").sum())
    revenue = float(ok["Booking_Value"].sum())
    lost = float(df.loc[df["Booking_Status"] != SUCCESS, "Booking_Value"].sum())
    return {
        "total": total, "success": len(ok), "cust_cancel": cust, "drv_cancel": drv,
        "not_found": nf, "cancelled": cust + drv,
        "success_rate": safe_div(len(ok), total),
        "cancel_rate": safe_div(cust + drv, total),
        "not_found_rate": safe_div(nf, total),
        "revenue": revenue, "lost_value": lost,
        "avg_fare": safe_div(revenue, len(ok)),
        "avg_distance": float(ok["Ride_Distance"].mean()) if len(ok) else 0.0,
        "avg_driver_rating": float(ok["Driver_Ratings"].mean()) if len(ok) else 0.0,
        "avg_customer_rating": float(ok["Customer_Rating"].mean()) if len(ok) else 0.0,
        "incomplete": int((ok["Incomplete_Rides"] == "Yes").sum()),
        "unique_customers": int(df["Customer_ID"].nunique()),
        "days": int(df["Ride_Date"].nunique()),
    }


def daily_series(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("Ride_Date")
    out = pd.DataFrame({
        "rides": g.size(),
        "success": g["Booking_Status"].apply(lambda s: (s == SUCCESS).sum()),
        "cancelled": g["Booking_Status"].apply(lambda s: s.isin(CANCEL_STATUSES).sum()),
    })
    out["revenue"] = df[df["Booking_Status"] == SUCCESS].groupby("Ride_Date")["Booking_Value"].sum()
    out["revenue"] = out["revenue"].fillna(0)
    out["cancel_rate"] = out["cancelled"] / out["rides"]
    return out.reset_index()


def hour_weekday_matrix(df: pd.DataFrame) -> pd.DataFrame:
    m = df.pivot_table(index="Weekday", columns="Hour", values="Booking_ID",
                       aggfunc="count", fill_value=0)
    return m.reindex([d for d in WEEKDAYS if d in m.index])


def reason_counts(df: pd.DataFrame, column: str) -> pd.DataFrame:
    s = df.loc[df[column] != NOT_APPLICABLE, column]
    out = s.value_counts().rename_axis("Reason").reset_index(name="Rides")
    return out


IMG_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif")
_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}


def _norm(text: str) -> str:
    """Lower-case letters and digits only, so 'Prime plus', 'Prime_plus' and 'E-bike' / 'eBike' match."""
    return re.sub(r"[^a-z0-9]+", "", str(text).lower())


def list_images(folder) -> dict:
    """{normalised file name: Path} for every image in the folder (empty if the folder is missing)."""
    p = Path(folder) if folder else None
    if p is None or not p.is_dir():
        return {}
    out = {}
    for f in sorted(p.iterdir()):
        if f.is_file() and f.suffix.lower() in IMG_EXT:
            out.setdefault(_norm(f.stem), f)
    return out


def find_image(lib: dict, key: str, exact: bool = True) -> Optional[Path]:
    """Find an image by name. exact=False also accepts a file whose name contains the key."""
    k = str(key)
    if k.lower().endswith(IMG_EXT):
        k = k.rsplit(".", 1)[0]
    k = _norm(k)
    if not k:
        return None
    if k in lib:
        return lib[k]
    if not exact:
        for name, path in lib.items():
            if k in name:
                return path
    return None


def image_data_uri(path, max_px: Optional[int] = None) -> Optional[str]:
    """Read a local image as a data URI (works offline). Large files are shrunk to max_px for speed."""
    p = Path(path)
    mime = _MIME.get(p.suffix.lower())
    if not p.is_file() or mime is None:
        return None
    raw = p.read_bytes()
    if max_px:
        try:
            from PIL import Image
            with Image.open(io.BytesIO(raw)) as im:
                if max(im.size) > max_px:
                    small = im.convert("RGBA")
                    small.thumbnail((max_px, max_px))
                    buf = io.BytesIO()
                    small.save(buf, "PNG", optimize=True)
                    raw, mime = buf.getvalue(), "image/png"
        except Exception:
            pass
    return f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")


def vehicle_image_map(df: pd.DataFrame, assets_dir=None) -> dict:
    """Vehicle_Type -> image. Files in your logo folder win; otherwise the https flaticon link in the data."""
    out = {}
    if "Vehicle_Images" in df.columns:
        pairs = df[["Vehicle_Type", "Vehicle_Images"]].dropna().drop_duplicates("Vehicle_Type")
        for vtype, url in zip(pairs["Vehicle_Type"], pairs["Vehicle_Images"]):
            try:
                p = urlparse(str(url).strip())
            except ValueError:
                continue
            host = (p.hostname or "").lower()
            if p.scheme == "https" and (host == "flaticon.com" or host.endswith(".flaticon.com")):
                out[vtype] = str(url).strip()
    lib = list_images(assets_dir)
    for vtype in df["Vehicle_Type"].dropna().unique():
        path = find_image(lib, vtype)               # 'eBike' finds E-bike.png, 'Prime Plus' finds Prime plus.png
        uri = image_data_uri(path, 160) if path else None
        if uri:
            out[vtype] = uri
    return out


def vehicle_summary(df: pd.DataFrame) -> pd.DataFrame:
    ok = df[df["Booking_Status"] == SUCCESS]
    g = df.groupby("Vehicle_Type")
    out = pd.DataFrame({
        "Bookings": g.size(),
        "Cancelled": g["Booking_Status"].apply(lambda s: s.isin(CANCEL_STATUSES).sum()),
    })
    out["Cancel %"] = out["Cancelled"] / out["Bookings"] * 100
    og = ok.groupby("Vehicle_Type")
    out["Success rides"] = og.size()
    out["Total distance (km)"] = og["Ride_Distance"].sum()
    out["Avg distance (km)"] = og["Ride_Distance"].mean()
    out["Revenue"] = og["Booking_Value"].sum()
    out["Revenue per km"] = out["Revenue"] / out["Total distance (km)"]
    out["Avg driver rating"] = og["Driver_Ratings"].mean()
    out["Avg customer rating"] = og["Customer_Rating"].mean()
    return out.reset_index().round(2)


# --------------------------------------------------------------------------
# SQL (SQLite engine over the cleaned data)
# --------------------------------------------------------------------------
def make_connection(df: pd.DataFrame) -> sqlite3.Connection:
    d = df.copy()
    d["Date"] = d["Date"].dt.strftime("%Y-%m-%d %H:%M:%S")
    d["Ride_Date"] = d["Ride_Date"].dt.strftime("%Y-%m-%d")
    d["Is_Weekend"] = d["Is_Weekend"].astype(int)
    for c in d.columns:
        if str(d[c].dtype) in ("string", "str"):
            d[c] = d[c].astype(object).where(d[c].notna(), None)
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    d.to_sql(TABLE_NAME, conn, index=False)
    return conn


_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum|"
    r"reindex|truncate|grant|revoke|load_extension)\b", re.IGNORECASE)


def validate_select(query: str) -> str:
    """Allow one read-only SELECT / WITH statement. Returns the cleaned query."""
    q = (query or "").strip()
    q = re.sub(r"--[^\n]*", "", q)                      # strip line comments
    q = re.sub(r"/\*.*?\*/", "", q, flags=re.DOTALL)    # strip block comments
    q = q.strip().rstrip(";").strip()
    if not q:
        raise ValueError("Write a query first.")
    if ";" in q:
        raise ValueError("Only one statement at a time is allowed.")
    if not re.match(r"^(select|with)\b", q, re.IGNORECASE):
        raise ValueError("Only SELECT queries are allowed in the playground.")
    if _FORBIDDEN.search(q):
        raise ValueError("This playground is read-only: data-changing keywords are blocked.")
    return q


def run_sql(conn: sqlite3.Connection, query: str, max_rows: int = 5000,
            timeout_s: float = 10.0) -> tuple[pd.DataFrame, float, bool]:
    """Run a read-only query. Returns (dataframe, seconds, truncated)."""
    q = validate_select(query)
    deadline = time.time() + timeout_s

    def _guard():
        return 1 if time.time() > deadline else 0

    conn.execute("PRAGMA query_only = ON")
    conn.set_progress_handler(_guard, 20000)
    start = time.time()
    try:
        cur = conn.execute(q)
        cols = [c[0] for c in cur.description] if cur.description else []
        rows = cur.fetchmany(max_rows + 1)
    except sqlite3.OperationalError as exc:
        msg = str(exc)
        if "interrupted" in msg:
            msg = f"Query stopped after {timeout_s:.0f}s. Add a WHERE or LIMIT."
        raise ValueError(msg) from exc
    finally:
        conn.set_progress_handler(None, 0)
    truncated = len(rows) > max_rows
    return pd.DataFrame(rows[:max_rows], columns=cols), time.time() - start, truncated


T = TABLE_NAME
PROJECT_QUERIES = {
    "Q1. All successful bookings": f"SELECT *\nFROM {T}\nWHERE Booking_Status = 'Success'\nLIMIT 1000;",
    "Q2. Average ride distance by vehicle type": (
        f"SELECT Vehicle_Type, ROUND(AVG(Ride_Distance), 2) AS avg_distance_km\n"
        f"FROM {T}\nWHERE Booking_Status = 'Success'\nGROUP BY Vehicle_Type\nORDER BY avg_distance_km DESC;"),
    "Q3. Total rides cancelled by customers": (
        f"SELECT COUNT(*) AS cancelled_by_customer\nFROM {T}\nWHERE Booking_Status = 'Canceled by Customer';"),
    "Q4. Top 5 customers by number of rides": (
        f"SELECT Customer_ID, COUNT(*) AS total_rides\nFROM {T}\nGROUP BY Customer_ID\n"
        f"ORDER BY total_rides DESC\nLIMIT 5;"),
    "Q5. Driver cancellations: personal and car issues": (
        f"SELECT COUNT(*) AS personal_car_issue\nFROM {T}\n"
        f"WHERE Canceled_Rides_by_Driver = 'Personal & Car related issue';"),
    "Q6. Max and min driver rating, Prime Sedan": (
        f"SELECT MAX(Driver_Ratings) AS max_rating, MIN(Driver_Ratings) AS min_rating\nFROM {T}\n"
        f"WHERE Vehicle_Type = 'Prime Sedan' AND Booking_Status = 'Success';"),
    "Q7. Rides paid by UPI": f"SELECT *\nFROM {T}\nWHERE Payment_Method = 'UPI'\nLIMIT 1000;",
    "Q8. Average customer rating per vehicle type": (
        f"SELECT Vehicle_Type, ROUND(AVG(Customer_Rating), 2) AS avg_customer_rating\nFROM {T}\n"
        f"WHERE Booking_Status = 'Success'\nGROUP BY Vehicle_Type\nORDER BY avg_customer_rating DESC;"),
    "Q9. Total booking value of successful rides": (
        f"SELECT SUM(Booking_Value) AS total_booking_value\nFROM {T}\nWHERE Booking_Status = 'Success';"),
    "Q10. Incomplete rides with reason": (
        f"SELECT Booking_ID, Vehicle_Type, Incomplete_Rides_Reason\nFROM {T}\n"
        f"WHERE Incomplete_Rides = 'Yes'\nLIMIT 1000;"),
}

BUSINESS_QUERIES = {
    "B1. Cancellation rate by vehicle type": (
        f"SELECT Vehicle_Type, COUNT(*) AS total_bookings,\n"
        f"       SUM(Booking_Status LIKE 'Canceled%') AS cancelled,\n"
        f"       ROUND(100.0 * SUM(Booking_Status LIKE 'Canceled%') / COUNT(*), 1) AS cancel_pct\n"
        f"FROM {T}\nGROUP BY Vehicle_Type\nORDER BY cancel_pct DESC;"),
    "B2. Peak demand hours (top 5)": (
        f"SELECT Hour, COUNT(*) AS bookings\nFROM {T}\nGROUP BY Hour\nORDER BY bookings DESC\nLIMIT 5;"),
    "B3. Unmet demand: Driver Not Found by pickup area": (
        f"SELECT Pickup_Location, COUNT(*) AS no_driver_found\nFROM {T}\n"
        f"WHERE Booking_Status = 'Driver Not Found'\nGROUP BY Pickup_Location\n"
        f"ORDER BY no_driver_found DESC\nLIMIT 10;"),
    "B4. Booking value lost to failed bookings": (
        f"SELECT Booking_Status, COUNT(*) AS rides, SUM(Booking_Value) AS lost_value\nFROM {T}\n"
        f"WHERE Booking_Status <> 'Success'\nGROUP BY Booking_Status;"),
    "B5. Revenue per km by vehicle type": (
        f"SELECT Vehicle_Type, ROUND(SUM(Booking_Value) * 1.0 / SUM(Ride_Distance), 2) AS value_per_km\n"
        f"FROM {T}\nWHERE Booking_Status = 'Success'\nGROUP BY Vehicle_Type\nORDER BY value_per_km DESC;"),
    "B6. Repeat customers (more than one successful ride)": (
        f"SELECT COUNT(*) AS repeat_customers\nFROM (SELECT Customer_ID\n      FROM {T}\n"
        f"      WHERE Booking_Status = 'Success'\n      GROUP BY Customer_ID\n"
        f"      HAVING COUNT(*) > 1) t;"),
    "B7. Payment method share of successful rides": (
        f"SELECT Payment_Method, COUNT(*) AS rides,\n"
        f"       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct\nFROM {T}\n"
        f"WHERE Booking_Status = 'Success'\nGROUP BY Payment_Method\nORDER BY rides DESC;"),
    "B8. Top 5 pickup locations by revenue": (
        f"SELECT Pickup_Location, SUM(Booking_Value) AS revenue\nFROM {T}\n"
        f"WHERE Booking_Status = 'Success'\nGROUP BY Pickup_Location\nORDER BY revenue DESC\nLIMIT 5;"),
    "B9. Low-rated drivers (below 3.5) by vehicle type": (
        f"SELECT Vehicle_Type, SUM(Driver_Ratings < 3.5) AS low_rated,\n"
        f"       COUNT(Driver_Ratings) AS rated_rides\nFROM {T}\nGROUP BY Vehicle_Type\n"
        f"ORDER BY low_rated DESC;"),
    "B10. Highest revenue days": (
        f"SELECT Ride_Date, SUM(Booking_Value) AS revenue\nFROM {T}\n"
        f"WHERE Booking_Status = 'Success'\nGROUP BY Ride_Date\nORDER BY revenue DESC\nLIMIT 5;"),
}


# --------------------------------------------------------------------------
# Insights and anomalies
# --------------------------------------------------------------------------
def zscore_flags(df: pd.DataFrame, col: str, threshold: float = 2.0) -> pd.DataFrame:
    d = df.copy()
    sd = d[col].std(ddof=0)
    d["z_score"] = (d[col] - d[col].mean()) / sd if sd else 0.0
    d["anomaly"] = d["z_score"].abs() >= threshold
    return d


def price_per_km_table(df: pd.DataFrame) -> pd.DataFrame:
    ok = df[df["Booking_Status"] == SUCCESS]
    g = ok.groupby("Vehicle_Type")
    out = pd.DataFrame({"Revenue": g["Booking_Value"].sum(), "Distance (km)": g["Ride_Distance"].sum()})
    out["Revenue per km"] = out["Revenue"] / out["Distance (km)"].replace(0, np.nan)
    med = out["Revenue per km"].median()
    out["Times the median"] = out["Revenue per km"] / med if med else np.nan
    out["Flag"] = np.where(out["Times the median"] >= 1.5, "Review pricing", "Normal")
    return out.reset_index().round(2).sort_values("Revenue per km", ascending=False)


def suspicious_customers(df: pd.DataFrame, min_cancels: int = 3) -> pd.DataFrame:
    d = df.assign(is_cancel=df["Booking_Status"].isin(CANCEL_STATUSES))
    g = d.groupby("Customer_ID")
    out = pd.DataFrame({"Bookings": g.size(), "Cancelled": g["is_cancel"].sum(),
                        "Value at risk": d[d["is_cancel"]].groupby("Customer_ID")["Booking_Value"].sum()})
    out["Cancel share"] = out["Cancelled"] / out["Bookings"]
    out = out[out["Cancelled"] >= min_cancels].fillna(0)
    return out.reset_index().sort_values(["Cancelled", "Value at risk"], ascending=False)


def hourly_cancellation(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("Hour")
    out = pd.DataFrame({"Bookings": g.size(),
                        "Cancelled": g["Booking_Status"].apply(lambda s: s.isin(CANCEL_STATUSES).sum())})
    out["Cancel rate"] = out["Cancelled"] / out["Bookings"]
    sd = out["Cancel rate"].std(ddof=0)
    out["z_score"] = (out["Cancel rate"] - out["Cancel rate"].mean()) / sd if sd else 0.0
    return out.reset_index()


def rating_gaps(df: pd.DataFrame, gap: float = 1.5) -> pd.DataFrame:
    ok = df[df["Booking_Status"] == SUCCESS].copy()
    ok["Rating gap"] = (ok["Driver_Ratings"] - ok["Customer_Rating"]).abs()
    return ok[ok["Rating gap"] >= gap][
        ["Booking_ID", "Vehicle_Type", "Driver_Ratings", "Customer_Rating", "Rating gap"]
    ].sort_values("Rating gap", ascending=False)


def fare_outliers(df: pd.DataFrame) -> pd.DataFrame:
    ok = df[df["Booking_Status"] == SUCCESS].copy()
    q1, q3 = ok["Booking_Value"].quantile([0.25, 0.75])
    upper = q3 + 1.5 * (q3 - q1)
    return ok[ok["Booking_Value"] > upper][
        ["Booking_ID", "Vehicle_Type", "Ride_Distance", "Booking_Value"]
    ].sort_values("Booking_Value", ascending=False)


# --------------------------------------------------------------------------
# Business recommendations (every number comes from the filtered data)
# --------------------------------------------------------------------------
def recommendations(df: pd.DataFrame) -> list[dict]:
    k = kpis(df)
    if k["total"] == 0:
        return []
    recs: list[dict] = []
    drv_share = safe_div(k["drv_cancel"], k["cancelled"])
    avg_lost = safe_div(df.loc[df["Booking_Status"] == "Canceled by Driver", "Booking_Value"].sum(),
                        k["drv_cancel"])

    drv_reasons = reason_counts(df, "Canceled_Rides_by_Driver")
    top_drv = drv_reasons.iloc[0] if len(drv_reasons) else None
    recs.append({
        "priority": "High", "title": "Reduce driver-side cancellations",
        "evidence": (f"Drivers cancel {k['drv_cancel']:,} rides, {pct(drv_share, 0)} of all cancellations."
                     + (f" Top reason: {top_drv['Reason']} ({int(top_drv['Rides']):,} rides)." if top_drv is not None else "")),
        "action": "Add acceptance incentives and a penalty ladder for repeat cancellers. Check vehicle fitness before shifts.",
        "impact": f"Recovering 10% of driver cancellations is worth about {inr(0.10 * k['drv_cancel'] * avg_lost)} a month.",
        "value": 0.10 * k["drv_cancel"] * avg_lost,
    })

    nf = df[df["Booking_Status"] == "Driver Not Found"]
    top_nf = nf["Pickup_Location"].value_counts().head(3)
    avg_nf = safe_div(nf["Booking_Value"].sum(), len(nf))
    recs.append({
        "priority": "High", "title": "Close the driver supply gaps",
        "evidence": (f"{pct(k['not_found_rate'])} of bookings ({k['not_found']:,}) found no driver. Worst areas: "
                     + ", ".join(f"{a} ({b})" for a, b in top_nf.items()) + "."),
        "action": "Pre-position drivers and add zone-based incentives in these pickup areas, mainly at peak hours.",
        "impact": f"Serving 25% of these bookings adds about {inr(0.25 * k['not_found'] * avg_nf)} a month.",
        "value": 0.25 * k["not_found"] * avg_nf,
    })

    cust_reasons = reason_counts(df, "Canceled_Rides_by_Customer")
    if len(cust_reasons):
        top_c = cust_reasons.head(2)
        recs.append({
            "priority": "Medium", "title": "Fix the reasons customers cancel",
            "evidence": "Top customer cancellation reasons: " + "; ".join(
                f"{r.Reason} ({int(r.Rides):,})" for r in top_c.itertuples()) + ".",
            "action": "Show accurate pickup ETAs, alert drivers who are not heading to the pickup point, and run AC and cleanliness checks.",
            "impact": f"Each 10% fewer customer cancellations protects about {inr(0.10 * k['cust_cancel'] * safe_div(df.loc[df['Booking_Status'] == 'Canceled by Customer', 'Booking_Value'].sum(), k['cust_cancel']))} a month.",
            "value": 0.10 * k["cust_cancel"] * safe_div(
                df.loc[df["Booking_Status"] == "Canceled by Customer", "Booking_Value"].sum(), k["cust_cancel"]),
        })

    hours = df.groupby("Hour").size().sort_values(ascending=False).head(3)
    recs.append({
        "priority": "Medium", "title": "Match driver supply to peak hours",
        "evidence": "Busiest hours: " + ", ".join(f"{h}:00 ({n:,})" for h, n in hours.items()) + ".",
        "action": "Schedule driver shifts and surge pricing around these hours, and pull idle drivers to hot zones.",
        "impact": "Lowers 'Driver Not Found' and waiting time at the busiest times.", "value": 0.0,
    })

    ok = df[df["Booking_Status"] == SUCCESS]
    pay = ok["Payment_Method"].value_counts(normalize=True)
    cash = float(pay.get("Cash", 0))
    recs.append({
        "priority": "Medium", "title": "Move cash riders to digital payments",
        "evidence": f"Cash is {pct(cash)} of successful rides; UPI is {pct(float(pay.get('UPI', 0)))}.",
        "action": "Offer small UPI cashback and wallet offers on first digital rides. This also cuts cash handling and disputes.",
        "impact": "Faster settlement and fewer payment disputes.", "value": 0.0,
    })

    ppk = price_per_km_table(df)
    if len(ppk) and ppk.iloc[0]["Times the median"] >= 1.5:
        r = ppk.iloc[0]
        recs.append({
            "priority": "Medium", "title": f"Review {r['Vehicle_Type']} pricing", "vehicle": r["Vehicle_Type"],
            "evidence": f"{r['Vehicle_Type']} earns {inr(r['Revenue per km'])} per km, {r['Times the median']:.1f}x the median vehicle type.",
            "action": "Check the fare rules and surge settings for this vehicle type; confirm the numbers are correct and fair.",
            "impact": "Avoids customer complaints or revenue leakage from a pricing error.", "value": 0.0,
        })

    inc = safe_div(k["incomplete"], k["success"])
    inc_r = ok.loc[ok["Incomplete_Rides"] == "Yes", "Incomplete_Rides_Reason"].value_counts()
    if len(inc_r):
        recs.append({
            "priority": "Low", "title": "Cut incomplete rides",
            "evidence": f"{pct(inc)} of successful bookings end incomplete. Top reason: {inc_r.index[0]} ({int(inc_r.iloc[0]):,}).",
            "action": "Schedule vehicle maintenance checks and give drivers clearer trip-completion prompts.",
            "impact": "Higher completed-ride revenue and better ratings.", "value": 0.0,
        })

    low = ok[ok["Driver_Ratings"] < 3.5]
    low_share = safe_div(len(low), len(ok))
    worst = low["Vehicle_Type"].value_counts()
    recs.append({
        "priority": "Low", "title": "Coach low-rated drivers",
        "evidence": f"{pct(low_share)} of rated rides have a driver rating below 3.5." + (f" Most in {worst.index[0]}." if len(worst) else ""),
        "action": "Run short driver-training modules and tie incentives to a rating floor.",
        "impact": "Better ratings and repeat bookings.", "value": 0.0,
    })

    cust = ok.groupby("Customer_ID").size()
    repeat = safe_div((cust > 1).sum(), len(cust))
    recs.append({
        "priority": "Low", "title": "Build customer retention",
        "evidence": f"Only {pct(repeat)} of customers with a successful ride booked more than once ({int((cust > 1).sum()):,} customers).",
        "action": "Launch a loyalty or ride-pack program and send reminder offers after a first successful ride.",
        "impact": "Repeat riders are cheaper to keep than new riders are to acquire.", "value": 0.0,
    })
    return recs


# --------------------------------------------------------------------------
# Forecast: scenario projection, NOT a statistical prediction
# --------------------------------------------------------------------------
def trend_stats(daily: pd.DataFrame, col: str = "rides") -> Optional[dict]:
    y = daily[col].to_numpy(dtype=float)
    if len(y) < 7:
        return None
    x = np.arange(len(y), dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (slope * x + intercept)
    denom = ((x - x.mean()) ** 2).sum()
    se = np.sqrt((resid ** 2).sum() / (len(y) - 2) / denom) if denom else 0.0
    t = slope / se if se else 0.0
    return {"slope_per_day": float(slope), "pct_per_day": float(slope / y.mean()),
            "t_stat": float(t), "significant": bool(abs(t) > 2), "days": len(y)}


def baseline(df: pd.DataFrame) -> dict:
    """Monthly run-rate of the selected data (scaled to a 30.4-day month)."""
    k = kpis(df)
    factor = safe_div(30.4375, k["days"]) if k["days"] else 0.0
    nonsucc = df[df["Booking_Status"] != SUCCESS]
    return {
        "rides": k["total"] * factor,
        "unsuccess_rate": 1 - k["success_rate"],
        "avg_fare": k["avg_fare"],
        "avg_lost_fare": safe_div(nonsucc["Booking_Value"].sum(), len(nonsucc)),
        "cancel_rate": k["cancel_rate"],
        "monthly_revenue": k["revenue"] * factor,
        "days": k["days"],
    }


def project(base: dict, years: int = 10, ride_growth: float = 0.0, fare_growth: float = 0.0,
            target_unsuccess: Optional[float] = None, ramp_years: float = 3.0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compound the monthly run-rate forward. Returns (monthly, yearly) tables."""
    months = np.arange(1, years * 12 + 1)
    t = months / 12.0
    rides = base["rides"] * (1 + ride_growth) ** t
    start = base["unsuccess_rate"]
    end = start if target_unsuccess is None else target_unsuccess
    unsucc = start + (end - start) * np.minimum(t / max(ramp_years, 1e-9), 1.0)
    fare_f = (1 + fare_growth) ** t
    success_rides = rides * (1 - unsucc)
    revenue = success_rides * base["avg_fare"] * fare_f
    lost = rides * unsucc * base["avg_lost_fare"] * fare_f
    monthly = pd.DataFrame({"Month": months, "Year": (months - 1) // 12 + 1, "Bookings": rides,
                            "Successful rides": success_rides, "Revenue": revenue,
                            "Lost revenue": lost, "Unsuccessful rate": unsucc})
    yearly = monthly.groupby("Year").agg({"Bookings": "sum", "Successful rides": "sum",
                                          "Revenue": "sum", "Lost revenue": "sum",
                                          "Unsuccessful rate": "last"}).reset_index()
    yearly["Cumulative revenue"] = yearly["Revenue"].cumsum()
    return monthly, yearly


def default_scenarios(base: dict) -> dict:
    cut = max(base["unsuccess_rate"] * 0.65, 0.0)
    return {
        "Status quo (flat)": dict(ride_growth=0.0, fare_growth=0.0, target_unsuccess=None),
        "Steady growth (8% / 4%)": dict(ride_growth=0.08, fare_growth=0.04, target_unsuccess=None),
        "Growth + fix cancellations": dict(ride_growth=0.08, fare_growth=0.04, target_unsuccess=cut),
    }
