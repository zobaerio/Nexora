"""Session 03 Unit 03 — Land Parcel Management.

Every plot in the blockout (District 1) and the generated town
becomes a land parcel: id, rect, area, zoning category (Unit 04),
ownership, market value, development status — with a persisted
ownership history. Parcels support subdivision, merging and
transfer; every mutation writes parcel_history, so the land
record is auditable like the money ledger.

Market values: a developed parcel carries its building's value
(buildings.building_value — the data's buy prices, or rent
capitalised at the sim's standing x120 convention). Vacant land
is priced by a labelled SIM MODEL rate per sqm by tier
(LAND_RATE_NCR_PER_SQM) — no land-price table exists in the
merged data, and the model says so rather than dressing a guess
up as design data.
"""
import json

from . import buildings as buildings_mod
from . import zoning as zoning_mod

LAND_RATE_NCR_PER_SQM = {1: 120, 2: 250, 3: 450, 4: 800, 5: 1400}


def _plot_rect(plot):
    r = plot["plot_rect_m"]
    return {"x": r["x"], "z": r["z"], "w": r["w"], "d": r["d"]}


def _development_status(building, category):
    if building is None:
        return "vacant"
    if building["id"] == "b_d1_industry_staged_plot":
        return "under_construction"  # the data's own status (GDD-08)
    if building["property_type"] == "plot":
        if category in ("recreational", "environmental_protection"):
            return "protected"
        return "developed"  # terminals, farmland: land in use
    return "developed"


def setup_parcels(store, data, spec, game_minutes):
    """One parcel per plot of the city spec. Idempotent."""
    if store.row("SELECT 1 FROM land_parcels WHERE city_id = ?",
                 (spec["city_id"],)):
        return 0
    buildings = {b["id"]: b for b in spec["properties"]}
    n = 0
    for plot in sorted(spec["plots"],
                       key=lambda p: p.get("building_id") or p["id"]):
        rect = _plot_rect(plot)
        building = buildings.get(plot.get("building_id") or "")
        category = zoning_mod.parcel_category(building,
                                              plot["zone_id"])
        owner_kind = "civic" if building and building.get(
            "civic_owned") else "private"
        if building is not None:
            value = buildings_mod.building_value(data, building)
        else:
            tier = 2
            value = int(rect["w"] * rect["d"]
                        * LAND_RATE_NCR_PER_SQM[tier])
        pid = store.next_id("LP", "land_parcels", "parcel_id")
        store.insert(
            "land_parcels", parcel_id=pid, city_id=spec["city_id"],
            zone_id=plot["zone_id"],
            building_id=plot.get("building_id"),
            x=rect["x"], z=rect["z"], w=rect["w"], d=rect["d"],
            area_sqm=rect["w"] * rect["d"], zoning_category=category,
            owner_kind=owner_kind, owner_character_id=None,
            market_value=value,
            development_status=_development_status(building, category),
            created_at_game_minutes=game_minutes)
        _history(store, pid, "genesis", None,
                 "SYS-CITY" if owner_kind == "civic" else "private",
                 value, {}, game_minutes)
        n += 1
    return n


def _history(store, parcel_id, event, from_owner, to_owner, value,
             details, game_minutes):
    hid = store.next_id("PH", "parcel_history", "history_id")
    store.insert("parcel_history", history_id=hid,
                 parcel_id=parcel_id, event=event,
                 from_owner=from_owner, to_owner=to_owner,
                 value_ncr=value, details=json.dumps(details),
                 game_minutes=game_minutes)
    return hid


def get(store, parcel_id):
    return store.row("SELECT * FROM land_parcels WHERE parcel_id = ?",
                     (parcel_id,))


def ownership_history(store, parcel_id):
    return store.rows("SELECT * FROM parcel_history WHERE parcel_id"
                      " = ? ORDER BY game_minutes, history_id",
                      (parcel_id,))


def _owner_label(row):
    if row["owner_character_id"]:
        return row["owner_character_id"]
    return "SYS-CITY" if row["owner_kind"] == "civic" else "private"


def transfer_parcel(store, parcel_id, to_character_id, price_ncr,
                    game_minutes):
    """Transfer ownership to a character. When a price is given it
    moves through the ledger (buyer -> previous owner; a civic
    seller is SYS-CITY, a private unowned seller is the market
    sink SYS-MARKET). Returns False when the buyer cannot pay —
    no transfer, no history, no partial state."""
    row = get(store, parcel_id)
    if row is None or row["development_status"] == "protected":
        return False
    seller = _owner_label(row)
    if seller == "private":
        seller = "SYS-MARKET"
    if price_ncr and price_ncr > 0:
        if store.balance(to_character_id) < price_ncr:
            return False
        store.transfer(to_character_id, seller, price_ncr,
                       "land_purchase", game_minutes,
                       note=f"parcel {parcel_id}",
                       related_property_id=None)
    store.execute(
        "UPDATE land_parcels SET owner_kind = 'character',"
        " owner_character_id = ?, market_value = ?"
        " WHERE parcel_id = ?",
        (to_character_id, price_ncr or row["market_value"], parcel_id))
    _history(store, parcel_id, "transfer", _owner_label(row),
             to_character_id, price_ncr or row["market_value"], {},
             game_minutes)
    return True


