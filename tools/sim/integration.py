"""Session 10 — Global Integration layer.

This layer READS and INDEXES Sessions 01–09; it replaces none of
them. Four pieces, each additive:

1. **Unified event registry** (`world_events`): a daily sync
   copies references from the existing history tables
   (life_events, elections, disaster_events, social_events,
   construction_projects, research_records, agreements,
   policies, crisis_records, business_events, government_events)
   into one normalised index — event type, sim timestamp, city,
   entity refs, source subsystem. The source tables remain the
   immutable originals; the registry never writes to them, and
   its UNIQUE (source_table, source_id) constraint plus per-
   source rowid watermarks make the sync idempotent and
   restart-safe. Events whose source row is not final yet
   (a scheduled election, an unfinished construction project,
   an unsigned agreement, a merely-proposed policy) are indexed
   only once they complete — a deferred scan handles those.

2. **Technology levels** (`technology_levels`): a monthly
   derived index, computed by the documented formula in
   data/integration-config.json from research_records
   (publications per field) and the measured credentialed share
   of living adults (Session 06 certifications). The basis is
   stored on every row. The level has exactly one consumer: the
   Session 06 research engine's capability gain per completed
   project is multiplied by (1 + factor_per_level * level) for
   the project's field — with no levels recorded the factor is
   exactly 1.0 and Session 06 behaviour is unchanged.

3. **Global scenarios**: the configured, labelled exogenous
   door (the Session 04 pattern). trigger_global_scenario opens
   a crisis_record naming the scenario; propagation is the
   Session 04 crisis effects surface (demand factor on household
   consumption + intercity trade movement); the integration
   monthly pass resolves the record after its configured
   duration. Nothing fires unconfigured.

4. **Resource balance**: a consolidated per-city report from
   existing records only (business_inventory, inventory_
   movements, household_consumption, env_water_state,
   env_snapshots, vehicles, transport_statistics). Shortage
   flags are raised only on the documented bases in the config.

The GameClock remains the single clock: this layer reads
world_state.game_minutes / day_index like every other layer and
keeps no time of its own.
"""
import json


def cfg(data):
    return data.integration_config


def is_setup(store):
    w = store.world()
    return bool(w and w.get("integration_setup"))


def setup_integration(store, data, game_minutes=480):
    """Seed the integration layer (idempotent): the setup flag.
    The registry sync itself is watermark-driven, so a world
    that gains the layer late indexes its whole history on the
    first sync — nothing is lost by seeding order."""
    if is_setup(store):
        return {"integration": "already set up"}
    store.set_world(integration_setup=1)
    store.commit()
    return {"integration": "ready"}


# ---------------------------------------------------------------------
# 1. Unified event registry
# ---------------------------------------------------------------------

def _city_maps(store):
    """(zone->city, household->(city, zone), character->household)
    from the Session 03 city layer; empty maps when the layer is
    absent (hand-built worlds), in which case city stays None."""
    zone_city = {r["zone_id"]: r["city_id"] for r in store.rows(
        "SELECT zone_id, city_id FROM city_zones")}
    households = {}
    for r in store.rows(
            "SELECT h.household_id AS hid, p.district_id AS zone"
            " FROM households h JOIN properties p"
            " ON p.property_id = h.home_property_id"):
        households[r["hid"]] = (zone_city.get(r["zone"]), r["zone"])
    char_hh = {r["character_id"]: r["household_id"] for r in
               store.rows("SELECT character_id, household_id"
                          " FROM characters")}
    return zone_city, households, char_hh


def _char_place(maps, character_id):
    _, households, char_hh = maps
    hid = char_hh.get(character_id)
    if hid is None:
        return None, None
    return households.get(hid, (None, None))


def _insert_event(store, event_type, game_minutes, city_id, zone_id,
                  entity_refs, source, source_table, source_id,
                  details=None):
    eid = store.next_id("WE", "world_events", "event_id")
    cur = store.execute(
        "INSERT OR IGNORE INTO world_events (event_id, event_type,"
        " game_minutes, day_index, city_id, zone_id, entity_refs,"
        " source, source_table, source_id, status, details)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'recorded', ?)",
        (eid, event_type, game_minutes, game_minutes // 1440,
         city_id, zone_id, json.dumps(entity_refs, sort_keys=True),
         source, source_table, source_id,
         json.dumps(details or {}, sort_keys=True)))
    return cur.rowcount


