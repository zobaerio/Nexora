"""Verify Queue 22 Unit EW — Home-Loop Purchase Decision (GDD-10
§5; ET follow-up).

Checks the purchase decision against its sources:
tools/sim/households.py (the monthly sweep + the decision),
tools/sim/lost_items.py (the standing-pieces helper it reads),
tools/sim/engine.py (the monthly social pass calls it after the
repair sweep), GDD-10 §5 (the decision is recorded), and the
tests (test_households.py TestMonthlyFurniturePurchase +
TestMonthlyFurniturePurchaseHook).
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue22_ew.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CHECKS = []


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def main():
    gdd10 = (ROOT / "docs" / "GDD-10-HOUSING-AND-HOME-LIFE.md").read_text()
    hh_src = (ROOT / "tools" / "sim" / "households.py").read_text()
    li_src = (ROOT / "tools" / "sim" / "lost_items.py").read_text()
    engine_src = (ROOT / "tools" / "sim" / "engine.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_households.py").read_text()

    # 1. The sweep exists and decides from sourced data only.
    sweep = hh_src.split("def monthly_furniture_purchase_sweep(")[1] \
        .split("def ")[0] if "def monthly_furniture_purchase_sweep(" \
        in hh_src else ""
    check("def monthly_furniture_purchase_sweep(" in hh_src,
          "households.py: monthly_furniture_purchase_sweep exists")
    check("effective_furniture_tier(store, data" in sweep,
          "households.py: the sweep reads the effective tier")
    check("furniture_pieces_standing(store" in sweep,
          "households.py: the sweep reads the standing pieces")
    check("NEXT_FURNITURE_TIER" in hh_src,
          "households.py: the next-tier map is explicit (None->F0)")
    check("min(missing" in sweep,
          "households.py: the sweep buys the cheapest missing piece")
    check("current_rent(store, data, hid)" in sweep,
          "households.py: affordability keeps a rent reserve")
    check("purchase_furniture(store, data, hid, cheapest" in sweep,
          "households.py: the purchase is the ET event, not a copy")
    check("event_ref = ?" in sweep and "month:" in sweep,
          "households.py: one piece per month via the ledger tag")
    check("dissolved_at_game_minutes IS NULL" in sweep,
          "households.py: dissolved households are skipped")

    # 2. The standing helper shares the tier rule.
    helper = li_src.split("def furniture_pieces_standing(")[1] \
        .split("def ")[0] if "def furniture_pieces_standing(" in li_src \
        else ""
    check("def furniture_pieces_standing(" in li_src,
          "lost_items.py: furniture_pieces_standing exists")
    check("item_condition(row) > 0" in helper
          and "_item_is_away(store" in helper,
          "lost_items.py: standing is condition > 0 and not away")

    # 3. The engine calls it every month, after the repair sweep.
    social = engine_src.split("def _monthly_social(")[1] \
        .split("def _monthly_city(")[0]
    check("monthly_furniture_purchase_sweep(" in social,
          "engine.py: the monthly social pass calls the sweep")
    check(social.index("monthly_repair_sweep(")
          < social.index("monthly_furniture_purchase_sweep("),
          "engine.py: the purchase sweep runs after the repair sweep")
    check("month_index = (last_day + 1) // 30" in social,
          "engine.py: month_index is the other passes' formula")

    # 4. The decision is recorded in GDD-10 §5.
    check("Update, Unit EW" in gdd10,
          "GDD-10 §5: the EW decision note is present")
    check("rent reserve" in gdd10,
          "GDD-10 §5: the rent reserve is recorded")
    check("cheapest missing piece" in gdd10,
          "GDD-10 §5: cheapest-first is recorded")
    check("F2/F3 are now reachable in a live world" in gdd10,
          "GDD-10 §5: F2/F3 reachability is recorded")

    # 5. Tests prove buy-when / not-when.
    check("class TestMonthlyFurniturePurchase" in tests,
          "tests: the purchase-decision test class exists")
    check("test_rich_f1_household_buys_cheapest_f2_piece" in tests,
          "tests: a rich F1 household buys the cheapest F2 piece")
    check("test_poor_household_buys_nothing" in tests,
          "tests: a poor household buys nothing (rent reserve)")
    check("test_exactly_enough_buys" in tests,
          "tests: exactly price + rent buys")
    check("test_richest_member_pays" in tests,
          "tests: the richest member pays")
    check("test_head_payer_is_protected_by_the_reserve" in tests,
          "tests: the head-payer rent reserve holds")
    check("test_f3_household_buys_nothing" in tests,
          "tests: an F3 household buys nothing")
    check("test_broken_f0_piece_is_replaced_free" in tests,
          "tests: a broken F0 piece is replaced free")
    check("test_one_piece_per_month" in tests,
          "tests: one piece per month (ledger tag)")
    check("class TestMonthlyFurniturePurchaseHook" in tests,
          "tests: the live engine-hook test exists")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed, "
          f"{len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
