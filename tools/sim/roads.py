"""Session 03 Unit 06 — Road Network Engine.

A real graph over the blockout's segment geometry — not a list of
roads with claimed connectivity. Graph construction:

- nodes are segment endpoints and named junctions;
- a segment is SPLIT wherever a junction lies on it, another
  segment's endpoint touches it, or another segment crosses it;
- blockout v1 positions are a grid approximation (TECH-
  DISTRICT1-BLOCKOUT: "positions are negotiable"), so a near-miss
  endpoint is MOVED onto its target: within SNAP_LINE_M of a
  segment's line (projected onto it) or SNAP_END_M of another
  segment's endpoint (merged with it) — never when the two
  segments already cross or share a node. Every snap is reported
  by build_graph() so nothing connects silently.

Pathfinding is Dijkstra over travel time with per-mode class
restrictions taken from GDD-07 §3 (motor traffic never enters
lanes or the promenade; rickshaws are barred from arterials;
cycles may use the promenade). Segment condition is sim state
(road_segments table), decayed and repaired by Unit 09.
"""
import heapq
import math

SNAP_LINE_M = 25.0   # endpoint -> projection on a segment's line
SNAP_END_M = 50.0    # endpoint -> another segment's endpoint
_EPS = 0.51  # coordinate equality tolerance (data uses 0.1 steps)

LANES = {"arterial": 4, "collector": 2, "local": 2, "lane": 1,
         "promenade": 0}
SPEED_KMH = {"arterial": 40, "collector": 30, "local": 20,
             "lane": 5, "promenade": 3}
CAPACITY_VPH = {"arterial": 2200, "collector": 1200, "local": 700,
                "lane": 150, "promenade": 1800}

MODES = {
    "motor": {"arterial", "collector", "local"},
    "rickshaw": {"collector", "local", "lane"},
    "cycle": {"collector", "local", "lane", "promenade"},
    "walk": {"arterial", "collector", "local", "lane", "promenade"},
}


def _key(x, z):
    return (round(x, 1), round(z, 1))


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _point_seg(p, a, b):
    """(distance, projected point, t) of point p to segment a-b."""
    ax, az = a
    bx, bz = b
    dx, dz = bx - ax, bz - az
    length_sq = dx * dx + dz * dz
    if length_sq == 0:
        return _dist(p, a), a, 0.0
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - az) * dz)
                     / length_sq))
    proj = (ax + t * dx, az + t * dz)
    return _dist(p, proj), proj, t


def _seg_crossing(a, b, c, d):
    """Proper crossing point of segments a-b and c-d, or None.
    Touching at shared endpoints is handled by node merging, not
    here; this finds interior crossings and T-touches."""
    def orient(p, q, r):
        v = (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0]
                                                             - p[0])
        return v

    def on(p, q, r):  # q on segment p-r (collinear case)
        return min(p[0], r[0]) - _EPS <= q[0] <= max(p[0], r[0]) \
            + _EPS and min(p[1], r[1]) - _EPS <= q[1] \
            <= max(p[1], r[1]) + _EPS

    o1, o2 = orient(a, b, c), orient(a, b, d)
    o3, o4 = orient(c, d, a), orient(c, d, b)
    if ((o1 > 0) != (o2 > 0)) and ((o3 > 0) != (o4 > 0)) \
            and o1 != 0 and o2 != 0 and o3 != 0 and o4 != 0:
        # Interior crossing: solve for the point.
        t = ((c[0] - a[0]) * (d[1] - c[1]) - (c[1] - a[1])
             * (d[0] - c[0])) / ((b[0] - a[0]) * (d[1] - c[1])
                                 - (b[1] - a[1]) * (d[0] - c[0]))
        return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
    if o1 == 0 and on(a, c, b):
        return c
    if o2 == 0 and on(a, d, b):
        return d
    if o3 == 0 and on(c, a, d):
        return a
    if o4 == 0 and on(c, b, d):
        return b
    return None


