"""Unit 02 — Personality: generation, the derived-trait mapping,
profession affinity (statistical), slow clamped drift."""
import unittest

from tools.sim.tests.common import make_person, make_store, rng, set_profile
from tools.sim import personality as pm


class TestPersonality(unittest.TestCase):
    def test_generate_ranges_and_determinism(self):
        r1, r2 = rng(), rng()
        p1 = pm.generate(r1.stream("personality", "X"))
        p2 = pm.generate(r2.stream("personality", "X"))
        self.assertEqual(p1, p2)
        self.assertEqual(set(p1.keys()), set(pm.ATTRIBUTES))
        for v in p1.values():
            self.assertTrue(0 <= v <= 100)

    def test_canonical_trait_mapping(self):
        profile = {a: 50 for a in pm.ATTRIBUTES}
        profile.update(empathy=100, cooperation=0, extraversion=33,
                       ambition=71, discipline=22, risk_tolerance=88)
        traits = pm.canonical_traits(profile)
        self.assertEqual(traits["trait_kindness"], 60)  # .6*100 + .4*0
        self.assertEqual(traits["trait_sociability"], 33)
        self.assertEqual(traits["trait_ambition"], 71)
        self.assertEqual(traits["trait_discipline"], 22)
        self.assertEqual(traits["trait_risk_tolerance"], 88)

    def test_profession_affinity_statistical(self):
        r = rng("affinity")
        docs = [pm.generate(r.stream("p", "doc", i), "doctor")
                for i in range(300)]
        cons = [pm.generate(r.stream("p", "con", i), "construction_worker")
                for i in range(300)]
        mean_doc = sum(p["intelligence"] for p in docs) / 300
        mean_con = sum(p["intelligence"] for p in cons) / 300
        self.assertGreater(mean_doc, mean_con + 5)

    def test_nudge_clamped_and_rederived(self):
        store = make_store()
        cid = make_person(store)
        before = pm.get_profile(store, cid)["ambition"]
        pm.nudge(store, cid, 480, ambition=50)  # asks +50, clamps to +6
        after = pm.get_profile(store, cid)["ambition"]
        self.assertEqual(after, min(100, before + 6))
        char = store.row("SELECT trait_ambition FROM characters"
                         " WHERE character_id = ?", (cid,))
        self.assertEqual(char["trait_ambition"], after)


if __name__ == "__main__":
    unittest.main()
