"""Session 10 — one configured global scenario end-to-end and
the consolidated resource balance.

The scenario (international supply disruption) enters only
through the configured door, propagates through the Session 04
crisis surface (active_effects demand factor), measurably cuts
the scenario world's month-2 household consumption against its
same-seed twin, is indexed by the event registry, and resolves
after its configured duration. The resource report is computed
from existing records only; its shortage flags follow the
documented bases in data/integration-config.json."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))

from tools.sim import crises as crises_mod  # noqa: E402
from tools.sim import integration  # noqa: E402
from tools.sim.engine import Simulation  # noqa: E402
from tools.sim.tests.common import rng  # noqa: E402
from tools.sim.tests.envcommon import env_world  # noqa: E402


def _tmp_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


def _consumption(store, month_index):
    return store.row(
        "SELECT COALESCE(SUM(units), 0) AS q FROM"
        " household_consumption WHERE month_index = ?",
        (month_index,))["q"]


class TestGlobalScenario(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = []
        sims = {}
        for name in ("twin", "scenario"):
            path = _tmp_path()
            cls.paths.append(path)
            sim = Simulation(path, seed="s10-scenario")
            sim.generate_population(40)
            sim.run_days(35)
            sims[name] = sim
        cls.twin = sims["twin"]
        cls.scen = sims["scenario"]
        # The scenario opens at the end of month 1 in one world
        # only; both worlds then run month 2 identically.
        cls.crisis_id = integration.trigger_global_scenario(
            cls.scen.store, cls.scen.data, "supply_disruption", 1,
            cls.scen.store.world()["game_minutes"])
        cls.scen.store.commit()
        cls.factor_active = crises_mod.active_effects(
            cls.scen.store)["demand_factor"]
        for sim in sims.values():
            sim.run_days(30)

    @classmethod
    def tearDownClass(cls):
        for sim in (cls.twin, cls.scen):
            sim.close()
        for p in cls.paths:
            os.remove(p)

    def test_scenario_recorded_and_factor_applies(self):
        row = self.scen.store.row(
            "SELECT * FROM crisis_records WHERE crisis_id = ?",
            (self.crisis_id,))
        self.assertEqual(row["crisis_type"], "supply_disruption")
        self.assertEqual(row["scope"], "global")
        self.assertEqual(self.factor_active, 0.6)
        # The twin never saw the factor.
        self.assertEqual(crises_mod.active_effects(
            self.twin.store)["demand_factor"], 1.0)

    def test_consumption_measurably_reduced(self):
        twin_q = _consumption(self.twin.store, 2)
        scen_q = _consumption(self.scen.store, 2)
        self.assertGreater(twin_q, 0)
        self.assertLess(scen_q, twin_q)

    def test_registry_indexes_the_scenario(self):
        # The engine's daily pass writes the registry alongside:
        # the scenario's crisis record is indexed without any
        # manual sync.
        row = self.scen.store.row(
            "SELECT * FROM world_events WHERE source_table ="
            " 'crisis_records' AND source_id = ?",
            (self.crisis_id,))
        self.assertIsNotNone(row)
        self.assertEqual(row["event_type"], "economic_crisis")

    def test_dedupe_unknown_and_resolution(self):
        store, d = self.scen.store, self.scen.data
        again = integration.trigger_global_scenario(
            store, d, "supply_disruption", 2,
            store.world()["game_minutes"])
        self.assertEqual(again, self.crisis_id)
        with self.assertRaises(ValueError):
            integration.trigger_global_scenario(
                store, d, "alien_invasion", 2,
                store.world()["game_minutes"])
        # Opened month 1, duration 3: the month-4 integration
        # pass resolves it and the factor lifts.
        integration.monthly_pass(store, d, rng(), 4,
                                 store.world()["game_minutes"])
        row = store.row("SELECT status FROM crisis_records WHERE"
                        " crisis_id = ?", (self.crisis_id,))
        self.assertEqual(row["status"], "resolved")
        self.assertEqual(crises_mod.active_effects(
            store)["demand_factor"], 1.0)


class TestResourceReport(unittest.TestCase):
    def test_report_shape_and_water_stress_flag(self):
        store, d = env_world()
        integration.setup_integration(store, d)
        report = integration.resource_report(store, d)
        self.assertEqual(set(report["cities"]),
                         {"rupsha_city", "shibnagar_town"})
        rup = report["cities"]["rupsha_city"]
        for key in ("residents", "stored_goods",
                    "production_last_30d",
                    "consumption_latest_month", "food", "water",
                    "energy_fuel", "construction_materials",
                    "shortage_flags"):
            self.assertIn(key, rup)
        self.assertIsNotNone(rup["water"]["groundwater_index"])
        self.assertNotIn("water_stress", rup["shortage_flags"])
        store.execute("UPDATE env_water_state SET"
                      " groundwater_index = 0.1 WHERE city_id ="
                      " 'rupsha_city'")
        store.commit()
        report = integration.resource_report(store, d)
        self.assertIn("water_stress",
                      report["cities"]["rupsha_city"]["shortage_flags"])
        self.assertNotIn(
            "water_stress",
            report["cities"]["shibnagar_town"]["shortage_flags"])

    def test_food_cover_flag_from_real_balances(self):
        store, d = env_world()
        integration.setup_integration(store, d)
        # No residents and no stock: cover is undefined, and no
        # flag is invented for an empty balance.
        report = integration.resource_report(store, d)
        for city in report["cities"].values():
            self.assertIsNone(
                city["food"]["months_cover_per_resident"])
            self.assertNotIn("food_shortage_risk", city["shortage_flags"])


if __name__ == "__main__":
    unittest.main()
