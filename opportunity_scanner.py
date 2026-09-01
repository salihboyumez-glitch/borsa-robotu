import json
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf
from dotenv import load_dotenv


load_dotenv()
STATE_FILE = Path(__file__).with_name(".opportunity_telegram_state.json")
EXCLUDED_FROM_TOP5 = {"NTSK"}


@st.cache_data(ttl=1800)
def download_universe(symbols_tuple):
    symbols = list(symbols_tuple)
    if not symbols:
        return pd.DataFrame()
    try:
        result = yf.download(
            symbols,
            period="1y",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=False,
        )
        return result if isinstance(result, pd.DataFrame) else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def download_intraday(symbols_tuple):
    symbols = list(symbols_tuple)
    if not symbols:
        return pd.DataFrame()
    try:
        result = yf.download(
            symbols,
            period="5d",
            interval="30m",
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=False,
            prepost=False,
        )
        return result if isinstance(result, pd.DataFrame) else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def _symbol_frame(batch, symbol, symbol_count):
    try:
        if symbol_count == 1 and not isinstance(batch.columns, pd.MultiIndex):
            frame = batch.copy()
        elif isinstance(batch.columns, pd.MultiIndex):
            first = batch.columns.get_level_values(0)
            second = batch.columns.get_level_values(1)
            if symbol in first:
                frame = batch[symbol].copy()
            elif symbol in second:
                frame = batch.xs(symbol, axis=1, level=1).copy()
            else:
                return pd.DataFrame()
        else:
            return pd.DataFrame()
        return frame.dropna(subset=["Close", "High", "Low"]).copy()
    except Exception:
        return pd.DataFrame()


def _rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    return 100 - 100 / (1 + gain / loss.replace(0, np.nan))


