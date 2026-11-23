"""Session 02 Unit 08 — Education & Social Development.

The education loop GDD-11 designed, implemented against Session
01's machinery: schooling is *time in a place, recorded as skill*.

- Enrolment: every child/teen (3–17) is enrolled at the District
  School (b_d1_civic_school, from the buildings data) — a row in
  education_records, swept monthly so newborns ageing in and
  children arriving by guardianship are picked up by the same rule.
  (Session 06: school_id_for enrols Shibnagar-resident children at
  Shibnagar Primary School instead — the school in their own city;
  Rupsha behaviour is unchanged.)
- Attendance is measured, not assumed: the fraction of the last 30
  days whose persisted schedule contains a study block at the
  institution's location (school / college), read from
  instantiated_schedules.
- Performance combines attendance, the student's actual
  subject_knowledge, and parent involvement (a living parent's
  engagement, strongest when a parent teaches) — the inequality in
  the inputs is the simulated fact GDD-11 asks the system to carry.
- The caps are contract (GDD-11 §4): education sources alone cap
  subject_knowledge at level 20 and a college programme skill at
  24 — both below every tier-2 threshold in professions.json (30+),
  so education can never promote anyone by itself.
- College: a Young Adult enrols in a programme (a stage goal, per
  GDD-11 §5) at the District College; while enrolled their schedule
  runs the student_day template and study blocks accrue the
  programme skill. Completion at the cap converts the record to a
  credential, and the decision engine's hiring reads it: the four
  credential-gated professions (civil_engineer, doctor, teacher,
  software_developer — GDD-11 §5's table) cannot be entered without
  one. Genesis professionals are grandfathered: they were employed
  before the sim started, which the data represents directly.
- Education is civic and free in District 1 (GDD-11 §7): no fees,
  which is why the family accounts carry a 0 education line.
"""
from . import memory as memory_mod

# GDD-11 §5's programme table, transcribed: profession -> the skill
# its college programme teaches (each is the profession's first
# primary skill in professions.json — a test guards the match).
GATED_PROGRAMMES = {
    "civil_engineer": "engineering",
    "doctor": "medicine",
    "teacher": "teaching",
    "software_developer": "programming",
}
SCHOOL_CAP_LEVEL = 20     # GDD-11 §4
COLLEGE_CAP_LEVEL = 24    # GDD-11 §4
SCHOOL_PROGRAMME = "school"


def _building_id(data, name):
    for b in data.buildings:
        if b["name"] == name:
            return b["id"]
    return None


def school_id(data):
    return _building_id(data, "District School")


def shibnagar_school_id(data):
    for b in data.city2_file["properties"]:
        if b["name"] == "Shibnagar Primary School":
            return b["id"]
    return None


def school_id_for(store, data, character_id):
    """Session 06: a child enrols at the school of the city they
    live in — the same zone-membership rule the city layer counts
    population by. Rupsha residents (and everyone without a known
    city, including all genesis households) keep the District
    School, so pre-Session-06 behaviour is unchanged there;
    Shibnagar residents enrol at Shibnagar Primary School, the
    school that actually exists in their city."""
    row = store.row(
        "SELECT h.district_id FROM characters c JOIN households h"
        " ON h.household_id = c.household_id WHERE"
        " c.character_id = ?", (character_id,))
    if row and row["district_id"]:
        for spec in data.city_specs():
            if row["district_id"] in spec["zones"]:
                if spec["city_id"] == "shibnagar_town":
                    return shibnagar_school_id(data) \
                        or school_id(data)
                break
    return school_id(data)


def college_id(data):
    return _building_id(data, "District College")


def active_record(store, character_id, programme=None):
    sql = ("SELECT * FROM education_records WHERE character_id = ?"
           " AND status = 'enrolled'")
    params = [character_id]
    if programme is not None:
        sql += " AND programme = ?"
        params.append(programme)
    return store.row(sql, tuple(params))


def is_school_student(store, character_id):
    return active_record(store, character_id, SCHOOL_PROGRAMME) is not None


def college_enrolment(store, character_id):
    rec = store.row("SELECT * FROM education_records WHERE"
                    " character_id = ? AND status = 'enrolled'"
                    " AND programme != ?", (character_id, SCHOOL_PROGRAMME))
    return rec


def has_credential(store, character_id, profession_id):
    if profession_id not in GATED_PROGRAMMES:
        return True
    rec = store.row("SELECT * FROM education_records WHERE"
                    " character_id = ? AND programme = ?"
                    " AND status = 'completed'",
                    (character_id, profession_id))
    return rec is not None


