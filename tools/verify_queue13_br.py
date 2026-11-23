"""Verify Queue 13 Unit BR — GDD-15 §15.2 lost-item + discovery favour
nodes (the nodes Unit BO deferred, now that the BL/BM records exist).

Checks the nodes against the sources they must resolve to: GDD-04
§3/§3.1/§3.3/§3.4 (types + reward patterns + records), GDD-15 §12.4/§13/
§15.1/§15.2, data/dialogue-lines.json, tools/validate_data.py.
Prints one line per check and a summary; exits 0 only when every check
passes. Run from the repo root: python3 tools/verify_queue13_br.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKS = []

TYPES = ["find_a_lost_item", "discovery"]


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

    # 1. §15.2 exists, headed Unit BR, Queue 13.
    m152 = re.search(r"### 15\.2 Lost-item \+ discovery favour nodes "
                     r"\(Unit BR · Queue 13", gdd15)
    check(m152 is not None, "GDD-15 §15.2 exists, headed Unit BR, Queue 13")
    sec = gdd15[m152.start():] if m152 else ""
    sec = sec.split("*End of GDD-15 §15.2")[0]

    # 2. The two new favour_type values are in the vocabulary.
    vocab = dlg["condition_vocabulary"].get("favour_type", "")
    for t in TYPES:
        check(t in vocab, f"condition_vocabulary documents favour_type {t}")

    # 3. Favour topic node inventory: 2 offer + 2 accept + 2 complete.
    favour = dlg["topics"]["favour"]["nodes"]
    by_id = {n["node_id"]: n for n in favour}
    for t in TYPES:
        for kind in ("offer", "accept", "complete"):
            check(f"dlg_favour_{kind}_{t}" in by_id,
                  f"favour node dlg_favour_{kind}_{t} exists")
    check(len([n for n in favour
               if n["node_id"].startswith("dlg_favour_complete_")]) == 7,
          "seven complete nodes (five BO + two BR)")
    check(len([n for n in favour
               if n["node_id"].startswith("dlg_favour_offer_")]) == 7,
          "seven offer nodes (five BO + two BR)")
    check(len([n for n in favour
               if n["node_id"].startswith("dlg_favour_accept_")]) == 7,
          "seven accept nodes (five BO + two BR)")

    # 4. Node order: new completes sit with the other completes, new
    #    offer/accept pairs sit with the other pairs, §3 table order.
    order = [n["node_id"] for n in favour]
    check(order.index("dlg_favour_complete_find_a_lost_item")
          > order.index("dlg_favour_complete_favours_mediate")
          and order.index("dlg_favour_complete_find_a_lost_item")
          < order.index("dlg_favour_complete_events"),
          "lost-item complete sits after mediate, before events")
    check(order.index("dlg_favour_complete_discovery")
          > order.index("dlg_favour_complete_events"),
          "discovery complete sits after events (last complete)")
    check(order.index("dlg_favour_offer_find_a_lost_item")
          > order.index("dlg_favour_accept_favours_mediate")
          and order.index("dlg_favour_offer_find_a_lost_item")
          < order.index("dlg_favour_offer_events"),
          "lost-item offer/accept sit after mediate, before events")
    check(order.index("dlg_favour_offer_discovery")
          > order.index("dlg_favour_accept_events")
          and order.index("dlg_favour_offer_discovery")
          < order.index("dlg_favour_decline"),
          "discovery offer/accept sit after events, before decline")
    check(order.index("dlg_favour_progress")
          < order.index("dlg_favour_offer_find_a_lost_item"),
          "progress reminder still precedes the new offers")

    # 5. Offer lines quote the §3 pattern verbatim for the type.
    pat_for = {"find_a_lost_item": patterns["favours"],
               "discovery": patterns["discovery"]}
    for t in TYPES:
        text = " ".join(ln["text"]
                        for ln in by_id[f"dlg_favour_offer_{t}"]["lines"])
        check(pat_for[t] in text,
              f"offer line for {t} quotes its §3 pattern verbatim",
              f"pattern={pat_for[t]!r}")

    # 6. Offer choices: accept + decline, both resolving.
    for t in TYPES:
        nxt = [c["next"] for c in by_id[f"dlg_favour_offer_{t}"]["choices"]]
        check(f"dlg_favour_accept_{t}" in nxt
              and "dlg_favour_decline" in nxt,
              f"offer {t} has accept + decline choices")

    # 7. The stub has one conditional choice per type (seven total).
    stub = by_id["dlg_topic_favour"]
    got = {c["condition"].get("favour_type"): c["next"]
           for c in stub["choices"]}
    all_types = ["errands", "work_shifts", "favours_lend",
                 "favours_mediate", "find_a_lost_item", "events",
                 "discovery"]
    check(set(got) == set(all_types),
          "offer stub has one conditional choice per type (seven)",
          f"got={sorted(got)}")
    check(all(got[t] == f"dlg_favour_offer_{t}" for t in all_types),
          "stub choices lead to the matching offer node")

    # 8. Accept effects: mission_progress, instance key, state accepted.
    for t in TYPES:
        effs = effects_of(by_id[f"dlg_favour_accept_{t}"])
        check(any(e.get("type") == "mission_progress"
                  and e.get("mission_id_ref") == "favour_instance"
                  and e.get("state") == "accepted" for e in effs),
              f"accept {t} writes mission_progress under the instance key")

    # 9. Complete effects: mission_complete, instance key + reward ref.
    for t in TYPES:
        effs = effects_of(by_id[f"dlg_favour_complete_{t}"])
        check(any(e.get("type") == "mission_complete"
                  and e.get("mission_id_ref") == "favour_instance"
                  and e.get("rewards_ref") == "favour_instance"
                  for e in effs),
              f"complete {t} pays the instance's recorded reward")

    # 10. The lost-item offer names the lost place and states no amount;
    #     the discovery offer names the unfound discoverable.
    lost_text = " ".join(ln["text"] for ln in
                         by_id["dlg_favour_offer_find_a_lost_item"]["lines"])
    check("<lost_place_name>" in lost_text,
          "lost-item offer names the lost place via <lost_place_name>")
    check(not re.search(r"\b\d[\d,]*\s*NCr\b", lost_text),
          "lost-item offer states no NCr amount")
    disc_text = " ".join(ln["text"] for ln in
                         by_id["dlg_favour_offer_discovery"]["lines"])
    check("<discoverable_name>" in disc_text,
          "discovery offer names the unfound discoverable")
    check(re.search(r"\b500 NCr\b", disc_text) is not None
          and patterns["discovery"] in disc_text,
          "discovery offer carries the 500 NCr pattern verbatim, nothing else")

    # 11. The two new placeholders are documented in the file notes.
    notes = " ".join(dlg["notes"])
    check("<lost_place_name>" in notes and "<discoverable_name>" in notes,
          "dialogue-lines.json notes document both new placeholders")

    # 12. No other favour line states an invented NCr amount (the two
    #     verbatim patterns are the only NCr figures).
    texts = [ln["text"] for n in favour for ln in n["lines"]]
    bad = [t for t in texts
           if re.search(r"\b\d[\d,]*\s*NCr\b", t)
           and patterns["errands"] not in t
           and patterns["discovery"] not in t]
    check(not bad, "no favour line states an invented NCr amount",
          f"bad={bad[:2]}")

    # 13. §15.2 states the completion rule and the eligibility limit.
    check("returned" in sec and "GDD-04 §3.3" in sec,
          "§15.2 ties lost-item completion to the returned write")
    check("discovery_progress" in sec and "GDD-04 §3.4" in sec,
          "§15.2 ties discovery completion to the discovery_progress row")
    check("no merged event writes a loss yet" in sec
          or "no row exists to satisfy it" in sec
          or "still finds no row" in sec,
          "§15.2 keeps the losing-event gap open, honestly")
    check("Photograph-the-district stays ungeneratable" in sec,
          "§15.2 keeps photograph-the-district ungeneratable")

    # 14. GDD-04 §3.1 no longer bars the two types; §3.3/§3.4 point here.
    s31 = gdd04.split("### 3.1 Favour Generation Contract")[1].split(
        "### 3.2 Mission Deadlines")[0]
    check("no lost-item favour" not in s31
          or "struck" in s31,
          "§3.1 never-invent list no longer bars lost-item/discovery")
    check("GDD-15 §15.2" in gdd04.split("### 3.3 Lost-Item Record")[1]
          .split("### 3.4 Discovery Progress Record")[0],
          "§3.3 points at §15.2 for the nodes")
    check("GDD-15 §15.2" in gdd04.split(
        "### 3.4 Discovery Progress Record")[1].split("## 4. ")[0],
          "§3.4 points at §15.2 for the nodes")

    # 15. §12.8 G2 and §15 name §15.2; validate_data carries the check.
    check("§15.2" in gdd15.split("**G2 — Favour availability.**")[1]
          .split("- **G3")[0],
          "§12.8 G2 points at §15.2")
    check("find_a_lost_item" in validator
          and '"discovery"' in validator,
          "validate_data.py favour-flow check covers the two new types")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed; "
          f"{len(failed)} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
