"""Session 07 acceptance — the spec's 12 criteria in real
long-running worlds, plus restart identity and determinism with
the transport layer live.

Criteria map: (1) networks connect — intercity trips + bridge
shipments exist; (2) vehicles follow valid routes — every trip's
segments exist; (3) congestion emerges — max factor > 1 from the
world's own trips (mechanism proof at corridor scale is in
test_transport_congestion); (4) transit operates — boardings and
runs recorded; (5) passenger journeys recorded; (6) freight
deliveries function — shipments delivered; (7) fuel consumed —
vehicle tanks/odometers move; (8) emergency vehicles navigate —
the machinery is unit-proven in test_transport_trips (referrals
are rare organically); here healthcare journeys stand as the
organic evidence; (9) closures affect routing — unit-proven in
test_transport_congestion; (10) transport costs reach accounts —
fares in the ledger + purchases; (11) environmental records —
fuel/emissions in the monthly statistics; (12) previous sessions
functional — integrity checks below.
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))

from tools.sim import finance  # noqa: E402
from tools.sim.engine import Simulation  # noqa: E402


def make_sim(population, days, seed="s07-acceptance"):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    sim = Simulation(path, seed=seed)
    sim.generate_population(population)
    if days:
        sim.run_days(days)
    return sim, path


class TestSession07LongRun(unittest.TestCase):
    def test_population_world_criteria(self):
        sim, path = make_sim(120, 200)
        try:
            store = sim.store
            s = sim.summary()
            tr = s["transport"]
            # 5. Passenger journeys recorded, at scale.
            self.assertGreater(tr["trips_total"], 10000)
            self.assertIn("walk", tr["trips_by_mode"])
            # 4. Public transportation operates.
            self.assertGreater(tr["boardings_total"], 0)
            runs = store.row("SELECT COUNT(*) AS n FROM"
                             " transit_runs")["n"]
            self.assertGreater(runs, 0)
            # 2. Every recorded route uses real segments.
            valid = {r["segment_id"] for r in store.rows(
                "SELECT segment_id FROM road_segments")}
            valid |= {"RC-ROAD-1", "RC-FERRY-1"}
            bad = 0
            for t in store.rows("SELECT segment_ids FROM trips"):
                if any(x not in valid
                       for x in json.loads(t["segment_ids"])):
                    bad += 1
            self.assertEqual(bad, 0)
            # 1. Networks connect: bridge crossings on record
            #    (intercity trips and/or trade shipments).
            crossings = store.row(
                "SELECT COUNT(*) AS n FROM trips WHERE"
                " segment_ids LIKE '%RC-ROAD-1%'")["n"]
            crossings += store.row(
                "SELECT COUNT(*) AS n FROM freight_shipments WHERE"
                " segment_ids LIKE '%RC-ROAD-1%'")["n"]
            self.assertGreater(crossings, 0)
            # 3. Congestion emerged from the world's own trips.
            self.assertGreater(tr["max_congestion_factor"], 1.0)
            # 6. Freight deliveries complete.
            self.assertGreater(tr["shipments_total"], 0)
            self.assertGreater(tr["shipments_delivered"], 0)
            # 7. Fuel is consumed and vehicles move.
            moved = store.row(
                "SELECT COUNT(*) AS n FROM vehicles WHERE"
                " odometer_km > 0")["n"]
            self.assertGreater(moved, 0)
            # 10. Transport costs reach accounts: fares were paid
            #     through the ledger; vehicles were bought.
            self.assertGreater(tr["fares_total_ncr"], 0)
            fare_rows = store.row(
                "SELECT COUNT(*) AS n FROM economy_ledger WHERE"
                " reason_code = 'taxi_fare'")["n"]
            self.assertGreater(fare_rows, 0)
            # 11. Environmental records exist in the statistics.
            stats = store.rows("SELECT statistics FROM"
                               " transport_statistics WHERE scope"
                               " = 'national'")
            self.assertTrue(stats)
            latest = json.loads(stats[-1]["statistics"])
            self.assertGreater(latest["fuel_litres"], 0)
            self.assertGreater(latest["emissions_kg"], 0)
            # Healthcare journeys happen organically (criterion
            # 8's machinery is unit-proven).
            health_trips = store.row(
                "SELECT COUNT(*) AS n FROM trips WHERE purpose ="
                " 'healthcare'")["n"]
            self.assertGreater(health_trips, 0)
            # 12. Previous sessions remain functional.
            self.assertEqual(s["ledger_mismatches"], 0)
            self.assertEqual(store.ledger_sum_check(), [])
            self.assertEqual(finance.verify_conservation(store), [])
            self.assertTrue(s["government"])
            self.assertTrue(s["humandev"])
        finally:
            sim.close()
            os.remove(path)

    def test_restart_identity(self):
        whole, path_a = make_sim(80, 90, seed="s07-restart")
        try:
            expected = whole.summary()
        finally:
            whole.close()
            os.remove(path_a)
        sim, path = make_sim(80, 45, seed="s07-restart")
        try:
            sim.close()
            resumed = Simulation(path, seed="s07-restart")
            try:
                resumed.run_days(45)
                self.assertEqual(resumed.summary(), expected)
            finally:
                resumed.close()
        finally:
            os.remove(path)

    def test_determinism(self):
        a, pa = make_sim(60, 45, seed="s07-determinism")
        b, pb = make_sim(60, 45, seed="s07-determinism")
        try:
            self.assertEqual(a.summary(), b.summary())
        finally:
            a.close()
            b.close()
            os.remove(pa)
            os.remove(pb)


if __name__ == "__main__":
    unittest.main()
