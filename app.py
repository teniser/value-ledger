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
# STRAN IN VIDEZ
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
# SEKTORJI IN UNIVERZUM
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

# Izmenično dodajaj tickerje iz sektorjev, nato omeji na največ 150.
AI_UNIVERSE = []
_max_sector_size = max(len(group) for group in SECTOR_GROUPS.values())

for _index in range(_max_sector_size):
    for _group in SECTOR_GROUPS.values():
        if _index < len(_group) and _group[_index] not in AI_UNIVERSE:
            AI_UNIVERSE.append(_group[_index])

AI_UNIVERSE = AI_UNIVERSE[:150]


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
        if any(
            name.strip().lower().replace("_", " ") in key
            for name in names
        ):
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
                continue
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
    """Prebere EPS-revizije analitikov, če jih Yahoo Finance vrne."""
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

            ups = sum(safe_float(row.get(up_col)) or 0 for row in selected)
            downs = sum(
                safe_float(row.get(down_col)) or 0
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
            history = yf.Ticker(ticker).history(
                period="8mo",
                interval="1d",
                auto_adjust=True,
            )
            if history is not None and not history.empty:
                prices[ticker] = history["Close"].dropna().astype(float)
        except Exception:
            continue

    if "SPY" not in prices:
        return {"rows": [], "rotation": "NI PODATKOV", "detail": ""}

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
    for sector, ticker in etfs.items():
        if ticker not in prices:
            continue

        rel5 = relative_return(prices[ticker], prices["SPY"], 5)
        rel20 = relative_return(prices[ticker], prices["SPY"], 20)
        rel60 = relative_return(prices[ticker], prices["SPY"], 60)

        if rel5 is None or rel20 is None or rel60 is None:
            continue

        early_turn = rel5 > 0 and rel20 > 0 and rel60 < 0

        if early_turn:
            label = "MOŽEN ZGODNJI OBRAT"
        elif rel20 > 0 and rel60 > 0:
            label = "RELATIVNO VODI"
        elif rel5 < 0 and rel20 < 0 and rel60 > 0:
            label = "SLABI"
        elif rel20 < 0:
            label = "ZAOSTAJA"
        else:
            label = "MEŠANO"

        rows.append({
            "ETF": ticker,
            "Sektor": sector,
            "Rel. 5d % vs SPY": round(rel5, 2),
            "Rel. 20d % vs SPY": round(rel20, 2),
            "Rel. 60d % vs SPY": round(rel60, 2),
            "Zgodnji obrat navzgor": early_turn,
            "Oznaka": label,
        })

    rows.sort(key=lambda item: item["Rel. 20d % vs SPY"], reverse=True)

    rotation_label = "NI PODATKOV"
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
                rotation_label = "MOŽEN ZAČETEK RELATIVNE ROTACIJE SEMIS → SAAS"
            elif change20 > 0 and change60 > 0 and above_sma20:
                rotation_label = "SAAS RELATIVNO VODI SEMIS"
            elif change20 < 0 and change60 > 0:
                rotation_label = "SAAS RELATIVNO SLABI PROTI SEMIS"
            elif change20 < 0 and not above_sma20:
                rotation_label = "SEMIS RELATIVNO VODI SAAS"
            else:
                rotation_label = "NI JASNE RELATIVNE ROTACIJE"

            detail = (
                f"IGV/SMH: 20d {change20:+.1f}%, "
                f"60d {change60:+.1f}%; nad SMA20: "
                f"{'DA' if above_sma20 else 'NE'}"
            )

    return {
        "rows": rows,
        "rotation": rotation_label,
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
        ebitda_values = annual_values(
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
                "ebitda": ebitda_values.get(year),
            })

        annual.sort(key=lambda item: item["year"])
        fcf_years = len(annual)
        positive_fcf_years = sum(item["fcf"] > 0 for item in annual)

        fcf_margins = [
            item["fcf"] / item["revenue"] * 100
            for item in annual
            if item["revenue"] > 0
        ]
        cfo_conversions = [
            item["cfo"] / item["net_income"]
            for item in annual
            if item["net_income"] > 0
        ]
        sbc_rates = [
            item["sbc"] / item["revenue"] * 100
            for item in annual
            if item["sbc"] is not None and item["revenue"] > 0
        ]

        median_fcf_margin = (
            float(pd.Series(fcf_margins).median())
            if fcf_margins else None
        )
        median_conversion = (
            float(pd.Series(cfo_conversions).median())
            if cfo_conversions else None
        )
        median_sbc = (
            float(pd.Series(sbc_rates).median())
            if sbc_rates else None
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

        target_price = number("targetMeanPrice")
        if target_price is None:
            target_price = number("targetMedianPrice")

        analyst_upside = None
        if target_price is not None and price is not None and price > 0:
            analyst_upside = (target_price / price - 1) * 100

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
            eps_data = get_eps_revision_metrics(stock)
        except Exception:
            eps_data = {
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
            "analyst_count": number("numberOfAnalystOpinions"),
            "analyst_upside": analyst_upside,
            **eps_data,
        }

    except Exception:
        return None


# ============================================================
# LIKVIDNOST, MULTIPLE IN FUNDAMENTALNI FILTRI
# ============================================================

def liquidity_reasons(data):
    reasons = []

    market_cap = data.get("market_cap")
    dollar_volume = data.get("dollar_volume")

    if market_cap is None:
        reasons.append("market cap podatek manjka")
    elif market_cap < MIN_MARKET_CAP:
        reasons.append("market cap je pod 2B USD")

    if dollar_volume is None:
        reasons.append("dolarskega prometa ni mogoče izračunati")
    elif dollar_volume < MIN_DOLLAR_VOLUME:
        reasons.append("povprečni dolarski promet je pod 20M USD")

    return reasons


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
    components = []
    years = data.get("fcf_years", 0)

    if years >= 3:
        components.append((
            data["positive_fcf_years"] / years * 10,
            0.25,
        ))
    if data.get("median_fcf_margin") is not None:
        components.append((
            max(0.0, min(10.0, data["median_fcf_margin"] / 2)),
            0.25,
        ))
    if data.get("median_conversion") is not None:
        components.append((
            max(0.0, min(10.0, data["median_conversion"] * 5)),
            0.20,
        ))
    if data.get("median_sbc") is not None:
        components.append((
            max(0.0, min(10.0, 10 - data["median_sbc"] / 2)),
            0.15,
        ))
    if data.get("net_cash") is not None:
        components.append((
            8.0 if data["net_cash"] >= 0 else 3.0,
            0.15,
        ))

    if len(components) < 4:
        return None

    weight_sum = sum(weight for _, weight in components)
    if weight_sum <= 0:
        return None

    score = sum(value * weight for value, weight in components) / weight_sum
    return round(max(0.0, min(10.0, score)), 1)


def long_filter_reasons(data):
    reasons = liquidity_reasons(data)

    if data.get("fcf_years", 0) < 3:
        reasons.append("manj kot 3 leta primerljivih finančnih izkazov")
    if data.get("latest_fcf") is None or data["latest_fcf"] <= 0:
        reasons.append("zadnji letni FCF ni pozitiven")
    if (
        data.get("fcf_years", 0) >= 3
        and data.get("positive_fcf_years", 0) < 2
    ):
        reasons.append("pozitiven FCF ni bil dosežen v vsaj 2 od 3 let")
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
        reasons.append("SBC podatek manjka")
    elif data["median_sbc"] > 15:
        reasons.append("SBC presega 15 % prihodkov")
    if data.get("growth") is None or data["growth"] < 0.10:
        reasons.append("rast prihodkov je pod 10 % ali manjka")
    if data.get("net_cash") is None:
        reasons.append("neto denar/dolg podatek manjka")
    elif data["net_cash"] < 0:
        ebitda = data.get("latest_ebitda")
        if ebitda is None or ebitda <= 0:
            reasons.append("neto dolg in ni pozitivnega EBITDA")
        elif abs(data["net_cash"]) / ebitda > 2.5:
            reasons.append("net debt/EBITDA presega 2,5x")
    if data.get("drawdown_52w") is None:
        reasons.append("ni dovolj zgodovine za 52-tedenski padec")
    if data.get("return20") is None or data.get("return60") is None:
        reasons.append("ni dovolj zgodovine za 20d/60d zagon")

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


def wallstreet_score(data):
    """Pretvori analyst recommendation in target upside v omejeno oceno."""
    recommendation = data.get("recommendation_mean")
    upside = data.get("analyst_upside")
    analyst_count = data.get("analyst_count")

    if recommendation is None and upside is None:
        return None

    score = 5.0

    # Yahoo recommendationMean: 1 = strong buy, 5 = sell.
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

    if upside is not None:
        if upside > 30:
            score += 1.5
        elif upside > 15:
            score += 1.0
        elif upside > 5:
            score += 0.5
        elif upside < -10:
            score -= 1.0

    if analyst_count is not None and analyst_count < 5:
        score -= 0.5

    return round(max(0.0, min(10.0, score)), 1)


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

        result = safe_float(true_range.rolling(14).mean().iloc[-1])
        return result if result is not None and result > 0 else None
    except Exception:
        return None


# ============================================================
# SEKTORSKI ZAGON IN ŠIRINA
# ============================================================

def calculate_sector_metrics(records, rotation_data):
    rotation_by_etf = {
        row.get("ETF"): row
        for row in rotation_data.get("rows", [])
        if row.get("ETF")
    }
    result = {}

    for sector, members in SECTOR_GROUPS.items():
        available = [
            records[ticker]
            for ticker in members
            if ticker in records
        ]

        above20 = [
            row for row in available
            if row.get("above_sma20") is not None
        ]
        above50 = [
            row for row in available
            if row.get("above_sma50") is not None
        ]
        revisions = [
            row for row in available
            if row.get("eps_revision_net_30d") is not None
        ]

        above20_pct = (
            100 * sum(bool(row["above_sma20"]) for row in above20) / len(above20)
            if above20 else None
        )
        above50_pct = (
            100 * sum(bool(row["above_sma50"]) for row in above50) / len(above50)
            if above50 else None
        )
        positive_revision_pct = (
            100
            * sum(row["eps_revision_net_30d"] > 0 for row in revisions)
            / len(revisions)
            if revisions else None
        )

        etf = SECTOR_ETF.get(sector)
        etf_data = rotation_by_etf.get(etf, {})
        rel5 = safe_float(etf_data.get("Rel. 5d % vs SPY"))
        rel20 = safe_float(etf_data.get("Rel. 20d % vs SPY"))
        rel60 = safe_float(etf_data.get("Rel. 60d % vs SPY"))
        early_turn = bool(etf_data.get("Zgodnji obrat navzgor", False))

        components = []

        if rel20 is not None:
            components.append((
                max(0.0, min(10.0, 5.0 + rel20 * 0.35)),
                0.25,
            ))
        if rel5 is not None:
            components.append((
                max(0.0, min(10.0, 5.0 + rel5 * 0.50)),
                0.15,
            ))
        if above20_pct is not None:
            components.append((above20_pct / 10.0, 0.25))
        if above50_pct is not None:
            components.append((above50_pct / 10.0, 0.15))
        if positive_revision_pct is not None:
            components.append((positive_revision_pct / 10.0, 0.20))

        score = None
        if components:
            weight_sum = sum(weight for _, weight in components)
            score = sum(
                value * weight for value, weight in components
            ) / weight_sum

            if early_turn:
                score += 0.5

            score = round(max(0.0, min(10.0, score)), 1)

        result[sector] = {
            "sector": sector,
            "etf": etf,
            "sector_score": score,
            "rel5": rel5,
            "rel20": rel20,
            "rel60": rel60,
            "early_turn": early_turn,
            "above20_pct": above20_pct,
            "above20_count": len(above20),
            "above50_pct": above50_pct,
            "above50_count": len(above50),
            "revision_positive_pct": positive_revision_pct,
            "revision_count": len(revisions),
            "ticker_count": len(available),
        }

    return result


# ============================================================
# RELATIVNI DONOS DELNICE PROTI SEKTORJU
# Ta funkcija je na najvišji ravni in pred dashboardom.
# ============================================================

@st.cache_data(ttl=900, show_spinner=False)
def sector_relative_returns(ticker, sector):
    etf = SECTOR_ETF.get(sector)
    if not etf:
        return None, None

    try:
        stock_history = yf.Ticker(ticker).history(
            period="6mo",
            interval="1d",
            auto_adjust=True,
        )
        sector_history = yf.Ticker(etf).history(
            period="6mo",
            interval="1d",
            auto_adjust=True,
        )

        if (
            stock_history is None
            or stock_history.empty
            or sector_history is None
            or sector_history.empty
        ):
            return None, None

        joined = pd.concat(
            [
                stock_history["Close"].rename("stock"),
                sector_history["Close"].rename("sector"),
            ],
            axis=1,
            join="inner",
        ).dropna()

        if len(joined) < 61:
            return None, None

        rel20 = (
            (
                joined["stock"].iloc[-1]
                / joined["stock"].iloc[-21]
                - 1
            )
            - (
                joined["sector"].iloc[-1]
                / joined["sector"].iloc[-21]
                - 1
            )
        ) * 100

        rel60 = (
            (
                joined["stock"].iloc[-1]
                / joined["stock"].iloc[-61]
                - 1
            )
            - (
                joined["sector"].iloc[-1]
                / joined["sector"].iloc[-61]
                - 1
            )
        ) * 100

        return round(float(rel20), 2), round(float(rel60), 2)
    except Exception:
        return None, None


# ============================================================
# FUNDAMENTALNI LONG SKEN
# ============================================================

@st.cache_data(ttl=300, show_spinner=False)
def scan_long(universe):
    records = []
    errors = []

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(get_stock_data, ticker): ticker
            for ticker in universe
        }

        for future in as_completed(futures):
            ticker = futures[future]
            try:
                data = future.result()
                if not data:
                    errors.append(f"{ticker}: podatki niso bili vrnjeni")
                    continue

                data["multiple"] = get_multiple(data)
                data["quality"] = quality_score(data)
                data["coverage"] = coverage_score(data)
                data["reasons"] = long_filter_reasons(data)
                data["drawdown_score"] = drawdown_score(
                    data.get("drawdown_52w")
                )
                data["momentum_score"] = momentum_score(
                    data.get("return20"),
                    data.get("return60"),
                    data.get("return120"),
                )
                data["ws_score"] = wallstreet_score(data)

                revisions = data.get("eps_revision_net_30d")
                data["revision_score"] = (
                    max(0.0, min(10.0, 5.0 + revisions))
                    if revisions is not None
                    else None
                )

                records.append(data)

            except Exception as error:
                errors.append(f"{ticker}: {error}")

    audit = {row["ticker"]: row for row in records}
    rotation = get_rotation()
    sector_metrics = calculate_sector_metrics(audit, rotation)

    peers_by_sector = {}
    for row in records:
        if (
            not liquidity_reasons(row)
            and row["multiple"]["value"] is not None
        ):
            peers_by_sector.setdefault(row["sector"], []).append(row)

    ranked = []

    for candidate in records:
        if candidate["reasons"] or candidate["quality"] is None:
            continue

        if (
            candidate["drawdown_score"] is None
            or candidate["momentum_score"] is None
        ):
            candidate["reasons"].append(
                "manjka podatek za oceno padca ali zagona"
            )
            continue

        peers = [
            peer
            for peer in peers_by_sector.get(candidate["sector"], [])
            if (
                peer["multiple"]["name"] == candidate["multiple"]["name"]
                and peer["multiple"]["value"] is not None
            )
        ]

        if len(peers) < 5:
            candidate["reasons"].append(
                f"le {len(peers)} primerljivih peerjev; "
                "potrebnih je vsaj 5"
            )
            continue

        valuation_pct = midrank_percentile(
            [peer["multiple"]["value"] for peer in peers],
            candidate["multiple"]["value"],
            lower_is_better=True,
        )
        fcf_pct = midrank_percentile(
            [
                peer["quality"]
                for peer in peers
                if peer["quality"] is not None
            ],
            candidate["quality"],
        )
        growth_pct = midrank_percentile(
            [
                peer["growth"]
                for peer in peers
                if peer["growth"] is not None
            ],
            candidate["growth"],
        )

        if (
            valuation_pct is None
            or fcf_pct is None
            or growth_pct is None
        ):
            candidate["reasons"].append(
                "premalo podatkov za peer percentile"
            )
            continue

        candidate["peer_count"] = len(peers)
        candidate["valuation_percentile"] = valuation_pct
        candidate["fcf_percentile"] = fcf_pct
        candidate["growth_percentile"] = growth_pct

        sector = sector_metrics.get(candidate["sector"], {})
        candidate["sector_momentum_score"] = sector.get("sector_score")
        candidate["sector_rel5"] = sector.get("rel5")
        candidate["sector_rel20"] = sector.get("rel20")
        candidate["sector_rel60"] = sector.get("rel60")
        candidate["sector_early_turn"] = sector.get("early_turn", False)
        candidate["sector_above20_pct"] = sector.get("above20_pct")
        candidate["sector_above50_pct"] = sector.get("above50_pct")
        candidate["sector_revision_pct"] = sector.get(
            "revision_positive_pct"
        )

        components = [
            (candidate["quality"] * 10, 0.18),
            (valuation_pct, 0.20),
            (candidate["drawdown_score"] * 10, 0.12),
            (candidate["momentum_score"] * 10, 0.10),
            (growth_pct, 0.08),
        ]

        if candidate["sector_momentum_score"] is not None:
            components.append((
                candidate["sector_momentum_score"] * 10,
                0.15,
            ))
        if candidate["ws_score"] is not None:
            components.append((candidate["ws_score"] * 10, 0.10))
        if candidate["revision_score"] is not None:
            components.append((candidate["revision_score"] * 10, 0.07))

        weight_sum = sum(weight for _, weight in components)
        if weight_sum <= 0:
            continue

        raw_score = sum(
            value * weight for value, weight in components
        ) / weight_sum

        candidate["asymmetry_score"] = round(raw_score / 10, 1)
        candidate["score_coverage"] = round(weight_sum * 100)
        ranked.append(candidate)

    ranked.sort(
        key=lambda row: (
            row["asymmetry_score"],
            row["quality"],
            row["coverage"],
            row["ticker"],
        ),
        reverse=True,
    )

    for ticker, data in audit.items():
        sector = sector_metrics.get(data["sector"], {})
        data["sector_momentum_score"] = sector.get("sector_score")
        data["sector_rel5"] = sector.get("rel5")
        data["sector_rel20"] = sector.get("rel20")
        data["sector_rel60"] = sector.get("rel60")
        data["sector_early_turn"] = sector.get("early_turn", False)
        data["sector_above20_pct"] = sector.get("above20_pct")
        data["sector_above50_pct"] = sector.get("above50_pct")
        data["sector_revision_pct"] = sector.get(
            "revision_positive_pct"
        )

    return ranked, audit, errors


# ============================================================
# PREMARKET INTRADAY PODATKI IN REVERSAL SKEN
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
        if frame.empty:
            return None

        if frame.index.tz is None:
            frame.index = frame.index.tz_localize("UTC")
        frame.index = frame.index.tz_convert(NY_TZ)

        valid = [
            time(4, 0) <= stamp.time() < time(16, 0)
            for stamp in frame.index
        ]
        frame = frame.loc[valid]

        return frame if not frame.empty else None
    except Exception:
        return None


def session_bars(frame, day, session):
    if frame is None or frame.empty:
        return pd.DataFrame()

    same_day = frame[
        [stamp.date() == day for stamp in frame.index]
    ]

    if session == "premarket":
        return same_day.between_time("04:00", "09:29")

    return same_day.between_time("09:30", "15:59")


def previous_regular_close(frame, day):
    previous_days = sorted(
        {
            stamp.date()
            for stamp in frame.index
            if stamp.date() < day
        },
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
    current_volume = safe_float(bars["Volume"].iloc[index])
    if current_volume is None or current_volume <= 0:
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
        previous = session_bars(frame, previous_day, session)
        matching_times = [
            item
            for item in previous.index
            if item.strftime("%H:%M") == clock
        ]

        if matching_times:
            volume = safe_float(
                previous.loc[matching_times[-1], "Volume"]
            )
            if volume is not None and volume > 0:
                samples.append(volume)

    if not samples:
        return None

    baseline = float(pd.Series(samples).median())
    return current_volume / baseline if baseline > 0 else None


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
    """Vrne True, če ni earnings v oknu; None pomeni, da datuma ni preveril."""
    try:
        dates = yf.Ticker(ticker).get_earnings_dates(limit=8)
        if dates is None or len(dates) == 0:
            return None

        today = datetime.now(NY_TZ).date()

        for raw_date in dates.index:
            date_value = pd.Timestamp(raw_date)
            if date_value.tzinfo is not None:
                date_value = date_value.tz_convert(NY_TZ)

            difference = (date_value.date() - today).days
            if 0 <= difference <= days:
                return False

        return True
    except Exception:
        return None


def reversal_signal(ticker, frame, market_penalty, now=None):
    now = now or datetime.now(NY_TZ)
    current_day = now.date()

    if frame is None or frame.empty:
        return None

    today = frame[
        [stamp.date() == current_day for stamp in frame.index]
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

    bars = session_bars(frame, current_day, session)
    bars = bars[
        [stamp + timedelta(minutes=5) <= now for stamp in bars.index]
    ]

    if len(bars) < 15:
        return None

    prior_close = previous_regular_close(frame, current_day)
    if prior_close is None:
        return None

    # Če earnings datuma ni mogoče preveriti, skener ne izda reversal signala.
    if earnings_clear(ticker, 5) is not True:
        return None

    vwap = calculate_vwap(bars)
    signals = []

    for index in range(14, len(bars)):
        stamp = bars.index[index]
        close = safe_float(bars["Close"].iloc[index])
        candle_open = safe_float(bars["Open"].iloc[index])
        previous_close = safe_float(bars["Close"].iloc[index - 1])
        current_vwap = safe_float(vwap.iloc[index])
        previous_vwap = safe_float(vwap.iloc[index - 1])

        required_values = [
            close,
            candle_open,
            previous_close,
            current_vwap,
            previous_vwap,
        ]
        if any(value is None for value in required_values):
            continue

        relative_open = (close / prior_close - 1) * 100
        if not -8.0 <= relative_open <= -1.0:
            continue

        reclaimed_vwap = (
            previous_close <= previous_vwap
            and close > current_vwap
        )
        relative_vwap = (close / current_vwap - 1) * 100

        if not reclaimed_vwap:
            continue
        if close <= candle_open or relative_vwap < -2.0:
            continue

        rsi = calculate_rsi(bars["Close"].iloc[:index + 1])
        volume_ratio = same_time_volume_ratio(
            frame,
            stamp,
            bars,
            index,
        )
        momentum = (close / previous_close - 1) * 100

        if rsi is None or rsi > 35:
            continue
        if volume_ratio is None or volume_ratio < 1.3:
            continue
        if momentum <= 0:
            continue

        score = 6.0
        score += min(max(volume_ratio - 1.3, 0) * 0.5, 1.5)
        score += min(momentum * 0.25, 1.0)
        score -= market_penalty
        score = round(max(0.0, min(10.0, score)), 1)

        if score < 6.0:
            continue

        signals.append({
            "Ticker": ticker,
            "Čas": stamp.strftime("%H:%M ET"),
            "Seja": (
                "PREMARKET"
                if stamp.time() < time(9, 30)
                else "REDNA SEJA"
            ),
            "Cena": round(close, 2),
            "Rel. vs prejšnji close %": round(relative_open, 2),
            "VWAP": round(current_vwap, 2),
            "Rel. VWAP %": round(relative_vwap, 2),
            "Volumen / ista ura x": round(volume_ratio, 2),
            "RSI 5m": round(rsi, 1),
            "Momentum %": round(momentum, 2),
            "Ocena filtra": score,
        })

    return signals[-1] if signals else None


@st.cache_data(ttl=90, show_spinner=False)
def scan_reversals(universe, market_penalty):
    results = []
    now = datetime.now(NY_TZ)

    for ticker in universe:
        try:
            frame = get_intraday_history(ticker)
            signal = reversal_signal(
                ticker,
                frame,
                market_penalty,
                now,
            )
            if signal:
                results.append(signal)
        except Exception:
            continue

    results.sort(
        key=lambda item: item["Ocena filtra"],
        reverse=True,
    )
    return results[:5]


# ============================================================
# AI ANALIZA TRGA
# ============================================================

def build_ai_context(
    market,
    rotation,
    sector_metrics,
    long_candidates,
    reversal_candidates,
    audit,
):
    lines = [
        "TRŽNI REŽIM:",
        f"- Režim: {market.get('regime', 'NI PODATKA')}",
        f"- SPY sprememba 20d: {fmt(market.get('change20'), 2, '%')}",
        "",
        "SEKTORSKA ROTACIJA:",
        f"- IGV/SMH: {rotation.get('rotation', 'NI PODATKA')}",
        f"- Podrobnosti: {rotation.get('detail') or 'Ni podatkov.'}",
        "",
        "SEKTORSKI ZAGON:",
    ]

    sorted_sectors = sorted(
        sector_metrics.values(),
        key=lambda row: (
            row.get("sector_score") is not None,
            row.get("sector_score") or -1,
        ),
        reverse=True,
    )

    if sorted_sectors:
        for row in sorted_sectors:
            lines.append(
                f"- {row['sector']} ({row.get('etf') or 'brez ETF'}): "
                f"zagon {fmt(row.get('sector_score'), 1)}/10; "
                f"relativni donos proti SPY 5d "
                f"{fmt(row.get('rel5'), 2, '%')}, 20d "
                f"{fmt(row.get('rel20'), 2, '%')}, 60d "
                f"{fmt(row.get('rel60'), 2, '%')}; "
                f"nad SMA20 {fmt(row.get('above20_pct'), 1, '%')} "
                f"({row.get('above20_count', 0)} tickerjev); "
                f"nad SMA50 {fmt(row.get('above50_pct'), 1, '%')} "
                f"({row.get('above50_count', 0)} tickerjev); "
                f"pozitivne EPS-revizije "
                f"{fmt(row.get('revision_positive_pct'), 1, '%')} "
                f"({row.get('revision_count', 0)} podatkov); "
                f"zgodnji obrat "
                f"{'DA' if row.get('early_turn') else 'NE'}."
            )
    else:
        lines.append("- Sektorskih podatkov ni.")

    lines.extend(["", "TOP LONG:"])
    if long_candidates:
        for item in long_candidates[:5]:
            growth = item.get("growth")
            growth_pct = growth * 100 if growth is not None else None
            multiple = item.get("multiple", {})

            lines.append(
                f"- {item.get('ticker')}: ocena "
                f"{fmt(item.get('asymmetry_score'), 1)}/10; "
                f"sektor {item.get('sector')}; cena "
                f"{fmt(item.get('price'))}; "
                f"{multiple.get('name', 'multiple')} "
                f"{fmt(multiple.get('value'))}; peer vrednotenje "
                f"{fmt(item.get('valuation_percentile'), 0)}; "
                f"FCF kakovost {fmt(item.get('quality'), 1)}/10; "
                f"rast prihodkov {fmt(growth_pct, 1, '%')}; "
                f"FCF yield {fmt(item.get('fcf_yield'), 2, '%')}; "
                f"Wall Street ocena {fmt(item.get('ws_score'), 1)}/10; "
                f"sektorski zagon "
                f"{fmt(item.get('sector_momentum_score'), 1)}/10."
            )
    else:
        lines.append("- Ni Long kandidata po strogih filtrih.")

    lines.extend(["", "INTRADAY / PREMARKET REVERSAL:"])
    if reversal_candidates:
        for item in reversal_candidates:
            lines.append(
                f"- {item.get('Ticker')}, {item.get('Seja')}, "
                f"{item.get('Čas')}; cena {fmt(item.get('Cena'))}; "
                f"proti prejšnjemu close "
                f"{fmt(item.get('Rel. vs prejšnji close %'), 2, '%')}; "
                f"proti VWAP {fmt(item.get('Rel. VWAP %'), 2, '%')}; "
                f"volumen/ista ura "
                f"{fmt(item.get('Volumen / ista ura x'), 2, 'x')}; "
                f"RSI {fmt(item.get('RSI 5m'), 1)}; "
                f"momentum {fmt(item.get('Momentum %'), 2, '%')}; "
                f"ocena filtra {fmt(item.get('Ocena filtra'), 1)}/10."
            )
    else:
        lines.append("- Trenutno ni kandidata po reversal filtrih.")

    mndy = audit.get("MNDY")
    lines.extend(["", "MNDY STATUS:"])

    if mndy is None:
        lines.append("- Za MNDY ni bilo dovolj podatkov.")
    else:
        mndy_ranked = next(
            (
                row for row in long_candidates
                if row.get("ticker") == "MNDY"
            ),
            None,
        )

        if mndy_ranked:
            lines.append(
                f"- MNDY je uvrščen z oceno "
                f"{fmt(mndy_ranked.get('asymmetry_score'), 1)}/10; "
                f"SaaS sektorski zagon "
                f"{fmt(mndy_ranked.get('sector_momentum_score'), 1)}/10."
            )
        else:
            lines.append("- MNDY ni uvrščen med Long kandidate.")
            if mndy.get("reasons"):
                lines.append("- Razlogi: " + "; ".join(mndy["reasons"]))

    lines.extend([
        "",
        "OMEJITVE:",
        "- ETF relativna moč in širina delnic sta cenovna približka sentimenta.",
        "- To niso neposredno izmerjeni kapitalski tokovi.",
        "- Manjkajočih podatkov ne ugibaj.",
        "- Hevristična ocena ni zagotovilo donosa.",
    ])

    return "\n".join(lines)


def request_ai_analysis(api_key, context):
    key = api_key.strip()
    if not key:
        raise ValueError("Vnesi Gemini API ključ.")

    models_response = requests.get(
        "https://generativelanguage.googleapis.com/v1beta/models",
        params={"key": key},
        timeout=20,
    )
    models_response.raise_for_status()

    models = [
        item["name"].split("/")[-1]
        for item in models_response.json().get("models", [])
        if "generateContent" in item.get("supportedGenerationMethods", [])
    ]

    if not models:
        raise RuntimeError(
            "API ni vrnil modela, ki podpira generateContent."
        )

    preferred = [
        model for model in models
        if model == "gemini-2.5-flash"
    ]
    models = preferred + [
        model for model in models
        if model not in preferred
    ]

    prompt = f"""
Odgovori v slovenščini in uporabi samo številke iz spodnjega konteksta.

Povzemi tržni režim; razvrsti sektorje po zagonu; izpostavi možne zgodnje
obrate; razloži sektorski kontekst Long kandidatov; povzemi reversal
kandidate ter navedi manjkajoče podatke in tveganja.

Ne izmišljaj si cen, novic, številk, denarnih tokov ali zgodovinskih
vrednotenj. Če podatka ni, napiši »ni podatka«. Relativna moč ETF-ja ni
neposredna meritev kapitalskih tokov. Ocene so hevristične, ne zagotovilo
donosa.

Podatki:
{context}
"""

    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }
    last_error = "Klic API-ja ni uspel."

    for model_name in models:
        try:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model_name}:generateContent"
            )
            response = requests.post(
                url,
                params={"key": key},
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=40,
            )

            if response.status_code == 200:
                candidates = response.json().get("candidates", [])
                if candidates:
                    parts = (
                        candidates[0]
                        .get("content", {})
                        .get("parts", [])
                    )
                    text = "\n".join(
                        part.get("text", "")
                        for part in parts
                        if part.get("text")
                    )
                    if text.strip():
                        return model_name, text

                last_error = f"{model_name}: API ni vrnil besedila."
            else:
                last_error = (
                    f"{model_name}: HTTP {response.status_code} "
                    f"{response.text[:300]}"
                )
        except requests.RequestException as error:
            last_error = str(error)

    raise RuntimeError(last_error)


