"""Verify Queue 25 Unit HC — Per-Good Purchase Audit
(GB follow-up).

Checks the decision + implementation against its sources:
docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the decision — record
the per-good split BESIDE the combined row — with the rejected
alternatives and their reasons), tools/sim/persistence.py (the
purchase_audit + takings_audit tables), tools/sim/market.py (the
pass writes the audit; the draw returns the takings split; no
ledger row is added), data/schema.sql (the server mirror), and
the tests (test_economy_business_market.py
TestPerGoodPurchaseAudit). Runs a live seeded month
(seed q25-hc-audit) and proves the reconciliation identities
exactly, printing the measured table.
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue25_hc.py
"""
import os
import subprocess
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


def main():
    gdd03 = (ROOT / "docs" / "GDD-03-ECONOMY-AND-PROFESSIONS.md").read_text()
    persist = (ROOT / "tools" / "sim" / "persistence.py").read_text()
    market_src = (ROOT / "tools" / "sim" / "market.py").read_text()
    schema = (ROOT / "data" / "schema.sql").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_economy_business_market.py").read_text()

    # 1. The decision is recorded in GDD-03 §2, with the
    # alternatives and why they were rejected.
    check("Unit HC · Queue 25" in gdd03,
          "GDD-03 §2: the HC decision is recorded")
    check("record the per-good split BESIDE the combined row"
          in gdd03,
          "GDD-03 §2: the chosen rule is (b), beside the row")
    check("split the purchase into per-good rows at settlement"
          " time — REJECTED" in gdd03,
          "GDD-03 §2: rule (a) is rejected, with its reason")
    check("record the owner-shop share alone — REJECTED" in gdd03,
          "GDD-03 §2: rule (c) is rejected, with its reason")
    check("167,250 / 167,250 / 0" in gdd03,
          "GDD-03 §2: the measured food reconciliation is quoted")
    check("37,120" in gdd03,
          "GDD-03 §2: the measured clothing residual is quoted")
    check("269,168" in gdd03,
          "GDD-03 §2: the measured ledger takings total is quoted")

    # 2. The tables exist in the sim schema, with the right keys.
    for table, pk in (
            ("purchase_audit",
             "PRIMARY KEY (household_id, month_index, good_id)"),
            ("takings_audit",
             "PRIMARY KEY (city_id, month_index, good_id)")):
        block = persist.split(f"CREATE TABLE IF NOT EXISTS {table} (")[1] \
            .split(");")[0]
        check(pk in persist,
              f"persistence.py: {table} has its natural PK")
        check("intended_spend_ncr" in block if table == "purchase_audit"
              else "system_takings_ncr" in block,
              f"persistence.py: {table} carries its columns")
    check("Queue 25 Unit HC" in persist,
          "persistence.py: the tables record the HC decision")

    # 3. The pass writes the audit; the draw returns the split;
    # the audit adds no ledger row.
    alloc = market_src.split("def retail_allocation(")[1].split(
        "# -- Queue 22 Unit EV")[0]
    check("INSERT OR REPLACE INTO purchase_audit" in alloc,
          "market.py: the pass writes purchase_audit")
    check("INSERT OR REPLACE INTO takings_audit" in alloc,
          "market.py: the pass writes takings_audit")
    check("intended - spend" in alloc,
          "market.py: the residual is derived (intended - spend)")
    check("spend_total - system_takings" in alloc,
          "market.py: the owner share is derived (spend - takings)")
    check('drawn["system_takings_ncr"]' in alloc,
          "market.py: the pass reads the draw's takings split")
    draw = market_src.split("def _draw_from_shelves(")[1] \
        .split("def ")[0]
    check('"system_takings_ncr"' in draw,
          "market.py: _draw_from_shelves returns the takings")
    audit_blocks = alloc.split("Queue 25 Unit HC")
    check(all("store.transfer" not in b for b in audit_blocks[1:]),
          "market.py: the audit writes no ledger row")
    check("purchase_audit" in market_src.split('"""')[1]
          or "per-good purchase audit" in market_src,
          "market.py: the module docstring records the audit")

    # 4. The server mirror exists, field-for-field, same PKs.
    for table, pk in (
            ("purchase_audit",
             "PRIMARY KEY (household_id, month_index, good_id)"),
            ("takings_audit",
             "PRIMARY KEY (city_id, month_index, good_id)")):
        check(f"CREATE TABLE {table} (" in schema,
              f"schema.sql: {table} is mirrored")
        check(pk in schema,
              f"schema.sql: {table} keeps its PK")

    # 5. The tests prove the reconciliation.
    check("class TestPerGoodPurchaseAudit" in tests,
          "tests: the audit class exists")
    for name in ("test_month_per_good_purchase_reconciles",
                 "test_audit_spend_matches_consumption_spend",
                 "test_system_takings_match_the_ledger",
                 "test_owner_share_is_a_real_draw_not_an_invention",
                 "test_combined_purchase_row_is_unchanged"):
        check(f"def {name}" in tests, f"tests: {name} exists")

    # 6. Live run (seed q25-hc-audit, 32 days): the identities
    # hold exactly, and the measured numbers are the documented
    # ones.
    from tools.sim.engine import Simulation
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    sim = Simulation(path, seed="q25-hc-audit")
    try:
        sim.generate_population(60)
        sim.run_days(32)
        store = sim.store
        measured = {}
        for r in store.rows(
                "SELECT good_id, SUM(intended_spend_ncr) AS i,"
                " SUM(spend_ncr) AS s, SUM(residual_ncr) AS r FROM"
                " purchase_audit WHERE month_index = 1"
                " GROUP BY good_id"):
            measured[r["good_id"]] = (r["i"], r["s"], r["r"])
            check(r["i"] == r["s"] + r["r"],
                  f"live: {r['good_id']} intended = spend + residual",
                  f"{r['i']} = {r['s']} + {r['r']}")
        print("  measured month-1 purchase_audit (intended/spend/"
              "residual): " + "; ".join(
                  f"{g} {v[0]}/{v[1]}/{v[2]}"
                  for g, v in sorted(measured.items())))
        check(measured.get("food_basket") == (167250, 167250, 0),
              "live: the food reconciliation is the documented one",
              str(measured.get("food_basket")))
        check(measured.get("clothing_set") == (88120, 51000, 37120),
              "live: the clothing residual is the documented one",
              str(measured.get("clothing_set")))
        for r in store.rows(
                "SELECT * FROM takings_audit WHERE month_index = 1"):
            check(r["spend_ncr"] == r["system_takings_ncr"]
                  + r["owner_share_ncr"],
                  f"live: {r['city_id']}/{r['good_id']} spend = "
                  "takings + owner",
                  f"{r['spend_ncr']} = {r['system_takings_ncr']} + "
                  f"{r['owner_share_ncr']}")
        audit_takings = store.row(
            "SELECT COALESCE(SUM(system_takings_ncr), 0) AS s FROM"
            " takings_audit WHERE month_index = 1")["s"]
        ledger_takings = store.row(
            "SELECT COALESCE(SUM(amount), 0) AS s FROM economy_ledger"
            " WHERE reason_code = 'retail_takings' AND event_ref ="
            " 'month:1'")["s"]
        check(audit_takings == ledger_takings == 269168,
              "live: audit takings = ledger takings = 269168",
              f"{audit_takings} vs {ledger_takings}")
        food = store.row(
            "SELECT * FROM takings_audit WHERE month_index = 1 AND"
            " city_id = 'rupsha_city' AND good_id = 'food_basket'")
        check(food["owner_share_ncr"] == 9842,
              "live: the food owner share is the documented 9,842",
              str(food["owner_share_ncr"]))
    finally:
        sim.close()
        os.remove(path)
        for f in Path("/tmp").glob("tmp*.db"):
            try:
                f.unlink()
            except OSError:
                pass

    # 7. Scope: only the HC files changed on this branch since
    # the HB commit.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    check(names == {"tools/sim/market.py",
                    "tools/sim/persistence.py",
                    "data/schema.sql",
                    "docs/GDD-03-ECONOMY-AND-PROFESSIONS.md",
                    "tools/sim/tests/test_economy_business_market.py",
                    "tools/verify_queue25_hc.py"},
          "scope: only the six HC files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
