"""Verify Queue 17 Unit DM — Mission 1.4 Dialogue Tree
(GDD-04 §2, §3.6; GDD-15 §5/§11; AO/BO patterns).

Checks the authored tree against its sources:
data/dialogue-lines.json (the dlg_1_4_* nodes), data/missions.json
(1.4 objectives/rewards/unlocks, quoted verbatim), GDD-04 §3.6
(the tree does not exist yet — this unit authors it) and
tools/validate_data.py (the generic dialogue checks cover it).
Prints one line per check and a summary; exits 0 only when every
check passes. Run from the repo root: python3 tools/verify_queue17_dm.py
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
    dlg = json.loads((ROOT / "data" / "dialogue-lines.json").read_text())
    missions = json.loads((ROOT / "data" / "missions.json").read_text())
    validator = (ROOT / "tools" / "validate_data.py").read_text()

    tree = dlg["trees"].get("mission_1_4_river_at_dusk", {})
    nodes = {n["node_id"]: n for n in tree.get("nodes", [])}
    m14 = next(m for m in missions["missions"] if m["id"] == "1.4")

    # 1. The tree exists with the AO/BO node set.
    check("mission_1_4_river_at_dusk" in dlg["trees"],
          "dialogue-lines.json has the mission_1_4_river_at_dusk tree")
    check(sorted(nodes) == sorted([
        "dlg_1_4_intro", "dlg_1_4_offer", "dlg_1_4_accept",
        "dlg_1_4_decline", "dlg_1_4_hello", "dlg_1_4_reminder",
        "dlg_1_4_reminder_exit", "dlg_1_4_return"]),
        "the tree has the 8 AO-pattern nodes",
        f"{sorted(nodes)}")
    check(tree.get("mission_id") == "1.4"
          and tree.get("title") == "The River at Dusk",
          "tree mission_id/title match missions.json 1.4")

    # 2. Rewards/objectives/unlocks are quoted verbatim.
    check(tree.get("objectives_quoted") == m14["objectives"],
          "objectives_quoted match missions.json 1.4 verbatim")
    check(tree.get("rewards_quoted") == m14["rewards"],
          "rewards_quoted match missions.json 1.4 verbatim")
    check(tree.get("unlocks_quoted") == m14["unlocks"],
          "unlocks_quoted match missions.json 1.4 verbatim")

    # 3. Conditions follow the §5 contract and the 1.3 pattern.
    check(nodes["dlg_1_4_offer"]["condition"] ==
          {"mission": "1.4", "state": "available"},
          "offer is gated on mission 1.4 available")
    check(nodes["dlg_1_4_accept"]["condition"] ==
          {"mission": "1.4", "state": "offered"},
          "accept is gated on mission 1.4 offered")
    check(nodes["dlg_1_4_reminder"]["condition"] ==
          {"mission": "1.4", "state": "accepted"},
          "reminder is gated on mission 1.4 accepted")
    check(nodes["dlg_1_4_return"]["condition"] ==
          {"mission": "1.4", "state": "objective_complete"},
          "return is gated on mission 1.4 objective_complete")

    # 4. Effects follow the §5 contract: accept writes accepted,
    # return writes mission_complete with verbatim rewards.
    accept_fx = nodes["dlg_1_4_accept"]["effects"]
    check(accept_fx == [{"type": "mission_progress",
                         "mission_id": "1.4", "state": "accepted"}],
          "accept effect is mission_progress accepted")
    ret_fx = nodes["dlg_1_4_return"]["effects"]
    check(ret_fx == [{"type": "mission_complete", "mission_id": "1.4",
                      "rewards": m14["rewards"]}],
          "return effect is mission_complete with verbatim rewards")
    check(nodes["dlg_1_4_offer"]["choices"][0]["next"]
          == "dlg_1_4_accept"
          and nodes["dlg_1_4_offer"]["choices"][1]["next"]
          == "dlg_1_4_decline",
          "offer choices go to accept / decline")

    # 5. The offer line names the objectives and the reward honestly.
    offer_text = " ".join(ln["text"] for n in tree["nodes"]
                          for ln in n["lines"]
                          if n["node_id"] == "dlg_1_4_offer")
    check("Watch the sunset from the riverfront promenade" in offer_text
          and "Visit the tea stall" in offer_text,
          "offer line names both objectives verbatim")
    check("no credits" in offer_text.lower(),
          "offer line states there are no credits (credits_ncr null)")
    check("First evening in Rupsha" in offer_text,
          "offer line names the memory-event reward")
    check("Photo mode" in offer_text
          and "Promenade leisure anchor" in offer_text,
          "offer line names both unlocks")

    # 6. No invented numbers: no NCr amount, no drift/memory weight.
    texts = [ln["text"] for n in tree["nodes"] for ln in n["lines"]]
    check(not any("NCr" in t for t in texts),
          "no 1.4 line states an NCr amount")
    all_fx = [fx for n in tree["nodes"] for fx in n["effects"]]
    check(not any(fx.get("type") == "memory_write" for fx in all_fx),
          "no memory_write with an unsourced weight (1.4 has none)")
    check(not any(fx.get("type") == "relationship_drift"
                  and n["node_id"] == "dlg_1_4_return"
                  for n in tree["nodes"] for fx in n["effects"]),
          "return carries no unsourced relationship drift")

    # 7. Every node/line carries condition + effects (§5 contract)
    # and every choice target resolves (the validator checks this
    # globally; this unit checks its own tree directly).
    check(all("condition" in n and "effects" in n
              for n in tree["nodes"]),
          "every 1.4 node carries condition + effects")
    check(all("condition" in ln and "effects" in ln
              for n in tree["nodes"] for ln in n["lines"]),
          "every 1.4 line carries condition + effects")
    check(all(c["next"] in nodes
              for n in tree["nodes"] for c in n.get("choices", [])),
          "every 1.4 choice target resolves inside the tree")

    # 8. The validator covers the tree generically.
    check("dialogue mission rewards/objectives/unlocks " in validator,
          "validate_data.py checks rewards/objectives/unlocks verbatim")
    check("mission 1.4 dialogue tree exists" in validator,
          "validate_data.py checks the 1.4 tree exists")
    check("What this contract does not do" in gdd04
          and "the offer/accept/complete nodes for 1.4 are a later"
             " unit's job" in gdd04,
          "GDD-04 §3.6 kept its honest note that the tree was missing"
          " (now authored by this unit)")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