# -- append sources: rows are final at insert; watermark by rowid --

def _sync_life_events(store, maps, watermark):
    n = 0
    rows = store.rows(
        "SELECT rowid AS _rid, * FROM life_events WHERE rowid > ?"
        " ORDER BY rowid", (watermark,))
    for r in rows:
        city, zone = _char_place(maps, r["character_id"])
        n += _insert_event(
            store, r["event_type"], r["game_minutes"], city, zone,
            {"character_id": r["character_id"],
             "other_character_id": r["other_character_id"]},
            "life", "life_events", r["event_id"],
            {"details": json.loads(r["details"])})
        watermark = r["_rid"]
    return n, watermark


def _sync_disasters(store, maps, watermark):
    n = 0
    rows = store.rows(
        "SELECT rowid AS _rid, * FROM disaster_events"
        " WHERE rowid > ? ORDER BY rowid", (watermark,))
    for r in rows:
        n += _insert_event(
            store, "disaster", r["created_at_game_minutes"],
            r["city_id"], None, {"disaster_id": r["disaster_id"]},
            "environment", "disaster_events", r["disaster_id"],
            {"disaster_type": r["disaster_type"],
             "scenario_id": r["scenario_id"],
             "status_at_sync": r["status"],
             "affected_population": r["affected_population"],
             "damage_estimate_ncr": r["damage_estimate_ncr"]})
        watermark = r["_rid"]
    return n, watermark


def _sync_social_events(store, maps, watermark):
    n = 0
    rows = store.rows(
        "SELECT rowid AS _rid, * FROM social_events"
        " WHERE rowid > ? ORDER BY rowid", (watermark,))
    for r in rows:
        city = maps[0].get(r["zone_id"])
        n += _insert_event(
            store, r["event_type"], r["game_minutes"], city,
            r["zone_id"],
            {"participants": json.loads(r["participant_ids"])},
            "society", "social_events", r["event_id"],
            {"location_label": r["location_label"],
             "outcome": json.loads(r["outcome"])})
        watermark = r["_rid"]
    return n, watermark


def _sync_research_records(store, maps, watermark):
    n = 0
    rows = store.rows(
        "SELECT rowid AS _rid, * FROM research_records"
        " WHERE rowid > ? ORDER BY rowid", (watermark,))
    for r in rows:
        n += _insert_event(
            store, "scientific_discovery", r["game_minutes"], None,
            None,
            {"record_id": r["record_id"],
             "project_id": r["project_id"],
             "institution_id": r["institution_id"]},
            "humandev", "research_records", r["record_id"],
            {"field": r["field"], "kind": r["kind"]})
        watermark = r["_rid"]
    return n, watermark


def _sync_crises(store, maps, watermark):
    n = 0
    rows = store.rows(
        "SELECT rowid AS _rid, * FROM crisis_records"
        " WHERE rowid > ? ORDER BY rowid", (watermark,))
    for r in rows:
        details = json.loads(r["details"])
        n += _insert_event(
            store, "economic_crisis", r["opened_at_game_minutes"],
            None, None, {"crisis_id": r["crisis_id"]},
            "economy", "crisis_records", r["crisis_id"],
            {"crisis_type": r["crisis_type"],
             "source": details.get("source"),
             "scenario": (details.get("scenario") or {}).get("id")})
        watermark = r["_rid"]
    return n, watermark


_BUSINESS_TYPE_MAP = {"registered": "business_formation",
                      "system_foundation": "business_formation",
                      "closed": "business_failure"}


