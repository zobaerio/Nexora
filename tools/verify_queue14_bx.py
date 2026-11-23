"""Verify Queue 14 Unit BX — GDD-04 §3.3 lost-item losing event design
(the BL §3.3 event gap: no merged event writes a loss yet).

Checks the design against the sources it must resolve to: GDD-04 §3.1/§3.3,
GDD-15 §18, data/schema.sql (inventory_items), tools/sim/safety.py
(traffic_accident), tools/sim/environment.py (disaster_impacts),
tools/sim/transport.py (trips), tools/sim/households.py (move_household),
tools/sim/persistence.py (no personal inventory table).
Prints one line per check and a summary; exits 0 only when every check
passes. Run from the repo root: python3 tools/verify_queue14_bx.py
"""
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
    safety = (ROOT / "tools" / "sim" / "safety.py").read_text()
    environ = (ROOT / "tools" / "sim" / "environment.py").read_text()
    transport = (ROOT / "tools" / "sim" / "transport.py").read_text()
    households = (ROOT / "tools" / "sim" / "households.py").read_text()
    persist = (ROOT / "tools" / "sim" / "persistence.py").read_text()

    # 1. The subsection exists, headed Unit BX, Queue 14.
    m = re.search(r"\*\*The losing events \(Unit BX · Queue 14", gdd04)
    check(m is not None, "GDD-04 §3.3 losing-events subsection exists, Unit BX")
    sec = gdd04[m.start():] if m else ""
    sec = sec.split("*End of GDD-04 §3.3 losing events")[0]

    # 2. The write contract: one helper, named, with the refusal rule.
    check("record_loss(store, owner_character_id, item_instance_id, "
          "game_minutes, lost_zone, lost_anchor=None)" in sec,
          "§3.3 names the record_loss helper with its full signature")
    check("tools/sim/lost_items.py" in sec,
          "§3.3 places the helper in a new tools/sim/lost_items.py module")
    check("refuses" in sec and "writes no row" in sec,
          "§3.3 states the helper refuses when the precondition fails")

    # 3. Three events, each grounded in a real merged system.
    for ev in ("Commute incident", "Storm-soaked market trip",
               "Move-house"):
        check(ev in sec, f"§3.3 designs the {ev.lower()} losing event")
    check("traffic_accident" in sec and "intake_incidents" in sec,
          "E1 cites safety.intake_incidents traffic_accident")
    check("segment_ids" in sec and "trips" in sec,
          "E1 attributes via trips.segment_ids")
    check("disaster_impacts" in sec and "cyclone" in sec,
          "E2 cites environment disaster_events/disaster_impacts")
    check("move_household" in sec,
          "E3 cites households.move_household")
    check("destination_zone" in sec,
          "E1/E2 lost_zone comes from the trip's destination_zone")

    # 4. The cited sources really exist in the code.
    check("traffic_accident" in safety,
          "safety.py really creates traffic_accident incidents")
    check("segment_id" in safety,
          "safety.py traffic_accident details carry segment_id")
    check("disaster_impacts" in environ,
          "environment.py really writes disaster_impacts rows")
    check("segment_ids" in transport,
          "transport.py trips really carry segment_ids")
    check("def move_household" in households,
          "households.py really defines move_household")

    # 5. Zone/anchor rules per event.
    check("lost_anchor` = null" in sec or "lost_anchor = null" in sec,
          "E1/E3 record lost_anchor null (segment/home is not an anchor)")
    check("lost_anchor` = `market`" in sec,
          "E2 records lost_anchor market (destination anchor known)")
    check("goods" in sec and "document" in sec and "tool" in sec,
          "§3.3 restricts item types per event from the schema vocabulary")

    # 6. The rate is a Phase 6 parameter, no number invented.
    check("Phase 6 parameter" in sec and "no number decided here" in sec,
          "§3.3 leaves the loss rate a Phase 6 parameter, undecided")

    # 7. The item precondition — the honest open gap.
    check("holds no personal inventory" in sec,
          "§3.3 records the sim holds no personal inventory")
    check("inventory_items" in sec,
          "§3.3 names inventory_items as the required row")
    check("Queue 15" in sec,
          "§3.3 assigns the personal-inventory record to Queue 15")
    check("CREATE TABLE IF NOT EXISTS inventory_items" not in persist,
          "persistence.py really has no inventory_items table (gap is real)")
    check("business_inventory" in persist,
          "persistence.py has only business/medical inventory (gap check)")

    # 8. §3.1 status line updated, and the favour stays ungeneratable live.
    check("Unit BX · Queue 14" in gdd04.split("### 3.1 ")[1].split("### 3.2")[0]
          if "### 3.1 " in gdd04 else False,
          "§3.1 find-a-lost-item row carries the BX update")
    check("stays ungeneratable in live worlds" in sec
          or "the favour stays ungeneratable" in sec,
          "§3.3 states the favour stays ungeneratable until wiring lands")

    # 9. Schema vocabulary the design relies on.
    check("item_type" in schema and "vehicle | furniture | tool | clothing"
          in schema,
          "schema.sql inventory_items carries the item_type vocabulary")
    check("lost_items" not in schema,
          "schema.sql has no lost_items table yet (Phase 6/9 record)")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
