"""Verify Queue 35 Unit MD — Surge Section in the Shibnagar
Variant (MC follow-up).

Checks the wiring against its sources: tools/economy_sim.py
(the KC surge section is now print_taxi_weather_surge(), and
the --shibnagar variant prints its own table after its bridge
check, computed on Shibnagar's own rents — the rows are
identical to District 1, so the D1 figures stand for both
cities), tools/sim/tests/test_no_regression.py (new tests pin
the 108-row identity, the printed variant table, and the
D1 match — the pinned default-run md5 does NOT move: the MC
baseline stands, the MB md5 kept as history),
docs/ECONOMY-SIM-REPORT-V7.md §24 (the prose matches the
tool output, including the per-tier table and the md5 note),
§16 (the variant paragraph) and §23 (the open note is
closed), and docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the
MD update). Re-runs the surged rows on Shibnagar rents live
and asserts the figures.
Prints one line per check and a summary; exits 0 only when
every check passes.
Run from the repo root: python3 tools/verify_queue35_md.py
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
SH_MD5 = "762a2b6395a1c83fc86f2b5f9c1839bc"
SH_MD5_OLD = "2aaf1c4786292fcc405bdc9f5925982b"


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

    # 1. The figures hold: all 108 surged rows identical on
    # Shibnagar rents — 12 single-earner (owning + renting ×
    # 3 tiers × flat/surged) and 96 second-earner (4 pairings
    # × 3 tiers × 4 positions × flat/surged), on minbal, net
    # and end balance.
    prices = econ.load("prices.json")
    rents, _stock = econ.load_shibnagar_rents(prices)
    bands = {w["profession_id"]: w
             for w in prices["wages_monthly"]}
    cab = prices["taxi_fares"]["cab_rental_ncr_per_day"]
    weather = dict(
        taxi_rain_days=econ.TAXI_WEATHER_MEASURED_RAIN_DAYS,
        taxi_storm_days=econ.TAXI_WEATHER_MEASURED_STORM_DAYS)
    positions = (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                 econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS)
    checked = 0
    identical = True
    shib_taxi = rents[econ.SHIBNAGAR_RENT_TIER["taxi_driver"]]
    for kw in ({}, {"extra_daily_cost": cab,
                    "label_suffix": " (renting cab)"}):
        for tier in ("entry", "mid", "senior"):
            for skw in ({}, weather):
                d1 = econ.simulate(prices, bands["taxi_driver"],
                                   tier, **kw, **skw)
                sh = econ.simulate(prices, bands["taxi_driver"],
                                   tier, rent_override=shib_taxi,
                                   **kw, **skw)
                if (d1["min_balance"], d1["net"],
                        d1["end_balance"]) != \
                        (sh["min_balance"], sh["net"],
                         sh["end_balance"]):
                    identical = False
                checked += 1
    shib_cw = rents[econ.SHIBNAGAR_RENT_TIER["construction_worker"]]
    w = bands["construction_worker"]
    for kw in ({"second_earner": "taxi_driver"},
               {"second_earner": "taxi_driver",
                "second_earner_tier": "mid"},
               {"second_earner": "taxi_driver",
                "second_earner_tier": "mid",
                "second_earner_renting_cab": True},
               {"second_earner": "taxi_driver",
                "second_earner_renting_cab": True}):
        for tier in ("entry", "mid", "senior"):
            for pos in positions:
                for skw in ({}, weather):
                    d1 = econ.simulate(prices, w, tier,
                                       storm_days=pos, **kw, **skw)
                    sh = econ.simulate(prices, w, tier,
                                       storm_days=pos,
                                       rent_override=shib_cw,
                                       **kw, **skw)
                    if (d1["min_balance"], d1["net"],
                            d1["end_balance"]) != \
                            (sh["min_balance"], sh["net"],
                             sh["end_balance"]):
                        identical = False
                    checked += 1
    check(checked == 108, "tool: 108 surged rows compared",
          str(checked))
    check(identical,
          "tool: all 108 surged rows identical on Shibnagar"
          " rents (minbal, net, end balance)")
    check("def print_taxi_weather_surge" in sim_src
          and "rent_overrides" in sim_src,
          "tool: the KC section is a function taking rent"
          " overrides")
    check("print_taxi_weather_surge(\n        prices, bands,"
          " variant=True" in sim_src,
          "tool: the variant calls the section with its own"
          " rents")

    # 2. The wiring: the default run is byte-identical (the
    # pinned md5 stays the MC baseline), the --shibnagar run
    # prints its own table after its bridge check, and the
    # variant rows match the District 1 rows.
    d1 = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py")],
        capture_output=True, cwd=ROOT)
    check(d1.returncode == 0, "tool: default run exits 0")
    d1_text = d1.stdout.decode()
    md5 = hashlib.md5(d1.stdout).hexdigest()
    pinned = re.search(
        r'ECONOMY_SIM_BASELINE_MD5 = "([0-9a-f]{32})"',
        regress).group(1)
    check(md5 == pinned,
          "tool: default-run md5 equals the pinned baseline",
          md5)
    check(pinned == MC_MD5,
          "tool: the pinned md5 stays the MC baseline",
          pinned)
    check(MB_MD5 in regress,
          "tests: the MB md5 is kept as history")
    check("Queue 35 (Unit MD, 2026-11-25) wires the surge table"
          in regress,
          "tests: the pin comment records that MD does not"
          " move the baseline")
    check("BRIDGE FAIL rows: []" in d1_text,
          "tool: no D1 bridge failure")
    sh = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py"),
         "--shibnagar"],
        capture_output=True, cwd=ROOT)
    check(sh.returncode == 0, "tool: --shibnagar run exits 0")
    sh_text = sh.stdout.decode()
    sh_md5 = hashlib.md5(sh.stdout).hexdigest()
    sh2 = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py"),
         "--shibnagar"],
        capture_output=True, cwd=ROOT)
    check(hashlib.md5(sh2.stdout).hexdigest() == sh_md5,
          "tool: two --shibnagar runs are byte-identical",
          sh_md5)
    check(sh_md5 == SH_MD5,
          "tool: --shibnagar md5 matches the §24 record",
          sh_md5)
    check("shibnagar BRIDGE FAIL rows: []" in sh_text,
          "tool: no Shibnagar bridge failure")
    check("taxi weather-surge month (Unit KC" in sh_text,
          "tool: the --shibnagar run still prints the D1"
          " surge section first")
    check("shibnagar taxi weather-surge month (Unit MD"
          in sh_text,
          "tool: the variant prints its own surge table")
    section = sh_text.split(
        "shibnagar taxi weather-surge month")[1].split(
        "district 1 vs shibnagar")[0]
    for row in ("taxi_driver (renting cab)    senior       36000"
                "   37800    14550      15630     +1080",
                "taxi-driver (entry, renting) senior        -419"
                "         -389    12201      12656"):
        check(row in section,
              "tool: the variant table prints a surged row",
              row.split()[3])
    for pairing in ("taxi-driver (entry, owning)",
                    "taxi-driver (mid, owning)",
                    "taxi-driver (mid, renting)",
                    "taxi-driver (entry, renting)"):
        check(pairing in section,
              "tool: the variant table keeps a pairing",
              pairing)
    check("senior, renting" not in section,
          "tool: no senior renting pairing is printed")
    check(section.count("(renting cab)") == 3,
          "tool: the variant table prints three renting rows")
    d1_rows = [ln for ln in d1_text.split(
        "taxi weather-surge month (Unit KC")[1].splitlines()
        if (ln.startswith("taxi_driver")
            or ln.startswith("taxi-driver"))
        and "weather-surge month" not in ln]
    sh_rows = [ln for ln in section.splitlines()
               if (ln.startswith("taxi_driver")
                   or ln.startswith("taxi-driver"))
               and "weather-surge month" not in ln]
    check(len(d1_rows) == 18 and sh_rows == d1_rows,
          "tool: the variant table's 18 rows match District 1",
          f"{len(sh_rows)} rows")

    # 3. The V7 report §24: prose matches the tool output.
    check("## 24. Addendum — Surge section in the Shibnagar"
          " variant (Unit MD, Queue 35)" in report,
          "report §24: the addendum exists")
    s24 = report.split("## 24.")[1]
    check("108" in s24 and "−419" in s24 and "12,656" in s24,
          "report §24: the measured figures are quoted")
    check("does NOT move" in s24 and MC_MD5 in s24,
          "report §24: the md5 note is recorded")
    check(SH_MD5 in s24 and SH_MD5_OLD in s24,
          "report §24: the --shibnagar md5 move is recorded")
    check("Queue 36 Unit ME" in s24,
          "report §24: the open note names Queue 36")
    check("shibnagar taxi weather-surge month (Unit MD"
          in s24,
          "report §24: the verbatim output gains the variant"
          " table")
    check("taxi-driver (entry, renting) senior        -419"
          "         -389    12201      12656" in s24,
          "report §24: the verbatim rows match the tool")
    check("The Shibnagar variant now prints its own surge table"
          " (Unit\nMD" in report.split("## 16.")[1].split("## 17.")[0],
          "report §16: the variant paragraph is added")
    check("Closed 2026-11-25 by\nQueue 35 Unit MD"
          in report.split("## 23.")[1].split("## 24.")[0],
          "report §23: the surge-section open note is closed")

    # 4. GDD-03 §2 records the MD update.
    check("Unit MD · Queue 35" in gdd03,
          "GDD-03 §2: the MD update is recorded")
    check("108" in gdd03 and "12,656" in gdd03,
          "GDD-03 §2: the measured figures are quoted")
    check(MC_MD5 in gdd03,
          "GDD-03 §2: the md5 note is recorded")

    # 5. Tests pin the MD rows and the wiring.
    for name in ("test_surged_rows_are_identical_on_shibnagar"
                 "_rents",
                 "test_shibnagar_variant_prints_own_surge_table",
                 "test_shibnagar_surge_table_matches_district1"):
        check(name in regress,
              "tests: the MD test exists", name)

    # 6. Scope: only the MD files changed for this unit.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 35 MD:",
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
                    "tools/verify_queue35_md.py"},
          "scope: only the five MD files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
