"""Verify Queue 24 Unit GD — Two-Earner Storm-Position Scenario
(GDD-03 §2; FB follow-up).

Checks the scenario against its sources: tools/economy_sim.py
(the second_earner kwarg + the new default-run section),
tools/sim/tests/test_no_regression.py (the two-earner tests),
docs/ECONOMY-SIM-REPORT-V7.md §7 (the table beside the
single-earner figures, verbatim), and tools/sim/engine.py
(the _living_costs scaling the costs follow). Runs the tool
live and checks the section prints with the measured figures.
(The default-run md5 moves with this unit and again with Unit
GE; the pin is updated once, by GE — this script does not pin
it.)
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue24_gd.py
"""
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
    econ_src = (ROOT / "tools" / "economy_sim.py").read_text()
    report = (ROOT / "docs" / "ECONOMY-SIM-REPORT-V7.md").read_text()
    regress = (ROOT / "tools" / "sim" / "tests"
               / "test_no_regression.py").read_text()
    engine_src = (ROOT / "tools" / "sim" / "engine.py").read_text()
    from tools import economy_sim as econ
    prices = econ.load("prices.json")
    w = next(w for w in prices["wages_monthly"]
             if w["profession_id"] == "construction_worker")

    # 1. The kwarg and its refusals.
    check("second_earner=False" in econ_src,
          "economy_sim.py: simulate takes second_earner")
    sim = econ_src.split("def simulate(")[1].split("def ")[0]
    check("gross *= 2" in sim and "tax *= 2" in sim,
          "economy_sim.py: gross and tax double per earner")
    check("uplift *= 2" in sim,
          "economy_sim.py: the uplift doubles (per earner)")
    check("food *= 2" in sim and "clothing *= 2" in sim
          and "transport *= 2" in sim and "eating *= 2" in sim,
          "economy_sim.py: food/clothing/transport/eating scale x2")
    check("second_earner is a day-wage scenario" in sim,
          "economy_sim.py: second_earner refused off day-wage")
    check("cannot combine with the v3" in sim,
          "economy_sim.py: second_earner refused with side income")
    check('"second_earner": second_earner' in sim,
          "economy_sim.py: the flag is returned")

    # 2. The figures are the measured ones (computed, not quoted).
    two = econ.simulate(prices, w, "entry",
                        storm_days=econ.STORM_MEASURED_DAYS,
                        second_earner=True)
    check(two["min_balance"] == 0 and two["net"] == 5100,
          "figures: two-earner measured entry dips 0 (net 5100)")
    early = econ.simulate(prices, w, "entry",
                          storm_days=econ.STORM_EARLY_DAYS,
                          second_earner=True)
    check(early["min_balance"] == -780,
          "figures: two-earner early entry dips -780")
    mid = econ.simulate(prices, w, "mid",
                        storm_days=econ.STORM_EARLY_DAYS,
                        second_earner=True)
    senior = econ.simulate(prices, w, "senior",
                           storm_days=econ.STORM_EARLY_DAYS,
                           second_earner=True)
    check(mid["min_balance"] == -970 and mid["net"] == 11588,
          "figures: two-earner early mid dips -970 (net 11588)")
    check(senior["min_balance"] == -1231
          and senior["net"] == 18502,
          "figures: two-earner early senior dips -1231 (net 18502)")
    single = econ.simulate(prices, w, "entry",
                           storm_days=econ.STORM_EARLY_DAYS)
    check(early["min_balance"] < single["min_balance"],
          "figures: the early dip is deeper two-earner than one",
          f"{early['min_balance']} vs {single['min_balance']}")
    bad = []
    for tier in ("entry", "mid", "senior"):
        for pos in (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                    econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS):
            r = econ.simulate(prices, w, tier, storm_days=pos,
                              second_earner=True)
            if r["end_balance"] != r["net"]:
                bad.append((tier, pos))
    check(not bad,
          "figures: the trajectory ends at net for every two-earner"
          " row", f"{bad}" if bad else "")

    # 3. The costs follow engine._living_costs, not an invented
    # line.
    lc = engine_src.split("def _living_costs(")[1].split("def ")[0]
    check('"food": round(lc["food_home_cooking"][band]' in lc,
          "engine.py: food scales with household size")
    check('"clothing": round(lc["clothing_personal"][band]' in lc,
          "engine.py: clothing scales with household size")
    check("for pid in earner_pids" in lc,
          "engine.py: transport is per earner")
    check("max(1, len(earner_pids))" in lc,
          "engine.py: eating out is per earner")
    check("utilities" in lc and "medical" in lc,
          "engine.py: utilities/medical are flat per household")

    # 4. The report records the table and the finding.
    check("## 7. Addendum — Two-earner storm-position scenario"
          " (Unit GD, Queue 24)" in report,
          "report V7: the GD addendum exists")
    check("construction_worker          entry      -780       0"
          "       0        0       0  (net 5100)" in report,
          "report V7: the two-earner entry row is quoted verbatim")
    check("construction_worker          senior    -1231" in report,
          "report V7: the two-earner senior row is quoted verbatim")
    check("a second earner does not help the early-position dip"
          in report,
          "report V7: the early-dip finding is recorded")
    check("2 × 5,000 = 10,000" in report,
          "report V7: the combined starting balance is stated")
    check("No tuning call" in report,
          "report V7: no tuning call is taken")

    # 5. Tests pin the model.
    check("test_two_earner_storm_position_minbal_is_measured"
          in regress,
          "tests: the measured-minbal test exists")
    check("test_two_earner_costs_follow_engine_scaling" in regress,
          "tests: the engine-scaling test exists")
    check("test_two_earner_trajectory_still_ends_at_net" in regress,
          "tests: the trajectory-still-ends-at-net test exists")
    check("test_second_earner_is_refused_off_day_wage" in regress,
          "tests: the refusal test exists")

    # 6. Live: the tool runs and the new section prints.
    out = subprocess.run([sys.executable,
                          str(ROOT / "tools" / "economy_sim.py")],
                         capture_output=True, cwd=ROOT)
    check(out.returncode == 0, "live: economy_sim.py runs clean")
    text = out.stdout.decode()
    check("two-earner storm-position month (Unit GD" in text,
          "live: the two-earner section prints")
    check("construction_worker          entry      -780       0"
          "       0        0       0  (net 5100)" in text,
          "live: the two-earner entry row prints with the figures")
    check("day-wage storm-position month (Unit FB" in text,
          "live: the single-earner section still prints")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed, "
          f"{len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
