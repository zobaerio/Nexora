"""Verify Queue 44 Unit MM — Wire the Senior Taxi-Driver
Second Earner (ML follow-up).

Checks the decision against its sources: tools/sim/dataio.py
(TIER_WAGE_KEYS — tiers 3-5 are all paid at the senior band,
so "senior" in the live world means tier >= 3, not tier == 3),
data/prices.json (the senior taxi band: 36,000),
tools/economy_sim.py (the MM wiring — the senior taxi-driver
rows in the IC section and the bridge line in both bridge
checks; the pinned md5s MOVE; the renting senior-tier taxi
second earner stays allowed but unprinted on the re-measured
no-finding reason alone), tools/sim/tests/test_no_regression.py
(the MM figure + bridge-line tests) and
test_economy_labour_banking.py (the MM guard tests pin the
pairing-query method + the renting decision's measured basis),
docs/ECONOMY-SIM-REPORT-V7.md §33 (the measured decision)
and docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the MM update).
Re-runs the two holding seeds (ml-seed-1 and ml-seed-3, 300
population, 365 days each) and asserts both pairings
reproduce exactly (HH000030 and HH000042).
Prints one line per check and a summary; exits 0 only when
every check passes.
Run from the repo root: python3 tools/verify_queue44_mm.py
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

MM_MD5 = "47ec8771cc8bca2889d62faa3b23c6e6"
SH_MD5 = "402b9eb3e286aba1a446c0ae49b8b012"
MI_MD5 = "3d3fce982a64634a0b03bb0af3643f94"
SH_OLD_MD5 = "17bc7165d1e6ad48de4123e38e426bd7"

# The measured re-runs, from the probe run and ML's record
# (verify_queue43_ml.py EXPECTED): the household count, the
# senior-band taxi-driver and civil-engineer counts, the
# senior taxi-driver second earners in any household (with
# head wages), the senior civil-engineer second earners in
# any household, the second earners in any household, the
# two construction-worker-headed target counts, and the
# target households (head + second earner, tier + wage).
EXPECTED = {
    "ml-seed-1": {
        "households": 123, "senior_taxi": 20, "senior_ce": 15,
        "any_taxi": [
            ("HH000030", "construction_worker", 5, 20000,
             "Sohel Howlader", 4, 36000, "Ishrat Chowdhury"),
            ("HH000070", "teacher", 5, 38000, "Shilpi Ahmed",
             5, 36000, "Arif Talukder"),
            ("HH000018", "shop_owner", 5, 55000, "Liton Rahman",
             5, 36000, "Mitu Sarkar"),
            ("HH000052", "shop_owner", 3, 55000, "Roksana Hasan",
             4, 36000, "Tareq Sikder"),
            ("HH000120", "civil_engineer", 4, 65000,
             "Sharmin Miah", 5, 36000, "Mehedi Gazi"),
            ("HH000055", "software_developer", 3, 90000,
             "Fahim Saha", 5, 36000, "Tanvir Bepari"),
            ("HH000112", "software_developer", 4, 90000,
             "Salma Islam", 5, 36000, "Liton Pramanik"),
            ("HH000117", "software_developer", 5, 90000,
             "Tania Dewan", 4, 36000, "Rony Sarkar"),
            ("HH000088", "pilot", 2, 95000, "Khadija Fakir",
             5, 36000, "Rumana Mondal")],
        "senior_ce_any": 6, "second_any": 63,
        "cw_target_taxi": 1, "cw_target_ce": 1,
        "cw_taxi_households": ["HH000030"],
        "target_head": ("construction_worker", 5, 20000,
                        "Sohel Howlader"),
        "target_member": ("Ishrat Chowdhury", 4, 36000)},
    "ml-seed-3": {
        "households": 113, "senior_taxi": 12, "senior_ce": 11,
        "any_taxi": [
            ("HH000042", "construction_worker", 5, 20000,
             "Karim Biswas", 5, 36000, "Rina Saha"),
            ("HH000066", "taxi_driver", 5, 36000, "Sumon Biswas",
             4, 36000, "Sakib Pramanik"),
            ("HH000027", "shop_owner", 4, 55000, "Rafid Miah",
             4, 36000, "Niloy Sarkar"),
            ("HH000039", "civil_engineer", 4, 65000,
             "Shanto Talukder", 5, 36000, "Nabila Akter"),
            ("HH000054", "pilot", 2, 95000, "Shova Rahman",
             5, 36000, "Rahad Sardar")],
        "senior_ce_any": 2, "second_any": 71,
        "cw_target_taxi": 1, "cw_target_ce": 0,
        "cw_taxi_households": ["HH000042"],
        "target_head": ("construction_worker", 5, 20000,
                        "Karim Biswas"),
        "target_member": ("Rina Saha", 5, 36000)},
}


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


# A household pairs a construction-worker head with a second
# earner when a non-head member holds a current employment.
# Senior band = tier >= 3 (dataio.TIER_WAGE_KEYS maps tiers
# 3-5 to the senior band). The query is the ML query.
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
    """One holding-seed re-run: returns the household count,
    the senior-band counts, the senior taxi-driver second
    earners in any household (with head wages), the senior
    CE second earners in any household, the second earners
    in any household, the two construction-worker-headed
    target counts + the pairing households, and the target
    household's head and second earner.

    NOTE (Queue 44 Unit MM): the temp DB lives in a
    dedicated subdirectory of /tmp, NOT as a bare
    /tmp/tmp*.db file — a bare tmp*.db is deleted by any
    concurrent run's pre-sweep `rm -f /tmp/tmp*.db`, and
    unlinking a live SQLite file makes the next write fail
    with "attempt to write a readonly database" (proven
    live: this script's first full run died mid-ml-seed-3
    on exactly that, after ml-seed-1 had passed all 11 of
    its live checks). The checks are unchanged; only the
    temp location is collision-proof.
    """
    from tools.sim.engine import Simulation
    tmpdir = tempfile.mkdtemp(prefix="mm-verify-")
    db_path = os.path.join(tmpdir, "seed.db")
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
    senior_ce = store.row(
        "SELECT COUNT(*) AS n FROM employments"
        " WHERE profession_id = 'civil_engineer' AND tier >= 3"
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
    cw_taxi_households = store.rows(
        "SELECT h.household_id FROM households h JOIN "
        + _HEAD + " JOIN " + _MEMBER +
        " WHERE " + _CW_HEAD + " AND " + _MEMBER_NOW +
        " AND e2.profession_id = 'taxi_driver'"
        " AND e2.tier >= 3 ORDER BY h.household_id")
    target_hh = EXPECTED[seed]["cw_taxi_households"][0]
    head = store.row(
        "SELECT e.profession_id AS prof, e.tier AS tier,"
        " e.wage_per_month AS wage, c.display_name AS name"
        " FROM household_members hm JOIN employments e ON"
        " e.character_id = hm.character_id JOIN characters c"
        " ON c.character_id = hm.character_id WHERE"
        " hm.household_id = ? AND hm.role = 'head'"
        " AND hm.left_at_game_minutes IS NULL AND"
        " e.ended_at_game_minutes IS NULL",
        (target_hh,))
    member = store.row(
        "SELECT c.display_name AS name, e2.tier AS tier,"
        " e2.wage_per_month AS wage FROM household_members"
        " hm2 JOIN employments e2 ON e2.character_id ="
        " hm2.character_id JOIN characters c ON"
        " c.character_id = hm2.character_id WHERE"
        " hm2.household_id = ? AND hm2.role != 'head'"
        " AND hm2.left_at_game_minutes IS NULL AND"
        " e2.ended_at_game_minutes IS NULL AND"
        " e2.profession_id = 'taxi_driver' AND e2.tier >= 3",
        (target_hh,))
    sim.close()
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    return (households, senior_taxi, senior_ce, any_taxi,
            senior_ce_any, second_any, cw_target_taxi,
            cw_target_ce, cw_taxi_households,
            (head["prof"], head["tier"], head["wage"],
             head["name"]),
            (member["name"], member["tier"], member["wage"]))


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
    prices = econ.load("prices.json")
    bands = {w["profession_id"]: w
             for w in prices["wages_monthly"]}
    check(bands["taxi_driver"]["senior"] == 36000,
          "source: prices.json senior taxi band is 36,000")

    # 2. The tool is wired: both runs exit 0, the md5s move
    # to the MM baselines, no bridge failure, the senior
    # taxi rows print, the bridge line is 10,000 in both
    # cities, and no senior renting row is printed.
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
    check(pinned == MM_MD5,
          "tool: the pinned md5 is the MM baseline",
          pinned)
    check(MI_MD5 in regress,
          "tool: the MI baseline is kept as history",
          MI_MD5)
    check("BRIDGE FAIL rows: []" in d1_text,
          "tool: no D1 bridge failure")
    check("taxi-driver second earner (senior 36,000,"
          " per-fare)" in d1_text,
          "tool: the senior taxi rows print in the default run")
    check("construction_worker + taxi-driver (senior)"
          " start  10000 + other-tier dip       0"
          " =   10000  OK" in d1_text,
          "tool: the D1 bridge line is 10,000 + 0 = 10,000")
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
          "tool: --shibnagar md5 is the MM baseline",
          sh_md5)
    check("shibnagar BRIDGE FAIL rows: []" in sh_text,
          "tool: no Shibnagar bridge failure")
    check("construction_worker + taxi-driver (senior)"
          " start  10000 + other-tier dip       0"
          " =   10000  OK" in sh_text,
          "tool: the Shibnagar bridge line is 10,000 too")
    check("senior, renting" not in sh_text,
          "tool: the --shibnagar run prints no senior renting"
          " row")

    # 3. The wired figures, recomputed from the tool.
    w = bands["construction_worker"]
    for tier, want_net in (
            ("entry", 23950), ("mid", 27194),
            ("senior", 30651)):
        for pos in (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                    econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS):
            row = econ.simulate(
                prices, w, tier, storm_days=pos,
                second_earner="taxi_driver",
                second_earner_tier="senior")
            check(row["min_balance"] == 0
                  and row["net"] == want_net,
                  f"tool: senior taxi {tier}/{pos} minbal/net"
                  f" are 0/{want_net}",
                  f"{row['min_balance']}/{row['net']}")
            check(row["end_balance"] == row["net"],
                  f"tool: senior taxi {tier}/{pos} trajectory"
                  " ends at net")
        # The pay-timing contrast with the senior CE lump.
        ce = econ.simulate(
            prices, w, tier, storm_days=econ.STORM_EARLY_DAYS,
            second_earner="civil_engineer",
            second_earner_tier="senior")
        check(ce["min_balance"] < 0,
              f"tool: senior CE {tier} early still dips"
              " (the contrast)",
              str(ce["min_balance"]))

    # 4. The renting re-open, re-measured on ME's own terms:
    # senior wage 36,000, flat 5,200 rental; dip at every
    # tier; bridge line.
    positions = (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                 econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS)
    checked = 0
    rental_rule = True
    ends_at_net = True
    no_dip = True
    for tier in ("entry", "mid", "senior"):
        for pos in positions:
            r = econ.simulate(
                prices, w, tier, storm_days=pos,
                second_earner="taxi_driver",
                second_earner_tier="senior",
                second_earner_renting_cab=True)
            own = econ.simulate(
                prices, w, tier, storm_days=pos,
                second_earner="taxi_driver",
                second_earner_tier="senior")
            checked += 1
            if r["net"] != own["net"] - 5200:
                rental_rule = False
            if r["end_balance"] != r["net"]:
                ends_at_net = False
            if r["min_balance"] != 0:
                no_dip = False
    check(checked == 12, "tool: 12 senior renting rows computed",
          str(checked))
    check(rental_rule,
          "tool: the renting net is exactly 5,200 below the"
          " owning senior driver at every tier and position")
    check(ends_at_net,
          "tool: every senior renting trajectory ends exactly"
          " at net")
    check(no_dip,
          "tool: the renting dip is 0 at every tier and"
          " position (the row would add no finding)")
    worst_rent = min(
        econ.simulate(
            prices, w, tier, storm_days=pos,
            second_earner="taxi_driver",
            second_earner_tier="senior",
            second_earner_renting_cab=True)["min_balance"]
        for tier in ("entry", "mid", "senior")
        for pos in positions)
    check(worst_rent == 0 and 5000 + 5000 + worst_rent == 10000,
          "tool: the renting bridge line would be the trivial"
          " 10,000 + 0 = 10,000")

    # 5. The live measurement: the two holding-seed re-runs.
    for seed in ("ml-seed-1", "ml-seed-3"):
        exp = EXPECTED[seed]
        (households, senior_taxi, senior_ce, any_taxi,
         senior_ce_any, second_any, cw_target_taxi,
         cw_target_ce, cw_taxi_households, target_head,
         target_member) = _measure(seed)
        check(households == exp["households"],
              f"live {seed}: {exp['households']} households",
              str(households))
        check(senior_taxi == exp["senior_taxi"],
              f"live {seed}: {exp['senior_taxi']} senior-band"
              " taxi drivers",
              str(senior_taxi))
        check(senior_ce == exp["senior_ce"],
              f"live {seed}: {exp['senior_ce']} senior-band"
              " civil engineers",
              str(senior_ce))
        got = [(r["household_id"], r["head_prof"],
                r["head_tier"], r["head_wage"], r["head_name"],
                r["se_tier"], r["se_wage"], r["se_name"])
               for r in any_taxi]
        check(got == exp["any_taxi"],
              f"live {seed}: the senior taxi-driver second"
              " earners in any household are the measured ones",
              str(got))
        check(senior_ce_any == exp["senior_ce_any"],
              f"live {seed}: {exp['senior_ce_any']} senior CE"
              " second earners in any household",
              str(senior_ce_any))
        check(second_any == exp["second_any"],
              f"live {seed}: {exp['second_any']} second earners"
              " in any household",
              str(second_any))
        check(cw_target_taxi == exp["cw_target_taxi"],
              f"live {seed}: {exp['cw_target_taxi']} senior"
              " taxi-driver second earner in a"
              " construction-worker-headed household",
              str(cw_target_taxi))
        check(cw_target_ce == exp["cw_target_ce"],
              f"live {seed}: {exp['cw_target_ce']} senior"
              " civil-engineer second earner in a"
              " construction-worker-headed household",
              str(cw_target_ce))
        check([r["household_id"] for r in cw_taxi_households]
              == exp["cw_taxi_households"],
              f"live {seed}: the pairing household is"
              f" {exp['cw_taxi_households']}",
              str([r["household_id"]
                   for r in cw_taxi_households]))
        check(target_head == exp["target_head"],
              f"live {seed}: the target household's head is"
              " the measured construction worker",
              str(target_head))
        check(target_member == exp["target_member"],
              f"live {seed}: the target second earner is the"
              " measured senior taxi driver",
              str(target_member))

    # 6. The V7 report §33: the measurement + the decision.
    check("## 33. Addendum — Wire the senior taxi-driver"
          " second earner (Unit MM, Queue 44)" in report,
          "report §33: the addendum exists")
    s33 = report.split("## 33.")[1]
    s33_flat = " ".join(s33.split())
    check("DECIDED" in s33 and "wire the senior taxi-driver"
          " second-earner rows" in s33_flat,
          "report §33: the wire decision is stated")
    check("ml-seed-1" in s33_flat and "ml-seed-3" in s33_flat
          and "300 population" in s33_flat
          and "365 days" in s33_flat,
          "report §33: the measured seeds are named")
    check("HH000030" in s33_flat and "Sohel Howlader" in s33_flat
          and "Ishrat Chowdhury" in s33_flat
          and "HH000042" in s33_flat and "Karim Biswas" in s33_flat
          and "Rina Saha" in s33_flat,
          "report §33: both target households are named")
    check("10,000 + 0 = 10,000" in s33_flat,
          "report §33: the bridge line is quoted")
    check("23,950" in s33_flat and "27,194" in s33_flat
          and "30,651" in s33_flat,
          "report §33: the wired nets are quoted")
    check("Reason (a) FALLS" in s33
          and "Reason (b)" in s33 and "STANDS" in s33,
          "report §33: the renting re-open reasons are stated")
    check("18,750" in s33_flat and "21,994" in s33_flat
          and "25,451" in s33_flat,
          "report §33: the renting nets are quoted")
    check("stays allowed but unprinted" in s33_flat,
          "report §33: the renting decision is stated")
    check(MM_MD5 in s33 and SH_MD5 in s33
          and MI_MD5 in s33 and SH_OLD_MD5 in s33,
          "report §33: both md5 moves are recorded")
    check("Queue 45" in s33 and "Unit MN" in s33,
          "report §33: the follow-up names Queue 45")

    # 7. GDD-03 §2 records the MM update.
    check("Unit MM \u00b7 Queue 44" in gdd03,
          "GDD-03 \u00a72: the MM update is recorded")
    check("HH000030" in gdd03 and "HH000042" in gdd03,
          "GDD-03 \u00a72: the target households are named")
    check("10,000 + 0 = 10,000" in gdd03,
          "GDD-03 \u00a72: the bridge line is quoted")
    check("18,750" in gdd03 and "25,451" in gdd03,
          "GDD-03 \u00a72: the renting nets are quoted")

    # 8. The economy_sim.py comments record the MM outcome.
    check("Queue 44 / Unit MM" in sim_src,
          "tool: the comments name the MM wiring")
    check("ml-seed-1" in sim_src and "ml-seed-3" in sim_src
          and "report \u00a733" in sim_src,
          "tool: the comments record the seeds and \u00a733")
    check("re-opened 2026-11-26" in sim_src
          and "dangling argument FALLS" in sim_src,
          "tool: the ME re-open is commented at the surge"
          " table pairings list")

    # 9. Tests pin the MM wiring.
    check("class TestSeniorTaxiSecondEarnerWired"
          in labour_tests,
          "tests: the MM guard class exists")
    check("test_pairing_query_counts_senior_taxi_second_earners"
          in labour_tests,
          "tests: the pairing-query test exists")
    check("test_renting_senior_taxi_row_adds_no_finding"
          in labour_tests,
          "tests: the renting no-finding test exists")
    check("test_senior_taxi_driver_second_earner_is_measured"
          in regress,
          "tests: the senior taxi figures test exists")
    check("test_senior_taxi_driver_bridge_line_is_wired"
          in regress,
          "tests: the bridge-line test exists")
    check("re-open condition these" in labour_tests
          and "has FIRED in the full seeds" in labour_tests,
          "tests: the MI guard docstring records the fired"
          " re-open condition")

    # 10. Scope: only the MM files changed for this unit.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 44 MM:",
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
                    "tools/verify_queue44_mm.py"},
          "scope: only the six MM files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
