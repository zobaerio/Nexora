"""Verify Queue 21 Unit EU — Repair Call Sites (GDD-04 §3.3; EH
follow-up).

Checks the monthly tool service against its sources:
tools/sim/lost_items.py (the sweep + the predicate it consumes),
tools/sim/engine.py (the monthly social pass calls it), GDD-04
§3.3 (the decision is recorded), and the tests
(test_lost_items.py TestMonthlyRepairSweep + TestMonthlyRepairHook).
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue21_eu.py
"""
import json
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

    # 1. The sweep exists and follows the DQ service rule.
    check("def monthly_repair_sweep(" in li_src,
          "lost_items.py defines monthly_repair_sweep")
    sweep = li_src.split("def monthly_repair_sweep(")[1].split("def ")[0]
    check("tool_needs_service(store, data, cid)" in sweep,
          "the sweep services what tool_needs_service reports")
    check('repair_tool(store, row["item_instance_id"])' in sweep,
          "the sweep repairs via repair_tool")
    check("item_condition(row) == 0" in sweep,
          "the sweep distinguishes broken tools (condition 0)")
    check("is_system = 0" in sweep and "died_at_game_minutes IS NULL"
          in sweep,
          "the sweep covers living characters only")
    check("economy_ledger" not in sweep and "transfer(" not in sweep,
          "the sweep writes no ledger row (DQ price rule)")

    # 2. The engine calls it every month.
    social = engine_src.split("def _monthly_social(")[1] \
        .split("def _monthly_city(")[0]
    check("lost_items_mod.monthly_repair_sweep(" in social,
          "the monthly social pass calls monthly_repair_sweep")
    check("repair_furniture(" not in engine_src,
          "repair_furniture has no engine call site (recorded gap)")

    # 3. The decision is recorded.
    check("Update (Unit EU" in gdd04,
          "GDD-04 §3.3 carries the EU update")
    check("repair_furniture()` has no call site" in gdd04,
          "GDD-04 §3.3 records the furniture-repair gap honestly")

    # 4. The tests cover the sweep and the hook.
    check("class TestMonthlyRepairSweep(" in tests,
          "tests define TestMonthlyRepairSweep")
    check("class TestMonthlyRepairHook(" in tests,
          "tests define TestMonthlyRepairHook")
    for name in ("test_repairs_tools_at_or_below_sixty",
                 "test_repairs_a_broken_tool_and_lists_it_broken",
                 "test_repairs_every_due_tool_for_every_character",
                 "test_no_ledger_charge",
                 "test_ignores_tools_of_another_profession",
                 "test_dead_characters_are_not_serviced",
                 "test_sweep_is_a_noop_with_no_tools",
                 "test_monthly_social_repairs_a_broken_tool"):
        check(f"def {name}(" in tests, f"tests define {name}")

    # 5. Live behaviour: a worn and a broken tool, on a real store.
    from tools.sim import lost_items as li
    from tools.sim.tests.common import (data, make_person, make_store)
    store = make_store()
    worker = make_person(store, age=30, first="Worker")
    store.insert("employments", employment_id="EM-VERIFY-EU",
                 character_id=worker,
                 profession_id="construction_worker",
                 tier=1, wage_per_month=10000,
                 started_at_game_minutes=480,
                 ended_at_game_minutes=None)
    made = li.seed_tool_rows(store, data(), worker,
                             "construction_worker", 480)

    def _set(iid, value):
        row = store.row("SELECT state FROM inventory_items"
                        " WHERE item_instance_id = ?", (iid,))
        state = json.loads(row["state"])
        state["condition"] = value
        store.execute("UPDATE inventory_items SET state = ?"
                      " WHERE item_instance_id = ?",
                      (json.dumps(state), iid))

    def _cond(iid):
        row = store.row("SELECT state FROM inventory_items"
                        " WHERE item_instance_id = ?", (iid,))
        return json.loads(row["state"])["condition"]

    _set(made[0], 0)
    _set(made[1], 60)
    _set(made[2], 61)
    out = li.monthly_repair_sweep(store, data(), 480)
    check(set(out["repaired"]) == {made[0], made[1]},
          "the sweep repaired the broken and the 60 tool", "2")
    check(out["broken"] == [made[0]],
          "the sweep listed the broken tool", "1")
    check(_cond(made[0]) == 90 and _cond(made[1]) == 90
          and _cond(made[2]) == 61,
          "conditions are 90 / 90 / 61 after the sweep")
    check(store.row("SELECT COUNT(*) AS n FROM economy_ledger")["n"] == 0,
          "no ledger row was written")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    if failed:
        print("FAILED:")
        for _, label, detail in failed:
            print(f"  - {label}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
