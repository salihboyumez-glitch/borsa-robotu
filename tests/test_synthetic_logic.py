"""İnternet kullanmadan fırsat modelinin temel matematiğini doğrular."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backtest_calibration import add_barrier_outcome, symbol_history
from model_calibration import calibrated_lines, regime_summary_line
from opportunity_scanner import TARGET_1_R, _levels_from_raw, score_opportunities


def fake_prices(count=1200, seed=7):
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0006, 0.018, count)
    close = 90 * np.exp(np.cumsum(returns))
    high = close * (1 + np.abs(rng.normal(0, 0.010, count)))
    low = close * (1 - np.abs(rng.normal(0, 0.010, count)))
    opening = close * (1 + rng.normal(0, 0.005, count))
    volume = rng.lognormal(15, 0.45, count)
    index = pd.bdate_range("2020-01-01", periods=count)
    return pd.DataFrame(
        {"Open": opening, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=index,
    )


def test_indicators_and_future_boundary():
    prices = fake_prices()
    metrics = symbol_history("TEST", prices)
    assert not metrics.empty
    assert metrics["RSI"].between(0, 100).all()
    assert (metrics["ATR"] > 0).all()
    # Son üç satırın sonucu henüz bilinemez; geçmiş başarıya katılmamalıdır.
    assert metrics["Veri Tarihi"].max() == prices.index[-4].date().isoformat()


def test_levels_keep_reward_risk_from_worst_entry():
    levels = _levels_from_raw({"Fiyat": 100.0, "20G Destek": 98.0, "ATR": 2.5})
    reward_risk = (levels["Hedef 1"] - levels["Alım Üst"]) / (
        levels["Alım Üst"] - levels["Stop"]
    )
    assert abs(reward_risk - TARGET_1_R) < 0.01
    assert levels["Stop"] < levels["Alım Alt"] < levels["Alım Üst"] < levels["Hedef 1"] < levels["Hedef 2"]


def test_scored_rows_have_valid_trade_order():
    histories = []
    for number in range(40):
        frame = symbol_history(f"T{number:02d}", fake_prices(seed=number + 10))
        histories.append(frame.iloc[-1])
    scored = score_opportunities([row["Hisse"] for row in histories], raw_data=pd.DataFrame(histories))
    assert not scored.empty
    assert (scored["Stop"] < scored["Alım Alt"]).all()
    assert (scored["Alım Alt"] < scored["Alım Üst"]).all()
    assert (scored["Alım Üst"] < scored["Hedef 1"]).all()
    assert (scored["Hedef 1"] < scored["Hedef 2"]).all()


def test_calibration_message_contains_context_and_sample_size():
    calibration = {
        "baseline": {"rise_rate": 54.0},
        "score_bins": {
            "80-89": {
                "n": 500,
                "rise_rate": 67.0,
                "jump_rate": 24.0,
                "rise_ci_low": 62.8,
                "rise_ci_high": 71.0,
            }
        },
        "regimes": {
            "bull": {"n": 180, "rise_rate": 74.0},
            "sideways": {"n": 95, "rise_rate": 58.0},
            "bear": {"n": 60, "rise_rate": 41.0},
        },
    }
    lines = calibrated_lines({"Fırsat Puanı": 85}, calibration)
    assert "sinyalsiz ortalama: %54.0, n=500" in lines[0]
    assert "%95 güven aralığı" in lines[1]
    regimes = regime_summary_line(calibration)
    assert "Yükselen %74.0 (n=180)" in regimes
    assert "Düşen %41.0 (n=60)" in regimes


def test_barrier_order_is_conservative():
    rows = pd.DataFrame(
        [
            {"Stop": 95.0, "Hedef 1": 110.0, "future_low_1": 96.0, "future_high_1": 111.0,
             "future_low_2": 96.0, "future_high_2": 108.0, "future_low_3": 96.0, "future_high_3": 108.0},
            {"Stop": 95.0, "Hedef 1": 110.0, "future_low_1": 94.0, "future_high_1": 111.0,
             "future_low_2": 96.0, "future_high_2": 111.0, "future_low_3": 96.0, "future_high_3": 111.0},
            {"Stop": 95.0, "Hedef 1": 110.0, "future_low_1": 96.0, "future_high_1": 109.0,
             "future_low_2": 96.0, "future_high_2": 109.0, "future_low_3": 96.0, "future_high_3": 109.0},
        ]
    )
    assert add_barrier_outcome(rows)["future_jump"].tolist() == [1.0, 0.0, 0.0]


if __name__ == "__main__":
    tests = [
        test_indicators_and_future_boundary,
        test_levels_keep_reward_risk_from_worst_entry,
        test_scored_rows_have_valid_trade_order,
        test_calibration_message_contains_context_and_sample_size,
        test_barrier_order_is_conservative,
    ]
    for test in tests:
        test()
        print(f"GEÇTİ: {test.__name__}")
    print("TÜM SENTETİK TESTLER GEÇTİ")
