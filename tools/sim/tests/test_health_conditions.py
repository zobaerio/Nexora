"""Session 06 — Health conditions (GDD-12): closed causes,
measured onset, treated/untreated courses, complications only
from untreated courses, rest through the scheduler's machinery,
elder mortality multiplier."""
import unittest

from tools.sim import health
from tools.sim.tests.common import rng
from tools.sim.tests.humandevcommon import citizen, hd_world

GM = 480


def _world_with_config(**overrides):
    store, d = hd_world()
    cfg = d.education_health_config["health"]
    for key, value in overrides.items():
        if key == "complication_chance":
            cfg["recovery_days"]["complication_chance"] = value
        else:
            cfg[key] = value
    return store, d


class TestConditions(unittest.TestCase):
    def test_closed_cause_list(self):
        store, d = hd_world()
        cid = citizen(store, age=30)
        with self.assertRaises(ValueError):
            health.start_condition(store, d, rng(), cid, "injured",
                                   "spontaneous_combustion", 5, GM)
        out = health.start_condition(store, d, rng(), cid, "injured",
                                     "construction_accident", 5, GM)
        self.assertIsNotNone(out)
        row = store.row("SELECT * FROM health_conditions WHERE"
                        " character_id = ?", (cid,))
        self.assertEqual(row["status"], "active")
        self.assertEqual(row["cause"], "construction_accident")
        self.assertGreater(row["recovery_end_day"], 5)
        self.assertEqual(row["treated"], 0)

    def test_one_open_condition_per_character(self):
        store, d = hd_world()
        cid = citizen(store, age=30)
        first = health.start_condition(store, d, rng(), cid, "unwell",
                                       "weather_exposure", 5, GM)
        second = health.start_condition(store, d, rng(), cid,
                                        "injured", "commute_incident",
                                        5, GM)
        self.assertIsNotNone(first)
        self.assertIsNone(second)

    def test_untreated_course_recovers_without_complication(self):
        store, d = _world_with_config(complication_chance=0.0)
        cid = citizen(store, age=30)
        health.start_condition(store, d, rng(), cid, "unwell",
                               "weather_exposure", 5, GM)
        row = store.row("SELECT * FROM health_conditions WHERE"
                        " character_id = ?", (cid,))
        closed, complicated = health._progress_courses(
            store, d, rng(), row["recovery_end_day"] + 1,
            (row["recovery_end_day"] + 1) * 1440)
        self.assertEqual((closed, complicated), (1, 0))
        row = store.row("SELECT * FROM health_conditions WHERE"
                        " character_id = ?", (cid,))
        self.assertEqual(row["status"], "closed")
        self.assertEqual(row["outcome"], "recovered_untreated")

    def test_untreated_injury_escalates_with_complication(self):
        store, d = _world_with_config(complication_chance=1.0)
        cid = citizen(store, age=30)
        health.start_condition(store, d, rng(), cid, "injured",
                               "commute_incident", 5, GM)
        row = store.row("SELECT * FROM health_conditions WHERE"
                        " character_id = ?", (cid,))
        closed, complicated = health._progress_courses(
            store, d, rng(), row["recovery_end_day"] + 1,
            (row["recovery_end_day"] + 1) * 1440)
        self.assertEqual((closed, complicated), (0, 1))
        row = store.row("SELECT * FROM health_conditions WHERE"
                        " character_id = ?", (cid,))
        self.assertEqual(row["status"], "active")
        self.assertEqual(row["band"], "serious")
        self.assertEqual(row["complicated"], 1)

    def test_treated_course_never_complicates(self):
        store, d = _world_with_config(complication_chance=1.0)
        cid = citizen(store, age=30)
        health.start_condition(store, d, rng(), cid, "injured",
                               "commute_incident", 5, GM)
        store.execute("UPDATE health_conditions SET status ="
                      " 'recovering', treated = 1 WHERE"
                      " character_id = ?", (cid,))
        row = store.row("SELECT * FROM health_conditions WHERE"
                        " character_id = ?", (cid,))
        closed, complicated = health._progress_courses(
            store, d, rng(), row["recovery_end_day"] + 1,
            (row["recovery_end_day"] + 1) * 1440)
        self.assertEqual((closed, complicated), (1, 0))
        row = store.row("SELECT status, outcome FROM"
                        " health_conditions WHERE character_id = ?",
                        (cid,))
        self.assertEqual(row["status"], "closed")
        self.assertEqual(row["outcome"], "recovered")

    def test_serious_condition_sets_rest_days(self):
        store, d = hd_world()
        cid = citizen(store, age=30)
        health.start_condition(store, d, rng(), cid, "serious",
                               "age_related", 10, 10 * 1440)
        health._apply_rest_days(store, 10)
        st = store.row("SELECT rest_day FROM agent_state WHERE"
                       " character_id = ?", (cid,))
        self.assertEqual(st["rest_day"], 1)

    def test_onset_applies_illness_emotion(self):
        store, d = hd_world()
        cid = citizen(store, age=30)
        before = store.row("SELECT stress FROM emotional_state"
                           " WHERE character_id = ?",
                           (cid,))["stress"]
        health.start_condition(store, d, rng(), cid, "unwell",
                               "weather_exposure", 5, GM)
        after = store.row("SELECT stress FROM emotional_state WHERE"
                          " character_id = ?", (cid,))["stress"]
        self.assertGreater(after, before)

    def test_mortality_multiplier(self):
        store, d = hd_world()
        elder = citizen(store, age=70)
        self.assertEqual(health.mortality_multiplier(store, elder),
                         1.0)
        health.start_condition(store, d, rng(), elder, "serious",
                               "age_related", 5, GM)
        self.assertEqual(health.mortality_multiplier(store, elder),
                         3.0)
        young = citizen(store, age=30)
        health.start_condition(store, d, rng(), young, "serious",
                               "construction_accident", 5, GM)
        # The multiplier itself is condition-driven; the age >= 65
        # gate lives in lifecycle.daily_check, which is the only
        # caller.
        self.assertEqual(health.mortality_multiplier(store, young),
                         3.0)


class TestProfiles(unittest.TestCase):
    def test_profile_score_moves_toward_measured_target(self):
        store, d = hd_world()
        cid = citizen(store, age=30)
        health.monthly_pass(store, d, rng(), 1, 30 * 1440)
        seeded = store.row("SELECT health_score FROM health_profiles"
                           " WHERE character_id = ?",
                           (cid,))["health_score"]
        store.execute("UPDATE needs_state SET healthcare = 90,"
                      " sleep = 90, hunger = 90 WHERE character_id"
                      " = ?", (cid,))
        health.monthly_pass(store, d, rng(), 2, 60 * 1440)
        row = store.row("SELECT * FROM health_profiles WHERE"
                        " character_id = ?", (cid,))
        # target = .5*90 + .25*90 + .25*90 = 90 (age 30: no
        # penalties); the score moves halfway from its seed.
        self.assertEqual(row["health_score"],
                         round(seeded + (90.0 - seeded) * 0.5, 2))
        self.assertEqual(row["chronic"], 0)

    def test_profiles_persist_across_months(self):
        store, d = hd_world()
        cid = citizen(store, age=30)
        health.monthly_pass(store, d, rng(), 1, 30 * 1440)
        health.monthly_pass(store, d, rng(), 2, 60 * 1440)
        rows = store.rows("SELECT * FROM health_profiles WHERE"
                          " character_id = ?", (cid,))
        self.assertEqual(len(rows), 1)  # one profile, updated


if __name__ == "__main__":
    unittest.main()
