import os
from datetime import datetime

import requests
import pandas as pd
import streamlit as st
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FINNHUB_API_KEY")

SEC_HEADERS = {
    "User-Agent": "BorsaRobotu/1.0 contact@example.com"
}

SYMBOLS = ["NTSK", "NVDA", "CRWD", "ALAB"]

st.set_page_config(
    page_title="ABD Borsa Robotu",
    layout="wide"
)

st.title("📈 ABD Borsa Robotu")

st.caption(
    "Finnhub + Yahoo Finance + Teknik Analiz + SEC XBRL Finansal Analiz"
)


# =========================================================
# FINNHUB CANLI FİYAT
# =========================================================

def get_quote(symbol):

    try:

        r = requests.get(
            "https://finnhub.io/api/v1/quote",
            params={
                "symbol": symbol,
                "token": API_KEY
            },
            timeout=10
        )

        r.raise_for_status()

        return r.json()

    except Exception:

        return {}


# =========================================================
# YAHOO GEÇMİŞ VERİ
# =========================================================

@st.cache_data(ttl=900)
def get_history(symbol):

    try:

        df = yf.download(
            symbol,
            period="6mo",
            interval="1d",
            progress=False,
            auto_adjust=False
        )

        if df.empty:
            return pd.DataFrame()

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        return df.dropna()

    except Exception:

        return pd.DataFrame()


def calculate_rsi(series, period=14):

    delta = series.diff()

    gain = delta.clip(lower=0)

    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        min_periods=period,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss.replace(
        0,
        0.000001
    )

    return 100 - (100 / (1 + rs))


def add_indicators(df):

    df = df.copy()

    df["SMA20"] = df["Close"].rolling(20).mean()

    df["SMA50"] = df["Close"].rolling(50).mean()

    df["RSI"] = calculate_rsi(
        df["Close"]
    )

    ema12 = df["Close"].ewm(
        span=12,
        adjust=False
    ).mean()

    ema26 = df["Close"].ewm(
        span=26,
        adjust=False
    ).mean()

    df["MACD"] = ema12 - ema26

    df["MACD_SIGNAL"] = (
        df["MACD"]
        .ewm(
            span=9,
            adjust=False
        )
        .mean()
    )

    previous_close = df["Close"].shift(1)

    tr1 = df["High"] - df["Low"]

    tr2 = (
        df["High"] - previous_close
    ).abs()

    tr3 = (
        df["Low"] - previous_close
    ).abs()

    df["TR"] = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    df["ATR14"] = (
        df["TR"]
        .rolling(14)
        .mean()
    )

    df["VOL20"] = (
        df["Volume"]
        .rolling(20)
        .mean()
    )

    df["SUPPORT20"] = (
        df["Low"]
        .rolling(20)
        .min()
    )

    df["RESIST20"] = (
        df["High"]
        .rolling(20)
        .max()
    )

    return df


# =========================================================
# TEKNİK PUAN
# =========================================================

def analyze_technical(symbol):

    quote = get_quote(symbol)

    df = get_history(symbol)

    live_price = float(
        quote.get("c", 0) or 0
    )

    daily_change = float(
        quote.get("dp", 0) or 0
    )

    result = {
        "Hisse": symbol,
        "Fiyat": live_price,
        "Günlük %": daily_change,
        "RSI": None,
        "MACD": None,
        "ATR %": None,
        "Hacim": None,
        "Destek": None,
        "Direnç": None,
        "Teknik Puan": 50
    }

    if df.empty or len(df) < 60:
        return result

    df = add_indicators(df)

    latest = df.iloc[-1]

    price = (
        live_price
        if live_price > 0
        else float(latest["Close"])
    )

    rsi = float(latest["RSI"])

    sma20 = float(latest["SMA20"])

    sma50 = float(latest["SMA50"])

    macd = float(latest["MACD"])

    macd_signal = float(
        latest["MACD_SIGNAL"]
    )

    atr = float(
        latest["ATR14"]
    )

    atr_pct = (
        atr / price * 100
        if price > 0
        else 0
    )

    volume = float(
        latest["Volume"]
    )

    avg_volume = float(
        latest["VOL20"]
    )

    volume_ratio = (
        volume / avg_volume
        if avg_volume > 0
        else 0
    )

    support = float(
        latest["SUPPORT20"]
    )

    resistance = float(
        latest["RESIST20"]
    )

    score = 50

    # Trend
    score += 8 if price > sma20 else -8

    score += 7 if price > sma50 else -7

    score += 5 if sma20 > sma50 else -5

    # RSI
    if 50 <= rsi <= 65:
        score += 8

    elif 40 <= rsi < 50:
        score += 4

    elif 30 <= rsi < 40:
        score += 1

    elif 65 < rsi <= 70:
        score += 2

    elif rsi > 75:
        score -= 10

    elif rsi < 30:
        score += 3

    # MACD
    if macd > macd_signal and macd > 0:
        score += 10

    elif macd > macd_signal:
        score += 5

    elif macd < macd_signal and macd < 0:
        score -= 10

    else:
        score -= 4

    # Hacim
    if volume_ratio >= 1.5:

        score += (
            8
            if daily_change > 0
            else -8
        )

    elif volume_ratio >= 1.1:

        score += (
            4
            if daily_change > 0
            else -4
        )

    elif volume_ratio < 0.6:

        score -= 3

    # Momentum
    if daily_change >= 3:

        score += 5

    elif daily_change >= 1:

        score += 2

    elif daily_change <= -5:

        score -= 8

    elif daily_change <= -3:

        score -= 5

    # Destek
    if price > 0:

        support_distance = (
            (price - support)
            / price
            * 100
        )

        if 0 <= support_distance <= 3:
            score += 5

    # Direnç
    if price > 0:

        resistance_distance = (
            (resistance - price)
            / price
            * 100
        )

        if 0 <= resistance_distance <= 2:
            score -= 4

    # ATR
    if atr_pct >= 8:

        score -= 8

    elif atr_pct >= 5:

        score -= 4

    elif atr_pct <= 3:

        score += 2

    score = max(
        0,
        min(
            100,
            round(score)
        )
    )

    result.update({

        "Fiyat": round(price, 2),

        "RSI": round(rsi, 1),

        "MACD": round(macd, 2),

        "ATR %": round(atr_pct, 2),

        "Hacim": round(volume_ratio, 2),

        "Destek": round(support, 2),

        "Direnç": round(resistance, 2),

        "Teknik Puan": score

    })

    return result


