"""Verify Queue 11 Unit BK — runbook §12 payload store + operator tooling
(AW open decisions OD-6 + OD-7).

Checks the section against the sources it must resolve to:
docs/TECH-CHECKPOINT-RUNBOOK.md §2/§7/§8, TECH-PERSISTENT-WORLD §3/§4,
TECH-MULTIPLAYER §6/§7, data/schema.sql, tools/sim/__main__.py.
Prints one line per check and a summary; exits 0 only when every check
passes. Run from the repo root: python3 tools/verify_queue11_bk.py
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
    multi = (ROOT / "docs" / "TECH-MULTIPLAYER.md").read_text()
    schema = (ROOT / "data" / "schema.sql").read_text()
    main_py = (ROOT / "tools" / "sim" / "__main__.py").read_text()

    # 1. §12 exists, headed Unit BK, Queue 11, resolving OD-6 + OD-7.
    m12 = re.search(r"## 12\. Snapshot Payload Store & Operator Tooling "
                    r"\(AW open decisions OD-6 \+ OD-7 — resolved\)\n\n"
                    r"\*\*Unit BK · Queue 11",
                    runbook)
    check(m12 is not None,
          "runbook §12 exists, headed Unit BK, Queue 11 (OD-6 + OD-7)")

    # 2. §7 OD-6 and OD-7 rows say Resolved, pointing at §12.
    sec7 = runbook.split("\n## 7. ")[1].split("\n## 8. ")[0]
    check("**Resolved — §12.1 (Unit BK, Queue 11):**" in sec7,
          "§7 OD-6 row resolved, pointing at §12.1")
    check("**Resolved — §12.2 (Unit BK, Queue 11):**" in sec7,
          "§7 OD-7 row resolved, pointing at §12.2")

    sec12 = runbook.split("\n## 12. ")[1]

    # 3. The §11 citation correction: TECH-PERSISTENT-WORLD has no §11.
    check(re.search(r"^## 11\.", tpw, re.M) is None,
          "TECH-PERSISTENT-WORLD has no §11 (citation corrected)")
    check("No §11 exists in that document" in sec12,
          "§12 records the missing-§11 correction")
    check("payload-store note is **§3**" in sec12,
          "§12 points at TECH-PERSISTENT-WORLD §3 instead")

    # 4. TECH-PERSISTENT-WORLD §3 maps checkpoint_db to payload_ref.
    sec3 = tpw.split("\n## 3. ")[1].split("\n## 4. ")[0]
    check("save_slots.payload_ref" in sec3
          and "file path / blob key" in sec3,
          "§3 maps checkpoint_db to payload_ref (file path / blob key)")

    # 5. schema.sql payload_ref comment allows either value.
    check("payload_ref     TEXT,            -- local file path / blob key"
          in schema, "schema.sql payload_ref allows file path / blob key")

    # 6. Payload path format uses save_slot_id, manifest beside it.
    check("<snapshot_dir>/<world_id>/<save_slot_id>.payload.json" in sec12,
          "payload path format stated")
    check("<save_slot_id>.manifest.json" in sec12,
          "manifest file lives beside the payload")
    check("not the human checkpoint name" in sec12,
          "file name uses save_slot_id, not the label")

    # 7. Rationale: v1 server on the owner's PC/LAN; no blob store exists.
    check("owner's PC/LAN" in sec12,
          "§12.1 rationale cites the PC/LAN v1 server")
    check("no blob store exists" in sec12,
          "§12.1 states no blob store exists")
    check("No netcode" in multi or "no netcode is specified" in multi,
          "TECH-MULTIPLAYER §7 specifies no netcode")
    check("no hosting provider" in multi.lower(),
          "TECH-MULTIPLAYER §7 chooses no hosting provider")

    # 8. The CLI is local on the server host, mirroring the sim flags.
    check("`nexora-server`" in sec12, "operator CLI is named nexora-server")
    check("local tool, not a network API" in sec12,
          "CLI is local, not a network API")
    for flag in ("--checkpoint", "--checkpoints", "--restore-checkpoint",
                 "--duplicate-to", "--from-checkpoint"):
        check(flag in main_py, f"sim CLI has {flag}")

    # 9. All five commands are in the §12.2 table.
    for cmd in ("nexora-server checkpoints", "nexora-server checkpoint",
                "nexora-server restore", "nexora-server duplicate",
                "nexora-server verify"):
        check(cmd in sec12, f"§12.2 defines {cmd}")

    # 10. On-demand checkpoints are day-boundary only.
    check("at a day boundary only" in sec12,
          "on-demand checkpoint is day-boundary only")

    # 11. Restore takes a safety snapshot first (pre-restore-<name>).
    check("pre-restore-<name>" in sec12,
          "restore takes a pre-restore safety snapshot first")
    check("so the restore is reversible" in sec12,
          "safety snapshot makes the restore reversible")

    # 12. Duplicate never goes into the live world's slot.
    check("Never into the live world's slot" in sec12,
          "duplicate never targets the live world's slot")
    check("fresh registry entry" in sec12,
          "duplicate gets a fresh registry entry")

    # 13. verify is labelled as added here (no sim equivalent).
    check("no standalone verify flag" in sec12
          and "added here" in sec12,
          "verify command labelled as added here")

    # 14. The CLI serves the §8 pre-flight checklist.
    check("§8 pre-flight checklist" in sec12 or "pre-flight" in sec12,
          "§12.2 ties the CLI to the §8 pre-flight checklist")

    # 15. All eight OD rows in §7 now say Resolved.
    od_rows = re.findall(r"\| OD-\d \|", sec7)
    resolved = re.findall(r"\*\*Resolved —", sec7)
    check(len(od_rows) == 8 and len(resolved) == 8,
          "all 8 OD rows in §7 say Resolved",
          f"rows={len(od_rows)} resolved={len(resolved)}")

    # 16. OD-6/OD-7 resolution statement present.
    check("**OD-6 and OD-7 are resolved by this section**" in sec12,
          "§12 states OD-6 and OD-7 resolved")

    # 17. No schema.sql change by this unit (design only).
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
