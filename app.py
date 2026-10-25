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
    .hero-long {
        background: linear-gradient(145deg, rgba(48,34,10,0.72), rgba(13,17,28,0.96));
        border: 1px solid rgba(245,158,11,0.58);
        border-radius: 18px;
        padding: 20px 24px;
        min-height: 210px;
    }
    .hero-reversal {
        background: linear-gradient(145deg, rgba(9,43,39,0.75), rgba(13,17,28,0.96));
        border: 1px solid rgba(16,185,129,0.48);
        border-radius: 18px;
        padding: 20px 24px;
        min-height: 210px;
    }
    .ledger-card {
        background: linear-gradient(145deg, #0D111C, #090B12);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 20px 24px;
        margin: 8px 0 18px 0;
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

    # Velika tehnologija in internet
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


# Ročne skupine za primerjavo. To niso uradne klasifikacije podjetij.
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

# Za vsako skupino določimo en primerjalni multiple.
# Vrednosti različnih multiple-ov se nikoli ne mešajo v isti peer primerjavi.
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
        result = float(value)
        return result if math.isfinite(result) else None
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
    if frame is None or frame.empty:
        st.info("Ni podatkov za prikaz.")
        return

    headers = "".join(
        f"<th>{html.escape(str(column))}</th>"
        for column in frame.columns
    )

    rows = []
    for _, row in frame.iterrows():
        cells = []
        for value in row.tolist():
            text = "—" if pd.isna(value) else str(value)
            cells.append(f"<td>{html.escape(text)}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")

    table_html = (
        '<div style="overflow-x:auto;border:1px solid #263044;'
        'border-radius:10px;margin:8px 0 18px 0;">'
        '<table style="border-collapse:collapse;width:100%;'
        'background:#0D111C;color:#CBD5E1;font-size:0.82rem;">'
        '<thead><tr style="background:#151B29;color:#F8FAFC;">'
        + headers
        + "</tr></thead><tbody>"
        + "".join(rows)
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

    index_map = {
        str(index).strip().lower().replace("_", " "): index
        for index in frame.index
    }

    for name in names:
        key = name.strip().lower().replace("_", " ")
        if key in index_map:
            return frame.loc[index_map[key]]

    for normalized, original in index_map.items():
        if any(
            name.strip().lower().replace("_", " ") in normalized
            for name in names
        ):
            return frame.loc[original]

    return None


def statement_values_by_year(frame, names):
    row = get_statement_row(frame, names)
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


# ============================================================
# MARKET REGIME AND SECTOR ROTATION
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
def get_capital_rotation():
    etfs = {
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

    close_data = {}
    for ticker in list(etfs.values()) + ["SPY"]:
        try:
            frame = yf.Ticker(ticker).history(
                period="8mo",
                interval="1d",
                auto_adjust=True,
            )
            if frame is not None and not frame.empty:
                close_data[ticker] = frame["Close"].dropna().astype(float)
        except Exception:
            continue

    if "SPY" not in close_data:
        return {"rows": [], "rotation": "NI PODATKOV", "detail": ""}

    def relative_return(series, benchmark, days):
        joined = pd.concat(
            [series.rename("sector"), benchmark.rename("spy")],
            axis=1,
            join="inner",
        ).dropna()
        if len(joined) <= days:
            return None

        sector_change = (
            joined["sector"].iloc[-1] / joined["sector"].iloc[-1 - days] - 1
        ) * 100
        spy_change = (
            joined["spy"].iloc[-1] / joined["spy"].iloc[-1 - days] - 1
        ) * 100
        return float(sector_change - spy_change)

    rows = []
    for label, ticker in etfs.items():
        if ticker not in close_data:
            continue

        r5 = relative_return(close_data[ticker], close_data["SPY"], 5)
        r20 = relative_return(close_data[ticker], close_data["SPY"], 20)
        r60 = relative_return(close_data[ticker], close_data["SPY"], 60)

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

    if "IGV" in close_data and "SMH" in close_data:
        joined = pd.concat(
            [
                close_data["IGV"].rename("igv"),
                close_data["SMH"].rename("smh"),
            ],
            axis=1,
            join="inner",
        ).dropna()

        if len(joined) > 60:
            ratio = joined["igv"] / joined["smh"]
            change20 = (ratio.iloc[-1] / ratio.iloc[-21] - 1) * 100
            change60 = (ratio.iloc[-1] / ratio.iloc[-61] - 1) * 100
            sma20 = ratio.rolling(20).mean().iloc[-1]
            above_sma = bool(ratio.iloc[-1] > sma20)

            if change20 > 0 and change60 < 0 and above_sma:
                rotation = "MOŽEN ZAČETEK RELATIVNE ROTACIJE SEMIS → SAAS"
            elif change20 > 0 and change60 > 0 and above_sma:
                rotation = "SAAS RELATIVNO VODI SEMIS"
            elif change20 < 0 and change60 > 0:
                rotation = "SAAS RELATIVNO SLABI PROTI SEMIS"
            elif change20 < 0 and not above_sma:
                rotation = "SEMIS RELATIVNO VODI SAAS"
            else:
                rotation = "NI JASNE RELATIVNE ROTACIJE"

            detail = (
                f"IGV/SMH razmerje: 20d {change20:+.1f}%, "
                f"60d {change60:+.1f}%; nad SMA20: "
                f"{'DA' if above_sma else 'NE'}"
            )

    return {"rows": rows, "rotation": rotation, "detail": detail}


# ============================================================
# FUNDAMENTALNI PODATKI IN WALL STREET REVIZIJE
# ============================================================

@st.cache_data(ttl=1800, show_spinner=False)
def get_fundamental_data(ticker):
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

        cfo = statement_values_by_year(
            cashflow,
            [
                "Operating Cash Flow",
                "Total Cash From Operating Activities",
                "Cash Flow From Continuing Operating Activities",
            ],
        )
        capex = statement_values_by_year(
            cashflow,
            ["Capital Expenditure", "Capital Expenditures"],
        )
        sbc = statement_values_by_year(
            cashflow,
            ["Stock Based Compensation", "Share Based Compensation"],
        )
        net_income = statement_values_by_year(
            income,
            [
                "Net Income",
                "Net Income Common Stockholders",
                "Net Income From Continuing Operations",
            ],
        )
        revenue = statement_values_by_year(
            income,
            ["Total Revenue", "Operating Revenue", "Revenue"],
        )
        ebitda = statement_values_by_year(
            income,
            ["EBITDA", "Normalized EBITDA"],
        )

        common_years = sorted(
            set(cfo) & set(capex) & set(net_income) & set(revenue)
        )[-5:]

        annual = []
        for year in common_years:
            yearly_revenue = revenue[year]
            yearly_cfo = cfo[year]
            yearly_capex = abs(capex[year])
            yearly_income = net_income[year]
            yearly_sbc = sbc.get(year)

            annual.append({
                "year": year,
                "revenue": yearly_revenue,
                "cfo": yearly_cfo,
                "capex": yearly_capex,
                "fcf": yearly_cfo - yearly_capex,
                "net_income": yearly_income,
                "sbc": abs(yearly_sbc) if yearly_sbc is not None else None,
                "ebitda": ebitda.get(year),
            })

        annual.sort(key=lambda row: row["year"])

        fcf_years = len(annual)
        positive_fcf_years = sum(row["fcf"] > 0 for row in annual)
        fcf_margins = [
            row["fcf"] / row["revenue"] * 100
            for row in annual
            if row["revenue"] > 0
        ]
        cash_conversion = [
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
            float(pd.Series(cash_conversion).median())
            if cash_conversion
            else None
        )
        median_sbc_burden = (
            float(pd.Series(sbc_burdens).median()) if sbc_burdens else None
        )

        annual_growth = None
        if len(annual) >= 2 and annual[-2]["revenue"] > 0:
            annual_growth = (
                annual[-1]["revenue"] / annual[-2]["revenue"] - 1
            )

        info_growth = number("revenueGrowth")
        if info_growth is not None and info_growth > 1:
            info_growth /= 100
        revenue_growth = annual_growth if annual_growth is not None else info_growth

        latest_fcf = annual[-1]["fcf"] if annual else None
        latest_ebitda = annual[-1]["ebitda"] if annual else None

        fcf_yield = (
            latest_fcf / market_cap * 100
            if latest_fcf is not None and market_cap and market_cap > 0
            else None
        )
        fcf_yield_valid = (
            fcf_yield is not None and -10 <= fcf_yield <= 20
        )

        ps = number("priceToSalesTrailing12Months")
        pb = number("priceToBook")
        ev_ebitda = number("enterpriseToEbitda")
        ev = number("enterpriseValue")

        # Če ponudnik EV/EBITDA ne poda, ga izračunamo samo ob pozitivnem EBITDA.
        if (
            (ev_ebitda is None or ev_ebitda <= 0)
            and ev is not None
            and latest_ebitda is not None
            and latest_ebitda > 0
        ):
            ev_ebitda = ev / latest_ebitda

        analyst_upside = None
        target = number("targetMeanPrice") or number("targetMedianPrice")
        if price and target:
            analyst_upside = (target / price - 1) * 100

        try:
            revisions = stock.upgrades_downgrades
        except Exception:
            revisions = None

        upgrade_count_90d = None
        downgrade_count_90d = None
        revision_net_90d = None
        if revisions is not None and not revisions.empty:
            revision_frame = revisions.copy()
            date_column = None
            for column in revision_frame.columns:
                if str(column).lower() in ("gradedate", "date"):
                    date_column = column
                    break

            if date_column is not None:
                dates = pd.to_datetime(revision_frame[date_column], errors="coerce")
            else:
                dates = pd.to_datetime(revision_frame.index, errors="coerce")

            cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=90)
            try:
                if getattr(dates, "tz", None) is None:
                    dates = dates.tz_localize("UTC")
                else:
                    dates = dates.tz_convert("UTC")
                recent_mask = dates >= cutoff
            except Exception:
                recent_mask = pd.Series([False] * len(revision_frame))

            recent = revision_frame.loc[list(recent_mask)].copy()
            action_values = []
            for column in recent.columns:
                if str(column).lower() == "action":
                    action_values.extend(recent[column].fillna("").astype(str).tolist())

            actions = [value.lower() for value in action_values]
            upgrade_count_90d = sum(
                "up" in value or "upgrade" in value
                for value in actions
            )
            downgrade_count_90d = sum(
                "down" in value or "downgrade" in value
                for value in actions
            )
            revision_net_90d = upgrade_count_90d - downgrade_count_90d

        return {
            "ticker": ticker,
            "name": info.get("shortName") or ticker,
            "sector": get_sector_group(ticker),
            "price": price,
            "market_cap": market_cap,
            "dollar_volume": dollar_volume,
            "cash": cash,
            "debt": debt,
            "net_cash": net_cash,
            "ps": ps,
            "pb": pb,
            "ev_ebitda": ev_ebitda,
            "revenue_growth": revenue_growth,
            "annual": annual,
            "fcf_years": fcf_years,
            "positive_fcf_years": positive_fcf_years,
            "latest_fcf": latest_fcf,
            "latest_ebitda": latest_ebitda,
            "median_fcf_margin": median_fcf_margin,
            "median_cash_conversion": median_cash_conversion,
            "median_sbc_burden": median_sbc_burden,
            "fcf_yield": fcf_yield if fcf_yield_valid else None,
            "fcf_yield_valid": fcf_yield_valid,
            "analyst_count": number("numberOfAnalystOpinions"),
            "recommendation_mean": number("recommendationMean"),
            "analyst_upside": analyst_upside,
            "upgrade_count_90d": upgrade_count_90d,
            "downgrade_count_90d": downgrade_count_90d,
            "revision_net_90d": revision_net_90d,
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
    """
    FCF kakovost 0–10 iz večletne doslednosti, marže, denarne pretvorbe,
    SBC bremena in bilance. Manjkajoča polja se izpustijo, ne ugibajo.
    """
    components = []

    years = data.get("fcf_years", 0)
    if years >= 3:
        components.append(
            (data["positive_fcf_years"] / years * 10, 0.25)
        )

    margin = data.get("median_fcf_margin")
    if margin is not None:
        # 0 % = 0 točk, 20 % ali več = 10 točk.
        components.append((max(0.0, min(10.0, margin / 2)), 0.25))

    conversion = data.get("median_cash_conversion")
    if conversion is not None:
        # Omejitev prepreči, da majhen čisti dobiček nesorazmerno napihne oceno.
        components.append(
            (max(0.0, min(10.0, conversion * 5)), 0.20)
        )

    sbc_burden = data.get("median_sbc_burden")
    if sbc_burden is not None:
        components.append(
            (max(0.0, min(10.0, 10 - sbc_burden / 2)), 0.15)
        )

    net_cash = data.get("net_cash")
    if net_cash is not None:
        components.append((8.0 if net_cash >= 0 else 3.0, 0.15))

    if not components:
        return None

    total_weight = sum(weight for _, weight in components)
    if total_weight <= 0:
        return None

    result = sum(value * weight for value, weight in components) / total_weight
    return round(max(0.0, min(10.0, result)), 1)


def long_eligibility(data):
    """Strogi osnovni pogoji; vrne (ali_ustreza, razlogi)."""
    reasons = []

    if not passes_liquidity(data):
        reasons.append("likvidnost ali market cap ni potrjen")
        return False, reasons

    if data.get("fcf_years", 0) < 3:
        reasons.append("manj kot 3 skupna leta računovodskih podatkov")

    if data.get("latest_fcf") is None or data["latest_fcf"] <= 0:
        reasons.append("zadnji letni FCF ni pozitiven")

    years = data.get("fcf_years", 0)
    if years >= 3 and data.get("positive_fcf_years", 0) < 2:
        reasons.append("FCF ni bil pozitiven v vsaj 2 od zadnjih 3+ let")

    margin = data.get("median_fcf_margin")
    if margin is None or margin < 5:
        reasons.append("mediana FCF marže je pod 5 % ali manjka")

    growth = data.get("revenue_growth")
    if growth is None or growth < 0.10:
        reasons.append("rast prihodkov je pod 10 % ali manjka")

    sbc_burden = data.get("median_sbc_burden")
    if sbc_burden is not None and sbc_burden > 15:
        reasons.append("SBC presega 15 % prihodkov")

    # Če je podjetje neto zadolženo, uporabimo grobo omejitev net debt/EBITDA.
    net_cash = data.get("net_cash")
    if net_cash is not None and net_cash < 0:
        ebitda = data.get("latest_ebitda")
        if ebitda is None or ebitda <= 0:
            reasons.append("neto dolg in ni pozitivnega EBITDA za preverbo")
        elif abs(net_cash) / ebitda > 2.5:
            reasons.append("net debt / EBITDA presega 2,5x")

    return len(reasons) == 0, reasons


def data_reliability(data):
    """Pokritost polj, ne neodvisna potrditev pravilnosti podatkov."""
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
        data.get("ps") is not None or data.get("ev_ebitda") is not None,
    ]

    flags = []
    if data.get("fcf_years", 0) < 3:
        flags.append("manj kot 3 skupna leta izkazov")
    if data.get("median_cash_conversion") is None:
        flags.append("ni uporabnega razmerja CFO/čisti dobiček")
    if data.get("median_sbc_burden") is None:
        flags.append("SBC ni na voljo")
    if data.get("revision_net_90d") is None:
        flags.append("ni 90-dnevne zgodovine sprememb analitikov")
    if data.get("fcf_yield") is None:
        flags.append("FCF yield ni uporaben")

    return round(sum(checks) / len(checks) * 100), flags


def valuation_metric(data):
    group = data.get("sector")
    chosen = SECTOR_MULTIPLE.get(group)

    if chosen == "P/S":
        value = data.get("ps")
        if value is not None and value >= 1:
            return {"name": "P/S", "value": value}

    elif chosen == "P/B":
        value = data.get("pb")
        if value is not None and value > 0:
            return {"name": "P/B", "value": value}

    elif chosen == "EV/EBITDA":
        value = data.get("ev_ebitda")
        if value is not None and value > 0:
            return {"name": "EV/EBITDA", "value": value}

    return {"name": chosen or "NI PODATKA", "value": None}


def analyst_revision_score(data):
    """
    90-dnevni neto trend sprememb priporočil, če yfinance vrne uporabne podatke.
    Ne nadomešča zgodovinske baze analitikov.
    """
    net = data.get("revision_net_90d")
    if net is None:
        return None
    return round(max(0.0, min(10.0, 5.0 + net)), 1)


@st.cache_data(ttl=1800, show_spinner=False)
def scan_long_candidates(universe):
    candidates = []

    for ticker in universe:
        data = get_fundamental_data(ticker)
        if not data:
            continue

        eligible, reasons = long_eligibility(data)
        if not eligible:
            continue

        data["fcf_quality"] = fcf_quality_score(data)
        data["reliability"], data["reliability_flags"] = data_reliability(data)
        data["valuation_metric"] = valuation_metric(data)
        data["ws_revision_score"] = analyst_revision_score(data)

        # Za pošteno primerjavo mora obstajati sektorski multiple.
        if data["valuation_metric"]["value"] is None:
            continue

        candidates.append(data)

    groups = {}
    for item in candidates:
        groups.setdefault(item["sector"], []).append(item)

    ranked = []
    for group_name, group_items in groups.items():
        # Ne uporabljamo peer-percentila za 1–4 podjetja.
        if len(group_items) < 5:
            continue

        multiple_names = {item["valuation_metric"]["name"] for item in group_items}
        if len(multiple_names) != 1:
            continue

        metric_name = next(iter(multiple_names))
        metric_values = [
            item["valuation_metric"]["value"]
            for item in group_items
            if item["valuation_metric"]["value"] is not None
        ]
        fcf_scores = [
            item["fcf_quality"]
            for item in group_items
            if item["fcf_quality"] is not None
        ]
        growth_values = [
            item["revenue_growth"]
            for item in group_items
            if item["revenue_growth"] is not None
        ]

        for item in group_items:
            item["peer_count"] = len(group_items)
            item["comparison_metric_name"] = metric_name

            # Nižji multiple je ugodnejši. Percentil se izračuna le ob >=5 peerjih.
            own_multiple = item["valuation_metric"]["value"]
            item["valuation_percentile"] = round(
                sum(value >= own_multiple for value in metric_values)
                / len(metric_values)
                * 100
            )

            own_fcf = item["fcf_quality"]
            item["fcf_percentile"] = (
                round(
                    sum(value <= own_fcf for value in fcf_scores)
                    / len(fcf_scores)
                    * 100
                )
                if own_fcf is not None and fcf_scores
                else None
            )

            own_growth = item["revenue_growth"]
            item["growth_percentile"] = (
                round(
                    sum(value <= own_growth for value in growth_values)
                    / len(growth_values)
                    * 100
                )
                if own_growth is not None and growth_values
                else None
            )

            # Vsaka komponenta je normalizirana na 0–10 znotraj iste skupine.
            components = [
                (item["valuation_percentile"] / 10, 0.35),
            ]
            if item["fcf_percentile"] is not None:
                components.append((item["fcf_percentile"] / 10, 0.40))
            if item["growth_percentile"] is not None:
                components.append((item["growth_percentile"] / 10, 0.15))
            if item["ws_revision_score"] is not None:
                components.append((item["ws_revision_score"], 0.10))

            total_weight = sum(weight for _, weight in components)
            item["composite_score"] = round(
                sum(score * weight for score, weight in components)
                / total_weight,
                1,
            )
            item["sector"] = group_name
            ranked.append(item)

    ranked.sort(
        key=lambda item: (
            item["composite_score"],
            item["reliability"],
            item["ticker"],
        ),
        reverse=True,
    )
    return ranked


# ============================================================
# PREMARKET INTRADAY SCANNER
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
    earlier_dates = sorted({
        stamp.date() for stamp in frame.index
        if stamp.date() < date_value
    }, reverse=True)

    for earlier_date in earlier_dates:
        bars = session_bars(frame, earlier_date, "regular")
        if not bars.empty:
            value = safe_float(bars["Close"].iloc[-1])
            if value and value > 0:
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
    cumulative = volume.cumsum().replace(0, float("nan"))
    return (typical * volume).cumsum() / cumulative


def same_time_volume_ratio(frame, stamp, bars, index):
    current_volume = safe_float(bars["Volume"].iloc[index])
    if current_volume is None or current_volume <= 0:
        return None

    session = "premarket" if stamp.time() < time(9, 30) else "regular"
    clock = stamp.strftime("%H:%M")
    prior_dates = sorted({
        item.date() for item in frame.index
        if item.date() < stamp.date()
    })[-5:]

    previous_volumes = []
    for prior_date in prior_dates:
        prior = session_bars(frame, prior_date, session)
        matches = [
            item for item in prior.index
            if item.strftime("%H:%M") == clock
        ]
        if matches:
            value = safe_float(prior.loc[matches[-1], "Volume"])
            if value is not None and value > 0:
                previous_volumes.append(value)

    if not previous_volumes:
        return None

    baseline = float(pd.Series(previous_volumes).median())
    return current_volume / baseline if baseline > 0 else None


def rsi_value(values, period=14):
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
    # None pomeni, da preverjanja ni bilo mogoče zanesljivo opraviti.
    try:
        dates = yf.Ticker(ticker).get_earnings_dates(limit=8)
        if dates is None or len(dates) == 0:
            return None

        today = datetime.now(NY_TZ).date()
        for raw in dates.index:
            value = pd.Timestamp(raw)
            if value.tzinfo is not None:
                value = value.tz_convert(None)
            delta = (value.date() - today).days
            if 0 <= delta <= days:
                return False
        return True
    except Exception:
        return None


def find_reversal_signal(ticker, frame, now=None):
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

    latest = completed.index[-1]
    session = "premarket" if latest.time() < time(9, 30) else "regular"
    bars = session_bars(frame, today, session)
    bars = bars[
        [stamp + timedelta(minutes=5) <= now for stamp in bars.index]
    ]

    if len(bars) < 15:
        return None

    prev_close = previous_regular_close(frame, today)
    if prev_close is None:
        return None

    if not earnings_clear(ticker, 5):
        return None

    vwap = session_vwap(bars)
    signals = []

    for index in range(14, len(bars)):
        stamp = bars.index[index]
        close = safe_float(bars["Close"].iloc[index])
        open_price = safe_float(bars["Open"].iloc[index])
        previous = safe_float(bars["Close"].iloc[index - 1])
        current_vwap = safe_float(vwap.iloc[index])
        prior_vwap = safe_float(vwap.iloc[index - 1])

        if any(value is None for value in (
            close, open_price, previous, current_vwap, prior_vwap
        )):
            continue

        gap = (close / prev_close - 1) * 100
        if not -8 <= gap <= -1:
            continue

        crossed = previous <= prior_vwap and close > current_vwap
        if not crossed or close <= open_price:
            continue

        rsi = rsi_value(bars["Close"].iloc[:index + 1])
        volume_ratio = same_time_volume_ratio(frame, stamp, bars, index)
        momentum = (close / previous - 1) * 100

        if rsi is None or rsi >= 35:
            continue
        if volume_ratio is None or volume_ratio < 1.3:
            continue
        if momentum <= 0:
            continue

        score = 6.0 + min((volume_ratio - 1.3) * 0.5, 1.5)
        score += min(momentum * 0.25, 1.0)
        score -= market["penalty"]
        score = round(max(0.0, min(10.0, score)), 1)

        signals.append({
            "Ticker": ticker,
            "Čas": stamp.strftime("%H:%M ET"),
            "Seja": "PREMARKET" if session == "premarket" else "REDNA SEJA",
            "Cena": round(close, 2),
            "Gap %": round(gap, 2),
            "VWAP": round(current_vwap, 2),
            "Odstopanje VWAP %": round((close / current_vwap - 1) * 100, 2),
            "Volumen proti isti uri x": round(volume_ratio, 2),
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
        frame = get_intraday_history(ticker, "5d")
        if frame is None:
            continue

        signal = find_reversal_signal(ticker, frame, now)
        if signal:
            results.append(signal)

    results.sort(key=lambda item: item["Ocena filtra"], reverse=True)
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
        prior = close.shift(1)

        true_range = pd.concat(
            [
                high - low,
                (high - prior).abs(),
                (low - prior).abs(),
            ],
            axis=1,
        ).max(axis=1)

        value = safe_float(true_range.rolling(14).mean().iloc[-1])
        return value if value is not None and value > 0 else None
    except Exception:
        return None


# ============================================================
# GEMINI ANALITIK
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

            last_error = f"{model}: HTTP {response.status_code} {response.text[:250]}"
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
api_key = st.sidebar.text_input(
    "Gemini API ključ (neobvezno)",
    type="password",
)
st.sidebar.caption(f"Unikatni tickerji: {len(AI_UNIVERSE)}")
st.sidebar.caption("Podatki Yahoo Finance so lahko zakasnjeni ali nepopolni.")
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Tržni režim:** {market['regime']}")

if market["change20"] is not None:
    st.sidebar.caption(f"SPY 20d: {market['change20']:+.2f}%")

if st.sidebar.button("Osveži skene"):
    scan_long_candidates.clear()
    scan_reversals.clear()
    get_fundamental_data.clear()
    get_intraday_history.clear()
    get_market_regime.clear()
    get_capital_rotation.clear()
    st.rerun()

st.title("Value Ledger 2.0")
st.caption(
    "Fundamentalne ocene so relativna hevristika, ne napoved donosa. "
    "Skener ne oddaja naročil."
)

with st.spinner("Skeniram fundamentalne in intraday podatke..."):
    long_candidates = scan_long_candidates(tuple(AI_UNIVERSE))
    reversal_candidates = scan_reversals(tuple(AI_UNIVERSE))

best_long = long_candidates[0] if long_candidates else None
best_reversal = reversal_candidates[0] if reversal_candidates else None


# ============================================================
# DINAMIČNI ZLATI LONG IN ZELENI REVERSAL
# ============================================================

long_col, reversal_col = st.columns(2)

with long_col:
    if best_long:
        item = best_long
        atr = get_atr(item["ticker"])
        stop = item["price"] - 1.5 * atr if atr and item["price"] else None
        target1 = item["price"] + 1.5 * atr if atr and item["price"] else None
        target2 = item["price"] + 2.5 * atr if atr and item["price"] else None

        warning_text = (
            "; ".join(item["reliability_flags"])
            if item["reliability_flags"]
            else "brez samodejnih opozoril"
        )

        st.markdown(
            f"""
            <div class="hero-long">
              <div style="color:#FBBF24;font-size:0.78rem;font-weight:700;">
                FUNDAMENTALNI LONG · SEKTORSKO PRIMERJANJE
              </div>
              <div style="font-size:1.55rem;font-weight:700;color:#FFFFFF;margin-top:5px;">
                {html.escape(item["ticker"])}
              </div>
              <div style="color:#CBD5E1;font-size:0.86rem;margin-top:2px;">
                {html.escape(item["name"])} · {html.escape(item["sector"])}
              </div>
              <div style="color:#F8FAFC;font-size:1rem;margin-top:10px;">
                Cena {display_value(item["price"])} ·
                Skupna ocena {item["composite_score"]}/10
              </div>
              <div style="color:#CBD5E1;font-size:0.78rem;margin-top:8px;line-height:1.7;">
                Kakovost FCF {display_value(item["fcf_quality"], 1)}/10 ·
                Vrednotenje {item["valuation_percentile"]}/100<br>
                Rastni percentil {item["growth_percentile"]}/100 ·
                WS spremembe 90d {display_value(item["revision_net_90d"], 0)}<br>
                Peerji {item["peer_count"]} · Zanesljivost polj {item["reliability"]}/100<br>
                ATR {display_value(atr)} · STOP {display_value(stop)} ·
                T1 {display_value(target1)} · T2 {display_value(target2)}<br>
                Opozorila: {html.escape(warning_text)}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="hero-long">
              <div style="color:#FBBF24;font-size:0.78rem;font-weight:700;">
                FUNDAMENTALNI LONG · SEKTORSKO PRIMERJANJE
              </div>
              <div style="font-size:1.3rem;font-weight:700;color:#FFFFFF;margin-top:12px;">
                NI DOVOLJ PODATKOV ZA ZANESLJIVO PRIMERJAVO
              </div>
              <div style="color:#CBD5E1;font-size:0.82rem;margin-top:10px;">
                Kandidat mora prestati stroge FCF, rastne in bilančne filtre,
                njegova skupina pa mora imeti vsaj 5 primernih peerjev.
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
              <div style="color:#F8FAFC;font-size:1rem;margin-top:10px;">
                Cena {item["Cena"]} · Ocena filtra {item["Ocena filtra"]}/10
              </div>
              <div style="color:#CBD5E1;font-size:0.78rem;margin-top:8px;line-height:1.7;">
                Gap {item["Gap %"]:+.2f}% · VWAP {item["VWAP"]}<br>
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
              <div style="color:#6EE7B7;font-size:0.78rem;font-weight:700;">
                NAJBOLJŠE UJEMANJE INTRADAY FILTROV · NI NAPOVED
              </div>
              <div style="font-size:1.3rem;font-weight:700;color:#FFFFFF;margin-top:12px;">
                NI STROGEGA KANDIDATA
              </div>
              <div style="color:#CBD5E1;font-size:0.82rem;margin-top:10px;">
                Noben ticker trenutno ne prestane vseh intraday pogojev.
                Skener kandidata ne izbere na silo.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.caption(
    "Zlata kartica prikazuje najbolje uvrščenega kandidata, ki je prestal "
    "fundamentalne filtre in ima vsaj pet peerjev. Zelena kartica prikazuje "
    "najboljše ujemanje reversal filtrov. Nobena ni samodejno naročilo za nakup."
)


# ============================================================
# CAPITAL ROTATION
# ============================================================

st.subheader("Capital Rotation Radar")

detail_html = ""
if rotation["detail"]:
    detail_html = (
        "<div style='color:#94A3B8;font-size:0.82rem;margin-top:6px;'>"
        + html.escape(rotation["detail"])
        + "</div>"
    )

st.markdown(
    "<div class='ledger-card'>"
    "<div style='color:#FBBF24;font-weight:700;font-size:1rem;'>"
    + html.escape(rotation["rotation"])
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
    "Relativna moč ETF-jev je cenovni približek, ne neposredno merjenje "
    "Wall Street tokov kapitala ali spremembe analitičnega sentimenta."
)


# ============================================================
# TOP 5 LONG
# ============================================================

st.subheader("TOP 5 Long · kakovost FCF, vrednotenje in sektor")
st.caption(
    "Vrednotenje se primerja samo znotraj sektorske skupine in z istim "
    "multiple-om. Potrebnih je vsaj 5 kandidatov, ki prestanejo osnovne "
    "filtre; sicer sektorskega percentila ne prikažemo."
)

if long_candidates:
    long_table = []

    for item in long_candidates[:5]:
        metric = item["valuation_metric"]

        long_table.append({
            "Ticker": item["ticker"],
            "Podjetje": item["name"],
            "Skupina": item["sector"],
            "Peerji": item["peer_count"],
            "Skupna ocena / 10": item["composite_score"],
            "Kakovost FCF / 10": display_value(item["fcf_quality"], 1),
            "FCF pozitivna leta": (
                f"{item['positive_fcf_years']}/{item['fcf_years']}"
            ),
            "Mediana FCF marže %": display_value(
                item["median_fcf_margin"], 1, "%"
            ),
            "CFO / čisti dobiček": display_value(
                item["median_cash_conversion"], 2, "x"
            ),
            "SBC / prihodki %": display_value(
                item["median_sbc_burden"], 1, "%"
            ),
            "Vrednotenjski multiple": metric["name"],
            "Vrednost multipla": display_value(metric["value"]),
            "Vrednotenje v sektorju / 100": item["valuation_percentile"],
            "Rast prihodkov %": display_value(
                item["revenue_growth"] * 100, 1, "%"
            ),
            "Rastni percentil / 100": item["growth_percentile"],
            "WS neto spremembe 90d": display_value(
                item["revision_net_90d"], 0
            ),
            "Zanesljivost polj / 100": item["reliability"],
            "Opozorila": (
                "; ".join(item["reliability_flags"])
                if item["reliability_flags"]
                else "—"
            ),
        })

    render_dark_table(pd.DataFrame(long_table))
else:
    st.info(
        "Ni kandidata, ki bi prestal pogoje ali imel dovolj primerljivih "
        "podjetij za sektorsko vrednotenje."
    )

st.caption(
    "Zanesljivost polj pomeni razpoložljivost izbranih podatkov, ne "
    "neodvisne potrditve njihove pravilnosti. Točkovanje in pragovi so "
    "začetna hevristika, ne potrjen trgovalni model."
)


# ============================================================
# TOP 5 REVERSAL
# ============================================================

st.subheader("TOP 5 Intraday Reversal")
st.caption(
    "Premarket in redna seja imata ločeno izračunan VWAP. Volumen se "
    "primerja z isto 5-minutno uro in isto vrsto seje v preteklih dneh."
)

if reversal_candidates:
    render_dark_table(pd.DataFrame(reversal_candidates))
else:
    st.info(
        "NI STROGEGA KANDIDATA. Filter zahteva padec od -1 % do -8 % proti "
        "prejšnjemu close-u, dejanski prehod VWAP-a navzgor, zeleno svečo, "
        "RSI pod 35, volumen vsaj 1,3×, pozitiven momentum in preverjene earnings."
    )

st.warning(
    "Premarket
