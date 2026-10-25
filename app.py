# app.py
import html
import math
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import pytz
import requests
import streamlit as st
import yfinance as yf

# ============================================================
# PAGE CONFIG + DARK TERMINAL THEME
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
        background-color: #06070B !important;
        color: #E2E8F0 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #0A0D14 !important;
        border-right: 1px solid rgba(255,255,255,0.06);
    }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
        font-family: 'Space Grotesk', sans-serif !important;
        color: #E2E8F0 !important;
    }
    [data-testid="stCaptionContainer"] {
        color: #94A3B8 !important;
    }
    .ledger-card {
        background: linear-gradient(145deg, #0D111C, #090B12);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 20px 24px;
        margin: 8px 0 18px 0;
    }
    .hero-mndy {
        background: linear-gradient(145deg, rgba(48,34,10,0.72), rgba(13,17,28,0.96));
        border: 1px solid rgba(245,158,11,0.55);
        border-radius: 18px;
        padding: 20px 24px;
        min-height: 125px;
    }
    .hero-crwd {
        background: linear-gradient(145deg, rgba(9,43,39,0.75), rgba(13,17,28,0.96));
        border: 1px solid rgba(16,185,129,0.42);
        border-radius: 18px;
        padding: 20px 24px;
        min-height: 125px;
    }
    div.stButton > button {
        background: linear-gradient(135deg,#F59E0B 0%,#D97706 100%) !important;
        color:#0A0D14 !important;
        font-weight:700 !important;
        border:none !important;
        border-radius:10px !important;
        padding:10px 18px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

NY_TZ = ZoneInfo("America/New_York")
LJ_TZ = ZoneInfo("Europe/Ljubljana")

# ============================================================
# UNIVERSE: DEDUPLICATED, LIMITED TO 150 TICKERS
# ============================================================

TICKER_CANDIDATES = [
    # SaaS, software and cloud
    "MNDY", "CRWD", "SNOW", "HUBS", "DDOG", "TEAM", "NOW", "PANW",
    "PLTR", "CRM", "ADBE", "SHOP", "NET", "ZS", "OKTA", "MDB",
    "ESTC", "PATH", "WDAY", "CFLT", "DOCN", "GTLB", "TOST", "BILL",
    "ASAN", "IOT", "FSLY", "DT", "BSY", "PCOR", "NCNO", "ZM",
    "DOCU", "TWLO", "PD", "DBX", "SMAR", "UPWK", "SPT", "APPN",
    "PEGA", "FROG", "RNG", "VEEV", "TYL", "PTC", "ADSK", "TRMB",

    # Large technology and internet
    "AAPL", "MSFT", "META", "AMZN", "GOOGL", "NFLX", "TSLA",
    "UBER", "ABNB", "DASH", "SPOT", "RBLX", "TTD", "ROKU",
    "PINS", "SNAP", "MTCH", "DKNG", "LYFT", "EBAY",

    # Semiconductors, equipment and hardware
    "NVDA", "AVGO", "AMD", "TSM", "MU", "QCOM", "ARM", "SMCI",
    "ANET", "MRVL", "SNPS", "CDNS", "ANSS", "ALAB", "LITE",
    "COHR", "VRT", "NTNX", "PSTG", "STX", "WDC", "TXN", "ADI",
    "NXPI", "MCHP", "ON", "INTC", "ASML", "AMAT", "LRCX",
    "KLAC", "DELL", "CSCO", "HPE", "HPQ", "GLW", "TER", "KEYS",

    # Cybersecurity
    "CHKP", "CYBR", "TENB", "VRNS", "QLYS", "FTNT", "AKAM",
    "VRSN", "GEN", "S",

    # Finance, payments and fintech
    "COIN", "HOOD", "XYZ", "PYPL", "SOFI", "AFRM", "MELI",
    "SE", "NU", "V", "MA", "GLBE", "JPM", "GS", "MS", "C",
    "BAC", "SCHW", "ICE", "CME",

    # Healthcare and medical technology
    "ISRG", "DXCM", "PODD", "EXAS", "ILMN", "ALGN", "MDT",
    "SYK", "BSX", "ABT", "VRTX", "REGN", "LLY", "NVO", "UNH",

    # Industrials, energy, consumer and other sectors
    "CAT", "DE", "ETN", "GE", "HON", "PH", "RTX", "LMT",
    "XOM", "CVX", "SLB", "FSLR", "ENPH", "NXT", "COST",
    "WMT", "HD", "LOW", "MCD", "NKE", "KO", "PG", "F",
    "GM", "RIVN", "LCID", "CVNA", "UPST", "Z", "W",
]

AI_UNIVERSE = list(dict.fromkeys(TICKER_CANDIDATES))[:150]

TICKERS_CONFIG = {
    "MNDY": {"name": "monday.com", "sector": "SaaS"},
    "CRWD": {"name": "CrowdStrike", "sector": "Cybersecurity"},
    "SNOW": {"name": "Snowflake", "sector": "Cloud"},
    "HUBS": {"name": "HubSpot", "sector": "Software"},
    "DELL": {"name": "Dell Technologies", "sector": "Hardware"},
    "DDOG": {"name": "Datadog", "sector": "Cloud"},
    "TEAM": {"name": "Atlassian", "sector": "Software"},
    "NOW": {"name": "ServiceNow", "sector": "Software"},
    "PANW": {"name": "Palo Alto Networks", "sector": "Cybersecurity"},
    "PLTR": {"name": "Palantir", "sector": "Software"},
}

# ============================================================
# HELPERS
# ============================================================

def safe_float(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None

def display_value(value, digits=2, suffix=""):
    if value is None:
        return "—"
    try:
        return f"{float(value):,.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return "—"

def render_dark_table(frame):
    """Render a compact HTML table so the dark theme is consistent."""
    if frame is None or frame.empty:
        st.info("Ni podatkov za prikaz.")
        return

    headers = "".join(
        f"<th>{html.escape(str(column))}</th>" for column in frame.columns
    )
    body_rows = []

    for _, row in frame.iterrows():
        cells = []
        for value in row.tolist():
            if pd.isna(value):
                text = "—"
            else:
                text = str(value)
            cells.append(f"<td>{html.escape(text)}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")

    table_html = f"""
    <div style="overflow-x:auto;border:1px solid #263044;border-radius:10px;
                margin:8px 0 18px 0;">
      <table style="border-collapse:collapse;width:100%;background:#0D111C;
                    color:#CBD5E1;font-size:0.82rem;">
        <thead>
          <tr style="background:#151B29;color:#F8FAFC;">{headers}</tr>
        </thead>
        <tbody>{''.join(body_rows)}</tbody>
      </table>
    </div>
    <style>
      table th, table td {
        border:1px solid #202838;
        padding:8px 10px;
        text-align:left;
        white-space:nowrap;
      }
      table tbody tr:nth-child(even) { background:#101522; }
    </style>
    """
    st.markdown(table_html, unsafe_allow_html=True)

def log_event(kind, ticker, score, detail=""):
    try:
        safe_detail = str(detail).replace(",", ";").replace("\n", " ")
        with open("king_log.csv", "a", encoding="utf-8") as log_file:
            log_file.write(
                f"{datetime.now().isoformat()},{kind},{ticker},{score},{safe_detail}\n"
            )
    except Exception:
        # Logging should not stop the app.
        pass

# ============================================================
# MARKET REGIME AND SECTOR RELATIVE STRENGTH
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def get_market_regime():
    try:
        hist = yf.Ticker("SPY").history(
            period="6mo", interval="1d", auto_adjust=True
        )
        if hist is None or len(hist) < 60:
            return {"regime": "NEZNANO", "spy_chg": None, "penalty": 0.0}

        close = hist["Close"].dropna().astype(float)
        if len(close) < 50:
            return {"regime": "NEZNANO", "spy_chg": None, "penalty": 0.0}

        last = float(close.iloc[-1])
        sma50 = float(close.rolling(50).mean().iloc[-1])
        chg20 = (last / float(close.iloc[-21]) - 1) * 100

        if last > sma50 and chg20 > -3:
            regime, penalty = "RISK-ON", 0.0
        elif last < sma50 and chg20 < -3:
            regime, penalty = "RISK-OFF", 1.0
        else:
            regime, penalty = "NEVTRALNO", 0.5

        return {
            "regime": regime,
            "spy_chg": round(chg20, 2),
            "penalty": penalty,
        }
    except Exception:
        return {"regime": "NEZNANO", "spy_chg": None, "penalty": 0.0}

@st.cache_data(ttl=900, show_spinner=False)
def get_capital_rotation():
    # ETF-ji so približek relativne cenovne moči, ne neposredni tokovi denarja.
    sector_etfs = {
        "SaaS / software (IGV)": "IGV",
        "Semiconductors (SMH)": "SMH",
        "Cybersecurity (CIBR)": "CIBR",
        "Nasdaq (QQQ)": "QQQ",
        "Finance (XLF)": "XLF",
        "Healthcare (XLV)": "XLV",
        "Energy (XLE)": "XLE",
        "Industrials (XLI)": "XLI",
        "Consumer discretionary (XLY)": "XLY",
        "Consumer staples (XLP)": "XLP",
        "Materials (XLB)": "XLB",
        "Utilities (XLU)": "XLU",
        "Small caps (IWM)": "IWM",
    }

    closes = {}
    for ticker in list(sector_etfs.values()) + ["SPY"]:
        try:
            hist = yf.Ticker(ticker).history(
                period="8mo", interval="1d", auto_adjust=True
            )
            if hist is not None and not hist.empty:
                closes[ticker] = hist["Close"].dropna().astype(float)
        except Exception:
            continue

    if "SPY" not in closes:
        return {"rows": [], "pair": "NI PODATKOV", "pair_detail": ""}

    def relative_return(series, benchmark, days):
        joined = pd.concat(
            [series.rename("sector"), benchmark.rename("benchmark")],
            axis=1,
            join="inner",
        ).dropna()
        if len(joined) <= days:
            return None
        sector_return = (
            joined["sector"].iloc[-1] / joined["sector"].iloc[-1 - days] - 1
        ) * 100
        benchmark_return = (
            joined["benchmark"].iloc[-1] / joined["benchmark"].iloc[-1 - days] - 1
        ) * 100
        return float(sector_return - benchmark_return)

    rows = []
    for label, ticker in sector_etfs.items():
        if ticker not in closes:
            continue

        r5 = relative_return(closes[ticker], closes["SPY"], 5)
        r20 = relative_return(closes[ticker], closes["SPY"], 20)
        r60 = relative_return(closes[ticker], closes["SPY"], 60)
        if r5 is None or r20 is None or r60 is None:
            continue

        if r5 > 0 and r20 > 0 and r60 < 0:
            status = "KREPI"
        elif r20 > 0 and r60 > 0:
            status = "RELATIVNO VODI"
        elif r5 < 0 and r20 < 0 and r60 > 0:
            status = "SLABI"
        elif r20 < 0:
            status = "ZAOSTAJA"
        else:
            status = "MEŠANO"

        rows.append({
            "Sektor / ETF": label,
            "Rel. 5d % vs SPY": round(r5, 1),
            "Rel. 20d % vs SPY": round(r20, 1),
            "Rel. 60d % vs SPY": round(r60, 1),
            "Oznaka": status,
        })

    rows.sort(key=lambda row: row["Rel. 20d % vs SPY"], reverse=True)

    pair = "NI PODATKOV"
    detail = ""

    if "IGV" in closes and "SMH" in closes:
        joined = pd.concat(
            [
                closes["IGV"].rename("igv"),
                closes["SMH"].rename("smh"),
            ],
            axis=1,
            join="inner",
        ).dropna()

        if len(joined) > 60:
            ratio = joined["igv"] / joined["smh"]
            p20 = (ratio.iloc[-1] / ratio.iloc[-21] - 1) * 100
            p60 = (ratio.iloc[-1] / ratio.iloc[-61] - 1) * 100
            sma20 = ratio.rolling(20).mean().iloc[-1]
            above_sma20 = bool(ratio.iloc[-1] > sma20)

            if p20 > 0 and p60 < 0 and above_sma20:
                pair = "MOŽEN ZAČETEK RELATIVNE ROTACIJE SEMIS → SAAS"
            elif p20 > 0 and p60 > 0 and above_sma20:
                pair = "SAAS RELATIVNO VODI SEMIS"
            elif p20 < 0 and p60 > 0:
                pair = "SAAS RELATIVNO SLABI PROTI SEMIS"
            elif p20 < 0 and not above_sma20:
                pair = "SEMIS RELATIVNO VODI SAAS"
            else:
                pair = "NI JASNE RELATIVNE ROTACIJE"

            detail = (
                f"IGV/SMH razmerje: 20d {p20:+.1f}%, 60d {p60:+.1f}%; "
                f"nad SMA20: {'DA' if above_sma20 else 'NE'}"
            )

    return {"rows": rows, "pair": pair, "pair_detail": detail}

market = get_market_regime()
rotation = get_capital_rotation()

# ============================================================
# FUNDAMENTAL DATA: TRANSPARENT HEURISTIC, NOT A VERIFIED RANKING
# ============================================================

@st.cache_data(ttl=1800, show_spinner=False)
def get_fundamental_data(ticker):
    try:
        info = yf.Ticker(ticker).info or {}

        def get_num(key):
            return safe_float(info.get(key))

        price = get_num("currentPrice") or get_num("regularMarketPrice")
        market_cap = get_num("marketCap")
        average_volume = get_num("averageVolume")
        ps = get_num("priceToSalesTrailing12Months")
        peg = get_num("pegRatio")
        revenue_growth = get_num("revenueGrowth")
        cash = get_num("totalCash")
        debt = get_num("totalDebt")
        fcf = get_num("freeCashflow")
        revenue = get_num("totalRevenue")
        analyst_count = get_num("numberOfAnalystOpinions")
        analyst_target = get_num("targetMeanPrice") or get_num("targetMedianPrice")

        if revenue_growth is not None and revenue_growth > 1:
            revenue_growth = revenue_growth / 100

        fcf_margin = None
        if fcf is not None and revenue not in (None, 0):
            fcf_margin = (fcf / revenue) * 100

        dollar_volume = None
        if price is not None and average_volume is not None:
            dollar_volume = price * average_volume

        analyst_upside = None
        if price and analyst_target:
            analyst_upside = (analyst_target / price - 1) * 100

        net_cash = None
        if cash is not None and debt is not None:
            net_cash = cash - debt

        return {
            "ticker": ticker,
            "name": info.get("shortName") or ticker,
            "price": price,
            "market_cap": market_cap,
            "dollar_volume": dollar_volume,
            "ps": ps,
            "peg": peg,
            "revenue_growth": revenue_growth,
            "fcf_margin": fcf_margin,
            "net_cash": net_cash,
            "analyst_count": analyst_count,
            "analyst_upside": analyst_upside,
        }
    except Exception:
        return None

def passes_liquidity(data):
    # Manjkajoči podatki niso obravnavani kot dokaz zadostne likvidnosti.
    return bool(
        data
        and data.get("market_cap") is not None
        and data.get("dollar_volume") is not None
        and data["market_cap"] >= 2_000_000_000
        and data["dollar_volume"] >= 20_000_000
    )

def heuristic_fundamental_score(data):
    """
    Pregledna, nebacktestirana točkovna heuristika.
    Manjkajoče metrike niso nadomeščene z izmišljenimi privzetimi vrednostmi.
    """
    if not data:
        return None, 0

    score = 5.0
    observed = 0
    possible = 5

    ps = data.get("ps")
    if ps is not None and ps > 0:
        observed += 1
        if ps < 4:
            score += 1.2
        elif ps < 8:
            score += 0.7
        elif ps > 25:
            score -= 0.8

    growth = data.get("revenue_growth")
    if growth is not None:
        observed += 1
        if growth > 0.25:
            score += 1.0
        elif growth > 0.10:
            score += 0.5
        elif growth < 0:
            score -= 0.8

    fcf_margin = data.get("fcf_margin")
    if fcf_margin is not None:
        observed += 1
        if fcf_margin > 15:
            score += 0.7
        elif fcf_margin < 0:
            score -= 0.7

    net_cash = data.get("net_cash")
    if net_cash is not None:
        observed += 1
        score += 0.5 if net_cash > 0 else -0.5

    analyst_upside = data.get("analyst_upside")
    if analyst_upside is not None:
        observed += 1
        if analyst_upside > 20:
            score += 0.4
        elif analyst_upside < -10:
            score -= 0.4

    score -= market["penalty"]
    score = round(max(0.0, min(10.0, score)), 1)
    coverage = round(observed / possible * 100)
    return score, coverage

@st.cache_data(ttl=1800, show_spinner=False)
def scan_fundamental_universe(universe):
    rows = []

    for ticker in universe:
        data = get_fundamental_data(ticker)
        if not data or not passes_liquidity(data):
            continue

        score, coverage = heuristic_fundamental_score(data)
        rows.append({
            **data,
            "heuristic_score": score,
            "data_coverage": coverage,
        })

    # Razvrstitev je samo po prikazani heuristiki. Ni dokaz pričakovanega donosa.
    rows.sort(
        key=lambda row: (
            row["heuristic_score"],
            row["data_coverage"],
            row["ticker"],
        ),
        reverse=True,
    )
    return rows

@st.cache_data(ttl=1800, show_spinner=False)
def get_three_year_price_context(ticker):
    # Zgodovinska cena ni isto kot zgodovinska valuacija ali P/S.
    try:
        hist = yf.Ticker(ticker).history(
            period="3y", interval="1wk", auto_adjust=True
        )
        if hist is None or hist.empty:
            return None

        close = hist["Close"].dropna().astype(float)
        if len(close) < 50:
            return None

        median_price = float(close.median())
        current_price = float(close.iloc[-1])
        if median_price <= 0:
            return None

        return round((current_price / median_price - 1) * 100, 1)
    except Exception:
        return None

# ============================================================
# INTRADAY DATA: SEPARATE PREMARKET AND REGULAR SESSION
# ============================================================

@st.cache_data(ttl=90, show_spinner=False)
def get_intraday_history(ticker, period="5d"):
    try:
        hist = yf.Ticker(ticker).history(
            period=period,
            interval="5m",
            prepost=True,
            auto_adjust=False,
        )
        if hist is None or hist.empty:
            return None

        required = ["Open", "High", "Low", "Close", "Volume"]
        if any(column not in hist.columns for column in required):
            return None

        hist = hist.dropna(subset=required).copy()
        if hist.empty:
            return None

        if hist.index.tz is None:
            hist.index = hist.index.tz_localize("UTC")
        hist.index = hist.index.tz_convert(NY_TZ)

        # Obdrži premarket in redno sejo; after-hours izloči.
        keep = [
            time(4, 0) <= stamp.time() < time(16, 0)
            for stamp in hist.index
        ]
        hist = hist.loc[keep].copy()
        return hist if not hist.empty else None
    except Exception:
        return None

def get_session_bars(history, session_date, session_kind):
    if history is None or history.empty:
        return pd.DataFrame()

    same_day = history[
        [stamp.date() == session_date for stamp in history.index]
    ].copy()

    if same_day.empty:
        return same_day

    if session_kind == "premarket":
        return same_day.between_time("04:00", "09:29")
    return same_day.between_time("09:30", "15:59")

def get_previous_regular_close(history, session_date):
    if history is None or history.empty:
        return None

    earlier = history[[stamp.date() < session_date for stamp in history.index]]
    if earlier.empty:
        return None

    previous_date = max(stamp.date() for stamp in earlier.index)
    previous_session = get_session_bars(history, previous_date, "regular")
    if previous_session.empty:
        return None

    close = safe_float(previous_session["Close"].iloc[-1])
    if close is None or close <= 0:
        return None
    return close

def anchored_vwap_series(bars):
    if bars is None or bars.empty:
        return pd.Series(dtype=float)

    high = bars["High"].astype(float)
    low = bars["Low"].astype(float)
    close = bars["Close"].astype(float)
    volume = bars["Volume"].astype(float).clip(lower=0)

    # HLC3 VWAP, ponastavljen ob začetku premarket ali redne seje.
    typical_price = (high + low + close) / 3
    cumulative_volume = volume.cumsum().replace(0, float("nan"))
    return (typical_price * volume).cumsum() / cumulative_volume

def same_time_volume_ratio(history, timestamp, session_bars, index_in_session):
    """
    Primerja tekočo 5-minutno svečo z mediano prometa ob isti uri
    v preteklih sejah iste vrste (premarket z premarketom, redna seja z redno).
    Če primerljivih podatkov ni, vrne None namesto ugibanega razmerja.
    """
    current_volume = safe_float(session_bars["Volume"].iloc[index_in_session])
    if current_volume is None or current_volume <= 0:
        return None

    session_kind = (
        "premarket" if timestamp.time() < time(9, 30) else "regular"
    )
    clock = timestamp.strftime("%H:%M")
    earlier_dates = sorted({
        stamp.date()
        for stamp in history.index
        if stamp.date() < timestamp.date()
    })

    prior_volumes = []
    for prior_date in earlier_dates[-5:]:
        prior_bars = get_session_bars(history, prior_date, session_kind)
        if prior_bars.empty:
            continue

        matching = [
            stamp for stamp in prior_bars.index
            if stamp.strftime("%H:%M") == clock
        ]
        if matching:
            volume = safe_float(prior_bars.loc[matching[-1], "Volume"])
            if volume is not None and volume > 0:
                prior_volumes.append(volume)

    if not prior_volumes:
        return None

    baseline = float(pd.Series(prior_volumes).median())
    if baseline <= 0:
        return None

    return current_volume / baseline

def calculate_rsi(values, period=14):
    close = pd.Series(values, dtype=float)
    if len(close) < period + 1:
        return None

    change = close.diff()
    gains = change.clip(lower=0)
    losses = -change.clip(upper=0)

    average_gain = gains.rolling(period).mean().iloc[-1]
    average_loss = losses.rolling(period).mean().iloc[-1]

    if pd.isna(average_gain) or pd.isna(average_loss):
        return None
    if average_loss == 0:
        return 100.0 if average_gain > 0 else 50.0

    relative_strength = average_gain / average_loss
    return float(100 - (100 / (1 + relative_strength)))

def earnings_within_days(ticker, days=5):
    """
    True: najden datum v obdobju.
    False: podatki so bili pridobljeni in datuma v obdobju ni.
    None: preverjanje ni uspelo ali datum ni na voljo.
    """
    try:
        earnings = yf.Ticker(ticker).get_earnings_dates(limit=8)
        if earnings is None or len(earnings) == 0:
            return None

        today = datetime.now(NY_TZ).date()
        for raw_date in earnings.index:
            date_value = pd.Timestamp(raw_date)
            if date_value.tzinfo is not None:
                date_value = date_value.tz_convert(None)

            delta = (date_value.date() - today).days
            if 0 <= delta <= days:
                return True

        return False
    except Exception:
        return None

def build_reversal_signal(ticker, history, session_date, now_ny=None):
    if history is None or history.empty:
        return None

    now_ny = now_ny or datetime.now(NY_TZ)
    if session_date != now_ny.date():
        return None

    current_day = history[
        [stamp.date() == session_date for stamp in history.index]
    ].copy()
    if current_day.empty:
        return None

    # Uporabljaj samo zaključene sveče.
    completed_day = current_day[
        [stamp + timedelta(minutes=5) <= now_ny for stamp in current_day.index]
    ]
    if completed_day.empty:
        return None

    last_timestamp = completed_day.index[-1]
    session_kind = (
        "premarket" if last_timestamp.time() < time(9, 30) else "regular"
    )
    bars = get_session_bars(history, session_date, session_kind)
    bars = bars[
        [stamp + timedelta(minutes=5) <= now_ny for stamp in bars.index]
    ]

    # Zahteva dovolj sveč za izračun RSI in znotrajsejnih meritev.
    if len(bars) < 15:
        return None

    last_timestamp = bars.index[-1]
    last_index = len(bars) - 1
    previous_close = get_previous_regular_close(history, session_date)
    if previous_close is None:
        return None

    close = safe_float(bars["Close"].iloc[-1])
    open_price = safe_float(bars["Open"].iloc[-1])
    previous_bar_close = safe_float(bars["Close"].iloc[-2])
    if not close or not open_price or not previous_bar_close:
        return None

    gap_pct = (close / previous_close - 1) * 100
    if not -8.0 <= gap_pct <= -1.0:
        return None

    vwap = anchored_vwap_series(bars)
    if len(vwap) < 2 or pd.isna(vwap.iloc[-1]) or pd.isna(vwap.iloc[-2]):
        return None

    prior_close = safe_float(bars["Close"].iloc[-2])
    prior_vwap = safe_float(vwap.iloc[-2])
    current_vwap = safe_float(vwap.iloc[-1])
    if prior_close is None or prior_vwap is None or current_vwap is None:
        return None

    # Dejanski preboj VWAP-a navzgor med dvema zaključenima svečama.
    crossed_up = prior_close <= prior_vwap and close > current_vwap
    green_candle = close > open_price
    if not crossed_up or not green_candle:
        return None

    rsi = calculate_rsi(bars["Close"])
    if rsi is None or rsi >= 35:
        return None

    volume_ratio = same_time_volume_ratio(
        history, last_timestamp, bars, last_index
    )
    if volume_ratio is None or volume_ratio < 1.3:
        return None

    momentum = (close / previous_bar_close - 1) * 100
    if momentum <= 0:
        return None

    earnings_status = earnings_within_days(ticker, 5)
    # Neoznači signal kot primeren, če earnings niso mogli biti preverjeni.
    if earnings_status is not False:
        return None

    vwap_distance = (close / current_vwap - 1) * 100

    score = 6.0
    score += min(max(volume_ratio - 1.3, 0) * 0.5, 1.5)
    score += min(max(momentum, 0) * 0.25, 1.0)
    score -= market["penalty"]
    score = round(max(0.0, min(10.0, score)), 1)

    if score < 6.0:
        return None

    return {
        "Ticker": ticker,
        "Čas": last_timestamp.strftime("%H:%M ET"),
        "Seja": "PREMARKET" if session_kind == "premarket" else "REDNA SEJA",
        "Cena": round(close, 2),
        "Gap proti prejšnjemu close %": round(gap_pct, 2),
        "Sejni VWAP": round(current_vwap, 2),
        "Odstopanje od VWAP %": round(vwap_distance, 2),
        "Volumen proti isti uri x": round(volume_ratio, 2),
        "RSI 5m": round(rsi, 1),
        "Momentum %": round(momentum, 2),
        "Ocena (heuristika)": score,
    }

@st.cache_data(ttl=90, show_spinner=False)
def scan_reversals(universe, n=5):
    now_ny = datetime.now(NY_TZ)
    results = []

    for ticker in universe:
        history = get_intraday_history(ticker, "5d")
        if history is None or history.empty:
            continue

        signal = build_reversal_signal(
            ticker=ticker,
            history=history,
            session_date=now_ny.date(),
            now_ny=now_ny,
        )
        if signal:
            results.append(signal)

    results.sort(
        key=lambda row: row["Ocena (heuristika)"],
        reverse=True,
    )
    return results[:n]

# ============================================================
# DIAGNOSTIC HISTORICAL CHECK
# ============================================================

def backtest_ticker(ticker, holding_bars=12):
    """
    Diagnostic only:
    - Uses available 30-day 5-minute Yahoo data.
    - Entry is next bar open after the signal bar.
    - Exit is close after holding_bars.
    - Historical earnings availability is not reconstructed.
    - No fees, spread, slippage or fill modeling.
    """
    history = get_intraday_history(ticker, "30d")
    if history is None or history.empty:
        return []

    dates = sorted({stamp.date() for stamp in history.index})
    trades = []

    for session_date in dates:
        previous_close = get_previous_regular_close(history, session_date)
        if previous_close is None:
            continue

        for session_kind in ("premarket", "regular"):
            bars = get_session_bars(history, session_date, session_kind)
            if len(bars) < 16:
                continue

            vwap = anchored_vwap_series(bars)
            closes = bars["Close"].astype(float)
            opens = bars["Open"].astype(float)

            for index in range(15, len(bars) - holding_bars - 1):
                close = safe_float(closes.iloc[index])
                open_price = safe_float(opens.iloc[index])
                prior_close = safe_float(closes.iloc[index - 1])
                current_vwap = safe_float(vwap.iloc[index])
                prior_vwap = safe_float(vwap.iloc[index - 1])

                if any(value is None for value in (
                    close, open_price, prior_close, current_vwap, prior_vwap
                )):
                    continue

                gap_pct = (close / previous_close - 1) * 100
                if not -8 <= gap_pct <= -1:
                    continue

                crossed_up = (
                    float(closes.iloc[index - 1]) <= prior_vwap
                    and close > current_vwap
                )
                if not crossed_up or close <= open_price:
                    continue

                rsi = calculate_rsi(closes.iloc[:index + 1])
                if rsi is None or rsi >= 35:
                    continue

                timestamp = bars.index[index]
                volume_ratio = same_time_volume_ratio(
                    history, timestamp, bars, index
                )
                if volume_ratio is None or volume_ratio < 1.3:
                    continue

                momentum = (close / prior_close - 1) * 100
                if momentum <= 0:
                    continue

                entry_index = index + 1
                exit_index = min(entry_index + holding_bars, len(bars) - 1)
                entry = safe_float(bars["Open"].iloc[entry_index])
                exit_price = safe_float(bars["Close"].iloc[exit_index])
                if not entry or not exit_price:
                    continue

                trades.append({
                    "Datum": str(session_date),
                    "Ticker": ticker,
                    "Seja": "Premarket" if session_kind == "premarket" else "Redna",
                    "Vstop": round(entry, 2),
                    "Izhod": round(exit_price, 2),
                    "Donos %": round((exit_price / entry - 1) * 100, 2),
                })

                # Največ en rezultat na ticker na dan in sejo.
                break

    return trades

def run_diagnostic_backtest(tickers):
    trades = []
    for ticker in tickers:
        trades.extend(backtest_ticker(ticker))
    return pd.DataFrame(trades)

# ============================================================
# GEMINI COMMENTARY: ANALYZE PROVIDED DATA, DO NOT INVENT METRICS
# ============================================================

def get_gemini_comment(api_key, prompt):
    api_key = api_key.strip()
    if not api_key:
        raise ValueError("Vnesi Gemini API ključ.")

    response = requests.get(
        "https://generativelanguage.googleapis.com/v1beta/models",
        params={"key": api_key},
        timeout=20,
    )
    response.raise_for_status()

    models = response.json().get("models", [])
    model_names = [
        model["name"].split("/")[-1]
        for model in models
        if "generateContent" in model.get("supportedGenerationMethods", [])
    ]
    if not model_names:
        raise RuntimeError("API ni vrnil modela, ki podpira generateContent.")

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    last_error = "Klic API-ja ni uspel."

    for model_name in model_names:
        try:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model_name}:generateContent"
            )
            result = requests.post(
                url,
                params={"key": api_key},
                json=payload,
                timeout=35,
            )

            if result.status_code == 200:
                parts = (
                    result.json()
                    .get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [])
                )
                text = "\n".join(
                    part.get("text", "")
                    for part in parts
                    if part.get("text")
                )
                if text:
                    return model_name, text

            last_error = (
                f"{model_name}: HTTP {result.status_code} "
                f"{result.text[:250]}"
            )
        except Exception as error:
            last_error = str(error)

    raise RuntimeError(last_error)

# ============================================================
# APP UI
# ============================================================

now_ljubljana = datetime.now(LJ_TZ)

st.markdown(
    f"""
    <div style="border-bottom:1px solid rgba(255,255,255,0.08);
                padding-bottom:12px;margin-bottom:18px;">
      <h1 style="margin:0;">
        <span style="color:#F59E0B;">THE VALUE LEDGER</span>
        <span style="color:#60A5FA;">2.0</span>
      </h1>
      <p style="color:#94A3B8;">
        Kvantitativni terminal · {now_ljubljana.strftime("%d.%m.%Y %H:%M")} Ljubljana
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown("### Nastavitve")
gemini_api_key = st.sidebar.text_input(
    "Gemini API ključ (neobvezno)",
    type="password",
)
st.sidebar.caption(f"Unikatni tickerji: {len(AI_UNIVERSE)}")
st.sidebar.caption("Podatki Yahoo Finance so lahko zakasnjeni ali nepopolni.")
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Tržni režim:** {market['regime']}")

if market["spy_chg"] is not None:
    st.sidebar.caption(f"SPY 20d: {market['spy_chg']:+.2f}%")

held_ticker = st.sidebar.selectbox(
    "Delnica za pregled",
    options=list(TICKERS_CONFIG.keys()),
    index=list(TICKERS_CONFIG.keys()).index("CRWD"),
)

st.title("Value Ledger 2.0")
st.caption(
    "Skener prikazuje merila in kandidate. Ocena ni potrjena napoved "
    "donosa, signal ni zagotovilo dobička, aplikacija pa ne oddaja naročil."
)

# Hero cards use current data, with no hard-coded placeholder prices.
hero_left, hero_right = st.columns(2)

mndy_data = get_fundamental_data("MNDY")
crwd_data = get_fundamental_data("CRWD")

with hero_left:
    mndy_price = mndy_data.get("price") if mndy_data else None
    mndy_ps = mndy_data.get("ps") if mndy_data else None
    st.markdown(
        f"""
        <div class="hero-mndy">
          <div style="color:#FBBF24;font-size:0.78rem;font-weight:700;">
            SAAS · FUNDAMENTALNI PODATKI
          </div>
          <div style="font-size:1.5rem;font-weight:700;color:#FFFFFF;margin-top:5px;">
            MNDY
          </div>
          <div style="color:#CBD5E1;margin-top:7px;">
            Cena: {"$" + format(mndy_price, ".2f") if mndy_price else "ni podatka"}
            &nbsp; · &nbsp;
            P/S: {format(mndy_ps, ".2f") if mndy_ps is not None else "ni podatka"}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with hero_right:
    crwd_price = crwd_data.get("price") if crwd_data else None
    crwd_ps = crwd_data.get("ps") if crwd_data else None
    st.markdown(
        f"""
        <div class="hero-crwd">
          <div style="color:#6EE7B7;font-size:0.78rem;font-weight:700;">
            CYBERSECURITY · FUNDAMENTALNI PODATKI
          </div>
          <div style="font-size:1.5rem;font-weight:700;color:#FFFFFF;margin-top:5px;">
            CRWD
          </div>
          <div style="color:#CBD5E1;margin-top:7px;">
            Cena: {"$" + format(crwd_price, ".2f") if crwd_price else "ni podatka"}
            &nbsp; · &nbsp;
            P/S: {format(crwd_ps, ".2f") if crwd_ps is not None else "ni podatka"}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ------------------------------------------------------------
# Sector rotation
# ------------------------------------------------------------

st.subheader("Capital Rotation Radar")
st.markdown(
    f"""
    <div class="ledger-card">
      <div style="color:#FBBF24;font-weight:700;font-size:1rem;">
        {html.escape(rotation["pair"])}
      </div>
      <div style="color:#94A3B8;font-size:0.82rem;margin-top:6px;">
        Tržni režim: {html.escape(market["regime"])}
        {(" · " + html.escape(rotation["pair_detail"])) if rotation["pair_detail"] else ""}
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if rotation["rows"]:
    render_dark_table(pd.DataFrame(rotation["rows"]))
else:
    st.info("Sektorski podatki trenutno niso na voljo.")

st.caption(
    "Primerjava ETF-jev kaže relativno gibanje cen proti SPY, ne neposrednih "
    "nakupnih ali prodajnih tokov Wall Streeta."
)

# ------------------------------------------------------------
# Fundamental screen, explicitly labeled as heuristic
# ------------------------------------------------------------

st.subheader("Fundamentalni pregled · hevristika, ne potrjena primerjava")
st.caption(
    "Točkovanje je ročno določena, nebacktestirana hevristika. Razvrstitev "
    "ne dokazuje, da je delnica podcenjena ali da bo presegla druge. "
    "P/S ni primerljiv med vsemi sektorji, PEG in podatki Yahoo Finance "
    "pa so lahko manjkajoči ali zastareli."
)

with st.spinner("Pregledujem temeljne podatke univerzuma..."):
    fundamental_rows = scan_fundamental_universe(tuple(AI_UNIVERSE))

if fundamental_rows:
    top_rows = fundamental_rows[:5]
    displayed = []

    for row in top_rows:
        price_vs_median = get_three_year_price_context(row["ticker"])
        growth = row.get("revenue_growth")

        displayed.append({
            "Ticker": row["ticker"],
            "Podjetje": row["name"],
            "Hevristična ocena / 10": row["heuristic_score"],
            "Pokritost meril %": row["data_coverage"],
            "Cena $": display_value(row.get("price")),
            "P/S": display_value(row.get("ps")),
            "PEG": display_value(row.get("peg")),
            "Rast prihodkov %": display_value(
                growth * 100 if growth is not None else None, 1
            ),
            "FCF marža %": display_value(row.get("fcf_margin"), 1),
            "Neto denar $": display_value(row.get("net_cash"), 0),
            "Analitiki": display_value(row.get("analyst_count"), 0),
            "Ciljna rast analitikov %": display_value(
                row.get("analyst_upside"), 1
            ),
            "Cena proti 3y mediani %": display_value(price_vs_median, 1),
        })

    render_dark_table(pd.DataFrame(displayed))
else:
    st.info(
        "Ni delnic z dovolj razpoložljivimi podatki, ki bi prestale "
        "nastavljeni filter likvidnosti."
    )

st.caption(
    "»Cena proti 3y mediani« primerja samo zgodovinsko ceno. Ni zgodovinski "
    "P/S ali dokaz podcenjenosti. Za pravo primerjavo valuacije bi potrebovali "
    "zanesljive zgodovinske prihodke in tržno kapitalizacijo."
)

# ------------------------------------------------------------
# Intraday reversal scan
# ------------------------------------------------------------

st.subheader("TOP 5 Intraday Reversal")
st.caption(
    "Premarket VWAP se računa ločeno od začetka premarketa. VWAP redne seje "
    "se ponastavi ob 09:30 ET. Volumen se primerja z isto 5-minutno uro "
    "in isto vrsto seje v preteklih dneh."
)

if st.button("Osveži intraday skener"):
    scan_reversals.clear()
    get_intraday_history.clear()
    st.rerun()

with st.spinner("Pregledujem intraday podatke..."):
    reversal_rows = scan_reversals(tuple(AI_UNIVERSE), 5)

if reversal_rows:
    render_dark_table(pd.DataFrame(reversal_rows))
else:
    st.info(
        "NI STROGEGA KANDIDATA. Filter zahteva gap od -1 % do -8 %, "
        "dejanski preboj VWAP-a navzgor, zeleno zaključeno svečo, RSI pod 35, "
        "volumen vsaj 1,3× primerljive sveče, pozitiven momentum in uspešno "
        "preverjene earnings podatke."
    )

st.warning(
    "Premarket je pogosto manj likviden in njegovi podatki so lahko nepopolni. "
    "Prestani pogoji pomenijo samo, da se številke ujemajo s filtrom, ne da "
    "je setup A+ ali dobičkonosen."
)

# ------------------------------------------------------------
# Diagnostic backtest
# ------------------------------------------------------------

st.subheader("Diagnostični zgodovinski test")
st.caption(
    "Za izbrane tickerje uporabi do približno 30 dni 5-minutnih podatkov. "
    "Vstop je modeliran na naslednji sveči, izhod po 12 svečah. Zgodovinski "
    "earnings filter, stroški, zdrs in realistična izvršitev niso vključeni; "
    "rezultat ni dokaz trgovalne prednosti."
)

backtest_tickers = st.multiselect(
    "Tickerji za test (izberi manjše število)",
    options=AI_UNIVERSE,
    default=["CRWD", "MNDY", "NOW"],
    max_selections=5,
)

if st.button("Zaženi diagnostični backtest"):
    if not backtest_tickers:
        st.warning("Izberi vsaj en ticker.")
    else:
        with st.spinner("Prenos in obdelava zgodovinskih podatkov..."):
            backtest_frame = pd.DataFrame()

            trades = []
            for ticker in backtest_tickers:
                trades.extend(backtest_ticker(ticker))

            if trades:
                backtest_frame = pd.DataFrame(trades)

        if backtest_frame.empty:
            st.info("V prenesenih podatkih ni bilo najdenih setupov po pravilih.")
        else:
            win_rate = (
                (backtest_frame["Donos %"] > 0).mean() * 100
            )
            average_return = backtest_frame["Donos %"].mean()
            median_return = backtest_frame["Donos %"].median()

            metric1, metric2, metric3, metric4 = st.columns(4)
            metric1.metric("Posli", len(backtest_frame))
            metric2.metric("Pozitivni posli", f"{win_rate:.1f}%")
            metric3.metric("Povprečni donos", f"{average_return:.2f}%")
            metric4.metric("Mediani donos", f"{median_return:.2f}%")

            render_dark_table(backtest_frame)

            st.warning(
                "Rezultat je diagnostičen, ne potrjen backtest: vzorec je "
                "omejen, zgodovinska earnings zaščita manjka, podatki so "
                "odvisni od ponudnika, stroški in zdrs pa niso vključeni."
            )

# ------------------------------------------------------------
# Autonomous AI analyst: commentary on displayed data only
# ------------------------------------------------------------

st.subheader("Avtonomni AI Analitik")
st.caption(
    "Analitik komentira podatke, ki jih je skener dejansko prikazal. "
    "Ne sme si izmišljati manjkajočih metrik ali obljubljati donosa."
)

if st.button("Zaženi AI komentar trga"):
    if not gemini_api_key:
        st.error("Vnesi Gemini API ključ za AI komentar.")
    else:
        fundamental_context = [
            {
                "ticker": row["ticker"],
                "heuristic_score": row["heuristic_score"],
                "data_coverage_pct": row["data_coverage"],
                "price": row.get("price"),
                "ps": row.get("ps"),
                "peg": row.get("peg"),
                "revenue_growth": row.get("revenue_growth"),
                "fcf_margin": row.get("fcf_margin"),
                "net_cash": row.get("net_cash"),
                "analyst_upside": row.get("analyst_upside"),
            }
            for row in fundamental_rows[:5]
        ]

        prompt = f"""
Odgovori v slovenščini kot previden analitik podatkov.

Uporabi samo spodaj navedene podatke. Ne izmišljaj si cen, novic,
earnings datumov, tokov kapitala ali prihodnjih donosov.
ETF relativna moč je cenovni približek in ni neposredno merjenje tokov denarja.
Hevristična temeljna ocena ni potrjena primerjava valuacije in ni napoved donosa.
Če reversal kandidatov ni, napiši "NI STROGEGA KANDIDATA".
Ne uporabljaj izrazov "zagotovljen", "100 %", "A+ dobiček" ali podobnih obljub.

Tržni režim: {market}
Sektorska relativna moč: {rotation}
Fundamentalni kandidati: {fundamental_context}
Intraday reversal kandidati: {reversal_rows}

Odgovori v treh kratkih delih:
1. Tržni režim in kaj kaže relativna moč sektorjev.
2. Kaj kažejo prikazani temeljni podatki ter njihove omejitve.
3. Ali so reversal kandidati prestali prikazane filtre; navedi njihove dejanske številke.
Če pomemben podatek manjka, ga označi kot manjkajoč.
"""

        try:
            with st.spinner("Pripravljam AI komentar prikazanih podatkov..."):
                model_name, report = get_gemini_comment(
                    gemini_api_key,
                    prompt,
                )
            st.caption(f"API model: {model_name}")
            st.markdown(
                f'<div class="ledger-card">{report}</div>',
                unsafe_allow_html=True,
            )
        except Exception as error:
            st.error(f"AI komentar ni uspel: {error}")

st.caption(
    "Skener se zažene ob nalaganju strani ali ob ročni osvežitvi. "
    "Aplikacija ne spremlja trga v ozadju in ne pošilja samodejnih opozoril."
)
