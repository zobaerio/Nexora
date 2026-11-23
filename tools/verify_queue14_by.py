"""Verify Queue 14 Unit BY — GDD-04 §3.5 photograph record design
(the BM §3.4 gap: photograph-the-district stayed ungeneratable because
no photo record existed).

Checks the design against the sources it must resolve to: GDD-04 §2
(mission 1.4 photo-mode unlock), §3.1/§3.4 (discovery set + eligibility),
GDD-15 §15.2/§18 (discovery nodes, current-zone accessor), data/schema.sql
(accounts), data/missions.json (discovery side type).
Prints one line per check and a summary; exits 0 only when every check
passes. Run from the repo root: python3 tools/verify_queue14_by.py
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
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    schema = (ROOT / "data" / "schema.sql").read_text()
    missions = json.loads((ROOT / "data" / "missions.json").read_text())

    # 1. The section exists, headed Unit BY, Queue 14.
    m = re.search(r"### 3\.5 Photograph Record \(Unit BY · Queue 14",
                  gdd04)
    check(m is not None, "GDD-04 §3.5 exists, headed Unit BY, Queue 14")
    sec = gdd04[m.start():] if m else ""
    sec = sec.split("*End of GDD-04 §3.5")[0]

    # 2. The record: table, fields, account keying.
    check("`photographs`" in sec, "§3.5 names the photographs store")
    for field in ("photograph_id", "account_id", "character_id",
                  "discoverable_id", "taken_at_game_minutes",
                  "taken_in_zone"):
        check(f"`{field}`" in sec, f"§3.5 defines field {field}")
    check("PRIMARY KEY (account_id, discoverable_id)" in sec
          or "PK `(account_id, discoverable_id)`" in sec,
          "§3.5 keys photographs by account + discoverable")
    check("photographs" not in schema,
          "schema.sql has no photographs table yet (Phase 6/9 record)")

    # 3. The gate is sourced: mission 1.4 unlocks photo mode.
    check("1.4" in sec and "photo mode" in sec,
          "§3.5 gates photographs on the mission 1.4 photo-mode unlock")
    check("photo mode" in gdd04.split("1.4 | The River at Dusk")[1]
          .split("\n")[0] if "1.4 | The River at Dusk" in gdd04 else False,
          "GDD-04 §2 really lists photo mode as the 1.4 unlock")

    # 4. Two rows, one transaction; landmarks only.
    check("two" in sec.lower() and "one transaction" in sec,
          "§3.5 writes photographs + discovery_progress in one transaction")
    check("bus route cannot be photographed" in sec,
          "§3.5 excludes the bus route (ridden, not photographed)")
    check("landmark" in sec and "District 2" in sec,
          "§3.5 covers D2 landmarks when they join the set")

    # 5. No new node needed; eligibility unchanged.
    check("No new dialogue node" in sec,
          "§3.5 states no new dialogue node is authored")
    check("eligibility is unchanged" in sec,
          "§3.5 leaves the discovery eligibility rule unchanged")

    # 6. Honest limits: no image bytes, no portraits, no price.
    check("no image bytes" in sec,
          "§3.5 states the row records the act, not the image")
    check("Photographing a person is not covered" in sec,
          "§3.5 excludes photographing people")
    check("charges nothing" in sec,
          "§3.5 charges nothing for a photograph (no invented price)")

    # 7. The stale notes are retired.
    check(sec.count("stays ungeneratable") == 1
          and '"photograph stays ungeneratable" note' in sec,
          "§3.5 mentions ungeneratable only to retire the old note")
    check("retired by this section" in sec,
          "§3.5 retires the §3.4 / §15.2 ungeneratable notes")
    check("Photograph-the-district stays ungeneratable" not in gdd04,
          "GDD-04 carries no ungeneratable photograph note any more")
    check("Photograph-the-district stays ungeneratable" not in gdd15,
          "GDD-15 §15.2 carries no ungeneratable photograph note any more")
    check("is generatable" in gdd15,
          "GDD-15 §15.2 now states photograph-the-district is generatable")

    # 8. missions.json already lists photograph as a discovery example.
    side = missions.get("side_mission_types", [])
    disc = [s for s in side if s.get("type") == "discovery"]
    check(len(disc) == 1 and "photograph the district"
          in disc[0].get("examples", ""),
          "missions.json discovery side type lists photograph the district")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
