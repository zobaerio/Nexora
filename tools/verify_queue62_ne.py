"""Verify Queue 62 Unit NE — Senior Taxi Settlement at
1.1417, Weather-First: the senior stays tool-computed
only; the entry and mid tiers settle live (ND follow-up).

Checks the corroboration against its sources:
tools/sim/engine.py (the settlement scales a taxi driver's
gross by taxi_factor = 1 + 0.25 x rain_days/30 + 0.5 x
storm_days/30, rounded to an integer, in the SYS-EMPLOYERS
branch only), tools/economy_sim.py (a comment only — the
tool's formula already reproduces the settled grosses, so
no tool change and the pinned md5 does NOT move),
tools/sim/tests/test_no_regression.py (a new test pins the
1.1417 factor from all three mixes, the per-tier grosses
and nets, the rounding down at both lower tiers and the
no-op at the senior tier, the per-tier deltas, and the two
live entry + five live mid settlements — and that no senior
settles),
docs/ECONOMY-SIM-REPORT-V7.md §51 (the prose matches the
measurement, including the per-tier table, the full
four-seed scan table, the seven live settlements, the gap
check against the sweep tables, and the senior staying
tool-computed only) and §16 (the 1.1417 update is
recorded),
and docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the NE
update). Re-runs the weather-only scan over the 2,000
fresh seeds and every matching month live (four seeds, 60
population, 32 days each) and asserts the recorded
weather counts and settled taxi grosses — and checks the
gap claim against the sweep tables, per the NB lesson:
the factor column of every sweep table tops out at
1.1333 and 1.1417 appears before §51 only as the factor
above the new top, so no month in the record held a
settlement at 1.1417 at any tier and the gap was real.
Prints one line per check and a summary; exits 0 only when
every check passes.
Run from the repo root: python3 tools/verify_queue62_ne.py
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

# The four matching months, in scan order: seed ->
# ((rain, storm), rain day indices, storm day indices,
#  {character id: (wage band, settled gross)}). Three
# mixes: 5 rain + 6 storm (ne-probe-1117, ne-probe-1751),
# 7 rain + 5 storm (ne-probe-1459), 9 rain + 4 storm
# (ne-probe-1532). No senior driver in any month.
EXPECTED_LIVE = {
    "ne-probe-1117": ((5, 6),
                      [5, 6, 7, 14, 27],
                      [1, 2, 16, 17, 21, 25],
                      {"NEX000002": (14000, 15983),
                       "NEX000012": (14000, 15983),
                       "NEX000043": (23000, 26258)}),
    "ne-probe-1459": ((7, 5),
                      [0, 13, 15, 20, 22, 28, 29],
                      [3, 4, 16, 23, 27],
                      {"NEX000021": (23000, 26258)}),
    "ne-probe-1532": ((9, 4),
                      [0, 1, 2, 4, 5, 11, 12, 24, 29],
                      [7, 9, 13, 27],
                      {"NEX000029": (23000, 26258),
                       "NEX000058": (23000, 26258)}),
    "ne-probe-1751": ((5, 6),
                      [7, 13, 14, 18, 26],
                      [0, 1, 9, 17, 19, 29],
                      {"NEX000042": (23000, 26258)}),
}


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def _scan():
    """The weather-only pre-filter: the month's weather for
    each of the 2,000 fresh seeds, read from the seed alone
    (SimRng.stream("weather", day_index) is keyed by the
    seed, not by the population). Returns
    {seed: (rain, storm, rain indices, storm indices)} for
    the seeds matching rain + 2 x storm == 17."""
    from tools.sim.engine import WEATHER_WEIGHTS
    from tools.sim.rng import SimRng
    names = [n for n, _ in WEATHER_WEIGHTS]
    weights = [w for _, w in WEATHER_WEIGHTS]
    matches = {}
    for i in range(1, 2001):
        seed = f"ne-probe-{i}"
        rng = SimRng(seed)
        presets = [rng.stream("weather", d).choices(
            names, weights=weights)[0] for d in range(30)]
        rain = presets.count("rain")
        storm = presets.count("storm")
        if rain + 2 * storm == 17:
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

    # 2. The tool's figures at the new factor, from the NE
    # mixes (5/6, 7/5, 9/4): the gross is round(band x
    # factor), the nets follow with tax and uplift
    # recomputed, the trajectory ends at net.
    for r, s in ((5, 6), (7, 5), (9, 4)):
        check(abs(econ.taxi_weather_factor(r, s)
                  - 1.1416666666666666) < 1e-15,
              f"tool: the {r}/{s} factor is 1.1416666666666666",
              str(econ.taxi_weather_factor(r, s)))
    check(f"{econ.taxi_weather_factor(5, 6):.4f}" == "1.1417",
          "tool: the factor prints as 1.1417 to four places")
    prices = econ.load("prices.json")
    wages = {w["profession_id"]: w
             for w in prices["wages_monthly"]}
    for tier, gross, net, delta in (("entry", 15983, 7740, 1983),
                                    ("mid", 26258, 13905, 3258),
                                    ("senior", 41100, 22755, 5100)):
        flat = econ.simulate(prices, wages["taxi_driver"],
                             tier)
        surged = econ.simulate(
            prices, wages["taxi_driver"], tier,
            taxi_rain_days=5, taxi_storm_days=6)
        check(surged["gross"] == gross,
              f"tool: 5/6 {tier} gross is {gross}",
              str(surged["gross"]))
        check(surged["net"] == net,
              f"tool: 5/6 {tier} net is {net}",
              str(surged["net"]))
        check(surged["gross"] - flat["gross"] == delta,
              f"tool: 5/6 {tier} delta is {delta}",
              str(surged["gross"] - flat["gross"]))
        check(surged["end_balance"] == surged["net"],
              f"tool: 5/6 {tier} ends at net",
              str(surged["end_balance"]))
        check(surged["min_balance"] == 0,
              f"tool: 5/6 {tier} minbal is 0",
              str(surged["min_balance"]))
        check(surged["gross"]
              == round(flat["gross"]
                       * econ.taxi_weather_factor(5, 6)),
              f"tool: 5/6 {tier} gross is round(band x factor)",
              str(surged["gross"]))
    # The rounding at 1.1417 goes DOWN at both lower tiers
    # (the products sit a third above the integer) and is a
    # no-op at the senior tier — the mirror of ND's up at
    # 1.1333, and the first factor where the lower tiers
    # round down while the senior product sits a float
    # epsilon above the integer from one mix and exact from
    # the others.
    for band, gross in ((14000, 15983), (23000, 26258)):
        product = band * econ.taxi_weather_factor(5, 6)
        check(gross < product < gross + 1
              and round(product) == gross,
              f"tool: {band:,} x 1.1417 is {product:.4f},"
              f" rounding down to {gross:,}",
              str(product))
    check(abs(36000 * econ.taxi_weather_factor(5, 6)
              - 41100.0) < 1e-9
          and round(36000 * econ.taxi_weather_factor(5, 6))
          == 41100,
          "tool: 36,000 x 1.1417 is 41100.00000000001 from"
          " the 5/6 mix (no-op)",
          str(36000 * econ.taxi_weather_factor(5, 6)))
    check(36000 * econ.taxi_weather_factor(7, 5) == 41100.0
          and 36000 * econ.taxi_weather_factor(9, 4) == 41100.0,
          "tool: 36,000 x 1.1417 is exactly 41100.0 from the"
          " 7/5 and 9/4 mixes (no-op)",
          str([36000 * econ.taxi_weather_factor(r, s)
               for r, s in ((7, 5), (9, 4))]))
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
    # The factor keys on the counts, not the mix: the 5/6,
    # 7/5 and 9/4 mixes land on the same factor up to float
    # error (the 5/6 mix lands one ulp above the others:
    # 1.1416666666666668 vs 1.1416666666666666), and the
    # tool's grosses are identical from all three.
    check(all(abs(econ.taxi_weather_factor(5, 6)
                 - econ.taxi_weather_factor(r, s)) < 1e-15
              for r, s in ((7, 5), (9, 4))),
          "tool: the 5/6, 7/5 and 9/4 mixes give the same"
          " factor up to float error",
          str([econ.taxi_weather_factor(r, s)
               for r, s in ((5, 6), (7, 5), (9, 4))]))
    for tier in ("entry", "mid", "senior"):
        grosses = {econ.simulate(
            prices, wages["taxi_driver"], tier,
            taxi_rain_days=r, taxi_storm_days=s)["gross"]
            for r, s in ((5, 6), (7, 5), (9, 4))}
        check(len(grosses) == 1,
              f"tool: the {tier} gross is identical from all"
              " three 1.1417 mixes",
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
    check("ne-probe" not in d1_text,
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

    # 4. The weather-only scan: exactly four of the 2,000
    # fresh seeds match rain + 2 x storm == 17, with the
    # recorded counts and day indices — across three mixes.
    scanned = _scan()
    expected_scan = {
        seed: (counts[0], counts[1], r_idx, s_idx)
        for seed, (counts, r_idx, s_idx, _)
        in EXPECTED_LIVE.items()
    }
    check(scanned == expected_scan,
          "scan: exactly the four recorded seeds match rain"
          " + 2 x storm == 17",
          str(sorted(scanned)))
    check(len(scanned) == 4,
          "scan: the hit rate is 4 in 2,000",
          str(len(scanned)))
    check({counts for counts, _, _, _
           in EXPECTED_LIVE.values()}
          == {(5, 6), (7, 5), (9, 4)},
          "scan: the four matches span three mixes",
          str({s: c[0] for s, c in EXPECTED_LIVE.items()}))
    check(len({tuple(r) for _, r, _, _ in
               EXPECTED_LIVE.values()}) == 4,
          "scan: the four matches sit at four different"
          " day positions",
          str(sorted({tuple(r) for _, r, _, _ in
                      EXPECTED_LIVE.values()})))

    # 5. Live re-derivation of the four matching months.
    total_drivers = 0
    total_entry = 0
    total_mid = 0
    total_seniors = 0
    senior_months = []
    two_entry_months = []
    two_mid_months = []
    entry_mid_months = []
    all_three = []
    for seed, (counts, r_idx, s_idx, expected) in \
            EXPECTED_LIVE.items():
        rain, storm, live_r, live_s, drivers = _measure(seed)
        factor = econ.taxi_weather_factor(rain, storm)
        total_drivers += len(drivers)
        n_entry = sum(
            1 for d in drivers.values() if d[0] == 14000)
        n_mid = sum(
            1 for d in drivers.values() if d[0] == 23000)
        n_senior = sum(
            1 for d in drivers.values() if d[0] == 36000)
        total_entry += n_entry
        total_mid += n_mid
        total_seniors += n_senior
        if n_senior:
            senior_months.append(seed)
        if n_entry == 2:
            two_entry_months.append(seed)
        if n_mid == 2:
            two_mid_months.append(seed)
        tiers = {d[0] for d in drivers.values()}
        if tiers == {14000, 23000}:
            entry_mid_months.append(seed)
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
    check(total_drivers == 7,
          "live: seven taxi drivers in all across the"
          " four months",
          str(total_drivers))
    check((total_entry, total_mid, total_seniors) == (2, 5, 0),
          "live: two entry, five mid, zero senior drivers"
          " across the four months",
          str((total_entry, total_mid, total_seniors)))
    check(f"{econ.taxi_weather_factor(5, 6):.4f}" == "1.1417",
          "live: the ne-probe-1117 month is factor 1.1417 to"
          " four places")
    check(senior_months == [],
          "live: no month holds a senior driver — the senior"
          " gross at 1.1417 stays tool-computed only",
          str(senior_months))
    check(total_seniors == 0,
          "live: zero senior settlements in the NE hunt",
          str(total_seniors))
    check(sorted(two_entry_months) == ["ne-probe-1117"],
          "live: exactly one month holds two entries",
          str(sorted(two_entry_months)))
    check(sorted(two_mid_months) == ["ne-probe-1532"],
          "live: exactly one month holds two mid drivers",
          str(sorted(two_mid_months)))
    check(sorted(entry_mid_months) == ["ne-probe-1117"],
          "live: exactly one month holds entry + mid",
          str(sorted(entry_mid_months)))
    check(all_three == [],
          "live: no month holds all three tiers",
          str(all_three))
    check(sum(1 for _, (_, _, _, expected) in
              EXPECTED_LIVE.items()
              for band, _ in expected.values()
              if band == 14000) == 2,
          "live: exactly two entry settlements in the NE"
          " hunt (ne-probe-1117 x2)",
          "NEX000002, NEX000012")
    check(sum(1 for _, (_, _, _, expected) in
              EXPECTED_LIVE.items()
              for band, _ in expected.values()
              if band == 23000) == 5,
          "live: exactly five mid settlements in the NE"
          " hunt (ne-probe-1117, ne-probe-1459,"
          " ne-probe-1532 x2, ne-probe-1751)",
          "NEX000043, NEX000021, NEX000029, NEX000058,"
          " NEX000042")
    # The 5/6 mix now has a second live instance, from
    # different day positions, so the settlement keys on
    # the counts, not the positions.
    check(EXPECTED_LIVE["ne-probe-1117"][0]
          == EXPECTED_LIVE["ne-probe-1751"][0]
          == (5, 6),
          "live: ne-probe-1117 and ne-probe-1751 share the"
          " 5/6 mix",
          str([EXPECTED_LIVE[s][0]
               for s in ("ne-probe-1117", "ne-probe-1751")]))
    check(EXPECTED_LIVE["ne-probe-1117"][1]
          != EXPECTED_LIVE["ne-probe-1751"][1],
          "live: the two 5/6 months sit at different day"
          " positions",
          str([EXPECTED_LIVE[s][1]
               for s in ("ne-probe-1117", "ne-probe-1751")]))

    # 6. The gap claim, checked against the sweep tables
    # per the NB lesson: no month in the record held a
    # settlement at 1.1417 at any tier. The factor column
    # of every sweep table tops out at 1.1333, and 1.1417
    # appears before §51 only as the factor above the new
    # top.
    pre51 = report.split("## 51.")[0]
    # The §16 NE paragraph is the new record itself, so
    # the "above the new top" check reads the text without
    # it.
    ne_para_start = pre51.find(
        "**Taxi surge at the factor above the new top, 1.1417")
    ne_para_end = pre51.find(
        "The entry driver's uplift appears only under the"
        " surge", ne_para_start)
    without_ne = (pre51[:ne_para_start]
                  + pre51[ne_para_end:])
    rows = [ln for ln in pre51.splitlines()
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
    check(max(factors) == 1.1333,
          "record: the factor column of every sweep table"
          " tops out at 1.1333",
          str(sorted(set(factors))))
    check(all("1.1417" not in ln for ln in rows),
          "record: no sweep-table row holds a settlement at"
          " 1.1417",
          str([ln for ln in rows if "1.1417" in ln]))
    # The phrase is "above the new top" in §50 and §16, and
    # it wraps across line breaks in two places, so the
    # check reads the flattened prose and looks back 200
    # characters from each mention for the form — no
    # measured fact changed (same class as Queue 55's §44
    # wrap, Queue 59's §47 wrap, Queue 60's §49 wrap and
    # Queue 61's §50 wrap).
    without_ne_flat = " ".join(without_ne.split())
    mentions = [m.start() for m in
                re.finditer("1.1417", without_ne_flat)]
    check(len(mentions) > 0
          and all(re.search(r"above the new top",
                            without_ne_flat[
                                max(0, pos - 200):pos])
                  for pos in mentions),
          "record: every other pre-§51 mention of 1.1417 is"
          " the factor-above-the-new-top prose",
          str([without_ne_flat[max(0, pos - 60):pos + 6]
               for pos in mentions
               if not re.search(
                   r"above the new top", without_ne_flat[
                       max(0, pos - 200):pos])]))

    # 7. The V7 report §51: prose matches the measurement.
    check("## 51. Addendum — Senior taxi settlement at"
          " 1.1417, weather-first: the senior stays"
          " tool-computed only; the entry and mid tiers"
          " settle live (Unit NE, Queue 62)" in report,
          "report §51: the addendum exists")
    s51 = report.split("## 51.")[1]
    s51_flat = " ".join(s51.split())
    check("ne-probe-1117" in s51 and "ne-probe-1751" in s51,
          "report §51: the 5/6 probe seeds are named")
    check("ne-probe-1459" in s51 and "ne-probe-1532" in s51,
          "report §51: the 7/5 and 9/4 probe seeds are named")
    check("NEX000002" in s51 and "NEX000012" in s51
          and "NEX000043" in s51,
          "report §51: the ne-probe-1117 drivers are named")
    check("NEX000021" in s51 and "NEX000029" in s51
          and "NEX000058" in s51 and "NEX000042" in s51,
          "report §51: the mid drivers are named")
    check("1.1417" in s51,
          "report §51: the new factor is quoted")
    check("15,983" in s51 and "26,258" in s51
          and "41,100" in s51,
          "report §51: all three surged grosses are quoted")
    check("15983.333333333336" in s51
          and "26258.333333333336" in s51
          and "41100.00000000001" in s51
          and "41100.0" in s51,
          "report §51: the rounding cases are quoted")
    check("no senior" in s51_flat,
          "report §51: no senior in the hunt is recorded")
    check("tool-computed only" in s51_flat,
          "report §51: the senior stays tool-computed only")
    check("does NOT move" in s51_flat
          and MN_MD5 in s51 and MN_SH_MD5 in s51,
          "report §51: the md5 standing is recorded")
    check("| 1.1417 | entry | 15,983 | 7,740 | +1,983 | +1,240 |"
          in s51,
          "report §51: the per-factor entry row is printed")
    check("| 1.1417 | mid | 26,258 | 13,905 | +3,258 | +1,955 |"
          in s51,
          "report §51: the per-factor mid row is printed")
    check("| 1.1417 | senior | 41,100 | 22,755 | +5,100 |"
          " +3,005 |" in s51,
          "report §51: the per-factor senior row is printed")
    check("0.2% hit rate" in s51_flat,
          "report §51: the scan hit rate is recorded")
    check("ne-probe-1" in s51 and "ne-probe-2000" in s51,
          "report §51: the full scan range is recorded")
    check("rain + 2 × storm = 17" in s51_flat,
          "report §51: the pre-filter signature is recorded")
    check("nine live factors" in s51_flat,
          "report §51: the surge still rests on nine live"
          " factors")
    check("extends one step above the old top" in s51_flat
          and "1..17" in s51_flat,
          "report §51: the ladder now runs 1..17")
    check("Queue 63 Unit NF" in s51_flat,
          "report §51: the open 1.1500 hunt is recorded")
    check("1.1500" in s51_flat,
          "report §51: the factor above the new top is"
          " recorded")
    check("eleventh time" in s51_flat,
          "report §51: the pre-filter is verified an"
          " eleventh time")
    check("different day positions" in s51_flat,
          "report §51: the counts-not-positions finding is"
          " recorded")
    check("gap was real" in s51_flat,
          "report §51: the prior-months check is stated")
    # The "No month holds all three tiers" string wraps
    # across a line break in §51, so the check reads the
    # flattened prose — no measured fact changed (same class
    # as Queue 55's §44 wrap, Queue 59's §47 wrap, Queue
    # 60's §49 wrap and Queue 61's §50 wrap).
    check("No month holds all three tiers" in s51_flat,
          "report §51: no all-three-tiers month is recorded")
    check("nf-probe-668" in s51_flat,
          "report §51: the NF feasibility seed is named")
    check("| ne-probe-1117 | 5 | 6 | 1.1417 | entry: 15,983"
          " × 2, mid: 26,258 |" in s51,
          "report §51: the ne-probe-1117 scan row is printed")
    check("| ne-probe-1459 | 7 | 5 | 1.1417 | mid: 26,258 |"
          in s51,
          "report §51: the ne-probe-1459 scan row is printed")
    check("| ne-probe-1532 | 9 | 4 | 1.1417 | mid: 26,258"
          " × 2 |" in s51,
          "report §51: the ne-probe-1532 scan row is printed")
    check("| ne-probe-1751 | 5 | 6 | 1.1417 | mid: 26,258 |"
          in s51,
          "report §51: the ne-probe-1751 scan row is printed")
    # The "Unit NE, Queue 62, §51" string wraps across a
    # line break in §16, so the check reads the flattened
    # prose — no measured fact changed (same class as
    # Queue 55's §44 wrap, Queue 59's §47 wrap, Queue 60's
    # §49 wrap and Queue 61's §50 wrap).
    s16_flat = " ".join(report.split("## 16.")[1]
                        .split("## 17.")[0].split())
    check("Unit NE, Queue 62, §51" in s16_flat,
          "report §16: the NE update is recorded")
    check("NEX000002" in report.split("## 16.")[1]
          .split("## 17.")[0],
          "report §16: the live entry driver is named")

    # 8. GDD-03 §2 records the NE update.
    check("Unit NE · Queue 62" in gdd03,
          "GDD-03 §2: the NE update is recorded")
    check("NEX000002" in gdd03,
          "GDD-03 §2: the live entry driver is named")
    check("does NOT move" in gdd03,
          "GDD-03 §2: the md5 standing is recorded")

    # 9. The economy_sim.py comments record the NE outcome.
    check("Queue 62 Unit NE" in sim_src,
          "tool: the comments name the NE decision")
    check("report §51" in sim_src,
          "tool: the comments record §51")
    check("ne-probe-1117" in sim_src,
          "tool: the comments name the 5/6 seed")
    check("ne-probe-1751" in sim_src,
          "tool: the comments name the second 5/6 seed")

    # 10. Tests pin the NE figures.
    check("test_taxi_surge_entry_mid_settle_live_at_11417"
          in regress,
          "tests: the entry-mid-settle-live-at-1.1417 test"
          " exists")
    check("15983, 7740" in regress and "26258, 13905" in regress
          and "41100, 22755" in regress,
          "tests: the new-factor grosses and nets are pinned")
    check("1983, 3258, 5100" in regress,
          "tests: the per-tier deltas are pinned")
    check("41100.0" in regress,
          "tests: the exact senior product is pinned")

    # 11. Scope: only the NE files changed for this unit.
    # The grep matches the unit commit only: the queue-tick
    # commit shares the "Queue 62 NE:" prefix but carries
    # bookkeeping (STATUS.md + WORK-QUEUE.md), not unit files.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H",
         "--grep=^Queue 62 NE: senior taxi settlement at 1.1417",
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
                    "tools/verify_queue62_ne.py"},
          "scope: only the five NE files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
