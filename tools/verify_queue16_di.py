"""Verify Queue 16 Unit DI — UE Anchor-Pick Verification Harness
(GDD-15 §21.5, Unit DC).

A headless check of DC's rule, stated in blockout metres so it is
testable without a UE build: for a set of sample NPC positions, the
UE nearest pick (Euclidean distance in blockout metres from the
NPC's position at block start, ties by file order) is computed from
data/district1-blockout.json and compared against the sim's
within-zone file-order pick (tools/sim/scheduler.py
resolve_service_anchor). Every sample must agree on the zone — the
rule never moves an NPC between zones — and must differ from file
order wherever positions differ, or agree where the zone holds a
single anchor. The market-kitchen example from §21.5 is sample 1;
riverfront and uptown samples follow.

This harness tests the rule AS STATED against the data file. It
does not compile or run UE, and it does not prove the UE build
picks the same anchor — the PC build is the proof of that.
Prints one line per check and a summary; exits 0 only when every
check passes. Run from the repo root: python3 tools/verify_queue16_di.py
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools.sim.scheduler import resolve_service_anchor  # noqa: E402

CHECKS = []

# (label, npc position (x, z), token, home zone, workplace zone,
#  expected UE anchor id, expected sim anchor id, picks differ?)
SAMPLES = [
    # §21.5 worked example: the market kitchen, (60, 40). File
    # order sends the NPC to Stall 1 at (60, -20), 60 m away; the
    # UE measures all six and sends them to Stall 2 at (90, 20),
    # ~36 m. Same zone, a shorter walk.
    ("market kitchen", (60, 40), "tea_stall", "d1_market", "d1_midtown",
     "anchor_tea_stall_bazar_2", "anchor_tea_stall_bazar_1", True),
    # Riverfront position, home/workplace outside the tea-stall
    # zones: the zone rule defaults to d1_market, and the UE still
    # picks within that zone — Stall 6 is nearest from (0, 380)
    # even though the NPC stands in the riverfront. The zone gate
    # holds: a stall in another zone is never "nearest".
    ("riverfront position", (0, 380), "tea_stall", "d1_midtown",
     "d1_uptown", "anchor_tea_stall_bazar_6",
     "anchor_tea_stall_bazar_1", True),
    # Uptown position, same default: from (420, 350) the nearest
    # Boro Bazar stall is Stall 5, not Stall 1.
    ("uptown position", (420, 350), "tea_stall", "d1_uptown",
     "d1_midtown", "anchor_tea_stall_bazar_5",
     "anchor_tea_stall_bazar_1", True),
    # Riverfront home: one tea stall in the zone, so the UE pick
    # and the sim pick agree — the control case.
    ("riverfront home", (10, 370), "tea_stall", "d1_riverfront",
     "d1_market", "anchor_tea_stall_riverfront_1",
     "anchor_tea_stall_riverfront_1", False),
    # Uptown restaurant: one per zone, so the UE pick is vacuous
    # (§21.5) — both pick the rooftop restaurant.
    ("uptown restaurant", (420, 350), "restaurant", "d1_uptown",
     "d1_midtown", "anchor_restaurant_rooftop",
     "anchor_restaurant_rooftop", False),
    # Market restaurant: one per zone — the market kitchen.
    ("market restaurant", (60, 40), "restaurant", "d1_market",
     "d1_midtown", "anchor_restaurant_market_kitchen",
     "anchor_restaurant_market_kitchen", False),
]


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def ue_nearest(position, token, zone, anchors):
    """The DC rule (§21.5): the anchor of that token's type in the
    resolved zone minimising Euclidean distance in blockout metres
    from the NPC's position, ties by file order."""
    best, best_d = None, None
    for a in anchors:
        if a["type"] != token or a["zone_id"] != zone:
            continue
        d = math.hypot(a["at"][0] - position[0],
                       a["at"][1] - position[1])
        if best_d is None or d < best_d - 1e-9:
            best, best_d = a, d
    return best, best_d


