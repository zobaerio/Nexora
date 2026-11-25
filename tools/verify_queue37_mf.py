"""Verify Queue 37 Unit MF — Senior Second Earner Live-World
Check (ME follow-up).

Checks the decision against its sources: tools/sim/dataio.py
(TIER_WAGE_KEYS — tiers 3-5 are all paid at the senior band,
so "senior" in the live world means tier >= 3, not tier == 3),
data/prices.json (the senior bands: taxi 36,000, civil
engineer 65,000), tools/economy_sim.py (the ME comment now
records the MF outcome — the pinned md5s do NOT move),
tools/sim/tests/test_economy_labour_banking.py (guard tests
pin the measurement), docs/ECONOMY-SIM-REPORT-V7.md §26 (the
measured decision) and docs/GDD-03-ECONOMY-AND-PROFESSIONS.md
§2 (the MF update). Re-runs the live world (seed mf-measure,
120 population, 90 days) and asserts no construction-worker-
headed household has a senior taxi-driver or senior civil-
engineer second earner.
Prints one line per check and a summary; exits 0 only when
every check passes.
Run from the repo root: python3 tools/verify_queue37_mf.py
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


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


# A household pairs a construction-worker head with a second
# earner when a non-head member holds a current employment.
# Senior band = tier >= 3 (dataio.TIER_WAGE_KEYS maps tiers
# 3-5 to the senior band — a tier-4 taxi driver earns 36,000,
# the senior wage, and a tier == 3 check would miss them).
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


def _measure():
    """The MF live world: returns the household counts, the
    second-earner rows in construction-worker-headed
    households, the senior-band drivers/engineers, and the
    two target counts."""
    from tools.sim.engine import Simulation
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(db_path)
    sim = Simulation(db_path, seed="mf-measure")
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
    senior_taxi = store.rows(
        "SELECT character_id, tier, wage_per_month FROM"
        " employments WHERE profession_id = 'taxi_driver'"
        " AND tier >= 3 AND ended_at_game_minutes IS NULL")
    senior_ce = store.rows(
        "SELECT character_id, tier, wage_per_month FROM"
        " employments WHERE profession_id = 'civil_engineer'"
        " AND tier >= 3 AND ended_at_game_minutes IS NULL")
    taxi_role = store.rows(
        "SELECT hm.household_id, hm.role FROM household_members"
        " hm JOIN employments e ON e.character_id ="
        " hm.character_id WHERE e.profession_id = 'taxi_driver'"
        " AND e.tier >= 3 AND e.ended_at_game_minutes IS NULL"
        " AND hm.left_at_game_minutes IS NULL")
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
            taxi_role, target_taxi, target_ce)


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
    # the MD baselines, no bridge failure, no senior renting
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
          "tool: --shibnagar md5 matches the §25 record",
          sh_md5)
    check("shibnagar BRIDGE FAIL rows: []" in sh_text,
          "tool: no Shibnagar bridge failure")
    check("senior, renting" not in sh_text,
          "tool: the --shibnagar run prints no senior renting"
          " row")

    # 3. The live measurement: the mf-measure world.
    (households, cw_heads, second, senior_taxi, senior_ce,
     taxi_role, target_taxi, target_ce) = _measure()
    check(households == 55,
          "live: the world holds 55 households", str(households))
    check(cw_heads == 4,
          "live: 4 construction-worker-headed households",
          str(cw_heads))
    got = [(r["household_id"], r["prof"], r["tier"], r["wage"])
           for r in second]
    check(got == [("HH000043", "construction_worker", 2, 14000),
                  ("HH000054", "police_officer", 2, 28000)],
          "live: the only second earners in those households"
          " are a mid construction worker and a mid police"
          " officer", str(got))
    check(len(senior_taxi) == 1
          and senior_taxi[0]["character_id"] == "NEX000032"
          and senior_taxi[0]["tier"] == 4
          and senior_taxi[0]["wage_per_month"] == 36000,
          "live: exactly 1 senior-band taxi driver — tier 4,"
          " 36,000 (a tier == 3 check would have missed them)",
          str([dict(r) for r in senior_taxi]))
    check(len(taxi_role) == 1
          and taxi_role[0]["household_id"] == "HH000017"
          and taxi_role[0]["role"] == "head",
          "live: that senior-band taxi driver is a household"
          " head, not a second earner",
          str([dict(r) for r in taxi_role]))
    check(len(senior_ce) == 0,
          "live: 0 senior-band civil engineers in the world",
          str(len(senior_ce)))
    check(target_taxi == 0,
          "live: 0 senior taxi-driver second earners in"
          " construction-worker-headed households",
          str(target_taxi))
    check(target_ce == 0,
          "live: 0 senior civil-engineer second earners in"
          " construction-worker-headed households",
          str(target_ce))

    # 4. The V7 report §26: the measurement + the decision.
    check("## 26. Addendum — Senior second earner live-world"
          " check (Unit MF, Queue 37)" in report,
          "report §26: the addendum exists")
    s26 = report.split("## 26.")[1]
    s26_flat = " ".join(s26.split())
    check("DECIDED" in s26 and "§12 rule stands" in s26,
          "report §26: the no-change decision is stated")
    check("mf-measure" in s26_flat and "120 population" in s26_flat
          and "90 days" in s26_flat,
          "report §26: the measured world is named")
    check("0 senior taxi-driver second earners" in s26
          and "0 senior civil-engineer second earners" in s26,
          "report §26: the target zeros are quoted")
    check("tier >= 3" in s26 and "TIER_WAGE_KEYS" in s26
          and "NEX000032" in s26,
          "report §26: the senior-band definition and the"
          " one senior-band driver are recorded")
    check("does NOT move" in s26 and MC_MD5 in s26
          and SH_MD5 in s26,
          "report §26: both md5 notes are recorded")
    check("Queue 38" in s26 and "Unit MG" in s26,
          "report §26: the follow-up names Queue 38")

    # 5. GDD-03 §2 records the MF update.
    check("Unit MF · Queue 37" in gdd03,
          "GDD-03 §2: the MF update is recorded")
    check("mf-measure" in gdd03,
          "GDD-03 §2: the measured world is named")
    check("§12 rule stands" in gdd03,
          "GDD-03 §2: the decision is quoted")

    # 6. The economy_sim.py comment records the MF outcome.
    check("Queue 37 Unit MF" in sim_src,
          "tool: the ME comment still names the reopen"
          " condition")
    check("MF checked" in sim_src and "mf-measure" in sim_src,
          "tool: the comment records the MF outcome")

    # 7. Tests pin the MF measurement.
    check("class TestSeniorSecondEarnerLiveWorld" in labour_tests,
          "tests: the MF guard class exists")
    check("test_no_senior_second_earner_in_seeded_world"
          in labour_tests,
          "tests: the seeded-world test exists")
    check("test_senior_band_is_tier_three_or_higher"
          in labour_tests,
          "tests: the senior-band definition test exists")

    # 8. Scope: only the MF files changed for this unit.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 37 MF:",
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
                    "tools/verify_queue37_mf.py"},
          "scope: only the five MF files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
