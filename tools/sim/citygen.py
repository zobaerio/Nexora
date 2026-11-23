"""Session 03 Unit 01 — City Generation Engine (town spec generator).

Rupsha City (District 1) is authored design data (GDD-02 + the
Unit C/Unit R data files). A civilization of one city cannot
exercise multi-city systems, so the second city is GENERATED:
this module procedurally builds a smaller neighbour town —
Shibnagar Town, across the Rupsha river — through the same spec
shape the authored district uses (zones, zone boxes, properties,
plots, road segments, junctions, terrain regions), so every
Session 03 system consumes both cities through one code path.

The output is deterministic (a pure function of the prices data
and the layout tables below — no RNG state, no clock), and the
generated file is labelled GENERATED wherever it is stored:
`data/city2-shibnagar.json` is machine output, not authored
design. A test re-runs this generator and asserts the committed
file is byte-identical to a fresh generation.

Rents and buy prices come from prices.json's rent tiers (the
canonical table) — the generator invents no prices of its own.
"""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_HERE, "..", "..", "data")

CITY_ID = "shibnagar_town"

# Zone boxes in the town's local metre frame. Origin at the ferry
# ghat landing; +x east, +z south. The river band closes the north
# edge (z -80..0), mirroring District 1's south-edge river.
ZONE_BOXES = {
    "c2_transport":   {"x0": 40, "x1": 320, "z0": 0, "z1": 60},
    "c2_riverfront":  {"x0": 340, "x1": 520, "z0": 0, "z1": 60},
    "c2_residential": {"x0": 40, "x1": 320, "z0": 80, "z1": 320},
    "c2_market":      {"x0": 340, "x1": 520, "z0": 80, "z1": 240},
    "c2_civic":       {"x0": 340, "x1": 520, "z0": 260, "z1": 360},
    "c2_agriculture": {"x0": 40, "x1": 520, "z0": 380, "z1": 480},
}

# (id, name, property_type, zone, tier, units, civic_owned, footprint)
_BUILDINGS = [
    ("b_c2_transport_ghat", "Shibnagar Ferry Ghat", "plot",
     "c2_transport", 1, 1, True, (60, 40)),
    ("b_c2_transport_bus_stand", "Shibnagar Bus Stand", "plot",
     "c2_transport", 1, 1, True, (50, 40)),
    ("b_c2_riverfront_fish_stalls", "Shibnagar Fish Stalls", "shop",
     "c2_riverfront", 1, 6, False, (36, 20)),
    ("b_c2_riverfront_tea_stall", "Riverside Tea Stall", "shop",
     "c2_riverfront", 1, 1, False, (12, 10)),
    ("b_c2_res_apts_a", "Shibnagar Apartments A", "apartment",
     "c2_residential", 2, 12, False, (44, 32)),
    ("b_c2_res_apts_b", "Shibnagar Apartments B", "apartment",
     "c2_residential", 1, 10, False, (40, 30)),
    ("b_c2_res_apts_c", "Shibnagar Apartments C", "apartment",
     "c2_residential", 2, 8, False, (40, 30)),
    ("b_c2_res_houses_a", "Shibnagar Houses A", "house",
     "c2_residential", 2, 5, False, (30, 24)),
    ("b_c2_res_houses_b", "Shibnagar Houses B", "house",
     "c2_residential", 3, 4, False, (30, 24)),
    ("b_c2_market_shops", "Shibnagar Bazar Shops", "shop",
     "c2_market", 2, 10, False, (44, 26)),
    ("b_c2_market_tea_stall", "Bazar Tea Stall", "shop",
     "c2_market", 1, 1, False, (12, 10)),
    ("b_c2_market_godown", "Shibnagar Godown", "factory",
     "c2_market", 2, 2, False, (40, 28)),
    ("b_c2_civic_school", "Shibnagar Primary School", "office",
     "c2_civic", 2, 1, True, (36, 26)),
    ("b_c2_civic_clinic", "Shibnagar Clinic", "office",
     "c2_civic", 2, 1, True, (30, 22)),
    ("b_c2_civic_office", "Shibnagar Town Office", "office",
     "c2_civic", 2, 1, True, (30, 22)),
    ("b_c2_agri_farmland_a", "Farmland A (paddy)", "plot",
     "c2_agriculture", 1, 1, False, (120, 70)),
    ("b_c2_agri_farmland_b", "Farmland B (vegetables)", "plot",
     "c2_agriculture", 1, 1, False, (120, 70)),
    ("b_c2_agri_warehouse", "Produce Warehouse", "factory",
     "c2_agriculture", 1, 1, False, (36, 24)),
]

# Shop/factory rents and prices by tier — patterned on the District
# 1 data's own conventions (tier-1 stalls rent-only, civic offices
# unpriced), stated here as the generator's layout table.
_COMMERCIAL = {  # tier -> (rent_per_unit, buy_per_unit)
    1: (1200, None), 2: (5000, 600000), 3: (9000, 1100000),
}
_FACTORY = {1: (6000, None), 2: (12000, None), 3: (20000, 2600000)}

