import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st
import yfinance as yf


# ============================================================
# PAGE SETUP
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
        background:#06070B !important;
        color:#E2E8F0 !important;
        font-family:'Plus Jakarta Sans',sans-serif !important;
    }
    section[data-testid="stSidebar"] {
        background:#0A0D14 !important;
        border-right:1px solid rgba(255,255,255,.06);
    }
    h1, h2, h3, h4 {
        font-family:'Space Grotesk',sans-serif !important;
    }
    .hero-long {
        background:linear-gradient(145deg,rgba(48,34,10,.72),rgba(13,17,28,.96));
        border:1px solid rgba(245,158,11,.58);
        border-radius:18px;padding:20px 24px;min-height:220px;
    }
    .hero-reversal {
        background:linear-gradient(145deg,rgba(9,43,39,.75),rgba(13,17,28,.96));
        border:1px solid rgba(16,185,129,.48);
        border-radius:18px;padding:20px 24px;min-height:220px;
    }
    .ledger-card {
        background:linear-gradient(145deg,#0D111C,#090B12);
        border:1px solid rgba(255,255,255,.08);
        border-radius:16px;padding:20px 24px;margin:8px 0 18px;
    }
    div.stButton > button {
        background:linear-gradient(135deg,#F59E0B 0%,#D97706 100%) !important;
        color:#0A0D14 !important;font-weight:700 !important;
        border:none !important;border-radius:10px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

NY_TZ = ZoneInfo("America/New_York")
LJ_TZ = ZoneInfo("Europe/Ljubljana")


# ============================================================
# UNIVERZUM IN ROČNE PRIMERJALNE SKUPINE
# ============================================================

TICKER_CANDIDATES = [
    "MNDY", "CRWD", "SNOW", "HUBS", "DDOG", "TEAM", "NOW", "PANW",
    "PLTR", "CRM", "ADBE", "SHOP", "NET", "ZS", "OKTA", "MDB",
    "ESTC", "PATH", "WDAY", "CFLT", "DOCN", "GTLB", "TOST", "BILL",
    "ASAN", "IOT", "FSLY", "DT", "BSY", "PCOR", "NCNO", "ZM",
    "DOCU", "TWLO", "PD", "DBX", "SMAR", "UPWK", "SPT", "APPN",
    "PEGA", "FROG", "RNG", "VEEV", "TYL", "PTC", "ADSK", "TRMB",
    "AAPL", "MSFT", "META", "AMZN", "GOOGL", "NFLX", "TSLA",
    "UBER", "ABNB", "DASH", "SPOT", "RBLX", "TTD", "ROKU",
    "PINS", "SNAP", "MTCH", "DKNG", "LYFT", "EBAY",
    "NVDA", "AVGO", "AMD", "TSM", "MU", "QCOM", "ARM", "SMCI",
    "ANET", "MRVL", "SNPS", "CDNS", "ANSS", "ALAB", "LITE",
    "COHR", "VRT", "NTNX", "PSTG", "STX", "WDC", "TXN", "ADI",
    "NXPI", "MCHP", "ON", "INTC", "ASML", "AMAT", "LRCX", "KLAC",
    "DELL", "CSCO", "HPE", "HPQ", "GLW", "TER", "KEYS",
    "CHKP", "CYBR", "TENB", "VRNS", "QLYS", "FTNT", "AKAM",
    "VRSN", "GEN", "S",
    "COIN", "HOOD", "XYZ", "PYPL", "SOFI", "AFRM", "MELI",
    "SE", "NU", "V", "MA", "GLBE", "JPM", "GS", "MS", "C",
    "BAC", "SCHW", "ICE", "CME",
    "ISRG", "DXCM", "PODD", "EXAS", "ILMN", "ALGN", "MDT",
    "SYK", "BSX", "ABT", "VRTX", "REGN", "LLY", "NVO", "UNH",
    "CAT", "DE", "ETN", "GE", "HON", "PH", "RTX", "LMT",
    "XOM", "CVX", "SLB", "FSLR", "ENPH", "NXT", "COST",
    "WMT", "HD", "LOW", "MCD", "NKE", "KO", "PG", "F",
    "GM", "RIVN", "LCID", "CVNA", "UPST", "Z", "W",
]
AI_UNIVERSE = list(dict.fromkeys(TICKER_CANDIDATES))[:150]

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
        "NXPI", "MCHP", "ON", "INTC", "ASML", "AMAT", "LRCX", "KLAC",
        "DELL", "CSCO", "HPE", "HPQ", "GLW", "TER", "KEYS",
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

SECTOR_ETF = {
    "SaaS / Software": "IGV",
    "Cybersecurity": "CIBR",
    "Semiconductors / Hardware": "SMH",
    "Large Tech / Internet": "QQQ",
    "Financials / Fintech": "XLF",
    "Healthcare": "XLV",
    "Industrials": "XLI",
    "Energy": "XLE",
    "Consumer": "XLY",
}

KNOWN_NAMES = {
    "MNDY": "monday.com",
    "CRWD": "CrowdStrike",
    "TSM": "Taiwan Semiconductor Manufacturing",
    "FTNT": "Fortinet",
    "NOW": "ServiceNow",
    "PANW": "Palo Alto Networks",
    "PLTR": "Palantir",
    "DDOG": "Datadog",
    "TEAM": "Atlassian",
    "SNOW": "Snowflake",
    "HUBS": "HubSpot",
    "DELL": "Dell Technologies",
}


def get_sector(ticker):
    for sector, members in SECTOR_GROUPS.items():
        if ticker in members:
            return sector
    return "Other / unclassified"


# ============================================================
# SPLOŠNE POMOŽNE FUNKCIJE
# ============================================================

def safe_float(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def fmt(value, digits=2, suffix=""):
    if value is None:
        return "—"
    try:
        return f"{float(value):,.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return "—"


def render_table(frame):
    if frame is None or frame.empty:
        st.info("Ni podatkov za prikaz.")
    else:
        st.dataframe(frame, use_container_width=True, hide_index=True)


def statement_row(frame, names):
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

    for key, original in labels.items():
        if any(name.strip().lower().replace("_", " ") in key for name in names):
            return frame.loc[original]
    return None


def annual_values(frame, names):
    row = statement_row(frame, names)
    if row is None:
        return {}

    result = {}
    for column, value in row.items():
        number = safe_float(value)
        if number is not None:
            try:
                result[pd.Timestamp(column).year] = number
            except Exception:
                pass
    return result


def percentile(values, target, lower_is_better=False):
    values = [
        value for value in values
        if value is not None and math.isfinite(value)
    ]
    if target is None or len(values) < 5:
        return None

    below = sum(value < target for value in values)
    equal = sum(value == target for value in values)
    result = (below + 0.5 * equal) / len(values) * 100
    if lower_is_better:
        result = 100 - result
    return round(max(0.0, min(100.0, result)))


# ============================================================
# TRŽNI REŽIM IN CAPITAL ROTATION RADAR
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def get_market_regime():
    try:
        data = yf.Ticker("SPY").history(
            period="6mo", interval="1d", auto_adjust=True
        )
        if data is None or len(data) < 60:
            return {"regime": "NEZNANO", "change20": None, "penalty": 0.0}

        close = data["Close"].dropna().astype(float)
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
def get_rotation():
    funds = {
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

    prices = {}
    for ticker in list(funds.values()) + ["SPY"]:
        try:
            data = yf.Ticker(ticker).history(
                period="8mo", interval="1d", auto_adjust=True
            )
            if data is not None and not data.empty:
                prices[ticker] = data["Close"].dropna().astype(float)
        except Exception:
            continue

    if "SPY" not in prices:
        return {"rows": [], "rotation": "NI PODATKOV", "detail": ""}

    def rel_return(series, benchmark, days):
        joined = pd.concat(
            [series.rename("sector"), benchmark.rename("spy")],
            axis=1, join="inner"
        ).dropna()
        if len(joined) <= days:
            return None
        a = (joined["sector"].iloc[-1] / joined["sector"].iloc[-1-days] - 1) * 100
        b = (joined["spy"].iloc[-1] / joined["spy"].iloc[-1-days] - 1) * 100
        return float(a - b)

    rows = []
    for label, ticker in funds.items():
        if ticker not in prices:
            continue
        r5 = rel_return(prices[ticker], prices["SPY"], 5)
        r20 = rel_return(prices[ticker], prices["SPY"], 20)
        r60 = rel_return(prices[ticker], prices["SPY"], 60)
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
    rotation, detail = "NI PODATKOV", ""

    if "IGV" in prices and "SMH" in prices:
        joined = pd.concat(
            [prices["IGV"].rename("igv"), prices["SMH"].rename("smh")],
            axis=1, join="inner"
        ).dropna()

        if len(joined) > 60:
            ratio = joined["igv"] / joined["smh"]
            chg20 = (ratio.iloc[-1] / ratio.iloc[-21] - 1) * 100
            chg60 = (ratio.iloc[-1] / ratio.iloc[-61] - 1) * 100
            above = bool(ratio.iloc[-1] > ratio.rolling(20).mean().iloc[-1])

            if chg20 > 0 and chg60 < 0 and above:
                rotation = "MOŽEN ZAČETEK RELATIVNE ROTACIJE SEMIS → SAAS"
            elif chg20 > 0 and chg60 > 0 and above:
                rotation = "SAAS RELATIVNO VODI SEMIS"
            elif chg20 < 0 and chg60 > 0:
                rotation = "SAAS RELATIVNO SLABI PROTI SEMIS"
            elif chg20 < 0 and not above:
                rotation = "SEMIS RELATIVNO VODI SAAS"
            else:
                rotation = "NI JASNE RELATIVNE ROTACIJE"

            detail = (
                f"IGV/SMH: 20d {chg20:+.1f}%, 60d {chg60:+.1f}%; "
                f"nad SMA20: {'DA' if above else 'NE'}"
            )

    return {"rows": rows, "rotation": rotation, "detail": detail}


# ============================================================
# FUNDAMENTALNI PODATKI
# ============================================================

@st.cache_data(ttl=1800, show_spinner=False)
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}

        def number(key):
            return safe_float(info.get(key))

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
            ["Operating Cash Flow", "Total Cash From Operating Activities"],
        )
        capex = annual_values(
            cashflow, ["Capital Expenditure", "Capital Expenditures"]
        )
        sbc = annual_values(
            cashflow, ["Stock Based Compensation", "Share Based Compensation"]
        )
        net_income = annual_values(
            income,
            ["Net Income", "Net Income Common Stockholders",
             "Net Income From Continuing Operations"],
        )
        revenue = annual_values(
            income, ["Total Revenue", "Operating Revenue", "Revenue"]
        )
        ebitda_by_year = annual_values(income, ["EBITDA", "Normalized EBITDA"])

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
                "ebitda": ebitda_by_year.get(year),
            })

        annual.sort(key=lambda row: row["year"])
        fcf_years = len(annual)
        positive_fcf_years = sum(row["fcf"] > 0 for row in annual)

        margins = [
            row["fcf"] / row["revenue"] * 100
            for row in annual if row["revenue"] > 0
        ]
        conversions = [
            row["cfo"] / row["net_income"]
            for row in annual if row["net_income"] > 0
        ]
        sbc_rates = [
            row["sbc"] / row["revenue"] * 100
            for row in annual
            if row["sbc"] is not None and row["revenue"] > 0
        ]

        median_margin = float(pd.Series(margins).median()) if margins else None
        median_conversion = (
            float(pd.Series(conversions).median()) if conversions else None
        )
        median_sbc = float(pd.Series(sbc_rates).median()) if sbc_rates else None

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

        try:
            history = stock.history(
                period="2y", interval="1d", auto_adjust=True
            )
        except Exception:
            history = pd.DataFrame()

        close = (
            history["Close"].dropna().astype(float)
            if history is not None and not history.empty and "Close" in history
            else pd.Series(dtype=float)
        )

        drawdown = high_52w = ret20 = ret60 = ret120 = None
        if len(close) >= 20:
            last = float(close.iloc[-1])
            high_52w = float(close.tail(252).max())
            if high_52w > 0:
                drawdown = (last / high_52w - 1) * 100
            if len(close) > 20:
                ret20 = (last / float(close.iloc[-21]) - 1) * 100
            if len(close) > 60:
                ret60 = (last / float(close.iloc[-61]) - 1) * 100
            if len(close) > 120:
                ret120 = (last / float(close.iloc[-121]) - 1) * 100

        # Wall Street revizije so prikazane samo, če vir vrne zgodovinske zapise.
        net_revisions = upgrades = downgrades = None
        try:
            revision_frame = stock.upgrades_downgrades
        except Exception:
            revision_frame = None

        if revision_frame is not None and not revision_frame.empty:
            dates = pd.to_datetime(revision_frame.index, errors="coerce")
            try:
                if getattr(dates, "tz", None) is None:
                    dates = dates.tz_localize("UTC")
                else:
                    dates = dates.tz_convert("UTC")
                cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=90)
                recent = revision_frame.loc[list(dates >= cutoff)]
            except Exception:
                recent = pd.DataFrame()

            action_col = next(
                (col for col in recent.columns if str(col).lower() == "action"),
                None,
            )
            if action_col is not None:
                actions = (
                    recent[action_col].fillna("").astype(str).str.lower().tolist()
                )
                upgrades = sum(
                    "upgrade" in action or action.strip() == "up"
                    for action in actions
                )
                downgrades = sum(
                    "downgrade" in action or action.strip() == "down"
                    for action in actions
                )
                net_revisions = upgrades - downgrades

        return {
            "ticker": ticker,
            "name": info.get("shortName") or KNOWN_NAMES.get(ticker, ticker),
            "sector": get_sector(ticker),
            "price": price,
            "market_cap": market_cap,
            "dollar_volume": dollar_volume,
            "cash": cash,
            "debt": debt,
            "net_cash": net_cash,
            "ps": number("priceToSalesTrailing12Months"),
            "pb": number("priceToBook"),
            "ev_ebitda": ev_ebitda,
            "growth": growth,
            "annual": annual,
            "fcf_years": fcf_years,
            "positive_fcf_years": positive_fcf_years,
            "latest_fcf": latest_fcf,
            "latest_ebitda": latest_ebitda,
            "median_fcf_margin": median_margin,
            "median_conversion": median_conversion,
            "median_sbc": median_sbc,
            "drawdown_52w": drawdown,
            "high_52w": high_52w,
            "return20": ret20,
            "return60": ret60,
            "return120": ret120,
            "analyst_count": number("numberOfAnalystOpinions"),
            "recommendation_mean": number("recommendationMean"),
            "analyst_upside": analyst_upside,
            "revision_net_90d": net_revisions,
            "upgrades_90d": upgrades,
            "downgrades_90d": downgrades,
        }
    except Exception:
        return None


