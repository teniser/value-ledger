import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime, time
import pytz

st.set_page_config(
    page_title="The Value Ledger 2.0 Terminal",
    page_icon="Diamond",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""<style>
html, body, .stApp { background-color: #06070B !important; color: #E2E8F0 !important; }
section[data-testid="stSidebar"] { background-color: #0A0D14 !important; }
.ledger-card {
    background: rgba(13,17,28,0.7);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 16px;
    padding: 22px 26px;
    margin-bottom: 20px;
}
.mndy-hero-card {
    background: linear-gradient(145deg, rgba(20,17,10,0.8) 0%, rgba(10,9,6,0.9) 100%);
    border: 1.5px solid rgba(245,158,11,0.6);
    border-radius: 18px;
    padding: 24px 26px;
    margin-bottom: 22px;
}
.aplus-badge {
    display: inline-flex; align-items: center;
    border: 1.2px solid #F59E0B; color: #FBBF24;
    font-size: 0.76rem; padding: 3px 12px; border-radius: 9999px;
}
.badge-sector {
    font-size: 0.7rem; padding: 3px 8px; border-radius: 6px;
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
.metric-label { color:#94A3B8; font-size:0.7rem; text-transform:uppercase; margin-bottom:3px; }
.metric-value { font-size:1.02rem; color:#F8FAFC; }
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
    return {"score": round(score, 1), "last": round(last, 2), "rel_open": round(rel_open, 2), "rel_vwap": round(rel_vwap, 2), "momentum": round(momentum, 2), "vol_ratio": round(vol_ratio, 2), "vwap": round(vwap, 2)}

def get_best_tactical_candidate(exclude_ticker=None):
    best = None
    for t in TICKERS_CONFIG.keys():
        if t == exclude_ticker:
            continue
        sig = tactical_intraday_signal(get_intraday_df(t))
        if sig is None:
            continue
        sig["score"] = king_adjusted_score(sig["score"], t)
        if best is None or sig["score"] > best["signal"]["score"]:
            best = {"ticker": t, "signal": sig}
    return best

def get_evening_decision(held_ticker):
    held_sig = tactical_intraday_signal(get_intraday_df(held_ticker))
    if held_sig is None:
        return {"action": "NI PODATKOV", "reason": "Ni intraday podatkov.", "best": None, "held": None}
    held_sig["score"] = king_adjusted_score(held_sig["score"], held_ticker)
    if held_sig["score"] >= 7.0:
        action = "DRZI CEZ NOC"
    elif held_sig["score"] >= 6.0:
        action = "DELNO ZMANJSAJ / OPREZ"
    else:
        action = "PRODAJ PRED ZAPRTJEM"
    best = get_best_tactical_candidate(exclude_ticker=held_ticker)
    return {"action": action, "reason": "Rotacija preverjena.", "best": best, "held": held_sig}

def is_preclose_window(now_ny=None):
    if now_ny is None:
        now_ny = datetime.now(NY_TZ)
    if now_ny.weekday() >= 5:
        return False
    start = time(15, 30)
    end = time(16, 0)
    return start <= now_ny.time() < end

def build_preclose_banner(held_ticker, evening):
    held = evening["held"]
    best = evening["best"]
    if held is None:
        return None
    act = evening["action"]
    if act == "DRZI CEZ NOC":
        act_color = "#10B981"
    elif act == "DELNO ZMANJSAJ / OPREZ":
        act_color = "#F59E0B"
    else:
        act_color = "#EF4444"
    if best is not None:
        bt = best["ticker"]
        bs = best["signal"]["score"]
        best_line = "Najboljsa alternativa zdaj: " + str(bt) + " " + str(bs) + "/10"
    else:
        best_line = "Ni mocnejse rotacije."
    atr_info = get_atr_stop_target(get_intraday_df(held_ticker))
    earn = get_earnings_warning(held_ticker)
    regime = market["regime"]
    h_score = held["score"]
    h_last = held["last"]
    h_vwap = held["rel_vwap"]
    h_mom = held["momentum"]
    h_vol = held["vol_ratio"]
    a_stop = atr_info["stop"]
    a_tgt = atr_info["target"]
    a_atr = atr_info["atr"]
    html = (
        '<div class="preclose-banner">'
        + '<div style="font-size:1.02rem;font-weight:700;color:#FEE2E2;">Pred-zapiralni alert za ' + str(held_ticker) + ' Trg: ' + str(regime) + '</div>'
        + '<div style="margin-top:5px;color:#FCA5A5;font-size:0.82rem;">Trg se bliza zaprtju. Sistem je ob osvezitvi preveril pozicijo.</div>'
        + '<div style="margin-top:10px;color:#FEE2E2;">ODLOCITEV: <span style="color:' + act_color + ';font-weight:700;">' + act + '</span></div>'
        + '<div style="margin-top:10px;color:#FCA5A5;font-size:0.82rem;">King ocena: ' + str(h_score) + '/10 Cena: ' + str(h_last) + ' VWAP: ' + str(h_vwap) + '% Momentum: ' + str(h_mom) + '% Volumen: ' + str(h_vol) + 'x<br>'
        + 'ATR stop/target: ' + str(a_stop) + ' / ' + str(a_tgt) + ' (ATR ' + str(a_atr) + ') Earnings: ' + str(earn) + '<br>'
        + 'Rotacija: ' + best_line + '</div></div>'
    )
    return html

lj_time = datetime.now(LJ_TZ).strftime("%d.%m.%Y %H:%M CET")
st.markdown(
    '<div style="border-bottom:1px solid rgba(255,255,255,0.06);padding-bottom:14px;margin-bottom:20px;">'
    + '<h1 style="margin:0;font-size:1.8rem;font-weight:700;"><span style="color:#F59E0B;">THE VALUE LEDGER</span> <span style="color:#60A5FA;">2.0</span></h1>'
    + '<p style="color:#94A3B8;font-size:0.82rem;">Kvantitativni Terminal ' + lj_time + '</p></div>',
    unsafe_allow_html=True
)

st.sidebar.markdown("### Vecerni takticni pregled")
tick_list = list(TICKERS_CONFIG.keys())
held_ticker = st.sidebar.selectbox("Katera delnica je trenutno v poziciji?", options=tick_list, index=tick_list.index("CRWD"))
regime_txt = market["regime"]
spy_txt = market["spy_chg"]
st.sidebar.markdown("**Trg:** " + str(regime_txt) + " (SPY 20d: " + str(spy_txt) + "%)")
if regime_txt == "RISK-OFF":
    st.sidebar.warning("RISK-OFF: zmanjsaj velikost pozicije, A+ samo izjemoma.")
st.sidebar.caption("Banner se pokaze v zadnjih 30 minutah pred zaprtjem trga ob osvezitvi strani.")

evening = get_evening_decision(held_ticker)
if is_preclose_window():
    banner_html = build_preclose_banner(held_ticker, evening)
    if banner_html:
        st.markdown(banner_html, unsafe_allow_html=True)

m = data.get("MNDY", {"price": 106.86, "chg": 0.0, "ps": 3.3})
m_price = m["price"]
m_chg = m["chg"]
m_ps = m["ps"]
m_col = "#10B981" if m_chg >= 0 else "#EF4444"
m_sign = "+" if m_chg >= 0 else ""
mndy_html = (
    '<div class="mndy-hero-card">'
    + '<div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;">'
    + '<div><span style="font-size:1.35rem;font-weight:700;color:#FFFFFF;">MNDY</span> '
    + '<span class="badge-sector">SaaS / Work OS</span> '
    + '<span style="color:#FBBF24;font-size:0.7rem;">NO1 ASIMETRICNA NALOZBA</span>'
    + '<div style="color:#94A3B8;font-size:0.86rem;">monday.com Glavna trdnjava portfelja</div></div>'
    + '<div style="text-align:right;"><div style="font-size:1.7rem;color:#FFFFFF;">$' + str(m_price) + ' <span style="font-size:0.95rem;color:' + m_col + ';">' + m_sign + str(m_chg) + '%</span></div>'
    + '<div style="color:#F59E0B;font-size:0.82rem;">Ocena Asimetrije: 9.4 / 10</div></div></div>'
    + '<div class="metrics-grid">'
    + '<div><div class="metric-label">P/S</div><div class="metric-value">' + str(m_ps) + 'x</div></div>'
    + '<div><div class="metric-label">PEG</div><div class="metric-value">0.62</div></div>'
    + '<div><div class="metric-label">Rast</div><div class="metric-value">+24.2%</div></div>'
    + '<div><div class="metric-label">FCF</div><div class="metric-value">21.8%</div></div>'
    + '<div><div class="metric-label">R40</div><div class="metric-value">46%</div></div>'
    + '</div></div>'
)
st.markdown(mndy_html, unsafe_allow_html=True)

c = data.get("CRWD", {"price": 325.0, "chg": 0.0, "ps": 17.0})
c_price = c["price"]
c_chg = c["chg"]
c_ps = c["ps"]
c_col = "#10B981" if c_chg >= 0 else "#EF4444"
c_sign = "+" if c_chg >= 0 else ""
crwd_html = (
    '<div class="ledger-card">'
    + '<div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;">'
    + '<div><span style="font-size:1.25rem;font-weight:700;color:#FFFFFF;">CRWD</span> '
    + '<span class="badge-sector">Kibernetska varnost</span> '
    + '<span class="aplus-badge">A+ SETUP</span>'
    + '<div style="color:#94A3B8;font-size:0.84rem;">CrowdStrike Takticni obrat dneva</div></div>'
    + '<div style="text-align:right;"><div style="font-size:1.55rem;color:#FFFFFF;">$' + str(c_price) + ' <span style="font-size:0.9rem;color:' + c_col + ';">' + c_sign + str(c_chg) + '%</span></div>'
    + '<div style="color:#10B981;font-size:0.8rem;">Ocena Obrata: 9.5 / 10</div></div></div>'
    + '<div class="metrics-grid">'
    + '<div><div class="metric-label">P/S</div><div class="metric-value">' + str(c_ps) + 'x</div></div>'
    + '<div><div class="metric-label">PEG</div><div class="metric-value">1.80</div></div>'
    + '<div><div class="metric-label">Rast</div><div class="metric-value">+28%</div></div>'
    + '<div><div class="metric-label">R40</div><div class="metric-value">60%</div></div>'
    + '</div></div>'
)
st.markdown(crwd_html, unsafe_allow_html=True)

col_radar, col_table = st.columns([1, 1.25])

with col_radar:
    st.markdown("<h3>Primerjava 4 stebrov</h3>", unsafe_allow_html=True)
    selected_tickers = st.multiselect("Izberite delnice:", options=tick_list, default=["MNDY", "CRWD", "NOW", "PLTR"])
    categories = ["Sentiment", "Makro", "Temelji", "Podcenjenost"]
    fig = go.Figure()
    colors = {"MNDY": "#F59E0B", "CRWD": "#10B981", "SNOW": "#60A5FA", "NOW": "#8B5CF6", "PLTR": "#EF4444", "DELL": "#38BDF8", "HUBS": "#F97316", "DDOG": "#A855F7", "TEAM": "#EC4899", "PANW": "#64748B"}
    for t in selected_tickers:
        cfg = TICKERS_CONFIG[t]
        vals = [cfg["sentiment"], cfg["makro"], cfg["temelji"], cfg["podcenjenost"]]
        vals.append(vals[0])
        fig.add_trace(go.Scatterpolar(r=vals, theta=categories + [categories[0]], name=t, line=dict(color=colors.get(t, "#FFFFFF"), width=2), fill="toself"))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=300, margin=dict(l=20, r=20, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

with col_table:
    st.markdown("<h3>Primerjalna tabela</h3>", unsafe_allow_html=True)
    rows = []
    for t, cfg in TICKERS_CONFIG.items():
        ld = data.get(t, {"price": 0.0, "chg": 0.0, "ps": 0.0})
        sc = round((cfg["sentiment"] * 1.2 + cfg["makro"] * 1.0 + cfg["temelji"] * 1.1 + cfg["podcenjenost"] * 1.4) / 4.7, 1)
        rows.append({"Ticker": t, "Cena": ld["price"], "P/S": ld["ps"], "Rast": cfg["growth"], "R40": cfg["r40"], "Ocena": sc, "Status": cfg["category"]})
    df = pd.DataFrame(rows).sort_values(by="Ocena", ascending=False)
    st.dataframe(df, use_container_width=True, hide_index=True)

col_rot, col_exit = st.columns(2)
with col_rot:
    rot_html = (
        '<div class="ledger-card">'
        + '<h4 style="color:#10B981;">Capital Rotation Radar</h4>'
        + '<p style="font-size:0.82rem;color:#94A3B8;">Trg: ' + str(regime_txt) + ' (SPY 20d ' + str(spy_txt) + '%)</p>'
        + '<div style="background:rgba(16,185,129,0.06);border:1px solid rgba(16,185,129,0.25);border-radius:8px;padding:10px 14px;font-size:0.82rem;color:#6EE7B7;">MNDY ostaja No1 (9.4). Ni potrebe po rotaciji.</div>'
        + '</div>'
    )
    st.markdown(rot_html, unsafe_allow_html=True)

with col_exit:
    st.markdown('<div class="ledger-card"><h4 style="color:#F59E0B;">MNDY Stopnje</h4><div style="font-size:0.82rem;color:#CBD5E1;">1. Tartca 220-240: prodaj 20-25%.<br>2. Tarca 280-310: prodaj 50%.<br>3. Tarca nad 340: popolna prodaja.</div></div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown("<h3>Avtonomni AI Analitik</h3>", unsafe_allow_html=True)
if st.button("POZENI AVTONOMNI AI PREGLED TRGA"):
    if not api_key:
        st.error("Vnesite Gemini API kljuc v levi stranski vrstici.")
    else:
        with st.spinner("Povezovanje z Gemini AI..."):
            prompt_text = "Ti si borzni analitik The Value Ledger 2.0. Cene: " + str(data) + " Trg: " + str(regime_txt) + ". Pripravi porocilo: 1. MNDY long, 2. A+ takticni zmagovalec, 3. izstop pred 21:00 CET. Odgovori v slovenscini z ocenami 1-10."
            clean_key = api_key.strip()
            payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
            success = False
            report_text = ""
            used_model = ""
      
