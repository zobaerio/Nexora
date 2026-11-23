"""Unit 09 — Life Cycle: stage bands, retirement at 65, and the
death cascade (inheritance order, equal shares, escheat, headship,
grief)."""
import json
import unittest

from tools.sim.tests.common import (employ, data, make_household,
                                    make_person, make_store, rng)
from tools.sim import lifecycle, relationships as rel


class TestStages(unittest.TestCase):
    def test_stage_bands(self):
        cases = {0: "Infant", 2: "Infant", 3: "Child", 12: "Child",
                 13: "Teen", 17: "Teen", 18: "Young Adult",
                 29: "Young Adult", 30: "Adult", 49: "Adult",
                 50: "Middle-Aged", 64: "Middle-Aged", 65: "Elder",
                 90: "Elder"}
        for age, stage in cases.items():
            self.assertEqual(lifecycle.stage_for_age(age), stage, age)


class TestDeathCascade(unittest.TestCase):
    def _couple(self, store, husband_balance=10000):
        h = make_person(store, first="Husband")
        w = make_person(store, first="Wife", sex="female")
        hid, pid = make_household(store, [h, w])
        rel.marry(store, h, w, 480)
        if husband_balance:
            store.transfer("SYS-EMPLOYERS", h, husband_balance, "seed", 480)
        return h, w, hid, pid

    def test_spouse_inherits_and_grieves(self):
        store = make_store()
        h, w, hid, pid = self._couple(store)
        employ(store, data(), h, "teacher")
        store.execute("UPDATE properties SET owner_character_id = ?"
                      " WHERE property_id = ?", (h, pid))
        heirs = lifecycle.die(store, h, 1000)
        self.assertEqual(heirs, [w])
        self.assertEqual(store.balance(w), 10000)
        self.assertEqual(store.balance(h), 0)
        emp = store.row("SELECT ended_at_game_minutes FROM employments"
                        " WHERE character_id = ?", (h,))
        self.assertIsNotNone(emp["ended_at_game_minutes"])
        grief = store.row("SELECT COUNT(*) AS n FROM character_memories"
                          " WHERE character_id = ? AND event_type ="
                          " 'death_of_family'", (w,))["n"]
        self.assertEqual(grief, 1)
        head = store.row("SELECT role FROM household_members"
                         " WHERE household_id = ? AND character_id = ?"
                         " AND left_at_game_minutes IS NULL", (hid, w))
        self.assertEqual(head["role"], "head")
        prop = store.row("SELECT owner_character_id FROM properties"
                         " WHERE property_id = ?", (pid,))
        self.assertEqual(prop["owner_character_id"], w)
        self.assertEqual(store.ledger_sum_check(), [])

    def test_children_share_equally_remainder_to_city(self):
        store = make_store()
        parent = make_person(store, first="Parent")
        c1 = make_person(store, first="Kid1", age=20)
        c2 = make_person(store, first="Kid2", age=22)
        make_household(store, [parent, c1, c2])
        rel.add_edge(store, parent, c1, "parent", 480, both_ways=False)
        rel.add_edge(store, parent, c2, "parent", 480, both_ways=False)
        store.transfer("SYS-EMPLOYERS", parent, 9001, "seed", 480)
        city_before = store.balance("SYS-CITY")
        heirs = lifecycle.die(store, parent, 1000)
        self.assertEqual(heirs, sorted([c1, c2]))
        self.assertEqual(store.balance(c1), 4500)
        self.assertEqual(store.balance(c2), 4500)
        self.assertEqual(store.balance("SYS-CITY"), city_before + 1)

    def test_escheat_when_no_heirs(self):
        store = make_store()
        loner = make_person(store, first="Loner")
        make_household(store, [loner])
        store.transfer("SYS-EMPLOYERS", loner, 5000, "seed", 480)
        city_before = store.balance("SYS-CITY")
        heirs = lifecycle.die(store, loner, 1000)
        self.assertEqual(heirs, [])
        self.assertEqual(store.balance("SYS-CITY"), city_before + 5000)
        hh = store.row("SELECT dissolved_at_game_minutes FROM households")
        self.assertIsNotNone(hh["dissolved_at_game_minutes"])


class TestRetirement(unittest.TestCase):
    def test_retirement_on_turning_65(self):
        store = make_store()
        # Born so that age is 64 at minute 480 and 65 a day later.
        born = 480 - (65 * 365 - 1) * 1440
        from tools.sim import identity as identity_mod
        cid = identity_mod.create_person(
            store, rng(), first_name="Old", last_name="Timer", sex="male",
            born_at_game_minutes=born, game_minutes=480)
        employ(store, data(), cid, "teacher")
        store.execute("UPDATE agent_state SET life_stage = 'Middle-Aged'"
                      " WHERE character_id = ?", (cid,))
        char = store.row("SELECT * FROM characters WHERE character_id = ?",
                         (cid,))
        lifecycle.daily_check(store, rng(), char, 1, 480 + 1440)
        emp = store.row("SELECT ended_at_game_minutes FROM employments"
                        " WHERE character_id = ?", (cid,))
        self.assertIsNotNone(emp["ended_at_game_minutes"])
        ev = store.row("SELECT COUNT(*) AS n FROM life_events"
                       " WHERE character_id = ? AND event_type ="
                       " 'retirement'", (cid,))["n"]
