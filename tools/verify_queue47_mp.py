"""Verify Queue 47 Unit MP — Taxi Surge at a Second Weather
Factor (MO follow-up).

Checks the corroboration against its sources:
tools/sim/engine.py (the settlement scales a taxi driver's
gross by taxi_factor = 1 + 0.25 x rain_days/30 + 0.5 x
storm_days/30, rounded to an integer, in the SYS-EMPLOYERS
branch only), tools/economy_sim.py (a comment only — the
tool's formula already reproduces the settled grosses, so
no tool change and the pinned md5 does NOT move),
tools/sim/tests/test_no_regression.py (a new test pins the
two new factors, the per-tier grosses and nets, the
rounding in both directions and the per-tier deltas),
docs/ECONOMY-SIM-REPORT-V7.md §36 (the prose matches the
measurement, including the per-tier table) and §16 (the
new factors and their per-tier deltas are recorded), and
docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the MP update).
Re-runs both fresh seeded live months live (seeds
mo-probe-1 and mo-probe-2, 60 population, 32 days each)
and asserts the recorded weather counts and settled taxi
grosses. Prints one line per check and a summary; exits 0
only when every check passes.
Run from the repo root: python3 tools/verify_queue47_mp.py
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

    # 2. The tool's figures at the two new factors: the
    # gross is round(band x factor), the nets follow with
    # tax and uplift recomputed, the trajectory ends at net.
    check(abs(econ.taxi_weather_factor(1, 2)
              - 1.0416666666666667) < 1e-12,
          "tool: the mo-probe-1 factor is 1.0417")
    check(abs(econ.taxi_weather_factor(4, 3)
              - 1.0833333333333335) < 1e-12,
          "tool: the mo-probe-2 factor is 1.0833")
    prices = econ.load("prices.json")
    wages = {w["profession_id"]: w
             for w in prices["wages_monthly"]}
    for (rain, storm), rows in (
            ((1, 2), (("entry", 14583, 6879, 583),
                      ("mid", 23958, 12525, 958),
                      ("senior", 37500, 20650, 1500))),
            ((4, 3), (("entry", 15167, 7251, 1167),
                      ("mid", 24917, 13100, 1917),
                      ("senior", 39000, 21550, 3000)))):
        for tier, gross, net, delta in rows:
            flat = econ.simulate(prices, wages["taxi_driver"],
                                 tier)
            surged = econ.simulate(
                prices, wages["taxi_driver"], tier,
                taxi_rain_days=rain, taxi_storm_days=storm)
            check(surged["gross"] == gross,
                  f"tool: {rain}/{storm} {tier} gross is {gross}",
                  str(surged["gross"]))
            check(surged["net"] == net,
                  f"tool: {rain}/{storm} {tier} net is {net}",
                  str(surged["net"]))
            check(surged["gross"] - flat["gross"] == delta,
                  f"tool: {rain}/{storm} {tier} delta is {delta}",
                  str(surged["gross"] - flat["gross"]))
            check(surged["end_balance"] == surged["net"],
                  f"tool: {rain}/{storm} {tier} ends at net",
                  str(surged["end_balance"]))
            check(surged["min_balance"] == 0,
                  f"tool: {rain}/{storm} {tier} minbal is 0",
                  str(surged["min_balance"]))
    # The rounding agrees in both directions.
    check(round(14000 * econ.taxi_weather_factor(1, 2)) == 14583
          and 14000 * econ.taxi_weather_factor(1, 2) < 14583.5,
          "tool: 14,000 x 1.0417 rounds down to 14,583")
    check(round(23000 * econ.taxi_weather_factor(4, 3)) == 24917
          and 23000 * econ.taxi_weather_factor(4, 3) > 24916.5,
          "tool: 23,000 x 1.0833 rounds up to 24,917")

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
    check("mo-probe" not in d1_text,
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

    # 4. Live re-derivation of both fresh months.
    for seed, weather, rain_idx, storm_idx, count, settled in (
            ("mo-probe-1", (1, 2), [9], [6, 28], 4,
             [14583, 23958, 37500]),
            ("mo-probe-2", (4, 3), [0, 3, 9, 15], [4, 5, 28], 2,
             [24917, 39000])):
        rain, storm, r_idx, s_idx, drivers = _measure(seed)
        factor = econ.taxi_weather_factor(rain, storm)
        check((rain, storm) == weather,
              f"live {seed}: month 1 has {weather[0]} rain days"
              f" and {weather[1]} storm days",
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

    # 5. The V7 report §36: prose matches the measurement.
    check("## 36. Addendum — Taxi surge at a second weather"
          " factor (Unit MP, Queue 47)" in report,
          "report §36: the addendum exists")
    s36 = report.split("## 36.")[1]
    s36_flat = " ".join(s36.split())
    check("mo-probe-1" in s36 and "mo-probe-2" in s36,
          "report §36: both probe seeds are named")
    check("1.0417" in s36 and "1.0833" in s36,
          "report §36: both new factors are quoted")
    check("14,583" in s36 and "23,958" in s36
          and "37,500" in s36 and "15,167" in s36
          and "24,917" in s36 and "39,000" in s36,
          "report §36: all six settled grosses are quoted")
    check("14,583.33" in s36 and "24,916.67" in s36,
          "report §36: the rounding cases are quoted")
    check("does NOT move" in s36_flat
          and MN_MD5 in s36 and MN_SH_MD5 in s36,
          "report §36: the md5 standing is recorded")
    check("| 1.0417 | entry | 14,583 | 6,879 | +583 | +379 |"
          in s36,
          "report §36: the per-factor table is printed")
    check("1.0417" in report.split("## 16.")[1]
          .split("## 17.")[0]
          and "1.0833" in report.split("## 16.")[1]
          .split("## 17.")[0],
          "report §16: the new factors are recorded")
    check("+1,167 / +1,917 / +3,000" in report.split(
        "## 16.")[1].split("## 17.")[0],
        "report §16: the 1.0833 per-tier deltas are quoted")

    # 6. GDD-03 §2 records the MP update.
    check("Unit MP · Queue 47" in gdd03,
          "GDD-03 §2: the MP update is recorded")
    check("1.0417" in gdd03 and "1.0833" in gdd03,
          "GDD-03 §2: both new factors are quoted")
    check("does NOT move" in gdd03,
          "GDD-03 §2: the md5 standing is recorded")

    # 7. The economy_sim.py comments record the MP outcome.
    check("Queue 47 Unit MP" in sim_src,
          "tool: the comments name the MP decision")
    check("report §36" in sim_src,
          "tool: the comments record §36")
    check("mo-probe-1" in sim_src and "mo-probe-2" in sim_src,
          "tool: the comments name both probe seeds")

    # 8. Tests pin the MP figures.
    check("test_taxi_surge_at_second_weather_factors_is_measured"
          in regress,
          "tests: the second-factor surge test exists")
    check("14583, 6879" in regress and "23958, 12525" in regress
          and "37500, 20650" in regress
          and "15167, 7251" in regress
          and "24917, 13100" in regress
          and "39000, 21550" in regress,
          "tests: the new-factor grosses and nets are pinned")
    check("583, 958, 1500" in regress
          and "1167, 1917, 3000" in regress,
          "tests: the per-tier deltas are pinned")

    # 9. Scope: only the MP files changed for this unit.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 47 MP:",
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
                    "tools/verify_queue47_mp.py"},
          "scope: only the five MP files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
