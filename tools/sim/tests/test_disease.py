"""Session 06 — Disease simulation (simplified, labelled):
transmission over measured contacts, recovery + immunity,
vaccination, surveillance-triggered campaigns, scenario seeding."""
import unittest

from tools.sim import disease
from tools.sim import healthcare as care
from tools.sim.tests.common import make_household, rng
from tools.sim.tests.humandevcommon import citizen, hd_world

FLU = "sim_seasonal_flu"
RUP = "HEALTH-RUPSHA-CLINIC"


def _flu_config(d, **overrides):
    flu = d.education_health_config["disease"]["diseases"][0]
    flu.update(overrides)
    return flu


class TestInfection(unittest.TestCase):
    def test_infect_records_and_opens_condition(self):
        store, d = hd_world()
        cid = citizen(store, age=30)
        rid = disease.infect(store, d, rng(), cid, FLU, "transmission",
                             5, 5 * 1440)
        self.assertIsNotNone(rid)
        rec = store.row("SELECT * FROM disease_records WHERE"
                        " record_id = ?", (rid,))
        self.assertEqual(rec["status"], "infectious")
        self.assertEqual(rec["city_id"], "rupsha_city")
        self.assertGreater(rec["immune_until_day"],
                           rec["recovered_day"])
        cond = store.row("SELECT * FROM health_conditions WHERE"
                         " character_id = ?", (cid,))
        self.assertEqual(cond["cause"], "disease_transmission")
        # Already infectious: no second record.
        self.assertIsNone(disease.infect(store, d, rng(), cid, FLU,
                                         "transmission", 5, 5 * 1440))

    def test_recovery_grants_immunity_window(self):
        store, d = hd_world()
        cid = citizen(store, age=30)
        disease.infect(store, d, rng(), cid, FLU, "transmission",
                       5, 5 * 1440)
        rec = store.row("SELECT * FROM disease_records WHERE"
                        " character_id = ?", (cid,))
        disease.daily_transmission(store, d, rng(),
                                   rec["recovered_day"] + 1,
                                   (rec["recovered_day"] + 1) * 1440)
        rec = store.row("SELECT * FROM disease_records WHERE"
                        " character_id = ?", (cid,))
        self.assertEqual(rec["status"], "recovered")
        self.assertTrue(disease.is_immune(store, d, rng(), cid, FLU,
                                          rec["recovered_day"] + 2))
        self.assertIsNone(disease.infect(
            store, d, rng(), cid, FLU, "transmission",
            rec["recovered_day"] + 2,
            (rec["recovered_day"] + 2) * 1440))


class TestTransmission(unittest.TestCase):
    def test_household_spread_at_full_transmission(self):
        store, d = hd_world()
        _flu_config(d, transmission_per_contact_day=1.0,
                    endemic_index_chance_per_day=0.0)
        head = citizen(store, age=35, first="Head")
        hid = store.row("SELECT household_id FROM characters WHERE"
                        " character_id = ?", (head,))["household_id"]
        members = [citizen(store, age=30, first=f"M{i}",
                           household=hid) for i in range(3)]
        disease.infect(store, d, rng(), head, FLU, "transmission",
                       5, 5 * 1440)
        new = disease.daily_transmission(store, d, rng(), 6, 6 * 1440)
        self.assertEqual(new, 3)
        for m in members:
            rec = store.row("SELECT * FROM disease_records WHERE"
                            " character_id = ?", (m,))
            self.assertIsNotNone(rec)
            self.assertEqual(rec["source"], "transmission")

    def test_no_spread_at_zero_transmission(self):
        store, d = hd_world()
        _flu_config(d, transmission_per_contact_day=0.0,
                    endemic_index_chance_per_day=0.0)
        head = citizen(store, age=35, first="Head")
        hid = store.row("SELECT household_id FROM characters WHERE"
                        " character_id = ?", (head,))["household_id"]
        citizen(store, age=30, household=hid)
        disease.infect(store, d, rng(), head, FLU, "transmission",
                       5, 5 * 1440)
        new = disease.daily_transmission(store, d, rng(), 6, 6 * 1440)
        self.assertEqual(new, 0)

    def test_scenario_seeds_index_case(self):
        store, d = hd_world()
        _flu_config(d, endemic_index_chance_per_day=0.0)
        d.education_health_config["disease"]["scenarios"] = [
            {"day_index": 7, "disease_id": FLU,
             "city_id": "rupsha_city", "index_cases": 1}]
        citizen(store, age=30)
        new = disease.daily_transmission(store, d, rng(), 7, 7 * 1440)
        self.assertEqual(new, 1)
        rec = store.row("SELECT * FROM disease_records")
        self.assertEqual(rec["source"], "scenario")


class TestVaccinationAndCampaign(unittest.TestCase):
    def test_vaccination_recorded_and_effective(self):
        store, d = hd_world()
        _flu_config(d, vaccine_effectiveness=1.0)
        cid = citizen(store, age=30)
        rid = disease.vaccinate(store, cid, FLU, RUP, 5, 5 * 1440)
        self.assertIsNotNone(rid)
        self.assertTrue(disease.is_immune(store, d, rng(), cid, FLU, 6))
        # Idempotent per day.
        self.assertIsNone(disease.vaccinate(store, cid, FLU, RUP, 5,
                                            5 * 1440))

    def test_campaign_fires_over_threshold(self):
        store, d = hd_world()
        _flu_config(d, endemic_index_chance_per_day=0.0)
        people = [citizen(store, age=30, first=f"C{i}")
                  for i in range(12)]
        # 1 active case in 12 residents = 8.3/100 >= 4.0 threshold.
        disease.infect(store, d, rng(), people[0], FLU, "transmission",
                       5, 5 * 1440)
        care.monthly_pass(store, d, 1, 30 * 1440)  # budget rows exist
        out = disease.monthly_pass(store, d, rng(), 1, 30 * 1440)
        self.assertIn("rupsha_city", out)
        given = out["rupsha_city"]["vaccinations_given"]
        self.assertGreater(given, 0)
        rows = store.rows("SELECT * FROM vaccination_records")
        self.assertEqual(len(rows), given)
        # Campaign cost accounted on the facility's budget row.
        budget = store.row("SELECT * FROM healthcare_budgets WHERE"
                           " facility_id = ? AND month_index = 1",
                           (RUP,))
        self.assertEqual(budget["campaign_ncr"], given * 150)

    def test_no_campaign_below_threshold(self):
        store, d = hd_world()
        _flu_config(d, endemic_index_chance_per_day=0.0)
        for i in range(40):
            citizen(store, age=30, first=f"C{i}")
        out = disease.monthly_pass(store, d, rng(), 1, 30 * 1440)
        self.assertEqual(out, {})


if __name__ == "__main__":
    unittest.main()
