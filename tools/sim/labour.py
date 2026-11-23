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
