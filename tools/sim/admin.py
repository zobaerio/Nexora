"""Session 05 Unit 08 — Public Administration.

Civil servants are real citizens, recruited through the same
vacancy/application machinery as Session 04's labour market
(the labour pass deliberately skips government posts; this pass
matches them), employed by an institution, and paid by that
institution's treasury account through the ledger (engine's
government wage pre-pass). The remit is deliberately distinct
from Session 04's civic payroll (teachers/doctors/police for
Rupsha, which stays as it is): the civil service staffs what
Session 05 creates — Shibnagar's police and clinic, the housing
ministry's engineers, and the two municipal administrations.

Evaluations are computed from measured institutional output
(incidents processed, service levels, coverage against target),
blended with the servant's own discipline — never asserted.
Promotion follows the canonical profession tiers and wage bands;
transfers rebalance a surplus institution toward an understaffed
one, at most one per month, always recorded.
"""
import json

from . import cities as cities_mod
from . import government as gov
from . import labour as labour_mod

# SIM MODEL staffing plan: (institution, profession, basis).
# basis ("per_100", city, rate) scales with the city's residents;
# ("fixed", n) is a flat establishment. Rates echo Session 04's
# civic ratios where a counterpart exists (police 1.0, doctor 0.8
# per 100) — labelled model values, as there.
STAFFING = (
    ("GOV-POLICE-SHIBNAGAR", "police_officer",
     ("per_100", cities_mod.SHIBNAGAR, 1.0)),
    ("GOV-HEALTH", "doctor",
     ("per_100", cities_mod.SHIBNAGAR, 0.8)),
    ("GOV-HOUSING", "civil_engineer", ("fixed", 2)),
    ("GOV-CITY-RUPSHA", "civil_engineer", ("fixed", 1)),
    ("GOV-CITY-SHIBNAGAR", "civil_engineer", ("fixed", 1)),
)


def _target(store, data, basis):
    if basis[0] == "fixed":
        return basis[1]
    _kind, city_id, rate = basis
    pop = cities_mod.city_population(store, data, city_id)
    return int(pop * rate / 100)


def staff_of(store, institution_id):
    return store.rows(
        "SELECT * FROM civil_service WHERE institution_id = ?"
        " AND status = 'active' ORDER BY character_id",
        (institution_id,))


def post_vacancies(store, data, month_index, game_minutes):
    """Post this month's civil-service vacancies for understaffed
    institutions. Returns the vacancy ids."""
    posted = []
    for institution_id, profession_id, basis in STAFFING:
        target = _target(store, data, basis)
        if len(staff_of(store, institution_id)) >= target:
            continue
        if store.row("SELECT 1 FROM vacancies WHERE"
                     " employer_institution_id = ? AND status ="
                     " 'open'", (institution_id,)):
            continue
        inst = store.row("SELECT * FROM institutions WHERE"
                         " institution_id = ?", (institution_id,))
        vid = store.next_id("VC", "vacancies", "vacancy_id")
        store.insert(
            "vacancies", vacancy_id=vid, employer_kind="government",
            employer_business_id=None, profession_id=profession_id,
            city_id=inst["city_id"], wage_per_month=data.wage(
                profession_id, "entry"), status="open",
            posted_month=month_index,
            created_at_game_minutes=game_minutes,
            employer_account_id=inst["account_id"],
            employer_institution_id=institution_id)
        posted.append(vid)
    return posted


def _unemployed_pool(store, game_minutes):
    from . import education as education_mod
    from . import identity as identity_mod
    pool = []
    for c in store.rows("SELECT * FROM characters WHERE is_system"
                        " = 0 AND died_at_game_minutes IS NULL"
                        " ORDER BY character_id"):
        age = identity_mod.age_years(c["born_at_game_minutes"],
                                     game_minutes)
        if age < 18 or age >= 65:
            continue
        if store.row("SELECT 1 FROM employments WHERE character_id"
                     " = ? AND ended_at_game_minutes IS NULL",
                     (c["character_id"],)):
            continue
        if education_mod.college_enrolment(store, c["character_id"]):
            continue
        pool.append(c["character_id"])
    return pool


