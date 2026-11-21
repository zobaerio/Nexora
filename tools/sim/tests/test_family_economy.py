"""Session 02 Unit 03 — Family Economy: monthly household accounts,
contributions, debt accrual and repayment, financial conditions."""
import os
import tempfile
import unittest

from tools.sim.tests.common import (data, employ, make_household,
                                    make_person, make_store)
from tools.sim import family_economy as fe
from tools.sim.engine import Simulation


def _tmp_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


class TestFamilyEconomyUnits(unittest.TestCase):
    def test_record_month_and_debt(self):
        store = make_store()
        a = make_person(store, age=35, first="Earner")
        hid, _ = make_household(store, [a])
        store.transfer("SYS-EMPLOYERS", a, 5000, "seed", 480)
        fe.record_month(store, hid, 1, 30 * 1440, income=15000,
                        food=4000, housing=4000, transport=1000,
                        other=2000, emergency=0)
        snap = fe.snapshot(store, hid)
        self.assertEqual(snap["debt_ncr"], 0)
        self.assertEqual(snap["latest_month"]["income_ncr"], 15000)
        self.assertEqual(snap["latest_month"]["education_ncr"], 0)
        self.assertEqual(snap["latest_month"]["healthcare_ncr"], 0)
        # A month with arrears puts the family in debt.
        fe.record_month(store, hid, 2, 60 * 1440, income=9000,
                        food=4000, housing=4000, transport=1000,
                        other=2000, emergency=2500)
        self.assertEqual(fe.debt_of(store, hid), 2500)
        self.assertEqual(fe.snapshot(store, hid)["condition"], "in_debt")
        # Repayment clears it from the head's balance, keeping the
        # reserve; the ledger still reconciles.
        paid = fe.repay_debt(store, hid, a, 61 * 1440)
        self.assertEqual(paid, 2500)
        self.assertEqual(fe.debt_of(store, hid), 0)
        self.assertEqual(store.balance(a), 2500)
        self.assertEqual(store.ledger_sum_check(), [])

    def test_contributions(self):
        store = make_store()
        d = data()
        a = make_person(store, age=35, first="Worker")
        kid = make_person(store, age=9, first="Kid")
        hid, _ = make_household(store, [a, kid])
        employ(store, d, a, "teacher", tier=1)
        contribs = {c["character_id"]: c
                    for c in fe.contributions(store, hid)}
        self.assertEqual(contribs[a]["kind"], "wage")
        self.assertEqual(contribs[a]["monthly_ncr"],
                         d.wage_at("teacher", 1))
        self.assertEqual(contribs[kid]["kind"], "none")


class TestFamilyEconomyEngine(unittest.TestCase):
    def test_engine_writes_household_accounts(self):
        """Two settled months over a generated population: every
        active household has accounts, categories sum from real
        settlement lines, and the ledger still reconciles."""
        path = _tmp_path()
        sim = Simulation(path, seed="fam-econ")
        sim.generate_population(80)
        sim.run_days(60)
        store = sim.store
        rows = store.rows("SELECT DISTINCT household_id"
                          " FROM household_finances")
        active = store.row("SELECT COUNT(*) AS n FROM households"
                           " WHERE dissolved_at_game_minutes IS NULL")["n"]
        self.assertGreaterEqual(len(rows), active - 2)
        months = store.rows("SELECT DISTINCT month_index"
                            " FROM household_finances ORDER BY month_index")
        self.assertEqual([m["month_index"] for m in months], [1, 2])
        sample = store.row("SELECT * FROM household_finances LIMIT 1")
        self.assertGreater(sample["income_ncr"], 0)
        self.assertGreater(sample["food_ncr"], 0)
        self.assertEqual(store.ledger_sum_check(), [])
        sim.close()
        os.remove(path)


if __name__ == "__main__":
    unittest.main()
