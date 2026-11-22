"""Verify Queue 13 Unit BV — GDD-15 §17.7 flag-visibility fix design
(the pair-level flag store; the limit Unit BF recorded in §17.3).

Checks the design against the sources it must resolve to: GDD-15
§12.1/§12.3/§12.4/§12.5/§17, GDD-01 §2.3/§6.1, tools/sim/
relationships.py, data/schema.sql.
Prints one line per check and a summary; exits 0 only when every check
passes. Run from the repo root: python3 tools/verify_queue13_bv.py
"""
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
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    gdd01 = (ROOT / "docs" / "GDD-01-LIFE-AND-DATA-MODEL.md").read_text()
    rels = (ROOT / "tools" / "sim" / "relationships.py").read_text()
    schema = (ROOT / "data" / "schema.sql").read_text()

    # 1. §17.7 exists, headed Unit BV, Queue 13.
    m177 = re.search(r"### 17\.7 The fix — flags live on the pair "
                     r"\(Unit BV · Queue 13", gdd15)
    check(m177 is not None, "GDD-15 §17.7 exists, headed Unit BV, Queue 13")
    sec = gdd15[m177.start():] if m177 else ""
    sec = sec.split("*End of GDD-15 §17.7")[0]

    # 2. The diagnosis: every shipped flag is a pair fact.
    check("pair facts, but the store holds them per edge" in sec
          or "a fact about the *pair*" in sec,
          "§17.7 diagnoses flags as pair facts stored per edge")
    for flag in ("met_player", "worked_with_player", "employs_player",
                 "apologised_for_offence"):
        check(flag in sec, f"§17.7 lists stored flag {flag} as moving")
    check("debt flags do **not** move" in sec,
          "§17.7 keeps the debt flags derived, not stored")

    # 3. The store: one row per unordered pair, canonical key.
    check("relationship_pair_flags" in sec,
          "§17.7 names the pair-level table")
    check("PRIMARY KEY (character_a_id, character_b_id)" in sec,
          "§17.7 gives the pair table's primary key")
    check("lexicographic order" in sec,
          "§17.7 canonicalises the pair key lexicographically")
    check("get_pair_flag" in sec and "set_pair_flag" in sec,
          "§17.7 names the pair-level accessors")
    check("minus `relation_type`" in sec,
          "§17.7 accessors drop the relation_type argument")

    # 4. The migration: merge rule, no live rows, forward-only.
    check("latest `last_interaction_at_game_minutes` wins" in sec,
          "§17.7 merge rule: latest interaction wins")
    check("§17.2 edge priority" in sec,
          "§17.7 merge rule ties break by §17.2 priority")
    check("no column is dropped" in sec,
          "§17.7 keeps the relationships.flags column")
    check("no down-migration" in sec,
          "§17.7 states the server migration has no down-migration")
    check("`set_flag()` has no sim callers" in sec,
          "§17.7 records no live flag rows exist to migrate")

    # 5. What changes: §12.1 snapshot + §17.3 read/write rules.
    check("relationship_pair_flags" in gdd15.split(
        "### 12.1 The conversation-time snapshot")[1].split("### 12.2")[0],
          "§12.1 snapshot table reads flags from the pair store")
    check("relationship_pair_flags" in gdd15.split(
        "| `flag` |")[1].split("\n")[0],
          "§12.3 flag condition reads the pair store")
    check("set_pair_flag" in gdd15.split("### 12.4 Effect application")[1]
          .split("### 12.5")[0],
          "§12.4 set_flag effect writes the pair store")
    check("§17.7" in gdd15.split("### 17.3 What the selected edge "
                                 "supplies")[1].split("### 17.4")[0],
          "§17.3 limit now points at §17.7")
    check("Resolved by design in §17.7" in gdd15,
          "§17.3 states the limit is resolved by design")

    # 6. What does not change: scores stay edge facts; drift target.
    check("scores *are* edge facts" in sec,
          "§17.7 keeps scores on the selected edge")
    check("band, mean, respect, and the drift target" in sec,
          "§17.7 keeps band/mean/respect/drift on the selected edge")

    # 7. The rejected alternative: union-read, with both reasons.
    check("union-read" in sec.lower(),
          "§17.7 names the rejected union-read alternative")
    check("Conflicts have no winner" in sec,
          "§17.7 rejects union-read: conflicts have no winner")
    check("model stays confused" in sec
          or "stays confused" in sec,
          "§17.7 rejects union-read: the home stays wrong")

    # 8. The sources agree: GDD-01 §2.3 defines semantic memory as
    #    pair facts; relationships.py stores flags per edge today.
    check("Semantic memory" in gdd01 and "flags like `met_player`" in gdd01,
          "GDD-01 §2.3 defines semantic memory with met_player")
    check("def set_flag(store, a, b, relation_type, key, value):" in rels,
          "relationships.py set_flag() is edge-scoped today (the bug)")
    check("flags           JSONB NOT NULL DEFAULT '{}'::jsonb" in schema,
          "schema.sql relationships.flags is a per-edge JSONB column")
    check("def get_flag(store, a, b, relation_type, key, default=None):"
          in rels,
          "relationships.py get_flag() is edge-scoped today")

    # 9. §12.8 G4 points at §17.7; no sim code changed.
    check("§17.7" in gdd15.split("**G4 — Which edge supplies the band.**")[1]
          .split("- **G5")[0],
          "§12.8 G4 points at §17.7")
    check("no sim code change" in sec.lower()
          or "adds no sim code change" in sec,
          "§17.7 is design only (no sim code changed)")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed; "
          f"{len(failed)} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
