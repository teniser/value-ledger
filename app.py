import math
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import pytz
import requests
import streamlit as st
import yfinance as yf


# ------------------------------------------------------------
# Nastavitve in prikaz
# ------------------------------------------------------------

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
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: #E2E8F0 !important;
    }
    section[data-testid="stSidebar"] { background-color: #0A0D14 !important; }
    .ledger-card {
        background: rgba(13,17,28,0.7);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 16px;
        padding: 20px 24px;
        margin-bottom: 16px;
    }
    div.stButton > button {
        background: linear-gradient(135deg,#F59E0B 0%,#D97706 100%) !important;
        color:#0A0D14 !important;
        font-weight:600 !important;
        border:none !important;
        border-radius:10px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

NY_TZ = ZoneInfo("America/New_York")
LJ_TZ = ZoneInfo("Europe/Ljubljana")


# ------------------------------------------------------------
# Univerzum: razpršen seznam kandidatov, omejen na 150 unikatnih
# ------------------------------------------------------------

TICKER_CANDIDATES = [
    # SaaS, programska oprema in cloud
    "MNDY", "CRWD", "SNOW", "HUBS", "DDOG", "TEAM", "NOW", "PANW",
    "PLTR", "CRM", "ADBE", "SHOP", "NET", "ZS", "OKTA", "MDB",
    "ESTC", "PATH", "WDAY", "CFLT", "DOCN", "GTLB", "TOST", "BILL",
    "ASAN", "IOT", "FSLY", "DT", "BSY", "PCOR", "NCNO", "ZM",
    "DOCU", "TWLO", "PD", "DBX", "SMAR", "UPWK", "SPT", "APPN",
    "PEGA", "FROG", "RNG", "VEEV", "TYL", "PTC", "ADSK", "TRMB",

    # Večja tehnološka podjetja in internet
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
    "CRWD": {"name": "CrowdStrike", "sector": "Cyber"},
    "SNOW": {"name": "Snowflake", "sector": "Cloud"},
    "HUBS": {"name": "HubSpot", "sector": "SaaS"},
    "DELL": {"name": "Dell", "sector": "Hardware"},
    "DDOG": {"name": "Datadog", "sector": "Cloud"},
    "TEAM": {"name": "Atlassian", "sector": "Software"},
    "NOW": {"name": "ServiceNow", "sector": "Software"},
    "PANW": {"name": "Palo Alto Networks", "sector": "Cyber"},
    "PLTR": {"name": "Palantir", "sector": "Software"},
}


# ------------------------------------------------------------
# Makro in relativna moč sektorjev
# ------------------------------------------------------------

@st.cache_data(ttl=900, show_spinner=False)
def get_market_regime():
    try:
        df = yf.Ticker("SPY").history(
            period="6mo", interval="1d", auto_adjust=True
        )
        if df is None or len(df) < 60:
            return {"regime": "NEZNANO", "spy_chg": None, "penalty": 0.0}

        close = df["Close"].dropna().astype(float)
        if len(close) < 50:
            return {"regime": "NEZNANO", "spy_chg": None, "penalty": 0.0}

        sma50 = float(close.rolling(50).mean().iloc[-1])
        last = float(close.iloc[-1])
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
    # Relativna donosnost cen ETF-jev proti SPY ni neposreden podatek o tokovih kapitala.
    etfs = {
        "SaaS / software (IGV)": "IGV",
        "Semis (SMH)": "SMH",
        "Cyber (CIBR)": "CIBR",
        "Nasdaq (QQQ)": "QQQ",
        "Finance (XLF)": "XLF",
        "Health care (XLV)": "XLV",
        "Energy (XLE)": "XLE",
        "Industrials (XLI)": "XLI",
        "Consumer discretionary (XLY)": "XLY",
        "Consumer staples (XLP)": "XLP",
        "Materials (XLB)": "XLB",
        "Utilities (XLU)": "XLU",
        "Small caps (IWM)": "IWM",
    }

    closes = {}
    for ticker in list(etfs.values()) + ["SPY"]:
        try:
            hist = yf.Ticker(ticker).history(
                period="8mo", interval="1d", auto_adjust=True
            )
            if hist is not None and not hist.empty:
                closes[ticker] = hist["Close"].dropna().astype(float)
        except Exception:
            continue

    if "SPY" not in closes:
        return {
            "rows": [],
            "pair": "NI PODATKOV",
            "pair_detail": "",
        }

    def relative_return(series, benchmark, days):
        joined = pd.concat(
            [series.rename("sector"), benchmark.rename("spy")],
            axis=1,
            join="inner",
        ).dropna()
        if len(joined) <= days:
            return None
        sector_return = (joined["sector"].iloc[-1] / joined["sector"].iloc[-1-days] - 1) * 100
        spy_return = (joined["spy"].iloc[-1] / joined["spy"].iloc[-1-days] - 1) * 100
        return float(sector_return - spy_return)

    rows = []
    for label, ticker in etfs.items():
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
            "sektor": label,
            "r5": round(r5, 1),
            "r20": round(r20, 1),
            "r60": round(r60, 1),
            "status": status,
        })

    rows.sort(key=lambda row: row["r20"], reverse=True)

    pair = "NI PODATKOV"
    detail = ""
    if "IGV" in closes and "SMH" in closes:
        joined = pd.concat(
            [closes["IGV"].rename("igv"), closes["SMH"].rename("smh")],
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
                f"razmerje nad SMA20: {'da' if above_sma20 else 'ne'}"
            )

    return {"rows": rows, "pair": pair, "pair_detail": detail}


market = get_market_regime()
rotation = get_capital_rotation()


# ------------------------------------------------------------
# Osnovni podatki in dolgoročni pregled
# ------------------------------------------------------------

@st.cache_data(ttl=1800, show_spinner=False)
def get_fundamental_data(ticker):
    try:
        info = yf.Ticker(ticker).info or {}

        def number(key):
            value = info.get(key)
            try:
                value = float(value)
                return value if math.isfinite(value) else None
            except (TypeError, ValueError):
                return None

        price = number("currentPrice") or number("regularMarketPrice")
        market_cap = number("marketCap")
        avg_volume = number("averageVolume")
        ps = number("priceToSalesTrailing12Months")
        peg = number("pegRatio")
        revenue_growth = number("revenueGrowth")
        cash = number("totalCash")
        debt = number("totalDebt")
        fcf = number("freeCashflow")
        revenue = number("totalRevenue")
        analyst_rec = number("recommendationMean")
        analyst_count = number("numberOfAnalystOpinions")
        target = number("targetMeanPrice") or number("targetMedianPrice")

        if revenue_growth is not None and revenue_growth > 1:
            revenue_growth /= 100

        fcf_margin = None
        if fcf is not None and revenue not in (None, 0):
            fcf_margin = fcf / revenue * 100

        dollar_volume = None
        if price is not None and avg_volume is not None:
            dollar_volume = price * avg_volume

        analyst_upside = None
        if price and target:
            analyst_upside = (target / price - 1) * 100

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
            "growth": revenue_growth,
            "fcf_margin": fcf_margin,
            "net_cash": net_cash,
            "analyst_rec": analyst_rec,
            "analyst_count": analyst_count,
            "analyst_upside": analyst_upside,
        }
    except Exception:
        return None


