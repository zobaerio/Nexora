"""Verify Queue 33 Unit MB — Renting Rows in the Surge Section
(MA follow-up).

Checks the wiring against its sources: tools/economy_sim.py
(the KC taxi weather-surge section now prints the
single-earner renting-cab row at every tier, beside the
owning rows — the mid/senior rows rise by exactly the
owning driver's surge deltas because the rental stays the
flat 5,200 unsurged; the second-earner surge table is
untouched), tools/sim/tests/test_no_regression.py (new
tests pin the per-tier renting surge figures, the three
printed rows, the untouched second-earner table, and the
re-pinned default-run md5 — the MA md5 is kept as history),
docs/ECONOMY-SIM-REPORT-V7.md §22 (the prose matches the
tool output, including the per-tier table and the md5 move)
and §16 (the table and verbatim output gain the two rows),
and docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the MB
update). Re-runs the renting surge rows for every tier live
and asserts the figures.
Prints one line per check and a summary; exits 0 only when
every check passes.
Run from the repo root: python3 tools/verify_queue33_mb.py
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CHECKS = []

MB_MD5 = "4abf52ff0dc7d00f6acd3168d7c1c807"
MA_MD5 = "bc9a35e1c95d4b8a512c0a4a6e0994cd"


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

    # 1. The figures hold: the renting surge row at every
    # tier — the same flat 5,200/month rental, the net rising
    # by exactly the owning driver's surge delta, the surged
    # net exactly 5,200 below the owning surged net, minbal
    # 0 flat and surged, trajectory ends exactly at net.
    prices = econ.load("prices.json")
    cab = prices["taxi_fares"]["cab_rental_ncr_per_day"]
    check(cab * econ.WORK_DAYS == 5200,
          "tool: the rental is 200/day x 26 = 5200/month")
    w = next(w for w in prices["wages_monthly"]
             if w["profession_id"] == "taxi_driver")
    expected = (("entry", 14000, 14700, 1300, 1755, 455),
                ("mid", 23000, 24150, 6750, 7441, 691),
                ("senior", 36000, 37800, 14550, 15630, 1080))
    checked = 0
    identical = True
    for tier, flat_gross, surged_gross, flat_net, surged_net, delta in expected:
        flat = econ.simulate(
            prices, w, tier, extra_daily_cost=cab,
            label_suffix=" (renting cab)")
        surged = econ.simulate(
            prices, w, tier, extra_daily_cost=cab,
            label_suffix=" (renting cab)",
            taxi_rain_days=econ.TAXI_WEATHER_MEASURED_RAIN_DAYS,
            taxi_storm_days=econ.TAXI_WEATHER_MEASURED_STORM_DAYS)
        if (flat["gross"], surged["gross"], flat["net"],
                surged["net"], surged["net"] - flat["net"]) != \
                (flat_gross, surged_gross, flat_net, surged_net,
                 delta):
            identical = False
        if surged["extra"] != 5200:
            identical = False
        if surged["end_balance"] != surged["net"]:
            identical = False
        if (flat["min_balance"], surged["min_balance"]) != (0, 0):
            identical = False
        owning_flat = econ.simulate(prices, w, tier)
        owning_surged = econ.simulate(
            prices, w, tier,
            taxi_rain_days=econ.TAXI_WEATHER_MEASURED_RAIN_DAYS,
            taxi_storm_days=econ.TAXI_WEATHER_MEASURED_STORM_DAYS)
        if owning_surged["net"] - owning_flat["net"] != delta:
            identical = False
        if owning_surged["net"] - surged["net"] != 5200:
            identical = False
        checked += 1
    check(checked == 3, "tool: 3 renting surge tiers compared",
          str(checked))
    check(identical,
          "tool: renting surge rows are entry 1300->1755 /"
          " mid 6750->7441 / senior 14550->15630, deltas"
          " equal owning, surged nets 5200 below owning,"
          " minbal 0 flat and surged")
    check("for tier in (\"entry\", \"mid\", \"senior\"):" in sim_src
          and "label_suffix=\" (renting cab)\"" in sim_src,
          "tool: the surge section loops the renting row over"
          " all three tiers")

    # 2. The wiring: the default run prints all three
    # renting rows in the KC section, the second-earner table
    # is untouched, and the default-run md5 moves to the MB
    # pin.
    d1 = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py")],
        capture_output=True, cwd=ROOT)
    check(d1.returncode == 0, "tool: default run exits 0")
    d1_text = d1.stdout.decode()
    section = d1_text.split(
        "taxi weather-surge month (Unit KC")[1].split(
        "taxi-driver second earner")[0]
    for row in ("taxi_driver (renting cab)    entry        14000"
                "   14700     1300       1755      +455",
                "taxi_driver (renting cab)    mid          23000"
                "   24150     6750       7441      +691",
                "taxi_driver (renting cab)    senior       36000"
                "   37800    14550      15630     +1080"):
        check(row in section,
              "tool: the KC section prints a renting surge row",
              row.split()[3])
    check(section.count("(renting cab)") == 3,
          "tool: the KC section prints exactly three renting"
          " rows")
    second = d1_text.split(
        "taxi-driver second earner weather-surge month")[1]
    check("taxi-driver (mid, renting)" in second
          and "senior, renting" not in second,
          "tool: the second-earner surge table is untouched")
    check("BRIDGE FAIL rows: []" in d1_text,
          "tool: no D1 bridge failure")
    md5 = hashlib.md5(d1.stdout).hexdigest()
    pinned = re.search(
        r'ECONOMY_SIM_BASELINE_MD5 = "([0-9a-f]{32})"',
        regress).group(1)
    check(md5 == pinned,
          "tool: default-run md5 equals the pinned baseline",
          md5)
    check(pinned == MB_MD5,
          "tool: the pinned md5 moved to the MB baseline",
          pinned)
    check(MA_MD5 in regress,
          "tests: the MA md5 is kept as history")
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py"),
         "--shibnagar"],
        capture_output=True, cwd=ROOT)
    check(out.returncode == 0, "tool: --shibnagar run exits 0")
    sh_text = out.stdout.decode()
    check("shibnagar BRIDGE FAIL rows: []" in sh_text,
          "tool: no Shibnagar bridge failure")
    check(sh_text.count(
        "taxi_driver (renting cab)    mid          23000"
        "   24150     6750       7441      +691") == 1,
          "tool: the --shibnagar run prints the mid renting"
          " surge row once (D1 section only)")
    # The base table and bridge lines are untouched.
    check("rows: 36" in d1_text,
          "tool: the base table still has 36 rows")
    check("taxi_driver (renting cab) start   5000 + dip"
          "       0 =    5000  OK  (worst renting tier)"
          in d1_text,
          "tool: the swept renting bridge line is unchanged")

    # 3. The V7 report §22: prose matches the tool output.
    check("## 22. Addendum — Renting rows in the surge section"
          " (Unit MB, Queue 33)" in report,
          "report §22: the addendum exists")
    check("7,441" in report.split("## 22.")[1]
          and "15,630" in report.split("## 22.")[1],
          "report §22: the mid/senior surged renting nets are"
          " quoted")
    check(MB_MD5 in report.split("## 22.")[1],
          "report §22: the md5 move is recorded")
    check("Queue 34" in report.split("## 22.")[1]
          and "Unit MC" in report.split("## 22.")[1],
          "report §22: the second-earner-table open note is"
          " recorded")
    check("mid (renting cab) | 23,000 | 24,150 | 6,750 | 7,441"
          in report.split("## 16.")[1].split("## 17.")[0],
          "report §16: the prose table gains the mid renting"
          " row")
    check("taxi_driver (renting cab)    senior       36000"
          "   37800    14550      15630     +1080"
          in report.split("## 16.")[1].split("## 17.")[0],
          "report §16: the verbatim output gains the senior"
          " renting row")
    check("Closed 2026-11-25 by Queue 33 Unit MB"
          in report.split("## 21.")[1].split("## 22.")[0],
          "report §21: the surge-section open note is closed")

    # 4. GDD-03 §2 records the MB update.
    check("Unit MB · Queue 33" in gdd03,
          "GDD-03 §2: the MB update is recorded")
    check("mid 6,750" in gdd03
          and "15,630" in gdd03,
          "GDD-03 §2: the mid/senior surged renting nets are"
          " quoted")
    check("4abf52ff0dc7d00f6acd3168d7c1c807" in gdd03,
          "GDD-03 §2: the md5 move is recorded")

    # 5. Tests pin the MB rows and the wiring.
    check("test_renting_surge_rows_at_all_tiers_are_measured"
          in regress,
          "tests: the per-tier renting surge figures test"
          " exists")
    check("test_surge_table_prints_all_three_renting_rows"
          in regress,
          "tests: the three-rows test exists")
    check("test_second_earner_surge_table_is_untouched"
          in regress,
          "tests: the untouched-second-table test exists")

    # 6. Scope: only the MB files changed for this unit.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 33 MB:",
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
                    "tools/verify_queue33_mb.py"},
          "scope: only the five MB files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
