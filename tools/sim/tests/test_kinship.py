"""Session 02 Unit 01 — Family Formation: derived extended kinship,
guardianship, relationship history and graph consistency."""
import unittest

from tools.sim.tests.common import (make_household, make_person,
                                    make_store)
from tools.sim import kinship
from tools.sim import relationships as rel


def _family(store):
    """grandparent + two parent-siblings; one parent has two kids,
    the other has one kid (a cousin)."""
    gp = make_person(store, age=70, first="Gp")
    p1 = make_person(store, age=45, first="P1")
    p2 = make_person(store, age=42, first="P2")
    sp = make_person(store, age=44, first="Sp")
    k1 = make_person(store, age=15, first="K1")
    k2 = make_person(store, age=12, first="K2")
    cousin = make_person(store, age=14, first="Cuz")
    for parent, child in ((gp, p1), (gp, p2)):
        rel.add_edge(store, parent, child, "parent", 480, both_ways=False)
        rel.add_edge(store, child, parent, "child", 480, both_ways=False)
    rel.add_edge(store, p1, p2, "sibling", 480)
    rel.add_edge(store, p1, sp, "spouse", 480)
    for parent, child in ((p1, k1), (p1, k2), (sp, k1), (sp, k2),
                          (p2, cousin)):
        rel.add_edge(store, parent, child, "parent", 480, both_ways=False)
        rel.add_edge(store, child, parent, "child", 480, both_ways=False)
    rel.add_edge(store, k1, k2, "sibling", 480)
    return gp, p1, p2, sp, k1, k2, cousin


class TestKinship(unittest.TestCase):
    def test_derived_kinship(self):
        store = make_store()
        gp, p1, p2, sp, k1, k2, cousin = _family(store)
        self.assertEqual(kinship.grandparents(store, k1), [gp])
        self.assertEqual(kinship.grandchildren(store, gp),
                         sorted([k1, k2, cousin]))
        self.assertEqual(kinship.uncles_aunts(store, k1), [p2])
        self.assertEqual(kinship.cousins(store, k1), [cousin])
        self.assertEqual(kinship.cousins(store, cousin), sorted([k1, k2]))
        self.assertEqual(kinship.nephews_nieces(store, p2),
                         sorted([k1, k2]))
        self.assertEqual(kinship.parents_in_law(store, sp), [gp])
        self.assertTrue(kinship.is_kin(store, k1, cousin))
        tree = kinship.family_tree(store, k1)
        self.assertEqual(tree["grandparents"][0]["character_id"], gp)
        self.assertEqual(tree["cousins"][0]["character_id"], cousin)

    def test_kinship_is_derived_not_stored(self):
        """No 'grandparent'/'cousin' edges may exist in the table —
        extended kinship is computed, so it cannot go stale."""
        store = make_store()
        _family(store)
        rows = store.rows("SELECT DISTINCT relation_type FROM relationships")
        types = {r["relation_type"] for r in rows}
        self.assertNotIn("grandparent", types)
        self.assertNotIn("cousin", types)
        self.assertNotIn("uncle", types)

    def test_relationship_history_records_formation(self):
        store = make_store()
        a = make_person(store, age=30, first="A")
        b = make_person(store, age=28, first="B")
        rel.add_edge(store, a, b, "friend", 480, affection=20)
        hist = rel.history_of(store, a, b)
        formed = [h for h in hist if h["event"] == "formed"]
        self.assertEqual(len(formed), 2)  # symmetric: both directions
        self.assertTrue(all(h["relation_type"] == "friend"
                            for h in formed))

    def test_guardianship_after_parents_die(self):
        store = make_store()
        gp, p1, p2, sp, k1, k2, cousin = _family(store)
        hid, _ = make_household(store, [gp, p1, sp, k1, k2])
        # Both of k1's parents die; the grandparent in the household
        # becomes guardian.
        for dead in (p1, sp):
            store.execute("UPDATE characters SET died_at_game_minutes"
                          " = 1000 WHERE character_id = ?", (dead,))
        created = kinship.ensure_guardianship(store, 2000)
        pairs = dict((c, g) for c, g in created)
        self.assertEqual(pairs.get(k1), gp)
        self.assertEqual(kinship.guardian_of(store, k1), gp)
        # Idempotent: a second sweep creates nothing new.
        self.assertEqual(kinship.ensure_guardianship(store, 3000), [])
        ev = store.row("SELECT * FROM life_events WHERE character_id = ?"
                       " AND event_type = 'guardianship'", (k1,))
        self.assertIsNotNone(ev)

    def test_no_guardianship_with_living_parent(self):
        store = make_store()
        gp, p1, p2, sp, k1, k2, cousin = _family(store)
        make_household(store, [gp, p1, sp, k1, k2])
        self.assertEqual(kinship.ensure_guardianship(store, 2000), [])
        self.assertIsNone(kinship.guardian_of(store, k1))


if __name__ == "__main__":
    unittest.main()
