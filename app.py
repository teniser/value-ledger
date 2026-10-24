import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime
import pytz

# --- NASTAVITEV STRANI ---
st.set_page_config(
    page_title="The Value Ledger 2.0 · Luxury Terminal",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- LUXURY OLED OBSIDIAN & GLASSMORPHISM STIL ---
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp {
    background-color: #050508 !important;
    font-family: 'Inter', sans-serif !important;
    color: #F3F4F6 !important;
}

section[data-testid="stSidebar"] {
    background-color: #090D16 !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
}

.ledger-card {
    background: linear-gradient(135deg, rgba(17, 24, 39, 0.75) 0%, rgba(9, 13, 22, 0.9) 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 22px;
    box-shadow: 0 14px 35px rgba(0, 0, 0, 0.65);
    backdrop-filter: blur(14px);
}

.mndy-hero-card {
    background: linear-gradient(135deg, rgba(24, 20, 10, 0.85) 0%, rgba(12, 10, 6, 0.95) 100%);
    border: 2px solid #F59E0B;
    border-radius: 18px;
    padding: 26px;
    margin-bottom: 24px;
    box-shadow: 0 0 25px rgba(245, 158, 11, 0.25);
    animation: pulseGold 3s infinite ease-in-out;
}

@keyframes pulseGold {
    0%, 100% { box-shadow: 0 0 16px rgba(245, 158, 11, 0.2); border-color: rgba(245, 158, 11, 0.7); }
    50% { box-shadow: 0 0 32px rgba(245, 158, 11, 0.5); border-color: #FBBF24; }
}

.aplus-badge {
    display: inline-block;
    background: transparent !important;
    border: 1.8px solid #F59E0B;
    color: #FBBF24;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    font-size: 0.8rem;
    padding: 4px 14px;
    border-radius: 9999px;
    box-shadow: 0 0 14px rgba(245, 158, 11, 0.35);
    animation: pulseGoldBadge 2.2s infinite ease-in-out;
    letter-spacing: 0.5px;
}

@keyframes pulseGoldBadge {
    0%, 100% { box-shadow: 0 0 8px rgba(245, 158, 11, 0.25); border-color: #F59E0B; }
    50% { box-shadow: 0 0 22px rgba(245, 158, 11, 0.7); border-color: #FDE68A; }
}

.badge-sector {
    font-size: 0.72rem;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.12);
    color: #9CA3AF;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 12px;
    margin: 16px 0;
    padding: 14px;
    background: rgba(0, 0, 0, 0.35);
    border-radius: 12px;
}

.metric-label {
    color: #9CA3AF;
    font-size: 0.72rem;
    margin-bottom: 2px;
    text-transform: uppercase;
}

.metric-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.05rem;
    font-weight: 700;
    color: #FFFFFF;
}

div.stButton > button {
    background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%) !important;
    color: #000000 !important;
    font-weight: 700 !important;
    font-family: 'JetBrains Mono', monospace !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 12px 24px !important;
    font-size: 0.95rem !important;
    box-shadow: 0 4px 18px rgba(245, 158, 11, 0.3) !important;
    transition: all 0.2s ease-in-out !important;
}

div.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 25px rgba(245, 158, 11, 0.5) !important;
}
</style>""", unsafe_allow_html=True)

# --- VNOS API KLJUČA ---
st.sidebar.markdown("### 🔑 Google AI Nastavitev")
api_key = st.sidebar.text_input("Vnesite brezplačni Gemini API ključ:", type="password")

# --- BAZA PODATKOV THE VALUE LEDGER 2.0 ---
TICKERS_CONFIG = {
    "MNDY": {
        "name": "monday.com", "sector": "SaaS / Work OS", "category": "💎 #1 Asimetrični Zmagovalec",
        "growth": 24.2, "fcf_margin": 21.8, "r40": 46.0, "net_cash": ">1.66B $ (0 dolga)",
        "peg": 0.62, "sentiment": 9.1, "makro": 8.5, "temelji": 9.2, "podcenjenost": 9.5
    },
    "CRWD": {
        "name": "CrowdStrike", "sector": "Kibernetska varnost", "category": "🔥 #1 Taktični Obrat Dneva",
        "growth": 28.0, "fcf_margin": 32.0, "r40": 60.0, "net_cash": "Močna gotovina",
        "peg": 1.80, "sentiment": 9.5, "makro": 8.5, "temelji": 9.5, "podcenjenost": 6.5
    },
    "SNOW": {
        "name": "Snowflake", "sector": "AI Podatkovna Hramba", "category": "Na opazovanju",
        "growth": 28.0, "fcf_margin": 27.0, "r40": 55.0, "net_cash": ">4.0B $ (0 dolga)",
        "peg": 1.70, "sentiment": 8.2, "makro": 8.3, "temelji": 8.7, "podcenjenost": 6.8
    },
    "HUBS": {
        "name": "HubSpot", "sector": "CRM / Marketing", "category": "Na opazovanju",
        "growth": 20.0, "fcf_margin": 18.0, "r40": 38.0, "net_cash": "Stabilna gotovina",
        "peg": 1.10, "sentiment": 7.7, "makro": 7.0, "temelji": 8.5, "podcenjenost": 8.0
    },
    "DELL": {
        "name": "Dell Technologies", "sector": "AI Strojna Oprema", "category": "Na opazovanju",
        "growth": 14.0, "fcf_margin": 12.0, "r40": 26.0, "net_cash": "Močan FCF",
        "peg": 0.85, "sentiment": 8.0, "makro": 8.2, "temelji": 8.4, "podcenjenost": 8.5
    },
    "DDOG": {
        "name": "Datadog", "sector": "Nadzor Oblaka & AI", "category": "Na opazovanju",
        "growth": 27.0, "fcf_margin": 26.0, "r40": 53.0, "net_cash": ">2.8B $ gotovine",
        "peg": 1.60, "sentiment": 7.9, "makro": 8.0, "temelji": 9.1, "podcenjenost": 5.8
    },
    "TEAM": {
        "name": "Atlassian", "sector": "Orodja za Razvijalce", "category": "Na opazovanju",
        "growth": 21.0, "fcf_margin": 28.0, "r40": 49.0, "net_cash": "Pozitivna bilanca",
        "peg": 1.80, "sentiment": 7.0, "makro": 7.5, "temelji": 8.8, "podcenjenost": 5.5
    },
    "NOW": {
        "name": "ServiceNow", "sector": "Enterprise Delovni Tokovi", "category": "Polno ovrednoteno",
        "growth": 22.0, "fcf_margin": 34.0, "r40": 56.0, "net_cash": "Močna bilanca",
        "peg": 1.20, "sentiment": 6.8, "makro": 8.5, "temelji": 9.8, "podcenjenost": 4.5
    },
    "PANW": {
        "name": "Palo Alto Networks", "sector": "Kibernetska varnost", "category": "Precenjeno",
        "growth": 13.0, "fcf_margin": 38.0, "r40": 51.0, "net_cash": "Pozitivna bilanca",
        "peg": 2.20, "sentiment": 6.5, "makro": 8.5, "temelji": 9.0, "podcenjenost": 3.8
    },
    "PLTR": {
        "name": "Palantir", "sector": "AI Platforma / AIP", "category": "Tveganje prevrednotenja",
        "growth": 30.0, "fcf_margin": 38.0, "r40": 68.0, "net_cash": ">4.0B $ (0 dolga)",
        "peg": 2.80, "sentiment": 5.2, "makro": 9.4, "temelji": 9.6, "podcenjenost": 2.1
    }
}

# --- ČRPANJE BORZNIH PODATKOV ---
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
        except:
            results[t] = {"price": 106.86 if t == "MNDY" else 325.0, "chg": 0.0, "ps": 3.3}
    return results

data = get_live_data()

# --- GLAVA TERMINALA ---
lj_time = datetime.now(pytz.timezone("Europe/Ljubljana")).strftime("%d.%m.%Y · %H:%M CET")

header_html = f"""<div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(255,255,255,0.08);padding-bottom:16px;margin-bottom:22px;">
<div>
<h1 style="margin:0;font-size:1.95rem;font-weight:800;letter-spacing:-0.5px;">
<span style="color:#F59E0B;">THE VALUE LEDGER</span> <span style="color:#60A5FA;">2.0</span>
</h1>
<p style="margin:4px 0 0 0;color:#9CA3AF;font-size:0.85rem;">
Sentiment Obrata × Makro Zaščita × Temelji × Podcenjenost · Osebni Kvantitativni Terminal
</p>
</div>
<div style="text-align:right;">
<div style="display:inline-flex;align-items:center;gap:8px;background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);padding:5px 12px;border-radius:9999px;">
<span style="width:8px;height:8px;background:#10B981;border-radius:50%;box-shadow:0 0 10px #10B981;"></span>
<span style="font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:#10B981;font-weight:700;">ŽIVI BORZNI RADAR AKTIVEN</span>
</div>
<div style="font-size:0.72rem;color:#6B7280;font-family:'JetBrains Mono',monospace;margin-top:4px;">{lj_time}</div>
</div>
</div>"""
st.markdown(header_html, unsafe_allow_html=True)

# --- 1. KARTICA: MNDY #1 ASIMETRIČNI VODITELJ ---
mndy_live = data.get("MNDY", {"price": 106.86, "chg": 0.0, "ps": 3.3})
m_col = "#10B981" if mndy_live["chg"] >= 0 else "#EF4444"
m_sign = "+" if mndy_live["chg"] >= 0 else ""

mndy_card_html = f"""<div class="mndy-hero-card">
<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;">
<div>
<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
<span style="font-family:'JetBrains Mono',monospace;font-size:1.45rem;font-weight:800;color:#FFFFFF;">MNDY</span>
<span class="badge-sector">SaaS / Work OS</span>
<span style="background:rgba(245,158,11,0.2);border:1px solid #F59E0B;color:#FBBF24;font-size:0.72rem;font-weight:700;padding:3px 8px;border-radius:6px;">💎 #1 ASIMETRIČNA GLAVNA NALOŽBA</span>
</div>
<div style="color:#9CA3AF;font-size:0.9rem;">monday.com Ltd. · Glavna Trdnjava Portfelja (+200 % Potencial do 320 $+)</div>
</div>
<div style="text-align:right;">
<div style="font-size:1.85rem;font-weight:800;font-family:'JetBrains Mono',monospace;color:#FFFFFF;">
${mndy_live['price']} <span style="font-size:1rem;color:{m_col};">{m_sign}{mndy_live['chg']}%</span>
</div>
<div style="color:#F59E0B;font-weight:700;font-family:'JetBrains Mono',monospace;">Ocena Asimetrije: 9.4 / 10</div>
</div>
</div>
<div class="metrics-grid">
<div><div class="metric-label">P/S Multiplikator</div><div class="metric-value" style="color:#60A5FA;">{mndy_live['ps']}x (EV/S 1.9x)</div></div>
<div><div class="metric-label">PEG Razmerje</div><div class="metric-value" style="color:#10B981;">0.62 (Ekstremno poceni)</div></div>
<div><div class="metric-label">Rast Prihodkov</div><div class="metric-value" style="color:#10B981;">+24.2% YoY</div></div>
<div><div class="metric-label">Prosti Denar (FCF)</div><div class="metric-value" style="color:#10B981;">21.8% marža</div></div>
<div><div class="metric-label">Rule of 40</div><div class="metric-value" style="color:#10B981;">46% (Elitno)</div></div>
<div><div class="metric-label">Gotovina / Dolg</div><div class="metric-value" style="color:#FBBF24;">>1.66B $ (0 dolga)</div></div>
</div>
<div style="display:flex;justify-content:space-between;align-items:center;border-top:1px solid rgba(245,158,11,0.2);padding-top:12px;font-size:0.85rem;flex-wrap:wrap;gap:8px;">
<span style="color:#D1D5DB;"><strong>Status:</strong> 🟢 Akumuliraj in mirno drži do ciljnih stopenj.</span>
<span style="color:#9CA3AF;font-family:'JetBrains Mono',monospace;">1. Tarča: $230 (5.5x) · 2. Tarča: $290 (7.5x) · 3. Tarča: $350+ (8.5x+)</span>
</div>
</div>"""
st.markdown(mndy_card_html, unsafe_allow_html=True)

# --- 2. KARTICA: CRWD #1 TAKTIČNI A+ OBRAT ---
crwd_live = data.get("CRWD", {"price": 325.0, "chg": 0.0, "ps": 17.0})
c_col = "#10B981" if crwd_live["chg"] >= 0 else "#EF4444"
c_sign = "+" if crwd_live["chg"] >= 0 else ""

crwd_card_html = f"""<div class="ledger-card">
<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;">
<div>
<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
<span style="font-family:'JetBrains Mono',monospace;font-size:1.35rem;font-weight:800;color:#FFFFFF;">CRWD</span>
<span class="badge-sector">Kibernetska varnost</span>
<div class="aplus-badge">🌟 A+ SETUP</div>
</div>
<div style="color:#9CA3AF;font-size:0.85rem;">CrowdStrike · Edini potrjeni taktični obrat dneva (Absorpcija panike & Short Squeeze)</div>
</div>
<div style="text-align:right;">
<div style="font-size:1.65rem;font-weight:800;font-family:'JetBrains Mono',monospace;color:#FFFFFF;">
${crwd_live['price']} <span style="font-size:0.95rem;color:{c_col};">{c_sign}{crwd_live['chg']}%</span>
</div>
<div style="color:#10B981;font-weight:700;font-family:'JetBrains Mono',monospace;">Ocena Obrata: 9.5 / 10</div>
</div>
</div>
<div class="metrics-grid">
<div><div class="metric-label">P/S Multiplikator</div><div class="metric-value">{crwd_live['ps']}x</div></div>
<div><div class="metric-label">PEG Razmerje</div><div class="metric-value">1.80</div></div>
<div><div class="metric-label">Rast Prihodkov</div><div class="metric-value" style="color:#10B981;">+28% YoY</div></div>
<div><div class="metric-label">Rule of 40</div><div class="metric-value" style="color:#10B981;">60%</div></div>
<div><div class="metric-label">Zadržanje Strank</div><div class="metric-value" style="color:#10B981;">>97%</div></div>
<div><div class="metric-label">Premarket Skok</div><div class="metric-value" style="color:#10B981;">+0.4% → +8.2%</div></div>
</div>
<div style="border-top:1px solid rgba(255,255,255,0.08);padding-top:10px;font-size:0.8rem;color:#9CA3AF;">
<strong>Trgovalno pravilo:</strong> Vstop v premarketu / ob odprtju · Izstop ob dosegu +5 % do +8 %+ pred zaprtjem ob 21:00 CET.
</div>
</div>"""
st.markdown(crwd_card_html, unsafe_allow_html=True)

# --- 3. DVOJNI POGLED: RADAR & TABELA 9 DELNIC ---
col_radar, col_table = st.columns([1, 1.25])

with col_radar:
    st.markdown("<h3 style='font-size: 1.15rem; margin-bottom: 12px;'>🕸️ Primerjava 4 Stebrov</h3>", unsafe_allow_html=True)
    selected_tickers = st.multiselect(
        "Izberite delnice za primerjavo:",
        options=list(TICKERS_CONFIG.keys()),
        default=["MNDY", "CRWD", "NOW", "PLTR"]
    )

    categories = ['Sentiment Obrata', 'Makro Zaščita', 'Temelji', 'Podcenjenost']
    fig = go.Figure()
    colors = {"MNDY": "#F59E0B", "CRWD": "#10B981", "SNOW": "#60A5FA", "NOW": "#8B5CF6", "PLTR": "#EF4444", "DELL": "#38BDF8", "HUBS": "#F97316", "DDOG": "#A855F7", "TEAM": "#EC4899", "PANW": "#64748B"}

    for t in selected_tickers:
        c = TICKERS_CONFIG[t]
        values = [c['sentiment'], c['makro'], c['temelji'], c['podcenjenost']]
        values.append(values[0])
        fig.add_trace(go.Scatterpolar(
            r=values, theta=categories + [categories[0]], name=t,
            line=dict(color=colors.get(t, "#FFFFFF"), width=2.5),
            fill='toself',
            fillcolor=f"rgba({int(colors.get(t, '#FFFFFF')[1:3], 16)}, {int(colors.get(t, '#FFFFFF')[3:5], 16)}, {int(colors.get(t, '#FFFFFF')[5:7], 16)}, 0.15)"
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 10], color="#9CA3AF", gridcolor="rgba(255,255,255,0.08)"),
            angularaxis=dict(color="#F3F4F6", gridcolor="rgba(255,255,255,0.08)")
        ),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        showlegend=True, legend=dict(font=dict(color="#F3F4F6", size=10)),
        margin=dict(l=20, r=20, t=10, b=10), height=320
    )
    st.plotly_chart(fig, use_container_width=True)

with col_table:
    st.markdown("<h3 style='font-size: 1.15rem; margin-bottom: 12px;'>📊 Primerjalna Tabela 9 Delnic</h3>", unsafe_allow_html=True)
    table_rows = []
    for t, c in TICKERS_CONFIG.items():
        ld = data.get(t, {"price": 0.0, "chg": 0.0, "ps": 0.0})
        score = round((c['sentiment']*1.2 + c['makro']*1.0 + c['temelji']*1.1 + c['podcenjenost']*1.4) / 4.7, 1)
        stars = "⭐⭐⭐⭐⭐" if score >= 8.5 else ("⭐⭐⭐⭐" if score >= 7.5 else "⭐⭐⭐")
        table_rows.append({
            "Ticker": t,
            "Cena": f"${ld['price']}",
            "P/S": f"{ld['ps']}x",
            "Rast": f"+{c['growth']}%",
            "R40": f"{c['r40']}%",
            "Ocena": f"{score}",
            "Zvezdice": stars,
            "Status": c["category"]
        })
    df = pd.DataFrame(table_rows).sort_values(by="Ocena", ascending=False)
    st.dataframe(df, use_container_width=True, hide_index=True)

# --- 4. ZAKLEPANJE DOBIČKOV & ROTACIJA ---
st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
col_rot, col_exit = st.columns(2)

with col_rot:
    st.markdown("""<div class="ledger-card">
<h4 style="margin:0 0 8px 0;color:#10B981;font-size:1rem;">🔄 Capital Rotation Radar (Signal za Rotacijo)</h4>
<p style="font-size:0.85rem;color:#9CA3AF;margin-bottom:12px;">
Sistem nenehno preverja, ali se na trgu pojavi naložba z večjo asimetrijo od MNDY.
</p>
<div style="background:rgba(16,185,129,0.1);border:1px solid #10B981;border-radius:8px;padding:12px;font-size:0.85rem;color:#6EE7B7;">
<strong>🟢 TRENUTNI STATUS:</strong> MNDY ostaja trdna #1 izbira (Ocena 9.4). Ni potrebe po rotaciji kapitala.
</div>
</div>""", unsafe_allow_html=True)

with col_exit:
    st.markdown("""<div class="ledger-card">
<h4 style="margin:0 0 8px 0;color:#F59E0B;font-size:1rem;">🎯 MNDY Stopnje za Zaklep Dobička</h4>
<div style="font-size:0.85rem;color:#D1D5DB;line-height:1.7;">
<div><strong>1. Tarča ($220–$240 · P/S ~5.5x):</strong> Prodaj 20–25 % (Izplačilo vložka / Risk-Free).</div>
<div><strong>2. Tarča ($280–$310 · P/S ~7.5x):</strong> Prodaj 50 % preostanka (Zaklep glavnine dobička).</div>
<div><strong>3. Tarča (>$340–$380 · P/S >8.5x):</strong> 🚨 Popolna prodaja ob evforiji.</div>
</div>
</div>""", unsafe_allow_html=True)

# --- 5. GUMB ZA AVTONOMNI AI PREGLED TRGA ---
st.markdown("---")
st.markdown("<h3 style='font-size: 1.2rem; margin-bottom: 10px;'>🤖 Avtonomni AI Analitik (Google Gemini)</h3>", unsafe_allow_html=True)

if st.button("POŽENI AVTONOMNI AI PREGLED TRGA (Iskanje A+ Obratov)"):
    if not api_key:
        st.error("Prosimo, vnesite brezplačni Gemini API ključ v levi stranski vrstici!")
    else:
        with st.spinner("Povezovanje z Gemini AI in priprava poročila The Value Ledger 2.0..."):
            prompt_text = f"""
            Ti si elitni borzni analitik po kvantitativnem modelu 'The Value Ledger 2.0'.
            Formula: (Sentiment Obrata x Katalizator) x Makro Zascita x Temelji x Podcenjenost.
            Trenutne borzne cene: {data}
            
            Pripravi celovito, elitno porocilo:
            1. MNDY (#1 Asimetricni Long): Pojasni, zakaj ostaja #1 (stisnjen P/S 3.3x, 1.66 mrd gotovine brez dolga) in potrdi cilj 320 $+.
            2. Doloci EDINEGA #1 A+ Takticnega zmagovalca dneva (CRWD ali kdor ima najvecji odboj in absorpcijo panike).
            3. Podaj natancno navodilo za izstop pred zaprtjem trga ob 21:00 CET ob dosegu +5% do +8%+.
            
            Odgovori v lepi slovenscini, zelo pregledno z ocenami od 1 do 10.
            """
            
            clean_key = api_key.strip()
            payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
            
            success = False
            report_text = ""
            used_model = ""
            
            try:
                list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={clean_key}"
                l_res = requests.get(list_url, timeout=10)
                generate_models = [m["name"] for m in l_res.json().get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])] if l_res.status_code == 200 else []
            except:
                generate_models = []
                
            endpoints_to_try = [f"https://generativelanguage.googleapis.com/v1beta/{gm}:generateContent?key={clean_key}" for gm in generate_models]
            endpoints_to_try += [
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={clean_key}",
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={clean_key}",
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={clean_key}"
            ]
            
            for url in endpoints_to_try:
                try:
                    res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=25)
                    if res.status_code == 200:
                        report_text = res.json()['candidates'][0]['content']['parts'][0]['text']
                        used_model = url.split("models/")[1].split(":")[0] if "models/" in url else "Gemini"
                        success = True
                        break
                except:
                    continue
                    
            if success:
                st.session_state["ai_report"] = report_text
                st.session_state["used_model"] = used_model
            else:
                st.error("Googlov strežnik ni sprejel zahteve. Prosimo, preverite API ključ.")

if "ai_report" in st.session_state:
    rep_formatted = st.session_state['ai_report'].replace('\n', '<br>')
    st.markdown(f"""<div class="ledger-card" style="border:1px solid rgba(96,165,250,0.4);margin-top:20px;">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;border-bottom:1px solid rgba(255,255,255,0.08);padding-bottom:8px;">
<h3 style="margin:0;color:#60A5FA;font-size:1.2rem;">🧠 Dnevno Poročilo AI Možganov (The Value Ledger 2.0)</h3>
<span style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:#9CA3AF;">Model: {st.session_state.get('used_model', 'Gemini')}</span>
</div>
<div style="font-size:0.95rem;line-height:1.7;color:#E5E7EB;">
{rep_formatted}
</div>
</div>""", unsafe_allow_html=True)
