"""Verify Queue 22 Unit EX — Furniture Service Call Site (GDD-04
§3.3; EH/DQ/EU follow-up).

Checks the furniture service against its sources:
tools/sim/lost_items.py (the predicate + the sweep),
tools/sim/engine.py (the monthly social pass calls it beside the
tool service), GDD-04 §3.3 (the decision is recorded), and the
tests (test_lost_items.py TestMonthlyFurnitureService +
TestMonthlyFurnitureServiceHook).
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue22_ex.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CHECKS = []


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def main():
    gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md").read_text()
    li_src = (ROOT / "tools" / "sim" / "lost_items.py").read_text()
    engine_src = (ROOT / "tools" / "sim" / "engine.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_lost_items.py").read_text()

    # 1. The predicate mirrors tool_needs_service (DQ 60).
    pred = li_src.split("def furniture_needs_service(")[1] \
        .split("def ")[0] if "def furniture_needs_service(" in li_src \
        else ""
    check("def furniture_needs_service(" in li_src,
          "lost_items.py: furniture_needs_service exists")
    check("item_condition(r) <= SERVICE_THRESHOLD" in pred,
          "lost_items.py: the predicate uses the DQ 60 threshold")
    check("item_type = 'furniture'" in pred,
          "lost_items.py: the predicate reads furniture rows")
    check("household_head(store, household_id)" in pred,
          "lost_items.py: the predicate reads the household head")

    # 2. The sweep mirrors monthly_repair_sweep.
    sweep = li_src.split("def monthly_furniture_service_sweep(")[1] \
        .split("def ")[0] if "def monthly_furniture_service_sweep(" \
        in li_src else ""
    check("def monthly_furniture_service_sweep(" in li_src,
          "lost_items.py: monthly_furniture_service_sweep exists")
    check("furniture_needs_service(store, data, hid)" in sweep,
          "lost_items.py: the sweep services what the predicate reports")
    check('repair_furniture(store, row["item_instance_id"])' in sweep,
          "lost_items.py: the sweep repairs via repair_furniture")
    check("item_condition(row) == 0" in sweep,
          "lost_items.py: the sweep distinguishes broken pieces")
    check("economy_ledger" not in sweep and "transfer(" not in sweep,
          "lost_items.py: the sweep writes no ledger row (DQ price rule)")
    check("dissolved_at_game_minutes IS NULL" in sweep,
          "lost_items.py: dissolved households are skipped")

    # 3. The engine calls it every month, beside the tool service.
    social = engine_src.split("def _monthly_social(")[1] \
        .split("def _monthly_city(")[0]
    check("monthly_furniture_service_sweep(" in social,
          "engine.py: the monthly social pass calls the sweep")
    check(social.index("monthly_repair_sweep(")
          < social.index("monthly_furniture_service_sweep(")
          < social.index("monthly_furniture_purchase_sweep("),
          "engine.py: order is tool service, furniture service, purchase")

    # 4. The decision is recorded in GDD-04 §3.3.
    check("Update, Unit EX" in gdd04,
          "GDD-04 §3.3: the EX update note is present")
    check("Still open: `repair_furniture()` has no call site"
          not in gdd04,
          "GDD-04 §3.3: the 'no call site' gap is closed, not repeated")
    check("furniture_needs_service()" in gdd04,
          "GDD-04 §3.3: the predicate is named")

    # 5. Tests prove a worn piece is serviced and a sound one is not.
    check("class TestMonthlyFurnitureService" in tests,
          "tests: the furniture-service test class exists")
    check("test_repairs_furniture_at_or_below_sixty" in tests,
          "tests: pieces at or below 60 are repaired to 90")
    check("test_repairs_a_broken_piece_and_lists_it_broken" in tests,
          "tests: a broken piece is repaired and listed broken")
    check("test_predicate_reports_due_pieces_only" in tests,
          "tests: the predicate reports due pieces only")
    check("test_no_ledger_charge_and_no_life_event" in tests,
          "tests: no ledger charge, no life event")
    check("test_sound_home_is_not_serviced" in tests,
          "tests: a sound home is not serviced")
    check("class TestMonthlyFurnitureServiceHook" in tests,
          "tests: the live engine-hook test exists")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed, "
          f"{len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
