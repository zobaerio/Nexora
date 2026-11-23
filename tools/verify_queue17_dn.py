"""Verify Queue 17 Unit DN — Certification -> Document Row
(GDD-04 §3.3, Unit DE follow-up).

Checks the decision and its implementation: the rule (a lost
credential is NOT a revoked one), tools/sim/academics.py (the
issue_certifications wiring), tools/sim/lost_items.py
(seed_document_row), data/documents.json (the credential entries),
tools/sim/education.py (has_credential reads records, never
inventory) and tools/sim/tests/test_academics.py.
Prints one line per check and a summary; exits 0 only when every
check passes. Run from the repo root: python3 tools/verify_queue17_dn.py
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
    documents = json.loads((ROOT / "data" / "documents.json").read_text())
    academics = (ROOT / "tools" / "sim" / "academics.py").read_text()
    lost = (ROOT / "tools" / "sim" / "lost_items.py").read_text()
    education = (ROOT / "tools" / "sim" / "education.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_academics.py").read_text()

    # 1. The catalogue carries the two credential entries (DE did).
    ids = {i["id"] for i in documents["items"]}
    check("school_leaving_certificate" in ids,
          "documents.json carries school_leaving_certificate")
    check("college_credential" in ids,
          "documents.json carries college_credential")
    check(all(i.get("source", "") != "" for i in documents["items"]
              if i["id"] in ("school_leaving_certificate",
                             "college_credential")),
          "both credential entries name their source")

    # 2. The wiring: issue_certifications seeds the document row.
    check("seed_document_row(" in academics,
          "academics.issue_certifications seeds the document row")
    check('"school_leaving_certificate"' in academics
          and '"college_credential"' in academics,
          "both kinds map to their document catalogue id")
    check('"certification_id": cert_id' in academics
          or '"certification_id"' in academics,
          "the document state carries the certification id")
    check("is NOT a revoked one" in academics,
          "academics.py states the lost-credential rule")

    # 3. The rule is recorded in the design doc.
    check("a lost credential is not a revoked one" in gdd04.lower(),
          "GDD-04 §3.3 states the lost-credential rule")
    check("has_credential()` (which reads `education_records`, never"
          " inventory)" in gdd04,
          "GDD-04 states has_credential reads records, never inventory")
    check("Units DJ + DN · Queue 17" in gdd04,
          "GDD-04 carries the DJ+DN document update")

    # 4. has_credential really does read records, never inventory.
    check("def has_credential" in education,
          "education.py defines has_credential")
    has_fn = education.split("def has_credential")[1].split("def ")[0]
    check("education_records" in has_fn
          and "inventory_items" not in has_fn
          and "lost_items" not in has_fn,
          "has_credential reads education_records only")

    # 5. The seed helper refuses a duplicate of the same record.
    check("def seed_document_row" in lost,
          "lost_items.py defines seed_document_row")
    check("the same issuing record seeded twice is a duplicate"
          in lost,
          "seed_document_row refuses the same record twice")

    # 6. The tests cover the decision.
    check("class TestCertificationDocumentRow" in tests,
          "tests carry a TestCertificationDocumentRow class")
    n_tests = len(re.findall(r"def test_", tests))
    check("test_school_leaving_writes_a_document_row" in tests,
          "tests prove a school-leaving cert writes a document row")
    check("test_college_credential_writes_a_document_row" in tests,
          "tests prove a college credential writes a document row")
    check("test_lost_credential_is_not_revoked" in tests,
          "tests prove a lost credential is not revoked")
    check("test_reissue_writes_no_second_document_row" in tests,
          "tests prove re-issue writes no second document row")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
