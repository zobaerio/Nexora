"""Session 06 — Research Ecosystem (college-based).

The world's only higher-education institution is the District
College (GDD-11: a college, not a university — no university
exists in the building data, and none is invented here). Research
therefore lives at the college, in the spec's shape:

- Projects are led by real lecturer citizens (this month's
  teacher assignments at the college), funded from a configured
  share of the college's monthly civic budget authority — the
  spend is accounted on the institution's own budget counter
  (institutions.py), never invented money.
- A project runs a configured number of months, then completes
  into a research_record: a publication as a simulated record
  (field + project reference), persisted like every other record.
- Completion raises the college's measured research_capability,
  which feeds its institution performance (institutions.py) and
  the human-development research-activity indicator (humandev.py)
  — the configurable institutional-development effect, stated as
  a rule, not hidden in a formula elsewhere.
- When the college has no lecturer, no project starts: research
  does not conjure researchers.
- Session 10: the capability gain from a completion is scaled
  by the technology factor for the project's field
  (integration.technology_factor — derived from the world's own
  accumulated publications + credentialed share). The factor is
  exactly 1.0 when the integration layer is absent or no level
  is recorded yet, so pre-Session-10 behaviour is unchanged.
"""
import json


def _cfg(data):
    return data.education_health_config["research"]


def _college(store):
    return store.row("SELECT * FROM educational_institutions WHERE"
                     " level = 'college' AND active = 1"
                     " ORDER BY institution_id LIMIT 1")


def monthly_pass(store, data, rng, month_index, game_minutes):
    rcfg = _cfg(data)
    college = _college(store)
    if college is None:
        return {"research": "no college"}
    iid = college["institution_id"]
    out = {"completed": 0, "started": 0}
    # Completions first: projects whose term has run.
    for proj in store.rows("SELECT * FROM research_projects WHERE"
                           " institution_id = ? AND status = 'active'"
                           " AND ends_month <= ? ORDER BY project_id",
                           (iid, month_index)):
        store.execute("UPDATE research_projects SET status ="
                      " 'completed', completed_month = ?"
                      " WHERE project_id = ?",
                      (month_index, proj["project_id"]))
        rid = store.next_id("RR", "research_records", "record_id")
        store.insert("research_records", record_id=rid,
                     project_id=proj["project_id"], institution_id=iid,
                     field=proj["field"], kind="publication",
                     month_index=month_index,
                     game_minutes=game_minutes,
                     details=json.dumps(
                         {"lead_character_id":
                          proj["lead_character_id"],
                          "budget_ncr": proj["budget_ncr"]},
                         sort_keys=True))
        from . import integration as integration_mod
        gain = rcfg["capability_gain_per_completion"] \
            * integration_mod.technology_factor(
                store, data, proj["field"])
        store.execute("UPDATE educational_institutions SET"
                      " research_capability = research_capability + ?"
                      " WHERE institution_id = ?",
                      (gain, iid))
        out["completed"] += 1
    # One active project at a time; start the next when a lecturer
    # exists and the budget share is unspent.
    active = store.row("SELECT 1 FROM research_projects WHERE"
                       " institution_id = ? AND status = 'active'",
                       (iid,))
    if active is None:
        lead = store.row("SELECT character_id FROM teacher_assignments"
                         " WHERE institution_id = ? AND month_index = ?"
                         " ORDER BY assignment_id LIMIT 1",
                         (iid, month_index))
        budget = int(college["monthly_budget_ncr"]
                     * rcfg["monthly_budget_share"])
        if lead and budget > 0 \
                and college["budget_spent_month_ncr"] + budget \
                <= college["monthly_budget_ncr"]:
            field = rng.stream("research-field", iid,
                               month_index).choice(rcfg["fields"])
            duration = rng.stream("research-duration", iid,
                                  month_index).randint(
                *rcfg["project_duration_months"])
            pid = store.next_id("RP", "research_projects", "project_id")
            store.insert("research_projects", project_id=pid,
                         institution_id=iid,
                         lead_character_id=lead["character_id"],
                         field=field, status="active",
                         budget_ncr=budget, started_month=month_index,
                         ends_month=month_index + duration,
                         game_minutes=game_minutes)
            store.execute("UPDATE educational_institutions SET"
                          " budget_spent_month_ncr ="
                          " budget_spent_month_ncr + ?"
                          " WHERE institution_id = ?", (budget, iid))
            out["started"] += 1
            out["field"] = field
    return out