def match_vacancies(store, data, rng, month_index, game_minutes):
    """Applications + hiring for government vacancies — the
    labour market's own scoring and credential gates, reused.
    A hire creates the employment (treasury-paid) and the
    civil-service assignment record together."""
    from . import emotions as emotions_mod
    from . import memory as memory_mod
    pool = _unemployed_pool(store, game_minutes)
    hires = []
    day_index = game_minutes // 1440
    for v in store.rows("SELECT * FROM vacancies WHERE status ="
                        " 'open' AND employer_kind = 'government'"
                        " ORDER BY vacancy_id"):
        best, best_score = None, -1
        for cid in pool:
            if not labour_mod._eligible(store, data, cid,
                                        v["profession_id"]):
                continue
            score = labour_mod._score(store, data, rng, cid, v,
                                      day_index)
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
        eid = store.next_id("EM", "employments", "employment_id")
        store.insert(
            "employments", employment_id=eid, character_id=best,
            profession_id=v["profession_id"],
            employer_business_id=None,
            employer_character_id=v["employer_account_id"],
            tier=1, wage_per_month=v["wage_per_month"],
            started_at_game_minutes=game_minutes)
        # Queue 16 Unit DD: the issued uniform (GDD-09 §5) — the
        # civil-service hire path, same rule as labour's (a police
        # uniform is issued here; a re-hire keeps the set it holds).
        from . import lost_items as lost_items_mod
        lost_items_mod.seed_uniform_rows(
            store, data, best, v["profession_id"], 1, game_minutes)
        rid = store.next_id("CS", "civil_service", "record_id")
        store.insert(
            "civil_service", record_id=rid, character_id=best,
            institution_id=v["employer_institution_id"],
            vacancy_id=v["vacancy_id"],
            role=v["profession_id"], status="active",
            started_at_game_minutes=game_minutes)
        store.execute(
            "UPDATE vacancies SET status = 'filled',"
            " filled_by_character_id = ?, closed_at_game_minutes"
            " = ? WHERE vacancy_id = ?",
            (best, game_minutes, v["vacancy_id"]))
        store.execute(
            "UPDATE job_applications SET status = 'rejected' WHERE"
            " vacancy_id = ? AND character_id != ?",
            (v["vacancy_id"], best))
        store.execute(
            "UPDATE job_applications SET status = 'accepted' WHERE"
            " vacancy_id = ? AND character_id = ?",
            (v["vacancy_id"], best))
        pool.remove(best)
        memory_mod.log_life_event(
            store, best, "job_gain", game_minutes,
            details={"profession": v["profession_id"],
                     "via": "civil_service",
                     "institution_id":
                     v["employer_institution_id"]})
        emotions_mod.apply_event(store, best, "job_gain")
        hires.append({"vacancy_id": v["vacancy_id"],
                      "character_id": best,
                      "institution_id":
                      v["employer_institution_id"]})
    return hires


def institution_output(store, data, institution_id, game_minutes):
    """Measured institutional output 0..100, from records only:
    police — share of the month's incidents processed; health —
    doctor coverage of the town against the civic ratio; housing
    — construction momentum; municipal — the city's average
    service level."""
    since = game_minutes - 30 * 1440
    inst = store.row("SELECT * FROM institutions WHERE"
                     " institution_id = ?", (institution_id,))
    if inst is None:
        return 50.0
    if "POLICE" in institution_id:
        total = store.row(
            "SELECT COUNT(*) AS n FROM incidents WHERE city_id = ?"
            " AND created_at_game_minutes > ?",
            (inst["city_id"], since))["n"]
        done = store.row(
            "SELECT COUNT(*) AS n FROM incidents WHERE city_id = ?"
            " AND created_at_game_minutes > ? AND status IN"
            " ('referred', 'closed')",
            (inst["city_id"], since))["n"]
        return round(60 + 40 * (done / total), 1) if total else 70.0
    if institution_id == "GOV-HEALTH":
        target = max(1, _target(store, data,
                                ("per_100", cities_mod.SHIBNAGAR,
                                 0.8)))
        have = len(staff_of(store, institution_id))
        return round(min(100.0, 40 + 60 * have / target), 1)
    if institution_id == "GOV-HOUSING":
        active = store.row(
            "SELECT COUNT(*) AS n FROM construction_projects WHERE"
            " status = 'active'")["n"]
        done = store.row(
            "SELECT COUNT(*) AS n FROM construction_projects WHERE"
            " status IN ('completed', 'occupied')")["n"]
        return round(min(100.0, 50 + 10 * active + 10 * done), 1)
    if inst["level"] == "municipal":
        lvl = store.row(
            "SELECT AVG(level) AS l FROM municipal_services WHERE"
            " city_id = ?", (inst["city_id"],))
        return round(lvl["l"], 1) if lvl and lvl["l"] is not None \
            else 50.0
    return 60.0


