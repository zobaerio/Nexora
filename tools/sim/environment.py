"""Session 08 — Weather, Climate, Environment & Ecosystem Engine.

A regional environmental layer over Sessions 01–07, built by
extension and never by recreation:

- WEATHER: Rupsha City's daily preset remains the engine's own
  daily_weather draw (every earlier session reads it; nothing
  changes). Each other city evolves its own preset by a seeded
  Markov-style reweighting of the same weights — season and region
  rain factors plus wet/dry persistence — and every region's full
  field set (temperature, humidity, pressure, wind, cloud,
  precipitation mm, visibility, sunrise/sunset) is derived from
  the preset's own data in data/weather-presets.json plus the
  documented season/region offsets in
  data/environment-config.json. All of it is SIMULATED: never a
  real-world observation, never a scientific forecast.
- WATER: one catchment per city over Session 03's terrain —
  rainfall accumulates, drainage (Session 03's drainage network
  capacity) removes water, the river rises and falls, groundwater
  recharges and is drawn by residents. When the river crosses the
  configured flood level, EXPOSED ground floods: exposure is
  geographic (Session 03 terrain regions), roads close through
  road_segments.closed (Session 07 routing detours), buildings
  lose condition (Session 03 building_state), businesses record
  the disruption, resident households are displaced by record.
- AGRICULTURE: crop cycles on the real agricultural parcels
  (Session 03 land_parcels), growth scored from soil moisture +
  fertility and recorded rainfall; harvest enters Session 04's
  market through adjust_inventory (kind 'harvest') on the city's
  agriculture business — no crop price is invented (the good and
  its price are Session 04's own).
- POLLUTION: monthly per-city air/water indices whose every point
  traces to a recorded source (Session 07 transport statistics
  emissions, active industry, Session 03 wastewater/drainage
  overloads, flood episodes). An enacted Session 05 law of kind
  'emission_limit' reduces the industry component measurably.
- DISASTERS: only from CONFIGURED scenarios
  (data/environment-config.json 'scenarios'), triggered
  explicitly through trigger_scenario() — never generated at
  random. (Hydrological flooding is a mechanism, not a scenario:
  it follows from the water model in any world.) Response uses
  actual resources only: relief from the city's real treasury
  balance through the ledger, shelter in a real civic building,
  evacuation as recorded trips, recovery repairs paid from the
  treasury until the recorded damage is repaired.
- VEGETATION / WILDLIFE: cover and population INDICES per
  habitat region — abstracted indices, labelled as such, not
  biological claims.

Every rate lives in data/environment-config.json, labelled
SIM MODEL there and in docs/SESSION-08-REPORT.md. Deterministic:
all draws come from SimRng streams keyed by (region, day) or
(city, month). Persistence is additive; the layer no-ops in
worlds that never set it up.
"""
import json
import math

from . import business as business_mod
from . import cities as cities_mod
from . import government as gov_mod
from . import market as market_mod
from . import needs as needs_mod
from . import terrain as terrain_mod

WET_PRESETS = ("rain", "storm")
ALL_PRESETS = ("clear_day", "sunrise_clear", "night_clear", "cloudy",
               "rain", "storm", "fog", "windy")


def cfg(data):
    return data.environment_config


def is_setup(store):
    row = store.world()
    return bool(row and row["environment_setup"])


# -- seasons / daylight ----------------------------------------------------

def season_for_day(data, day_index):
    """The configured season containing this day-of-year (the sim
    year is 365 days; day-of-year = day_index % 365). Season rows
    may wrap the year boundary (winter is stored as two rows)."""
    doy = day_index % 365
    for s in cfg(data)["seasons"]:
        if s["day_of_year_start"] <= doy <= s["day_of_year_end"]:
            return s
    return cfg(data)["seasons"][0]


def daylight(data, day_index):
    """(sunrise_min, sunset_min) — the documented approximation
    in the config (base 06:00/18:00 shifted by the season's
    daylight amplitude)."""
    season = season_for_day(data, day_index)
    amp = season["daylight_amplitude_min"]
    dl = cfg(data)["daylight"]
    return (dl["base_sunrise_min"] - amp, dl["base_sunset_min"] + amp)


# -- setup -------------------------------------------------------------------

def setup_environment(store, data, game_minutes=480):
    """Seed the layer for both cities: water state, soil for the
    agricultural parcels, vegetation + wildlife per habitat
    region. Idempotent; no-ops in worlds without the city layer."""
    if is_setup(store):
        return {"already": True}
    if not cities_mod.is_setup(store):
        return {"skipped": "no city layer"}
    wm = cfg(data)["water_model"]
    counts = {"cities": 0, "soil_parcels": 0, "vegetation": 0,
              "wildlife": 0}
    for spec in data.city_specs():
        cid = spec["city_id"]
        if not store.row("SELECT 1 FROM env_water_state WHERE"
                         " city_id = ?", (cid,)):
            store.insert(
                "env_water_state", city_id=cid,
                river_level_m=wm["river_base_level_m"],
                surface_storage_mm=0, groundwater_index=0.7,
                flood_active=0, updated_day=0)
        counts["cities"] += 1
        for region in terrain_mod.regions_for_spec(spec):
            cls = region["terrain_class"]
            if cls in ("forest", "wetland", "river"):
                key = region["id"]
                if not store.row("SELECT 1 FROM env_vegetation WHERE"
                                 " region_key = ?", (key,)):
                    store.insert(
                        "env_vegetation", region_key=key, city_id=cid,
                        name=region["name"], habitat_class=cls,
                        cover_index=0.6, updated_day=0)
                    counts["vegetation"] += 1
                if not store.row("SELECT 1 FROM env_wildlife WHERE"
                                 " region_key = ?", (key,)):
                    store.insert(
                        "env_wildlife", region_key=key, city_id=cid,
                        habitat_class=cls, population_index=0.55,
                        updated_day=0)
                    counts["wildlife"] += 1
        # The authored city's park land is vegetation too (its
        # terrain class is plain, but the parcel is the park).
        for p in store.rows(
                "SELECT parcel_id, building_id FROM land_parcels"
                " WHERE city_id = ?", (cid,)):
            if p["building_id"] and "park" in p["building_id"]:
                key = f"park:{p['parcel_id']}"
                if not store.row("SELECT 1 FROM env_vegetation WHERE"
                                 " region_key = ?", (key,)):
                    store.insert(
                        "env_vegetation", region_key=key, city_id=cid,
                        name="Park land", habitat_class="park",
                        cover_index=0.7, updated_day=0)
                    counts["vegetation"] += 1
    for p in store.rows("SELECT parcel_id FROM land_parcels WHERE"
                        " zoning_category = 'agricultural'"):
        if not store.row("SELECT 1 FROM env_soil WHERE parcel_id = ?",
                         (p["parcel_id"],)):
            store.insert("env_soil", parcel_id=p["parcel_id"],
                         moisture=0.5, fertility=0.7, updated_day=0)
            counts["soil_parcels"] += 1
    store.set_world(environment_setup=1)
    store.commit()
    return counts


