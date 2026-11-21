"""Session 03 Unit 13 — City Analytics Engine.

Every statistic is computed from live simulation rows at call
time — population from households, housing from properties,
employment from employments, land from parcels, buildings from
building_state, roads from the graph + segment condition,
infrastructure from infrastructure_state, construction from
construction_projects, municipal from the budget tables. Nothing
is cached from a previous state of the world: run the sim,
change something, re-read, and the analytics have moved (the
acceptance test does exactly that). Monthly snapshots persist
the same computation into city_statistics for history.
"""
import json

from . import cities as cities_mod
from . import distribution as distribution_mod
from . import growth as growth_mod
from . import roads as roads_mod


def city_analytics(store, data, city_id):
    spec = data.city_spec(city_id)
    if spec is None:
        return None
    metrics = growth_mod.city_metrics(store, data, city_id)
    zones = spec["zones"]
    marks = ",".join("?" for _ in zones)
    land = store.row(
        "SELECT COUNT(*) AS n, AVG(market_value) AS avg_v,"
        " SUM(market_value) AS total_v FROM land_parcels WHERE"
        " city_id = ?", (city_id,))
    buildings = store.rows(
        "SELECT bs.building_id, bs.condition FROM building_state bs"
        " WHERE bs.city_id = ?", (city_id,))
    by_condition = {"good": 0, "fair": 0, "poor": 0, "critical": 0}
    from . import buildings as buildings_mod
    for b in buildings:
        by_condition[buildings_mod.condition_band(b["condition"])] \
            += 1
    graph = roads_mod.build_graph(spec)
    comps = roads_mod.components(graph, "walk")
    seg = store.row("SELECT COUNT(*) AS n, SUM(length_m) AS km,"
                    " AVG(condition) AS c FROM road_segments WHERE"
                    " city_id = ?", (city_id,))
    infra = {r["network"]: {"load": round(r["l"], 3),
                            "status": "overloaded" if r["l"] >= 1
                            else ("strained" if r["l"] >= 0.85
                                  else "ok")}
             for r in store.rows(
                 "SELECT network, MAX(load_ratio) AS l FROM"
                 " infrastructure_state WHERE city_id = ? GROUP BY"
                 " network", (city_id,))}
    construction = {
        r["status"]: r["n"] for r in store.rows(
            "SELECT status, COUNT(*) AS n FROM construction_projects"
            " WHERE city_id = ? GROUP BY status", (city_id,))}
    budget = store.row("SELECT * FROM municipal_budgets WHERE"
                       " city_id = ? ORDER BY month_index DESC"
                       " LIMIT 1", (city_id,))
    density = {z: distribution_mod.zone_density(store, data, z)
               for z in zones}
    return {
        "city_id": city_id, "name": spec["name"],
        "population": metrics["population"],
        "households": metrics["households"],
        "population_density_per_km2": round(
            metrics["population"]
            / (sum((b["x1"] - b["x0"]) * (b["z1"] - b["z0"])
                   for b in spec["zone_boxes_m"].values())
               / 1_000_000), 1),
        "zone_density_per_km2": density,
        "housing": metrics["housing"],
        "residential_demand": distribution_mod.residential_demand(
            store, data, city_id),
        "employment_rate": metrics["employment_rate"],
        "band_mix": metrics["band_mix"],
        "land": {"parcels": land["n"],
                 "avg_parcel_value_ncr": int(land["avg_v"] or 0),
                 "total_land_value_ncr": int(land["total_v"] or 0)},
        "buildings": {"count": len(buildings),
                      "avg_condition": metrics[
                          "avg_building_condition"],
                      "by_condition": by_condition},
        "roads": {"segments": seg["n"],
                  "total_km": round((seg["km"] or 0) / 1000, 2),
                  "avg_condition": round(seg["c"] or 0, 1),
                  "graph_components_walk": len(comps),
                  "graph_nodes": len(graph.nodes)},
        "infrastructure": infra,
        "construction": construction,
        "municipal": ({"month_index": budget["month_index"],
                       "revenue_tax_ncr": budget["revenue_tax_ncr"],
                       "revenue_rent_ncr": budget[
                           "revenue_rent_ncr"],
                       "spend_services_ncr": budget[
                           "spend_services_ncr"]}
                      if budget else None),
        "development": {"index": metrics["development_index"],
                        "level": metrics["development_level"],
                        "economic_class": metrics["economic_class"],
                        "services_level": metrics["services_level"],
                        "infra_headroom": metrics["infra_headroom"]},
    }


def record_snapshots(store, data, month_index, game_minutes):
    """Persist the month's analytics for both cities (history the
    growth engine reads last month's population from)."""
    out = {}
    for spec in data.city_specs():
        a = city_analytics(store, data, spec["city_id"])
        store.execute(
            "INSERT OR REPLACE INTO city_statistics (city_id,"
            " month_index, metrics, game_minutes) VALUES (?, ?, ?, ?)",
            (spec["city_id"], month_index, json.dumps(a),
             game_minutes))
        out[spec["city_id"]] = a
    return out
