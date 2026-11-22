"""Verify Queue 12 Unit BN — GDD-15 §20 character↔character loan source.

Checks the loan section against the sources it must resolve to:
GDD-04 §3/§3.1, GDD-15 §14, GDD-03 §4.3, data/schema.sql (reason
codes, no loans table), tools/sim/banking.py (bank loans only).
Prints one line per check and a summary; exits 0 only when every check
passes. Run from the repo root: python3 tools/verify_queue12_bn.py
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
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    gdd03 = (ROOT / "docs" / "GDD-03-ECONOMY-AND-PROFESSIONS.md").read_text()
    schema = (ROOT / "data" / "schema.sql").read_text()
    banking = (ROOT / "tools" / "sim" / "banking.py").read_text()
    conflicts = (ROOT / "tools" / "sim" / "conflicts.py").read_text()
    justice = (ROOT / "tools" / "sim" / "justice.py").read_text()

    # 1. §20 exists, headed Unit BN, Queue 12.
    m20 = re.search(r"## 20\. Character↔Character Loan Source "
                    r"\(AV gap G3 follow-up — the loan the favour creates\)",
                    gdd15)
    check(m20 is not None, "GDD-15 §20 exists, headed Unit BN, Queue 12")
    sec = gdd15[m20.start():] if m20 else ""
    sec = sec.split("*End of GDD-15 §20")[0]

    # 2. The loan is ledger rows only; the schema codes are the codes.
    check("'loan_disburse'" in schema and "'loan_repay'" in schema,
          "schema.sql reason codes include loan_disburse / loan_repay")
    check("reason_code = 'loan_disburse'" in sec,
          "disburse row carries loan_disburse")
    check("reason_code = 'loan_repay'" in sec,
          "repay row carries loan_repay (the §14.4 ruling)")
    check("CREATE TABLE loans" not in schema,
          "schema.sql has no loans table — the ledger rows are the record")
    check("no `loans` table" in sec,
          "§20 states the schema has no loans table")

    # 3. Traceability: both rows carry the favour instance key.
    check("side:favours:<giver_character_id>:<generated_at_game_minutes>"
          in sec,
          "transfer_key / event_ref is the §3.1 favour instance key")
    check("side:<type>:<giver_character_id>:<generated_at_game_minutes>"
          in gdd04,
          "GDD-04 §3.1 defines that instance-key format")

    # 4. Direction: player lends, NPC borrows; the reverse is not designed.
    check("player → NPC" in sec,
          "designed direction is player lends, NPC borrows")
    check("not designed here" in sec,
          "reverse direction (NPC lends to player) is not designed")

    # 5. Terms: no interest, no due date.
    check("Interest: none" in sec,
          "character loan is principal-only, no interest")
    check("12% annual" in gdd03,
          "GDD-03 §4.3 bank rate exists to contrast against")
    check("does not transfer to a loan between two people" in sec,
          "bank rate explicitly does not transfer")
    check("Due date: none" in sec,
          "no due date — favours have no deadline (GDD-04 §3.1)")

    # 6. One outstanding loan per pair, labelled as this unit's decision.
    check("One outstanding loan per pair" in sec,
          "one-open-loan-per-pair gate is defined")
    check("Decided here" in sec,
          "the gate is labelled as this unit's decision")

    # 7. Funds check at accept; rollback on failure.
    check("validates funds" in sec,
          "funds are checked at accept time")
    check("roll back as one transaction" in sec,
          "failed accept rolls back per §12.4")

    # 8. Missed repayment: no enforcement invented; only existing
    #    mechanisms are named, and they exist.
    check("No enforcement is invented" in sec,
          "§20 states no enforcement is invented")
    check("def disburse_loan" in banking
          and "SYS-BANK" in banking,
          "banking.py disburse_loan exists (SYS-BANK loans, for contrast)")
    check("def " in conflicts and "mediate" in conflicts.lower()
          or "mediation" in conflicts,
          "conflicts.py carries the mediation machinery §20 cites")
    check("court" in justice.lower(),
          "justice.py carries the court referral path §20 cites")
    check("never repaid stays outstanding forever" in sec,
          "unrepaid loan stays outstanding — no write-off invented")

    # 9. §14.5 and the §3.1 lend-money row now point at §20.
    check("GDD-15 §20" in gdd15.split("### 14.5")[1].split("### 14.6")[0]
          if "### 14.5" in gdd15 else False,
          "§14.5 points at §20 as the defined loan source")
    row = re.search(r"Favours — lend money.*?\n", gdd04)
    check(row is not None and "§20" in row.group(0),
          "§3.1 lend-money row points at §20")
    check(row is not None and "one open loan per pair" in row.group(0),
          "§3.1 row carries the one-open-loan gate")

    # 10. The section says what becomes true — and what stays untrue.
    check("owes_player` derive true" in sec,
          "§20 states the first favour loan makes owes_player derive true")
    check("No sim code is changed" in sec,
          "§20 is design only — no sim code changed")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed; "
          f"{len(failed)} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