# ============================================================
# GLAVA IN SIDEBAR
# ============================================================

local_now = datetime.now(LJ_TZ)

st.markdown(
    f"""
    <div style="border-bottom:1px solid rgba(255,255,255,.08);
                padding-bottom:12px;margin-bottom:18px;">
      <h1 style="margin:0;">
        <span style="color:#F59E0B;">THE VALUE LEDGER</span>
        <span style="color:#60A5FA;">2.0</span>
      </h1>
      <p style="color:#94A3B8;">
        Kvantitativni terminal · {local_now.strftime("%d.%m.%Y %H:%M")} Ljubljana
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption("Presejalno orodje, ne napoved donosa ali samodejno naročilo.")

st.sidebar.markdown("### Nastavitve")
api_key = st.sidebar.text_input(
    "Gemini API ključ (neobvezno)",
    type="password",
)
st.sidebar.caption(f"Tickerjev v skenu: {len(AI_UNIVERSE)}")
st.sidebar.caption(
    "Sektorska relativna moč je približek sentimenta, ne neposreden podatek "
    "o kapitalskih tokovih."
)

# Sidebar je izven fragmenta, da se prepreči težava z izrisom sidebar elementov.
market_for_sidebar = get_market_regime()
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Tržni režim:** {market_for_sidebar['regime']}")
if market_for_sidebar["change20"] is not None:
    st.sidebar.caption(
        f"SPY 20d: {market_for_sidebar['change20']:+.2f}%"
    )


# ============================================================
# GLAVNA PLOŠČA
# ============================================================

def render_dashboard():
    if st.button("Osveži skene zdaj", key="refresh_value_ledger"):
        scan_long.clear()
        scan_reversals.clear()
        get_stock_data.clear()
        get_intraday_history.clear()
        get_market_regime.clear()
        get_rotation.clear()
        get_atr.clear()
        earnings_clear.clear()
        sector_relative_returns.clear()
        st.rerun()

    with st.spinner("Nalagam tržni režim in sektorsko rotacijo..."):
        market = get_market_regime()
        rotation = get_rotation()

    progress = st.progress(0)
    long_candidates = []
    audit = {}
    errors = []
    reversals = []

    try:
        with st.spinner("Skeniram temelje, sektorje in intraday podatke..."):
            long_candidates, audit, errors = scan_long(tuple(AI_UNIVERSE))
            progress.progress(55)

            reversals = scan_reversals(
                tuple(AI_UNIVERSE),
                float(market["penalty"]),
            )
            progress.progress(100)
    except Exception as error:
        st.error(f"Skeniranje ni uspelo: {str(error)[:400]}")
    finally:
        progress.empty()

    sector_metrics = calculate_sector_metrics(audit, rotation)

    if errors:
        st.caption(
            f"Podatkov ni bilo mogoče dobiti za {len(errors)} tickerjev."
        )

    best_long = long_candidates[0] if long_candidates else None
    best_reversal = reversals[0] if reversals else None

    # Zlata Long kartica in zelena reversal kartica.
    left, right = st.columns(2)

    with left:
        if best_long:
            item = best_long
            atr = get_atr(item["ticker"])
            price = item.get("price")
            stop = price - 1.5 * atr if price and atr else None
            target1 = price + 1.5 * atr if price and atr else None
            target2 = price + 2.5 * atr if price and atr else None

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
                    Cena {fmt(price)} · Ocena {item["asymmetry_score"]}/10
                  </div>
