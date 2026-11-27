"""Verify Queue 56 Unit MY — Senior Taxi Settlement at
1.1250, Weather-First: the hunt finds no senior; the mid
tier settles live (MX follow-up).

Checks the corroboration against its sources:
tools/sim/engine.py (the settlement scales a taxi driver's
gross by taxi_factor = 1 + 0.25 x rain_days/30 + 0.5 x
storm_days/30, rounded to an integer, in the SYS-EMPLOYERS
branch only), tools/economy_sim.py (a comment only — the
tool's formula already reproduces the settled grosses, so
no tool change and the pinned md5 does NOT move),
tools/sim/tests/test_no_regression.py (a new test pins the
1.1250 factor from both mixes, the per-tier grosses and
nets, the rounding no-op at every tier, the per-tier
deltas, and the three live mid settlements),
docs/ECONOMY-SIM-REPORT-V7.md §45 (the prose matches the
measurement, including the per-tier table, the full
two-hundred-seed scan table and the three live mid
settlements) and §16 (the 1.1250 mid settlement and its
per-tier deltas are recorded), and
docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the MY update).
Re-runs the weather-only scan over the two hundred fresh
seeds and the two matching months live (seeds my-probe-53
and my-probe-137, 60 population, 32 days each) and asserts
the recorded weather counts and settled taxi grosses.
Prints one line per check and a summary; exits 0 only when
every check passes.
Run from the repo root: python3 tools/verify_queue56_my.py
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
    the seeds matching rain + 2 x storm == 15."""
    from tools.sim.engine import WEATHER_WEIGHTS
    from tools.sim.rng import SimRng
    names = [n for n, _ in WEATHER_WEIGHTS]
    weights = [w for _, w in WEATHER_WEIGHTS]
    matches = {}
    for i in range(1, 201):
        seed = f"my-probe-{i}"
        rng = SimRng(seed)
        presets = [rng.stream("weather", d).choices(
            names, weights=weights)[0] for d in range(30)]
        rain = presets.count("rain")
        storm = presets.count("storm")
        if rain + 2 * storm == 15:
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

    # 2. The tool's figures at the new factor, from both
    # mixes: the gross is round(band x factor), the nets
    # follow with tax and uplift recomputed, the trajectory
    # ends at net.
    check(econ.taxi_weather_factor(11, 2) == 1.125,
          "tool: the 11/2 factor is exactly 1.125",
          str(econ.taxi_weather_factor(11, 2)))
    check(econ.taxi_weather_factor(7, 4) == 1.125,
          "tool: the 7/4 factor is exactly 1.125",
          str(econ.taxi_weather_factor(7, 4)))
    prices = econ.load("prices.json")
    wages = {w["profession_id"]: w
             for w in prices["wages_monthly"]}
    for tier, gross, net, delta in (("entry", 15750, 7601, 1750),
                                    ("mid", 25875, 13675, 2875),
                                    ("senior", 40500, 22425, 4500)):
        flat = econ.simulate(prices, wages["taxi_driver"],
                             tier)
        for rain_days, storm_days in ((11, 2), (7, 4)):
            surged = econ.simulate(
                prices, wages["taxi_driver"], tier,
                taxi_rain_days=rain_days,
                taxi_storm_days=storm_days)
            check(surged["gross"] == gross,
                  f"tool: {rain_days}/{storm_days} {tier}"
                  f" gross is {gross}",
                  str(surged["gross"]))
            check(surged["net"] == net,
                  f"tool: {rain_days}/{storm_days} {tier}"
                  f" net is {net}",
                  str(surged["net"]))
            check(surged["gross"] - flat["gross"] == delta,
                  f"tool: {rain_days}/{storm_days} {tier}"
                  f" delta is {delta}",
                  str(surged["gross"] - flat["gross"]))
            check(surged["end_balance"] == surged["net"],
                  f"tool: {rain_days}/{storm_days} {tier}"
                  " ends at net",
                  str(surged["end_balance"]))
            check(surged["min_balance"] == 0,
                  f"tool: {rain_days}/{storm_days} {tier}"
                  " minbal is 0",
                  str(surged["min_balance"]))
    # The rounding at 1.1250 is a no-op at every tier, from
    # either mix: all three products are exact integers
    # (15,750.0, 25,875.0, 40,500.0).
    for band, gross in ((14000, 15750), (23000, 25875),
                        (36000, 40500)):
        for rain_days, storm_days in ((11, 2), (7, 4)):
            product = band * econ.taxi_weather_factor(
                rain_days, storm_days)
            check(product == float(gross)
                  and round(product) == gross,
                  f"tool: {band:,} x 1.1250 is exactly"
                  f" {gross:,}.0 (no-op) from"
                  f" {rain_days}/{storm_days}",
                  str(product))
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
    check("my-probe" not in d1_text,
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

    # 4. The weather-only scan: exactly two of the 200
    # fresh seeds match rain + 2 x storm == 15, with the
    # recorded counts and day indices.
    scanned = _scan()
    expected_scan = {
        "my-probe-53": (11, 2,
                        [0, 3, 8, 9, 10, 14, 17, 18, 20,
                         23, 24],
                        [26, 27]),
        "my-probe-137": (7, 4, [9, 10, 13, 16, 20, 23, 24],
                         [2, 14, 17, 27]),
    }
    check(scanned == expected_scan,
          "scan: exactly the two recorded seeds match rain +"
          " 2 x storm == 15",
          str(sorted(scanned)))
    check(len(scanned) == 2,
          "scan: the hit rate is 2 in 200",
          str(len(scanned)))

    # 5. Live re-derivation of the two matching months.
    expected_live = {
        "my-probe-53": ((11, 2),
                        [0, 3, 8, 9, 10, 14, 17, 18, 20,
                         23, 24],
                        [26, 27], 2,
                        {"NEX000002", "NEX000051"}),
        "my-probe-137": ((7, 4),
                         [9, 10, 13, 16, 20, 23, 24],
                         [2, 14, 17, 27], 1,
                         {"NEX000035"}),
    }
    for seed, (counts, r_idx, s_idx, n_drivers, cids) in \
            expected_live.items():
        rain, storm, live_r, live_s, drivers = _measure(seed)
        factor = econ.taxi_weather_factor(rain, storm)
        check((rain, storm) == counts,
              f"live {seed}: month 1 has {counts[0]} rain"
              f" days and {counts[1]} storm days",
              f"rain={rain} storm={storm}")
        check((rain, storm) == scanned[seed][:2],
              f"live {seed}: the full run reproduces the"
              " scanned counts",
              f"rain={rain} storm={storm}")
        check(live_r == r_idx,
              f"live {seed}: the rain day indices match",
              str(live_r))
        check(live_s == s_idx,
              f"live {seed}: the storm day indices match",
              str(live_s))
        check(len(drivers) == n_drivers,
              f"live {seed}: the month holds {n_drivers}"
              " taxi driver(s)",
              str(len(drivers)))
        check(all(d[3] is None for d in drivers.values()),
              f"live {seed}: every taxi driver is"
              " SYS-EMPLOYERS-paid (no business employer)",
              str({k: v[3] for k, v in drivers.items()}))
        check(all(d[2] == ["SYS-EMPLOYERS"]
                  for d in drivers.values()),
              f"live {seed}: every settled wage comes from"
              " SYS-EMPLOYERS")
        check(all(d[0] == 23000 for d in drivers.values()),
              f"live {seed}: every driver is mid tier",
              str(sorted({d[0] for d in drivers.values()})))
        check(all(d[0] != 36000 for d in drivers.values()),
              f"live {seed}: no senior driver in this month",
              str(sorted({d[0] for d in drivers.values()})))
        check(all(d[0] != 14000 for d in drivers.values()),
              f"live {seed}: no entry driver in this month",
              str(sorted({d[0] for d in drivers.values()})))
        ok = all(len(d[1]) == 1
                 and d[1][0] == round(d[0] * factor)
                 for d in drivers.values())
        check(ok,
              f"live {seed}: every taxi driver settled at"
              " exactly round(band x factor)",
              str({k: (v[0], v[1])
                   for k, v in drivers.items()}))
        check(sorted({d[1][0] for d in drivers.values()})
              == [25875],
              f"live {seed}: the settled grosses are [25875]",
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
              str({k: (v[0], v[1])
                   for k, v in drivers.items()}))
        for cid in sorted(cids):
            entry_ok = (drivers.get(cid, (None, [], [], None))[0]
                        == 23000
                        and drivers.get(cid, (None, [], [], None))[1]
                        == [25875])
            check(entry_ok,
                  f"live {seed}: the mid driver is {cid},"
                  " settled 25,875",
                  str({c: drivers.get(c) for c in (cid,)}))
    check(f"{econ.taxi_weather_factor(11, 2):.4f}" == "1.1250",
          "live: the my-probe-53 month is factor 1.1250 to"
          " four places")
    check(f"{econ.taxi_weather_factor(7, 4):.4f}" == "1.1250",
          "live: the my-probe-137 month is factor 1.1250 to"
          " four places")

    # 6. The V7 report §45: prose matches the measurement.
    check("## 45. Addendum — Senior taxi settlement at"
          " 1.1250, weather-first: the hunt finds none; the"
          " mid tier settles live (Unit MY, Queue 56)"
          in report,
          "report §45: the addendum exists")
    s45 = report.split("## 45.")[1]
    s45_flat = " ".join(s45.split())
    check("my-probe-53" in s45 and "my-probe-137" in s45,
          "report §45: both probe seeds are named")
    check("1.1250" in s45,
          "report §45: the new factor is quoted")
    check("15,750" in s45 and "25,875" in s45
          and "40,500" in s45,
          "report §45: all three surged grosses are quoted")
    check("15,750.0" in s45 and "25,875.0" in s45
          and "40,500.0" in s45,
          "report §45: the rounding cases are quoted")
    check("NEX000002" in s45 and "NEX000051" in s45
          and "NEX000035" in s45,
          "report §45: all three mid drivers are named")
    check("does NOT move" in s45_flat
          and MN_MD5 in s45 and MN_SH_MD5 in s45,
          "report §45: the md5 standing is recorded")
    check("| 1.1250 | mid | 25,875 | 13,675 | +2,875 |"
          " +1,725 |" in s45,
          "report §45: the per-factor table is printed")
    check("1.0% hit rate" in s45_flat,
          "report §45: the scan hit rate is recorded")
    check("my-probe-1" in s45 and "my-probe-200" in s45,
          "report §45: the full scan range is recorded")
    check("rain + 2 × storm = 15" in s45_flat,
          "report §45: the pre-filter signature is recorded")
    check("nine live factors" in s45_flat,
          "report §45: the surge still rests on nine live"
          " factors")
    check("1.0750" in s45_flat and "no month in the record"
          " holds a senior" in s45_flat,
          "report §45: the 1.0750 senior gap is recorded")
    check("40,500 at 1.1250" in s45_flat
          and "still tool-computed only" in s45_flat,
          "report §45: the 1.1250 senior gap is recorded")
    check("Queue 57 Unit MZ" in s45_flat,
          "report §45: the open wider senior hunt is"
          " recorded")
    check("fifth time" in s45_flat,
          "report §45: the pre-filter is verified a fifth"
          " time")
    check("two different mixes" in s45_flat,
          "report §45: the factor-not-mix finding is"
          " recorded")
    check("| my-probe-53 | 11 | 2 | 1.1250 | mid:"
          " 25,875 × 2 |" in s45,
          "report §45: the my-probe-53 scan row is printed")
    check("| my-probe-137 | 7 | 4 | 1.1250 | mid:"
          " 25,875 |" in s45,
          "report §45: the my-probe-137 scan row is printed")
    check("Unit MY, Queue 56, §45" in report.split("## 16.")[1]
          .split("## 17.")[0],
          "report §16: the MY update is recorded")
    check("+1,750 / +2,875 / +4,500" in report.split(
        "## 16.")[1].split("## 17.")[0],
        "report §16: the 1.1250 per-tier deltas are quoted")

    # 7. GDD-03 §2 records the MY update.
    check("Unit MY · Queue 56" in gdd03,
          "GDD-03 §2: the MY update is recorded")
    check("1.1250" in gdd03,
          "GDD-03 §2: the new factor is quoted")
    check("does NOT move" in gdd03,
          "GDD-03 §2: the md5 standing is recorded")

    # 8. The economy_sim.py comments record the MY outcome.
    check("Queue 56 Unit MY" in sim_src,
          "tool: the comments name the MY decision")
    check("report §45" in sim_src,
          "tool: the comments record §45")
    check("my-probe-53" in sim_src and "my-probe-137" in sim_src,
          "tool: the comments name the 1.1250 probe seeds")

    # 9. Tests pin the MY figures.
    check("test_taxi_surge_mid_settled_live_at_11250"
          in regress,
          "tests: the mid-settled-live-at-1.1250 test exists")
    check("15750, 7601" in regress and "25875, 13675" in regress
          and "40500, 22425" in regress,
          "tests: the new-factor grosses and nets are pinned")
    check("1750, 2875, 4500" in regress,
          "tests: the per-tier deltas are pinned")
    check("40500.0" in regress,
          "tests: the exact senior product is pinned")

    # 10. Scope: only the MY files changed for this unit.
    # The grep matches the unit commit only: the queue-tick
    # commit shares the "Queue 56 MY:" prefix but carries
    # bookkeeping (STATUS.md + WORK-QUEUE.md), not unit files.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H",
         "--grep=^Queue 56 MY: senior taxi settlement at 1.1250",
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
                    "tools/verify_queue56_my.py"},
          "scope: only the five MY files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
