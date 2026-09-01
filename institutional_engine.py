import numpy as np
import pandas as pd
import streamlit as st

from dashboard_extras import extended_history


def _clip(value, low=0, high=100):
    return float(max(low, min(high, value)))


def _percentile_score(value, bad, good):
    if pd.isna(value) or good == bad:
        return 50.0
    return _clip((float(value) - bad) / (good - bad) * 100)


@st.cache_data(ttl=900)
def market_regime():
    spy = extended_history("SPY", "1y")
    qqq = extended_history("QQQ", "1y")
    if spy.empty or qqq.empty or len(spy) < 200 or len(qqq) < 200:
        return {
            "Rejim": "⚪ BELİRSİZ",
            "Risk Bütçesi %": 40,
            "Puan": 40,
            "Açıklama": "Piyasa rejimi için yeterli veri yok; temkinli bütçe kullanılıyor.",
        }

    def state(frame):
        close = frame["Close"]
        last = float(close.iloc[-1])
        sma50 = float(close.rolling(50).mean().iloc[-1])
        sma200 = float(close.rolling(200).mean().iloc[-1])
        ret_63 = last / float(close.iloc[-64]) - 1
        vol = float(close.pct_change().tail(20).std() * np.sqrt(252))
        return last, sma50, sma200, ret_63, vol

    spy_state = state(spy)
    qqq_state = state(qqq)
    breadth = sum(
        [
            spy_state[0] > spy_state[1] > spy_state[2],
            qqq_state[0] > qqq_state[1] > qqq_state[2],
            spy_state[3] > 0,
            qqq_state[3] > 0,
        ]
    )
    high_vol = max(spy_state[4], qqq_state[4]) > 0.28

    if breadth == 4 and not high_vol:
        return {
            "Rejim": "🟢 RİSK AÇIK",
            "Risk Bütçesi %": 100,
            "Puan": 85,
            "Açıklama": "SPY ve QQQ, 50/200 günlük trendlerin üzerinde; momentum pozitif.",
        }
    if breadth >= 2:
        return {
            "Rejim": "🟡 SEÇİCİ",
            "Risk Bütçesi %": 60,
            "Puan": 60,
            "Açıklama": "Piyasa sinyalleri karışık; yalnızca en güçlü adaylarda küçük pozisyon.",
        }
    return {
        "Rejim": "🔴 RİSK KAPALI",
        "Risk Bütçesi %": 25,
        "Puan": 25,
        "Açıklama": "Ana endeks trendleri zayıf; nakit oranı yükseltilmeli ve yeni risk azaltılmalı.",
    }


def price_factors(symbol):
    frame = extended_history(symbol, "1y")
    if frame.empty or len(frame) < 130:
        return None

    close = frame["Close"].astype(float)
    volume = frame["Volume"].astype(float)
    returns = close.pct_change().dropna()
    last = float(close.iloc[-1])
    sma50 = float(close.rolling(50).mean().iloc[-1])
    sma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else np.nan
    high_52 = float(close.max())
    momentum_12_1 = float(close.iloc[-22] / close.iloc[0] - 1)
    momentum_6 = float(last / close.iloc[-126] - 1)
    momentum_1 = float(last / close.iloc[-22] - 1)
    volatility = float(returns.tail(63).std() * np.sqrt(252))
    downside = float(returns.tail(63).clip(upper=0).std() * np.sqrt(252))
    drawdown = float(last / high_52 - 1)
    dollar_volume = float((close * volume).tail(20).mean())

    momentum_score = (
        _percentile_score(momentum_12_1, -0.20, 0.60) * 0.50
        + _percentile_score(momentum_6, -0.15, 0.40) * 0.30
        + _percentile_score(momentum_1, -0.10, 0.15) * 0.20
    )
    trend_score = 50
    trend_score += 20 if last > sma50 else -20
    if pd.notna(sma200):
        trend_score += 20 if last > sma200 else -20
        trend_score += 10 if sma50 > sma200 else -10
    trend_score = _clip(trend_score)

    volatility_score = _percentile_score(volatility, 0.90, 0.18)
    downside_score = _percentile_score(downside, 0.65, 0.10)
    drawdown_score = _percentile_score(drawdown, -0.50, -0.03)
    risk_score = volatility_score * 0.40 + downside_score * 0.30 + drawdown_score * 0.30

    return {
        "Fiyat": last,
        "12-1 Momentum %": momentum_12_1 * 100,
        "6A Momentum %": momentum_6 * 100,
        "1A Momentum %": momentum_1 * 100,
        "Momentum": round(momentum_score),
        "Trend": round(trend_score),
        "Risk Kalitesi": round(risk_score),
        "Yıllık Volatilite %": volatility * 100,
        "Aşağı Yönlü Vol %": downside * 100,
        "52H Zirveye Uzaklık %": drawdown * 100,
        "Ort. Günlük $ Hacim": dollar_volume,
        "Getiriler": returns.tail(126),
    }


