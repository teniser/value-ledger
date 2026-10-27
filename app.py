SAAS_BASKET = ["MNDY","SNOW","HUBS","DDOG","TEAM","NOW","CRM","ADBE","WDAY","ZS","OKTA"]
INFRA_BASKET = ["NVDA","AVGO","AMD","TSM","MU","QCOM","SMCI","ANET","MRVL","KLAC","LRCX"]

@st.cache_data(ttl=1800, show_spinner=False)
def get_trend_metrics(ticker):
    try:
        d = get_history(ticker, "1mo", "1d", False)
        if d.empty or len(d) < 6:
            return {"chg_2d": None, "chg_5d": None, "below_20sma": False}
        c = d["Close"].astype(float)
        last = float(c.iloc[-1])
        chg_2d = (last / float(c.iloc[-3]) - 1) * 100 if len(c) >= 3 else None
        chg_5d = (last / float(c.iloc[-6]) - 1) * 100 if len(c) >= 6 else None
        sma20 = float(c.tail(20).mean()) if len(c) >= 20 else last
        return {"chg_2d": round(chg_2d,2) if chg_2d is not None else None,
                "chg_5d": round(chg_5d,2) if chg_5d is not None else None,
                "below_20sma": last < sma20}
    except Exception:
        return {"chg_2d": None, "chg_5d": None, "below_20sma": False}

@st.cache_data(ttl=1800, show_spinner=False)
def get_sector_wind():
    def basket_5d(basket):
        vals = []
        for t in basket:
            m = get_trend_metrics(t)
            if m["chg_5d"] is not None:
                vals.append(m["chg_5d"])
        return sum(vals)/len(vals) if vals else 0.0
    saas = basket_5d(SAAS_BASKET)
    infra = basket_5d(INFRA_BASKET)
    return {"saas_5d": round(saas,2), "infra_5d": round(infra,2), "rotation": round(infra - saas,2)}
