"""Verify Queue 61 Unit ND — Senior Taxi Settlement at
1.1333, Weather-First: the senior settles live above the
top; the ladder extends one step (NC follow-up).

Checks the corroboration against its sources:
tools/sim/engine.py (the settlement scales a taxi driver's
gross by taxi_factor = 1 + 0.25 x rain_days/30 + 0.5 x
storm_days/30, rounded to an integer, in the SYS-EMPLOYERS
branch only), tools/economy_sim.py (a comment only — the
tool's formula already reproduces the settled grosses, so
no tool change and the pinned md5 does NOT move),
tools/sim/tests/test_no_regression.py (a new test pins the
1.1333 factor from all three mixes, the per-tier grosses
and nets, the rounding up at both lower tiers and the
no-op at the senior tier, the per-tier deltas, and the four
live senior settlements),
docs/ECONOMY-SIM-REPORT-V7.md §50 (the prose matches the
measurement, including the per-tier table, the full
six-seed scan table, the six live settlements, the gap
check against the sweep tables, and the §49 denominator
correction) and §16 (the 1.1333 update is recorded),
and docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the ND
update). Re-runs the weather-only scan over the 800 fresh
seeds and every matching month live (six seeds, 60
population, 32 days each) and asserts the recorded
weather counts and settled taxi grosses — and checks the
gap claim against the sweep tables, per the NB lesson:
the factor column of every sweep table tops out at
1.1250 and 1.1333 appears before §50 only as the factor
above the top, so no month in the record held a settlement
at 1.1333 at any tier and the gap was real. Also checks
nd-probe-801..1000 holds no further match, so §49's seed
list was complete and only its denominator was off.
Prints one line per check and a summary; exits 0 only when
every check passes.
Run from the repo root: python3 tools/verify_queue61_nd.py
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

# The six matching months, in scan order: seed ->
# ((rain, storm), rain day indices, storm day indices,
#  {character id: (wage band, settled gross)}). Three
# mixes: 6 rain + 5 storm (nd-probe-68, nd-probe-165),
# 8 rain + 4 storm (nd-probe-190, nd-probe-270,
# nd-probe-792), 10 rain + 3 storm (nd-probe-650).
EXPECTED_LIVE = {
    "nd-probe-68": ((6, 5),
                    [7, 12, 19, 20, 21, 22],
                    [1, 8, 18, 24, 27],
                    {"NEX000009": (14000, 15867)}),
    "nd-probe-165": ((6, 5),
                     [0, 7, 10, 21, 24, 26],
                     [1, 3, 6, 8, 17],
                     {"NEX000006": (36000, 40800),
                      "NEX000007": (36000, 40800)}),
    "nd-probe-190": ((8, 4),
                     [3, 4, 5, 7, 13, 16, 27, 29],
                     [6, 19, 22, 25],
                     {"NEX000011": (23000, 26067),
                      "NEX000042": (23000, 26067)}),
    "nd-probe-270": ((8, 4),
                     [2, 3, 4, 9, 13, 18, 19, 24],
                     [22, 23, 25, 29],
                     {"NEX000029": (14000, 15867),
                      "NEX000031": (23000, 26067)}),
    "nd-probe-650": ((10, 3),
                     [0, 4, 8, 11, 14, 15, 16, 22, 27, 29],
                     [13, 17, 23],
                     {"NEX000002": (23000, 26067),
                      "NEX000032": (36000, 40800),
                      "NEX000059": (36000, 40800)}),
    "nd-probe-792": ((8, 4),
                     [0, 2, 3, 4, 14, 26, 27, 29],
                     [8, 12, 18, 21],
                     {"NEX000008": (23000, 26067),
                      "NEX000014": (23000, 26067),
                      "NEX000029": (23000, 26067),
                      "NEX000032": (23000, 26067)}),
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
    the seeds matching rain + 2 x storm == 16."""
    from tools.sim.engine import WEATHER_WEIGHTS
    from tools.sim.rng import SimRng
    names = [n for n, _ in WEATHER_WEIGHTS]
    weights = [w for _, w in WEATHER_WEIGHTS]
    matches = {}
    for i in range(1, 801):
        seed = f"nd-probe-{i}"
        rng = SimRng(seed)
        presets = [rng.stream("weather", d).choices(
            names, weights=weights)[0] for d in range(30)]
        rain = presets.count("rain")
        storm = presets.count("storm")
        if rain + 2 * storm == 16:
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

    # 2. The tool's figures at the new factor, from the ND
    # mixes (6/5, 8/4, 10/3): the gross is round(band x
    # factor), the nets follow with tax and uplift
    # recomputed, the trajectory ends at net.
    for r, s in ((6, 5), (8, 4), (10, 3)):
        check(abs(econ.taxi_weather_factor(r, s)
                  - 1.1333333333333333) < 1e-15,
              f"tool: the {r}/{s} factor is 1.1333333333333333",
              str(econ.taxi_weather_factor(r, s)))
    check(f"{econ.taxi_weather_factor(6, 5):.4f}" == "1.1333",
          "tool: the factor prints as 1.1333 to four places")
    prices = econ.load("prices.json")
    wages = {w["profession_id"]: w
             for w in prices["wages_monthly"]}
    for tier, gross, net, delta in (("entry", 15867, 7671, 1867),
                                    ("mid", 26067, 13791, 3067),
                                    ("senior", 40800, 22590, 4800)):
        flat = econ.simulate(prices, wages["taxi_driver"],
                             tier)
        surged = econ.simulate(
            prices, wages["taxi_driver"], tier,
            taxi_rain_days=6, taxi_storm_days=5)
        check(surged["gross"] == gross,
              f"tool: 6/5 {tier} gross is {gross}",
              str(surged["gross"]))
        check(surged["net"] == net,
              f"tool: 6/5 {tier} net is {net}",
              str(surged["net"]))
        check(surged["gross"] - flat["gross"] == delta,
              f"tool: 6/5 {tier} delta is {delta}",
              str(surged["gross"] - flat["gross"]))
        check(surged["end_balance"] == surged["net"],
              f"tool: 6/5 {tier} ends at net",
              str(surged["end_balance"]))
        check(surged["min_balance"] == 0,
              f"tool: 6/5 {tier} minbal is 0",
              str(surged["min_balance"]))
        check(surged["gross"]
              == round(flat["gross"]
                       * econ.taxi_weather_factor(6, 5)),
              f"tool: 6/5 {tier} gross is round(band x factor)",
              str(surged["gross"]))
    # The rounding at 1.1333 goes UP at both lower tiers
    # (the products sit two thirds below the integer) and
    # is a no-op at the senior tier (the product is exactly
    # 40800.0) — the mirror of NC's down at 1.0167, and the
    # first factor where the lower tiers round up while the
    # senior product stays exact.
    for band, gross in ((14000, 15867), (23000, 26067)):
        product = band * econ.taxi_weather_factor(6, 5)
        check(gross - 1 < product < gross
              and round(product) == gross,
              f"tool: {band:,} x 1.1333 is {product:.4f},"
              f" rounding up to {gross:,}",
              str(product))
    product = 36000 * econ.taxi_weather_factor(6, 5)
    check(product == 40800.0 and round(product) == 40800,
          "tool: 36,000 x 1.1333 is exactly 40800.0 (no-op)",
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
    # The factor keys on the counts, not the mix: the 6/5,
    # 8/4 and 10/3 mixes land on the same factor, and the
    # tool's grosses are identical from all three.
    check(econ.taxi_weather_factor(6, 5)
          == econ.taxi_weather_factor(8, 4)
          == econ.taxi_weather_factor(10, 3),
          "tool: the 6/5, 8/4 and 10/3 mixes give the same"
          " factor",
          str([econ.taxi_weather_factor(r, s)
               for r, s in ((6, 5), (8, 4), (10, 3))]))
    for tier in ("entry", "mid", "senior"):
        grosses = {econ.simulate(
            prices, wages["taxi_driver"], tier,
            taxi_rain_days=r, taxi_storm_days=s)["gross"]
            for r, s in ((6, 5), (8, 4), (10, 3))}
        check(len(grosses) == 1,
              f"tool: the {tier} gross is identical from all"
              " three 1.1333 mixes",
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
    check("nd-probe" not in d1_text,
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

    # 4. The weather-only scan: exactly six of the 800
    # fresh seeds match rain + 2 x storm == 16, with the
    # recorded counts and day indices — across three mixes.
    scanned = _scan()
    expected_scan = {
        seed: (counts[0], counts[1], r_idx, s_idx)
        for seed, (counts, r_idx, s_idx, _)
        in EXPECTED_LIVE.items()
    }
    check(scanned == expected_scan,
          "scan: exactly the six recorded seeds match rain"
          " + 2 x storm == 16",
          str(sorted(scanned)))
    check(len(scanned) == 6,
          "scan: the hit rate is 6 in 800",
          str(len(scanned)))
    check({counts for counts, _, _, _
           in EXPECTED_LIVE.values()}
          == {(6, 5), (8, 4), (10, 3)},
          "scan: the six matches span three mixes",
          str({s: c[0] for s, c in EXPECTED_LIVE.items()}))
    check(len({tuple(r) for _, r, _, _ in
               EXPECTED_LIVE.values()}) == 6,
          "scan: the six matches sit at six different"
          " day positions",
          str(sorted({tuple(r) for _, r, _, _ in
                      EXPECTED_LIVE.values()})))

    # 5. Live re-derivation of the six matching months.
    total_drivers = 0
    total_entry = 0
    total_mid = 0
    total_seniors = 0
    senior_months = []
    two_senior_months = []
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
        if n_senior == 2:
            two_senior_months.append(seed)
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
    check(total_drivers == 14,
          "live: fourteen taxi drivers in all across the"
          " six months",
          str(total_drivers))
    check((total_entry, total_mid, total_seniors) == (2, 8, 4),
          "live: two entry, eight mid, four senior drivers"
          " across the six months",
          str((total_entry, total_mid, total_seniors)))
    check(f"{econ.taxi_weather_factor(6, 5):.4f}" == "1.1333",
          "live: the nd-probe-68 month is factor 1.1333 to"
          " four places")
    check(sorted(senior_months) == ["nd-probe-165",
                                    "nd-probe-650"],
          "live: exactly two of the six months hold a senior"
          " driver",
          str(sorted(senior_months)))
    check(sorted(two_senior_months) == ["nd-probe-165",
                                        "nd-probe-650"],
          "live: exactly two months hold two seniors each",
          str(sorted(two_senior_months)))
    check(all_three == [],
          "live: no month holds all three tiers",
          str(all_three))
    check(sum(1 for _, (_, _, _, expected) in
              EXPECTED_LIVE.items()
              for band, _ in expected.values()
              if band == 36000) == 4,
          "live: exactly four senior settlements in the ND"
          " hunt (nd-probe-165 x2, nd-probe-650 x2)",
          "NEX000006, NEX000007, NEX000032, NEX000059")
    # The two senior months come from different mixes at
    # different day positions, so the settlement keys on
    # the counts, not the positions.
    check(EXPECTED_LIVE["nd-probe-165"][0]
          != EXPECTED_LIVE["nd-probe-650"][0],
          "live: the two senior months come from different"
          " mixes (6/5 vs 10/3)",
          str([EXPECTED_LIVE[s][0] for s in senior_months]))

    # 6. The gap claim, checked against the sweep tables
    # per the NB lesson: no month in the record held a
    # settlement at 1.1333 at any tier. The factor column
    # of every sweep table tops out at 1.1250, and 1.1333
    # appears before §50 only as the factor above the top.
    pre50 = report.split("## 50.")[0]
    # The §16 ND paragraph is the new record itself, so
    # the "above the top" check reads the text without it.
    nd_para_start = pre50.find(
        "**Taxi surge at the factor above the new top, 1.1333")
    nd_para_end = pre50.find(
        "The entry driver's uplift appears only under the"
        " surge", nd_para_start)
    without_nd = (pre50[:nd_para_start]
                  + pre50[nd_para_end:])
    rows = [ln for ln in pre50.splitlines()
            if ln.startswith("|")
            and re.match(r"\| [a-z]+-probe-\d+ \|", ln)]
    factors = []
    for ln in rows:
        parts = [p.strip() for p in ln.split("|")]
        try:
            factors.append(float(parts[4]))
        except (IndexError, ValueError):
            pass
    check(len(factors) > 0,
          "record: sweep-table rows with a factor column"
          " exist to check against",
          str(len(factors)))
    check(max(factors) == 1.1250,
          "record: the factor column of every sweep table"
          " tops out at 1.1250",
          str(sorted(set(factors))))
    check(all("1.1333" not in ln for ln in rows),
          "record: no sweep-table row holds a settlement at"
          " 1.1333",
          str([ln for ln in rows if "1.1333" in ln]))
    # The phrase is "above the new top" in §45–§49 and
    # "above the top" in §16/§49, and it wraps across line
    # breaks in two places, so the check reads the flattened
    # prose and looks back 200 characters from each mention
    # for either form — no measured fact changed (same class
    # as Queue 55's §44 wrap, Queue 59's §47 wrap and Queue
    # 60's §49 wrap).
    without_nd_flat = " ".join(without_nd.split())
    mentions = [m.start() for m in
                re.finditer("1.1333", without_nd_flat)]
    check(len(mentions) > 0
          and all(re.search(r"above the (new )?top",
                            without_nd_flat[
                                max(0, pos - 200):pos])
                  for pos in mentions),
          "record: every other pre-§50 mention of 1.1333 is"
          " the factor-above-the-top prose",
          str([without_nd_flat[max(0, pos - 60):pos + 6]
               for pos in mentions
               if not re.search(
                   r"above the (new )?top", without_nd_flat[
                       max(0, pos - 200):pos])]))
    # §49's seed list was complete: nd-probe-801..1000
    # holds no further match, so only its denominator was
    # off (6 of 800, not 6 of 1,000).
    from tools.sim.engine import WEATHER_WEIGHTS
    from tools.sim.rng import SimRng
    names = [n for n, _ in WEATHER_WEIGHTS]
    weights = [w for _, w in WEATHER_WEIGHTS]
    extra = []
    for i in range(801, 1001):
        seed = f"nd-probe-{i}"
        rng = SimRng(seed)
        presets = [rng.stream("weather", d).choices(
            names, weights=weights)[0] for d in range(30)]
        if presets.count("rain") + 2 * presets.count("storm") == 16:
            extra.append(seed)
    check(extra == [],
          "record: nd-probe-801..1000 holds no further match",
          str(extra))

    # 7. The V7 report §50: prose matches the measurement.
    check("## 50. Addendum — Senior taxi settlement at"
          " 1.1333, weather-first: the senior settles live"
          " above the top; the ladder extends one step (Unit"
          " ND, Queue 61)" in report,
          "report §50: the addendum exists")
    s50 = report.split("## 50.")[1]
    s50_flat = " ".join(s50.split())
    check("nd-probe-165" in s50 and "nd-probe-650" in s50,
          "report §50: the senior probe seeds are named")
    check("NEX000006" in s50 and "NEX000007" in s50
          and "NEX000032" in s50 and "NEX000059" in s50,
          "report §50: the senior drivers are named")
    check("1.1333" in s50,
          "report §50: the new factor is quoted")
    check("15,867" in s50 and "26,067" in s50
          and "40,800" in s50,
          "report §50: all three surged grosses are quoted")
    check("15866.666666666666" in s50
          and "26066.666666666664" in s50
          and "40800.0" in s50,
          "report §50: the rounding cases are quoted")
    check("NEX000009" in s50 and "NEX000029" in s50
          and "NEX000002" in s50,
          "report §50: the lower-tier drivers are named")
    check("does NOT move" in s50_flat
          and MN_MD5 in s50 and MN_SH_MD5 in s50,
          "report §50: the md5 standing is recorded")
    check("| 1.1333 | entry | 15,867 | 7,671 | +1,867 | +1,171 |"
          in s50,
          "report §50: the per-factor entry row is printed")
    check("| 1.1333 | mid | 26,067 | 13,791 | +3,067 | +1,841 |"
          in s50,
          "report §50: the per-factor mid row is printed")
    check("| 1.1333 | senior | 40,800 | 22,590 | +4,800 |"
          " +2,840 |" in s50,
          "report §50: the per-factor senior row is printed")
    check("0.75% hit rate" in s50_flat,
          "report §50: the scan hit rate is recorded")
    check("nd-probe-1" in s50 and "nd-probe-800" in s50,
          "report §50: the full scan range is recorded")
    check("rain + 2 × storm = 16" in s50_flat,
          "report §50: the pre-filter signature is recorded")
    check("nine live factors" in s50_flat,
          "report §50: the surge still rests on nine live"
          " factors")
    check("extends one step above the old top" in s50_flat
          and "1..16" in s50_flat,
          "report §50: the ladder now runs 1..16")
    check("Queue 62 Unit NE" in s50_flat,
          "report §50: the open 1.1417 hunt is recorded")
    check("1.1417" in s50_flat,
          "report §50: the factor above the new top is"
          " recorded")
    check("tenth time" in s50_flat,
          "report §50: the pre-filter is verified a tenth"
          " time")
    check("different day positions" in s50_flat,
          "report §50: the counts-not-positions finding is"
          " recorded")
    check("gap was real" in s50_flat,
          "report §50: the prior-months check is stated")
    check("6 of 1,000" in s50_flat and "6 in 800" in s50_flat,
          "report §50: the §49 denominator correction is"
          " recorded")
    check("nd-probe-801" in s50 and "nd-probe-1000" in s50,
          "report §50: the 801–1000 check is recorded")
    check("No month holds all three tiers" in s50,
          "report §50: no all-three-tiers month is recorded")
    check("| nd-probe-165 | 6 | 5 | 1.1333 | senior: 40,800"
          " × 2 |" in s50,
          "report §50: the nd-probe-165 scan row is printed")
    check("| nd-probe-650 | 10 | 3 | 1.1333 | mid: 26,067,"
          " senior: 40,800 × 2 |" in s50,
          "report §50: the nd-probe-650 scan row is printed")
    check("| nd-probe-792 | 8 | 4 | 1.1333 | mid: 26,067"
          " × 4 |" in s50,
          "report §50: the nd-probe-792 scan row is printed")
    check("| nd-probe-68 | 6 | 5 | 1.1333 | entry: 15,867 |"
          in s50,
          "report §50: the nd-probe-68 scan row is printed")
    # The "Unit ND, Queue 61, §50" string wraps across a
    # line break in §16, so the check reads the flattened
    # prose — no measured fact changed (same class as
    # Queue 55's §44 wrap, Queue 59's §47 wrap and Queue
    # 60's §49 wrap).
    s16_flat = " ".join(report.split("## 16.")[1]
                        .split("## 17.")[0].split())
    check("Unit ND, Queue 61, §50" in s16_flat,
          "report §16: the ND update is recorded")
    check("NEX000006" in report.split("## 16.")[1]
          .split("## 17.")[0],
          "report §16: the live senior driver is named")

    # 8. GDD-03 §2 records the ND update.
    check("Unit ND · Queue 61" in gdd03,
          "GDD-03 §2: the ND update is recorded")
    check("NEX000006" in gdd03,
          "GDD-03 §2: the live senior driver is named")
    check("does NOT move" in gdd03,
          "GDD-03 §2: the md5 standing is recorded")

    # 9. The economy_sim.py comments record the ND outcome.
    check("Queue 61 Unit ND" in sim_src,
          "tool: the comments name the ND decision")
    check("report §50" in sim_src,
          "tool: the comments record §50")
    check("nd-probe-650" in sim_src,
          "tool: the comments name the 10/3 seed")
    check("nd-probe-165" in sim_src,
          "tool: the comments name the 6/5 senior seed")

    # 10. Tests pin the ND figures.
    check("test_taxi_surge_senior_settles_live_at_11333"
          in regress,
          "tests: the senior-settles-live-at-1.1333 test"
          " exists")
    check("15867, 7671" in regress and "26067, 13791" in regress
          and "40800, 22590" in regress,
          "tests: the new-factor grosses and nets are pinned")
    check("1867, 3067, 4800" in regress,
          "tests: the per-tier deltas are pinned")
    check("40800.0" in regress,
          "tests: the exact senior product is pinned")

    # 11. Scope: only the ND files changed for this unit.
    # The grep matches the unit commit only: the queue-tick
    # commit shares the "Queue 61 ND:" prefix but carries
    # bookkeeping (STATUS.md + WORK-QUEUE.md), not unit files.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H",
         "--grep=^Queue 61 ND: senior taxi settlement at 1.1333",
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
                    "tools/verify_queue61_nd.py"},
          "scope: only the five ND files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
