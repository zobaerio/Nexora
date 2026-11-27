"""Verify Queue 54 Unit MW — Taxi Surge at the Smallest
Factor, 1.0083: live-settled at all three tiers, by
weather-first hunt (MV follow-up).

Checks the corroboration against its sources:
tools/sim/engine.py (the settlement scales a taxi driver's
gross by taxi_factor = 1 + 0.25 x rain_days/30 + 0.5 x
storm_days/30, rounded to an integer, in the SYS-EMPLOYERS
branch only), tools/economy_sim.py (a comment only — the
tool's formula already reproduces the settled grosses, so
no tool change and the pinned md5 does NOT move),
tools/sim/tests/test_no_regression.py (a new test pins the
1.0083 factor, the per-tier grosses and nets, the rounding
up at the lower tiers and the no-op at the senior tier,
the per-tier deltas, and the three live senior
settlements),
docs/ECONOMY-SIM-REPORT-V7.md §43 (the prose matches the
measurement, including the per-tier table, the full
two-hundred-seed scan table and the three live senior
settlements) and §16 (the 1.0083 live settlement and its
per-tier deltas are recorded), and
docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the MW update).
Re-runs the weather-only scan over the two hundred fresh
seeds and the three matching months live (seeds mw-probe-15,
mw-probe-124 and mw-probe-150, 60 population, 32 days
each) and asserts the recorded weather counts and settled
taxi grosses. Prints one line per check and a summary;
exits 0 only when every check passes.
Run from the repo root: python3 tools/verify_queue54_mw.py
"""
import hashlib
import os
import re
import subprocess
import sys
import tempfile
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


def _scan():
    """The weather-only pre-filter: the month's weather for
    each of the 200 fresh seeds, read from the seed alone
    (SimRng.stream("weather", day_index) is keyed by the
    seed, not by the population). Returns
    {seed: (rain, storm, rain indices, storm indices)} for
    the seeds matching rain + 2 x storm == 1."""
    from tools.sim.engine import WEATHER_WEIGHTS
    from tools.sim.rng import SimRng
    names = [n for n, _ in WEATHER_WEIGHTS]
    weights = [w for _, w in WEATHER_WEIGHTS]
    matches = {}
    for i in range(1, 201):
        seed = f"mw-probe-{i}"
        rng = SimRng(seed)
        presets = [rng.stream("weather", d).choices(
            names, weights=weights)[0] for d in range(30)]
        rain = presets.count("rain")
        storm = presets.count("storm")
        if rain + 2 * storm == 1:
            matches[seed] = (
                rain, storm,
                [d for d, p in enumerate(presets)
                 if p == "rain"],
                [d for d, p in enumerate(presets)
                 if p == "storm"])
    return matches


def _measure(seed):
    """A fresh seeded live month in the EY shape: returns
    (rain days, storm days, rain day indices, storm day
    indices, {cid: (band, settled amounts, sources,
    employer_business_id)})."""
    from tools.sim.engine import Simulation
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(db_path)
    sim = Simulation(db_path, seed=seed)
    sim.generate_population(60)
    sim.run_days(32)
    store = sim.store
    presets = [sim.weather_for_day(d) for d in range(30)]
    rain = presets.count("rain")
    storm = presets.count("storm")
    rain_idx = [d for d, p in enumerate(presets) if p == "rain"]
    storm_idx = [d for d, p in enumerate(presets) if p == "storm"]
    drivers = {}
    for e in store.rows(
            "SELECT character_id, wage_per_month,"
            " employer_business_id FROM employments"
            " WHERE profession_id = 'taxi_driver'"
            " AND ended_at_game_minutes IS NULL"):
        cid = e["character_id"]
        settled = store.rows(
            "SELECT amount, from_character_id FROM economy_ledger"
            " WHERE to_character_id = ? AND reason_code = 'wage'"
            " AND game_minutes = 43200", (cid,))
        drivers[cid] = (e["wage_per_month"],
                        [r["amount"] for r in settled],
                        [r["from_character_id"] for r in settled],
                        e["employer_business_id"])
    sim.close()
    os.remove(db_path)
    return rain, storm, rain_idx, storm_idx, drivers


