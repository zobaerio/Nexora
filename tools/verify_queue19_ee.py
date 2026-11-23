"""Verify Queue 19 Unit EE — Tool Condition Wiring (GDD-04 §3.3,
Unit DQ follow-up).

Checks the tool-condition wiring against its sources:
tools/sim/lost_items.py (condition state + wear + break),
tools/sim/scheduler.py (the broken-tool bend),
tools/sim/engine.py (the run_day wiring), GDD-04 §3.3 (the DQ
design + the EE implementation note), and the tests
(test_lost_items.py TestToolCondition + test_scheduler.py bend
tests). Prints one line per check and a summary; exits 0 only
when every check passes.
Run from the repo root: python3 tools/verify_queue19_ee.py
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
    lost_items = (ROOT / "tools" / "sim" / "lost_items.py").read_text()
    scheduler = (ROOT / "tools" / "sim" / "scheduler.py").read_text()
    engine = (ROOT / "tools" / "sim" / "engine.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_lost_items.py").read_text()
    sched_tests = (ROOT / "tools" / "sim" / "tests"
                   / "test_scheduler.py").read_text()

    # 1. The constants are the vehicle's thresholds (DQ design).
    check("CONDITION_NEW = 100" in lost_items,
          "lost_items.py seeds condition at 100")
    check("SERVICE_THRESHOLD = 60" in lost_items,
          "lost_items.py pins the service threshold at 60")
    check("RESTORED_CONDITION = 90" in lost_items,
          "lost_items.py pins the restored condition at 90")

    # 2. The state carries condition, and a missing key reads 100.
    tool_seed = lost_items.split("def seed_tool_rows(")[1] \
        .split("def seed_furniture_rows(")[0]
    check('"condition": CONDITION_NEW' in tool_seed,
          "seed_tool_rows writes condition 100 (CONDITION_NEW)")
    check("def item_condition(" in lost_items,
          "lost_items.py defines item_condition")
    check("100" in lost_items.split("def item_condition(")[1]
          .split("def _set_condition(")[0],
          "a missing condition key reads as 100 (pre-Queue-19 rows)")

    # 3. The wear and the break.
    check("def apply_tool_wear(" in lost_items,
          "lost_items.py defines apply_tool_wear")
    check("def broken_tools_for(" in lost_items,
          "lost_items.py defines broken_tools_for")
    check("def tool_needs_service(" in lost_items,
          "lost_items.py defines tool_needs_service")
    check("tool_broken" in lost_items,
          "the break logs a tool_broken life event")
    check("def _profession_tool_rows(" in lost_items,
          "lost_items.py defines _profession_tool_rows")

    # 4. The scheduler bends a broken tool's work blocks to rest.
    check("broken_tool=False" in scheduler,
          "scheduler.instantiate takes a broken_tool flag")
    check('b["broken_tool"] = True' in scheduler,
          "the bent block carries the broken_tool flag")
    bend = scheduler.split("if broken_tool:")[1] \
        .split("jitter = jitter_for")[0]
    check('b["activity"] = "home"' in bend
          and 'b["location"] = "home"' in bend,
          "the bend retargets the work block to home (rest)")
    check('b["activity"] == "work"' in bend,
          "only work blocks bend (study blocks never do)")

    # 5. The engine wires both halves.
    check("import lost_items" in engine
          or "from tools.sim import lost_items" in engine,
          "engine.py imports lost_items")
    check("broken_tools_for(" in engine,
          "engine.py reads the broken tools for the worker")
    check("apply_tool_wear(" in engine,
          "engine.py applies tool wear after the work day")

    # 6. The design records the wiring.
    check("**Implementation (Unit EE" in gdd04,
          "GDD-04 §3.3 carries the EE implementation note")
    check("tool weather cause" in gdd04
          or "tool weather wear" in gdd04
          or "weather wear" in gdd04,
          "GDD-04 §3.3 records the unwired tool weather wear as open")

    # 7. The tests prove the wiring.
    check("class TestToolCondition" in tests,
          "test_lost_items.py has the tool-condition tests")
    check("test_broken_tool_bends_work_blocks_to_rest" in sched_tests,
          "test_scheduler.py tests the broken-tool bend")
    check("test_broken_tool_leaves_study_blocks_alone" in sched_tests,
          "test_scheduler.py tests study blocks untouched")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
