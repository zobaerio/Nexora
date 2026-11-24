"""Verify Queue 26 Unit IB — Renting-Cab Taxi Second Earner
(HD follow-up).

Checks the extension against its sources: tools/economy_sim.py
(simulate() takes second_earner_renting_cab=True with the taxi
second earner — the rental is the settlement's rule, 200/day ×
26 worked days = 5,200/month, a monthly cost line),
tools/sim/tests/test_no_regression.py (the pinned md5 moves to
the IB baseline, the IA md5 kept as history),
docs/ECONOMY-SIM-REPORT-V7.md §11 (the addendum, with verbatim
output matching the tool), and docs/GDD-03-ECONOMY-AND-
PROFESSIONS.md §2 (the IB update).
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue26_ib.py
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
    regress = (ROOT / "tools" / "sim" / "tests"
               / "test_no_regression.py").read_text()
    report = (ROOT / "docs" / "ECONOMY-SIM-REPORT-V7.md").read_text()
    gdd03 = (ROOT / "docs" / "GDD-03-ECONOMY-AND-PROFESSIONS.md").read_text()

    # 1. The rental is the settlement's rule, read from the
    # source data — not an invented count.
    prices = econ.load("prices.json")
    check(prices["taxi_fares"]["cab_rental_ncr_per_day"] == 200,
          "data: cab rental is 200 NCr/day in prices.json")
    check(econ.WORK_DAYS == 26,
          "tool: the settlement charges the rental on 26 days"
          " (WORK_DAYS)")
    engine_src = (ROOT / "tools" / "sim" / "engine.py").read_text()
    check("taxi_rental_total += rental_day * econ.WORK_DAYS"
          in engine_src,
          "settlement: engine._settle_month charges rental_day x"
          " WORK_DAYS flat")
    w = next(x for x in prices["wages_monthly"]
             if x["profession_id"] == "construction_worker")

    # 2. The measured month-1 minbal per position, renting cab.
    renting_measured = {t: econ.simulate(
        prices, w, t, storm_days=econ.STORM_MEASURED_DAYS,
        second_earner="taxi_driver",
        second_earner_renting_cab=True)["min_balance"]
        for t in ("entry", "mid", "senior")}
    check(renting_measured == {"entry": 0, "mid": 0, "senior": 0},
          "tool: renting-cab measured dips nothing",
          str(renting_measured))
    for tier, dip, net in (("entry", -193, 5500),
                           ("mid", -288, 8744),
                           ("senior", -419, 12201)):
        row = econ.simulate(
            prices, w, tier, storm_days=econ.STORM_EARLY_DAYS,
            second_earner="taxi_driver",
            second_earner_renting_cab=True)
        check(row["min_balance"] == dip and row["net"] == net,
              f"tool: renting-cab {tier} early dips {dip}, net"
              f" {net}",
              f"minbal {row['min_balance']}, net {row['net']}")
        check(row["second_earner_rental"] == 5200,
              f"tool: renting-cab {tier} rental is 5200")
        check(row["end_balance"] == row["net"],
              f"tool: renting-cab {tier} trajectory ends at net")

    # 3. The rental is exactly 5,200 on top of the owning
    # variant — costs +5,200, net −5,200, gross/tax untouched.
    ok = True
    for tier in ("entry", "mid", "senior"):
        for pos in (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                    econ.STORM_LATE_DAYS,
                    econ.STORM_MEASURED_DAYS):
            owning = econ.simulate(prices, w, tier, storm_days=pos,
                                   second_earner="taxi_driver")
            renting = econ.simulate(
                prices, w, tier, storm_days=pos,
                second_earner="taxi_driver",
                second_earner_renting_cab=True)
            if (renting["costs_total"] - owning["costs_total"]
                    != 5200
                    or owning["net"] - renting["net"] != 5200
                    or renting["gross"] != owning["gross"]
                    or renting["tax"] != owning["tax"]):
                ok = False
    check(ok, "tool: renting is exactly +5200 costs / -5200 net"
          " at every tier and position")
    owning = econ.simulate(prices, w, "entry",
                           storm_days=econ.STORM_MEASURED_DAYS,
                           second_earner="taxi_driver")
    check(owning["second_earner_rental"] == 0
          and not owning["second_earner_renting_cab"],
          "tool: the owning driver charges no rental")

    # 4. The default run: md5 moves to the IB baseline; the
    # renting section is printed; nothing fails.
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py")],
        capture_output=True, cwd=ROOT)
    check(out.returncode == 0, "tool: default run exits 0")
    text = out.stdout.decode()
    md5 = hashlib.md5(out.stdout).hexdigest()
    check(md5 == "27464ea221694880a4369f805d8cd455",
          "tool: default-run md5 is the IB baseline", md5)
    check("27464ea221694880a4369f805d8cd455" in regress,
          "tests: the IB md5 is pinned in test_no_regression.py")
    check("45a45edc63cee4b142891da938ef79bd" in regress,
          "tests: the IA md5 is kept as history")
    check("renting-cab taxi-driver second earner storm-position"
          " month" in text,
          "tool: the renting-cab section is printed")
    check("renting the cab at 200/day x 26 = 5,200/mo" in text,
          "tool: the section names the settlement's rental rule")
    check("BRIDGE FAIL rows: []" in text,
          "tool: no bridge failure in any position")

    # 5. The V7 report §11: the addendum, the table, the
    # verbatim output matching the tool, and the honest limit.
    check("## 11. Addendum — Renting-cab taxi-driver second"
          " earner" in report,
          "report §11: the addendum exists")
    check("| entry | −193 | 0 | 0 | 0 | 0 | 5,500 | 0 | 0 |"
          " 10,700 |" in report,
          "report §11: the renting table's entry row")
    check("| senior | −419 | 0 | 0 | 0 | 0 | 12,201 | −72 | 0 |"
          " 17,401 |" in report,
          "report §11: the renting table's senior row")
    check("10,000 − 419 = 9,581" in report,
          "report §11: the renting bridge figure is quoted")
    check("the rental re-opens the early dip" in report.replace(
        "\n", " "),
          "report §11: the finding is stated, not hidden")
    blocks = re.findall(r"```\n(renting-cab.*?)\n```", report,
                        re.S)
    tool_sections = "\n\n".join(
        s for s in text.split("\n\n")
        if s.startswith("renting-cab"))
    check(len(blocks) == 1 and blocks[0].strip()
          == tool_sections.strip(),
          "report §11: the verbatim output matches the tool")
    check("single-earner renting-cab row" in report.replace(
        "\n", " ") and "600/month" in report,
          "report §11: the single-earner rental discrepancy is"
          " recorded honestly")
    check("Unit IB DONE 2026-11-24" in report,
          "report §9: the renting-cab gap is marked IB DONE")
    check("27464ea221694880a4369f805d8cd455" in report,
          "report §11: the md5 is the IB baseline")

    # 6. GDD-03 §2 records the IB update.
    check("Unit IB · Queue 26" in gdd03,
          "GDD-03 §2: the IB update is recorded")
    check("−193 / −288 / −419" in gdd03,
          "GDD-03 §2: the renting early dips are quoted")
    check("600/month" in gdd03,
          "GDD-03 §2: the single-earner rental discrepancy is"
          " recorded")

    # 7. Scope: only the IB files changed for this unit (union
    # of the working tree and the unit's own commit, found by
    # its message — see the IA script's note).
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 26 IB:",
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
                    "tools/verify_queue26_ib.py"},
          "scope: only the five IB files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
