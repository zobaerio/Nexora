"""Verify Queue 20 Unit EK — Deceased-Giver Favour Guard (GDD-04
§3.1/§3.3; DP follow-up).

Checks the guard against its sources: tools/sim/missions.py
(create_favour_instance), GDD-04 §3.1 (the generator's rule list),
and the tests (test_missions.py TestFavourInstances). Prints one
line per check and a summary; exits 0 only when every check passes.
Run from the repo root: python3 tools/verify_queue20_ek.py
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
    missions = (ROOT / "tools" / "sim" / "missions.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_missions.py").read_text()

    # 1. The guard sits at the favour-instance creation path.
    check("def create_favour_instance(" in missions,
          "missions.py defines create_favour_instance")
    fn = missions.split("def create_favour_instance(")[1] \
        .split("def verify_favour_objectives(")[0]
    check("died_at_game_minutes" in fn,
          "the guard reads the giver's death minute")
    check("giver is None or giver[\"died_at_game_minutes\"]"
          " is not None" in fn,
          "an unknown giver is refused too (no row to offer from)")
    check("return None" in fn,
          "the refusal returns None (no row is created)")
    check("make_available(" in fn,
          "a living giver still creates the row via make_available")

    # 2. The design records the guard.
    check("no favour for a deceased giver" in gdd04,
          "GDD-04 §3.1 records the deceased-giver rule")
    check("Unit EK" in gdd04,
          "GDD-04 §3.1 carries the EK update note")

    # 3. The tests prove the refusal and the unaffected living giver.
    for name in ("test_create_favour_instance_refuses_a_deceased_giver",
                 "test_create_favour_instance_refuses_an_unknown_giver",
                 "test_a_living_giver_is_unaffected"):
        check(name in tests, f"test_missions.py has {name}")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
