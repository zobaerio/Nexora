"""Session 02 Units 11 + 12 — Social Mobility & Generational
Development: status changes from real outcomes, lineage, persisted
generational history, elder knowledge transfer."""
import unittest

from tools.sim.tests.common import (data, employ, make_household,
                                    make_person, make_store)
from tools.sim import decisions as dec
from tools.sim import generations as gen
from tools.sim import mobility
from tools.sim import relationships as rel


class TestMobility(unittest.TestCase):
    def test_baseline_then_change_on_promotion(self):
        store = make_store()
        d = data()
        a = make_person(store, age=35, first="Climber")
        make_household(store, [a])
        employ(store, d, a, "teacher", tier=1)
        n = mobility.monthly_check(store, d, 1000)
        self.assertGreaterEqual(n, 3)  # three baseline dimensions
        status = mobility.current_status(store, d, a)
        self.assertEqual(status["career_tier"], "1")
        # Promote for real, then the next check records the change.
        store.execute("UPDATE employments SET tier = 2"
                      " WHERE character_id = ?", (a,))
        mobility.monthly_check(store, d, 2000)
        hist = [h for h in mobility.mobility_summary(store, d, a)["history"]
                if h["dimension"] == "career_tier"]
        self.assertEqual(hist[-1]["from_value"], "1")
        self.assertEqual(hist[-1]["to_value"], "2")
        ev = store.row("SELECT * FROM life_events WHERE character_id = ?"
                       " AND event_type = 'status_change'", (a,))
        self.assertIsNotNone(ev)

    def test_hardship_direction_same_mechanism(self):
        store = make_store()
        d = data()
        a = make_person(store, age=40, first="Faller")
        make_household(store, [a])
        employ(store, d, a, "chef", tier=3)
        mobility.monthly_check(store, d, 1000)
        store.execute("UPDATE employments SET ended_at_game_minutes"
                      " = 1500 WHERE character_id = ?", (a,))
        mobility.monthly_check(store, d, 2000)
        status = mobility.current_status(store, d, a)
        self.assertEqual(status["economic_band"], "none")
        self.assertEqual(status["career_tier"], "0")


class TestGenerations(unittest.TestCase):
    def _lineage(self, store):
        gp = make_person(store, age=72, first="Gp")
        parent = make_person(store, age=45, first="Parent")
        kid = make_person(store, age=10, first="Kid")
        grandkid = make_person(store, age=2, first="GK")
        # grandkid is kid's sibling-generation fixture: parent->kid
        # only; add a child of kid's sibling line via parent again
        for p, c in ((gp, parent), (parent, kid)):
            rel.add_edge(store, p, c, "parent", 480, both_ways=False)
            rel.add_edge(store, c, p, "child", 480, both_ways=False)
        return gp, parent, kid

    def test_generation_index_and_lineage(self):
        store = make_store()
        gp, parent, kid = self._lineage(store)
        self.assertEqual(gen.generation_of(store, gp), 1)
        self.assertEqual(gen.generation_of(store, parent), 2)
        self.assertEqual(gen.generation_of(store, kid), 3)
        lin = gen.lineage(store, kid)
        self.assertEqual(set(lin["ancestors"]), {gp, parent})
        self.assertEqual(set(gen.descendants(store, gp)), {parent, kid})

    def test_knowledge_transfer(self):
        store = make_store()
        d = data()
        elder = make_person(store, age=70, first="Elder")
        kid = make_person(store, age=10, first="Kid")
        make_household(store, [elder, kid])
        dec.add_skill_xp(store, elder, "medicine", 60 * 50)
        n = gen.knowledge_transfer(store, d, 5000)
        self.assertEqual(n, 1)
        row = store.row("SELECT experience FROM character_skills"
                        " WHERE character_id = ? AND skill_id ="
                        " 'medicine'", (kid,))
        self.assertIsNotNone(row)
        self.assertGreater(row["experience"], 0)
        hist = gen.history_of(store, kid)
        self.assertTrue(any(h["event_type"] == "knowledge_transfer"
                            for h in hist))
        self.assertEqual(hist[0]["generation"], 1)

    def test_history_sweep_persists_births(self):
        store = make_store()
        a = make_person(store, age=30, first="Ma")
        b = make_person(store, age=30, first="Pa")
        make_household(store, [a, b])
        rel.add_edge(store, a, b, "spouse", 480)
        from tools.sim.tests.common import rng
        child = rel.have_child(store, rng(), a, b, 1000, set())
        written = gen.record_history_sweep(store, 2000)
        self.assertGreaterEqual(written, 1)
        hist = gen.history_of(store, child)
        self.assertTrue(any(h["event_type"] == "lineage_birth"
                            for h in hist))
        self.assertEqual(hist[0]["generation"], 2)
        # Idempotent.
        self.assertEqual(gen.record_history_sweep(store, 3000), 0)


if __name__ == "__main__":
    unittest.main()
