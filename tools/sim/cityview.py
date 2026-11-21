"""Session 03 Unit 12 — City Visualization (data layer).

HONEST SCOPE, stated in the module because it is the unit's main
limitation: the 3D visualization engine is Unreal Engine 5 on the
owner's PC. It cannot be built, rendered or benchmarked in this
VM, and Session 03 does not claim otherwise — acceptance
criterion 13 (3D performance) is DEFERRED to the owner's PC build
(see docs/SESSION-03-REPORT.md).

What this unit delivers is everything the 3D layer will consume,
plus the observation surfaces that work today:

- export_city_state(): the full city state as one JSON document
  (registry, zones, terrain, parcels, buildings with live state
  and occupancy, road graph nodes/edges with condition,
  infrastructure status, analytics) — the contract the UE layer
  reads its world from;
- ascii_map(): a map-mode overview rendered from the real
  coordinates (terrain, roads, building anchors, river), the
  text counterpart of the map/3D mode switch — every glyph is a
  simulated fact, nothing is decorative filler.
"""
import json

from . import analytics as analytics_mod
from . import buildings as buildings_mod
from . import roads as roads_mod
from . import terrain as terrain_mod


def export_city_state(store, data, city_id):
    """The complete city state, read live, as one JSON-ready
    document for the (future, PC-side) 3D layer."""
    spec = data.city_spec(city_id)
    if spec is None:
        return None
    registry = store.row("SELECT * FROM cities WHERE city_id = ?",
                         (city_id,))
    graph = roads_mod.build_graph(spec)
    seg_state = {r["segment_id"]: r for r in store.rows(
        "SELECT * FROM road_segments WHERE city_id = ?", (city_id,))}
    buildings = []
    for b in spec["properties"]:
        state = store.row("SELECT * FROM building_state WHERE"
                          " building_id = ?", (b["id"],))
        buildings.append({
            "building_id": b["id"], "name": b["name"],
            "property_type": b["property_type"],
            "zone_id": b["zone_id"], "tier": b["tier"],
            "units": b.get("units", 1),
            "state": state,
            "occupancy": buildings_mod.occupancy(store, data,
                                                 b["id"]),
        })
    for state in store.rows("SELECT * FROM building_state WHERE"
                            " city_id = ? AND building_id LIKE"
                            " '%_built_%'", (city_id,)):
        buildings.append({
            "building_id": state["building_id"],
            "name": "Constructed building (Unit 11)",
            "property_type": None, "zone_id": None, "tier": None,
            "units": None, "state": state,
            "occupancy": buildings_mod.occupancy(
                store, data, state["building_id"]),
        })
    return {
        "city": registry,
        "zones": store.rows("SELECT * FROM city_zones WHERE city_id"
                            " = ?", (city_id,)),
        "terrain": [dict(r, bbox=json.loads(r["bbox"])) for r in
                    store.rows("SELECT * FROM terrain_regions WHERE"
                               " city_id = ?", (city_id,))],
        "parcels": store.rows("SELECT * FROM land_parcels WHERE"
                              " city_id = ?", (city_id,)),
        "buildings": buildings,
        "roads": {
            "nodes": [{"x": n["x"], "z": n["z"],
                       "junction_ref": n["junction_ref"]}
                      for n in graph.nodes.values()],
            "edges": [{"segment_id": e["segment_id"],
                       "road_class": e["road_class"],
                       "length_m": e["length"],
                       "condition": (seg_state[e["segment_id"]]
                                     ["condition"] if e["segment_id"]
                                     in seg_state else None)}
                      for e in graph.edges],
            "documented_snaps": graph.snaps,
        },
        "infrastructure": store.rows(
            "SELECT * FROM infrastructure_state WHERE city_id = ?",
            (city_id,)),
        "services": store.rows("SELECT * FROM municipal_services"
                               " WHERE city_id = ?", (city_id,)),
        "analytics": analytics_mod.city_analytics(store, data,
                                                  city_id),
    }


def ascii_map(store, data, city_id, width=104, height=46):
    """A map-mode rendering from real coordinates. Terrain fills
    the base ('~' water, '.' land, ',' farmland, '^' hills), roads
    draw as '#', building anchors as 'B', the river gate as 'G'.
    Returns the map as a list of strings (deterministic)."""
    spec = data.city_spec(city_id)
    if spec is None:
        return None
    regions = terrain_mod.regions_for_spec(spec)
    boxes = list(spec["zone_boxes_m"].values())
    x0 = min(b["x0"] for b in boxes)
    x1 = max(b["x1"] for b in boxes)
    z0 = min(b["z0"] for b in boxes)
    z1 = max(b["z1"] for b in boxes)
    if spec["river"]:
        band = spec["river"]["band"]
        x0 = min(x0, band["x0"])
        x1 = max(x1, band["x1"])
        z0 = min(z0, band["z0"])
        z1 = max(z1, band["z1"])
    grid = [[" "] * width for _ in range(height)]

    def cell(x, z):
        cx = min(width - 1, max(0, int((x - x0) / (x1 - x0)
                                       * (width - 1))))
        cy = min(height - 1, max(0, int((z - z0) / (z1 - z0)
                                        * (height - 1))))
        return cx, cy

    base_char = {"river": "~", "lake": "~", "wetland": "~",
                 "farmland": ",", "hills": "^", "floodplain": ".",
                 "plain": ".", "urban": "."}
    for cy in range(height):
        for cx in range(width):
            x = x0 + (cx + 0.5) / width * (x1 - x0)
            z = z0 + (cy + 0.5) / height * (z1 - z0)
            region = terrain_mod.terrain_at(regions, x, z)
            grid[cy][cx] = base_char.get(
                region["terrain_class"], ".") if region else " "
    for s in spec["road_segments"]:
        ax, az = s["from"]
        bx, bz = s["to"]
        steps = max(abs(bx - ax), abs(bz - az))
        steps = int(steps / 8) + 1
        for i in range(steps + 1):
            x = ax + (bx - ax) * i / steps
            z = az + (bz - az) * i / steps
            cx, cy = cell(x, z)
            if grid[cy][cx] != "~":
                grid[cy][cx] = "#"
    plots = {p.get("building_id"): p for p in spec["plots"]}
    for b in spec["properties"]:
        plot = plots.get(b["id"])
        if plot is None:
            continue
        r = plot["plot_rect_m"]
        cx, cy = cell(r["x"] + r["w"] / 2, r["z"] + r["d"] / 2)
        grid[cy][cx] = "B"
    return ["".join(row) for row in grid]
