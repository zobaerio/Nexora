"""Session 04 Unit 03 — Labour Market.

Employment stops being only a genesis fact and a daily decision:
employers post vacancies, unemployed people apply, and hiring is
a recorded match between the two.

- Vacancies: businesses post for the staff their category needs
  (STAFFING below — SIM MODEL headcount targets, labelled),
  gated by solvency: a business may post only while its balance
  covers the configured wage reserve for its whole wage bill
  including the new hire. An employer who cannot pay cannot
  hire — and if it later cannot pay, the settlement's business
  wage pass pays what exists, records the shortfall, and the
  distress machinery (business.py) takes its course. Civic
  employers (school, clinic, police) post against population
  ratios (SIM MODEL) and pay through the existing civic payroll.
- Applications: every unemployed adult who is not in college
  applies to open vacancies they are eligible for. Eligibility
  reuses Session 02's credential gates verbatim (doctor, teacher,
  civil engineer, software developer require the completed
  college credential) plus the profession's skill base.
- Matching: score = primary-skill sum + discipline/intelligence
  fit + a seeded jitter. The best applicant is hired: an
  employment row appears carrying employer_business_id (or the
  civic employer), the vacancy fills, the losing applications
  close. Wages for business hires are paid by the business
  account at settlement (engine._pay_business_wages); civic
  wages keep the SYS-EMPLOYERS payroll.
- Separations: employees of a distressed business may resign to
  an open vacancy elsewhere; a distressed business sheds its
  newest hire. Both are recorded with causes. (Business closure
  layoffs live in business.py.)

Unemployment is measured, not asserted: labour force = living
residents aged 18-64 who are not enrolled in college; the rate
feeds Unit 11's indicators and Unit 12's crisis detection.
"""
import json

from . import business as business_mod
from . import cities as cities_mod

# SIM MODEL staffing targets: employees per business by category,
# and the profession they are hired as. Retail and fishing stay
# owner/crew-run (their Session 01 professions already people
# them); there is no shop-assistant or farmhand profession in the
# canonical 11, so floor staff are hired as construction_worker
# (manual labour) and kitchen staff as chef — documented here.
STAFFING = {
    "food_service": ("chef", 2),
    "manufacturing": ("construction_worker", 3),
    "food_processing": ("construction_worker", 2),
    "agriculture": ("construction_worker", 2),
    "professional_services": ("software_developer", 2),
}
# SIM MODEL civic posts per 100 residents, by profession.
CIVIC_RATIOS = {"teacher": 1.2, "doctor": 0.8, "police_officer": 1.0}
CIVIC_CITY = cities_mod.RUPSHA  # District 1 hosts the institutions


def _post_vacancy(store, *, employer_kind, business_id, profession_id,
                  city_id, wage, month_index, game_minutes):
    vid = store.next_id("VC", "vacancies", "vacancy_id")
    store.insert("vacancies", vacancy_id=vid,
                 employer_kind=employer_kind,
                 employer_business_id=business_id,
                 profession_id=profession_id, city_id=city_id,
                 wage_per_month=wage, status="open",
                 posted_month=month_index,
                 created_at_game_minutes=game_minutes)
    return vid


def post_vacancies(store, data, month_index, game_minutes,
                   hiring_freeze=False):
    """Employers post this month's vacancies. Returns the ids."""
    posted = []
    if hiring_freeze:
        return posted  # Unit 12: a live crisis freezes business hiring
    cfg = data.economy_config["business"]
    reserve_months = cfg["wage_reserve_months"]
    for b in business_mod.active_businesses(store):
        spec = STAFFING.get(b["category"])
        if spec is None:
            continue
        profession_id, target = spec
        current = len(business_mod.employees_of(store,
                                               b["business_id"]))
        if current >= target:
            continue
        wage = data.wage(profession_id, "entry")
        from . import justice as justice_mod
        wage = justice_mod.apply_wage_floor(store, data, wage)
        bill = business_mod.wage_bill(store, b["business_id"])
        if store.business_balance(b["business_id"]) \
                < (bill + wage) * reserve_months:
            continue  # cannot pay -> cannot hire (recorded by absence)
        existing = store.row(
            "SELECT COUNT(*) AS n FROM vacancies WHERE"
            " employer_business_id = ? AND status = 'open'",
            (b["business_id"],))["n"]
        if existing:
            continue
        vid = _post_vacancy(
            store, employer_kind="business",
            business_id=b["business_id"], profession_id=profession_id,
            city_id=business_mod.business_city(store, data, b),
            wage=wage, month_index=month_index,
            game_minutes=game_minutes)
        posted.append(vid)
    # Civic posts against the city's population.
    pop = cities_mod.city_population(store, data, CIVIC_CITY)
    for profession_id, per_100 in CIVIC_RATIOS.items():
        target = int(pop * per_100 / 100)
        current = store.row(
            "SELECT COUNT(*) AS n FROM employments WHERE"
            " profession_id = ? AND ended_at_game_minutes IS NULL",
            (profession_id,))["n"]
        if current >= target:
            continue
        existing = store.row(
            "SELECT COUNT(*) AS n FROM vacancies WHERE"
            " employer_kind = 'civic' AND profession_id = ?"
            " AND status = 'open'", (profession_id,))["n"]
        if existing:
            continue
        from . import justice as justice_mod
        vid = _post_vacancy(
            store, employer_kind="civic", business_id=None,
            profession_id=profession_id, city_id=CIVIC_CITY,
            wage=justice_mod.apply_wage_floor(
                store, data, data.wage(profession_id, "entry")),
            month_index=month_index, game_minutes=game_minutes)
        posted.append(vid)
    return posted


