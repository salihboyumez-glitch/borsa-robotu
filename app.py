from app_smart_insider_working import *

import re
import html
from datetime import datetime, timedelta

import pandas as pd
import requests
import streamlit as st

from dashboard_extras import render_extras
from opportunity_scanner import render_opportunity_scanner


# =========================================================
# AYARLAR
# =========================================================

st.title("🚀 ABD Borsa Robotu — FINAL")

st.caption(
    "Teknik + SEC finansal + Form 4 insider + "
    "8-K + güncel Finnhub haber katalizörleri"
)


# =========================================================
# AKILLI INSIDER
# =========================================================

def final_insider(symbol):

    base = parse_form4(symbol)
    ctx = form4_context(symbol)

    işlem = str(base.get("İşlem", ""))

    value = base.get("Yaklaşık $")

    try:
        value = float(value)
    except Exception:
        value = 0

    note = str(
        ctx.get("Footnote / Açıklama", "")
    ).lower()

    plan = str(
        ctx.get("10b5-1", "")
    )


    if "ALIŞ" in işlem:

        if value >= 1_000_000:
            return 85, "🟢 Güçlü açık piyasa alış"

        if value >= 250_000:
            return 78, "🟢 Açık piyasa alış"

        return 70, "🟢 Insider alış"


    if "SATIŞ" in işlem:

        tax_words = [
            "tax",
            "withholding",
            "withhold",
            "satisfy tax",
            "tax liability"
        ]

        if any(x in note for x in tax_words):
            return 50, "⚪ Vergi amaçlı satış"

        if "EVET" in plan:
            return 47, "⚪ 10b5-1 planlı satış"

        if value >= 5_000_000:
            return 30, "🔴 Büyük açık piyasa satış"

        if value >= 1_000_000:
            return 35, "🔴 Açık piyasa satış"

        return 40, "🟠 Insider satış"


    return 50, "⚪ Yönsüz / diğer"


# =========================================================
# SEC 8-K
# =========================================================

@st.cache_data(ttl=1800)
def get_latest_8k(symbol):

    try:

        ticker_map = get_sec_ticker_map()
        cik = ticker_map.get(symbol.upper())

        if not cik:
            return None

        url = (
            f"https://data.sec.gov/submissions/"
            f"CIK{cik}.json"
        )

        r = requests.get(
            url,
            headers=SEC_HEADERS,
            timeout=20
        )

        r.raise_for_status()

        recent = r.json()["filings"]["recent"]

        for form, date, accession, document in zip(
            recent["form"],
            recent["filingDate"],
            recent["accessionNumber"],
            recent["primaryDocument"]
        ):

            if form in ["8-K", "8-K/A"]:

                return {
                    "CIK": cik,
                    "Tarih": date,
                    "Accession": accession,
                    "Document": document
                }

    except Exception:
        pass

    return None


@st.cache_data(ttl=1800)
def get_8k_text(cik, accession):

    try:

        cik_num = str(int(cik))
        acc = accession.replace("-", "")

        base = (
            "https://www.sec.gov/Archives/"
            f"edgar/data/{cik_num}/{acc}/"
        )

        idx = requests.get(
            base + "index.json",
            headers=SEC_HEADERS,
            timeout=20
        )

        idx.raise_for_status()

        items = (
            idx.json()
            .get("directory", {})
            .get("item", [])
        )

        names = []

        for item in items:

            name = str(item.get("name", ""))

            if name.lower().endswith(
                (".htm", ".html")
            ):
                names.append(name)

        # Exhibit 99 genelde bilanço basın bülteni
        names.sort(
            key=lambda n:
            0 if "99" in n.lower() else 1
        )

        texts = []

        for name in names[:6]:

            try:

                r = requests.get(
                    base + name,
                    headers=SEC_HEADERS,
                    timeout=20
                )

                if not r.ok:
                    continue

                text = r.text

                text = re.sub(
                    r"<script[\s\S]*?</script>",
                    " ",
                    text,
                    flags=re.I
                )

                text = re.sub(
                    r"<style[\s\S]*?</style>",
                    " ",
                    text,
                    flags=re.I
                )

                text = re.sub(
                    r"<[^>]+>",
                    " ",
                    text
                )

                text = html.unescape(text)

                text = re.sub(
                    r"\s+",
                    " ",
                    text
                )

                texts.append(text)

            except Exception:
                pass

        return " ".join(texts)

    except Exception:
        return ""


