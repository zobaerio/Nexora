"""Session 03 Unit 02 — Geographical & Terrain Engine.

Terrain regions under both cities: class, elevation, water and
buildability, in each city's local metre frame. District 1's
regions are derived from the blockout's own river band plus
GDD-02's geography (the river closing the south edge, the Central
Park pond, the riverfront floodplain, the uptown rise); the
generated town carries its regions in its generated file. Both
flow through this one engine.

The buildability contract is enforced, not advisory:
validate_build() rejects any construction footprint that touches
a non-buildable region (water, wetland) — a building in the river
is a failed validation, never a placed building.
"""
import json

# District 1 regions, most specific first (terrain_at returns the
# first containing region). The river band is the blockout's own
# data; the pond wetland is centred on landmark lm_park_pond
# (60, 255); the floodplain is the riverfront strip GDD-02 §2
# describes; the rise is uptown's elevated ground.
DISTRICT1_REGIONS = [
    {"id": "tr_d1_river", "name": "Rupsha River", "terrain_class":
     "river", "elevation_m": -3,
     "bbox": {"x0": -520, "x1": 520, "z0": 432, "z1": 520},
     "buildable": False, "restriction": "water"},
    {"id": "tr_d1_pond_wetland", "name": "Central Park pond wetland",
     "terrain_class": "wetland", "elevation_m": 3,
     # The pond (landmark at (60, 255)) sits in the unplotted park
     # ground between the park_land and food-carts plots — the
     # bbox covers that gap and touches neither plot.
     "bbox": {"x0": 28, "x1": 67, "z0": 222, "z1": 288},
     "buildable": False, "restriction": "water"},
    {"id": "tr_d1_floodplain", "name": "Riverfront floodplain",
     "terrain_class": "floodplain", "elevation_m": 2,
     "bbox": {"x0": -520, "x1": 520, "z0": 340, "z1": 432},
     "buildable": True, "restriction": "flood_risk"},
    {"id": "tr_d1_hills", "name": "Uptown rise", "terrain_class":
     "hills", "elevation_m": 14,
     "bbox": {"x0": 350, "x1": 520, "z0": 250, "z1": 340},
     "buildable": True, "restriction": "slope"},
    {"id": "tr_d1_plain", "name": "Rupsha plain", "terrain_class":
     "plain", "elevation_m": 5,
     "bbox": {"x0": -520, "x1": 520, "z0": -520, "z1": 340},
     "buildable": True, "restriction": None},
]

TERRAIN_CLASSES = ("plain", "hills", "mountains", "river", "lake",
                   "coastline", "forest", "farmland", "wetland",
                   "floodplain", "urban")


def regions_for_spec(spec):
    """The terrain regions of one city spec (generated file's own
    list, or District 1's derived set)."""
    if spec.get("terrain_regions"):
        return spec["terrain_regions"]
    return DISTRICT1_REGIONS


def _contains(bbox, x, z):
    return bbox["x0"] <= x <= bbox["x1"] and bbox["z0"] <= z <= bbox["z1"]


def _intersects(a, b):
    return not (a["x1"] < b["x0"] or b["x1"] < a["x0"]
                or a["z1"] < b["z0"] or b["z1"] < a["z0"])


def terrain_at(regions, x, z):
    """The most specific region containing a point (list order is
    specificity order), or None outside the modelled extent."""
    for r in regions:
        if _contains(r["bbox"], x, z):
            return r
    return None


def validate_build(regions, rect):
    """May a building footprint (rect {x,z,w,d}) stand here?
    Returns (ok, violations): any intersection with a non-buildable
    region is a violation naming the region and its class."""
    foot = {"x0": rect["x"], "x1": rect["x"] + rect["w"],
            "z0": rect["z"], "z1": rect["z"] + rect["d"]}
    violations = []
    for r in regions:
        if not r["buildable"] and _intersects(foot, r["bbox"]):
            violations.append(
                f"footprint intersects {r['name']} "
                f"({r['terrain_class']}, non-buildable)")
    return (not violations), violations


def restrictions_at(regions, rect):
    """Non-fatal terrain restrictions a footprint carries (flood
    risk, slope) — recorded on the project, priced by the design's
    risk model, never silently ignored."""
    foot = {"x0": rect["x"], "x1": rect["x"] + rect["w"],
            "z0": rect["z"], "z1": rect["z"] + rect["d"]}
    return sorted({r["restriction"] for r in regions
                   if r["buildable"] and r["restriction"]
                   and _intersects(foot, r["bbox"])})


def setup_terrain(store, spec, game_minutes):
    """Persist a city's terrain regions (idempotent)."""
    for r in regions_for_spec(spec):
        store.execute(
            "INSERT OR IGNORE INTO terrain_regions (region_id,"
            " city_id, name, terrain_class, elevation_m, bbox,"
            " buildable, restriction) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (r["id"], spec["city_id"], r["name"], r["terrain_class"],
             r["elevation_m"], json.dumps(r["bbox"]),
             1 if r["buildable"] else 0, r["restriction"]))
    return len(regions_for_spec(spec))
