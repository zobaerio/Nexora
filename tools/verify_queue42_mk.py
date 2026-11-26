"""Verify Queue 42 Unit MK — Senior Taxi Driver Under a
Low-Wage Head (MJ follow-up).

Checks the decision against its sources: tools/sim/dataio.py
(TIER_WAGE_KEYS — tiers 3-5 are all paid at the senior band,
so a construction-worker head at any tier >= 3 earns the
senior 20,000), data/prices.json (the bands: taxi senior
36,000, civil engineer senior 65,000, construction worker
senior 20,000, teacher mid 24,000), tools/economy_sim.py
(the MK comment now records the sweep outcome — the pinned
md5s do NOT move), tools/sim/tests/
test_economy_labour_banking.py (guard tests pin the
head-wage query method), docs/ECONOMY-SIM-REPORT-V7.md §31
(the measured decision) and docs/GDD-03-ECONOMY-AND-
PROFESSIONS.md §2 (the MK update). Re-runs the MJ
any-household query WITH the head's current wage joined
(e.wage_per_month) on both MJ worlds (mi-seed-1 re-run +
mj-seed-2 re-run, 300 population, 365 days each) and
asserts the middle outcome: exactly one senior taxi-driver
second earner under a head earning <= 25,000 (the 24,000
mid-tier teacher in mi-seed-1) and none under a head
earning <= 20,000 in either world — but every head
earning <= 20,000 in both worlds is a construction worker,
so the absence cannot separate profession from wage.
Prints one line per check and a summary; exits 0 only when
every check passes.
Run from the repo root: python3 tools/verify_queue42_mk.py
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
# senior taxi-driver second earners in any household
# (household, head profession, head tier, head wage, head
# name, second earner tier, wage, second earner name), the
# senior civil-engineer second earners in any household,
# the second earners in any household, the senior
# taxi-driver second earners under a construction-worker
# head, the construction-worker-headed households with a
# senior civil-engineer second earner (the MI pairing),
# the counts under heads earning <= 25,000 and <= 20,000,
# the heads earning <= 25,000 (count + lowest wage), and
# the construction-worker heads (household, tier, wage,
# name — all at the flat senior 20,000).
EXPECTED = {
    "mi-seed-1": {
        "households": 123, "senior_taxi": 9,
        "any_taxi": [
            ("HH000061", "teacher", 2, 24000, "Jamal Begum",
             4, 36000, "Tamim Sarkar"),
            ("HH000007", "pilot", 1, 45000, "Shakib Sikder",
             5, 36000, "Pranto Molla"),
            ("HH000003", "shop_owner", 5, 55000, "Farhana Kazi",
             5, 36000, "Ayesha Biswas"),
            ("HH000096", "civil_engineer", 5, 65000,
             "Sumon Fakir", 5, 36000, "Mitu Uddin"),
            ("HH000054", "software_developer", 5, 90000,
             "Ayesha Halder", 5, 36000, "Sakib Ghosh"),
            ("HH000063", "pilot", 2, 95000, "Ruma Ghosh",
             4, 36000, "Salma Das")],
        "senior_ce_any": 4, "second_any": 62,
        "cw_target_taxi": 0, "cw_target_ce": 1,
        "cw_ce_households": ["HH000086"],
        "le25": 1, "le20": 0,
        "low_heads": (11, 20000),
        "cw_heads": [
            ("HH000011", 5, 20000, "Shakib Sheikh"),
            ("HH000017", 5, 20000, "Khadija Das"),
            ("HH000029", 3, 20000, "Farhana Marma"),
            ("HH000039", 5, 20000, "Salma Gazi"),
            ("HH000079", 5, 20000, "Ayesha Khan"),
            ("HH000086", 4, 20000, "Omar Sheikh"),
            ("HH000089", 5, 20000, "Nusrat Fakir"),
            ("HH000100", 4, 20000, "Mushfiq Halder"),
            ("HH000107", 4, 20000, "Rakib Tripura")]},
    "mj-seed-2": {
        "households": 123, "senior_taxi": 10,
        "any_taxi": [
            ("HH000089", "taxi_driver", 5, 36000,
             "Fahim Matubbar", 5, 36000, "Rafid Biswas"),
            ("HH000092", "teacher", 4, 38000, "Ayesha Islam",
             5, 36000, "Nusrat Mir"),
            ("HH000100", "shop_owner", 5, 55000, "Taslima Dewan",
             5, 36000, "Fahim Molla"),
            ("HH000027", "doctor", 5, 95000, "Tamanna Khan",
             5, 36000, "Shakib Howlader"),
            ("HH000105", "business_owner", 4, 300000,
             "Sultana Ali", 4, 36000, "Sharmin Sarkar")],
        "senior_ce_any": 4, "second_any": 62,
        "cw_target_taxi": 0, "cw_target_ce": 1,
        "cw_ce_households": ["HH000028"],
        "le25": 0, "le20": 0,
        "low_heads": (8, 20000),
        "cw_heads": [
            ("HH000008", 3, 20000, "Shakib Begum"),
            ("HH000023", 5, 20000, "Rakib Ahmed"),
            ("HH000028", 5, 20000, "Rakib Akter"),
            ("HH000051", 3, 20000, "Nargis Bepari"),
            ("HH000067", 5, 20000, "Farhan Gazi"),
            ("HH000072", 4, 20000, "Hasan Das"),
            ("HH000076", 4, 20000, "Ishrat Uddin"),
            ("HH000093", 5, 20000, "Habiba Shah")]},
}


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


# A household has a second earner when a non-head member
# holds a current employment. Senior band = tier >= 3
# (dataio.TIER_WAGE_KEYS maps tiers 3-5 to the senior band).
# The MK query is the MJ any-household query WITH the
# head's current wage joined (e.wage_per_month).
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
    second earners in any household (with head wages), the
    senior civil-engineer second earners in any household,
    the second earners in any household, the two
    construction-worker-headed target counts + the MI-pairing
    households, the counts under heads earning <= 25,000
    and <= 20,000, the low-wage heads (count + lowest wage),
    and the construction-worker heads."""
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
        " e.tier AS head_tier, e.wage_per_month AS head_wage,"
        " c.display_name AS head_name, e2.tier AS se_tier,"
        " e2.wage_per_month AS se_wage, c2.display_name AS"
        " se_name FROM households h JOIN " + _HEAD +
        " JOIN " + _MEMBER +
        " JOIN characters c ON c.character_id ="
        " hm.character_id JOIN characters c2 ON"
        " c2.character_id = hm2.character_id"
        " WHERE " + _HEAD_NOW + " AND " + _MEMBER_NOW +
        " AND e2.profession_id = 'taxi_driver'"
        " AND e2.tier >= 3 ORDER BY e.wage_per_month,"
        " h.household_id")
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
    le25 = store.row(
        "SELECT COUNT(*) AS n FROM households h JOIN " + _HEAD +
        " JOIN " + _MEMBER +
        " WHERE " + _HEAD_NOW + " AND " + _MEMBER_NOW +
        " AND e2.profession_id = 'taxi_driver'"
        " AND e2.tier >= 3 AND e.wage_per_month <= 25000")["n"]
    le20 = store.row(
        "SELECT COUNT(*) AS n FROM households h JOIN " + _HEAD +
        " JOIN " + _MEMBER +
        " WHERE " + _HEAD_NOW + " AND " + _MEMBER_NOW +
        " AND e2.profession_id = 'taxi_driver'"
        " AND e2.tier >= 3 AND e.wage_per_month <= 20000")["n"]
    low_heads = store.row(
        "SELECT MIN(e.wage_per_month) AS mn, COUNT(*) AS n"
        " FROM households h JOIN " + _HEAD +
        " WHERE " + _HEAD_NOW + " AND e.wage_per_month <= 25000")
    cw_heads = store.rows(
        "SELECT h.household_id, e.tier, e.wage_per_month,"
        " c.display_name FROM households h JOIN " + _HEAD +
        " JOIN characters c ON c.character_id ="
        " hm.character_id WHERE " + _HEAD_NOW +
        " AND e.profession_id = 'construction_worker'"
        " ORDER BY e.wage_per_month, h.household_id")
    sim.close()
    os.remove(db_path)
    return (households, senior_taxi, any_taxi, senior_ce_any,
            second_any, cw_target_taxi, cw_target_ce,
            [r["household_id"] for r in cw_ce_households],
            le25, le20, (low_heads["n"], low_heads["mn"]),
            [(r["household_id"], r["tier"],
              r["wage_per_month"], r["display_name"])
             for r in cw_heads])


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

    # 1. The senior-band definition + the wages the sweep
    # turns on, read from the source.
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
    check(data.wage_at("construction_worker", 3) == 20000
          and data.wage_at("construction_worker", 4) == 20000
          and data.wage_at("construction_worker", 5) == 20000,
          "source: a tier-3/4/5 construction worker earns the"
          " senior 20,000")
    check(data.wage_at("teacher", 2) == 24000,
          "source: a tier-2 teacher earns the mid 24,000")
    prices = econ.load("prices.json")
    bands = {w["profession_id"]: w
             for w in prices["wages_monthly"]}
    check(bands["taxi_driver"]["senior"] == 36000
          and bands["civil_engineer"]["senior"] == 65000
          and bands["construction_worker"]["senior"] == 20000
          and bands["teacher"]["mid"] == 24000,
          "source: prices.json bands are 36,000 / 65,000 /"
          " 20,000 / 24,000")

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
    # worlds, with the head wage joined.
    total_hh = total_st = total_any = total_sce = 0
    total_second = total_tt = total_tc = 0
    total_le25 = total_le20 = total_low = total_cw = 0
    for seed, exp in EXPECTED.items():
        (households, senior_taxi, any_taxi, senior_ce_any,
         second_any, cw_target_taxi, cw_target_ce,
         cw_ce_households, le25, le20, low_heads,
         cw_heads) = _measure(seed)
        total_hh += households
        total_st += senior_taxi
        total_any += len(any_taxi)
        total_sce += senior_ce_any
        total_second += second_any
        total_tt += cw_target_taxi
        total_tc += cw_target_ce
        total_le25 += le25
        total_le20 += le20
        total_low += low_heads[0]
        total_cw += len(cw_heads)
        check(households == exp["households"],
              f"live {seed}: {exp['households']} households",
              str(households))
        check(senior_taxi == exp["senior_taxi"],
              f"live {seed}: {exp['senior_taxi']} senior-band"
              " taxi drivers",
              str(senior_taxi))
        got = [(r["household_id"], r["head_prof"],
                r["head_tier"], r["head_wage"], r["head_name"],
                r["se_tier"], r["se_wage"], r["se_name"])
               for r in any_taxi]
        check(got == exp["any_taxi"],
              f"live {seed}: the senior taxi second earners"
              " in any household are the measured ones, with"
              " head wages",
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
        check(le25 == exp["le25"],
              f"live {seed}: {exp['le25']} senior taxi second"
              " earners under a head earning <= 25,000",
              str(le25))
        check(le20 == exp["le20"],
              f"live {seed}: {exp['le20']} senior taxi second"
              " earners under a head earning <= 20,000",
              str(le20))
        check(low_heads == exp["low_heads"],
              f"live {seed}: {exp['low_heads'][0]} heads earn"
              f" <= 25,000, lowest {exp['low_heads'][1]}",
              str(low_heads))
        check(cw_heads == exp["cw_heads"],
              f"live {seed}: the {len(exp['cw_heads'])}"
              " construction-worker heads are the measured"
              " ones, all at 20,000",
              str(cw_heads))
        check(all(w == 20000 for _h, _t, w, _n in cw_heads),
              f"live {seed}: every construction-worker head"
              " earns exactly 20,000")
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
    check(total_le25 == 1,
          "live totals: 1 senior taxi second earner under a"
          " head earning <= 25,000",
          str(total_le25))
    check(total_le20 == 0,
          "live totals: 0 senior taxi second earners under a"
          " head earning <= 20,000",
          str(total_le20))
    check(total_low == 19,
          "live totals: 19 heads earn <= 25,000 across the"
          " two seeds",
          str(total_low))
    check(total_cw == 17,
          "live totals: 17 construction-worker heads, all at"
          " exactly 20,000",
          str(total_cw))

    # 4. The V7 report §31: the measurement + the decision.
    check("## 31. Addendum — Senior taxi driver under a"
          " low-wage head (Unit MK, Queue 42)"
          in report,
          "report §31: the addendum exists")
    s31 = report.split("## 31.")[1]
    s31_flat = " ".join(s31.split())
    check("DECIDED" in s31 and "strong wage-band hypothesis"
          " is refuted" in s31_flat,
          "report §31: the refuted-hypothesis decision is"
          " stated")
    check("HH000061" in s31_flat and "Jamal Begum" in s31_flat
          and "24,000" in s31_flat and "Tamim Sarkar"
          in s31_flat,
          "report §31: the 24,000 counterexample is named")
    check("mi-seed-1" in s31_flat and "mj-seed-2" in s31_flat
          and "300 population" in s31_flat
          and "365 days" in s31_flat,
          "report §31: the two measured seeds are named")
    check("1 senior taxi-driver second earner under a head"
          " earning <= 25,000" in s31_flat
          and "0 senior taxi-driver second earners under a"
          " head earning <= 20,000" in s31_flat,
          "report §31: the headline counts are quoted")
    check("confounded" in s31_flat,
          "report §31: the profession/wage confound is"
          " stated")
    check("17 construction-worker heads" in s31_flat
          and "all at exactly 20,000" in s31_flat,
          "report §31: the flat construction-worker wage is"
          " recorded")
    check("does NOT move" in s31 and MI_MD5 in s31
          and SH_MD5 in s31,
          "report §31: both md5 notes are recorded")
    check("Queue 43" in s31 and "Unit ML" in s31,
          "report §31: the follow-up names Queue 43")

    # 5. GDD-03 §2 records the MK update.
    check("Unit MK · Queue 42" in gdd03,
          "GDD-03 §2: the MK update is recorded")
    check("mj-seed-2" in gdd03,
          "GDD-03 §2: the fresh seed is named")
    check("confounded" in gdd03,
          "GDD-03 §2: the confound is quoted")

    # 6. The economy_sim.py comment records the MK outcome.
    check("Queue 42 / Unit MK" in sim_src,
          "tool: the comment names the MK sweep")
    check("HH000061" in sim_src and "report §31" in sim_src,
          "tool: the comment records the counterexample and"
          " §31")

    # 7. Tests pin the MK sweep.
    check("class TestSeniorTaxiSecondEarnerHeadWage"
          in labour_tests,
          "tests: the MK guard class exists")
    check("test_head_wage_join_returns_the_current_"
          "employment_wage" in labour_tests,
          "tests: the head-wage join test exists")
    check("test_construction_worker_head_wage_follows_the"
          "_band" in labour_tests,
          "tests: the construction-worker head-wage test"
          " exists")

    # 8. Scope: only the MK files changed for this unit.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 42 MK:",
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
                    "tools/verify_queue42_mk.py"},
          "scope: only the five MK files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
