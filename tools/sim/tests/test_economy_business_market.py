"""Session 04 Units 04-07 + 14 — Businesses, Production,
Supply Chain, Markets & Pricing, Household Consumption."""
import os
import tempfile
import unittest

from tools.sim import business as business_mod
from tools.sim import cities as cities_mod
from tools.sim import market as market_mod
from tools.sim import missions as ms
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


class TestHaggleAtTheMonthlyPass(unittest.TestCase):
    # Queue 23 Unit FA — the live haggle call site (GDD-04 §3.6,
    # mission 2.3): the monthly shopping pass haggles. Rupsha's
    # food_basket shelf is raised above the catalogue base price
    # (3750 vs base 2500) before the month-1 settlement, so every
    # headed Rupsha household that buys food haggles the stall
    # down to base — and the haggle records, verifies, and moves
    # the money at the paid price.
    @classmethod
    def setUpClass(cls):
        cls.path = _tmp_path()
        cls.sim = Simulation(cls.path, seed="q23-fa-haggle")
        cls.sim.generate_population(60)
        cls.store = cls.sim.store
        cls.data = cls.sim.data
        cls.store.execute(
            "UPDATE market_prices SET price_ncr = 3750 WHERE"
            " city_id = 'rupsha_city' AND good_id = 'food_basket'")
        cls.sim.run_days(32)

    @classmethod
    def tearDownClass(cls):
        cls.sim.close()
        os.remove(cls.path)

    def _rupsha_households_with_food(self):
        out = []
        for r in self.store.rows(
                "SELECT hc.household_id, hc.units, hc.spend_ncr,"
                " h.district_id FROM household_consumption hc"
                " JOIN households h ON h.household_id ="
                " hc.household_id WHERE hc.month_index = 1 AND"
                " hc.good_id = 'food_basket' AND hc.units > 0"):
            if cities_mod.city_of_zone(self.data,
                                       r["district_id"]) != "rupsha_city":
                continue
            head = self.store.row(
                "SELECT character_id FROM household_members WHERE"
                " household_id = ? AND role = 'head' AND"
                " left_at_game_minutes IS NULL",
                (r["household_id"],))
            out.append((r, head["character_id"] if head else None))
        return out

    def test_haggled_food_purchase_records_a_successful_haggle(self):
        rows = self.store.rows("SELECT * FROM haggle_events")
        self.assertTrue(rows)
        # Every haggle is the mission's food good, in Boro Bazar,
        # won down to the catalogue base price from the raised
        # shelf — the fish shelf stood at base, so no fish haggle.
        for r in rows:
            self.assertEqual(r["good_id"], "food_basket")
            self.assertEqual(r["zone"], "d1_market")
            self.assertEqual(r["outcome"], "success")
            self.assertEqual(r["asked_price_ncr"], 3750)
            self.assertEqual(r["paid_price_ncr"], 2500)
        # Exactly one haggle per headed Rupsha household that
        # bought food — one stall purchase, one record.
        haggled = {r["character_id"] for r in rows}
        for _row, head in self._rupsha_households_with_food():
            if head is None:
                continue
            self.assertIn(head, haggled)
            self.assertEqual(
                sum(1 for r in rows
                    if r["character_id"] == head), 1)

    def test_haggled_households_spend_the_paid_price(self):
        haggled = {r["character_id"]
                   for r in self.store.rows(
                       "SELECT character_id FROM haggle_events")}
        checked = 0
        for row, head in self._rupsha_households_with_food():
            if head is None or head not in haggled:
                continue
            checked += 1
            # The consumption row records the paid price, and the
            # same spend bought more food than the shelf price
            # would have bought. (Units are stored rounded to 3
            # decimals while spend is computed from the unrounded
            # units, so the paid-price check allows ±2 NCr.)
            self.assertLessEqual(
                abs(row["spend_ncr"] - round(row["units"] * 2500)),
                2)
            self.assertGreater(row["units"] * 3750, row["spend_ncr"])
        self.assertGreater(checked, 0)

    def test_shelves_are_paid_what_buyers_paid(self):
        # SYS-MARKET sellers are paid takings on what left their
        # shelves at the price the buyers actually paid (2500),
        # not the shelf price (3750); owner-run shops are not paid
        # takings at all (their P&L is the settlement's). The
        # per-seller int(round()) bounds the total error.
        sys_drawn = 0.0
        for r in self.store.rows(
                "SELECT * FROM inventory_movements WHERE kind ="
                " 'retail_sale' AND good_id = 'food_basket' AND"
                " game_minutes = 43200"):
            b = self.store.row(
                "SELECT * FROM businesses WHERE business_id = ?",
                (r["business_id"],))
            if b and b["owner_character_id"] == "SYS-MARKET" \
                    and business_mod.business_city(
                        self.store, self.data, b) == "rupsha_city":
                sys_drawn += -r["delta"]
        takings = 0
        sellers = set()
        for r in self.store.rows(
                "SELECT * FROM economy_ledger WHERE reason_code ="
                " 'retail_takings' AND transfer_key LIKE"
                " '%:food_basket:1'"):
            b = self.store.row(
                "SELECT * FROM businesses WHERE business_id = ?",
                (r["to_business_id"],))
            if b and business_mod.business_city(
                    self.store, self.data, b) == "rupsha_city":
                takings += r["amount"]
                sellers.add(r["to_business_id"])
        self.assertGreater(sys_drawn, 0)
        self.assertLessEqual(abs(takings - round(sys_drawn * 2500)),
                             len(sellers))
        self.assertLess(abs(takings - round(sys_drawn * 2500)),
                        abs(takings - round(sys_drawn * 3750)))

    def test_haggled_month_completes_mission_2_3(self):
        row = self.store.row("SELECT character_id FROM haggle_events"
                             " LIMIT 1")
        cid = row["character_id"]
        self.assertTrue(market_mod.has_successful_haggle(
            self.store, cid, "d1_market"))
        ms.make_available(self.store, cid, "2.3", 10 ** 8)
        ms.accept_mission(self.store, cid, "2.3", 10 ** 8 + 100)
        self.assertTrue(ms.verify_mission_2_3(
            self.store, self.data, cid, 10 ** 8 + 200))


