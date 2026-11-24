"""Verify Queue 26 Unit ID — Monthly-Timing View Beside the
Daily Model (HE follow-up).

This unit is deliberately NOT implemented: HE left the
monthly-settlement alternative open only when a use is named,
and no use is named in this run — so the view stays open and
unimplemented. This script verifies the honest record instead
of a build: the tool is byte-identical (no monthly-timing view
added, the md5 still the IC baseline), WORK-QUEUE.md ticks the
unit as "stays open and unimplemented — no use named", and the
V7 report §10 + GDD-03 §2 record the check.
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue26_id.py
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CHECKS = []


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def main():
    from tools import economy_sim as econ
    sim_src = (ROOT / "tools" / "economy_sim.py").read_text()
    queue = (ROOT / "WORK-QUEUE.md").read_text()
    report = (ROOT / "docs" / "ECONOMY-SIM-REPORT-V7.md").read_text()
    gdd03 = (ROOT / "docs" / "GDD-03-ECONOMY-AND-PROFESSIONS.md").read_text()

    # 1. No monthly-timing view was built: no such symbol in
    # the tool, and the default run is byte-identical to the IC
    # baseline.
    check("monthly_timing" not in sim_src
          and "month_end_trajectory" not in sim_src,
          "tool: no monthly-timing view exists in economy_sim.py")
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py")],
        capture_output=True, cwd=ROOT)
    check(out.returncode == 0, "tool: default run exits 0")
    md5 = hashlib.md5(out.stdout).hexdigest()
    check(md5 == "d198a2fe0970e11aaa105bcc4bfb19f9",
          "tool: default-run md5 is still the IC baseline (no"
          " ID change)", md5)
    check("second earner at another tier" in out.stdout.decode(),
          "tool: the IC sections are still printed")

    # 2. WORK-QUEUE.md ticks ID as open and unimplemented — no
    # use named — and does not claim a build.
    m = re.search(r"- \[(.)\] \*\*Unit ID\*\*.*?(?=\n- \[|\Z)",
                  queue, re.S)
    check(m is not None, "queue: Unit ID is present")
    if m:
        text = m.group(0)
        check(m.group(1) == "x",
              "queue: Unit ID is ticked")
        check("stays open and unimplemented" in text,
              "queue: Unit ID stays open and unimplemented")
        check("no use named" in text,
              "queue: no use is named for the view")
        check("not a build" in text,
              "queue: the tick is a check, not a build")

    # 3. The V7 report §10 records the ID check.
    section10 = report.split("## 10.")[1].split("## 11.")[0]
    flat10 = re.sub(r"\s+", " ", section10)
    check("Unit ID" in section10,
          "report §10: the ID check is recorded")
    check("stays open and unimplemented" in flat10,
          "report §10: the view stays open and unimplemented")
    check("d198a2fe0970e11aaa105bcc4bfb19f9" in section10,
          "report §10: the tool is recorded byte-identical")

    # 4. GDD-03 §2 records the ID check.
    check("Unit ID · Queue 26" in gdd03,
          "GDD-03 §2: the ID check is recorded")
    check("stays open and unimplemented" in gdd03,
          "GDD-03 §2: the view stays open and unimplemented")

    # 5. Scope: only the ID files changed for this unit (union
    # of the working tree and the unit's own commit, found by
    # its message — see the IA script's note).
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 26 ID:",
         "HEAD"], capture_output=True, cwd=ROOT).stdout.decode()
    for sha in own.splitlines():
        if not sha.strip():
            continue
        shown = subprocess.run(
            ["git", "show", "--name-only", "--pretty=format:",
             sha.strip()], capture_output=True,
            cwd=ROOT).stdout.decode()
        names |= {ln for ln in shown.splitlines() if ln.strip()}
    check(names == {"WORK-QUEUE.md",
                    "docs/ECONOMY-SIM-REPORT-V7.md",
                    "docs/GDD-03-ECONOMY-AND-PROFESSIONS.md",
                    "tools/verify_queue26_id.py"},
          "scope: only the four ID files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