def _sync_business_events(store, maps, watermark):
    n = 0
    rows = store.rows(
        "SELECT rowid AS _rid, * FROM business_events"
        " WHERE rowid > ? ORDER BY rowid", (watermark,))
    for r in rows:
        watermark = r["_rid"]
        etype = _BUSINESS_TYPE_MAP.get(r["event_type"])
        if etype is None:
            continue  # state changes (distress/recovered) are not
            # major events; the business's own log keeps them.
        biz = store.row("SELECT property_id FROM businesses"
                        " WHERE business_id = ?", (r["business_id"],))
        zone = None
        if biz and biz["property_id"]:
            p = store.row("SELECT district_id FROM properties"
                          " WHERE property_id = ?",
                          (biz["property_id"],))
            zone = p["district_id"] if p else None
        n += _insert_event(
            store, etype, r["game_minutes"], maps[0].get(zone), zone,
            {"business_id": r["business_id"]},
            "economy", "business_events", r["event_id"],
            {"business_event_type": r["event_type"]})
    return n, watermark


def _sync_government_events(store, maps, watermark):
    n = 0
    rows = store.rows(
        "SELECT rowid AS _rid, * FROM government_events"
        " WHERE rowid > ? ORDER BY rowid", (watermark,))
    for r in rows:
        city, zone = _char_place(maps, r["actor_character_id"])
        n += _insert_event(
            store, r["event_type"], r["game_minutes"], city, zone,
            {"actor_character_id": r["actor_character_id"]},
            "government", "government_events", r["event_id"],
            {"details": json.loads(r["details"])})
        watermark = r["_rid"]
    return n, watermark


_APPEND_SOURCES = (
    ("life_events", _sync_life_events),
    ("disaster_events", _sync_disasters),
    ("social_events", _sync_social_events),
    ("research_records", _sync_research_records),
    ("crisis_records", _sync_crises),
    ("business_events", _sync_business_events),
    ("government_events", _sync_government_events),
)


# -- deferred sources: indexed once the source row is final ---------

def _sync_deferred(store, maps):
    n = 0
    for r in store.rows("SELECT * FROM elections"
                        " WHERE game_minutes IS NOT NULL"
                        " ORDER BY election_id"):
        n += _insert_event(
            store, "election", r["game_minutes"], None, None,
            {"election_id": r["election_id"],
             "country_id": r["country_id"],
             "winner_party_id": r["winner_party_id"]},
            "government", "elections", r["election_id"],
            {"turnout": r["turnout"], "eligible": r["eligible"],
             "month_index": r["month_index"]})
    for r in store.rows("SELECT * FROM construction_projects"
                        " WHERE status = 'completed'"
                        " ORDER BY project_id"):
        gm = r["updated_at_game_minutes"] or \
            (r["completed_day"] or r["created_day"]) * 1440
        n += _insert_event(
            store, "construction_completed", gm, r["city_id"], None,
            {"project_id": r["project_id"],
             "result_building_id": r["result_building_id"]},
            "city", "construction_projects", r["project_id"],
            {"kind": r["kind"]})
    for r in store.rows("SELECT * FROM agreements"
                        " WHERE status IN ('signed', 'active')"
                        " ORDER BY agreement_id"):
        n += _insert_event(
            store, "international_agreement",
            r["created_at_game_minutes"], None, None,
            {"agreement_id": r["agreement_id"],
             "partner_id": r["partner_id"]},
            "government", "agreements", r["agreement_id"],
            {"kind": r["kind"], "status": r["status"]})
    for r in store.rows("SELECT * FROM policies"
                        " WHERE status != 'proposed'"
                        " ORDER BY policy_id"):
        n += _insert_event(
            store, "policy_enacted", r["created_at_game_minutes"],
            r["city_id"], None,
            {"policy_id": r["policy_id"], "kind": r["kind"]},
            "government", "policies", r["policy_id"],
            {"title": r["title"], "status": r["status"],
             "budget_ncr": r["budget_ncr"]})
    return n


