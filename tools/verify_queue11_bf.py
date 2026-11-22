"""Verify Queue 11 Unit BF — GDD-15 §17 edge selection (AV gap G4).

Checks the selection section against the sources it must resolve to:
GDD-01 §6.1/§6.2, GDD-15 §3/§12, data/dialogue-lines.json,
tools/sim/relationships.py.
Prints one line per check and a summary; exits 0 only when every check
passes. Run from the repo root: python3 tools/verify_queue11_bf.py
"""
import json
import re
import subprocess
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
    gdd01 = (ROOT / "docs" / "GDD-01-LIFE-AND-DATA-MODEL.md").read_text()
    rel = (ROOT / "tools" / "sim" / "relationships.py").read_text()
    dlg = load_json("dialogue-lines.json")

    # 1. §17 exists, headed Unit BF, Queue 11, resolving G4.
    m17 = re.search(r"## 17\. Edge Selection for the Greeting Band "
                    r"\(AV gap G4 — resolved\)\n\n\*\*Unit BF · Queue 11",
                    gdd15)
    check(m17 is not None, "GDD-15 §17 exists, headed Unit BF, Queue 11")

    # 2. §12.8 G4 is marked resolved by BF.
    check("**Resolved by Queue 11, Unit BF (GDD-15 §17):**" in gdd15,
          "§12.8 G4 marked resolved by Queue 11 Unit BF")

    # 3. The priority table lists all 13 GDD-01 §6.1 types exactly once.
    gdd01_types = set(
        re.search(r"`(parent, child, sibling, partner, spouse, "
                  r"ex_partner, friend, best_friend, colleague, "
                  r"employer, employee, rival, acquaintance)`",
                  gdd01.split("### 6.1 Kinship")[1].split("### 6.2")[0]
                  ).group(1).split(", "))
    sec17 = gdd15.split("\n## 17. ")[1].split("\n## 18. ")[0]
    table_types = re.findall(
        r"\| \d+ \| `(parent|child|sibling|partner|spouse|ex_partner|"
        r"friend|best_friend|colleague|employer|employee|rival|"
        r"acquaintance)` \|", sec17)
    check(set(table_types) == gdd01_types and len(table_types) == 13,
          "priority table lists all 13 GDD-01 §6.1 types exactly once",
          f"types={len(table_types)}")

    # 4. Priority order: spouse first, ex_partner last.
    order = {t: i for i, t in enumerate(table_types)}
    check(order.get("spouse") == 0 and order.get("ex_partner") == 12,
          "spouse is priority 1, ex_partner is priority 13")
    check(order.get("rival", 99) > order.get("colleague", 0),
          "rival ranks below colleague (a conflict never reframes the pair)")
    check(order.get("partner") == 1 and order.get("best_friend") == 2,
          "partner 2nd, best_friend 3rd")

    # 5. The priority order is labelled as this unit's decision.
    check("The priority order is this unit's decision" in sec17,
          "priority order labelled as this unit's decision")

    # 6. get_edge() requires a relation_type.
    check("def get_edge(store, a, b, relation_type):" in rel,
          "get_edge() requires relation_type")

    # 7. adjust_scores() with no relation_type moves every edge a->b.
    check('"""Move the scores on every edge a->b (or one type).' in rel,
          "adjust_scores() unscoped moves every edge a->b")

    # 8. §17.3 binds drift to the selected edge (never unscoped).
    check("never unscoped" in sec17
          and "relation_type` = the selected type" in sec17,
          "drift target is the selected edge, never unscoped")

    # 9. Symmetric mirroring still applies for symmetric selected types.
    check('SYMMETRIC = ("spouse", "sibling", "friend", "partner",' in rel,
          "SYMMETRIC includes spouse/sibling/friend/partner")

    # 10. §17.3 lists all five reads/writes from the selected edge.
    for item in ("Greeting band", "relationship_mean_min", "respect_min",
                 "Drift target", "Semantic flags"):
        check(item in sec17, f"§17.3 covers {item}")

    # 11. set_flag/get_flag take a relation_type (flags live per edge).
    check("def set_flag(store, a, b, relation_type, key, value):" in rel,
          "set_flag() takes relation_type")
    check("def get_flag(store, a, b, relation_type, key, default=None):"
          in rel, "get_flag() takes relation_type")

    # 12. No-edge and zero-score cases read neutral.
    check("No NPC→player edge at all** → band `neutral`" in sec17
          or "No NPC→player edge at all" in sec17,
          "no edge reads neutral")
    check("Selected edge exists with the sim's default scores" in sec17,
          "zero-score edge reads neutral like no edge")

    # 13. The return edge is never read for the greeting (GDD-01 §6.2).
    check("The return edge is never read for the greeting" in sec17,
          "return edge never read for the greeting")

    # 14. §17.5 worked examples cover the four cases.
    for case in ("Spouse + colleague", "Colleague + rival",
                 "`ex_partner` only", "No edge"):
        check(case in sec17, f"worked example: {case}")

    # 15. The flag-visibility limit is recorded, not papered over.
    check("flags on a non-selected edge are invisible to dialogue" in sec17,
          "flag-visibility limit recorded in §17.3")

    # 16. Greeting bands exist in the data (five bands, §3 thresholds).
    bands = {b["band"]: b for b in dlg["greeting_bands"]}
    check(set(bands) == {"close", "warm", "neutral", "wary", "hostile"},
          "data carries the five greeting bands")
    check(bands["close"]["mean_trust_affection_min"] == 60
          and bands["hostile"]["mean_trust_affection_max"] == -60,
          "band thresholds match GDD-15 §3 (close >= 60, hostile <= -60)")

    # 17. relationship_mean_min / respect_min are in the condition vocabulary.
    vocab = dlg["condition_vocabulary"]
    check("relationship_mean_min" in vocab and "respect_min" in vocab,
          "condition vocabulary has relationship_mean_min and respect_min")

    # 18. A shipped node uses relationship_mean_min 40 (dlg_2_4_entry).
    nodes = {n["node_id"]: n for n in all_nodes(dlg)}
    check(nodes.get("dlg_2_4_entry", {}).get("condition", {}).get(
        "relationship_mean_min") == 40,
        "dlg_2_4_entry requires relationship_mean_min 40")

    # 19. §12.3 still says "the same edge" — the ambiguity §17 resolves.
    sec12 = gdd15.split("### 12.3 Condition evaluation")[1].split(
        "### 12.4")[0]
    check("the same edge" in sec12 or "Same edge" in sec12,
          "§12.3 reads 'the same edge' (the ambiguity §17 resolves)")

    # 20. §17 names the sim functions it binds.
    for fn in ("get_edge(store", "adjust_scores()", "set_flag()",
               "get_flag()"):
        check(fn in sec17, f"§17 names {fn}")

    # 21. Gap G4 resolution statement present.
    check("**Gap G4 is resolved by this section**" in sec17,
          "§17 states gap G4 resolved")

    # 22. No sim code changed by this unit (design only).
    diff = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "--name-only"],
        capture_output=True, text=True).stdout.splitlines()
    check(not any(p.startswith("tools/sim/") for p in diff),
          "no tools/sim/ file changed (design only)",
          f"changed={diff}")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed, "
          f"{len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