def evaluate_staff(store, data, game_minutes):
    """Monthly evaluations: institutional output blended with
    the servant's discipline; promotion at sustained excellence
    (3+ evaluations, score >= 75) into the next canonical tier."""
    from . import memory as memory_mod
    out = {"evaluated": 0, "promoted": []}
    for rec in store.rows("SELECT * FROM civil_service WHERE"
                          " status = 'active' ORDER BY record_id"):
        output = institution_output(store, data,
                                    rec["institution_id"],
                                    game_minutes)
        prof = gov._profile(store, rec["character_id"])
        score = round(0.7 * output
                      + 0.3 * prof.get("discipline", 50), 1)
        store.execute(
            "UPDATE civil_service SET evaluation_score = ?,"
            " evaluations = evaluations + 1 WHERE record_id = ?",
            (score, rec["record_id"]))
        out["evaluated"] += 1
        if score >= 75 and rec["evaluations"] + 1 >= 3:
            emp = store.row(
                "SELECT * FROM employments WHERE character_id = ?"
                " AND ended_at_game_minutes IS NULL",
                (rec["character_id"],))
            if emp and emp["tier"] < 3:
                new_tier = emp["tier"] + 1
                store.execute(
                    "UPDATE employments SET tier = ?,"
                    " wage_per_month = ? WHERE employment_id = ?",
                    (new_tier, data.wage_at(emp["profession_id"],
                                            new_tier),
                     emp["employment_id"]))
                memory_mod.log_life_event(
                    store, rec["character_id"], "promotion",
                    game_minutes,
                    details={"tier": new_tier,
                             "via": "civil_service"})
                out["promoted"].append(rec["character_id"])
    return out


def rebalance_transfers(store, data, game_minutes):
    """At most one transfer per month: the lowest-scored servant
    of a surplus institution moves to an understaffed institution
    hiring the same profession. Fully recorded."""
    by_prof = {}
    for institution_id, profession_id, basis in STAFFING:
        target = _target(store, data, basis)
        staff = staff_of(store, institution_id)
        by_prof.setdefault(profession_id, []).append(
            (institution_id, target, staff))
    for profession_id, entries in by_prof.items():
        surplus = [(i, s) for i, t, s in entries if len(s) > t]
        deficit = [(i, t, s) for i, t, s in entries
                   if len(s) < t]
        if not surplus or not deficit:
            continue
        src_inst, src_staff = surplus[0]
        dst_inst = deficit[0][0]
        mover = sorted(
            src_staff,
            key=lambda r: (r["evaluation_score"] or 0,
                           r["character_id"]))[0]
        dst = store.row("SELECT * FROM institutions WHERE"
                        " institution_id = ?", (dst_inst,))
        store.execute("UPDATE civil_service SET status ="
                      " 'transferred', ended_at_game_minutes = ?"
                      " WHERE record_id = ?",
                      (game_minutes, mover["record_id"]))
        rid = store.next_id("CS", "civil_service", "record_id")
        store.insert(
            "civil_service", record_id=rid,
            character_id=mover["character_id"],
            institution_id=dst_inst, vacancy_id=None,
            role=profession_id, status="active",
            started_at_game_minutes=game_minutes)
        store.execute(
            "UPDATE employments SET employer_character_id = ?"
            " WHERE character_id = ? AND ended_at_game_minutes"
            " IS NULL",
            (dst["account_id"], mover["character_id"]))
        gov.log_event(store, "civil_service_transfer",
                      mover["character_id"],
                      {"from_institution": src_inst,
                       "to_institution": dst_inst,
                       "profession": profession_id}, game_minutes)
        return {"character_id": mover["character_id"],
                "from": src_inst, "to": dst_inst}
    return None


def monthly_pass(store, data, rng, month_index, game_minutes):
    if not gov.is_setup(store):
        return None
    posted = post_vacancies(store, data, month_index, game_minutes)
    hires = match_vacancies(store, data, rng, month_index,
                            game_minutes)
    evaluated = evaluate_staff(store, data, game_minutes)
    transfer = rebalance_transfers(store, data, game_minutes)
    return {"posted": len(posted), "hires": hires,
            "evaluated": evaluated, "transfer": transfer}
