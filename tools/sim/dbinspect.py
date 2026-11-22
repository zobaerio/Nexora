"""Session 10 — Database inspection.

A read-only structural audit of a world database: table census,
index inventory, declared foreign keys, PRAGMA
foreign_key_check, and orphan scans over the relations the
engine depends on. Nothing here writes.

An honest structural fact this surfaces: the SQLite schema
declares NO foreign-key constraints (integrity is enforced by
engine code, the append-only ledger/ballot triggers and the
unique indexes — mirroring how the sim was built session by
session). PRAGMA foreign_key_check therefore has nothing to
check; the orphan scans below are the operative integrity
evidence, and the report says so rather than dressing the
empty FK check up as a pass.
"""
import os
import sqlite3

# (label, sql counting rows whose referenced parent is missing)
_ORPHAN_SCANS = (
    ("employments.character_id -> characters",
     "SELECT COUNT(*) FROM employments e LEFT JOIN characters c"
     " ON c.character_id = e.character_id WHERE c.character_id"
     " IS NULL"),
    ("characters.household_id -> households",
     "SELECT COUNT(*) FROM characters ch LEFT JOIN households h"
     " ON h.household_id = ch.household_id WHERE ch.household_id"
     " IS NOT NULL AND h.household_id IS NULL"),
    ("household_members.household_id -> households",
     "SELECT COUNT(*) FROM household_members m LEFT JOIN"
     " households h ON h.household_id = m.household_id WHERE"
     " h.household_id IS NULL"),
    ("household_members.character_id -> characters",
     "SELECT COUNT(*) FROM household_members m LEFT JOIN"
     " characters c ON c.character_id = m.character_id WHERE"
     " c.character_id IS NULL"),
    ("economy_ledger.from_character_id -> characters",
     "SELECT COUNT(*) FROM economy_ledger l LEFT JOIN characters c"
     " ON c.character_id = l.from_character_id WHERE"
     " l.from_character_id IS NOT NULL AND c.character_id IS NULL"),
    ("economy_ledger.to_character_id -> characters",
     "SELECT COUNT(*) FROM economy_ledger l LEFT JOIN characters c"
     " ON c.character_id = l.to_character_id WHERE"
     " l.to_character_id IS NOT NULL AND c.character_id IS NULL"),
    ("economy_ledger.to_business_id -> businesses",
     "SELECT COUNT(*) FROM economy_ledger l LEFT JOIN businesses b"
     " ON b.business_id = l.to_business_id WHERE"
     " l.to_business_id IS NOT NULL AND b.business_id IS NULL"),
    ("business_inventory.business_id -> businesses",
     "SELECT COUNT(*) FROM business_inventory i LEFT JOIN"
     " businesses b ON b.business_id = i.business_id WHERE"
     " b.business_id IS NULL"),
    ("ballots.election_id -> elections",
     "SELECT COUNT(*) FROM ballots b LEFT JOIN elections e"
     " ON e.election_id = b.election_id WHERE e.election_id"
     " IS NULL"),
    ("trips.vehicle_id -> vehicles",
     "SELECT COUNT(*) FROM trips t LEFT JOIN vehicles v"
     " ON v.vehicle_id = t.vehicle_id WHERE t.vehicle_id"
     " IS NOT NULL AND v.vehicle_id IS NULL"),
    ("disaster_impacts.disaster_id -> disaster_events",
     "SELECT COUNT(*) FROM disaster_impacts i LEFT JOIN"
     " disaster_events d ON d.disaster_id = i.disaster_id WHERE"
     " d.disaster_id IS NULL"),
    ("tenancies.property_id -> properties",
     "SELECT COUNT(*) FROM tenancies t LEFT JOIN properties p"
     " ON p.property_id = t.property_id WHERE p.property_id"
     " IS NULL"),
    ("certifications.character_id -> characters",
     "SELECT COUNT(*) FROM certifications x LEFT JOIN characters c"
     " ON c.character_id = x.character_id WHERE c.character_id"
     " IS NULL"),
    ("research_records.project_id -> research_projects",
     "SELECT COUNT(*) FROM research_records r LEFT JOIN"
     " research_projects p ON p.project_id = r.project_id WHERE"
     " p.project_id IS NULL"),
)


def inspect_world(db_path):
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
            " AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        census = {}
        for t in tables:
            census[t] = conn.execute(
                f"SELECT COUNT(*) FROM \"{t}\"").fetchone()[0]
        indexes = [{"name": r[0], "table": r[1]} for r in
                   conn.execute(
                       "SELECT name, tbl_name FROM sqlite_master"
                       " WHERE type = 'index' AND name NOT LIKE"
                       " 'sqlite_%' ORDER BY name")]
        declared_fks = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type ="
            " 'table' AND sql LIKE '%FOREIGN KEY%'").fetchone()[0]
        fk_violations = conn.execute(
            "PRAGMA foreign_key_check").fetchall()
        orphans = {}
        for label, sql in _ORPHAN_SCANS:
            try:
                orphans[label] = conn.execute(sql).fetchone()[0]
            except sqlite3.Error as e:
                orphans[label] = f"scan error: {e}"
        dup_keys = conn.execute(
            "SELECT COUNT(*) FROM (SELECT transfer_key FROM"
            " economy_ledger WHERE transfer_key IS NOT NULL"
            " GROUP BY transfer_key HAVING COUNT(*) > 1)"
        ).fetchone()[0]
        dup_events = conn.execute(
            "SELECT COUNT(*) FROM (SELECT source_table, source_id"
            " FROM world_events GROUP BY source_table, source_id"
            " HAVING COUNT(*) > 1)").fetchone()[0] \
            if "world_events" in census else None
        return {
            "path": os.path.abspath(db_path),
            "size_bytes": os.path.getsize(db_path),
            "table_count": len(tables),
            "total_rows": sum(census.values()),
            "census": census,
            "empty_tables": sorted(t for t, n in census.items()
                                   if n == 0),
            "index_count": len(indexes),
            "indexes": indexes,
            "declared_foreign_key_tables": declared_fks,
            "foreign_key_check_violations": len(fk_violations),
            "orphan_scans": orphans,
            "duplicate_transfer_keys": dup_keys,
            "duplicate_registry_events": dup_events,
            "note": "The SQLite schema declares no FOREIGN KEY"
                    " constraints (integrity is engine-enforced:"
                    " append-only triggers, unique indexes,"
                    " reconciliation). foreign_key_check therefore"
                    " has nothing to check; the orphan scans are"
                    " the operative evidence.",
        }
    finally:
        conn.close()
