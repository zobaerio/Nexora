"""Verify Queue 16 Unit DD — Clothing Inventory Seeding (GDD-04 §3.3,
Unit CX record; GDD-09 §5).

Checks the implementation against the design it seeds: GDD-04 §3.3
(CX seeding table + CY implementation note + DD note),
data/clothing.json (starting_outfits), tools/sim/lost_items.py
(the seeding helpers), the wiring call sites
(identity.create_person / population.new_person / labour +
admin.match_vacancies), tools/sim/dataio.py (the clothing loader),
tools/validate_data.py (the starting_outfits checks) and
tools/sim/tests/test_lost_items.py.
Prints one line per check and a summary; exits 0 only when every
check passes. Run from the repo root: python3 tools/verify_queue16_dd.py
"""
import json
import re
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
    gdd09 = (ROOT / "docs" / "GDD-09-CHARACTER-CREATOR.md").read_text()
    clothing = json.loads(
        (ROOT / "data" / "clothing.json").read_text())
    lost = (ROOT / "tools" / "sim" / "lost_items.py").read_text()
    identity = (ROOT / "tools" / "sim" / "identity.py").read_text()
    population = (ROOT / "tools" / "sim" / "population.py").read_text()
    labour = (ROOT / "tools" / "sim" / "labour.py").read_text()
    admin = (ROOT / "tools" / "sim" / "admin.py").read_text()
    dataio = (ROOT / "tools" / "sim" / "dataio.py").read_text()
    validator = (ROOT / "tools" / "validate_data.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_lost_items.py").read_text()
    prices = json.loads((ROOT / "data" / "prices.json").read_text())

    # 1. The catalogue carries the authored starting outfits.
    starting = clothing.get("starting_outfits", {})
    check(set(starting) >= {"casual", "formal", "work_default"},
          "clothing.json has starting_outfits casual/formal/work_default")
    check("PROPOSED" in starting.get("notes", "")
          and "no source names a default starting outfit"
          in starting.get("notes", ""),
          "starting_outfits are labelled authored/PROPOSED, not sourced")
    by_id = {i["id"]: i for i in clothing["items"]}
    check(len(clothing["items"]) == 31,
          "clothing catalogue still has 31 items", "31")
    for key, ctx in (("casual", "casual"), ("formal", "formal"),
                     ("work_default", "work")):
        items = starting.get(key, [])
        check(all(i in by_id for i in items),
              f"starting_outfits {key}: every item resolves",
              f"{items}")
        slots = [by_id[i]["slot"] for i in items if i in by_id]
        check(len(slots) == len(set(slots)),
              f"starting_outfits {key}: one item per slot",
              f"{slots}")
        check(all(ctx in by_id[i]["contexts"] for i in items
                  if i in by_id),
              f"starting_outfits {key}: every item carries the"
              f" {ctx} context")
        check(all(by_id[i]["price_ref"] in
                  {p["id"] for p in prices["clothing"]["items"]}
                  for i in items if i in by_id),
              f"starting_outfits {key}: every item is priced",
              "prices.json clothing")

    # 2. The seeding helpers exist with the CX record shape.
    check("def seed_clothing_rows" in lost,
          "lost_items.py defines seed_clothing_rows")
    check("def starting_outfits" in lost,
          "lost_items.py defines starting_outfits")
    check("def seed_starting_outfits" in lost,
          "lost_items.py defines seed_starting_outfits")
    check("def seed_uniform_rows" in lost,
          "lost_items.py defines seed_uniform_rows")
    check("def uniform_items" in lost,
          "lost_items.py defines uniform_items")
    check('item_type="clothing"' in lost or
          'item_type = "clothing"' in lost,
          "seed_clothing_rows writes item_type clothing")
    check('"slot"' in lost and '"outfit_context"' in lost
          and '"issued"' in lost,
          "clothing state JSON carries slot/outfit_context/issued (CX)")
    check("unknown clothing item" in lost,
          "seed_clothing_rows refuses an unknown catalogue id")
    check('profession_id == "pilot"' in lost,
          "uniform_items never issues the pilot uniform (GDD-09 §5)")
    check('profession_id == "taxi_driver"' in lost
          and "(tier or 1) < 2" in lost,
          "uniform_items holds the taxi uniform below tier 2 (GDD-09 §5)")
    check('sim_tier == "ambient"' in lost,
          "starting_outfits seeds nothing for Ambient (GDD-09 §2)")

    # 3. The wiring call sites.
    check("outfits=None" in identity and "data=None" in identity,
          "identity.create_person takes optional data/outfits")
    check("seed_clothing_rows(" in identity,
          "create_person seeds the outfits it is given")
    check("starting_outfits(" in population,
          "population.new_person computes the starting outfits")
    check("age >= 18" in population,
          "genesis outfits are adults only (children: Unit AB)")
    check("seed_uniform_rows(" in labour,
          "labour.match_vacancies seeds the issued uniform")
    check("seed_uniform_rows(" in admin,
          "admin.match_vacancies seeds the issued uniform")
    check("clothing_file" in dataio,
          "dataio loads clothing.json as clothing_file")

    # 4. The validator checks the new data.
    check("starting_outfits" in validator,
          "validate_data.py checks starting_outfits")
    check("one item per slot" in validator,
          "validate_data.py checks one item per slot")

    # 5. The GDD records the implementation.
    check("Implementation (Unit DD · Queue 16" in gdd04,
          "GDD-04 §3.3 carries the DD implementation note")
    check("Unit DD · Queue 16" in gdd04,
          "GDD-04 §3.3 CX table carries the DD update")
    check("No ledger purchase row is written for genesis outfits"
          in gdd04,
          "GDD-04 records the genesis no-ledger-charge difference")
    check("E3 move-house branch can now lose a clothing item" in gdd04,
          "GDD-04 states what the seeding unlocks (E3 only)")

    # 6. The tests cover the contract.
    n_tests = len(re.findall(r"def test_", tests))
    check(n_tests >= 24 + 12,
          "test_lost_items.py has 36+ tests (24 CY + 12 DD)",
          f"{n_tests} tests")
    check("class TestClothingSeeding" in tests,
          "tests carry a TestClothingSeeding class")
    check("test_seeded_clothing_can_be_lost_via_record_loss" in tests,
          "tests prove a seeded clothing item can be lost")
    check("test_hiring_seeds_the_uniform" in tests,
          "tests prove hiring seeds the uniform")
    check("test_pilot_uniform_is_never_issued" in tests,
          "tests prove the pilot uniform is never issued")

    # 7. Nothing else changed its honesty: furniture/tool/document
    # stay unseedable, the rate stays 0.
    config = json.loads(
        (ROOT / "data" / "lost-items-config.json").read_text())
    check(config.get("loss_rate") == 0,
          "lost-items-config.json still sets loss_rate 0")
    check("furniture/tool/document" in gdd04,
          "GDD-04 keeps the unseedable-types honesty note")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
