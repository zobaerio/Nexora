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
    # Session 02 observation: inspect real simulation data.
    ap.add_argument("--inspect", metavar="CHARACTER_ID",
                    help="person: profile, family tree, network,"
                         " mobility, lineage")
    ap.add_argument("--household", metavar="HOUSEHOLD_ID",
                    help="household: composition, conditions, finances")
    ap.add_argument("--community", metavar="ZONE_ID",
                    help="community: population, leader, issues,"
                         " facilities")
    ap.add_argument("--society", action="store_true",
                    help="society overview: all communities + counts")
    # Session 03 city observation: real sim data only.
    ap.add_argument("--city", metavar="CITY_ID",
                    help="full city state export (the UE data layer)")
    ap.add_argument("--city-map", metavar="CITY_ID",
                    help="map-mode overview rendered from real"
                         " coordinates")
    ap.add_argument("--analytics", metavar="CITY_ID",
                    help="live city analytics")
    # Session 04 economy observation: real sim data only.
    ap.add_argument("--economy", action="store_true",
                    help="economy overview: foundation, indicators,"
                         " bank, labour, prices, crises")
    ap.add_argument("--business", metavar="BUSINESS_ID",
                    help="business: P&L history, inventory,"
                         " employees, shareholders")
    ap.add_argument("--bank", action="store_true",
                    help="bank: stats, loans, reconciliation")
    ap.add_argument("--indicators", metavar="SCOPE",
                    help="indicator series for a scope (national"
                         " or a city id)")
    ap.add_argument("--finances", metavar="CHARACTER_ID",
                    help="a person's financial profile from the"
                         " ledger")
    args = ap.parse_args(argv)

    sim = Simulation(args.db, seed=args.seed)
    if args.economy or args.business or args.bank \
            or args.indicators or args.finances:
        from tools.sim import econview
        if args.economy:
            out = econview.economy_overview(sim.store, sim.data)
        elif args.business:
            out = econview.business_view(sim.store, sim.data,
                                         args.business)
        elif args.bank:
            out = econview.bank_view(sim.store, sim.data)
        elif args.indicators:
            out = econview.indicators_view(sim.store, sim.data,
                                           args.indicators)
        else:
            out = econview.person_finance_view(sim.store, sim.data,
                                               args.finances)
        print(json.dumps(out, indent=1, sort_keys=True,
                         default=str))
        sim.close()
        return 0
    if args.city or args.city_map or args.analytics:
        from tools.sim import analytics as analytics_mod
        from tools.sim import cityview
        if args.city:
            out = cityview.export_city_state(sim.store, sim.data,
                                             args.city)
            print(json.dumps(out, indent=1, sort_keys=True,
                             default=str))
        elif args.city_map:
            lines = cityview.ascii_map(sim.store, sim.data,
                                       args.city_map)
            print("\n".join(lines) if lines else "unknown city")
        else:
            out = analytics_mod.city_analytics(sim.store, sim.data,
                                               args.analytics)
            print(json.dumps(out, indent=1, sort_keys=True,
                             default=str))
        sim.close()
        return 0
    if args.inspect or args.household or args.community or args.society:
        from tools.sim import observation
        if args.inspect:
            out = observation.inspect_person(sim.store, sim.data,
                                             args.inspect)
        elif args.household:
            out = observation.inspect_household(sim.store, sim.data,
                                                args.household)
        elif args.community:
            out = observation.inspect_community(sim.store, sim.data,
                                                args.community)
        else:
            out = observation.society_overview(sim.store, sim.data)
        print(json.dumps(out, indent=1, sort_keys=True, default=str))
        sim.close()
        return 0
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
