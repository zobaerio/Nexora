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
# v7 + Queue 45 baseline (Unit MN, 2026-11-26): the
# senior taxi-driver second earner in the surge table (the
# fifth pairing — early 0 -> 0, nets +1,080 at every tier).
# See docs/ECONOMY-SIM-REPORT-V7.md §34.
# Previous baseline (v7 + Queue 44, Unit MM):
# 47ec8771cc8bca2889d62faa3b23c6e6. Previous baseline (v7 + Queue 40, Unit MI):
# 3d3fce982a64634a0b03bb0af3643f94. Previous baseline (v7 + Queue 34, Unit MC):
# a818a3273cdad108c4d8d4ae198b5b44. Previous baseline (v7 + Queue 33, Unit MB):
# 4abf52ff0dc7d00f6acd3168d7c1c807. Previous baseline (v7 + Queue 32, Unit MA):
# bc9a35e1c95d4b8a512c0a4a6e0994cd. Previous baseline (v7 + Queue 31, Unit LA):
# 2b9d24f9663f88ad0d13be1f5e86c40c. Previous baseline (v7 +
# Queue 28, Unit KA):
# 5f50931cbaad263812473ce1c7830e59. Previous baseline (v7 +
# Queue 27, Unit JA):
# b70b18972aeb5c3b2d0273b986060058. Previous baseline (v7 +
# Queue 26, Unit IC):
# d198a2fe0970e11aaa105bcc4bfb19f9. Previous baseline (v7 +
# Queue 26, Unit IB):
# 27464ea221694880a4369f805d8cd455. Previous baseline (v7 +
# Queue 26, Unit IA):
# 45a45edc63cee4b142891da938ef79bd. Previous baseline (v7 +
# Queue 25, Unit HD):
# 5431558ffa3d023c436366c26535f932. Previous baseline (v7 +
# Queue 29, Unit KC):
# f6cec5a23109c4e7f9aeff3f7361e89d. Previous baseline (v7 +
# Queue 25, Unit HA):
# ede430d0bf391fac3f8599334f55b77b. Previous baseline (v7 +
# Queue 24, Units GD–GE):
# d699ae7d37fe8ca077f873ba238dd86b. Previous baseline (v7, pinned
# 2026-11-24 through Queue 23):
# e598e416c07b21bacee9fe98fdb27244. Previous baseline (v6, pinned
# 2026-11-24 through Queue 22): 9ac10779c231b7aa6120a6ff457982de.
# v5 baseline: 318c6114c143a81a579e70b39ccca8f8. v2 baseline (pinned
# 2026-11-21 through v3): 16740182867525bd659735deeb05150a.
ECONOMY_SIM_BASELINE_MD5 = "c70567cb94bd018ef50df1470fdbe746"


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
    # starting balance + its worst storm-position dip. Queue 31
    # Unit LA sweeps the tiers too (the minimum across the
    # first earner's tiers and the four storm positions, like
    # the two-earner lines): the worst dip is senior early
    # (−726), so the line is 5,000 − 726 = 4,274 — the
    # household's worst across tiers, not the entry row's.
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
            "    -726 =    4274  OK  (worst storm position,"
            " all tiers)", text)
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

    # Queue 26 Unit IA — the mixed two-earner bridge lines: the
    # bridge check prints the combined canonical start plus the
    # worst mixed minbal per second-earner profession. Each
    # earner brings their own genesis balance
    # (professions.json starting_balance_ncr: construction_worker
    # 5,000, taxi_driver 5,000, civil_engineer 25,000) — so the
    # taxi-second start is 10,000 and the civil-engineer-second
    # start is 30,000, not the 10,000 HD's prose carried for
    # both (V7 §9's 10,000 − 8,623 = 1,377 understates the
    # engineer's start by 20,000; corrected here to 30,000 −
    # 8,623 = 21,377).
    def test_mixed_two_earner_bridge_line_is_printed(self):
        import subprocess
        out = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools",
                                          "economy_sim.py")],
            capture_output=True, cwd=ROOT)
        self.assertEqual(out.returncode, 0)
        text = out.stdout.decode()
        self.assertIn(
            "construction_worker + taxi-driver    start  10000"
            " + mixed dip     -72 =    9928  OK  (worst mixed"
            " storm position)", text)
        self.assertIn(
            "construction_worker + civil-engineer start  30000"
            " + mixed dip   -8623 =   21377  OK  (worst mixed"
            " storm position)", text)
        self.assertIn("BRIDGE FAIL rows: []", text)

    def test_worst_mixed_dip_is_measured_per_pairing(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # The worst mixed dip is the minimum across the first
        # earner's tiers and the four storm positions: taxi-second
        # −72 (senior, early — the only negative anywhere) and
        # civil-engineer-second −8,623 (entry, early/mid/
        # measured — the late position is shallower).
        for pid2, worst in (("taxi_driver", -72),
                            ("civil_engineer", -8623)):
            dips = [econ.simulate(prices, w, tier, storm_days=pos,
                                  second_earner=pid2)["min_balance"]
                    for tier in ("entry", "mid", "senior")
                    for pos in (econ.STORM_EARLY_DAYS,
                                econ.STORM_MID_DAYS,
                                econ.STORM_LATE_DAYS,
                                econ.STORM_MEASURED_DAYS)]
            self.assertEqual(min(dips), worst, pid2)
        # The combined starts are the sums of the two earners'
        # own genesis balances, read from the source data — not
        # a single figure applied to both pairings.
        profs = econ.load("professions.json")
        starts = {p["id"]: p.get("starting_balance_ncr", 0)
                  for p in profs["professions"]}
        self.assertEqual(starts["construction_worker"]
                         + starts["taxi_driver"], 10000)
        self.assertEqual(starts["construction_worker"]
                         + starts["civil_engineer"], 30000)

    # Queue 27 Unit JA — the remaining two-earner bridge
    # lines: the bridge check prints the combined canonical
    # start plus the worst minbal for the GD same-tier
    # household and the IC other-tier pairings, wired the same
    # way as IA's mixed lines. Same-tier: 10,000 − 1,231 =
    # 8,769. Mid-tier taxi-second: 10,000 − 0 = 10,000. Entry
    # civil-engineer-second: 30,000 − 3,210 = 26,790. With
    # these three lines, no two-earner bridge figure is
    # report-only.
    def test_remaining_two_earner_bridge_lines_are_printed(self):
        import subprocess
        out = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools",
                                          "economy_sim.py")],
            capture_output=True, cwd=ROOT)
        self.assertEqual(out.returncode, 0)
        text = out.stdout.decode()
        self.assertIn(
            "construction_worker + construction-worker start"
            "  10000 + same-tier dip   -1231 =    8769  OK"
            "  (worst same-tier storm position)", text)
        self.assertIn(
            "construction_worker + taxi-driver (mid) start"
            "  10000 + other-tier dip       0 =   10000  OK"
            "  (worst other-tier storm position)", text)
        self.assertIn(
            "construction_worker + civil-engineer (entry) start"
            "  30000 + other-tier dip   -3210 =   26790  OK"
            "  (worst other-tier storm position)", text)
        self.assertIn("BRIDGE FAIL rows: []", text)

    def test_worst_remaining_dips_are_measured(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # The worst dip is the minimum across the first
        # earner's tiers and the four storm positions, per
        # household: same-tier −1,231 (senior, early),
        # mid-tier taxi-second 0 (nothing dips anywhere),
        # entry civil-engineer-second −3,210 (entry,
        # early/mid/measured).
        positions = (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                     econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS)
        same = min(
            econ.simulate(prices, w, tier, storm_days=pos,
                          second_earner=True)["min_balance"]
            for tier in ("entry", "mid", "senior")
            for pos in positions)
        self.assertEqual(same, -1231)
        taxi_mid = min(
            econ.simulate(prices, w, tier, storm_days=pos,
                          second_earner="taxi_driver",
                          second_earner_tier="mid")["min_balance"]
            for tier in ("entry", "mid", "senior")
            for pos in positions)
        self.assertEqual(taxi_mid, 0)
        ce_entry = min(
            econ.simulate(prices, w, tier, storm_days=pos,
                          second_earner="civil_engineer",
                          second_earner_tier="entry")["min_balance"]
            for tier in ("entry", "mid", "senior")
            for pos in positions)
        self.assertEqual(ce_entry, -3210)
        # The combined starts are the sums of the two earners'
        # own genesis balances, read from the source data.
        profs = econ.load("professions.json")
        starts = {p["id"]: p.get("starting_balance_ncr", 0)
                  for p in profs["professions"]}
        self.assertEqual(2 * starts["construction_worker"],
                         10000)
        self.assertEqual(starts["construction_worker"]
                         + starts["taxi_driver"], 10000)
        self.assertEqual(starts["construction_worker"]
                         + starts["civil_engineer"], 30000)

    # Queue 26 Unit IB — the renting-cab taxi second earner:
    # the same entry taxi driver (14,000, per-fare), but renting
    # the licensed cab. The rental follows the settlement's rule
    # (engine._settle_month: cab_rental_ncr_per_day × WORK_DAYS
    # = 200 × 26 = 5,200/month flat) and is a monthly cost line,
    # so the net drops by exactly 5,200 at every tier and the
    # early dip the owning driver had closed re-opens (the
    # rental accrues daily while the construction pay waits).
    def test_renting_cab_second_earner_minbal_is_measured(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        renting = {t: econ.simulate(
            prices, w, t, storm_days=econ.STORM_MEASURED_DAYS,
            second_earner="taxi_driver",
            second_earner_renting_cab=True) for t in
            ("entry", "mid", "senior")}
        self.assertEqual(renting["entry"]["min_balance"], 0)
        self.assertEqual(renting["mid"]["min_balance"], 0)
        self.assertEqual(renting["senior"]["min_balance"], 0)
        for tier, dip, net in (("entry", -193, 5500),
                               ("mid", -288, 8744),
                               ("senior", -419, 12201)):
            row = econ.simulate(
                prices, w, tier, storm_days=econ.STORM_EARLY_DAYS,
                second_earner="taxi_driver",
                second_earner_renting_cab=True)
            self.assertEqual(row["min_balance"], dip, tier)
            self.assertEqual(row["net"], net, tier)
            self.assertEqual(row["second_earner_rental"], 5200,
                             tier)
            self.assertTrue(row["second_earner_renting_cab"])
        # The rental is exactly the settlement's charge: 200/day
        # × 26 worked days, read from the source data.
        self.assertEqual(
            prices["taxi_fares"]["cab_rental_ncr_per_day"]
            * econ.WORK_DAYS, 5200)

    def test_renting_cab_second_earner_costs_and_net(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # The rental is a monthly cost line on top of the owning
        # variant: costs +5,200, net −5,200, gross and tax
        # untouched, at every tier and every position.
        for tier in ("entry", "mid", "senior"):
            for pos in (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                        econ.STORM_LATE_DAYS,
                        econ.STORM_MEASURED_DAYS):
                owning = econ.simulate(
                    prices, w, tier, storm_days=pos,
                    second_earner="taxi_driver")
                renting = econ.simulate(
                    prices, w, tier, storm_days=pos,
                    second_earner="taxi_driver",
                    second_earner_renting_cab=True)
                self.assertEqual(renting["costs_total"]
                                 - owning["costs_total"], 5200,
                                 f"{tier}/{pos}")
                self.assertEqual(owning["net"] - renting["net"],
                                 5200, f"{tier}/{pos}")
                self.assertEqual(renting["gross"], owning["gross"],
                                 f"{tier}/{pos}")
                self.assertEqual(renting["tax"], owning["tax"],
                                 f"{tier}/{pos}")
                self.assertEqual(renting["end_balance"],
                                 renting["net"], f"{tier}/{pos}")
        # The owning driver charges no rental.
        owning = econ.simulate(
            prices, w, "entry", storm_days=econ.STORM_MEASURED_DAYS,
            second_earner="taxi_driver")
        self.assertEqual(owning["second_earner_rental"], 0)
        self.assertFalse(owning["second_earner_renting_cab"])

    def test_renting_cab_second_earner_refusals(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # The rental belongs to the taxi driver alone — not to
        # the civil engineer, not to the same-tier second earner,
        # and not to a household with no second earner.
        with self.assertRaises(ValueError):
            econ.simulate(prices, w, "entry",
                          second_earner="civil_engineer",
                          second_earner_renting_cab=True)
        with self.assertRaises(ValueError):
            econ.simulate(prices, w, "entry", second_earner=True,
                          second_earner_renting_cab=True)
        with self.assertRaises(ValueError):
            econ.simulate(prices, w, "entry",
                          second_earner_renting_cab=True)

    # Queue 27 Unit JB — the single-earner renting-cab row
    # follows the settlement's rental charge: 200 NCr/day ×
    # WORK_DAYS (26) = 5,200/month flat, with no Sunday
    # exclusion. The v1 rule charged the rental only on days
    # ≤ 26 excluding Sundays (23 days = 4,600 in the
    # trajectory, while the headline net already subtracted
    # the full 5,200) — so the row's trajectory ended 600
    # above its own net. The decision follows the settlement
    # (engine._settle_month charges rental_day × WORK_DAYS);
    # the v1 23-day rule is not kept, because no source gives
    # the rental a day-of-week rule and the 23-day trajectory
    # was internally inconsistent.
    def test_single_earner_renting_cab_row_follows_settlement(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "taxi_driver")
        # The settlement's charge, read from the source data:
        # 200/day × 26 worked days, flat.
        self.assertEqual(
            prices["taxi_fares"]["cab_rental_ncr_per_day"]
            * econ.WORK_DAYS, 5200)
        row = econ.simulate(
            prices, w, "entry",
            extra_daily_cost=prices["taxi_fares"]
            ["cab_rental_ncr_per_day"],
            label_suffix=" (renting cab)")
        self.assertEqual(row["extra"], 5200)
        self.assertEqual(row["net"], 1300)
        self.assertEqual(row["min_balance"], 0)
        # The trajectory now charges the full monthly rental
        # (26 days × 200) and ends exactly at net — under the
        # v1 rule it ended at 1,900, 600 above net.
        self.assertEqual(row["end_balance"], row["net"])
        self.assertEqual(row["end_balance"], 1300)
        # The base table's renting row and its bridge line do
        # not move under the decision: the headline figures
        # were already right (the net always subtracted the
        # full 5,200); only the trajectory was 600 short.
        self.assertEqual(row["rate"], 9.3)
        self.assertIn("TIGHT", row["flags"])

    # Queue 26 Unit IC — the second earner at another tier: a
    # mid-tier taxi driver (23,000, per-fare) or an entry civil
    # engineer (22,000, monthly), each at the tier the source
    # data actually gives. The measured tier stays the default,
    # so the HD/IB figures are untouched by the new kwarg.
    def test_second_earner_at_other_tiers_is_measured(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # Mid-tier taxi: the higher per-fare pay covers the
        # cost-only days at every tier — no dip anywhere, and the
        # senior early −72 of the measured tier is gone too.
        for tier, net in (("entry", 16150), ("mid", 19394),
                          ("senior", 22851)):
            for pos in (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                        econ.STORM_LATE_DAYS,
                        econ.STORM_MEASURED_DAYS):
                row = econ.simulate(
                    prices, w, tier, storm_days=pos,
                    second_earner="taxi_driver",
                    second_earner_tier="mid")
                self.assertEqual(row["min_balance"], 0,
                                 f"taxi/mid/{tier}/{pos}")
                self.assertEqual(row["net"], net,
                                 f"taxi/mid/{tier}/{pos}")
                self.assertEqual(row["second_earner_tier"], "mid")
                self.assertEqual(row["end_balance"], row["net"])
        # Entry civil engineer: the monthly lump still lands on
        # day 30, so the dip is shallower than the measured
        # mid-tier pairing (−8,623) but deeper than the
        # taxi pairings — and nearly position-independent again.
        ce = {t: econ.simulate(
            prices, w, t, storm_days=econ.STORM_MEASURED_DAYS,
            second_earner="civil_engineer",
            second_earner_tier="entry") for t in
            ("entry", "mid", "senior")}
        self.assertEqual(ce["entry"]["min_balance"], -3210)
        self.assertEqual(ce["mid"]["min_balance"], -350)
        self.assertEqual(ce["senior"]["min_balance"], -31)
        self.assertEqual(ce["entry"]["net"], 18350)
        self.assertEqual(
            econ.simulate(prices, w, "entry",
                          storm_days=econ.STORM_EARLY_DAYS,
                          second_earner="civil_engineer",
                          second_earner_tier="entry")
            ["min_balance"], -3210)
        self.assertEqual(
            econ.simulate(prices, w, "entry",
                          storm_days=econ.STORM_LATE_DAYS,
                          second_earner="civil_engineer",
                          second_earner_tier="entry")
            ["min_balance"], -2910)
        self.assertEqual(
            econ.simulate(prices, w, "mid",
                          storm_days=econ.STORM_EARLY_DAYS,
                          second_earner="civil_engineer",
                          second_earner_tier="entry")
            ["min_balance"], -875)
        self.assertEqual(
            econ.simulate(prices, w, "senior",
                          storm_days=econ.STORM_EARLY_DAYS,
                          second_earner="civil_engineer",
                          second_earner_tier="entry")
            ["min_balance"], -1006)

    # Queue 40 Unit MI — the senior civil-engineer second
    # earner, wired: a measured household appeared in the
    # larger world (seed mi-seed-1, 300 population, 365 days:
    # HH000086 pairs a construction-worker head with a tier-5
    # civil engineer at 65,000/month), so the IC section
    # gains the senior rows and both bridge checks gain the
    # line. The senior monthly lump lands on day 30 while
    # the senior lifestyle uplift accrues daily, so the
    # month-1 dip is DEEPER than the mid-tier pairing's
    # despite the higher pay — the figures below are the
    # measured ones, not a scaling of the mid tier.
    def test_senior_civil_engineer_second_earner_is_measured(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # The senior band is sourced, not invented:
        # civil_engineer senior is 65,000 in prices.json.
        wages = {x["profession_id"]: x
                 for x in prices["wages_monthly"]}
        self.assertEqual(wages["civil_engineer"]["senior"], 65000)
        # Month-1 minbal by storm position, per first-earner
        # tier: nearly position-independent (the monthly lump
        # lands day 30 whatever the storms), only late is
        # shallower — and deeper than the mid-tier pairing
        # (−8,623 / −5,499 / −2,170) at every tier.
        expected = {
            "entry": ((-17758, -17758, -17458, -17758, -17738),
                      42900),
            "mid": ((-14634, -14634, -14167, -14634, -14602),
                    46144),
            "senior": ((-11305, -11305, -10645, -11305, -11261),
                       49601),
        }
        positions = (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                     econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS)
        for tier, (minbals, net) in expected.items():
            for pos, want in zip(positions, minbals[:4]):
                row = econ.simulate(
                    prices, w, tier, storm_days=pos,
                    second_earner="civil_engineer",
                    second_earner_tier="senior")
                self.assertEqual(row["min_balance"], want,
                                 f"senior-CE/{tier}/{pos}")
                self.assertEqual(row["net"], net,
                                 f"senior-CE/{tier}/{pos}")
                self.assertEqual(row["end_balance"], row["net"])
            even = econ.simulate(
                prices, w, tier, day_wage_worked_days=28,
                second_earner="civil_engineer",
                second_earner_tier="senior")
            self.assertEqual(even["min_balance"], minbals[4],
                             f"senior-CE/{tier}/even")
            self.assertEqual(even["net"], net)
        # The senior pairing's net is higher than the mid
        # tier's at every tier, while its dip is deeper —
        # the uplift, not the pay, sets the trough.
        for tier in ("entry", "mid", "senior"):
            senior_net = econ.simulate(
                prices, w, tier, storm_days=econ.STORM_EARLY_DAYS,
                second_earner="civil_engineer",
                second_earner_tier="senior")["net"]
            mid_net = econ.simulate(
                prices, w, tier, storm_days=econ.STORM_EARLY_DAYS,
                second_earner="civil_engineer")["net"]
            self.assertGreater(senior_net, mid_net, tier)

    def test_senior_civil_engineer_bridge_line_is_wired(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # The bridge worst is the minimum across the first
        # earner's tiers and the four storm positions.
        worst = min(
            econ.simulate(
                prices, w, tier, storm_days=pos,
                second_earner="civil_engineer",
                second_earner_tier="senior")["min_balance"]
            for tier in ("entry", "mid", "senior")
            for pos in (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                        econ.STORM_LATE_DAYS,
                        econ.STORM_MEASURED_DAYS))
        self.assertEqual(worst, -17758)
        start = 5000 + 25000
        self.assertEqual(start + worst, 12242)
        # The printed output wires the row and the line in
        # both runs: the IC section header and the bridge
        # line (30,000 - 17,758 = 12,242, OK) in the default
        # run, and the same line in the --shibnagar variant's
        # own bridge check.
        for args in ([], ["--shibnagar"]):
            out = subprocess.run(
                [sys.executable,
                 os.path.join(ROOT, "tools", "economy_sim.py")]
                + args, capture_output=True, cwd=ROOT)
            text = out.stdout.decode()
            self.assertEqual(out.returncode, 0, args)
            self.assertIn(
                "civil-engineer second earner (senior 65,000,"
                " monthly)", text, args)
            self.assertIn(
                "construction_worker + civil-engineer (senior)"
                " start  30000 + other-tier dip  -17758"
                " =   12242  OK", text, args)
            self.assertIn("BRIDGE FAIL rows: []", text, args)

    # Queue 44 Unit MM — the senior taxi-driver second
    # earner, wired: ML measured the pairing under a
    # construction-worker head twice (ml-seed-1 HH000030,
    # ml-seed-3 HH000042), and MM re-ran both holding seeds
    # and both pairings reproduce exactly, so the IC section
    # gains the senior taxi rows and both bridge checks gain
    # the line. Unlike the senior civil engineer, the
    # per-fare senior pay lands daily, so the month-1 dip is
    # 0 at every tier and position — the pay-timing contrast
    # with the senior CE lump is the finding, and the nets
    # below are the measured ones, not a scaling of the mid
    # tier.
    def test_senior_taxi_driver_second_earner_is_measured(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # The senior band is sourced, not invented:
        # taxi_driver senior is 36,000 in prices.json.
        wages = {x["profession_id"]: x
                 for x in prices["wages_monthly"]}
        self.assertEqual(wages["taxi_driver"]["senior"], 36000)
        # Month-1 minbal by storm position, per first-earner
        # tier: 0 everywhere — the per-fare pay covers the
        # cost-only days at every tier, unlike the senior CE
        # lump (−17,758 / −14,634 / −11,305 early).
        expected = {
            "entry": ((0, 0, 0, 0, 0), 23950),
            "mid": ((0, 0, 0, 0, 0), 27194),
            "senior": ((0, 0, 0, 0, 0), 30651),
        }
        positions = (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                     econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS)
        for tier, (minbals, net) in expected.items():
            for pos, want in zip(positions, minbals[:4]):
                row = econ.simulate(
                    prices, w, tier, storm_days=pos,
                    second_earner="taxi_driver",
                    second_earner_tier="senior")
                self.assertEqual(row["min_balance"], want,
                                 f"senior-taxi/{tier}/{pos}")
                self.assertEqual(row["net"], net,
                                 f"senior-taxi/{tier}/{pos}")
                self.assertEqual(row["end_balance"], row["net"])
            even = econ.simulate(
                prices, w, tier, day_wage_worked_days=28,
                second_earner="taxi_driver",
                second_earner_tier="senior")
            self.assertEqual(even["min_balance"], minbals[4],
                             f"senior-taxi/{tier}/even")
            self.assertEqual(even["net"], net)
        # The senior pairing's net is higher than the mid
        # tier's at every tier, while its dip is no deeper
        # (0 against 0) — the per-fare pay, not the band,
        # sets the trough.
        for tier in ("entry", "mid", "senior"):
            senior_net = econ.simulate(
                prices, w, tier, storm_days=econ.STORM_EARLY_DAYS,
                second_earner="taxi_driver",
                second_earner_tier="senior")["net"]
            mid_net = econ.simulate(
                prices, w, tier, storm_days=econ.STORM_EARLY_DAYS,
                second_earner="taxi_driver",
                second_earner_tier="mid")["net"]
            self.assertGreater(senior_net, mid_net, tier)
            senior_dip = econ.simulate(
                prices, w, tier, storm_days=econ.STORM_EARLY_DAYS,
                second_earner="taxi_driver",
                second_earner_tier="senior")["min_balance"]
            ce_dip = econ.simulate(
                prices, w, tier, storm_days=econ.STORM_EARLY_DAYS,
                second_earner="civil_engineer",
                second_earner_tier="senior")["min_balance"]
            self.assertEqual(senior_dip, 0, tier)
            self.assertLess(ce_dip, senior_dip, tier)

    def test_senior_taxi_driver_bridge_line_is_wired(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # The bridge worst is the minimum across the first
        # earner's tiers and the four storm positions.
        worst = min(
            econ.simulate(
                prices, w, tier, storm_days=pos,
                second_earner="taxi_driver",
                second_earner_tier="senior")["min_balance"]
            for tier in ("entry", "mid", "senior")
            for pos in (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                        econ.STORM_LATE_DAYS,
                        econ.STORM_MEASURED_DAYS))
        self.assertEqual(worst, 0)
        start = 5000 + 5000
        self.assertEqual(start + worst, 10000)
        # The printed output wires the row and the line in
        # both runs: the IC section header and the bridge
        # line (10,000 + 0 = 10,000, OK) in the default
        # run, and the same line in the --shibnagar variant's
        # own bridge check.
        for args in ([], ["--shibnagar"]):
            out = subprocess.run(
                [sys.executable,
                 os.path.join(ROOT, "tools", "economy_sim.py")]
                + args, capture_output=True, cwd=ROOT)
            text = out.stdout.decode()
            self.assertEqual(out.returncode, 0, args)
            self.assertIn(
                "taxi-driver second earner (senior 36,000,"
                " per-fare)", text, args)
            self.assertIn(
                "construction_worker + taxi-driver (senior)"
                " start  10000 + other-tier dip       0"
                " =   10000  OK", text, args)
            self.assertIn("BRIDGE FAIL rows: []", text, args)

    def test_second_earner_tier_uses_sourced_wages(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # The tier wages come from the source data, not the test:
        # mid taxi 23,000 (tax 400, uplift 35% of 9,000) and
        # entry civil engineer 22,000 (tax 350, uplift 0).
        wages = {x["profession_id"]: x
                 for x in prices["wages_monthly"]}
        self.assertEqual(wages["taxi_driver"]["mid"], 23000)
        self.assertEqual(wages["civil_engineer"]["entry"], 22000)
        taxi_mid = econ.simulate(
            prices, w, "entry", storm_days=econ.STORM_MEASURED_DAYS,
            second_earner="taxi_driver", second_earner_tier="mid")
        taxi_entry = econ.simulate(
            prices, w, "entry", storm_days=econ.STORM_MEASURED_DAYS,
            second_earner="taxi_driver")
        self.assertEqual(taxi_mid["gross"] - taxi_entry["gross"],
                         9000)
        self.assertEqual(taxi_mid["tax"] - taxi_entry["tax"], 400)
        self.assertEqual(taxi_mid["costs_total"]
                         - taxi_entry["costs_total"], 3150)
        ce_entry = econ.simulate(
            prices, w, "entry", storm_days=econ.STORM_MEASURED_DAYS,
            second_earner="civil_engineer",
            second_earner_tier="entry")
        ce_mid = econ.simulate(
            prices, w, "entry", storm_days=econ.STORM_MEASURED_DAYS,
            second_earner="civil_engineer")
        self.assertEqual(ce_mid["gross"] - ce_entry["gross"], 16000)
        self.assertEqual(ce_mid["tax"] - ce_entry["tax"], 800)
        self.assertEqual(ce_mid["costs_total"]
                         - ce_entry["costs_total"], 5600)
        # The default is still the measured tier — the kwarg
        # changes nothing unless it is given.
        self.assertEqual(taxi_entry["second_earner_tier"], "entry")
        self.assertEqual(ce_mid["second_earner_tier"], "mid")
        self.assertEqual(
            econ.simulate(prices, w, "entry",
                          storm_days=econ.STORM_MEASURED_DAYS,
                          second_earner="taxi_driver")
            ["min_balance"], 0)
        for tier in ("entry", "mid", "senior"):
            for pos in (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                        econ.STORM_LATE_DAYS,
                        econ.STORM_MEASURED_DAYS):
                for pid2, tier2 in (("taxi_driver", "mid"),
                                    ("civil_engineer", "entry")):
                    row = econ.simulate(
                        prices, w, tier, storm_days=pos,
                        second_earner=pid2,
                        second_earner_tier=tier2)
                    self.assertEqual(row["end_balance"], row["net"],
                                     f"{pid2}/{tier2}/{tier}/{pos}")

    def test_second_earner_tier_refusals(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # A tier override needs a mixed second earner — not the
        # same-tier case, not no second earner — and must name a
        # real tier.
        with self.assertRaises(ValueError):
            econ.simulate(prices, w, "entry", second_earner=True,
                          second_earner_tier="mid")
        with self.assertRaises(ValueError):
            econ.simulate(prices, w, "entry",
                          second_earner_tier="mid")
        with self.assertRaises(ValueError):
            econ.simulate(prices, w, "entry",
                          second_earner="taxi_driver",
                          second_earner_tier="principal")
        # Queue 28 Unit KA: the renting variant now combines
        # with a named tier for the taxi driver — the refusal
        # this test used to assert is gone (see the KA tests
        # below); a renting civil engineer stays refused
        # (civil engineers hold no cab).
        with self.assertRaises(ValueError):
            econ.simulate(prices, w, "entry",
                          second_earner="civil_engineer",
                          second_earner_renting_cab=True,
                          second_earner_tier="entry")

    # Queue 28 Unit KA — the renting-cab second earner at
    # another tier: the same mid-tier taxi driver (23,000,
    # per-fare) as §12's owning driver, but renting the
    # licensed cab at the settlement's flat 5,200/month. The
    # rental is the same at every tier — the tier moves the
    # pay, not the rental — so the net drops by exactly 5,200
    # against the owning mid-tier figures, and the early dip
    # the owning driver had closed re-opens only where the
    # household's daily cost outruns the taxi pay (senior:
    # 781/day of cost against 753/day of taxi pay, −28/day
    # for the two cost-only days = −56).
    def test_renting_cab_second_earner_at_another_tier_is_measured(
            self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # The measured position dips nothing at any tier; the
        # early position dips only at senior (−56).
        for tier, dip, net in (("entry", 0, 10950),
                               ("mid", 0, 14194),
                               ("senior", 0, 17651)):
            row = econ.simulate(
                prices, w, tier, storm_days=econ.STORM_MEASURED_DAYS,
                second_earner="taxi_driver",
                second_earner_tier="mid",
                second_earner_renting_cab=True)
            self.assertEqual(row["min_balance"], dip, tier)
            self.assertEqual(row["net"], net, tier)
            self.assertEqual(row["second_earner_rental"], 5200,
                             tier)
            self.assertTrue(row["second_earner_renting_cab"])
            self.assertEqual(row["second_earner_tier"], "mid",
                             tier)
            self.assertEqual(row["end_balance"], row["net"], tier)
        for tier, dip in (("entry", 0), ("mid", 0),
                          ("senior", -56)):
            row = econ.simulate(
                prices, w, tier, storm_days=econ.STORM_EARLY_DAYS,
                second_earner="taxi_driver",
                second_earner_tier="mid",
                second_earner_renting_cab=True)
            self.assertEqual(row["min_balance"], dip, tier)
        # Mid and late positions dip nothing at any tier.
        for tier in ("entry", "mid", "senior"):
            for pos in (econ.STORM_MID_DAYS, econ.STORM_LATE_DAYS):
                row = econ.simulate(
                    prices, w, tier, storm_days=pos,
                    second_earner="taxi_driver",
                    second_earner_tier="mid",
                    second_earner_renting_cab=True)
                self.assertEqual(row["min_balance"], 0,
                                 f"{tier}/{pos}")
        # The rental is exactly the settlement's charge:
        # 200/day × 26 worked days, read from the source data.
        self.assertEqual(
            prices["taxi_fares"]["cab_rental_ncr_per_day"]
            * econ.WORK_DAYS, 5200)
        # The tier wages come from the source data, not the
        # test: mid taxi 23,000.
        wages = {x["profession_id"]: x
                 for x in prices["wages_monthly"]}
        self.assertEqual(wages["taxi_driver"]["mid"], 23000)

    def test_renting_cab_second_earner_at_another_tier_costs_and_net(
            self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # The rental is a monthly cost line on top of the
        # owning mid-tier variant: costs +5,200, net −5,200,
        # gross and tax untouched, at every tier and every
        # position.
        for tier in ("entry", "mid", "senior"):
            for pos in (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                        econ.STORM_LATE_DAYS,
                        econ.STORM_MEASURED_DAYS):
                owning = econ.simulate(
                    prices, w, tier, storm_days=pos,
                    second_earner="taxi_driver",
                    second_earner_tier="mid")
                renting = econ.simulate(
                    prices, w, tier, storm_days=pos,
                    second_earner="taxi_driver",
                    second_earner_tier="mid",
                    second_earner_renting_cab=True)
                self.assertEqual(renting["costs_total"]
                                 - owning["costs_total"], 5200,
                                 f"{tier}/{pos}")
                self.assertEqual(owning["net"] - renting["net"],
                                 5200, f"{tier}/{pos}")
                self.assertEqual(renting["gross"], owning["gross"],
                                 f"{tier}/{pos}")
                self.assertEqual(renting["tax"], owning["tax"],
                                 f"{tier}/{pos}")
                self.assertEqual(renting["end_balance"],
                                 renting["net"], f"{tier}/{pos}")
        # The owning mid-tier driver charges no rental.
        owning = econ.simulate(
            prices, w, "entry", storm_days=econ.STORM_MEASURED_DAYS,
            second_earner="taxi_driver",
            second_earner_tier="mid")
        self.assertEqual(owning["second_earner_rental"], 0)
        self.assertFalse(owning["second_earner_renting_cab"])

    def test_renting_cab_second_earner_at_another_tier_refusals(
            self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # A renting civil engineer is meaningless — civil
        # engineers hold no cab — with or without a named
        # tier. The rental stays the taxi driver's alone: not
        # the same-tier second earner, and not a household
        # with no second earner.
        with self.assertRaises(ValueError):
            econ.simulate(prices, w, "entry",
                          second_earner="civil_engineer",
                          second_earner_renting_cab=True)
        with self.assertRaises(ValueError):
            econ.simulate(prices, w, "entry",
                          second_earner="civil_engineer",
                          second_earner_tier="entry",
                          second_earner_renting_cab=True)
        with self.assertRaises(ValueError):
            econ.simulate(prices, w, "entry", second_earner=True,
                          second_earner_renting_cab=True)
        with self.assertRaises(ValueError):
            econ.simulate(prices, w, "entry",
                          second_earner_renting_cab=True)
        # A named tier must still be a real tier, even with
        # the rental.
        with self.assertRaises(ValueError):
            econ.simulate(prices, w, "entry",
                          second_earner="taxi_driver",
                          second_earner_tier="principal",
                          second_earner_renting_cab=True)

    def test_renting_mid_tier_bridge_line_is_printed(self):
        import subprocess
        out = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools",
                                          "economy_sim.py")],
            capture_output=True, cwd=ROOT)
        self.assertEqual(out.returncode, 0)
        text = out.stdout.decode()
        # The worst renting dip is the senior early −56
        # against the combined canonical start 10,000.
        self.assertIn(
            "construction_worker + taxi-driver (mid, renting)"
            " start  10000 + renting dip     -56 =    9944  OK"
            "  (worst renting storm position)", text)
        self.assertIn("BRIDGE FAIL rows: []", text)

    def test_worst_renting_mid_tier_dip_is_measured(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # The worst dip is the minimum across the first
        # earner's tiers and the four storm positions: −56
        # (senior, early) — entry and mid dip nothing
        # anywhere, so the senior household sets the line.
        positions = (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                     econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS)
        worst = min(
            econ.simulate(prices, w, tier, storm_days=pos,
                          second_earner="taxi_driver",
                          second_earner_tier="mid",
                          second_earner_renting_cab=True)
            ["min_balance"]
            for tier in ("entry", "mid", "senior")
            for pos in positions)
        self.assertEqual(worst, -56)
        # The combined start is the sum of the two earners'
        # own genesis balances, read from the source data.
        profs = econ.load("professions.json")
        starts = {p["id"]: p.get("starting_balance_ncr", 0)
                  for p in profs["professions"]}
        self.assertEqual(starts["construction_worker"]
                         + starts["taxi_driver"], 10000)


class TestSundayExclusionAudit(unittest.TestCase):
    # Queue 28 Unit KB — the Sunday-exclusion audit (JB
    # follow-up): JB found the Sunday exclusion in the renting
    # row was a v5-daily-schedule leftover with no source behind
    # it. This audit reads every day-of-week use in the tool and
    # in the settlement path it mirrors, and finds no other
    # exclusion in a cost or pay line — the remaining uses are
    # schedule shaping (transcribed from the data's weekend
    # notes), a weekly cadence tick, and weather, not weekday,
    # effects. These tests pin the audit so a later unit cannot
    # reintroduce a weekday exclusion unnoticed.
    def test_no_day_of_week_exclusion_in_economy_tool(self):
        import os
        with open(os.path.join(ROOT, "tools", "economy_sim.py")) as f:
            src = f.read()
        # No weekday arithmetic anywhere in the tool — not
        # even in a comment: the v5 daily branch and the v1
        # renting rule are both retired.
        self.assertNotIn("day % 7", src)
        self.assertNotIn("weekday", src.lower())
        # "Sunday" survives only in the module docstring (the
        # history of the retired rules) and in # comments —
        # never in live code.
        lines = src.splitlines()
        doc_end = 1
        while lines[doc_end].strip() != '"""':
            doc_end += 1
        for i, ln in enumerate(lines):
            if "sunday" in ln.lower():
                self.assertTrue(
                    i <= doc_end or ln.strip().startswith("#"),
                    f"line {i + 1}: {ln}")
        # The three WORK_DAYS uses are all flat: the rental
        # (5,200), the headline extra, and the trajectory
        # (days 1–26) — no exclusion at any of them.
        self.assertIn('["cab_rental_ncr_per_day"] * WORK_DAYS',
                      src)
        self.assertIn(
            "extra_monthly = extra_daily_cost * WORK_DAYS", src)
        self.assertIn(
            "if extra_daily_cost and day <= WORK_DAYS:", src)

    def test_construction_worker_keeps_work_on_fridays(self):
        from tools.sim.tests.common import data, rng
        from tools.sim import scheduler
        d = data()
        needs = {"hunger": 90, "thirst": 90, "sleep": 90,
                 "rest": 90, "safety": 90, "social": 90,
                 "healthcare": 90, "financial": 90,
                 "education": 90, "development": 90}
        ctx = {"character_id": "NEX000001",
               "template_id": "construction_worker",
               "is_life_stage": False, "home_zone": "d1_old_town",
               "workplace_zone": d.professions[
                   "construction_worker"]["workplace_zone"]}
        # A work block on every day of a 30-day month,
        # including all four Fridays (day_index 4, 11, 18, 25)
        # — the Friday variant keeps the morning shift (work
        # ends 12:30), so a Friday is a worked day and the
        # day-wage rule pays it in full.
        for day in range(30):
            blocks, _ = scheduler.instantiate(
                d, ctx, day, rng(), needs=needs)
            self.assertTrue(
                any(b["activity"] == "work" for b in blocks),
                f"day {day}")

    def test_friday_work_loss_does_not_dock_monthly_pay(self):
        from tools.sim import labour
        # The Friday variant bends work blocks home for the
        # monthly-paid professions (civil engineer, teacher,
        # doctor on rotation, software developer) — but their
        # pay is the monthly wage, and the settlement docks
        # nothing: the broken-tool dock is 0 and wage_due_for
        # returns the full wage.
        self.assertEqual(
            labour.broken_tool_wage_dock(None, "NEX000001", 1,
                                         22000), 0)
        for pid, wage in (("civil_engineer", 22000),
                          ("teacher", 15000), ("doctor", 30000),
                          ("software_developer", 28000),
                          ("taxi_driver", 14000),
                          ("chef", 13000)):
            self.assertEqual(
                labour.wage_due_for(None, "NEX000001", pid, 1,
                                    wage), wage, pid)

    def test_weekly_tick_is_cadence_not_exclusion(self):
        import os
        with open(os.path.join(ROOT, "tools", "sim",
                               "engine.py")) as f:
            lines = f.read().splitlines()
        idx = next(i for i, ln in enumerate(lines)
                   if "day % 7 == 6" in ln)
        block = "\n".join(lines[idx:idx + 6])
        # The weekly tick runs the weekly passes — drift,
        # social, infrastructure — and touches no pay or cost
        # line.
        self.assertIn("weekly_drift", block)
        self.assertIn("_weekly_social", block)
        self.assertIn("weekly_update", block)
        for word in ("wage", "rental", "living", "cost"):
            self.assertNotIn(word, block.lower(), word)

    def test_settlement_pay_lines_have_no_weekday_rule(self):
        import os
        with open(os.path.join(ROOT, "tools", "sim",
                               "labour.py")) as f:
            labour_src = f.read()
        # The day-wage rule counts worked days from the stored
        # schedules — no weekday filter anywhere in the module.
        self.assertNotIn("day % 7", labour_src)
        self.assertNotIn("weekday", labour_src.lower())
        self.assertNotIn("sunday", labour_src.lower())
        with open(os.path.join(ROOT, "tools", "sim",
                               "engine.py")) as f:
            engine_src = f.read()
        # The settlement's rental is flat (JB), and the taxi
        # surge is weather, not weekday: rain/storm counts.
        self.assertIn(
            "taxi_rental_total += rental_day * econ.WORK_DAYS",
            engine_src)
        factor = next(ln for ln in engine_src.splitlines()
                      if ln.strip().startswith("taxi_factor"))
        self.assertIn("rain_days", factor)
        self.assertIn("storm_days", factor)


class TestTaxiWeatherSurge(unittest.TestCase):
    def test_taxi_weather_factor_is_measured(self):
        from tools import economy_sim as econ
        # The EY month's weather (seed ey-measure: rain on
        # day_index 2 and 28, storm on 3 and 22) is 2 rain days
        # + 2 storm days; the settlement's formula gives
        # exactly 1.05 — and all six taxi drivers in that
        # world settled at exactly band × 1.05.
        self.assertEqual(
            econ.TAXI_WEATHER_MEASURED_RAIN_DAYS, 2)
        self.assertEqual(
            econ.TAXI_WEATHER_MEASURED_STORM_DAYS, 2)
        self.assertEqual(
            econ.taxi_weather_factor(2, 2), 1.05)
        self.assertEqual(
            econ.taxi_weather_factor(
                econ.TAXI_WEATHER_MEASURED_RAIN_DAYS,
                econ.TAXI_WEATHER_MEASURED_STORM_DAYS), 1.05)
        # No weather, no surge — and the factor can never
        # fall below 1, so a flat taxi row is the
        # conservative case.
        self.assertEqual(econ.taxi_weather_factor(0, 0), 1.0)
        self.assertGreater(econ.taxi_weather_factor(30, 0), 1.0)
        self.assertGreater(econ.taxi_weather_factor(0, 30), 1.0)

    def test_single_earner_taxi_surge_is_measured(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        wages = {w["profession_id"]: w
                 for w in prices["wages_monthly"]}
        # Flat vs surged at the EY month's weather: the gross
        # is band × 1.05, the tax and the uplift are recomputed
        # on the surged gross (the settlement taxes what it
        # paid), and the trajectory still ends at net.
        for tier, gross, tax, uplift, net in (
                ("entry", 14700, 0, 245, 6955),
                ("mid", 24150, 457, 3552, 12641),
                ("senior", 37800, 1140, 8330, 20830)):
            flat = econ.simulate(prices, wages["taxi_driver"],
                                 tier)
            surged = econ.simulate(
                prices, wages["taxi_driver"], tier,
                taxi_rain_days=econ
                .TAXI_WEATHER_MEASURED_RAIN_DAYS,
                taxi_storm_days=econ
                .TAXI_WEATHER_MEASURED_STORM_DAYS)
            self.assertEqual(surged["gross"], gross, tier)
            self.assertEqual(surged["tax"], tax, tier)
            self.assertEqual(surged["uplift"], uplift, tier)
            self.assertEqual(surged["net"], net, tier)
            self.assertEqual(surged["taxi_factor"], 1.05, tier)
            self.assertEqual(flat["taxi_factor"], 1.0, tier)
            self.assertEqual(surged["end_balance"], surged["net"],
                             tier)
            self.assertEqual(surged["min_balance"], 0, tier)
        # The surge is the only change: the flat row is the
        # canonical band, untouched.
        flat = econ.simulate(prices, wages["taxi_driver"], "mid")
        self.assertEqual((flat["gross"], flat["tax"], flat["net"]),
                         (23000, 400, 11950))

    def test_renting_cab_single_earner_surge(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        wages = {w["profession_id"]: w
                 for w in prices["wages_monthly"]}
        cab = prices["taxi_fares"]["cab_rental_ncr_per_day"]
        # The surge lifts the gross; the rental stays the
        # flat 5,200 — the settlement charges it unsurged —
        # so the net rises by exactly the surged-gross gain
        # less the uplift on it (455 at entry).
        flat = econ.simulate(prices, wages["taxi_driver"], "entry",
                             extra_daily_cost=cab,
                             label_suffix=" (renting cab)")
        surged = econ.simulate(
            prices, wages["taxi_driver"], "entry",
            extra_daily_cost=cab, label_suffix=" (renting cab)",
            taxi_rain_days=econ.TAXI_WEATHER_MEASURED_RAIN_DAYS,
            taxi_storm_days=econ.TAXI_WEATHER_MEASURED_STORM_DAYS)
        self.assertEqual((flat["gross"], flat["net"]), (14000, 1300))
        self.assertEqual((surged["gross"], surged["net"]),
                         (14700, 1755))
        self.assertEqual(surged["end_balance"], surged["net"])
        self.assertEqual(surged["extra"], 5200)
        owning = econ.simulate(
            prices, wages["taxi_driver"], "entry",
            taxi_rain_days=econ.TAXI_WEATHER_MEASURED_RAIN_DAYS,
            taxi_storm_days=econ.TAXI_WEATHER_MEASURED_STORM_DAYS)
        self.assertEqual(surged["costs_total"]
                         - owning["costs_total"], 5200)

    def test_taxi_second_earner_surge_is_measured(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        # The surge shrinks all three early dips — the HD senior
        # dip, the KA renting senior dip, and the IB entry
        # renting dips — but closes none of them; the measured
        # position dips 0 flat and surged for every pairing and
        # tier; the nets rise by the second earner's
        # surged-gross gain (+455 entry, +691 mid). Queue 45
        # Unit MN: the senior owning pairing dips 0 flat and
        # surged at every tier — the per-fare senior pay already
        # covers the cost-only days — and its nets rise by
        # exactly the senior taxi surge (+1,080).
        cases = (
            ({"second_earner": "taxi_driver"}, "senior", -72, -42,
             17401, 17856),
            ({"second_earner": "taxi_driver",
              "second_earner_tier": "mid"}, "senior", 0, 0,
             22851, 23542),
            ({"second_earner": "taxi_driver",
              "second_earner_tier": "mid",
              "second_earner_renting_cab": True}, "senior", -56, -9,
             17651, 18342),
            ({"second_earner": "taxi_driver",
              "second_earner_renting_cab": True}, "senior", -419,
             -389, 12201, 12656),
            ({"second_earner": "taxi_driver",
              "second_earner_tier": "senior"}, "senior", 0, 0,
             30651, 31731),
        )
        for kw, tier, dip, surged_dip, net, surged_net in cases:
            flat = econ.simulate(
                prices, w, tier, storm_days=econ.STORM_EARLY_DAYS,
                **kw)
            surged = econ.simulate(
                prices, w, tier, storm_days=econ.STORM_EARLY_DAYS,
                taxi_rain_days=econ.TAXI_WEATHER_MEASURED_RAIN_DAYS,
                taxi_storm_days=econ.TAXI_WEATHER_MEASURED_STORM_DAYS,
                **kw)
            self.assertEqual(flat["min_balance"], dip, tier)
            self.assertEqual(surged["min_balance"], surged_dip,
                             tier)
            self.assertEqual(flat["net"], net, tier)
            self.assertEqual(surged["net"], surged_net, tier)
            self.assertEqual(surged["end_balance"], surged["net"],
                             tier)
        for kw in ({"second_earner": "taxi_driver"},
                   {"second_earner": "taxi_driver",
                    "second_earner_tier": "mid"},
                   {"second_earner": "taxi_driver",
                    "second_earner_tier": "mid",
                    "second_earner_renting_cab": True},
                   {"second_earner": "taxi_driver",
                    "second_earner_renting_cab": True},
                   {"second_earner": "taxi_driver",
                    "second_earner_tier": "senior"}):
            for tier in ("entry", "mid", "senior"):
                for pos in (econ.STORM_EARLY_DAYS,
                            econ.STORM_MID_DAYS, econ.STORM_LATE_DAYS,
                            econ.STORM_MEASURED_DAYS):
                    flat = econ.simulate(prices, w, tier,
                                         storm_days=pos, **kw)
                    surged = econ.simulate(
                        prices, w, tier, storm_days=pos,
                        taxi_rain_days=econ
                        .TAXI_WEATHER_MEASURED_RAIN_DAYS,
                        taxi_storm_days=econ
                        .TAXI_WEATHER_MEASURED_STORM_DAYS, **kw)
                    # The surge can only shrink a dip, never
                    # deepen one — so the flat bridge lines are
                    # the conservative case.
                    self.assertGreaterEqual(
                        surged["min_balance"], flat["min_balance"],
                        f"{tier}/{pos}")
                    self.assertEqual(surged["end_balance"],
                                     surged["net"], f"{tier}/{pos}")
        # The measured position dips nothing, flat or surged.
        for kw in ({"second_earner": "taxi_driver"},
                   {"second_earner": "taxi_driver",
                    "second_earner_tier": "mid"},
                   {"second_earner": "taxi_driver",
                    "second_earner_tier": "mid",
                    "second_earner_renting_cab": True},
                   {"second_earner": "taxi_driver",
                    "second_earner_renting_cab": True},
                   {"second_earner": "taxi_driver",
                    "second_earner_tier": "senior"}):
            for tier in ("entry", "mid", "senior"):
                flat = econ.simulate(
                    prices, w, tier,
                    storm_days=econ.STORM_MEASURED_DAYS, **kw)
                surged = econ.simulate(
                    prices, w, tier,
                    storm_days=econ.STORM_MEASURED_DAYS,
                    taxi_rain_days=econ
                    .TAXI_WEATHER_MEASURED_RAIN_DAYS,
                    taxi_storm_days=econ
                    .TAXI_WEATHER_MEASURED_STORM_DAYS, **kw)
                self.assertEqual(flat["min_balance"], 0,
                                 f"{tier}")
                self.assertEqual(surged["min_balance"], 0,
                                 f"{tier}")

    def test_senior_taxi_second_earner_surge_is_measured(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        bands = {w2["profession_id"]: w2
                 for w2 in prices["wages_monthly"]}
        # Queue 45 Unit MN: the senior taxi-driver second
        # earner in the surge table. It is per-fare, so its
        # gross DOES surge with the taxi weather — unlike the
        # monthly-paid senior civil engineer, which the taxi
        # surge cannot move by construction. Early dip 0 flat
        # and surged at every tier and storm position; nets
        # rise by exactly the senior single-earner taxi surge
        # delta (+1,080) at every tier.
        kw = {"second_earner": "taxi_driver",
              "second_earner_tier": "senior"}
        expected = (("entry", 23950, 25030),
                    ("mid", 27194, 28274),
                    ("senior", 30651, 31731))
        for tier, net, surged_net in expected:
            for pos in (econ.STORM_EARLY_DAYS,
                        econ.STORM_MID_DAYS, econ.STORM_LATE_DAYS,
                        econ.STORM_MEASURED_DAYS):
                flat = econ.simulate(prices, w, tier,
                                     storm_days=pos, **kw)
                surged = econ.simulate(
                    prices, w, tier, storm_days=pos,
                    taxi_rain_days=econ
                    .TAXI_WEATHER_MEASURED_RAIN_DAYS,
                    taxi_storm_days=econ
                    .TAXI_WEATHER_MEASURED_STORM_DAYS, **kw)
                self.assertEqual(flat["min_balance"], 0,
                                 f"{tier}/{pos}")
                self.assertEqual(surged["min_balance"], 0,
                                 f"{tier}/{pos}")
                self.assertEqual(flat["net"], net, f"{tier}/{pos}")
                self.assertEqual(surged["net"], surged_net,
                                 f"{tier}/{pos}")
                self.assertEqual(surged["net"] - flat["net"],
                                 1080, f"{tier}/{pos}")
                self.assertEqual(surged["end_balance"],
                                 surged["net"], f"{tier}/{pos}")
        # The delta is the senior single-earner taxi surge
        # delta, not a two-earner artefact — the second
        # earner's gross is the senior band at every
        # first-earner tier, so the household delta is the
        # senior delta (+1,080) at every tier, while the
        # single-earner deltas are per-tier (+455 / +691 /
        # +1,080).
        for tier, delta in (("entry", 455), ("mid", 691),
                            ("senior", 1080)):
            own_flat = econ.simulate(prices, bands["taxi_driver"],
                                     tier)
            own_surged = econ.simulate(
                prices, bands["taxi_driver"], tier,
                taxi_rain_days=econ
                .TAXI_WEATHER_MEASURED_RAIN_DAYS,
                taxi_storm_days=econ
                .TAXI_WEATHER_MEASURED_STORM_DAYS)
            self.assertEqual(own_surged["net"] - own_flat["net"],
                             delta, tier)

    def test_senior_renting_second_earner_surge_is_measured(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        bands = {w2["profession_id"]: w2
                 for w2 in prices["wages_monthly"]}
        # Queue 46 Unit MO: the renting senior-tier taxi
        # second earner on the KC surge pattern, beside the
        # now-printed senior owning row. The surge adds no
        # finding: early dip 0 flat and surged at every tier
        # and storm position, nets rise by exactly the senior
        # taxi surge (+1,080) at every tier, every net exactly
        # 5,200 below the owning surged net — the surged
        # figures are fully implied by the printed owning row
        # plus the flat 5,200 rental rule — so the pairing
        # stays allowed but unprinted (V7 §35).
        kw = {"second_earner": "taxi_driver",
              "second_earner_tier": "senior",
              "second_earner_renting_cab": True}
        own_kw = {"second_earner": "taxi_driver",
                  "second_earner_tier": "senior"}
        expected = (("entry", 18750, 19830),
                    ("mid", 21994, 23074),
                    ("senior", 25451, 26531))
        positions = (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                     econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS)
        weather = dict(
            taxi_rain_days=econ.TAXI_WEATHER_MEASURED_RAIN_DAYS,
            taxi_storm_days=econ
            .TAXI_WEATHER_MEASURED_STORM_DAYS)
        for tier, net, surged_net in expected:
            for pos in positions:
                flat = econ.simulate(prices, w, tier,
                                     storm_days=pos, **kw)
                surged = econ.simulate(
                    prices, w, tier, storm_days=pos,
                    **weather, **kw)
                own_surged = econ.simulate(
                    prices, w, tier, storm_days=pos,
                    **weather, **own_kw)
                self.assertEqual(flat["min_balance"], 0,
                                 f"{tier}/{pos}")
                self.assertEqual(surged["min_balance"], 0,
                                 f"{tier}/{pos}")
                self.assertEqual(flat["net"], net, f"{tier}/{pos}")
                self.assertEqual(surged["net"], surged_net,
                                 f"{tier}/{pos}")
                self.assertEqual(surged["net"] - flat["net"],
                                 1080, f"{tier}/{pos}")
                self.assertEqual(own_surged["net"] - surged["net"],
                                 5200, f"{tier}/{pos}")
                self.assertEqual(surged["end_balance"],
                                 surged["net"], f"{tier}/{pos}")
        # Identical on Shibnagar rents (the two-earner rows
        # rent at tier 1 in both cities — the MD identity).
        rents, _stock = econ.load_shibnagar_rents(prices)
        shib_cw = rents[econ.SHIBNAGAR_RENT_TIER[
            "construction_worker"]]
        for tier, net, surged_net in expected:
            for pos in positions:
                sh = econ.simulate(prices, w, tier,
                                   storm_days=pos,
                                   rent_override=shib_cw, **kw)
                sh_surged = econ.simulate(
                    prices, w, tier, storm_days=pos,
                    rent_override=shib_cw, **weather, **kw)
                self.assertEqual(sh["min_balance"], 0,
                                 f"shibnagar/{tier}/{pos}")
                self.assertEqual(sh_surged["min_balance"], 0,
                                 f"shibnagar/{tier}/{pos}")
                self.assertEqual(sh["net"], net,
                                 f"shibnagar/{tier}/{pos}")
                self.assertEqual(sh_surged["net"], surged_net,
                                 f"shibnagar/{tier}/{pos}")
                self.assertEqual(sh_surged["end_balance"],
                                 sh_surged["net"],
                                 f"shibnagar/{tier}/{pos}")

    def test_taxi_surge_at_second_weather_factors_is_measured(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        wages = {w["profession_id"]: w
                 for w in prices["wages_monthly"]}
        # Queue 47 Unit MP: the KC surge formula corroborated
        # at two more live factors — seed mo-probe-1 (1 rain +
        # 2 storm, factor 1.0417) and seed mo-probe-2 (4 rain +
        # 3 storm, factor 1.0833), both the EY shape (60
        # population, 32 days). The tool's gross at each
        # factor is round(band x factor), the same rounding
        # the settlement applies — 14,000 x 1.0417 is
        # 14,583.33 -> 14,583 (rounds down) and 23,000 x
        # 1.0833 is 24,916.67 -> 24,917 (rounds up) — and
        # the nets follow with tax and uplift recomputed on
        # the surged gross.
        self.assertAlmostEqual(econ.taxi_weather_factor(1, 2),
                               1.0416666666666667)
        self.assertAlmostEqual(econ.taxi_weather_factor(4, 3),
                               1.0833333333333335)
        for (rain, storm), rows in (
                ((1, 2), (("entry", 14583, 6879),
                          ("mid", 23958, 12525),
                          ("senior", 37500, 20650))),
                ((4, 3), (("entry", 15167, 7251),
                          ("mid", 24917, 13100),
                          ("senior", 39000, 21550)))):
            for tier, gross, net in rows:
                flat = econ.simulate(prices, wages["taxi_driver"],
                                     tier)
                surged = econ.simulate(
                    prices, wages["taxi_driver"], tier,
                    taxi_rain_days=rain, taxi_storm_days=storm)
                self.assertEqual(surged["gross"], gross,
                                 f"{rain}/{storm}/{tier}")
                self.assertEqual(surged["net"], net,
                                 f"{rain}/{storm}/{tier}")
                self.assertEqual(surged["end_balance"],
                                 surged["net"], f"{rain}/{storm}/"
                                 f"{tier}")
                self.assertEqual(surged["min_balance"], 0,
                                 f"{rain}/{storm}/{tier}")
                self.assertEqual(surged["gross"],
                                 round(flat["gross"]
                                       * econ.taxi_weather_factor(
                                           rain, storm)),
                                 f"{rain}/{storm}/{tier}")
        # The deltas are the per-tier surge at each factor,
        # not the EY factor's: +583 / +958 / +1,500 gross at
        # 1.0417 and +1,167 / +1,917 / +3,000 at 1.0833.
        for (rain, storm), deltas in (
                ((1, 2), (583, 958, 1500)),
                ((4, 3), (1167, 1917, 3000))):
            for tier, delta in zip(("entry", "mid", "senior"),
                                   deltas):
                flat = econ.simulate(prices, wages["taxi_driver"],
                                     tier)
                surged = econ.simulate(
                    prices, wages["taxi_driver"], tier,
                    taxi_rain_days=rain, taxi_storm_days=storm)
                self.assertEqual(surged["gross"] - flat["gross"],
                                 delta, f"{rain}/{storm}/{tier}")

    def test_taxi_surge_outside_the_band_is_measured(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        wages = {w["profession_id"]: w
                 for w in prices["wages_monthly"]}
        # Queue 48 Unit MQ: the KC surge formula corroborated
        # at two more live factors, both ABOVE the 1.04–1.09
        # band — seed mq-probe-1 (8 rain + 3 storm, factor
        # 1.1167) and seed mq-probe-6 (6 rain + 3 storm,
        # factor 1.1000), both the EY shape (60 population,
        # 32 days). Neither world holds a senior taxi driver,
        # so the senior grosses at these factors (40,200 /
        # 39,600) are tool-computed, not live-settled — the
        # test pins them as computed figures and the live
        # corroboration as entry + mid only. The tool's gross
        # at each factor is round(band x factor), the same
        # rounding the settlement applies — 14,000 x 1.1167
        # is 15,633.33 -> 15,633 (rounds down) and at 1.1000
        # the products are integers up to float error, so
        # rounding is a no-op — and the nets follow with tax
        # and uplift recomputed on the surged gross.
        self.assertAlmostEqual(econ.taxi_weather_factor(8, 3),
                               1.1166666666666667)
        self.assertAlmostEqual(econ.taxi_weather_factor(6, 3),
                               1.1000000000000001)
        for (rain, storm), rows in (
                ((8, 3), (("entry", 15633, 7529),
                          ("mid", 25683, 13560),
                          ("senior", 40200, 22260))),
                ((6, 3), (("entry", 15400, 7390),
                          ("mid", 25300, 13330),
                          ("senior", 39600, 21910)))):
            for tier, gross, net in rows:
                flat = econ.simulate(prices, wages["taxi_driver"],
                                     tier)
                surged = econ.simulate(
                    prices, wages["taxi_driver"], tier,
                    taxi_rain_days=rain, taxi_storm_days=storm)
                self.assertEqual(surged["gross"], gross,
                                 f"{rain}/{storm}/{tier}")
                self.assertEqual(surged["net"], net,
                                 f"{rain}/{storm}/{tier}")
                self.assertEqual(surged["end_balance"],
                                 surged["net"], f"{rain}/{storm}/"
                                 f"{tier}")
                self.assertEqual(surged["min_balance"], 0,
                                 f"{rain}/{storm}/{tier}")
                self.assertEqual(surged["gross"],
                                 round(flat["gross"]
                                       * econ.taxi_weather_factor(
                                           rain, storm)),
                                 f"{rain}/{storm}/{tier}")
        # The deltas are the per-tier surge at each factor,
        # not the EY factor's: +1,633 / +2,683 / +4,200 gross
        # at 1.1167 and +1,400 / +2,300 / +3,600 at 1.1000.
        for (rain, storm), deltas in (
                ((8, 3), (1633, 2683, 4200)),
                ((6, 3), (1400, 2300, 3600))):
            for tier, delta in zip(("entry", "mid", "senior"),
                                   deltas):
                flat = econ.simulate(prices, wages["taxi_driver"],
                                     tier)
                surged = econ.simulate(
                    prices, wages["taxi_driver"], tier,
                    taxi_rain_days=rain, taxi_storm_days=storm)
                self.assertEqual(surged["gross"] - flat["gross"],
                                 delta, f"{rain}/{storm}/{tier}")

    def test_taxi_surge_storm_heavy_month_is_measured(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        wages = {w["profession_id"]: w
                 for w in prices["wages_monthly"]}
        # Queue 49 Unit MR: the KC surge formula corroborated
        # at one more live factor, 1.1083, in a STORM-HEAVY
        # month above the band — seed mq-probe-11 (3 rain + 5
        # storm, one mid driver, settled 25,492) — and the
        # same factor from the opposite mix, seed mr-probe-7
        # (9 rain + 2 storm, entry + mid, settled 15,517 /
        # 25,492), both the EY shape (60 population, 32 days).
        # Neither world holds a senior taxi driver, so the
        # senior gross at this factor (39,900) is
        # tool-computed, not live-settled — the test pins it
        # as a computed figure and the live corroboration as
        # entry + mid only. The two mixes land on the same
        # factor and settle identically, so the settlement
        # keys on the factor, not the mix. The tool's gross
        # at the factor is round(band x factor), the same
        # rounding the settlement applies — and this time the
        # rounding goes UP at both settled tiers: 14,000 x
        # 1.1083 is 15,516.67 -> 15,517 and 23,000 x 1.1083
        # is 25,491.67 -> 25,492 — while the senior product
        # is an integer up to float error, so rounding is a
        # no-op there; and the nets follow with tax and
        # uplift recomputed on the surged gross.
        self.assertAlmostEqual(econ.taxi_weather_factor(3, 5),
                               1.1083333333333332)
        self.assertAlmostEqual(econ.taxi_weather_factor(9, 2),
                               1.1083333333333334)
        for (rain, storm), rows in (
                ((3, 5), (("entry", 15517, 7460),
                          ("mid", 25492, 13445),
                          ("senior", 39900, 22090))),
                ((9, 2), (("entry", 15517, 7460),
                          ("mid", 25492, 13445),
                          ("senior", 39900, 22090)))):
            for tier, gross, net in rows:
                flat = econ.simulate(prices, wages["taxi_driver"],
                                     tier)
                surged = econ.simulate(
                    prices, wages["taxi_driver"], tier,
                    taxi_rain_days=rain, taxi_storm_days=storm)
                self.assertEqual(surged["gross"], gross,
                                 f"{rain}/{storm}/{tier}")
                self.assertEqual(surged["net"], net,
                                 f"{rain}/{storm}/{tier}")
                self.assertEqual(surged["end_balance"],
                                 surged["net"], f"{rain}/{storm}/"
                                 f"{tier}")
                self.assertEqual(surged["min_balance"], 0,
                                 f"{rain}/{storm}/{tier}")
                self.assertEqual(surged["gross"],
                                 round(flat["gross"]
                                       * econ.taxi_weather_factor(
                                           rain, storm)),
                                 f"{rain}/{storm}/{tier}")
        # The deltas are the per-tier surge at 1.1083, not
        # the EY factor's: +1,517 / +2,492 / +3,900 gross.
        for (rain, storm), deltas in (
                ((3, 5), (1517, 2492, 3900)),
                ((9, 2), (1517, 2492, 3900))):
            for tier, delta in zip(("entry", "mid", "senior"),
                                   deltas):
                flat = econ.simulate(prices, wages["taxi_driver"],
                                     tier)
                surged = econ.simulate(
                    prices, wages["taxi_driver"], tier,
                    taxi_rain_days=rain, taxi_storm_days=storm)
                self.assertEqual(surged["gross"] - flat["gross"],
                                 delta, f"{rain}/{storm}/{tier}")
        # The two mixes settle identically at the same factor.
        self.assertEqual(
            econ.simulate(prices, wages["taxi_driver"], "mid",
                          taxi_rain_days=3,
                          taxi_storm_days=5)["gross"],
            econ.simulate(prices, wages["taxi_driver"], "mid",
                          taxi_rain_days=9,
                          taxi_storm_days=2)["gross"])

    def test_taxi_surge_senior_settled_above_band_is_measured(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        wages = {w["profession_id"]: w
                 for w in prices["wages_monthly"]}
        # Queue 50 Unit MS: the senior gross above the band
        # is now LIVE-SETTLED — seed ms-probe-11 (5 rain + 3
        # storm, factor 1.0917, four taxi drivers all
        # SYS-EMPLOYERS-paid, settled 15,283 / 25,108 /
        # 25,108 / 39,300) — and a second seeded month lands
        # on the SAME factor from different day positions,
        # seed ms-probe-7 (5 rain + 3 storm, two mid drivers,
        # both settled 25,108), both the EY shape (60
        # population, 32 days). The senior driver is
        # NEX000043 (taxi tier 5, 36,000) — the first senior
        # taxi driver to settle live above the band, so the
        # senior gross at this factor (39,300) is a measured
        # figure, not tool-computed. The settlement keys on
        # the counts, not the positions: the two months share
        # the counts and settle identically. The tool's gross
        # at the factor is round(band x factor), the same
        # rounding the settlement applies — and this time the
        # rounding goes DOWN at both settled lower tiers:
        # 14,000 x 1.0917 is 15,283.33 -> 15,283 and 23,000
        # x 1.0917 is 25,108.33 -> 25,108 — while the senior
        # product is an integer up to float error, so
        # rounding is a no-op there; and the nets follow with
        # tax and uplift recomputed on the surged gross.
        self.assertAlmostEqual(econ.taxi_weather_factor(5, 3),
                               1.0916666666666668)
        for tier, gross, net in (("entry", 15283, 7320),
                                 ("mid", 25108, 13215),
                                 ("senior", 39300, 21730)):
            flat = econ.simulate(prices, wages["taxi_driver"],
                                 tier)
            surged = econ.simulate(
                prices, wages["taxi_driver"], tier,
                taxi_rain_days=5, taxi_storm_days=3)
            self.assertEqual(surged["gross"], gross,
                             f"5/3/{tier}")
            self.assertEqual(surged["net"], net,
                             f"5/3/{tier}")
            self.assertEqual(surged["end_balance"],
                             surged["net"], f"5/3/{tier}")
            self.assertEqual(surged["min_balance"], 0,
                             f"5/3/{tier}")
            self.assertEqual(surged["gross"],
                             round(flat["gross"]
                                   * econ.taxi_weather_factor(
                                       5, 3)),
                             f"5/3/{tier}")
        # The deltas are the per-tier surge at 1.0917, not
        # the EY factor's: +1,283 / +2,108 / +3,300 gross.
        for tier, delta in zip(("entry", "mid", "senior"),
                               (1283, 2108, 3300)):
            flat = econ.simulate(prices, wages["taxi_driver"],
                                 tier)
            surged = econ.simulate(
                prices, wages["taxi_driver"], tier,
                taxi_rain_days=5, taxi_storm_days=3)
            self.assertEqual(surged["gross"] - flat["gross"],
                             delta, f"5/3/{tier}")
        # The two months settle identically at the same
        # factor, from different day positions.
        # The rounding at 1.0917 goes DOWN at both settled
        # lower tiers; the senior product is an integer up to
        # float error, so rounding is a no-op there.
        self.assertEqual(round(
            14000 * econ.taxi_weather_factor(5, 3)), 15283)
        self.assertEqual(round(
            23000 * econ.taxi_weather_factor(5, 3)), 25108)
        self.assertAlmostEqual(
            36000 * econ.taxi_weather_factor(5, 3), 39300)
        self.assertEqual(round(
            36000 * econ.taxi_weather_factor(5, 3)), 39300)

    def test_taxi_surge_second_senior_settled_above_band(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        wages = {w["profession_id"]: w
                 for w in prices["wages_monthly"]}
        # Queue 51 Unit MT: the senior gross above the band
        # is now LIVE-SETTLED at a second factor — seed
        # mt-probe-5 (7 rain + 3 storm, factor 1.1083, five
        # taxi drivers all SYS-EMPLOYERS-paid, four mid
        # settled 25,492 and senior NEX000047 settled
        # 39,900) — and a second seeded month lands on the
        # MS factor, seed mt-probe-13 (5 rain + 3 storm,
        # factor 1.0917, four mid settled 25,108 and senior
        # NEX000028 settled 39,300), both the EY shape (60
        # population, 32 days). The tool's gross at the
        # factor is round(band x factor), the same rounding
        # the settlement applies — and this time the rounding
        # goes UP at both lower tiers: 14,000 x 1.1083 is
        # 15,516.67 -> 15,517 and 23,000 x 1.1083 is
        # 25,491.67 -> 25,492, as MR already measured at this
        # factor — while the senior product is exactly
        # 39,900.0, so rounding is a no-op there; and the
        # nets follow with tax and uplift recomputed on the
        # surged gross. The senior rounding question is
        # closed by construction: 36,000 x 0.25/30 is 300
        # per rain day and 36,000 x 0.5/30 is 600 per storm
        # day, so the senior gross is 36,000 + 300 x rain +
        # 600 x storm — always an integer up to float error.
        self.assertAlmostEqual(econ.taxi_weather_factor(7, 3),
                               1.1083333333333334)
        for tier, gross, net in (("entry", 15517, 7460),
                                 ("mid", 25492, 13445),
                                 ("senior", 39900, 22090)):
            flat = econ.simulate(prices, wages["taxi_driver"],
                                 tier)
            surged = econ.simulate(
                prices, wages["taxi_driver"], tier,
                taxi_rain_days=7, taxi_storm_days=3)
            self.assertEqual(surged["gross"], gross,
                             f"7/3/{tier}")
            self.assertEqual(surged["net"], net,
                             f"7/3/{tier}")
            self.assertEqual(surged["end_balance"],
                             surged["net"], f"7/3/{tier}")
            self.assertEqual(surged["min_balance"], 0,
                             f"7/3/{tier}")
            self.assertEqual(surged["gross"],
                             round(flat["gross"]
                                   * econ.taxi_weather_factor(
                                       7, 3)),
                             f"7/3/{tier}")
        # The deltas are the per-tier surge at 1.1083: +1,517
        # / +2,492 / +3,900 gross.
        for tier, delta in zip(("entry", "mid", "senior"),
                               (1517, 2492, 3900)):
            flat = econ.simulate(prices, wages["taxi_driver"],
                                 tier)
            surged = econ.simulate(
                prices, wages["taxi_driver"], tier,
                taxi_rain_days=7, taxi_storm_days=3)
            self.assertEqual(surged["gross"] - flat["gross"],
                             delta, f"7/3/{tier}")
        # The rounding at 1.1083 goes UP at both lower tiers;
        # the senior product is exactly an integer, so
        # rounding is a no-op there.
        self.assertEqual(round(
            14000 * econ.taxi_weather_factor(7, 3)), 15517)
        self.assertEqual(round(
            23000 * econ.taxi_weather_factor(7, 3)), 25492)
        self.assertEqual(
            36000 * econ.taxi_weather_factor(7, 3), 39900.0)
        self.assertEqual(round(
            36000 * econ.taxi_weather_factor(7, 3)), 39900)
        # The second live senior settlement at the MS factor
        # (mt-probe-13, 1.0917): the senior gross is 39,300.
        senior_5_3 = econ.simulate(
            prices, wages["taxi_driver"], "senior",
            taxi_rain_days=5, taxi_storm_days=3)
        self.assertEqual(senior_5_3["gross"], 39300)
        self.assertEqual(senior_5_3["net"], 21730)
        # The senior product is an integer at every factor, up
        # to float error: 36,000 + 300 x rain + 600 x storm,
        # for every rain count 0..9 and storm count 0..5 —
        # round() always lands on the integer.
        for rain in range(10):
            for storm in range(6):
                self.assertAlmostEqual(
                    36000 * econ.taxi_weather_factor(rain,
                                                     storm),
                    36000 + 300 * rain + 600 * storm, places=9)
                self.assertEqual(
                    round(36000 * econ.taxi_weather_factor(
                        rain, storm)),
                    36000 + 300 * rain + 600 * storm)

    def test_taxi_surge_senior_settled_at_11000_and_no_11167(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        wages = {w["profession_id"]: w
                 for w in prices["wages_monthly"]}
        # Queue 52 Unit MU: the hunt for a senior settlement
        # at 1.1167 found NONE in twenty-four fresh seeds
        # (mu-probe-1..mu-probe-24, EY shape, 60 population,
        # 32 days) — no month in the sweep reaches 1.1167 at
        # all (highest factor 1.1000), so the senior gross at
        # 1.1167 (40,200) stays tool-computed only. The sweep
        # still measures something real: the senior gross at
        # 1.1000 (39,600) is now LIVE-SETTLED — seed
        # mu-probe-8 (6 rain + 3 storm, factor 1.1000, three
        # taxi drivers all SYS-EMPLOYERS-paid, two mid
        # settled 25,300 and senior NEX000012 settled 39,600)
        # and seed mu-probe-16 (8 rain + 2 storm, the SAME
        # factor 1.1000 from the opposite mix, nine taxi
        # drivers all SYS-EMPLOYERS-paid, two entry settled
        # 15,400, five mid settled 25,300 and two seniors
        # NEX000045 and NEX000060 settled 39,600) — so the
        # settlement keys on the factor, not the mix, at
        # 1.1000 as MR already measured at 1.1083. A third
        # live senior settlement at 1.0917 also lands — seed
        # mu-probe-3 (7 rain + 2 storm, factor 1.0917 from a
        # different mix than MS/MT's 5 + 3, two taxi drivers
        # all SYS-EMPLOYERS-paid, mid settled 25,108 and
        # senior NEX000029 settled 39,300). The tool's gross
        # at the factor is round(band x factor), the same
        # rounding the settlement applies — and at 1.1000 the
        # rounding is a no-op at every tier (the products are
        # integers up to float error); the nets follow with
        # tax and uplift recomputed on the surged gross.
        self.assertAlmostEqual(econ.taxi_weather_factor(8, 2),
                               1.1)
        self.assertAlmostEqual(econ.taxi_weather_factor(6, 3),
                               1.1)
        for tier, gross, net in (("entry", 15400, 7390),
                                 ("mid", 25300, 13330),
                                 ("senior", 39600, 21910)):
            for rain, storm in ((8, 2), (6, 3)):
                flat = econ.simulate(prices,
                                     wages["taxi_driver"], tier)
                surged = econ.simulate(
                    prices, wages["taxi_driver"], tier,
                    taxi_rain_days=rain, taxi_storm_days=storm)
                self.assertEqual(surged["gross"], gross,
                                 f"{rain}/{storm}/{tier}")
                self.assertEqual(surged["net"], net,
                                 f"{rain}/{storm}/{tier}")
                self.assertEqual(surged["end_balance"],
                                 surged["net"],
                                 f"{rain}/{storm}/{tier}")
                self.assertEqual(surged["min_balance"], 0,
                                 f"{rain}/{storm}/{tier}")
                self.assertEqual(surged["gross"],
                                 round(flat["gross"]
                                       * econ.taxi_weather_factor(
                                           rain, storm)),
                                 f"{rain}/{storm}/{tier}")
        # The deltas are the per-tier surge at 1.1000: +1,400
        # / +2,300 / +3,600 gross.
        for tier, delta in zip(("entry", "mid", "senior"),
                               (1400, 2300, 3600)):
            flat = econ.simulate(prices, wages["taxi_driver"],
                                 tier)
            surged = econ.simulate(
                prices, wages["taxi_driver"], tier,
                taxi_rain_days=8, taxi_storm_days=2)
            self.assertEqual(surged["gross"] - flat["gross"],
                             delta, f"8/2/{tier}")
        # The rounding at 1.1000 is a no-op at every tier:
        # each product is an integer up to float error.
        for band, gross in ((14000, 15400), (23000, 25300),
                            (36000, 39600)):
            self.assertAlmostEqual(
                band * econ.taxi_weather_factor(8, 2), gross,
                places=9)
            self.assertEqual(
                round(band * econ.taxi_weather_factor(8, 2)),
                gross)
        # The third live senior settlement at 1.0917
        # (mu-probe-3, 7 rain + 2 storm): the senior gross is
        # 39,300, from a different mix than MS/MT's 5 + 3.
        senior_7_2 = econ.simulate(
            prices, wages["taxi_driver"], "senior",
            taxi_rain_days=7, taxi_storm_days=2)
        self.assertEqual(senior_7_2["gross"], 39300)
        self.assertEqual(senior_7_2["net"], 21730)
        # The hunt's target stays tool-computed only: factor
        # 1.1167 is 8 rain + 3 storm (r + 2s = 14), and the
        # tool's senior gross there is 40,200 — no senior has
        # settled live at it.
        self.assertAlmostEqual(econ.taxi_weather_factor(8, 3),
                               1.1166666666666667)
        senior_8_3 = econ.simulate(
            prices, wages["taxi_driver"], "senior",
            taxi_rain_days=8, taxi_storm_days=3)
        self.assertEqual(senior_8_3["gross"], 40200)

    def test_taxi_surge_senior_settled_live_at_11167(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        wages = {w["profession_id"]: w
                 for w in prices["wages_monthly"]}
        # Queue 53 Unit MV: the senior gross at 1.1167
        # (40,200) is now LIVE-SETTLED — twice, from two
        # different mixes. MU proved the month's weather is
        # seed-only, so MV scanned 200 fresh seeds
        # (mv-probe-1..mv-probe-200) on the weather signature
        # alone (rain + 2 x storm = 14) without running the
        # population, then ran the full EY shape (60
        # population, 32 days) only on the 5 matches:
        # mv-probe-3 (6 rain + 4 storm), mv-probe-38 (4 + 5),
        # mv-probe-105 (8 + 3, MQ's mix), mv-probe-106
        # (6 + 4) and mv-probe-115 (4 + 5). All five months
        # are factor 1.1167, 15 taxi drivers in all, all
        # SYS-EMPLOYERS-paid, every settled gross round(band
        # x factor): mv-probe-105 holds senior NEX000014
        # settled 40,200 (five drivers: entry 15,633, mid
        # 25,683 x 3, senior 40,200) and mv-probe-115 holds
        # senior NEX000053 settled 40,200 (three drivers:
        # mid 25,683 x 2, senior 40,200) — so the settlement
        # keys on the factor, not the mix, at 1.1167 as MR
        # already measured at 1.1083 and MU at 1.1000. The
        # tool's gross at the factor is round(band x factor),
        # the same rounding the settlement applies — and at
        # 1.1167 the rounding goes down at both lower tiers
        # (15,633.33 -> 15,633; 25,683.33 -> 25,683) while
        # the senior product is exactly 40,200.0; the nets
        # follow with tax and uplift recomputed on the
        # surged gross.
        self.assertAlmostEqual(econ.taxi_weather_factor(8, 3),
                               1.1166666666666667)
        self.assertAlmostEqual(econ.taxi_weather_factor(4, 5),
                               1.1166666666666667)
        self.assertAlmostEqual(econ.taxi_weather_factor(6, 4),
                               1.1166666666666667)
        for tier, gross, net in (("entry", 15633, 7529),
                                 ("mid", 25683, 13560),
                                 ("senior", 40200, 22260)):
            for rain, storm in ((8, 3), (4, 5), (6, 4)):
                flat = econ.simulate(prices,
                                     wages["taxi_driver"], tier)
                surged = econ.simulate(
                    prices, wages["taxi_driver"], tier,
                    taxi_rain_days=rain, taxi_storm_days=storm)
                self.assertEqual(surged["gross"], gross,
                                 f"{rain}/{storm}/{tier}")
                self.assertEqual(surged["net"], net,
                                 f"{rain}/{storm}/{tier}")
                self.assertEqual(surged["end_balance"],
                                 surged["net"],
                                 f"{rain}/{storm}/{tier}")
                self.assertEqual(surged["min_balance"], 0,
                                 f"{rain}/{storm}/{tier}")
                self.assertEqual(surged["gross"],
                                 round(flat["gross"]
                                       * econ.taxi_weather_factor(
                                           rain, storm)),
                                 f"{rain}/{storm}/{tier}")
        # The deltas are the per-tier surge at 1.1167: +1,633
        # / +2,683 / +4,200 gross.
        for tier, delta in zip(("entry", "mid", "senior"),
                               (1633, 2683, 4200)):
            flat = econ.simulate(prices, wages["taxi_driver"],
                                 tier)
            surged = econ.simulate(
                prices, wages["taxi_driver"], tier,
                taxi_rain_days=8, taxi_storm_days=3)
            self.assertEqual(surged["gross"] - flat["gross"],
                             delta, f"8/3/{tier}")
        # The rounding at 1.1167 goes down at both lower
        # tiers and is a no-op at the senior tier: the
        # senior product is exactly 40,200.0.
        for band, gross in ((14000, 15633), (23000, 25683)):
            product = band * econ.taxi_weather_factor(8, 3)
            self.assertGreater(product, gross)
            self.assertLess(product, gross + 1)
            self.assertEqual(round(product), gross)
        self.assertEqual(
            36000 * econ.taxi_weather_factor(8, 3), 40200.0)
        self.assertEqual(
            round(36000 * econ.taxi_weather_factor(8, 3)),
            40200)
        # The 1.1167 senior gross is no longer
        # tool-computed only: it is live-settled at two
        # seeds, from two mixes, and the senior tier above
        # the band now rests on four live factors (1.0917,
        # 1.1000, 1.1083, 1.1167).

    def test_taxi_weather_refusals(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        wages = {w["profession_id"]: w
                 for w in prices["wages_monthly"]}
        w = wages["construction_worker"]
        # No taxi gross to scale: a monthly row, a day-wage
        # row with no taxi earner, and a civil-engineer
        # second earner all refuse.
        with self.assertRaises(ValueError):
            econ.simulate(prices, wages["teacher"], "entry",
                          taxi_rain_days=2, taxi_storm_days=2)
        with self.assertRaises(ValueError):
            econ.simulate(prices, w, "entry", taxi_rain_days=2)
        with self.assertRaises(ValueError):
            econ.simulate(prices, w, "entry",
                          second_earner="civil_engineer",
                          taxi_rain_days=2)
        # The counts are day counts in one 30-day month.
        with self.assertRaises(ValueError):
            econ.simulate(prices, wages["taxi_driver"], "entry",
                          taxi_rain_days=31)
        with self.assertRaises(ValueError):
            econ.simulate(prices, wages["taxi_driver"], "entry",
                          taxi_storm_days=-1)
        with self.assertRaises(ValueError):
            econ.simulate(prices, wages["taxi_driver"], "entry",
                          taxi_rain_days=20, taxi_storm_days=11)
        with self.assertRaises(ValueError):
            econ.simulate(prices, wages["taxi_driver"], "entry",
                          taxi_rain_days=2.5)
        # A business P&L is not a wage: no taxi weather there.
        with self.assertRaises(ValueError):
            econ.simulate(prices, wages["shop_owner"], "entry",
                          taxi_rain_days=2)

    def test_taxi_surge_section_is_printed(self):
        import subprocess
        out = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools",
                                          "economy_sim.py")],
            capture_output=True, cwd=ROOT)
        self.assertEqual(out.returncode, 0)
        text = out.stdout.decode()
        self.assertIn(
            "taxi weather-surge month (Unit KC — the EY month's "
            "weather: 2 rain days, 2 storm days, taxi_factor"
            " 1.05", text)
        self.assertIn(
            "taxi_driver                  entry        14000"
            "   14700     6500       6955      +455", text)
        self.assertIn(
            "taxi_driver (renting cab)    entry        14000"
            "   14700     1300       1755      +455", text)
        self.assertIn(
            "taxi-driver second earner weather-surge month"
            " (Unit KC", text)
        self.assertIn(
            "taxi-driver (mid, renting)   senior         -56"
            "           -9    17651      18342", text)
        # The bridge lines stay flat — the KC section is the
        # only diff vs the KA baseline.
        self.assertIn(
            "construction_worker + taxi-driver (mid, renting)"
            " start  10000 + renting dip     -56 =    9944  OK"
            "  (worst renting storm position)", text)
        self.assertIn("BRIDGE FAIL rows: []", text)


class TestShibnagarTwoEarnerBridge(unittest.TestCase):
    def test_two_earner_rows_are_identical_on_shibnagar_rents(
            self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        rents, _stock = econ.load_shibnagar_rents(prices)
        # Shibnagar's tier-1 rent is the prices.json tier-1
        # rent (2,500) — asserted by load_shibnagar_rents,
        # not assumed — and the two-earner first earner is
        # always the construction worker (tier 1), so the
        # figures must be identical by construction.
        tier1 = next(r["rent_ncr"]
                     for r in prices["rent_monthly_by_tier"]
                     if r["tier"] == 1)
        self.assertEqual(rents[1], tier1)
        self.assertEqual(
            rents[econ.SHIBNAGAR_RENT_TIER["construction_worker"]],
            tier1)
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        override = rents[1]
        pairings = (
            {"second_earner": True},
            {"second_earner": "taxi_driver"},
            {"second_earner": "taxi_driver",
             "second_earner_tier": "mid"},
            {"second_earner": "taxi_driver",
             "second_earner_tier": "mid",
             "second_earner_renting_cab": True},
            {"second_earner": "civil_engineer"},
            {"second_earner": "civil_engineer",
             "second_earner_tier": "entry"},
        )
        positions = (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                     econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS)
        checked = 0
        for kw in pairings:
            for tier in ("entry", "mid", "senior"):
                for pos in positions:
                    d1 = econ.simulate(prices, w, tier,
                                       storm_days=pos, **kw)
                    sh = econ.simulate(prices, w, tier,
                                       storm_days=pos,
                                       rent_override=override,
                                       **kw)
                    self.assertEqual(sh["min_balance"],
                                     d1["min_balance"],
                                     f"{kw}/{tier}/{pos}")
                    self.assertEqual(sh["net"], d1["net"],
                                     f"{kw}/{tier}/{pos}")
                    self.assertEqual(sh["end_balance"],
                                     d1["end_balance"],
                                     f"{kw}/{tier}/{pos}")
                    checked += 1
        self.assertEqual(checked, 72)

    def test_shibnagar_bridge_check_prints_two_earner_lines(
            self):
        import subprocess
        out = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools",
                                          "economy_sim.py"),
             "--shibnagar"],
            capture_output=True, cwd=ROOT)
        self.assertEqual(out.returncode, 0)
        text = out.stdout.decode()
        # All six two-earner lines, with the District 1
        # figures — the variant's check now stands on its own
        # rents instead of leaving the lines to the D1 run.
        for line in (
                "construction_worker + taxi-driver    start"
                "  10000 + mixed dip     -72 =    9928  OK"
                "  (worst mixed storm position)",
                "construction_worker + civil-engineer start"
                "  30000 + mixed dip   -8623 =   21377  OK"
                "  (worst mixed storm position)",
                "construction_worker + construction-worker"
                " start  10000 + same-tier dip   -1231 ="
                "    8769  OK  (worst same-tier storm position)",
                "construction_worker + taxi-driver (mid) start"
                "  10000 + other-tier dip       0 =   10000  OK"
                "  (worst other-tier storm position)",
                "construction_worker + civil-engineer (entry)"
                " start  30000 + other-tier dip   -3210 ="
                "   26790  OK  (worst other-tier storm position)",
                "construction_worker + taxi-driver (mid, renting)"
                " start  10000 + renting dip     -56 =    9944"
                "  OK  (worst renting storm position)"):
            self.assertIn(line, text)
        self.assertIn("shibnagar BRIDGE FAIL rows: []", text)

    def test_shibnagar_two_earner_lines_match_district1(self):
        import subprocess
        d1 = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools",
                                          "economy_sim.py")],
            capture_output=True, cwd=ROOT)
        sh = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools",
                                          "economy_sim.py"),
             "--shibnagar"],
            capture_output=True, cwd=ROOT)
        self.assertEqual(d1.returncode, 0)
        self.assertEqual(sh.returncode, 0)
        d1_text, sh_text = d1.stdout.decode(), sh.stdout.decode()
        # Every two-earner bridge line the D1 run prints, the
        # variant prints with the same figures.
        for label in ("construction_worker + taxi-driver ",
                      "construction_worker + civil-engineer ",
                      "construction_worker + construction-worker",
                      "construction_worker + taxi-driver (mid)",
                      "construction_worker + civil-engineer (entry)",
                      "construction_worker + taxi-driver (mid,"
                      " renting)"):
            d1_line = next(ln for ln in d1_text.splitlines()
                           if ln.strip().startswith(label))
            sh_line = next(ln for ln in sh_text.splitlines()
                           if ln.strip().startswith(label))
            self.assertEqual(sh_line, d1_line, label)


class TestShibnagarStormBridge(unittest.TestCase):
    """Queue 30 Unit KE — the single-earner storm line in the
    --shibnagar variant's bridge check (Unit KD wired the
    two-earner lines; the GE storm line was still District 1
    only)."""

    def test_single_earner_storm_dip_is_identical_on_shibnagar_rents(
            self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        rents, _stock = econ.load_shibnagar_rents(prices)
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        override = rents[econ.SHIBNAGAR_RENT_TIER[
            "construction_worker"]]
        # Every storm position identical on Shibnagar rents —
        # the tier-1 rent is 2,500 in both cities — and the
        # worst dip is the early position, -500.
        for pos, dip in ((econ.STORM_EARLY_DAYS, -500),
                         (econ.STORM_MID_DAYS, 0),
                         (econ.STORM_LATE_DAYS, 0),
                         (econ.STORM_MEASURED_DAYS, -100)):
            d1 = econ.simulate(prices, w, "entry",
                               storm_days=pos)
            sh = econ.simulate(prices, w, "entry",
                               storm_days=pos,
                               rent_override=override)
            self.assertEqual(d1["min_balance"], dip, str(pos))
            self.assertEqual(sh["min_balance"], dip, str(pos))
            self.assertEqual(sh["net"], d1["net"], str(pos))
            self.assertEqual(sh["end_balance"], d1["end_balance"],
                             str(pos))
        worst = min(econ.simulate(
            prices, w, "entry", storm_days=pos,
            rent_override=override)["min_balance"]
            for pos in (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                        econ.STORM_LATE_DAYS,
                        econ.STORM_MEASURED_DAYS))
        self.assertEqual(worst, -500)

    def test_shibnagar_bridge_check_prints_storm_line(self):
        import subprocess
        out = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools",
                                          "economy_sim.py"),
             "--shibnagar"],
            capture_output=True, cwd=ROOT)
        self.assertEqual(out.returncode, 0)
        text = out.stdout.decode()
        # The storm line, with the District 1 figure, in the
        # variant's own bridge check — not only in the D1 run.
        variant = text.split(
            "shibnagar first-month bridge check")[1]
        self.assertIn(
            "construction_worker    start   5000 + storm dip"
            "    -726 =    4274  OK  (worst storm position,"
            " all tiers)",
            variant)
        self.assertIn("shibnagar BRIDGE FAIL rows: []", text)

    def test_shibnagar_storm_line_matches_district1(self):
        import subprocess
        d1 = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", "economy_sim.py")],
            capture_output=True, cwd=ROOT)
        sh = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools",
                                          "economy_sim.py"),
             "--shibnagar"],
            capture_output=True, cwd=ROOT)
        self.assertEqual(d1.returncode, 0)
        self.assertEqual(sh.returncode, 0)
        d1_text, sh_text = d1.stdout.decode(), sh.stdout.decode()
        # The storm line the D1 run prints, the variant prints
        # with the same figures.
        label = "construction_worker    start   5000 + storm dip"
        d1_line = next(ln for ln in d1_text.splitlines()
                       if label in ln)
        sh_variant = sh_text.split(
            "shibnagar first-month bridge check")[1]
        sh_line = next(ln for ln in sh_variant.splitlines()
                       if label in ln)
        self.assertEqual(sh_line, d1_line)


    # Queue 31 Unit LA — the single-earner storm line sweeps
    # tiers: the printed dip is the minimum across the
    # construction worker's tiers and the four storm positions
    # (entry −500, mid −595, senior −726 — early worst at every
    # tier), and the Shibnagar line sweeps the same way on its
    # own rents, so the two lines agree.
    def test_storm_line_sweeps_all_tiers(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        positions = (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                     econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS)
        for tier, worst in (("entry", -500), ("mid", -595),
                            ("senior", -726)):
            dips = [econ.simulate(prices, w, tier, storm_days=pos)
                    ["min_balance"] for pos in positions]
            self.assertEqual(min(dips), worst, tier)
        # The printed line's dip is the cross-tier minimum,
        # not the entry row's: 5,000 − 726 = 4,274.
        import subprocess
        out = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools",
                                          "economy_sim.py")],
            capture_output=True, cwd=ROOT)
        self.assertEqual(out.returncode, 0)
        text = out.stdout.decode()
        line = next(ln for ln in text.splitlines()
                    if "storm dip" in ln)
        self.assertIn("-726 =    4274", line)
        self.assertIn("(worst storm position, all tiers)", line)

    def test_shibnagar_storm_line_sweeps_all_tiers(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "construction_worker")
        rents, _stock = econ.load_shibnagar_rents(prices)
        override = rents[econ.SHIBNAGAR_RENT_TIER
                         ["construction_worker"]]
        positions = (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                     econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS)
        # Every tier's worst dip is identical on Shibnagar
        # rents — the rent is the tier-1 rent in both cities
        # and the dip is the first earner's own.
        for tier, worst in (("entry", -500), ("mid", -595),
                            ("senior", -726)):
            dips = [econ.simulate(prices, w, tier, storm_days=pos,
                                  rent_override=override)
                    ["min_balance"] for pos in positions]
            self.assertEqual(min(dips), worst, tier)
        import subprocess
        sh = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools",
                                          "economy_sim.py"),
             "--shibnagar"],
            capture_output=True, cwd=ROOT)
        self.assertEqual(sh.returncode, 0)
        variant = sh.stdout.decode().split(
            "shibnagar first-month bridge check")[1]
        line = next(ln for ln in variant.splitlines()
                    if "storm dip" in ln)
        self.assertIn("-726 =    4274", line)
        self.assertIn("(worst storm position, all tiers)", line)


class TestRentingCabRowAtAllTiers(unittest.TestCase):
    def test_renting_cab_rows_at_all_tiers_are_measured(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "taxi_driver")
        cab = prices["taxi_fares"]["cab_rental_ncr_per_day"]
        # The rental is the same flat 5,200/month at every
        # tier (200 x WORK_DAYS 26, the settlement rule) — the
        # tier moves the pay, not the rental.
        self.assertEqual(cab * econ.WORK_DAYS, 5200)
        expected = (("entry", 14000, 0, 1300, 9.3, True),
                    ("mid", 23000, 400, 6750, 29.3, False),
                    ("senior", 36000, 1050, 14550, 40.4, False))
        for tier, gross, tax, net, rate, tight in expected:
            owning = econ.simulate(prices, w, tier)
            renting = econ.simulate(
                prices, w, tier, extra_daily_cost=cab,
                label_suffix=" (renting cab)")
            self.assertEqual(
                (renting["gross"], renting["tax"],
                 renting["extra"], renting["net"],
                 renting["rate"], renting["min_balance"]),
                (gross, tax, 5200, net, rate, 0), tier)
            self.assertEqual(renting["end_balance"],
                             renting["net"], tier)
            self.assertEqual(owning["net"] - renting["net"],
                             5200, tier)
            self.assertEqual("TIGHT" in renting["flags"], tight,
                             tier)

    def test_base_table_has_three_renting_rows(self):
        import subprocess
        out = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools",
                                          "economy_sim.py")],
            capture_output=True, cwd=ROOT)
        self.assertEqual(out.returncode, 0)
        text = out.stdout.decode()
        self.assertIn("rows: 36", text)
        self.assertIn(
            "taxi_driver (renting cab)    entry     14000"
            "      0   2500  12700     1300    9.3        0"
            "  TIGHT", text)
        self.assertIn(
            "taxi_driver (renting cab)    mid       23000"
            "    400   2500  15850     6750   29.3        0"
            "  -", text)
        self.assertIn(
            "taxi_driver (renting cab)    senior    36000"
            "   1050   2500  20400    14550   40.4        0"
            "  -", text)

    def test_renting_bridge_line_sweeps_tiers(self):
        import subprocess
        out = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools",
                                          "economy_sim.py")],
            capture_output=True, cwd=ROOT)
        self.assertEqual(out.returncode, 0)
        text = out.stdout.decode()
        # The printed line's dip is the cross-tier minimum
        # (0 at every tier), not the entry row's alone:
        # 5,000 + 0 = 5,000 OK.
        line = next(ln for ln in text.splitlines()
                    if "renting cab" in ln and "start" in ln)
        self.assertIn("5000 + dip       0 =    5000  OK", line)
        self.assertIn("(worst renting tier)", line)
        self.assertIn("BRIDGE FAIL rows: []", text)

    def test_shibnagar_renting_rows_match_district1(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "taxi_driver")
        cab = prices["taxi_fares"]["cab_rental_ncr_per_day"]
        rents, _stock = econ.load_shibnagar_rents(prices)
        override = rents[econ.SHIBNAGAR_RENT_TIER["taxi_driver"]]
        # The taxi rent tier is unchanged in Shibnagar, so
        # every renting row is identical on the variant's own
        # rents — verified, not assumed.
        for tier, net in (("entry", 1300), ("mid", 6750),
                          ("senior", 14550)):
            d1 = econ.simulate(prices, w, tier,
                               extra_daily_cost=cab,
                               label_suffix=" (renting cab)")
            sh = econ.simulate(prices, w, tier,
                               extra_daily_cost=cab,
                               label_suffix=" (renting cab)",
                               rent_override=override)
            self.assertEqual((sh["net"], sh["min_balance"],
                              sh["end_balance"]), (net, 0, net),
                             tier)
            self.assertEqual(sh["net"], d1["net"], tier)
            self.assertEqual(sh["min_balance"],
                             d1["min_balance"], tier)
        import subprocess
        sh_out = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools",
                                          "economy_sim.py"),
             "--shibnagar"],
            capture_output=True, cwd=ROOT)
        self.assertEqual(sh_out.returncode, 0)
        text = sh_out.stdout.decode()
        # Each renting base-table line appears twice — once
        # in the District 1 table, once in the variant table.
        for row in ("taxi_driver (renting cab)    entry"
                    "     14000      0   2500  12700     1300",
                    "taxi_driver (renting cab)    mid"
                    "       23000    400   2500  15850     6750",
                    "taxi_driver (renting cab)    senior"
                    "    36000   1050   2500  20400    14550"):
            self.assertEqual(text.count(row), 2, row)
        variant = text.split(
            "shibnagar first-month bridge check")[1]
        line = next(ln for ln in variant.splitlines()
                    if "renting cab" in ln and "start" in ln)
        self.assertIn("5000 + dip       0 =    5000  OK", line)
        self.assertIn("(worst renting tier)", line)
        self.assertIn("shibnagar BRIDGE FAIL rows: []", text)


