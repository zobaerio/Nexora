"""Verify Queue 27 Unit JB — Reconcile the Single-Earner
Renting-Cab Row (IB follow-up).

Checks the decision against its sources: tools/sim/engine.py
(the settlement charges rental_day x WORK_DAYS flat —
200 x 26 = 5,200/month, no Sunday exclusion),
tools/economy_sim.py (the trajectory now charges
extra_daily_cost on days 1-26, so the row ends exactly at
net), tools/sim/tests/test_no_regression.py (a test pins the
row's end_balance == net; the pinned md5 does NOT move —
the default-run output is byte-identical, so the JA baseline
stands), docs/ECONOMY-SIM-REPORT-V7.md §§11, 13 (the
decision, the reasoning and the measured figures), and
docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the JB update).
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue27_jb.py
"""
import hashlib
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
    engine_src = (ROOT / "tools" / "sim" / "engine.py").read_text()
    regress = (ROOT / "tools" / "sim" / "tests"
               / "test_no_regression.py").read_text()
    report = (ROOT / "docs" / "ECONOMY-SIM-REPORT-V7.md").read_text()
    gdd03 = (ROOT / "docs" / "GDD-03-ECONOMY-AND-PROFESSIONS.md").read_text()

    # 1. The settlement's rule, read from the source — the
    # decision follows it, not the v1 23-day rule.
    check("taxi_rental_total += rental_day * econ.WORK_DAYS"
          in engine_src,
          "settlement: _settle_month charges rental_day x"
          " WORK_DAYS flat")
    prices = econ.load("prices.json")
    check(prices["taxi_fares"]["cab_rental_ncr_per_day"] == 200,
          "data: cab rental is 200 NCr/day")
    check(econ.WORK_DAYS == 26,
          "tool: WORK_DAYS is 26")
    check(prices["taxi_fares"]["cab_rental_ncr_per_day"]
          * econ.WORK_DAYS == 5200,
          "tool: the settlement's charge is 200 x 26 = 5200")
    check("Queue 27 Unit JB" in sim_src,
          "tool: the JB decision is recorded in the docstring")
    check("day % 7 != 0" not in sim_src,
          "tool: the v1 Sunday exclusion is gone")

    # 2. The renting row, from the tool itself: the trajectory
    # now charges the full 5,200 and ends exactly at net.
    w = next(x for x in prices["wages_monthly"]
             if x["profession_id"] == "taxi_driver")
    row = econ.simulate(
        prices, w, "entry",
        extra_daily_cost=prices["taxi_fares"]
        ["cab_rental_ncr_per_day"],
        label_suffix=" (renting cab)")
    check(row["extra"] == 5200,
          "tool: the renting row charges 5200", str(row["extra"]))
    check(row["net"] == 1300,
          "tool: the renting row nets 1300", str(row["net"]))
    check(row["min_balance"] == 0,
          "tool: the renting row minbal is 0",
          str(row["min_balance"]))
    check(row["end_balance"] == row["net"] == 1300,
          "tool: the renting row ends exactly at net (1300)",
          str(row["end_balance"]))
    check(row["rate"] == 9.3 and "TIGHT" in row["flags"],
          "tool: the renting row stays TIGHT at 9.3%")

    # 3. The default run: byte-identical output, so the md5
    # does NOT move — the JA baseline stands, no re-pin.
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py")],
        capture_output=True, cwd=ROOT)
    check(out.returncode == 0, "tool: default run exits 0")
    text = out.stdout.decode()
    md5 = hashlib.md5(out.stdout).hexdigest()
    check(md5 == "b70b18972aeb5c3b2d0273b986060058",
          "tool: default-run md5 is still the JA baseline (no"
          " re-pin)", md5)
    check("b70b18972aeb5c3b2d0273b986060058" in regress,
          "tests: the JA md5 is still pinned in"
          " test_no_regression.py")
    check("taxi_driver (renting cab)    entry     14000      0"
          "   2500  12700     1300    9.3        0  TIGHT" in text,
          "tool: the base table's renting row is unchanged")
    check("taxi_driver (renting cab) start   5000 + dip"
          "       0 =    5000  OK" in text,
          "tool: the renting-cab bridge line is unchanged")
    check("construction_worker + construction-worker start"
          "  10000 + same-tier dip   -1231 =    8769  OK"
          "  (worst same-tier storm position)" in text,
          "tool: the JA same-tier bridge line is unchanged")
    check("BRIDGE FAIL rows: []" in text,
          "tool: no bridge failure in any position")

    # 4. The V7 report §13: the decision, the reasoning and
    # the measured figures; §11 marks the gap JB DONE.
    check("## 13. Addendum — Reconcile the single-earner"
          " renting-cab row" in report,
          "report §13: the addendum exists")
    check("follow the settlement's 26-day charge"
          in report.replace("\n", " "),
          "report §13: the decision is stated")
    check("end_balance 1,300" in report
          or "end_balance 1,300 (was 1,900)" in report,
          "report §13: the end-balance figure is quoted")
    check("The md5 does not move" in report,
          "report §13: the md5 staying put is stated, not"
          " hidden")
    check("b70b18972aeb5c3b2d0273b986060058" in report,
          "report §13: the JA baseline md5 is quoted")
    check("Unit JB DONE 2026-11-24" in report,
          "report §11: the renting-row gap is marked JB DONE")
    check("did NOT move the base" in report,
          "report §11: the corrected expectation is recorded")

    # 5. GDD-03 §2 records the JB update.
    check("Unit JB · Queue 27" in gdd03,
          "GDD-03 §2: the JB update is recorded")
    check("1,900 → 1,300" in gdd03,
          "GDD-03 §2: the end-balance move is quoted")
    check("the pinned md5 does not move" in gdd03,
          "GDD-03 §2: the md5 staying put is stated")

    # 6. Scope: only the JB files changed for this unit. The
    # check reads the union of the working tree (before the
    # unit is committed) and the unit's own commit, found by
    # its message (after the commit — and still after later
    # units commit, because the message match is per-unit).
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 27 JB:",
         "HEAD"], capture_output=True, cwd=ROOT).stdout.decode()
    for sha in own.splitlines():
        if not sha.strip():
            continue
        shown = subprocess.run(
            ["git", "show", "--name-only", "--pretty=format:",
             sha.strip()], capture_output=True,
            cwd=ROOT).stdout.decode()
        names |= {ln for ln in shown.splitlines() if ln.strip()}
    check(names == {"tools/economy_sim.py",
                    "tools/sim/tests/test_no_regression.py",
                    "docs/ECONOMY-SIM-REPORT-V7.md",
                    "docs/GDD-03-ECONOMY-AND-PROFESSIONS.md",
                    "tools/verify_queue27_jb.py"},
          "scope: only the five JB files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
