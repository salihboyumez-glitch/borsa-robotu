import unittest
from unittest.mock import patch

import price_movement_alerts as movement


def quote(percent, high=103, low=97):
    return {
        "symbol": "IBM", "price": 103, "change": 3, "percent": percent,
        "previous_close": 100, "high": high, "low": low,
    }


class MovementTests(unittest.TestCase):
    def setUp(self):
        self.state = {"date": "2026-09-04", "sent": {}}

    @patch.object(movement.cfg, "HAREKET_GUN_ICI_YAKALA", False)
    def test_reports_highest_crossed_threshold(self):
        alert = movement.evaluate_quote(quote(5.7), self.state)
        self.assertEqual(alert["threshold"], 5.0)

    @patch.object(movement.cfg, "HAREKET_GUN_ICI_YAKALA", False)
    def test_does_not_repeat_same_threshold(self):
        self.state["sent"]["IBM_up"] = 5.0
        self.assertIsNone(movement.evaluate_quote(quote(5.7), self.state))

    @patch.object(movement.cfg, "HAREKET_GUN_ICI_YAKALA", False)
    def test_reports_next_threshold(self):
        self.state["sent"]["IBM_up"] = 3.0
        self.assertEqual(movement.evaluate_quote(quote(5.7), self.state)["threshold"], 5.0)

    def test_detects_recovered_intraday_drop(self):
        alert = movement.evaluate_quote(quote(-0.5, high=101, low=94), self.state)
        self.assertEqual(alert["evaluated_percent"], -6.0)
        self.assertTrue(alert["intraday_extreme"])

    @patch.object(movement.cfg, "HAREKET_GUN_ICI_YAKALA", False)
    def test_tracks_up_and_down_separately(self):
        self.state["sent"]["IBM_up"] = 5.0
        self.assertIsNotNone(movement.evaluate_quote(quote(-5.2), self.state))


if __name__ == "__main__":
    unittest.main()
