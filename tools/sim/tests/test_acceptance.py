"""Acceptance suite — the owner's 12 Session 01 criteria and the
audit's Unit AD criteria, tested at engine level:

- determinism: same seed -> identical summary (audit 2)
- save/restore identity: 15 days + restart + 15 days == 30 days
  uninterrupted (owner: data survives restart; audit 7)
- schedule coverage persisted for every agent (audit 4)
- economy reconciliation with economy_sim v2 for a single-adult
  household (audit 5)
- weather variety + coupling evidence (audit 6; coupling itself is
  unit-tested in test_scheduler)
- performance: 100 agents x 30 days well under 60 s (audit 8)
"""
import json
import os
import tempfile
import time
import unittest

from tools.sim.tests.common import data, employ, make_household
from tools.sim.engine import Simulation


def _tmp_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


def _run(path, population, days, seed="acc-seed"):
    sim = Simulation(path, seed=seed)
    sim.generate_population(population)
    sim.run_days(days)
    summary = sim.summary()
    sim.close()
    return summary


class TestDeterminism(unittest.TestCase):
    def test_same_seed_identical_summary(self):
        p1, p2 = _tmp_path(), _tmp_path()
        s1 = _run(p1, 100, 30)
        s2 = _run(p2, 100, 30)
        self.assertEqual(s1, s2)
        self.assertEqual(s1["ledger_mismatches"], 0)
        os.remove(p1)
        os.remove(p2)


class TestSaveRestore(unittest.TestCase):
    def test_restart_continuation_identical(self):
        pa, pb = _tmp_path(), _tmp_path()
        whole = _run(pa, 100, 30)
        sim = Simulation(pb, seed="acc-seed")
        sim.generate_population(100)
        sim.run_days(15)
        sim.close()
        sim = Simulation(pb, seed="acc-seed")  # reopen: the save loads
        sim.run_days(15)
        split = sim.summary()
        sim.close()
        self.assertEqual(whole, split)
        os.remove(pa)
        os.remove(pb)


class TestCoverageAndWeather(unittest.TestCase):
    def test_persisted_coverage_and_weather_variety(self):
        path = _tmp_path()
        sim = Simulation(path, seed="acc-seed")
        sim.generate_population(60)
        sim.run_days(10)
        rows = sim.store.rows(
            "SELECT blocks_json FROM instantiated_schedules"
            " WHERE day_index = 9")
        alive = sim.summary()["population_alive"]
        self.assertEqual(len(rows), alive)
        for r in rows:
            blocks = json.loads(r["blocks_json"])
            self.assertEqual(sum(b["end"] - b["start"] for b in blocks),
                             1440)
        presets = sim.store.rows("SELECT DISTINCT preset_id"
                                 " FROM daily_weather")
        self.assertGreaterEqual(len(presets), 3)
        sim.close()
        os.remove(path)


class TestReconciliation(unittest.TestCase):
    def test_single_adult_matches_economy_sim(self):
        """A lone teacher at entry tier, renting at the canonical
        tier-2 rent, must net exactly what economy_sim v2 computes
        for the same household over one month (the sim's scaling
        reduces to the reference model for one adult)."""
        d = data()
        path = _tmp_path()
        from tools.sim.persistence import Store
        from tools.sim.tests.common import make_person
        store = Store(path)
        store.init_world("test-seed")
        cid = make_person(store, age=30, first="Lone", last="Teacher")
        make_household(store, [cid], rent=4000)
        employ(store, d, cid, "teacher", tier=1)
        store.transfer("SYS-EMPLOYERS", cid, 20000, "seed", 480)
        store.set_world(population_generated=1)
        store.commit()
        store.close()

        sim = Simulation(path, seed="test-seed")
        sim.run_days(30)
        char = sim.store.row("SELECT balance_cached, died_at_game_minutes"
                             " FROM characters WHERE character_id = ?",
                             (cid,))
        self.assertIsNone(char["died_at_game_minutes"])
        delta = char["balance_cached"] - 20000
        wage_row = next(w for w in d.prices["wages_monthly"]
                        if w["profession_id"] == "teacher")
        expected = d.econ.simulate(d.prices, wage_row, "entry")["net"]
        self.assertLessEqual(abs(delta - expected), 2,
                             f"sim delta {delta} vs economy_sim {expected}")
        sim.close()
        os.remove(path)


class TestPerformance(unittest.TestCase):
    def test_100_agents_30_days_under_60s(self):
        path = _tmp_path()
        start = time.monotonic()
        _run(path, 100, 30)
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 60)
        os.remove(path)


if __name__ == "__main__":
    unittest.main()
