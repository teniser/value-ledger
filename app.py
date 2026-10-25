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

# 150 top liquid tech/growth/SaaS/Semis tickerjev
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

@st.cache_data(ttl=900, show_spinner=False)
def get_capital_rotation():
    # ETF-ji kot posrednik za tok denarja po sektorjih (relativna moc proti SPY)
    etfs = {"SaaS (IGV)": "IGV", "Semis (SMH)": "SMH", "Cyber (CIBR)": "CIBR", "Tech (QQQ)": "QQQ",
            "Finance (XLF)": "XLF", "Zdravje (XLV)": "XLV", "Energija (XLE)": "XLE",
            "Potrosnja (XLY)": "XLY", "Small caps (IWM)": "IWM"}
    closes = {}
    for tk in list(etfs.values()) + ["SPY"]:
        try:
            h = yf.Ticker(tk).history(period="8mo", interval="1d", auto_adjust=False)
            if h is not None and len(h) > 70:
                closes[tk] = h["Close"].astype(float).dropna()
        except Exception:
            pass
    if "SPY" not in closes:
        return {"rows": [], "pair": "NI PODATKOV", "pair_detail": "", "leader": None}

    def ret(s, n):
        return (float(s.iloc[-1]) / float(s.iloc[-1 - n]) - 1) * 100

    spy = closes["SPY"]
    rows = []
    for name, tk in etfs.items():
        if tk not in closes:
            continue
        s = closes[tk]
        r5, r20, r60 = ret(s, 5) - ret(spy, 5), ret(s, 20) - ret(spy, 20), ret(s, 60) - ret(spy, 60)
        if r5 > 0 and r20 > 0 and r60 < 0:
            tag = "NOV DENAR"
        elif r20 > 0 and r60 > 0:
            tag = "VODI"
        elif r5 < 0 and r20 < 0 and r60 > 0:
            tag = "DENAR ODTEKA"
        elif r20 < 0:
            tag = "ZAOSTAJA"
        else:
            tag = "NEVTRALNO"
        rows.append({"name": name, "r5": round(r5, 1), "r20": round(r20, 1), "r60": round(r60, 1), "tag": tag})
    rows.sort(key=lambda x: x["r20"], reverse=True)

    pair, pair_detail = "NI PODATKOV", ""
    if "IGV" in closes and "SMH" in closes:
        both = pd.concat([closes["IGV"], closes["SMH"]], axis=1, join="inner").dropna()
        both.columns = ["igv", "smh"]
        if len(both) > 65:
            ratio = both["igv"] / both["smh"]
            p5, p20, p60 = ret(ratio, 5), ret(ratio, 20), ret(ratio, 60)
            above20 = float(ratio.iloc[-1]) > float(ratio.rolling(20).mean().iloc[-1])
            if p20 > 0 and p60 < 0 and above20:
                pair = "ROTACIJA SEMIS -> SAAS (zacetek)"
            elif p20 > 0 and p60 > 0 and above20:
                pair = "SAAS VODI PROTI SEMIS (rotacija potrjena)"
            elif p20 < 0 and p60 > 0:
                pair = "ROTACIJA SAAS -> SEMIS (SaaS slabi)"
            elif p20 < 0 and not above20:
                pair = "SEMIS VODI PROTI SAAS"
            else:
                pair = "NEVTRALNO (ni jasne rotacije)"
            pair_detail = f"IGV/SMH razmerje: 5d {p5:+.1f}%, 20d {p20:+.1f}%, 60d {p60:+.1f}%, nad SMA20: {'DA' if above20 else 'NE'}"
    leader = rows[0]["name"] if rows else None
    return {"rows": rows, "pair": pair, "pair_detail": pair_detail, "leader": leader}

rotation = get_capital_rotation()

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

