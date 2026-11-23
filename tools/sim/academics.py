"""Session 06 — Student Journeys: Learning, Examinations,
Certifications, Dropout.

Built ON education.py's enrolment records (Session 02), never
beside them: an enrolled record is the student; this module gives
that student a journey.

- Learning records: per student per subject (curricula are config
  data — data/education-health-config.json), a proficiency 0–100
  that grows monthly from the record's MEASURED attendance rate
  and the institution's measured teaching quality. Proficiency is
  a study record, not a skill: character_skills writes remain
  education.py's alone, under the GDD-11 caps.
- Assignments: a monthly record per subject — how many were set
  (the calendar's configured count) and how many the student
  completed, derived from measured attendance and proficiency.
- Examinations: batch-processed in the calendar's exam months.
  Every result is a pure function of stored, measured inputs —
  attendance rate, subject proficiency, the institution's teacher
  score for the month, the institution building's measured
  condition — plus a seeded jitter keyed by (exam, student,
  subject). The inputs are stored ON the result row, so any grade
  can be audited back to its facts, and recomputing from the same
  inputs reproduces the same score exactly (no arbitrary grades).
- Certifications: when an education record completes, a
  certificate is issued if the student's measured examination
  history supports it (school-leaving: latest exam mean at or
  above the pass mark; college: the credential completion itself).
  A record can complete WITHOUT a certificate — the two facts are
  kept distinct on purpose.
- Dropout: only on measured circumstances (config rules): a
  school student aged 14+ whose household shows persistent
  arrears (unpaid emergencies in its last two monthly finance
  records, with debt outstanding) and whose measured performance
  is below the pass mark; a college student whose measured
  attendance stays below the configured floor across two windows.
  Every dropout is a status change with its cause recorded, plus
  a life event — never a random roll against a student.
"""
import json

from . import education as edu_mod
from . import institutions as inst_mod
from . import memory as memory_mod


def _cfg(data):
    return data.education_health_config["education"]


def registry_ids(store):
    """{building_id: institution_id} — Session 02 records carry
    the building id in education_records.institution_id; Session
    06 tables key on the registry id, resolved through this map."""
    return {r["building_id"]: r["institution_id"] for r in
            store.rows("SELECT building_id, institution_id FROM"
                       " educational_institutions")}


def subjects_for(data, record):
    """The curriculum subjects for an enrolment record: the school
    curriculum, or the college programme's subjects."""
    cur = _cfg(data)["curricula"]
    if record["programme"] == edu_mod.SCHOOL_PROGRAMME:
        return cur["school"]["subjects"]
    return cur["programmes"].get(record["programme"], [])


def grade_for(score, bands):
    for b in bands:
        if score >= b["min_score"]:
            return b["grade"]
    return bands[-1]["grade"]


def exam_score(attendance_rate, proficiency, teacher_score,
               institution_score, jitter, weights):
    """The examination formula — a pure function of its measured
    inputs (config weights), clamped to 0..100. Kept separate so
    tests can pin the arithmetic itself."""
    raw = (attendance_rate * 100 * weights["attendance"]
           + proficiency * weights["proficiency"]
           + teacher_score * weights["teacher"]
           + institution_score * weights["institution"])
    return round(max(0.0, min(100.0, raw + jitter)), 2)


def _attendance_window(store, character_id, location, game_minutes,
                       day_from, day_to):
    """Attendance over an explicit past day window, read from the
    persisted schedules exactly as education._attendance does for
    the recent window (measured, never assumed)."""
    world = store.world()
    today = world["day_index"] if world else 0
    present, attended = 0, 0
    for day in range(max(0, today - day_to), max(0, today - day_from)):
        row = store.row("SELECT blocks_json FROM instantiated_schedules"
                        " WHERE character_id = ? AND day_index = ?",
                        (character_id, day))
        if row is None:
            continue
        present += 1
        blocks = json.loads(row["blocks_json"])
        if any(b["activity"] == "study" and b["location"] == location
               for b in blocks):
            attended += 1
    return round(attended / present, 3) if present else 0.0


