"""Session 05 acceptance — the government layer in a real
long-running world: two full election cycles inside 13 months,
an annual budget, monthly audits, restart persistence of every
government record, determinism, and an enacted law measurably
changing what a purchase pays in tax."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))

from tools.sim import finance, government as gov, justice  # noqa: E402
from tools.sim.engine import Simulation  # noqa: E402


def make_sim(population, days, seed="s05-acceptance"):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    sim = Simulation(path, seed=seed)
    sim.generate_population(population)
    if days:
        sim.run_days(days)
    return sim, path


class TestSession05Acceptance(unittest.TestCase):
    def test_long_run_two_elections_budget_audits(self):
        sim, path = make_sim(80, 390)
        try:
            store = sim.store
            s = sim.summary()
            g = s["government"]
            # Two elections: months 1 and 13, each forming a
            # government from real ballots.
            elections = store.rows("SELECT * FROM elections"
                                   " ORDER BY month_index")
            self.assertEqual(len(elections), 2)
            for e in elections:
                self.assertEqual(e["status"], "formed")
                self.assertGreater(e["turnout"], 0)
                ballots = store.row(
                    "SELECT COUNT(*) AS n FROM ballots WHERE"
                    " election_id = ?", (e["election_id"],))["n"]
                self.assertEqual(ballots, e["turnout"])
            self.assertIsNotNone(g["governing_party"])
            self.assertIsNotNone(g["mean_approval"])
            # The annual budget closed the year with an approval.
            budgets = store.rows("SELECT * FROM budgets")
            self.assertGreaterEqual(len(budgets), 1)
            self.assertEqual(budgets[0]["status"], "approved")
            # Monthly accountability: an audit per month, all
            # clean — the books reconcile exactly.
            audits = store.rows("SELECT * FROM audits")
            self.assertGreaterEqual(len(audits), 12)
            self.assertTrue(all(a["discrepancy_count"] == 0
                                for a in audits))
            self.assertEqual(finance.verify_conservation(store),
                             [])
            self.assertEqual(store.ledger_sum_check(), [])
            self.assertEqual(s["ledger_mismatches"], 0)
            # The observatory reads the same records.
            from tools.sim import govview
            view = govview.overview(store, sim.data)
            self.assertEqual(view["country"]["country_id"],
                             "bangladesh")
            self.assertEqual(view["integrity_index"], 100)
        finally:
            sim.close()
            os.remove(path)

    def test_restart_persistence_of_government_records(self):
        whole, path1 = make_sim(80, 390)
        try:
            expected = whole.summary()
            whole.close()
            split, path2 = make_sim(80, 200)
            split.close()
            resumed = Simulation(path2, seed="s05-acceptance")
            resumed.run_days(190)
            try:
                self.assertEqual(resumed.summary(), expected)
                elections = resumed.store.row(
                    "SELECT COUNT(*) AS n FROM elections")["n"]
                self.assertEqual(elections, 2)
            finally:
                resumed.close()
                os.remove(path2)
        finally:
            os.remove(path1)

    def test_deterministic_government(self):
        a, pa = make_sim(60, 90, seed="s05-determinism")
        b, pb = make_sim(60, 90, seed="s05-determinism")
        try:
            self.assertEqual(a.summary(), b.summary())
        finally:
            a.close()
            b.close()
            os.remove(pa)
            os.remove(pb)

    def test_enacted_sales_tax_law_changes_purchases(self):
        sim, path = make_sim(60, 35)
        try:
            store, data = sim.store, sim.data
            pm = gov.office_holder(store, "prime_minister",
                                   "GOV-PM")["holder_character_id"]
            buyer = store.row(
                "SELECT character_id FROM characters WHERE"
                " is_system = 0 AND died_at_game_minutes IS NULL"
                " ORDER BY character_id LIMIT 1")["character_id"]
            store.transfer("SYS-MARKET", buyer, 500000,
                           "seed_grant", store.world()[
                               "game_minutes"],
                           note="test funds",
                           transfer_key="test:buyer-funds")
            gm = store.world()["game_minutes"]

            def tax_paid():
                before = store.balance("SYS-CITY")
                sim._pay_purchase(buyer, 105000, gm, "test purchase")
                return store.balance("SYS-CITY") - before

            # Configured SIM MODEL rate (5%): tax share of a
            # 105,000 purchase is exactly 5,000.
            self.assertEqual(tax_paid(), 5000)
            lid = justice.propose_law(store, data, "sales_tax", 8,
                                      pm, gm)
            result = justice.vote_law(store, data, lid, gm)
            self.assertTrue(result["enacted"])
            # The law takes effect next month; run into it.
            sim.run_days(60)
            gm2 = store.world()["game_minutes"]
            # The buyer has lived (and spent) for two months —
            # top them back up so the purchase is covered in
            # full and the tax share is exact.
            shortfall = 300000 - store.balance(buyer)
            if shortfall > 0:
                store.transfer("SYS-MARKET", buyer, shortfall,
                               "seed_grant", gm2,
                               note="test top-up",
                               transfer_key="test:buyer-topup")
            before = store.balance("SYS-CITY")
            sim._pay_purchase(buyer, 105000, gm2, "test purchase 2")
            self.assertEqual(store.balance("SYS-CITY") - before,
                             7778)  # 8% share, rounded
        finally:
            sim.close()
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
