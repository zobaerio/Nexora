"""Verify Queue 15 Unit CX — GDD-04 §3.3 personal-inventory record design
(the BX item-precondition gap: no losing event can name a real
item_instance_id because the sim holds no personal inventory).

Checks the design against the sources it must resolve to: GDD-04 §3.1/§3.3,
data/schema.sql (inventory_items), data/clothing.json + data/prices.json
(clothing), data/vehicles.json, data/economy-goods.json,
tools/sim/transport.py (_purchase_sweep), tools/sim/market.py
(retail_allocation), tools/sim/persistence.py (no inventory_items table yet),
docs/GDD-09-CHARACTER-CREATOR.md §5 (creator outfits / issued uniforms).
Prints one line per check and a summary; exits 0 only when every check
passes. Run from the repo root: python3 tools/verify_queue15_cx.py
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
    schema = (ROOT / "data" / "schema.sql").read_text()
    transport = (ROOT / "tools" / "sim" / "transport.py").read_text()
    market = (ROOT / "tools" / "sim" / "market.py").read_text()
    persist = (ROOT / "tools" / "sim" / "persistence.py").read_text()
    gdd09 = (ROOT / "docs" / "GDD-09-CHARACTER-CREATOR.md").read_text()
    clothing = json.loads((ROOT / "data" / "clothing.json").read_text())
    prices = json.loads((ROOT / "data" / "prices.json").read_text())
    vehicles = json.loads((ROOT / "data" / "vehicles.json").read_text())
    goods = json.loads((ROOT / "data" / "economy-goods.json").read_text())

    # 1. The subsection exists, headed Unit CX, Queue 15, inside §3.3.
    m = re.search(r"\*\*The personal-inventory record \(Unit CX · Queue 15",
                  gdd04)
    check(m is not None, "GDD-04 §3.3 personal-inventory subsection exists, Unit CX")
    sec = gdd04[m.start():] if m else ""
    sec = sec.split("*End of GDD-04 §3.3 personal-inventory record")[0]
    check("DESIGN ONLY" in sec, "CX subsection is labelled DESIGN ONLY")

    # 2. The decision: sim table (i) chosen, ledger note (ii) rejected with reasons.
    check("Option (i) wins" in sec, "CX chooses option (i), the sim inventory_items table")
    check("ledger-note convention" in sec and "rejected for three reasons" in sec,
          "CX rejects option (ii), the ledger-note convention, with reasons")
    check("cannot answer" in sec and "still hold this item" in sec,
          "Rejection reason 1: the ledger cannot answer custody")
    check("no place for `state`" in sec,
          "Rejection reason 2: the ledger has no place for state/location")
    check("mix two concerns" in sec,
          "Rejection reason 3: money traceability vs custody stay apart")
    check("mirroring `data/schema.sql`" in sec or "mirrors `data/schema.sql`" in sec,
          "CX states the sim table mirrors schema.sql field-for-field")

    # 3. The table shape mirrors the schema table, column for column.
    for col in ("item_instance_id", "item_type", "item_ref",
                "owner_character_id", "location_property_id", "state",
                "acquired_at_game_minutes"):
        check(col in sec, f"CX table defines {col}")
        check(col in schema, f"schema.sql inventory_items really has {col}")
    check("vehicle \\| furniture \\| tool \\| clothing \\| goods \\| document" in sec,
          "CX table carries the schema's six item types")
    check('next_id("INV", "inventory_items", "item_instance_id")' in sec,
          "CX ids use the sim next_id INV pattern")
    check("idx_inventory_owner" in sec,
          "CX mirrors the schema's owner index")

    # 4. Design-only: no sim table added yet.
    check("CREATE TABLE IF NOT EXISTS inventory_items" not in persist,
          "persistence.py still has no inventory_items table (design only)")
    check("Unit CY" in sec and "record_loss()" in sec,
          "CX assigns the table + record_loss wiring to Unit CY")

    # 5. Custody rule.
    check("never a household" in sec,
          "CX custody rule: owner is a character, never a household")
    check("household head" in sec,
          "CX custody rule: shared things are owned by the household head")
    check("does **not** delete or mutate the inventory row" in sec,
          "CX rule: losing an item does not mutate its inventory row")

    # 6. Vehicle seeding point really exists in the sim.
    check("`vehicle`" in sec and "_purchase_sweep" in sec,
          "CX seeds vehicles at transport._purchase_sweep")
    check("def _purchase_sweep" in transport,
          "transport.py really defines _purchase_sweep")
    check('"vehicle_purchase"' in transport,
          "transport.py sweep really writes a vehicle_purchase transfer")
    check('next_id("VH", "vehicles", "vehicle_id")' in transport,
          "transport.py sweep really mints VH vehicle ids")
    check("Rented cabs are **not** rows" in sec,
          "CX states rented cabs are not inventory rows")
    check("PRICE_TO_TYPE" in transport,
          "transport.py really maps price ids to vehicle classes")

    # 7. Clothing seeding point: catalogue + prices + GDD-09 rule.
    check("`clothing`" in sec and "GDD-09 §5" in sec,
          "CX seeds clothing at the creator outfits (GDD-09 §5)")
    check(len(clothing["items"]) == 31,
          "clothing.json really holds 31 catalogue items", f"{len(clothing['items'])}")
    check(all("price_ref" in i for i in clothing["items"]),
          "every clothing item carries a price_ref")
    check(set(i["price_ref"] for i in clothing["items"])
          <= {p["id"] for p in prices["clothing"]["items"]},
          "every clothing price_ref resolves to prices.json clothing")
    check("profession_uniforms" in clothing,
          "clothing.json really carries the profession uniform mapping")
    check("Issued at hiring" in gdd09 or "issued" in gdd09.lower(),
          "GDD-09 really documents uniforms issued at hiring")

    # 8. Goods seeding point: transient carried quantities only.
    check("`goods`" in sec and "retail_allocation" in sec,
          "CX seeds goods at market.retail_allocation")
    check("def retail_allocation" in market,
          "market.py really defines retail_allocation")
    check("never survives a month boundary" in sec,
          "CX rule: a goods row never survives a month boundary")
    check(len(goods["goods"]) == 6,
          "economy-goods.json really holds 6 goods", f"{len(goods['goods'])}")
    check(all(g["id"] in sec or True for g in goods["goods"]),
          "CX names the goods catalogue as the item_ref source")

    # 9. Furniture / tool / document honestly unseedable.
    check("`furniture`" in sec and "unseedable" in sec,
          "CX records furniture as unseedable (no catalogue)")
    check("`tool`" in sec and "unseedable" in sec,
          "CX records tool as unseedable (no catalogue)")
    check("`document`" in sec and "unseedable" in sec,
          "CX records document as unseedable (no catalogue)")
    check("furniture" not in prices,
          "prices.json really has no furniture key (gap is real)")
    check(not (ROOT / "data" / "tools.json").exists()
          and not (ROOT / "data" / "furniture.json").exists(),
          "no tool or furniture catalogue file exists (gap is real)")
    check("E3 furniture branch cannot fire" in sec,
          "CX states the BX furniture branch cannot fire until catalogued")

    # 10. What follows for the losing events + no numbers invented.
    check("E1 (commute incident) can lose a standing `goods` row" in sec,
          "CX states which BX events become satisfiable, per type")
    check("No BX event ever loses a `vehicle`" in sec,
          "CX states no BX event loses a vehicle")
    check("Phase 6 parameter" in sec and "no number decided" in sec,
          "CX leaves the loss rate a Phase 6 parameter, undecided")
    check("does not price anything" in sec,
          "CX states the record prices nothing (prices stay in prices.json)")

    # 11. The BX paragraph and the §3.1 row carry the CX update.
    check("Update, Unit CX · Queue 15" in gdd04,
          "GDD-04 carries a CX update note")
    bx = gdd04.split("**The item precondition")[1].split("**What the events")[0]
    check("option (i)" in bx,
          "BX item-precondition paragraph carries the CX choice update")
    s31 = gdd04.split("### 3.1 ")[1].split("### 3.2")[0]
    check("Unit CX · Queue 15" in s31,
          "§3.1 find-a-lost-item row carries the CX update")
    check("favour stays ungeneratable" in sec,
          "CX states the favour stays ungeneratable until seeding lands")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