def multiple_for(data):
    name = SECTOR_MULTIPLE.get(data["sector"])
    keys = {"P/S": "ps", "P/B": "pb", "EV/EBITDA": "ev_ebitda"}
    value = safe_float(data.get(keys.get(name, "")))

    if value is None or value <= 0:
        value = None
    return {"name": name or "NI PODATKA", "value": value}


def liquid(data):
    return bool(
        data
        and data.get("market_cap") is not None
        and data.get("dollar_volume") is not None
        and data["market_cap"] >= 2_000_000_000
        and data["dollar_volume"] >= 20_000_000
    )


def quality_score(data):
    parts = []

    years = data.get("fcf_years", 0)
    if years >= 3:
        parts.append((data["positive_fcf_years"] / years * 10, 0.25))

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

    if len(parts) < 4:
        return None

    total_weight = sum(weight for _, weight in parts)
    return round(
        sum(value * weight for value, weight in parts) / total_weight, 1
    )


def filter_reasons(data):
    reasons = []

    if not liquid(data):
        return ["likvidnost ali market cap nista potrjena"]
    if data.get("fcf_years", 0) < 3:
        reasons.append("manj kot 3 leta primerljivih izkazov")
    if data.get("latest_fcf") is None or data["latest_fcf"] <= 0:
        reasons.append("zadnji letni FCF ni pozitiven")
    if data.get("fcf_years", 0) >= 3 and data.get("positive_fcf_years", 0) < 2:
        reasons.append("FCF ni pozitiven v vsaj 2 od zadnjih 3+ let")
    if data.get("median_fcf_margin") is None or data["median_fcf_margin"] < 5:
        reasons.append("mediana FCF marže pod 5 % ali manjka")
    if data.get("median_conversion") is None or data["median_conversion"] < 0.7:
        reasons.append("CFO/čisti dobiček pod 0,7x ali manjka")
    if data.get("median_sbc") is None:
        reasons.append("SBC podatek ni na voljo")
    elif data["median_sbc"] > 15:
        reasons.append("SBC presega 15 % prihodkov")
    if data.get("growth") is None or data["growth"] < 0.10:
        reasons.append("rast prihodkov pod 10 % ali manjka")

    net_cash = data.get("net_cash")
    if net_cash is None:
        reasons.append("neto denar/dolg ni na voljo")
    elif net_cash < 0:
        ebitda = data.get("latest_ebitda")
        if ebitda is None or ebitda <= 0:
            reasons.append("neto dolg in ni pozitivnega EBITDA")
        elif abs(net_cash) / ebitda > 2.5:
            reasons.append("net debt/EBITDA presega 2,5x")

    if data.get("drawdown_52w") is None:
        reasons.append("ni dovolj cenovne zgodovine za izračun 52w padca")

    return reasons


