import argparse
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

import config as cfg
from opportunity_scanner import (
    EXCLUDED_FROM_TOP5,
    _levels_from_raw,
    _telegram_message,
    auto_send_top5,
    overlay_intraday,
    raw_metrics,
    score_opportunities,
)
from price_movement_alerts import mark_sent, movement_message, scan_movements
from tradingview_sync import sync_shared_watchlist
from watchlist import BASE_WATCHLIST, TRADINGVIEW_SHARED_WATCHLIST


PROJECT_DIR = Path(__file__).resolve().parent
LOCK_FILE = PROJECT_DIR / ".background_scanner.lock"
UNUSUAL_STATE_FILE = PROJECT_DIR / ".unusual_telegram_state.json"
NEWS_STATE_FILE = PROJECT_DIR / ".news_telegram_state.json"
TRANSLATION_CACHE_FILE = PROJECT_DIR / ".news_translation_cache.json"
NEW_YORK = ZoneInfo("America/New_York")
ISTANBUL = ZoneInfo("Europe/Istanbul")
PAYWALLED_NEWS_DOMAINS = {
    "seekingalpha.com",
    "www.seekingalpha.com",
}
load_dotenv(PROJECT_DIR / ".env")


def acquire_lock():
    try:
        descriptor = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(descriptor, str(os.getpid()).encode("utf-8"))
        os.close(descriptor)
        return True
    except FileExistsError:
        try:
            age = datetime.now().timestamp() - LOCK_FILE.stat().st_mtime
            if age > 3600:
                LOCK_FILE.unlink(missing_ok=True)
                return acquire_lock()
        except Exception:
            pass
        return False


def release_lock():
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def should_run(now_ny, force=False):
    if force:
        return True
    # Açılış öncesi analizden kapanış analizine kadar fiyat taraması yapılır.
    minutes = now_ny.hour * 60 + now_ny.minute
    return now_ny.weekday() < 5 and (8 * 60 + 25) <= minutes <= (16 * 60 + 15)


def delivery_slot(now_ny):
    """TOP 5 analizini açılıştan 1 saat önce, seans ortasında ve kapanışta gönderir."""
    minutes = now_ny.hour * 60 + now_ny.minute
    if (8 * 60 + 25) <= minutes < (8 * 60 + 50):
        return "acilistan_1_saat_once"
    if (12 * 60 + 40) <= minutes < (13 * 60 + 10):
        return "seans_ortasi"
    if (15 * 60 + 55) <= minutes <= (16 * 60 + 15):
        return "seans_kapanisi"
    return None


def news_delivery_mode(now_ny):
    """Normal haberleri iki özette, önemli haberleri yalnız seans içinde anlık yollar."""
    if now_ny.weekday() >= 5:
        return None
    ny_minutes = now_ny.hour * 60 + now_ny.minute
    now_tr = now_ny.astimezone(ISTANBUL)
    tr_minutes = now_tr.hour * 60 + now_tr.minute
    if (15 * 60 + 25) <= tr_minutes < (15 * 60 + 45):
        return "ozet_1530"
    if (15 * 60 + 55) <= ny_minutes <= (16 * 60 + 15):
        return "ozet_kapanis"
    if (9 * 60 + 30) <= ny_minutes < (16 * 60):
        return "onemli_anlik"
    return None


IMPORTANT_NEWS_TERMS = set(cfg.ONEMLI_KELIMELER)

COMPANY_HEADLINE_ALIASES = {
    "AMD": ("ADVANCED MICRO DEVICES",),
    "AVGO": ("BROADCOM",),
    "AAPL": ("APPLE",),
    "AMZN": ("AMAZON",),
    "GOOG": ("GOOGLE", "ALPHABET"),
    "META": ("META PLATFORMS", "FACEBOOK"),
    "MSFT": ("MICROSOFT",),
    "NVDA": ("NVIDIA",),
    "TSLA": ("TESLA",),
    "BA": ("BOEING",),
    "IBM": ("INTERNATIONAL BUSINESS MACHINES",),
    "WMT": ("WALMART",),
}

