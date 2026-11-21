"""Session 03 Unit 14 — Multi-City Regional Interaction."""
import os
import tempfile
import unittest

from tools.sim import distribution as distribution_mod
from tools.sim import regional as regional_mod
from tools.sim.engine import Simulation


def _tmp_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


class TestRegional(unittest.TestCase):
    def setUp(self):
        self.path = _tmp_path()
        self.sim = Simulation(self.path, seed="region-test")
        self.sim.generate_population(140)
        self.store = self.sim.store
        self.data = self.sim.data

    def tearDown(self):
        self.sim.close()
        os.remove(self.path)

    def test_connections_are_persisted(self):
        rows = self.store.rows("SELECT * FROM regional_connections")
        ids = {r["connection_id"] for r in rows}
        self.assertIn("RC-ROAD-1", ids)
        self.assertIn("RC-FERRY-1", ids)
        for r in rows:
            self.assertEqual({r["from_city_id"], r["to_city_id"]},
                             {"rupsha_city", "shibnagar_town"})

    def test_intercity_route_crosses_the_bridge_link(self):
        route = regional_mod.intercity_route(
            self.data, "d1_market", "c2_market")
        self.assertIsNotNone(route)
        self.assertIn("RC-ROAD-1", route["segment_ids"])
        self.assertGreater(route["distance_m"], 500)

    def test_commuters_appear_when_a_worker_moves(self):
        self.assertEqual(regional_mod.commuters(
            self.store, self.data), {})
        moved = False
        for h in self.store.rows(
                "SELECT * FROM households WHERE"
                " dissolved_at_game_minutes IS NULL"):
            head = self.store.row(
                "SELECT e.profession_id FROM employments e JOIN"
                " household_members hm ON hm.character_id ="
                " e.character_id WHERE hm.household_id = ? AND"
                " hm.role = 'head' AND e.ended_at_game_minutes"
                " IS NULL", (h["household_id"],))
            if not head:
                continue
            workplace = self.data.professions[
                head["profession_id"]].get("workplace_zone")
            if not workplace or not workplace.startswith("d1_"):
                continue
            from tools.sim import households as households_mod
            rent = households_mod.current_rent(
                self.store, self.data, h["household_id"])
            if not rent or rent < 7000:
                continue
            result = distribution_mod.migrate_household(
                self.store, self.data, h["household_id"],
                "shibnagar_town", {"test": "commuter"},
                480 + 40 * 1440)
            if result is not None:
                moved = True
                break
        self.assertTrue(moved, "an employed household migrated")
        commuters = regional_mod.commuters(self.store, self.data)
        self.assertGreaterEqual(
            commuters.get(("shibnagar_town", "rupsha_city"), 0), 1)

    def test_monthly_trade_flows_are_persisted(self):
        flows = regional_mod.monthly_flows(
            self.store, self.data, 1, 480 + 30 * 1440)
        rows = self.store.rows("SELECT * FROM trade_flows")
        self.assertEqual(len(rows), len(flows))
        self.assertGreaterEqual(len(rows), 1)
        for r in rows:
            self.assertGreaterEqual(r["amount_ncr"], 0)
            self.assertIn(r["goods"],
                          ("manufactured_goods",
                           "agricultural_produce"))
        # The town's farmland produces from day one, so the produce
        # flow exists even while the town is still unpopulated.
        self.assertTrue(any(r["goods"] == "agricultural_produce"
                            for r in rows))


if __name__ == "__main__":
    unittest.main()
