"""Queue 15 Unit CY — Losing-event wiring (GDD-04 §3.3, Unit BX design).

Tests the record_loss contract and the three event wirings: each event
writes exactly the §3.3 row, and refuses when the owner holds no
eligible item. The configured rate defaults to 0 (silent); tests pass
an explicit rate of 1.0 to the event functions, or set the config
rate around a single end-to-end move and restore it.
"""
import json
import os
import tempfile
import unittest

from tools.sim import banking as banking_mod
from tools.sim import households as hh
from tools.sim import lost_items as li
from tools.sim.engine import Simulation
from tools.sim.tests.common import (data, make_household, make_person,
                                    make_store, rng)

GM = 480


def _tmp_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


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

    def test_refuses_loss_while_found(self):
        # Queue 19 Unit EA — DP's hand-back custody rule: a found
        # item is in the finder's hands and cannot be lost again
        # until it is returned.
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        finder = make_person(store, age=28, first="Finder")
        iid = _item(store, owner)
        lid = li.record_loss(store, owner, iid, 600, "d1_market",
                             "market")
        li.find_lost_item(store, lid, finder, 900, "d1_market",
                          "market")
        self.assertIsNone(li.record_loss(store, owner, iid, 1000,
                                         "d1_riverfront"))
        self.assertEqual(store.row("SELECT COUNT(*) AS n FROM lost_items")
                         ["n"], 1)

    def test_eligible_items_exclude_found_items(self):
        # Queue 19 Unit EA — the events' eligible sets exclude a
        # found item, so no event even considers it.
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        finder = make_person(store, age=28, first="Finder")
        goods = _item(store, owner, "goods", "food_basket")
        tool = _item(store, owner, "tool", "hammer")
        lid = li.record_loss(store, owner, goods, 600, "d1_market",
                             "market")
        li.find_lost_item(store, lid, finder, 900, "d1_market",
                          "market")
        got = li.eligible_items(store, owner,
                                li.EVENT_TYPES["commute_incident"])
        self.assertEqual([r["item_instance_id"] for r in got], [tool])

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

    def test_move_loss_writes_nothing_for_a_found_item(self):
        # Queue 19 Unit EA — a found item is in the finder's
        # custody: the move-house event cannot lose it again.
        store = make_store()
        head, hid = self._household(store)
        finder = make_person(store, age=28, first="Finder")
        iid = _item(store, head, "goods", "food_basket")
        lid = li.record_loss(store, head, iid, 600, "d1_market",
                             "market")
        li.find_lost_item(store, lid, finder, 900, "d1_market",
                          "market")
        out = li.move_house_loss(store, data(), rng(), hid, "d1_midtown",
                                 2000, rate=1.0)
        self.assertEqual(out, [])
        self.assertEqual(store.row("SELECT COUNT(*) AS n FROM lost_items")
                         ["n"], 1)

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


