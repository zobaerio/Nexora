"""Verify Queue 20 Unit EI — Lost-Piece vs Effective-Tier Decision
(GDD-04 §3.3, GDD-10 §5; Unit EF follow-up).

Checks the decision against its sources: tools/sim/lost_items.py
(effective_furniture_tier + _item_is_away), GDD-04 §3.3 (the EI
implementation note, superseding EF's open question), GDD-10 §5
(the effect bullet), and the tests (test_lost_items.py
TestLostPieceVsTier). Prints one line per check and a summary;
exits 0 only when every check passes.
Run from the repo root: python3 tools/verify_queue20_ei.py
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
    gdd10 = (ROOT / "docs" / "GDD-10-HOUSING-AND-HOME-LIFE.md").read_text()
    lost_items = (ROOT / "tools" / "sim" / "lost_items.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_lost_items.py").read_text()

    # 1. The decision is implemented in effective_furniture_tier.
    check("def _item_is_away(" in lost_items,
          "lost_items.py defines _item_is_away")
    away = lost_items.split("def _item_is_away(")[1] \
        .split("def effective_furniture_tier(")[0]
    check("status IN ('lost', 'found')" in away,
          "a standing lost OR found row means the piece is away")
    tier = lost_items.split("def effective_furniture_tier(")[1] \
        .split("def furniture_restore_multiplier(")[0]
    check("_item_is_away(" in tier,
          "the tier check reads whether each piece is away")
    check("or stands" in tier,
          "a second row of one piece keeps the tier (any row stands)")
    check("A lost piece still counts" not in lost_items,
          "the EF open-question wording is gone (decided, not open)")

    # 2. The design records the decision and its reasoning.
    check("**Implementation (Unit EI" in gdd04,
          "GDD-04 §3.3 carries the EI implementation note")
    check("DECIDED" in gdd04.split("**Implementation (Unit EI")[1]
          .split("*End of GDD-04")[0],
          "the EI note states the decision (lost drops the tier)")
    check("Unit EI" in gdd10,
          "GDD-10 §5 carries the EI update on the effect bullet")
    check("hand-back restores the tier" in gdd04
          or "hand-back restoring the tier" in gdd04,
          "the reversibility (hand-back restores the tier) is stated")

    # 3. The tests prove both cases.
    check("class TestLostPieceVsTier" in tests,
          "test_lost_items.py has the lost-piece-vs-tier tests")
    for name in ("test_a_lost_piece_drops_the_tier",
                 "test_a_found_piece_still_drops_the_tier",
                 "test_the_hand_back_restores_the_tier",
                 "test_a_broken_piece_drops_the_tier_the_same_way",
                 "test_a_lost_f0_piece_leaves_no_tier_standing",
                 "test_a_second_row_of_the_piece_keeps_the_tier"):
        check(name in tests, f"test_lost_items.py has {name}")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