def sync_event_registry(store, data):
    """Index every not-yet-indexed source record into
    world_events. Idempotent (watermarks + the UNIQUE
    constraint); restart-safe (watermarks persist in
    event_sync_state); append-only (source tables are only
    read). Returns the number of newly indexed events by
    source."""
    maps = _city_maps(store)
    out = {}
    total = 0
    for table, fn in _APPEND_SOURCES:
        row = store.row("SELECT last_rowid FROM event_sync_state"
                        " WHERE source_table = ?", (table,))
        watermark = row["last_rowid"] if row else 0
        n, watermark = fn(store, maps, watermark)
        store.execute(
            "INSERT INTO event_sync_state (source_table, last_rowid)"
            " VALUES (?, ?) ON CONFLICT(source_table) DO UPDATE SET"
            " last_rowid = excluded.last_rowid", (table, watermark))
        out[table] = n
        total += n
    n = _sync_deferred(store, maps)
    out["deferred"] = n
    total += n
    out["indexed"] = total
    return out


# ---------------------------------------------------------------------
# 2. Technology levels
# ---------------------------------------------------------------------

def _credentialed_share(store, game_minutes):
    adults = store.row(
        "SELECT COUNT(*) AS n FROM characters WHERE is_system = 0"
        " AND died_at_game_minutes IS NULL AND (? -"
        " born_at_game_minutes) >= ?", (game_minutes,
                                        18 * 365 * 1440))["n"]
    if not adults:
        return 0.0, 0
    certs = store.row(
        "SELECT COUNT(DISTINCT character_id) AS n FROM"
        " certifications")["n"]
    return certs / adults, adults


def compute_technology(store, data, month_index, game_minutes):
    """Recompute + persist the technology level of every field
    for the month, with its basis. Formula (documented in the
    config): level = min(max_level, publications_weight *
    publications(field) + education_weight * credentialed_share).
    """
    tc = cfg(data)["technology"]
    share, adults = _credentialed_share(store, game_minutes)
    levels = {}
    for field, spec in tc["fields"].items():
        fields = spec["research_fields"]
        marks = ", ".join("?" for _ in fields)
        pubs = store.row(
            f"SELECT COUNT(*) AS n FROM research_records"
            f" WHERE field IN ({marks})", tuple(fields))["n"]
        level = min(tc["max_level"],
                    tc["publications_weight"] * pubs
                    + tc["education_weight"] * share)
        basis = {"publications": pubs,
                 "research_fields": fields,
                 "credentialed_share": round(share, 4),
                 "credentialed_adults_basis": adults,
                 "formula": "min(max_level, publications_weight *"
                            " publications + education_weight *"
                            " credentialed_share)"}
        store.execute(
            "INSERT OR REPLACE INTO technology_levels (field,"
            " month_index, level, basis, game_minutes) VALUES"
            " (?, ?, ?, ?, ?)",
            (field, month_index, round(level, 4),
             json.dumps(basis, sort_keys=True), game_minutes))
        levels[field] = round(level, 4)
    return levels


def technology_factor(store, data, research_field):
    """The research capability multiplier for a research field:
    1 + capability_factor_per_level * level(its technology
    field), from the latest persisted levels. Exactly 1.0 when
    the integration layer is absent or no level is recorded —
    Session 06 behaviour is then unchanged."""
    if not is_setup(store):
        return 1.0
    tc = cfg(data)["technology"]
    tech_field = next(
        (f for f, spec in tc["fields"].items()
         if research_field in spec["research_fields"]), None)
    if tech_field is None:
        return 1.0
    row = store.row("SELECT level FROM technology_levels WHERE"
                    " field = ? ORDER BY month_index DESC LIMIT 1",
                    (tech_field,))
    if row is None:
        return 1.0
    return 1.0 + tc["capability_factor_per_level"] * row["level"]


def latest_technology(store):
    out = {}
    for r in store.rows("SELECT field, level, month_index, basis"
                        " FROM technology_levels ORDER BY field,"
                        " month_index"):
        out[r["field"]] = {"level": r["level"],
                           "month_index": r["month_index"],
                           "basis": json.loads(r["basis"])}
    return out


# ---------------------------------------------------------------------
# 3. Global scenarios
# ---------------------------------------------------------------------

