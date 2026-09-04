import json
from pathlib import Path


CALIBRATION_FILE = Path(__file__).with_name("model_calibration.json")
MIN_SAMPLE_SIZE = 30


def load_calibration():
    try:
        payload = json.loads(CALIBRATION_FILE.read_text(encoding="utf-8"))
        return payload if payload.get("method_version") == 1 else {}
    except Exception:
        return {}


def score_bin(score):
    lower = max(0, min(90, int(float(score) // 10) * 10))
    return f"{lower}-{lower + 9}"


def calibrated_lines(row, calibration=None):
    calibration = calibration if calibration is not None else load_calibration()
    bucket = calibration.get("score_bins", {}).get(score_bin(row.get("Fırsat Puanı", 0)), {})
    sample = int(bucket.get("n", 0) or 0)
    baseline = calibration.get("baseline", {})
    if sample < MIN_SAMPLE_SIZE or not baseline:
        return ["📐 Geçmiş test olasılığı: yeterli bağımsız test örneği henüz yok"]

    rise = float(bucket.get("rise_rate", 0))
    jump = float(bucket.get("jump_rate", 0))
    base_rate = float(baseline.get("rise_rate", 0))
    ci_low = float(bucket.get("rise_ci_low", 0))
    ci_high = float(bucket.get("rise_ci_high", 0))
    return [
        f"3G yükseliş: %{rise:.1f} (sinyalsiz ortalama: %{base_rate:.1f}, n={sample})",
        f"%95 güven aralığı: %{ci_low:.1f}–%{ci_high:.1f} | 3G stop öncesi 2R hedef: %{jump:.1f}",
    ]


def regime_summary_line(calibration=None):
    calibration = calibration if calibration is not None else load_calibration()
    regimes = calibration.get("regimes", {})
    labels = (("bull", "Yükselen"), ("sideways", "Yatay"), ("bear", "Düşen"))
    parts = []
    for key, label in labels:
        item = regimes.get(key, {})
        if int(item.get("n", 0) or 0) >= MIN_SAMPLE_SIZE:
            parts.append(f"{label} %{float(item['rise_rate']):.1f} (n={int(item['n'])})")
    return " | ".join(parts)
