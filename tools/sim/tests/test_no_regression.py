"""No-existing-functionality-broken checks (owner criterion 11):
the economy balance simulator's output is byte-identical to its
pre-Session-01 baseline, and the committed data validation harness
passes. (The Godot testbed suite is re-run separately at delivery;
it cannot run inside this Python process.)"""
import hashlib
import os
import subprocess
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                    "..", "..", ".."))
# Pinned default-run md5 of tools/economy_sim.py.
# v6 baseline (Unit EY, Queue 22, 2026-11-24): the construction
# worker is modelled on the ES day wage (worked days x wage/30 —
# 30 worked days in a normal month, so the base table is unchanged)
# plus the new day-wage storm-month section (28 worked days). See
# docs/ECONOMY-SIM-REPORT-V6.md. Previous baseline (v4, pinned
# 2026-11-22 through v5): 318c6114c143a81a579e70b39ccca8f8. v2
# baseline (pinned 2026-11-21 through v3):
# 16740182867525bd659735deeb05150a.
ECONOMY_SIM_BASELINE_MD5 = "9ac10779c231b7aa6120a6ff457982de"


class TestDayWageModelling(unittest.TestCase):
    """Queue 22 Unit EY — the v6 day-wage model (ES follow-up):
    construction-worker pay is worked days x wage/30, and the
    trajectory ends exactly at net for every row (the v5 daily
    branch ended 3/26 of the band short of it)."""

    def test_trajectory_ends_at_net_for_every_row(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        for w in prices["wages_monthly"]:
            for tier in ("entry", "mid", "senior"):
                row = econ.simulate(prices, w, tier)
                self.assertEqual(row["end_balance"], row["net"],
                                 f"{w['profession_id']}/{tier}")

    def test_construction_worker_normal_month_pays_the_band(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # 30 worked days (the scheduler-measured normal month) pay
        # exactly the band — the headline figures are unchanged.
        row = econ.simulate(prices, w, "entry")
        self.assertEqual(row["gross"], 9000)
        self.assertEqual(row["net"], 1500)
        self.assertEqual(row["rate"], 16.7)

    def test_construction_worker_storm_month_pays_28_of_30(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # The measured live month: 28 worked days (2 storm days).
        row = econ.simulate(prices, w, "entry",
                            day_wage_worked_days=28)
        self.assertEqual(row["gross"], 8400)
        self.assertEqual(row["tax"], 0)
        self.assertEqual(row["net"], 900)
        self.assertEqual(row["rate"], 10.7)
        self.assertNotIn("TIGHT", row["flags"])
        # Senior: tax is recomputed on the reduced gross.
        senior = econ.simulate(prices, w, "senior",
                               day_wage_worked_days=28)
        self.assertEqual(senior["gross"], 18667)
        self.assertEqual(senior["tax"], 183)
        self.assertEqual(senior["net"], 7601)


class TestNoRegression(unittest.TestCase):
    def test_economy_sim_output_unchanged(self):
        out = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", "economy_sim.py")],
            capture_output=True, cwd=ROOT)
        self.assertEqual(out.returncode, 0)
        self.assertEqual(hashlib.md5(out.stdout).hexdigest(),
                         ECONOMY_SIM_BASELINE_MD5)

    def test_validate_data_passes(self):
        out = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", "validate_data.py")],
            capture_output=True, cwd=ROOT)
        self.assertEqual(out.returncode, 0,
                         out.stdout.decode() + out.stderr.decode())


if __name__ == "__main__":
    unittest.main()
