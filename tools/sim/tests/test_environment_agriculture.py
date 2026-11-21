"""Session 08 — agriculture cycles and soil."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))

from tools.sim import environment as env_mod  # noqa: E402
from tools.sim.tests.common import rng  # noqa: E402
from tools.sim.tests.envcommon import env_world, seed_weather  # noqa: E402


def _seed_month_rain(store, month_index, mm_per_day=8.0):
    lo = (month_index - 1) * 30
    for day in range(lo, lo + 30):
        for cid in ("rupsha_city", "shibnagar_town"):
            seed_weather(store, cid, day, precip_mm=mm_per_day)


def _set_soil(store, moisture, fertility=0.8):
    store.execute("UPDATE env_soil SET moisture = ?, fertility = ?",
                  (moisture, fertility))
    store.commit()


class TestAgriculture(unittest.TestCase):
    def test_planting_follows_season(self):
        store, d = env_world()
        r = rng()
        _seed_month_rain(store, 6)
        # Month 6 ends on day 179 — monsoon: aman paddy plants.
        env_mod.monthly_pass(store, d, r, 6, 180 * 1440)
        planted = store.row("SELECT COUNT(*) AS n FROM env_crops"
                            " WHERE status = 'growing'")["n"]
        parcels = store.row(
            "SELECT COUNT(*) AS n FROM land_parcels WHERE"
            " zoning_category = 'agricultural'")["n"]
        self.assertEqual(planted, parcels)
        crops = {row["crop_id"] for row in
                 store.rows("SELECT crop_id FROM env_crops")}
        self.assertEqual(crops, {"aman_paddy"})

    def test_harvest_enters_market_inventory(self):
        store, d = env_world()
        r = rng()
        _set_soil(store, 0.65)
        _seed_month_rain(store, 6)
        env_mod.monthly_pass(store, d, r, 6, 180 * 1440)
        for m in (7, 8, 9):
            _set_soil(store, 0.65)
            _seed_month_rain(store, m)
            env_mod.monthly_pass(store, d, r, m, (m * 30 + 30) * 1440)
        harvested = store.row(
            "SELECT COUNT(*) AS n, COALESCE(SUM(harvest_units), 0)"
            " AS units FROM env_crops WHERE status = 'harvested'")
        self.assertGreater(harvested["n"], 0)
        self.assertGreater(harvested["units"], 0)

    def test_drought_fails_crops(self):
        store, d = env_world()
        r = rng()
        _set_soil(store, 0.6)
        _seed_month_rain(store, 6)
        env_mod.monthly_pass(store, d, r, 6, 180 * 1440)
        for m in (7, 8, 9):
            _set_soil(store, 0.02, fertility=0.3)
            _seed_month_rain(store, m, mm_per_day=0.0)
            env_mod.monthly_pass(store, d, r, m, (m * 30 + 30) * 1440)
        failed = store.row("SELECT COUNT(*) AS n FROM env_crops"
                           " WHERE status = 'failed'")["n"]
        harvested = store.row("SELECT COUNT(*) AS n FROM env_crops"
                              " WHERE status = 'harvested'")["n"]
        self.assertGreater(failed, 0)
        self.assertEqual(harvested, 0)

    def test_soil_moisture_responds_to_rain(self):
        store, d = env_world()
        r = rng()
        _set_soil(store, 0.4)
        seed_weather(store, "rupsha_city", 0, precip_mm=0.0)
        seed_weather(store, "shibnagar_town", 0, precip_mm=100.0)
        env_mod.daily_pass(store, d, r, 0, 1440)
        wet = store.row(
            "SELECT AVG(es.moisture) AS m FROM env_soil es JOIN"
            " land_parcels lp ON lp.parcel_id = es.parcel_id WHERE"
            " lp.city_id = 'shibnagar_town'")["m"]
        dry = store.row(
            "SELECT AVG(es.moisture) AS m FROM env_soil es JOIN"
            " land_parcels lp ON lp.parcel_id = es.parcel_id WHERE"
            " lp.city_id = 'rupsha_city'")["m"]
        # All agricultural parcels are Shibnagar's; Rupsha has none.
        self.assertGreater(wet, 0.4)
        self.assertIsNone(dry)


if __name__ == "__main__":
    unittest.main()