# -- regional weather ----------------------------------------------------------

def _region_preset(store, data, rng, city_id, day_index, season):
    """Today's preset for one region. Rupsha City IS the engine's
    daily_weather draw (unchanged). Other regions reweight the
    same preset weights: season + region rain factors scale the
    wet presets, and yesterday's wet/dry state persists."""
    if city_id == cities_mod.RUPSHA:
        row = store.row("SELECT preset_id FROM daily_weather WHERE"
                        " day_index = ?", (day_index,))
        if row:
            return row["preset_id"]
        from .engine import WEATHER_WEIGHTS
        names = [n for n, _w in WEATHER_WEIGHTS]
        weights = [w for _n, w in WEATHER_WEIGHTS]
        return rng.stream("weather", day_index).choices(
            names, weights=weights)[0]
    from .engine import WEATHER_WEIGHTS
    rcfg = cfg(data)["regions"].get(city_id, {})
    wm = cfg(data)["weather_model"]
    rain_factor = season["rain_factor"] * rcfg.get("rain_factor", 1.0)
    prev = store.row("SELECT preset_id FROM env_weather WHERE"
                     " region_id = ? AND day_index = ?",
                     (city_id, day_index - 1))
    names, weights = [], []
    for name, w in WEATHER_WEIGHTS:
        weight = float(w)
        if name in WET_PRESETS:
            weight *= rain_factor
            if prev and prev["preset_id"] in WET_PRESETS:
                weight *= wm["wet_persistence"]
        elif prev and prev["preset_id"] in WET_PRESETS:
            weight /= wm["dry_persistence"]
        names.append(name)
        weights.append(weight)
    return rng.stream("env_weather", city_id, day_index).choices(
        names, weights=weights)[0]


def _active_scenario(store, city_id, day_index, types=None):
    q = ("SELECT * FROM disaster_events WHERE city_id = ? AND"
         " status = 'active' AND started_day <= ? AND"
         " (ends_day IS NULL OR ends_day >= ?)")
    rows = store.rows(q, (city_id, day_index, day_index))
    if types:
        rows = [r for r in rows if r["disaster_type"] in types]
    return rows


def weather_for_region(store, data, rng, city_id, day_index):
    """Today's full weather record for a region, computed once
    and persisted (a restart cannot re-roll it)."""
    row = store.row("SELECT * FROM env_weather WHERE region_id = ?"
                    " AND day_index = ?", (city_id, day_index))
    if row:
        return row
    season = season_for_day(data, day_index)
    preset_id = _region_preset(store, data, rng, city_id, day_index,
                               season)
    preset = data.weather_presets[preset_id]
    rcfg = cfg(data)["regions"].get(city_id, {})
    wm = cfg(data)["weather_model"]
    climate = cfg(data)["climate_scenarios"][
        cfg(data)["active_climate_scenario"]]
    stream = rng.stream("env_fields", city_id, day_index)
    jitter_t = stream.uniform(-wm["temp_jitter_c"], wm["temp_jitter_c"])
    jitter_p = stream.uniform(wm["precip_jitter_low"],
                              wm["precip_jitter_high"])
    temp_day = (preset["temperature_c"]["typical_day"]
                + season["temp_offset_c"] + rcfg.get("temp_offset_c", 0)
                + climate["temp_delta_c"] + jitter_t)
    temp_night = (preset["temperature_c"]["typical_night"]
                  + season["temp_offset_c"] + rcfg.get("temp_offset_c", 0)
                  + climate["temp_delta_c"] + jitter_t)
    precip = (preset["precipitation"]["rate"] * wm["mm_per_precip_rate"]
              * season["rain_factor"] * rcfg.get("rain_factor", 1.0)
              * climate["rain_factor"] * jitter_p)
    # Scenario modifiers (configured scenarios only): drought
    # dries the rain, heatwave adds its temperature offset,
    # cyclone/severe storm force the storm preset's shape.
    for sc in _active_scenario(store, city_id, day_index):
        if sc["disaster_type"] == "drought":
            precip *= (1 - 0.8 * sc["intensity"])
        elif sc["disaster_type"] == "heatwave":
            bump = 6.0 * sc["intensity"]
            temp_day += bump
            temp_night += bump
        elif sc["disaster_type"] in ("cyclone", "severe_storm"):
            if preset["precipitation"]["rate"] < 1.0:
                precip = max(precip, wm["mm_per_precip_rate"]
                             * season["rain_factor"] * jitter_p)
    cloud = preset["cloud_cover_percent"]
    humidity = min(98.0, max(25.0, 45 + cloud * 0.45
                             + precip * 0.5))
    pressure = wm["base_pressure_hpa"]
    if preset_id == "storm":
        pressure -= wm["storm_pressure_drop_hpa"]
    elif preset_id == "rain":
        pressure -= wm["rain_pressure_drop_hpa"]
    wind = preset["wind"]["speed_kmh"] * rcfg.get("wind_factor", 1.0)
    fog = preset.get("fog_density", 0)
    visibility = round(20.0 / (1 + fog * 900), 2) if fog else 20.0
    sunrise, sunset = daylight(data, day_index)
    store.execute(
        "INSERT OR REPLACE INTO env_weather (region_id, day_index,"
        " preset_id, season_id, temp_day_c, temp_night_c,"
        " humidity_pct, pressure_hpa, wind_kmh, wind_dir_deg,"
        " cloud_pct, precip_mm, visibility_km, sunrise_min,"
        " sunset_min) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,"
        " ?, ?, ?)",
        (city_id, day_index, preset_id, season["id"],
         round(temp_day, 2), round(temp_night, 2), round(humidity, 1),
         round(pressure, 1), round(wind, 1),
         preset["wind"]["direction_deg"], cloud, round(precip, 2),
         visibility, sunrise, sunset))
    return store.row("SELECT * FROM env_weather WHERE region_id = ?"
                     " AND day_index = ?", (city_id, day_index))


# -- exposure (Session 03 terrain decides) -------------------------------------

def exposed_zones(store, data, city_id):
    """Zones of the city intersecting a floodplain or wetland
    terrain region — the flood-exposed ground."""
    spec = next(s for s in data.city_specs() if s["city_id"] == city_id)
    exposed_regions = [r for r in terrain_mod.regions_for_spec(spec)
                       if r["terrain_class"] in ("floodplain", "wetland")]
    out = set()
    for zone, box in spec["zone_boxes_m"].items():
        cx = (box["x0"] + box["x1"]) / 2
        cz = (box["z0"] + box["z1"]) / 2
        region = terrain_mod.terrain_at(exposed_regions, cx, cz)
        if region is not None:
            out.add(zone)
    return sorted(out)


