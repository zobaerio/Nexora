"""Verify Queue 21 Unit EO — Mission 2.3 Tree + Condition +
Verifier (GDD-04 §3.6; EC precedent).

Checks the tree against its sources: data/missions.json (2.3
objectives/rewards/unlocks), data/dialogue-lines.json (the 8-node
AO-pattern tree), tools/sim/missions.py (the
verify_mission_2_3 writer + household_of / household_bought_food),
GDD-04 §3.6 (the 2.3 completion condition), GDD-15 §13.6 (the
count 35), and tools/validate_data.py (the 2.3 tree checks).
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue21_eo.py
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
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    missions_py = (ROOT / "tools" / "sim" / "missions.py").read_text()
    dlg = json.loads((ROOT / "data" / "dialogue-lines.json").read_text())
    missions = json.loads((ROOT / "data" / "missions.json").read_text())
    validator = (ROOT / "tools" / "validate_data.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_missions.py").read_text()
    suite = (ROOT / "tools" / "sim" / "tests"
             / "test_mission_progress_regression.py").read_text()

    m23 = next(m for m in missions["missions"] if m["id"] == "2.3")
    tree = dlg["trees"].get("mission_2_3_market_run", {})
    nodes = tree.get("nodes", [])
    by_id = {n["node_id"]: n for n in nodes}

    # 1. The tree is an 8-node AO-pattern tree (the 2.1/2.2
    # precedent).
    check("mission_2_3_market_run" in dlg["trees"],
          "dialogue-lines.json has the 2.3 tree")
    check([n["node_id"] for n in nodes] ==
          ["dlg_2_3_intro", "dlg_2_3_offer", "dlg_2_3_accept",
           "dlg_2_3_decline", "dlg_2_3_hello", "dlg_2_3_reminder",
           "dlg_2_3_reminder_exit", "dlg_2_3_return"],
          "the 2.3 tree has exactly the 8 AO-pattern nodes, in order")
    check(tree.get("mission_id") == "2.3"
          and tree.get("title") == m23["title"],
          "the 2.3 tree title matches missions.json")
    check("The giver for 2.3 is a condition, not a person: a neighbour"
          in gdd15,
          "GDD-15 §13.6 records the giver as a condition (a neighbour "
          "edge; the 1.3 fiction carries over)")

    # 2. The tree quotes the mission verbatim.
    check(tree.get("objectives_quoted") == m23["objectives"],
          "2.3 objectives_quoted match missions.json verbatim")
    check(tree.get("rewards_quoted") == m23["rewards"],
          "2.3 rewards_quoted match missions.json verbatim")
    check(tree.get("unlocks_quoted") == m23["unlocks"],
          "2.3 unlocks_quoted match missions.json verbatim")
    check(m23["rewards"] == {
        "credits_ncr": 500,
        "other": [],
        "reputation": [{"amount": 5, "scope": "market"}]},
          "missions.json 2.3 reward is 500 NCr + 5 market "
          "reputation")
    check(m23["unlocks"] == ["Haggling", "Market regular status"],
          "missions.json 2.3 unlocks are Haggling + Market regular "
          "status")
    ret = by_id.get("dlg_2_3_return", {})
    check(any(e.get("type") == "mission_complete"
              and e.get("rewards") == m23["rewards"]
              for e in ret.get("effects", [])),
          "the return node carries the reward verbatim in its "
          "mission_complete effect")
    check(tree.get("objectives_quoted")[0].startswith(
        "Buy a week's food at Boro Bazar"),
          "the first objective names the Boro Bazar food purchase")
    check(tree.get("objectives_quoted")[1] ==
          "Haggle once, successfully",
          "the second objective names the haggle")

    # 3. The tree follows the §5 contract.
    offer = by_id.get("dlg_2_3_offer", {})
    check(offer.get("condition") ==
          {"mission": "2.3", "state": "available"},
          "the offer node is gated on the mission being available")
    check({c.get("next") for c in offer.get("choices", [])} ==
          {"dlg_2_3_accept", "dlg_2_3_decline"},
          "the offer node's choices lead to accept and decline")
    accept = by_id.get("dlg_2_3_accept", {})
    check(any(e.get("type") == "mission_progress"
              and e.get("state") == "accepted"
              for e in accept.get("effects", [])),
          "the accept node moves the mission to accepted")
    reminder = by_id.get("dlg_2_3_reminder", {})
    check(len(reminder.get("lines", [])) == 1
          and reminder.get("condition") ==
          {"mission": "2.3", "state": "accepted"}
          and any(c.get("next") == "dlg_2_3_reminder_exit"
                  for c in reminder.get("choices", [])),
          "the reminder node is one line, gated on accepted, "
          "leading to reminder-exit")
    check(by_id.get("dlg_2_3_reminder_exit", {}).get("ends") is True,
          "the reminder-exit node ends the conversation")
    check(ret.get("condition") ==
          {"mission": "2.3", "state": "objective_complete"},
          "the return node is gated on objective completion")
    check(len([k for k in dlg["trees"] if k.startswith("mission_")])
          == 6,
          "6 mission trees in dialogue-lines.json (2.3 is the 6th)")
    mission_nodes = sum(
        1 for t in dlg["trees"].values()
        for n in t.get("nodes", [])
        if isinstance(n.get("condition"), dict)
        and "mission" in n["condition"])
    check(mission_nodes == 35,
          "35 mission-condition nodes across the shipped trees",
          f"{mission_nodes}")
    # No line prose may contain a digit + NCr (DO/EC precedent) —
    # the figure lives in rewards_quoted, not in a spoken line.
    bad = [n["node_id"] for n in nodes
           if re.search(r"\d[\d,]*\s*NCr",
                        " ".join(l.get("text", "")
                                 for l in n.get("lines", [])))]
    check(not bad, "no spoken line carries a digit + NCr",
          f"{bad}")
    check(tree.get("rewards_quoted", {}).get("credits_ncr") == 500,
          "the 500 figure lives in rewards_quoted")
    # The return line must not claim a haggle was won: the writer
    # cannot verify one (EO §3.6).
    ret_text = " ".join(l.get("text", "")
                        for l in ret.get("lines", []))
    check("haggle" not in ret_text.lower(),
          "the return line claims no haggle was won",
          ret_text[:60])

    # 4. The writer implements the condition.
    check("def verify_mission_2_3(" in missions_py,
          "missions.py implements verify_mission_2_3")
    check("def household_of(" in missions_py,
          "missions.py has the household_of helper")
    check("def household_bought_food(" in missions_py,
          "missions.py has the household_bought_food helper")
    check('BORO_BAZAR_CITY = "rupsha_city"' in missions_py,
          "missions.py pins Boro Bazar's city at rupsha_city")
    check('"2.3": "verify_mission_2_3"' in missions_py,
          "the registry holds 2.3")
    check("household_consumption" in missions_py,
          "the verifier reads the household_consumption record")
    check("food_basket" in missions_py and "'fish'" in missions_py,
          "the verifier names both food goods")

    # 5. The condition is specified in GDD-04 §3.6.
    check("**Completion condition — mission 2.3" in gdd04,
          "GDD-04 §3.6 specifies the 2.3 condition")
    s36 = gdd04.split("**Completion condition — mission 2.3")[1] \
        .split("**Completion condition — mission 2.4")[0]
    check("household_consumption" in s36
          and "food_basket" in s36 and "fish" in s36,
          "§3.6 names the consumption record and both food goods")
    check("Rupsha City" in s36 and "Shibnagar" in s36,
          "§3.6 states the Rupsha-only city rule")
    check("NOT verifiable" in s36 and "no world-state record" in s36,
          "§3.6 records the haggle as unverified, not faked")
    check("No household" in s36,
          "§3.6 states a character with no household cannot verify")
    check("does **not** open photo mode" in s36,
          "§3.6 states completing 2.3 does not open the DA gate")
    check("not** paid by this writer" in s36,
          "§3.6 states the 500 NCr + reputation is Phase 6 work")
    check("**Implementation (Unit EO" in gdd04,
          "GDD-04 §3.6 carries the EO implementation note")

    # 6. The dialogue doc is updated.
    check("35 mission-condition nodes" in gdd15,
          "GDD-15 §13.6 counts 35 mission-condition nodes")
    check("dlg_2_3_offer" in gdd15 and "dlg_2_3_return" in gdd15,
          "GDD-15 §13.6 lists the 2.3 table rows")
    check("6 × 2.3" in gdd15,
          "GDD-15 §13.6 records the 2.3 tree adding 6 nodes")

    # 7. The validator checks the new tree.
    check("mission_2_3_market_run" in validator,
          "validate_data.py checks the 2.3 tree")

    # 8. The tests prove the condition.
    check("class TestMission23" in tests,
          "test_missions.py has the 2.3 edge tests (EO)")
    check("test_no_household_cannot_verify" in tests,
          "test_missions.py tests the no-household refusal")
    check("test_shibnagar_household_does_not_verify" in tests,
          "test_missions.py tests the Shibnagar refusal")
    check("test_2_3_completes_only_with_a_rupsha_food_purchase"
          in suite,
          "the DS suite tests 2.3 completing only on a Rupsha food "
          "purchase")
    check("test_2_3_does_not_complete_for_a_shibnagar_household"
          in suite,
          "the DS suite tests 2.3 not completing for Shibnagar")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
