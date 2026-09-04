"""2020-2024 eğitim ve 2025+ test ayrımıyla fırsat modelini kalibre eder."""

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from opportunity_scanner import EXCLUDED_FROM_TOP5, score_opportunities
from watchlist import BASE_WATCHLIST


OUTPUT = Path(__file__).with_name("model_calibration.json")
REPORT_OUTPUT = Path(__file__).with_name("model_calibration_report.md")
START = "2019-01-01"
TRAIN_END = "2024-12-31"
TEST_START = "2025-01-01"


def _frame(batch, symbol):
    if not isinstance(batch, pd.DataFrame) or batch.empty:
        return pd.DataFrame()
    if isinstance(batch.columns, pd.MultiIndex):
        if symbol in batch.columns.get_level_values(0):
            return batch[symbol].copy()
        if symbol in batch.columns.get_level_values(1):
            return batch.xs(symbol, axis=1, level=1).copy()
    return pd.DataFrame()


def _rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    return 100 - 100 / (1 + gain / loss.replace(0, np.nan))


def _atr(frame, period=14):
    previous = frame["Close"].shift(1)
    ranges = pd.concat(
        [frame["High"] - frame["Low"], (frame["High"] - previous).abs(), (frame["Low"] - previous).abs()],
        axis=1,
    )
    return ranges.max(axis=1).rolling(period).mean()


def symbol_history(symbol, frame):
    frame = frame.dropna(subset=["Close", "High", "Low"]).copy()
    if len(frame) < 220:
        return pd.DataFrame()
    close = frame["Close"].astype(float)
    high = frame["High"].astype(float)
    low = frame["Low"].astype(float)
    volume = frame["Volume"].fillna(0).astype(float)
    average_volume = volume.rolling(20).mean()
    result = pd.DataFrame(index=frame.index)
    result["Hisse"] = symbol
    result["Veri Tarihi"] = pd.Index(frame.index).map(lambda value: pd.Timestamp(value).date().isoformat())
    result["Fiyat"] = close
    result["Önceki Kapanış"] = close.shift(1)
    result["Günlük %"] = close.pct_change() * 100
    result["3 Gün %"] = close.pct_change(3) * 100
    result["Haftalık %"] = close.pct_change(5) * 100
    result["20 Gün %"] = close.pct_change(20) * 100
    result["SMA20 Fark %"] = (close / close.rolling(20).mean() - 1) * 100
    result["SMA50 Fark %"] = (close / close.rolling(50).mean() - 1) * 100
    result["RSI"] = _rsi(close)
    result["Hacim Oranı"] = volume / average_volume.replace(0, np.nan)
    result["Ort Günlük Hacim"] = average_volume
    result["Volatilite %"] = close.pct_change().rolling(20).std() * np.sqrt(252) * 100
    result["Günlük $ Hacim"] = (close * volume).rolling(20).mean()
    result["Zirveye Uzaklık %"] = (close / high.rolling(252, min_periods=65).max() - 1) * 100
    result["ATR"] = _atr(frame)
    result["20G Destek"] = low.rolling(20).min()
    complete_future = close.shift(-3).notna()
    result["future_rise"] = np.where(complete_future, (close.shift(-3) > close).astype(float), np.nan)
    for day in range(1, 4):
        result[f"future_high_{day}"] = high.shift(-day)
        result[f"future_low_{day}"] = low.shift(-day)
    return result.replace([np.inf, -np.inf], np.nan).dropna()


def add_barrier_outcome(scored):
    """Üç günde hedefe stop öncesi ulaşmayı, aynı gün çakışmasında temkinli sayar."""
    if scored.empty:
        return scored
    scored = scored.copy()
    unresolved = pd.Series(True, index=scored.index)
    outcome = pd.Series(0.0, index=scored.index)
    for day in range(1, 4):
        stop_hit = scored[f"future_low_{day}"] <= scored["Stop"]
        target_hit = scored[f"future_high_{day}"] >= scored["Hedef 1"]
        won = unresolved & target_hit & ~stop_hit
        lost = unresolved & stop_hit
        outcome.loc[won] = 1.0
        unresolved.loc[won | lost] = False
    scored["future_jump"] = outcome
    return scored


def market_regimes(spy):
    close = spy["Close"].astype(float)
    fast = close.rolling(50).mean()
    slow = close.rolling(200).mean()
    ratio = fast / slow
    return pd.Series(np.where(ratio > 1.02, "bull", np.where(ratio < 0.98, "bear", "sideways")), index=spy.index)


def wilson(successes, count, z=1.96):
    if count <= 0:
        return 0.0, 0.0
    p = successes / count
    denominator = 1 + z * z / count
    center = (p + z * z / (2 * count)) / denominator
    margin = z * np.sqrt((p * (1 - p) + z * z / (4 * count)) / count) / denominator
    return 100 * (center - margin), 100 * (center + margin)


def stats(frame):
    n = len(frame)
    if not n:
        return {"n": 0, "rise_rate": 0.0, "jump_rate": 0.0, "rise_ci_low": 0.0, "rise_ci_high": 0.0}
    low, high = wilson(float(frame["future_rise"].sum()), n)
    return {
        "n": n,
        "rise_rate": round(float(frame["future_rise"].mean() * 100), 1),
        "jump_rate": round(float(frame["future_jump"].mean() * 100), 1),
        "rise_ci_low": round(low, 1),
        "rise_ci_high": round(high, 1),
    }


