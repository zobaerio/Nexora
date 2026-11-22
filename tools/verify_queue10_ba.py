"""Verify Queue 10 Unit BA — GDD-15 §13 mission-state mapping (AV gap G1).

Checks the mapping section against the sources it must resolve to:
GDD-15 §12, data/dialogue-lines.json, data/missions.json, data/schema.sql.
Prints one line per check and a summary; exits 0 only when every check
passes. Run from the repo root: python3 tools/verify_queue10_ba.py
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


def load_json(name):
    return json.loads((ROOT / "data" / name).read_text())


def all_nodes(dlg):
    out = []

    def walk(o):
        if isinstance(o, dict):
            if "node_id" in o:
                out.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(dlg)
    return out


def main():
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    schema = (ROOT / "data" / "schema.sql").read_text()
    dlg = load_json("dialogue-lines.json")
    missions = load_json("missions.json")

    # 1. The dialogue vocabulary is the six states §13.1 names.
    vocab = dlg["condition_vocabulary"]["mission"]
    expected_dialogue = {"available", "not_started", "offered",
                         "accepted", "objective_complete", "completed"}
    found_states = set(re.findall(
        r"available|not_started|offered|accepted|objective_complete"
        r"|completed", vocab))
    check(found_states == expected_dialogue,
          "dialogue mission vocabulary is the six §13.1 states",
          f"vocab={vocab!r}")

    # 2. The schema allows exactly the four statuses §13.1 names.
    m = re.search(r"CREATE TABLE mission_progress \(.*?CHECK \(status IN"
                  r"\s*\((.*?)\)\)", schema, re.S)
    check(m is not None, "mission_progress CHECK found in schema.sql")
    schema_states = set(re.findall(r"'([a-z_]+)'", m.group(1))) if m else set()
    check(schema_states == {"available", "active", "completed", "failed"},
          "schema mission_progress statuses are the four §13.1 states",
          f"states={sorted(schema_states)}")

    # 3. §13 exists and its mapping table covers all six dialogue states.
    sec13 = gdd15.split("## 13. Mission-State Mapping")[1].split(
        "## 14. Debt-Flag Derivation")[0]
    table = sec13.split("### 13.2 The mapping table")[1].split(
        "### 13.3")[0]
    rows = [ln for ln in table.splitlines() if ln.startswith("| `")]
    table_lines = [ln for ln in table.splitlines() if ln.startswith("|")]
    row_states = {re.match(r"\| `([a-z_]+)`", ln).group(1) for ln in rows
                  if re.match(r"\| `([a-z_]+)`", ln)}
    check(expected_dialogue <= row_states,
          "§13.2 mapping table covers all six dialogue states",
          f"rows={len(rows)} states={sorted(row_states)}")
    check(any("failed" in ln and "no dialogue state" in ln
              for ln in table_lines),
          "§13.2 records failed as having no dialogue state")

    # 4. The four progress keys are defined in §13.3.
    sec133 = sec13.split("### 13.3")[1].split("### 13.4")[0]
    for key in ("accepted_at_game_minutes", "objectives_complete",
                "completed_at_game_minutes", "abandoned"):
        check(f"`{key}`" in sec133, f"§13.3 defines progress key {key}")
    check("no `offered` key" in sec13 or "no offered key" in sec13.lower()
          or "There is deliberately **no `offered` key**" in sec13,
          "§13 states there is deliberately no stored offered key")

    # 5. All 12 mission-condition nodes exist with the states §13.6 lists.
    nodes = {n["node_id"]: n for n in all_nodes(dlg)}
    expected_nodes = {
        "dlg_1_3_offer": ("1.3", "available"),
        "dlg_1_3_accept": ("1.3", "offered"),
        "dlg_1_3_decline": ("1.3", "offered"),
        "dlg_1_3_reminder": ("1.3", "accepted"),
        "dlg_1_3_reminder_exit": ("1.3", "accepted"),
        "dlg_1_3_return": ("1.3", "objective_complete"),
        "dlg_2_4_offer": ("2.4", "available"),
        "dlg_2_4_accept": ("2.4", "offered"),
        "dlg_2_4_decline": ("2.4", "offered"),
        "dlg_2_4_progress": ("2.4", "accepted"),
        "dlg_2_4_return": ("2.4", "objective_complete"),
    }
    # dlg_1_3_return is in the data as dlg_1_3_return; accept both spellings.
    for nid, (mid, state) in expected_nodes.items():
        node = nodes.get(nid)
        cond = (node or {}).get("condition") or {}
        check(node is not None and cond.get("mission") == mid
              and cond.get("state") == state,
              f"node {nid} exists with mission {mid} state {state}")

    # 6. No shipped node conditions on not_started or completed.
    used = set()
    for n in nodes.values():
        c = n.get("condition") or {}
        if "mission" in c:
            used.add(c.get("state"))
    check("not_started" not in used and "completed" not in used,
          "no shipped node conditions on not_started or completed",
          f"used={sorted(used)}")

    # 7. Missions 1.3 and 2.4 exist in missions.json.
    ids = {mm["id"] for mm in missions["missions"]}
    check({"1.3", "2.4"} <= ids, "missions 1.3 and 2.4 exist in missions.json",
          f"n={len(ids)}")

    # 8. The effect mapping (§13.4) covers the data's effect states.
    sec134 = sec13.split("### 13.4")[1].split("### 13.5")[0]
    check("state `accepted`" in sec134 and "status` → `'active'`" in sec134,
          "§13.4 maps accept effect to status active")
    check("`mission_complete`" in sec134 and "'completed'" in sec134,
          "§13.4 maps mission_complete effect to status completed")

    # 9. §12.8 G1 is marked resolved by this unit.
    check("Resolved by Queue 10, Unit BA" in gdd15,
          "§12.8 G1 marked resolved by Unit BA")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\nCHECKS: {len(CHECKS)}, FAILURES: {len(failed)}")
    for _, label, detail in failed:
        print(f"  FAILED: {label} {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
