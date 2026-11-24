"""Verify Queue 24 Unit GB — Haggle-Saving Ledger Decision
(GDD-03 §2, GDD-04 §3.6; FA follow-up).

Design decision only — no sim change. Checks the decision
against its sources: GDD-03 §2 (the end-to-end trace, the
measured figures, the DECIDED clearing-residual rule and the
exact ledger rows it requires), GDD-04 §3.6 (the decision is
recorded at mission 2.3), and the code (the settlement's
`purchase` row, the pass's `retail_takings` row, no refund row
anywhere). Re-derives the measurement live: the FA world is run
twice (food shelf raised to 3,750 and at base) and the Rupsha
month-1 food totals must match the recorded figures and be
identical across runs — the residual is the unmet-want
shortfall, not a haggle-created pot.
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue24_gb.py
"""
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


def _rupsha_food_totals(raise_shelf):
    """One seeded FA-world month; returns (budgets, spend, unmet,
    takings) for Rupsha food_basket, month 1."""
    from tools.sim import business as business_mod
    from tools.sim import cities as cities_mod
    from tools.sim.engine import Simulation
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    sim = Simulation(path, seed="q23-fa-haggle")
    sim.generate_population(60)
    store, data = sim.store, sim.data
    if raise_shelf:
        store.execute(
            "UPDATE market_prices SET price_ncr = 3750 WHERE"
            " city_id = 'rupsha_city' AND good_id = 'food_basket'")
    sim.run_days(32)
    city_zones = ("SELECT zone_id FROM city_zones WHERE city_id ="
                  " 'rupsha_city'")
    budgets = store.row(
        "SELECT COALESCE(SUM(hf.food_ncr),0) AS s FROM"
        " household_finances hf JOIN households h ON"
        f" h.household_id = hf.household_id WHERE hf.month_index = 1"
        f" AND h.district_id IN ({city_zones})")["s"]
    spend = store.row(
        "SELECT COALESCE(SUM(hc.spend_ncr),0) AS s FROM"
        " household_consumption hc JOIN households h ON"
        " h.household_id = hc.household_id WHERE hc.month_index = 1"
        f" AND hc.good_id = 'food_basket' AND h.district_id IN"
        f" ({city_zones})")["s"]
    unmet = store.row(
        "SELECT COALESCE(SUM(hc.unmet_units),0) AS s FROM"
        " household_consumption hc JOIN households h ON"
        " h.household_id = hc.household_id WHERE hc.month_index = 1"
        f" AND hc.good_id = 'food_basket' AND h.district_id IN"
        f" ({city_zones})")["s"]
    takings = 0
    for r in store.rows(
            "SELECT * FROM economy_ledger WHERE reason_code ="
            " 'retail_takings' AND transfer_key LIKE '%:food_basket:1'"):
        b = store.row("SELECT * FROM businesses WHERE business_id = ?",
                      (r["to_business_id"],))
        if b and business_mod.business_city(store, data, b) \
                == "rupsha_city":
            takings += r["amount"]
    sim.close()
    os.remove(path)
    return budgets, spend, round(unmet, 3), takings


def main():
    gdd03 = (ROOT / "docs" / "GDD-03-ECONOMY-AND-PROFESSIONS.md") \
        .read_text()
    gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md") \
        .read_text()
    engine_src = (ROOT / "tools" / "sim" / "engine.py").read_text()
    market_src = (ROOT / "tools" / "sim" / "market.py").read_text()

    # 1. The decision is recorded in GDD-03 §2.
    check("Update, Unit GB" in gdd03,
          "GDD-03 §2: the GB decision note is present")
    check("DECIDED: the haggle saving stays in SYS-MARKET clearing"
          in gdd03,
          "GDD-03 §2: the decision is clearing residual")
    check("there is no household refund" in gdd03,
          "GDD-03 §2: no household refund")
    check("182,750" in gdd03 and "91,501" in gdd03
          and "91,249" in gdd03,
          "GDD-03 §2: the measured budgets/spend/residual are quoted")
    check("18.227" in gdd03,
          "GDD-03 §2: the unmet units are quoted")
    check("IDENTICAL with the shelf at base" in gdd03,
          "GDD-03 §2: the residual is identical across runs")
    check("NO new ledger rows" in gdd03,
          "GDD-03 §2: the decision requires no new rows")
    check("15,251" in gdd03,
          "GDD-03 §2: the owner-shop share gap is recorded")
    check("one combined `purchase` row per earner" in gdd03,
          "GDD-03 §2: the per-good audit gap is recorded")

    # 2. The decision is recorded at mission 2.3 in GDD-04 §3.6.
    sec23 = gdd04.split("Completion condition — mission 2.3")[1] \
        .split("Completion condition — mission 2.4")[0]
    check("Update, Unit GB" in sec23,
          "GDD-04 §3.6: the GB decision note is present")
    check("stays in SYS-MARKET clearing as a residual" in sec23,
          "GDD-04 §3.6: the decision is stated")
    check("no household refund" in sec23,
          "GDD-04 §3.6: no household refund")

    # 3. The cited code paths exist, and no refund row is written.
    check("def _pay_purchase(" in engine_src,
          "engine.py: the settlement purchase path exists")
    check('"purchase"' in engine_src,
          "engine.py: the purchase reason is written")
    check('"retail_takings"' in market_src,
          "market.py: the takings reason is written")
    check("unmet_units" in market_src,
          "market.py: the pass records unmet units")
    check("refund" not in market_src.lower(),
          "market.py: no refund row is written by the pass")
    check("refund" not in engine_src.lower(),
          "engine.py: no refund row is written by the settlement")

    # 4. Live re-derivation: the traced figures, identical across
    # both runs — the residual is the shortfall, not the haggle.
    raised = _rupsha_food_totals(True)
    check(raised == (182750, 91501, 18.227, 76250),
          "live: raised-shelf run matches the recorded figures",
          str(raised))
    base = _rupsha_food_totals(False)
    check(base == raised,
          "live: base-price run is identical (no haggle effect)",
          str(base))
    check(raised[0] - raised[1] == 91249,
          "live: the residual is budgets minus spend", "91249")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed, "
          f"{len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
