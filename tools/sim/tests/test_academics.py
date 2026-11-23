"""Session 06 — Academics: learning from measured attendance,
examinations as pure functions of measured inputs, certifications
with a real pass rule, dropout only on measured circumstances."""
import unittest

from tools.sim import academics as acad
from tools.sim import decisions as dec
from tools.sim import education as edu
from tools.sim.tests.common import make_household, rng
from tools.sim.tests.humandevcommon import citizen, hd_world

GM_END = 30 * 1440


def _school_student(store, d, age=10, attendance=0.9):
    cid = citizen(store, age=age, first="Pupil")
    edu.enrol_school_sweep(store, d, 480)
    rec = edu.active_record(store, cid, "school")
    assert rec is not None
    store.execute("UPDATE education_records SET attendance_rate = ?,"
                  " performance = 60 WHERE record_id = ?",
                  (attendance, rec["record_id"]))
    return cid, rec["record_id"]


class TestLearning(unittest.TestCase):
    def test_proficiency_grows_with_attendance(self):
        store, d = hd_world()
        keen, _ = _school_student(store, d, attendance=1.0)
        absent, _ = _school_student(store, d, attendance=0.1)
        acad.monthly_pass(store, d, rng(), 1, GM_END)
        kp = store.row("SELECT proficiency FROM learning_records"
                       " WHERE character_id = ? AND subject_id ="
                       " 'mathematics'", (keen,))["proficiency"]
        ap = store.row("SELECT proficiency FROM learning_records"
                       " WHERE character_id = ? AND subject_id ="
                       " 'mathematics'", (absent,))["proficiency"]
        self.assertGreater(kp, ap)
        self.assertGreater(kp, 0)
        rows = store.rows("SELECT * FROM assignments WHERE"
                          " character_id = ?", (keen,))
        self.assertEqual(len(rows), 5)  # five school subjects
        for r in rows:
            self.assertLessEqual(r["completed_count"],
                                 r["assigned_count"])

    def test_academics_never_writes_character_skills(self):
        store, d = hd_world()
        cid, _ = _school_student(store, d)
        before = dec.skill_level(store, cid, "subject_knowledge")
        acad.monthly_pass(store, d, rng(), 1, GM_END)
        self.assertEqual(dec.skill_level(store, cid,
                                         "subject_knowledge"), before)


class TestExaminations(unittest.TestCase):
    def test_score_formula_is_pure(self):
        w = {"attendance": 0.4, "proficiency": 0.4, "teacher": 0.1,
             "institution": 0.1}
        a = acad.exam_score(0.9, 50, 40, 80, 3.0, w)
        b = acad.exam_score(0.9, 50, 40, 80, 3.0, w)
        self.assertEqual(a, b)
        self.assertEqual(a, round(0.9 * 100 * 0.4 + 50 * 0.4
                                  + 40 * 0.1 + 80 * 0.1 + 3.0, 2))
        self.assertEqual(acad.grade_for(85, [{"grade": "A",
                                              "min_score": 80},
                                             {"grade": "F",
                                              "min_score": 0}]), "A")

    def test_exam_batch_and_determinism(self):
        store, d = hd_world()
        citizen(store, age=35, profession_id="teacher")
        _school_student(store, d, attendance=1.0)
        _school_student(store, d, attendance=0.2)
        out = acad.monthly_pass(store, d, rng(), 3, 90 * 1440)
        exams = out["examinations"]
        self.assertIn("EDU-RUPSHA-SCHOOL", exams)
        results = store.rows("SELECT * FROM examination_results"
                             " ORDER BY character_id, subject_id")
        self.assertEqual(len(results), 10)  # 2 students x 5 subjects
        for r in results:
            # Every grade carries its measured inputs on the row.
            self.assertIsNotNone(r["attendance_rate"])
            self.assertIsNotNone(r["proficiency"])
            self.assertIsNotNone(r["institution_score"])
        # The full-attendance student outscores the low-attendance
        # one on the same subject (the input gap, 32 points,
        # exceeds the jitter band).
        by_student = {}
        for r in results:
            if r["subject_id"] == "mathematics":
                by_student[r["character_id"]] = r["score"]
        self.assertEqual(len(by_student), 2)
        self.assertGreater(max(by_student.values()),
                           min(by_student.values()))

    def test_exam_recompute_reproduces_scores(self):
        # Criterion 5: same stored inputs -> same results. A fresh
        # world built identically produces identical scores.
        def build():
            store, d = hd_world()
            citizen(store, age=35, profession_id="teacher")
            _school_student(store, d, attendance=0.85)
            acad.monthly_pass(store, d, rng(), 3, 90 * 1440)
            return sorted((r["character_id"], r["subject_id"],
                           r["score"]) for r in store.rows(
                "SELECT * FROM examination_results"))
        self.assertEqual(build(), build())


