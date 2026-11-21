"""Session 05 Units 10+11+12+13 — Judiciary, Law Enforcement,
Corruption & Accountability, International Relations."""
import unittest

from tools.sim import diplomacy, government as gov, integrity
from tools.sim import justice, safety
from tools.sim.tests.common import rng
from tools.sim.tests.govcommon import GM, funded_world

M1 = 43200


def _pm(store):
    return gov.office_holder(store, "prime_minister",
                             "GOV-PM")["holder_character_id"]


class TestJudiciary(unittest.TestCase):
    def setUp(self):
        self.store, self.data, self.ids = funded_world(adults=40)

    def _defaulted_loan(self, borrower, outstanding=30000):
        self.store.insert(
            "loans", loan_id="LN-T1", borrower_character_id=borrower,
            kind="personal", principal_ncr=outstanding,
            outstanding_ncr=outstanding, annual_rate_percent=12,
            term_months=24, months_elapsed=6, interest_paid_ncr=0,
            missed_payments=3, status="defaulted", property_id=None,
            started_at_game_minutes=GM,
            updated_at_game_minutes=GM)
        return "LN-T1"

    def test_case_from_real_default(self):
        borrower = self.ids[10]
        self._defaulted_loan(borrower)
        cid = justice.file_case(
            self.store, "debt_default", "loan", "LN-T1", "SYS-BANK",
            borrower, {"claim": "loan default"}, M1)
        case = self.store.row("SELECT * FROM court_cases WHERE"
                              " case_id = ?", (cid,))
        # The allegation is on record; there is NO finding yet.
        self.assertIsNone(case["finding"])
        self.assertEqual(case["status"], "filed")
        result = justice.hear_case(self.store, self.data, cid, M1)
        self.assertTrue(result["liable"])
        case = self.store.row("SELECT * FROM court_cases WHERE"
                              " case_id = ?", (cid,))
        self.assertIsNotNone(case["finding"])
        self.assertEqual(case["status"], "judged")
        # The remedy executed: the borrower paid what they held
        # above the reserve and the loan book moved with it.
        loan = self.store.row("SELECT * FROM loans WHERE loan_id"
                              " = 'LN-T1'")
        paid = 30000 - loan["outstanding_ncr"]
        self.assertGreater(paid, 0)
        self.assertEqual(case["remedy_ncr"], paid)
        self.assertEqual(self.store.ledger_sum_check(), [])

    def test_monthly_intake_files_and_hears(self):
        self._defaulted_loan(self.ids[11])
        out = justice.monthly_pass(self.store, self.data, rng(), 1,
                                   M1)
        self.assertTrue(out["filed"])
        self.assertTrue(out["heard"])
        self.assertEqual(self.store.row(
            "SELECT COUNT(*) AS n FROM court_cases WHERE status"
            " = 'judged'")["n"], 1)

    def test_only_the_loser_may_appeal(self):
        borrower = self.ids[12]
        self._defaulted_loan(borrower)
        cid = justice.file_case(
            self.store, "debt_default", "loan", "LN-T1", "SYS-BANK",
            borrower, {"claim": "loan default"}, M1)
        justice.hear_case(self.store, self.data, cid, M1)
        # The bank won; it cannot appeal its own victory.
        with self.assertRaises(PermissionError):
            justice.appeal_case(self.store, self.data, cid,
                                "SYS-BANK", M1)
        # The borrower (loser) can — a second judge reviews under
        # the stricter standard and the record closes.
        out = justice.appeal_case(self.store, self.data, cid,
                                  borrower, M1)
        self.assertIn("appeal_id", out)
        appeal = self.store.row("SELECT * FROM court_cases WHERE"
                                " case_id = ?",
                                (out["appeal_id"],))
        self.assertEqual(appeal["appeal_of"], cid)
        self.assertEqual(appeal["status"], "closed")
        # An appeal judgment is final.
        with self.assertRaises(ValueError):
            justice.appeal_case(self.store, self.data,
                                out["appeal_id"], borrower, M1)


