"""Session 02 Unit 02 — Household Management: composition, living
conditions, leaving home and relocation through life events only."""
import json
import os
import tempfile
import unittest

from tools.sim.tests.common import (data, employ, make_household,
                                    make_person, make_store)
from tools.sim import households as hh
from tools.sim import lost_items as li
from tools.sim import relationships as rel


def _tmp_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


def _stocked_store():
    """A store with two real, data-priced properties: one occupied
    (rent 12000 tier-4 building) and one vacant cheap unit."""
    store = make_store()
    d = data()
    stock = d.residential_stock()
    pricey = next(u for u in stock if u["rent"] == 12000)
    cheap = next(u for u in stock if u["rent"] == 2500)
    ids = {}
    for key, u in (("pricey", pricey), ("cheap", cheap)):
        pid = store.next_id("PR", "properties", "property_id")
        store.insert("properties", property_id=pid,
                     property_type=u["property_type"],
                     district_id=u["zone_id"],
                     address_label=u["building_name"], tier=u["tier"],
                     status="vacant", market_value=0,
                     building_ref=u["building_id"],
                     unit_index=u["unit_index"])
        ids[key] = pid
    return store, d, ids


class TestHouseholds(unittest.TestCase):
    def test_composition_and_conditions(self):
        store = make_store()
        a = make_person(store, age=40, first="Head")
        b = make_person(store, age=10, first="Kid")
        hid, _ = make_household(store, [a, b])
        comp = hh.composition(store, hid)
        self.assertEqual(len(comp), 2)
        self.assertEqual(comp[0]["role"], "head")
        cond = hh.living_conditions(store, data(), hid)
        self.assertEqual(cond["members"], 2)
        self.assertEqual(cond["rent"], 4000)

    def test_rent_resolution_from_data(self):
        store, d, ids = _stocked_store()
        prop = store.row("SELECT * FROM properties WHERE property_id = ?",
                         (ids["pricey"],))
        self.assertEqual(hh.rent_of_property(store, d, prop), 12000)
        # A fixture property with no data row cannot be priced.
        pid = store.next_id("PR", "properties", "property_id")
        store.insert("properties", property_id=pid,
                     property_type="apartment", district_id="d1_midtown",
                     address_label="Fixture", tier=3, status="vacant",
                     market_value=0, building_ref="no_such_building",
                     unit_index=0)
        prop2 = store.row("SELECT * FROM properties WHERE property_id = ?",
                          (pid,))
        self.assertIsNone(hh.rent_of_property(store, d, prop2))

    def test_leave_home_forms_new_household(self):
        store, d, ids = _stocked_store()
        parent = make_person(store, age=50, first="Parent")
        adult = make_person(store, age=24, first="Adult")
        hid, _ = make_household(store, [parent, adult])
        rel.add_edge(store, parent, adult, "parent", 480, both_ways=False)
        new_hid = hh.leave_home(store, d, adult, 1000)
        self.assertIsNotNone(new_hid)
        self.assertNotEqual(new_hid, hid)
        char = store.row("SELECT household_id FROM characters"
                         " WHERE character_id = ?", (adult,))
        self.assertEqual(char["household_id"], new_hid)
        role = store.row("SELECT role FROM household_members"
                         " WHERE household_id = ? AND character_id = ?",
                         (new_hid, adult))
        self.assertEqual(role["role"], "head")
        # The new tenancy's rent is the data price of the unit moved
        # into — resolved, never invented.
        new_home = hh.home_property(store, new_hid)
        ten = store.row("SELECT rent_per_month FROM tenancies"
                        " WHERE tenant_household_id = ?", (new_hid,))
        self.assertEqual(ten["rent_per_month"],
                         hh.rent_of_property(store, d, new_home))
        self.assertEqual(new_home["status"], "rented")
        ev = store.row("SELECT * FROM life_events WHERE character_id = ?"
                       " AND event_type = 'left_home'", (adult,))
        self.assertIsNotNone(ev)

    def test_leave_home_no_vacancy(self):
        store = make_store()
        parent = make_person(store, age=50, first="Parent")
        adult = make_person(store, age=24, first="Adult")
        make_household(store, [parent, adult])
        self.assertIsNone(hh.leave_home(store, data(), adult, 1000))

    def test_move_household_relocates(self):
        store, d, ids = _stocked_store()
        a = make_person(store, age=35, first="Mover")
        # A consistent fixture: household + tenancy both on the
        # pricey stocked unit at its data rent.
        hid = store.next_id("HH", "households", "household_id")
        pricey = store.row("SELECT * FROM properties"
                           " WHERE property_id = ?", (ids["pricey"],))
        store.insert("households", household_id=hid, name="Movers",
                     home_property_id=ids["pricey"],
                     district_id=pricey["district_id"],
                     created_at_game_minutes=480)
        store.insert("household_members", household_id=hid,
                     character_id=a, role="head",
                     joined_at_game_minutes=480)
        store.execute("UPDATE characters SET household_id = ?"
                      " WHERE character_id = ?", (hid, a))
        store.execute("UPDATE properties SET status = 'rented'"
                      " WHERE property_id = ?", (ids["pricey"],))
        tid = store.next_id("TN", "tenancies", "tenancy_id")
        store.insert("tenancies", tenancy_id=tid,
                     property_id=ids["pricey"], tenant_household_id=hid,
                     rent_per_month=12000, started_at_game_minutes=480)
        new_rent = hh.move_household(store, d, hid, ids["cheap"], 2000)
        self.assertEqual(new_rent, 2500)
        ten = store.row("SELECT rent_per_month FROM tenancies"
                        " WHERE tenant_household_id = ?"
                        " AND ended_at_game_minutes IS NULL", (hid,))
        self.assertEqual(ten["rent_per_month"], 2500)
        old = store.row("SELECT status FROM properties"
                        " WHERE property_id = ?", (ids["pricey"],))
        self.assertEqual(old["status"], "vacant")
        # Moving into an occupied/unpriceable unit is refused.
        self.assertIsNone(hh.move_household(store, d, hid,
                                            ids["cheap"], 3000))