def update_learning(store, data, month_index, game_minutes):
    """Monthly learning + assignments for every enrolled student.
    Returns (students_updated, assignment_rows)."""
    ecfg = _cfg(data)
    learn = ecfg["learning"]
    cal = ecfg["calendar"]
    reg = registry_ids(store)
    students, rows = 0, 0
    for rec in store.rows("SELECT * FROM education_records"
                          " WHERE status = 'enrolled'"
                          " ORDER BY record_id"):
        cid = rec["character_id"]
        subjects = subjects_for(data, rec)
        if not subjects:
            continue
        iid = reg.get(rec["institution_id"], rec["institution_id"])
        teacher_q = inst_mod.teacher_score_for(
            store, iid, month_index)
        factor = 0.7 + 0.3 * (teacher_q / 100.0)
        gain = (learn["proficiency_gain_per_month"]
                * (rec["attendance_rate"] or 0.0) * factor)
        for subj in subjects:
            sid = subj["id"]
            row = store.row("SELECT * FROM learning_records WHERE"
                            " character_id = ? AND subject_id = ?",
                            (cid, sid))
            if row is None:
                rid = store.next_id("LR", "learning_records",
                                    "record_id")
                store.insert("learning_records", record_id=rid,
                             character_id=cid, institution_id=iid,
                             subject_id=sid, proficiency=0.0,
                             months_studied=0,
                             updated_month=month_index)
                prof = 0.0
            else:
                prof = row["proficiency"]
            prof = round(min(100.0, prof + gain), 2)
            store.execute("UPDATE learning_records SET proficiency = ?,"
                          " months_studied = months_studied + 1,"
                          " updated_month = ? WHERE character_id = ?"
                          " AND subject_id = ?",
                          (prof, month_index, cid, sid))
            due = cal["assignments_per_month"]
            completed = int(round(due * (rec["attendance_rate"] or 0.0)
                                  * (learn["assignment_completion_base"]
                                     + 0.45 * (prof / 100.0))))
            completed = max(0, min(due, completed))
            if store.row("SELECT 1 FROM assignments WHERE"
                         " character_id = ? AND subject_id = ?"
                         " AND month_index = ?",
                         (cid, sid, month_index)):
                continue  # month replay: row already written
            aid = store.next_id("AS", "assignments", "assignment_id")
            store.insert("assignments", assignment_id=aid,
                         character_id=cid, institution_id=iid,
                         subject_id=sid, month_index=month_index,
                         assigned_count=due, completed_count=completed)
            rows += 1
        students += 1
    return students, rows