@st.cache_data(ttl=1800, show_spinner=False)
def get_three_year_price_context(ticker):
    # To je zgodovinski položaj CENE, ne zgodovinski P/S ali dokaz podcenjenosti.
    try:
        hist = yf.Ticker(ticker).history(
            period="3y", interval="1wk", auto_adjust=True
        )
        if hist is None or hist.empty or "Close" not in hist:
            return None

        closes = hist["Close"].dropna().astype(float)
        if len(closes) < 50:
            return None

        median_price = float(closes.median())
        current_price = float(closes.iloc[-1])
        if median_price <= 0:
            return None

        return round((current_price / median_price - 1) * 100, 1)
    except Exception:
        return None


def fundamental_score(data):
    if not data or not data.get("price"):
        return None

    score = 5.0

    ps = data.get("ps")
    if ps is not None and ps > 0:
        if ps < 4:
            score += 1.5
        elif ps < 8:
            score += 1.0
        elif ps > 25:
            score -= 1.0

    peg = data.get("peg")
    if peg is not None and peg > 0:
        if peg < 1:
            score += 1.0
        elif peg < 1.5:
            score += 0.5
        elif peg > 3:
            score -= 1.0

    growth = data.get("growth")
    if growth is not None:
        if growth > 0.25:
            score += 1.0
        elif growth > 0.10:
            score += 0.5
        elif growth < 0:
            score -= 1.0

    fcf_margin = data.get("fcf_margin")
    if fcf_margin is not None:
        if fcf_margin > 15:
            score += 0.75
        elif fcf_margin < 0:
            score -= 0.75

    net_cash = data.get("net_cash")
    if net_cash is not None:
        if net_cash > 0:
            score += 0.5
        else:
            score -= 0.5

    analyst_upside = data.get("analyst_upside")
    if analyst_upside is not None:
        if analyst_upside > 20:
            score += 0.5
        elif analyst_upside < -10:
            score -= 0.5

    score -= market["penalty"]
    return round(max(0.0, min(10.0, score)), 1)


