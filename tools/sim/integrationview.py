"""Session 10 — Integration observatory (data layer only).

Every figure here is read from the world's own records: the
event registry, the persisted technology levels (with their
basis), and the consolidated resource balances. Historical
playback is exactly this: read-only queries over persisted
records — opening a view never advances or mutates the world.
"""
import json

from . import integration as integration_mod


def events_view(store, data):
    by_type = {r["event_type"]: r["n"] for r in store.rows(
        "SELECT event_type, COUNT(*) AS n FROM world_events"
        " GROUP BY event_type ORDER BY event_type")}
    by_source = {r["source"]: r["n"] for r in store.rows(
        "SELECT source, COUNT(*) AS n FROM world_events"
        " GROUP BY source ORDER BY source")}
    by_city = {str(r["city_id"]): r["n"] for r in store.rows(
        "SELECT city_id, COUNT(*) AS n FROM world_events"
        " GROUP BY city_id ORDER BY city_id")}
    recent = []
    for r in store.rows("SELECT * FROM world_events ORDER BY"
                        " game_minutes DESC, event_id DESC"
                        " LIMIT 20"):
        row = dict(r)
        row["entity_refs"] = json.loads(row["entity_refs"])
        row["details"] = json.loads(row["details"])
        recent.append(row)
    return {"total_events": sum(by_type.values()),
            "by_type": by_type, "by_source": by_source,
            "by_city": by_city, "recent": recent,
            "note": "The registry is an index over the source"
                    " history tables (life_events, elections,"
                    " disaster_events, social_events,"
                    " construction_projects, research_records,"
                    " agreements, policies, crisis_records,"
                    " business_events, government_events), which"
                    " remain the immutable originals."}


def technology_view(store, data):
    history = {}
    for r in store.rows("SELECT field, month_index, level, basis"
                        " FROM technology_levels ORDER BY field,"
                        " month_index"):
        history.setdefault(r["field"], []).append(
            {"month_index": r["month_index"], "level": r["level"],
             "basis": json.loads(r["basis"])})
    return {"latest": integration_mod.latest_technology(store),
            "history": history,
            "method": data.integration_config["technology"]
            ["basis"],
            "consumer": "Session 06 research capability gain per"
                        " completed project is multiplied by"
                        " (1 + capability_factor_per_level *"
                        " level) for the project's field; exactly"
                        " 1.0 before any level is recorded."}


def resources_view(store, data):
    return integration_mod.resource_report(store, data)