def coverage_score(data):
    fields = [
        data.get("price") is not None,
        data.get("market_cap") is not None,
        data.get("dollar_volume") is not None,
        data.get("growth") is not None,
        data.get("fcf_years", 0) >= 3,
        data.get("median_fcf_margin") is not None,
        data.get("median_conversion") is not None,
        data.get("median_sbc") is not None,
        data.get("net_cash") is not None,
        data.get("latest_fcf") is not None,
    ]
    return round(sum(fields) / len(fields) * 100)


def drawdown_score(drawdown):
    if drawdown is None:
        return None
    decline = abs(min(drawdown, 0.0))
    if decline < 10:
        return 2.0
    if decline < 20:
        return 4.0
    if decline <= 50:
        return 10.0
    if decline <= 65:
        return 7.0
    if decline <= 75:
        return 4.0
    return 1.0


def momentum_score(ret20, ret60, ret120):
    if ret20 is None or ret60 is None:
        return None

    score = 5.0
    if ret20 > 0:
        score += 2.0
    if ret20 > ret60 / 3:
        score += 1.5
    if ret60 > -15:
        score += 1.0
    if ret120 is not None and ret20 > ret120 / 6:
        score += 0.5
    if ret20 < -10:
        score -= 2.0
    return round(max(0.0, min(10.0, score)), 1)


