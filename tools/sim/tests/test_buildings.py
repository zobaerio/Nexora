"""Session 03 Unit 05 — Building Generation & State Engine."""
import unittest

from tools.sim import buildings as buildings_mod
from tools.sim import cities as cities_mod
from tools.sim.tests.common import data, make_store, rng


class TestBuildings(unittest.TestCase):
    def setUp(self):
        self.store = make_store()
        self.d = data()
        cities_mod.setup_cities(self.store, self.d, rng())

    def tearDown(self):
        self.store.close()

    def test_state_for_every_building(self):
        n = self.store.row("SELECT COUNT(*) AS n FROM"
                           " building_state")["n"]
        self.assertEqual(n, 60)  # 42 authored + 18 generated
        ids = {r["building_id"] for r in self.store.rows(
            "SELECT building_id FROM building_state")}
        self.assertTrue(ids <= set(self.d.all_buildings()))

    def test_floors_from_design(self):
        state = {r["building_id"]: r for r in self.store.rows(
            "SELECT * FROM building_state")}
        # GDD-02: midtown blocks are 6-storey; the rooftop tower
        # is the district's only high-rise.
        self.assertEqual(state["b_d1_midtown_starter_block"]
                         ["floors"], 6)
        self.assertEqual(state["b_d1_uptown_rooftop_restaurant"]
                         ["floors"], 12)
        self.assertEqual(state["b_d1_park_land"]["floors"], 0)
        self.assertIsNone(state["b_d1_park_land"]
                          ["construction_year"])

    def test_value_from_data_prices(self):
        state = self.store.row("SELECT * FROM building_state WHERE"
                               " building_id ="
                               " 'b_d1_midtown_starter_block'")
        self.assertEqual(state["economic_value"], 750000 * 24)

    def test_occupancy_bases(self):
        # With no population yet, occupancy falls back to the data
        # file's own unit status.
        occ = buildings_mod.occupancy(self.store, self.d,
                                      "b_d1_market_hall_units")
        self.assertEqual(occ["basis"], "data_status")
        occ = buildings_mod.occupancy(self.store, self.d,
                                      "b_d1_midtown_starter_block")
        self.assertEqual(occ["basis"], "data_status")
        self.assertEqual(occ["total_units"], 24)

    def test_occupancy_from_tenancies_in_a_populated_world(self):
        import os
        import tempfile
        from tools.sim.engine import Simulation
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(path)
        sim = Simulation(path, seed="occ-test")
        sim.generate_population(120)
        occ = buildings_mod.occupancy(sim.store, sim.data,
                                      "b_d1_midtown_starter_block")
        self.assertEqual(occ["basis"], "tenancies")
        self.assertEqual(occ["total_units"], 24)
        rented = sim.store.row(
            "SELECT COUNT(*) AS n FROM properties WHERE"
            " building_ref = 'b_d1_midtown_starter_block' AND"
            " status = 'rented'")["n"]
        self.assertEqual(occ["occupied_units"], rented)
        self.assertAlmostEqual(occ["rate"], rented / 24, places=2)
        sim.close()
        os.remove(path)

    def test_upkeep_decays_and_maintenance_restores(self):
        before = self.store.row("SELECT condition FROM building_state"
                                " WHERE building_id ="
                                " 'b_d1_oldtown_walkups'")["condition"]
        buildings_mod.monthly_upkeep(self.store, self.d, 1440)
        after = self.store.row("SELECT condition FROM building_state"
                               " WHERE building_id ="
                               " 'b_d1_oldtown_walkups'")["condition"]
        self.assertLess(after, before)
        restored = buildings_mod.apply_maintenance(
            self.store, "b_d1_oldtown_walkups", 10, 2880)
        self.assertAlmostEqual(restored, min(100.0, after + 10))
        capped = buildings_mod.apply_maintenance(
            self.store, "b_d1_oldtown_walkups", 500, 2880)
        self.assertEqual(capped, 100.0)

    def test_condition_bands(self):
        self.assertEqual(buildings_mod.condition_band(90), "good")
        self.assertEqual(buildings_mod.condition_band(60), "fair")
        self.assertEqual(buildings_mod.condition_band(40), "poor")
        self.assertEqual(buildings_mod.condition_band(20), "critical")


if __name__ == "__main__":
    unittest.main()
