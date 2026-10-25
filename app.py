import html
import math
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st
import yfinance as yf


# ============================================================
# NASTAVITVE IN VIDEZ
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
        background-color:#06070B !important;
        color:#E2E8F0 !important;
        font-family:'Plus Jakarta Sans',sans-serif !important;
    }
    section[data-testid="stSidebar"] {
        background-color:#0A0D14 !important;
        border-right:1px solid rgba(255,255,255,.06);
    }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
        font-family:'Space Grotesk',sans-serif !important;
        color:#E2E8F0 !important;
    }
    [data-testid="stCaptionContainer"] { color:#94A3B8 !important; }
    .hero-long {
        background:linear-gradient(145deg,rgba(48,34,10,.72),rgba(13,17,28,.96));
        border:1px solid rgba(245,158,11,.58);
        border-radius:18px;
        padding:20px 24px;
        min-height:210px;
    }
    .hero-reversal {
        background:linear-gradient(145deg,rgba(9,43,39,.75),rgba(13,17,28,.96));
        border:1px solid rgba(16,185,129,.48);
        border-radius:18px;
        padding:20px 24px;
        min-height:210px;
    }
    .ledger-card {
        background:linear-gradient(145deg,#0D111C,#090B12);
        border:1px solid rgba(255,255,255,.08);
        border-radius:16px;
        padding:20px 24px;
        margin:8px 0 18px 0;
    }
    div.stButton > button {
        background:linear-gradient(135deg,#F59E0B 0%,#D97706 100%) !important;
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
# UNIVERZUM: 150 RAZLIČNIH TICKERJEV
# ============================================================

TICKER_CANDIDATES = [
    # SaaS, programska oprema, cloud
    "MNDY", "CRWD", "SNOW", "HUBS", "DDOG", "TEAM", "NOW", "PANW",
    "PLTR", "CRM", "ADBE", "SHOP", "NET", "ZS", "OKTA", "MDB",
    "ESTC", "PATH", "WDAY", "CFLT", "DOCN", "GTLB", "TOST", "BILL",
    "ASAN", "IOT", "FSLY", "DT", "BSY", "PCOR", "NCNO", "ZM",
    "DOCU", "TWLO", "PD", "DBX", "SMAR", "UPWK", "SPT", "APPN",
    "PEGA", "FROG", "RNG", "VEEV", "TYL", "PTC", "ADSK", "TRMB",

    # Velika tehnologija in internet
    "AAPL", "MSFT", "META", "AMZN", "GOOGL", "NFLX", "TSLA",
    "UBER", "ABNB", "DASH", "SPOT", "RBLX", "TTD", "ROKU",
    "PINS", "SNAP", "MTCH", "DKNG", "LYFT", "EBAY",

    # Polprevodniki in strojna oprema
    "NVDA", "AVGO", "AMD", "TSM", "MU", "QCOM", "ARM", "SMCI",
    "ANET", "MRVL", "SNPS", "CDNS", "ANSS", "ALAB", "LITE",
    "COHR", "VRT", "NTNX", "PSTG", "STX", "WDC", "TXN", "ADI",
    "NXPI", "MCHP", "ON", "INTC", "ASML", "AMAT", "LRCX",
    "KLAC", "DELL", "CSCO", "HPE", "HPQ", "GLW", "TER", "KEYS",

    # Kibernetska varnost
    "CHKP", "CYBR", "TENB", "VRNS", "QLYS", "FTNT", "AKAM",
    "VRSN", "GEN", "S",

    # Finance in fintech
    "COIN", "HOOD", "XYZ", "PYPL", "SOFI", "AFRM", "MELI",
    "SE", "NU", "V", "MA", "GLBE", "JPM", "GS", "MS", "C",
    "BAC", "SCHW", "ICE", "CME",

    # Zdravstvo
    "ISRG", "DXCM", "PODD", "EXAS", "ILMN", "ALGN", "MDT",
    "SYK", "BSX", "ABT", "VRTX", "REGN", "LLY", "NVO", "UNH",

    # Industrija, energija, potrošnja in drugi
    "CAT", "DE", "ETN", "GE", "HON", "PH", "RTX", "LMT",
    "XOM", "CVX", "SLB", "FSLR", "ENPH", "NXT", "COST",
    "WMT", "HD", "LOW", "MCD", "NKE", "KO", "PG", "F",
    "GM", "RIVN", "LCID", "CVNA", "UPST", "Z", "W",
]

AI_UNIVERSE = list(dict.fromkeys(TICKER_CANDIDATES))[:150]

# Ročno določene primerjalne skupine. Niso uradne sektorske klasifikacije.
SECTOR_GROUPS = {
    "SaaS / Software": [
        "MNDY", "SNOW", "HUBS", "DDOG", "TEAM", "NOW", "CRM", "ADBE",
        "SHOP", "NET", "ZS", "OKTA", "MDB", "ESTC", "PATH", "WDAY",
        "CFLT", "DOCN", "GTLB", "BILL", "ASAN", "IOT", "FSLY", "DT",
        "BSY", "PCOR", "NCNO", "ZM", "DOCU", "TWLO", "PD", "DBX",
        "SMAR", "UPWK", "SPT", "APPN", "PEGA", "FROG", "RNG", "PLTR",
        "VEEV", "TYL", "PTC", "ADSK", "TRMB",
    ],
    "Cybersecurity": [
        "CRWD", "PANW", "CHKP", "CYBR", "TENB", "VRNS",
        "QLYS", "FTNT", "AKAM", "VRSN", "GEN", "S",
    ],
    "Semiconductors / Hardware": [
        "NVDA", "AVGO", "AMD", "TSM", "MU", "QCOM", "ARM", "SMCI",
        "ANET", "MRVL", "SNPS", "CDNS", "ANSS", "ALAB", "LITE",
        "COHR", "VRT", "NTNX", "PSTG", "STX", "WDC", "TXN", "ADI",
        "NXPI", "MCHP", "ON", "INTC", "ASML", "AMAT", "LRCX",
        "KLAC", "DELL", "CSCO", "HPE", "HPQ", "GLW", "TER", "KEYS",
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

# Enak multiple za vsako skupino. Različnih multiple-ov ne mešamo med sabo.
SECTOR_MULTIPLE = {
    "SaaS / Software": "P/S",
    "Cybersecurity": "P/S",
    "Semiconductors / Hardware": "EV/EBITDA",
    "Large Tech / Internet": "EV/EBITDA",
    "Financials / Fintech": "P/B",
    "Healthcare": "EV/EBITDA",
    "Industrials": "EV/EBITDA",
    "Energy": "EV/EBITDA",
    "Consumer": "EV/EBITDA",
}


def sector_group(ticker):
    for name, members in SECTOR_GROUPS.items():
        if ticker in members:
            return name
    return "Other / unclassified"


# ============================================================
# POMOŽNE FUNKCIJE
# ============================================================

def as_float(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def fmt(value, digits=2, suffix=""):
    if value is None:
        return "—"
    try:
        return f"{float(value):,.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return "—"


def render_dark_table(frame):
    if frame is None or frame.empty:
        st.info("Ni podatkov za prikaz.")
        return

    header = "".join(
        f"<th>{html.escape(str(col))}</th>"
        for col in frame.columns
    )
    body = []

    for _, row in frame.iterrows():
        cells = []
        for value in row.tolist():
            text = "—" if pd.isna(value) else str(value)
            cells.append(f"<td>{html.escape(text)}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")

    # CSS je navaden niz, ne f-string.
    table_html = (
        '<div style="overflow-x:auto;border:1px solid #263044;'
        'border-radius:10px;margin:8px 0 18px 0;">'
        '<table style="border-collapse:collapse;width:100%;'
        'background:#0D111C;color:#CBD5E1;font-size:0.82rem;">'
        '<thead><tr style="background:#151B29;color:#F8FAFC;">'
        + header
        + "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></div>"
        "<style>"
        "table th,table td{border:1px solid #202838;padding:8px 10px;"
        "text-align:left;white-space:nowrap;}"
        "table tbody tr:nth-child(even){background:#101522;}"
        "</style>"
    )
    st.markdown(table_html, unsafe_allow_html=True)


def get_statement_row(frame, names):
    if frame is None or frame.empty:
        return None

    labels = {
        str(index).strip().lower().replace("_", " "): index
        for index in frame.index
    }

    for name in names:
        key = name.strip().lower().replace("_", " ")
        if key in labels:
            return frame.loc[labels[key]]

    for normalized, original in labels.items():
        if any(
            name.strip().lower().replace("_", " ") in normalized
            for name in names
        ):
            return frame.loc[original]

    return None


def annual_values(frame, names):
    row = get_statement_row(frame, names)
    if row is None:
        return {}

    values = {}
    for column, value in row.items():
        number = as_float(value)
        if number is None:
            continue
        try:
            values[pd.Timestamp(column).year] = number
        except Exception:
            continue
    return values


def midrank_percentile(values, target, lower_is_better=False):
    clean = [
        value for value in values
        if value is not None and math.isfinite(value)
    ]
    if target is None or len(clean) < 5:
        return None

    less = sum(value < target for value in clean)
    equal = sum(value == target for value in clean)

    # Mid-rank prepreči avtomatični 100. percentil pri izenačenih vrednostih.
    percentile = (less + 0.5 * equal) / len(clean) * 100

    if lower_is_better:
        percentile = 100 - percentile

    return round(max(0, min(100, percentile)))


# ============================================================
# TRŽNI REŽIM IN SEKTORSKA ROTACIJA
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def get_market_regime():
    try:
        frame = yf.Ticker("SPY").history(
            period="6mo",
            interval="1d",
            auto_adjust=True,
        )
        if frame is None or len(frame) < 60:
            return {"regime": "NEZNANO", "change20": None, "penalty": 0.0}

        close = frame["Close"].dropna().astype(float)
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
            "change20": round(change20, 2),
            "penalty": penalty,
        }
    except Exception:
        return {"regime": "NEZNANO", "change20": None, "penalty": 0.0}


@st.cache_data(ttl=900, show_spinner=False)
def get_capital_rotation():
    etfs = {
        "SaaS / software (IGV)": "IGV",
        "Polprevodniki (SMH)": "SMH",
        "Kibernetska varnost (CIBR)": "CIBR",
        "Nasdaq (QQQ)": "QQQ",
        "Finance (XLF)": "XLF",
        "Zdravstvo (XLV)": "XLV",
        "Energija (XLE)": "XLE",
        "Industrija (XLI)": "XLI",
        "Potrošnja diskrecijska (XLY)": "XLY",
        "Osnovna potrošnja (XLP)": "XLP",
        "Materiali (XLB)": "XLB",
        "Utilities (XLU)": "XLU",
        "Small caps (IWM)": "IWM",
    }

    closes = {}
    for ticker in list(etfs.values()) + ["SPY"]:
        try:
            frame = yf.Ticker(ticker).history(
                period="8mo",
                interval="1d",
                auto_adjust=True,
            )
            if frame is not None and not frame.empty:
                closes[ticker] = frame["Close"].dropna().astype(float)
        except Exception:
            continue

    if "SPY" not in closes:
        return {"rows": [], "rotation": "NI PODATKOV", "detail": ""}

    def relative_return(series, benchmark, days):
        joined = pd.concat(
            [series.rename("sector"), benchmark.rename("spy")],
            axis=1,
            join="inner",
        ).dropna()
        if len(joined) <= days:
            return None

        sector_return = (
            joined["sector"].iloc[-1] / joined["sector"].iloc[-1 - days] - 1
        ) * 100
        spy_return = (
            joined["spy"].iloc[-1] / joined["spy"].iloc[-1 - days] - 1
        ) * 100
        return float(sector_return - spy_return)

    rows = []
    for label, ticker in etfs.items():
        if ticker not in closes:
            continue

        r5 = relative_return(closes[ticker], closes["SPY"], 5)
        r20 = relative_return(closes[ticker], closes["SPY"], 20)
        r60 = relative_return(closes[ticker], closes["SPY"], 60)

        if r5 is None or r20 is None or r60 is None:
            continue

        if r5 > 0 and r20 > 0 and r60 < 0:
            status = "KREPI"
        elif r20 > 0 and r60 > 0:
            status = "RELATIVNO VODI"
        elif r5 < 0 and r20 < 0 and r60 > 0:
            status = "SLABI"
        elif r20 < 0:
            status = "ZAOSTAJA"
        else:
            status = "MEŠANO"

        rows.append({
            "Sektor / ETF": label,
            "Rel. 5d % vs SPY": round(r5, 1),
            "Rel. 20d % vs SPY": round(r20, 1),
            "Rel. 60d % vs SPY": round(r60, 1),
            "Oznaka": status,
        })

    rows.sort(key=lambda item: item["Rel. 20d % vs SPY"], reverse=True)

    rotation = "NI PODATKOV"
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
                rotation = "MOŽEN ZAČETEK RELATIVNE ROTACIJE SEMIS → SAAS"
            elif change20 > 0 and change60 > 0 and above_sma20:
                rotation = "SAAS RELATIVNO VODI SEMIS"
            elif change20 < 0 and change60 > 0:
                rotation = "SAAS RELATIVNO SLABI PROTI SEMIS"
            elif change20 < 0 and not above_sma20:
                rotation = "SEMIS RELATIVNO VODI SAAS"
            else:
                rotation = "NI JASNE RELATIVNE ROTACIJE"

            detail = (
                f"IGV/SMH: 20d {change20:+.1f}%, "
                f"60d {change60:+.1f}%; nad SMA20: "
                f"{'DA' if above_sma20 else 'NE'}"
            )

    return {"rows": rows, "rotation": rotation, "detail": detail}


# ============================================================
# FUNDAMENTI: FCF, VREDNOTENJE, SEKTORSKI PEERJI
# ============================================================

@st.cache_data(ttl=1800, show_spinner=False)
def get_fundamental_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}

        def number(key):
            return as_float(info.get(key))

        price = number("currentPrice") or number("regularMarketPrice")
        market_cap = number("marketCap")
        average_volume = number("averageVolume")
        dollar_volume = (
            price * average_volume
            if price is not None and average_volume is not None
            else None
        )

        cash = number("totalCash")
        debt = number("totalDebt")
        net_cash = cash - debt if cash is not None and debt is not None else None

        try:
            cashflow = stock.cashflow
        except Exception:
            cashflow = None

        try:
            income = stock.income_stmt
        except Exception:
            income = None

        cfo = annual_values(
            cashflow,
            [
                "Operating Cash Flow",
                "Total Cash From Operating Activities",
                "Cash Flow From Continuing Operating Activities",
            ],
        )
        capex = annual_values(
            cashflow,
            ["Capital Expenditure", "Capital Expenditures"],
        )
        sbc = annual_values(
            cashflow,
            ["Stock Based Compensation", "Share Based Compensation"],
        )
        net_income = annual_values(
            income,
            [
                "Net Income",
                "Net Income Common Stockholders",
                "Net Income From Continuing Operations",
            ],
        )
        revenue = annual_values(
            income,
            ["Total Revenue", "Operating Revenue", "Revenue"],
        )
        ebitda_series = annual_values(
            income,
            ["EBITDA", "Normalized EBITDA"],
        )

        years = sorted(set(cfo) & set(capex) & set(net_income) & set(revenue))[-5:]
        annual = []

        for year in years:
            annual.append({
                "year": year,
                "cfo": cfo[year],
                "capex": abs(capex[year]),
                "fcf": cfo[year] - abs(capex[year]),
                "net_income": net_income[year],
                "revenue": revenue[year],
                "sbc": abs(sbc[year]) if year in sbc else None,
                "ebitda": ebitda_series.get(year),
            })

        annual.sort(key=lambda row: row["year"])
        fcf_years = len(annual)
        positive_fcf_years = sum(row["fcf"] > 0 for row in annual)

        fcf_margins = [
            row["fcf"] / row["revenue"] * 100
            for row in annual
            if row["revenue"] > 0
        ]
        cash_conversions = [
            row["cfo"] / row["net_income"]
            for row in annual
            if row["net_income"] > 0
        ]
        sbc_burdens = [
            row["sbc"] / row["revenue"] * 100
            for row in annual
            if row["sbc"] is not None and row["revenue"] > 0
        ]

        median_fcf_margin = (
            float(pd.Series(fcf_margins).median()) if fcf_margins else None
        )
        median_cash_conversion = (
            float(pd.Series(cash_conversions).median())
            if cash_conversions
            else None
        )
        median_sbc_burden = (
            float(pd.Series(sbc_burdens).median()) if sbc_burdens else None
        )

        growth_info = number("revenueGrowth")
        if growth_info is not None and growth_info > 1:
            growth_info /= 100

        annual_growth = None
        if len(annual) >= 2 and annual[-2]["revenue"] > 0:
            annual_growth = annual[-1]["revenue"] / annual[-2]["revenue"] - 1

        revenue_growth = annual_growth if annual_growth is not None else growth_info
        latest_fcf = annual[-1]["fcf"] if annual else None
        latest_ebitda = annual[-1]["ebitda"] if annual else None

        fcf_yield_raw = (
            latest_fcf / market_cap * 100
            if latest_fcf is not None and market_cap and market_cap > 0
            else None
        )
        fcf_yield_valid = (
            fcf_yield_raw is not None and -10 <= fcf_yield_raw <= 20
        )

        enterprise_value = number("enterpriseValue")
        ev_ebitda = number("enterpriseToEbitda")
        if (
            (ev_ebitda is None or ev_ebitda <= 0)
            and enterprise_value is not None
            and latest_ebitda is not None
            and latest_ebitda > 0
        ):
            ev_ebitda = enterprise_value / latest_ebitda

        price_to_book = number("priceToBook")
        analyst_target = number("targetMeanPrice") or number("targetMedianPrice")
        analyst_upside = (
            (analyst_target / price - 1) * 100
            if price and analyst_target
            else None
        )

        return {
            "ticker": ticker,
            "name": info.get("shortName") or ticker,
            "sector": sector_group(ticker),
            "price": price,
            "market_cap": market_cap,
            "dollar_volume": dollar_volume,
            "cash": cash,
            "debt": debt,
            "net_cash": net_cash,
            "ps": number("priceToSalesTrailing12Months"),
            "peg": number("pegRatio"),
            "ev_ebitda": ev_ebitda,
            "price_to_book": price_to_book,
            "revenue_growth": revenue_growth,
            "annual": annual,
            "fcf_years": fcf_years,
            "positive_fcf_years": positive_fcf_years,
            "latest_fcf": latest_fcf,
            "latest_ebitda": latest_ebitda,
            "median_fcf_margin": median_fcf_margin,
            "median_cash_conversion": median_cash_conversion,
            "median_sbc_burden": median_sbc_burden,
            "fcf_yield": fcf_yield_raw if fcf_yield_valid else None,
            "fcf_yield_raw": fcf_yield_raw,
            "fcf_yield_valid": fcf_yield_valid,
            "analyst_count": number("numberOfAnalystOpinions"),
            "recommendation_mean": number("recommendationMean"),
            "analyst_upside": analyst_upside,
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


def selected_multiple(data):
    group = data["sector"]
    multiple_name = SECTOR_MULTIPLE.get(group)

    if multiple_name == "P/S":
        value = data.get("ps")
        if value is not None and value >= 1:
            return {"name": "P/S", "value": value}

    elif multiple_name == "P/B":
        value = data.get("price_to_book")
        if value is not None and value > 0:
            return {"name": "P/B", "value": value}

    elif multiple_name == "EV/EBITDA":
        value = data.get("ev_ebitda")
        if value is not None and value > 0:
            return {"name": "EV/EBITDA", "value": value}

    return {"name": multiple_name or "NI PODATKA", "value": None}


def fcf_quality(data):
    """Hevristična ocena 0–10; ne nadomesti pregleda računovodskih izkazov."""
    parts = []

    years = data.get("fcf_years", 0)
    if years >= 3:
        parts.append((
            data["positive_fcf_years"] / years * 10,
            0.25,
        ))

    margin = data.get("median_fcf_margin")
    if margin is not None:
        parts.append((max(0, min(10, margin / 2)), 0.25))

    conversion = data.get("median_cash_conversion")
    if conversion is not None:
        parts.append((max(0, min(10, conversion * 5)), 0.20))

    sbc = data.get("median_sbc_burden")
    if sbc is not None:
        parts.append((max(0, min(10, 10 - sbc / 2)), 0.15))

    net_cash = data.get("net_cash")
    if net_cash is not None:
        parts.append((8.0 if net_cash >= 0 else 3.0, 0.15))

    if len(parts) < 4:
        return None

    weight_sum = sum(weight for _, weight in parts)
    if weight_sum <= 0:
        return None

    value = sum(score * weight for score, weight in parts) / weight_sum
    return round(max(0, min(10, value)), 1)


def long_filter_reasons(data):
    reasons = []

    if not passes_liquidity(data):
        reasons.append("ni potrjene minimalne likvidnosti")
        return reasons

    if data.get("fcf_years", 0) < 3:
        reasons.append("manj kot 3 leta primerljivih izkazov")
    if data.get("latest_fcf") is None or data["latest_fcf"] <= 0:
        reasons.append("zadnji letni FCF ni pozitiven")
    if (
        data.get("fcf_years", 0) >= 3
        and data.get("positive_fcf_years", 0) < 2
    ):
        reasons.append("FCF ni pozitiven v vsaj 2 od zadnjih 3+ let")
    if (
        data.get("median_fcf_margin") is None
        or data["median_fcf_margin"] < 5
    ):
        reasons.append("mediana FCF marže je pod 5 % ali ni na voljo")
    if (
        data.get("median_cash_conversion") is None
        or data["median_cash_conversion"] < 0.7
    ):
        reasons.append("CFO/čisti dobiček je pod 0,7x ali ni na voljo")
    if (
        data.get("median_sbc_burden") is None
        or data["median_sbc_burden"] > 15
    ):
        reasons.append("SBC podatek manjka ali presega 15 % prihodkov")
    if (
        data.get("revenue_growth") is None
        or data["revenue_growth"] < 0.10
    ):
        reasons.append("rast prihodkov je pod 10 % ali ni na voljo")

    net_cash = data.get("net_cash")
    ebitda = data.get("latest_ebitda")
    if net_cash is None:
        reasons.append("neto denar/dolg ni na voljo")
    elif net_cash < 0:
        if ebitda is None or ebitda <= 0:
            reasons.append("neto dolg in ni pozitivnega EBITDA")
        elif abs(net_cash) / ebitda > 2.5:
            reasons.append("net debt/EBITDA presega 2,5x")

    return reasons


def reliability_score(data):
    """Pokritost izbranih polj, ne neodvisna potrditev njihove točnosti."""
    checks = [
        data.get("price") is not None,
        data.get("market_cap") is not None,
        data.get("dollar_volume") is not None,
        data.get("revenue_growth") is not None,
        data.get("fcf_years", 0) >= 3,
        data.get("median_fcf_margin") is not None,
        data.get("median_cash_conversion") is not None,
        data.get("median_sbc_burden") is not None,
        data.get("net_cash") is not None,
        data.get("latest_fcf") is not None,
    ]
    return round(sum(checks) / len(checks) * 100)


def analyst_snapshot(data):
    """Trenutna ocena in ciljna cena, ne zgodovinski sentimentni trend."""
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

    return round(max(0, min(10, score)), 1)


@st.cache_data(ttl=1800, show_spinner=False)
def scan_long(universe):
    """
    Peerji za vrednotenje se vzamejo iz vseh likvidnih tickerjev z veljavnim
    multiple-om, ne samo iz tistih, ki že prestanejo Long filtre.
    """
    all_data = []
    eligible = []

    for ticker in universe:
        data = get_fundamental_data(ticker)
        if not data:
            continue

        data["multiple"] = selected_multiple(data)
        data["quality"] = fcf_quality(data)
        data["reliability"] = reliability_score(data)
        data["filter_reasons"] = long_filter_reasons(data)

        if passes_liquidity(data) and data["multiple"]["value"] is not None:
            all_data.append(data)

        if not data["filter_reasons"] and data["quality"] is not None:
            eligible.append(data)

    peers_by_group = {}
    for data in all_data:
        peers_by_group.setdefault(data["sector"], []).append(data)

    ranked = []

    for candidate in eligible:
        peers = peers_by_group.get(candidate["sector"], [])
        same_multiple = [
            peer for peer in peers
            if peer["multiple"]["name"] == candidate["multiple"]["name"]
            and peer["multiple"]["value"] is not None
        ]

        # Ne izračunaj percentila iz manj kot petih primerljivih podjetij.
        if len(same_multiple) < 5:
            continue

        valuation_values = [
            peer["multiple"]["value"] for peer in same_multiple
        ]
        valuation_percentile = midrank_percentile(
            valuation_values,
            candidate["multiple"]["value"],
            lower_is_better=True,
        )

        fcf_values = [
            peer["quality"] for peer in same_multiple
            if peer["quality"] is not None
        ]
        fcf_percentile = midrank_percentile(
            fcf_values,
            candidate["quality"],
            lower_is_better=False,
        )

        growth_values = [
            peer["revenue_growth"] for peer in same_multiple
            if peer["revenue_growth"] is not None
        ]
        growth_percentile = midrank_percentile(
            growth_values,
            candidate["revenue_growth"],
            lower_is_better=False,
        )

        if (
            valuation_percentile is None
            or fcf_percentile is None
            or growth_percentile is None
        ):
            continue

        # Vse komponente so percentile 0–100 znotraj iste primerjalne skupine.
        composite = (
            0.45 * fcf_percentile
            + 0.35 * valuation_percentile
            + 0.20 * growth_percentile
        ) / 10

        result = dict(candidate)
        result["peer_count"] = len(same_multiple)
        result["valuation_percentile"] = valuation_percentile
        result["fcf_percentile"] = fcf_percentile
        result["growth_percentile"] = growth_percentile
        result["composite_score"] = round(composite, 1)
        ranked.append(result)

    ranked.sort(
        key=lambda row: (
            row["composite_score"],
            row["reliability"],
            row["ticker"],
        ),
        reverse=True,
    )
    return ranked, len(all_data)


# ============================================================
# INTRADAY PODATKI: PREMARKET LOČENO OD REDNE SEJE
# ============================================================

@st.cache_data(ttl=90, show_spinner=False)
def get_intraday_history(ticker, period="5d"):
    try:
        frame = yf.Ticker(ticker).history(
            period=period,
            interval="5m",
            prepost=True,
            auto_adjust=False,
        )
        if frame is None or frame.empty:
            return None

        needed = ["Open", "High", "Low", "Close", "Volume"]
        if any(column not in frame.columns for column in needed):
            return None

        frame = frame.dropna(subset=needed).copy()
        if frame.empty:
            return None

        if frame.index.tz is None:
            frame.index = frame.index.tz_localize("UTC")
        frame.index = frame.index.tz_convert(NY_TZ)

        # Uporabi premarket in redno sejo; after-hours izloči.
        keep = [
            time(4, 0) <= stamp.time() < time(16, 0)
            for stamp in frame.index
        ]
        frame = frame.loc[keep]
        return frame if not frame.empty else None
    except Exception:
        return None


def session_bars(frame, date_value, session):
    if frame is None or frame.empty:
        return pd.DataFrame()

    same_day = frame[
        [stamp.date() == date_value for stamp in frame.index]
    ].copy()

    if session == "premarket":
        return same_day.between_time("04:00", "09:29")

    return same_day.between_time("09:30", "15:59")


def prior_regular_close(frame, date_value):
    earlier_dates = sorted(
        {stamp.date() for stamp in frame.index if stamp.date() < date_value},
        reverse=True,
    )

    for earlier_date in earlier_dates:
        bars = session_bars(frame, earlier_date, "regular")
        if not bars.empty:
            value = as_float(bars["Close"].iloc[-1])
            if value is not None and value > 0:
                return value

    return None


def anchored_vwap(bars):
    if bars is None or bars.empty:
        return pd.Series(dtype=float)

    typical = (
        bars["High"].astype(float)
        + bars["Low"].astype(float)
        + bars["Close"].astype(float)
    ) / 3
    volume = bars["Volume"].astype(float).clip(lower=0)
    total_volume = volume.cumsum().replace(0, float("nan"))
    return (typical * volume).cumsum() / total_volume


def same_time_volume_ratio(frame, timestamp, bars, index):
    current_volume = as_float(bars["Volume"].iloc[index])
    if current_volume is None or current_volume <= 0:
        return None

    session = "premarket" if timestamp.time() < time(9, 30) else "regular"
    clock = timestamp.strftime("%H:%M")
    prior_dates = sorted({
        stamp.date() for stamp in frame.index
        if stamp.date() < timestamp.date()
    })[-5:]

    previous_volumes = []
    for prior_date in prior_dates:
        prior = session_bars(frame, prior_date, session)
        matches = [
            stamp for stamp in prior.index
            if stamp.strftime("%H:%M") == clock
        ]
        if matches:
            value = as_float(prior.loc[matches[-1], "Volume"])
            if value is not None and value > 0:
                previous_volumes.append(value)

    if not previous_volumes:
        return None

    baseline = float(pd.Series(previous_volumes).median())
    return current_volume / baseline if baseline > 0 else None


def calculate_rsi(values, period=14):
    close = pd.Series(values, dtype=float)
    if len(close) < period + 1:
        return None

    change = close.diff()
    gain = change.clip(lower=0).rolling(period).mean().iloc[-1]
    loss = (-change.clip(upper=0)).rolling(period).mean().iloc[-1]

    if pd.isna(gain) or pd.isna(loss):
        return None
    if loss == 0:
        return 100.0 if gain > 0 else 50.0

    relative_strength = gain / loss
    return float(100 - 100 / (1 + relative_strength))


def earnings_clear(ticker, days=5):
    """True = preverjeno brez bližnjih earnings; None = ni preverljivo."""
    try:
        earnings = yf.Ticker(ticker).get_earnings_dates(limit=8)
        if earnings is None or len(earnings) == 0:
            return None

        today = datetime.now(NY_TZ).date()
        for raw_date in earnings.index:
            value = pd.Timestamp(raw_date)
            if value.tzinfo is not None:
                value = value.tz_convert(None)
            delta = (value.date() - today).days
            if 0 <= delta <= days:
                return False

        return True
    except Exception:
        return None


def reversal_signal(ticker, frame, now=None):
    now = now or datetime.now(NY_TZ)
    today = now.date()

    if frame is None or frame.empty:
        return None

    day = frame[[stamp.date() == today for stamp in frame.index]]
    if day.empty:
        return None

    # Uporabi samo že zaključene 5-minutne sveče.
    completed = day[
        [stamp + timedelta(minutes=5) <= now for stamp in day.index]
    ]
    if completed.empty:
        return None

    last_stamp = completed.index[-1]
    session = "premarket" if last_stamp.time() < time(9, 30) else "regular"
    bars = session_bars(frame, today, session)
    bars = bars[
        [stamp + timedelta(minutes=5) <= now for stamp in bars.index]
    ]

    if len(bars) < 15:
        return None

    previous_close = prior_regular_close(frame, today)
    if previous_close is None or earnings_clear(ticker, 5) is not True:
        return None

    vwap = anchored_vwap(bars)
    valid = []

    for index in range(14, len(bars)):
        stamp = bars.index[index]
        close = as_float(bars["Close"].iloc[index])
        open_price = as_float(bars["Open"].iloc[index])
        previous = as_float(bars["Close"].iloc[index - 1])
        current_vwap = as_float(vwap.iloc[index])
        prior_vwap = as_float(vwap.iloc[index - 1])

        if any(value is None for value in (
            close, open_price, previous, current_vwap, prior_vwap
        )):
            continue

        # Gap glede na prejšnje redne close, ne glede na prvo premaket svečo.
        gap = (close / previous_close - 1) * 100
        if not -8 <= gap <= -1:
            continue

        # Sveča mora prečkati VWAP navzgor, zapreti zeleno in ostati blizu VWAP.
        crossed_up = previous <= prior_vwap and close > current_vwap
        green_candle = close > open_price
        distance_vwap = (close / current_vwap - 1) * 100

        if not crossed_up or not green_candle or distance_vwap < -2:
            continue

        rsi = calculate_rsi(bars["Close"].iloc[:index + 1])
        volume_ratio = same_time_volume_ratio(frame, stamp, bars, index)
        momentum = (close / previous - 1) * 100

        if rsi is None or rsi >= 35:
            continue
        if volume_ratio is None or volume_ratio < 1.3:
            continue
        if momentum <= 0:
            continue

        score = 6.0
        score += min((volume_ratio - 1.3) * 0.5, 1.5)
        score += min(momentum * 0.25, 1.0)
        score -= market["penalty"]
        score = round(max(0, min(10, score)), 1)

        if score < 6:
            continue

        valid.append({
            "Ticker": ticker,
            "Čas": stamp.strftime("%H:%M ET"),
            "Seja": "PREMARKET" if session == "premarket" else "REDNA SEJA",
            "Cena": round(close, 2),
            "Gap proti prejšnjemu close %": round(gap, 2),
            "VWAP": round(current_vwap, 2),
            "Odstopanje od VWAP %": round(distance_vwap, 2),
            "Volumen proti isti uri x": round(volume_ratio, 2),
            "RSI 5m": round(rsi, 1),
            "Momentum %": round(momentum, 2),
            "Ocena filtra": score,
        })

    return valid[-1] if valid else None


@st.cache_data(ttl=90, show_spinner=False)
def scan_reversals(universe):
    now = datetime.now(NY_TZ)
    results = []

    for ticker in universe:
        frame = get_intraday_history(ticker, "5d")
        if frame is None:
            continue

        signal = reversal_signal(ticker, frame, now)
        if signal:
            results.append(signal)

    results.sort(key=lambda row: row["Ocena filtra"], reverse=True)
    return results[:5]


# ============================================================
# ATR STOP IN CILJI
# ============================================================

@st.cache_data(ttl=1800, show_spinner=False)
def get_atr(ticker):
    try:
        frame = yf.Ticker(ticker).history(
            period="3mo",
            interval="1d",
            auto_adjust=True,
        )
        if frame is None or len(frame) < 20:
            return None

        high = frame["High"].astype(float)
        low = frame["Low"].astype(float)
        close = frame["Close"].astype(float)
        previous = close.shift(1)

        true_range = pd.concat(
            [
                high - low,
                (high - previous).abs(),
                (low - previous).abs(),
            ],
            axis=1,
        ).max(axis=1)

        value = as_float(true_range.rolling(14).mean().iloc[-1])
        return value if value is not None and value > 0 else None
    except Exception:
        return None


# ============================================================
# GEMINI: KOMENTAR PRIKAZANIH PODATKOV
# ============================================================

def gemini_comment(api_key, prompt):
    api_key = api_key.strip()
    if not api_key:
        raise ValueError("Vnesi Gemini API ključ.")

    listing = requests.get(
        "https://generativelanguage.googleapis.com/v1beta/models",
        params={"key": api_key},
        timeout=20,
    )
    listing.raise_for_status()

    models = [
        item["name"].split("/")[-1]
        for item in listing.json().get("models", [])
        if "generateContent" in item.get("supportedGenerationMethods", [])
    ]
    if not models:
        raise RuntimeError("API ni vrnil modela za generateContent.")

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    last_error = "Klic API-ja ni uspel."

    for model in models:
        try:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent"
            )
            response = requests.post(
                url,
                params={"key": api_key},
                json=payload,
                timeout=35,
            )

            if response.status_code == 200:
                parts = (
                    response.json()
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
                    return model, text

            last_error = (
                f"{model}: HTTP {response.status_code} "
                f"{response.text[:250]}"
            )
        except Exception as error:
            last_error = str(error)

    raise RuntimeError(last_error)


# ============================================================
# GLAVNI PRIKAZ
# ============================================================

market = get_market_regime()
rotation = get_capital_rotation()
now_ljubljana = datetime.now(LJ_TZ)

st.markdown(
    f"""
    <div style="border-bottom:1px solid rgba(255,255,255,.08);
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
api_key = st.sidebar.text_input(
    "Gemini API ključ (neobvezno)",
    type="password",
)
st.sidebar.caption(f"Tickerji v univerzumu: {len(AI_UNIVERSE)}")
st.sidebar.caption("Podatki Yahoo Finance so lahko zakasnjeni ali nepopolni.")
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Tržni režim:** {market['regime']}")
if market["change20"] is not None:
    st.sidebar.caption(f"SPY 20d: {market['change20']:+.2f}%")

if st.button("Osveži skene"):
    scan_long.clear()
    scan_reversals.clear()
    get_fundamental_data.clear()
    get_intraday_history.clear()
    get_market_regime.clear()
    get_capital_rotation.clear()
    st.rerun()

st.title("Value Ledger 2.0")
st.caption(
    "Ocene so hevristične, ne potrjene napovedi donosa. "
    "Aplikacija ne oddaja naročil."
)

with st.spinner("Skeniram fundamentalne in intraday podatke..."):
    long_candidates, eligible_peer_data_count = scan_long(tuple(AI_UNIVERSE))
    reversal_candidates = scan_reversals(tuple(AI_UNIVERSE))

best_long = long_candidates[0] if long_candidates else None
best_reversal = reversal_candidates[0] if reversal_candidates else None


# ============================================================
# DINAMIČNI KARTICI
# ============================================================

left, right = st.columns(2)

with left:
    if best_long:
        item = best_long
        atr = get_atr(item["ticker"])
        stop = item["price"] - 1.5 * atr if atr and item["price"] else None
        target1 = item["price"] + 1.5 * atr if atr and item["price"] else None
        target2 = item["price"] + 2.5 * atr if atr and item["price"] else None

        st.markdown(
            f"""
            <div class="hero-long">
              <div style="color:#FBBF24;font-size:.78rem;font-weight:700;">
                FUNDAMENTALNI LONG · SEKTORSKO PRIMERJANJE
              </div>
              <div style="font-size:1.55rem;font-weight:700;color:#FFFFFF;margin-top:5px;">
                {html.escape(item["ticker"])}
              </div>
              <div style="color:#CBD5E1;font-size:.86rem;margin-top:2px;">
                {html.escape(item["name"])} · {html.escape(item["sector"])}
              </div>
              <div style="color:#F8FAFC;font-size:1rem;margin-top:10px;">
                Cena {fmt(item["price"])} · Skupna ocena {item["composite_score"]}/10
              </div>
              <div style="color:#CBD5E1;font-size:.78rem;margin-top:8px;line-height:1.7;">
                Kakovost FCF {fmt(item["quality"], 1)}/10 ·
                FCF peer percentil {item["fcf_percentile"]}/100<br>
                Vrednotenje {item["multiple"]["name"]}: {fmt(item["multiple"]["value"])} ·
                Peer percentil {item["valuation_percentile"]}/100<br>
                Rast prihodkov {fmt(item["revenue_growth"] * 100, 1, "%")} ·
                Rastni percentil {item["growth_percentile"]}/100<br>
                Peerji {item["peer_count"]} · Pokritost polj {item["reliability"]}/100<br>
                ATR {fmt(atr)} · STOP {fmt(stop)} · T1 {fmt(target1)} · T2 {fmt(target2)}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="hero-long">
              <div style="color:#FBBF24;font-size:.78rem;font-weight:700;">
                FUNDAMENTALNI LONG · SEKTORSKO PRIMERJANJE
              </div>
              <div style="font-size:1.3rem;font-weight:700;color:#FFFFFF;margin-top:12px;">
                NI DOVOLJ PODATKOV ZA ZANESLJIVO PRIMERJAVO
              </div>
              <div style="color:#CBD5E1;font-size:.82rem;margin-top:10px;">
                Potreben je strog FCF in bilančni filter ter vsaj pet
                primerljivih podjetij z istim vrednotenjsким multipлом.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with right:
    if best_reversal:
        item = best_reversal
        st.markdown(
            f"""
            <div class="hero-reversal">
              <div style="color:#6EE7B7;font-size:.78rem;font-weight:700;">
                NAJBOLJŠE UJEMANJE INTRADAY FILTROV · NI NAPOVED
              </div>
              <div style="font-size:1.55rem;font-weight:700;color:#FFFFFF;margin-top:5px;">
                {html.escape(item["Ticker"])}
              </div>
              <div style="color:#CBD5E1;font-size:.86rem;margin-top:2px;">
                {html.escape(item["Seja"])} · {html.escape(item["Čas"])}
              </div>
              <div style="color:#F8FAFC;font-size:1rem;margin-top:10px;">
                Cena {item["Cena"]} · Ocena filtra {item["Ocena filtra"]}/10
              </div>
              <div style="color:#CBD5E1;font-size:.78rem;margin-top:8px;line-height:1.7;">
                Gap {item["Gap proti prejšnjemu close %"]:+.2f}% ·
                VWAP {item["VWAP"]} ({item["Odstopanje od VWAP %"]:+.2f}%)<br>
                Volumen {item["Volumen proti isti uri x"]}x ·
                RSI {item["RSI 5m"]} · Momentum {item["Momentum %"]:+.2f}%
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="hero-reversal">
              <div style="color:#6EE7B7;font-size:.78rem;font-weight:700;">
                NAJBOLJŠE UJEMANJE INTRADAY FILTROV · NI NAPOVED
              </div>
              <div style="font-size:1.3rem;font-weight:700;color:#FFFFFF;margin-top:12px;">
                NI STROGEGA KANDIDATA
              </div>
              <div style="color:#CBD5E1;font-size:.82rem;margin-top:10px;">
                Noben ticker trenutno ne prestane vseh filtrov.
                Skener kandidata ne izbere na silo.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.caption(
    "Zlata kartica izbere najbolje uvrščenega kandidata po FCF kakovosti, "
    "vrednotenju in rasti glede na sektor. Zelena kartica pokaže najboljši "
    "intraday signal, ki prestane nastavljene filtre."
)


# ============================================================
# CAPITAL ROTATION RADAR
# ============================================================

st.subheader("Capital Rotation Radar")

detail_html = ""
if rotation["detail"]:
    detail_html = (
        "<div style='color:#94A3B8;font-size:.82rem;margin-top:6px;'>"
        + html.escape(rotation["detail"])
        + "</div>"
    )

st.markdown(
    "<div class='ledger-card'>"
    "<div style='color:#FBBF24;font-weight:700;font-size:1rem;'>"
    + html.escape(rotation["rotation"])
    + "</div>"
    "<div style='color:#94A3B8;font-size:.82rem;margin-top:6px;'>"
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
    "ETF-ji kažejo relativno gibanje cen proti SPY, ne neposrednih tokov "
    "kapitala ali sprememb analitičnega sentimenta."
)


# ============================================================
# TOP 5 LONG
# ============================================================

st.subheader("TOP 5 Long · FCF kakovost, vrednotenje in sektor")
st.caption(
    "Long filter zahteva vsaj tri leta izkazov, pozitiven zadnji letni FCF, "
    "doslednost FCF, minimalno FCF maržo, pretvorbo dobička v denar, "
    "omejeno SBC breme, rast in preverjeno bilanco. Za sektorski percentil "
    "mora biti vsaj pet likvidnih primerljivih podjetij z istim multipлом."
)

if long_candidates:
    table_rows = []

    for item in long_candidates[:5]:
        table_rows.append({
            "Ticker": item["ticker"],
            "Podjetje": item["name"],
            "Sektor": item["sector"],
            "Peerji": item["peer_count"],
            "Skupna ocena / 10": item["composite_score"],
            "Kakovost FCF / 10": fmt(item["quality"], 1),
            "FCF pozitivna leta": (
                f"{item['positive_fcf_years']}/{item['fcf_years']}"
            ),
            "Mediana FCF marže %": fmt(item["median_fcf_margin"], 1, "%"),
            "CFO / čisti dobiček": fmt(item["median_cash_conversion"], 2, "x"),
            "SBC / prihodki %": fmt(item["median_sbc_burden"], 1, "%"),
            "FCF yield %": fmt(item["fcf_yield"], 1, "%"),
            "Primerjalni multiple": item["multiple"]["name"],
            "Vrednost multipla": fmt(item["multiple"]["value"]),
            "Vrednotenje peer percentil": item["valuation_percentile"],
            "FCF peer percentil": item["fcf_percentile"],
            "Rast prihodkov %": fmt(item["revenue_growth"] * 100, 1, "%"),
            "Rastni peer percentil": item["growth_percentile"],
            "Analitiki": fmt(item["analyst_count"], 0),
            "WS priporočilo, ni trend": fmt(item["recommendation_mean"], 2),
            "Ciljna rast analitikov %": fmt(item["analyst_upside"], 1, "%"),
            "Pokritost polj / 100": item["reliability"],
        })

    render_dark_table(pd.DataFrame(table_rows))
else:
    st.info(
        "Ni fundamentalnega kandidata, ki bi prestal stroge filtre "
        "in imel najmanj pet primerljivih peerjev."
    )

st.caption(
    "Pokritost polj pomeni, da so bila vhodna polja na voljo; to ni "
    "neodvisna revizija njihove pravilnosti. Trenutni sektorski multiple "
    "ni primerjava z lastno zgodovinsko mediano vrednotenja podjetja."
)


# ============================================================
# TOP 5 INTRADAY REVERSAL
# ============================================================

st.subheader("TOP 5 Intraday Reversal")
st.caption(
    "Premarket VWAP in redni VWAP se računata ločeno. Signal zahteva padec "
    "1–8 % glede na prejšnji redni close, zeleno zaključeno svečo, prehod "
    "VWAP-a navzgor, RSI pod 35, volumen vsaj 1,3× glede na isto uro, "
    "pozitiven momentum in preverjene earnings."
)

if reversal_candidates:
    render_dark_table(pd.DataFrame(reversal_candidates))
else:
    st.info(
        "NI STROGEGA KANDIDATA. Ni delnice, ki bi trenutno prestala vse pogoje."
    )

st.warning(
    "Premarket je lahko manj likviden, Yahoo Finance pa lahko vrne "
    "nepopolne ali zakasnjene podatke. Signal ni zagotovilo donosa "
    "in ni samodejno priporočilo za nakup."
)


# ============================================================
# AI KOMENTAR
# ============================================================

st.subheader("Avtonomni AI Analitik")
st.caption(
    "AI komentira podatke, prikazane v skenu; manjkajočih številk ne sme "
    "nadomeščati z ugibanjem."
)

if st.button("Zaženi AI komentar trga"):
    if not api_key:
        st.error("Vnesi Gemini API ključ.")
    else:
        long_context = [
            {
                "ticker": item["ticker"],
                "sector": item["sector"],
                "score": item["composite_score"],
                "fcf_quality": item["quality"],
                "valuation_multiple": item["multiple"],
                "valuation_percentile": item["valuation_percentile"],
                "growth_percentile": item["growth_percentile"],
                "reliability": item["reliability"],
            }
            for item in long_candidates[:5]
        ]

        prompt = f"""
Odgovori v slovenščini. Uporabi samo spodaj navedene podatke.
Ne izmišljaj si cen, novic, denarnih tokov, sprememb sentimenta
ali prihodnjih donosov.

ETF relativna moč je cenovni približek, ne neposredna meritev tokov kapitala.
Yahoo trenutno priporočilo analitikov ni isto kot zgodovinska sprememba
sentimenta.
Long ocena je heuristična in ni potrjen model pričakovanega donosa.
Če kandidatov ni, napiši "NI STROGEGA KANDIDATA".

Tržni režim: {market}
Sektorska relativna moč: {rotation}
Long kandidati: {long_context}
Intraday kandidati: {reversal_candidates}

Odgovori v treh kratkih odstavkih:
1. Tržni režim in sektorska relativna moč.
2. Najboljši Long po prikazani metodologiji in omejitve podatkov.
3. Intraday kandidat, če obstaja, z dejanskimi prikazanimi meritvami.
"""
        try:
            with st.spinner("Pripravljam komentar podatkov..."):
                model_name, report = gemini_comment(api_key, prompt)
            st.caption(f"API model: {model_name}")
            st.markdown(report)
        except Exception as error:
            st.error(f"AI komentar ni uspel: {error}")


st.caption(
    "Skeni se osvežijo ob ponovnem nalaganju ali s klikom na »Osveži skene«. "
    "Aplikacija ne spremlja trga v ozadju in ne pošilja samodejnih opozoril."
)
