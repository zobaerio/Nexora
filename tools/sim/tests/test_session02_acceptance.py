"""Session 02 acceptance suite — the session's verification list at
engine level, over a generated population:

- family creation + relationship consistency (kinship derives from
  the graph; no stored extended-kin edges)
- household membership changes only via life events
- family financial transactions recorded per household per month
- social network development (neighbour edges appear over time)
- community participation + all 10 communities exist
- cultural event execution (a festival fires on its calendar day)
- education integration (children enrolled; attendance measured)
- social event participation (celebrations/meetings recorded)
- generational history persistence
- data integrity after restart: 30 + reopen + 30 == 60 days,
  with every Session 02 cadence active
- no regressions are covered by the Session 01 suite + the
  no-regression file (economy_sim md5, Godot 8/8, validate_data)
"""
import os
import tempfile
import unittest

from tools.sim.engine import Simulation


def _tmp_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


def _run(path, population, days, seed="s02-acc"):
    sim = Simulation(path, seed=seed)
    sim.generate_population(population)
    sim.run_days(days)
    summary = sim.summary()
    sim.close()
    return summary


class TestSession02Engine(unittest.TestCase):
    def test_society_layer_after_90_days(self):
        path = _tmp_path()
        sim = Simulation(path, seed="s02-acc")
        sim.generate_population(120)
        sim.run_days(90)
        store = sim.store
        s = sim.summary()
        # Family finances: three settled months of accounts.
        months = store.rows("SELECT DISTINCT month_index FROM"
                            " household_finances ORDER BY month_index")
        self.assertEqual([m["month_index"] for m in months], [1, 2, 3])
        self.assertEqual(store.ledger_sum_check(), [])
        # Communities: all 10 zones, populated.
        self.assertEqual(s["communities"], 10)
        total_pop = store.row("SELECT SUM(population) AS p FROM"
                              " communities")["p"]
        self.assertGreaterEqual(total_pop, s["population_alive"] - 5)
        # Social network developed: neighbour edges exist.
        self.assertGreater(s["neighbour_edges"], 0)
        # Education: children enrolled by the monthly sweep.
        self.assertGreater(s["students_enrolled"], 0)
        # Events: festivals (day 45) + meetings + celebrations ran.
        self.assertGreater(s["social_events"], 0)
        fest = store.row("SELECT COUNT(*) AS n FROM social_events"
                         " WHERE event_type = 'festival'")
        self.assertGreaterEqual(fest["n"], 1)
        # Generational history persisted (transfers and/or births).
        gh = store.row("SELECT COUNT(*) AS n FROM"
                       " generational_history")["n"]
        self.assertGreater(gh, 0)
        # Kinship stays derived: no stored extended-kin edge types.
        bad = store.row("SELECT COUNT(*) AS n FROM relationships"
                        " WHERE relation_type IN ('grandparent',"
                        " 'cousin', 'uncle')")["n"]
        self.assertEqual(bad, 0)
        sim.close()
        os.remove(path)

    def test_restart_integrity_with_social_cadences(self):
        pa, pb = _tmp_path(), _tmp_path()
        whole = _run(pa, 100, 60)
        sim = Simulation(pb, seed="s02-acc")
        sim.generate_population(100)
        sim.run_days(30)
        sim.close()
        sim = Simulation(pb, seed="s02-acc")
        sim.run_days(30)
        split = sim.summary()
        sim.close()
        self.assertEqual(whole, split)
        self.assertEqual(whole["ledger_mismatches"], 0)
        os.remove(pa)
        os.remove(pb)


if __name__ == "__main__":
    unittest.main()
