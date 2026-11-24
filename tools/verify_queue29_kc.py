"""Verify Queue 29 Unit KC — Taxi Weather Surge in the Tool's
Taxi Rows (KB follow-up).

Checks the model against its sources: tools/sim/engine.py (the
settlement scales a taxi driver's gross by taxi_factor = 1 +
0.25 × rain_days/30 + 0.5 × storm_days/30, in the SYS-EMPLOYERS
branch only), tools/economy_sim.py (simulate(..., taxi_rain_
days=..., taxi_storm_days=...) scales the taxi gross by the
settlement's formula, tax and uplift recomputed on the surged
gross; the rental stays flat; the bridge check stays flat
because the factor is >= 1, so the flat lines are the
conservative case),
tools/sim/tests/test_no_regression.py (the pinned md5 moves to
the KC baseline, the KA md5 kept as history; new tests pin the
measured figures, the refusals and the printed section),
docs/ECONOMY-SIM-REPORT-V7.md §16 (the prose matches the tool
output, including the surged early dips), and docs/GDD-03-
ECONOMY-AND-PROFESSIONS.md §2 (the KC update). Re-runs the EY
live month live (seed ey-measure, 60 population, 32 days) and
asserts the recorded weather counts and settled taxi grosses.
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue29_kc.py
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

KA_MD5 = "5f50931cbaad263812473ce1c7830e59"


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def _measure():
    """The EY live month, re-run: returns (rain days, storm
    days, {cid: (band, settled gross, employer_business_id)},
    the Priya-household taxi earner's settled gross)."""
    from tools.sim.engine import Simulation
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(db_path)
    sim = Simulation(db_path, seed="ey-measure")
    sim.generate_population(60)
    sim.run_days(32)
    store = sim.store
    presets = [sim.weather_for_day(d) for d in range(30)]
    rain = presets.count("rain")
    storm = presets.count("storm")
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
    priya = drivers.get("NEX000041")
    sim.close()
    os.remove(db_path)
    return rain, storm, drivers, priya


def main():
    from tools import economy_sim as econ
    sim_src = (ROOT / "tools" / "economy_sim.py").read_text()
    regress = (ROOT / "tools" / "sim" / "tests"
               / "test_no_regression.py").read_text()
    report = (ROOT / "docs" / "ECONOMY-SIM-REPORT-V7.md").read_text()
    gdd03 = (ROOT / "docs" / "GDD-03-ECONOMY-AND-PROFESSIONS.md").read_text()
    engine_src = (ROOT / "tools" / "sim" / "engine.py").read_text()

    # 1. The settlement's rule, read from the source: the factor
    # is defined once and applied once, in the SYS-EMPLOYERS
    # branch of _settle_month — not in _pay_business_wages.
    check(engine_src.count("taxi_factor") == 2,
          "source: taxi_factor is defined once and used once"
          " in engine.py", str(engine_src.count("taxi_factor")))
    check("taxi_factor = 1 + 0.25 * rain_days / 30 + 0.5"
          " * storm_days / 30" in engine_src,
          "source: the factor formula is the settlement's own")
    check("gross = round(gross * taxi_factor)" in engine_src,
          "source: the factor scales the taxi gross")
    check("taxi_factor" not in engine_src.split(
        "def _pay_business_wages")[1].split("def _pay_government")[0],
        "source: _pay_business_wages applies no surge")

    # 2. The measured figures, from the tool itself — the
    # single-earner taxi rows at the EY month's weather.
    prices = econ.load("prices.json")
    wages = {w["profession_id"]: w
             for w in prices["wages_monthly"]}
    weather = {"taxi_rain_days":
               econ.TAXI_WEATHER_MEASURED_RAIN_DAYS,
               "taxi_storm_days":
               econ.TAXI_WEATHER_MEASURED_STORM_DAYS}
    check(econ.taxi_weather_factor(2, 2) == 1.05,
          "tool: the EY weather factor is exactly 1.05")
    for tier, gross, tax, uplift, net in (
            ("entry", 14700, 0, 245, 6955),
            ("mid", 24150, 457, 3552, 12641),
            ("senior", 37800, 1140, 8330, 20830)):
        row = econ.simulate(prices, wages["taxi_driver"], tier,
                            **weather)
        check(row["gross"] == gross,
              f"tool: surged {tier} gross is {gross}",
              str(row["gross"]))
        check(row["tax"] == tax,
              f"tool: surged {tier} tax is {tax}", str(row["tax"]))
        check(row["uplift"] == uplift,
              f"tool: surged {tier} uplift is {uplift}",
              str(row["uplift"]))
        check(row["net"] == net,
              f"tool: surged {tier} net is {net}", str(row["net"]))
        check(row["end_balance"] == row["net"],
              f"tool: surged {tier} trajectory ends at net",
              str(row["end_balance"]))
        check(row["taxi_factor"] == 1.05,
              f"tool: surged {tier} row carries factor 1.05")
    cab = prices["taxi_fares"]["cab_rental_ncr_per_day"]
    renting = econ.simulate(prices, wages["taxi_driver"], "entry",
                            extra_daily_cost=cab,
                            label_suffix=" (renting cab)", **weather)
    check((renting["gross"], renting["net"]) == (14700, 1755),
          "tool: surged renting entry is 14700 / 1755",
          f"{renting['gross']} / {renting['net']}")
    check(renting["extra"] == 5200,
          "tool: the rental stays the flat 5200 under the surge")

    # 3. The taxi second earner: the surge shrinks both early
    # dips but closes neither; the measured position dips
    # nothing flat or surged; the nets rise by the second
    # earner's gain.
    w = wages["construction_worker"]
    for kw, tier, dip, surged_dip, net, surged_net in (
            ({"second_earner": "taxi_driver"}, "senior",
             -72, -42, 17401, 17856),
            ({"second_earner": "taxi_driver",
              "second_earner_tier": "mid",
              "second_earner_renting_cab": True}, "senior",
             -56, -9, 17651, 18342)):
        flat = econ.simulate(prices, w, tier,
                             storm_days=econ.STORM_EARLY_DAYS, **kw)
        surged = econ.simulate(
            prices, w, tier, storm_days=econ.STORM_EARLY_DAYS,
            **weather, **kw)
        check(flat["min_balance"] == dip,
              f"tool: flat early dip is {dip} ({tier})",
              str(flat["min_balance"]))
        check(surged["min_balance"] == surged_dip,
              f"tool: surged early dip is {surged_dip} ({tier})",
              str(surged["min_balance"]))
        check((flat["net"], surged["net"]) == (net, surged_net),
              f"tool: nets are {net} -> {surged_net} ({tier})",
              f"{flat['net']} -> {surged['net']}")
    # The surge never deepens a dip: the flat bridge lines are
    # the conservative case.
    worst_flat = min(econ.simulate(
        prices, w, tier, storm_days=pos,
        second_earner="taxi_driver",
        second_earner_tier="mid",
        second_earner_renting_cab=True)["min_balance"]
        for tier in ("entry", "mid", "senior")
        for pos in (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                    econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS))
    worst_surged = min(econ.simulate(
        prices, w, tier, storm_days=pos,
        second_earner="taxi_driver",
        second_earner_tier="mid",
        second_earner_renting_cab=True,
        **weather)["min_balance"]
        for tier in ("entry", "mid", "senior")
        for pos in (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                    econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS))
    check(worst_flat == -56 and worst_surged == -9,
          "tool: worst renting dip shrinks -56 -> -9, never"
          " deepens", f"{worst_flat} -> {worst_surged}")

    # 4. The default run: the md5 moves to the KC baseline
    # (the pin in test_no_regression.py, read live — not a
    # literal in this script); the KC section is printed; the
    # KA bridge line is unchanged; nothing fails.
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py")],
        capture_output=True, cwd=ROOT)
    check(out.returncode == 0, "tool: default run exits 0")
    text = out.stdout.decode()
    md5 = hashlib.md5(out.stdout).hexdigest()
    pinned = re.search(
        r'ECONOMY_SIM_BASELINE_MD5 = "([0-9a-f]{32})"',
        regress).group(1)
    check(md5 == pinned,
          "tool: default-run md5 equals the pinned baseline",
          md5)
    check(pinned != KA_MD5,
          "tool: the pinned md5 moved from the KA baseline",
          pinned)
    check(KA_MD5 in regress,
          "tests: the KA md5 is kept as history")
    check("taxi weather-surge month (Unit KC — the EY month's "
          "weather: 2 rain days, 2 storm days, taxi_factor"
          " 1.05" in text,
          "tool: the KC single-earner section is printed")
    check("taxi_driver                  entry        14000"
          "   14700     6500       6955      +455" in text,
          "tool: the KC entry row is printed")
    check("taxi-driver (mid, renting)   senior         -56"
          "           -9    17651      18342" in text,
          "tool: the KC renting senior row is printed")
    check("construction_worker + taxi-driver (mid, renting)"
          " start  10000 + renting dip     -56 =    9944  OK"
          "  (worst renting storm position)" in text,
          "tool: the KA renting bridge line is unchanged")
    check("BRIDGE FAIL rows: []" in text,
          "tool: no bridge failure in any position")

    # 5. Live re-derivation of the EY live month.
    rain, storm, drivers, priya = _measure()
    check((rain, storm) == (2, 2),
          "live: month 1 has 2 rain days and 2 storm days",
          f"rain={rain} storm={storm}")
    check(len(drivers) == 6,
          "live: the month holds 6 taxi drivers",
          str(len(drivers)))
    check(all(d[3] is None for d in drivers.values()),
          "live: every taxi driver is SYS-EMPLOYERS-paid"
          " (no business employer)",
          str({k: v[3] for k, v in drivers.items()}))
    check(all(d[2] == ["SYS-EMPLOYERS"] for d in drivers.values()),
          "live: every settled wage comes from SYS-EMPLOYERS")
    ok = all(len(d[1]) == 1
             and d[1][0] == round(d[0] * 1.05)
             for d in drivers.values())
    check(ok,
          "live: every taxi driver settled at exactly band"
          " x 1.05",
          str({k: (v[0], v[1]) for k, v in drivers.items()}))
    check(sorted({d[1][0] for d in drivers.values()})
          == [14700, 24150, 37800],
          "live: the settled grosses are 14700 / 24150 /"
          " 37800",
          str(sorted({d[1][0] for d in drivers.values()})))
    check(priya is not None and priya[1] == [14700],
          "live: the Priya-household taxi earner (NEX000041)"
          " settled 14700", str(priya[1]) if priya else "")

    # 6. The V7 report §16: prose matches the tool output.
    check("## 16. Addendum — Taxi weather surge (Unit KC,"
          " Queue 29)" in report,
          "report §16: the addendum exists")
    check("2 rain days, 2 storm days" in report
          and "taxi_factor 1.05" in report,
          "report §16: the measured weather and factor are"
          " quoted")
    check("14,700 / 24,150 / 37,800" in report,
          "report §16: the settled grosses are quoted")
    check("−56 → −9" in report,
          "report §16: the renting senior dip is quoted")
    check(md5 in report,
          "report §16: the KC baseline md5 is quoted", md5)
    check(KA_MD5 in report,
          "report §16: the KA md5 is kept as history")
    check("DECIDED" in report.split("## 16.")[1],
          "report §16: the model-it decision is stated")

    # 7. GDD-03 §2 records the KC update.
    check("Unit KC · Queue 29" in gdd03,
          "GDD-03 §2: the KC update is recorded")
    check("taxi_factor 1.05" in gdd03 or "1.05" in gdd03,
          "GDD-03 §2: the measured factor is quoted")
    check("−56 → −9" in gdd03,
          "GDD-03 §2: the renting senior dip is quoted")

    # 8. Tests pin the KC figures and refusals.
    check("test_single_earner_taxi_surge_is_measured" in regress,
          "tests: the single-earner surge test exists")
    check("test_taxi_second_earner_surge_is_measured" in regress,
          "tests: the second-earner surge test exists")
    check("test_taxi_weather_refusals" in regress,
          "tests: the refusals test exists")
    check("test_taxi_surge_section_is_printed" in regress,
          "tests: the printed-section test exists")

    # 9. Scope: only the KC files changed for this unit.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 29 KC:",
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
                    "tools/verify_queue29_kc.py"},
          "scope: only the five KC files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
