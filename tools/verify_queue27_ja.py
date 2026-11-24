"""Verify Queue 27 Unit JA — Wire the Remaining Two-Earner
Bridge Lines (IA/IC follow-up).

Checks the extension against its sources: tools/economy_sim.py
(the bridge check prints the GD same-tier line and the IC
other-tier lines — the combined canonical start plus the worst
minbal, the minimum across the first earner's tiers and the four
storm positions),
tools/sim/tests/test_no_regression.py (the pinned md5 moves to
the JA baseline, the IC md5 kept as history),
docs/ECONOMY-SIM-REPORT-V7.md §§7, 8, 12 (the prose matches
the tool output, so no two-earner bridge figure is report-only),
and docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the JA update).
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue27_ja.py
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

    # 1. The worst dips per household, from the tool itself —
    # the minimum across the first earner's tiers and the four
    # storm positions. No figure is invented: each is recomputed
    # live by the tool from the measured scenarios.
    prices = econ.load("prices.json")
    w = next(x for x in prices["wages_monthly"]
             if x["profession_id"] == "construction_worker")
    positions = (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                 econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS)
    same = min(econ.simulate(prices, w, tier, storm_days=pos,
                             second_earner=True)["min_balance"]
               for tier in ("entry", "mid", "senior")
               for pos in positions)
    check(same == -1231,
          "tool: worst same-tier dip is -1231 (senior, early)",
          str(same))
    taxi_mid = min(econ.simulate(
        prices, w, tier, storm_days=pos,
        second_earner="taxi_driver",
        second_earner_tier="mid")["min_balance"]
        for tier in ("entry", "mid", "senior")
        for pos in positions)
    check(taxi_mid == 0,
          "tool: worst mid-tier taxi-second dip is 0",
          str(taxi_mid))
    ce_entry = min(econ.simulate(
        prices, w, tier, storm_days=pos,
        second_earner="civil_engineer",
        second_earner_tier="entry")["min_balance"]
        for tier in ("entry", "mid", "senior")
        for pos in positions)
    check(ce_entry == -3210,
          "tool: worst entry civil-engineer-second dip is -3210",
          str(ce_entry))
    # The combined starts are the sums of the two earners' own
    # genesis balances, read from professions.json — the same
    # combined-start rule as IA.
    profs = econ.load("professions.json")
    starts = {p["id"]: p.get("starting_balance_ncr", 0)
              for p in profs["professions"]}
    check(2 * starts["construction_worker"] == 10000,
          "tool: same-tier combined start is 10000 (5000+5000)")
    check(starts["construction_worker"] + starts["taxi_driver"]
          == 10000,
          "tool: mid-tier taxi-second combined start is 10000"
          " (5000+5000)")
    check(starts["construction_worker"]
          + starts["civil_engineer"] == 30000,
          "tool: entry civil-engineer-second combined start is"
          " 30000 (5000+25000)")

    # 2. The default run: md5 moves to the JA baseline; the
    # three new bridge lines are printed; the IA lines are
    # unchanged; nothing fails.
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py")],
        capture_output=True, cwd=ROOT)
    check(out.returncode == 0, "tool: default run exits 0")
    text = out.stdout.decode()
    md5 = hashlib.md5(out.stdout).hexdigest()
    check(md5 == "b70b18972aeb5c3b2d0273b986060058",
          "tool: default-run md5 is the JA baseline", md5)
    check("b70b18972aeb5c3b2d0273b986060058" in regress,
          "tests: the JA md5 is pinned in test_no_regression.py")
    check("d198a2fe0970e11aaa105bcc4bfb19f9" in regress,
          "tests: the IC md5 is kept as history")
    check("construction_worker + construction-worker start"
          "  10000 + same-tier dip   -1231 =    8769  OK"
          "  (worst same-tier storm position)" in text,
          "tool: the same-tier bridge line is printed")
    check("construction_worker + taxi-driver (mid) start"
          "  10000 + other-tier dip       0 =   10000  OK"
          "  (worst other-tier storm position)" in text,
          "tool: the mid-tier taxi-second bridge line is printed")
    check("construction_worker + civil-engineer (entry) start"
          "  30000 + other-tier dip   -3210 =   26790  OK"
          "  (worst other-tier storm position)" in text,
          "tool: the entry civil-engineer-second bridge line is"
          " printed")
    check("construction_worker + taxi-driver    start  10000"
          " + mixed dip     -72 =    9928  OK  (worst mixed"
          " storm position)" in text,
          "tool: the IA taxi-second bridge line is unchanged")
    check("construction_worker + civil-engineer start  30000"
          " + mixed dip   -8623 =   21377  OK  (worst mixed"
          " storm position)" in text,
          "tool: the IA civil-engineer-second bridge line is"
          " unchanged")
    check("BRIDGE FAIL rows: []" in text,
          "tool: no bridge failure in any position")

    # 3. The V7 report §§7, 8, 12: prose matches the tool
    # output, so no two-earner bridge figure is report-only.
    check("Unit JA DONE 2026-11-24" in report.split("## 8.")[0],
          "report §7: the same-tier bridge gap is marked JA"
          " DONE")
    check("10,000 − 1,231 = 8,769" in report,
          "report §7: the same-tier bridge figure is quoted")
    check("construction_worker + construction-worker start"
          "  10000 + same-tier dip   -1231 =    8769  OK"
          "  (worst same-tier storm position)" in report,
          "report §8: the same-tier line is quoted verbatim")
    check("construction_worker + taxi-driver (mid) start"
          "  10000 + other-tier dip       0 =   10000  OK"
          "  (worst other-tier storm position)" in report,
          "report §8: the mid-tier taxi-second line is quoted"
          " verbatim")
    check("construction_worker + civil-engineer (entry) start"
          "  30000 + other-tier dip   -3210 =   26790  OK"
          "  (worst other-tier storm position)" in report,
          "report §8: the entry civil-engineer-second line is"
          " quoted verbatim")
    check("b70b18972aeb5c3b2d0273b986060058" in report,
          "report §8: the md5 is the JA baseline")
    check("d198a2fe0970e11aaa105bcc4bfb19f9" in report,
          "report §8: the IC md5 is kept as history")
    check("Unit JA DONE 2026-11-24" in report.split("## 12.")[1],
          "report §12: the other-tier bridge gap is marked JA"
          " DONE")
    check("10,000 − 0 = 10,000" in report
          and "30,000 − 3,210 = 26,790" in report,
          "report §12: the other-tier bridge figures are quoted")

    # 4. GDD-03 §2 records the JA update.
    check("Unit JA · Queue 27" in gdd03,
          "GDD-03 §2: the JA update is recorded")
    check("10,000 − 1,231 = 8,769" in gdd03,
          "GDD-03 §2: the same-tier figure is quoted")
    check("10,000 − 0 = 10,000" in gdd03
          and "30,000 − 3,210 = 26,790" in gdd03,
          "GDD-03 §2: the other-tier figures are quoted")

    # 5. Scope: only the JA files changed for this unit. The
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
        ["git", "log", "--format=%H", "--grep=^Queue 27 JA:",
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
                    "tools/verify_queue27_ja.py"},
          "scope: only the five JA files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