def exposed_parcels(store, data, city_id):
    """Parcels whose centre sits in a floodplain/wetland region."""
    spec = next(s for s in data.city_specs() if s["city_id"] == city_id)
    regions = terrain_mod.regions_for_spec(spec)
    out = []
    for p in store.rows("SELECT * FROM land_parcels WHERE city_id = ?",
                        (city_id,)):
        cx, cz = p["x"] + p["w"] / 2, p["z"] + p["d"] / 2
        region = terrain_mod.terrain_at(regions, cx, cz)
        if region and region["terrain_class"] in ("floodplain",
                                                  "wetland"):
            out.append(p)
    return out


def _city_residents(store, city_id, data):
    zones = [z for z in data.city_specs() if z["city_id"] == city_id]
    zone_ids = set(zones[0]["zones"]) if zones else set()
    return [r for r in store.rows(
        "SELECT c.character_id, h.household_id, h.district_id"
        " FROM characters c JOIN households h"
        " ON h.household_id = c.household_id"
        " WHERE c.is_system = 0 AND c.died_at_game_minutes IS NULL"
        " AND h.dissolved_at_game_minutes IS NULL")
        if r["district_id"] in zone_ids]


def _treasury_account(store, city_id):
    """The account relief/repairs draw on: the municipal treasury
    when the government layer exists, else SYS-CITY. Only what
    the account holds is ever spent (callers cap by balance)."""
    acct = gov_mod.MUNICIPAL_ACCOUNTS.get(city_id, "SYS-CITY")
    if store.row("SELECT 1 FROM characters WHERE character_id = ?",
                 (acct,)):
        return acct
    return "SYS-CITY"


# -- disasters: lifecycle ---------------------------------------------------------

def _log_response(store, disaster_id, action, ref_id, amount,
                  details, game_minutes):
    rid = store.next_id("DR", "disaster_responses", "response_id")
    store.insert("disaster_responses", response_id=rid,
                 disaster_id=disaster_id, action=action, ref_id=ref_id,
                 amount_ncr=int(amount), details=json.dumps(details),
                 game_minutes=game_minutes)
    return rid


def _impact(store, disaster_id, kind, ref_id, city_id, zone_id,
            damage, details, game_minutes):
    iid = store.next_id("DI", "disaster_impacts", "impact_id")
    store.insert("disaster_impacts", impact_id=iid,
                 disaster_id=disaster_id, kind=kind, ref_id=ref_id,
                 city_id=city_id, zone_id=zone_id, damage=damage,
                 repaired=0, details=json.dumps(details),
                 game_minutes=game_minutes)
    return iid


def start_disaster(store, data, disaster_type, city_id, day_index,
                   game_minutes, scenario_id=None, intensity=0.5,
                   duration_days=None, details=None):
    """Open a disaster record. Called by trigger_scenario()
    (configured scenarios) and by the hydrology pass (flood
    episodes). Never called by a random draw."""
    did = store.next_id("DS", "disaster_events", "disaster_id")
    ends = (day_index + duration_days - 1) if duration_days else None
    store.insert(
        "disaster_events", disaster_id=did, scenario_id=scenario_id,
        disaster_type=disaster_type, city_id=city_id,
        intensity=intensity, status="active", started_day=day_index,
        ends_day=ends, affected_population=0, damage_estimate_ncr=0,
        relief_paid_ncr=0, repair_spent_ncr=0,
        details=json.dumps(details or {}),
        created_at_game_minutes=game_minutes)
    store.execute(
        "INSERT INTO env_events (event_id, city_id, kind, day_index,"
        " details, game_minutes) VALUES (?, ?, ?, ?, ?, ?)",
        (store.next_id("EV", "env_events", "event_id"), city_id,
         f"disaster_start:{disaster_type}", day_index,
         json.dumps({"disaster_id": did, "scenario_id": scenario_id,
                     "intensity": intensity}), game_minutes))
    return did


def trigger_scenario(store, data, scenario_id, day_index,
                     game_minutes):
    """Trigger one CONFIGURED scenario from the config's
    'scenarios' list — the only door through which scenario
    disasters enter a world. Unknown ids raise."""
    scen = next((s for s in cfg(data)["scenarios"]
                 if s["id"] == scenario_id), None)
    if scen is None:
        raise ValueError(f"unknown scenario {scenario_id}")
    return start_disaster(
        store, data, scen["type"], scen["city_id"], day_index,
        game_minutes, scenario_id=scenario_id,
        intensity=scen["intensity"],
        duration_days=scen["duration_days"],
        details={"basis": scen["basis"]})


def _displace_households(store, data, disaster, zones, game_minutes):
    """Record displacement for households resident in the given
    zones (once per disaster per household). Returns the newly
    displaced household rows."""
    did = disaster["disaster_id"]
    already = {r["ref_id"] for r in store.rows(
        "SELECT ref_id FROM disaster_impacts WHERE disaster_id = ?"
        " AND kind = 'household_displaced'", (did,))}
    out = []
    for h in store.rows(
            "SELECT household_id, district_id FROM households"
            " WHERE dissolved_at_game_minutes IS NULL"):
        if h["district_id"] not in zones or h["household_id"] in already:
            continue
        members = store.rows(
            "SELECT character_id FROM household_members WHERE"
            " household_id = ? AND left_at_game_minutes IS NULL",
            (h["household_id"],))
        _impact(store, did, "household_displaced", h["household_id"],
                disaster["city_id"], h["district_id"], 0,
                {"members": len(members)}, game_minutes)
        out.append(h)
    return out


def _shelter_building(store, data, city_id, safe_zones):
    """A real civic-owned building in a safe zone of the city —
    the shelter of record. None when no such building exists."""
    spec = next(s for s in data.city_specs() if s["city_id"] == city_id)
    for b in spec["properties"]:
        if b.get("civic_owned") and b["zone_id"] in safe_zones \
                and "part_of" not in b:
            return b
    return None


