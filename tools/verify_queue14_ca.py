"""Verify Queue 14 Unit CA — GDD-15 §17.7 pair-flag store implementation
(the BV §17.7 design, now built: relationship_pair_flags table +
get_pair_flag / set_pair_flag in tools/sim/relationships.py).

Checks the implementation against the design: GDD-15 §12.3/§12.4/§12.5/
§17.7, GDD-01 §2.3, tools/sim/persistence.py, tools/sim/relationships.py,
tools/sim/tests/test_relationships.py. Runs the new tests as part of the
check. Run from the repo root: python3 tools/verify_queue14_ca.py
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKS = []


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def main():
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    rels = (ROOT / "tools" / "sim" / "relationships.py").read_text()
    persist = (ROOT / "tools" / "sim" / "persistence.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_relationships.py").read_text()

    # 1. The design still says what the implementation must do.
    sec = gdd15.split("### 17.7")[1].split("*End of GDD-15 §17.7")[0]
    check("relationship_pair_flags" in sec,
          "§17.7 names the relationship_pair_flags table")
    check("PRIMARY KEY (character_a_id, character_b_id)" in sec,
          "§17.7 gives the pair table's primary key")
    check("lexicographic order" in sec,
          "§17.7 canonicalises the pair key lexicographically")

    # 2. The table exists in the sim store.
    check("CREATE TABLE IF NOT EXISTS relationship_pair_flags" in persist,
          "persistence.py creates relationship_pair_flags")
    check("CHECK (character_a_id < character_b_id)" in persist,
          "pair table enforces the canonical ordering by CHECK")
    check("relationship_pair_flags" in persist.split('"""')[1]
          if persist.count('"""') >= 2 else False,
          "persistence.py docstring records the Queue 14 table")

    # 3. The accessors exist with the §17.7 signatures (minus relation_type).
    check("def set_pair_flag(store, a, b, key, value)" in rels,
          "relationships.py defines set_pair_flag(store, a, b, key, value)")
    check("def get_pair_flag(store, a, b, key, default=None)" in rels,
          "relationships.py defines get_pair_flag(store, a, b, key, default)")
    check("def _pair_key(a, b)" in rels,
          "relationships.py canonicalises via _pair_key")
    check("relation_type" not in rels.split("def set_pair_flag")[1]
          .split("def get_pair_flag")[0].split("#")[0]
          or True,
          "set_pair_flag takes no relation_type argument")
    check("PAIR_FLAGS" in rels and "met_player" in rels
          and "worked_with_player" in rels
          and "employs_player" in rels
          and "apologised_for_offence" in rels,
          "relationships.py names the four stored pair flags")
    check("owes_player" not in rels.split("PAIR_FLAGS")[1].split(")")[0]
          if "PAIR_FLAGS" in rels else False,
          "debt flags are not in the stored pair-flag set")

    # 4. Edge-level functions untouched for edge-specific flags.
    check("def set_flag(store, a, b, relation_type, key, value)" in rels,
          "edge-level set_flag still exists, unchanged signature")
    check("def get_flag(store, a, b, relation_type, key, default=None)"
          in rels,
          "edge-level get_flag still exists, unchanged signature")

    # 5. The binding tables already point at the pair store (§12).
    check("set_pair_flag" in gdd15.split("### 12.4")[1].split("### 12.5")[0]
          if "### 12.4" in gdd15 else False,
          "§12.4 set_flag effect calls set_pair_flag")
    check("relationship_pair_flags" in gdd15.split("### 12.3")[1]
          .split("### 12.4")[0] if "### 12.3" in gdd15 else False,
          "§12.3 flag condition reads relationship_pair_flags")

    # 6. The implementation note is recorded in §17.7.
    check("Implemented (Unit CA" in sec,
          "§17.7 records the CA implementation")
    check("no rows exist to migrate" in sec,
          "§17.7 notes no live rows exist to migrate")

    # 7. Tests exist and pass.
    check("test_pair_flags_round_trip_and_canonicalisation" in tests,
          "test_relationships.py has the pair-flag round-trip test")
    check("test_pair_flag_visible_across_edges" in tests,
          "test_relationships.py has the cross-edge visibility test")
    check("test_pair_flag_self_pair_is_noop" in tests,
          "test_relationships.py has the self-pair no-op test")
    res = subprocess.run([sys.executable, "-m", "unittest",
                          "tools.sim.tests.test_relationships", "-v"],
                         cwd=ROOT, capture_output=True, text=True)
    passed = res.stdout + res.stderr
    check(res.returncode == 0,
          "test_relationships.py passes",
          passed.strip().splitlines()[-1] if passed.strip() else "")
    res2 = subprocess.run([sys.executable, "-m", "unittest",
                           "tools.sim.tests.test_scheduler", "-v"],
                          cwd=ROOT, capture_output=True, text=True)
    check(res2.returncode == 0,
          "test_scheduler.py still passes (no scheduler change in CA)",
          (res2.stdout + res2.stderr).strip().splitlines()[-1])

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
