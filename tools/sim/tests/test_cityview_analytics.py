"""Session 03 Units 12+13 — City-state export & analytics.

Unit 12's 3D half runs on Unreal on the owner's PC; acceptance
criterion 13 (3D performance) is DEFERRED there and is not
asserted anywhere in this suite. What is asserted is the data
layer UE will consume: a complete, live, JSON-ready city state
plus a data-driven map view.
"""
import json
import os
import tempfile
import unittest

from tools.sim import analytics as analytics_mod
from tools.sim import cityview as cityview_mod
from tools.sim import distribution as distribution_mod
from tools.sim import households as households_mod
from tools.sim.engine import Simulation


def _tmp_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


class TestCityViewAnalytics(unittest.TestCase):
    def setUp(self):
        self.path = _tmp_path()
        self.sim = Simulation(self.path, seed="view-test")
        self.sim.generate_population(120)
        self.store = self.sim.store
        self.data = self.sim.data

    def tearDown(self):
        self.sim.close()
        os.remove(self.path)

    def test_export_is_complete_and_json_ready(self):
        export = cityview_mod.export_city_state(
            self.store, self.data, "rupsha_city")
        self.assertEqual(export["city"]["city_id"], "rupsha_city")
        self.assertEqual(len(export["zones"]), 10)
        self.assertEqual(len(export["parcels"]), 42)
        self.assertEqual(len(export["buildings"]), 42)
        self.assertEqual(len(export["infrastructure"]), 10 * 8)
        self.assertTrue(export["roads"]["edges"])
        self.assertIn("documented_snaps", export["roads"])
        json.dumps(export)  # must serialize as-is for UE ingestion
        town = cityview_mod.export_city_state(
            self.store, self.data, "shibnagar_town")
        self.assertEqual(len(town["parcels"]), 22)
        self.assertEqual(len(town["zones"]), 6)

    def test_ascii_map_is_drawn_from_real_geometry(self):
        lines = cityview_mod.ascii_map(self.store, self.data,
                                       "rupsha_city")
        view = "\n".join(lines)
        self.assertEqual(len(lines), 46)
        self.assertIn("~", view)   # the river, south edge
        self.assertIn("#", view)   # roads
        self.assertIn("B", view)   # buildings
        town = "\n".join(cityview_mod.ascii_map(
            self.store, self.data, "shibnagar_town"))
        self.assertIn("~", town)

    def test_analytics_change_when_the_world_changes(self):
        before = analytics_mod.city_analytics(
            self.store, self.data, "shibnagar_town")
        self.assertEqual(before["population"], 0)
        target = None
        for h in self.store.rows(
                "SELECT * FROM households WHERE"
                " dissolved_at_game_minutes IS NULL"):
            rent = households_mod.current_rent(
                self.store, self.data, h["household_id"])
            if rent and rent >= 7000:
                target = h
                break
        self.assertIsNotNone(target)
        distribution_mod.migrate_household(
            self.store, self.data, target["household_id"],
            "shibnagar_town", {"test": "analytics"}, 480 + 40 * 1440)
        after = analytics_mod.city_analytics(
            self.store, self.data, "shibnagar_town")
        self.assertGreater(after["population"], 0)
        self.assertNotEqual(after["population"],
                            before["population"])

    def test_snapshots_persist_for_growth_history(self):
        out = analytics_mod.record_snapshots(
            self.store, self.data, 1, 480 + 30 * 1440)
        self.assertEqual(set(out), {"rupsha_city",
                                    "shibnagar_town"})
        rows = self.store.rows("SELECT * FROM city_statistics")
        self.assertEqual(len(rows), 2)
        metrics = json.loads(rows[0]["metrics"])
        self.assertIn("index", metrics["development"])
        self.assertIn("population", metrics)


if __name__ == "__main__":
    unittest.main()