def analyst_revision_score(data):
    net = data.get("revision_net_90d")
    return None if net is None else round(max(0.0, min(10.0, 5 + net)), 1)


@st.cache_data(ttl=1800, show_spinner=False)
def scan_long(universe):
    records = []
    errors = []

    with ThreadPoolExecutor(max_workers=6) as pool:
        tasks = {
            pool.submit(get_stock_data, ticker): ticker
            for ticker in universe
        }
        for future in as_completed(tasks):
            ticker = tasks[future]
            try:
                data = future.result()
                if data:
                    data["multiple"] = multiple_for(data)
                    data["quality"] = quality_score(data)
                    data["coverage"] = coverage_score(data)
                    data["reasons"] = filter_reasons(data)
                    data["drawdown_score"] = drawdown_score(data["drawdown_52w"])
                    data["momentum_score"] = momentum_score(
                        data["return20"], data["return60"], data["return120"]
                    )
                    data["revision_score"] = analyst_revision_score(data)
                    records.append(data)
            except Exception as error:
                errors.append(f"{ticker}: {error}")

    peers_by_sector = {}
    for data in records:
        if liquid(data) and data["multiple"]["value"] is not None:
            peers_by_sector.setdefault(data["sector"], []).append(data)

    ranked = []
    for candidate in records:
        if candidate["reasons"] or candidate["quality"] is None:
            continue

        peers = [
            peer for peer in peers_by_sector.get(candidate["sector"], [])
            if peer["multiple"]["name"] == candidate["multiple"]["name"]
            and peer["multiple"]["value"] is not None
        ]
        if len(peers) < 5:
            continue

        val_pct = percentile(
            [peer["multiple"]["value"] for peer in peers],
            candidate["multiple"]["value"],
            lower_is_better=True,
        )
        fcf_pct = percentile(
            [peer["quality"] for peer in peers if peer["quality"] is not None],
            candidate["quality"],
        )
        growth_pct = percentile(
            [peer["growth"] for peer in peers if peer["growth"] is not None],
            candidate["growth"],
        )
        if val_pct is None or fcf_pct is None or growth_pct is None:
            continue

        candidate["peer_count"] = len(peers)
        candidate["valuation_percentile"] = val_pct
        candidate["fcf_percentile"] = fcf_pct
        candidate["growth_percentile"] = growth_pct

        # Kakovost 25%, relativno vrednotenje 25%, padec 15%,
        # zagon 15%, rast 10%, analitikove revizije 10%.
        components = [
            (candidate["quality"] * 10, 0.25),
            (val_pct, 0.25),
            (candidate["drawdown_score"] * 10, 0.15),
            (candidate["momentum_score"] * 10, 0.15),
            (growth_pct, 0.10),
        ]
        if candidate["revision_score"] is not None:
            components.append((candidate["revision_score"] * 10, 0.10))

        weight_sum = sum(weight for _, weight in components)
        if weight_sum <= 0:
            continue

        raw = sum(value * weight for value, weight in components) / weight_sum
        candidate["asymmetry_score"] = round(raw / 10, 1)
        candidate["score_coverage"] = round(weight_sum * 100)
        ranked.append(candidate)

    ranked.sort(
        key=lambda item: (
            item["asymmetry_score"],
            item["quality"],
            item["coverage"],
            item["ticker"],
        ),
        reverse=True,
    )
    return ranked, {item["ticker"]: item for item in records}, errors


