"""Session 03 Unit 01 — City Generation & Registry.

A cities layer over the world: each city gets an identity row —
name, kind (seeded authored data vs generated town), boundary
(the union of its zone boxes), land area, climate (derived from
the world's weather-preset data, not asserted), and development /
economic classifications that Unit 10's growth engine DERIVES
from simulated facts and keeps current (refresh_registry).

setup_cities() is the Session 03 world bootstrap: it registers
both cities and runs every urban system's setup (terrain,
parcels, buildings, roads, infrastructure, regional connections)
plus the generated town's residential property stock, so
households can honestly live in Shibnagar through the same
tenancy machinery as District 1. Idempotent — existing worlds
open unchanged, and worlds built by hand in tests (which never
call it) simply have no city layer; every Session 03 engine pass
no-ops on is_setup() == False.
"""
import json

from . import buildings as buildings_mod
from . import infrastructure as infrastructure_mod
from . import parcels as parcels_mod
from . import regional as regional_mod
from . import roads as roads_mod
from . import terrain as terrain_mod
from . import zoning as zoning_mod

RUPSHA = "rupsha_city"
SHIBNAGAR = "shibnagar_town"


def is_setup(store):
    return store.row("SELECT COUNT(*) AS n FROM cities")["n"] > 0


def city_of_zone(data, zone_id):
    return data.zone_city(zone_id)


def _boundary(spec):
    boxes = list(spec["zone_boxes_m"].values())
    return {"x0": min(b["x0"] for b in boxes),
            "x1": max(b["x1"] for b in boxes),
            "z0": min(b["z0"] for b in boxes),
            "z1": max(b["z1"] for b in boxes)}


def _land_area(spec):
    return float(sum((b["x1"] - b["x0"]) * (b["z1"] - b["z0"])
                     for b in spec["zone_boxes_m"].values()))


def climate_for(data):
    """The world's climate classification, derived from the
    weather-preset weights the engine actually draws from: heavy
    rain+storm share over a long wet season is a tropical monsoon
    climate. (Both cities share one river valley and one weather
    system in v1 — stated, not hidden.)"""
    from .engine import WEATHER_WEIGHTS
    total = sum(w for _n, w in WEATHER_WEIGHTS)
    wet = sum(w for n, w in WEATHER_WEIGHTS
              if n in ("rain", "storm"))
    if wet / total >= 0.18:
        return "tropical_monsoon"
    if wet / total >= 0.08:
        return "subtropical_humid"
    return "temperate"


def setup_cities(store, data, rng, game_minutes=480):
    """Register both cities + every urban system's per-city setup
    + Shibnagar's residential property stock. Returns per-city
    setup counts. Idempotent."""
    out = {}
    for spec in data.city_specs():
        cid = spec["city_id"]
        if not store.row("SELECT 1 FROM cities WHERE city_id = ?",
                         (cid,)):
            store.insert(
                "cities", city_id=cid, name=spec["name"],
                kind=spec["kind"],
                district_label=spec["district_label"],
                boundary=json.dumps(_boundary(spec)),
                climate=climate_for(data),
                development_level="developing", development_index=0,
                economic_class="mixed_income",
                land_area_sqm=_land_area(spec),
                created_at_game_minutes=game_minutes,
                updated_at_game_minutes=game_minutes)
            for zone in spec["zones"]:
                store.insert(
                    "city_zones", zone_id=zone, city_id=cid,
                    name=zone, zone_category=zoning_mod.zone_category(
                        zone),
                    bbox=json.dumps(spec["zone_boxes_m"][zone]))
        counts = {
            "terrain": terrain_mod.setup_terrain(store, spec,
                                                 game_minutes),
            "parcels": parcels_mod.setup_parcels(store, data, spec,
                                                 game_minutes),
            "buildings": buildings_mod.setup_buildings(
                store, data, spec, rng, game_minutes),
            "roads": roads_mod.setup_roads(store, spec, game_minutes),
            "infrastructure": infrastructure_mod.setup_infrastructure(
                store, data, spec, game_minutes),
        }
        if cid == SHIBNAGAR:
            counts["property_stock"] = _setup_town_stock(
                store, data, spec)
        out[cid] = counts
    regional_mod.setup_connections(store, game_minutes)
    store.commit()
    return out


def _setup_town_stock(store, data, spec):
    """Shibnagar's residential units as property rows (vacant) —
    the same stock shape population.py creates for District 1, so
    tenancies, relocation and migration treat both cities alike."""
    if store.row("SELECT 1 FROM properties WHERE district_id LIKE"
                 " 'c2_%'"):
        return 0
    n = 0
    for u in data.residential_stock_city(spec):
        pid = store.next_id("PR", "properties", "property_id")
        store.insert(
            "properties", property_id=pid,
            property_type=u["property_type"], district_id=u["zone_id"],
            address_label=f"{u['building_name']} #{u['unit_index'] + 1}",
            tier=u["tier"], status="vacant",
            market_value=u["buy_price"] or u["rent"] * 120,
            building_ref=u["building_id"], unit_index=u["unit_index"])
        n += 1
    return n


def city_population(store, data, city_id):
    spec = data.city_spec(city_id)
    if spec is None:
        return 0
    zones = spec["zones"]
    marks = ",".join("?" for _ in zones)
    return store.row(
        f"SELECT COUNT(*) AS n FROM characters c JOIN households h"
        f" ON h.household_id = c.household_id WHERE h.district_id"
        f" IN ({marks}) AND c.is_system = 0"
        f" AND c.died_at_game_minutes IS NULL"
        f" AND h.dissolved_at_game_minutes IS NULL",
        tuple(zones))["n"]


def city_households(store, data, city_id):
    spec = data.city_spec(city_id)
    zones = spec["zones"]
    marks = ",".join("?" for _ in zones)
    return store.rows(
        f"SELECT * FROM households WHERE district_id IN ({marks})"
        f" AND dissolved_at_game_minutes IS NULL ORDER BY"
        f" household_id", tuple(zones))


def refresh_registry(store, data, game_minutes):
    """Keep each city's derived classifications current (Unit 10
    owns the metrics; this writes them onto the registry row)."""
    from . import growth as growth_mod  # late: avoids a cycle
    for spec in data.city_specs():
        m = growth_mod.city_metrics(store, data, spec["city_id"])
        store.execute(
            "UPDATE cities SET development_level = ?,"
            " development_index = ?, economic_class = ?,"
            " updated_at_game_minutes = ? WHERE city_id = ?",
            (m["development_level"], m["development_index"],
             m["economic_class"], game_minutes, spec["city_id"]))
    return True