def _eligible(store, data, cid, profession_id):
    from . import education as education_mod
    if profession_id in education_mod.GATED_PROGRAMMES:
        if not education_mod.has_credential(store, cid, profession_id):
            return False
    return True


def _score(store, data, rng, cid, vacancy, day_index):
    from . import decisions as decisions_mod
    prof = data.professions[vacancy["profession_id"]]
    score = sum(decisions_mod.skill_level(store, cid, s)
                for s in prof["primary_skills"])
    profile = store.row("SELECT discipline, intelligence FROM"
                        " personality_profiles WHERE character_id = ?",
                        (cid,))
    if profile:
        score += profile["discipline"] * 0.2 \
            + profile["intelligence"] * 0.1
    score += rng.stream("apply", cid, vacancy["vacancy_id"]).uniform(0, 8)
    return round(score, 2)


def match_vacancies(store, data, rng, month_index, game_minutes):
    """Applications + hiring for every open vacancy. Returns the
    hires made: [{vacancy_id, character_id, profession_id}]."""
    from . import identity as identity_mod
    from . import emotions as emotions_mod
    from . import memory as memory_mod
    now = game_minutes
    unemployed = []
    for c in store.rows("SELECT * FROM characters WHERE is_system = 0"
                        " AND died_at_game_minutes IS NULL"
                        " ORDER BY character_id"):
        age = identity_mod.age_years(c["born_at_game_minutes"], now)
        if age < 18 or age >= 65:
            continue
        if store.row("SELECT 1 FROM employments WHERE character_id"
                     " = ? AND ended_at_game_minutes IS NULL",
                     (c["character_id"],)):
            continue
        from . import education as education_mod
        if education_mod.college_enrolment(store, c["character_id"]):
            continue
        unemployed.append(c["character_id"])
    hires = []
    day_index = now // 1440
    for v in store.rows("SELECT * FROM vacancies WHERE status = 'open'"
                        " ORDER BY vacancy_id"):
        if v["employer_kind"] == "government":
            continue  # Session 05: government posts are matched by
            # the civil-service pass (admin.py), which records the
            # institution assignment and pays from the treasury.
        best, best_score = None, -1
        pool_scores = []
        for cid in unemployed:
            if not _eligible(store, data, cid, v["profession_id"]):
                continue
            score = _score(store, data, rng, cid, v, day_index)
            pool_scores.append(score)
            aid = store.next_id("AP", "job_applications",
                                "application_id")
            store.insert("job_applications", application_id=aid,
                         vacancy_id=v["vacancy_id"], character_id=cid,
                         score=score, status="pending",
                         game_minutes=game_minutes)
            if score > best_score:
                best, best_score = cid, score
        if best is None:
            continue
        wage = v["wage_per_month"]
        # Session 09: a business hire is a structured negotiation
        # when the coordination layer is live — the best candidate
        # may ask a premium over the posted wage, the employer may
        # counter, and a walk-away leaves the vacancy open with
        # the candidate still in the pool. Civic pay is a fixed
        # scale and is never negotiated. Worlds without the agent
        # layer keep the exact Session 04 behaviour.
        if v["employer_kind"] == "business":
            from . import agents as agents_mod
            if agents_mod.is_setup(store):
                wage, _nid = agents_mod.negotiate_wage(
                    store, data, v, best, best_score, pool_scores,
                    game_minutes)
                if wage is None:
                    store.execute(
                        "UPDATE job_applications SET status ="
                        " 'walked_away' WHERE vacancy_id = ? AND"
                        " character_id = ?",
                        (v["vacancy_id"], best))
                    continue
        eid = store.next_id("EM", "employments", "employment_id")
        store.insert(
            "employments", employment_id=eid, character_id=best,
            profession_id=v["profession_id"],
            employer_business_id=v["employer_business_id"],
            employer_character_id="SYS-CITY"
            if v["employer_kind"] == "civic" else None,
            tier=1, wage_per_month=wage,
            started_at_game_minutes=game_minutes)
        # Queue 16 Unit DD: the issued uniform (GDD-09 §5) — seeded
        # beside the employment, no ledger charge (issued, not
        # bought). A re-hire in the same profession keeps the set
        # it already holds; the helper skips those items.
        from . import lost_items as lost_items_mod
        lost_items_mod.seed_uniform_rows(
            store, data, best, v["profession_id"], 1, game_minutes)
        # Queue 17 Unit DJ: the trade's instruments, issued by the
        # employer at hiring beside the uniform (no ledger charge).
        lost_items_mod.seed_tool_rows(
            store, data, best, v["profession_id"], game_minutes)
        store.execute(
            "UPDATE vacancies SET status = 'filled',"
            " filled_by_character_id = ?, closed_at_game_minutes = ?"
            " WHERE vacancy_id = ?", (best, game_minutes,
                                      v["vacancy_id"]))
        store.execute(
            "UPDATE job_applications SET status = 'rejected' WHERE"
            " vacancy_id = ? AND character_id != ?",
            (v["vacancy_id"], best))
        store.execute(
            "UPDATE job_applications SET status = 'accepted' WHERE"
            " vacancy_id = ? AND character_id = ?",
            (v["vacancy_id"], best))
        unemployed.remove(best)
        # Session 09: contention resolution, recorded. One person
        # cannot take two jobs: the hired candidate's still-pending
        # applications to other vacancies close as contention_lost,
        # with the orchestrator's rule on record (vacancies are
        # processed in id order; the highest score wins the
        # person). The household analogue — two households claiming
        # one vacant unit — is resolved by households.move_household
        # (first mover wins; the loser gets None, recorded in its
        # decision outcome).
        from . import agents as agents_mod
        if agents_mod.is_setup(store):
            lost = store.rows(
                "SELECT vacancy_id FROM job_applications WHERE"
                " character_id = ? AND status = 'pending'",
                (best,))
            if lost:
                store.execute(
                    "UPDATE job_applications SET status ="
                    " 'contention_lost' WHERE character_id = ? AND"
                    " status = 'pending'", (best,))
                agents_mod.log_agent_decision(
                    store, best, "citizen", "conflict_resolution",
                    {"won_vacancy": v["vacancy_id"],
                     "lost_vacancies": [r["vacancy_id"]
                                        for r in lost]},
                    "one agent, one job: vacancies in id order,"
                    " highest score wins the candidate; losing"
                    " applications close with the reason recorded",
                    {"hired_vacancy": v["vacancy_id"]},
                    game_minutes)
        memory_mod.log_life_event(
            store, best, "job_gain", game_minutes,
            details={"profession": v["profession_id"],
                     "via": "labour_market",
                     "employer_business_id": v["employer_business_id"]})
        emotions_mod.apply_event(store, best, "job_gain")
        hires.append({"vacancy_id": v["vacancy_id"],
                      "character_id": best,
                      "profession_id": v["profession_id"],
                      "employer_business_id": v["employer_business_id"]})
    return hires


