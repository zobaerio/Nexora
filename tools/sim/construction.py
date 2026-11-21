"""Session 03 Unit 11 — Architecture & Construction Engine.

GDD-08's construction lifecycle, implemented against the ledger:
land selection -> planning -> design approval -> financing ->
construction approval -> foundation -> frame -> walls -> roof ->
finishing -> completion -> occupancy, then maintenance /
renovation / demolition as later project kinds.

The design law holds literally: a building is a ledger with
walls. The client funds estimate + fee at the financing stage
(ledger 'construction_funding' to the engineer, GDD-08 §6.1's
escrow line on the engineer's ledger); each build stage buys its
materials from the market at prices.json's construction_materials
prices ('purchase' rows) before work starts; stage completion
releases the stage's materials + fee share to the engineer
(tracked on the job record, GDD-08 §6.2 — the money is already
the engineer's escrow, so the release is the job's accounting,
not a second transfer). The BOQ is GDD-08 §3's worked example,
verbatim quantities, scaled by the plan: at scale 1.0 the
materials total is exactly 86,700 NCr and the entry fee 8,670.

Weather halts outdoor stages on storm days (the storm preset's
cover-seeking family is the sim's outdoor-work halt signal —
GDD-08 §2's rule, GDD-06 §7). A stage whose engineer is absent
completes uninspected and rolls the defect risk: rework re-buys
40% of the stage's materials from the escrow. Crew are real
employed construction_workers; an absent crew means the stage
waits. Crew wages ride the existing monthly wage system (they
are salaried employments) — stated here, not double-paid.

Renovation and demolition are simpler kinds on the same record:
renovation's works consume a materials budget of 15% of the
building's value and restore its condition; demolition clears a
building back to a vacant parcel for 5% of its value.
"""
import json

from . import buildings as buildings_mod
from . import cities as cities_mod
from . import households as households_mod
from . import memory as memory_mod
from . import terrain as terrain_mod
from . import zoning as zoning_mod

# GDD-08 §3's worked-example quantities (the table is authority).
BOQ = {
    "foundation": {"cement_bag_50kg": 14, "brick_first_class": 0.5,
                   "sand_river": 70, "stone_aggregate": 60},
    "frame": {"cement_bag_50kg": 16, "rebar_60_grade": 0.13,
              "sand_river": 60, "stone_aggregate": 60},
    "walls": {"brick_first_class": 0.75, "cement_bag_50kg": 5,
              "sand_river": 45},
    "roof": {"cement_bag_50kg": 15, "rebar_60_grade": 0.06,
             "sand_river": 45, "stone_aggregate": 55},
    "finishing": {"tiles_floor": 30, "paint_weathercoat": 5,
                  "cement_bag_50kg": 2},
}
BUILD_STAGES = ("foundation", "frame", "walls", "roof", "finishing")
STAGE_DAYS = {"planning": 1, "design_approval": 1, "financing": 1,
              "construction_approval": 1, "foundation": 3, "frame": 3,
              "walls": 2, "roof": 2, "finishing": 2, "works": 4}
OUTDOOR_STAGES = {"foundation", "frame", "walls", "roof", "works"}
STAGE_ORDER = ("planning", "design_approval", "financing",
               "construction_approval") + BUILD_STAGES
KIND_STAGES = {
    "new_build": STAGE_ORDER,
    "extension": STAGE_ORDER,
    "renovation": ("planning", "financing", "works", "finishing"),
    "demolition": ("planning", "financing", "construction_approval",
                   "works"),
}
FEE_ENTRY, FEE_SENIOR = 0.10, 0.15  # GDD-08 §6.1


def material_prices(data):
    return {m["id"]: m["price_ncr"]
            for m in data.prices["construction_materials"]}


def stage_material_cost(data, stage, scale):
    prices = material_prices(data)
    return int(round(sum(qty * prices[mid] for mid, qty
                         in BOQ[stage].items()) * scale))


def estimate_for(data, plan):
    """Materials estimate for a plan (new_build/extension), from
    the BOQ at the plan's scale. Scale 1.0 -> exactly 86,700."""
    scale = plan.get("scale")
    if scale is None:
        scale = max(1, plan.get("units", 1)) * max(1, plan.get(
            "floors", 1)) / 2
    return sum(stage_material_cost(data, s, scale)
               for s in BUILD_STAGES), scale


