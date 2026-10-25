# app.py
import html
import math
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st
import yfinance as yf


# ============================================================
# NASTAVITVE IN TEMNI VIDEZ
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
    .hero-long {
        background: linear-gradient(145deg, rgba(48,34,10,0.72), rgba(13,17,28,0.96));
        border: 1px solid rgba(245,158,11,0.58);
        border-radius: 18px;
        padding: 20px 24px;
        min-height: 190px;
    }
    .hero-reversal {
        background: linear-gradient(145deg, rgba(9,43,39,0.75), rgba(13,17,28,0.96));
        border: 1px solid rgba(16,185,129,0.48);
        border-radius: 18px;
        padding: 20px 24px;
        min-height: 190px;
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
# UNIVERZUM: UNIKATNI TICKERJI, NAJVEČ 150
# ============================================================

TICKER_CANDIDATES = [
    # SaaS, programska oprema in cloud
    "MNDY", "CRWD", "SNOW", "HUBS", "DDOG", "TEAM", "NOW", "PANW",
    "PLTR", "CRM", "ADBE", "SHOP", "NET", "ZS", "OKTA", "MDB",
    "ESTC", "PATH", "WDAY", "CFLT", "DOCN", "GTLB", "TOST", "BILL",
    "ASAN", "IOT", "FSLY", "DT", "BSY", "PCOR", "NCNO", "ZM",
    "DOCU", "TWLO", "PD", "DBX", "SMAR", "UPWK", "SPT", "APPN",
    "PEGA", "FROG", "RNG", "VEEV", "TYL", "PTC", "ADSK", "TRMB",

    # Velika tehnologija in internet
    "AAPL", "MSFT", "META", "AMZN", "GOOGL", "NFLX", "TSLA",
    "UBER", "ABNB", "DASH", "SPOT", "RBLX", "TTD", "ROKU",
    "PINS", "SNAP", "MTCH", "DKNG", "LYFT", "EBAY",

    # Polprevodniki, oprema in strojna oprema
    "NVDA", "AVGO", "AMD", "TSM", "MU", "QCOM", "ARM", "SMCI",
    "ANET", "MRVL", "SNPS", "CDNS", "ANSS", "ALAB", "LITE",
    "COHR", "VRT", "NTNX", "PSTG", "STX", "WDC", "TXN", "ADI",
    "NXPI", "MCHP", "ON", "INTC", "ASML", "AMAT", "LRCX",
    "KLAC", "DELL", "CSCO", "HPE", "HPQ", "GLW", "TER", "KEYS",

    # Kibernetska varnost
    "CHKP", "CYBR", "TENB", "VRNS", "QLYS", "FTNT", "AKAM",
    "VRSN", "GEN", "S",

    # Finance, plačila in fintech
    "COIN", "HOOD", "XYZ", "PYPL", "SOFI", "AFRM", "MELI",
    "SE", "NU", "V", "MA", "GLBE", "JPM", "GS", "MS", "C",
    "BAC", "SCHW", "ICE", "CME",

    # Zdravstvo in medicinska tehnologija
    "ISRG", "DXCM", "PODD", "EXAS", "ILMN", "ALGN", "MDT",
    "SYK", "BSX", "ABT", "VRTX", "REGN", "LLY", "NVO", "UNH",

    # Industrija, energija, potrošnja in drugi sektorji
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
# SPLOŠNE POMOŽNE FUNKCIJE
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
    """Prikaže tabelo v temnem slogu."""
    if frame is None or frame.empty:
        st.info("Ni podatkov za prikaz.")
        return

    headers = "".join(
        f"<th>{html.escape(str(column))}</th>"
        for column in frame.columns
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

    # Navaden niz, ne f-string: zaviti CSS-oklepaji ne sprožijo Pythonove napake.
    table_html = (
        '<div style="overflow-x:auto;border:1px solid #263044;'
        'border-radius:10px;margin:8px 0 18px 0;">'
        '<table style="border-collapse:collapse;width:100%;'
        'background:#0D111C;color:#CBD5E1;font-size:0.82rem;">'
        '<thead><tr style="background:#151B29;color:#F8FAFC;">'
        + headers
        + "</tr></thead><tbody>"
        + "".join(body_rows)
        + "</tbody></table></div>"
        "<style>"
        "table th, table td {"
        "border:1px solid #202838;"
        "padding:8px 10px;"
        "text-align:left;"
        "white-space:nowrap;"
        "}"
        "table tbody tr:nth-child(even) {background:#101522;}"
        "</style>"
    )
    st.markdown(table_html, unsafe_allow_html=True)


def log_event(kind, ticker, score, detail=""):
    try:
        safe_detail = str(detail).replace(",", ";").replace("\n", " ")
        with open("king_log.csv", "a", encoding="utf-8") as log_file:
            log_file.write(
                f"{datetime.now().isoformat()},{kind},{ticker},{score},{safe_detail}\n"
            )
    except Exception:
        pass


# ============================================================
# TRŽNI REŽIM IN SEKTORSKA RELATIVNA MOČ
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def get_market_regime():
    try:
        hist = yf.Ticker("SPY").history(
            period="6mo",
            interval="1d",
            auto_adjust=True,
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
    # ETF-ji merijo relativno gibanje cen, ne neposrednih denarnih tokov.
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
                period="8mo",
                interval="1d",
                auto_adjust=True,
            )
            if hist is not None and not hist.empty:
                closes[ticker] = hist["Close"].dropna().astype(float)
        except Exception:
            continue

    if "SPY" not in closes:
        return {"rows": [], "pair": "NI PODATKOV", "pair_detail": ""}

    def relative_return(series, benchmark, days):
        joined = pd.concat(
            [
                series.rename("sector"),
                benchmark.rename("benchmark"),
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

        benchmark_return = (
            joined["benchmark"].iloc[-1]
            / joined["benchmark"].iloc[-1 - days]
            - 1
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

    rows.sort(
        key=lambda row: row["Rel. 20d % vs SPY"],
        reverse=True,
    )

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
                f"IGV/SMH: 20d {p20:+.1f}%, 60d {p60:+.1f}%; "
                f"nad SMA20: {'DA' if above_sma20 else 'NE'}"
            )

    return {
        "rows": rows,
        "pair": pair,
        "pair_detail": detail,
    }


market = get_market_regime()
rotation = get_capital_rotation()


# ============================================================
# FUNDAMENTI IN DINAMIČNI TOP LONG
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
        ps_raw = get_num("priceToSalesTrailing12Months")
        peg = get_num("pegRatio")
        revenue_growth = get_num("revenueGrowth")
        cash = get_num("totalCash")
        debt = get_num("totalDebt")
        fcf = get_num("freeCashflow")
        revenue = get_num("totalRevenue")
        analyst_count = get_num("numberOfAnalystOpinions")
        recommendation_mean = get_num("recommendationMean")
        analyst_target = (
            get_num("targetMeanPrice")
            or get_num("targetMedianPrice")
        )

        if revenue_growth is not None and revenue_growth > 1:
            revenue_growth /= 100

        fcf_margin = None
        if fcf is not None and revenue not in (None, 0):
            fcf_margin = fcf / revenue * 100

        dollar_volume = None
        if price is not None and average_volume is not None:
            dollar_volume = price * average_volume

        analyst_upside = None
        if price and analyst_target:
            analyst_upside = (analyst_target / price - 1) * 100

        net_cash = None
        if cash is not None and debt is not None:
            net_cash = cash - debt

        fcf_yield_raw = None
        if fcf is not None and market_cap not in (None, 0):
            fcf_yield_raw = fcf / market_cap * 100

        # Ekstremne vrednosti obravnavamo kot sumljive podatke in jih ne točkujemo.
        fcf_yield = fcf_yield_raw
        fcf_yield_valid = (
            fcf_yield_raw is not None
            and -10 <= fcf_yield_raw <= 15
        )
        if not fcf_yield_valid:
            fcf_yield = None

        return {
            "ticker": ticker,
            "name": info.get("shortName") or ticker,
            "price": price,
            "market_cap": market_cap,
            "dollar_volume": dollar_volume,
            "ps": ps_raw,
            "ps_valid": ps_raw is not None and ps_raw >= 1,
            "peg": peg,
            "revenue_growth": revenue_growth,
            "fcf": fcf,
            "fcf_margin": fcf_margin,
            "fcf_yield": fcf_yield,
            "fcf_yield_raw": fcf_yield_raw,
            "fcf_yield_valid": fcf_yield_valid,
            "net_cash": net_cash,
            "debt": debt,
            "analyst_count": analyst_count,
            "recommendation_mean": recommendation_mean,
            "analyst_upside": analyst_upside,
        }
    except Exception:
        return None


@st.cache_data(ttl=1800, show_spinner=False)
def get_three_year_price_context(ticker):
    # Mediana cene ni zgodovinski P/S in sama ne dokazuje podcenjenosti.
    try:
        hist = yf.Ticker(ticker).history(
            period="3y",
            interval="1wk",
            auto_adjust=True,
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


def passes_liquidity(data):
    return bool(
        data
        and data.get("market_cap") is not None
        and data.get("dollar_volume") is not None
        and data["market_cap"] >= 2_000_000_000
        and data["dollar_volume"] >= 20_000_000
    )


def wall_street_score(data):
    """
    Groba ocena Yahoo Finance analitikov in ciljne cene.
    Ne meri spremembe sentimenta skozi čas.
    """
    score = 5.0
    recommendation = data.get("recommendation_mean")

    if recommendation is not None:
        if recommendation <= 1.5:
            score += 2.0
        elif recommendation <= 2.0:
            score += 1.5
        elif recommendation <= 2.5:
            score += 0.5
        elif recommendation >= 4.0:
            score -= 1.5
        elif recommendation >= 3.5:
            score -= 1.0

    upside = data.get("analyst_upside")
    if upside is not None:
        if upside > 30:
            score += 1.5
        elif upside > 15:
            score += 1.0
        elif upside > 5:
            score += 0.5
        elif upside < -10:
            score -= 1.0

    analyst_count = data.get("analyst_count")
    if analyst_count is not None and analyst_count < 5:
        score -= 0.5

    return max(0.0, min(10.0, score))


def asymmetric_long_score(data):
    """
    Hevristična točkovna ocena. Ni potrjen model pričakovanega donosa.
    """
    if not data:
        return None, 0

    score = 5.0
    observed = 0
    possible = 7

    ps = data.get("ps")
    if ps is not None and ps >= 1:
        observed += 1
        if ps < 4:
            score += 2.0
        elif ps < 7:
            score += 1.5
        elif ps < 12:
            score += 0.75
        elif ps > 20:
            score -= 1.0

    peg = data.get("peg")
    if peg is not None and peg > 0:
        observed += 1
        if peg < 0.9:
            score += 1.5
        elif peg < 1.3:
            score += 1.0
        elif peg < 2.0:
            score += 0.4
        elif peg > 2.8:
            score -= 1.0

    growth = data.get("revenue_growth")
    if growth is not None:
        observed += 1
        if growth > 0.25:
            score += 1.0
        elif growth > 0.15:
            score += 0.6
        elif growth < 0.12:
            score -= 0.5

    fcf_margin = data.get("fcf_margin")
    if fcf_margin is not None:
        observed += 1
        if fcf_margin > 20:
            score += 1.0
        elif fcf_margin > 10:
            score += 0.5
        elif fcf_margin < 0:
            score -= 1.0

    if data.get("net_cash") is not None:
        observed += 1
        if data["net_cash"] > 0:
            score += 0.75
        else:
            score -= 0.75

    if data.get("fcf_yield_valid"):
        observed += 1
        if data["fcf_yield"] > 5:
            score += 0.75
        elif data["fcf_yield"] > 3:
            score += 0.4
        elif data["fcf_yield"] < 0:
            score -= 0.5

    if (
        data.get("analyst_upside") is not None
        or data.get("recommendation_mean") is not None
    ):
        observed += 1
        score += (wall_street_score(data) - 5.0) * 0.25

    score -= market["penalty"]
    score = round(max(0.0, min(10.0, score)), 1)
    coverage = round(observed / possible * 100)

    return score, coverage


@st.cache_data(ttl=1800, show_spinner=False)
def scan_top_long(universe, n=5):
    rows = []

    for ticker in universe:
        data = get_fundamental_data(ticker)
        if not data or not passes_liquidity(data):
            continue

        # Izločimo neveljaven P/S, vključno z znanimi pod-1 napakami.
        if not data.get("ps_valid"):
            continue

        # Zahtevani podatki za ta fundamentalni filter.
        if data.get("peg") is None or data["peg"] <= 0 or data["peg"] > 2.8:
            continue

        growth = data.get("revenue_growth")
        if growth is None or growth < 0.12:
            continue

        if (
            data.get("debt") is not None
            and data.get("net_cash") is not None
            and data["debt"] > 0
            and data["net_cash"] < 0
        ):
            continue

        score, coverage = asymmetric_long_score(data)
        if score is None:
            continue

        row = {
            **data,
            "score": score,
            "coverage": coverage,
        }
        rows.append(row)

    rows.sort(
        key=lambda row: (
            row["score"],
            row["coverage"],
            row["ticker"],
        ),
        reverse=True,
    )
    return rows[:n]


# ============================================================
# INTRADAY: PREMARKET IN REDNA SEJA LOČENO
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

        # Premarket od 04:00 ET in redna seja do 16:00 ET. After-hours izločimo.
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

    earlier = history[
        [stamp.date() < session_date for stamp in history.index]
    ]
    if earlier.empty:
        return None

    earlier_dates = sorted(
        {stamp.date() for stamp in earlier.index},
        reverse=True,
    )

    for previous_date in earlier_dates:
        previous_session = get_session_bars(
            history,
            previous_date,
            "regular",
        )
        if previous_session.empty:
            continue

        close = safe_float(previous_session["Close"].iloc[-1])
        if close is not None and close > 0:
            return close

    return None


def anchored_vwap_series(bars):
    if bars is None or bars.empty:
        return pd.Series(dtype=float)

    high = bars["High"].astype(float)
    low = bars["Low"].astype(float)
    close = bars["Close"].astype(float)
    volume = bars["Volume"].astype(float).clip(lower=0)

    typical_price = (high + low + close) / 3
    cumulative_volume = volume.cumsum().replace(0, float("nan"))

    return (typical_price * volume).cumsum() / cumulative_volume


def same_time_volume_ratio(history, timestamp, session_bars, index_in_session):
    """
    Primerjava z mediano prometa ob isti uri v zadnjih petih primerljivih sejah.
    Premarket se ne primerja z redno sejo.
    """
    current_volume = safe_float(
        session_bars["Volume"].iloc[index_in_session]
    )
    if current_volume is None or current_volume <= 0:
        return None

    session_kind = (
        "premarket"
        if timestamp.time() < time(9, 30)
        else "regular"
    )
    clock = timestamp.strftime("%H:%M")

    earlier_dates = sorted({
        stamp.date()
        for stamp in history.index
        if stamp.date() < timestamp.date()
    })

    prior_volumes = []
    for prior_date in earlier_dates[-5:]:
        prior_bars = get_session_bars(
            history,
            prior_date,
            session_kind,
        )
        if prior_bars.empty:
            continue

        matching = [
            stamp
            for stamp in prior_bars.index
            if stamp.strftime("%H:%M") == clock
        ]
        if matching:
            volume = safe_float(
                prior_bars.loc[matching[-1], "Volume"]
            )
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
    True: datum je najden v obdobju.
    False: podatki so bili pridobljeni in datuma ni v obdobju.
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

    # Uporabi samo zaključene 5-minutne sveče.
    completed_day = current_day[
        [
            stamp + timedelta(minutes=5) <= now_ny
            for stamp in current_day.index
        ]
    ]
    if completed_day.empty:
        return None

    latest_timestamp = completed_day.index[-1]
    session_kind = (
        "premarket"
        if latest_timestamp.time() < time(9, 30)
        else "regular"
    )

    bars = get_session_bars(history, session_date, session_kind)
    bars = bars[
        [
            stamp + timedelta(minutes=5) <= now_ny
            for stamp in bars.index
        ]
    ]

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

    # Dejanski prehod: prejšnji close je pod VWAP, zadnji pa nad njim.
    crossed_up = prior_close <= prior_vwap and close > current_vwap
    green_candle = close > open_price

    if not crossed_up or not green_candle:
        return None

    rsi = calculate_rsi(bars["Close"])
    if rsi is None or rsi >= 35:
        return None

    volume_ratio = same_time_volume_ratio(
        history,
        last_timestamp,
        bars,
        last_index,
    )
    if volume_ratio is None or volume_ratio < 1.3:
        return None

    momentum = (close / previous_bar_close - 1) * 100
    if momentum <= 0:
        return None

    earnings_status = earnings_within_days(ticker, 5)
    # Kandidata ne označimo kot ustreznega, če earnings niso preverljivi.
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
        "Seja": (
            "PREMARKET"
            if session_kind == "premarket"
            else "REDNA SEJA"
        ),
        "Cena": round(close, 2),
        "Gap proti prejšnjemu close %": round(gap_pct, 2),
        "VWAP": round(current_vwap, 2),
        "Odstopanje od VWAP %": round(vwap_distance, 2),
        "Volumen proti isti uri x": round(volume_ratio, 2),
        "RSI 5m": round(rsi, 1),
        "Momentum %": round(momentum, 2),
        "Ocena (hevristika)": score,
    }


@st.cache_data(ttl=90, show_spinner=False)
def scan_top_reversal(universe, n=5):
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
        key=lambda row: row["Ocena (hevristika)"],
        reverse=True,
    )
    return results[:n]


# ============================================================
# ATR STOP IN CILJI ZA DYNAMIC LONG KARTICO
# ============================================================

@st.cache_data(ttl=1800, show_spinner=False)
def get_atr_value(ticker):
    try:
        hist = yf.Ticker(ticker).history(
            period="3mo",
            interval="1d",
            auto_adjust=True,
        )
        if hist is None or len(hist) < 20:
            return None

        high = hist["High"].astype(float)
        low = hist["Low"].astype(float)
        close = hist["Close"].astype(float)
        prior_close = close.shift(1)

        true_range = pd.concat(
            [
                high - low,
                (high - prior_close).abs(),
                (low - prior_close).abs(),
            ],
            axis=1,
        ).max(axis=1)

        atr = safe_float(true_range.rolling(14).mean().iloc[-1])
        return atr if atr and atr > 0 else None
    except Exception:
        return None


# ============================================================
# DIAGNOSTIČNI ZGODOVINSKI TEST
# ============================================================

def backtest_ticker(ticker, holding_bars=12):
    """
    Omejen diagnostični pregled:
    - do približno 30 dni 5-minutnih Yahoo Finance podatkov
    - vstop na open naslednje sveče po signalu
    - izstop po holding_bars svečah
    - brez zgodovinskega earnings filtra, stroškov, zdrsa in modeliranja izvršitve
    """
    history = get_intraday_history(ticker, "30d")
    if history is None or history.empty:
        return []

    session_dates = sorted({stamp.date() for stamp in history.index})
    trades = []

    for session_date in session_dates:
        previous_close = get_previous_regular_close(history, session_date)
        if previous_close is None:
            continue

        for session_kind in ("premarket", "regular"):
            bars = get_session_bars(
                history,
                session_date,
                session_kind,
            )
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
                    close,
                    open_price,
                    prior_close,
                    current_vwap,
                    prior_vwap,
                )):
                    continue

                gap_pct = (close / previous_close - 1) * 100
                if not -8.0 <= gap_pct <= -1.0:
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
                    history,
                    timestamp,
                    bars,
                    index,
                )
                if volume_ratio is None or volume_ratio < 1.3:
                    continue

                momentum = (close / prior_close - 1) * 100
                if momentum <= 0:
                    continue

                entry_index = index + 1
                exit_index = min(
                    entry_index + holding_bars,
                    len(bars) - 1,
                )

                entry = safe_float(bars["Open"].iloc[entry_index])
                exit_price = safe_float(bars["Close"].iloc[exit_index])
                if not entry or not exit_price:
                    continue

                trades.append({
                    "Datum": str(session_date),
                    "Ticker": ticker,
                    "Seja": (
                        "Premarket"
                        if session_kind == "premarket"
                        else "Redna"
                    ),
                    "Vstop": round(entry, 2),
                    "Izhod": round(exit_price, 2),
                    "Donos %": round((exit_price / entry - 1) * 100, 2),
                })

                # Največ en signal na ticker na dan in sejo.
                break

    return trades


# ============================================================
# GEMINI: KOMENTAR PODATKOV, KI JIH JE SKENER DEJANSKO PRIKAZAL
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
        raise RuntimeError(
            "API ni vrnil modela, ki podpira generateContent."
        )

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
# ZAČETNI PRIKAZ IN SKENIRANJE
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
st.sidebar.caption("Yahoo Finance podatki so lahko zakasnjeni ali nepopolni.")
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Tržni režim:** {market['regime']}")

if market["spy_chg"] is not None:
    st.sidebar.caption(f"SPY 20d: {market['spy_chg']:+.2f}%")

held_ticker = st.sidebar.selectbox(
    "Delnica za večerni pregled",
    options=list(TICKERS_CONFIG.keys()),
    index=list(TICKERS_CONFIG.keys()).index("CRWD"),
)

st.title("Value Ledger 2.0")
st.caption(
    "Kandidati se izberejo dinamično iz podatkov, ki jih vrne Yahoo Finance. "
    "Ocene so hevristične, ne potrjene napovedi donosa."
)

st.sidebar.markdown("---")
if st.sidebar.button("Osveži skene"):
    scan_top_long.clear()
    scan_top_reversal.clear()
    get_fundamental_data.clear()
    get_intraday_history.clear()
    get_capital_rotation.clear()
    get_market_regime.clear()
    st.rerun()

with st.spinner("Skeniram fundamentalne in intraday podatke..."):
    top_long = scan_top_long(tuple(AI_UNIVERSE), 5)
    top_reversals = scan_top_reversal(tuple(AI_UNIVERSE), 5)

# ============================================================
# DINAMIČNI DVE KARTICI: BEST LONG IN BEST OBRAT
# ============================================================

long_candidate = None
if top_long and top_long[0]["score"] >= 6.5:
    long_candidate = top_long[0]

reversal_candidate = top_reversals[0] if top_reversals else None

long_col, reversal_col = st.columns(2)

with long_col:
    if long_candidate:
        item = long_candidate
        ticker = item["ticker"]
        price_context = get_three_year_price_context(ticker)
        atr = get_atr_value(ticker)
        stop = item["price"] - 1.5 * atr if atr and item.get("price") else None
        target1 = item["price"] + 1.5 * atr if atr and item.get("price") else None
        target2 = item["price"] + 2.5 * atr if atr and item.get("price") else None

        title = html.escape(item["name"])
        ticker_safe = html.escape(ticker)
        ps_text = display_value(item.get("ps"))
        peg_text = display_value(item.get("peg"))
        growth_text = display_value(
            item["revenue_growth"] * 100
            if item.get("revenue_growth") is not None
            else None,
            1,
            "%",
        )
        fcf_margin_text = display_value(item.get("fcf_margin"), 1, "%")
        fcf_yield_text = display_value(item.get("fcf_yield"), 1, "%")
        net_cash_text = display_value(item.get("net_cash"), 0)
        ws_text = display_value(wall_street_score(item), 1, "/10")
        coverage_text = f"{item['coverage']}%"
        historical_text = display_value(price_context, 1, "%")
        atr_text = (
            f"ATR {display_value(atr)} · STOP {display_value(stop)} · "
            f"T1 {display_value(target1)} · T2 {display_value(target2)}"
            if atr
            else "ATR ravni niso na voljo"
        )

        st.markdown(
            f"""
            <div class="hero-long">
              <div style="color:#FBBF24;font-size:0.78rem;font-weight:700;">
                FUNDAMENTALNI LONG · HEVRISTIČNI SKEN
              </div>
              <div style="font-size:1.55rem;font-weight:700;color:#FFFFFF;margin-top:5px;">
                {ticker_safe}
              </div>
              <div style="color:#CBD5E1;font-size:0.86rem;margin-top:2px;">
                {title}
              </div>
              <div style="color:#F8FAFC;font-size:1.05rem;margin-top:10px;">
                Cena {display_value(item.get("price"))} ·
                Ocena {item["score"]}/10
              </div>
              <div style="color:#CBD5E1;font-size:0.78rem;margin-top:8px;line-height:1.7;">
                P/S {ps_text} · PEG {peg_text} · Rast prihodkov {growth_text}<br>
                FCF marža {fcf_margin_text} · FCF yield {fcf_yield_text} ·
                Neto denar {net_cash_text}<br>
                WS približek {ws_text} · Pokritost podatkov {coverage_text}<br>
                Cena proti 3y mediani {historical_text}<br>
                {html.escape(atr_text)}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="hero-long">
              <div style="color:#FBBF24;font-size:0.78rem;font-weight:700;">
                FUNDAMENTALNI LONG · HEVRISTIČNI SKEN
              </div>
              <div style="font-size:1.35rem;font-weight:700;color:#FFFFFF;margin-top:12px;">
                NI STROGEGA KANDIDATA
              </div>
              <div style="color:#CBD5E1;font-size:0.82rem;margin-top:10px;">
                Noben ticker v trenutnem skenu ni dosegel minimalne ocene
                ob izpolnjenih filtrih za likvidnost, P/S, PEG in rast.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with reversal_col:
    if reversal_candidate:
        item = reversal_candidate
        ticker_safe = html.escape(item["Ticker"])
        st.markdown(
            f"""
            <div class="hero-reversal">
              <div style="color:#6EE7B7;font-size:0.78rem;font-weight:700;">
                NAJBOLJŠI UJEMANJE INTRADAY FILTROV · NI NAPOVED
              </div>
              <div style="font-size:1.55rem;font-weight:700;color:#FFFFFF;margin-top:5px;">
                {ticker_safe}
              </div>
              <div style="color:#CBD5E1;font-size:0.86rem;margin-top:2px;">
                {html.escape(item["Seja"])} · {html.escape(item["Čas"])}
              </div>
              <div style="color:#F8FAFC;font-size:1.05rem;margin-top:10px;">
                Cena {item["Cena"]} · Ocena {item["Ocena (hevristika)"]}/10
              </div>
              <div style="color:#CBD5E1;font-size:0.78rem;margin-top:8px;line-height:1.7;">
                Gap {item["Gap proti prejšnjemu close %"]:+.2f}% ·
                VWAP {item["VWAP"]} ({item["Odstopanje od VWAP %"]:+.2f}%)<br>
                Volumen proti isti uri {item["Volumen proti isti uri x"]}x ·
                RSI {item["RSI 5m"]} · Momentum {item["Momentum %"]:+.2f}%<br>
                Filtri vključujejo zeleno svečo, VWAP reclaim in preverjene earnings.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="hero-reversal">
              <div style="color:#6EE7B7;font-size:0.78rem;font-weight:700;">
                NAJBOLJŠI UJEMANJE INTRADAY FILTROV · NI NAPOVED
              </div>
              <div style="font-size:1.35rem;font-weight:700;color:#FFFFFF;margin-top:12px;">
                NI STROGEGA KANDIDATA
              </div>
              <div style="color:#CBD5E1;font-size:0.82rem;margin-top:10px;">
                Trenutno ni delnice, ki bi prestala vse pogoje. Skener ne bo
                izbral kandidata na silo.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.caption(
    "Zlata kartica pokaže najvišje uvrščen fundamentalni kandidat, če doseže "
    "oceno najmanj 6,5/10. Zelena kartica pokaže najvišje uvrščen današnji "
    "reversal kandidat. Obe oceni sta hevristični; ne zagotavljata uspešnega posla."
)


# ============================================================
# SEKTORSKA ROTACIJA
# ============================================================

st.subheader("Capital Rotation Radar")

pair_detail_html = (
    f"<div style='color:#94A3B8;font-size:0.82rem;margin-top:6px;'>"
    f"{html.escape(rotation['pair_detail'])}</div>"
    if rotation["pair_detail"]
    else ""
)

st.markdown(
    f"""
    <div class="ledger-card">
      <div style="color:#FBBF24;font-weight:700;font-size:1rem;">
        {html.escape(rotation["pair"])}
      </div>
      <div style="color:#94A3B8;font-size:0.82rem;margin-top:6px;">
        Tržni režim: {html.escape(market["regime"])}
      </div>
      {pair_detail_html}
    </div>
    """,
    unsafe_allow_html=True,
)

if rotation["rows"]:
    render_dark_table(pd.DataFrame(rotation["rows"]))
else:
    st.info("Sektorski podatki trenutno niso na voljo.")

st.caption(
    "ETF primerjava kaže relativno gibanje cen proti SPY, ne neposrednih "
    "nakupnih ali prodajnih tokov Wall Streeta."
)


# ============================================================
# TOP 5 LONG: ISTI PODATKI KOT ZLATA KARTICA
# ============================================================

st.subheader("TOP 5 Long · fundamentalni heuristični pregled")
st.caption(
    "Točkovanje je ročno določena hevristika, ne potrjen model pričakovanega "
    "donosa. P/S se med sektorji ne primerja kot enotna mera poštene vrednosti."
)

if top_long:
    long_rows = []

    for item in top_long:
        price_context = get_three_year_price_context(item["ticker"])
        growth = item.get("revenue_growth")
        atr = get_atr_value(item["ticker"])
        stop = item["price"] - 1.5 * atr if atr and item.get("price") else None
        target1 = item["price"] + 1.5 * atr if atr and item.get("price") else None

        long_rows.append({
            "Ticker": item["ticker"],
            "Podjetje": item["name"],
            "Ocena / 10": item["score"],
            "Pokritost %": item["coverage"],
            "Cena": display_value(item.get("price")),
            "P/S": display_value(item.get("ps")),
            "PEG": display_value(item.get("peg")),
            "Rast prihodkov %": display_value(
                growth * 100 if growth is not None else None,
                1,
                "%",
            ),
            "FCF marža %": display_value(item.get("fcf_margin"), 1, "%"),
            "FCF yield %": display_value(item.get("fcf_yield"), 1, "%"),
            "WS približek / 10": display_value(
                wall_street_score(item),
                1,
            ),
            "Cena proti 3y mediani %": display_value(
                price_context,
                1,
                "%",
            ),
            "ATR STOP": display_value(stop),
            "ATR T1": display_value(target1),
        })

    render_dark_table(pd.DataFrame(long_rows))
else:
    st.info(
        "Ni fundamentalnega kandidata, ki bi prestal trenutne filtre "
        "in dosegel minimalno oceno."
    )

st.caption(
    "»Cena proti 3y mediani« primerja ceno z zgodovinsko mediano cene; "
    "ni zgodovinski P/S in sama ne dokazuje podcenjenosti."
)


# ============================================================
# TOP 5 REVERSAL: ISTI PODATKI KOT ZELENA KARTICA
# ============================================================

st.subheader("TOP 5 Intraday Reversal")
st.caption(
    "Premarket in redna seja imata ločen VWAP. Volumen se primerja z isto "
    "5-minutno uro v preteklih sejah iste vrste."
)

if st.button("Osveži intraday skener"):
    scan_top_reversal.clear()
    get_intraday_history.clear()
    st.rerun()

# Uporabi lahko svež rezultat po pritisku gumba ali rezultat v cache-u.
top_reversals = scan_top_reversal(tuple(AI_UNIVERSE), 5)

if top_reversals:
    render_dark_table(pd.DataFrame(top_reversals))
else:
    st.info(
        "NI STROGEGA KANDIDATA. Filter zahteva gap od -1 % do -8 %, "
        "dejanski prehod izpod VWAP-a nad njega, zeleno zaključeno svečo, "
        "RSI pod 35, volumen vsaj 1,3× glede na isto uro, pozitiven momentum "
        "in uspešno preverjene earnings podatke."
    )

st.warning(
    "Premarket je pogosto manj likviden, podatki pa so lahko nepopolni. "
    "Prestani filtri pomenijo le ujemanje s pravili, ne pa zagotovila "
    "dobička ali potrditve za nakup."
)


# ============================================================
# DIAGNOSTIČNI BACKTEST
# ============================================================

st.subheader("Diagnostični zgodovinski test")
st.caption(
    "Do približno 30 dni 5-minutnih podatkov za izbrane tickre. Vstop je "
    "modeliran na naslednji sveči, izstop po 12 svečah. Brez zgodovinskega "
    "earnings filtra, provizij, zdrsa in realističnega modela izvršitve; "
    "rezultat ni dokaz trgovalne prednosti."
)

backtest_tickers = st.multiselect(
    "Tickerji za test",
    options=AI_UNIVERSE,
    default=["CRWD", "MNDY", "NOW"],
    max_selections=5,
)

if st.button("Zaženi diagnostični backtest"):
    if not backtest_tickers:
        st.warning("Izberi vsaj en ticker.")
    else:
        trades = []

        with st.spinner("Obdelujem zgodovinske 5-minutne podatke..."):
            for ticker in backtest_tickers:
                history = get_intraday_history(ticker, "30d")
                if history is None or history.empty:
                    continue

                session_dates = sorted({
                    stamp.date() for stamp in history.index
                })

                for session_date in session_dates:
                    previous_close = get_previous_regular_close(
                        history,
                        session_date,
                    )
                    if previous_close is None:
                        continue

                    for session_kind in ("premarket", "regular"):
                        bars = get_session_bars(
                            history,
                            session_date,
                            session_kind,
                        )
                        if len(bars) < 16:
                            continue

                        vwap = anchored_vwap_series(bars)
                        closes = bars["Close"].astype(float)
                        opens = bars["Open"].astype(float)

                        for index in range(15, len(bars) - 13):
                            close = safe_float(closes.iloc[index])
                            open_price = safe_float(opens.iloc[index])
                            previous_bar_close = safe_float(closes.iloc[index - 1])
                            current_vwap = safe_float(vwap.iloc[index])
                            previous_vwap = safe_float(vwap.iloc[index - 1])

                            if any(value is None for value in (
                                close,
                                open_price,
                                previous_bar_close,
                                current_vwap,
                                previous_vwap,
                            )):
                                continue

                            gap_pct = (close / previous_close - 1) * 100
                            if not -8 <= gap_pct <= -1:
                                continue

                            crossed_up = (
                                float(closes.iloc[index - 1]) <= previous_vwap
                                and close > current_vwap
                            )
                            if not crossed_up or close <= open_price:
                                continue

                            rsi = calculate_rsi(closes.iloc[:index + 1])
                            if rsi is None or rsi >= 35:
                                continue

                            timestamp = bars.index[index]
                            volume_ratio = same_time_volume_ratio(
                                history,
                                timestamp,
                                bars,
                                index,
                            )
                            if volume_ratio is None or volume_ratio < 1.3:
                                continue

                            momentum = (close / previous_bar_close - 1) * 100
                            if momentum <= 0:
                                continue

                            entry_index = index + 1
                            exit_index = min(entry_index + 12, len(bars) - 1)
                            entry = safe_float(bars["Open"].iloc[entry_index])
                            exit_price = safe_float(bars["Close"].iloc[exit_index])

                            if not entry or not exit_price:
                                continue

                            trades.append({
                                "Datum": str(session_date),
                                "Ticker": ticker,
                                "Seja": (
                                    "Premarket"
                                    if session_kind == "premarket"
                                    else "Redna"
                                ),
                                "Vstop": round(entry, 2),
                                "Izhod": round(exit_price, 2),
                                "Donos %": round(
                                    (exit_price / entry - 1) * 100,
                                    2,
                                ),
                            })

                            # Največ en signal na ticker na dan in sejo.
                            break

        backtest_frame = pd.DataFrame(trades)

        if backtest_frame.empty:
            st.info(
                "V pridobljenih podatkih ni bilo najdenega setupa po teh pravilih."
            )
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
                "To je omejen diagnostični izračun, ne potrjen backtest. "
                "Ne vključuje zgodovinskih earnings informacij, stroškov "
                "ali zdrsa."
            )


# ============================================================
# AI ANALITIK
# ============================================================

st.subheader("Avtonomni AI Analitik")
st.caption(
    "AI komentira dejanske podatke, prikazane v skenu. Ne sme si izmišljati "
    "manjkajočih meritev ali obljubljati donosa."
)

if st.button("Zaženi AI komentar trga"):
    if not gemini_api_key:
        st.error("Vnesi Gemini API ključ za AI komentar.")
    else:
        long_context = [
            {
                "ticker": item["ticker"],
                "score": item["score"],
                "coverage": item["coverage"],
                "price": item.get("price"),
                "ps": item.get("ps"),
                "peg": item.get("peg"),
                "revenue_growth": item.get("revenue_growth"),
                "fcf_margin": item.get("fcf_margin"),
                "fcf_yield": item.get("fcf_yield"),
                "net_cash": item.get("net_cash"),
                "analyst_upside": item.get("analyst_upside"),
            }
            for item in top_long
        ]

        prompt = f"""
Odgovori v slovenščini kot previden analitik.

Uporabi samo spodnje podatke. Ne izmišljaj si cen, novic, earnings datumov,
tokov kapitala ali prihodnjih donosov.
Relativna moč ETF-jev je cenovni približek, ne neposredno merjenje tokov denarja.
Fundamentalna ocena je hevristika, ne potrjena primerjava poštene vrednosti.
Če kandidatov ni, napiši "NI STROGEGA KANDIDATA".
Ne obljubljaj dobička in nobenega kandidata ne imenuj zagotovljenega zmagovalca.

Tržni režim: {market}
Sektorska relativna moč: {rotation}
Fundamentalni kandidati: {long_context}
Intraday reversal kandidati: {top_reversals}

Odgovori v treh kratkih delih:
1. Tržni režim in relativna moč sektorjev.
2. Kaj kažejo fundamentalni kandidati in katere so omejitve.
3. Ali je reversal kandidat prestal filtre; navedi samo podatke iz seznama.
Če je pomemben podatek manjkajoč, to jasno napiši.
"""

        try:
            with st.spinner("Pripravljam komentar prikazanih podatkov..."):
                model_name, report = get_gemini_comment(
                    gemini_api_key,
                    prompt,
                )

            st.caption(f"API model: {model_name}")
            st.markdown(report)

        except Exception as error:
            st.error(f"AI komentar ni uspel: {error}")


st.caption(
    "Podatki se osvežijo ob ponovnem zagonu aplikacije ali s klikom na "
    "Osveži skene. Aplikacija ne spremlja trga v ozadju in ne pošilja "
    "samodejnih opozoril."
)