class TestAgeUpOutfits(unittest.TestCase):
    """Queue 17 Unit DK — starting outfits at the age-up to Young
    Adult (18) for characters born in-world (GDD-09 §3, Unit DD)."""

    def _teen(self, store, age=17):
        cid = make_person(store, age=age, first="Teen")
        store.execute("UPDATE agent_state SET life_stage = 'Teen'"
                      " WHERE character_id = ?", (cid,))
        return cid

    def _at_age(self, store, cid, age):
        char = store.row("SELECT * FROM characters"
                         " WHERE character_id = ?", (cid,))
        gm = char["born_at_game_minutes"] + age * 365 * 1440
        fresh = store.row("SELECT * FROM characters"
                          " WHERE character_id = ?", (cid,))
        return lifecycle.daily_check(store, rng(), fresh,
                                     gm // 1440, gm, data=data())

    def test_age_up_to_18_seeds_starting_outfits(self):
        store = make_store()
        cid = self._teen(store)
        self.assertIsNone(self._at_age(store, cid, 18))
        rows = store.rows("SELECT * FROM inventory_items WHERE"
                          " owner_character_id = ? AND"
                          " item_type = 'clothing'", (cid,))
        contexts = {json.loads(r["state"])["outfit_context"]
                    for r in rows}
        self.assertEqual(contexts, {"work", "casual", "formal"})
        # The work outfit is the default (no employment yet).
        work = [r for r in rows
                if json.loads(r["state"])["outfit_context"] == "work"]
        self.assertEqual({r["item_ref"] for r in work},
                         {"shirt_basic", "trousers_basic",
                          "shoes_leather"})

    def test_age_up_outfits_can_be_lost_via_record_loss(self):
        from tools.sim import lost_items as li
        store = make_store()
        cid = self._teen(store)
        self._at_age(store, cid, 18)
        row = store.row("SELECT * FROM inventory_items WHERE"
                        " owner_character_id = ?", (cid,))
        lid = li.record_loss(store, cid, row["item_instance_id"], 2000,
                             "d1_midtown")
        self.assertIsNotNone(lid)

    def test_no_seeding_before_18_or_twice(self):
        store = make_store()
        cid = self._teen(store)
        # Still 17: no transition, no outfits.
        self.assertIsNone(self._at_age(store, cid, 17))
        self.assertEqual(store.row("SELECT COUNT(*) AS n FROM"
                                   " inventory_items")["n"], 0)
        self._at_age(store, cid, 18)
        first = store.row("SELECT COUNT(*) AS n FROM"
                          " inventory_items")["n"]
        self.assertGreater(first, 0)
        # A later daily check (now Young Adult) seeds nothing more.
        self._at_age(store, cid, 19)
        self.assertEqual(store.row("SELECT COUNT(*) AS n FROM"
                                   " inventory_items")["n"], first)

    def test_school_uniform_does_not_block_age_up_outfits(self):
        from tools.sim import education as edu
        store = make_store()
        d = data()
        kid = make_person(store, age=8, first="Kid")
        edu.enrol_school_sweep(store, d, 480)
        self.assertEqual(store.row("SELECT COUNT(*) AS n FROM"
                                   " inventory_items")["n"], 1)
        store.execute("UPDATE agent_state SET life_stage = 'Teen'"
                      " WHERE character_id = ?", (kid,))
        self._at_age(store, kid, 18)
        rows = store.rows("SELECT * FROM inventory_items WHERE"
                          " owner_character_id = ?", (kid,))
        contexts = {json.loads(r["state"])["outfit_context"]
                    for r in rows}
        self.assertIn("school", contexts)
        self.assertEqual(contexts & {"work", "casual", "formal"},
                         {"work", "casual", "formal"})

    def test_age_up_without_data_seeds_nothing(self):
        store = make_store()
        cid = self._teen(store)
        char = store.row("SELECT * FROM characters"
                         " WHERE character_id = ?", (cid,))
        gm = char["born_at_game_minutes"] + 18 * 365 * 1440
        lifecycle.daily_check(store, rng(), char, gm // 1440, gm)
        self.assertEqual(store.row("SELECT COUNT(*) AS n FROM"
                                   " inventory_items")["n"], 0)


if __name__ == "__main__":
    unittest.main()
