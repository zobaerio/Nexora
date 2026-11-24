"""Verify Queue 21 Unit ER — Foreclosure-to-Repurchase Deed
Lifecycle (GDD-04 §3.3, GDD-10 §8; EN follow-up).

Checks the lifecycle against its sources: tools/sim/lost_items.py
(the surrender helper), tools/sim/banking.py (the foreclosure
calls it), GDD-04 §3.3 + GDD-10 §8 (the decision is recorded),
and the tests (test_lost_items.py TestDeedLifecycle). Prints one
line per check and a summary; exits 0 only when every check
passes.
Run from the repo root: python3 tools/verify_queue21_er.py
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
    banking = (ROOT / "tools" / "sim" / "banking.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_lost_items.py").read_text()

    # 1. The surrender helper exists and follows the paper rule.
    check("def surrender_property_deed(" in lost_items,
          "lost_items.py defines surrender_property_deed")
    helper = lost_items.split("def surrender_property_deed(")[1] \
        .split("def ")[0]
    check("item_ref = 'property_deed'" in helper,
          "the helper surrenders the property deed only")
    check('_item_is_away(' in helper,
          "the helper skips a deed that is lost/found")
    check("DELETE FROM inventory_items" in helper,
          "the surrender deletes the held deed row")
    check('state.get("property_id")' in helper,
          "the helper matches the deed by its property id")

    # 2. The foreclosure calls it.
    check("surrender_property_deed(" in banking,
          "banking._foreclose calls surrender_property_deed")
    foreclose = banking.split("def _foreclose(")[1] \
        .split("def share_price(")[0]
    check("surrender_property_deed(store, borrower, pid)" in foreclose,
          "the foreclosure surrenders the borrower's deed for the "
          "foreclosed property")

    # 3. The decision is recorded in both docs.
    check("*(Update, Unit ER" in gdd10,
          "GDD-10 §8 carries the ER update")
    check("the paper follows the right" in gdd10,
          "GDD-10 §8 states the decision (paper follows the right)")
    check("remains the deed of record" in gdd10,
          "GDD-10 §8 records the lost-deed exception")
    check("Open edge, recorded" not in gdd10.split(
        "The purchase writes a property deed")[1].split(
        "Becoming a landlord")[0],
          "GDD-10 §8 no longer lists the lifecycle as an open edge")
    check("*(Update, Unit ER" in gdd04,
          "GDD-04 §3.3 carries the ER update")
    check("refused by the helper's duplicate guard, so the old deed"
          " row stands" not in gdd04,
          "GDD-04 §3.3 no longer states the old open edge")

    # 4. The tests prove both cases.
    check("class TestDeedLifecycle" in tests,
          "test_lost_items.py has the deed-lifecycle tests")
    for name in ("test_foreclosure_surrenders_the_held_deed",
                 "test_repurchase_after_foreclosure_seeds_a_fresh_deed",
                 "test_foreclosure_leaves_a_lost_deed",
                 "test_foreclosure_without_a_deed_is_a_noop_for_the_paper",
                 "test_surrender_returns_the_id_then_none"):
        check(name in tests, f"test_lost_items.py has {name}")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