def _enrol(store, character_id, institution_id, programme, game_minutes):
    rid = store.next_id("ED", "education_records", "record_id")
    store.insert("education_records", record_id=rid,
                 character_id=character_id, institution_id=institution_id,
                 programme=programme, status="enrolled",
                 started_at_game_minutes=game_minutes)
    return rid


def enrol_school_sweep(store, data, game_minutes):
    """Enrol every unenrolled 3–17-year-old at the District School;
    close the records of those who aged out or died. Returns the
    number newly enrolled."""
    from .identity import age_years
    sid = school_id(data)
    if sid is None:
        return 0
    count = 0
    chars = store.rows("SELECT * FROM characters WHERE is_system = 0"
                       " ORDER BY character_id")
    for c in chars:
        cid = c["character_id"]
        age = age_years(c["born_at_game_minutes"], game_minutes)
        rec = active_record(store, cid, SCHOOL_PROGRAMME)
        if c["died_at_game_minutes"] is not None:
            if rec:
                store.execute("UPDATE education_records SET status ="
                              " 'left' WHERE record_id = ?",
                              (rec["record_id"],))
            continue
        if 3 <= age <= 17 and rec is None:
            # A terminal record (completed / dropped out — the
            # dropout status arrived with Session 06) is final:
            # the automatic sweep never re-enrols over it (and
            # re-enrolling at the same school would violate the
            # records' UNIQUE key).
            terminal = store.row(
                "SELECT 1 FROM education_records WHERE character_id"
                " = ? AND programme = ? AND status IN ('completed',"
                " 'dropped_out')", (cid, SCHOOL_PROGRAMME))
            if terminal:
                continue
            _enrol(store, cid, school_id_for(store, data, cid),
                   SCHOOL_PROGRAMME, game_minutes)
            # Queue 17 Unit DK: the school uniform (GDD-09 §5 —
            # bought by the household) is issued beside the
            # enrolment, in the same call. One set per student; a
            # student who already holds it is not issued a second.
            from . import lost_items as lost_items_mod
            lost_items_mod.seed_school_uniform(store, data, cid,
                                               game_minutes)
            memory_mod.log_life_event(store, cid, "school_enrolled",
                                      game_minutes)
            count += 1
        elif age >= 18 and rec is not None:
            store.execute("UPDATE education_records SET status ="
                          " 'completed', completed_at_game_minutes = ?"
                          " WHERE record_id = ?",
                          (game_minutes, rec["record_id"]))
            memory_mod.log_life_event(store, cid, "school_completed",
                                      game_minutes)
    return count


def enrol_college(store, data, character_id, profession_id,
                  game_minutes):
    """Enrolment is a stage goal (GDD-11 §5): the goal is written,
    the record opened, and completion later converts both."""
    from . import identity as identity_mod
    cid_ = college_id(data)
    existing = store.row("SELECT * FROM education_records WHERE"
                         " character_id = ? AND institution_id = ?"
                         " AND programme = ?",
                         (character_id, cid_, profession_id))
    if existing is not None:
        # One record per (student, institution, programme) — the
        # table's UNIQUE key. A dropped-out student who chooses
        # college again (a deliberate decision, unlike the school
        # sweep) reactivates their record instead of duplicating
        # it; any other existing record is returned as-is.
        if existing["status"] == "dropped_out":
            store.execute("UPDATE education_records SET status ="
                          " 'enrolled', started_at_game_minutes = ?,"
                          " completed_at_game_minutes = NULL WHERE"
                          " record_id = ?",
                          (game_minutes, existing["record_id"]))
        return existing["record_id"]
    rid = _enrol(store, character_id, cid_, profession_id, game_minutes)
    identity_mod.add_goal(store, character_id, "stage",
                          "college_programme",
                          {"profession": profession_id}, game_minutes)
    memory_mod.log_life_event(store, character_id, "college_enrolled",
                              game_minutes,
                              details={"profession": profession_id})
    return rid


def _attendance(store, character_id, location, game_minutes,
                days=30):
    """Fraction of recent days with a study block at `location`,
    from the persisted instantiated schedules — measured, never
    assumed. Days before the sim persisted schedules don't count
    against the student."""
    import json as _json
    world = store.world()
    today = world["day_index"] if world else 0
    present, attended = 0, 0
    for day in range(max(0, today - days), today):
        row = store.row("SELECT blocks_json FROM instantiated_schedules"
                        " WHERE character_id = ? AND day_index = ?",
                        (character_id, day))
        if row is None:
            continue
        present += 1
        blocks = _json.loads(row["blocks_json"])
        if any(b["activity"] == "study" and b["location"] == location
               for b in blocks):
            attended += 1
    return round(attended / present, 3) if present else 0.0