class TestRentingRowsInSurgeSection(unittest.TestCase):
    def test_renting_surge_rows_at_all_tiers_are_measured(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        w = next(w for w in prices["wages_monthly"]
                 if w["profession_id"] == "taxi_driver")
        cab = prices["taxi_fares"]["cab_rental_ncr_per_day"]
        # The rental stays the flat 5,200 unsurged, so the
        # renting rows rise by exactly the owning driver's
        # surge deltas (+455 / +691 / +1,080) — measured in
        # V7 §16 prose, now printed rows.
        expected = (("entry", 14000, 14700, 1300, 1755, 455),
                    ("mid", 23000, 24150, 6750, 7441, 691),
                    ("senior", 36000, 37800, 14550, 15630, 1080))
        for tier, flat_gross, surged_gross, flat_net, surged_net, delta in expected:
            flat = econ.simulate(
                prices, w, tier, extra_daily_cost=cab,
                label_suffix=" (renting cab)")
            surged = econ.simulate(
                prices, w, tier, extra_daily_cost=cab,
                label_suffix=" (renting cab)",
                taxi_rain_days=econ
                .TAXI_WEATHER_MEASURED_RAIN_DAYS,
                taxi_storm_days=econ
                .TAXI_WEATHER_MEASURED_STORM_DAYS)
            self.assertEqual(
                (flat["gross"], surged["gross"], flat["net"],
                 surged["net"], surged["net"] - flat["net"]),
                (flat_gross, surged_gross, flat_net, surged_net,
                 delta), tier)
            self.assertEqual(surged["extra"], 5200, tier)
            self.assertEqual(surged["end_balance"],
                             surged["net"], tier)
            self.assertEqual(
                (flat["min_balance"], surged["min_balance"]),
                (0, 0), tier)
            owning_flat = econ.simulate(prices, w, tier)
            owning_surged = econ.simulate(
                prices, w, tier,
                taxi_rain_days=econ
                .TAXI_WEATHER_MEASURED_RAIN_DAYS,
                taxi_storm_days=econ
                .TAXI_WEATHER_MEASURED_STORM_DAYS)
            self.assertEqual(
                owning_surged["net"] - owning_flat["net"],
                delta, tier)
            self.assertEqual(
                owning_surged["net"] - surged["net"], 5200, tier)

    def test_surge_table_prints_all_three_renting_rows(self):
        import subprocess
        out = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools",
                                          "economy_sim.py")],
            capture_output=True, cwd=ROOT)
        self.assertEqual(out.returncode, 0)
        text = out.stdout.decode()
        section = text.split(
            "taxi weather-surge month (Unit KC")[1].split(
            "taxi-driver second earner")[0]
        # The owning rows are unchanged; the renting rows now
        # print at every tier, in the same columns.
        self.assertIn(
            "taxi_driver                  entry        14000"
            "   14700     6500       6955      +455", section)
        self.assertIn(
            "taxi_driver (renting cab)    entry        14000"
            "   14700     1300       1755      +455", section)
        self.assertIn(
            "taxi_driver (renting cab)    mid          23000"
            "   24150     6750       7441      +691", section)
        self.assertIn(
            "taxi_driver (renting cab)    senior       36000"
            "   37800    14550      15630     +1080", section)
        self.assertEqual(section.count("(renting cab)"), 3)

    def test_second_earner_surge_table_has_five_pairings(self):
        import subprocess
        out = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools",
                                          "economy_sim.py")],
            capture_output=True, cwd=ROOT)
        self.assertEqual(out.returncode, 0)
        text = out.stdout.decode()
        section = text.split(
            "taxi-driver second earner weather-surge month")[1]
        # Queue 45 Unit MN wires the fifth pairing in — the
        # senior owning second earner (measured by ML, wired
        # by MM in the IC section). The four-pairings test is
        # superseded by this one; the renting senior-tier
        # second earner stays allowed but unprinted — Queue
        # 46 Unit MO measures it on the surge pattern and
        # decides it stays unprinted (V7 §35).
        self.assertIn("taxi-driver (entry, owning)", section)
        self.assertIn("taxi-driver (mid, owning)", section)
        self.assertIn("taxi-driver (mid, renting)", section)
        self.assertIn("taxi-driver (entry, renting)", section)
        self.assertIn("taxi-driver (senior, owning)", section)
        self.assertNotIn("senior, renting", section)

    def test_second_earner_surge_table_prints_entry_renting_rows(
            self):
        import subprocess
        out = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools",
                                          "economy_sim.py")],
            capture_output=True, cwd=ROOT)
        self.assertEqual(out.returncode, 0)
        text = out.stdout.decode()
        section = text.split(
            "taxi-driver second earner weather-surge month")[1]
        # The IB dips shrink by the entry taxi surge but close
        # none: -193 -> -163, -288 -> -258, -419 -> -389; the
        # nets rise +455 at every tier.
        self.assertIn(
            "taxi-driver (entry, renting) entry         -193"
            "         -163     5500       5955", section)
        self.assertIn(
            "taxi-driver (entry, renting) mid           -288"
            "         -258     8744       9199", section)
        self.assertIn(
            "taxi-driver (entry, renting) senior        -419"
            "         -389    12201      12656", section)
        self.assertEqual(
            section.count("taxi-driver (entry, renting)"), 3)

    def test_second_earner_surge_table_prints_senior_owning_rows(
            self):
        import subprocess
        out = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools",
                                          "economy_sim.py")],
            capture_output=True, cwd=ROOT)
        self.assertEqual(out.returncode, 0)
        text = out.stdout.decode()
        section = text.split(
            "taxi-driver second earner weather-surge month")[1]
        # Queue 45 Unit MN: the senior owning pairing dips 0
        # flat and surged at every tier; the nets rise +1,080
        # at every tier — exactly the senior taxi surge.
        self.assertIn(
            "taxi-driver (senior, owning) entry            0"
            "            0    23950      25030", section)
        self.assertIn(
            "taxi-driver (senior, owning) mid              0"
            "            0    27194      28274", section)
        self.assertIn(
            "taxi-driver (senior, owning) senior           0"
            "            0    30651      31731", section)
        self.assertEqual(
            section.count("taxi-driver (senior, owning)"), 3)