def passes_liquidity(data):
    # Če tržni kapitalizaciji ali dolarskemu prometu ni podatka, delnice ne štejemo
    # kot potrjeno likvidne.
    return bool(
        data
        and data.get("market_cap") is not None
        and data.get("dollar_volume") is not None
        and data["market_cap"] >= 2_000_000_000
        and data["dollar_volume"] >= 20_000_000
    )


@st.cache_data(ttl=1800, show_spinner=False)
def scan_top_long(universe, n=5):
    rows = []

    for ticker in universe:
        data = get_fundamental_data(ticker)
        if not data or not passes_liquidity(data):
            continue

        score = fundamental_score(data)
        if score is None:
            continue

        # Ne uporabljamo izmišljenih nadomestnih vrednosti za manjkajoče P/S ali PEG.
        ps = data.get("ps")
        peg = data.get("peg")
        growth = data.get("growth")

        if ps is not None and (ps <= 0 or ps > 20):
            continue
        if peg is not None and peg > 2.8:
            continue
        if growth is not None and growth < 0.12:
            continue

        rows.append({**data, "score": score})

    rows.sort(key=lambda row: row["score"], reverse=True)
    return rows[:n]


# ------------------------------------------------------------
# Intraday podatki: ločena premarket in redna seja
# ------------------------------------------------------------

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

        # V Yahoo podatkih so lahko tudi after-hours sveče. Za ta signal jih izločimo.
        local_times = [stamp.time() for stamp in hist.index]
        keep = [
            time(4, 0) <= current_time < time(16, 0)
            for current_time in local_times
        ]
        hist = hist.loc[keep].copy()
        return hist if not hist.empty else None
    except Exception:
        return None


def session_type(timestamp):
    return "premarket" if timestamp.time() < time(9, 30) else "regular"


def get_session_bars(history, session_date, kind):
    if history is None or history.empty:
        return pd.DataFrame()

    same_day = history[
        [stamp.date() == session_date for stamp in history.index]
    ].copy()

    if same_day.empty:
        return same_day

    if kind == "premarket":
        return same_day.between_time("04:00", "09:29")
    return same_day.between_time("09:30", "15:59")


def get_previous_regular_close(history, session_date):
    if history is None or history.empty:
        return None

    earlier = history[[stamp.date() < session_date for stamp in history.index]]
    if earlier.empty:
        return None

    previous_date = max(stamp.date() for stamp in earlier.index)
    previous_regular = get_session_bars(history, previous_date, "regular")
    if previous_regular.empty:
        return None

    value = float(previous_regular["Close"].iloc[-1])
    return value if math.isfinite(value) and value > 0 else None


def anchored_vwap_series(bars):
    if bars is None or bars.empty:
        return pd.Series(dtype=float)

    high = bars["High"].astype(float)
    low = bars["Low"].astype(float)
    close = bars["Close"].astype(float)
    volume = bars["Volume"].astype(float).clip(lower=0)

    # HLC3 VWAP, kumulativen samo od začetka izbrane seje.
    typical_price = (high + low + close) / 3
    cumulative_volume = volume.cumsum().replace(0, float("nan"))
    return (typical_price * volume).cumsum() / cumulative_volume


