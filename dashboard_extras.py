import os
from datetime import datetime

import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf
from dotenv import load_dotenv


load_dotenv()


@st.cache_data(ttl=900)
def extended_history(symbol, period="1y"):
    try:
        frame = yf.download(
            symbol,
            period=period,
            interval="1d",
            progress=False,
            auto_adjust=False,
        )
        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = frame.columns.get_level_values(0)
        return frame.dropna()
    except Exception:
        return pd.DataFrame()


def add_indicators(frame):
    data = frame.copy()
    close = data["Close"]
    data["SMA20"] = close.rolling(20).mean()
    data["SMA50"] = close.rolling(50).mean()
    data["SMA200"] = close.rolling(200).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    data["RSI"] = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    data["MACD"] = ema12 - ema26
    data["MACD Signal"] = data["MACD"].ewm(span=9, adjust=False).mean()

    previous = close.shift(1)
    true_range = pd.concat(
        [
            data["High"] - data["Low"],
            (data["High"] - previous).abs(),
            (data["Low"] - previous).abs(),
        ],
        axis=1,
    ).max(axis=1)
    data["ATR14"] = true_range.rolling(14).mean()
    return data


def risk_plan(symbol, account_size, risk_percent):
    data = extended_history(symbol, "6mo")
    if data.empty or len(data) < 20:
        return None

    data = add_indicators(data)
    latest = data.iloc[-1]
    entry = float(latest["Close"])
    atr = float(latest["ATR14"]) if pd.notna(latest["ATR14"]) else entry * 0.03
    stop = max(0.01, entry - 2 * atr)
    risk_per_share = max(0.01, entry - stop)
    target_1 = entry + 2 * risk_per_share
    target_2 = entry + 3 * risk_per_share
    risk_budget = account_size * risk_percent / 100
    quantity = int(risk_budget / risk_per_share) if risk_budget > 0 else 0

    return {
        "Hisse": symbol,
        "Giriş": round(entry, 2),
        "Stop": round(stop, 2),
        "Hedef 1": round(target_1, 2),
        "Hedef 2": round(target_2, 2),
        "Risk/Getiri": "1:2 / 1:3",
        "ATR": round(atr, 2),
        "Adet": quantity,
        "Azami Risk $": round(quantity * risk_per_share, 2),
    }


def render_risk(symbols):
    st.header("🛡️ Risk Yönetimi")
    col1, col2 = st.columns(2)
    with col1:
        account_size = st.number_input(
            "Portföy büyüklüğü ($)", min_value=100.0, value=10_000.0, step=500.0
        )
    with col2:
        risk_percent = st.number_input(
            "İşlem başına risk (%)", min_value=0.1, max_value=10.0, value=1.0, step=0.1
        )

    rows = [plan for symbol in symbols[:5] if (plan := risk_plan(symbol, account_size, risk_percent))]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.caption(
        "Stop mesafesi 2×ATR, hedefler 2R ve 3R ile hesaplanır. Adet, seçilen azami "
        "portföy riskine göre belirlenir; yatırım tavsiyesi değildir."
    )


def render_detail(symbols):
    st.header("🔎 Hisse Detayı & Grafikler")
    symbol = st.selectbox("İncelenecek hisse", symbols, key="detail_symbol")

    with st.expander(f"{symbol} grafiklerini aç", expanded=False):
        data = extended_history(symbol)
        if data.empty:
            st.warning("Grafik için geçmiş fiyat verisi bulunamadı.")
            return symbol

        data = add_indicators(data)
        last = data.iloc[-1]
        previous = data.iloc[-2]
        change = (float(last["Close"]) / float(previous["Close"]) - 1) * 100
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Son fiyat", f"${float(last['Close']):.2f}", f"{change:+.2f}%")
        c2.metric("RSI", f"{float(last['RSI']):.1f}" if pd.notna(last["RSI"]) else "—")
        c3.metric("ATR", f"${float(last['ATR14']):.2f}" if pd.notna(last["ATR14"]) else "—")
        c4.metric("SMA200", f"${float(last['SMA200']):.2f}" if pd.notna(last["SMA200"]) else "—")

        st.subheader("Fiyat ve hareketli ortalamalar")
        st.line_chart(data[["Close", "SMA20", "SMA50", "SMA200"]].dropna(how="all"))
        st.subheader("Hacim")
        st.bar_chart(data[["Volume"]])
        left, right = st.columns(2)
        with left:
            st.subheader("RSI")
            st.line_chart(data[["RSI"]].dropna())
        with right:
            st.subheader("MACD")
            st.line_chart(data[["MACD", "MACD Signal"]].dropna())
    return symbol