class TestShibnagarSurgeTable(unittest.TestCase):
    """Queue 35 Unit MD — the KC surge section in the
    --shibnagar variant's own table (MC wired the fourth
    pairing into the District 1 table; the section itself was
    still District 1 only in the printed run)."""
    def test_surged_rows_are_identical_on_shibnagar_rents(
            self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        rents, _stock = econ.load_shibnagar_rents(prices)
        # Shibnagar's tier-1 rent is the prices.json tier-1
        # rent (2,500) — asserted by load_shibnagar_rents,
        # not assumed — and the surge rows rent at tier 1
        # (the taxi driver and the construction worker both),
        # so the figures must be identical by construction.
        tier1 = next(r["rent_ncr"]
                     for r in prices["rent_monthly_by_tier"]
                     if r["tier"] == 1)
        self.assertEqual(rents[1], tier1)
        self.assertEqual(
            rents[econ.SHIBNAGAR_RENT_TIER["taxi_driver"]],
            tier1)
        self.assertEqual(
            rents[econ.SHIBNAGAR_RENT_TIER["construction_worker"]],
            tier1)
        bands = {w["profession_id"]: w
                 for w in prices["wages_monthly"]}
        cab = prices["taxi_fares"]["cab_rental_ncr_per_day"]
        weather = dict(
            taxi_rain_days=econ.TAXI_WEATHER_MEASURED_RAIN_DAYS,
            taxi_storm_days=econ
            .TAXI_WEATHER_MEASURED_STORM_DAYS)
        checked = 0
        # Single-earner rows: owning and renting at every
        # tier, flat and surged.
        shib_taxi = rents[econ.SHIBNAGAR_RENT_TIER["taxi_driver"]]
        for kw in ({}, {"extra_daily_cost": cab,
                        "label_suffix": " (renting cab)"}):
            for tier in ("entry", "mid", "senior"):
                for skw in ({}, weather):
                    d1 = econ.simulate(prices, bands["taxi_driver"],
                                       tier, **kw, **skw)
                    sh = econ.simulate(prices, bands["taxi_driver"],
                                       tier, rent_override=shib_taxi,
                                       **kw, **skw)
                    self.assertEqual(sh["min_balance"],
                                     d1["min_balance"], tier)
                    self.assertEqual(sh["net"], d1["net"], tier)
                    self.assertEqual(sh["end_balance"],
                                     d1["end_balance"], tier)
                    checked += 1
        # Second-earner rows: all five pairings × three tiers
        # × four storm positions, flat and surged.
        shib_cw = rents[econ.SHIBNAGAR_RENT_TIER[
            "construction_worker"]]
        w = bands["construction_worker"]
        pairings = (
            {"second_earner": "taxi_driver"},
            {"second_earner": "taxi_driver",
             "second_earner_tier": "mid"},
            {"second_earner": "taxi_driver",
             "second_earner_tier": "mid",
             "second_earner_renting_cab": True},
            {"second_earner": "taxi_driver",
             "second_earner_renting_cab": True},
            # Queue 45 Unit MN: the senior owning pairing.
            {"second_earner": "taxi_driver",
             "second_earner_tier": "senior"},
        )
        positions = (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                     econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS)
        for kw in pairings:
            for tier in ("entry", "mid", "senior"):
                for pos in positions:
                    for skw in ({}, weather):
                        d1 = econ.simulate(prices, w, tier,
                                           storm_days=pos,
                                           **kw, **skw)
                        sh = econ.simulate(prices, w, tier,
                                           storm_days=pos,
                                           rent_override=shib_cw,
                                           **kw, **skw)
                        self.assertEqual(sh["min_balance"],
                                         d1["min_balance"],
                                         f"{kw}/{tier}/{pos}")
                        self.assertEqual(sh["net"], d1["net"],
                                         f"{kw}/{tier}/{pos}")
                        self.assertEqual(sh["end_balance"],
                                         d1["end_balance"],
                                         f"{kw}/{tier}/{pos}")
                        checked += 1
        # 12 single-earner + 120 second-earner rows.
        self.assertEqual(checked, 132)

    def test_shibnagar_variant_prints_own_surge_table(self):
        import subprocess
        out = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools",
                                          "economy_sim.py"),
             "--shibnagar"],
            capture_output=True, cwd=ROOT)
        self.assertEqual(out.returncode, 0)
        text = out.stdout.decode()
        # The variant's own table, computed on Shibnagar's
        # rents — headed Unit MD, not a reprint of the D1
        # section (which the run still prints first).
        self.assertIn("shibnagar taxi weather-surge month "
                      "(Unit MD", text)
        self.assertIn("shibnagar taxi-driver second earner "
                      "weather-surge month (Unit MD", text)
        section = text.split(
            "shibnagar taxi weather-surge month")[1].split(
            "district 1 vs shibnagar")[0]
        for row in (
                "taxi_driver                  entry        14000"
                "   14700     6500       6955      +455",
                "taxi_driver                  mid          23000"
                "   24150    11950      12641      +691",
                "taxi_driver                  senior       36000"
                "   37800    19750      20830     +1080",
                "taxi_driver (renting cab)    entry        14000"
                "   14700     1300       1755      +455",
                "taxi_driver (renting cab)    mid          23000"
                "   24150     6750       7441      +691",
                "taxi_driver (renting cab)    senior       36000"
                "   37800    14550      15630     +1080"):
            self.assertIn(row, section)
        self.assertEqual(section.count("(renting cab)"), 3)
        for row in (
                "taxi-driver (entry, owning)  senior         -72"
                "          -42    17401      17856",
                "taxi-driver (mid, owning)    senior           0"
                "            0    22851      23542",
                "taxi-driver (mid, renting)   senior         -56"
                "           -9    17651      18342",
                "taxi-driver (entry, renting) senior        -419"
                "         -389    12201      12656",
                # Queue 45 Unit MN: the senior owning rows.
                "taxi-driver (senior, owning) entry            0"
                "            0    23950      25030",
                "taxi-driver (senior, owning) mid              0"
                "            0    27194      28274",
                "taxi-driver (senior, owning) senior           0"
                "            0    30651      31731"):
            self.assertIn(row, section)
        for pairing in ("taxi-driver (entry, owning)",
                        "taxi-driver (mid, owning)",
                        "taxi-driver (mid, renting)",
                        "taxi-driver (entry, renting)",
                        "taxi-driver (senior, owning)"):
            self.assertIn(pairing, section)
        self.assertNotIn("senior, renting", section)
        self.assertIn("shibnagar BRIDGE FAIL rows: []", text)

    def test_shibnagar_surge_table_matches_district1(self):
        import subprocess
        d1 = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools",
                                          "economy_sim.py")],
            capture_output=True, cwd=ROOT)
        sh = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools",
                                          "economy_sim.py"),
             "--shibnagar"],
            capture_output=True, cwd=ROOT)
        self.assertEqual(d1.returncode, 0)
        self.assertEqual(sh.returncode, 0)
        d1_text, sh_text = d1.stdout.decode(), sh.stdout.decode()
        # The data rows of the two tables, line for line —
        # the headers differ (Unit KC vs Unit MD) but every
        # printed figure is the same.
        d1_rows = [ln for ln in d1_text.split(
            "taxi weather-surge month (Unit KC")[1].splitlines()
            if (ln.startswith("taxi_driver")
                or ln.startswith("taxi-driver"))
            and "weather-surge month" not in ln]
        sh_rows = [ln for ln in sh_text.split(
            "shibnagar taxi weather-surge month")[1].split(
            "district 1 vs shibnagar")[0].splitlines()
            if (ln.startswith("taxi_driver")
                or ln.startswith("taxi-driver"))
            and "weather-surge month" not in ln]
        self.assertEqual(len(d1_rows), 21)
        self.assertEqual(sh_rows, d1_rows)


