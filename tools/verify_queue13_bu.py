"""Verify Queue 13 Unit BU — GDD-15 §22 ledger reason-code alignment +
TECH-PERSISTENT-WORLD §11 ingest note (the Phase 9 alignment §14.4
called for).

Checks the mapping against the sources it must resolve to: the sim's
actual reason strings (re-derived here from tools/sim/*.py, the same
inventory method §22.1 states), data/schema.sql reason CHECK, GDD-15
§14.4, docs/TECH-PERSISTENT-WORLD.md.
Prints one line per check and a summary; exits 0 only when every check
passes. Run from the repo root: python3 tools/verify_queue13_bu.py
"""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKS = []

# The §22.2 verdicts, as this script expects them in the doc table.
EXPECTED = {
    "loan_disbursement": "loan_disburse",
    "loan_repayment": "loan_repay",
    "mortgage_disbursement": "loan_disburse",
    "commercial_rent": "rent",
    "business_sale": "sale",
    "sales_tax": "tax",
    "tariff": "tax",
    "land_purchase": "purchase",
    "vehicle_purchase": "purchase",
    "debt_repayment": "transfer",
    "court_refund": "transfer",
    "restitution": "transfer",
    "retail_takings": "business_revenue",
    "production_cost": "business_expense",
    "shipping": "business_expense",
    "taxi_fare": "purchase",
    "transit_subsidy": "transfer",
    "medical_procurement": "purchase",
    "municipal_service": "purchase",
    "policy_spend": "purchase",
    "disaster_repair": "purchase",
    "construction_funding": "transfer",
    "office_allowance": "wage",
    "welfare": "transfer",
    "disaster_relief": "transfer",
    "treasury_allocation": "transfer",
    "party_dues": "transfer",
    "party_funding": "transfer",
    "campaign": "purchase",
    "cooperation_grant": "transfer",
    "genesis_grant": "seed",
    "bank_capital": "transfer",
    "bank_deposit": "transfer",
    "bank_withdrawal": "transfer",
    "interest": "transfer",
    "dividend": "transfer",
    "investment": "purchase",
    "business_capital": "transfer",
}


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def sim_reasons():
    """Re-derive the sim's distinct reason strings the way §22.1
    states: every constant reason reaching store.transfer, including
    via the _pay/_pay_purchase forwarders."""
    reasons = set()
    for p in sorted((ROOT / "tools" / "sim").glob("*.py")):
        tree = ast.parse(p.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "attr", None)
            if name == "transfer":
                if len(node.args) >= 4 \
                        and isinstance(node.args[3], ast.Constant):
                    reasons.add(node.args[3].value)
                for kw in node.keywords:
                    if kw.arg == "reason" \
                            and isinstance(kw.value, ast.Constant):
                        reasons.add(kw.value.value)
            elif name in ("_pay", "_pay_purchase"):
                for a in node.args:
                    if isinstance(a, ast.Constant) \
                            and isinstance(a.value, str) \
                            and a.value not in ("SYS-MARKET", "SYS-CITY"):
                        reasons.add(a.value)
                        break
    return reasons


