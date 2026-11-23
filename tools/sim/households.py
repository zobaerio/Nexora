"""Session 02 Unit 02 — Household Management Engine.

A household is the Session 01 structure — members in one of the 140
real residential units, sharing one tenancy — given a management
surface: composition, living conditions, and the membership changes
that happen only through life events. Session 01 already moves
people for marriage (merge), birth (join) and death (leave, headship
passes). This unit adds the two remaining honest moves:

- leaving home: an adult child forms a new household in a vacant
  unit of the real stock;
- relocation: a household moves to another vacant unit (cheaper
  under financial pressure, or better when thriving).

Rents for vacant units are read from the canonical buildings data
through the property row's building_ref + unit_index — the same
join population.py used to create the stock. A property whose rent
cannot be resolved from the data (a fixture, a future building
without a data row) is simply not movable-to: no rent is ever
invented. This closes the Session 01 report's move-house gap using
only data that was always in the repo.
"""
from . import emotions as emotions_mod
from . import memory as memory_mod
from . import relationships as rel


def members(store, household_id):
    return store.rows(
        "SELECT c.* FROM household_members hm JOIN characters c"
        " ON c.character_id = hm.character_id WHERE hm.household_id = ?"
        " AND hm.left_at_game_minutes IS NULL"
        " AND c.died_at_game_minutes IS NULL ORDER BY c.character_id",
        (household_id,))


def composition(store, household_id):
    """Who lives here, in what roles and life stages — read live."""
    from .identity import age_years
    from .lifecycle import stage_for_age
    now = store.world()["game_minutes"]
    out = []
    for m in members(store, household_id):
        role = store.row("SELECT role FROM household_members"
                         " WHERE household_id = ? AND character_id = ?"
                         " AND left_at_game_minutes IS NULL",
                         (household_id, m["character_id"]))["role"]
        age = age_years(m["born_at_game_minutes"], now)
        out.append({"character_id": m["character_id"],
                    "name": m["display_name"], "role": role, "age": age,
                    "life_stage": stage_for_age(age)})
    return out


def home_property(store, household_id):
    h = store.row("SELECT home_property_id FROM households"
                  " WHERE household_id = ?", (household_id,))
    if not h or not h["home_property_id"]:
        return None
    return store.row("SELECT * FROM properties WHERE property_id = ?",
                     (h["home_property_id"],))


def rent_of_property(store, data, property_row):
    """The monthly rent of a unit, resolved from the canonical
    buildings data via building_ref + unit_index. None when the
    data cannot price this unit — callers must treat None as
    'not available', never as zero."""
    if not property_row or property_row["building_ref"] is None \
            or property_row["unit_index"] is None:
        return None
    # Session 03: the rent index spans both cities' stock (District
    # 1 genesis behaviour is unchanged — same entries, same rents).
    unit = data.rent_index().get(
        (property_row["building_ref"], property_row["unit_index"]))
    if unit:
        return unit["rent"]
    # Session 03 Unit 11: a unit of a building constructed in-sim
    # is priced by its tier's canonical rent (prices.json
    # rent_monthly_by_tier) — the same table the data files' rents
    # come from, so a built unit is movable-to like any other.
    if property_row["building_ref"] and "_built_" in \
            property_row["building_ref"]:
        for t in data.prices["rent_monthly_by_tier"]:
            if t["tier"] == property_row["tier"]:
                return t["rent_ncr"]
    return None


def current_rent(store, data, household_id):
    tenancy = store.row("SELECT rent_per_month FROM tenancies"
                        " WHERE tenant_household_id = ?"
                        " AND ended_at_game_minutes IS NULL",
                        (household_id,))
    if tenancy:
        return tenancy["rent_per_month"]
    prop = home_property(store, household_id)
    return rent_of_property(store, data, prop) if prop else None


def vacant_units(store, data):
    """Vacant, data-priced units of the real stock, cheapest first."""
    out = []
    for p in store.rows("SELECT * FROM properties WHERE status ="
                        " 'vacant' ORDER BY property_id"):
        rent = rent_of_property(store, data, p)
        if rent is not None:
            out.append({"property": p, "rent": rent})
    return sorted(out, key=lambda v: (v["rent"], v["property"]["property_id"]))


def living_conditions(store, data, household_id):
    """Derived living conditions: the home's tier, crowding, and a
    plain-language band. A description of state, not a score anyone
    optimises."""
    prop = home_property(store, household_id)
    mem = members(store, household_id)
    if not prop:
        return {"tier": None, "members": len(mem), "band": "no_home"}
    tier = prop["tier"]
    crowded = len(mem) >= 5
    if tier >= 4 and not crowded:
        band = "comfortable"
    elif tier >= 3 and not crowded:
        band = "adequate"
    elif crowded:
        band = "crowded"
    else:
        band = "basic"
    return {"tier": tier, "members": len(mem),
            "address": prop["address_label"], "band": band,
            "rent": current_rent(store, data, household_id)}


