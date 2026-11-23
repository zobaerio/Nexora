"""Verify Queue 18 Unit DP — Lost-Item Hand-Back Journey (GDD-04
§3.3; DF/DJ follow-up).

Checks the hand-back design against the sources it builds on:
GDD-04 §3.1/§3.3 (the favour, the lifecycle, the eligibility check),
tools/sim/lost_items.py (find/return/predicate/record_loss),
tools/sim/households.py (move_household), tools/sim/lifecycle.py
(die() / the inheritance cascade), data/dialogue-lines.json (the
complete node), and the building data (no civic desk exists).
Design only — no sim code changes. Prints one line per check and
a summary; exits 0 only when every check passes. Run from the repo
root: python3 tools/verify_queue18_dp.py
"""
import json
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
    lost_items = (ROOT / "tools" / "sim" / "lost_items.py").read_text()
    households = (ROOT / "tools" / "sim" / "households.py").read_text()
    lifecycle = (ROOT / "tools" / "sim" / "lifecycle.py").read_text()
    dlg = json.loads((ROOT / "data" / "dialogue-lines.json").read_text())
    b1 = json.loads(
        (ROOT / "data" / "buildings-district1.json").read_text())
    b2 = json.loads((ROOT / "data" / "city2-shibnagar.json").read_text())

    s33 = gdd04.split("**The lost-item hand-back (Unit DP")[1] \
        .split("### 3.4 Discovery")[0]

    # 1. The section exists with the design's decisions.
    check("**The lost-item hand-back (Unit DP" in gdd04,
          "GDD-04 §3.3 has the hand-back subsection")
    check("the finder carries the item to the owner" in s33.lower()
          or "The finder carries the item to the owner" in s33,
          "the design names the finder as the carrier")
    check("is **rejected** for three reasons" in s33,
          "the civic desk is considered and rejected with reasons")
    check("owner's CURRENT home" in s33,
          "the hand-back place is the owner's current home")
    check("lost_anchor" in s33 and "FIND place" in s33,
          "the lost_anchor is named the find place, not the return place")
    check("orphaned favour" in s33,
          "the deceased-owner state is named (orphaned favour)")
    check("No new field is added" in s33,
          "the design adds no new field to any row")

    # 2. The DF wiring the design builds on.
    check("def find_lost_item(" in lost_items,
          "lost_items.py implements find_lost_item")
    check("def return_lost_item(" in lost_items,
          "lost_items.py implements return_lost_item")
    check("def favour_objective_complete(" in lost_items,
          "lost_items.py provides the favour completion predicate")
    check("found_by_character_id" in lost_items,
          "the found row records who holds the item")
    check("AND status = 'lost'" in lost_items,
          "record_loss refuses only a standing lost row")
    record_loss_body = lost_items.split("def record_loss(")[1] \
        .split("# -- Queue 16 Unit DF")[0]
    check("found" not in record_loss_body,
          "record_loss has no found-row exclusion (the recorded edge)")

    # 3. The move re-routes, it does not strand.
    check("def move_household(" in households,
          "households.py implements move_household")
    check("move_house_loss" in households,
          "move_household still fires the E3 loss at the origin zone")
    check("for m in members(store, household_id)" in households,
          "move_household moves the whole household")

    # 4. Death moves money and property, not inventory.
    die = lifecycle.split("def die(")[1].split("def ")[0]
    check("inventory_items" not in die,
          "die() never touches inventory_items (the orphaned rule)")
    check("heirs_in_order" in die and "SYS-CITY" in die,
          "die() moves balance/property to heirs or the city")

    # 5. The complete node already exists; no new node is needed.
    all_nodes = [n["node_id"] for t in dlg["trees"].values()
                 for n in t.get("nodes", [])]
    topics = dlg.get("topics", {})
    topic_nodes = [n["node_id"] for t in topics.values()
                   for n in t.get("nodes", [])] if topics else []
    check("dlg_favour_complete_find_a_lost_item"
          in all_nodes + topic_nodes,
          "the favour complete node exists in dialogue-lines.json")
    check("dlg_favour_complete_find_a_lost_item" in gdd15,
          "GDD-15 §15.2 names the complete node")
    check("current_zone_at" in gdd15,
          "GDD-15 §18 provides the current-zone accessor (fallback)")

    # 6. No civic desk exists in any source.
    names = " ".join(
        str(b.get("name", "")) + " " + str(b.get("id", ""))
        for b in b1.get("buildings", []) + b2.get("buildings", []))
    check("lost" not in names.lower()
          and "lost-property" not in names.lower(),
          "no building in either city is a lost-property desk")

    # 7. The favour's only exit is abandon (§3.6).
    check("a favour fails only by abandon" in gdd04,
          "§3.6 states a favour fails only by abandon (the orphan exit)")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
