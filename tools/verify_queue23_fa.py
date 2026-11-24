"""Verify Queue 23 Unit FA — Live Haggle Call Site (GDD-04 §3.6,
mission 2.3; EV follow-up).

Checks the call site against its sources: tools/sim/market.py
(the monthly shopping pass haggles food stalls down to the
catalogue base price and records the haggle), tools/sim/
missions.py (the 2.3 verifier still requires both objectives),
GDD-04 §3.6 (the call site is recorded wired, with what it is
and is not), and the tests (test_economy_business_market.py
TestHaggleAtTheMonthlyPass + TestNoHaggleAtBasePrices).
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue23_fa.py
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
    gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md").read_text()
    market_src = (ROOT / "tools" / "sim" / "market.py").read_text()
    missions_src = (ROOT / "tools" / "sim" / "missions.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_economy_business_market.py").read_text()
    ev_script = (ROOT / "tools" / "verify_queue22_ev.py").read_text()

    # 1. The haggle rule: food goods + clothing, head haggles to
    # base. (Queue 24 Unit GA extended HAGGLE_GOODS with
    # clothing_set; the tuple below is the GA tuple.)
    check('HAGGLE_GOODS = ("food_basket", "fish", "clothing_set")'
          in market_src,
          "market.py: the pass haggles the food goods + clothing")
    hag = market_src.split("def _haggled_price(")[1].split("def ")[0]
    check('data.goods[good_id]["base_price_ncr"]' in hag,
          "market.py: the paid price is the catalogue base price")
    check("shelf_price_ncr > base" in hag,
          "market.py: the haggle fires only above base")
    check("discount" not in hag.lower()
          and "chance" not in hag.lower(),
          "market.py: _haggled_price invents no discount rate")
    check("head_character_id is None" in hag,
          "market.py: a headless household has no haggler")

    # 2. The call site: retail_allocation records the haggle.
    alloc = market_src.split("def retail_allocation(")[1].split(
        "# -- Queue 22 Unit EV")[0]
    check("record_haggle(" in alloc,
          "market.py: retail_allocation records the haggle")
    check("market_zone_of_city(data, city)" in alloc,
          "market.py: the haggle is zoned to the city's market")
    check("pay_price < shelf" in alloc,
          "market.py: only a won haggle is recorded")
    check("got_units > 0" in alloc,
          "market.py: no purchase, no haggle")
    check('"haggles": 0' in alloc or '"haggles"' in alloc,
          "market.py: totals counts the haggles")
    check("unit_price=unit_price" in alloc,
          "market.py: the shelf draw is paid the paid price")
    zone = market_src.split("def market_zone_of_city(")[1] \
        .split("def ")[0]
    check('zone.endswith("_market")' in zone,
          "market.py: the market zone is read from the city's zones")
    draw = market_src.split("def _draw_from_shelves(")[1] \
        .split("def ")[0]
    check("unit_price=None" in draw
          and "unit_price if unit_price is not None" in draw,
          "market.py: the draw takes the paid unit price")

    # 3. The stranded return is restored (found while wiring FA:
    # EV's insertion left `return totals` inside
    # has_successful_haggle, so retail_allocation returned None
    # despite its docstring).
    check(alloc.rstrip().endswith("return totals"),
          "market.py: retail_allocation returns totals again")
    pred = market_src.split("def has_successful_haggle(")[1] \
        .split("def ")[0]
    check("return totals" not in pred,
          "market.py: no stray return left in has_successful_haggle")

    # 4. The verifier still requires BOTH objectives (unchanged).
    ver = missions_src.split("def verify_mission_2_3(")[1].split("def ")[0]
    check("has_successful_haggle(store, character_id" in ver,
          "missions.py: verify_mission_2_3 still reads the haggle")
    check("household_bought_food(store, household_id)" in ver,
          "missions.py: the food objective is still required")

    # 5. The decision is recorded in GDD-04 §3.6.
    sec23 = gdd04.split("Completion condition — mission 2.3")[1] \
        .split("Completion condition — mission 2.4")[0]
    check("Live call site — wired (Unit FA" in sec23,
          "GDD-04 §3.6: the call site is recorded wired")
    check("Live call site — still open" not in sec23,
          "GDD-04 §3.6: no 'still open' remains for 2.3")
    check("no stall conversation runs" in sec23,
          "GDD-04 §3.6: the no-dialogue-runtime limit is stated")
    check("Update, Unit FA" in sec23,
          "GDD-04 §3.6: the FA implementation note is present")
    check("Clothing and household-supply haggling is not modelled"
          in sec23,
          "GDD-04 §3.6: the clothing limit is recorded")
    check("return totals" in sec23,
          "GDD-04 §3.6: the stranded-return fix is recorded")

    # 6. The EV script's struck assertion was updated, not left
    # failing.
    check("the shopping pass haggles (FA live call site)" in ev_script,
          "verify_queue22_ev.py: the struck EV check is updated")

    # 7. Tests prove haggled verifies and unhaggled does not.
    check("class TestHaggleAtTheMonthlyPass" in tests,
          "tests: the haggled-pass class exists")
    check("class TestNoHaggleAtBasePrices" in tests,
          "tests: the base-price negative class exists")
    check("test_haggled_food_purchase_records_a_successful_haggle"
          in tests,
          "tests: the haggled purchase records a successful haggle")
    check("test_haggled_households_spend_the_paid_price" in tests,
          "tests: haggled households spend the paid price")
    check("test_shelves_are_paid_what_buyers_paid" in tests,
          "tests: shelves are paid what buyers paid")
    check("test_haggled_month_completes_mission_2_3" in tests,
          "tests: the haggled month completes 2.3")
    check("test_no_haggle_rows_when_shelves_are_at_base" in tests,
          "tests: no haggle rows at base prices")
    check("test_food_without_a_haggle_does_not_verify_2_3" in tests,
          "tests: food without a haggle does not verify 2.3")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed, "
          f"{len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