def separations(store, data, month_index, game_minutes):
    """Distress separations: a distressed business sheds its
    newest business hire; its other employees may resign when a
    vacancy elsewhere is open. Returns what happened."""
    out = {"laid_off": [], "resigned": []}
    open_vac = store.row("SELECT COUNT(*) AS n FROM vacancies WHERE"
                         " status = 'open'")["n"]
    for b in business_mod.active_businesses(store):
        if b["status"] != "distressed":
            continue
        emps = business_mod.employees_of(store, b["business_id"])
        if not emps:
            continue
        newest = emps[-1]
        store.execute("UPDATE employments SET ended_at_game_minutes"
                      " = ? WHERE employment_id = ?",
                      (game_minutes, newest["employment_id"]))
        out["laid_off"].append(newest["character_id"])
        business_mod.log_event(store, b["business_id"], "layoff",
                               {"character_id": newest["character_id"],
                                "cause": "distress",
                                "month_index": month_index},
                               game_minutes)
        if open_vac:
            for e in emps[:-1]:
                store.execute(
                    "UPDATE employments SET ended_at_game_minutes"
                    " = ? WHERE employment_id = ?",
                    (game_minutes, e["employment_id"]))
                out["resigned"].append(e["character_id"])
                business_mod.log_event(
                    store, b["business_id"], "resignation",
                    {"character_id": e["character_id"],
                     "cause": "employer_distress",
                     "month_index": month_index}, game_minutes)
    return out