def institutional_rows(final_frame, regime):
    rows = []
    returns_map = {}
    if final_frame is None or final_frame.empty:
        return pd.DataFrame(), returns_map

    for _, base in final_frame.iterrows():
        symbol = str(base["Hisse"])
        factors = price_factors(symbol)
        if not factors:
            continue

        quality = float(base.get("SEC", 50))
        insider = float(base.get("Insider", 50))
        catalyst = float(base.get("Katalizör", 50))
        technical = float(base.get("Teknik", 50))

        # Kalite + fiyat davranışı + olay katalizörü; rejim nihai risk kapısıdır.
        score = round(
            quality * 0.22
            + factors["Momentum"] * 0.22
            + factors["Trend"] * 0.14
            + factors["Risk Kalitesi"] * 0.16
            + catalyst * 0.16
            + insider * 0.06
            + technical * 0.04
        )

        gates = []
        if factors["Fiyat"] < 5:
            gates.append("Fiyat < $5")
        if factors["Ort. Günlük $ Hacim"] < 10_000_000:
            gates.append("Likidite < $10M")
        if factors["Yıllık Volatilite %"] > 90:
            gates.append("Aşırı volatilite")
        if factors["52H Zirveye Uzaklık %"] < -45:
            gates.append("Derin düşüş trendi")
        if factors["Trend"] < 40:
            gates.append("Trend zayıf")

        surprise = (
            catalyst >= 65
            and factors["Momentum"] >= 58
            and quality >= 55
            and factors["1A Momentum %"] < 25
        )

        if gates:
            decision = "⛔ ALIM YOK"
        elif regime["Puan"] < 40:
            decision = "🔴 BEKLE / ÇOK KÜÇÜK"
        elif score >= 78:
            decision = "🟢 KOMİTE ONAY ADAYI"
        elif score >= 68:
            decision = "🟡 İZLE / KADEMELİ"
        else:
            decision = "⚪ BEKLE"

        rows.append(
            {
                "Hisse": symbol,
                "Kurumsal Puan": score,
                "Kalite": round(quality),
                "Momentum": factors["Momentum"],
                "Trend": factors["Trend"],
                "Risk Kalitesi": factors["Risk Kalitesi"],
                "Katalizör": round(catalyst),
                "Volatilite %": round(factors["Yıllık Volatilite %"], 1),
                "Zirveye Uzaklık %": round(factors["52H Zirveye Uzaklık %"], 1),
                "Sürpriz Potansiyeli": "✨ VAR" if surprise else "—",
                "Risk Kapısı": " | ".join(gates) if gates else "✅ Geçti",
                "Komite Kararı": decision,
            }
        )
        returns_map[symbol] = factors["Getiriler"]

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values("Kurumsal Puan", ascending=False).reset_index(drop=True)
        result.insert(0, "Sıra", range(1, len(result) + 1))
    return result, returns_map