def _start_tenancy(store, household_id, prop, rent, game_minutes):
    store.execute("UPDATE properties SET status = 'rented'"
                  " WHERE property_id = ?", (prop["property_id"],))
    store.execute("UPDATE households SET home_property_id = ?,"
                  " district_id = ? WHERE household_id = ?",
                  (prop["property_id"], prop["district_id"],
                   household_id))
    tid = store.next_id("TN", "tenancies", "tenancy_id")
    store.insert("tenancies", tenancy_id=tid,
                 property_id=prop["property_id"],
                 tenant_household_id=household_id, rent_per_month=rent,
                 started_at_game_minutes=game_minutes)
    return tid


def _end_tenancy(store, household_id, game_minutes):
    tenancy = store.row("SELECT * FROM tenancies WHERE"
                        " tenant_household_id = ?"
                        " AND ended_at_game_minutes IS NULL",
                        (household_id,))
    if tenancy:
        store.execute("UPDATE tenancies SET ended_at_game_minutes = ?"
                      " WHERE tenancy_id = ?",
                      (game_minutes, tenancy["tenancy_id"]))
        store.execute("UPDATE properties SET status = 'vacant'"
                      " WHERE property_id = ?",
                      (tenancy["property_id"],))
    return tenancy


def move_household(store, data, household_id, new_property_id,
                   game_minutes):
    """Relocation: the whole household moves to a vacant unit.
    Returns the new rent, or None if the move is not honestly
    possible (unit taken, or its rent is not in the data)."""
    prop = store.row("SELECT * FROM properties WHERE property_id = ?",
                     (new_property_id,))
    if not prop or prop["status"] != "vacant":
        return None
    rent = rent_of_property(store, data, prop)
    if rent is None:
        return None
    # Queue 15 Unit CY: BX event E3 reads the origin zone before the
    # tenancy moves — _start_tenancy overwrites it.
    origin = store.row("SELECT district_id FROM households"
                       " WHERE household_id = ?", (household_id,))
    origin_zone = origin["district_id"] if origin else None
    _end_tenancy(store, household_id, game_minutes)
    _start_tenancy(store, household_id, prop, rent, game_minutes)
    # Queue 17 Unit DJ: the move-in furnishes the home — the F1
    # "Basic" set for a household whose head holds no furniture
    # (furniture moves with the household, GDD-10 §4, so a household
    # that already holds it is never re-seeded).
    from . import lost_items as lost_items_mod
    # Queue 19 Unit EF: the move wears the furniture the household
    # carries (−2 per move, DQ) — before the move-in seeding below,
    # so newly seeded rows (new furniture, condition 100) are never
    # worn by the move that furnished the home.
    lost_items_mod.apply_furniture_move_wear(
        store, data, household_id, game_minutes,
        new_property_id=prop["property_id"])
    lost_items_mod.seed_furniture_at_move_in(
        store, data, household_id, prop["property_id"], game_minutes)
    for m in members(store, household_id):
        memory_mod.log_life_event(store, m["character_id"], "moved_home",
                                  game_minutes,
                                  details={"household_id": household_id,
                                           "rent": rent})
        emotions_mod.apply_event(store, m["character_id"], "moved_home")
    # Queue 15 Unit CY: BX event E3 — the move itself can lose a
    # packed thing. One loss per move at most; silent at the default
    # rate 0. No rng is passed here (no caller has one in scope);
    # the event resolves its draw from the world's stored seed.
    if origin_zone:
        lost_items_mod.move_house_loss(store, data, None, household_id,
                                       origin_zone, game_minutes)
    return rent


def leave_home(store, data, character_id, game_minutes):
    """An adult leaves the parental household and forms a new one in
    the cheapest suitable vacant unit (same zone preferred). Returns
    the new household id, or None when the stock has no vacancy —
    scarcity is a simulated fact, not an error."""
    char = store.row("SELECT * FROM characters WHERE character_id = ?",
                     (character_id,))
    if not char or not char["household_id"]:
        return None
    old_hid = char["household_id"]
    old_prop = home_property(store, old_hid)
    zone = old_prop["district_id"] if old_prop else None
    options = vacant_units(store, data)
    if not options:
        return None
    same_zone = [o for o in options
                 if o["property"]["district_id"] == zone]
    chosen = (same_zone or options)[0]
    prop = chosen["property"]
    new_hid = store.next_id("HH", "households", "household_id")
    store.insert("households", household_id=new_hid,
                 name=f"{char['last_name']} Household",
                 home_property_id=prop["property_id"],
                 district_id=prop["district_id"],
                 created_at_game_minutes=game_minutes)
    _start_tenancy(store, new_hid, prop, chosen["rent"], game_minutes)
    rel._move_household_member(store, character_id, old_hid, new_hid,
                               game_minutes)
    store.execute("UPDATE household_members SET role = 'head'"
                  " WHERE household_id = ? AND character_id = ?",
                  (new_hid, character_id))
    # Queue 17 Unit DJ: the new household's move-in furnishes its
    # home — the F1 set for a head who holds no furniture rows (the
    # leaver owns none of the old household's furniture, which stays
    # with the old head).
    from . import lost_items as lost_items_mod
    lost_items_mod.seed_furniture_at_move_in(
        store, data, new_hid, prop["property_id"], game_minutes)
    memory_mod.log_life_event(store, character_id, "left_home",
                              game_minutes,
                              details={"from_household": old_hid,
                                       "to_household": new_hid})
    emotions_mod.apply_event(store, character_id, "moved_home")
    return new_hid
