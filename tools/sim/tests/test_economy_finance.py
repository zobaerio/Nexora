"""Session 04 Units 01-02 + financial integrity.

The owner's special order for this session: every unit of money
fully traceable. These tests pin that contract — conservation,
idempotency, atomicity, ledger immutability, reconciliation —
plus the foundation views (regions, currency, per-person
financial profiles) and the guarantee that hand-built worlds
without the economy layer are untouched by it.
"""
import os
import tempfile
import unittest

from tools.sim import business as business_mod
from tools.sim import finance as finance_mod
from tools.sim import labour as labour_mod
from tools.sim.engine import Simulation

from .common import make_store, rng


def _tmp_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


class TestEconomyFoundation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = _tmp_path()
        cls.sim = Simulation(cls.path, seed="s04-finance")
        cls.sim.generate_population(60)
        cls.sim.run_days(35)
        cls.store = cls.sim.store
        cls.data = cls.sim.data

    @classmethod
    def tearDownClass(cls):
        cls.sim.close()
        os.remove(cls.path)

    def test_setup_is_flagged_and_idempotent(self):
        self.assertTrue(business_mod.is_setup(self.store))
        again = business_mod.setup_economy(
            self.store, self.data, self.sim.rng)
        self.assertTrue(again.get("already_setup"))
        n = self.store.row("SELECT COUNT(*) AS n FROM businesses")["n"]
        self.assertGreater(n, 30)

    def test_regions_one_national_economy_two_cities(self):
        view = finance_mod.regions(self.store, self.data)
        self.assertEqual(view["currency"]["code"], "NCr")
        self.assertEqual(len(view["regions"]), 2)
        city_ids = {r["city_id"] for r in view["regions"]}
        self.assertEqual(city_ids, {"rupsha_city", "shibnagar_town"})
        total_pop = sum(r["population"] for r in view["regions"])
        alive = self.store.row(
            "SELECT COUNT(*) AS n FROM characters WHERE"
            " died_at_game_minutes IS NULL AND is_system = 0")["n"]
        self.assertEqual(total_pop, alive)

    def test_event_history_is_chronological_and_typed(self):
        events = finance_mod.economic_event_history(self.store,
                                                    limit=25)
        self.assertTrue(events)
        minutes = [e["game_minutes"] for e in events]
        self.assertEqual(minutes, sorted(minutes, reverse=True))
        for e in events:
            self.assertIn("event_type", e)
            self.assertIn("details", e)

    def test_financial_profile_recomputes_from_ledger(self):
        emp = self.store.row(
            "SELECT character_id FROM employments WHERE"
            " ended_at_game_minutes IS NULL LIMIT 1")
        cid = emp["character_id"]
        profile = finance_mod.financial_profile(
            self.store, self.data, cid)
        self.assertEqual(profile["character_id"], cid)
        self.assertEqual(profile["balance_ncr"],
                         self.store.balance(cid))
        self.assertGreater(profile["income_total_ncr"], 0)
        # Net worth identity, exactly as documented in finance.py:
        # cash + assets - debt, all recomputed from the ledger.
        expect = profile["balance_ncr"] \
            + profile["assets"]["total_ncr"] \
            - profile["debt"]["total_ncr"]
        self.assertEqual(profile["net_worth_ncr"], expect)
        self.assertEqual(
            profile["purchasing_power_ncr"],
            profile["balance_ncr"]
            + profile["assets"]["bank_deposits_ncr"]
            - profile["obligations_monthly_ncr"])
        history = finance_mod.transaction_history(self.store, cid)
        self.assertTrue(history)
        for row in history:
            self.assertTrue(row["from_character_id"] == cid
                            or row["to_character_id"] == cid)

    def test_conservation_and_reconciliation_are_clean(self):
        self.assertEqual(self.store.ledger_sum_check(), [])
        self.assertEqual(finance_mod.verify_conservation(self.store),
                         [])

    def test_transfer_key_idempotency(self):
        cid = self.store.row(
            "SELECT character_id FROM characters WHERE"
            " died_at_game_minutes IS NULL LIMIT 1")["character_id"]
        before = self.store.balance(cid)
        rows_before = self.store.row(
            "SELECT COUNT(*) AS n FROM economy_ledger")["n"]
        first = self.store.transfer(
            "SYS-MARKET", cid, 123, "grant", 10 ** 9,
            transfer_key="test:idem:1")
        second = self.store.transfer(
            "SYS-MARKET", cid, 123, "grant", 10 ** 9,
            transfer_key="test:idem:1")
        self.assertEqual(first, second)
        self.assertEqual(self.store.balance(cid), before + 123)
        self.assertEqual(self.store.row(
            "SELECT COUNT(*) AS n FROM economy_ledger")["n"],
            rows_before + 1)

    def test_failed_transfer_is_atomic(self):
        cid = self.store.row(
            "SELECT character_id FROM characters WHERE"
            " died_at_game_minutes IS NULL AND is_system = 0"
            " LIMIT 1")["character_id"]
        rows_before = self.store.row(
            "SELECT COUNT(*) AS n FROM economy_ledger")["n"]
        balance_before = self.store.balance(cid)
        with self.assertRaises(ValueError):
            self.store.transfer(cid, "SYS-MARKET", 10 ** 12,
                                "purchase", 10 ** 9)
        self.assertEqual(self.store.balance(cid), balance_before)
        self.assertEqual(self.store.row(
            "SELECT COUNT(*) AS n FROM economy_ledger")["n"],
            rows_before)

    def test_ledger_is_append_only(self):
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.execute(
                "UPDATE economy_ledger SET amount = 1 WHERE"
                " ledger_id = (SELECT MIN(ledger_id) FROM"
                " economy_ledger)")
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.execute(
                "DELETE FROM economy_ledger WHERE ledger_id ="
                " (SELECT MIN(ledger_id) FROM economy_ledger)")

    def test_business_balances_reconcile_with_ledger(self):
        for b in self.store.rows(
                "SELECT business_id FROM businesses LIMIT 8"):
            bid = b["business_id"]
            inn = self.store.row(
                "SELECT COALESCE(SUM(amount),0) AS s FROM"
                " economy_ledger WHERE to_business_id = ?",
                (bid,))["s"]
            out = self.store.row(
                "SELECT COALESCE(SUM(amount),0) AS s FROM"
                " economy_ledger WHERE from_business_id = ?",
                (bid,))["s"]
            self.assertEqual(self.store.business_balance(bid),
                             inn - out)


class TestHandBuiltWorldUntouched(unittest.TestCase):
    """The Session 01-03 contract: worlds that never ran the
    economy setup see none of it — no businesses, no vacancies,
    no bank, and the labour pass is a no-op."""

    def test_no_setup_no_economy(self):
        store = make_store()
        try:
            self.assertFalse(business_mod.is_setup(store))
            self.assertEqual(store.rows("SELECT * FROM businesses"),
                             [])
            result = labour_mod.monthly_pass(
                store, _Data(), rng(), 1, 43200)
            self.assertEqual(store.rows("SELECT * FROM vacancies"),
                             [])
            self.assertEqual(store.balance("SYS-BANK"), 0)
            self.assertIsInstance(result, dict)
        finally:
            store.close()
            os.remove(store.path)


def _Data():
    from .common import data
    return data()


if __name__ == "__main__":
    unittest.main()
