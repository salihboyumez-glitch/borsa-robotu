from app_form4_working import *

import re
import xml.etree.ElementTree as ET
import pandas as pd
import streamlit as st


def safe_text(node, path):
    try:
        x = node.find(path)
        if x is not None and x.text:
            return x.text.strip()
    except Exception:
        pass
    return None


def form4_context(symbol):

    result = {
        "Hisse": symbol,
        "Insider": "-",
        "Görev": "-",
        "10b5-1": "BULUNMADI",
        "İşlem Sonrası Hisse": None,
        "Footnote / Açıklama": "-"
    }

    try:
        filing = latest_form4(symbol)

        if not filing:
            return result

        raw = get_raw_form4_xml(
            filing["CIK"],
            filing["Accession"]
        )

        if not raw:
            result["Footnote / Açıklama"] = "Ham XML alınamadı"
            return result

        root = ET.fromstring(raw)
        root = clean_namespace(root)

        owner = safe_text(
            root,
            ".//reportingOwnerId/rptOwnerName"
        )

        if owner:
            result["Insider"] = owner


        # Insider görevini bul
        relationship = root.find(
            ".//reportingOwnerRelationship"
        )

        roles = []

        if relationship is not None:

            is_director = safe_text(
                relationship,
                "isDirector"
            )

            is_officer = safe_text(
                relationship,
                "isOfficer"
            )

            is_ten = safe_text(
                relationship,
                "isTenPercentOwner"
            )

            officer_title = safe_text(
                relationship,
                "officerTitle"
            )

            if is_director == "1":
                roles.append("Director")

            if is_officer == "1":
                if officer_title:
                    roles.append(officer_title)
                else:
                    roles.append("Officer")

            if is_ten == "1":
                roles.append("%10+ Hissedar")

        if roles:
            result["Görev"] = ", ".join(roles)


        # Footnote metinleri
        footnotes = []

        for footnote in root.findall(".//footnote"):
            text = "".join(
                footnote.itertext()
            ).strip()

            if text:
                footnotes.append(text)

        full_notes = " ".join(footnotes)


        # SEC XML'deki olası 10b5-1 alanlarını da kontrol et
        tag_10b5 = False

        for element in root.iter():

            tag = str(element.tag).lower()

            if "10b5" in tag:

                value = (
                    element.text.strip()
                    if element.text
                    else ""
                )

                if value.lower() in [
                    "1",
                    "true",
                    "yes",
                    "y"
                ]:
                    tag_10b5 = True


        if (
            re.search(
                r"10b5[\-\s]?1",
                full_notes,
                flags=re.I
            )
            or tag_10b5
        ):

            result["10b5-1"] = "EVET ⚪"


        # Açık piyasa işleminden sonra kalan hisse
        transactions = root.findall(
            ".//nonDerivativeTransaction"
        )

        for tx in transactions:

            code = safe_text(
                tx,
                "./transactionCoding/transactionCode"
            )

            if code in ["P", "S"]:

                remaining = safe_text(
                    tx,
                    "./postTransactionAmounts/"
                    "sharesOwnedFollowingTransaction/value"
                )

                if remaining:

                    try:
                        result[
                            "İşlem Sonrası Hisse"
                        ] = round(float(remaining))
                    except Exception:
                        pass


        # Açıklamayı kısa tut
        if full_notes:

            clean_note = re.sub(
                r"\s+",
                " ",
                full_notes
            ).strip()

            if len(clean_note) > 260:
                clean_note = clean_note[:260] + "..."

            result[
                "Footnote / Açıklama"
            ] = clean_note

        else:

            result[
                "Footnote / Açıklama"
            ] = "Footnote yok"


        return result

    except Exception as e:

        result[
            "Footnote / Açıklama"
        ] = f"Okuma hatası: {type(e).__name__}"

        return result


context_rows = [
    form4_context(symbol)
    for symbol in SYMBOLS
]


st.subheader("🔎 Insider İşlem Bağlamı")

st.dataframe(
    pd.DataFrame(context_rows),
    width="stretch",
    hide_index=True
)

st.caption(
    "10b5-1 = önceden oluşturulmuş işlem planı göstergesi. "
    "Özellikle insider satışlarında sinyalin yorumunu değiştirebilir."
)
