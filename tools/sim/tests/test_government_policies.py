"""Session 05 Units 06+07+08+09 — Policies with real effects,
the annual budget with explicit borrowing, civil-service
recruitment and treasury payroll, and laws that measurably
change behaviour."""
import unittest

from tools.sim import admin, government as gov, justice, policies
from tools.sim import politics
from tools.sim.tests.common import rng
from tools.sim.tests.govcommon import GM, funded_world

M1 = 43200  # end of month 1


def _pm(store):
    return gov.office_holder(store, "prime_minister",
                             "GOV-PM")["holder_character_id"]


class TestPolicies(unittest.TestCase):
    def setUp(self):
        self.store, self.data, self.ids = funded_world(adults=40)
        self.pm = _pm(self.store)

    def test_welfare_pays_the_measured_poor(self):
        # A household whose recorded income is below the poverty
        # line receives a top-up from the treasury, traceable to
        # the policy in the ledger.
        household = self.store.row(
            "SELECT household_id FROM household_members WHERE"
            " character_id = ?", (self.ids[0],))["household_id"]
        self.store.insert(
            "household_finances", finance_id="HF-T1",
            household_id=household, month_index=1, income_ncr=1000,
            food_ncr=0, housing_ncr=0, education_ncr=0,
            healthcare_ncr=0, transport_ncr=0, other_ncr=0,
            emergency_ncr=0, savings_delta_ncr=0, debt_after_ncr=0,
            game_minutes=M1)
        head_before = self.store.balance(self.ids[0])
        pid = policies.propose_policy(self.store, self.data,
                                      "welfare_support", self.pm, 1,
                                      M1)
        policies.approve_policy(self.store, self.data, pid,
                                self.pm, M1)
        out = policies.monthly_pass(self.store, self.data, 2,
                                    M1 * 2)
        self.assertIn(pid, out)
        self.assertGreater(self.store.balance(self.ids[0]),
                           head_before)
        rows = self.store.rows(
            "SELECT * FROM economy_ledger WHERE event_ref = ?",
            (pid,))
        self.assertTrue(rows)
        self.assertTrue(all(r["reason_code"] == "welfare"
                            for r in rows))
        policy = self.store.row("SELECT * FROM policies WHERE"
                                " policy_id = ?", (pid,))
        self.assertEqual(policies.policy_spent(self.store, policy),
                         sum(r["amount"] for r in rows))

    def test_infrastructure_repairs_real_roads(self):
        # A city-scoped policy spends the CITY treasury: fund it
        # first (a national-to-municipal grant through the
        # ledger), then the repairs draw on it.
        self.store.transfer("SYS-MARKET", "SYS-TREASURY-RUPSHA",
                            100000, "municipal_grant", GM,
                            note="seeded municipal funds",
                            transfer_key="seed:municipal")
        self.store.insert(
            "road_segments", segment_id="SEG-T1",
            city_id="rupsha_city", name="Test Road",
            road_class="arterial", length_m=1000, lanes=2,
            speed_limit_kmh=40, capacity_vph=1000, condition=40,
            updated_at_game_minutes=GM)
        pid = policies.propose_policy(
            self.store, self.data, "infrastructure_maintenance",
            self.pm, 1, M1, city_id="rupsha_city")
        policies.approve_policy(self.store, self.data, pid,
                                self.pm, M1)
        policies.monthly_pass(self.store, self.data, 2, M1 * 2)
        seg = self.store.row("SELECT * FROM road_segments WHERE"
                             " segment_id = 'SEG-T1'")
        # 60,000 NCr cap at 2 NCr/m/point over 1000 m = +30
        # points on a 40-condition segment.
        self.assertEqual(seg["condition"], 70)
        policy = self.store.row("SELECT * FROM policies WHERE"
                                " policy_id = ?", (pid,))
        self.assertEqual(policies.policy_spent(self.store, policy),
                         60000)

    def test_policy_approval_needs_authority(self):
        plain = next(c for c in self.ids
                     if not gov.offices_of(self.store, c))
        pid = policies.propose_policy(self.store, self.data,
                                      "welfare_support", self.pm, 1,
                                      M1)
        with self.assertRaises(PermissionError):
            policies.approve_policy(self.store, self.data, pid,
                                    plain, M1)


