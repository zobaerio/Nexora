"""Session 03 Unit 14 — Multi-City Interaction.

Two cities, connected in fact, not in prose:

- a ROAD connection: Rupsha City's bridge approach (GDD-02 §4:
  the crossing is a Phase 8 travel gate — the approach and toll
  plaza are District 1 geometry) meets Shibnagar's Main Street at
  its ghat gate. intercity_route() pathfinds through both cities'
  graphs and the connection, so a route from Boro Bazar to
  Shibnagar Bazar exists or fails honestly;
- a FERRY connection at the two ghats (river transport, the
  launch-terminal economy of GDD-02);
- MIGRATION (Unit 08's distribution pass writes migration_records)
  and EMPLOYMENT MOBILITY: residents of one city whose profession
  works in the other are intercity commuters — counted from live
  employments, persisted monthly on the connection rows;
- TRADE: a monthly flow between the cities, sized by measured
  facts — District 1's industry-zone employment produces
  manufactured goods Shibnagar's population demands; Shibnagar's
  farmland and population produce agricultural goods Rupsha
  demands. The per-worker/per-capita rates are SIM MODEL
  constants (labelled); the flows are accounting records in
  trade_flows (intercity settlement rides the SYS-MARKET aggregate,
  like business revenue in Session 01 — no character money is
  created or destroyed by a flow row).
"""
from . import roads as roads_mod

# SIM MODEL constants (see docstring).
TRADE_PER_INDUSTRY_WORKER_NCR = 1500
TRADE_DEMAND_PER_RESIDENT_NCR = 40
TRADE_PER_FARMLAND_PARCEL_NCR = 800
TRADE_PRODUCE_PER_RESIDENT_NCR = 25

CONNECTIONS = (
    {"connection_id": "RC-ROAD-1", "kind": "road_bridge",
     "via": "seg_bridge_approach + Shibnagar Main Street (bridge "
            "crossing is a Phase 8 travel gate, GDD-02 §4)"},
    {"connection_id": "RC-FERRY-1", "kind": "ferry",
     "via": "Rupsha Ghat (0, 432) <-> Shibnagar Ghat (280, 0)"},
)


def setup_connections(store, game_minutes):
    for c in CONNECTIONS:
        store.execute(
            "INSERT OR IGNORE INTO regional_connections"
            " (connection_id, from_city_id, to_city_id, kind, via,"
            " status, updated_at_game_minutes)"
            " VALUES (?, 'rupsha_city', 'shibnagar_town', ?, ?,"
            " 'open', ?)",
            (c["connection_id"], c["kind"], c["via"], game_minutes))
    return len(CONNECTIONS)


def intercity_route(data, from_zone, to_zone, mode="motor"):
    """A route between zones of (possibly) different cities.
    Cross-city routes pathfind to the bridge gate in the origin
    city and from the ghat gate in the destination city — the two
    graph endpoints the road connection joins."""
    from . import cities as cities_mod  # late: avoids a cycle
    origin = cities_mod.city_of_zone(data, from_zone)
    dest = cities_mod.city_of_zone(data, to_zone)
    if origin is None or dest is None:
        return None
    if origin == dest:
        graph = roads_mod.build_graph(data.city_spec(origin))
        return roads_mod.pathfind(
            graph, roads_mod.zone_anchor(data.city_spec(origin),
                                         from_zone),
            roads_mod.zone_anchor(data.city_spec(dest), to_zone),
            mode)
    spec_a, spec_b = data.city_spec(origin), data.city_spec(dest)
    gate_a = (520, 465)   # bridge approach end, District 1 frame
    gate_b = (280, 0)     # Shibnagar ghat gate, town frame
    leg_a = roads_mod.pathfind(
        roads_mod.build_graph(spec_a),
        roads_mod.zone_anchor(spec_a, from_zone), gate_a, mode)
    leg_b = roads_mod.pathfind(
        roads_mod.build_graph(spec_b), gate_b,
        roads_mod.zone_anchor(spec_b, to_zone), mode)
    if leg_a is None or leg_b is None:
        return None
    return {"segment_ids": leg_a["segment_ids"] + ["RC-ROAD-1"]
            + leg_b["segment_ids"],
            "distance_m": round(leg_a["distance_m"]
                                + leg_b["distance_m"], 1),
            "time_min": round(leg_a["time_min"] + leg_b["time_min"],
                              2),
            "connection_id": "RC-ROAD-1"}


