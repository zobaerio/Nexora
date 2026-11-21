#!/usr/bin/env python3
"""NEXORA — committed data validation harness (Audit Unit AD, milestone 1).

Every cross-reference that previous units verified with ad-hoc scripts is
re-checked here, from the repo, forever. Run before any simulation or data
change ships:

    python3 tools/validate_data.py

Exit code 0 = all checks pass. Any failure prints FAIL lines and exits 1.

Checks (from docs/AUDIT-AND-CHECKLIST.md §2/§7):
- All 10 JSON data files parse.
- npc-schedules profession templates match professions.json ids 1:1;
  the 3 life-stage templates exist.
- district1-blockout plots match buildings-district1 properties 1:1 by id.
- Residential stock == 140 units honouring the `part_of` rule
  (single-unit entries counted inside their parents are excluded).
- clothing.json price_refs resolve into prices.json's clothing table;
  profession uniforms cover all 11 professions.
- vehicles.json price_refs resolve into prices.json vehicles, or are
  null (the documented non-buyable gap, GDD-07 §8).
- missions.json zone_refs / profession_refs resolve.
- Wage bands: professions.json income_band_monthly must equal
  prices.json wages_monthly for all 11 professions (the audit §4.2
  duplication is guarded here until Unit AE single-sources it).
- Schedule activities stay within the 8-activity GDD-06 vocabulary and
  location tokens within the known anchor set.
- weather-presets.json carries the 9 canonical preset ids.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

FAILURES = []
NOTES = []


def load(name):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)


def check(cond, label, detail=""):
    if cond:
        print(f"  ok: {label}")
    else:
        FAILURES.append(label)
        print(f"  FAIL: {label} {detail}")


def main():
    names = ["professions.json", "npc-schedules.json",
             "buildings-district1.json", "district1-blockout.json",
             "prices.json", "weather-presets.json", "missions.json",
             "clothing.json", "vehicles.json", "planets.json"]
    data = {}
    for n in names:
        try:
            data[n] = load(n)
        except Exception as e:  # parse failure is a failed check
            check(False, f"{n} parses", f"({e})")
    if FAILURES:
        return finish()
    print(f"  ok: all {len(names)} JSON files parse")

    professions = data["professions.json"]["professions"]
    prof_ids = [p["id"] for p in professions]
    schedules = data["npc-schedules.json"]
    sched_ids = [s["profession_id"] for s in schedules["schedules"]]
    check(sorted(prof_ids) == sorted(sched_ids) and len(prof_ids) == 11,
          "professions <-> schedules 1:1 (11 ids)",
          f"prof={sorted(prof_ids)} sched={sorted(sched_ids)}")
    check(sorted(schedules["life_stage_templates"].keys()) ==
          ["child_school_day", "elder_day", "student_day"],
          "3 life-stage templates present")

    buildings = data["buildings-district1.json"]["properties"]
    blockout = data["district1-blockout.json"]
    plots = blockout.get("plots") or blockout.get("properties") or []
    plot_ids = [p.get("building_id") or p.get("id") for p in plots]
    bldg_ids = [b["id"] for b in buildings]
    check(sorted(plot_ids) == sorted(bldg_ids),
          "blockout plots <-> buildings 1:1 by id",
          f"plots={len(plot_ids)} buildings={len(bldg_ids)}")

    res = [b for b in buildings
           if b["property_type"] in ("apartment", "house")]
    naive = sum(b.get("units", 1) for b in res)
    stock = sum(b.get("units", 1) for b in res if "part_of" not in b)
    check(stock == 140, "residential stock == 140 (part_of rule)",
          f"naive={naive} part_of-adjusted={stock}")
    NOTES.append(f"residential units: naive {naive}, part_of-adjusted {stock}")

    prices = data["prices.json"]
    clothing_prices = {i["id"] for i in prices["clothing"]["items"]}
    clothing = data["clothing.json"]
    bad = [i["id"] for i in clothing["items"]
           if i["price_ref"] not in clothing_prices]
    check(not bad, "clothing price_refs resolve (31 items)",
          f"unresolved={bad}")
    uniforms = clothing.get("profession_uniforms", [])
    uniform_ids = {u["profession_id"] for u in uniforms}
    check(uniform_ids == set(prof_ids),
          "profession uniforms cover all 11 professions",
          f"missing={set(prof_ids) - uniform_ids}")
    bad = [i for u in uniforms for i in u.get("outfit_item_ids", [])
           if i not in {c["id"] for c in clothing["items"]}]
    check(not bad, "uniform outfit_item_ids resolve to clothing items",
          f"unresolved={bad}")

    vehicle_prices = {v["id"] for v in prices["vehicles"]}
    bad = []
    nulls = []
    for v in data["vehicles.json"]["vehicles"]:
        ref = v.get("price_ref")
        if ref is None:
            nulls.append(v["id"])
        elif ref not in vehicle_prices:
            bad.append(v["id"])
    check(not bad, "vehicle price_refs resolve or are documented nulls",
          f"unresolved={bad}")
    NOTES.append(f"vehicles with null price_ref (documented gap): {nulls}")

    zones = set(data["buildings-district1.json"]["zones"])
    bad = []
    for m in data["missions.json"]["missions"]:
        for z in m.get("zone_refs", []):
            if z not in zones:
                bad.append((m["id"], z))
        for p in m.get("profession_refs", []):
            if p not in prof_ids:
                bad.append((m["id"], p))
    check(not bad, "mission zone_refs/profession_refs resolve",
          f"bad={bad}")

    wages = {w["profession_id"]: w for w in prices["wages_monthly"]}
    drift = []
    for p in professions:
        band = p["income_band_monthly"]
        w = wages.get(p["id"])
        if w is None or any(w[t] != band[t]
                            for t in ("entry", "mid", "senior")):
            drift.append(p["id"])
    check(not drift,
          "wage bands equal in professions.json and prices.json (11/11)",
          f"drift={drift}")
    NOTES.append("wage bands are stored twice (audit §4.2); this check "
                 "guards the duplication until Unit AE single-sources it")

    acts, locs = set(), set()
    for s in schedules["schedules"]:
        for b in s["template"]:
            acts.add(b["activity"])
            locs.add(b["location"])
    for t in schedules["life_stage_templates"].values():
        for b in t:
            acts.add(b["activity"])
            locs.add(b["location"])
    check(acts <= {"sleep", "home", "commute", "work", "break", "errand",
                   "leisure", "study"},
          "schedule activities within GDD-06 vocabulary",
          f"extra={acts - {'sleep','home','commute','work','break','errand','leisure','study'}}")
    check(locs <= {"home", "workplace", "transit", "tea_stall", "market",
                   "riverfront", "park", "restaurant", "college_para",
                   "college", "school", "mobile"},
          "schedule locations within known anchor tokens",
          f"extra={locs - {'home','workplace','transit','tea_stall','market','riverfront','park','restaurant','college_para','college','school','mobile'}}")

    preset_ids = sorted(p["id"] for p in
                        data["weather-presets.json"]["presets"])
    check(preset_ids == ["clear_day", "cloudy", "fog", "night_clear",
                         "rain", "snow", "storm", "sunrise_clear",
                         "windy"],
          "9 canonical weather preset ids", f"got={preset_ids}")

    return finish()


def finish():
    for n in NOTES:
        print(f"  note: {n}")
    if FAILURES:
        print(f"VALIDATION FAILED: {len(FAILURES)} check(s): {FAILURES}")
        return 1
    print("VALIDATION PASSED: all data cross-references resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
