"""Session 09 — Agent registry + permission governance.

The registry is a view over real actors (never duplicates), and
the capability model gates the coordination layer's own actions:
a citizen agent attempting a policy action is denied, the denial
is a recorded failed action, and a government agent succeeds.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))

from tools.sim import agents as agents_mod  # noqa: E402
from tools.sim.tests.common import (data, make_person,  # noqa: E402
                                    make_store, rng)

GM = 480


class TestRegistry(unittest.TestCase):
    def setUp(self):
        self.store = make_store()
        self.data = data()
        self.r = rng()
        self.cids = [make_person(self.store, age=30 + i,
                                 first=f"Reg{i}", game_minutes=GM,
                                 r=self.r) for i in range(3)]
        self.store.insert(
            "businesses", business_id="BZ-REG1", name="Reg Shop",
            business_type="shop", category="retail",
            owner_character_id=self.cids[0], status="active",
            founded_at_game_minutes=GM)
        self.store.insert(
            "countries", country_id="CT-REG", name="Testland",
            capital_city_id=None, currency_code="NCr",
            created_at_game_minutes=GM)
        self.store.commit()

    def tearDown(self):
        self.store.close()

    def test_setup_registers_real_actors_once(self):
        counts = agents_mod.setup_agents(self.store, self.data, GM)
        self.assertEqual(counts["citizen"], 3)
        self.assertEqual(counts["business"], 1)
        self.assertEqual(counts["government"], 1)
        rows = self.store.rows("SELECT * FROM agent_registry")
        self.assertEqual(len(rows), 5)
        # Registry ids are a deterministic function of the actor.
        self.assertIn(agents_mod.agent_id("citizen", self.cids[0]),
                      {r["agent_id"] for r in rows})
        # Idempotent: a second setup registers nothing new.
        agents_mod.setup_agents(self.store, self.data, GM)
        self.assertEqual(
            self.store.row("SELECT COUNT(*) AS n FROM"
                           " agent_registry")["n"], 5)

    def test_registry_status_follows_the_actor(self):
        agents_mod.setup_agents(self.store, self.data, GM)
        self.store.execute(
            "UPDATE characters SET died_at_game_minutes = ? WHERE"
            " character_id = ?", (GM + 100, self.cids[1]))
        agents_mod.sync_registry(self.store, self.data, GM + 200)
        row = self.store.row(
            "SELECT status FROM agent_registry WHERE agent_id = ?",
            (agents_mod.agent_id("citizen", self.cids[1]),))
        self.assertEqual(row["status"], "inactive")

    def test_capabilities_come_from_config(self):
        caps = agents_mod.class_capabilities(self.data, "government")
        self.assertIn("enact_policy", caps)
        self.assertNotIn(
            "enact_policy",
            agents_mod.class_capabilities(self.data, "citizen"))

    def test_permission_denial_is_recorded_and_raises(self):
        agents_mod.setup_agents(self.store, self.data, GM)
        with self.assertRaises(PermissionError):
            agents_mod.request_policy_action(
                self.store, self.data, "citizen", self.cids[0],
                "welfare_support", GM)
        failed = self.store.rows(
            "SELECT * FROM agent_actions WHERE status = 'failed'"
            " AND action_kind = 'policy_action'")
        self.assertEqual(len(failed), 1)
        import json
        self.assertEqual(json.loads(failed[0]["details"])["reason"],
                         "permission_denied")

    def test_government_policy_action_is_routed(self):
        agents_mod.setup_agents(self.store, self.data, GM)
        aid = agents_mod.request_policy_action(
            self.store, self.data, "government", "CT-REG",
            "welfare_support", GM)
        self.assertEqual(aid, agents_mod.agent_id("government",
                                                  "CT-REG"))
        msgs = self.store.rows(
            "SELECT * FROM agent_messages WHERE kind ="
            " 'policy_action_request'")
        self.assertEqual(len(msgs), 1)


if __name__ == "__main__":
    unittest.main()
