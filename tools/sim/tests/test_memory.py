"""Unit 03 — Memory: episodic storage for Full tier only, the
200-memory retention cap forgetting the weakest first, event log."""
import unittest

from tools.sim.tests.common import make_person, make_store
from tools.sim import memory as mem


class TestMemory(unittest.TestCase):
    def test_full_tier_records_scheduled_does_not(self):
        store = make_store()
        full = make_person(store, sim_tier="full")
        sched = make_person(store, sim_tier="scheduled", first="Sched")
        self.assertIsNotNone(mem.record_memory(store, full, "met_friend",
                                               20, 480))
        self.assertIsNone(mem.record_memory(store, sched, "met_friend",
                                            20, 480))
        n = store.row("SELECT COUNT(*) AS n FROM character_memories"
                      " WHERE character_id = ?", (sched,))["n"]
        self.assertEqual(n, 0)

    def test_retention_cap_keeps_strongest(self):
        store = make_store()
        cid = make_person(store, sim_tier="full")
        mem.record_memory(store, cid, "defining_moment", 100, 480)
        for i in range(240):
            mem.record_memory(store, cid, "minor", 1, 480 + i + 1)
        rows = store.rows("SELECT event_type FROM character_memories"
                          " WHERE character_id = ?", (cid,))
        self.assertEqual(len(rows), mem.MEMORY_CAP)
        self.assertIn("defining_moment", {r["event_type"] for r in rows})

    def test_memories_about_strongest_first(self):
        store = make_store()
        a = make_person(store, sim_tier="full")
        b = make_person(store, sim_tier="full", first="Other")
        mem.record_memory(store, a, "small", 5, 480, other_character_id=b)
        mem.record_memory(store, a, "huge", 80, 500, other_character_id=b)
        got = mem.memories_about(store, a, b)
        self.assertEqual(got[0]["event_type"], "huge")

    def test_life_event_log(self):
        store = make_store()
        cid = make_person(store, sim_tier="scheduled")
        mem.log_life_event(store, cid, "job_gain", 480,
                           details={"profession": "chef"})
        row = store.row("SELECT * FROM life_events WHERE character_id = ?",
                        (cid,))
        self.assertEqual(row["event_type"], "job_gain")


if __name__ == "__main__":
    unittest.main()
