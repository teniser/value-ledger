import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, time
import pytz

# --- NASTAVITEV STRANI ---
st.set_page_config(
    page_title="The Value Ledger 2.0 · Terminal",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- STIL ---
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
    background: transparent !important;
    border: 1.2px solid #F59E0B; color: #FBBF24;
    font-family: 'Space Grotesk', sans-serif; font-weight: 600;
    font-size: 0.76rem; padding: 3px 12px; border-radius: 9999px;
    letter-spacing: 0.8px;
}
.badge-sector {
    font-family: 'Space Grotesk', sans-serif; font-size: 0.7rem; font-weight: 500;
    padding: 3px 8px; border-radius: 6px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    color: #94A3B8; letter-spacing: 0.6px; text-transform: uppercase;
}
.metrics-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(130px,1fr));
    gap: 12px; margin: 16px 0; padding: 14px 18px;
    background: rgba(0,0,0,0.25); border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.03);
}
.metric-label { color:#94A3B8; font-size:0.7rem; font-weight:500; letter-spacing:0.5px; margin-bottom:3px; text-transform:uppercase; font-family:'Space Grotesk',sans-serif; }
.metric-value { font-family:'JetBrains Mono',monospace; font-size:1.02rem; font-weight:500; color:#F8FAFC; }
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
.preclose-banner .title { font-family:'Space Grotesk',sans-serif; font-size:1.02rem; font-weight:700; color:#FEE2E2; }
.preclose-banner .sub { margin-top:5px; color:#FCA5A5; font-size:0.82rem; line-height:1.5; }
.preclose-banner .pill {
    display:inline-flex; align-items:center; gap:6px; margin-top:10px; padding:4px 10px;
    border-radius:9999px; border:1px solid rgba(248,113,113,0.35);
    background:rgba(0,0,0,0.18); color:#FEE2E2; font-size:0.74rem;
    font-family:'Space Grotesk',sans-serif;
}
</style>""", unsafe_allow_html=True)

# --- SIDEBAR: API ---
st.sidebar.markdown("### 🔑 Google AI Nastavitev")
api_key = st.sidebar.text_input("Vnesite brezplačni Gemini API ključ:", type="password")

# --- BAZA ---
TICKERS_CONFIG = {
    "MNDY": {"name":"monday.com","sector":"SaaS / Work OS","category":"💎 #1 Asimetrični Zmagovalec","growth":24.2,"fcf_margin":21.8,"r40":46.0,"net_cash":">1.66B $ (0 dolga)","peg":0.62,"sentiment":9.1,"makro":8.5,"temelji":9.2,"podcenjenost":9.5},
    "CRWD": {"name":"CrowdStrike","sector":"Kibernetska varnost","category":"🔥 #1 Taktični Obrat Dneva","growth":28.0,"fcf_margin":32.0,"r40":60.0,"net_cash":"Močna gotovina","peg":1.80,"sentiment":9.5,"makro":8.5,"temelji":9.5,"podcenjenost":6.5},
    "SNOW": {"name":"Snowflake","sector":"AI Podatkovna Hramba","category":"Na opazovanju","growth":28.0,"fcf_margin":27.0,"r40":55.0,"net_cash":">4.0B $ (0 dolga)","peg":1.70,"sentiment":8.2,"makro":8.3,"temelji":8.7,"podcenjenost":6.8},
    "HUBS": {"name":"HubSpot","sector":"CRM / Marketing","category":"Na opazovanju","growth":20.0,"fcf_margin":18.0,"r40":38.0,"net_cash":"Stabilna gotovina","peg":1.10,"sentiment":7.7,"makro":7.0,"temelji":8.5,"podcenjenost":8.0},
    "DELL": {"name":"Dell Technologies","sector":"AI Strojna Oprema","category":"Na opazovanju","growth":14.0,"fcf_margin":12.0,"r40":26.0,"net_cash":"Močan FCF","peg":0.85,"sentiment":8.0,"makro":8.2,"temelji":8.4,"podcenjenost":8.5},
    "DDOG": {"name":"Datadog","sector":"Nadzor Oblaka & AI","category":"Na opazovanju","growth":27.0,"fcf_margin":26.0,"r40":53.0,"net_cash":">2.8B $ gotovine","peg":1.60,"sentiment":7.9,"makro":8.0,"temelji":9.1,"podcenjenost":5.8},
    "TEAM": {"name":"Atlassian","sector":"Orodja za Razvijalce","category":"Na opazovanju","growth":21.0,"fcf_margin":28.0,"r40":49.0,"net_cash":"Pozitivna bilanca","peg":1.80,"sentiment":7.0,"makro":7.5,"temelji":8.8,"podcenjenost":5.5},
    "NOW": {"name":"ServiceNow","sector":"Enterprise Delovni Tokovi","category":"Polno ovrednoteno","growth":22.0,"fcf_margin":34.0,"r40":56.0,"net_cash":"Močna bilanca","peg":1.20,"sentiment":6.8,"makro":8.5,"temelji":9.8,"podcenjenost":4.5},
    "PANW": {"name":"Palo Alto Networks","sector":"Kibernetska varnost","category":"Precenjeno","growth":13.0,"fcf_margin":38.0,"r40":51.0,"net_cash":"Pozitivna bilanca","peg":2.20,"sentiment":6.5,"makro":8.5,"temelji":9.0,"podcenjenost":3.8},
    "PLTR": {"name":"Palantir","sector":"AI Platforma / AIP","category":"Tveganje prevrednotenja","growth":30.0,"fcf_margin":38.0,"r40":68.0,"net_cash":">4.0B $ (0 dolga)","peg":2.80,"sentiment":5.2,"makro":9.4,"temelji":9.6,"podcenjenost":2.1}
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
            results[t] = {"price": round(price,2), "chg": round(chg,2), "ps": round(ps,2)}
        except:
            results[t] = {"price": 106.86 if t=="MNDY" else 325.0, "chg": 0.0, "ps": 3.3}
    return results

data = get_live_data()

# --- KING UPGRADE 1+2+3: MARKET REGIME + ATR + EARNINGS + KING SCORE ---
@st.cache_data(ttl=900)
def get_market_regime():
    try:
        spy = yf.Ticker("SPY").history(period="6mo", interval="1d", auto_adjust=False)
        if spy is None or len(spy) < 60:
            return {"regime":"NEZNANO","spy_chg":0.0,"penalty":0.0}
        close = spy["Close"].astype(float)
        sma50 = float(close.rolling(50).mean().iloc[-1])
        last = float(close.iloc[-1])
        chg20 = float((last / float(close.iloc[-21]) - 1) * 100) if len(close) > 21 else 0.0
        if last > sma50 and chg20 > -3:
            return {"regime":"RISK-ON","spy_chg":round(chg20,2),"penalty":0.0}
        elif last < sma50 and chg20 < -3:
            return {"regime":"RISK-OFF","spy_chg":round(chg20,2),"penalty":1.5}
        else:
            return {"regime":"NEVTRALNO","spy_chg":round(chg20,2),"penalty":0.5}
    except:
        return {"regime":"NEZNANO","spy_chg":0.0,"penalty":0.0}

market = get_market_regime()

def get_atr_stop_target(df, atr_mult_stop=1.5, atr_mult_target=2.5):
    try:
        h = df["High"].astype(float); l = df["Low"].astype(float); c = df["Close"].astype(float)
        tr = pd.concat([h-l,(h-c.shift(1)).abs(),(l-c.shift(1)).abs()], axis=1).max(axis=1)
        atr = float(tr.rolling(14).mean().iloc[-1])
        last = float(c.iloc[-1])
        return {"atr":round(atr,2),"stop":round(last-atr*atr_mult_stop,2),"target":round(last+atr*atr_mult_target,2)}
    except:
        return {"atr":0.0,"stop":0.0,"target":0.0}

def get_earnings_warning(ticker):
    try:
        cal = yf.Ticker(ticker).calendar
        if cal is None or (isinstance(cal, pd.DataFrame) and cal.empty):
            return "ni podatka"
        return "preveri earnings datum v Yahoo koledarju"
    except:
        return "ni podatka"

def king_adjusted_score(base_score, ticker):
    adj = base_score - market["penalty"]
    if ticker == "MNDY":
        adj += 0.5
    return max(0.0, min(10.0, round(adj,1)))

# --- INTRADAY SIGNAL ---
NY_TZ = pytz.timezone("America/New_York")
LJ_TZ = pytz.timezone("Europe/Ljubljana")

def get_intraday_df(ticker, period="1d", interval="5m"):
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=False)
        if df is None or df.empty:
            return None
        df = df.dropna(subset=["Open","High","Low","Close","Volume"])
        return df
    except:
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
    prev_close = float(close.shift(1).iloc[-1]) if len(close)>1 else None
    gap = (((day_open/prev_close)-1)*100) if prev_close else 0.0
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
    if abs(gap)>4.0: score-=0.5
    score = max(0.0,min(10.0,score))
    return {"score":round(score,1),"last":round(last,2),"rel_open":round(rel_open,2),"rel_vwap":round(rel_vwap,2),"momentum":round(momentum,2),"vol_ratio":round(vol_ratio,2),"ema9":round(ema9,2),"ema20":round(ema20,2),"vwap":round(vwap,2),"gap":round(gap,2)}

def get_best_tactical_candidate(exclude_ticker=None):
    best=None
    for t in TICKERS_CONFIG.keys():
        if t==exclude_ticker: continue
        df=get_intraday_df(t)
        sig=tactical_intraday_signal(df)
        if sig is None: continue
        sig["score"]=king_adjusted_score(sig["score"],t)
        if best is None or sig["score"]>best["signal"]["score"]:
            best={"ticker":t,"signal":sig}
    return best

def get_evening_decision(held_ticker):
    held_df=get_intraday_df(held_ticker)
    held_sig=tactical_intraday_signal(held_df)
    if held_sig is None:
        return {"action":"NI PODATKOV","reason":"Za ta ticker danes ni dovolj intraday podatkov.","best":None,"held":None}
    held_sig["score"]=king_adjusted_score(held_sig["score"],held_ticker)
    if held_sig["score"]>=7.0: action="DRŽI ČEZ NOČ"
    elif held_sig["score"]>=6.0: action="DELNO ZMANJŠAJ / OPREZ"
    else: action="PRODAJ PRED ZAPRTJEM"
    best=get_best_tactical_candidate(exclude_ticker=held_ticker)
    rotation_text="Boljši taktični obrat trenutno ni jasen."
    if best and best["signal"]["score"]>=held_sig["score"]+0.5 and best["signal"]["score"]>=7.0:
        rotation_text=f"Boljši taktični obrat: {best['ticker']} ({best['signal']['score']}/10) je močnejši od {held_ticker} ({held_sig['score']}/10)."
    return {"action":action,"reason":rotation_text,"best":best,"held":held_sig}

def is_preclose_window(now_ny=None):
    now_ny=now_ny or datetime.now(NY_TZ)
    if now_ny.weekday()>=5: return False
    start=time(15,30); end=time(16,0)
    return start<=now_ny.time()<end

def build_preclose_banner(held_ticker, evening):
    held=evening["held"]; best=evening["best"]
    if held is None: return None
    action_color="#10B981" if evening["action"]=="DRŽI ČEZ NOČ" else ("#F59E0B" if evening["action"]=="DELNO ZMANJŠAJ / OPREZ" else "#EF4444")
    best_line="Ni močnejše rotacije."
    if best is not None:
        best_line=f"Najboljša alternativa zdaj: {best['ticker']} · {best['signal']['score']}/10"
    atr_info=get_atr_stop_target(get_intraday_df(held_ticker))
    earn=get_earnings_warning(held_ticker)
    return f"""
    <div class="preclose-banner">
        <div class="title">⚠️ Pred-zapiralni alert za {held_ticker} · Trg: {market['regime']}</div>
        <div class="sub">Trg se bliža zaprtju. Sistem je ob osvežitvi preveril pozicijo.</div>
        <div class="pill">ODLOČITEV: <span style="color:{action_color};font-weight:700;">{evening['action']}</span></div>
        <div class="sub" style="margin-top:10px;">
            <strong>King ocena:</strong> {held['score']}/10 ·
            <strong>Cena:</strong> ${held['last']} ·
            <strong>VWAP:</strong> {held['rel_vwap']}% ·
            <strong>Momentum:</strong> {held['momentum']}% ·
            <strong>Volumen:</strong> {held['vol_ratio']}x<br>
            <strong>ATR stop/target:</strong> {atr_info['stop']} / {atr_info['target']} (ATR {atr_info['atr']}) ·
            <strong>Earnings:</strong> {earn}<br>
            <strong>Rotacija:</strong> {best_line}
        </div>
    </div>
    """

# --- GLAVA ---
lj_time=datetime.now(LJ_TZ).strftime("%d.%m.%Y · %H:%M CET")
st.markdown(f"""<div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(255,255,255,0.06);padding-bottom:14px;margin-bottom:20px;">
<div><h1 style="margin:0;font-family:'Space Grotesk',sans-serif;font-size:1.8rem;font-weight:700;"><span style="color:#F59E0B;">THE VALUE LEDGER</span> <span style="color:#60A5FA;font-weight:400;">2.0</span></h1>
<p style="margin:3px 0 0 0;color:#94A3B8;font-size:0.82rem;">Sentiment Obrata × Makro Zaščita × Temelji × Podcenjenost · Kvantitativni Terminal</p></div>
<div style="text-align:right;"><div style="display:inline-flex;align-items:center;gap:6px;background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.25);padding:4px 10px;border-radius:9999px;"><span style="width:6px;height:6px;background:#10B981;border-radius:50%;"></span><span style="font-family:'Space Grotesk',sans-serif;font-size:0.74rem;color:#10B981;font-weight:600;">ŽIVI RADAR AKTIVEN</span></div>
<div style="font-size:0.7rem;color:#64748B;font-family:'JetBrains Mono',monospace;margin-top:3px;">{lj_time}</div></div></div>""", unsafe_allow_html=True)

# --- SIDEBAR: POZICIJA ---
st.sidebar.markdown("### 🌙 Večerni taktični pregled")
held_ticker=st.sidebar.selectbox("Katera delnica je trenutno v poziciji?", options=list(TICKERS_CONFIG.keys()), index=list(TICKERS_CONFIG.keys()).index("CRWD"))
st.sidebar.markdown(f"**Trg:** {market['regime']} (SPY 20d: {market['spy_chg']}%)")
if market["regime"]=="RISK-OFF":
    st.sidebar.warning("RISK-OFF: zmanjšaj velikost pozicije, A+ samo izjemoma.")
st.sidebar.caption("Banner se sam pokaže v zadnjih 30 minutah pred zaprtjem trga ob osvežitvi strani.")

# --- BANNER ---
evening=get_evening_decision(held_ticker)
if is_preclose_window():
    banner_html=build_preclose_banner(held_ticker, evening)
    if banner_html: st.markdown(banner_html, unsafe_allow_html=True)

# --- MNDY ---
mndy_live=data.get("MNDY",{"price":106.86,"chg":0.0,"ps":3.3})
m_col="#10B981" if mndy_live["chg"]>=0 else "#EF4444"
m_sign="+" if mndy_live["chg"]>=0 else ""
st.markdown(f"""<div class="mndy-hero-card">
<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;">
<div><div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
<span style="font-family:'Space Grotesk',sans-serif;font-size:1.35rem;font-weight:700;color:#FFFFFF;">MNDY</span>
<span class="badge-sector">SaaS / Work OS</span>
<span style="background:rgba(245,158,11,0.15);border:1px solid rgba(245,158,11,0.4);color:#FBBF24;font-family:'Space Grotesk',sans-serif;font-size:0.7rem;font-weight:600;padding:2px 8px;border-radius:6px;">💎 #1 ASIMETRIČNA GLAVNA NALOŽBA</span></div>
<div style="color:#94A3B8;font-size:0.86rem;">monday.com Ltd. · Glavna Trdnjava Portfelja (+200 % Potencial do 320 $+)</div></div>
<div style="text-align:right;"><div style="font-size:1.7rem;font-weight:600;font-family:'JetBrains Mono',monospace;color:#FFFFFF;">${mndy_live['price']} <span style="font-size:0.95rem;color:{m_col};">{m_sign}{mndy_live['chg']}%</span></div>
<div style="color:#F59E0B;font-weight:600;font-family:'Space Grotesk',sans-serif;font-size:0.82rem;">Ocena Asimetrije: 9.4 / 10</div></div></div>
<div class="metrics-grid">
<div><div class="metric-label">P/S</div><div class="metric-value" style="color:#60A5FA;">{mndy_live['ps']}x</div></div>
<div><div class="metric-label">PEG</div><div class="metric-value" style="color:#10B981;">0.62</div></div>
<div><div class="metric-label">Rast</div><div class="metric-value" style="color:#10B981;">+24.2% YoY</div></div>
<div><div class="metric-label">FCF</div><div class="metric-value" style="color:#10B981;">21.8%</div></div>
<div><div class="metric-label">Rule of 40</div><div class="metric-value" style="color:#10B981;">46%</div></div>
<div><div class="metric-label">Gotovina</div><div class="metric-value" style="color:#FBBF24;">>1.66B $</div></div>
</div></div>""", unsafe_allow_html=True)

# --- CRWD ---
crwd_live=data.get("CRWD",{"price":325.0,"chg":0.0,"ps":17.0})
c_col="#10B981" if crwd_live["chg"]>=0 else "#EF4444"
c_sign="+" if crwd_live["chg"]>=0 else ""
st.markdown(f"""<div class="ledger-card">
<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;">
<div><div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
<span style="font-family:'Space Grotesk',sans-serif;font-size:1.25rem;font-weight:700;color:#FFFFFF;">CRWD</span>
<span class="badge-sector">Kibernetska varnost</span><div class="aplus-badge">🌟 A+ SETUP</div></div>
<div style="color:#94A3B8;font-size:0.84rem;">CrowdStrike · Edini potrjeni taktični obrat dneva</div></div>
<div style="text-align:right;"><div style="font-size:1.55rem;font-weight:600;font-family:'JetBrains Mono',monospace;color:#FFFFFF;">${crwd_live['price']} <span style="font-size:0.9rem;color:{c_col};">{c_sign}{crwd_live['chg']}%</span></div>
<div style="color:#10B981;font-weight:600;font-family:'Space Grotesk',sans-serif;font-size:0.8rem;">Ocena Obrata: 9.5 / 10</div></div></div>
<div class="metrics-grid">
<div><div class="metric-label">P/S</div><div class="metric-value">{crwd_live['ps']}x</div></div>
<div><div class="metric-label">PEG</div><div class="metric-value">1.80</div></div>
<div><div class="metric-label">Rast</div><div class="metric-value" style="color:#10B981;">+28% YoY</div></div>
<div><div class="metric-label">Rule of 40</div><div class="metric-value" style="color:#10B981;">60%</div></div>
<div><div class="metric-label">Zadržanje</div><div class="metric-value" style="color:#10B981;">>97%</div></div>
<div><div class="metric-label">Premarket</div><div class="metric-value" style="color:#10B981;">+0.4% → +8.2%</div></div>
</div></div>""", unsafe