class TestSeniorRentingSecondEarnerDecision(unittest.TestCase):
    """Queue 36 Unit ME — the renting senior-tier taxi
    second earner stays allowed but unmeasured (MD follow-up):
    simulate() computes the combination (the senior wage and
    the flat rental are both sourced), but the default run
    prints no row for it and neither bridge check wires a
    line for it. (Update, Queue 44 Unit MM — the ME decision
    was re-opened: the measured household HAS appeared (ML:
    ml-seed-1 HH000030 and ml-seed-3 HH000042, both pairings
    reproduced by MM's re-runs), so the owning senior row is
    now wired and ME's dangling argument FALLS — a renting
    row beside it would no longer dangle. The decision
    stands on the re-measured no-finding reason alone: the
    dip is 0 at every tier and storm position, the net is
    exactly 5,200 below the owning senior driver, and the
    bridge line would be the trivial 10,000 + 0 = 10,000 —
    the same line the owning senior row just wired — so the
    row adds nothing new. Full detail: V7 report §33.)"""
    def test_senior_renting_second_earner_is_allowed(self):
        from tools import economy_sim as econ
        prices = econ.load("prices.json")
        bands = {w["profession_id"]: w
                 for w in prices["wages_monthly"]}
        w = bands["construction_worker"]
        rental = (prices["taxi_fares"]["cab_rental_ncr_per_day"]
                  * econ.WORK_DAYS)
        self.assertEqual(rental, 5200)
        positions = (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                     econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS)
        for tier in ("entry", "mid", "senior"):
            for pos in positions:
                kw = dict(second_earner="taxi_driver",
                          second_earner_tier="senior",
                          second_earner_renting_cab=True)
                r = econ.simulate(prices, w, tier,
                                  storm_days=pos, **kw)
                own = econ.simulate(
                    prices, w, tier, storm_days=pos,
                    second_earner="taxi_driver",
                    second_earner_tier="senior")
                # The combination computes (allowed, not
                # refused); the rental is the same flat
                # 5,200 at every tier and position, so the
                # net is exactly 5,200 below the owning
                # senior driver — the rental rule, not a
                # measured household figure — and the
                # trajectory ends exactly at net.
                self.assertEqual(r["net"], own["net"] - 5200)
                self.assertEqual(r["end_balance"], r["net"])
                # The senior pay covers the cost-only days
                # at every tier, so the pairing dips nowhere
                # — the row would add no finding, which is
                # part of why ME leaves it unprinted.
                self.assertEqual(r["min_balance"], 0)

    def test_senior_renting_second_earner_is_not_printed(self):
        import subprocess
        d1 = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools",
                                          "economy_sim.py")],
            capture_output=True, cwd=ROOT)
        sh = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools",
                                          "economy_sim.py"),
             "--shibnagar"],
            capture_output=True, cwd=ROOT)
        self.assertEqual(d1.returncode, 0)
        self.assertEqual(sh.returncode, 0)
        for text in (d1.stdout.decode(), sh.stdout.decode()):
            # The surge table keeps its five pairings and
            # neither bridge check wires a senior renting
            # line; the renting mid-tier line (Unit KA) is
            # the only renting second-earner line in either
            # check. Queue 46 Unit MO: measured on the surge
            # pattern beside the printed senior owning row —
            # the surge adds no finding, so it stays
            # unprinted (V7 §35).
            self.assertNotIn("senior, renting", text)
            self.assertNotIn("taxi-driver (senior, renting)",
                             text)
            self.assertIn("taxi-driver (mid, renting)", text)
            self.assertIn(
                "construction_worker + taxi-driver"
                " (mid, renting)", text)
        section = d1.stdout.decode().split(
            "taxi-driver second earner weather-surge month")[1]
        for pairing in ("taxi-driver (entry, owning)",
                        "taxi-driver (mid, owning)",
                        "taxi-driver (mid, renting)",
                        "taxi-driver (entry, renting)",
                        # Queue 45 Unit MN: the senior owning
                        # pairing is printed now.
                        "taxi-driver (senior, owning)"):
            self.assertIn(pairing, section)


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