# =========================================================
# SEC TICKER -> CIK
# =========================================================

@st.cache_data(ttl=86400)
def get_sec_ticker_map():

    try:

        r = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=SEC_HEADERS,
            timeout=15
        )

        r.raise_for_status()

        raw = r.json()

        ticker_map = {}

        for item in raw.values():

            ticker = str(
                item["ticker"]
            ).upper()

            cik = str(
                item["cik_str"]
            ).zfill(10)

            ticker_map[ticker] = cik

        return ticker_map

    except Exception:

        return {}


# =========================================================
# SEC COMPANYFACTS / XBRL
# =========================================================

@st.cache_data(ttl=3600)
def get_companyfacts(symbol):

    ticker_map = get_sec_ticker_map()

    cik = ticker_map.get(
        symbol.upper()
    )

    if not cik:

        return {}

    try:

        url = (
            "https://data.sec.gov/api/xbrl/"
            f"companyfacts/CIK{cik}.json"
        )

        r = requests.get(
            url,
            headers=SEC_HEADERS,
            timeout=20
        )

        r.raise_for_status()

        return r.json()

    except Exception:

        return {}


def get_us_gaap_facts(companyfacts):

    return (
        companyfacts
        .get("facts", {})
        .get("us-gaap", {})
    )


def get_fact_units(
    facts,
    possible_tags
):

    for tag in possible_tags:

        item = facts.get(tag)

        if not item:

            continue

        units = item.get(
            "units",
            {}
        )

        for unit_name in [
            "USD",
            "shares"
        ]:

            if unit_name in units:

                return units[
                    unit_name
                ]

    return []


# =========================================================
# ÇEYREKLİK GELİR / KÂR
# =========================================================

def quarterly_values(
    facts,
    tags
):

    units = get_fact_units(
        facts,
        tags
    )

    rows = []

    for item in units:

        form = item.get("form")

        if form != "10-Q":
            continue

        start = item.get("start")

        end = item.get("end")

        val = item.get("val")

        if (
            not start
            or not end
            or val is None
        ):
            continue

        try:

            start_date = datetime.strptime(
                start,
                "%Y-%m-%d"
            )

            end_date = datetime.strptime(
                end,
                "%Y-%m-%d"
            )

            days = (
                end_date
                -
                start_date
            ).days

            # Yaklaşık tek çeyreklik değer
            if 65 <= days <= 115:

                rows.append({
                    "start": start,
                    "end": end,
                    "val": float(val)
                })

        except Exception:

            pass

    if not rows:

        return []

    df = pd.DataFrame(rows)

    df = (
        df
        .drop_duplicates(
            subset=["end"],
            keep="last"
        )
        .sort_values("end")
    )

    return df.to_dict(
        "records"
    )