def trigger_global_scenario(store, data, scenario_id, month_index,
                              game_minutes):
    """Open a configured global scenario through the Session 04
    crisis machinery. Unknown ids raise; re-triggering an active
    scenario returns the existing record (no duplicates)."""
    scen = next((s for s in cfg(data)["global_scenarios"]
                 ["scenarios"] if s["id"] == scenario_id), None)
    if scen is None:
        raise ValueError(f"unknown global scenario {scenario_id}")
    for c in store.rows("SELECT * FROM crisis_records WHERE"
                        " status = 'active'"):
        details = json.loads(c["details"])
        if details.get("source") == "global_scenario" and \
                (details.get("scenario") or {}).get("id") \
                == scenario_id:
            return c["crisis_id"]
    cid = store.next_id("CR", "crisis_records", "crisis_id")
    store.insert(
        "crisis_records", crisis_id=cid,
        crisis_type=scen["crisis_type"], scope="global",
        status="active",
        severity=json.dumps({"scenario": scen}, sort_keys=True),
        opened_month=month_index,
        opened_at_game_minutes=game_minutes,
        details=json.dumps(
            {"source": "global_scenario",
             "scenario": {"id": scen["id"], "title": scen["title"],
                          "takings_factor": scen["takings_factor"],
                          "duration_months":
                          scen["duration_months"]}},
            sort_keys=True))
    return cid


def _close_global_scenarios(store, month_index, game_minutes):
    closed = []
    for c in store.rows("SELECT * FROM crisis_records WHERE"
                        " status = 'active'"):
        details = json.loads(c["details"])
        if details.get("source") != "global_scenario":
            continue
        scen = details.get("scenario") or {}
        if month_index >= c["opened_month"] \
                + scen.get("duration_months", 1):
            store.execute(
                "UPDATE crisis_records SET status = 'resolved',"
                " resolved_at_game_minutes = ? WHERE crisis_id"
                " = ?", (game_minutes, c["crisis_id"]))
            closed.append(c["crisis_id"])
    return closed


# ---------------------------------------------------------------------
# 4. Resource balance
# ---------------------------------------------------------------------

