"""Session 03 Unit 01 — City Generation & Registry."""
import os
import unittest

from tools.sim import cities as cities_mod
from tools.sim import citygen
from tools.sim.engine import Simulation
from tools.sim.tests.common import data, make_store, rng


class TestGenerator(unittest.TestCase):
    def test_generated_file_reproducible(self):
        """The committed town file is exactly what the generator
        produces — generated data can never drift from its code."""
        path = os.path.join(os.path.dirname(__file__), "..", "..",
                            "..", "data", "city2-shibnagar.json")
        with open(os.path.abspath(path)) as f:
            committed = f.read()
        self.assertEqual(committed, citygen.generate_file_text())

    def test_town_spec_shape(self):
        spec = data().city_spec("shibnagar_town")
        self.assertEqual(spec["kind"], "generated_town")
        self.assertEqual(len(spec["zones"]), 6)
        units = data().residential_stock_city(spec)
        self.assertEqual(len(units), 39)


class TestRegistry(unittest.TestCase):
    def test_setup_registers_both_cities(self):
        store = make_store()
        cities_mod.setup_cities(store, data(), rng())
        rows = store.rows("SELECT * FROM cities ORDER BY city_id")
        self.assertEqual([r["city_id"] for r in rows],
                         ["rupsha_city", "shibnagar_town"])
        self.assertEqual(rows[0]["kind"], "seeded")
        self.assertEqual(rows[1]["kind"], "generated_town")
        self.assertEqual(rows[0]["climate"], "tropical_monsoon")
        self.assertEqual(store.row("SELECT COUNT(*) AS n FROM"
                                   " city_zones")["n"], 16)
        store.close()

    def test_setup_idempotent_and_town_stock(self):
        store = make_store()
        cities_mod.setup_cities(store, data(), rng())
        cities_mod.setup_cities(store, data(), rng())
        self.assertEqual(store.row("SELECT COUNT(*) AS n FROM"
                                   " cities")["n"], 2)
        stock = store.row("SELECT COUNT(*) AS n FROM properties"
                          " WHERE district_id LIKE 'c2_%'")["n"]
        self.assertEqual(stock, 39)
        store.close()

    def test_city_population_reads_residence(self):
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(path)
        sim = Simulation(path, seed="city-test")
        sim.generate_population(100)
        self.assertGreater(cities_mod.city_population(
            sim.store, sim.data, "rupsha_city"), 0)
        self.assertEqual(cities_mod.city_population(
            sim.store, sim.data, "shibnagar_town"), 0)
        sim.close()
        os.remove(path)


if __name__ == "__main__":
    unittest.main()