def volume_ratio_for_bar(history, timestamp, current_session, index_in_session):
    # Primarna primerjava: ista 5-minutna ura in ista vrsta seje v preteklih dneh.
    clock_time = timestamp.strftime("%H:%M")
    kind = session_type(timestamp)
    prior_values = []

    if history is not None and not history.empty:
        prior_dates = sorted({
            stamp.date()
            for stamp in history.index
            if stamp.date() < timestamp.date()
        })

        for prior_date in prior_dates[-5:]:
            prior_bars = get_session_bars(history, prior_date, kind)
            if prior_bars.empty:
                continue

            matches = [
                stamp for stamp in prior_bars.index
                if stamp.strftime("%H:%M") == clock_time
            ]
            if matches:
                value = float(prior_bars.loc[matches[-1], "Volume"])
                if math.isfinite(value) and value > 0:
                    prior_values.append(value)

    current_volume = float(current_session["Volume"].iloc[index_in_session])
    if current_volume <= 0:
        return None

    if prior_values:
        reference = float(pd.Series(prior_values).median())
    else:
        # Brez zgodovinske primerljive sveče ne razglasimo volumna za potrjen.
        return None

    if reference <= 0:
        return None
    return current_volume / reference


def calculate_rsi(close, period=14):
    close = pd.Series(close, dtype=float)
    if len(close) < period + 1:
        return None

    change = close.diff()
    gains = change.clip(lower=0)
    losses = -change.clip(upper=0)

    avg_gain = gains.rolling(period).mean()
    avg_loss = losses.rolling(period).mean()

    latest_gain = avg_gain.iloc[-1]
    latest_loss = avg_loss.iloc[-1]

    if pd.isna(latest_gain) or pd.isna(latest_loss):
        return None
    if latest_loss == 0:
        return 100.0 if latest_gain > 0 else 50.0

    rs = latest_gain / latest_loss
    return float(100 - (100 / (1 + rs)))


def get_earnings_status(ticker, days=5):
    # True = datum je v obdobju; False = preverjeni podatki ne kažejo datuma;
    # None = datuma ni bilo mogoče zanesljivo pridobiti.
    try:
        dates = yf.Ticker(ticker).get_earnings_dates(limit=8)
        if dates is None or len(dates) == 0:
            return None

        now = datetime.now(NY_TZ).date()
        for value in dates.index:
            date_value = pd.Timestamp(value)
            if date_value.tzinfo is not None:
                date_value = date_value.tz_convert(None)
            earnings_date = date_value.date()
            delta = (earnings_date - now).days
            if 0 <= delta <= days:
                return True
        return False
    except Exception:
        return None


def make_reversal_signal(history, session_date, now_ny=None):
    if history is None or history.empty:
        return None

    if now_ny is None:
        now_ny = datetime.now(NY_TZ)

    if session_date != now_ny.date():
        return None

    day = history[[stamp.date() == session_date for stamp in history.index]].copy()
    if day.empty:
        return None

    # Izločimo sve 5-minutne sveče, ki še niso zaključene.
    completed = day[
        [stamp + timedelta(minutes=5) <= now_ny for stamp in day.index]
    ]
    if completed.empty:
        return None

    last_stamp = completed.index[-1]
    kind = session_type(last_stamp)
    bars = get_session_bars(history, session_date, kind)

    bars = bars[
        [stamp + timedelta(minutes=5) <= now_ny for stamp in bars.index]
    ]
    if len(bars) < 15:
        return None

    last_stamp = bars.index[-1]
    last_index = len(bars) - 1
    previous_close = get_previous_regular_close(history, session_date)
    if previous_close is None:
        return None

    last_close = float(bars["Close"].iloc[-1])
    last_open = float(bars["Open"].iloc[-1])
    prior_close = float(bars["Close"].iloc[-2])
    gap_pct = (last_close / previous_close - 1) * 100

    if not -8.0 <= gap_pct <= -1.0:
        return None

    vwap = anchored_vwap_series(bars)
    if len(vwap) < 2 or pd.isna(vwap.iloc[-1]) or pd.isna(vwap.iloc[-2]):
        return None

    # Dejanski preboj: prejšnja zaključena sveča pod svojim VWAP-om,
    # zadnja zaključena sveča pa nad svojim VWAP-om.
    crossed_up = (
        float(bars["Close"].iloc[-2]) <= float(vwap.iloc[-2])
        and last_close > float(vwap.iloc[-1])
    )
    green_candle = last_close > last_open

    rsi = calculate_rsi(bars["Close"])
    if rsi is None or rsi >= 35:
        return None

    volume_ratio = volume_ratio_for_bar(
        history, last_stamp, bars, last_index
    )
    if volume_ratio is None or volume_ratio < 1.3:
        return None

    momentum = (last_close / prior_close - 1) * 100 if prior_close else 0
    if momentum <= 0:
        return None

    if not crossed_up or not green_candle:
        return None

    earnings = get_earnings_status(history.attrs.get("ticker", ""), 5)
    if earnings is not False:
        # Če so earnings v naslednjih petih dneh ali jih ni mogoče preveriti,
        # signal ne dobi oznake potrjenega kandidata.
        return None

    vwap_distance = (last_close / float(vwap.iloc[-1]) - 1) * 100
    score = 6.0
    score += min(max(volume_ratio - 1.3, 0) * 0.5, 1.5)
    score += min(max(momentum, 0) * 0.25, 1.0)
    score -= market["penalty"]
    score = round(max(0.0, min(10.0, score)), 1)

    if score < 6.0:
        return None

    return {
        "time": last_stamp.strftime("%H:%M ET"),
        "session": "PREMARKET" if kind == "premarket" else "REDNA SEJA",
        "price": round(last_close, 2),
        "gap_pct": round(gap_pct, 2),
        "vwap": round(float(vwap.iloc[-1]), 2),
        "vwap_pct": round(vwap_distance, 2),
        "volume_ratio": round(volume_ratio, 2),
        "rsi": round(rsi, 1),
        "momentum": round(momentum, 2),
        "score": score,
    }


