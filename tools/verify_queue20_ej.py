"""Verify Queue 20 Unit EJ — Mission 2.4 Completion Condition +
Verifier (GDD-04 §3.6; DS follow-up).

Checks the 2.4 condition against its sources: data/missions.json
(the objective), data/dialogue-lines.json (the tree + the entry
gate), tools/sim/missions.py (verify_mission_2_4 + the registry),
GDD-04 §3.6 (the condition + the implementation note), GDD-15
§12.3 (the mean reading), and the tests (test_missions.py
TestMission24 + the DS regression suite). Prints one line per
check and a summary; exits 0 only when every check passes.
Run from the repo root: python3 tools/verify_queue20_ej.py
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
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    missions = (ROOT / "tools" / "sim" / "missions.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_missions.py").read_text()
    regression = (ROOT / "tools" / "sim" / "tests"
                  / "test_mission_progress_regression.py").read_text()
    missions_json = json.loads(
        (ROOT / "data" / "missions.json").read_text())
    dialogue = json.loads(
        (ROOT / "data" / "dialogue-lines.json").read_text())

    # 1. The objective is the mission's own (data/missions.json).
    m24 = next(m for m in missions_json["missions"]
               if m["id"] == "2.4")
    check(m24["objectives"] == ["Raise one friendship to 40+"
                                " (trust/affection)"],
          "missions.json 2.4 objective is the single friendship "
          "objective")
    check(m24["rewards"]["credits_ncr"] is None,
          "2.4 carries no credit reward (Phase 6 reward step)")

    # 2. The tree exists and its entry gate agrees on the number.
    tree = dialogue["trees"]["mission_2_4_friendship"]
    nodes = tree["nodes"]
    check(len(nodes) == 7,
          "the 2.4 tree has 7 nodes (entry/offer/accept/decline/"
          "later/progress/return)", f"found {len(nodes)}")
    entry = next(n for n in nodes
                 if n["node_id"] == "dlg_2_4_entry")
    check(entry["condition"].get("relationship_mean_min") == 40,
          "the tree's entry gate requires relationship_mean_min 40")
    check("mean of trust and affection" in gdd15,
          "GDD-15 §12.3 defines the mean (trust + affection)")

    # 3. The verifier exists, is registered, and reads friend edges.
    check("def verify_mission_2_4(" in missions,
          "missions.py defines verify_mission_2_4")
    check("def friendship_mean(" in missions,
          "missions.py defines friendship_mean")
    check('"2.4": "verify_mission_2_4"' in missions,
          "2.4 is registered in CONDITIONED_MISSIONS")
    check("MISSION_2_4_FRIENDSHIP_MEAN = 40" in missions,
          "the threshold is the mission's own number (40)")
    verifier = missions.split("def verify_mission_2_4(")[1] \
        .split("def complete_mission(")[0]
    check("relation_type = 'friend'" in verifier,
          "the verifier reads friend edges only")
    check("set_objectives_complete(" in verifier,
          "verification sets objectives_complete while active")

    # 4. The design records the condition.
    check("**Completion condition — mission 2.4" in gdd04,
          "GDD-04 §3.6 carries the 2.4 completion condition")
    check("**Implementation (Unit EJ" in gdd04,
          "GDD-04 §3.6 carries the EJ implementation note")
    check("every shipped mission tree has a condition" in gdd04,
          "the EJ note records that every shipped tree now has a "
          "condition")
    check(gdd04.count("*(Update, Unit EJ") == 3,
          "each stale '2.4 has no condition' sentence carries an EJ "
          "update note (EB, DO, EC paragraphs)",
          f"found {gdd04.count('*(Update, Unit EJ')}")

    # 5. The tests prove the verifier and the suite covers it.
    check("class TestMission24" in tests,
          "test_missions.py has the 2.4 tests")
    for name in ("test_a_friend_at_mean_40_completes_2_4",
                 "test_one_short_of_the_mean_does_not_verify",
                 "test_a_spouse_or_colleague_at_40_does_not_verify",
                 "test_no_friend_edge_does_not_verify",
                 "test_2_4_completion_does_not_open_the_da_gate"):
        check(name in tests, f"test_missions.py has {name}")
    check("test_every_shipped_mission_tree_has_a_condition"
          in regression,
          "the DS suite asserts every shipped tree has a condition")
    check("test_2_4_completes_only_with_a_friend_at_mean_40"
          in regression,
          "the DS suite proves 2.4 completes exactly when its "
          "condition holds")
    check("assertNotIn(\"2.4\", ms.CONDITIONED_MISSIONS)"
          not in regression,
          "the DS suite no longer records 2.4 as out of scope")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