def _run_response(store, data, disaster, day_index, game_minutes):
    """The response pass, run once when a disaster leaves its
    active phase: relief through the ledger from the real
    treasury balance, shelter assignment, evacuation trips for
    displaced household heads, medical flag for the clinics."""
    did = disaster["disaster_id"]
    city_id = disaster["city_id"]
    rcfg = cfg(data)["disaster_response"]
    displaced = store.rows(
        "SELECT ref_id, zone_id FROM disaster_impacts WHERE"
        " disaster_id = ? AND kind = 'household_displaced'",
        (did,))
    zones = exposed_zones(store, data, city_id)
    safe = [z for z in next(s for s in data.city_specs()
                            if s["city_id"] == city_id)["zones"]
            if z not in zones]
    shelter = _shelter_building(store, data, city_id, safe)
    _log_response(store, did, "shelter_assignment", None, 0,
                  {"shelter_building_id": shelter["id"] if shelter
                   else None,
                   "shelter_zone": shelter["zone_id"] if shelter
                   else None,
                   "note": "real civic building" if shelter else
                   "no civic building in a safe zone — shelter"
                   " recorded as unavailable, never invented"},
                  game_minutes)
    account = _treasury_account(store, city_id)
    relief_total = 0
    month_spent = store.row(
        "SELECT COALESCE(SUM(amount_ncr), 0) AS s FROM"
        " disaster_responses WHERE action = 'relief_payment' AND"
        " game_minutes > ?", (game_minutes - 30 * 1440,))["s"]
    for h in displaced:
        head = store.row(
            "SELECT character_id FROM household_members WHERE"
            " household_id = ? AND role = 'head' AND"
            " left_at_game_minutes IS NULL", (h["ref_id"],))
        if head is None:
            continue
        head_id = head["character_id"]
        amount = rcfg["relief_ncr_per_household"]
        if month_spent + relief_total + amount > \
                rcfg["monthly_relief_cap_ncr"]:
            amount = max(0, rcfg["monthly_relief_cap_ncr"]
                         - month_spent - relief_total)
        amount = min(amount, max(0, store.balance(account)))
        if amount > 0:
            store.transfer(
                account, head_id, amount, "disaster_relief",
                game_minutes, note=f"relief for {did}",
                transfer_key=f"relief:{did}:{h['ref_id']}",
                event_ref=did)
            relief_total += amount
        _log_response(store, did, "relief_payment", h["ref_id"],
                      amount, {"head": head_id, "account": account},
                      game_minutes)
        if shelter:
            tid = store.next_id("TR", "trips", "trip_id")
            store.insert(
                "trips", trip_id=tid, character_id=head_id,
                day_index=day_index, purpose="evacuation",
                origin_zone=h["zone_id"],
                destination_zone=shelter["zone_id"], mode="walk",
                vehicle_id=None, route_id=None, segment_ids="[]",
                distance_m=0, depart_minute=game_minutes,
                free_flow_min=0, travel_min=0,
                arrive_minute=game_minutes, fare_ncr=0,
                fare_basis="none", fuel_litres=0, status="completed",
                details=json.dumps({"disaster_id": did,
                                    "shelter_building_id":
                                    shelter["id"]}))
            _log_response(store, did, "evacuation_trip", head_id, 0,
                          {"trip_id": tid, "from_zone": h["zone_id"],
                           "to_zone": shelter["zone_id"]},
                          game_minutes)
    store.execute(
        "UPDATE disaster_events SET relief_paid_ncr = ? WHERE"
        " disaster_id = ?", (relief_total, did))
    _log_response(store, did, "medical_flag", None, 0,
                  {"note": "displaced residents flagged for the"
                   " Session 06 clinic queue via their existing"
                   " health profiles; no parallel medical system"},
                  game_minutes)
    return relief_total


def _repair_pass(store, data, disaster, day_index, game_minutes):
    """Recovery: treasury-funded repairs restore the recorded
    building damage. Returns True when nothing remains damaged."""
    did = disaster["disaster_id"]
    rcfg = cfg(data)["disaster_response"]
    account = _treasury_account(store, disaster["city_id"])
    budget = min(rcfg["repair_daily_budget_ncr"],
                 max(0, store.balance(account)))
    spent = 0
    remaining = False
    for imp in store.rows(
            "SELECT * FROM disaster_impacts WHERE disaster_id = ?"
            " AND kind = 'building_damage' AND repaired < damage"
            " ORDER BY impact_id", (did,)):
        gap = imp["damage"] - imp["repaired"]
        # Condition points affordable with today's remaining budget.
        fix = min(gap, (budget - spent)
                  / 1000.0 * rcfg["repair_condition_per_1000_ncr"])
        if fix <= 0:
            remaining = True
            continue
        cost = int(math.ceil(fix / rcfg["repair_condition_per_1000_ncr"]
                             * 1000))
        cost = min(cost, budget - spent)
        if cost <= 0:
            remaining = True
            continue
        store.transfer(account, "SYS-MARKET", cost, "disaster_repair",
                       game_minutes, note=f"repair for {did}",
                       transfer_key=f"repair:{did}:{imp['impact_id']}:"
                                    f"{day_index}",
                       event_ref=did)
        spent += cost
        store.execute(
            "UPDATE disaster_impacts SET repaired = repaired + ?"
            " WHERE impact_id = ?", (fix, imp["impact_id"]))
        b = store.row("SELECT condition FROM building_state WHERE"
                      " building_id = ?", (imp["ref_id"],))
        if b:
            store.execute(
                "UPDATE building_state SET condition = ?,"
                " updated_at_game_minutes = ? WHERE building_id = ?",
                (min(100.0, b["condition"] + fix), game_minutes,
                 imp["ref_id"]))
        if fix < gap:
            remaining = True
    if spent:
        store.execute(
            "UPDATE disaster_events SET repair_spent_ncr ="
            " repair_spent_ncr + ? WHERE disaster_id = ?",
            (spent, did))
        _log_response(store, did, "repair_payment", None, spent,
                      {"account": account}, game_minutes)
    still = store.row(
        "SELECT COUNT(*) AS n FROM disaster_impacts WHERE"
        " disaster_id = ? AND kind = 'building_damage' AND"
        " repaired < damage", (did,))["n"]
    return still == 0 and not remaining


def _damage_buildings(store, data, disaster, parcels, per_day,
                      game_minutes):
    """Apply one day of damage to exposed buildings (recorded as
    impacts, condition floored at the config minimum)."""
    did = disaster["disaster_id"]
    floor = cfg(data)["flood_model"]["min_building_condition"]
    total_damage = 0.0
    for p in parcels:
        bid = p["building_id"]
        if not bid:
            continue
        b = store.row("SELECT condition FROM building_state WHERE"
                      " building_id = ?", (bid,))
        if b is None:
            continue
        loss = min(per_day, max(0.0, b["condition"] - floor))
        if loss <= 0:
            continue
        store.execute(
            "UPDATE building_state SET condition = ?,"
            " updated_at_game_minutes = ? WHERE building_id = ?",
            (b["condition"] - loss, game_minutes, bid))
        _impact(store, did, "building_damage", bid,
                disaster["city_id"], p["zone_id"], loss,
                {"parcel_id": p["parcel_id"]}, game_minutes)
        total_damage += loss
        for biz in store.rows(
                "SELECT biz.business_id FROM businesses biz JOIN"
                " properties pr ON pr.property_id = biz.property_id"
                " WHERE pr.building_ref = ? AND"
                " biz.closed_at_game_minutes IS NULL", (bid,)):
            business_mod.log_event(
                store, biz["business_id"], "environment_disruption",
                {"disaster_id": did,
                 "kind": disaster["disaster_type"]}, game_minutes)
    if total_damage:
        store.execute(
            "UPDATE disaster_events SET damage_estimate_ncr ="
            " damage_estimate_ncr + ? WHERE disaster_id = ?",
            (int(total_damage * 100), did))
    return total_damage