def backtest(symbol):
    data = add_indicators(extended_history(symbol, "2y"))
    if data.empty or len(data) < 220:
        return None, pd.DataFrame()

    data["Signal"] = (
        (data["SMA20"] > data["SMA50"])
        & (data["Close"] > data["SMA200"])
        & data["RSI"].between(45, 70)
    )
    entries = data[data["Signal"] & ~data["Signal"].shift(1).fillna(False)].copy()
    for days in (1, 5, 20, 60):
        entries[f"{days} Gün %"] = (
            data["Close"].shift(-days).reindex(entries.index) / entries["Close"] - 1
        ) * 100

    valid_20 = entries["20 Gün %"].dropna()
    summary = {
        "Sinyal Sayısı": len(entries),
        "20 Gün İsabet %": round((valid_20 > 0).mean() * 100, 1) if len(valid_20) else "—",
        "Ort. 5 Gün %": round(entries["5 Gün %"].mean(), 2),
        "Ort. 20 Gün %": round(entries["20 Gün %"].mean(), 2),
        "Ort. 60 Gün %": round(entries["60 Gün %"].mean(), 2),
        "En Kötü 20 Gün %": round(entries["20 Gün %"].min(), 2),
    }
    detail = entries.reset_index().tail(20)
    date_col = detail.columns[0]
    detail = detail[[date_col, "Close", "1 Gün %", "5 Gün %", "20 Gün %", "60 Gün %"]]
    detail = detail.rename(columns={date_col: "Tarih", "Close": "Giriş Fiyatı"})
    return summary, detail


def render_backtest(symbol):
    st.header("🧪 Geçmiş Performans Testi")
    with st.expander(f"{symbol} için backtest çalıştır", expanded=False):
        if st.button("Backtest'i çalıştır", key=f"backtest_{symbol}"):
            summary, detail = backtest(symbol)
            if summary is None:
                st.warning("Backtest için yeterli geçmiş veri bulunamadı.")
            else:
                st.dataframe(pd.DataFrame([summary]), width="stretch", hide_index=True)
                st.dataframe(detail, width="stretch", hide_index=True)
                st.caption(
                    "Kural: SMA20 > SMA50, fiyat > SMA200 ve RSI 45–70. Sonuçlara komisyon, "
                    "vergi ve fiyat kayması dahil değildir; geçmiş performans geleceği garanti etmez."
                )


def render_portfolio(symbols):
    st.header("💼 Portföy Takibi")
    if "portfolio_editor" not in st.session_state:
        st.session_state.portfolio_editor = pd.DataFrame(
            [{"Hisse": symbols[0], "Adet": 0.0, "Alış Fiyatı": 0.0}]
        )

    edited = st.data_editor(
        st.session_state.portfolio_editor,
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        key="portfolio_input",
    )
    st.session_state.portfolio_editor = edited

    rows = []
    for _, item in edited.iterrows():
        symbol = str(item.get("Hisse", "")).strip().upper()
        try:
            quantity = float(item.get("Adet", 0))
            cost = float(item.get("Alış Fiyatı", 0))
        except (TypeError, ValueError):
            continue
        if not symbol or quantity <= 0 or cost <= 0:
            continue
        history = extended_history(symbol, "5d")
        if history.empty:
            continue
        price = float(history["Close"].iloc[-1])
        value = price * quantity
        invested = cost * quantity
        rows.append(
            {
                "Hisse": symbol,
                "Adet": quantity,
                "Alış": round(cost, 2),
                "Güncel": round(price, 2),
                "Maliyet $": round(invested, 2),
                "Değer $": round(value, 2),
                "K/Z $": round(value - invested, 2),
                "K/Z %": round((value / invested - 1) * 100, 2),
            }
        )

    if rows:
        result = pd.DataFrame(rows)
        total_cost = result["Maliyet $"].sum()
        total_value = result["Değer $"].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam maliyet", f"${total_cost:,.2f}")
        c2.metric("Güncel değer", f"${total_value:,.2f}")
        c3.metric(
            "Toplam K/Z",
            f"${total_value - total_cost:,.2f}",
            f"{(total_value / total_cost - 1) * 100:+.2f}%",
        )
        st.dataframe(result, width="stretch", hide_index=True)
    else:
        st.info("Takip için hisse, adet ve alış fiyatı girin.")


