import streamlit as st
import yfinance as yf
import pandas as pd
import google.generativeai as genai
from datetime import datetime
import pytz

# --- NASTAVITEV STRANI ---
st.set_page_config(page_title="The Value Ledger 2.0", page_icon="💎", layout="wide")

# --- LUXURY DARK TERMINAL CSS ---
st.markdown("""
<style>
    html, body, [class*="css"] { background-color: #050508 !important; color: #F3F4F6 !important; font-family: sans-serif; }
    .stApp { background-color: #050508; }
    .card { background: rgba(17, 24, 39, 0.75); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 20px; margin-bottom: 18px; }
    .hero-mndy { border: 2px solid #F59E0B; box-shadow: 0 0 20px rgba(245, 158, 11, 0.25); background: rgba(24, 20, 10, 0.85); }
    .aplus-badge { border: 1.8px solid #F59E0B; color: #FBBF24; padding: 4px 12px; border-radius: 9999px; font-weight: 700; font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

# --- VNOS BREZPLAČNEGA GOOGLE GEMINI API KLJUČA ---
st.sidebar.markdown("### 🔑 Google Gemini AI Nastavitev")
api_key = st.sidebar.text_input("Vnesite vaš brezplačni Gemini API ključ:", type="password")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    model = None
    st.sidebar.warning("⚠️ Vnesite vaš API ključ zgoraj.")

# --- BAZA DELNIC ---
WATCHLIST = ["MNDY", "CRWD", "SNOW", "HUBS", "DELL", "DDOG", "TEAM", "NOW", "PLTR"]

@st.cache_data(ttl=300)
def get_live_data():
    results = {}
    for t in WATCHLIST:
        try:
            ticker = yf.Ticker(t)
            info = ticker.info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
            prev = info.get("regularMarketPreviousClose") or price
            chg = ((price - prev) / prev * 100) if prev else 0.0
            ps = info.get("priceToSalesTrailing12Months") or 0.0
            results[t] = {"price": round(price, 2), "chg": round(chg, 2), "ps": round(ps, 2)}
        except:
            results[t] = {"price": 100.0, "chg": 0.0, "ps": 3.0}
    return results

data = get_live_data()

# --- GLAVA ---
lj_time = datetime.now(pytz.timezone("Europe/Ljubljana")).strftime("%d.%m.%Y · %H:%M CET")
st.markdown("## 💎 THE VALUE LEDGER 2.0 · <span style='color:#60A5FA;'>Avtonomni AI Terminal</span>", unsafe_allow_html=True)
st.caption(f"Sentiment Obrata × Makro Zaščita × Temelji × Podcenjenost · Čas: {lj_time}")

# --- GUMB ZA DNEVNI AI PREGLED TRGA ---
if st.button("🤖 POŽENI AVTONOMNI AI PREGLED TRGA (Iskanje A+ Obratov)"):
    if not model:
        st.error("Prosimo, vnesite API ključ v levi stranski vrstici!")
    else:
        with st.spinner("AI analizira trg, absorpcijo panike in išče A+ obrate..."):
            prompt = f"""
            Ti si borzni analitik po modelu 'The Value Ledger 2.0'.
            Formula: (Sentiment Obrata x Katalizator) x Makro Zascita x Temelji x Podcenjenost.
            Trenutne borzne cene: {data}
            
            Analiziraj:
            1. MNDY (#1 Asimetricni Long): Ali ostaja #1 ali priporocas rotacijo?
            2. Doloci EDINEGA #1 A+ Takticnega zmagovalca dneva (kdor ima najvecjo preprodanost in odboj).
            3. Podaj navodilo za izstop ob 21:00 CET pred zaprtjem trga.
            
            Odgovori v slovenscini, pregledno z ocenami od 1 do 10.
            """
            response = model.generate_content(prompt)
            st.session_state["ai_report"] = response.text

if "ai_report" in st.session_state:
    st.markdown("### 🧠 Poročilo AI Analitika")
    st.markdown(f"<div class='card'>{st.session_state['ai_report']}</div>", unsafe_allow_html=True)

# --- 1. KARTICA: MNDY ---
m = data.get("MNDY", {"price": 106.86, "chg": 0.0, "ps": 3.3})
st.markdown(f"""
<div class="card hero-mndy">
    <div style="display:flex; justify-content:space-between;">
        <div>
            <h3>💎 MNDY · #1 Asimetrični Zmagovalec (monday.com)</h3>
            <p style="color:#9CA3AF;">Glavna naložba (+200 % potencial do 320 $+) · 1.66B $ gotovine, 0 dolga</p>
        </div>
        <div style="text-align:right;">
            <h2>${m['price']} <span style="font-size:1rem; color:#10B981;">+{m['chg']}%</span></h2>
            <div style="color:#F59E0B; font-weight:700;">P/S: {m['ps']}x · Ocena: 9.4 / 10</div>
        </div>
    </div>
    <div style="margin-top:10px; font-size:0.85rem; color:#D1D5DB; border-top:1px solid rgba(245,158,11,0.2); padding-top:8px;">
        <strong>Stopnje za prodajo:</strong> 1. Tarča: $230 (5.5x) · 2. Tarča: $290 (7.5x) · 3. Tarča: $350+ (8.5x+)
    </div>
</div>
""", unsafe_allow_html=True)

# --- 2. TABELA DELNIC ---
st.markdown("### 📊 Živi Borzni Podatki")
rows = []
for ticker, d in data.items():
    rows.append({
        "Ticker": ticker,
        "Cena ($)": f"${d['price']}",
        "Dnevni Premik (%)": f"{d['chg']}%",
        "P/S Multiplikator": f"{d['ps']}x"
    })
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