def sector_relative_returns(ticker, sector):
    etf = SECTOR_ETF.get(sector)
    if not etf:
        return None, None

    try:
        frame = yf.download(
            [ticker, etf],
            period="6mo",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False,
        )
        if frame is None or frame.empty or not isinstance(frame.columns, pd.MultiIndex):
            return None, None

        close = frame["Close"]
        if ticker not in close.columns or etf not in close.columns:
            return None, None

        joined = pd.concat(
            [
                close[ticker].rename("stock"),
                close[etf].rename("sector"),
            ],
            axis=1,
        ).dropna()
        if len(joined) < 61:
            return None, None

        rel20 = (
            (joined["stock"].iloc[-1] / joined["stock"].iloc[-21] - 1)
            - (joined["sector"].iloc[-1] / joined["sector"].iloc[-21] - 1)
        ) * 100
        rel60 = (
            (joined["stock"].iloc[-1] / joined["stock"].iloc[-61] - 1)
            - (joined["sector"].iloc[-1] / joined["sector"].iloc[-61] - 1)
        ) * 100
        return round(float(rel20), 2), round(float(rel60), 2)
    except Exception:
        return None, None


# ============================================================
# ATR
# ============================================================

@st.cache_data(ttl=1800, show_spinner=False)
def get_atr(ticker):
    try:
        frame = yf.Ticker(ticker).history(
            period="3mo", interval="1d", auto_adjust=True
        )
        if frame is None or len(frame) < 20:
            return None

        high = frame["High"].astype(float)
        low = frame["Low"].astype(float)
        close = frame["Close"].astype(float)
        previous = close.shift(1)

        tr = pd.concat(
            [high - low, (high - previous).abs(), (low - previous).abs()],
            axis=1,
        ).max(axis=1)
        value = safe_float(tr.rolling(14).mean().iloc[-1])
        return value if value is not None and value > 0 else None
    except Exception:
        return None


# ============================================================
# INTRADAY REVERSAL: PREMARKET IN REDNA SEJA
# ============================================================