# Vacant, developable plots (no building): (id, zone, footprint).
_VACANT_PLOTS = [
    ("plot_c2_res_vacant_1", "c2_residential", (40, 30)),
    ("plot_c2_res_vacant_2", "c2_residential", (36, 28)),
    ("plot_c2_market_vacant_1", "c2_market", (36, 24)),
    ("plot_c2_agri_vacant_1", "c2_agriculture", (60, 40)),
]

_ROADS = [
    # id, name, class, width, from, to
    ("seg_c2_main_st", "Shibnagar Main Street", "collector", 10,
     (280, 0), (280, 480)),
    ("seg_c2_ghat_rd", "Ghat Road", "local", 8, (40, 60), (520, 60)),
    ("seg_c2_mid_st", "Mid Town Street", "local", 8,
     (40, 250), (520, 250)),
    ("seg_c2_south_st", "South Street", "local", 8,
     (40, 370), (520, 370)),
    ("seg_c2_west_st", "West Street", "local", 8, (40, 60), (40, 370)),
    ("seg_c2_east_st", "East Street", "local", 8,
     (520, 60), (520, 370)),
    ("seg_c2_farm_rd", "Farm Road", "lane", 4, (40, 430), (520, 430)),
]

_JUNCTIONS = [
    ("j_c2_ghat", (280, 0), False), ("j_c2_main_ghat_rd", (280, 60),
     False),
    ("j_c2_main_mid", (280, 250), False),
    ("j_c2_main_south", (280, 370), False),
    ("j_c2_west_ghat", (40, 60), False), ("j_c2_east_ghat", (520, 60),
     False),
    ("j_c2_west_mid", (40, 250), False), ("j_c2_east_mid", (520, 250),
     False),
    ("j_c2_west_south", (40, 370), False),
    ("j_c2_east_south", (520, 370), False),
]

_TERRAIN = [
    ("tr_c2_river", "Rupsha River (north bank)", "river", -3,
     {"x0": -40, "x1": 560, "z0": -80, "z1": 0}, False, "water"),
    ("tr_c2_floodplain", "Shibnagar floodplain strip", "floodplain", 1,
     {"x0": -40, "x1": 560, "z0": 0, "z1": 60}, True, "flood_risk"),
    ("tr_c2_wetland", "Shibnagar beel (wetland)", "wetland", 0,
     {"x0": 430, "x1": 560, "z0": 390, "z1": 500}, False, "water"),
    ("tr_c2_farmland", "Shibnagar farmland", "farmland", 2,
     {"x0": -40, "x1": 560, "z0": 370, "z1": 500}, True,
     "agricultural_land"),
    ("tr_c2_plain", "Shibnagar plain", "plain", 4,
     {"x0": -40, "x1": 560, "z0": 60, "z1": 370}, True, None),
]


# (landmark id, name, building id) — Unit CZ, Queue 15 (GDD-04 §3.4).
# The town's landmarks: the civic/transport nodes a player can be
# directed to and recognise. Only properties that qualify: the two
# transport nodes (the ferry ghat is the town's river crossing, the
# bus stand its road terminal — the District 1 analogues are the
# launch terminal and the station) and the three civic institutions
# (school, clinic, town office — unique, named, public). The two tea
# stalls do NOT qualify: in District 1 a tea stall is a service
# anchor (GDD-06 §3), not a landmark. The fish stalls, bazar shops,
# godown, warehouse, farmland and housing do not qualify either: a
# shop row, generic retail, industrial and residential stock are not
# landmarks. Coordinates are derived, never invented: each
# landmark's point is its building's plot anchor (see
# generate_town_spec), so the point always falls inside the
# building's own zone box.
_LANDMARKS = [
    ("c2_lm_ferry_ghat", "Shibnagar Ferry Ghat",
     "b_c2_transport_ghat"),
    ("c2_lm_bus_stand", "Shibnagar Bus Stand",
     "b_c2_transport_bus_stand"),
    ("c2_lm_primary_school", "Shibnagar Primary School",
     "b_c2_civic_school"),
    ("c2_lm_clinic", "Shibnagar Clinic", "b_c2_civic_clinic"),
    ("c2_lm_town_office", "Shibnagar Town Office",
     "b_c2_civic_office"),
]


def _pack_plots(zone_id, items):
    """Deterministic row packing inside the zone box: cursor walks
    east, wraps south. items: [(key, (w, d))]. Returns {key: rect}."""
    box = ZONE_BOXES[zone_id]
    margin, gap = 8, 8
    x, z, row_h = box["x0"] + margin, box["z0"] + margin, 0
    out = {}
    for key, (w, d) in items:
        if x + w > box["x1"] - margin:
            x = box["x0"] + margin
            z += row_h + gap
            row_h = 0
        out[key] = {"x": float(x), "z": float(z), "w": w, "d": d}
        x += w + gap
        row_h = max(row_h, d)
    return out


