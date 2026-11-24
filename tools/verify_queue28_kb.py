"""Verify Queue 28 Unit KB — Sunday-Exclusion Audit (JB
follow-up).

Checks the audit against its sources: tools/economy_sim.py
(no day-of-week exclusion in any cost or pay line — the
WORK_DAYS uses are flat, "Sunday" survives only in the
docstring and comments),
tools/sim/engine.py (the settlement's rental is flat, the
weekly tick is cadence, the taxi surge is weather),
tools/sim/labour.py (the day-wage rule counts worked days,
no weekday filter), tools/sim/scheduler.py (the
Friday/Saturday variants are schedule shaping transcribed
from the data's weekend notes — the construction worker keeps
a work block on every day including Fridays, and monthly pay
is never docked), docs/ECONOMY-SIM-REPORT-V7.md §15 (the
nine-item audit table), and
docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the KB update).
The audit finds NO fix: the tool is byte-identical, so the
pinned md5 does not move (the KA baseline stands).
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue28_kb.py
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CHECKS = []

KA_MD5 = "5f50931cbaad263812473ce1c7830e59"
FULL_NEEDS = {"hunger": 90, "thirst": 90, "sleep": 90, "rest": 90,
              "safety": 90, "social": 90, "healthcare": 90,
              "financial": 90, "education": 90, "development": 90}


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def main():
    from tools import economy_sim as econ
    sim_src = (ROOT / "tools" / "economy_sim.py").read_text()
    engine_src = (ROOT / "tools" / "sim" / "engine.py").read_text()
    labour_src = (ROOT / "tools" / "sim" / "labour.py").read_text()
    sched_src = (ROOT / "tools" / "sim" / "scheduler.py").read_text()
    regress = (ROOT / "tools" / "sim" / "tests"
               / "test_no_regression.py").read_text()
    report = (ROOT / "docs" / "ECONOMY-SIM-REPORT-V7.md").read_text()
    gdd03 = (ROOT / "docs" / "GDD-03-ECONOMY-AND-PROFESSIONS.md").read_text()
    schedules = json.loads(
        (ROOT / "data" / "npc-schedules.json").read_text())

    # 1. The tool: no day-of-week exclusion in any cost or pay
    # line. "Sunday" survives only in the module docstring
    # (the retired rules' history) and in # comments.
    check("day % 7" not in sim_src,
          "tool: no weekday arithmetic in economy_sim.py")
    check("weekday" not in sim_src.lower(),
          "tool: no 'weekday' in economy_sim.py")
    lines = sim_src.splitlines()
    doc_end = 1
    while lines[doc_end].strip() != '"""':
        doc_end += 1
    sunday_live = [f"line {i + 1}: {ln}" for i, ln in enumerate(lines)
                   if "sunday" in ln.lower()
                   and not (i <= doc_end
                            or ln.strip().startswith("#"))]
    check(not sunday_live,
          "tool: 'Sunday' only in the docstring/comments",
          "; ".join(sunday_live[:3]))
    check('["cab_rental_ncr_per_day"] * WORK_DAYS' in sim_src,
          "tool: the rental is rental_day x WORK_DAYS flat")
    check("extra_monthly = extra_daily_cost * WORK_DAYS"
          in sim_src,
          "tool: the headline extra is extra_daily_cost x"
          " WORK_DAYS")
    check("if extra_daily_cost and day <= WORK_DAYS:" in sim_src,
          "tool: the trajectory charges days 1-26")
    check(econ.WORK_DAYS == 26,
          "tool: WORK_DAYS is 26", str(econ.WORK_DAYS))

    # 2. The settlement path: the rental is flat, the weekly
    # tick is cadence, the taxi surge is weather.
    check("taxi_rental_total += rental_day * econ.WORK_DAYS"
          in engine_src,
          "settlement: _settle_month charges rental_day x"
          " WORK_DAYS flat")
    elines = engine_src.splitlines()
    idx = next(i for i, ln in enumerate(elines)
               if "day % 7 == 6" in ln)
    block = "\n".join(elines[idx:idx + 6])
    check("weekly_drift" in block and "_weekly_social" in block
          and "weekly_update" in block,
          "settlement: the day % 7 == 6 tick runs the weekly"
          " passes", block.splitlines()[0].strip())
    check(all(w not in block.lower()
              for w in ("wage", "rental", "living", "cost")),
          "settlement: the weekly tick touches no pay/cost"
          " line")
    factor = next(ln for ln in elines
                  if ln.strip().startswith("taxi_factor"))
    check("rain_days" in factor and "storm_days" in factor
          and "day % 7" not in factor,
          "settlement: the taxi surge is weather, not weekday",
          factor.strip())
    check("day % 7" not in labour_src
          and "weekday" not in labour_src.lower()
          and "sunday" not in labour_src.lower(),
          "settlement: labour.py has no weekday filter")
    # The day-wage rule counts worked days from the stored
    # schedules — storm/rest/broken-tool days pay 0 by the ES
    # rule, a worked-day rule, not a weekday rule.
    check("worked_days(store, character_id, month_index)"
          in labour_src
          and "wage_per_month / DAYS_PER_MONTH" in labour_src,
          "settlement: day-wage pay is worked days x wage/30")

    # 3. The scheduler: Friday/Saturday variants are schedule
    # shaping transcribed from the data's weekend notes — and
    # the day-wage profession keeps its work on Fridays.
    from tools.sim.tests.common import data, rng
    from tools.sim import scheduler, labour
    d = data()
    # Every profession with a weekend_variant note is handled
    # in _apply_friday (pilot: roster decides, no work blocks
    # — the function says so in a comment).
    notes = {s["profession_id"]: s.get("weekend_variant", "")
             for s in schedules["schedules"]}
    missing = [pid for pid, note in notes.items()
               if note and pid not in sched_src
               and pid != "pilot"]
    check(not missing,
          "scheduler: _apply_friday handles every profession"
          " with a weekend note", str(missing))
    check("pilot: roster decides" in sched_src,
          "scheduler: the pilot roster note is stated")
    check("teacher" in sched_src and "chef" in sched_src,
          "scheduler: _apply_saturday handles teacher + chef")

    def ctx_for(pid):
        return {"character_id": "NEX000001", "template_id": pid,
                "is_life_stage": False, "home_zone": "d1_old_town",
                "workplace_zone": d.professions[pid][
                    "workplace_zone"]}
    # The construction worker keeps a work block on every day
    # of a 30-day month, including all four Fridays.
    cw_days = []
    for day in range(30):
        blocks, _ = scheduler.instantiate(
            d, ctx_for("construction_worker"), day, rng(),
            needs=FULL_NEEDS)
        cw_days.append(any(b["activity"] == "work" for b in blocks))
    check(all(cw_days),
          "scheduler: construction worker works all 30 days",
          f"Fridays {[cw_days[i] for i in (4, 11, 18, 25)]}")
    # The Friday work loss for monthly-paid professions docks
    # nothing: pay is the monthly wage, the dock is 0.
    check(labour.broken_tool_wage_dock(None, "NEX000001", 1,
                                       22000) == 0,
          "settlement: the broken-tool dock is 0")
    monthly_ok = all(
        labour.wage_due_for(None, "NEX000001", pid, 1, wage)
        == wage
        for pid, wage in (("civil_engineer", 22000),
                          ("teacher", 15000), ("doctor", 30000),
                          ("software_developer", 28000)))
    check(monthly_ok,
          "settlement: Friday work loss docks no monthly pay")
    # Friday work presence per profession, measured live:
    # the day-wage profession keeps work; the monthly-paid
    # ones that lose it are paid monthly regardless.
    fri = {}
    for pid in d.professions:
        blocks, _ = scheduler.instantiate(
            d, ctx_for(pid), 4, rng(), needs=FULL_NEEDS)
        fri[pid] = any(b["activity"] == "work" for b in blocks)
    check(fri["construction_worker"] is True,
          "scheduler: construction worker keeps Friday work")
    check(fri["taxi_driver"] is True,
          "scheduler: taxi driver keeps Friday work (extends"
          " to 23:00)")
    check(fri["civil_engineer"] is False
          and fri["teacher"] is False
          and fri["software_developer"] is False,
          "scheduler: CE/teacher/software-dev lose Friday work"
          " (monthly pay, undocked)")

    # 4. The default run: byte-identical output, so the md5
    # does NOT move — the KA baseline stands, no re-pin.
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py")],
        capture_output=True, cwd=ROOT)
    check(out.returncode == 0, "tool: default run exits 0")
    text = out.stdout.decode()
    md5 = hashlib.md5(out.stdout).hexdigest()
    check(md5 == KA_MD5,
          "tool: default-run md5 is still the KA baseline (no"
          " re-pin)", md5)
    pinned = re.search(
        r'ECONOMY_SIM_BASELINE_MD5 = "([0-9a-f]{32})"',
        regress).group(1)
    check(pinned == KA_MD5,
          "tests: the KA md5 is still pinned in"
          " test_no_regression.py", pinned)
    check("BRIDGE FAIL rows: []" in text,
          "tool: no bridge failure in any position")

    # 5. The V7 report §15: the nine-item audit table, the
    # no-fix finding, and the open item.
    check("## 15. Addendum — Sunday-exclusion audit (Unit KB,"
          " Queue 28)" in report,
          "report §15: the addendum exists")
    check("no other day-of-week exclusion exists in any cost"
          " or pay line" in report.replace("\n", " "),
          "report §15: the no-fix finding is stated")
    check("The pinned md5 does not move" in report.replace(
        "\n", " "),
          "report §15: the md5 staying put is stated")
    check(KA_MD5 in report,
          "report §15: the KA baseline md5 is quoted")
    check("taxi weather surge" in report,
          "report §15: the taxi-surge gap is recorded")
    check("Unit KB DONE 2026-11-24" in report,
          "report §15: the audit is marked KB DONE")

    # 6. GDD-03 §2 records the KB update.
    check("Unit KB · Queue 28" in gdd03,
          "GDD-03 §2: the KB update is recorded")
    check("no other exclusion exists in any cost or pay line"
          in gdd03,
          "GDD-03 §2: the no-fix finding is quoted")
    check("the tool not modelling that surge at all is"
          " recorded as a gap" in gdd03,
          "GDD-03 §2: the taxi-surge gap is recorded")

    # 7. Tests pin the audit findings.
    check("TestSundayExclusionAudit" in regress,
          "tests: the KB audit test class exists")
    check("test_no_day_of_week_exclusion_in_economy_tool"
          in regress,
          "tests: the tool audit test exists")
    check("test_construction_worker_keeps_work_on_fridays"
          in regress,
          "tests: the Friday work test exists")
    check("test_weekly_tick_is_cadence_not_exclusion"
          in regress,
          "tests: the weekly-tick test exists")

    # 8. Scope: only the KB files changed for this unit. The
    # check reads the union of the working tree (before the
    # unit is committed) and the unit's own commit, found by
    # its message (after the commit — and still after later
    # units commit, because the message match is per-unit).
    # economy_sim.py is NOT among them: the audit found no
    # fix, so the tool is byte-identical.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 28 KB:",
         "HEAD"], capture_output=True, cwd=ROOT).stdout.decode()
    for sha in own.splitlines():
        if not sha.strip():
            continue
        shown = subprocess.run(
            ["git", "show", "--name-only", "--pretty=format:",
             sha.strip()], capture_output=True,
            cwd=ROOT).stdout.decode()
        names |= {ln for ln in shown.splitlines() if ln.strip()}
    check(names == {"tools/sim/tests/test_no_regression.py",
                    "docs/ECONOMY-SIM-REPORT-V7.md",
                    "docs/GDD-03-ECONOMY-AND-PROFESSIONS.md",
                    "tools/verify_queue28_kb.py"},
          "scope: only the four KB files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
