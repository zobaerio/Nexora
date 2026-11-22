"""Session 10 endurance + scale + recovery measurements.

Not a unit test — a measurement script whose ACTUAL output is
quoted in docs/SESSION-10-REPORT.md. Three modes:

  endurance : 242 agents x 365 days with the full check battery
              (ledger reconciliation, conservation, government
              audits, database inspection), throughput, DB size
              growth, peak memory, checkpoint save/restore time.
  scale     : 500 agents x 90 days (the scale probe).
  recovery  : build 35 days, resume in a subprocess, kill it
              mid-run, time the reopen + verification, and check
              the recovered world matches its uninterrupted twin.

Usage: python3 -m tools.run_session10_endurance <mode> <dbpath>
Run with TMPDIR set to a roomy directory.
"""
import json
import os
import resource
import sqlite3
import subprocess
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..")))

from tools.sim import dbinspect  # noqa: E402
from tools.sim import finance  # noqa: E402
from tools.sim import worlds as worlds_mod  # noqa: E402
from tools.sim.engine import Simulation  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _peak_mb():
    return round(resource.getrusage(
        resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)


def _size(path):
    total = os.path.getsize(path)
    for suffix in ("-wal", "-shm"):
        if os.path.exists(path + suffix):
            total += os.path.getsize(path + suffix)
    return total


def endurance(path):
    out = {"mode": "endurance", "population": 242, "days": 365}
    t0 = time.time()
    sim = Simulation(path, seed="s10-endurance")
    sim.generate_population(242)
    out["genesis_seconds"] = round(time.time() - t0, 2)
    out["db_bytes_after_genesis"] = _size(path)
    t0 = time.time()
    sim.run_days(365)
    out["run_seconds"] = round(time.time() - t0, 2)
    out["days_per_second"] = round(365 / out["run_seconds"], 3)
    out["peak_memory_mb"] = _peak_mb()
    out["db_bytes_final"] = _size(path)
    store = sim.store
    s = sim.summary()
    out["summary"] = {
        "population_alive": s["population_alive"],
        "ledger_mismatches": s["ledger_mismatches"],
        "registry_events": s["integration"]["registry_events"],
        "registry_by_source": s["integration"]["registry_by_source"],
        "technology": s["integration"]["technology"],
        "businesses_active": s["businesses_active"],
        "latest_indicators": bool(s["latest_indicators"]),
    }
    out["ledger_sum_check"] = store.ledger_sum_check()
    out["conservation_violations"] = finance.verify_conservation(
        store)
    audits = store.rows(
        "SELECT result, COUNT(*) AS n, SUM(discrepancy_count) AS d"
        " FROM audits GROUP BY result")
    out["audits"] = {r["result"]: {"count": r["n"],
                                   "discrepancies": r["d"]}
                     for r in audits}
    sim.close()
    insp = dbinspect.inspect_world(path)
    out["inspection"] = {
        "table_count": insp["table_count"],
        "total_rows": insp["total_rows"],
        "foreign_key_check_violations":
            insp["foreign_key_check_violations"],
        "orphan_scans_nonzero": {
            k: v for k, v in insp["orphan_scans"].items() if v},
        "duplicate_transfer_keys": insp["duplicate_transfer_keys"],
        "duplicate_registry_events":
            insp["duplicate_registry_events"],
    }
    # Checkpoint timings on the finished world.
    t0 = time.time()
    manifest = worlds_mod.create_checkpoint(path, "endurance-final")
    out["checkpoint_save_seconds"] = round(time.time() - t0, 3)
    out["checkpoint_manifest"] = {
        "day_index": manifest["day_index"],
        "population_alive": manifest["population_alive"],
        "ledger_rows": manifest["ledger_rows"],
        "ledger_reconciled": manifest["ledger_reconciled"],
    }
    digest = worlds_mod.world_digest(path)
    t0 = time.time()
    worlds_mod.restore_checkpoint(path, "endurance-final")
    out["checkpoint_restore_seconds"] = round(time.time() - t0, 3)
    out["digest_restored_matches"] = (
        worlds_mod.world_digest(path) == digest)
    return out


def scale(path):
    out = {"mode": "scale", "population": 500, "days": 90}
    t0 = time.time()
    sim = Simulation(path, seed="s10-scale")
    sim.generate_population(500)
    out["genesis_seconds"] = round(time.time() - t0, 2)
    t0 = time.time()
    sim.run_days(90)
    out["run_seconds"] = round(time.time() - t0, 2)
    out["days_per_second"] = round(90 / out["run_seconds"], 3)
    out["peak_memory_mb"] = _peak_mb()
    out["db_bytes_final"] = _size(path)
    s = sim.summary()
    out["summary"] = {
        "population_alive": s["population_alive"],
        "ledger_mismatches": s["ledger_mismatches"],
        "registry_events": s["integration"]["registry_events"],
    }
    out["ledger_sum_check"] = sim.store.ledger_sum_check()
    out["conservation_violations"] = finance.verify_conservation(
        sim.store)
    sim.close()
    return out


def _day_index(path):
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return conn.execute(
            "SELECT day_index FROM world_state WHERE id = 1").fetchone()[0]
    finally:
        conn.close()


def recovery(path):
    out = {"mode": "recovery", "population": 60}
    twin = path + ".twin.db"
    for p in (path, twin):
        if os.path.exists(p):
            os.remove(p)
    sim = Simulation(twin, seed="s10-recovery")
    sim.generate_population(60)
    sim.run_days(65)
    digest_twin = worlds_mod.world_digest(twin)
    sim.close()
    sim = Simulation(path, seed="s10-recovery")
    sim.generate_population(60)
    sim.run_days(35)
    sim.close()
    env = dict(os.environ)
    proc = subprocess.Popen(
        [sys.executable, "-m", "tools.sim", "--db", path,
         "--days", "300"], cwd=ROOT, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.time() + 120
        while time.time() < deadline:
            time.sleep(2)
            try:
                if _day_index(path) > 35:
                    break
            except sqlite3.Error:
                continue
    finally:
        proc.kill()
        proc.wait()
    out["killed_at_day"] = _day_index(path)
    t0 = time.time()
    sim = Simulation(path, seed="s10-recovery")
    out["ledger_sum_check"] = sim.store.ledger_sum_check()
    day = sim.store.world()["day_index"]
    sim.run_days(65 - day)
    sim.close()
    out["recovery_reopen_and_finish_seconds"] = round(
        time.time() - t0, 2)
    out["digest_matches_twin"] = (
        worlds_mod.world_digest(path) == digest_twin)
    os.remove(twin)
    return out


if __name__ == "__main__":
    mode, path = sys.argv[1], sys.argv[2]
    fn = {"endurance": endurance, "scale": scale,
          "recovery": recovery}[mode]
    print(json.dumps(fn(path), indent=1, sort_keys=True))
