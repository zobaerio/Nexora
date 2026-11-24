"""Verify Queue 30 Unit KF — Business-Employed Taxi Surge
(KC follow-up).

Checks the decision against its sources: tools/sim/labour.py
(business STAFFING + civic CIVIC_RATIOS — no vacancy source
posts a taxi driver), tools/sim/admin.py (government
STAFFING), tools/sim/policies.py (the employment programme
posts construction_worker only), tools/sim/population.py +
tools/sim/decisions.py (genesis and the seek-employment hire
set no business employer; a job change takes the vacancy's
profession), tools/sim/engine.py (the surge is applied in
exactly one place — the SYS-EMPLOYERS branch; the business
path is untouched), tools/sim/tests/test_economy_labour_
banking.py (guard tests pin the audit), docs/ECONOMY-SIM-
REPORT-V7.md §19 (the measured decision), and docs/GDD-03-
ECONOMY-AND-PROFESSIONS.md §2 (the KF update). Re-runs the
live world (seed kf-measure, 120 population, 90 days) and
asserts no business-employed taxi driver exists.
Prints one line per check and a summary; exits 0 only when
every check passes.
Run from the repo root: python3 tools/verify_queue30_kf.py
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

KC_MD5 = "f6cec5a23109c4e7f9aeff3f7361e89d"


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def _measure():
    """The KF live world: returns (taxi vacancies ever, taxi
    drivers, business-employed taxi drivers, business wage
    rows to taxi drivers, taxi wage rows total, vacancy
    professions ever)."""
    from tools.sim.engine import Simulation
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(db_path)
    sim = Simulation(db_path, seed="kf-measure")
    sim.generate_population(120)
    sim.run_days(90)
    store = sim.store
    taxi_vac = store.row(
        "SELECT COUNT(*) AS n FROM vacancies WHERE"
        " profession_id = 'taxi_driver'")["n"]
    taxi_emp = store.row(
        "SELECT COUNT(*) AS n FROM employments WHERE"
        " profession_id = 'taxi_driver'"
        " AND ended_at_game_minutes IS NULL")["n"]
    biz_taxi = store.row(
        "SELECT COUNT(*) AS n FROM employments WHERE"
        " profession_id = 'taxi_driver'"
        " AND employer_business_id IS NOT NULL"
        " AND ended_at_game_minutes IS NULL")["n"]
    biz_wages = store.row(
        "SELECT COUNT(*) AS n FROM economy_ledger l"
        " JOIN employments e ON e.character_id ="
        " l.to_character_id WHERE e.profession_id ="
        " 'taxi_driver' AND l.reason_code = 'wage'"
        " AND l.from_business_id IS NOT NULL")["n"]
    taxi_wages = store.row(
        "SELECT COUNT(*) AS n FROM economy_ledger l"
        " JOIN employments e ON e.character_id ="
        " l.to_character_id WHERE e.profession_id ="
        " 'taxi_driver' AND l.reason_code = 'wage'")["n"]
    vac_profs = sorted({r["profession_id"] for r in store.rows(
        "SELECT DISTINCT profession_id FROM vacancies")})
    sim.close()
    os.remove(db_path)
    return (taxi_vac, taxi_emp, biz_taxi, biz_wages, taxi_wages,
            vac_profs)


def main():
    from tools import economy_sim as econ
    labour_src = (ROOT / "tools" / "sim" / "labour.py").read_text()
    admin_src = (ROOT / "tools" / "sim" / "admin.py").read_text()
    policies_src = (ROOT / "tools" / "sim" / "policies.py").read_text()
    population_src = (ROOT / "tools" / "sim"
                      / "population.py").read_text()
    decisions_src = (ROOT / "tools" / "sim"
                     / "decisions.py").read_text()
    engine_src = (ROOT / "tools" / "sim" / "engine.py").read_text()
    labour_tests = (ROOT / "tools" / "sim" / "tests"
                    / "test_economy_labour_banking.py").read_text()
    regress = (ROOT / "tools" / "sim" / "tests"
               / "test_no_regression.py").read_text()
    report = (ROOT / "docs" / "ECONOMY-SIM-REPORT-V7.md").read_text()
    gdd03 = (ROOT / "docs" / "GDD-03-ECONOMY-AND-PROFESSIONS.md").read_text()

    # 1. The vacancy sources, read from the source: no source
    # posts a taxi driver.
    from tools.sim import labour as labour_mod
    from tools.sim import admin as admin_mod
    business = {prof for prof, _target
                in labour_mod.STAFFING.values()}
    civic = set(labour_mod.CIVIC_RATIOS)
    government = {prof for _inst, prof, _basis
                  in admin_mod.STAFFING}
    check("taxi_driver" not in business,
          "source: business staffing posts no taxi driver",
          str(sorted(business)))
    check("taxi_driver" not in civic,
          "source: civic posts no taxi driver",
          str(sorted(civic)))
    check("taxi_driver" not in government,
          "source: government staffing posts no taxi driver",
          str(sorted(government)))
    check('profession_id="construction_worker"' in policies_src,
          "source: the employment programme posts"
          " construction_worker only")
    check(business | civic | government
          == {"chef", "construction_worker", "software_developer",
              "teacher", "doctor", "police_officer",
              "civil_engineer"},
          "source: the vacancy professions are exactly the"
          " seven known")

    # 2. The employment-creation sites: genesis and the
    # seek-employment hire set no business employer; a job
    # change takes the vacancy's profession.
    genesis = population_src.split(
        "def employ(cid, profession_id, tier, age):")[1].split(
            "def ")[0]
    check("employer_business_id" not in genesis,
          "source: genesis employments carry no business"
          " employer")
    hire = decisions_src.split("def _hire(store, data,")[1].split(
        "\n\n\n")[0]
    check("employer_business_id" not in hire,
          "source: the seek-employment hire sets no business"
          " employer")
    check('employer_business_id=best["employer_business_id"]'
          in decisions_src,
          "source: a job change takes the vacancy's business"
          " employer")
    check('profession_id=best["profession_id"]' in decisions_src,
          "source: a job change takes the vacancy's profession")

    # 3. The settlement is unchanged: the surge is applied in
    # exactly one place, and the business path has no factor.
    check(engine_src.count("taxi_factor") == 2,
          "source: taxi_factor is defined once and used once"
          " in engine.py", str(engine_src.count("taxi_factor")))
    check("taxi_factor" not in engine_src.split(
        "def _pay_business_wages")[1].split("def _pay_government")[0],
        "source: _pay_business_wages applies no surge")
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py")],
        capture_output=True, cwd=ROOT)
    check(out.returncode == 0, "tool: default run exits 0")
    md5 = hashlib.md5(out.stdout).hexdigest()
    pinned = re.search(
        r'ECONOMY_SIM_BASELINE_MD5 = "([0-9a-f]{32})"',
        regress).group(1)
    check(md5 == pinned == KC_MD5,
          "tool: default-run md5 is still the KC baseline",
          md5)

    # 4. The live measurement: the kf-measure world.
    taxi_vac, taxi_emp, biz_taxi, biz_wages, taxi_wages, \
        vac_profs = _measure()
    check(taxi_vac == 0,
          "live: 0 taxi vacancies ever posted", str(taxi_vac))
    check(taxi_emp == 4,
          "live: the world holds 4 taxi drivers", str(taxi_emp))
    check(biz_taxi == 0,
          "live: 0 business-employed taxi drivers",
          str(biz_taxi))
    check(biz_wages == 0,
          "live: 0 business wage rows to a taxi driver",
          str(biz_wages))
    check(taxi_wages == 12,
          "live: 12 taxi wage rows, all SYS-EMPLOYERS",
          str(taxi_wages))
    check(vac_profs == ["civil_engineer", "construction_worker",
                        "software_developer"],
          "live: the only vacancy professions ever posted",
          str(vac_profs))

    # 5. The V7 report §19: prose matches the measurement.
    check("## 19. Addendum — Business-employed taxi surge"
          " (Unit KF, Queue 30)" in report,
          "report §19: the addendum exists")
    check("0 taxi vacancies ever posted" in report
          and "0 business-employed" in report,
          "report §19: the measured zeros are quoted")
    check("12 taxi wage rows" in report,
          "report §19: the wage-row count is quoted")
    check("DECIDED" in report.split("## 19.")[1],
          "report §19: the no-change decision is stated")
    check("no settlement change" in report.split("## 19.")[1],
          "report §19: the decision is named")
    check("re-opens" in report.split("## 19.")[1],
          "report §19: the re-open condition is recorded")

    # 6. GDD-03 §2 records the KF update.
    check("Unit KF · Queue 30" in gdd03,
          "GDD-03 §2: the KF update is recorded")
    check("kf-measure" in gdd03,
          "GDD-03 §2: the measured world is named")

    # 7. Tests pin the KF audit.
    check("class TestBusinessEmployedTaxiSurge" in labour_tests,
          "tests: the KF guard class exists")
    check("test_no_vacancy_source_posts_taxi_driver"
          in labour_tests,
          "tests: the vacancy-source test exists")
    check("test_seeded_world_posts_no_taxi_vacancy"
          in labour_tests,
          "tests: the seeded-world test exists")

    # 8. Scope: only the KF files changed for this unit.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 30 KF:",
         "HEAD"], capture_output=True, cwd=ROOT).stdout.decode()
    for sha in own.splitlines():
        if not sha.strip():
            continue
        shown = subprocess.run(
            ["git", "show", "--name-only", "--pretty=format:",
             sha.strip()], capture_output=True,
            cwd=ROOT).stdout.decode()
        names |= {ln for ln in shown.splitlines() if ln.strip()}
    # The KE commit's files are excluded: this unit's scope is
    # its own four files (the shared docs carry both units'
    # updates, one addendum each).
    ke = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 30 KE:",
         "HEAD"], capture_output=True, cwd=ROOT).stdout.decode()
    for sha in ke.splitlines():
        if not sha.strip():
            continue
        shown = subprocess.run(
            ["git", "show", "--name-only", "--pretty=format:",
             sha.strip()], capture_output=True,
            cwd=ROOT).stdout.decode()
        names -= {ln for ln in shown.splitlines() if ln.strip()}
    check(names == {"tools/sim/tests/"
                    "test_economy_labour_banking.py",
                    "tools/verify_queue30_kf.py"},
          "scope: only the two KF-only files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