def _employed_as(store, profession_id):
    return [r["character_id"] for r in store.rows(
        "SELECT e.character_id FROM employments e JOIN characters c"
        " ON c.character_id = e.character_id WHERE e.profession_id"
        " = ? AND e.ended_at_game_minutes IS NULL"
        " AND c.died_at_game_minutes IS NULL ORDER BY e.character_id",
        (profession_id,))]


def _alive_employed(store, character_id, profession_id):
    return store.row(
        "SELECT 1 FROM employments e JOIN characters c"
        " ON c.character_id = e.character_id WHERE e.character_id"
        " = ? AND e.profession_id = ? AND e.ended_at_game_minutes"
        " IS NULL AND c.died_at_game_minutes IS NULL",
        (character_id, profession_id)) is not None


def _engineer_tier(store, engineer_id):
    row = store.row("SELECT tier FROM employments WHERE character_id"
                    " = ? AND profession_id = 'civil_engineer'"
                    " AND ended_at_game_minutes IS NULL",
                    (engineer_id,))
    return row["tier"] if row else 1


def start_project(store, data, *, city_id, kind="new_build",
                  parcel_id=None, target_building_id=None,
                  client_character_id=None, engineer_character_id=None,
                  plan=None, game_minutes, day_index):
    """Open a construction job. Validates zoning (Unit 04) and
    terrain (Unit 02) for builds; raises ValueError with the
    violations when the job is not lawful — a rejected plan is a
    design-approval fact, not a silent no-op."""
    plan = dict(plan or {})
    parcel = None
    if kind in ("new_build",):
        parcel = store.row("SELECT * FROM land_parcels WHERE"
                           " parcel_id = ?", (parcel_id,))
        if parcel is None:
            raise ValueError(f"unknown parcel {parcel_id}")
        if parcel["development_status"] not in (
                "vacant", "under_construction"):
            raise ValueError("parcel is not available for building")
        category = zoning_mod.building_category(
            {"id": "planned", "property_type":
             plan.get("property_type", "house")})
        violations = zoning_mod.validate_placement(
            category, parcel["zone_id"], units=plan.get("units", 1),
            area_sqm=parcel["area_sqm"])
        spec = data.city_spec(city_id)
        ok, terr = terrain_mod.validate_build(
            terrain_mod.regions_for_spec(spec),
            {"x": parcel["x"], "z": parcel["z"], "w": parcel["w"],
             "d": parcel["d"]})
        violations += terr
        if violations:
            raise ValueError("; ".join(violations))
    engineers = _employed_as(store, "civil_engineer")
    engineer = engineer_character_id or (engineers[0] if engineers
                                         else None)
    if engineer is None or not _alive_employed(store, engineer,
                                               "civil_engineer"):
        raise ValueError("no civil engineer available for the job")
    crew = _employed_as(store, "construction_worker")[:3]
    if len(crew) < 2:
        raise ValueError("insufficient construction crew available")
    if kind in ("new_build", "extension"):
        estimate, scale = estimate_for(data, plan)
        plan["scale"] = scale
    elif kind == "renovation":
        state = store.row("SELECT economic_value FROM building_state"
                          " WHERE building_id = ?",
                          (target_building_id,))
        if state is None:
            raise ValueError("renovation target has no building state")
        estimate = int(round(state["economic_value"] * 0.15))
    else:  # demolition
        state = store.row("SELECT economic_value FROM building_state"
                          " WHERE building_id = ?",
                          (target_building_id,))
        if state is None:
            raise ValueError("demolition target has no building state")
        estimate = int(round(state["economic_value"] * 0.05))
    tier = _engineer_tier(store, engineer)
    fee = int(round(estimate * (FEE_SENIOR if tier >= 3
                                else FEE_ENTRY)))
    pid = store.next_id("CP", "construction_projects", "project_id")
    store.insert(
        "construction_projects", project_id=pid, city_id=city_id,
        parcel_id=parcel_id, kind=kind,
        target_building_id=target_building_id,
        client_character_id=client_character_id,
        engineer_character_id=engineer, plan=json.dumps(plan),
        stage=KIND_STAGES[kind][0], stage_day=0, status="active",
        estimate_materials_ncr=estimate, fee_ncr=fee, funding_ncr=0,
        spent_materials_ncr=0, paid_engineer_ncr=0,
        crew=json.dumps(crew), inspections="{}", defects="[]",
        created_day=day_index, deadline_day=day_index + 40,
        created_at_game_minutes=game_minutes,
        updated_at_game_minutes=game_minutes)
    if parcel is not None:
        store.execute("UPDATE land_parcels SET development_status ="
                      " 'under_construction' WHERE parcel_id = ?",
                      (parcel_id,))
    eid = store.next_id("CE", "city_events", "event_id")
    store.insert("city_events", event_id=eid, city_id=city_id,
                 event_type="construction_started",
                 details=json.dumps({"project_id": pid, "kind": kind,
                                     "estimate_ncr": estimate,
                                     "fee_ncr": fee}),
                 game_minutes=game_minutes)
    return pid