class TestBudget(unittest.TestCase):
    def setUp(self):
        self.store, self.data, self.ids = funded_world(adults=40)
        self.pm = _pm(self.store)

    def _seed_revenue(self, monthly=100000, months=(10, 11, 12)):
        for m in months:
            self.store.transfer(
                "SYS-MARKET", "SYS-CITY", monthly, "tax", M1 * m,
                note="seeded tax revenue",
                transfer_key=f"seedtax:{m}")

    def test_annual_budget_from_recorded_revenue(self):
        self._seed_revenue()
        out = policies.budget_pass(self.store, self.data, 12,
                                   M1 * 12)
        self.assertIsNotNone(out)
        budget = self.store.row("SELECT * FROM budgets WHERE"
                                " fiscal_year = 2")
        self.assertIsNotNone(budget)
        self.assertEqual(budget["status"], "approved")
        self.assertIsNotNone(budget["approved_by"])
        # Forecast = trailing-12-month recorded revenue (the
        # seeded 300,000 plus genesis founder-era flows are
        # outside the window / not revenue reasons).
        self.assertGreaterEqual(budget["forecast_revenue_ncr"],
                                300000)
        import json
        allocations = json.loads(budget["allocations"])
        self.assertAlmostEqual(sum(allocations.values()),
                               budget["forecast_revenue_ncr"],
                               delta=len(allocations))

    def test_overdraft_formalised_as_explicit_debt(self):
        self._seed_revenue()
        # The bank lends only what it holds: capitalise it the
        # way Session 04's genesis does.
        self.store.transfer("SYS-MARKET", "SYS-BANK", 1000000,
                            "bank_capital", GM,
                            note="seeded bank capital",
                            transfer_key="seed:bank")
        # Drive the treasury into overdraft beyond the seeded
        # revenue, then close the year.
        self.store.transfer("SYS-CITY", "SYS-MARKET", 2000000,
                            "policy_spend", M1 * 12,
                            note="seeded overdraft",
                            transfer_key="seed:overdraft")
        self.assertLess(self.store.balance("SYS-CITY"), 0)
        policies.budget_pass(self.store, self.data, 12, M1 * 12)
        budget = self.store.row("SELECT * FROM budgets WHERE"
                                " fiscal_year = 2")
        self.assertIsNotNone(budget["borrowed_loan_id"])
        loan = self.store.row("SELECT * FROM loans WHERE loan_id"
                              " = ?", (budget["borrowed_loan_id"],))
        self.assertEqual(loan["borrower_character_id"], "SYS-CITY")
        self.assertGreater(loan["outstanding_ncr"], 0)
        debt = policies.public_debt(self.store)
        # No double counting: total = explicit + remaining
        # implicit overdraft.
        self.assertEqual(debt["explicit_loans_ncr"],
                         loan["outstanding_ncr"])
        self.assertEqual(
            debt["total_ncr"],
            debt["explicit_loans_ncr"]
            + debt["implicit_overdraft_ncr"])
        self.assertEqual(self.store.ledger_sum_check(), [])


class TestCivilService(unittest.TestCase):
    def setUp(self):
        self.store, self.data, self.ids = funded_world(adults=40)

    def test_recruitment_and_treasury_payroll(self):
        engineer = self.ids[5]
        self.store.insert(
            "education_records", record_id="ER-T1",
            character_id=engineer, institution_id="college",
            programme="civil_engineer", status="completed",
            attendance_rate=100, performance=90,
            parent_involvement=50, started_at_game_minutes=GM,
            completed_at_game_minutes=GM)
        out = admin.monthly_pass(self.store, self.data, rng(), 1,
                                 M1)
        self.assertTrue(out["hires"])
        hire = out["hires"][0]
        self.assertEqual(hire["character_id"], engineer)
        record = self.store.row("SELECT * FROM civil_service WHERE"
                                " character_id = ?", (engineer,))
        self.assertEqual(record["status"], "active")
        emp = self.store.row("SELECT * FROM employments WHERE"
                             " character_id = ? AND"
                             " ended_at_game_minutes IS NULL",
                             (engineer,))
        self.assertIn(emp["employer_character_id"],
                      gov.TREASURY_ACCOUNTS)
        before = self.store.balance(engineer)
        paid = gov.pay_government_wages(self.store, self.data, 2,
                                        M1 * 2)
        self.assertEqual(paid[emp["employment_id"]],
                         emp["wage_per_month"])
        self.assertEqual(self.store.balance(engineer),
                         before + emp["wage_per_month"])
        row = self.store.row(
            "SELECT * FROM economy_ledger WHERE transfer_key = ?",
            (f"gwage:{emp['employment_id']}:2",))
        self.assertIsNotNone(row)
        self.assertEqual(row["from_character_id"],
                         emp["employer_character_id"])


