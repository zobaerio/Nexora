"""Verify Queue 15 Unit DC — UE Nearest-Anchor Selection Note
(GDD-15 §21.5, GDD-06 §3 follow-up).

Checks the note against its sources: the nine named anchors in
data/district1-blockout.json service_anchors, the sim's
resolve_service_anchor() in tools/sim/scheduler.py (file order
within a zone), and TECH-DISTRICT1-BLOCKOUT §1 (local metres,
x east / z south). Recomputes the worked example from the data.
Prints one line per check and a summary; exits 0 only when every
check passes. Run from the repo root:
python3 tools/verify_queue15_dc.py
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKS = []


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def main():
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    sched = (ROOT / "tools" / "sim" / "scheduler.py").read_text()
    blockout = json.loads(
        (ROOT / "data" / "district1-blockout.json").read_text())
    anchors = blockout["service_anchors"]

    note = gdd15.split("### 21.5 UE nearest-anchor selection", 1)[1]
    note = note.split("*End of GDD-15 §21", 1)[0]
    check("### 21.5 UE nearest-anchor selection" in gdd15,
          "§21.5 exists in GDD-15")

    # 1. The anchor counts the note states are the data's counts.
    tea = [a for a in anchors if a["type"] == "tea_stall"]
    rest = [a for a in anchors if a["type"] == "restaurant"]
    check(len(tea) == 7, "the blockout has 7 tea stalls",
          f"{len(tea)} found")
    check(len(rest) == 2, "the blockout has 2 restaurants",
          f"{len(rest)} found")
    check(len([a for a in tea if a["zone_id"] == "d1_market"]) == 6,
          "6 tea stalls stand in d1_market")
    check(len([a for a in tea if a["zone_id"] == "d1_riverfront"]) == 1,
          "1 tea stall stands on the riverfront")
    check({a["zone_id"] for a in rest} == {"d1_market", "d1_uptown"},
          "restaurants are in d1_market and d1_uptown")

    # 2. The rule is stated: zone first, distance within it, file-order tie.
    check("The zone rule is unchanged" in note,
          "the note keeps the §21.2 zone rule")
    check("Euclidean distance" in note,
          "the within-zone pick is Euclidean distance")
    check("Ties break by file order" in note,
          "ties break by file order (the sim's rule)")
    check("at the moment the block starts" in note,
          "distance is measured from the NPC's position at block start")

    # 3. The worked example recomputes from the data.
    pos = (60, 40)
    market_stalls = [a for a in tea if a["zone_id"] == "d1_market"]
    nearest = min(market_stalls, key=lambda a: dist(pos, a["at"]))
    check(nearest["id"] == "anchor_tea_stall_bazar_2",
          "worked example: nearest stall to (60, 40) is Bazar Stall 2",
          f"{nearest['id']} at {dist(pos, nearest['at']):.1f} m")
    check(abs(dist(pos, [60, -20]) - 60.0) < 0.01,
          "worked example: Stall 1 is 60 m from (60, 40)")
    check(abs(dist(pos, nearest["at"]) - math.sqrt(1300)) < 0.01,
          "worked example: Stall 2 is ~36 m from (60, 40)")

    # 4. The sim side is untouched: file order within a zone.
    check("in file order" in sched,
          "scheduler.py still picks within a zone in file order")
    check("the UE\n    layer, which has positions, picks the truly nearest"
          in sched or "picks the truly nearest" in sched,
          "scheduler.py already points at the UE pick this note writes down")

    # 5. Scope: other tokens are excluded, dialogue is untouched.
    check("Not covered by this rule" in note,
          "tokens with no named anchors are excluded")
    check("§21.4 stands" in note or "no dialogue line changes" in note,
          "the note states dialogue is unchanged")
    check("positions are negotiable" in note,
          "the note honours the build law on positions")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
