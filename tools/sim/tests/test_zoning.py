"""Session 03 Unit 04 — Urban Zoning Engine."""
import unittest

from tools.sim import zoning as zoning_mod
from tools.sim.tests.common import data


class TestZoning(unittest.TestCase):
    def test_building_categories(self):
        d = data()
        by_id = d.all_buildings()
        self.assertEqual(zoning_mod.building_category(
            by_id["b_d1_civic_school"]), "educational")
        self.assertEqual(zoning_mod.building_category(
            by_id["b_d1_civic_clinic"]), "healthcare")
        self.assertEqual(zoning_mod.building_category(
            by_id["b_d1_civic_police"]), "government")
        self.assertEqual(zoning_mod.building_category(
            by_id["b_d1_midtown_starter_block"]), "residential")
        self.assertEqual(zoning_mod.building_category(
            by_id["b_d1_industry_factories"]), "industrial")
        self.assertEqual(zoning_mod.building_category(
            by_id["b_d1_market_hall_units"]), "commercial")
        self.assertEqual(zoning_mod.building_category(
            by_id["b_d1_park_land"]), "recreational")
        self.assertEqual(zoning_mod.building_category(
            by_id["b_d1_transport_station"]), "transportation")

    def test_ten_categories(self):
        self.assertEqual(len(zoning_mod.CATEGORIES), 10)

    def test_school_in_industrial_rejected(self):
        violations = zoning_mod.validate_placement(
            "educational", "d1_industry")
        self.assertTrue(any("industrial" in v for v in violations))

    def test_density_cap(self):
        violations = zoning_mod.validate_placement(
            "residential", "d1_midtown", units=100, area_sqm=1000)
        self.assertTrue(any("density" in v for v in violations))
        self.assertEqual(zoning_mod.validate_placement(
            "residential", "d1_midtown", units=10, area_sqm=1000), [])

    def test_lawful_placements(self):
        self.assertEqual(zoning_mod.validate_placement(
            "commercial", "d1_market"), [])
        self.assertEqual(zoning_mod.validate_placement(
            "healthcare", "d1_civic"), [])
        self.assertEqual(zoning_mod.validate_placement(
            "industrial", "d1_industry"), [])

    def test_environmental_protection_takes_nothing(self):
        violations = zoning_mod.validate_placement(
            "environmental_protection", "d1_park")
        self.assertTrue(violations)

    def test_grandfathered_nonconformities_reported(self):
        out = zoning_mod.audit_existing(data())
        ids = {e["building_id"] for e in out}
        # The market godowns are industry inside a commercial zone.
        self.assertIn("b_d1_market_godowns", ids)
        for e in out:
            allowed = zoning_mod.ZONE_ALLOWED[e["zone_category"]]
            self.assertNotIn(e["category"], allowed)


if __name__ == "__main__":
    unittest.main()
