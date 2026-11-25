"""Verify Queue 34 Unit MC — Entry Renting Second Earner in the
Surge Table (MB follow-up).

Checks the wiring against its sources: tools/economy_sim.py
(the KC second-earner surge section now prints the (entry,
renting) pairing at every tier beside the other three — the
surge shrinks its early dips by exactly the entry taxi surge
and closes none; the measured position dips 0 flat and
surged), tools/sim/tests/test_no_regression.py (new tests pin
the per-tier entry-renting surge figures, the three printed
rows, the four-pairings table, and the re-pinned default-run
md5 — the MB md5 is kept as history; the MB "untouched"
test is superseded by the four-pairings test),
docs/ECONOMY-SIM-REPORT-V7.md §23 (the prose matches the
tool output, including the per-tier table and the md5 move),
§16 (the prose table, the Finding, and the verbatim output
gain the three rows) and §22 (the open note is closed), and
docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the MC update).
Re-runs the entry renting second earner for every tier live
and asserts the figures.
Prints one line per check and a summary; exits 0 only when
every check passes.
Run from the repo root: python3 tools/verify_queue34_mc.py
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CHECKS = []

MC_MD5 = "a818a3273cdad108c4d8d4ae198b5b44"
MB_MD5 = "4abf52ff0dc7d00f6acd3168d7c1c807"


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

    # 1. The figures hold: the (entry, renting) second earner
    # at every tier — the early dips shrink by the entry taxi
    # surge and close none, the nets rise +455 at every tier,
    # the measured position dips 0, every trajectory ends
    # exactly at net.
    prices = econ.load("prices.json")
    w = next(w for w in prices["wages_monthly"]
             if w["profession_id"] == "construction_worker")
    kw = {"second_earner": "taxi_driver",
          "second_earner_renting_cab": True}
    expected = (("entry", -193, -163, 5500, 5955),
                ("mid", -288, -258, 8744, 9199),
                ("senior", -419, -389, 12201, 12656))
    checked = 0
    identical = True
    for tier, dip, surged_dip, net, surged_net in expected:
        flat = econ.simulate(prices, w, tier,
                             storm_days=econ.STORM_EARLY_DAYS,
                             **kw)
        surged = econ.simulate(
            prices, w, tier, storm_days=econ.STORM_EARLY_DAYS,
            taxi_rain_days=econ.TAXI_WEATHER_MEASURED_RAIN_DAYS,
            taxi_storm_days=econ.TAXI_WEATHER_MEASURED_STORM_DAYS,
            **kw)
        if (flat["min_balance"], surged["min_balance"],
                flat["net"], surged["net"]) != \
                (dip, surged_dip, net, surged_net):
            identical = False
        if surged["net"] - flat["net"] != 455:
            identical = False
        if surged["end_balance"] != surged["net"]:
            identical = False
        meas = econ.simulate(prices, w, tier,
                             storm_days=econ.STORM_MEASURED_DAYS,
                             **kw)
        meas_surged = econ.simulate(
            prices, w, tier, storm_days=econ.STORM_MEASURED_DAYS,
            taxi_rain_days=econ.TAXI_WEATHER_MEASURED_RAIN_DAYS,
            taxi_storm_days=econ.TAXI_WEATHER_MEASURED_STORM_DAYS,
            **kw)
        if (meas["min_balance"], meas_surged["min_balance"]) \
                != (0, 0):
            identical = False
        checked += 1
    check(checked == 3, "tool: 3 entry-renting surge tiers compared",
          str(checked))
    check(identical,
          "tool: entry-renting surge is entry -193->-163 /"
          " mid -288->-258 / senior -419->-389, nets +455 at"
          " every tier, measured 0 flat and surged")
    check("taxi-driver (entry, renting)" in sim_src
          and "second_earner_renting_cab\": True" in sim_src,
          "tool: the second-earner surge table loops the"
          " (entry, renting) pairing")

    # 2. The wiring: the default run prints the three new
    # rows in the second-earner table, the table now has four
    # pairings, and the default-run md5 moves to the MC pin.
    d1 = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py")],
        capture_output=True, cwd=ROOT)
    check(d1.returncode == 0, "tool: default run exits 0")
    d1_text = d1.stdout.decode()
    second = d1_text.split(
        "taxi-driver second earner weather-surge month")[1]
    for row in ("taxi-driver (entry, renting) entry"
                "         -193         -163     5500       5955",
                "taxi-driver (entry, renting) mid"
                "           -288         -258     8744       9199",
                "taxi-driver (entry, renting) senior"
                "        -419         -389    12201      12656"):
        check(row in second,
              "tool: the second-earner table prints an"
              " entry-renting surge row",
              row.split()[3])
    check(second.count("taxi-driver (entry, renting)") == 3,
          "tool: the second-earner table prints exactly three"
          " entry-renting rows")
    for pairing in ("taxi-driver (entry, owning)",
                    "taxi-driver (mid, owning)",
                    "taxi-driver (mid, renting)",
                    "taxi-driver (entry, renting)"):
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
    check(pinned == MC_MD5,
          "tool: the pinned md5 moved to the MC baseline",
          pinned)
    check(MB_MD5 in regress,
          "tests: the MB md5 is kept as history")
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py"),
         "--shibnagar"],
        capture_output=True, cwd=ROOT)
    check(out.returncode == 0, "tool: --shibnagar run exits 0")
    sh_text = out.stdout.decode()
    check("shibnagar BRIDGE FAIL rows: []" in sh_text,
          "tool: no Shibnagar bridge failure")
    # The base table and bridge lines are untouched.
    check("rows: 36" in d1_text,
          "tool: the base table still has 36 rows")
    check("taxi_driver (renting cab) start   5000 + dip"
          "       0 =    5000  OK  (worst renting tier)"
          in d1_text,
          "tool: the swept renting bridge line is unchanged")

    # 3. The V7 report §23: prose matches the tool output.
    check("## 23. Addendum — Entry renting second earner in the"
          " surge table (Unit MC, Queue 34)" in report,
          "report §23: the addendum exists")
    check("−193" in report.split("## 23.")[1]
          and "12,656" in report.split("## 23.")[1],
          "report §23: the entry-renting surge figures are"
          " quoted")
    check(MC_MD5 in report.split("## 23.")[1],
          "report §23: the md5 move is recorded")
    check("Queue 35" in report.split("## 23.")[1]
          and "Unit MD" in report.split("## 23.")[1],
          "report §23: the surge-section open note is"
          " recorded")
    check("| entry, renting | entry | −193 | −163 | 5,500 | 5,955 |"
          in report.split("## 16.")[1].split("## 17.")[0],
          "report §16: the prose table gains the entry"
          " renting rows")
    check("taxi-driver (entry, renting) senior        -419"
          "         -389    12201      12656"
          in report.split("## 16.")[1].split("## 17.")[0],
          "report §16: the verbatim output gains the entry"
          " renting rows")
    check("shrinks all three early dips"
          in report.split("## 16.")[1].split("## 17.")[0],
          "report §16: the Finding now reads three early dips")
    check("Closed 2026-11-25 by Queue 34 Unit MC"
          in report.split("## 22.")[1].split("## 23.")[0],
          "report §22: the second-earner-table open note is"
          " closed")

    # 4. GDD-03 §2 records the MC update.
    check("Unit MC · Queue 34" in gdd03,
          "GDD-03 §2: the MC update is recorded")
    check("−193" in gdd03
          and "12,656" in gdd03,
          "GDD-03 §2: the entry-renting surge figures are"
          " quoted")
    check("a818a3273cdad108c4d8d4ae198b5b44" in gdd03,
          "GDD-03 §2: the md5 move is recorded")

    # 5. Tests pin the MC rows and the wiring.
    check("test_second_earner_surge_table_has_four_pairings"
          in regress,
          "tests: the four-pairings test exists")
    check("test_second_earner_surge_table_prints_entry_renting_rows"
          in regress,
          "tests: the entry-renting printed-rows test exists")
    check("test_second_earner_surge_table_is_untouched"
          not in regress,
          "tests: the superseded untouched-table test is gone")
    check("-419" in regress
          and "12201, 12656" in regress,
          "tests: the senior entry-renting figures are pinned")

    # 6. Scope: only the MC files changed for this unit.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 34 MC:",
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
                    "tools/verify_queue34_mc.py"},
          "scope: only the five MC files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
