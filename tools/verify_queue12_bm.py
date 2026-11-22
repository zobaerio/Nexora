"""Verify Queue 12 Unit BM — GDD-04 §3.4 discovery progress record.

Checks the record section against the sources it must resolve to:
GDD-02 §4 (landmarks), data/district1-blockout.json (ids + zone boxes),
GDD-07 §1 / data/vehicles.json (bus routes), GDD-04 §3.1/§5,
data/schema.sql (accounts, achievements), data/missions.json
(reward pattern).
Prints one line per check and a summary; exits 0 only when every check
passes. Run from the repo root: python3 tools/verify_queue12_bm.py
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
    gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md").read_text()
    gdd02 = (ROOT / "docs" / "GDD-02-RUPSHA-CITY-DISTRICT1.md").read_text()
    gdd07 = (ROOT / "docs" / "GDD-07-VEHICLES-AND-TRAFFIC.md").read_text()
    schema = (ROOT / "data" / "schema.sql").read_text()
    blockout = json.loads(
        (ROOT / "data" / "district1-blockout.json").read_text())
    vehicles = json.loads((ROOT / "data" / "vehicles.json").read_text())
    missions = json.loads((ROOT / "data" / "missions.json").read_text())
    pattern = next(s["reward_pattern"] for s in
                   missions["side_mission_types"] if s["type"] == "discovery")

    # 1. §3.4 exists, headed Unit BM, Queue 12.
    m34 = re.search(r"### 3\.4 Discovery Progress Record \(Unit BM · Queue 12",
                    gdd04)
    check(m34 is not None, "GDD-04 §3.4 exists, headed Unit BM, Queue 12")
    sec = gdd04[m34.start():] if m34 else ""
    sec = sec.split("## 4. Free-Roam Rules")[0]

    # 2. All five record fields + the composite key are defined.
    fields = ["account_id", "discoverable_type", "discoverable_id",
              "discovered_at_game_minutes", "discovered_in_zone"]
    missing = [f for f in fields if f not in sec]
    check(not missing, "discovery_progress defines all five fields",
          f"missing={missing}")
    check("PK `(account_id, discoverable_type, discoverable_id)`" in sec,
          "composite primary key is (account, type, id)")

    # 3. Account-level home, with the achievements discrepancy recorded.
    check("account, not character" in sec,
          "§3.4 places the record on the account (GDD-04 §5)")
    check("CREATE TABLE accounts" in schema,
          "schema.sql carries accounts")
    check("achievements" in schema and "character_id" in schema,
          "schema.sql achievements table exists to contrast against")
    check("keyed by `character_id`" in sec,
          "§3.4 records the achievements-table keying discrepancy")

    # 4. All 8 landmark ids from the blockout are in the set.
    lm_ids = [lm["id"] for lm in blockout["landmarks"]]
    check(len(lm_ids) == 8, "blockout carries exactly 8 landmarks",
          f"n={len(lm_ids)}")
    missing_lm = [i for i in lm_ids if i not in sec]
    check(not missing_lm, "all 8 landmark ids are in the §3.4 set",
          f"missing={missing_lm}")

    # 5. Landmark zones: the six box-verified ones match the boxes.
    boxes = blockout["zone_boxes_m"]
    bad_zone = []
    for lm in blockout["landmarks"]:
        x, z = lm["at"]
        inside = [zid for zid, b in boxes.items()
                  if b["x0"] <= x <= b["x1"] and b["z0"] <= z <= b["z1"]]
        if not inside:
            continue
        m = re.search(r"\| `" + re.escape(lm["id"]) + r"` \|[^|]*\| `([^`]+)`",
                      sec)
        if not m or m.group(1) != inside[0]:
            bad_zone.append((lm["id"], inside, m.group(1) if m else None))
    check(not bad_zone,
          "box-verified landmark zones match zone_boxes_m",
          f"bad={bad_zone}")
    check(sec.count("Assigned by description") == 2,
          "exactly two landmark zones are assigned by description",
          "Clock Tower + Bridge Approach fall outside every box")

    # 6. Landmark names match GDD-02 §4.
    for name in ["The Clock Tower", "Rupsha Bridge approach",
                 "Launch Terminal", "Central Park pond & banyan tree",
                 "Boro Bazar market hall",
                 "Uptown rooftop restaurant tower",
                 "Railway station clock frontage", "The old water tank"]:
        check(name in gdd02, f"GDD-02 §4 names {name!r}")

    # 7. Bus routes: no named route exists in the sources; the single
    #    decided-here route is the described terminal loop.
    bus = next(v for v in vehicles["vehicles"] if v["id"] == "bus")
    check("terminal" in bus["notes"] and "district edge" in bus["notes"],
          "vehicles.json bus note describes the terminal loop only")
    check("fixed terminal loops" in gdd07,
          "GDD-07 §1 names no route id, only fixed terminal loops")
    check("bus_route_terminal_loop" in sec,
          "§3.4 defines the single decided-here route id")
    check("Decided here" in sec,
          "the route id is labelled as this unit's decision")

    # 8. Eligibility: unfound only, first in set order, deterministic.
    check("no `discovery_progress` row" in sec,
          "eligibility is unfound-only")
    check("first in set order" in sec,
          "offered discoverable is the first unfound in set order")
    check("no random pick" in sec,
          "no randomness in the pick (GDD-15 §12.6 rule 6)")

    # 9. Photograph-the-district stays ungeneratable, honestly.
    check("Photographing has no record" in sec,
          "§3.4 excludes photographing — no photo record exists")
    check("photograph the district" in sec,
          "§3.4 names the uncovered §3 example")

    # 10. Reward pattern verbatim from missions.json.
    check(pattern == "500 NCr each + Explorer progress",
          "discovery reward pattern is 500 NCr each + Explorer progress",
          f"pattern={pattern!r}")
    check("500 NCr each + Explorer progress" in sec,
          "§3.4 quotes the pattern verbatim")

    # 11. §3.1 discovery row no longer says Ungeneratable.
    s31 = gdd04.split("### 3.1 ")[1].split("### 3.2 ")[0]
    row = re.search(r"\| Discovery \(`discovery`\) \| At least one "
                    r"discoverable.*?\n", s31)
    check(row is not None and "Ungeneratable" not in row.group(0),
          "§3.1 discovery row no longer Ungeneratable")
    check(row is not None and "§3.4" in row.group(0),
          "§3.1 row points at the §3.4 record")

    # 12. No sim table or schema change is claimed.
    check("adds no sim table, no schema change" in sec,
          "§3.4 is design only — no table or schema change applied")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed; "
          f"{len(failed)} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
