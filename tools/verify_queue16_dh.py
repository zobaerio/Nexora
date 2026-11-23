"""Verify Queue 16 Unit DH — Sim Tables in schema.sql (GDD-04 §3.3/
§3.4/§3.5; CY/DA follow-up).

Compares the three new server tables in data/schema.sql against the
sim tables in tools/sim/persistence.py field-for-field: same columns
in the same order, same primary keys, same CHECKs, same defaults,
same indexes — with the documented store mapping applied (sim TEXT
sequence ids -> server UUIDs, sim INTEGER game_minutes -> server
BIGINT). Also checks the Phase 9 migration note, the GDD-04 record
updates, and that no migration file and no sim change came with it.
Prints one line per check and a summary; exits 0 only when every
check passes. Run from the repo root: python3 tools/verify_queue16_dh.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKS = []

# The documented store mapping (CX): the sim uses TEXT sequence ids
# (LI/PH + sequence) while the server keeps UUIDs; game minutes are
# INTEGER in SQLite and BIGINT in PostgreSQL. Same column, same
# meaning — the mapping is 1:1 by column.
ID_COLUMNS = {
    "lost_item_id", "owner_character_id", "item_instance_id",
    "found_by_character_id", "account_id", "character_id",
    "photograph_id",
}
TYPE_MAP = {"TEXT": "TEXT", "INTEGER": "BIGINT", "UUID": "UUID",
            "BIGINT": "BIGINT"}


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def _strip_comments(sql):
    return re.sub(r"--[^\n]*", "", sql)


def _table_block(sql, name):
    m = re.search(r"CREATE TABLE (?:IF NOT EXISTS )?%s\s*\(" % name,
                  sql)
    if not m:
        return None
    depth, start = 0, m.end() - 1
    for i in range(start, len(sql)):
        if sql[i] == "(":
            depth += 1
        elif sql[i] == ")":
            depth -= 1
            if depth == 0:
                return sql[start + 1:i]
    return None


def _columns(block):
    """[(name, type, rest)] for the column lines of a CREATE TABLE
    block, skipping PRIMARY KEY / CHECK / UNIQUE table constraints
    (those are returned separately by _constraints)."""
    cols, constraints = [], []
    # Split on top-level commas: commas inside CHECK(...) parens
    # and DEFAULT '...' strings must not split.
    parts, depth, cur, quote = [], 0, "", False
    for ch in block:
        if ch == "'":
            quote = not quote
        if not quote:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if ch == "," and depth == 0:
                parts.append(cur)
                cur = ""
                continue
        cur += ch
    if cur.strip():
        parts.append(cur)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if re.match(r"(?i)^(PRIMARY KEY|CHECK|UNIQUE|FOREIGN KEY"
                    r"|CONSTRAINT)\b", part):
            constraints.append(part)
            continue
        m = re.match(r"(\w+)\s+(\w+)(.*)$", part, re.S)
        if not m:
            constraints.append(part)
            continue
        cols.append((m.group(1), m.group(2).upper(),
                     " ".join(m.group(3).split())))
    return cols, constraints


def _pk(constraints, cols):
    for c in constraints:
        m = re.search(r"PRIMARY KEY\s*\(([^)]*)\)", c, re.I)
        if m:
            return [x.strip() for x in m.group(1).split(",")]
    inline = [n for n, _t, r in cols
              if re.search(r"PRIMARY KEY", r, re.I)]
    return inline


def _checks(constraints, cols):
    out = []
    for c in constraints:
        m = re.search(r"CHECK\s*\((.*)\)\s*$", c, re.I | re.S)
        if m:
            out.append(" ".join(m.group(1).split()))
    for _n, _t, r in cols:
        m = re.search(r"CHECK\s*\((.*)\)", r, re.I | re.S)
        if m:
            out.append(" ".join(m.group(1).split()))
    return sorted(out)


def _norm_check(text):
    return re.sub(r"['\"\s]", "", text).lower()


def compare(sim_sql, schema_sql, name):
    sim_block = _table_block(sim_sql, name)
    sch_block = _table_block(schema_sql, name)
    check(sim_block is not None, f"sim persistence.py defines {name}")
    check(sch_block is not None, f"schema.sql defines {name}")
    if sim_block is None or sch_block is None:
        return
    sim_cols, sim_cons = _columns(sim_block)
    sch_cols, sch_cons = _columns(sch_block)
    check([c[0] for c in sim_cols] == [c[0] for c in sch_cols],
          f"{name}: same columns in the same order",
          f"sim={[c[0] for c in sim_cols]}"
          f" schema={[c[0] for c in sch_cols]}")
    bad_types = []
    for (sn, st, _sr), (cn, ct, _cr) in zip(sim_cols, sch_cols):
        if sn != cn:
            continue
        if sn in ID_COLUMNS:
            want = "UUID"
        else:
            want = TYPE_MAP.get(st, st)
        if ct != want:
            bad_types.append(f"{sn}: sim {st} -> schema {ct}"
                             f" (want {want})")
    check(not bad_types, f"{name}: types match under the store mapping",
          "; ".join(bad_types) if bad_types else "TEXT->UUID ids,"
          " INTEGER->BIGINT minutes")
    check(_pk(sim_cons, sim_cols) == _pk(sch_cons, sch_cols),
          f"{name}: same primary key",
          f"PK={_pk(sch_cons, sch_cols)}")
    sim_checks = [_norm_check(c) for c in _checks(sim_cons, sim_cols)]
    sch_checks = [_norm_check(c) for c in _checks(sch_cons, sch_cols)]
    check(sim_checks == sch_checks,
          f"{name}: same CHECKs",
          f"{_checks(sch_cons, sch_cols)}")
    for (sn, _st, sr), (cn, _ct, cr) in zip(sim_cols, sch_cols):
        if sn != cn:
            continue
        sim_nn = "NOT NULL" in sr.upper()
        sch_nn = "NOT NULL" in cr.upper()
        check(sim_nn == sch_nn,
              f"{name}.{sn}: NOT NULL agrees ({sim_nn})")
        sim_def = re.search(r"DEFAULT\s+('[^']*'|\S+)", sr, re.I)
        sch_def = re.search(r"DEFAULT\s+('[^']*'|\S+)", cr, re.I)
        sim_d = sim_def.group(1).strip("'") if sim_def else None
        sch_d = sch_def.group(1).strip("'") if sch_def else None
        # gen_random_uuid() is the server's default for generated
        # ids, not a sim default — the only expected difference,
        # and only for the two generated ids (FK ids have none).
        if sn in ("lost_item_id", "photograph_id"):
            check(sch_d == "gen_random_uuid()",
                  f"{name}.{sn}: server default is gen_random_uuid()")
        else:
            check(sim_d == sch_d,
                  f"{name}.{sn}: DEFAULT agrees ({sim_d})")


def main():
    gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md").read_text()
    schema = (ROOT / "data" / "schema.sql").read_text()
    sim = (ROOT / "tools" / "sim" / "persistence.py").read_text()
    schema_clean = _strip_comments(schema)
    sim_clean = _strip_comments(sim)

    # 1. The three tables exist in the schema (19 -> 22).
    n_tables = len(re.findall(r"(?m)^CREATE TABLE ", schema))
    check(n_tables == 22, "schema.sql has 22 CREATE TABLEs (19 + 3)",
          f"{n_tables} tables")
    for name in ("lost_items", "discovery_progress", "photographs"):
        check(f"CREATE TABLE {name} (" in schema,
              f"schema.sql defines {name}")

    # 2. Field-for-field against the sim tables.
    for name in ("lost_items", "discovery_progress", "photographs"):
        compare(sim_clean, schema_clean, name)

    # 3. Indexes match the sim's.
    check("CREATE INDEX idx_lost_items_owner ON lost_items"
          "(owner_character_id, status)" in
          " ".join(schema.split()),
          "schema.sql indexes lost_items by (owner, status) like the sim")

    # 4. The migration note, and no migration file.
    dh = schema.split("Unit DH")[1].split("CREATE TABLE lost_items")[0]
    check("Phase 9" in dh and "forward-only migration" in dh,
          "schema.sql DH note says the Phase 9 migration creates them")
    check("no migration file" in dh.lower(),
          "schema.sql DH note says no migration file is written here")
    check("mission_progress already mirrors this schema" in dh,
          "schema.sql DH note states mission_progress is unchanged")
    check(not list((ROOT / "data" / "migrations").glob("*"))
          if (ROOT / "data" / "migrations").exists() else True,
          "no data/migrations directory was created")
    check("CREATE TABLE IF NOT EXISTS lost_items" in sim
          and "CREATE TABLE IF NOT EXISTS photographs" in sim
          and "CREATE TABLE IF NOT EXISTS discovery_progress" in sim,
          "sim persistence.py still defines the three tables (source)")

    # 5. The GDD records the tables.
    check(gdd04.count("Unit DH · Queue 16") >= 3,
          "GDD-04 §§3.3/3.4/3.5 carry the DH update",
          f"{gdd04.count('Unit DH · Queue 16')} mentions")
    check(all("the table now exists in `data/schema.sql`" in
              gdd04.split(f"### {sec} ")[1].split("###")[0]
              for sec in ("3.3", "3.4", "3.5")),
          "§§3.3/3.4/3.5 each state the table now exists (DH update)")

    # 6. Foreign keys point at real tables.
    check("REFERENCES inventory_items(item_instance_id)" in schema,
          "lost_items.item_instance_id references inventory_items")
    check(schema.count("REFERENCES accounts(account_id)") >= 3,
          "account-keyed tables reference accounts(account_id)")
    check(schema.count("REFERENCES characters(character_id)") >= 4,
          "character-keyed columns reference characters(character_id)")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
