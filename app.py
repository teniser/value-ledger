import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, time
import pandas as pd
import plotly.graph_objects as go
import pytz
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="The Value Ledger 2.0 · Terminal", page_icon="💎", layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
html, body, [class*="css"], .stApp { background-color:#06070B !important; font-family:'Plus Jakarta Sans',sans-serif !important; color:#E2E8F0 !important; }
section[data-testid="stSidebar"] { background-color:#0A0D14 !important; border-right:1px solid rgba(255,255,255,0.05) !important; }
.ledger-card { background:rgba(13,17,28,0.7); border:1px solid rgba(255,255,255,0.06); border-radius:16px; padding:22px 26px; margin-bottom:20px; }
.mndy-hero-card { background:linear-gradient(145deg,rgba(20,17,10,0.8),rgba(10,9,6,0.9)); border:1.5px solid rgba(245,158,11,0.6); border-radius:18px; padding:24px 26px; margin-bottom:22px; }
.badge-sector { font-size:.7rem; padding:3px 8px; border-radius:6px; background:rgba(255,255,255,.04); color:#94A3B8; text-transform:uppercase; }
.aplus-badge { display:inline-flex; border:1.2px solid #F59E0B; color:#FBBF24; font-size:.76rem; padding:3px 12px; border-radius:9999px; }
.metrics-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:12px; margin:16px 0; padding:14px 18px; background:rgba(0,0,0,.25); border-radius:12px; }
.metric-label { color:#94A3B8; font-size:.7rem; text-transform:uppercase; font-family:'Space Grotesk',sans-serif; }
.metric-value { font-family:'JetBrains Mono',monospace; font-size:1rem; color:#F8FAFC; }
div.stButton > button { background:linear-gradient(135deg,#F59E0B,#D97706) !important; color:#0A0D14 !important; font-weight:600 !important; border:none !important; border-radius:10px !important; padding:12px 24px !important; }
</style>""", unsafe_allow_html=True)

st.sidebar.markdown("### 🔑 Google AI nastavitev")
api_key = st.sidebar.text_input("Gemini API ključ:", type="password")

NY_TZ = pytz.timezone("America/New_York")
LJ_TZ = pytz.timezone("Europe/Ljubljana")

# --- UNIVERZUM 9 sektorjev ---
SECTORS = {
 "SaaS/Software": ["MNDY","NOW","ADBE","SNOW","HUBS","DDOG","TEAM","CRM","WDAY","ADSK","VEEV","DOCU","ZM","TWLO","SHOP","WIX","GTLB","CFLT","IOT","INTA","APP","PATH","DUOL","INTU","CSCO","IBM","ACN","WIX","FSLY","GDDY"],
 "Semiconductors/Hardware": ["NVDA","AVGO","AMD","TSM","MU","QCOM","ARM","SMCI","ANET","MRVL","KLAC","LRCX","AMAT","ASML","ON","NXPI","TXN","ADI","MCHP","INTC","STX","WDC","NTAP","DELL","HPQ","HPE","CLS","JBL","TER","ENTG","LITE","COHR","CIEN","ANSS","CDNS","SNPS","GFS","MPWR"],
 "Cloud/Cyber": ["CRWD","PANW","ZS","OKTA","FTNT","S","CYBR","TENB","NET","MDB","ESTC"],
 "AI/Data": ["MSFT","GOOGL","META","ORCL","AI","PLTR","SNOW","DDOG","ANET","MRVL"],
 "Fintech": ["SQ","PYPL","AFRM","SOFI","COIN","HOOD","SCHW","BLK","V","MA","FICO"],
 "Ecom/Consumer": ["AMZN","NFLX","SHOP","ABNB","UBER","DASH","MELI","SE","SPOT","RDDT","RBLX","TTD","COST","WMT","TGT","HD","LOW","LULU","ELF","CAVA","CELH","NKE"],
 "Industrial/Energy": ["GE","CAT","DE","ETN","PWR","CEG","VST","NEE","XOM","CVX","COP","SLB","FSLR","ENPH"],
 "Banks": ["JPM","GS","MS","BAC"],
 "Auto/Gaming": ["TSLA","RIVN","LCID","RACE","DKNG","U","RBLX"],
}
AI_UNIVERSE = list(dict.fromkeys([t for v in SECTORS.values() for t in v]))
SAAS_BASKET = SECTORS["SaaS/Software"]
INFRA_BASKET = SECTORS["Semiconductors/Hardware"]

TICKERS_CONFIG = {
 "MNDY": {"name":"monday.com","sector":"SaaS / Work OS","category":"Na opazovanju","sentiment":9.1,"makro":8.5,"temelji":9.2,"podcenjenost":9.5},
 "CRWD": {"name":"CrowdStrike","sector":"Kibernetska varnost","category":"Na opazovanju","sentiment":9.5,"makro":8.5,"temelji":9.5,"podcenjenost":6.5},
 "SNOW": {"name":"Snowflake","sector":"AI podatki","category":"Na opazovanju","sentiment":8.2,"makro":8.3,"temelji":8.7,"podcenjenost":6.8},
 "HUBS": {"name":"HubSpot","sector":"CRM","category":"Na opazovanju","sentiment":7.7,"makro":7.0,"temelji":8.5,"podcenjenost":8.0},
 "DELL": {"name":"Dell","sector":"AI HW","category":"Na opazovanju","sentiment":8.0,"makro":8.2,"temelji":8.4,"podcenjenost":8.5},
 "DDOG": {"name":"Datadog","sector":"Cloud","category":"Na opazovanju","sentiment":7.9,"makro":8.0,"temelji":9.1,"podcenjenost":5.8},
 "TEAM": {"name":"Atlassian","sector":"Dev","category":"Na opazovanju","sentiment":7.0,"makro":7.5,"temelji":8.8,"podcenjenost":5.5},
 "NOW": {"name":"ServiceNow","sector":"Enterprise","category":"Na opazovanju","sentiment":6.8,"makro":8.5,"temelji":9.8,"podcenjenost":4.5},
 "PANW": {"name":"Palo Alto","sector":"Security","category":"Na opazovanju","sentiment":6.5,"makro":8.5,"temelji":9.0,"podcenjenost":3.8},
 "PLTR": {"name":"Palantir","sector":"AI platforma","category":"Na opazovanju","sentiment":5.2,"makro":9.4,"temelji":9.6,"podcenjenost":2.1},
}

def as_float(x):
    try:
        if x is None or pd.isna(x): return None
        v=float(x); return v if math.isfinite(v) else None
    except: return None

def fmt(v,suf="",d=2):
    return "ni podatka" if v is None else f"{v:.{d}f}{suf}"

def find_row(df,names):
    if not isinstance(df,pd.DataFrame) or df.empty: return None
    low={str(i).strip().lower():i for i in df.index}
    for n in names:
        if n.strip().lower() in low: return df.loc[low[n.strip().lower()]]
    for i in df.index:
        al=str(i).lower()
        if any(n.lower() in al for n in names): return df.loc[i]
    return None

@st.cache_data(ttl=900, show_spinner=False)
def get_ticker_info(t):
    try:
        r=yf.Ticker(t).info; return r if isinstance(r,dict) else {}
    except: return {}

@st.cache_data(ttl=300, show_spinner=False)
def get_history(t,period="5d",interval="5m",prepost=False):
    try:
        f=yf.Ticker(t).history(period=period,interval=interval,auto_adjust=False,prepost=prepost)
        if f is None or f.empty: return pd.DataFrame()
        return f.dropna(subset=["Open","High","Low","Close","Volume"])
    except: return pd.DataFrame()

def get_market_regime():
    try:
        f=get_history("SPY","6mo","1d",False)
        if f.empty or len(f)<60: return {"regime":"NEZNANO","spy_20d_pct":None,"penalty":0.0}
        c=f["Close"].astype(float); last=float(c.iloc[-1]); sma=float(c.rolling(50).mean().iloc[-1]); ch=(last/float(c.iloc[-21])-1)*100
        if last>sma and ch>-3: return {"regime":"RISK-ON","spy_20d_pct":round(ch,2),"penalty":0.0}
        if last<sma and ch<-3: return {"regime":"RISK-OFF","spy_20d_pct":round(ch,2),"penalty":0.8}
        return {"regime":"NEVTRALNO","spy_20d_pct":round(ch,2),"penalty":0.3}
    except: return {"regime":"NEZNANO","spy_20d_pct":None,"penalty":0.0}
market=get_market_regime()

@st.cache_data(ttl=1800, show_spinner=False)
def get_trend_metrics(t):
    try:
        d=get_history(t,"1mo","1d",False)
        if d.empty or len(d)<6: return {"chg_2d":None,"chg_5d":None,"below_20sma":False}
        c=d["Close"].astype(float); last=float(c.iloc[-1])
        c2=(last/float(c.iloc[-3])-1)*100 if len(c)>=3 else None
        c5=(last/float(c.iloc[-6])-1)*100 if len(c)>=6 else None
        sma=float(c.tail(20).mean()) if len(c)>=20 else last
        return {"chg_2d":round(c2,2) if c2 is not None else None,"chg_5d":round(c5,2) if c5 is not None else None,"below_20sma":last<sma}
    except: return {"chg_2d":None,"chg_5d":None,"below_20sma":False}

@st.cache_data(ttl=1800, show_spinner=False)
def get_sector_wind():
    def avg(b):
        v=[get_trend_metrics(t)["chg_5d"] for t in b]; v=[x for x in v if x is not None]
        return sum(v)/len(v) if v else 0.0
    saas=avg(SAAS_BASKET); infra=avg(INFRA_BASKET)
    sec={}
    for s, tickers in SECTORS.items():
        vals=[get_trend_metrics(t)["chg_5d"] for t in tickers]; vals=[x for x in vals if x is not None]
        sec[s]=round(sum(vals)/len(vals),2) if vals else 0.0
    return {"saas_5d":round(saas,2),"infra_5d":round(infra,2),"rotation":round(infra-saas,2),"sectors":sec}
wind=get_sector_wind()

def get_atr(t):
    try:
        d=get_history(t,"1mo","1d",False)
        if d.empty or len(d)<15: return {"atr":None,"stop":None,"target":None}
        h=d["High"].astype(float); l=d["Low"].astype(float); c=d["Close"].astype(float)
        tr=pd.concat([h-l,(h-c.shift(1)).abs(),(l-c.shift(1)).abs()],axis=1).max(axis=1)
        atr=float(tr.rolling(14).mean().iloc[-1]); last=float(c.iloc[-1])
        return {"atr":round(atr,2),"stop":round(last-atr*1.5,2),"target":round(last+atr*2.5,2)}
    except: return {"atr":None,"stop":None,"target":None}

@st.cache_data(ttl=86400, show_spinner=False)
def get_historical_ps_metrics(t):
    empty={"historical_ps_median":None,"current_vs_median_pct":None,"samples":0,"method":"ni dovolj podatkov"}
    try:
        s=yf.Ticker(t); inc=s.quarterly_income_stmt
        rev=find_row(inc,["Total Revenue"])
        if rev is None: return empty
        revenue=pd.to_numeric(rev,errors="coerce").dropna().sort_index()
        if len(revenue)<4: return empty
        info=get_ticker_info(t); price=as_float(info.get("currentPrice") or info.get("regularMarketPrice"))
        mc=as_float(info.get("marketCap")); tr=as_float(info.get("totalRevenue"))
        if not price or not mc or not tr: return empty
        shares=mc/price
        prices=s.history(period="5y",interval="1d",auto_adjust=False)
        if prices is None or prices.empty: return empty
        cutoff=pd.Timestamp.now().normalize()-pd.Timedelta(days=365*3)
        samps=[]
        for d in revenue.index:
            d=pd.Timestamp(d).tz_localize(None) if pd.Timestamp(d).tzinfo else pd.Timestamp(d)
            if d<cutoff: continue
            ttm=as_float(revenue.loc[:pd.Timestamp(revenue.index[revenue.index<=d.tz_localize(None) if hasattr(d,'tz_localize') else d]).tail(4).sum()] if False else None)
            # enostavno TTM iz zadnjih 4
            ttm=float(revenue.loc[:d].tail(4).sum()) if len(revenue.loc[:d])>=1 else 0
            if ttm<=0: continue
            px=prices.loc[prices.index<=d.tz_localize(prices.index.tz) if prices.index.tz else d]
            if px.empty: continue
            close=as_float(px["Close"].iloc[-1])
            if not close: continue
            est=close*shares/ttm
            if 0<est<100: samps.append(est)
        if len(samps)<6: return {**empty,"samples":len(samps),"method":"premalo vzorcev"}
        med=float(pd.Series(samps).median()); cur=mc/tr
        return {"historical_ps_median":round(med,2),"current_vs_median_pct":round((cur/med-1)*100,1),"samples":len(samps),"method":"ocena; delnice konst."}
    except: return empty

def get_wallstreet(info,price):
    rec=as_float(info.get("recommendationMean")); num=as_float(info.get("numberOfAnalystOpinions")); tgt=as_float(info.get("targetMeanPrice"))
    up=(tgt/price-1)*100 if tgt and price else None
    sc=None
    if rec is not None and 1<=rec<=5: sc=max(0,min(10,10-(rec-1)*2.5))
    return {"ws_score":round(sc,1) if sc is not None else None,"rec":rec,"num":int(num) if num else None,"upside":round(up,1) if up is not None else None}

def score_low(v,e,g,f,p):
    if v<=e: return 10.0
    if v<=g: return 8.0
    if v<=f: return 6.0
    if v<=p: return 4.0
    return 2.0
def score_high(v,p,f,g,e):
    if v>=e: return 10.0
    if v>=g: return 8.0
    if v>=f: return 6.0
    if v>=p: return 4.0
    return 2.0

@st.cache_data(ttl=1800, show_spinner=False)
def analyze_long_ticker(t):
    info=get_ticker_info(t)
    mc=as_float(info.get("marketCap")); price=as_float(info.get("currentPrice") or info.get("regularMarketPrice"))
    avgv=as_float(info.get("averageVolume")); dv=price*avgv if price and avgv else None
    if not mc or mc<2_000_000_000 or not dv or dv<20_000_000: return None
    rev=as_float(info.get("totalRevenue")); gr=as_float(info.get("revenueGrowth")); peg=as_float(info.get("pegRatio"))
    cash=as_float(info.get("totalCash")); debt=as_float(info.get("totalDebt")); fcf=as_float(info.get("freeCashflow"))
    if gr is not None and gr>1: gr/=100.0
    if not rev or rev<=0 or not price: return None
    ps=mc/rev
    if not math.isfinite(ps) or ps<1 or ps>100: return None
    if peg is None or peg<=0 or peg>3.0: return None
    if gr is None or not math.isfinite(gr) or gr<0.12 or gr>2.0: return None
    if cash is None or debt is None: return None
    nc=cash-debt
    if nc<-0.10*mc: return None
    fcfm=fcf/rev*100 if fcf is not None else None
    rawy=fcf/mc*100 if fcf is not None else None
    susp=rawy is not None and (rawy>25 or rawy<-25)
    fcfy=None if susp else rawy
    hist=get_historical_ps_metrics(t); ws=get_wallstreet(info,price)
    comps=[(score_low(ps,3,6,10,15),0.18),(score_low(peg,0.8,1.2,1.8,2.5),0.13),(score_high(gr*100,10,15,25,40),0.14),(score_high(nc/mc*100,-10,0,10,25),0.12)]
    if fcfm is not None: comps.append((score_high(fcfm,0,5,15,25),0.10))
    if fcfy is not None: comps.append((score_high(fcfy,-5,0,3,7),0.10))
    if hist["current_vs_median_pct"] is not None: comps.append((score_high(-hist["current_vs_median_pct"],-30,-10,10,30),0.13))
    if ws["ws_score"] is not None: comps.append((ws["ws_score"],0.10 if (ws["num"] or 0)>=5 else 0.04))
    tw=sum(w for _,w in comps); raw=sum(v*w for v,w in comps)/tw if tw else 0
    tr=get_trend_metrics(t); pen=0.0
    if tr["chg_2d"] is not None and tr["chg_2d"]<-3.0: pen+=1.0
    if tr["below_20sma"] and (tr["chg_5d"] or 0)<0: pen+=0.5
    if wind["rotation"]>3.0:
        if t in SAAS_BASKET: pen+=1.0
        elif t in INFRA_BASKET: pen-=0.5
    # sektorski veter vseh sektorjev
    for s, tickers in SECTORS.items():
        if t in tickers:
            sm=wind["sectors"].get(s,0)
            if sm<-2.0: pen+=0.5
            elif sm>4.0: pen-=0.3
    raw-=pen
    final=max(0,min(10,raw-market["penalty"]))
    atr=get_atr(t)
    return {"ticker":t,"score":round(final,1),"price":round(price,2),"ps":round(ps,2),"peg":round(peg,2),"growth_pct":round(gr*100,1),"net_cash":nc,"fcf_margin_pct":round(fcfm,1) if fcfm is not None else None,"fcf_yield_pct":round(fcfy,2) if fcfy is not None else None,"fcf_suspect":susp,"historical_ps_median":hist["historical_ps_median"],"current_vs_historical_ps_pct":hist["current_vs_median_pct"],"ws_score":ws["ws_score"],"ws_upside":ws["upside"],"chg_2d":tr["chg_2d"],"chg_5d":tr["chg_5d"],"stop":atr["stop"],"target":atr["target"],"coverage":round(tw/0.90*100)}

@st.cache_data(ttl=1800, show_spinner=False)
def scan_top_long(uni,count=5):
    res=[]
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs={ex.submit(analyze_long_ticker,t):t for t in uni}
        for f in as_completed(futs):
            try:
                r=f.result()
                if r and r["score"]>=5.5: res.append(r)
            except: continue
    res.sort(key=lambda x:(x["score"],x["coverage"]),reverse=True)
    if "king_log" not in st.session_state: st.session_state["king_log"]=[]
    st.session_state["king_log"].append({"time":datetime.now(LJ_TZ).strftime("%d.%m %H:%M"),"best":res[0]["ticker"] if res else None,"score":res[0]["score"] if res else None})
    return res[:count]

def calc_rsi(c,p=14):
    s=pd.Series(c,dtype=float)
    if len(s)<p+1: return None
    d=s.diff(); g=d.clip(lower=0).rolling(p).mean(); l=(-d.clip(upper=0)).rolling(p).mean()
    r=100-100/(1+g/l.replace(0,float("nan")))
    return as_float(r.iloc[-1])

def earn_soon(t,days=5):
    try:
        e=yf.Ticker(t).get_earnings_dates(limit=8)
        if e is None or e.empty: return None
        now=pd.Timestamp.now(tz="UTC")
        for d in e.index:
            ed=pd.Timestamp(d)
            if ed.tzinfo is None: ed=ed.tz_localize("UTC")
            if 0<=(ed-now).total_seconds()/86400<=days: return True
        return False
    except: return None

def get_intraday_signal(t):
    f=get_history(t,"5d","5m",True)
    if f.empty: return None
    try:
        idx=pd.DatetimeIndex(f.index)
        if idx.tz is None: idx=idx.tz_localize("UTC")
        f=f.copy(); f.index=idx.tz_convert(NY_TZ)
        today=datetime.now(NY_TZ).date()
        td=f[f.index.date==today]; ed=f[f.index.date<today]
        if td.empty: return None
        pc=None
        if not ed.empty:
            pr=ed[(ed.index.time>=time(9,30))&(ed.index.time<time(16,0))]
            if not pr.empty: pc=as_float(pr["Close"].iloc[-1])
        if pc is None:
            d=get_history(t,"10d","1d",False)
            if len(d)>=2: pc=as_float(d["Close"].iloc[-2])
        if not pc: return None
        pre=td[(td.index.time>=time(4,0))&(td.index.time<time(9,30))]
        reg=td[(td.index.time>=time(9,30))&(td.index.time<time(16,0))]
        is_pre=not pre.empty and reg.empty
        act=pre if is_pre else reg
        if act.empty: return None
        cl=act["Close"].astype(float); vol=act["Volume"].fillna(0).astype(float); last=float(cl.iloc[-1])
        tv=float(vol.sum()); vwap=float((cl*vol).sum()/tv) if tv>0 else last
        vd=(last/vwap-1)*100; ch=(last/pc-1)*100; mo=(last/float(cl.iloc[-2])-1)*100 if len(cl)>1 else 0.0
        lo=as_float(act["Open"].iloc[-1]); green=lo is not None and last>lo; rsi=calc_rsi(cl)
        vr=None
        if len(vol)>=3:
            med=as_float(vol.iloc[:-1].tail(20).median()); lv=as_float(vol.iloc[-1])
            vr=lv/med if med else None
        sc=0.0
        sc+=2.0 if rsi is not None and rsi<35 else (1.0 if rsi is not None and rsi<45 else 0.0)
        sc+=2.0 if vd>=0 else (1.0 if vd>=-2 else 0.0)
        sc+=2.0 if mo>0 else 0.0
        sc+=1.0 if green else 0.0
        sc+=2.0 if vr is not None and vr>=1.3 else 0.0
        sc+=1.0 if -8<=ch<=2.5 else 0.0
        if market["regime"]=="RISK-OFF": sc-=market["penalty"]
        return {"ticker":t,"score":round(max(0,min(10,sc)),1),"price":round(last,2),"change_from_previous_pct":round(ch,2),"vwap_distance_pct":round(vd,2),"momentum_pct":round(mo,2),"volume_ratio":round(vr,2) if vr is not None else None,"rsi":round(rsi,1) if rsi is not None else None,"green_candle":green,"premarket":is_pre}
    except: return None

@st.cache_data(ttl=180, show_spinner=False)
def scan_top_reversal(uni,count=5):
    strict=[]; watch=[]
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs={ex.submit(get_intraday_signal,t):t for t in uni}
        for f in as_completed(futs):
            t=futs[f]
            try: s=f.result()
            except: continue
            if not s: continue
            e=earn_soon(t,5)
            if s["premarket"]:
                if -5<=s["change_from_previous_pct"]<=2.5 and s["score"]>=4:
                    s["status"]="PREMARKET WATCH · ni potrjen A+"; s["earn"]=e; watch.append(s)
                continue
            if e is not False: continue
            if not (-8<=s["change_from_previous_pct"]<=-1): continue
            if s["rsi"] is None or s["rsi"]>=35: continue
            if s["vwap_distance_pct"]<-2: continue
            if s["volume_ratio"] is None or s["volume_ratio"]<=1.3: continue
            if s["momentum_pct"]<=0 or not s["green_candle"]: continue
            if s["score"]<=6.0: continue
            s["status"]="STROGI DIP SETUP"; s["earn"]=False; strict.append(s)
    strict.sort(key=lambda x:x["score"],reverse=True); watch.sort(key=lambda x:x["score"],reverse=True)
    return {"strict":strict[:count],"watch":watch[:count]}

if st.button("⟳ Osveži podatke"):
    st.cache_data.clear(); st.rerun()

with st.spinner("Skeniram univerzum..."):
    longs=scan_top_long(tuple(AI_UNIVERSE),5)
    revs=scan_top_reversal(tuple(AI_UNIVERSE),5)

dash={}
for t in TICKERS_CONFIG:
    i=get_ticker_info(t); p=as_float(i.get("currentPrice") or i.get("regularMarketPrice")); pr=as_float(i.get("regularMarketPreviousClose"))
    ch=(p/pr-1)*100 if p and pr else None; mc=as_float(i.get("marketCap")); rv=as_float(i.get("totalRevenue")); ps=mc/rv if mc and rv else None
    dash[t]={"price":round(p,2) if p else None,"change":round(ch,2) if ch is not None else None,"ps":round(ps,2) if ps else None}

def build_ai_context():
    L=[f"Režim: {market['regime']} SPY20d {fmt(market['spy_20d_pct'],'%')} SaaS5d {wind['saas_5d']}% Infra5d {wind['infra_5d']}% rotacija {wind['rotation']}pp.","Sektorji: "+"; ".join([f"{k} {v}%" for k,v in wind['sectors'].items()]),"Samo številke spodaj. Manjkajoče ne izmišljaj. Univerzum: samo seznam, ne cel trg.","TOP LONG:"]
    if not longs: L.append("Ni kandidata.")
    for r in longs: L.append(f"{r['ticker']}: {r['score']}/10 P/S {r['ps']} PEG {r['peg']} rast {r['growth_pct']}% vs3y {fmt(r['current_vs_historical_ps_pct'],'%')} FCFy {fmt(r['fcf_yield_pct'],'%')} WS {fmt(r['ws_score'])} upside {fmt(r['ws_upside'],'%')} 2d {fmt(r['chg_2d'],'%')} 5d {fmt(r['chg_5d'],'%')} stop {r['stop']} target {r['target']}")
    L.append("STROGI OBRATI:")
    if not revs["strict"]: L.append("Ni kandidata.")
    for s in revs["strict"]: L.append(f"{s['ticker']}: {s['score']}/10 ch {s['change_from_previous_pct']}% RSI {s['rsi']} VWAP {s['vwap_distance_pct']}% vol {fmt(s['volume_ratio'],'x')} mom {s['momentum_pct']}% zelena {s['green_candle']}")
    L.append("WATCH (ni A+):")
    if not revs["watch"]: L.append("Ni watch.")
    for s in revs["watch"]: L.append(f"{s['ticker']}: {s['score']}/10 ch {s['change_from_previous_pct']}% RSI {s['rsi']}")
    return "\n".join(L)

lj_time=datetime.now(LJ_TZ).strftime("%d.%m.%Y · %H:%M %Z")
st.markdown(f"""<div style="display:flex;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,.06);padding-bottom:14px;margin-bottom:20px;"><div><h1 style="margin:0;font-size:1.8rem;"><span style="color:#F59E0B;">THE VALUE LEDGER</span> <span style="color:#60A5FA;">2.0</span></h1><p style="color:#94A3B8;font-size:.82rem;">Kvantitativni Terminal {lj_time}</p></div><div style="text-align:right;color:#94A3B8;font-size:.75rem;">Trg: {market['regime']} · SaaS {wind['saas_5d']}% · Infra {wind['infra_5d']}%</div></div>""",unsafe_allow_html=True)

st.sidebar.markdown("### 🌙 Pozicija")
held=st.sidebar.selectbox("Katera delnica je v poziciji?",list(TICKERS_CONFIG),index=list(TICKERS_CONFIG).index("CRWD"))

m=dash.get("MNDY",{})
st.markdown(f"""<div class="mndy-hero-card"><span style="font-size:1.35rem;font-weight:700;color:#fff;">MNDY</span> <span class="badge-sector">SaaS</span><div style="font-size:1.7rem;color:#fff;">{fmt(m.get('price'),'$')}</div><div style="color:#F59E0B;">Brez ročne prednosti · določi skener</div></div>""",unsafe_allow_html=True)
c=dash.get("CRWD",{})
st.markdown(f"""<div class="ledger-card"><span style="font-size:1.25rem;font-weight:700;color:#fff;">CRWD</span> <span class="aplus-badge">REFERENČNI PRIMER</span><div style="font-size:1.55rem;color:#fff;">{fmt(c.get('price'),'$')}</div></div>""",unsafe_allow_html=True)

st.markdown("### 🏆 TOP 5 LONG · asimetrija")
if longs:
    st.dataframe(pd.DataFrame([{"Ticker":r["ticker"],"Ocena":r["score"],"Cena":r["price"],"P/S":r["ps"],"PEG":r["peg"],"vs3y %":r["current_vs_historical_ps_pct"],"FCFy %":r["fcf_yield_pct"],"WS":r["ws_score"],"2d %":r["chg_2d"],"5d %":r["chg_5d"],"Stop":r["stop"],"Target":r["target"]} for r in longs]),use_container_width=True,hide_index=True)
    st.markdown(f"Trenutni #1: **{longs[0]['ticker']} · {longs[0]['score']}/10** — vrstni red filtra, ne priporočilo.")
else: st.info("NI STROGEGA KANDIDATA")

st.markdown("### 🔄 TOP 5 REVERSAL DIP")
if revs["strict"]:
    st.dataframe(pd.DataFrame([{"Ticker":s["ticker"],"Ocena":s["score"],"ch %":s["change_from_previous_pct"],"RSI":s["rsi"],"VWAP %":s["vwap_distance_pct"],"Vol":s["volume_ratio"],"Mom %":s["momentum_pct"]} for s in revs["strict"]]),use_container_width=True,hide_index=True)
else: st.info("NI STROGEGA KANDIDATA")
if revs["watch"]:
    st.markdown("#### Premarket watch · ni A+")
    st.dataframe(pd.DataFrame([{"Ticker":s["ticker"],"Ocena":s["score"],"ch %":s["change_from_previous_pct"],"RSI":s["rsi"]} for s in revs["watch"]]),use_container_width=True,hide_index=True)

col1,col2=st.columns([1,1.25])
with col1:
    st.markdown("### 🕸️ 4 stebri")
    sel=st.multiselect("Izberi:",list(TICKERS_CONFIG),default=["MNDY","CRWD","NOW","PLTR"])
    cats=["Sentiment","Makro","Temelji","Podcenjenost"]; fig=go.Figure()
    cols={"MNDY":"#F59E0B","CRWD":"#10B981","SNOW":"#60A5FA","NOW":"#8B5CF6","PLTR":"#EF4444"}
    for t in sel:
        cfg=TICKERS_CONFIG[t]; vals=[cfg["sentiment"],cfg["makro"],cfg["temelji"],cfg["podcenjenost"]]
        fig.add_trace(go.Scatterpolar(r=vals+[vals[0]],theta=cats+[cats[0]],name=t,line=dict(color=cols.get(t,"#fff"),width=2),fill="toself"))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,10])),paper_bgcolor="rgba(0,0,0,0)",height=300,margin=dict(l=20,r=20,t=10,b=10))
    st.plotly_chart(fig,use_container_width=True)
with col2:
    st.markdown("### 📊 Tabela")
    lk={r["ticker"]:r for r in longs}; rows=[]
    for t,cfg in TICKERS_CONFIG.items():
        lv=dash.get(t,{}); mm=lk.get(t,{})
        rows.append({"Ticker":t,"Cena":lv.get("price"),"P/S":mm.get("ps",lv.get("ps")),"Ocena":mm.get("score"),"Status":cfg["category"]})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

c1,c2=st.columns(2)
with c1:
    st.markdown("### 🔄 Rotation Radar")
    st.write(f"BEST LONG: **{longs[0]['ticker'] if longs else 'NI STROGEGA KANDIDATA'}**")
    st.write(f"BEST OBRAT: **{revs['strict'][0]['ticker'] if revs['strict'] else 'NI STROGEGA KANDIDATA'}**")
    if revs["watch"]: st.write(f"WATCH: **{revs['watch'][0]['ticker']}**")
with c2:
    st.markdown("### 🎯 MNDY cilji")
    st.write("1. $220–$240 · 2. $280–$310 · 3. nad $340 — statični cilji iz konfiguracije.")

st.markdown("---")
st.markdown("### 🤖 AI analitik")
if st.button("POŽENI AVTONOMNI AI PREGLED TRGA"):
    if not api_key.strip(): st.error("Vnesi ključ.")
    else:
        ctx=build_ai_context()
        prompt=f"Analiziraj samo kontekst. Ne dodajaj cen/donosov/novic ki niso zapisane. Če manjka napiši ni podatka. Ne trdi cel trg, samo seznam. Ocene so vrstni red, ne priporočilo.\n{ctx}\nSlovensko: 1. TOP LONG zakaj prvi, 2. loči strogi obrat in watch, 3. samo številke iz konteksta, 4. če ni kandidata povej."
        pay={"contents":[{"parts":[{"text":prompt}]}]}; last=""; rep=None
        try:
            mr=requests.get("https://generativelanguage.googleapis.com/v1beta/models",params={"key":api_key.strip()},timeout=15); mr.raise_for_status()
            mns=[m["name"] for m in mr.json().get("models",[]) if "generateContent" in m.get("supportedGenerationMethods",[])]
        except Exception as e: mns=[]; last=str(e)
        if not mns: st.error("Ni modelov. "+last)
        else:
            with st.spinner("Analiziram..."):
                for mn in mns:
                    try:
                        r=requests.post(f"https://generativelanguage.googleapis.com/v1beta/{mn}:generateContent",params={"key":api_key.strip()},json=pay,timeout=30)
                        if r.status_code==200:
                            rep=r.json()["candidates"][0]["content"]["parts"][0]["text"]; st.session_state["ai_report"]=rep; st.session_state["ai_model"]=mn.split("/")[-1]; break
                        else: last=f"{mn}: {r.status_code} {r.text[:250]}"
                    except Exception as e: last=str(e)
            if rep is None: st.error("Napaka: "+last)
if "ai_report" in st.session_state:
    st.write(f"Model: {st.session_state.get('ai_model','Gemini')}")
    st.write(st.session_state["ai_report"])

with st.expander("Metodologija"):
    st.write("Long: P/S, PEG, rast, bilanca, FCF, zgodovinski P/S, WS + 2d/5d trend kazen + SaaS/infra rotacija + sektorski veter. Reversal: -8 do -1%, RSI<35, VWAP>=-2%, vol>1.3x, momentum>0, zelena sveča, earnings filter. Premarket je samo watch. Ni finančni nasvet.")
