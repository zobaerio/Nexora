"""Command-line entry for the headless simulation core.

Usage:
  python3 -m tools.sim --db /tmp/world.db --population 240 --days 30
  python3 -m tools.sim --db /tmp/world.db --summary-only

The database file is the save: rerunning with the same --db resumes
exactly where the previous process stopped (deterministic streams
make the continuation identical to an uninterrupted run).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tools.sim.engine import Simulation  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tools.sim")
    ap.add_argument("--db", required=True, help="SQLite world file")
    ap.add_argument("--seed", default="nexora-1")
    ap.add_argument("--population", type=int, default=240)
    ap.add_argument("--days", type=int, default=0)
    ap.add_argument("--summary-only", action="store_true")
    args = ap.parse_args(argv)

    sim = Simulation(args.db, seed=args.seed)
    if not args.summary_only:
        stats = sim.generate_population(args.population)
        print(json.dumps({"population": stats}, indent=1, sort_keys=True))
        if args.days:
            sim.run_days(args.days)
    print(json.dumps(sim.summary(), indent=1, sort_keys=True))
    sim.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
