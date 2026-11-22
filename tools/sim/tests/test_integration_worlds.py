"""Session 10 — world registry, multi-world isolation,
checkpoints, duplication and crash recovery.

Isolation is proven by digest: a world's digest covers its living
population (identity + balance + death), its ledger (row count +
amount sum) and its clock. Advancing one world must leave another
world's digest untouched; restoring a checkpoint must reproduce
the checkpointed digest exactly; a process killed mid-run must
reopen on the last committed day with a clean ledger, and
continuing it must land on the same digest as the uninterrupted
twin (the Session 01 restart-identity property, now under kill
conditions)."""
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))

from tools.sim import worlds as worlds_mod  # noqa: E402
from tools.sim.engine import Simulation  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                    "..", "..", ".."))


def _tmp_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


def _build(path, seed, population, days):
    sim = Simulation(path, seed=seed)
    sim.generate_population(population)
    if days:
        sim.run_days(days)
    sim.close()


def _day_index(path):
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return conn.execute(
            "SELECT day_index FROM world_state WHERE id = 1").fetchone()[0]
    finally:
        conn.close()


class TestRegistryAndInfo(unittest.TestCase):
    def test_register_list_info(self):
        reg = _tmp_path() + ".json"
        a, b = _tmp_path(), _tmp_path()
        try:
            _build(a, "s10-reg-a", 30, 5)
            _build(b, "s10-reg-b", 30, 5)
            ea = worlds_mod.register_world(reg, a, "World A")
            eb = worlds_mod.register_world(reg, b, "World B")
            self.assertEqual(ea["world_id"], "WORLD-0001")
            self.assertEqual(eb["world_id"], "WORLD-0002")
            self.assertEqual(ea["seed"], "s10-reg-a")
            again = worlds_mod.register_world(reg, a, "World A2")
            self.assertEqual(again["world_id"], "WORLD-0001")
            entries = worlds_mod.list_worlds(reg)
            self.assertEqual(len(entries), 2)
            info = worlds_mod.world_info(a)
            self.assertEqual(info["day_index"], 5)
            # Genesis created the 30 residents; births since
            # then only add.
            self.assertGreaterEqual(info["population_alive"], 30)
            self.assertGreater(info["ledger_rows"], 0)
        finally:
            for p in (a, b, reg):
                if os.path.exists(p):
                    os.remove(p)


class TestIsolation(unittest.TestCase):
    def test_advancing_one_world_leaves_the_other_identical(self):
        a, b = _tmp_path(), _tmp_path()
        try:
            _build(a, "s10-iso-a", 30, 35)
            _build(b, "s10-iso-b", 30, 35)
            digest_b = worlds_mod.world_digest(b)
            digest_a = worlds_mod.world_digest(a)
            _build(a, "s10-iso-a", 30, 30)  # resume + advance A
            self.assertEqual(worlds_mod.world_digest(b), digest_b)
            self.assertNotEqual(worlds_mod.world_digest(a),
                                digest_a)
            self.assertEqual(_day_index(b), 35)
            self.assertEqual(_day_index(a), 65)
        finally:
            for p in (a, b):
                os.remove(p)


class TestCheckpoints(unittest.TestCase):
    def test_checkpoint_restore_and_duplicate(self):
        c = _tmp_path()
        dup = _tmp_path()
        try:
            _build(c, "s10-ckpt", 40, 35)
            digest_35 = worlds_mod.world_digest(c)
            alive_35 = worlds_mod.world_info(c)[
                "population_alive"]
            manifest = worlds_mod.create_checkpoint(c, "base")
            self.assertEqual(manifest["day_index"], 35)
            self.assertEqual(manifest["population_alive"],
                             alive_35)
            self.assertTrue(manifest["ledger_reconciled"])
            self.assertEqual(manifest["digest"], digest_35)
            self.assertEqual(manifest["code_version"],
                             worlds_mod.CODE_VERSION)
            listed = worlds_mod.list_checkpoints(c)
            self.assertEqual(
                [m["name"] for m in listed["checkpoints"]],
                ["base"])
            _build(c, "s10-ckpt", 40, 30)  # advance to day 65
            self.assertNotEqual(worlds_mod.world_digest(c),
                                digest_35)
            worlds_mod.restore_checkpoint(c, "base")
            self.assertEqual(worlds_mod.world_digest(c), digest_35)
            self.assertEqual(_day_index(c), 35)
            # Duplication from the checkpoint: an independent
            # world at day 35 that can advance on its own.
            worlds_mod.duplicate_world(c, dup,
                                       from_checkpoint="base")
            self.assertEqual(_day_index(dup), 35)
            _build(dup, "s10-ckpt", 40, 5)
            self.assertEqual(_day_index(dup), 40)
            self.assertEqual(worlds_mod.world_digest(c), digest_35)
            with self.assertRaises(FileExistsError):
                worlds_mod.duplicate_world(c, dup)
            with self.assertRaises(FileNotFoundError):
                worlds_mod.restore_checkpoint(c, "nope")
        finally:
            for p in (c, dup):
                if os.path.exists(p):
                    os.remove(p)
            ckdir = c + ".checkpoints"
            if os.path.isdir(ckdir):
                for f in os.listdir(ckdir):
                    os.remove(os.path.join(ckdir, f))
                os.rmdir(ckdir)


class TestCrashRecovery(unittest.TestCase):
    def test_kill_mid_run_recovers_and_matches_twin(self):
        twin, victim = _tmp_path(), _tmp_path()
        try:
            _build(twin, "s10-crash", 40, 65)
            digest_twin = worlds_mod.world_digest(twin)
            _build(victim, "s10-crash", 40, 35)
            env = dict(os.environ)
            env["TMPDIR"] = os.path.expanduser("~/tmp-tests")
            proc = subprocess.Popen(
                [sys.executable, "-m", "tools.sim", "--db", victim,
                 "--days", "300"], cwd=ROOT, env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
            try:
                deadline = time.time() + 90
                progressed = False
                while time.time() < deadline:
                    time.sleep(2)
                    try:
                        if _day_index(victim) > 35:
                            progressed = True
                            break
                    except sqlite3.Error:
                        continue
                self.assertTrue(progressed,
                                "resumed run made no progress")
            finally:
                proc.kill()
                proc.wait()
            # Reopen: the ledger is clean and the clock stands at
            # the last committed day (never a partial day).
            sim = Simulation(victim, seed="s10-crash")
            try:
                self.assertEqual(sim.store.ledger_sum_check(), [])
                day = sim.store.world()["day_index"]
                self.assertGreater(day, 35)
                self.assertLess(day, 300)
                sim.run_days(65 - day)
            finally:
                sim.close()
            self.assertEqual(worlds_mod.world_digest(victim),
                             digest_twin)
        finally:
            for p in (twin, victim):
                if os.path.exists(p):
                    os.remove(p)


if __name__ == "__main__":
    unittest.main()
