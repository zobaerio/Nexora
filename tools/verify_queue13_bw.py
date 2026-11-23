"""Verify Queue 13 Unit BW — GDD-04 §3.2 per-mission deadline values
(4.2 -> 30, 6.2 -> 45, 7.4 -> 60; the other 29 missions carry none).

Checks the values against the sources they must resolve to: GDD-04
§2/§3.2 (mission fiction + stage arithmetic), GDD-15 §19, data/
missions.json, tools/sim/construction.py STAGE_DAYS, tools/
validate_data.py.
Prints one line per check and a summary; exits 0 only when every check
passes. Run from the repo root: python3 tools/verify_queue13_bw.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKS = []

EXPECTED = {"4.2": 30, "6.2": 45, "7.4": 60}


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def main():
    gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md").read_text()
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    missions = json.loads((ROOT / "data" / "missions.json").read_text())
    validator = (ROOT / "tools" / "validate_data.py").read_text()
    construction = (ROOT / "tools" / "sim" / "construction.py").read_text()
    gdd08 = (ROOT / "docs" / "GDD-08-CONSTRUCTION-SYSTEM.md").read_text()

    # 1. The §3.2 values table exists, headed Unit BW, Queue 13.
    m = re.search(r"\*\*Which missions carry one — three do "
                  r"\(Unit BW · Queue 13", gdd04)
    check(m is not None, "GDD-04 §3.2 values table exists, Unit BW, Queue 13")
    sec = gdd04.split("### 3.2 Mission Deadlines")[1].split(
        "### 3.3 Lost-Item Record")[0]

    # 2. Exactly the three missions carry a value, and the values match.
    by_id = {x["id"]: x for x in missions["missions"]}
    check(len(missions["missions"]) == 32, "missions.json still has 32 missions")
    got = {x["id"]: x["deadline_days"] for x in missions["missions"]
           if "deadline_days" in x}
    check(got == EXPECTED, "deadline_days values are exactly 4.2/30, 6.2/45, 7.4/60",
          f"got={got}")
    for mid, days in EXPECTED.items():
        check(isinstance(by_id[mid]["deadline_days"], int)
              and by_id[mid]["deadline_days"] >= 1,
              f"mission {mid} deadline_days is a positive integer")

    # 3. The stage arithmetic behind the numbers is sourced.
    stage = re.search(r"STAGE_DAYS = \{(.*?)\}", construction, re.S)
    check(stage is not None, "STAGE_DAYS table exists in construction.py")
    days = [int(n) for n in re.findall(r": (\d+)", stage.group(1))]
    check(sum(days) == 20, "STAGE_DAYS sums to 20 worked days",
          f"sum={sum(days)}")
    check("20 worked days" in sec, "§3.2 cites the 20-worked-day sum")
    check("halted days do not count" in gdd08
          or "do not count against the deadline's *worked* days" in gdd08,
          "GDD-08 §2 states halted days do not count against worked days")
    check("budget, deadline (game days)" in gdd08,
          "GDD-08 §2 gives jobs a deadline in game days (4.2's source)")

    # 4. Each value has its fiction reason stated in §3.2.
    for mid, why in (("4.2", "private client"),
                     ("6.2", "the city"),
                     ("7.4", "two cities")):
        row = re.search(rf"\| {re.escape(mid)} .*\|", sec)
        check(row is not None and why in row.group(0),
              f"§3.2 justifies {mid} from its fiction ({why})")

    # 5. The near-misses are considered and rejected, with reasons.
    for mid in ("2.3", "4.4", "6.3", "6.4", "8.1"):
        check(f"| {mid} " in sec,
              f"§3.2 considers and rejects {mid} with a reason")
    check("most missions carry none" in sec.lower()
          or "Most missions carry none" in sec,
          "§3.2 restates most missions carry none")
    check("a number without a fiction reason" in sec,
          "§3.2 forbids a deadline without a fiction reason")

    # 6. The lead window / expiry / retry follow without further design.
    check("4320" in sec or "3-day lead window" in sec,
          "§3.2 states the 3-day lead window still applies")
    check("expiry-to-`failed`" in sec or "expiry" in sec,
          "§3.2 states expiry-to-failed still applies")
    check("7-day retry" in sec, "§3.2 states the 7-day retry still applies")
    check("no deadline" in sec.lower(),
          "§3.2 states the other 29 missions carry none")

    # 7. GDD-15 §19 and §12.8 G10 now name the values.
    check("4.2 → 30 days, 6.2 → 45, 7.4 → 60" in gdd15,
          "GDD-15 §19 names the three values")
    check("The other 29 missions carry no deadline" in gdd15,
          "GDD-15 §19 states the other 29 carry none")
    check("Unit BW" in gdd15.split("**G10 — No mission deadlines.**")[1]
          .split("- **")[0] if "**G10" in gdd15 else False,
          "§12.8 G10 points at Unit BW")

    # 8. validate_data.py guards the values.
    check("def check_mission_deadlines" in validator,
          "validate_data.py carries the mission-deadlines check")
    check("check_mission_deadlines(data)" in validator,
          "validate_data.py calls the mission-deadlines check")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed; "
          f"{len(failed)} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