def run_examinations(store, data, rng, month_index, game_minutes):
    """Batch examinations for every institution with enrolled
    students. Returns {institution_id: exam summary}."""
    ecfg = _cfg(data)
    xcfg = ecfg["examinations"]
    out = {}
    for inst in store.rows("SELECT * FROM educational_institutions"
                           " WHERE active = 1 AND level != 'support'"
                           " ORDER BY institution_id"):
        iid = inst["institution_id"]
        records = store.rows("SELECT * FROM education_records WHERE"
                             " institution_id = ? AND status = 'enrolled'"
                             " ORDER BY record_id",
                             (inst["building_id"],))
        if not records:
            continue
        if store.row("SELECT 1 FROM examinations WHERE institution_id"
                     " = ? AND month_index = ?", (iid, month_index)):
            continue  # month replay: this term's exam already ran
        exam_id = store.next_id("EX", "examinations", "exam_id")
        store.insert("examinations", exam_id=exam_id,
                     institution_id=iid, level=inst["level"],
                     month_index=month_index,
                     game_minutes=game_minutes, candidates=len(records))
        bstate = store.row("SELECT condition FROM building_state"
                           " WHERE building_id = ?",
                           (inst["building_id"],))
        inst_score = bstate["condition"] if bstate else 50.0
        teacher_score = inst_mod.teacher_score_for(store, iid,
                                                   month_index)
        scores = []
        for rec in records:
            cid = rec["character_id"]
            for subj in subjects_for(data, rec):
                sid = subj["id"]
                lr = store.row("SELECT proficiency FROM learning_records"
                               " WHERE character_id = ? AND subject_id"
                               " = ?", (cid, sid))
                prof = lr["proficiency"] if lr else 0.0
                jitter = rng.stream("exam", exam_id, cid, sid).uniform(
                    -xcfg["jitter_points"], xcfg["jitter_points"])
                score = exam_score(rec["attendance_rate"] or 0.0, prof,
                                   teacher_score, inst_score, jitter,
                                   xcfg["weights"])
                rid = store.next_id("ER", "examination_results",
                                    "result_id")
                store.insert(
                    "examination_results", result_id=rid, exam_id=exam_id,
                    character_id=cid, subject_id=sid, score=score,
                    grade=grade_for(score, xcfg["grade_bands"]),
                    attendance_rate=rec["attendance_rate"] or 0.0,
                    proficiency=prof, teacher_score=teacher_score,
                    institution_score=inst_score, jitter=jitter)
                scores.append(score)
        mean = round(sum(scores) / len(scores), 2) if scores else None
        store.execute("UPDATE examinations SET mean_score = ?"
                      " WHERE exam_id = ?", (mean, exam_id))
        out[iid] = {"exam_id": exam_id, "candidates": len(records),
                    "results": len(scores), "mean_score": mean}
    return out


def issue_certifications(store, data, month_index, game_minutes):
    """Certificates for education records that completed without
    one. School-leaving requires a measured examination mean at or
    above the pass mark; a college completion IS the credential
    (Session 02) and its certificate records the fact."""
    xcfg = _cfg(data)["examinations"]
    issued = 0
    for rec in store.rows("SELECT * FROM education_records"
                          " WHERE status = 'completed'"
                          " ORDER BY record_id"):
        cid = rec["character_id"]
        if rec["programme"] == edu_mod.SCHOOL_PROGRAMME:
            kind, programme = "school_leaving", None
        else:
            kind, programme = "college_credential", rec["programme"]
        if store.row("SELECT 1 FROM certifications WHERE character_id"
                     " = ? AND kind = ? AND programme IS ?",
                     (cid, kind, programme)):
            continue
        mean = store.row("SELECT AVG(score) AS s FROM examination_results"
                         " WHERE character_id = ?", (cid,))
        mean_score = mean["s"] if mean else None
        if kind == "school_leaving":
            if mean_score is None or mean_score < xcfg["pass_mark"]:
                continue  # completed without a certificate — distinct
        cert_id = store.next_id("CT", "certifications",
                                "certification_id")
        store.insert("certifications", certification_id=cert_id,
                     character_id=cid,
                     institution_id=rec["institution_id"], kind=kind,
                     programme=programme,
                     mean_score=(round(mean_score, 2)
                                 if mean_score is not None else None),
                     issued_month=month_index,
                     game_minutes=game_minutes)
        # Queue 17 Unit DN: the certification is also a losable
        # document row (data/documents.json: school_leaving ->
        # school_leaving_certificate, college_credential ->
        # college_credential) for the graduate, so a credential can
        # be lost via record_loss() and recovered via DF's wiring.
        # The rule, stated here and in GDD-04 §3.3: a LOST credential
        # is NOT a revoked one. The certifications row stands
        # whatever happens to the paper, so has_credential() — which
        # reads education_records, never inventory — still returns
        # True while the document row is `lost`; losing the paper
        # loses only the paper, never the qualification.
        from . import lost_items as lost_items_mod
        doc_id = ("school_leaving_certificate"
                  if kind == "school_leaving" else "college_credential")
        lost_items_mod.seed_document_row(
            store, data, cid, doc_id, game_minutes,
            {"certification_id": cert_id, "kind": kind,
             "programme": programme})
        memory_mod.log_life_event(store, cid, "certification_issued",
                                  game_minutes,
                                  details={"kind": kind,
                                           "programme": programme})
        issued += 1
    return issued


