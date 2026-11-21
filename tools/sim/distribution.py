"""Session 03 Unit 08 — Population Distribution Engine.

Connects Sessions 01/02 to the city layer: households already
occupy real units (population.py, households.py); this unit adds
the city-level read of that fact — residential demand, density —
and the one movement the earlier sessions could not express:
MIGRATION between cities.

Migration is pressure-driven, never random. A household becomes a
candidate when its head is unemployed AND the household is in
debt or rent-burdened (last settled month: housing > 50% of
income, or no income at all) — and it moves only when the other
city offers a real vacant unit at <= 60% of its current rent.
Moves go through households.move_household (the Session 02
machinery), are capped per month, and are recorded in
migration_records + life events + city events. Employment
mobility (commuting) is Unit 14's regional read of the same
moves: a migrant keeps their job, so their workplace stays
behind in the other city.
"""
import json

from . import cities as cities_mod
from . import households as households_mod

MAX_MIGRATIONS_PER_MONTH = 2
TARGET_RENT_RATIO = 0.6


def zone_density(store, data, zone_id):
    """Residents per km2 of zone box area, from live households."""
    spec = None
    for s in data.city_specs():
        if zone_id in s["zones"]:
            spec = s
            break
    if spec is None:
        return 0.0
    box = spec["zone_boxes_m"][zone_id]
    area_km2 = (box["x1"] - box["x0"]) * (box["z1"] - box["z0"]) \
        / 1_000_000
    n = store.row(
        "SELECT COUNT(*) AS n FROM characters c JOIN households h"
        " ON h.household_id = c.household_id WHERE h.district_id = ?"
        " AND c.is_system = 0 AND c.died_at_game_minutes IS NULL"
        " AND h.dissolved_at_game_minutes IS NULL",
        (zone_id,))["n"]
    return round(n / area_km2, 1) if area_km2 else 0.0


def residential_demand(store, data, city_id):
    """Measured housing demand in a city: households in debt plus
    adults still living as 'child' in a parental household (the
    would-be household formers Session 02's leave-home serves)."""
    zones = data.city_spec(city_id)["zones"]
    marks = ",".join("?" for _ in zones)
    indebted = store.row(
        f"SELECT COUNT(*) AS n FROM households h JOIN household_state"
        f" hs ON hs.household_id = h.household_id WHERE"
        f" h.district_id IN ({marks}) AND hs.debt_ncr > 0"
        f" AND h.dissolved_at_game_minutes IS NULL",
        tuple(zones))["n"]
    waiting = 0
    from .identity import age_years
    now = store.world()["game_minutes"]
    for r in store.rows(
            f"SELECT c.born_at_game_minutes FROM household_members hm"
            f" JOIN characters c ON c.character_id = hm.character_id"
            f" JOIN households h ON h.household_id = hm.household_id"
            f" WHERE hm.role = 'child' AND hm.left_at_game_minutes"
            f" IS NULL AND h.district_id IN ({marks})"
            f" AND c.died_at_game_minutes IS NULL", tuple(zones)):
        if age_years(r["born_at_game_minutes"], now) >= 21:
            waiting += 1
    return {"indebted_households": indebted,
            "adults_waiting_to_form": waiting,
            "total": indebted + waiting}


def housing_pressure(store, data, city_id):
    """Occupied / total residential units of a city, live."""
    zones = data.city_spec(city_id)["zones"]
    marks = ",".join("?" for _ in zones)
    rows = store.rows(
        f"SELECT status, COUNT(*) AS n FROM properties WHERE"
        f" district_id IN ({marks}) GROUP BY status", tuple(zones))
    total = sum(r["n"] for r in rows)
    occupied = sum(r["n"] for r in rows if r["status"] == "rented")
    return {"total_units": total, "occupied_units": occupied,
            "vacancy_rate": round(1 - occupied / total, 3)
            if total else 0.0}


