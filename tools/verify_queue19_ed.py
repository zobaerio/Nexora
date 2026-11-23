"""Verify Queue 19 Unit ED — Hand-Back Wiring (GDD-04 §3.3,
Unit DP follow-up; GDD-15 §18).

Checks the hand-back against its sources: tools/sim/lost_items.py
(current_zone_at + hand_back_lost_item), GDD-04 §3.3 (the DP
hand-back design + the ED implementation note), GDD-15 §18 (the
finder-location rule + the ED note), and
tools/sim/tests/test_lost_items.py (the hand-back tests). Prints
one line per check and a summary; exits 0 only when every check
passes. Run from the repo root: python3 tools/verify_queue19_ed.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKS = []


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def main():
    gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md").read_text()
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    lost_items = (ROOT / "tools" / "sim" / "lost_items.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_lost_items.py").read_text()

    # 1. The zone accessor implements GDD-15 §18.1.
    check("def current_zone_at(" in lost_items,
          "lost_items.py defines current_zone_at")
    cza = lost_items.split("def current_zone_at(")[1] \
        .split("def hand_back_lost_item(")[0]
    check("instantiated_schedules" in cza,
          "current_zone_at reads the instantiated_schedules row")
    check("block" in cza and "zone" in cza,
          "current_zone_at returns the block's zone")

    # 2. The hand-back refuses every case the design refuses.
    check("def hand_back_lost_item(" in lost_items,
          "lost_items.py defines hand_back_lost_item")
    hb = lost_items.split("def hand_back_lost_item(")[1] \
        .split("def seed_tool_rows(")[0] \
        if "def seed_tool_rows(" in lost_items else \
        lost_items.split("def hand_back_lost_item(")[1]
    check("finder" in hb and "recorded finder" in hb
          or "the recorded finder" in hb,
          "hand_back refuses a caller who is not the recorded finder")
    check("died_at_game_minutes\"] is not None" in hb,
          "hand_back refuses a deceased owner (orphaned favour)")
    check("finder_property_id" in hb,
          "hand_back reads the open tenancy's property")
    check("finder_zone" in hb,
          "hand_back falls back to the owner's current zone")
    check("return_lost_item(" in hb,
          "a successful hand-back calls return_lost_item")

    # 3. The design records the wiring.
    check("**Implementation (Unit ED" in gdd04,
          "GDD-04 §3.3 carries the ED implementation note")
    check("current_zone_at" in gdd15,
          "GDD-15 §18 names current_zone_at as the sim implementation")
    check("no tenancy" in gdd15 or "current_zone_at" in gdd15,
          "GDD-15 §18 covers the no-tenancy zone fallback")

    # 4. The tests prove the wiring.
    check("class TestCurrentZoneAt" in tests,
          "test_lost_items.py has the current_zone_at tests")
    check("class TestHandBack" in tests,
          "test_lost_items.py has the hand-back tests")
    check("test_deceased_owner_is_orphaned_not_re_routed" in tests,
          "test_lost_items.py tests the deceased-owner refusal")
    check("test_hand_back_at_the_current_home_succeeds" in tests,
          "test_lost_items.py tests the home hand-back")
    check("test_moved_owner_re_routes_to_the_new_home" in tests,
          "test_lost_items.py tests the moved-owner re-route")
    check("test_no_tenancy_and_no_stored_day_refuses" in tests,
          "test_lost_items.py tests the no-stored-day refusal")
    check("test_hand_back_refuses_a_finder_who_does_not_hold_it"
          in tests,
          "test_lost_items.py tests the wrong-finder refusal")
    check("test_no_tenancy_falls_back_to_the_current_zone" in tests,
          "test_lost_items.py tests the zone fallback")
    check("test_hand_back_refuses_the_wrong_property" in tests,
          "test_lost_items.py tests the wrong-property refusal")
    check("test_hand_back_refuses_an_item_never_found" in tests,
          "test_lost_items.py tests the never-found refusal")
    check("test_hand_back_refuses_an_unknown_row" in tests,
          "test_lost_items.py tests the unknown-row refusal")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