class TestSafety(unittest.TestCase):
    def setUp(self):
        self.store, self.data, self.ids = funded_world(adults=40)

    def test_no_incidents_without_sources(self):
        out = safety.monthly_pass(self.store, self.data, rng(), 1,
                                  M1)
        self.assertEqual(out["created"], [])
        self.assertEqual(safety.safety_stats(self.store)["total"], 0)

    def test_escalated_conflict_becomes_case(self):
        a, b = self.ids[20], self.ids[21]
        rid = "RL-T1"
        self.store.insert(
            "relationships", relationship_id=rid,
            from_character_id=a, to_character_id=b,
            relation_type="neighbour", trust=10, affection=10,
            respect=10, flags="{}",
            last_interaction_at_game_minutes=GM,
            created_at_game_minutes=GM)
        self.store.insert(
            "social_profiles", relationship_id=rid, familiarity=5,
            conflict=60, interaction_count=9, last_event="argument",
            updated_at_game_minutes=GM)
        self.store.insert(
            "conflict_records", conflict_id="CF-T1",
            a_character_id=a, b_character_id=b,
            cause="resource_dispute", status="escalated",
            mediator_character_id=None, resolution=None,
            opened_at_game_minutes=GM, closed_at_game_minutes=None)
        # A civic police officer resident in Rupsha.
        officer = self.ids[22]
        self.store.insert(
            "employments", employment_id="EM-T1",
            character_id=officer, profession_id="police_officer",
            employer_business_id=None,
            employer_character_id="SYS-CITY", tier=1,
            wage_per_month=20000, started_at_game_minutes=GM)
        out = safety.monthly_pass(self.store, self.data, rng(), 1,
                                  M1)
        self.assertEqual(len(out["created"]), 1)
        incident = self.store.row("SELECT * FROM incidents")
        self.assertEqual(incident["incident_type"], "public_order")
        self.assertEqual(incident["officer_character_id"], officer)
        self.assertEqual(incident["status"], "referred_to_court")
        case = self.store.row("SELECT * FROM court_cases WHERE"
                              " source_kind = 'incident'")
        self.assertIsNotNone(case)
        self.assertEqual(case["plaintiff_id"], a)
        self.assertEqual(case["defendant_id"], b)


class TestIntegrity(unittest.TestCase):
    def setUp(self):
        self.store, self.data, self.ids = funded_world(adults=40)

    def test_clean_audit_measures_zero_discrepancies(self):
        out = integrity.monthly_pass(self.store, self.data, rng(),
                                     1, M1)
        self.assertEqual(out["discrepancies"], 0)
        self.assertEqual(out["integrity_index"], 100)
        audit = self.store.row("SELECT * FROM audits")
        self.assertEqual(audit["result"], "clean")
        self.assertIsNotNone(audit["auditor_character_id"])

    def test_conflict_of_interest_flagged_from_data(self):
        pm = _pm(self.store)
        self.store.insert(
            "businesses", business_id="BZ-T1", name="PM Ventures",
            business_type="retail", owner_character_id=pm,
            property_id=None, balance_cached=0,
            founded_at_game_minutes=GM,
            closed_at_game_minutes=None, status="active")
        flagged = integrity.conflict_of_interest_scan(self.store,
                                                      M1)
        self.assertEqual(len(flagged), 1)
        row = self.store.row("SELECT * FROM coi_records")
        self.assertEqual(row["character_id"], pm)
        self.assertEqual(row["business_id"], "BZ-T1")
        # A flag is a record to manage, not a conviction: the
        # audit still measures clean.
        out = integrity.audit_government(self.store, self.data, M1)
        self.assertEqual(out["discrepancies"], [])

    def test_whistleblower_report_checked_and_closed(self):
        rid = integrity.file_report(self.store, self.ids[0],
                                    "SYS-CITY", M1)
        out = integrity.investigate_report(self.store, self.data,
                                           rid, M1)
        # The ledger reconciles, so the claim is unsubstantiated —
        # on the record, not silently dropped.
        self.assertEqual(out["outcome"], "unsubstantiated")
        rep = self.store.row("SELECT * FROM integrity_reports"
                             " WHERE report_id = ?", (rid,))
        self.assertEqual(rep["status"], "closed")


class TestDiplomacy(unittest.TestCase):
    def setUp(self):
        self.store, self.data, self.ids = funded_world(adults=40)
        self.pm = _pm(self.store)

    def test_partner_is_a_labelled_model(self):
        partner = self.store.row("SELECT * FROM external_partners")
        self.assertEqual(partner["partner_id"], "external_partner")
        self.assertIn("model", partner["model_note"].lower())
        # No fabricated nation: exactly one country exists.
        self.assertEqual(self.store.row(
            "SELECT COUNT(*) AS n FROM countries")["n"], 1)

    def test_trade_agreement_moves_the_tariff(self):
        self.assertEqual(diplomacy.tariff_delta(self.store,
                                                self.data), 0)
        diplomacy.sign_agreement(self.store, self.data, "trade",
                                 self.pm, M1)
        self.assertEqual(diplomacy.tariff_delta(self.store,
                                                self.data), -2)

    def test_only_the_executive_signs(self):
        plain = next(c for c in self.ids
                     if not gov.offices_of(self.store, c))
        with self.assertRaises(PermissionError):
            diplomacy.sign_agreement(self.store, self.data,
                                     "trade", plain, M1)

    def test_cooperation_grant_flows_through_ledger(self):
        diplomacy.sign_agreement(self.store, self.data,
                                 "cooperation", self.pm, M1)
        before = self.store.balance("SYS-CITY")
        partner_before = self.store.balance("SYS-EXTERNAL")
        out = diplomacy.monthly_pass(self.store, self.data, rng(),
                                     2, M1 * 2)
        self.assertEqual(out["cooperation_grant_ncr"], 10000)
        self.assertEqual(self.store.balance("SYS-CITY"),
                         before + 10000)
        self.assertEqual(self.store.balance("SYS-EXTERNAL"),
                         partner_before - 10000)


if __name__ == "__main__":
    unittest.main()
