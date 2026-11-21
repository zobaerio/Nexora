"""Session 06 — Healthcare delivery: facility staffing/capacity,
patient journeys, medication inventory gating treatment, civic
budgets with ledgered procurement, life-stage care."""
import json
import unittest

from tools.sim import health
from tools.sim import healthcare as care
from tools.sim.tests.common import rng
from tools.sim.tests.humandevcommon import citizen, hd_world

GM = 480
RUP = "HEALTH-RUPSHA-CLINIC"


def _facility(store, fid=RUP):
    return store.row("SELECT * FROM healthcare_facilities WHERE"
                     " facility_id = ?", (fid,))


def _staffed_world():
    store, d = hd_world()
    doctor = citizen(store, age=40, profession_id="doctor",
                     first="Doctor")
    return store, d, doctor


class TestFacilities(unittest.TestCase):
    def test_facilities_grounded_and_stocked(self):
        store, d = hd_world()
        rows = store.rows("SELECT * FROM healthcare_facilities"
                          " ORDER BY facility_id")
        self.assertEqual(len(rows), 2)
        buildings = d.all_buildings()
        for r in rows:
            self.assertIn(r["building_id"], buildings)
        stock = store.row("SELECT quantity FROM medical_inventory"
                          " WHERE facility_id = ? AND item_id ="
                          " 'sim_fever_course'", (RUP,))
        self.assertEqual(stock["quantity"], 60)  # config target
        genesis = store.rows("SELECT * FROM pharmacy_records WHERE"
                             " reason = 'genesis_stock'")
        self.assertEqual(len(genesis), 14)  # 7 items x 2 facilities

    def test_capacity_follows_doctors(self):
        store, d = hd_world()
        self.assertEqual(care.daily_capacity(store, d,
                                             _facility(store)), 6)
        citizen(store, age=40, profession_id="doctor")
        citizen(store, age=38, profession_id="doctor")
        self.assertEqual(care.daily_capacity(store, d,
                                             _facility(store)), 6 + 16)


class TestPatientJourney(unittest.TestCase):
    def test_full_journey_consumes_medication(self):
        store, d, doctor = _staffed_world()
        patient = citizen(store, age=30, first="Patient")
        cond_id = health.start_condition(
            store, d, rng(), patient, "unwell", "weather_exposure",
            5, 5 * 1440, facility_id=RUP)
        visit = store.row("SELECT * FROM patient_visits WHERE"
                          " condition_id = ?", (cond_id,))
        self.assertEqual(visit["stage"], "registered")
        before = store.row("SELECT quantity FROM medical_inventory"
                           " WHERE facility_id = ? AND item_id ="
                           " 'sim_fever_course'",
                           (RUP,))["quantity"]
        processed = care.process_daily_queue(store, d, rng(), 5,
                                             5 * 1440)
        self.assertEqual(processed, 1)
        visit = store.row("SELECT * FROM patient_visits WHERE"
                          " visit_id = ?", (visit["visit_id"],))
        self.assertEqual(visit["stage"], "treated")
        actions = {r["action"] for r in store.rows(
            "SELECT action FROM treatment_records WHERE visit_id = ?",
            (visit["visit_id"],))}
        self.assertEqual(actions, {"assessment", "treatment"})
        after = store.row("SELECT quantity FROM medical_inventory"
                          " WHERE facility_id = ? AND item_id ="
                          " 'sim_fever_course'",
                          (RUP,))["quantity"]
        self.assertEqual(after, before - 1)
        cond = store.row("SELECT * FROM health_conditions WHERE"
                         " condition_id = ?", (cond_id,))
        self.assertEqual(cond["status"], "recovering")
        self.assertEqual(cond["treated"], 1)

    def test_stockout_blocks_treatment(self):
        store, d, doctor = _staffed_world()
        patient = citizen(store, age=30, first="Patient")
        store.execute("UPDATE medical_inventory SET quantity = 0"
                      " WHERE facility_id = ? AND item_id ="
                      " 'sim_fever_course'", (RUP,))
        cond_id = health.start_condition(
            store, d, rng(), patient, "unwell", "weather_exposure",
            5, 5 * 1440, facility_id=RUP)
        care.process_daily_queue(store, d, rng(), 5, 5 * 1440)
        visit = store.row("SELECT * FROM patient_visits WHERE"
                          " condition_id = ?", (cond_id,))
        self.assertEqual(visit["stage"], "registered")
        self.assertEqual(json.loads(visit["details"])
                         ["awaiting_medication"], "sim_fever_course")
        actions = {r["action"] for r in store.rows(
            "SELECT action FROM treatment_records WHERE visit_id = ?",
            (visit["visit_id"],))}
        self.assertIn("awaiting_medication", actions)
        cond = store.row("SELECT treated FROM health_conditions"
                         " WHERE condition_id = ?", (cond_id,))
        self.assertEqual(cond["treated"], 0)

    def test_capacity_constraint(self):
        store, d, doctor = _staffed_world()
        capacity = care.daily_capacity(store, d, _facility(store))
        patients = [citizen(store, age=25, first=f"P{i}")
                    for i in range(capacity + 3)]
        for p in patients:
            care.register_visit(store, p, RUP, "follow_up", 5,
                                5 * 1440)
        processed = care.process_daily_queue(store, d, rng(), 5,
                                             5 * 1440)
        self.assertEqual(processed, capacity)
        remaining = store.row("SELECT COUNT(*) AS n FROM"
                              " patient_visits WHERE stage ="
                              " 'registered'")["n"]
        self.assertEqual(remaining, 3)

    def test_no_doctor_no_treatment(self):
        store, d = hd_world()
        patient = citizen(store, age=30, first="Patient")
        health.start_condition(store, d, rng(), patient, "unwell",
                               "weather_exposure", 5, 5 * 1440,
                               facility_id=RUP)
        processed = care.process_daily_queue(store, d, rng(), 5,
                                             5 * 1440)
        self.assertEqual(processed, 0)
        visit = store.row("SELECT stage FROM patient_visits WHERE"
                          " character_id = ?", (patient,))
        self.assertEqual(visit["stage"], "registered")

    def test_serious_case_referred_off_district(self):
        store, d, doctor = _staffed_world()
        patient = citizen(store, age=55, first="Patient")
        cond_id = health.start_condition(
            store, d, rng(), patient, "serious", "age_related",
            5, 5 * 1440, facility_id=RUP)
        visit = store.row("SELECT * FROM patient_visits WHERE"
                          " condition_id = ?", (cond_id,))
        care.process_daily_queue(store, d, rng(), 5, 5 * 1440)
        adm = store.row("SELECT * FROM hospital_admissions WHERE"
                        " visit_id = ?", (visit["visit_id"],))
        self.assertIsNotNone(adm)
        self.assertEqual(adm["referred_off_district"], 1)
        self.assertEqual(adm["transfer_days"], 2)


