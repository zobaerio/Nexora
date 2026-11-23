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

    def test_pair_flags_round_trip_and_canonicalisation(self):
        # Unit CA (Queue 14, GDD-15 §17.7): the pair store is one row
        # per unordered pair — (a, b) and (b, a) are the same row.
        store = make_store()
        a = make_person(store, first="A")
        b = make_person(store, first="B")
        self.assertIsNone(rel.get_pair_flag(store, a, b, "met_player"))
        self.assertEqual(rel.get_pair_flag(store, a, b, "met_player",
                                           default=False), False)
        rel.set_pair_flag(store, a, b, "met_player", True)
        self.assertTrue(rel.get_pair_flag(store, b, a, "met_player"))
        rel.set_pair_flag(store, b, a, "met_player", False)
        self.assertFalse(rel.get_pair_flag(store, a, b, "met_player"))
        rows = store.rows("SELECT * FROM relationship_pair_flags")
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["character_a_id"],
                          rows[0]["character_b_id"]),
                         (min(a, b), max(a, b)))

    def test_pair_flag_visible_across_edges(self):
        # The §17.3 limit, fixed: a flag written while the spouse edge
        # is selected is visible when the colleague edge is selected
        # next, because the flag lives on the pair, not the edge. The
        # edge-level store stays separate: an edge flag is not a pair
        # flag and never leaks into the pair store.
        store = make_store()
        a = make_person(store, first="A")
        b = make_person(store, first="B")
        rel.add_edge(store, a, b, "spouse", 480, affection=60)
        rel.add_edge(store, a, b, "colleague", 480, affection=20)
        rel.set_flag(store, a, b, "spouse", "met_at", "market")
        self.assertIsNone(rel.get_pair_flag(store, a, b, "met_at"))
        self.assertIsNone(rel.get_flag(store, a, b, "colleague",
                                       "met_at"))
        rel.set_pair_flag(store, a, b, "met_player", True)
        self.assertTrue(rel.get_pair_flag(store, a, b, "met_player"))
        self.assertTrue(rel.get_pair_flag(store, b, a, "met_player"))
        # The pair write did not touch either edge's flags.
        self.assertIsNone(rel.get_flag(store, a, b, "spouse",
                                       "met_player"))
        self.assertIsNone(rel.get_flag(store, a, b, "colleague",
                                       "met_player"))

    def test_pair_flag_self_pair_is_noop(self):
        store = make_store()
        a = make_person(store, first="A")
        rel.set_pair_flag(store, a, a, "met_player", True)
        self.assertIsNone(rel.get_pair_flag(store, a, a, "met_player"))
        self.assertEqual(store.rows(
            "SELECT * FROM relationship_pair_flags"), [])

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
