"""Verify Queue 21 Unit EP — Concurrent-Disaster Exposure Wear
Dedupe (GDD-04 §3.3, EG follow-up).

Checks the dedupe against its sources: tools/sim/environment.py
(the daily pass unions the exposed zones and calls each wear
helper once per day), tools/sim/lost_items.py (the wear helpers'
docstrings record the new call shape), GDD-04 §3.3 (the EG note
now records the dedupe), and the tests (test_lost_items.py
TestExposureWearDedupe). Prints one line per check and a summary;
exits 0 only when every check passes.
Run from the repo root: python3 tools/verify_queue21_ep.py
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
    environment = (ROOT / "tools" / "sim" / "environment.py").read_text()
    lost_items = (ROOT / "tools" / "sim" / "lost_items.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_lost_items.py").read_text()
    eg_script = (ROOT / "tools" / "verify_queue20_eg.py").read_text()

    # 1. The daily pass unions the exposed zones and calls each
    # wear helper once.
    check("exposed |= set(exposed_zones(" in environment,
          "daily_pass unions the exposed zones across disasters")
    wear = environment.split("exposed |= set(exposed_zones(")[1] \
        .split("# Disaster phase transitions")[0]
    check(wear.count("apply_furniture_exposure_wear(") == 1,
          "the pass calls the furniture wear exactly once per day")
    check(wear.count("apply_tool_weather_wear(") == 1,
          "the pass calls the tool wear exactly once per day")
    check("if exposed:" in wear,
          "the wear calls run only when a zone is exposed")
    check("two simultaneous disasters wore twice a day before this"
          " unit" in environment,
          "the pass comment records the old double-wear behaviour")

    # 2. The wear helpers record the new call shape.
    check("once per day over the union" in lost_items,
          "the wear helpers' docstrings record the once-per-day "
          "union call")
    check("wears twice in one day" not in lost_items,
          "no helper docstring still claims the double wear")

    # 3. The design note records the dedupe.
    check("**Implementation (Unit EG" in gdd04,
          "GDD-04 §3.3 still carries the EG implementation note")
    eg_note = gdd04.split("**Implementation (Unit EG")[1] \
        .split("**Implementation (Unit EH")[0]
    check("once per day over the union" in eg_note,
          "the EG note states the once-per-day union call")
    check("two simultaneous disasters wore twice in one day before"
          " Unit EP" in eg_note,
          "the EG note records the old behaviour as past tense")
    check("*(Update, Unit EP" in eg_note,
          "the EG note carries the EP update")

    # 4. The EG verify script was updated to the new shape (its old
    # wiring check asserted the per-disaster call).
    check("exposed |= set(exposed_zones(" in eg_script,
          "verify_queue20_eg.py checks the union, not the old "
          "per-disaster call")

    # 5. The tests prove the dedupe.
    check("class TestExposureWearDedupe" in tests,
          "test_lost_items.py has the dedupe tests")
    for name in ("test_two_simultaneous_disasters_wear_once",
                 "test_second_day_wears_again",
                 "test_helpers_still_wear_once_per_call"):
        check(name in tests, f"test_lost_items.py has {name}")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
