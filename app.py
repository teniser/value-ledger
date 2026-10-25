import html
import math
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st
import yfinance as yf


# ============================================================
# NASTAVITVE IN TEMNI VIDEZ
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
# UNIVERZUM: UNIKATNI TICKERJI, NAJVEČ 150
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
    "MNDY": {"name": "monday.com", "sector": "SaaS / Software"},
    "CRWD": {"name": "CrowdStrike", "sector": "Cybersecurity"},
    "SNOW": {"name": "Snowflake", "sector": "SaaS / Software"},
    "HUBS": {"name": "HubSpot", "sector": "SaaS / Software"},
    "DELL": {"name": "Dell Technologies", "sector": "Semiconductors / Hardware"},
    "DDOG": {"name": "Datadog", "sector": "SaaS / Software"},
    "TEAM": {"name": "Atlassian", "sector": "SaaS / Software"},
    "NOW": {"name": "ServiceNow", "sector": "SaaS / Software"},
    "PANW": {"name": "Palo Alto Networks", "sector": "Cybersecurity"},
    "PLTR": {"name": "Palantir", "sector": "SaaS / Software"},
}

# Ročno določene primerjalne skupine za ta skener.
# To niso uradne klasifikacije in se lahko prekrivajo po poslovnih dejavnostih.
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
        "ANET", "MRVL", "SNPS", "CDNS", "ANSS", "ALAB", "LITE",
        "COHR", "VRT", "NTNX", "PSTG", "STX", "WDC", "TXN", "ADI",
        "NXPI", "MCHP", "ON", "INTC", "ASML", "AMAT", "LRCX",
        "KLAC", "DELL", "CSCO", "HPE", "HPQ", "GLW", "TER", "KEYS",
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
        "COIN", "HOOD", "XYZ", "PYPL", "SOFI", "AFRM", "MELI",
        "SE", "NU", "V", "MA", "GLBE", "JPM", "GS", "MS", "C",
        "BAC", "SCHW", "ICE", "CME",
    ],
    "Healthcare": [
        "ISRG", "DXCM", "PODD", "EXAS", "ILMN", "ALGN", "MDT",
        "SYK", "BSX", "ABT", "VRTX", "REGN", "LLY", "NVO", "UNH",
    ],
    "Industrials": ["CAT", "DE", "ETN", "GE", "HON", "PH", "RTX", "LMT"],
    "Energy": ["XOM", "CVX", "SLB", "FSLR", "ENPH", "NXT"],
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
# SPLOŠNE POMOŽNE FUNKCIJE
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
    # Relativna cenovna moč ETF-jev ni neposredno merjenje denarnih tokov.
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
# FUNDAMENTALNI PODATKI IN DENARNI TOK
# ============================================================

def find_statement_row(frame, possible_names):
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


