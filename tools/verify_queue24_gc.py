"""Verify Queue 24 Unit GC — Settlement-Measured Storm-Month
Trajectory (GDD-03 §2; FB follow-up).

Analysis + data — no sim change, no tuning call. Checks the
comparison against its sources: docs/ECONOMY-SIM-REPORT-V7.md
§6 (the addendum — storm days, worked days, one worker's real
daily balance path, the verdict, and where the tool and the
settlement differ), GDD-03 §2 (the GC pointer), and the tool
(the (4, 23) position's own dip). Re-runs the EY live month
live (seed ey-measure, 60 population, 32 days) and asserts the
recorded figures: storm day_index [3, 22], all four workers at
28/30 worked days, Priya Khan's minimum end-of-day balance 89
and Mariam Shah's 0, and the taxi-fare-only within-month flow.
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue24_gc.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CHECKS = []


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def _measure():
    """The EY live month, re-run: returns (storm day_index,
    {cid: (worked, due, lost days)}, {cid: (seed, min balance,
    end-of-month-1 balance, month-1 flow by reason)})."""
    from tools.sim import labour as labour_mod
    from tools.sim.engine import Simulation
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(db_path)
    sim = Simulation(db_path, seed="ey-measure")
    sim.generate_population(60)
    sim.run_days(32)
    store = sim.store
    storm_idx = [d for d in range(30)
                 if sim.weather_for_day(d) == "storm"]
    workers = {}
    paths = {}
    for w in store.rows(
            "SELECT e.character_id, e.wage_per_month FROM employments e"
            " WHERE e.profession_id = 'construction_worker'"
            " AND e.ended_at_game_minutes IS NULL"):
        cid = w["character_id"]
        wd = labour_mod.worked_days(store, cid, 1)
        due = labour_mod.day_wage_due(store, cid, 1,
                                      w["wage_per_month"])
        lost = []
        for row in store.rows(
                "SELECT day_index, blocks_json FROM"
                " instantiated_schedules WHERE character_id = ?"
                " AND day_index >= 0 AND day_index < 30",
                (cid,)):
            blocks = json.loads(row["blocks_json"])
            if not any(b.get("activity") == "work"
                       and not b.get("broken_tool") for b in blocks):
                lost.append(row["day_index"])
        workers[cid] = (wd, due, sorted(lost))
        if w["wage_per_month"] != 9000:
            continue
        rows = store.rows(
            "SELECT game_minutes, reason_code, amount,"
            " from_character_id, to_character_id FROM economy_ledger"
            " WHERE (from_character_id = ? OR to_character_id = ?)"
            " ORDER BY game_minutes, ledger_id", (cid, cid))
        net_all = sum(r["amount"]
                      if r["to_character_id"] == cid else -r["amount"]
                      for r in rows)
        now = store.row("SELECT balance_cached FROM characters WHERE"
                        " character_id = ?", (cid,))["balance_cached"]
        start = now - net_all
        daily, bal, idx = [], start, 0
        ordered = sorted(rows, key=lambda r: r["game_minutes"])
        for d in range(30):
            while idx < len(ordered) and ordered[idx]["game_minutes"] \
                    < (d + 1) * 1440:
                r = ordered[idx]
                bal += r["amount"] if r["to_character_id"] == cid \
                    else -r["amount"]
                idx += 1
            daily.append(bal)
        flow = {}
        for r in rows:
            if r["game_minutes"] >= 43200:
                continue
            signed = r["amount"] if r["to_character_id"] == cid \
                else -r["amount"]
            flow[r["reason_code"]] = flow.get(r["reason_code"], 0) \
                + signed
        seed = flow.get("seed", 0)
        paths[cid] = (seed, min(daily), daily[29], flow)
    sim.close()
    os.remove(db_path)
    return storm_idx, workers, paths


def main():
    report = (ROOT / "docs" / "ECONOMY-SIM-REPORT-V7.md").read_text()
    gdd03 = (ROOT / "docs" / "GDD-03-ECONOMY-AND-PROFESSIONS.md") \
        .read_text()
    from tools import economy_sim as econ
    prices = econ.load("prices.json")
    w = next(w for w in prices["wages_monthly"]
             if w["profession_id"] == "construction_worker")

    # 1. The addendum is recorded in the V7 report.
    check("## 6. Addendum — Settlement-measured storm-month"
          " trajectory (Unit GC, Queue 24)" in report,
          "report V7: the GC addendum exists")
    check("1-based days 4 and 23 — not 3 and 22" in report,
          "report V7: the off-by-one is stated")
    check("entry −100, mid 0, senior 0" in report,
          "report V7: the true-position dip is recorded")
    check("28/30 in month 1" in report,
          "report V7: the worked days are recorded")
    check("4,985, 4,985, 4,585, 4,585, 3,989" in report,
          "report V7: Priya Khan's daily path is quoted")
    check("Minimum end-of-day balance in month 1: **89**" in report,
          "report V7: Priya Khan's minimum is recorded")
    check("drains on taxi fares alone to exactly **0**" in report
          and "stays at 0 through day_index 29" in report,
          "report V7: Mariam Shah's minimum is recorded")
    check("Does the tool's −150 entry dip match" in report
          and "No." in report,
          "report V7: the verdict (no match) is recorded")
    check("Second earner" in report and "Arrears" in report
          and "Other income" in report and "Taxi fares" in report,
          "report V7: the differences are named")
    check("office_allowance` +16,000" in report,
          "report V7: the office allowance is recorded")
    check("No tuning call" in report or "no tuning\ncall" in report,
          "report V7: no tuning call is taken")
    check("STORM_MEASURED_DAYS` to (4, 23)" in report,
          "report V7: the correction is recorded open")

    # 2. GDD-03 §2 points at the addendum.
    check("Update, Unit GC" in gdd03,
          "GDD-03 §2: the GC pointer is present")
    check("1-based days 4 and 23" in gdd03,
          "GDD-03 §2: the corrected storm days are stated")

    # 3. The tool's own model at the true position.
    true_pos = econ.simulate(prices, w, "entry",
                             storm_days=(4, 23))
    check(true_pos["min_balance"] == -100,
          "tool: entry dips to -100 at the true position (4, 23)",
          str(true_pos["min_balance"]))
    recorded = econ.simulate(prices, w, "entry",
                             storm_days=econ.STORM_MEASURED_DAYS)
    check(recorded["min_balance"] == -150,
          "tool: the recorded (3, 22) position still dips -150",
          str(recorded["min_balance"]))

    # 4. Live re-derivation of the EY live month.
    storm_idx, workers, paths = _measure()
    check(storm_idx == [3, 22],
          "live: storm day_index are 3 and 22", str(storm_idx))
    check(len(workers) == 4,
          "live: the month holds 4 construction workers",
          str(len(workers)))
    check(all(v[0] == 28 for v in workers.values()),
          "live: every worker worked 28/30 days",
          str({k: v[0] for k, v in workers.items()}))
    check(all(v[2] == [3, 22] for v in workers.values()),
          "live: every worker lost exactly day_index 3 and 22",
          str({k: v[2] for k, v in workers.items()}))
    check(all(v[1] == 8400 for v in workers.values()
              if v[1] <= 9000) and
          all(v[1] == 13067 for v in workers.values()
              if v[1] > 9000),
          "live: day-wage due is 8400 entry / 13067 mid",
          str({k: v[1] for k, v in workers.items()}))
    priya = paths.get("NEX000042")
    check(priya is not None and priya[0] == 5385
          and priya[1] == 89 and priya[2] == 89,
          "live: Priya Khan seed 5385, min 89, month-end 89",
          str(priya))
    check(priya is not None
          and set(priya[3]) == {"seed", "taxi_fare"}
          and priya[3]["taxi_fare"] == -5296,
          "live: Priya Khan's month-1 flow is seed + fares only",
          str(priya[3]) if priya else "")
    mariam = paths.get("NEX000045")
    check(mariam is not None and mariam[0] == 4496
          and mariam[1] == 0 and mariam[2] == 0,
          "live: Mariam Shah seed 4496, min 0, month-end 0",
          str(mariam))

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed, "
          f"{len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
