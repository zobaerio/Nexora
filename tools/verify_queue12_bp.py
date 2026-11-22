"""Verify Queue 12 Unit BP — GDD-15 §16.2 goals-node restructure.

Checks the restructure against the sources it must resolve to:
GDD-01 §2.2 (goal stack cap), GDD-15 §7/§12.4/§16.2,
data/dialogue-lines.json, tools/validate_data.py.
Prints one line per check and a summary; exits 0 only when every check
passes. Run from the repo root: python3 tools/verify_queue12_bp.py
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


def effects_of(node):
    out = list(node.get("effects", []))
    for ln in node.get("lines", []):
        out.extend(ln.get("effects", []))
    return out


def main():
    gdd01 = (ROOT / "docs" / "GDD-01-LIFE-AND-DATA-MODEL.md").read_text()
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    dlg = json.loads((ROOT / "data" / "dialogue-lines.json").read_text())
    validator = (ROOT / "tools" / "validate_data.py").read_text()

    goals = dlg["topics"]["ask_about_goals"]["nodes"]
    by_id = {n["node_id"]: n for n in goals}
    help_node = by_id["dlg_topic_goals_help"]
    accept_node = by_id["dlg_topic_goals_accepted"]
    decline_node = by_id["dlg_topic_goals_declined"]

    # 1. The help node no longer fires propose_goal on entry.
    check(not any(e.get("type") == "propose_goal"
                  for e in effects_of(help_node)),
          "dlg_topic_goals_help carries no propose_goal on entry")

    # 2. The help node's line is the proposal itself, with no effect.
    check(any("<life_goal>" in ln["text"] for ln in help_node["lines"]),
          "help line states the NPC's goal (the proposal itself)")
    check(all(e.get("type") == "none"
              for ln in help_node["lines"] for e in ln["effects"]),
          "help lines carry effect none only")

    # 3. Two choices: accept (stack-cap gated) + decline.
    choices = {c["next"]: c for c in help_node["choices"]}
    check(set(choices) == {"dlg_topic_goals_accepted",
                           "dlg_topic_goals_declined"},
          "help node has exactly accept + decline choices",
          f"choices={sorted(choices)}")
    acc = choices["dlg_topic_goals_accepted"]
    check(acc.get("condition", {}).get("goals_full") is False,
          "accept choice is hidden when the goal stack is full")
    check(choices["dlg_topic_goals_declined"].get("condition", {})
          .get("always") is True,
          "decline choice is always offered")
    check(all(c["text"].strip() for c in help_node["choices"]),
          "choice labels are authored text, not empty")

    # 4. The accept node carries propose_goal (line + node, the shipped
    #    pattern — the format has no effect field on choices).
    check(any(e.get("type") == "propose_goal"
              and e.get("goal_ref") == "npc_life_goal"
              for e in accept_node["lines"][0]["effects"]),
          "accept node's line carries propose_goal (npc_life_goal)")
    check(any(e.get("type") == "propose_goal"
              for e in accept_node["effects"]),
          "accept node's effects carry propose_goal")

    # 5. The decline node writes nothing.
    check(all(e.get("type") == "none" for e in effects_of(decline_node)),
          "decline node writes nothing (effect none)")

    # 6. The goals_full key is documented and guarded.
    check("goals_full" in dlg["condition_vocabulary"],
          "condition_vocabulary documents goals_full")
    check('"goals_full"' in validator,
          "validate_data.py guards goals_full")

    # 7. GDD-01 §2.2 stack cap: 1 life + up to 2 stage goals.
    check("max 3 active" in gdd01,
          "GDD-01 §2.2 caps the stack at 3 active goals")
    check("up to 2" in gdd01 and "Stage goals" in gdd01,
          "GDD-01 §2.2 allows up to 2 stage goals")

    # 8. §16.2 records the fix as applied by Unit BP.
    s162 = gdd15.split("### 16.2 ")[1].split("### 16.3 ")[0]
    check("Data fix applied (Queue 12, Unit BP" in s162,
          "§16.2 records the restructure as applied by Unit BP")
    check("dlg_topic_goals_accepted" in s162
          and "dlg_topic_goals_declined" in s162,
          "§16.2 names the accept + decline nodes")
    check("effects on nodes and lines, not on choices" in s162,
          "§16.2 states why the effect sits on the accept node")

    # 9. §12.8 G7 records the restructure as applied.
    g7 = gdd15.split("**G7 — Goal proposal")[1].split("- **G8")[0]
    check("Restructure applied by Queue 12, Unit BP" in g7,
          "§12.8 G7 records the restructure as applied")

    # 10. §12.4 propose_goal row no longer says "None exists".
    row = re.search(r"\| `propose_goal` \|.*?\n", gdd15)
    check(row is not None and "None exists" not in row.group(0),
          "§12.4 propose_goal row no longer says None exists")
    check(row is not None and "Unit BP" in row.group(0),
          "§12.4 row points at the BP data fix")

    # 11. No new goal type is invented; the proposal stays a stage goal.
    check("stage" in s162 and "never `life`" in s162,
          "proposed goal stays kind stage, never life")
    check("goal_ref" in json.dumps(accept_node)
          and "npc_life_goal" in json.dumps(accept_node),
          "accept proposes the NPC's own life goal, no invented type")

    # 12. validate_data.py carries the goals-help check.
    check("def check_goals_help_restructure" in validator,
          "validate_data.py carries the goals-help check")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed; "
          f"{len(failed)} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