def main():
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    blockout = json.loads(
        (ROOT / "data" / "district1-blockout.json").read_text())
    anchors = blockout["service_anchors"]
    scheduler = (ROOT / "tools" / "sim" / "scheduler.py").read_text()

    # 1. The rule is stated in §21.5 as the harness implements it.
    s215 = gdd15.split("### 21.5 ")[1].split("## 22.")[0]
    check("minimising Euclidean distance in blockout metres" in s215,
          "§21.5 states the Euclidean pick in blockout metres")
    check("Ties break by file order" in s215,
          "§21.5 states the file-order tie-break")
    check("The rule never moves an NPC between zones" in s215,
          "§21.5 states the zone gate (no cross-zone pick)")

    # 2. The §21.5 worked example, recomputed independently.
    kitchen = (60, 40)
    dists = {}
    for a in anchors:
        if a["type"] == "tea_stall" and a["zone_id"] == "d1_market":
            dists[a["id"]] = math.hypot(a["at"][0] - kitchen[0],
                                        a["at"][1] - kitchen[1])
    check(abs(dists["anchor_tea_stall_bazar_2"] - 36.0555) < 0.01,
          "worked example: Stall 2 is ~36 m from the market kitchen",
          f"{dists['anchor_tea_stall_bazar_2']:.2f} m")
    check(abs(dists["anchor_tea_stall_bazar_1"] - 60.0) < 0.01,
          "worked example: Stall 1 is 60 m from the market kitchen",
          f"{dists['anchor_tea_stall_bazar_1']:.2f} m")
    check(min(dists, key=dists.get) == "anchor_tea_stall_bazar_2",
          "worked example: Stall 2 is the nearest of the six",
          f"nearest={min(dists, key=dists.get)}")

    # 3. The tie-break: the midpoint of Stalls 1 and 2 is exactly
    # equidistant (25 m each) — file order must win, i.e. Stall 1.
    tie_pos = (75, 0)
    tie_pick, tie_d = ue_nearest(tie_pos, "tea_stall", "d1_market",
                                 anchors)
    d1 = math.hypot(60 - 75, -20 - 0)
    d2 = math.hypot(90 - 75, 20 - 0)
    check(abs(d1 - d2) < 1e-9 and abs(d1 - 25.0) < 1e-9,
          "tie sample: midpoint (75, 0) is 25 m from Stalls 1 and 2",
          f"d1={d1:.2f} d2={d2:.2f}")
    check(tie_pick["id"] == "anchor_tea_stall_bazar_1",
          "tie-break picks Stall 1 (first in file order)",
          f"picked={tie_pick['id']}")

    # 4. Every sample: zones agree; picks differ exactly where the
    # sample says they should.
    for label, pos, token, home, work, want_ue, want_sim, differs \
            in SAMPLES:
        zone, sim_pick = resolve_service_anchor(token, home, work,
                                                anchors)
        ue_pick, ue_d = ue_nearest(pos, token, zone, anchors)
        check(ue_pick is not None,
              f"{label}: the UE rule finds an anchor in {zone}")
        if ue_pick is None:
            continue
        check(ue_pick["zone_id"] == zone,
              f"{label}: UE pick stays in the resolved zone {zone}",
              f"picked {ue_pick['id']}")
        check(ue_pick["id"] == want_ue,
              f"{label}: UE nearest pick is {want_ue}",
              f"picked {ue_pick['id']} at {ue_d:.1f} m")
        check(sim_pick == want_sim,
              f"{label}: sim file-order pick is {want_sim}",
              f"picked {sim_pick}")
        check((ue_pick["id"] != sim_pick) == differs,
              f"{label}: picks {'differ' if differs else 'agree'}"
              " as expected",
              f"UE={ue_pick['id']} sim={sim_pick}")

    # 5. The sim's rule is the file-order rule §21.5 describes.
    check("in file order" in scheduler,
          "scheduler.py states the within-zone pick is file order")
    check("SERVICE_ANCHOR_ZONES" in scheduler,
          "scheduler.py carries the zone rule the harness reuses")

    # 6. The honest boundary: the harness tests the rule, not UE.
    check("does not compile or run UE" in
          Path(__file__).read_text(),
          "this harness states it does not compile or run UE")
    check("Unit DI · Queue 16" in gdd15,
          "GDD-15 §21.5 carries the DI harness note")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
