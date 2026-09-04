"""Finnhub anlık fiyatlarından kademeli hareket bildirimleri üretir."""

import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

import config as cfg


PROJECT_DIR = Path(__file__).resolve().parent
STATE_FILE = PROJECT_DIR / ".price_movement_state.json"
NEW_YORK = ZoneInfo("America/New_York")


def _today():
    return datetime.now(NEW_YORK).date().isoformat()


def load_state():
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if state.get("date") == _today():
            return state
    except Exception:
        pass
    return {"date": _today(), "sent": {}}


def save_state(state):
    temporary = STATE_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    temporary.replace(STATE_FILE)


def fetch_quote(symbol):
    api_key = cfg.finnhub_key()
    if not api_key:
        return None
    try:
        response = requests.get(
            "https://finnhub.io/api/v1/quote",
            params={"symbol": symbol, "token": api_key},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return None
    if not data or not data.get("c"):
        return None
    return {
        "symbol": symbol,
        "price": float(data["c"]),
        "change": float(data.get("d", 0) or 0),
        "percent": float(data.get("dp", 0) or 0),
        "previous_close": float(data.get("pc", 0) or 0),
        "high": float(data.get("h", 0) or 0),
        "low": float(data.get("l", 0) or 0),
    }


def crossed_threshold(percent):
    crossed = [value for value in cfg.HAREKET_ESIKLERI if abs(percent) >= value]
    return max(crossed) if crossed else None


def evaluate_quote(quote, state):
    percent = quote["percent"]
    evaluated = percent
    previous_close = quote["previous_close"]
    if cfg.HAREKET_GUN_ICI_YAKALA and previous_close:
        candidates = (
            (quote["low"] - previous_close) / previous_close * 100,
            (quote["high"] - previous_close) / previous_close * 100,
        )
        evaluated = max((percent, *candidates), key=abs)
    if cfg.HAREKET_SADECE_YUKSELIS and evaluated < 0:
        return None
    if cfg.HAREKET_SADECE_DUSUS and evaluated > 0:
        return None
    threshold = crossed_threshold(evaluated)
    if threshold is None:
        return None
    direction = "up" if evaluated > 0 else "down"
    key = f"{quote['symbol']}_{direction}"
    if threshold <= float(state["sent"].get(key, 0)):
        return None
    result = dict(quote)
    result.update(
        threshold=threshold,
        evaluated_percent=evaluated,
        intraday_extreme=abs(evaluated - percent) >= 1.5,
        state_key=key,
    )
    return result


def scan_movements(symbols):
    state = load_state()
    alerts = []
    unique_symbols = list(dict.fromkeys(symbols))
    for index, symbol in enumerate(unique_symbols):
        quote = fetch_quote(symbol)
        if quote:
            alert = evaluate_quote(quote, state)
            if alert:
                alerts.append(alert)
        if index + 1 < len(unique_symbols):
            time.sleep(cfg.HAREKET_ISTEK_ARALIGI)
    return alerts, state


def mark_sent(alert, state):
    state["sent"][alert["state_key"]] = alert["threshold"]
    save_state(state)


def movement_message(alert):
    evaluated = alert["evaluated_percent"]
    direction = "📈 YÜKSELİŞ" if evaluated > 0 else "📉 DÜŞÜŞ"
    sign = "+" if alert["percent"] > 0 else ""
    lines = [
        f"{direction} — <b>{alert['symbol']}</b>",
        f"${alert['price']:.2f} ({sign}{alert['percent']:.2f}% | {sign}${alert['change']:.2f})",
        f"Önceki kapanış: ${alert['previous_close']:.2f}",
        f"Gün içi: ${alert['low']:.2f} – ${alert['high']:.2f}",
        f"Geçilen eşik: %{alert['threshold']:.0f}",
    ]
    if alert["intraday_extreme"]:
        lines.append(f"ℹ️ Hareket gün içinde %{evaluated:.1f} seviyesine ulaştı; fiyat kısmen toparlandı.")
    lines.append("\n⚠️ Fiyat bildirimi yatırım tavsiyesi değildir.")
    return "\n".join(lines)
