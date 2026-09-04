from datetime import datetime, timedelta, timezone
from unittest import TestCase, mock

import stocktwits_social as sosyal


def _mesaj(simdi, saat, duygu=None):
    sonuc = {"created_at": (simdi - timedelta(hours=saat)).strftime("%Y-%m-%dT%H:%M:%SZ")}
    if duygu:
        sonuc["entities"] = {"sentiment": {"basic": duygu}}
    return sonuc


class StocktwitsSocialTests(TestCase):
    def test_sosyal_ozet_trafik_ve_duygu(self):
        simdi = datetime(2026, 9, 4, 15, tzinfo=timezone.utc)
        mesajlar = [_mesaj(simdi, 0.5, "Bullish") for _ in range(6)]
        mesajlar += [_mesaj(simdi, 6, "Bearish"), _mesaj(simdi, 10)]
        with mock.patch.object(sosyal, "sembol_akisi", return_value={"messages": mesajlar}):
            sonuc = sosyal.sosyal_ozet("AAPL", simdi=simdi)
        self.assertEqual(sonuc["mesaj_sayisi"], 8)
        self.assertGreater(sonuc["trafik_katsayi"], 2)
        self.assertEqual(sonuc["etiketli_sayi"], 7)
        self.assertEqual(round(sonuc["yukselis_orani"]), 86)

    def test_veri_yokken_bildirime_ek_yapmaz(self):
        with mock.patch.object(sosyal, "sembol_akisi", return_value=None):
            self.assertEqual(sosyal.sosyal_satirlar("AAPL"), [])
