"""Session 07 — trips: schedule journeys, mode choice, taxi
fares through the ledger, bus boardings, clinic + emergency
journeys, intercity travel."""
import json
import unittest

from tools.sim import transport as transport_mod
from tools.sim.tests.common import rng
from tools.sim.tests.transportcommon import (GM, citizen,
                                             day_schedule,
                                             transport_world)


class TestScheduleTrips(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store, cls.data = transport_world()

    def test_commute_trips_recorded_with_valid_routes(self):
        store, data = self.store, self.data
        worker = citizen(store, zone="d1_midtown",
                         profession_id="teacher")
        day_schedule(store, worker, 0, "d1_midtown", "d1_civic")
        stats = transport_mod.daily_pass(store, data, rng(), 0,
                                         1440, "clear_day")
        self.assertGreaterEqual(stats["trips"], 2)
        trips = store.rows("SELECT * FROM trips WHERE character_id"
                           " = ? ORDER BY depart_minute", (worker,))
        self.assertEqual(len(trips), 2)
        self.assertEqual(trips[0]["origin_zone"], "d1_midtown")
        self.assertEqual(trips[0]["destination_zone"], "d1_civic")
        self.assertEqual(trips[0]["purpose"], "work")
        self.assertEqual(trips[1]["purpose"], "home")
        valid = {r["segment_id"] for r in store.rows(
            "SELECT segment_id FROM road_segments")}
        for t in trips:
            segs = json.loads(t["segment_ids"])
            self.assertTrue(segs)
            self.assertTrue(all(s in valid for s in segs))
            self.assertGreater(t["distance_m"], 0)
            self.assertGreater(t["arrive_minute"], t["depart_minute"])
            self.assertEqual(t["status"], "completed")

    def test_daily_pass_is_restart_safe(self):
        store, data = self.store, self.data
        again = transport_mod.daily_pass(store, data, rng(), 0,
                                         1440, "clear_day")
        self.assertEqual(again, {"already_recorded": True})


class TestTaxiFare(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store, cls.data = transport_world()

    def test_fare_formula_and_surge(self):
        data = self.data
        # base 60 + 25/km at prices.json taxi_fares.
        self.assertEqual(transport_mod.taxi_fare(
            data, 2000, "clear_day", 600), 110)
        # Rain surge x1.5.
        self.assertEqual(transport_mod.taxi_fare(
            data, 2000, "rain", 600), 165)
        # Night surge x1.5.
        self.assertEqual(transport_mod.taxi_fare(
            data, 2000, "clear_day", 23 * 60), 165)

    def test_taxi_trip_charges_the_ledger(self):
        store, data = self.store, self.data
        mc = data.transport_config["mode_choice"]
        old_walk, old_rick = mc["walk_max_distance_m"], \
            mc["rickshaw_max_distance_m"]
        mc["walk_max_distance_m"] = 0
        mc["rickshaw_max_distance_m"] = 0
        try:
            citizen(store, profession_id="taxi_driver")  # service
            rider = citizen(store, zone="d1_riverfront",
                            profession_id="construction_worker",
                            balance=100000)
            day_schedule(store, rider, 0, "d1_riverfront",
                         "d1_industry")
            before = store.balance(rider)
            transport_mod.daily_pass(store, data, rng(), 0, 1440,
                                     "clear_day")
            trips = store.rows("SELECT * FROM trips WHERE"
                               " character_id = ? AND purpose ="
                               " 'work'", (rider,))
            self.assertEqual(len(trips), 1)
            t = trips[0]
            self.assertEqual(t["mode"], "taxi")
            self.assertEqual(t["fare_basis"], "prices_taxi_fares")
            expected = transport_mod.taxi_fare(
                data, t["distance_m"], "clear_day",
                t["depart_minute"])
            self.assertEqual(t["fare_ncr"], expected)
            # Both legs are taxi hires: the ledger carries one
            # fare row per trip and the balance fell by their sum.
            rows = store.rows("SELECT * FROM economy_ledger WHERE"
                              " reason_code = 'taxi_fare' AND"
                              " from_character_id = ?", (rider,))
            self.assertEqual(len(rows), 2)
            self.assertTrue(any(r["amount"] == expected
                                for r in rows))
            self.assertEqual(store.balance(rider),
                             before - sum(r["amount"] for r in rows))
            self.assertEqual(store.ledger_sum_check(), [])
        finally:
            mc["walk_max_distance_m"] = old_walk
            mc["rickshaw_max_distance_m"] = old_rick


class TestBusBoarding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store, cls.data = transport_world()

    def test_bus_trip_and_run_recorded(self):
        store, data = self.store, self.data
        mc = data.transport_config["mode_choice"]
        old_walk = mc["walk_max_distance_m"]
        mc["walk_max_distance_m"] = 0
        try:
            rider = citizen(store, zone="d1_midtown",
                            profession_id="teacher")
            day_schedule(store, rider, 0, "d1_midtown", "d1_civic")
            transport_mod.daily_pass(store, data, rng(), 0, 1440,
                                     "clear_day")
            trips = store.rows("SELECT * FROM trips WHERE"
                               " character_id = ? AND purpose ="
                               " 'work'", (rider,))
            self.assertEqual(len(trips), 1)
            self.assertEqual(trips[0]["mode"], "bus")
            self.assertEqual(trips[0]["route_id"], "BUS-RUPSHA-LOOP")
            self.assertEqual(trips[0]["fare_basis"],
                             "monthly_transport_line")
            run = store.row("SELECT * FROM transit_runs WHERE"
                            " route_id = 'BUS-RUPSHA-LOOP' AND"
                            " day_index = 0")
            self.assertIsNotNone(run)
            self.assertGreaterEqual(run["boardings"], 1)
            self.assertGreater(run["capacity"], 0)
        finally:
            mc["walk_max_distance_m"] = old_walk


class TestHealthJourneys(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store, cls.data = transport_world(with_humandev=True)

    def test_clinic_trip_and_emergency_referral(self):
        store, data = self.store, self.data
        patient = citizen(store, zone="d1_midtown")
        fac = store.row("SELECT * FROM healthcare_facilities WHERE"
                        " city_id = 'rupsha_city'")
        self.assertIsNotNone(fac)
        vid = store.next_id("PV", "patient_visits", "visit_id")
        store.insert("patient_visits", visit_id=vid,
                     character_id=patient, facility_id=fac[
                         "facility_id"], visit_type="condition",
                     stage="registered", registered_day=0)
        aid = store.next_id("HA", "hospital_admissions",
                            "admission_id")
        store.insert("hospital_admissions", admission_id=aid,
                     visit_id=vid, character_id=patient,
                     facility_id=fac["facility_id"],
                     referred_off_district=1, transfer_days=2,
                     admitted_day=0)
        store.commit()
        transport_mod.daily_pass(store, data, rng(), 0, 1440,
                                 "clear_day")
        clinic = store.rows("SELECT * FROM trips WHERE character_id"
                            " = ? AND purpose = 'healthcare'",
                            (patient,))
        self.assertEqual(len(clinic), 1)
        self.assertEqual(clinic[0]["destination_zone"], "d1_civic")
        amb = store.rows("SELECT * FROM trips WHERE character_id"
                         " = ? AND purpose = 'emergency'", (patient,))
        self.assertEqual(len(amb), 1)
        self.assertEqual(amb[0]["mode"], "ambulance")
        self.assertEqual(amb[0]["destination_zone"], "off_district")
        self.assertEqual(json.loads(amb[0]["details"])["admission_id"],
                         aid)
        # Priority: the ambulance beats the same route at ordinary
        # speed — its travel time is at most the free-flow time.
        self.assertLessEqual(amb[0]["travel_min"],
                             amb[0]["free_flow_min"])


class TestIntercity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store, cls.data = transport_world()

    def test_ferry_serves_ghat_to_ghat(self):
        # No profession's schedule generates a ghat-to-ghat leg
        # organically (the ghat zones host no workplace), so the
        # journey is fabricated as a schedule: riverfront home,
        # an errand at the Shibnagar ghat, home again.
        store, data = self.store, self.data
        from tools.sim.tests.transportcommon import set_schedule
        traveller = citizen(store, zone="d1_riverfront")
        set_schedule(store, traveller, 1, [
            (0, 600, "home", "d1_riverfront"),
            (600, 900, "errand", "c2_transport"),
            (900, 1440, "home", "d1_riverfront")])
        transport_mod.daily_pass(store, data, rng(), 1, 2 * 1440,
                                 "clear_day")
        trips = store.rows("SELECT * FROM trips WHERE character_id"
                           " = ? ORDER BY depart_minute",
                           (traveller,))
        self.assertEqual(len(trips), 2)
        self.assertTrue(all(t["mode"] == "ferry" for t in trips))
        self.assertTrue(all(t["route_id"] == "RC-FERRY-1"
                            for t in trips))
        self.assertEqual(trips[0]["travel_min"], 45)  # config

    def test_commuter_trip_crosses_the_bridge(self):
        store, data = self.store, self.data
        commuter = citizen(store, zone="c2_residential",
                           profession_id="teacher")
        day_schedule(store, commuter, 0, "c2_residential", "d1_civic")
        transport_mod.daily_pass(store, data, rng(), 0, 1440,
                                 "clear_day")
        trips = store.rows("SELECT * FROM trips WHERE character_id"
                           " = ? AND purpose = 'work'", (commuter,))
        self.assertEqual(len(trips), 1)
        t = trips[0]
        self.assertEqual(t["mode"], "intercity_bus")
        self.assertIn("RC-ROAD-1", json.loads(t["segment_ids"]))
        self.assertGreater(t["distance_m"], 3000)


if __name__ == "__main__":
    unittest.main()
