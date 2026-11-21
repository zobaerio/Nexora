"""Session 08 — Environment observatory (data layer only).

Every value is read from the environment layer's own records:
regional weather, water state, soil, crops, vegetation/wildlife
indices, pollution with its source breakdown, climate trend
snapshots and disaster records. All conditions are SIMULATED —
the view says so on its face, and never presents a simulated
value as a real-world observation.
"""
import json

from . import environment as env_mod


def environment_view(store, data):
    if not env_mod.is_setup(store):
        return {"environment_setup": False}
    cities = {}
    for spec in data.city_specs():
        cid = spec["city_id"]
        weather = store.rows(
            "SELECT * FROM env_weather WHERE region_id = ? ORDER BY"
            " day_index DESC LIMIT 7", (cid,))
        water = store.row("SELECT * FROM env_water_state WHERE"
                          " city_id = ?", (cid,))
        snapshots = store.rows(
            "SELECT month_index, metrics FROM env_snapshots WHERE"
            " city_id = ? ORDER BY month_index", (cid,))
        pollution = store.rows(
            "SELECT month_index, air_index, water_index, sources"
            " FROM env_pollution WHERE city_id = ? ORDER BY"
            " month_index", (cid,))
        cities[cid] = {
            "recent_weather": [dict(w) for w in reversed(weather)],
            "water_state": dict(water) if water else None,
            "exposed_zones": env_mod.exposed_zones(store, data, cid),
            "climate_trend_snapshots": [
                {"month_index": s["month_index"],
                 **json.loads(s["metrics"])} for s in snapshots],
            "pollution": [
                {"month_index": p["month_index"],
                 "air_index": p["air_index"],
                 "water_index": p["water_index"],
                 "sources": json.loads(p["sources"])}
                for p in pollution],
            "vegetation": [dict(v) for v in store.rows(
                "SELECT * FROM env_vegetation WHERE city_id = ?",
                (cid,))],
            "wildlife_indices": [dict(w) for w in store.rows(
                "SELECT * FROM env_wildlife WHERE city_id = ?",
                (cid,))],
            "soil": [dict(s) for s in store.rows(
                "SELECT es.* FROM env_soil es JOIN land_parcels lp"
                " ON lp.parcel_id = es.parcel_id WHERE lp.city_id"
                " = ?", (cid,))],
        }
    disasters = [dict(d) for d in store.rows(
        "SELECT * FROM disaster_events ORDER BY started_day")]
    for d in disasters:
        d["impacts"] = store.row(
            "SELECT COUNT(*) AS n FROM disaster_impacts WHERE"
            " disaster_id = ?", (d["disaster_id"],))["n"]
        d["responses"] = [dict(r) for r in store.rows(
            "SELECT action, COUNT(*) AS n, COALESCE(SUM(amount_ncr),"
            " 0) AS total FROM disaster_responses WHERE disaster_id"
            " = ? GROUP BY action", (d["disaster_id"],))]
    crops = store.rows(
        "SELECT crop_id, status, COUNT(*) AS n, COALESCE(SUM"
        "(harvest_units), 0) AS units FROM env_crops GROUP BY"
        " crop_id, status")
    return {
        "environment_setup": True,
        "simulated": True,
        "note": "All conditions are simulated by the Session 08"
                " SIM MODEL layer — not real-world observations"
                " and not scientific forecasts.",
        "emission_limit_reduction_percent":
            env_mod.effective_emission_reduction(store),
        "cities": cities,
        "disasters": disasters,
        "crops": [dict(c) for c in crops],
        "summary": env_mod.environment_summary(store),
    }
