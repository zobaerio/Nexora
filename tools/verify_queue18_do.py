"""Verify Queue 18 Unit DO — Mission 2.1 Dialogue Tree + Completion
(GDD-04 §2, §3.6; GDD-15 §5/§11/§13; AO/BO patterns).

Checks the authored tree and condition against their sources:
data/dialogue-lines.json (the dlg_2_1_* nodes),
data/missions.json (2.1 objectives/rewards/unlocks, quoted verbatim),
data/professions.json (primary_skills[0] is the primary skill),
GDD-04 §3.6 (the 2.1 completion condition, and the correction that
no mission 1.5 exists), GDD-15 §13.6 (the mapping table covers 2.1),
tools/sim/missions.py (the verify_mission_2_1 writer), and
tools/validate_data.py (the generic dialogue checks cover the tree).
Prints one line per check and a summary; exits 0 only when every
check passes. Run from the repo root: python3 tools/verify_queue18_do.py
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
    gdd11 = (ROOT / "docs" / "GDD-11-EDUCATION.md").read_text()
    gdd03 = (ROOT / "docs" / "GDD-03-ECONOMY-AND-PROFESSIONS.md").read_text()
    dlg = json.loads((ROOT / "data" / "dialogue-lines.json").read_text())
    missions = json.loads((ROOT / "data" / "missions.json").read_text())
    profs = json.loads((ROOT / "data" / "professions.json").read_text())
    missions_py = (ROOT / "tools" / "sim" / "missions.py").read_text()
    validator = (ROOT / "tools" / "validate_data.py").read_text()

    tree = dlg["trees"].get("mission_2_1_learn_the_trade", {})
    nodes = {n["node_id"]: n for n in tree.get("nodes", [])}
    m21 = next(m for m in missions["missions"] if m["id"] == "2.1")
    ids = [m["id"] for m in missions["missions"]]

    # 1. The correction: no mission 1.5 exists anywhere.
    check("1.5" not in ids,
          "missions.json has no mission 1.5 (Level 1 is 1.1-1.4)",
          f"{len(ids)} ids, {ids[:5]}")
    check("2.1" in ids and ids.index("2.1") == 4,
          "2.1 is the next mission after 1.4 in missions.json order")
    check("there is no mission 1.5" in gdd04,
          "GDD-04 §3.6 records the no-1.5 correction")

    # 2. The tree exists with the AO/BO node set.
    check("mission_2_1_learn_the_trade" in dlg["trees"],
          "dialogue-lines.json has the mission_2_1_learn_the_trade tree")
    check(sorted(nodes) == sorted([
        "dlg_2_1_intro", "dlg_2_1_offer", "dlg_2_1_accept",
        "dlg_2_1_decline", "dlg_2_1_hello", "dlg_2_1_reminder",
        "dlg_2_1_reminder_exit", "dlg_2_1_return"]),
        "the tree has the 8 AO-pattern nodes",
        f"{sorted(nodes)}")
    check(tree.get("mission_id") == "2.1"
          and tree.get("title") == "Learn the Trade",
          "tree mission_id/title match missions.json 2.1")

    # 3. Rewards/objectives/unlocks are quoted verbatim.
    check(tree.get("objectives_quoted") == m21["objectives"],
          "objectives_quoted match missions.json 2.1 verbatim")
    check(tree.get("rewards_quoted") == m21["rewards"],
          "rewards_quoted match missions.json 2.1 verbatim")
    check(tree.get("unlocks_quoted") == m21["unlocks"],
          "unlocks_quoted match missions.json 2.1 verbatim")
    ret = nodes["dlg_2_1_return"]
    check(ret["effects"][0].get("rewards") == m21["rewards"],
          "return node pays the rewards verbatim (mission_complete)")
    check(m21["rewards"]["credits_ncr"] == 2000
          and m21["rewards"]["reputation"] == [
              {"amount": 10, "scope": "profession"}],
          "2.1 reward is 2,000 NCr + 10 profession reputation")

    # 4. Conditions follow the §5 contract and the 1.4 pattern.
    check(nodes["dlg_2_1_offer"]["condition"] ==
          {"mission": "2.1", "state": "available"},
          "offer is gated on mission 2.1 available")
    check(nodes["dlg_2_1_accept"]["condition"] ==
          {"mission": "2.1", "state": "offered"},
          "accept is gated on mission 2.1 offered")
    check(nodes["dlg_2_1_reminder"]["condition"] ==
          {"mission": "2.1", "state": "accepted"},
          "reminder is gated on mission 2.1 accepted")
    check(nodes["dlg_2_1_return"]["condition"] ==
          {"mission": "2.1", "state": "objective_complete"},
          "return is gated on mission 2.1 objective_complete")
    check(all("condition" in n and "effects" in n
              for n in tree["nodes"]),
          "every 2.1 node carries condition + effects")
    check(all("condition" in ln and "effects" in ln
              for n in tree["nodes"] for ln in n["lines"]),
          "every 2.1 line carries condition + effects")
    check(all(c["next"] in nodes
              for n in tree["nodes"] for c in n.get("choices", [])),
          "every 2.1 choice target resolves inside the tree")

    # 5. The completion condition in GDD-04 §3.6.
    s36 = gdd04.split("**Completion condition — mission 2.1")[1] \
        .split("**What this contract does not do.**")[0]
    check("primary_skills[0]" in s36,
          "§3.6 names primary_skills[0] as the primary skill")
    check("worked_with_player" in s36,
          "§3.6 names the giver condition (colleague, pair flag)")
    check("unemployed" in s36 and "second" in s36,
          "§3.6 states what does NOT verify (unemployed, second skill)")
    check("does **not** open photo mode" in s36,
          "§3.6 states completing 2.1 does not open the DA gate")
    check("2,000 NCr" in s36 and "not** paid by this writer" in s36,
          "§3.6 states the credit/reputation reward is Phase 6 work")

    # 6. The primary-skill reading is sourced, not invented.
    check("second primary skill" in gdd11,
          "GDD-11 names the second entry the second primary skill")
    check("skill 40 in the profession's primary skill" in gdd03,
          "GDD-03 §2 reads the same primary-skill slot")
    check(all(len(p.get("primary_skills", [])) >= 1
              for p in profs["professions"]),
          "every profession lists at least one primary skill")
    check(all(p["primary_skills"][0] != p["primary_skills"][1]
              for p in profs["professions"]
              if len(p["primary_skills"]) > 1),
          "first and second primary skills differ everywhere")

    # 7. The writer implements the condition.
    check("def verify_mission_2_1(" in missions_py,
          "missions.py implements verify_mission_2_1")
    check("MISSION_2_1_SKILL_LEVEL = 20" in missions_py,
          "missions.py pins the 2.1 threshold at 20")
    check("def primary_skill_of(" in missions_py
          and "def current_profession_id(" in missions_py,
          "missions.py has the primary-skill / current-profession helpers")
    check("photo_mode" not in missions_py.split(
        "def verify_mission_2_1(")[1].split("def complete_mission")[0],
        "the 2.1 verifier touches no photo-mode gate")

    # 8. GDD-15 keeps its mapping accurate.
    check("dlg_2_1_offer" in gdd15 and "dlg_2_1_return" in gdd15,
          "GDD-15 §13.6 table covers the 2.1 nodes")
    check("dlg_1_4_offer" in gdd15 and "dlg_1_4_return" in gdd15,
          "GDD-15 §13.6 table covers the 1.4 nodes (DM staleness fixed)")
    check("all 23 mission-condition nodes" in gdd15,
          "GDD-15 §13.6 counts 23 mission-condition nodes")
    counted = sum(
        1 for t in dlg["trees"].values() for n in t.get("nodes", [])
        if "mission" in n.get("condition", {}))
    check(counted == 23,
          "the data holds exactly 23 mission-condition nodes",
          f"counted {counted}")

    # 9. The validator covers the tree generically.
    check("mission 2.1 dialogue tree exists" in validator,
          "validate_data.py checks the 2.1 tree exists")
    check("mission 2.1 tree has the 8 AO-pattern nodes" in validator,
          "validate_data.py checks the 2.1 node set")
    check("mission 2.1 rewards quoted verbatim" in validator,
          "validate_data.py checks the 2.1 rewards verbatim")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
