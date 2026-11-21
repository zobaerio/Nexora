"""Session 03 Unit 09 — City Services & Municipal Budgets."""
import os
import tempfile
import unittest

from tools.sim import cities as cities_mod
from tools.sim import services as services_mod
from tools.sim.engine import Simulation
from tools.sim.tests.common import data, make_person, make_store, rng


def _tmp_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


class TestServicesEngine(unittest.TestCase):
    def test_two_months_of_budgets_and_levels(self):
        path = _tmp_path()
        sim = Simulation(path, seed="svc-test")
        sim.generate_population(100)
        sim.run_days(62)
        summary = sim.summary()
        self.assertEqual(summary["ledger_mismatches"], 0)
        budgets = sim.store.rows("SELECT * FROM municipal_budgets")
        self.assertEqual(len(budgets), 4)  # 2 cities x 2 months
        rupsha_m1 = [b for b in budgets
                     if b["city_id"] == "rupsha_city"
                     and b["month_index"] == 1][0]
        # Wage taxes are measured ledger revenue, not an invention.
        self.assertGreater(rupsha_m1["revenue_tax_ncr"], 0)
        self.assertGreater(rupsha_m1["revenue_rent_ncr"], 0)
        # municipal_services is the current-levels table (one row
        # per city+service, month stamped on the row); the monthly
        # history lives in municipal_budgets above.
        levels = sim.store.rows("SELECT * FROM municipal_services")
        self.assertEqual(len(levels), 8 * 2)
        for row in levels:
            self.assertEqual(row["month_index"], 2)
            self.assertGreaterEqual(row["level"], 0)
            self.assertLessEqual(row["level"], 100)
        sim.close()
        os.remove(path)


class TestServicesUnits(unittest.TestCase):
    def setUp(self):
        self.store = make_store()
        self.d = data()
        cities_mod.setup_cities(self.store, self.d, rng())

    def tearDown(self):
        self.store.close()

    def test_property_tax_at_the_designed_rate(self):
        owner = make_person(self.store, first="Tax", last="Payer")
        self.store.transfer("SYS-EMPLOYERS", owner, 100000, "seed",
                            480)
        self.store.insert(
            "properties", property_id="PR-TAX1",
            property_type="house", district_id="d1_midtown",
            address_label="Tax test house", tier=2, status="owned",
            market_value=1200000, building_ref=None, unit_index=0,
            owner_character_id=owner)
        rate = self.d.prices["tax"][
            "property_annual_percent_of_value"]
        expected = round(1200000 * rate / 100 / 12)
        self.assertGreater(expected, 0)
        collected = services_mod._assess_property_tax(
            self.store, self.d, 480)
        self.assertEqual(collected, {"rupsha_city": expected})
        self.assertEqual(self.store.balance("SYS-CITY"), expected)
        self.assertEqual(self.store.balance(owner), 100000 - expected)

    def test_spend_never_overdraws_the_city(self):
        self.store.transfer("SYS-EMPLOYERS", "SYS-CITY", 300, "seed",
                            480)
        paid = services_mod._spend(self.store, 1000, "test spend",
                                   480)
        self.assertEqual(paid, 300)
        self.assertEqual(self.store.balance("SYS-CITY"), 0)
        self.assertEqual(services_mod._spend(
            self.store, 1000, "test spend", 480), 0)


if __name__ == "__main__":
    unittest.main()
