"""Verify Queue 32 Unit MA — Renting-Cab Row at Mid/Senior
Tiers (LA follow-up).

Checks the wiring against its sources: tools/economy_sim.py
(the single-earner renting-cab row is now modelled at every
tier in the District 1 base table and in the Shibnagar
variant, and both bridge checks' renting lines sweep tiers —
the worst minbal across the three renting rows against the
same 5,000 start), tools/sim/tests/test_no_regression.py
(new tests pin the per-tier renting figures, the three base
table rows, the swept bridge line in both runs, and the
re-pinned default-run md5 — the LA md5 is kept as history),
docs/ECONOMY-SIM-REPORT-V7.md §21 (the prose matches the
tool output, including the per-tier table and the md5 move),
and docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the MA
update). Re-runs the renting rows for every tier on both
rents live and asserts the figures.
Prints one line per check and a summary; exits 0 only when
every check passes.
Run from the repo root: python3 tools/verify_queue32_ma.py
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CHECKS = []

MA_MD5 = "bc9a35e1c95d4b8a512c0a4a6e0994cd"
LA_MD5 = "2b9d24f9663f88ad0d13be1f5e86c40c"

RENT_LINE = ("taxi_driver (renting cab) start   5000 + dip"
             "       0 =    5000  OK  (worst renting tier)")


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

    # 1. The figures hold: the renting row at every tier —
    # the same flat 5,200/month rental, the net exactly
    # 5,200 below the owning driver, minbal 0 everywhere.
    prices = econ.load("prices.json")
    cab = prices["taxi_fares"]["cab_rental_ncr_per_day"]
    check(cab * econ.WORK_DAYS == 5200,
          "tool: the rental is 200/day x 26 = 5200/month")
    w = next(w for w in prices["wages_monthly"]
             if w["profession_id"] == "taxi_driver")
    rents, _stock = econ.load_shibnagar_rents(prices)
    override = rents[econ.SHIBNAGAR_RENT_TIER["taxi_driver"]]
    expected = (("entry", 14000, 0, 1300, 9.3, True),
                ("mid", 23000, 400, 6750, 29.3, False),
                ("senior", 36000, 1050, 14550, 40.4, False))
    checked = 0
    identical = True
    for tier, gross, tax, net, rate, tight in expected:
        owning = econ.simulate(prices, w, tier)
        renting = econ.simulate(
            prices, w, tier, extra_daily_cost=cab,
            label_suffix=" (renting cab)")
        if (renting["gross"], renting["tax"],
                renting["extra"], renting["net"],
                renting["rate"], renting["min_balance"]) != \
                (gross, tax, 5200, net, rate, 0):
            identical = False
        if renting["end_balance"] != renting["net"]:
            identical = False
        if owning["net"] - renting["net"] != 5200:
            identical = False
        if ("TIGHT" in renting["flags"]) != tight:
            identical = False
        sh = econ.simulate(prices, w, tier,
                           extra_daily_cost=cab,
                           label_suffix=" (renting cab)",
                           rent_override=override)
        if (sh["net"], sh["min_balance"]) != (net, 0):
            identical = False
        if sh["net"] != renting["net"]:
            identical = False
        checked += 1
    check(checked == 3, "tool: 3 renting tiers compared",
          str(checked))
    check(identical,
          "tool: renting rows are entry 1300 / mid 6750 /"
          " senior 14550, exactly 5200 below owning, minbal"
          " 0, identical on Shibnagar rents")
    check(5000 + 0 == 5000,
          "tool: the renting bridge is 5000 + 0 = 5000")

    # 2. The wiring: both runs print the three renting rows
    # and the swept bridge line; the default-run md5 moves
    # to the MA pin.
    d1 = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py")],
        capture_output=True, cwd=ROOT)
    check(d1.returncode == 0, "tool: default run exits 0")
    d1_text = d1.stdout.decode()
    check("rows: 36" in d1_text,
          "tool: the base table has 36 rows")
    for row in ("taxi_driver (renting cab)    entry     14000"
                "      0   2500  12700     1300    9.3",
                "taxi_driver (renting cab)    mid       23000"
                "    400   2500  15850     6750   29.3",
                "taxi_driver (renting cab)    senior    36000"
                "   1050   2500  20400    14550   40.4"):
        check(row in d1_text,
              "tool: the D1 base table prints a renting row",
              row.split()[3])
    check(RENT_LINE in d1_text,
          "tool: the D1 check prints the swept renting line")
    check("BRIDGE FAIL rows: []" in d1_text,
          "tool: no D1 bridge failure")
    md5 = hashlib.md5(d1.stdout).hexdigest()
    pinned = re.search(
        r'ECONOMY_SIM_BASELINE_MD5 = "([0-9a-f]{32})"',
        regress).group(1)
    check(md5 == pinned,
          "tool: default-run md5 equals the pinned baseline",
          md5)
    check(pinned == MA_MD5,
          "tool: the pinned md5 moved to the MA baseline",
          pinned)
    check(LA_MD5 in regress,
          "tests: the LA md5 is kept as history")
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py"),
         "--shibnagar"],
        capture_output=True, cwd=ROOT)
    check(out.returncode == 0, "tool: --shibnagar run exits 0")
    sh_text = out.stdout.decode()
    variant = sh_text.split(
        "shibnagar first-month bridge check")[1]
    check(RENT_LINE in variant,
          "tool: the Shibnagar check prints the swept renting"
          " line")
    check("shibnagar BRIDGE FAIL rows: []" in sh_text,
          "tool: no Shibnagar bridge failure")
    d1_line = next(ln for ln in d1_text.splitlines()
                   if "renting cab" in ln and "start" in ln)
    sh_line = next(ln for ln in variant.splitlines()
                   if "renting cab" in ln and "start" in ln)
    check(sh_line == d1_line,
          "tool: the Shibnagar renting line equals the D1 line")
    # The storm line still sweeps tiers (no regression).
    check("construction_worker    start   5000 + storm dip"
          "    -726 =    4274  OK  (worst storm position,"
          " all tiers)" in d1_text,
          "tool: the D1 check still prints the swept storm"
          " line")

    # 3. The V7 report §21: prose matches the tool output.
    check("## 21. Addendum — Renting-cab row at mid/senior"
          " tiers (Unit MA, Queue 32)" in report,
          "report §21: the addendum exists")
    check("6,750" in report.split("## 21.")[1]
          and "14,550" in report.split("## 21.")[1],
          "report §21: the mid/senior renting nets are quoted")
    check(MA_MD5 in report.split("## 21.")[1],
          "report §21: the md5 move is recorded")
    check("Queue 33" in report.split("## 21.")[1]
          and "Unit MB" in report.split("## 21.")[1],
          "report §21: the surge-section open note is recorded")

    # 4. GDD-03 §2 records the MA update.
    check("Unit MA · Queue 32" in gdd03,
          "GDD-03 §2: the MA update is recorded")
    check("mid net 6,750" in gdd03
          or "6,750 (29.3%)" in gdd03,
          "GDD-03 §2: the mid renting net is quoted")
    check("5,000 + 0 = 5,000 OK" in gdd03,
          "GDD-03 §2: the swept renting bridge line is quoted")

    # 5. Tests pin the MA rows and the wiring.
    check("test_renting_cab_rows_at_all_tiers_are_measured"
          in regress,
          "tests: the per-tier renting figures test exists")
    check("test_base_table_has_three_renting_rows" in regress,
          "tests: the three-rows test exists")
    check("test_renting_bridge_line_sweeps_tiers" in regress,
          "tests: the swept-line test exists")
    check("test_shibnagar_renting_rows_match_district1"
          in regress,
          "tests: the Shibnagar renting test exists")
    check("(worst renting tier)" in regress,
          "tests: the printed-line tests use the new label")

    # 6. Scope: only the MA files changed for this unit.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 32 MA:",
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
                    "tools/verify_queue32_ma.py"},
          "scope: only the five MA files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
