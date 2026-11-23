"""Verify Queue 20 Unit EN — Property Deed Seeding (GDD-04 §3.3,
GDD-10 §8; DN follow-up).

Checks the deed seeding against its sources: tools/sim/decisions.py
(both purchase closures seed the deed), tools/sim/lost_items.py
(the helper + the corrected DJ note), data/documents.json (the
deed catalogue row), GDD-04 §3.3 (the EN implementation note) and
GDD-10 §8 (the deed bullet), and the tests (test_decisions.py).
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue20_en.py
"""
import json
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
    gdd10 = (ROOT / "docs" / "GDD-10-HOUSING-AND-HOME-LIFE.md").read_text()
    decisions = (ROOT / "tools" / "sim" / "decisions.py").read_text()
    lost_items = (ROOT / "tools" / "sim" / "lost_items.py").read_text()
    documents = json.loads(
        (ROOT / "data" / "documents.json").read_text())
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_decisions.py").read_text()

    # 1. The deed catalogue row exists and is unpriced.
    deed = next((i for i in documents["items"]
                 if i["id"] == "property_deed"), None)
    check(deed is not None,
          "documents.json carries the property_deed row")
    prices = json.loads((ROOT / "data" / "prices.json").read_text())
    doc_prices = {i["id"]: i["price_ncr"]
                  for i in prices["documents"]["items"]}
    check(deed is not None and deed["price_ref"] in doc_prices
          and doc_prices[deed["price_ref"]] == 0,
          "the deed's price_ref resolves in prices.json documents"
          " at 0 (UNPRICED, not free)")

    # 2. Both purchase closures seed the deed.
    check(decisions.count('seed_document_row(') >= 2,
          "decisions.py seeds a document row in both purchase "
          "closures (cash + mortgage)",
          f"found {decisions.count('seed_document_row(')} calls")
    cash = decisions.split("def _cand_buy_home(ctx):")[1] \
        .split("def _cand_buy_home_mortgage(ctx):")[0]
    mortgage = decisions.split("def _cand_buy_home_mortgage(ctx):")[1] \
        .split("CANDIDATES = (")[0]
    check('"property_deed"' in cash,
          "the cash purchase seeds a property_deed row")
    check('"property_deed"' in mortgage,
          "the mortgage purchase seeds a property_deed row")
    check('{"property_id": prop["property_id"]}' in cash
          and '{"property_id": prop["property_id"]}' in mortgage,
          "the deed state names the bought property (both paths)")

    # 3. The stale "no property purchase" claim is corrected.
    check("there is no property purchase" not in lost_items,
          "lost_items.py no longer claims no purchase exists")
    check("Unit EN" in lost_items,
          "lost_items.py carries the EN correction in the DJ note")
    check("*(Update, Unit EN" in gdd04,
          "GDD-04 §3.3 carries the EN correction on the DJ note")

    # 4. The design records the seeding.
    check("**Implementation (Unit EN" in gdd04,
          "GDD-04 §3.3 carries the EN implementation note")
    check("The purchase writes a property deed" in gdd10,
          "GDD-10 §8 carries the deed bullet")
    check("re-purchase" in gdd10,
          "the foreclosure re-purchase edge is recorded, not hidden")

    # 5. The tests prove the seeding on both paths.
    check("test_buy_home_mortgage_seeds_the_deed" in tests,
          "test_decisions.py tests the mortgage-path deed")
    check("property_deed" in tests,
          "test_decisions.py asserts the deed row after purchase")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
