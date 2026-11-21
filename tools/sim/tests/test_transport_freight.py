"""Session 07 — freight: Session 04 supply orders and intercity
trade flows become traceable physical shipments."""
import json
import unittest

from tools.sim import transport as transport_mod
from tools.sim.tests.common import rng
from tools.sim.tests.transportcommon import GM, transport_world


def _business(store, zone, category="retail"):
    pid = store.next_id("PR", "properties", "property_id")
    store.insert("properties", property_id=pid,
                 property_type="shop", district_id=zone,
                 address_label="Freight Test", tier=2,
                 status="owned", market_value=500000,
                 building_ref="test", unit_index=0)
    bid = store.next_id("BZ", "businesses", "business_id")
    store.insert("businesses", business_id=bid, name="Freight Test",
                 business_type="shop", owner_character_id="SYS-MARKET",
                 property_id=pid, balance_cached=0,
                 founded_at_game_minutes=GM)
    store.execute("UPDATE businesses SET category = ?, status ="
                  " 'active' WHERE business_id = ?", (category, bid))
    store.commit()
    return bid


class TestSupplyShipments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store, cls.data = transport_world()
        store = cls.store
        cls.seller = _business(store, "d1_industry",
                               category="manufacturing")
        cls.buyer = _business(store, "d1_market", category="retail")

    def test_order_becomes_a_traceable_shipment(self):
        store, data = self.store, self.data
        orders = [{"buyer": self.buyer, "seller": self.seller,
                   "good_id": "manufactured_goods", "units": 12,
                   "amount_ncr": 5000, "shipping_ncr": 340}]
        made = transport_mod.record_shipments(store, data, 1,
                                              30 * 1440, orders)
        self.assertEqual(len(made), 1)
        s = store.row("SELECT * FROM freight_shipments WHERE"
                      " shipment_id = ?", (made[0],))
        self.assertEqual(s["from_business_id"], self.seller)
        self.assertEqual(s["to_business_id"], self.buyer)
        self.assertEqual(s["good_id"], "manufactured_goods")
        self.assertEqual(s["units"], 12)
        self.assertEqual(s["freight_ncr"], 340)
        self.assertEqual(s["status"], "in_transit")
        self.assertGreater(s["arrives_at"], s["departed_at"])
        self.assertGreater(s["distance_km"], 0)
        valid = {r["segment_id"] for r in store.rows(
            "SELECT segment_id FROM road_segments")}
        segs = json.loads(s["segment_ids"])
        self.assertTrue(segs)
        self.assertTrue(all(x in valid for x in segs))
        self.assertIsNotNone(s["vehicle_id"])

    def test_shipment_is_delivered_after_its_arrival(self):
        store, data = self.store, self.data
        s = store.row("SELECT * FROM freight_shipments LIMIT 1")
        self.assertEqual(s["status"], "in_transit")
        # A later day's transport pass flips arrived shipments.
        day = s["arrives_at"] // 1440 + 1
        transport_mod.daily_pass(store, data, rng(), day,
                                 (day + 1) * 1440, "clear_day")
        s = store.row("SELECT * FROM freight_shipments WHERE"
                      " shipment_id = ?", (s["shipment_id"],))
        self.assertEqual(s["status"], "delivered")

    def test_congestion_delays_shipments(self):
        store, data = self.store, self.data
        # Load the network's record: heavy factors on day 3, which
        # _latest_factors reads for new shipments.
        store.set_world(day_index=3)
        for r in store.rows("SELECT segment_id FROM road_segments"):
            store.execute(
                "INSERT OR REPLACE INTO road_loads (day_index,"
                " segment_id, hour, vehicle_count, capacity_vph,"
                " congestion_factor) VALUES (3, ?, 10, 900, 700,"
                " 2.5)", (r["segment_id"],))
        store.commit()
        orders = [{"buyer": self.buyer, "seller": self.seller,
                   "good_id": "manufactured_goods", "units": 5,
                   "amount_ncr": 2000, "shipping_ncr": 120}]
        made = transport_mod.record_shipments(store, data, 2,
                                              60 * 1440, orders)
        self.assertEqual(len(made), 1)
        s = store.row("SELECT * FROM freight_shipments WHERE"
                      " shipment_id = ?", (made[0],))
        self.assertGreater(s["travel_min"], s["free_flow_min"])
        self.assertGreater(s["delay_min"], 0)


class TestTradeShipments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store, cls.data = transport_world()

    def test_trade_flow_crosses_the_bridge(self):
        store, data = self.store, self.data
        flows = [("shibnagar_town", "rupsha_city",
                  "agricultural_produce", 4200)]
        made = transport_mod.record_trade_shipments(
            store, data, 1, 30 * 1440, flows)
        self.assertEqual(len(made), 1)
        s = store.row("SELECT * FROM freight_shipments WHERE"
                      " shipment_id = ?", (made[0],))
        self.assertEqual(s["kind"], "trade_flow")
        self.assertEqual(s["from_city_id"], "shibnagar_town")
        self.assertEqual(s["to_city_id"], "rupsha_city")
        self.assertIn("RC-ROAD-1", json.loads(s["segment_ids"]))
        self.assertEqual(s["freight_ncr"], 0)  # tariff is S04's


if __name__ == "__main__":
    unittest.main()