def analyze_8k(symbol):

    filing = get_latest_8k(symbol)

    if not filing:
        return 50, "-", "⚪ 8-K yok"

    text = get_8k_text(
        filing["CIK"],
        filing["Accession"]
    )

    low = text.lower()

    score = 50
    reasons = []


    # POZİTİF
    positive = [
        ("raises guidance", 10),
        ("raised guidance", 10),
        ("increased guidance", 8),
        ("record revenue", 8),
        ("record quarterly revenue", 8),
        ("exceeded expectations", 8),
        ("above expectations", 6),
        ("strategic partnership", 5),
        ("contract award", 6),
        ("awarded a contract", 6)
    ]

    for phrase, points in positive:

        if phrase in low:
            score += points
            reasons.append(phrase)


    # NEGATİF
    # NOT: "default" KASITLI OLARAK BURADA YOK.
    negative = [
        ("lowers guidance", -10),
        ("lowered guidance", -10),
        ("reduced guidance", -8),
        ("missed expectations", -8),
        ("below expectations", -6),
        ("going concern", -10),
        ("bankruptcy", -15),
        ("cybersecurity incident", -12)
    ]

    for phrase, points in negative:

        if phrase in low:
            score += points
            reasons.append(phrase)


    if re.search(
        r"item\s+1\.05",
        low
    ):
        score -= 12
        reasons.append("Item 1.05 cyber")


    if re.search(
        r"item\s+2\.02",
        low
    ):
        reasons.append("Item 2.02 bilanço")


    score = max(
        0,
        min(100, round(score))
    )

    if score >= 70:
        signal = "🟢 Güçlü pozitif"

    elif score >= 58:
        signal = "🟢 Pozitif"

    elif score >= 43:
        signal = "⚪ Nötr"

    elif score >= 30:
        signal = "🟠 Negatif"

    else:
        signal = "🔴 Güçlü negatif"


    reason = (
        " | ".join(dict.fromkeys(reasons))
        if reasons
        else "Belirgin yönlü 8-K sinyali yok"
    )

    return score, filing["Tarih"], signal + " — " + reason


# =========================================================
# FINNHUB GÜNCEL HABER
# =========================================================

@st.cache_data(ttl=900)
def get_company_news(symbol):

    if not API_KEY:
        return []

    try:

        today = datetime.now().date()

        start = today - timedelta(days=4)

        url = (
            "https://finnhub.io/api/v1/company-news"
            f"?symbol={symbol}"
            f"&from={start.isoformat()}"
            f"&to={today.isoformat()}"
            f"&token={API_KEY}"
        )

        r = requests.get(
            url,
            timeout=20
        )

        r.raise_for_status()

        return r.json()[:20]

    except Exception:
        return []


def analyze_news(symbol):

    news = get_company_news(symbol)

    if not news:
        return 50, "Haber bulunamadı"


    score = 50
    reasons = []


    positive_words = [
        "beats",
        "beat expectations",
        "raises guidance",
        "upgrade",
        "price target raised",
        "partnership",
        "contract",
        "award",
        "record revenue",
        "launch",
        "approval"
    ]


    negative_words = [
        "misses",
        "missed expectations",
        "downgrade",
        "price target cut",
        "cuts guidance",
        "lowers guidance",
        "investigation",
        "lawsuit",
        "breach",
        "cyberattack"
    ]


    for article in news[:10]:

        headline = str(
            article.get("headline", "")
        ).lower()


        for word in positive_words:

            if word in headline:

                score += 4

                reasons.append(
                    "🟢 " +
                    article.get(
                        "headline",
                        ""
                    )[:70]
                )

                break


        for word in negative_words:

            if word in headline:

                score -= 5

                reasons.append(
                    "🔴 " +
                    article.get(
                        "headline",
                        ""
                    )[:70]
                )

                break


    score = max(
        0,
        min(100, round(score))
    )


    if reasons:

        summary = " | ".join(
            reasons[:2]
        )

    else:

        summary = "Son haberlerde güçlü yönlü başlık yok"


    return score, summary


# =========================================================
# BİLANÇO TAKVİMİ / BEKLENTİ / SÜRPRİZ
# =========================================================

