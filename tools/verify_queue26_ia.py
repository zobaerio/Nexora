"""Verify Queue 26 Unit IA — Two-Earner Bridge Line (GD/HD
follow-up).

Checks the extension against its sources: tools/economy_sim.py
(the bridge check prints a mixed two-earner line per measured
second-earner profession — the combined canonical start plus
the worst mixed minbal, the minimum across the first earner's
tiers and the four storm positions),
tools/sim/tests/test_no_regression.py (the pinned md5 moves to
the IA baseline, the HD md5 kept as history),
docs/ECONOMY-SIM-REPORT-V7.md §§7–9 (the prose matches the
tool output, including the correction of HD's civil-engineer
combined start from 10,000 to the sourced 30,000), and
docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the IA update).
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue26_ia.py
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
    regress = (ROOT / "tools" / "sim" / "tests"
               / "test_no_regression.py").read_text()
    report = (ROOT / "docs" / "ECONOMY-SIM-REPORT-V7.md").read_text()
    gdd03 = (ROOT / "docs" / "GDD-03-ECONOMY-AND-PROFESSIONS.md").read_text()

    # 1. The worst mixed dip per pairing, from the tool itself.
    prices = econ.load("prices.json")
    w = next(x for x in prices["wages_monthly"]
             if x["profession_id"] == "construction_worker")
    for pid2, worst in (("taxi_driver", -72),
                        ("civil_engineer", -8623)):
        dips = [econ.simulate(prices, w, tier, storm_days=pos,
                              second_earner=pid2)["min_balance"]
                for tier in ("entry", "mid", "senior")
                for pos in (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                            econ.STORM_LATE_DAYS,
                            econ.STORM_MEASURED_DAYS)]
        check(min(dips) == worst,
              f"tool: worst mixed dip for {pid2} is {worst}",
              str(sorted(set(dips))))
    # The combined starts are the sums of the two earners' own
    # genesis balances, read from professions.json — not one
    # figure applied to both pairings.
    profs = econ.load("professions.json")
    starts = {p["id"]: p.get("starting_balance_ncr", 0)
              for p in profs["professions"]}
    check(starts["construction_worker"] + starts["taxi_driver"]
          == 10000,
          "tool: taxi-second combined start is 10000 (5000+5000)")
    check(starts["construction_worker"]
          + starts["civil_engineer"] == 30000,
          "tool: civil-engineer-second combined start is 30000"
          " (5000+25000)")

    # 2. The default run: md5 moves to the IA baseline; the
    # mixed bridge lines are printed; nothing fails.
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py")],
        capture_output=True, cwd=ROOT)
    check(out.returncode == 0, "tool: default run exits 0")
    text = out.stdout.decode()
    md5 = hashlib.md5(out.stdout).hexdigest()
    check(md5 == "45a45edc63cee4b142891da938ef79bd",
          "tool: default-run md5 is the IA baseline", md5)
    check("45a45edc63cee4b142891da938ef79bd" in regress,
          "tests: the IA md5 is pinned in test_no_regression.py")
    check("5431558ffa3d023c436366c26535f932" in regress,
          "tests: the HD md5 is kept as history")
    check("construction_worker + taxi-driver    start  10000"
          " + mixed dip     -72 =    9928  OK  (worst mixed"
          " storm position)" in text,
          "tool: the taxi-second bridge line is printed")
    check("construction_worker + civil-engineer start  30000"
          " + mixed dip   -8623 =   21377  OK  (worst mixed"
          " storm position)" in text,
          "tool: the civil-engineer-second bridge line is printed")
    check("construction_worker    start   5000 + storm dip"
          "    -500 =    4500  OK  (worst storm position)" in text,
          "tool: the single-earner storm line is unchanged")
    check("BRIDGE FAIL rows: []" in text,
          "tool: no bridge failure in any position")

    # 3. The V7 report §§7–9: prose matches the tool output,
    # including the correction of HD's civil-engineer start.
    check("Unit IA DONE 2026-11-24" in report,
          "report §7: the mixed bridge gap is marked IA DONE")
    check("construction_worker + taxi-driver    start  10000"
          " + mixed dip     -72 =    9928  OK  (worst mixed"
          " storm position)" in report,
          "report §8: the taxi-second line is quoted verbatim")
    check("construction_worker + civil-engineer start  30000"
          " + mixed dip   -8623 =   21377  OK  (worst mixed"
          " storm position)" in report,
          "report §8: the civil-engineer-second line is quoted"
          " verbatim")
    check("45a45edc63cee4b142891da938ef79bd" in report,
          "report §8: the md5 is the IA baseline")
    check("5431558ffa3d023c436366c26535f932" in report,
          "report §8: the HD md5 is kept as history")
    check("30,000 − 8,623 = 21,377" in report,
          "report §9: the corrected civil-engineer bridge figure"
          " is quoted")
    check("10,000 − 8,623 = 1,377" in report
          and "superseded" in report,
          "report §9: HD's 10,000 figure is named and superseded,"
          " not silently dropped")
    check("Unit IA DONE 2026-11-24" in report.split("## 9.")[1],
          "report §9: the bridge-line gap is marked IA DONE")
    check("16,877" in report,
          "report §10: the seed caveat carries the corrected"
          " figure")

    # 4. GDD-03 §2 records the IA update and the correction.
    check("Unit IA · Queue 26" in gdd03,
          "GDD-03 §2: the IA update is recorded")
    check("30,000 − 8,623 = 21,377" in gdd03,
          "GDD-03 §2: the corrected figure is quoted")
    check("10,000 − 8,623 = 1,377" in gdd03,
          "GDD-03 §2: the superseded figure is named")

    # 5. Scope: only the IA files changed for this unit. The
    # check reads the union of the working tree (before the
    # unit is committed) and the unit's own commit, found by
    # its message (after the commit — and still after later
    # units commit, because the message match is per-unit).
    # The Queue 25 scripts checked the dirty tree only and
    # failed post-commit; the local `main` branch is stale
    # (Session 03), so a diff against it is meaningless here.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 26 IA:",
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
                    "tools/verify_queue26_ia.py"},
          "scope: only the five IA files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
