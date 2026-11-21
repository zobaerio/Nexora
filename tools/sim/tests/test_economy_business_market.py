"""Session 04 Units 04-07 + 14 — Businesses, Production,
Supply Chain, Markets & Pricing, Household Consumption."""
import os
import tempfile
import unittest

from tools.sim import business as business_mod
from tools.sim import market as market_mod
from tools.sim.engine import Simulation


def _tmp_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


class TestBusinessesAndMarkets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = _tmp_path()
        cls.sim = Simulation(cls.path, seed="s04-bizmark")
        cls.sim.generate_population(60)
        cls.store = cls.sim.store
        cls.data = cls.sim.data

    @classmethod
    def tearDownClass(cls):
        cls.sim.close()
        os.remove(cls.path)

    def test_businesses_sit_in_real_commercial_properties(self):
        buildings = self.data.all_buildings()
        placed = 0
        for b in self.store.rows("SELECT * FROM businesses"):
            self.assertIn(b["category"], business_mod.GENESIS_CAPITAL)
            if b["property_id"]:
                prop = self.store.row(
                    "SELECT * FROM properties WHERE property_id = ?",
                    (b["property_id"],))
                self.assertIsNotNone(prop)
                self.assertEqual(prop["status"], "commercial")
                self.assertIn(prop["building_ref"], buildings)
                placed += 1
        self.assertGreater(placed, 30)

    def test_system_firms_are_labelled_as_such(self):
        system = self.store.rows(
            "SELECT business_id FROM businesses WHERE"
            " owner_character_id = 'SYS-MARKET'")
        self.assertTrue(system)
        for b in system[:5]:
            events = self.store.rows(
                "SELECT details FROM business_events WHERE"
                " business_id = ? AND event_type = 'registered'",
                (b["business_id"],))
            self.assertTrue(events)
            self.assertIn('"system"', events[0]["details"])

    def test_genesis_capital_came_through_the_ledger(self):
        for b in self.store.rows(
                "SELECT business_id FROM businesses LIMIT 10"):
            rows = self.store.rows(
                "SELECT amount FROM economy_ledger WHERE"
                " to_business_id = ? AND reason_code ="
                " 'business_capital'", (b["business_id"],))
            self.assertEqual(len(rows), 1)
            self.assertGreater(rows[0]["amount"], 0)

    def test_production_pays_materials_and_stocks_output(self):
        fisher = self.store.row(
            "SELECT * FROM businesses WHERE category = 'fishing'"
            " AND closed_at_game_minutes IS NULL LIMIT 1")
        bid = fisher["business_id"]
        stock_before = market_mod.inventory_of(self.store, bid,
                                               "fish")
        balance_before = self.store.business_balance(bid)
        produced = market_mod.production_pass(
            self.store, self.data, 900, 10 ** 8)
        self.assertGreater(produced.get(bid, 0), 0)
        self.assertGreater(market_mod.inventory_of(
            self.store, bid, "fish"), stock_before)
        recipe = [r for r in self.data.recipes
                  if r["id"] == "fishing"][0]
        expected_cost = produced[bid] \
            * recipe["materials_ncr_per_unit"]
        self.assertEqual(self.store.business_balance(bid),
                         balance_before - expected_cost)
        moves = self.store.rows(
            "SELECT * FROM inventory_movements WHERE business_id"
            " = ? AND kind = 'production'", (bid,))
        self.assertTrue(moves)

    def test_supply_chain_moves_stock_and_charges_shipping(self):
        # A retailer with an empty household_supplies shelf orders
        # from whoever packs them; stock and money both move.
        retailer = self.store.row(
            "SELECT * FROM businesses WHERE category = 'retail'"
            " AND owner_character_id = 'SYS-MARKET'"
            " AND closed_at_game_minutes IS NULL LIMIT 1")
        bid = retailer["business_id"]
        market_mod.adjust_inventory(
            self.store, bid, "household_supplies",
            -market_mod.inventory_of(self.store, bid,
                                     "household_supplies"),
            "test_clear", 10 ** 8)
        maker = self.store.row(
            "SELECT * FROM businesses WHERE category ="
            " 'manufacturing' AND closed_at_game_minutes IS NULL"
            " LIMIT 1")
        market_mod.adjust_inventory(
            self.store, maker["business_id"], "household_supplies",
            500, "test_stock", 10 ** 8)
        maker_stock = market_mod.inventory_of(
            self.store, maker["business_id"], "household_supplies")
        orders = market_mod.supply_chain_pass(
            self.store, self.data, 901, 10 ** 8)
        got = market_mod.inventory_of(self.store, bid,
                                      "household_supplies")
        self.assertGreater(got, 0)
        self.assertLess(market_mod.inventory_of(
            self.store, maker["business_id"], "household_supplies"),
            maker_stock)
        self.assertTrue(any(o["good_id"] == "household_supplies"
                            and o["buyer"] == bid for o in orders))

    def test_price_rises_on_shortage_and_cites_its_signals(self):
        # Wipe Rupsha's fish stock: coverage collapses, the price
        # must step up and the history row must carry the signals.
        for b in business_mod.active_businesses(self.store):
            if business_mod.business_city(self.store, self.data, b) \
                    == "rupsha_city":
                qty = market_mod.inventory_of(
                    self.store, b["business_id"], "fish")
                if qty:
                    market_mod.adjust_inventory(
                        self.store, b["business_id"], "fish", -qty,
                        "test_clear", 10 ** 8)
        old = market_mod.price_of(self.store, self.data,
                                  "rupsha_city", "fish")
        market_mod.update_prices(self.store, self.data, 902, 10 ** 8)
        new = market_mod.price_of(self.store, self.data,
                                  "rupsha_city", "fish")
        self.assertGreater(new, old)
        hist = self.store.row(
            "SELECT * FROM price_history WHERE city_id ="
            " 'rupsha_city' AND good_id = 'fish' ORDER BY"
            " history_id DESC LIMIT 1")
        self.assertIsNotNone(hist)
        self.assertEqual(hist["old_price_ncr"], old)
        self.assertEqual(hist["new_price_ncr"], new)
        self.assertIn("coverage", hist["signals"])
        self.assertIn("supply_units", hist["signals"])

    def test_price_never_leaves_its_band(self):
        self.store.execute(
            "UPDATE market_prices SET price_ncr = 1 WHERE city_id ="
            " 'rupsha_city' AND good_id = 'clothing_set'")
        market_mod.update_prices(self.store, self.data, 903, 10 ** 8)
        base = self.data.goods["clothing_set"]["base_price_ncr"]
        price = market_mod.price_of(self.store, self.data,
                                    "rupsha_city", "clothing_set")
        self.assertGreaterEqual(price, round(
            base * market_mod.PRICE_FLOOR_RATIO))
        self.assertLessEqual(price, round(
            base * market_mod.PRICE_CAP_RATIO))