@st.cache_data(ttl=1800)
def get_earnings_calendar(symbol):
    """Finnhub bilanço takvimini döndürür; anahtar/veri yoksa boş liste."""
    if not API_KEY:
        return []

    try:
        today = datetime.now().date()
        params = {
            "symbol": symbol,
            "from": (today - timedelta(days=370)).isoformat(),
            "to": (today + timedelta(days=120)).isoformat(),
            "token": API_KEY,
        }
        response = requests.get(
            "https://finnhub.io/api/v1/calendar/earnings",
            params=params,
            timeout=20,
        )
        response.raise_for_status()
        return response.json().get("earningsCalendar", [])
    except Exception:
        return []


def _surprise_pct(actual, estimate):
    try:
        actual = float(actual)
        estimate = float(estimate)
        if estimate == 0:
            return None
        return (actual - estimate) / abs(estimate) * 100
    except (TypeError, ValueError):
        return None


def analyze_earnings(symbol):
    events = get_earnings_calendar(symbol)
    today = datetime.now().date()
    upcoming = []
    completed = []

    for event in events:
        try:
            event_date = datetime.strptime(event.get("date", ""), "%Y-%m-%d").date()
        except (TypeError, ValueError):
            continue

        if event_date >= today:
            upcoming.append((event_date, event))
        elif event.get("epsActual") is not None or event.get("revenueActual") is not None:
            completed.append((event_date, event))

    upcoming.sort(key=lambda item: item[0])
    completed.sort(key=lambda item: item[0], reverse=True)

    score = 50
    notes = []
    next_date = "—"
    days_left = None

    if upcoming:
        event_date, event = upcoming[0]
        next_date = event_date.isoformat()
        days_left = (event_date - today).days
        eps_estimate = event.get("epsEstimate")
        revenue_estimate = event.get("revenueEstimate")
        if eps_estimate is not None:
            notes.append(f"EPS beklenti {eps_estimate}")
        if revenue_estimate is not None:
            try:
                notes.append(f"Ciro beklenti ${float(revenue_estimate) / 1_000_000:.1f}M")
            except (TypeError, ValueError):
                pass
        if days_left <= 7:
            notes.append(f"{days_left} gün kaldı: yüksek oynaklık riski")

    eps_surprise = None
    revenue_surprise = None
    if completed:
        _, latest = completed[0]
        eps_surprise = _surprise_pct(latest.get("epsActual"), latest.get("epsEstimate"))
        revenue_surprise = _surprise_pct(
            latest.get("revenueActual"), latest.get("revenueEstimate")
        )

        if eps_surprise is not None:
            score += max(-15, min(15, eps_surprise * 0.75))
            notes.append(f"Son EPS sürprizi %{eps_surprise:+.1f}")
        if revenue_surprise is not None:
            score += max(-10, min(10, revenue_surprise * 0.5))
            notes.append(f"Son ciro sürprizi %{revenue_surprise:+.1f}")

    score = int(round(max(0, min(100, score))))
    if score >= 60:
        signal = "🟢 POZİTİF"
    elif score <= 40:
        signal = "🟠 NEGATİF"
    else:
        signal = "⚪ NÖTR"

    if not events:
        notes.append("Bilanço takvimi verisi yok")

    return {
        "Puan": score,
        "Sonraki Bilanço": next_date,
        "Kalan Gün": days_left if days_left is not None else "—",
        "EPS Sürpriz %": round(eps_surprise, 1) if eps_surprise is not None else "—",
        "Ciro Sürpriz %": round(revenue_surprise, 1) if revenue_surprise is not None else "—",
        "Sinyal": signal,
        "Açıklama": " | ".join(notes) if notes else "Beklenti/sürpriz verisi yok",
    }


# =========================================================
# FINAL MOTOR
# =========================================================

final_rows = []

detail_rows = []


