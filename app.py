# --- KING UPGRADE 1+2+3: MARKET REGIME + ATR + EARNINGS + KING SCORE ---
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
    except:
        return {"regime": "NEZNANO", "spy_chg": 0.0, "penalty": 0.0}

market = get_market_regime()
st.sidebar.markdown(f"**Trg:** {market['regime']} (SPY 20d: {market['spy_chg']}%)")
if market["regime"] == "RISK-OFF":
    st.sidebar.warning("RISK-OFF: zmanjšaj velikost pozicije, A+ samo izjemoma.")

def get_atr_stop_target(df, atr_mult_stop=1.5, atr_mult_target=2.5):
    try:
        h = df["High"].astype(float); l = df["Low"].astype(float); c = df["Close"].astype(float)
        tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
        atr = float(tr.rolling(14).mean().iloc[-1])
        last = float(c.iloc[-1])
        return {"atr": round(atr, 2), "stop": round(last - atr * atr_mult_stop, 2), "target": round(last + atr * atr_mult_target, 2)}
    except:
        return {"atr": 0.0, "stop": 0.0, "target": 0.0}

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
    return max(0.0, min(10.0, round(adj, 1)))