class Graph:
    def __init__(self):
        self.nodes = {}       # key -> {x, z, junction_ref}
        self.adjacency = {}   # key -> [(key, edge)]
        self.edges = []       # {a, b, segment_id, road_class, length}
        self.snaps = []       # documented snap events

    def add_node(self, x, z, junction_ref=None):
        k = _key(x, z)
        if k not in self.nodes:
            self.nodes[k] = {"x": k[0], "z": k[1],
                             "junction_ref": junction_ref}
            self.adjacency[k] = []
        elif junction_ref and not self.nodes[k]["junction_ref"]:
            self.nodes[k]["junction_ref"] = junction_ref
        return k

    def add_edge(self, ka, kb, segment_id, road_class, length):
        if ka == kb:
            return
        edge = {"a": ka, "b": kb, "segment_id": segment_id,
                "road_class": road_class, "length": length}
        self.edges.append(edge)
        self.adjacency[ka].append((kb, edge))
        self.adjacency[kb].append((ka, edge))


def _snap_endpoints(segs, snaps):
    """Move near-miss endpoints onto their targets (see module
    docstring for the rules). Mutates segs' a/b in place; appends
    one record per snap to `snaps`."""
    def shares_or_crosses(o, s):
        if _key(*o["a"]) in (_key(*s["a"]), _key(*s["b"])) \
                or _key(*o["b"]) in (_key(*s["a"]), _key(*s["b"])):
            return True
        return _seg_crossing(o["a"], o["b"], s["a"], s["b"]) \
            is not None

    for o in segs:
        for end in ("a", "b"):
            p = o[end]
            if any(_key(*p) == _key(*q) for s in segs if s is not o
                   for q in (s["a"], s["b"])):
                continue  # already a shared node
            best = None  # (distance, target_point, onto_id)
            for s in segs:
                if s is o or shares_or_crosses(o, s):
                    continue
                d, proj, t = _point_seg(p, s["a"], s["b"])
                if _EPS < d <= SNAP_LINE_M and 0.0 < t < 1.0:
                    if best is None or d < best[0]:
                        best = (d, proj, s["id"])
                for q in (s["a"], s["b"]):
                    dq = _dist(p, q)
                    if dq <= SNAP_END_M and dq > _EPS:
                        if best is None or dq < best[0]:
                            best = (dq, q, s["id"])
            if best is not None:
                snaps.append({"point": p, "onto": best[2],
                              "distance_m": round(best[0], 1),
                              "moved_to": best[1]})
                o[end] = best[1]


def build_graph(spec):
    """Construct the road graph of one city spec from its segment
    geometry. Deterministic: nodes/edges derive only from data."""
    g = Graph()
    segs = []
    for s in spec["road_segments"]:
        a = (float(s["from"][0]), float(s["from"][1]))
        b = (float(s["to"][0]), float(s["to"][1]))
        segs.append({"id": s["id"], "class": s["class"], "a": a,
                     "b": b})
    _snap_endpoints(segs, g.snaps)
    junctions = [((float(j["at"][0]), float(j["at"][1])), j["id"])
                 for j in spec["junctions"]]
    for (x, z), jid in junctions:
        g.add_node(x, z, junction_ref=jid)
    for s in segs:
        g.add_node(*s["a"])
        g.add_node(*s["b"])

    # Split points per segment: (t, point) along the segment.
    splits = {s["id"]: {0.0: s["a"], 1.0: s["b"]} for s in segs}
    for s in segs:
        for (jx, jz), _jid in junctions:
            d, proj, t = _point_seg((jx, jz), s["a"], s["b"])
            if d <= _EPS and 0.0 < t < 1.0:
                splits[s["id"]][t] = proj
        for o in segs:
            if o["id"] == s["id"]:
                continue
            for p in (o["a"], o["b"]):
                d, proj, t = _point_seg(p, s["a"], s["b"])
                if d <= _EPS and 0.0 < t < 1.0:
                    splits[s["id"]][t] = proj
            cross = _seg_crossing(s["a"], s["b"], o["a"], o["b"])
            if cross is not None:
                d, proj, t = _point_seg(cross, s["a"], s["b"])
                if 0.0 < t < 1.0:
                    splits[s["id"]][t] = proj

    for s in segs:
        points = sorted(splits[s["id"]].items())
        total = _dist(s["a"], s["b"])
        for (t0, p0), (t1, p1) in zip(points, points[1:]):
            ka = g.add_node(*p0)
            kb = g.add_node(*p1)
            g.add_edge(ka, kb, s["id"], s["class"],
                       round(total * (t1 - t0), 2))
    # Prune phantom nodes: junction points no segment passes
    # through are not part of the network.
    for key in [k for k, adj in g.adjacency.items() if not adj]:
        del g.nodes[key]
        del g.adjacency[key]
    return g


