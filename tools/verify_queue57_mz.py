"""Verify Queue 57 Unit MZ — Senior Taxi Settlement at
1.1250, Wider Weather-First Scan: the hunt finds no
senior again; both lower tiers settle live from a third
mix (MY follow-up).

Checks the corroboration against its sources:
tools/sim/engine.py (the settlement scales a taxi driver's
gross by taxi_factor = 1 + 0.25 x rain_days/30 + 0.5 x
storm_days/30, rounded to an integer, in the SYS-EMPLOYERS
branch only), tools/economy_sim.py (a comment only — the
tool's formula already reproduces the settled grosses, so
no tool change and the pinned md5 does NOT move),
tools/sim/tests/test_no_regression.py (a new test pins the
1.1250 factor from the MZ mix, the per-tier grosses and
nets, the rounding no-op at every tier, the per-tier
deltas, and the live entry/mid settlements with the senior
still tool-computed),
docs/ECONOMY-SIM-REPORT-V7.md §46 (the prose matches the
measurement, including the per-tier table, the full
four-hundred-seed scan table and the three live
settlements) and §16 (the 1.1250 wider-hunt update is
recorded), and
docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the MZ update).
Re-runs the weather-only scan over the four hundred fresh
seeds and the one matching month live (seed mz-probe-397,
60 population, 32 days each) and asserts the recorded
weather counts and settled taxi grosses.
Prints one line per check and a summary; exits 0 only when
every check passes.
Run from the repo root: python3 tools/verify_queue57_mz.py
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
    each of the 400 fresh seeds, read from the seed alone
    (SimRng.stream("weather", day_index) is keyed by the
    seed, not by the population). Returns
    {seed: (rain, storm, rain indices, storm indices)} for
    the seeds matching rain + 2 x storm == 15."""
    from tools.sim.engine import WEATHER_WEIGHTS
    from tools.sim.rng import SimRng
    names = [n for n, _ in WEATHER_WEIGHTS]
    weights = [w for _, w in WEATHER_WEIGHTS]
    matches = {}
    for i in range(1, 401):
        seed = f"mz-probe-{i}"
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

    # 2. The tool's figures at the new factor, from the MZ
    # mix: the gross is round(band x factor), the nets
    # follow with tax and uplift recomputed, the trajectory
    # ends at net.
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
        surged = econ.simulate(
            prices, wages["taxi_driver"], tier,
            taxi_rain_days=7, taxi_storm_days=4)
        check(surged["gross"] == gross,
              f"tool: 7/4 {tier} gross is {gross}",
              str(surged["gross"]))
        check(surged["net"] == net,
              f"tool: 7/4 {tier} net is {net}",
              str(surged["net"]))
        check(surged["gross"] - flat["gross"] == delta,
              f"tool: 7/4 {tier} delta is {delta}",
              str(surged["gross"] - flat["gross"]))
        check(surged["end_balance"] == surged["net"],
              f"tool: 7/4 {tier} ends at net",
              str(surged["end_balance"]))
        check(surged["min_balance"] == 0,
              f"tool: 7/4 {tier} minbal is 0",
              str(surged["min_balance"]))
    # The rounding at 1.1250 is a no-op at every tier, from
    # the MZ mix: all three products are exact integers
    # (15,750.0, 25,875.0, 40,500.0).
    for band, gross in ((14000, 15750), (23000, 25875),
                        (36000, 40500)):
        product = band * econ.taxi_weather_factor(7, 4)
        check(product == float(gross)
              and round(product) == gross,
              f"tool: {band:,} x 1.1250 is exactly"
              f" {gross:,}.0 (no-op) from 7/4",
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
    check("mz-probe" not in d1_text,
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

    # 4. The weather-only scan: exactly one of the 400
    # fresh seeds matches rain + 2 x storm == 15, with the
    # recorded counts and day indices.
    scanned = _scan()
    expected_scan = {
        "mz-probe-397": (7, 4,
                         [0, 1, 10, 17, 18, 22, 29],
                         [9, 16, 23, 25]),
    }
    check(scanned == expected_scan,
          "scan: exactly the one recorded seed matches rain +"
          " 2 x storm == 15",
          str(sorted(scanned)))
    check(len(scanned) == 1,
          "scan: the hit rate is 1 in 400",
          str(len(scanned)))

    # 5. Live re-derivation of the one matching month.
    expected_live = {
        "mz-probe-397": ((7, 4),
                         [0, 1, 10, 17, 18, 22, 29],
                         [9, 16, 23, 25], 3,
                         {"NEX000010", "NEX000043",
                          "NEX000058"}),
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
        check(all(d[0] != 36000 for d in drivers.values()),
              f"live {seed}: no senior driver in this month",
              str(sorted({d[0] for d in drivers.values()})))
        check(sorted({d[0] for d in drivers.values()})
              == [14000, 23000],
              f"live {seed}: the drivers are entry and mid"
              " only",
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
              == [15750, 25875],
              f"live {seed}: the settled grosses are [15750,"
              " 25875]",
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
        for cid, band, gross in (
                ("NEX000010", 14000, 15750),
                ("NEX000058", 14000, 15750),
                ("NEX000043", 23000, 25875)):
            entry_ok = (drivers.get(cid, (None, [], [], None))[0]
                        == band
                        and drivers.get(cid, (None, [], [], None))[1]
                        == [gross])
            tier = "entry" if band == 14000 else "mid"
            check(entry_ok,
                  f"live {seed}: the {tier} driver is {cid},"
                  f" settled {gross:,}",
                  str({c: drivers.get(c) for c in (cid,)}))
    check(f"{econ.taxi_weather_factor(7, 4):.4f}" == "1.1250",
          "live: the mz-probe-397 month is factor 1.1250 to"
          " four places")
    # The MZ mix is the 7 + 4 mix MY already measured, but
    # from different day positions — the settlement keys on
    # the counts, not the positions.
    check(scanned["mz-probe-397"][2]
          != [9, 10, 13, 16, 20, 23, 24]
          and scanned["mz-probe-397"][3] != [2, 14, 17, 27],
          "live: the MZ day positions differ from"
          " my-probe-137's (same counts, new positions)",
          str(scanned["mz-probe-397"][2:]))

    # 6. The V7 report §46: prose matches the measurement.
    check("## 46. Addendum — Senior taxi settlement at"
          " 1.1250, wider weather-first scan: the hunt finds"
          " none again; both lower tiers settle live from a"
          " third mix (Unit MZ, Queue 57)"
          in report,
          "report §46: the addendum exists")
    s46 = report.split("## 46.")[1]
    s46_flat = " ".join(s46.split())
    check("mz-probe-397" in s46,
          "report §46: the probe seed is named")
    check("1.1250" in s46,
          "report §46: the new factor is quoted")
    check("15,750" in s46 and "25,875" in s46
          and "40,500" in s46,
          "report §46: all three surged grosses are quoted")
    check("15,750.0" in s46 and "25,875.0" in s46
          and "40,500.0" in s46,
          "report §46: the rounding cases are quoted")
    check("NEX000010" in s46 and "NEX000058" in s46
          and "NEX000043" in s46,
          "report §46: all three drivers are named")
    check("does NOT move" in s46_flat
          and MN_MD5 in s46 and MN_SH_MD5 in s46,
          "report §46: the md5 standing is recorded")
    check("| 1.1250 | entry | 15,750 | 7,601 | +1,750 |"
          " +1,101 |" in s46,
          "report §46: the per-factor entry row is printed")
    check("| 1.1250 | mid | 25,875 | 13,675 | +2,875 |"
          " +1,725 |" in s46,
          "report §46: the per-factor mid row is printed")
    check("0.25% hit rate" in s46_flat,
          "report §46: the scan hit rate is recorded")
    check("mz-probe-1" in s46 and "mz-probe-400" in s46,
          "report §46: the full scan range is recorded")
    check("rain + 2 × storm = 15" in s46_flat,
          "report §46: the pre-filter signature is recorded")
    check("nine live factors" in s46_flat,
          "report §46: the surge still rests on nine live"
          " factors")
    check("1.0750" in s46_flat and "no month in the record"
          " holds a senior" in s46_flat,
          "report §46: the 1.0750 senior gap is recorded")
    check("40,500 at 1.1250" in s46_flat
          and "still tool-computed only" in s46_flat,
          "report §46: the 1.1250 senior gap is recorded")
    check("Queue 58 Unit NA" in s46_flat,
          "report §46: the open still-wider senior hunt is"
          " recorded")
    check("sixth time" in s46_flat,
          "report §46: the pre-filter is verified a sixth"
          " time")
    check("different day positions" in s46_flat,
          "report §46: the counts-not-positions finding is"
          " recorded")
    check("| mz-probe-397 | 7 | 4 | 1.1250 | entry:"
          " 15,750 × 2, mid: 25,875 |" in s46,
          "report §46: the mz-probe-397 scan row is printed")
    check("Unit MZ, Queue 57, §46" in report.split("## 16.")[1]
          .split("## 17.")[0],
          "report §16: the MZ update is recorded")
    check("+1,750 / +2,875 / +4,500" in report.split(
        "## 16.")[1].split("## 17.")[0],
        "report §16: the 1.1250 per-tier deltas are quoted")

    # 7. GDD-03 §2 records the MZ update.
    check("Unit MZ · Queue 57" in gdd03,
          "GDD-03 §2: the MZ update is recorded")
    check("1.1250" in gdd03,
          "GDD-03 §2: the new factor is quoted")
    check("does NOT move" in gdd03,
          "GDD-03 §2: the md5 standing is recorded")

    # 8. The economy_sim.py comments record the MZ outcome.
    check("Queue 57 Unit MZ" in sim_src,
          "tool: the comments name the MZ decision")
    check("report §46" in sim_src,
          "tool: the comments record §46")
    check("mz-probe-397" in sim_src,
          "tool: the comments name the 1.1250 probe seed")

    # 9. Tests pin the MZ figures.
    check("test_taxi_surge_wider_scan_no_senior_at_11250"
          in regress,
          "tests: the wider-scan-no-senior-at-1.1250 test"
          " exists")
    check("15750, 7601" in regress and "25875, 13675" in regress
          and "40500, 22425" in regress,
          "tests: the new-factor grosses and nets are pinned")
    check("1750, 2875, 4500" in regress,
          "tests: the per-tier deltas are pinned")
    check("40500.0" in regress,
          "tests: the exact senior product is pinned")

    # 10. Scope: only the MZ files changed for this unit.
    # The grep matches the unit commit only: the queue-tick
    # commit shares the "Queue 57 MZ:" prefix but carries
    # bookkeeping (STATUS.md + WORK-QUEUE.md), not unit files.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H",
         "--grep=^Queue 57 MZ: senior taxi settlement at 1.1250",
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
                    "tools/verify_queue57_mz.py"},
          "scope: only the five MZ files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
