-- ============================================================================
-- NEXORA — PostgreSQL schema draft v1.0 (Unit B)
-- Implements docs/GDD-01-LIFE-AND-DATA-MODEL.md.
--
-- Design laws (from the master plan, NEXORA-MIGRATION-PLAN.md):
--   * One data model from single-player (Phases 1-8, serialised into save
--     slots) to multiplayer (Phase 9, this schema on a server).
--   * The economy ledger is the ONLY truth for money. Balances are cached,
--     never authoritative. (GDD-01 §8)
--   * In Phase 9 the SERVER is the only writer of economy_ledger,
--     properties.owner_* and inventory rows. Clients request; server
--     validates and commits. Enforce with DB roles/grants at deploy time;
--     the shape below assumes that enforcement.
--   * Money is integer minor units (Nexora Credits). No floats near money.
--   * Age and life stage are DERIVED from born_at_game_minutes + the world
--     clock; they are never stored as editable columns. (GDD-01 §3)
--   * Characters are archived on death, never deleted: family trees,
--     memories and inheritance reference them forever. (GDD-01 §3, §6.4)
--
-- Game time: stored as BIGINT minutes since world epoch ("game_minutes")
-- so accelerated simulation and real-time play share one clock (Unit E).
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ----------------------------------------------------------------------------
-- accounts — the real person's login (GDD-01 §1). Phase 9: backed by EOS.
-- Account-level data survives character death.
-- ----------------------------------------------------------------------------
CREATE TABLE accounts (
    account_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        TEXT NOT NULL UNIQUE,               -- displayed as @username
    display_name    TEXT NOT NULL,
    auth_provider   TEXT NOT NULL DEFAULT 'eos',        -- eos | local (single-player profiles)
    auth_subject    TEXT,                               -- provider subject id; NULL for local
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at   TIMESTAMPTZ,
    is_banned       BOOLEAN NOT NULL DEFAULT FALSE
);
COMMENT ON TABLE accounts IS 'GDD-01 §1: real-person login; survives character death.';

-- ----------------------------------------------------------------------------
-- households — the economic unit sharing a home (GDD-01 §5).
-- home_property_id is filled after properties exist; FK added below.
-- ----------------------------------------------------------------------------
CREATE TABLE households (
    household_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT,                               -- e.g. "Hasan Household"
    home_property_id UUID,                              -- FK added after properties
    district_id     TEXT NOT NULL,                      -- matches GDD-02 district zone ids
    created_at_game_minutes BIGINT NOT NULL DEFAULT 0,
    dissolved_at_game_minutes BIGINT                  -- set when the household ends
);
COMMENT ON TABLE households IS 'GDD-01 §5: economic unit; members in household_members.';

