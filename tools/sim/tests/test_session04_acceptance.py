"""Session 04 acceptance — the economy layer end to end.

A full generated world runs a quarter with the economy live:
the books must balance exactly, businesses must operate from
real premises and real accounts, the bank must reconcile,
indicators and government finance must be written from records,
and the whole run must be deterministic and restart-safe — the
same guarantees Sessions 01-03 acceptance pinned, extended to
the economy.
"""
import os
import tempfile
import unittest

from tools.sim import banking as banking_mod
from tools.sim import finance as finance_mod
from tools.sim.engine import Simulation


def _tmp_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


class TestSession04Acceptance(unittest.TestCase):
    def test_full_economy_quarter(self):
        path = _tmp_path()
        sim = Simulation(path, seed="s04-acceptance")
        try:
            sim.generate_population(100)
            sim.run_days(90)
            store = sim.store
            summary = sim.summary()
            # The traceability spine: zero mismatches, always.
            self.assertEqual(summary["ledger_mismatches"], 0)
            self.assertEqual(finance_mod.verify_conservation(store),
                             [])
            self.assertEqual(
                banking_mod.account_reconciliation(store), [])
            # Businesses operate, the bank holds reserves, the
            # labour market and price layer are alive.
            self.assertGreater(summary["businesses_active"], 40)
            self.assertGreater(summary["bank_reserves_ncr"], 0)
            self.assertIsNotNone(summary["price_index"])
            self.assertTrue(50 <= summary["price_index"] <= 200)
            # Monthly records exist for the whole quarter.
            months = {r["month_index"] for r in store.rows(
                "SELECT DISTINCT month_index FROM"
                " economic_indicators WHERE scope = 'national'")}
            self.assertEqual(months, {1, 2, 3})
            self.assertGreaterEqual(store.row(
                "SELECT COUNT(*) AS n FROM government_finance")
                ["n"], 6)
            self.assertGreater(store.row(
                "SELECT COUNT(*) AS n FROM business_monthly")["n"],
                100)
            self.assertGreater(store.row(
                "SELECT COUNT(*) AS n FROM household_consumption")
                ["n"], 100)
            # Households actually ate: food coverage is real.
            food = store.row(
                "SELECT COALESCE(SUM(units),0) AS u,"
                " COALESCE(SUM(unmet_units),0) AS un FROM"
                " household_consumption WHERE good_id ="
                " 'food_basket'")
            self.assertGreater(food["u"], 0)
            coverage = food["u"] / (food["u"] + food["un"]) \
                if food["u"] + food["un"] else 0
            self.assertGreater(coverage, 0.5)
            ind = summary["latest_indicators"]
            self.assertIsNotNone(ind)
            self.assertGreater(ind["gdp_ncr"], 0)
        finally:
            sim.close()
            os.remove(path)

    def test_determinism_with_economy(self):
        summaries = []
        for _ in range(2):
            path = _tmp_path()
            sim = Simulation(path, seed="s04-determinism")
            try:
                sim.generate_population(40)
                sim.run_days(35)
                summaries.append(sim.summary())
            finally:
                sim.close()
                os.remove(path)
        self.assertEqual(summaries[0], summaries[1])

    def test_restart_persistence_with_economy(self):
        path_a, path_b = _tmp_path(), _tmp_path()
        sim = Simulation(path_a, seed="s04-restart")
        try:
            sim.generate_population(40)
            sim.run_days(90)
            whole = sim.summary()
        finally:
            sim.close()
        sim = Simulation(path_b, seed="s04-restart")
        try:
            sim.generate_population(40)
            sim.run_days(45)
        finally:
            sim.close()
        sim = Simulation(path_b, seed="s04-restart")
        try:
            sim.run_days(45)
            split = sim.summary()
        finally:
            sim.close()
            os.remove(path_a)
            os.remove(path_b)
        self.assertEqual(whole, split)


if __name__ == "__main__":
    unittest.main()
