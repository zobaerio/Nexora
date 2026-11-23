"""Verify Queue 15 Unit DB — Pair-Flag Server Schema Note
(GDD-15 §17.7 follow-up, TECH-PERSISTENT-WORLD Appendix C).

Checks the note against its sources: GDD-15 §17.7 (the pair store,
the merge rule, the four stored flags), the proven sim table in
tools/sim/persistence.py, and data/schema.sql (relationships.flags).
Prints one line per check and a summary; exits 0 only when every
check passes. Run from the repo root:
python3 tools/verify_queue15_db.py
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
    tech = (ROOT / "docs" / "TECH-PERSISTENT-WORLD.md").read_text()
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    persist = (ROOT / "tools" / "sim" / "persistence.py").read_text()
    schema = (ROOT / "data" / "schema.sql").read_text()

    app = tech.split("Appendix C — Relationship Pair Flags", 1)[1]
    check("Appendix C — Relationship Pair Flags" in tech,
          "Appendix C exists in TECH-PERSISTENT-WORLD.md")

    # 1. The migration statement matches the sim table exactly.
    check("004_relationship_pair_flags" in app,
          "proposed migration name follows 003 (004_relationship_pair_flags)")
    check("CREATE TABLE relationship_pair_flags" in app,
          "Appendix C carries the exact CREATE TABLE statement")
    check("CHECK (character_a_id < character_b_id)" in app,
          "the canonical pair key is the CHECK (a < b)")
    check("PRIMARY KEY (character_a_id, character_b_id)" in app,
          "the PK is the unordered pair")
    check("CHECK (character_a_id < character_b_id)" in persist,
          "the sim table carries the same CHECK (parity)")
    check("PRIMARY KEY (character_a_id, character_b_id)" in persist,
          "the sim table carries the same PK (parity)")

    # 2. The four stored flags, and the two that never move.
    for flag in ("met_player", "worked_with_player",
                 "employs_player", "apologised_for_offence"):
        check(flag in app, f"Appendix C names stored flag {flag}")
    check("are **not** backfilled" in app,
          "the debt flags are excluded from the backfill")
    check("flags = flags\n       - 'met_player'" in app
          or "- 'met_player' - 'worked_with_player'" in app,
          "the edge-clearing UPDATE removes exactly the four flags")

    # 3. The merge rule is the §17.7 rule, verbatim in substance.
    check("latest `last_interaction_at_game_minutes` wins" in app,
          "the backfill merge rule is latest-interaction wins")
    check("§17.2 edge priority" in app,
          "ties break by the §17.2 edge priority")
    check("in one transaction" in app and "same transaction" in app,
          "backfill and edge-clear run in one transaction")
    check("no down-migration" in app,
          "rollback posture is forward-only, no down-migration")

    # 4. The note does not claim a server exists.
    check("No server build, no netcode, no migration file exists yet"
          in app, "Appendix C states no server/migration file exists yet")
    check("NOT written into `data/schema.sql`" in app,
          "the note lives in the design doc, not in schema.sql")
    check("CREATE TABLE relationship_pair_flags" not in schema,
          "schema.sql is untouched (no pair-flag table there)")

    # 5. The GDD-15 CA paragraph records the note.
    check("Update, Unit DB · Queue 15" in gdd15,
          "GDD-15 §17.7 records the DB update")
    check("Appendix C" in gdd15,
          "GDD-15 points at Appendix C")

    # 6. The note's numbered steps are complete.
    steps = re.findall(r"^\d+\. \*\*", app, re.M)
    check(len(steps) >= 8, "Appendix C has the full numbered steps",
          f"{len(steps)} steps")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
