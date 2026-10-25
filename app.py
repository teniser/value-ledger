import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
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
.metric-label { color:#94A3B8; font-size:0.7rem; text-transform:uppercase; }
.metric-value { font-size:1.02rem; color:#F8FAFC; }
div.stButton > button { background: linear-gradient(135deg,#F59E0B 0%,#D97706 100%) !important; color:#0A0D14 !important; font-weight:600 !important; border:none !important; border-radius:10px !important; padding:12px 24px !important; }
</style>""", unsafe_allow_html=True)

st.sidebar.markdown("### Google AI Nastavitev")
api_key = st.sidebar.text_input("Vnesite brezplacni Gemini API kljuc:", type="password")

TICKERS_CONFIG = {
    "MNDY": {"name": "monday.com", "sector": "SaaS / Work OS", "category": "No1 Asimetricni Zmagovalec", "growth": 24.2, "fcf_margin": 21.8, "r40": 46.0, "peg": 0.62, "sentiment": 9.1, "makro": 8.5, "temelji": 9.2, "podcenjenost": 9.5},
    "CRWD": {"name": "CrowdStrike", "sector": "Security", "category": "No1 Takticni Obrat", "growth": 28.0, "fcf_margin": 32.0, "r40": 60.0, "peg": 1.80, "sentiment": 9.5, "makro": 8.5, "temelji": 9.5, "podcenjenost": 6.5},
    "SNOW": {"name": "Snowflake", "sector": "AI Podatki", "category": "Na opazovanju", "growth": 28.0, "fcf_margin": 27.0, "r40": 55.0, "peg": 1.70, "sentiment": 8.2, "makro": 8.3, "temelji": 8.7, "podcenjenost": 6.8},
    "HUBS": {"name": "HubSpot", "sector": "CRM", "category": "Na opazovanju", "growth": 20.0, "fcf_margin": 18.0, "r40": 38.0, "peg": 1.10, "sentiment": 7.7, "makro": 7.0, "temelji": 8.5, "podcenjenost": 8.0},
    "DELL": {"name": "Dell", "sector": "AI HW", "category": "Na opazovanju", "growth": 14.0, "fcf_margin": 12.0, "r40": 26.0, "peg": 0.85, "sentiment": 8.0, "makro": 8.2, "temelji": 8.4, "podcenjenost": 8.5},
    "DDOG": {"name": "Datadog", "sector": "Cloud", "category": "Na opazovanju", "growth": 27.0, "fcf_margin": 26.0, "r40": 53.0, "peg": 1.60, "sentiment": 7.9, "makro": 8.0, "temelji": 9.1, "podcenjenost": 5.8},
    "TEAM": {"name": "Atlassian", "sector": "Dev", "category": "Na opazovanju", "growth": 21.0, "fcf_margin": 28.0, "r40": 49.0, "peg": 1.80, "sentiment": 7.0, "makro": 7.5, "temelji": 8.8, "podcenjenost": 5.5},
    "NOW": {"name": "ServiceNow", "sector": "Enterprise", "category": "Polno ovrednoteno", "growth": 22.0, "fcf_margin": 34.0, "r40": 56.0, "peg": 1.20, "sentiment": 6.8, "makro": 8.5, "temelji": 9.8, "podcenjenost": 4.5},
    "PANW": {"name": "Palo Alto", "sector": "Security", "category": "Precenjeno", "growth": 13.0, "fcf_margin": 38.0, "r40": 51.0, "peg": 2.20, "sentiment": 6.5, "makro": 8.5, "temelji": 9.0, "podcenjenost": 3.8},
    "PLTR": {"name": "Palantir", "sector": "AI Platform", "category": "Tveganje", "growth": 30.0, "fcf_margin": 38.0, "r40": 68.0, "peg": 2.80, "sentiment": 5.2, "makro": 9.4, "temelji": 9.6, "podcenjenost": 2.1}
}

AI_UNIVERSE = ["MNDY","CRWD","SNOW","HUBS","DELL","DDOG","TEAM","NOW","PANW","PLTR","NVDA","AAPL","MSFT","META","AMZN","GOOGL","AVGO","AMD","TSM","NFLX","ORCL","CRM","ADBE","MU","QCOM","ARM","SHOP","NET","ZS","OKTA","MDB","ESTC","COIN","HOOD","SMCI","ANET","MRVL","FTNT","AI","PATH","SNPS","CDNS","APP","ANSS"]

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
            results[t] = {"price": round(price,2), "chg": round(chg,2), "ps": round(ps,2)}
        except Exception:
            results[t] = {"price": 106.86 if t=="MNDY" else 325.0, "chg": 0.0, "ps": 3.3}
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

def king_adjusted_score(base_score, ticker):
    adj = base_score - market["penalty"]
    if ticker == "MNDY":
        adj += 0.5
    return max(0.0, min(10.0, round(adj,1)))

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

def tactical_intraday_signal(df):
    if df is None or len(df) < 12:
        return None
    close = df["Close"].astype(float)
    volume = df["Volume"].replace(0, pd.NA).ffill().fillna(0).astype(float)
    last = float(close.iloc[-1])
    prev = float(close.iloc[-2])
    day_open = float(df["Open"].iloc[0])
    vol_sum = float(volume.cumsum().iloc[-1])
    vwap = float(((close*volume).cumsum().iloc[-1]/vol_sum)) if vol_sum else last
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
    return {"score":round(score,1),"last":round(last,2),"rel_open":round(rel_open,2),"rel_vwap":round(rel_vwap,2),"momentum":round(momentum,2),"vol_ratio":round(vol_ratio,2)}

def get_asymmetry_score(ticker):
    try:
        info = yf.Ticker(ticker).info
        ps = info.get("priceToSalesTrailing12Months") or 20.0
        # varovalka proti yfinance napaki kot TSM 0.44
        if float(ps) < 1.0:
            ps = 20.0
        peg = info.get("pegRatio") or 2.0
        gr = info.get("revenueGrowth") or 0.15
        if isinstance(gr, float) and gr > 1.0:
            gr = gr / 100.0
        price = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
        price_f = float(price) if price else 0.0
        cash = info.get("totalCash") or 0.0
        debt = info.get("totalDebt") or 0.0
        fcf = info.get("freeCashflow") or 0.0
        rev = info.get("totalRevenue") or 0.0
        mcap = info.get("marketCap") or 0.0
        fcf_m = (fcf / rev * 100) if fcf and rev else 0.0
        net_cash = cash - debt
        s = 5.0
        if ps < 4: s += 3.0
        elif ps < 7: s += 2.0
        elif ps < 12: s += 1.0
        elif ps > 25: s -= 1.5
        if peg < 0.9: s += 2.5
        elif peg < 1.3: s += 1.5
        elif peg > 3.0: s -= 1.5
        if gr > 0.25: s += 1.5
        elif gr > 0.15: s += 0.75
        if debt == 0 or net_cash > 1000000000: s += 2.0
        elif net_cash > 0: s += 1.0
        else: s -= 1.0
        if fcf_m > 20: s += 1.0
        elif fcf_m < 0: s -= 1.0
        ws = parse_wallstreet(info, price_f)
        s = s * 0.7 + ws["ws_score"] * 0.3
        he = get_history_edge(ticker, price_f, fcf, mcap)
        s += he["bonus"]
        s = max(0.0, min(10.0, s))
        return {"score": king_adjusted_score(round(s,1), ticker), "ps": round(float(ps),2), "peg": round(float(peg),2), "growth": round(float(gr)*100,1), "price": round(price_f,2), "net_cash": net_cash, "debt": debt, "ws_score": ws["ws_score"], "ws_rec": ws["rec"], "ws_upside": ws["upside"], "ws_num": ws["num"], "vs_med": he["vs_med"], "fcf_yield": he["fcf_yield"]}
    except Exception:
        return None

def get_liquidity_ok(ticker):
    try:
        info = yf.Ticker(ticker).info
        mcap = info.get("marketCap") or 0
        avgv = info.get("averageVolume") or 0
        price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
        if mcap < 2000000000:
            return False
        if avgv and price and (float(avgv) * float(price) < 20000000):
            return False
        return True
    except Exception:
        return True

def get_rsi_5m(df, period=14):
    try:
        c = df["Close"].astype(float)
        d = c.diff()
        up = d.clip(lower=0).rolling(period).mean()
        down = (-d.clip(upper=0)).rolling(period).mean()
        rs = up / down.replace(0, float("nan"))
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])
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

@st.cache_data(ttl=1800)
def scan_best_long():
    best = None
    for t in AI_UNIVERSE:
        r = get_asymmetry_score(t)
        if r is None:
            continue
        if r["ps"] > 20 or r["peg"] > 2.8 or r["growth"] < 12:
            continue
        if r["debt"] > 0 and r["net_cash"] < 0:
            continue
        if not get_liquidity_ok(t):
            continue
        if r["score"] < 6.5:
            continue
        if best is None or r["score"] > best["signal"]["score"]:
            best = {"ticker": t, "signal": r}
    return best

@st.cache_data(ttl=600)
def scan_best_reversal():
    best = None
    for t in AI_UNIVERSE:
        df = get_intraday_df(t)
        sig = tactical_intraday_signal(df)
        if sig is None or df is None:
            continue
        sig["score"] = king_adjusted_score(sig["score"], t)
        if not (-8.0 <= sig.get("rel_open", 0) <= -1.0):
            continue
        if sig.get("rel_vwap", 0) < -2.0:
            continue
        if sig.get("vol_ratio", 0) < 1.3:
            continue
        if sig.get("momentum", 0) < 0:
            continue
        if get_rsi_5m(df) > 35:
            continue
        if has_earnings_soon(t, 5):
            continue
        if sig["score"] < 6.0:
            continue
        if best is None or sig["score"] > best["signal"]["score"]:
            best = {"ticker": t, "signal": sig}
    return best

@st.cache_data(ttl=1800)
def scan_top_long(n=5):
    out = []
    for t in AI_UNIVERSE:
        r = get_asymmetry_score(t)
        if r is None:
            continue
        if r["ps"] > 20 or r["peg"] > 2.8 or r["growth"] < 12:
            continue
        if r["debt"] > 0 and r["net_cash"] < 0:
            continue
        if not get_liquidity_ok(t):
            continue
        out.append((t, r))
    out.sort(key=lambda x: x[1]["score"], reverse=True)
    return [{"ticker": t, "signal": r} for t, r in out[:n]]

@st.cache_data(ttl=600)
def scan_top_reversal(n=5):
    out = []
    for t in AI_UNIVERSE:
        df = get_intraday_df(t)
        sig = tactical_intraday_signal(df)
        if sig is None or df is None:
            continue
        sig["score"] = king_adjusted_score(sig["score"], t)
        rsi = get_rsi_5m(df)
        earn = has_earnings_soon(t, 5)
        sig["rsi"] = round(rsi,1)
        sig["earn"] = earn
        if not (-8.0 <= sig.get("rel_open", 0) <= -1.0):
            continue
        if sig.get("vol_ratio", 0) < 1.3:
            continue
        if earn:
            continue
        out.append((t, sig))
    out.sort(key=lambda x: x[1]["score"], reverse=True)
    return [{"ticker": t, "signal": s} for t, s in out[:n]]

def build_ai_context():
    topL = scan_top_long(5)
    topR = scan_top_reversal(5)
    lines = []
    lines.append("MAKRO: " + str(market["regime"]) + " SPY20d " + str(market["spy_chg"]) + "%")
    lines.append("TOP5 LONG:")
    for x in topL:
        s = x["signal"]
        lines.append("- " + x["ticker"] + " sc " + str(s["score"]) + " P/S " + str(s["ps"]) + " PEG " + str(s["peg"]) + " rast " + str(s["growth"]) + "% vs3y " + str(s.get("vs_med")) + "% FCFy " + str(s.get("fcf_yield")) + "% WS " + str(s["ws_score"]))
    lines.append("TOP5 DIP:")
    for x in topR:
        s = x["signal"]
        lines.append("- " + x["ticker"] + " sc " + str(s["score"]) + " open " + str(s.get("rel_open")) + "% vwap " + str(s.get("rel_vwap")) + "% vol " + str(s.get("vol_ratio")) + "x RSI " + str(s.get("rsi")))
    return "\n".join(lines)

def get_evening_decision(held_ticker):
    held_sig = tactical_intraday_signal(get_intraday_df(held_ticker))
    if held_sig is None:
        return {"action": "NI PODATKOV", "best": None, "held": None}
    held_sig["score"] = king_adjusted_score(held_sig["score"], held_ticker)
    if held_sig["score"] >= 7.0:
        action = "DRZI CEZ NOC"
    elif held_sig["score"] >= 6.0:
        action = "DELNO ZMANJSAJ / OPREZ"
    else:
        action = "PRODAJ PRED ZAPRTJEM"
    return {"action": action, "best": None, "held": held_sig}

def is_preclose_window(now_ny=None):
    if now_ny is None:
        now_ny = datetime.now(NY_TZ)
    if now_ny.weekday() >= 5:
        return False
    return time(15,30) <= now_ny.time() < time(16,0)

lj_time = datetime.now(LJ_TZ).strftime("%d.%m.%Y %H:%M CET")
st.markdown('<div style="border-bottom:1px solid rgba(255,255,255,0.06);padding-bottom:14px;margin-bottom:20px;"><h1 style="margin:0;font-size:1.8rem;"><span style="color:#F59E0B;">THE VALUE LEDGER</span> <span style="color:#60A5FA;">2.0</span></h1><p style="color:#94A3B8;font-size:0.82rem;">Kvantitativni Terminal ' + lj_time + '</p></div>', unsafe_allow_html=True)

st.sidebar.markdown("### Vecerni takticni pregled")
tick_list = list(TICKERS_CONFIG.keys())
held_ticker = st.sidebar.selectbox("Katera delnica je v poziciji?", options=tick_list, index=tick_list.index("CRWD"))
st.sidebar.markdown("**Trg:** " + str(market["regime"]) + " (SPY 20d: " + str(market["spy_chg"]) + "%)")
if market["regime"] == "RISK-OFF":
    st.sidebar.warning("RISK-OFF: zmanjsaj velikost pozicije, A+ samo izjemoma.")

bestL = scan_best_long()
bestR = scan_best_reversal()
if bestL is not None:
    l_txt = str(bestL["ticker"]) + " " + str(bestL["signal"]["score"]) + "/10 P/S " + str(bestL["signal"]["ps"]) + " PEG " + str(bestL["signal"]["peg"])
else:
    l_txt = "NI STROGEGA KANDIDATA"
if bestR is not None:
    r_txt = str(bestR["ticker"]) + " " + str(bestR["signal"]["score"]) + "/10"
else:
    r_txt = "NI STROGEGA KANDIDATA"

evening = get_evening_decision(held_ticker)
if is_preclose_window() and evening["held"] is not None:
    act = evening["action"]
    col = "#10B981" if act == "DRZI CEZ NOC" else ("#F59E0B" if act == "DELNO ZMANJSAJ / OPREZ" else "#EF4444")
    st.markdown('<div class="ledger-card"><div style="font-weight:700;">Vecerni pregled ' + str(held_ticker) + ': <span style="color:' + col + ';">' + act + '</span></div></div>', unsafe_allow_html=True)

m = data.get("MNDY", {"price": 106.86, "chg": 0.0, "ps": 3.3})
st.markdown('<div class="mndy-hero-card"><span style="font-size:1.35rem;font-weight:700;color:#FFFFFF;">MNDY</span> <span class="badge-sector">SaaS</span><div style="font-size:1.7rem;color:#fff;">$' + str(m["price"]) + '</div><div style="color:#F59E0B;">Ocena Asimetrije: 9.4 / 10</div></div>', unsafe_allow_html=True)

c = data.get("CRWD", {"price": 325.0, "chg": 0.0, "ps": 17.0})
st.markdown('<div class="ledger-card"><span style="font-size:1.25rem;font-weight:700;color:#FFFFFF;">CRWD</span> <span class="aplus-badge">A+ SETUP</span><div style="font-size:1.55rem;color:#fff;">$' + str(c["price"]) + '</div></div>', unsafe_allow_html=True)

col1, col2 = st.columns([1, 1.25])
with col1:
    st.markdown("<h3>Primerjava 4 stebrov</h3>", unsafe_allow_html=True)
    sel = st.multiselect("Izberite delnice:", options=tick_list, default=["MNDY", "CRWD", "NOW", "PLTR"])
    cats = ["Sentiment", "Makro", "Temelji", "Podcenjenost"]
    fig = go.Figure()
    cols = {"MNDY": "#F59E0B", "CRWD": "#10B981", "SNOW": "#60A5FA", "NOW": "#8B5CF6", "PLTR": "#EF4444"}
    for t in sel:
        cfg = TICKERS_CONFIG[t]
        vals = [cfg["sentiment"], cfg["makro"], cfg["temelji"], cfg["podcenjenost"]]
        vals.append(vals[0])
        fig.add_trace(go.Scatterpolar(r=vals, theta=cats+[cats[0]], name=t, line=dict(color=cols.get(t, "#fff"), width=2), fill="toself"))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])), paper_bgcolor="rgba(0,0,0,0)", height=300, margin=dict(l=20, r=20, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
with col2:
    st.markdown("<h3>Primerjalna tabela</h3>", unsafe_allow_html=True)
    rows = []
    for t, cfg in TICKERS_CONFIG.items():
        ld = data.get(t, {"price": 0.0, "ps": 0.0})
        sc = round((cfg["sentiment"]*1.2+cfg["makro"]+cfg["temelji"]*1.1+cfg["podcenjenost"]*1.4)/4.7,1)
        rows.append({"Ticker": t, "Cena": ld["price"], "P/S": ld["ps"], "Ocena": sc, "Status": cfg["category"]})
    st.dataframe(pd.DataFrame(rows).sort_values(by="Ocena", ascending=False), use_container_width=True, hide_index=True)

col_rot, col_exit = st.columns(2)
with col_rot:
    st.markdown('<div class="ledger-card"><h4 style="color:#10B981;">Capital Rotation Radar</h4><p style="font-size:0.82rem;color:#94A3B8;">Trg: ' + str(market["regime"]) + '</p><div style="font-size:0.82rem;color:#6EE7B7;">BEST LONG: ' + l_txt + '<br>BEST OBRAT: ' + r_txt + '</div></div>', unsafe_allow_html=True)
with col_exit:
    st.markdown('<div class="ledger-card"><h4 style="color:#F59E0B;">MNDY Stopnje</h4><div style="font-size:0.82rem;color:#CBD5E1;">1. Tarca 220-240: prodaj 20-25%.<br>2. Tarca 280-310: prodaj 50%.<br>3. Tarca nad 340: popolna prodaja.</div></div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown("<h3>Avtonomni AI Analitik</h3>", unsafe_allow_html=True)
if st.button("POZENI AVTONOMNI AI PREGLED TRGA"):
    if not api_key:
        st.error("Vnesite Gemini API kljuc.")
    else:
        with st.spinner("Povezovanje z Gemini AI..."):
            ctx = build_ai_context()
            prompt_text = "Ti si analitik Value Ledger 2.0.\n" + ctx + "\nCene10: " + str(data) + "\nIzberi 1 BEST LONG za asimetrijo + 1 BEST DIP tik pred obratom kot CRWD +0.2% -> +8.2% + 1 za izogib. Za vsakega 3 razlogi s stevilkami P/S PEG WS RSI VWAP volumen earnings. Odgovori v slovenscini z ocenami 1-10."
            clean_key = api_key.strip()
            payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
            success = False
            last_error = ""
            try:
                l_res = requests.get("https://generativelanguage.googleapis.com/v1beta/models?key=" + clean_key, timeout=15)
                if l_res.status_code == 200:
                    all_m = l_res.json().get("models", [])
                    models_to_try = [mm["name"].split("/")[-1] for mm in all_m if "generateContent" in mm.get("supportedGenerationMethods", [])]
                else:
                    models_to_try = []
                    last_error = "ListModels: " + str(l_res.status_code)
            except Exception as e:
                models_to_try = []
                last_error = str(e)
            if not models_to_try:
                models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash-latest"]
            st.caption("Najdeni modeli: " + ", ".join(models_to_try[:5]))
            for mname in models_to_try:
                try:
                    url = "https://generativelanguage.googleapis.com/v1beta/models/" + mname + ":generateContent?key=" + clean_key
                    res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=25)
                    if res.status_code == 200:
                        st.session_state["ai_report"] = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                        st.session_state["used_model"] = mname
                        success = True
                        break
                    else:
                        last_error = mname + ": " + str(res.status_code) + " " + res.text[:300]
                except Exception as e:
                    last_error = str(e)
                    continue
            if not success:
                st.error("Zadnja napaka: " + last_error)
if "ai_report" in st.session_state:
    rep = st.session_state["ai_report"].replace("\n", "<br>")
    st.markdown('<div class="ledger-card"><h3>Porocilo AI (' + st.session_state.get("used_model", "Gemini") + ')</h3><div>' + rep + '</div></div>', unsafe_allow_html=True)
