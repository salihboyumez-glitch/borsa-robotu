import pandas as pd

from dashboard_extras import _zones_from_history


def test_zones_are_ordered_and_include_stop():
    closes = [100 + i * 0.5 for i in range(30)]
    frame = pd.DataFrame(
        {
            "Close": closes,
            "High": [value + 1 for value in closes],
            "Low": [value - 1 for value in closes],
            "Volume": [1000] * 30,
        }
    )
    zones = _zones_from_history(frame)
    assert zones is not None
    assert zones["Zarar Kes"] < zones["Alım Bölgesi Alt"]
    assert zones["Alım Bölgesi Alt"] <= zones["Alım Bölgesi Üst"]
    assert zones["Alım Bölgesi Üst"] <= zones["Satış Bölgesi Alt"]
    assert zones["Satış Bölgesi Alt"] <= zones["Satış Bölgesi Üst"]


def test_zones_require_enough_history():
    frame = pd.DataFrame({"Close": [100], "High": [101], "Low": [99]})
    assert _zones_from_history(frame) is None
