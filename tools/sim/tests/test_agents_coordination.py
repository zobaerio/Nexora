"""Session 09 — Emergency coordination over Session 08's
disaster response: the task sequence is derived from the real
impacts, completion is proven by Session 08's own response
records, overdue tasks escalate by message, and tasks unmet at
recovery close as recorded failures with a review — never
silently dropped.
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))

from tools.sim import agents as agents_mod  # noqa: E402
from tools.sim.tests.common import (data, make_store)  # noqa: E402

GM = 480
DAY = 1440


class TestCoordination(unittest.TestCase):
    def setUp(self):
        self.store = make_store()
        self.data = data()
        self.store.insert(
            "countries", country_id="CT-CO", name="Coordland",
            capital_city_id=None, currency_code="NCr",
            created_at_game_minutes=GM)
        self.store.insert(
            "disaster_events", disaster_id="DS-1",
            disaster_type="flood", city_id="rupsha_city",
            intensity=2.0, status="active", started_day=0,
            damage_estimate_ncr=5000, created_at_game_minutes=GM)
        self.store.insert(
            "disaster_impacts", impact_id="DI-1", disaster_id="DS-1",
            kind="household_displaced", ref_id="HH-1",
            city_id="rupsha_city", game_minutes=GM)
        self.store.insert(
            "disaster_impacts", impact_id="DI-2", disaster_id="DS-1",
            kind="building_damage", ref_id="B-1",
            city_id="rupsha_city", damage=3000, game_minutes=GM)
        self.store.insert(
            "disaster_responses", response_id="DR-1",
            disaster_id="DS-1", action="relief_payment",
            ref_id="HH-1", amount_ncr=1000, game_minutes=GM)
        self.store.commit()

    def tearDown(self):
        self.store.close()

    def _tasks(self):
        return {t["kind"]: t for t in self.store.rows(
            "SELECT * FROM coordination_tasks WHERE disaster_id ="
            " 'DS-1'")}

    def test_sequence_derived_and_evidence_completes(self):
        agents_mod.coordination_pass(self.store, self.data, GM)
        tasks = self._tasks()
        self.assertEqual(tasks["assess"]["status"], "done")
        self.assertEqual(tasks["relief"]["status"], "done")
        self.assertEqual(tasks["evacuate"]["status"], "pending")
        self.assertEqual(tasks["shelter"]["status"], "pending")
        self.assertEqual(tasks["repair"]["status"], "pending")
        self.assertNotIn("medical", tasks)  # no injury impacts
        # Session 08 records the remaining responses.
        for i, action in enumerate(
                ("evacuation_trip", "shelter_assignment",
                 "repair_payment")):
            self.store.insert(
                "disaster_responses", response_id=f"DR-X{i}",
                disaster_id="DS-1", action=action, ref_id="HH-1",
                amount_ncr=500, game_minutes=GM + DAY)
        self.store.commit()
        agents_mod.coordination_pass(self.store, self.data,
                                     GM + DAY)
        tasks = self._tasks()
        self.assertTrue(all(t["status"] == "done"
                            for t in tasks.values()))

    def test_overdue_task_escalates_to_government(self):
        agents_mod.coordination_pass(self.store, self.data, GM)
        out = agents_mod.coordination_pass(self.store, self.data,
                                           GM + 8 * DAY)
        self.assertGreaterEqual(out["escalated"], 1)
        shelter = self._tasks()["shelter"]
        self.assertEqual(shelter["attempts"], 1)
        self.assertTrue(json.loads(shelter["details"])["escalated"])
        msgs = self.store.rows(
            "SELECT * FROM agent_messages WHERE kind ="
            " 'escalation'")
        self.assertTrue(msgs)
        self.assertEqual(msgs[0]["to_ref"],
                         agents_mod.agent_id("government", "CT-CO"))

    def test_unmet_tasks_close_with_failure_and_review(self):
        agents_mod.coordination_pass(self.store, self.data, GM)
        self.store.execute(
            "UPDATE disaster_events SET status = 'recovered',"
            " recovered_at_game_minutes = ? WHERE disaster_id ="
            " 'DS-1'", (GM + 2 * DAY,))
        self.store.commit()
        out = agents_mod.coordination_pass(self.store, self.data,
                                           GM + 2 * DAY)
        self.assertGreaterEqual(out["closed_unmet"], 1)
        self.assertEqual(out["reviews"], 1)
        tasks = self._tasks()
        self.assertEqual(tasks["repair"]["status"], "closed_unmet")
        review = tasks["review"]
        self.assertEqual(review["status"], "done")
        unmet = json.loads(review["details"])["unmet_tasks"]
        self.assertIn("repair", unmet)
        self.assertIn("shelter", unmet)
        failed = self.store.rows(
            "SELECT * FROM agent_actions WHERE status = 'failed'"
            " AND action_kind LIKE 'coordination_%'")
        self.assertTrue(failed)


if __name__ == "__main__":
    unittest.main()