-- ----------------------------------------------------------------------------
-- characters — one life inside NEXORA (GDD-01 §1, §2). Players and NPCs share
-- this table; sim_tier controls simulation depth, never the shape.
-- ----------------------------------------------------------------------------
CREATE TABLE characters (
    character_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id      UUID REFERENCES accounts(account_id),  -- NULL for NPCs
    is_player       BOOLEAN NOT NULL DEFAULT FALSE,
    sim_tier        TEXT NOT NULL DEFAULT 'scheduled'
                    CHECK (sim_tier IN ('full','scheduled','ambient')),
    display_name    TEXT NOT NULL,
    sex             TEXT CHECK (sex IN ('female','male')),
    born_at_game_minutes BIGINT NOT NULL,               -- age = world clock - this
    died_at_game_minutes BIGINT,                        -- NULL while alive
    aging_enabled   BOOLEAN NOT NULL DEFAULT TRUE,      -- players may opt out (GDD-01 §3)
    household_id    UUID REFERENCES households(household_id),
    residence_city  TEXT NOT NULL DEFAULT 'Rupsha City',
    avatar_ref      TEXT,                               -- MetaHuman param set / stage variant id
    -- Personality traits 0..100 (GDD-01 §2.1): behaviour weights, not flavour
    trait_ambition        SMALLINT NOT NULL DEFAULT 50 CHECK (trait_ambition BETWEEN 0 AND 100),
    trait_sociability     SMALLINT NOT NULL DEFAULT 50 CHECK (trait_sociability BETWEEN 0 AND 100),
    trait_discipline      SMALLINT NOT NULL DEFAULT 50 CHECK (trait_discipline BETWEEN 0 AND 100),
    trait_kindness        SMALLINT NOT NULL DEFAULT 50 CHECK (trait_kindness BETWEEN 0 AND 100),
    trait_risk_tolerance  SMALLINT NOT NULL DEFAULT 50 CHECK (trait_risk_tolerance BETWEEN 0 AND 100),
    -- Money cache: a performance copy ONLY. Truth = economy_ledger (GDD-01 §8).
    balance_cached  BIGINT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_characters_household ON characters(household_id);
CREATE INDEX idx_characters_account ON characters(account_id);
COMMENT ON TABLE characters IS 'GDD-01 §2: one life; players + NPCs, tiered simulation.';

-- Household members with roles (GDD-01 §5)
CREATE TABLE household_members (
    household_id    UUID NOT NULL REFERENCES households(household_id),
    character_id    UUID NOT NULL REFERENCES characters(character_id),
    role            TEXT NOT NULL CHECK (role IN ('head','partner','child','dependent','roommate')),
    joined_at_game_minutes BIGINT NOT NULL DEFAULT 0,
    left_at_game_minutes   BIGINT,
    PRIMARY KEY (household_id, character_id)
);

-- ----------------------------------------------------------------------------
-- properties — land and buildings (GDD-01 §5; master plan Part C #12).
-- Ownership changes are server-validated in Phase 9.
-- ----------------------------------------------------------------------------
CREATE TABLE properties (
    property_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_type   TEXT NOT NULL CHECK (property_type IN
                    ('plot','house','apartment','shop','office','factory','farm')),
    district_id     TEXT NOT NULL,                      -- GDD-02 zone ids
    address_label   TEXT NOT NULL,                      -- in-world address shown to players
    size_sqm        NUMERIC(10,2),
    tier            SMALLINT NOT NULL DEFAULT 1 CHECK (tier BETWEEN 1 AND 5),
    status          TEXT NOT NULL DEFAULT 'owned' CHECK (status IN
                    ('owned','rented','for_sale','for_rent','under_construction')),
    construction_stage SMALLINT NOT NULL DEFAULT 100 CHECK (construction_stage BETWEEN 0 AND 100),
    owner_character_id UUID REFERENCES characters(character_id),
    owner_household_id UUID REFERENCES households(household_id),
    owner_business_id  UUID,                            -- FK added after businesses
    market_value    BIGINT NOT NULL DEFAULT 0,          -- Nexora Credits, set by economy sim
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (num_nonnulls(owner_character_id, owner_household_id, owner_business_id) <= 1)
);
CREATE INDEX idx_properties_district ON properties(district_id);
CREATE INDEX idx_properties_owner_char ON properties(owner_character_id);
COMMENT ON TABLE properties IS 'GDD-01 §5: property; exactly one owner kind at a time.';

ALTER TABLE households
    ADD CONSTRAINT fk_households_home_property
    FOREIGN KEY (home_property_id) REFERENCES properties(property_id);

-- Tenancy: who rents which property from whom (renting is first-class, §5)
CREATE TABLE tenancies (
    tenancy_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id     UUID NOT NULL REFERENCES properties(property_id),
    tenant_household_id UUID NOT NULL REFERENCES households(household_id),
    rent_per_month  BIGINT NOT NULL CHECK (rent_per_month >= 0),
    started_at_game_minutes BIGINT NOT NULL DEFAULT 0,
    ended_at_game_minutes   BIGINT
);

-- ----------------------------------------------------------------------------
-- relationships — directed kinship + social edges (GDD-01 §6).
-- A->B is not B->A. Scores -100..100: trust / affection / respect.
-- ----------------------------------------------------------------------------
CREATE TABLE relationships (
    relationship_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_character_id UUID NOT NULL REFERENCES characters(character_id),
    to_character_id   UUID NOT NULL REFERENCES characters(character_id),
    relation_type   TEXT NOT NULL CHECK (relation_type IN
                    ('parent','child','sibling','partner','spouse','ex_partner',
                     'friend','best_friend','colleague','employer','employee',
                     'rival','acquaintance')),
    trust           SMALLINT NOT NULL DEFAULT 0 CHECK (trust BETWEEN -100 AND 100),
    affection       SMALLINT NOT NULL DEFAULT 0 CHECK (affection BETWEEN -100 AND 100),
    respect         SMALLINT NOT NULL DEFAULT 0 CHECK (respect BETWEEN -100 AND 100),
    flags           JSONB NOT NULL DEFAULT '{}'::jsonb,  -- semantic memory (§2.3)
    last_interaction_at_game_minutes BIGINT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (from_character_id, to_character_id, relation_type),
    CHECK (from_character_id <> to_character_id)
);
CREATE INDEX idx_relationships_from ON relationships(from_character_id);
CREATE INDEX idx_relationships_to ON relationships(to_character_id);
COMMENT ON TABLE relationships IS 'GDD-01 §6: directed edges; family tree + social graph.';

-- Episodic memory for full-tier characters (GDD-01 §2.3)
CREATE TABLE character_memories (
    memory_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id    UUID NOT NULL REFERENCES characters(character_id),
    other_character_id UUID REFERENCES characters(character_id),
    event_type      TEXT NOT NULL,   -- first_job | wedding | business_opened | accident | inheritance | helped_by_player | ...
    emotional_weight SMALLINT NOT NULL DEFAULT 0 CHECK (emotional_weight BETWEEN -100 AND 100),
    details         JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at_game_minutes BIGINT NOT NULL
);
CREATE INDEX idx_memories_character ON character_memories(character_id, occurred_at_game_minutes DESC);

-- Skills and goals (GDD-01 §2.1, §2.2)
CREATE TABLE character_skills (
    character_id    UUID NOT NULL REFERENCES characters(character_id),
    skill_id        TEXT NOT NULL,   -- engineering | driving | cooking | trading | medicine | teaching | ...
    level           SMALLINT NOT NULL DEFAULT 0 CHECK (level BETWEEN 0 AND 100),
    experience      BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (character_id, skill_id)
);

CREATE TABLE character_goals (
    goal_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id    UUID NOT NULL REFERENCES characters(character_id),
    goal_kind       TEXT NOT NULL CHECK (goal_kind IN ('life','stage','want')),
    goal_type       TEXT NOT NULL,   -- own_company | own_house | save_amount | reach_skill | marry | ...
    target          JSONB NOT NULL DEFAULT '{}'::jsonb,
    status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','completed','abandoned')),
    created_at_game_minutes BIGINT NOT NULL DEFAULT 0,
    completed_at_game_minutes BIGINT
);
CREATE INDEX idx_goals_character ON character_goals(character_id) WHERE status = 'active';

-- ----------------------------------------------------------------------------
-- businesses — companies owned by characters (GDD-01 §6.4, §7; Unit F detail)
-- ----------------------------------------------------------------------------
CREATE TABLE businesses (
    business_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    business_type   TEXT NOT NULL,   -- construction | retail | transport | restaurant | clinic | ...
    owner_character_id UUID NOT NULL REFERENCES characters(character_id),
    property_id     UUID REFERENCES properties(property_id),  -- premises, if any
    balance_cached  BIGINT NOT NULL DEFAULT 0,       -- cache only; ledger is truth
    founded_at_game_minutes BIGINT NOT NULL DEFAULT 0,
    closed_at_game_minutes  BIGINT
);
ALTER TABLE properties
    ADD CONSTRAINT fk_properties_owner_business
    FOREIGN KEY (owner_business_id) REFERENCES businesses(business_id);

-- Employments — profession history; current row has ended_at NULL (GDD-01 §1)
-- Profession catalogue itself lives in data/professions.json (Unit C).
CREATE TABLE employments (
    employment_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id    UUID NOT NULL REFERENCES characters(character_id),
    profession_id   TEXT NOT NULL,   -- matches professions.json ids
    employer_business_id UUID REFERENCES businesses(business_id),
    employer_character_id UUID REFERENCES characters(character_id),
    tier            SMALLINT NOT NULL DEFAULT 1 CHECK (tier BETWEEN 1 AND 5),
    wage_per_month  BIGINT NOT NULL DEFAULT 0,
    started_at_game_minutes BIGINT NOT NULL DEFAULT 0,
    ended_at_game_minutes   BIGINT
);
CREATE INDEX idx_employments_character ON employments(character_id) WHERE ended_at_game_minutes IS NULL;

-- ----------------------------------------------------------------------------
-- inventory — items owned by a character (master plan Phase 9 list).
-- Server-validated in multiplayer, like money and property.
-- ----------------------------------------------------------------------------
CREATE TABLE inventory_items (
    item_instance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_type       TEXT NOT NULL,   -- vehicle | furniture | tool | clothing | goods | document
    item_ref        TEXT NOT NULL,   -- catalogue id of the item kind
    owner_character_id UUID NOT NULL REFERENCES characters(character_id),
    location_property_id UUID REFERENCES properties(property_id),
    state           JSONB NOT NULL DEFAULT '{}'::jsonb,  -- condition, fuel, customisation...
    acquired_at_game_minutes BIGINT NOT NULL DEFAULT 0
);
CREATE INDEX idx_inventory_owner ON inventory_items(owner_character_id);

-- ----------------------------------------------------------------------------
-- economy_ledger — APPEND-ONLY. The only truth for money (GDD-01 §8).
-- System accounts (bank, city, employers-as-institutions) are rows in
-- characters with account_id NULL and a reserved display_name, or use the
-- well-known zero UUIDs documented in Unit F. Money is conserved:
-- every row moves value from one holder to another.
-- ----------------------------------------------------------------------------
CREATE TABLE economy_ledger (
    ledger_id       BIGSERIAL PRIMARY KEY,
    from_character_id UUID REFERENCES characters(character_id),
    to_character_id   UUID REFERENCES characters(character_id),
    from_business_id  UUID REFERENCES businesses(business_id),
    to_business_id    UUID REFERENCES businesses(business_id),
    amount          BIGINT NOT NULL CHECK (amount > 0),  -- Nexora Credits, integer
    reason_code     TEXT NOT NULL CHECK (reason_code IN
                    ('wage','rent','purchase','sale','tax','inheritance',
                     'mission_reward','loan_disburse','loan_repay','transfer',
                     'business_revenue','business_expense','fine','pension','seed')),
    related_property_id UUID REFERENCES properties(property_id),
    related_business_id UUID REFERENCES businesses(business_id),
    note            TEXT,
    game_minutes    BIGINT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_ledger_from_char ON economy_ledger(from_character_id, ledger_id);
CREATE INDEX idx_ledger_to_char ON economy_ledger(to_character_id, ledger_id);
COMMENT ON TABLE economy_ledger IS 'GDD-01 §8: append-only; server-only writes in Phase 9; balance caches must reconcile to this.';

-- ----------------------------------------------------------------------------
-- mission_progress + achievements (owner Phase 9 persistence list; Unit G
-- owns mission definitions — this is only the per-character state).
-- ----------------------------------------------------------------------------
CREATE TABLE mission_progress (
    character_id    UUID NOT NULL REFERENCES characters(character_id),
    mission_id      TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'available' CHECK (status IN
                    ('available','active','completed','failed')),
    progress        JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at_game_minutes BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (character_id, mission_id)
);

CREATE TABLE achievements (
    character_id    UUID NOT NULL REFERENCES characters(character_id),
    achievement_id  TEXT NOT NULL,
    unlocked_at_game_minutes BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (character_id, achievement_id)
);
-- KEYING DECISION (Unit BT · Queue 13 · 2026-11-22 — GDD-04 §5.1):
-- the character_id key above is WRONG against GDD-04 §5 + GDD-01 §1
-- (achievement data lives on the account and survives character death).
-- The account wins: the Phase 9 forward-only migration adds account_id,
-- backfills it from characters.account_id, and re-keys the primary key
-- to (account_id, achievement_id). No DDL is applied by this unit and
-- no live rows exist to migrate (the sim has no achievements table;
-- this schema is the Phase 9 draft). discovery_progress (GDD-04 §3.4)
-- is already account-keyed and is unchanged by the decision.

-- Account-level friendships between players (Phase 9 social list).
-- In-world character relationships live in `relationships`; this table is
-- the platform-level friend graph between accounts.
CREATE TABLE account_friendships (
    account_id      UUID NOT NULL REFERENCES accounts(account_id),
    friend_account_id UUID NOT NULL REFERENCES accounts(account_id),
    status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','accepted','blocked')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (account_id, friend_account_id),
    CHECK (account_id <> friend_account_id)
);

-- ----------------------------------------------------------------------------
-- save_slots — single-player mapping (GDD-01 §9). A slot serialises the
-- world tables above; schema_version drives forward-only migrations.
-- In Phase 9 this table is unused (characters live server-side) and the
-- character-select list replaces slots.
-- ----------------------------------------------------------------------------
CREATE TABLE save_slots (
    save_slot_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id      UUID NOT NULL REFERENCES accounts(account_id),
    character_id    UUID REFERENCES characters(character_id),
    slot_label      TEXT NOT NULL,
    schema_version  INTEGER NOT NULL DEFAULT 1,
    game_minutes    BIGINT NOT NULL DEFAULT 0,
    playtime_seconds BIGINT NOT NULL DEFAULT 0,
    payload_ref     TEXT,            -- local file path / blob key for the serialised world
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- World clock singleton (Unit E owns the runtime; the row persists it).
CREATE TABLE world_state (
    id              SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    game_minutes    BIGINT NOT NULL DEFAULT 480,     -- starts Day 1, 08:00
    time_scale      NUMERIC(6,2) NOT NULL DEFAULT 60.00,  -- game-min per real-min (design setting)
    weather_preset  TEXT NOT NULL DEFAULT 'clear_day',    -- data/weather-presets.json ids
    schema_version  INTEGER NOT NULL DEFAULT 1
);
INSERT INTO world_state (id) VALUES (1);

-- ============================================================================
-- End of schema draft v1.0. Changes require a migration note in the PR
-- (GDD-01 §10). Validated against the PostgreSQL grammar (pglast) at
-- authoring time; first real deployment is Phase 9 (or a local Phase 5
-- prototype store if the owner chooses Postgres early).
-- ============================================================================
