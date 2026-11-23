"""Queue 15 Unit DA — Photograph Mechanic Implementation (GDD-04 §3.5,
Unit BY design).

Tests the photograph record: the gate (mission 1.4 unlock), the
presence rule, the dual write (photographs + discovery_progress in
one transaction), and the duplicate rule (a photograph of an already
discovered landmark writes nothing).
"""
import unittest

from tools.sim import photographs as ph
from tools.sim.tests.common import data, make_person, make_store

ACCT = "ACCT-TEST-1"
GM = 480

# The §3.4 discovery set as GDD-04 states it: 8 District 1 + 6
# District 2 + 5 Shibnagar landmarks, with the zones §3.4 assigns
# (17 verified by point-in-box, 3 assigned by description).
EXPECTED_ZONES = {
    "lm_clock_tower": "d1_market",
    "lm_bridge_approach": "d1_riverfront",
    "lm_launch_terminal": "d1_riverfront",
    "lm_park_pond": "d1_park",
    "lm_market_hall": "d1_market",
    "lm_rooftop_tower": "d1_uptown",
    "lm_station": "d1_transport",
    "lm_water_tank": "d1_oldtown",
    "d2_lm_northgate_tower": "d2_market",
    "d2_lm_north_bazar_hall": "d2_market",
    "d2_lm_maidan_pavilion": "d2_maidan",
    "d2_lm_garden_tank": "d2_garden",
    "d2_lm_north_gate_depot": "d2_transport",
    "d2_lm_north_heights_view": "d2_uptown",
    "c2_lm_ferry_ghat": "c2_transport",
    "c2_lm_bus_stand": "c2_transport",
    "c2_lm_primary_school": "c2_civic",
    "c2_lm_clinic": "c2_civic",
    "c2_lm_town_office": "c2_civic",
}


def _unlock(store, character_id):
    """Complete mission 1.4 for the character — the row the Phase 6
    mission system will write; tests insert it directly."""
    store.insert("mission_progress", character_id=character_id,
                 mission_id="1.4", status="completed", progress="{}",
                 updated_at_game_minutes=GM)


class TestDiscoverySet(unittest.TestCase):
    def test_set_is_19_landmarks_with_section_zones(self):
        self.assertEqual(ph.discovery_set(data()), EXPECTED_ZONES)

    def test_tables_exist(self):
        store = make_store()
        tables = {r["name"] for r in store.rows(
            "SELECT name FROM sqlite_master WHERE type = 'table'")}
        self.assertIn("photographs", tables)
        self.assertIn("discovery_progress", tables)
        self.assertIn("mission_progress", tables)


class TestGate(unittest.TestCase):
    def test_gate_closed_without_mission_14(self):
        store = make_store()
        player = make_person(store, age=30, first="Player")
        self.assertFalse(ph.photo_mode_unlocked(store, player))
        pid = ph.take_photograph(store, data(), ACCT, player,
                                 "lm_clock_tower", 600, "d1_market")
        self.assertIsNone(pid)
        self.assertEqual(store.row("SELECT COUNT(*) AS n FROM photographs")
                         ["n"], 0)

    def test_gate_open_after_mission_14(self):
        store = make_store()
        player = make_person(store, age=30, first="Player")
        _unlock(store, player)
        self.assertTrue(ph.photo_mode_unlocked(store, player))

    def test_other_mission_does_not_unlock(self):
        store = make_store()
        player = make_person(store, age=30, first="Player")
        store.insert("mission_progress", character_id=player,
                     mission_id="1.3", status="completed", progress="{}",
                     updated_at_game_minutes=GM)
        self.assertFalse(ph.photo_mode_unlocked(store, player))
        # An active (not completed) 1.4 does not unlock either.
        store.insert("mission_progress", character_id=player,
                     mission_id="1.4", status="active", progress="{}",
                     updated_at_game_minutes=GM)
        self.assertFalse(ph.photo_mode_unlocked(store, player))


