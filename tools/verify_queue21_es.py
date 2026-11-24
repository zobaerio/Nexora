"""Verify Queue 21 Unit ES — Construction Worker Day-Wage Pay
(GDD-03 §2; EL follow-up).

Checks the day-wage model against its sources: tools/sim/labour.py
(the worked-days count, the day-wage due, and the single routing
helper), tools/sim/engine.py (both settlement payment points call
the helper; the treasury path is untouched), GDD-03 §2 + GDD-04
§3.3 (the decision is recorded, and the EL honest limit is closed),
and the tests (test_broken_tool_wages.py TestDayWagePay +
TestDayWageSettlement). Prints one line per check and a summary;
exits 0 only when every check passes.
Run from the repo root: python3 tools/verify_queue21_es.py
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
    gdd03 = (ROOT / "docs" / "GDD-03-ECONOMY-AND-PROFESSIONS.md").read_text()
    gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md").read_text()
    labour_src = (ROOT / "tools" / "sim" / "labour.py").read_text()
    engine_src = (ROOT / "tools" / "sim" / "engine.py").read_text()
    gov_src = (ROOT / "tools" / "sim" / "government.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_broken_tool_wages.py").read_text()

    # 1. The day-wage helpers exist in labour.py.
    check('DAY_WAGE_PROFESSIONS = ("construction_worker",)' in labour_src,
          "labour.py names construction_worker the day-wage profession")
    check("def worked_days(" in labour_src,
          "labour.py defines worked_days")
    check("def day_wage_due(" in labour_src,
          "labour.py defines day_wage_due")
    check("def wage_due_for(" in labour_src,
          "labour.py defines wage_due_for")
    worked = labour_src.split("def worked_days(")[1].split("def ")[0]
    check('b.get("activity") == "work"' in worked,
          "worked_days counts work blocks")
    check('not b.get("broken_tool")' in worked,
          "worked_days counts only unbent work blocks")
    due = labour_src.split("def day_wage_due(")[1].split("def ")[0]
    check("DAYS_PER_MONTH" in due,
          "day_wage_due divides by DAYS_PER_MONTH (30)")
    route = labour_src.split("def wage_due_for(")[1].split("def ")[0]
    check("DAY_WAGE_PROFESSIONS" in route
          and "day_wage_due(" in route,
          "wage_due_for routes day-wage professions to day_wage_due")
    check("broken_tool_wage_dock(" in route,
          "wage_due_for routes monthly professions via the dock")

    # 2. The settlement consults the helper at both payment points.
    pay_biz = engine_src.split("def _pay_business_wages(")[1] \
        .split("def _pay_government_wages(")[0]
    check("labour_mod.wage_due_for(" in pay_biz,
          "engine._pay_business_wages calls wage_due_for")
    check("broken_tool_wage_dock(" not in pay_biz,
          "the business path no longer calls the dock directly")
    settle = engine_src.split("def _settle_month(")[1]
    check("labour_mod.wage_due_for(" in settle,
          "the SYS-EMPLOYERS branch calls wage_due_for")
    check("wage_due_for" not in gov_src,
          "the treasury path is untouched (no day-wage call site)")

    # 3. The decision is recorded in both docs.
    check("Update (Unit ES" in gdd03,
          "GDD-03 §2 carries the ES update")
    check("resolved by the pay model, not by an exception" in gdd03,
          "GDD-03 §2 states the dock resolution")
    check("is NOT implemented in the sim" not in gdd03,
          "GDD-03 §2 no longer says day-wage pay is unimplemented")
    check("Update (Unit ES" in gdd04,
          "GDD-04 §3.3 carries the ES update")
    check("the EL dock question is resolved for that profession alone"
          in gdd04,
          "GDD-04 §3.3 states the dock question is resolved")

    # 4. The tests cover the model and the EL proof moved.
    check("class TestDayWagePay(" in tests,
          "tests define TestDayWagePay")
    check("class TestDayWageSettlement(" in tests,
          "tests define TestDayWageSettlement")
    check("def _work_day(" in tests,
          "tests define the _work_day helper")
    check('profession_id="chef"' in tests,
          "the EL settlement proof now uses a monthly profession")
    check('profession_id="construction_worker"' in tests,
          "the ES settlement tests hire construction workers")

    # 5. Live behaviour: worked days and the due, on a real store.
    from tools.sim import labour as labour_mod
    from tools.sim.tests.common import make_person, make_store
    store = make_store()
    cid = make_person(store, age=30, first="Builder")

    def _work_day(day, bent=False):
        blocks = [{"start": 0, "end": 480, "activity": "home",
                   "location": "home", "zone": "d1_midtown"},
                  {"start": 480, "end": 1020, "activity": "work",
                   "location": "d1_industry", "zone": "d1_industry",
                   "broken_tool": bent},
                  {"start": 1020, "end": 1440, "activity": "home",
                   "location": "home", "zone": "d1_midtown"}]
        store.execute(
            "INSERT INTO instantiated_schedules"
            " (character_id, day_index, blocks_json)"
            " VALUES (?, ?, ?)", (cid, day, json.dumps(blocks)))

    for day in range(120, 130):
        _work_day(day)
    _work_day(130, bent=True)
    check(labour_mod.worked_days(store, cid, 5) == 10,
          "worked_days counts 10 unbent days, not the bent day",
          "10")
    check(labour_mod.day_wage_due(store, cid, 5, 9000) == 3000,
          "day_wage_due is 10 × 9000/30", "3000")
    check(labour_mod.wage_due_for(
        store, cid, "construction_worker", 5, 9000) == 3000,
          "wage_due_for pays the day wage for construction workers")
    check(labour_mod.wage_due_for(store, cid, "chef", 5, 9000) == 9000,
          "wage_due_for pays the full monthly wage for a chef")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    if failed:
        print("FAILED:")
        for _, label, detail in failed:
            print(f"  - {label}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
