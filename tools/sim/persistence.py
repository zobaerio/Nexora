"""SQLite persistence for the simulation core.

The table set mirrors data/schema.sql (the PostgreSQL Phase 9 design)
name-for-name and column-for-column wherever the sim exercises the
table, so the mapping proven here is the mapping the server will use.
SQLite adaptations: UUID -> TEXT ids, JSONB -> TEXT (JSON), TIMESTAMPTZ
dropped in favour of game_minutes (the design's own clock).

SIM-ONLY tables (structures schema.sql lacks — recorded as gaps for a
future schema revision; the PostgreSQL file is NOT modified by
Session 01):
- personality_profiles — the Session 01 extended 12-attribute profile
  (schema.sql stores only GDD-01's 5 canonical traits, on characters).
- needs_state — current need satisfactions per character.
- emotional_state — current emotional state per character.
- life_events — the event history (schema.sql scatters this across
  character_memories + flags; the sim keeps one explicit event log).
- decision_log — decision histories (Unit 08's audit trail).
- agent_state — current activity/anchor per agent (runtime state).
- instantiated_schedules — per-agent per-day schedule blocks.
- daily_weather — the deterministic daily weather record.
- characters.is_system — marks system accounts (city/employers/market)
  that schema.sql represents as reserved character rows.
- characters.first_name / last_name / birthplace / nationality /
  family_background — Session 01 Unit 01 identity fields that
  schema.sql folds into display_name / leaves implicit.
"""
import json
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS world_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    game_minutes INTEGER NOT NULL DEFAULT 480,
    time_scale REAL NOT NULL DEFAULT 60.0,
    weather_preset TEXT NOT NULL DEFAULT 'clear_day',
    schema_version INTEGER NOT NULL DEFAULT 1,
    sim_seed TEXT NOT NULL DEFAULT 'nexora-1',
    day_index INTEGER NOT NULL DEFAULT 0,
    population_generated INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS households (
    household_id TEXT PRIMARY KEY,
    name TEXT,
    home_property_id TEXT,
    district_id TEXT NOT NULL,
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    dissolved_at_game_minutes INTEGER
);
CREATE TABLE IF NOT EXISTS properties (
    property_id TEXT PRIMARY KEY,
    property_type TEXT NOT NULL,
    district_id TEXT NOT NULL,
    address_label TEXT NOT NULL,
    size_sqm REAL,
    tier INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'owned',
    construction_stage INTEGER NOT NULL DEFAULT 100,
    owner_character_id TEXT,
    owner_household_id TEXT,
    owner_business_id TEXT,
    market_value INTEGER NOT NULL DEFAULT 0,
    building_ref TEXT,
    unit_index INTEGER
);
CREATE TABLE IF NOT EXISTS characters (
    character_id TEXT PRIMARY KEY,
    account_id TEXT,
    is_player INTEGER NOT NULL DEFAULT 0,
    sim_tier TEXT NOT NULL DEFAULT 'scheduled',
    display_name TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    sex TEXT,
    born_at_game_minutes INTEGER NOT NULL,
    died_at_game_minutes INTEGER,
    aging_enabled INTEGER NOT NULL DEFAULT 1,
    household_id TEXT,
    residence_city TEXT NOT NULL DEFAULT 'Rupsha City',
    avatar_ref TEXT,
    trait_ambition INTEGER NOT NULL DEFAULT 50,
    trait_sociability INTEGER NOT NULL DEFAULT 50,
    trait_discipline INTEGER NOT NULL DEFAULT 50,
    trait_kindness INTEGER NOT NULL DEFAULT 50,
    trait_risk_tolerance INTEGER NOT NULL DEFAULT 50,
    balance_cached INTEGER NOT NULL DEFAULT 0,
    is_system INTEGER NOT NULL DEFAULT 0,
    birthplace TEXT,
    nationality TEXT,
    family_background TEXT
);
CREATE TABLE IF NOT EXISTS household_members (
    household_id TEXT NOT NULL,
    character_id TEXT NOT NULL,
    role TEXT NOT NULL,
    joined_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    left_at_game_minutes INTEGER,
    PRIMARY KEY (household_id, character_id)
);
CREATE TABLE IF NOT EXISTS tenancies (
    tenancy_id TEXT PRIMARY KEY,
    property_id TEXT NOT NULL,
    tenant_household_id TEXT NOT NULL,
    landlord_character_id TEXT,
    rent_per_month INTEGER NOT NULL,
    started_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    ended_at_game_minutes INTEGER
);
CREATE TABLE IF NOT EXISTS relationships (
    relationship_id TEXT PRIMARY KEY,
    from_character_id TEXT NOT NULL,
    to_character_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    trust INTEGER NOT NULL DEFAULT 0,
    affection INTEGER NOT NULL DEFAULT 0,
    respect INTEGER NOT NULL DEFAULT 0,
    flags TEXT NOT NULL DEFAULT '{}',
    last_interaction_at_game_minutes INTEGER,
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    UNIQUE (from_character_id, to_character_id, relation_type)
);
CREATE TABLE IF NOT EXISTS character_memories (
    memory_id TEXT PRIMARY KEY,
    character_id TEXT NOT NULL,
    other_character_id TEXT,
    event_type TEXT NOT NULL,
    emotional_weight INTEGER NOT NULL DEFAULT 0,
    details TEXT NOT NULL DEFAULT '{}',
    occurred_at_game_minutes INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memories_character
    ON character_memories(character_id, occurred_at_game_minutes);
CREATE TABLE IF NOT EXISTS character_skills (
    character_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    level INTEGER NOT NULL DEFAULT 0,
    experience INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (character_id, skill_id)
);
CREATE TABLE IF NOT EXISTS character_goals (
    goal_id TEXT PRIMARY KEY,
    character_id TEXT NOT NULL,
    goal_kind TEXT NOT NULL,
    goal_type TEXT NOT NULL,
    target TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'active',
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    completed_at_game_minutes INTEGER
);
CREATE TABLE IF NOT EXISTS businesses (
    business_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    business_type TEXT NOT NULL,
    owner_character_id TEXT NOT NULL,
    property_id TEXT,
    balance_cached INTEGER NOT NULL DEFAULT 0,
    founded_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    closed_at_game_minutes INTEGER
);
CREATE TABLE IF NOT EXISTS employments (
    employment_id TEXT PRIMARY KEY,
    character_id TEXT NOT NULL,
    profession_id TEXT NOT NULL,
    employer_business_id TEXT,
    employer_character_id TEXT,
    tier INTEGER NOT NULL DEFAULT 1,
    wage_per_month INTEGER NOT NULL DEFAULT 0,
    started_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    ended_at_game_minutes INTEGER
);
CREATE TABLE IF NOT EXISTS economy_ledger (
    ledger_id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_character_id TEXT,
    to_character_id TEXT,
    from_business_id TEXT,
    to_business_id TEXT,
    amount INTEGER NOT NULL CHECK (amount > 0),
    reason_code TEXT NOT NULL,
    related_property_id TEXT,
    related_business_id TEXT,
    note TEXT,
    game_minutes INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ledger_from ON economy_ledger(from_character_id);
CREATE INDEX IF NOT EXISTS idx_ledger_to ON economy_ledger(to_character_id);
-- SIM-ONLY tables (see module docstring) --------------------------------
CREATE TABLE IF NOT EXISTS personality_profiles (
    character_id TEXT PRIMARY KEY,
    extraversion INTEGER NOT NULL,
    confidence INTEGER NOT NULL,
    intelligence INTEGER NOT NULL,
    curiosity INTEGER NOT NULL,
    patience INTEGER NOT NULL,
    creativity INTEGER NOT NULL,
    ambition INTEGER NOT NULL,
    empathy INTEGER NOT NULL,
    risk_tolerance INTEGER NOT NULL,
    discipline INTEGER NOT NULL,
    cooperation INTEGER NOT NULL,
    emotional_sensitivity INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS needs_state (
    character_id TEXT PRIMARY KEY,
    hunger INTEGER NOT NULL DEFAULT 70,
    thirst INTEGER NOT NULL DEFAULT 70,
    sleep INTEGER NOT NULL DEFAULT 70,
    rest INTEGER NOT NULL DEFAULT 70,
    safety INTEGER NOT NULL DEFAULT 70,
    social INTEGER NOT NULL DEFAULT 60,
    healthcare INTEGER NOT NULL DEFAULT 80,
    financial INTEGER NOT NULL DEFAULT 50,
    education INTEGER NOT NULL DEFAULT 50,
    development INTEGER NOT NULL DEFAULT 50,
    updated_at_game_minutes INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS emotional_state (
    character_id TEXT PRIMARY KEY,
    happiness INTEGER NOT NULL DEFAULT 55,
    sadness INTEGER NOT NULL DEFAULT 20,
    stress INTEGER NOT NULL DEFAULT 30,
    fear INTEGER NOT NULL DEFAULT 10,
    anger INTEGER NOT NULL DEFAULT 10,
    excitement INTEGER NOT NULL DEFAULT 30,
    loneliness INTEGER NOT NULL DEFAULT 30,
    satisfaction INTEGER NOT NULL DEFAULT 50,
    motivation INTEGER NOT NULL DEFAULT 50
);
CREATE TABLE IF NOT EXISTS life_events (
    event_id TEXT PRIMARY KEY,
    character_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    other_character_id TEXT,
    details TEXT NOT NULL DEFAULT '{}',
    game_minutes INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_character ON life_events(character_id);
CREATE TABLE IF NOT EXISTS decision_log (
    decision_id TEXT PRIMARY KEY,
    character_id TEXT NOT NULL,
    decision_type TEXT NOT NULL,
    factors TEXT NOT NULL DEFAULT '{}',
    outcome TEXT NOT NULL DEFAULT '{}',
    game_minutes INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_state (
    character_id TEXT PRIMARY KEY,
    current_activity TEXT,
    current_location TEXT,
    current_zone TEXT,
    schedule_template_id TEXT,
    jitter_minutes INTEGER NOT NULL DEFAULT 0,
    rest_day INTEGER NOT NULL DEFAULT 0,
    life_stage TEXT
);
CREATE TABLE IF NOT EXISTS instantiated_schedules (
    character_id TEXT NOT NULL,
    day_index INTEGER NOT NULL,
    blocks_json TEXT NOT NULL,
    PRIMARY KEY (character_id, day_index)
);
CREATE TABLE IF NOT EXISTS daily_weather (
    day_index INTEGER PRIMARY KEY,
    preset_id TEXT NOT NULL
);
"""

SYSTEM_ACCOUNTS = ("SYS-CITY", "SYS-EMPLOYERS", "SYS-MARKET")


class Store:
    """One SQLite database = one simulated world. The file IS the save:
    closing and reopening it is save/restore (GDD-01 §9 local store)."""

    def __init__(self, path):
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        self._counters = {}

    def close(self):
        self.conn.commit()
        self.conn.close()

    # -- ids ---------------------------------------------------------------
    def next_id(self, prefix, table, column):
        if prefix not in self._counters:
            row = self.conn.execute(
                f"SELECT COUNT(*) AS n FROM {table}").fetchone()
            self._counters[prefix] = row["n"]
        self._counters[prefix] += 1
        return f"{prefix}{self._counters[prefix]:06d}"

    # -- generic row helpers -------------------------------------------------
    def insert(self, table, **row):
        cols = ", ".join(row.keys())
        marks = ", ".join("?" for _ in row)
        self.conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})",
                          tuple(row.values()))

    def rows(self, sql, params=()):
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def row(self, sql, params=()):
        r = self.conn.execute(sql, params).fetchone()
        return dict(r) if r else None

    def execute(self, sql, params=()):
        return self.conn.execute(sql, params)

    def commit(self):
        self.conn.commit()

    # -- world state ---------------------------------------------------------
    def world(self):
        return self.row("SELECT * FROM world_state WHERE id = 1")

    def init_world(self, seed, start_minutes=480):
        if self.world() is None:
            self.insert("world_state", id=1, game_minutes=start_minutes,
                        sim_seed=str(seed))
            for sid in SYSTEM_ACCOUNTS:
                self.insert("characters", character_id=sid,
                            display_name=f"System: {sid}",
                            sim_tier="ambient", sex=None,
                            born_at_game_minutes=0, is_system=1,
                            balance_cached=0)
            self.commit()

    def set_world(self, **fields):
        sets = ", ".join(f"{k} = ?" for k in fields)
        self.conn.execute(f"UPDATE world_state SET {sets} WHERE id = 1",
                          tuple(fields.values()))

    # -- money: the ledger is the truth (GDD-01 §8) ---------------------------
    def transfer(self, from_id, to_id, amount, reason, game_minutes,
                 note=None, related_property_id=None,
                 related_business_id=None):
        """Append-only ledger row + balance caches, one transaction.
        System accounts may go negative (they are the money source/sink);
        regular characters may not spend below zero — the caller checks,
        this method enforces it for non-system senders."""
        amount = int(amount)
        if amount <= 0:
            return None
        if from_id is not None and from_id not in SYSTEM_ACCOUNTS:
            bal = self.balance(from_id)
            if bal < amount:
                raise ValueError(
                    f"insufficient funds: {from_id} has {bal}, needs {amount}")
        lid = None
        cur = self.conn.execute(
            "INSERT INTO economy_ledger (from_character_id, to_character_id,"
            " amount, reason_code, related_property_id, related_business_id,"
            " note, game_minutes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (from_id, to_id, amount, reason, related_property_id,
             related_business_id, note, game_minutes))
        lid = cur.lastrowid
        if from_id is not None:
            self.conn.execute(
                "UPDATE characters SET balance_cached = balance_cached - ?"
                " WHERE character_id = ?", (amount, from_id))
        if to_id is not None:
            self.conn.execute(
                "UPDATE characters SET balance_cached = balance_cached + ?"
                " WHERE character_id = ?", (amount, to_id))
        return lid

    def balance(self, character_id):
        r = self.row("SELECT balance_cached FROM characters"
                     " WHERE character_id = ?", (character_id,))
        return r["balance_cached"] if r else 0

    def ledger_sum_check(self):
        """Reconciliation: every character's cache must equal its ledger
        sum (seed balances are ledger rows too, so this must hold
        exactly). Returns a list of mismatches — empty means the ledger
        and the caches agree (GDD-01 §8's reconciliation job)."""
        mismatches = []
        chars = self.rows("SELECT character_id, balance_cached FROM characters")
        for c in chars:
            cid = c["character_id"]
            inn = self.row(
                "SELECT COALESCE(SUM(amount),0) AS s FROM economy_ledger"
                " WHERE to_character_id = ?", (cid,))["s"]
            out = self.row(
                "SELECT COALESCE(SUM(amount),0) AS s FROM economy_ledger"
                " WHERE from_character_id = ?", (cid,))["s"]
            if inn - out != c["balance_cached"]:
                mismatches.append((cid, c["balance_cached"], inn - out))
        return mismatches
