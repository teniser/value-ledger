import html
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st
import yfinance as yf


# ============================================================
# NASTAVITVE IN SLOG
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
    .hero-long {
        background:linear-gradient(145deg,rgba(48,34,10,.72),rgba(13,17,28,.96));
        border:1px solid rgba(245,158,11,.58);
        border-radius:18px;
        padding:20px 24px;
        min-height:220px;
    }
    .hero-reversal {
        background:linear-gradient(145deg,rgba(9,43,39,.75),rgba(13,17,28,.96));
        border:1px solid rgba(16,185,129,.48);
        border-radius:18px;
        padding:20px 24px;
        min-height:220px;
    }
    .ledger-card {
        background:linear-gradient(145deg,#0D111C,#090B12);
        border:1px solid rgba(255,255,255,.08);
        border-radius:16px;
        padding:20px 24px;
        margin:8px 0 18px;
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
# UNIVERZUM
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

# Primerjalna mera je določena po skupini. Različnih multiple-ov ne mešamo.
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

# Ime podjetja uporabimo le, kadar ga Yahoo Finance ne vrne.
KNOWN_NAMES = {
    "MNDY": "monday.com",
    "CRWD": "CrowdStrike",
    "FTNT": "Fortinet",
    "TSM": "Taiwan Semiconductor Manufacturing",
    "TOST": "Toast",
    "NOW": "ServiceNow",
    "PANW": "Palo Alto Networks",
    "PLTR": "Palantir",
    "DDOG": "Datadog",
    "TEAM": "Atlassian",
    "SNOW": "Snowflake",
    "HUBS": "HubSpot",
    "DELL": "Dell Technologies",
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


def get_statement_row(frame, names):
    if frame is None or frame.empty:
        return None

    labels = {
        str(index).strip().lower().replace("_", " "): index
        for index in frame.index
    }

    for name in names:
        normalized = name.strip().lower().replace("_", " ")
        if normalized in labels:
            return frame.loc[labels[normalized]]

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


def render_dark_table(frame):
    if frame is None or frame.empty:
        st.info("Ni podatkov za prikaz.")
        return

    header = "".join(
        f"<th>{html.escape(str(column))}</th>"
        for column in frame.columns
    )

    body_rows = []
    for _, row in frame.iterrows():
        cells = []
        for value in row.tolist():
            text = "—" if pd.isna(value) else str(value)
            cells.append(f"<td>{html.escape(text)}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")

    # Navaden niz, ne f-string; CSS zaviti oklepaji niso Python izraz.
    table_html = (
        '<div style="overflow-x:auto;border:1px solid #263044;'
        'border-radius:10px;margin:8px 0 18px 0;">'
        '<table style="border-collapse:collapse;width:100%;'
        'background:#0D111C;color:#CBD5E1;font-size:.82rem;">'
        '<thead><tr style="background:#151B29;color:#F8FAFC;">'
        + header
        + "</tr></thead><tbody>"
        + "".join(body_rows)
        + "</tbody></table></div>"
        "<style>"
        "table th,table td{border:1px solid #202838;padding:8px 10px;"
        "text-align:left;white-space:nowrap;}"
        "table tbody tr:nth-child(even){background:#101522;}"
        "</style>"
    )
    st.markdown(table_html, unsafe_allow_html=True)


def midrank_percentile(values, target, lower_is_better=False):
    clean = [
        value for value in values
        if value is not None and math.isfinite(value)
    ]

    if target is None or len(clean) < 5:
        return None

    less = sum(value < target for value in clean)
    equal = sum(value == target for value in clean)
    percentile = (less + 0.5 * equal) / len(clean) * 100

    if lower_is_better:
        percentile = 100 - percentile

    return round(max(0, min(100, percentile)))


def safe_error_text(error):
    return html.escape(str(error)[:400])


# ============================================================
# TRŽNI REŽIM
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
            return {
                "regime": "NEZNANO",
                "change20": None,
                "penalty": 0.0,
            }

        close = frame["Close"].dropna().astype(float)
        if len(close) < 50:
            return {
                "regime": "NEZNANO",
                "change20": None,
                "penalty": 0.0,
            }

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
        return {
            "regime": "NEZNANO",
            "change20": None,
            "penalty": 0.0,
        }


# ============================================================
# CAPITAL ROTATION RADAR
# ============================================================

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
        "Potrošnja (XLY)": "XLY",
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
            joined["sector"].iloc[-1]
            / joined["sector"].iloc[-1 - days]
            - 1
        ) * 100
        spy_return = (
            joined["spy"].iloc[-1]
            / joined["spy"].iloc[-1 - days]
            - 1
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

    rows.sort(key=lambda row: row["Rel. 20d % vs SPY"], reverse=True)

    rotation = "NI PODATKOV"
    detail = ""

    if "IGV" in closes and "SMH" in closes:
        joined = pd.concat(
            [
                closes["IGV"].rename("igv"),
                closes["SMH"].rename("smh"),
            ],
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
# FUNDAMENTALNI PODATKI
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
        net_cash = (
            cash - debt
            if cash is not None and debt is not None
            else None
        )

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
        ebitda_by_year = annual_values(
            income,
            ["EBITDA", "Normalized EBITDA"],
        )

        years = sorted(
            set(cfo) & set(capex) & set(net_income) & set(revenue)
        )[-5:]

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
                "ebitda": ebitda_by_year.get(year),
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
        median_conversion = (
            float(pd.Series(cash_conversions).median())
            if cash_conversions
            else None
        )
        median_sbc = (
            float(pd.Series(sbc_burdens).median()) if sbc_burdens else None
        )

        growth = number("revenueGrowth")
        if growth is not None and growth > 1:
            growth /= 100

        if len(annual) >= 2 and annual[-2]["revenue"] > 0:
            growth = annual[-1]["revenue"] / annual[-2]["revenue"] - 1

        latest_fcf = annual[-1]["fcf"] if annual else None
        latest_ebitda = annual[-1]["ebitda"] if annual else None
        enterprise_value = number("enterpriseValue")
        ev_ebitda = number("enterpriseToEbitda")

        if (
            (ev_ebitda is None or ev_ebitda <= 0)
            and enterprise_value is not None
            and latest_ebitda is not None
            and latest_ebitda > 0
        ):
            ev_ebitda = enterprise_value / latest_ebitda

        target = number("targetMeanPrice") or number("targetMedianPrice")
        analyst_upside = (
            (target / price - 1) * 100
            if target is not None and price is not None and price > 0
            else None
        )

        return {
            "ticker": ticker,
            "name": info.get("shortName") or KNOWN_NAMES.get(ticker, ticker),
            "sector": sector_group(ticker),
            "price": price,
            "market_cap": market_cap,
            "dollar_volume": dollar_volume,
            "cash": cash,
            "debt": debt,
            "net_cash": net_cash,
            "ps": number("priceToSalesTrailing12Months"),
            "pb": number("priceToBook"),
            "ev_ebitda": ev_ebitda,
            "peg": number("pegRatio"),
            "revenue_growth": growth,
            "annual": annual,
            "fcf_years": fcf_years,
            "positive_fcf_years": positive_fcf_years,
            "latest_fcf": latest_fcf,
            "latest_ebitda": latest_ebitda,
            "median_fcf_margin": median_fcf_margin,
            "median_conversion": median_conversion,
            "median_sbc": median_sbc,
            "analyst_count": number("numberOfAnalystOpinions"),
            "recommendation_mean": number("recommendationMean"),
            "analyst_upside": analyst_upside,
        }

    except Exception:
        return None


def multiple_for(data):
    multiple_name = SECTOR_MULTIPLE.get(data["sector"])

    if multiple_name == "P/S":
        value = data.get("ps")
        return {
            "name": multiple_name,
            "value": value if value is not None and value >= 1 else None,
        }

    if multiple_name == "P/B":
        value = data.get("pb")
        return {
            "name": multiple_name,
            "value": value if value is not None and value > 0 else None,
        }

    if multiple_name == "EV/EBITDA":
        value = data.get("ev_ebitda")
        return {
            "name": multiple_name,
            "value": value if value is not None and value > 0 else None,
        }

    return {"name": "NI PODATKA", "value": None}


def is_liquid(data):
    return bool(
        data
        and data.get("market_cap") is not None
        and data.get("dollar_volume") is not None
        and data["market_cap"] >= 2_000_000_000
        and data["dollar_volume"] >= 20_000_000
    )


def fcf_quality_score(data):
    """Hevristična FCF ocena 0–10; ne nadomesti pregleda izkazov."""
    parts = []

    years = data.get("fcf_years", 0)
    if years >= 3:
        parts.append((
            data["positive_fcf_years"] / years * 10,
            0.25,
        ))

    margin = data.get("median_fcf_margin")
    if margin is not None:
        parts.append((max(0.0, min(10.0, margin / 2)), 0.25))

    conversion = data.get("median_conversion")
    if conversion is not None:
        parts.append((max(0.0, min(10.0, conversion * 5)), 0.20))

    sbc = data.get("median_sbc")
    if sbc is not None:
        parts.append((max(0.0, min(10.0, 10 - sbc / 2)), 0.15))

    net_cash = data.get("net_cash")
    if net_cash is not None:
        parts.append((8.0 if net_cash >= 0 else 3.0, 0.15))

    # Če manjka več komponent, ocene ne izmišljamo.
    if len(parts) < 4:
        return None

    total_weight = sum(weight for _, weight in parts)
    if total_weight <= 0:
        return None

    score = sum(value * weight for value, weight in parts) / total_weight
    return round(max(0.0, min(10.0, score)), 1)


def long_filter_reasons(data):
    reasons = []

    if not is_liquid(data):
        return ["likvidnost ali market cap ni potrjen"]

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
        reasons.append("mediana FCF marže je pod 5 % ali manjka")

    if (
        data.get("median_conversion") is None
        or data["median_conversion"] < 0.7
    ):
        reasons.append("CFO/čisti dobiček je pod 0,7x ali manjka")

    if (
        data.get("median_sbc") is None
        or data["median_sbc"] > 15
    ):
        reasons.append("SBC manjka ali presega 15 % prihodkov")

    if (
        data.get("revenue_growth") is None
        or data["revenue_growth"] < 0.10
    ):
        reasons.append("rast prihodkov je pod 10 % ali manjka")

    if data.get("net_cash") is None:
        reasons.append("neto denar/dolg ni na voljo")
    elif data["net_cash"] < 0:
        ebitda = data.get("latest_ebitda")
        if ebitda is None or ebitda <= 0:
            reasons.append("neto dolg in ni pozitivnega EBITDA")
        elif abs(data["net_cash"]) / ebitda > 2.5:
            reasons.append("net debt/EBITDA presega 2,5x")

    return reasons


def data_coverage_score(data):
    """Pokritost polj, ne neodvisna potrditev njihove pravilnosti."""
    checks = [
        data.get("price") is not None,
        data.get("market_cap") is not None,
        data.get("dollar_volume") is not None,
        data.get("revenue_growth") is not None,
        data.get("fcf_years", 0) >= 3,
        data.get("median_fcf_margin") is not None,
        data.get("median_conversion") is not None,
        data.get("median_sbc") is not None,
        data.get("net_cash") is not None,
        data.get("latest_fcf") is not None,
    ]
    return round(sum(checks) / len(checks) * 100)


def analyst_snapshot(data):
    """Trenutno priporočilo analitikov, ne zgodovinski trend sentimenta."""
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


@st.cache_data(ttl=1800, show_spinner=False)
def scan_long(universe):
    """
    Primerjalna skupina vsebuje likvidne tickerje z veljavnim istim
    sektorskim multipлом. Kandidati z manj kot petimi peerji se izpustijo.
    """
    all_data = []
    eligible = []

    for ticker in universe:
        data = get_fundamental_data(ticker)
        if not data:
            continue

        data["multiple"] = multiple_for(data)
        data["quality"] = fcf_quality_score(data)
        data["coverage"] = data_coverage_score(data)
        data["reasons"] = long_filter_reasons(data)

        if is_liquid(data) and data["multiple"]["value"] is not None:
            all_data.append(data)

        if not data["reasons"] and data["quality"] is not None:
            eligible.append(data)

    peers_by_sector = {}
    for item in all_data:
        peers_by_sector.setdefault(item["sector"], []).append(item)

    ranked = []

    for candidate in eligible:
        peers = peers_by_sector.get(candidate["sector"], [])
        peers = [
            peer for peer in peers
            if (
                peer["multiple"]["name"] == candidate["multiple"]["name"]
                and peer["multiple"]["value"] is not None
            )
        ]

        if len(peers) < 5:
            continue

        multiple_values = [peer["multiple"]["value"] for peer in peers]
        quality_values = [
            peer["quality"] for peer in peers
            if peer["quality"] is not None
        ]
        growth_values = [
            peer["revenue_growth"] for peer in peers
            if peer["revenue_growth"] is not None
        ]

        valuation_pct = midrank_percentile(
            multiple_values,
            candidate["multiple"]["value"],
            lower_is_better=True,
        )
        fcf_pct = midrank_percentile(
            quality_values,
            candidate["quality"],
            lower_is_better=False,
        )
        growth_pct = midrank_percentile(
            growth_values,
            candidate["revenue_growth"],
            lower_is_better=False,
        )

        if valuation_pct is None or fcf_pct is None or growth_pct is None:
            continue

        # Enotna lestvica sektorskih percentilov; ne primerjamo surovih P/S
        # in EV/EBITDA vrednosti neposredno med različnimi sektorji.
        score = (
            0.45 * fcf_pct
            + 0.35 * valuation_pct
            + 0.20 * growth_pct
        ) / 10

        result = dict(candidate)
        result["peer_count"] = len(peers)
        result["valuation_percentile"] = valuation_pct
        result["fcf_percentile"] = fcf_pct
        result["growth_percentile"] = growth_pct
        result["composite_score"] = round(score, 1)
        ranked.append(result)

    ranked.sort(
        key=lambda item: (
            item["composite_score"],
            item["coverage"],
            item["ticker"],
        ),
        reverse=True,
    )

    # MNDY vključimo v prikaz tudi, če zaradi filtrov ni uvrščen.
    mndy_data = get_fundamental_data("MNDY")
    mndy_result = None

    if mndy_data:
        mndy_data["multiple"] = multiple_for(mndy_data)
        mndy_data["quality"] = fcf_quality_score(mndy_data)
        mndy_data["coverage"] = data_coverage_score(mndy_data)
        mndy_data["reasons"] = long_filter_reasons(mndy_data)

        for row in ranked:
            if row["ticker"] == "MNDY":
                mndy_result = row
                break

        if mndy_result is None:
            mndy_result = mndy_data

    return ranked, mndy_result, len(all_data)


# ============================================================
# ATR
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
# INTRADAY PODATKI: PREMARKET IN REDNA SEJA LOČENO
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

        required = ["Open", "High", "Low", "Close", "Volume"]
        if any(column not in frame.columns for column in required):
            return None

        frame = frame.dropna(subset=required).copy()
        if frame.empty:
            return None

        if frame.index.tz is None:
            frame.index = frame.index.tz_localize("UTC")
        frame.index = frame.index.tz_convert(NY_TZ)

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


def previous_regular_close(frame, date_value):
    dates = sorted(
        {
            stamp.date()
            for stamp in frame.index
            if stamp.date() < date_value
        },
        reverse=True,
    )

    for prior_date in dates:
        bars = session_bars(frame, prior_date, "regular")
        if not bars.empty:
            value = as_float(bars["Close"].iloc[-1])
            if value is not None and value > 0:
                return value

    return None


def session_vwap(bars):
    if bars is None or bars.empty:
        return pd.Series(dtype=float)

    typical = (
        bars["High"].astype(float)
        + bars["Low"].astype(float)
        + bars["Close"].astype(float)
    ) / 3
    volume = bars["Volume"].astype(float).clip(lower=0)
    cumulative_volume = volume.cumsum().replace(0, float("nan"))
    return (typical * volume).cumsum() / cumulative_volume


def same_time_volume_ratio(frame, timestamp, bars, index):
    current_volume = as_float(bars["Volume"].iloc[index])
    if current_volume is None or current_volume <= 0:
        return None

    session = (
        "premarket"
        if timestamp.time() < time(9, 30)
        else "regular"
    )
    clock = timestamp.strftime("%H:%M")

    prior_dates = sorted({
        stamp.date()
        for stamp in frame.index
        if stamp.date() < timestamp.date()
    })[-5:]

    prior_volumes = []
    for prior_date in prior_dates:
        prior = session_bars(frame, prior_date, session)
        matches = [
            stamp for stamp in prior.index
            if stamp.strftime("%H:%M") == clock
        ]

        if matches:
            value = as_float(prior.loc[matches[-1], "Volume"])
            if value is not None and value > 0:
                prior_volumes.append(value)

    if not prior_volumes:
        return None

    baseline = float(pd.Series(prior_volumes).median())
    return current_volume / baseline if baseline > 0 else None


def calculate_rsi(values, period=14):
    close = pd.Series(values, dtype=float)
    if len(close) < period + 1:
        return None

    change = close.diff()
    average_gain = change.clip(lower=0).rolling(period).mean().iloc[-1]
    average_loss = (-change.clip(upper=0)).rolling(period).mean().iloc[-1]

    if pd.isna(average_gain) or pd.isna(average_loss):
        return None
    if average_loss == 0:
        return 100.0 if average_gain > 0 else 50.0

    rs = average_gain / average_loss
    return float(100 - 100 / (1 + rs))


def earnings_clear(ticker, days=5):
    """
    True: podatek ne kaže earnings v naslednjih dneh.
    False: earnings so v obdobju.
    None: vira ni bilo mogoče zanesljivo preveriti.
    """
    try:
        earnings = yf.Ticker(ticker).get_earnings_dates(limit=8)
        if earnings is None or len(earnings) == 0:
            return None

        today = datetime.now(NY_TZ).date()

        for raw_date in earnings.index:
            value = pd.Timestamp(raw_date)
            if value.tzinfo is not None:
                value = value.tz_convert(None)

            difference = (value.date() - today).days
            if 0 <= difference <= days:
                return False

        return True
    except Exception:
        return None


def make_reversal_signal(ticker, frame, now=None):
    now = now or datetime.now(NY_TZ)
    today = now.date()

    if frame is None or frame.empty:
        return None

    day = frame[
        [stamp.date() == today for stamp in frame.index]
    ]
    if day.empty:
        return None

    completed = day[
        [stamp + timedelta(minutes=5) <= now for stamp in day.index]
    ]
    if completed.empty:
        return None

    latest_stamp = completed.index[-1]
    session = (
        "premarket"
        if latest_stamp.time() < time(9, 30)
        else "regular"
    )

    bars = session_bars(frame, today, session)
    bars = bars[
        [stamp + timedelta(minutes=5) <= now for stamp in bars.index]
    ]

    if len(bars) < 15:
        return None

    prior_close = previous_regular_close(frame, today)
    if prior_close is None:
        return None

    # Če earnings podatkov ni mogoče preveriti, ticker ne prestane varovalke.
    if earnings_clear(ticker, 5) is not True:
        return None

    vwap = session_vwap(bars)
    signals = []

    for index in range(14, len(bars)):
        stamp = bars.index[index]
        close = as_float(bars["Close"].iloc[index])
        candle_open = as_float(bars["Open"].iloc[index])
        prior_bar_close = as_float(bars["Close"].iloc[index - 1])
        current_vwap = as_float(vwap.iloc[index])
        previous_vwap = as_float(vwap.iloc[index - 1])

        values = (
            close,
            candle_open,
            prior_bar_close,
            current_vwap,
            previous_vwap,
        )
        if any(value is None for value in values):
            continue

        if session == "premarket":
            reference_open = prior_close
        else:
            regular_bars = session_bars(frame, today, "regular")
            if regular_bars.empty:
                continue

            reference_open = as_float(regular_bars["Open"].iloc[0])
            if reference_open is None or reference_open <= 0:
                continue

        rel_open = (close / reference_open - 1) * 100
        if not -8.0 <= rel_open <= -1.0:
            continue

        crossed_up = (
            prior_bar_close <= previous_vwap
            and close > current_vwap
        )
        green_candle = close > candle_open
        rel_vwap = (close / current_vwap - 1) * 100

        if not crossed_up or not green_candle or rel_vwap < -2.0:
            continue

        rsi = calculate_rsi(bars["Close"].iloc[:index + 1])
        volume_ratio = same_time_volume_ratio(frame, stamp, bars, index)
        momentum = (close / prior_bar_close - 1) * 100

        if rsi is None or rsi >= 35:
            continue
        if volume_ratio is None or volume_ratio < 1.3:
            continue
        if momentum < 0:
            continue

        score = 6.0
        score += min(max(volume_ratio - 1.3, 0) * 0.5, 1.5)
        score += min(max(momentum, 0) * 0.25, 1.0)
        score -= market["penalty"]
        score = round(max(0.0, min(10.0, score)), 1)

        if score < 6.0:
            continue

        signals.append({
            "Ticker": ticker,
            "Čas": stamp.strftime("%H:%M ET"),
            "Seja": "PREMARKET" if session == "premarket" else "REDNA SEJA",
            "Cena": round(close, 2),
            "Rel. open %": round(rel_open, 2),
            "VWAP": round(current_vwap, 2),
            "Rel. VWAP %": round(rel_vwap, 2),
            "Volumen / ista ura x": round(volume_ratio, 2),
            "RSI 5m": round(rsi, 1),
            "Momentum %": round(momentum, 2),
            "Ocena filtra": score,
        })

    return signals[-1] if signals else None


@st.cache_data(ttl=90, show_spinner=False)
def scan_reversals(universe):
    now = datetime.now(NY_TZ)
    results = []

    for ticker in universe:
        try:
            frame = get_intraday_history(ticker, "5d")
            signal = make_reversal_signal(ticker, frame, now)
            if signal:
                results.append(signal)
        except Exception:
            continue

    results.sort(key=lambda row: row["Ocena filtra"], reverse=True)
    return results[:5]


# ============================================================
# GEMINI API
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
# ZAČETNI IZRIS: NASLOV SE PRIKAŽE PRED PODATKOVNIMI KLICI
# ============================================================

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

st.title("Value Ledger 2.0")
st.caption(
    "Fundamentalne ocene so hevristične, ne potrjene napovedi donosa. "
    "Aplikacija ne oddaja naročil."
)

st.sidebar.markdown("### Nastavitve")
api_key = st.sidebar.text_input(
    "Gemini API ključ (neobvezno)",
    type="password",
)
st.sidebar.caption(f"Unikatni tickerji: {len(AI_UNIVERSE)}")
st.sidebar.caption("Yahoo Finance podatki so lahko zakasnjeni ali nepopolni.")

refresh = st.button("Osveži skene")
if refresh:
    scan_long.clear()
    scan_reversals.clear()
    get_fundamental_data.clear()
    get_intraday_history.clear()
    get_market_regime.clear()
    get_capital_rotation.clear()
    get_atr.clear()

market = get_market_regime()
rotation = get_capital_rotation()

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Tržni režim:** {market['regime']}")
if market["change20"] is not None:
    st.sidebar.caption(f"SPY 20d: {market['change20']:+.2f}%")

long_candidates = []
mndy_audit = None
peer_data_count = 0
reversal_candidates = []
scan_problem = None

progress = st.progress(0, text="Pripravljam skener...")
try:
    with st.spinner("Skeniram fundamentals in intraday podatke..."):
        long_candidates, mndy_audit, peer_data_count = scan_long(
            tuple(AI_UNIVERSE)
        )
        progress.progress(65, text="Fundamentalni pregled končan; skeniram intraday...")
        reversal_candidates = scan_reversals(tuple(AI_UNIVERSE))
        progress.progress(100, text="Skeniranje končano.")
except Exception as error:
    scan_problem = str(error)
finally:
    progress.empty()

if scan_problem:
    st.error(f"Sken se ni končal: {safe_error_text(scan_problem)}")

best_long = long_candidates[0] if long_candidates else None
best_reversal = reversal_candidates[0] if reversal_candidates else None


# ============================================================
# DINAMIČNI ZLATI LONG IN ZELENI INTRADAY OBRAT
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
                FUNDAMENTALNI LONG · HEVRISTIČNA SEKTORSKA PRIMERJAVA
              </div>
              <div style="font-size:1.55rem;font-weight:700;color:#FFFFFF;margin-top:5px;">
                {html.escape(item["ticker"])}
              </div>
              <div style="color:#CBD5E1;font-size:.86rem;margin-top:2px;">
                {html.escape(item["name"])} · {html.escape(item["sector"])}
              </div>
              <div style="color:#F8FAFC;font-size:1rem;margin-top:10px;">
                Cena {fmt(item["price"])} · Ocena {item["composite_score"]}/10
              </div>
              <div style="color:#CBD5E1;font-size:.78rem;margin-top:8px;line-height:1.7;">
                Kakovost FCF {fmt(item["quality"], 1)}/10 ·
                FCF peer percentil {item["fcf_percentile"]}/100<br>
                {item["multiple"]["name"]} {fmt(item["multiple"]["value"])} ·
                Vrednotenje peer percentil {item["valuation_percentile"]}/100<br>
                Rast prihodkov {fmt(item["revenue_growth"] * 100, 1, "%")} ·
                Rastni peer percentil {item["growth_percentile"]}/100<br>
                Peerji {item["peer_count"]} · Pokritost polj {item["coverage"]}/100<br>
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
                FUNDAMENTALNI LONG · HEVRISTIČNA SEKTORSKA PRIMERJAVA
              </div>
              <div style="font-size:1.3rem;font-weight:700;color:#FFFFFF;margin-top:12px;">
                NI STROGEGA KANDIDATA
              </div>
              <div style="color:#CBD5E1;font-size:.82rem;margin-top:10px;">
                Kandidat mora prestati FCF, rastne in bilančne filtre ter
                imeti vsaj pet primerljivih podjetij z istim multipлом.
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
                Rel. open {item["Rel. open %"]:+.2f}% ·
                VWAP {item["VWAP"]} ({item["Rel. VWAP %"]:+.2f}%)<br>
                Volumen {item["Volumen / ista ura x"]}x ·
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
                Noben ticker trenutno ne prestane vseh intraday pogojev.
                Skener kandidata ne izbere na silo.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.caption(
    "Long ocena razvršča le delnice, ki prestanejo filtre in imajo dovolj "
    "peerjev. Rezultat ni dokaz, da je izbrana delnica boljša naložba od "
    "delnice v drugi skupini."
)


# ============================================================
# CAPITAL ROTATION RADAR
# ============================================================

st.subheader("Capital Rotation Radar")

rotation_detail = ""
if rotation["detail"]:
    rotation_detail = (
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
    + rotation_detail
    + "</div>",
    unsafe_allow_html=True,
)

if rotation["rows"]:
    render_dark_table(pd.DataFrame(rotation["rows"]))
else:
    st.info("Sektorski podatki trenutno niso na voljo.")

st.caption(
    "ETF relativna moč prikazuje gibanje cen, ne neposrednih tokov kapitala "
    "ali zgodovinskih sprememb sentimenta analitikov."
)


# ============================================================
# TOP 5 FUNDAMENTALNI LONG
# ============================================================

st.subheader("TOP 5 Long · FCF kakovost, vrednotenje in sektor")
st.caption(
    "Uporabljeni filtri: najmanj tri leta podatkov, zadnji letni FCF pozitiven, "
    "FCF pozitiven v vsaj dveh letih, mediana FCF marže najmanj 5 %, "
    "CFO/čisti dobiček najmanj 0,7x, SBC največ 15 % prihodkov, "
    "rast prihodkov najmanj 10 % in preverljiva bilanca."
)

if long_candidates:
    rows = []

    for item in long_candidates[:5]:
        latest_fcf_yield = None
        if item["market_cap"] and item["latest_fcf"] is not None:
            latest_fcf_yield = item["latest_fcf"] / item["market_cap"] * 100

        rows.append({
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
            "CFO / čisti dobiček": fmt(item["median_conversion"], 2, "x"),
            "SBC / prihodki %": fmt(item["median_sbc"], 1, "%"),
            "FCF yield %": fmt(latest_fcf_yield, 1, "%"),
            "Multiple": item["multiple"]["name"],
            "Vrednost multipla": fmt(item["multiple"]["value"]),
            "Vrednotenje peer percentil": item["valuation_percentile"],
            "FCF peer percentil": item["fcf_percentile"],
            "Rast prihodkov %": fmt(item["revenue_growth"] * 100, 1, "%"),
            "Rastni peer percentil": item["growth_percentile"],
            "Analitikov priporočil": fmt(item["analyst_count"], 0),
            "Priporočilo analitikov": fmt(item["recommendation_mean"], 2),
            "Ciljna cena: implied upside %": fmt(item["analyst_upside"], 1, "%"),
            "Pokritost polj / 100": item["coverage"],
        })

    render_dark_table(pd.DataFrame(rows))
else:
    st.info(
        "Ni kandidata, ki bi prestal stroge filtre in imel najmanj pet "
        "primerljivih podjetij z istim multipлом."
    )

st.caption(
    "Pokritost polj ni neodvisna revizija pravilnosti. Primerjava je "
    "znotraj ročno določene sektorske skupine; trenutni multiple ni "
    "zgodovinska mediana vrednotenja podjetja."
)


# ============================================================
# LOČEN PREGLED MNDY
# ============================================================

st.subheader("MNDY · pregled proti Long filtrom")

if mndy_audit:
    mndy_reasons = mndy_audit.get("reasons", [])

    mndy_columns = [
        "Ticker",
        "Cena",
        "FCF zadnje leto",
        "Pozitivna FCF leta",
        "FCF marža mediana",
        "CFO/čisti dobiček",
        "SBC/prihodki",
        "Rast prihodkov",
        "Multiple",
        "Vrednost multipla",
        "Kakovost FCF",
        "Pokritost polj",
    ]

    mndy_row = {
        "Ticker": "MNDY",
        "Cena": fmt(mndy_audit.get("price")),
        "FCF zadnje leto": fmt(mndy_audit.get("latest_fcf"), 0),
        "Pozitivna FCF leta": (
            f"{mndy_audit.get('positive_fcf_years', 0)}/"
            f"{mndy_audit.get('fcf_years', 0)}"
        ),
        "FCF marža mediana": fmt(
            mndy_audit.get("median_fcf_margin"), 1, "%"
        ),
        "CFO/čisti dobiček": fmt(
            mndy_audit.get("median_conversion"), 2, "x"
        ),
        "SBC/prihodki": fmt(mndy_audit.get("median_sbc"), 1, "%"),
        "Rast prihodkov": fmt(
            (
                mndy_audit.get("revenue_growth") * 100
                if mndy_audit.get("revenue_growth") is not None
                else None
            ),
            1,
            "%",
        ),
        "Multiple": (
            mndy_audit.get("multiple", {}).get("name", "—")
        ),
        "Vrednost multipla": fmt(
            mndy_audit.get("multiple", {}).get("value")
        ),
        "Kakovost FCF": fmt(mndy_audit.get("quality"), 1, "/10"),
        "Pokritost polj": f"{mndy_audit.get('coverage', 0)}/100",
    }

    render_dark_table(pd.DataFrame([mndy_row], columns=mndy_columns))

    if mndy_reasons:
        st.warning("MNDY ne prestane vseh trenutnih Long filtrov:")
        for reason in mndy_reasons:
            st.write(f"- {reason}")
    else:
        mndy_in_ranking = any(
            item["ticker"] == "MNDY"
            for item in long_candidates
        )
        if mndy_in_ranking:
            st.info(
                "MNDY je prestal filtre in je v TOP 5, če njegova uvrstitev "
                "to dopušča."
            )
        else:
            st.info(
                "MNDY je prestal finančne filtre, vendar ni bil med petimi "
                "najvišje uvrščenimi peerji."
            )
else:
    st.info("Za MNDY trenutno ni dovolj podatkov za prikaz.")


# ============================================================
# TOP 5 INTRADAY REVERSAL
# ============================================================

st.subheader("TOP 5 Intraday Reversal")
st.caption(
    "Premarket in redni VWAP se računata ločeno. Filter zahteva padec "
    "1–8 % glede na ustrezno referenco, VWAP reclaim, zeleno svečo, "
    "RSI pod 35, volumen vsaj 1,3× glede na isto uro, pozitiven momentum "
    "in uspešno preverjanje earnings."
)

if reversal_candidates:
    render_dark_table(pd.DataFrame(reversal_candidates))
else:
    st.info(
        "NI STROGEGA KANDIDATA. Noben ticker trenutno ne prestane vseh "
        "intraday filtrov."
    )

st.warning(
    "Premarket je lahko manj likviden. Yahoo Finance lahko vrne zakasnjene "
    "ali nepopolne podatke; signal ni zagotovilo donosa."
)


# ============================================================
# GEMINI KOMENTAR
# ============================================================

st.subheader("Avtonomni AI analitik")
st.caption(
    "Komentar naj uporablja prikazane meritve in ne ugiba manjkajočih "
    "podatkov ali prihodnjih donosov."
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
                "multiple": item["multiple"],
                "valuation_percentile": item["valuation_percentile"],
                "fcf_percentile": item["fcf_percentile"],
                "growth_percentile": item["growth_percentile"],
                "peer_count": item["peer_count"],
            }
            for item in long_candidates[:5]
        ]

        prompt = f"""
Odgovori v slovenščini in uporabljaj samo spodnje podatke.
Ne izmišljaj si cen, novic, denarnih tokov, zgodovinskega sentimenta
ali prihodnjih donosov.

ETF relativna moč je cenovni približek, ne neposredna meritev tokov kapitala.
Trenutno priporočilo analitikov ni zgodovinski trend sentimenta.
Long ocene so hevristične, ne potrjena napoved donosa.
Če kandidatov ni, napiši: NI STROGEGA KANDIDATA.

Tržni režim: {market}
Capital Rotation Radar: {rotation}
Long TOP 5: {long_context}
MNDY pregled: {mndy_audit}
Intraday kandidati: {reversal_candidates}

Odgovori v treh kratkih odstavkih:
1. Tržni režim in sektorska relativna moč.
2. TOP Long in kaj rezultat ne dokazuje.
3. Intraday kandidat, če obstaja, z navedenimi meritvami.
"""

        try:
            with st.spinner("Pripravljam komentar..."):
                model_name, report = gemini_comment(api_key, prompt)
            st.caption(f"API model: {model_name}")
            st.markdown(report)
        except Exception as error:
            st.error(f"AI komentar ni uspel: {safe_error_text(error)}")


st.caption(
    "Sken se osveži ob ponovnem nalaganju strani ali s klikom na »Osveži skene«. "
    "Aplikacija ne spremlja trga v ozadju in ne pošilja samodejnih opozoril."
)
