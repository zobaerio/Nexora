"""Session 02 Units 04 + 06 — Social Relationship & Interaction
Engines: colleague/neighbour/rival edges, familiarity and conflict
dynamics, neighbour gatherings, network views."""
import unittest

from tools.sim.tests.common import (data, employ, make_household,
                                    make_person, make_store, rng)
from tools.sim import interaction as inter
from tools.sim import relationships as rel
from tools.sim import social


class TestSocialDynamics(unittest.TestCase):
    def test_familiarity_grows_through_interaction(self):
        store = make_store()
        a = make_person(store, age=30, first="A")
        b = make_person(store, age=30, first="B")
        rel.add_edge(store, a, b, "acquaintance", 480, affection=15)
        social.record_interaction(store, a, b, "leisure", "bonded", 1000)
        social.record_interaction(store, a, b, "leisure", "bonded", 2000)
        edge = rel.get_edge(store, a, b, "acquaintance")
        prof = social.profile_of(store, edge["relationship_id"])
        self.assertEqual(prof["interaction_count"], 2)
        self.assertEqual(prof["familiarity"], 8)
        net = social.network(store, a)
        entry = next(n for n in net if n["type"] == "acquaintance")
        self.assertEqual(entry["strength"], social.strength(edge))
        self.assertEqual(entry["familiarity"], 8)

    def test_colleague_edge_at_workplace_break(self):
        store = make_store()
        d = data()
        a = make_person(store, age=30, first="T1")
        b = make_person(store, age=32, first="T2")
        employ(store, d, a, "teacher")
        employ(store, d, b, "teacher")
        social.record_interaction(store, a, b, "break", "neutral", 1000)
        self.assertIsNotNone(rel.get_edge(store, a, b, "colleague"))
        # A leisure meeting does not make colleagues of strangers in
        # different professions.
        c = make_person(store, age=30, first="C")
        employ(store, d, c, "chef")
        social.record_interaction(store, a, c, "break", "neutral", 1000)
        self.assertIsNone(rel.get_edge(store, a, c, "colleague"))

    def test_rivalry_forms_from_repeated_conflict_only(self):
        store = make_store()
        a = make_person(store, age=30, first="A")
        b = make_person(store, age=30, first="B")
        rel.add_edge(store, a, b, "acquaintance", 480, affection=10)
        social.record_interaction(store, a, b, "leisure", "conflict", 1000)
        self.assertIsNone(rel.get_edge(store, a, b, "rival"))
        social.record_interaction(store, a, b, "leisure", "conflict", 2000)
        self.assertIsNotNone(rel.get_edge(store, a, b, "rival"))
        hist = rel.history_of(store, a, b)
        self.assertTrue(any(h["event"] == "rivalry_formed" for h in hist))

    def test_weekly_decay_cools_conflict(self):
        store = make_store()
        a = make_person(store, age=30, first="A")
        b = make_person(store, age=30, first="B")
        rel.add_edge(store, a, b, "acquaintance", 480)
        social.record_interaction(store, a, b, "leisure", "conflict", 1000)
        edge = rel.get_edge(store, a, b, "acquaintance")
        social.weekly_decay(store, 2000)
        prof = social.profile_of(store, edge["relationship_id"])
        self.assertEqual(prof["conflict"], 22)


class TestNeighbourGathering(unittest.TestCase):
    def test_gathering_creates_neighbour_edges(self):
        store = make_store()
        people = [make_person(store, age=30 + i, first=f"N{i}")
                  for i in range(4)]
        make_household(store, people[:2])
        make_household(store, people[2:])
        # Both fixture households sit in d1_midtown.
        meetings = social.neighbour_gathering(store, rng(), data(), 10000)
        self.assertGreaterEqual(meetings, 1)
        edges = store.rows("SELECT * FROM relationships"
                           " WHERE relation_type = 'neighbour'")
        self.assertGreaterEqual(len(edges), 2)  # symmetric pair
        ev = store.row("SELECT * FROM life_events"
                       " WHERE event_type = 'neighbour_meeting'")
        self.assertIsNotNone(ev)
        # Second gathering: pairs already neighbours — no duplicate
        # edges, familiarity still grows.
        social.neighbour_gathering(store, rng(), data(), 20000)
        edges2 = store.rows("SELECT * FROM relationships"
                            " WHERE relation_type = 'neighbour'")
        self.assertEqual(len(edges2), len(edges))


if __name__ == "__main__":
    unittest.main()
