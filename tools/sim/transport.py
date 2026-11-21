"""Session 07 — Transportation, Mobility & Smart Infrastructure.

The physical movement layer the earlier sessions imply but never
recorded. Sessions 01–06 move citizens *logically*: schedules put
a citizen in a zone, the clinic registers a visit, Session 04's
supply chain moves inventory with a distance-priced shipping
charge. This session records the journeys themselves, on Session
03's real road graphs, and lets the journeys push back: traffic
is the day's actual trips loading the day's actual segments, and
travel times (and tomorrow's route choices) respond to that load.

What is grounded where:

- Networks: Session 03's per-city road graphs (roads.build_graph)
  plus its two persisted regional connections (RC-ROAD-1 bridge,
  RC-FERRY-1 ferry). No new network is drawn. A railway station
  plot and a launch terminal exist as buildings, but no rail
  track/service data exists anywhere in the merged data, so no
  rail operations run — stated plainly, not papered over. The
  ferry runs because Session 03 persisted the connection and
  both ghats exist as buildings.
- Vehicles: classes, road rights, capacities and fuel
  consumption from data/vehicles.json. Buyable classes are
  bought at data/prices.json prices through the ledger; fleet
  classes (bus, truck) are SYS-MARKET / business vehicles, as
  vehicles.json itself frames them. There is no ambulance or
  vessel class in vehicles.json, so emergency and ferry trips
  reference their route, not an invented vehicle row.
- Fares: taxi hire is charged per trip at prices.json
  taxi_fares (base + per-km, surge per its own conditions) to
  SYS-MARKET, the taxi-system aggregate — taxi drivers' income
  stays the settlement's wage (they also pay its cab rental), so
  no fare is counted twice. Bus / rickshaw / ferry travel is
  covered by the monthly transport_public_bus_rickshaw living
  line prices.json already charges; fare 0 at point of use.
  Fuel has NO price in prices.json, so fuel is tracked as a
  quantity (litres/kg from vehicles.json consumption) and never
  charged per trip; owners' running costs stay their monthly
  transport_own_car_fuel_upkeep band.
- Traffic: per (segment, hour) flow is tallied from the day's
  own vehicle trips (passenger-car equivalents in the config);
  the congestion factor is the config's labelled SIM MODEL
  function of flow against roads.py's class capacities. Routing
  uses yesterday's peak factors (drivers plan around the worst
  hour they know); today's travel times use today's factors.
  Road condition (Session 03 state, repaired by Session 05
  policy) slows segments measurably; a segment under the
  critical condition or explicitly closed is impassable.
- Freight: Session 04's supply orders and the intercity trade
  flows gain a physical record — vehicle, route, departure,
  congested arrival, delay — while the money stays exactly
  where Session 04 put it (its shipping charge). The inventory
  transfer itself remains Session 04's pass-end settlement;
  the shipment record is the journey's audit trail.

Every pass no-ops in worlds where the layer was never set up
(hand-built test worlds), the bootstrap discipline of Sessions
03–06. All randomness is keyed rng streams, so determinism and
restart identity hold with the layer live.
"""
import heapq
import json
import math

from . import cities as cities_mod
from . import roads as roads_mod

# Purpose labels for a trip, from the destination block's
# scheduler activity (the GDD-06 vocabulary).
PURPOSE_BY_ACTIVITY = {
    "work": "work", "study": "education", "home": "home",
    "sleep": "home", "leisure": "leisure", "errand": "shopping",
    "break": "break",
}

# Session 03's regional gates (regional.py): the bridge approach
# end in District 1's frame and the ghat gate in Shibnagar's.
GATES = {"rupsha_city": (520, 465), "shibnagar_town": (280, 0)}
FERRY_ROUTE_ID = "RC-FERRY-1"
ROAD_CONNECTION_ID = "RC-ROAD-1"


def cfg(data):
    return data.transport_config


def is_setup(store):
    w = store.world()
    return bool(w and w.get("transport_setup")) \
        and store.row("SELECT 1 FROM transit_routes LIMIT 1") \
        is not None


# ---------------------------------------------------------------------
# Setup: transit routes, fleets, business trucks, taxi cabs.
# ---------------------------------------------------------------------

def _new_vehicle(store, data, vehicle_type, game_minutes, **kw):
    tcfg = cfg(data)["tanks"]
    vid = store.next_id("VH", "vehicles", "vehicle_id")
    store.insert(
        "vehicles", vehicle_id=vid, vehicle_type=vehicle_type,
        fuel_litres=tcfg.get(vehicle_type, 0),
        fuel_capacity_litres=tcfg.get(vehicle_type, 0),
        condition=cfg(data)["maintenance"]["initial_condition"],
        acquired_at_game_minutes=game_minutes, **kw)
    return vid


def _ensure_taxi_cabs(store, data, game_minutes):
    """Every active taxi driver operates a rented cab (the
    settlement already charges them its rental): a SYS-MARKET
    vehicle with the driver as operator. Cabs of drivers who
    left the profession are returned. Returns cabs created."""
    drivers = {r["character_id"] for r in store.rows(
        "SELECT character_id FROM employments WHERE profession_id"
        " = 'taxi_driver' AND ended_at_game_minutes IS NULL")}
    have = {}
    for v in store.rows("SELECT * FROM vehicles WHERE"
                        " vehicle_type = 'taxi' AND status = 'active'"):
        if v["operator_character_id"]:
            have[v["operator_character_id"]] = v
    created = 0
    for cid in sorted(drivers):
        if cid in have:
            continue
        home = store.row(
            "SELECT h.district_id AS zone FROM characters c"
            " JOIN households h ON h.household_id = c.household_id"
            " WHERE c.character_id = ?", (cid,))
        zone = home["zone"] if home else "d1_industry"
        _new_vehicle(
            store, data, "taxi", game_minutes,
            owner_character_id="SYS-MARKET", operator_character_id=cid,
            city_id=cities_mod.city_of_zone(data, zone),
            home_zone=zone, current_zone=zone, acquisition="rental")
        created += 1
    for cid, v in have.items():
        if cid not in drivers:
            store.execute("UPDATE vehicles SET status = 'returned'"
                          " WHERE vehicle_id = ?", (v["vehicle_id"],))
    return created


