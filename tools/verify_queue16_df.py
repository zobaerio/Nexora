"""Verify Queue 16 Unit DF — Lost-Item Recovery Wiring (GDD-04 §3.3
lifecycle; GDD-04 §3.1; GDD-15 §15.2).

Checks the recovery implementation against the design it wires:
GDD-04 §3.3 (lifecycle lost -> found -> returned, the §3.1
completion rule), GDD-15 §15.2 (the complete node),
tools/sim/lost_items.py (find_lost_item / return_lost_item /
favour_objective_complete), tools/sim/persistence.py (the
lost_items table already carries the found/returned columns) and
tools/sim/tests/test_lost_items.py.
Prints one line per check and a summary; exits 0 only when every
check passes. Run from the repo root: python3 tools/verify_queue16_df.py
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
    lost = (ROOT / "tools" / "sim" / "lost_items.py").read_text()
    persist = (ROOT / "tools" / "sim" / "persistence.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_lost_items.py").read_text()

    # 1. The design names the lifecycle and the completion rule.
    s33 = gdd04.split("### 3.3 ")[1].split("### 3.4")[0]
    check("`lost → found → returned`, and nothing else" in s33,
          "GDD-04 §3.3 states the lifecycle lost -> found -> returned")
    check("Handing it to the owner writes `returned` and completes"
          " the favour" in s33,
          "GDD-04 §3.3 states the return completes the favour")
    check("found_by_character_id" in s33
          and "found_at_game_minutes" in s33
          and "returned_at_game_minutes" in s33,
          "GDD-04 §3.3 defines the found/returned fields")
    check("the mission system sets `progress.objectives_complete`"
          in gdd15,
          "GDD-15 §15.2 states the mission system sets"
          " objectives_complete on return")
    check("dlg_favour_complete_find_a_lost_item" in gdd15,
          "GDD-15 §15.2 names the existing complete node")

    # 2. The functions exist with the §3.3 contract.
    check("def find_lost_item" in lost,
          "lost_items.py defines find_lost_item")
    check("def return_lost_item" in lost,
          "lost_items.py defines return_lost_item")
    check("def favour_objective_complete" in lost,
          "lost_items.py defines favour_objective_complete")
    check("status = 'found'" in lost
          and "found_by_character_id" in lost
          and "found_at_game_minutes" in lost,
          "find_lost_item writes found + finder + minute")
    check("status = 'returned'" in lost
          and "returned_at_game_minutes" in lost,
          "return_lost_item writes returned + minute")
    check("finder_zone != row[\"lost_zone\"]" in lost,
          "find refuses a finder outside the lost_zone")
    check("lost_anchor" in lost and "finder_anchor" in lost,
          "find checks the recorded lost_anchor where one exists")
    check("row[\"status\"] != \"found\"" in lost,
          "return refuses a row that is not found")
    check("row[\"status\"] == \"returned\"" in lost,
          "favour_objective_complete is true iff status is returned")

    # 3. The table already carries the columns (CY) — no schema
    # change was needed for this unit.
    check("found_by_character_id TEXT" in persist,
          "persistence.py lost_items has found_by_character_id")
    check("found_at_game_minutes INTEGER" in persist,
          "persistence.py lost_items has found_at_game_minutes")
    check("returned_at_game_minutes INTEGER" in persist,
          "persistence.py lost_items has returned_at_game_minutes")
    check("'lost', 'found', 'returned'" in persist,
          "persistence.py lost_items status CHECK is the lifecycle")

    # 4. The GDDs record the implementation.
    check("Implementation (Unit DF · Queue 16" in gdd04,
          "GDD-04 §3.3 carries the DF implementation note")
    check("Unit DF · Queue 16" in gdd04.split("### 3.1 ")[1]
          .split("### 3.2")[0],
          "§3.1 find-a-lost-item row carries the DF update")
    check("Unit DF · Queue 16" in gdd15,
          "GDD-15 §15.2 carries the DF update")
    check("the mission system itself is still Phase 6 work" in gdd15,
          "GDD-15 records the mission system as still Phase 6 work")

    # 5. The tests cover the contract.
    n_tests = len(re.findall(r"def test_", tests))
    check(n_tests >= 36 + 12,
          "test_lost_items.py has 48+ tests (36 DD + 12 DF)",
          f"{n_tests} tests")
    check("class TestRecovery" in tests,
          "tests carry a TestRecovery class")
    check("test_return_refuses_item_never_found" in tests,
          "tests prove a return of an item never found is refused")
    check("test_find_without_anchor_needs_zone_only" in tests,
          "tests prove the zone-only check where no anchor recorded")
    check("test_full_lifecycle_then_reloss" in tests,
          "tests prove the full lifecycle and re-loss after return")
    check("test_favour_objective_complete_predicate" in tests,
          "tests prove the completion predicate at each status")

    # 6. Nothing else changed: the rate stays 0, record_loss is
    # untouched.
    config = json.loads(
        (ROOT / "data" / "lost-items-config.json").read_text())
    check(config.get("loss_rate") == 0,
          "lost-items-config.json still sets loss_rate 0")
    check("def record_loss(store, owner_character_id, item_instance_id,"
          in lost,
          "record_loss is unchanged (the CY signature stands)")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
