"""Session 08 — configured disaster scenarios, response with
actual resources, recovery, and environmental governance."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))

from tools.sim import environment as env_mod  # noqa: E402
from tools.sim import justice as justice_mod  # noqa: E402
from tools.sim.tests.common import rng  # noqa: E402
from tools.sim.tests.envcommon import env_world, seed_weather  # noqa: E402
from tools.sim.tests.transportcommon import citizen  # noqa: E402

RUP = "rupsha_city"


def _funded_world():
    store, d = env_world()
    citizen(store, zone="d1_riverfront", first="River")
    store.transfer("SYS-MARKET", "SYS-CITY", 1000000, "seed_grant",
                   480, transfer_key="seed:disaster-treasury")
    store.commit()
    return store, d


def _run_days(store, d, r, first, last):
    for day in range(first, last + 1):
        env_mod.daily_pass(store, d, r, day, (day + 1) * 1440)


class TestScenarioDoor(unittest.TestCase):
    def test_unknown_scenario_raises(self):
        store, d = env_world()
        with self.assertRaises(ValueError):
            env_mod.trigger_scenario(store, d, "meteor_shower", 0, 480)

    def test_no_disasters_without_trigger(self):
        store, d = env_world()
        r = rng()
        _run_days(store, d, r, 0, 20)
        n = store.row("SELECT COUNT(*) AS n FROM disaster_events"
                      " WHERE scenario_id IS NOT NULL")["n"]
        self.assertEqual(n, 0)


class TestCycloneLifecycle(unittest.TestCase):
    def test_damage_response_recovery(self):
        store, d = _funded_world()
        r = rng()
        did = env_mod.trigger_scenario(store, d, "cyclone_rupsha",
                                       10, 11 * 1440)
        store.commit()
        _run_days(store, d, r, 10, 13)
        damage = store.row(
            "SELECT COUNT(*) AS n FROM disaster_impacts WHERE"
            " disaster_id = ? AND kind = 'building_damage'",
            (did,))["n"]
        self.assertGreater(damage, 0)
        displaced = store.row(
            "SELECT COUNT(*) AS n FROM disaster_impacts WHERE"
            " disaster_id = ? AND kind = 'household_displaced'",
            (did,))["n"]
        self.assertGreaterEqual(displaced, 1)
        # Run past the scenario's end: response + repairs.
        recovered = False
        for day in range(14, 200):
            env_mod.daily_pass(store, d, r, day, (day + 1) * 1440)
            row = store.row("SELECT status FROM disaster_events"
                            " WHERE disaster_id = ?", (did,))
            if row["status"] == "recovered":
                recovered = True
                break
        self.assertTrue(recovered)
        relief = store.row(
            "SELECT COALESCE(SUM(amount), 0) AS s FROM economy_ledger"
            " WHERE reason_code = 'disaster_relief' AND event_ref"
            " = ?", (did,))["s"]
        self.assertGreater(relief, 0)
        self.assertEqual(len(store.ledger_sum_check()), 0)
        trips = store.row(
            "SELECT COUNT(*) AS n FROM trips WHERE purpose ="
            " 'evacuation'")["n"]
        self.assertGreaterEqual(trips, 1)
        repairs = store.row(
            "SELECT COALESCE(SUM(amount), 0) AS s FROM economy_ledger"
            " WHERE reason_code = 'disaster_repair' AND event_ref"
            " = ?", (did,))["s"]
        self.assertGreater(repairs, 0)
        remaining = store.row(
            "SELECT COUNT(*) AS n FROM disaster_impacts WHERE"
            " disaster_id = ? AND kind = 'building_damage' AND"
            " repaired < damage", (did,))["n"]
        self.assertEqual(remaining, 0)


class TestHeatwaveAndDrought(unittest.TestCase):
    def test_heatwave_impacts_residents_and_recovers(self):
        store, d = _funded_world()
        r = rng()
        head = store.row("SELECT character_id FROM characters WHERE"
                         " is_system = 0 LIMIT 1")["character_id"]
        from tools.sim import needs as needs_mod
        before = needs_mod.get_needs(store, head)["healthcare"]
        did = env_mod.trigger_scenario(store, d, "heatwave_rupsha",
                                       5, 6 * 1440)
        store.commit()
        _run_days(store, d, r, 5, 30)
        after = needs_mod.get_needs(store, head)["healthcare"]
        self.assertLess(after, before)
        status = store.row("SELECT status FROM disaster_events"
                           " WHERE disaster_id = ?", (did,))["status"]
        self.assertEqual(status, "recovered")

    def test_drought_reduces_precipitation(self):
        results = {}
        for label, use_drought in (("plain", False), ("drought", True)):
            store, d = env_world()
            r = rng()
            if use_drought:
                env_mod.trigger_scenario(store, d, "drought_season",
                                         150, 151 * 1440)
                store.commit()
            total = 0.0
            for day in range(150, 180):
                w = env_mod.weather_for_region(store, d, r, RUP, day)
                total += w["precip_mm"]
            results[label] = total
        self.assertLess(results["drought"], results["plain"])


class TestGovernance(unittest.TestCase):
    def test_emission_law_kind_registered(self):
        self.assertIn("emission_limit", justice_mod.LAW_KINDS)

    def test_enacted_law_changes_pollution_and_vegetation(self):
        outcomes = {}
        for label, with_law in (("plain", False), ("law", True)):
            store, d = env_world()
            r = rng()
            if with_law:
                lid = store.next_id("LW", "laws", "law_id")
                store.insert(
                    "laws", law_id=lid, title="Emission Limit Act",
                    kind="emission_limit",
                    effect=json.dumps({"reduction_percent": 50}),
                    proposed_by=None, status="enacted",
                    effective_month=0, created_at_game_minutes=480,
                    enacted_at_game_minutes=480)
                store.commit()
            self.assertEqual(
                env_mod.effective_emission_reduction(store),
                50.0 if with_law else 0.0)
            before = store.row(
                "SELECT AVG(cover_index) AS a FROM env_vegetation"
                )["a"]
            for day in range(0, 30):
                seed_weather(store, "rupsha_city", day, precip_mm=6.0)
                seed_weather(store, "shibnagar_town", day,
                             precip_mm=6.0)
            env_mod.monthly_pass(store, d, r, 1, 30 * 1440)
            after = store.row(
                "SELECT AVG(cover_index) AS a FROM env_vegetation")["a"]
            pol = store.row("SELECT sources FROM env_pollution WHERE"
                            " city_id = 'rupsha_city'")["sources"]
            outcomes[label] = (after - before,
                               json.loads(pol)[
                                   "emission_limit_reduction_percent"])
        self.assertGreater(outcomes["law"][0], outcomes["plain"][0])
        self.assertEqual(outcomes["law"][1], 50.0)
        self.assertEqual(outcomes["plain"][1], 0.0)


if __name__ == "__main__":
    unittest.main()