def _atr(frame, period=14):
    previous = frame["Close"].shift(1)
    ranges = pd.concat(
        [
            frame["High"] - frame["Low"],
            (frame["High"] - previous).abs(),
            (frame["Low"] - previous).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1).rolling(period).mean()


def raw_metrics(symbols):
    batch = download_universe(tuple(symbols))
    if batch is None or not isinstance(batch, pd.DataFrame) or batch.empty:
        return pd.DataFrame()

    rows = []
    for symbol in symbols:
        frame = _symbol_frame(batch, symbol, len(symbols))
        if frame.empty or len(frame) < 65:
            continue
        close = frame["Close"].astype(float)
        volume = frame["Volume"].fillna(0).astype(float)
        last = float(close.iloc[-1])
        atr = float(_atr(frame).iloc[-1])
        if not np.isfinite(atr) or atr <= 0:
            continue
        sma20 = float(close.rolling(20).mean().iloc[-1])
        sma50 = float(close.rolling(50).mean().iloc[-1])
        support20 = float(frame["Low"].tail(20).min())
        high52 = float(frame["High"].max())
        vol20 = float(close.pct_change().tail(20).std() * np.sqrt(252))
        dollar_volume = float((close * volume).tail(20).mean())
        average_volume = float(volume.tail(20).mean())
        volume_ratio = float(volume.iloc[-1] / average_volume) if average_volume else 0
        rsi = float(_rsi(close).iloc[-1])

        rows.append(
            {
                "Hisse": symbol,
                "Veri Tarihi": pd.Timestamp(frame.index[-1]).date().isoformat(),
                "Fiyat": last,
                "Önceki Kapanış": float(close.iloc[-2]),
                "Günlük %": (last / float(close.iloc[-2]) - 1) * 100,
                "3 Gün %": (last / float(close.iloc[-4]) - 1) * 100,
                "Haftalık %": (last / float(close.iloc[-6]) - 1) * 100,
                "20 Gün %": (last / float(close.iloc[-21]) - 1) * 100,
                "SMA20 Fark %": (last / sma20 - 1) * 100,
                "SMA50 Fark %": (last / sma50 - 1) * 100,
                "RSI": rsi,
                "Hacim Oranı": volume_ratio,
                "Ort Günlük Hacim": average_volume,
                "Volatilite %": vol20 * 100,
                "Günlük $ Hacim": dollar_volume,
                "Zirveye Uzaklık %": (last / high52 - 1) * 100,
                "ATR": atr,
                "20G Destek": support20,
            }
        )
    return pd.DataFrame(rows)


def overlay_intraday(raw, symbols):
    """30 dakikalık toplu veriyi günlük faktör tablosuna bindirir."""
    if raw is None or not isinstance(raw, pd.DataFrame) or raw.empty:
        return raw
    intraday = download_intraday(tuple(symbols))
    if intraday is None or not isinstance(intraday, pd.DataFrame) or intraday.empty:
        return raw

    result = raw.copy()
    for index, row in result.iterrows():
        symbol = str(row["Hisse"])
        frame = _symbol_frame(intraday, symbol, len(symbols))
        if frame.empty:
            continue
        latest = frame.iloc[-1]
        price = float(latest["Close"])
        latest_date = pd.Timestamp(frame.index[-1]).date().isoformat()
        same_day = frame[pd.Index(frame.index).map(lambda value: pd.Timestamp(value).date().isoformat() == latest_date)]
        day_volume = float(same_day["Volume"].fillna(0).sum()) if not same_day.empty else 0
        previous_close = float(row["Önceki Kapanış"])
        old_price = float(row["Fiyat"])
        result.at[index, "Veri Tarihi"] = latest_date
        result.at[index, "Fiyat"] = price
        result.at[index, "Günlük %"] = (price / previous_close - 1) * 100
        result.at[index, "Hacim Oranı"] = day_volume / max(float(row["Ort Günlük Hacim"]), 1)
        if old_price > 0:
            price_delta = price / old_price - 1
            result.at[index, "3 Gün %"] = ((1 + float(row["3 Gün %"]) / 100) * (1 + price_delta) - 1) * 100
            result.at[index, "Haftalık %"] = ((1 + float(row["Haftalık %"]) / 100) * (1 + price_delta) - 1) * 100
            result.at[index, "20 Gün %"] = ((1 + float(row["20 Gün %"]) / 100) * (1 + price_delta) - 1) * 100
            result.at[index, "SMA20 Fark %"] = ((1 + float(row["SMA20 Fark %"]) / 100) * (1 + price_delta) - 1) * 100
            result.at[index, "SMA50 Fark %"] = ((1 + float(row["SMA50 Fark %"]) / 100) * (1 + price_delta) - 1) * 100
    return result


def _rank(series, ascending=True):
    return series.rank(pct=True, ascending=ascending).fillna(0.5) * 100


def score_opportunities(symbols, raw_data=None):
    data = raw_metrics(symbols) if raw_data is None else raw_data.copy()
    if data.empty:
        return data

    liquid = (
        (data["Fiyat"] >= 5)
        & (data["Günlük $ Hacim"] >= 10_000_000)
        & (data["RSI"].between(35, 78))
        & (data["Zirveye Uzaklık %"] >= -45)
    )
    data = data[liquid].copy()
    if data.empty:
        return data

    risk_rank = _rank(data["Volatilite %"], ascending=False)
    volume_rank = _rank(data["Hacim Oranı"])
    trend20 = _rank(data["SMA20 Fark %"])
    trend50 = _rank(data["SMA50 Fark %"])

    data["Günlük Puan"] = (
        _rank(data["Günlük %"]) * 0.30
        + _rank(data["3 Gün %"]) * 0.20
        + volume_rank * 0.20
        + trend20 * 0.15
        + risk_rank * 0.15
    ).round()
    data["3 Günlük Puan"] = (
        _rank(data["3 Gün %"]) * 0.35
        + _rank(data["Haftalık %"]) * 0.20
        + trend20 * 0.20
        + volume_rank * 0.10
        + risk_rank * 0.15
    ).round()
    data["Haftalık Puan"] = (
        _rank(data["Haftalık %"]) * 0.30
        + _rank(data["20 Gün %"]) * 0.25
        + trend50 * 0.20
        + risk_rank * 0.15
        + volume_rank * 0.10
    ).round()

    score_columns = ["Günlük Puan", "3 Günlük Puan", "Haftalık Puan"]
    data["Fırsat Puanı"] = data[score_columns].max(axis=1)
    labels = {
        "Günlük Puan": "GÜNLÜK",
        "3 Günlük Puan": "3 GÜNLÜK",
        "Haftalık Puan": "HAFTALIK",
    }
    data["Ufuk"] = data[score_columns].idxmax(axis=1).map(labels)

    entry_center = np.maximum(data["20G Destek"], data["Fiyat"] - 0.50 * data["ATR"])
    data["Alım Alt"] = np.maximum(0.01, entry_center - 0.25 * data["ATR"])
    data["Alım Üst"] = entry_center + 0.25 * data["ATR"]
    data["Stop"] = np.maximum(0.01, data["Alım Alt"] - 1.50 * data["ATR"])
    risk = ((data["Alım Alt"] + data["Alım Üst"]) / 2) - data["Stop"]
    data["Hedef 1"] = ((data["Alım Alt"] + data["Alım Üst"]) / 2) + 2 * risk
    data["Hedef 2"] = ((data["Alım Alt"] + data["Alım Üst"]) / 2) + 3 * risk

    numeric = ["Fiyat", "Alım Alt", "Alım Üst", "Stop", "Hedef 1", "Hedef 2"]
    data[numeric] = data[numeric].round(2)
    return data.sort_values("Fırsat Puanı", ascending=False).reset_index(drop=True)


def top5_opportunities(symbols):
    scored = score_opportunities(symbols)
    if scored.empty:
        return scored
    return scored[~scored["Hisse"].isin(EXCLUDED_FROM_TOP5)].head(5).copy()


def _levels_from_raw(row):
    entry_center = max(float(row["20G Destek"]), float(row["Fiyat"]) - 0.50 * float(row["ATR"]))
    entry_low = max(0.01, entry_center - 0.25 * float(row["ATR"]))
    entry_high = entry_center + 0.25 * float(row["ATR"])
    stop = max(0.01, entry_low - 1.50 * float(row["ATR"]))
    risk = (entry_low + entry_high) / 2 - stop
    return {
        "Alım Alt": round(entry_low, 2),
        "Alım Üst": round(entry_high, 2),
        "Stop": round(stop, 2),
        "Hedef 1": round((entry_low + entry_high) / 2 + 2 * risk, 2),
        "Hedef 2": round((entry_low + entry_high) / 2 + 3 * risk, 2),
    }


def _telegram_message(top5, scanned_count, ntsk_row=None, ntsk_context=None, unusual=None):
    lines = [
        f"📌 NTSK SABİT TAKİP + {scanned_count} HİSSE FIRSAT RADARI",
        f"🕒 {datetime.now():%Y-%m-%d %H:%M}",
        "",
    ]
    context = ntsk_context or {}
    if ntsk_row is not None:
        levels = _levels_from_raw(ntsk_row)
        lines.extend(
            [
                "⭐ NTSK — SABİT ÖZEL TAKİP",
                f"Fiyat: ${float(ntsk_row['Fiyat']):.2f} | Günlük: %{float(ntsk_row['Günlük %']):+.2f}",
                f"Final: {context.get('FINAL', '—')}/100 | Karar: {context.get('Karar', '—')}",
                f"Teknik: {context.get('Teknik', '—')} | SEC: {context.get('SEC', '—')} | Insider: {context.get('Insider', '—')} | Katalizör: {context.get('Katalizör', '—')}",
                f"Takip alım bölgesi: ${levels['Alım Alt']:.2f}–${levels['Alım Üst']:.2f}",
                f"Risk stopu: ${levels['Stop']:.2f} | Hedefler: ${levels['Hedef 1']:.2f} / ${levels['Hedef 2']:.2f}",
                f"Son 8-K: {context.get('Son 8-K', '—')} — {context.get('8-K', '—')}",
                f"Haber: {context.get('Haber', '—')}",
                f"Sonraki bilanço: {context.get('Sonraki Bilanço', '—')}",
                "",
            ]
        )
    else:
        lines.extend(["⭐ NTSK: fiyat verisi alınamadı; sabit takip devam ediyor.", ""])

    lines.append("🎯 DİNAMİK FIRSAT TOP 5 — NTSK HARİÇ")
    for rank, (_, row) in enumerate(top5.iterrows(), start=1):
        lines.extend(
            [
                f"{rank}. {row['Hisse']} — {row['Ufuk']} — {int(row['Fırsat Puanı'])}/100",
                f"Fiyat: ${row['Fiyat']:.2f}",
                f"Alım bölgesi: ${row['Alım Alt']:.2f}–${row['Alım Üst']:.2f}",
                f"Stop: ${row['Stop']:.2f}",
                f"Hedef 1: ${row['Hedef 1']:.2f} | Hedef 2: ${row['Hedef 2']:.2f}",
                f"RSI: {row['RSI']:.1f} | Volatilite: %{row['Volatilite %']:.1f}",
                "",
            ]
        )
    if unusual is not None and not unusual.empty:
        lines.append("⚡ OLAĞAN DIŞI HAREKETLER")
        for _, row in unusual.head(5).iterrows():
            reason = []
            if float(row["Günlük %"]) <= -7:
                reason.append("sert indirim")
            if float(row["Hacim Oranı"]) >= 2:
                reason.append(f"{float(row['Hacim Oranı']):.1f}x hacim")
            lines.append(
                f"{row['Hisse']}: %{float(row['Günlük %']):+.2f} — {', '.join(reason)}"
            )
        lines.append("")
    lines.extend(
        [
            f"📊 {scanned_count} sembol toplu tarandı. NTSK fırsat TOP 5'ine dahil edilmedi.",
            "⚠️ Seviyeler ATR tabanlı model çıktısıdır; yatırım tavsiyesi veya gerçekleşme garantisi değildir.",
        ]
    )
    return "\n".join(lines)


def _load_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state):
    temporary = STATE_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    temporary.replace(STATE_FILE)


