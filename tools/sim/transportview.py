"""Session 07 observatory — the transportation data layer.

Every figure is read from the layer's own persisted records
(vehicles, trips, road_loads, transit runs, freight shipments,
monthly statistics). Nothing is estimated here; where a number
does not exist yet, the field says so.
"""
import json

from . import transport as transport_mod


def transport_view(store, data):
    if not transport_mod.is_setup(store):
        return {"setup": False}
    vehicles = {}
    for r in store.rows(
            "SELECT vehicle_type, acquisition, COUNT(*) AS n FROM"
            " vehicles WHERE status = 'active' GROUP BY"
            " vehicle_type, acquisition ORDER BY vehicle_type"):
        vehicles[f"{r['vehicle_type']}/{r['acquisition']}"] = r["n"]
    trips_by_mode = {r["mode"]: r["n"] for r in store.rows(
        "SELECT mode, COUNT(*) AS n FROM trips GROUP BY mode"
        " ORDER BY mode")}
    hotspots = store.rows(
        "SELECT segment_id, MAX(congestion_factor) AS f,"
        " MAX(vehicle_count) AS flow FROM road_loads GROUP BY"
        " segment_id ORDER BY f DESC LIMIT 8")
    routes = []
    for r in store.rows("SELECT * FROM transit_routes ORDER BY"
                        " route_id"):
        runs = store.row(
            "SELECT COUNT(*) AS n, COALESCE(SUM(boardings),0) AS b,"
            " COALESCE(SUM(capacity),0) AS c FROM transit_runs"
            " WHERE route_id = ?", (r["route_id"],))
        routes.append({
            "route_id": r["route_id"], "kind": r["kind"],
            "name": r["name"], "stops": json.loads(r["stops_json"]),
            "headway_min": r["headway_min"],
            "runs_recorded": runs["n"], "boardings": runs["b"],
            "capacity_offered": runs["c"],
            "load_factor": round(runs["b"] / runs["c"], 3)
            if runs["c"] else None})
    shipments = store.row(
        "SELECT COUNT(*) AS n, SUM(CASE WHEN status = 'delivered'"
        " THEN 1 ELSE 0 END) AS d, ROUND(AVG(delay_min),2) AS avg_delay"
        " FROM freight_shipments")
    latest_stats = {}
    for r in store.rows(
            "SELECT scope, statistics FROM transport_statistics"
            " WHERE (scope, month_index) IN (SELECT scope,"
            " MAX(month_index) FROM transport_statistics"
            " GROUP BY scope)"):
        latest_stats[r["scope"]] = json.loads(r["statistics"])
    return {
        "setup": True,
        "vehicles_active_by_type": vehicles,
        "trips_total": store.row("SELECT COUNT(*) AS n FROM trips")
        ["n"],
        "trips_by_mode": trips_by_mode,
        "fares_total_ncr": store.row(
            "SELECT COALESCE(SUM(fare_ncr),0) AS s FROM trips")["s"],
        "congestion_hotspots": [
            {"segment_id": h["segment_id"],
             "max_factor": h["f"], "peak_hour_flow": h["flow"]}
            for h in hotspots],
        "transit_routes": routes,
        "freight": {"shipments": shipments["n"] or 0,
                    "delivered": shipments["d"] or 0,
                    "avg_delay_min": shipments["avg_delay"]},
        "latest_month_statistics": latest_stats,
        "methodology": {
            "traffic": "congestion factors are tallied from the"
                       " day's own recorded vehicle trips per"
                       " (segment, hour) against roads.py class"
                       " capacities; see data/transport-config.json",
            "fares": "taxi fares are prices.json taxi_fares;"
                     " bus/rickshaw/ferry are covered by the"
                     " monthly transport_public_bus_rickshaw line",
            "rail_air": "no rail/air operations run: no track or"
                        " airfield network data exists in the"
                        " merged data (a station plot exists as a"
                        " building only)",
        },
    }
