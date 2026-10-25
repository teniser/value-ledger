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

# Izmenično dodaj tickerje sektorjev, da prvih 150 ni skoraj samo tehnologija.
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

ETF_SECTOR_LABELS = {
    "IGV": "SaaS / Software",
    "CIBR": "Cybersecurity",
    "SMH": "Semiconductors / Hardware",
    "QQQ": "Large Tech / Internet",
    "XLF": "Financials / Fintech",
    "XLV": "Healthcare",
    "XLI": "Industrials",
    "XLE": "Energy",
    "XLY": "Consumer",
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
                safe_float(row.get(down_col)) or 0.0
                for row in selected
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
# TRŽNI REŽIM IN CAPITAL ROTATION RADAR
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


@st.cache_data(ttl=300, show_spinner=False)
def get_rotation():
    etfs = {
        "SaaS / Software": "IGV",
        "Cybersecurity": "CIBR",
        "Semiconductors / Hardware": "SMH",
        "Large Tech / Internet": "QQQ",
        "Financials / Fintech": "XLF",
        "Healthcare": "XLV",
        "Industrials": "XLI",
        "Energy": "XLE",
        "Consumer": "XLY",
        "Osnovna potrošnja": "XLP",
        "Materiali": "XLB",
        "Utilities": "XLU",
        "Small caps": "IWM",
    }

    prices = {}
    for ticker in list(etfs.values()) + ["SPY"]:
        try:
            frame = yf.Ticker(ticker).history(
                period="8mo",
                interval="1d",
                auto_adjust=True,
            )
            if frame is not None and not frame.empty:
                prices[ticker] = frame["Close"].dropna().astype(float)
        except Exception:
            continue

    if "SPY" not in prices:
        return {
            "rows": [],
            "rotation": "NI PODATKOV",
            "detail": "",
        }

    def relative_return(series, benchmark, days):
        joined = pd.concat(
            [
                series.rename("sector"),
                benchmark.rename("spy"),
            ],
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
        if ticker not in prices:
            continue

        rel5 = relative_return(prices[ticker], prices["SPY"], 5)
        rel20 = relative_return(prices[ticker], prices["SPY"], 20)
        rel60 = relative_return(prices[ticker], prices["SPY"], 60)

        if rel5 is None or rel20 is None or rel60 is None:
            continue

        early_turn = rel5 > 0 and rel20 > 0 and rel60 < 0

        if early_turn:
            status = "MOŽEN ZGODNJI OBRAT"
        elif rel20 > 0 and rel60 > 0:
            status = "RELATIVNO VODI"
        elif rel5 < 0 and rel20 < 0 and rel60 > 0:
            status = "SLABI"
        elif rel20 < 0:
            status = "ZAOSTAJA"
        else:
            status = "MEŠANO"

        rows.append({
            "ETF": ticker,
            "Sektor": label,
            "Rel. 5d % vs SPY": round(rel5, 2),
            "Rel. 20d % vs SPY": round(rel20, 2),
            "Rel. 60d % vs SPY": round(rel60, 2),
            "Zgodnji obrat navzgor": early_turn,
            "Oznaka": status,
        })

    rows.sort(
        key=lambda row: row["Rel. 20d % vs SPY"],
        reverse=True,
    )

    rotation = "NI PODATKOV"
    detail = ""

    if "IGV" in prices and "SMH" in prices:
        joined = pd.concat(
            [
                prices["IGV"].rename("igv"),
                prices["SMH"].rename("smh"),
            ],
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

    return {
        "rows": rows,
        "rotation": rotation,
        "detail": detail,
    }


# ============================================================
# FUNDAMENTALNI PODATKI
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}

        def number(key):
            return safe_float(info.get(key))

        price = number("currentPrice") or number("regularMarketPrice")
        market_cap = number("marketCap")
        average_volume = number("averageVolume")

        dollar_volume = None
        if price is not None and average_volume is not None:
            dollar_volume = price * average_volume

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
            for row in annual
            if row["revenue"] > 0
        ]
        conversions = [
            row["cfo"] / row["net_income"]
            for row in annual
            if row["net_income"] > 0
        ]
        sbc_rates = [
            row["sbc"] / row["revenue"] * 100
            for row in annual
            if row["sbc"] is not None and row["revenue"] > 0
        ]

        median_fcf_margin = (
            float(pd.Series(margins).median()) if margins else None
        )
        median_conversion = (
            float(pd.Series(conversions).median()) if conversions else None
        )
        median_sbc = (
            float(pd.Series(sbc_rates).median()) if sbc_rates else None
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

        try:
            history = stock.history(
                period="2y",
                interval="1d",
                auto_adjust=True,
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
            eps_metrics = get_eps_revision_metrics(stock)
        except Exception:
            eps_metrics = {
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
            "return20_positive": (
                return20 > 0 if return20 is not None else None
            ),
            "recommendation_mean": number("recommendationMean"),
            "analyst_upside": analyst_upside,
            **eps_metrics,
        }

    except Exception:
        return None


# ============================================================
# SEKTORSKI ZAGON IN ŠIRINA
# ============================================================

def calculate_sector_metrics(records, rotation_data):
    """
    Združi relativno moč sektorskega ETF-ja z gibanjem delnic v sektorju.
    To je cenovni/analitikovski približek sentimenta, ne neposredni tok kapitala.
    """
    rotation_rows = rotation_data.get("rows", [])
    rows_by_etf = {
        row.get("ETF"): row
        for row in rotation_rows
        if row.get("ETF")
    }

    output = {}

    for sector, members in SECTOR_GROUPS.items():
        available = [
            records[ticker]
            for ticker in members
            if ticker in records
        ]

        rows = []
        for ticker in members:
            etf = SECTOR_ETF.get(sector)
            rotation_row = rows_by_etf.get(etf, {})
            if ticker in records:
                rows.append(records[ticker])

        positive20 = [
            row for row in rows
            if row.get("return20_positive") is not None
        ]
        above20 = [
            row for row in rows
            if row.get("above_sma20") is not None
        ]
        above50 = [
            row for row in rows
            if row.get("above_sma50") is not None
        ]
        revision_rows = [
            row for row in rows
            if row.get("eps_revision_net_30d") is not None
        ]
        estimate_rows = [
            row for row in rows
            if row.get("eps_estimate_change_30d_pct") is not None
        ]

        positive20_pct = (
            100 * sum(bool(row["return20_positive"]) for row in positive20)
            / len(positive20)
            if positive20 else None
        )
        above20_pct = (
            100 * sum(bool(row["above_sma20"]) for row in above20)
            / len(above20)
            if above20 else None
        )
        above50_pct = (
            100 * sum(bool(row["above_sma50"]) for row in above50)
            / len(above50)
            if above50 else None
        )
        positive_revision_pct = (
            100
            * sum(row["eps_revision_net_30d"] > 0 for row in revision_rows)
            / len(revision_rows)
            if revision_rows else None
        )
        average_eps_change = (
            sum(row["eps_estimate_change_30d_pct"] for row in estimate_rows)
            / len(estimate_rows)
            if estimate_rows else None
        )

        rel5 = safe_float(rotation_row.get("Rel. 5d % vs SPY"))
        rel20 = safe_float(rotation_row.get("Rel. 20d % vs SPY"))
        rel60 = safe_float(rotation_row.get("Rel. 60d % vs SPY"))
        early_turn = bool(rotation_row.get("Zgodnji obrat navzgor", False))

        # Skale se omejijo na 0–10, da ekstremna dnevna gibanja ne prevladajo.
        rel5_score = (
            max(0.0, min(10.0, 5.0 + rel5 * 0.5))
            if rel5 is not None else None
        )
        rel20_score = (
            max(0.0, min(10.0, 5.0 + rel20 * 0.35))
            if rel20 is not None else None
        )
        breadth20_score = (
            above20_pct / 10.0 if above20_pct is not None else None
        )
        breadth50_score = (
            above50_pct / 10.0 if above50_pct is not None else None
        )
        revision_score = (
            positive_revision_pct / 10.0
            if positive_revision_pct is not None else None
        )

        components = [
            (rel20_score, 0.25),
            (rel5_score, 0.15),
            (breadth20_score, 0.25),
            (breadth50_score, 0.15),
            (revision_score, 0.20),
        ]
        valid_components = [
            (value, weight)
            for value, weight in components
            if value is not None
        ]

        if valid_components:
            total_weight = sum(weight for _, weight in valid_components)
            score = sum(
                value * weight for value, weight in valid_components
            ) / total_weight
            if early_turn:
                score += 0.5
            score = round(max(0.0, min(10.0, score)), 1)
        else:
            score = None

        output[sector] = {
            "sector": sector,
            "etf": SECTOR_ETF.get(sector),
            "sector_score": score,
            "rel5": rel5,
            "rel20": rel20,
            "rel60": rel60,
            "early_turn": early_turn,
            "positive20_pct": positive20_pct,
            "positive20_count": len(positive20),
            "above20_pct": above20_pct,
            "above20_count": len(above20),
            "above50_pct": above50_pct,
            "above50_count": len(above50),
            "revision_positive_pct": positive_revision_pct,
            "revision_count": len(revision_rows),
            "average_eps_change": average_eps_change,
            "estimate_count": len(estimate_rows),
            "ticker_count": len(available),
        }

    return output


def calculate_saas_breadth(records):
    """Ohranjena SaaS funkcija za prikaz obstoječih SaaS meritev."""
    metrics = calculate_sector_metrics(records, {"rows": []})
    return metrics.get("SaaS / Software", {})


# ============================================================
# LIKVIDNOST IN LONG FILTRI
# ============================================================

def liquidity_reasons(data):
    reasons = []
    market_cap = data.get("market_cap")
    dollar_volume = data.get("dollar_volume")

    if market_cap is None:
        reasons.append("Yahoo Finance ni vrnil market cap podatka")
    elif market_cap < MIN_MARKET_CAP:
        reasons.append(
            f"market cap {market_cap / 1_000_000_000:.2f}B USD "
            "je pod pragom 2.00B USD"
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
            f"povprečni dolarski promet {dollar_volume / 1_000_000:.2f}M USD "
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
            max(0.0, min(10.0, data["median_fcf_margin"] / 2)),
            0.25,
        ))
    if data.get("median_conversion") is not None:
        parts.append((
            max(0.0, min(10.0, data["median_conversion"] * 5)),
            0.20,
        ))
    if data.get("median_sbc") is not None:
        parts.append((
            max(0.0, min(10.0, 10 - data["median_sbc"] / 2)),
            0.15,
        ))
    if data.get("net_cash") is not None:
        parts.append((8.0 if data["net_cash"] >= 0 else 3.0, 0.15))

    if len(parts) < 4:
        return None

    weight = sum(part_weight for _, part_weight in parts)
    if weight <= 0:
        return None

    score = sum(value * part_weight for value, part_weight in parts) / weight
    return round(max(0.0, min(10.0, score)), 1)


def long_filter_reasons(data):
    reasons = liquidity_reasons(data)
    if reasons:
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
        reasons.append("mediana FCF marže je pod 5 % ali manjka")
    if (
        data.get("median_conversion") is None
        or data["median_conversion"] < 0.7
    ):
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
    checks = [
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
    return round(sum(checks) / len(checks) * 100)


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


# ============================================================
# ATR IN INTRADAY REVERSAL
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

    day_frame = frame[
        [stamp.date() == day for stamp in frame.index]
    ]
    if session == "premarket":
        return day_frame.between_time("04:00", "09:29")
    return day_frame.between_time("09:30", "15:59")


def previous_regular_close(frame, day):
    previous_days = sorted(
        {stamp.date() for stamp in frame.index if stamp.date() < day},
        reverse=True,
    )

    for previous_day in previous_days:
        bars = session_bars(frame, previous_day, "regular")
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
    cumulative_volume = volume.cumsum().replace(0, float("nan"))
    return (typical * volume).cumsum() / cumulative_volume


def same_time_volume_ratio(frame, stamp, bars, index):
    current = safe_float(bars["Volume"].iloc[index])
    if current is None or current <= 0:
        return None

    session = "premarket" if stamp.time() < time(9, 30) else "regular"
    clock = stamp.strftime("%H:%M")
    previous_days = sorted({
        item.date()
        for item in frame.index
        if item.date() < stamp.date()
    })[-5:]

    samples = []
    for previous_day in previous_days:
        prior = session_bars(frame, previous_day, session)
        matches = [
            item
            for item in prior.index
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

    relative_strength = gains / losses
    return float(100 - 100 / (1 + relative_strength))


@st.cache_data(ttl=1800, show_spinner=False)
def earnings_clear(ticker, days=5):
    """True: earnings niso v oknu; None: datuma ni bilo mogoče preveriti."""
    try:
        dates = yf.Ticker(ticker).get_earnings_dates(limit=8)
        if dates is None or len(dates) == 0:
            return None

        today = datetime.now(NY_TZ).date()

        for raw_date in dates.index:
            value = pd.Timestamp(raw_date)
            if value.tzinfo is not None:
                value = value.tz_convert(NY_TZ)
            difference = (value.date() - today).days
            if 0 <= difference <= days:
                return False

        return True
    except Exception:
        return None


def reversal_signal(ticker, frame, now=None):
    now = now or datetime.now(NY_TZ)
    day = now.date()

    if frame is None or frame.empty:
        return None

    today = frame[
        [stamp.date() == day for stamp in frame.index]
    ]
    if today.empty:
        return None

    completed = today[
        [stamp + timedelta(minutes=5) <= now for stamp in today.index]
    ]
    if completed.empty:
        return None

    latest_stamp = completed.index[-1]
    session = (
        "premarket"
        if latest_stamp.time() < time(9, 30)
        else "regular"
    )

    bars = session_bars(frame, day, session)
    bars = bars[
        [stamp + timedelta(minutes=5) <= now for stamp in bars.index]
    ]

    if len(bars) < 15:
        return None

    previous_close = previous_regular_close(frame, day)
    if previous_close is None:
        return None

    if earnings_clear(ticker, 5) is not True:
        return None

    vwap = calculate_vwap(bars)
    signals = []

    for index in range(14, len(bars)):
        stamp = bars.index[index]
        close = safe_float(bars["Close"].iloc[index])
        candle_open = safe_float(bars["Open"].iloc[index])
        prior_bar_close = safe_float(bars["Close"].iloc[index - 1])
        current_vwap = safe_float(vwap.iloc[index])
        prior_vwap = safe_float(vwap.iloc[index - 1])

        if any(value is None for value in (
            close,
            candle_open,
            prior_bar_close,
            current_vwap,
            prior_vwap,
        )):
            continue

        # Gap se meri glede na prejšnje redno zaprtje tudi premarket.
        rel_open = (close / previous_close - 1) * 100
        if not -8.0 <= rel_open <= -1.0:
            continue

        reclaimed_vwap = (
            prior_bar_close <= prior_vwap
            and close > current_vwap
        )
        rel_vwap = (close / current_vwap - 1) * 100

        if not reclaimed_vwap:
            continue
        if close <= candle_open or rel_vwap < -2.0:
            continue

        rsi = calculate_rsi(bars["Close"].iloc[:index + 1])
        volume_ratio = same_time_volume_ratio(
            frame,
            stamp,
            bars,
            index,
        )