def send_alert(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": message},
        timeout=15,
    )
    response.raise_for_status()
    return True


def render_alerts(final_frame):
    st.header("🔔 Otomatik Alarm Merkezi")
    threshold = st.slider("Telegram alarm eşiği", 50, 90, 70, 1)
    automatic = st.toggle("Telegram alarmları aktif", value=True)
    if final_frame is None or final_frame.empty:
        st.info("Alarm üretmek için final analiz verisi yok.")
        return

    scores = pd.to_numeric(final_frame.get("FINAL"), errors="coerce")
    alerts = final_frame.loc[scores >= threshold, ["Hisse", "FINAL", "Karar"]].copy()
    st.dataframe(alerts, width="stretch", hide_index=True)

    if automatic and not alerts.empty:
        signature = "|".join(
            f"{row['Hisse']}:{row['FINAL']}" for _, row in alerts.iterrows()
        )
        if st.session_state.get("last_alarm_signature") != signature:
            lines = [f"🔔 BORSA ROBOTU ALARMI — eşik {threshold}"]
            lines.extend(
                f"{row['Hisse']} — {row['FINAL']}/100 — {row['Karar']}"
                for _, row in alerts.iterrows()
            )
            try:
                if send_alert("\n".join(lines)):
                    st.session_state.last_alarm_signature = signature
                    st.success("Yeni alarm Telegram'a gönderildi.")
            except Exception as exc:
                st.warning(f"Alarm gönderilemedi: {type(exc).__name__}")


