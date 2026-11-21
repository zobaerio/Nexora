"""Session 05 Units 01+02 — National Government Foundation and
Government Organization: one real country, defined authority,
cross-branch refusal, treasury conservation, multi-country
data model."""
import sqlite3
import unittest

from tools.sim import government as gov
from tools.sim.tests.govcommon import GM, funded_world


class TestFoundation(unittest.TestCase):
    def setUp(self):
        self.store, self.data, self.ids = funded_world(adults=40)

    def test_one_country_both_cities(self):
        row = self.store.row("SELECT * FROM countries")
        self.assertEqual(row["country_id"], "bangladesh")
        self.assertEqual(row["capital_city_id"], "rupsha_city")
        cities = {r["city_id"] for r in self.store.rows(
            "SELECT * FROM treasuries WHERE scope = 'municipal'")}
        self.assertEqual(cities, {"rupsha_city", "shibnagar_town"})

    def test_second_country_record_constructible(self):
        # The data model supports multiple countries; a minimal
        # second record is data only — no fabricated population.
        self.store.insert(
            "countries", country_id="testland", name="Testland",
            capital_city_id=None, currency_code="TST",
            next_election_month=None,
            created_at_game_minutes=GM)
        self.assertEqual(self.store.row(
            "SELECT COUNT(*) AS n FROM countries")["n"], 2)

    def test_institutions_and_offices_seated(self):
        n = self.store.row("SELECT COUNT(*) AS n FROM"
                           " institutions")["n"]
        self.assertGreaterEqual(n, 15)
        for title, inst in (("president", "GOV-PRESIDENCY"),
                            ("prime_minister", "GOV-PM"),
                            ("chief_justice", "GOV-COURT"),
                            ("auditor_general", "GOV-AUDIT"),
                            ("election_commissioner", "GOV-EC")):
            office = gov.office_holder(self.store, title, inst)
            self.assertIsNotNone(office, title)
            self.assertIn(office["holder_character_id"], self.ids)
        judges = self.store.rows(
            "SELECT * FROM offices WHERE institution_id ="
            " 'GOV-COURT' AND status = 'active'")
        self.assertGreaterEqual(len(judges), 3)

    def test_leadership_are_real_citizens(self):
        for o in self.store.rows("SELECT * FROM offices WHERE"
                                 " status = 'active' AND"
                                 " holder_character_id IS NOT NULL"):
            char = self.store.row(
                "SELECT * FROM characters WHERE character_id = ?",
                (o["holder_character_id"],))
            self.assertEqual(char["is_system"], 0)
            self.assertIsNone(char["died_at_game_minutes"])

    def test_empty_city_has_no_mayor(self):
        # Shibnagar has no residents in this fixture: the mayor's
        # office honestly stays vacant rather than importing a
        # Rupsha citizen.
        office = gov.office_holder(self.store, "mayor",
                                   "GOV-CITY-SHIBNAGAR")
        self.assertTrue(office is None
                        or office["holder_character_id"] is None)
        rupsha = gov.office_holder(self.store, "mayor",
                                   "GOV-CITY-RUPSHA")
        self.assertIsNotNone(rupsha["holder_character_id"])

    def test_treasury_split_conserves_money(self):
        # Setup moved no money unaccountably: the whole ledger
        # still reconciles exactly, and the municipal treasuries
        # plus the national account hold what the records say.
        self.assertEqual(self.store.ledger_sum_check(), [])
        balances = gov.government_balances(self.store)
        self.assertEqual(set(balances), set(gov.TREASURY_ACCOUNTS))
        total = self.store.row(
            "SELECT COALESCE(SUM(balance_cached), 0) AS s FROM"
            " characters")["s"]
        ledger_total = self.store.row(
            "SELECT COALESCE(SUM(amount), 0) AS s FROM"
            " economy_ledger WHERE to_character_id IS NOT NULL")["s"] \
            - self.store.row(
            "SELECT COALESCE(SUM(amount), 0) AS s FROM"
            " economy_ledger WHERE from_character_id IS NOT NULL")["s"]
        self.assertEqual(total, ledger_total)


class TestAuthority(unittest.TestCase):
    def setUp(self):
        self.store, self.data, self.ids = funded_world(adults=40)

    def test_cross_branch_actions_rejected(self):
        judge = gov.office_holder(self.store, "judge",
                                  "GOV-COURT")["holder_character_id"]
        pm = gov.office_holder(self.store, "prime_minister",
                               "GOV-PM")["holder_character_id"]
        mayor = gov.office_holder(self.store, "mayor",
                                  "GOV-CITY-RUPSHA")[
                                      "holder_character_id"]
        plain = next(c for c in self.ids
                     if not gov.offices_of(self.store, c))
        # Judiciary cannot approve budgets or sign agreements.
        with self.assertRaises(PermissionError):
            gov.require_authority(self.store, judge,
                                  "approve_budget")
        with self.assertRaises(PermissionError):
            gov.require_authority(self.store, judge,
                                  "sign_agreement")
        # Executive cannot judge cases.
        with self.assertRaises(PermissionError):
            gov.require_authority(self.store, pm, "judge_case")
        # A mayor's authority is scoped to their own city.
        with self.assertRaises(PermissionError):
            gov.require_authority(self.store, mayor,
                                  "municipal_policy",
                                  city_id="shibnagar_town")
        gov.require_authority(self.store, mayor, "municipal_policy",
                              city_id="rupsha_city")
        # A citizen with no office holds no authority at all.
        with self.assertRaises(PermissionError):
            gov.require_authority(self.store, plain, "approve_budget")
        # And the right holders pass their own checks.
        gov.require_authority(self.store, pm, "sign_agreement")
        gov.require_authority(self.store, judge, "judge_case")

    def test_office_transfer_preserves_records(self):
        pm_office = gov.office_holder(self.store, "prime_minister",
                                      "GOV-PM")
        first = pm_office["holder_character_id"]
        replacement = next(c for c in self.ids if c != first)
        gov.appoint_office(self.store, "GOV-PM", "prime_minister",
                           replacement, "test", GM + 1000)
        old = self.store.row(
            "SELECT * FROM offices WHERE office_id = ?",
            (pm_office["office_id"],))
        self.assertEqual(old["status"], "ended")
        self.assertEqual(old["holder_character_id"], first)
        new = gov.office_holder(self.store, "prime_minister",
                                "GOV-PM")
        self.assertEqual(new["holder_character_id"], replacement)


if __name__ == "__main__":
    unittest.main()
