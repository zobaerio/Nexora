"""Session 08 test fixtures: a hand-built world with the city
layer and the Session 08 environment layer set up."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))

from tools.sim import cities as cities_mod  # noqa: E402
from tools.sim import environment as env_mod  # noqa: E402
from tools.sim.tests.common import data, make_store, rng  # noqa: E402
from tools.sim.tests.transportcommon import citizen  # noqa: E402

GM = 480


def env_world():
    """(store, data) with cities + environment seeded."""
    store = make_store()
    d = data()
    r = rng()
    cities_mod.setup_cities(store, d, r)
    env_mod.setup_environment(store, d, GM)
    store.commit()
    return store, d


def seed_weather(store, city_id, day_index, preset_id="rain",
                 precip_mm=50.0, temp_day=28.0):
    """Pre-seed a region's weather row (weather_for_region returns
    persisted rows, so the daily pass consumes exactly this)."""
    store.execute(
        "INSERT OR REPLACE INTO env_weather (region_id, day_index,"
        " preset_id, season_id, temp_day_c, temp_night_c,"
        " humidity_pct, pressure_hpa, wind_kmh, wind_dir_deg,"
        " cloud_pct, precip_mm, visibility_km, sunrise_min,"
        " sunset_min) VALUES (?, ?, ?, 'test', ?, ?, 80, 1005, 15,"
        " 180, 80, ?, 10, 360, 1080)",
        (city_id, day_index, preset_id, temp_day, temp_day - 5,
         precip_mm))
    store.commit()