class TestMonthlyFurniturePurchase(unittest.TestCase):
    """Queue 22 Unit EW — the home-loop purchase decision (GDD-10
    §5): one cheapest missing piece of the next tier per household
    per month, when the pool covers price + one month's rent."""

    GM = 480

    def _home(self, head_funds=100000, member_funds=0, seed=True):
        store = make_store()
        head = make_person(store, age=35, first="Head")
        member = make_person(store, age=30, first="Member")
        hid, pid = make_household(store, [head, member])
        store.transfer(None, head, head_funds, "seed", self.GM)
        if member_funds:
            store.transfer(None, member, member_funds, "seed", self.GM)
        if seed:
            li.seed_furniture_at_move_in(store, data(), hid, pid,
                                         self.GM)
        return store, head, member, hid, pid

    def _set_condition(self, store, iid, value):
        row = store.row("SELECT state FROM inventory_items"
                        " WHERE item_instance_id = ?", (iid,))
        state = json.loads(row["state"])
        state["condition"] = value
        store.execute("UPDATE inventory_items SET state = ?"
                      " WHERE item_instance_id = ?",
                      (json.dumps(state), iid))

    def test_rich_f1_household_buys_cheapest_f2_piece(self):
        store, head, _m, hid, _p = self._home()
        # Rent 4000 (the fixture tenancy); cheapest missing F2
        # piece is the curtains at 1,000.
        out = hh.monthly_furniture_purchase_sweep(store, data(), 5,
                                                  self.GM)
        self.assertEqual(out["purchased"], [(hid, "curtains", 1000)])
        self.assertEqual(store.balance(head), 99000)
        row = store.row(
            "SELECT * FROM inventory_items WHERE"
            " owner_character_id = ? AND item_ref = 'curtains'",
            (head,))
        self.assertIsNotNone(row)
        # One F2 piece alone does not raise the tier (GDD-10 §5).
        self.assertEqual(
            li.effective_furniture_tier(store, data(), head), "F1")

    def test_poor_household_buys_nothing(self):
        # 4,500 covers the 1,000 curtains but not the curtains plus
        # one month's rent (4,000): the rent reserve holds.
        store, head, _m, hid, _p = self._home(head_funds=4500)
        out = hh.monthly_furniture_purchase_sweep(store, data(), 5,
                                                  self.GM)
        self.assertEqual(out["purchased"], [])
        self.assertEqual(store.balance(head), 4500)
        self.assertEqual(store.rows(
            "SELECT * FROM economy_ledger WHERE reason_code ="
            " 'purchase'"), [])

    def test_head_payer_is_protected_by_the_reserve(self):
        # The head covers the price (1,500 > 1,000) but not price
        # + rent (5,000) — and the head is the event's payer, so
        # the sweep must NOT buy on the member's balance. Buying
        # here would spend the head's rent money.
        store, head, member, hid, _p = self._home(
            head_funds=1500, member_funds=100000)
        out = hh.monthly_furniture_purchase_sweep(store, data(), 5,
                                                  self.GM)
        self.assertEqual(out["purchased"], [])
        self.assertEqual(store.balance(head), 1500)
        self.assertEqual(store.balance(member), 100000)

    def test_exactly_enough_buys(self):
        # 5,000 is exactly price (1,000) + rent (4,000).
        store, head, _m, hid, _p = self._home(head_funds=5000)
        out = hh.monthly_furniture_purchase_sweep(store, data(), 5,
                                                  self.GM)
        self.assertEqual(out["purchased"], [(hid, "curtains", 1000)])
        self.assertEqual(store.balance(head), 4000)

    def test_richest_member_pays(self):
        # The head cannot cover the price (500 < 1,000), so the
        # event falls back to the richest member — the sweep
        # decides on the same payer, and the member pays.
        store, head, member, hid, _p = self._home(
            head_funds=500, member_funds=100000)
        out = hh.monthly_furniture_purchase_sweep(store, data(), 5,
                                                  self.GM)
        self.assertEqual(out["purchased"], [(hid, "curtains", 1000)])
        self.assertEqual(store.balance(head), 500)
        self.assertEqual(store.balance(member), 99000)

    def test_f3_household_buys_nothing(self):
        store, head, _m, hid, pid = self._home()
        li.seed_furniture_rows(store, data(), head,
                               li.furniture_tier_items(data(), "F3"),
                               "F3", pid, self.GM)
        self.assertEqual(
            li.effective_furniture_tier(store, data(), head), "F3")
        out = hh.monthly_furniture_purchase_sweep(store, data(), 5,
                                                  self.GM)
        self.assertEqual(out["purchased"], [])
        self.assertEqual(store.balance(head), 100000)

    def test_broken_f0_piece_is_replaced_free(self):
        store, head, _m, hid, pid = self._home()
        mattress = store.row(
            "SELECT item_instance_id FROM inventory_items WHERE"
            " owner_character_id = ? AND item_ref = 'floor_mattress'",
            (head,))["item_instance_id"]
        self._set_condition(store, mattress, 0)
        self.assertIsNone(
            li.effective_furniture_tier(store, data(), head))
        out = hh.monthly_furniture_purchase_sweep(store, data(), 5,
                                                  self.GM)
        self.assertEqual(out["purchased"],
                         [(hid, "floor_mattress", 0)])
        # An F0 piece costs 0: no money moves, no ledger row.
        self.assertEqual(store.balance(head), 100000)
        self.assertEqual(store.rows(
            "SELECT * FROM economy_ledger WHERE reason_code ="
            " 'purchase'"), [])
        # The replacement stands beside the broken original, so
        # the F0 set stands again — and with every F1 piece
        # standing, the tier is F1, not F0 (any standing row
        # counts).
        self.assertEqual(
            li.effective_furniture_tier(store, data(), head), "F1")

    def test_one_piece_per_month(self):
        store, head, _m, hid, _p = self._home()
        out = hh.monthly_furniture_purchase_sweep(store, data(), 5,
                                                  self.GM)
        self.assertEqual(out["purchased"], [(hid, "curtains", 1000)])
        # A second call in the same month buys nothing (the ledger
        # tag is the idempotency backstop).
        out = hh.monthly_furniture_purchase_sweep(store, data(), 5,
                                                  self.GM)
        self.assertEqual(out["purchased"], [])
        # Next month buys the next cheapest F2 piece (bookshelf,
        # 2,000 — the first 2,000 in catalogue order).
        out = hh.monthly_furniture_purchase_sweep(store, data(), 6,
                                                  self.GM + 1440)
        self.assertEqual(out["purchased"], [(hid, "bookshelf", 2000)])
        self.assertEqual(store.balance(head), 97000)


