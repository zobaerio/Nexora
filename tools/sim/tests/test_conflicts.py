"""Session 02 Unit 10 — Social Conflict & Resolution: conflicts
diagnosed from measured conflict levels and real circumstances,
mediation by real people, resolution/escalation with consequences,
cooldowns preventing conflict spam."""
import unittest

from tools.sim.tests.common import (make_household, make_person,
                                    make_store, rng, set_profile)
from tools.sim import conflicts
from tools.sim import family_economy as fe
from tools.sim import relationships as rel
from tools.sim import social


def _hot_pair(store, a, b, fights=2):
    rel.add_edge(store, a, b, "acquaintance", 480, affection=10)
    for i in range(fights):
        social.record_interaction(store, a, b, "leisure", "conflict",
                                  1000 + i)


class TestConflicts(unittest.TestCase):
    def test_no_conflict_without_measured_heat(self):
        store = make_store()
        a = make_person(store, age=30, first="A")
        b = make_person(store, age=30, first="B")
        rel.add_edge(store, a, b, "acquaintance", 480, affection=30)
        social.record_interaction(store, a, b, "leisure", "bonded", 1000)
        self.assertEqual(conflicts.detect_conflicts(store, 2000), [])

    def test_detection_and_cause_from_circumstance(self):
        store = make_store()
        a = make_person(store, age=30, first="A")
        b = make_person(store, age=30, first="B")
        hid, _ = make_household(store, [a])
        make_household(store, [b])
        # Friction above the opening threshold but below the
        # rivalry threshold (two real fights would form a rivalry,
        # whose -35 affection honestly reads as relationship
        # strain): set the measured level directly as a fixture.
        rel.add_edge(store, a, b, "acquaintance", 480, affection=10)
        social.record_interaction(store, a, b, "leisure", "conflict",
                                  1000)
        edge = rel.get_edge(store, a, b, "acquaintance")
        store.execute("UPDATE social_profiles SET conflict = 45"
                      " WHERE relationship_id = ?",
                      (edge["relationship_id"],))
        created = conflicts.detect_conflicts(store, 5000)
        self.assertEqual(len(created), 1)
        rec = store.row("SELECT * FROM conflict_records"
                        " WHERE conflict_id = ?", (created[0],))
        self.assertEqual(rec["cause"], "misunderstanding")
        fe.record_month(store, hid, 1, 5000, income=1, food=1,
                        housing=1, transport=1, other=1, emergency=900)
        c = make_person(store, age=30, first="C")
        _hot_pair(store, a, c)
        created2 = conflicts.detect_conflicts(store, 6000)
        self.assertEqual(len(created2), 1)
        rec2 = store.row("SELECT * FROM conflict_records"
                         " WHERE conflict_id = ?", (created2[0],))
        self.assertEqual(rec2["cause"], "resource_dispute")

    def test_resolution_by_mediator(self):
        store = make_store()
        a = make_person(store, age=30, first="A")
        b = make_person(store, age=30, first="B")
        friend = make_person(store, age=35, first="Mediator")
        make_household(store, [a, b, friend])
        _hot_pair(store, a, b)
        rel.add_edge(store, a, friend, "friend", 480, affection=40)
        rel.add_edge(store, b, friend, "friend", 480, affection=40)
        set_profile(store, friend, empathy=95)
        set_profile(store, a, patience=90)
        set_profile(store, b, patience=90)
        created = conflicts.detect_conflicts(store, 5000)
        rec = store.row("SELECT * FROM conflict_records"
                        " WHERE conflict_id = ?", (created[0],))
        outcome = None
        for week in range(1, 6):
            outcome = conflicts.attempt_resolution(
                store, rng(), rec, 5000 + week * 7 * 1440)
            if outcome != "open":
                break
            rec = store.row("SELECT * FROM conflict_records"
                            " WHERE conflict_id = ?", (created[0],))
        self.assertEqual(outcome, "resolved")
        final = store.row("SELECT * FROM conflict_records"
                          " WHERE conflict_id = ?", (created[0],))
        self.assertEqual(final["mediator_character_id"], friend)
        self.assertLess(conflicts.pair_conflict_level(store, a, b), 50)
        ev = store.row("SELECT * FROM life_events WHERE character_id = ?"
                       " AND event_type = 'conflict_resolved'", (a,))
        self.assertIsNotNone(ev)

    def test_cooldown_prevents_respam(self):
        store = make_store()
        a = make_person(store, age=30, first="A")
        b = make_person(store, age=30, first="B")
        _hot_pair(store, a, b)
        created = conflicts.detect_conflicts(store, 5000)
        store.execute("UPDATE conflict_records SET status = 'resolved',"
                      " closed_at_game_minutes = 6000"
                      " WHERE conflict_id = ?", (created[0],))
        # Still hot, but inside the 30-day cooldown: nothing opens.
        self.assertEqual(conflicts.detect_conflicts(store, 7000), [])
        # After the cooldown, a still-hot pair can conflict again.
        later = conflicts.detect_conflicts(store, 6000 + 31 * 1440)
        self.assertEqual(len(later), 1)


if __name__ == "__main__":
    unittest.main()