class TestNoHaggleAtBasePrices(unittest.TestCase):
    # Queue 23 Unit FA — the negative case: at genesis prices
    # every shelf stands at its base price, so there is nothing to
    # haggle down to, no haggle is recorded, and the food purchase
    # alone does not verify mission 2.3.
    @classmethod
    def setUpClass(cls):
        cls.path = _tmp_path()
        cls.sim = Simulation(cls.path, seed="q23-fa-nohaggle")
        cls.sim.generate_population(60)
        cls.store = cls.sim.store
        cls.data = cls.sim.data
        cls.sim.run_days(32)

    @classmethod
    def tearDownClass(cls):
        cls.sim.close()
        os.remove(cls.path)

    def test_no_haggle_rows_when_shelves_are_at_base(self):
        self.assertEqual(
            self.store.rows("SELECT * FROM haggle_events"), [])

    def test_food_without_a_haggle_does_not_verify_2_3(self):
        cid = None
        for r in self.store.rows(
                "SELECT hc.household_id FROM household_consumption"
                " hc JOIN households h ON h.household_id ="
                " hc.household_id WHERE hc.month_index = 1 AND"
                " hc.good_id = 'food_basket' AND hc.units > 0"):
            if cities_mod.city_of_zone(
                    self.data,
                    self.store.row(
                        "SELECT district_id FROM households WHERE"
                        " household_id = ?",
                        (r["household_id"],))["district_id"]) \
                    != "rupsha_city":
                continue
            head = self.store.row(
                "SELECT character_id FROM household_members WHERE"
                " household_id = ? AND role = 'head' AND"
                " left_at_game_minutes IS NULL",
                (r["household_id"],))
            if head is not None:
                cid = head["character_id"]
                break
        self.assertIsNotNone(cid)
        self.assertFalse(market_mod.has_successful_haggle(
            self.store, cid, "d1_market"))
        ms.make_available(self.store, cid, "2.3", 10 ** 8)
        ms.accept_mission(self.store, cid, "2.3", 10 ** 8 + 100)
        self.assertFalse(ms.verify_mission_2_3(
            self.store, self.data, cid, 10 ** 8 + 200))


