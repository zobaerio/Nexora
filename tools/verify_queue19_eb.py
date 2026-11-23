"""Verify Queue 19 Unit EB — Mission 1.3 Completion Condition +
Verifier (GDD-04 §3.6; DS follow-up).

Checks the condition against its sources: data/missions.json (1.3
objectives/rewards/unlocks), tools/sim/missions.py (the
verify_mission_1_3 writer + neighbours_of helper + the registry),
GDD-04 §3.6 (the 1.3 completion condition), data/dialogue-lines.json
(the 1.3 tree, unchanged — EB adds no tree), and the tests
(test_missions.py TestMission13 + the DS regression suite).
Prints one line per check and a summary; exits 0 only when every
check passes. Run from the repo root: python3 tools/verify_queue19_eb.py
"""
import json
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
    dlg = json.loads((ROOT / "data" / "dialogue-lines.json").read_text())
    missions = json.loads((ROOT / "data" / "missions.json").read_text())
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_missions.py").read_text()
    suite = (ROOT / "tools" / "sim" / "tests"
             / "test_mission_progress_regression.py").read_text()
    ds = (ROOT / "tools" / "verify_queue18_ds.py").read_text()

    m13 = next(m for m in missions["missions"] if m["id"] == "1.3")
    tree = dlg["trees"].get("mission_1_3_neighbour_help", {})

    # 1. The mission data is what the condition verifies.
    check(m13["objectives"] == ["Meet 3 neighbours",
                                "Help one neighbour with a small task "
                                "(carry, fetch, fix)"],
          "missions.json 1.3 carries the two objectives")
    check(m13["rewards"]["credits_ncr"] is None
          and m13["rewards"]["reputation"] == [
              {"amount": 10, "scope": "relationship_each_met"},
              {"amount": 5, "scope": "district"}],
          "missions.json 1.3 reward is +10 each met + 5 district, "
          "no credits")
    check(m13["unlocks"] == ["Neighbour favour system"],
          "missions.json 1.3 unlocks the Neighbour favour system")

    # 2. The writer implements the condition.
    check("def verify_mission_1_3(" in missions_py,
          "missions.py implements verify_mission_1_3")
    check("def neighbours_of(" in missions_py,
          "missions.py has the neighbours_of helper")
    check("MISSION_1_3_NEIGHBOURS_TO_MEET = 3" in missions_py,
          "missions.py pins the neighbour count at 3")
    check('"1.3": "verify_mission_1_3"' in missions_py,
          "the registry holds 1.3")
    check("side:errands:" in missions_py
          or '"side:errands:%"' in missions_py,
          "the verifier reads completed errands favour instances")
    check("set_objectives_complete(store, character_id, \"1.3\""
          in missions_py,
          "the verifier sets objectives_complete while still active")

    # 3. The condition is specified in GDD-04 §3.6.
    check("**Completion condition — mission 1.3" in gdd04,
          "GDD-04 §3.6 specifies the 1.3 condition")
    s36 = gdd04.split("**Completion condition — mission 1.3")[1] \
        .split("**Completion condition — mission 1.4")[0]
    check("neighbour" in s36 and "errands" in s36,
          "§3.6 names the neighbour edges and the errands favour")
    check("stranger" in s36,
          "§3.6 states what does NOT verify (a stranger's errand)")
    check("does **not** open photo mode" in s36,
          "§3.6 states completing 1.3 does not open the DA gate")
    check("not** paid by this writer" in s36,
          "§3.6 states the reputation reward is Phase 6 work")
    check("**Implementation (Unit EB" in gdd04,
          "GDD-04 §3.6 carries the EB implementation note")

    # 4. The tree is unchanged — EB adds the condition and the
    # verifier, not a tree (the 1.3 tree shipped with Unit AO).
    check("mission_1_3_neighbour_help" in dlg["trees"],
          "dialogue-lines.json still has the 1.3 tree")
    check(tree.get("objectives_quoted") == m13["objectives"],
          "1.3 objectives_quoted match missions.json verbatim")
    check(tree.get("rewards_quoted") == m13["rewards"],
          "1.3 rewards_quoted match missions.json verbatim")
    check(tree.get("unlocks_quoted") == m13["unlocks"],
          "1.3 unlocks_quoted match missions.json verbatim")

    # 5. The DS suite covers 1.3 now.
    check('"1.3"' in ds and "verify_mission_1_3" in ds,
          "the DS verify script covers 1.3")
    check("test_1_3_completes_only_with_3_neighbours_and_a_help"
          in suite,
          "the DS suite tests 1.3 completing only with 3 neighbours "
          "and a help")
    check("class TestMission13" in tests,
          "test_missions.py has the 1.3 edge tests (EB)")
    check("test_helping_a_stranger_does_not_verify" in tests,
          "test_missions.py tests the stranger-errand refusal")
    check("test_help_before_acceptance_still_verifies" in tests,
          "test_missions.py tests help predating acceptance")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