def get_intraday_df(ticker, period="5d", interval="5m"):
    # prepost=True: vkljuci premarket (od 4:00 ET = 10:00 CET) in after-hours.
    # Vrne samo svece zadnjega trgovalnega dne; zaprtje prejsnje redne seje
    # je v df.attrs["prev_close"] za izracun gapa.
    try:
        raw = yf.Ticker(ticker).history(period=period, interval=interval, prepost=True, auto_adjust=False)
        if raw is None or raw.empty:
            return None
        raw = raw.dropna(subset=["Open","High","Low","Close","Volume"])
        if raw.empty:
            return None
        if raw.index.tz is not None:
            raw.index = raw.index.tz_convert(NY_TZ)
        dates = pd.Series(raw.index.date, index=raw.index)
        last_date = dates.iloc[-1]
        today = raw[dates == last_date].copy()
        prev = raw[dates < last_date]
        prev_close = None
        if len(prev) > 0:
            prev_reg = prev.between_time("09:30", "15:59")
            if len(prev_reg) > 0:
                prev_close = float(prev_reg["Close"].iloc[-1])
        today.attrs["prev_close"] = prev_close
        return today
    except Exception:
        return None

def tactical_vwap(df):
    try:
        typ = (df["High"].astype(float) + df["Low"].astype(float) + df["Close"].astype(float)) / 3.0
        vol = df["Volume"].astype(float)
        vsum = float(vol.sum())
        if vsum <= 0:
            return float(df["Close"].iloc[-1])
        return float((typ * vol).sum() / vsum)
    except Exception:
        return float(df["Close"].iloc[-1])

