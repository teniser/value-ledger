import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, time

import pandas as pd
import plotly.graph_objects as go
import pytz
import requests
import streamlit as st
import yfinance as yf


# ---------- STRAN IN VIDEZ ----------
st.set_page_config(
    page_title="The Value Ledger 2.0 · Terminal",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@300;400;500;600&display=swap');

html, body, [class*="css"], .stApp {
    background-color: #06070B !important;
    font-family: 'Plus Jakarta Sans', -apple-system, sans-serif !important;
    color: #E2E8F0 !important;
    -webkit-font-smoothing: antialiased;
}
section[data-testid="stSidebar"] {
    background-color: #0A0D14 !important;
    border-right: 1px solid rgba(255,255,255,0.05) !important;
}
.ledger-card {
    background: rgba(13,17,28,0.7);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 22px 26px;
    margin-bottom: 20px;
    backdrop-filter: blur(16px);
}
.mndy-hero-card {
    background: linear-gradient(145deg, rgba(20,17,10,0.8), rgba(10,9,6,0.9));
    border: 1.5px solid rgba(245,158,11,0.6);
    border-radius: 18px;
    padding: 24px 26px;
    margin-bottom: 22px;
}
.badge-sector {
    font-family: 'Space Grotesk', sans-serif;
    font-size: .7rem;
    padding: 3px 8px;
    border-radius: 6px;
    background: rgba(255,255,255,.04);
    border: 1px solid rgba(255,255,255,.08);
    color: #94A3B8;
    text-transform: uppercase;
}
.aplus-badge {
    display: inline-flex;
    border: 1.2px solid #F59E0B;
    color: #FBBF24;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
    font-size: .76rem;
    padding: 3px 12px;
    border-radius: 9999px;
}
.metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit,minmax(130px,1fr));
    gap: 12px;
    margin: 16px 0;
    padding: 14px 18px;
    background: rgba(0,0,0,.25);
    border-radius: 12px;
}
.metric-label {
    color: #94A3B8;
    font-size: .7rem;
    text-transform: uppercase;
    font-family: 'Space Grotesk', sans-serif;
}
.metric-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1rem;
    color: #F8FAFC;
}
div.stButton > button {
    background: linear-gradient(135deg,#F59E0B,#D97706) !important;
    color: #0A0D14 !important;
    font-weight: 600 !important;
    font-family: 'Space Grotesk',sans-serif !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 12px 24px !important;
}
</style>""", unsafe_allow_html=True)


# ---------- UNIVERZUM ----------
# To je seznam za skeniranje, ne celoten borzni trg.
AI_UNIVERSE = list(dict.fromkeys("""
MNDY CRWD SNOW HUBS DELL DDOG TEAM NOW PANW PLTR
NVDA AAPL MSFT META AMZN GOOGL AVGO AMD TSM NFLX
ORCL CRM ADBE MU QCOM ARM SHOP NET ZS OKTA MDB ESTC
COIN HOOD SMCI ANET MRVL FTNT AI PATH SNPS CDNS APP
ANSS NOW IBM CSCO INTU WDAY ADSK ACN VEEV TEAM
KLAC LRCX AMAT ASML ON NXPI TXN ADI MCHP
MRNA ISRG TTD RBLX UBER DASH ABNB MELI SE
SQ PYPL AFRM SOFI DKNG RDDT SPOT DUOL
CAVA CELH ELF LULU COST WMT TGT HD LOW
GE CAT DE ETN PWR CEG VST NEE
XOM CVX COP SLB
JPM GS MS BAC SCHW BLK
RACE FICO V MA
DOCU ZM TWLO FSLY GDDY WIX
FSLR ENPH
GTLB CFLT IOT INTA TENB S CYBR
RIVN LCID
""".split()))


# Delnice, ki so že prikazane na osnovnih karticah in primerjalnem grafu.
TICKERS_CONFIG = {
    "MNDY": {
        "name": "monday.com",
        "sector": "SaaS / Work OS",
        "category": "Na opazovanju",
        "sentiment": 9.1, "makro": 8.5, "temelji": 9.2, "podcenjenost": 9.5,
    },
    "CRWD": {
        "name": "CrowdStrike",
        "sector": "Kibernetska varnost",
        "category": "Na opazovanju",
        "sentiment": 9.5, "makro": 8.5, "temelji": 9.5, "podcenjenost": 6.5,
    },
    "SNOW": {
        "name": "Snowflake",
        "sector": "AI podatki",
        "category": "Na opazovanju",
        "sentiment": 8.2, "makro": 8.3, "temelji": 8.7, "podcenjenost": 6.8,
    },
    "HUBS": {
        "name": "HubSpot",
        "sector": "CRM / Marketing",
        "category": "Na opazovanju",
        "sentiment": 7.7, "makro": 7.0, "temelji": 8.5, "podcenjenost": 8.0,
    },
    "DELL": {
        "name": "Dell Technologies",
        "sector": "AI strojna oprema",
        "category": "Na opazovanju",
        "sentiment": 8.0, "makro": 8.2, "temelji": 8.4, "podcenjenost": 8.5,
    },
    "DDOG": {
        "name": "Datadog",
        "sector": "Cloud",
        "category": "Na opazovanju",
        "sentiment": 7.9, "makro": 8.0, "temelji": 9.1, "podcenjenost": 5.8,
    },
    "TEAM": {
        "name": "Atlassian",
        "sector": "Razvojna orodja",
        "category": "Na opazovanju",
        "sentiment": 7.0, "makro": 7.5, "temelji": 8.8, "podcenjenost": 5.5,
    },
    "NOW": {
        "name": "ServiceNow",
        "sector": "Enterprise",
        "category": "Na opazovanju",
        "sentiment": 6.8, "makro": 8.5, "temelji": 9.8, "podcenjenost": 4.5,
    },
    "PANW": {
        "name": "Palo Alto Networks",
        "sector": "Kibernetska varnost",
        "category": "Na opazovanju",
        "sentiment": 6.5, "makro": 8.5, "temelji": 9.0, "podcenjenost": 3.8,
    },
    "PLTR": {
        "name": "Palantir",
        "sector": "AI platforma",
        "category": "Na opazovanju",
        "sentiment": 5.2, "makro": 9.4, "temelji": 9.6, "podcenjenost": 2.1,
    },
}

NY_TZ = pytz.timezone("America/New_York")
LJ_TZ = pytz.timezone("Europe/Ljubljana")


# ---------- SPLOŠNI PRIPOMOČKI ----------
def as_float(value):
    try:
        if value is None or pd.isna(value):
            return None
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def fmt(value, suffix="", digits=2):
    if value is None:
        return "ni podatka"
    return f"{value:.{digits}f}{suffix}"


def find_statement_row(statement, possible_names):
    if not isinstance(statement, pd.DataFrame) or statement.empty:
        return None

    labels = {str(label).strip().lower(): label for label in statement.index}
    for candidate in possible_names:
        label = labels.get(candidate.strip().lower())
        if label is not None:
            return statement.loc[label]

    for label in statement.index:
        actual = str(label).strip().lower()
        if any(candidate.strip().lower() in actual for candidate in possible_names):
            return statement.loc[label]

    return None


@st.cache_data(ttl=900, show_spinner=False)
def get_ticker_info(ticker):
    try:
        result = yf.Ticker(ticker).info
        return result if isinstance(result, dict) else {}
    except Exception:
        return {}


@st.cache_data(ttl=300, show_spinner=False)
def get_history(ticker, period="5d", interval="5m", prepost=False):
    try:
        frame = yf.Ticker(ticker).history(
            period=period,
            interval=interval,
            auto_adjust=False,
            prepost=prepost,
        )
        if frame is None or frame.empty:
            return pd.DataFrame()
        needed = ["Open", "High", "Low", "Close", "Volume"]
        if any(column not in frame.columns for column in needed):
            return pd.DataFrame()
        return frame.dropna(subset=needed)
    except Exception:
        return pd.DataFrame()


def get_market_regime():
    try:
        frame = get_history("SPY", "6mo", "1d", False)
        if frame.empty or len(frame) < 60:
            return {"regime": "NEZNANO", "spy_20d_pct": None, "penalty": 0.0}

        close = frame["Close"].astype(float)
        last = float(close.iloc[-1])
        sma50 = float(close.rolling(50).mean().iloc[-1])
        change20 = (last / float(close.iloc[-21]) - 1) * 100

        if last > sma50 and change20 > -3:
            regime, penalty = "RISK-ON", 0.0
        elif last < sma50 and change20 < -3:
            regime, penalty = "RISK-OFF", 0.8
        else:
            regime, penalty = "NEVTRALNO", 0.3

        return {
            "regime": regime,
            "spy_20d_pct": round(change20, 2),
            "penalty": penalty,
        }
    except Exception:
        return {"regime": "NEZNANO", "spy_20d_pct": None, "penalty": 0.0}


market = get_market_regime()


# ---------- DOLGOROČNI LONG: PODATKI IN OCENA ----------
def get_liquidity_metrics(info):
    market_cap = as_float(info.get("marketCap"))
    price = as_float(info.get("currentPrice") or info.get("regularMarketPrice"))
    avg_volume = as_float(
        info.get("averageVolume") or info.get("averageDailyVolume10Day")
    )

    dollar_volume = price * avg_volume if price and avg_volume else None
    eligible = (
        market_cap is not None
        and market_cap >= 2_000_000_000
        and dollar_volume is not None
        and dollar_volume >= 20_000_000
    )
    return market_cap, dollar_volume, eligible


def get_wall_street_metrics(info, price):
    recommendation = as_float(info.get("recommendationMean"))
    analyst_count = as_float(info.get("numberOfAnalystOpinions"))
    target_price = as_float(info.get("targetMeanPrice"))

    target_upside = None
    if target_price and price and price > 0:
        target_upside = (target_price / price - 1) * 100

    # Yahoo recommendationMean: približno 1 = Strong Buy, 5 = Sell.
    score = None
    if recommendation is not None and 1 <= recommendation <= 5:
        score = max(0.0, min(10.0, 10 - (recommendation - 1) * 2.5))

    return {
        "ws_score": round(score, 1) if score is not None else None,
        "recommendation": recommendation,
        "analyst_count": int(analyst_count) if analyst_count is not None else None,
        "target_upside_pct": (
            round(target_upside, 1) if target_upside is not None else None
        ),
    }


@st.cache_data(ttl=86400, show_spinner=False)
def get_historical_ps_metrics(ticker):
    """
    Ocena zgodovinskega P/S. Za zgodovinsko tržno kapitalizacijo uporablja
    trenutno število delnic, zato je približek, ne uradna zgodovinska mera.
    """
    empty = {
        "historical_ps_median": None,
        "current_vs_median_pct": None,
        "samples": 0,
        "method": "ni dovolj podatkov",
    }

    try:
        stock = yf.Ticker(ticker)
        income = stock.quarterly_income_stmt
        balance = stock.balance_sheet

        revenue_row = find_statement_row(
            income, ["Total Revenue", "Operating Revenue"]
        )
        if revenue_row is None:
            return empty

        revenue = pd.to_numeric(revenue_row, errors="coerce").dropna().sort_index()
        if len(revenue) < 4:
            return empty

        info = get_ticker_info(ticker)
        current_price = as_float(
            info.get("currentPrice") or info.get("regularMarketPrice")
        )
        current_market_cap = as_float(info.get("marketCap"))
        current_revenue = as_float(info.get("totalRevenue"))

        if not current_price or not current_market_cap or not current_revenue:
            return empty

        current_shares = current_market_cap / current_price
        if current_shares <= 0:
            return empty

        prices = stock.history(period="5y", interval="1d", auto_adjust=False)
        if prices is None or prices.empty:
            return empty

        prices = prices.copy()
        prices.index = pd.to_datetime(prices.index)
        if prices.index.tz is not None:
            prices.index = prices.index.tz_localize(None)

        revenue.index = pd.to_datetime(revenue.index)
        if revenue.index.tz is not None:
            revenue.index = revenue.index.tz_localize(None)

        cutoff = pd.Timestamp.now().normalize() - pd.Timedelta(days=365 * 3)
        samples = []

        for report_date in revenue.index:
            if report_date < cutoff:
                continue

            trailing_revenue = as_float(revenue.loc[:report_date].tail(4).sum())
            if not trailing_revenue or trailing_revenue <= 0:
                continue

            available_prices = prices.loc[prices.index <= report_date]
            if available_prices.empty:
                continue

            historical_price = as_float(available_prices["Close"].iloc[-1])
            if historical_price is None or historical_price <= 0:
                continue

            estimated_market_cap = historical_price * current_shares
            estimated_ps = estimated_market_cap / trailing_revenue

            if 0 < estimated_ps < 100:
                samples.append((report_date, estimated_ps))

        if len(samples) < 6:
            return {
                **empty,
                "samples": len(samples),
                "method": "premalo četrtletnih vzorcev",
            }

        median_ps = float(pd.Series([value for _, value in samples]).median())
        current_ps = current_market_cap / current_revenue
        comparison = (current_ps / median_ps - 1) * 100 if median_ps > 0 else None

        return {
            "historical_ps_median": round(median_ps, 2),
            "current_vs_median_pct": round(comparison, 1) if comparison is not None else None,
            "samples": len(samples),
            "method": "ocena; zgodovinsko število delnic ni na voljo",
        }
    except Exception:
        return empty


@st.cache_data(ttl=86400, show_spinner=False)
def get_quarterly_fcf_metrics(ticker):
    try:
        cashflow = yf.Ticker(ticker).quarterly_cashflow
        if not isinstance(cashflow, pd.DataFrame) or cashflow.empty:
            return {"fcf_ttm": None, "fcf_trend_pct": None}

        fcf_row = find_statement_row(cashflow, ["Free Cash Flow"])
        if fcf_row is not None:
            fcf = pd.to_numeric(fcf_row, errors="coerce").dropna().sort_index()
        else:
            operating = find_statement_row(
                cashflow,
                [
                    "Operating Cash Flow",
                    "Cash Flow From Continuing Operating Activities",
                ],
            )
            capex = find_statement_row(
                cashflow, ["Capital Expenditure", "Capital Expenditures"]
            )
            if operating is None or capex is None:
                return {"fcf_ttm": None, "fcf_trend_pct": None}

            operating = pd.to_numeric(operating, errors="coerce")
            capex = pd.to_numeric(capex, errors="coerce")
            # Capex je v Yahoo tabelah pogosto že negativen.
            fcf = (operating + capex).dropna().sort_index()

        if len(fcf) < 4:
            return {"fcf_ttm": None, "fcf_trend_pct": None}

        ttm_series = []
        for end in range(3, len(fcf)):
            ttm_series.append(float(fcf.iloc[end - 3:end + 1].sum()))

        latest_ttm = ttm_series[-1]
        trend = None
        if len(ttm_series) >= 5 and abs(ttm_series[-5]) > 0:
            trend = (latest_ttm / abs(ttm_series[-5]) - 1) * 100

        return {
            "fcf_ttm": round(latest_ttm, 2),
            "fcf_trend_pct": round(trend, 1) if trend is not None else None,
        }
    except Exception:
        return {"fcf_ttm": None, "fcf_trend_pct": None}


def score_low_is_good(value, excellent, good, fair, poor):
    if value <= excellent:
        return 10.0
    if value <= good:
        return 8.0
    if value <= fair:
        return 6.0
    if value <= poor:
        return 4.0
    return 2.0


def score_high_is_good(value, poor, fair, good, excellent):
    if value >= excellent:
        return 10.0
    if value >= good:
        return 8.0
    if value >= fair:
        return 6.0
