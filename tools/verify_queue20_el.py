"""Verify Queue 20 Unit EL — Broken-Tool Wage Consequence (GDD-04
§3.3, GDD-03 §2; DQ/EE follow-up).

Checks the decision against its sources: tools/sim/labour.py
(broken_tool_days + broken_tool_wage_dock), tools/sim/engine.py
(the settlement consults the rule), GDD-03 §2 (the decided rule +
the day-wage honest limit), GDD-04 §3.3 (the EL implementation
note), and the tests (test_broken_tool_wages.py). Prints one line
per check and a summary; exits 0 only when every check passes.
Run from the repo root: python3 tools/verify_queue20_el.py
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
    gdd03 = (ROOT / "docs" / "GDD-03-ECONOMY-AND-PROFESSIONS.md").read_text()
    gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md").read_text()
    labour = (ROOT / "tools" / "sim" / "labour.py").read_text()
    engine = (ROOT / "tools" / "sim" / "engine.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_broken_tool_wages.py").read_text()

    # 1. The helpers exist and the dock is 0.
    check("def broken_tool_days(" in labour,
          "labour.py defines broken_tool_days")
    check("def broken_tool_wage_dock(" in labour,
          "labour.py defines broken_tool_wage_dock")
    dock = labour.split("def broken_tool_wage_dock(")[1] \
        .split("def unemployment_stats(")[0] \
        if "def unemployment_stats(" in labour else ""
    check(dock.strip().endswith("return 0") or "\n    return 0" in dock,
          "the dock returns 0 (the no-dock rule)")
    check("DAYS_PER_MONTH = 30" in labour,
          "the month mapping is pinned (30 days)")
    check("broken_tool" in labour.split(
        "def broken_tool_days(")[1].split("def broken_tool_wage_dock(")[0],
        "broken_tool_days reads the scheduler's broken_tool flag")

    # 2. The settlement consults the rule at the point of payment.
    check("broken_tool_wage_dock(" in engine,
          "engine.py consults broken_tool_wage_dock")
    check(engine.count("broken_tool_wage_dock(") >= 2,
          "both engine wage paths consult it (business + "
          "SYS-EMPLOYERS)",
          f"found {engine.count('broken_tool_wage_dock(')} calls")

    # 3. The decision is recorded, with its reasons and its limit.
    check("**Broken-tool wage rule (Unit EL" in gdd03,
          "GDD-03 §2 carries the decided no-dock rule")
    check("day-wage" in gdd03.split("**Broken-tool wage rule")[1]
          .split("## 3.")[0],
          "GDD-03 records the day-wage honest limit")
    check("**Implementation (Unit EL" in gdd04,
          "GDD-04 §3.3 carries the EL implementation note")
    check("DECIDED" in gdd04.split("**Implementation (Unit EL")[1]
          .split("*End of GDD-04")[0],
          "the EL note states the decision (no-dock stands)")

    # 4. The tests prove the wages for a broken-tool day.
    for name in ("test_counts_only_days_with_a_bent_block",
                 "test_month_boundaries_are_exact",
                 "test_the_dock_is_zero_with_bent_days",
                 "test_business_wages_pay_in_full_after_a_bent_day"):
        check(name in tests, f"test_broken_tool_wages.py has {name}")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
