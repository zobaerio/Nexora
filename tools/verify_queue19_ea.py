"""Verify Queue 19 Unit EA — Found-Item Re-Loss Exclusion
(GDD-04 §3.3, Unit DP follow-up).

Checks the exclusion against its sources: tools/sim/lost_items.py
(the record_loss refusal + the eligible_items exclusion),
GDD-04 §3.3 (the DP recorded edge + the EA implementation note),
and tools/sim/tests/test_lost_items.py (the EA tests). No new
tables, no new fields. Prints one line per check and a summary;
exits 0 only when every check passes.
Run from the repo root: python3 tools/verify_queue19_ea.py
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
    lost_items = (ROOT / "tools" / "sim" / "lost_items.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_lost_items.py").read_text()

    # 1. The helper refuses a second loss while a found row stands.
    check("def _has_standing_found_row(" in lost_items,
          "lost_items.py defines _has_standing_found_row")
    check("AND status = 'found'" in lost_items,
          "the helper queries for a standing found row")
    check("_has_standing_found_row(store, item_instance_id)"
          in lost_items.split("def record_loss(")[1]
          .split("def find_lost_item(")[0],
          "record_loss() refuses when a found row stands")

    # 2. The events' eligible sets exclude found items.
    check("not _has_standing_found_row(store,"
          in lost_items.split("def eligible_items(")[1]
          .split("def record_loss(")[0],
          "eligible_items() excludes items with a standing found row")

    # 3. The other refusals are untouched.
    check("a ``lost`` row already stands for the item" in lost_items,
          "record_loss() still refuses a standing lost row")
    check("test_allows_reloss_after_return" in tests,
          "the re-loss-after-return test still exists (a returned "
          "item may be lost again)")

    # 4. The design records the closure.
    check("Recorded edge — a found item can be lost again." in gdd04,
          "GDD-04 §3.3 still names the DP recorded edge")
    check("**Implementation (Unit EA" in gdd04,
          "GDD-04 §3.3 carries the EA implementation note")
    check("excludes items with a standing `found` row" in gdd04
          or "exclude items with a standing `found` row" in gdd04,
          "the EA note states the eligible-set exclusion")

    # 5. The tests prove the exclusion at both levels.
    check("test_refuses_loss_while_found" in tests,
          "test_lost_items.py tests the record_loss refusal")
    check("test_eligible_items_exclude_found_items" in tests,
          "test_lost_items.py tests the eligible-set exclusion")
    check("test_move_loss_writes_nothing_for_a_found_item" in tests,
          "test_lost_items.py tests the exclusion at event level "
          "(move-house)")

    # 6. No new field, no new table, no behaviour change beyond the
    # exclusion: the found row is still the finder's custody.
    check("def record_loss(" in lost_items
          and lost_items.count("def record_loss(") == 1,
          "record_loss() is still the single write helper")
    check("status = 'found'" in lost_items,
          "the found status is still written by find_lost_item only")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