def explain_opportunity(row, question="", is_top5=False):
    """Model puanlarını kısa, anlaşılır ve hesaplanabilir gerekçelere çevirir."""
    symbol = str(row.get("Hisse", "—"))
    score = int(float(row.get("Fırsat Puanı", 0)))
    horizon = str(row.get("Ufuk", "—"))
    daily = float(row.get("Günlük %", 0))
    three_day = float(row.get("3 Gün %", 0))
    weekly = float(row.get("Haftalık %", 0))
    rsi = float(row.get("RSI", 0))
    volume_ratio = float(row.get("Hacim Oranı", 0))
    volatility = float(row.get("Volatilite %", 0))
    sma20 = float(row.get("SMA20 Fark %", 0))
    sma50 = float(row.get("SMA50 Fark %", 0))

    positives = []
    if sma20 > 0:
        positives.append(f"fiyat 20 günlük ortalamanın %{sma20:.1f} üzerinde")
    if sma50 > 0:
        positives.append(f"50 günlük ana trend %{sma50:.1f} pozitif")
    if volume_ratio >= 1.5:
        positives.append(f"hacim normalin {volume_ratio:.1f} katı")
    if 40 <= rsi <= 68:
        positives.append(f"RSI {rsi:.1f} ile dengeli bölgede")
    if daily > 0 or three_day > 0 or weekly > 0:
        positives.append(
            f"momentum günlük %{daily:+.1f}, 3 günlük %{three_day:+.1f}, haftalık %{weekly:+.1f}"
        )
    if not positives:
        positives.append("model içindeki göreli puanı diğer taranan hisselerden yüksek")

    risks = []
    if rsi >= 70:
        risks.append(f"RSI {rsi:.1f}; kısa vadede aşırı alım riski var")
    elif rsi < 40:
        risks.append(f"RSI {rsi:.1f}; momentum henüz zayıf")
    if volatility >= 55:
        risks.append(f"yıllıklandırılmış oynaklık %{volatility:.1f}; fiyat sert hareket edebilir")
    if sma20 < 0:
        risks.append(f"fiyat 20 günlük ortalamanın %{abs(sma20):.1f} altında")
    if volume_ratio < 0.8:
        risks.append(f"hacim oranı {volume_ratio:.1f}; hareketin teyidi zayıf")
    if not risks:
        risks.append("stop seviyesi kırılırsa model senaryosu geçersiz sayılmalı")

    rank_text = "TOP 5'e girdi" if is_top5 else "izleme havuzunda puanlandı"
    lines = [
        f"**{symbol} neden {rank_text}?**",
        f"Model puanı **{score}/100**, baskın fırsat ufku **{horizon}**.",
        "Olumlu gerekçeler: " + "; ".join(positives[:4]) + ".",
        "Riskler: " + "; ".join(risks[:3]) + ".",
        (
            f"Planlanan bölge: **${float(row.get('Alım Alt', 0)):.2f}–"
            f"${float(row.get('Alım Üst', 0)):.2f} alım**, "
            f"**${float(row.get('Stop', 0)):.2f} stop**, "
            f"**${float(row.get('Hedef 1', 0)):.2f} / ${float(row.get('Hedef 2', 0)):.2f} hedef**."
        ),
    ]
    if question.strip():
        lines.append(f"Sorunun özeti: “{question.strip()}” — cevap yukarıdaki güncel radar verilerine dayanır.")
    lines.append("Bu açıklama olasılık ve risk modelidir; kâr garantisi veya yatırım tavsiyesi değildir.")
    return "\n\n".join(lines)