def commuters(store, data):
    """Live intercity commuters: employed residents whose
    profession's workplace zone is in the other city.
    Returns {(from_city, to_city): count}."""
    from . import cities as cities_mod
    out = {}
    for r in store.rows(
            "SELECT c.character_id, h.district_id AS home_zone,"
            " e.profession_id FROM employments e"
            " JOIN characters c ON c.character_id = e.character_id"
            " JOIN households h ON h.household_id = c.household_id"
            " WHERE e.ended_at_game_minutes IS NULL"
            " AND c.died_at_game_minutes IS NULL"):
        prof = data.professions.get(r["profession_id"])
        if not prof:
            continue
        home_city = cities_mod.city_of_zone(data, r["home_zone"])
        work_city = cities_mod.city_of_zone(
            data, prof["workplace_zone"])
        if home_city and work_city and home_city != work_city:
            key = (home_city, work_city)
            out[key] = out.get(key, 0) + 1
    return out


def monthly_flows(store, data, month_index, game_minutes):
    """Persist the month's trade flows + commuter/migrant counts.
    Returns the flow rows written."""
    from . import cities as cities_mod
    pop = {cid: cities_mod.city_population(store, data, cid)
           for cid in ("rupsha_city", "shibnagar_town")}
    industry_workers = 0
    for r in store.rows("SELECT profession_id, COUNT(*) AS n FROM"
                        " employments WHERE ended_at_game_minutes"
                        " IS NULL GROUP BY profession_id"):
        prof = data.professions.get(r["profession_id"])
        if prof and prof["workplace_zone"] == "d1_industry":
            industry_workers += r["n"]
    farmland = store.row("SELECT COUNT(*) AS n FROM land_parcels"
                         " WHERE city_id = 'shibnagar_town' AND"
                         " zoning_category = 'agricultural'")["n"]
    flows = []
    manufactured = min(
        industry_workers * TRADE_PER_INDUSTRY_WORKER_NCR,
        pop["shibnagar_town"] * TRADE_DEMAND_PER_RESIDENT_NCR)
    if manufactured > 0:
        flows.append(("rupsha_city", "shibnagar_town",
                      "manufactured_goods", manufactured))
    produce = min(
        farmland * TRADE_PER_FARMLAND_PARCEL_NCR
        + pop["shibnagar_town"] * TRADE_PRODUCE_PER_RESIDENT_NCR,
        pop["rupsha_city"] * TRADE_DEMAND_PER_RESIDENT_NCR)
    if produce > 0:
        flows.append(("shibnagar_town", "rupsha_city",
                      "agricultural_produce", produce))
    for frm, to, goods, amount in flows:
        fid = store.next_id("TF", "trade_flows", "flow_id")
        store.insert("trade_flows", flow_id=fid,
                     month_index=month_index, from_city_id=frm,
                     to_city_id=to, goods=goods, amount_ncr=amount,
                     game_minutes=game_minutes)
    comm = commuters(store, data)
    migrants = store.row(
        "SELECT COUNT(*) AS n FROM migration_records WHERE"
        " game_minutes > ?", (game_minutes - 30 * 1440,))["n"]
    for c in CONNECTIONS:
        store.execute(
            "UPDATE regional_connections SET last_month_commuters"
            " = ?, last_month_migrants = ?,"
            " updated_at_game_minutes = ? WHERE connection_id = ?",
            (comm.get(("shibnagar_town", "rupsha_city"), 0)
             + comm.get(("rupsha_city", "shibnagar_town"), 0),
             migrants, game_minutes, c["connection_id"]))
    return flows
