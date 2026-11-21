"""Session 07 — vehicles: fleets, taxi cabs, purchases, fuel,
maintenance."""
import unittest

from tools.sim import transport as transport_mod
from tools.sim.tests.common import rng
from tools.sim.tests.transportcommon import (GM, citizen,
                                             transport_world)


class TestSetup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store, cls.data = transport_world()

    def test_routes_and_fleets_seeded(self):
        store = self.store
        routes = {r["route_id"] for r in store.rows(
            "SELECT route_id FROM transit_routes")}
        self.assertEqual(routes, {"BUS-RUPSHA-LOOP", "BUS-SHIBNAGAR",
                                  "RC-FERRY-1"})
        buses = store.row("SELECT COUNT(*) AS n FROM vehicles WHERE"
                          " vehicle_type = 'bus' AND status ="
                          " 'active'")["n"]
        self.assertEqual(buses, 5)  # 3 Rupsha + 2 Shibnagar
        carriers = store.row("SELECT COUNT(*) AS n FROM vehicles"
                             " WHERE vehicle_type = 'truck' AND"
                             " owner_character_id = 'SYS-MARKET'")["n"]
        self.assertEqual(carriers, 4)  # 2 per city

    def test_setup_idempotent(self):
        again = transport_mod.setup_transport(self.store, self.data,
                                              GM)
        self.assertEqual(again, {"already_setup": True})


class TestTaxiCabs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store, cls.data = transport_world()

    def test_driver_gets_rented_cab_and_returns_it(self):
        store = self.store
        driver = citizen(store, profession_id="taxi_driver")
        created = transport_mod._ensure_taxi_cabs(store, self.data,
                                                  GM)
        self.assertEqual(created, 1)
        cab = store.row("SELECT * FROM vehicles WHERE"
                        " operator_character_id = ?", (driver,))
        self.assertIsNotNone(cab)
        self.assertEqual(cab["vehicle_type"], "taxi")
        self.assertEqual(cab["owner_character_id"], "SYS-MARKET")
        self.assertEqual(cab["acquisition"], "rental")
        # Leaving the profession returns the cab.
        store.execute("UPDATE employments SET"
                      " ended_at_game_minutes = ? WHERE"
                      " character_id = ?", (GM + 100, driver))
        transport_mod._ensure_taxi_cabs(store, self.data, GM + 100)
        cab = store.row("SELECT * FROM vehicles WHERE"
                        " operator_character_id = ?", (driver,))
        self.assertEqual(cab["status"], "returned")


class TestPurchaseSweep(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store, cls.data = transport_world()

    def test_rich_citizen_buys_at_prices_json_price(self):
        store, data = self.store, self.data
        data.transport_config["vehicle_purchase"]["monthly_chance"] \
            = 1.0
        try:
            buyer = citizen(store, profession_id="software_developer",
                            balance=200000)
            before = store.balance(buyer)
            bought = transport_mod._purchase_sweep(
                store, data, rng(), 1, GM + 30 * 1440)
            self.assertEqual(len(bought), 1)
            v = store.row("SELECT * FROM vehicles WHERE vehicle_id"
                          " = ?", (bought[0],))
            # 200,000 supports a motorbike (120,000 x 1.25) but
            # not a small car (450,000 x 1.25).
            self.assertEqual(v["vehicle_type"], "motorbike")
            self.assertEqual(v["owner_character_id"], buyer)
            self.assertEqual(v["acquisition"], "purchase")
            price = next(x["price_ncr"] for x in
                         data.prices["vehicles"]
                         if x["id"] == "motorbike")
            self.assertEqual(store.balance(buyer), before - price)
            self.assertEqual(store.ledger_sum_check(), [])
        finally:
            data.transport_config["vehicle_purchase"][
                "monthly_chance"] = 0.25

    def test_poor_citizen_buys_nothing(self):
        store, data = self.store, self.data
        data.transport_config["vehicle_purchase"]["monthly_chance"] \
            = 1.0
        try:
            citizen(store, profession_id="chef", balance=5000)
            bought = transport_mod._purchase_sweep(
                store, data, rng(), 1, GM + 30 * 1440)
            self.assertEqual(bought, [])
        finally:
            data.transport_config["vehicle_purchase"][
                "monthly_chance"] = 0.25


class TestFuelAndMaintenance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store, cls.data = transport_world()

    def test_fuel_consumption_from_vehicles_json(self):
        # car_small burns 7.0 litres per 100 km (vehicles.json).
        trip = {"mode": "own_vehicle", "vehicle_type": "car_small",
                "distance_m": 100000}
        self.assertEqual(transport_mod._fuel_for(self.data, trip),
                         7.0)
        # A bicycle burns nothing.
        trip = {"mode": "own_vehicle", "vehicle_type": "bicycle",
                "distance_m": 100000}
        self.assertEqual(transport_mod._fuel_for(self.data, trip),
                         0.0)

    def test_worn_vehicle_is_serviced(self):
        store, data = self.store, self.data
        vid = transport_mod._new_vehicle(
            store, data, "motorbike", GM,
            owner_character_id="SYS-MARKET", city_id="rupsha_city",
            home_zone="d1_midtown", current_zone="d1_midtown",
            acquisition="fleet")
        store.execute("UPDATE vehicles SET condition = 55 WHERE"
                      " vehicle_id = ?", (vid,))
        tid = store.next_id("TR", "trips", "trip_id")
        store.insert("trips", trip_id=tid, character_id=None,
                     day_index=5, purpose="work",
                     origin_zone="d1_midtown",
                     destination_zone="d1_civic", mode="own_vehicle",
                     vehicle_id=vid, segment_ids="[]",
                     distance_m=2000, depart_minute=5 * 1440 + 480,
                     free_flow_min=5, travel_min=6,
                     arrive_minute=5 * 1440 + 486)
        serviced = transport_mod._maintenance_pass(store, data, 1,
                                                   GM + 30 * 1440)
        self.assertEqual(serviced, 1)
        v = store.row("SELECT * FROM vehicles WHERE vehicle_id = ?",
                      (vid,))
        self.assertEqual(v["condition"], 90.0)
        ev = store.row("SELECT * FROM vehicle_events WHERE"
                       " vehicle_id = ? AND kind = 'maintenance'",
                       (vid,))
        self.assertIsNotNone(ev)


if __name__ == "__main__":
    unittest.main()
