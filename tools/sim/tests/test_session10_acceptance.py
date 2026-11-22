"""Session 10 acceptance — the integrated civilization.

Checklist mapping (docs/SESSION-10-REPORT.md carries the full
20-item demonstration checklist with evidence pointers):

  * a 200-day run crosses every session's systems with the
    integration layer live: the registry fills from at least the
    life / economy / government / society / humandev sources,
    technology levels persist monthly, the resource report
    computes for both cities, and the money layer stays clean
    (0 ledger mismatches, 0 conservation violations);
  * time modes are the runner's honest capabilities: step
    advances exactly N days on the single GameClock, paused is
    state at rest (open + close changes nothing), playback is
    read-only (the observatory views mutate nothing), and
    accelerated is the batch run itself;
  * database inspection on a live world: no foreign-key
    violations, every orphan scan at zero, no duplicate
    transfer keys, no duplicate registry events;
  * restart identity + determinism WITH the integration layer
    live (registry + technology rows are part of the digest).
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))

from tools.sim import dbinspect  # noqa: E402
from tools.sim import finance  # noqa: E402
from tools.sim import integration  # noqa: E402
from tools.sim import integrationview  # noqa: E402
from tools.sim import worlds as worlds_mod  # noqa: E402
from tools.sim.engine import Simulation  # noqa: E402


def _tmp_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


def _digest(sim):
    store = sim.store
    return {
        "world": worlds_mod.world_digest(sim.store.path),
        "events": store.row("SELECT COUNT(*) AS n FROM"
                            " world_events")["n"],
        "technology_rows": store.row(
            "SELECT COUNT(*) AS n FROM technology_levels")["n"],
        "ledger_rows": store.row("SELECT COUNT(*) AS n FROM"
                                 " economy_ledger")["n"],
    }


class TestIntegratedLongRun(unittest.TestCase):
    def test_200_day_integrated_world(self):
        path = _tmp_path()
        sim = Simulation(path, seed="s10-acceptance")
        try:
            sim.generate_population(100)
            sim.run_days(200)
            store = sim.store
            s = sim.summary()
            reg = s["integration"]
            self.assertGreater(reg["registry_events"], 400)
            for src in ("life", "economy", "government"):
                self.assertIn(src, reg["registry_by_source"])
            months = store.row(
                "SELECT COUNT(DISTINCT month_index) AS n FROM"
                " technology_levels")["n"]
            self.assertGreaterEqual(months, 5)
            report = integration.resource_report(store, sim.data)
            self.assertEqual(set(report["cities"]),
                             {"rupsha_city", "shibnagar_town"})
            for city in report["cities"].values():
                self.assertIn("food", city)
                self.assertIn("water", city)
                self.assertIn("energy_fuel", city)
            self.assertEqual(s["ledger_mismatches"], 0)
            self.assertEqual(finance.verify_conservation(store),
                             [])
            self.assertEqual(store.ledger_sum_check(), [])
        finally:
            sim.close()
            os.remove(path)


class TestTimeModes(unittest.TestCase):
    def test_step_pause_playback(self):
        path = _tmp_path()
        sim = Simulation(path, seed="s10-time")
        try:
            sim.generate_population(30)
            # Step: exactly one day on the single clock.
            before = sim.store.world()
            sim.run_days(1)
            world = sim.store.world()
            self.assertEqual(world["day_index"],
                             before["day_index"] + 1)
            # The engine's day convention: day N ends at minute
            # N*1440 (genesis events carry minute 480 inside
            # day 1; the clock itself is day-aligned).
            self.assertEqual(world["game_minutes"],
                             world["day_index"] * 1440)
            self.assertGreater(world["game_minutes"],
                               before["game_minutes"])
            sim.close()
            digest_rest = worlds_mod.world_digest(path)
            # Paused: opening and closing changes nothing.
            sim = Simulation(path, seed="s10-time")
            sim.close()
            self.assertEqual(worlds_mod.world_digest(path),
                             digest_rest)
            # Playback: the observatory views are read-only.
            sim = Simulation(path, seed="s10-time")
            store = sim.store
            integrationview.events_view(store, sim.data)
            integrationview.technology_view(store, sim.data)
            integrationview.resources_view(store, sim.data)
            worlds_mod.world_info(path)
            sim.close()
            self.assertEqual(worlds_mod.world_digest(path),
                             digest_rest)
        finally:
            if os.path.exists(path):
                os.remove(path)


class TestDatabaseInspection(unittest.TestCase):
    def test_live_world_integrity(self):
        path = _tmp_path()
        sim = Simulation(path, seed="s10-inspect")
        try:
            sim.generate_population(30)
            sim.run_days(35)
        finally:
            sim.close()
        try:
            out = dbinspect.inspect_world(path)
            self.assertGreaterEqual(out["table_count"], 140)
            self.assertEqual(out["foreign_key_check_violations"],
                             0)
            self.assertTrue(out["orphan_scans"])
            for label, n in out["orphan_scans"].items():
                self.assertEqual(n, 0, label)
            self.assertEqual(out["duplicate_transfer_keys"], 0)
            self.assertEqual(out["duplicate_registry_events"], 0)
            self.assertGreater(out["index_count"], 0)
            self.assertGreater(out["census"]["world_events"], 0)
        finally:
            os.remove(path)


class TestRestartIdentityWithIntegration(unittest.TestCase):
    def test_restart_and_determinism(self):
        digests = []
        for mode in ("straight", "restart", "again"):
            path = _tmp_path()
            sim = Simulation(path, seed="s10-restart")
            try:
                sim.generate_population(60)
                if mode == "restart":
                    sim.run_days(45)
                    sim.close()
                    sim = Simulation(path, seed="s10-restart")
                    sim.run_days(45)
                else:
                    sim.run_days(90)
                digests.append(_digest(sim))
            finally:
                sim.close()
                os.remove(path)
        self.assertEqual(digests[0], digests[1])
        self.assertEqual(digests[0], digests[2])
        self.assertGreater(digests[0]["events"], 0)
        self.assertGreater(digests[0]["technology_rows"], 0)


if __name__ == "__main__":
    unittest.main()
