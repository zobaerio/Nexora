"""Verify Queue 58 Unit NA — Senior Taxi Settlement at
1.1250, Still-Wider Weather-First Scan: the senior settles
live at last; all three tiers live at the top step (MZ
follow-up).

Checks the corroboration against its sources:
tools/sim/engine.py (the settlement scales a taxi driver's
gross by taxi_factor = 1 + 0.25 x rain_days/30 + 0.5 x
storm_days/30, rounded to an integer, in the SYS-EMPLOYERS
branch only), tools/economy_sim.py (a comment only — the
tool's formula already reproduces the settled grosses, so
no tool change and the pinned md5 does NOT move),
tools/sim/tests/test_no_regression.py (a new test pins the
1.1250 factor from the NA mix, the per-tier grosses and
nets, the rounding no-op at every tier, the per-tier
deltas, and the live senior settlement),
docs/ECONOMY-SIM-REPORT-V7.md §47 (the prose matches the
measurement, including the per-tier table, the full
eight-hundred-seed scan table and the nineteen live
settlements) and §16 (the 1.1250 still-wider-hunt update
is recorded), and
docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the NA update).
Re-runs the weather-only scan over the eight hundred fresh
seeds and every matching month live (ten seeds, 60
population, 32 days each) and asserts the recorded
weather counts and settled taxi grosses.
Prints one line per check and a summary; exits 0 only when
every check passes.
Run from the repo root: python3 tools/verify_queue58_na.py
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

# The ten matching months, in scan order: seed ->
# ((rain, storm), rain day indices, storm day indices,
#  {character id: (wage band, settled gross)}).
EXPECTED_LIVE = {
    "na-probe-34": ((9, 3),
                    [2, 6, 11, 12, 15, 16, 20, 25, 28],
                    [1, 14, 19],
                    {"NEX000016": (23000, 25875)}),
    "na-probe-93": ((9, 3),
                    [3, 5, 7, 9, 11, 15, 20, 22, 23],
                    [6, 8, 28],
                    {"NEX000001": (23000, 25875)}),
    "na-probe-98": ((3, 6),
                    [8, 12, 28],
                    [9, 15, 19, 23, 27, 29],
                    {"NEX000001": (23000, 25875),
                     "NEX000042": (23000, 25875)}),
    "na-probe-129": ((3, 6),
                     [10, 18, 21],
                     [0, 17, 19, 24, 26, 29],
                     {"NEX000001": (23000, 25875),
                      "NEX000043": (36000, 40500),
                      "NEX000050": (23000, 25875),
                      "NEX000058": (14000, 15750)}),
    "na-probe-311": ((7, 4),
                     [0, 4, 7, 12, 15, 18, 21],
                     [3, 6, 10, 22],
                     {"NEX000025": (23000, 25875),
                      "NEX000029": (23000, 25875),
                      "NEX000059": (23000, 25875)}),
    "na-probe-341": ((5, 5),
                     [0, 4, 8, 26, 28],
                     [2, 13, 20, 22, 23],
                     {"NEX000007": (23000, 25875),
                      "NEX000011": (23000, 25875)}),
    "na-probe-389": ((5, 5),
                     [5, 9, 17, 22, 27],
                     [0, 3, 15, 25, 28],
                     {"NEX000027": (23000, 25875),
                      "NEX000057": (23000, 25875)}),
    "na-probe-439": ((3, 6),
                     [20, 26, 27],
                     [1, 6, 13, 18, 22, 28],
                     {"NEX000008": (23000, 25875)}),
    "na-probe-660": ((5, 5),
                     [9, 11, 12, 20, 23],
                     [0, 4, 6, 13, 21],
                     {"NEX000001": (23000, 25875)}),
    "na-probe-788": ((11, 2),
                     [3, 9, 13, 14, 15, 18, 19, 24, 26, 28, 29],
                     [8, 23],
                     {"NEX000048": (23000, 25875),
                      "NEX000052": (23000, 25875)}),
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
    the seeds matching rain + 2 x storm == 15."""
    from tools.sim.engine import WEATHER_WEIGHTS
    from tools.sim.rng import SimRng
    names = [n for n, _ in WEATHER_WEIGHTS]
    weights = [w for _, w in WEATHER_WEIGHTS]
    matches = {}
    for i in range(1, 801):
        seed = f"na-probe-{i}"
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

    # 2. The tool's figures at the new factor, from the NA
    # mix (3 rain + 6 storm, the senior month): the gross
    # is round(band x factor), the nets follow with tax and
    # uplift recomputed, the trajectory ends at net.
    check(econ.taxi_weather_factor(3, 6) == 1.125,
          "tool: the 3/6 factor is exactly 1.125",
          str(econ.taxi_weather_factor(3, 6)))
    prices = econ.load("prices.json")
    wages = {w["profession_id"]: w
             for w in prices["wages_monthly"]}
    for tier, gross, net, delta in (("entry", 15750, 7601, 1750),
                                    ("mid", 25875, 13675, 2875),
                                    ("senior", 40500, 22425, 4500)):
        flat = econ.simulate(prices, wages["taxi_driver"],
                             tier)
        surged = econ.simulate(
            prices, wages["taxi_driver"], tier,
            taxi_rain_days=3, taxi_storm_days=6)
        check(surged["gross"] == gross,
              f"tool: 3/6 {tier} gross is {gross}",
              str(surged["gross"]))
        check(surged["net"] == net,
              f"tool: 3/6 {tier} net is {net}",
              str(surged["net"]))
        check(surged["gross"] - flat["gross"] == delta,
              f"tool: 3/6 {tier} delta is {delta}",
              str(surged["gross"] - flat["gross"]))
        check(surged["end_balance"] == surged["net"],
              f"tool: 3/6 {tier} ends at net",
              str(surged["end_balance"]))
        check(surged["min_balance"] == 0,
              f"tool: 3/6 {tier} minbal is 0",
              str(surged["min_balance"]))
        check(surged["gross"]
              == round(flat["gross"]
                       * econ.taxi_weather_factor(3, 6)),
              f"tool: 3/6 {tier} gross is round(band x factor)",
              str(surged["gross"]))
    # The rounding at 1.1250 is a no-op at every tier, from
    # the NA mix: all three products are exact integers
    # (15,750.0, 25,875.0, 40,500.0).
    for band, gross in ((14000, 15750), (23000, 25875),
                        (36000, 40500)):
        product = band * econ.taxi_weather_factor(3, 6)
        check(product == float(gross)
              and round(product) == gross,
              f"tool: {band:,} x 1.1250 is exactly"
              f" {gross:,}.0 (no-op) from 3/6",
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
    # The factor keys on the counts, not the mix: all five
    # NA mixes land on exactly 1.125.
    check(all(econ.taxi_weather_factor(r, s) == 1.125
              for r, s in ((9, 3), (3, 6), (7, 4), (5, 5),
                           (11, 2))),
          "tool: all five NA mixes give factor exactly 1.125",
          str([econ.taxi_weather_factor(r, s)
               for r, s in ((9, 3), (3, 6), (7, 4), (5, 5),
                            (11, 2))]))

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
    check("na-probe" not in d1_text,
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

    # 4. The weather-only scan: exactly ten of the 800
    # fresh seeds match rain + 2 x storm == 15, with the
    # recorded counts and day indices.
    scanned = _scan()
    expected_scan = {
        seed: (counts[0], counts[1], r_idx, s_idx)
        for seed, (counts, r_idx, s_idx, _)
        in EXPECTED_LIVE.items()
    }
    check(scanned == expected_scan,
          "scan: exactly the ten recorded seeds match rain +"
          " 2 x storm == 15",
          str(sorted(scanned)))
    check(len(scanned) == 10,
          "scan: the hit rate is 10 in 800",
          str(len(scanned)))

    # 5. Live re-derivation of the ten matching months.
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
    check(total_drivers == 19,
          "live: nineteen taxi drivers in all across the ten"
          " months",
          str(total_drivers))
    check(total_seniors == 1,
          "live: exactly one senior driver across the ten"
          " months",
          str(total_seniors))
    check(f"{econ.taxi_weather_factor(3, 6):.4f}" == "1.1250",
          "live: the na-probe-129 month is factor 1.1250 to"
          " four places")
    # na-probe-129 is the only month holding a senior, and
    # the only month holding all three tiers.
    check(sorted({band for band, _ in
                  EXPECTED_LIVE["na-probe-129"][3].values()})
          == [14000, 23000, 36000],
          "live: na-probe-129 holds all three tiers",
          str(sorted({band for band, _ in
                      EXPECTED_LIVE["na-probe-129"][3]
                      .values()})))
    check(sum(1 for _, (_, _, _, expected) in
              EXPECTED_LIVE.items()
              for band, _ in expected.values()
              if band == 36000) == 1,
          "live: exactly one senior settlement in the record"
          " at 1.1250 (na-probe-129)",
          "NEX000043")
    # The 7 + 4 mix now has a third live instance, from
    # different day positions than mz-probe-397 and
    # my-probe-137 — the settlement keys on the counts,
    # not the positions.
    check(scanned["na-probe-311"][2]
          != [0, 1, 10, 17, 18, 22, 29]
          and scanned["na-probe-311"][2]
          != [9, 10, 13, 16, 20, 23, 24]
          and scanned["na-probe-311"][3] != [9, 16, 23, 25]
          and scanned["na-probe-311"][3] != [2, 14, 17, 27],
          "live: the NA 7/4 day positions differ from"
          " mz-probe-397's and my-probe-137's (same counts,"
          " new positions)",
          str(scanned["na-probe-311"][2:]))

    # 6. The V7 report §47: prose matches the measurement.
    check("## 47. Addendum — Senior taxi settlement at"
          " 1.1250, still-wider weather-first scan: the"
          " senior settles live at last; all three tiers"
          " live at the top step (Unit NA, Queue 58)"
          in report,
          "report §47: the addendum exists")
    s47 = report.split("## 47.")[1]
    s47_flat = " ".join(s47.split())
    check("na-probe-129" in s47,
          "report §47: the senior probe seed is named")
    check("NEX000043" in s47,
          "report §47: the senior driver is named")
    check("1.1250" in s47,
          "report §47: the new factor is quoted")
    check("15,750" in s47 and "25,875" in s47
          and "40,500" in s47,
          "report §47: all three surged grosses are quoted")
    check("15,750.0" in s47 and "25,875.0" in s47
          and "40,500.0" in s47,
          "report §47: the rounding cases are quoted")
    check("NEX000058" in s47 and "NEX000001" in s47
          and "NEX000050" in s47,
          "report §47: the other na-probe-129 drivers are"
          " named")
    check("does NOT move" in s47_flat
          and MN_MD5 in s47 and MN_SH_MD5 in s47,
          "report §47: the md5 standing is recorded")
    check("| 1.1250 | entry | 15,750 | 7,601 | +1,750 |"
          " +1,101 |" in s47,
          "report §47: the per-factor entry row is printed")
    check("| 1.1250 | mid | 25,875 | 13,675 | +2,875 |"
          " +1,725 |" in s47,
          "report §47: the per-factor mid row is printed")
    check("| 1.1250 | senior | 40,500 | 22,425 | +4,500 |"
          " +2,675 |" in s47,
          "report §47: the per-factor senior row is printed")
    check("1.25% hit rate" in s47_flat,
          "report §47: the scan hit rate is recorded")
    check("na-probe-1" in s47 and "na-probe-800" in s47,
          "report §47: the full scan range is recorded")
    check("rain + 2 × storm = 15" in s47_flat,
          "report §47: the pre-filter signature is recorded")
    check("nine live factors" in s47_flat,
          "report §47: the surge still rests on nine live"
          " factors")
    check("five live factors" in s47_flat,
          "report §47: the senior tier now rests on five"
          " live factors")
    check("1.0750" in s47_flat and "no month in the record"
          " holds a senior" in s47_flat,
          "report §47: the 1.0750 senior gap is recorded")
    check("Queue 59 Unit NB" in s47_flat,
          "report §47: the open 1.0750 senior hunt is"
          " recorded")
    check("seventh time" in s47_flat,
          "report §47: the pre-filter is verified a seventh"
          " time")
    check("different day positions" in s47_flat,
          "report §47: the counts-not-positions finding is"
          " recorded")
    check("| na-probe-129 | 3 | 6 | 1.1250 | entry:"
          " 15,750, mid: 25,875 × 2, senior: 40,500 |"
          in s47,
          "report §47: the na-probe-129 scan row is printed")
    check("| na-probe-34 | 9 | 3 | 1.1250 | mid: 25,875 |"
          in s47,
          "report §47: the na-probe-34 scan row is printed")
    check("| na-probe-788 | 11 | 2 | 1.1250 | mid:"
          " 25,875 × 2 |" in s47,
          "report §47: the na-probe-788 scan row is printed")
    check("Unit NA, Queue 58, §47" in report.split("## 16.")[1]
          .split("## 17.")[0],
          "report §16: the NA update is recorded")
    check("NEX000043" in report.split("## 16.")[1]
          .split("## 17.")[0],
          "report §16: the live senior driver is named")

    # 7. GDD-03 §2 records the NA update.
    check("Unit NA · Queue 58" in gdd03,
          "GDD-03 §2: the NA update is recorded")
    check("NEX000043" in gdd03,
          "GDD-03 §2: the live senior driver is named")
    check("does NOT move" in gdd03,
          "GDD-03 §2: the md5 standing is recorded")

    # 8. The economy_sim.py comments record the NA outcome.
    check("Queue 58 Unit NA" in sim_src,
          "tool: the comments name the NA decision")
    check("report §47" in sim_src,
          "tool: the comments record §47")
    check("na-probe-129" in sim_src,
          "tool: the comments name the 1.1250 senior seed")

    # 9. Tests pin the NA figures.
    check("test_taxi_surge_still_wider_scan_senior_settles"
          "_live_at_11250" in regress,
          "tests: the still-wider-scan-senior-settles-live"
          "-at-1.1250 test exists")
    check("15750, 7601" in regress and "25875, 13675" in regress
          and "40500, 22425" in regress,
          "tests: the new-factor grosses and nets are pinned")
    check("1750, 2875, 4500" in regress,
          "tests: the per-tier deltas are pinned")
    check("40500.0" in regress,
          "tests: the exact senior product is pinned")

    # 10. Scope: only the NA files changed for this unit.
    # The grep matches the unit commit only: the queue-tick
    # commit shares the "Queue 58 NA:" prefix but carries
    # bookkeeping (STATUS.md + WORK-QUEUE.md), not unit files.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H",
         "--grep=^Queue 58 NA: senior taxi settlement at 1.1250",
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
                    "tools/verify_queue58_na.py"},
          "scope: only the five NA files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