for symbol in SYMBOLS:

    try:

        tech = analyze_technical(symbol)

        sec = analyze_sec_xbrl(symbol)

        insider_score, insider_text = (
            final_insider(symbol)
        )

        sec8_score, sec8_date, sec8_text = (
            analyze_8k(symbol)
        )

        news_score, news_text = (
            analyze_news(symbol)
        )

        earnings = analyze_earnings(symbol)
        earnings_score = float(earnings.get("Puan", 50))


        tech_score = float(
            tech.get("Teknik Puan", 50)
        )

        sec_score = float(
            sec.get("SEC Finansal Puan", 50)
        )


        # 8-K + haber birlikte katalizör
        catalyst_score = round(
            sec8_score * 0.55
            +
            news_score * 0.45
        )


        # FINAL:
        # Teknik %35
        # SEC %25
        # Insider %15
        # Katalizör %15
        # Bilanço %10

        total = round(
            tech_score * 0.35
            +
            sec_score * 0.25
            +
            insider_score * 0.15
            +
            catalyst_score * 0.15
            +
            earnings_score * 0.10
        )


        if total >= 80:
            karar = "🟢 ÇOK GÜÇLÜ"

        elif total >= 70:
            karar = "🟢 GÜÇLÜ"

        elif total >= 60:
            karar = "🟢 POZİTİF"

        elif total >= 50:
            karar = "🟡 İZLE"

        elif total >= 40:
            karar = "🟠 TEMKİNLİ"

        else:
            karar = "🔴 ZAYIF"


        final_rows.append({

            "Hisse": symbol,

            "Fiyat": tech.get("Fiyat") if tech.get("Fiyat") is not None else "—",

            "Teknik": round(
                tech_score
            ),

            "SEC": round(
                sec_score
            ),

            "Insider": insider_score,

            "Katalizör": catalyst_score,

            "Bilanço": round(earnings_score),

            "FINAL": total,

            "Karar": karar
        })


        detail_rows.append({

            "Hisse": symbol,

            "Son 8-K": sec8_date,

            "8-K Puan": sec8_score,

            "Haber Puan": news_score,

            "Insider": insider_text,

            "8-K": sec8_text,

            "Haber": news_text,

            "Sonraki Bilanço": earnings.get("Sonraki Bilanço", "—"),

            "Bilanço": earnings.get("Açıklama", "Veri yok")
        })


    except Exception as e:

        final_rows.append({

            "Hisse": symbol,

            "Fiyat": "—",

            "Teknik": "—",

            "SEC": "—",

            "Insider": "—",

            "Katalizör": "—",

            "Bilanço": "—",

            "FINAL": None,

            "Karar":
            f"⚠️ {type(e).__name__}"
        })


# =========================================================
# TEK ANA TABLO
# =========================================================

final_df = pd.DataFrame(
    final_rows
)

final_df = final_df.sort_values(
    "FINAL",
    ascending=False
)


st.subheader(
    "🏆 FINAL Yatırım Sıralaması"
)

st.dataframe(
    final_df.fillna("—"),
    width="stretch",
    hide_index=True
)


st.subheader(
    "🧠 Katalizör Açıklamaları"
)

st.dataframe(
    pd.DataFrame(detail_rows),
    width="stretch",
    hide_index=True
)


st.info(
    "FINAL = %35 Teknik + %25 SEC finansal + "
    "%15 insider + %15 katalizör + %10 bilanço. "
    "Katalizör puanı SEC 8-K ve son Finnhub haberlerini birlikte kullanır. "
    "'default' kelimesi artık negatif katalizör olarak değerlendirilmez."
)


st.subheader("📅 Bilanço Beklentisi & Sürpriz Radarı")

earnings_rows = []
for symbol in SYMBOLS:
    result = analyze_earnings(symbol)
    earnings_rows.append({"Hisse": symbol, **result})

st.dataframe(
    pd.DataFrame(earnings_rows),
    width="stretch",
    hide_index=True,
)

st.caption(
    "Yaklaşan bilanço tarihi ve beklentiler ile son açıklanan EPS/ciro "
    "sürprizleri gösterilir. Bilanço puanı tek başına alım-satım sinyali değildir."
)


if st.button("🔄 FINAL Verileri Yenile", key="final_refresh"):

    st.cache_data.clear()

    st.rerun()
# =========================================================
# GELİŞMİŞ HABER / KATALİZÖR RADARI
# =========================================================

st.divider()
st.header("🛰️ Güncel Haber & Katalizör Radarı")

