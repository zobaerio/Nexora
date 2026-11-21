"""Session 09 — Structured wage negotiation + supplier
selection by measured reliability.

Protocol proofs are direct calls with controlled state (the
candidate's leverage is set through their recorded needs; the
employer's cap is a learned parameter). Learning proof: after a
walk-away the employer's cap rises, and the SAME pair then
reaches agreement at a counter the old cap would have refused —
behaviour changed by a recorded outcome. Integration proof: the
Session 04 labour match hires through the protocol.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))

from tools.sim import agents as agents_mod  # noqa: E402
from tools.sim import business as business_mod  # noqa: E402
from tools.sim import labour as labour_mod  # noqa: E402
from tools.sim.engine import Simulation  # noqa: E402
from tools.sim.tests.common import rng  # noqa: E402

GM = 480
POSTED = 10000


def _tmp_path():
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


class NegotiationWorld(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = _tmp_path()
        cls.sim = Simulation(cls.path, seed="s09-negotiation")
        cls.sim.generate_population(60)
        cls.store = cls.sim.store
        cls.data = cls.sim.data

    @classmethod
    def tearDownClass(cls):
        cls.sim.close()
        os.remove(cls.path)

    def _business(self):
        b = self.store.row(
            "SELECT * FROM businesses WHERE closed_at_game_minutes"
            " IS NULL AND balance_cached > 1000000 LIMIT 1")
        if b is None:
            b = self.store.row(
                "SELECT * FROM businesses WHERE"
                " closed_at_game_minutes IS NULL LIMIT 1")
            self.store.transfer(
                "SYS-MARKET", None, 5000000, "test_fund", GM,
                to_business_id=b["business_id"],
                transfer_key=f"fund:{b['business_id']}")
            b = self.store.row("SELECT * FROM businesses WHERE"
                               " business_id = ?",
                               (b["business_id"],))
        return b

    def _candidate(self):
        # The same pool the labour match draws from: working-age,
        # not employed, not enrolled in college.
        from tools.sim import education as education_mod
        from tools.sim import identity as identity_mod
        now = self.store.world()["game_minutes"]
        cid = None
        for c in self.store.rows(
                "SELECT * FROM characters WHERE is_system = 0 AND"
                " died_at_game_minutes IS NULL ORDER BY"
                " character_id"):
            age = identity_mod.age_years(c["born_at_game_minutes"],
                                         now)
            if age < 18 or age >= 65:
                continue
            if self.store.row(
                    "SELECT 1 FROM employments WHERE character_id"
                    " = ? AND ended_at_game_minutes IS NULL",
                    (c["character_id"],)):
                continue
            if education_mod.college_enrolment(
                    self.store, c["character_id"]):
                continue
            cid = c["character_id"]
            break
        if cid is None:
            # Make one: end the most recent employment.
            emp = self.store.row(
                "SELECT * FROM employments WHERE"
                " ended_at_game_minutes IS NULL ORDER BY"
                " employment_id DESC LIMIT 1")
            self.store.execute(
                "UPDATE employments SET ended_at_game_minutes = ?"
                " WHERE employment_id = ?",
                (now, emp["employment_id"]))
            cid = emp["character_id"]
        # Maximum patience: the recorded financial need says this
        # citizen can afford to wait, so leverage is 0.5 exactly
        # (sole applicant -> score margin 0).
        self.store.execute("UPDATE needs_state SET financial = 100"
                           " WHERE character_id = ?", (cid,))
        self.store.commit()
        return cid

    def _vacancy(self, bid):
        return {"vacancy_id": "VC-TEST", "wage_per_month": POSTED,
                "employer_business_id": bid}

    def test_ask_accepted_at_default_cap(self):
        b = self._business()
        cid = self._candidate()
        wage, nid = agents_mod.negotiate_wage(
            self.store, self.data, self._vacancy(b["business_id"]),
            cid, 50.0, [50.0], GM)
        # premium = 0.12 * 0.5 * 1.0 = 0.06 <= default cap 0.06.
        self.assertEqual(wage, 10600)
        neg = self.store.row("SELECT * FROM negotiations WHERE"
                             " negotiation_id = ?", (nid,))
        self.assertEqual(neg["status"], "accepted")
        offers = self.store.rows(
            "SELECT * FROM negotiation_offers WHERE negotiation_id"
            " = ? ORDER BY round", (nid,))
        self.assertEqual([o["response"] for o in offers],
                         ["ask", "accept"])

    def test_counter_accepted_and_candidate_learns(self):
        b = self._business()
        cid = self._candidate()
        agents_mod.set_param(self.store, b["business_id"],
                             "wage_accept_cap", 0.04, (0.0, 0.15),
                             {"test": "cap"}, GM)
        agents_mod.set_param(self.store, cid, "wage_premium_factor",
                             1.0, (0.5, 1.2), {"test": "reset"}, GM)
        wage, nid = agents_mod.negotiate_wage(
            self.store, self.data, self._vacancy(b["business_id"]),
            cid, 50.0, [50.0], GM)
        # ask 10600 > cap counter 10400 >= floor 10300 -> conceded.
        self.assertEqual(wage, 10400)
        factor = agents_mod.get_param(self.store, cid,
                                      "wage_premium_factor", 1.0)
        self.assertAlmostEqual(factor, 0.97, places=6)
        learn = self.store.rows(
            "SELECT * FROM agent_learning WHERE owner_ref = ? AND"
            " param = 'wage_premium_factor'", (cid,))
        self.assertTrue(learn)

    def test_walkaway_teaches_employer_and_changes_outcome(self):
        b = self._business()
        cid = self._candidate()
        bid = b["business_id"]
        agents_mod.set_param(self.store, bid, "wage_accept_cap",
                             0.01, (0.0, 0.15), {"test": "cap"}, GM)
        agents_mod.set_param(self.store, cid, "wage_premium_factor",
                             0.6, (0.5, 1.2), {"test": "factor"}, GM)
        # premium = 0.12 * 0.5 * 0.6 = 0.036; floor = 1.018;
        # counter at cap 0.01 = 1.01 < floor -> walk-away.
        wage, nid = agents_mod.negotiate_wage(
            self.store, self.data, self._vacancy(bid), cid, 50.0,
            [50.0], GM)
        self.assertIsNone(wage)
        neg = self.store.row("SELECT * FROM negotiations WHERE"
                             " negotiation_id = ?", (nid,))
        self.assertEqual(neg["status"], "walked_away")
        cap = agents_mod.get_param(self.store, bid,
                                   "wage_accept_cap", 0.06)
        self.assertAlmostEqual(cap, 0.02, places=6)
        # Same pair, same candidate state: the learned cap (0.02)
        # now counters at 1.02 >= floor 1.018 -> agreement. The
        # recorded outcome changed the behaviour.
        wage2, nid2 = agents_mod.negotiate_wage(
            self.store, self.data, self._vacancy(bid), cid, 50.0,
            [50.0], GM)
        self.assertEqual(wage2, 10200)
        neg2 = self.store.row("SELECT * FROM negotiations WHERE"
                              " negotiation_id = ?", (nid2,))
        self.assertEqual(neg2["status"], "accepted")

    def test_labour_match_hires_through_negotiation(self):
        b = self._business()
        cid = self._candidate()
        bid = b["business_id"]
        agents_mod.set_param(self.store, bid, "wage_accept_cap",
                             0.15, (0.0, 0.15), {"test": "cap"}, GM)
        # Make the candidate the strongest applicant for a
        # construction vacancy: max the profession's skills.
        pid = "construction_worker"
        for skill in self.data.professions[pid]["primary_skills"]:
            self.store.execute(
                "INSERT OR REPLACE INTO character_skills"
                " (character_id, skill_id, level, experience)"
                " VALUES (?, ?, 95, 4750)", (cid, skill))
        vid = labour_mod._post_vacancy(
            self.store, employer_kind="business", business_id=bid,
            profession_id=pid,
            city_id=business_mod.business_city(self.store,
                                               self.data, b),
            wage=POSTED, month_index=1, game_minutes=GM)
        self.store.commit()
        hires = labour_mod.match_vacancies(
            self.store, self.data, rng("s09-negotiation"), 1, GM)
        mine = [h for h in hires if h["vacancy_id"] == vid]
        self.assertTrue(mine)
        emp = self.store.row(
            "SELECT * FROM employments WHERE character_id = ? AND"
            " ended_at_game_minutes IS NULL", (cid,))
        self.assertIsNotNone(emp)
        negs = self.store.rows(
            "SELECT * FROM negotiations WHERE vacancy_id = ?",
            (vid,))
        self.assertTrue(negs)
        self.assertEqual(negs[0]["status"], "accepted")
        import json
        final = json.loads(negs[0]["final_terms"])
        self.assertEqual(emp["wage_per_month"],
                         final["wage_per_month"])
        self.assertGreaterEqual(emp["wage_per_month"], POSTED)


class TestSupplierReliability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = _tmp_path()
        cls.sim = Simulation(cls.path, seed="s09-suppliers")
        cls.sim.generate_population(60)
        cls.store = cls.sim.store
        cls.data = cls.sim.data

    @classmethod
    def tearDownClass(cls):
        cls.sim.close()
        os.remove(cls.path)

    def test_reliability_from_recorded_orders(self):
        from tools.sim import agents as a
        seller = self.store.row(
            "SELECT business_id FROM businesses LIMIT 1")[
            "business_id"]
        self.assertEqual(a.supplier_reliability(
            self.store, self.data, seller, "manufactured_goods", 3),
            0.0)
        a.record_supply_order(
            self.store, {"buyer": "BZ-X", "seller": seller,
                         "good_id": "manufactured_goods",
                         "units": 25.0, "amount_ncr": 5000}, 3, GM)
        self.assertEqual(a.supplier_reliability(
            self.store, self.data, seller, "manufactured_goods", 3),
            25.0)
        self.assertTrue(a.supplier_reliable(
            self.store, self.data, seller, "manufactured_goods", 3))
        # Outside the trailing window the record no longer counts.
        self.assertEqual(a.supplier_reliability(
            self.store, self.data, seller, "manufactured_goods", 9),
            0.0)


if __name__ == "__main__":
    unittest.main()
