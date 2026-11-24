"""Verify Queue 25 Unit HB — Haggle Household Supplies
(GA follow-up).

Checks the extension against its sources: tools/sim/market.py
(the monthly shopping pass buys one household-month unit of
household_supplies per household and haggles the stall down to
the catalogue base price when the shelf stands above it,
recorded via record_haggle(), takings following the paid price),
tools/sim/business.py (retail genesis stock seeds supplies, so
the want can buy), data/economy-goods.json (the good's unit and
base price), docs/GDD-04-MISSIONS-AND-PROGRESSION.md §3.6 (the
extension is recorded), and the tests
(test_economy_business_market.py TestHaggleSuppliesAtTheMonthlyPass
+ TestNoSuppliesHaggleAtBasePrices).
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue25_hb.py
"""
import subprocess
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
    market_src = (ROOT / "tools" / "sim" / "market.py").read_text()
    business_src = (ROOT / "tools" / "sim" / "business.py").read_text()
    gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_economy_business_market.py").read_text()
    goods = (ROOT / "data" / "economy-goods.json").read_text()

    # 1. The haggle rule now covers household_supplies — the
    # basket is fully haggled.
    haggle_line = [ln for ln in market_src.splitlines()
                   if ln.startswith("HAGGLE_GOODS =")]
    check(len(haggle_line) == 1, "market.py: one HAGGLE_GOODS line")
    joined = " ".join(market_src.split(
        "HAGGLE_GOODS = (")[1].split(")")[0].split())
    check("household_supplies" in joined,
          "market.py: household_supplies joins HAGGLE_GOODS",
          joined.strip())
    for good in ("food_basket", "fish", "clothing_set",
                 "household_supplies"):
        check(f'"{good}"' in joined,
              f"market.py: HAGGLE_GOODS still covers {good}")

    # 2. The pass buys the supplies want: one household-month
    # unit per household, scaled by hardship — no spend line is
    # invented, because the settlement has no supplies budget
    # line (engine._living_costs).
    alloc = market_src.split("def retail_allocation(")[1].split(
        "# -- Queue 22 Unit EV")[0]
    check('"household_supplies"' in alloc,
          "market.py: the pass allocates a supplies want")
    check("units = hardship * demand_factor" in alloc,
          "market.py: the supplies want is one unit, hardship-"
          "scaled")
    check("no spend line is" in alloc
          or "no settlement budget line for supplies" in alloc,
          "market.py: the want records why no spend line exists")
    hag = market_src.split("def _haggled_price(")[1].split("def ")[0]
    check("household_supplies" in hag,
          "market.py: _haggled_price names the supplies extension")
    check("a non-haggled good (household_supplies)" not in hag,
          "market.py: supplies are no longer the non-haggled good")
    check("record_haggle(" in alloc,
          "market.py: retail_allocation records the haggle")
    check("pay_price < shelf" in alloc,
          "market.py: only a won haggle is recorded")
    check("got_units > 0" in alloc,
          "market.py: no purchase, no haggle")
    check("unit_price=unit_price" in alloc,
          "market.py: the shelf draw is paid the paid price")

    # 3. The shelf holds supplies at all: retail genesis stock
    # seeds it (2 per retailer, like clothing_set) — before HB
    # no household ever wanted supplies, so no shelf held it.
    check('"household_supplies": 2' in business_src,
          "business.py: retail genesis stock seeds supplies (2)")
    check("Queue 25 Unit HB" in business_src,
          "business.py: the seed records why it exists")

    # 4. The catalogue facts the rule rests on: one
    # household-month unit, base price 500.
    check('"id": "household_supplies"' in goods
          or '"id":"household_supplies"' in goods,
          "economy-goods.json: household_supplies is catalogued")
    check('"base_price_ncr": 500' in goods.replace(" ", "")
          or '"base_price_ncr":500' in goods.replace(" ", ""),
          "economy-goods.json: the supplies base price is 500")
    check("household_month" in goods,
          "economy-goods.json: the supplies unit is household_month")

    # 5. GDD-04 §3.6 records the extension and the good-agnostic
    # consequence (a supplies haggle satisfies objective (2)).
    check("Unit HB · Queue 25" in gdd04,
          "GDD-04 §3.6: the HB update is recorded")
    check("household_supplies` joins `HAGGLE_GOODS`" in gdd04
          or "household_supplies` haggles to base" in gdd04,
          "GDD-04 §3.6: the rule is stated")
    check("The basket is now fully haggled" in gdd04
          or "basket is fully haggled" in gdd04,
          "GDD-04 §3.6: the basket is fully haggled")
    check("no settlement budget line for supplies" in gdd04,
          "GDD-04 §3.6: the no-spend-line reasoning is recorded")

    # 6. The tests: a haggled supplies purchase records, an
    # at-base one does not, and the haggle verifies 2.3.
    check("class TestHaggleSuppliesAtTheMonthlyPass" in tests,
          "tests: the haggled-supplies class exists")
    check("class TestNoSuppliesHaggleAtBasePrices" in tests,
          "tests: the at-base class exists")
    check("def test_haggled_supplies_purchase_records_a_"
          "successful_haggle" in tests,
          "tests: the haggled purchase records")
    check("def test_haggled_supplies_households_spend_the_"
          "paid_price" in tests,
          "tests: the haggled spend follows the paid price")
    check("def test_supplies_haggle_satisfies_mission_2_3"
          in tests,
          "tests: the supplies haggle verifies 2.3")
    check("def test_no_supplies_haggle_rows_when_shelf_is_at_base"
          in tests,
          "tests: at base, no haggle rows")
    check("def test_supplies_are_still_bought_at_base" in tests,
          "tests: at base, supplies are still bought")
    check('"household_supplies", "household_supplies"' not in tests,
          "tests: no placeholder text")

    # 7. Scope: only the HB files changed on this branch since
    # the HA commit.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    check(names == {"tools/sim/market.py",
                    "tools/sim/business.py",
                    "docs/GDD-04-MISSIONS-AND-PROGRESSION.md",
                    "tools/sim/tests/test_economy_business_market.py",
                    "tools/verify_queue25_hb.py"},
          "scope: only the five HB files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
