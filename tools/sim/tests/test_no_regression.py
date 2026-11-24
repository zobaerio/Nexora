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
# v7 baseline (Unit FB, Queue 23, 2026-11-24): the storm-position
# scenario — the same 28 worked days with the two storm days
# early / mid / late / at the measured position, plus the v6
# even-spread baseline for comparison. See
# docs/ECONOMY-SIM-REPORT-V7.md. Previous baseline (v6, pinned
# 2026-11-24 through Queue 22): 9ac10779c231b7aa6120a6ff457982de.
# v5 baseline: 318c6114c143a81a579e70b39ccca8f8. v2 baseline (pinned
# 2026-11-21 through v3): 16740182867525bd659735deeb05150a.
ECONOMY_SIM_BASELINE_MD5 = "e598e416c07b21bacee9fe98fdb27244"


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

    # Queue 23 Unit FB — the storm-position scenario: the same 28
    # worked days, but the two storm days fall early / mid / late
    # or at the measured position (days 3 and 22, where the live
    # month's storms actually fell). The net is the same for every
    # position — only the month-1 minimum balance moves, and that
    # is now a measured figure per position.
    def test_storm_position_minbal_is_measured(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # Entry: a storm on day 1 dips deeper than a storm on day
        # 29 — the v6 even-spread minbal (0) understates the dip.
        early = econ.simulate(prices, w, "entry",
                              storm_days=econ.STORM_EARLY_DAYS)
        self.assertEqual(early["min_balance"], -500)
        self.assertEqual(early["net"], 900)
        measured = econ.simulate(prices, w, "entry",
                                 storm_days=econ.STORM_MEASURED_DAYS)
        self.assertEqual(measured["min_balance"], -150)
        self.assertEqual(measured["net"], 900)
        mid = econ.simulate(prices, w, "entry",
                            storm_days=econ.STORM_MID_DAYS)
        late = econ.simulate(prices, w, "entry",
                             storm_days=econ.STORM_LATE_DAYS)
        even = econ.simulate(prices, w, "entry",
                            day_wage_worked_days=28)
        self.assertEqual(mid["min_balance"], 0)
        self.assertEqual(late["min_balance"], 0)
        self.assertEqual(even["min_balance"], 0)
        # Mid and senior dip deeper in the early position (their
        # daily cost is higher), and stay at 0 everywhere else.
        self.assertEqual(
            econ.simulate(prices, w, "mid",
                          storm_days=econ.STORM_EARLY_DAYS)
            ["min_balance"], -595)
        self.assertEqual(
            econ.simulate(prices, w, "senior",
                          storm_days=econ.STORM_EARLY_DAYS)
            ["min_balance"], -726)
        for tier in ("entry", "mid", "senior"):
            for pos in (econ.STORM_MID_DAYS, econ.STORM_LATE_DAYS,
                        econ.STORM_MEASURED_DAYS):
                self.assertEqual(
                    econ.simulate(prices, w, tier, storm_days=pos)
                    ["min_balance"], 0
                    if tier != "entry" or pos != econ.STORM_MEASURED_DAYS
                    else -150)

    def test_storm_position_trajectory_still_ends_at_net(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # The total pay is the same whatever the days — the
        # trajectory must end exactly at net for every position.
        for tier in ("entry", "mid", "senior"):
            for pos in (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                        econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS):
                row = econ.simulate(prices, w, tier, storm_days=pos)
                self.assertEqual(row["end_balance"], row["net"],
                                 f"{tier}/{pos}")
                self.assertEqual(row["gross"],
                                 econ.simulate(
                                     prices, w, tier,
                                     day_wage_worked_days=28)["gross"])

    def test_storm_days_must_be_one_coherent_month(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # Storm days imply the worked count — a disagreeing count,
        # a day outside 1..30, or a repeated day is refused.
        with self.assertRaises(ValueError):
            econ.simulate(prices, w, "entry", storm_days=(1, 2),
                          day_wage_worked_days=27)
        with self.assertRaises(ValueError):
            econ.simulate(prices, w, "entry", storm_days=(0, 1))
        with self.assertRaises(ValueError):
            econ.simulate(prices, w, "entry", storm_days=(1, 31))
        with self.assertRaises(ValueError):
            econ.simulate(prices, w, "entry", storm_days=(1, 1))
        # storm_days is a day-wage scenario only — a monthly-paid
        # profession refuses it rather than ignoring it.
        teacher = next(w for w in prices["wages_monthly"]
                       if w["profession_id"] == "teacher")
        with self.assertRaises(ValueError):
            econ.simulate(prices, teacher, "entry",
                          storm_days=(1, 2))


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
