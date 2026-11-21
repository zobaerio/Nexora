"""Session 03 Unit 02 — Geographical & Terrain Engine."""
import unittest

from tools.sim import cities as cities_mod
from tools.sim import terrain as terrain_mod
from tools.sim.tests.common import data, make_store, rng


class TestTerrain(unittest.TestCase):
    def setUp(self):
        self.d = data()
        self.regions = terrain_mod.regions_for_spec(
            self.d.city_spec("rupsha_city"))

    def test_terrain_classes_at_points(self):
        self.assertEqual(terrain_mod.terrain_at(
            self.regions, 0, 470)["terrain_class"], "river")
        self.assertEqual(terrain_mod.terrain_at(
            self.regions, 60, 255)["terrain_class"], "wetland")
        self.assertEqual(terrain_mod.terrain_at(
            self.regions, 0, 400)["terrain_class"], "floodplain")
        self.assertEqual(terrain_mod.terrain_at(
            self.regions, 400, 300)["terrain_class"], "hills")
        self.assertEqual(terrain_mod.terrain_at(
            self.regions, 0, 0)["terrain_class"], "plain")

    def test_building_in_river_rejected(self):
        ok, violations = terrain_mod.validate_build(
            self.regions, {"x": 0, "z": 460, "w": 30, "d": 30})
        self.assertFalse(ok)
        self.assertTrue(any("river" in v for v in violations))

    def test_all_structural_plots_pass(self):
        """Every District 1 plot carrying a structure stands on
        buildable terrain — the authored city respects its own
        geography."""
        spec = self.d.city_spec("rupsha_city")
        buildings = {b["id"]: b for b in spec["properties"]}
        for plot in spec["plots"]:
            b = buildings.get(plot["building_id"])
            if b is None or b["property_type"] == "plot":
                continue
            ok, violations = terrain_mod.validate_build(
                self.regions, plot["plot_rect_m"])
            self.assertTrue(ok, f"{b['id']}: {violations}")

    def test_flood_risk_restriction_recorded(self):
        spec = self.d.city_spec("rupsha_city")
        plot = next(p for p in spec["plots"]
                    if p["building_id"]
                    == "b_d1_riverfront_houses")
        restrictions = terrain_mod.restrictions_at(
            self.regions, plot["plot_rect_m"])
        self.assertIn("flood_risk", restrictions)

    def test_town_terrain_from_generated_file(self):
        spec = self.d.city_spec("shibnagar_town")
        regions = terrain_mod.regions_for_spec(spec)
        self.assertEqual(terrain_mod.terrain_at(
            regions, 280, -40)["terrain_class"], "river")
        self.assertEqual(terrain_mod.terrain_at(
            regions, 500, 440)["terrain_class"], "wetland")
        ok, _ = terrain_mod.validate_build(
            regions, {"x": 460, "z": 420, "w": 40, "d": 40})
        self.assertFalse(ok)  # in the beel

    def test_setup_persists_regions(self):
        store = make_store()
        cities_mod.setup_cities(store, self.d, rng())
        self.assertEqual(store.row("SELECT COUNT(*) AS n FROM"
                                   " terrain_regions")["n"], 10)
        store.close()


if __name__ == "__main__":
    unittest.main()