FINANCE_TRANSLATION_REPLACEMENTS = {
    "paylar": "hisseler",
    "pay senedi": "hisse",
    "stok fiyatı": "hisse fiyatı",
    "stok": "hisse",
    "kazanç raporu": "bilanço",
    "kazanç çağrısı": "bilanço toplantısı",
    "rehberlik": "beklenti",
    "yönlendirme": "beklenti",
    "notu düşürdü": "tavsiyesini düşürdü",
    "notu yükseltti": "tavsiyesini yükseltti",
    "geri alım": "hisse geri alımı",
}


def _fix_finance_terms(text):
    """Makine çevirisindeki yaygın finans terimi hatalarını düzeltir."""
    result = str(text or "")
    for wrong, correct in FINANCE_TRANSLATION_REPLACEMENTS.items():
        result = re.sub(rf"\b{re.escape(wrong)}\b", correct, result, flags=re.IGNORECASE)
    return result


def _translate_with_claude(text):
    """Anahtar ve açık tercih varsa Claude ile finans odaklı çeviri yapar."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key or os.getenv("NEWS_TRANSLATION_PROVIDER", "").casefold() != "anthropic":
        return None
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": os.getenv("ANTHROPIC_TRANSLATION_MODEL", "claude-haiku-4-5-20251001"),
                "max_tokens": 300,
                "system": (
                    "Verilen İngilizce borsa haberi başlığını doğal Türkçeye çevir. "
                    "Finans terimlerini doğru kullan; şirket adlarını ve hisse sembollerini "
                    "değiştirme. Yalnızca çeviriyi yaz."
                ),
                "messages": [{"role": "user", "content": text}],
            },
            timeout=25,
        )
        response.raise_for_status()
        parts = response.json().get("content", [])
        translated = "".join(
            part.get("text", "") for part in parts if part.get("type") == "text"
        ).strip()
        return _fix_finance_terms(translated) or None
    except Exception as exc:
        print(f"Claude çevirisi başarısız: {type(exc).__name__}", file=sys.stderr)
        return None


def _translate_with_google(text):
    """Anahtar gerektirmeyen Google çeviri ucunu kullanır."""
    try:
        response = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "en", "tl": "tr", "dt": "t", "q": text},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=12,
        )
        response.raise_for_status()
        payload = response.json()
        translated = "".join(part[0] for part in payload[0] if part and part[0]).strip()
        return _fix_finance_terms(translated) or None
    except Exception as exc:
        print(f"Google çevirisi başarısız: {type(exc).__name__}", file=sys.stderr)
        return None


def translate_news_to_turkish(text):
    """Önce isteğe bağlı Claude, sonra ücretsiz Google ile Türkçeye çevirir."""
    original = html.unescape(str(text or "").strip())
    if not original:
        return "Yeni haber"
    try:
        cache = json.loads(TRANSLATION_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        cache = {}
    cached = str(cache.get(original, "")).strip()
    if cached:
        return cached
    for translator in (_translate_with_claude, _translate_with_google):
        translated = translator(original)
        if not translated or translated.casefold() == original.casefold():
            continue
        cache[original] = translated
        cache = dict(list(cache.items())[-1000:])
        try:
            temporary = TRANSLATION_CACHE_FILE.with_suffix(".tmp")
            temporary.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            temporary.replace(TRANSLATION_CACHE_FILE)
        except Exception as exc:
            print(f"Çeviri önbelleği yazılamadı: {type(exc).__name__}", file=sys.stderr)
        return translated
    # İngilizce alarm göndermek yerine sonraki taramada yeniden denenecek.
    return None


def _is_important_news(article):
    text = " ".join(
        str(article.get(key, "")) for key in ("headline", "summary", "category")
    ).casefold()
    return any(term in text for term in IMPORTANT_NEWS_TERMS)


def _news_id(symbol, article):
    return "|".join(
        [
            str(symbol),
            str(article.get("id", "")),
            str(article.get("datetime", "")),
            str(article.get("url", "")),
            str(article.get("headline", "")),
        ]
    )


def _article_key(article):
    """Aynı Finnhub haberini farklı sembol sorgularında tekilleştirir."""
    return "|".join(
        [
            str(article.get("id", "")),
            str(article.get("datetime", "")),
            str(article.get("url", "")),
            str(article.get("headline", "")),
        ]
    )


def _news_is_relevant(symbol, article):
    """Çok sembollü Finnhub eşleşmelerinde yanlış şirket etiketini engeller."""
    symbol = str(symbol).strip().upper()
    related = {
        item.strip().upper()
        for item in re.split(r"[,;\s]+", str(article.get("related", "")))
        if item.strip()
    }
    headline = str(article.get("headline", "")).upper()
    explicit_tickers = {
        match.group(1)
        for match in re.finditer(r"\((?:NASDAQ:|NYSE:)?\s*\$?([A-Z]{1,5})\)", headline)
    }
    # Başlıktaki açık ticker, sağlayıcının hatalı `related` alanından üstündür.
    if explicit_tickers:
        return symbol in explicit_tickers
    if related and symbol not in related:
        return False
    ticker_in_headline = len(symbol) > 1 and re.search(
        rf"(?<![A-Z0-9]){re.escape(symbol)}(?![A-Z0-9])", headline
    )
    alias_in_headline = any(
        alias in headline for alias in COMPANY_HEADLINE_ALIASES.get(symbol, ())
    )
    return bool(ticker_in_headline or alias_in_headline)


def _is_paywalled_news(article):
    """Telegram'a ücretli abonelik isteyen haber bağlantılarını gönderme."""
    source = str(article.get("source", "")).strip().casefold()
    url = str(article.get("url", "")).strip()
    hostname = (urlparse(url).hostname or "").casefold()
    return "seeking alpha" in source or any(
        hostname == domain or hostname.endswith(f".{domain}")
        for domain in PAYWALLED_NEWS_DOMAINS
    )


