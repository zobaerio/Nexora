"""Unit 05 — Needs: activity-driven satisfaction changes, meals,
social anchors, daily financial/healthcare components."""
import unittest

from tools.sim.tests.common import make_person, make_store, set_needs
from tools.sim import needs as needs_mod


class TestNeeds(unittest.TestCase):
    def test_sleep_restores_sleep_costs_hunger(self):
        store = make_store()
        cid = make_person(store)
        set_needs(store, cid, sleep=40, hunger=80)
        needs_mod.apply_activity(store, cid, "sleep", "home", 8, 480)
        got = needs_mod.get_needs(store, cid)
        self.assertEqual(got["sleep"], 100)   # 40 + 14*8, clamped
        self.assertEqual(got["hunger"], 48)   # 80 - 4*8

    def test_social_anchor_feeds_social_more(self):
        store = make_store()
        a = make_person(store, first="A")
        b = make_person(store, first="B")
        set_needs(store, a, social=50)
        set_needs(store, b, social=50)
        needs_mod.apply_activity(store, a, "leisure", "tea_stall", 2, 480)
        needs_mod.apply_activity(store, b, "leisure", "park", 2, 480)
        self.assertGreater(needs_mod.get_needs(store, a)["social"],
                           needs_mod.get_needs(store, b)["social"])

    def test_meal_bonus(self):
        store = make_store()
        cid = make_person(store)
        set_needs(store, cid, hunger=30, thirst=30)
        needs_mod.apply_activity(store, cid, "home", "home", 0, 480,
                                 meal=True)
        got = needs_mod.get_needs(store, cid)
        self.assertEqual(got["hunger"], 52)
        self.assertEqual(got["thirst"], 46)

    def test_daily_financial_from_balance(self):
        store = make_store()
        broke = make_person(store, first="Broke")
        rich = make_person(store, first="Rich")
        for cid, balance in ((broke, 0), (rich, 90000)):
            needs_mod.daily_update(store, cid, age=30, home_tier=3,
                                   balance=balance,
                                   monthly_cost_estimate=9000,
                                   studied_today=True, storm_today=False,
                                   game_minutes=1440)
        self.assertEqual(needs_mod.get_needs(store, broke)["financial"], 15)
        self.assertGreater(needs_mod.get_needs(store, rich)["financial"],
                           90)


if __name__ == "__main__":
    unittest.main()