def statement_values_by_year(frame, possible_names):
    row = find_statement_row(frame, possible_names)
    if row is None:
        return {}

    values = {}
    for column, value in row.items():
        number = safe_float(value)
        if number is None:
            continue
        try:
            year = pd.Timestamp(column).year
            values[year] = number
        except Exception:
            continue

    return values


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
        trailing_pe = get_num("trailingPE")
        price_to_book = get_num("priceToBook")
        enterprise_to_ebitda = get_num("enterpriseToEbitda")
        revenue_growth = get_num("revenueGrowth")
        cash = get_num("totalCash")
        debt = get_num("totalDebt")
        analyst_count = get_num("numberOfAnalystOpinions")
        recommendation_mean = get_num("recommendationMean")
        target_price = get_num("targetMeanPrice") or get_num("targetMedianPrice")

        if revenue_growth is not None and revenue_growth > 1:
            revenue_growth /= 100

        dollar_volume = None
        if price is not None and average_volume is not None:
            dollar_volume = price * average_volume

        analyst_upside = None
        if price and target_price:
            analyst_upside = (target_price / price - 1) * 100

        net_cash = None
        if cash is not None and debt is not None:
            net_cash = cash - debt

        try:
            cashflow = stock.cashflow
        except Exception:
            cashflow = None

        try:
            income_stmt = stock.income_stmt
        except Exception:
            income_stmt = None

        cfo_by_year = statement_values_by_year(
            cashflow,
            [
                "Operating Cash Flow",
                "Total Cash From Operating Activities",
                "Cash Flow From Continuing Operating Activities",
            ],
        )
        capex_by_year = statement_values_by_year(
            cashflow,
            [
                "Capital Expenditure",
                "Capital Expenditures",
                "Capital Expenditure Reported",
            ],
        )
        sbc_by_year = statement_values_by_year(
            cashflow,
            [
                "Stock Based Compensation",
                "Share Based Compensation",
            ],
        )
        net_income_by_year = statement_values_by_year(
            income_stmt,
            [
                "Net Income",
                "Net Income Common Stockholders",
                "Net Income From Continuing Operations",
            ],
        )
        revenue_by_year = statement_values_by_year(
            income_stmt,
            [
                "Total Revenue",
                "Operating Revenue",
                "Revenue",
            ],
        )

        common_years = sorted(
            set(cfo_by_year)
            & set(capex_by_year)
            & set(net_income_by_year)
            & set(revenue_by_year)
        )[-5:]

        annual_records = []
        for year in common_years:
            cfo = cfo_by_year[year]
            capex = abs(capex_by_year[year])
            net_income = net_income_by_year[year]
            revenue = revenue_by_year[year]
            sbc = sbc_by_year.get(year)

            annual_records.append({
                "year": year,
                "cfo": cfo,
                "capex": capex,
                "fcf": cfo - capex,
                "net_income": net_income,
                "revenue": revenue,
                "sbc": abs(sbc) if sbc is not None else None,
            })

        fcf_years = len(annual_records)
        positive_fcf_years = sum(
            row["fcf"] > 0 for row in annual_records
        )

        fcf_margins = [
            row["fcf"] / row["revenue"] * 100
            for row in annual_records
            if row["revenue"] > 0
        ]
        median_fcf_margin = (
            float(pd.Series(fcf_margins).median())
            if fcf_margins
            else None
        )

        cash_conversions = [
            row["cfo"] / row["net_income"]
            for row in annual_records
            if row["net_income"] > 0
        ]
        median_cash_conversion = (
            float(pd.Series(cash_conversions).median())
            if cash_conversions
            else None
        )

        sbc_burdens = [
            row["sbc"] / row["revenue"] * 100
            for row in annual_records
            if row["sbc"] is not None and row["revenue"] > 0
        ]
        latest_sbc_burden = sbc_burdens[-1] if sbc_burdens else None

        latest_fcf_yield = None
        if annual_records and market_cap and market_cap > 0:
            latest_fcf_yield = annual_records[-1]["fcf"] / market_cap * 100

        fcf_yield_valid = (
            latest_fcf_yield is not None
            and -10 <= latest_fcf_yield <= 15
        )
        fcf_yield = latest_fcf_yield if fcf_yield_valid else None

        return {
            "ticker": ticker,
            "name": info.get("shortName") or ticker,
            "sector": get_sector_group(ticker),
            "price": price,
            "market_cap": market_cap,
            "dollar_volume": dollar_volume,
            "ps": ps,
            "peg": peg,
            "trailing_pe": trailing_pe,
            "price_to_book": price_to_book,
            "enterprise_to_ebitda": enterprise_to_ebitda,
            "revenue_growth": revenue_growth,
            "cash": cash,
            "debt": debt,
            "net_cash": net_cash,
            "analyst_count": analyst_count,
            "recommendation_mean": recommendation_mean,
            "analyst_upside": analyst_upside,
            "annual_records": annual_records,
            "fcf_years": fcf_years,
            "positive_fcf_years": positive_fcf_years,
            "median_fcf_margin": median_fcf_margin,
            "median_cash_conversion": median_cash_conversion,
            "sbc_burden": latest_sbc_burden,
            "fcf_yield": fcf_yield,
            "fcf_yield_raw": latest_fcf_yield,
            "fcf_yield_valid": fcf_yield_valid,
        }
    except Exception:
        return None


