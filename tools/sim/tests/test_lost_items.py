"""Queue 15 Unit CY — Losing-event wiring (GDD-04 §3.3, Unit BX design).

Tests the record_loss contract and the three event wirings: each event
writes exactly the §3.3 row, and refuses when the owner holds no
eligible item. The configured rate defaults to 0 (silent); tests pass
an explicit rate of 1.0 to the event functions, or set the config
rate around a single end-to-end move and restore it.
"""
import json
import unittest

from tools.sim import households as hh
from tools.sim import lost_items as li
from tools.sim.tests.common import (data, make_household, make_person,
                                    make_store, rng)

GM = 480


def _item(store, owner, item_type="goods", item_ref="food_basket",
          state=None):
    iid = store.next_id("INV", "inventory_items", "item_instance_id")
    store.insert("inventory_items", item_instance_id=iid,
                 item_type=item_type, item_ref=item_ref,
                 owner_character_id=owner, location_property_id=None,
                 state=json.dumps(state or {}),
                 acquired_at_game_minutes=GM)
    return iid


def _trip(store, character_id, day_index=5, destination_zone="d1_market",
          mode="walk", segment_ids="[]", arrive_minute=600):
    tid = store.next_id("TR", "trips", "trip_id")
    store.insert("trips", trip_id=tid, character_id=character_id,
                 day_index=day_index, purpose="shopping",
                 origin_zone="d1_midtown",
                 destination_zone=destination_zone, mode=mode,
                 segment_ids=segment_ids, depart_minute=540,
                 arrive_minute=arrive_minute)
    return tid


def _stocked_store():
    """Two real, data-priced properties (copied from
    test_households._stocked_store): one pricey occupied unit, one
    vacant cheap unit."""
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


class TestTablesAndConfig(unittest.TestCase):
    def test_tables_exist(self):
        store = make_store()
        tables = {r["name"] for r in store.rows(
            "SELECT name FROM sqlite_master WHERE type = 'table'")}
        self.assertIn("inventory_items", tables)
        self.assertIn("lost_items", tables)

    def test_config_default_rate_is_zero(self):
        self.assertEqual(data().lost_items_config.get("loss_rate"), 0)
        self.assertEqual(li.loss_rate(data()), 0.0)

    def test_rate_clamps(self):
        class FakeData:
            lost_items_config = {"loss_rate": 2.5}
        self.assertEqual(li.loss_rate(FakeData()), 1.0)

        class FakeDataNeg:
            lost_items_config = {"loss_rate": -1}
        self.assertEqual(li.loss_rate(FakeDataNeg()), 0.0)


