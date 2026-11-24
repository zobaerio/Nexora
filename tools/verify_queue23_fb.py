"""Verify Queue 23 Unit FB — Storm-Timing Balance Scenario
(GDD-03 §2; EY follow-up).

Checks the scenario against its sources: tools/economy_sim.py
(the storm_days position model + the new default-run section),
tools/sim/tests/test_no_regression.py (the v7 md5 pin + the
position tests), docs/ECONOMY-SIM-REPORT-V7.md (the verbatim
output and the measured minbal per storm position, with the v6
even-spread figure labelled as such), and GDD-03 §2 (the open
item closed). Runs the tool live and checks its md5 against the
pin. Prints one line per check and a summary; exits 0 only when
every check passes.
Run from the repo root: python3 tools/verify_queue23_fb.py
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
    gdd03 = (ROOT / "docs" / "GDD-03-ECONOMY-AND-PROFESSIONS.md") \
        .read_text()
    econ_src = (ROOT / "tools" / "economy_sim.py").read_text()
    report = (ROOT / "docs" / "ECONOMY-SIM-REPORT-V7.md").read_text()
    regress = (ROOT / "tools" / "sim" / "tests"
               / "test_no_regression.py").read_text()

    # 1. The position model in simulate().
    check("day_wage_worked_days=None, storm_days=None" in econ_src,
          "economy_sim.py: simulate takes storm_days")
    sim = econ_src.split("def simulate(")[1].split("def ")[0]
    check("storm_set = set(storm_days)" in sim,
          "economy_sim.py: the storm days become a set")
    check("worked = DAYS - len(storm_set)" in sim,
          "economy_sim.py: worked days are 30 minus storm days")
    check("storm_days imply " in sim,
          "economy_sim.py: a disagreeing worked count is refused")
    check("distinct day numbers in" in sim,
          "economy_sim.py: days outside 1..30 or repeats refused")
    check("storm_days is a day-wage scenario" in sim,
          "economy_sim.py: storm_days refused off day-wage pay")
    traj = sim.split('elif sched == "daily":')[1]
    check("elif day not in storm_set:" in traj,
          "economy_sim.py: pay lands only on worked days")
    check("(base_gross - base_tax) / worked" in traj,
          "economy_sim.py: worked days share the month's pay")
    check("STORM_EARLY_DAYS = (1, 2)" in econ_src
          and "STORM_MID_DAYS = (15, 16)" in econ_src
          and "STORM_LATE_DAYS = (29, 30)" in econ_src
          and "STORM_MEASURED_DAYS = (3, 22)" in econ_src,
          "economy_sim.py: the four storm positions are named")
    main_src = econ_src.split("def main()")[1]
    check("storm-position month (Unit FB" in main_src,
          "economy_sim.py: the new default-run section exists")
    check("day_wage_worked_days=28" in main_src,
          "economy_sim.py: the v6 even-spread section is unchanged")

    # 2. The pin + the tests.
    check('ECONOMY_SIM_BASELINE_MD5 = "e598e416c07b21bacee9fe98fdb27244"'
          in regress,
          "test_no_regression.py: the v7 md5 is pinned")
    check("9ac10779c231b7aa6120a6ff457982de" in regress,
          "test_no_regression.py: the v6 md5 is kept as history")
    check("test_storm_position_minbal_is_measured" in regress,
          "tests: the measured-minbal test exists")
    check("test_storm_position_trajectory_still_ends_at_net"
          in regress,
          "tests: the trajectory-still-ends-at-net test exists")
    check("test_storm_days_must_be_one_coherent_month" in regress,
          "tests: the storm-days validation test exists")
    check('["min_balance"], -500' in regress
          or '["min_balance"], -500)' in regress
          or '), -500)' in regress,
          "tests: the early entry dip (-500) is pinned")
    check('["min_balance"], -150' in regress,
          "tests: the measured entry dip (-150) is pinned")

    # 3. The report: verbatim output, measured figures, and the
    # v6 figure labelled for what it is.
    check("day-wage storm-position month (Unit FB" in report,
          "report V7: the new section is quoted verbatim")
    check("construction_worker          entry      -500       0"
          "       0     -150       0  (net 900)" in report,
          "report V7: the entry row is quoted verbatim")
    check("construction_worker          mid        -595" in report,
          "report V7: the mid row is quoted verbatim")
    check("construction_worker          senior     -726" in report,
          "report V7: the senior row is quoted verbatim")
    check("e598e416c07b21bacee9fe98fdb27244" in report,
          "report V7: the v7 md5 is recorded")
    check("even-spread figure" in report,
          "report V7: the v6 figure is labelled even-spread")
    check("5,000 − 500 = 4,500" in report,
          "report V7: the worst dip is bridged against the start")
    check("No tuning call" in report,
          "report V7: no tuning call is recorded")
    check("only the measured position (days 3 and 22) is where"
          in report,
          "report V7: the scenario positions are not oversold")

    # 4. GDD-03 §2: the open item is closed.
    check("Update, Unit FB" in gdd03,
          "GDD-03 §2: the FB closure note is present")
    check("Open, recorded: the tool's storm scenario accrues"
          not in gdd03,
          "GDD-03 §2: no open storm-timing item remains")
    check("ECONOMY-SIM-REPORT-V7.md" in gdd03,
          "GDD-03 §2: the V7 report is cited")

    # 5. Live: the tool runs and its md5 matches the pin.
    out = subprocess.run([sys.executable,
                          str(ROOT / "tools" / "economy_sim.py")],
                         capture_output=True, cwd=ROOT)
    check(out.returncode == 0, "live: economy_sim.py runs clean")
    md5 = hashlib.md5(out.stdout).hexdigest()
    check(md5 == "e598e416c07b21bacee9fe98fdb27244",
          "live: the default-run md5 matches the v7 pin", md5)
    text = out.stdout.decode()
    check("day-wage storm-position month (Unit FB" in text,
          "live: the storm-position section prints")
    check("construction_worker          entry      -500       0"
          "       0     -150       0  (net 900)" in text,
          "live: the entry row prints with the measured figures")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed, "
          f"{len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
