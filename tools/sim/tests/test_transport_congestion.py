"""Session 07 — traffic: congestion emerges from the day's own
vehicle trips; closures and road condition change routing."""
import json
import unittest

from tools.sim import transport as transport_mod
from tools.sim.tests.common import rng
from tools.sim.tests.transportcommon import (citizen, day_schedule,
                                             transport_world)


class TestCongestionEmergence(unittest.TestCase):
    """The same traveller on the same route: alone on day 0,
    then one of forty taxis in the same hour on day 1. The
    loaded day must be slower, and the load must be on record."""

    @classmethod
    def setUpClass(cls):
        cls.store, cls.data = transport_world()
        store, data = cls.store, cls.data
        mc = data.transport_config["mode_choice"]
        mc["walk_max_distance_m"] = 0
        mc["rickshaw_max_distance_m"] = 0
        citizen(store, profession_id="taxi_driver")  # the service
        cls.probe = citizen(store, zone="d1_riverfront",
                            profession_id="construction_worker",
                            balance=100000, first="Probe")
        day_schedule(store, cls.probe, 0, "d1_riverfront",
                     "d1_industry")
        transport_mod.daily_pass(store, data, rng(), 0, 1440,
                                 "clear_day")
        # Day 1: thirty-nine more travellers, same OD, same hour.
        for i in range(39):
            cid = citizen(store, zone="d1_riverfront",
                          profession_id="construction_worker",
                          balance=100000, first=f"Loader{i}")
            day_schedule(store, cid, 1, "d1_riverfront",
                         "d1_industry")
        day_schedule(store, cls.probe, 1, "d1_riverfront",
                     "d1_industry")
        transport_mod.daily_pass(store, data, rng(), 1, 2 * 1440,
                                 "clear_day")

    @classmethod
    def tearDownClass(cls):
        mc = cls.data.transport_config["mode_choice"]
        mc["walk_max_distance_m"] = 1200
        mc["rickshaw_max_distance_m"] = 3500

    def test_loaded_day_is_slower(self):
        store = self.store
        t0 = store.row("SELECT * FROM trips WHERE character_id = ?"
                       " AND day_index = 0 AND purpose = 'work'",
                       (self.probe,))
        t1 = store.row("SELECT * FROM trips WHERE character_id = ?"
                       " AND day_index = 1 AND purpose = 'work'",
                       (self.probe,))
        self.assertEqual(t0["mode"], "taxi")
        self.assertEqual(t1["mode"], "taxi")
        self.assertEqual(t0["segment_ids"], t1["segment_ids"])
        self.assertGreater(t1["travel_min"], t0["travel_min"])

    def test_load_is_recorded_per_segment_hour(self):
        store = self.store
        t1 = store.row("SELECT * FROM trips WHERE character_id = ?"
                       " AND day_index = 1 AND purpose = 'work'",
                       (self.probe,))
        segs = json.loads(t1["segment_ids"])
        hour = (t1["depart_minute"] % 1440) // 60
        loaded = store.rows(
            "SELECT * FROM road_loads WHERE day_index = 1 AND hour"
            " = ? AND segment_id IN (%s)" % ",".join(
                "?" for _ in segs), [hour] + segs)
        self.assertTrue(loaded)
        self.assertTrue(any(r["vehicle_count"] >= 30
                            for r in loaded))
        self.assertTrue(any(r["congestion_factor"] > 1.1
                            for r in loaded))


class TestClosuresAndCondition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store, cls.data = transport_world()

    def test_closure_forces_a_detour(self):
        store, data = self.store, self.data
        net = transport_mod.Network(store, data, 0)
        classes = {"arterial", "collector", "local"}
        base = net.zone_route("rupsha_city", "d1_midtown",
                              "d1_civic", classes)
        self.assertIsNotNone(base)
        # Close each route segment in turn until one leaves a
        # detour: that segment's closure must change the route.
        detour = None
        for sid in base["segment_ids"]:
            store.execute("UPDATE road_segments SET closed = 1"
                          " WHERE segment_id = ?", (sid,))
            net2 = transport_mod.Network(store, data, 0)
            alt = net2.zone_route("rupsha_city", "d1_midtown",
                                  "d1_civic", classes)
            store.execute("UPDATE road_segments SET closed = 0"
                          " WHERE segment_id = ?", (sid,))
            if alt is not None and sid not in alt["segment_ids"]:
                detour = (sid, alt)
                break
        self.assertIsNotNone(detour,
                             "no closable segment had a detour")

    def test_critical_condition_is_impassable(self):
        store, data = self.store, self.data
        net = transport_mod.Network(store, data, 0)
        sid = store.row("SELECT segment_id FROM road_segments"
                        " LIMIT 1")["segment_id"]
        self.assertFalse(net.impassable(sid))
        store.execute("UPDATE road_segments SET condition = 10"
                      " WHERE segment_id = ?", (sid,))
        net2 = transport_mod.Network(store, data, 0)
        self.assertTrue(net2.impassable(sid))

    def test_poor_condition_slows_travel(self):
        store, data = self.store, self.data
        net = transport_mod.Network(store, data, 0)
        classes = {"arterial", "collector", "local"}
        route = net.zone_route("rupsha_city", "d1_midtown",
                               "d1_industry", classes)
        self.assertIsNotNone(route)
        sid = route["segment_ids"][0]
        free = route["free_min"]
        # Degrade every segment of the route: the same route must
        # take longer under the condition factor.
        for s in route["segment_ids"]:
            store.execute("UPDATE road_segments SET condition = 30"
                          " WHERE segment_id = ?", (s,))
        net2 = transport_mod.Network(store, data, 0)
        slowed = transport_mod.travel_time(route, {}, net2, 8)
        self.assertGreater(slowed, free)


if __name__ == "__main__":
    unittest.main()
