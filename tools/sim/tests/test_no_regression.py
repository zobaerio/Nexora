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
# v7 + Queue 25 baseline (Unit HD, 2026-11-24): the
# mixed-profession two-earner storm-position section (HD).
# See docs/ECONOMY-SIM-REPORT-V7.md §9.
# Previous baseline (v7 + Queue 25, Unit HA):
# ede430d0bf391fac3f8599334f55b77b. Previous baseline (v7 +
# Queue 24, Units GD–GE):
# d699ae7d37fe8ca077f873ba238dd86b. Previous baseline (v7, pinned
# 2026-11-24 through Queue 23):
# e598e416c07b21bacee9fe98fdb27244. Previous baseline (v6, pinned
# 2026-11-24 through Queue 22): 9ac10779c231b7aa6120a6ff457982de.
# v5 baseline: 318c6114c143a81a579e70b39ccca8f8. v2 baseline (pinned
# 2026-11-21 through v3): 16740182867525bd659735deeb05150a.
ECONOMY_SIM_BASELINE_MD5 = "5431558ffa3d023c436366c26535f932"


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
    # or at the measured position (days 4 and 23, where the live
    # month's storms actually fell — Queue 25 Unit HA corrects
    # FB's (3, 22), which were the 0-based day indices). The net
    # is the same for every position — only the month-1 minimum
    # balance moves, and that is now a measured figure per
    # position.
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
        self.assertEqual(measured["min_balance"], -100)
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
                    else -100)

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


    # Queue 24 Unit GD — the two-earner storm-position scenario:
    # a second construction worker at the same tier, on the same
    # storm days and the same day-wage rule, with the household
    # costs following engine._living_costs for two adults. The
    # measured position dips nothing (pay lands on days 1–3
    # before the day-4 storm — Queue 25 Unit HA corrects the
    # position from (3, 22)), but the early position dips DEEPER
    # the single-earner household — two adults burn the daily cost
    # with no pay arriving on days 1–2.
    def test_two_earner_storm_position_minbal_is_measured(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        early = econ.simulate(prices, w, "entry",
                              storm_days=econ.STORM_EARLY_DAYS,
                              second_earner=True)
        self.assertEqual(early["min_balance"], -780)
        self.assertEqual(early["net"], 5100)
        measured = econ.simulate(prices, w, "entry",
                                 storm_days=econ.STORM_MEASURED_DAYS,
                                 second_earner=True)
        self.assertEqual(measured["min_balance"], 0)
        self.assertEqual(measured["net"], 5100)
        for tier in ("entry", "mid", "senior"):
            for pos in (econ.STORM_MID_DAYS, econ.STORM_LATE_DAYS,
                        econ.STORM_MEASURED_DAYS):
                self.assertEqual(
                    econ.simulate(prices, w, tier, storm_days=pos,
                                  second_earner=True)["min_balance"],
                    0, f"{tier}/{pos}")
        # The early dip is deeper than the single-earner one in
        # NCr (two adults, no pay on days 1–2) — the second earner
        # does not help the early position.
        self.assertEqual(
            econ.simulate(prices, w, "mid",
                          storm_days=econ.STORM_EARLY_DAYS,
                          second_earner=True)["min_balance"], -970)
        self.assertEqual(
            econ.simulate(prices, w, "senior",
                          storm_days=econ.STORM_EARLY_DAYS,
                          second_earner=True)["min_balance"], -1231)
        self.assertEqual(
            econ.simulate(prices, w, "mid",
                          storm_days=econ.STORM_EARLY_DAYS,
                          second_earner=True)["net"], 11588)
        self.assertEqual(
            econ.simulate(prices, w, "senior",
                          storm_days=econ.STORM_EARLY_DAYS,
                          second_earner=True)["net"], 18502)

    def test_two_earner_costs_follow_engine_scaling(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # Storm month at the measured position: the two-earner
        # costs are the single-earner costs plus the second
        # adult's food/clothing/transport/eating (4,200 at the
        # lower band) plus the second earner's own uplift.
        for tier, delta in (("entry", 4200), ("mid", 5623),
                            ("senior", 7583)):
            single = econ.simulate(prices, w, tier,
                                   storm_days=econ.STORM_MEASURED_DAYS)
            two = econ.simulate(prices, w, tier,
                                storm_days=econ.STORM_MEASURED_DAYS,
                                second_earner=True)
            self.assertEqual(two["costs_total"]
                             - single["costs_total"], delta, tier)
            # Gross doubles; tax is per person (senior: 2 x 183).
            self.assertEqual(two["gross"], 2 * single["gross"], tier)
            self.assertEqual(two["tax"], 2 * single["tax"], tier)
            self.assertEqual(two["uplift"], 2 * single["uplift"],
                             tier)
            self.assertTrue(two["second_earner"])
            self.assertFalse(single["second_earner"])

    def test_two_earner_trajectory_still_ends_at_net(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        for tier in ("entry", "mid", "senior"):
            for pos in (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                        econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS):
                row = econ.simulate(prices, w, tier, storm_days=pos,
                                    second_earner=True)
                self.assertEqual(row["end_balance"], row["net"],
                                 f"{tier}/{pos}")

    def test_second_earner_is_refused_off_day_wage(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        teacher = next(w for w in prices["wages_monthly"]
                       if w["profession_id"] == "teacher")
        with self.assertRaises(ValueError):
            econ.simulate(prices, teacher, "entry",
                          second_earner=True)
        with self.assertRaises(ValueError):
            econ.simulate(prices, w, "entry", second_earner=True,
                          tutoring_income=2400)
        # Without the flag, the single-earner figures are
        # untouched by the new kwarg.
        row = econ.simulate(prices, w, "entry",
                            storm_days=econ.STORM_MEASURED_DAYS)
        self.assertEqual(row["min_balance"], -100)
        self.assertEqual(row["net"], 900)


    # Queue 25 Unit HD — the mixed-profession two-earner
    # storm-position scenario: the second earner is a taxi driver
    # at entry (14,000, per-fare) or a civil engineer at mid
    # (38,000, monthly) — the settlement's measured pairings (V7
    # §6) — at the FIXED measured tier while the first earner
    # varies. Storm days do not change the second earner's pay
    # (the per-fare rule has no storm days; the monthly pay lands
    # day 30 regardless), so the storm-position effect comes from
    # the first earner alone, against the second earner's steady
    # pay. Costs follow engine._living_costs for two adults.
    def test_mixed_second_earner_minbal_is_measured(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # Taxi second earner: the steady per-fare pay covers the
        # early dip almost everywhere — only the senior early row
        # dips at all (-72), and the measured position dips nothing.
        taxi = {t: econ.simulate(
            prices, w, t, storm_days=econ.STORM_MEASURED_DAYS,
            second_earner="taxi_driver") for t in
            ("entry", "mid", "senior")}
        self.assertEqual(taxi["entry"]["min_balance"], 0)
        self.assertEqual(taxi["mid"]["min_balance"], 0)
        self.assertEqual(taxi["senior"]["min_balance"], 0)
        self.assertEqual(taxi["entry"]["net"], 10700)
        self.assertEqual(
            econ.simulate(prices, w, "senior",
                          storm_days=econ.STORM_EARLY_DAYS,
                          second_earner="taxi_driver")["min_balance"],
            -72)
        # Civil-engineer second earner: the monthly pay lands on
        # day 30, so the household burns the daily cost for 29 days
        # first — the dip is deep and nearly position-independent
        # (the early/mid/measured positions share it; only the late
        # position is shallower, because the day-29 storm costs a
        # day of construction pay that the day-30 lump then covers).
        ce = {t: econ.simulate(
            prices, w, t, storm_days=econ.STORM_MEASURED_DAYS,
            second_earner="civil_engineer") for t in
            ("entry", "mid", "senior")}
        self.assertEqual(ce["entry"]["min_balance"], -8623)
        self.assertEqual(ce["mid"]["min_balance"], -5499)
        self.assertEqual(ce["senior"]["min_balance"], -2170)
        self.assertEqual(ce["entry"]["net"], 27950)
        self.assertEqual(
            econ.simulate(prices, w, "entry",
                          storm_days=econ.STORM_EARLY_DAYS,
                          second_earner="civil_engineer")
            ["min_balance"], -8623)
        self.assertEqual(
            econ.simulate(prices, w, "entry",
                          storm_days=econ.STORM_LATE_DAYS,
                          second_earner="civil_engineer")
            ["min_balance"], -8323)

    def test_mixed_second_earner_costs_follow_engine_scaling(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # Taxi: the second adult's food/clothing/transport/eating
        # (4,200 at the lower band) and no uplift (14,000 is the
        # taxi entry wage). Civil engineer: 4,200 plus the
        # mid-tier uplift (35% of 38,000 - 22,000 = 5,600).
        for tier, delta in (("entry", 4200), ("mid", 4200),
                            ("senior", 4200)):
            single = econ.simulate(prices, w, tier,
                                   storm_days=econ.STORM_MEASURED_DAYS)
            two = econ.simulate(prices, w, tier,
                                storm_days=econ.STORM_MEASURED_DAYS,
                                second_earner="taxi_driver")
            self.assertEqual(two["costs_total"]
                             - single["costs_total"], delta, tier)
            self.assertEqual(two["gross"], single["gross"] + 14000,
                             tier)
            self.assertEqual(two["tax"], single["tax"], tier)
            self.assertEqual(two["uplift"], single["uplift"], tier)
            self.assertEqual(two["second_earner_pid"], "taxi_driver")
        for tier in ("entry", "mid", "senior"):
            single = econ.simulate(prices, w, tier,
                                   storm_days=econ.STORM_MEASURED_DAYS)
            two = econ.simulate(prices, w, tier,
                                storm_days=econ.STORM_MEASURED_DAYS,
                                second_earner="civil_engineer")
            self.assertEqual(two["costs_total"]
                             - single["costs_total"], 9800, tier)
            self.assertEqual(two["gross"], single["gross"] + 38000,
                             tier)
            self.assertEqual(two["tax"], single["tax"] + 1150, tier)
            self.assertEqual(two["uplift"],
                             single["uplift"] + 5600, tier)
            self.assertEqual(two["second_earner_pid"],
                             "civil_engineer")
            self.assertIsNone(single["second_earner_pid"])
        # The GD same-tier case records its pid too.
        self.assertEqual(
            econ.simulate(prices, w, "entry",
                          storm_days=econ.STORM_MEASURED_DAYS,
                          second_earner=True)["second_earner_pid"],
            "construction_worker")

    def test_mixed_second_earner_pay_is_storm_independent(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # The second earner's pay is the full tier wage at every
        # storm position: the mixed gross is the single-earner
        # storm gross plus exactly 14,000 / 38,000, whatever the
        # days — no storm effect is forced where the pay rule has
        # none.
        for pid2, pay in (("taxi_driver", 14000),
                          ("civil_engineer", 38000)):
            for tier in ("entry", "mid", "senior"):
                for pos in (econ.STORM_EARLY_DAYS,
                            econ.STORM_MID_DAYS,
                            econ.STORM_LATE_DAYS,
                            econ.STORM_MEASURED_DAYS):
                    single = econ.simulate(prices, w, tier,
                                           storm_days=pos)
                    mixed = econ.simulate(prices, w, tier,
                                          storm_days=pos,
                                          second_earner=pid2)
                    self.assertEqual(mixed["gross"],
                                     single["gross"] + pay,
                                     f"{pid2}/{tier}/{pos}")

    def test_mixed_second_earner_trajectory_still_ends_at_net(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        for pid2 in ("taxi_driver", "civil_engineer"):
            for tier in ("entry", "mid", "senior"):
                for pos in (econ.STORM_EARLY_DAYS,
                            econ.STORM_MID_DAYS,
                            econ.STORM_LATE_DAYS,
                            econ.STORM_MEASURED_DAYS):
                    row = econ.simulate(prices, w, tier,
                                        storm_days=pos,
                                        second_earner=pid2)
                    self.assertEqual(row["end_balance"], row["net"],
                                     f"{pid2}/{tier}/{pos}")

    def test_mixed_second_earner_refusals(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        teacher = next(w for w in prices["wages_monthly"]
                       if w["profession_id"] == "teacher")
        # Only the two measured pairings are modelled — any other
        # profession is refused, not silently treated as one.
        with self.assertRaises(ValueError):
            econ.simulate(prices, w, "entry",
                          second_earner="pilot")
        # The first earner must still be day-wage, and v3 lines
        # are still refused with a second earner.
        with self.assertRaises(ValueError):
            econ.simulate(prices, teacher, "entry",
                          second_earner="taxi_driver")
        with self.assertRaises(ValueError):
            econ.simulate(prices, w, "entry",
                          second_earner="taxi_driver",
                          tutoring_income=2400)


    # Queue 24 Unit GE — the storm-position bridge line: the
    # bridge check prints the construction_worker entry row's
    # starting balance + its worst storm-position dip. The worst
    # dip is the early position (−500 entry); the line must carry
    # the report's bridge observation (5,000 − 500 = 4,500).
    def test_storm_position_bridge_line_is_printed(self):
        import subprocess
        out = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools",
                                          "economy_sim.py")],
            capture_output=True, cwd=ROOT)
        self.assertEqual(out.returncode, 0)
        text = out.stdout.decode()
        self.assertIn(
            "construction_worker    start   5000 + storm dip"
            "    -500 =    4500  OK  (worst storm position)", text)
        self.assertIn("BRIDGE FAIL rows: []", text)

    def test_worst_storm_position_dip_is_the_early_one(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # The worst dip across the four positions is the early
        # one, for every tier — the bridge line wires the minimum,
        # not the measured position.
        for tier, worst in (("entry", -500), ("mid", -595),
                            ("senior", -726)):
            dips = [econ.simulate(prices, w, tier, storm_days=pos)
                    ["min_balance"]
                    for pos in (econ.STORM_EARLY_DAYS,
                                econ.STORM_MID_DAYS,
                                econ.STORM_LATE_DAYS,
                                econ.STORM_MEASURED_DAYS)]
            self.assertEqual(min(dips), worst, tier)
            self.assertEqual(
                econ.simulate(prices, w, tier,
                              storm_days=econ.STORM_EARLY_DAYS)
                ["min_balance"], worst, tier)


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