def write_report(payload):
    overall = payload["overall"]
    baseline = payload["baseline"]
    lines = [
        "# Fırsat modeli doğrulama raporu",
        "",
        f"Üretim zamanı (UTC): {payload['generated_at']}",
        "",
        "## Ayrı test sonucu",
        "",
        f"- Model sinyali: %{overall['rise_rate']:.1f} (sinyalsiz ortalama: %{baseline['rise_rate']:.1f}, n={overall['n']})",
        f"- %95 güven aralığı: %{overall['rise_ci_low']:.1f}–%{overall['rise_ci_high']:.1f}",
        f"- Üç günde stop öncesi 2R hedef başarısı: %{overall['jump_rate']:.1f}",
        "",
        "## Piyasa rejimleri",
        "",
        "| Rejim | 3G yükseliş | n | %95 güven aralığı |",
        "|---|---:|---:|---:|",
    ]
    regime_names = {"bull": "Yükselen", "sideways": "Yatay", "bear": "Düşen"}
    for key in ("bull", "sideways", "bear"):
        item = payload["regimes"].get(key, stats(pd.DataFrame()))
        lines.append(
            f"| {regime_names[key]} | %{item['rise_rate']:.1f} | {item['n']} | "
            f"%{item['rise_ci_low']:.1f}–%{item['rise_ci_high']:.1f} |"
        )
    lines.extend(
        [
            "",
            "## Kalibrasyon kontrolü",
            "",
            "| Modelin eğitimde söylediği aralık | Eğitim ortalaması | Testte gerçekleşen | n | %95 güven aralığı |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for item in payload["calibration_bins"]:
        lines.append(
            f"| %{item['predicted_range']} | %{item['trained_mean']:.1f} | %{item['rise_rate']:.1f} | "
            f"{item['n']} | %{item['rise_ci_low']:.1f}–%{item['rise_ci_high']:.1f} |"
        )
    lines.extend(
        [
            "",
            "## Yöntem",
            "",
            f"- Eğitim/kalibrasyon dönemi: {payload['training_period']}",
            f"- Hiç dokunulmamış test dönemi: {payload['test_period']}",
            f"- {payload['notes']}",
            "- n<30 olan gruplar Telegram çıktısında olasılık olarak gösterilmez.",
            "",
        ]
    )
    REPORT_OUTPUT.write_text("\n".join(lines), encoding="utf-8")


def main():
    symbols = list(dict.fromkeys(BASE_WATCHLIST))
    batch = yf.download(symbols, start=START, interval="1d", group_by="ticker", auto_adjust=True, threads=True, progress=False)
    histories = [symbol_history(symbol, _frame(batch, symbol)) for symbol in symbols]
    universe = pd.concat([item for item in histories if not item.empty], ignore_index=True)
    spy_batch = yf.download("SPY", start=START, interval="1d", auto_adjust=True, progress=False)
    if isinstance(spy_batch.columns, pd.MultiIndex):
        spy_batch.columns = spy_batch.columns.get_level_values(0)
    regimes = market_regimes(spy_batch)
    regime_by_date = {pd.Timestamp(index).date().isoformat(): value for index, value in regimes.items()}

    signals = []
    baselines = []
    for date, daily in universe.groupby("Veri Tarihi", sort=True):
        if date < "2020-01-01":
            continue
        scored = score_opportunities(symbols, raw_data=daily)
        if scored.empty:
            continue
        scored = add_barrier_outcome(scored)
        scored["regime"] = regime_by_date.get(date, "sideways")
        scored["score_bin"] = (scored["Fırsat Puanı"].clip(0, 99) // 10 * 10).astype(int)
        eligible = scored[~scored["Hisse"].isin(EXCLUDED_FROM_TOP5)].copy()
        top = eligible.head(5).copy()
        signals.append(top)
        baselines.append(eligible.iloc[5:].copy())

    signal_data = pd.concat(signals, ignore_index=True)
    baseline_data = pd.concat(baselines, ignore_index=True)
    train = signal_data[signal_data["Veri Tarihi"] <= TRAIN_END].copy()
    test = signal_data[signal_data["Veri Tarihi"] >= TEST_START].copy()
    baseline_test = baseline_data[baseline_data["Veri Tarihi"] >= TEST_START].copy()

    train_rates = train.groupby("score_bin")["future_rise"].mean().to_dict()
    test["trained_probability"] = test["score_bin"].map(train_rates) * 100
    test["calibration_bin"] = (test["trained_probability"].fillna(-1).clip(0, 99) // 10 * 10).astype(int)

    score_bins = {}
    for bucket, frame in test.groupby("score_bin"):
        score_bins[f"{int(bucket)}-{int(bucket) + 9}"] = stats(frame)
    regime_stats = {regime: stats(frame) for regime, frame in test.groupby("regime")}
    calibration_table = []
    for bucket, frame in test[test["trained_probability"].notna()].groupby("calibration_bin"):
        item = stats(frame)
        item["predicted_range"] = f"{int(bucket)}-{int(bucket) + 9}"
        item["trained_mean"] = round(float(frame["trained_probability"].mean()), 1)
        calibration_table.append(item)

    payload = {
        "method_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "training_period": "2020-01-01..2024-12-31",
        "test_period": f"2025-01-01..{datetime.now(timezone.utc).date().isoformat()}",
        "symbols_requested": len(symbols),
        "overall": stats(test),
        "baseline": stats(baseline_test),
        "regimes": regime_stats,
        "score_bins": score_bins,
        "calibration_bins": calibration_table,
        "notes": "3 işlem günü sonrası pozitif kapanış; işlem başarısı, 3 günde stopa değmeden önce 2R hedefe ulaşmadır. Aynı gün iki bariyer de görülürse kayıp, zaman aşımı başarısız sayılır. Test verisi eğitimden ayrıdır.",
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(payload)
    print(json.dumps({"signals_test": len(test), "baseline_test": len(baseline_test), "score_bins": len(score_bins)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