def portfolio_weights(scores, returns_map, regime_budget):
    eligible = scores[
        scores["Komite Kararı"].isin(["🟢 KOMİTE ONAY ADAYI", "🟡 İZLE / KADEMELİ"])
    ].copy()
    if eligible.empty:
        return pd.DataFrame()

    raw = []
    selected_returns = {}
    for _, row in eligible.iterrows():
        symbol = row["Hisse"]
        series = returns_map.get(symbol)
        if series is None or series.empty:
            continue
        annual_vol = float(series.std() * np.sqrt(252))
        inverse_vol = 1 / max(annual_vol, 0.10)
        conviction = max(0.25, (float(row["Kurumsal Puan"]) - 55) / 30)
        raw.append((symbol, inverse_vol * conviction, annual_vol))
        selected_returns[symbol] = series

    if not raw:
        return pd.DataFrame()

    raw_total = sum(item[1] for item in raw)
    budget = regime_budget / 100
    rows = []
    accepted = []
    for symbol, raw_weight, annual_vol in sorted(raw, key=lambda item: item[1], reverse=True):
        correlation_warning = "—"
        for existing in accepted:
            joined = pd.concat([selected_returns[symbol], selected_returns[existing]], axis=1).dropna()
            if len(joined) > 30 and float(joined.corr().iloc[0, 1]) > 0.80:
                correlation_warning = f"⚠️ {existing} ile yüksek korelasyon"
                raw_weight *= 0.50
                break
        accepted.append(symbol)
        weight = min(0.25, raw_weight / raw_total * budget)
        rows.append(
            {
                "Hisse": symbol,
                "Önerilen Azami Ağırlık %": round(weight * 100, 1),
                "Yıllık Volatilite %": round(annual_vol * 100, 1),
                "Korelasyon Kontrolü": correlation_warning,
            }
        )

    invested = sum(row["Önerilen Azami Ağırlık %"] for row in rows)
    rows.append(
        {
            "Hisse": "NAKİT / KISA VADE",
            "Önerilen Azami Ağırlık %": round(max(0, 100 - invested), 1),
            "Yıllık Volatilite %": 0.0,
            "Korelasyon Kontrolü": "Rejim ve risk tamponu",
        }
    )
    return pd.DataFrame(rows)


def render_institutional_engine(final_frame):
    st.header("🏛️ Kurumsal Yatırım Komitesi")
    st.warning(
        "Bu motor olasılık ve risk disiplinini iyileştirmek için tasarlanmıştır; kârı garanti "
        "etmez. Gerçek para öncesinde paper-trading ve ileri dönem doğrulaması gerekir."
    )
    regime = market_regime()
    c1, c2, c3 = st.columns(3)
    c1.metric("Piyasa rejimi", regime["Rejim"])
    c2.metric("Azami risk bütçesi", f"%{regime['Risk Bütçesi %']}")
    c3.metric("Rejim puanı", f"{regime['Puan']}/100")
    st.caption(regime["Açıklama"])

    with st.spinner("Komite risk ve faktör kontrollerini hesaplıyor..."):
        scores, returns_map = institutional_rows(final_frame, regime)
    if scores.empty:
        st.info("Kurumsal motor için yeterli aday verisi bulunamadı.")
        return

    st.subheader("Komite sıralaması")
    st.dataframe(scores, width="stretch", hide_index=True)

    st.subheader("Volatilite kontrollü sermaye planı")
    weights = portfolio_weights(scores, returns_map, regime["Risk Bütçesi %"])
    if weights.empty:
        st.info("Risk kapılarından geçen alım adayı yok; nakitte bekleme öncelikli.")
    else:
        st.dataframe(weights, width="stretch", hide_index=True)

    st.info(
        "Süreç: likidite/risk kapısı → kalite → 12-1 ve 6 aylık momentum → trend → "
        "8-K/haber/insider katalizörü → volatilite ve korelasyon kontrollü ağırlık. "
        "Tek hisse ağırlığı %25 ile sınırlandırılır."
    )
