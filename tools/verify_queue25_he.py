"""Verify Queue 25 Unit HE — Settlement-Timing Trajectory Decision
(GC follow-up).

Checks the decision against its sources: docs/ECONOMY-SIM-
REPORT-V7.md §10 (the decision, the four reasons, the
documented limits), docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2
(the HE update), and the V7 report §§6 + 9 (the decision
marked DONE / the pointer resolved) — and that the tool is
UNCHANGED, because a "stay" decision means no sim change: the
default-run md5 is still the HD baseline and no tool or test
file changed.
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue25_he.py
"""
import hashlib
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
    report = (ROOT / "docs" / "ECONOMY-SIM-REPORT-V7.md").read_text()
    gdd03 = (ROOT / "docs" / "GDD-03-ECONOMY-AND-PROFESSIONS.md").read_text()

    # 1. The decision is recorded, in §10.
    check("## 10. Addendum — Settlement-Timing Trajectory Decision"
          " (Unit HE, Queue 25)" in report,
          "report §10: the addendum exists")
    check("Decision: the tool STAYS a stylised\ndaily model" in report,
          "report §10: the decision is STAY a stylised daily model")
    check("It does not model monthly settlement timing" in report,
          "report §10: monthly settlement timing is NOT modelled")

    # 2. The four reasons are recorded.
    check("The storm-position signal is the tool's reason for"
          in report,
          "report §10: reason 1 — the storm-position signal")
    check("early, mid, late and measured would be identical"
          in report,
          "report §10: reason 1 — monthly timing destroys the"
          " signal")
    report_flat = " ".join(report.split())
    check("The settlement's actual within-month path is already"
          " measured directly" in report_flat,
          "report §10: reason 2 — the settlement path is already"
          " measured")
    check("The daily model is the bridge check's model" in report,
          "report §10: reason 3 — the bridge check's model")
    check("Determinism" in report,
          "report §10: reason 4 — determinism")

    # 3. The documented limits are recorded, with the GC figures.
    check("The tool's trajectory has no settlement counterpart"
          in report,
          "report §10: limit — no settlement counterpart")
    check("+89 / 0 in absolute NCr" in report,
          "report §10: limit — the settlement's measured minimum")
    check("The taxi-fare drain" in report,
          "report §10: limit — the taxi-fare drain")
    check("The randomised start" in report,
          "report §10: limit — the randomised start")
    check("5,385" in report and "4,496" in report,
          "report §10: the measured seeds are quoted")
    check("1,377 − 504 = 873" in report,
          "report §10: the low-seed bridge margin is worked")
    check("The monthly-settlement alternative stays open as a"
          " documented alternative, not implemented"
          in report_flat,
          "report §10: the monthly alternative stays open, not"
          " implemented")
    check("No tuning call" in report,
          "report §10: no tuning call")

    # 4. The decision is marked DONE where §6 posed it, and the
    # §9 pointer is resolved.
    check("Units HA + HE DONE\n2026-11-24" in report,
          "report §6: the HE decision is marked DONE")
    check("(Unit HE DONE\n2026-11-24 — see §10: the tool stays a"
          " stylised daily model.)" in report,
          "report §9: the HE pointer is resolved")

    # 5. GDD-03 §2 records the HE update.
    check("Unit HE · Queue 25" in gdd03,
          "GDD-03 §2: the HE update is recorded")
    check("DECISION — the tool STAYS a stylised daily model"
          in gdd03,
          "GDD-03 §2: the decision is quoted")
    check("Priya Khan seed 5,385" in gdd03,
          "GDD-03 §2: the taxi-fare drain figures are quoted")

    # 6. No sim change: the tool is byte-identical — the default
    # run still hashes to the HD baseline, and no tool or test
    # file changed on this branch since the HD commit.
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py")],
        capture_output=True, cwd=ROOT)
    check(out.returncode == 0, "tool: default run exits 0")
    md5 = hashlib.md5(out.stdout).hexdigest()
    check(md5 == "5431558ffa3d023c436366c26535f932",
          "tool: default-run md5 is STILL the HD baseline", md5)
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    check(names == {"docs/ECONOMY-SIM-REPORT-V7.md",
                    "docs/GDD-03-ECONOMY-AND-PROFESSIONS.md",
                    "tools/verify_queue25_he.py"},
          "scope: only the two docs + this script changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
