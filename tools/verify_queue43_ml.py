"""Verify Queue 43 Unit ML — Low-Wage Head Who Is Not a
Construction Worker (MK follow-up).

Checks the decision against its sources: tools/sim/dataio.py
(TIER_WAGE_KEYS — tiers 3-5 are all paid at the senior band,
so a construction-worker head at any tier >= 3 earns the
senior 20,000; the five entry bands the sweep looks for —
shop owner 12,000, chef 13,000, taxi driver 14,000, teacher
15,000, police officer 18,000), data/prices.json (the
bands), tools/economy_sim.py (the ML comment now records
the sweep outcome — the pinned md5s do NOT move),
tools/sim/tests/test_economy_labour_banking.py (guard tests
pin the low-wage-head query method), docs/ECONOMY-SIM-
REPORT-V7.md §32 (the measured decision) and
docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the ML update).
Re-runs the MK head-wage query on five fresh seeds
(ml-seed-1..5, 300 population, 365 days each) and asserts
the measured outcome: a low-wage non-construction-worker
head DOES exist (ml-seed-1 HH000035, shop-owner head
Sabbir Fakir at the entry 12,000) but holds no senior
taxi-driver second earner — and the pairing appears under
a construction-worker head TWICE (ml-seed-1 HH000030 and
ml-seed-3 HH000042, both heads at exactly 20,000), so
the §12 taxi half is refuted and neither the profession
nor the wage band blocks it. Prints one line per check
and a summary; exits 0 only when every check passes.
Run from the repo root: python3 tools/verify_queue43_ml.py
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
# household count, the senior-band taxi-driver and civil-
# engineer counts, the senior taxi-driver second earners
# in any household (household, head profession, head tier,
# head wage, head name, second earner tier, wage, second
# earner name), the senior civil-engineer second earners
# in any household, the second earners in any household,
# the construction-worker-headed target counts + the
# pairing households, the heads earning <= 20,000
# (household, profession, tier, wage, name), the lowest
# head wage, the heads below 20,000 and at 20,000, the
# construction-worker heads (household, tier, wage, name
# — all at the flat senior 20,000), and the low-wage
# non-construction-worker heads + the senior taxi-driver
# second earners under one.
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
        "le20_heads": [
            ("HH000035", "shop_owner", 1, 12000, "Sabbir Fakir"),
            ("HH000007", "construction_worker", 3, 20000,
             "Liton Khan"),
            ("HH000027", "construction_worker", 4, 20000,
             "Shamima Hasan"),
            ("HH000030", "construction_worker", 5, 20000,
             "Sohel Howlader"),
            ("HH000061", "construction_worker", 5, 20000,
             "Shakil Tripura"),
            ("HH000069", "construction_worker", 5, 20000,
             "Nasrin Miah"),
            ("HH000073", "construction_worker", 5, 20000,
             "Jahid Khan"),
            ("HH000100", "construction_worker", 3, 20000,
             "Taslima Kazi"),
            ("HH000107", "construction_worker", 4, 20000,
             "Farhan Hossain"),
            ("HH000118", "construction_worker", 5, 20000,
             "Mushfiq Mir")],
        "lowest_head_wage": 12000, "below_20000": 1,
        "at_20000": 9,
        "cw_heads": [
            ("HH000007", 3, 20000, "Liton Khan"),
            ("HH000027", 4, 20000, "Shamima Hasan"),
            ("HH000030", 5, 20000, "Sohel Howlader"),
            ("HH000061", 5, 20000, "Shakil Tripura"),
            ("HH000069", 5, 20000, "Nasrin Miah"),
            ("HH000073", 5, 20000, "Jahid Khan"),
            ("HH000100", 3, 20000, "Taslima Kazi"),
            ("HH000107", 4, 20000, "Farhan Hossain"),
            ("HH000118", 5, 20000, "Mushfiq Mir")],
        "noncw_le20_heads": [
            ("HH000035", "shop_owner", 1, 12000, "Sabbir Fakir")],
        "noncw_le20_taxi": 0},
    "ml-seed-2": {
        "households": 124, "senior_taxi": 7, "senior_ce": 13,
        "any_taxi": [
            ("HH000055", "pilot", 1, 45000, "Anik Howlader",
             4, 36000, "Niloy Ahmed"),
            ("HH000080", "civil_engineer", 5, 65000,
             "Sumaya Matubbar", 5, 36000, "Shahana Kazi")],
        "senior_ce_any": 5, "second_any": 63,
        "cw_target_taxi": 0, "cw_target_ce": 0,
        "cw_taxi_households": [],
        "le20_heads": [
            ("HH000038", "construction_worker", 5, 20000,
             "Nasrin Fakir"),
            ("HH000041", "construction_worker", 5, 20000,
             "Imran Hasan"),
            ("HH000047", "construction_worker", 4, 20000,
             "Nasrin Mir"),
            ("HH000058", "construction_worker", 5, 20000,
             "Rumana Kazi"),
            ("HH000081", "construction_worker", 4, 20000,
             "Champa Bepari"),
            ("HH000092", "construction_worker", 5, 20000,
             "Jannat Mondal"),
            ("HH000098", "construction_worker", 5, 20000,
             "Rina Pal")],
        "lowest_head_wage": 20000, "below_20000": 0,
        "at_20000": 7,
        "cw_heads": [
            ("HH000038", 5, 20000, "Nasrin Fakir"),
            ("HH000041", 5, 20000, "Imran Hasan"),
            ("HH000047", 4, 20000, "Nasrin Mir"),
            ("HH000058", 5, 20000, "Rumana Kazi"),
            ("HH000081", 4, 20000, "Champa Bepari"),
            ("HH000092", 5, 20000, "Jannat Mondal"),
            ("HH000098", 5, 20000, "Rina Pal")],
        "noncw_le20_heads": [],
        "noncw_le20_taxi": 0},
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
        "le20_heads": [
            ("HH000003", "construction_worker", 5, 20000,
             "Sumon Ghosh"),
            ("HH000033", "construction_worker", 5, 20000,
             "Habiba Marma"),
            ("HH000042", "construction_worker", 5, 20000,
             "Karim Biswas"),
            ("HH000050", "construction_worker", 5, 20000,
             "Sumon Akter"),
            ("HH000055", "construction_worker", 5, 20000,
             "Pranto Sikder"),
            ("HH000094", "construction_worker", 5, 20000,
             "Mariam Biswas")],
        "lowest_head_wage": 20000, "below_20000": 0,
        "at_20000": 6,
        "cw_heads": [
            ("HH000003", 5, 20000, "Sumon Ghosh"),
            ("HH000033", 5, 20000, "Habiba Marma"),
            ("HH000042", 5, 20000, "Karim Biswas"),
            ("HH000050", 5, 20000, "Sumon Akter"),
            ("HH000055", 5, 20000, "Pranto Sikder"),
            ("HH000094", 5, 20000, "Mariam Biswas")],
        "noncw_le20_heads": [],
        "noncw_le20_taxi": 0},
    "ml-seed-4": {
        "households": 113, "senior_taxi": 12, "senior_ce": 16,
        "any_taxi": [
            ("HH000093", "teacher", 5, 38000, "Farida Sheikh",
             5, 36000, "Shakil Pal"),
            ("HH000082", "shop_owner", 5, 55000, "Shova Bepari",
             5, 36000, "Mitu Matubbar")],
        "senior_ce_any": 11, "second_any": 62,
        "cw_target_taxi": 0, "cw_target_ce": 1,
        "cw_taxi_households": [],
        "le20_heads": [
            ("HH000008", "construction_worker", 5, 20000,
             "Jamal Dewan"),
            ("HH000031", "construction_worker", 3, 20000,
             "Rani Pramanik"),
            ("HH000033", "construction_worker", 5, 20000,
             "Dolly Das"),
            ("HH000046", "construction_worker", 3, 20000,
             "Rakib Khan"),
            ("HH000047", "construction_worker", 5, 20000,
             "Hridoy Begum"),
            ("HH000053", "construction_worker", 4, 20000,
             "Nabila Hossain"),
            ("HH000060", "construction_worker", 5, 20000,
             "Ishrat Begum"),
            ("HH000062", "construction_worker", 5, 20000,
             "Roksana Howlader"),
            ("HH000066", "construction_worker", 5, 20000,
             "Arif Mondal"),
            ("HH000099", "construction_worker", 5, 20000,
             "Shahana Hossain"),
            ("HH000101", "construction_worker", 5, 20000,
             "Rakib Uddin")],
        "lowest_head_wage": 20000, "below_20000": 0,
        "at_20000": 11,
        "cw_heads": [
            ("HH000008", 5, 20000, "Jamal Dewan"),
            ("HH000031", 3, 20000, "Rani Pramanik"),
            ("HH000033", 5, 20000, "Dolly Das"),
            ("HH000046", 3, 20000, "Rakib Khan"),
            ("HH000047", 5, 20000, "Hridoy Begum"),
            ("HH000053", 4, 20000, "Nabila Hossain"),
            ("HH000060", 5, 20000, "Ishrat Begum"),
            ("HH000062", 5, 20000, "Roksana Howlader"),
            ("HH000066", 5, 20000, "Arif Mondal"),
            ("HH000099", 5, 20000, "Shahana Hossain"),
            ("HH000101", 5, 20000, "Rakib Uddin")],
        "noncw_le20_heads": [],
        "noncw_le20_taxi": 0},
    "ml-seed-5": {
        "households": 129, "senior_taxi": 13, "senior_ce": 16,
        "any_taxi": [
            ("HH000046", "teacher", 3, 38000,
             "Shamima Howlader", 5, 36000, "Sumon Molla"),
            ("HH000125", "pilot", 3, 180000, "Khadija Fakir",
             5, 36000, "Beauty Marma"),
            ("HH000053", "business_owner", 5, 300000,
             "Monira Sikder", 5, 36000, "Mizan Rahman"),
            ("HH000110", "business_owner", 4, 300000,
             "Fahim Islam", 4, 36000, "Anik Rahman")],
        "senior_ce_any": 5, "second_any": 74,
        "cw_target_taxi": 0, "cw_target_ce": 1,
        "cw_taxi_households": [],
        "le20_heads": [
            ("HH000011", "construction_worker", 5, 20000,
             "Rahad Chakma"),
            ("HH000019", "construction_worker", 5, 20000,
             "Taslima Fakir"),
            ("HH000042", "construction_worker", 5, 20000,
             "Nusrat Hossain"),
            ("HH000051", "construction_worker", 5, 20000,
             "Shamima Barua"),
            ("HH000081", "construction_worker", 4, 20000,
             "Nabil Miah"),
            ("HH000086", "construction_worker", 5, 20000,
             "Rafid Hasan"),
            ("HH000090", "construction_worker", 5, 20000,
             "Omar Dewan"),
            ("HH000100", "construction_worker", 5, 20000,
             "Mitu Kazi"),
            ("HH000102", "construction_worker", 5, 20000,
             "Tamim Chowdhury"),
            ("HH000109", "construction_worker", 5, 20000,
             "Farhana Molla"),
            ("HH000127", "construction_worker", 5, 20000,
             "Shakil Miah")],
        "lowest_head_wage": 20000, "below_20000": 0,
        "at_20000": 11,
        "cw_heads": [
            ("HH000011", 5, 20000, "Rahad Chakma"),
            ("HH000019", 5, 20000, "Taslima Fakir"),
            ("HH000042", 5, 20000, "Nusrat Hossain"),
            ("HH000051", 5, 20000, "Shamima Barua"),
            ("HH000081", 4, 20000, "Nabil Miah"),
            ("HH000086", 5, 20000, "Rafid Hasan"),
            ("HH000090", 5, 20000, "Omar Dewan"),
            ("HH000100", 5, 20000, "Mitu Kazi"),
            ("HH000102", 5, 20000, "Tamim Chowdhury"),
            ("HH000109", 5, 20000, "Farhana Molla"),
            ("HH000127", 5, 20000, "Shakil Miah")],
        "noncw_le20_heads": [],
        "noncw_le20_taxi": 0},
}


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


# A household has a second earner when a non-head member
# holds a current employment. Senior band = tier >= 3
# (dataio.TIER_WAGE_KEYS maps tiers 3-5 to the senior band).
# The ML query is the MK head-wage query, restricted to
# heads earning <= 20,000, with the head's profession
# beside its wage.
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
    senior-band taxi-driver and civil-engineer counts, the
    senior taxi-driver second earners in any household
    (with head wages), the senior civil-engineer second
    earners in any household, the second earners in any
    household, the two construction-worker-headed target
    counts + the pairing households, the heads earning
    <= 20,000, the lowest head wage, the heads below and at
    20,000, the construction-worker heads, and the low-wage
    non-construction-worker heads + the senior taxi-driver
    second earners under one."""
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
    le20_heads = store.rows(
        "SELECT h.household_id, e.profession_id AS prof,"
        " e.tier, e.wage_per_month AS wage,"
        " c.display_name AS name FROM households h JOIN "
        + _HEAD + " JOIN characters c ON c.character_id ="
        " hm.character_id WHERE " + _HEAD_NOW +
        " AND e.wage_per_month <= 20000"
        " ORDER BY e.wage_per_month, h.household_id")
    lowest = store.row(
        "SELECT MIN(e.wage_per_month) AS mn FROM households h"
        " JOIN " + _HEAD + " WHERE " + _HEAD_NOW)["mn"]
    below = store.row(
        "SELECT COUNT(*) AS n FROM households h JOIN " + _HEAD +
        " WHERE " + _HEAD_NOW +
        " AND e.wage_per_month < 20000")["n"]
    at = store.row(
        "SELECT COUNT(*) AS n FROM households h JOIN " + _HEAD +
        " WHERE " + _HEAD_NOW +
        " AND e.wage_per_month = 20000")["n"]
    cw_heads = store.rows(
        "SELECT h.household_id, e.tier, e.wage_per_month,"
        " c.display_name FROM households h JOIN " + _HEAD +
        " JOIN characters c ON c.character_id ="
        " hm.character_id WHERE " + _HEAD_NOW +
        " AND e.profession_id = 'construction_worker'"
        " ORDER BY e.wage_per_month, h.household_id")
    noncw_le20_heads = store.rows(
        "SELECT h.household_id, e.profession_id AS prof,"
        " e.tier, e.wage_per_month AS wage,"
        " c.display_name AS name FROM households h JOIN "
        + _HEAD + " JOIN characters c ON c.character_id ="
        " hm.character_id WHERE " + _HEAD_NOW +
        " AND e.wage_per_month <= 20000"
        " AND e.profession_id != 'construction_worker'"
        " ORDER BY e.wage_per_month, h.household_id")
    noncw_le20_taxi = store.row(
        "SELECT COUNT(*) AS n FROM households h JOIN " + _HEAD +
        " JOIN " + _MEMBER +
        " WHERE " + _HEAD_NOW + " AND " + _MEMBER_NOW +
        " AND e2.profession_id = 'taxi_driver'"
        " AND e2.tier >= 3 AND e.wage_per_month <= 20000"
        " AND e.profession_id != 'construction_worker'")["n"]
    sim.close()
    os.remove(db_path)
    return (households, senior_taxi, senior_ce, any_taxi,
            senior_ce_any, second_any, cw_target_taxi,
            cw_target_ce,
            [r["household_id"] for r in cw_taxi_households],
            [(r["household_id"], r["prof"], r["tier"],
              r["wage"], r["name"]) for r in le20_heads],
            lowest, below, at,
            [(r["household_id"], r["tier"],
              r["wage_per_month"], r["display_name"])
             for r in cw_heads],
            [(r["household_id"], r["prof"], r["tier"],
              r["wage"], r["name"]) for r in noncw_le20_heads],
            noncw_le20_taxi)


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
    check(data.wage_at("shop_owner", 1) == 12000
          and data.wage_at("chef", 1) == 13000
          and data.wage_at("taxi_driver", 1) == 14000
          and data.wage_at("teacher", 1) == 15000
          and data.wage_at("police_officer", 1) == 18000,
          "source: the five entry wages are 12,000 / 13,000 /"
          " 14,000 / 15,000 / 18,000")
    prices = econ.load("prices.json")
    bands = {w["profession_id"]: w
             for w in prices["wages_monthly"]}
    check(bands["taxi_driver"]["senior"] == 36000
          and bands["civil_engineer"]["senior"] == 65000
          and bands["construction_worker"]["senior"] == 20000
          and bands["shop_owner"]["entry"] == 12000,
          "source: prices.json bands are 36,000 / 65,000 /"
          " 20,000 / 12,000")

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

    # 3. The live measurement: the five fresh year-long
    # worlds, with the head wage joined.
    total_hh = total_st = total_sce = total_any = 0
    total_sce_any = total_second = total_tt = total_tc = 0
    total_le20 = total_below = total_at = total_cw = 0
    total_noncw = total_noncw_taxi = 0
    for seed, exp in EXPECTED.items():
        (households, senior_taxi, senior_ce, any_taxi,
         senior_ce_any, second_any, cw_target_taxi,
         cw_target_ce, cw_taxi_households, le20_heads,
         lowest, below, at, cw_heads, noncw_le20_heads,
         noncw_le20_taxi) = _measure(seed)
        total_hh += households
        total_st += senior_taxi
        total_sce += senior_ce
        total_any += len(any_taxi)
        total_sce_any += senior_ce_any
        total_second += second_any
        total_tt += cw_target_taxi
        total_tc += cw_target_ce
        total_le20 += len(le20_heads)
        total_below += below
        total_at += at
        total_cw += len(cw_heads)
        total_noncw += len(noncw_le20_heads)
        total_noncw_taxi += noncw_le20_taxi
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
              f"live {seed}: the senior taxi second earners"
              " in any household are the measured ones, with"
              " head wages",
              str(got))
        check(senior_ce_any == exp["senior_ce_any"],
              f"live {seed}: {exp['senior_ce_any']} senior CE"
              " second earners in any household",
              str(senior_ce_any))
        check(second_any == exp["second_any"],
              f"live {seed}: {exp['second_any']} second"
              " earners in any household",
              str(second_any))
        check(cw_target_taxi == exp["cw_target_taxi"],
              f"live {seed}: {exp['cw_target_taxi']} senior"
              " taxi-driver second earner under a"
              " construction-worker head",
              str(cw_target_taxi))
        check(cw_taxi_households == exp["cw_taxi_households"],
              f"live {seed}: the construction-worker-headed"
              f" taxi pairing is {exp['cw_taxi_households']}",
              str(cw_taxi_households))
        check(cw_target_ce == exp["cw_target_ce"],
              f"live {seed}: {exp['cw_target_ce']} senior"
              " civil-engineer second earner under a"
              " construction-worker head",
              str(cw_target_ce))
        check(le20_heads == exp["le20_heads"],
              f"live {seed}: the {len(exp['le20_heads'])}"
              " heads earning <= 20,000 are the measured"
              " ones",
              str(le20_heads))
        check(lowest == exp["lowest_head_wage"],
              f"live {seed}: lowest head wage is"
              f" {exp['lowest_head_wage']}",
              str(lowest))
        check(below == exp["below_20000"],
              f"live {seed}: {exp['below_20000']} heads earn"
              " below 20,000",
              str(below))
        check(at == exp["at_20000"],
              f"live {seed}: {exp['at_20000']} heads earn"
              " exactly 20,000",
              str(at))
        check(cw_heads == exp["cw_heads"],
              f"live {seed}: the {len(exp['cw_heads'])}"
              " construction-worker heads are the measured"
              " ones, all at 20,000",
              str(cw_heads))
        check(all(w == 20000 for _h, _t, w, _n in cw_heads),
              f"live {seed}: every construction-worker head"
              " earns exactly 20,000")
        check(noncw_le20_heads == exp["noncw_le20_heads"],
              f"live {seed}: the low-wage non-construction-"
              f"worker heads are {exp['noncw_le20_heads']}",
              str(noncw_le20_heads))
        check(noncw_le20_taxi == 0,
              f"live {seed}: 0 senior taxi second earners"
              " under a low-wage non-construction-worker"
              " head",
              str(noncw_le20_taxi))
    check(total_hh == 602,
          "live totals: 602 households across the five seeds",
          str(total_hh))
    check(total_st == 64,
          "live totals: 64 senior-band taxi drivers",
          str(total_st))
    check(total_sce == 71,
          "live totals: 71 senior-band civil engineers",
          str(total_sce))
    check(total_any == 22,
          "live totals: 22 senior taxi second earners in any"
          " household",
          str(total_any))
    check(total_sce_any == 29,
          "live totals: 29 senior CE second earners in any"
          " household",
          str(total_sce_any))
    check(total_second == 333,
          "live totals: 333 second earners in any household",
          str(total_second))
    check(total_tt == 2,
          "live totals: 2 senior taxi-driver second earners"
          " under a construction-worker head",
          str(total_tt))
    check(total_tc == 3,
          "live totals: 3 senior civil-engineer second"
          " earners under a construction-worker head",
          str(total_tc))
    check(total_le20 == 45,
          "live totals: 45 heads earn <= 20,000 across the"
          " five seeds",
          str(total_le20))
    check(total_below == 1,
          "live totals: 1 head earns below 20,000",
          str(total_below))
    check(total_at == 44,
          "live totals: 44 heads earn exactly 20,000",
          str(total_at))
    check(total_cw == 44,
          "live totals: 44 construction-worker heads, all at"
          " exactly 20,000",
          str(total_cw))
    check(total_noncw == 1,
          "live totals: 1 low-wage head who is not a"
          " construction worker",
          str(total_noncw))
    check(total_noncw_taxi == 0,
          "live totals: 0 senior taxi second earners under a"
          " low-wage non-construction-worker head",
          str(total_noncw_taxi))

    # 4. The V7 report §32: the measurement + the decision.
    check("## 32. Addendum — Low-wage head who is not a"
          " construction worker (Unit ML, Queue 43)"
          in report,
          "report §32: the addendum exists")
    s32 = report.split("## 32.")[1]
    s32_flat = " ".join(s32.split())
    check("DECIDED" in s32 and "profession explanation is"
          " refuted" in s32_flat,
          "report §32: the refuted-profession decision is"
          " stated")
    check("§12 taxi half falls" in s32_flat,
          "report §32: the §12 taxi half is recorded as"
          " fallen")
    check("HH000030" in s32_flat and "Sohel Howlader"
          in s32_flat and "Ishrat Chowdhury" in s32_flat,
          "report §32: the ml-seed-1 pairing is named")
    check("HH000042" in s32_flat and "Karim Biswas"
          in s32_flat and "Rina Saha" in s32_flat,
          "report §32: the ml-seed-3 pairing is named")
    check("HH000035" in s32_flat and "Sabbir Fakir"
          in s32_flat and "12,000" in s32_flat,
          "report §32: the entry-wage head is named")
    check("ml-seed-1" in s32_flat and "ml-seed-5" in s32_flat
          and "300 population" in s32_flat
          and "365 days" in s32_flat,
          "report §32: the five measured seeds are named")
    check("2 senior taxi-driver second earners under a"
          " construction-worker head" in s32_flat,
          "report §32: the headline pairing count is quoted")
    check("45 heads earn <= 20,000" in s32_flat
          and "44 are construction workers" in s32_flat,
          "report §32: the low-wage head counts are quoted")
    check("chance on a thin base" in s32_flat,
          "report §32: the chance explanation is stated")
    check("does NOT move" in s32 and MI_MD5 in s32
          and SH_MD5 in s32,
          "report §32: both md5 notes are recorded")
    check("Queue 44" in s32 and "Unit MM" in s32,
          "report §32: the follow-up names Queue 44")

    # 5. GDD-03 §2 records the ML update.
    check("Unit ML · Queue 43" in gdd03,
          "GDD-03 §2: the ML update is recorded")
    check("Sabbir Fakir" in gdd03,
          "GDD-03 §2: the entry-wage head is named")
    check("§12 taxi half falls" in gdd03,
          "GDD-03 §2: the fallen §12 half is quoted")

    # 6. The economy_sim.py comment records the ML outcome.
    check("Queue 43 / Unit ML" in sim_src,
          "tool: the comment names the ML sweep")
    check("HH000030" in sim_src and "HH000042" in sim_src
          and "report §32" in sim_src,
          "tool: the comment records both pairings and §32")

    # 7. Tests pin the ML sweep.
    check("class TestLowWageHeadNotConstructionWorker"
          in labour_tests,
          "tests: the ML guard class exists")
    check("test_low_wage_head_query_returns_profession_and_"
          "current_wage" in labour_tests,
          "tests: the low-wage-head query test exists")
    check("test_entry_band_wages_are_the_sweep_targets"
          in labour_tests,
          "tests: the entry-band wage test exists")

    # 8. Scope: only the ML files changed for this unit.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 43 ML:",
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
                    "tools/verify_queue43_ml.py"},
          "scope: only the five ML files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
