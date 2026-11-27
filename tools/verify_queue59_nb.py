"""Verify Queue 59 Unit NB — Senior Taxi Settlement at
1.0750, Weather-First: the senior was already live; the
hunt finds two more, and the record is corrected (NA
follow-up).

Checks the corroboration against its sources:
tools/sim/engine.py (the settlement scales a taxi driver's
gross by taxi_factor = 1 + 0.25 x rain_days/30 + 0.5 x
storm_days/30, rounded to an integer, in the SYS-EMPLOYERS
branch only), tools/economy_sim.py (a comment only — the
tool's formula already reproduces the settled grosses, so
no tool change and the pinned md5 does NOT move),
tools/sim/tests/test_no_regression.py (a new test pins the
1.0750 factor from the NB mixes, the per-tier grosses and
nets, the rounding no-op at every tier, the per-tier
deltas, the two live senior settlements, and the record
correction),
docs/ECONOMY-SIM-REPORT-V7.md §48 (the prose matches the
measurement, including the per-tier table, the full
twenty-four-seed scan table, the nine live settlements,
and the correction of the 1.0750 senior gap) and §16 (the
1.0750 update is recorded), and
docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the NB update).
Re-runs the weather-only scan over the twenty-four fresh
seeds and every matching month live (nine seeds, 60
population, 32 days each) and asserts the recorded
weather counts and settled taxi grosses — and re-derives
the five prior 1.0750 months live (ms-probe-8,
mt-probe-10, mt-probe-22, mu-probe-2, mu-probe-14) to
prove the correction: the senior at 1.0750 was already
live before NB.
Prints one line per check and a summary; exits 0 only when
every check passes.
Run from the repo root: python3 tools/verify_queue59_nb.py
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

# The nine matching months, in scan order: seed ->
# ((rain, storm), rain day indices, storm day indices,
#  {character id: (wage band, settled gross)}).
EXPECTED_LIVE = {
    "nb-probe-2": ((7, 1),
                   [5, 11, 17, 21, 24, 25, 29],
                   [26],
                   {"NEX000007": (36000, 38700),
                    "NEX000019": (14000, 15050),
                    "NEX000056": (14000, 15050)}),
    "nb-probe-4": ((7, 1),
                   [8, 10, 12, 13, 19, 20, 23],
                   [0],
                   {"NEX000028": (23000, 24725),
                    "NEX000037": (23000, 24725),
                    "NEX000049": (23000, 24725)}),
    "nb-probe-5": ((5, 2),
                   [1, 4, 8, 15, 24],
                   [5, 23],
                   {"NEX000008": (23000, 24725),
                    "NEX000010": (23000, 24725),
                    "NEX000033": (14000, 15050)}),
    "nb-probe-6": ((5, 2),
                   [0, 17, 19, 23, 28],
                   [3, 4],
                   {"NEX000018": (14000, 15050)}),
    "nb-probe-7": ((5, 2),
                   [0, 11, 12, 23, 28],
                   [4, 6],
                   {"NEX000020": (23000, 24725),
                    "NEX000037": (23000, 24725),
                    "NEX000045": (23000, 24725),
                    "NEX000049": (14000, 15050)}),
    "nb-probe-10": ((5, 2),
                    [11, 18, 19, 25, 29],
                    [7, 16],
                    {"NEX000027": (23000, 24725),
                     "NEX000031": (14000, 15050)}),
    "nb-probe-11": ((7, 1),
                    [1, 4, 10, 11, 20, 24, 28],
                    [15],
                    {"NEX000009": (23000, 24725),
                     "NEX000039": (23000, 24725),
                     "NEX000045": (23000, 24725)}),
    "nb-probe-15": ((7, 1),
                    [0, 5, 8, 12, 13, 20, 22],
                    [4],
                    {"NEX000001": (23000, 24725),
                     "NEX000026": (23000, 24725),
                     "NEX000036": (14000, 15050),
                     "NEX000048": (36000, 38700),
                     "NEX000056": (23000, 24725)}),
    "nb-probe-23": ((9, 0),
                    [0, 4, 5, 7, 14, 21, 22, 25, 26],
                    [],
                    {"NEX000027": (23000, 24725),
                     "NEX000033": (23000, 24725),
                     "NEX000037": (23000, 24725)}),
}

# The five prior 1.0750 months in the record: seed ->
# ((rain, storm), {character id: (wage band, settled
# gross)}). The §39/§41 tables record these rows; the
# MS/MU verify scripts never re-derived them, so NB
# re-derives them live here.
PRIOR_10750 = {
    "ms-probe-8": ((7, 1),
                   {"NEX000034": (36000, 38700)}),
    "mt-probe-10": ((3, 3),
                    {"NEX000005": (23000, 24725),
                     "NEX000015": (23000, 24725),
                     "NEX000029": (23000, 24725),
                     "NEX000034": (23000, 24725)}),
    "mt-probe-22": ((7, 1),
                    {"NEX000001": (23000, 24725)}),
    "mu-probe-2": ((3, 3),
                   {"NEX000018": (14000, 15050),
                    "NEX000043": (14000, 15050),
                    "NEX000058": (23000, 24725)}),
    "mu-probe-14": ((5, 2),
                    {"NEX000007": (36000, 38700),
                     "NEX000015": (23000, 24725),
                     "NEX000036": (23000, 24725),
                     "NEX000045": (23000, 24725)}),
}


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def _scan():
    """The weather-only pre-filter: the month's weather for
    each of the 24 fresh seeds, read from the seed alone
    (SimRng.stream("weather", day_index) is keyed by the
    seed, not by the population). Returns
    {seed: (rain, storm, rain indices, storm indices)} for
    the seeds matching rain + 2 x storm == 9."""
    from tools.sim.engine import WEATHER_WEIGHTS
    from tools.sim.rng import SimRng
    names = [n for n, _ in WEATHER_WEIGHTS]
    weights = [w for _, w in WEATHER_WEIGHTS]
    matches = {}
    for i in range(1, 25):
        seed = f"nb-probe-{i}"
        rng = SimRng(seed)
        presets = [rng.stream("weather", d).choices(
            names, weights=weights)[0] for d in range(30)]
        rain = presets.count("rain")
        storm = presets.count("storm")
        if rain + 2 * storm == 9:
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

    # 2. The tool's figures at the new factor, from the NB
    # mix both senior months share (7 rain + 1 storm): the
    # gross is round(band x factor), the nets follow with
    # tax and uplift recomputed, the trajectory ends at net.
    check(econ.taxi_weather_factor(7, 1) == 1.075,
          "tool: the 7/1 factor is exactly 1.075",
          str(econ.taxi_weather_factor(7, 1)))
    check(econ.taxi_weather_factor(9, 0) == 1.075,
          "tool: the 9/0 factor is exactly 1.075",
          str(econ.taxi_weather_factor(9, 0)))
    check(abs(econ.taxi_weather_factor(5, 2) - 1.075) < 1e-9,
          "tool: the 5/2 factor is 1.075 up to float error",
          str(econ.taxi_weather_factor(5, 2)))
    prices = econ.load("prices.json")
    wages = {w["profession_id"]: w
             for w in prices["wages_monthly"]}
    for tier, gross, net, delta in (("entry", 15050, 7180, 1050),
                                    ("mid", 24725, 12985, 1725),
                                    ("senior", 38700, 21370, 2700)):
        flat = econ.simulate(prices, wages["taxi_driver"],
                             tier)
        surged = econ.simulate(
            prices, wages["taxi_driver"], tier,
            taxi_rain_days=7, taxi_storm_days=1)
        check(surged["gross"] == gross,
              f"tool: 7/1 {tier} gross is {gross}",
              str(surged["gross"]))
        check(surged["net"] == net,
              f"tool: 7/1 {tier} net is {net}",
              str(surged["net"]))
        check(surged["gross"] - flat["gross"] == delta,
              f"tool: 7/1 {tier} delta is {delta}",
              str(surged["gross"] - flat["gross"]))
        check(surged["end_balance"] == surged["net"],
              f"tool: 7/1 {tier} ends at net",
              str(surged["end_balance"]))
        check(surged["min_balance"] == 0,
              f"tool: 7/1 {tier} minbal is 0",
              str(surged["min_balance"]))
        check(surged["gross"]
              == round(flat["gross"]
                       * econ.taxi_weather_factor(7, 1)),
              f"tool: 7/1 {tier} gross is round(band x factor)",
              str(surged["gross"]))
    # The rounding at 1.0750 is a no-op at every tier: the
    # products are exact integers from the 7/1 and 9/0
    # mixes, and sit a float epsilon above the integer from
    # the 5/2 mix, with round() landing on them in every
    # case — the same shape as MU at 1.1000.
    for band, gross in ((14000, 15050), (23000, 24725),
                        (36000, 38700)):
        product = band * econ.taxi_weather_factor(7, 1)
        check(product == float(gross)
              and round(product) == gross,
              f"tool: {band:,} x 1.0750 is exactly"
              f" {gross:,}.0 (no-op) from 7/1",
              str(product))
        product90 = band * econ.taxi_weather_factor(9, 0)
        check(product90 == float(gross)
              and round(product90) == gross,
              f"tool: {band:,} x 1.0750 is exactly"
              f" {gross:,}.0 (no-op) from 9/0",
              str(product90))
        product52 = band * econ.taxi_weather_factor(5, 2)
        check(abs(product52 - gross) < 1e-9
              and round(product52) == gross,
              f"tool: {band:,} x 1.0750 is {gross:,} up to"
              " float error from 5/2",
              str(product52))
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
    # The factor keys on the counts, not the mix: all three
    # NB mixes land on 1.0750 (the 5/2 mix within float
    # error), and the tool's grosses are identical from all
    # three.
    check(econ.taxi_weather_factor(7, 1) == 1.075
          and econ.taxi_weather_factor(9, 0) == 1.075
          and abs(econ.taxi_weather_factor(5, 2) - 1.075)
          < 1e-9,
          "tool: all three NB mixes give factor 1.075",
          str([econ.taxi_weather_factor(r, s)
               for r, s in ((7, 1), (5, 2), (9, 0))]))
    for tier in ("entry", "mid", "senior"):
        grosses = {econ.simulate(
            prices, wages["taxi_driver"], tier,
            taxi_rain_days=r, taxi_storm_days=s)["gross"]
            for r, s in ((7, 1), (5, 2), (9, 0))}
        check(len(grosses) == 1,
              f"tool: the {tier} gross is identical from all"
              " three NB mixes",
              str(grosses))

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
    check("nb-probe" not in d1_text,
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

    # 4. The weather-only scan: exactly nine of the 24
    # fresh seeds match rain + 2 x storm == 9, with the
    # recorded counts and day indices.
    scanned = _scan()
    expected_scan = {
        seed: (counts[0], counts[1], r_idx, s_idx)
        for seed, (counts, r_idx, s_idx, _)
        in EXPECTED_LIVE.items()
    }
    check(scanned == expected_scan,
          "scan: exactly the nine recorded seeds match rain +"
          " 2 x storm == 9",
          str(sorted(scanned)))
    check(len(scanned) == 9,
          "scan: the hit rate is 9 in 24",
          str(len(scanned)))

    # 5. Live re-derivation of the nine matching months.
    total_drivers = 0
    total_seniors = 0
    for seed, (counts, r_idx, s_idx, expected) in \
            EXPECTED_LIVE.items():
        rain, storm, live_r, live_s, drivers = _measure(seed)
        factor = econ.taxi_weather_factor(rain, storm)
        total_drivers += len(drivers)
        total_seniors += sum(
            1 for d in drivers.values() if d[0] == 36000)
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
        check(len(drivers) == len(expected),
              f"live {seed}: the month holds {len(expected)}"
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
        ok = all(len(d[1]) == 1
                 and d[1][0] == round(d[0] * factor)
                 for d in drivers.values())
        check(ok,
              f"live {seed}: every taxi driver settled at"
              " exactly round(band x factor)",
              str({k: (v[0], v[1])
                   for k, v in drivers.items()}))
        check(sorted({d[1][0] for d in drivers.values()})
              == sorted({g for _, g in expected.values()}),
              f"live {seed}: the settled grosses are"
              f" {sorted({g for _, g in expected.values()})}",
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
        got = {cid: (d[0], d[1][0]) for cid, d in drivers.items()
               if len(d[1]) == 1}
        check(got == expected,
              f"live {seed}: the drivers are exactly the"
              " recorded ones, at the recorded grosses",
              str(got))
    check(total_drivers == 27,
          "live: twenty-seven taxi drivers in all across the"
          " nine months",
          str(total_drivers))
    check(total_seniors == 2,
          "live: exactly two senior drivers across the nine"
          " months",
          str(total_seniors))
    check(f"{econ.taxi_weather_factor(7, 1):.4f}" == "1.0750",
          "live: the nb-probe-2 month is factor 1.0750 to"
          " four places")
    # nb-probe-15 is the month at 1.0750 holding all three
    # tiers; nb-probe-2 holds a senior and entries, no mid.
    check(sorted({band for band, _ in
                  EXPECTED_LIVE["nb-probe-15"][3].values()})
          == [14000, 23000, 36000],
          "live: nb-probe-15 holds all three tiers",
          str(sorted({band for band, _ in
                      EXPECTED_LIVE["nb-probe-15"][3]
                      .values()})))
    check(sorted({band for band, _ in
                  EXPECTED_LIVE["nb-probe-2"][3].values()})
          == [14000, 36000],
          "live: nb-probe-2 holds senior and entry, no mid",
          str(sorted({band for band, _ in
                      EXPECTED_LIVE["nb-probe-2"][3]
                      .values()})))
    check(sum(1 for _, (_, _, _, expected) in
              EXPECTED_LIVE.items()
              for band, _ in expected.values()
              if band == 36000) == 2,
          "live: exactly two senior settlements in the NB"
          " hunt (nb-probe-2, nb-probe-15)",
          "NEX000007, NEX000048")
    # Both senior months share the 7/1 mix at different day
    # positions — the settlement keys on the counts, not the
    # positions.
    check(scanned["nb-probe-2"][2]
          != scanned["nb-probe-15"][2]
          and scanned["nb-probe-2"][3]
          != scanned["nb-probe-15"][3],
          "live: the two senior months share the 7/1 mix at"
          " different day positions",
          str((scanned["nb-probe-2"][2:],
               scanned["nb-probe-15"][2:])))
    # nb-probe-23 is the first live 9 rain + 0 storm month
    # at 1.0750: no prior 1.0750 month has that mix.
    check(all(counts != (9, 0)
              for counts, _ in PRIOR_10750.values()),
          "live: no prior 1.0750 month is 9 rain + 0 storm",
          str([c for c, _ in PRIOR_10750.values()]))

    # 6. The record correction: re-derive the five prior
    # 1.0750 months live. The §39/§41 tables already hold
    # the senior settlements; the MS/MU verify scripts
    # never re-derived them, so this is the first live
    # check of those rows.
    s39 = report.split("## 39.")[1].split("## 40.")[0]
    s41 = report.split("## 41.")[1].split("## 42.")[0]
    check("| ms-probe-8 | 7 | 1 | 1.0750 | senior: 38,700 |"
          in s39,
          "record §39: the ms-probe-8 senior row is in the"
          " table")
    check("| mu-probe-14 | 5 | 2 | 1.0750 | mid: 24,725 × 3;"
          " senior: 38,700 |" in s41,
          "record §41: the mu-probe-14 senior row is in the"
          " table")
    # The erroneous claim wraps across a line break in §47,
    # so the check reads the flattened prose — no measured
    # fact changed.
    s47 = report.split("## 47.")[1].split("## 48.")[0]
    s47_flat = " ".join(s47.split())
    check("no month in the record holds a senior at 1.0750"
          in s47_flat,
          "record §47: the erroneous gap claim is on record"
          " (the claim NB corrects)")
    prior_entry = 0
    prior_mid = 0
    prior_senior = 0
    for seed, (counts, expected) in PRIOR_10750.items():
        rain, storm, _, _, drivers = _measure(seed)
        factor = econ.taxi_weather_factor(rain, storm)
        prior_entry += sum(
            1 for d in drivers.values() if d[0] == 14000)
        prior_mid += sum(
            1 for d in drivers.values() if d[0] == 23000)
        prior_senior += sum(
            1 for d in drivers.values() if d[0] == 36000)
        check((rain, storm) == counts,
              f"prior {seed}: month 1 has {counts[0]} rain"
              f" days and {counts[1]} storm days",
              f"rain={rain} storm={storm}")
        check(len(drivers) == len(expected),
              f"prior {seed}: the month holds {len(expected)}"
              " taxi driver(s)",
              str(len(drivers)))
        check(all(d[3] is None for d in drivers.values()),
              f"prior {seed}: every taxi driver is"
              " SYS-EMPLOYERS-paid")
        ok = all(len(d[1]) == 1
                 and d[1][0] == round(d[0] * factor)
                 for d in drivers.values())
        check(ok,
              f"prior {seed}: every taxi driver settled at"
              " exactly round(band x factor)",
              str({k: (v[0], v[1])
                   for k, v in drivers.items()}))
        got = {cid: (d[0], d[1][0]) for cid, d in drivers.items()
               if len(d[1]) == 1}
        check(got == expected,
              f"prior {seed}: the drivers are exactly the"
              " recorded ones, at the recorded grosses",
              str(got))
    check((prior_entry, prior_mid, prior_senior) == (2, 9, 2),
          "prior: before NB the tiers at 1.0750 were already"
          " live entry 2, mid 9, senior 2",
          str((prior_entry, prior_mid, prior_senior)))
    nb_entry = sum(1 for _, (_, _, _, expected) in
                   EXPECTED_LIVE.items()
                   for band, _ in expected.values()
                   if band == 14000)
    nb_mid = sum(1 for _, (_, _, _, expected) in
                 EXPECTED_LIVE.items()
                 for band, _ in expected.values()
                 if band == 23000)
    check((prior_entry + nb_entry, prior_mid + nb_mid,
           prior_senior + total_seniors) == (9, 27, 4),
          "prior: after NB the tiers at 1.0750 are live"
          " entry 9, mid 27, senior 4",
          str((prior_entry + nb_entry, prior_mid + nb_mid,
               prior_senior + total_seniors)))

    # 7. The V7 report §48: prose matches the measurement.
    check("## 48. Addendum — Senior taxi settlement at"
          " 1.0750, weather-first: the senior was already"
          " live; the hunt finds two more, and the record"
          " is corrected (Unit NB, Queue 59)"
          in report,
          "report §48: the addendum exists")
    s48 = report.split("## 48.")[1]
    s48_flat = " ".join(s48.split())
    check("nb-probe-2" in s48 and "nb-probe-15" in s48,
          "report §48: the senior probe seeds are named")
    check("NEX000007" in s48 and "NEX000048" in s48,
          "report §48: the senior drivers are named")
    check("1.0750" in s48,
          "report §48: the new factor is quoted")
    check("15,050" in s48 and "24,725" in s48
          and "38,700" in s48,
          "report §48: all three surged grosses are quoted")
    check("15,050.0" in s48 and "24,725.0" in s48
          and "38,700.0" in s48,
          "report §48: the rounding cases are quoted")
    check("15,050.000000000002" in s48
          and "24,725.000000000004" in s48
          and "38,700.00000000001" in s48,
          "report §48: the 5/2 float-epsilon products are"
          " quoted")
    check("NEX000036" in s48 and "NEX000001" in s48
          and "NEX000026" in s48 and "NEX000056" in s48,
          "report §48: the other nb-probe-15 drivers are"
          " named")
    check("does NOT move" in s48_flat
          and MN_MD5 in s48 and MN_SH_MD5 in s48,
          "report §48: the md5 standing is recorded")
    check("| 1.0750 | entry | 15,050 | 7,180 | +1,050 |"
          " +680 |" in s48,
          "report §48: the per-factor entry row is printed")
    check("| 1.0750 | mid | 24,725 | 12,985 | +1,725 |"
          " +1,035 |" in s48,
          "report §48: the per-factor mid row is printed")
    check("| 1.0750 | senior | 38,700 | 21,370 | +2,700 |"
          " +1,620 |" in s48,
          "report §48: the per-factor senior row is printed")
    check("37.5% hit rate" in s48_flat,
          "report §48: the scan hit rate is recorded")
    check("nb-probe-1" in s48 and "nb-probe-24" in s48,
          "report §48: the full scan range is recorded")
    check("rain + 2 × storm = 9" in s48_flat,
          "report §48: the pre-filter signature is recorded")
    check("nine live factors" in s48_flat,
          "report §48: the surge still rests on nine live"
          " factors")
    check("1.0167" in s48_flat and "only remaining in-ladder"
          " senior gap" in s48_flat,
          "report §48: the 1.0167 senior gap is recorded")
    check("Queue 60 Unit NC" in s48_flat,
          "report §48: the open 1.0167 senior hunt is"
          " recorded")
    check("1.1333" in s48_flat,
          "report §48: the factor above the top is recorded")
    check("eighth time" in s48_flat,
          "report §48: the pre-filter is verified an eighth"
          " time")
    check("different day positions" in s48_flat,
          "report §48: the counts-not-positions finding is"
          " recorded")
    check("there was no gap" in s48_flat,
          "report §48: the correction is stated")
    check("ms-probe-8" in s48 and "mu-probe-14" in s48,
          "report §48: the two prior senior months are"
          " named")
    check("| nb-probe-2 | 7 | 1 | 1.0750 | entry: 15,050 × 2,"
          " senior: 38,700 |" in s48,
          "report §48: the nb-probe-2 scan row is printed")
    check("| nb-probe-15 | 7 | 1 | 1.0750 | entry: 15,050,"
          " mid: 24,725 × 3, senior: 38,700 |" in s48,
          "report §48: the nb-probe-15 scan row is printed")
    check("| nb-probe-23 | 9 | 0 | 1.0750 | mid: 24,725 × 3 |"
          in s48,
          "report §48: the nb-probe-23 scan row is printed")
    check("Unit NB, Queue 59, §48" in report.split("## 16.")[1]
          .split("## 17.")[0],
          "report §16: the NB update is recorded")
    check("NEX000048" in report.split("## 16.")[1]
          .split("## 17.")[0],
          "report §16: the live senior driver is named")

    # 8. GDD-03 §2 records the NB update.
    check("Unit NB · Queue 59" in gdd03,
          "GDD-03 §2: the NB update is recorded")
    check("NEX000048" in gdd03,
          "GDD-03 §2: the live senior driver is named")
    check("does NOT move" in gdd03,
          "GDD-03 §2: the md5 standing is recorded")

    # 9. The economy_sim.py comments record the NB outcome
    # and the correction.
    check("Queue 59 Unit NB" in sim_src,
          "tool: the comments name the NB decision")
    check("report §48" in sim_src,
          "tool: the comments record §48")
    check("nb-probe-15" in sim_src,
          "tool: the comments name the all-three-tiers seed")
    check("ms-probe-8" in sim_src,
          "tool: the comments name the prior senior seed")

    # 10. Tests pin the NB figures.
    check("test_taxi_surge_senior_settles_live_at_10750"
          in regress,
          "tests: the senior-settles-live-at-1.0750 test"
          " exists")
    check("15050, 7180" in regress and "24725, 12985" in regress
          and "38700, 21370" in regress,
          "tests: the new-factor grosses and nets are pinned")
    check("1050, 1725, 2700" in regress,
          "tests: the per-tier deltas are pinned")
    check("38700.0" in regress,
          "tests: the exact senior product is pinned")

    # 11. Scope: only the NB files changed for this unit.
    # The grep matches the unit commit only: the queue-tick
    # commit shares the "Queue 59 NB:" prefix but carries
    # bookkeeping (STATUS.md + WORK-QUEUE.md), not unit files.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H",
         "--grep=^Queue 59 NB: senior taxi settlement at 1.0750",
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
                    "tools/verify_queue59_nb.py"},
          "scope: only the five NB files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