def _close_roads(store, data, disaster, zones, game_minutes):
    """Close road segments with an endpoint in an exposed zone
    (recorded once per disaster); Session 07 routing detours."""
    did = disaster["disaster_id"]
    already = {r["ref_id"] for r in store.rows(
        "SELECT ref_id FROM disaster_impacts WHERE disaster_id = ?"
        " AND kind = 'road_closure'", (did,))}
    spec = next(s for s in data.city_specs()
                if s["city_id"] == disaster["city_id"])
    boxes = spec["zone_boxes_m"]

    def zone_at(x, z):
        for zone, b in boxes.items():
            if b["x0"] <= x <= b["x1"] and b["z0"] <= z <= b["z1"]:
                return zone
        return None

    for seg in spec["road_segments"]:
        sid = seg["id"]
        if sid in already:
            continue
        pts = []
        for key in ("from", "to", "a", "b", "start", "end"):
            if isinstance(seg.get(key), (list, tuple)):
                pts.append(seg[key])
        if not pts and "points" in seg:
            pts = [seg["points"][0], seg["points"][-1]]
        hit = any(zone_at(p[0], p[1]) in zones for p in pts if p)
        if hit:
            store.execute("UPDATE road_segments SET closed = 1 WHERE"
                          " segment_id = ?", (sid,))
            _impact(store, did, "road_closure", sid,
                    disaster["city_id"], None, 0, {}, game_minutes)


def _reopen_roads(store, disaster):
    for imp in store.rows(
            "SELECT ref_id FROM disaster_impacts WHERE disaster_id"
            " = ? AND kind = 'road_closure'", (disaster["disaster_id"],)):
        store.execute("UPDATE road_segments SET closed = 0 WHERE"
                      " segment_id = ?", (imp["ref_id"],))


# -- governance hook (Session 05 law book) -------------------------------------

