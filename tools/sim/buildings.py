"""Session 03 Unit 05 — Building Generation & State Engine.

The buildings themselves are the data files' identities (42 in
District 1, 18 generated in Shibnagar) — this unit does not create
a parallel building table. It maintains the sim-side STATE of each
building in building_state, keyed by the data's building id:
floors, construction year, structural condition, maintenance
status, economic value; and it reads occupancy live from the
simulation (households in the building's units).

Derivations, all deterministic:
- floors from type + tier (GDD-02: midtown apartment blocks are
  6-storey; the uptown rooftop tower is the district's only
  high-rise at 12);
- construction year from a per-building seeded stream inside a
  per-zone age band (the old town is old);
- condition starts from age and decays monthly (monthly_upkeep);
  maintenance (Unit 09's services, or a renovation project,
  Unit 11) restores it;
- economic value = the data's buy price x units, or monthly rent
  x 120 x units when the data sells no price (the sim's standing
  capitalisation convention, population.py) — civic plots with
  neither carry 0 building value (their land is the parcel's).
"""
from .rng import SimRng

_APARTMENT_FLOORS = {1: 2, 2: 3, 3: 6, 4: 6, 5: 8}
_ZONE_AGE = {  # (earliest, latest) construction-year band by zone
    "d1_oldtown": (1955, 1995), "d1_market": (1960, 2000),
    "d1_riverfront": (1970, 2010), "d1_transport": (1960, 2000),
    "d1_civic": (1970, 2010), "d1_education": (1975, 2005),
    "d1_park": (1950, 1980), "d1_industry": (1980, 2010),
    "d1_midtown": (1985, 2015), "d1_uptown": (2000, 2022),
}
_DEFAULT_AGE = (1985, 2015)
REFERENCE_YEAR = 2026


def floors_for(building):
    ptype, tier, bid = (building["property_type"], building["tier"],
                        building["id"])
    if bid == "b_d1_uptown_rooftop_restaurant":
        return 12  # GDD-02 §4.6: the district's only high-rise
    if ptype == "apartment":
        return _APARTMENT_FLOORS.get(tier, 3)
    if ptype == "house":
        return 2 if tier <= 4 else 3
    if ptype == "shop":
        return {1: 1, 2: 1, 3: 2, 4: 3, 5: 2}.get(tier, 1)
    if ptype == "office":
        return 5 if bid == "b_d1_uptown_offices" else 3
    if ptype == "factory":
        return 1
    return 0  # plots are land, not structures


def building_value(data, building):
    units = building.get("units", 1)
    buy = building.get("buy_price_ncr_per_unit")
    if buy:
        return int(buy * units)
    rent = building.get("rent_monthly_ncr_per_unit")
    if rent:
        return int(rent * 120 * units)
    return 0


def _year_for(rng, building):
    lo, hi = _ZONE_AGE.get(building["zone_id"], _DEFAULT_AGE)
    return rng.stream("building-year", building["id"]).randint(lo, hi)


def condition_band(condition):
    if condition >= 75:
        return "good"
    if condition >= 55:
        return "fair"
    if condition >= 35:
        return "poor"
    return "critical"


def setup_buildings(store, data, spec, rng, game_minutes):
    """One building_state row per building of the city (part_of
    entries included — they are distinct identities in the data).
    Idempotent."""
    n = 0
    for b in spec["properties"]:
        if store.row("SELECT 1 FROM building_state WHERE building_id"
                     " = ?", (b["id"],)):
            continue
        year = _year_for(rng, b) if b["property_type"] != "plot" \
            else None
        if year is None:
            condition = 90.0
        else:
            jitter = rng.stream("building-cond", b["id"]).uniform(
                -4, 4)
            condition = max(50.0, min(97.0, 100
                                       - (REFERENCE_YEAR - year) * 0.55
                                       + jitter))
        store.insert(
            "building_state", building_id=b["id"],
            city_id=spec["city_id"], floors=floors_for(b),
            construction_year=year, condition=round(condition, 2),
            maintenance_status=condition_band(condition),
            economic_value=building_value(data, b),
            updated_at_game_minutes=game_minutes)
        n += 1
    return n


def register_built_building(store, data, building_id, city_id, *,
                            floors, tier, property_type, units,
                            value, game_minutes):
    """A Unit 11 construction completion becomes a building the
    rest of the simulation can see: building_state row with the
    plan's facts and a fresh condition."""
    store.execute(
        "INSERT OR REPLACE INTO building_state (building_id, city_id,"
        " floors, construction_year, condition, maintenance_status,"
        " economic_value, updated_at_game_minutes)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (building_id, city_id, floors, REFERENCE_YEAR, 100.0, "good",
         value, game_minutes))


def occupancy(store, data, building_id):
    """Occupancy read live: residential buildings from their unit
    property rows (rented units / total units); non-residential
    buildings have no unit rows — their in-use state is the data's
    own status, reported as such, never dressed up as a rate."""
    rows = store.rows("SELECT status FROM properties WHERE"
                      " building_ref = ?", (building_id,))
    if rows:
        occupied = sum(1 for r in rows if r["status"] == "rented")
        return {"occupied_units": occupied, "total_units": len(rows),
                "rate": round(occupied / len(rows), 3),
                "basis": "tenancies"}
    building = data.all_buildings().get(building_id)
    if building is None:
        return {"occupied_units": 0, "total_units": 0, "rate": None,
                "basis": "unknown"}
    in_use = building["status"] in ("owned", "rented")
    return {"occupied_units": building.get("units", 1) if in_use
            else 0,
            "total_units": building.get("units", 1),
            "rate": None, "basis": "data_status"}


def monthly_upkeep(store, data, game_minutes, decline=False):
    """Condition decay: age wear + occupancy wear, doubled under
    decline pressure (Unit 10). Civic maintenance is Unit 09's
    spend, applied through apply_maintenance — upkeep itself only
    decays, so an unfunded city visibly deteriorates."""
    states = store.rows("SELECT * FROM building_state WHERE"
                        " construction_year IS NOT NULL")
    for s in states:
        age = REFERENCE_YEAR - s["construction_year"]
        decay = 0.22 + min(0.5, age / 400.0)
        occ = occupancy(store, data, s["building_id"])
        if occ.get("rate"):
            decay += 0.1 * occ["rate"]
        if decline:
            decay *= 1.5
        condition = max(5.0, s["condition"] - decay)
        store.execute(
            "UPDATE building_state SET condition = ?,"
            " maintenance_status = ?, updated_at_game_minutes = ?"
            " WHERE building_id = ?",
            (round(condition, 2), condition_band(condition),
             game_minutes, s["building_id"]))
    return len(states)


def apply_maintenance(store, building_id, points, game_minutes):
    """Restore condition (services spend or renovation). Returns
    the new condition, or None for an unknown building."""
    s = store.row("SELECT condition FROM building_state WHERE"
                  " building_id = ?", (building_id,))
    if s is None:
        return None
    condition = min(100.0, s["condition"] + points)
    store.execute(
        "UPDATE building_state SET condition = ?,"
        " maintenance_status = ?, updated_at_game_minutes = ?"
        " WHERE building_id = ?",
        (round(condition, 2), condition_band(condition), game_minutes,
         building_id))
    return condition