@st.cache_data(ttl=90, show_spinner=False)
def get_intraday_history(ticker):
    try:
        frame = yf.Ticker(ticker).history(
            period="5d",
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
        if frame.index.tz is None:
            frame.index = frame.index.tz_localize("UTC")
        frame.index = frame.index.tz_convert(NY_TZ)

        mask = [
            time(4, 0) <= stamp.time() < time(16, 0)
            for stamp in frame.index
        ]
        frame = frame.loc[mask]
        return frame if not frame.empty else None
    except Exception:
        return None


def session_bars(frame, date_value, session):
    if frame is None or frame.empty:
        return pd.DataFrame()

    day = frame[[stamp.date() == date_value for stamp in frame.index]]
    if session == "premarket":
        return day.between_time("04:00", "09:29")
    return day.between_time("09:30", "15:59")


def previous_regular_close(frame, date_value):
    dates = sorted(
        {stamp.date() for stamp in frame.index if stamp.date() < date_value},
        reverse=True,
    )
    for previous_date in dates:
        bars = session_bars(frame, previous_date, "regular")
        if not bars.empty:
            value = safe_float(bars["Close"].iloc[-1])
            if value is not None and value > 0:
                return value
    return None


def calculate_vwap(bars):
    typical = (
        bars["High"].astype(float)
        + bars["Low"].astype(float)
        + bars["Close"].astype(float)
    ) / 3
    volume = bars["Volume"].astype(float).clip(lower=0)
    cumulative = volume.cumsum().replace(0, float("nan"))
    return (typical * volume).cumsum() / cumulative


def same_time_volume_ratio(frame, stamp, bars, index):
    current = safe_float(bars["Volume"].iloc[index])
    if current is None or current <= 0:
        return None

    session = "premarket" if stamp.time() < time(9, 30) else "regular"
    clock = stamp.strftime("%H:%M")
    previous_dates = sorted({
        item.date() for item in frame.index if item.date() < stamp.date()
    })[-5:]

    previous_volumes = []
    for previous_date in previous_dates:
        prior = session_bars(frame, previous_date, session)
        matches = [
            item for item in prior.index if item.strftime("%H:%M") == clock
        ]
        if matches:
            value = safe_float(prior.loc[matches[-1], "Volume"])
            if value is not None and value > 0:
                previous_volumes.append(value)

    if not previous_volumes:
        return None
    baseline = float(pd.Series(previous_volumes).median())
    return current / baseline if baseline > 0 else None


def rsi_5m(values, period=14):
    close = pd.Series(values, dtype=float)
    if len(close) < period + 1:
        return None

    change = close.diff()
    gains = change.clip(lower=0).rolling(period).mean().iloc[-1]
    losses = (-change.clip(upper=0)).rolling(period).mean().iloc[-1]

    if pd.isna(gains) or pd.isna(losses):
        return None
    if losses == 0:
        return 100.0 if gains > 0 else 50.0

    rs = gains / losses
    return float(100 - 100 / (1 + rs))


def earnings_clear(ticker, days=5):
    """None pomeni, da earnings datuma ni bilo mogoče zanesljivo preveriti."""
    try:
        data = yf.Ticker(ticker).get_earnings_dates(limit=8)
        if data is None or len(data) == 0:
            return None

        today = datetime.now(NY_TZ).date()
        for raw_date in data.index:
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

    prev_close = previous_regular_close(frame, today)
    if prev_close is None or earnings_clear(ticker, 5) is not True:
        return None

    vwap = calculate_vwap(bars)
    found = []

    for index in range(14, len(bars)):
        stamp = bars.index[index]
        close = safe_float(bars["Close"].iloc[index])
        candle_open = safe_float(bars["Open"].iloc[index])
        prior_bar_close = safe_float(bars["Close"].iloc[index - 1])
        current_vwap = safe_float(vwap.iloc[index])
        prior_vwap = safe_float(vwap.iloc[index - 1])

        if any(value is None for value in (
            close, candle_open, prior_bar_close, current_vwap, prior_vwap
        )):
            continue

        if session == "premarket":
            reference = prev_close
        else:
            regular = session_bars(frame, today, "regular")
            if regular.empty:
                continue
            reference = safe_float(regular["Open"].iloc[0])
            if reference is None or reference <= 0:
                continue

        rel_open = (close / reference - 1) * 100
        if not -8.0 <= rel_open <= -1.0:
            continue

        reclaim = prior_bar_close <= prior_vwap and close > current_vwap
        rel_vwap = (close / current_vwap - 1) * 100
        if not reclaim or close <= candle_open or rel_vwap < -2:
            continue

        rsi = rsi_5m(bars["Close"].iloc[:index + 1])
        volume_ratio = same_time_volume_ratio(frame, stamp, bars, index)
        momentum = (close / prior_bar_close - 1) * 100

        if rsi is None or rsi >= 35:
            continue
        if volume_ratio is None or volume_ratio < 1.3 or momentum <= 0:
            continue

        score = 6.0 + min(max(volume_ratio - 1.3, 0) * 0.5, 1.5)
        score += min(momentum * 0.25, 1.0)
        score -= market["penalty"]
        score = round(max(0.0, min(10.0, score)), 1)

        if score < 6.0:
            continue

        found.append({
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

    return found[-1] if found else None


@st.cache_data(ttl=90, show_spinner=False)
def scan_reversals(universe):
    results = []
    now = datetime.now(NY_TZ)

    for ticker in universe:
        try:
            frame = get_intraday_history(ticker)
            signal = reversal_signal(ticker, frame, now)
            if signal:
                results.append(signal)
        except Exception:
            continue

    results.sort(key=lambda item: item["Ocena filtra"], reverse=True)
    return results[:5]


# ============================================================
# GEMINI API
# ============================================================

def ask_gemini(api_key, prompt):
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
                    for part in parts if part.get("text")
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
    "Ocene so presejalni pripomoček, ne napoved donosa. "
    "Aplikacija ne oddaja naročil."
)

st.sidebar.markdown("### Nastavitve")
api_key = st.sidebar.text_input(
    "Gemini API ključ (neobvezno)",
    type="password",
)
st.sidebar.caption(f"Tickerji v univerzumu: {len(AI_UNIVERSE)}")
st.sidebar.caption("Yahoo Finance podatki so lahko zakasnjeni ali nepopolni.")

if st.button("Osveži skene"):
    scan_long.clear()
    scan_reversals.clear()
    get_stock_data.clear()
    get_intraday_history.clear()
    get_market_regime.clear()
    get_rotation.clear()
    get_atr.clear()
    st.rerun()

with st.spinner("Nalagam tržni režim in sektorsko relativno moč..."):
    market = get_market_regime()
    rotation = get_rotation()

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Tržni režim:** {market['regime']}")
if market["change20"] is not None:
    st.sidebar.caption(f"SPY 20d: {market['change20']:+.2f}%")

long_candidates = []
audit = {}
scan_errors = []
reversal_candidates = []

progress = st.progress(0, text="Začenjam skeniranje...")
try:
    with st.spinner("Skeniram fundamentals in intraday podatke..."):
        long_candidates, audit, scan_errors = scan_long(tuple(AI_UNIVERSE))
        progress.progress(60, text="Fundamentalni sken končan; preverjam intraday...")
        reversal_candidates = scan_reversals(tuple(AI_UNIVERSE))
        progress.progress(100, text="Skeniranje končano.")
except Exception as error:
    st.error(f"Skeniranje ni uspelo: {str(error)[:400]}")
finally:
    progress.empty()

if scan_errors:
    st.caption(f"Napake pri posameznih tickerjih: {len(scan_errors)}")

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
                ASIMETRIČNI LONG · HEVRISTIČNA RAZVRSTITEV
              </div>
              <div style="font-size:1.55rem;font-weight:700;color:#FFFFFF;margin-top:5px;">
                {item["ticker"]}
              </div>
              <div style="color:#CBD5E1;font-size:.86rem;margin-top:2px;">
                {item["name"]} · {item["sector"]}
              </div>
              <div style="color:#F8FAFC;font-size:1rem;margin-top:10px;">
                Cena {fmt(item["price"])} · Ocena {item["asymmetry_score"]}/10
              </div>
              <div style="color:#CBD5E1;font-size:.78rem;margin-top:8px;line-height:1.7;">
                FCF kakovost {fmt(item["quality"], 1)}/10 ·
                FCF peer percentil {item["fcf_percentile"]}/100<br>
                {item["multiple"]["name"]} {fmt(item["multiple"]["value"])} ·
                Vrednotenje peer percentil {item["valuation_percentile"]}/100<br>
                Padec od 52w vrha {fmt(item["drawdown_52w"], 1, "%")} ·
                Donos 20d {fmt(item["return20"], 1, "%")}<br>
                Rast prihodkov {fmt(item["growth"] * 100, 1, "%")} ·
                Peerji {item["peer_count"]}<br>
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
                ASIMETRIČNI LONG · HEVRISTIČNA RAZVRSTITEV
              </div>
              <div style="font-size:1.3rem;font-weight:700;color:#FFFFFF;margin-top:12px;">
                NI STROGEGA KANDIDATA
              </div>
              <div style="color:#CBD5E1;font-size:.82rem;margin-top:10px;">
                Potrebni so prestani finančni filtri, uporabni podatki
                in vsaj pet primerljivih podjetij.
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
                INTRADAY REVERSAL · UJEMANJE S FILTRI, NE NAPOVED
              </div>
              <div style="font-size:1.55rem;font-weight:700;color:#FFFFFF;margin-top:5px;">
                {item["Ticker"]}
              </div>
              <div style="color:#CBD5E1;font-size:.86rem;margin-top:2px;">
                {item["Seja"]} · {item["Čas"]}
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
                INTRADAY REVERSAL · UJEMANJE S FILTRI, NE NAPOVED
              </div>
              <div style="font-size:1.3rem;font-weight:700;color:#FFFFFF;margin-top:12px;">
                NI STROGEGA KANDIDATA
              </div>
              <div style="color:#CBD5E1;font-size:.82rem;margin-top:10px;">
                Noben ticker trenutno ne prestane vseh intraday pogojev.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.caption(
    "TSM in MNDY se primerjata z različnimi sektorskimi peerji. "
    "Njuna percentila ne dokazujeta, katera delnica ima večji prihodnji upside."
)


# ============================================================
# CAPITAL ROTATION RADAR
# ============================================================

st.subheader("Capital Rotation Radar")

st.markdown(
    "<div class='ledger-card'>"
    "<div style='color:#FBBF24;font-weight:700;font-size:1rem;'>"
    + rotation["rotation"]
    + "</div><div style='color:#94A3B8;font-size:.82rem;margin-top:6px;'>"
    + "Tržni režim: " + market["regime"] + "</div>"
    + (
        "<div style='color:#94A3B8;font-size:.82rem;margin-top:6px;'>"
        + rotation["detail"] + "</div>"
        if rotation["detail"] else ""
    )
    + "</div>",
    unsafe_allow_html=True,
)

if rotation["rows"]:
    render_table(pd.DataFrame(rotation["rows"]))
else:
    st.info("Sektorski podatki trenutno niso na voljo.")

st.caption(
    "ETF relativna moč meri cenovno gibanje, ne neposrednih tokov kapitala "
    "ali zgodovinskega Wall Street sentimenta."
)


# ============================================================
# TOP 5 LONG
# ============================================================

st.subheader("TOP 5 Long · kakovost, vrednotenje, padec in obrat")
st.caption(
    "Padec od 52-tedenskega vrha se točkuje šele po temeljnih filtrih. "
    "Peer multiple ni zgodovinsko vrednotenje podjetja."
)

if long_candidates:
    rows = []
    for item in long_candidates[:5]:
        fcf_yield = (
            item["latest_fcf"] / item["market_cap"] * 100
            if item["market_cap"] and item["latest_fcf"] is not None
            else None
        )
        rel20, rel60 = sector_relative_returns(item["ticker"], item["sector"])

        rows.append({
            "Ticker": item["ticker"],
            "Podjetje": item["name"],
            "Sektor": item["sector"],
            "Peerji": item["peer_count"],
            "Asimetrija / 10": item["asymmetry_score"],
            "FCF kakovost / 10": item["quality"],
            "FCF peer percentil": item["fcf_percentile"],
            "Multiple": item["multiple"]["name"],
            "Vrednost multipla": fmt(item["multiple"]["value"]),
            "Vrednotenje peer percentil": item["valuation_percentile"],
            "Rast prihodkov %": fmt(item["growth"] * 100, 1, "%"),
            "Rastni peer percentil": item["growth_percentile"],
            "FCF pozitivna leta": f"{item['positive_fcf_years']}/{item['fcf_years']}",
            "Mediana FCF marže %": fmt(item["median_fcf_margin"], 1, "%"),
            "CFO / čisti dobiček": fmt(item["median_conversion"], 2, "x"),
            "SBC / prihodki %": fmt(item["median_sbc"], 1, "%"),
            "FCF yield %": fmt(fcf_yield, 1, "%"),
            "Padec od 52w vrha %": fmt(item["drawdown_52w"], 1, "%"),
            "Donos 20d %": fmt(item["return20"], 1, "%"),
            "Rel. donos vs sektor 20d %": fmt(rel20, 1, "%"),
            "Rel. donos vs sektor 60d %": fmt(rel60, 1, "%"),
            "WS neto revizije 90d": fmt(item["revision_net_90d"], 0),
            "WS trenutno priporočilo": fmt(item["recommendation_mean"], 2),
            "WS ciljna rast %": fmt(item["analyst_upside"], 1, "%"),
            "Pokritost polj / 100": item["coverage"],
        })

    render_table(pd.DataFrame(rows))
else:
    st.info("Ni kandidata, ki bi prestal filtre in imel dovolj peerjev.")

st.caption(
    "Yahoo Finance tu ne zagotavlja zanesljive zgodovine P/S ali EV/EBITDA; "
    "koda zato ne trdi, da je delnica poceni glede na lastno večletno vrednotenje. "
    "Trenutna ciljna cena analitikov ni trend sentimenta."
)


# ============================================================
# MNDY PROTI NAJBOLJŠEMU KANDIDATU
# ============================================================

st.subheader("MNDY proti najbolje uvrščenemu Long kandidatu")

comparison_tickers = ["MNDY"]
if best_long and best_long["ticker"] != "MNDY":
    comparison_tickers.append(best_long["ticker"])

comparison_rows = []

for ticker in comparison_tickers:
    data = audit.get(ticker)
    if not data:
        continue

    ranked = next(
        (row for row in long_candidates if row["ticker"] == ticker),
        None,
    )

    if ranked:
        rank_text = f"{ranked['asymmetry_score']}/10"
        val_pct = ranked.get("valuation_percentile")
        fcf_pct = ranked.get("fcf_percentile")
        growth_pct = ranked.get("growth_percentile")
        peer_count = ranked.get("peer_count")
    else:
        rank_text = "NI UVRŠČEN"
        val_pct = fcf_pct = growth_pct = peer_count = None

    fcf_yield = (
        data["latest_fcf"] / data["market_cap"] * 100
        if data.get("market_cap") and data.get("latest_fcf") is not None
        else None
    )
    growth = data.get("growth")
    rel20, rel60 = sector_relative_returns(ticker, data["sector"])

    comparison_rows.append({
        "Ticker": ticker,
        "Podjetje": data["name"],
        "Sektor": data["sector"],
        "Cena": fmt(data.get("price")),
        "P/S": fmt(data.get("ps")),
        "EV/EBITDA": fmt(data.get("ev_ebitda")),
        "FCF yield %": fmt(fcf_yield, 1, "%"),
        "Rast prihodkov %": fmt(growth * 100 if growth is not None else None, 1, "%"),
        "FCF kakovost / 10": fmt(quality_score(data), 1),
        "Padec od 52w vrha %": fmt(data.get("drawdown_52w"), 1, "%"),
        "Donos 20d %": fmt(data.get("return20"), 1, "%"),
        "Rel. donos vs sektor 20d %": fmt(rel20, 1, "%"),
        "Rel. donos vs sektor 60d %": fmt(rel60, 1, "%"),
        "WS neto revizije 90d": fmt(data.get("revision_net_90d"), 0),
        "WS priporočilo": fmt(data.get("recommendation_mean"), 2),
        "Uvrstitev": rank_text,
        "Vrednotenje peer percentil": val_pct,
        "FCF peer percentil": fcf_pct,
        "Rastni peer percentil": growth_pct,
        "Peerji": peer_count,
        "Pokritost polj": f"{coverage_score(data)}/100",
    })

if comparison_rows:
    render_table(pd.DataFrame(comparison_rows))
else:
    st.info("Za MNDY in najbolje uvrščenega kandidata ni dovolj podatkov.")

mndy = audit.get("MNDY")
if mndy:
    reasons = mndy.get("reasons", [])
    if reasons:
        st.warning("MNDY ne prestane vseh trenutnih Long filtrov:")
        for reason in reasons:
            st.write(f"- {reason}")
    elif not any(row["ticker"] == "MNDY" for row in long_candidates):
        st.info(
            "MNDY je prestal temeljne filtre, vendar ni uvrščen v TOP 5; "
            "preveri sektorske peerje in razpoložljivost primerjalnih podatkov."
        )
else:
    st.info("Podatki za MNDY trenutno niso na voljo.")


# ============================================================
# TOP 5 INTRADAY REVERSAL
# ============================================================

st.subheader("TOP 5 Intraday Reversal")
st.caption(
    "Premarket in redna seja imata ločena VWAP-a. Filter zahteva padec "
    "1–8 %, VWAP reclaim, zeleno svečo, RSI pod 35, volumen vsaj 1,3× "
    "glede na isto uro, pozitiven momentum in preverjene earnings."
)

if reversal_candidates:
    render_table(pd.DataFrame(reversal_candidates))
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
# GEMINI ANALITIK
# ============================================================

st.subheader("Avtonomni AI analitik")
st.caption(
    "AI komentar mora uporabljati prikazane meritve in ne sme ugibati "
    "manjkajočih podatkov ali prihodnjih donosov."
)

if st.button("Zaženi AI komentar trga"):
    if not api_key:
        st.error("Vnesi Gemini API ključ.")
    else:
        long_context = [
            {
                "ticker": row["ticker"],
                "sector": row["sector"],
                "score": row["asymmetry_score"],
                "FCF_quality": row["quality"],
                "multiple": row["multiple"],
                "valuation_percentile": row["valuation_percentile"],
                "drawdown_52w": row["drawdown_52w"],
                "return_20d": row["return20"],
                "analyst_revision_net_90d": row["revision_net_90d"],
                "peer_count": row["peer_count"],
            }
            for row in long_candidates[:5]
        ]

        prompt = f"""
Odgovori v slovenščini in uporabljaj samo spodnje podatke.
Ne izmišljaj si cen, novic, zgodovinskega vrednotenja ali donosov.

ETF relativna moč je cenovni približek, ne neposredna meritev tokov kapitala.
Trenutno priporočilo analitikov ni zgodovinski trend sentimenta.
Ocene so hevristične, ne napoved donosa. Če ni kandidatov, napiši:
NI STROGEGA KANDIDATA.

Tržni režim: {market}
Capital Rotation Radar: {rotation}
Long kandidati: {long_context}
MNDY podatki: {mndy}
Intraday kandidati: {reversal_candidates}

Napiši tri kratke odstavke:
1. Tržni režim in sektorska relativna moč.
2. Najboljši Long po prikazani metodi in omejitve primerjave z MNDY.
3. Intraday kandidat, če obstaja, z uporabo samo prikazanih meritev.
"""

        try:
            with st.spinner("Pripravljam komentar..."):
                model_name, report = ask_gemini(api_key, prompt)
            st.caption(f"API model: {model_name}")
            st.markdown(report)
        except Exception as error:
            st.error(f"AI komentar ni uspel: {str(error)[:400]}")

st.caption(
    "Sken se osveži ob ponovnem nalaganju strani ali s klikom na »Osveži skene«. "
    "Aplikacija ne spremlja trga v ozadju in ne pošilja samodejnih opozoril."
)
