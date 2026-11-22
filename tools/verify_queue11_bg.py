"""Verify Queue 11 Unit BG — GDD-15 §18 current-zone accessor (AV gap G8).

Checks the accessor section against the sources it must resolve to:
GDD-06 §3, GDD-15 §12, data/dialogue-lines.json, tools/sim/scheduler.py,
tools/sim/engine.py, tools/sim/persistence.py.
Prints one line per check and a summary; exits 0 only when every check
passes. Run from the repo root: python3 tools/verify_queue11_bg.py
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


def main():
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    gdd06 = (ROOT / "docs" / "GDD-06-NPC-BEHAVIOUR.md").read_text()
    sched = (ROOT / "tools" / "sim" / "scheduler.py").read_text()
    engine = (ROOT / "tools" / "sim" / "engine.py").read_text()
    persist = (ROOT / "tools" / "sim" / "persistence.py").read_text()
    dlg = load_json("dialogue-lines.json")

    # 1. §18 exists, headed Unit BG, Queue 11, resolving G8.
    m18 = re.search(r"## 18\. Current-Zone Accessor \(AV gap G8 — resolved\)"
                    r"\n\n\*\*Unit BG · Queue 11",
                    gdd15)
    check(m18 is not None, "GDD-15 §18 exists, headed Unit BG, Queue 11")

    # 2. §12.8 G8 is marked resolved by BG.
    check("**Resolved by Queue 11, Unit BG (GDD-15 §18):**" in gdd15,
          "§12.8 G8 marked resolved by Queue 11 Unit BG")

    # 3. The accessor contract is stated with its signature and None case.
    sec18 = gdd15.split("\n## 18. ")[1].split("\n## 19. ")[0]
    check("current_zone_at(store, character_id, game_minutes)" in sec18,
          "accessor contract current_zone_at() stated")
    check("day_index = game_minutes // 1440" in sec18,
          "day derived as game_minutes // 1440")

    # 4. instantiate() assigns a zone to every block.
    check('b["zone"] = character["home_zone"]' in sched,
          "instantiate() assigns home_zone to home blocks")
    check('b["zone"] = character["workplace_zone"]' in sched,
          "instantiate() assigns workplace_zone to workplace blocks")
    check('b["zone"] = LEISURE_ZONE[b["location"]]' in sched,
          "instantiate() assigns LEISURE_ZONE for leisure locations")

    # 5. LEISURE_ZONE carries the seven mappings §18.2 states.
    lz = re.search(r"LEISURE_ZONE = \{(.*?)\}", sched, re.S).group(1)
    expected_lz = {"riverfront": "d1_riverfront", "park": "d1_park",
                   "market": "d1_market", "restaurant": "d1_midtown",
                   "college": "d1_education", "school": "d1_education",
                   "college_para": "d1_education"}
    found_lz = dict(re.findall(r'"(\w+)": "(d1_\w+)"', lz))
    check(found_lz == expected_lz, "LEISURE_ZONE matches §18.2 table",
          f"found={found_lz}")

    # 6. The fallback maps transit/tea_stall/mobile to home_zone.
    check('else:  # transit, tea_stall, mobile: local to home/work path'
          in sched,
          "transit/tea_stall/mobile fall back to home_zone in scheduler")

    # 7. The engine persists one instantiated day per character per day.
    check("instantiated_schedules" in engine
          and "INSERT OR REPLACE INTO instantiated_schedules" in engine,
          "engine persists instantiated_schedules per character per day")
    check("assert total == 1440" in engine,
          "engine asserts 1440-minute day coverage")

    # 8. The instantiated_schedules table exists with the (character, day) key.
    check("CREATE TABLE IF NOT EXISTS instantiated_schedules" in persist,
          "instantiated_schedules table exists in the sim store")
    check("PRIMARY KEY (character_id, day_index)" in persist,
          "instantiated_schedules keyed by (character_id, day_index)")

    # 9. _normalise tiles the day (gaps become explicit home blocks).
    check('"gap_fill": True' in sched,
          "_normalise gap-fills the day with home blocks")

    # 10. All 10 place nodes exist with the zone ids §18.7 lists.
    place = dlg["topics"]["ask_about_place"]["nodes"]
    found_place = {n["node_id"]: n["condition"]["zone"] for n in place}
    expected_place = {
        "dlg_topic_place_market": "d1_market",
        "dlg_topic_place_oldtown": "d1_oldtown",
        "dlg_topic_place_riverfront": "d1_riverfront",
        "dlg_topic_place_midtown": "d1_midtown",
        "dlg_topic_place_civic": "d1_civic",
        "dlg_topic_place_education": "d1_education",
        "dlg_topic_place_industry": "d1_industry",
        "dlg_topic_place_park": "d1_park",
        "dlg_topic_place_transport": "d1_transport",
        "dlg_topic_place_uptown": "d1_uptown"}
    check(found_place == expected_place,
          "all 10 place nodes exist with the §18.7 zone ids",
          f"found={len(found_place)}")

    # 11. ask_about_place unlock is Always (§4).
    check(dlg["topics"]["ask_about_place"]["unlock"] == "Always",
          "ask_about_place unlock is Always")

    # 12. The tea-stall discrepancy is recorded (§18.5).
    check("tea_stall" in sec18 and "d1_market" in sec18,
          "§18.5 records the tea_stall store difference")
    market_node = next(n for n in place
                       if n["node_id"] == "dlg_topic_place_market")
    check("tea stalls" in json.dumps(market_node["lines"]),
          "market line places tea stalls in Boro Bazar (d1_market)")

    # 13. GDD-06 §3 token table names transit and mobile.
    sec3 = gdd06.split("## 3. Anchors, Templates & Jitter")[1].split(
        "\n## 4. Per-Profession")[0]
    check("`transit`" in sec3 and "`mobile`" in sec3,
          "GDD-06 §3 token table names transit and mobile")
    check("Nearest stop on the commute path" in sec3,
          "transit resolves to nearest stop on the commute path")

    # 14. Commute is the only state that moves between anchors (GDD-06 §2).
    check("`Commute` is the only state that moves an NPC between anchors"
          in gdd06,
          "Commute is the only anchor-moving state (GDD-06 §2)")

    # 15. Day 1 is a Monday; 1440 minutes per day.
    check("Day 1 (index 0) is a Monday" in sched,
          "Day 1 is a Monday (scheduler)")
    check("1440" in sec18, "§18 uses 1440 game minutes per day")

    # 16. The None case falls back per §12.6 rule 1.
    check("§12.6 rule 1" in sec18,
          "None zone falls back per §12.6 rule 1")

    # 17. §12.1 snapshot table's Current zone row cites G8.
    sec121 = gdd15.split("### 12.1")[1].split("### 12.2")[0]
    check("G8" in sec121, "§12.1 Current zone row cites gap G8")

    # 18. §18.7 names the <zone_name> placeholder fill.
    check("<zone_name>" in sec18, "§18.7 fills the <zone_name> placeholder")

    # 19. Gap G8 resolution statement present.
    check("**Gap G8 is resolved by this section**" in sec18,
          "§18 states gap G8 resolved")

    # 20. No sim code changed by this unit (design only).
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
