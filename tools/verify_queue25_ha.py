"""Verify Queue 25 Unit HA — Correct the Measured Storm Position
(GC follow-up).

Checks the correction against its sources: tools/economy_sim.py
(the constant is now (4, 23) — 1-based days 4 and 23; FB's (3, 22)
were the 0-based day indices), tools/sim/tests/test_no_regression.py
(the pinned md5 moves to the HA baseline, the GE md5 kept as
history), docs/ECONOMY-SIM-REPORT-V7.md (the FB/GD sections that
quoted the measured position), and docs/GDD-03-ECONOMY-AND-
PROFESSIONS.md §2 (the FB update + the HA update).
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue25_ha.py
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

    # 1. The constant is the true position, 1-based days 4 and 23.
    check(econ.STORM_MEASURED_DAYS == (4, 23),
          "economy_sim.py: STORM_MEASURED_DAYS is (4, 23)",
          str(econ.STORM_MEASURED_DAYS))
    check("STORM_MEASURED_DAYS = (3, 22)" not in sim_src,
          "economy_sim.py: the old (3, 22) constant is gone")
    check("FB encoded the 0-based day indices 3 and 22"
          in sim_src.replace("\n", " ")
          or "0-based day indices 3 and 22" in sim_src,
          "economy_sim.py: the correction records why (3, 22) "
          "was wrong")

    # 2. The tool's own model at the true position dips entry to
    # -100, not -150 (GC's figure, re-measured live here).
    prices = econ.load("prices.json")
    w = next(x for x in prices["wages_monthly"]
             if x["profession_id"] == "construction_worker")
    for tier, dip in (("entry", -100), ("mid", 0), ("senior", 0)):
        row = econ.simulate(prices, w, tier,
                            storm_days=econ.STORM_MEASURED_DAYS)
        check(row["min_balance"] == dip,
              f"tool: measured position dips {tier} to {dip}",
              str(row["min_balance"]))
        check(row["end_balance"] == row["net"],
              f"tool: measured trajectory ends at net ({tier})")
    # The old figure is the model at the wrong position, not
    # erased: (3, 22) still dips entry to -150.
    old = econ.simulate(prices, w, "entry", storm_days=(3, 22))
    check(old["min_balance"] == -150,
          "tool: the old (3, 22) position still dips -150",
          "the -150 is the model at the wrong position")
    # Two-earner measured is unchanged (0 for every tier).
    for tier in ("entry", "mid", "senior"):
        row = econ.simulate(prices, w, tier,
                            storm_days=econ.STORM_MEASURED_DAYS,
                            second_earner=True)
        check(row["min_balance"] == 0,
              f"tool: two-earner measured still 0 ({tier})")

    # 3. The default run: md5 moves to the HA baseline, and the
    # only stdout diff vs the GE run is the one measured cell.
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py")],
        capture_output=True, cwd=ROOT)
    check(out.returncode == 0, "tool: default run exits 0")
    text = out.stdout.decode()
    md5 = hashlib.md5(out.stdout).hexdigest()
    check(md5 == "ede430d0bf391fac3f8599334f55b77b",
          "tool: default-run md5 is the HA baseline", md5)
    check("ede430d0bf391fac3f8599334f55b77b"
          in regress,
          "tests: the HA md5 is pinned in test_no_regression.py")
    check("d699ae7d37fe8ca077f873ba238dd86b" in regress,
          "tests: the GE md5 is kept as history")
    check("e598e416c07b21bacee9fe98fdb27244" in regress,
          "tests: the v7 md5 is kept as history")
    check('["min_balance"], -100' in regress,
          "tests: the FB test pins the corrected -100 dip")
    check('["min_balance"], -150' not in regress,
          "tests: no -150 expectation survives in the suite")
    check("construction_worker    start   5000 + storm dip"
          "    -500 =    4500  OK  (worst storm position)" in text,
          "tool: the bridge line is unchanged (worst dip still "
          "the early -500)")
    check("BRIDGE FAIL rows: []" in text,
          "tool: no bridge failure in any position")
    check("       0     -100       0  (net 900)" in text,
          "tool: the printed storm-position row shows -100")

    # 4. The V7 report: the FB sections quote the corrected
    # position; the GC addendum marks the correction done.
    check("Measured (4, 23)" in report,
          "report §2: the table header is Measured (4, 23)")
    check("Measured (3, 22)" not in report,
          "report: no Measured (3, 22) header survives")
    check("| entry | −500 | 0 | 0 | −100 | 0 | 900 |" in report,
          "report §2: the entry row reads -100")
    check("on day 4 the entry household has banked three days"
          in report.replace("\n", " "),
          "report §2: the day-4 reasoning (three banked days)")
    check("(days 4 and 23) already dips the entry row to −100"
          in report,
          "report §5: the verdict quotes -100 at days 4 and 23")
    check("| entry | −780 | 0 | 0 | 0 | 0 | 5,100 | −500 | −100 | 900 |"
          in report,
          "report §7: the GD table's Single measured is -100")
    check("Unit HA DONE 2026-11-24" in report,
          "report §6: the open item is marked HA DONE")
    check("ede430d0bf391fac3f8599334f55b77b" in report,
          "report §8: the md5 is the HA baseline")
    check("v7 as printed showed −150" in report,
          "report §4: the v7-as-printed figure is kept visible")

    # 5. GDD-03 §2: the FB update quotes the corrected position,
    # and the HA update is appended.
    check("−100 measured (days 4 and 23)" in gdd03,
          "GDD-03 §2: the FB update quotes -100 at days 4 and 23")
    check("Unit HA · Queue 25" in gdd03,
          "GDD-03 §2: the HA update is recorded")
    check("ede430d0bf391fac3f8599334f55b77b" in gdd03,
          "GDD-03 §2: the HA update carries the new md5")

    # 6. Scope: only the four HA files changed, and the old
    # verify scripts are untouched history — the FB/GE scripts
    # pinned the -150 of their own runs and are superseded by
    # this script (they are frozen records, not re-run).
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    check(names == {"tools/economy_sim.py",
                    "tools/sim/tests/test_no_regression.py",
                    "docs/ECONOMY-SIM-REPORT-V7.md",
                    "docs/GDD-03-ECONOMY-AND-PROFESSIONS.md",
                    "tools/verify_queue25_ha.py"},
          "scope: only the five HA files changed", str(sorted(names)))
    old_scripts = subprocess.run(
        ["git", "diff", "--name-only"], capture_output=True,
        cwd=ROOT).stdout.decode()
    check("tools/verify_queue23_fb.py" not in old_scripts
          and "tools/verify_queue24_ge.py" not in old_scripts,
          "scope: the FB/GE verify scripts are untouched history")

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