def smart_news_analysis(symbol):
    news = get_company_news(symbol)

    if not news:
        return {
            "Hisse": symbol,
            "Haber": "Haber bulunamadı",
            "Puan": 50,
            "Sinyal": "⚪ NÖTR"
        }

    positive = {
        "raises guidance": 15,
        "raised guidance": 15,
        "beats estimates": 12,
        "beat estimates": 12,
        "record revenue": 10,
        "record earnings": 10,
        "contract awarded": 12,
        "wins contract": 12,
        "strategic partnership": 8,
        "partnership": 5,
        "collaboration": 5,
        "price target raised": 8,
        "upgrade": 8,
        "buy rating": 6,
        "approval": 10,
        "acquisition": 5,
        "expansion": 5
    }

    negative = {
        "cuts guidance": -15,
        "lowers guidance": -15,
        "misses estimates": -12,
        "missed estimates": -12,
        "downgrade": -8,
        "price target cut": -8,
        "investigation": -8,
        "lawsuit": -7,
        "data breach": -15,
        "cyberattack": -15,
        "layoffs": -5
    }

    best_score = 50
    best_headline = ""
    best_time = 0

    for article in news[:20]:
        headline = str(article.get("headline", ""))
        summary = str(article.get("summary", ""))

        text = headline.lower()

        score = 50

        for phrase, points in positive.items():
            if phrase in text:
                score += points

        for phrase, points in negative.items():
            if phrase in text:
                score += points

        score = max(0, min(100, score))

        article_time = article.get("datetime", 0) or 0

        # En güçlü yönlü katalizörü seç
        if abs(score - 50) > abs(best_score - 50):
            best_score = score
            best_headline = headline
            best_time = article_time

    if best_score >= 70:
        signal = "🟢 GÜÇLÜ POZİTİF"
    elif best_score >= 56:
        signal = "🟢 POZİTİF"
    elif best_score <= 30:
        signal = "🔴 GÜÇLÜ NEGATİF"
    elif best_score <= 44:
        signal = "🟠 NEGATİF"
    else:
        signal = "⚪ NÖTR"

    if not best_headline and news:
        best_headline = str(news[0].get("headline", ""))

    if best_time:
        try:
            tarih = datetime.fromtimestamp(best_time).strftime("%Y-%m-%d %H:%M")
        except Exception:
            tarih = "-"
    else:
        tarih = "-"

    return {
        "Hisse": symbol,
        "Tarih": tarih,
        "Haber": best_headline[:120],
        "Puan": best_score,
        "Sinyal": signal
    }


news_radar = []

for symbol in SYMBOLS:
    news_radar.append(
        smart_news_analysis(symbol)
    )

news_df = pd.DataFrame(news_radar)

news_df = news_df.sort_values(
    "Puan",
    ascending=False
)

st.dataframe(
    news_df,
    width="stretch",
    hide_index=True
)

st.caption(
    "Bu radar Finnhub şirket haberlerinin başlık ve özetlerini tarar. "
    "Bilanço sürprizi, guidance, kontrat, ortaklık, analist değişikliği, "
    "onay, dava ve siber olayları yönlü katalizör olarak sınıflandırır."
)
# =========================================================
# ŞİRKETLE İLGİLİ HABER FİLTRESİ
# =========================================================

COMPANY_NAMES = {
    "NTSK": ["netskope", "ntsk"],
    "NVDA": ["nvidia", "nvda"],
    "CRWD": ["crowdstrike", "crwd"],
    "ALAB": ["astera labs", "astera", "alab"],
}

def filtered_company_news(symbol):
    raw = get_company_news(symbol)

    names = COMPANY_NAMES.get(symbol, [symbol.lower()])
    result = []

    for article in raw[:30]:
        headline = str(article.get("headline", ""))
        summary = str(article.get("summary", ""))

        text = headline.lower()

        # Şirket adı/ticker metinde yoksa haberi alma
        if not any(name in text for name in names):
            continue

        article["_company_relevant"] = True
        result.append(article)

    return result


st.divider()
st.header("🎯 Şirkete Özel Haber Radarı")

filtered_radar = []