@st.cache_data(ttl=90, show_spinner=False)
def scan_top_reversal(universe, n=5):
    now_ny = datetime.now(NY_TZ)
    results = []

    for ticker in universe:
        history = get_intraday_history(ticker, "5d")
        if history is None or history.empty:
            continue

        # Ticker shranimo v attrs za earnings funkcijo.
        history.attrs["ticker"] = ticker
        signal = make_reversal_signal(history, now_ny.date(), now_ny)
        if signal:
            signal["ticker"] = ticker
            results.append(signal)

    results.sort(key=lambda row: row["score"], reverse=True)
    return results[:n]


# ------------------------------------------------------------
# Preprost diagnostični backtest na 5-minutnih podatkih
# ------------------------------------------------------------

def backtest_one_ticker(ticker, holding_bars=12):
    history = get_intraday_history(ticker, "30d")
    if history is None or history.empty:
        return []

    history.attrs["ticker"] = ticker
    session_dates = sorted({stamp.date() for stamp in history.index})
    trades = []

    for session_date in session_dates:
        previous_close = get_previous_regular_close(history, session_date)
        if previous_close is None:
            continue

        # Backtest ne uporablja prihajajočih earnings podatkov kot znanih
        # zgodovinskih dejstev. Zato je rezultat diagnostičen, ne investicijski.
        day = history[[stamp.date() == session_date for stamp in history.index]]
        if day.empty:
            continue

        for kind in ("premarket", "regular"):
            bars = get_session_bars(history, session_date, kind)
            if len(bars) < 16:
                continue

            vwap = anchored_vwap_series(bars)
            closes = bars["Close"].astype(float)
            opens = bars["Open"].astype(float)

            for i in range(15, len(bars) - holding_bars):
                current_stamp = bars.index[i]
                current_close = float(closes.iloc[i])
                current_open = float(opens.iloc[i])
                previous_bar_close = float(closes.iloc[i - 1])

                gap_pct = (current_close / previous_close - 1) * 100
                if not -8.0 <= gap_pct <= -1.0:
                    continue

                current_vwap = vwap.iloc[i]
                prior_vwap = vwap.iloc[i - 1]
                if pd.isna(current_vwap) or pd.isna(prior_vwap):
                    continue

                crossed_up = (
                    float(closes.iloc[i - 1]) <= float(prior_vwap)
                    and current_close > float(current_vwap)
                )
                if not crossed_up or current_close <= current_open:
                    continue

                rsi = calculate_rsi(closes.iloc[:i + 1])
                if rsi is None or rsi >= 35:
                    continue

                volume_ratio = volume_ratio_for_bar(
                    history, current_stamp, bars, i
                )
                if volume_ratio is None or volume_ratio < 1.3:
                    continue

                momentum = (
                    (current_close / previous_bar_close - 1) * 100
                    if previous_bar_close else 0
                )
                if momentum <= 0:
                    continue

                # Signal se pozna šele ob zaključku sveče; vstop je naslednja
                # sveča na open, izhod po izbranem številu sveč na close.
                entry_index = i + 1
                exit_index = min(entry_index + holding_bars, len(bars) - 1)
                entry = float(bars["Open"].iloc[entry_index])
                exit_price = float(bars["Close"].iloc[exit_index])

                if entry <= 0:
                    continue

                return_pct = (exit_price / entry - 1) * 100
                trades.append({
                    "Datum": str(session_date),
                    "Ticker": ticker,
                    "Seja": "Premarket" if kind == "premarket" else "Redna",
                    "Vstop": round(entry, 2),
                    "Izhod": round(exit_price, 2),
                    "Donos %": round(return_pct, 2),
                })

                # Največ en trade na ticker na dan in vrsto seje.
                break

    return trades


