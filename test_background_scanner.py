import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import background_scanner as scanner


class NewsRelevanceTests(unittest.TestCase):
    def test_explicit_psn_ticker_blocks_ibm(self):
        article = {"headline": "Parsons (PSN): Buy, Sell, or Hold Post Q2 Earnings?", "related": "IBM"}
        self.assertFalse(scanner._news_is_relevant("IBM", article))

    def test_explicit_tal_ticker_blocks_wmt(self):
        article = {"headline": "TAL Education Group (TAL) Reports Quarterly Results", "related": "WMT"}
        self.assertFalse(scanner._news_is_relevant("WMT", article))

    def test_explicit_hurn_ticker_blocks_ba(self):
        article = {"headline": "Huron Consulting Group (HURN) Raises Guidance", "related": "BA"}
        self.assertFalse(scanner._news_is_relevant("BA", article))

    def test_unrelated_asian_adr_blocks_meta(self):
        article = {"headline": "Asian ADRs Move Lower in Friday Trading", "related": "META"}
        self.assertFalse(scanner._news_is_relevant("META", article))

    def test_company_name_confirms_followed_symbol(self):
        article = {"headline": "IBM announces new enterprise AI products", "related": "IBM"}
        self.assertTrue(scanner._news_is_relevant("IBM", article))


class TranslationTests(unittest.TestCase):
    @patch.object(scanner.requests, "get")
    def test_translates_english_headline(self, get):
        response = Mock()
        response.json.return_value = [[["IBM yeni ürünlerini duyurdu", None]]]
        get.return_value = response

        with TemporaryDirectory() as directory, patch.object(
            scanner, "TRANSLATION_CACHE_FILE", Path(directory) / "cache.json"
        ):
            result = scanner.translate_news_to_turkish("IBM announces new products")

        self.assertEqual(result, "IBM yeni ürünlerini duyurdu")

    @patch.object(scanner.requests, "get", side_effect=RuntimeError("offline"))
    def test_does_not_fall_back_to_english(self, _get):
        with TemporaryDirectory() as directory, patch.object(
            scanner, "TRANSLATION_CACHE_FILE", Path(directory) / "cache.json"
        ):
            self.assertIsNone(scanner.translate_news_to_turkish("English headline"))


if __name__ == "__main__":
    unittest.main()