def calculate_yoy(
    quarterly_data
):

    if len(quarterly_data) < 2:

        return None

    latest = quarterly_data[-1]

    latest_end = datetime.strptime(
        latest["end"],
        "%Y-%m-%d"
    )

    best_previous = None

    best_difference = 9999

    for row in quarterly_data[:-1]:

        old_end = datetime.strptime(
            row["end"],
            "%Y-%m-%d"
        )

        difference = (
            latest_end
            -
            old_end
        ).days

        if 300 <= difference <= 430:

            distance = abs(
                difference - 365
            )

            if distance < best_difference:

                best_previous = row

                best_difference = distance

    if not best_previous:

        return None

    old_value = float(
        best_previous["val"]
    )

    new_value = float(
        latest["val"]
    )

    if old_value == 0:

        return None

    return (
        (new_value - old_value)
        / abs(old_value)
        * 100
    )


# =========================================================
# SON BİLANÇO DEĞERİ
# =========================================================

def latest_instant_value(
    facts,
    tags
):

    units = get_fact_units(
        facts,
        tags
    )

    rows = []

    for item in units:

        if item.get("form") not in [
            "10-Q",
            "10-K"
        ]:

            continue

        end = item.get("end")

        val = item.get("val")

        if not end or val is None:

            continue

        rows.append({
            "end": end,
            "val": float(val)
        })

    if not rows:

        return None, None

    df = pd.DataFrame(rows)

    df = (
        df
        .drop_duplicates(
            subset=["end"],
            keep="last"
        )
        .sort_values("end")
    )

    latest = df.iloc[-1]

    previous = (
        df.iloc[-2]
        if len(df) >= 2
        else None
    )

    return (
        float(latest["val"]),
        (
            float(previous["val"])
            if previous is not None
            else None
        )
    )


# =========================================================
# SEC XBRL FİNANSAL PUAN
# =========================================================

def analyze_sec_xbrl(symbol):

    companyfacts = (
        get_companyfacts(symbol)
    )

    facts = (
        get_us_gaap_facts(
            companyfacts
        )
    )

    result = {
        "Hisse": symbol,
        "Gelir Büyüme %": None,
        "Net Kâr": None,
        "Nakit": None,
        "Borç": None,
        "Hisse Değişim %": None,
        "SEC Finansal Puan": 50,
        "SEC Durum": "🟡 NÖTR"
    }

    if not facts:

        return result

    # -----------------------------------------------------
    # GELİR
    # -----------------------------------------------------

    revenue_tags = [

        "RevenueFromContractWithCustomerExcludingAssessedTax",

        "Revenues",

        "SalesRevenueNet"
    ]

    revenue_quarters = quarterly_values(
        facts,
        revenue_tags
    )

    revenue_growth = calculate_yoy(
        revenue_quarters
    )

    # -----------------------------------------------------
    # NET KÂR
    # -----------------------------------------------------

    income_tags = [
        "NetIncomeLoss"
    ]

    income_quarters = quarterly_values(
        facts,
        income_tags
    )

    latest_income = None

    if income_quarters:

        latest_income = float(
            income_quarters[-1]["val"]
        )

    # -----------------------------------------------------
    # NAKİT
    # -----------------------------------------------------

    cash_tags = [

        "CashAndCashEquivalentsAtCarryingValue",

        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"
    ]

    cash_latest, cash_previous = (
        latest_instant_value(
            facts,
            cash_tags
        )
    )

    # -----------------------------------------------------
    # BORÇ
    # -----------------------------------------------------

    debt_tags = [

        "LongTermDebtAndFinanceLeaseObligationsCurrent",

        "LongTermDebtCurrent",

        "LongTermDebtNoncurrent",

        "LongTermDebt"
    ]

    debt_latest, debt_previous = (
        latest_instant_value(
            facts,
            debt_tags
        )
    )

    # -----------------------------------------------------
    # HİSSE SAYISI
    # -----------------------------------------------------

    share_tags = [
        "CommonStockSharesOutstanding"
    ]

    shares_latest, shares_previous = (
        latest_instant_value(
            facts,
            share_tags
        )
    )

    share_change = None

    if (
        shares_latest is not None
        and shares_previous is not None
        and shares_previous > 0
    ):

        share_change = (
            (
                shares_latest
                -
                shares_previous
            )
            /
            shares_previous
            *
            100
        )

    # -----------------------------------------------------
    # PUANLAMA
    # -----------------------------------------------------

    score = 50

    # Gelir büyümesi
    if revenue_growth is not None:

        if revenue_growth >= 30:

            score += 18

        elif revenue_growth >= 20:

            score += 14

        elif revenue_growth >= 10:

            score += 10

        elif revenue_growth >= 0:

            score += 4

        elif revenue_growth <= -20:

            score -= 15

        elif revenue_growth < 0:

            score -= 8

    # Kâr / zarar
    if latest_income is not None:

        if latest_income > 0:

            score += 10

        else:

            score -= 5

    # Nakit değişimi
    if (
        cash_latest is not None
        and cash_previous is not None
        and cash_previous > 0
    ):

        cash_change = (
            (
                cash_latest
                -
                cash_previous
            )
            /
            cash_previous
            *
            100
        )

        if cash_change >= 10:

            score += 6

        elif cash_change <= -20:

            score -= 6

    # Borç
    if (
        debt_latest is not None
        and debt_previous is not None
        and debt_previous > 0
    ):

        debt_change = (
            (
                debt_latest
                -
                debt_previous
            )
            /
            debt_previous
            *
            100
        )

        if debt_change <= -10:

            score += 5

        elif debt_change >= 25:

            score -= 7

    # Dilution
    if share_change is not None:

        if share_change >= 10:

            score -= 15

        elif share_change >= 5:

            score -= 9

        elif share_change >= 2:

            score -= 4

        elif share_change < 0:

            score += 2

    score = max(
        0,
        min(
            100,
            round(score)
        )
    )

    if score >= 80:

        sec_status = "🟢 GÜÇLÜ"

    elif score >= 65:

        sec_status = "🟢 OLUMLU"

    elif score >= 50:

        sec_status = "🟡 NÖTR"

    elif score >= 35:

        sec_status = "🟠 TEMKİNLİ"

    else:

        sec_status = "🔴 ZAYIF"

    result.update({

        "Gelir Büyüme %":
            (
                round(
                    revenue_growth,
                    1
                )
                if revenue_growth is not None
                else None
            ),

        "Net Kâr":
            (
                round(
                    latest_income / 1_000_000,
                    1
                )
                if latest_income is not None
                else None
            ),

        "Nakit":
            (
                round(
                    cash_latest / 1_000_000,
                    1
                )
                if cash_latest is not None
                else None
            ),

        "Borç":
            (
                round(
                    debt_latest / 1_000_000,
                    1
                )
                if debt_latest is not None
                else None
            ),

        "Hisse Değişim %":
            (
                round(
                    share_change,
                    2
                )
                if share_change is not None
                else None
            ),

        "SEC Finansal Puan":
            score,

        "SEC Durum":
            sec_status

    })

    return result