class TestClothingSeeding(unittest.TestCase):
    """Queue 16 Unit DD — clothing inventory seeding (GDD-09 §5,
    Unit CX record)."""

    def test_seed_clothing_rows_writes_one_row_per_garment(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        made = li.seed_clothing_rows(store, data(), owner,
                                     ["shirt_basic", "trousers_basic"],
                                     "casual", "creator", GM)
        self.assertEqual(len(made), 2)
        rows = store.rows("SELECT * FROM inventory_items WHERE"
                          " owner_character_id = ?"
                          " ORDER BY item_instance_id", (owner,))
        self.assertEqual([r["item_type"] for r in rows],
                         ["clothing", "clothing"])
        self.assertEqual([r["item_ref"] for r in rows],
                         ["shirt_basic", "trousers_basic"])
        states = [json.loads(r["state"]) for r in rows]
        self.assertEqual(states[0],
                         {"slot": "top", "outfit_context": "casual",
                          "issued": "creator"})
        self.assertEqual(states[1]["slot"], "bottom")
        self.assertEqual(rows[0]["acquired_at_game_minutes"], GM)

    def test_seed_clothing_rows_refuses_unknown_item(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        with self.assertRaises(ValueError):
            li.seed_clothing_rows(store, data(), owner,
                                  ["not_a_garment"], "casual",
                                  "creator", GM)
        self.assertEqual(store.row("SELECT COUNT(*) AS n FROM"
                                   " inventory_items")["n"], 0)

    def test_starting_outfits_construction_worker(self):
        out = li.starting_outfits(data(), "construction_worker", 1,
                                  "scheduled")
        self.assertEqual(out["work"],
                         {"items": ["ppe_set_construction"],
                          "issued": "employer"})
        self.assertEqual(out["casual"]["items"],
                         ["genji_vest", "lungi_cotton", "sandals"])
        self.assertEqual(out["casual"]["issued"], "creator")
        self.assertEqual(out["formal"]["items"],
                         ["shirt_formal", "trousers_formal",
                          "shoes_leather"])

    def test_starting_outfits_teacher_has_no_uniform(self):
        out = li.starting_outfits(data(), "teacher", 1, "scheduled")
        self.assertEqual(out["work"],
                         {"items": ["shirt_basic", "trousers_basic",
                                    "shoes_leather"],
                          "issued": "creator"})

    def test_pilot_uniform_is_never_issued(self):
        # GDD-09 §5: no airline operates in District 1 — the
        # uniform is catalogued, never issued or faked as worn.
        self.assertEqual(li.uniform_items(data(), "pilot", 1), [])
        out = li.starting_outfits(data(), "pilot", 1, "scheduled")
        self.assertNotIn("uniform_pilot", out["work"]["items"])
        self.assertEqual(out["work"]["issued"], "creator")

    def test_taxi_uniform_needs_tier_two(self):
        self.assertEqual(li.uniform_items(data(), "taxi_driver", 1),
                         [])
        self.assertEqual(li.uniform_items(data(), "taxi_driver", 2),
                         ["uniform_driver_depot"])

    def test_starting_outfits_ambient_is_empty(self):
        self.assertEqual(li.starting_outfits(data(), "chef", 1,
                                             "ambient"), {})

    def test_create_person_with_outfits_seeds_rows(self):
        store = make_store()
        outfits = li.starting_outfits(data(), "chef", 1, "scheduled")
        cid = make_person(store, age=30, first="Chef")
        # make_person does not pass outfits; seed through the
        # creator seam directly, as population.new_person does.
        from tools.sim import identity as identity_mod
        cid2 = identity_mod.create_person(
            store, rng(), first_name="Second", last_name="Chef",
            sex="male", born_at_game_minutes=480 - 30 * 365 * 1440,
            profession_id="chef", sim_tier="scheduled",
            game_minutes=GM, data=data(), outfits=outfits)
        rows = store.rows("SELECT * FROM inventory_items WHERE"
                          " owner_character_id = ?", (cid2,))
        refs = sorted(r["item_ref"] for r in rows)
        self.assertEqual(refs, sorted(["uniform_chef"] +
                                      ["genji_vest", "lungi_cotton",
                                       "sandals"] +
                                      ["shirt_formal",
                                       "trousers_formal",
                                       "shoes_leather"]))
        uniform = next(r for r in rows
                       if r["item_ref"] == "uniform_chef")
        self.assertEqual(json.loads(uniform["state"])["issued"],
                         "employer")
        self.assertEqual(json.loads(uniform["state"])["slot"],
                         "uniform_set")
        # And a person created without outfits holds nothing.
        self.assertEqual(store.rows(
            "SELECT * FROM inventory_items WHERE owner_character_id"
            " = ?", (cid,)), [])

    def test_seed_uniform_rows_skips_already_held(self):
        store = make_store()
        owner = make_person(store, age=30, first="Officer")
        first = li.seed_uniform_rows(store, data(), owner,
                                     "police_officer", 1, GM)
        self.assertEqual(len(first), 1)
        second = li.seed_uniform_rows(store, data(), owner,
                                      "police_officer", 1, GM)
        self.assertEqual(second, [])
        self.assertEqual(store.row("SELECT COUNT(*) AS n FROM"
                                   " inventory_items")["n"], 1)

    def test_seeded_clothing_can_be_lost_via_record_loss(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        made = li.seed_clothing_rows(store, data(), owner,
                                     ["shirt_basic"], "casual",
                                     "creator", GM)
        lid = li.record_loss(store, owner, made[0], 600, "d1_market")
        self.assertIsNotNone(lid)
        row = store.row("SELECT * FROM lost_items WHERE lost_item_id"
                        " = ?", (lid,))
        self.assertEqual(row["status"], "lost")
        self.assertEqual(row["item_instance_id"], made[0])

    def test_move_house_loses_seeded_clothing(self):
        store = make_store()
        head, hid = self._household(store)
        li.seed_clothing_rows(store, data(), head, ["shirt_basic"],
                              "casual", "creator", GM)
        out = li.move_house_loss(store, data(), rng(), hid,
                                 "d1_midtown", 2000, rate=1.0)
        self.assertEqual(len(out), 1)
        row = store.row("SELECT * FROM lost_items WHERE lost_item_id"
                        " = ?", (out[0],))
        item = store.row("SELECT * FROM inventory_items WHERE"
                         " item_instance_id = ?",
                         (row["item_instance_id"],))
        self.assertEqual(item["item_type"], "clothing")
        self.assertEqual(item["item_ref"], "shirt_basic")

    def _household(self, store):
        head = make_person(store, age=35, first="Head")
        hid, _ = make_household(store, [head])
        return head, hid

    def test_hiring_seeds_the_uniform(self):
        # The labour hire path: an unemployed adult + an open
        # business vacancy for a uniform profession.
        from tools.sim import labour as labour_mod
        store = make_store()
        d = data()
        candidate = make_person(store, age=30, first="Builder")
        vid = store.next_id("VC", "vacancies", "vacancy_id")
        store.insert("vacancies", vacancy_id=vid,
                     employer_kind="business",
                     employer_business_id=None,
                     profession_id="construction_worker",
                     city_id="rupsha_city", wage_per_month=20000,
                     status="open", posted_month=1,
                     created_at_game_minutes=GM)
        hires = labour_mod.match_vacancies(store, d, rng(), 1, GM)
        self.assertEqual(len(hires), 1)
        self.assertEqual(hires[0]["character_id"], candidate)
        self.assertEqual(hires[0]["profession_id"],
                         "construction_worker")
        rows = store.rows("SELECT * FROM inventory_items WHERE"
                          " owner_character_id = ? AND"
                          " item_type = 'clothing'", (candidate,))
        self.assertEqual([r["item_ref"] for r in rows],
                         ["ppe_set_construction"])
        self.assertEqual(json.loads(rows[0]["state"])["issued"],
                         "employer")


class TestRecovery(unittest.TestCase):
    """Queue 16 Unit DF — lost-item recovery wiring (GDD-04 §3.3
    lifecycle lost -> found -> returned)."""

    def _lost(self, store, owner, anchor="market", zone="d1_market"):
        iid = _item(store, owner, "goods", "food_basket",
                    {"quantity": 1.0, "unit": "adult_month"})
        lid = li.record_loss(store, owner, iid, 600, zone, anchor)
        return lid, iid

    def test_find_writes_found_with_finder_and_minute(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        finder = make_person(store, age=28, first="Finder")
        lid, _ = self._lost(store, owner)
        got = li.find_lost_item(store, lid, finder, 900, "d1_market",
                                "market")
        self.assertEqual(got, lid)
        row = store.row("SELECT * FROM lost_items WHERE lost_item_id"
                        " = ?", (lid,))
        self.assertEqual(row["status"], "found")
        self.assertEqual(row["found_by_character_id"], finder)
        self.assertEqual(row["found_at_game_minutes"], 900)
        self.assertIsNone(row["returned_at_game_minutes"])

    def test_find_refuses_wrong_zone(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        finder = make_person(store, age=28, first="Finder")
        lid, _ = self._lost(store, owner)
        self.assertIsNone(li.find_lost_item(store, lid, finder, 900,
                                            "d1_midtown", "market"))
        row = store.row("SELECT * FROM lost_items WHERE lost_item_id"
                        " = ?", (lid,))
        self.assertEqual(row["status"], "lost")
        self.assertIsNone(row["found_by_character_id"])

    def test_find_refuses_wrong_anchor(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        finder = make_person(store, age=28, first="Finder")
        lid, _ = self._lost(store, owner)
        self.assertIsNone(li.find_lost_item(store, lid, finder, 900,
                                            "d1_market", "tea_stall"))
        self.assertEqual(store.row(
            "SELECT status FROM lost_items WHERE lost_item_id = ?",
            (lid,))["status"], "lost")

    def test_find_without_anchor_needs_zone_only(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        finder = make_person(store, age=28, first="Finder")
        lid, _ = self._lost(store, owner, anchor=None)
        # No anchor was recorded (E1/E3): the zone alone is the
        # check, and no anchor need be supplied.
        got = li.find_lost_item(store, lid, finder, 900, "d1_market")
        self.assertEqual(got, lid)
        self.assertEqual(store.row(
            "SELECT status FROM lost_items WHERE lost_item_id = ?",
            (lid,))["status"], "found")

    def test_find_refuses_already_found(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        first = make_person(store, age=28, first="First")
        second = make_person(store, age=26, first="Second")
        lid, _ = self._lost(store, owner)
        li.find_lost_item(store, lid, first, 900, "d1_market",
                          "market")
        self.assertIsNone(li.find_lost_item(store, lid, second, 950,
                                            "d1_market", "market"))
        row = store.row("SELECT * FROM lost_items WHERE lost_item_id"
                        " = ?", (lid,))
        self.assertEqual(row["found_by_character_id"], first)
        self.assertEqual(row["found_at_game_minutes"], 900)

    def test_find_refuses_unknown_row(self):
        store = make_store()
        finder = make_person(store, age=28, first="Finder")
        self.assertIsNone(li.find_lost_item(store, "LI999", finder,
                                            900, "d1_market"))

    def test_return_writes_returned(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        finder = make_person(store, age=28, first="Finder")
        lid, iid = self._lost(store, owner)
        li.find_lost_item(store, lid, finder, 900, "d1_market",
                          "market")
        got = li.return_lost_item(store, lid, 1200)
        self.assertEqual(got, lid)
        row = store.row("SELECT * FROM lost_items WHERE lost_item_id"
                        " = ?", (lid,))
        self.assertEqual(row["status"], "returned")
        self.assertEqual(row["returned_at_game_minutes"], 1200)
        self.assertEqual(row["found_by_character_id"], finder)
        # The inventory row is untouched throughout the lifecycle.
        self.assertIsNotNone(store.row(
            "SELECT * FROM inventory_items WHERE item_instance_id = ?",
            (iid,)))

    def test_return_refuses_item_never_found(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        lid, _ = self._lost(store, owner)
        self.assertIsNone(li.return_lost_item(store, lid, 1200))
        self.assertEqual(store.row(
            "SELECT status FROM lost_items WHERE lost_item_id = ?",
            (lid,))["status"], "lost")

    def test_return_refuses_already_returned(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        finder = make_person(store, age=28, first="Finder")
        lid, _ = self._lost(store, owner)
        li.find_lost_item(store, lid, finder, 900, "d1_market",
                          "market")
        li.return_lost_item(store, lid, 1200)
        self.assertIsNone(li.return_lost_item(store, lid, 1300))
        self.assertEqual(store.row(
            "SELECT returned_at_game_minutes FROM lost_items"
            " WHERE lost_item_id = ?", (lid,))
            ["returned_at_game_minutes"], 1200)

    def test_return_refuses_unknown_row(self):
        store = make_store()
        self.assertIsNone(li.return_lost_item(store, "LI999", 1200))

    def test_full_lifecycle_then_reloss(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        finder = make_person(store, age=28, first="Finder")
        lid, iid = self._lost(store, owner)
        li.find_lost_item(store, lid, finder, 900, "d1_market",
                          "market")
        li.return_lost_item(store, lid, 1200)
        second = li.record_loss(store, owner, iid, 1500,
                                "d1_riverfront")
        self.assertIsNotNone(second)
        self.assertNotEqual(lid, second)

    def test_favour_objective_complete_predicate(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        finder = make_person(store, age=28, first="Finder")
        lid, _ = self._lost(store, owner)
        # Lost: not complete. Found: not complete. Returned:
        # complete — the §15.2 condition for the complete node.
        self.assertFalse(li.favour_objective_complete(store, lid))
        li.find_lost_item(store, lid, finder, 900, "d1_market",
                          "market")
        self.assertFalse(li.favour_objective_complete(store, lid))
        li.return_lost_item(store, lid, 1200)
        self.assertTrue(li.favour_objective_complete(store, lid))
        self.assertFalse(li.favour_objective_complete(store, "LI999"))


class TestFurnitureSeeding(unittest.TestCase):
    """Queue 17 Unit DJ — furniture seeding at move-in (GDD-10 §5)."""

    def test_tier_items_are_cumulative(self):
        d = data()
        self.assertEqual(li.furniture_tier_items(d, "F0"),
                         ["floor_mattress", "single_burner",
                          "crate_table"])
        self.assertEqual(li.furniture_tier_items(d, "F1"),
                         ["floor_mattress", "single_burner",
                          "crate_table", "bed", "table_chairs",
                          "stove", "wardrobe", "fan"])
        self.assertEqual(len(li.furniture_tier_items(d, "F3")), 18)
        self.assertEqual(li.furniture_tier_items(d, "F9"), [])

    def test_move_in_seeds_f1_for_a_bare_head(self):
        store = make_store()
        head = make_person(store, age=35, first="Head")
        hid, pid = make_household(store, [head])
        made = li.seed_furniture_at_move_in(store, data(), hid, pid, GM)
        self.assertEqual(len(made), 8)  # F0 + F1 pieces
        rows = store.rows("SELECT * FROM inventory_items WHERE"
                          " owner_character_id = ?"
                          " ORDER BY item_instance_id", (head,))
        self.assertTrue(all(r["item_type"] == "furniture" for r in rows))
        self.assertEqual({r["item_ref"] for r in rows},
                         set(li.furniture_tier_items(data(), "F1")))
        self.assertTrue(all(r["location_property_id"] == pid
                            for r in rows))
        self.assertEqual(json.loads(rows[0]["state"]),
                         {"furniture_tier": "F1", "condition": 100})

    def test_move_in_never_reseeds_a_furnished_head(self):
        store = make_store()
        head = make_person(store, age=35, first="Head")
        hid, pid = make_household(store, [head])
        li.seed_furniture_at_move_in(store, data(), hid, pid, GM)
        again = li.seed_furniture_at_move_in(store, data(), hid, pid,
                                             GM + 1000)
        self.assertEqual(again, [])
        self.assertEqual(store.row("SELECT COUNT(*) AS n FROM"
                                   " inventory_items")["n"], 8)

    def test_furniture_can_be_lost_via_record_loss(self):
        store = make_store()
        head = make_person(store, age=35, first="Head")
        hid, pid = make_household(store, [head])
        made = li.seed_furniture_at_move_in(store, data(), hid, pid, GM)
        lid = li.record_loss(store, head, made[0], 2000, "d1_midtown")
        self.assertIsNotNone(lid)
        row = store.row("SELECT * FROM lost_items WHERE lost_item_id = ?",
                        (lid,))
        self.assertEqual(row["status"], "lost")

    def test_move_household_furnishes_the_new_home(self):
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
        self.assertEqual(hh.move_household(store, d, hid, ids["cheap"],
                                           2000), 2500)
        rows = store.rows("SELECT * FROM inventory_items WHERE"
                          " owner_character_id = ? AND"
                          " item_type = 'furniture'", (head,))
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(r["location_property_id"] == ids["cheap"]
                            for r in rows))

    def test_seed_furniture_rows_refuses_unknown_item(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        with self.assertRaises(ValueError):
            li.seed_furniture_rows(store, data(), owner,
                                   ["not_a_piece"], "F1", None, GM)


class TestToolSeeding(unittest.TestCase):
    """Queue 17 Unit DJ — tool seeding at hiring (data/tools.json)."""

    def test_tool_items_follow_the_catalogue_mapping(self):
        d = data()
        self.assertEqual(
            li.tool_items(d, "construction_worker"),
            ["hammer", "handsaw", "measuring_tape", "trowel",
             "spirit_level", "wrench_set", "screwdriver_set",
             "toolbox", "paint_brush_set"])
        self.assertEqual(li.tool_items(d, "chef"),
                         ["kitchen_knife_set"])
        self.assertEqual(li.tool_items(d, "teacher"), [])
        self.assertEqual(li.tool_items(d, None), [])

    def test_seed_tool_rows_issues_the_trade_instruments(self):
        store = make_store()
        worker = make_person(store, age=30, first="Worker")
        made = li.seed_tool_rows(store, data(), worker,
                                "construction_worker", GM)
        self.assertEqual(len(made), 9)
        rows = store.rows("SELECT * FROM inventory_items WHERE"
                          " owner_character_id = ?", (worker,))
        self.assertTrue(all(r["item_type"] == "tool" for r in rows))
        self.assertEqual(json.loads(rows[0]["state"]),
                         {"issued": "employer", "condition": 100})

    def test_seed_tool_rows_skips_already_held_tools(self):
        store = make_store()
        worker = make_person(store, age=30, first="Worker")
        li.seed_tool_rows(store, data(), worker, "construction_worker",
                         GM)
        again = li.seed_tool_rows(store, data(), worker,
                                  "construction_worker", GM + 1000)
        self.assertEqual(again, [])
        self.assertEqual(store.row("SELECT COUNT(*) AS n FROM"
                                   " inventory_items")["n"], 9)

    def test_tool_can_be_lost_via_record_loss(self):
        store = make_store()
        worker = make_person(store, age=30, first="Worker")
        made = li.seed_tool_rows(store, data(), worker,
                                "taxi_driver", GM)
        self.assertEqual(len(made), 3)  # wrench, screwdriver, toolbox
        lid = li.record_loss(store, worker, made[0], 2000, "d1_market")
        self.assertIsNotNone(lid)


class TestDocumentSeeding(unittest.TestCase):
    """Queue 17 Unit DJ — document rows at the issuing events."""

    def test_seed_document_row_writes_the_paper(self):
        store = make_store()
        owner = make_person(store, age=40, first="Owner")
        iid = li.seed_document_row(store, data(), owner,
                                   "business_licence", GM,
                                   {"business_id": "BZ1"})
        row = store.row("SELECT * FROM inventory_items"
                        " WHERE item_instance_id = ?", (iid,))
        self.assertEqual(row["item_type"], "document")
        self.assertEqual(row["item_ref"], "business_licence")
        self.assertEqual(json.loads(row["state"]),
                         {"business_id": "BZ1"})

    def test_seed_document_row_refuses_the_same_record_twice(self):
        store = make_store()
        owner = make_person(store, age=40, first="Owner")
        first = li.seed_document_row(store, data(), owner,
                                     "business_licence", GM,
                                     {"business_id": "BZ1"})
        second = li.seed_document_row(store, data(), owner,
                                      "business_licence", GM + 100,
                                      {"business_id": "BZ1"})
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        # A different issuing record is a different document.
        third = li.seed_document_row(store, data(), owner,
                                     "business_licence", GM + 200,
                                     {"business_id": "BZ2"})
        self.assertIsNotNone(third)

    def test_seed_document_row_refuses_unknown_document(self):
        store = make_store()
        owner = make_person(store, age=40, first="Owner")
        with self.assertRaises(ValueError):
            li.seed_document_row(store, data(), owner,
                                 "not_a_document", GM)

    def test_document_can_be_lost_and_found_and_returned(self):
        store = make_store()
        owner = make_person(store, age=40, first="Owner")
        iid = li.seed_document_row(store, data(), owner,
                                   "property_deed", GM,
                                   {"property_id": "PR1"})
        lid = li.record_loss(store, owner, iid, 2000, "d1_midtown")
        self.assertIsNotNone(lid)
        self.assertIsNone(li.return_lost_item(store, lid, 2100))
        self.assertEqual(
            li.find_lost_item(store, lid, owner, 2100, "d1_midtown"),
            lid)
        self.assertEqual(li.return_lost_item(store, lid, 2200), lid)
        self.assertTrue(li.favour_objective_complete(store, lid))

    def test_register_business_issues_a_licence_to_a_real_owner(self):
        from tools.sim import business as biz
        store = make_store()
        owner = make_person(store, age=40, first="Owner")
        bid = biz.register_business(
            store, name="Owner Shop", business_type="shop_owner",
            category="retail", owner_character_id=owner,
            property_id=None, game_minutes=GM,
            founded_by="owner_profession", data=data())
        rows = store.rows("SELECT * FROM inventory_items WHERE"
                          " owner_character_id = ? AND"
                          " item_type = 'document'", (owner,))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["item_ref"], "business_licence")
        self.assertEqual(json.loads(rows[0]["state"]),
                         {"business_id": bid})

    def test_system_founded_firm_gets_no_licence_row(self):
        # SYS-MARKET is not a character and holds no inventory.
        from tools.sim import business as biz
        store = make_store()
        biz.register_business(
            store, name="System Firm", business_type="system_firm",
            category="retail", owner_character_id="SYS-MARKET",
            property_id=None, game_minutes=GM, founded_by="system",
            data=data())
        self.assertEqual(store.row("SELECT COUNT(*) AS n FROM"
                                   " inventory_items")["n"], 0)


class TestDeedLifecycle(unittest.TestCase):
    """Queue 21 Unit ER — foreclosure-to-repurchase deed lifecycle
    (GDD-04 §3.3, GDD-10 §8): a foreclosure surrenders the deed
    the borrower still holds, so a re-purchase is issued a fresh
    deed; a deed already lost/found is not surrendered and remains
    the deed of record."""

    def _deeded_owner(self, store, d):
        cid = make_person(store, age=40, first="Owner")
        hid, pid = make_household(store, [cid])
        # A real stock unit, so rent_of_property resolves and the
        # foreclosure writes the bank tenancy (a synthetic "test"
        # building_ref prices to None and the tenancy branch skips).
        unit = next(u for u in d.residential_stock()
                    if u["rent"] == 2500)
        store.execute("UPDATE properties SET building_ref = ?,"
                      " unit_index = ? WHERE property_id = ?",
                      (unit["building_id"], unit["unit_index"], pid))
        # The pre-foreclosure state is an owner-occupier with a
        # mortgage: the purchase closures set the ownership, and
        # _foreclose reads owner_household_id for the tenancy.
        store.execute("UPDATE properties SET owner_household_id = ?,"
                      " owner_character_id = ?, status = 'owned'"
                      " WHERE property_id = ?", (hid, cid, pid))
        deed = li.seed_document_row(store, d, cid, "property_deed",
                                    GM, {"property_id": pid})
        return cid, hid, pid, deed

    def _mortgage(self, store, cid, pid):
        store.insert("loans", loan_id="LN-TEST-ER",
                     borrower_character_id=cid, kind="mortgage",
                     principal_ncr=400000, outstanding_ncr=400000,
                     annual_rate_percent=9.0, term_months=240,
                     months_elapsed=0, interest_paid_ncr=0,
                     missed_payments=3, status="defaulted",
                     property_id=pid, started_at_game_minutes=GM,
                     updated_at_game_minutes=GM)
        return store.row("SELECT * FROM loans WHERE loan_id = ?",
                         ("LN-TEST-ER",))

    def _deed_row(self, store, cid, pid):
        return store.row(
            "SELECT * FROM inventory_items WHERE"
            " owner_character_id = ? AND item_type = 'document'"
            " AND item_ref = 'property_deed'", (cid,))

    def test_foreclosure_surrenders_the_held_deed(self):
        store = make_store()
        d = data()
        cid, hid, pid, deed = self._deeded_owner(store, d)
        loan = self._mortgage(store, cid, pid)
        banking_mod._foreclose(store, loan, GM)
        # The paper follows the right: the deed row is gone.
        self.assertIsNone(self._deed_row(store, cid, pid))
        prop = store.row("SELECT * FROM properties WHERE property_id"
                         " = ?", (pid,))
        self.assertEqual(prop["owner_character_id"], "SYS-BANK")
        self.assertIsNone(prop["owner_household_id"])
        self.assertEqual(prop["status"], "rented")
        # The household stays as the bank's tenant (pre-existing
        # foreclosure behaviour, unchanged by this unit).
        ten = store.row("SELECT * FROM tenancies WHERE property_id = ?"
                        " AND tenant_household_id = ? AND"
                        " landlord_character_id = 'SYS-BANK'",
                        (pid, hid))
        self.assertIsNotNone(ten)
        event = store.row("SELECT * FROM life_events WHERE"
                          " character_id = ? AND event_type ="
                          " 'foreclosure'", (cid,))
        self.assertIsNotNone(event)
        self.assertEqual(json.loads(event["details"])["property_id"],
                         pid)

    def test_repurchase_after_foreclosure_seeds_a_fresh_deed(self):
        store = make_store()
        d = data()
        cid, hid, pid, deed = self._deeded_owner(store, d)
        loan = self._mortgage(store, cid, pid)
        banking_mod._foreclose(store, loan, GM)
        # The same seed call the purchase closures make now writes
        # a fresh deed — the duplicate guard no longer blocks it.
        fresh = li.seed_document_row(store, d, cid, "property_deed",
                                     GM + 100, {"property_id": pid})
        self.assertIsNotNone(fresh)
        self.assertNotEqual(fresh, deed)
        row = store.row("SELECT * FROM inventory_items WHERE"
                        " item_instance_id = ?", (fresh,))
        self.assertEqual(json.loads(row["state"]),
                         {"property_id": pid})

    def test_foreclosure_leaves_a_lost_deed(self):
        store = make_store()
        d = data()
        cid, hid, pid, deed = self._deeded_owner(store, d)
        finder = make_person(store, age=28, first="Finder")
        lid = li.record_loss(store, cid, deed, 600, "d1_market",
                             "market")
        self.assertIsNotNone(lid)
        self.assertEqual(li.find_lost_item(store, lid, finder, 900,
                                           "d1_market", "market"), lid)
        loan = self._mortgage(store, cid, pid)
        banking_mod._foreclose(store, loan, GM)
        # The paper is in the finder's hands, not the borrower's —
        # it is not surrendered and stays the deed of record.
        self.assertIsNotNone(self._deed_row(store, cid, pid))
        # A re-purchase while it is lost is refused by the guard:
        # the owner still holds a deed for this property.
        self.assertIsNone(li.seed_document_row(
            store, d, cid, "property_deed", GM + 100,
            {"property_id": pid}))
        # When the paper comes back, it serves as the deed again.
        self.assertEqual(li.return_lost_item(store, lid, 1000), lid)
        self.assertIsNotNone(self._deed_row(store, cid, pid))

    def test_foreclosure_without_a_deed_is_a_noop_for_the_paper(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=40, first="Owner")
        hid, pid = make_household(store, [cid])
        loan = self._mortgage(store, cid, pid)
        banking_mod._foreclose(store, loan, GM)
        self.assertIsNone(self._deed_row(store, cid, pid))
        self.assertIsNone(li.surrender_property_deed(store, cid, pid))
        prop = store.row("SELECT * FROM properties WHERE property_id"
                         " = ?", (pid,))
        self.assertEqual(prop["owner_character_id"], "SYS-BANK")

    def test_surrender_returns_the_id_then_none(self):
        store = make_store()
        d = data()
        cid, hid, pid, deed = self._deeded_owner(store, d)
        self.assertEqual(li.surrender_property_deed(store, cid, pid),
                         deed)
        self.assertIsNone(self._deed_row(store, cid, pid))
        self.assertIsNone(li.surrender_property_deed(store, cid, pid))


class TestSchoolUniform(unittest.TestCase):
    """Queue 17 Unit DK — school uniform at enrolment (GDD-09 §5)."""

    def test_enrolment_issues_the_uniform(self):
        from tools.sim import education as edu
        store = make_store()
        d = data()
        kid = make_person(store, age=8, first="Kid")
        self.assertEqual(edu.enrol_school_sweep(store, d, 480), 1)
        rows = store.rows("SELECT * FROM inventory_items WHERE"
                          " owner_character_id = ? AND"
                          " item_type = 'clothing'", (kid,))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["item_ref"], "uniform_school")
        self.assertEqual(json.loads(rows[0]["state"]),
                         {"slot": "uniform_set",
                          "outfit_context": "school",
                          "issued": "household"})

    def test_uniform_can_be_lost_via_record_loss(self):
        from tools.sim import education as edu
        store = make_store()
        d = data()
        kid = make_person(store, age=8, first="Kid")
        edu.enrol_school_sweep(store, d, 480)
        row = store.row("SELECT * FROM inventory_items WHERE"
                        " owner_character_id = ?", (kid,))
        lid = li.record_loss(store, kid, row["item_instance_id"], 2000,
                             "d1_midtown")
        self.assertIsNotNone(lid)

    def test_re_enrolment_issues_no_second_uniform(self):
        from tools.sim import education as edu
        store = make_store()
        d = data()
        kid = make_person(store, age=8, first="Kid")
        edu.enrol_school_sweep(store, d, 480)
        # The sweep is idempotent, and so is the uniform issue.
        self.assertEqual(edu.enrol_school_sweep(store, d, 1000), 0)
        self.assertEqual(li.seed_school_uniform(store, d, kid, 1000),
                         [])
        self.assertEqual(store.row("SELECT COUNT(*) AS n FROM"
                                   " inventory_items")["n"], 1)

    def test_adult_enrolment_issues_no_uniform(self):
        from tools.sim import education as edu
        store = make_store()
        d = data()
        adult = make_person(store, age=30, first="Adult")
        self.assertEqual(edu.enrol_school_sweep(store, d, 480), 0)
        self.assertEqual(store.row("SELECT COUNT(*) AS n FROM"
                                   " inventory_items")["n"], 0)


class TestCurrentZoneAt(unittest.TestCase):
    """Queue 19 Unit ED — the GDD-15 §18 accessor, implemented for
    the hand-back fallback (the design added no sim function)."""

    def _day(self, store, cid, zones=((0, 600, "d1_midtown"),
                                      (600, 1440, "d1_civic"))):
        blocks = [{"start": s, "end": e, "activity": "home",
                   "location": "home", "zone": z}
                  for s, e, z in zones]
        store.execute(
            "INSERT INTO instantiated_schedules"
            " (character_id, day_index, blocks_json)"
            " VALUES (?, ?, ?)",
            (cid, 0, json.dumps(blocks)))

    def test_reads_the_block_containing_the_minute(self):
        store = make_store()
        cid = make_person(store, age=30, first="Walker")
        self._day(store, cid)
        self.assertEqual(li.current_zone_at(store, cid, 480),
                         "d1_midtown")
        self.assertEqual(li.current_zone_at(store, cid, 700),
                         "d1_civic")
        # The block boundary belongs to the block that starts there.
        self.assertEqual(li.current_zone_at(store, cid, 600),
                         "d1_civic")

    def test_none_without_a_stored_day(self):
        store = make_store()
        cid = make_person(store, age=30, first="Walker")
        self.assertIsNone(li.current_zone_at(store, cid, 480))
        # A stored day for another day is not this day's truth.
        self._day(store, cid)
        self.assertIsNone(li.current_zone_at(store, cid, 480 + 1440))


class TestHandBack(unittest.TestCase):
    """Queue 19 Unit ED — the DP hand-back, performed (GDD-04 §3.3)."""

    def _found(self, store, owner, finder, zone="d1_market",
               anchor="market"):
        iid = _item(store, owner, "goods", "food_basket",
                    {"quantity": 1.0, "unit": "adult_month"})
        lid = li.record_loss(store, owner, iid, 600, zone, anchor)
        li.find_lost_item(store, lid, finder, 900, zone, anchor)
        return lid, iid

    def _household(self, store, owner):
        hid, pid = make_household(store, [owner])
        return hid, pid

    def test_hand_back_at_the_current_home_succeeds(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        finder = make_person(store, age=28, first="Finder")
        _, pid = self._household(store, owner)
        lid, _ = self._found(store, owner, finder)
        got = li.hand_back_lost_item(store, lid, finder, 1200,
                                     finder_property_id=pid)
        self.assertEqual(got, lid)
        row = store.row("SELECT * FROM lost_items WHERE lost_item_id"
                        " = ?", (lid,))
        self.assertEqual(row["status"], "returned")
        self.assertEqual(row["returned_at_game_minutes"], 1200)
        self.assertTrue(li.favour_objective_complete(store, lid))

    def test_hand_back_refuses_the_wrong_property(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        finder = make_person(store, age=28, first="Finder")
        _, pid = self._household(store, owner)
        lid, _ = self._found(store, owner, finder)
        self.assertIsNone(li.hand_back_lost_item(
            store, lid, finder, 1200, finder_property_id="PR-OTHER"))
        self.assertEqual(store.row(
            "SELECT status FROM lost_items WHERE lost_item_id = ?",
            (lid,))["status"], "found")

    def test_moved_owner_re_routes_to_the_new_home(self):
        # DP: a move does not make the owner unreachable — the
        # hand-back goes to the CURRENT home, not the origin zone.
        store, d, ids = _stocked_store()
        owner = make_person(store, age=35, first="Mover")
        finder = make_person(store, age=28, first="Finder")
        hid = store.next_id("HH", "households", "household_id")
        pricey = store.row("SELECT * FROM properties WHERE property_id"
                           " = ?", (ids["pricey"],))
        store.insert("households", household_id=hid, name="Movers",
                     home_property_id=ids["pricey"],
                     district_id=pricey["district_id"],
                     created_at_game_minutes=GM)
        store.insert("household_members", household_id=hid,
                     character_id=owner, role="head",
                     joined_at_game_minutes=GM)
        store.execute("UPDATE characters SET household_id = ?"
                      " WHERE character_id = ?", (hid, owner))
        store.execute("UPDATE properties SET status = 'rented'"
                      " WHERE property_id = ?", (ids["pricey"],))
        tid = store.next_id("TN", "tenancies", "tenancy_id")
        store.insert("tenancies", tenancy_id=tid,
                     property_id=ids["pricey"], tenant_household_id=hid,
                     rent_per_month=12000, started_at_game_minutes=GM)
        lid, _ = self._found(store, owner, finder)
        self.assertEqual(hh.move_household(store, d, hid, ids["cheap"],
                                           2000), 2500)
        # The old home no longer works; the new one does.
        self.assertIsNone(li.hand_back_lost_item(
            store, lid, finder, 2500,
            finder_property_id=ids["pricey"]))
        self.assertEqual(li.hand_back_lost_item(
            store, lid, finder, 2500,
            finder_property_id=ids["cheap"]), lid)
        self.assertEqual(store.row(
            "SELECT status FROM lost_items WHERE lost_item_id = ?",
            (lid,))["status"], "returned")

    def test_no_tenancy_falls_back_to_the_current_zone(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        finder = make_person(store, age=28, first="Finder")
        # No household, no tenancy: the fallback is the owner's
        # current zone from the stored day.
        blocks = [{"start": 0, "end": 1440, "activity": "home",
                   "location": "home", "zone": "d1_midtown"}]
        store.execute(
            "INSERT INTO instantiated_schedules"
            " (character_id, day_index, blocks_json)"
            " VALUES (?, ?, ?)",
            (owner, 0, json.dumps(blocks)))
        lid, _ = self._found(store, owner, finder)
        self.assertIsNone(li.hand_back_lost_item(
            store, lid, finder, 1200, finder_zone="d1_civic"))
        self.assertEqual(li.hand_back_lost_item(
            store, lid, finder, 1200, finder_zone="d1_midtown"), lid)

    def test_no_tenancy_and_no_stored_day_refuses(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        finder = make_person(store, age=28, first="Finder")
        lid, _ = self._found(store, owner, finder)
        self.assertIsNone(li.hand_back_lost_item(
            store, lid, finder, 1200, finder_zone="d1_midtown"))
        self.assertEqual(store.row(
            "SELECT status FROM lost_items WHERE lost_item_id = ?",
            (lid,))["status"], "found")

    def test_deceased_owner_is_orphaned_not_re_routed(self):
        # DP: death is the genuinely unreachable case — no
        # hand-back to the heir (the cascade moves money +
        # property, never inventory).
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        finder = make_person(store, age=28, first="Finder")
        _, pid = self._household(store, owner)
        lid, _ = self._found(store, owner, finder)
        store.execute("UPDATE characters SET died_at_game_minutes = ?"
                      " WHERE character_id = ?", (1000, owner))
        self.assertIsNone(li.hand_back_lost_item(
            store, lid, finder, 1200, finder_property_id=pid))
        row = store.row("SELECT * FROM lost_items WHERE lost_item_id"
                        " = ?", (lid,))
        self.assertEqual(row["status"], "found")
        self.assertIsNone(row["returned_at_game_minutes"])

    def test_hand_back_refuses_a_finder_who_does_not_hold_it(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        finder = make_person(store, age=28, first="Finder")
        other = make_person(store, age=26, first="Other")
        _, pid = self._household(store, owner)
        lid, _ = self._found(store, owner, finder)
        self.assertIsNone(li.hand_back_lost_item(
            store, lid, other, 1200, finder_property_id=pid))
        self.assertEqual(store.row(
            "SELECT status FROM lost_items WHERE lost_item_id = ?",
            (lid,))["status"], "found")

    def test_hand_back_refuses_an_item_never_found(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        finder = make_person(store, age=28, first="Finder")
        _, pid = self._household(store, owner)
        iid = _item(store, owner)
        lid = li.record_loss(store, owner, iid, 600, "d1_market")
        self.assertIsNone(li.hand_back_lost_item(
            store, lid, finder, 1200, finder_property_id=pid))
        self.assertEqual(store.row(
            "SELECT status FROM lost_items WHERE lost_item_id = ?",
            (lid,))["status"], "lost")

    def test_hand_back_refuses_an_unknown_row(self):
        store = make_store()
        finder = make_person(store, age=28, first="Finder")
        self.assertIsNone(li.hand_back_lost_item(
            store, "LI999", finder, 1200, finder_property_id="PR1"))


class TestToolCondition(unittest.TestCase):
    """Queue 19 Unit EE — tool condition & decay wiring (GDD-04
    §3.3, Unit DQ design)."""

    def _employ(self, store, cid, profession_id):
        store.insert("employments", employment_id="EM-TEST-EE",
                     character_id=cid, profession_id=profession_id,
                     tier=1, wage_per_month=10000,
                     started_at_game_minutes=GM,
                     ended_at_game_minutes=None)

    def _condition(self, store, iid):
        row = store.row("SELECT state FROM inventory_items"
                        " WHERE item_instance_id = ?", (iid,))
        return json.loads(row["state"])["condition"]

    def _set_condition(self, store, iid, value):
        row = store.row("SELECT state FROM inventory_items"
                        " WHERE item_instance_id = ?", (iid,))
        state = json.loads(row["state"])
        state["condition"] = value
        store.execute("UPDATE inventory_items SET state = ?"
                      " WHERE item_instance_id = ?",
                      (json.dumps(state), iid))

    def _broken_count(self, store, cid):
        return store.row("SELECT COUNT(*) AS n FROM life_events"
                         " WHERE character_id = ?"
                         " AND event_type = 'tool_broken'",
                         (cid,))["n"]

    def test_seed_tool_rows_write_condition_100(self):
        store = make_store()
        worker = make_person(store, age=30, first="Worker")
        made = li.seed_tool_rows(store, data(), worker,
                                "construction_worker", GM)
        self.assertEqual(len(made), 9)
        self.assertTrue(all(self._condition(store, iid) == 100
                            for iid in made))

    def test_item_condition_defaults_to_100_for_legacy_rows(self):
        # Rows seeded before Queue 19 carry no `condition` key
        # (DJ wrote {"issued": "employer"}) — they read as new.
        store = make_store()
        worker = make_person(store, age=30, first="Worker")
        iid = _item(store, worker, "tool", "hammer",
                    {"issued": "employer"})
        row = store.row("SELECT * FROM inventory_items"
                        " WHERE item_instance_id = ?", (iid,))
        self.assertEqual(li.item_condition(row), 100)

    def test_apply_tool_wear_lowers_by_one_per_worked_day(self):
        store = make_store()
        d = data()
        worker = make_person(store, age=30, first="Worker")
        self._employ(store, worker, "construction_worker")
        made = li.seed_tool_rows(store, d, worker,
                                "construction_worker", GM)
        for _ in range(3):
            self.assertEqual(len(li.apply_tool_wear(store, d, worker,
                                                    GM)), 9)
        self.assertTrue(all(self._condition(store, iid) == 97
                            for iid in made))

    def test_wear_floors_at_zero_and_logs_one_event(self):
        store = make_store()
        d = data()
        worker = make_person(store, age=30, first="Worker")
        self._employ(store, worker, "construction_worker")
        made = li.seed_tool_rows(store, d, worker,
                                "construction_worker", GM)
        hammer = next(i for i in made
                      if store.row("SELECT item_ref FROM inventory_items"
                                   " WHERE item_instance_id = ?",
                                   (i,))["item_ref"] == "hammer")
        self._set_condition(store, hammer, 1)
        worn = li.apply_tool_wear(store, d, worker, GM)
        self.assertIn(hammer, worn)
        self.assertEqual(self._condition(store, hammer), 0)
        self.assertEqual(self._broken_count(store, worker), 1)
        event = store.row("SELECT * FROM life_events WHERE"
                          " character_id = ? AND"
                          " event_type = 'tool_broken'", (worker,))
        self.assertEqual(json.loads(event["details"])["item_ref"],
                         "hammer")
        # A second worked day wears the other tools again (one per
        # worked day each) but the broken hammer wears nothing
        # further and logs no second event: the break is one event,
        # not one per day.
        worn_again = li.apply_tool_wear(store, d, worker, GM)
        self.assertNotIn(hammer, worn_again)
        self.assertEqual(len(worn_again), 8)
        self.assertEqual(self._broken_count(store, worker), 1)

    def test_wear_skips_already_broken_tools(self):
        store = make_store()
        d = data()
        worker = make_person(store, age=30, first="Worker")
        self._employ(store, worker, "construction_worker")
        made = li.seed_tool_rows(store, d, worker,
                                "construction_worker", GM)
        for iid in made:
            self._set_condition(store, iid, 0)
        self.assertEqual(li.apply_tool_wear(store, d, worker, GM), [])
        self.assertEqual(self._broken_count(store, worker), 0)

    def test_broken_tools_for_lists_only_broken_tools(self):
        store = make_store()
        d = data()
        worker = make_person(store, age=30, first="Worker")
        self._employ(store, worker, "construction_worker")
        made = li.seed_tool_rows(store, d, worker,
                                "construction_worker", GM)
        self.assertEqual(li.broken_tools_for(store, d, worker), [])
        self._set_condition(store, made[0], 0)
        broken = li.broken_tools_for(store, d, worker)
        self.assertEqual(len(broken), 1)
        self.assertEqual(broken[0]["item_instance_id"], made[0])

    def test_tool_needs_service_at_sixty_or_below(self):
        store = make_store()
        d = data()
        worker = make_person(store, age=30, first="Worker")
        self._employ(store, worker, "construction_worker")
        made = li.seed_tool_rows(store, d, worker,
                                "construction_worker", GM)
        self._set_condition(store, made[0], 61)
        self.assertEqual(li.tool_needs_service(store, d, worker), [])
        self._set_condition(store, made[0], 60)
        self.assertEqual([r["item_instance_id"] for r in
                          li.tool_needs_service(store, d, worker)],
                         [made[0]])
        # A broken tool is due attention too (the repair that
        # restores it to 90).
        self._set_condition(store, made[0], 0)
        self.assertEqual([r["item_instance_id"] for r in
                          li.tool_needs_service(store, d, worker)],
                         [made[0]])

    def test_wear_does_nothing_without_employment(self):
        store = make_store()
        d = data()
        worker = make_person(store, age=30, first="Worker")
        made = li.seed_tool_rows(store, d, worker,
                                "construction_worker", GM)
        self.assertEqual(li.apply_tool_wear(store, d, worker, GM), [])
        self.assertTrue(all(self._condition(store, iid) == 100
                            for iid in made))

    def test_wear_ignores_tools_of_other_trades(self):
        store = make_store()
        d = data()
        teacher = make_person(store, age=30, first="Teacher")
        self._employ(store, teacher, "teacher")
        # A hammer row the teacher holds anyway (never their trade's
        # instrument) is not worn by their worked days.
        iid = _item(store, teacher, "tool", "hammer",
                    {"issued": "employer", "condition": 100})
        self.assertEqual(li.apply_tool_wear(store, d, teacher, GM), [])
        self.assertEqual(self._condition(store, iid), 100)

    def test_broken_tool_can_still_be_lost(self):
        # DQ: record_loss() checks the row exists, not its
        # condition — a broken tool lost is still a lost tool.
        store = make_store()
        worker = make_person(store, age=30, first="Worker")
        made = li.seed_tool_rows(store, data(), worker,
                                "construction_worker", GM)
        self._set_condition(store, made[0], 0)
        lid = li.record_loss(store, worker, made[0], 2000, "d1_market")
        self.assertIsNotNone(lid)

    def test_wear_applies_to_every_tool_of_the_trade(self):
        store = make_store()
        d = data()
        worker = make_person(store, age=30, first="Worker")
        self._employ(store, worker, "construction_worker")
        made = li.seed_tool_rows(store, d, worker,
                                "construction_worker", GM)
        li.apply_tool_wear(store, d, worker, GM)
        self.assertTrue(all(self._condition(store, iid) == 99
                            for iid in made))


class TestFurnitureCondition(unittest.TestCase):
    """Queue 19 Unit EF — furniture condition & decay wiring
    (GDD-04 §3.3, Unit DQ design; GDD-10 §5/§6)."""

    def _condition(self, store, iid):
        row = store.row("SELECT state FROM inventory_items"
                        " WHERE item_instance_id = ?", (iid,))
        return json.loads(row["state"])["condition"]

    def _set_condition(self, store, iid, value):
        row = store.row("SELECT state FROM inventory_items"
                        " WHERE item_instance_id = ?", (iid,))
        state = json.loads(row["state"])
        state["condition"] = value
        store.execute("UPDATE inventory_items SET state = ?"
                      " WHERE item_instance_id = ?",
                      (json.dumps(state), iid))

    def test_seed_furniture_rows_write_condition_100(self):
        store = make_store()
        head = make_person(store, age=35, first="Head")
        hid, pid = make_household(store, [head])
        made = li.seed_furniture_rows(store, data(), head,
                                      ["bed", "stove"], "F1", pid, GM)
        self.assertEqual(len(made), 2)
        self.assertTrue(all(self._condition(store, iid) == 100
                            for iid in made))

    def test_move_wear_lowers_by_two(self):
        store = make_store()
        head = make_person(store, age=35, first="Head")
        hid, pid = make_household(store, [head])
        made = li.seed_furniture_at_move_in(store, data(), hid, pid,
                                            GM)
        self.assertEqual(len(made), 8)
        worn = li.apply_furniture_move_wear(store, data(), hid, GM)
        self.assertEqual(sorted(worn), sorted(made))
        self.assertTrue(all(self._condition(store, iid) == 98
                            for iid in made))

    def test_move_wear_floors_at_zero(self):
        store = make_store()
        head = make_person(store, age=35, first="Head")
        hid, pid = make_household(store, [head])
        made = li.seed_furniture_at_move_in(store, data(), hid, pid,
                                            GM)
        self._set_condition(store, made[0], 1)
        li.apply_furniture_move_wear(store, data(), hid, GM)
        self.assertEqual(self._condition(store, made[0]), 0)
        li.apply_furniture_move_wear(store, data(), hid, GM)
        self.assertEqual(self._condition(store, made[0]), 0)

    def test_end_to_end_move_wears_carried_furniture(self):
        store, d, ids = _stocked_store()
        head = make_person(store, age=35, first="Mover")
        hid = store.next_id("HH", "households", "household_id")
        pricey = store.row("SELECT * FROM properties WHERE property_id"
                           " = ?", (ids["pricey"],))
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
        made = li.seed_furniture_at_move_in(store, d, hid,
                                            ids["pricey"], GM)
        self.assertEqual(len(made), 8)
        self.assertEqual(hh.move_household(store, d, hid, ids["cheap"],
                                           2000), 2500)
        rows = store.rows("SELECT * FROM inventory_items WHERE"
                          " owner_character_id = ? AND"
                          " item_type = 'furniture'", (head,))
        self.assertEqual(len(rows), 8)  # carried, not re-seeded
        self.assertTrue(all(self._condition(
            store, r["item_instance_id"]) == 98 for r in rows))
        self.assertTrue(all(r["location_property_id"] == ids["cheap"]
                            for r in rows))

    def test_move_in_seeding_never_wears_new_rows(self):
        # A bare head moving into a home is furnished at 100 — the
        # move wears the furniture carried, and new furniture was
        # never carried.
        store, d, ids = _stocked_store()
        head = make_person(store, age=35, first="Mover")
        hid = store.next_id("HH", "households", "household_id")
        pricey = store.row("SELECT * FROM properties WHERE property_id"
                           " = ?", (ids["pricey"],))
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
        self.assertEqual(hh.move_household(store, d, hid, ids["cheap"],
                                           2000), 2500)
        rows = store.rows("SELECT * FROM inventory_items WHERE"
                          " owner_character_id = ? AND"
                          " item_type = 'furniture'", (head,))
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(self._condition(
            store, r["item_instance_id"]) == 100 for r in rows))

    def test_exposure_wear_lowers_by_one_in_the_zone(self):
        store = make_store()
        head = make_person(store, age=35, first="Head")
        hid, pid = make_household(store, [head])
        made = li.seed_furniture_at_move_in(store, data(), hid, pid,
                                            GM)
        worn = li.apply_furniture_exposure_wear(
            store, data(), {"d1_midtown"}, GM)
        self.assertEqual(sorted(worn), sorted(made))
        self.assertTrue(all(self._condition(store, iid) == 99
                            for iid in made))

    def test_exposure_wear_skips_other_zones(self):
        store = make_store()
        head = make_person(store, age=35, first="Head")
        hid, pid = make_household(store, [head])
        made = li.seed_furniture_at_move_in(store, data(), hid, pid,
                                            GM)
        self.assertEqual(li.apply_furniture_exposure_wear(
            store, data(), {"d1_uptown"}, GM), [])
        self.assertTrue(all(self._condition(store, iid) == 100
                            for iid in made))

    def test_exposure_wear_skips_rows_with_no_location(self):
        store = make_store()
        head = make_person(store, age=35, first="Head")
        made = li.seed_furniture_rows(store, data(), head,
                                      ["bed"], "F1", None, GM)
        self.assertEqual(li.apply_furniture_exposure_wear(
            store, data(), {"d1_midtown"}, GM), [])
        self.assertEqual(self._condition(store, made[0]), 100)

    def test_effective_tier_drops_as_pieces_break(self):
        store = make_store()
        d = data()
        head = make_person(store, age=35, first="Head")
        hid, pid = make_household(store, [head])
        made = li.seed_furniture_at_move_in(store, d, hid, pid, GM)
        self.assertEqual(li.effective_furniture_tier(store, d, head),
                         "F1")
        # Break one F1 piece: the F1 set no longer fully stands.
        bed = next(i for i in made
                   if store.row("SELECT item_ref FROM inventory_items"
                                " WHERE item_instance_id = ?",
                                (i,))["item_ref"] == "bed")
        self._set_condition(store, bed, 0)
        self.assertEqual(li.effective_furniture_tier(store, d, head),
                         "F0")
        # Break one F0 piece too: no tier stands.
        mattress = next(i for i in made
                        if store.row(
                            "SELECT item_ref FROM inventory_items"
                            " WHERE item_instance_id = ?", (i,))[
                                "item_ref"] == "floor_mattress")
        self._set_condition(store, mattress, 0)
        self.assertIsNone(li.effective_furniture_tier(store, d, head))

    def test_restore_multiplier_follows_the_effective_tier(self):
        store = make_store()
        d = data()
        head = make_person(store, age=35, first="Head")
        hid, pid = make_household(store, [head])
        li.seed_furniture_rows(store, d, head,
                               li.furniture_tier_items(d, "F3"), "F3",
                               pid, GM)
        self.assertEqual(li.effective_furniture_tier(store, d, head),
                         "F3")
        self.assertEqual(
            li.furniture_restore_multiplier(store, d, head), 1.3)
        # Break the TV: F3 falls to F2.
        tv = store.row("SELECT item_instance_id FROM inventory_items"
                       " WHERE owner_character_id = ? AND"
                       " item_ref = 'tv'", (head,))["item_instance_id"]
        self._set_condition(store, tv, 0)
        self.assertEqual(li.effective_furniture_tier(store, d, head),
                         "F2")
        self.assertEqual(
            li.furniture_restore_multiplier(store, d, head), 1.15)
        # Break every F0 piece: no tier stands, no rate invented.
        for iid in [r["item_instance_id"] for r in store.rows(
                "SELECT item_instance_id FROM inventory_items"
                " WHERE owner_character_id = ? AND item_ref IN"
                " ('floor_mattress', 'single_burner', 'crate_table')",
                (head,))]:
            self._set_condition(store, iid, 0)
        self.assertIsNone(li.effective_furniture_tier(store, d, head))
        self.assertIsNone(
            li.furniture_restore_multiplier(store, d, head))


class TestToolWeatherWear(unittest.TestCase):
    """Queue 20 Unit EG — tool weather wear (GDD-04 §3.3, Unit DQ
    design): the environment pass's exposure wears the tools of
    characters whose home stands in an exposed zone."""

    def _employ(self, store, cid, profession_id):
        store.insert("employments",
                     employment_id=f"EM-TEST-EG-{cid}",
                     character_id=cid, profession_id=profession_id,
                     tier=1, wage_per_month=10000,
                     started_at_game_minutes=GM,
                     ended_at_game_minutes=None)

    def _condition(self, store, iid):
        row = store.row("SELECT state FROM inventory_items"
                        " WHERE item_instance_id = ?", (iid,))
        return json.loads(row["state"])["condition"]

    def _set_condition(self, store, iid, value):
        row = store.row("SELECT state FROM inventory_items"
                        " WHERE item_instance_id = ?", (iid,))
        state = json.loads(row["state"])
        state["condition"] = value
        store.execute("UPDATE inventory_items SET state = ?"
                      " WHERE item_instance_id = ?", (json.dumps(state),
                                                      iid))

    def _broken_count(self, store, cid):
        return store.row("SELECT COUNT(*) AS n FROM life_events"
                         " WHERE character_id = ?"
                         " AND event_type = 'tool_broken'",
                         (cid,))["n"]

    def test_exposed_home_wears_the_tools_by_one(self):
        store = make_store()
        d = data()
        worker = make_person(store, age=30, first="Worker")
        hid, pid = make_household(store, [worker])
        self._employ(store, worker, "construction_worker")
        made = li.seed_tool_rows(store, d, worker,
                                "construction_worker", GM)
        worn = li.apply_tool_weather_wear(store, d, {"d1_midtown"},
                                          GM)
        self.assertEqual(sorted(worn), sorted(made))
        self.assertTrue(all(self._condition(store, iid) == 99
                            for iid in made))

    def test_unexposed_home_wears_nothing(self):
        store = make_store()
        d = data()
        worker = make_person(store, age=30, first="Worker")
        hid, pid = make_household(store, [worker])
        self._employ(store, worker, "construction_worker")
        made = li.seed_tool_rows(store, d, worker,
                                "construction_worker", GM)
        self.assertEqual(li.apply_tool_weather_wear(
            store, d, {"d1_uptown"}, GM), [])
        self.assertTrue(all(self._condition(store, iid) == 100
                            for iid in made))

    def test_no_household_wears_nothing(self):
        # No home, no exposed home: the tools stay at 100.
        store = make_store()
        d = data()
        worker = make_person(store, age=30, first="Worker")
        self._employ(store, worker, "construction_worker")
        made = li.seed_tool_rows(store, d, worker,
                                "construction_worker", GM)
        self.assertEqual(li.apply_tool_weather_wear(
            store, d, {"d1_midtown"}, GM), [])
        self.assertTrue(all(self._condition(store, iid) == 100
                            for iid in made))

    def test_weather_break_logs_one_event(self):
        store = make_store()
        d = data()
        worker = make_person(store, age=30, first="Worker")
        hid, pid = make_household(store, [worker])
        self._employ(store, worker, "construction_worker")
        made = li.seed_tool_rows(store, d, worker,
                                "construction_worker", GM)
        hammer = next(i for i in made
                      if store.row("SELECT item_ref FROM inventory_items"
                                   " WHERE item_instance_id = ?",
                                   (i,))["item_ref"] == "hammer")
        self._set_condition(store, hammer, 1)
        worn = li.apply_tool_weather_wear(store, d, {"d1_midtown"},
                                          GM)
        self.assertIn(hammer, worn)
        self.assertEqual(self._condition(store, hammer), 0)
        self.assertEqual(self._broken_count(store, worker), 1)
        event = store.row("SELECT * FROM life_events WHERE"
                          " character_id = ? AND"
                          " event_type = 'tool_broken'", (worker,))
        self.assertEqual(json.loads(event["details"])["cause"],
                         "weather_exposure")
        # A second exposed day wears the other tools again but the
        # broken hammer wears nothing further and logs no second
        # event.
        li.apply_tool_weather_wear(store, d, {"d1_midtown"}, GM)
        self.assertEqual(self._broken_count(store, worker), 1)

    def test_empty_zones_wear_nothing(self):
        store = make_store()
        d = data()
        worker = make_person(store, age=30, first="Worker")
        hid, pid = make_household(store, [worker])
        self._employ(store, worker, "construction_worker")
        made = li.seed_tool_rows(store, d, worker,
                                "construction_worker", GM)
        self.assertEqual(li.apply_tool_weather_wear(store, d, set(),
                                                    GM), [])
        self.assertTrue(all(self._condition(store, iid) == 100
                            for iid in made))

    def test_environment_pass_wears_exposed_tools_and_furniture(self):
        # End to end: an active disaster in the environment pass
        # wears the exposed home's tools beside its furniture, and
        # the unexposed home's tools stay at 100. A cyclone, not a
        # flood: the hydrology pass retires a synthetic flood the
        # moment the river sits below the flood level (the flood's
        # own phase rule), so a hand-started flood never reaches
        # the wear loop — a cyclone stays active through the pass,
        # and the wear loop treats flood / cyclone / severe_storm
        # identically (one call per active disaster, same zones).
        from tools.sim import environment as env_mod
        from tools.sim.tests.envcommon import env_world
        store, d = env_world()
        zones = env_mod.exposed_zones(store, d, "rupsha_city")
        self.assertTrue(zones)
        exposed = sorted(zones)[0]
        safe = next(z for z in ("d1_midtown", "d1_uptown",
                                "d1_riverfront", "d1_civic",
                                "d1_old_town")
                    if z not in zones)
        worker = make_person(store, age=30, first="Worker")
        self._employ(store, worker, "construction_worker")
        hid, pid = make_household(store, [worker])
        store.execute("UPDATE properties SET district_id = ?"
                      " WHERE property_id = ?", (exposed, pid))
        store.execute("UPDATE households SET district_id = ?"
                      " WHERE household_id = ?", (exposed, hid))
        tools = li.seed_tool_rows(store, d, worker,
                                  "construction_worker", GM)
        furniture = li.seed_furniture_at_move_in(store, d, hid, pid,
                                                 GM)
        other = make_person(store, age=30, first="Other")
        self._employ(store, other, "construction_worker")
        hid2, pid2 = make_household(store, [other])
        store.execute("UPDATE properties SET district_id = ?"
                      " WHERE property_id = ?", (safe, pid2))
        store.execute("UPDATE households SET district_id = ?"
                      " WHERE household_id = ?", (safe, hid2))
        other_tools = li.seed_tool_rows(store, d, other,
                                        "construction_worker", GM)
        env_mod.start_disaster(store, d, "cyclone", "rupsha_city", 0,
                               1440)
        env_mod.daily_pass(store, d, rng(), 0, 1440)
        self.assertTrue(all(self._condition(store, iid) == 99
                            for iid in tools))
        self.assertTrue(all(self._condition(store, iid) == 99
                            for iid in furniture))
        self.assertTrue(all(self._condition(store, iid) == 100
                            for iid in other_tools))


class TestExposureWearDedupe(unittest.TestCase):
    """Queue 21 Unit EP — concurrent-disaster exposure wear dedupe
    (GDD-04 §3.3, EG follow-up): a zone under two simultaneous
    disasters wears once per day, furniture and tools alike. The
    dedupe lives in environment.daily_pass (one call over the
    union of the disasters' exposed zones), not in the wear
    helpers — the helpers still wear once per call."""

    def _employ(self, store, cid, profession_id):
        store.insert("employments",
                     employment_id=f"EM-TEST-EP-{cid}",
                     character_id=cid, profession_id=profession_id,
                     tier=1, wage_per_month=10000,
                     started_at_game_minutes=GM,
                     ended_at_game_minutes=None)

    def _condition(self, store, iid):
        row = store.row("SELECT state FROM inventory_items"
                        " WHERE item_instance_id = ?", (iid,))
        return json.loads(row["state"])["condition"]

    def _world_with_exposed_home(self):
        # (store, data, exposed_zone, worker, tools, furniture)
        from tools.sim import environment as env_mod
        from tools.sim.tests.envcommon import env_world
        store, d = env_world()
        zones = env_mod.exposed_zones(store, d, "rupsha_city")
        self.assertTrue(zones)
        exposed = sorted(zones)[0]
        worker = make_person(store, age=30, first="Worker")
        self._employ(store, worker, "construction_worker")
        hid, pid = make_household(store, [worker])
        store.execute("UPDATE properties SET district_id = ?"
                      " WHERE property_id = ?", (exposed, pid))
        store.execute("UPDATE households SET district_id = ?"
                      " WHERE household_id = ?", (exposed, hid))
        tools = li.seed_tool_rows(store, d, worker,
                                  "construction_worker", GM)
        furniture = li.seed_furniture_at_move_in(store, d, hid, pid,
                                                 GM)
        return store, d, exposed, worker, tools, furniture

    def test_two_simultaneous_disasters_wear_once(self):
        from tools.sim import environment as env_mod
        store, d, _exposed, _worker, tools, furniture = \
            self._world_with_exposed_home()
        env_mod.start_disaster(store, d, "cyclone", "rupsha_city", 0,
                               1440)
        env_mod.start_disaster(store, d, "severe_storm", "rupsha_city",
                               0, 1440)
        env_mod.daily_pass(store, d, rng(), 0, 1440)
        # Before EP this was 98 (one wear per disaster); now 99.
        self.assertTrue(all(self._condition(store, iid) == 99
                            for iid in tools))
        self.assertTrue(all(self._condition(store, iid) == 99
                            for iid in furniture))

    def test_second_day_wears_again(self):
        # The dedupe is per day, not permanent: the next day's pass
        # wears again.
        from tools.sim import environment as env_mod
        store, d, _exposed, _worker, tools, furniture = \
            self._world_with_exposed_home()
        env_mod.start_disaster(store, d, "cyclone", "rupsha_city", 0,
                               1440)
        env_mod.start_disaster(store, d, "cyclone", "rupsha_city", 0,
                               1440)
        env_mod.daily_pass(store, d, rng(), 0, 1440)
        self.assertTrue(all(self._condition(store, iid) == 99
                            for iid in tools))
        env_mod.daily_pass(store, d, rng(), 1, 2880)
        self.assertTrue(all(self._condition(store, iid) == 98
                            for iid in tools))
        self.assertTrue(all(self._condition(store, iid) == 98
                            for iid in furniture))

    def test_helpers_still_wear_once_per_call(self):
        # The dedupe lives in the pass: calling a wear helper twice
        # directly still wears twice. This pins the design — a
        # future caller must go through the pass (or union first).
        store = make_store()
        d = data()
        worker = make_person(store, age=30, first="Worker")
        hid, pid = make_household(store, [worker])
        self._employ(store, worker, "construction_worker")
        made = li.seed_tool_rows(store, d, worker,
                                "construction_worker", GM)
        li.apply_tool_weather_wear(store, d, {"d1_midtown"}, GM)
        li.apply_tool_weather_wear(store, d, {"d1_midtown"}, GM)
        self.assertTrue(all(self._condition(store, iid) == 98
                            for iid in made))


class TestRepair(unittest.TestCase):
    """Queue 20 Unit EH — tool & furniture repair (GDD-04 §3.3,
    Unit DQ design): restore to 90, no ledger charge."""

    def _condition(self, store, iid):
        row = store.row("SELECT state FROM inventory_items"
                        " WHERE item_instance_id = ?", (iid,))
        return json.loads(row["state"])["condition"]

    def _set_condition(self, store, iid, value):
        row = store.row("SELECT state FROM inventory_items"
                        " WHERE item_instance_id = ?", (iid,))
        state = json.loads(row["state"])
        state["condition"] = value
        store.execute("UPDATE inventory_items SET state = ?"
                      " WHERE item_instance_id = ?", (json.dumps(state),
                                                      iid))

    def _ledger_rows(self, store):
        return store.row("SELECT COUNT(*) AS n FROM economy_ledger")["n"]

    def test_repair_tool_restores_a_worn_tool_to_90(self):
        store = make_store()
        worker = make_person(store, age=30, first="Worker")
        made = li.seed_tool_rows(store, data(), worker,
                                "construction_worker", GM)
        self._set_condition(store, made[0], 50)
        before = self._ledger_rows(store)
        self.assertEqual(li.repair_tool(store, made[0]), made[0])
        self.assertEqual(self._condition(store, made[0]), 90)
        self.assertEqual(self._ledger_rows(store), before)

    def test_repair_tool_restores_a_broken_tool_to_90(self):
        store = make_store()
        worker = make_person(store, age=30, first="Worker")
        made = li.seed_tool_rows(store, data(), worker,
                                "construction_worker", GM)
        self._set_condition(store, made[0], 0)
        self.assertEqual(li.repair_tool(store, made[0]), made[0])
        self.assertEqual(self._condition(store, made[0]), 90)

    def test_repair_furniture_restores_a_worn_piece_to_90(self):
        store = make_store()
        head = make_person(store, age=35, first="Head")
        hid, pid = make_household(store, [head])
        made = li.seed_furniture_rows(store, data(), head,
                                      ["bed"], "F1", pid, GM)
        self._set_condition(store, made[0], 42)
        before = self._ledger_rows(store)
        self.assertEqual(li.repair_furniture(store, made[0]),
                         made[0])
        self.assertEqual(self._condition(store, made[0]), 90)
        self.assertEqual(self._ledger_rows(store), before)

    def test_repair_refuses_a_row_already_at_90_or_above(self):
        store = make_store()
        worker = make_person(store, age=30, first="Worker")
        made = li.seed_tool_rows(store, data(), worker,
                                "construction_worker", GM)
        self._set_condition(store, made[0], 90)
        self.assertIsNone(li.repair_tool(store, made[0]))
        self.assertEqual(self._condition(store, made[0]), 90)
        # 100 (new) needs no repair either.
        self.assertIsNone(li.repair_tool(store, made[1]))
        self.assertEqual(self._condition(store, made[1]), 100)
        # 95 is better than repaired: refused, not lowered.
        self._set_condition(store, made[2], 95)
        self.assertIsNone(li.repair_tool(store, made[2]))
        self.assertEqual(self._condition(store, made[2]), 95)

    def test_repair_refuses_an_unknown_row(self):
        store = make_store()
        self.assertIsNone(li.repair_tool(store, "INV999"))
        self.assertIsNone(li.repair_furniture(store, "INV999"))

    def test_repair_refuses_the_other_type(self):
        store = make_store()
        head = make_person(store, age=35, first="Head")
        hid, pid = make_household(store, [head])
        furniture = li.seed_furniture_rows(store, data(), head,
                                           ["bed"], "F1", pid, GM)
        self._set_condition(store, furniture[0], 50)
        self.assertIsNone(li.repair_tool(store, furniture[0]))
        self.assertEqual(self._condition(store, furniture[0]), 50)
        worker = make_person(store, age=30, first="Worker")
        tools = li.seed_tool_rows(store, data(), worker,
                                  "construction_worker", GM)
        self._set_condition(store, tools[0], 50)
        self.assertIsNone(li.repair_furniture(store, tools[0]))
        self.assertEqual(self._condition(store, tools[0]), 50)

    def test_repair_keeps_the_other_state_keys(self):
        store = make_store()
        worker = make_person(store, age=30, first="Worker")
        made = li.seed_tool_rows(store, data(), worker,
                                "construction_worker", GM)
        self._set_condition(store, made[0], 30)
        li.repair_tool(store, made[0])
        state = json.loads(store.row(
            "SELECT state FROM inventory_items"
            " WHERE item_instance_id = ?", (made[0],))["state"])
        self.assertEqual(state["issued"], "employer")
        self.assertEqual(state["condition"], 90)


class TestLostPieceVsTier(unittest.TestCase):
    """Queue 20 Unit EI — the lost-piece decision (GDD-04 §3.3,
    GDD-10 §5): a lost piece drops the effective tier."""

    def _condition(self, store, iid):
        row = store.row("SELECT state FROM inventory_items"
                        " WHERE item_instance_id = ?", (iid,))
        return json.loads(row["state"])["condition"]

    def _set_condition(self, store, iid, value):
        row = store.row("SELECT state FROM inventory_items"
                        " WHERE item_instance_id = ?", (iid,))
        state = json.loads(row["state"])
        state["condition"] = value
        store.execute("UPDATE inventory_items SET state = ?"
                      " WHERE item_instance_id = ?", (json.dumps(state),
                                                      iid))

    def _piece(self, store, head, item_ref):
        return store.row("SELECT item_instance_id FROM inventory_items"
                         " WHERE owner_character_id = ? AND"
                         " item_ref = ?", (head, item_ref))[
                             "item_instance_id"]

    def _seeded(self, store, d, head, hid, pid):
        return li.seed_furniture_at_move_in(store, d, hid, pid, GM)

    def test_a_lost_piece_drops_the_tier(self):
        store = make_store()
        d = data()
        head = make_person(store, age=35, first="Head")
        hid, pid = make_household(store, [head])
        self._seeded(store, d, head, hid, pid)
        self.assertEqual(li.effective_furniture_tier(store, d, head),
                         "F1")
        bed = self._piece(store, head, "bed")
        lid = li.record_loss(store, head, bed, 2000, "d1_midtown")
        self.assertIsNotNone(lid)
        # The bed is lost, not broken — the tier drops all the same.
        self.assertEqual(self._condition(store, bed), 100)
        self.assertEqual(li.effective_furniture_tier(store, d, head),
                         "F0")

    def test_a_found_piece_still_drops_the_tier(self):
        # The finder holds it, not the home: still not standing.
        store = make_store()
        d = data()
        head = make_person(store, age=35, first="Head")
        finder = make_person(store, age=28, first="Finder")
        hid, pid = make_household(store, [head])
        self._seeded(store, d, head, hid, pid)
        bed = self._piece(store, head, "bed")
        lid = li.record_loss(store, head, bed, 2000, "d1_midtown")
        self.assertEqual(li.find_lost_item(store, lid, finder, 2100,
                                           "d1_midtown"), lid)
        self.assertEqual(li.effective_furniture_tier(store, d, head),
                         "F0")

    def test_the_hand_back_restores_the_tier(self):
        store = make_store()
        d = data()
        head = make_person(store, age=35, first="Head")
        finder = make_person(store, age=28, first="Finder")
        hid, pid = make_household(store, [head])
        self._seeded(store, d, head, hid, pid)
        bed = self._piece(store, head, "bed")
        lid = li.record_loss(store, head, bed, 2000, "d1_midtown")
        li.find_lost_item(store, lid, finder, 2100, "d1_midtown")
        self.assertEqual(li.effective_furniture_tier(store, d, head),
                         "F0")
        self.assertEqual(li.hand_back_lost_item(
            store, lid, finder, 2200, finder_property_id=pid), lid)
        self.assertEqual(li.effective_furniture_tier(store, d, head),
                         "F1")

    def test_a_broken_piece_drops_the_tier_the_same_way(self):
        # The EF case, re-proven under the EI rule: broken and lost
        # are one rule ("not usable tonight"), not two.
        store = make_store()
        d = data()
        head = make_person(store, age=35, first="Head")
        hid, pid = make_household(store, [head])
        self._seeded(store, d, head, hid, pid)
        bed = self._piece(store, head, "bed")
        self._set_condition(store, bed, 0)
        self.assertEqual(li.effective_furniture_tier(store, d, head),
                         "F0")

    def test_a_lost_f0_piece_leaves_no_tier_standing(self):
        store = make_store()
        d = data()
        head = make_person(store, age=35, first="Head")
        hid, pid = make_household(store, [head])
        self._seeded(store, d, head, hid, pid)
        mattress = self._piece(store, head, "floor_mattress")
        lid = li.record_loss(store, head, mattress, 2000,
                             "d1_midtown")
        self.assertIsNotNone(lid)
        self.assertIsNone(li.effective_furniture_tier(store, d, head))
        self.assertIsNone(
            li.furniture_restore_multiplier(store, d, head))

    def test_a_second_row_of_the_piece_keeps_the_tier(self):
        # A replacement bought beside the lost original: one usable
        # piece in the home is one furnished piece. (The replacement
        # is written directly here: seed_furniture_rows() skips
        # pieces the owner already holds — its seeding rule — so a
        # replacement row comes from the purchase event, Unit EM,
        # not from seeding.)
        store = make_store()
        d = data()
        head = make_person(store, age=35, first="Head")
        hid, pid = make_household(store, [head])
        self._seeded(store, d, head, hid, pid)
        bed = self._piece(store, head, "bed")
        li.record_loss(store, head, bed, 2000, "d1_midtown")
        self.assertEqual(li.effective_furniture_tier(store, d, head),
                         "F0")
        replacement = _item(store, head, "furniture", "bed",
                            {"furniture_tier": "F1", "condition": 100})
        store.execute("UPDATE inventory_items SET"
                      " location_property_id = ?"
                      " WHERE item_instance_id = ?",
                      (pid, replacement))
        self.assertEqual(li.effective_furniture_tier(store, d, head),
                         "F1")


class TestFurniturePurchase(unittest.TestCase):
    """Queue 21 Unit ET — the furniture purchase event (GDD-10 §5)."""

    def _home(self, head_funds=100000, member_funds=0, seed=True):
        store = make_store()
        head = make_person(store, age=35, first="Head")
        member = make_person(store, age=30, first="Member")
        hid, pid = make_household(store, [head, member])
        store.transfer(None, head, head_funds, "seed", GM)
        if member_funds:
            store.transfer(None, member, member_funds, "seed", GM)
        if seed:
            li.seed_furniture_at_move_in(store, data(), hid, pid, GM)
        return store, head, member, hid, pid

    def _ledger_purchase(self, store, payer):
        return store.row(
            "SELECT * FROM economy_ledger WHERE from_character_id = ?"
            " AND to_character_id = 'SYS-MARKET'"
            " AND reason_code = 'purchase'", (payer,))

    def test_buys_an_f2_piece_at_catalogue_price(self):
        store, head, _m, hid, pid = self._home()
        iid = hh.purchase_furniture(store, data(), hid, "sofa", 5, GM)
        self.assertIsNotNone(iid)
        self.assertEqual(store.balance(head), 95000)  # sofa 5,000
        row = self._ledger_purchase(store, head)
        self.assertIsNotNone(row)
        self.assertEqual(row["amount"], 5000)
        bought = store.row(
            "SELECT * FROM inventory_items WHERE item_instance_id = ?",
            (iid,))
        self.assertEqual(bought["item_type"], "furniture")
        self.assertEqual(bought["item_ref"], "sofa")
        self.assertEqual(bought["owner_character_id"], head)
        self.assertEqual(bought["location_property_id"], pid)
        self.assertEqual(json.loads(bought["state"]),
                         {"furniture_tier": "F2", "condition": 100})
        # One F2 sofa alone does not raise the tier (GDD-10 §5).
        self.assertEqual(
            li.effective_furniture_tier(store, data(), head), "F1")

    def test_buying_the_full_f2_set_raises_the_tier(self):
        store, head, _m, hid, _p = self._home()
        for piece in ("sofa", "bookshelf", "desk", "kitchen_upgrade",
                      "curtains"):
            self.assertIsNotNone(
                hh.purchase_furniture(store, data(), hid, piece, 5, GM))
        self.assertEqual(store.balance(head), 88000)  # F2 adds 12,000
        self.assertEqual(
            li.effective_furniture_tier(store, data(), head), "F2")

    def test_second_row_for_an_already_held_piece(self):
        store, head, _m, hid, _p = self._home()
        iid = hh.purchase_furniture(store, data(), hid, "bed", 5, GM)
        self.assertIsNotNone(iid)
        self.assertEqual(store.balance(head), 96000)  # bed 4,000
        beds = store.rows(
            "SELECT * FROM inventory_items WHERE owner_character_id = ?"
            " AND item_type = 'furniture' AND item_ref = 'bed'",
            (head,))
        self.assertEqual(len(beds), 2)
        self.assertTrue(all(
            json.loads(b["state"])["condition"] == 100 for b in beds))
        self.assertEqual(
            li.effective_furniture_tier(store, data(), head), "F1")

    def test_refuses_when_the_pool_cannot_cover_it(self):
        store, head, _m, hid, _p = self._home(head_funds=1000)
        self.assertIsNone(
            hh.purchase_furniture(store, data(), hid, "sofa", 5, GM))
        self.assertEqual(store.balance(head), 1000)
        self.assertIsNone(self._ledger_purchase(store, head))
        self.assertEqual(store.row(
            "SELECT COUNT(*) AS n FROM inventory_items WHERE"
            " owner_character_id = ? AND item_ref = 'sofa'",
            (head,))["n"], 0)

    def test_richest_member_covers_when_the_head_is_short(self):
        store, head, member, hid, _p = self._home(
            head_funds=1000, member_funds=100000)
        iid = hh.purchase_furniture(store, data(), hid, "sofa", 5, GM)
        self.assertIsNotNone(iid)
        self.assertEqual(store.balance(head), 1000)
        self.assertEqual(store.balance(member), 95000)
        self.assertIsNotNone(self._ledger_purchase(store, member))

    def test_unknown_item_raises(self):
        store, _h, _m, hid, _p = self._home()
        with self.assertRaises(ValueError):
            hh.purchase_furniture(store, data(), hid, "not_a_piece",
                                  5, GM)

    def test_no_head_returns_none(self):
        store = make_store()
        hid, _pid = make_household(store, [])
        self.assertIsNone(
            hh.purchase_furniture(store, data(), hid, "sofa", 5, GM))

    def test_no_home_returns_none(self):
        store, head, _m, hid, _p = self._home()
        store.execute("UPDATE households SET home_property_id = NULL"
                      " WHERE household_id = ?", (hid,))
        self.assertIsNone(
            hh.purchase_furniture(store, data(), hid, "sofa", 5, GM))
        self.assertEqual(store.balance(head), 100000)

    def test_f0_piece_costs_nothing_and_seeds_a_second_row(self):
        store, head, _m, hid, _p = self._home()
        iid = hh.purchase_furniture(store, data(), hid,
                                    "floor_mattress", 5, GM)
        self.assertIsNotNone(iid)
        self.assertEqual(store.balance(head), 100000)
        self.assertIsNone(self._ledger_purchase(store, head))
        rows = store.rows(
            "SELECT * FROM inventory_items WHERE owner_character_id = ?"
            " AND item_type = 'furniture'"
            " AND item_ref = 'floor_mattress'", (head,))
        self.assertEqual(len(rows), 2)

    def test_a_second_purchase_in_the_same_month_is_a_second_purchase(self):
        store, head, _m, hid, _p = self._home()
        first = hh.purchase_furniture(store, data(), hid, "sofa", 5, GM)
        second = hh.purchase_furniture(store, data(), hid, "sofa", 5, GM)
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertNotEqual(first, second)
        self.assertEqual(store.balance(head), 90000)
        self.assertEqual(store.row(
            "SELECT COUNT(*) AS n FROM economy_ledger WHERE"
            " from_character_id = ? AND reason_code = 'purchase'",
            (head,))["n"], 2)

    def test_seed_furniture_rows_still_skips_held_pieces_by_default(self):
        store = make_store()
        owner = make_person(store, age=30, first="Owner")
        made = li.seed_furniture_rows(store, data(), owner, ["bed"],
                                     "F1", None, GM)
        self.assertEqual(len(made), 1)
        self.assertEqual(li.seed_furniture_rows(
            store, data(), owner, ["bed"], "F1", None, GM), [])
        again = li.seed_furniture_rows(
            store, data(), owner, ["bed"], "F1", None, GM,
            allow_duplicate=True)
        self.assertEqual(len(again), 1)
        self.assertNotEqual(again[0], made[0])


class TestMonthlyRepairSweep(unittest.TestCase):
    """Queue 21 Unit EU — the monthly tool service (GDD-04 §3.3)."""

    def _worker_with_tools(self, store,
                           profession_id="construction_worker"):
        worker = make_person(store, age=30, first="Worker")
        store.insert("employments", employment_id="EM-TEST-EU",
                     character_id=worker, profession_id=profession_id,
                     tier=1, wage_per_month=10000,
                     started_at_game_minutes=GM,
                     ended_at_game_minutes=None)
        made = li.seed_tool_rows(store, data(), worker,
                                 profession_id, GM)
        return worker, made

    def _condition(self, store, iid):
        row = store.row("SELECT state FROM inventory_items"
                        " WHERE item_instance_id = ?", (iid,))
        return json.loads(row["state"])["condition"]

    def _set_condition(self, store, iid, value):
        row = store.row("SELECT state FROM inventory_items"
                        " WHERE item_instance_id = ?", (iid,))
        state = json.loads(row["state"])
        state["condition"] = value
        store.execute("UPDATE inventory_items SET state = ?"
                      " WHERE item_instance_id = ?",
                      (json.dumps(state), iid))

    def test_repairs_tools_at_or_below_sixty(self):
        store = make_store()
        _w, made = self._worker_with_tools(store)
        self._set_condition(store, made[0], 60)
        self._set_condition(store, made[1], 61)
        self._set_condition(store, made[2], 30)
        self._set_condition(store, made[3], 100)
        out = li.monthly_repair_sweep(store, data(), GM)
        self.assertEqual(set(out["repaired"]), {made[0], made[2]})
        self.assertEqual(out["broken"], [])
        self.assertEqual(self._condition(store, made[0]), 90)
        self.assertEqual(self._condition(store, made[1]), 61)
        self.assertEqual(self._condition(store, made[2]), 90)
        self.assertEqual(self._condition(store, made[3]), 100)

    def test_repairs_a_broken_tool_and_lists_it_broken(self):
        store = make_store()
        _w, made = self._worker_with_tools(store)
        self._set_condition(store, made[0], 0)
        out = li.monthly_repair_sweep(store, data(), GM)
        self.assertEqual(out["broken"], [made[0]])
        self.assertEqual(self._condition(store, made[0]), 90)

    def test_repairs_every_due_tool_for_every_character(self):
        store = make_store()
        _w1, made1 = self._worker_with_tools(store)
        worker2 = make_person(store, age=28, first="Second")
        store.insert("employments", employment_id="EM-TEST-EU2",
                     character_id=worker2,
                     profession_id="construction_worker",
                     tier=1, wage_per_month=10000,
                     started_at_game_minutes=GM,
                     ended_at_game_minutes=None)
        made2 = li.seed_tool_rows(store, data(), worker2,
                                 "construction_worker", GM)
        self._set_condition(store, made1[0], 45)
        self._set_condition(store, made2[0], 0)
        out = li.monthly_repair_sweep(store, data(), GM)
        self.assertEqual(set(out["repaired"]), {made1[0], made2[0]})
        self.assertEqual(out["broken"], [made2[0]])
        self.assertEqual(self._condition(store, made1[0]), 90)
        self.assertEqual(self._condition(store, made2[0]), 90)

    def test_no_ledger_charge(self):
        store = make_store()
        _w, made = self._worker_with_tools(store)
        self._set_condition(store, made[0], 0)
        self._set_condition(store, made[1], 20)
        li.monthly_repair_sweep(store, data(), GM)
        self.assertEqual(store.row(
            "SELECT COUNT(*) AS n FROM economy_ledger")["n"], 0)

    def test_ignores_tools_of_another_profession(self):
        store = make_store()
        worker, made = self._worker_with_tools(store)
        chef_tool = li.seed_tool_rows(store, data(), worker,
                                     "chef", GM)[0]
        self._set_condition(store, made[0], 10)
        self._set_condition(store, chef_tool, 10)
        li.monthly_repair_sweep(store, data(), GM)
        self.assertEqual(self._condition(store, made[0]), 90)
        self.assertEqual(self._condition(store, chef_tool), 10)

    def test_dead_characters_are_not_serviced(self):
        store = make_store()
        worker, made = self._worker_with_tools(store)
        self._set_condition(store, made[0], 10)
        store.execute("UPDATE characters SET died_at_game_minutes = ?"
                      " WHERE character_id = ?", (GM, worker))
        out = li.monthly_repair_sweep(store, data(), GM)
        self.assertEqual(out, {"repaired": [], "broken": []})
        self.assertEqual(self._condition(store, made[0]), 10)

    def test_sweep_is_a_noop_with_no_tools(self):
        store = make_store()
        self.assertEqual(li.monthly_repair_sweep(store, data(), GM),
                         {"repaired": [], "broken": []})


class TestMonthlyRepairHook(unittest.TestCase):
    """The engine's monthly social pass calls the repair sweep:
    a worn tool in a live world is repaired at month end."""

    @classmethod
    def setUpClass(cls):
        cls.path = _tmp_path()
        cls.sim = Simulation(cls.path, seed="q21-eu")
        cls.sim.generate_population(60)
        cls.store = cls.sim.store
        cls.data = cls.sim.data

    @classmethod
    def tearDownClass(cls):
        cls.sim.close()
        os.remove(cls.path)

    def test_monthly_social_repairs_a_broken_tool(self):
        worker = self.store.row(
            "SELECT c.character_id FROM characters c WHERE"
            " c.is_system = 0 AND c.died_at_game_minutes IS NULL"
            " AND NOT EXISTS (SELECT 1 FROM employments e WHERE"
            " e.character_id = c.character_id AND"
            " e.ended_at_game_minutes IS NULL) LIMIT 1")
        if worker is None:
            self.skipTest("no unemployed adult in this world")
        cid = worker["character_id"]
        eid = self.store.next_id("EM", "employments",
                                 "employment_id")
        self.store.insert(
            "employments", employment_id=eid, character_id=cid,
            profession_id="construction_worker",
            tier=1, wage_per_month=10000,
            started_at_game_minutes=500, ended_at_game_minutes=None)
        made = li.seed_tool_rows(self.store, self.data, cid,
                                 "construction_worker", 500)
        row = self.store.row(
            "SELECT state FROM inventory_items"
            " WHERE item_instance_id = ?", (made[0],))
        state = json.loads(row["state"])
        state["condition"] = 0
        self.store.execute(
            "UPDATE inventory_items SET state = ?"
            " WHERE item_instance_id = ?",
            (json.dumps(state), made[0]))
        self.sim._monthly_social(29)
        after = self.store.row(
            "SELECT state FROM inventory_items"
            " WHERE item_instance_id = ?", (made[0],))
        self.assertEqual(json.loads(after["state"])["condition"], 90)


if __name__ == "__main__":
    unittest.main()
