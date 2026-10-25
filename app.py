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
        flags.append("P/S < 1: preveri podatek")
    if (
        data.get("fcf_yield_raw") is not None
        and not data.get("fcf_yield_valid")
    ):
        flags.append("FCF yield izven kontrolnega razpona")
    if data.get("fcf_years", 0) < 2:
        flags.append("manj kot 2 skupni leti izkazov")
    if data.get("median_cash_conversion") is None:
        flags.append("ni uporabne pretvorbe v denar")
    if data.get("sbc_burden") is None:
        flags.append("ni podatka o SBC")

    return score, flags


def percentile_score(values, target, lower_is_better):
    clean_values = [
        value for value in values
        if value is not None and math.isfinite(value)
    ]
    if target is None or not clean_values:
        return None

    if lower_is_better:
        percentile = sum(value >= target for value in clean_values) / len(clean_values) * 100
    else:
        percentile = sum(value <= target for value in clean_values) / len(clean_values) * 100

    return round(percentile)


def calculate_peer_scores(rows):
    """Izračuna percentile le med podjetji iste skupine v trenutnem skenu."""
    groups = {}
    for row in rows:
        groups.setdefault(row["sector"], []).append(row)

    for group_rows in groups.values():
        peer_count = len(group_rows)

        for row in group_rows:
            row["peer_count"] = peer_count

            quality_values = [
                peer["fcf_quality"]
                for peer in group_rows
                if peer["fcf_quality"] is not None
            ]
            row["fcf_percentile"] = percentile_score(
                quality_values,
                row["fcf_quality"],
                lower_is_better=False,
            )

            metric_name = row["valuation_metric"]["name"]
            valuation_values = [
                peer["valuation_metric"]["value"]
                for peer in group_rows
                if (
                    peer["valuation_metric"]["name"] == metric_name
                    and peer["valuation_metric"]["value"] is not None
                )
            ]
            row["valuation_percentile"] = percentile_score(
                valuation_values,
                row["valuation_metric"]["value"],
                lower_is_better=True,
            )

            peer_scores = []
            if row["fcf_percentile"] is not None:
                peer_scores.append(row["fcf_percentile"] / 10)
            if row["valuation_percentile"] is not None:
                peer_scores.append(row["valuation_percentile"] / 10)

            row["sector_percentile"] = (
                round(sum(peer_scores) / len(peer_scores) * 10)
                if peer_scores
                else None
            )

            # Ločene komponente; manjkajoče se izpustijo in niso ničle.
            components = []
            if row["fcf_quality"] is not None:
                components.append((row["fcf_quality"], 0.50))
            if row["valuation_percentile"] is not None:
                components.append((row["valuation_percentile"] / 10, 0.30))
            if row["sector_percentile"] is not None:
                components.append((row["sector_percentile"] / 10, 0.20))

            total_weight = sum(weight for _, weight in components)
            row["composite_score"] = (
                round(
                    sum(score * weight for score, weight in components)
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

        # Hitra rastna podjetja: P/S + PEG + rast.
        # Zrelejši sektorji: uporabljamo razpoložljivi sektorski multiple.
        sector = data["sector"]
        growth = data.get("revenue_growth")

        if sector in (
            "SaaS / Software",
            "Semiconductors / Hardware",
            "Cybersecurity",
            "Large Tech / Internet",
        ):
            if data.get("ps") is None or not 1 <= data["ps"] <= 20:
                continue
            if data.get("peg") is None or not 0 < data["peg"] <= 2.8:
                continue
            if growth is None or growth < 0.12:
                continue
        else:
            # Za druge skupine ne vsiljujemo istih P/S in PEG pragov.
            if growth is None or growth < 0.03:
                continue
            metric = get_sector_valuation_metric(data)
            if metric["value"] is None:
                continue

        if (
            data.get("debt") is not None
            and data.get("net_cash") is not None
            and data["debt"] > 0
            and data["net_cash"] < 0
        ):
            continue

        data["fcf_quality"] = fcf_quality_score(data)
        data["data_reliability"], data["data_flags"] = data_reliability_score(data)
        data["valuation_metric"] = get_sector_valuation_metric(data)

        rows.append(data)

    rows = calculate_peer_scores(rows)
    rows = [
        row for row in rows
        if row.get("composite_score") is not None
    ]
    rows.sort(
        key=lambda row: (
            row["composite_score"],
            row["data_reliability"],
            row["ticker"],
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


@st.cache_data(ttl=1800, show_spinner=False)
def get_atr_value(ticker):
    try:
        hist = yf.Ticker(ticker).history(
            period="3mo",
            interval="1d",
            auto_adjust=True,
        )
        if hist is None or len(hist) < 20:
            return None

        high = hist["High"].astype(float)
        low = hist["Low"].astype(float)
        close = hist["Close"].astype(float)
        previous_close = close.shift(1)

        true_range = pd.concat(
            [
                high - low,
                (high - previous_close).abs(),
                (low - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1)

        atr = safe_float(true_range.rolling(14).mean().iloc[-1])
        return atr if atr and atr > 0 else None
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

        # Vključimo premarket in redno sejo; after-hours izločimo.
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

    typical_price = (high + low + close) / 3
    cumulative_volume = volume.cumsum().replace(0, float("nan"))

    return (typical_price * volume).cumsum() / cumulative_volume


def same_time_volume_ratio(history, timestamp, session_bars, index_in_session):
    """
    Primerja volumen s svečami ob isti uri v zadnjih petih sejah iste vrste.
    Premarket se primerja samo s premarketom.
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
    True: earnings datum je v naslednjih dneh.
    False: preverjeni podatki ne kažejo earnings v obdobju.
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

    # Uporabi samo zaključene petminutne sveče.
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

    previous_close = get_previous_regular_close(history, session_date)
    if previous_close is None:
        return None

    vwap_series = anchored_vwap_series(bars)
    if vwap_series.empty:
        return None

    earnings_status = earnings_within_days(ticker, 5)
    if earnings_status is not False:
        return None

    # Poišče zadnji veljaven signal, tudi če zadnja sveča ni več signalna.
    valid_signal = None

    for index in range(14, len(bars)):
        stamp = bars.index[index]
        close = safe_float(bars["Close"].iloc[index])
        open_price = safe_float(bars["Open"].iloc[index])
        previous_bar_close = safe_float(bars["Close"].iloc[index - 1])
        current_vwap = safe_float(vwap_series.iloc[index])
        previous_vwap = safe_float(vwap_series.iloc[index - 1])

        if any(value is None for value in (
            close,
            open_price,
            previous_bar_close,
            current_vwap,
            previous_vwap,
        )):
            continue

        gap_pct = (close / previous_close - 1) * 100
        if not -8.0 <= gap_pct <= -1.0:
            continue

        crossed_up = (
            previous_bar_close <= previous_vwap
            and close > current_vwap
        )
        green_candle = close > open_price
        if not crossed_up or not green_candle:
            continue

        rsi = calculate_rsi(bars["Close"].iloc[:index + 1])
        if rsi is None or rsi >= 35:
            continue

        volume_ratio = same_time_volume_ratio(
            history,
            stamp,
            bars,
            index,
        )
        if volume_ratio is None or volume_ratio < 1.3:
            continue

        momentum = (close / previous_bar_close - 1) * 100
        if momentum <= 0:
            continue

        vwap_distance = (close / current_vwap - 1) * 100
        score = 6.0
        score += min(max(volume_ratio - 1.3, 0) * 0.5, 1.5)
        score += min(max(momentum, 0) * 0.25, 1.0)
        score -= market["penalty"]
        score = round(max(0.0, min(10.0, score)), 1)

        if score < 6.0:
            continue

        valid_signal = {
            "Ticker": ticker,
            "Čas": stamp.strftime("%H:%M ET"),
            "Seja": "PREMARKET" if session_kind == "premarket" else "REDNA SEJA",
            "Cena": round(close, 2),
            "Gap proti prejšnjemu close %": round(gap_pct, 2),
            "VWAP": round(current_vwap, 2),
            "Odstopanje od VWAP %": round(vwap_distance, 2),
            "Volumen proti isti uri x": round(volume_ratio, 2),
            "RSI 5m": round(rsi, 1),
            "Momentum %": round(momentum, 2),
            "Ocena filtra": score,
        }

    return valid_signal


@st.cache_data(ttl=90, show_spinner=False)
def scan_top_reversal(universe, n=5):
    now_ny = datetime.now(NY_TZ)
    results = []

    for ticker in universe:
        history = get_intraday_history(ticker, "5d")
        if history is None or history.empty:
            continue

        signal = build_reversal_signal(
            ticker,
            history,
            now_ny.date(),
            now_ny,
        )
        if signal:
            results.append(signal)

    results.sort(
        key=lambda row: row["Ocena filtra"],
        reverse=True,
    )
    return results[:n]


# ============================================================
# AI ANALITIK
# ============================================================

def get_gemini_comment(api_key, prompt):
    api_key = api_key.strip()
    if not api_key:
        raise ValueError("Vnesi Gemini API ključ.")

    response = requests.get(
        "https://generativelanguage.googleapis.com/v1beta/models",
        params={"key": api_key},
        timeout=20,
    )
    response.raise_for_status()

    models = response.json().get("models", [])
    model_names = [
        model["name"].split("/")[-1]
        for model in models
        if "generateContent" in model.get("supportedGenerationMethods", [])
    ]

    if not model_names:
        raise RuntimeError(
            "API ni vrnil modela, ki podpira generateContent."
        )

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    last_error = "Klic API-ja ni uspel."

    for model_name in model_names:
        try:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model_name}:generateContent"
            )
            result = requests.post(
                url,
                params={"key": api_key},
                json=payload,
                timeout=35,
            )

            if result.status_code == 200:
                parts = (
                    result.json()
                    .get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [])
                )
                text = "\n".join(
                    part.get("text", "")
                    for part in parts
                    if part.get("text")
                )
                if text:
                    return model_name, text

            last_error = (
                f"{model_name}: HTTP {result.status_code} "
                f"{result.text[:250]}"
            )
        except Exception as error:
            last_error = str(error)

    raise RuntimeError(last_error)


# ============================================================
# GLAVNI PRIKAZ
# ============================================================

now_ljubljana = datetime.now(LJ_TZ)

st.markdown(
    f"""
    <div style="border-bottom:1px solid rgba(255,255,255,0.08);
                padding-bottom:12px;margin-bottom:18px;">
      <h1 style="margin:0;">
        <span style="color:#F59E0B;">THE VALUE LEDGER</span>
        <span style="color:#60A5FA;">2.0</span>
      </h1>
      <p style="color:#94A3B8;">
        Kvantitativni terminal · {now_ljubljana.strftime("%d.%m.%Y %H:%M")} Ljubljana
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown("### Nastavitve")
gemini_api_key = st.sidebar.text_input(
    "Gemini API ključ (neobvezno)",
    type="password",
)
st.sidebar.caption(f"Unikatni tickerji: {len(AI_UNIVERSE)}")
st.sidebar.caption("Yahoo Finance podatki so lahko zakasnjeni ali nepopolni.")
st.sidebar.markdown("---")

market = get_market_regime()
rotation = get_capital_rotation()

st.sidebar.markdown(f"**Tržni režim:** {market['regime']}")
if market["spy_chg"] is not None:
    st.sidebar.caption(f"SPY 20d: {market['spy_chg']:+.2f}%")

held_ticker = st.sidebar.selectbox(
    "Delnica za večerni pregled",
    options=list(TICKERS_CONFIG.keys()),
    index=list(TICKERS_CONFIG.keys()).index("CRWD"),
)

st.title("Value Ledger 2.0")
st.caption(
    "Ocene so hevristične, ne potrjene napovedi donosa. "
    "Skener ne oddaja naročil."
)

if st.button("Osveži skene"):
    scan_long_universe.clear()
    scan_top_reversal.clear()
    get_fundamental_data.clear()
    get_intraday_history.clear()
    get_capital_rotation.clear()
    get_market_regime.clear()
    st.rerun()

with st.spinner("Skeniram fundamentalne in intraday podatke..."):
    long_candidates = scan_long_universe(tuple(AI_UNIVERSE))
    reversal_candidates = scan_top_reversal(tuple(AI_UNIVERSE), 5)

best_long = long_candidates[0] if long_candidates else None
best_reversal = reversal_candidates[0] if reversal_candidates else None


# ============================================================
# DINAMIČNI ZLATI LONG IN ZELENI OBRAT
# ============================================================

long_col, reversal_col = st.columns(2)

with long_col:
    if best_long:
        item = best_long
        ticker = item["ticker"]
        price_context = get_three_year_price_context(ticker)
        atr = get_atr_value(ticker)

        stop = (
            item["price"] - 1.5 * atr
            if atr and item.get("price")
            else None
        )
        target1 = (
            item["price"] + 1.5 * atr
            if atr and item.get("price")
            else None
        )
        target2 = (
            item["price"] + 2.5 * atr
            if atr and item.get("price")
            else None
        )

        flags_text = (
            "; ".join(item["data_flags"])
            if item["data_flags"]
            else "brez samodejnih opozoril"
        )
        atr_text = (
            f"ATR {display_value(atr)} · STOP {display_value(stop)} · "
            f"T1 {display_value(target1)} · T2 {display_value(target2)}"
            if atr
            else "ATR ravni niso na voljo"
        )

        st.markdown(
            f"""
            <div class="hero-long">
              <div style="color:#FBBF24;font-size:0.78rem;font-weight:700;">
                FUNDAMENTALNI LONG · DINAMIČNA PRIMERJAVA
              </div>
              <div style="font-size:1.55rem;font-weight:700;color:#FFFFFF;margin-top:5px;">
                {html.escape(ticker)}
              </div>
              <div style="color:#CBD5E1;font-size:0.86rem;margin-top:2px;">
                {html.escape(item["name"])} · {html.escape(item["sector"])}
              </div>
              <div style="color:#F8FAFC;font-size:1.02rem;margin-top:10px;">
                Cena {display_value(item.get("price"))} ·
                Skupna hevristika {item["composite_score"]}/10
              </div>
              <div style="color:#CBD5E1;font-size:0.78rem;margin-top:8px;line-height:1.75;">
                Kakovost FCF {display_value(item.get("fcf_quality"), 1)}/10 ·
                Vrednotenje {display_value(item.get("valuation_score"), 1)}/10<br>
                Sektorski percentil {display_value(item.get("sector_percentile"), 0)} ·
                Zanesljivost podatkov {item["data_reliability"]}/100<br>
                Primerljivih podjetij: {item["peer_count"]}<br>
                {html.escape(atr_text)}<br>
                Podatkovna opozorila: {html.escape(flags_text)}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            "Sektorski percentil velja le za tickerje iste ročno določene "
            "skupine, ki so prestali filtre."
        )
    else:
        st.markdown(
            """
            <div class="hero-long">
              <div style="color:#FBBF24;font-size:0.78rem;font-weight:700;">
                FUNDAMENTALNI LONG · DINAMIČNA PRIMERJAVA
              </div>
              <div style="font-size:1.35rem;font-weight:700;color:#FFFFFF;margin-top:12px;">
                NI STROGEGA KANDIDATA
              </div>
              <div style="color:#CBD5E1;font-size:0.82rem;margin-top:10px;">
                Noben ticker ni prestal filtrov ali imel dovolj podatkov
                za izračun ločenih ocen.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with reversal_col:
    if best_reversal:
        item = best_reversal
        st.markdown(
            f"""
            <div class="hero-reversal">
              <div style="color:#6EE7B7;font-size:0.78rem;font-weight:700;">
                NAJBOLJŠE UJEMANJE INTRADAY FILTROV · NI NAPOVED
              </div>
              <div style="font-size:1.55rem;font-weight:700;color:#FFFFFF;margin-top:5px;">
                {html.escape(item["Ticker"])}
              </div>
              <div style="color:#CBD5E1;font-size:0.86rem;margin-top:2px;">
                {html.escape(item["Seja"])} · {html.escape(item["Čas"])}
              </div>
              <div style="color:#F8FAFC;font-size:1.02rem;margin-top:10px;">
                Cena {item["Cena"]} · Ocena filtra {item["Ocena filtra"]}/10
              </div>
              <div style="color:#CBD5E1;font-size:0.78rem;margin-top:8px;line-height:1.75;">
                Gap {item["Gap proti prejšnjemu close %"]:+.2f}% ·
                VWAP {item["VWAP"]} ({item["Odstopanje od VWAP %"]:+.2f}%)<br>
                Volumen proti isti uri {item["Volumen proti isti uri x"]}x ·
                RSI {item["RSI 5m"]} · Momentum {item["Momentum %"]:+.2f}%<br>
                Filtri vključujejo zeleno svečo, VWAP reclaim in preverjanje earnings.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="hero-reversal">
              <div style="color:#6EE7B7;font-size:0.78rem;font-weight:700;">
                NAJBOLJŠE UJEMANJE INTRADAY FILTROV · NI NAPOVED
              </div>
              <div style="font-size:1.35rem;font-weight:700;color:#FFFFFF;margin-top:12px;">
                NI STROGEGA KANDIDATA
              </div>
              <div style="color:#CBD5E1;font-size:0.82rem;margin-top:10px;">
                Noben ticker trenutno ne prestane vseh pogojev.
                Skener kandidata ne izbere na silo.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.caption(
    "Zlata kartica pokaže najvišje uvrščen fundamentalni kandidat. "
    "Zelena kartica pokaže najvišje uvrščeni intraday reversal kandidat. "
    "Nobena kartica ni samodejno priporočilo za nakup."
)


# ============================================================
# SEKTORSKA ROTACIJA
# ============================================================

st.subheader("Capital Rotation Radar")

detail_html = ""
if rotation["pair_detail"]:
    detail_html = (
        "<div style='color:#94A3B8;font-size:0.82rem;margin-top:6px;'>"
        + html.escape(rotation["pair_detail"])
        + "</div>"
    )

st.markdown(
    "<div class='ledger-card'>"
    "<div style='color:#FBBF24;font-weight:700;font-size:1rem;'>"
    + html.escape(rotation["pair"])
    + "</div>"
    "<div style='color:#94A3B8;font-size:0.82rem;margin-top:6px;'>"
    "Tržni režim: "
    + html.escape(market["regime"])
    + "</div>"
    + detail_html
    + "</div>",
    unsafe_allow_html=True,
)

if rotation["rows"]:
    render_dark_table(pd.DataFrame(rotation["rows"]))
else:
    st.info("Sektorski podatki trenutno niso na voljo.")

st.caption(
    "ETF-ji kažejo relativno gibanje cen proti SPY, ne neposrednih "
    "nakupnih ali prodajnih tokov Wall Streeta."
)


# ============================================================
# TOP 5 LONG: LOČENE OCENE
# ============================================================

st.subheader("TOP 5 Long · kakovost, vrednotenje in primerjava sektorja")
st.caption(
    "Točkovanje je hevristično in še ni potrjeno z večletnim backtestom. "
    "Različni sektorji uporabljajo različne razpoložljive večkratnike."
)

if long_candidates:
    long_table = []

    for item in long_candidates[:5]:
        price_context = get_three_year_price_context(item["ticker"])
        growth = item.get("revenue_growth")
        metric = item["valuation_metric"]
        atr = get_atr_value(item["ticker"])

        stop = (
            item["price"] - 1.5 * atr
            if atr and item.get("price")
            else None
        )
        target1 = (
            item["price"] + 1.5 * atr
            if atr and item.get("price")
            else None
        )

        long_table.append({
            "Ticker": item["ticker"],
            "Podjetje": item["name"],
            "Skupina": item["sector"],
            "Peerji": item["peer_count"],
            "Skupna ocena / 10": item["composite_score"],
            "Kakovost FCF / 10": display_value(item.get("fcf_quality"), 1),
            "Vrednotenje / 10": display_value(item.get("valuation_score"), 1),
            "Sektorski percentil": display_value(
                item.get("sector_percentile"), 0, "%"
            ),
            "Zanesljivost podatkov": f"{item['data_reliability']}/100",
            "FCF pozitivna leta": (
                f"{item['positive_fcf_years']}/{item['fcf_years']}"
                if item["fcf_years"]
                else "ni podatka"
            ),
            "Mediana FCF marže %": display_value(
                item.get("median_fcf_margin"), 1, "%"
            ),
            "Pretvorba CFO/dobiček": display_value(
                item.get("median_cash_conversion"), 2, "x"
            ),
            "SBC/prihodki %": display_value(
                item.get("sbc_burden"), 1, "%"
            ),
            "Primerjalni multiple": metric["name"],
            "Vrednost multipla": display_value(metric["value"]),
            "P/S": display_value(item.get("ps")),
            "PEG": display_value(item.get("peg")),
            "Rast prihodkov %": display_value(
                growth * 100 if growth is not None else None,
                1,
                "%",
            ),
            "FCF yield %": display_value(item.get("fcf_yield"), 1, "%"),
            "WS približek / 10": display_value(
                wall_street_score(item), 1
            ),
            "Cena proti 3y mediani %": display_value(
                price_context, 1, "%"
            ),
            "ATR STOP": display_value(stop),
            "ATR T1": display_value(target1),
            "Opozorila": (
                "; ".join(item["data_flags"])
                if item["data_flags"]
                else "—"
            ),
        })

    render_dark_table(pd.DataFrame(long_table))
else:
    st.info(
        "Ni kandidatov, ki bi prestali fundamentalne in likvidnostne filtre."
    )

st.caption(
    "Zanesljivost meri prisotnost izbranih vhodnih polj, ne neodvisne "
    "revizije njihove pravilnosti. Primerjava z 3-letno mediano je samo "
    "primerjava cene delnice, ne zgodovinskega P/S."
)


# ============================================================
# TOP 5 INTRADAY REVERSAL
# ============================================================

st.subheader("TOP 5 Intraday Reversal")
st.caption(
    "Premarket VWAP se računa ločeno od začetka premarketa; redni VWAP se "
    "ponastavi ob 09:30 ET. Volumen se primerja z isto 5-minutno uro "
    "v preteklih sejah iste vrste."
)

if st.button("Osveži intraday skener"):
    scan_top_reversal.clear()
    get_intraday_history.clear()
    st.rerun()

reversal_candidates = scan_top_reversal(tuple(AI_UNIVERSE), 5)
best_reversal = reversal_candidates[0] if reversal_candidates else None

if reversal_candidates:
    render_dark_table(pd.DataFrame(reversal_candidates))
else:
    st.info(
        "NI STROGEGA KANDIDATA. Filter zahteva gap od -1 % do -8 %, "
        "dejanski prehod zaključene sveče izpod VWAP-a nad njega, zeleno "
        "svečo, RSI pod 35, volumen vsaj 1,3× glede na isto uro, pozitiven "
        "momentum in uspešno preverjene earnings podatke."
    )

st.warning(
    "Premarket je lahko slabo likviden, podatki pa nepopolni. "
    "Ujemanje s filtri ni zagotovilo dobička ali potrditev za nakup."
)


# ============================================================
# DIAGNOSTIČNI BACKTEST
