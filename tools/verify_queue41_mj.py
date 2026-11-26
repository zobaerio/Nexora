"""Verify Queue 41 Unit MJ — Senior Taxi Driver as Second
Earner in Any Household (MI follow-up).

Checks the decision against its sources: tools/sim/dataio.py
(TIER_WAGE_KEYS — tiers 3-5 are all paid at the senior band,
so "senior" in the live world means tier >= 3, not tier == 3),
data/prices.json (the senior bands: taxi 36,000, civil
engineer 65,000), tools/economy_sim.py (the MJ comment now
records the sweep outcome — the pinned md5s do NOT move),
tools/sim/tests/test_economy_labour_banking.py (guard tests
pin the any-household query method), docs/ECONOMY-SIM-REPORT-
V7.md §30 (the measured decision) and docs/GDD-03-ECONOMY-
AND-PROFESSIONS.md §2 (the MJ update). Re-runs the live sweep
(seed mi-seed-1 re-run + fresh seed mj-seed-2, 300
population, 365 days each) and asserts senior taxi drivers DO
sit on the second-earner side in both worlds — 6 and 5 — but
never under a construction-worker head in either.
Prints one line per check and a summary; exits 0 only when
every check passes.
Run from the repo root: python3 tools/verify_queue41_mj.py
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

MI_MD5 = "3d3fce982a64634a0b03bb0af3643f94"
SH_MD5 = "17bc7165d1e6ad48de4123e38e426bd7"

# The measured sweep, from the probe runs: per seed, the
# household count, the senior-band taxi-driver count, the
# senior taxi-driver second earners in ANY household
# (household, head profession, head tier, head name, second
# earner tier, wage, second earner name), the senior
# civil-engineer second earners in any household, the
# second earners in any household, the senior taxi-driver
# second earners under a construction-worker head, and the
# construction-worker-headed households with a senior
# civil-engineer second earner (the MI pairing, re-measured
# here — one in each world).
EXPECTED = {
    "mi-seed-1": {
        "households": 123, "senior_taxi": 9,
        "any_taxi": [
            ("HH000003", "shop_owner", 5, "Farhana Kazi",
             5, 36000, "Ayesha Biswas"),
            ("HH000007", "pilot", 1, "Shakib Sikder",
             5, 36000, "Pranto Molla"),
            ("HH000054", "software_developer", 5, "Ayesha Halder",
             5, 36000, "Sakib Ghosh"),
            ("HH000061", "teacher", 2, "Jamal Begum",
             4, 36000, "Tamim Sarkar"),
            ("HH000063", "pilot", 2, "Ruma Ghosh",
             4, 36000, "Salma Das"),
            ("HH000096", "civil_engineer", 5, "Sumon Fakir",
             5, 36000, "Mitu Uddin")],
        "senior_ce_any": 4, "second_any": 62,
        "cw_target_taxi": 0, "cw_target_ce": 1,
        "cw_ce_households": ["HH000086"]},
    "mj-seed-2": {
        "households": 123, "senior_taxi": 10,
        "any_taxi": [
            ("HH000027", "doctor", 5, "Tamanna Khan",
             5, 36000, "Shakib Howlader"),
            ("HH000089", "taxi_driver", 5, "Fahim Matubbar",
             5, 36000, "Rafid Biswas"),
            ("HH000092", "teacher", 4, "Ayesha Islam",
             5, 36000, "Nusrat Mir"),
            ("HH000100", "shop_owner", 5, "Taslima Dewan",
             5, 36000, "Fahim Molla"),
            ("HH000105", "business_owner", 4, "Sultana Ali",
             4, 36000, "Sharmin Sarkar")],
        "senior_ce_any": 4, "second_any": 62,
        "cw_target_taxi": 0, "cw_target_ce": 1,
        "cw_ce_households": ["HH000028"]},
}


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


# A household has a second earner when a non-head member
# holds a current employment. Senior band = tier >= 3
# (dataio.TIER_WAGE_KEYS maps tiers 3-5 to the senior band —
# a tier-5 taxi driver earns 36,000, the senior wage, and a
# tier == 3 check would have missed them). The MJ query is
# the MF pairing query WITHOUT the construction-worker-head
# restriction.
_HEAD = ("household_members hm ON hm.household_id"
         " = h.household_id JOIN employments e"
         " ON e.character_id = hm.character_id")
_MEMBER = ("household_members hm2 ON hm2.household_id"
           " = h.household_id JOIN employments e2"
           " ON e2.character_id = hm2.character_id")
_HEAD_NOW = ("hm.role = 'head' AND hm.left_at_game_minutes"
             " IS NULL AND e.ended_at_game_minutes IS NULL")
_MEMBER_NOW = ("hm2.role != 'head' AND hm2.left_at_game_minutes"
               " IS NULL AND e2.ended_at_game_minutes IS NULL")
_CW_HEAD = (_HEAD_NOW + " AND e.profession_id ="
            " 'construction_worker'")


def _measure(seed):
    """One sweep world: returns the household count, the
    senior-band taxi-driver count, the senior taxi-driver
    second earners in any household, the senior civil-
    engineer second earners in any household, the second
    earners in any household, and the two construction-
    worker-headed target counts + the MI-pairing
    households."""
    from tools.sim.engine import Simulation
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(db_path)
    sim = Simulation(db_path, seed=seed)
    sim.generate_population(300)
    sim.run_days(365)
    store = sim.store
    households = store.row(
        "SELECT COUNT(*) AS n FROM households")["n"]
    senior_taxi = store.row(
        "SELECT COUNT(*) AS n FROM employments"
        " WHERE profession_id = 'taxi_driver' AND tier >= 3"
        " AND ended_at_game_minutes IS NULL")["n"]
    any_taxi = store.rows(
        "SELECT h.household_id, e.profession_id AS head_prof,"
        " e.tier AS head_tier, c.display_name AS head_name,"
        " e2.tier AS se_tier, e2.wage_per_month AS se_wage,"
        " c2.display_name AS se_name"
        " FROM households h JOIN " + _HEAD +
        " JOIN " + _MEMBER +
        " JOIN characters c ON c.character_id ="
        " hm.character_id JOIN characters c2 ON"
        " c2.character_id = hm2.character_id"
        " WHERE " + _HEAD_NOW + " AND " + _MEMBER_NOW +
        " AND e2.profession_id = 'taxi_driver'"
        " AND e2.tier >= 3 ORDER BY h.household_id")
    senior_ce_any = store.row(
        "SELECT COUNT(*) AS n FROM households h JOIN " + _HEAD +
        " JOIN " + _MEMBER +
        " WHERE " + _HEAD_NOW + " AND " + _MEMBER_NOW +
        " AND e2.profession_id = 'civil_engineer'"
        " AND e2.tier >= 3")["n"]
    second_any = store.row(
        "SELECT COUNT(*) AS n FROM households h JOIN " + _HEAD +
        " JOIN " + _MEMBER +
        " WHERE " + _HEAD_NOW + " AND " + _MEMBER_NOW)["n"]
    cw_target_taxi = store.row(
        "SELECT COUNT(*) AS n FROM households h JOIN " + _HEAD +
        " JOIN " + _MEMBER +
        " WHERE " + _CW_HEAD + " AND " + _MEMBER_NOW +
        " AND e2.profession_id = 'taxi_driver'"
        " AND e2.tier >= 3")["n"]
    cw_target_ce = store.row(
        "SELECT COUNT(*) AS n FROM households h JOIN " + _HEAD +
        " JOIN " + _MEMBER +
        " WHERE " + _CW_HEAD + " AND " + _MEMBER_NOW +
        " AND e2.profession_id = 'civil_engineer'"
        " AND e2.tier >= 3")["n"]
    cw_ce_households = store.rows(
        "SELECT h.household_id FROM households h JOIN "
        + _HEAD + " JOIN " + _MEMBER +
        " WHERE " + _CW_HEAD + " AND " + _MEMBER_NOW +
        " AND e2.profession_id = 'civil_engineer'"
        " AND e2.tier >= 3 ORDER BY h.household_id")
    sim.close()
    os.remove(db_path)
    return (households, senior_taxi, any_taxi, senior_ce_any,
            second_any, cw_target_taxi, cw_target_ce,
            [r["household_id"] for r in cw_ce_households])


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
    # the MI baselines, no bridge failure, no senior renting
    # row printed, the senior CE rows and bridge line still
    # wired.
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
    check(pinned == MI_MD5,
          "tool: the pinned md5 stays the MI baseline",
          pinned)
    check("BRIDGE FAIL rows: []" in d1_text,
          "tool: no D1 bridge failure")
    check("civil-engineer second earner (senior 65,000,"
          " monthly)" in d1_text,
          "tool: the senior CE rows still print")
    check("construction_worker + civil-engineer (senior)"
          " start  30000 + other-tier dip  -17758"
          " =   12242  OK" in d1_text,
          "tool: the D1 bridge line is still 12,242")
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
          "tool: --shibnagar md5 stays the MI baseline",
          sh_md5)
    check("shibnagar BRIDGE FAIL rows: []" in sh_text,
          "tool: no Shibnagar bridge failure")
    check("senior, renting" not in sh_text,
          "tool: the --shibnagar run prints no senior renting"
          " row")

    # 3. The live measurement: the two larger year-long
    # worlds.
    total_hh = total_st = total_any = total_sce = 0
    total_second = total_tt = total_tc = 0
    for seed, exp in EXPECTED.items():
        (households, senior_taxi, any_taxi, senior_ce_any,
         second_any, cw_target_taxi, cw_target_ce,
         cw_ce_households) = _measure(seed)
        total_hh += households
        total_st += senior_taxi
        total_any += len(any_taxi)
        total_sce += senior_ce_any
        total_second += second_any
        total_tt += cw_target_taxi
        total_tc += cw_target_ce
        check(households == exp["households"],
              f"live {seed}: {exp['households']} households",
              str(households))
        check(senior_taxi == exp["senior_taxi"],
              f"live {seed}: {exp['senior_taxi']} senior-band"
              " taxi drivers",
              str(senior_taxi))
        got = [(r["household_id"], r["head_prof"],
                r["head_tier"], r["head_name"], r["se_tier"],
                r["se_wage"], r["se_name"]) for r in any_taxi]
        check(got == exp["any_taxi"],
              f"live {seed}: the senior taxi second earners"
              " in any household are the measured ones",
              str(got))
        check(all(r["head_prof"] != "construction_worker"
                  for r in any_taxi),
              f"live {seed}: none of them sits under a"
              " construction-worker head")
        check(senior_ce_any == exp["senior_ce_any"],
              f"live {seed}: {exp['senior_ce_any']} senior CE"
              " second earners in any household",
              str(senior_ce_any))
        check(second_any == exp["second_any"],
              f"live {seed}: {exp['second_any']} second"
              " earners in any household",
              str(second_any))
        check(cw_target_taxi == 0,
              f"live {seed}: 0 senior taxi-driver second"
              " earners under a construction-worker head",
              str(cw_target_taxi))
        check(cw_target_ce == exp["cw_target_ce"],
              f"live {seed}: {exp['cw_target_ce']} senior"
              " civil-engineer second earner under a"
              " construction-worker head",
              str(cw_target_ce))
        check(cw_ce_households == exp["cw_ce_households"],
              f"live {seed}: the MI pairing is"
              f" {exp['cw_ce_households']}",
              str(cw_ce_households))
    check(total_hh == 246,
          "live totals: 246 households across the two seeds",
          str(total_hh))
    check(total_st == 19,
          "live totals: 19 senior-band taxi drivers",
          str(total_st))
    check(total_any == 11,
          "live totals: 11 senior taxi second earners in any"
          " household",
          str(total_any))
    check(total_sce == 8,
          "live totals: 8 senior CE second earners in any"
          " household",
          str(total_sce))
    check(total_second == 124,
          "live totals: 124 second earners in any household",
          str(total_second))
    check(total_tt == 0 and total_tc == 2,
          "live totals: 0 taxi targets, 2 CE targets (the MI"
          " pairing, once per world)",
          f"{total_tt} / {total_tc}")

    # 4. The V7 report §30: the measurement + the decision.
    check("## 30. Addendum — Senior taxi driver as second"
          " earner in any household (Unit MJ, Queue 41)"
          in report,
          "report §30: the addendum exists")
    s30 = report.split("## 30.")[1]
    s30_flat = " ".join(s30.split())
    check("DECIDED" in s30 and "specific to the"
          " construction-worker pairing" in s30_flat,
          "report §30: the pairing-specific decision is"
          " stated")
    check("mi-seed-1" in s30_flat and "mj-seed-2" in s30_flat
          and "300 population" in s30_flat
          and "365 days" in s30_flat,
          "report §30: the two measured seeds are named")
    check("11 senior taxi-driver second earners" in s30_flat
          and "0 senior taxi-driver second earners under a"
          " construction-worker head" in s30_flat,
          "report §30: the headline counts are quoted")
    check("HH000003" in s30_flat and "Ayesha Biswas" in s30_flat
          and "HH000027" in s30_flat
          and "Shakib Howlader" in s30_flat,
          "report §30: households from both seeds are named")
    check("HH000028" in s30_flat,
          "report §30: the fresh-seed MI pairing is recorded")
    check("does NOT move" in s30 and MI_MD5 in s30
          and SH_MD5 in s30,
          "report §30: both md5 notes are recorded")
    check("Queue 42" in s30 and "Unit MK" in s30,
          "report §30: the follow-up names Queue 42")

    # 5. GDD-03 §2 records the MJ update.
    check("Unit MJ · Queue 41" in gdd03,
          "GDD-03 §2: the MJ update is recorded")
    check("mj-seed-2" in gdd03,
          "GDD-03 §2: the fresh seed is named")
    check("specific to the construction-worker pairing"
          in gdd03,
          "GDD-03 §2: the decision is quoted")

    # 6. The economy_sim.py comment records the MJ outcome.
    check("Queue 41 / Unit MJ" in sim_src,
          "tool: the comment names the MJ sweep")
    check("mj-seed-2" in sim_src and "report §30" in sim_src,
          "tool: the comment records the seed and §30")

    # 7. Tests pin the MJ sweep.
    check("class TestSeniorTaxiSecondEarnerAnyHousehold"
          in labour_tests,
          "tests: the MJ guard class exists")
    check("test_any_household_query_counts_senior_taxi"
          "_second_earners" in labour_tests,
          "tests: the any-household query test exists")
    check("test_senior_band_wage_holds_in_every_seed"
          in labour_tests,
          "tests: the senior-band wage test exists")

    # 8. Scope: only the MJ files changed for this unit.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 41 MJ:",
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
                    "tools/verify_queue41_mj.py"},
          "scope: only the five MJ files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