class TestBudgets(unittest.TestCase):
    def test_procurement_ledgered_and_capped(self):
        store, d, doctor = _staffed_world()
        patient = citizen(store, age=30, first="Patient")
        health.start_condition(store, d, rng(), patient, "unwell",
                               "weather_exposure", 5, 5 * 1440,
                               facility_id=RUP)
        care.process_daily_queue(store, d, rng(), 5, 5 * 1440)
        out = care.monthly_pass(store, d, 1, 30 * 1440)
        self.assertIn(RUP, out)
        budget = store.row("SELECT * FROM healthcare_budgets WHERE"
                           " facility_id = ? AND month_index = 1",
                           (RUP,))
        self.assertIsNotNone(budget)
        self.assertLessEqual(budget["procurement_ncr"],
                             budget["allocated_ncr"])
        self.assertGreater(budget["procurement_ncr"], 0)
        rows = store.rows("SELECT * FROM economy_ledger WHERE"
                          " reason_code = 'medical_procurement'")
        self.assertTrue(rows)
        for r in rows:
            self.assertEqual(r["from_character_id"], "SYS-CITY")
            self.assertEqual(r["to_character_id"], "SYS-MARKET")
            self.assertEqual(r["event_ref"], budget["budget_id"])
            self.assertTrue(r["transfer_key"].startswith("medproc:"))
        self.assertEqual(store.ledger_sum_check(), [])
        # Stock was topped back up toward target.
        stock = store.row("SELECT quantity FROM medical_inventory"
                          " WHERE facility_id = ? AND item_id ="
                          " 'sim_fever_course'", (RUP,))
        self.assertEqual(stock["quantity"], 60)


class TestLifeStageCare(unittest.TestCase):
    def test_birth_care_from_real_childbirth_event(self):
        store, d, doctor = _staffed_world()
        mother = citizen(store, age=28, first="Mother")
        from tools.sim import memory as memory_mod
        memory_mod.log_life_event(store, mother, "childbirth",
                                  20 * 1440, details={})
        registered = care.register_life_stage_care(
            store, d, 1, 30 * 1440)
        self.assertEqual(registered, 1)
        visit = store.row("SELECT * FROM patient_visits WHERE"
                          " character_id = ? AND visit_type ="
                          " 'birth_care'", (mother,))
        self.assertIsNotNone(visit)
        before = store.row("SELECT quantity FROM medical_inventory"
                           " WHERE facility_id = ? AND item_id ="
                           " 'sim_maternal_kit'", (RUP,))["quantity"]
        care.process_daily_queue(store, d, rng(), 30, 30 * 1440)
        visit = store.row("SELECT * FROM patient_visits WHERE"
                          " visit_id = ?", (visit["visit_id"],))
        self.assertEqual(visit["stage"], "closed")
        after = store.row("SELECT quantity FROM medical_inventory"
                          " WHERE facility_id = ? AND item_id ="
                          " 'sim_maternal_kit'", (RUP,))["quantity"]
        self.assertEqual(after, before - 1)


if __name__ == "__main__":
    unittest.main()