def render_quality(symbols, api_key_present):
    st.header("🩺 Veri Kalitesi")
    history_ok = 0
    for symbol in symbols[:5]:
        if not extended_history(symbol, "5d").empty:
            history_ok += 1
    rows = [
        {"Kaynak": "Yahoo Finance", "Durum": "🟢 Çalışıyor" if history_ok else "🔴 Veri yok", "Kapsam": f"{history_ok}/{min(5, len(symbols))}"},
        {"Kaynak": "Finnhub", "Durum": "🟢 Anahtar hazır" if api_key_present else "🔴 Anahtar yok", "Kapsam": "Fiyat, haber, bilanço"},
        {"Kaynak": "SEC EDGAR", "Durum": "🟢 Etkin", "Kapsam": "XBRL, Form 4, 8-K"},
        {"Kaynak": "Dashboard", "Durum": "🟢 Güncel", "Kapsam": datetime.now().strftime("%Y-%m-%d %H:%M")},
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def _score_change_frame(final_frame):
    current = {
        str(row["Hisse"]): float(row["FINAL"])
        for _, row in final_frame.iterrows()
        if pd.notna(row.get("FINAL"))
    }
    signature = "|".join(f"{key}:{value}" for key, value in sorted(current.items()))

    if "score_snapshot" not in st.session_state:
        st.session_state.score_snapshot = current
        st.session_state.score_signature = signature
        st.session_state.score_deltas = {key: None for key in current}
    elif st.session_state.get("score_signature") != signature:
        previous = st.session_state.score_snapshot
        st.session_state.score_deltas = {
            key: value - previous[key] if key in previous else None
            for key, value in current.items()
        }
        st.session_state.score_snapshot = current
        st.session_state.score_signature = signature

    result = final_frame.copy()
    deltas = st.session_state.get("score_deltas", {})
    result["Puan Değişimi"] = result["Hisse"].map(
        lambda symbol: (
            f"{deltas[symbol]:+.0f}"
            if symbol in deltas and deltas[symbol] is not None
            else "Yeni / ilk tarama"
        )
    )
    return result


def _confidence(row):
    components = ["Teknik", "SEC", "Insider", "8-K", "Haber"]
    available = sum(pd.notna(row.get(column)) for column in components)
    neutral = sum(
        pd.notna(row.get(column)) and float(row.get(column)) == 50
        for column in components
    )
    if available == len(components) and neutral <= 1:
        return "🟢 YÜKSEK"
    if available >= 4 and neutral <= 3:
        return "🟡 ORTA"
    return "🟠 DÜŞÜK"


def render_light_tools(final_frame):
    st.header("⚡ Hafif Analiz Merkezi")
    st.caption("Bu bölüm mevcut sonuçları kullanır; yeni veri sorgusu yapmaz.")
    if final_frame is None or final_frame.empty:
        st.info("Hafif analiz için TOP 5 sonuçları henüz oluşmadı.")
        return

    data = _score_change_frame(final_frame)
    data["Güven"] = data.apply(_confidence, axis=1)

    min_score = st.slider("Minimum FINAL puanı", 0, 100, 50, 1)
    decisions = list(data["Karar"].dropna().unique())
    selected_decisions = st.multiselect(
        "Karar filtresi",
        decisions,
        default=decisions,
    )
    filtered = data[
        (pd.to_numeric(data["FINAL"], errors="coerce") >= min_score)
        & data["Karar"].isin(selected_decisions)
    ]
    display_columns = [
        column
        for column in [
            "Sıra", "Hisse", "Fiyat", "Teknik", "SEC", "Insider", "8-K",
            "Haber", "Katalizör", "FINAL", "Puan Değişimi", "Güven", "Karar"
        ]
        if column in filtered.columns
    ]
    st.dataframe(filtered[display_columns], width="stretch", hide_index=True)

    csv_data = filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Filtrelenmiş sonuçları CSV indir",
        data=csv_data,
        file_name=f"borsa_robotu_{datetime.now():%Y%m%d_%H%M}.csv",
        mime="text/csv",
    )

    st.subheader("🧠 Puan Açıklaması")
    explain_symbol = st.selectbox(
        "Açıklanacak hisse", data["Hisse"].tolist(), key="explain_symbol"
    )
    row = data[data["Hisse"] == explain_symbol].iloc[0]
    contributions = pd.DataFrame(
        [
            {"Bileşen": "Teknik", "Puan": row.get("Teknik"), "Ağırlık": "%35", "Katkı": round(float(row.get("Teknik", 50)) * 0.35, 1)},
            {"Bileşen": "SEC", "Puan": row.get("SEC"), "Ağırlık": "%25", "Katkı": round(float(row.get("SEC", 50)) * 0.25, 1)},
            {"Bileşen": "Insider", "Puan": row.get("Insider"), "Ağırlık": "%15", "Katkı": round(float(row.get("Insider", 50)) * 0.15, 1)},
            {"Bileşen": "Katalizör", "Puan": row.get("Katalizör"), "Ağırlık": "%25", "Katkı": round(float(row.get("Katalizör", 50)) * 0.25, 1)},
        ]
    )
    st.dataframe(contributions, width="stretch", hide_index=True)
    strongest = contributions.loc[contributions["Katkı"].idxmax()]
    weakest = contributions.loc[contributions["Katkı"].idxmin()]
    st.info(
        f"{explain_symbol} için en güçlü katkı {strongest['Bileşen']}, "
        f"en zayıf katkı {weakest['Bileşen']}. Veri güveni: {row['Güven']}."
    )

    st.subheader("⚖️ Hızlı Karşılaştırma")
    compare_symbols = st.multiselect(
        "En fazla 3 hisse seçin",
        data["Hisse"].tolist(),
        default=data["Hisse"].tolist()[:2],
        max_selections=3,
    )
    compare_columns = [
        column for column in ["Hisse", "Teknik", "SEC", "Insider", "8-K", "Haber", "FINAL", "Güven", "Karar"]
        if column in data.columns
    ]
    st.dataframe(
        data[data["Hisse"].isin(compare_symbols)][compare_columns],
        width="stretch",
        hide_index=True,
    )


def render_extras(symbols, final_frame, api_key_present=False):
    if not symbols:
        return
    st.divider()
    st.title("🧰 Gelişmiş Yatırım Araçları")
    section = st.radio(
        "Araç seçin",
        ["Hafif Araçlar", "Kurumsal Motor", "Risk", "Detay & Grafik", "Backtest", "Portföy", "Alarmlar", "Veri Kalitesi"],
        horizontal=True,
        label_visibility="collapsed",
    )
    if section == "Kurumsal Motor":
        from institutional_engine import render_institutional_engine

        render_institutional_engine(final_frame)
    elif section == "Hafif Araçlar":
        render_light_tools(final_frame)
    elif section == "Risk":
        render_risk(symbols)
    elif section == "Detay & Grafik":
        render_detail(symbols)
    elif section == "Backtest":
        selected = st.selectbox("Backtest hissesi", symbols, key="backtest_symbol")
        render_backtest(selected)
    elif section == "Portföy":
        render_portfolio(symbols)
    elif section == "Alarmlar":
        render_alerts(final_frame)
    else:
        render_quality(symbols, api_key_present)