class TestTakePhotograph(unittest.TestCase):
    def _unlocked(self, store):
        player = make_person(store, age=30, first="Player")
        _unlock(store, player)
        return player

    def test_writes_both_rows_in_one_write(self):
        store = make_store()
        player = self._unlocked(store)
        pid = ph.take_photograph(store, data(), ACCT, player,
                                 "lm_clock_tower", 600, "d1_market")
        self.assertIsNotNone(pid)
        self.assertTrue(pid.startswith("PH"))
        photo = store.row("SELECT * FROM photographs WHERE"
                          " photograph_id = ?", (pid,))
        self.assertEqual(photo["account_id"], ACCT)
        self.assertEqual(photo["character_id"], player)
        self.assertEqual(photo["discoverable_id"], "lm_clock_tower")
        self.assertEqual(photo["taken_at_game_minutes"], 600)
        self.assertEqual(photo["taken_in_zone"], "d1_market")
        disc = store.row("SELECT * FROM discovery_progress WHERE"
                         " account_id = ? AND discoverable_type ="
                         " 'landmark' AND discoverable_id = ?",
                         (ACCT, "lm_clock_tower"))
        self.assertIsNotNone(disc)
        self.assertEqual(disc["discovered_at_game_minutes"], 600)
        self.assertEqual(disc["discovered_in_zone"], "d1_market")

    def test_wrong_zone_refused(self):
        store = make_store()
        player = self._unlocked(store)
        pid = ph.take_photograph(store, data(), ACCT, player,
                                 "lm_clock_tower", 600, "d1_riverfront")
        self.assertIsNone(pid)
        self.assertEqual(store.row("SELECT COUNT(*) AS n FROM photographs")
                         ["n"], 0)
        self.assertEqual(store.row(
            "SELECT COUNT(*) AS n FROM discovery_progress")["n"], 0)

    def test_bus_route_cannot_be_photographed(self):
        store = make_store()
        player = self._unlocked(store)
        pid = ph.take_photograph(store, data(), ACCT, player,
                                 "bus_route_terminal_loop", 600,
                                 "d1_transport")
        self.assertIsNone(pid)

    def test_unknown_discoverable_refused(self):
        store = make_store()
        player = self._unlocked(store)
        pid = ph.take_photograph(store, data(), ACCT, player,
                                 "lm_no_such_place", 600, "d1_market")
        self.assertIsNone(pid)

    def test_duplicate_photograph_writes_nothing(self):
        store = make_store()
        player = self._unlocked(store)
        first = ph.take_photograph(store, data(), ACCT, player,
                                   "lm_market_hall", 600, "d1_market")
        self.assertIsNotNone(first)
        second = ph.take_photograph(store, data(), ACCT, player,
                                    "lm_market_hall", 700, "d1_market")
        self.assertIsNone(second)
        self.assertEqual(store.row("SELECT COUNT(*) AS n FROM photographs")
                         ["n"], 1)
        self.assertEqual(store.row(
            "SELECT COUNT(*) AS n FROM discovery_progress")["n"], 1)

    def test_photograph_after_visit_writes_nothing(self):
        # A visit already wrote the discovery row (§3.4): the
        # photograph would add no discovery, so it writes nothing.
        store = make_store()
        player = self._unlocked(store)
        store.insert("discovery_progress", account_id=ACCT,
                     discoverable_type="landmark",
                     discoverable_id="lm_park_pond",
                     discovered_at_game_minutes=500,
                     discovered_in_zone="d1_park")
        pid = ph.take_photograph(store, data(), ACCT, player,
                                 "lm_park_pond", 600, "d1_park")
        self.assertIsNone(pid)
        self.assertEqual(store.row("SELECT COUNT(*) AS n FROM photographs")
                         ["n"], 0)

    def test_two_accounts_photograph_independently(self):
        store = make_store()
        player = self._unlocked(store)
        first = ph.take_photograph(store, data(), ACCT, player,
                                   "c2_lm_clinic", 600, "c2_civic")
        second = ph.take_photograph(store, data(), "ACCT-TEST-2",
                                    player, "c2_lm_clinic", 650,
                                    "c2_civic")
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
