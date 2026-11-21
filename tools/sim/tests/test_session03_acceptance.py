"""Session 03 acceptance — the owner's 14 criteria, at engine
level. Criterion 13 (3D rendering performance) belongs to the
Unreal build on the owner's PC and is DEFERRED: it is not
asserted here, and nothing in this suite claims it passed.
What criterion 12/13's data layer owes — a complete city-state
export — is asserted under criteria 12.
"""
import os
import tempfile
import unittest

from tools.sim import cities as cities_mod
from tools.sim import cityview as cityview_mod
from tools.sim import regional as regional_mod
from tools.sim import roads as roads_mod
from tools.sim import terrain as terrain_mod
from tools.sim import zoning as zoning_mod
from tools.sim.engine import Simulation


def _tmp_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


class TestSession03Acceptance(unittest.TestCase):
    def setUp(self):
        self.path = _tmp_path()
        self.sim = Simulation(self.path, seed="s03-acceptance")
        self.sim.generate_population(120)
        self.store = self.sim.store
        self.data = self.sim.data

    def tearDown(self):
        self.sim.close()
        os.remove(self.path)

    def test_01_two_cities_registered_with_derived_identity(self):
        rows = {r["city_id"]: r for r in self.store.rows(
            "SELECT * FROM cities")}
        self.assertEqual(set(rows), {"rupsha_city",
                                     "shibnagar_town"})
        for r in rows.values():
            self.assertEqual(r["climate"], "tropical_monsoon")
            self.assertIn(r["development_level"],
                          ("emerging", "developing", "established",
                           "advanced"))
        self.assertEqual(rows["rupsha_city"]["kind"], "seeded")
        self.assertEqual(rows["shibnagar_town"]["kind"],
                         "generated_town")

    def test_02_terrain_rejects_building_on_water(self):
        spec = self.data.city_spec("rupsha_city")
        ok, violations = terrain_mod.validate_build(
            terrain_mod.regions_for_spec(spec),
            {"x": 0, "z": 460, "w": 30, "d": 30})
        self.assertFalse(ok)
        self.assertTrue(violations)

    def test_03_parcels_cover_every_plot_with_history(self):
        self.assertEqual(self.store.row(
            "SELECT COUNT(*) AS n FROM land_parcels")["n"], 64)
        self.assertEqual(self.store.row(
            "SELECT COUNT(*) AS n FROM parcel_history WHERE event"
            " = 'genesis'")["n"], 64)

    def test_04_zoning_rules_enforced(self):
        self.assertTrue(zoning_mod.validate_placement(
            "educational", "d1_industry"))
        self.assertEqual(zoning_mod.validate_placement(
            "educational", "d1_civic"), [])

    def test_05_building_state_extends_real_buildings(self):
        self.assertEqual(self.store.row(
            "SELECT COUNT(*) AS n FROM building_state")["n"], 60)

    def test_06_road_graph_connected_with_valid_routes(self):
        spec = self.data.city_spec("rupsha_city")
        graph = roads_mod.build_graph(spec)
        self.assertEqual(len(roads_mod.components(graph, "walk")),
                         1)
        route = roads_mod.pathfind(
            graph, roads_mod.zone_anchor(spec, "d1_market"),
            roads_mod.zone_anchor(spec, "d1_transport"), "motor")
        self.assertIsNotNone(route)
        self.assertGreater(route["distance_m"], 0)

    def test_07_infrastructure_covers_every_zone(self):
        self.assertEqual(self.store.row(
            "SELECT COUNT(*) AS n FROM infrastructure_state")["n"],
            16 * 8)

    def test_08_housing_stock_is_real_in_both_cities(self):
        from tools.sim import distribution as distribution_mod
        self.assertEqual(distribution_mod.housing_pressure(
            self.store, self.data, "rupsha_city")["total_units"],
            140)
        self.assertEqual(distribution_mod.housing_pressure(
            self.store, self.data, "shibnagar_town")["total_units"],
            39)

    def test_09_11_14_engine_run_exercises_services_growth_and_trade(
            self):
        self.sim.run_days(65)
        summary = self.sim.summary()
        self.assertEqual(summary["ledger_mismatches"], 0)
        self.assertGreaterEqual(self.store.row(
            "SELECT COUNT(*) AS n FROM municipal_budgets")["n"], 4)
        self.assertGreaterEqual(self.store.row(
            "SELECT COUNT(*) AS n FROM city_statistics")["n"], 4)
        self.assertGreaterEqual(self.store.row(
            "SELECT COUNT(*) AS n FROM trade_flows")["n"], 1)

    def test_10_growth_metrics_are_live(self):
        from tools.sim import growth as growth_mod
        m = growth_mod.city_metrics(self.store, self.data,
                                    "rupsha_city")
        self.assertEqual(m["population"], cities_mod.city_population(
            self.store, self.data, "rupsha_city"))
        self.assertGreater(m["population"], 0)
        self.assertTrue(0 <= m["development_index"] <= 100)

    def test_12_export_exists_for_the_deferred_3d_layer(self):
        export = cityview_mod.export_city_state(
            self.store, self.data, "rupsha_city")
        for key in ("city", "zones", "terrain", "parcels",
                    "buildings", "roads", "infrastructure",
                    "services", "analytics"):
            self.assertIn(key, export)
        self.assertTrue(export["roads"]["edges"])

    def test_14_intercity_route_exists(self):
        route = regional_mod.intercity_route(
            self.data, "d1_civic", "c2_civic")
        self.assertIsNotNone(route)
        self.assertIn("RC-ROAD-1", route["segment_ids"])


if __name__ == "__main__":
    unittest.main()
