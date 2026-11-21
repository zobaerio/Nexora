"""Unit 01 — Identity: persistent unique identities, derived age,
population composition (audit criterion: >=100 agents spanning all
11 professions plus child/student/elder)."""
import os
import tempfile
import unittest

from tools.sim.tests.common import make_person, make_store, rng
from tools.sim import identity as identity_mod
from tools.sim.engine import Simulation


class TestIdentity(unittest.TestCase):
    def test_create_person_and_card(self):
        store = make_store()
        cid = make_person(store, age=30, first="Arif", last="Hasan")
        card = identity_mod.profile_card(store, cid)
        self.assertTrue(card["human_id"].startswith("NEX-"))
        self.assertEqual(card["name"], "Arif Hasan")
        self.assertEqual(card["age"], 30)
        self.assertEqual(card["life_stage"], "Adult")
        self.assertTrue(card["alive"])
        self.assertEqual(card["nationality"], "Bangladeshi")
        self.assertIsNotNone(card["needs"])
        self.assertIsNotNone(card["emotions"])

    def test_unique_ids_and_names(self):
        store = make_store()
        ids = {make_person(store, age=25, first=f"P{i}", last="X")
               for i in range(20)}
        self.assertEqual(len(ids), 20)

    def test_age_is_derived(self):
        self.assertEqual(identity_mod.age_years(0, 364 * 1440), 0)
        self.assertEqual(identity_mod.age_years(0, 365 * 1440), 1)
        self.assertEqual(identity_mod.age_years(480, 480 + 40 * 365 * 1440),
                         40)


class TestPopulationComposition(unittest.TestCase):
    def test_population_spans_world(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(path)
        sim = Simulation(path, seed="test-seed")
        stats = sim.generate_population(120)
        self.assertGreaterEqual(stats["people"], 100)
        self.assertEqual(set(stats["by_profession"].keys()),
                         set(sim.data.professions.keys()))
        self.assertGreater(stats["children"], 0)
        self.assertGreater(stats["elders"], 0)
        students = sim.store.row(
            "SELECT COUNT(*) AS n FROM agent_state"
            " WHERE schedule_template_id = 'student_day'")["n"]
        self.assertGreater(students, 0)
        # Genesis balances are ledger rows: reconciliation is exact.
        self.assertEqual(sim.store.ledger_sum_check(), [])
        sim.close()
        os.remove(path)


if __name__ == "__main__":
    unittest.main()