class TestMonthlyFurniturePurchaseHook(unittest.TestCase):
    """The engine's monthly social pass calls the purchase sweep:
    a rich F1 household in a live world holds a bought F2 piece
    after month end."""

    @classmethod
    def setUpClass(cls):
        from tools.sim.engine import Simulation
        cls.path = _tmp_path()
        cls.sim = Simulation(cls.path, seed="q22-ew")
        cls.sim.generate_population(60)
        cls.store = cls.sim.store
        cls.data = cls.sim.data

    @classmethod
    def tearDownClass(cls):
        cls.sim.close()
        os.remove(cls.path)

    def test_monthly_social_buys_an_f2_piece(self):
        head = self.store.row(
            "SELECT c.character_id FROM characters c JOIN"
            " household_members hm ON hm.character_id ="
            " c.character_id AND hm.role = 'head' JOIN households h"
            " ON h.household_id = hm.household_id WHERE"
            " c.is_system = 0 AND c.died_at_game_minutes IS NULL"
            " AND h.home_property_id IS NOT NULL LIMIT 1")
        if head is None:
            self.skipTest("no headed household with a home")
        cid = head["character_id"]
        self.store.transfer(None, cid, 100000, "seed", 500)
        self.sim._monthly_social(29)
        row = self.store.row(
            "SELECT * FROM inventory_items WHERE"
            " owner_character_id = ? AND item_ref = 'curtains'",
            (cid,))
        self.assertIsNotNone(row)


if __name__ == "__main__":
    unittest.main()