class TestCertificationsAndDropout(unittest.TestCase):
    def _completed_school_record(self, store, d, score):
        cid, rid = _school_student(store, d, age=17)
        acad.monthly_pass(store, d, rng(), 3, 90 * 1440)
        # Force the student's measured exam mean to `score`.
        store.execute("UPDATE examination_results SET score = ?"
                      " WHERE character_id = ?", (score, cid))
        store.execute("UPDATE education_records SET status ="
                      " 'completed', completed_at_game_minutes = ?"
                      " WHERE record_id = ?", (90 * 1440, rid))
        return cid

    def test_certificate_requires_measured_pass(self):
        store, d = hd_world()
        citizen(store, age=35, profession_id="teacher")
        good = self._completed_school_record(store, d, 72)
        n = acad.issue_certifications(store, d, 4, 120 * 1440)
        self.assertEqual(n, 1)
        cert = store.row("SELECT * FROM certifications WHERE"
                         " character_id = ?", (good,))
        self.assertEqual(cert["kind"], "school_leaving")
        self.assertEqual(cert["mean_score"], 72)

    def test_no_certificate_below_pass(self):
        store, d = hd_world()
        citizen(store, age=35, profession_id="teacher")
        weak = self._completed_school_record(store, d, 25)
        n = acad.issue_certifications(store, d, 4, 120 * 1440)
        self.assertEqual(n, 0)
        self.assertIsNone(store.row("SELECT * FROM certifications"
                                    " WHERE character_id = ?",
                                    (weak,)))
        # ...while the record itself still completed: the two
        # facts are distinct on purpose.
        rec = edu.active_record(store, weak, "school")
        self.assertIsNone(rec)

    def test_school_dropout_on_measured_distress(self):
        store, d = hd_world()
        cid, rid = _school_student(store, d, age=15, attendance=0.5)
        store.execute("UPDATE education_records SET performance = 20"
                      " WHERE record_id = ?", (rid,))
        char = store.row("SELECT household_id FROM characters WHERE"
                         " character_id = ?", (cid,))
        hid = char["household_id"]
        # Measured distress: debt outstanding + unpaid emergencies
        # in the last two monthly finance records.
        store.insert("household_state", household_id=hid,
                     debt_ncr=5000)
        for m in (1, 2):
            store.insert("household_finances",
                         finance_id=f"FIN-{m}", household_id=hid,
                         month_index=m, emergency_ncr=1200,
                         game_minutes=60 * 1440)
        out = acad.process_dropouts(store, d, 3, 90 * 1440)
        self.assertEqual(out, [(cid, "household_financial_distress")])
        rec = store.row("SELECT status FROM education_records WHERE"
                        " record_id = ?", (rid,))
        self.assertEqual(rec["status"], "dropped_out")

    def test_no_dropout_without_distress(self):
        store, d = hd_world()
        cid, rid = _school_student(store, d, age=15, attendance=0.5)
        store.execute("UPDATE education_records SET performance = 20"
                      " WHERE record_id = ?", (rid,))
        out = acad.process_dropouts(store, d, 3, 90 * 1440)
        self.assertEqual(out, [])

    def test_college_dropout_on_persistent_non_attendance(self):
        store, d = hd_world()
        cid = citizen(store, age=21, first="Student")
        edu.enrol_college(store, d, cid, "doctor", 480)
        # No schedules exist in the fixture, so both measured
        # attendance windows read 0.0 — below the floor.
        out = acad.process_dropouts(store, d, 3, 90 * 1440)
        self.assertIn((cid, "persistent_non_attendance"), out)

    def test_college_reenrolment_reactivates_dropped_record(self):
        store, d = hd_world()
        cid = citizen(store, age=21, first="Student")
        rid = edu.enrol_college(store, d, cid, "doctor", 480)
        acad.process_dropouts(store, d, 3, 90 * 1440)
        rid2 = edu.enrol_college(store, d, cid, "doctor", 100 * 1440)
        self.assertEqual(rid2, rid)  # same record, reactivated
        rec = edu.active_record(store, cid, "doctor")
        self.assertIsNotNone(rec)
        rows = store.rows("SELECT * FROM education_records WHERE"
                          " character_id = ?", (cid,))
        self.assertEqual(len(rows), 1)

    def test_school_sweep_never_reenrols_a_dropout(self):
        store, d = hd_world()
        cid, rid = _school_student(store, d, age=15, attendance=0.5)
        store.execute("UPDATE education_records SET status ="
                      " 'dropped_out' WHERE record_id = ?", (rid,))
        edu.enrol_school_sweep(store, d, 100 * 1440)
        rows = store.rows("SELECT * FROM education_records WHERE"
                          " character_id = ?", (cid,))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "dropped_out")


