"""Verify Queue 21 Unit ET — Furniture Purchase Event (GDD-10 §5;
EM follow-up).

Checks the purchase event against its sources: tools/sim/
households.py (the event), tools/sim/lost_items.py (the
allow_duplicate seeding rule + the catalogue accessor), GDD-10 §5
+ GDD-04 §3.3 (the decision is recorded, and the EM honest limit
is closed), and the tests (test_lost_items.py
TestFurniturePurchase). Prints one line per check and a summary;
exits 0 only when every check passes.
Run from the repo root: python3 tools/verify_queue21_et.py
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
    gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md").read_text()
    hh_src = (ROOT / "tools" / "sim" / "households.py").read_text()
    li_src = (ROOT / "tools" / "sim" / "lost_items.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_lost_items.py").read_text()

    # 1. The seeding helper gains the purchase mode, default off.
    check("def furniture_item(" in li_src,
          "lost_items.py defines the furniture_item accessor")
    check("allow_duplicate=False" in li_src,
          "seed_furniture_rows gains allow_duplicate, default False")
    seed = li_src.split("def seed_furniture_rows(")[1].split("def ")[0]
    check("not allow_duplicate" in seed,
          "the skip rule stands unless allow_duplicate is set")

    # 2. The purchase event exists and follows the specified point.
    check("def purchase_furniture(" in hh_src,
          "households.py defines purchase_furniture")
    event = hh_src.split("def purchase_furniture(")[1]
    check("furniture_item(data, item_id)" in event,
          "the event validates against the catalogue")
    check('data.prices["furniture"]["items"]' in event,
          "the event prices from prices.json furniture")
    check('item["price_ref"]' in event,
          "the event prices via the piece's price_ref")
    check('"SYS-MARKET", price, "purchase"' in event,
          "the event pays with the ledger purchase row to SYS-MARKET")
    check("seed_furniture_rows(" in event
          and "allow_duplicate=True" in event,
          "the event seeds via seed_furniture_rows, duplicates allowed")
    check('item["tier"]' in event,
          "the seeded row carries the catalogue tier")
    check("household_head(store, household_id)" in event,
          "the event buys through the household head")
    check("home_property(store, household_id)" in event,
          "the event seeds at the home property")
    event_code = event.split('"""')[2]  # past the docstring
    check("transfer_key" not in event_code,
          "the event carries no transfer_key (each call is one purchase)")

    # 3. The decision is recorded in both docs.
    check("Update, Unit ET" in gdd10,
          "GDD-10 §5 carries the ET update")
    check("no monthly sweep or decision calls the event yet" in gdd10,
          "GDD-10 §5 records the missing trigger honestly")
    check("sales-tax treatment of durable purchases" in gdd10,
          "GDD-10 §5 records the undecided sales-tax treatment")
    check("Update (Unit ET" in gdd04,
          "GDD-04 §3.3 carries the ET update")

    # 4. The tests cover the event.
    check("class TestFurniturePurchase(" in tests,
          "tests define TestFurniturePurchase")
    for name in ("test_buys_an_f2_piece_at_catalogue_price",
                 "test_buying_the_full_f2_set_raises_the_tier",
                 "test_second_row_for_an_already_held_piece",
                 "test_refuses_when_the_pool_cannot_cover_it",
                 "test_richest_member_covers_when_the_head_is_short",
                 "test_unknown_item_raises",
                 "test_no_head_returns_none",
                 "test_no_home_returns_none",
                 "test_f0_piece_costs_nothing_and_seeds_a_second_row",
                 "test_a_second_purchase_in_the_same_month_is_a_second_purchase"):
        check(f"def {name}(" in tests, f"tests define {name}")

    # 5. Live behaviour: buy one F2 piece, on a real store.
    from tools.sim import households as hh
    from tools.sim import lost_items as li
    from tools.sim.tests.common import (data, make_household,
                                        make_person, make_store)
    store = make_store()
    head = make_person(store, age=35, first="Head")
    hid, pid = make_household(store, [head])
    store.transfer(None, head, 100000, "seed", 480)
    li.seed_furniture_at_move_in(store, data(), hid, pid, 480)
    iid = hh.purchase_furniture(store, data(), hid, "sofa", 5, 480)
    check(iid is not None, "purchase_furniture returns the new item id")
    check(store.balance(head) == 95000,
          "the head paid the catalogue price", "95000")
    row = store.row(
        "SELECT * FROM economy_ledger WHERE from_character_id = ?"
        " AND reason_code = 'purchase'", (head,))
    check(row is not None and row["amount"] == 5000
          and row["to_character_id"] == "SYS-MARKET",
          "the ledger holds the purchase row to SYS-MARKET", "5000")
    check(li.effective_furniture_tier(store, data(), head) == "F1",
          "one F2 sofa alone does not raise the tier", "F1")
    second = hh.purchase_furniture(store, data(), hid, "sofa", 5, 480)
    check(second is not None and second != iid,
          "a second purchase writes a second row")
    check(store.balance(head) == 90000,
          "the second purchase charged again", "90000")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    if failed:
        print("FAILED:")
        for _, label, detail in failed:
            print(f"  - {label}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