def subdivide_parcel(store, parcel_id, game_minutes):
    """Split a vacant parcel into two along its longer side.
    Returns the new parcel's id, or None when subdivision is not
    honest (developed/protected, or too small to split lawfully)."""
    row = get(store, parcel_id)
    if row is None or row["development_status"] != "vacant":
        return None
    if row["area_sqm"] < 800:
        return None
    if row["w"] >= row["d"]:
        keep_w, new_w = row["w"] / 2, row["w"] - row["w"] / 2
        new_rect = {"x": row["x"] + keep_w, "z": row["z"],
                    "w": new_w, "d": row["d"]}
        store.execute("UPDATE land_parcels SET w = ?, area_sqm = ?"
                      " WHERE parcel_id = ?",
                      (keep_w, keep_w * row["d"], parcel_id))
    else:
        keep_d, new_d = row["d"] / 2, row["d"] - row["d"] / 2
        new_rect = {"x": row["x"], "z": row["z"] + keep_d,
                    "w": row["w"], "d": new_d}
        store.execute("UPDATE land_parcels SET d = ?, area_sqm = ?"
                      " WHERE parcel_id = ?",
                      (keep_d, row["w"] * keep_d, parcel_id))
    new_id = store.next_id("LP", "land_parcels", "parcel_id")
    store.insert(
        "land_parcels", parcel_id=new_id, city_id=row["city_id"],
        zone_id=row["zone_id"], building_id=None,
        x=new_rect["x"], z=new_rect["z"], w=new_rect["w"],
        d=new_rect["d"], area_sqm=new_rect["w"] * new_rect["d"],
        zoning_category=row["zoning_category"],
        owner_kind=row["owner_kind"],
        owner_character_id=row["owner_character_id"],
        market_value=row["market_value"] // 2,
        development_status="vacant",
        created_at_game_minutes=game_minutes)
    store.execute("UPDATE land_parcels SET market_value = ?"
                  " WHERE parcel_id = ?",
                  (row["market_value"] - row["market_value"] // 2,
                   parcel_id))
    _history(store, parcel_id, "subdivided", _owner_label(row),
             _owner_label(row), row["market_value"],
             {"new_parcel_id": new_id}, game_minutes)
    _history(store, new_id, "subdivided_from", _owner_label(row),
             _owner_label(row), row["market_value"] // 2,
             {"source_parcel_id": parcel_id}, game_minutes)
    return new_id


def _adjacent(a, b):
    """True when two rects share an edge (within 1 m tolerance)."""
    eps = 1.0
    side_by_side = abs((a["x"] + a["w"]) - b["x"]) <= eps \
        or abs((b["x"] + b["w"]) - a["x"]) <= eps
    if side_by_side and abs(a["z"] - b["z"]) <= eps \
            and abs(a["d"] - b["d"]) <= eps:
        return "x"
    stacked = abs((a["z"] + a["d"]) - b["z"]) <= eps \
        or abs((b["z"] + b["d"]) - a["z"]) <= eps
    if stacked and abs(a["x"] - b["x"]) <= eps \
            and abs(a["w"] - b["w"]) <= eps:
        return "z"
    return None


def merge_parcels(store, parcel_a, parcel_b, game_minutes):
    """Merge two adjacent vacant parcels of the same zone and
    owner into parcel_a. Returns True on success."""
    a, b = get(store, parcel_a), get(store, parcel_b)
    if a is None or b is None:
        return False
    if a["development_status"] != "vacant" \
            or b["development_status"] != "vacant":
        return False
    if a["zone_id"] != b["zone_id"] \
            or _owner_label(a) != _owner_label(b):
        return False
    axis = _adjacent(a, b)
    if axis is None:
        return False
    if axis == "x":
        x = min(a["x"], b["x"])
        store.execute("UPDATE land_parcels SET x = ?, w = ?,"
                      " area_sqm = ?, market_value = ?"
                      " WHERE parcel_id = ?",
                      (x, a["w"] + b["w"],
                       (a["w"] + b["w"]) * a["d"],
                       a["market_value"] + b["market_value"],
                       parcel_a))
    else:
        z = min(a["z"], b["z"])
        store.execute("UPDATE land_parcels SET z = ?, d = ?,"
                      " area_sqm = ?, market_value = ?"
                      " WHERE parcel_id = ?",
                      (z, a["d"] + b["d"], a["w"] * (a["d"] + b["d"]),
                       a["market_value"] + b["market_value"],
                       parcel_a))
    store.execute("DELETE FROM land_parcels WHERE parcel_id = ?",
                  (parcel_b,))
    _history(store, parcel_a, "merged", _owner_label(a),
             _owner_label(a), a["market_value"] + b["market_value"],
             {"absorbed_parcel_id": parcel_b}, game_minutes)
    _history(store, parcel_b, "merged_into", _owner_label(b),
             _owner_label(a), b["market_value"],
             {"surviving_parcel_id": parcel_a}, game_minutes)
    return True