for symbol in SYMBOLS:
    news = filtered_company_news(symbol)

    if not news:
        filtered_radar.append({
            "Hisse": symbol,
            "Haber": "Şirketle doğrudan ilişkili yeni haber yok",
            "Puan": 50,
            "Sinyal": "⚪ NÖTR"
        })
        continue

    best = news[0]

    headline = str(best.get("headline", ""))
    summary = str(best.get("summary", ""))

    text = headline.lower()

    score = 50

    positive_words = [
        "raises guidance",
        "raised guidance",
        "beats estimates",
        "beat estimates",
        "record revenue",
        "record earnings",
        "contract",
        "partnership",
        "strategic partnership",
        "collaboration",
        "upgrade",
        "price target raised",
        "approval",
        "acquisition",
        "expansion"
    ]

    negative_words = [
        "cuts guidance",
        "lowers guidance",
        "misses estimates",
        "missed estimates",
        "downgrade",
        "price target cut",
        "investigation",
        "lawsuit",
        "data breach",
        "cyberattack",
        "layoffs"
    ]

    for word in positive_words:
        if word in text:
            score += 8

    for word in negative_words:
        if word in text:
            score -= 10

    score = max(0, min(100, score))

    if score >= 70:
        signal = "🟢 GÜÇLÜ POZİTİF"
    elif score >= 56:
        signal = "🟢 POZİTİF"
    elif score <= 30:
        signal = "🔴 GÜÇLÜ NEGATİF"
    elif score <= 44:
        signal = "🟠 NEGATİF"
    else:
        signal = "⚪ NÖTR"

    filtered_radar.append({
        "Hisse": symbol,
        "Haber": headline[:140],
        "Puan": score,
        "Sinyal": signal
    })

filtered_df = pd.DataFrame(filtered_radar)

st.dataframe(
    filtered_df,
    width="stretch",
    hide_index=True
)

st.caption(
    "Yalnızca ticker veya şirket adı doğrudan geçen haberler değerlendirmeye alınır."
)
# =========================================================
# 20 HİSSELİK HIZLI TARAYICI
# =========================================================

st.divider()
st.header("⚡ Hızlı Hisse Tarayıcı")

from watchlist import WATCHLIST, PRIORITY_SYMBOLS, get_watchlist

full_scan = st.checkbox(
    f"{len(WATCHLIST)} hissenin tamamını tara (daha uzun sürer)",
    value=False,
    help="Kapalıyken öncelikli hisseler dahil ilk 20 hisse taranır.",
)

quick_watchlist = list(dict.fromkeys(PRIORITY_SYMBOLS + WATCHLIST))[:20]
FAST_SYMBOLS = WATCHLIST if full_scan else quick_watchlist

st.caption(
    f"Bu çalıştırmada {len(FAST_SYMBOLS)} hisse taranıyor. "
    "Hızlı açılış için varsayılan 20 hissedir."
)
fast_rows = []

for symbol in FAST_SYMBOLS:
    try:
        q = get_quote(symbol)

        price = q.get("c", 0)
        change_pct = q.get("dp", 0)

        # Basit hızlı momentum puanı
        momentum_score = 50

        if change_pct >= 5:
            momentum_score += 15
        elif change_pct >= 2:
            momentum_score += 8
        elif change_pct <= -5:
            momentum_score -= 15
        elif change_pct <= -2:
            momentum_score -= 8

        # Şirkete özel haber kontrolü
        company_news = filtered_company_news(symbol)

        news_score = 50
        news_headline = "Yeni doğrudan haber yok"

        if company_news:
            article = company_news[0]
            news_headline = str(article.get("headline", ""))

            text = news_headline.lower()

            positive_words = [
                "raises guidance",
                "beats estimates",
                "record revenue",
                "contract",
                "partnership",
                "upgrade",
                "price target raised",
                "approval"
            ]

            negative_words = [
                "cuts guidance",
                "misses estimates",
                "downgrade",
                "price target cut",
                "investigation",
                "lawsuit",
                "data breach",
                "cyberattack"
            ]

            for word in positive_words:
                if word in text:
                    news_score += 8

            for word in negative_words:
                if word in text:
                    news_score -= 10

        news_score = max(0, min(100, news_score))

        fast_score = round(
            momentum_score * 0.55 +
            news_score * 0.45
        )

        if fast_score >= 70:
            signal = "🟢 GÜÇLÜ ADAY"
        elif fast_score >= 60:
            signal = "🟢 POZİTİF"
        elif fast_score >= 50:
            signal = "🟡 İZLE"
        elif fast_score >= 40:
            signal = "🟠 TEMKİNLİ"
        else:
            signal = "🔴 ZAYIF"

        fast_rows.append({
            "Hisse": symbol,
            "Fiyat": round(price, 2),
            "Günlük %": round(change_pct, 2),
            "Momentum": momentum_score,
            "Haber": news_score,
            "Hızlı Puan": fast_score,
            "Sinyal": signal,
            "Son Haber": news_headline[:90]
        })

    except Exception as e:
        fast_rows.append({
            "Hisse": symbol,
            "Fiyat": None,
            "Günlük %": None,
            "Momentum": 50,
            "Haber": 50,
            "Hızlı Puan": 50,
            "Sinyal": "⚪ VERİ HATASI",
            "Son Haber": str(e)[:90]
        })

