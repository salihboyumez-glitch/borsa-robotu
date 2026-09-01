from app_insider_context_working import *

import re
import pandas as pd
import streamlit as st


def smart_insider_score(symbol):

    # Önce mevcut çalışan Form 4 sonucunu al
    base = parse_form4(symbol)

    # Bağlam bilgisini al
    ctx = form4_context(symbol)

    işlem = str(base.get("İşlem", ""))
    value = base.get("Yaklaşık $")
    note = str(ctx.get("Footnote / Açıklama", ""))
    plan = str(ctx.get("10b5-1", ""))

    try:
        value = float(value) if value is not None else 0
    except Exception:
        value = 0

    note_lower = note.lower()

    result = {
        "Hisse": symbol,
        "Insider": base.get("Insider", "-"),
        "İşlem": işlem,
        "10b5-1": plan,
        "Yaklaşık $": value if value else None,
        "Akıllı Insider Puan": 50,
        "Yorum": "⚪ NÖTR"
    }


    # ----------------------------------
    # AÇIK PİYASA ALIŞ
    # ----------------------------------

    if "ALIŞ" in işlem:

        score = 70

        if value >= 1_000_000:
            score = 85

        elif value >= 250_000:
            score = 78

        # 10b5-1 planlı alış ise biraz azalt
        if "EVET" in plan:
            score -= 8

        result["Akıllı Insider Puan"] = score

        if score >= 80:
            result["Yorum"] = "🟢 GÜÇLÜ INSIDER ALIŞ"

        else:
            result["Yorum"] = "🟢 POZİTİF INSIDER ALIŞ"

        return result


    # ----------------------------------
    # AÇIK PİYASA SATIŞ
    # ----------------------------------

    if "SATIŞ" in işlem:

        # Normal satış
        score = 40
        yorum = "🔴 INSIDER SATIŞ"

        if value >= 1_000_000:
            score = 35

        if value >= 5_000_000:
            score = 30


        # ----------------------------------
        # 10b5-1 PLANLI SATIŞ
        # ----------------------------------

        if "EVET" in plan:

            score = 47
            yorum = "⚪ 10b5-1 PLANLI SATIŞ"


        # ----------------------------------
        # VERGİ AMAÇLI SATIŞ
        # ----------------------------------

        tax_words = [
            "tax",
            "withholding",
            "withhold",
            "tax obligation",
            "tax liability",
            "satisfy tax",
            "taxes"
        ]

        tax_sale = any(
            word in note_lower
            for word in tax_words
        )

        if tax_sale:

            score = 50
            yorum = "⚪ VERGİ AMAÇLI SATIŞ"


        result["Akıllı Insider Puan"] = score
        result["Yorum"] = yorum

        return result


    # ----------------------------------
    # DİĞER FORM 4 İŞLEMLERİ
    # ----------------------------------

    result["Akıllı Insider Puan"] = 50
    result["Yorum"] = "⚪ YÖNSÜZ / DİĞER"

    return result


smart_rows = [
    smart_insider_score(symbol)
    for symbol in SYMBOLS
]


st.subheader("🧠 Akıllı Insider Değerlendirmesi")

smart_df = pd.DataFrame(smart_rows)

st.dataframe(
    smart_df,
    width="stretch",
    hide_index=True
)


# ==========================================
# YENİ BİRLEŞİK PUAN
# ==========================================

st.subheader("🏆 Geliştirilmiş Birleşik Yatırım Puanı")


new_scores = []


for symbol in SYMBOLS:

    try:

        tech = analyze_technical(symbol)
        sec = analyze_sec_xbrl(symbol)
        insider = smart_insider_score(symbol)

        tech_score = float(
            tech.get("Teknik Puan", 50)
        )

        sec_score = float(
            sec.get("SEC Finansal Puan", 50)
        )

        insider_score = float(
            insider.get(
                "Akıllı Insider Puan",
                50
            )
        )


        # AĞIRLIKLAR
        #
        # Teknik       %50
        # SEC Finansal %35
        # Insider      %15

        total = round(
            tech_score * 0.50
            +
            sec_score * 0.35
            +
            insider_score * 0.15
        )


        if total >= 75:

            decision = "🟢 GÜÇLÜ"

        elif total >= 65:

            decision = "🟢 POZİTİF"

        elif total >= 55:

            decision = "🟡 İZLE"

        elif total >= 45:

            decision = "🟠 TEMKİNLİ"

        else:

            decision = "🔴 ZAYIF"


        new_scores.append({

            "Hisse": symbol,

            "Teknik": round(
                tech_score
            ),

            "SEC Finansal": round(
                sec_score
            ),

            "Insider": round(
                insider_score
            ),

            "Toplam": total,

            "Karar": decision
        })


    except Exception as e:

        new_scores.append({

            "Hisse": symbol,

            "Teknik": None,

            "SEC Finansal": None,

            "Insider": None,

            "Toplam": None,

            "Karar":
            f"⚠️ {type(e).__name__}"
        })


new_score_df = pd.DataFrame(new_scores)


st.dataframe(
    new_score_df,
    width="stretch",
    hide_index=True
)


st.caption(
    "Yeni puan: %50 teknik + %35 SEC finansal + "
    "%15 akıllı insider. 10b5-1 planlı ve vergi amaçlı "
    "satışlar normal açık piyasa satışından ayrı değerlendirilir."
)
