"""Unit 05 — Needs: activity-driven satisfaction changes, meals,
social anchors, daily financial/healthcare components."""
import json
import unittest

from tools.sim import lost_items as li
from tools.sim import needs as needs_mod
from tools.sim.tests.common import (data, make_household, make_person,
                                    make_store, set_needs)


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


class TestFurnitureRestoreWiring(unittest.TestCase):
    """Queue 21 Unit EQ — the effective furniture tier scales the
    home restores (GDD-10 §5/§6): rest/sleep restores of home/sleep
    blocks follow the multiplier (F0 ×0.7, F1 ×1.0, F2 ×1.15,
    F3 ×1.3). A lost or broken bed measurably costs the household
    its rest until the favour completes or the repair lands."""

    def _furnished_head(self, store, d):
        head = make_person(store, age=35, first="Head")
        hid, pid = make_household(store, [head])
        li.seed_furniture_at_move_in(store, d, hid, pid, 480)
        return head, hid, pid

    def _piece(self, store, cid, ref):
        row = store.row("SELECT item_instance_id FROM inventory_items"
                        " WHERE owner_character_id = ? AND item_ref = ?",
                        (cid, ref))
        return row["item_instance_id"]

    def _set_condition(self, store, iid, value):
        row = store.row("SELECT state FROM inventory_items"
                        " WHERE item_instance_id = ?", (iid,))
        state = json.loads(row["state"])
        state["condition"] = value
        store.execute("UPDATE inventory_items SET state = ?"
                      " WHERE item_instance_id = ?", (json.dumps(state),
                                                      iid))

    def test_f1_home_restores_at_full_rate(self):
        store = make_store()
        d = data()
        head, _hid, _pid = self._furnished_head(store, d)
        self.assertEqual(li.furniture_restore_multiplier(store, d, head),
                         1.0)
        set_needs(store, head, rest=50, sleep=50)
        needs_mod.apply_activity(store, head, "sleep", "home", 1, 480,
                                 data=d)
        got = needs_mod.get_needs(store, head)
        self.assertEqual(got["rest"], 58)    # 50 + 8 * 1.0
        self.assertEqual(got["sleep"], 64)   # 50 + 14 * 1.0

    def test_broken_bed_drops_the_restore_rate(self):
        store = make_store()
        d = data()
        head, _hid, _pid = self._furnished_head(store, d)
        self._set_condition(store, self._piece(store, head, "bed"), 0)
        self.assertEqual(li.effective_furniture_tier(store, d, head),
                         "F0")
        self.assertEqual(li.furniture_restore_multiplier(store, d, head),
                         0.7)
        set_needs(store, head, rest=50, sleep=50)
        needs_mod.apply_activity(store, head, "sleep", "home", 1, 480,
                                 data=d)
        got = needs_mod.get_needs(store, head)
        self.assertEqual(got["rest"], 56)    # 50 + 8 * 0.7 = 55.6
        self.assertEqual(got["sleep"], 60)   # 50 + 14 * 0.7 = 59.8

    def test_lost_bed_drops_the_restore_rate(self):
        # The EI decision: a lost piece drops the tier the same way
        # a broken one does — and the restore rate follows.
        store = make_store()
        d = data()
        head, _hid, _pid = self._furnished_head(store, d)
        bed = self._piece(store, head, "bed")
        self.assertIsNotNone(li.record_loss(store, head, bed, 2000,
                                            "d1_midtown"))
        self.assertEqual(li.effective_furniture_tier(store, d, head),
                         "F0")
        set_needs(store, head, rest=50, sleep=50)
        needs_mod.apply_activity(store, head, "sleep", "home", 1, 480,
                                 data=d)
        self.assertEqual(needs_mod.get_needs(store, head)["rest"], 56)

    def test_repair_restores_the_rate(self):
        store = make_store()
        d = data()
        head, _hid, _pid = self._furnished_head(store, d)
        bed = self._piece(store, head, "bed")
        self._set_condition(store, bed, 0)
        set_needs(store, head, rest=50, sleep=50)
        needs_mod.apply_activity(store, head, "sleep", "home", 1, 480,
                                 data=d)
        self.assertEqual(needs_mod.get_needs(store, head)["rest"], 56)
        self.assertEqual(li.repair_furniture(store, bed), bed)
        set_needs(store, head, rest=50, sleep=50)
        needs_mod.apply_activity(store, head, "sleep", "home", 1, 480,
                                 data=d)
        self.assertEqual(needs_mod.get_needs(store, head)["rest"], 58)

    def test_home_block_restores_scale_and_drains_do_not(self):
        store = make_store()
        d = data()
        head, _hid, _pid = self._furnished_head(store, d)
        self._set_condition(store, self._piece(store, head, "bed"), 0)
        set_needs(store, head, rest=50, sleep=50, hunger=50)
        needs_mod.apply_activity(store, head, "home", "home", 2, 480,
                                 data=d)
        got = needs_mod.get_needs(store, head)
        self.assertEqual(got["rest"], 57)    # 50 + 5*2 * 0.7
        self.assertEqual(got["sleep"], 46)   # 50 - 2*2, drain unscaled
        self.assertEqual(got["hunger"], 58)  # 50 + 4*2, not a restore

    def test_sleep_block_drain_stays_unscaled(self):
        store = make_store()
        d = data()
        head, _hid, _pid = self._furnished_head(store, d)
        self._set_condition(store, self._piece(store, head, "bed"), 0)
        set_needs(store, head, hunger=80)
        needs_mod.apply_activity(store, head, "sleep", "home", 8, 480,
                                 data=d)
        self.assertEqual(needs_mod.get_needs(store, head)["hunger"], 48)

    def test_no_data_means_no_scaling(self):
        # Old callers (and old tests) pass no data: the exact old
        # behaviour, even in an F0 home.
        store = make_store()
        d = data()
        head, _hid, _pid = self._furnished_head(store, d)
        self._set_condition(store, self._piece(store, head, "bed"), 0)
        set_needs(store, head, rest=50)
        needs_mod.apply_activity(store, head, "sleep", "home", 1, 480)
        self.assertEqual(needs_mod.get_needs(store, head)["rest"], 58)

    def test_no_tier_means_no_scaling(self):
        # No tier stands (all three F0 pieces broken): the
        # multiplier is None and no scaling is applied — no fallback
        # rate is invented (EF's boundary, EQ §5 note).
        store = make_store()
        d = data()
        head, _hid, _pid = self._furnished_head(store, d)
        for ref in ("floor_mattress", "single_burner", "crate_table"):
            self._set_condition(store, self._piece(store, head, ref), 0)
        self.assertIsNone(li.effective_furniture_tier(store, d, head))
        self.assertIsNone(li.furniture_restore_multiplier(store, d,
                                                          head))
        set_needs(store, head, rest=50)
        needs_mod.apply_activity(store, head, "sleep", "home", 1, 480,
                                 data=d)
        self.assertEqual(needs_mod.get_needs(store, head)["rest"], 58)


if __name__ == "__main__":
    unittest.main()