def main():
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    tech = (ROOT / "docs" / "TECH-PERSISTENT-WORLD.md").read_text()
    schema = (ROOT / "data" / "schema.sql").read_text()

    # 1. §22 exists, headed Unit BU, Queue 13.
    m22 = re.search(r"## 22\. Ledger Reason-Code Alignment \(Phase 9\)",
                    gdd15)
    check(m22 is not None, "GDD-15 §22 exists, headed Unit BU, Queue 13")
    sec = gdd15[m22.start():] if m22 else ""
    sec = sec.split("*End of GDD-15 §22")[0]

    # 2. The inventory is re-derived from the sim and matches §22.1.
    reasons = sim_reasons()
    schema_codes = set(re.search(
        r"reason_code\s+TEXT NOT NULL CHECK \(reason_code IN\s+\((.*?)\)\)",
        schema, re.S).group(1).replace("'", "").replace("\n", "")
        .replace(" ", "").split(","))
    passing = reasons & schema_codes
    rejected = reasons - schema_codes
    check(len(reasons) == 47, "sim writes 47 distinct reason strings",
          f"got={len(reasons)}")
    check(len(passing) == 9, "9 sim strings pass the schema CHECK",
          f"got={sorted(passing)}")
    check(len(rejected) == 38, "38 sim strings are rejected by the CHECK",
          f"got={len(rejected)}")
    check("**38**" in sec and '"~39" was an estimate' in sec,
          "§22.1 corrects §14.4's ~39 estimate to 38")
    check(set(EXPECTED) == rejected,
          "the 38 mapped strings are exactly the rejected set",
          f"missing={sorted(rejected - set(EXPECTED))} "
          f"extra={sorted(set(EXPECTED) - rejected)}")

    # 3. Every mapped string appears in the §22.2 table with its code.
    rows = re.findall(r"\| `([a-z_]+)` \| `([a-z_]+)` \|", sec)
    table = dict(rows)
    check(len(rows) == 38, "§22.2 table has 38 rows", f"got={len(rows)}")
    bad = [(s, EXPECTED[s], table.get(s)) for s in EXPECTED
           if table.get(s) != EXPECTED[s]]
    check(not bad, "every mapped string lands on its §22.2 code",
          f"bad={bad[:4]}")
    check(all(c in schema_codes for c in EXPECTED.values()),
          "every mapped code is an existing schema code (no new code)")

    # 4. The 9 passing strings and 6 unused codes are recorded.
    check("`business_expense`, `business_revenue`, `inheritance`, "
          "`pension`, `purchase`, `rent`, `seed`, `tax`, `wage`" in sec,
          "§22.1 lists the 9 passing strings")
    check("`sale`, `mission_reward`, `loan_disburse`, `loan_repay`, "
          "`transfer`, `fine`" in sec,
          "§22.1 lists the 6 schema codes the sim never writes")

    # 5. The ingest rule: translate at ingest, fidelity prefix,
    #    fail-closed, list unchanged, sim unchanged, BD untouched.
    for frag, label in (
            ("Translate at ingest, never rewrite sim history",
             "rule 1: translate at ingest, never rewrite sim history"),
            ("[sim:<original>]", "rule 2: [sim:<original>] note prefix"),
            ("Fail closed", "rule 3: fail-closed on unmapped strings"),
            ("The code list does not change",
             "rule 4: the 15-code list does not change"),
            ("The BD migration is untouched",
             "rule 5: the BD migration is untouched"),
    ):
        check(frag in sec, f"§22.3 states {label}")

    # 6. Consequences: tariff/sales_tax queries move to note/key filters.
    check("must move to note-prefix" in sec
          or "note-prefix / `transfer_key`-prefix filters" in sec,
          "§22.3 states the tariff/sales_tax query consequence")

    # 7. What it does not do: no sim/schema change; GDD-01 §8 drift
    #    recorded, correction deferred to a later unit.
    check("does not change the sim, the schema" in sec,
          "§22.4 states no sim/schema change")
    check("GDD-01 §8" in sec and "`loan` is not a schema code" in sec,
          "§22.4 records the GDD-01 §8 'loan' doc drift")
    check("recorded for Queue 14" in sec,
          "§22.4 defers the GDD-01 correction to Queue 14")

    # 8. TECH-PERSISTENT-WORLD §11 exists and states the rule.
    m11 = re.search(r"## 11\. Ledger Reason-Code Alignment at Ingest "
                    r"\(Unit BU · Queue 13\)", tech)
    check(m11 is not None, "TECH-PERSISTENT-WORLD §11 exists, Unit BU")
    s11 = tech[m11.start():] if m11 else ""
    s11 = s11.split("*End of TECH-PERSISTENT-WORLD §11")[0]
    check("fail-closed" in s11, "§11 states fail-closed ingest")
    check("The schema `CHECK` list stays at its 15 codes" in s11,
          "§11 states the CHECK list stays at 15 codes")
    check("The §10/Appendix B migration is untouched" in s11,
          "§11 states the BD migration is untouched")
    check("Session 10 digest is unaffected" in s11,
          "§11 states the digest is unaffected by translation")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed; "
          f"{len(failed)} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
