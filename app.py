import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime, time
import pytz

st.set_page_config(
    page_title="The Value Ledger 2.0 Terminal",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
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
    background: linear-gradient(145deg, rgba(20,17,10,0.8) 0%, rgba(10,9,6,0.9) 100%);
    border: 1.5px solid rgba(245,158,11,0.6);
    border-radius: 18px;
    padding: 24px 26px;
    margin-bottom: 22px;
    box-shadow: 0 0 30px rgba(245,158,11,0.12);
}
.aplus-badge {
    display: inline-flex; align-items: center;
    border: 1.2px solid #F59E0B; color: #FBBF24;
    font-family: 'Space Grotesk', sans-serif; font-weight: 600;
    font-size: 0.76rem; padding: 3px 12px; border-radius: 9999px;
}
.badge-sector {
    font-family: 'Space Grotesk', sans-serif; font-size: 0.7rem; padding: 3px 8px; border-radius: 6px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    color: #94A3B8; text-transform: uppercase;
}
.metrics-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(130px,1fr));
    gap: 12px; margin: 16px 0; padding: 14px 18px;
    background: rgba(0,0,0,0.25); border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.03);
}
.metric-label { color:#94A3B8; font-size:0.7rem; text-transform:uppercase; margin-bottom:3px; font-family:'Space Grotesk',sans-serif; }
.metric-value { font-family:'JetBrains Mono',monospace; font-size:1.02rem; color:#F8FAFC; }
div.stButton > button {
    background: linear-gradient(135deg,#F59E0B 0%,#D97706 100%) !important;
    color:#0A0D14 !important; font-weight:600 !important;
    font-family:'Space Grotesk',sans-serif !important;
    border:none !important; border-radius:10px !important; padding:12px 24px !important;
}
.preclose-banner {
    background: linear-gradient(135deg, rgba(127,29,29,0.92) 0%, rgba(69,10,10,0.96) 100%);
    border: 1px solid rgba(248,113,113,0.55);
    border-radius: 18px; padding: 18px 20px; margin: 16px 0 22px 0;
}
</style>""", unsafe_allow_html=True)

st.sidebar.markdown("### Google AI Nastavitev")
api_key = st.sidebar.text_input("Vnesite brezplacni Gemini API kljuc:", type="password")

TICKERS_CONFIG = {
    "MNDY": {"name": "monday.com", "sector": "SaaS / Work OS", "category": "No1 Asimetricni Zmagovalec", "growth": 24.2, "fcf_margin": 21.8, "r40": 46.0, "peg": 0.62, "sentiment": 9.1, "makro": 8.5, "temelji": 9.2, "podcenjenost": 9.5},
    "CRWD": {"name": "CrowdStrike", "sector": "Kibernetska varnost", "category": "No1 Takticni Obrat Dneva", "growth": 28.0, "fcf_margin": 32.0, "r40": 60.0, "peg": 1.80, "sentiment": 9.5, "makro": 8.5, "temelji": 9.5, "podcenjenost": 6.5},
    "SNOW": {"name": "Snowflake", "sector": "AI Podatki", "category": "Na opazovanju", "growth": 28.0, "fcf_margin": 27.0, "r40": 55.0, "peg": 1.70, "sentiment": 8.2, "makro": 8.3, "temelji": 8.7, "podcenjenost": 6.8},
    "HUBS": {"name": "HubSpot", "sector": "CRM", "category": "Na opazovanju", "growth": 20.0, "fcf_margin": 18.0, "r40": 38.0, "peg": 1.10, "sentiment": 7.7, "makro": 7.0, "temelji": 8.5, "podcenjenost": 8.0},
    "DELL": {"name": "Dell", "sector": "AI Hardware", "category": "Na opazovanju", "growth": 14.0, "fcf_margin": 12.0, "r40": 26.0, "peg": 0.85, "sentiment": 8.0, "makro": 8.2, "temelji": 8.4, "podcenjenost": 8.5},
    "DDOG": {"name": "Datadog", "sector": "Cloud", "category": "Na opazovanju", "growth": 27.0, "fcf_margin": 26.0, "r40": 53.0, "peg": 1.60, "sentiment": 7.9, "makro": 8.0, "temelji": 9.1, "podcenjenost": 5.8},
    "TEAM": {"name": "Atlassian", "sector": "Dev Tools", "category": "Na opazovanju", "growth": 21.0, "fcf_margin": 28.0, "r40": 49.0, "peg": 1.80, "sentiment": 7.0, "makro": 7.5, "temelji": 8.8, "podcenjenost": 5.5},
    "NOW": {"name": "ServiceNow", "sector": "Enterprise", "category": "Polno ovrednoteno", "growth": 22.0, "fcf_margin": 34.0, "r40": 56.0, "peg": 1.20, "sentiment": 6.8, "makro": 8.5, "temelji": 9.8, "podcenjenost": 4.5},
    "PANW": {"name": "Palo Alto", "sector": "Security", "category": "Precenjeno", "growth": 13.0, "fcf_margin": 38.0, "r40": 51.0, "peg": 2.20, "sentiment": 6.5, "makro": 8.5, "temelji": 9.0, "podcenjenost": 3.8},
    "PLTR": {"name": "Palantir", "sector": "AI Platform", "category": "Tveganje", "growth": 30.0, "fcf_margin": 38.0, "r40": 68.0, "peg": 2.80, "sentiment": 5.2, "makro": 9.4, "temelji": 9.6, "podcenjenost": 2.1}
}

@st.cache_data(ttl=300)
def get_live_data():
    results = {}
    for t in TICKERS_CONFIG.keys():
        try:
            ticker = yf.Ticker(t)
            info = ticker.info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
            prev = info.get("regularMarketPreviousClose") or price
            chg = ((price - prev) / prev * 100) if prev else 0.0
            ps = info.get("priceToSalesTrailing12Months") or 0.0
            results[t] = {"price": round(price, 2), "chg": round(chg, 2), "ps": round(ps, 2)}
        except Exception:
            fb = 106.86 if t == "MNDY" else 325.0
            results[t] = {"price": fb, "chg": 0.0, "ps": 3.3}
    return results

data = get_live_data()

@st.cache_data(ttl=900)
def get_market_regime():
    try:
        spy = yf.Ticker("SPY").history(period="6mo", interval="1d", auto_adjust=False)
        if spy is None or len(spy) < 60:
            return {"regime": "NEZNANO", "spy_chg": 0.0, "penalty": 0.0}
        close = spy["Close"].astype(float)
        sma50 = float(close.rolling(50).mean().iloc[-1])
        last = float(close.iloc[-1])
        chg20 = float((last / float(close.iloc[-21]) - 1) * 100) if len(close) > 21 else 0.0
        if last > sma50 and chg20 > -3:
            return {"regime": "RISK-ON", "spy_chg": round(chg20, 2), "penalty": 0.0}
        elif last < sma50 and chg20 < -3:
            return {"regime": "RISK-OFF", "spy_chg": round(chg20, 2), "penalty": 1.5}
        else:
            return {"regime": "NEVTRALNO", "spy_chg": round(chg20, 2), "penalty": 0.5}
    except Exception:
        return {"regime": "NEZNANO", "spy_chg": 0.0, "penalty": 0.0}

market = get_market_regime()

def get_atr_stop_target(df, atr_mult_stop=1.5, atr_mult_target=2.5):
    try:
        h = df["High"].astype(float)
        l = df["Low"].astype(float)
        c = df["Close"].astype(float)
        tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
        atr = float(tr.rolling(14).mean().iloc[-1])
        last = float(c.iloc[-1])
        return {"atr": round(atr, 2), "stop": round(last - atr * atr_mult_stop, 2), "target": round(last + atr * atr_mult_target, 2)}
    except Exception:
        return {"atr": 0.0, "stop": 0.0, "target": 0.0}

def get_earnings_warning(ticker):
    try:
        cal = yf.Ticker(ticker).calendar
        if cal is None:
            return "ni podatka"
        if isinstance(cal, pd.DataFrame) and cal.empty:
            return "ni podatka"
        return "preveri earnings datum v Yahoo koledarju"
    except Exception:
        return "ni podatka"

def king_adjusted_score(base_score, ticker):
    adj = base_score - market["penalty"]
    if ticker == "MNDY":
        adj += 0.5
    return max(0.0, min(10.0, round(adj, 1)))

NY_TZ = pytz.timezone("America/New_York")
LJ_TZ = pytz.timezone("Europe/Ljubljana")

def get_intraday_df(ticker, period="1d", interval="5m"):
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=False)
        if df is None or df.empty:
            return None
        df = df.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
        return df
    except Exception:
        return None

def tactical_intraday_signal(df):
    if df is None or len(df) < 12:
        return None
    close = df["Close"].astype(float)
    volume = df["Volume"].replace(0, pd.NA).ffill().fillna(0).astype(float)
    last = float(close.iloc[-1])
    prev = float(close.iloc[-2])
    day_open = float(df["Open"].iloc[0])
    vol_sum = float(volume.cumsum().iloc[-1])
    if vol_sum:
        vwap = float(((close * volume).cumsum().iloc[-1] / vol_sum))
    else:
        vwap = last
    ema9 = float(close.ewm(span=9, adjust=False).mean().iloc[-1])
    ema20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
    if len(volume) >= 20:
        avg_vol20 = float(volume.tail(20).mean())
    else:
        avg_vol20 = float(volume.mean())
    last_vol = float(volume.iloc[-1]) if len(volume) else 0.0
    vol_ratio = (last_vol / avg_vol20) if avg_vol20 else 1.0
    rel_open = ((last / day_open) - 1) * 100 if day_open else 0.0
    rel_vwap = ((last / vwap) - 1) * 100 if vwap else 0.0
    momentum = ((last / prev) - 1) * 100 if prev else 0.0
    score = 5.0
    score += max(min(rel_vwap * 0.8, 2.0), -2.0)
    if ema9 > ema20:
        score += 1.0
    else:
        score -= 1.0
    score += max(min(momentum * 2.0, 1.0), -1.0)
    if vol_ratio >= 1.2:
        score += 1.0
    elif vol_ratio <= 0.8:
        score -= 0.5
    if rel_open < -2.5:
        score -= 0.75
    score = max(0.0, min(10.0, score))
