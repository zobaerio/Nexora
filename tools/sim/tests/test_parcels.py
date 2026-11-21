"""Session 03 Unit 03 — Land Parcel Management."""
import unittest

from tools.sim import cities as cities_mod
from tools.sim import parcels as parcels_mod
from tools.sim.tests.common import data, make_person, make_store, rng


class TestParcels(unittest.TestCase):
    def setUp(self):
        self.store = make_store()
        self.d = data()
        cities_mod.setup_cities(self.store, self.d, rng())

    def tearDown(self):
        self.store.close()

    def test_setup_one_parcel_per_plot(self):
        n = self.store.row("SELECT COUNT(*) AS n FROM"
                           " land_parcels")["n"]
        self.assertEqual(n, 64)  # 42 District 1 + 22 generated
        for p in self.store.rows("SELECT * FROM land_parcels"):
            self.assertAlmostEqual(p["area_sqm"], p["w"] * p["d"])
            self.assertIsNotNone(p["zoning_category"])
        genesis = self.store.row("SELECT COUNT(*) AS n FROM"
                                 " parcel_history WHERE event ="
                                 " 'genesis'")["n"]
        self.assertEqual(genesis, 64)

    def _vacant(self):
        return self.store.row("SELECT * FROM land_parcels WHERE"
                              " development_status = 'vacant'"
                              " ORDER BY parcel_id LIMIT 1")

    def test_transfer_with_payment(self):
        parcel = self._vacant()
        buyer = make_person(self.store, first="Land", last="Buyer")
        self.store.transfer("SYS-EMPLOYERS", buyer, 500000, "seed",
                            480)
        before = self.store.balance(buyer)
        self.assertTrue(parcels_mod.transfer_parcel(
            self.store, parcel["parcel_id"], buyer, 100000, 480))
        row = parcels_mod.get(self.store, parcel["parcel_id"])
        self.assertEqual(row["owner_character_id"], buyer)
        self.assertEqual(self.store.balance(buyer), before - 100000)
        events = [h["event"] for h in parcels_mod.ownership_history(
            self.store, parcel["parcel_id"])]
        self.assertEqual(events, ["genesis", "transfer"])
        self.assertEqual(self.store.ledger_sum_check(), [])

    def test_transfer_protected_refused(self):
        park = self.store.row("SELECT * FROM land_parcels WHERE"
                              " building_id = 'b_d1_park_land'")
        buyer = make_person(self.store, first="Park", last="Buyer")
        self.assertFalse(parcels_mod.transfer_parcel(
            self.store, park["parcel_id"], buyer, 1000, 480))

    def test_transfer_unaffordable_refused(self):
        parcel = self._vacant()
        buyer = make_person(self.store, first="Poor", last="Buyer")
        self.assertFalse(parcels_mod.transfer_parcel(
            self.store, parcel["parcel_id"], buyer, 10 ** 9, 480))
        self.assertIsNone(parcels_mod.get(
            self.store, parcel["parcel_id"])["owner_character_id"])

    def test_subdivide_and_merge_roundtrip(self):
        parcel = self.store.row(
            "SELECT * FROM land_parcels WHERE building_id IS NULL"
            " AND zone_id = 'c2_agriculture'")
        area = parcel["area_sqm"]
        new_id = parcels_mod.subdivide_parcel(
            self.store, parcel["parcel_id"], 480)
        self.assertIsNotNone(new_id)
        a = parcels_mod.get(self.store, parcel["parcel_id"])
        b = parcels_mod.get(self.store, new_id)
        self.assertAlmostEqual(a["area_sqm"] + b["area_sqm"], area)
        self.assertTrue(parcels_mod.merge_parcels(
            self.store, parcel["parcel_id"], new_id, 480))
        merged = parcels_mod.get(self.store, parcel["parcel_id"])
        self.assertAlmostEqual(merged["area_sqm"], area)
        self.assertIsNone(parcels_mod.get(self.store, new_id))

    def test_subdivide_developed_refused(self):
        developed = self.store.row(
            "SELECT * FROM land_parcels WHERE development_status ="
            " 'developed' LIMIT 1")
        self.assertIsNone(parcels_mod.subdivide_parcel(
            self.store, developed["parcel_id"], 480))


if __name__ == "__main__":
    unittest.main()