class TestLaws(unittest.TestCase):
    def setUp(self):
        self.store, self.data, self.ids = funded_world(adults=40)
        politics.update_opinion(self.store, self.data, 1, M1)
        politics.run_election(self.store, self.data, rng(), 1, M1)
        self.pm = _pm(self.store)

    def test_sales_tax_law_lifecycle_and_effect(self):
        default = justice.effective_sales_tax_percent(
            self.store, self.data)
        self.assertEqual(default, self.data.economy_config[
            "tax_rules"]["sales_tax_percent"])
        lid = justice.propose_law(self.store, self.data,
                                  "sales_tax", 8, self.pm, M1 * 2)
        positions = justice.debate_law(self.store, self.data, lid,
                                       M1 * 2)
        self.assertEqual(len(positions), 3)
        result = justice.vote_law(self.store, self.data, lid,
                                  M1 * 2)
        self.assertTrue(result["enacted"])
        law = self.store.row("SELECT * FROM laws WHERE law_id = ?",
                             (lid,))
        self.assertEqual(law["status"], "enacted")
        self.assertEqual(law["effective_month"], 3)
        # Not yet in force in month 2; in force from month 3.
        self.store.set_world(game_minutes=M1 * 2)
        self.assertEqual(justice.effective_sales_tax_percent(
            self.store, self.data), default)
        self.store.set_world(game_minutes=M1 * 3)
        self.assertEqual(justice.effective_sales_tax_percent(
            self.store, self.data), 8)

    def test_law_bounds_and_proposer_office(self):
        plain = next(c for c in self.ids
                     if not gov.offices_of(self.store, c))
        with self.assertRaises(PermissionError):
            justice.propose_law(self.store, self.data, "sales_tax",
                                5, plain, M1 * 2)
        with self.assertRaises(ValueError):
            justice.propose_law(self.store, self.data, "sales_tax",
                                40, self.pm, M1 * 2)  # bound is 10

    def test_wage_floor_and_migration_accessors(self):
        lid = justice.propose_law(self.store, self.data,
                                  "wage_floor", 10, self.pm, M1 * 2)
        result = justice.vote_law(self.store, self.data, lid,
                                  M1 * 2)
        self.assertTrue(result["enacted"])
        self.store.set_world(game_minutes=M1 * 3)
        self.assertEqual(justice.wage_floor_uplift_percent(
            self.store, self.data), 10)
        self.assertEqual(justice.apply_wage_floor(
            self.store, self.data, 10000), 11000)
        self.assertEqual(justice.migration_openness(
            self.store, self.data), 1.0)  # no migration law


class TestDecisionEngine(unittest.TestCase):
    def setUp(self):
        self.store, self.data, self.ids = funded_world(adults=40)
        self.pm = _pm(self.store)

    def test_measured_crisis_triggers_a_traced_policy(self):
        # A measured unemployment spike in the indicator record
        # (25% vs the 10% configured trigger) fires the engine.
        # By design the first firing OPENS A CITIZEN CONSULTATION
        # (Unit 05 with consequences); only when the recorded
        # consultation supports it does the engine propose +
        # approve the policy — traced in both logs.
        import json as _json
        self.store.insert(
            "economic_indicators", scope="national", month_index=1,
            metrics=_json.dumps({"unemployment_rate": 0.25,
                                 "poverty_rate": 0.0}),
            game_minutes=M1)
        out = policies.decision_engine_pass(self.store, self.data,
                                            rng(), 2, M1 * 2)
        made = [d for d in out["decisions"]
                if d["kind"] == "employment_programme"]
        self.assertTrue(made)
        self.assertEqual(made[0]["action"], "consultation")
        consultation = self.store.row(
            "SELECT * FROM citizen_feedback WHERE kind ="
            " 'consultation' AND status = 'open'")
        self.assertIsNotNone(consultation)
        # The consultation closes with measured support.
        self.store.execute(
            "UPDATE citizen_feedback SET status = 'closed',"
            " response = ? WHERE feedback_id = ?",
            (_json.dumps({"support": 12, "oppose": 3}),
             consultation["feedback_id"]))
        out2 = policies.decision_engine_pass(self.store, self.data,
                                             rng(), 3, M1 * 3)
        made2 = [d for d in out2["decisions"]
                 if d["kind"] == "employment_programme"]
        self.assertTrue(made2)
        self.assertEqual(made2[0]["action"], "approved")
        row = self.store.row("SELECT * FROM policies WHERE kind ="
                             " 'employment_programme'")
        self.assertIsNotNone(row)
        self.assertEqual(row["status"], "active")
        self.assertEqual(row["approved_by"], self.pm)
        log = self.store.row("SELECT * FROM decision_log WHERE"
                             " decision_type = 'government_policy'")
        self.assertIsNotNone(log)
        event = self.store.row("SELECT * FROM government_events"
                               " WHERE event_type ="
                               " 'policy_decision'")
        self.assertIsNotNone(event)

    def test_calm_indicators_leave_only_real_fact_triggers(self):
        # With calm indicators, no indicator-driven policy fires.
        # The one remaining trigger is a measured FACT: this
        # fixture employs no doctors at all (0 per 100 < the 0.8
        # trigger), so a health consultation opens — and nothing
        # is approved without consultation support.
        import json as _json
        self.store.insert(
            "economic_indicators", scope="national", month_index=1,
            metrics=_json.dumps({"unemployment_rate": 0.03,
                                 "poverty_rate": 0.05}),
            game_minutes=M1)
        out = policies.decision_engine_pass(self.store, self.data,
                                            rng(), 2, M1 * 2)
        self.assertEqual(
            out["decisions"],
            [{"kind": "health_investment",
              "action": "consultation"}])
        self.assertEqual(self.store.row(
            "SELECT COUNT(*) AS n FROM policies")["n"], 0)


if __name__ == "__main__":
    unittest.main()
