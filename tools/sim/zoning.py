"""Session 03 Unit 04 — Urban Zoning Engine.

The ten zoning categories of the Session 03 brief, mapped onto the
district's real zones and buildings. Two levels, kept distinct:

- a zone's PRIMARY category (what the zone is for, from GDD-02 §2's
  zone characters and the generated town's zone design);
- a parcel's category, derived from the building the data puts on
  it (an apartment is residential wherever it stands).

Validation applies to NEW placements (construction, change of
use): the category must be allowed in the zone, residential
density is capped per parcel area, and protected categories take
nothing. Existing buildings that predate the rules are reported
by audit_existing() as grandfathered nonconformities — the sim
does not pretend the old town was built to code.
"""

CATEGORIES = ("residential", "commercial", "industrial",
              "educational", "healthcare", "government",
              "recreational", "agricultural", "transportation",
              "environmental_protection")

ZONE_PRIMARY = {
    "d1_market": "commercial", "d1_oldtown": "residential",
    "d1_riverfront": "recreational", "d1_midtown": "residential",
    "d1_civic": "government", "d1_education": "educational",
    "d1_industry": "industrial", "d1_park": "recreational",
    "d1_transport": "transportation", "d1_uptown": "residential",
    "c2_transport": "transportation", "c2_riverfront": "recreational",
    "c2_residential": "residential", "c2_market": "commercial",
    "c2_civic": "government", "c2_agriculture": "agricultural",
}

# Categories a zone accepts for NEW placements.
ZONE_ALLOWED = {
    "residential": {"residential", "commercial", "educational",
                    "recreational", "government", "healthcare"},
    "commercial": {"commercial", "residential", "government",
                   "educational", "transportation"},
    "industrial": {"industrial", "commercial", "transportation"},
    "educational": {"educational", "residential", "recreational",
                    "commercial", "healthcare"},
    "government": {"government", "educational", "healthcare",
                   "commercial", "transportation"},
    "recreational": {"recreational", "commercial"},
    "transportation": {"transportation", "commercial", "industrial"},
    "agricultural": {"agricultural", "industrial", "residential"},
    "environmental_protection": set(),
}

# One residential unit needs at least this much parcel area —
# the density cap new residential construction must respect.
MIN_AREA_PER_UNIT_SQM = 40


def zone_category(zone_id):
    return ZONE_PRIMARY.get(zone_id)


def building_category(building):
    """The zoning category of a building from the data, by its
    property_type and (for the 'office' grab-bag) its identity."""
    if building is None:
        return None
    bid, ptype = building["id"], building["property_type"]
    if ptype in ("apartment", "house"):
        return "residential"
    if ptype == "shop":
        return "commercial"
    if ptype == "factory":
        return "industrial"
    if ptype == "office":
        if any(k in bid for k in ("school", "college", "library")):
            return "educational"
        if "clinic" in bid:
            return "healthcare"
        if any(k in bid for k in ("police", "city_office",
                                  "town_office")):
            return "government"
        return "commercial"  # bank + private offices
    if ptype == "plot":
        return plot_category(building["zone_id"], bid)
    return None


def plot_category(zone_id, building_id=None):
    """Category of an open plot (no structure): by identity where
    the data names one, else the zone's primary category."""
    bid = building_id or ""
    if "park" in bid:
        return "recreational"
    if any(k in bid for k in ("terminal", "station", "stands",
                              "ghat", "bus_stand")):
        return "transportation"
    if "farmland" in bid:
        return "agricultural"
    if any(k in bid for k in ("construction_yard", "staged_plot")):
        return "industrial"
    return zone_category(zone_id)


def parcel_category(building, zone_id):
    if building is not None:
        return building_category(building)
    return zone_category(zone_id)


def validate_placement(category, zone_id, units=0, area_sqm=None):
    """Validate a proposed new placement. Returns a list of
    violation strings (empty = lawful)."""
    violations = []
    primary = zone_category(zone_id)
    if primary is None:
        return [f"unknown zone {zone_id}"]
    if category not in CATEGORIES:
        violations.append(f"unknown zoning category {category}")
        return violations
    if category == "environmental_protection":
        violations.append("environmental protection land takes no "
                          "placement")
    if category not in ZONE_ALLOWED[primary]:
        violations.append(
            f"{category} is not permitted in a {primary} zone "
            f"({zone_id})")
    if category in ("educational", "healthcare") \
            and primary == "industrial":
        violations.append(
            f"{category} may never be placed in an industrial zone")
    if category == "residential" and units and area_sqm:
        if units > area_sqm // MIN_AREA_PER_UNIT_SQM:
            violations.append(
                f"density cap: {units} units on {area_sqm:.0f} sqm "
                f"exceeds 1 unit per {MIN_AREA_PER_UNIT_SQM} sqm")
    return violations


def audit_existing(data):
    """Existing buildings whose category is not in their zone's
    allowed set — grandfathered nonconformities, reported, never
    silently 'fixed'."""
    out = []
    for spec in data.city_specs():
        for b in spec["properties"]:
            if "part_of" in b:
                continue
            cat = building_category(b)
            primary = zone_category(b["zone_id"])
            if cat and primary and cat not in ZONE_ALLOWED[primary]:
                out.append({"building_id": b["id"], "category": cat,
                            "zone_id": b["zone_id"],
                            "zone_category": primary})
    return out