def run_backtest(tickers):
    all_trades = []
    for ticker in tickers:
        all_trades.extend(backtest_one_ticker(ticker))
    return pd.DataFrame(all_trades)


# ------------------------------------------------------------
# Gemini: komentar na podatke, ne samostojen izbirnik signalov
# ------------------------------------------------------------

def call_gemini(api_key, prompt_text):
    clean_key = api_key.strip()
    if not clean_key:
        raise ValueError("Vnesi Gemini API ključ.")

    response = requests.get(
        "https://generativelanguage.googleapis.com/v1beta/models",
        params={"key": clean_key},
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

    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    last_error = "Ni uspelo poklicati razpoložljivega modela."

    for model_name in model_names:
        try:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model_name}:generateContent"
            )
            result = requests.post(
                url,
                params={"key": clean_key},
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
                    part.get("text", "") for part in parts
                    if part.get("text")
                )
                if text:
                    return model_name, text
            last_error = f"{model_name}: HTTP {result.status_code} {result.text[:250]}"
        except Exception as error:
            last_error = str(error)

    raise RuntimeError(last_error)


# ------------------------------------------------------------
# Vmesnik
# ------------------------------------------------------------

local_now = datetime.now(LJ_TZ)
st.markdown(
    f"""
    <div style="border-bottom:1px solid rgba(255,255,255,0.08);
                padding-bottom:12px;margin-bottom:18px;">
      <h1 style="margin:0;">
        <span style="color:#F59E0B;">THE VALUE LEDGER</span>
        <span style="color:#60A5FA;">2.0</span>
      </h1>
      <p style="color:#94A3B8;">
        Kvantitativni pregled · {local_now.strftime("%d.%m.%Y %H:%M")} Ljubljana
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown("### Nastavitve")
api_key = st.sidebar.text_input(
    "Gemini API ključ (neobvezno)",
    type="password",
)

st.sidebar.caption(
    f"Unikatni tickerji v skenerju: {len(AI_UNIVERSE)}"
)
st.sidebar.caption(
    "Podatki Yahoo Finance so lahko zakasnjeni ali nepopolni."
)
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Tržni režim:** {market['regime']}")
if market["spy_chg"] is not None:
    st.sidebar.caption(f"SPY 20-dnevna sprememba: {market['spy_chg']:+.2f}%")

held_options = list(TICKERS_CONFIG.keys())
held_ticker = st.sidebar.selectbox(
    "Delnica za večerni pregled",
    options=held_options,
    index=held_options.index("CRWD"),
)

st.title("Value Ledger 2.0")
st.caption(
    "Skener označi kandidate po pravilih. Ne napoveduje zagotovljenega "
    "dobička in ne oddaja naročil."
)

st.subheader("Sektorska relativna moč")
st.markdown(
    f"**IGV proti SMH:** {rotation['pair']}  \n"
    f"{rotation['pair_detail']}"
)
if rotation["rows"]:
    st.dataframe(
        pd.DataFrame(rotation["rows"]).rename(columns={
            "sektor": "Sektor / ETF",
            "r5": "Rel. 5d % vs SPY",
            "r20": "Rel. 20d % vs SPY",
            "r60": "Rel. 60d % vs SPY",
            "status": "Oznaka",
        }),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("Za sektorsko primerjavo trenutno ni dovolj podatkov.")

st.caption(
    "Relativna moč temelji na cenah ETF-jev proti SPY. To ni neposreden "
    "merilnik nakupnih ali prodajnih tokov Wall Streeta."
)

st.subheader("TOP 5 Long · temeljni pregled")
with st.spinner("Pregledujem fundamentalne podatke univerzuma..."):
    top_long = scan_top_long(tuple(AI_UNIVERSE), 5)

if top_long:
    long_rows = []
    for item in top_long:
        price_context = get_three_year_price_context(item["ticker"])
        growth = item.get("growth")
        long_rows.append({
            "Ticker": item["ticker"],
            "Podjetje": item["name"],
            "Ocena": item["score"],
            "Cena": round(item["price"], 2) if item.get("price") else None,
            "P/S": round(item["ps"], 2) if item.get("ps") is not None else None,
            "PEG": round(item["peg"], 2) if item.get("peg") is not None else None,
            "Rast prihodkov %": round(growth * 100, 1) if growth is not None else None,
            "FCF marža %": round(item["fcf_margin"], 1) if item.get("fcf_margin") is not None else None,
            "Neto denar": round(item["net_cash"]) if item.get("net_cash") is not None else None,
            "Analitiki": item.get("analyst_count"),
            "Ciljna rast %": round(item["analyst_upside"], 1) if item.get("analyst_upside") is not None else None,
            "Cena proti 3y mediani %": price_context,
        })

    st.dataframe(
        pd.DataFrame(long_rows),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("Ni kandidata, ki bi prestal razpoložljive filtre in podatkovne kontrole.")

st.caption(
    "»Cena proti 3y mediani« je primerjava trenutne cene z mediano zgodovinske "
    "cene. Ni zgodovinski P/S in sama po sebi ne pomeni, da je delnica podcenjena."
)

st.subheader("TOP 5 Intraday reversal · strogi pogoji")
st.caption(
    "Premarket VWAP se računa samo iz premarket sveč od 04:00 ET; "
    "redni VWAP se znova začne ob 09:30 ET. Volumen se primerja z isto "
    "5-minutno uro v preteklih sejah."
)

with st.spinner("Skeniram intraday podatke..."):
    top_reversals = scan_top_reversal(tuple(AI_UNIVERSE), 5)

if top_reversals:
    st.dataframe(
        pd.DataFrame(top_reversals).rename(columns={
            "ticker": "Ticker",
            "time": "Čas",
            "session": "Seja",
            "price": "Cena",
            "gap_pct": "Sprememba proti prejšnjemu close %",
            "vwap": "Sejni VWAP",
            "vwap_pct": "Odstopanje od VWAP %",
            "volume_ratio": "Volumen proti isti uri x",
            "rsi": "RSI 5m",
            "momentum": "Momentum %",
            "score": "Ocena",
        }),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info(
        "NI STROGEGA KANDIDATA. Signal zahteva padec proti prejšnjemu "
        "close-u, potrjen preboj VWAP-a, RSI < 35, zeleno svečo, "
        "volumen ≥ 1,3x, pozitiven momentum in preverjene earnings podatke."
    )

st.warning(
    "Predmarketni signal je posebej občutljiv na nizko likvidnost in "
    "nepopolne podatke. Oznaka pomeni, da so pravila prestana, ne pa "
    "da je setup A+ ali da bo trade dobičkonosen."
)

st.subheader("Capital Rotation Radar")
col_rotation, col_evening = st.columns(2)

with col_rotation:
    st.markdown("**Makro režim:** " + market["regime"])
    st.markdown("**SaaS / semis:** " + rotation["pair"])
    if rotation["pair_detail"]:
        st.caption(rotation["pair_detail"])

with col_evening:
    st.markdown("**Izbrana delnica:** " + held_ticker)
    st.caption(
        "Ta verzija ne izpiše avtomatičnega »drži/prodaj čez noč« priporočila."
    )

st.subheader("Diagnostični zgodovinski test")
st.caption(
    "Uporablja 30-dnevne 5-minutne podatke, vstop na naslednji sveči in "
    "izhod po 12 svečah. Ne vključuje earnings filtra, provizij, zdrsa ali "
    "realističnega izvrševanja naročil. Rezultate obravnavaj kot začetno "
    "diagnostiko, ne kot dokaz prednosti strategije."
)

backtest_tickers = st.multiselect(
    "Tickerji za test (omeji jih, da skeniranje ne bo predolgo)",
    options=AI_UNIVERSE,
    default=["CRWD", "MNDY", "NOW"],
    max_selections=10,
)

if st.button("Zaženi diagnostični backtest"):
    if not backtest_tickers:
        st.warning("Izberi vsaj en ticker.")
    else:
        with st.spinner("Prenos in preverjanje zgodovinskih 5-minutnih podatkov..."):
            trades_df = run_backtest(backtest_tickers)

        if trades_df.empty:
            st.info(
                "V pridobljenem obdobju ni bilo signalov po vseh izbranih pravilih."
            )
        else:
            wins = int((trades_df["Donos %"] > 0).sum())
            total = len(trades_df)
            win_rate = wins / total * 100
            average_return = float(trades_df["Donos %"].mean())
            median_return = float(trades_df["Donos %"].median())

            metric1, metric2, metric3, metric4 = st.columns(4)
            metric1.metric("Število poslov", total)
            metric2.metric("Pozitivni posli", f"{win_rate:.1f}%")
            metric3.metric("Povprečni donos", f"{average_return:.2f}%")
            metric4.metric("Mediani donos", f"{median_return:.2f}%")

            st.dataframe(
                trades_df,
                use_container_width=True,
                hide_index=True,
            )

            st.warning(
                "To ni potrjen backtest strategije: vzorec je kratek, "
                "predmarketna izvedba je lahko nerealistična, podatki so "
                "odvisni od Yahoo Finance, rezultati pa ne vključujejo "
                "transakcijskih stroškov ali zdrsa."
            )

st.subheader("Avtonomni AI Analitik")
st.caption(
    "Analitik komentira podatke, ki jih skener dejansko prikaže. "
    "Ne sme si izmišljati manjkajočih metrik ali kandidata razglasiti za "
    "zagotovljen zmagovalni trade."
)

if st.button("Zaženi AI komentar trga"):
    if not api_key:
        st.error("Za AI komentar vnesi Gemini API ključ.")
    else:
        reversal_context = (
            pd.DataFrame(top_reversals).to_dict(orient="records")
            if top_reversals else []
        )
        long_context = [
            {
                "ticker": row["ticker"],
                "score": row["score"],
                "ps": row.get("ps"),
                "peg": row.get("peg"),
                "growth": row.get("growth"),
                "fcf_margin": row.get("fcf_margin"),
                "analyst_upside": row.get("analyst_upside"),
            }
            for row in top_long
        ]

        prompt = f"""
Deluj kot previden analitik podatkov, ne kot promotor delnic.
Odgovori v slovenščini.

Uporabi samo naslednje podatke; ne izmišljaj si manjkajočih vrednosti,
novic, earnings datumov, tokov kapitala ali prihodnjih donosov.
Če ni ustreznega reversal kandidata, jasno napiši "NI STROGEGA KANDIDATA".
Ne trdi, da je signal A+, zagotovljen ali dobičkonosen.
ETF relativna moč je cenovni približek, ne neposreden podatek o denarnih tokovih.

Tržni režim: {market}
Relativna rotacija sektorjev: {rotation}
TOP long podatki: {long_context}
Reversal kandidati: {reversal_context}

Podaj:
1. Kratek povzetek režima in sektorske relativne moči.
2. Kaj podatki podpirajo in česa ne morejo potrditi.
3. Pri reversal kandidatih navedi dejanske kriterije in metrike.
4. Če podatki manjkajo ali so nezanesljivi, to izrecno povej.
"""

        try:
            with st.spinner("Pripravljam komentar na prikazane podatke..."):
                model_name, report = call_gemini(api_key, prompt)
            st.markdown(f"**Uporabljeni API model:** `{model_name}`")
            st.markdown(report)
        except Exception as error:
            st.error(f"AI komentar ni uspel: {error}")

st.caption(
    "Skeniranje se izvede ob nalaganju oziroma ponovnem zagonu aplikacije. "
    "Za sveže podatke uporabi Streamlitovo osvežitev strani; aplikacija "
    "sama ne pošilja opozoril v ozadju."
)
