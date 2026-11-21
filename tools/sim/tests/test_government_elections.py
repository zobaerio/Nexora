"""Session 05 Units 03+04+05 — Political Parties, Elections,
Citizen Participation: measured opinion, one immutable ballot
per voter, deterministic counting, government formation and
peaceful transfer of power."""
import sqlite3
import unittest

from tools.sim import government as gov
from tools.sim import politics
from tools.sim.tests.common import make_person, rng
from tools.sim.tests.govcommon import GM, funded_world

ELECTION_GM = 43200  # end of month 1


class TestParties(unittest.TestCase):
    def setUp(self):
        self.store, self.data, self.ids = funded_world(adults=40)

    def test_parties_registered_with_citizen_leaders(self):
        parties = self.store.rows("SELECT * FROM parties")
        self.assertEqual(len(parties), 3)
        for p in parties:
            self.assertIn(p["leader_character_id"], self.ids)
            members = politics.members_of(self.store, p["party_id"])
            self.assertGreaterEqual(len(members), 1)
            self.assertTrue(all(m["character_id"] in self.ids
                                for m in members))
            # Ideology is data: a 5-dimension stance vector.
            import json
            stances = json.loads(p["stances"])
            self.assertEqual(set(stances), {
                "economy", "welfare", "services", "development",
                "law_order"})

    def test_party_funding_through_ledger(self):
        # Founders who held the seed money contributed it; every
        # party balance is exactly its ledger sum.
        self.assertEqual(self.store.ledger_sum_check(), [])
        for p in self.store.rows("SELECT * FROM parties"):
            rows = self.store.rows(
                "SELECT * FROM economy_ledger WHERE"
                " to_character_id = ? AND reason_code ="
                " 'party_funding'", (p["party_id"],))
            self.assertEqual(
                sum(r["amount"] for r in rows),
                self.store.balance(p["party_id"]))

    def test_opinion_is_measured_and_snapshotted(self):
        out = politics.update_opinion(self.store, self.data, 1,
                                      ELECTION_GM)
        self.assertIsNotNone(out)
        rows = self.store.rows("SELECT * FROM citizen_opinion")
        self.assertEqual(len(rows), len(self.ids))
        import json
        for r in rows:
            components = json.loads(r["components"])
            self.assertIn("income", components)
            self.assertTrue(0 <= r["approval"] <= 100)
        snap = self.store.row("SELECT * FROM opinion_snapshots"
                              " WHERE month_index = 1")
        self.assertIsNotNone(snap)
        self.assertEqual(snap["respondents"], len(self.ids))


class TestElection(unittest.TestCase):
    def setUp(self):
        self.store, self.data, self.ids = funded_world(adults=40)
        politics.update_opinion(self.store, self.data, 1,
                                ELECTION_GM)
        self.result = politics.run_election(
            self.store, self.data, rng(), 1, ELECTION_GM)

    def test_full_cycle_forms_government(self):
        self.assertIsNotNone(self.result)
        e = self.store.row("SELECT * FROM elections")
        self.assertEqual(e["status"], "formed")
        self.assertIn(e["winner_party_id"],
                      {"PTY-JANATA", "PTY-OIKYA", "PTY-SHANTI"})
        ballots = self.store.row("SELECT COUNT(*) AS n FROM"
                                 " ballots")["n"]
        self.assertEqual(ballots, e["turnout"])
        self.assertLessEqual(ballots, e["eligible"])
        # Seats: every ballot counted; seats allocated for the
        # constituency that voted (all fixture citizens live in
        # Rupsha — Shibnagar's seats stay unfilled with no
        # voters, which is the honest outcome).
        import json
        results = json.loads(e["results"])
        total_seats = sum(results["seats"].values())
        total_votes = sum(results["totals"].values())
        self.assertEqual(total_votes, ballots)
        self.assertEqual(total_seats, 12)
        # The winner governs: the PM is of the winning party.
        self.assertEqual(politics.governing_party(self.store),
                         e["winner_party_id"])
        mps = self.store.rows(
            "SELECT * FROM offices WHERE institution_id ="
            " 'GOV-PARLIAMENT' AND title = 'mp' AND status ="
            " 'active'")
        self.assertGreaterEqual(len(mps), 1)
        self.assertLessEqual(len(mps), total_seats)

    def test_recount_agrees(self):
        e = self.store.row("SELECT * FROM elections")
        again = politics.recount(self.store, e["election_id"])
        self.assertTrue(again["agree"])
        self.assertEqual(again["ballots"], e["turnout"])

    def _open_election(self):
        eid = self.store.next_id("EL", "elections", "election_id")
        self.store.insert(
            "elections", election_id=eid, country_id="bangladesh",
            month_index=2, status="voting", rules="{}",
            game_minutes=ELECTION_GM)
        return eid

    def test_duplicate_ballot_impossible(self):
        eid = self._open_election()
        voter = self.ids[0]
        politics.cast_ballot(self.store, self.data, eid, voter,
                             "PTY-JANATA", ELECTION_GM + 60)
        with self.assertRaises(ValueError):
            politics.cast_ballot(self.store, self.data, eid, voter,
                                 "PTY-OIKYA", ELECTION_GM + 120)
        rows = self.store.rows("SELECT * FROM ballots WHERE"
                               " election_id = ?", (eid,))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["party_id"], "PTY-JANATA")

    def test_ballots_are_immutable(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.execute("UPDATE ballots SET party_id ="
                               " 'PTY-OIKYA'")
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.execute("DELETE FROM ballots")

    def test_underage_cannot_vote(self):
        kid = make_person(self.store, age=17, first="Kid",
                          last="Test", game_minutes=ELECTION_GM,
                          r=rng())
        eid = self._open_election()
        with self.assertRaises(ValueError):
            politics.cast_ballot(self.store, self.data, eid, kid,
                                 "PTY-JANATA", ELECTION_GM + 60)
        self.assertEqual(self.store.row(
            "SELECT COUNT(*) AS n FROM ballots WHERE"
            " character_id = ?", (kid,))["n"], 0)

    def test_second_election_transfers_power_peacefully(self):
        first_pm = gov.office_holder(
            self.store, "prime_minister",
            "GOV-PM")["holder_character_id"]
        first_election = self.store.row(
            "SELECT * FROM elections")["election_id"]
        # Month 13: the term ends, a second election runs.
        politics.update_opinion(self.store, self.data, 13,
                                ELECTION_GM * 13)
        result2 = politics.run_election(
            self.store, self.data, rng(), 13, ELECTION_GM * 13)
        self.assertIsNotNone(result2)
        elections = self.store.rows("SELECT * FROM elections"
                                    " ORDER BY election_id")
        self.assertEqual(len(elections), 2)
        # The first election's records are untouched.
        e1 = elections[0]
        self.assertEqual(e1["election_id"], first_election)
        self.assertEqual(e1["status"], "formed")
        b1 = self.store.row("SELECT COUNT(*) AS n FROM ballots"
                            " WHERE election_id = ?",
                            (first_election,))["n"]
        self.assertGreater(b1, 0)
        # Judiciary and audit offices are NOT swept by the
        # transfer: the chief justice seated at genesis remains.
        cj = gov.office_holder(self.store, "chief_justice",
                               "GOV-COURT")
        self.assertIsNotNone(cj["holder_character_id"])
        # A government exists after the transfer.
        self.assertIsNotNone(politics.governing_party(self.store))
        _ = first_pm  # may or may not be re-elected; both legal


if __name__ == "__main__":
    unittest.main()
