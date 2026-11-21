"""Unit 06 — Emotions: event-driven deltas (the owner's examples:
job loss raises stress, goal achievement raises happiness, family
death causes grief), sensitivity scaling, personality baselines."""
import unittest

from tools.sim.tests.common import (make_person, make_store, set_emotions,
                                    set_profile)
from tools.sim import emotions as emo


class TestEmotions(unittest.TestCase):
    def test_job_loss_raises_stress(self):
        store = make_store()
        cid = make_person(store)
        set_emotions(store, cid, stress=30, happiness=60)
        emo.apply_event(store, cid, "job_loss")
        got = emo.get_emotions(store, cid)
        self.assertGreater(got["stress"], 45)
        self.assertLess(got["happiness"], 60)

    def test_goal_complete_raises_happiness(self):
        store = make_store()
        cid = make_person(store)
        set_emotions(store, cid, happiness=40)
        emo.apply_event(store, cid, "goal_complete")
        self.assertGreaterEqual(emo.get_emotions(store, cid)["happiness"],
                                65)

    def test_grief_from_family_death(self):
        store = make_store()
        cid = make_person(store)
        set_emotions(store, cid, sadness=10)
        emo.apply_event(store, cid, "death_of_family")
        self.assertGreater(emo.get_emotions(store, cid)["sadness"], 40)

    def test_sensitivity_scales_negative_events(self):
        store = make_store()
        hi = make_person(store, first="Hi")
        lo = make_person(store, first="Lo")
        set_profile(store, hi, emotional_sensitivity=100)
        set_profile(store, lo, emotional_sensitivity=0)
        set_emotions(store, hi, sadness=10)
        set_emotions(store, lo, sadness=10)
        emo.apply_event(store, hi, "death_of_family")
        emo.apply_event(store, lo, "death_of_family")
        self.assertGreater(emo.get_emotions(store, hi)["sadness"],
                           emo.get_emotions(store, lo)["sadness"])

    def test_baselines_follow_personality(self):
        store = make_store()
        calm = {a: 50 for a in emo.EMOTIONS}
        patient = dict(calm)
        from tools.sim import personality as pm
        profile = {a: 50 for a in pm.ATTRIBUTES}
        base_calm = emo.baselines(profile)
        profile["patience"] = 100
        base_patient = emo.baselines(profile)
        self.assertLess(base_patient["stress"], base_calm["stress"])
        profile["ambition"] = 100
        self.assertGreater(emo.baselines(profile)["motivation"],
                           base_calm["motivation"])


if __name__ == "__main__":
    unittest.main()