def monthly_pass(store, data, rng, month_index, game_minutes,
                 hiring_freeze=False):
    posted = post_vacancies(store, data, month_index, game_minutes,
                            hiring_freeze=hiring_freeze)
    hires = match_vacancies(store, data, rng, month_index,
                            game_minutes)
    sep = separations(store, data, month_index, game_minutes)
    return {"posted": len(posted), "hires": hires,
            "laid_off": sep["laid_off"], "resigned": sep["resigned"]}


# -- Queue 20 Unit EL: broken-tool wage consequence (GDD-04 §3.3,
# Unit DQ/EE follow-up) -------------------------------------------------
# DECIDED (recorded in GDD-04 §3.3 and GDD-03 §2): the NO-DOCK rule
# stands — a work block bent by a broken tool does NOT dock the
# day's wages. The reasons, in order:
#
# 1. The tool is employer-issued (Unit DJ: issued by the employer
#    at hiring, no ledger charge — the GDD-09 §5 uniform economics
#    by analogy). The worker does not own the tool, so the
#    downtime cost falls on the employer, not the worker; docking
#    the worker's pay for the employer's broken instrument would
#    charge the wrong party.
# 2. The settlement pays MONTHLY salaries (wage_per_month) for
#    every employment, and it has no absence docking for ANY
#    absence — a rest day, an illness rest bend (the same scheduler
#    bend to home), and a storm day all pay in full. Docking only
#    broken-tool days while identical absences pay full would be
#    one cause singled out without a rule behind it.
# 3. The cost is already real without a dock: a bent block is no
#    work hour, so no skill XP accrues that day, and the employer
#    loses the day's output (the business still pays the full
#    wage for a day it got nothing from — the employer's loss, not
#    the worker's).
#
# The one sourced exception is the construction worker's day wage
# (GDD-03 §2: "paid per worked day; no work, no pay") — but the
# sim does not implement day-wage pay at all: the settlement pays
# construction workers the same monthly wage_per_month as everyone
# else. Implementing a broken-tool dock for day-wage workers only
# would mean building the day-wage pay model first, which is a
# separate unit's job (recorded as an open gap, not built here).
# When day-wage pay lands, the dock question re-opens for that
# profession alone; until then the no-dock rule is uniform.

DAYS_PER_MONTH = 30


def broken_tool_days(store, character_id, month_index):
    """The days in the month whose instantiated schedule bent a
    work block for a broken tool — the count the dock would be
    computed from. Read from the stored `instantiated_schedules`
    rows: a day counts when any of its blocks carries the
    `broken_tool` flag the scheduler sets on a bent work block.
    Months are 1-based (month m covers days (m-1)*30 .. m*30-1,
    the settlement's own mapping). A rest day, a day with no work
    blocks, or a character with no stored day counts 0 — only
    work actually refused counts. 0 for an unknown character."""
    start_day = (month_index - 1) * DAYS_PER_MONTH
    count = 0
    for row in store.rows(
            "SELECT blocks_json FROM instantiated_schedules"
            " WHERE character_id = ? AND day_index >= ?"
            " AND day_index < ?",
            (character_id, start_day, start_day + DAYS_PER_MONTH)):
        try:
            blocks = json.loads(row["blocks_json"])
        except ValueError:
            continue
        if any(b.get("broken_tool") for b in blocks):
            count += 1
    return count


def broken_tool_wage_dock(store, character_id, month_index,
                          wage_per_month):
    """The wage dock for the month's broken-tool days, in NCr: 0,
    always, under the no-dock rule above. The settlement calls this
    for every wage it pays, so the rule is consulted at the point
    of payment, not assumed — a future tuning call changes this
    single return (a day's wages would be wage_per_month / 30 per
    bent day) without touching the settlement. The arguments are
    the inputs the dock would be computed from; today they are
    read and the answer is 0."""
    return 0


