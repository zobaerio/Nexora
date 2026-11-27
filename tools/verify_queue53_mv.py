"""Verify Queue 53 Unit MV — Senior Taxi Settlement at 1.1167,
Weather-First: live-settled, twice (MU follow-up).

Checks the corroboration against its sources:
tools/sim/engine.py (the settlement scales a taxi driver's
gross by taxi_factor = 1 + 0.25 x rain_days/30 + 0.5 x
storm_days/30, rounded to an integer, in the SYS-EMPLOYERS
branch only), tools/economy_sim.py (a comment only — the
tool's formula already reproduces the settled grosses, so
no tool change and the pinned md5 does NOT move),
tools/sim/tests/test_no_regression.py (a new test pins the
1.1167 factor from all three mixes, the per-tier grosses and
nets, the rounding down at the lower tiers and the no-op at
the senior tier, the per-tier deltas, and the two live
senior settlements),
docs/ECONOMY-SIM-REPORT-V7.md §42 (the prose matches the
measurement, including the per-tier table, the full
two-hundred-seed scan table and the two live senior
settlements) and §16 (the 1.1167 live settlement and its
per-tier deltas are recorded), and
docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the MV update).
Re-runs the weather-only scan over the two hundred fresh
seeds and the five matching months live (seeds mv-probe-3,
mv-probe-38, mv-probe-105, mv-probe-106 and mv-probe-115,
60 population, 32 days each) and asserts the recorded
weather counts and settled taxi grosses. Prints one line
per check and a summary; exits 0 only when every check
passes.
Run from the repo root: python3 tools/verify_queue53_mv.py
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
    the seeds matching rain + 2 x storm == 14."""
    from tools.sim.engine import WEATHER_WEIGHTS
    from tools.sim.rng import SimRng
    names = [n for n, _ in WEATHER_WEIGHTS]
    weights = [w for _, w in WEATHER_WEIGHTS]
    matches = {}
    for i in range(1, 201):
        seed = f"mv-probe-{i}"
        rng = SimRng(seed)
        presets = [rng.stream("weather", d).choices(
            names, weights=weights)[0] for d in range(30)]
        rain = presets.count("rain")
        storm = presets.count("storm")
        if rain + 2 * storm == 14:
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
    for rain, storm in ((8, 3), (4, 5), (6, 4)):
        check(abs(econ.taxi_weather_factor(rain, storm)
                  - 1.1166666666666667) < 1e-12,
              f"tool: the {rain}/{storm} factor is 1.1167",
              str(econ.taxi_weather_factor(rain, storm)))
    prices = econ.load("prices.json")
    wages = {w["profession_id"]: w
             for w in prices["wages_monthly"]}
    for tier, gross, net, delta in (("entry", 15633, 7529, 1633),
                                    ("mid", 25683, 13560, 2683),
                                    ("senior", 40200, 22260, 4200)):
        flat = econ.simulate(prices, wages["taxi_driver"],
                             tier)
        surged = econ.simulate(
            prices, wages["taxi_driver"], tier,
            taxi_rain_days=8, taxi_storm_days=3)
        check(surged["gross"] == gross,
              f"tool: 8/3 {tier} gross is {gross}",
              str(surged["gross"]))
        check(surged["net"] == net,
              f"tool: 8/3 {tier} net is {net}",
              str(surged["net"]))
        check(surged["gross"] - flat["gross"] == delta,
              f"tool: 8/3 {tier} delta is {delta}",
              str(surged["gross"] - flat["gross"]))
        check(surged["end_balance"] == surged["net"],
              f"tool: 8/3 {tier} ends at net",
              str(surged["end_balance"]))
        check(surged["min_balance"] == 0,
              f"tool: 8/3 {tier} minbal is 0",
              str(surged["min_balance"]))
    # The same factor from the other two mixes settles
    # identically — the settlement keys on the factor.
    check(all(econ.simulate(
        prices, wages["taxi_driver"], tier,
        taxi_rain_days=r, taxi_storm_days=s)["gross"]
        == econ.simulate(
            prices, wages["taxi_driver"], tier,
            taxi_rain_days=8, taxi_storm_days=3)["gross"]
        for tier in ("entry", "mid", "senior")
        for r, s in ((4, 5), (6, 4))),
        "tool: 4/5 and 6/4 grosses equal the 8/3 grosses at"
        " every tier")
    # The rounding at 1.1167 goes down at both lower tiers
    # (15,633.33 -> 15,633; 25,683.33 -> 25,683) and is a
    # no-op at the senior tier (exactly 40,200.0).
    for band, gross in ((14000, 15633), (23000, 25683)):
        product = band * econ.taxi_weather_factor(8, 3)
        check(product > gross and product < gross + 1
              and round(product) == gross,
              f"tool: {band:,} x 1.1167 rounds down to"
              f" {gross:,}",
              str(product))
    check(36000 * econ.taxi_weather_factor(8, 3) == 40200.0
          and round(36000 * econ.taxi_weather_factor(8, 3))
          == 40200,
          "tool: 36,000 x 1.1167 is exactly 40,200.0 (no-op)",
          str(36000 * econ.taxi_weather_factor(8, 3)))
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
    check("mv-probe" not in d1_text,
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

    # 4. The weather-only scan: exactly five of the 200
    # fresh seeds match rain + 2 x storm == 14, with the
    # recorded counts and day indices.
    scanned = _scan()
    expected_scan = {
        "mv-probe-3": (6, 4, [2, 4, 9, 12, 27, 28],
                       [14, 19, 20, 24]),
        "mv-probe-38": (4, 5, [4, 20, 21, 29],
                        [0, 3, 9, 11, 22]),
        "mv-probe-105": (8, 3, [0, 3, 8, 9, 12, 13, 17, 21],
                         [2, 19, 28]),
        "mv-probe-106": (6, 4, [9, 19, 23, 25, 26, 28],
                         [2, 7, 22, 29]),
        "mv-probe-115": (4, 5, [5, 9, 14, 18],
                         [6, 10, 13, 15, 25]),
    }
    check(scanned == expected_scan,
          "scan: exactly the five recorded seeds match rain +"
          " 2 x storm == 14",
          str(sorted(scanned)))
    check(len(scanned) == 5,
          "scan: the hit rate is 5 in 200",
          str(len(scanned)))

    # 5. Live re-derivation of the five matching months.
    for seed, weather, rain_idx, storm_idx, count, bands, settled, senior in (
            ("mv-probe-3", (6, 4),
             [2, 4, 9, 12, 27, 28], [14, 19, 20, 24], 3,
             (14000, 23000), [15633, 25683], None),
            ("mv-probe-38", (4, 5),
             [4, 20, 21, 29], [0, 3, 9, 11, 22], 2,
             (23000,), [25683], None),
            ("mv-probe-105", (8, 3),
             [0, 3, 8, 9, 12, 13, 17, 21], [2, 19, 28], 5,
             (14000, 23000, 36000), [15633, 25683, 40200],
             ("NEX000014", 40200)),
            ("mv-probe-106", (6, 4),
             [9, 19, 23, 25, 26, 28], [2, 7, 22, 29], 2,
             (14000,), [15633], None),
            ("mv-probe-115", (4, 5),
             [5, 9, 14, 18], [6, 10, 13, 15, 25], 3,
             (23000, 36000), [25683, 40200],
             ("NEX000053", 40200))):
        rain, storm, r_idx, s_idx, drivers = _measure(seed)
        factor = econ.taxi_weather_factor(rain, storm)
        check((rain, storm) == weather,
              f"live {seed}: month 1 has {weather[0]} rain days"
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
        if senior is None:
            check(all(d[0] != 36000 for d in drivers.values()),
                  f"live {seed}: no senior taxi driver in this"
                  " month",
                  str(sorted({d[0] for d in drivers.values()})))
        else:
            senior_ok = (drivers.get(senior[0], (None, [], [], None))[0]
                         == 36000
                         and drivers.get(senior[0], (None, [], [], None))[1]
                         == [senior[1]])
            check(senior_ok,
                  f"live {seed}: the senior driver is"
                  f" {senior[0]}, settled {senior[1]:,}",
                  str({cid: drivers.get(cid) for cid in
                       (senior[0],)}))
    check(f"{econ.taxi_weather_factor(8, 3):.4f}" == "1.1167",
          "live: the mv-probe-105 month is factor 1.1167 to"
          " four places")

    # 6. The V7 report §42: prose matches the measurement.
    check("## 42. Addendum — Senior taxi settlement at 1.1167:"
          " live-settled, twice, by weather-first hunt"
          " (Unit MV, Queue 53)" in report,
          "report §42: the addendum exists")
    s42 = report.split("## 42.")[1]
    s42_flat = " ".join(s42.split())
    check("mv-probe-3" in s42 and "mv-probe-38" in s42
          and "mv-probe-105" in s42 and "mv-probe-106" in s42
          and "mv-probe-115" in s42,
          "report §42: all five probe seeds are named")
    check("1.1167" in s42,
          "report §42: the new factor is quoted")
    check("15,633" in s42 and "25,683" in s42
          and "40,200" in s42,
          "report §42: all three surged grosses are quoted")
    check("15,633.333333333334" in s42
          and "25,683.333333333336" in s42
          and "40,200.0" in s42,
          "report §42: the rounding cases are quoted")
    check("NEX000014" in s42 and "NEX000053" in s42,
          "report §42: both senior drivers are named")
    check("does NOT move" in s42_flat
          and MN_MD5 in s42 and MN_SH_MD5 in s42,
          "report §42: the md5 standing is recorded")
    check("| 1.1167 | senior | 40,200 | 22,260 | +4,200 |"
          " +2,510 |" in s42,
          "report §42: the per-factor table is printed")
    check("2.5% hit rate" in s42_flat,
          "report §42: the scan hit rate is recorded")
    check("mv-probe-1" in s42 and "mv-probe-200" in s42,
          "report §42: the full scan range is recorded")
    check("rain + 2 × storm = 14" in s42_flat,
          "report §42: the pre-filter signature is recorded")
    check("four live factors" in s42_flat,
          "report §42: the senior tier now rests on four"
          " live factors")
    check("1.0083" in s42_flat and "Queue 54 Unit MW" in s42,
          "report §42: the open 1.0083 hunt is recorded")
    check("Unit MV, Queue 53, §42" in report.split("## 16.")[1]
          .split("## 17.")[0],
          "report §16: the MV update is recorded")
    check("+1,633 / +2,683 / +4,200" in report.split(
        "## 16.")[1].split("## 17.")[0],
        "report §16: the 1.1167 per-tier deltas are quoted")

    # 7. GDD-03 §2 records the MV update.
    check("Unit MV · Queue 53" in gdd03,
          "GDD-03 §2: the MV update is recorded")
    check("1.1167" in gdd03,
          "GDD-03 §2: the new factor is quoted")
    check("does NOT move" in gdd03,
          "GDD-03 §2: the md5 standing is recorded")

    # 8. The economy_sim.py comments record the MV outcome.
    check("Queue 53 Unit MV" in sim_src,
          "tool: the comments name the MV decision")
    check("report §42" in sim_src,
          "tool: the comments record §42")
    check("mv-probe-105" in sim_src and "mv-probe-115" in sim_src,
          "tool: the comments name both 1.1167 probe seeds")

    # 9. Tests pin the MV figures.
    check("test_taxi_surge_senior_settled_live_at_11167"
          in regress,
          "tests: the senior-live-at-1.1167 test exists")
    check("15633, 7529" in regress and "25683, 13560" in regress
          and "40200, 22260" in regress,
          "tests: the new-factor grosses and nets are pinned")
    check("1633, 2683, 4200" in regress,
          "tests: the per-tier deltas are pinned")
    check("40200.0" in regress,
          "tests: the exact senior product is pinned")

    # 10. Scope: only the MV files changed for this unit.
    # The grep matches the unit commit only: the queue-tick
    # commit shares the "Queue 53 MV:" prefix but carries
    # bookkeeping (STATUS.md + WORK-QUEUE.md), not unit files.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H",
         "--grep=^Queue 53 MV: senior taxi settlement at 1.1167",
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
                    "tools/verify_queue53_mv.py"},
          "scope: only the five MV files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
