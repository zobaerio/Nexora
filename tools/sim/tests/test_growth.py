"""Session 03 Unit 10 — City Growth Engine."""
import json
import os
import tempfile
import unittest

from tools.sim import growth as growth_mod
from tools.sim.engine import Simulation


def _tmp_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


def _force_crew(store):
    people = [r["character_id"] for r in store.rows(
        "SELECT character_id FROM characters WHERE is_system = 0"
        " AND died_at_game_minutes IS NULL ORDER BY character_id"
        " LIMIT 4")]
    for cid, prof in zip(people, ("civil_engineer",
                                  "construction_worker",
                                  "construction_worker",
                                  "construction_worker")):
        eid = store.next_id("EM", "employments", "employment_id")
        store.insert("employments", employment_id=eid,
                     character_id=cid, profession_id=prof, tier=1,
                     wage_per_month=30000, started_at_game_minutes=480)


class TestGrowth(unittest.TestCase):
    def test_metrics_are_derived_and_bounded(self):
        path = _tmp_path()
        sim = Simulation(path, seed="growth-test")
        sim.generate_population(80)
        m = growth_mod.city_metrics(sim.store, sim.data,
                                    "rupsha_city")
        from tools.sim import cities as cities_mod
        self.assertEqual(m["population"], cities_mod.city_population(
            sim.store, sim.data, "rupsha_city"))
        self.assertGreater(m["population"], 0)
        self.assertGreaterEqual(m["development_index"], 0)
        self.assertLessEqual(m["development_index"], 100)
        self.assertIn(m["development_level"],
                      ("emerging", "developing", "established",
                       "advanced"))
        self.assertIn(m["economic_class"],
                      ("affluent", "lower_income", "mixed_income"))
        self.assertEqual(m["housing"]["total_units"], 140)
        sim.close()
        os.remove(path)

    def test_growth_commissions_when_demand_meets_full_housing(self):
        path = _tmp_path()
        sim = Simulation(path, seed="growth-test")
        sim.generate_population(80)
        store = sim.store
        _force_crew(store)
        # Measured pressure: no vacant homes, a household in debt,
        # and a city treasury that can fund the build.
        store.execute("UPDATE properties SET status = 'rented'"
                      " WHERE district_id LIKE 'd1_%'")
        hid = store.row("SELECT household_id FROM households WHERE"
                        " district_id LIKE 'd1_%' LIMIT 1")
        store.execute("INSERT OR IGNORE INTO household_state"
                      " (household_id) VALUES (?)",
                      (hid["household_id"],))
        store.execute("UPDATE household_state SET debt_ncr = 5000"
                      " WHERE household_id = ?",
                      (hid["household_id"],))
        store.transfer("SYS-EMPLOYERS", "SYS-CITY", 3000000, "seed",
                       480)
        out = growth_mod.monthly_growth(store, sim.data, 1, 480)
        self.assertTrue(any(a.startswith("commissioned:")
                            for a in out["rupsha_city"]["actions"]))
        proj = store.row("SELECT * FROM construction_projects WHERE"
                         " city_id = 'rupsha_city'")
        self.assertIsNotNone(proj)
        # District 1 has no vacant residential parcel: the honest
        # growth move is densification of an existing block.
        self.assertEqual(proj["kind"], "extension")
        event = store.row("SELECT * FROM city_events WHERE"
                          " event_type = 'growth_commissioned'")
        self.assertIsNotNone(event)
        sim.close()
        os.remove(path)

    def test_decline_pressure_from_measured_loss(self):
        path = _tmp_path()
        sim = Simulation(path, seed="growth-test")
        sim.generate_population(40)
        store = sim.store
        # Last month's snapshot says the city was bigger; housing
        # is mostly empty (40 people in 140 units).
        store.execute(
            "INSERT INTO city_statistics (city_id, month_index,"
            " metrics, game_minutes) VALUES ('rupsha_city', 0, ?,"
            " 480)", (json.dumps({"population": 400}),))
        growth_mod.monthly_growth(store, sim.data, 1, 480)
        event = store.row("SELECT * FROM city_events WHERE"
                          " event_type = 'decline_pressure' AND"
                          " city_id = 'rupsha_city'")
        self.assertIsNotNone(event)
        sim.close()
        os.remove(path)


if __name__ == "__main__":
    unittest.main()
