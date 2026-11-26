"""Verify Queue 49 Unit MR — Taxi Surge in a Storm-Heavy
Month Above the Band (MQ follow-up).

Checks the corroboration against its sources:
tools/sim/engine.py (the settlement scales a taxi driver's
gross by taxi_factor = 1 + 0.25 x rain_days/30 + 0.5 x
storm_days/30, rounded to an integer, in the SYS-EMPLOYERS
branch only), tools/economy_sim.py (a comment only — the
tool's formula already reproduces the settled grosses, so
no tool change and the pinned md5 does NOT move),
tools/sim/tests/test_no_regression.py (a new test pins the
1.1083 factor from both weather mixes, the per-tier grosses
and nets, the rounding UP at both settled tiers and the
exact integer at the senior tier, and the per-tier deltas —
with the senior gross pinned as tool-computed, not
live-settled, and the two mixes settling identically),
docs/ECONOMY-SIM-REPORT-V7.md §38 (the prose matches the
measurement, including the per-tier table and the honest
senior limit) and §16 (the new factor and its per-tier
deltas are recorded), and
docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the MR update).
Re-runs both fresh seeded live months live (seeds
mq-probe-11 and mr-probe-7, 60 population, 32 days each)
and asserts the recorded weather counts and settled taxi
grosses. Prints one line per check and a summary; exits 0
only when every check passes.
Run from the repo root: python3 tools/verify_queue49_mr.py
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

    # 2. The tool's figures at the new factor: the gross is
    # round(band x factor), the nets follow with tax and
    # uplift recomputed, the trajectory ends at net — and
    # the two weather mixes land on the same factor and
    # give identical grosses.
    check(abs(econ.taxi_weather_factor(3, 5)
              - 1.1083333333333332) < 1e-12,
          "tool: the mq-probe-11 factor is 1.1083")
    check(abs(econ.taxi_weather_factor(9, 2)
              - 1.1083333333333334) < 1e-12,
          "tool: the mr-probe-7 factor is 1.1083")
    check(abs(econ.taxi_weather_factor(3, 5)
              - econ.taxi_weather_factor(9, 2)) < 1e-12,
          "tool: the two mixes land on the same factor")
    prices = econ.load("prices.json")
    wages = {w["profession_id"]: w
             for w in prices["wages_monthly"]}
    for (rain, storm), rows in (
            ((3, 5), (("entry", 15517, 7460, 1517),
                      ("mid", 25492, 13445, 2492),
                      ("senior", 39900, 22090, 3900))),
            ((9, 2), (("entry", 15517, 7460, 1517),
                      ("mid", 25492, 13445, 2492),
                      ("senior", 39900, 22090, 3900)))):
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
    # The rounding at 1.1083 goes UP at both settled tiers;
    # the senior product is an integer up to float error.
    check(15516.5 < 14000 * econ.taxi_weather_factor(3, 5)
          < 15517.5
          and round(14000 * econ.taxi_weather_factor(3, 5))
          == 15517,
          "tool: 14,000 x 1.1083 rounds up to 15,517")
    check(25491.5 < 23000 * econ.taxi_weather_factor(3, 5)
          < 25492.5
          and round(23000 * econ.taxi_weather_factor(3, 5))
          == 25492,
          "tool: 23,000 x 1.1083 rounds up to 25,492")
    check(abs(36000 * econ.taxi_weather_factor(3, 5) - 39900)
          < 1e-9
          and round(36000 * econ.taxi_weather_factor(3, 5))
          == 39900,
          "tool: 1.1083 senior product is an integer up to"
          " float error, so rounding is a no-op")
    check(econ.simulate(prices, wages["taxi_driver"], "mid",
                        taxi_rain_days=3, taxi_storm_days=5)
          ["gross"] == econ.simulate(
              prices, wages["taxi_driver"], "mid",
              taxi_rain_days=9, taxi_storm_days=2)["gross"],
          "tool: the two mixes give the same mid gross")

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
    check("mq-probe" not in d1_text and "mr-probe" not in d1_text,
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
    for seed, weather, rain_idx, storm_idx, count, bands, settled in (
            ("mq-probe-11", (3, 5),
             [2, 25, 26], [6, 8, 10, 14, 29], 1, (23000,),
             [25492]),
            ("mr-probe-7", (9, 2),
             [2, 5, 8, 10, 16, 19, 21, 26, 27], [14, 24], 2,
             (14000, 23000), [15517, 25492])):
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
              " driver" + ("s" if count > 1 else ""),
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
              f"live {seed}: the driver bands are {bands},"
              " no senior driver in the world",
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
    check(f"{econ.taxi_weather_factor(3, 5):.4f}" == "1.1083"
          and f"{econ.taxi_weather_factor(9, 2):.4f}" == "1.1083",
          "live: both months are factor 1.1083 to four places")

    # 5. The V7 report §38: prose matches the measurement.
    check("## 38. Addendum — Taxi surge in a storm-heavy"
          " month above the band (Unit MR, Queue 49)" in report,
          "report §38: the addendum exists")
    s38 = report.split("## 38.")[1]
    s38_flat = " ".join(s38.split())
    check("mq-probe-11" in s38 and "mr-probe-7" in s38,
          "report §38: both probe seeds are named")
    check("1.1083" in s38,
          "report §38: the new factor is quoted")
    check("25,492" in s38 and "15,517" in s38
          and "39,900" in s38,
          "report §38: all three surged grosses are quoted")
    check("15,516.67" in s38 and "25,491.67" in s38,
          "report §38: the rounding cases are quoted")
    check("does NOT move" in s38_flat
          and MN_MD5 in s38 and MN_SH_MD5 in s38,
          "report §38: the md5 standing is recorded")
    check("| 1.1083 | entry | 15,517 | 7,460 | +1,517 | +960 |"
          in s38,
          "report §38: the per-factor table is printed")
    check("tool-computed, not live-settled" in s38_flat
          and "still unmeasured" in s38_flat,
          "report §38: the senior limit is stated honestly")
    check("keys on the factor, not the mix" in s38_flat,
          "report §38: the mix-independence finding is stated")
    check("mr-probe-1" in s38 and "mr-probe-16" in s38
          and "1.0917" in s38 and "25,108" in s38,
          "report §38: the follow-up sweep is recorded")
    check("1.1083" in report.split("## 16.")[1]
          .split("## 17.")[0],
          "report §16: the new factor is recorded")
    check("+1,517 / +2,492 / +3,900" in report.split(
        "## 16.")[1].split("## 17.")[0],
        "report §16: the 1.1083 per-tier deltas are quoted")

    # 6. GDD-03 §2 records the MR update.
    check("Unit MR · Queue 49" in gdd03,
          "GDD-03 §2: the MR update is recorded")
    check("1.1083" in gdd03,
          "GDD-03 §2: the new factor is quoted")
    check("does NOT move" in gdd03,
          "GDD-03 §2: the md5 standing is recorded")

    # 7. The economy_sim.py comments record the MR outcome.
    check("Queue 49 Unit MR" in sim_src,
          "tool: the comments name the MR decision")
    check("report §38" in sim_src,
          "tool: the comments record §38")
    check("mq-probe-11" in sim_src and "mr-probe-7" in sim_src,
          "tool: the comments name both probe seeds")

    # 8. Tests pin the MR figures.
    check("test_taxi_surge_storm_heavy_month_is_measured"
          in regress,
          "tests: the storm-heavy surge test exists")
    check("15517, 7460" in regress and "25492, 13445" in regress
          and "39900, 22090" in regress,
          "tests: the new-factor grosses and nets are pinned")
    check("1517, 2492, 3900" in regress,
          "tests: the per-tier deltas are pinned")

    # 9. Scope: only the MR files changed for this unit.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 49 MR:",
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
                    "tools/verify_queue49_mr.py"},
          "scope: only the five MR files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
