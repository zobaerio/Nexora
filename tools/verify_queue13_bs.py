"""Verify Queue 13 Unit BS — GDD-15 §21.2/§21.3 anchor resolution
implemented in tools/sim/scheduler.py (the change Unit BQ specified).

Checks the implementation against the sources it must resolve to:
GDD-15 §18/§21, GDD-06 §3, data/npc-schedules.json, GDD-02 §2/§5,
tools/sim/tests/test_scheduler.py.
Prints one line per check and a summary; exits 0 only when every check
passes. Run from the repo root: python3 tools/verify_queue13_bs.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKS = []


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def main():
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    gdd06 = (ROOT / "docs" / "GDD-06-NPC-BEHAVIOUR.md").read_text()
    sched = (ROOT / "tools" / "sim" / "scheduler.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_scheduler.py").read_text()
    schedules = json.loads(
        (ROOT / "data" / "npc-schedules.json").read_text())
    professions = json.loads(
        (ROOT / "data" / "professions.json").read_text())

    # 1. The §21.2 implementation note exists, headed Unit BS.
    check("**Implemented (Unit BS, Queue 13" in gdd15
          and "resolve_service_anchor" in gdd15,
          "GDD-15 §21.2 records the BS implementation")
    check("**Recorded discrepancy — resolved by implementation "
          "(Unit BS, Queue 13)" in gdd15,
          "GDD-15 §21.3 records the restaurant entry removal")

    # 2. LEISURE_ZONE has no service-token entry.
    lz = re.search(r"LEISURE_ZONE = \{(.*?)\}", sched, re.S).group(1)
    check("tea_stall" not in lz, "LEISURE_ZONE has no tea_stall entry")
    check("restaurant" not in lz, "LEISURE_ZONE has no restaurant entry")
    check('"d1_midtown"' not in lz,
          "no d1_midtown mapping survives in LEISURE_ZONE")

    # 3. The anchor table carries exactly the two sourced zone pairs.
    m = re.search(r"SERVICE_ANCHOR_ZONES = \{(.*?)\n\}", sched, re.S)
    check(m is not None, "SERVICE_ANCHOR_ZONES table exists")
    table = m.group(1) if m else ""
    check('"tea_stall": ("d1_market", "d1_riverfront")' in table,
          "tea_stall candidates are d1_market + d1_riverfront (GDD-02 §2/§5)")
    check('"restaurant": ("d1_market", "d1_uptown")' in table,
          "restaurant candidates are d1_market + d1_uptown (GDD-02 §5/§4.6)")

    # 4. The resolver exists with the home -> work -> default rule.
    check("def resolve_service_anchor(location, home_zone, "
          "workplace_zone)" in sched,
          "resolve_service_anchor() exists with the three inputs")
    fn = sched.split("def resolve_service_anchor")[1].split(
        "def _mins")[0] if "def resolve_service_anchor" in sched else ""
    check("if home_zone in candidates" in fn
          and "elif workplace_zone in candidates" in fn,
          "resolver prefers home zone, then workplace zone")
    check('zone = candidates[0]' in fn,
          "resolver defaults to the first candidate (d1_market)")
    check('f"{location}:{zone}"' in fn,
          "stored anchor id is type:zone (no invented per-stall id)")

    # 5. instantiate() resolves service anchors first and stores both.
    inst = sched.split("def instantiate(")[1]
    check('if b["location"] in SERVICE_ANCHOR_ZONES:' in inst,
          "instantiate() checks service anchors before LEISURE_ZONE")
    check('b["anchor"] = anchor' in inst,
          "instantiate() stores the resolved anchor on the block")
    check('else:  # transit, mobile: local to home/work path' in inst,
          "transit/mobile keep the home_zone fallback")

    # 6. The templates the brief names really carry the blocks.
    by_prof = {s["profession_id"]: s for s in schedules["schedules"]}
    ce = [b for b in by_prof["civil_engineer"]["template"]
          if b["location"] == "tea_stall"]
    check(len(ce) == 2,
          "civil_engineer template has two tea-stall blocks",
          f"n={len(ce)}")
    bo = [b for b in by_prof["business_owner"]["template"]
          if b["location"] == "restaurant"]
    check(len(bo) == 1 and bo[0]["from"] == "13:30"
          and bo[0]["to"] == "14:30",
          "business_owner template has the one restaurant block 13:30-14:30")
    wz = {p["id"]: p["workplace_zone"] for p in professions["professions"]}
    check(wz["business_owner"] == "d1_uptown",
          "business_owner workplace is d1_uptown (rooftop zone)")
    check(wz["civil_engineer"] == "d1_industry",
          "civil_engineer workplace is d1_industry (no stall there)")

    # 7. The tests prove the brief's three assertions.
    for name in ("test_service_anchor_tea_stall",
                 "test_service_anchor_restaurant",
                 "test_service_anchor_home_zone_wins",
                 "test_service_anchor_workplace_wins",
                 "test_transit_mobile_keep_home_zone",
                 "test_leisure_zone_has_no_service_tokens"):
        check(f"def {name}" in tests, f"scheduler test {name} exists")
    check('assertNotEqual(b["zone"], "d1_midtown")' in tests,
          "restaurant test asserts never d1_midtown")

    # 8. GDD-06 §3 still states the nearest-anchor rule this unit
    #    implements; §18.2/§18.5/§21.4 now read as implemented.
    check("Nearest leisure/service anchor of that type in the NPC's "
          "zone cluster" in gdd06,
          "GDD-06 §3 states the nearest-anchor rule")
    check("### 18.5 The `tea_stall` discrepancy — resolved by "
          "implementation" in gdd15,
          "§18.5 now reads as resolved, not recorded")
    check("Now (implemented rule, Unit BS)" in gdd15,
          "§21.4 table now reads as implemented")
    check("implemented by Queue 13, Unit BS" in gdd15.split(
        "- **G8 — Current zone")[1].split("- **G9")[0],
          "§12.8 G8 points at the BS implementation")

    # 9. The zone-cluster operationalisation is labelled as a decision.
    check("this unit's labelled decisions" in gdd15.split("### 21.2")[1].split(
        "### 21.3")[0],
          "§21.2 labels the zone-cluster operationalisation as BS's decision")
    check("no coordinates for a household property" in sched
          or "stores no coordinates" in sched,
          "scheduler documents why nearest is zone-based, not geometric")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed; "
          f"{len(failed)} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