def _household_persistent_arrears(store, character_id):
    """Measured financial distress: the student's household has
    debt outstanding AND unpaid emergencies in its last two
    monthly finance records (family_economy.py's own facts)."""
    char = store.row("SELECT household_id FROM characters"
                     " WHERE character_id = ?", (character_id,))
    if not char or not char["household_id"]:
        return False
    hid = char["household_id"]
    state = store.row("SELECT debt_ncr FROM household_state"
                      " WHERE household_id = ?", (hid,))
    if not state or not state["debt_ncr"]:
        return False
    rows = store.rows("SELECT emergency_ncr FROM household_finances"
                      " WHERE household_id = ? ORDER BY month_index"
                      " DESC LIMIT 2", (hid,))
    return len(rows) == 2 and all(r["emergency_ncr"] > 0 for r in rows)


def process_dropouts(store, data, month_index, game_minutes):
    """Apply the config's justified-dropout rules from measured
    records. Returns the list of (character_id, cause)."""
    from .identity import age_years
    dcfg = _cfg(data)["dropout"]
    xcfg = _cfg(data)["examinations"]
    out = []
    for rec in store.rows("SELECT * FROM education_records"
                          " WHERE status = 'enrolled'"
                          " ORDER BY record_id"):
        cid = rec["character_id"]
        char = store.row("SELECT born_at_game_minutes FROM characters"
                         " WHERE character_id = ?", (cid,))
        if char is None:
            continue
        cause = None
        if rec["programme"] == edu_mod.SCHOOL_PROGRAMME:
            age = age_years(char["born_at_game_minutes"], game_minutes)
            if age < dcfg["school_min_age"]:
                continue
            latest = store.row(
                "SELECT AVG(score) AS s FROM examination_results"
                " WHERE character_id = ? AND exam_id = (SELECT exam_id"
                " FROM examination_results WHERE character_id = ?"
                " ORDER BY result_id DESC LIMIT 1)", (cid, cid))
            measured = (latest["s"] if latest and latest["s"]
                        is not None else rec["performance"])
            if measured < xcfg["pass_mark"] and \
                    _household_persistent_arrears(store, cid):
                cause = "household_financial_distress"
        else:
            recent = _attendance_window(store, cid, "college",
                                        game_minutes, 0, 30)
            prior = _attendance_window(store, cid, "college",
                                       game_minutes, 30, 60)
            floor = dcfg["college_attendance_floor"]
            if recent < floor and prior < floor:
                cause = "persistent_non_attendance"
        if cause:
            store.execute("UPDATE education_records SET status ="
                          " 'dropped_out' WHERE record_id = ?",
                          (rec["record_id"],))
            memory_mod.log_life_event(store, cid, "dropped_out",
                                      game_minutes,
                                      details={"cause": cause,
                                               "programme":
                                               rec["programme"]})
            out.append((cid, cause))
    return out


def monthly_pass(store, data, rng, month_index, game_minutes):
    """Academics' monthly cadence: learning + assignments every
    month; examinations in the calendar's exam months; then
    certifications and dropouts read the fresh records."""
    ecfg = _cfg(data)
    students, rows = update_learning(store, data, month_index,
                                     game_minutes)
    exams = {}
    if month_index % ecfg["calendar"]["exam_every_months"] == 0:
        exams = run_examinations(store, data, rng, month_index,
                                 game_minutes)
    certs = issue_certifications(store, data, month_index,
                                 game_minutes)
    drops = process_dropouts(store, data, month_index, game_minutes)
    return {"students_updated": students, "assignment_rows": rows,
            "examinations": exams, "certifications_issued": certs,
            "dropouts": len(drops)}