def resource_report(store, data):
    """Consolidated per-city resource balances from existing
    records only. See data/integration-config.json 'resources'
    for the sources and the shortage-flag bases."""
    rc = cfg(data)["resources"]
    world = store.world()
    now = world["game_minutes"]
    window_start = now - 30 * 1440
    cities = [r["city_id"] for r in store.rows(
        "SELECT city_id FROM cities ORDER BY city_id")] or \
        [r["city_id"] for r in store.rows(
            "SELECT DISTINCT city_id FROM city_zones"
            " ORDER BY city_id")]
    report = {"day_index": world["day_index"], "cities": {},
              "method": rc["basis"]}
    for city_id in cities:
        stored = {}
        for r in store.rows(
                "SELECT bi.good_id AS g, SUM(bi.quantity) AS q"
                " FROM business_inventory bi"
                " JOIN businesses b ON b.business_id = bi.business_id"
                " JOIN properties p ON p.property_id = b.property_id"
                " JOIN city_zones cz ON cz.zone_id = p.district_id"
                " WHERE cz.city_id = ? GROUP BY bi.good_id",
                (city_id,)):
            stored[r["g"]] = round(r["q"], 3)
        residents = store.row(
            "SELECT COUNT(*) AS n FROM characters c"
            " JOIN households h ON h.household_id = c.household_id"
            " JOIN properties p ON p.property_id = h.home_property_id"
            " JOIN city_zones cz ON cz.zone_id = p.district_id"
            " WHERE cz.city_id = ? AND c.is_system = 0"
            " AND c.died_at_game_minutes IS NULL", (city_id,))["n"]
        production = {}
        for r in store.rows(
                "SELECT im.good_id AS g, SUM(im.delta) AS q"
                " FROM inventory_movements im"
                " JOIN businesses b ON b.business_id = im.business_id"
                " JOIN properties p ON p.property_id = b.property_id"
                " JOIN city_zones cz ON cz.zone_id = p.district_id"
                " WHERE cz.city_id = ? AND im.kind IN ('production',"
                " 'harvest') AND im.game_minutes > ?"
                " AND im.game_minutes <= ? GROUP BY im.good_id",
                (city_id, window_start, now)):
            production[r["g"]] = round(r["q"], 3)
        latest_month = store.row(
            "SELECT MAX(month_index) AS m FROM household_consumption"
        )["m"]
        consumption = {}
        if latest_month is not None:
            for r in store.rows(
                    "SELECT hc.good_id AS g, SUM(hc.units) AS q"
                    " FROM household_consumption hc"
                    " JOIN households h ON h.household_id ="
                    " hc.household_id JOIN properties p"
                    " ON p.property_id = h.home_property_id"
                    " JOIN city_zones cz ON cz.zone_id ="
                    " p.district_id WHERE cz.city_id = ?"
                    " AND hc.month_index = ? GROUP BY hc.good_id",
                    (city_id, latest_month)):
                consumption[r["g"]] = round(r["q"], 3)
        food_stored = stored.get("food_basket", 0) \
            + stored.get("fish", 0)
        cover = (food_stored / residents) if residents else None
        water_row = store.row("SELECT * FROM env_water_state"
                              " WHERE city_id = ?", (city_id,))
        snap = store.row("SELECT metrics FROM env_snapshots WHERE"
                         " city_id = ? ORDER BY month_index DESC"
                         " LIMIT 1", (city_id,))
        snap_metrics = json.loads(snap["metrics"]) if snap else {}
        fuel_stored = store.row(
            "SELECT COALESCE(SUM(fuel_litres), 0) AS q FROM vehicles"
            " WHERE city_id = ? AND status = 'active'",
            (city_id,))["q"]
        tstat = store.row("SELECT statistics FROM"
                          " transport_statistics WHERE scope = ?"
                          " ORDER BY month_index DESC LIMIT 1",
                          (city_id,))
        tstats = json.loads(tstat["statistics"]) if tstat else {}
        flags = []
        if cover is not None and cover \
                < rc["food_shortage_min_months_cover"]:
            flags.append("food_shortage_risk")
        if water_row and water_row["groundwater_index"] \
                < rc["water_stress_max_groundwater_index"]:
            flags.append("water_stress")
        report["cities"][city_id] = {
            "residents": residents,
            "stored_goods": stored,
            "production_last_30d": production,
            "consumption_latest_month": consumption,
            "food": {
                "stored_units": round(food_stored, 3),
                "months_cover_per_resident":
                    round(cover, 4) if cover is not None else None,
                "note": "food_basket units are adult-months;"
                        " fish units are household-months — the"
                        " cover figure sums both as stored food"
                        " units per resident (documented"
                        " approximation)."},
            "water": {
                "river_level_m": water_row["river_level_m"]
                if water_row else None,
                "groundwater_index": water_row["groundwater_index"]
                if water_row else None,
                "surface_storage_mm": water_row["surface_storage_mm"]
                if water_row else None,
                "availability_index": snap_metrics.get(
                    "water_availability_index")},
            "energy_fuel": {
                "fuel_stored_litres": round(fuel_stored, 1),
                "fuel_consumed_latest_month_litres":
                    tstats.get("fuel_litres"),
                "note": "fuel is tracked as quantities only — no"
                        " fuel price exists in the design data"
                        " (Session 07)."},
            "construction_materials": {
                "manufactured_goods_stored":
                    stored.get("manufactured_goods", 0),
                "agricultural_produce_stored":
                    stored.get("agricultural_produce", 0),
                "note": "manufactured_goods is the sim's"
                        " construction-scale lot good (Session 04"
                        " goods catalogue)."},
            "shortage_flags": flags,
        }
    return report


# ---------------------------------------------------------------------
# Cadences (engine wiring)
# ---------------------------------------------------------------------

def daily_pass(store, data, rng, day_index, game_minutes):
    """The registry sync — runs at the end of every simulated
    day, after every other layer's daily pass, so the day's
    events from all subsystems are indexed the day they
    happen."""
    if not is_setup(store):
        return {}
    return sync_event_registry(store, data)


def monthly_pass(store, data, rng, month_index, game_minutes):
    """Technology recomputation + global-scenario lifecycle,
    over the settled month."""
    if not is_setup(store):
        return {}
    levels = compute_technology(store, data, month_index,
                                game_minutes)
    closed = _close_global_scenarios(store, month_index,
                                     game_minutes)
    return {"technology_levels": levels,
            "global_scenarios_resolved": closed}
