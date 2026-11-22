"""Session 10 — the unified event registry: an append-only index
written alongside the existing history tables. The sources are
never rewritten; re-syncing never duplicates; deferred sources
(elections, construction, agreements, policies) are indexed only
once their records are final."""
import hashlib
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))

from tools.sim import integration  # noqa: E402
from tools.sim.engine import Simulation  # noqa: E402
from tools.sim.tests.common import (data, make_household,  # noqa: E402
                                    make_person, make_store, rng)

GM = 480


def _digest(rows):
    h = hashlib.sha256()
    for r in rows:
        h.update(repr(tuple(r)).encode())
    return h.hexdigest()


class TestRegistrySync(unittest.TestCase):
    def setUp(self):
        self.store = make_store()
        self.d = data()
        r = rng()
        self.cid = make_person(self.store, age=30, sex="female",
                               first="Reg", last="Test",
                               game_minutes=GM, r=r)
        make_household(self.store, [self.cid], game_minutes=GM)
        self.store.insert(
            "life_events", event_id="LE-T1", character_id=self.cid,
            event_type="birth", game_minutes=GM, details="{}")
        self.store.insert(
            "life_events", event_id="LE-T2", character_id=self.cid,
            event_type="mystery_type", game_minutes=GM, details="{}")
        self.store.insert(
            "social_events", event_id="SE-T1", event_type="festival",
            zone_id=None, participant_ids="[]", outcome="{}",
            game_minutes=GM)
        self.store.insert(
            "business_events", event_id="BE-T1",
            business_id="BIZ-T1", event_type="registered",
            game_minutes=GM, details="{}")
        self.store.insert(
            "business_events", event_id="BE-T2",
            business_id="BIZ-T1", event_type="distress",
            game_minutes=GM, details="{}")
        self.store.insert(
            "government_events", event_id="GE-T1",
            event_type="law_enacted", actor_character_id=None,
            game_minutes=GM, details="{}")
        self.store.commit()

    def test_setup_is_idempotent(self):
        self.assertFalse(integration.is_setup(self.store))
        first = integration.setup_integration(self.store, self.d)
        self.assertEqual(first, {"integration": "ready"})
        self.assertTrue(integration.is_setup(self.store))
        second = integration.setup_integration(self.store, self.d)
        self.assertEqual(second, {"integration": "already set up"})
        self.assertTrue(integration.is_setup(self.store))

    def test_sync_maps_types_and_skips_noise(self):
        integration.setup_integration(self.store, self.d)
        out = integration.sync_event_registry(self.store, self.d)
        self.assertEqual(out["life_events"], 2)
        self.assertEqual(out["social_events"], 1)
        # 'registered' maps; 'distress' is deliberately not a
        # major event class and is skipped.
        self.assertEqual(out["business_events"], 1)
        self.assertEqual(out["government_events"], 1)
        types = {r["event_type"] for r in self.store.rows(
            "SELECT event_type FROM world_events")}
        self.assertIn("birth", types)
        # An unlisted life type is still indexed — the registry
        # preserves the source vocabulary rather than dropping
        # or renaming what it does not know.
        self.assertIn("mystery_type", types)
        self.assertIn("business_formation", types)
        fest = self.store.row(
            "SELECT * FROM world_events WHERE source_table ="
            " 'social_events'")
        self.assertEqual(fest["event_type"], "festival")
        self.assertEqual(fest["source"], "society")

    def test_resync_never_duplicates(self):
        integration.setup_integration(self.store, self.d)
        integration.sync_event_registry(self.store, self.d)
        n = self.store.row("SELECT COUNT(*) AS n FROM"
                           " world_events")["n"]
        out = integration.sync_event_registry(self.store, self.d)
        self.assertTrue(all(v == 0 for v in out.values()))
        self.assertEqual(self.store.row(
            "SELECT COUNT(*) AS n FROM world_events")["n"], n)

    def test_sources_are_never_rewritten(self):
        before = {}
        for t in ("life_events", "social_events", "business_events",
                  "government_events"):
            rows = self.store.rows(f"SELECT * FROM {t}")
            before[t] = (len(rows), _digest(rows))
        integration.setup_integration(self.store, self.d)
        integration.sync_event_registry(self.store, self.d)
        integration.sync_event_registry(self.store, self.d)
        for t, (n, h) in before.items():
            rows = self.store.rows(f"SELECT * FROM {t}")
            self.assertEqual((len(rows), _digest(rows)), (n, h), t)


