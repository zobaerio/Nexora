"""Verify Queue 38 Unit MG — Multi-Seed Senior Second
Earner Sweep (MF follow-up).

Checks the decision against its sources: tools/sim/dataio.py
(TIER_WAGE_KEYS — tiers 3-5 are all paid at the senior band,
so "senior" in the live world means tier >= 3, not tier == 3),
data/prices.json (the senior bands: taxi 36,000, civil
engineer 65,000), tools/economy_sim.py (the MG comment now
records the sweep outcome — the pinned md5s do NOT move),
tools/sim/tests/test_economy_labour_banking.py (guard tests
pin the sweep method), docs/ECONOMY-SIM-REPORT-V7.md §27 (the
measured decision) and docs/GDD-03-ECONOMY-AND-PROFESSIONS.md
§2 (the MG update). Re-runs the live sweep (seeds mg-seed-1
.. mg-seed-5, 120 population, 90 days each) and asserts no
construction-worker-headed household has a senior taxi-driver
or senior civil-engineer second earner in any seed.
Prints one line per check and a summary; exits 0 only when
every check passes.
Run from the repo root: python3 tools/verify_queue38_mg.py
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

MC_MD5 = "a818a3273cdad108c4d8d4ae198b5b44"
SH_MD5 = "762a2b6395a1c83fc86f2b5f9c1839bc"

# The measured sweep, from the probe run: per seed, the
# household count, the construction-worker-headed count, the
# second earners found in those households (household,
# profession, tier, wage), the senior-band taxi-driver and
# civil-engineer counts, and the two target counts.
EXPECTED = {
    "mg-seed-1": {
        "households": 51, "cw_heads": 6,
        "second": [("HH000014", "software_developer", 2, 52000),
                   ("HH000043", "shop_owner", 3, 55000)],
        "senior_taxi": 1, "senior_ce": 2,
        "target_taxi": 0, "target_ce": 0},
    "mg-seed-2": {
        "households": 42, "cw_heads": 4,
        "second": [("HH000012", "software_developer", 2, 52000),
                   ("HH000032", "business_owner", 2, 110000),
                   ("HH000035", "construction_worker", 3, 20000)],
        "senior_taxi": 1, "senior_ce": 2,
        "target_taxi": 0, "target_ce": 0},
    "mg-seed-3": {
        "households": 45, "cw_heads": 3,
        "second": [("HH000002", "pilot", 2, 95000),
                   ("HH000002", "pilot", 1, 45000),
                   ("HH000020", "software_developer", 2, 52000),
                   ("HH000033", "software_developer", 2, 52000)],
        "senior_taxi": 2, "senior_ce": 2,
        "target_taxi": 0, "target_ce": 0},
    "mg-seed-4": {
        "households": 48, "cw_heads": 6,
        "second": [("HH000002", "business_owner", 3, 300000),
                   ("HH000018", "police_officer", 2, 28000),
                   ("HH000018", "pilot", 1, 45000),
                   ("HH000027", "police_officer", 2, 28000),
                   ("HH000036", "taxi_driver", 2, 23000)],
        "senior_taxi": 2, "senior_ce": 2,
        "target_taxi": 0, "target_ce": 0},
    "mg-seed-5": {
        "households": 48, "cw_heads": 8,
        "second": [("HH000014", "pilot", 2, 95000),
                   ("HH000025", "doctor", 2, 55000),
                   ("HH000031", "teacher", 2, 24000),
                   ("HH000035", "business_owner", 3, 300000),
                   ("HH000040", "software_developer", 2, 52000),
                   ("HH000043", "pilot", 2, 95000)],
        "senior_taxi": 0, "senior_ce": 2,
        "target_taxi": 0, "target_ce": 0},
}


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


# A household pairs a construction-worker head with a second
# earner when a non-head member holds a current employment.
# Senior band = tier >= 3 (dataio.TIER_WAGE_KEYS maps tiers
# 3-5 to the senior band — a tier-4 taxi driver earns 36,000,
# the senior wage, and a tier == 3 check would have missed
# them). The query is the MF query, run per seed.
_HEAD = ("household_members hm ON hm.household_id"
         " = h.household_id JOIN employments e"
         " ON e.character_id = hm.character_id")
_MEMBER = ("household_members hm2 ON hm2.household_id"
           " = h.household_id JOIN employments e2"
           " ON e2.character_id = hm2.character_id")
_CW_HEAD = ("hm.role = 'head' AND hm.left_at_game_minutes"
            " IS NULL AND e.profession_id ="
            " 'construction_worker' AND e.ended_at_game_minutes"
            " IS NULL")
_MEMBER_NOW = ("hm2.role != 'head' AND hm2.left_at_game_minutes"
               " IS NULL AND e2.ended_at_game_minutes IS NULL")


def _measure(seed):
    """One sweep world: returns the household counts, the
    second-earner rows in construction-worker-headed
    households, the senior-band driver/engineer counts, and
    the two target counts."""
    from tools.sim.engine import Simulation
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(db_path)
    sim = Simulation(db_path, seed=seed)
    sim.generate_population(120)
    sim.run_days(90)
    store = sim.store
    households = store.row(
        "SELECT COUNT(*) AS n FROM households")["n"]
    cw_heads = store.row(
        "SELECT COUNT(DISTINCT h.household_id) AS n FROM"
        " households h JOIN " + _HEAD +
        " WHERE " + _CW_HEAD)["n"]
    second = store.rows(
        "SELECT h.household_id, e2.profession_id AS prof,"
        " e2.tier AS tier, e2.wage_per_month AS wage"
        " FROM households h JOIN " + _HEAD +
        " JOIN " + _MEMBER +
        " WHERE " + _CW_HEAD + " AND " + _MEMBER_NOW +
        " ORDER BY h.household_id")
    senior_taxi = store.row(
        "SELECT COUNT(*) AS n FROM employments"
        " WHERE profession_id = 'taxi_driver' AND tier >= 3"
        " AND ended_at_game_minutes IS NULL")["n"]
    senior_ce = store.row(
        "SELECT COUNT(*) AS n FROM employments"
        " WHERE profession_id = 'civil_engineer' AND tier >= 3"
        " AND ended_at_game_minutes IS NULL")["n"]
    target_taxi = store.row(
        "SELECT COUNT(*) AS n FROM households h JOIN " + _HEAD +
        " JOIN " + _MEMBER +
        " WHERE " + _CW_HEAD + " AND " + _MEMBER_NOW +
        " AND e2.profession_id = 'taxi_driver' AND e2.tier >= 3"
        )["n"]
    target_ce = store.row(
        "SELECT COUNT(*) AS n FROM households h JOIN " + _HEAD +
        " JOIN " + _MEMBER +
        " WHERE " + _CW_HEAD + " AND " + _MEMBER_NOW +
        " AND e2.profession_id = 'civil_engineer'"
        " AND e2.tier >= 3")["n"]
    sim.close()
    os.remove(db_path)
    return (households, cw_heads, second, senior_taxi, senior_ce,
            target_taxi, target_ce)


def main():
    from tools import economy_sim as econ
    from tools.sim import dataio as dataio_mod
    sim_src = (ROOT / "tools" / "economy_sim.py").read_text()
    regress = (ROOT / "tools" / "sim" / "tests"
               / "test_no_regression.py").read_text()
    labour_tests = (ROOT / "tools" / "sim" / "tests"
                    / "test_economy_labour_banking.py").read_text()
    report = (ROOT / "docs" / "ECONOMY-SIM-REPORT-V7.md").read_text()
    gdd03 = (ROOT / "docs" / "GDD-03-ECONOMY-AND-PROFESSIONS.md").read_text()

    # 1. The senior-band definition, read from the source:
    # tiers 3-5 are all paid at the senior band.
    data = dataio_mod.WorldData()
    check(data.TIER_WAGE_KEYS[2:] ==
          ("senior", "senior", "senior"),
          "source: TIER_WAGE_KEYS maps tiers 3-5 to senior",
          str(data.TIER_WAGE_KEYS))
    check(data.wage_at("taxi_driver", 3) == 36000
          and data.wage_at("taxi_driver", 4) == 36000
          and data.wage_at("taxi_driver", 5) == 36000,
          "source: a tier-3/4/5 taxi driver earns the senior"
          " 36,000")
    check(data.wage_at("civil_engineer", 3) == 65000,
          "source: a tier-3 civil engineer earns the senior"
          " 65,000")
    prices = econ.load("prices.json")
    bands = {w["profession_id"]: w
             for w in prices["wages_monthly"]}
    check(bands["taxi_driver"]["senior"] == 36000
          and bands["civil_engineer"]["senior"] == 65000,
          "source: prices.json senior bands are 36,000 /"
          " 65,000")

    # 2. The tool is unchanged: both runs byte-identical to
    # the MF baselines, no bridge failure, no senior renting
    # row printed.
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
    check(pinned == MC_MD5,
          "tool: the pinned md5 stays the MC baseline",
          pinned)
    check("BRIDGE FAIL rows: []" in d1_text,
          "tool: no D1 bridge failure")
    check("senior, renting" not in d1_text,
          "tool: the default run prints no senior renting row")
    sh = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py"),
         "--shibnagar"],
        capture_output=True, cwd=ROOT)
    check(sh.returncode == 0, "tool: --shibnagar run exits 0")
    sh_text = sh.stdout.decode()
    sh_md5 = hashlib.md5(sh.stdout).hexdigest()
    sh2 = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py"),
         "--shibnagar"],
        capture_output=True, cwd=ROOT)
    check(hashlib.md5(sh2.stdout).hexdigest() == sh_md5,
          "tool: two --shibnagar runs are byte-identical",
          sh_md5)
    check(sh_md5 == SH_MD5,
          "tool: --shibnagar md5 matches the §26 record",
          sh_md5)
    check("shibnagar BRIDGE FAIL rows: []" in sh_text,
          "tool: no Shibnagar bridge failure")
    check("senior, renting" not in sh_text,
          "tool: the --shibnagar run prints no senior renting"
          " row")

    # 3. The live measurement: the five sweep worlds.
    total_hh = total_cw = total_second = 0
    total_st = total_sce = total_tt = total_tc = 0
    for seed, exp in EXPECTED.items():
        (households, cw_heads, second, senior_taxi, senior_ce,
         target_taxi, target_ce) = _measure(seed)
        total_hh += households
        total_cw += cw_heads
        total_second += len(second)
        total_st += senior_taxi
        total_sce += senior_ce
        total_tt += target_taxi
        total_tc += target_ce
        check(households == exp["households"],
              f"live {seed}: {exp['households']} households",
              str(households))
        check(cw_heads == exp["cw_heads"],
              f"live {seed}: {exp['cw_heads']} construction-"
              "worker-headed households",
              str(cw_heads))
        got = [(r["household_id"], r["prof"], r["tier"], r["wage"])
               for r in second]
        check(got == exp["second"],
              f"live {seed}: the second earners in those"
              " households are the measured ones",
              str(got))
        check(senior_taxi == exp["senior_taxi"],
              f"live {seed}: {exp['senior_taxi']} senior-band"
              " taxi drivers",
              str(senior_taxi))
        check(senior_ce == exp["senior_ce"],
              f"live {seed}: {exp['senior_ce']} senior-band"
              " civil engineers",
              str(senior_ce))
        check(target_taxi == 0,
              f"live {seed}: 0 senior taxi-driver second"
              " earners in construction-worker-headed"
              " households",
              str(target_taxi))
        check(target_ce == 0,
              f"live {seed}: 0 senior civil-engineer second"
              " earners in construction-worker-headed"
              " households",
              str(target_ce))
    check(total_hh == 234,
          "live totals: 234 households across the five seeds",
          str(total_hh))
    check(total_cw == 27,
          "live totals: 27 construction-worker-headed"
          " households",
          str(total_cw))
    check(total_second == 20,
          "live totals: 20 second earners found in those"
          " households",
          str(total_second))
    check(total_st == 6 and total_sce == 10,
          "live totals: 6 senior-band taxi drivers, 10"
          " senior-band civil engineers",
          f"{total_st} / {total_sce}")
    check(total_tt == 0 and total_tc == 0,
          "live totals: 0 targets in any seed",
          f"{total_tt} / {total_tc}")

    # 4. The V7 report §27: the measurement + the decision.
    check("## 27. Addendum — Multi-seed senior second earner"
          " sweep (Unit MG, Queue 38)" in report,
          "report §27: the addendum exists")
    s27 = report.split("## 27.")[1]
    s27_flat = " ".join(s27.split())
    check("DECIDED" in s27 and "§12 rule stands" in s27,
          "report §27: the no-change decision is stated")
    check("mg-seed-1" in s27_flat and "mg-seed-5" in s27_flat
          and "120 population" in s27_flat
          and "90 days" in s27_flat,
          "report §27: the five measured seeds are named")
    check("0 senior taxi-driver second earners" in s27_flat
          and "0 senior civil-engineer second earners"
          in s27_flat,
          "report §27: the target zeros are quoted")
    check("234 households" in s27_flat
          and "27" in s27_flat and "20 second earners" in s27,
          "report §27: the sweep totals are quoted")
    check("tier-3 shop owner" in s27_flat
          and "tier-3 business owner" in s27_flat,
          "report §27: the senior second earners that do"
          " occur are recorded")
    check("does NOT move" in s27 and MC_MD5 in s27
          and SH_MD5 in s27,
          "report §27: both md5 notes are recorded")
    check("Queue 39" in s27 and "Unit MH" in s27,
          "report §27: the follow-up names Queue 39")

    # 5. GDD-03 §2 records the MG update.
    check("Unit MG · Queue 38" in gdd03,
          "GDD-03 §2: the MG update is recorded")
    check("mg-seed-1" in gdd03,
          "GDD-03 §2: the measured seeds are named")
    check("§12 rule stands on a broader base" in gdd03,
          "GDD-03 §2: the decision is quoted")

    # 6. The economy_sim.py comment records the MG outcome.
    check("Queue 38 / Unit MG" in sim_src,
          "tool: the comment names the MG sweep")
    check("mg-seed-1" in sim_src and "report §27" in sim_src,
          "tool: the comment records the seeds and §27")

    # 7. Tests pin the MG sweep.
    check("class TestSeniorSecondEarnerMultiSeedSweep"
          in labour_tests,
          "tests: the MG guard class exists")
    check("test_no_senior_second_earner_in_any_seed"
          in labour_tests,
          "tests: the multi-seed test exists")
    check("test_senior_band_wage_holds_in_every_seed"
          in labour_tests,
          "tests: the senior-band wage test exists")

    # 8. Scope: only the MG files changed for this unit.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 38 MG:",
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
                    "tools/sim/tests/test_economy_labour_banking.py",
                    "docs/ECONOMY-SIM-REPORT-V7.md",
                    "docs/GDD-03-ECONOMY-AND-PROFESSIONS.md",
                    "tools/verify_queue38_mg.py"},
          "scope: only the five MG files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