# -- Queue 21 Unit ES: construction-worker day-wage pay (GDD-03
# §2, EL follow-up) ------------------------------------------------------
# DECIDED (recorded in GDD-03 §2 and GDD-04 §3.3): construction
# workers are paid per worked day — "paid per worked day; no work,
# no pay" (GDD-03 §2) — not the monthly wage_per_month every other
# profession receives. The day wage is wage_per_month / 30 (the
# settlement's DAYS_PER_MONTH; the EL docstring's own figure for
# "a day's wages"), and a month of 30 worked days pays exactly the
# band. A day counts as worked when its stored schedule has at
# least one work block NOT bent by a broken tool — the scheduler
# keeps the construction morning shift on Fridays, so a normal
# month is a full month. The EL dock question re-opens here and is
# resolved by the pay model, not by an exception: rest days,
# storm-bent days, and broken-tool days all pay 0 — the cause of
# non-work does not matter, because day-wage pay docks every
# non-worked day uniformly. The EL no-dock rule stands unchanged
# for every monthly-paid profession: a bent block never docks a
# monthly wage, and only the construction worker's pay model
# differs. The treasury path pays no construction workers (civic
# posts are teacher/doctor/police only; institutions hire civil
# servants), so only the business and SYS-EMPLOYERS payment
# points consult this.
DAY_WAGE_PROFESSIONS = ("construction_worker",)


def worked_days(store, character_id, month_index):
    """Days in the month with at least one unbent work block, read
    from the stored instantiated_schedules rows (the same source
    broken_tool_days reads; months are 1-based, month m covers
    days (m-1)*30..m*30-1). A day whose work blocks were all bent
    by a broken tool, a rest day, and a storm-bent day all count
    zero — none of them is a worked day."""
    start_day = (month_index - 1) * DAYS_PER_MONTH
    end_day = start_day + DAYS_PER_MONTH
    count = 0
    for row in store.rows(
            "SELECT blocks_json FROM instantiated_schedules WHERE"
            " character_id = ? AND day_index >= ? AND day_index < ?",
            (character_id, start_day, end_day)):
        blocks = json.loads(row["blocks_json"])
        if any(b.get("activity") == "work"
               and not b.get("broken_tool") for b in blocks):
            count += 1
    return count


def day_wage_due(store, character_id, month_index, wage_per_month):
    """Day-wage pay for the month, in NCr: worked_days ×
    (wage_per_month / 30), rounded to the nearest NCr. A month of
    30 worked days pays exactly the band."""
    return round(worked_days(store, character_id, month_index)
                 * wage_per_month / DAYS_PER_MONTH)


def wage_due_for(store, character_id, profession_id, month_index,
                 wage_per_month):
    """The month's gross wage for one employment: day-wage
    professions are paid per worked day; every other profession
    is paid the monthly wage less the broken-tool dock (0 under
    the no-dock rule). Both settlement payment points call this —
    the business path and the SYS-EMPLOYERS branch — so the rule
    is consulted once, at the point of payment."""
    if profession_id in DAY_WAGE_PROFESSIONS:
        return day_wage_due(store, character_id, month_index,
                            wage_per_month)
    return wage_per_month - broken_tool_wage_dock(
        store, character_id, month_index, wage_per_month)


def unemployment_stats(store, data):
    """Measured labour market state over living residents."""
    from . import identity as identity_mod
    from . import education as education_mod
    now = store.world()["game_minutes"]
    labour_force = employed = 0
    by_city = {}
    for c in store.rows("SELECT * FROM characters WHERE is_system = 0"
                        " AND died_at_game_minutes IS NULL"):
        age = identity_mod.age_years(c["born_at_game_minutes"], now)
        if age < 18 or age >= 65:
            continue
        if education_mod.college_enrolment(store, c["character_id"]):
            continue
        labour_force += 1
        emp = store.row("SELECT 1 FROM employments WHERE character_id"
                        " = ? AND ended_at_game_minutes IS NULL",
                        (c["character_id"],))
        if emp:
            employed += 1
        city = None
        if c["household_id"]:
            h = store.row("SELECT district_id FROM households WHERE"
                          " household_id = ?", (c["household_id"],))
            if h:
                city = cities_mod.city_of_zone(data, h["district_id"])
        if city:
            d = by_city.setdefault(city, {"labour_force": 0,
                                          "employed": 0})
            d["labour_force"] += 1
            if emp:
                d["employed"] += 1
    unemployed = labour_force - employed
    for d in by_city.values():
        d["unemployed"] = d["labour_force"] - d["employed"]
        d["unemployment_rate"] = round(
            d["unemployed"] / d["labour_force"], 4) \
            if d["labour_force"] else 0.0
    return {"labour_force": labour_force, "employed": employed,
            "unemployed": unemployed,
            "unemployment_rate": round(unemployed / labour_force, 4)
            if labour_force else 0.0,
            "by_city": by_city}
