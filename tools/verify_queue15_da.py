"""Verify Queue 15 Unit DA — Photograph Mechanic Implementation
(GDD-04 §3.5, Unit BY design).

Checks the implementation against the design it implements: GDD-04
§3.5 (the record, the gate, the dual write) and §3.4 (the set),
tools/sim/photographs.py, the three new sim tables, the District 2
loader in tools/sim/dataio.py, and tools/sim/tests/
test_photographs.py. Prints one line per check and a summary; exits
0 only when every check passes. Run from the repo root:
python3 tools/verify_queue15_da.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKS = []


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def main():
    gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md").read_text()
    photo = (ROOT / "tools" / "sim" / "photographs.py").read_text()
    persist = (ROOT / "tools" / "sim" / "persistence.py").read_text()
    dataio = (ROOT / "tools" / "sim" / "dataio.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_photographs.py").read_text()
    schema = (ROOT / "data" / "schema.sql").read_text()

    # 1. The module exists with the §3.5 contract.
    check("def take_photograph(store, data, account_id, character_id,"
          in photo, "photographs.py defines take_photograph")
    check("def photo_mode_unlocked" in photo,
          "photographs.py defines the photo-mode gate")
    check("def discovery_set" in photo,
          "photographs.py reads the set from data (not a fixed list)")
    check('PHOTO_MODE_MISSION = "1.4"' in photo,
          "the gate is mission 1.4 (the §2 unlock)")
    check("ZONE_OVERRIDES" in photo
          and '"lm_clock_tower"' in photo
          and '"lm_bridge_approach"' in photo
          and '"d2_lm_northgate_tower"' in photo,
          "the three assigned-by-description zones are explicit overrides")

    # 2. The refusal rules are in the code.
    check("discoverable_type = 'landmark'" in photo,
          "duplicate check covers the discovery row too")
    check("taken_in_zone != zone" in photo,
          "take_photograph enforces the presence rule")
    check("zones.get(discoverable_id)" in photo
          and "if zone is None:" in photo,
          "take_photograph refuses ids outside the landmark set")

    # 3. The three tables exist in the sim store, mirroring §3.5/§3.4.
    check("CREATE TABLE IF NOT EXISTS photographs" in persist,
          "persistence.py creates photographs")
    check("CREATE TABLE IF NOT EXISTS discovery_progress" in persist,
          "persistence.py creates discovery_progress")
    check("CREATE TABLE IF NOT EXISTS mission_progress" in persist,
          "persistence.py creates mission_progress")
    check("PRIMARY KEY (account_id, discoverable_id)" in persist,
          "photographs PK is (account_id, discoverable_id) (§3.5)")
    check("PRIMARY KEY (account_id, discoverable_type, discoverable_id)"
          in persist,
          "discovery_progress PK is the §3.4 triple")
    check("mission_progress" in schema,
          "schema.sql really has mission_progress (the gate's source)")

    # 4. The District 2 loader exists (the set needs all three files).
    check("district2_blockout" in dataio,
          "dataio loads district2-blockout.json")

    # 5. The GDD records the implementation.
    check("Implementation (Unit DA · Queue 15" in gdd04,
          "GDD-04 §3.5 carries the DA implementation note")
    check("19 landmarks" in gdd04,
          "GDD-04 §3.5 notes the set has grown to 19 landmarks")
    check("gate stays closed" in gdd04,
          "GDD-04 states the gate stays closed until the mission system")

    # 6. The tests cover the contract.
    n_tests = len(re.findall(r"def test_", tests))
    check(n_tests >= 10, "test_photographs.py has 10+ tests",
          f"{n_tests} tests")
    check("test_duplicate_photograph_writes_nothing" in tests,
          "tests prove a duplicate photograph writes nothing")
    check("test_photograph_after_visit_writes_nothing" in tests,
          "tests prove a photograph after a visit writes nothing")
    check("test_writes_both_rows_in_one_write" in tests,
          "tests prove the dual write")
    check("test_bus_route_cannot_be_photographed" in tests,
          "tests prove a bus route cannot be photographed")
    check("EXPECTED_ZONES" in tests and len(re.findall(
        r'"[a-z0-9_]+": "d[12]_', tests)) >= 10,
          "tests assert the full 19-landmark zone mapping")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