def main():
    from tools import economy_sim as econ
    sim_src = (ROOT / "tools" / "economy_sim.py").read_text()
    regress = (ROOT / "tools" / "sim" / "tests"
               / "test_no_regression.py").read_text()
    report = (ROOT / "docs" / "ECONOMY-SIM-REPORT-V7.md").read_text()
    gdd03 = (ROOT / "docs" / "GDD-03-ECONOMY-AND-PROFESSIONS.md").read_text()
    engine_src = (ROOT / "tools" / "sim" / "engine.py").read_text()

    # 1. The settlement's rule, read from the source: the
    # factor is defined once and applied once, rounded, in
    # the SYS-EMPLOYERS branch of _settle_month.
    check("taxi_factor = 1 + 0.25 * rain_days / 30 + 0.5"
          " * storm_days / 30" in engine_src,
          "source: the factor formula is the settlement's own")
    check("gross = round(gross * taxi_factor)" in engine_src,
          "source: the settlement rounds the surged gross")

    # 2. The tool's figures at the new factor: the gross is
    # round(band x factor), the nets follow with tax and
    # uplift recomputed, the trajectory ends at net.
    check(abs(econ.taxi_weather_factor(1, 0)
              - 1.0083333333333333) < 1e-12,
          "tool: the 1/0 factor is 1.0083",
          str(econ.taxi_weather_factor(1, 0)))
    prices = econ.load("prices.json")
    wages = {w["profession_id"]: w
             for w in prices["wages_monthly"]}
    for tier, gross, net, delta in (("entry", 14117, 6576, 117),
                                    ("mid", 23192, 12065, 192),
                                    ("senior", 36300, 19930, 300)):
        flat = econ.simulate(prices, wages["taxi_driver"],
                             tier)
        surged = econ.simulate(
            prices, wages["taxi_driver"], tier,
            taxi_rain_days=1, taxi_storm_days=0)
        check(surged["gross"] == gross,
              f"tool: 1/0 {tier} gross is {gross}",
              str(surged["gross"]))
        check(surged["net"] == net,
              f"tool: 1/0 {tier} net is {net}",
              str(surged["net"]))
        check(surged["gross"] - flat["gross"] == delta,
              f"tool: 1/0 {tier} delta is {delta}",
              str(surged["gross"] - flat["gross"]))
        check(surged["end_balance"] == surged["net"],
              f"tool: 1/0 {tier} ends at net",
              str(surged["end_balance"]))
        check(surged["min_balance"] == 0,
              f"tool: 1/0 {tier} minbal is 0",
              str(surged["min_balance"]))
    # The rounding at 1.0083 goes up at both lower tiers
    # (14,116.67 -> 14,117; 23,191.67 -> 23,192) and is a
    # no-op at the senior tier (exactly 36,300.0).
    for band, gross in ((14000, 14117), (23000, 23192)):
        product = band * econ.taxi_weather_factor(1, 0)
        check(product > gross - 1 and product < gross
              and round(product) == gross,
              f"tool: {band:,} x 1.0083 rounds up to"
              f" {gross:,}",
              str(product))
    check(36000 * econ.taxi_weather_factor(1, 0) == 36300.0
          and round(36000 * econ.taxi_weather_factor(1, 0))
          == 36300,
          "tool: 36,000 x 1.0083 is exactly 36,300.0 (no-op)",
          str(36000 * econ.taxi_weather_factor(1, 0)))
    # The senior product is an integer at every factor, up to
    # float error: 36,000 + 300 x rain + 600 x storm —
    # round() always lands on it.
    check(all(abs(36000 * econ.taxi_weather_factor(r, s)
                  - (36000 + 300 * r + 600 * s)) < 1e-9
              and round(36000 * econ.taxi_weather_factor(r, s))
              == 36000 + 300 * r + 600 * s
              for r in range(10) for s in range(6)),
          "tool: the senior product is an integer up to float"
          " error at every factor (36,000 + 300 x rain + 600"
          " x storm)")

    # 3. The default run: the md5 does NOT move (comment
    # only), the KC section still prints the EY weather, and
    # nothing fails; same on --shibnagar.
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
    check(pinned == MN_MD5,
          "tool: the pinned md5 stands at the MN baseline",
          pinned)
    check("taxi weather-surge month (Unit KC — the EY month's "
          "weather: 2 rain days, 2 storm days, taxi_factor"
          " 1.05" in d1_text,
          "tool: the KC section still prints the EY weather")
    check("mw-probe" not in d1_text,
          "tool: the probe seeds are not printed in the output")
    check("BRIDGE FAIL rows: []" in d1_text,
          "tool: no D1 bridge failure")
    check("rows: 36" in d1_text,
          "tool: the base table still has 36 rows")
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

    # 4. The weather-only scan: exactly three of the 200
    # fresh seeds match rain + 2 x storm == 1, with the
    # recorded counts and day indices.
    scanned = _scan()
    expected_scan = {
        "mw-probe-15": (1, 0, [3], []),
        "mw-probe-124": (1, 0, [11], []),
        "mw-probe-150": (1, 0, [9], []),
    }
    check(scanned == expected_scan,
          "scan: exactly the three recorded seeds match rain +"
          " 2 x storm == 1",
          str(sorted(scanned)))
    check(len(scanned) == 3,
          "scan: the hit rate is 3 in 200",
          str(len(scanned)))

    # 5. Live re-derivation of the three matching months.
    for seed, weather, rain_idx, storm_idx, count, bands, settled, seniors in (
            ("mw-probe-15", (1, 0),
             [3], [], 5,
             (14000, 23000, 36000), [14117, 23192, 36300],
             (("NEX000059", 36300),)),
            ("mw-probe-124", (1, 0),
             [11], [], 0,
             (), [], ()),
            ("mw-probe-150", (1, 0),
             [9], [], 4,
             (23000, 36000), [23192, 36300],
             (("NEX000015", 36300), ("NEX000028", 36300)))):
        rain, storm, r_idx, s_idx, drivers = _measure(seed)
        factor = econ.taxi_weather_factor(rain, storm)
        check((rain, storm) == weather,
              f"live {seed}: month 1 has {weather[0]} rain day"
              f" and {weather[1]} storm days",
              f"rain={rain} storm={storm}")
        check((rain, storm) == scanned[seed][:2],
              f"live {seed}: the full run reproduces the"
              " scanned counts",
              f"rain={rain} storm={storm}")
        check(r_idx == rain_idx,
              f"live {seed}: the rain day indices match",
              str(r_idx))
        check(s_idx == storm_idx,
              f"live {seed}: the storm day indices match",
              str(s_idx))
        check(len(drivers) == count,
              f"live {seed}: the month holds {count} taxi"
              " drivers",
              str(len(drivers)))
        check(all(d[3] is None for d in drivers.values()),
              f"live {seed}: every taxi driver is"
              " SYS-EMPLOYERS-paid (no business employer)",
              str({k: v[3] for k, v in drivers.items()}))
        check(all(d[2] == ["SYS-EMPLOYERS"]
                  for d in drivers.values()),
              f"live {seed}: every settled wage comes from"
              " SYS-EMPLOYERS")
        check(all(d[0] in bands for d in drivers.values())
              and sorted({d[0] for d in drivers.values()})
              == sorted(bands),
              f"live {seed}: the driver bands are {bands}",
              str(sorted({d[0] for d in drivers.values()})))
        ok = all(len(d[1]) == 1
                 and d[1][0] == round(d[0] * factor)
                 for d in drivers.values())
        check(ok,
              f"live {seed}: every taxi driver settled at"
              " exactly round(band x factor)",
              str({k: (v[0], v[1]) for k, v in drivers.items()}))
        check(sorted({d[1][0] for d in drivers.values()})
              == settled,
              f"live {seed}: the settled grosses are"
              f" {settled}",
              str(sorted({d[1][0]
                          for d in drivers.values()})))
        tool_ok = all(
            econ.simulate(prices, wages["taxi_driver"],
                          {14000: "entry", 23000: "mid",
                           36000: "senior"}[d[0]],
                          taxi_rain_days=rain,
                          taxi_storm_days=storm)["gross"]
            == d[1][0]
            for d in drivers.values())
        check(tool_ok,
              f"live {seed}: the tool's gross equals every"
              " settled gross",
              str({k: (v[0], v[1]) for k, v in drivers.items()}))
        if not seniors:
            check(all(d[0] != 36000 for d in drivers.values())
                  and len(drivers) == 0,
                  f"live {seed}: no taxi driver in this month",
                  str(sorted({d[0] for d in drivers.values()})))
        else:
            for cid, gross in seniors:
                senior_ok = (drivers.get(cid, (None, [], [], None))[0]
                             == 36000
                             and drivers.get(cid, (None, [], [], None))[1]
                             == [gross])
                check(senior_ok,
                      f"live {seed}: the senior driver is"
                      f" {cid}, settled {gross:,}",
                      str({c: drivers.get(c) for c in (cid,)}))
    check(f"{econ.taxi_weather_factor(1, 0):.4f}" == "1.0083",
          "live: the mw-probe-15 month is factor 1.0083 to"
          " four places")

    # 6. The V7 report §43: prose matches the measurement.
    check("## 43. Addendum — Taxi surge at the smallest"
          " factor, 1.0083: live-settled at all three tiers,"
          " by weather-first hunt (Unit MW, Queue 54)"
          in report,
          "report §43: the addendum exists")
    s43 = report.split("## 43.")[1]
    s43_flat = " ".join(s43.split())
    check("mw-probe-15" in s43 and "mw-probe-124" in s43
          and "mw-probe-150" in s43,
          "report §43: all three probe seeds are named")
    check("1.0083" in s43,
          "report §43: the new factor is quoted")
    check("14,117" in s43 and "23,192" in s43
          and "36,300" in s43,
          "report §43: all three surged grosses are quoted")
    check("14,116.666666666666" in s43
          and "23,191.666666666664" in s43
          and "36,300.0" in s43,
          "report §43: the rounding cases are quoted")
    check("NEX000059" in s43 and "NEX000015" in s43
          and "NEX000028" in s43,
          "report §43: all three senior drivers are named")
    check("does NOT move" in s43_flat
          and MN_MD5 in s43 and MN_SH_MD5 in s43,
          "report §43: the md5 standing is recorded")
    check("| 1.0083 | senior | 36,300 | 19,930 | +300 |"
          " +180 |" in s43,
          "report §43: the per-factor table is printed")
    check("1.5% hit rate" in s43_flat,
          "report §43: the scan hit rate is recorded")
    check("mw-probe-1" in s43 and "mw-probe-200" in s43,
          "report §43: the full scan range is recorded")
    check("rain + 2 × storm = 1" in s43_flat,
          "report §43: the pre-filter signature is recorded")
    check("eight live factors" in s43_flat,
          "report §43: the surge now rests on eight live"
          " factors")
    check("1.0750" in s43_flat and "no month in the record"
          " holds a senior" in s43_flat,
          "report §43: the 1.0750 senior gap is recorded")
    check("Queue 55 Unit MX" in s43,
          "report §43: the open 1.1250 hunt is recorded")
    check("Unit MW, Queue 54, §43" in report.split("## 16.")[1]
          .split("## 17.")[0],
          "report §16: the MW update is recorded")
    check("+117 / +192 / +300" in report.split(
        "## 16.")[1].split("## 17.")[0],
        "report §16: the 1.0083 per-tier deltas are quoted")

    # 7. GDD-03 §2 records the MW update.
    check("Unit MW · Queue 54" in gdd03,
          "GDD-03 §2: the MW update is recorded")
    check("1.0083" in gdd03,
          "GDD-03 §2: the new factor is quoted")
    check("does NOT move" in gdd03,
          "GDD-03 §2: the md5 standing is recorded")

    # 8. The economy_sim.py comments record the MW outcome.
    check("Queue 54 Unit MW" in sim_src,
          "tool: the comments name the MW decision")
    check("report §43" in sim_src,
          "tool: the comments record §43")
    check("mw-probe-15" in sim_src and "mw-probe-150" in sim_src,
          "tool: the comments name both 1.0083 probe seeds")

    # 9. Tests pin the MW figures.
    check("test_taxi_surge_settled_live_at_10083"
          in regress,
          "tests: the settled-live-at-1.0083 test exists")
    check("14117, 6576" in regress and "23192, 12065" in regress
          and "36300, 19930" in regress,
          "tests: the new-factor grosses and nets are pinned")
    check("117, 192, 300" in regress,
          "tests: the per-tier deltas are pinned")
    check("36300.0" in regress,
          "tests: the exact senior product is pinned")

    # 10. Scope: only the MW files changed for this unit.
    # The grep matches the unit commit only: the queue-tick
    # commit shares the "Queue 54 MW:" prefix but carries
    # bookkeeping (STATUS.md + WORK-QUEUE.md), not unit files.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H",
         "--grep=^Queue 54 MW: taxi surge at the smallest factor, 1.0083",
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
                    "tools/verify_queue54_mw.py"},
          "scope: only the five MW files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
