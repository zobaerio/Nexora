"""Session 06 — Educational Institutions & Teachers.

What Session 02 built (education.py) is the *student* side:
enrolment records, measured attendance, GDD-11 skill caps and the
credential gates. This module is the *institution* side the
Session 06 spec adds, and it creates nothing that already exists:

- A registry of the educational institutions that ACTUALLY exist,
  seeded from data/education-health-config.json whose entries are
  grounded in the merged building data (District School, District
  College, College Library in Rupsha; Shibnagar Primary School in
  Shibnagar). Institution types with no building (kindergarten,
  university, technical institute...) exist in the config's type
  framework only — no institution row is ever created for a
  building the world does not have.
- Departments per institution (config data).
- An operating-budget authority per institution per month (civic
  funding, GDD-11 §7: education is free at point of use; the real
  money that moves for education is the teachers' wages, paid by
  the existing payroll — this module moves no money itself).
- Teacher assignments: teachers are real citizens employed as the
  teacher profession (genesis, Session 04 civic labour market,
  Session 05 civil service). Each month they are assigned to an
  institution by residence city (config rule: in Rupsha the
  college takes lecturer posts first, 1 per 10 enrolled college
  students; the rest teach at the school), given a subject, and
  evaluated from the institution's MEASURED student outcomes —
  the latest examination mean and the students' measured
  attendance. No evaluation is ever asserted without those rows.
- Institution performance: the latest examination mean at the
  institution, blended with its research capability for the
  college (research.py) — again, only from records.
"""
import json

from . import cities as cities_mod
from . import government as gov_mod


def cfg(data):
    return data.education_health_config["education"]


def seed_institutions(store, data, game_minutes):
    """Create the institution + department rows for the buildings
    that exist. Idempotent; returns the institution ids."""
    ecfg = cfg(data)
    buildings = data.all_buildings()
    ids = []
    for spec in ecfg["institutions"]:
        if spec["building_id"] not in buildings:
            continue  # never register an institution with no building
        iid = spec["institution_id"]
        if store.row("SELECT 1 FROM educational_institutions"
                     " WHERE institution_id = ?", (iid,)) is None:
            tcfg = ecfg["institution_types"][spec["type"]]
            store.insert(
                "educational_institutions",
                institution_id=iid, building_id=spec["building_id"],
                city_id=spec["city_id"],
                institution_type=spec["type"], name=spec["name"],
                level=spec["level"],
                capacity_students=tcfg["capacity_students"],
                monthly_budget_ncr=tcfg["monthly_budget_ncr"],
                created_at_game_minutes=game_minutes)
            for dept in ecfg["departments"].get(spec["type"], []):
                store.insert("institution_departments",
                             institution_id=iid, department=dept)
        ids.append(iid)
    return ids


def institution_of_building(store, building_id):
    return store.row("SELECT * FROM educational_institutions"
                     " WHERE building_id = ?", (building_id,))


def institution_by_id(store, institution_id):
    return store.row("SELECT * FROM educational_institutions"
                     " WHERE institution_id = ?", (institution_id,))


def enrolled_count(store, institution_id):
    # education_records carry the BUILDING id (Session 02); the
    # registry id resolves through educational_institutions.
    inst = institution_by_id(store, institution_id)
    key = inst["building_id"] if inst else institution_id
    row = store.row("SELECT COUNT(*) AS n FROM education_records"
                    " WHERE institution_id = ?"
                    " AND status = 'enrolled'", (key,))
    return row["n"] if row else 0


def _teachers_by_city(store, data):
    """Living citizens currently employed as teachers, grouped by
    residence city (the assignment rule's input)."""
    out = {}
    rows = store.rows(
        "SELECT c.character_id FROM characters c"
        " JOIN employments e ON e.character_id = c.character_id"
        " WHERE e.profession_id = 'teacher'"
        " AND e.ended_at_game_minutes IS NULL"
        " AND c.died_at_game_minutes IS NULL AND c.is_system = 0"
        " ORDER BY c.character_id")
    for r in rows:
        city = gov_mod.city_of_character(store, data, r["character_id"])
        out.setdefault(city or cities_mod.RUPSHA, []).append(
            r["character_id"])
    return out


def _institution_outcomes(store, institution_id):
    """(latest examination mean, mean measured attendance of the
    institution's enrolled students) — either may be None when the
    records do not exist yet."""
    exam = store.row("SELECT mean_score FROM examinations WHERE"
                     " institution_id = ? ORDER BY month_index DESC"
                     " LIMIT 1", (institution_id,))
    inst = institution_by_id(store, institution_id)
    key = inst["building_id"] if inst else institution_id
    att = store.row("SELECT AVG(attendance_rate) AS a FROM"
                    " education_records WHERE institution_id = ?"
                    " AND status = 'enrolled'", (key,))
    return (exam["mean_score"] if exam else None,
            att["a"] if att and att["a"] is not None else None)