def send_new_news_alerts(symbols, now_ny=None, force=False):
    """Normal haberleri planlı özetlerde, önemli haberleri seans içinde anlık gönderir."""
    now_ny = now_ny or datetime.now(NEW_YORK)
    mode = "ozet_zorunlu" if force else news_delivery_mode(now_ny)
    if mode is None:
        return 0, "Haber gönderim zamanı değil"
    api_key = cfg.finnhub_key()
    token = cfg.telegram_token()
    chat_id = cfg.telegram_chat_id()
    if not api_key or not token or not chat_id:
        return 0, "Haber/Telegram bilgileri eksik"

    try:
        state = json.loads(NEWS_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        state = {}
    seen = set(state.get("seen", []))
    first_run = not NEWS_STATE_FILE.exists()
    today = datetime.now(NEW_YORK).date()
    collected = []
    all_current_ids = set()
    skipped_paywalled_ids = set()
    skipped_irrelevant_ids = set()
    collected_article_keys = set()

    # Finnhub'un dakika kotasını aşmamak için istekleri aralıklı yap.
    for index, symbol in enumerate(dict.fromkeys(symbols)):
        try:
            response = requests.get(
                "https://finnhub.io/api/v1/company-news",
                params={
                    "symbol": symbol,
                    "from": (today - timedelta(days=cfg.HABER_GERI_GUN)).isoformat(),
                    "to": today.isoformat(),
                    "token": api_key,
                },
                timeout=20,
            )
            response.raise_for_status()
            articles = response.json()
            if not isinstance(articles, list):
                articles = []
            for article in articles:
                article_id = _news_id(symbol, article)
                all_current_ids.add(article_id)
                if _is_paywalled_news(article):
                    skipped_paywalled_ids.add(article_id)
                    continue
                if not _news_is_relevant(symbol, article):
                    skipped_irrelevant_ids.add(article_id)
                    continue
                article_key = _article_key(article)
                if article_id not in seen and article_key not in collected_article_keys:
                    collected.append((int(article.get("datetime", 0) or 0), symbol, article_id, article))
                    collected_article_keys.add(article_key)
        except Exception as exc:
            print(f"Haber kontrolü başarısız: {symbol} — {type(exc).__name__}", file=sys.stderr)
        if index + 1 < len(symbols):
            time.sleep(1.05)

    if first_run:
        initial = sorted(all_current_ids)[-5000:]
        NEWS_STATE_FILE.write_text(
            json.dumps({"seen": initial, "initialized_at": datetime.now().isoformat()}, ensure_ascii=False),
            encoding="utf-8",
        )
        return 0, f"Haber radarı başlatıldı; {len(initial)} mevcut haber başlangıç kabul edildi"

    collected.sort(key=lambda item: item[0])
    if mode == "onemli_anlik":
        collected = [item for item in collected if _is_important_news(item[3])]
    delivered = []
    # Tek mesajı Telegram sınırının altında tut; kalanlar sonraki kontrolde gönderilir.
    for timestamp, symbol, article_id, article in collected[:8]:
        headline = str(article.get("headline", "Yeni haber")).strip()
        turkish_headline = translate_news_to_turkish(headline)
        if not turkish_headline:
            continue
        source = str(article.get("source", "Kaynak belirtilmedi")).strip()
        url = str(article.get("url", "")).strip()
        news_time = datetime.fromtimestamp(timestamp, NEW_YORK).strftime("%Y-%m-%d %H:%M ET") if timestamp else "Saat bilinmiyor"
        label = "🚨 ÖNEMLİ SEANS HABERİ" if mode == "onemli_anlik" else "📰 PLANLI HABER ÖZETİ"
        message = "\n".join(
            [
                f"{label} — {symbol}",
                f"🇹🇷 {turkish_headline[:500]}",
                f"🕒 {news_time}",
                f"Kaynak: {source[:100]}",
                url,
                "⚠️ Haber bildirimi yatırım tavsiyesi değildir.",
            ]
        )
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": message, "disable_web_page_preview": True},
            timeout=20,
        )
        response.raise_for_status()
        delivered.append(article_id)

    if delivered or skipped_paywalled_ids or skipped_irrelevant_ids:
        seen.update(delivered)
        seen.update(skipped_paywalled_ids)
        seen.update(skipped_irrelevant_ids)
        NEWS_STATE_FILE.write_text(
            json.dumps({"seen": sorted(seen)[-5000:], "updated_at": datetime.now().isoformat()}, ensure_ascii=False),
            encoding="utf-8",
        )
    return len(delivered), (
        f"Yeni ücretsiz haber={len(collected)}, gönderilen={len(delivered)}, "
        f"ücretli kaynak atlandı={len(skipped_paywalled_ids)}, "
        f"ilgisiz sembol eşleşmesi atlandı={len(skipped_irrelevant_ids)}"
    )


def send_unusual_alerts(unusual):
    """Önemli düşüşleri aynı gün bir kez, seans sırasında anında gönderir."""
    if unusual is None or unusual.empty:
        return 0
    token = cfg.telegram_token()
    chat_id = cfg.telegram_chat_id()
    if not token or not chat_id:
        return 0

    today = datetime.now(NEW_YORK).date().isoformat()
    try:
        state = json.loads(UNUSUAL_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        state = {}
    sent_symbols = set(state.get("symbols", [])) if state.get("date") == today else set()
    new_rows = unusual[~unusual["Hisse"].isin(sent_symbols)].head(5)
    if new_rows.empty:
        return 0

    lines = ["🔻 ÖNEMLİ DÜŞÜŞ — CANLI RADAR", f"🕒 {datetime.now(NEW_YORK):%Y-%m-%d %H:%M ET}", ""]
    delivered = []
    for _, row in new_rows.iterrows():
        levels = _levels_from_raw(row)
        reasons = []
        if float(row["Günlük %"]) <= cfg.ONEMLI_DUSUS_ESIGI:
            reasons.append("sert düşüş")
        if float(row["Hacim Oranı"]) >= cfg.ANORMAL_HACIM_ORANI:
            reasons.append(f"{float(row['Hacim Oranı']):.1f}x hacim")
        lines.extend(
            [
                f"{row['Hisse']} — %{float(row['Günlük %']):+.2f} — {', '.join(reasons)}",
                f"Fiyat: ${float(row['Fiyat']):.2f}",
                f"Model alım bölgesi: ${levels['Alım Alt']:.2f}–${levels['Alım Üst']:.2f}",
                f"Stop: ${levels['Stop']:.2f} | Hedef: ${levels['Hedef 1']:.2f} / ${levels['Hedef 2']:.2f}",
                "",
            ]
        )
        delivered.append(str(row["Hisse"]))
    lines.append("⚠️ Düşüş tek başına alım sinyali değildir; haber ve risk kapıları kontrol edilmelidir.")
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": "\n".join(lines)},
        timeout=20,
    )
    response.raise_for_status()
    sent_symbols.update(delivered)
    temporary = UNUSUAL_STATE_FILE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({"date": today, "symbols": sorted(sent_symbols)}, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(UNUSUAL_STATE_FILE)
    return len(delivered)


def send_price_movement_alerts(symbols):
    """Yeni eşik aşan fiyat hareketlerini Telegram'a gönderir."""
    token = cfg.telegram_token()
    chat_id = cfg.telegram_chat_id()
    if not token or not chat_id:
        return 0
    alerts, state = scan_movements(symbols)
    delivered = 0
    for alert in alerts:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": movement_message(alert),
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=20,
        )
        response.raise_for_status()
        mark_sent(alert, state)
        delivered += 1
    return delivered


def fetch_ntsk_context():
    context = {
        "FINAL": "—",
        "Karar": "SABİT TAKİP",
        "Teknik": "Arka plan fiyat radarı",
        "SEC": "—",
        "Insider": "—",
        "Katalizör": "—",
        "Son 8-K": "—",
        "8-K": "Yeni yönlü olay saptanmadı",
        "Haber": "Yeni şirket haberi bulunamadı",
        "Sonraki Bilanço": "—",
    }
    api_key = cfg.finnhub_key()
    headers = {"User-Agent": "BorsaRobotu/1.0 contact@example.com"}
    today = datetime.now(NEW_YORK).date()

    if api_key:
        try:
            news = requests.get(
                "https://finnhub.io/api/v1/company-news",
                params={
                    "symbol": "NTSK",
                    "from": (today - timedelta(days=4)).isoformat(),
                    "to": today.isoformat(),
                    "token": api_key,
                },
                timeout=20,
            )
            news.raise_for_status()
            headlines = [str(item.get("headline", "")).strip() for item in news.json()[:3]]
            headlines = [headline for headline in headlines if headline]
            if headlines:
                context["Haber"] = " | ".join(headlines)[:600]
        except Exception:
            pass

        try:
            earnings = requests.get(
                "https://finnhub.io/api/v1/calendar/earnings",
                params={
                    "symbol": "NTSK",
                    "from": today.isoformat(),
                    "to": (today + timedelta(days=120)).isoformat(),
                    "token": api_key,
                },
                timeout=20,
            )
            earnings.raise_for_status()
            events = earnings.json().get("earningsCalendar", [])
            if events:
                context["Sonraki Bilanço"] = events[0].get("date", "—")
        except Exception:
            pass

    try:
        ticker_response = requests.get(
            "https://www.sec.gov/files/company_tickers.json", headers=headers, timeout=20
        )
        ticker_response.raise_for_status()
        cik = None
        for item in ticker_response.json().values():
            if str(item.get("ticker", "")).upper() == "NTSK":
                cik = str(item.get("cik_str", "")).zfill(10)
                break
        if cik:
            submission = requests.get(
                f"https://data.sec.gov/submissions/CIK{cik}.json",
                headers=headers,
                timeout=20,
            )
            submission.raise_for_status()
            recent = submission.json().get("filings", {}).get("recent", {})
            for form, date in zip(recent.get("form", []), recent.get("filingDate", [])):
                if form in {"8-K", "8-K/A"}:
                    context["Son 8-K"] = date
                    context["8-K"] = f"{form} bildirimi"
                    break
    except Exception:
        pass
    return context


def build_scan(watchlist):
    raw = raw_metrics(watchlist)
    if raw.empty:
        raise RuntimeError("Toplu fiyat verisi alınamadı")
    raw = overlay_intraday(raw, watchlist)

    scored = score_opportunities(watchlist, raw_data=raw)
    if scored.empty:
        raise RuntimeError("Fırsat puanı üretilemedi")
    top5 = scored[~scored["Hisse"].isin(EXCLUDED_FROM_TOP5)].head(5).copy()
    ntsk_match = raw[raw["Hisse"] == "NTSK"]
    ntsk_row = ntsk_match.iloc[0] if not ntsk_match.empty else None
    unusual = raw[
        (raw["Hisse"] != "NTSK")
        & (
            (raw["Günlük %"] <= cfg.ONEMLI_DUSUS_ESIGI)
            | (
                (raw["Hacim Oranı"] >= cfg.ANORMAL_HACIM_ORANI)
                & (raw["Günlük %"] <= cfg.HACIMLI_DUSUS_ESIGI)
            )
        )
    ].copy()
    if not unusual.empty:
        unusual["Hareket Gücü"] = unusual["Günlük %"].abs() * unusual["Hacim Oranı"].clip(lower=1)
        unusual = unusual.sort_values("Hareket Gücü", ascending=False)
    return raw, top5, ntsk_row, unusual


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "komut",
        nargs="?",
        default="hepsi",
        choices=("hepsi", "tarama", "haber", "hareket"),
        help="Çalıştırılacak bölüm (varsayılan: hepsi)",
    )
    parser.add_argument("--force", action="store_true", help="Saat kontrolünü atla")
    parser.add_argument("--dry-run", action="store_true", help="Telegram'a göndermeden test et")
    args = parser.parse_args()
    now_ny = datetime.now(NEW_YORK)
    if args.komut == "hareket":
        if not should_run(now_ny, force=args.force):
            print(f"{now_ny.isoformat()} — hareket taraması piyasa penceresini bekliyor")
            return 0
        if args.dry_run:
            print("Kuru çalıştırma: hareketler Telegram'a gönderilmedi")
            return 0
        count = send_price_movement_alerts(BASE_WATCHLIST)
        print(f"{datetime.now().isoformat()} — fiyat hareketi taraması — sent={count}")
        return 0
    if args.komut in ("haber", "hepsi"):
        if args.dry_run:
            print("Kuru çalıştırma: haberler Telegram'a gönderilmedi")
        else:
            try:
                news_count, news_status = send_new_news_alerts(BASE_WATCHLIST, now_ny=now_ny, force=args.force)
                print(f"{datetime.now().isoformat()} — {news_status} — news_sent={news_count}")
            except Exception as exc:
                print(f"Haber bildirimi hatası: {type(exc).__name__}: {exc}", file=sys.stderr)
    if args.komut == "haber":
        return 0
    if not should_run(now_ny, force=args.force):
        print(f"{now_ny.isoformat()} — piyasa sonrası çalışma penceresi bekleniyor")
        return 0
    if not acquire_lock():
        print("Başka bir tarama çalışıyor; çıkılıyor")
        return 0

    try:
        tradingview_symbols, synced, sync_status = sync_shared_watchlist(
            fallback=TRADINGVIEW_SHARED_WATCHLIST
        )
        active_watchlist = list(dict.fromkeys(BASE_WATCHLIST + tradingview_symbols))
        print(f"{datetime.now().isoformat()} — {sync_status} — total={len(active_watchlist)}")
        raw, top5, ntsk_row, unusual = build_scan(active_watchlist)
        # Tatil/hafta sonu veya gecikmiş veri, yeni günlük sinyal olarak gönderilmez.
        latest_date = max(raw["Veri Tarihi"].dropna().astype(str))
        if not args.force and latest_date != now_ny.date().isoformat():
            print(f"Güncel seans verisi yok: son veri {latest_date}")
            return 0
        context = fetch_ntsk_context()
        if args.dry_run and args.komut in ("tarama", "hepsi"):
            print(
                _telegram_message(
                    top5,
                    len(active_watchlist),
                    ntsk_row=ntsk_row,
                    ntsk_context=context,
                    unusual=unusual,
                )
            )
            return 0
        if args.dry_run and args.komut == "hareket":
            if unusual.empty:
                print("Olağan dışı hareket bulunmadı")
            else:
                print(unusual[["Hisse", "Fiyat", "Günlük %", "Hacim Oranı"]].to_string(index=False))
            return 0
        unusual_count = send_unusual_alerts(unusual) if args.komut == "hepsi" else 0
        slot = delivery_slot(now_ny)
        if slot or args.force:
            sent, status = auto_send_top5(
                top5,
                len(active_watchlist),
                ntsk_row=ntsk_row,
                ntsk_context=context,
                unusual=unusual,
                delivery_key=slot or "zorunlu_test",
            )
        else:
            sent, status = False, "Normal TOP 5 mesaj dilimi bekleniyor"
        print(
            f"{datetime.now().isoformat()} — {status} — sent={sent} — "
            f"new_unusual={unusual_count}"
        )
        return 0
    except Exception as exc:
        print(f"Tarama hatası: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())
