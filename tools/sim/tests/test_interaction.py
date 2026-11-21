"""Unit 10 — Interaction: co-located encounters bond, befriend and
conflict according to personality compatibility; household time
warms family edges."""
import unittest

from tools.sim.tests.common import (make_household, make_person,
                                    make_store, rng, set_profile)
from tools.sim import emotions as emo
from tools.sim import interaction as inter
from tools.sim import relationships as rel

ALL_ATTRS = ("extraversion", "confidence", "intelligence", "curiosity",
             "patience", "creativity", "ambition", "empathy",
             "risk_tolerance", "discipline", "cooperation",
             "emotional_sensitivity")


def _profile(store, cid, **values):
    full = {a: 50 for a in ALL_ATTRS}
    full.update(values)
    set_profile(store, cid, **full)


class TestInteraction(unittest.TestCase):
    def test_repeated_good_encounters_befriend(self):
        store = make_store()
        a = make_person(store, first="A")
        b = make_person(store, first="B")
        _profile(store, a)  # identical profiles -> compatibility 100
        _profile(store, b)
        outcomes = [inter.interact_pair(store, rng(), a, b, "leisure",
                                        480 + i * 60) for i in range(6)]
        self.assertIn("befriended", outcomes)
        self.assertIsNotNone(rel.get_edge(store, a, b, "friend"))
        memories = store.row("SELECT COUNT(*) AS n FROM character_memories"
                             " WHERE character_id = ? AND event_type ="
                             " 'new_friend'", (a,))["n"]
        self.assertEqual(memories, 1)

    def test_clashing_impatient_pair_conflicts(self):
        store = make_store()
        a = make_person(store, first="A")
        b = make_person(store, first="B")
        _profile(store, a, patience=0, empathy=0, cooperation=0,
                 emotional_sensitivity=0, risk_tolerance=0, extraversion=0)
        _profile(store, b, patience=100, empathy=100, cooperation=100,
                 emotional_sensitivity=100, risk_tolerance=100,
                 extraversion=100)
        before = emo.get_emotions(store, a)["anger"]
        result = inter.interact_pair(store, rng(), a, b, "leisure", 480)
        self.assertEqual(result, "conflict")
        self.assertGreater(emo.get_emotions(store, a)["anger"], before)

    def test_household_time_warms_family(self):
        store = make_store()
        a = make_person(store, first="A")
        b = make_person(store, first="B", sex="female")
        hid, _ = make_household(store, [a, b])
        rel.add_edge(store, a, b, "spouse", 480, affection=50)
        inter.household_time(store, hid, 480)
        self.assertEqual(rel.get_edge(store, a, b, "spouse")["affection"],
                         51)


if __name__ == "__main__":
    unittest.main()
