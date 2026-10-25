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
    }
    </style>
    """,
    unsafe_allow_html=True,
)

NY_TZ = ZoneInfo("America/New_York")
LJ_TZ = ZoneInfo("Europe/Ljubljana")
MIN_MARKET_CAP = 2_000_000_000
MIN_DOLLAR_VOLUME = 20_000_000


# ============================================================
# SEKTORSKI UNIVERZUM
# Interleaving sektorjev prepreči, da bi prvih 150 pomenilo
# skoraj samo tehnologijo, ker je bil ticker prej v seznamu.
# ============================================================

SECTOR_GROUPS = {
    "SaaS / Software": [
        "MNDY", "SNOW", "HUBS", "DDOG", "TEAM", "NOW", "CRM", "ADBE",
        "SHOP", "NET", "ZS", "OKTA", "MDB", "ESTC", "PATH", "WDAY",
        "CFLT", "DOCN", "GTLB", "BILL", "ASAN", "IOT", "FSLY", "DT",
        "BSY", "PCOR", "NCNO", "ZM", "DOCU", "TWLO", "PD", "DBX",
        "SMAR", "UPWK", "SPT", "APPN", "PEGA", "FROG", "RNG", "VEEV",
        "TYL", "PTC", "ADSK", "TRMB",
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
    "Industrials": [
        "CAT", "DE", "ETN", "GE", "HON", "PH", "RTX", "LMT",
    ],
    "Energy": ["XOM", "CVX", "SLB", "FSLR", "ENPH", "NXT"],
    "Consumer": [
        "COST", "WMT", "HD", "LOW", "MCD", "NKE", "KO", "PG",
        "F", "GM", "RIVN", "LCID", "CVNA", "UPST", "Z", "W",
    ],
}

# Izmenično dodaj tickerje iz vsake skupine, nato izberi največ 150.
AI_UNIVERSE = []
_max_sector_size = max(len(group) for group in SECTOR_GROUPS.values())
for _index in range(_max_sector_size):
    for _group in SECTOR_GROUPS.values():
        if _index < len(_group):
            _ticker = _group[_index]
            if _ticker not in AI_UNIVERSE:
                AI_UNIVERSE.append(_ticker)
AI_UNIVERSE = AI_UNIVERSE[:150]

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


def sector_for(ticker):
    for sector, members in SECTOR_GROUPS.items():
        if ticker in members:
            return sector
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


def get_statement_row(frame, names):
    if frame is None or frame.empty:
        return None

    normalized = {
        str(index).strip().lower().replace("_", " "): index
        for index in frame.index
    }

    for name in names:
        key = name.strip().lower().replace("_", " ")
        if key in normalized:
            return frame.loc[normalized[key]]

    for key, original in normalized.items():
        if any(name.strip().lower().replace("_", " ") in key for name in names):
            return frame.loc[original]

    return None


def annual_values(frame, names):
    row = get_statement_row(frame, names)
    if row is None:
        return {}

    output = {}
    for column, raw_value in row.items():
        value = safe_float(raw_value)
        if value is not None:
            try:
                output[pd.Timestamp(column).year] = value
            except Exception:
                pass
    return output


def midrank_percentile(values, target, lower_is_better=False):
    valid = [
        value for value in values
        if value is not None and math.isfinite(value)
    ]
    if target is None or len(valid) < 5:
        return None

    below = sum(value < target for value in valid)
    equal = sum(value == target for value in valid)
    percentile = (below + 0.5 * equal) / len(valid) * 100

    if lower_is_better:
        percentile = 100 - percentile
    return round(max(0.0, min(100.0, percentile)))


def get_eps_revision_metrics(ticker_obj):
    """Vrne analitikove EPS-revizije, če jih Yahoo Finance posreduje."""
    net_revisions = None
    estimate_change = None

    try:
        revisions = ticker_obj.eps_revisions
    except Exception:
        revisions = None

    if revisions is not None and not revisions.empty:
        columns = {
            str(column).lower().replace("_", ""): column
            for column in revisions.columns
        }
        up_col = columns.get("uplast30days")
        down_col = columns.get("downlast30days")

        if up_col is not None and down_col is not None:
            selected = []
            for index, row in revisions.iterrows():
                label = str(index).lower().replace(" ", "")
                if "0q" in label or "+1q" in label or "1q" in label:
                    selected.append(row)

            if not selected:
                selected = [row for _, row in revisions.iterrows()]

            ups = sum(safe_float(row.get(up_col)) or 0.0 for row in selected)
            downs = sum(
                safe_float(row.get(down_col)) or 0.0 for row in selected
            )
            if ups or downs:
                net_revisions = int(round(ups - downs))

    try:
        trend = ticker_obj.eps_trend
    except Exception:
        trend = None

    if trend is not None and not trend.empty:
        columns = {
            str(column).lower().replace("_", ""): column
            for column in trend.columns
        }
        current_col = columns.get("current")
        old_col = columns.get("30daysago")

        if current_col is not None and old_col is not None:
            selected = []
            for index, row in trend.iterrows():
                label = str(index).lower().replace(" ", "")
                if "0q" in label or "+1q" in label or "1q" in label:
                    selected.append(row)

            if not selected:
                selected = [row for _, row in trend.iterrows()]

            changes = []
            for row in selected:
                current = safe_float(row.get(current_col))
                old = safe_float(row.get(old_col))
                if current is not None and old not in (None, 0):
                    changes.append((current / old - 1) * 100)

            if changes:
                estimate_change = sum(changes) / len(changes)

    return {
        "eps_revision_net_30d": net_revisions,
        "eps_estimate_change_30d_pct": estimate_change,
    }


# ============================================================
# TRŽNI REŽIM IN SEKTORSKA ROTACIJA
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def get_market_regime():
    try:
        frame = yf.Ticker("SPY").history(
            period="6mo", interval="1d", auto_adjust=True
        )
        if frame is None or len(frame) < 60:
            return {"regime": "NEZNANO", "change20": None, "penalty": 0.0}

        close = frame["Close"].dropna().astype(float)
        if len(close) < 50:
            return {"regime": "NEZNANO", "change20": None, "penalty": 0.0}

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
    etfs = {
        "SaaS / software (IGV)": "IGV",
        "Polprevodniki (SMH)": "SMH",
        "Kibernetska varnost (CIBR)": "CIBR",
        "Nasdaq (QQQ)": "QQQ",
        "Finance (XLF)": "XLF",
        "Zdravstvo (XLV)": "XLV",
        "Industrija (XLI)": "XLI",
        "Energija (XLE)": "XLE",
        "Potrošnja (XLY)": "XLY",
        "Osnovna potrošnja (XLP)": "XLP",
        "Materiali (XLB)": "XLB",
        "Utilities (XLU)": "XLU",
        "Small caps (IWM)": "IWM",
    }

    prices = {}
    for ticker in list(etfs.values()) + ["SPY"]:
        try:
            frame = yf.Ticker(ticker).history(
                period="8mo", interval="1d", auto_adjust=True
            )
            if frame is not None and not frame.empty:
                prices[ticker] = frame["Close"].dropna().astype(float)
        except Exception:
            pass

    if "SPY" not in prices:
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
        if ticker not in prices:
            continue

        rel5 = relative_return(prices[ticker], prices["SPY"], 5)
        rel20 = relative_return(prices[ticker], prices["SPY"], 20)
        rel60 = relative_return(prices[ticker], prices["SPY"], 60)
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

    rows.sort(key=lambda row: row["Rel. 20d % vs SPY"], reverse=True)

    rotation = "NI PODATKOV"
    detail = ""

    if "IGV" in prices and "SMH" in prices:
        joined = pd.concat(
            [prices["IGV"].rename("igv"), prices["SMH"].rename("smh")],
            axis=1,
            join="inner",
        ).dropna()

        if len(joined) > 60:
            ratio = joined["igv"] / joined["smh"]
            change20 = (ratio.iloc[-1] / ratio.iloc[-21] - 1) * 100
            change60 = (ratio.iloc[-1] / ratio.iloc[-61] - 1) * 100
            above_sma20 = bool(
                ratio.iloc[-1] > ratio.rolling(20).mean().iloc[-1]
            )

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
# PODATKI IN SAAS ŠIRINA
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
            [
                "Operating Cash Flow",
                "Total Cash From Operating Activities",
                "Cash Flow From Continuing Operating Activities",
            ],
        )
        capex = annual_values(
            cashflow, ["Capital Expenditure", "Capital Expenditures"]
        )
        sbc = annual_values(
            cashflow, ["Stock Based Compensation", "Share Based Compensation"]
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
            income, ["Total Revenue", "Operating Revenue", "Revenue"]
        )
        ebitda_by_year = annual_values(income, ["EBITDA", "Normalized EBITDA"])

        years = sorted(set(cfo) & set(capex) & set(net_income) & set(revenue))[-5:]
        annual = []
        for year in years:
            annual.append({
                "year": year,
                "cfo": cfo[year],
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

        median_fcf_margin = float(pd.Series(margins).median()) if margins else None
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

        if history is not None and not history.empty and "Close" in history:
            close = history["Close"].dropna().astype(float)
        else:
            close = pd.Series(dtype=float)

        drawdown_52w = None
        return20 = None
        return60 = None
        return120 = None
        above_sma20 = None
        above_sma50 = None

        if len(close) >= 20:
            last = float(close.iloc[-1])
            high_52w = float(close.tail(252).max())
            if high_52w > 0:
                drawdown_52w = (last / high_52w - 1) * 100
            if len(close) >= 21:
                return20 = (last / float(close.iloc[-21]) - 1) * 100
            if len(close) >= 61:
                return60 = (last / float(close.iloc[-61]) - 1) * 100
            if len(close) >= 121:
                return120 = (last / float(close.iloc[-121]) - 1) * 100
            above_sma20 = last > float(close.rolling(20).mean().iloc[-1])
            if len(close) >= 50:
                above_sma50 = last > float(close.rolling(50).mean().iloc[-1])

        try:
            eps = get_eps_revision_metrics(stock)
        except Exception:
            eps = {
                "eps_revision_net_30d": None,
                "eps_estimate_change_30d_pct": None,
            }

        return {
            "ticker": ticker,
            "name": info.get("shortName") or KNOWN_NAMES.get(ticker, ticker),
            "sector": sector_for(ticker),
            "price": price,
            "market_cap": market_cap,
            "average_volume": average_volume,
            "dollar_volume": dollar_volume,
            "cash": cash,
            "debt": debt,
            "net_cash": net_cash,
            "ps": number("priceToSalesTrailing12Months"),
            "peg": number("pegRatio"),
            "pb": number("priceToBook"),
            "ev_ebitda": ev_ebitda,
            "growth": growth,
            "annual": annual,
            "fcf_years": fcf_years,
            "positive_fcf_years": positive_fcf_years,
            "latest_fcf": latest_fcf,
            "latest_ebitda": latest_ebitda,
            "median_fcf_margin": median_fcf_margin,
            "median_conversion": median_conversion,
            "median_sbc": median_sbc,
            "drawdown_52w": drawdown_52w,
            "return20": return20,
            "return60": return60,
            "return120": return120,
            "above_sma20": above_sma20,
            "above_sma50": above_sma50,
            "return20_positive": return20 > 0 if return20 is not None else None,
            "recommendation_mean": number("recommendationMean"),
            "analyst_upside": analyst_upside,
            **eps,
        }
    except Exception:
        return None


def calculate_saas_breadth(records):
    members = [
        ticker for ticker in SECTOR_GROUPS["SaaS / Software"]
        if ticker in AI_UNIVERSE
    ]
    available = [records[ticker] for ticker in members if ticker in records]

    def pct_true(rows, key):
        if not rows:
            return None
        return 100 * sum(bool(row[key]) for row in rows) / len(rows)

    positive20 = [
        row for row in available
        if row.get("return20_positive") is not None
    ]
    above20 = [
        row for row in available if row.get("above_sma20") is not None
    ]
    above50 = [
        row for row in available if row.get("above_sma50") is not None
    ]
    revisions = [
        row for row in available
        if row.get("eps_revision_net_30d") is not None
    ]
    estimates = [
        row for row in available
        if row.get("eps_estimate_change_30d_pct") is not None
    ]

    positive_revision_share = None
    if revisions:
        positive_revision_share = (
            100
            * sum(row["eps_revision_net_30d"] > 0 for row in revisions)
            / len(revisions)
        )

    average_estimate_change = None
    if estimates:
        average_estimate_change = sum(
            row["eps_estimate_change_30d_pct"] for row in estimates
        ) / len(estimates)

    return {
        "universe_count": len(members),
        "positive20_count": sum(bool(row["return20_positive"]) for row in positive20),
        "positive20_coverage": len(positive20),
        "positive20_pct": pct_true(positive20, "return20_positive"),
        "above20_pct": pct_true(above20, "above_sma20"),
        "above50_pct": pct_true(above50, "above_sma50"),
        "above20_coverage": len(above20),
        "above50_coverage": len(above50),
        "revision_coverage": len(revisions),
        "positive_revision_share": positive_revision_share,
        "estimate_coverage": len(estimates),
        "average_estimate_change": average_estimate_change,
    }


# ============================================================
# LONG FILTRI IN RAZVRSTITEV
# ============================================================

def liquidity_reasons(data):
    reasons = []
    market_cap = data.get("market_cap")
    dollar_volume = data.get("dollar_volume")

    if market_cap is None:
        reasons.append("Yahoo Finance ni vrnil market cap podatka")
    elif market_cap < MIN_MARKET_CAP:
        reasons.append(
            f"market cap {market_cap / 1e9:.2f}B USD je pod pragom 2.00B USD"
        )

    if dollar_volume is None:
        missing = []
        if data.get("price") is None:
            missing.append("cena")
        if data.get("average_volume") is None:
            missing.append("povprečni volumen")
        suffix = f" (manjka: {', '.join(missing)})" if missing else ""
        reasons.append("dolarskega prometa ni mogoče izračunati" + suffix)
    elif dollar_volume < MIN_DOLLAR_VOLUME:
        reasons.append(
            f"povprečni dolarski promet {dollar_volume / 1e6:.2f}M USD "
            "je pod pragom 20.00M USD"
        )

    return reasons


def is_liquid(data):
    return not liquidity_reasons(data)


def get_multiple(data):
    name = SECTOR_MULTIPLE.get(data["sector"])
    field = {
        "P/S": "ps",
        "P/B": "pb",
        "EV/EBITDA": "ev_ebitda",
    }.get(name)
    value = safe_float(data.get(field)) if field else None
    if value is None or value <= 0:
        value = None
    return {"name": name or "NI PODATKA", "value": value}


def quality_score(data):
    parts = []
    years = data.get("fcf_years", 0)

    if years >= 3:
        parts.append((data["positive_fcf_years"] / years * 10, 0.25))
    if data.get("median_fcf_margin") is not None:
        parts.append((
            max(0.0, min(10.0, data["median_fcf_margin"] / 2)), 0.25
        ))
    if data.get("median_conversion") is not None:
        parts.append((
            max(0.0, min(10.0, data["median_conversion"] * 5)), 0.20
        ))
    if data.get("median_sbc") is not None:
        parts.append((
            max(0.0, min(10.0, 10 - data["median_sbc"] / 2)), 0.15
        ))
    if data.get("net_cash") is not None:
        parts.append((8.0 if data["net_cash"] >= 0 else 3.0, 0.15))

    if len(parts) < 4:
        return None

    weight = sum(item[1] for item in parts)
    if weight <= 0:
        return None

    result = sum(value * part_weight for value, part_weight in parts) / weight
    return round(max(0.0, min(10.0, result)), 1)


def long_filter_reasons(data):
    reasons = liquidity_reasons(data)
    if reasons:
        return reasons

    if data.get("fcf_years", 0) < 3:
        reasons.append("manj kot 3 leta primerljivih izkazov")
    if data.get("latest_fcf") is None or data["latest_fcf"] <= 0:
        reasons.append("zadnji letni FCF ni pozitiven")
    if data.get("fcf_years", 0) >= 3 and data.get("positive_fcf_years", 0) < 2:
        reasons.append("FCF ni pozitiven v vsaj 2 od zadnjih 3+ let")
    if data.get("median_fcf_margin") is None or data["median_fcf_margin"] < 5:
        reasons.append("mediana FCF marže je pod 5 % ali manjka")
    if data.get("median_conversion") is None or data["median_conversion"] < 0.7:
        reasons.append("CFO/čisti dobiček je pod 0,7x ali manjka")
    if data.get("median_sbc") is None:
        reasons.append("SBC podatek ni na voljo")
    elif data["median_sbc"] > 15:
        reasons.append("SBC presega 15 % prihodkov")
    if data.get("growth") is None or data["growth"] < 0.10:
        reasons.append("rast prihodkov je pod 10 % ali manjka")
    if data.get("net_cash") is None:
        reasons.append("neto denar/dolg ni na voljo")
    elif data["net_cash"] < 0:
        ebitda = data.get("latest_ebitda")
        if ebitda is None or ebitda <= 0:
            reasons.append("neto dolg in ni pozitivnega EBITDA")
        elif abs(data["net_cash"]) / ebitda > 2.5:
            reasons.append("net debt/EBITDA presega 2,5x")
    if data.get("drawdown_52w") is None:
        reasons.append("ni dovolj zgodovine za izračun 52w padca")
    if data.get("return20") is None or data.get("return60") is None:
        reasons.append("ni dovolj zgodovine za izračun 20d/60d zagona")

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


def momentum_score(return20, return60, return120):
    if return20 is None or return60 is None:
        return None
    score = 5.0
    if return20 > 0:
        score += 2.0
    if return20 > return60 / 3:
        score += 1.5
    if return60 > -15:
        score += 1.0
    if return120 is not None and return20 > return120 / 6:
        score += 0.5
    if return20 < -10:
        score -= 2.0
    return round(max(0.0, min(10.0, score)), 1)


@st.cache_data(ttl=1800, show_spinner=False)
def scan_long(universe):
    records = []
    errors = []

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(get_stock_data, t): t for t in universe}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                data = future.result()
                if not data:
                    errors.append(f"{ticker}: brez podatkov")
                    continue

                data["multiple"] = get_multiple(data)
                data["quality"] = quality_score(data)
                data["coverage"] = coverage_score(data)
                data["reasons"] = long_filter_reasons(data)
                data["drawdown_score"] = drawdown_score(data.get("drawdown_52w"))
                data["momentum_score"] = momentum_score(
                    data.get("return20"),
                    data.get("return60"),
                    data.get("return120"),
                )
                net = data.get("eps_revision_net_30d")
                data["revision_score"] = (
                    max(0.0, min(10.0, 5.0 + net))
                    if net is not None
                    else None
                )
                records.append(data)
            except Exception as error:
                errors.append(f"{ticker}: {error}")

    peers_by_sector = {}
    for data in records:
        if is_liquid(data) and data["multiple"]["value"] is not None:
            peers_by_sector.setdefault(data["sector"], []).append(data)

    ranked = []

    for candidate in records:
        if candidate["reasons"] or candidate["quality"] is None:
            continue
        if candidate["drawdown_score"] is None or candidate["momentum_score"] is None:
            candidate["reasons"].append("manjka podatek o padcu ali zagonu")
            continue

        peers = [
            peer for peer in peers_by_sector.get(candidate["sector"], [])
            if peer["multiple"]["name"] == candidate["multiple"]["name"]
            and peer["multiple"]["value"] is not None
        ]
        if len(peers) < 5:
            candidate["reasons"].append(
                f"le {len(peers)} primerljivih peerjev; potrebnih je vsaj 5"
            )
            continue

        valuation = midrank_percentile(
            [peer["multiple"]["value"] for peer in peers],
            candidate["multiple"]["value"],
            lower_is_better=True,
        )
        fcf_pct = midrank_percentile(
            [peer["quality"] for peer in peers if peer["quality"] is not None],
            candidate["quality"],
        )
        growth_pct = midrank_percentile(
            [peer["growth"] for peer in peers if peer["growth"] is not None],
            candidate["growth"],
        )

        if valuation is None or fcf_pct is None or growth_pct is None:
            candidate["reasons"].append("premalo podatkov za peer percentile")
            continue

        candidate["peer_count"] = len(peers)
        candidate["valuation_percentile"] = valuation
        candidate["fcf_percentile"] = fcf_pct
        candidate["growth_percentile"] = growth_pct

        parts = [
            (candidate["quality"] * 10, 0.25),
            (valuation, 0.25),
            (candidate["drawdown_score"] * 10, 0.15),
            (candidate["momentum_score"] * 10, 0.15),
            (growth_pct, 0.10),
        ]
        if candidate["revision_score"] is not None:
            parts.append((candidate["revision_score"] * 10, 0.10))

        total_weight = sum(weight for _, weight in parts)
        if total_weight <= 0:
            continue

        raw_score = sum(value * weight for value, weight in parts) / total_weight
        candidate["asymmetry_score"] = round(raw_score / 10, 1)
        ranked.append(candidate)

    ranked.sort(
        key=lambda item: (
            item["asymmetry_score"],
            item["quality"],
            item["coverage"],
        ),
        reverse=True,
    )
    audit = {item["ticker"]: item for item in records}
    return ranked, audit, errors


# ============================================================
# ATR IN INTRADAY REVERSAL
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
        true_range = pd.concat(
            [
                high - low,
                (high - previous).abs(),
                (low - previous).abs(),
            ],
            axis=1,
        ).max(axis=1)

        value = safe_float(true_range.rolling(14).mean().iloc[-1])
        return value if value is not None and value > 0 else None
    except Exception:
        return None


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


def session_bars(frame, day, session):
    if frame is None or frame.empty:
        return pd.DataFrame()

    today = frame[[stamp.date() == day for stamp in frame.index]]
    if session == "premarket":
        return today.between_time("04:00", "09:29")
    return today.between_time("09:30", "15:59")


def previous_regular_close(frame, day):
    prior_days = sorted(
        {stamp.date() for stamp in frame.index if stamp.date() < day},
        reverse=True,
    )
    for prior_day in prior_days:
        bars = session_bars(frame, prior_day, "regular")
        if not bars.empty:
            close = safe_float(bars["Close"].iloc[-1])
            if close is not None and close > 0:
                return close
    return None


def calculate_vwap(bars):
    typical = (
        bars["High"].astype(float)
        + bars["Low"].astype(float)
        + bars["Close"].astype(float)
    ) / 3
    volume = bars["Volume"].astype(float).clip(lower=0)
    denominator = volume.cumsum().replace(0, float("nan"))
    return (typical * volume).cumsum() / denominator


def same_time_volume_ratio(frame, stamp, bars, index):
    current = safe_float(bars["Volume"].iloc[index])
    if current is None or current <= 0:
        return None

    session = "premarket" if stamp.time() < time(9, 30) else "regular"
    clock = stamp.strftime("%H:%M")
    previous_days = sorted({
        item.date() for item in frame.index if item.date() < stamp.date()
    })[-5:]

    samples = []
    for prior_day in previous_days:
        prior = session_bars(frame, prior_day, session)
        matches = [
            item for item in prior.index
            if item.strftime("%H:%M") == clock
        ]
        if matches:
            value = safe_float(prior.loc[matches[-1], "Volume"])
            if value is not None and value > 0:
                samples.append(value)

    if not samples:
        return None
    baseline = float(pd.Series(samples).median())
    return current / baseline if baseline > 0 else None


def calculate_rsi(values, period=14):
    close = pd.Series(values, dtype=float)
    if len(close) < period + 1:
        return None

    changes = close.diff()
    gains = changes.clip(lower=0).rolling(period).mean().iloc[-1]
    losses = (-changes.clip(upper=0)).rolling(period).mean().iloc[-1]

    if pd.isna(gains) or pd.isna(losses):
        return None
    if losses == 0:
        return 100.0 if gains > 0 else 50.0

    ratio = gains / losses
    return float(100 - 100 / (1 + ratio))


@st.cache_data(ttl=1800, show_spinner=False)
def earnings_clear(ticker, days=5):
    """True: v prihodnjih dneh ni earnings; None: vira ni bilo mogoče preveriti."""
    try:
        dates = yf.Ticker(ticker).get_earnings_dates(limit=8)
        if dates is None or len(dates) == 0:
            return None

        today = datetime.now(NY_TZ).date()
        for raw_date in dates.index:
            value = pd.Timestamp(raw_date)
            if value.tzinfo is not None:
                value = value.tz_convert(None)
            if 0 <= (value.date() - today).days <= days:
                return False
        return True
    except Exception:
        return None


def reversal_signal(ticker, frame, now=None):
    now = now or datetime.now(NY_TZ)
    day = now.date()

    if frame is None or frame.empty:
        return None

    today = frame[[stamp.date() == day for stamp in frame.index]]
    if today.empty:
        return None

    completed = today[
        [stamp + timedelta(minutes=5) <= now for stamp in today.index]
    ]
    if completed.empty:
        return None

    last_stamp = completed.index[-1]
    session = "premarket" if last_stamp.time() < time(9, 30) else "regular"
    bars = session_bars(frame, day, session)
    bars = bars[
        [stamp + timedelta(minutes=5) <= now for stamp in bars.index]
    ]
    if len(bars) < 15:
        return None

    prior_close = previous_regular_close(frame, day)
    if prior_close is None or earnings_clear(ticker, 5) is not True:
        return None

    vwap = calculate_vwap(bars)
    signals = []

    for index in range(14, len(bars)):
        stamp = bars.index[index]
        close = safe_float(bars["Close"].iloc[index])
        candle_open = safe_float(bars["Open"].iloc[index])
        prev_close = safe_float(bars["Close"].iloc[index - 1])
        current_vwap = safe_float(vwap.iloc[index])
        prev_vwap = safe_float(vwap.iloc[index - 1])

        if any(value is None for value in (
            close, candle_open, prev_close, current_vwap, prev_vwap
        )):
            continue

        # Premarket gap in redna seja se merita glede na prejšnji redni close.
        rel_open = (close / prior_close - 1) * 100
        if not -8.0 <= rel_open <= -1.0:
            continue

        reclaimed = prev_close <= prev_vwap and close > current_vwap
        rel_vwap = (close / current_vwap - 1) * 100
        if not reclaimed or close <= candle_open or rel_vwap < -2.0:
            continue

        rsi = calculate_rsi(bars["Close"].iloc[:index + 1])
        volume_ratio = same_time_volume_ratio(frame, stamp, bars, index)
        momentum = (close / prev_close - 1) * 100

        if rsi is None or rsi >= 35:
            continue
        if volume_ratio is None or volume_ratio < 1.3:
            continue
        if momentum <= 0:
            continue

        score = 6.0
        score += min(max(volume_ratio - 1.3, 0) * 0.5, 1.5)
        score += min(momentum * 0.25, 1.0)
        score -= market["penalty"]
        score = round(max(0.0, min(10.0, score)), 1)
        if score < 6.0:
            continue

        signals.append({
            "Ticker": ticker,
            "Čas": stamp.strftime("%H:%M ET"),
            "Seja": "PREMARKET" if stamp.time() < time(9, 30) else "REDNA SEJA",
            "Cena": round(close, 2),
            "Rel. vs prejšnji close %": round(rel_open, 2),
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
    output = []
    now = datetime.now(NY_TZ)

    for ticker in universe:
        try:
            signal = reversal_signal(ticker, get_intraday_history(ticker), now)
            if signal:
                output.append(signal)
        except Exception:
            continue

    output.sort(key=lambda row: row["Ocena filtra"], reverse=True)
    return output[:5]


# ============================================================
# RELATIVNA MOČ DELNICE PROTI SEKTORJU
# ============================================================

def sector_relative_returns(ticker, sector):
    etf = SECTOR_ETF.get(sector)
    if not etf:
        return None, None

    try:
        stock = yf.Ticker(ticker).history(
            period="6mo", interval="1d", auto_adjust=True
        )
        benchmark = yf.Ticker(etf).history(
            period="6mo", interval="1d", auto_adjust=True
        )
        if stock is None or benchmark is None or stock.empty or benchmark.empty:
            return None, None

        joined = pd.concat(
            [
                stock["Close"].rename("stock"),
                benchmark["Close"].rename("sector"),
            ],
            axis=1,
            join="inner",
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
# GLAVNI IZRAČUNI IN PRIKAZ
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

st.caption(
    "Presejalno orodje, ne napoved donosa ali samodejno naročilo."
)

st.sidebar.markdown("### Nastavitve")
api_key = st.sidebar.text_input(
    "Gemini API ključ (neobvezno)",
    type="password",
)
st.sidebar.caption(f"Tickerjev v skenu: {len(AI_UNIVERSE)}")
st.sidebar.caption("Yahoo Finance lahko vrne zakasnjene ali manjkajoče podatke.")

if st.button("Osveži skene"):
    scan_long.clear()
    scan_reversals.clear()
    get_stock_data.clear()
    get_intraday_history.clear()
    get_market_regime.clear()
    get_rotation.clear()
    get_atr.clear()
    earnings_clear.clear()
    st.rerun()

with st.spinner("Nalagam tržni režim in sektorsko relativno moč..."):
    market = get_market_regime()
    rotation = get_rotation()

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Tržni režim:** {market['regime']}")
if market["change20"] is not None:
    st.sidebar.caption(f"SPY 20d: {market['change20']:+.2f}%")

progress = st.progress(0)
long_candidates = []
audit = {}
scan_errors = []
reversal_candidates = []

try:
    with st.spinner("Skeniram fundamentalne podatke in intraday nastavitve..."):
        long_candidates, audit, scan_errors = scan_long(tuple(AI_UNIVERSE))
        progress.progress(60)
        reversal_candidates = scan_reversals(tuple(AI_UNIVERSE))
        progress.progress(100)
except Exception as error:
    st.error(f"Skeniranje ni uspelo: {str(error)[:400]}")
finally:
    progress.empty()

if scan_errors:
    st.caption(f"Podatkov ni bilo mogoče dobiti za {len(scan_errors)} tickerjev.")

best_long = long_candidates[0] if long_candidates else None
best_reversal = reversal_candidates[0] if reversal_candidates else None
saas = calculate_saas_breadth(audit)


# Dve dinamični kartici
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
              <div style="color:#CBD5E1;font-size:.86rem;">
                {html.escape(item["name"])} · {html.escape(item["sector"])}
              </div>
              <div style="color:#F8FAFC;font-size:1rem;margin-top:10px;">
                Cena {fmt(item["price"])} · Ocena {item["asymmetry_score"]}/10
              </div>
              <div style="color:#CBD5E1;font-size:.78rem;margin-top:8px;line-height:1.7;">
                FCF kakovost {fmt(item["quality"], 1)}/10 ·
                FCF peer percentil {item["fcf_percentile"]}/100<br>
                {html.escape(item["multiple"]["name"])} {fmt(item["multiple"]["value"])} ·
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
                Ni delnice, ki bi prestala filtre in imela dovolj peer podatkov.
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
              <div style="color:#CBD5E1;font-size:.86rem;">
                {html.escape(item["Seja"])} · {html.escape(item["Čas"])}
              </div>
              <div style="color:#F8FAFC;font-size:1rem;margin-top:10px;">
                Cena {item["Cena"]} · Ocena filtra {item["Ocena filtra"]}/10
              </div>
              <div style="color:#CBD5E1;font-size:.78rem;margin-top:8px;line-height:1.7;">
                Padec vs prejšnji close {item["Rel. vs prejšnji close %"]:+.2f}% ·
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
                Noben ticker trenutno ne prestane vseh reversal pogojev.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# Capital Rotation Radar in SaaS širina
st.subheader("Capital Rotation Radar")

rotation_html = (
    "<div class='ledger-card'>"
    "<div style='color:#FBBF24;font-weight:700;font-size:1rem;'>"
    + html.escape(rotation["rotation"])
    + "</div>"
    "<div style='color:#94A3B8;font-size:.82rem;margin-top:6px;'>"
    + "Tržni režim: " + html.escape(market["regime"])
    + "</div>"
)

if rotation.get("detail"):
    rotation_html += (
        "<div style='color:#94A3B8;font-size:.82rem;margin-top:6px;'>"
        + html.escape(rotation["detail"])
        + "</div>"
    )

rotation_html += "</div>"
st.markdown(rotation_html, unsafe_allow_html=True)

if rotation["rows"]:
    render_table(pd.DataFrame(rotation["rows"]))
else:
    st.info("Sektorski podatki trenutno niso na voljo.")

st.markdown("#### Širina gibanja SaaS")
breadth_table = pd.DataFrame([
    {
        "Meritev": "SaaS delnice s pozitivnim 20d donosom",
        "Rezultat": fmt(saas["positive20_pct"], 1, "%"),
        "Podatki": f"{saas['positive20_count']}/{saas['positive20_coverage']}",
    },
    {
        "Meritev": "SaaS delnice nad 20-dnevnim povprečjem",
        "Rezultat": fmt(saas["above20_pct"], 1, "%"),
        "Podatki": f"{saas['above20_coverage']}/{saas['universe_count']}",
    },
    {
        "Meritev": "SaaS delnice nad 50-dnevnim povprečjem",
        "Rezultat": fmt(saas["above50_pct"], 1, "%"),
        "Podatki": f"{saas['above50_coverage']}/{saas['universe_count']}",
    },
    {
        "Meritev": "Podjetja s pozitivnim neto EPS-revizijskim trendom, 30d",
        "Rezultat": fmt(saas["positive_revision_share"], 1, "%"),
        "Podatki": f"{saas['revision_coverage']}/{saas['universe_count']}",
    },
    {
        "Meritev": "Povprečna sprememba EPS-ocene v 30 dneh",
        "Rezultat": fmt(saas["average_estimate_change"], 2, "%"),
        "Podatki": f"{saas['estimate_coverage']}/{saas['universe_count']}",
    },
])
render_table(breadth_table)

st.caption(
    "SaaS širina in EPS-revizije vključujejo samo delnice z razpoložljivimi "
    "podatki. IGV/SMH in sektorski ETF-ji merijo relativno gibanje cen, "
    "ne neposrednih tokov kapitala. Skener ne uporablja izmišljene "
    "zgodovinske P/S vrednosti."
)


# TOP 5 Long
st.subheader("TOP 5 Long · temeljni in cenovni pregled")

if long_candidates:
    long_rows = []
    for item in long_candidates[:5]:
        fcf_yield = (
            item["latest_fcf"] / item["market_cap"] * 100
            if item["market_cap"] and item["latest_fcf"] is not None
            else None
        )
        rel20, rel60 = sector_relative_returns(
            item["ticker"], item["sector"]
        )

        long_rows.append({
            "Ticker": item["ticker"],
            "Podjetje": item["name"],
            "Sektor": item["sector"],
            "Cena": fmt(item["price"]),
            "Ocena / 10": item["asymmetry_score"],
            "P/S": fmt(item["ps"]),
            "PEG": fmt(item["peg"]),
            "FCF kakovost / 10": item["quality"],
            "FCF yield %": fmt(fcf_yield, 1, "%"),
            "Vrednotenje peer percentil": item["valuation_percentile"],
            "Rast prihodkov %": fmt(item["growth"] * 100, 1, "%"),
            "Padec od 52w vrha %": fmt(item["drawdown_52w"], 1, "%"),
            "Rel. donos vs sektor 20d %": fmt(rel20, 1, "%"),
            "Rel. donos vs sektor 60d %": fmt(rel60, 1, "%"),
            "EPS neto revizije 30d": fmt(item["eps_revision_net_30d"], 0),
            "EPS sprememba ocene 30d %": fmt(
                item["eps_estimate_change_30d_pct"], 1, "%"
            ),
            "Peerji": item["peer_count"],
            "Pokritost podatkov %": item["coverage"],
        })

    render_table(pd.DataFrame(long_rows))
else:
    st.info("Ni Long kandidata, ki bi prestal filtre in peer preverjanje.")


# MNDY in konkretni razlogi, če je izločen
st.subheader("MNDY · status filtrov")

mndy = audit.get("MNDY")
if mndy is None:
    st.warning("Za MNDY ni bilo mogoče pridobiti dovolj podatkov.")
else:
    mndy_ranked = next(
        (item for item in long_candidates if item["ticker"] == "MNDY"),
        None,
    )

    if mndy_ranked:
        st.success(
            f"MNDY je prestal Long filtre in je uvrščen "
            f"z oceno {mndy_ranked['asymmetry_score']}/10."
        )
    else:
        reasons = list(mndy.get("reasons", []))
        if mndy.get("quality") is None:
            reasons.append("ni dovolj podatkov za izračun FCF kakovosti")
        if mndy.get("multiple") and mndy["multiple"]["value"] is None:
            reasons.append(
                f"manjka veljaven {mndy['multiple']['name']} za primerjavo"
            )
        if not reasons:
            reasons.append(
                "ni izpolnil pogojev peer primerjave ali razvrstitve"
            )

        st.warning("MNDY trenutno ni uvrščen. Razlogi:")
        for reason in dict.fromkeys(reasons):
            st.write(f"- {reason}")

    st.caption(
        "Uvrstitev pomeni le, da je kandidat prestal pravila te hevristike. "
        "Ni dokaz, da je delnica podcenjena ali da bo prinesla donos."
    )


# TOP 5 intraday/premarket reversal
st.subheader("TOP 5 Intraday Reversal")

st.caption(
    "Premarket in redna seja imata ločen VWAP. Padec se meri proti "
    "prejšnjemu rednemu zaprtju; volumen primerja svečo z isto uro "
    "v razpoložljivih prejšnjih sejah."
)

if reversal_candidates:
    render_table(pd.DataFrame(reversal_candidates))
else:
    st.info(
        "NI STROGEGA KANDIDATA. Intraday oziroma premarket podatki "
        "trenutno ne izpolnjujejo vseh pogojev."
    )z
