"""Stocktwits mesaj trafiğini fiyat uyarılarına sosyal bağlam olarak ekler."""

from collections import Counter
from datetime import datetime, timedelta, timezone

import requests

import config as cfg


TABAN = "https://api.stocktwits.com/api/2"
YUKSELIS = "Bullish"
DUSUS = "Bearish"


def _istek(yol):
    try:
        cevap = requests.get(
            f"{TABAN}/{yol}",
            headers={"User-Agent": "Mozilla/5.0 (borsa-robotu)"},
            timeout=20,
        )
        if cevap.status_code in (403, 429):
            print(f"Stocktwits erişim/hız sınırı: HTTP {cevap.status_code}")
            return None
        cevap.raise_for_status()
        return cevap.json()
    except Exception as hata:
        print(f"Stocktwits isteği başarısız: {hata}")
        return None


def sembol_akisi(sembol):
    return _istek(f"streams/symbol/{sembol}.json")


def sosyal_ozet(sembol, simdi=None):
    veri = sembol_akisi(sembol)
    if not veri or not veri.get("messages"):
        return None
    simdi = simdi or datetime.now(timezone.utc)
    son_24 = []
    for mesaj in veri["messages"]:
        try:
            tarih = datetime.strptime(mesaj["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
        except Exception:
            continue
        if timedelta(0) <= simdi - tarih <= timedelta(hours=24):
            son_24.append((tarih, mesaj))
    if not son_24:
        return None

    esik = simdi - timedelta(hours=2)
    yeni = [x for x in son_24 if x[0] >= esik]
    eski = [x for x in son_24 if x[0] < esik]
    yeni_hiz = len(yeni) / 2.0
    if eski:
        saat = max((esik - min(x[0] for x in eski)).total_seconds() / 3600, 1.0)
        eski_hiz = len(eski) / saat
    else:
        eski_hiz = 0.0
    katsayi = yeni_hiz / eski_hiz if eski_hiz else None

    etiketler = Counter()
    for _, mesaj in son_24:
        duygu = (mesaj.get("entities") or {}).get("sentiment") or {}
        if duygu.get("basic") in (YUKSELIS, DUSUS):
            etiketler[duygu["basic"]] += 1
    etiketli = sum(etiketler.values())
    return {
        "sembol": sembol,
        "mesaj_sayisi": len(son_24),
        "saatlik_hiz": yeni_hiz,
        "onceki_hiz": eski_hiz,
        "trafik_katsayi": katsayi,
        "yukselis_orani": etiketler[YUKSELIS] / etiketli * 100 if etiketli else None,
        "etiketli_sayi": etiketli,
    }


def sosyal_satirlar(sembol):
    if not cfg.STOCKTWITS_AKTIF:
        return []
    ozet = sosyal_ozet(sembol)
    if not ozet:
        return []
    satirlar = ["", "<b>Sosyal trafik (Stocktwits)</b>",
                f"Son 24 saat: {ozet['mesaj_sayisi']} mesaj"]
    katsayi = ozet["trafik_katsayi"]
    if katsayi is not None:
        if katsayi >= cfg.STOCKTWITS_TRAFIK_ESIGI:
            satirlar.append(f"⚡ Konuşma trafiği {katsayi:.1f} kat arttı")
        else:
            satirlar.append(f"Trafik {katsayi:.1f}x (normal)")
    if ozet["etiketli_sayi"] >= cfg.STOCKTWITS_MIN_ETIKET:
        satirlar.append(
            f"Etiketli mesajların %{ozet['yukselis_orani']:.0f}'i yükseliş yönlü "
            f"(n={ozet['etiketli_sayi']})"
        )
        satirlar.append("ℹ️ Bu oran yön tahmini değil, yalnız topluluk havasıdır.")
    return satirlar
