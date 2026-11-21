"""Session 02 Unit 02 — Household Management: composition, living
conditions, leaving home and relocation through life events only."""
import unittest

from tools.sim.tests.common import (data, employ, make_household,
                                    make_person, make_store)
from tools.sim import households as hh
from tools.sim import relationships as rel


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


if __name__ == "__main__":
    unittest.main()
