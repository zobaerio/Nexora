"""Verify Queue 40 Unit MI — Senior Second Earner in a
Larger World (MH follow-up).

Checks the decision against its sources: tools/sim/dataio.py
(TIER_WAGE_KEYS — tiers 3-5 are all paid at the senior band,
so "senior" in the live world means tier >= 3, not tier == 3),
data/prices.json (the senior bands: taxi 36,000, civil
engineer 65,000), tools/economy_sim.py (the MI wiring — the
senior civil-engineer rows in the IC section and the bridge
line in both bridge checks; the pinned md5s MOVE), tools/sim/
tests/test_no_regression.py (the MI figure + bridge-line
tests) and test_economy_labour_banking.py (guard tests pin
the sweep method), docs/ECONOMY-SIM-REPORT-V7.md §29 (the
measured decision) and docs/GDD-03-ECONOMY-AND-PROFESSIONS.md
§2 (the MI update). Re-runs the live sweep (seed mi-seed-1,
300 population, 365 days) and asserts the larger world holds
exactly one construction-worker-headed household with a senior
civil-engineer second earner (HH000086) and none with a senior
taxi-driver second earner.
Prints one line per check and a summary; exits 0 only when
every check passes.
Run from the repo root: python3 tools/verify_queue40_mi.py
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
MC_MD5 = "a818a3273cdad108c4d8d4ae198b5b44"
SH_OLD_MD5 = "762a2b6395a1c83fc86f2b5f9c1839bc"

# The measured sweep, from the probe run: the household count,
# the construction-worker-headed count, the second earners
# found in those households (household, profession, tier,
# wage), the senior-band taxi-driver and civil-engineer
# counts, the two target counts, and the target household's
# head (Omar Sheikh, construction worker tier 4) and second
# earner (Liton Tripura, civil engineer tier 5).
EXPECTED = {
    "households": 123, "cw_heads": 9,
    "second": [("HH000039", "civil_engineer", 2, 38000),
               ("HH000079", "software_developer", 4, 90000),
               ("HH000086", "civil_engineer", 5, 65000),
               ("HH000100", "shop_owner", 5, 55000),
               ("HH000107", "pilot", 3, 180000)],
    "senior_taxi": 9, "senior_ce": 20,
    "target_taxi": 0, "target_ce": 1,
    "target_head": ("construction_worker", 4, "Omar Sheikh"),
    "target_member": "Liton Tripura",
    "senior_ce_any_household": 4,
}


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


# A household pairs a construction-worker head with a second
# earner when a non-head member holds a current employment.
# Senior band = tier >= 3 (dataio.TIER_WAGE_KEYS maps tiers
# 3-5 to the senior band — a tier-5 civil engineer earns
# 65,000, the senior wage, and a tier == 3 check would have
# missed them). The query is the MF query.
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
    households, the senior-band driver/engineer counts, the
    two target counts, the target household's head and second
    earner, and the senior-CE-second-earner count in any
    household."""
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
    head = store.row(
        "SELECT e.profession_id AS prof, e.tier AS tier,"
        " c.display_name AS name FROM household_members hm"
        " JOIN employments e ON e.character_id ="
        " hm.character_id JOIN characters c ON"
        " c.character_id = hm.character_id WHERE"
        " hm.household_id = 'HH000086' AND hm.role = 'head'"
        " AND hm.left_at_game_minutes IS NULL AND"
        " e.ended_at_game_minutes IS NULL")
    member = store.row(
        "SELECT c.display_name AS name FROM household_members"
        " hm2 JOIN employments e2 ON e2.character_id ="
        " hm2.character_id JOIN characters c ON"
        " c.character_id = hm2.character_id WHERE"
        " hm2.household_id = 'HH000086' AND hm2.role != 'head'"
        " AND hm2.left_at_game_minutes IS NULL AND"
        " e2.ended_at_game_minutes IS NULL AND"
        " e2.profession_id = 'civil_engineer' AND e2.tier >= 3")
    senior_ce_any = store.row(
        "SELECT COUNT(*) AS n FROM households h JOIN " + _HEAD +
        " JOIN " + _MEMBER +
        " WHERE hm.role = 'head' AND hm.left_at_game_minutes"
        " IS NULL AND e.ended_at_game_minutes IS NULL"
        " AND " + _MEMBER_NOW +
        " AND e2.profession_id = 'civil_engineer'"
        " AND e2.tier >= 3")["n"]
    sim.close()
    os.remove(db_path)
    return (households, cw_heads, second, senior_taxi, senior_ce,
            target_taxi, target_ce,
            (head["prof"], head["tier"], head["name"]),
            member["name"], senior_ce_any)


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
          and data.wage_at("taxi_driver", 5) == 36000,
          "source: a tier-3/5 taxi driver earns the senior"
          " 36,000")
    check(data.wage_at("civil_engineer", 3) == 65000
          and data.wage_at("civil_engineer", 5) == 65000,
          "source: a tier-3/5 civil engineer earns the senior"
          " 65,000")
    prices = econ.load("prices.json")
    bands = {w["profession_id"]: w
             for w in prices["wages_monthly"]}
    check(bands["taxi_driver"]["senior"] == 36000
          and bands["civil_engineer"]["senior"] == 65000,
          "source: prices.json senior bands are 36,000 /"
          " 65,000")

    # 2. The tool is wired: both runs exit 0, the md5s move
    # to the MI baselines, no bridge failure, the senior CE
    # rows print, the bridge line is 12,242 in both cities,
    # and no senior renting row is printed.
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
          "tool: the pinned md5 is the MI baseline",
          pinned)
    check(MC_MD5 in regress,
          "tool: the MC baseline is kept as history",
          MC_MD5)
    check("BRIDGE FAIL rows: []" in d1_text,
          "tool: no D1 bridge failure")
    check("civil-engineer second earner (senior 65,000,"
          " monthly)" in d1_text,
          "tool: the senior CE rows print in the default run")
    check("construction_worker + civil-engineer (senior)"
          " start  30000 + other-tier dip  -17758"
          " =   12242  OK" in d1_text,
          "tool: the D1 bridge line is 30,000 - 17,758"
          " = 12,242")
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
          "tool: --shibnagar md5 is the MI baseline",
          sh_md5)
    check("shibnagar BRIDGE FAIL rows: []" in sh_text,
          "tool: no Shibnagar bridge failure")
    check("construction_worker + civil-engineer (senior)"
          " start  30000 + other-tier dip  -17758"
          " =   12242  OK" in sh_text,
          "tool: the Shibnagar bridge line is 12,242 too")
    check("senior, renting" not in sh_text,
          "tool: the --shibnagar run prints no senior renting"
          " row")

    # 3. The wired figures, recomputed from the tool.
    w = bands["construction_worker"]
    for tier, want_min, want_net in (
            ("entry", -17758, 42900), ("mid", -14634, 46144),
            ("senior", -11305, 49601)):
        row = econ.simulate(
            prices, w, tier, storm_days=econ.STORM_EARLY_DAYS,
            second_earner="civil_engineer",
            second_earner_tier="senior")
        check(row["min_balance"] == want_min
              and row["net"] == want_net,
              f"tool: senior CE {tier} early minbal/net are"
              f" {want_min}/{want_net}",
              f"{row['min_balance']}/{row['net']}")
        check(row["end_balance"] == row["net"],
              f"tool: senior CE {tier} trajectory ends at net")

    # 4. The live measurement: the larger year-long world.
    exp = EXPECTED
    (households, cw_heads, second, senior_taxi, senior_ce,
     target_taxi, target_ce, target_head, target_member,
     senior_ce_any) = _measure("mi-seed-1")
    check(households == exp["households"],
          f"live mi-seed-1: {exp['households']} households",
          str(households))
    check(cw_heads == exp["cw_heads"],
          f"live mi-seed-1: {exp['cw_heads']} construction-"
          "worker-headed households",
          str(cw_heads))
    got = [(r["household_id"], r["prof"], r["tier"], r["wage"])
           for r in second]
    check(got == exp["second"],
          "live mi-seed-1: the second earners in those"
          " households are the measured ones",
          str(got))
    check(senior_taxi == exp["senior_taxi"],
          f"live mi-seed-1: {exp['senior_taxi']} senior-band"
          " taxi drivers",
          str(senior_taxi))
    check(senior_ce == exp["senior_ce"],
          f"live mi-seed-1: {exp['senior_ce']} senior-band"
          " civil engineers",
          str(senior_ce))
    check(target_taxi == 0,
          "live mi-seed-1: 0 senior taxi-driver second earners"
          " in construction-worker-headed households",
          str(target_taxi))
    check(target_ce == 1,
          "live mi-seed-1: 1 senior civil-engineer second"
          " earner in a construction-worker-headed household",
          str(target_ce))
    check(target_head == exp["target_head"],
          "live mi-seed-1: the target household's head is a"
          " tier-4 construction worker (Omar Sheikh)",
          str(target_head))
    check(target_member == exp["target_member"],
          "live mi-seed-1: the target second earner is Liton"
          " Tripura",
          str(target_member))
    check(senior_ce_any == exp["senior_ce_any_household"],
          "live mi-seed-1: 4 senior CE second earners in any"
          " household",
          str(senior_ce_any))

    # 5. The V7 report §29: the measurement + the decision.
    check("## 29. Addendum — Senior second earner in a larger"
          " world (Unit MI, Queue 40)" in report,
          "report §29: the addendum exists")
    s29 = report.split("## 29.")[1]
    s29_flat = " ".join(s29.split())
    check("DECIDED" in s29 and "wire the senior civil-engineer"
          " pairing" in s29_flat,
          "report §29: the wire decision is stated")
    check("mi-seed-1" in s29_flat and "300 population" in s29_flat
          and "365 days" in s29_flat,
          "report §29: the measured seed is named")
    check("HH000086" in s29_flat and "Omar Sheikh" in s29_flat
          and "Liton Tripura" in s29_flat,
          "report §29: the target household is named")
    check("30,000 − 17,758 = 12,242" in s29_flat
          or "30,000 - 17,758 = 12,242" in s29_flat,
          "report §29: the bridge line is quoted")
    check("123 households" in s29_flat
          and "9 construction-worker-headed" in s29_flat
          and "5 second earners" in s29_flat
          and "9 senior-band taxi drivers" in s29_flat
          and "20 senior-band civil engineers" in s29_flat,
          "report §29: the sweep totals are quoted")
    check("4 senior civil-engineer second earners" in s29_flat,
          "report §29: the any-household count is recorded")
    check(MI_MD5 in s29 and SH_MD5 in s29
          and MC_MD5 in s29 and SH_OLD_MD5 in s29,
          "report §29: both md5 moves are recorded")
    check("Queue 41" in s29 and "Unit MJ" in s29,
          "report §29: the follow-up names Queue 41")

    # 6. GDD-03 §2 records the MI update.
    check("Unit MI · Queue 40" in gdd03,
          "GDD-03 §2: the MI update is recorded")
    check("HH000086" in gdd03,
          "GDD-03 §2: the target household is named")
    check("30,000 − 17,758 = 12,242" in gdd03
          or "30,000 - 17,758 = 12,242" in gdd03,
          "GDD-03 §2: the bridge line is quoted")

    # 7. The economy_sim.py comments record the MI outcome.
    check("Queue 40 / Unit MI" in sim_src,
          "tool: the comments name the MI wiring")
    check("mi-seed-1" in sim_src and "report §29" in sim_src,
          "tool: the comments record the seed and §29")

    # 8. Tests pin the MI wiring.
    check("class TestSeniorSecondEarnerLargerWorld"
          in labour_tests,
          "tests: the MI guard class exists")
    check("test_no_senior_taxi_second_earner_in_any_seed"
          in labour_tests,
          "tests: the senior-taxi guard test exists")
    check("test_senior_band_wage_holds_in_every_seed"
          in labour_tests,
          "tests: the senior-band wage test exists")
    check("test_senior_civil_engineer_second_earner_is_measured"
          in regress,
          "tests: the senior CE figures test exists")
    check("test_senior_civil_engineer_bridge_line_is_wired"
          in regress,
          "tests: the bridge-line test exists")

    # 9. Scope: only the MI files changed for this unit.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 40 MI:",
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
                    "tools/sim/tests/test_economy_labour_banking.py",
                    "docs/ECONOMY-SIM-REPORT-V7.md",
                    "docs/GDD-03-ECONOMY-AND-PROFESSIONS.md",
                    "tools/verify_queue40_mi.py"},
          "scope: only the six MI files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
