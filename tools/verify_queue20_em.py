"""Verify Queue 20 Unit EM — F2/F3 Furniture Purchase Point
(GDD-10 §5, GDD-04 §3.3; DQ follow-up).

Checks the specified purchase point against its sources:
data/furniture.json (the catalogue), data/prices.json (the
catalogue prices — PROPOSED, summing to the §5 Tier-3 packages),
GDD-10 §5 (the purchase-point bullet) and GDD-04 §3.3 (the EM
implementation note). Design + data only: no furniture purchase
event exists in the sim, so no sim change lands in this unit —
the script asserts that limit too. Prints one line per check and
a summary; exits 0 only when every check passes.
Run from the repo root: python3 tools/verify_queue20_em.py
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
    furniture = json.loads((ROOT / "data" / "furniture.json").read_text())
    prices = json.loads((ROOT / "data" / "prices.json").read_text())
    sim = "".join(p.read_text() for p in
                  (ROOT / "tools" / "sim").glob("*.py"))

    # 1. Every F2/F3 piece's price resolves, and is above 0.
    priced = {i["id"]: i["price_ncr"]
              for i in prices["furniture"]["items"]}
    f2 = [i for i in furniture["items"] if i["tier"] == "F2"]
    f3 = [i for i in furniture["items"] if i["tier"] == "F3"]
    check(len(f2) == 5 and len(f3) == 5,
          "the catalogue carries 5 F2 + 5 F3 pieces",
          f"found {len(f2)} F2, {len(f3)} F3")
    for piece in f2 + f3:
        ref = piece["price_ref"]
        check(ref in priced,
              f"{piece['id']} price_ref resolves in prices.json")
        check(priced.get(ref, 0) > 0,
              f"{piece['id']} is priced above 0 (not a free piece)",
              f"{priced.get(ref)} NCr")

    # 2. The piece prices sum to the §5 Tier-3 packages.
    f1 = [i for i in furniture["items"] if i["tier"] == "F1"]
    check(sum(priced[i["price_ref"]] for i in f1) == 12000,
          "F1 pieces sum to the §5 Tier-3 F1 package (12,000)")
    check(sum(priced[i["price_ref"]] for i in f2) == 12000,
          "F2 additions sum to 12,000 (F2 package 24,000)")
    check(sum(priced[i["price_ref"]] for i in f3) == 18000,
          "F3 additions sum to 18,000 (F3 package 42,000)")

    # 3. The purchase point is specified in both documents.
    check("F2/F3 pieces are bought, not seeded" in gdd10,
          "GDD-10 §5 carries the F2/F3 purchase-point bullet")
    check("purchase_furniture()" in gdd10,
          "GDD-10 §5 names the purchase event (Phase 5/6 home loop)")
    check("**Implementation (Unit EM" in gdd04,
          "GDD-04 §3.3 carries the EM implementation note")
    check("no furniture purchase event exists" in gdd04,
          "the EM note records the honest limit (design + data, "
          "no sim change)")
    check("second row for a piece the head already holds" in gdd10,
          "the replacement-row rule is specified (seeding skip "
          "does not apply to purchases)")

    # 4. No sim change was smuggled in: no purchase_furniture
    # function exists anywhere in the sim.
    check("def purchase_furniture(" not in sim,
          "no purchase_furniture function exists in the sim yet")
    check("purchase_furniture" in gdd10 and
          "purchase_furniture" in gdd04,
          "the event is named in the docs only, not the code")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
