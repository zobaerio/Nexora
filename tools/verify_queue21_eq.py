"""Verify Queue 21 Unit EQ — Effective-Tier Restore Multiplier
Wiring (GDD-10 §5/§6, EF follow-up).

Checks the wiring against its sources: tools/sim/needs.py (the
restore scaling in apply_activity), tools/sim/engine.py (the
daily pass passes the world data), tools/sim/lost_items.py (the
multiplier's docstring names its live consumer), GDD-10 §5/§6 +
GDD-04 §3.3 (the design notes record the wiring and its scope),
and the tests (test_needs.py TestFurnitureRestoreWiring). Prints
one line per check and a summary; exits 0 only when every check
passes.
Run from the repo root: python3 tools/verify_queue21_eq.py
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
    gdd10 = (ROOT / "docs" / "GDD-10-HOUSING-AND-HOME-LIFE.md").read_text()
    gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md").read_text()
    needs = (ROOT / "tools" / "sim" / "needs.py").read_text()
    engine = (ROOT / "tools" / "sim" / "engine.py").read_text()
    lost_items = (ROOT / "tools" / "sim" / "lost_items.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_needs.py").read_text()

    # 1. The needs engine scales the home restores by the tier.
    check("def apply_activity(store, character_id, activity, location,"
          " hours,\n                   game_minutes, meal=False, data=None):"
          in needs,
          "apply_activity takes the world data (data=None default)")
    check("furniture_restore_multiplier(" in needs,
          "apply_activity reads the furniture restore multiplier")
    check('activity in ("home", "sleep")' in needs,
          "the scaling applies to home/sleep blocks only")
    check('need in ("rest", "sleep")' in needs,
          "only the rest/sleep restores scale")
    check("delta > 0" in needs,
          "only positive deltas scale — drains stay unscaled")

    # 2. The engine passes the world data at every block boundary.
    check(engine.count("data=data") >= 3,
          "the engine passes data to every apply_activity call",
          f"{engine.count('data=data')} call sites")

    # 3. The multiplier names its live consumer.
    check("The live consumer is the needs" in lost_items,
          "furniture_restore_multiplier names needs.apply_activity "
          "as its live consumer")
    check("No live consumer" not in lost_items,
          "no docstring still claims the multiplier has no consumer")

    # 4. The design notes record the wiring and its scope.
    check("*(Update, Unit EQ" in gdd10,
          "GDD-10 §5 carries the EQ update")
    check("only positive rest/sleep deltas scale" in gdd10,
          "GDD-10 §5 records the scaling scope")
    check("no fallback rate is invented" in gdd10,
          "GDD-10 §5 records the None case (no invented rate)")
    check("*(Update, Unit EQ" in gdd04,
          "GDD-04 §3.3 carries the EQ update")

    # 5. The tests prove the wiring.
    check("class TestFurnitureRestoreWiring" in tests,
          "test_needs.py has the restore-wiring tests")
    for name in ("test_f1_home_restores_at_full_rate",
                 "test_broken_bed_drops_the_restore_rate",
                 "test_lost_bed_drops_the_restore_rate",
                 "test_repair_restores_the_rate",
                 "test_home_block_restores_scale_and_drains_do_not",
                 "test_sleep_block_drain_stays_unscaled",
                 "test_no_data_means_no_scaling",
                 "test_no_tier_means_no_scaling"):
        check(name in tests, f"test_needs.py has {name}")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
