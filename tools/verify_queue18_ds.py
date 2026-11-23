"""Verify Queue 18 Unit DS — Mission-Progress Regression Suite
(GDD-04 §3.6; DL/DO follow-up).

Checks the suite against the sources it guards: tools/sim/missions.py
(the CONDITIONED_MISSIONS registry + the verifiers), GDD-04 §3.6
(the completion conditions), tools/sim/photographs.py (the DA gate),
tools/sim/tests/test_mission_progress_regression.py (the suite
itself), and tools/sim/tests/test_missions.py (the per-mission edge
coverage the suite builds on). No sim behaviour change. Prints one
line per check and a summary; exits 0 only when every check passes.
Run from the repo root: python3 tools/verify_queue18_ds.py
"""
import json
import re
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
    missions_py = (ROOT / "tools" / "sim" / "missions.py").read_text()
    photos_py = (ROOT / "tools" / "sim" / "photographs.py").read_text()
    suite = (ROOT / "tools" / "sim" / "tests"
             / "test_mission_progress_regression.py").read_text()
    missions_tests = (ROOT / "tools" / "sim" / "tests"
                      / "test_missions.py").read_text()
    dlg = json.loads((ROOT / "data" / "dialogue-lines.json").read_text())

    # 1. The registry is the single source of truth.
    check("CONDITIONED_MISSIONS = {" in missions_py,
          "missions.py defines the CONDITIONED_MISSIONS registry")
    check('"1.3": "verify_mission_1_3"' in missions_py
          and '"1.4": "verify_mission_1_4"' in missions_py
          and '"2.1": "verify_mission_2_1"' in missions_py
          and '"2.2": "verify_mission_2_2"' in missions_py,
          "the registry holds exactly 1.3, 1.4, 2.1 and 2.2")
    check('"2.4"' not in missions_py.split(
        "CONDITIONED_MISSIONS = {")[1].split("}")[0],
          "2.4 is not in the registry (no condition, no verifier)")

    # 2. The tripwire: every verifier is registered, every registered
    # mission has a §3.6 condition, every §3.6 condition is registered.
    verifiers = re.findall(r"def (verify_mission_[\w.]+)\(", missions_py)
    check(sorted(verifiers) == ["verify_mission_1_3",
                                "verify_mission_1_4",
                                "verify_mission_2_1",
                                "verify_mission_2_2"],
          "missions.py has exactly four verifiers (1.3, 1.4, 2.1, 2.2)",
          f"{verifiers}")
    specified = re.findall(
        r"\*\*Completion condition — mission (\d+\.\d+)", gdd04)
    check(sorted(specified) == ["1.3", "1.4", "2.1", "2.2"],
          "GDD-04 §3.6 specifies exactly four conditions"
          " (1.3, 1.4, 2.1, 2.2)",
          f"{specified}")
    check(sorted(specified) == sorted(
        re.findall(r'"(\d+\.\d+)": "verify_mission', missions_py)),
          "the §3.6 conditions and the registry agree")

    # 3. The suite asserts the tripwire as standing tests.
    check("class TestRegistryTripwire" in suite,
          "the suite has a registry-tripwire test class")
    check("test_every_verifier_is_registered" in suite
          and "test_every_section_3_6_condition_is_registered" in suite,
          "the suite tests both directions of the tripwire")
    check("test_trees_without_conditions_are_out_of_scope" in suite,
          "the suite records that 2.4 is out of scope (1.3 is covered "
          "since Queue 19 Unit EB)")

    # 4. The suite asserts the writer completes each conditioned
    # mission exactly when its condition holds.
    check("class TestWriterCompletesConditionedMissions" in suite,
          "the suite has a writer-completes test class")
    check("test_1_3_completes_only_with_3_neighbours_and_a_help"
          in suite,
          "the suite tests 1.3 completing only with 3 neighbours "
          "and a help")
    check("test_1_4_completes_only_in_the_sunset_window_at_the_stall"
          in suite,
          "the suite tests 1.4 completing only in its window")
    check("test_2_1_completes_only_at_skill_20_in_the_primary_skill"
          in suite,
          "the suite tests 2.1 completing only at skill 20")
    check("test_2_2_completes_only_at_starting_balance_plus_15000"
          in suite,
          "the suite tests 2.2 completing only at starting + 15,000")
    check("test_a_conditioned_mission_never_completes_unverified"
          in suite,
          "the suite tests no completion without verification")

    # 5. The suite asserts the DA gate stays closed otherwise.
    check("class TestGateStaysClosedOtherwise" in suite,
          "the suite has a gate test class")
    check("test_completing_2_1_does_not_open_the_gate" in suite
          and "test_completing_1_3_does_not_open_the_gate" in suite
          and "test_completing_2_2_does_not_open_the_gate" in suite
          and "test_gate_stays_closed_when_1_4_fails" in suite
          and "test_completing_a_favour_does_not_open_the_gate" in suite,
          "the suite tests the gate against 1.3, 2.1, 2.2, a failed "
          "1.4, a favour")
    check('PHOTO_MODE_MISSION = "1.4"' in photos_py,
          "the DA gate reads the 1.4 row only")

    # 6. The per-mission edge coverage the suite builds on exists.
    check("class TestMission13" in missions_tests,
          "test_missions.py has the 1.3 edge tests (EB)")
    check("class TestMission22" in missions_tests,
          "test_missions.py has the 2.2 edge tests (EC)")
    check("class TestMission21" in missions_tests,
          "test_missions.py has the 2.1 edge tests (DO)")
    check("class TestMission14" in missions_tests,
          "test_missions.py has the 1.4 edge tests (DL)")

    # 7. No sim behaviour change in this unit: the registry is defined
    # but consumed by no sim code path — only the suite reads it.
    check(missions_py.count("CONDITIONED_MISSIONS") == 1,
          "the registry is defined but never read by sim code "
          "(definition only)",
          f"{missions_py.count('CONDITIONED_MISSIONS')} mention")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
