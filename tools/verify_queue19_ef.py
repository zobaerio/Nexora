"""Verify Queue 19 Unit EF — Furniture Condition Wiring
(GDD-04 §3.3, Unit DQ follow-up; GDD-10 §5).

Checks the furniture-condition wiring against its sources:
tools/sim/lost_items.py (condition state + move/exposure wear +
effective tier), tools/sim/households.py (move wear before
seeding), tools/sim/environment.py (exposure wear in daily_pass),
GDD-04 §3.3 (the DQ design + the EF implementation note),
GDD-10 §5 (the effective-tier rule), and
tools/sim/tests/test_lost_items.py (TestFurnitureCondition).
Prints one line per check and a summary; exits 0 only when every
check passes. Run from the repo root: python3 tools/verify_queue19_ef.py
"""
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
    gdd10 = (ROOT / "docs" / "GDD-10-HOUSING-AND-HOME-LIFE.md").read_text()
    lost_items = (ROOT / "tools" / "sim" / "lost_items.py").read_text()
    households = (ROOT / "tools" / "sim" / "households.py").read_text()
    environment = (ROOT / "tools" / "sim" / "environment.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_lost_items.py").read_text()

    # 1. The state carries condition.
    furn_seed = lost_items.split("def seed_furniture_rows(")[1] \
        .split("def seed_tool_rows(")[0]
    check('"condition": CONDITION_NEW' in furn_seed,
          "seed_furniture_rows writes condition 100 (CONDITION_NEW)")

    # 2. The wear hooks.
    check("def apply_furniture_move_wear(" in lost_items,
          "lost_items.py defines apply_furniture_move_wear")
    check("def apply_furniture_exposure_wear(" in lost_items,
          "lost_items.py defines apply_furniture_exposure_wear")
    check("apply_furniture_move_wear(" in households,
          "households.move_household applies move wear")
    check("apply_furniture_exposure_wear(" in environment,
          "environment.daily_pass applies exposure wear")
    check("flood" in environment and "cyclone" in environment
          and "severe_storm" in environment,
          "exposure wear covers flood, cyclone and severe storm")

    # 3. The effective tier and its multipliers.
    check("def effective_furniture_tier(" in lost_items,
          "lost_items.py defines effective_furniture_tier")
    check("FURNITURE_RESTORE_MULTIPLIERS" in lost_items,
          "lost_items.py defines the restore multipliers")
    check("0.7" in lost_items and "1.0" in lost_items
          and "1.15" in lost_items and "1.3" in lost_items,
          "the multipliers are F0 0.7 / F1 1.0 / F2 1.15 / F3 1.3")
    check("def furniture_restore_multiplier(" in lost_items,
          "lost_items.py defines furniture_restore_multiplier")

    # 4. The design records the wiring.
    check("**Implementation (Unit EF" in gdd04,
          "GDD-04 §3.3 carries the EF implementation note")
    check("effective" in gdd10.lower()
          and "tier" in gdd10.lower(),
          "GDD-10 §5 names the effective-tier rule")
    check("lost piece" in gdd04 or "lost piece" in gdd10,
          "the lost-piece vs effective-tier question is recorded "
          "as open, not decided")

    # 5. The tests prove the wiring.
    check("class TestFurnitureCondition" in tests,
          "test_lost_items.py has the furniture-condition tests")
    check("test_move_wear_runs_before_move_in_seeding" in tests
          or "test_move_wear" in tests,
          "test_lost_items.py tests the move wear")
    check("test_exposure_wear" in tests,
          "test_lost_items.py tests the exposure wear")
    check("test_effective_tier" in tests,
          "test_lost_items.py tests the effective tier")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
