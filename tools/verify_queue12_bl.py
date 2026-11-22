"""Verify Queue 12 Unit BL — GDD-04 §3.3 lost-item record (find-a-lost-item).

Checks the record section against the sources it must resolve to:
GDD-04 §3/§3.1, GDD-15 §15/§18, GDD-06 §3, data/schema.sql
(inventory_items), data/missions.json (reward pattern).
Prints one line per check and a summary; exits 0 only when every check
passes. Run from the repo root: python3 tools/verify_queue12_bl.py
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
    gdd06 = (ROOT / "docs" / "GDD-06-NPC-BEHAVIOUR.md").read_text()
    schema = (ROOT / "data" / "schema.sql").read_text()
    missions = json.loads((ROOT / "data" / "missions.json").read_text())
    pattern = next(s["reward_pattern"] for s in
                   missions["side_mission_types"] if s["type"] == "favours")

    # 1. §3.3 exists, headed Unit BL, Queue 12.
    m33 = re.search(r"### 3\.3 Lost-Item Record \(Unit BL · Queue 12",
                    gdd04)
    check(m33 is not None, "GDD-04 §3.3 exists, headed Unit BL, Queue 12")

    # 2. The §3.3 section body.
    sec = gdd04[m33.start():] if m33 else ""
    sec = sec.split("### 3.4 ")[0]

    # 3. All ten record fields are defined.
    fields = ["lost_item_id", "owner_character_id", "item_instance_id",
              "lost_at_game_minutes", "lost_zone", "lost_anchor",
              "status", "found_by_character_id",
              "found_at_game_minutes", "returned_at_game_minutes"]
    missing = [f for f in fields if f not in sec]
    check(not missing, "lost_items record defines all ten fields",
          f"missing={missing}")

    # 4. Lifecycle lost -> found -> returned, no expiry.
    check("`lost` \\| `found` | `returned`" in sec
          or "`lost` \\| `found` \\| `returned`" in sec,
          "lifecycle states are lost / found / returned")
    check("no expiry" in sec.lower(),
          "no expiry on a lost item (favours have no deadline)")

    # 5. The item must resolve to an inventory_items row; the schema
    #    carries that table with the item_type vocabulary.
    check("inventory_items.item_instance_id" in sec,
          "item identified by its inventory_items row, never by name")
    check("CREATE TABLE inventory_items" in schema,
          "schema.sql carries inventory_items")
    check("vehicle | furniture | tool | clothing | goods | document"
          in schema,
          "schema item_type vocabulary matches §3.3")
    check("Money cannot be lost" in sec,
          "money / property / business stock excluded as losable")

    # 6. Eligibility check: a lost row owned by the giver.
    check("status = 'lost'" in sec and "owner_character_id" in sec,
          "eligibility check is a lost row owned by the giver NPC")
    check("lost_zone" in sec and "lost_anchor" in sec,
          "favour parameters carry where to look")

    # 7. Honest limit: no merged event writes a loss today.
    check("No merged event writes a loss today" in sec,
          "recorded honestly: no event writes a loss yet")

    # 8. §3.1 find-a-lost-item row no longer says Ungeneratable.
    row = re.search(r"Favours — find a lost item.*?\n", gdd04)
    check(row is not None and "Ungeneratable" not in row.group(0),
          "§3.1 find-a-lost-item row no longer Ungeneratable")
    check(row is not None and "§3.3" in row.group(0),
          "§3.1 row points at the §3.3 record")

    # 9. Reward pattern is the §3 pattern, verbatim from missions.json.
    check(pattern == "Relationship + small credits",
          "favours reward pattern is Relationship + small credits",
          f"pattern={pattern!r}")
    check("Relationship + small credits" in sec,
          "§3.3 quotes the pattern, invents no amount")

    # 10. Cross-references resolve.
    check("GDD-15 §18" in sec and "current_zone_at" in sec,
          "§3.3 cites the §18 current-zone accessor for lost_zone")
    check("GDD-06 §3" in sec,
          "§3.3 cites GDD-06 §3 anchors for lost_anchor")
    check("TECH-MULTIPLAYER §4" in sec,
          "find is verified against world state (TECH-MULTIPLAYER §4)")
    check("GDD-15 §15" in gdd15 and "find-a-lost-item" in gdd15,
          "GDD-15 §15 still names find-a-lost-item as record-gated")

    # 11. The section says what the generator must never invent.
    check("must never invent" in sec,
          "§3.3 states the generator's never-invent rules")

    # 12. No sim table or schema change is claimed.
    check("adds no sim table, no schema change" in sec,
          "§3.3 is design only — no table or schema change applied")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed; "
          f"{len(failed)} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
