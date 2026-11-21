"""Unit 08 — Decision-Making: utility choices that change real
world state, the decision audit log, and personality-differentiated
behaviour (same situation, different personality -> different
choice)."""
import unittest

from tools.sim.tests.common import (data, employ, make_household,
                                    make_person, make_store, rng,
                                    set_needs, set_profile)
from tools.sim import decisions as dec
from tools.sim import relationships as rel


def _char(store, cid):
    return store.row("SELECT * FROM characters WHERE character_id = ?",
                     (cid,))


class TestDecisions(unittest.TestCase):
    def test_seek_employment_changes_world(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=30)
        make_household(store, [cid])
        set_needs(store, cid, financial=10, social=90, sleep=90, rest=90,
                  safety=90, development=90, education=90)
        set_profile(store, cid, ambition=60)
        result = dec.decide(store, d, rng(), _char(store, cid), 0, 480, set())
        self.assertEqual(result, "seek_employment")
        emp = store.row("SELECT * FROM employments WHERE character_id = ?",
                        (cid,))
        self.assertIsNotNone(emp)
        log = store.row("SELECT * FROM decision_log WHERE character_id = ?",
                        (cid,))
        self.assertEqual(log["decision_type"], "seek_employment")

    def test_promotion_when_skill_ready(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=35)
        make_household(store, [cid])
        employ(store, d, cid, "teacher", tier=1)
        dec.add_skill_xp(store, cid, "teaching", 40 * 50)  # level 40 >= 30
        set_needs(store, cid, financial=80, social=90, sleep=90, rest=90,
                  safety=90, development=90, education=90)
        result = dec.decide(store, d, rng(), _char(store, cid), 0, 480, set())
        self.assertEqual(result, "promotion")
        emp = store.row("SELECT * FROM employments WHERE character_id = ?",
                        (cid,))
        self.assertEqual(emp["tier"], 2)
        self.assertEqual(emp["wage_per_month"], d.wage_at("teacher", 2))

    def test_buy_home_changes_property_and_ledger(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=40)
        hid, pid = make_household(store, [cid], market_value=500000)
        employ(store, d, cid, "doctor", tier=5)
        store.execute("UPDATE employments SET tier = 5 WHERE character_id"
                      " = ?", (cid,))
        store.transfer("SYS-EMPLOYERS", cid, 2000000, "seed", 480)
        set_profile(store, cid, ambition=30, risk_tolerance=30)
        set_needs(store, cid, financial=95, social=95, sleep=95, rest=95,
                  safety=95, development=95, education=95)
        result = dec.decide(store, d, rng(), _char(store, cid), 0, 480, set())
        self.assertEqual(result, "buy_home")
        prop = store.row("SELECT * FROM properties WHERE property_id = ?",
                         (pid,))
        self.assertEqual(prop["status"], "owned")
        self.assertEqual(prop["owner_household_id"], hid)
        ten = store.row("SELECT ended_at_game_minutes FROM tenancies"
                        " WHERE property_id = ?", (pid,))
        self.assertIsNotNone(ten["ended_at_game_minutes"])
        self.assertEqual(store.balance(cid), 2000000 - 500000)
        self.assertEqual(store.ledger_sum_check(), [])

    def test_rest_decision_sets_rest_day(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=30)
        make_household(store, [cid])
        employ(store, d, cid, "chef", tier=5)  # top tier: no promotion due
        dec.add_skill_xp(store, cid, "cooking", 90 * 50)
        set_needs(store, cid, financial=90, social=90, sleep=10, rest=10,
                  safety=90, development=90, education=90)
        result = dec.decide(store, d, rng(), _char(store, cid), 0, 480, set())
        self.assertEqual(result, "rest")
        state = store.row("SELECT rest_day FROM agent_state"
                          " WHERE character_id = ?", (cid,))
        self.assertEqual(state["rest_day"], 1)

    def test_personality_changes_choice(self):
        """Behavioural differentiation: two agents in the identical
        situation (employed, below promotion threshold, socially
        deprived) choose differently because ambition differs — the
        ambitious one trains, the unambitious one socialises."""
        outcomes = {}
        for label, ambition in (("driven", 95), ("easygoing", 15)):
            store = make_store()
            d = data()
            cid = make_person(store, age=30, first=label)
            friend = make_person(store, age=30, first="Pal")
            make_household(store, [cid])
            employ(store, d, cid, "teacher", tier=1)
            rel.add_edge(store, cid, friend, "friend", 480, affection=40)
            set_profile(store, cid, ambition=ambition)
            set_needs(store, cid, financial=90, social=30, sleep=90,
                      rest=90, safety=90, development=70, education=70)
            outcomes[label] = dec.decide(store, d, rng(), _char(store, cid),
                                         0, 480, set())
        self.assertEqual(outcomes["driven"], "train")
        self.assertEqual(outcomes["easygoing"], "socialise")


if __name__ == "__main__":
    unittest.main()