class TestRecordLoss(unittest.TestCase):
    def test_writes_exactly_the_section_row(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        iid = _item(store, owner, "goods", "food_basket",
                    {"quantity": 1.0, "unit": "adult_month"})
        lid = li.record_loss(store, owner, iid, 600, "d1_market",
                             "market")
        self.assertIsNotNone(lid)
        self.assertTrue(lid.startswith("LI"))
        row = store.row("SELECT * FROM lost_items WHERE lost_item_id = ?",
                        (lid,))
        self.assertEqual(row["owner_character_id"], owner)
        self.assertEqual(row["item_instance_id"], iid)
        self.assertEqual(row["lost_at_game_minutes"], 600)
        self.assertEqual(row["lost_zone"], "d1_market")
        self.assertEqual(row["lost_anchor"], "market")
        self.assertEqual(row["status"], "lost")
        self.assertIsNone(row["found_by_character_id"])
        self.assertIsNone(row["found_at_game_minutes"])
        self.assertIsNone(row["returned_at_game_minutes"])
        # The inventory row itself is untouched: the item still
        # exists; only its whereabouts are unknown (CX).
        self.assertIsNotNone(store.row(
            "SELECT * FROM inventory_items WHERE item_instance_id = ?",
            (iid,)))

    def test_refuses_unknown_item(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        self.assertIsNone(li.record_loss(store, owner, "INV999", 600,
                                         "d1_market"))

    def test_refuses_another_owners_item(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        other = make_person(store, age=28, first="Other")
        iid = _item(store, other)
        self.assertIsNone(li.record_loss(store, owner, iid, 600,
                                         "d1_market"))
        self.assertEqual(store.row("SELECT COUNT(*) AS n FROM lost_items")
                         ["n"], 0)

    def test_refuses_second_loss_while_standing(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        iid = _item(store, owner)
        first = li.record_loss(store, owner, iid, 600, "d1_market")
        self.assertIsNotNone(first)
        self.assertIsNone(li.record_loss(store, owner, iid, 700,
                                         "d1_midtown"))
        self.assertEqual(store.row("SELECT COUNT(*) AS n FROM lost_items")
                         ["n"], 1)

    def test_allows_reloss_after_return(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        iid = _item(store, owner)
        first = li.record_loss(store, owner, iid, 600, "d1_market")
        store.execute("UPDATE lost_items SET status = 'returned',"
                      " returned_at_game_minutes = 900"
                      " WHERE lost_item_id = ?", (first,))
        second = li.record_loss(store, owner, iid, 1000, "d1_riverfront")
        self.assertIsNotNone(second)
        self.assertNotEqual(first, second)

    def test_eligible_items_follow_event_priority(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        tool = _item(store, owner, "tool", "hammer")
        goods = _item(store, owner, "goods", "food_basket")
        doc = _item(store, owner, "document", "certificate")
        got = li.eligible_items(store, owner,
                                li.EVENT_TYPES["commute_incident"])
        # BX E1 order is goods, document, tool — not insertion order.
        self.assertEqual([r["item_instance_id"] for r in got],
                         [goods, doc, tool])
        self.assertEqual(li.eligible_items(store, owner, ("clothing",)),
                         [])


class TestCommuteIncident(unittest.TestCase):
    def test_writes_row_from_earliest_trip_on_segment(self):
        store = make_store()
        owner = make_person(store, age=30, first="Traveller")
        _item(store, owner, "goods", "food_basket")
        _trip(store, owner, day_index=5, destination_zone="d1_market",
              segment_ids=json.dumps(["seg_a"]))
        out = li.commute_incident_losses(store, data(), rng(), "INC1",
                                         "seg_a", 1, 2000, rate=1.0)
        self.assertEqual(len(out), 1)
        row = store.row("SELECT * FROM lost_items WHERE lost_item_id = ?",
                        (out[0],))
        self.assertEqual(row["owner_character_id"], owner)
        self.assertEqual(row["lost_zone"], "d1_market")
        self.assertEqual(row["lost_at_game_minutes"], 600)
        self.assertIsNone(row["lost_anchor"])

    def test_no_trip_on_segment_writes_nothing(self):
        store = make_store()
        owner = make_person(store, age=30, first="Traveller")
        _item(store, owner, "goods", "food_basket")
        _trip(store, owner, segment_ids=json.dumps(["seg_other"]))
        out = li.commute_incident_losses(store, data(), rng(), "INC1",
                                         "seg_a", 1, 2000, rate=1.0)
        self.assertEqual(out, [])

    def test_rate_zero_writes_nothing(self):
        store = make_store()
        owner = make_person(store, age=30, first="Traveller")
        _item(store, owner, "goods", "food_basket")
        _trip(store, owner, segment_ids=json.dumps(["seg_a"]))
        out = li.commute_incident_losses(store, data(), rng(), "INC1",
                                         "seg_a", 1, 2000, rate=0.0)
        self.assertEqual(out, [])

    def test_no_eligible_item_writes_nothing(self):
        store = make_store()
        owner = make_person(store, age=30, first="Traveller")
        _item(store, owner, "vehicle", "private_car")
        _trip(store, owner, segment_ids=json.dumps(["seg_a"]))
        out = li.commute_incident_losses(store, data(), rng(), "INC1",
                                         "seg_a", 1, 2000, rate=1.0)
        self.assertEqual(out, [])

    def test_one_loss_per_incident(self):
        store = make_store()
        a = make_person(store, age=30, first="First")
        b = make_person(store, age=32, first="Second")
        _item(store, a, "goods", "food_basket")
        _item(store, b, "goods", "fish")
        _trip(store, a, segment_ids=json.dumps(["seg_a"]))
        _trip(store, b, segment_ids=json.dumps(["seg_a"]))
        out = li.commute_incident_losses(store, data(), rng(), "INC1",
                                         "seg_a", 1, 2000, rate=1.0)
        self.assertEqual(len(out), 1)
        row = store.row("SELECT * FROM lost_items WHERE lost_item_id = ?",
                        (out[0],))
        # The earliest trip in trip_id order is the first traveller.
        self.assertEqual(row["owner_character_id"], a)


class TestStormMarket(unittest.TestCase):
    def _disaster(self, store, day=5, disaster_type="cyclone",
                  with_impact=True):
        did = store.next_id("DS", "disaster_events", "disaster_id")
        store.insert("disaster_events", disaster_id=did,
                     disaster_type=disaster_type, city_id="rupsha_city",
                     status="active", started_day=day, ends_day=day + 2,
                     created_at_game_minutes=GM)
        if with_impact:
            iid = store.next_id("DI", "disaster_impacts", "impact_id")
            store.insert("disaster_impacts", impact_id=iid,
                         disaster_id=did, kind="flooding",
                         ref_id="market", city_id="rupsha_city",
                         zone_id="d1_market", game_minutes=GM)
        return did

    def test_writes_row_with_market_anchor(self):
        store = make_store()
        owner = make_person(store, age=30, first="Shopper")
        _item(store, owner, "goods", "food_basket")
        did = self._disaster(store)
        _trip(store, owner, day_index=5, mode="walk")
        out = li.storm_market_losses(store, data(), rng(), did, 5, 2000,
                                     rate=1.0)
        self.assertEqual(len(out), 1)
        row = store.row("SELECT * FROM lost_items WHERE lost_item_id = ?",
                        (out[0],))
        self.assertEqual(row["lost_zone"], "d1_market")
        self.assertEqual(row["lost_anchor"], "market")

    def test_bus_trip_is_not_exposed(self):
        store = make_store()
        owner = make_person(store, age=30, first="Shopper")
        _item(store, owner, "goods", "food_basket")
        did = self._disaster(store)
        _trip(store, owner, day_index=5, mode="bus")
        out = li.storm_market_losses(store, data(), rng(), did, 5, 2000,
                                     rate=1.0)
        self.assertEqual(out, [])

    def test_no_market_impact_writes_nothing(self):
        store = make_store()
        owner = make_person(store, age=30, first="Shopper")
        _item(store, owner, "goods", "food_basket")
        did = self._disaster(store, with_impact=False)
        _trip(store, owner, day_index=5, mode="walk")
        out = li.storm_market_losses(store, data(), rng(), did, 5, 2000,
                                     rate=1.0)
        self.assertEqual(out, [])

    def test_wrong_disaster_type_writes_nothing(self):
        store = make_store()
        owner = make_person(store, age=30, first="Shopper")
        _item(store, owner, "goods", "food_basket")
        did = self._disaster(store, disaster_type="heatwave")
        _trip(store, owner, day_index=5, mode="walk")
        out = li.storm_market_losses(store, data(), rng(), did, 5, 2000,
                                     rate=1.0)
        self.assertEqual(out, [])

    def test_one_loss_per_disaster_day(self):
        store = make_store()
        a = make_person(store, age=30, first="First")
        b = make_person(store, age=32, first="Second")
        _item(store, a, "goods", "food_basket")
        _item(store, b, "goods", "fish")
        did = self._disaster(store)
        _trip(store, a, day_index=5, mode="walk")
        _trip(store, b, day_index=5, mode="rickshaw")
        out = li.storm_market_losses(store, data(), rng(), did, 5, 2000,
                                     rate=1.0)
        self.assertEqual(len(out), 1)
        # A second call for the same (disaster, day) finds the item
        # already lost and writes nothing more.
        out2 = li.storm_market_losses(store, data(), rng(), did, 5, 2000,
                                      rate=1.0)
        self.assertEqual(out2, [])


class TestMoveHouse(unittest.TestCase):
    def _household(self, store):
        head = make_person(store, age=35, first="Head")
        hid, _ = make_household(store, [head])
        return head, hid

    def test_writes_row_in_origin_zone(self):
        store = make_store()
        head, hid = self._household(store)
        _item(store, head, "clothing", "shirt_basic")
        out = li.move_house_loss(store, data(), rng(), hid, "d1_midtown",
                                 2000, rate=1.0)
        self.assertEqual(len(out), 1)
        row = store.row("SELECT * FROM lost_items WHERE lost_item_id = ?",
                        (out[0],))
        self.assertEqual(row["owner_character_id"], head)
        self.assertEqual(row["lost_zone"], "d1_midtown")
        self.assertEqual(row["lost_at_game_minutes"], 2000)
        self.assertIsNone(row["lost_anchor"])

    def test_no_eligible_item_writes_nothing(self):
        store = make_store()
        head, hid = self._household(store)
        _item(store, head, "vehicle", "private_car")
        out = li.move_house_loss(store, data(), rng(), hid, "d1_midtown",
                                 2000, rate=1.0)
        self.assertEqual(out, [])

    def test_end_to_end_move_loses_at_config_rate(self):
        store, d, ids = _stocked_store()
        head = make_person(store, age=35, first="Mover")
        hid = store.next_id("HH", "households", "household_id")
        pricey = store.row("SELECT * FROM properties WHERE property_id = ?",
                           (ids["pricey"],))
        store.insert("households", household_id=hid, name="Movers",
                     home_property_id=ids["pricey"],
                     district_id=pricey["district_id"],
                     created_at_game_minutes=GM)
        store.insert("household_members", household_id=hid,
                     character_id=head, role="head",
                     joined_at_game_minutes=GM)
        store.execute("UPDATE characters SET household_id = ?"
                      " WHERE character_id = ?", (hid, head))
        store.execute("UPDATE properties SET status = 'rented'"
                      " WHERE property_id = ?", (ids["pricey"],))
        tid = store.next_id("TN", "tenancies", "tenancy_id")
        store.insert("tenancies", tenancy_id=tid,
                     property_id=ids["pricey"], tenant_household_id=hid,
                     rent_per_month=12000, started_at_game_minutes=GM)
        _item(store, head, "goods", "food_basket")
        cfg = d.lost_items_config
        old = cfg.get("loss_rate")
        try:
            cfg["loss_rate"] = 1.0
            new_rent = hh.move_household(store, d, hid, ids["cheap"],
                                         2000)
        finally:
            cfg["loss_rate"] = old
        self.assertEqual(new_rent, 2500)
        rows = store.rows("SELECT * FROM lost_items")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["owner_character_id"], head)
        self.assertEqual(rows[0]["lost_zone"],
                         pricey["district_id"])
        # And with the default rate 0 the same move loses nothing.
        self.assertEqual(li.loss_rate(d), 0.0)


class TestSeeding(unittest.TestCase):
    def test_seed_vehicle_row(self):
        store = make_store()
        owner = make_person(store, age=30, first="Driver")
        iid = li.seed_vehicle_row(store, owner, "VH1", "private_car",
                                  GM, 92.0, 40.0)
        row = store.row("SELECT * FROM inventory_items"
                        " WHERE item_instance_id = ?", (iid,))
        self.assertEqual(row["item_type"], "vehicle")
        self.assertEqual(row["item_ref"], "private_car")
        self.assertEqual(row["owner_character_id"], owner)
        state = json.loads(row["state"])
        self.assertEqual(state["vehicle_id"], "VH1")
        self.assertEqual(state["condition"], 92.0)

    def test_seed_goods_rows(self):
        store = make_store()
        head = make_person(store, age=35, first="Head")
        hid, _ = make_household(store, [head])
        made = li.seed_goods_rows(store, data(), hid, head,
                                  {"food_basket": 1.5, "fish": 0.0,
                                   "clothing_set": 0.25}, GM)
        self.assertEqual(len(made), 2)  # zero-quantity fish gets no row
        refs = {r["item_ref"] for r in store.rows(
            "SELECT * FROM inventory_items")}
        self.assertEqual(refs, {"food_basket", "clothing_set"})
        food = store.row("SELECT * FROM inventory_items WHERE"
                         " item_ref = 'food_basket'")
        self.assertEqual(json.loads(food["state"])["quantity"], 1.5)
        self.assertEqual(json.loads(food["state"])["unit"], "adult_month")


if __name__ == "__main__":
    unittest.main()