class TestHaggleClothingAtTheMonthlyPass(unittest.TestCase):
    # Queue 24 Unit GA — the same rule, extended to clothing
    # (GDD-04 §3.6, mission 2.3): the monthly shopping pass
    # haggles clothing stalls too. Rupsha's clothing_set shelf is
    # raised above the catalogue base price (900 vs base 600)
    # before the month-1 settlement, so every headed Rupsha
    # household that buys clothing haggles the stall down to base
    # — and the haggle records, moves the money at the paid price,
    # and satisfies mission 2.3's "haggle once" objective, because
    # the verifier reads character + zone + success, never the
    # good. The food shelf stands at base in this run, so no food
    # haggle fires — the clothing haggle alone must verify 2.3.
    @classmethod
    def setUpClass(cls):
        cls.path = _tmp_path()
        cls.sim = Simulation(cls.path, seed="q24-ga-clothing")
        cls.sim.generate_population(60)
        cls.store = cls.sim.store
        cls.data = cls.sim.data
        cls.store.execute(
            "UPDATE market_prices SET price_ncr = 900 WHERE"
            " city_id = 'rupsha_city' AND good_id = 'clothing_set'")
        cls.sim.run_days(32)

    @classmethod
    def tearDownClass(cls):
        cls.sim.close()
        os.remove(cls.path)

    def _rupsha_households_with_clothing(self):
        out = []
        for r in self.store.rows(
                "SELECT hc.household_id, hc.units, hc.spend_ncr,"
                " h.district_id FROM household_consumption hc"
                " JOIN households h ON h.household_id ="
                " hc.household_id WHERE hc.month_index = 1 AND"
                " hc.good_id = 'clothing_set' AND hc.units > 0"):
            if cities_mod.city_of_zone(self.data,
                                       r["district_id"]) != "rupsha_city":
                continue
            head = self.store.row(
                "SELECT character_id FROM household_members WHERE"
                " household_id = ? AND role = 'head' AND"
                " left_at_game_minutes IS NULL",
                (r["household_id"],))
            out.append((r, head["character_id"] if head else None))
        return out

    def test_haggled_clothing_purchase_records_a_successful_haggle(self):
        rows = self.store.rows(
            "SELECT * FROM haggle_events WHERE good_id ="
            " 'clothing_set'")
        self.assertTrue(rows)
        # Every clothing haggle is in Boro Bazar, won down to the
        # catalogue base price (600) from a shelf above it — the
        # asked price is read from the row, not assumed to be the
        # raised 900, because the monthly price pass may step the
        # shelf before the allocation reads it.
        for r in rows:
            self.assertEqual(r["zone"], "d1_market")
            self.assertEqual(r["outcome"], "success")
            self.assertEqual(r["paid_price_ncr"], 600)
            self.assertGreater(r["asked_price_ncr"], 600)
        # Exactly one clothing haggle per headed Rupsha household
        # that bought clothing — one stall purchase, one record.
        haggled = {r["character_id"] for r in rows}
        for _row, head in self._rupsha_households_with_clothing():
            if head is None:
                continue
            self.assertIn(head, haggled)
            self.assertEqual(
                sum(1 for r in rows
                    if r["character_id"] == head), 1)

    def test_haggled_clothing_households_spend_the_paid_price(self):
        haggled = {r["character_id"]
                   for r in self.store.rows(
                       "SELECT character_id FROM haggle_events WHERE"
                       " good_id = 'clothing_set'")}
        checked = 0
        for row, head in self._rupsha_households_with_clothing():
            if head is None or head not in haggled:
                continue
            checked += 1
            # The consumption row records the paid price (600), and
            # the same spend bought more clothing than the shelf
            # price would have bought. (Units are stored rounded to
            # 3 decimals while spend is computed from the unrounded
            # units, so the paid-price check allows ±2 NCr.)
            self.assertLessEqual(
                abs(row["spend_ncr"] - round(row["units"] * 600)),
                2)
            self.assertGreater(row["units"] * 900, row["spend_ncr"])
        self.assertGreater(checked, 0)

    def test_clothing_haggle_satisfies_mission_2_3(self):
        # A clothing haggle in d1_market satisfies objective (2):
        # the verifier is good-agnostic. The household also bought
        # food this month (objective (1)), so the month verifies
        # 2.3 with no food haggle anywhere in the world.
        self.assertEqual(
            self.store.rows("SELECT * FROM haggle_events WHERE"
                            " good_id = 'food_basket'"), [])
        cid = None
        for row, head in self._rupsha_households_with_clothing():
            if head is None:
                continue
            food = self.store.row(
                "SELECT 1 FROM household_consumption WHERE"
                " household_id = ? AND month_index = 1 AND"
                " good_id = 'food_basket' AND units > 0",
                (row["household_id"],))
            if food is not None:
                cid = head
                break
        self.assertIsNotNone(cid)
        self.assertTrue(market_mod.has_successful_haggle(
            self.store, cid, "d1_market"))
        ms.make_available(self.store, cid, "2.3", 10 ** 8)
        ms.accept_mission(self.store, cid, "2.3", 10 ** 8 + 100)
        self.assertTrue(ms.verify_mission_2_3(
            self.store, self.data, cid, 10 ** 8 + 200))


if __name__ == "__main__":
    unittest.main()
