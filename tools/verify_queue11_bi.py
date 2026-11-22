"""Verify Queue 11 Unit BI — runbook §10 wording + audit destination
(AW open decisions OD-1 + OD-5).

Checks the section against the sources it must resolve to:
docs/TECH-CHECKPOINT-RUNBOOK.md §3.4/§4/§7, TECH-PERSISTENT-WORLD
Appendix A §A.5 step 5, tools/sim/integrity.py, tools/sim/persistence.py,
data/schema.sql (unchanged).
Prints one line per check and a summary; exits 0 only when every check
passes. Run from the repo root: python3 tools/verify_queue11_bi.py
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKS = []


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def main():
    runbook = (ROOT / "docs" / "TECH-CHECKPOINT-RUNBOOK.md").read_text()
    tpw = (ROOT / "docs" / "TECH-PERSISTENT-WORLD.md").read_text()
    integrity = (ROOT / "tools" / "sim" / "integrity.py").read_text()
    persist = (ROOT / "tools" / "sim" / "persistence.py").read_text()
    schema = (ROOT / "data" / "schema.sql").read_text()

    # 1. §10 exists, headed Unit BI, Queue 11, resolving OD-1 + OD-5.
    m10 = re.search(r"## 10\. Operator Wording & Audit Destination "
                    r"\(AW open decisions OD-1 \+ OD-5 — resolved\)\n\n"
                    r"\*\*Unit BI · Queue 11",
                    runbook)
    check(m10 is not None,
          "runbook §10 exists, headed Unit BI, Queue 11 (OD-1 + OD-5)")

    # 2. §7 OD-1 and OD-5 rows say Resolved, pointing at §10.
    sec7 = runbook.split("\n## 7. ")[1].split("\n## 8. ")[0]
    check("**Resolved — §10 (Unit BI, Queue 11):**" in sec7,
          "§7 OD-1 row resolved, pointing at §10")
    check("**Resolved — §10.3 (Unit BI, Queue 11):**" in sec7,
          "§7 OD-5 row resolved, pointing at §10.3")

    sec10 = runbook.split("\n## 10. ")[1].split("\n## 11. ")[0]

    # 3. The three messages exist with their exact headers.
    for header in ("REFUSED: world <world>", "FALLBACK: starting world",
                   "GENESIS: no named checkpoint"):
        check(header in sec10, f"§10.2 template present: {header[:24]}…")

    # 4. Every message names world, snapshot, and day/game_minutes.
    for name in ("<world>", "<snapshot>", "<day>", "<game_minutes>"):
        check(name in sec10, f"templates use placeholder {name}")

    # 5. Each template names the failed gate and the next action.
    check("<gate>" in sec10 and "Next: confirm fallback" in sec10,
          "refusal names the gate and the next action")

    # 6. Genesis confirmation requires typing the world name.
    check("Type the world name '<world>' to confirm:" in sec10,
          "genesis confirmation requires typing the world name")

    # 7. Digest split rule: full in log, 12-hex on console.
    check("full 64-hex digests" in sec10 and "first 12 hex characters"
          in sec10, "digest split rule stated (full in log, 12-hex console)")

    # 8. Language rule: English, following the document's language.
    check("Language: English" in sec10,
          "wording language is English (§10.1)")

    # 9. The wording never invents a cause (§10.1 rule 2).
    check("never invents a cause" in sec10,
          "§10.1 forbids inventing a cause")

    # 10. The §0 pointer error is corrected in §10.
    check("Correction to §0" in sec10
          and "that pointer is wrong" in sec10,
          "§10 records the §0 pointer correction")

    # 11. Audit destination is audits, scope snapshot_verification.
    check("`audits` table, scope `snapshot_verification`" in sec10,
          "audit destination is audits, scope snapshot_verification")

    # 12. The row shape matches the sim audits table columns.
    audit_cols = re.search(
        r"CREATE TABLE IF NOT EXISTS audits \((.*?)\);", persist, re.S
    ).group(1)
    for col in ("audit_id", "scope", "month_index", "discrepancies",
                "discrepancy_count", "result", "integrity_index",
                "auditor_character_id", "game_minutes"):
        check(col in audit_cols, f"sim audits table has {col}")
        check(f"`{col}`" in sec10 or col in sec10,
              f"§10.3 row shape names {col}")

    # 13. Result values: mismatch and version_refusal.
    check("'mismatch'" in sec10 and "'version_refusal'" in sec10,
          "result values mismatch / version_refusal defined")

    # 14. integrity_index and auditor are NULL, with reasons.
    check("`integrity_index` | `NULL`" in sec10,
          "integrity_index is NULL for snapshot checks")
    check("`auditor_character_id` | `NULL`" in sec10,
          "auditor_character_id is NULL (server process audits)")

    # 15. month_index rule matches audit_government().
    check("game_minutes // 43200" in integrity,
          "audit_government() uses month_index game_minutes // 43200")
    check("`game_minutes // 43200`" in sec10,
          "§10.3 uses the same month_index rule")

    # 16. audits does NOT exist in data/schema.sql (checked, not assumed).
    check("CREATE TABLE audits" not in schema
          and "CREATE TABLE IF NOT EXISTS audits" not in schema,
          "audits table absent from data/schema.sql")
    check("does **not** exist in `data/schema.sql` today" in sec10,
          "§10.3 states the table is absent from schema.sql")
    check("19 `CREATE TABLE` statements" in sec10,
          "§10.3 cites the checked count (19 CREATE TABLEs)")

    # 17. integrity_reports is rejected with its reason.
    check("Rejected alternative — `integrity_reports`" in sec10,
          "integrity_reports rejection recorded")
    check("not an allegation against anyone" in sec10,
          "integrity_reports rejection reason stated")

    # 18. A new table is rejected with its reason.
    check("Rejected alternative — a new server table" in sec10,
          "new-table rejection recorded")

    # 19. Appendix A §A.5 step 5 is the source of "write an audit row".
    check("write an audit row" in tpw.split("\n## A.5 ")[1].split(
        "\n## A.6 ")[0], "Appendix A §A.5 step 5 sources 'write an audit row'")

    # 20. The metadata outcome record is still written alongside.
    check("snapshot_metadata.last_verified_at" in sec10
          and "verification_status" in sec10,
          "§10.3 keeps the metadata outcome record alongside the audit row")

    # 21. OD-1 + OD-5 resolution statement present.
    check("**OD-1 and OD-5 are resolved by this section**" in sec10,
          "§10 states OD-1 and OD-5 resolved")

    # 22. No schema.sql change by this unit (design only).
    diff = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "--name-only"],
        capture_output=True, text=True).stdout.splitlines()
    check("data/schema.sql" not in diff,
          "data/schema.sql unchanged (design only)",
          f"changed={diff}")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed, "
          f"{len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