def auto_send_top5(
    top5,
    scanned_count,
    ntsk_row=None,
    ntsk_context=None,
    unusual=None,
    delivery_key="daily",
):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id or top5.empty:
        return False, "Telegram bilgileri veya fırsat listesi eksik."

    today = datetime.now().date().isoformat()
    signature = "|".join(
        f"{row['Hisse']}:{row['Ufuk']}:{row['Alım Alt']:.2f}:{row['Stop']:.2f}:{row['Hedef 1']:.2f}"
        for _, row in top5.iterrows()
    )
    state = _load_state()
    sent_keys = state.get("sent_keys", []) if state.get("date") == today else []
    if delivery_key in sent_keys:
        return False, f"Bugünkü {delivery_key} fırsat mesajı daha önce gönderildi."

    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": _telegram_message(
                top5,
                scanned_count,
                ntsk_row=ntsk_row,
                ntsk_context=ntsk_context,
                unusual=unusual,
            ),
        },
        timeout=20,
    )
    response.raise_for_status()
    sent_keys.append(delivery_key)
    _save_state(
        {
            "date": today,
            "signature": signature,
            "sent_at": datetime.now().isoformat(),
            "sent_keys": sent_keys,
        }
    )
    return True, "Fırsat TOP 5 Telegram'a otomatik gönderildi."