def passes_liquidity(data):
    return bool(
        data
        and data.get("market_cap") is not None
        and data.get("dollar_volume") is not None
        and data["market_cap"] >= 2_000_000_000
        and data["dollar_volume"] >= 20_000_000
    )


def fcf_quality_score(data):
    """Hevristična FCF ocena iz razpoložljivih večletnih meril."""
    components = []

    years = data.get("fcf_years", 0)
    if years > 0:
        positive_years = data.get("positive_fcf_years", 0)
        consistency_score = positive_years / years * 10
        components.append((consistency_score, 0.25))

    conversion = data.get("median_cash_conversion")
    if conversion is not None and math.isfinite(conversion):
        conversion_score = max(0.0, min(10.0, conversion * 5))
        components.append((conversion_score, 0.20))

    fcf_margin = data.get("median_fcf_margin")
    if fcf_margin is not None:
        margin_score = max(0.0, min(10.0, fcf_margin / 2))
        components.append((margin_score, 0.20))

    sbc_burden = data.get("sbc_burden")
    if sbc_burden is not None:
        sbc_score = max(0.0, min(10.0, 10 - sbc_burden / 2))
        components.append((sbc_score, 0.20))

    net_cash = data.get("net_cash")
    if net_cash is not None:
        components.append((7.0 if net_cash > 0 else 3.0, 0.15))

    if not components:
        return None

    weight_total = sum(weight for _, weight in components)
    if weight_total <= 0:
        return None

    result = sum(score * weight for score, weight in components) / weight_total
    return round(max(0.0, min(10.0, result)), 1)


def wall_street_score(data):
    """Trenutni analitik/target približek; ne meri sentimenta skozi čas."""
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

    analyst_count = data.get("analyst_count")
    if analyst_count is not None and analyst_count < 5:
        score -= 0.5

    return round(max(0.0, min(10.0, score)), 1)


def get_sector_valuation_metric(data):
    """
    Izbere primernejši razpoložljivi večkratnik za sektorsko primerjavo.
    Ni vseh metrik mogoče uporabiti pri vseh podjetjih.
    """
    sector = data.get("sector")

    if sector == "Financials / Fintech":
        for key, label in (
            ("price_to_book", "P/B"),
            ("trailing_pe", "P/E"),
        ):
            value = data.get(key)
            if value is not None and value > 0:
                return {"name": label, "value": value, "lower_is_better": True}

    if sector in ("Industrials", "Energy", "Consumer", "Healthcare"):
        for key, label in (
            ("enterprise_to_ebitda", "EV/EBITDA"),
            ("trailing_pe", "P/E"),
        ):
            value = data.get(key)
            if value is not None and value > 0:
                return {"name": label, "value": value, "lower_is_better": True}

    if sector in (
        "SaaS / Software",
        "Semiconductors / Hardware",
        "Cybersecurity",
        "Large Tech / Internet",
        "Other / unclassified",
    ):
        ps = data.get("ps")
        if ps is not None and ps >= 1:
            return {"name": "P/S", "value": ps, "lower_is_better": True}

        pe = data.get("trailing_pe")
        if pe is not None and pe > 0:
            return {"name": "P/E", "value": pe, "lower_is_better": True}

    return {"name": "NI PODATKA", "value": None, "lower_is_better": True}


def data_reliability_score(data):
    """Prisotnost in osnovna skladnost podatkov, ne neodvisna revizija."""
    checks = [
        data.get("price") is not None,
        data.get("market_cap") is not None,
        data.get("dollar_volume") is not None,
        data.get("revenue_growth") is not None,
        data.get("ps") is not None or data.get("trailing_pe") is not None,
        data.get("fcf_years", 0) >= 2,
        data.get("median_fcf_margin") is not None,
        data.get("median_cash_conversion") is not None,
        data.get("sbc_burden") is not None,
        data.get("net_cash") is not None,
    ]

    score = round(sum(checks) / len(checks) * 100)
    flags = []

    if data.get("ps") is not None and data["ps"] < 1:
