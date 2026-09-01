import json
import re
from datetime import datetime
from pathlib import Path

import requests


TRADINGVIEW_WATCHLIST_URLS = (
    "https://tr.tradingview.com/watchlists/36892357/",
    "https://tr.tradingview.com/watchlists/38678961/",
    "https://tr.tradingview.com/watchlists/40819901/",
    "https://tr.tradingview.com/watchlists/40916025/",
    "https://tr.tradingview.com/watchlists/71973820/",
    "https://tr.tradingview.com/watchlists/40915820/",
    "https://tr.tradingview.com/watchlists/40852901/",
    "https://tr.tradingview.com/watchlists/40874120/",
    "https://tr.tradingview.com/watchlists/40854421/",
    "https://tr.tradingview.com/watchlists/74528880/",
    "https://tr.tradingview.com/watchlists/41489478/",
    "https://tr.tradingview.com/watchlists/69825283/",
    "https://tr.tradingview.com/watchlists/40932991/",
    "https://tr.tradingview.com/watchlists/41267568/",
    "https://tr.tradingview.com/watchlists/40820092/",
    "https://tr.tradingview.com/watchlists/41525945/",
    "https://tr.tradingview.com/watchlists/40297832/",
    "https://tr.tradingview.com/watchlists/40916833/",
    "https://tr.tradingview.com/watchlists/40819830/",
    "https://tr.tradingview.com/watchlists/42295094/",
    "https://tr.tradingview.com/watchlists/65944555/",
    "https://tr.tradingview.com/watchlists/41269883/",
    "https://tr.tradingview.com/watchlists/71350971/",
    "https://tr.tradingview.com/watchlists/65939161/",
    "https://tr.tradingview.com/watchlists/42099764/",
    "https://tr.tradingview.com/watchlists/40819751/",
)
# Eski kodlarla uyumluluk için birincil liste adresi korunur.
TRADINGVIEW_WATCHLIST_URL = TRADINGVIEW_WATCHLIST_URLS[0]
CACHE_FILE = Path(__file__).with_name("tradingview_watchlist_cache.json")
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,14}$")


def parse_shared_watchlist_html(html):
    match = re.search(r'"list"\s*:\s*\{.*?"symbols"\s*:\s*(\[[^\]]*\])', html, re.S)
    if not match:
        raise ValueError("TradingView sembol dizisi bulunamadı")
    exchange_symbols = json.loads(match.group(1))
    symbols = []
    for item in exchange_symbols:
        ticker = str(item).split(":")[-1].strip().upper()
        if SYMBOL_PATTERN.fullmatch(ticker):
            symbols.append(ticker)
    symbols = list(dict.fromkeys(symbols))
    if not symbols:
        raise ValueError("TradingView listesi boş veya geçersiz")
    return symbols


def load_cached_symbols(fallback=None):
    try:
        payload = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        symbols = [
            str(symbol).upper()
            for symbol in payload.get("symbols", [])
            if SYMBOL_PATTERN.fullmatch(str(symbol).upper())
        ]
        if symbols:
            return list(dict.fromkeys(symbols))
    except Exception:
        pass
    return list(fallback or [])


def _save_cache(symbols):
    payload = {
        "sources": list(TRADINGVIEW_WATCHLIST_URLS),
        "synced_at": datetime.now().isoformat(),
        "count": len(symbols),
        "symbols": symbols,
    }
    temporary = CACHE_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(CACHE_FILE)


def sync_shared_watchlist(timeout=20, fallback=None):
    try:
        symbols = []
        for watchlist_url in TRADINGVIEW_WATCHLIST_URLS:
            response = requests.get(
                watchlist_url,
                headers={"User-Agent": "Mozilla/5.0 BorsaRobotu/1.0"},
                timeout=timeout,
            )
            response.raise_for_status()
            symbols.extend(parse_shared_watchlist_html(response.text))
        symbols = list(dict.fromkeys(symbols))
        _save_cache(symbols)
        return symbols, True, (
            f"TradingView senkronlandı: {len(TRADINGVIEW_WATCHLIST_URLS)} liste, "
            f"{len(symbols)} sembol"
        )
    except Exception as exc:
        cached = load_cached_symbols(fallback=fallback)
        return cached, False, f"TradingView erişilemedi, önbellek kullanıldı: {type(exc).__name__}"
