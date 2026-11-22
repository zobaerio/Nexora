"""Verify Queue 12 Unit BO — GDD-15 §15.1 favour offer/accept/complete
nodes (favour flow for the generatable types).

Checks the flow against the sources it must resolve to: GDD-04 §3/§3.1
(types + reward patterns + instance key), GDD-15 §12.4/§13/§15,
data/dialogue-lines.json, tools/validate_data.py.
Prints one line per check and a summary; exits 0 only when every check
passes. Run from the repo root: python3 tools/verify_queue12_bo.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKS = []

TYPES = ["errands", "work_shifts", "favours_lend", "favours_mediate",
         "events"]


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
    gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md").read_text()
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    dlg = json.loads((ROOT / "data" / "dialogue-lines.json").read_text())
    validator = (ROOT / "tools" / "validate_data.py").read_text()
    missions = json.loads((ROOT / "data" / "missions.json").read_text())
    patterns = {s["type"]: s["reward_pattern"] for s in
                missions["side_mission_types"]}

    # 1. §15.1 exists, headed Unit BO, Queue 12.
    m151 = re.search(r"### 15\.1 The favour flow — offer / accept / "
                     r"complete nodes \(Unit BO · Queue 12", gdd15)
    check(m151 is not None, "GDD-15 §15.1 exists, headed Unit BO, Queue 12")
    sec = gdd15[m151.start():] if m151 else ""
    sec = sec.split("*End of GDD-15 §15")[0]

    # 2. The two new condition keys are documented and guarded.
    for key in ("favour_type", "favour_state"):
        check(key in dlg["condition_vocabulary"],
              f"condition_vocabulary documents {key}")
        check(f'"{key}"' in validator or f"'{key}'" in validator,
              f"validate_data.py guards {key}")

    # 3. Favour topic node inventory: 5 offer + 5 accept + 5 complete +
    #    progress + decline + the two shipped stubs.
    favour = dlg["topics"]["favour"]["nodes"]
    by_id = {n["node_id"]: n for n in favour}
    for t in TYPES:
        for kind in ("offer", "accept", "complete"):
            check(f"dlg_favour_{kind}_{t}" in by_id,
                  f"favour node dlg_favour_{kind}_{t} exists")
    check("dlg_favour_progress" in by_id, "reminder node exists")
    check("dlg_favour_decline" in by_id, "shared decline node exists")
    check("dlg_topic_favour" in by_id and "dlg_topic_favour_none" in by_id,
          "shipped favour stubs kept")

    # 4. No offer/accept/complete nodes for find-a-lost-item/discovery.
    for t in ("find_a_lost_item", "discovery"):
        hit = [n["node_id"] for n in favour
               if t in n["node_id"]
               or n.get("condition", {}).get("favour_type") == t]
        check(not hit, f"no favour flow nodes for {t} (follow-up unit)",
              f"hit={hit}")

    # 5. Node order: complete nodes first, then progress, then the stub.
    order = [n["node_id"] for n in favour]
    first_complete = min(order.index(f"dlg_favour_complete_{t}")
                         for t in TYPES)
    check(order.index("dlg_favour_progress") > first_complete,
          "progress node sits after the complete nodes")
    check(order.index("dlg_topic_favour")
          > order.index("dlg_favour_progress"),
          "offer stub sits after the progress node (precedence)")

    # 6. Offer lines quote the §3 pattern verbatim for the type.
    pat_for = {"errands": patterns["errands"],
               "work_shifts": patterns["work_shifts"],
               "favours_lend": patterns["favours"],
               "favours_mediate": patterns["favours"],
               "events": patterns["events"]}
    for t in TYPES:
        text = " ".join(ln["text"]
                        for ln in by_id[f"dlg_favour_offer_{t}"]["lines"])
        check(pat_for[t] in text,
              f"offer line for {t} quotes its §3 pattern verbatim",
              f"pattern={pat_for[t]!r}")

    # 7. Offer choices: accept + decline, both resolving.
    for t in TYPES:
        nxt = [c["next"] for c in by_id[f"dlg_favour_offer_{t}"]["choices"]]
        check(f"dlg_favour_accept_{t}" in nxt
              and "dlg_favour_decline" in nxt,
              f"offer {t} has accept + decline choices")

    # 8. The stub has exactly one choice per type, conditioned on it.
    stub = by_id["dlg_topic_favour"]
    got = {c["condition"].get("favour_type"): c["next"]
           for c in stub["choices"]}
    check(set(got) == set(TYPES),
          "offer stub has one conditional choice per type",
          f"got={sorted(got)}")
    check(all(got[t] == f"dlg_favour_offer_{t}" for t in TYPES),
          "stub choices lead to the matching offer node")

    # 9. Accept effects: mission_progress, instance key, state accepted.
    for t in TYPES:
        effs = effects_of(by_id[f"dlg_favour_accept_{t}"])
        check(any(e.get("type") == "mission_progress"
                  and e.get("mission_id_ref") == "favour_instance"
                  and e.get("state") == "accepted" for e in effs),
              f"accept {t} writes mission_progress under the instance key")

    # 10. Complete effects: mission_complete, instance key + reward ref.
    for t in TYPES:
        effs = effects_of(by_id[f"dlg_favour_complete_{t}"])
        check(any(e.get("type") == "mission_complete"
                  and e.get("mission_id_ref") == "favour_instance"
                  and e.get("rewards_ref") == "favour_instance"
                  for e in effs),
              f"complete {t} pays the instance's recorded reward")

    # 11. No new line states an invented NCr amount (the errand pattern
    #     is the only NCr figure, and it is quoted verbatim).
    texts = [ln["text"] for n in favour for ln in n["lines"]]
    bad = [t for t in texts
           if re.search(r"\b\d[\d,]*\s*NCr\b", t)
           and patterns["errands"] not in t]
    check(not bad, "no favour line states an invented NCr amount",
          f"bad={bad[:2]}")

    # 12. The lend accept carries no ledger effect — the loan row is
    #     the mission system's consequence (GDD-15 §20).
    lend_effs = effects_of(by_id["dlg_favour_accept_favours_lend"])
    check(not any(e.get("type") == "ledger_settlement" for e in lend_effs),
          "lend accept carries no ledger effect (mission system writes it)")
    check("loan_disburse" in sec and "GDD-15 §20" in sec,
          "§15.1 names the §20 loan consequence for lend accept")

    # 13. §15 + §15.1 state the precedence, the most-recent-instance
    #     rule, and the follow-up for lost-item/discovery nodes.
    check("completion first" in sec,
          "§15.1 states the completion > reminder > offer precedence")
    check("most recent favour instance" in sec,
          "§15.1 defines favour_state over the most recent instance")
    s15 = gdd15.split("## 15. Favour Topic Note")[1].split("## 16. ")[0]
    check("follow-up" in s15 and "GDD-04 §3.3" in s15
          and "§3.4" in s15,
          "§15 names the BL/BM follow-up for the other two types")

    # 14. §12.8 G2 now points at §15.1 for the authored flow.
    check("§15.1" in gdd15.split("**G2 — Favour availability.**")[1]
          .split("- **G3")[0],
          "§12.8 G2 points at §15.1")

    # 15. validate_data.py carries the favour-flow check and passes.
    check("def check_favour_flow_nodes" in validator,
          "validate_data.py carries the favour-flow check")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed; "
          f"{len(failed)} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
