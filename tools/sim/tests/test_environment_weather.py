"""Session 08 — regional weather, seasons, day/night."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))

from tools.sim import environment as env_mod  # noqa: E402
from tools.sim.tests.common import rng  # noqa: E402
from tools.sim.tests.envcommon import env_world  # noqa: E402


class TestSetup(unittest.TestCase):
    def test_setup_idempotent_and_seeded(self):
        store, d = env_world()
        self.assertTrue(env_mod.is_setup(store))
        again = env_mod.setup_environment(store, d, 480)
        self.assertEqual(again, {"already": True})
        waters = store.rows("SELECT * FROM env_water_state")
        self.assertEqual(len(waters), 2)
        soils = store.row("SELECT COUNT(*) AS n FROM env_soil")["n"]
        parcels = store.row(
            "SELECT COUNT(*) AS n FROM land_parcels WHERE"
            " zoning_category = 'agricultural'")["n"]
        self.assertEqual(soils, parcels)
        self.assertGreater(parcels, 0)
        self.assertGreater(
            store.row("SELECT COUNT(*) AS n FROM env_vegetation")["n"],
            0)


class TestRegionalWeather(unittest.TestCase):
    def test_weather_recorded_for_both_regions(self):
        store, d = env_world()
        r = rng()
        for day in range(30):
            env_mod.daily_pass(store, d, r, day, (day + 1) * 1440)
        for cid in ("rupsha_city", "shibnagar_town"):
            n = store.row("SELECT COUNT(*) AS n FROM env_weather"
                          " WHERE region_id = ?", (cid,))["n"]
            self.assertEqual(n, 30)
            bad = store.row(
                "SELECT COUNT(*) AS n FROM env_weather WHERE"
                " region_id = ? AND (precip_mm < 0 OR temp_day_c <"
                " -10 OR temp_day_c > 50)", (cid,))["n"]
            self.assertEqual(bad, 0)

    def test_regions_differ(self):
        store, d = env_world()
        r = rng()
        differ = 0
        for day in range(60):
            a = env_mod.weather_for_region(store, d, r, "rupsha_city",
                                           day)
            b = env_mod.weather_for_region(store, d, r,
                                           "shibnagar_town", day)
            if a["preset_id"] != b["preset_id"] \
                    or a["precip_mm"] != b["precip_mm"] \
                    or a["temp_day_c"] != b["temp_day_c"]:
                differ += 1
        self.assertGreater(differ, 10)

    def test_weather_persists_identically(self):
        store, d = env_world()
        r = rng()
        first = env_mod.weather_for_region(store, d, r,
                                           "shibnagar_town", 7)
        second = env_mod.weather_for_region(store, d, r,
                                            "shibnagar_town", 7)
        self.assertEqual(first["preset_id"], second["preset_id"])
        self.assertEqual(first["precip_mm"], second["precip_mm"])
        self.assertEqual(first["temp_day_c"], second["temp_day_c"])

    def test_monsoon_wetter_than_winter(self):
        store, d = env_world()
        r = rng()
        winter = monsoon = 0.0
        for day in range(0, 60):
            w = env_mod.weather_for_region(store, d, r,
                                           "shibnagar_town", day)
            winter += w["precip_mm"]
        for day in range(150, 210):
            w = env_mod.weather_for_region(store, d, r,
                                           "shibnagar_town", day)
            monsoon += w["precip_mm"]
        self.assertGreater(monsoon, winter)


class TestSeasonsDaylight(unittest.TestCase):
    def test_seasons_tile_and_differ(self):
        store, d = env_world()
        self.assertEqual(env_mod.season_for_day(d, 10)["id"], "winter")
        self.assertEqual(env_mod.season_for_day(d, 180)["id"], "monsoon")
        self.assertEqual(env_mod.season_for_day(d, 300)["id"],
                         "late_autumn")

    def test_daylight_varies_by_season(self):
        _store, d = env_world()
        w_sunrise, w_sunset = env_mod.daylight(d, 350)   # winter
        s_sunrise, s_sunset = env_mod.daylight(d, 100)   # summer-ish
        self.assertGreater(w_sunrise, s_sunrise)
        self.assertLess(w_sunset, s_sunset)
        self.assertGreater(s_sunset - s_sunrise, w_sunset - w_sunrise)


if __name__ == "__main__":
    unittest.main()
