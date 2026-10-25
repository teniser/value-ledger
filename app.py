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
# PAGE AND STYLE
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
        border-right: 1px solid rgba(255,255,255,.06);
    }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
        font-family: 'Space Grotesk', sans-serif !important;
        color: #E2E8F0 !important;
    }
    .hero-long {
        background: linear-gradient(145deg, rgba(48,34,10,.72), rgba(13,17,28,.96));
        border: 1px solid rgba(245,158,11,.58);
        border-radius: 18px;
        padding: 20px 24px;
        min-height: 230px;
    }
    .hero-reversal {
        background: linear-gradient(145deg, rgba(9,43,39,.75), rgba(13,17,28,.96));
        border: 1px solid rgba(16,185,129,.48);
        border-radius: 18px;
        padding: 20px 24px;
        min-height: 230px;
    }
    .ledger-card {
        background: linear-gradient(145deg,#0D111C,#090B12);
        border: 1px solid rgba(255,255,255,.08);
        border-radius: 16px;
        padding: 20px 24px;
        margin: 8px 0 18px;
    }
    div.stButton > button {
        background: linear-gradient(135deg,#F59E0B 0%,#D97706 100%) !important;
        color: #0A0D14 !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 10px 18px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

NY_TZ = ZoneInfo("America/New_York")
LJ_TZ = ZoneInfo("Europe/Ljubljana")


# ============================================================
# STOCK UNIVERSE
# ============================================================

TICKER_CANDIDATES = [
    # Software, SaaS and cloud
    "MNDY", "CRWD", "SNOW", "HUBS", "DDOG", "TEAM", "NOW", "PANW",
    "PLTR", "CRM", "ADBE", "SHOP", "NET", "ZS", "OKTA", "MDB",
    "ESTC", "PATH", "WDAY", "CFLT", "DOCN", "GTLB", "TOST", "BILL",
    "ASAN", "IOT", "FSLY", "DT", "BSY", "PCOR", "NCNO", "ZM",
    "DOCU", "TWLO", "PD", "DBX", "SMAR", "UPWK", "SPT", "APPN",
    "PEGA", "FROG", "RNG", "VEEV", "TYL", "PTC", "ADSK", "TRMB",

    # Large technology and internet
    "AAPL", "MSFT", "META", "AMZN", "GOOGL", "NFLX", "TSLA",
    "UBER", "ABNB", "DASH", "SPOT", "RBLX", "TTD", "ROKU",
    "PINS", "SNAP", "MTCH", "DKNG", "LYFT", "EBAY",

    # Semiconductors and hardware
    "NVDA", "AVGO", "AMD", "TSM", "MU", "QCOM", "ARM", "SMCI",
    "ANET", "MRVL", "SNPS", "CDNS", "ANSS", "ALAB", "LITE",
    "COHR", "VRT", "NTNX", "PSTG", "STX", "WDC", "TXN", "ADI",
    "NXPI", "MCHP", "ON", "INTC", "ASML", "AMAT", "LRCX",
    "KLAC", "DELL", "CSCO", "HPE", "HPQ", "GLW", "TER", "KEYS",

    # Cybersecurity
    "CHKP", "CYBR", "TENB", "VRNS", "QLYS", "FTNT", "AKAM",
    "VRSN", "GEN", "S",

    # Financials and fintech
    "COIN", "HOOD", "XYZ", "PYPL", "SOFI", "AFRM", "MELI",
    "SE", "NU", "V", "MA", "GLBE", "JPM", "GS", "MS", "C",
    "BAC", "SCHW", "ICE", "CME",

    # Healthcare
    "ISRG", "DXCM", "PODD", "EXAS", "ILMN", "ALGN", "MDT",
    "SYK", "BSX", "ABT", "VRTX", "REGN", "LLY", "NVO", "UNH",

    # Industrials, energy, consumer and others
    "CAT", "DE", "ETN", "GE", "HON", "PH", "RTX", "LMT",
    "XOM", "CVX", "SLB", "FSLR", "ENPH", "NXT", "COST",
    "WMT", "HD", "LOW", "MCD", "NKE", "KO", "PG", "F",
    "GM", "RIVN", "LCID", "CVNA", "UPST", "Z", "W",
]

AI_UNIVERSE = list(dict.fromkeys(TICKER_CANDIDATES))[:150]

# Manual comparison groups, not official classifications.
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
        "CRWD", "PANW", "CHKP", "CYBR", "TENB", "VRNS", "QLYS",
        "FTNT", "AKAM", "VRSN", "GEN", "S",
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

# One peer multiple per group. Do not compare raw P/S with raw EV/EBITDA.
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


def get_sector(ticker):
    for sector, members in SECTOR_GROUPS.items():
        if ticker in members:
            return sector
    return "Other / unclassified"


# ============================================================
# GENERIC HELPERS
# ============================================================

def safe_float(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def fmt(value, digits=2, suffix=""):
    if value is None:
        return "—"
    try:
        return f"{float(value):,.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return "—"


def get_statement_row(frame, possible_names):
    if frame is None or frame.empty:
        return None

    normalized = {
        str(index).strip().lower().replace("_", " "): index
        for index in frame.index
    }

    for name in possible_names:
        key = name.strip().lower().replace("_", " ")
        if key in normalized:
            return frame.loc[normalized[key]]

    for key, original in normalized.items():
        if any(
            name.strip().lower().replace("_", " ") in key
            for name in possible_names
        ):
            return frame.loc[original]

    return None


def annual_statement_values(frame, possible_names):
    row = get_statement_row(frame, possible_names)
    if row is None:
        return {}

    result = {}
    for column, value in row.items():
        number = safe_float(value)
        if number is None:
            continue
        try:
            result[pd.Timestamp(column).year] = number
        except Exception:
            continue

    return result


def render_table(frame):
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
            text = "—" if pd.isna(value) else str(value)
            cells.append(f"<td>{html.escape(text)}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")

    table_html = (
        '<div style="overflow-x:auto;border:1px solid #263044;'
        'border-radius:10px;margin:8px 0 18px;">'
        '<table style="border-collapse:collapse;width:100%;'
        'background:#0D111C;color:#CBD5E1;font-size:.82rem;">'
        '<thead><tr style="background:#151B29;color:#F8FAFC;">'
        + headers
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

    return round(max(0.0, min(100.0, percentile)))


# ============================================================
# MARKET REGIME
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


# ============================================================
# SECTOR ROTATION RADAR
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def get_rotation():
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
            data = yf.Ticker(ticker).history(
                period="8mo",
                interval="1d",
                auto_adjust=True,
            )
            if data is not None and not data.empty:
                closes[ticker] = data["Close"].dropna().astype(float)
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

        rel5 = relative_return(closes[ticker], closes["SPY"], 5)
        rel20 = relative_return(closes[ticker], closes["SPY"], 20)
        rel60 = relative_return(closes[ticker], closes["SPY"], 60)

        if rel5 is None or rel20 is None or rel60 is None:
            continue

        if rel5 > 0 and rel20 > 0 and rel60 < 0:
            status = "KREPI"
        elif rel20 > 0 and rel60 > 0:
            status = "RELATIVNO VODI"
        elif rel5 < 0 and rel20 < 0 and rel60 > 0:
            status = "SLABI"
        elif rel20 < 0:
            status = "ZAOSTAJA"
        else:
            status = "MEŠANO"

        rows.append({
            "Sektor / ETF": label,
            "Rel. 5d % vs SPY": round(rel5, 1),
            "Rel. 20d % vs SPY": round(rel20, 1),
            "Rel. 60d % vs SPY": round(rel60, 1),
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
# FUNDAMENTALS, PRICE HISTORY, ANALYST REVISIONS
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
        avg_volume = number("averageVolume")
        dollar_volume = (
            price * avg_volume
            if price is not None and avg_volume is not None
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

        cfo = annual_statement_values(
            cashflow,
            [
                "Operating Cash Flow",
                "Total Cash From Operating Activities",
                "Cash Flow From Continuing Operating Activities",
            ],
        )
        capex = annual_statement_values(
            cashflow,
            ["Capital Expenditure", "Capital Expenditures"],
        )
        sbc = annual_statement_values(
            cashflow,
            ["Stock Based Compensation", "Share Based Compensation"],
        )
        net_income = annual_statement_values(
            income,
            [
                "Net Income",
                "Net Income Common Stockholders",
                "Net Income From Continuing Operations",
            ],
        )
        revenue = annual_statement_values(
            income,
            ["Total Revenue", "Operating Revenue", "Revenue"],
        )
        ebitda_by_year = annual_statement_values(
            income,
            ["EBITDA", "Normalized EBITDA"],
        )

        common_years = sorted(
            set(cfo) & set(capex) & set(net_income) & set(revenue)
        )[-5:]

        annual = []
        for year in common_years:
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
        conversions = [
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
            float(pd.Series(conversions).median()) if conversions else None
        )
        median_sbc = (
            float(pd.Series(sbc_burdens).median()) if sbc_burdens else None
        )

        revenue_growth = number("revenueGrowth")
        if revenue_growth is not None and revenue_growth > 1:
            revenue_growth /= 100

        if len(annual) >= 2 and annual[-2]["revenue"] > 0:
            revenue_growth = (
                annual[-1]["revenue"] / annual[-2]["revenue"] - 1
            )

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

        target_price = number("targetMeanPrice") or number("targetMedianPrice")
        analyst_upside = (
            (target_price / price - 1) * 100
            if target_price is not None and price is not None and price > 0
            else None
        )

        try:
            price_history = stock.history(
                period="2y",
                interval="1d",
                auto_adjust=True,
            )
        except Exception:
            price_history = pd.DataFrame()

        price_history = (
            price_history["Close"].dropna().astype(float)
            if price_history is not None
            and not price_history.empty
            and "Close" in price_history
            else pd.Series(dtype=float)
        )

        drawdown_52w = None
        high_52w = None
        return_20d = None
        return_60d = None
        return_120d = None

        if len(price_history) >= 20:
            current_history_price = float(price_history.iloc[-1])
            history_52w = price_history.tail(252)
            high_52w = float(history_52w.max())
            if high_52w > 0:
                drawdown_52w = (
                    current_history_price / high_52w - 1
                ) * 100

            if len(price_history) > 20:
                return_20d = (
                    current_history_price / float(price_history.iloc[-21]) - 1
                ) * 100
            if len(price_history) > 60:
                return_60d = (
                    current_history_price / float(price_history.iloc[-61]) - 1
                ) * 100
            if len(price_history) > 120:
                return_120d = (
                    current_history_price / float(price_history.iloc[-121]) - 1
                ) * 100

        # Wall Street upgrades/downgrades: public provider data can be incomplete.
        revision_net_90d = None
        upgrade_count_90d = None
        downgrade_count_90d = None

        try:
            revisions = stock.upgrades_downgrades
        except Exception:
            revisions = None

        if revisions is not None and not revisions.empty:
            revision_frame = revisions.copy()
            date_values = pd.to_datetime(revision_frame.index, errors="coerce")

            try:
                if getattr(date_values, "tz", None) is None:
                    date_values = date_values.tz_localize("UTC")
                else:
                    date_values = date_values.tz_convert("UTC")

                cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=90)
                recent = revision_frame.loc[list(date_values >= cutoff)].copy()
            except Exception:
                recent = pd.DataFrame()

            action_column = next(
                (
                    column for column in recent.columns
                    if str(column).lower() == "action"
                ),
                None,
            )

            if action_column is not None:
                actions = (
                    recent[action_column]
                    .fillna("")
                    .astype(str)
                    .str.lower()
                    .tolist()
                )

                upgrades = sum(
                    "upgrade" in action or "up" in action
                    for action in actions
                )
                downgrades = sum(
                    "downgrade" in action or "down" in action
                    for action in actions
                )
                upgrade_count_90d = upgrades
                downgrade_count_90d = downgrades
                revision_net_90d = upgrades - downgrades

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
            "peg": number("pegRatio"),
            "revenue_growth": revenue_growth,
            "annual": annual,
            "fcf_years": fcf_years,
            "positive_fcf_years": positive_fcf_years,
            "latest_fcf": latest_fcf,
            "latest_ebitda": latest_ebitda,
            "median_fcf_margin": median_fcf_margin,
            "median_conversion": median_conversion,
            "median_sbc": median_sbc,
            "drawdown_52w": drawdown_52w,
            "high_52w": high_52w,
            "return_20d": return_20d,
            "return_60d": return_60d,
            "return_120d": return_120d,
            "analyst_count": number("numberOfAnalystOpinions"),
            "recommendation_mean": number("recommendationMean"),
            "analyst_upside": analyst_upside,
            "revision_net_90d": revision_net_90d,
            "upgrade_count_90d": upgrade_count_90d,
            "downgrade_count_90d": downgrade_count_90d,
        }

    except Exception:
        return None


def is_liquid(data):
    return bool(
        data
        and data.get("market_cap") is not None
        and data.get("dollar_volume") is not None
        and data["market_cap"] >= 2_000_000_000
        and data["dollar_volume"] >= 20_000_000
    )


def get_multiple(data):
    multiple_name = SECTOR_MULTIPLE.get(data["sector"])

    if multiple_name == "P/S":
        value = data.get("ps")
        if value is not None and value >= 1:
            return {"name": multiple_name, "value": value}

    elif multiple_name == "P/B":
        value = data.get("pb")
        if value is not None and value > 0:
            return {"name": multiple_name, "value": value}

    elif multiple_name == "EV/EBITDA":
        value = data.get("ev_ebitda")
        if value is not None and value > 0:
            return {"name": multiple_name, "value": value}

    return {"name": multiple_name or "NI PODATKA", "value": None}


def fcf_quality_score(data):
    """Hevristična ocena večletne kakovosti FCF, od 0 do 10."""
    components = []

    years = data.get("fcf_years", 0)
    if years >= 3:
        components.append((
            data["positive_fcf_years"] / years * 10,
            0.25,
        ))

    margin = data.get("median_fcf_margin")
    if margin is not None:
        components.append((max(0.0, min(10.0, margin / 2)), 0.25))

    conversion = data.get("median_conversion")
    if conversion is not None:
        components.append((max(0.0, min(10.0, conversion * 5)), 0.20))

    sbc = data.get("median_sbc")
    if sbc is not None:
        components.append((max(0.0, min(10.0, 10 - sbc / 2)), 0.15))

    net_cash = data.get("net_cash")
    if net_cash is not None:
        components.append((8.0 if net_cash >= 0 else 3.0, 0.15))

    if len(components) < 4:
        return None

    total_weight = sum(weight for _, weight in components)
    if total_weight <= 0:
        return None

    score = sum(value * weight for value, weight in components) / total_weight
    return round(max(0.0, min(10.0, score)), 1)


def long_filter_reasons(data):
    reasons = []

    if not is_liquid(data):
        reasons.append("likvidnost ali market cap ni potrjen")
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
        reasons.append("mediana FCF marže pod 5 % ali manjka")

    if (
        data.get("median_conversion") is None
        or data["median_conversion"] < 0.7
    ):
        reasons.append("CFO/čisti dobiček pod 0,7x ali manjka")

    if data.get("median_sbc") is None:
        reasons.append("SBC podatka ni")
    elif data["median_sbc"] > 15:
        reasons.append("SBC presega 15 % prihodkov")

    if (
        data.get("revenue_growth") is None
        or data["revenue_growth"] < 0.10
    ):
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
        reasons.append("ni dovolj zgodovine cene za izračun 52w padca")

    return reasons


def coverage_score(data):
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


def drawdown_score(drawdown_pct):
    """
    Padec od 52w vrha prispeva le znotraj razpona.
    Dolg padec sam po sebi ni dokaz podcenjenosti.
    """
    if drawdown_pct is None:
        return None

    decline = abs(min(drawdown_pct, 0.0))

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


def momentum_turn_score(return_20d, return_60d, return_120d):
    """
    Išče izboljšanje kratkoročnega zagona glede na daljši trend.
    Ne potrjuje fundamentalnega obrata.
    """
    if return_20d is None or return_60d is None:
        return None

    score = 5.0

    if return_20d > 0:
        score += 2.0
    if return_20d > return_60d / 3:
        score += 1.5
    if return_60d > -15:
        score += 1.0
    if return_120d is not None and return_20d > return_120d / 6:
        score += 0.5

    if return_20d < -10:
        score -= 2.0

    return round(max(0.0, min(10.0, score)), 1)


def analyst_revision_score(data):
    """
    Če zgodovine sprememb priporočil ni, ta komponenta ostane manjkajoča.
    Trenutno priporočilo in ciljna cena nista predstavljena kot trend.
    """
    net = data.get("revision_net_90d")
    if net is None:
        return None

    return round(max(0.0, min(10.0, 5.0 + net)), 1)


# ============================================================
# LONG SCORING AND PEER COMPARISON
# ============================================================

@st.cache_data(ttl=1800, show_spinner=False)
def scan_long(universe):
    records = []
    errors = []

    # Omejena vzporednost skrajša čakanje; napaka enega tickerja ne ustavi skena.
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(get_stock_data, ticker): ticker
            for ticker in universe
        }

        for future in as_completed(futures):
            ticker = futures[future]
            try:
                data = future.result()
                if data:
                    data["multiple"] = get_multiple(data)
                    data["quality"] = fcf_quality_score(data)
                    data["coverage"] = coverage_score(data)
                    data["reasons"] = long_filter_reasons(data)
                    data["drawdown_score"] = drawdown_score(
                        data.get("drawdown_52w")
                    )
                    data["momentum_score"] = momentum_turn_score(
                        data.get("return_20d"),
                        data.get("return_60d"),
                        data.get("return_120d"),
                    )
                    data["analyst_revision_score"] = analyst_revision_score(data)
                    records.append(data)
            except Exception as error:
                errors.append(f"{ticker}: {error}")

    peers_by_sector = {}
    for data in records:
        if (
            is_liquid(data)
            and data["multiple"]["value"] is not None
        ):
            peers_by_sector.setdefault(data["sector"], []).append(data)

    ranked = []
    audit_by_ticker = {}

    for candidate in records:
        audit_by_ticker[candidate["ticker"]] = candidate

        if candidate["reasons"] or candidate["quality"] is None:
            continue

        peers = peers_by_sector.get(candidate["sector"], [])
        peers = [
            peer for peer in peers
            if (
                peer["multiple"]["name"] == candidate["multiple"]["name"]
                and peer["multiple"]["value"] is not None
            )
        ]

        if len(peers) < 5:
            candidate["ranking_note"] = (
                f"Le {len(peers)} veljavnih peerjev; zahtevanih je vsaj 5"
            )
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
            candidate["ranking_note"] = "Premalo peer podatkov za percentile"
            continue

        candidate["peer_count"] = len(peers)
        candidate["valuation_percentile"] = valuation_pct
        candidate["fcf_percentile"] = fcf_pct
        candidate["growth_percentile"] = growth_pct

        # Ocena asimetrije:
        # 25% FCF kakovost, 25% relativno vrednotenje,
        # 15% padec od vrha ob prestanih finančnih filtrih,
        # 15% izboljšanje zagona, 10% rast in 10% analitikove revizije.
        # Manjkajoče opcijske komponente se ne pretvorijo v ničle.
        components = [
            (candidate["quality"] * 10, 0.25),
            (valuation_pct, 0.25),
            (candidate["drawdown_score"] * 10, 0.15),
            (candidate["momentum_score"] * 10, 0.15),
            (growth_pct, 0.10),
        ]

        if candidate["analyst_revision_score"] is not None:
            components.append((
                candidate["analyst_revision_score"] * 10,
                0.10,
            ))

        total_weight = sum(weight for _, weight in components)
        if total_weight <= 0:
            continue

        score = sum(value * weight for value, weight in components) / total_weight
        candidate["asymmetry_score"] = round(score / 10, 1)

        # Preglednost: vse sestavne komponente ostanejo vidne.
        candidate["score_coverage"] = round(total_weight / 1.0 * 100)
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

    return ranked, audit_by_ticker, errors


def sector_relative_returns(ticker, sector):
    """
    Primerja 20d/60d donos delnice z ustreznim sektorskim ETF.
    Vrne None, kadar podatkov ni.
    """
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
        if frame is None or frame.empty:
            return None, None

        if isinstance(frame.columns, pd.MultiIndex):
            close = frame["Close"]
            if ticker not in close or etf not in close:
                return None, None
            joined = pd.concat(
                [close[ticker].rename("stock"), close[etf].rename("sector")],
                axis=1,
            ).dropna()
        else:
            return None, None

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
# INTRADAY DATA
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


def bars_for_session(frame, date_value, session):
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
        {stamp.date() for stamp in frame.index if stamp.date() < date_value},
        reverse=True,
    )

    for prior_date in dates:
        bars = bars_for_session(frame, prior_date, "regular")
        if not bars.empty:
            close = safe_float(bars["Close"].iloc[-1])
            if close is not None and close > 0:
                return close

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
    current_volume = safe_float(bars["Volume"].iloc[index])
    if current_volume is None or current_volume <= 0:
        return None

    session = "premarket" if timestamp.time() < time(9, 30) else "regular"
    clock = timestamp.strftime("%H:%M")
    previous_dates = sorted({
        stamp.date() for stamp in frame.index
        if stamp.date() < timestamp.date()
    })[-5:]

    prior_volumes = []
    for prior_date in previous_dates:
        prior = bars_for_session(frame, prior_date, session)
        matches = [
            stamp for stamp in prior.index
            if stamp.strftime("%H:%M") == clock
        ]
        if matches:
            value = safe_float(prior.loc[matches[-1], "Volume"])
            if value is not None and value > 0:
                prior_volumes.append(value)

    if not prior_volumes:
        return None

    baseline = float(pd.Series(prior_volumes).median())
    return current_volume / baseline if baseline > 0 else None


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

    relative_strength = gains / losses
    return float(100 - 100 / (1 + relative_strength))


def earnings_clear(ticker, days=5):
    """True: ni earnings v obdobju; None: preverjanje ni uspelo."""
    try:
        earnings = yf.Ticker(ticker).get_earnings_dates(limit=8)
        if earnings is None or len(earnings) == 0:
            return None

        today = datetime.now(NY_TZ).date()

        for raw_date in earnings.index:
            earnings_date = pd.Timestamp(raw_date)
            if earnings_date.tzinfo is not None:
                earnings_date = earnings_date.tz_convert(None)

            delta = (earnings_date.date() - today).days
            if 0 <= delta <= days:
                return False

        return True
    except Exception:
        return None


def make_reversal_signal(ticker, frame, now=None):
    now = now or datetime.now(NY_TZ)
    today = now.date()

    if frame is None or frame.empty:
        return None

    current_day = frame[
        [stamp.date() == today for stamp in frame.index]
    ]
    if current_day.empty:
        return None

    completed = current_day[
        [stamp + timedelta(minutes=5) <= now for stamp in current_day.index]
    ]
    if completed.empty:
        return None

    latest_stamp = completed.index[-1]
    session = "premarket" if latest_stamp.time() < time(9, 30) else "regular"

    bars = bars_for_session(frame, today, session)
    bars = bars[
        [stamp + timedelta(minutes=5) <= now for stamp in bars.index]
    ]

    if len(bars) < 15:
        return None

    previous_close = previous_regular_close(frame, today)
    if previous_close is None:
        return None

    # Ne obravnavaj neznanega earnings statusa kot potrjeno varnega.
    if earnings_clear(ticker, 5) is not True:
        return None

    vwap = session_vwap(bars)
    valid_signals = []

    for index in range(14, len(bars)):
        stamp = bars.index[index]
        close = safe_float(bars["Close"].iloc[index])
        candle_open = safe_float(bars["Open"].iloc[index])
        prior_close = safe_float(bars["Close"].iloc[index - 1])
        current_vwap = safe_float(vwap.iloc[index])
        prior_vwap = safe_float(vwap.iloc[index - 1])

        values = (
            close,
            candle_open,
            prior_close,
            current_vwap,
            prior_vwap,
        )
        if any(value is None for value in values):
            continue

        if session == "premarket":
            reference_price = previous_close
        else:
            regular_bars = bars_for_session(frame, today, "regular")
            if regular_bars.empty:
                continue
            reference_price = safe_float(regular_bars["Open"].iloc[0])
            if reference_price is None or reference_price <= 0:
                continue

        relative_open = (close / reference_price - 1) * 100
        if not -8.0 <= relative_open <= -1.0:
            continue

        crossed_above_vwap = (
            prior_close <= prior_vwap and close > current_vwap
        )
        green_candle = close > candle_open
        relative_vwap = (close / current_vwap - 1) * 100

        if not crossed_above_vwap or not green_candle or relative_vwap < -2:
            continue

        current_rsi = rsi_5m(bars["Close"].iloc[:index + 1])
        volume_ratio = same_time_volume_ratio(frame, stamp, bars, index)
        momentum = (close / prior_close - 1) * 100

        if current_rsi is None or current_rsi >= 35:
            continue
        if volume_ratio is None or volume_ratio < 1.3:
            continue
        if momentum < 0:
            continue

        score = 6.0
        score += min(max(volume_ratio - 1.3, 0) * 0.5, 1.5)
        score += min(max(momentum, 0) * 0.25, 1.0)
        score -= market["penalty"]
        score = round(max(0, min(10, score)), 1)

        if score < 6:
            continue

        valid_signals.append({
            "Ticker": ticker,
            "Čas": stamp.strftime("%H:%M ET"),
            "Seja": "PREMARKET" if session == "premarket" else "REDNA SEJA",
            "Cena": round(close, 2),
            "Rel. open %": round(relative_open, 2),
            "VWAP": round(current_vwap, 2),
            "Rel. VWAP %": round(relative_vwap, 2),
            "Volumen / ista ura x": round(volume_ratio, 2),
            "RSI 5m": round(current_rsi, 1),
            "Momentum %": round(momentum, 2),
            "Ocena filtra": score,
        })

    return valid_signals[-1] if valid_signals else None


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

    results.sort(key=lambda item: item["Ocena filtra"], reverse=True)
    return results[:5]


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
        prior_close = close.shift(1)

        true_range = pd.concat(
            [
                high - low,
                (high - prior_close).abs(),
                (low - prior_close).abs(),
            ],
            axis=1,
        ).max(axis=1)

        atr = safe_float(true_range.rolling(14).mean().iloc[-1])
        return atr if atr is not None and atr > 0 else None
    except Exception:
        return None


# ============================================================
# GEMINI COMMENTARY
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

    model_names = [
        item["name"].split("/")[-1]
        for item in listing.json().get("models", [])
        if "generateContent" in item.get("supportedGenerationMethods", [])
    ]

    if not model_names:
        raise RuntimeError("API ni vrnil modela za generateContent.")

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    last_error = "Klic API-ja ni uspel."

    for model_name in model_names:
        try:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model_name}:generateContent"
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
                    return model_name, text

            last_error = (
                f"{model_name}: HTTP {response.status_code} "
                f"{response.text[:250]}"
            )
        except Exception as error:
            last_error = str(error)

    raise RuntimeError(last_error)


# ============================================================
# PAGE HEADER FIRST, DATA SCANS AFTER
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
    "Ocene so hevristične in ne napovedujejo donosa. "
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

with st.spinner("Pridobivam tržni režim in sektorsko relativno moč..."):
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

progress = st.progress(0, text="Začenjam fundamentalni sken...")
try:
    with st.spinner("Skeniram fundamentals in intraday podatke..."):
        long_candidates, audit, scan_errors = scan_long(tuple(AI_UNIVERSE))
        progress.progress(65, text="Fundamentalni sken končan; preverjam intraday setup-e...")
        reversal_candidates = scan_reversals(tuple(AI_UNIVERSE))
        progress.progress(100, text="Skeniranje končano.")
except Exception as error:
    st.error(f"Skeniranje ni uspelo: {html.escape(str(error)[:400])}")
finally:
    progress.empty()

if scan_errors:
    st.caption(f"Posamezne napake pri tickerjih: {len(scan_errors)}")

best_long = long_candidates[0] if long_candidates else None
best_reversal = reversal_candidates[0] if reversal_candidates else None


# ============================================================
# GOLD LONG CARD AND GREEN REVERSAL CARD
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
                {html.escape(item["ticker"])}
              </div>
              <div style="color:#CBD5E1;font-size:.86rem;margin-top:2px;">
                {html.escape(item["name"])} · {html.escape(item["sector"])}
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
                Zagon 20d {fmt(item["return_20d"], 1, "%")}<br>
                Rast prihodkov {fmt(item["revenue_growth"] * 100, 1, "%")} ·
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
                NI DOVOLJ PODATKOV ZA STROGEGA KANDIDATA
              </div>
              <div style="color:#CBD5E1;font-size:.82rem;margin-top:10px;">
                Kandidat mora prestati finančne filtre, imeti uporabne
                podatke in najmanj pet peerjev za sektorsko primerjavo.
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
    "Sestavljena ocena je presejalno orodje, ne poštena vrednost delnice. "
    "Percentili TSM in MNDY so izračunani znotraj različnih skupin, zato "
    "ne pomenijo neposredne primerjave med podjetjema."
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
    render_table(pd.DataFrame(rotation["rows"]))
else:
    st.info("Sektorski podatki trenutno niso na voljo.")

st.caption(
    "ETF relativna moč je cenovni približek; ne meri neposrednih Wall Street "
    "tokov kapitala. Trenutno priporočilo analitikov ni zgodovinski trend."
)


# ============================================================
# LONG RANKING
# ============================================================

st.subheader("TOP 5 Long · kakovost, vrednotenje, padec in obrat")
st.caption(
    "Padec od 52w vrha prispeva k oceni samo, če podjetje prestane temeljne "
    "filtre. P/S, P/B in EV/EBITDA se primerjajo znotraj ročno določene "
    "skupine; to ni zgodovinsko vrednotenje podjetja."
)

if long_candidates:
    long_rows = []

    for item in long_candidates[:5]:
        fcf_yield = None
        if item["market_cap"] and item["latest_fcf"] is not None:
            fcf_yield = item["latest_fcf"] / item["market_cap"] * 100

        relative20, relative60 = sector_relative_returns(
            item["ticker"],
            item["sector"],
        )

        long_rows.append({
            "Ticker": item["ticker"],
            "Podjetje": item["name"],
            "Sektor": item["sector"],
            "Peerji": item["peer_count"],
            "Asimetrija / 10": item["asymmetry_score"],
            "FCF kakovost / 10": item["quality"],
            "FCF peer percentil": item["fcf_percentile"],
            "Multiple": item["multiple"]["name"],
            "Multiple vrednost": fmt(item["multiple"]["value"]),
            "Vrednotenje peer percentil": item["valuation_percentile"],
            "Rast prihodkov %": fmt(item["revenue_growth"] * 100, 1, "%"),
            "Rastni peer percentil": item["growth_percentile"],
            "FCF pozitivna leta": (
                f"{item['positive_fcf_years']}/{item['fcf_years']}"
            ),
            "Mediana FCF marže %": fmt(
                item["median_fcf_margin"], 1, "%"
            ),
            "CFO / čisti dobiček": fmt(
                item["median_conversion"], 2, "x"
            ),
            "SBC / prihodki %": fmt(item["median_sbc"], 1, "%"),
            "FCF yield %": fmt(fcf_yield, 1, "%"),
            "Padec od 52w vrha %": fmt(item["drawdown_52w"], 1, "%"),
            "Donos 20d %": fmt(item["return_20d"], 1, "%"),
            "Rel. donos vs sektor 20d %": fmt(relative20, 1, "%"),
            "Rel. donos vs sektor 60d %": fmt(relative60, 1, "%"),
            "WS neto revizije 90d": fmt(item["revision_net_90d"], 0),
            "WS trenutna ocena": fmt(
                item["recommendation_mean"], 2
            ),
            "WS implied upside %": fmt(item["analyst_upside"], 1, "%"),
            "Pokritost vhodnih polj": f"{item['coverage']}/100",
        })

    render_table(pd.DataFrame(long_rows))
else:
    st.info(
        "Ni kandidata, ki bi prestal filtre in imel dovolj peerjev za "
        "sektorsko primerjavo."
    )

st.caption(
    "Manjkajoča zgodovina sprememb priporočil ostane neocenjena. Trenutna "
    "ciljna cena analitikov ni obravnavana kot dokaz prihodnjega donosa."
)


# ============================================================
# MNDY AUDIT AND COMPARISON WITH THE TOP PICK
# ============================================================

st.subheader("MNDY proti najbolje uvrščenemu kandidatu")

mndy = audit.get("MNDY")
comparison_tickers = ["MNDY"]

if best_long and best_long["ticker"] != "MNDY":
    comparison_tickers.append(best_long["ticker"])

comparison_rows = []

for ticker in comparison_tickers:
    data = audit.get(ticker)
    if not data:
        continue

    ranked_item = next(
        (item for item in long_candidates if item["ticker"] == ticker),
        None,
    )

    relative20, relative60 = sector_relative_returns(
        ticker,
        data["sector"],
    )

    if ranked_item:
        score_text = f"{ranked_item['asymmetry_score']}/10"
        valuation_pct = ranked_item["valuation_percentile"]
        fcf_pct = ranked_item["fcf_percentile"]
        growth_pct = ranked_item["growth_percentile"]
        peer_count = ranked_item["peer_count"]
    else:
        score_text = "NI UVRŠČEN"
        valuation_pct = None
        fcf_pct = None
        growth_pct = None
        peer_count = None

    comparison_rows.append({
        "Ticker": ticker,
        "Podjetje": data["name"],
        "Sektor": data["sector"],
        "Cena": fmt(data["price"]),
        "P/S": fmt(data.get("ps")),
        "EV/EBITDA": fmt(data.get("ev_ebitda")),
        "FCF yield %": fmt(
            (
                data["latest_fcf"] / data["market_cap"] * 100
                if data.get("market_cap")
                and data.get("latest_fcf") is not None
                else None
            ),
            1,
            "%",
        ),
        "Rast prihodkov %": fmt(
            (
                data["revenue_growth"] * 100
                if data.get("revenue_growth") is not None
                else None
            ),
            1,
            "%",
        ),
        "FCF kakovost / 10": fmt(fcf_quality_score(data), 1),
        "Padec od 52w vrha %": fmt(data.get("drawdown_52w"), 1, "%"),
        "Donos 20d %": fmt(data.get("return_20d"), 1, "%"),
        "Rel. donos vs sektor 20d %": fmt(relative20, 1, "%"),
        "Rel. donos vs sektor 60d %": fmt(relative60, 1, "%"),
        "WS neto revizije 90d": fmt(data.get("revision_net_90d"), 0),
        "WS priporočilo": fmt
