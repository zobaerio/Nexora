"""Verify Queue 22 Unit EV — Haggle Record + Mechanic (GDD-04 §3.6,
mission 2.3 objective (2); EO follow-up).

Checks the haggle record against its sources: tools/sim/market.py
(the record + the success predicate), tools/sim/persistence.py
(the haggle_events table), tools/sim/missions.py (the 2.3
verifier now requires both objectives), GDD-04 §3.6 (the
objective is recorded verifiable, the live call site recorded
open), data/schema.sql (the server-side mirror), and the tests
(test_missions.py TestMission23 + TestHaggleRecord).
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue22_ev.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CHECKS = []


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def main():
    gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md").read_text()
    market_src = (ROOT / "tools" / "sim" / "market.py").read_text()
    persist_src = (ROOT / "tools" / "sim" / "persistence.py").read_text()
    missions_src = (ROOT / "tools" / "sim" / "missions.py").read_text()
    schema = (ROOT / "data" / "schema.sql").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_missions.py").read_text()
    regress = (ROOT / "tools" / "sim" / "tests"
               / "test_mission_progress_regression.py").read_text()

    # 1. The table exists with the record's shape.
    table = persist_src.split("CREATE TABLE IF NOT EXISTS haggle_events (")[1] \
        .split(");")[0]
    check("haggle_id TEXT PRIMARY KEY" in table,
          "persistence.py: haggle_events has haggle_id PK")
    check("outcome TEXT NOT NULL CHECK (outcome IN ('success', 'failed'))"
          in table,
          "persistence.py: haggle_events outcome is success/failed only")
    check("asked_price_ncr INTEGER NOT NULL" in table
          and "paid_price_ncr INTEGER NOT NULL" in table,
          "persistence.py: haggle_events records asked + paid prices")
    check("game_minutes INTEGER NOT NULL" in table
          and "zone TEXT NOT NULL" in table
          and "good_id TEXT NOT NULL" in table,
          "persistence.py: haggle_events records zone, good, minute")

    # 2. The record function: derived outcome, no invented rate.
    rec = market_src.split("def record_haggle(")[1].split("def ")[0]
    check("paid_price_ncr < asked_price_ncr" in " ".join(rec.split()),
          "market.py: success is derived (paid < asked)")
    # The derivation must be the whole rule: no discount constant,
    # no success chance, no target price anywhere in the body
    # (the docstring may say "no rate" — the body must have none).
    body = rec.split('"""', 2)[2] if rec.count('"""') >= 2 else rec
    check("discount" not in body.lower()
          and "chance" not in body.lower()
          and "DISCOUNT" not in body,
          "market.py: record_haggle invents no discount rate")
    check("paid_price_ncr > asked_price_ncr" in rec,
          "market.py: paying over the ask is refused")
    check("has_successful_haggle(store, character_id" in market_src,
          "market.py: has_successful_haggle predicate exists")
    pred = market_src.split("def has_successful_haggle(")[1] \
        .split("def ")[0] if "def has_successful_haggle(" in market_src \
        else ""
    check("outcome = 'success'" in pred,
          "market.py: the predicate reads successful rows only")
    # (Update, Unit FA · Queue 23: the shopping pass IS the live
    # call site now — retail_allocation records the haggle. The
    # EV-era assertion that it does not haggle is struck here, not
    # silently left failing.)
    check("record_haggle(" in market_src.split(
        "def retail_allocation(")[1].split(
        "# -- Queue 22 Unit EV")[0],
        "market.py: the shopping pass haggles (FA live call site)")

    # 3. The verifier requires BOTH objectives.
    ver = missions_src.split("def verify_mission_2_3(")[1].split("def ")[0]
    check("has_successful_haggle(store, character_id" in ver,
          "missions.py: verify_mission_2_3 reads the haggle record")
    check("BORO_BAZAR_ZONE" in ver,
          "missions.py: the haggle must be in Boro Bazar's zone")
    check('BORO_BAZAR_ZONE = "d1_market"' in missions_src,
          "missions.py: Boro Bazar's zone is d1_market (mission zone_ref)")
    check("household_bought_food(store, household_id)" in ver,
          "missions.py: the food objective is still required")

    # 4. The decision is recorded in GDD-04 §3.6.
    check("The objective (2) | \"Haggle once, successfully\" is verified"
          in gdd04,
          "GDD-04 §3.6: objective (2) is recorded verifiable")
    check("NOT verifiable" not in gdd04.split(
        "Completion condition — mission 2.3")[1].split(
        "Completion condition — mission 2.4")[0].replace(
        "The objective (2) | \"Haggle once, successfully\" is verified",
        ""),
          "GDD-04 §3.6: no 'NOT verifiable' remains for 2.3's haggle")
    check("Live call site — wired (Unit FA" in gdd04
          and "Phase 6 dialogue/mission runtime" in gdd04,
          "GDD-04 §3.6: the live call site is recorded wired (FA)")
    check("Update, Unit EV" in gdd04,
          "GDD-04 §3.6: the EV implementation note is present")

    # 5. The server-side mirror (DH precedent).
    check("CREATE TABLE haggle_events (" in schema,
          "schema.sql: haggle_events mirrored")
    check("outcome         TEXT NOT NULL CHECK (outcome IN" in schema,
          "schema.sql: haggle_events outcome check mirrored")

    # 6. Tests prove haggled verifies and unhaggled does not.
    check("test_food_without_haggle_does_not_verify" in tests,
          "tests: food without a haggle does not verify 2.3")
    check("test_failed_haggle_does_not_verify" in tests,
          "tests: a failed haggle does not verify 2.3")
    check("test_haggle_in_another_zone_does_not_verify" in tests,
          "tests: a haggle in another zone does not verify 2.3")
    check("test_another_characters_haggle_does_not_verify" in tests,
          "tests: another character's haggle does not verify 2.3")
    check("class TestHaggleRecord" in tests,
          "tests: the haggle record has its own test class")
    check("test_paying_over_the_asked_price_is_refused" in tests,
          "tests: paying over the ask is refused")
    check("record_haggle(store, cid, \"food_basket\"" in regress,
          "regression: the DS suite's 2.3 test records a haggle")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed, "
          f"{len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
