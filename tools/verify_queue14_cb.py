"""Verify Queue 14 Unit CB — Named tea-stall + restaurant anchors
(the BS follow-up: resolve_service_anchor() returned "<token>:<zone>"
because no per-stall / per-restaurant ids existed in any source).

Checks the anchors against the sources they must resolve to: GDD-02 §2/§4/§5,
GDD-15 §21.2/§21.3, data/district1-blockout.json, data/buildings-district1.json,
tools/sim/scheduler.py, tools/validate_data.py. Runs the scheduler tests
as part of the check. Run from the repo root:
python3 tools/verify_queue14_cb.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKS = []


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def main():
    gdd02 = (ROOT / "docs" / "GDD-02-RUPSHA-CITY-DISTRICT1.md").read_text()
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    d1 = json.loads((ROOT / "data" / "district1-blockout.json").read_text())
    bldgs = json.loads(
        (ROOT / "data" / "buildings-district1.json").read_text())
    sched = (ROOT / "tools" / "sim" / "scheduler.py").read_text()
    validator = (ROOT / "tools" / "validate_data.py").read_text()

    anchors = d1.get("service_anchors", [])

    # 1. The anchors exist in the data: 9, in the right places.
    check(len(anchors) == 9, "district1-blockout.json has 9 service_anchors",
          f"got {len(anchors)}")
    by_type_zone = {}
    for a in anchors:
        by_type_zone.setdefault((a["type"], a["zone_id"]), []).append(a)
    check(len(by_type_zone.get(("tea_stall", "d1_market"), [])) == 6,
          "6 Boro Bazar tea stalls in d1_market")
    check(len(by_type_zone.get(("tea_stall", "d1_riverfront"), [])) == 1,
          "1 riverfront tea stall in d1_riverfront")
    check(len(by_type_zone.get(("restaurant", "d1_market"), [])) == 1,
          "1 market-kitchen restaurant in d1_market")
    check(len(by_type_zone.get(("restaurant", "d1_uptown"), [])) == 1,
          "1 rooftop restaurant in d1_uptown")
    check("anchor_restaurant_rooftop" in [a["id"] for a in anchors],
          "rooftop anchor id exists")
    check("anchor_restaurant_market_kitchen" in [a["id"] for a in anchors],
          "market-kitchen anchor id exists")

    # 2. Sources: counts/zones from GDD-02; names labelled as authored.
    check("tea stalls ×6" in gdd02 or "tea stalls \\u00d76" in gdd02,
          "GDD-02 §2 sources the 6 Boro Bazar tea stalls")
    check("Rooftop restaurant" in gdd02 or "rooftop restaurant" in gdd02,
          "GDD-02 §4.6/§5 sources the rooftop restaurant")
    check("Unit CB authored name" in json.dumps(anchors),
          "stall names are labelled as Unit CB authored names")
    check("Named service anchors (Unit CB" in gdd02,
          "GDD-02 §5 records the named anchors")

    # 3. Building refs resolve.
    bldg_ids = {b["id"] for b in bldgs["properties"]}
    bad = [a["id"] for a in anchors
           if "building_id" in a and a["building_id"] not in bldg_ids]
    check(not bad, "anchor building_ids resolve to buildings-district1",
          f"bad={bad}")
    kitchen = [a for a in anchors
               if a["id"] == "anchor_restaurant_market_kitchen"][0]
    check(kitchen.get("building_id") == "b_d1_market_hall_units",
          "market kitchen sits in the market hall building")
    roof = [a for a in anchors
            if a["id"] == "anchor_restaurant_rooftop"][0]
    check(roof.get("building_id") == "b_d1_uptown_rooftop_restaurant",
          "rooftop restaurant sits in the rooftop tower building")

    # 4. The scheduler returns named ids, with the documented fallback.
    check("anchors=None" in sched,
          "resolve_service_anchor takes an optional anchors list")
    check('return zone, a["id"]' in sched,
          "resolve_service_anchor returns the named anchor id")
    check("first anchor of that type in the resolved zone" in sched
          or "first anchor" in sched,
          "scheduler documents the within-zone file-order rule")
    check("service_anchors" in sched,
          "instantiate() passes the blockout service_anchors list")
    check("Named anchors (Unit CB" in gdd15,
          "GDD-15 §21.2 records the named-anchor follow-up")

    # 5. The zone rule is unchanged; the validator guards the anchors.
    check("check_service_anchors" in validator,
          "validate_data.py guards the service anchors")
    res = subprocess.run([sys.executable, "tools/validate_data.py"],
                         cwd=ROOT, capture_output=True, text=True)
    check(res.returncode == 0, "validate_data.py green",
          (res.stdout + res.stderr).strip().splitlines()[-1])
    res2 = subprocess.run([sys.executable, "-m", "unittest",
                           "tools.sim.tests.test_scheduler", "-v"],
                          cwd=ROOT, capture_output=True, text=True)
    check(res2.returncode == 0, "test_scheduler.py passes (incl. CB tests)",
          (res2.stdout + res2.stderr).strip().splitlines()[-1])

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
