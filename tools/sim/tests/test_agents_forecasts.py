"""Session 09 — Forecasting: transparent trend models stored
with their inputs, then scored against the actual outcome when
the horizon arrives (forecast != outcome; both recorded).
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))

from tools.sim import agents as agents_mod  # noqa: E402
from tools.sim.tests.common import (data, make_person,  # noqa: E402
                                    make_store, rng)

GM = 480
MONTH = 30 * 1440


class TestForecasts(unittest.TestCase):
    def setUp(self):
        self.store = make_store()
        self.data = data()
        self.r = rng()
        for i in range(5):
            make_person(self.store, age=25 + i, first=f"Fc{i}",
                        game_minutes=GM, r=self.r)
        self.store.commit()

    def tearDown(self):
        self.store.close()

    def _congestion_stat(self, month, value):
        self.store.insert(
            "transport_statistics", scope="rupsha_city",
            month_index=month,
            statistics=json.dumps(
                {"trips": 100, "max_congestion_factor": value}),
            game_minutes=GM + month * MONTH)

    def test_population_forecast_created_then_scored(self):
        out = agents_mod.forecasts_pass(self.store, self.data, 1,
                                        GM + MONTH)
        self.assertGreaterEqual(out["created"], 1)
        f = self.store.row(
            "SELECT * FROM forecasts WHERE kind = 'population'")
        self.assertEqual(f["status"], "open")
        self.assertEqual(json.loads(f["predicted"])["value"], 5.0)
        inputs = json.loads(f["inputs"])
        self.assertEqual(inputs["population"], 5)
        self.assertEqual(inputs["monthly_net_series"], [0])
        # A birth arrives; next month the forecast is scored.
        make_person(self.store, age=0, first="New",
                    game_minutes=GM + MONTH, r=self.r)
        out2 = agents_mod.forecasts_pass(self.store, self.data, 2,
                                         GM + 2 * MONTH)
        self.assertEqual(out2["scored"], 1)
        f = self.store.row("SELECT * FROM forecasts WHERE"
                           " forecast_id = ?", (f["forecast_id"],))
        self.assertEqual(f["status"], "scored")
        self.assertEqual(json.loads(f["actual"])["value"], 6.0)
        score = json.loads(f["score"])
        self.assertAlmostEqual(score["abs_error"], 1.0)
        self.assertAlmostEqual(score["pct_error"], 1.0 / 6.0,
                               places=3)

    def test_congestion_forecast_uses_transport_statistics(self):
        self._congestion_stat(0, 1.0)
        self._congestion_stat(1, 1.2)
        self.store.commit()
        agents_mod.forecasts_pass(self.store, self.data, 1,
                                  GM + MONTH)
        f = self.store.row(
            "SELECT * FROM forecasts WHERE kind = 'congestion'"
            " AND scope = 'rupsha_city'")
        self.assertIsNotNone(f)
        # last + trend([1.0, 1.2]) = 1.2 + 0.2 = 1.4
        self.assertAlmostEqual(json.loads(f["predicted"])["value"],
                               1.4)
        agents_mod.forecasts_pass(self.store, self.data, 2,
                                  GM + 2 * MONTH)
        f = self.store.row("SELECT * FROM forecasts WHERE"
                           " forecast_id = ?", (f["forecast_id"],))
        self.assertEqual(f["status"], "scored")
        score = json.loads(f["score"])
        self.assertAlmostEqual(score["actual"], 1.2)
        self.assertAlmostEqual(score["abs_error"], 0.2)


if __name__ == "__main__":
    unittest.main()
