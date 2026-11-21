"""Session 02 Unit 07 — Culture & Tradition: data-driven profiles,
household assignment, festival calendar, traditions, and the
adoption rule reading the profile flag (Unit 01 integration)."""
import unittest

from tools.sim.tests.common import (data, make_household, make_person,
                                    make_store)
from tools.sim import culture
from tools.sim import kinship
from tools.sim import relationships as rel


class TestCulture(unittest.TestCase):
    def test_profiles_come_from_data(self):
        d = data()
        self.assertGreaterEqual(len(d.culture_profiles), 2)
        langs = {p["language"] for p in d.culture_profiles.values()}
        self.assertEqual(len(langs), len(d.culture_profiles))

    def test_assignment_is_stable_and_configured(self):
        store = make_store()
        d = data()
        a = make_person(store, age=30, first="A")
        hid, _ = make_household(store, [a])
        p1 = culture.profile_for_household(store, d, hid)
        p2 = culture.profile_for_household(store, d, hid)
        self.assertEqual(p1["id"], p2["id"])
        row = store.row("SELECT profile_id FROM household_culture"
                        " WHERE household_id = ?", (hid,))
        self.assertEqual(row["profile_id"], p1["id"])
        self.assertIn(p1["id"], d.culture_profiles)

    def test_festival_calendar(self):
        d = data()
        hits = culture.festivals_on(d, 45)
        self.assertTrue(any(f["id"] == "river_festival"
                            for _, f in hits))
        self.assertEqual(culture.festivals_on(d, 999), [])

    def test_tradition_observance(self):
        store = make_store()
        d = data()
        a = make_person(store, age=30, first="A")
        hid, _ = make_household(store, [a])
        profile = culture.profile_for_household(store, d, hid)
        tradition = profile["family_traditions"][0]
        self.assertTrue(culture.observe_tradition(
            store, d, hid, tradition, 1000))
        self.assertFalse(culture.observe_tradition(
            store, d, hid, "not_a_real_tradition", 1000))
        ev = store.row("SELECT * FROM life_events WHERE character_id = ?"
                       " AND event_type = 'tradition_observed'", (a,))
        self.assertIsNotNone(ev)

    def test_adoption_uses_profile_flag(self):
        """A non-kin guardian whose household culture enables
        adoption converts to a parent after sustained care."""
        store = make_store()
        d = data()
        guardian = make_person(store, age=40, first="Guardian")
        child = make_person(store, age=8, first="Orphan")
        hid, _ = make_household(store, [guardian, child])
        rel.add_edge(store, guardian, child, "guardian", 480,
                     both_ways=False)
        rel.add_edge(store, child, guardian, "ward", 480, both_ways=False)
        # Both shipped profiles enable adoption; before the care
        # period nothing converts.
        self.assertEqual(kinship.maybe_adopt(store, d, 480 + 30 * 1440),
                         [])
        adopted = kinship.maybe_adopt(
            store, d, 480 + (kinship.ADOPTION_MIN_GUARDIAN_DAYS + 1) * 1440)
        self.assertEqual(adopted, [child])
        edge = rel.get_edge(store, guardian, child, "parent")
        self.assertIsNotNone(edge)
        import json
        self.assertTrue(json.loads(edge["flags"]).get("adoptive"))
        # The adopted child now derives the guardian's kin as family.
        self.assertIn(guardian, rel.parents_of(store, child))


if __name__ == "__main__":
    unittest.main()
