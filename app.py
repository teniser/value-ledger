import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, time
import pytz

st.set_page_config(page_title="The Value Ledger 2.0 Terminal", page_icon="💎", layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@300;400;500;600&display=swap');
html, body, [class*="css"], .stApp { background-color: #06070B !important; font-family: 'Plus Jakarta Sans', sans-serif !important; color: #E2E8F0 !important; }
section[data-testid="stSidebar"] { background-color: #0A0D14 !important; }
.ledger-card { background: rgba(13,17,28,0.7); border: 1px solid rgba(255,255,255,0.06); border-radius: 16px; padding: 22px 26px; margin-bottom: 20px; }
.mndy-hero-card { background: linear-gradient(145deg, rgba(20,17,10,0.8) 0%, rgba(10,9,6,0.9) 100%); border: 1.5px solid rgba(245,158,11,0.6); border-radius: 18px; padding: 24px 26px; margin-bottom: 22px; }
.aplus-badge { display: inline-flex; border: 1.2px solid #F59E0B; color: #FBBF24; font-size: 0.76rem; padding: 3px 12px; border-radius: 9999px; }
.badge-sector { font-size: 0.7rem; padding: 3px 8px; border-radius: 6px; background: rgba(255,255,255,0.04); color: #94A3B8; text-transform: uppercase; }
div.stButton > button { background: linear-gradient(135deg,#F59E0B 0%,#D97706 100%) !important; color:#0A0D14 !important; font-weight:600 !important; border:none !important; border-radius:10px !important; padding:12px 24px !important; }
</style>""", unsafe_allow_html=True)

st.sidebar.markdown("### Google AI Nastavitev")
api_key = st.sidebar.text_input("Vnesite brezplacni Gemini API kljuc:", type="password")

# Baza za hitri vecerni pregled
TICKERS_CONFIG = {
    "MNDY": {"name": "monday.com", "sector": "SaaS / Work OS", "category": "No1 Asimetricni Zmagovalec"},
    "CRWD": {"name": "CrowdStrike", "sector": "Security", "category": "No1 Takticni Obrat"},
    "SNOW": {"name": "Snowflake", "sector": "AI Podatki", "category": "Na opazovanju"},
    "HUBS": {"name": "HubSpot", "sector": "CRM", "category": "Na opazovanju"},
    "DELL": {"name": "Dell", "sector": "AI HW", "category": "Na opazovanju"},
    "DDOG": {"name": "Datadog", "sector": "Cloud", "category": "Na opazovanju"},
    "TEAM": {"name": "Atlassian", "sector": "Dev", "category": "Na opazovanju"},
    "NOW": {"name": "ServiceNow", "sector": "Enterprise", "category": "Polno ovrednoteno"},
    "PANW": {"name": "Palo Alto", "sector": "Security", "category": "Precenjeno"},
    "PLTR": {"name": "Palantir", "sector": "AI Platform", "category": "Tveganje"}
}

# Razsirjeno na 150 top liquid tech/growth/SaaS/Semis tickerjev
AI_UNIVERSE = [
    # Core SaaS & Cloud Software
    "MNDY","CRWD","SNOW","HUBS","DDOG","TEAM","NOW","PANW","PLTR","CRM","ADBE","SHOP","NET","ZS","OKTA","MDB","ESTC","PATH","APP",
    "WDAY","CFLT","DOCN","GTLB","TOST","BILL","ASAN","IOT","TEM","FSLY","DT","BSY","PCOR","NCNO","S","ZM","DOCU","TWLO","PD","DBX","SMAR","FIVR","UPWK","SPT","DOMO","APPN","PEGA","FROG","BAND","RNG",
    # Big Tech & AI
    "NVDA","AAPL","MSFT","META","AMZN","GOOGL","NFLX","TSLA",
    # Semis & Hardware
    "AVGO","AMD","TSM","MU","QCOM","ARM","SMCI","ANET","MRVL","AI","SNPS","CDNS","ANSS","SYM","ALAB","LITE","COHR","VRT","NTNX","PSTG","STX","WDC","TXN","ADI","NXPI","MCHP","ON","INTC","ASML","AMAT","LRCX","KLAC","DELL","CSCO","HPQ","HPE","JNPR","FFIV","GLW","TER",
    # Fintech & Crypto
    "COIN","HOOD","SQ","PYPL","SOFI","AFRM","MELI","SE","NU","MSTR","MARA","RIOT","V","MA","GLBE",
    # Cyber & Infrastructure
    "CHKP","CYBR","TENB","VRNS","QLYS","FTNT","AKAM","VRSN","IT","GDDY",
    # Consumer Tech, Gig & Real Estate
    "UBER","ABNB","DASH","SPOT","RBLX","TTD","ROKU","PINS","SNAP","Z","CVNA","UPST","W","MTCH","BMBL",
    # High Growth / MedTech / Clean Energy
    "ISRG","VEEV","TDOC","ENPH","SEDG","FSLR","RIVN","LCID","DKNG","U","EXAS","ILMN","ALGN","DXCM","PODD","ALTR","TDC","TYL","PTC","ADSK","TRMB","ZBRA","KEYS"
]

@st.cache_data(ttl=300)
def get_live_data():
    results = {}
    for t in TICKERS_CONFIG.keys():
        try:
            info = yf.Ticker(t).info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
            prev = info.get("regularMarketPreviousClose") or price
            chg = ((price - prev) / prev * 100) if prev else 0.0
            ps = info.get("priceToSalesTrailing12Months") or 0.0
            results[t] = {"price": round(float(price),2), "chg": round(float(chg),2), "ps": round(float(ps),2)}
        except Exception:
            results[t] = {"price": 0.0, "chg": 0.0, "ps": 0.0}
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
            return {"regime": "RISK-ON", "spy_chg": round(chg20,2), "penalty": 0.0}
        elif last < sma50 and chg20 < -3:
            return {"regime": "RISK-OFF", "spy_chg": round(chg20,2), "penalty": 1.5}
        else:
            return {"regime": "NEVTRALNO", "spy_chg": round(chg20,2), "penalty": 0.5}
    except Exception:
        return {"regime": "NEZNANO", "spy_chg": 0.0, "penalty": 0.0}

market = get_market_regime()

@st.cache_data(ttl=900)
def get_sector_sentiment():
    # IGV = SaaS/Software, SMH = Semiconductors, QQQ = Nasdaq 100
    etfs = {"SaaS (IGV)": "IGV", "Semis (SMH)": "SMH", "Tech (QQQ)": "QQQ"}
    res = {}
    for name, ticker in etfs.items():
        try:
            df = yf.Ticker(ticker).history(period="6mo", interval="1d", auto_adjust=False)
            if df is not None and len(df) > 50:
                c = df["Close"].astype(float)
                last = float(c.iloc[-1])
                sma50 = float(c.rolling(50).mean().iloc[-1])
                chg20 = (last / float(c.iloc[-21]) - 1) * 100
                trend = "BULL (nad SMA50)" if last > sma50 else "BEAR (pod SMA50)"
                res[name] = f"{trend}, 1m zagon: {chg20:.1f}%"
            else:
                res[name] = "NI PODATKOV"
        except Exception:
            res[name] = "NAPAKA"
    return res

sector_sentiment = get_sector_sentiment()

def king_adjusted_score(base_score, ticker):
    adj = base_score - market["penalty"]
    if ticker == "MNDY":
        adj += 0.5
    return max(0.0, min(10.0, round(adj,1)))

def log_king_score(kind, ticker, score, extra=""):
    try:
        with open("king_log.csv", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()},{kind},{ticker},{score},{extra}\n")
    except Exception:
        pass

def parse_wallstreet(info, price):
    try:
        rec = info.get("recommendationMean")
        num = info.get("numberOfAnalystOpinions") or 0
        target = info.get("targetMeanPrice") or info.get("targetMedianPrice") or info.get("targetMean") or 0.0
        upside = 0.0
        if target and price:
            upside = (float(target) / float(price) - 1) * 100
        s = 5.0
        if rec is not None:
            rec = float(rec)
            if rec <= 1.5: s += 2.0
            elif rec <= 2.0: s += 1.5
            elif rec <= 2.5: s += 0.5
            elif rec >= 4.0: s -= 1.5
            elif rec >= 3.5: s -= 1.0
        else:
            rec = 0.0
        if upside > 30: s += 2.0
        elif upside > 15: s += 1.0
        elif upside > 5: s += 0.5
        elif upside < -10: s -= 1.0
        if num and num < 5: s -= 0.5
        s = max(0.0, min(10.0, s))
        return {"ws_score": round(s,1), "rec": round(float(rec),2) if rec else 0.0, "upside": round(float(upside),1), "num": int(num) if num else 0}
    except Exception:
        return {"ws_score": 5.0, "rec": 0.0, "upside": 0.0, "num": 0}

def get_history_edge(ticker, price_f, fcf, mcap):
    try:
        if not price_f:
            return {"bonus": 0.0, "vs_med": 0.0, "fcf_yield": 0.0}
        hist = yf.Ticker(ticker).history(period="3y", interval="1wk", auto_adjust=False)
        vs_med = 0.0
        bonus = 0.0
        if hist is not None and len(hist) > 50:
            closes = hist["Close"].astype(float).dropna()
            med = float(closes.median())
            if med > 0:
                vs_med = (float(price_f) / med - 1) * 100
                if vs_med < -30: bonus += 1.5
                elif vs_med < -15: bonus += 1.0
                elif vs_med < 0: bonus += 0.5
                elif vs_med > 80: bonus -= 1.0
        fcf_y = 0.0
        if fcf and mcap and mcap > 0:
            fcf_y = float(fcf) / float(mcap) * 100
            # KING GUARD: nemogoc yield = yfinance napaka, brez bonusa
            if fcf_y > 15.0 or fcf_y < -10.0:
                fcf_y = max(-10.0, min(fcf_y, 15.0))
            else:
                if fcf_y > 5: bonus += 1.0
                elif fcf_y > 3: bonus += 0.5
                elif fcf_y < 0: bonus -= 0.5
        return {"bonus": round(bonus,2), "vs_med": round(vs_med,1), "fcf_yield": round(fcf_y,2)}
    except Exception:
        return {"bonus": 0.0, "vs_med": 0.0, "fcf_yield": 0.0}

NY_TZ = pytz.timezone("America/New_York")
LJ_TZ = pytz.timezone("Europe/Ljubljana")

def get_intraday_df(ticker, period="1d", interval="5m"):
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=False)
        if df is None or df.empty:
            return None
        return df.dropna(subset=["Open","High","Low","Close","Volume"])
    except Exception:
        return None

def tactical_vwap(df):
    try:
        typ = (df["High"].astype(float) + df["Low"].astype(float) + df["Close"].astype(float)) / 3.0
        vol = df["Volume"].astype(float)
        vsum = float(vol.sum())
        if vsum <= 0:
            return float(df["Close"].iloc[-1])
        return float((typ * vol).cumsum().iloc[-1] / vsum)
    except Exception:
        return float(df["Close"].iloc[-1])

def tactical_intraday_signal(df):
    if df is None or len(df) < 12:
        return None
    close = df["Close"].astype(float)
    volume = df["Volume"].replace(0, pd.NA).ffill().fillna(0).astype(float)
    last = float(close.iloc[-1])
    prev = float(close.iloc[-2])
    day_open = float(df["Open"].iloc[0])
    vwap = tactical_vwap(df)
    ema9 = float(close.ewm(span=9, adjust=False).mean().iloc[-1])
    ema20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
    avg_vol20 = float(volume.tail(20).mean()) if len(volume)>=20 else float(volume.mean())
    last_vol = float(volume.iloc[-1]) if len(volume) else 0.0
    vol_ratio = (last_vol/avg_vol20) if avg_vol20 else 1.0
    rel_open = ((last/day_open)-1)*100 if day_open else 0.0
    rel_vwap = ((last/vwap)-1)*100 if vwap else 0.0
    momentum = ((last/prev)-1)*100 if prev else 0.0
    score = 5.0
    score += max(min(rel_vwap*0.8,2.0),-2.0)
    score += 1.0 if ema9>ema20 else -1.0
    score += max(min(momentum*2.0,1.0),-1.0)
    if vol_ratio>=1.2: score+=1.0
    elif vol_ratio<=0.8: score-=0.5
    if rel_open<-2.5: score-=0.75
    score = max(0.0,min(10.0,score))
    return {"score":round(score,1),"last":round(last,2),"vwap":round(vwap,2),"rel_open":round(rel_open,2),"rel_vwap":round(rel_vwap,2),"momentum":round(momentum,2),"vol_ratio":round(vol_ratio,2)}

def is_green_reclaim(df):
    try:
        last_o = float(df["Open"].iloc[-1])
        last_c = float(df["Close"].iloc[-1])
        vwap = tactical_vwap(df)
        return (last_c > last_o) and ((last_c / vwap - 1) * 100 >= -0.3)
    except Exception:
        return False

def get_rsi_5m(df, period=14):
    try:
        c = df["Close"].astype(float)
        d = c.diff()
        up = d.clip(lower=0).rolling(period).mean()
        down = (-d.clip(upper=0)).rolling(period).mean()
        rs = up / down.replace(0, float("nan"))
        rsi = 100 - (100 / (1 + rs))
        v = float(rsi.iloc[-1])
        return v if v == v else 50.0
    except Exception:
        return 50.0

def has_earnings_soon(ticker, days=5):
    try:
        ed = yf.Ticker(ticker).get_earnings_dates(limit=2)
        if ed is None or (isinstance(ed, pd.DataFrame) and ed.empty):
            return False
        earn_date = pd.to_datetime(ed.index[0]).tz_localize(None)
        delta = (earn_date - datetime.now()).days
        return 0 <= delta <= days
    except Exception:
        return False

def get_atr_levels(ticker, price, mult_stop=1.5, mult_t1=1.5, mult_t2=2.5):
    try:
        d = yf.Ticker(ticker).history(period="3mo", interval="1d", auto_adjust=False)
        if d is None or len(d) < 20:
            return None
        h, l, c = d["High"].astype(float), d["Low"].astype(float), d["Close
