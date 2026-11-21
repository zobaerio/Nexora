"""Session 09 — Government/city assessment loop, closed:
measured indicator -> identified problem -> funded action linked
-> same indicator re-measured and evaluated. Covers roads
(Session 05 policy link), pollution (recommendation message to
the government agent) and disaster recovery (coordination link).
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))

from tools.sim import agents as agents_mod  # noqa: E402
from tools.sim.engine import Simulation  # noqa: E402

MONTH = 30 * 1440


def _tmp_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


class AssessmentWorld(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = _tmp_path()
        cls.sim = Simulation(cls.path, seed="s09-assessments")
        cls.sim.generate_population(40)
        cls.store = cls.sim.store
        cls.data = cls.sim.data
        cls.gm = cls.store.world()["game_minutes"]

    @classmethod
    def tearDownClass(cls):
        cls.sim.close()
        os.remove(cls.path)

    def _assessment(self, kind, scope="rupsha_city"):
        return self.store.row(
            "SELECT * FROM assessments WHERE scope = ? AND"
            " problem_kind = ? ORDER BY assessment_id DESC"
            " LIMIT 1", (scope, kind))

    def test_road_condition_closed_loop(self):
        gm = self.gm
        self.store.execute(
            "UPDATE road_segments SET condition = 30 WHERE city_id"
            " = 'rupsha_city'")
        self.store.commit()
        out = agents_mod.assessments_pass(self.store, self.data, 1,
                                          gm)
        self.assertGreaterEqual(out["identified"], 1)
        a = self._assessment("road_condition")
        self.assertIsNotNone(a)
        self.assertEqual(a["status"], "identified")
        self.assertAlmostEqual(a["baseline"], 30.0)
        # Session 05 funds the response.
        self.store.insert(
            "policies", policy_id="PL-ROAD", kind=
            "infrastructure_maintenance", title="Road repairs",
            city_id="rupsha_city", status="active",
            created_at_game_minutes=gm)
        self.store.commit()
        out = agents_mod.assessments_pass(self.store, self.data, 2,
                                          gm + MONTH)
        self.assertGreaterEqual(out["acted"], 1)
        a = self._assessment("road_condition")
        self.assertEqual(a["status"], "acted")
        self.assertEqual(a["action_kind"], "policy")
        self.assertEqual(a["action_ref"], "PL-ROAD")
        # The roads are actually repaired; evaluation re-measures.
        self.store.execute(
            "UPDATE road_segments SET condition = 90 WHERE city_id"
            " = 'rupsha_city'")
        self.store.commit()
        out = agents_mod.assessments_pass(self.store, self.data, 3,
                                          gm + 2 * MONTH)
        self.assertGreaterEqual(out["evaluated"], 1)
        a = self._assessment("road_condition")
        self.assertEqual(a["status"], "evaluated")
        ev = json.loads(a["evaluation"])
        self.assertTrue(ev["improved"])
        self.assertAlmostEqual(ev["current"], 90.0)

    def test_pollution_raises_recommendation_to_government(self):
        gm = self.gm
        self.store.insert(
            "env_pollution", city_id="rupsha_city", month_index=0,
            air_index=80.0, water_index=10.0, sources="{}",
            game_minutes=gm)
        self.store.commit()
        agents_mod.assessments_pass(self.store, self.data, 1, gm)
        a = self._assessment("pollution")
        self.assertIsNotNone(a)
        self.assertEqual(a["status"], "identified")
        msgs = self.store.rows(
            "SELECT * FROM agent_messages WHERE kind ="
            " 'recommendation'")
        self.assertTrue(msgs)
        country = self.store.row("SELECT country_id FROM countries"
                                 " LIMIT 1")
        self.assertEqual(
            msgs[0]["to_ref"],
            agents_mod.agent_id("government",
                                country["country_id"]))

    def test_disaster_recovery_links_coordination(self):
        gm = self.gm
        self.store.insert(
            "disaster_events", disaster_id="DS-AS",
            disaster_type="flood", city_id="rupsha_city",
            intensity=1.0, status="responding", started_day=0,
            damage_estimate_ncr=10000, relief_paid_ncr=0,
            repair_spent_ncr=0, created_at_game_minutes=gm)
        self.store.insert(
            "disaster_impacts", impact_id="DI-AS",
            disaster_id="DS-AS", kind="building_damage",
            ref_id="B-9", city_id="rupsha_city", damage=8000,
            game_minutes=gm)
        self.store.commit()
        agents_mod.coordination_pass(self.store, self.data, gm)
        agents_mod.assessments_pass(self.store, self.data, 1, gm)
        a = self._assessment("disaster_recovery")
        self.assertIsNotNone(a)
        self.assertEqual(a["status"], "identified")
        self.assertAlmostEqual(a["baseline"], 10000.0)
        agents_mod.assessments_pass(self.store, self.data, 2,
                                    gm + MONTH)
        a = self._assessment("disaster_recovery")
        self.assertEqual(a["status"], "acted")
        self.assertEqual(a["action_kind"], "coordination")
        # Recovery completes and the money is recorded as spent.
        self.store.execute(
            "UPDATE disaster_events SET status = 'recovered',"
            " relief_paid_ncr = 4000, repair_spent_ncr = 6000,"
            " recovered_at_game_minutes = ? WHERE disaster_id ="
            " 'DS-AS'", (gm + MONTH,))
        self.store.commit()
        agents_mod.assessments_pass(self.store, self.data, 3,
                                    gm + 2 * MONTH)
        a = self._assessment("disaster_recovery")
        self.assertEqual(a["status"], "evaluated")
        self.assertTrue(json.loads(a["evaluation"])["improved"])


if __name__ == "__main__":
    unittest.main()
