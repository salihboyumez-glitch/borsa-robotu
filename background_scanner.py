import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

from opportunity_scanner import (
    EXCLUDED_FROM_TOP5,
    _levels_from_raw,
    _telegram_message,
    auto_send_top5,
    overlay_intraday,
    raw_metrics,
    score_opportunities,
)
from tradingview_sync import sync_shared_watchlist
from watchlist import BASE_WATCHLIST, TRADINGVIEW_SHARED_WATCHLIST


PROJECT_DIR = Path(__file__).resolve().parent
LOCK_FILE = PROJECT_DIR / ".background_scanner.lock"
UNUSUAL_STATE_FILE = PROJECT_DIR / ".unusual_telegram_state.json"
NEW_YORK = ZoneInfo("America/New_York")
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
    # Hafta içi ABD normal seansı: açılıştan birkaç dakika sonra başlayıp kapanışa kadar.
    minutes = now_ny.hour * 60 + now_ny.minute
    return now_ny.weekday() < 5 and (9 * 60 + 35) <= minutes <= (16 * 60 + 15)


def delivery_slot(now_ny):
    """Normal TOP 5 mesajlarını günde üç zaman dilimiyle sınırlar."""
    minutes = now_ny.hour * 60 + now_ny.minute
    if (9 * 60 + 35) <= minutes < (10 * 60 + 35):
        return "acilis"
    if (12 * 60) <= minutes < (13 * 60 + 15):
        return "seans_ortasi"
    if (15 * 60 + 15) <= minutes <= (16 * 60 + 15):
        return "kapanis_oncesi"
    return None


def send_unusual_alerts(unusual):
    """Yeni olağan dışı hisseleri aynı gün bir kez, tarama anında gönderir."""
    if unusual is None or unusual.empty:
        return 0
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
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

    lines = ["⚡ OLAĞAN DIŞI HAREKET — CANLI RADAR", f"🕒 {datetime.now(NEW_YORK):%Y-%m-%d %H:%M ET}", ""]
    delivered = []
    for _, row in new_rows.iterrows():
        levels = _levels_from_raw(row)
        reasons = []
        if float(row["Günlük %"]) <= -7:
            reasons.append("olağan dışı indirim")
        if float(row["Hacim Oranı"]) >= 2:
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
    lines.append("⚠️ Sert düşüş tek başına alım sinyali değildir; haber ve risk kapıları kontrol edilmelidir.")
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
    api_key = os.getenv("FINNHUB_API_KEY")
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
            (raw["Günlük %"] <= -7)
            | ((raw["Hacim Oranı"] >= 2) & (raw["Günlük %"].abs() >= 3))
        )
    ].copy()
    if not unusual.empty:
        unusual["Hareket Gücü"] = unusual["Günlük %"].abs() * unusual["Hacim Oranı"].clip(lower=1)
        unusual = unusual.sort_values("Hareket Gücü", ascending=False)
    return raw, top5, ntsk_row, unusual


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Saat kontrolünü atla")
    parser.add_argument("--dry-run", action="store_true", help="Telegram'a göndermeden test et")
    args = parser.parse_args()
    now_ny = datetime.now(NEW_YORK)
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
        if args.dry_run:
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
        unusual_count = send_unusual_alerts(unusual)
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
