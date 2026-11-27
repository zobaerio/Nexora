"""Verify Queue 60 Unit NC — Senior Taxi Settlement at
1.0167, Weather-First: the senior settles live at last;
the ladder is closed (NB follow-up).

Checks the corroboration against its sources:
tools/sim/engine.py (the settlement scales a taxi driver's
gross by taxi_factor = 1 + 0.25 x rain_days/30 + 0.5 x
storm_days/30, rounded to an integer, in the SYS-EMPLOYERS
branch only), tools/economy_sim.py (a comment only — the
tool's formula already reproduces the settled grosses, so
no tool change and the pinned md5 does NOT move),
tools/sim/tests/test_no_regression.py (a new test pins the
1.0167 factor from both mixes, the per-tier grosses and
nets, the rounding down at both lower tiers and the no-op
at the senior tier, the per-tier deltas, and the six live
senior settlements),
docs/ECONOMY-SIM-REPORT-V7.md §49 (the prose matches the
measurement, including the per-tier table, the full
twelve-seed scan table, the twelve live settlements, and
the re-derivation of the three prior 1.0167 months proving
the gap was real) and §16 (the 1.0167 update is recorded),
and docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the NC
update). Re-runs the weather-only scan over the 800 fresh
seeds and every matching month live (twelve seeds, 60
population, 32 days each) and asserts the recorded
weather counts and settled taxi grosses — and re-derives
the three prior 1.0167 months live (ms-probe-12,
ms-probe-13, mt-probe-8) to prove the gap claim against
the sweep tables, per the NB lesson: the gap was real
this time — no prior 1.0167 month holds a senior.
Prints one line per check and a summary; exits 0 only when
every check passes.
Run from the repo root: python3 tools/verify_queue60_nc.py
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

# The twelve matching months, in scan order: seed ->
# ((rain, storm), rain day indices, storm day indices,
#  {character id: (wage band, settled gross)}). All twelve
# are the single 2 rain + 0 storm mix, at twelve different
# day positions.
EXPECTED_LIVE = {
    "nc-probe-21": ((2, 0),
                    [2, 5],
                    [],
                    {"NEX000008": (23000, 23383),
                     "NEX000021": (14000, 14233),
                     "NEX000035": (23000, 23383),
                     "NEX000053": (14000, 14233)}),
    "nc-probe-306": ((2, 0),
                     [20, 23],
                     [],
                     {"NEX000006": (23000, 23383),
                      "NEX000022": (36000, 36600),
                      "NEX000026": (23000, 23383),
                      "NEX000030": (23000, 23383)}),
    "nc-probe-339": ((2, 0),
                     [20, 29],
                     [],
                     {"NEX000013": (23000, 23383),
                      "NEX000016": (23000, 23383),
                      "NEX000059": (23000, 23383)}),
    "nc-probe-472": ((2, 0),
                     [25, 28],
                     [],
                     {"NEX000025": (36000, 36600),
                      "NEX000051": (14000, 14233)}),
    "nc-probe-517": ((2, 0),
                     [16, 19],
                     [],
                     {"NEX000005": (23000, 23383),
                      "NEX000015": (23000, 23383)}),
    "nc-probe-525": ((2, 0),
                     [8, 22],
                     [],
                     {"NEX000029": (36000, 36600),
                      "NEX000030": (36000, 36600),
                      "NEX000041": (23000, 23383),
                      "NEX000049": (23000, 23383)}),
    "nc-probe-588": ((2, 0),
                     [3, 4],
                     [],
                     {"NEX000026": (14000, 14233),
                      "NEX000027": (23000, 23383),
                      "NEX000043": (23000, 23383)}),
    "nc-probe-597": ((2, 0),
                     [21, 24],
                     [],
                     {"NEX000010": (23000, 23383),
                      "NEX000021": (23000, 23383),
                      "NEX000048": (14000, 14233),
                      "NEX000049": (36000, 36600),
                      "NEX000056": (23000, 23383)}),
    "nc-probe-620": ((2, 0),
                     [1, 6],
                     [],
                     {"NEX000030": (23000, 23383),
                      "NEX000056": (23000, 23383),
                      "NEX000060": (23000, 23383)}),
    "nc-probe-629": ((2, 0),
                     [13, 16],
                     [],
                     {"NEX000007": (14000, 14233),
                      "NEX000026": (36000, 36600),
                      "NEX000051": (23000, 23383)}),
    "nc-probe-759": ((2, 0),
                     [7, 25],
                     [],
                     {"NEX000021": (23000, 23383),
                      "NEX000055": (23000, 23383),
                      "NEX000061": (23000, 23383)}),
    "nc-probe-780": ((2, 0),
                     [23, 29],
                     [],
                     {"NEX000018": (23000, 23383),
                      "NEX000021": (14000, 14233)}),
}

# The three prior 1.0167 months in the record: seed ->
# ((rain, storm), rain day indices, storm day indices,
#  {character id: (wage band, settled gross)}). The §39/§40
# tables record these rows; NB's lesson says a gap claim
# must be checked against the tables, so NC re-derives
# them live here — and the gap was real: none holds a
# senior.
PRIOR_10167 = {
    "ms-probe-12": ((0, 1),
                    [],
                    [1],
                    {"NEX000008": (14000, 14233),
                     "NEX000020": (23000, 23383),
                     "NEX000021": (14000, 14233),
                     "NEX000037": (23000, 23383)}),
    "ms-probe-13": ((2, 0),
                    [6, 23],
                    [],
                    {"NEX000012": (14000, 14233),
                     "NEX000040": (23000, 23383)}),
    "mt-probe-8": ((2, 0),
                   [3, 28],
                   [],
                   {"NEX000044": (23000, 23383)}),
}


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def _scan():
    """The weather-only pre-filter: the month's weather for
    each of the 800 fresh seeds, read from the seed alone
    (SimRng.stream("weather", day_index) is keyed by the
    seed, not by the population). Returns
    {seed: (rain, storm, rain indices, storm indices)} for
    the seeds matching rain + 2 x storm == 2."""
    from tools.sim.engine import WEATHER_WEIGHTS
    from tools.sim.rng import SimRng
    names = [n for n, _ in WEATHER_WEIGHTS]
    weights = [w for _, w in WEATHER_WEIGHTS]
    matches = {}
    for i in range(1, 801):
        seed = f"nc-probe-{i}"
        rng = SimRng(seed)
        presets = [rng.stream("weather", d).choices(
            names, weights=weights)[0] for d in range(30)]
        rain = presets.count("rain")
        storm = presets.count("storm")
        if rain + 2 * storm == 2:
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

    # 2. The tool's figures at the new factor, from the NC
    # mix (2 rain + 0 storm): the gross is round(band x
    # factor), the nets follow with tax and uplift
    # recomputed, the trajectory ends at net.
    check(abs(econ.taxi_weather_factor(2, 0)
              - 1.0166666666666666) < 1e-15,
          "tool: the 2/0 factor is 1.0166666666666666",
          str(econ.taxi_weather_factor(2, 0)))
    check(abs(econ.taxi_weather_factor(0, 1)
              - 1.0166666666666666) < 1e-15,
          "tool: the 0/1 factor is 1.0166666666666666",
          str(econ.taxi_weather_factor(0, 1)))
    check(f"{econ.taxi_weather_factor(2, 0):.4f}" == "1.0167",
          "tool: the factor prints as 1.0167 to four places")
    prices = econ.load("prices.json")
    wages = {w["profession_id"]: w
             for w in prices["wages_monthly"]}
    for tier, gross, net, delta in (("entry", 14233, 6651, 233),
                                    ("mid", 23383, 12180, 383),
                                    ("senior", 36600, 20110, 600)):
        flat = econ.simulate(prices, wages["taxi_driver"],
                             tier)
        surged = econ.simulate(
            prices, wages["taxi_driver"], tier,
            taxi_rain_days=2, taxi_storm_days=0)
        check(surged["gross"] == gross,
              f"tool: 2/0 {tier} gross is {gross}",
              str(surged["gross"]))
        check(surged["net"] == net,
              f"tool: 2/0 {tier} net is {net}",
              str(surged["net"]))
        check(surged["gross"] - flat["gross"] == delta,
              f"tool: 2/0 {tier} delta is {delta}",
              str(surged["gross"] - flat["gross"]))
        check(surged["end_balance"] == surged["net"],
              f"tool: 2/0 {tier} ends at net",
              str(surged["end_balance"]))
        check(surged["min_balance"] == 0,
              f"tool: 2/0 {tier} minbal is 0",
              str(surged["min_balance"]))
        check(surged["gross"]
              == round(flat["gross"]
                       * econ.taxi_weather_factor(2, 0)),
              f"tool: 2/0 {tier} gross is round(band x factor)",
              str(surged["gross"]))
    # The rounding at 1.0167 goes DOWN at both lower tiers
    # (the products sit a third above the integer) and is a
    # no-op at the senior tier (the product is exactly
    # 36,600.0) — the mirror of MV's down at 1.1167, and
    # the first factor where the lower tiers round down
    # while the senior product stays exact.
    for band, gross in ((14000, 14233), (23000, 23383)):
        product = band * econ.taxi_weather_factor(2, 0)
        check(gross < product < gross + 1
              and round(product) == gross,
              f"tool: {band:,} x 1.0167 is {product:.4f},"
              f" rounding down to {gross:,}",
              str(product))
    product = 36000 * econ.taxi_weather_factor(2, 0)
    check(product == 36600.0 and round(product) == 36600,
          "tool: 36,000 x 1.0167 is exactly 36600.0 (no-op)",
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
    # The factor keys on the counts, not the mix: the 2/0
    # mix (this hunt) and the 0/1 mix (the prior months)
    # land on the same factor, and the tool's grosses are
    # identical from both.
    check(econ.taxi_weather_factor(2, 0)
          == econ.taxi_weather_factor(0, 1),
          "tool: the 2/0 and 0/1 mixes give the same factor",
          str([econ.taxi_weather_factor(r, s)
               for r, s in ((2, 0), (0, 1))]))
    for tier in ("entry", "mid", "senior"):
        grosses = {econ.simulate(
            prices, wages["taxi_driver"], tier,
            taxi_rain_days=r, taxi_storm_days=s)["gross"]
            for r, s in ((2, 0), (0, 1))}
        check(len(grosses) == 1,
              f"tool: the {tier} gross is identical from both"
              " 1.0167 mixes",
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
    check("nc-probe" not in d1_text,
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

    # 4. The weather-only scan: exactly twelve of the 800
    # fresh seeds match rain + 2 x storm == 2, with the
    # recorded counts and day indices — all 2 rain + 0
    # storm, at twelve different day positions.
    scanned = _scan()
    expected_scan = {
        seed: (counts[0], counts[1], r_idx, s_idx)
        for seed, (counts, r_idx, s_idx, _)
        in EXPECTED_LIVE.items()
    }
    check(scanned == expected_scan,
          "scan: exactly the twelve recorded seeds match rain"
          " + 2 x storm == 2",
          str(sorted(scanned)))
    check(len(scanned) == 12,
          "scan: the hit rate is 12 in 800",
          str(len(scanned)))
    check(all(counts == (2, 0) for counts, _, _, _
              in EXPECTED_LIVE.values()),
          "scan: every match is 2 rain + 0 storm",
          str({s: c[0] for s, c in EXPECTED_LIVE.items()}))
    check(len({tuple(r) for _, r, _, _ in
               EXPECTED_LIVE.values()}) == 12,
          "scan: the twelve matches sit at twelve different"
          " day positions",
          str(sorted({tuple(r) for _, r, _, _ in
                      EXPECTED_LIVE.values()})))

    # 5. Live re-derivation of the twelve matching months.
    total_drivers = 0
    total_entry = 0
    total_mid = 0
    total_seniors = 0
    senior_months = []
    all_three = []
    for seed, (counts, r_idx, s_idx, expected) in \
            EXPECTED_LIVE.items():
        rain, storm, live_r, live_s, drivers = _measure(seed)
        factor = econ.taxi_weather_factor(rain, storm)
        total_drivers += len(drivers)
        total_entry += sum(
            1 for d in drivers.values() if d[0] == 14000)
        total_mid += sum(
            1 for d in drivers.values() if d[0] == 23000)
        n_senior = sum(
            1 for d in drivers.values() if d[0] == 36000)
        total_seniors += n_senior
        if n_senior:
            senior_months.append(seed)
        tiers = {d[0] for d in drivers.values()}
        if tiers == {14000, 23000, 36000}:
            all_three.append(seed)
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
    check(total_drivers == 38,
          "live: thirty-eight taxi drivers in all across the"
          " twelve months",
          str(total_drivers))
    check((total_entry, total_mid, total_seniors) == (7, 25, 6),
          "live: seven entry, twenty-five mid, six senior"
          " drivers across the twelve months",
          str((total_entry, total_mid, total_seniors)))
    check(f"{econ.taxi_weather_factor(2, 0):.4f}" == "1.0167",
          "live: the nc-probe-21 month is factor 1.0167 to"
          " four places")
    check(sorted(senior_months) == ["nc-probe-306",
                                    "nc-probe-472",
                                    "nc-probe-525",
                                    "nc-probe-597",
                                    "nc-probe-629"],
          "live: exactly five of the twelve months hold a"
          " senior driver",
          str(sorted(senior_months)))
    check(sorted(all_three) == ["nc-probe-597",
                                "nc-probe-629"],
          "live: exactly two months hold all three tiers",
          str(sorted(all_three)))
    check(sum(1 for _, (_, _, _, expected) in
              EXPECTED_LIVE.items()
              for band, _ in expected.values()
              if band == 36000) == 6,
          "live: exactly six senior settlements in the NC"
          " hunt (nc-probe-306, nc-probe-472, nc-probe-525"
          " x2, nc-probe-597, nc-probe-629)",
          "NEX000022, NEX000025, NEX000029, NEX000030,"
          " NEX000049, NEX000026")
    # nc-probe-525 holds two seniors from the same 2/0 mix
    # at the same day positions as each other — and all five
    # senior months share the mix at different day
    # positions, so the settlement keys on the counts, not
    # the positions.
    check(len({tuple(r) for s, r in
               ((seed, EXPECTED_LIVE[seed][1])
                for seed in senior_months)}) == 5,
          "live: the five senior months share the 2/0 mix at"
          " five different day positions",
          str([EXPECTED_LIVE[s][1] for s in senior_months]))

    # 6. The gap claim, checked against the sweep tables
    # per the NB lesson: re-derive the three prior 1.0167
    # months live. The §39/§40 tables already hold their
    # rows; the MS/MT verify scripts never re-derived them,
    # so this is the first live check of those rows — and
    # the gap was REAL this time: none holds a senior.
    s39 = report.split("## 39.")[1].split("## 40.")[0]
    s40 = report.split("## 40.")[1].split("## 41.")[0]
    check("| ms-probe-12 | 0 | 1 | 1.0167 | entry: 14,233 × 2;"
          " mid: 23,383 × 2 |" in s39,
          "record §39: the ms-probe-12 row is in the table")
    check("| ms-probe-13 | 2 | 0 | 1.0167 | entry: 14,233;"
          " mid: 23,383 |" in s39,
          "record §39: the ms-probe-13 row is in the table")
    check("| mt-probe-8 | 2 | 0 | 1.0167 | mid: 23,383 |"
          in s40,
          "record §40: the mt-probe-8 row is in the table")
    prior_entry = 0
    prior_mid = 0
    prior_senior = 0
    for seed, (counts, r_idx, s_idx, expected) in \
            PRIOR_10167.items():
        rain, storm, live_r, live_s, drivers = _measure(seed)
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
        check(live_r == r_idx,
              f"prior {seed}: the rain day indices match",
              str(live_r))
        check(live_s == s_idx,
              f"prior {seed}: the storm day indices match",
              str(live_s))
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
    check((prior_entry, prior_mid, prior_senior) == (3, 4, 0),
          "prior: before NC the tiers at 1.0167 were live"
          " entry 3, mid 4, senior 0 — the gap was real",
          str((prior_entry, prior_mid, prior_senior)))
    check((prior_entry + total_entry, prior_mid + total_mid,
           prior_senior + total_seniors) == (10, 29, 6),
          "prior: after NC the tiers at 1.0167 are live"
          " entry 10, mid 29, senior 6",
          str((prior_entry + total_entry,
               prior_mid + total_mid,
               prior_senior + total_seniors)))

    # 7. The V7 report §49: prose matches the measurement.
    check("## 49. Addendum — Senior taxi settlement at"
          " 1.0167, weather-first: the senior settles live"
          " at last; the ladder is closed (Unit NC, Queue"
          " 60)" in report,
          "report §49: the addendum exists")
    s49 = report.split("## 49.")[1]
    s49_flat = " ".join(s49.split())
    check("nc-probe-306" in s49 and "nc-probe-629" in s49,
          "report §49: the senior probe seeds are named")
    check("NEX000022" in s49 and "NEX000026" in s49
          and "NEX000049" in s49,
          "report §49: the senior drivers are named")
    check("1.0167" in s49,
          "report §49: the new factor is quoted")
    check("14,233" in s49 and "23,383" in s49
          and "36,600" in s49,
          "report §49: all three surged grosses are quoted")
    check("14233.333333333332" in s49
          and "23383.333333333332" in s49
          and "36600.0" in s49,
          "report §49: the rounding cases are quoted")
    check("NEX000029" in s49 and "NEX000030" in s49
          and "NEX000025" in s49,
          "report §49: the other senior drivers are named")
    check("does NOT move" in s49_flat
          and MN_MD5 in s49 and MN_SH_MD5 in s49,
          "report §49: the md5 standing is recorded")
    check("| 1.0167 | entry | 14,233 | 6,651 | +233 | +151 |"
          in s49,
          "report §49: the per-factor entry row is printed")
    check("| 1.0167 | mid | 23,383 | 12,180 | +383 | +230 |"
          in s49,
          "report §49: the per-factor mid row is printed")
    check("| 1.0167 | senior | 36,600 | 20,110 | +600 | +360 |"
          in s49,
          "report §49: the per-factor senior row is printed")
    check("1.5% hit rate" in s49_flat,
          "report §49: the scan hit rate is recorded")
    check("nc-probe-1" in s49 and "nc-probe-800" in s49,
          "report §49: the full scan range is recorded")
    check("rain + 2 × storm = 2" in s49_flat,
          "report §49: the pre-filter signature is recorded")
    check("nine live factors" in s49_flat,
          "report §49: the surge still rests on nine live"
          " factors")
    check("every step" in s49_flat and "ladder is closed"
          in s49_flat,
          "report §49: the senior tier is live at every step"
          " of the ladder")
    check("Queue 61 Unit ND" in s49_flat,
          "report §49: the open 1.1333 hunt is recorded")
    check("1.1333" in s49_flat,
          "report §49: the factor above the top is recorded")
    check("ninth time" in s49_flat,
          "report §49: the pre-filter is verified a ninth"
          " time")
    check("different day positions" in s49_flat,
          "report §49: the counts-not-positions finding is"
          " recorded")
    check("gap was real" in s49_flat,
          "report §49: the prior-months check is stated")
    check("ms-probe-12" in s49 and "ms-probe-13" in s49
          and "mt-probe-8" in s49,
          "report §49: the three prior months are named")
    check("| nc-probe-306 | 2 | 0 | 1.0167 | mid: 23,383 × 3,"
          " senior: 36,600 |" in s49,
          "report §49: the nc-probe-306 scan row is printed")
    check("| nc-probe-525 | 2 | 0 | 1.0167 | mid: 23,383 × 2,"
          " senior: 36,600 × 2 |" in s49,
          "report §49: the nc-probe-525 scan row is printed")
    check("| nc-probe-597 | 2 | 0 | 1.0167 | entry: 14,233,"
          " mid: 23,383 × 3, senior: 36,600 |" in s49,
          "report §49: the nc-probe-597 scan row is printed")
    check("| nc-probe-629 | 2 | 0 | 1.0167 | entry: 14,233,"
          " mid: 23,383, senior: 36,600 |" in s49,
          "report §49: the nc-probe-629 scan row is printed")
    # The "Unit NC, Queue 60, §49" string wraps across a
    # line break in §16, so the check reads the flattened
    # prose — no measured fact changed (same class as
    # Queue 55's §44 wrap and Queue 59's §47 wrap).
    s16_flat = " ".join(report.split("## 16.")[1]
                        .split("## 17.")[0].split())
    check("Unit NC, Queue 60, §49" in s16_flat,
          "report §16: the NC update is recorded")
    check("NEX000022" in report.split("## 16.")[1]
          .split("## 17.")[0],
          "report §16: the live senior driver is named")

    # 8. GDD-03 §2 records the NC update.
    check("Unit NC · Queue 60" in gdd03,
          "GDD-03 §2: the NC update is recorded")
    check("NEX000022" in gdd03,
          "GDD-03 §2: the live senior driver is named")
    check("does NOT move" in gdd03,
          "GDD-03 §2: the md5 standing is recorded")

    # 9. The economy_sim.py comments record the NC outcome.
    check("Queue 60 Unit NC" in sim_src,
          "tool: the comments name the NC decision")
    check("report §49" in sim_src,
          "tool: the comments record §49")
    check("nc-probe-597" in sim_src,
          "tool: the comments name the all-three-tiers seed")
    check("ms-probe-12" in sim_src,
          "tool: the comments name the prior seed")

    # 10. Tests pin the NC figures.
    check("test_taxi_surge_senior_settles_live_at_10167"
          in regress,
          "tests: the senior-settles-live-at-1.0167 test"
          " exists")
    check("14233, 6651" in regress and "23383, 12180" in regress
          and "36600, 20110" in regress,
          "tests: the new-factor grosses and nets are pinned")
    check("233, 383, 600" in regress,
          "tests: the per-tier deltas are pinned")
    check("36600.0" in regress,
          "tests: the exact senior product is pinned")

    # 11. Scope: only the NC files changed for this unit.
    # The grep matches the unit commit only: the queue-tick
    # commit shares the "Queue 60 NC:" prefix but carries
    # bookkeeping (STATUS.md + WORK-QUEUE.md), not unit files.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H",
         "--grep=^Queue 60 NC: senior taxi settlement at 1.0167",
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
                    "tools/verify_queue60_nc.py"},
          "scope: only the five NC files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
