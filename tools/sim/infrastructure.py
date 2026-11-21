"""Session 03 Unit 07 — Public Infrastructure Engine.

Eight networks per zone — electricity, water, wastewater,
drainage, solid waste, street lighting, telecom, public
transport — each with a capacity and a demand, recomputed weekly
from simulated facts:

- demand = residents of the zone x per-capita demand + workers in
  the zone x a workplace factor (employments read through their
  profession's workplace_zone, the data's own anchor);
- capacity = the zone's building count x a per-network base.

The base rates are SIM MODEL constants (labelled, like Session
01's pension): no infrastructure capacity table exists in the
merged design data. What is NOT modelled is the consequence
chain: load ratio >= 1.0 is 'overloaded', >= 0.85 'strained', and
a monthly pass applies the overload to residents' needs (water
and waste overloads hit healthcare; power hits rest and safety)
through needs.adjust — overload is felt by households, and it
gates Unit 10's growth (a city does not densify into a zone whose
water already fails).
"""
from . import needs as needs_mod

NETWORKS = ("electricity", "water", "wastewater", "drainage",
            "solid_waste", "street_lighting", "telecom",
            "public_transport")

# SIM MODEL constants (see docstring).
CAPACITY_PER_BUILDING = {"electricity": 26, "water": 26,
                         "wastewater": 24, "drainage": 30,
                         "solid_waste": 24, "street_lighting": 20,
                         "telecom": 26, "public_transport": 18}
DEMAND_PER_RESIDENT = {"electricity": 1.0, "water": 1.0,
                       "wastewater": 0.9, "drainage": 0.8,
                       "solid_waste": 1.0, "street_lighting": 0.6,
                       "telecom": 0.9, "public_transport": 0.5}
WORKPLACE_FACTOR = 0.4

# Monthly need deltas per overloaded network (per resident).
OVERLOAD_EFFECTS = {
    "water": {"healthcare": -4, "safety": -2},
    "electricity": {"rest": -3, "safety": -2},
    "solid_waste": {"healthcare": -3},
    "drainage": {"healthcare": -2},
    "wastewater": {"healthcare": -2},
    "street_lighting": {"safety": -3},
}


def _status(load):
    if load >= 1.0:
        return "overloaded"
    if load >= 0.85:
        return "strained"
    return "ok"


def zone_residents(store, zone_id):
    return store.rows(
        "SELECT c.character_id FROM characters c JOIN households h"
        " ON h.household_id = c.household_id WHERE h.district_id = ?"
        " AND c.is_system = 0 AND c.died_at_game_minutes IS NULL"
        " AND h.dissolved_at_game_minutes IS NULL", (zone_id,))


def zone_workers(store, data, zone_id):
    n = 0
    for r in store.rows("SELECT profession_id, COUNT(*) AS n FROM"
                        " employments WHERE ended_at_game_minutes"
                        " IS NULL GROUP BY profession_id"):
        prof = data.professions.get(r["profession_id"])
        if prof and prof["workplace_zone"] == zone_id:
            n += r["n"]
    return n


def setup_infrastructure(store, data, spec, game_minutes):
    """Capacity rows for every (zone, network) of the city.
    Idempotent; demand starts at 0 until the first weekly update."""
    n = 0
    building_counts = {}
    for b in spec["properties"]:
        if "part_of" not in b:
            building_counts[b["zone_id"]] = \
                building_counts.get(b["zone_id"], 0) + 1
    for zone in spec["zones"]:
        for network in NETWORKS:
            if store.row("SELECT 1 FROM infrastructure_state WHERE"
                         " zone_id = ? AND network = ?",
                         (zone, network)):
                continue
            store.insert(
                "infrastructure_state", city_id=spec["city_id"],
                zone_id=zone, network=network,
                capacity_units=building_counts.get(zone, 0)
                * CAPACITY_PER_BUILDING[network],
                demand_units=0, load_ratio=0, status="ok",
                updated_at_game_minutes=game_minutes)
            n += 1
    return n


def weekly_update(store, data, game_minutes):
    """Recompute demand/load/status for every zone of every set-up
    city. A bounded aggregate pass, like the society cadences."""
    out = {}
    for row in store.rows("SELECT DISTINCT zone_id, city_id FROM"
                          " infrastructure_state"):
        zone, city = row["zone_id"], row["city_id"]
        residents = len(zone_residents(store, zone))
        workers = zone_workers(store, data, zone)
        for network in NETWORKS:
            demand = residents * DEMAND_PER_RESIDENT[network] \
                + workers * WORKPLACE_FACTOR \
                * DEMAND_PER_RESIDENT[network]
            cap = store.row("SELECT capacity_units FROM"
                            " infrastructure_state WHERE zone_id = ?"
                            " AND network = ?", (zone, network))
            capacity = cap["capacity_units"] if cap else 0
            load = round(demand / capacity, 3) if capacity else 0.0
            store.execute(
                "UPDATE infrastructure_state SET demand_units = ?,"
                " load_ratio = ?, status = ?,"
                " updated_at_game_minutes = ? WHERE zone_id = ?"
                " AND network = ?",
                (round(demand, 1), load, _status(load), game_minutes,
                 zone, network))
            out[(zone, network)] = load
    return out


def monthly_effects(store, data, game_minutes):
    """Apply overloaded networks to their residents' needs.
    Returns {zone: [networks overloaded]} for reporting."""
    overloaded = {}
    for row in store.rows("SELECT zone_id, network FROM"
                          " infrastructure_state WHERE status ="
                          " 'overloaded'"):
        overloaded.setdefault(row["zone_id"], []).append(
            row["network"])
    for zone, networks in overloaded.items():
        deltas = {}
        for network in networks:
            for need, delta in OVERLOAD_EFFECTS.get(
                    network, {}).items():
                deltas[need] = max(-8, deltas.get(need, 0) + delta)
        if not deltas:
            continue
        for r in zone_residents(store, zone):
            needs_mod.adjust(store, r["character_id"], deltas,
                             game_minutes)
    return overloaded


def headroom(store, city_id):
    """The city's infrastructure headroom: 1 - worst load across
    its zones/networks (negative when anything is overloaded).
    Unit 10's growth gate reads this."""
    row = store.row("SELECT MAX(load_ratio) AS m FROM"
                    " infrastructure_state WHERE city_id = ?",
                    (city_id,))
    if row is None or row["m"] is None:
        return 1.0
    return round(1.0 - row["m"], 3)


def zone_status(store, zone_id):
    return {r["network"]: {"load_ratio": r["load_ratio"],
                           "status": r["status"]}
            for r in store.rows("SELECT * FROM infrastructure_state"
                                " WHERE zone_id = ?", (zone_id,))}