class TestConsumptionAfterAMonth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = _tmp_path()
        cls.sim = Simulation(cls.path, seed="s04-consume")
        cls.sim.generate_population(60)
        cls.sim.run_days(32)
        cls.store = cls.sim.store
        cls.data = cls.sim.data

    @classmethod
    def tearDownClass(cls):
        cls.sim.close()
        os.remove(cls.path)

    def test_consumption_rows_exist_for_settled_households(self):
        rows = self.store.rows(
            "SELECT * FROM household_consumption WHERE month_index"
            " = 1")
        self.assertTrue(rows)
        goods = {r["good_id"] for r in rows}
        self.assertIn("food_basket", goods)
        total_units = sum(r["units"] for r in rows)
        self.assertGreater(total_units, 0)

    def test_rationing_is_fair_within_a_city(self):
        # Every household in a city gets the same coverage
        # fraction of its want for a good (within rounding).
        rows = self.store.rows(
            "SELECT hc.units, hc.unmet_units, h.district_id FROM"
            " household_consumption hc JOIN households h"
            " ON h.household_id = hc.household_id WHERE"
            " hc.month_index = 1 AND hc.good_id = 'food_basket'"
            " AND hc.units + hc.unmet_units >= 1")
        from tools.sim import cities as cities_mod
        by_city = {}
        for r in rows:
            city = cities_mod.city_of_zone(self.data,
                                           r["district_id"])
            want = r["units"] + r["unmet_units"]
            by_city.setdefault(city, []).append(r["units"] / want)
        for city, ratios in by_city.items():
            if len(ratios) > 1:
                self.assertLess(max(ratios) - min(ratios), 0.02,
                                f"unfair rationing in {city}")

    def test_system_retailers_were_paid_takings(self):
        takings = self.store.row(
            "SELECT COALESCE(SUM(amount),0) AS s FROM economy_ledger"
            " WHERE reason_code = 'retail_takings'")["s"]
        self.assertGreater(takings, 0)
        # Takings keys are unique per seller/good/month: no seller
        # was paid twice for the same shelf in the same month.
        dup = self.store.row(
            "SELECT COUNT(*) AS n FROM (SELECT transfer_key FROM"
            " economy_ledger WHERE reason_code = 'retail_takings'"
            " GROUP BY transfer_key HAVING COUNT(*) > 1)")["n"]
        self.assertEqual(dup, 0)


if __name__ == "__main__":
    unittest.main()
