"""Session 06 — Educational institutions & teachers: the registry
is grounded in real buildings, assignments are real citizens with
measured evaluations, budgets are config authority."""
import unittest

from tools.sim import education as edu
from tools.sim import humandev as humandev_mod
from tools.sim import institutions as inst
from tools.sim.tests.humandevcommon import citizen, hd_world


class TestInstitutions(unittest.TestCase):
    def test_registry_grounded_in_real_buildings(self):
        store, d = hd_world()
        rows = store.rows("SELECT * FROM educational_institutions"
                          " ORDER BY institution_id")
        self.assertEqual(len(rows), 4)
        buildings = d.all_buildings()
        for row in rows:
            self.assertIn(row["building_id"], buildings)
        types = {r["institution_id"]: r["institution_type"]
                 for r in rows}
        self.assertEqual(types["EDU-RUPSHA-SCHOOL"], "school")
        self.assertEqual(types["EDU-RUPSHA-COLLEGE"], "college")
        self.assertEqual(types["EDU-SHIBNAGAR-SCHOOL"],
                         "primary_school")
        # No university was fabricated: the framework's types are
        # config, the registry holds only real buildings.
        self.assertNotIn("university",
                         {r["institution_type"] for r in rows})
        depts = store.rows("SELECT * FROM institution_departments"
                           " WHERE institution_id ="
                           " 'EDU-RUPSHA-COLLEGE'")
        self.assertEqual({r["department"] for r in depts},
                         {"engineering", "medicine", "education",
                          "technology"})

    def test_setup_is_idempotent(self):
        store, d = hd_world()
        out = humandev_mod.setup_humandev(store, d, 480)
        self.assertTrue(out["already_setup"])
        self.assertEqual(store.row(
            "SELECT COUNT(*) AS n FROM educational_institutions"
        )["n"], 4)

    def test_teacher_assignments_and_evaluations(self):
        store, d = hd_world()
        teachers = [citizen(store, age=35, profession_id="teacher",
                            first=f"Teacher{i}") for i in range(3)]
        out = inst.monthly_pass(store, d, 1, 30 * 1440)
        self.assertEqual(out["teachers_assigned"], 3)
        rows = store.rows("SELECT * FROM teacher_assignments"
                          " WHERE month_index = 1")
        self.assertEqual({r["character_id"] for r in rows},
                         set(teachers))
        for r in rows:
            self.assertEqual(r["institution_id"], "EDU-RUPSHA-SCHOOL")
            # Evaluation is a measured number (teaching-skill
            # fallback before any examination exists), not a
            # constant: genesis teachers carry skill 0, so the
            # honest value here is 0.0.
            self.assertIsNotNone(r["evaluation_score"])
        # Month replay writes nothing twice.
        out2 = inst.monthly_pass(store, d, 1, 30 * 1440)
        self.assertEqual(out2["teachers_assigned"], 0)

    def test_college_lecturer_posts_follow_enrolment(self):
        store, d = hd_world()
        for i in range(2):
            citizen(store, age=40, profession_id="teacher",
                    first=f"Teacher{i}")
        student = citizen(store, age=20, first="Student")
        edu.enrol_college(store, d, student, "doctor", 480)
        inst.monthly_pass(store, d, 1, 30 * 1440)
        rows = store.rows("SELECT * FROM teacher_assignments"
                          " WHERE month_index = 1")
        college = [r for r in rows
                   if r["institution_id"] == "EDU-RUPSHA-COLLEGE"]
        school = [r for r in rows
                  if r["institution_id"] == "EDU-RUPSHA-SCHOOL"]
        self.assertEqual(len(college), 1)  # 1 per 10 enrolled, min 1
        self.assertEqual(len(school), 1)
        self.assertEqual(college[0]["subject"], "programme")

    def test_budget_authority_from_config(self):
        store, d = hd_world()
        citizen(store, age=35, profession_id="teacher")
        inst.monthly_pass(store, d, 1, 30 * 1440)
        row = store.row("SELECT * FROM educational_institutions"
                        " WHERE institution_id = 'EDU-RUPSHA-SCHOOL'")
        expect = d.education_health_config["education"][
            "institution_types"]["school"]["monthly_budget_ncr"]
        self.assertEqual(row["monthly_budget_ncr"], expect)
        self.assertEqual(row["budget_spent_month_ncr"], 0)
        self.assertEqual(row["capacity_students"], 400)

    def test_teacher_score_zero_without_teachers(self):
        store, d = hd_world()
        self.assertEqual(
            inst.teacher_score_for(store, "EDU-RUPSHA-SCHOOL", 1), 0.0)


if __name__ == "__main__":
    unittest.main()