def generate_town_spec(prices):
    """Build the Shibnagar Town spec. `prices` is prices.json's
    parsed content (rent tiers are the canonical price source)."""
    rent_tiers = {t["tier"]: t for t in prices["rent_monthly_by_tier"]}

    properties = []
    for bid, name, ptype, zone, tier, units, civic, _fp in _BUILDINGS:
        if ptype in ("apartment", "house"):
            rent = rent_tiers[tier]["rent_ncr"]
            buy = rent_tiers[tier]["buy_price_guide_ncr"]
            status = "owned"
        elif ptype == "shop":
            rent, buy = _COMMERCIAL[tier]
            status = "owned"
        elif ptype == "factory":
            rent, buy = _FACTORY[tier]
            status = "owned"
        else:  # plot / civic office: unpriced in the District 1 data too
            rent, buy, status = None, None, "owned"
        properties.append({
            "id": bid, "name": name, "property_type": ptype,
            "zone_id": zone, "tier": tier, "units": units,
            "civic_owned": civic, "interior": False, "status": status,
            "rent_monthly_ncr_per_unit": rent,
            "buy_price_ncr_per_unit": buy,
            "for_rent_units": 0, "for_sale_units": 0,
            "notes": "GENERATED building (citygen.py) — not authored "
                     "design data.",
        })

    plots = []
    by_zone = {}
    for bid, _n, _t, zone, _ti, _u, _c, fp in _BUILDINGS:
        by_zone.setdefault(zone, []).append((bid, fp))
    for pid, zone, fp in _VACANT_PLOTS:
        by_zone.setdefault(zone, []).append((pid, fp))
    for zone, items in by_zone.items():
        rects = _pack_plots(zone, items)
        for key, rect in rects.items():
            is_building = key.startswith("b_c2_")
            plots.append({
                "id": key if not is_building else f"plot_{key[2:]}",
                "building_id": key if is_building else None,
                "zone_id": zone, "plot_rect_m": rect,
                "anchor": {"x": rect["x"] + rect["w"] / 2,
                           "z": rect["z"] + rect["d"],
                           "facing": "south"},
                "notes": "GENERATED plot (citygen.py).",
            })
    plots.sort(key=lambda p: p["id"])

    # Landmarks (Unit CZ, Queue 15): one entry per _LANDMARKS row,
    # pointed at the building's own plot anchor — the plot packing
    # above puts every anchor inside the building's zone box, so the
    # landmark's zone is the building's zone by construction.
    by_building = {p["building_id"]: p for p in plots
                   if p["building_id"]}
    properties_by_id = {p["id"]: p for p in properties}
    landmarks = []
    for lm_id, name, bid in _LANDMARKS:
        anchor = by_building[bid]["anchor"]
        zone = properties_by_id[bid]["zone_id"]
        landmarks.append({
            "at": [anchor["x"], anchor["z"]],
            "id": lm_id,
            "name": name,
            "source": f"GDD-04 §3.4 (Unit CZ · Queue 15) — Shibnagar "
                      f"landmark; building {bid}, zone {zone} "
                      f"(GENERATED town, citygen.py).",
        })

    return {
        "generated": True,
        "generated_by": "tools/sim/citygen.py — Session 03 Unit 01",
        "warning": "GENERATED DATA: Shibnagar Town is a procedurally "
                   "generated neighbour town for the multi-city "
                   "systems. It is NOT authored design data like "
                   "District 1 (GDD-02).",
        "version": 1,
        "city": {"city_id": CITY_ID, "name": "Shibnagar Town",
                 "kind": "generated_town"},
        "coordinate_system": "Local metres, town frame. Origin at "
                             "the ferry ghat landing; +x east, "
                             "+z south. River band closes the north "
                             "edge.",
        "zones": sorted(ZONE_BOXES.keys()),
        "zone_boxes_m": ZONE_BOXES,
        "landmarks": landmarks,
        "properties": properties,
        "plots": plots,
        "road_segments": [
            {"id": rid, "name": name, "class": cls, "width_m": w,
             "from": list(a), "to": list(b)}
            for rid, name, cls, w, a, b in _ROADS],
        "junctions": [
            {"id": jid, "at": list(at), "signalled": sig}
            for jid, at, sig in _JUNCTIONS],
        "river": {"name": "Rupsha River",
                  "band": {"x0": -40, "x1": 560, "z0": -80, "z1": 0},
                  "flow": "west to east",
                  "ghat": {"at": [280, 0],
                           "name": "Shibnagar Ghat — ferry to Rupsha "
                                   "City"}},
        "terrain_regions": [
            {"id": rid, "name": name, "terrain_class": cls,
             "elevation_m": elev, "bbox": bbox, "buildable": build,
             "restriction": restr}
            for rid, name, cls, elev, bbox, build, restr in _TERRAIN],
    }


def generate_file_text():
    with open(os.path.join(DATA_DIR, "prices.json")) as f:
        prices = json.load(f)
    return json.dumps(generate_town_spec(prices), indent=1,
                      sort_keys=True) + "\n"


if __name__ == "__main__":
    out = os.path.join(DATA_DIR, "city2-shibnagar.json")
    with open(out, "w") as f:
        f.write(generate_file_text())
    print(f"wrote {out}")
