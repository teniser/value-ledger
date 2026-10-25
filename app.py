import html
import math
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st
import yfinance as yf


# ============================================================
# PAGE CONFIG + TEMNI VIDEZ
# ============================================================

st.set_page_config(
    page_title="The Value Ledger 2.0 Terminal",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

    html, body, [class*="css"], .stApp {
        background-color: #06070B !important;
        color: #E2E8F0 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #0A0D14 !important;
        border-right: 1px solid rgba(255,255,255,0.06);
    }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
        font-family: 'Space Grotesk', sans-serif !important;
        color: #E2E8F0 !important;
    }
    [data-testid="stCaptionContainer"] {
        color: #94A3B8 !important;
    }
    .ledger-card {
        background: linear-gradient(145deg, #0D111C, #090B12);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 20px 24px;
        margin: 8px 0 18px 0;
    }
    .hero-long {
        background: linear-gradient(145deg, rgba(48,34,10,0.72), rgba(13,17,28,0.96));
        border: 1px solid rgba(245,158,11,0.58);
        border-radius: 18px;
        padding: 20px 24px;
        min-height: 205px;
    }
    .hero-reversal {
        background: linear-gradient(145deg, rgba(9,43,39,0.75), rgba(13,17,28,0.96));
        border: 1px solid rgba(16,185,129,0.48);
        border-radius: 18px;
        padding: 20px 24px;
        min-height: 205px;
    }
    div.stButton > button {
        background: linear-gradient(135deg,#F59E0B 0%,#D97706 100%) !important;
        color:#0A0D14 !important;
        font-weight:700 !important;
        border:none !important;
        border-radius:10px !important;
        padding:10px 18px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

NY_TZ = ZoneInfo("America/New_York")
LJ_TZ = ZoneInfo("Europe/Ljubljana")


# ============================================================
# UNIVERZUM: DEDUPLICIRAN SEZNAM, NAJVEČ 150 TICKERJEV
# ============================================================

TICKER_CANDIDATES = [
    # SaaS, programska oprema in cloud
    "MNDY", "CRWD", "SNOW", "HUBS", "DDOG", "TEAM", "NOW", "PANW",
    "PLTR", "CRM", "ADBE", "SHOP", "NET", "ZS", "OKTA", "MDB",
    "ESTC", "PATH", "WDAY", "CFLT", "DOCN", "GTLB", "TOST", "BILL",
    "ASAN", "IOT", "FSLY", "DT", "BSY", "PCOR", "NCNO", "ZM",
    "DOCU", "TWLO", "PD", "DBX", "SMAR", "UPWK", "SPT", "APPN",
    "PEGA", "FROG", "RNG", "VEEV", "TYL", "PTC", "ADSK", "TRMB",

    # Večja tehnologija in internet
    "AAPL", "MSFT", "META", "AMZN", "GOOGL", "NFLX", "TSLA",
    "UBER", "ABNB", "DASH", "SPOT", "RBLX", "TTD", "ROKU",
    "PINS", "SNAP", "MTCH", "DKNG", "LYFT", "EBAY",

    # Polprevodniki, oprema in strojna oprema
    "NVDA", "AVGO", "AMD", "TSM", "MU", "QCOM", "ARM", "SMCI",
    "ANET", "MRVL", "SNPS", "CDNS", "ANSS", "ALAB", "LITE",
    "COHR", "VRT", "NTNX", "PSTG", "STX", "WDC", "TXN", "ADI",
    "NXPI", "MCHP", "ON", "INTC", "ASML", "AMAT", "LRCX",
    "KLAC", "DELL", "CSCO", "HPE", "HPQ", "GLW", "TER", "KEYS",

    # Kibernetska varnost
    "CHKP", "CYBR", "TENB", "VRNS", "QLYS", "FTNT", "AKAM",
    "VRSN", "GEN", "S",

    # Finance, plačila in fintech
    "COIN", "HOOD", "XYZ", "PYPL", "SOFI", "AFRM", "MELI",
    "SE", "NU", "V", "MA", "GLBE", "JPM", "GS", "MS", "C",
    "BAC", "SCHW", "ICE", "CME",

    # Zdravstvo in medicinska tehnologija
    "ISRG", "DXCM", "PODD", "EXAS", "ILMN", "ALGN", "MDT",
    "SYK", "BSX", "ABT", "VRTX", "REGN", "LLY", "NVO", "UNH",

    # Industrija, energija, potrošnja in drugi sektorji
    "CAT", "DE", "ETN", "GE", "HON", "PH", "RTX", "LMT",
    "XOM", "CVX", "SLB", "FSLR", "ENPH", "NXT", "COST",
    "WMT", "HD", "LOW", "MCD", "NKE", "KO", "PG", "F",
    "GM", "RIVN", "LCID", "CVNA", "UPST", "Z", "W",
]

AI_UNIVERSE = list(dict.fromkeys(TICKER_CANDIDATES))[:150]

TICKERS_CONFIG = {
    "MNDY": {"name": "monday.com", "sector": "SaaS"},
    "CRWD": {"name": "CrowdStrike", "sector": "Cybersecurity"},
    "SNOW": {"name": "Snowflake", "sector": "Cloud"},
    "HUBS": {"name": "HubSpot", "sector": "Software"},
    "DELL": {"name": "Dell Technologies", "sector": "Hardware"},
    "DDOG": {"name": "Datadog", "sector": "Cloud"},
    "TEAM": {"name": "Atlassian", "sector": "Software"},
    "NOW": {"name": "ServiceNow", "sector": "Software"},
    "PANW": {"name": "Palo Alto Networks", "sector": "Cybersecurity"},
    "PLTR": {"name": "Palantir", "sector": "Software"},
}


# Sektorske skupine so približne klasifikacije za primerjavo znotraj
# univerzuma te aplikacije, ne uradne GICS klasifikacije.
SECTOR_GROUPS = {
    "SaaS / Software": [
        "MNDY", "SNOW", "HUBS", "DDOG", "TEAM", "NOW", "CRM", "ADBE",
        "SHOP", "NET", "ZS", "OKTA", "MDB", "ESTC", "PATH", "WDAY",
        "CFLT", "DOCN", "GTLB", "BILL", "ASAN", "IOT", "FSLY", "DT",
        "BSY", "PCOR", "NCNO", "ZM", "DOCU", "TWLO", "PD", "DBX",
        "SMAR", "UPWK", "SPT", "APPN", "PEGA", "FROG", "RNG", "PLTR",
        "VEEV", "TYL", "PTC", "ADSK", "TRMB",
    ],
    "Semiconductors / Hardware": [
        "NVDA", "AVGO", "AMD", "TSM", "MU", "QCOM", "ARM", "SMCI",
        "ANET", "MRVL", "SNPS", "CDNS", "ANSS", "ALAB", "LITE", "COHR",
        "VRT", "NTNX", "PSTG", "STX", "WDC", "TXN", "ADI", "NXPI",
        "MCHP", "ON", "INTC", "ASML", "AMAT", "LRCX", "KLAC", "DELL",
        "CSCO", "HPE", "HPQ", "GLW", "TER", "KEYS",
    ],
    "Cybersecurity": [
        "CRWD", "PANW", "CHKP", "CYBR", "TENB", "VRNS", "QLYS",
        "FTNT", "AKAM", "VRSN", "GEN", "S",
    ],
    "Large Tech / Internet": [
        "AAPL", "MSFT", "META", "AMZN", "GOOGL", "NFLX", "TSLA",
        "UBER", "ABNB", "DASH", "SPOT", "RBLX", "TTD", "ROKU",
        "PINS", "SNAP", "MTCH", "DKNG", "LYFT", "EBAY",
    ],
    "Financials / Fintech": [
        "COIN", "HOOD", "XYZ", "PYPL", "SOFI", "AFRM", "MELI", "SE",
        "NU", "V", "MA", "GLBE", "JPM", "GS", "MS", "C", "BAC",
        "SCHW", "ICE", "CME",
    ],
    "Healthcare": [
        "ISRG", "DXCM", "PODD", "EXAS", "ILMN", "ALGN", "MDT",
        "SYK", "BSX", "ABT", "VRTX", "REGN", "LLY", "NVO", "UNH",
    ],
    "Industrials": [
        "CAT", "DE", "ETN", "GE", "HON", "PH", "RTX", "LMT",
    ],
    "Energy": [
        "XOM", "CVX", "SLB", "FSLR", "ENPH", "NXT",
    ],
    "Consumer": [
        "COST", "WMT", "HD", "LOW", "MCD", "NKE", "KO", "PG",
        "F", "GM", "RIVN", "LCID", "CVNA", "UPST", "Z", "W",
    ],
}


def get_sector_group(ticker):
    for group_name, members in SECTOR_GROUPS.items():
        if ticker in members:
            return group_name
    return "Other / unclassified"


# ============================================================
# POMOŽNE FUNKCIJE
# ============================================================

def safe_float(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def display_value(value, digits=2, suffix=""):
    if value is None:
        return "—"
    try:
        return f"{float(value):,.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return "—"


def render_dark_table(frame):
    """Prikaže tabelo v temnem slogu; CSS ni f-string."""
    if frame is None or frame.empty:
        st.info("Ni podatkov za prikaz.")
        return

    headers = "".join(
        f"<th>{html.escape(str(column))}</th>"
        for column in frame.columns
    )

    body_rows = []
    for _, row in frame.iterrows():
        cells = []
        for value in row.tolist():
            if pd.isna(value):
                text = "—"
            else:
                text = str(value)
            cells.append(f"<td>{html.escape(text)}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")

    table_html = (
        '<div style="overflow-x:auto;border:1px solid #263044;'
        'border-radius:10px;margin:8px 0 18px 0;">'
        '<table style="border-collapse:collapse;width:100%;'
        'background:#0D111C;color:#CBD5E1;font-size:0.82rem;">'
        '<thead><tr style="background:#151B29;color:#F8FAFC;">'
        + headers
        + "</tr></thead><tbody>"
        + "".join(body_rows)
        + "</tbody></table></div>"
        "<style>"
        "table th, table td {"
        "border:1px solid #202838;"
        "padding:8px 10px;"
        "text-align:left;"
        "white-space:nowrap;"
        "}"
        "table tbody tr:nth-child(even) {background:#101522;}"
        "</style>"
    )

    st.markdown(table_html, unsafe_allow_html=True)


# ============================================================
# TRŽNI REŽIM IN SEKTORSKA RELATIVNA MOČ
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def get_market_regime():
    try:
        hist = yf.Ticker("SPY").history(
            period="6mo",
            interval="1d",
            auto_adjust=True,
        )
        if hist is None or len(hist) < 60:
            return {"regime": "NEZNANO", "spy_chg": None, "penalty": 0.0}

        close = hist["Close"].dropna().astype(float)
        if len(close) < 50:
            return {"regime": "NEZNANO", "spy_chg": None, "penalty": 0.0}

        last = float(close.iloc[-1])
        sma50 = float(close.rolling(50).mean().iloc[-1])
        change20 = (last / float(close.iloc[-21]) - 1) * 100

        if last > sma50 and change20 > -3:
            regime, penalty = "RISK-ON", 0.0
        elif last < sma50 and change20 < -3:
            regime, penalty = "RISK-OFF", 1.0
        else:
            regime, penalty = "NEVTRALNO", 0.5

        return {
            "regime": regime,
            "spy_chg": round(change20, 2),
            "penalty": penalty,
        }
    except Exception:
        return {"regime": "NEZNANO", "spy_chg": None, "penalty": 0.0}


@st.cache_data(ttl=900, show_spinner=False)
def get_capital_rotation():
    # Relativna cenovna moč ETF-jev ni neposredno merjenje tokov kapitala.
    sector_etfs = {
        "SaaS / software (IGV)": "IGV",
        "Semiconductors (SMH)": "SMH",
        "Cybersecurity (CIBR)": "CIBR",
        "Nasdaq (QQQ)": "QQQ",
        "Finance (XLF)": "XLF",
        "Healthcare (XLV)": "XLV",
        "Energy (XLE)": "XLE",
        "Industrials (XLI)": "XLI",
        "Consumer discretionary (XLY)": "XLY",
        "Consumer staples (XLP)": "XLP",
        "Materials (XLB)": "XLB",
        "Utilities (XLU)": "XLU",
        "Small caps (IWM)": "IWM",
    }

    closes = {}
    for ticker in list(sector_etfs.values()) + ["SPY"]:
        try:
            hist = yf.Ticker(ticker).history(
                period="8mo",
                interval="1d",
                auto_adjust=True,
            )
            if hist is not None and not hist.empty:
                closes[ticker] = hist["Close"].dropna().astype(float)
        except Exception:
            continue

    if "SPY" not in closes:
        return {"rows": [], "pair": "NI PODATKOV", "pair_detail": ""}

    def relative_return(series, benchmark, days):
        joined = pd.concat(
            [series.rename("sector"), benchmark.rename("benchmark")],
            axis=1,
            join="inner",
        ).dropna()

        if len(joined) <= days:
            return None

        sector_return = (
            joined["sector"].iloc[-1] / joined["sector"].iloc[-1 - days] - 1
        ) * 100
        benchmark_return = (
            joined["benchmark"].iloc[-1]
            / joined["benchmark"].iloc[-1 - days]
            - 1
        ) * 100

        return float(sector_return - benchmark_return)

    rows = []
    for label, ticker in sector_etfs.items():
        if ticker not in closes:
            continue

        result5 = relative_return(closes[ticker], closes["SPY"], 5)
        result20 = relative_return(closes[ticker], closes["SPY"], 20)
        result60 = relative_return(closes[ticker], closes["SPY"], 60)

        if result5 is None or result20 is None or result60 is None:
            continue

        if result5 > 0 and result20 > 0 and result60 < 0:
            status = "KREPI"
        elif result20 > 0 and result60 > 0:
            status = "RELATIVNO VODI"
        elif result5 < 0 and result20 < 0 and result60 > 0:
            status = "SLABI"
        elif result20 < 0:
            status = "ZAOSTAJA"
        else:
            status = "MEŠANO"

        rows.append({
            "Sektor / ETF": label,
            "Rel. 5d % vs SPY": round(result5, 1),
            "Rel. 20d % vs SPY": round(result20, 1),
            "Rel. 60d % vs SPY": round(result60, 1),
            "Oznaka": status,
        })

    rows.sort(
        key=lambda row: row["Rel. 20d % vs SPY"],
        reverse=True,
    )

    pair = "NI PODATKOV"
    detail = ""

    if "IGV" in closes and "SMH" in closes:
        joined = pd.concat(
            [closes["IGV"].rename("igv"), closes["SMH"].rename("smh")],
            axis=1,
            join="inner",
        ).dropna()

        if len(joined) > 60:
            ratio = joined["igv"] / joined["smh"]
            change20 = (ratio.iloc[-1] / ratio.iloc[-21] - 1) * 100
            change60 = (ratio.iloc[-1] / ratio.iloc[-61] - 1) * 100
            sma20 = ratio.rolling(20).mean().iloc[-1]
            above_sma20 = bool(ratio.iloc[-1] > sma20)

            if change20 > 0 and change60 < 0 and above_sma20:
                pair = "MOŽEN ZAČETEK RELATIVNE ROTACIJE SEMIS → SAAS"
            elif change20 > 0 and change60 > 0 and above_sma20:
                pair = "SAAS RELATIVNO VODI SEMIS"
            elif change20 < 0 and change60 > 0:
                pair = "SAAS RELATIVNO SLABI PROTI SEMIS"
            elif change20 < 0 and not above_sma20:
                pair = "SEMIS RELATIVNO VODI SAAS"
            else:
                pair = "NI JASNE RELATIVNE ROTACIJE"

            detail = (
                f"IGV/SMH: 20d {change20:+.1f}%, "
                f"60d {change60:+.1f}%; "
                f"nad SMA20: {'DA' if above_sma20 else 'NE'}"
            )

    return {"rows": rows, "pair": pair, "pair_detail": detail}


market = get_market_regime()
rotation = get_capital_rotation()


# ============================================================
# FUNDAMENTALNI PODATKI IN KAKOVOST FCF
# ============================================================

def find_statement_row(frame, possible_names):
    """Poišče vrstico finančnega izkaza po več možnih oznakah."""
    if frame is None or frame.empty:
        return None

    normalized = {
        str(index).strip().lower().replace("_", " "): index
        for index in frame.index
    }

    for possible in possible_names:
        key = possible.strip().lower().replace("_", " ")
        if key in normalized:
            return frame.loc[normalized[key]]

    for normalized_name, original_name in normalized.items():
        if any(
            possible.strip().lower().replace("_", " ") in normalized_name
            for possible in possible_names
        ):
            return frame.loc[original_name]

    return None


def annual_series(frame, names):
    row = find_statement_row(frame, names)
    if row is None:
        return []

    values = []
    for column, value in row.items():
        number = safe_float(value)
        if number is not None:
            values.append((column, number))

    try:
        values.sort(key=lambda item: pd.Timestamp(item[0]))
    except Exception:
        pass

    return [value for _, value in values[-5:]]


@st.cache_data(ttl=1800, show_spinner=False)
def get_fundamental_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}

        def get_num(key):
            return safe_float(info.get(key))

        price = get_num("currentPrice") or get_num("regularMarketPrice")
        market_cap = get_num("marketCap")
        average_volume = get_num("averageVolume")
        ps = get_num("priceToSalesTrailing12Months")
        peg = get_num("pegRatio")
        revenue_growth = get_num("revenueGrowth")
        cash = get_num("totalCash")
        debt = get_num("totalDebt")
        analyst_count = get_num("numberOfAnalystOpinions")
        recommendation_mean = get_num("recommendationMean")
        analyst_target = (
            get_num("targetMeanPrice")
            or get_num("targetMedianPrice")
        )

        if revenue_growth is not None and revenue_growth > 1:
            revenue_growth /= 100

        dollar_volume = None
        if price is not None and average_volume is not None:
            dollar_volume = price * average_volume

        analyst_upside = None
        if price and analyst_target:
            analyst_upside = (analyst_target / price - 1) * 100

        net_cash = None
        if cash is not None and debt is not None:
            net_cash = cash - debt

        # Annual izkazi se uporabljajo za večletno FCF doslednost,
        # pretvorbo čistega dobička v denar in SBC.
        try:
            cashflow = stock.cashflow
        except Exception:
            cashflow = None

        try:
            income_stmt = stock.income_stmt
        except Exception:
            income_stmt = None

        cfo_series = annual_series(
            cashflow,
            [
                "Operating Cash Flow",
                "Total Cash From Operating Activities",
                "Cash Flow From Continuing Operating Activities",
            ],
        )
        capex_series = annual_series(
            cashflow,
            [
                "Capital Expenditure",
                "Capital Expenditures",
                "Capital Expenditure Reported",
            ],
        )
        sbc_series = annual_series(
            cashflow,
            [
                "Stock Based Compensation",
                "Share Based Compensation",
            ],
        )
        net_income_series = annual_series(
            income_stmt,
            [
                "Net Income",
                "Net Income Common Stockholders",
                "Net Income From Continuing Operations",
            ],
        )
        revenue_series = annual_series(
            income_stmt,
            [
                "Total Revenue",
                "Operating Revenue",
                "Revenue",
            ],
        )

        count = min(
            len(cfo_series),
            len(capex_series),
            len(net_income_series),
            len(revenue_series),
        )

        annual_records = []
        if count:
            cfo_values = cfo_series[-count:]
            capex_values = capex_series[-count:]
            net_income_values = net_income_series[-count:]
            revenue_values = revenue_series[-count:]

            sbc_values = sbc_series[-count:] if sbc_series else [None] * count

            for index in range(count):
                cfo = cfo_values[index]
                capex = capex_values[index]
                net_income = net_income_values[index]
                revenue = revenue_values[index]
                sbc = sbc_values[index] if index < len(sbc_values) else None

                # Capex je lahko v izkazu negativen ali pozitiven.
                fcf = cfo - abs(capex)
                annual_records.append({
                    "cfo": cfo,
                    "capex": abs(capex),
                    "fcf": fcf,
                    "net_income": net_income,
                    "revenue": revenue,
                    "sbc": abs(sbc) if sbc is not None else None,
                })

        fcf_values = [record["fcf"] for record in annual_records]
        positive_fcf_count = sum(value > 0 for value in fcf_values)
        fcf_years = len(fcf_values)

        fcf_margin_values = [
            record["fcf"] / record["revenue"] * 100
            for record in annual_records
            if record["revenue"] and record["revenue"] > 0
        ]
        median_fcf_margin = (
            float(pd.Series(fcf_margin_values).median())
            if fcf_margin_values
            else None
        )

        cash_conversion_values = [
            record["cfo"] / record["net_income"]
            for record in annual_records
            if record["net_income"] and record["net_income"] > 0
        ]
        median_cash_conversion = (
            float(pd.Series(cash_conversion_values).median())
            if cash_conversion_values
            else None
        )

        latest_sbc_burden = None
        for record in reversed(annual_records):
            if record["sbc"] is not None and record["revenue"] and record["revenue"] > 0:
                latest_sbc_burden = record["sbc"] / record["revenue"] * 100
                break

        latest_fcf_yield = None
        if annual_records and market_cap and market_cap > 0:
            latest_fcf_yield = annual_records[-1]["fcf"] / market_cap * 100

        # Ekstremne FCF yield vrednosti označi kot sumljive, ne kot bonus.
        fcf_yield_valid = (
            latest_fcf_yield is not None
            and -10 <= latest_fcf_yield <= 15
        )
        if not fcf_yield_valid:
            latest_fcf_yield_display = None
        else:
            latest_fcf_yield_display = latest_fcf_yield

        return {
            "ticker": ticker,
            "name": info.get("shortName") or ticker,
            "sector": get_sector_group(ticker),
            "price": price,
            "market_cap": market_cap,
            "dollar_volume": dollar_volume,
            "ps": ps,
            "peg": peg,
            "revenue_growth": revenue_growth,
            "cash": cash,
            "debt": debt,
            "net_cash": net_cash,
            "analyst_count": analyst_count,
            "recommendation_mean": recommendation_mean,
            "analyst_upside": analyst_upside,
            "annual_records": annual_records,
            "fcf_years": fcf_years,
            "positive_fcf_years": positive_fcf_count,
            "median_fcf_margin": median_fcf_margin,
            "median_cash_conversion": median_cash_conversion,
            "sbc_burden": latest_sbc_burden,
            "fcf_yield": latest_fcf_yield_display,
            "fcf_yield_raw": latest_fcf_yield,
            "fcf_yield_valid": fcf_yield_valid,
        }

    except Exception:
        return None


def passes_liquidity(data):
    # Če so bistveni podatki o velikosti ali prometu manjkajoči,
    # likvidnosti ne štejemo kot potrjene.
    return bool(
        data
        and data.get("market_cap") is not None
        and data.get("dollar_volume") is not None
        and data["market_cap"] >= 2_000_000_000
        and data["dollar_volume"] >= 20_000_000
    )


def fcf_quality_score(data):
    """
    Hevristična kakovost FCF:
    vzdržnost, denarna pretvorba, marža, SBC breme in neto denar.
    Ne nadomešča pregleda poročil podjetja.
    """
    components = []

    years = data.get("fcf_years", 0)
    positive_years = data.get("positive_fcf_years", 0)
    if years > 0:
        consistency = positive_years / years * 10
        components.append((consistency, 0.25))

    conversion = data.get("median_cash_conversion")
    if conversion is not None and math.isfinite(conversion):
        # Ocena je omejena, saj so ekstremna razmerja pogosto posledica
        # majhnega imenovalca ali računovodskih posebnosti.
        conversion_score = max(0.0, min(10.0, conversion * 5))
        components.append((conversion_score, 0.20))

    fcf_margin = data.get("median_fcf_margin")
    if fcf_margin is not None:
        # 0% = nizka ocena; 20% ali več doseže zgornji del lestvice.
        margin_score = max(0.0, min(10.0, fcf_margin / 2))
        components.append((margin_score, 0.20))

    sbc_burden = data.get("sbc_burden")
    if sbc_burden is not None:
        sbc_score = max(0.0, min(10.0, 10 - sbc_burden / 2))
        components.append((sbc_score, 0.20))

    net_cash = data.get("net_cash")
    if net_cash is not None:
        balance_score = 7.0 if net_cash > 0 else 3.0
        components.append((balance_score, 0.15))

    if not components:
        return None

    total_weight = sum(weight for _, weight in components)
    if total_weight <= 0:
        return None

    # Manjkajoče komponente se ne obravnavajo kot ničla; pokritost je ločena.
    weighted = sum(score * weight for score, weight in components) / total_weight
    return round(max(0.0, min(10.0, weighted)), 1)


def fundamental_data_reliability(data):
    """
    Zanesljivost pomeni razpoložljivost in osnovno skladnost polj,
    ne neodvisno preverjanje pravilnosti Yahoo Finance podatkov.
    """
    checks = []

    for key in ("price", "market_cap", "dollar_volume", "ps", "peg", "revenue_growth"):
        checks.append(data.get(key) is not None)

    checks.append(data.get("fcf_years", 0) >= 2)
    checks.append(data.get("median_fcf_margin") is not None)
    checks.append(data.get("median_cash_conversion") is not None)
    checks.append(data.get("sbc_burden") is not None)

    score = sum(checks) / len(checks) * 100

    flags = []
    if data.get("ps") is not None and data["ps"] < 1:
        flags.append("P/S < 1: preveri podatek")
    if (
        data.get("fcf_yield_raw") is not None
        and not data.get("fcf_yield_valid")
    ):
        flags.append("FCF yield izven kontrolnega razpona")
    if data.get("fcf_years", 0) < 2:
        flags.append("malo letnih FCF podatkov")
    if data.get("median_cash_conversion") is None:
        flags.append("ni uporabne pretvorbe dobička v denar")

    return round(score), flags


def wall_street_score(data):
    """
    Grob približek na podlagi trenutnih Yahoo Finance analitikov.
    Ne meri spremembe sentimenta analitikov skozi čas.
    """
    score = 5.0
    recommendation = data.get("recommendation_mean")

    if recommendation is not None:
        if recommendation <= 1.5:
            score += 2.0
        elif recommendation <= 2.0:
            score += 1.5
        elif recommendation <= 2.5:
            score += 0.5
        elif recommendation >= 4.0:
            score -= 1.5
        elif recommendation >= 3.5:
            score -= 1.0

    upside = data.get("analyst_upside")
    if upside is not None:
        if upside > 30:
            score += 1.5
        elif upside > 15:
            score += 1.0
        elif upside > 5:
            score += 0.5
        elif upside < -10:
            score -= 1.0

    count = data.get("analyst_count")
    if count is not None and count < 5:
        score -= 0.5

    return round(max(0.0, min(10.0, score)), 1)


def raw_valuation_metrics(data):
    ps = data.get("ps")
    fcf_yield = data.get("fcf_yield")

    # Za relativno vrednotenje uporabimo P/S in FCF yield, kadar sta uporabna.
    # Višji FCF yield je ugodnejši; negativni ali ekstremni yield ni točkovan.
    return {
        "ps": ps if ps is not None and ps >= 1 else None,
        "fcf_yield": (
            fcf_yield
            if data.get("fcf_yield_valid") and fcf_yield is not None
            else None
        ),
    }


def calculate_sector_percentiles(rows):
    """
    Percentili se izračunajo samo proti drugim tickerjem iste ročne
    sektorske skupine, ki so prestali podatkovne in likvidnostne filtre.
    Majhen peer group je označen z nizkim številom primerljivih podjetij.
    """
    by_sector = {}
    for row in rows:
        by_sector.setdefault(row["sector"], []).append(row)

    for sector_rows in by_sector.values():
        for row in sector_rows:
            peers = sector_rows
            row["sector_peer_count"] = len(peers)

            fcf_scores = [
                peer["fcf_quality"]
                for peer in peers
                if peer["fcf_quality"] is not None
            ]
            if row["fcf_quality"] is not None and fcf_scores:
                row["fcf_percentile"] = round(
                    sum(value <= row["fcf_quality"] for value in fcf_scores)
                    / len(fcf_scores)
                    * 100
                )
            else:
                row["fcf_percentile"] = None

            valuation_parts = []

            ps_values = [
                peer["valuation_metrics"]["ps"]
                for peer in peers
                if peer["valuation_metrics"]["ps"] is not None
            ]
            row_ps = row["valuation_metrics"]["ps"]
            if row_ps is not None and len(ps_values) >= 2:
                # Nižji P/S dobi višji percentile znotraj peer skupine.
                percentile = sum(value >= row_ps for value in ps_values) / len(ps_values) * 100
                valuation_parts.append(percentile)

            fcf_yields = [
                peer["valuation_metrics"]["fcf_yield"]
                for peer in peers
                if peer["valuation_metrics"]["fcf_yield"] is not None
            ]
            row_fcf_yield = row["valuation_metrics"]["fcf_yield"]
            if row_fcf_yield is not None and len(fcf_yields) >= 2:
                # Višji veljaven FCF yield dobi višji percentile.
                percentile = sum(value <= row_fcf_yield for value in fcf_yields) / len(fcf_yields) * 100
                valuation_parts.append(percentile)

            row["valuation_score"] = (
                round(sum(valuation_parts) / len(valuation_parts) / 10, 1)
                if valuation_parts
                else None
            )

            peer_parts = []
            if row.get("fcf_percentile") is not None:
                peer_parts.append(row["fcf_percentile"])
            if row.get("valuation_score") is not None:
                peer_parts.append(row["valuation_score"] * 10)

            row["sector_percentile"] = (
                round(sum(peer_parts) / len(peer_parts))
                if peer_parts
                else None
            )

            # Skupna razvrstitvena ocena uporablja le komponente, ki obstajajo.
            composite_parts = []
            if row.get("fcf_quality") is not None:
                composite_parts.append((row["fcf_quality"], 0.45))
            if row.get("valuation_score") is not None:
                composite_parts.append((row["valuation_score"], 0.35))
            if row.get("sector_percentile") is not None:
                composite_parts.append((row["sector_percentile"] / 10, 0.20))

            total_weight = sum(weight for _, weight in composite_parts)
            row["composite_score"] = (
                round(
                    sum(score * weight for score, weight in composite_parts)
                    / total_weight,
                    1,
                )
                if total_weight > 0
                else None
            )

    return rows


@st.cache_data(ttl=1800, show_spinner=False)
def scan_long_universe(universe):
    rows = []

    for ticker in universe:
        data = get_fundamental_data(ticker)
        if not data or not passes_liquidity(data):
            continue

        # Brez veljavnih P/S, PEG in rasti ni kandidata za ta fundamentalni sken.
        if data.get("ps") is None or data["ps"] < 1 or data["ps"] > 20:
            continue
        if data.get("peg") is None or data["peg"] <= 0 or data["peg"] > 2.8:
            continue
        if (
            data.get("revenue_growth") is None
            or data["revenue_growth"] < 0.12
        ):
            continue

        # Če je podjetje zadolženo in ima negativen neto denar, ga izločimo.
        if (
            data.get("debt") is not None
            and data.get("net_cash") is not None
            and data["debt"] > 0
            and data["net_cash"] < 0
        ):
            continue

        quality = fcf_quality_score(data)
        reliability, flags = fundamental_data_reliability(data)
        metrics = raw_valuation_metrics(data)

        rows.append({
            **data,
            "fcf_quality": quality,
            "data_reliability": reliability,
            "data_flags": flags,
            "valuation_metrics": metrics,
        })

    rows = calculate_sector_percentiles(rows)
    rows = [
        row for row in rows
        if row.get("composite_score") is not None
    ]
    rows.sort(
        key=lambda row: (
            row.get("composite_score", -1),
            row.get("data_reliability", 0),
            row.get("ticker", ""),
        ),
        reverse=True,
    )
    return rows


@st.cache_data(ttl=1800, show_spinner=False)
def get_three_year_price_context(ticker):
    # Mediana cene ni zgodovinski P/S in sama ne dokazuje podcenjenosti.
    try:
        hist = yf.Ticker(ticker).history(
            period="3y",
            interval="1wk",
            auto_adjust=True,
        )
        if hist is None or hist.empty:
            return None

        close = hist["Close"].dropna().astype(float)
        if len(close) < 50:
            return None

        median_price = float(close.median())
        current_price = float(close.iloc[-1])
        if median_price <= 0:
            return None

        return round((current_price / median_price - 1) * 100, 1)
    except Exception:
        return None


# ============================================================
# INTRADAY PODATKI: PREMARKET IN REDNA SEJA LOČENO
# ============================================================

@st.cache_data(ttl=90, show_spinner=False)
def get_intraday_history(ticker, period="5d"):
    try:
        hist = yf.Ticker(ticker).history(
            period=period,
            interval="5m",
            prepost=True,
            auto_adjust=False,
        )
        if hist is None or hist.empty:
            return None

        required = ["Open", "High", "Low", "Close", "Volume"]
        if any(column not in hist.columns for column in required):
            return None

        hist = hist.dropna(subset=required).copy()
        if hist.empty:
            return None

        if hist.index.tz is None:
            hist.index = hist.index.tz_localize("UTC")
        hist.index = hist.index.tz_convert(NY_TZ)

        # Obdrži premarket in redno sejo; after-hours izloči.
        keep = [
            time(4, 0) <= stamp.time() < time(16, 0)
            for stamp in hist.index
        ]
        hist = hist.loc[keep].copy()
        return hist if not hist.empty else None
    except Exception:
        return None


def get_session_bars(history, session_date, session_kind):
    if history is None or history.empty:
        return pd.DataFrame()

    same_day = history[
        [stamp.date() == session_date for stamp in history.index]
    ].copy()

    if same_day.empty:
        return same_day

    if session_kind == "premarket":
        return same_day.between_time("04:00", "09:29")

    return same_day.between_time("09:30", "15:59")


def get_previous_regular_close(history, session_date):
    if history is None or history.empty:
        return None

    earlier = history[
        [stamp.date() < session_date for stamp in history.index]
    ]
    if earlier.empty:
        return None

    previous_dates = sorted(
        {stamp.date() for stamp in earlier.index},
        reverse=True,
    )

    for previous_date in previous_dates:
        bars = get_session_bars(history, previous_date, "regular")
        if bars.empty:
            continue
        close = safe_float(bars["Close"].iloc[-1])
        if close is not None and close > 0:
            return close

    return None


def anchored_vwap_series(bars):
    if bars is None or bars.empty:
        return pd.Series(dtype=float)

    high = bars["High"].astype(float)
    low = bars["Low"].astype(float)
    close = bars["Close"].astype(float)
    volume = bars["Volume"].astype(float).clip(lower=0)

    # HLC3 VWAP se ponastavi na začetku izbrane seje.
    typical_price = (high + low + close) / 3
    cumulative_volume = volume.cumsum().replace(0, float("nan"))
    return (typical_price * volume).cumsum() / cumulative_volume


def same_time_volume_ratio(history, timestamp, session_bars, index_in_session):
    """
    Primerja tekočo 5-minutno svečo z mediano prometa ob isti uri
    v zadnjih petih razpoložljivih primerljivih sejah.
    """
    current_volume = safe_float(
        session_bars["Volume"].iloc[index_in_session]
    )
    if current_volume is None or current_volume <= 0:
        return None

    session_kind = (
        "premarket"
        if timestamp.time() < time(9, 30)
        else "regular"
    )
    clock = timestamp.strftime("%H:%M")

    earlier_dates = sorted({
        stamp.date()
        for stamp in history.index
        if stamp.date() < timestamp.date()
    })

    prior_volumes = []
    for prior_date in earlier_dates[-5:]:
        prior_bars = get_session_bars(
            history,
            prior_date,
            session_kind,
        )
        if prior_bars.empty:
            continue

        matching = [
            stamp for stamp in prior_bars.index
            if stamp.strftime("%H:%M") == clock
        ]
        if matching:
            volume = safe_float(
                prior_bars.loc[matching[-1], "Volume"]
            )
            if volume is not None and volume > 0:
                prior_volumes.append(volume)

    if not prior_volumes:
        return None

    baseline = float(pd.Series(prior_volumes).median())
    if baseline <= 0:
        return None

    return current_volume / baseline


def calculate_rsi(values, period=14):
    close = pd.Series(values, dtype=float)
    if len(close) < period + 1:
        return None

    change = close.diff()
    gains = change.clip(lower=0)
    losses = -change.clip(upper=0)

    average_gain = gains.rolling(period).mean().iloc[-1]
    average_loss = losses.rolling(period).mean().iloc[-1]

    if pd.isna(average_gain) or pd.isna(average_loss):
        return None
    if average_loss == 0:
        return 100.0 if average_gain > 0 else 50.0

    relative_strength = average_gain / average_loss
    return float(100 - (100 / (1 + relative_strength)))


def earnings_within_days(ticker, days=5):
    """
    True: datum je najden v obdobju.
    False: uspešno preverjeni podatki ne kažejo datuma v obdobju.
    None: preverjanje ni uspelo ali datum ni na voljo.
    """
    try:
        earnings = yf.Ticker(ticker).get_earnings_dates(limit=8)
        if earnings is None or len(earnings) == 0:
            return None

        today = datetime.now(NY_TZ).date()
        for raw_date in earnings.index:
            date_value = pd.Timestamp(raw_date)
            if date_value.tzinfo is not None:
                date_value = date_value.tz_convert(None)

            delta = (date_value.date() - today).days
            if 0 <= delta <= days:
                return True

        return False
    except Exception:
        return None


def build_reversal_signal(ticker, history, session_date, now_ny=None):
    if history is None or history.empty:
        return None

    now_ny = now_ny or datetime.now(NY_TZ)
    if session_date != now_ny.date():
        return None

    current_day = history[
        [stamp.date() == session_date for stamp in history.index]
    ].copy()
    if current_day.empty:
        return None

    # Uporabi samo zaključene 5-minutne sveče.
    completed = current_day[
        [
            stamp + timedelta(minutes=5) <= now_ny
            for stamp in current_day.index
        ]
    ]
    if completed.empty:
        return None

    latest_stamp = completed.index[-1]
    session_kind = (
        "premarket"
        if latest_stamp.time() < time(9, 30)
        else "regular"
    )

    bars = get_session_bars(history, session_date, session_kind)
    bars = bars[
        [
            stamp + timedelta(minutes=5) <= now_ny
            for stamp in bars.index
        ]
    ]
    if len(bars) < 15:
        return None

    last_stamp = bars.index[-1]
    last_index = len(bars) - 1
    previous_close = get_previous_regular_close(history, session_date)
    if previous_close is None:
        return None

    close = safe_float(bars["Close"].iloc[-1])
    open_price = safe_float(bars["Open"].iloc[-1])
    previous_bar_close = safe_float(bars["Close"].iloc[-2])
    if not close or not open_price or not previous_bar_close:
        return None

    gap_pct = (close / previous_close - 1) * 100
    if not -8.0 <= gap_pct <= -1.0:
        return None

    vwap = anchored_vwap_series(bars)
    if len(vwap) < 2 or pd.isna(vwap.iloc[-1]) or pd.isna(vwap.iloc[-2]):
        return None

    prior_close = safe_float(bars["Close"].iloc[-2])
    prior_vwap = safe_float(vwap.iloc[-2])
    current_vwap = safe_float(vwap.iloc[-1])
