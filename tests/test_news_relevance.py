"""Finnhub haberlerinin doğru sembolle etiketlenmesini çevrimdışı doğrular."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from background_scanner import _article_key, _news_is_relevant


def test_single_related_symbol_is_accepted():
    assert _news_is_relevant("AMD", {"related": "AMD", "headline": "Chip demand rises"})


def test_broadcom_story_is_not_labeled_amd():
    article = {"related": "AMD,AVGO", "headline": "Broadcom raises annual guidance"}
    assert not _news_is_relevant("AMD", article)
    assert _news_is_relevant("AVGO", article)


def test_company_name_can_confirm_multi_symbol_story():
    article = {
        "related": "AMD,NVDA",
        "headline": "Advanced Micro Devices launches new accelerator",
    }
    assert _news_is_relevant("AMD", article)
    assert not _news_is_relevant("NVDA", article)


def test_unrelated_field_rejects_symbol():
    assert not _news_is_relevant("AMD", {"related": "AVGO", "headline": "AMD mentioned"})


def test_article_key_is_symbol_independent():
    article = {"id": 42, "datetime": 123, "url": "https://example.com/a", "headline": "News"}
    assert _article_key(article) == _article_key(dict(article))


if __name__ == "__main__":
    tests = [
        test_single_related_symbol_is_accepted,
        test_broadcom_story_is_not_labeled_amd,
        test_company_name_can_confirm_multi_symbol_story,
        test_unrelated_field_rejects_symbol,
        test_article_key_is_symbol_independent,
    ]
    for test in tests:
        test()
        print(f"GEÇTİ: {test.__name__}")
    print("TÜM HABER İLGİ TESTLERİ GEÇTİ")
