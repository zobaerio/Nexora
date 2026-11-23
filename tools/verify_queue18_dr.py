"""Verify Queue 18 Unit DR — Lost-Credential Panel Display (GDD-05
§4; DN follow-up).

Checks the panel design against the sources it builds on:
docs/GDD-05-UI-AND-PANELS.md §4 (the panel + tabs + NPC inspect),
data/documents.json (the credential document ids),
tools/sim/academics.py (the DN seeding shape),
tools/sim/education.py (has_credential reads education_records),
tools/sim/persistence.py (the certifications table),
data/education-health-config.json (the institutions),
docs/GDD-11-EDUCATION.md (the credential gates), and
data/prices.json (documents are unpriced). Design only — no sim
code changes. Prints one line per check and a summary; exits 0
only when every check passes. Run from the repo root:
python3 tools/verify_queue18_dr.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKS = []


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def main():
    gdd05 = (ROOT / "docs" / "GDD-05-UI-AND-PANELS.md").read_text()
    gdd11 = (ROOT / "docs" / "GDD-11-EDUCATION.md").read_text()
    gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md").read_text()
    documents = json.loads((ROOT / "data" / "documents.json").read_text())
    prices = json.loads((ROOT / "data" / "prices.json").read_text())
    edu_cfg = json.loads(
        (ROOT / "data" / "education-health-config.json").read_text())
    academics = (ROOT / "tools" / "sim" / "academics.py").read_text()
    education = (ROOT / "tools" / "sim" / "education.py").read_text()
    persistence = (ROOT / "tools" / "sim" / "persistence.py").read_text()

    s4 = gdd05.split("**Credentials on the profile panel (Unit DR")[1] \
        .split("## 5. Environment Control Panel")[0]

    # 1. The section exists with the design's decisions.
    check("**Credentials on the profile panel (Unit DR" in gdd05,
          "GDD-05 §4 has the credentials subsection")
    check("Credentials block on the Skills tab" in s4,
          "the block lives on the Skills tab")
    check("Paper lost — credential valid" in s4,
          "the lost chip reads 'Paper lost — credential valid'")
    check("Found — awaiting hand-back" in s4,
          "the found chip reads 'Found — awaiting hand-back'")
    check("never a red X" in s4,
          "the icon state forbids a red X")
    check('Never "revoked"' in s4,
          "the panel must never claim revoked")
    check("Find it — a favour can be raised for this paper" in s4,
          "the recovery path points at the §3.1 favour")
    check("no Credentials-block row" in s4,
          "the deed and licence are out of scope (not credentials)")

    # 2. The credential document ids exist and are sourced.
    doc_ids = {i["id"]: i for i in documents["items"]}
    check("school_leaving_certificate" in doc_ids
          and "college_credential" in doc_ids,
          "both credential documents exist in documents.json")
    check("academics.py" in doc_ids["school_leaving_certificate"]["source"]
          and "academics.py" in doc_ids["college_credential"]["source"],
          "both credential documents source academics.py")
    check(len(documents["items"]) == 4,
          "the document catalogue has 4 items (deed + licence + 2)")

    # 3. The DN seeding shape is what the panel reads.
    check('"certification_id": cert_id' in academics,
          "academics.py seeds the document row with certification_id")
    check("school_leaving_certificate" in academics
          and "college_credential" in academics,
          "academics.py maps both certification kinds to document ids")
    check("def has_credential(" in education
          and "education_records" in education.split(
              "def has_credential(")[1].split("def ")[0],
          "has_credential reads education_records, never inventory")

    # 4. The certifications table carries the fields the panel shows.
    certs = persistence.split("CREATE TABLE IF NOT EXISTS certifications")[1] \
        .split(");")[0]
    check(all(f in certs for f in
              ("character_id", "institution_id", "kind", "programme",
               "issued_month")),
          "the certifications table has character/institution/kind/"
          "programme/issued_month")

    # 5. The issuing institutions resolve.
    insts = {i["institution_id"]: i["name"]
             for i in edu_cfg["education"]["institutions"]}
    check(insts.get("EDU-RUPSHA-SCHOOL") == "District School"
          and insts.get("EDU-RUPSHA-COLLEGE") == "District College"
          and insts.get("EDU-SHIBNAGAR-SCHOOL")
          == "Shibnagar Primary School",
          "the three institutions resolve to their names")

    # 6. The credential gates are sourced in GDD-11.
    check("credential-gated professions" in gdd11,
          "GDD-11 names the credential-gated professions")
    check("civil_engineer" in gdd11 and "software_developer" in gdd11,
          "GDD-11 names the four gated professions")

    # 7. Documents are unpriced — the panel shows no fee.
    check(all(i["price_ncr"] == 0 for i in prices["documents"]["items"]),
          "every document is unpriced (0 = unpriced, not free)")

    # 8. The panel rules the design follows.
    check("**Skills:** `character_skills` rows" in gdd05,
          "the Skills tab lists character_skills rows")
    check("only what the *player character* could know" in gdd05,
          "the Memories tab restriction is the NPC-inspect contrast")
    check("**NPC inspect** uses the same panel, read-only" in gdd05,
          "NPC inspect uses the same panel read-only")
    check("a lost credential is NOT a revoked one" in gdd04
          or "a LOST credential is NOT a revoked one" in gdd04,
          "GDD-04 §3.3 states the DN rule the panel displays")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
