"""Session 03 Unit 06 — Road Network Engine."""
import unittest

from tools.sim import cities as cities_mod
from tools.sim import roads as roads_mod
from tools.sim.tests.common import data, make_store, rng

GOLIS = {"seg_goli_1", "seg_goli_2", "seg_goli_3"}


class TestRoads(unittest.TestCase):
    def setUp(self):
        self.d = data()
        self.spec = self.d.city_spec("rupsha_city")
        self.graph = roads_mod.build_graph(self.spec)

    def test_district_graph_is_one_network(self):
        comps = roads_mod.components(self.graph, "walk")
        self.assertEqual(len(comps), 1)
        used = {e["segment_id"] for e in self.graph.edges}
        all_ids = {s["id"] for s in self.spec["road_segments"]}
        self.assertEqual(used, all_ids)

    def test_town_graph_is_one_network(self):
        spec = self.d.city_spec("shibnagar_town")
        graph = roads_mod.build_graph(spec)
        self.assertEqual(len(roads_mod.components(graph, "walk")), 1)

    def test_motor_route_avoids_lanes(self):
        route = roads_mod.pathfind(
            self.graph, roads_mod.zone_anchor(self.spec, "d1_market"),
            roads_mod.zone_anchor(self.spec, "d1_oldtown"), "motor")
        self.assertIsNotNone(route)
        self.assertFalse(set(route["segment_ids"]) & GOLIS)
        self.assertNotIn("seg_promenade", route["segment_ids"])
        self.assertGreater(route["distance_m"], 300)

    def test_rickshaw_may_use_the_golis(self):
        route = roads_mod.pathfind(
            self.graph, roads_mod.zone_anchor(self.spec, "d1_market"),
            roads_mod.zone_anchor(self.spec, "d1_oldtown"),
            "rickshaw")
        self.assertIsNotNone(route)
        classes = {e["road_class"] for e in self.graph.edges
                   if e["segment_id"] in route["segment_ids"]}
        self.assertTrue(classes <= roads_mod.MODES["rickshaw"])

    def test_route_to_bridge_gate_exists(self):
        route = roads_mod.pathfind(
            self.graph, roads_mod.zone_anchor(self.spec, "d1_market"),
            (520, 465), "motor")
        self.assertIsNotNone(route)
        self.assertIn("seg_bridge_approach", route["segment_ids"])

    def test_cycle_routes_inside_the_ring_network(self):
        route = roads_mod.pathfind(
            self.graph, roads_mod.zone_anchor(self.spec, "d1_midtown"),
            roads_mod.zone_anchor(self.spec, "d1_oldtown"), "cycle")
        self.assertIsNotNone(route)
        classes = {e["road_class"] for e in self.graph.edges
                   if e["segment_id"] in route["segment_ids"]}
        self.assertNotIn("arterial", classes)

    def test_cycle_barred_from_arterials_by_design(self):
        # GDD-07: bicycles go on collector/local/lane/promenade
        # only. The promenade is a spur off Civic Avenue (arterial),
        # so no legal cycle route park -> riverfront exists, while
        # walking it uses the promenade.
        self.assertIsNone(roads_mod.pathfind(
            self.graph, roads_mod.zone_anchor(self.spec, "d1_park"),
            roads_mod.zone_anchor(self.spec, "d1_riverfront"),
            "cycle"))
        walk = roads_mod.pathfind(
            self.graph, roads_mod.zone_anchor(self.spec, "d1_park"),
            roads_mod.zone_anchor(self.spec, "d1_riverfront"),
            "walk")
        self.assertIsNotNone(walk)

    def test_snaps_are_documented(self):
        # The v1 blockout's near-miss joins (uptown local, bridge
        # approach) connect only through reported snaps.
        self.assertGreaterEqual(len(self.graph.snaps), 1)
        for snap in self.graph.snaps:
            self.assertLessEqual(snap["distance_m"],
                                 roads_mod.SNAP_END_M)
            self.assertIn("moved_to", snap)

    def test_setup_persists_segment_state(self):
        store = make_store()
        cities_mod.setup_cities(store, self.d, rng())
        self.assertEqual(store.row("SELECT COUNT(*) AS n FROM"
                                   " road_segments")["n"], 28)
        seg = store.row("SELECT * FROM road_segments WHERE"
                        " segment_id = 'seg_civic_ave_n'")
        self.assertEqual(seg["lanes"], 4)
        self.assertEqual(seg["speed_limit_kmh"], 40)
        self.assertAlmostEqual(seg["length_m"], 440.0)
        store.close()


if __name__ == "__main__":
    unittest.main()
