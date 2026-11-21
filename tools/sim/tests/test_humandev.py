"""Session 06 — Wellbeing, research, human development
indicators: wellbeing derived from Session 01/02 state, research
as persistent records at the real college, HDI per the documented
methodology in humandev.METHODOLOGY."""
import unittest

from tools.sim import education as edu
from tools.sim import humandev
from tools.sim import institutions as inst
from tools.sim import research
from tools.sim import wellbeing
from tools.sim.tests.common import rng
from tools.sim.tests.humandevcommon import citizen, hd_world


class TestWellbeing(unittest.TestCase):
    def test_snapshot_from_measured_state(self):
        store, d = hd_world()
        cid = citizen(store, age=30)
        store.execute("UPDATE emotional_state SET stress = 80,"
                      " loneliness = 60 WHERE character_id = ?",
                      (cid,))
        snap = wellbeing.snapshot_character(store, cid)
        self.assertEqual(snap["stress"], 80)
        self.assertEqual(snap["loneliness"], 60)
        # No friends, household of 1, no community membership:
        # support = 0*12 + 1*6 + 0 = 6.
        self.assertEqual(snap["social_support"], 6.0)

    def test_monthly_snapshots_persist(self):
        store, d = hd_world()
        citizen(store, age=30)
        citizen(store, age=40)
        out = wellbeing.monthly_pass(store, d, 1, 30 * 1440)
        self.assertEqual(out["wellbeing_snapshots"], 2)
        rows = store.rows("SELECT * FROM wellbeing_records WHERE"
                          " month_index = 1")
        self.assertEqual(len(rows), 2)
        for r in rows:
            self.assertIsNotNone(r["work_life"])


class TestResearch(unittest.TestCase):
    def _college_world(self):
        store, d = hd_world()
        citizen(store, age=40, profession_id="teacher",
                first="Lecturer")
        student = citizen(store, age=20, first="Student")
        edu.enrol_college(store, d, student, "doctor", 480)
        inst.monthly_pass(store, d, 1, 30 * 1440)
        return store, d

    def test_project_starts_with_real_lecturer(self):
        store, d = self._college_world()
        out = research.monthly_pass(store, d, rng(), 1, 30 * 1440)
        self.assertEqual(out["started"], 1)
        proj = store.row("SELECT * FROM research_projects")
        self.assertEqual(proj["institution_id"], "EDU-RUPSHA-COLLEGE")
        self.assertEqual(proj["status"], "active")
        self.assertGreater(proj["ends_month"], 1)
        self.assertGreater(proj["budget_ncr"], 0)
        college = store.row("SELECT * FROM educational_institutions"
                            " WHERE institution_id ="
                            " 'EDU-RUPSHA-COLLEGE'")
        self.assertEqual(college["budget_spent_month_ncr"],
                         proj["budget_ncr"])

    def test_completion_writes_publication_and_capability(self):
        store, d = self._college_world()
        research.monthly_pass(store, d, rng(), 1, 30 * 1440)
        proj = store.row("SELECT * FROM research_projects")
        before = store.row("SELECT research_capability FROM"
                           " educational_institutions WHERE"
                           " institution_id = 'EDU-RUPSHA-COLLEGE'"
                           )["research_capability"]
        out = research.monthly_pass(store, d, rng(),
                                    proj["ends_month"],
                                    proj["ends_month"] * 30 * 1440)
        self.assertEqual(out["completed"], 1)
        rec = store.row("SELECT * FROM research_records")
        self.assertEqual(rec["kind"], "publication")
        self.assertEqual(rec["project_id"], proj["project_id"])
        after = store.row("SELECT research_capability FROM"
                          " educational_institutions WHERE"
                          " institution_id = 'EDU-RUPSHA-COLLEGE'"
                          )["research_capability"]
        self.assertEqual(after, before + 2.0)

    def test_no_lecturer_no_project(self):
        store, d = hd_world()
        out = research.monthly_pass(store, d, rng(), 1, 30 * 1440)
        self.assertEqual(out.get("started", 0), 0)
        self.assertIsNone(store.row("SELECT * FROM research_projects"))


class TestIndicators(unittest.TestCase):
    def test_model_life_expectancy_matches_methodology(self):
        # The documented model value: integrating the lifecycle
        # death-probability curve gives 65.61 years.
        self.assertEqual(humandev.model_life_expectancy(), 65.61)

    def test_components_from_persistent_data(self):
        store, d = hd_world()
        kid = citizen(store, age=10, first="Kid")
        adult = citizen(store, age=30, first="Adult")
        edu.enrol_school_sweep(store, d, 480)
        ind = humandev.compute_indicators(store, d, 1, 30 * 1440)
        self.assertEqual(ind["population"], 2)
        self.assertEqual(ind["education_access"], 1.0)
        self.assertEqual(ind["healthcare_access"], 1.0)
        self.assertEqual(ind["life_expectancy_model"], 65.61)
        # No economic_indicators rows in the fixture -> no GDP ->
        # no HDI (a component is absent, never invented).
        self.assertNotIn("hdi", ind)
        self.assertNotIn("gdp_per_capita_ncr", ind)

    def test_hdi_is_geometric_mean_of_indices(self):
        store, d = hd_world()
        citizen(store, age=30)
        citizen(store, age=10, first="Kid")
        edu.enrol_school_sweep(store, d, 480)
        store.insert("economic_indicators", scope="national",
                     month_index=1,
                     metrics='{"gdp_per_capita_ncr": 30478}',
                     game_minutes=30 * 1440)
        ind = humandev.compute_indicators(store, d, 1, 30 * 1440)
        import math
        expect = (ind["hdi_health_index"] * ind["hdi_education_index"]
                  * ind["hdi_income_index"]) ** (1 / 3)
        self.assertAlmostEqual(ind["hdi"], round(expect, 4), places=3)
        self.assertEqual(ind["hdi_health_index"],
                         round(65.61 / 85.0, 4))

    def test_indicators_persist_and_replay(self):
        store, d = hd_world()
        citizen(store, age=30)
        humandev.indicators_monthly(store, d, 1, 30 * 1440)
        humandev.indicators_monthly(store, d, 1, 30 * 1440)
        rows = store.rows("SELECT * FROM human_development_indicators"
                          " WHERE month_index = 1")
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
