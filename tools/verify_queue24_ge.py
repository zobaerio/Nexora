"""Verify Queue 24 Unit GE — Storm-Position Bridge Line
(GDD-03 §2; FB follow-up).

Checks the wiring against its sources: tools/economy_sim.py
(the bridge check prints the construction_worker entry row's
starting balance + worst storm-position minbal), tools/sim/tests/
test_no_regression.py (the new md5 pin + the bridge-line tests,
with v7 kept as history), docs/ECONOMY-SIM-REPORT-V7.md §8
(the line quoted verbatim + the new md5), and
tools/verify_queue23_fb.py (its struck md5 checks updated, not
left failing). Runs the tool live and checks its md5 against the
pin.
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue24_ge.py
"""
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CHECKS = []
NEW_MD5 = "d699ae7d37fe8ca077f873ba238dd86b"
V7_MD5 = "e598e416c07b21bacee9fe98fdb27244"


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def main():
    econ_src = (ROOT / "tools" / "economy_sim.py").read_text()
    report = (ROOT / "docs" / "ECONOMY-SIM-REPORT-V7.md").read_text()
    regress = (ROOT / "tools" / "sim" / "tests"
               / "test_no_regression.py").read_text()
    fb_script = (ROOT / "tools" / "verify_queue23_fb.py").read_text()
    from tools import economy_sim as econ
    prices = econ.load("prices.json")
    w = next(w for w in prices["wages_monthly"]
             if w["profession_id"] == "construction_worker")

    # 1. The bridge check wires the worst storm-position dip.
    main_src = econ_src.split("def main()")[1]
    bridge = main_src.split("first-month bridge check")[1] \
        .split("if \"--shibnagar\"")[0]
    check("worst_storm" in bridge,
          "economy_sim.py: the bridge check computes a storm dip")
    check("STORM_EARLY_DAYS, STORM_MID_DAYS" in bridge
          and "STORM_LATE_DAYS, STORM_MEASURED_DAYS" in bridge,
          "economy_sim.py: the worst dip spans all four positions")
    check("+ storm dip" in bridge,
          "economy_sim.py: the storm line is printed")
    check("(worst storm position)" in bridge,
          "economy_sim.py: the storm line is labelled")
    check('bridge_fail.append("construction_worker (storm)")'
          in bridge,
          "economy_sim.py: a failing storm line joins BRIDGE FAIL")
    check("storm_worst = start + worst_storm" in bridge,
          "economy_sim.py: the storm line applies the start balance")

    # 2. The worst dip is the early one (computed, not quoted).
    dips = [econ.simulate(prices, w, "entry", storm_days=pos)
            ["min_balance"]
            for pos in (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                        econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS)]
    check(min(dips) == -500,
          "figures: the worst entry storm dip is -500 (early)",
          str(dips))
    check(dips == [-500, 0, 0, -150],
          "figures: the four position dips are -500/0/0/-150",
          str(dips))

    # 3. The pin moves; v7 (and v6) are kept as history.
    check(f'ECONOMY_SIM_BASELINE_MD5 = "{NEW_MD5}"' in regress,
          "test_no_regression.py: the new md5 is pinned")
    check(V7_MD5 in regress,
          "test_no_regression.py: the v7 md5 is kept as history")
    check("9ac10779c231b7aa6120a6ff457982de" in regress,
          "test_no_regression.py: the v6 md5 is kept as history")
    check("test_storm_position_bridge_line_is_printed" in regress,
          "tests: the bridge-line test exists")
    check("test_worst_storm_position_dip_is_the_early_one"
          in regress,
          "tests: the worst-dip test exists")

    # 4. The report records the line and the new md5.
    check("## 8. Addendum — Storm-position bridge line"
          " (Unit GE, Queue 24)" in report,
          "report V7: the GE addendum exists")
    check("construction_worker    start   5000 + storm dip"
          "    -500 =    4500  OK  (worst storm position)" in report,
          "report V7: the bridge line is quoted verbatim")
    check(NEW_MD5 in report,
          "report V7: the new md5 is recorded")
    check("No tuning call" in report,
          "report V7: no tuning call is taken")

    # 5. The FB script's struck md5 checks were updated, not left
    # failing.
    check(f'"{NEW_MD5}"' in fb_script,
          "verify_queue23_fb.py: the struck md5 check is updated")
    check("Queue 24 Units GD" in fb_script
          or "Units GD" in fb_script,
          "verify_queue23_fb.py: the update is noted")

    # 6. Live: the tool runs, the line prints, the md5 matches.
    out = subprocess.run([sys.executable,
                          str(ROOT / "tools" / "economy_sim.py")],
                         capture_output=True, cwd=ROOT)
    check(out.returncode == 0, "live: economy_sim.py runs clean")
    md5 = hashlib.md5(out.stdout).hexdigest()
    check(md5 == NEW_MD5,
          "live: the default-run md5 matches the new pin", md5)
    text = out.stdout.decode()
    check("construction_worker    start   5000 + storm dip"
          "    -500 =    4500  OK  (worst storm position)" in text,
          "live: the bridge line prints with the figures")
    check("BRIDGE FAIL rows: []" in text,
          "live: no bridge failure")
    check("two-earner storm-position month (Unit GD" in text,
          "live: the GD section still prints")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed, "
          f"{len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