def start_civic_project(store, data, city_id, game_minutes, day_index):
    """Unit 10's commission: the city builds housing. Site order:
    a vacant residentially-zoned parcel (new build), else an
    extension on the city's lowest-tier apartment block
    (densification). Funded only when SYS-CITY's real balance
    covers estimate + fee. Returns the project id or None."""
    spec = data.city_spec(city_id)
    zones = set(spec["zones"])
    for parcel in store.rows(
            "SELECT * FROM land_parcels WHERE city_id = ? AND"
            " development_status = 'vacant' ORDER BY parcel_id",
            (city_id,)):
        if parcel["zoning_category"] != "residential":
            continue
        plan = {"property_type": "apartment", "units": 6, "floors": 3,
                "tier": 2}
        estimate, _ = estimate_for(data, plan)
        fee = int(round(estimate * FEE_ENTRY))
        if store.balance("SYS-CITY") < estimate + fee:
            return None
        try:
            return start_project(
                store, data, city_id=city_id, kind="new_build",
                parcel_id=parcel["parcel_id"], plan=plan,
                game_minutes=game_minutes, day_index=day_index)
        except ValueError:
            continue
    candidates = [b for b in spec["properties"]
                  if b["property_type"] == "apartment"
                  and "part_of" not in b]
    for b in sorted(candidates, key=lambda b: (b["tier"], b["id"])):
        plan = {"property_type": "apartment", "units": 4,
                "floors": buildings_mod.floors_for(b),
                "tier": b["tier"]}
        estimate, _ = estimate_for(data, plan)
        fee = int(round(estimate * FEE_ENTRY))
        if store.balance("SYS-CITY") < estimate + fee:
            return None
        parcel = store.row("SELECT parcel_id FROM land_parcels WHERE"
                           " building_id = ?", (b["id"],))
        try:
            return start_project(
                store, data, city_id=city_id, kind="extension",
                parcel_id=parcel["parcel_id"] if parcel else None,
                target_building_id=b["id"], plan=plan,
                game_minutes=game_minutes, day_index=day_index)
        except ValueError:
            continue
    return None


def _save(store, proj, game_minutes, **fields):
    sets = ", ".join(f"{k} = ?" for k in fields)
    store.execute(f"UPDATE construction_projects SET {sets},"
                  " updated_at_game_minutes = ? WHERE project_id = ?",
                  tuple(fields.values()) + (game_minutes,
                                            proj["project_id"]))
    proj.update(fields)


def _pay(store, from_id, to_id, amount, reason, game_minutes, note):
    if amount <= 0:
        return 0
    paid = min(amount, max(0, store.balance(from_id))) \
        if from_id != "SYS-CITY" else amount
    if paid > 0:
        store.transfer(from_id, to_id, paid, reason, game_minutes,
                       note=note)
    return paid


def daily_progress(store, data, rng, day_index, weather_preset,
                   game_minutes):
    """Advance every active project by one day. Deterministic:
    projects in id order, defect rolls from keyed streams."""
    if not cities_mod.is_setup(store):
        return []
    storm = weather_preset == "storm"
    results = []
    for proj in store.rows("SELECT * FROM construction_projects"
                           " WHERE status = 'active' ORDER BY"
                           " project_id"):
        results.append(_advance(store, data, rng, dict(proj),
                                day_index, storm, game_minutes))
    return results