def tactical_intraday_signal(df):
    if df is None or len(df) < 12:
        return None
    close = df["Close"].astype(float)
    volume = df["Volume"].replace(0, pd.NA).ffill().fillna(0).astype(float)
    last = float(close.iloc[-1])
    prev = float(close.iloc[-2])
    pc = df.attrs.get("prev_close")
    day_open = float(pc) if pc else float(df["Open"].iloc[0])
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
        h, l, c = d["High"].astype(float), d["Low"].astype(float), d["Close"].astype(float)
        pc = c.shift(1)
        tr = pd.concat([h-l, (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)
        atr = float(tr.rolling(14).mean().iloc[-1])
        if not atr or atr != atr:
            return None
        return {"atr": round(atr,2), "stop": round(price - atr*mult_stop,2), "t1": round(price + atr*mult_t1,2), "t2": round(price + atr*mult_t2,2)}
    except Exception:
        return None

@st.cache_data(ttl=1800, show_spinner=False)
def get_asymmetry_score(ticker):
    try:
        info = yf.Ticker(ticker).info
        ps_raw = info.get("priceToSalesTrailing12Months")
        if ps_raw is None or float(ps_raw) < 1.0:
            return {"score": 0.0, "ps": 20.0, "peg": 99.0, "growth": 0.0, "price": 0.0, "net_cash": 0, "debt": 1, "ws_score": 0, "ws_rec": 0, "ws_upside": 0, "ws_num": 0, "vs_med": 0, "fcf_yield": 0, "bad_data": True}
        ps = float(ps_raw)
        peg = float(info.get("pegRatio") or 2.0)
        gr = float(info.get("revenueGrowth") or 0.15)
        if gr > 1.0:
            gr = gr / 100.0
        if gr > 0.40:
            gr = 0.25
        price = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
        price_f = float(price) if price else 0.0
        cash = info.get("totalCash") or 0.0
        debt = info.get("totalDebt") or 0.0
        fcf = info.get("freeCashflow") or 0.0
        rev = info.get("totalRevenue") or 0.0
        mcap = info.get("marketCap") or 0.0
        fcf_m = (float(fcf) / float(rev) * 100) if fcf and rev else 0.0
        net_cash = float(cash) - float(debt)
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
        return {"score": king_adjusted_score(round(s,1), ticker), "ps": round(float(ps),2), "peg": round(float(peg),2), "growth": round(float(gr)*100,1), "price": round(price_f,2), "net_cash": net_cash, "debt": debt, "ws_score": ws["ws_score"], "ws_rec": ws["rec"], "ws_upside": ws["upside"], "ws_num": ws["num"], "vs_med": he["vs_med"], "fcf_yield": he["fcf_yield"], "bad_data": False}
    except Exception:
        return None

@st.cache_data(ttl=1800, show_spinner=False)
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

@st.cache_data(ttl=1800, show_spinner=False)
def scan_top_long(n=5):
    out = []
    for t in AI_UNIVERSE:
        r = get_asymmetry_score(t)
        if r is None or r.get("bad_data"):
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

@st.cache_data(ttl=600, show_spinner=False)
def scan_top_reversal(n=5):
    out = []
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
        rsi = get_rsi_5m(df)
        if rsi > 35:
            continue
        if not is_green_reclaim(df):
            continue
        if sig["score"] < 6.0:
            continue
        # earnings preverjamo zadnje, samo za tiste ki so prestali vse ostale filtre
        if has_earnings_soon(t, 5):
            continue
        sig["rsi"] = round(rsi,1)
        sig["earn"] = False
        out.append((t, sig))
    out.sort(key=lambda x: x[1]["score"], reverse=True)
    return [{"ticker": t, "signal": s} for t, s in out[:n]]

def scan_best_long():
    top = scan_top_long(5)
    if top and top[0]["signal"]["score"] >= 6.5:
        best = top[0]
        log_king_score("LONG", best["ticker"], best["signal"]["score"], f'PS{best["signal"]["ps"]}')
        return best
    return None

def scan_best_reversal():
    top = scan_top_reversal(5)
    if top:
        best = top[0]
        log_king_score("REVERSAL", best["ticker"], best["signal"]["score"])
        return best
    return None

def build_ai_context():
    topL = scan_top_long(5)
    topR = scan_top_reversal(5)
    lines = []
    lines.append("MAKRO TRG: " + str(market["regime"]) + " SPY20d " + str(market["spy_chg"]) + "%")

    lines.append("SEKTORSKI SENTIMENT (Kapitalska rotacija):")
    for sec, dat in sector_sentiment.items():
        lines.append(f"- {sec}: {dat}")

    lines.append("ROTACIJA KAPITALA: " + rotation["pair"] + " | " + rotation["pair_detail"])
    for rw in rotation["rows"][:5]:
        lines.append(f'- {rw["name"]}: 5d {rw["r5"]}% 20d {rw["r20"]}% 60d {rw["r60"]}% vs SPY ({rw["tag"]})')

    lines.append("TOP5 LONG:")
    for x in topL:
        s = x["signal"]
        lines.append("- " + x["ticker"] + " sc " + str(s["score"]) + " P/S " + str(s["ps"]) + " PEG " + str(s["peg"]) + " rast " + str(s["growth"]) + "% vs3y " + str(s.get("vs_med")) + "% FCFy " + str(s.get("fcf_yield")) + "% WS " + str(s["ws_score"]))
    lines.append("TOP5 DIP:")
    for x in topR:
        s = x["signal"]
        lines.append("- " + x["ticker"] + " sc " + str(s["score"]) + " open " + str(s.get("rel_open")) + "% vwap " + str(s.get("rel_vwap")) + "% vol " + str(s.get("vol_ratio")) + "x RSI " + str(s.get("rsi")))
    if not topR:
        lines.append("- NI STROGEGA KANDIDATA (vsi padejo na RSI/vol/momentum/green/earnings)")
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

# Izpis Sektorskega Sentimenta v sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("**Rotacija Sektorjev:**")
for sec, val in sector_sentiment.items():
    col = "#10B981" if "BULL" in val else "#EF4444"
    st.sidebar.markdown(f"<span style='font-size:0.8rem;'>{sec}: <span style='color:{col};'>{val}</span></span>", unsafe_allow_html=True)
st.sidebar.markdown(f"<span style='font-size:0.8rem;color:#FBBF24;'>{rotation['pair']}</span>", unsafe_allow_html=True)

if market["regime"] == "RISK-OFF":
    st.sidebar.warning("RISK-OFF: zmanjsaj velikost pozicije, A+ samo izjemoma.")

with st.spinner("Skeniram 150 delnic..."):
    bestL = scan_best_long()
    bestR = scan_best_reversal()
if bestL is not None:
    l_txt = str(bestL["ticker"]) + " " + str(bestL["signal"]["score"]) + "/10 P/S " + str(bestL["signal"]["ps"]) + " PEG " + str(bestL["signal"]["peg"])
    lv = get_atr_levels(bestL["ticker"], bestL["signal"]["price"])
    if lv:
        l_txt += f' | ATR {lv["atr"]} STOP {lv["stop"]} T1 {lv["t1"]} T2 {lv["t2"]}'
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
st.markdown('<div class="mndy-hero-card"><span style="font-size:1.35rem;font-weight:700;color:#FFFFFF;">MNDY</span> <span class="badge-sector">SaaS</span><div style="font-size:1.7rem;color:#fff;">$' + str(m["price"]) + '</div><div style="color:#F59E0B;">Ocena Asimetrije: 9.4 / 10 | SaaS strah = popust</div></div>', unsafe_allow_html=True)

c = data.get("CRWD", {"price": 325.0, "chg": 0.0, "ps": 17.0})
st.markdown('<div class="ledger-card"><span style="font-size:1.25rem;font-weight:700;color:#FFFFFF;">CRWD</span> <span class="aplus-badge">A+ SETUP</span><div style="font-size:1.55rem;color:#fff;">$' + str(c["price"]) + '</div></div>', unsafe_allow_html=True)

topL = scan_top_long(5)
topR = scan_top_reversal(5)

colL, colR = st.columns(2)
with colL:
    st.markdown("### King TOP5 Long - asimetrija")
    rowsL = []
    for x in topL:
        s = x["signal"]
        lv = get_atr_levels(x["ticker"], s["price"])
        rowsL.append({"Ticker": x["ticker"], "Cena": s["price"], "Score": s["score"], "P/S": s["ps"], "PEG": s["peg"], "vs3y%": s.get("vs_med"), "FCFy%": s.get("fcf_yield"), "WS": s.get("ws_score"), "STOP": lv["stop"] if lv else None, "T1": lv["t1"] if lv else None})
    if rowsL:
        st.dataframe(pd.DataFrame(rowsL).sort_values(by="Score", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("NI STROGEGA KANDIDATA")

with colR:
    st.markdown("### King TOP5 Dip - tik pred obratom")
    rowsR = []
    for x in topR:
        s = x["signal"]
        rowsR.append({"Ticker": x["ticker"], "Score": s["score"], "open%": s.get("rel_open"), "vwap%": s.get("rel_vwap"), "volx": s.get("vol_ratio"), "RSI": s.get("rsi"), "mom%": s.get("momentum")})
    if rowsR:
        st.dataframe(pd.DataFrame(rowsR).sort_values(by="Score", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("NI STROGEGA KANDIDATA - cakaj kot CRWD setup")

col_rot, col_exit = st.columns(2)
with col_rot:
    rot_lines = ""
    for rw in rotation["rows"]:
        colr = "#10B981" if rw["tag"] in ("VODI", "NOV DENAR") else ("#EF4444" if rw["tag"] in ("ZAOSTAJA", "DENAR ODTEKA") else "#94A3B8")
        rot_lines += f'<div style="font-size:0.78rem;color:{colr};">{rw["name"]}: 5d {rw["r5"]:+.1f}% | 20d {rw["r20"]:+.1f}% | 60d {rw["r60"]:+.1f}% vs SPY - {rw["tag"]}</div>'
    st.markdown('<div class="ledger-card"><h4 style="color:#10B981;">Capital Rotation Radar</h4><p style="font-size:0.82rem;color:#94A3B8;">Trg: ' + str(market["regime"]) + '</p><div style="font-size:0.9rem;color:#FBBF24;font-weight:600;">' + rotation["pair"] + '</div><div style="font-size:0.75rem;color:#94A3B8;margin-bottom:8px;">' + rotation["pair_detail"] + '</div>' + rot_lines + '<div style="font-size:0.82rem;color:#6EE7B7;margin-top:10px;">BEST LONG: ' + l_txt + '<br>BEST OBRAT: ' + r_txt + '</div></div>', unsafe_allow_html=True)
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
            prompt_text = "Ti si analitik Value Ledger 2.0 KING.\n" + ctx + "\nCene10: " + str(data) + "\nPRAVILA: Upotevaj sektorski sentiment in rotacijo kapitala (npr. rotacija Semis -> SaaS) za trend denarja. TSM in vsak ticker z bad_data ali FCFy>15% ali P/S fallback 20.0 IGNORIRAJ kot pokvarjen podatek. MNDY je historicni hold zaradi 3y mediane -50% in SaaS strahu, net-cash, FCF 21.8%, PEG 0.62. DIP velja samo ce score>6.0 + RSI<35 + zelena sveca + VWAP reclaim + vol>1.3x + momentum>0 + ni earnings 5d, sicer napisi NI STROGEGA KANDIDATA. ADBE 4.4/10 ni BEST. Izberi 1 BEST LONG + 1 BEST DIP + 1 AVOID. Za vsakega 3 razlogi s stevilkami P/S PEG WS RSI VWAP volumen earnings. Odgovori v slovenscini z ocenami 1-10."
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