fast_df = pd.DataFrame(fast_rows)

fast_df = fast_df.sort_values(
    "Hızlı Puan",
    ascending=False
)

st.dataframe(
    fast_df,
    width="stretch",
    hide_index=True
)

st.caption(
    "Bu bölüm hızlı ön eleme yapar. En yüksek puanlı hisseler daha sonra SEC, "
    "Form 4, 8-K ve teknik analiz motorunda derin incelemeye alınır."
)
# =========================================================
# TOP 5 OTOMATİK ADAY SEÇİM MOTORU
# =========================================================

st.divider()
st.header("🚀 TOP 5 — TAM DERİN FINAL")

def safe_number(value, default=50):
    try:
        if value is None:
            return float(default)
        return float(value)
    except:
        return float(default)


def filtered_news_score(symbol):
    try:
        articles = filtered_company_news(symbol)
    except:
        return 50, "Doğrudan şirket haberi bulunamadı"

    if not articles:
        return 50, "Doğrudan şirket haberi bulunamadı"

    positive = {
        "raises guidance": 15,
        "raised guidance": 15,
        "beats estimates": 12,
        "beat estimates": 12,
        "record revenue": 10,
        "record earnings": 10,
        "wins contract": 12,
        "contract awarded": 12,
        "strategic partnership": 10,
        "price target raised": 8,
        "upgraded": 8,
        "upgrade": 8,
        "approval": 10
    }

    negative = {
        "cuts guidance": -15,
        "lowers guidance": -15,
        "misses estimates": -12,
        "missed estimates": -12,
        "downgraded": -8,
        "downgrade": -8,
        "price target cut": -8,
        "investigation": -10,
        "lawsuit": -8,
        "data breach": -15,
        "cyberattack": -15
    }

    best_score = 50
    best_headline = ""

    for article in articles[:10]:
        headline = str(article.get("headline", ""))
        text = headline.lower()

        score = 50

        for phrase, points in positive.items():
            if phrase in text:
                score += points

        for phrase, points in negative.items():
            if phrase in text:
                score += points

        score = max(0, min(100, score))

        if abs(score - 50) > abs(best_score - 50):
            best_score = score
            best_headline = headline

    if not best_headline:
        best_headline = str(articles[0].get("headline", ""))

    return best_score, best_headline


top5_df = (
    fast_df[fast_df["Hisse"] != "NTSK"]
    .sort_values("Hızlı Puan", ascending=False)
    .head(5)
    .copy()
)

deep_final_rows = []

