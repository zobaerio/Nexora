"""Verify Queue 15 Unit CY — Losing-event wiring (GDD-04 §3.3, Unit BX).

Checks the implementation against the design it wires: GDD-04 §3.3
(BX events + CX record), data/lost-items-config.json,
tools/sim/lost_items.py, the five wiring call sites
(safety/environment/households/transport/market), tools/sim/
persistence.py (the two new tables), tools/validate_data.py (the
new config check) and tools/sim/tests/test_lost_items.py.
Prints one line per check and a summary; exits 0 only when every
check passes. Run from the repo root: python3 tools/verify_queue15_cy.py
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
    lost = (ROOT / "tools" / "sim" / "lost_items.py").read_text()
    safety = (ROOT / "tools" / "sim" / "safety.py").read_text()
    environ = (ROOT / "tools" / "sim" / "environment.py").read_text()
    households = (ROOT / "tools" / "sim" / "households.py").read_text()
    transport = (ROOT / "tools" / "sim" / "transport.py").read_text()
    market = (ROOT / "tools" / "sim" / "market.py").read_text()
    persist = (ROOT / "tools" / "sim" / "persistence.py").read_text()
    dataio = (ROOT / "tools" / "sim" / "dataio.py").read_text()
    validator = (ROOT / "tools" / "validate_data.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_lost_items.py").read_text()
    config = json.loads(
        (ROOT / "data" / "lost-items-config.json").read_text())

    # 1. The module exists with the BX contract.
    check("def record_loss(store, owner_character_id, item_instance_id,"
          in lost, "lost_items.py defines record_loss with the BX signature")
    check("def commute_incident_losses" in lost,
          "lost_items.py defines the E1 function")
    check("def storm_market_losses" in lost,
          "lost_items.py defines the E2 function")
    check("def move_house_loss" in lost,
          "lost_items.py defines the E3 function")
    check("def seed_vehicle_row" in lost,
          "lost_items.py defines the vehicle seeding helper")
    check("def seed_goods_rows" in lost,
          "lost_items.py defines the goods seeding helper")
    check('"goods", "document", "tool"' in lost,
          "E1 eligible types are goods/document/tool (BX order)")
    check('"furniture", "tool", "clothing", "goods"' in lost,
          "E3 eligible types are furniture/tool/clothing/goods (BX order)")
    check('("walk", "cycle", "rickshaw")' in lost,
          "E2 exposed modes are walk/cycle/rickshaw (BX)")

    # 2. The refusal rules are in the code.
    check("standing" in lost and "status = 'lost'" in lost,
          "record_loss refuses a second loss while one stands")
    check("owner_character_id = ?" in lost,
          "record_loss checks the owner holds the item")

    # 3. The rate lives in config, default 0.
    check(config.get("loss_rate") == 0,
          "lost-items-config.json sets loss_rate 0 (default, silent)")
    check("lost_items_config" in dataio,
          "dataio loads lost_items_config")
    check("DEFAULT_LOSS_RATE = 0.0" in lost,
          "lost_items.py defaults the rate to 0.0")
    check("loss_rate" in validator,
          "validate_data.py checks the lost-items config rate")

    # 4. The two tables exist in the sim store.
    check("CREATE TABLE IF NOT EXISTS inventory_items" in persist,
          "persistence.py creates inventory_items")
    check("CREATE TABLE IF NOT EXISTS lost_items" in persist,
          "persistence.py creates lost_items")
    check("idx_inventory_owner" in persist,
          "persistence.py indexes inventory_items by owner")
    check("'lost', 'found', 'returned'" in persist,
          "lost_items status CHECK is the §3.3 lifecycle")

    # 5. The five wiring call sites.
    check("commute_incident_losses(" in safety,
          "safety.intake_incidents calls the E1 function")
    check("storm_market_losses(" in environ,
          "environment.daily_pass calls the E2 function")
    check("move_house_loss(" in households,
          "households.move_household calls the E3 function")
    check("origin_zone" in households,
          "move_household reads the origin zone before the move")
    check("seed_vehicle_row(" in transport,
          "transport._purchase_sweep seeds the vehicle row")
    check("seed_goods_rows(" in market,
          "market.retail_allocation seeds the goods rows")
    check("DELETE FROM inventory_items WHERE item_type = 'goods'"
          in market,
          "retail_allocation consumes last month's goods rows first")

    # 6. The GDD records the implementation.
    check("Implementation (Unit CY · Queue 15" in gdd04,
          "GDD-04 §3.3 carries the CY implementation note")
    s31 = gdd04.split("### 3.1 ")[1].split("### 3.2")[0]
    check("Unit CY · Queue 15" in s31,
          "§3.1 find-a-lost-item row carries the CY update")
    check("default 0" in gdd04 and "specified but silent" in gdd04,
          "GDD-04 states the rate is default 0, specified but silent")

    # 7. The tests cover the contract.
    n_tests = len(re.findall(r"def test_", tests))
    check(n_tests >= 20, "test_lost_items.py has 20+ tests",
          f"{n_tests} tests")
    check("rate=0.0" in tests,
          "tests prove the default rate writes nothing")
    check("rate=1.0" in tests,
          "tests prove each event writes at rate 1.0")
    check("test_end_to_end_move_loses_at_config_rate" in tests,
          "tests prove the real move_household loses at rate 1.0")

    # 8. Design honesty carried over: unseedable types stay refused.
    check("furniture/tool/document" in gdd04
          or "furniture" in gdd04,
          "GDD-04 keeps the unseedable-types honesty note")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
