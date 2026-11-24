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
# v7 + Queue 28 baseline (Unit KA, 2026-11-24): the
# renting-cab second earner at another tier (KA).
# See docs/ECONOMY-SIM-REPORT-V7.md §14.
# Previous baseline (v7 + Queue 27, Unit JA):
# b70b18972aeb5c3b2d0273b986060058. Previous baseline (v7 +
# Queue 26, Unit IC):
# d198a2fe0970e11aaa105bcc4bfb19f9. Previous baseline (v7 +
# Queue 26, Unit IB):
# 27464ea221694880a4369f805d8cd455. Previous baseline (v7 +
# Queue 26, Unit IA):
# 45a45edc63cee4b142891da938ef79bd. Previous baseline (v7 +
# Queue 25, Unit HD):
# 5431558ffa3d023c436366c26535f932. Previous baseline (v7 +
# Queue 25, Unit HA):
# ede430d0bf391fac3f8599334f55b77b. Previous baseline (v7 +
# Queue 24, Units GD–GE):
# d699ae7d37fe8ca077f873ba238dd86b. Previous baseline (v7, pinned
# 2026-11-24 through Queue 23):
# e598e416c07b21bacee9fe98fdb27244. Previous baseline (v6, pinned
# 2026-11-24 through Queue 22): 9ac10779c231b7aa6120a6ff457982de.
# v5 baseline: 318c6114c143a81a579e70b39ccca8f8. v2 baseline (pinned
# 2026-11-21 through v3): 16740182867525bd659735deeb05150a.
ECONOMY_SIM_BASELINE_MD5 = "5f50931cbaad263812473ce1c7830e59"


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