for _, row in top5_df.iterrows():

    symbol = row["Hisse"]

    # -----------------------------
    # GERÇEK TEKNİK ANALİZ
    # -----------------------------
    try:
        tech = analyze_technical(symbol)
        tech_score = safe_number(
            tech.get("Teknik Puan", 50)
        )
    except Exception:
        tech_score = 50

    # -----------------------------
    # GERÇEK SEC / XBRL ANALİZİ
    # -----------------------------
    try:
        sec = analyze_sec_xbrl(symbol)
        sec_score = safe_number(
            sec.get("SEC Finansal Puan", 50)
        )
    except Exception:
        sec_score = 50

    # -----------------------------
    # GERÇEK FORM 4 / INSIDER
    # -----------------------------
    try:
        insider = smart_insider_score(symbol)

        if isinstance(insider, dict):
            insider_score = safe_number(
                insider.get("Akıllı Insider Puan", 50)
            )
        else:
            insider_score = safe_number(insider)

    except Exception:
        insider_score = 50

    # -----------------------------
    # GERÇEK 8-K KATALİZÖRÜ
    # -----------------------------
    try:
        k8_result = analyze_8k(symbol)

        if isinstance(k8_result, tuple):
            k8_score = safe_number(k8_result[0])
            k8_reason = str(k8_result[1])
        elif isinstance(k8_result, dict):
            k8_score = safe_number(
                k8_result.get("Puan", 50)
            )
            k8_reason = str(
                k8_result.get("Neden", "")
            )
        else:
            k8_score = safe_number(k8_result)
            k8_reason = ""

    except Exception:
        k8_score = 50
        k8_reason = "Yeni güçlü 8-K sinyali yok"

    # -----------------------------
    # ŞİRKETE ÖZEL HABER
    # -----------------------------
    news_score, headline = filtered_news_score(symbol)

    # 8-K + HABER
    catalyst_score = round(
        k8_score * 0.55 +
        news_score * 0.45
    )

    # -----------------------------
    # GERÇEK FINAL PUAN
    # -----------------------------
    final_score = round(
        tech_score * 0.35 +
        sec_score * 0.25 +
        insider_score * 0.15 +
        catalyst_score * 0.25
    )

    if final_score >= 80:
        decision = "🟢 ÇOK GÜÇLÜ ADAY"
    elif final_score >= 70:
        decision = "🟢 GÜÇLÜ ADAY"
    elif final_score >= 60:
        decision = "🟡 POZİTİF / İZLE"
    elif final_score >= 50:
        decision = "🟠 TEMKİNLİ"
    else:
        decision = "🔴 ZAYIF / BEKLE"

    deep_final_rows.append({
        "Hisse": symbol,
        "Fiyat": row.get("Fiyat"),
        "Teknik": round(tech_score),
        "SEC": round(sec_score),
        "Insider": round(insider_score),
        "8-K": round(k8_score),
        "Haber": round(news_score),
        "Katalizör": catalyst_score,
        "FINAL": final_score,
        "Karar": decision,
        "Önemli Haber": headline[:80]
    })


deep_final_df = pd.DataFrame(deep_final_rows)

deep_final_df = deep_final_df.sort_values(
    "FINAL",
    ascending=False
).reset_index(drop=True)

deep_final_df.insert(
    0,
    "Sıra",
    range(1, len(deep_final_df) + 1)
)

st.dataframe(
    deep_final_df,
    width="stretch",
    hide_index=True
)

if not deep_final_df.empty:
    leader = deep_final_df.iloc[0]

    st.success(
        f"🥇 Derin analiz lideri: "
        f"{leader['Hisse']} — "
        f"{leader['FINAL']}/100 — "
        f"{leader['Karar']}"
    )

st.caption(
    "Bu tabloda TOP 5 hisseler için teknik analiz, SEC/XBRL finansalları, "
    "Form 4 insider, SEC 8-K ve şirkete özel haber motorları yeniden ve "
    "doğrudan çalıştırılır."
)

# ===== TELEGRAM TOP 5 OTOMATIK GONDERIM =====
def telegram_top5_gonder(df):
    import os, requests
    from dotenv import load_dotenv
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id or df.empty:
        return

    mesaj = "🚀 BORSA ROBOTU — TOP 5\n\n"
    for _, r in df.head(5).iterrows():
        mesaj += f"{int(r['Sıra'])}. {r['Hisse']} — {r['FINAL']}/100 — {r['Karar']}\n"
    mesaj += f"\n📊 {len(FAST_SYMBOLS)} hisse taranarak oluşturuldu."

    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": mesaj},
        timeout=15
    )

ntsk_context = {}
ntsk_final_match = final_df[final_df["Hisse"] == "NTSK"]
if not ntsk_final_match.empty:
    ntsk_final = ntsk_final_match.iloc[0]
    for key in ["Fiyat", "Teknik", "SEC", "Insider", "Katalizör", "Bilanço", "FINAL", "Karar"]:
        ntsk_context[key] = ntsk_final.get(key, "—")

ntsk_detail_frame = pd.DataFrame(detail_rows)
if not ntsk_detail_frame.empty:
    ntsk_detail_match = ntsk_detail_frame[ntsk_detail_frame["Hisse"] == "NTSK"]
    if not ntsk_detail_match.empty:
        ntsk_detail = ntsk_detail_match.iloc[0]
        for key in ["Son 8-K", "8-K", "Haber", "Sonraki Bilanço"]:
            ntsk_context[key] = ntsk_detail.get(key, "—")


@st.fragment(run_every="30m")
def opportunity_radar_fragment():
    render_opportunity_scanner(get_watchlist(), ntsk_context=ntsk_context)


opportunity_radar_fragment()


render_extras(
    FAST_SYMBOLS,
    deep_final_df,
    api_key_present=bool(API_KEY),
)
# ============================================
