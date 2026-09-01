from app_xbrl_backup import *

import requests
import pandas as pd
import streamlit as st
import xml.etree.ElementTree as ET


SEC_HEADERS = {
    "User-Agent": "BorsaRobotu/1.0 research-app"
}


@st.cache_data(ttl=1800)
def get_sec_filings(symbol):

    ticker_map = get_sec_ticker_map()

    cik = ticker_map.get(symbol.upper())

    if not cik:
        return []

    try:

        url = f"https://data.sec.gov/submissions/CIK{cik}.json"

        r = requests.get(
            url,
            headers=SEC_HEADERS,
            timeout=20
        )

        r.raise_for_status()

        recent = r.json()["filings"]["recent"]

        filings = []

        for form, date, accession in zip(
            recent["form"],
            recent["filingDate"],
            recent["accessionNumber"]
        ):

            filings.append({
                "Form": form,
                "Tarih": date,
                "Accession": accession,
                "CIK": cik
            })

        return filings

    except Exception:
        return []


def latest_form4(symbol):

    for filing in get_sec_filings(symbol):

        if filing["Form"] == "4":
            return filing

    return None


@st.cache_data(ttl=1800)
def get_raw_form4_xml(cik, accession):

    try:

        cik_num = str(int(cik))

        accession_clean = accession.replace("-", "")

        base_url = (
            "https://www.sec.gov/Archives/edgar/data/"
            f"{cik_num}/{accession_clean}"
        )

        # SEC klasöründeki gerçek dosyaları öğren
        index_url = f"{base_url}/index.json"

        r = requests.get(
            index_url,
            headers=SEC_HEADERS,
            timeout=20
        )

        r.raise_for_status()

        items = (
            r.json()
            .get("directory", {})
            .get("item", [])
        )

        xml_files = []

        for item in items:

            name = item.get("name", "")

            if name.lower().endswith(".xml"):
                xml_files.append(name)

        # Öncelik: ownership.xml
        selected = None

        for name in xml_files:

            if name.lower() == "ownership.xml":
                selected = name
                break

        if not selected and xml_files:
            selected = xml_files[0]

        if not selected:
            return ""

        xml_url = f"{base_url}/{selected}"

        xml_response = requests.get(
            xml_url,
            headers=SEC_HEADERS,
            timeout=20
        )

        xml_response.raise_for_status()

        return xml_response.text

    except Exception:
        return ""


def clean_namespace(root):

    for element in root.iter():

        if "}" in element.tag:
            element.tag = element.tag.split("}", 1)[1]

    return root


def get_text(parent, path):

    node = parent.find(path)

    if node is None or node.text is None:
        return None

    return node.text.strip()


def parse_form4(symbol):

    filing = latest_form4(symbol)

    result = {
        "Hisse": symbol,
        "Form 4 Tarih": "-",
        "Insider": "-",
        "İşlem": "⚪ YOK",
        "Adet": None,
        "Fiyat": None,
        "Yaklaşık $": None,
        "Form 4 Puan": 50
    }

    if not filing:
        return result

    result["Form 4 Tarih"] = filing["Tarih"]

    raw_xml = get_raw_form4_xml(
        filing["CIK"],
        filing["Accession"]
    )

    if not raw_xml:

        result["İşlem"] = "⚠️ HAM XML BULUNAMADI"
        return result

    try:

        root = ET.fromstring(raw_xml)

        root = clean_namespace(root)

    except Exception:

        result["İşlem"] = "⚠️ XML PARSE HATASI"
        return result


    owner = get_text(
        root,
        ".//reportingOwnerId/rptOwnerName"
    )

    if owner:
        result["Insider"] = owner


    purchases = []
    sales = []
    other_codes = []


    for transaction in root.findall(
        ".//nonDerivativeTransaction"
    ):

        code = get_text(
            transaction,
            "./transactionCoding/transactionCode"
        )

        ad_code = get_text(
            transaction,
            "./transactionAmounts/"
            "transactionAcquiredDisposedCode/value"
        )

        shares_text = get_text(
            transaction,
            "./transactionAmounts/"
            "transactionShares/value"
        )

        price_text = get_text(
            transaction,
            "./transactionAmounts/"
            "transactionPricePerShare/value"
        )


        try:
            shares = float(shares_text)
        except Exception:
            shares = 0


        try:
            price = float(price_text)
        except Exception:
            price = 0


        value = shares * price


        if code == "P" and ad_code == "A":

            purchases.append(
                (shares, price, value)
            )

        elif code == "S" and ad_code == "D":

            sales.append(
                (shares, price, value)
            )

        elif code:

            other_codes.append(code)


    if purchases:

        total_shares = sum(x[0] for x in purchases)

        total_value = sum(x[2] for x in purchases)

        avg_price = (
            total_value / total_shares
            if total_shares
            else 0
        )

        score = 70

        if total_value >= 1_000_000:
            score = 85

        elif total_value >= 250_000:
            score = 78


        result.update({
            "İşlem": "🟢 AÇIK PİYASA ALIŞ",
            "Adet": round(total_shares),
            "Fiyat": round(avg_price, 2),
            "Yaklaşık $": round(total_value),
            "Form 4 Puan": score
        })


    elif sales:

        total_shares = sum(x[0] for x in sales)

        total_value = sum(x[2] for x in sales)

        avg_price = (
            total_value / total_shares
            if total_shares
            else 0
        )

        score = 40

        if total_value >= 5_000_000:
            score = 25

        elif total_value >= 1_000_000:
            score = 32


        result.update({
            "İşlem": "🔴 AÇIK PİYASA SATIŞ",
            "Adet": round(total_shares),
            "Fiyat": round(avg_price, 2),
            "Yaklaşık $": round(total_value),
            "Form 4 Puan": score
        })


    elif other_codes:

        codes = ",".join(
            sorted(set(other_codes))
        )

        result["İşlem"] = (
            f"⚪ DİĞER FORM 4 ({codes})"
        )


    else:

        result["İşlem"] = "⚪ İŞLEM BULUNAMADI"


    return result


form4_data = [
    parse_form4(symbol)
    for symbol in SYMBOLS
]


st.subheader("👔 Form 4 Insider İşlemleri — Ham SEC XML")

st.dataframe(
    pd.DataFrame(form4_data),
    width="stretch",
    hide_index=True
)

st.info(
    "Bu bölüm SEC filing klasöründeki ham ownership.xml "
    "dosyasını kullanır. P = açık piyasa alış, "
    "S = açık piyasa satış."
)