def components(graph, mode="walk"):
    """Connected components over the mode's allowed classes."""
    allowed = MODES[mode]
    seen, comps = set(), []
    for start in sorted(graph.nodes):
        if start in seen:
            continue
        stack, comp = [start], set()
        seen.add(start)
        while stack:
            cur = stack.pop()
            comp.add(cur)
            for nb, edge in graph.adjacency[cur]:
                if edge["road_class"] in allowed and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        comps.append(comp)
    return comps


def nearest_node(graph, x, z):
    return min(graph.nodes, key=lambda k: _dist((x, z), k))


def _nearest_mode_node(graph, x, z, allowed):
    """Nearest node incident to at least one edge of an allowed
    class — a traveller snaps to their own network, not to a node
    they cannot legally use (e.g. a cyclist to an arterial-only
    ghat node)."""
    best, best_d = None, float("inf")
    for key in graph.nodes:
        nx, nz = key
        if not any(e["road_class"] in allowed
                   for _, e in graph.adjacency[key]):
            continue
        d = (nx - x) ** 2 + (nz - z) ** 2
        if d < best_d:
            best, best_d = key, d
    return best


def pathfind(graph, from_xy, to_xy, mode="motor"):
    """Shortest-time route between two points (snapped to their
    nearest nodes on the mode's own network). Returns the route or
    None when the mode's network cannot connect them."""
    allowed = MODES[mode]
    start = _nearest_mode_node(graph, from_xy[0], from_xy[1], allowed)
    goal = _nearest_mode_node(graph, to_xy[0], to_xy[1], allowed)
    if start is None or goal is None:
        return None
    if start == goal:
        return {"nodes": [start], "segment_ids": [], "distance_m": 0.0,
                "time_min": 0.0}
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
            if edge["road_class"] not in allowed:
                continue
            w = edge["length"] / (SPEED_KMH[edge["road_class"]]
                                  * 1000 / 60)
            nc = cost + w
            if nc < dist.get(nb, float("inf")):
                dist[nb] = nc
                prev[nb] = (cur, edge)
                heapq.heappush(pq, (nc, nb))
    if goal not in dist:
        return None
    nodes, seg_ids, total_len = [goal], [], 0.0
    cur = goal
    while cur != start:
        cur, edge = prev[cur]
        nodes.append(cur)
        seg_ids.append(edge["segment_id"])
        total_len += edge["length"]
    nodes.reverse()
    seg_ids.reverse()
    return {"nodes": nodes, "segment_ids": seg_ids,
            "distance_m": round(total_len, 1),
            "time_min": round(dist[goal], 2)}


def setup_roads(store, spec, game_minutes):
    """Persist segment state (condition) for one city. Idempotent.
    Lengths come from the routing graph's geometry (including the
    documented endpoint snaps) so the stored network and the routed
    network are the same one; lanes/speeds/capacity are the class
    model of GDD-02 §3 + GDD-07 §3."""
    graph = build_graph(spec)
    lengths = {}
    for e in graph.edges:
        lengths[e["segment_id"]] = lengths.get(e["segment_id"], 0.0) \
            + e["length"]
    n = 0
    for s in spec["road_segments"]:
        if store.row("SELECT 1 FROM road_segments WHERE segment_id"
                     " = ?", (s["id"],)):
            continue
        cls = s["class"]
        store.insert(
            "road_segments", segment_id=s["id"],
            city_id=spec["city_id"], name=s["name"], road_class=cls,
            length_m=round(lengths.get(s["id"], 0.0), 1),
            lanes=LANES[cls], speed_limit_kmh=SPEED_KMH[cls],
            capacity_vph=CAPACITY_VPH[cls], condition=92.0,
            updated_at_game_minutes=game_minutes)
        n += 1
    return n


def zone_anchor(spec, zone_id):
    """A zone's routing anchor: its box centre."""
    box = spec["zone_boxes_m"][zone_id]
    return ((box["x0"] + box["x1"]) / 2, (box["z0"] + box["z1"]) / 2)
