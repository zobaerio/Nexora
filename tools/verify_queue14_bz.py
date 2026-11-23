"""Verify Queue 14 Unit BZ — GDD-01 §8 reason-vocabulary correction
(the BU §22.4 doc drift: GDD-01 §8 listed "loan" as a reason code, but
the schema CHECK has loan_disburse / loan_repay, not "loan").

Checks the corrected list against the schema CHECK's 15 codes, verbatim,
and that no "loan" shorthand survives in §8. Run from the repo root:
python3 tools/verify_queue14_bz.py
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
    gdd01 = (ROOT / "docs" / "GDD-01-LIFE-AND-DATA-MODEL.md").read_text()
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    schema = (ROOT / "data" / "schema.sql").read_text()

    # 1. The schema CHECK's 15 codes, extracted from the file itself.
    m = re.search(r"reason_code\s+TEXT NOT NULL CHECK \(reason_code IN\s*\(([^)]*)\)",
                  schema, re.S)
    check(m is not None, "schema.sql economy_ledger reason_code CHECK found")
    codes = sorted(c.strip().strip("'\"") for c in m.group(1).split(",")
                   if c.strip()) if m else []
    check(len(codes) == 15, "schema CHECK holds exactly 15 codes",
          f"got {len(codes)}: {codes}")
    check("loan" not in codes and "loan_disburse" in codes
          and "loan_repay" in codes,
          "schema CHECK has loan_disburse/loan_repay, no bare loan")

    # 2. GDD-01 §8 lists the same 15 codes, verbatim.
    sec8 = gdd01.split("## 8. Money: the Ledger Is the Truth")[1]
    sec8 = sec8.split("## 9.")[0]
    listed = re.search(r"reason_code \(([^)]*)\)", sec8)
    check(listed is not None, "GDD-01 §8 reason_code list found")
    doc_codes = sorted(c.strip() for c in listed.group(1).split(",")
                       if c.strip()) if listed else []
    check(doc_codes == codes,
          "GDD-01 §8 lists exactly the schema CHECK's 15 codes",
          f"doc={doc_codes}")
    check("loan, " not in sec8 and "mission_reward, loan," not in sec8,
          "GDD-01 §8 carries no bare loan shorthand any more")

    # 3. The correction is labelled, and the CHECK stays authoritative.
    check("Unit BZ" in sec8, "§8 correction labelled Unit BZ, Queue 14")
    check("the `CHECK` in `data/schema.sql` is authoritative" in sec8,
          "§8 states the CHECK is authoritative, the list illustrative")

    # 4. The BU §22.4 pointer is honoured: GDD-15 names the follow-up.
    check("correcting the doc's shorthand is a later unit's job" in gdd15
          or "Queue 14" in gdd15.split("### 22.4")[1].split("*End of")[0]
          if "### 22.4" in gdd15 else False,
          "GDD-15 §22.4 recorded the correction as a later unit's job")
    check("loan" in gdd15.split("### 22.4")[1].split("*End of")[0]
          if "### 22.4" in gdd15 else False,
          "GDD-15 §22.4 names the loan shorthand drift")

    # 5. No doc repeats the drift except §22.4's labelled historical quote.
    hits = []
    for doc in ("GDD-01-LIFE-AND-DATA-MODEL.md", "GDD-04-MISSIONS-AND-PROGRESSION.md",
                "GDD-15-DIALOGUE.md"):
        text = (ROOT / "docs" / doc).read_text()
        hits += [(doc, m.start()) for m in
                 re.finditer(r"mission_reward, loan,", text)]
    check(len(hits) == 1 and hits[0][0] == "GDD-15-DIALOGUE.md"
          and "Correction applied, Unit BZ" in gdd15,
          "the drift survives only as §22.4's labelled historical quote",
          f"hits={hits}")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
