"""Verify Queue 10 Unit BB — GDD-15 §14 debt-flag derivation (AV gap G3).

Checks the derivation section against the sources it must resolve to:
GDD-01 §6, GDD-15 §12, data/dialogue-lines.json, data/schema.sql, and the
sim's loan machinery (tools/sim/banking.py). Prints one line per check
and a summary; exits 0 only when every check passes.
Run from the repo root: python3 tools/verify_queue10_bb.py
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


def load_json(name):
    return json.loads((ROOT / "data" / name).read_text())


def all_nodes(dlg):
    out = []

    def walk(o):
        if isinstance(o, dict):
            if "node_id" in o:
                out.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(dlg)
    return out


def main():
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    schema = (ROOT / "data" / "schema.sql").read_text()
    dlg = load_json("dialogue-lines.json")
    banking = (ROOT / "tools" / "sim" / "banking.py").read_text()

    # 1. The schema reason codes the rule uses exist in the CHECK list.
    m = re.search(r"CREATE TABLE economy_ledger \(.*?reason_code.*?CHECK"
                  r" \(reason_code IN\s*\((.*?)\)\)", schema, re.S)
    check(m is not None, "economy_ledger reason_code CHECK found")
    codes = set(re.findall(r"'([a-z_]+)'", m.group(1))) if m else set()
    check({"loan_disburse", "loan_repay"} <= codes,
          "schema reason codes include loan_disburse and loan_repay",
          f"n_codes={len(codes)}")

    # 2. §14 exists and states the derivation rule with the schema codes.
    sec14 = gdd15.split("## 14. Debt-Flag Derivation")[1].split(
        "## 15. Favour Topic Note")[0]
    check("owes_player(X)" in sec14 and "player_owes(X)" in sec14,
          "§14.2 states both flag derivation formulas")
    check("loan_disburse" in sec14 and "loan_repay" in sec14,
          "§14.2 uses the schema reason codes")
    check("SYS-BANK" in sec14 and "never set" in sec14.lower(),
          "§14.3 excludes bank loans from the flags")

    # 3. The debt tree exists and conditions on the two flags.
    nodes = {n["node_id"]: n for n in all_nodes(dlg)}
    debt_nodes = ["dlg_topic_debt", "dlg_debt_npc_owes", "dlg_debt_repay_now",
                  "dlg_debt_npc_refuses", "dlg_debt_wait",
                  "dlg_debt_player_owes", "dlg_debt_player_pays",
                  "dlg_debt_player_wait"]
    for nid in debt_nodes:
        check(nid in nodes, f"debt tree node {nid} exists")
    conds = json.dumps([nodes[n].get("condition") for n in debt_nodes
                        if n in nodes])
    check("owes_player" in conds and "player_owes" in conds,
          "debt tree conditions on owes_player and player_owes")

    # 4. The sim's loans are bank loans only (SYS-BANK endpoint).
    check("def disburse_loan" in banking,
          "sim banking.py defines disburse_loan")
    check('"SYS-BANK"' in banking and "loan:" in banking,
          "sim loans are SYS-BANK loans with loan: transfer keys")

    # 5. schema.sql has no loans table — the ledger rows are the record.
    check("CREATE TABLE loans" not in schema,
          "schema.sql has no loans table (ledger is the loan record)")

    # 6. The §14.4 drift claim is true: the sim writes loan strings the
    # schema CHECK would reject, and the dialogue settlement reason
    # 'repayment' is not a schema code.
    check("loan_disbursement" in banking and "loan_repayment" in banking,
          "sim banking.py writes loan_disbursement / loan_repayment")
    check("'repayment'" not in codes,
          "settlement reason 'repayment' is not a schema reason code")
    raw = json.dumps(dlg)
    check('"reason": "repayment"' in raw,
          "dialogue ledger_settlement uses reason repayment")
    check("loan_disbursement" in sec14 and "loan_repayment" in sec14,
          "§14.4 records the sim's differing loan strings")

    # 7. The decision (derive at conversation time) is stated, with the
    # rejected alternative.
    check("derive at conversation time" in sec14.lower(),
          "§14.6 decides derive-at-conversation-time")
    check("economy-maintained" in sec14 and "rejected" in sec14.lower(),
          "§14.6 records the rejected economy-maintained alternative")

    # 8. §12.8 G3 is marked resolved by this unit.
    check("Resolved by Queue 10, Unit BB" in gdd15,
          "§12.8 G3 marked resolved by Unit BB")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\nCHECKS: {len(CHECKS)}, FAILURES: {len(failed)}")
    for _, label, detail in failed:
        print(f"  FAILED: {label} {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
