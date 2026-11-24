"""Verify Queue 20 Unit EG — Tool Weather Wear (GDD-04 §3.3, Unit
DQ follow-up).

Checks the tool weather wear against its sources:
tools/sim/lost_items.py (the wear function), tools/sim/environment.py
(the daily-pass wiring beside the furniture wear), GDD-04 §3.3 (the
DQ design + the EG implementation note), and the tests
(test_lost_items.py TestToolWeatherWear). Prints one line per check
and a summary; exits 0 only when every check passes.
Run from the repo root: python3 tools/verify_queue20_eg.py
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
    environment = (ROOT / "tools" / "sim" / "environment.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_lost_items.py").read_text()

    # 1. The wear function exists and wears the tools of the trade.
    check("def apply_tool_weather_wear(" in lost_items,
          "lost_items.py defines apply_tool_weather_wear")
    wear = lost_items.split("def apply_tool_weather_wear(")[1] \
        .split("def _repair(")[0]
    check("_profession_tool_rows(" in wear,
          "the wear reads the tools of the trade (DJ seeding rule)")
    check("home_property_id" in wear,
          "the wear keys off the character's home property")
    check("district_id" in wear,
          "the wear reads the home property's district (zone)")
    check("before - 1" in wear,
          "the wear is -1 per exposed day (DQ)")
    check('\"tool_broken\"' in wear,
          "a tool reaching 0 logs the tool_broken life event")
    check('\"weather_exposure\"' in wear,
          "the weather break is distinguishable (cause recorded)")
    check("if not zones:" in wear,
          "an empty zone set wears nothing")

    # 2. The environment pass wires it beside the furniture wear.
    # Queue 21 Unit EP changed the shape: the pass unions the
    # exposed zones across all active disasters and calls each wear
    # helper once per day over that union (a doubly-exposed zone
    # wears once, not once per disaster).
    check("apply_tool_weather_wear(" in environment,
          "environment.daily_pass calls apply_tool_weather_wear")
    check("exposed |= set(exposed_zones(" in environment,
          "the pass unions the exposed zones across disasters")
    call = environment.split("apply_tool_weather_wear(")[1] \
        .split("game_minutes)")[0]
    check("exposed" in call,
          "the call passes the unioned exposed zones (EP)")
    check("apply_furniture_exposure_wear(" in environment,
          "the furniture wear call still stands beside it")

    # 3. The design records the wiring and the home-zone reading.
    check("**Implementation (Unit EG" in gdd04,
          "GDD-04 §3.3 carries the EG implementation note")
    check("HOME" in gdd04.split("**Implementation (Unit EG")[1]
          .split("**Implementation (Unit EH")[0],
          "the EG note records the home-zone reading (not DQ's "
          "current-zone wording)")
    check("two simultaneous disasters" in gdd04,
          "the concurrent-disaster double-wear edge is recorded, "
          "not silently fixed")

    # 4. The tests prove the wiring.
    check("class TestToolWeatherWear" in tests,
          "test_lost_items.py has the tool-weather-wear tests")
    for name in ("test_exposed_home_wears_the_tools_by_one",
                 "test_unexposed_home_wears_nothing",
                 "test_no_household_wears_nothing",
                 "test_weather_break_logs_one_event",
                 "test_environment_pass_wears_exposed_tools_and_furniture"):
        check(name in tests, f"test_lost_items.py has {name}")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
