"""Session 04 Units 10-13 — Government Finance, Indicators,
Crises, Trade."""
import json
import os
import tempfile
import unittest

from tools.sim import crises as crises_mod
from tools.sim import govfinance as govfinance_mod
from tools.sim import indicators as indicators_mod
from tools.sim import market as market_mod
from tools.sim import trade as trade_mod
from tools.sim.engine import Simulation

from .common import rng


def _tmp_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


class TestGovIndicatorsTrade(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = _tmp_path()
        cls.sim = Simulation(cls.path, seed="s04-gov")
        cls.sim.generate_population(60)
        cls.sim.run_days(65)
        cls.store = cls.sim.store
        cls.data = cls.sim.data

    @classmethod
    def tearDownClass(cls):
        cls.sim.close()
        os.remove(cls.path)

    def test_tax_rules_reference_design_rates(self):
        view = govfinance_mod.tax_rules_view(self.data)
        self.assertIn("prices.json", json.dumps(view))
        rates = self.data.economy_config["tax_rules"]
        self.assertEqual(view["sales_tax"]["percent"],
                         rates["sales_tax_percent"])
        self.assertEqual(view["import_tariff"]["percent"],
                         rates["import_tariff_percent"])
        # Design taxes are referenced, never copied: the view
        # carries prices.json's own bracket table.
        self.assertEqual(
            view["income_tax"]["brackets"],
            self.data.prices["tax"]["income_monthly_brackets"])

    def test_government_finance_rows_per_city_per_month(self):
        rows = self.store.rows("SELECT * FROM government_finance")
        self.assertTrue(rows)
        keys = {(r["city_id"], r["month_index"]) for r in rows}
        months = {m for _c, m in keys}
        self.assertGreaterEqual(len(months), 2)
        revenue_cols = [c for c in rows[0].keys()
                        if c.startswith("revenue_")]
        self.assertTrue(revenue_cols)
        national_total = 0
        for r in rows:
            national_total += sum(r[c] for c in revenue_cols)
            self.assertGreaterEqual(r["public_debt_ncr"], 0)
        self.assertGreater(national_total, 0)

    def test_govfinance_snapshot_writes_no_ledger_rows(self):
        before = self.store.row(
            "SELECT COUNT(*) AS n FROM economy_ledger")["n"]
        govfinance_mod.monthly_snapshot(self.store, self.data, 42,
                                        10 ** 8)
        after = self.store.row(
            "SELECT COUNT(*) AS n FROM economy_ledger")["n"]
        self.assertEqual(before, after)

    def test_sales_tax_reaches_the_city(self):
        rows = self.store.rows(
            "SELECT * FROM economy_ledger WHERE reason_code ="
            " 'sales_tax'")
        self.assertTrue(rows)
        for r in rows[:5]:
            self.assertEqual(r["to_character_id"], "SYS-CITY")

    def test_indicators_documented_and_in_range(self):
        self.assertIn("gdp", indicators_mod.METHODOLOGY)
        self.assertIn("unemployment", indicators_mod.METHODOLOGY)
        latest = indicators_mod.latest(self.store, "national")
        self.assertIsNotNone(latest)
        m = latest["metrics"]
        self.assertGreater(m["gdp_ncr"], 0)
        self.assertGreater(m["gdp_per_capita_ncr"], 0)
        self.assertTrue(0.0 <= m["unemployment_rate"] <= 1.0)
        self.assertTrue(0.0 <= m["poverty_rate"] <= 1.0)
        self.assertTrue(0.0 <= m["wealth_gini"] <= 1.0)
        # The inflation line is the market price index, recomputed.
        self.assertAlmostEqual(
            m["price_index"],
            market_mod.price_index(self.store, self.data), places=1)
        scopes = {r["scope"] for r in self.store.rows(
            "SELECT DISTINCT scope FROM economic_indicators")}
        self.assertEqual(scopes, {"national", "rupsha_city",
                                  "shibnagar_town"})

    def test_trade_settlement_moves_goods_and_collects_tariff(self):
        # A measured flow, constructed as regional.monthly_flows
        # writes it: manufactured goods Rupsha -> Shibnagar.
        maker = self.store.row(
            "SELECT b.business_id FROM businesses b JOIN"
            " properties p ON p.property_id = b.property_id WHERE"
            " b.category = 'manufacturing' AND p.district_id NOT"
            " LIKE 'c2%' AND b.closed_at_game_minutes IS NULL"
            " LIMIT 1")
        market_mod.adjust_inventory(
            self.store, maker["business_id"], "manufactured_goods",
            100, "test_stock", 10 ** 8)
        fid = self.store.next_id("TF", "trade_flows", "flow_id")
        self.store.insert(
            "trade_flows", flow_id=fid, month_index=88,
            from_city_id="rupsha_city", to_city_id="shibnagar_town",
            goods="manufactured_goods", amount_ncr=30000,
            game_minutes=10 ** 8)
        city_before = self.store.balance("SYS-CITY")
        result = trade_mod.settle_trade(self.store, self.data, 88,
                                        10 ** 8)
        self.assertTrue(result)
        tariff = self.store.row(
            "SELECT amount FROM economy_ledger WHERE reason_code"
            " = 'tariff' AND transfer_key = ?", (f"tariff:{fid}",))
        self.assertIsNotNone(tariff)
        rate = self.data.economy_config["tax_rules"][
            "import_tariff_percent"] / 100
        self.assertEqual(tariff["amount"], round(30000 * rate))
        self.assertEqual(self.store.balance("SYS-CITY"),
                         city_before + tariff["amount"])
        moved = self.store.row(
            "SELECT COALESCE(SUM(-delta),0) AS s FROM"
            " inventory_movements WHERE kind = 'trade_out' AND"
            " business_id = ?", (maker["business_id"],))["s"]
        self.assertGreater(moved, 0)
        arrived = self.store.row(
            "SELECT COALESCE(SUM(delta),0) AS s FROM"
            " inventory_movements WHERE kind = 'trade_in'")["s"]
        self.assertGreater(arrived, 0)
        # Idempotent: settling the same month again moves nothing.
        trade_mod.settle_trade(self.store, self.data, 88, 10 ** 8)
        moved2 = self.store.row(
            "SELECT COALESCE(SUM(-delta),0) AS s FROM"
            " inventory_movements WHERE kind = 'trade_out' AND"
            " business_id = ?", (maker["business_id"],))["s"]
        self.assertEqual(moved2, moved)


class TestCrisisDetection(unittest.TestCase):
    def test_unemployment_spike_opens_a_measured_crisis(self):
        path = _tmp_path()
        sim = Simulation(path, seed="s04-crisis")
        try:
            sim.generate_population(60)
            store, data = sim.store, sim.data
            # Mass layoff: every employment ends today. The next
            # indicator snapshot must measure ~total unemployment
            # and detection must open the crisis from that fact.
            store.execute(
                "UPDATE employments SET ended_at_game_minutes ="
                " 1000 WHERE ended_at_game_minutes IS NULL")
            indicators_mod.snapshot_month(store, data, 1, 43200)
            snap = indicators_mod.latest(store, "national")
            self.assertGreater(snap["metrics"]["unemployment_rate"],
                               0.9)
            opened = crises_mod.detect(store, data, 1, 43200)
            types = {c["crisis_type"] if isinstance(c, dict)
                     else c for c in opened} \
                if opened else set()
            active = {r["crisis_type"] for r in
                      crises_mod.active_crises(store)}
            self.assertIn("unemployment_crisis", active | types)
            record = store.row(
                "SELECT * FROM crisis_records WHERE crisis_type ="
                " 'unemployment_crisis'")
            self.assertIsNotNone(record)
            severity = json.loads(record["severity"])
            self.assertIn("unemployment_rate", severity)
        finally:
            sim.close()
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