def _advance(store, data, rng, proj, day_index, storm, game_minutes):
    pid = proj["project_id"]
    stages = KIND_STAGES[proj["kind"]]
    stage = proj["stage"]
    plan = json.loads(proj["plan"])
    inspections = json.loads(proj["inspections"])
    engineer_ok = _alive_employed(store, proj["engineer_character_id"],
                                  "civil_engineer")
    crew = [c for c in json.loads(proj["crew"])
            if _alive_employed(store, c, "construction_worker")]

    if stage == "financing" and not proj["funding_ncr"]:
        amount = proj["estimate_materials_ncr"] + proj["fee_ncr"]
        client = proj["client_character_id"]
        if client and store.balance(client) < amount:
            return f"{pid}: stalled_funding"  # GDD-08 §6.4 freeze
        funder = client or "SYS-CITY"
        store.transfer(funder, proj["engineer_character_id"], amount,
                       "construction_funding", game_minutes,
                       note=f"project {pid} funding")
        _save(store, proj, game_minutes, funding_ncr=amount)

    is_build = stage in BUILD_STAGES or stage == "works"
    if is_build:
        if storm and stage in OUTDOOR_STAGES:
            return f"{pid}: weather_halted"
        if len(crew) < 2:
            return f"{pid}: awaiting_crew"
        entry = inspections.setdefault(stage, {})
        if not entry.get("materials_bought"):
            if proj["kind"] in ("new_build", "extension"):
                cost = stage_material_cost(data, stage,
                                           plan.get("scale", 1.0))
            else:
                cost = proj["estimate_materials_ncr"] \
                    if stage == "works" else 0
            if cost > 0:
                _pay(store, proj["engineer_character_id"], "SYS-MARKET",
                     cost, "purchase", game_minutes,
                     note=f"project {pid} {stage} materials")
            entry["materials_bought"] = True
            entry["materials_ncr"] = cost
            _save(store, proj, game_minutes,
                  inspections=json.dumps(inspections),
                  spent_materials_ncr=proj["spent_materials_ncr"]
                  + cost)
    _save(store, proj, game_minutes, stage_day=proj["stage_day"] + 1)
    if proj["stage_day"] + 1 < STAGE_DAYS[stage]:
        return f"{pid}: {stage} day {proj['stage_day'] + 1}"
    # Stage complete.
    if is_build:
        entry = inspections.setdefault(stage, {})
        entry["inspected"] = bool(engineer_ok)
        defects = json.loads(proj["defects"])
        if not engineer_ok:
            roll = rng.stream("construction-defect", pid,
                              stage).random()
            if roll < 0.5:
                rework = int(round(entry.get("materials_ncr", 0)
                                   * 0.4))
                if rework > 0:
                    _pay(store, proj["engineer_character_id"],
                         "SYS-MARKET", rework, "purchase",
                         game_minutes,
                         note=f"project {pid} {stage} defect rework")
                defects.append({"stage": stage, "rework_ncr": rework,
                                "cause": "uninspected_stage"})
                _save(store, proj, game_minutes,
                      defects=json.dumps(defects),
                      spent_materials_ncr=proj["spent_materials_ncr"]
                      + rework)
        build_count = sum(1 for s in stages if s in BUILD_STAGES
                          or s == "works")
        share = (entry.get("materials_ncr", 0)
                 + proj["fee_ncr"] // max(1, build_count))
        _save(store, proj, game_minutes,
              inspections=json.dumps(inspections),
              paid_engineer_ncr=proj["paid_engineer_ncr"] + share)
    idx = stages.index(stage)
    if idx + 1 < len(stages):
        _save(store, proj, game_minutes, stage=stages[idx + 1],
              stage_day=0)
        return f"{pid}: {stage} complete"
    _complete_project(store, data, proj, day_index, game_minutes)
    return f"{pid}: completed"


def _unit_value(data, tier):
    for t in data.prices["rent_monthly_by_tier"]:
        if t["tier"] == tier:
            return t["buy_price_guide_ncr"] or t["rent_ncr"] * 120
    return 0


def _complete_project(store, data, proj, day_index, game_minutes):
    pid, kind = proj["project_id"], proj["kind"]
    plan = json.loads(proj["plan"])
    result_building = None
    if kind == "new_build":
        seq = store.row("SELECT COUNT(*) AS n FROM building_state"
                        " WHERE building_id LIKE '%_built_%'")["n"] + 1
        prefix = "d1" if proj["city_id"] == cities_mod.RUPSHA \
            else "c2"
        result_building = f"b_{prefix}_built_{seq:03d}"
        parcel = store.row("SELECT * FROM land_parcels WHERE"
                           " parcel_id = ?", (proj["parcel_id"],))
        per_unit = _unit_value(data, plan.get("tier", 2))
        for i in range(plan.get("units", 1)):
            prop_id = store.next_id("PR", "properties", "property_id")
            store.insert(
                "properties", property_id=prop_id,
                property_type=plan.get("property_type", "house"),
                district_id=parcel["zone_id"],
                address_label=f"New Building {result_building} "
                              f"#{i + 1}",
                tier=plan.get("tier", 2), status="vacant",
                market_value=per_unit, building_ref=result_building,
                unit_index=i)
        buildings_mod.register_built_building(
            store, data, result_building, proj["city_id"],
            floors=plan.get("floors", 1), tier=plan.get("tier", 2),
            property_type=plan.get("property_type", "house"),
            units=plan.get("units", 1),
            value=per_unit * plan.get("units", 1),
            game_minutes=game_minutes)
        store.execute("UPDATE land_parcels SET building_id = ?,"
                      " development_status = 'developed' WHERE"
                      " parcel_id = ?",
                      (result_building, proj["parcel_id"]))
    elif kind == "extension":
        target = proj["target_building_id"]
        parcel = store.row("SELECT * FROM land_parcels WHERE"
                           " building_id = ?", (target,))
        zone = parcel["zone_id"] if parcel else "d1_midtown"
        existing = store.row("SELECT MAX(unit_index) AS m FROM"
                             " properties WHERE building_ref = ?",
                             (target,))
        start = (existing["m"] + 1) if existing and existing["m"] \
            is not None else 0
        per_unit = _unit_value(data, plan.get("tier", 2))
        for i in range(plan.get("units", 1)):
            prop_id = store.next_id("PR", "properties", "property_id")
            store.insert(
                "properties", property_id=prop_id,
                property_type=plan.get("property_type", "apartment"),
                district_id=zone, address_label=f"Extension {target} "
                f"#{start + i + 1}", tier=plan.get("tier", 2),
                status="vacant", market_value=per_unit,
                building_ref=target, unit_index=start + i)
        state = store.row("SELECT economic_value FROM building_state"
                          " WHERE building_id = ?", (target,))
        if state:
            store.execute("UPDATE building_state SET economic_value"
                          " = ? WHERE building_id = ?",
                          (state["economic_value"]
                           + per_unit * plan.get("units", 1), target))
        result_building = target
    elif kind == "renovation":
        state = store.row("SELECT economic_value FROM building_state"
                          " WHERE building_id = ?",
                          (proj["target_building_id"],))
        buildings_mod.apply_maintenance(store,
                                        proj["target_building_id"],
                                        65, game_minutes)
        if state:
            store.execute("UPDATE building_state SET economic_value"
                          " = ? WHERE building_id = ?",
                          (int(state["economic_value"] * 1.1),
                           proj["target_building_id"]))
        result_building = proj["target_building_id"]
    elif kind == "demolition":
        target = proj["target_building_id"]
        store.execute("DELETE FROM properties WHERE building_ref = ?",
                      (target,))
        store.execute("DELETE FROM building_state WHERE building_id"
                      " = ?", (target,))
        store.execute("UPDATE land_parcels SET building_id = NULL,"
                      " development_status = 'vacant' WHERE"
                      " building_id = ?", (target,))
        result_building = target
    _save(store, proj, game_minutes, status="completed",
          completed_day=day_index, result_building_id=result_building)
    # Occupancy: a private client household moves into the first
    # new unit (the GDD-08 completion moment).
    if kind == "new_build" and proj["client_character_id"]:
        client = store.row("SELECT household_id FROM characters WHERE"
                           " character_id = ?",
                           (proj["client_character_id"],))
        if client and client["household_id"]:
            prop = store.row("SELECT property_id FROM properties"
                             " WHERE building_ref = ? ORDER BY"
                             " unit_index LIMIT 1", (result_building,))
            if prop:
                rent = households_mod.rent_of_property(
                    store, data, store.row(
                        "SELECT * FROM properties WHERE property_id"
                        " = ?", (prop["property_id"],)))
                if rent is not None and households_mod.move_household(
                        store, data, client["household_id"],
                        prop["property_id"], game_minutes):
                    _save(store, proj, game_minutes, status="occupied")
    eid = store.next_id("CE", "city_events", "event_id")
    store.insert("city_events", event_id=eid, city_id=proj["city_id"],
                 event_type="construction_completed",
                 details=json.dumps({"project_id": pid, "kind": kind,
                                     "building_id": result_building}),
                 game_minutes=game_minutes)
    memory_mod.log_life_event(store, proj["engineer_character_id"],
                              "construction_completed", game_minutes,
                              details={"project_id": pid, "kind": kind})
