"""Session 03 Unit 07 — Public Infrastructure Engine."""
import os
import tempfile
import unittest

from tools.sim import cities as cities_mod
from tools.sim import infrastructure as infrastructure_mod
from tools.sim import needs as needs_mod
from tools.sim.engine import Simulation
from tools.sim.tests.common import data, make_store, rng


def _tmp_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


class TestInfrastructure(unittest.TestCase):
    def test_setup_rows_for_all_zones_and_networks(self):
        store = make_store()
        cities_mod.setup_cities(store, data(), rng())
        self.assertEqual(store.row("SELECT COUNT(*) AS n FROM"
                                   " infrastructure_state")["n"],
                         16 * 8)
        store.close()

    def test_loads_computed_from_population(self):
        path = _tmp_path()
        sim = Simulation(path, seed="infra-test")
        sim.generate_population(100)
        infrastructure_mod.weekly_update(sim.store, sim.data, 480)
        row = sim.store.row("SELECT * FROM infrastructure_state"
                            " WHERE zone_id = 'd1_oldtown' AND"
                            " network = 'water'")
        self.assertGreater(row["demand_units"], 0)
        self.assertIn(row["status"], ("ok", "strained", "overloaded"))
        empty = sim.store.row("SELECT * FROM infrastructure_state"
                              " WHERE zone_id = 'c2_market' AND"
                              " network = 'water'")
        self.assertEqual(empty["demand_units"], 0)  # no residents yet
        sim.close()
        os.remove(path)

    def test_overload_is_felt_by_residents(self):
        path = _tmp_path()
        sim = Simulation(path, seed="infra-test")
        sim.generate_population(100)
        store = sim.store
        # Crush midtown's water capacity: the network must report
        # overload, and the monthly effect must land on residents.
        store.execute("UPDATE infrastructure_state SET capacity_units"
                      " = 1 WHERE zone_id = 'd1_midtown' AND network"
                      " = 'water'")
        infrastructure_mod.weekly_update(store, sim.data, 480)
        row = store.row("SELECT status FROM infrastructure_state"
                        " WHERE zone_id = 'd1_midtown' AND network"
                        " = 'water'")
        self.assertEqual(row["status"], "overloaded")
        resident = infrastructure_mod.zone_residents(
            store, "d1_midtown")[0]["character_id"]
        before = needs_mod.get_needs(store, resident)["healthcare"]
        overloaded = infrastructure_mod.monthly_effects(
            store, sim.data, 1440)
        self.assertIn("water", overloaded["d1_midtown"])
        after = needs_mod.get_needs(store, resident)["healthcare"]
        self.assertLess(after, before)
        self.assertLessEqual(infrastructure_mod.headroom(
            store, "rupsha_city"), 1.0)
        sim.close()
        os.remove(path)


if __name__ == "__main__":
    unittest.main()
