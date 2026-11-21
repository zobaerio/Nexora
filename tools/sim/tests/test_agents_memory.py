"""Session 09 — Multi-level memory: recording, retrieval with
access counting, dedupe, bounded compression, and the monthly
lift of major events into family / organisation / community /
civilization memory.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))

from tools.sim import agents as agents_mod  # noqa: E402
from tools.sim import memory as memory_mod  # noqa: E402
from tools.sim.tests.common import (data, make_household,  # noqa: E402
                                    make_person, make_store, rng)

GM = 480


class TestMemory(unittest.TestCase):
    def setUp(self):
        self.store = make_store()
        self.data = data()
        self.r = rng()

    def tearDown(self):
        self.store.close()

    def test_record_retrieve_and_dedupe(self):
        mid = agents_mod.record_agent_memory(
            self.store, "family", "HH-1", "marriage",
            {"ref": "LE-1"}, 80, GM)
        self.assertIsNotNone(mid)
        again = agents_mod.record_agent_memory(
            self.store, "family", "HH-1", "marriage",
            {"ref": "LE-1"}, 80, GM)
        self.assertIsNone(again)  # same source event: no duplicate
        hits = agents_mod.retrieve_memories(
            self.store, "family", "HH-1", event_kind="marriage")
        self.assertEqual(len(hits), 1)
        row = self.store.row("SELECT * FROM agent_memories WHERE"
                             " memory_id = ?", (mid,))
        self.assertEqual(row["access_count"], 1)

    def test_compression_bounds_the_level(self):
        for i in range(9):
            agents_mod.record_agent_memory(
                self.store, "family", "HH-2", "minor_event",
                {"ref": f"LE-C{i}"}, 10, GM + i)
        agents_mod.record_agent_memory(
            self.store, "family", "HH-2", "major_event",
            {"ref": "LE-BIG"}, 90, GM)
        agents_mod.compress_memories(self.store, "family", "HH-2",
                                     cap=4, threshold=40,
                                     game_minutes=GM + 100)
        rows = self.store.rows(
            "SELECT * FROM agent_memories WHERE level = 'family'"
            " AND owner_ref = 'HH-2'")
        self.assertLessEqual(len(rows), 4)
        kinds = {r["event_kind"] for r in rows}
        self.assertIn("compressed_summary", kinds)
        self.assertIn("major_event", kinds)  # important survives

    def test_memory_pass_lifts_major_events(self):
        a = make_person(self.store, age=30, first="MemA",
                        game_minutes=GM, r=self.r)
        b = make_person(self.store, age=28, first="MemB",
                        game_minutes=GM, r=self.r)
        hid, _pid = make_household(self.store, [a, b],
                                   game_minutes=GM)
        memory_mod.log_life_event(self.store, a, "marriage", GM,
                                  other_character_id=b)
        self.store.insert(
            "businesses", business_id="BZ-MEM", name="Mem Co",
            business_type="shop", category="retail",
            owner_character_id=a, status="closed",
            founded_at_game_minutes=GM,
            closed_at_game_minutes=GM + 50)
        self.store.insert(
            "business_events", event_id="BE-MEM-1",
            business_id="BZ-MEM", event_type="closed",
            details="{}", game_minutes=GM + 50)
        self.store.commit()
        agents_mod.memory_pass(self.store, self.data, 1, GM + 100)
        fam = self.store.rows(
            "SELECT * FROM agent_memories WHERE level = 'family'"
            " AND owner_ref = ?", (hid,))
        kinds = {r["event_kind"] for r in fam}
        self.assertIn("marriage", kinds)
        self.assertIn("business_closed", kinds)
        org = self.store.rows(
            "SELECT * FROM agent_memories WHERE level ="
            " 'organisation' AND owner_ref = 'BZ-MEM'")
        self.assertTrue(org)
        # Second pass: dedupe by source ref, nothing new.
        out = agents_mod.memory_pass(self.store, self.data, 2,
                                     GM + 200)
        self.assertEqual(out["family"], 0)


if __name__ == "__main__":
    unittest.main()
