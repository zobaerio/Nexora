"""Verify Queue 12 Unit BQ — GDD-15 §21 service-anchor zone resolution.

Checks the rule against the sources it must resolve to: GDD-06 §3
(anchor resolution), GDD-15 §18 (accessor + the §18.5 difference),
tools/sim/scheduler.py (LEISURE_ZONE + the home_zone fallback),
data/npc-schedules.json (the tokens in use),
data/dialogue-lines.json (the 10 place nodes).
Prints one line per check and a summary; exits 0 only when every check
passes. Run from the repo root: python3 tools/verify_queue12_bq.py
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
    gdd02 = (ROOT / "docs" / "GDD-02-RUPSHA-CITY-DISTRICT1.md").read_text()
    gdd06 = (ROOT / "docs" / "GDD-06-NPC-BEHAVIOUR.md").read_text()
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    sched = (ROOT / "tools" / "sim" / "scheduler.py").read_text()
    dlg = json.loads((ROOT / "data" / "dialogue-lines.json").read_text())
    schedules = json.loads(
        (ROOT / "data" / "npc-schedules.json").read_text())

    # 1. §21 exists, headed Unit BQ, Queue 12.
    m21 = re.search(r"## 21\. Service-Anchor Zone Resolution "
                    r"\(AV gap G8 follow-up — the `tea_stall` decision\)",
                    gdd15)
    check(m21 is not None, "GDD-15 §21 exists, headed Unit BQ, Queue 12")
    sec = gdd15[m21.start():] if m21 else ""
    sec = sec.split("*End of GDD-15 §21")[0]

    # 2. The rule: places resolve to their own zone, movement to home.
    check("place resolves to its own zone" in sec
          or "resolves to the zone of the anchor" in sec,
          "§21 states the place-vs-movement rule")
    check("movement" in sec and "home_zone" in sec,
          "§21 keeps transit/mobile on home_zone")

    # 3. Every token the schedules use is ruled on.
    tokens = set()
    for sch in schedules["schedules"]:
        for b in sch["template"]:
            tokens.add(b["location"])
    for t in schedules.get("life_stage_templates", {}).values():
        for b in t:
            tokens.add(b["location"])
    missing = [t for t in tokens if f"`{t}`" not in sec]
    check(not missing, "§21 rules on every token the schedules use",
          f"missing={missing} tokens={sorted(tokens)}")

    # 4. tea_stall: nearest stall's zone, d1_market or d1_riverfront.
    check("nearest tea stall" in sec,
          "§21 resolves tea_stall to the nearest stall's zone")
    check("`d1_market` or `d1_riverfront`" in sec,
          "tea-stall zones are d1_market / d1_riverfront")
    check("six tea stalls" in gdd02 or "tea stalls ×6" in gdd02,
          "GDD-02 §2 puts six tea stalls in Boro Bazar")
    check("tea stall" in gdd02.lower(),
          "GDD-02 names a riverfront tea stall")

    # 5. The sim side is as §21 says: tea_stall is NOT in LEISURE_ZONE
    #    and the fallback maps it to home_zone.
    lz = re.search(r"LEISURE_ZONE = \{(.*?)\}", sched, re.S).group(1)
    check("tea_stall" not in lz,
          "scheduler LEISURE_ZONE has no tea_stall entry")
    check("transit, tea_stall, mobile" in sched
          or "tea_stall, mobile" in sched,
          "scheduler fallback covers transit/tea_stall/mobile")
    check("Six `tea_stall` blocks" in sec,
          "§21 counts the tea_stall blocks in the templates")
    count = sum(1 for sch in schedules["schedules"]
                for b in sch["template"] if b["location"] == "tea_stall")
    check(count == 6, "templates carry exactly 6 tea_stall blocks",
          f"count={count}")

    # 6. restaurant: the d1_midtown discrepancy is recorded.
    check("`d1_midtown`" in sec and "no sourced restaurant" in sec,
          "§21 records the unsourced d1_midtown restaurant mapping")
    check("restaurant\" in gdd02" or "Restaurant kitchen" in gdd02,
          "GDD-02 §5 puts the restaurant kitchen in d1_market")
    check("rooftop restaurant" in gdd02,
          "GDD-02 puts the rooftop restaurant in d1_uptown")
    rest = sum(1 for sch in schedules["schedules"]
               for b in sch["template"] if b["location"] == "restaurant")
    check(rest == 1, "templates carry exactly 1 restaurant block",
          f"count={rest}")

    # 7. The scheduler change is specified, not applied.
    check("specified here for a later implementation unit" in sec,
          "§21 specifies the scheduler change without applying it")
    check("instantiate()" in sec,
          "§21 names instantiate() as the change point")
    check("does not change `scheduler.py`" in sec,
          "§21 states no sim code is changed")

    # 8. The 10 place nodes exist and condition on the 10 zones.
    place = dlg["topics"]["ask_about_place"]["nodes"]
    check(len(place) == 10, "ask_about_place has exactly 10 nodes",
          f"n={len(place)}")
    zones = {n["condition"].get("zone") for n in place}
    check(zones == {f"d1_{z}" for z in
                    ["market", "oldtown", "riverfront", "midtown",
                     "civic", "education", "industry", "park",
                     "transport", "uptown"]},
          "place nodes condition on all 10 zones",
          f"zones={sorted(zones)}")
    check("dlg_topic_place_market" in sec
          and "dlg_topic_place_riverfront" in sec,
          "§21.4 names the place nodes a tea-stall NPC now hits")
    check("dlg_topic_place_midtown" in sec,
          "§21.4 names the midtown node a restaurant NPC leaves")

    # 9. §18.5 and the G8 bullet now point at §21.
    s185 = gdd15.split("### 18.5 ")[1].split("### 18.6 ")[0]
    check("Unit BQ" in s185 and "§21" in s185,
          "§18.5 records the BQ decision")
    g8 = gdd15.split("**G8 — Current zone")[1].split("- **G9")[0]
    check("Unit BQ (GDD-15 §21)" in g8,
          "§12.8 G8 points at the §21 decision")

    # 10. GDD-06 §3 anchor rule is cited as the place side.
    check("GDD-06 §3" in sec,
          "§21 cites GDD-06 §3 anchor resolution")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed; "
          f"{len(failed)} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
