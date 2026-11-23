"""Verify Queue 19 Unit EC — Mission 2.2 Condition + Tree
(GDD-04 §3.6; DS follow-up; DO precedent).

Checks the tree against its sources: data/missions.json (2.2
objectives/rewards/unlocks), data/dialogue-lines.json (the 8-node
AO-pattern tree), tools/sim/missions.py (the
verify_mission_2_2 writer + starting_balance_of), GDD-04 §3.6
(the 2.2 completion condition), GDD-15 §13.6 (the count 29), and
tools/validate_data.py (the 2.2 tree checks). Prints one line per
check and a summary; exits 0 only when every check passes.
Run from the repo root: python3 tools/verify_queue19_ec.py
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


def check_lines(lines, pattern, label):
    for line in lines:
        if pattern in line:
            return check(True, label)
    return check(False, label, f"no line contains {pattern!r}")


def main():
    gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md").read_text()
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    missions_py = (ROOT / "tools" / "sim" / "missions.py").read_text()
    dlg = json.loads((ROOT / "data" / "dialogue-lines.json").read_text())
    missions = json.loads((ROOT / "data" / "missions.json").read_text())
    validator = (ROOT / "tools" / "validate_data.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_missions.py").read_text()
    suite = (ROOT / "tools" / "sim" / "tests"
             / "test_mission_progress_regression.py").read_text()

    m22 = next(m for m in missions["missions"] if m["id"] == "2.2")
    tree = dlg["trees"].get("mission_2_2_rainy_day_fund", {})
    nodes = tree.get("nodes", [])
    by_id = {n["node_id"]: n for n in nodes}

    # 1. The tree is an 8-node AO-pattern tree (the 2.1 precedent).
    check("mission_2_2_rainy_day_fund" in dlg["trees"],
          "dialogue-lines.json has the 2.2 tree")
    check([n["node_id"] for n in nodes] ==
          ["dlg_2_2_intro", "dlg_2_2_offer", "dlg_2_2_accept",
           "dlg_2_2_decline", "dlg_2_2_hello", "dlg_2_2_reminder",
           "dlg_2_2_reminder_exit", "dlg_2_2_return"],
          "the 2.2 tree has exactly the 8 AO-pattern nodes, in order")
    check(tree.get("mission_id") == "2.2"
          and tree.get("title") == m22["title"],
          "the 2.2 tree title matches missions.json")
    check("The giver for 2.2 is a condition, not a person: a neighbour"
          in gdd15,
          "GDD-15 §13.6 records the giver as a condition (a neighbour "
          "edge; the 1.3 fiction carries over)")

    # 2. The tree quotes the mission verbatim.
    check(tree.get("objectives_quoted") == m22["objectives"],
          "2.2 objectives_quoted match missions.json verbatim")
    check(tree.get("rewards_quoted") == m22["rewards"],
          "2.2 rewards_quoted match missions.json verbatim")
    check(tree.get("unlocks_quoted") == m22["unlocks"],
          "2.2 unlocks_quoted match missions.json verbatim")
    check(m22["rewards"] == {
        "credits_ncr": 1500,
        "other": ["Reward is an interest bonus (GDD-04 §2)"],
        "reputation": []},
          "missions.json 2.2 reward is 1,500 NCr interest bonus, "
          "no reputation")
    ret = by_id.get("dlg_2_2_return", {})
    check(any(e.get("type") == "mission_complete"
              and e.get("rewards") == m22["rewards"]
              for e in ret.get("effects", [])),
          "the return node carries the reward verbatim in its "
          "mission_complete effect")
    check(tree.get("objectives_quoted")[0].startswith(
        "Save 15,000 NCr above your starting balance"),
          "the first objective names the 15,000 NCr target")

    # 3. The tree follows the §5 contract.
    offer = by_id.get("dlg_2_2_offer", {})
    check(offer.get("condition") ==
          {"mission": "2.2", "state": "available"},
          "the offer node is gated on the mission being available")
    check({c.get("next") for c in offer.get("choices", [])} ==
          {"dlg_2_2_accept", "dlg_2_2_decline"},
          "the offer node's choices lead to accept and decline")
    accept = by_id.get("dlg_2_2_accept", {})
    check(any(e.get("type") == "mission_progress"
              and e.get("state") == "accepted"
              for e in accept.get("effects", [])),
          "the accept node moves the mission to accepted")
    reminder = by_id.get("dlg_2_2_reminder", {})
    check(len(reminder.get("lines", [])) == 1
          and reminder.get("condition") ==
          {"mission": "2.2", "state": "accepted"}
          and any(c.get("next") == "dlg_2_2_reminder_exit"
                  for c in reminder.get("choices", [])),
          "the reminder node is one line, gated on accepted, "
          "leading to reminder-exit")
    check(by_id.get("dlg_2_2_reminder_exit", {}).get("ends") is True,
          "the reminder-exit node ends the conversation")
    check(ret.get("condition") ==
          {"mission": "2.2", "state": "objective_complete"},
          "the return node is gated on objective completion")
    check(len([k for k in dlg["trees"] if k.startswith("mission_")])
          == 5,
          "5 mission trees in dialogue-lines.json (2.2 is the 5th)")
    mission_nodes = sum(
        1 for t in dlg["trees"].values()
        for n in t.get("nodes", [])
        if isinstance(n.get("condition"), dict)
        and "mission" in n["condition"])
    check(mission_nodes == 29,
          "29 mission-condition nodes across the shipped trees",
          f"{mission_nodes}")
    # No line prose may contain a digit + NCr (DO precedent) — the
    # figure lives in objectives_quoted, not in a spoken line.
    bad = [n["node_id"] for n in nodes
           if re.search(r"\d[\d,]*\s*NCr",
                        " ".join(l.get("text", "")
                                 for l in n.get("lines", [])))]
    check(not bad, "no spoken line carries a digit + NCr",
          f"{bad}")
    check("15,000" in tree.get("objectives_quoted", [""])[0],
          "the 15,000 figure lives in objectives_quoted")

    # 4. The writer implements the condition.
    check("def verify_mission_2_2(" in missions_py,
          "missions.py implements verify_mission_2_2")
    check("def starting_balance_of(" in missions_py,
          "missions.py has the starting_balance_of helper")
    check("MISSION_2_2_SAVINGS_TARGET = 15000" in missions_py,
          "missions.py pins the savings target at 15,000")
    check('"2.2": "verify_mission_2_2"' in missions_py,
          "the registry holds 2.2")
    check("store.balance(character_id)" in missions_py,
          "the verifier reads the balance via store.balance()")

    # 5. The condition is specified in GDD-04 §3.6.
    check("**Completion condition — mission 2.2" in gdd04,
          "GDD-04 §3.6 specifies the 2.2 condition")
    s36 = gdd04.split("**Completion condition — mission 2.2")[1] \
        .split("**Completion condition — mission 2.4")[0]
    check("15,000" in s36 and "starting_balance_ncr" in s36,
          "§3.6 names the 15,000 target and the starting balance")
    check("unemployed" in s36,
          "§3.6 states the unemployed cannot verify")
    check("does **not** open photo mode" in s36,
          "§3.6 states completing 2.2 does not open the DA gate")
    check("not** paid by this writer" in s36,
          "§3.6 states the 1,500 NCr interest bonus is Phase 6 work")
    check("**Implementation (Unit EC" in gdd04,
          "GDD-04 §3.6 carries the EC implementation note")

    # 6. The dialogue doc is updated.
    check("29 mission-condition nodes" in gdd15,
          "GDD-15 §13.6 counts 29 mission-condition nodes")
    check("dlg_2_2_offer" in gdd15 and "dlg_2_2_return" in gdd15,
          "GDD-15 §13.6 lists the 2.2 table rows")
    check("6 × 2.2" in gdd15,
          "GDD-15 §13.6 records the 2.2 tree adding 6 nodes")

    # 7. The validator checks the new tree.
    check("mission_2_2_rainy_day_fund" in validator,
          "validate_data.py checks the 2.2 tree")

    # 8. The tests prove the condition.
    check("class TestMission22" in tests,
          "test_missions.py has the 2.2 edge tests (EC)")
    check("test_unemployed_cannot_verify" in tests,
          "test_missions.py tests the unemployed refusal")
    check("test_2_2_completes_only_at_starting_balance_plus_15000"
          in suite,
          "the DS suite tests 2.2 completing only at starting "
          "+ 15,000")
    check("test_target_follows_the_current_profession" in tests,
          "test_missions.py tests the target following the "
          "current profession")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