def render_opportunity_scanner(symbols, ntsk_context=None):
    st.divider()
    st.title(f"🎯 {len(symbols)} Hisse Fırsat Radarı")
    st.caption(
        "Günlük, 3 günlük ve haftalık fırsatları toplu fiyat verisiyle tarar. "
        "NTSK bu TOP 5 listesine alınmaz."
    )
    enabled = st.toggle(f"{len(symbols)} hisse otomatik fırsat taraması", value=True)
    if not enabled:
        st.info("Fırsat taraması kapalı.")
        return

    with st.spinner(f"{len(symbols)} hisse toplu taranıyor..."):
        raw = raw_metrics(symbols)
        scored = score_opportunities(symbols, raw_data=raw)
        top5 = scored[~scored["Hisse"].isin(EXCLUDED_FROM_TOP5)].head(5).copy() if not scored.empty else scored

    ntsk_matches = raw[raw["Hisse"] == "NTSK"] if not raw.empty else pd.DataFrame()
    ntsk_row = ntsk_matches.iloc[0] if not ntsk_matches.empty else None
    unusual = raw[
        (raw["Hisse"] != "NTSK")
        & (
            (raw["Günlük %"] <= -7)
            | ((raw["Hacim Oranı"] >= 2) & (raw["Günlük %"].abs() >= 3))
        )
    ].copy() if not raw.empty else pd.DataFrame()
    if not unusual.empty:
        unusual["Hareket Gücü"] = unusual["Günlük %"].abs() * unusual["Hacim Oranı"].clip(lower=1)
        unusual = unusual.sort_values("Hareket Gücü", ascending=False)

    if top5.empty:
        st.warning("Fırsat taraması sonuç üretmedi; fiyat verisi bağlantısını kontrol edin.")
        return

    st.subheader("⭐ NTSK — Sabit Özel Takip")
    if ntsk_row is not None:
        levels = _levels_from_raw(ntsk_row)
        context = ntsk_context or {}
        ntsk_display = pd.DataFrame(
            [
                {
                    "Hisse": "NTSK",
                    "Fiyat": round(float(ntsk_row["Fiyat"]), 2),
                    "Günlük %": round(float(ntsk_row["Günlük %"]), 2),
                    "FINAL": context.get("FINAL", "—"),
                    "Karar": context.get("Karar", "—"),
                    "Alım Alt": levels["Alım Alt"],
                    "Alım Üst": levels["Alım Üst"],
                    "Stop": levels["Stop"],
                    "Hedef 1": levels["Hedef 1"],
                    "Hedef 2": levels["Hedef 2"],
                    "Sonraki Bilanço": context.get("Sonraki Bilanço", "—"),
                }
            ]
        )
        st.dataframe(ntsk_display, width="stretch", hide_index=True)
        st.info(f"Haber: {context.get('Haber', '—')} | 8-K: {context.get('8-K', '—')}")
    else:
        st.warning("NTSK fiyat verisi alınamadı; sabit takip listesinde kalmaya devam ediyor.")

    st.subheader("🎯 Dinamik Fırsat TOP 5 — NTSK Hariç")

    display = top5[
        [
            "Hisse", "Ufuk", "Fırsat Puanı", "Fiyat", "Alım Alt", "Alım Üst",
            "Stop", "Hedef 1", "Hedef 2", "RSI", "Volatilite %"
        ]
    ].copy()
    display.insert(0, "Sıra", range(1, len(display) + 1))
    st.dataframe(display, width="stretch", hide_index=True)

    st.subheader("💬 Radara Sor")
    st.caption(
        "Bir hisse seçip neden önerildiğini, riskini veya alım–stop–hedef planını sor. "
        "Yanıt mevcut tarama verilerinden anında üretilir."
    )
    answer_symbols = scored["Hisse"].astype(str).tolist()
    selected_symbol = st.selectbox(
        "Açıklanacak hisse",
        answer_symbols,
        key="radara_sor_symbol",
    )
    question = st.text_input(
        "Sorun",
        placeholder=f"Örnek: {selected_symbol} neden önerildi, riski ve stop seviyesi nedir?",
        key="radara_sor_question",
    )
    if st.button("Robota Sor", key="radara_sor_button", type="primary"):
        selected_row = scored[scored["Hisse"] == selected_symbol].iloc[0]
        st.markdown(
            explain_opportunity(
                selected_row,
                question=question,
                is_top5=selected_symbol in set(top5["Hisse"].astype(str)),
            )
        )

    try:
        sent, status = auto_send_top5(
            top5,
            len(symbols),
            ntsk_row=ntsk_row,
            ntsk_context=ntsk_context,
            unusual=unusual,
        )
        if sent:
            st.success(status)
        else:
            st.caption(status)
    except Exception as exc:
        st.warning(f"Telegram fırsat mesajı gönderilemedi: {type(exc).__name__}")

    st.subheader("⚡ Olağan Dışı İndirim / Hareket Radarı")
    if unusual.empty:
        st.caption("Bugün eşikleri aşan olağan dışı hareket bulunmadı.")
    else:
        st.dataframe(
            unusual[["Hisse", "Fiyat", "Günlük %", "Hacim Oranı", "Volatilite %", "Zirveye Uzaklık %"]].head(10),
            width="stretch",
            hide_index=True,
        )

    with st.expander("Ufuklara göre ilk 5 listeleri"):
        for title, column in [
            ("Günlük", "Günlük Puan"),
            ("3 Günlük", "3 Günlük Puan"),
            ("Haftalık", "Haftalık Puan"),
        ]:
            st.subheader(title)
            horizon = scored[~scored["Hisse"].isin(EXCLUDED_FROM_TOP5)].nlargest(5, column)
            st.dataframe(
                horizon[["Hisse", column, "Fiyat", "Alım Alt", "Alım Üst", "Stop", "Hedef 1"]],
                width="stretch",
                hide_index=True,
            )