def _evaluation(store, data, institution_id, character_id):
    """A teacher's evaluation from measured facts: the
    institution's latest examination mean (60%) and its students'
    measured attendance (40%). Before any examination exists, the
    teacher's own teaching skill level (a measured character_skills
    fact) is the fallback — documented, never a constant."""
    from . import decisions as decisions_mod
    exam_mean, att_mean = _institution_outcomes(store, institution_id)
    if exam_mean is not None:
        att_part = (att_mean or 0.0) * 100
        return round(0.6 * exam_mean + 0.4 * att_part, 2)
    return float(decisions_mod.skill_level(store, character_id,
                                           "teaching"))


def assign_teachers(store, data, month_index, game_minutes):
    """Write this month's teacher_assignments. Returns the number
    of assignments written."""
    ecfg = cfg(data)
    by_city = _teachers_by_city(store, data)
    count = 0
    for inst in store.rows("SELECT * FROM educational_institutions"
                           " WHERE active = 1"
                           " ORDER BY institution_id"):
        iid = inst["institution_id"]
        if inst["level"] == "support":
            continue  # the library has no teaching staff of its own
        pool = list(by_city.get(inst["city_id"], []))
        if inst["level"] == "college":
            enrolled = enrolled_count(store, iid)
            posts = 0
            if enrolled > 0:
                posts = max(1, int(enrolled
                                   * ecfg["teachers"]
                                   ["lecturers_per_college_students"]))
            chosen = pool[:posts]
            by_city[inst["city_id"]] = pool[posts:]
            subject = "programme"
        else:
            chosen = pool
            by_city[inst["city_id"]] = []
            subject = "general_studies"
        for cid in chosen:
            if store.row("SELECT 1 FROM teacher_assignments WHERE"
                         " character_id = ? AND month_index = ?",
                         (cid, month_index)):
                continue  # month replay: assignment already written
            aid = store.next_id("TA", "teacher_assignments",
                                "assignment_id")
            store.insert(
                "teacher_assignments", assignment_id=aid,
                character_id=cid, institution_id=iid,
                month_index=month_index, subject=subject,
                evaluation_score=_evaluation(store, data, iid, cid),
                created_at_game_minutes=game_minutes)
            count += 1
    return count


def teacher_score_for(store, institution_id, month_index):
    """The institution's teaching quality for examinations: the
    mean evaluation of this month's assigned teachers; falls back
    to their mean teaching skill when no assignment exists yet.
    Returns 0.0 when the institution has no teachers at all — an
    honest zero that examinations then reflect."""
    rows = store.rows("SELECT evaluation_score FROM teacher_assignments"
                      " WHERE institution_id = ? AND month_index = ?",
                      (institution_id, month_index))
    if rows:
        vals = [r["evaluation_score"] for r in rows
                if r["evaluation_score"] is not None]
        if vals:
            return round(sum(vals) / len(vals), 2)
    from . import decisions as decisions_mod
    rows = store.rows(
        "SELECT c.character_id FROM characters c"
        " JOIN employments e ON e.character_id = c.character_id"
        " WHERE e.profession_id = 'teacher'"
        " AND e.ended_at_game_minutes IS NULL"
        " AND c.died_at_game_minutes IS NULL")
    if not rows:
        return 0.0
    levels = [decisions_mod.skill_level(store, r["character_id"],
                                        "teaching") for r in rows]
    return round(sum(levels) / len(levels), 2) if levels else 0.0


def refresh_performance(store, data, game_minutes):
    """Institution performance from records: the latest
    examination mean, blended 80/20 with research capability for
    institutions that have any."""
    for inst in store.rows("SELECT * FROM educational_institutions"
                           " WHERE active = 1"):
        iid = inst["institution_id"]
        exam_mean, _ = _institution_outcomes(store, iid)
        perf = exam_mean
        if perf is not None and inst["research_capability"]:
            perf = round(0.8 * perf
                         + 0.2 * min(100.0,
                                     inst["research_capability"]), 2)
        store.execute(
            "UPDATE educational_institutions SET performance_score = ?"
            " WHERE institution_id = ?", (perf, iid))
    return True


def monthly_pass(store, data, month_index, game_minutes):
    """Institutions' monthly cadence, first in the Session 06
    sequence: the month's budget authority is refreshed from
    config and the spend counter reset (research.py draws against
    it later in the cadence), teachers are assigned (academics
    reads the assignments), and performance is refreshed from the
    records that exist at month start."""
    ecfg = cfg(data)
    for inst in store.rows("SELECT * FROM educational_institutions"
                           " WHERE active = 1"):
        tcfg = ecfg["institution_types"][inst["institution_type"]]
        store.execute(
            "UPDATE educational_institutions SET monthly_budget_ncr = ?,"
            " budget_spent_month_ncr = 0 WHERE institution_id = ?",
            (tcfg["monthly_budget_ncr"], inst["institution_id"]))
    assigned = assign_teachers(store, data, month_index, game_minutes)
    refresh_performance(store, data, game_minutes)
    return {"teachers_assigned": assigned}
