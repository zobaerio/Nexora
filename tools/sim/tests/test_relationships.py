"""Unit 07 — Relationships & family: edges and their direction
convention, semantic flags, marriage with household merge,
childbirth joining the family graph, weekly drift."""
import unittest

from tools.sim.tests.common import (make_household, make_person,
                                    make_store, rng)
from tools.sim import relationships as rel


class TestRelationships(unittest.TestCase):
    def test_symmetric_and_directional_edges(self):
        store = make_store()
        a = make_person(store, first="A")
        b = make_person(store, first="B")
        rel.add_edge(store, a, b, "spouse", 480, affection=60)
        self.assertIsNotNone(rel.get_edge(store, a, b, "spouse"))
        self.assertIsNotNone(rel.get_edge(store, b, a, "spouse"))
        rel.add_edge(store, a, b, "parent", 480, both_ways=False)
        self.assertIsNotNone(rel.get_edge(store, a, b, "parent"))
        self.assertIsNone(rel.get_edge(store, b, a, "parent"))
        self.assertEqual(rel.children_of(store, a), [b])
        self.assertEqual(rel.parents_of(store, b), [a])

    def test_scores_clamp_and_flags(self):
        store = make_store()
        a = make_person(store, first="A")
        b = make_person(store, first="B")
        rel.add_edge(store, a, b, "friend", 480, affection=98)
        rel.adjust_scores(store, a, b, 500, affection=50)
        self.assertEqual(rel.get_edge(store, a, b, "friend")["affection"],
                         100)
        rel.set_flag(store, a, b, "friend", "met_at", "market")
        self.assertEqual(rel.get_flag(store, a, b, "friend", "met_at"),
                         "market")

    def test_marriage_merges_households(self):
        store = make_store()
        a = make_person(store, first="A")
        b = make_person(store, first="B", sex="female")
        make_household(store, [a])
        make_household(store, [b])
        rel.marry(store, a, b, 480)
        self.assertEqual(rel.spouse_of(store, a), b)
        ca = store.row("SELECT household_id FROM characters"
                       " WHERE character_id = ?", (a,))
        cb = store.row("SELECT household_id FROM characters"
                       " WHERE character_id = ?", (b,))
        self.assertEqual(ca["household_id"], cb["household_id"])
        events = store.row("SELECT COUNT(*) AS n FROM life_events"
                           " WHERE event_type = 'marriage'")["n"]
        self.assertEqual(events, 2)

    def test_childbirth_joins_family_graph(self):
        store = make_store()
        a = make_person(store, first="A")
        b = make_person(store, first="B", sex="female")
        hid, _ = make_household(store, [a, b])
        rel.marry(store, a, b, 480)
        used = {("Test", "Person"), ("A", "Person"), ("B", "Person")}
        child = rel.have_child(store, rng(), b, a, 480, used)
        self.assertEqual(set(rel.children_of(store, a)), {child})
        self.assertEqual(set(rel.parents_of(store, child)), {a, b})
        child2 = rel.have_child(store, rng(), b, a, 500, used)
        self.assertIn(child2, rel.siblings_of(store, child))
        member = store.row("SELECT household_id FROM characters"
                           " WHERE character_id = ?", (child,))
        self.assertEqual(member["household_id"], hid)

    def test_weekly_drift_toward_baseline(self):
        store = make_store()
        a = make_person(store, first="A")
        b = make_person(store, first="B")
        rel.add_edge(store, a, b, "spouse", 480, affection=20)
        rel.weekly_drift(store, 480 + 7 * 1440)
        self.assertGreater(rel.get_edge(store, a, b, "spouse")["affection"],
                           20)


if __name__ == "__main__":
    unittest.main()
