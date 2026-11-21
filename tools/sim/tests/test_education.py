"""Session 02 Unit 08 — Education & Social Development: enrolment,
measured attendance, performance with parent involvement, GDD-11
caps, college credentials and the hiring gate."""
import unittest

from tools.sim.tests.common import (data, employ, make_household,
                                    make_person, make_store, rng,
                                    set_needs, set_profile)
from tools.sim import decisions as dec
from tools.sim import education as edu
from tools.sim import lifecycle


class TestEducation(unittest.TestCase):
    def test_programme_table_matches_professions(self):
        d = data()
        for pid, skill in edu.GATED_PROGRAMMES.items():
            self.assertEqual(d.professions[pid]["primary_skills"][0],
                             skill)
        self.assertEqual(edu.school_id(d), "b_d1_civic_school")
        self.assertEqual(edu.college_id(d), "b_d1_education_college")

    def test_school_enrolment_sweep(self):
        store = make_store()
        d = data()
        kid = make_person(store, age=8, first="Kid")
        teen = make_person(store, age=16, first="Teen")
        adult = make_person(store, age=30, first="Adult")
        n = edu.enrol_school_sweep(store, d, 480)
        self.assertEqual(n, 2)
        self.assertTrue(edu.is_school_student(store, kid))
        self.assertTrue(edu.is_school_student(store, teen))
        self.assertIsNone(edu.active_record(store, adult, "school"))
        # Idempotent.
        self.assertEqual(edu.enrol_school_sweep(store, d, 1000), 0)

    def test_school_cap_binds_education_only(self):
        store = make_store()
        kid = make_person(store, age=10, first="Kid")
        edu._enrol(store, kid, edu.school_id(data()), "school", 480)
        for _ in range(120):
            edu.accrue_school_study(store, kid, 10)
        level = dec.skill_level(store, kid, "subject_knowledge")
        self.assertEqual(level, edu.SCHOOL_CAP_LEVEL)
        # Work-source xp (direct add) can pass the cap — the cap
        # binds the source, not the person.
        dec.add_skill_xp(store, kid, "subject_knowledge", 500)
        self.assertGreater(dec.skill_level(store, kid,
                                           "subject_knowledge"),
                           edu.SCHOOL_CAP_LEVEL)

    def test_college_completion_grants_credential(self):
        store = make_store()
        d = data()
        ya = make_person(store, age=20, first="Student")
        make_household(store, [ya])
        self.assertFalse(edu.has_credential(store, ya, "doctor"))
        edu.enrol_college(store, d, ya, "doctor", 480)
        self.assertIsNotNone(edu.college_enrolment(store, ya))
        # Template switches to the student day while enrolled.
        tid, _ = lifecycle.template_id_for(store, ya, 20, None)
        self.assertEqual(tid, "student_day")
        # Study accrues the programme skill under the college cap.
        for _ in range(100):
            edu.accrue_college_study(store, ya, 8)
        level = dec.skill_level(store, ya, "medicine")
        self.assertEqual(level, edu.COLLEGE_CAP_LEVEL)
        edu.monthly_sweep(store, d, 30 * 1440)
        self.assertTrue(edu.has_credential(store, ya, "doctor"))
        goal = store.row("SELECT status FROM character_goals"
                         " WHERE character_id = ? AND goal_type ="
                         " 'college_programme'", (ya,))
        self.assertEqual(goal["status"], "completed")

    def test_hiring_gate(self):
        """Without a credential, job-seeking cannot land a gated
        profession; with one, it can."""
        store = make_store()
        d = data()
        ya = make_person(store, age=24, first="Hopeful")
        make_household(store, [ya])
        set_needs(store, ya, financial=5, social=90, sleep=90, rest=90,
                  safety=90, development=90, education=90)
        set_profile(store, ya, ambition=60, intelligence=95)
        # Give them overwhelming medicine skill — skill alone must
        # not open the gate (GDD-11 acceptance check 4).
        dec.add_skill_xp(store, ya, "medicine", 90 * 50)
        result = dec.decide(store, d, rng(), store.row(
            "SELECT * FROM characters WHERE character_id = ?", (ya,)),
            0, 480, set())
        self.assertEqual(result, "seek_employment")
        emp = store.row("SELECT profession_id FROM employments"
                        " WHERE character_id = ?", (ya,))
        self.assertNotIn(emp["profession_id"], edu.GATED_PROGRAMMES)

    def test_performance_reflects_involvement(self):
        store = make_store()
        d = data()
        teacher = make_person(store, age=35, first="Teach")
        kid_a = make_person(store, age=9, first="KidA")
        orphan = make_person(store, age=9, first="Orphan")
        from tools.sim import relationships as rel
        rel.add_edge(store, teacher, kid_a, "parent", 480,
                     both_ways=False)
        employ(store, d, teacher, "teacher", tier=1)
        edu.enrol_school_sweep(store, d, 480)
        edu.monthly_sweep(store, d, 1000)
        rec_a = edu.active_record(store, kid_a, "school")
        rec_o = edu.active_record(store, orphan, "school")
        self.assertEqual(rec_a["parent_involvement"], 20)
        self.assertEqual(rec_o["parent_involvement"], 0)
        self.assertGreater(rec_a["performance"], rec_o["performance"])


if __name__ == "__main__":
    unittest.main()
