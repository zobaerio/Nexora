"""Verify Queue 22 Unit EY — Economy Balance Re-run with Day-Wage
Pay (GDD-03 §2; ES follow-up).

Checks the v6 re-run against its sources: tools/economy_sim.py
(the day-wage model + the storm-month section), the measured
worked-days evidence (scheduler 30/30, live run 28/30),
docs/ECONOMY-SIM-REPORT-V6.md (the corrected figures, verbatim),
GDD-03 §2 (the stale-figures limit is closed), and the tests
(test_no_regression.py: the v6 pinned md5 + the day-wage tests).
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue22_ey.py
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
    sim_src = (ROOT / "tools" / "economy_sim.py").read_text()
    report = (ROOT / "docs" / "ECONOMY-SIM-REPORT-V6.md").read_text()
    gdd03 = (ROOT / "docs" / "GDD-03-ECONOMY-AND-PROFESSIONS.md").read_text()
    regress = (ROOT / "tools" / "sim" / "tests"
               / "test_no_regression.py").read_text()
    from tools import economy_sim as econ
    prices = econ.load("prices.json")
    w = next(w for w in prices["wages_monthly"]
             if w["profession_id"] == "construction_worker")

    # 1. The tool models the ES day wage.
    check("DAY_WAGE_WORKED_DAYS = 30" in sim_src,
          "economy_sim.py: normal month is 30 worked days")
    check("day_wage_worked_days=None" in sim_src,
          "economy_sim.py: simulate takes a worked-days override")
    check("round(wage_row[tier] * worked / DAYS)" in sim_src,
          "economy_sim.py: gross is band x worked/30")
    check("balance += (base_gross - base_tax) / DAYS" in sim_src,
          "economy_sim.py: day wage accrues evenly at band/30 per day")
    daily_branch = sim_src.split('elif sched == "daily":')[1] \
        .split("else:")[0]
    check("WORK_DAYS" not in daily_branch
          and "(base_gross - base_tax) / DAYS" in daily_branch,
          "economy_sim.py: the v5 23-pay-day branch is gone")
    check('"end_balance": round(balance)' in sim_src,
          "economy_sim.py: the trajectory end balance is returned")

    # 2. The figures are the corrected ones (computed, not quoted).
    base = econ.simulate(prices, w, "entry")
    check(base["gross"] == 9000 and base["net"] == 1500
          and base["rate"] == 16.7 and base["end_balance"] == 1500,
          "figures: normal month pays the band (entry 9000/1500/16.7%)")
    storm = econ.simulate(prices, w, "entry", day_wage_worked_days=28)
    check(storm["gross"] == 8400 and storm["net"] == 900
          and storm["rate"] == 10.7,
          "figures: storm month pays 28/30 (entry 8400/900/10.7%)")
    senior = econ.simulate(prices, w, "senior",
                           day_wage_worked_days=28)
    check(senior["gross"] == 18667 and senior["tax"] == 183
          and senior["net"] == 7601,
          "figures: storm senior recomputes tax (18667/183/7601)")
    bad = []
    for ww in prices["wages_monthly"]:
        for tier in ("entry", "mid", "senior"):
            r = econ.simulate(prices, ww, tier)
            if r["end_balance"] != r["net"]:
                bad.append((ww["profession_id"], tier))
    check(not bad,
          "figures: the trajectory ends at net for all 33 rows",
          f"{bad}" if bad else "")

    # 3. The default run prints the storm section; the base table
    # is unchanged vs v5 (only the new section differs).
    out = subprocess.run([sys.executable,
                          str(ROOT / "tools" / "economy_sim.py")],
                         capture_output=True, cwd=ROOT)
    text = out.stdout.decode()
    check(out.returncode == 0, "tool: the default run exits 0")
    check("day-wage storm month (Unit EY" in text,
          "tool: the default run prints the storm section")
    check("construction_worker          entry      8400      0   2500"
          "   7500      900   10.7" in text,
          "tool: the storm entry row is printed verbatim")
    md5 = hashlib.md5(out.stdout).hexdigest()
    check("9ac10779c231b7aa6120a6ff457982de" in regress,
          "tests: the v6 pinned md5 is recorded")
    check(md5 == "9ac10779c231b7aa6120a6ff457982de",
          "tool: the default-run md5 matches the v6 pin",
          md5)

    # 4. The report records the measurements and the verdicts.
    check("30/30 days" in report,
          "report: the scheduler measurement (30/30) is recorded")
    check("28 worked days" in report,
          "report: the live-run measurement (28/30) is recorded")
    check("days 3 and 22" in report,
          "report: the storm days are named")
    check("9ac10779c231b7aa6120a6ff457982de" in report,
          "report: the v6 md5 is recorded")
    check("UNCHANGED (and that is the finding)" in report,
          "report: the normal-month verdict is recorded")
    check("No tuning call" in report,
          "report: no tuning call is taken")

    # 5. GDD-03 §2 closes the stale-figures limit.
    check("closed by Unit EY" in gdd03,
          "GDD-03 §2: the stale-figures limit is closed")
    check("still models construction-worker income as the monthly"
          " band" not in gdd03,
          "GDD-03 §2: the stale wording is gone")

    # 6. Tests pin the model.
    check("class TestDayWageModelling" in regress,
          "tests: the day-wage test class exists")
    check("test_trajectory_ends_at_net_for_every_row" in regress,
          "tests: trajectory/net equality is pinned for every row")
    check("test_construction_worker_storm_month_pays_28_of_30"
          in regress,
          "tests: the 28/30 storm month is pinned")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed, "
          f"{len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
