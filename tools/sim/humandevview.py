"""Session 06 — Observatory: education / health / development
views over the real records (the --government pattern). Data
layer only; every number below is read from the simulation's own
tables at call time."""
import json

from . import humandev as humandev_mod


def education_view(store, data):
    institutions = []
    for inst in store.rows("SELECT * FROM educational_institutions"
                           " ORDER BY institution_id"):
        iid = inst["institution_id"]
        students = store.row("SELECT COUNT(*) AS n FROM"
                             " education_records WHERE institution_id"
                             " = ? AND status = 'enrolled'",
                             (iid,))["n"]
        teachers = store.row("SELECT COUNT(*) AS n FROM"
                             " teacher_assignments WHERE"
                             " institution_id = ? AND month_index ="
                             " (SELECT MAX(month_index) FROM"
                             " teacher_assignments)", (iid,))["n"]
        inst = dict(inst)
        inst["students_enrolled"] = students
        inst["teachers_assigned_latest_month"] = teachers
        inst["departments"] = [r["department"] for r in store.rows(
            "SELECT department FROM institution_departments WHERE"
            " institution_id = ? ORDER BY department", (iid,))]
        institutions.append(inst)
    exams = store.rows("SELECT exam_id, institution_id, month_index,"
                       " candidates, mean_score FROM examinations"
                       " ORDER BY month_index DESC LIMIT 12")
    certs = store.row("SELECT COUNT(*) AS n FROM certifications")["n"]
    dropouts = store.row("SELECT COUNT(*) AS n FROM education_records"
                         " WHERE status = 'dropped_out'")["n"]
    return {"institutions": institutions,
            "recent_examinations": exams,
            "certifications_issued": certs,
            "dropouts": dropouts}


def health_view(store, data):
    from . import healthcare as healthcare_mod
    facilities = []
    for fac in store.rows("SELECT * FROM healthcare_facilities"
                          " ORDER BY facility_id"):
        fac = dict(fac)
        fac["doctors"] = len(healthcare_mod.doctors_for_facility(
            store, data, fac))
        fac["daily_capacity"] = healthcare_mod.daily_capacity(
            store, data, fac)
        fac["inventory"] = {r["item_id"]: r["quantity"] for r in
                            store.rows("SELECT item_id, quantity FROM"
                                       " medical_inventory WHERE"
                                       " facility_id = ?",
                                       (fac["facility_id"],))}
        fac["budget_latest"] = store.row(
            "SELECT * FROM healthcare_budgets WHERE facility_id = ?"
            " ORDER BY month_index DESC LIMIT 1", (fac["facility_id"],))
        facilities.append(fac)
    conditions = store.rows("SELECT band, status, COUNT(*) AS n FROM"
                            " health_conditions GROUP BY band, status"
                            " ORDER BY band, status")
    visits = store.rows("SELECT stage, COUNT(*) AS n FROM"
                        " patient_visits GROUP BY stage ORDER BY stage")
    diseases = store.rows("SELECT disease_id, status, COUNT(*) AS n"
                          " FROM disease_records GROUP BY disease_id,"
                          " status ORDER BY disease_id, status")
    vaccinations = store.row("SELECT COUNT(*) AS n FROM"
                             " vaccination_records")["n"]
    return {"facilities": facilities, "conditions_by_band": conditions,
            "visits_by_stage": visits, "disease_records": diseases,
            "vaccinations": vaccinations}


def development_view(store, data):
    latest = store.row("SELECT * FROM human_development_indicators"
                       " WHERE scope = 'national' ORDER BY month_index"
                       " DESC LIMIT 1")
    out = {"methodology": humandev_mod.METHODOLOGY,
           "latest": None, "history": []}
    if latest:
        out["latest"] = {"month_index": latest["month_index"],
                         "indicators": json.loads(
                             latest["indicators"])}
    for row in store.rows("SELECT month_index, indicators FROM"
                          " human_development_indicators WHERE"
                          " scope = 'national' ORDER BY month_index"):
        out["history"].append({"month_index": row["month_index"],
                               "indicators": json.loads(
                                   row["indicators"])})
    research = store.rows("SELECT * FROM research_projects"
                          " ORDER BY project_id")
    out["research_projects"] = research
    out["research_records"] = store.row(
        "SELECT COUNT(*) AS n FROM research_records")["n"]
    return out
