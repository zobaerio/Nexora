"""Verify Queue 20 Unit EH — Tool & Furniture Repair (GDD-04 §3.3,
Unit DQ follow-up).

Checks the repair functions against their sources:
tools/sim/lost_items.py (repair_tool / repair_furniture),
data/prices.json (no repair key — the DQ price rule), GDD-04 §3.3
(the DQ design + the EH implementation note), and the tests
(test_lost_items.py TestRepair). Prints one line per check and a
summary; exits 0 only when every check passes.
Run from the repo root: python3 tools/verify_queue20_eh.py
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
    lost_items = (ROOT / "tools" / "sim" / "lost_items.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_lost_items.py").read_text()
    prices = json.loads((ROOT / "data" / "prices.json").read_text())

    # 1. The repair functions exist and restore to 90.
    check("def repair_tool(" in lost_items,
          "lost_items.py defines repair_tool")
    check("def repair_furniture(" in lost_items,
          "lost_items.py defines repair_furniture")
    check("def _repair(" in lost_items,
          "lost_items.py defines the shared repair helper")
    repair = lost_items.split("def _repair(")[1] \
        .split("# GDD-10")[0]
    check("RESTORED_CONDITION" in repair,
          "the repair restores to RESTORED_CONDITION (90)")
    check(">= RESTORED_CONDITION" in repair,
          "a row already at 90+ is refused (repair would lower it)")
    check('row["item_type"] != item_type' in repair,
          "a row of the other type is refused")
    check("store.transfer(" not in repair,
          "the repair writes no ledger row (no charge, DQ)")

    # 2. No repair price is invented.
    check("repair" not in prices,
          "prices.json carries no repair key (DQ price rule)")

    # 3. The design records the repair.
    check("**Implementation (Unit EH" in gdd04,
          "GDD-04 §3.3 carries the EH implementation note")
    check("RESTORED_CONDITION" in gdd04.split(
        "**Implementation (Unit EH")[1].split(
            "**Implementation (Unit EI")[0],
          "the EH note names the restored level (90, never 100)")

    # 4. The tests prove the repair.
    check("class TestRepair" in tests,
          "test_lost_items.py has the repair tests")
    for name in ("test_repair_tool_restores_a_worn_tool_to_90",
                 "test_repair_tool_restores_a_broken_tool_to_90",
                 "test_repair_furniture_restores_a_worn_piece_to_90",
                 "test_repair_refuses_a_row_already_at_90_or_above",
                 "test_repair_refuses_an_unknown_row",
                 "test_repair_refuses_the_other_type",
                 "test_repair_keeps_the_other_state_keys"):
        check(name in tests, f"test_lost_items.py has {name}")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
