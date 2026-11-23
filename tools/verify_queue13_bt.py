"""Verify Queue 13 Unit BT — GDD-04 §5.1 achievements keying decision
(the account wins over the schema's character_id key).

Checks the decision against the sources it must resolve to: GDD-04 §5/
§3.4, data/schema.sql (accounts/achievements), GDD-01 §1.
Prints one line per check and a summary; exits 0 only when every check
passes. Run from the repo root: python3 tools/verify_queue13_bt.py
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
    gdd01 = (ROOT / "docs" / "GDD-01-LIFE-AND-DATA-MODEL.md").read_text()
    schema = (ROOT / "data" / "schema.sql").read_text()

    # 1. §5.1 exists, headed Unit BT, Queue 13.
    m51 = re.search(r"### 5\.1 Achievement keying — the account wins "
                    r"\(Unit BT · Queue 13", gdd04)
    check(m51 is not None, "GDD-04 §5.1 exists, headed Unit BT, Queue 13")
    sec = gdd04[m51.start():] if m51 else ""
    sec = sec.split("*End of GDD-04 §5.1")[0]

    # 2. The decision is stated, with its two sources.
    check("The decision: the account wins" in sec,
          "§5.1 decides: the account wins")
    check("GDD-01 §1" in sec and "Account-level data (achievements" in sec,
          "§5.1 cites GDD-01 §1 account-level rule")
    check("The schema's `character_id` key is the error" in sec,
          "§5.1 names the schema key as the error, not the rule")

    # 3. The discrepancy is quoted exactly as BM recorded it.
    check("keyed by `character_id`" in sec
          and "achievement data lives on the account" in sec,
          "§5.1 states the BM discrepancy verbatim")

    # 4. The migration consequence: forward-only, numbered steps.
    check("forward-only" in sec, "§5.1 states the migration is forward-only")
    check("ADD COLUMN account_id" in sec,
          "§5.1 gives the add-column step")
    check("Backfill" in sec and "characters.account_id" in sec,
          "§5.1 gives the backfill step from characters.account_id")
    check("PRIMARY KEY (account_id, achievement_id)" in sec,
          "§5.1 gives the re-key step")
    check("no down-migration" in sec,
          "§5.1 states there is no down-migration")

    # 5. No live rows exist to migrate (both stores checked).
    check("no achievements table" in sec and "tools/sim/" in sec,
          "§5.1 records the sim has no achievements table")
    check("Phase 9 server draft, un-deployed" in sec
          or "Phase 9 draft" in sec,
          "§5.1 records schema.sql is the un-deployed Phase 9 draft")
    check("migrates zero rows" in sec,
          "§5.1 states the backfill migrates zero rows today")

    # 6. NPC rows with NULL account_id are counted, not silently kept.
    check("NULL" in sec and "out-of-scope data" in sec,
          "§5.1 handles NULL-account rows by counting, not hiding")

    # 7. discovery_progress is unchanged and now consistent.
    check("Nothing changes" in sec and "already keys it by `account_id`"
          in sec,
          "§5.1 states discovery_progress is unchanged (§3.4)")
    check("same key" in sec,
          "§5.1 states achievements + discovery_progress now agree on the key")

    # 8. What does not change: list, tiers, unlock rules; no sim table.
    check("The achievement list, the tiers, and the unlock rules" in sec
          and "untouched" in sec,
          "§5.1 states the list/tiers/rules are untouched")
    check("no achievements table from this unit" in sec
          or "gains no achievements table" in sec,
          "§5.1 adds no sim achievements table")

    # 9. schema.sql still carries the character_id key (no DDL applied)
    #    and the decision comment.
    ach = re.search(r"CREATE TABLE achievements \((.*?)\);", schema, re.S)
    check(ach is not None and "PRIMARY KEY (character_id, achievement_id)"
          in ach.group(1),
          "schema.sql achievements table is unchanged (no DDL applied)")
    check("KEYING DECISION (Unit BT" in schema
          and "GDD-04 §5.1" in schema,
          "schema.sql carries the BT decision comment")
    check("No DDL is applied by this unit" in schema,
          "schema.sql comment states no DDL was applied")

    # 10. The sources agree: GDD-01 §1 says account-level; §5 says account.
    check("Account-level data (achievements, friends, settings) survives "
          "character death" in gdd01,
          "GDD-01 §1 states achievements are account-level")
    check("Achievement data lives on the **account**" in gdd04,
          "GDD-04 §5 states achievements live on the account")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed; "
          f"{len(failed)} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
