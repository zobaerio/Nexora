"""Session 02 Unit 09 — Social Events: celebrations of real life
events, culture festivals, public meetings, family gatherings —
with participants, locations and written-back consequences."""
import json
import unittest

from tools.sim.tests.common import (data, make_household, make_person,
                                    make_store, rng)
from tools.sim import culture
from tools.sim import events
from tools.sim import memory as memory_mod
from tools.sim import relationships as rel


class TestEvents(unittest.TestCase):
    def test_wedding_celebration_follows_marriage(self):
        store = make_store()
        a = make_person(store, age=28, first="A")
        b = make_person(store, age=27, first="B")
        make_household(store, [a, b])
        rel.marry(store, a, b, 1000)
        created = events.celebrate_life_events(store, data(), rng(),
                                               2000)
        self.assertEqual(len(created), 1)
        ev = store.row("SELECT * FROM social_events"
                       " WHERE event_type = 'wedding_celebration'")
        self.assertIsNotNone(ev)
        participants = json.loads(ev["participant_ids"])
        self.assertIn(a, participants)
        self.assertIn(b, participants)
        self.assertEqual(ev["zone_id"], "d1_midtown")
        # Once only: a second sweep creates nothing.
        self.assertEqual(events.celebrate_life_events(
            store, data(), rng(), 3000), [])
        mem = store.row("SELECT * FROM character_memories"
                        " WHERE character_id = ? AND event_type ="
                        " 'wedding_celebration'", (a,))
        self.assertIsNotNone(mem)

    def test_birth_celebration(self):
        store = make_store()
        a = make_person(store, age=30, first="Ma")
        b = make_person(store, age=30, first="Pa")
        make_household(store, [a, b])
        rel.add_edge(store, a, b, "spouse", 480)
        child = rel.have_child(store, rng(), a, b, 1000, set())
        created = events.celebrate_life_events(store, data(), rng(),
                                               2000)
        kinds = [store.row("SELECT event_type FROM social_events"
                           " WHERE event_id = ?", (e,))["event_type"]
                 for e in created]
        self.assertIn("birth_celebration", kinds)

    def test_festival_from_culture_calendar(self):
        store = make_store()
        d = data()
        a = make_person(store, age=30, first="F1")
        b = make_person(store, age=28, first="F2")
        hid, _ = make_household(store, [a, b])
        profile = culture.profile_for_household(store, d, hid)
        festival = profile["festivals"][0]
        eid = events.run_festival(store, d, rng(), profile, festival,
                                  5000)
        self.assertIsNotNone(eid)
        ev = store.row("SELECT * FROM social_events WHERE event_id = ?",
                       (eid,))
        self.assertEqual(ev["event_type"], "festival")
        self.assertEqual(ev["location_label"], festival["name"])
        self.assertIn(a, json.loads(ev["participant_ids"]))
        life = store.row("SELECT * FROM life_events WHERE character_id"
                         " = ? AND event_type = 'festival_celebration'",
                         (a,))
        self.assertIsNotNone(life)
        # A household of the other culture does not celebrate it.
        other = next(p for p in d.culture_profiles.values()
                     if p["id"] != profile["id"])
        self.assertIsNone(events.run_festival(
            store, d, rng(), other, festival, 5000)
            if not culture.households_with_profile(store, other["id"])
            else "has-households")

    def test_public_meeting(self):
        store = make_store()
        d = data()
        people = [make_person(store, age=30 + i, first=f"M{i}")
                  for i in range(5)]
        make_household(store, people)
        from tools.sim import community
        community.weekly_update(store, d, rng(), 480)
        eid = events.public_meeting(store, d, rng(), "d1_midtown", 5000)
        self.assertIsNotNone(eid)
        ev = store.row("SELECT * FROM social_events WHERE event_id = ?",
                       (eid,))
        self.assertGreaterEqual(len(json.loads(ev["participant_ids"])), 3)
        self.assertIn("topic", json.loads(ev["outcome"]))

    def test_family_gathering(self):
        store = make_store()
        gp = make_person(store, age=70, first="Gp")
        parent = make_person(store, age=45, first="Parent")
        kid = make_person(store, age=12, first="Kid")
        make_household(store, [gp])
        hid2, _ = make_household(store, [parent, kid])
        rel.add_edge(store, gp, parent, "parent", 480, both_ways=False)
        rel.add_edge(store, parent, gp, "child", 480, both_ways=False)
        rel.add_edge(store, parent, kid, "parent", 480, both_ways=False)
        rel.add_edge(store, kid, parent, "child", 480, both_ways=False)
        before = rel.get_edge(store, parent, gp, "child")["affection"]
        created = events.family_gathering(store, data(), rng(), 5000)
        self.assertEqual(len(created), 1)
        after = rel.get_edge(store, parent, gp, "child")["affection"]
        self.assertGreater(after, before)


if __name__ == "__main__":
    unittest.main()
