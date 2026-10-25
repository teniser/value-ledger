import html
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st
import yfinance as yf


# ============================================================
# NASTAVITVE IN VIDEZ
# ============================================================

st.set_page_config(
    page_title="The Value Ledger 2.0 Terminal",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
    html, body, [class*="css"], .stApp {
        background:#06070B !important;
        color:#E2E8F0 !important;
        font-family:'Plus Jakarta Sans',sans-serif !important;
    }
    section[data-testid="stSidebar"] {
        background:#0A0D14 !important;
        border-right:1px solid rgba(255,255,255,.06);
    }
    h1, h2, h3, h4 {
        font-family:'Space Grotesk',sans-serif !important;
    }
    .hero-long {
        background:linear-gradient(145deg,rgba(48,34,10,.72),rgba(13,17,28,.96));
        border:1px solid rgba(245,158,11,.58);
        border-radius:18px;
        padding:20px 24px;
        min-height:220px;
    }
    .hero-reversal {
        background:linear-gradient(145deg,rgba(9,43,39,.75),rgba(13,17,28,.96));
        border:1px solid rgba(16,185,129,.48);
        border-radius:18px;
        padding:20px 24px;
        min-height:220px;
    }
    .ledger-card {
        background:linear-gradient(145deg,#0D111C,#090B12);
        border:1px solid rgba(255,255,255,.08);
        border-radius:16px;
        padding:20px 24px;
        margin:8px 0 18px;
    }
    div.stButton > button {
        background:linear-gradient(135deg,#F59E0B 0%,#D97706 100%) !important;
        color:#0A0D14 !important;
        font-weight:700 !important;
        border:none !important;
        border-radius:10px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

NY_TZ = ZoneInfo("America/New_York")
LJ_TZ = ZoneInfo("Europe/Ljubljana")
MIN_MARKET_CAP = 2_000_000_000
MIN_DOLLAR_VOLUME = 20_000_000


# ============================================================
# SEKTORSKI UNIVERZUM
# ============================================================

SECTOR_GROUPS = {
    "SaaS / Software": [
        "MNDY", "SNOW", "HUBS", "DDOG", "TEAM", "NOW", "CRM", "ADBE",
        "SHOP", "NET", "ZS", "OKTA", "MDB", "ESTC", "PATH", "WDAY",
        "CFLT", "DOCN", "GTLB", "BILL", "ASAN", "IOT", "FSLY", "DT",
        "BSY", "PCOR", "NCNO", "ZM", "DOCU", "TWLO", "PD", "DBX",
        "SMAR", "UPWK", "SPT", "APPN", "PEGA", "FROG", "RNG", "VEEV",
        "TYL", "PTC", "ADSK", "TRMB",
    ],
    "Cybersecurity": [
        "CRWD", "PANW", "CHKP", "CYBR", "TENB", "VRNS",
        "QLYS", "FTNT", "AKAM", "VRSN", "GEN", "S",
    ],
    "Semiconductors / Hardware": [
        "NVDA", "AVGO", "AMD", "TSM", "MU", "QCOM", "ARM", "SMCI",
        "ANET", "MRVL", "SNPS", "CDNS", "ANSS", "ALAB", "LITE",
        "COHR", "VRT", "NTNX", "PSTG", "STX", "WDC", "TXN", "ADI",
        "NXPI", "MCHP", "ON", "INTC", "ASML", "AMAT", "LRCX", "KLAC",
        "DELL", "CSCO", "HPE", "HPQ", "GLW", "TER", "KEYS",
    ],
    "Large Tech / Internet": [
        "AAPL", "MSFT", "META", "AMZN", "GOOGL", "NFLX", "TSLA",
        "UBER", "ABNB", "DASH", "SPOT", "RBLX", "TTD", "ROKU",
        "PINS", "SNAP", "MTCH", "DKNG", "LYFT", "EBAY",
    ],
    "Financials / Fintech": [
        "COIN", "HOOD", "XYZ", "PYPL", "SOFI", "AFRM", "MELI",
        "SE", "NU", "V", "MA", "GLBE", "JPM", "GS", "MS", "C",
        "BAC", "SCHW", "ICE", "CME",
    ],
    "Healthcare": [
        "ISRG", "DXCM", "PODD", "EXAS", "ILMN", "ALGN", "MDT",
        "SYK", "BSX", "ABT", "VRTX", "REGN", "LLY", "NVO", "UNH",
    ],
    "Industrials": [
        "CAT", "DE", "ETN", "GE", "HON", "PH", "RTX", "LMT",
    ],
    "Energy": ["XOM", "CVX", "SLB", "FSLR", "ENPH", "NXT"],
    "Consumer": [
        "COST", "WMT", "HD", "LOW", "MCD", "NKE", "KO", "PG",
        "F", "GM", "RIVN", "LCID", "CVNA", "UPST", "Z", "W",
    ],
}

AI_UNIVERSE = []
_max_sector_size = max(len(group) for group in SECTOR_GROUPS.values())

for index in range(_max_sector_size):
    for group in SECTOR_GROUPS.values():
        if index < len(group) and group[index] not in AI_UNIVERSE:
            AI_UNIVERSE.append(group[index])

AI_UNIVERSE = AI_UNIVERSE[:150]

SECTOR_ETF = {
    "SaaS / Software": "IGV",
    "Cybersecurity": "CIBR",
    "Semiconductors / Hardware": "SMH",
    "Large Tech / Internet": "QQQ",
    "Financials / Fintech": "XLF",
    "Healthcare": "XLV",
    "Industrials": "XLI",
    "Energy": "XLE",
    "Consumer": "XLY",
}

SECTOR_MULTIPLE = {
    "SaaS / Software": "P/S",
    "Cybersecurity": "P/S",
    "Semiconductors / Hardware": "EV/EBITDA",
    "Large Tech / Internet": "EV/EBITDA",
    "Financials / Fintech": "P/B",
    "Healthcare": "EV/EBITDA",
    "Industrials": "EV/EBITDA",
    "Energy": "EV/EBITDA",
    "Consumer": "EV/EBITDA",
}

KNOWN_NAMES = {
    "MNDY": "monday.com",
    "CRWD": "CrowdStrike",
    "TSM": "Taiwan Semiconductor Manufacturing",
    "FTNT": "Fortinet",
    "NOW": "ServiceNow",
    "PANW": "Palo Alto Networks",
    "PLTR": "Palantir",
    "DDOG": "Datadog",
    "TEAM": "Atlassian",
    "SNOW": "Snowflake",
    "HUBS": "HubSpot",
    "DELL": "Dell Technologies",
}


def sector_for(ticker):
    for sector, members in SECTOR_GROUPS.items():
        if ticker in members:
            return sector
    return "Other / unclassified"


# ============================================================
# POMOŽNE FUNKCIJE
# ============================================================

def safe_float(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def fmt(value, digits=2, suffix=""):
    if value is None:
        return "—"
    try:
        return f"{float(value):,.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return "—"


def render_table(frame):
    if frame is None or frame.empty:
        st.info("Ni podatkov za prikaz.")
    else:
        st.dataframe(frame, use_container_width=True, hide_index=True)


def get_statement_row(frame, names):
    if frame is None or frame.empty:
        return None

    normalized = {
        str(index).strip().lower().replace("_", " "): index
        for index in frame.index
    }

    for name in names:
        key = name.strip().lower().replace("_", " ")
        if key in normalized:
            return frame.loc[normalized[key]]

    for key, original in normalized.items():
        if any(name.strip().lower().replace("_", " ") in key for name in names):
            return frame.loc[original]

    return None


def annual_values(frame, names):
    row = get_statement_row(frame, names)
    if row is None:
        return {}

    output = {}
    for column, raw_value in row.items():
        value = safe_float(raw_value)
        if value is not None:
            try:
                output[pd.Timestamp(column).year] = value
            except Exception:
                continue
    return output


def midrank_percentile(values, target, lower_is_better=False):
    valid = [
        value for value in values
        if value is not None and math.isfinite(value)
    ]
    if target is None or len(valid) < 5:
        return None

    below = sum(value < target for value in valid)
    equal = sum(value == target for value in valid)
    percentile = (below + 0.5 * equal) / len(valid) * 100

    if lower_is_better:
        percentile = 100 - percentile

    return round(max(0.0, min(100.0, percentile)))


def get_eps_revision_metrics(ticker_obj):
    """EPS-revizije analitikov, kadar jih Yahoo Finance posreduje."""
    net_revisions = None
    estimate_change = None

    try:
        revisions = ticker_obj.eps_revisions
    except Exception:
        revisions = None

    if revisions is not None and not revisions.empty:
        columns = {
            str(column).lower().replace("_", ""): column
            for column in revisions.columns
        }
        up_col = columns.get("uplast30days")
        down_col = columns.get("downlast30days")

        if up_col is not None and down_col is not None:
            selected = []
            for index, row in revisions.iterrows():
                label = str(index).lower().replace(" ", "")
                if "0q" in label or "+1q" in label or "1q" in label:
                    selected.append(row)

            if not selected:
                selected = [row for _, row in revisions.iterrows()]

            ups = sum(safe_float(row.get(up_col)) or 0 for row in selected)
            downs = sum(
                safe_float(row.get(down_col)) or 0
                for row in selected
            )
            if ups or downs:
                net_revisions = int(round(ups - downs))

    try:
        trend = ticker_obj.eps_trend
    except Exception:
        trend = None

    if trend is not None and not trend.empty:
        columns = {
            str(column).lower().replace("_", ""): column
            for column in trend.columns
        }
        current_col = columns.get("current")
        old_col = columns.get("30daysago")

        if current_col is not None and old_col is not None:
            selected = []
            for index, row in trend.iterrows():
                label = str(index).lower().replace(" ", "")
                if "0q" in label or "+1q" in label or "1q" in label:
                    selected.append(row)

            if not selected:
                selected = [row for _, row in trend.iterrows()]

            changes = []
            for row in selected:
                current = safe_float(row.get(current_col))
                old = safe_float(row.get(old_col))
                if current is not None and old not in (None, 0):
                    changes.append((current / old - 1) * 100)

            if changes:
                estimate_change = sum(changes) / len(changes)

    return {
        "eps_revision_net_30d": net_revisions,
        "eps_estimate_change_30d_pct": estimate_change,
    }


# ============================================================
# TRŽNI REŽIM IN SEKTORSKA ROTACIJA
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def get_market_regime():
    try:
        frame = yf.Ticker("SPY").history(
            period="6mo",
            interval="1d",
            auto_adjust=True,
        )
        if frame is None or len(frame) < 60:
            return {"regime": "NEZNANO", "change20": None, "penalty": 0.0}

        close = frame["Close"].dropna().astype(float)
        if len(close) < 50:
            return {"regime": "NEZNANO", "change20": None, "penalty": 0.0}

        last = float(close.iloc[-1])
        sma50 = float(close.rolling(50).mean().iloc[-1])
        change20 = (last / float(close.iloc[-21]) - 1) * 100

        if last > sma50 and change20 > -3:
            regime, penalty = "RISK-ON", 0.0
        elif last < sma50 and change20 < -3:
            regime, penalty = "RISK-OFF", 1.0
        else:
            regime, penalty = "NEVTRALNO", 0.5

        return {
            "regime": regime,
            "change20": round(change20, 2),
            "penalty": penalty,
        }
    except Exception:
        return {"regime": "NEZNANO", "change20": None, "penalty": 0.0}


@st.cache_data(ttl=300, show_spinner=False)
def get_rotation():
    etfs = {
        "SaaS / Software": "IGV",
        "Cybersecurity": "CIBR",
        "Semiconductors / Hardware": "SMH",
        "Large Tech / Internet": "QQQ",
        "Financials / Fintech": "XLF",
        "Healthcare": "XLV",
        "Industrials": "XLI",
        "Energy": "XLE",
        "Consumer": "XLY",
        "Osnovna potrošnja": "XLP",
        "Materiali": "XLB",
        "Utilities": "XLU",
        "Small caps": "IWM",
    }

    prices = {}
    for ticker in list(etfs.values()) + ["SPY"]:
        try:
            history = yf.Ticker(ticker).history(
                period="8mo",
                interval="1d",
                auto_adjust=True,
            )
            if history is not None and not history.empty:
                prices[ticker] = history["Close"].dropna().astype(float)
        except Exception:
            continue

    if "SPY" not in prices:
        return {"rows": [], "rotation": "NI PODATKOV", "detail": ""}

    def relative_return(series, benchmark, days):
        joined = pd.concat(
            [
                series.rename("sector"),
                benchmark.rename("spy"),
            ],
            axis=1,
            join="inner",
        ).dropna()

        if len(joined) <= days:
            return None

        sector_return = (
            joined["sector"].iloc[-1]
            / joined["sector"].iloc[-1 - days]
            - 1
        ) * 100
        spy_return = (
            joined["spy"].iloc[-1]
            / joined["spy"].iloc[-1 - days]
            - 1
        ) * 100

        return float(sector_return - spy_return)

    rows = []
    for label, ticker in etfs.items():
        if ticker not in prices:
            continue

        rel5 = relative_return(prices[ticker], prices["SPY"], 5)
        rel20 = relative_return(prices[ticker], prices["SPY"], 20)
        rel60 = relative_return(prices[ticker], prices["SPY"], 60)

        if rel5 is None or rel20 is None or rel60 is None:
            continue

        early_turn = rel5 > 0 and rel20 > 0 and rel60 < 0

        if early_turn:
            status = "MOŽEN ZGODNJI OBRAT"
        elif rel20 > 0 and rel60 > 0:
            status = "RELATIVNO VODI"
        elif rel5 < 0 and rel20 < 0 and rel60 > 0:
            status = "SLABI"
        elif rel20 < 0:
            status = "ZAOSTAJA"
        else:
            status = "MEŠANO"

        rows.append({
            "ETF": ticker,
            "Sektor": label,
            "Rel. 5d % vs SPY": round(rel5, 2),
            "Rel. 20d % vs SPY": round(rel20, 2),
            "Rel. 60d % vs SPY": round(rel60, 2),
            "Zgodnji obrat navzgor": early_turn,
            "Oznaka": status,
        })

    rows.sort(key=lambda row: row["Rel. 20d % vs SPY"], reverse=True)

    rotation = "NI PODATKOV"
    detail = ""

    if "IGV" in prices and "SMH" in prices:
        joined = pd.concat(
            [
                prices["IGV"].rename("igv"),
                prices["SMH"].rename("smh"),
            ],
            axis=1,
            join="inner",
        ).dropna()

        if len(joined) > 60:
            ratio = joined["igv"] / joined["smh"]
            change20 = (ratio.iloc[-1] / ratio.iloc[-21] - 1) * 100
            change60 = (ratio.iloc[-1] / ratio.iloc[-61] - 1) * 100
            above_sma20 = bool(
                ratio.iloc[-1] > ratio.rolling(20).mean().iloc[-1]
            )

            if change20 > 0 and change60 < 0 and above_sma20:
                rotation = "MOŽEN ZAČETEK RELATIVNE ROTACIJE SEMIS → SAAS"
            elif change20 > 0 and change60 > 0 and above_sma20:
                rotation = "SAAS RELATIVNO VODI SEMIS"
            elif change20 < 0 and change60 > 0:
                rotation = "SAAS RELATIVNO SLABI PROTI SEMIS"
            elif change20 < 0 and not above_sma20:
                rotation = "SEMIS RELATIVNO VODI SAAS"
            else:
                rotation = "NI JASNE RELATIVNE ROTACIJE"

            detail = (
                f"IGV/SMH: 20d {change20:+.1f}%, "
                f"60d {change60:+.1f}%; nad SMA20: "
                f"{'DA' if above_sma20 else 'NE'}"
            )

    return {"rows": rows, "rotation": rotation, "detail": detail}


# ============================================================
# PODATKI POSAMEZNE DELNICE
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}

        def number(key):
            return safe_float(info.get(key))

        price = number("currentPrice") or number("regularMarketPrice")
        market_cap = number("marketCap")
        average_volume = number("averageVolume")

        dollar_volume = (
            price * average_volume
            if price is not None and average_volume is not None
            else None
        )

        cash = number("totalCash")
        debt = number("totalDebt")
        net_cash = cash - debt if cash is not None and debt is not None else None

        try:
            cashflow = stock.cashflow
        except Exception:
            cashflow = None

        try:
            income = stock.income_stmt
        except Exception:
            income = None

        cfo = annual_values(
            cashflow,
            [
                "Operating Cash Flow",
                "Total Cash From Operating Activities",
                "Cash Flow From Continuing Operating Activities",
            ],
        )
        capex = annual_values(
            cashflow,
            ["Capital Expenditure", "Capital Expenditures"],
        )
        sbc = annual_values(
            cashflow,
            ["Stock Based Compensation", "Share Based Compensation"],
        )
        net_income = annual_values(
            income,
            [
                "Net Income",
                "Net Income Common Stockholders",
                "Net Income From Continuing Operations",
            ],
        )
        revenue = annual_values(
            income,
            ["Total Revenue", "Operating Revenue", "Revenue"],
        )
        ebitda_values = annual_values(
            income,
            ["EBITDA", "Normalized EBITDA"],
        )

        years = sorted(
            set(cfo) & set(capex) & set(net_income) & set(revenue)
        )[-5:]

        annual = []
        for year in years:
            annual.append({
                "year": year,
                "cfo": cfo[year],
                "fcf": cfo[year] - abs(capex[year]),
                "net_income": net_income[year],
                "revenue": revenue[year],
                "sbc": abs(sbc[year]) if year in sbc else None,
                "ebitda": ebitda_values.get(year),
            })

        annual.sort(key=lambda item: item["year"])
        fcf_years = len(annual)
        positive_fcf_years = sum(item["fcf"] > 0 for item in annual)

        margins = [
            item["fcf"] / item["revenue"] * 100
            for item in annual
            if item["revenue"] > 0
        ]
        conversions = [
            item["cfo"] / item["net_income"]
            for item in annual
            if item["net_income"] > 0
        ]
        sbc_rates = [
            item["sbc"] / item["revenue"] * 100
            for item in annual
            if item["sbc"] is not None and item["revenue"] > 0
        ]

        median_fcf_margin = (
            float(pd.Series(margins).median()) if margins else None
        )
        median_conversion = (
            float(pd.Series(conversions).median()) if conversions else None
        )
        median_sbc = (
            float(pd.Series(sbc_rates).median()) if sbc_rates else None
        )

        growth = number("revenueGrowth")
        if growth is not None and growth > 1:
            growth /= 100
        if len(annual) >= 2 and annual[-2]["revenue"] > 0:
            growth = annual[-1]["revenue"] / annual[-2]["revenue"] - 1

        latest_fcf = annual[-1]["fcf"] if annual else None
        latest_ebitda = annual[-1]["ebitda"] if annual else None
        enterprise_value = number("enterpriseValue")
        ev_ebitda = number("enterpriseToEbitda")

        if (
            (ev_ebitda is None or ev_ebitda <= 0)
            and enterprise_value is not None
            and latest_ebitda is not None
            and latest_ebitda > 0
        ):
            ev_ebitda = enterprise_value / latest_ebitda

        try:
            history = stock.history(
                period="2y",
                interval="1d",
                auto_adjust=True,
            )
        except Exception:
            history = pd.DataFrame()

        close = (
            history["Close"].dropna().astype(float)
            if history is not None
            and not history.empty
            and "Close" in history
            else pd.Series(dtype=float)
        )

        drawdown_52w = None
        return20 = None
        return60 = None
        return120 = None
        above_sma20 = None
