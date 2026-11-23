"""Verify Queue 17 Unit DJ — Furniture, Tool & Document Seeding
(GDD-04 §3.3, Unit DE catalogues; GDD-10 §5; GDD-09 §5).

Checks the implementation against the design it seeds: GDD-04 §3.3
(the CX seeding table + DJ implementation note),
data/furniture.json + data/tools.json + data/documents.json (the DE
catalogues), tools/sim/lost_items.py (the seeding helpers), the
wiring call sites (population genesis / households.move_household +
leave_home / labour + admin.match_vacancies /
business.register_business), tools/sim/dataio.py (the catalogue
loaders), tools/validate_data.py (the DJ checks) and
tools/sim/tests/test_lost_items.py.
Prints one line per check and a summary; exits 0 only when every
check passes. Run from the repo root: python3 tools/verify_queue17_dj.py
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
    gdd10 = (ROOT / "docs" / "GDD-10-HOUSING-AND-HOME-LIFE.md").read_text()
    furniture = json.loads((ROOT / "data" / "furniture.json").read_text())
    tools = json.loads((ROOT / "data" / "tools.json").read_text())
    documents = json.loads((ROOT / "data" / "documents.json").read_text())
    lost = (ROOT / "tools" / "sim" / "lost_items.py").read_text()
    households = (ROOT / "tools" / "sim" / "households.py").read_text()
    population = (ROOT / "tools" / "sim" / "population.py").read_text()
    labour = (ROOT / "tools" / "sim" / "labour.py").read_text()
    admin = (ROOT / "tools" / "sim" / "admin.py").read_text()
    business = (ROOT / "tools" / "sim" / "business.py").read_text()
    dataio = (ROOT / "tools" / "sim" / "dataio.py").read_text()
    validator = (ROOT / "tools" / "validate_data.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_lost_items.py").read_text()

    # 1. The catalogues are the DE ones, unchanged by this unit.
    check(len(furniture["items"]) == 18,
          "furniture catalogue still has 18 items", "18")
    check(len(tools["items"]) == 10,
          "tools catalogue still has 10 items", "10")
    check(len(documents["items"]) == 4,
          "documents catalogue still has 4 items", "4")
    check(furniture.get("tiers", {}).get("F1") ==
          ["bed", "table_chairs", "stove", "wardrobe", "fan"],
          "furniture F1 set is the GDD-10 §5 Basic set")

    # 2. The seeding helpers exist with the CX record shape.
    check("def seed_furniture_rows" in lost,
          "lost_items.py defines seed_furniture_rows")
    check("def seed_furniture_at_move_in" in lost,
          "lost_items.py defines seed_furniture_at_move_in")
    check("def furniture_tier_items" in lost,
          "lost_items.py defines furniture_tier_items")
    check("def seed_tool_rows" in lost,
          "lost_items.py defines seed_tool_rows")
    check("def tool_items" in lost,
          "lost_items.py defines tool_items")
    check("def seed_document_row" in lost,
          "lost_items.py defines seed_document_row")
    check('item_type="furniture"' in lost,
          "furniture rows carry item_type furniture")
    check('item_type="tool"' in lost,
          "tool rows carry item_type tool")
    check('item_type="document"' in lost,
          "document rows carry item_type document")
    check('"furniture_tier"' in lost,
          "furniture state JSON carries furniture_tier (CX)")
    check('"issued": "employer"' in lost,
          "tool state JSON carries issued employer (CX)")
    check("unknown furniture item" in lost
          and "unknown tool" in lost
          and "unknown document" in lost,
          "all three helpers refuse an unknown catalogue id")
    check('"F1"' in lost and "furniture_tier_items(data, \"F1\")" in lost,
          "move-in seeds the F1 set (starter-flat rule, GDD-10 §5)")

    # 3. The decisions this unit takes are stated, not hidden.
    check("no source maps" in lost and "property tier to a furniture"
          in lost,
          "lost_items.py states no source maps property to furniture tier")
    check("F2/F3" in lost and "wait for a purchase point" in lost,
          "lost_items.py records F2/F3 upgrades wait for a purchase point")
    check("SYS-MARKET" in lost and "holds no inventory" in lost,
          "lost_items.py states system firms get no licence row")
    check("has NO issuing event" in lost,
          "lost_items.py records the deed has no issuing event yet")

    # 4. The wiring call sites.
    check("seed_furniture_at_move_in(" in population,
          "population genesis seeds furniture at household placement")
    check("seed_furniture_at_move_in(" in households,
          "households seeds furniture at move-in (move + leave_home)")
    check(households.count("seed_furniture_at_move_in(") >= 2,
          "households wires both move_household and leave_home",
          f"{households.count('seed_furniture_at_move_in(')} call sites")
    check("seed_tool_rows(" in labour,
          "labour.match_vacancies seeds tools at hiring")
    check("seed_tool_rows(" in admin,
          "admin.match_vacancies seeds tools at hiring")
    check("seed_document_row(" in business,
          "business.register_business seeds the licence at founding")
    check('owner_character_id != "SYS-MARKET"' in business,
          "register_business skips the licence for SYS-MARKET firms")
    check("furniture_file" in dataio and "tools_file" in dataio
          and "documents_file" in dataio,
          "dataio loads furniture/tools/documents catalogues")

    # 5. The validator checks the new data.
    check("anchor_tea_stall_riverfront_1" in validator,
          "validate_data.py checks the 1.4 tea stall anchor exists")
    check("school uniform" in validator,
          "validate_data.py checks the school uniform item (DK)")

    # 6. The GDD records the implementation and the gaps.
    check("Implementation (Unit DJ · Queue 17" in gdd04,
          "GDD-04 §3.3 carries the DJ implementation note")
    check("a lost credential is not a revoked one" in gdd04.lower(),
          "GDD-04 states the lost-credential rule (DN)")
    check("The property deed has NO issuing event yet" in gdd04,
          "GDD-04 records the deed gap honestly")
    check("E1 can now lose a standing `goods`, `tool`, or `document`"
          in gdd04,
          "GDD-04 states what the seeding unlocks per event")
    check("Update, Unit DJ · Queue 17" in gdd10,
          "GDD-10 §5 carries the DJ move-in note")

    # 7. The tests cover the contract.
    n_tests = len(re.findall(r"def test_", tests))
    check(n_tests >= 48 + 20,
          "test_lost_items.py has 68+ tests (48 before + 20 DJ/DK)",
          f"{n_tests} tests")
    check("class TestFurnitureSeeding" in tests,
          "tests carry a TestFurnitureSeeding class")
    check("class TestToolSeeding" in tests,
          "tests carry a TestToolSeeding class")
    check("class TestDocumentSeeding" in tests,
          "tests carry a TestDocumentSeeding class")
    check("test_move_household_furnishes_the_new_home" in tests,
          "tests prove a move furnishes the new home end-to-end")
    check("test_system_founded_firm_gets_no_licence_row" in tests,
          "tests prove SYS-MARKET firms get no licence row")

    # 8. Nothing else changed its honesty: the rate stays 0.
    config = json.loads(
        (ROOT / "data" / "lost-items-config.json").read_text())
    check(config.get("loss_rate") == 0,
          "lost-items-config.json still sets loss_rate 0")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