def setup_transport(store, data, game_minutes=480):
    """Seed the Session 07 layer. Idempotent; hand-built worlds
    that never generate a population have no transport layer and
    every Session 07 pass no-ops for them."""
    if is_setup(store):
        return {"already_setup": True}
    c = cfg(data)
    routes = 0
    for spec in c["transit_routes"]:
        vtype = data.vehicle_types.get(spec["vehicle_type"]) \
            if spec["vehicle_type"] else None
        runs_per_hour = max(1, 60 // spec["headway_min"])
        capacity = (vtype["capacity"]["passengers"] * runs_per_hour
                    if vtype else 40 * runs_per_hour)
        store.execute(
            "INSERT OR IGNORE INTO transit_routes (route_id,"
            " city_id, kind, name, stops_json, headway_min,"
            " capacity_per_hour, status) VALUES (?, ?, ?, ?, ?,"
            " ?, ?, 'active')",
            (spec["route_id"], spec["city_id"], spec["kind"],
             spec["name"], json.dumps(spec["stops"]),
             spec["headway_min"], capacity))
        routes += 1
    # Bus fleets at their real terminal buildings' zones.
    buses = 0
    for spec in c["transit_routes"]:
        if spec["kind"] != "bus":
            continue
        terminal_zone = spec["stops"][0]
        for _ in range(spec["fleet_size"]):
            _new_vehicle(
                store, data, "bus", game_minutes,
                owner_character_id="SYS-MARKET",
                city_id=spec["city_id"], home_zone=terminal_zone,
                current_zone=terminal_zone, acquisition="fleet")
            buses += 1
    # Trucks: one per producing/distributing business (its freight
    # vehicle), plus the SYS-MARKET carrier fleet per city.
    trucks = 0
    if store.row("SELECT 1 FROM businesses LIMIT 1"):
        for b in store.rows(
                "SELECT * FROM businesses WHERE closed_at_game_minutes"
                " IS NULL AND category IN ('manufacturing',"
                " 'distribution', 'agriculture', 'fishing',"
                " 'food_processing') ORDER BY business_id"):
            zone = None
            if b["property_id"]:
                prop = store.row("SELECT district_id FROM properties"
                                 " WHERE property_id = ?",
                                 (b["property_id"],))
                zone = prop["district_id"] if prop else None
            _new_vehicle(
                store, data, "truck", game_minutes,
                owner_business_id=b["business_id"],
                city_id=cities_mod.city_of_zone(data, zone)
                if zone else None,
                home_zone=zone, current_zone=zone,
                acquisition="business")
            trucks += 1
    carriers = 0
    for spec in data.city_specs():
        depot_zone = "d1_industry" if spec["city_id"] == "rupsha_city" \
            else "c2_transport"
        for _ in range(c["freight"]["carrier_trucks_per_city"]):
            _new_vehicle(
                store, data, "truck", game_minutes,
                owner_character_id="SYS-MARKET",
                city_id=spec["city_id"], home_zone=depot_zone,
                current_zone=depot_zone, acquisition="fleet")
            carriers += 1
    cabs = _ensure_taxi_cabs(store, data, game_minutes)
    store.set_world(transport_setup=1)
    store.commit()
    return {"routes": routes, "buses": buses, "trucks": trucks,
            "carrier_trucks": carriers, "taxi_cabs": cabs}


# ---------------------------------------------------------------------
# Routing over Session 03's graphs, weighted by load + condition.
# ---------------------------------------------------------------------

class Network:
    """One day's routing view: both cities' graphs, road state,
    and yesterday's peak congestion factors."""

    def __init__(self, store, data, day_index):
        self.store = store
        self.data = data
        self.graphs = {spec["city_id"]: roads_mod.build_graph(spec)
                       for spec in data.city_specs()}
        self.road_state = {r["segment_id"]: r for r in store.rows(
            "SELECT segment_id, road_class, condition, closed"
            " FROM road_segments")}
        self.peak_factors = {}
        if day_index > 0:
            for r in store.rows(
                    "SELECT segment_id, MAX(congestion_factor) AS f"
                    " FROM road_loads WHERE day_index = ?"
                    " GROUP BY segment_id", (day_index - 1,)):
                self.peak_factors[r["segment_id"]] = r["f"]
        self._route_cache = {}

    def condition_factor(self, segment_id):
        st = self.road_state.get(segment_id)
        if st is None:
            return 1.0
        slow = cfg(self.data)["road_condition"][
            "slowdown_at_zero_condition"]
        return 1.0 + (100.0 - st["condition"]) / 100.0 * slow

    def impassable(self, segment_id):
        st = self.road_state.get(segment_id)
        if st is None:
            return False
        crit = cfg(self.data)["road_condition"]["critical_condition"]
        return bool(st["closed"]) or st["condition"] < crit

    def route(self, city_id, from_xy, to_xy, allowed_classes):
        """Weighted Dijkstra. Edge weight = free-flow minutes x
        yesterday's peak congestion factor x condition factor;
        impassable segments are excluded. Returns {nodes,
        segment_ids, distance_m, free_min, plan_min} or None."""
        key = (city_id, from_xy, to_xy,
               frozenset(allowed_classes))
        if key in self._route_cache:
            return self._route_cache[key]
        graph = self.graphs[city_id]
        start = roads_mod._nearest_mode_node(
            graph, from_xy[0], from_xy[1], allowed_classes)
        goal = roads_mod._nearest_mode_node(
            graph, to_xy[0], to_xy[1], allowed_classes)
        result = None
        if start is not None and goal is not None:
            if start == goal:
                result = {"nodes": [start], "segment_ids": [],
                          "distance_m": 0.0, "free_min": 0.0,
                          "plan_min": 0.0, "edges": []}
            else:
                dist = {start: 0.0}
                prev = {}
                pq = [(0.0, start)]
                while pq:
                    cost, cur = heapq.heappop(pq)
                    if cur == goal:
                        break
                    if cost > dist.get(cur, float("inf")):
                        continue
                    for nb, edge in graph.adjacency[cur]:
                        if edge["road_class"] not in allowed_classes:
                            continue
                        sid = edge["segment_id"]
                        if self.impassable(sid):
                            continue
                        free = edge["length"] / (
                            roads_mod.SPEED_KMH[edge["road_class"]]
                            * 1000 / 60)
                        w = free * self.peak_factors.get(sid, 1.0) \
                            * self.condition_factor(sid)
                        nc = cost + w
                        if nc < dist.get(nb, float("inf")):
                            dist[nb] = nc
                            prev[nb] = (cur, edge, free)
                            heapq.heappush(pq, (nc, nb))
                if goal in dist:
                    nodes, seg_ids, edges = [goal], [], []
                    total_len = free_total = 0.0
                    cur = goal
                    while cur != start:
                        cur, edge, free = prev[cur]
                        nodes.append(cur)
                        seg_ids.append(edge["segment_id"])
                        edges.append((edge, free))
                        total_len += edge["length"]
                        free_total += free
                    nodes.reverse()
                    seg_ids.reverse()
                    edges.reverse()
                    result = {"nodes": nodes, "segment_ids": seg_ids,
                              "distance_m": round(total_len, 1),
                              "free_min": round(free_total, 2),
                              "plan_min": round(dist[goal], 2),
                              "edges": edges}
        self._route_cache[key] = result
        return result

    def zone_route(self, city_id, from_zone, to_zone, allowed):
        spec = self.data.city_spec(city_id)
        return self.route(city_id,
                          roads_mod.zone_anchor(spec, from_zone),
                          roads_mod.zone_anchor(spec, to_zone),
                          allowed)

    def intercity(self, from_zone, to_zone, allowed):
        """Cross-city route over the RC-ROAD-1 bridge connection:
        origin city to its gate, destination gate to destination
        zone, plus the config's crossing leg."""
        origin = cities_mod.city_of_zone(self.data, from_zone)
        dest = cities_mod.city_of_zone(self.data, to_zone)
        if origin is None or dest is None:
            return None
        if origin == dest:
            return self.zone_route(origin, from_zone, to_zone, allowed)
        spec_a = self.data.city_spec(origin)
        spec_b = self.data.city_spec(dest)
        leg_a = self.route(origin,
                           roads_mod.zone_anchor(spec_a, from_zone),
                           GATES[origin], allowed)
        leg_b = self.route(dest, GATES[dest],
                           roads_mod.zone_anchor(spec_b, to_zone),
                           allowed)
        if leg_a is None or leg_b is None:
            return None
        cross = cfg(self.data)["intercity"]
        return {
            "segment_ids": leg_a["segment_ids"] + [ROAD_CONNECTION_ID]
            + leg_b["segment_ids"],
            "edges": leg_a["edges"] + leg_b["edges"],
            "distance_m": round(leg_a["distance_m"] + leg_b["distance_m"]
                                + cross["crossing_distance_m"], 1),
            "free_min": round(leg_a["free_min"] + leg_b["free_min"]
                              + cross["crossing_min"], 2),
            "plan_min": round(leg_a["plan_min"] + leg_b["plan_min"]
                              + cross["crossing_min"], 2),
            "connection_id": ROAD_CONNECTION_ID}


def travel_time(route, factors, net, hour):
    """A route's travel minutes under a (segment, hour) factor map
    (today's measured loads), with condition factors applied."""
    total = 0.0
    for edge, free in route["edges"]:
        sid = edge["segment_id"]
        total += free * factors.get((sid, hour), 1.0) \
            * net.condition_factor(sid)
    if route.get("connection_id") == ROAD_CONNECTION_ID:
        total += cfg(net.data)["intercity"]["crossing_min"]
    return round(total, 2)


# ---------------------------------------------------------------------
# Transit: routes as cycles of graph legs between real zone stops.
# ---------------------------------------------------------------------

def build_transit_paths(store, data, net):
    """For each bus route: the segment path of every leg between
    consecutive stops (the last leg closes the loop), routed on
    the bus class's road rights from vehicles.json."""
    out = {}
    bus_classes = set(data.vehicle_types["bus"]["road_classes_allowed"])
    for spec in cfg(data)["transit_routes"]:
        if spec["kind"] != "bus":
            continue
        stops = spec["stops"]
        legs = []  # legs[i]: stop i -> stop i+1 (wrapping)
        ok = True
        for i, zone in enumerate(stops):
            nxt = stops[(i + 1) % len(stops)]
            r = net.zone_route(spec["city_id"], zone, nxt, bus_classes)
            if r is None:
                ok = False
                break
            legs.append(r)
        if ok:
            out[spec["route_id"]] = {"spec": spec, "legs": legs}
    return out


def transit_subpath(path, from_zone, to_zone):
    """The shorter way around the route's cycle between two
    stops: {segment_ids, edges, distance_m, free_min}."""
    stops = path["spec"]["stops"]
    legs = path["legs"]
    i, j = stops.index(from_zone), stops.index(to_zone)
    if i == j:
        return {"segment_ids": [], "edges": [], "distance_m": 0.0,
                "free_min": 0.0}

    def collect(a, b):
        seg_ids, edges, dist_m, free = [], [], 0.0, 0.0
        k = a
        while k != b:
            leg = legs[k]
            seg_ids += leg["segment_ids"]
            edges += leg["edges"]
            dist_m += leg["distance_m"]
            free += leg["free_min"]
            k = (k + 1) % len(stops)
        return {"segment_ids": seg_ids, "edges": edges,
                "distance_m": round(dist_m, 1),
                "free_min": round(free, 2)}

    fwd = collect(i, j)
    bwd = collect(j, i)
    return fwd if fwd["distance_m"] <= bwd["distance_m"] else bwd


def bus_route_for(store, data, paths, origin_zone, dest_zone):
    """The bus route serving an OD pair, if any (both zones are
    stops of one route)."""
    for route_id, path in paths.items():
        stops = path["spec"]["stops"]
        if origin_zone in stops and dest_zone in stops:
            return route_id, path
    return None, None


# ---------------------------------------------------------------------
# Mode choice + fares.
# ---------------------------------------------------------------------

TREASURY_BY_CITY = {"rupsha_city": "SYS-TREASURY-RUPSHA",
                    "shibnagar_town": "SYS-TREASURY-SHIBNAGAR"}
REPRESENTATIVE_ZONE = {"rupsha_city": "d1_midtown",
                       "shibnagar_town": "c2_residential"}
PRICE_TO_TYPE = {"bicycle": "bicycle", "rickshaw_own": "rickshaw",
                 "motorbike": "motorbike", "car_small": "car_small",
                 "car_premium": "car_premium"}
MOTOR_CLASSES = {"arterial", "collector", "local"}


def taxi_fare(data, distance_m, preset, depart_minute):
    """The prices.json taxi fare for a trip: base + per-km,
    surged by the file's own multiplier when its conditions hold
    (rain presets, night hours). Integer NCr, as the file rules."""
    fares = data.prices["taxi_fares"]
    amount = fares["base_ncr"] + fares["per_km_ncr"] * distance_m / 1000
    hour = (depart_minute % 1440) // 60
    surged = ("rain" in fares["surge_conditions"]
              and preset in ("rain", "storm")) or \
        ("night" in fares["surge_conditions"]
         and (hour >= 22 or hour < 5))
    if surged:
        amount *= fares["surge_multiplier"]
    return int(round(amount))


def _home_zones(store):
    return {r["character_id"]: r["district_id"] for r in store.rows(
        "SELECT c.character_id, h.district_id FROM characters c"
        " JOIN households h ON h.household_id = c.household_id"
        " WHERE c.is_system = 0")}


def _citizen_vehicles(store):
    """Purchased vehicles by owner, and rented cabs by operator."""
    owned, cabs = {}, {}
    for v in store.rows("SELECT * FROM vehicles WHERE status ="
                        " 'active' ORDER BY vehicle_id"):
        if v["operator_character_id"]:
            cabs[v["operator_character_id"]] = v
        elif v["owner_character_id"] and \
                v["owner_character_id"] not in (
                    "SYS-MARKET", "SYS-CITY", "SYS-BANK",
                    "SYS-EMPLOYERS"):
            owned.setdefault(v["owner_character_id"], v)
    return owned, cabs


def _taxi_cities(store, data, home_zone):
    """Cities with an active taxi service: at least one employed
    taxi driver resident there."""
    out = set()
    for r in store.rows(
            "SELECT character_id FROM employments WHERE"
            " profession_id = 'taxi_driver' AND"
            " ended_at_game_minutes IS NULL"):
        zone = home_zone.get(r["character_id"])
        city = cities_mod.city_of_zone(data, zone) if zone else None
        if city:
            out.add(city)
    return out


def _resolve_intent(store, data, net, paths, intent, owned, cabs,
                    taxi_cities):
    """Choose a mode and route for one journey. Returns a trip
    dict (without travel time, which needs the day's loads) or
    None when no network journey exists (intra-zone or
    off-world legs are not network trips)."""
    cid = intent["character_id"]
    oz, dz = intent["origin_zone"], intent["destination_zone"]
    if oz == dz:
        return None
    ocity = cities_mod.city_of_zone(data, oz)
    dcity = cities_mod.city_of_zone(data, dz)
    if ocity is None or dcity is None:
        return None
    base = dict(intent)
    base["segment_ids"] = []
    base["edges"] = []
    base["distance_m"] = 0.0
    base["free_min"] = 0.0
    base["vehicle_id"] = None
    base["route_id"] = None
    base["fare_ncr"] = 0
    base["fare_basis"] = "none"
    base["speed_mode"] = "motor"  # how travel time is computed
    vehicle = owned.get(cid)
    cab = cabs.get(cid)
    mc = cfg(data)["mode_choice"]

    def own_trip(v, mode):
        classes = set(data.vehicle_types[v["vehicle_type"]]
                      ["road_classes_allowed"])
        if ocity == dcity:
            r = net.zone_route(ocity, oz, dz, classes)
        else:
            r = net.intercity(oz, dz, classes)
        if r is None:
            return None
        t = dict(base, mode=mode, vehicle_id=v["vehicle_id"],
                 segment_ids=r["segment_ids"], edges=r["edges"],
                 distance_m=r["distance_m"], free_min=r["free_min"],
                 connection_id=r.get("connection_id"))
        if v["vehicle_type"] == "bicycle":
            t["speed_mode"] = "cycle"
        elif v["vehicle_type"] == "rickshaw":
            t["speed_mode"] = "rickshaw"
        return t

    if vehicle is not None:
        t = own_trip(vehicle, "own_vehicle")
        if t is not None:
            return t
    if cab is not None:
        t = own_trip(cab, "taxi_cab")
        if t is not None:
            return t

    if ocity != dcity:
        # Intercity: ferry when the leg is ghat-to-ghat, else the
        # intercity bus over the bridge connection, else on foot.
        ferry = next(r for r in cfg(data)["transit_routes"]
                     if r["route_id"] == FERRY_ROUTE_ID)
        if {oz, dz} == set(ferry["stops"]):
            hour = (intent["depart_minute"] % 1440) // 60
            if ferry["operating_start_hour"] <= hour \
                    < ferry["operating_end_hour"]:
                return dict(
                    base, mode="ferry", route_id=FERRY_ROUTE_ID,
                    segment_ids=[FERRY_ROUTE_ID],
                    distance_m=ferry["crossing_distance_m"],
                    free_min=ferry["crossing_min"],
                    speed_mode="ferry",
                    fare_basis="monthly_transport_line")
        bus_classes = set(data.vehicle_types["bus"]
                          ["road_classes_allowed"])
        r = net.intercity(oz, dz, bus_classes) or \
            net.intercity(oz, dz, MOTOR_CLASSES)
        if r is not None:
            return dict(base, mode="intercity_bus",
                        segment_ids=r["segment_ids"],
                        edges=r["edges"], distance_m=r["distance_m"],
                        free_min=r["free_min"],
                        connection_id=r.get("connection_id"),
                        fare_basis="monthly_transport_line")
        r = net.intercity(oz, dz, set(roads_mod.MODES["walk"]))
        if r is not None:
            return dict(base, mode="walk", segment_ids=r["segment_ids"],
                        edges=r["edges"], distance_m=r["distance_m"],
                        free_min=r["free_min"],
                        connection_id=r.get("connection_id"),
                        speed_mode="walk")
        return None

    # Same city.
    walk_r = net.zone_route(ocity, oz, dz, set(roads_mod.MODES["walk"]))
    if walk_r is not None and walk_r["distance_m"] \
            <= mc["walk_max_distance_m"]:
        return dict(base, mode="walk", segment_ids=walk_r["segment_ids"],
                    edges=walk_r["edges"],
                    distance_m=walk_r["distance_m"],
                    free_min=walk_r["free_min"], speed_mode="walk")
    route_id, path = bus_route_for(store, data, paths, oz, dz)
    depart_hour = (intent["depart_minute"] % 1440) // 60
    if route_id is not None:
        spec = path["spec"]
        if spec["operating_start_hour"] <= depart_hour \
                < spec["operating_end_hour"]:
            sub = transit_subpath(path, oz, dz)
            return dict(base, mode="bus", route_id=route_id,
                        segment_ids=sub["segment_ids"],
                        edges=sub["edges"], distance_m=sub["distance_m"],
                        free_min=sub["free_min"],
                        fare_basis="monthly_transport_line")
    rick_classes = set(data.vehicle_types["rickshaw"]
                       ["road_classes_allowed"])
    rick_r = net.zone_route(ocity, oz, dz, rick_classes)
    if rick_r is not None and rick_r["distance_m"] \
            <= mc["rickshaw_max_distance_m"]:
        return dict(base, mode="rickshaw",
                    segment_ids=rick_r["segment_ids"],
                    edges=rick_r["edges"],
                    distance_m=rick_r["distance_m"],
                    free_min=rick_r["free_min"], speed_mode="rickshaw",
                    fare_basis="monthly_transport_line")
    if ocity in taxi_cities:
        taxi_classes = set(data.vehicle_types["taxi"]
                           ["road_classes_allowed"])
        taxi_r = net.zone_route(ocity, oz, dz, taxi_classes)
        if taxi_r is not None:
            fare = taxi_fare(data, taxi_r["distance_m"],
                             intent["preset"], intent["depart_minute"])
            if store.balance(cid) >= fare:
                return dict(base, mode="taxi",
                            segment_ids=taxi_r["segment_ids"],
                            edges=taxi_r["edges"],
                            distance_m=taxi_r["distance_m"],
                            free_min=taxi_r["free_min"], fare_ncr=fare,
                            fare_basis="prices_taxi_fares")
    if walk_r is not None:
        return dict(base, mode="walk", segment_ids=walk_r["segment_ids"],
                    edges=walk_r["edges"],
                    distance_m=walk_r["distance_m"],
                    free_min=walk_r["free_min"], speed_mode="walk")
    return None


def _load_ratio(trip, factors, net, hour):
    """Congested/free ratio of a trip's route under today's
    loads (1.0 when the route has no timed edges)."""
    if not trip["edges"] or trip["free_min"] <= 0:
        return 1.0
    return travel_time(trip, factors, net, hour) / trip["free_min"]


def _travel_minutes(trip, factors, net, hour):
    sm = trip["speed_mode"]
    if sm == "ferry":
        return trip["free_min"]
    if sm == "walk":
        return round(trip["distance_m"] / 1000
                     / cfg(net.data)["mode_choice"]["walk_speed_kmh"]
                     * 60, 2)
    if sm in ("cycle", "rickshaw"):
        cruise = cfg(net.data)["mode_choice"][
            "cycle_cruise_kmh" if sm == "cycle"
            else "rickshaw_cruise_kmh"]
        base = trip["distance_m"] / 1000 / cruise * 60
        return round(base * _load_ratio(trip, factors, net, hour), 2)
    return travel_time(trip, factors, net, hour)


def _fuel_for(data, trip):
    """Litres (or kg) a trip consumes, from vehicles.json's
    consumption for the mode's vehicle class. 0 for human-powered
    and per-passenger bus travel (bus fuel is accounted per run
    in the monthly statistics)."""
    type_by_mode = {"own_vehicle": None, "taxi": "taxi",
                    "taxi_cab": "taxi", "intercity_bus": None,
                    "ambulance": "taxi", "rickshaw": None}
    if trip["mode"] == "own_vehicle" and trip.get("vehicle_type"):
        vtype = trip["vehicle_type"]
    else:
        vtype = type_by_mode.get(trip["mode"])
    if vtype is None:
        return 0.0
    per100 = data.vehicle_types[vtype]["fuel_consumption_per_100km"]
    if not per100:
        return 0.0
    return round(trip["distance_m"] / 1000 * per100 / 100, 3)


# ---------------------------------------------------------------------
# The daily pass: trips from the day's real schedules + clinic
# journeys + emergency referrals, traffic from the trips.
# ---------------------------------------------------------------------

def daily_pass(store, data, rng, day_index, day_end, preset):
    if not is_setup(store) or not cities_mod.is_setup(store):
        return {}
    if store.row("SELECT 1 FROM trips WHERE day_index = ? LIMIT 1",
                 (day_index,)):
        return {"already_recorded": True}  # restart safety
    c = cfg(data)
    day_start = day_index * 1440
    net = Network(store, data, day_index)
    paths = build_transit_paths(store, data, net)
    home_zone = _home_zones(store)
    owned, cabs = _citizen_vehicles(store)
    taxi_cities = _taxi_cities(store, data, home_zone)
    intents = []

    # 1. Schedule trips: consecutive blocks in different zones.
    for row in store.rows(
            "SELECT character_id, blocks_json FROM"
            " instantiated_schedules WHERE day_index = ?"
            " ORDER BY character_id", (day_index,)):
        blocks = json.loads(row["blocks_json"])
        for prev, nxt in zip(blocks, blocks[1:]):
            oz, dz = prev.get("zone"), nxt.get("zone")
            if not oz or not dz or oz == dz:
                continue
            intents.append({
                "character_id": row["character_id"],
                "purpose": PURPOSE_BY_ACTIVITY.get(
                    nxt["activity"], nxt["activity"]),
                "origin_zone": oz, "destination_zone": dz,
                "depart_minute": day_start + nxt["start"],
                "preset": preset})

    # 2. Clinic journeys + emergency referrals (Session 06 rows
    #    created by today's health pass).
    buildings = data.all_buildings()
    fac_zone = {}
    if store.row("SELECT 1 FROM healthcare_facilities LIMIT 1"):
        for f in store.rows("SELECT * FROM healthcare_facilities"):
            b = buildings.get(f["building_id"])
            if b:
                fac_zone[f["facility_id"]] = b["zone_id"]
    depart_clinic = day_start + c["emergency"]["clinic_depart_hour"] * 60
    for v in store.rows(
            "SELECT * FROM patient_visits WHERE registered_day = ?"
            " ORDER BY visit_id", (day_index,)):
        hz = home_zone.get(v["character_id"])
        fz = fac_zone.get(v["facility_id"])
        if hz and fz and hz != fz:
            intents.append({
                "character_id": v["character_id"],
                "purpose": "healthcare", "origin_zone": hz,
                "destination_zone": fz, "depart_minute": depart_clinic,
                "preset": preset,
                "details": {"visit_id": v["visit_id"]}})
    emergencies = []
    for a in store.rows(
            "SELECT * FROM hospital_admissions WHERE admitted_day = ?"
            " AND referred_off_district = 1 ORDER BY admission_id",
            (day_index,)):
        fz = fac_zone.get(a["facility_id"])
        if not fz:
            continue
        city = cities_mod.city_of_zone(data, fz)
        if city is None:
            continue
        spec = data.city_spec(city)
        r = net.route(city, roads_mod.zone_anchor(spec, fz),
                      GATES[city], MOTOR_CLASSES)
        if r is None:
            continue
        emergencies.append({
            "character_id": a["character_id"], "purpose": "emergency",
            "origin_zone": fz, "destination_zone": "off_district",
            "depart_minute": depart_clinic, "preset": preset,
            "mode": "ambulance", "segment_ids": r["segment_ids"],
            "edges": r["edges"], "distance_m": r["distance_m"],
            "free_min": r["free_min"], "vehicle_id": None,
            "route_id": None, "fare_ncr": 0, "fare_basis": "none",
            "speed_mode": "motor",
            "details": {"admission_id": a["admission_id"],
                        "kind": "referral_off_district"}})

    # 3. Resolve modes/routes.
    trips = []
    for intent in intents:
        t = _resolve_intent(store, data, net, paths, intent, owned,
                            cabs, taxi_cities)
        if t is None:
            continue
        if t["vehicle_id"]:
            v = store.row("SELECT vehicle_type FROM vehicles WHERE"
                          " vehicle_id = ?", (t["vehicle_id"],))
            t["vehicle_type"] = v["vehicle_type"] if v else None
        t.setdefault("details", intent.get("details", {}))
        trips.append(t)
    trips.extend(emergencies)
    trips.sort(key=lambda t: (t["depart_minute"], t["character_id"]
                              or ""))

    # 4. Bus capacity: an hour's boardings beyond the route's
    #    hourly capacity spill to rickshaw/walk, in character
    #    order (deterministic).
    by_run = {}
    for t in trips:
        if t["mode"] == "bus":
            key = (t["route_id"], (t["depart_minute"] % 1440) // 60)
            by_run.setdefault(key, []).append(t)
    route_capacity = {r["route_id"]: r["capacity_per_hour"]
                      for r in store.rows("SELECT * FROM transit_routes")}
    for (route_id, hour), riders in sorted(by_run.items()):
        cap = route_capacity.get(route_id, 0)
        for t in riders[cap:]:
            # Re-route on the fallback mode's own road rights —
            # a rickshaw may not use the bus path's arterials.
            city = cities_mod.city_of_zone(data, t["origin_zone"])
            rick_r = net.zone_route(
                city, t["origin_zone"], t["destination_zone"],
                set(data.vehicle_types["rickshaw"]
                    ["road_classes_allowed"]))
            if rick_r is not None:
                t.update(mode="rickshaw", route_id=None,
                         speed_mode="rickshaw",
                         segment_ids=rick_r["segment_ids"],
                         edges=rick_r["edges"],
                         distance_m=rick_r["distance_m"],
                         free_min=rick_r["free_min"])
            else:
                walk_r = net.zone_route(
                    city, t["origin_zone"], t["destination_zone"],
                    set(roads_mod.MODES["walk"]))
                if walk_r is None:
                    continue
                t.update(mode="walk", route_id=None,
                         speed_mode="walk",
                         segment_ids=walk_r["segment_ids"],
                         edges=walk_r["edges"],
                         distance_m=walk_r["distance_m"],
                         free_min=walk_r["free_min"])
            t["fare_basis"] = "monthly_transport_line"
            t["details"] = {**t.get("details", {}),
                            "spilled_from": route_id}

    # 5. Refuel vehicles below reserve before they travel.
    reserve = c["fuel_reserve_fraction"]
    for v in store.rows("SELECT * FROM vehicles WHERE status ="
                        " 'active' AND fuel_capacity_litres > 0"):
        if v["fuel_litres"] < reserve * v["fuel_capacity_litres"]:
            added = v["fuel_capacity_litres"] - v["fuel_litres"]
            store.execute("UPDATE vehicles SET fuel_litres = ?"
                          " WHERE vehicle_id = ?",
                          (v["fuel_capacity_litres"], v["vehicle_id"]))
            eid = store.next_id("VE", "vehicle_events", "event_id")
            store.insert("vehicle_events", event_id=eid,
                         vehicle_id=v["vehicle_id"], kind="refuel",
                         game_minutes=day_start,
                         details=json.dumps(
                             {"litres_added": round(added, 2),
                              "zone": v["current_zone"],
                              "note": "no fuel price exists in"
                                      " prices.json; quantity only"},
                             sort_keys=True))

    # 6. Tally today's loads from today's vehicle movement, then
    #    derive today's congestion factors.
    pce = c["congestion"]["pce"]
    flows = {}
    for t in trips:
        hour = (t["depart_minute"] % 1440) // 60
        w = pce.get(t["mode"], 0.0)
        if w:
            for sid in set(t["segment_ids"]):
                if sid in net.road_state:
                    flows[(sid, hour)] = flows.get((sid, hour), 0.0) + w
    for (route_id, hour), riders in sorted(by_run.items()):
        if not riders or riders[0]["mode"] != "bus":
            continue
        path = paths.get(route_id)
        if not path:
            continue
        for leg in path["legs"]:
            for sid in set(leg["segment_ids"]):
                if sid in net.road_state:
                    flows[(sid, hour)] = flows.get((sid, hour), 0.0) \
                        + pce["bus_run"]
    k = c["congestion"]["k"]
    max_factor = c["congestion"]["max_factor"]
    factors = {}
    for (sid, hour), flow in sorted(flows.items()):
        st = net.road_state[sid]
        capacity = roads_mod.CAPACITY_VPH[st["road_class"]]
        factor = min(max_factor, 1.0 + k * flow / capacity)
        factors[(sid, hour)] = factor
        store.execute(
            "INSERT OR REPLACE INTO road_loads (day_index,"
            " segment_id, hour, vehicle_count, capacity_vph,"
            " congestion_factor) VALUES (?, ?, ?, ?, ?, ?)",
            (day_index, sid, hour, flow, capacity, round(factor, 4)))

    # 7. Finalise: travel times, fares through the ledger, fuel,
    #    vehicle state, trip rows, transit runs.
    stats = {"trips": 0, "fares_ncr": 0, "by_mode": {}}
    vehicle_updates = {}
    for t in trips:
        hour = (t["depart_minute"] % 1440) // 60
        travel = _travel_minutes(t, factors, net, hour)
        if t["mode"] == "ambulance":
            travel = round(travel * c["emergency"]["priority_factor"], 2)
        arrive = int(round(t["depart_minute"] + travel))
        fuel = _fuel_for(data, t)
        trip_id = store.next_id("TR", "trips", "trip_id")
        if t["fare_ncr"] > 0:
            if store.balance(t["character_id"]) >= t["fare_ncr"]:
                store.transfer(
                    t["character_id"], "SYS-MARKET", t["fare_ncr"],
                    "taxi_fare", t["depart_minute"],
                    note=f"taxi {t['origin_zone']} ->"
                         f" {t['destination_zone']}",
                    transfer_key=f"taxi:{trip_id}",
                    event_ref=f"day:{day_index}")
                stats["fares_ncr"] += t["fare_ncr"]
            else:
                t["fare_ncr"] = 0
                t["fare_basis"] = "fare_unpaid_insufficient_funds"
        emissions = 0.0
        if fuel:
            vtype = t.get("vehicle_type") or "taxi"
            fuel_type = data.vehicle_types[vtype]["fuel_type"]
            emissions = round(fuel * c["emissions_kg_per_unit"].get(
                fuel_type, 0.0), 3)
        details = dict(t.get("details", {}))
        if emissions:
            details["emissions_kg"] = emissions
        store.insert(
            "trips", trip_id=trip_id, character_id=t["character_id"],
            day_index=day_index, purpose=t["purpose"],
            origin_zone=t["origin_zone"],
            destination_zone=t["destination_zone"], mode=t["mode"],
            vehicle_id=t["vehicle_id"], route_id=t["route_id"],
            segment_ids=json.dumps(t["segment_ids"]),
            distance_m=t["distance_m"],
            depart_minute=t["depart_minute"],
            free_flow_min=t["free_min"], travel_min=travel,
            arrive_minute=arrive, fare_ncr=t["fare_ncr"],
            fare_basis=t["fare_basis"], fuel_litres=fuel,
            status="completed", details=json.dumps(details,
                                                   sort_keys=True))
        stats["trips"] += 1
        stats["by_mode"][t["mode"]] = stats["by_mode"].get(
            t["mode"], 0) + 1
        if t["vehicle_id"]:
            u = vehicle_updates.setdefault(
                t["vehicle_id"], {"fuel": 0.0, "km": 0.0, "zone": None})
            u["fuel"] += fuel
            u["km"] += t["distance_m"] / 1000
            u["zone"] = t["destination_zone"]
    for vid, u in vehicle_updates.items():
        store.execute(
            "UPDATE vehicles SET fuel_litres = MAX(0, fuel_litres"
            " - ?), odometer_km = odometer_km + ?, current_zone = ?"
            " WHERE vehicle_id = ?",
            (round(u["fuel"], 3), round(u["km"], 3), u["zone"], vid))
    for (route_id, hour), riders in sorted(by_run.items()):
        boardings = sum(1 for t in riders if t["mode"] == "bus")
        if not boardings:
            continue
        cap = route_capacity.get(route_id, 0)
        existing = store.row("SELECT run_id FROM transit_runs WHERE"
                             " route_id = ? AND day_index = ? AND"
                             " hour = ?", (route_id, day_index, hour))
        if existing:
            store.execute("UPDATE transit_runs SET boardings = ?"
                          " WHERE run_id = ?",
                          (boardings, existing["run_id"]))
        else:
            rid = store.next_id("TR", "transit_runs", "run_id")
            store.insert("transit_runs", run_id=rid, route_id=route_id,
                         day_index=day_index, hour=hour,
                         boardings=boardings, capacity=cap)

    # 8. Shipments whose arrival time has passed are delivered.
    store.execute("UPDATE freight_shipments SET status = 'delivered'"
                  " WHERE status = 'in_transit' AND arrives_at <= ?",
                  (day_end,))
    stats["max_congestion_factor"] = round(
        max(factors.values()), 3) if factors else 1.0
    return stats


# ---------------------------------------------------------------------
# Freight: Session 04's orders and trade flows made physical.
# ---------------------------------------------------------------------

TRUCK_CLASSES = {"arterial", "collector"}


def _business_zone(store, business_id):
    b = store.row("SELECT property_id FROM businesses WHERE"
                  " business_id = ?", (business_id,))
    if b and b["property_id"]:
        p = store.row("SELECT district_id FROM properties WHERE"
                      " property_id = ?", (b["property_id"],))
        if p:
            return p["district_id"]
    return None


def _truck_for(store, business_id, city_id):
    if business_id:
        v = store.row("SELECT vehicle_id FROM vehicles WHERE"
                      " owner_business_id = ? AND status = 'active'"
                      " ORDER BY vehicle_id", (business_id,))
        if v:
            return v["vehicle_id"]
    v = store.row("SELECT vehicle_id FROM vehicles WHERE"
                  " owner_character_id = 'SYS-MARKET' AND"
                  " vehicle_type = 'truck' AND city_id = ? AND"
                  " status = 'active' ORDER BY vehicle_id",
                  (city_id,))
    return v["vehicle_id"] if v else None


def _latest_factors(store, net):
    row = store.row("SELECT MAX(day_index) AS d FROM road_loads")
    factors = {}
    if row and row["d"] is not None:
        for r in store.rows("SELECT segment_id, hour,"
                            " congestion_factor FROM road_loads"
                            " WHERE day_index = ?", (row["d"],)):
            factors[(r["segment_id"], r["hour"])] = \
                r["congestion_factor"]
    return factors


def _make_shipment(store, data, net, factors, month_index,
                   game_minutes, kind, from_zone, to_zone,
                   from_business_id, to_business_id, good_id, units,
                   freight_ncr, vehicle_id, details):
    if not from_zone or not to_zone or from_zone == to_zone:
        return None
    ocity = cities_mod.city_of_zone(data, from_zone)
    dcity = cities_mod.city_of_zone(data, to_zone)
    if ocity is None or dcity is None:
        return None
    if ocity == dcity:
        route = net.zone_route(ocity, from_zone, to_zone,
                               TRUCK_CLASSES) or \
            net.zone_route(ocity, from_zone, to_zone, MOTOR_CLASSES)
    else:
        route = net.intercity(from_zone, to_zone, TRUCK_CLASSES) or \
            net.intercity(from_zone, to_zone, MOTOR_CLASSES)
    if route is None:
        return None
    travel = travel_time(route, factors, net, 10)
    sid = store.next_id("FS", "freight_shipments", "shipment_id")
    store.insert(
        "freight_shipments", shipment_id=sid, month_index=month_index,
        kind=kind, from_business_id=from_business_id,
        to_business_id=to_business_id, from_city_id=ocity,
        to_city_id=dcity, good_id=good_id, units=units,
        vehicle_id=vehicle_id,
        segment_ids=json.dumps(route["segment_ids"]),
        distance_km=round(route["distance_m"] / 1000, 2),
        freight_ncr=freight_ncr, departed_at=game_minutes,
        free_flow_min=route["free_min"], travel_min=travel,
        arrives_at=game_minutes + int(math.ceil(travel)),
        delay_min=round(travel - route["free_min"], 2),
        status="in_transit", details=json.dumps(details,
                                                sort_keys=True))
    return sid


def record_shipments(store, data, month_index, game_minutes, orders):
    """One physical shipment per Session 04 supply order. The
    order's money (goods + shipping charge) already moved in
    market.supply_chain_pass; this records the journey the goods
    actually make, on the seller's truck or a carrier."""
    if not is_setup(store):
        return []
    net = Network(store, data, store.world()["day_index"])
    factors = _latest_factors(store, net)
    made = []
    for o in orders:
        sz = _business_zone(store, o["seller"])
        bz = _business_zone(store, o["buyer"])
        city = cities_mod.city_of_zone(data, sz) if sz else None
        sid = _make_shipment(
            store, data, net, factors, month_index, game_minutes,
            "supply_order", sz, bz, o["seller"], o["buyer"],
            o["good_id"], o["units"], o["shipping_ncr"],
            _truck_for(store, o["seller"], city),
            {"amount_ncr": o["amount_ncr"],
             "month_index": month_index})
        if sid:
            made.append(sid)
    return made


def record_trade_shipments(store, data, month_index, game_minutes,
                           flows):
    """One shipment per Session 03/04 intercity trade flow,
    market zone to market zone over the bridge connection. The
    flow's tariff is Session 04 trade's own ledger business;
    freight_ncr is 0 here by design (no second charge)."""
    if not is_setup(store):
        return []
    net = Network(store, data, store.world()["day_index"])
    factors = _latest_factors(store, net)
    zone_of_city = {"rupsha_city": "d1_market",
                    "shibnagar_town": "c2_market"}
    made = []
    for frm, to, goods, amount in flows:
        sid = _make_shipment(
            store, data, net, factors, month_index, game_minutes,
            "trade_flow", zone_of_city[frm], zone_of_city[to],
            None, None, goods, 0, 0,
            _truck_for(store, None, frm),
            {"amount_ncr": amount,
             "note": "tariff settled by Session 04 trade"})
        if sid:
            made.append(sid)
    return made


# ---------------------------------------------------------------------
# The monthly pass: cabs, purchases, maintenance, subsidy,
# migration journeys, statistics.
# ---------------------------------------------------------------------

def _purchase_sweep(store, data, rng, month_index, game_minutes):
    c = cfg(data)["vehicle_purchase"]
    prices = {v["id"]: v["price_ncr"] for v in data.prices["vehicles"]
              if v["id"] in PRICE_TO_TYPE}
    ladder = sorted(prices.items(), key=lambda kv: -kv[1])
    home_zone = _home_zones(store)
    bought = []
    for char in store.rows(
            "SELECT c.* FROM characters c WHERE c.is_system = 0"
            " AND c.died_at_game_minutes IS NULL ORDER BY"
            " c.character_id"):
        cid = char["character_id"]
        from . import identity as identity_mod
        if identity_mod.age_years(char["born_at_game_minutes"],
                                  game_minutes) < 18:
            continue
        emp = store.row("SELECT profession_id FROM employments"
                        " WHERE character_id = ? AND"
                        " ended_at_game_minutes IS NULL", (cid,))
        if emp is None or emp["profession_id"] == "taxi_driver":
            continue  # taxi drivers rent by the settlement's design
        if store.row("SELECT 1 FROM vehicles WHERE"
                     " owner_character_id = ? AND status = 'active'",
                     (cid,)):
            continue
        balance = store.balance(cid)
        choice = None
        for pid, price in ladder:
            if balance >= price * c["balance_multiple"]:
                choice = (pid, price)
                break
        if choice is None:
            continue
        if rng.stream("transport", "buy", month_index, cid).random() \
                >= c["monthly_chance"]:
            continue
        pid, price = choice
        zone = home_zone.get(cid)
        vid = store.next_id("VH", "vehicles", "vehicle_id")
        store.transfer(cid, "SYS-MARKET", price, "vehicle_purchase",
                       game_minutes, note=f"{pid} purchase",
                       transfer_key=f"vehbuy:{cid}:{month_index}",
                       event_ref=f"month:{month_index}")
        tcfg = cfg(data)["tanks"]
        vtype = PRICE_TO_TYPE[pid]
        store.execute(
            "INSERT INTO vehicles (vehicle_id, vehicle_type,"
            " owner_character_id, operator_character_id, city_id,"
            " home_zone, current_zone, fuel_litres,"
            " fuel_capacity_litres, odometer_km, condition, status,"
            " acquisition, acquired_at_game_minutes) VALUES (?, ?,"
            " ?, NULL, ?, ?, ?, ?, ?, 0, ?, 'active', 'purchase', ?)",
            (vid, vtype, cid,
             cities_mod.city_of_zone(data, zone) if zone else None,
             zone, zone, tcfg.get(vtype, 0), tcfg.get(vtype, 0),
             cfg(data)["maintenance"]["initial_condition"],
             game_minutes))
        bought.append(vid)
    return bought


def _maintenance_pass(store, data, month_index, game_minutes):
    c = cfg(data)["maintenance"]
    first_day = (month_index - 1) * 30
    dist = {}
    for r in store.rows(
            "SELECT vehicle_id, SUM(distance_m) AS m FROM trips"
            " WHERE vehicle_id IS NOT NULL AND day_index >= ?"
            " AND day_index < ? GROUP BY vehicle_id",
            (first_day, first_day + 30)):
        dist[r["vehicle_id"]] = r["m"] / 1000
    for r in store.rows(
            "SELECT vehicle_id, SUM(distance_km) AS km FROM"
            " freight_shipments WHERE vehicle_id IS NOT NULL AND"
            " month_index = ? GROUP BY vehicle_id", (month_index,)):
        dist[r["vehicle_id"]] = dist.get(r["vehicle_id"], 0.0) \
            + r["km"]
    serviced = 0
    for v in store.rows("SELECT * FROM vehicles WHERE status ="
                        " 'active' ORDER BY vehicle_id"):
        km = dist.get(v["vehicle_id"], 0.0)
        if km <= 0:
            continue
        wear = km / 500 * c["wear_points_per_500km"]
        condition = max(30.0, v["condition"] - wear)
        if condition < c["service_threshold"]:
            eid = store.next_id("VE", "vehicle_events", "event_id")
            store.insert("vehicle_events", event_id=eid,
                         vehicle_id=v["vehicle_id"],
                         kind="maintenance", game_minutes=game_minutes,
                         details=json.dumps(
                             {"condition_before": round(condition, 1),
                              "km_this_month": round(km, 1),
                              "note": "no per-event price exists in"
                                      " prices.json"}, sort_keys=True))
            condition = c["restored_condition"]
            serviced += 1
        store.execute("UPDATE vehicles SET condition = ? WHERE"
                      " vehicle_id = ?",
                      (round(condition, 2), v["vehicle_id"]))
    return serviced


def _transit_subsidy(store, data, month_index, game_minutes):
    """The municipal treasuries pay the transit operator per
    recorded boarding (config SIM MODEL rate, capped), only in
    government worlds and only what the treasury holds."""
    from . import government as gov_mod
    if not gov_mod.is_setup(store):
        return {}
    c = cfg(data)["subsidy"]
    first_day = (month_index - 1) * 30
    boardings = {}
    for r in store.rows(
            "SELECT route_id, COUNT(*) AS n FROM trips WHERE"
            " mode IN ('bus', 'ferry') AND day_index >= ? AND"
            " day_index < ? GROUP BY route_id",
            (first_day, first_day + 30)):
        route = store.row("SELECT city_id FROM transit_routes WHERE"
                          " route_id = ?", (r["route_id"],))
        city = route["city_id"] if route else "rupsha_city"
        boardings[city] = boardings.get(city, 0) + r["n"]
    paid = {}
    for city, n in sorted(boardings.items()):
        account = TREASURY_BY_CITY.get(city)
        if not account or not store.row(
                "SELECT 1 FROM characters WHERE character_id = ?",
                (account,)):
            continue
        amount = min(c["monthly_cap_ncr_per_city"],
                     n * c["per_boarding_ncr"],
                     store.balance(account))
        if amount > 0:
            store.transfer(account, "SYS-MARKET", amount,
                           "transit_subsidy", game_minutes,
                           note=f"{n} boardings, {city}",
                           transfer_key=f"transit-subsidy:{city}:"
                                        f"{month_index}",
                           event_ref=f"month:{month_index}")
            paid[city] = amount
    return paid


def _migration_trips(store, data, month_index, game_minutes):
    """A migrating household makes one recorded intercity journey
    (head of household, intercity bus) in its migration month."""
    first = (month_index - 1) * 30 * 1440
    made = 0
    for m in store.rows(
            "SELECT * FROM migration_records WHERE game_minutes > ?"
            " AND game_minutes <= ? ORDER BY migration_id",
            (first, game_minutes)):
        head = store.row(
            "SELECT character_id FROM household_members WHERE"
            " household_id = ? AND role = 'head' AND"
            " left_at_game_minutes IS NULL", (m["household_id"],))
        if head is None:
            continue
        oz = REPRESENTATIVE_ZONE[m["from_city_id"]]
        dz = REPRESENTATIVE_ZONE[m["to_city_id"]]
        if store.row("SELECT 1 FROM trips WHERE character_id = ?"
                     " AND purpose = 'migration' AND depart_minute"
                     " = ?", (head["character_id"], m["game_minutes"])):
            continue
        net = Network(store, data, max(0, m["game_minutes"] // 1440))
        r = net.intercity(oz, dz, MOTOR_CLASSES)
        if r is None:
            continue
        tid = store.next_id("TR", "trips", "trip_id")
        store.insert(
            "trips", trip_id=tid, character_id=head["character_id"],
            day_index=m["game_minutes"] // 1440, purpose="migration",
            origin_zone=oz, destination_zone=dz, mode="intercity_bus",
            vehicle_id=None, route_id=None,
            segment_ids=json.dumps(r["segment_ids"]),
            distance_m=r["distance_m"], depart_minute=m["game_minutes"],
            free_flow_min=r["free_min"], travel_min=r["free_min"],
            arrive_minute=m["game_minutes"] + int(r["free_min"]),
            fare_ncr=0, fare_basis="monthly_transport_line",
            fuel_litres=0, status="completed",
            details=json.dumps({"migration_id": m["migration_id"],
                                "household_id": m["household_id"]},
                               sort_keys=True))
        made += 1
    return made


def _month_statistics(store, data, month_index, game_minutes):
    """Monthly transport statistics per city + national, computed
    only from the layer's own records (Session 08 consumes the
    environmental block)."""
    first_day = (month_index - 1) * 30
    last_day = first_day + 30
    scopes = {}
    for spec in data.city_specs():
        scopes[spec["city_id"]] = set(spec["zones"])
    scopes["national"] = None
    out = {}
    for scope, zones in scopes.items():
        trips = [t for t in store.rows(
            "SELECT * FROM trips WHERE day_index >= ? AND"
            " day_index < ?", (first_day, last_day))
            if zones is None or t["origin_zone"] in zones]
        by_mode = {}
        fuel = 0.0
        emissions = 0.0
        for t in trips:
            by_mode[t["mode"]] = by_mode.get(t["mode"], 0) + 1
            fuel += t["fuel_litres"]
            emissions += json.loads(t["details"]).get(
                "emissions_kg", 0.0)
        shipments = [s for s in store.rows(
            "SELECT * FROM freight_shipments WHERE month_index = ?",
            (month_index,))
            if zones is None or s["from_city_id"] in (
                [scope] if scope != "national" else
                ["rupsha_city", "shibnagar_town"])]
        stats = {
            "trips": len(trips),
            "trips_by_mode": by_mode,
            "distance_km": round(sum(t["distance_m"] for t in trips)
                                 / 1000, 1),
            "avg_travel_min": round(
                sum(t["travel_min"] for t in trips) / len(trips), 2)
            if trips else 0.0,
            "boardings": by_mode.get("bus", 0) + by_mode.get("ferry", 0),
            "fares_ncr": sum(t["fare_ncr"] for t in trips),
            "fuel_litres": round(fuel, 1),
            "emissions_kg": round(emissions, 1),
            "shipments": len(shipments),
            "shipments_delivered": sum(
                1 for s in shipments if s["status"] == "delivered"),
            "avg_shipment_delay_min": round(
                sum(s["delay_min"] for s in shipments)
                / len(shipments), 2) if shipments else 0.0,
            "max_congestion_factor": store.row(
                "SELECT MAX(congestion_factor) AS f FROM road_loads"
                " WHERE day_index >= ? AND day_index < ?",
                (first_day, last_day))["f"] or 1.0,
        }
        sid = store.next_id("TS", "transport_statistics", "snapshot_id")
        store.execute(
            "INSERT OR REPLACE INTO transport_statistics"
            " (snapshot_id, scope, month_index, game_minutes,"
            " statistics) VALUES (?, ?, ?, ?, ?)",
            (sid, scope, month_index, game_minutes,
             json.dumps(stats, sort_keys=True)))
        out[scope] = stats
    return out


def monthly_pass(store, data, rng, month_index, game_minutes):
    if not is_setup(store):
        return {}
    cabs = _ensure_taxi_cabs(store, data, game_minutes)
    bought = _purchase_sweep(store, data, rng, month_index,
                             game_minutes)
    serviced = _maintenance_pass(store, data, month_index,
                                 game_minutes)
    subsidy = _transit_subsidy(store, data, month_index, game_minutes)
    migrations = _migration_trips(store, data, month_index,
                                  game_minutes)
    stats = _month_statistics(store, data, month_index, game_minutes)
    return {"taxi_cabs_created": cabs, "vehicles_bought": len(bought),
            "vehicles_serviced": serviced, "subsidy_paid": subsidy,
            "migration_trips": migrations, "statistics": stats}


def transport_summary(store):
    """The engine summary's transport block — persisted rows
    only, so restart/determinism comparisons stay honest."""
    if not is_setup(store):
        return {}
    by_mode = {r["mode"]: r["n"] for r in store.rows(
        "SELECT mode, COUNT(*) AS n FROM trips GROUP BY mode")}
    return {
        "vehicles_active": store.row(
            "SELECT COUNT(*) AS n FROM vehicles WHERE status ="
            " 'active'")["n"],
        "trips_total": store.row("SELECT COUNT(*) AS n FROM trips")["n"],
        "trips_by_mode": by_mode,
        "boardings_total": by_mode.get("bus", 0) + by_mode.get("ferry", 0),
        "fares_total_ncr": store.row(
            "SELECT COALESCE(SUM(fare_ncr),0) AS s FROM trips")["s"],
        "shipments_total": store.row(
            "SELECT COUNT(*) AS n FROM freight_shipments")["n"],
        "shipments_delivered": store.row(
            "SELECT COUNT(*) AS n FROM freight_shipments WHERE"
            " status = 'delivered'")["n"],
        "max_congestion_factor": store.row(
            "SELECT MAX(congestion_factor) AS f FROM road_loads")["f"]
        or 1.0,
    }
