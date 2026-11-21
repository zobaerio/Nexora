"""Session 08 — hydrology, water–city interaction, flooding."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))

from tools.sim import environment as env_mod  # noqa: E402
from tools.sim.tests.common import rng  # noqa: E402
from tools.sim.tests.envcommon import env_world, seed_weather  # noqa: E402
from tools.sim.tests.transportcommon import citizen  # noqa: E402

RUP = "rupsha_city"


def _river(store, cid=RUP):
    return store.row("SELECT river_level_m FROM env_water_state"
                     " WHERE city_id = ?", (cid,))["river_level_m"]


class TestHydrology(unittest.TestCase):
    def test_rainfall_changes_water_accumulation(self):
        store, d = env_world()
        r = rng()
        seed_weather(store, RUP, 0, precip_mm=0.0)
        seed_weather(store, "shibnagar_town", 0, precip_mm=0.0)
        env_mod.daily_pass(store, d, r, 0, 1440)
        dry_river = _river(store)
        dry_storage = store.row(
            "SELECT surface_storage_mm FROM env_water_state WHERE"
            " city_id = ?", (RUP,))["surface_storage_mm"]
        seed_weather(store, RUP, 1, precip_mm=200.0)
        seed_weather(store, "shibnagar_town", 1, precip_mm=0.0)
        env_mod.daily_pass(store, d, r, 1, 2880)
        self.assertGreater(_river(store), dry_river)
        wet_storage = store.row(
            "SELECT surface_storage_mm FROM env_water_state WHERE"
            " city_id = ?", (RUP,))["surface_storage_mm"]
        self.assertGreater(wet_storage, dry_storage)

    def test_drainage_capacity_reduces_rise(self):
        # Two identical worlds, one with its drainage network
        # zeroed: the undrained city must rise higher on the same
        # rain — the Session 03 network measurably interacts.
        rises = {}
        for label, drain in (("drained", True), ("undrained", False)):
            store, d = env_world()
            r = rng()
            if not drain:
                store.execute(
                    "UPDATE infrastructure_state SET capacity_units"
                    " = 0 WHERE network = 'drainage'")
                store.commit()
            seed_weather(store, RUP, 0, precip_mm=0.0)
            seed_weather(store, "shibnagar_town", 0, precip_mm=0.0)
            env_mod.daily_pass(store, d, r, 0, 1440)
            before = _river(store)
            seed_weather(store, RUP, 1, precip_mm=200.0)
            seed_weather(store, "shibnagar_town", 1, precip_mm=0.0)
            env_mod.daily_pass(store, d, r, 1, 2880)
            rises[label] = _river(store) - before
        self.assertGreater(rises["undrained"], rises["drained"])


class TestFlooding(unittest.TestCase):
    def _flood_world(self):
        store, d = env_world()
        r = rng()
        # A household resident in the exposed riverfront zone.
        cid = citizen(store, zone="d1_riverfront", first="River")
        # Fund the treasury so recovery repairs can actually run.
        store.transfer("SYS-MARKET", "SYS-CITY", 1000000,
                       "seed_grant", 480,
                       transfer_key="seed:flood-treasury")
        store.commit()
        return store, d, r, cid

    def test_extreme_rain_floods_exposed_ground(self):
        store, d, r, _cid = self._flood_world()
        zones = env_mod.exposed_zones(store, d, RUP)
        self.assertIn("d1_riverfront", zones)
        parcels = env_mod.exposed_parcels(store, d, RUP)
        self.assertGreater(len(parcels), 0)
        watched = next(p["building_id"] for p in parcels
                       if p["building_id"])
        before = store.row("SELECT condition FROM building_state"
                           " WHERE building_id = ?",
                           (watched,))["condition"]
        for day in range(6):
            seed_weather(store, RUP, day, precip_mm=320.0)
            seed_weather(store, "shibnagar_town", day, precip_mm=0.0)
            env_mod.daily_pass(store, d, r, day, (day + 1) * 1440)
        floods = store.rows("SELECT * FROM disaster_events WHERE"
                            " disaster_type = 'flood'")
        self.assertGreaterEqual(len(floods), 1)
        closed = store.row("SELECT COUNT(*) AS n FROM road_segments"
                           " WHERE closed = 1")["n"]
        self.assertGreater(closed, 0)
        after = store.row("SELECT condition FROM building_state"
                          " WHERE building_id = ?",
                          (watched,))["condition"]
        self.assertLess(after, before)
        displaced = store.row(
            "SELECT COUNT(*) AS n FROM disaster_impacts WHERE kind"
            " = 'household_displaced'")["n"]
        self.assertGreaterEqual(displaced, 1)

    def test_flood_recovers_when_river_falls(self):
        store, d, r, _cid = self._flood_world()
        for day in range(6):
            seed_weather(store, RUP, day, precip_mm=320.0)
            seed_weather(store, "shibnagar_town", day, precip_mm=0.0)
            env_mod.daily_pass(store, d, r, day, (day + 1) * 1440)
        self.assertGreaterEqual(
            store.row("SELECT COUNT(*) AS n FROM disaster_events"
                      " WHERE disaster_type = 'flood'")["n"], 1)
        # Dry days: the river falls, the episode ends, repairs run.
        recovered = False
        for day in range(6, 120):
            seed_weather(store, RUP, day, precip_mm=0.0)
            seed_weather(store, "shibnagar_town", day, precip_mm=0.0)
            env_mod.daily_pass(store, d, r, day, (day + 1) * 1440)
            row = store.row("SELECT status FROM disaster_events"
                            " WHERE disaster_type = 'flood' ORDER BY"
                            " started_day LIMIT 1")
            if row and row["status"] == "recovered":
                recovered = True
                break
        self.assertTrue(recovered)
        still_closed = store.row(
            "SELECT COUNT(*) AS n FROM disaster_impacts di JOIN"
            " road_segments rs ON rs.segment_id = di.ref_id WHERE"
            " di.kind = 'road_closure' AND rs.closed = 1")["n"]
        self.assertEqual(still_closed, 0)


if __name__ == "__main__":
    unittest.main()