def effective_emission_reduction(store):
    """The enacted emission_limit law's reduction percent (0 when
    no such law is in force) — read from the law book exactly the
    way justice.py's own hooks read it."""
    month = (store.world()["game_minutes"] // 43200)
    row = store.row(
        "SELECT effect FROM laws WHERE kind = 'emission_limit' AND"
        " status = 'enacted' AND effective_month <= ? ORDER BY"
        " enacted_at_game_minutes DESC, law_id DESC LIMIT 1",
        (month,))
    if row is None:
        return 0.0
    return float(json.loads(row["effect"]).get("reduction_percent", 0))


# -- daily pass ------------------------------------------------------------------

def _needs_impact(store, residents, deltas, game_minutes):
    for r in residents:
        needs_mod.adjust(store, r["character_id"], deltas, game_minutes)


def daily_pass(store, data, rng, day_index, game_minutes):
    """One environmental day: regional weather, scenario effects,
    hydrology, soil moisture, flood episodes, disaster phases.
    Runs after the transport pass, so today's flood road closures
    govern tomorrow's routing."""
    if not is_setup(store):
        return {}
    out = {}
    wcfg = cfg(data)["water_model"]
    fcfg = cfg(data)["flood_model"]
    for spec in data.city_specs():
        cid = spec["city_id"]
        weather = weather_for_region(store, data, rng, cid, day_index)
        precip = weather["precip_mm"]
        state = store.row("SELECT * FROM env_water_state WHERE"
                          " city_id = ?", (cid,))
        # Scenario river forcing (configured scenarios only).
        surge = 0.0
        for sc in _active_scenario(store, cid, day_index):
            if sc["disaster_type"] == "flood_surge":
                surge += 1.0 * sc["intensity"]
            elif sc["disaster_type"] == "cyclone":
                surge += 0.5 * sc["intensity"]
        # Hydrology: drainage first (Session 03 network), then
        # runoff into the river, infiltration to groundwater.
        drainage_cap = store.row(
            "SELECT COALESCE(SUM(capacity_units), 0) AS s FROM"
            " infrastructure_state WHERE city_id = ? AND network ="
            " 'drainage'", (cid,))["s"]
        drainage_mm = drainage_cap * wcfg["drainage_mm_per_capacity_unit"]
        drained = min(precip, drainage_mm)
        runoff = (precip - drained) * wcfg["runoff_share"]
        river = state["river_level_m"] + runoff / wcfg[
            "river_rise_divisor"] + surge
        # Recession: the river is fed upstream, so its level
        # relaxes toward the base level each day (the excess
        # above base recedes; a dry-season deficit recovers) —
        # it neither empties nor stays flooded forever.
        river = wcfg["river_base_level_m"] + (
            river - wcfg["river_base_level_m"]) * (
                1 - wcfg["river_recession_rate"])
        river = max(0.3, river)
        storage = state["surface_storage_mm"] + precip * (
            1 - wcfg["runoff_share"] - wcfg["infiltration_share"])
        storage = max(0.0, min(wcfg["surface_storage_capacity_mm"],
                               storage - wcfg[
                                   "surface_evaporation_mm_per_day"]))
        residents = _city_residents(store, cid, data)
        ground = state["groundwater_index"] \
            + precip * wcfg["infiltration_share"] \
            * wcfg["groundwater_recharge_rate"] \
            - len(residents) * wcfg["groundwater_draw_per_resident"]
        ground = max(0.0, min(1.0, ground))
        # Soil moisture on the city's agricultural parcels.
        scfg = cfg(data)["soil_model"]
        for p in store.rows(
                "SELECT lp.parcel_id FROM land_parcels lp JOIN"
                " env_soil es ON es.parcel_id = lp.parcel_id WHERE"
                " lp.city_id = ?", (cid,)):
            s = store.row("SELECT * FROM env_soil WHERE parcel_id = ?",
                          (p["parcel_id"],))
            moisture = max(0.0, min(1.0, s["moisture"]
                                    + precip * scfg["moisture_rain_gain"]
                                    - scfg["moisture_daily_loss"]))
            store.execute(
                "UPDATE env_soil SET moisture = ?, updated_day = ?"
                " WHERE parcel_id = ?", (round(moisture, 4), day_index,
                                         p["parcel_id"]))
        # Flood episodes: a mechanism of the water model.
        flood = next((d for d in _active_scenario(store, cid, day_index)
                      if d["disaster_type"] == "flood"), None)
        if flood is None and river >= wcfg["flood_level_m"]:
            zones = exposed_zones(store, data, cid)
            did = start_disaster(
                store, data, "flood", cid, day_index, game_minutes,
                scenario_id=None,
                intensity=min(1.0, 0.4 + (river - wcfg["flood_level_m"])),
                details={"mechanism": "river level crossed the"
                         " configured flood level",
                         "river_level_m": round(river, 3)})
            flood = store.row("SELECT * FROM disaster_events WHERE"
                              " disaster_id = ?", (did,))
            _close_roads(store, data, flood, zones, game_minutes)
            _displace_households(store, data, flood, zones, game_minutes)
            affected = len([r for r in residents
                            if r["district_id"] in zones])
            store.execute(
                "UPDATE disaster_events SET affected_population = ?"
                " WHERE disaster_id = ?", (affected, did))
            store.execute(
                "UPDATE env_water_state SET flood_active = 1 WHERE"
                " city_id = ?", (cid,))
        if flood is not None:
            parcels = exposed_parcels(store, data, cid)
            _damage_buildings(store, data, flood, parcels,
                              fcfg["building_condition_loss_per_day"],
                              game_minutes)
            zones = exposed_zones(store, data, cid)
            exposed_res = [r for r in residents
                           if r["district_id"] in zones]
            _needs_impact(store, exposed_res,
                          {"healthcare": -2, "safety": -2}, game_minutes)
            if river < wcfg["flood_level_m"] - fcfg["hysteresis_m"]:
                _to_responding(store, data, flood, day_index,
                               game_minutes)
                store.execute(
                    "UPDATE env_water_state SET flood_active = 0"
                    " WHERE city_id = ?", (cid,))
        # Scenario daily effects.
        for sc in _active_scenario(store, cid, day_index):
            if sc["disaster_type"] in ("cyclone", "severe_storm"):
                zones = exposed_zones(store, data, cid)
                if not sc["affected_population"]:
                    affected = len([r for r in residents
                                    if r["district_id"] in zones])
                    store.execute(
                        "UPDATE disaster_events SET"
                        " affected_population = ? WHERE disaster_id"
                        " = ?", (affected, sc["disaster_id"]))
                _close_roads(store, data, sc, zones, game_minutes)
                _displace_households(store, data, sc, zones, game_minutes)
                _damage_buildings(
                    store, data, sc, exposed_parcels(store, data, cid),
                    fcfg["building_condition_loss_per_day"]
                    * sc["intensity"], game_minutes)
            elif sc["disaster_type"] == "heatwave":
                _needs_impact(store, residents,
                              {"healthcare": -1, "rest": -1},
                              game_minutes)
        store.execute(
            "UPDATE env_water_state SET river_level_m = ?,"
            " surface_storage_mm = ?, groundwater_index = ?,"
            " updated_day = ? WHERE city_id = ?",
            (round(river, 4), round(storage, 2), round(ground, 4),
             day_index, cid))
        out[cid] = {"preset": weather["preset_id"],
                    "precip_mm": precip, "river_level_m": round(river, 3)}
    # Queue 15 Unit CY: BX event E2 — a storm-soaked market trip loses
    # a carried good. One loss per (disaster, day); silent at the
    # default rate 0. Transport's daily pass runs before this one in
    # the engine, so today's trips already exist.
    from . import lost_items as lost_items_mod
    for d in store.rows("SELECT * FROM disaster_events WHERE status"
                        " = 'active' AND disaster_type IN ('cyclone',"
                        " 'severe_storm') ORDER BY disaster_id"):
        lost_items_mod.storm_market_losses(
            store, data, rng, d["disaster_id"], day_index, game_minutes)
    # Queue 19 Unit EF: furniture standing in an exposed zone wears
    # (−1 per exposed day, DQ) — the same exposure the pass applies
    # to buildings, read off the row's location property. One call
    # per active flood / cyclone / severe_storm disaster, over that
    # disaster's exposed zones (floodplain/wetland zones).
    for d in store.rows("SELECT * FROM disaster_events WHERE status"
                        " = 'active' AND disaster_type IN ('flood',"
                        " 'cyclone', 'severe_storm')"
                        " ORDER BY disaster_id"):
        lost_items_mod.apply_furniture_exposure_wear(
            store, data, exposed_zones(store, data, d["city_id"]),
            game_minutes)
    # Disaster phase transitions + recovery.
    for d in store.rows("SELECT * FROM disaster_events WHERE status"
                        " = 'active' AND ends_day IS NOT NULL AND"
                        " ends_day < ?", (day_index,)):
        _to_responding(store, data, d, day_index, game_minutes)
    for d in store.rows("SELECT * FROM disaster_events WHERE status"
                        " = 'responding'"):
        if _repair_pass(store, data, d, day_index, game_minutes):
            store.execute(
                "UPDATE disaster_events SET status = 'recovered',"
                " recovered_at_game_minutes = ? WHERE disaster_id = ?",
                (game_minutes, d["disaster_id"]))
            store.execute(
                "INSERT INTO env_events (event_id, city_id, kind,"
                " day_index, details, game_minutes) VALUES (?, ?, ?,"
                " ?, ?, ?)",
                (store.next_id("EV", "env_events", "event_id"),
                 d["city_id"], "disaster_recovered", day_index,
                 json.dumps({"disaster_id": d["disaster_id"]}),
                 game_minutes))
    store.commit()
    return out


def _to_responding(store, data, disaster, day_index, game_minutes):
    store.execute(
        "UPDATE disaster_events SET status = 'responding' WHERE"
        " disaster_id = ?", (disaster["disaster_id"],))
    fresh = store.row("SELECT * FROM disaster_events WHERE"
                      " disaster_id = ?", (disaster["disaster_id"],))
    _reopen_roads(store, fresh)
    _run_response(store, data, fresh, day_index, game_minutes)


# -- monthly pass ------------------------------------------------------------------

def _month_weather(store, city_id, month_index):
    lo = (month_index - 1) * 30
    rows = store.rows("SELECT * FROM env_weather WHERE region_id = ?"
                      " AND day_index >= ? AND day_index < ?",
                      (city_id, lo, lo + 30))
    rain = sum(r["precip_mm"] for r in rows)
    temp = (sum(r["temp_day_c"] for r in rows) / len(rows)) if rows else 0
    return rain, temp, len(rows)


def _agriculture_pass(store, data, month_index, game_minutes):
    acfg = cfg(data)["agriculture"]
    scfg = cfg(data)["soil_model"]
    crops = {c["id"]: c for c in acfg["crops"]}
    season_now = season_for_day(data, month_index * 30 - 1)["id"]
    out = {"planted": 0, "harvested_units": 0.0, "failed": 0}
    flooded_cities = {r["city_id"] for r in store.rows(
        "SELECT DISTINCT city_id FROM disaster_events WHERE"
        " disaster_type = 'flood' AND started_day >= ?",
        ((month_index - 1) * 30,))}
    for p in store.rows("SELECT * FROM land_parcels WHERE"
                        " zoning_category = 'agricultural'"):
        soil = store.row("SELECT * FROM env_soil WHERE parcel_id = ?",
                         (p["parcel_id"],))
        if soil is None:
            continue
        active = store.row(
            "SELECT * FROM env_crops WHERE parcel_id = ? AND status"
            " = 'growing' ORDER BY planted_day DESC LIMIT 1",
            (p["parcel_id"],))
        rain, _t, _n = _month_weather(store, p["city_id"], month_index)
        if active:
            crop = crops[active["crop_id"]]
            moisture_score = min(1.2, soil["moisture"]
                                 / max(0.05, crop["min_moisture"]))
            rain_score = min(1.0, rain / 120.0)
            growth = (0.4 * moisture_score + 0.3 * soil["fertility"]
                      + 0.3 * rain_score) / crop["growth_months"]
            score = active["growth_score"] + growth
            store.execute(
                "UPDATE env_soil SET fertility = ? WHERE parcel_id = ?",
                (max(0.0, soil["fertility"]
                     - scfg["fertility_crop_drain_per_month"]),
                 p["parcel_id"]))
            age_months = month_index - active["planted_month"]
            if age_months >= crop["growth_months"]:
                if score >= acfg["growth_failure_threshold"]:
                    units = round(crop["yield_units_per_parcel"]
                                  * min(1.0, score), 2)
                    biz = _agriculture_business(store, data, p["city_id"])
                    if biz:
                        market_mod.adjust_inventory(
                            store, biz, "agricultural_produce", units,
                            "harvest", game_minutes,
                            details={"parcel_id": p["parcel_id"],
                                     "crop_id": crop["id"],
                                     "growth_score": round(score, 3)})
                    store.execute(
                        "UPDATE env_crops SET status = 'harvested',"
                        " growth_score = ?, harvest_units = ?,"
                        " updated_day = ? WHERE crop_record_id = ?",
                        (round(score, 4), units, month_index * 30 - 1,
                         active["crop_record_id"]))
                    out["harvested_units"] += units
                else:
                    store.execute(
                        "UPDATE env_crops SET status = 'failed',"
                        " growth_score = ?, updated_day = ? WHERE"
                        " crop_record_id = ?",
                        (round(score, 4), month_index * 30 - 1,
                         active["crop_record_id"]))
                    out["failed"] += 1
            else:
                store.execute(
                    "UPDATE env_crops SET growth_score = ?,"
                    " updated_day = ? WHERE crop_record_id = ?",
                    (round(score, 4), month_index * 30 - 1,
                     active["crop_record_id"]))
        else:
            fert = soil["fertility"] + scfg[
                "fertility_fallow_recovery_per_month"]
            if p["city_id"] in flooded_cities:
                fert -= scfg["fertility_flood_erosion"]
            store.execute(
                "UPDATE env_soil SET fertility = ? WHERE parcel_id = ?",
                (max(0.0, min(1.0, fert)), p["parcel_id"]))
            for crop in acfg["crops"]:
                if crop["plant_season"] == season_now:
                    rid = store.next_id("CR", "env_crops",
                                        "crop_record_id")
                    store.insert(
                        "env_crops", crop_record_id=rid,
                        parcel_id=p["parcel_id"], city_id=p["city_id"],
                        crop_id=crop["id"], planted_month=month_index,
                        planted_day=month_index * 30 - 30,
                        growth_score=0, status="growing",
                        harvest_units=0, updated_day=month_index * 30 - 1)
                    out["planted"] += 1
                    break
    return out


def _agriculture_business(store, data, city_id):
    for b in business_mod.active_businesses(store):
        if b["category"] != "agriculture" or not b["property_id"]:
            continue
        prop = store.row("SELECT district_id FROM properties WHERE"
                         " property_id = ?", (b["property_id"],))
        if prop and data.zone_city(prop["district_id"]) == city_id:
            return b["business_id"]
    return None


def _pollution_pass(store, data, month_index, game_minutes):
    pcfg = cfg(data)["pollution_model"]
    reduction = effective_emission_reduction(store)
    out = {}
    for spec in data.city_specs():
        cid = spec["city_id"]
        emissions = 0.0
        stat = store.row(
            "SELECT statistics FROM transport_statistics WHERE scope"
            " = ? AND month_index = ?", (cid, month_index))
        if stat:
            emissions = json.loads(stat["statistics"]).get(
                "emissions_kg", 0.0)
        industry = store.row(
            "SELECT COUNT(*) AS n FROM businesses WHERE category IN"
            " ('manufacturing', 'food_processing') AND"
            " closed_at_game_minutes IS NULL")["n"]
        # Industry is counted per city through property zones.
        industry = 0
        for b in business_mod.active_businesses(store):
            if b["category"] in ("manufacturing", "food_processing") \
                    and b["property_id"]:
                prop = store.row(
                    "SELECT district_id FROM properties WHERE"
                    " property_id = ?", (b["property_id"],))
                if prop and data.zone_city(prop["district_id"]) == cid:
                    industry += 1
        vehicle_part = emissions / pcfg[
            "vehicle_emissions_kg_per_index_point"]
        industry_part = industry * pcfg["industry_weight"] \
            * (1 - reduction / 100.0)
        air = min(100.0, vehicle_part + industry_part)
        nets = store.rows(
            "SELECT status FROM infrastructure_state WHERE city_id"
            " = ? AND network IN ('wastewater', 'drainage')", (cid,))
        overload_share = (sum(1 for n in nets
                              if n["status"] == "overloaded")
                          / len(nets)) if nets else 0
        floods = store.row(
            "SELECT COUNT(*) AS n FROM disaster_events WHERE city_id"
            " = ? AND disaster_type = 'flood' AND started_day >= ?",
            (cid, (month_index - 1) * 30))["n"]
        water = min(100.0, overload_share
                    * pcfg["wastewater_overload_weight"]
                    + floods * pcfg["flood_water_weight"])
        sources = {"vehicle_emissions_kg": round(emissions, 1),
                   "vehicle_index_points": round(vehicle_part, 2),
                   "industry_businesses": industry,
                   "industry_index_points": round(industry_part, 2),
                   "emission_limit_reduction_percent": reduction,
                   "wastewater_drainage_overload_share":
                   round(overload_share, 3),
                   "flood_episodes": floods}
        store.execute(
            "INSERT OR REPLACE INTO env_pollution (city_id,"
            " month_index, air_index, water_index, sources,"
            " game_minutes) VALUES (?, ?, ?, ?, ?, ?)",
            (cid, month_index, round(air, 2), round(water, 2),
             json.dumps(sources), game_minutes))
        if air > pcfg["air_health_threshold"]:
            _needs_impact(store, _city_residents(store, cid, data),
                          {"healthcare": pcfg["air_health_need_delta"]},
                          game_minutes)
        out[cid] = {"air_index": round(air, 2),
                    "water_index": round(water, 2)}
    return out


def _vegetation_pass(store, data, month_index, game_minutes):
    vcfg = cfg(data)["vegetation_model"]
    law = effective_emission_reduction(store) > 0
    for v in store.rows("SELECT * FROM env_vegetation"):
        rain, _t, _n = _month_weather(store, v["city_id"], month_index)
        cover = v["cover_index"]
        ceiling = vcfg["ceiling_by_class"].get(v["habitat_class"], 0.8)
        if rain < 30:
            cover -= vcfg["drought_decline_per_month"]
        else:
            cover += vcfg["growth_per_month"] * (ceiling - cover)
        built = store.row(
            "SELECT COUNT(*) AS n FROM construction_projects WHERE"
            " city_id = ? AND status IN ('completed', 'occupied')"
            " AND completed_day >= ?",
            (v["city_id"], (month_index - 1) * 30))["n"]
        cover -= built * vcfg["deforestation_per_construction"]
        if law:
            cover += vcfg["conservation_bonus_per_month"]
        cover = max(0.0, min(1.0, cover))
        store.execute(
            "UPDATE env_vegetation SET cover_index = ?, updated_day"
            " = ? WHERE region_key = ?",
            (round(cover, 4), month_index * 30 - 1, v["region_key"]))
        w = store.row("SELECT * FROM env_water_state WHERE city_id"
                      " = ?", (v["city_id"],))
        availability = (0.5 * (w["groundwater_index"] if w else 0.5)
                        + 0.5 * min(1.0, (w["surface_storage_mm"]
                                          if w else 0) / 260.0))
        target = cover * availability
        wild = store.row("SELECT * FROM env_wildlife WHERE region_key"
                         " = ?", (v["region_key"],))
        if wild:
            drift = cfg(data)["wildlife_model"]["drift_per_month"]
            idx = wild["population_index"] + max(
                -drift, min(drift, target - wild["population_index"]))
            store.execute(
                "UPDATE env_wildlife SET population_index = ?,"
                " updated_day = ? WHERE region_key = ?",
                (round(max(0.0, min(1.0, idx)), 4),
                 month_index * 30 - 1, v["region_key"]))


def monthly_pass(store, data, rng, month_index, game_minutes):
    if not is_setup(store):
        return {}
    out = {}
    out["agriculture"] = _agriculture_pass(store, data, month_index,
                                           game_minutes)
    out["pollution"] = _pollution_pass(store, data, month_index,
                                       game_minutes)
    _vegetation_pass(store, data, month_index, game_minutes)
    climate_name = cfg(data)["active_climate_scenario"]
    for spec in data.city_specs():
        cid = spec["city_id"]
        rain, temp, _n = _month_weather(store, cid, month_index)
        w = store.row("SELECT * FROM env_water_state WHERE city_id"
                      " = ?", (cid,))
        residents = _city_residents(store, cid, data)
        zones = exposed_zones(store, data, cid)
        exposed_res = len([r for r in residents
                           if r["district_id"] in zones])
        veg = store.row(
            "SELECT AVG(cover_index) AS a FROM env_vegetation WHERE"
            " city_id = ?", (cid,))["a"]
        pol = store.row("SELECT * FROM env_pollution WHERE city_id"
                        " = ? AND month_index = ?", (cid, month_index))
        metrics = {
            "avg_temp_day_c": round(temp, 2),
            "total_rain_mm": round(rain, 1),
            "river_level_m_end": w["river_level_m"] if w else None,
            "groundwater_index": w["groundwater_index"] if w else None,
            "surface_storage_mm": w["surface_storage_mm"] if w else None,
            "water_availability_index": round(
                0.5 * (w["groundwater_index"] if w else 0)
                + 0.5 * min(1.0, ((w["surface_storage_mm"] if w else 0)
                                  / cfg(data)["water_model"][
                                      "surface_storage_capacity_mm"])),
                3) if w else None,
            "vegetation_cover_avg": round(veg, 3) if veg else None,
            "air_index": pol["air_index"] if pol else None,
            "water_pollution_index": pol["water_index"] if pol else None,
            "climate_scenario": climate_name,
            "simulated": True,
            "vulnerability_exposed_resident_share": round(
                exposed_res / len(residents), 3) if residents else 0,
        }
        store.execute(
            "INSERT OR REPLACE INTO env_snapshots (city_id,"
            " month_index, metrics, game_minutes) VALUES (?, ?, ?, ?)",
            (cid, month_index, json.dumps(metrics), game_minutes))
    store.commit()
    return out


def environment_summary(store):
    if not is_setup(store):
        return {}
    latest = {}
    for spec_city in store.rows("SELECT city_id FROM cities"):
        cid = spec_city["city_id"]
        w = store.row("SELECT * FROM env_weather WHERE region_id = ?"
                      " ORDER BY day_index DESC LIMIT 1", (cid,))
        water = store.row("SELECT * FROM env_water_state WHERE"
                          " city_id = ?", (cid,))
        snap = store.row("SELECT metrics FROM env_snapshots WHERE"
                         " city_id = ? ORDER BY month_index DESC"
                         " LIMIT 1", (cid,))
        latest[cid] = {
            "weather": dict(w) if w else None,
            "water": dict(water) if water else None,
            "latest_snapshot": json.loads(snap["metrics"]) if snap
            else None,
        }
    return {
        "cities": latest,
        "disasters": {r["status"]: r["n"] for r in store.rows(
            "SELECT status, COUNT(*) AS n FROM disaster_events"
            " GROUP BY status")},
        "crops": {r["status"]: r["n"] for r in store.rows(
            "SELECT status, COUNT(*) AS n FROM env_crops GROUP BY"
            " status")},
        "harvested_units_total": store.row(
            "SELECT COALESCE(SUM(harvest_units), 0) AS s FROM"
            " env_crops")["s"],
        "flood_episodes": store.row(
            "SELECT COUNT(*) AS n FROM disaster_events WHERE"
            " disaster_type = 'flood'")["n"],
        "simulated": True,
    }
