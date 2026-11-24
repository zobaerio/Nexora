"""Verify Queue 24 Unit GA — Haggle the Rest of the Basket
(GDD-04 §3.6, mission 2.3; FA follow-up).

Checks the extension against its sources: tools/sim/market.py
(the monthly shopping pass haggles clothing stalls down to the
catalogue base price and records the haggle, takings follow the
paid price), tools/sim/missions.py (the 2.3 verifier is
good-agnostic — it reads character + zone + success, never the
good), GDD-04 §3.6 (the extension + the good-agnostic note are
recorded), and the tests (test_economy_business_market.py
TestHaggleClothingAtTheMonthlyPass).
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue24_ga.py
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
    fa_script = (ROOT / "tools" / "verify_queue23_fa.py").read_text()

    # 1. The haggle rule now covers clothing_set.
    check('HAGGLE_GOODS = ("food_basket", "fish", "clothing_set")'
          in market_src,
          "market.py: clothing_set joins HAGGLE_GOODS")
    haggle_line = [ln for ln in market_src.splitlines()
                   if ln.startswith("HAGGLE_GOODS =")][0]
    check("household_supplies" not in haggle_line,
          "market.py: household supplies are still not haggled")
    hag = market_src.split("def _haggled_price(")[1].split("def ")[0]
    check('data.goods[good_id]["base_price_ncr"]' in hag,
          "market.py: the paid price is the catalogue base price")
    check("shelf_price_ncr > base" in hag,
          "market.py: the haggle fires only above base")
    check("discount" not in hag.lower()
          and "chance" not in hag.lower(),
          "market.py: _haggled_price invents no discount rate")

    # 2. The call site records the clothing haggle the same way
    # as the food haggle (the recording block is good-agnostic —
    # it reads pay_price < shelf for every good in the pass).
    alloc = market_src.split("def retail_allocation(")[1].split(
        "# -- Queue 22 Unit EV")[0]
    check("record_haggle(" in alloc,
          "market.py: retail_allocation records the haggle")
    check("pay_price < shelf" in alloc,
          "market.py: only a won haggle is recorded")
    check("got_units > 0" in alloc,
          "market.py: no purchase, no haggle")
    check("unit_price=unit_price" in alloc,
          "market.py: the shelf draw is paid the paid price")
    check("clothing_set" in alloc,
          "market.py: the pass allocates a clothing want")

    # 3. The verifier is good-agnostic: it reads character +
    # zone + success and never the good.
    ver = missions_src.split("def verify_mission_2_3(")[1].split("def ")[0]
    check("has_successful_haggle(store, character_id" in ver,
          "missions.py: verify_mission_2_3 still reads the haggle")
    check("good_id" not in ver,
          "missions.py: the 2.3 verifier never reads the good")
    pred = market_src.split("def has_successful_haggle(")[1] \
        .split("def ")[0]
    check("good_id" not in pred,
          "market.py: has_successful_haggle never reads the good")

    # 4. The decision is recorded in GDD-04 §3.6.
    sec23 = gdd04.split("Completion condition — mission 2.3")[1] \
        .split("Completion condition — mission 2.4")[0]
    check("Update, Unit GA" in sec23,
          "GDD-04 §3.6: the GA update note is present")
    check("good-agnostic" in sec23,
          "GDD-04 §3.6: the verifier is recorded good-agnostic")
    check('"haggle once", not "haggle over food"' in sec23,
          "GDD-04 §3.6: the objective is 'haggle once'")
    check("clothing_set` haggles to the catalogue base price"
          in sec23,
          "GDD-04 §3.6: the clothing rule is recorded")
    check("Household-supply haggling is still not modelled" in sec23,
          "GDD-04 §3.6: the supplies limit is recorded")
    check("A clothing PURCHASE still does not satisfy objective (1)"
          in sec23,
          "GDD-04 §3.6: clothing buys no food objective")

    # 5. The FA script's struck assertion was updated, not left
    # failing.
    check('HAGGLE_GOODS = ("food_basket", "fish", "clothing_set")'
          in fa_script,
          "verify_queue23_fa.py: the struck FA check is updated")

    # 6. Tests prove a haggled clothing purchase records and
    # verifies, and an at-base one does not (the at-base negative
    # is the FA TestNoHaggleAtBasePrices class, which asserts the
    # haggle table is empty at genesis prices).
    check("class TestHaggleClothingAtTheMonthlyPass" in tests,
          "tests: the haggled-clothing class exists")
    check("test_haggled_clothing_purchase_records_a_successful_haggle"
          in tests,
          "tests: the haggled clothing purchase records")
    check("test_haggled_clothing_households_spend_the_paid_price"
          in tests,
          "tests: haggled clothing households spend the paid price")
    check("test_clothing_haggle_satisfies_mission_2_3" in tests,
          "tests: the clothing haggle satisfies 2.3")
    check("test_no_haggle_rows_when_shelves_are_at_base" in tests,
          "tests: the at-base negative still exists")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed, "
          f"{len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
