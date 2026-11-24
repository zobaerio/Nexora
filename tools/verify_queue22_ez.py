"""Verify Queue 22 Unit EZ — F0-Break / No-Tier Restore Edge
(GDD-10 §5 + GDD-04 §3.3; EQ follow-up).

Checks the FLOOR rule against its sources: tools/sim/lost_items.py
(furniture_restore_multiplier), the EQ wiring in tools/sim/needs.py
(apply_activity applies the multiplier, no other change), the
recorded decision in GDD-10 §5 and GDD-04 §3.3, and the tests that
pin it (test_lost_items.py + test_needs.py). Prints one line per
check and a summary; exits 0 only when every check passes.
Run from the repo root: python3 tools/verify_queue22_ez.py
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
    li_src = (ROOT / "tools" / "sim" / "lost_items.py").read_text()
    needs_src = (ROOT / "tools" / "sim" / "needs.py").read_text()
    gdd10 = (ROOT / "docs" / "GDD-10-HOUSING-AND-HOME-LIFE.md"
             ).read_text()
    gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md"
             ).read_text()
    lost_tests = (ROOT / "tools" / "sim" / "tests"
                  / "test_lost_items.py").read_text()
    needs_tests = (ROOT / "tools" / "sim" / "tests"
                   / "test_needs.py").read_text()
    from tools.sim import lost_items as li
    from tools.sim import needs as needs_mod
    from tools.sim.tests.common import (data, make_household,
                                        make_person, make_store,
                                        set_needs)
    d = data()

    def _set_condition(store, iid, value):
        import json
        row = store.row("SELECT state FROM inventory_items"
                        " WHERE item_instance_id = ?", (iid,))
        state = json.loads(row["state"])
        state["condition"] = value
        store.execute("UPDATE inventory_items SET state = ?"
                      " WHERE item_instance_id = ?",
                      (json.dumps(state), iid))

    def _seeded_head(store, tier):
        head = make_person(store, age=35, first="Head")
        hid, pid = make_household(store, [head])
        items = ["floor_mattress", "single_burner", "crate_table"]
        if tier == "F1":
            items += ["bed", "table_chairs", "stove", "wardrobe",
                      "fan"]
        li.seed_furniture_rows(store, d, head, items, tier, pid, 480)
        return head

    # 1. The rule: tier still wins when it stands; the floor when
    # rows are held; None only when no rows exist at all.
    check('FURNITURE_RESTORE_MULTIPLIERS["F0"]' in li_src
          and 'if holds_furniture:' in li_src,
          "lost_items.py: the floor reads the F0 rate, no new number")
    check("partial-credit" in li_src,
          "lost_items.py: the rejected alternative is recorded")
    store = make_store()
    head = _seeded_head(store, "F0")
    check(li.furniture_restore_multiplier(store, d, head) == 0.7,
          "rule: an F0 home restores at 0.7")
    for row in store.rows("SELECT item_instance_id FROM inventory_items"
                          " WHERE owner_character_id = ?"
                          " AND item_ref IN ('floor_mattress',"
                          " 'single_burner', 'crate_table')", (head,)):
        _set_condition(store, row["item_instance_id"], 0)
    check(li.effective_furniture_tier(store, d, head) is None,
          "rule: an F0-only home with every piece broken has no tier")
    check(li.furniture_restore_multiplier(store, d, head) == 0.7,
          "rule: breaking the last F0 piece changes nothing (0.7)")
    store = make_store()
    head = _seeded_head(store, "F1")
    bed = store.row("SELECT item_instance_id FROM inventory_items"
                    " WHERE owner_character_id = ? AND item_ref = 'bed'",
                    (head,))["item_instance_id"]
    mat = store.row("SELECT item_instance_id FROM inventory_items"
                    " WHERE owner_character_id = ?"
                    " AND item_ref = 'floor_mattress'",
                    (head,))["item_instance_id"]
    _set_condition(store, mat, 0)
    check(li.effective_furniture_tier(store, d, head) is None,
          "rule: an F1 home with one broken F0 piece has no tier")
    check(li.furniture_restore_multiplier(store, d, head) == 0.7,
          "rule: an F1 home with a broken F0 piece gets the floor")
    store = make_store()
    bare = make_person(store, age=35, first="Head")
    make_household(store, [bare])
    check(li.furniture_restore_multiplier(store, d, bare) is None,
          "rule: a character holding no furniture rows gets None")
    store = make_store()
    head = _seeded_head(store, "F1")
    lid = li.record_loss(store, head, bed, 2000, "d1_midtown")
    check(lid is not None
          and li.furniture_restore_multiplier(store, d, head) == 0.7,
          "rule: a lost bed still leaves the floor (the row is held)")

    # 2. The consumer: needs applies the floor rate; genuinely
    # bare stays unscaled; no other apply_activity change.
    store = make_store()
    head = _seeded_head(store, "F0")
    for row in store.rows("SELECT item_instance_id FROM inventory_items"
                          " WHERE owner_character_id = ?"
                          " AND item_ref IN ('floor_mattress',"
                          " 'single_burner', 'crate_table')", (head,)):
        _set_condition(store, row["item_instance_id"], 0)
    set_needs(store, head, rest=50)
    needs_mod.apply_activity(store, head, "sleep", "home", 1, 480,
                             data=d)
    check(needs_mod.get_needs(store, head)["rest"] == 56,
          "needs: a broken-out F0 home sleeps at 0.7 (50 -> 56)")
    store = make_store()
    bare = make_person(store, age=35, first="Head")
    make_household(store, [bare])
    set_needs(store, bare, rest=50)
    needs_mod.apply_activity(store, bare, "sleep", "home", 1, 480,
                             data=d)
    check(needs_mod.get_needs(store, bare)["rest"] == 58,
          "needs: a genuinely bare character sleeps unscaled (58)")

    # 3. The decision is recorded in both GDDs.
    check("Update, Unit EZ" in gdd10 and "FLOOR rule" in gdd10,
          "GDD-10 §5: the EZ floor decision is recorded")
    check("breaking the last F0 piece" in gdd10,
          "GDD-10 §5: the F0-only edge is named")
    check("Update, Unit EZ" in gdd04 and "FLOOR rule" in gdd04,
          "GDD-04 §3.3: the EZ floor decision is recorded")
    check("Partial credit" in gdd10 or "partial credit" in gdd10,
          "GDD-10 §5: the rejected partial-credit rule is recorded")

    # 4. The tests pin it.
    check("test_no_tier_means_the_f0_floor" in needs_tests,
          "tests: the F0-floor test exists")
    check("test_f1_home_with_one_broken_f0_piece_gets_the_floor"
          in needs_tests,
          "tests: the F1 broken-F0 edge test exists")
    check("test_no_furniture_rows_means_no_scaling" in needs_tests,
          "tests: the genuinely-bare test exists")
    check("test_no_tier_means_no_scaling" not in needs_tests,
          "tests: the old unscaled-no-tier test is gone")
    check("the Unit EZ floor" in lost_tests,
          "tests: the lost-items multiplier test records the floor")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed, "
          f"{len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
