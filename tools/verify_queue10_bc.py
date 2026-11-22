"""Verify Queue 10 Unit BC — favour generation contract (AV gap G2).

Checks the contract against the sources it must resolve to:
GDD-04 §3, GDD-15 §12, data/dialogue-lines.json, data/missions.json.
Prints one line per check and a summary; exits 0 only when every
check passes. Run from the repo root: python3 tools/verify_queue10_bc.py
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
    gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md").read_text()
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    dlg = load_json("dialogue-lines.json")
    missions = load_json("missions.json")

    # 1. The contract (§3.1) exists in GDD-04 and names all five types.
    sec31 = gdd04.split("### 3.1 Favour Generation Contract")[1].split(
        "## 4. Free-Roam Rules")[0]
    types = [t["type"] for t in missions["side_mission_types"]]
    check(len(types) == 5, "missions.json carries five side-mission types",
          f"types={types}")
    for t in types:
        check(t in sec31, f"§3.1 contract covers side-mission type {t}")

    # 2. No favour invents a missions.json id: no mission id starts with
    # 'side:', and the contract's instance key is a runtime key, not a
    # mission id.
    ids = {mm["id"] for mm in missions["missions"]}
    check(not any(i.startswith("side:") for i in ids),
          "no missions.json id is a generated favour key")
    check("side:<type>:<giver_character_id>:<generated_at_game_minutes>"
          in sec31,
          "§3.1 defines the runtime instance-key format")
    check("never receives a `missions.json` id" in sec31,
          "§3.1 states a favour never receives a missions.json id")

    # 3. The reward patterns in §3.1 match missions.json §3 verbatim.
    for t in missions["side_mission_types"]:
        check(t["reward_pattern"] in sec31,
              f"§3.1 quotes the {t['type']} reward pattern verbatim",
              t["reward_pattern"])

    # 4. The favour topic nodes exist and condition only on favour_available.
    nodes = {n["node_id"]: n for n in all_nodes(dlg)}
    for nid, val in (("dlg_topic_favour", True),
                     ("dlg_topic_favour_none", False)):
        node = nodes.get(nid)
        check(node is not None, f"favour node {nid} exists")
        cond = (node or {}).get("condition") or {}
        check(cond.get("favour_available") is val,
              f"node {nid} conditions on favour_available={val}")

    # 5. The ungeneratable types are named, with their missing record.
    check("find a lost item" in sec31.lower()
          and "Ungeneratable" in sec31,
          "§3.1 marks find-a-lost-item ungeneratable (no record)")
    check("Discovery" in sec31 and "no discovery-progress record" in sec31,
          "§3.1 marks discovery ungeneratable (no progress record)")

    # 6. favour_available evaluation: deterministic order, one per
    # conversation, no random pick.
    check("in §3 table order" in sec31,
          "§3.1 fixes the deterministic §3 table-order evaluation")
    check("One favour per conversation" in sec31,
          "§3.1 states one favour per conversation")
    check("no random pick" in sec31.lower()
          or "no random pick (GDD-15" in sec31,
          "§3.1 forbids a random pick")

    # 7. GDD-15 §15 exists and points to the contract as authoritative.
    check("## 15. Favour Topic Note" in gdd15,
          "GDD-15 §15 favour topic note exists")
    sec15 = gdd15.split("## 15. Favour Topic Note")[1].split(
        "## 16. Dialogue Effect Functions")[0]
    check("GDD-04-MISSIONS-AND-PROGRESSION.md` §3.1" in sec15,
          "§15 points to GDD-04 §3.1 as the authoritative contract")
    check("side:<type>:<giver>:<generated_at_game_minutes>" in sec15,
          "§15 repeats the instance-key format")

    # 8. §12.8 G2 is marked resolved by this unit.
    check("Resolved by Queue 10, Unit BC" in gdd15,
          "§12.8 G2 marked resolved by Unit BC")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\nCHECKS: {len(CHECKS)}, FAILURES: {len(failed)}")
    for _, label, detail in failed:
        print(f"  FAILED: {label} {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
