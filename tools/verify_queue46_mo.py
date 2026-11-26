"""Verify Queue 46 Unit MO — Renting Senior-Tier Taxi
Second Earner in the Surge Table (MN follow-up).

Checks the decision against its sources:
tools/economy_sim.py (a comment only — the KC
second-earner surge table still prints five pairings, the
(senior, renting) pairing stays allowed but unprinted;
the default run's output is byte-identical, so the pinned
md5 does NOT move),
tools/sim/tests/test_no_regression.py (a new test pins
the measured (senior, renting) surge figures — dip 0 flat
and surged at every tier and storm position, nets
18,750 -> 19,830 / 21,994 -> 23,074 / 25,451 -> 26,531,
+1,080 at every tier, exactly 5,200 below the owning
surged net — in both cities; the five-pairings and
not-printed tests still stand, with the MO decision noted),
docs/ECONOMY-SIM-REPORT-V7.md §35 (the prose matches the
measurement, including the per-tier table and the md5
standing), §16 (the Finding gains the renting senior row)
and §34 (the open note is closed), and
docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the MO update).
Re-runs the (senior, renting) second earner for every tier
and storm position live and asserts the figures.
Prints one line per check and a summary; exits 0 only when
every check passes.
Run from the repo root: python3 tools/verify_queue46_mo.py
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

    # 1. The figures hold: the (senior, renting) second
    # earner at every tier x every storm position — the
    # early dip is 0 flat and surged, the nets rise +1,080
    # at every tier, every net is exactly 5,200 below the
    # owning surged net, every trajectory ends exactly at
    # net — in both cities (the variant's own rents).
    prices = econ.load("prices.json")
    bands = {w["profession_id"]: w
             for w in prices["wages_monthly"]}
    w = bands["construction_worker"]
    kw = {"second_earner": "taxi_driver",
          "second_earner_tier": "senior",
          "second_earner_renting_cab": True}
    own_kw = {"second_earner": "taxi_driver",
              "second_earner_tier": "senior"}
    expected = (("entry", 18750, 19830),
                ("mid", 21994, 23074),
                ("senior", 25451, 26531))
    positions = (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                 econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS)
    weather = dict(
        taxi_rain_days=econ.TAXI_WEATHER_MEASURED_RAIN_DAYS,
        taxi_storm_days=econ.TAXI_WEATHER_MEASURED_STORM_DAYS)
    rents, _stock = econ.load_shibnagar_rents(prices)
    shib_cw = rents[econ.SHIBNAGAR_RENT_TIER[
        "construction_worker"]]
    checked = 0
    identical = True
    for tier, net, surged_net in expected:
        for pos in positions:
            flat = econ.simulate(prices, w, tier,
                                 storm_days=pos, **kw)
            surged = econ.simulate(
                prices, w, tier, storm_days=pos,
                **weather, **kw)
            own_surged = econ.simulate(
                prices, w, tier, storm_days=pos,
                **weather, **own_kw)
            sh_flat = econ.simulate(prices, w, tier,
                                    storm_days=pos,
                                    rent_override=shib_cw, **kw)
            sh_surged = econ.simulate(
                prices, w, tier, storm_days=pos,
                rent_override=shib_cw, **weather, **kw)
            if (flat["min_balance"], surged["min_balance"],
                    flat["net"], surged["net"]) != \
                    (0, 0, net, surged_net):
                identical = False
            if surged["net"] - flat["net"] != 1080:
                identical = False
            if own_surged["net"] - surged["net"] != 5200:
                identical = False
            if surged["end_balance"] != surged["net"]:
                identical = False
            if (sh_flat["min_balance"], sh_surged["min_balance"],
                    sh_flat["net"], sh_surged["net"]) != \
                    (0, 0, net, surged_net):
                identical = False
            if sh_surged["end_balance"] != sh_surged["net"]:
                identical = False
            checked += 1
    check(checked == 12,
          "tool: 12 renting-senior surge tier/position rows"
          " compared in both cities",
          str(checked))
    check(identical,
          "tool: renting-senior surge is early 0->0 at every"
          " tier and position, nets +1,080 at every tier,"
          " exactly 5,200 below the owning surged net, every"
          " trajectory ends at net, identical in both cities")
    own_flat = econ.simulate(prices, bands["taxi_driver"],
                             "senior")
    own_surged = econ.simulate(
        prices, bands["taxi_driver"], "senior", **weather)
    check(own_surged["net"] - own_flat["net"] == 1080,
          "tool: the delta is the senior single-earner taxi"
          " surge delta",
          str(own_surged["net"] - own_flat["net"]))
    check("taxi-driver (senior, renting)" not in sim_src,
          "tool: no senior renting pairing is wired into the"
          " surge table")

    # 2. The wiring: nothing is printed — the table keeps
    # five pairings, the default-run output is byte-identical
    # to the MN run, and the pinned md5 does NOT move.
    d1 = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py")],
        capture_output=True, cwd=ROOT)
    check(d1.returncode == 0, "tool: default run exits 0")
    d1_text = d1.stdout.decode()
    second = d1_text.split(
        "taxi-driver second earner weather-surge month")[1]
    for pairing in ("taxi-driver (entry, owning)",
                    "taxi-driver (mid, owning)",
                    "taxi-driver (mid, renting)",
                    "taxi-driver (entry, renting)",
                    "taxi-driver (senior, owning)"):
        check(pairing in second,
              "tool: the second-earner table keeps a pairing",
              pairing)
    check(second.count("taxi-driver (senior, owning)") == 3,
          "tool: the second-earner table prints exactly three"
          " senior-owning rows")
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
          "tool: the pinned md5 stands at the MN baseline",
          pinned)
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py"),
         "--shibnagar"],
        capture_output=True, cwd=ROOT)
    check(out.returncode == 0, "tool: --shibnagar run exits 0")
    sh_text = out.stdout.decode()
    sh_md5 = hashlib.md5(out.stdout).hexdigest()
    check(sh_md5 == MN_SH_MD5,
          "tool: --shibnagar md5 stands at the MN baseline",
          sh_md5)
    check("shibnagar BRIDGE FAIL rows: []" in sh_text,
          "tool: no Shibnagar bridge failure")
    check("senior, renting" not in sh_text,
          "tool: no senior renting pairing is printed on"
          " Shibnagar either")
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
    check("construction_worker + taxi-driver (mid, renting)"
          in d1_text,
          "tool: the KA renting bridge line is unchanged")
    check("taxi-driver (senior, renting)" not in d1_text,
          "tool: no senior renting line in either bridge check")

    # 3. The V7 report §35: prose matches the measurement.
    check("## 35. Addendum — Renting senior-tier taxi second"
          " earner in the surge table (Unit MO, Queue 46)"
          in report,
          "report §35: the addendum exists")
    s35 = report.split("## 35.")[1]
    s35_flat = " ".join(s35.split())
    check("DECIDED" in s35 and "stays allowed but unprinted"
          in s35_flat,
          "report §35: the stays-unprinted decision is stated")
    check("18,750" in s35_flat and "19,830" in s35_flat
          and "21,994" in s35_flat and "23,074" in s35_flat
          and "25,451" in s35_flat and "26,531" in s35_flat,
          "report §35: the renting-senior surge figures are"
          " quoted")
    check("+1,080" in s35_flat,
          "report §35: the +1,080 delta is quoted")
    check("5,200" in s35_flat,
          "report §35: the 5,200 gap is quoted")
    check("does NOT move" in s35_flat
          and MN_MD5 in s35 and MN_SH_MD5 in s35,
          "report §35: the md5 standing is recorded")
    check("132 rows" in s35_flat,
          "report §35: the 132-row Shibnagar identity stands")
    check("| senior, renting | entry | 0 | 0 | 18,750 | 19,830 |"
          in s35,
          "report §35: the per-tier table is printed")
    check("Closed 2026-11-26 by Queue 46 Unit MO"
          in report.split("## 34.")[1].split("## 35.")[0],
          "report §34: the open note is closed")
    check("The renting senior row (Unit MO, Queue 46, §35)"
          " was measured" in " ".join(
              report.split("## 16.")[1].split("## 17.")[0]
              .split()),
          "report §16: the Finding gains the renting senior"
          " row")
    check("18,750" in report.split("## 16.")[1]
          .split("## 17.")[0],
          "report §16: the renting-senior surge figures are"
          " quoted in the Finding")

    # 4. GDD-03 §2 records the MO update.
    check("Unit MO · Queue 46" in gdd03,
          "GDD-03 §2: the MO update is recorded")
    check("18,750" in gdd03 and "26,531" in gdd03,
          "GDD-03 §2: the renting-senior surge figures are"
          " quoted")
    check("does NOT move" in gdd03,
          "GDD-03 §2: the md5 standing is recorded")

    # 5. The economy_sim.py comments record the MO outcome.
    check("Queue 46 Unit MO" in sim_src,
          "tool: the comments name the MO decision")
    check("report §35" in sim_src,
          "tool: the comments record §35")
    check("unprinted (V7 §33) — not queued" not in sim_src,
          "tool: the stale MN-era 'not queued' note is gone")

    # 6. Tests pin the MO figures and the standing decision.
    check("test_senior_renting_second_earner_surge_is_measured"
          in regress,
          "tests: the renting-senior surge figures test exists")
    check("test_second_earner_surge_table_has_five_pairings"
          in regress,
          "tests: the five-pairings test still stands")
    check("test_senior_renting_second_earner_is_not_printed"
          in regress,
          "tests: the not-printed test still stands")
    check("not queued" not in regress,
          "tests: the stale 'not queued' note is gone")
    check("18750, 19830" in regress
          and "21994, 23074" in regress
          and "25451, 26531" in regress,
          "tests: the renting-senior surge figures are pinned")
    check("132" in regress and "21)" in regress,
          "tests: the 132-row identity and 21-row table"
          " counts still stand")

    # 7. Scope: only the MO files changed for this unit.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 46 MO:",
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
                    "tools/verify_queue46_mo.py"},
          "scope: only the five MO files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