def _parent_involvement(store, character_id):
    """0..20 from the parents' real state: a parent who teaches is
    the strongest involvement the sim can express; an engaged
    living parent (education need satisfied) is next; any living
    parent counts for something; none, for nothing."""
    from . import needs as needs_mod
    from . import relationships as rel
    best = 0
    for p in rel.parents_of(store, character_id):
        prow = store.row("SELECT died_at_game_minutes FROM characters"
                         " WHERE character_id = ?", (p,))
        if prow is None or prow["died_at_game_minutes"] is not None:
            continue
        emp = store.row("SELECT profession_id FROM employments"
                        " WHERE character_id = ?"
                        " AND ended_at_game_minutes IS NULL", (p,))
        if emp and emp["profession_id"] == "teacher":
            best = max(best, 20)
            continue
        needs = needs_mod.get_needs(store, p)
        if needs and needs["education"] >= 60:
            best = max(best, 12)
        else:
            best = max(best, 6)
    return best


def _capped_gain(store, character_id, skill_id, gain, cap_level):
    """Add skill xp from an *education source*, honouring the
    GDD-11 cap: education alone may not raise the skill past
    cap_level. Skill already above the cap (earned at work) is
    never reduced — the cap binds the source, not the person."""
    from . import decisions as decisions_mod
    row = store.row("SELECT experience FROM character_skills"
                    " WHERE character_id = ? AND skill_id = ?",
                    (character_id, skill_id))
    xp = row["experience"] if row else 0
    cap_xp = cap_level * 50 + 49
    allowed = max(0, min(gain, cap_xp - xp)) if xp < cap_xp else 0
    if allowed:
        decisions_mod.add_skill_xp(store, character_id, skill_id,
                                   allowed)
    return allowed


def accrue_school_study(store, character_id, hours):
    return _capped_gain(store, character_id, "subject_knowledge",
                        int(hours), SCHOOL_CAP_LEVEL)


def accrue_college_study(store, character_id, hours):
    rec = college_enrolment(store, character_id)
    if rec is None:
        return 0
    skill = GATED_PROGRAMMES[rec["programme"]]
    return _capped_gain(store, character_id, skill, int(hours * 2),
                        COLLEGE_CAP_LEVEL)


def monthly_sweep(store, data, game_minutes):
    """Enrolment, attendance, performance, completions — the
    monthly education batch. Returns a small summary dict."""
    from . import decisions as decisions_mod
    enrolled = enrol_school_sweep(store, data, game_minutes)
    updated = 0
    for rec in store.rows("SELECT * FROM education_records"
                          " WHERE status = 'enrolled'"):
        cid = rec["character_id"]
        if rec["programme"] == SCHOOL_PROGRAMME:
            rate = _attendance(store, cid, "school", game_minutes)
            from . import decisions as _dec
            skill = _dec.skill_level(store, cid, "subject_knowledge")
            involvement = _parent_involvement(store, cid)
            performance = max(0, min(100, round(
                rate * 60 + min(20, skill) + involvement)))
            store.execute(
                "UPDATE education_records SET attendance_rate = ?,"
                " performance = ?, parent_involvement = ?"
                " WHERE record_id = ?",
                (rate, performance, involvement, rec["record_id"]))
            updated += 1
        else:
            rate = _attendance(store, cid, "college", game_minutes)
            store.execute("UPDATE education_records SET"
                          " attendance_rate = ? WHERE record_id = ?",
                          (rate, rec["record_id"]))
            skill = GATED_PROGRAMMES[rec["programme"]]
            level = decisions_mod.skill_level(store, cid, skill)
            if level >= COLLEGE_CAP_LEVEL:
                store.execute(
                    "UPDATE education_records SET status = 'completed',"
                    " completed_at_game_minutes = ? WHERE record_id = ?",
                    (game_minutes, rec["record_id"]))
                decisions_mod.complete_goals_of_type(
                    store, cid, "college_programme", game_minutes)
                memory_mod.log_life_event(
                    store, cid, "graduated", game_minutes,
                    details={"profession": rec["programme"]})
                memory_mod.record_memory(store, cid, "graduated", 50,
                                         game_minutes)
    return {"newly_enrolled": enrolled, "records_updated": updated}
