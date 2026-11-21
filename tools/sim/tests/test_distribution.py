"""Session 03 Unit 08 — Population Distribution & Migration."""
import os
import tempfile
import unittest

from tools.sim import cities as cities_mod
from tools.sim import distribution as distribution_mod
from tools.sim import households as households_mod
from tools.sim.engine import Simulation


def _tmp_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


class TestDistribution(unittest.TestCase):
    def setUp(self):
        self.path = _tmp_path()
        self.sim = Simulation(self.path, seed="dist-test")
        self.sim.generate_population(140)
        self.store = self.sim.store
        self.data = self.sim.data

    def tearDown(self):
        self.sim.close()
        os.remove(self.path)

    def test_housing_totals_span_both_cities(self):
        rupsha = distribution_mod.housing_pressure(
            self.store, self.data, "rupsha_city")
        self.assertEqual(rupsha["total_units"], 140)
        self.assertGreater(rupsha["occupied_units"], 0)
        town = distribution_mod.housing_pressure(
            self.store, self.data, "shibnagar_town")
        self.assertEqual(town["total_units"], 39)
        self.assertEqual(town["occupied_units"], 0)

    def test_density_only_where_people_live(self):
        self.assertGreater(distribution_mod.zone_density(
            self.store, self.data, "d1_oldtown"), 0)
        self.assertEqual(distribution_mod.zone_density(
            self.store, self.data, "c2_market"), 0.0)

    def test_demand_shape(self):
        demand = distribution_mod.residential_demand(
            self.store, self.data, "rupsha_city")
        self.assertEqual(demand["total"],
                         demand["indebted_households"]
                         + demand["adults_waiting_to_form"])

    def _high_rent_household(self):
        for h in self.store.rows(
                "SELECT * FROM households WHERE"
                " dissolved_at_game_minutes IS NULL"):
            rent = households_mod.current_rent(
                self.store, self.data, h["household_id"])
            if rent and rent >= 7000:
                return h, rent
        return None, None

    def test_migration_moves_household_to_the_town(self):
        household, rent = self._high_rent_household()
        self.assertIsNotNone(household,
                             "seed world has a tier-3 tenant")
        hid = household["household_id"]
        size = len(households_mod.members(self.store, hid))
        new_rent = distribution_mod.migrate_household(
            self.store, self.data, hid, "shibnagar_town",
            {"test": "pressure"}, 480 + 40 * 1440)
        self.assertIsNotNone(new_rent)
        self.assertLessEqual(new_rent, 0.6 * rent)
        moved = self.store.row("SELECT district_id FROM households"
                               " WHERE household_id = ?", (hid,))
        self.assertTrue(moved["district_id"].startswith("c2_"))
        self.assertEqual(cities_mod.city_population(
            self.store, self.data, "shibnagar_town"), size)
        rec = self.store.row("SELECT * FROM migration_records WHERE"
                             " household_id = ?", (hid,))
        self.assertEqual(rec["from_city_id"], "rupsha_city")
        self.assertEqual(rec["to_city_id"], "shibnagar_town")

    def test_same_city_move_is_no_move(self):
        household, _rent = self._high_rent_household()
        self.assertIsNone(distribution_mod.migrate_household(
            self.store, self.data, household["household_id"],
            "rupsha_city", {"test": "same"}, 480))

    def test_pressure_needs_unemployment_plus_a_reason(self):
        household, _rent = self._high_rent_household()
        hid = household["household_id"]
        head = self.store.row(
            "SELECT character_id FROM household_members WHERE"
            " household_id = ? AND role = 'head' AND"
            " left_at_game_minutes IS NULL", (hid,))
        employed = self.store.row(
            "SELECT 1 FROM employments WHERE character_id = ? AND"
            " ended_at_game_minutes IS NULL",
            (head["character_id"],))
        if employed:
            qualifies, _ = distribution_mod.migration_pressure(
                self.store, self.data, household)
            self.assertFalse(qualifies)
        self.store.execute(
            "UPDATE employments SET ended_at_game_minutes = 480"
            " WHERE character_id = ?", (head["character_id"],))
        self.store.execute(
            "INSERT OR IGNORE INTO household_state (household_id)"
            " VALUES (?)", (hid,))
        self.store.execute(
            "UPDATE household_state SET debt_ncr = 500 WHERE"
            " household_id = ?", (hid,))
        qualifies, facts = distribution_mod.migration_pressure(
            self.store, self.data, household)
        self.assertTrue(qualifies)
        self.assertEqual(facts["debt_ncr"], 500)


if __name__ == "__main__":
    unittest.main()
