"""Verify Queue 10 Unit BD — ledger idempotency key home (AW OD-8).

Checks the decision against the sources it must resolve to:
TECH-PERSISTENT-WORLD §2/§7/§10 + Appendix A/B, TECH-MULTIPLAYER §6,
TECH-CHECKPOINT-RUNBOOK OD-8, data/schema.sql, tools/sim/persistence.py.
Prints one line per check and a summary; exits 0 only when every
check passes. Run from the repo root: python3 tools/verify_queue10_bd.py
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
    tpw = (ROOT / "docs" / "TECH-PERSISTENT-WORLD.md").read_text()
    schema = (ROOT / "data" / "schema.sql").read_text()
    multi = (ROOT / "docs" / "TECH-MULTIPLAYER.md").read_text()
    runbook = (ROOT / "docs" / "TECH-CHECKPOINT-RUNBOOK.md").read_text()
    persist = (ROOT / "tools" / "sim" / "persistence.py").read_text()

    # 1. §10 and Appendix B exist.
    check("## 10. Ledger Idempotency Key Home" in tpw,
          "TECH-PERSISTENT-WORLD §10 exists")
    check("# Appendix B — Ledger Idempotency Keys" in tpw,
          "TECH-PERSISTENT-WORLD Appendix B exists")

    # 2. The exact DDL appears in both §10.1 and §B.1.
    ddl = ["ALTER TABLE economy_ledger ADD COLUMN transfer_key TEXT;",
           "ALTER TABLE economy_ledger ADD COLUMN event_ref TEXT;",
           "CREATE UNIQUE INDEX idx_ledger_transfer_key"
           " ON economy_ledger (transfer_key);"]
    sec10 = tpw.split("## 10. Ledger Idempotency Key Home")[1].split(
        "# Appendix A")[0]
    appb = tpw.split("# Appendix B")[1]
    for stmt in ddl:
        check(stmt in sec10, f"§10.1 carries DDL: {stmt[:45]}…")
        check(stmt in appb, f"Appendix B carries DDL: {stmt[:45]}…")

    # 3. Design only: schema.sql still has no transfer_key/event_ref.
    ledger = re.search(r"CREATE TABLE economy_ledger \(.*?\);",
                       schema, re.S).group(0)
    check("transfer_key" not in ledger and "event_ref" not in ledger,
          "schema.sql economy_ledger still has no key columns (design only)")

    # 4. Parity with the proven sim store: the sim carries both columns
    # and the same-named unique index.
    check('("economy_ledger", "transfer_key", "TEXT")' in persist,
          "sim persistence.py migrates economy_ledger.transfer_key")
    check('("economy_ledger", "event_ref", "TEXT")' in persist,
          "sim persistence.py migrates economy_ledger.event_ref")
    check("CREATE UNIQUE INDEX IF NOT EXISTS idx_ledger_transfer_key"
          in persist,
          "sim carries the same-named unique index")

    # 5. The server rule mirrors Store.transfer (same key, same row).
    check("Same key, same row, never a duplicate charge" in sec10,
          "§10.2 states the same-key-same-row rule")
    check("one transaction" in sec10.lower(),
          "§10.2 requires key + row in one transaction")

    # 6. TECH-MULTIPLAYER §6 tests 3/4 are named with what they need.
    check("Test 3" in sec10 and "ledger race" in sec10.lower(),
          "§10.5 covers TECH-MULTIPLAYER §6 test 3 (ledger race)")
    check("Test 4" in sec10 and "disconnect honesty" in sec10.lower(),
          "§10.5 covers TECH-MULTIPLAYER §6 test 4 (disconnect honesty)")
    check("3. **Ledger race test:**" in multi,
          "TECH-MULTIPLAYER §6 test 3 exists")
    check("4. **Disconnect honesty test:**" in multi,
          "TECH-MULTIPLAYER §6 test 4 exists")

    # 7. Migration note follows the Appendix A pattern: named migration,
    # numbered steps, no backfill, forward-only / no down-migration.
    check("003_ledger_idempotency_keys" in appb,
          "Appendix B names migration 003_ledger_idempotency_keys")
    check("Backfill: none, by rule" in appb,
          "Appendix B states backfill: none, by rule")
    check("no down-migration" in appb.lower(),
          "Appendix B states forward-only, no down-migration")
    steps = re.findall(r"^(\d+)\. \*\*", appb, re.M)
    check(steps == ["1", "2", "3", "4", "5", "6"],
          "Appendix B has six numbered migration steps",
          f"steps={steps}")

    # 8. Alternatives considered and rejected are recorded.
    for alt in ("separate idempotency table", "note` TEXT",
                "client/request layer only"):
        check(alt.lower() in sec10.lower(),
              f"§10.4 rejects the alternative: {alt}")

    # 9. OD-8 is the decision this section closes (runbook still records it).
    check("OD-8" in runbook and "transfer_key" in runbook,
          "runbook still records OD-8 as the open decision §10 closes")
    check("Open decision OD-8 is decided by this section" in sec10,
          "§10 states OD-8 is decided")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\nCHECKS: {len(CHECKS)}, FAILURES: {len(failed)}")
    for _, label, detail in failed:
        print(f"  FAILED: {label} {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