class TestDeferredSources(unittest.TestCase):
    def setUp(self):
        self.store = make_store()
        self.d = data()
        integration.setup_integration(self.store, self.d)

    def test_election_indexed_only_when_held(self):
        self.store.insert(
            "elections", election_id="EL-T1", country_id="BD",
            month_index=1, status="scheduled", game_minutes=None)
        self.store.commit()
        out = integration.sync_event_registry(self.store, self.d)
        self.assertEqual(out["deferred"], 0)
        self.store.execute(
            "UPDATE elections SET game_minutes = ?, status ="
            " 'completed', winner_party_id = 'P1' WHERE"
            " election_id = 'EL-T1'", (GM,))
        self.store.commit()
        out = integration.sync_event_registry(self.store, self.d)
        self.assertEqual(out["deferred"], 1)
        row = self.store.row("SELECT * FROM world_events WHERE"
                             " source_table = 'elections'")
        self.assertEqual(row["event_type"], "election")
        # The registry row's own status is 'recorded' (it is an
        # index entry); the election's lifecycle lives in the
        # source table, which is never rewritten.
        self.assertEqual(row["status"], "recorded")

    def test_construction_indexed_only_when_completed(self):
        self.store.insert(
            "construction_projects", project_id="CP-T1",
            city_id="rupsha_city", kind="new_build",
            status="active")
        self.store.commit()
        out = integration.sync_event_registry(self.store, self.d)
        self.assertEqual(out["deferred"], 0)
        self.store.execute(
            "UPDATE construction_projects SET status ="
            " 'completed', completed_day = 1,"
            " updated_at_game_minutes = ? WHERE"
            " project_id = 'CP-T1'", (GM,))
        self.store.commit()
        out = integration.sync_event_registry(self.store, self.d)
        self.assertEqual(out["deferred"], 1)
        row = self.store.row("SELECT * FROM world_events WHERE"
                             " source_table ="
                             " 'construction_projects'")
        self.assertEqual(row["event_type"],
                         "construction_completed")
        self.assertEqual(row["city_id"], "rupsha_city")

    def test_policy_and_agreement_gates(self):
        self.store.insert(
            "policies", policy_id="POL-T1", kind="welfare_support",
            title="T", status="proposed")
        self.store.insert(
            "agreements", agreement_id="AG-T1", partner_id="EXT",
            kind="trade", status="proposed")
        self.store.commit()
        out = integration.sync_event_registry(self.store, self.d)
        self.assertEqual(out["deferred"], 0)
        self.store.execute("UPDATE policies SET status = 'active'"
                           " WHERE policy_id = 'POL-T1'")
        self.store.execute("UPDATE agreements SET status = 'active'"
                           " WHERE agreement_id = 'AG-T1'")
        self.store.commit()
        out = integration.sync_event_registry(self.store, self.d)
        self.assertEqual(out["deferred"], 2)


class TestRegistryInLiveWorld(unittest.TestCase):
    def test_live_world_registry_is_complete_for_append_sources(
            self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(path)
        sim = Simulation(path, seed="s10-registry")
        try:
            sim.generate_population(40)
            sim.run_days(35)
            s = sim.summary()
            reg = s["integration"]
            self.assertGreater(reg["registry_events"], 0)
            by_source = reg["registry_by_source"]
            for src in ("life", "economy", "government"):
                self.assertIn(src, by_source)
            store = sim.store
            # Append sources with total mappings are complete:
            # every life/government history row is indexed.
            for table in ("life_events", "government_events"):
                total = store.row(
                    f"SELECT COUNT(*) AS n FROM {table}")["n"]
                indexed = store.row(
                    "SELECT COUNT(*) AS n FROM world_events WHERE"
                    " source_table = ?", (table,))["n"]
                self.assertEqual(indexed, total, table)
            # The month-1 election reached the registry.
            self.assertGreaterEqual(store.row(
                "SELECT COUNT(*) AS n FROM world_events WHERE"
                " event_type = 'election'")["n"], 1)
            self.assertEqual(store.ledger_sum_check(), [])
        finally:
            sim.close()
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
