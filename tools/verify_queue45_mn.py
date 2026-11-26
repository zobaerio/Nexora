"""Verify Queue 45 Unit MN — Senior Taxi-Driver Second
Earner in the Surge Table (MM follow-up).

Checks the wiring against its sources: tools/economy_sim.py
(the KC second-earner surge table now prints the (senior,
owning) pairing at every tier beside the other four — the
early dip is 0 flat and surged at every tier and storm
position, the nets rise by exactly the senior taxi surge
(+1,080 at every tier); the measured position dips 0 flat
and surged; the renting senior-tier taxi second earner
stays allowed but unprinted),
tools/sim/tests/test_no_regression.py (new tests pin the
per-tier senior-owning surge figures, the three printed
rows, the five-pairings table, the Shibnagar identity over
all 132 rows, and the re-pinned default-run md5 — the MM
md5 is kept as history; the four-pairings test is
superseded by the five-pairings test),
docs/ECONOMY-SIM-REPORT-V7.md §34 (the prose matches the
tool output, including the per-tier table and the md5 move),
§16 (the prose table, the Finding, and the verbatim output
gain the three rows) and §33 (the open note is closed), and
docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the MN update).
Re-runs the senior owning second earner for every tier and
storm position live and asserts the figures.
Prints one line per check and a summary; exits 0 only when
every check passes.
Run from the repo root: python3 tools/verify_queue45_mn.py
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CHECKS = []

MN_MD5 = "c70567cb94bd018ef50df1470fdbe746"
MN_SH_MD5 = "95022a1592dca4d34b91f5f0a6890526"
MM_MD5 = "47ec8771cc8bca2889d62faa3b23c6e6"
MM_SH_MD5 = "402b9eb3e286aba1a446c0ae49b8b012"


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

    # 1. The figures hold: the (senior, owning) second earner
    # at every tier × every storm position — the early dip is
    # 0 flat and surged, the nets rise +1,080 at every tier,
    # the measured position dips 0, every trajectory ends
    # exactly at net, and the delta is the senior
    # single-earner taxi surge delta.
    prices = econ.load("prices.json")
    bands = {w["profession_id"]: w
             for w in prices["wages_monthly"]}
    w = bands["construction_worker"]
    kw = {"second_earner": "taxi_driver",
          "second_earner_tier": "senior"}
    expected = (("entry", 23950, 25030),
                ("mid", 27194, 28274),
                ("senior", 30651, 31731))
    positions = (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                 econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS)
    checked = 0
    identical = True
    for tier, net, surged_net in expected:
        for pos in positions:
            flat = econ.simulate(prices, w, tier, storm_days=pos,
                                 **kw)
            surged = econ.simulate(
                prices, w, tier, storm_days=pos,
                taxi_rain_days=econ
                .TAXI_WEATHER_MEASURED_RAIN_DAYS,
                taxi_storm_days=econ
                .TAXI_WEATHER_MEASURED_STORM_DAYS, **kw)
            if (flat["min_balance"], surged["min_balance"],
                    flat["net"], surged["net"]) != \
                    (0, 0, net, surged_net):
                identical = False
            if surged["net"] - flat["net"] != 1080:
                identical = False
            if surged["end_balance"] != surged["net"]:
                identical = False
            checked += 1
    check(checked == 12,
          "tool: 12 senior-owning surge tier/position rows"
          " compared",
          str(checked))
    check(identical,
          "tool: senior-owning surge is early 0->0 at every"
          " tier and position, nets +1,080 at every tier,"
          " every trajectory ends at net")
    own_flat = econ.simulate(prices, bands["taxi_driver"],
                             "senior")
    own_surged = econ.simulate(
        prices, bands["taxi_driver"], "senior",
        taxi_rain_days=econ.TAXI_WEATHER_MEASURED_RAIN_DAYS,
        taxi_storm_days=econ.TAXI_WEATHER_MEASURED_STORM_DAYS)
    check(own_surged["net"] - own_flat["net"] == 1080,
          "tool: the delta is the senior single-earner taxi"
          " surge delta",
          str(own_surged["net"] - own_flat["net"]))
    # The monthly-paid senior civil engineer cannot surge.
    with_rain = {"taxi_rain_days": 2, "taxi_storm_days": 2}
    refused = False
    try:
        econ.simulate(prices, w, "entry",
                      second_earner="civil_engineer",
                      second_earner_tier="senior", **with_rain)
    except ValueError:
        refused = True
    check(refused,
          "tool: the senior CE second earner refuses the"
          " taxi surge (monthly-paid, by construction)")
    check("taxi-driver (senior, owning)" in sim_src
          and '"second_earner_tier": "senior"' in sim_src,
          "tool: the second-earner surge table loops the"
          " (senior, owning) pairing")

    # 2. The wiring: the default run prints the three new
    # rows in the second-earner table, the table now has five
    # pairings, and the default-run md5 moves to the MN pin.
    d1 = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py")],
        capture_output=True, cwd=ROOT)
    check(d1.returncode == 0, "tool: default run exits 0")
    d1_text = d1.stdout.decode()
    second = d1_text.split(
        "taxi-driver second earner weather-surge month")[1]
    for row in ("taxi-driver (senior, owning) entry"
                "            0            0    23950      25030",
                "taxi-driver (senior, owning) mid"
                "              0            0    27194      28274",
                "taxi-driver (senior, owning) senior"
                "           0            0    30651      31731"):
        check(row in second,
              "tool: the second-earner table prints a"
              " senior-owning surge row",
              row.split()[3])
    check(second.count("taxi-driver (senior, owning)") == 3,
          "tool: the second-earner table prints exactly three"
          " senior-owning rows")
    for pairing in ("taxi-driver (entry, owning)",
                    "taxi-driver (mid, owning)",
                    "taxi-driver (mid, renting)",
                    "taxi-driver (entry, renting)",
                    "taxi-driver (senior, owning)"):
        check(pairing in second,
              "tool: the second-earner table keeps a pairing",
              pairing)
    check("senior, renting" not in second,
          "tool: no senior renting pairing is printed")
    check("BRIDGE FAIL rows: []" in d1_text,
          "tool: no D1 bridge failure")
    md5 = hashlib.md5(d1.stdout).hexdigest()
    pinned = re.search(
        r'ECONOMY_SIM_BASELINE_MD5 = "([0-9a-f]{32})"',
        regress).group(1)
    check(md5 == pinned,
          "tool: default-run md5 equals the pinned baseline",
          md5)
    check(pinned == MN_MD5,
          "tool: the pinned md5 moved to the MN baseline",
          pinned)
    check(MM_MD5 in regress,
          "tests: the MM md5 is kept as history")
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py"),
         "--shibnagar"],
        capture_output=True, cwd=ROOT)
    check(out.returncode == 0, "tool: --shibnagar run exits 0")
    sh_text = out.stdout.decode()
    sh_md5 = hashlib.md5(out.stdout).hexdigest()
    check(sh_md5 == MN_SH_MD5,
          "tool: --shibnagar md5 is the MN baseline",
          sh_md5)
    check("shibnagar BRIDGE FAIL rows: []" in sh_text,
          "tool: no Shibnagar bridge failure")
    sh_second = sh_text.split(
        "shibnagar taxi-driver second earner weather-surge"
        " month")[1]
    check("taxi-driver (senior, owning) senior           0"
          "            0    30651      31731" in sh_second,
          "tool: the Shibnagar table prints the senior-owning"
          " rows too")
    # The base table and bridge lines are untouched.
    check("rows: 36" in d1_text,
          "tool: the base table still has 36 rows")
    check("taxi_driver (renting cab) start   5000 + dip"
          "       0 =    5000  OK  (worst renting tier)"
          in d1_text,
          "tool: the swept renting bridge line is unchanged")
    check("construction_worker + taxi-driver (senior)"
          " start  10000 + other-tier dip       0"
          " =   10000  OK" in d1_text,
          "tool: the MM senior bridge line is unchanged")

    # 3. The V7 report §34: prose matches the tool output.
    check("## 34. Addendum — Senior taxi-driver second earner"
          " in the surge table (Unit MN, Queue 45)" in report,
          "report §34: the addendum exists")
    s34 = report.split("## 34.")[1]
    s34_flat = " ".join(s34.split())
    check("DECIDED" in s34 and "five pairings" in s34_flat,
          "report §34: the five-pairings decision is stated")
    check("23,950" in s34_flat and "25,030" in s34_flat
          and "27,194" in s34_flat and "28,274" in s34_flat
          and "30,651" in s34_flat and "31,731" in s34_flat,
          "report §34: the senior-owning surge figures are"
          " quoted")
    check("+1,080" in s34_flat,
          "report §34: the +1,080 delta is quoted")
    check(MN_MD5 in s34 and MN_SH_MD5 in s34
          and MM_MD5 in s34 and MM_SH_MD5 in s34,
          "report §34: both md5 moves are recorded")
    check("132 rows" in s34_flat,
          "report §34: the 132-row Shibnagar identity is"
          " recorded")
    check("Queue 46" in s34 and "Unit MO" in s34,
          "report §34: the follow-up names Queue 46")
    check("## 16." in report
          and "| senior, owning | entry | 0 | 0 | 23,950 | 25,030 |"
          in report.split("## 16.")[1].split("## 17.")[0],
          "report §16: the prose table gains the senior"
          " owning rows")
    check("taxi-driver (senior, owning) senior           0"
          "            0    30651      31731"
          in report.split("## 16.")[1].split("## 17.")[0],
          "report §16: the verbatim output gains the senior"
          " owning rows")
    check("132 rows" in report.split("## 16.")[1]
          .split("## 17.")[0],
          "report §16: the Shibnagar identity is now 132 rows")
    check("The senior owning row (Unit MN, Queue 45, §34)"
          " dips 0" in " ".join(
              report.split("## 16.")[1].split("## 17.")[0]
              .split()),
          "report §16: the Finding gains the senior owning row")
    check("Closed 2026-11-26 by Queue 45 Unit MN"
          in report.split("## 33.")[1].split("## 34.")[0],
          "report §33: the second-earner-table open note is"
          " closed")

    # 4. GDD-03 §2 records the MN update.
    check("Unit MN · Queue 45" in gdd03,
          "GDD-03 §2: the MN update is recorded")
    check("23,950" in gdd03 and "31,731" in gdd03,
          "GDD-03 §2: the senior-owning surge figures are"
          " quoted")
    check(MN_MD5 in gdd03 and MN_SH_MD5 in gdd03,
          "GDD-03 §2: the md5 moves are recorded")

    # 5. The economy_sim.py comments record the MN outcome.
    check("Queue 45 Unit MN" in sim_src,
          "tool: the comments name the MN wiring")
    check("report §34" in sim_src,
          "tool: the comments record §34")

    # 6. Tests pin the MN rows and the wiring.
    check("test_senior_taxi_second_earner_surge_is_measured"
          in regress,
          "tests: the senior-owning surge figures test exists")
    check("test_second_earner_surge_table_has_five_pairings"
          in regress,
          "tests: the five-pairings test exists")
    check("test_second_earner_surge_table_prints_senior_owning_rows"
          in regress,
          "tests: the senior-owning printed-rows test exists")
    check("test_second_earner_surge_table_has_four_pairings"
          not in regress,
          "tests: the superseded four-pairings test is gone")
    check("30651, 31731" in regress,
          "tests: the senior surge figures are pinned")
    check("132" in regress and "21)" in regress,
          "tests: the 132-row identity and 21-row table"
          " counts are pinned")

    # 7. Scope: only the MN files changed for this unit.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 45 MN:",
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
                    "tools/verify_queue45_mn.py"},
          "scope: only the five MN files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