class TestCertificationDocumentRow(unittest.TestCase):
    """Queue 17 Unit DN — certification writes a losable document
    row (GDD-04 §3.3, Unit DE). A lost credential is NOT a revoked
    one: the certifications row stands, so the qualification holds
    whatever happens to the paper."""

    def test_school_leaving_writes_a_document_row(self):
        import json
        store, d = hd_world()
        citizen(store, age=35, profession_id="teacher")
        cid, rid = _school_student(store, d, age=17)
        acad.monthly_pass(store, d, rng(), 3, 90 * 1440)
        store.execute("UPDATE examination_results SET score = 72"
                      " WHERE character_id = ?", (cid,))
        store.execute("UPDATE education_records SET status ="
                      " 'completed', completed_at_game_minutes = ?"
                      " WHERE record_id = ?", (90 * 1440, rid))
        n = acad.issue_certifications(store, d, 4, 120 * 1440)
        self.assertEqual(n, 1)
        cert = store.row("SELECT * FROM certifications WHERE"
                         " character_id = ?", (cid,))
        rows = store.rows("SELECT * FROM inventory_items WHERE"
                          " owner_character_id = ? AND"
                          " item_type = 'document'", (cid,))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["item_ref"],
                         "school_leaving_certificate")
        self.assertEqual(json.loads(rows[0]["state"]),
                         {"certification_id":
                          cert["certification_id"],
                          "kind": "school_leaving",
                          "programme": None})

    def test_college_credential_writes_a_document_row(self):
        import json
        store, d = hd_world()
        cid = citizen(store, age=21, first="Student")
        edu.enrol_college(store, d, cid, "doctor", 480)
        store.execute("UPDATE education_records SET status ="
                      " 'completed', completed_at_game_minutes = ?"
                      " WHERE character_id = ?",
                      (90 * 1440, cid))
        n = acad.issue_certifications(store, d, 4, 120 * 1440)
        self.assertEqual(n, 1)
        rows = store.rows("SELECT * FROM inventory_items WHERE"
                          " owner_character_id = ? AND"
                          " item_type = 'document'", (cid,))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["item_ref"], "college_credential")
        state = json.loads(rows[0]["state"])
        self.assertEqual(state["kind"], "college_credential")
        self.assertEqual(state["programme"], "doctor")

    def test_lost_credential_is_not_revoked(self):
        from tools.sim import lost_items as li
        store, d = hd_world()
        cid = citizen(store, age=21, first="Student")
        edu.enrol_college(store, d, cid, "doctor", 480)
        store.execute("UPDATE education_records SET status ="
                      " 'completed', completed_at_game_minutes = ?"
                      " WHERE character_id = ?",
                      (90 * 1440, cid))
        acad.issue_certifications(store, d, 4, 120 * 1440)
        row = store.row("SELECT * FROM inventory_items WHERE"
                        " owner_character_id = ?", (cid,))
        lid = li.record_loss(store, cid, row["item_instance_id"],
                             130 * 1440, "d1_midtown")
        self.assertIsNotNone(lid)
        # The paper is lost; the qualification stands.
        self.assertTrue(edu.has_credential(store, cid, "doctor"))
        self.assertIsNotNone(store.row(
            "SELECT * FROM certifications WHERE character_id = ?",
            (cid,)))
        # And the paper is recoverable through DF's wiring.
        self.assertEqual(li.find_lost_item(store, lid, cid,
                                           131 * 1440, "d1_midtown"),
                         lid)
        self.assertEqual(li.return_lost_item(store, lid, 132 * 1440),
                         lid)

    def test_reissue_writes_no_second_document_row(self):
        store, d = hd_world()
        citizen(store, age=35, profession_id="teacher")
        cid, rid = _school_student(store, d, age=17)
        acad.monthly_pass(store, d, rng(), 3, 90 * 1440)
        store.execute("UPDATE examination_results SET score = 72"
                      " WHERE character_id = ?", (cid,))
        store.execute("UPDATE education_records SET status ="
                      " 'completed', completed_at_game_minutes = ?"
                      " WHERE record_id = ?", (90 * 1440, rid))
        self.assertEqual(acad.issue_certifications(store, d, 4,
                                                  120 * 1440), 1)
        self.assertEqual(acad.issue_certifications(store, d, 5,
                                                  150 * 1440), 0)
        rows = store.rows("SELECT * FROM inventory_items WHERE"
                          " owner_character_id = ? AND"
                          " item_type = 'document'", (cid,))
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
