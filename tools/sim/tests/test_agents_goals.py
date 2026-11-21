"""Session 09 — Extended personal goals.

Derivation from measured state, progress from real records,
completion by record, abandonment past deadline, the monthly
step action (a real bank deposit), priority adaptation as
bounded learning — and the headline proof: a family memory of a
business failure, retrieved during derivation, changes the
derived goal's priority (retrieval changing a decision).
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))

from tools.sim import agents as agents_mod  # noqa: E402
from tools.sim import identity as identity_mod  # noqa: E402
from tools.sim.tests.common import (data, employ, make_household,  # noqa: E402
                                    make_person, make_store, rng,
                                    set_profile)

GM = 480
MONTH = 30 * 1440


def _fund(store, cid, amount):
    store.transfer("SYS-MARKET", cid, amount, "seed_grant", GM,
                   note="test funds", transfer_key=f"fund:{cid}")


class TestGoals(unittest.TestCase):
    def setUp(self):
        self.store = make_store()
        self.data = data()
        self.r = rng()
        agents_mod.setup_agents(self.store, self.data, GM)

    def tearDown(self):
        self.store.close()

    def _person(self, age=30, first="Goal"):
        return make_person(self.store, age=age, first=first,
                           game_minutes=GM, r=self.r)

    def test_employment_goal_derived_then_completed_by_record(self):
        cid = self._person()
        make_household(self.store, [cid], game_minutes=GM)
        out = agents_mod.goals_pass(self.store, self.data, self.r,
                                    1, GM + MONTH)
        self.assertGreaterEqual(out["derived"], 1)
        goal = self.store.row(
            "SELECT * FROM character_goals WHERE character_id = ?"
            " AND goal_type = 'find_employment'", (cid,))
        self.assertIsNotNone(goal)
        self.assertEqual(goal["goal_kind"], "agent")
        self.assertEqual(goal["priority"], 80)
        self.assertTrue(goal["deadline_game_minutes"])
        feas = json.loads(goal["feasibility"])
        self.assertEqual(feas["required"], {"status": "employed"})
        self.assertTrue(goal["completion_rule"])
        # The citizen gets a job; the next pass completes the goal
        # from the employment record itself.
        employ(self.store, self.data, cid, "chef", game_minutes=GM)
        agents_mod.goals_pass(self.store, self.data, self.r, 2,
                              GM + 2 * MONTH)
        goal = self.store.row(
            "SELECT * FROM character_goals WHERE goal_id = ?",
            (goal["goal_id"],))
        self.assertEqual(goal["status"], "completed")
        self.assertEqual(goal["progress"], 1.0)
        logs = self.store.rows(
            "SELECT * FROM goal_progress_log WHERE goal_id = ?",
            (goal["goal_id"],))
        self.assertTrue(any(l["progress"] == 1.0 for l in logs))

    def test_savings_goal_step_is_a_real_deposit(self):
        cid = self._person()
        make_household(self.store, [cid], game_minutes=GM)
        employ(self.store, self.data, cid, "teacher",
               game_minutes=GM)
        wage = self.data.wage_at("teacher", 1)
        _fund(self.store, cid, wage * 2)
        self.store.set_world(economy_setup=1)
        self.store.insert(
            "bank_accounts", account_id="BA-GOAL",
            character_id=cid, account_type="savings",
            balance_cached=0, opened_at_game_minutes=GM)
        self.store.commit()
        agents_mod.goals_pass(self.store, self.data, self.r, 1,
                              GM + MONTH)
        goal = self.store.row(
            "SELECT * FROM character_goals WHERE character_id = ?"
            " AND goal_type = 'save_amount' AND goal_kind ="
            " 'agent'", (cid,))
        self.assertIsNotNone(goal)
        acct = self.store.row("SELECT * FROM bank_accounts WHERE"
                              " character_id = ?", (cid,))
        self.assertGreater(acct["balance_cached"], 0)
        steps = self.store.rows(
            "SELECT * FROM agent_actions WHERE action_kind ="
            " 'goal_step' AND status = 'success'")
        self.assertTrue(steps)
        logged = self.store.rows(
            "SELECT * FROM decision_log WHERE decision_type ="
            " 'goal_step' AND character_id = ?", (cid,))
        self.assertTrue(logged)

    def test_goal_step_failure_is_recorded_without_account(self):
        cid = self._person()
        make_household(self.store, [cid], game_minutes=GM)
        employ(self.store, self.data, cid, "teacher",
               game_minutes=GM)
        wage = self.data.wage_at("teacher", 1)
        _fund(self.store, cid, wage * 2)
        self.store.set_world(economy_setup=1)
        self.store.commit()
        agents_mod.goals_pass(self.store, self.data, self.r, 1,
                              GM + MONTH)
        failed = self.store.rows(
            "SELECT * FROM agent_actions WHERE action_kind ="
            " 'goal_step' AND status = 'failed'")
        self.assertTrue(failed)
        self.assertEqual(json.loads(failed[0]["details"])["reason"],
                         "no_bank_account")

    def test_stalled_goal_is_abandoned_after_deadline(self):
        cid = self._person()
        make_household(self.store, [cid], game_minutes=GM)
        gid = identity_mod.add_goal(self.store, cid, "agent",
                                    "save_amount", {"amount": 99999},
                                    GM)
        self.store.execute(
            "UPDATE character_goals SET deadline_game_minutes = ?"
            " WHERE goal_id = ?", (GM + 100, gid))
        agents_mod.goals_pass(self.store, self.data, self.r, 5,
                              GM + 5 * MONTH)
        goal = self.store.row("SELECT * FROM character_goals WHERE"
                              " goal_id = ?", (gid,))
        self.assertEqual(goal["status"], "abandoned")

    def test_family_memory_of_failure_cuts_business_goal_priority(
            self):
        # Two identical citizens in separate households; only one's
        # household carries a family memory of a business closure.
        cids = {}
        for label in ("plain", "scarred"):
            cid = self._person(first=label)
            hid, _pid = make_household(self.store, [cid],
                                       game_minutes=GM)
            set_profile(self.store, cid, ambition=80,
                        risk_tolerance=60)
            employ(self.store, self.data, cid, "chef",
                   game_minutes=GM)
            _fund(self.store, cid, 60000)
            cids[label] = (cid, hid)
        scarred_hid = cids["scarred"][1]
        agents_mod.record_agent_memory(
            self.store, "family", scarred_hid, "business_closed",
            {"ref": "BE-TEST-1", "business_id": "BZ-GONE"}, 70, GM)
        self.store.commit()
        agents_mod.goals_pass(self.store, self.data, self.r, 1,
                              GM + MONTH)
        goals = {}
        for label, (cid, _hid) in cids.items():
            g = self.store.row(
                "SELECT * FROM character_goals WHERE character_id"
                " = ? AND goal_type = 'open_business'", (cid,))
            self.assertIsNotNone(g, label)
            goals[label] = g
        self.assertEqual(goals["plain"]["priority"], 60)
        self.assertEqual(goals["scarred"]["priority"], 30)
        feas = json.loads(goals["scarred"]["feasibility"])
        self.assertIn("household_business_failure_memory",
                      feas["risks"])
        self.assertFalse(feas["feasible"])
        # The retrieval itself was counted.
        mem = self.store.row(
            "SELECT * FROM agent_memories WHERE level = 'family'"
            " AND owner_ref = ?", (scarred_hid,))
        self.assertGreaterEqual(mem["access_count"], 1)


if __name__ == "__main__":
    unittest.main()
