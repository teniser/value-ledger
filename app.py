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
</style>
""", unsafe_allow_html=True)

# --- VNOS BREZPLAČNEGA GOOGLE GEMINI API KLJUČA ---
st.sidebar.markdown("### 🔑 Google Gemini AI Nastavitev")
api_key = st.sidebar.text_input("Vnesite vaš brezplačni Gemini API ključ:", type="password")

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
    if not api_key:
        st.error("Prosimo, vnesite brezplačni API ključ v levi stranski vrstici!")
    else:
        with st.spinner("Povezovanje z najnovejšim Gemini AI modelom in analiza trga..."):
            genai.configure(api_key=api_key.strip())
            
            prompt = f"""
            Ti si elitni borzni analitik po kvantitativnem modelu 'The Value Ledger 2.0'.
            Formula: (Sentiment Obrata x Katalizator) x Makro Zascita x Temelji x Podcenjenost.
            Trenutne cene delnic na trgu: {data}
            
            Pripravi jedrnato, profesionalno porocilo:
            1. MNDY (#1 Asimetricni Long): Pojasni, zakaj ostaja #1 (stisnjen P/S 3.3x, 1.66 mrd gotovine brez dolga) in potrdi cilj 320 $+.
            2. Doloci EDINEGA #1 A+ Takticnega zmagovalca dneva (CRWD ali kdor ima najvecji odboj in absorpcijo panike).
            3. Podaj natancno navodilo za izstop pred zaprtjem trga ob 21:00 CET ob dosegu +5% do +8%+.
            
            Odgovori v slovenscini, zelo pregledno z ocenami od 1 do 10.
            """
            
            # Seznam modelov po vrstnem redu od najnovejšega
            candidate_models = [
                "gemini-1.5-flash-latest",
                "gemini-1.5-flash-8b",
                "gemini-1.5-pro-latest",
                "gemini-2.0-flash-exp",
                "gemini-1.5-flash",
                "gemini-1.0-pro"
            ]
            
            success = False
            last_err = ""
            for m_name in candidate_models:
                try:
                    ai_engine = genai.GenerativeModel(m_name)
                    response = ai_engine.generate_content(prompt)
                    st.session_state["ai_report"] = response.text
                    st.session_state["used_model"] = m_name
                    success = True
                    break
                except Exception as e:
                    last_err = str(e)
                    continue
            
            if not success:
                st.error(f"Napaka pri klicu AI modelov. Zadnja napaka: {last_err}")

if "ai_report" in st.session_state:
    st.markdown("### 🧠 Poročilo AI Analitika")
    st.caption(f"Uspešno zagnano prek modela: {st.session_state.get('used_model', 'Gemini')}")
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
            <h2>${m['price']} <span style="font-size:1rem; color:#10B981;">{m['chg']}%</span></h2>
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