def _head(store, household_id):
    row = store.row("SELECT character_id FROM household_members"
                    " WHERE household_id = ? AND role = 'head'"
                    " AND left_at_game_minutes IS NULL",
                    (household_id,))
    return row["character_id"] if row else None


def _employed(store, character_id):
    return store.row("SELECT 1 FROM employments WHERE character_id"
                     " = ? AND ended_at_game_minutes IS NULL",
                     (character_id,)) is not None


def migration_pressure(store, data, household):
    """The household's migration pressure, from settled facts.
    Returns (qualifies, facts)."""
    hid = household["household_id"]
    head = _head(store, hid)
    if head is None or _employed(store, head):
        return False, {}
    state = store.row("SELECT debt_ncr FROM household_state WHERE"
                      " household_id = ?", (hid,))
    debt = state["debt_ncr"] if state else 0
    fin = store.row("SELECT income_ncr, housing_ncr FROM"
                    " household_finances WHERE household_id = ?"
                    " ORDER BY month_index DESC LIMIT 1", (hid,))
    rent_burden = False
    if fin:
        rent_burden = fin["income_ncr"] == 0 or (
            fin["income_ncr"] > 0
            and fin["housing_ncr"] > 0.5 * fin["income_ncr"])
    facts = {"head": head, "head_unemployed": True, "debt_ncr": debt,
             "rent_burden": rent_burden}
    return (debt > 0 or rent_burden), facts


def migrate_household(store, data, household_id, to_city_id, reason,
                      game_minutes):
    """Move one household to the cheapest qualifying vacant unit
    of another city (rent <= TARGET_RENT_RATIO x current rent).
    Returns the new rent, or None when no honest move exists."""
    h = store.row("SELECT * FROM households WHERE household_id = ?",
                  (household_id,))
    if h is None:
        return None
    from_city = cities_mod.city_of_zone(data, h["district_id"])
    if from_city is None or from_city == to_city_id:
        return None
    current_rent = households_mod.current_rent(store, data,
                                               household_id)
    if current_rent is None:
        return None
    zones = set(data.city_spec(to_city_id)["zones"])
    options = [v for v in households_mod.vacant_units(store, data)
               if v["property"]["district_id"] in zones
               and v["rent"] <= TARGET_RENT_RATIO * current_rent]
    if not options:
        return None
    chosen = options[0]
    new_rent = households_mod.move_household(
        store, data, household_id, chosen["property"]["property_id"],
        game_minutes)
    if new_rent is None:
        return None
    mid = store.next_id("MG", "migration_records", "migration_id")
    store.insert("migration_records", migration_id=mid,
                 household_id=household_id, from_city_id=from_city,
                 to_city_id=to_city_id,
                 reason=json.dumps(reason), game_minutes=game_minutes)
    from . import memory as memory_mod
    for m in households_mod.members(store, household_id):
        memory_mod.log_life_event(
            store, m["character_id"], "migrated", game_minutes,
            details={"from_city": from_city, "to_city": to_city_id,
                     "household_id": household_id})
    return new_rent


def monthly_migration(store, data, game_minutes):
    """The monthly pass: pressure-qualified households migrate,
    capped, in deterministic (household_id) order, both
    directions."""
    moved = []
    for spec in data.city_specs():
        other = cities_mod.SHIBNAGAR if spec["city_id"] \
            == cities_mod.RUPSHA else cities_mod.RUPSHA
        count = 0
        for h in cities_mod.city_households(store, data,
                                            spec["city_id"]):
            if count >= MAX_MIGRATIONS_PER_MONTH:
                break
            if h["created_at_game_minutes"] > game_minutes \
                    - 30 * 1440:
                continue  # settled households only
            qualifies, facts = migration_pressure(store, data, h)
            if not qualifies:
                continue
            rent = migrate_household(store, data, h["household_id"],
                                     other, facts, game_minutes)
            if rent is not None:
                moved.append({"household_id": h["household_id"],
                              "from": spec["city_id"], "to": other,
                              "new_rent": rent})
                count += 1
    return moved