# =========================================================
# TÜM ANALİZLER
# =========================================================

technical_data = [

    analyze_technical(symbol)

    for symbol in SYMBOLS

]

sec_data = [

    analyze_sec_xbrl(symbol)

    for symbol in SYMBOLS

]


sec_map = {

    row["Hisse"]: row

    for row in sec_data

}


# =========================================================
# BİRLEŞİK YATIRIM PUANI
# =========================================================

combined = []

for technical in technical_data:

    symbol = technical[
        "Hisse"
    ]

    technical_score = technical[
        "Teknik Puan"
    ]

    sec_score = sec_map[
        symbol
    ][
        "SEC Finansal Puan"
    ]

    total = round(

        technical_score * 0.60

        +

        sec_score * 0.40

    )

    if total >= 85:

        decision = "🟢 GÜÇLÜ AL"

    elif total >= 70:

        decision = "🟢 AL"

    elif total >= 55:

        decision = "🟡 İZLE"

    elif total >= 40:

        decision = "🟠 TEMKİNLİ"

    else:

        decision = "🔴 RİSKLİ"

    combined.append({

        "Hisse":
            symbol,

        "Fiyat":
            technical["Fiyat"],

        "Teknik":
            technical_score,

        "SEC Finansal":
            sec_score,

        "Toplam":
            total,

        "Karar":
            decision

    })


# =========================================================
# EKRAN
# =========================================================

st.subheader(
    "🏆 Birleşik Yatırım Puanı"
)

st.dataframe(
    pd.DataFrame(combined).fillna("—"),
    width="stretch",
    hide_index=True
)


st.subheader(
    "🎯 Teknik Analiz"
)

st.dataframe(
    pd.DataFrame(technical_data).fillna("—"),
    width="stretch",
    hide_index=True
)


st.subheader(
    "🏛️ SEC XBRL Finansal Analiz"
)

st.dataframe(
    pd.DataFrame(sec_data).fillna("—"),
    width="stretch",
    hide_index=True
)


st.caption(
    "Net Kâr, Nakit ve Borç değerleri milyon USD olarak gösterilir."
)


st.info(
    "Bu sürüm SEC companyfacts/XBRL verilerinden "
    "gerçek finansal rakamları kullanır. "
    "SEC puanı: gelir büyümesi, kârlılık, nakit, "
    "borç ve hisse sayısı/dilution değişimine göre hesaplanır."
)


st.warning(
    "Bu puan yatırım tavsiyesi değildir. "
    "Sonraki aşamada Form 4 insider alış/satış, "
    "8-K olay analizi, bilanço beklentisi ve "
    "haber/katalizör puanı ayrıca eklenecek."
)


if st.button(
    "🔄 Verileri Yenile"
):

    st.cache_data.clear()

    st.rerun()
