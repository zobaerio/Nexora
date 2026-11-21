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
- Session 02 additions (bottom of SCHEMA): relationship_history,
  social_profiles, household_finances, household_state, communities,
  community_members, household_culture, education_records,
  social_events, conflict_records, status_history,
  generational_history — all additive CREATE TABLE IF NOT EXISTS;
  schema.sql gaps they imply are listed in docs/SESSION-02-REPORT.md.
- Session 03 additions (bottom of SCHEMA): cities, city_zones,
  terrain_regions, land_parcels, parcel_history, building_state,
  road_segments, infrastructure_state, municipal_services,
  municipal_budgets, construction_projects, city_events,
  city_statistics, regional_connections, trade_flows,
  migration_records — the city/urban layer. schema.sql has a
  `properties` table (mirrored above) but no city, terrain, parcel,
  road, infrastructure, municipal or construction tables; each is
  recorded as a gap in docs/SESSION-03-REPORT.md.
- characters.is_system — marks system accounts (city/employers/market)
  that schema.sql represents as reserved character rows.
- Session 04 additions (bottom of SCHEMA): bank_accounts, loans,
  investments, business_inventory, inventory_movements,
  market_prices, price_history, vacancies, job_applications,
  business_monthly, business_events, economic_indicators,
  crisis_records, government_finance, household_consumption —
  the economy/business layer. schema.sql has a `businesses` table
  (mirrored above) but no banking, market, labour-market or
  indicator structures; each is recorded as a gap in
  docs/SESSION-04-REPORT.md. Two additive column migrations ride
  along (see MIGRATIONS): economy_ledger.transfer_key /
  event_ref (the owner's traceability order: every unit of money
  carries its idempotency key and the simulation event that
  caused it) and businesses.category / status.
- Session 06 additions (bottom of SCHEMA): educational_institutions,
  institution_departments, teacher_assignments, learning_records,
  assignments, examinations, examination_results, certifications,
  healthcare_facilities, health_profiles, health_conditions,
  patient_visits, treatment_records, hospital_admissions,
  medical_inventory, pharmacy_records, healthcare_budgets,
  disease_records, vaccination_records, wellbeing_records,
  research_projects, research_records,
  human_development_indicators — the education / healthcare /
  human-development layer. Enrolment stays education_records
  (Session 02), skills stay character_skills, careers stay
  employments; curricula/calendars live in the new config file.
  Each gap vs schema.sql is recorded in docs/SESSION-06-REPORT.md.
  One more column migration: world_state.humandev_setup.
- Session 05 additions (bottom of SCHEMA): countries, treasuries,
  institutions, offices, parties, party_memberships,
  citizen_opinion, opinion_snapshots, elections, ballots,
  citizen_feedback, policies, budgets, civil_service, laws,
  court_cases, incidents, audits, coi_records, integrity_reports,
  external_partners, agreements, development_plans,
  government_events — the government/politics layer. schema.sql
  has no government structures at all; each is recorded as a gap
  in docs/SESSION-05-REPORT.md. Ballots are append-only like the
  ledger (immutability triggers in _migrate). Two more column
  migrations: world_state.government_setup and
  vacancies.employer_account_id. Government authority exists
  ONLY as this in-simulation data — it grants nothing outside
  the sim (the owner's platform/government separation directive).
- characters.first_name / last_name / birthplace / nationality /
  family_background — Session 01 Unit 01 identity fields that
  schema.sql folds into display_name / leaves implicit.
- Session 07 additions (bottom of SCHEMA): vehicles, trips,
  road_loads, transit_routes, transit_runs, freight_shipments,
  vehicle_events, transport_statistics — the transportation
  layer. schema.sql has a vehicles concept only inside the UE
  design docs; none of these tables exist there, and each gap is
  recorded in docs/SESSION-07-REPORT.md. Two more column
  migrations: world_state.transport_setup and
  road_segments.closed (Session 03's road table gains the
  closure state Session 07 routing honours).
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
-- SESSION 02 tables (additive only; see SESSION-02-REPORT.md) ------------
-- relationship_history: formation/status history for relationship
-- rows. schema.sql's relationships table has created_at but no
-- history; recorded here as a schema gap.
CREATE TABLE IF NOT EXISTS relationship_history (
    history_id TEXT PRIMARY KEY,
    relationship_id TEXT,
    from_character_id TEXT NOT NULL,
    to_character_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    event TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '{}',
    game_minutes INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_relhist_pair
    ON relationship_history(from_character_id, to_character_id);
-- social_profiles: per-relationship social dynamics (familiarity,
-- conflict level, interaction count) keyed to a relationships row.
-- schema.sql has no equivalent; recorded as a gap.
CREATE TABLE IF NOT EXISTS social_profiles (
    relationship_id TEXT PRIMARY KEY,
    familiarity INTEGER NOT NULL DEFAULT 0,
    conflict INTEGER NOT NULL DEFAULT 0,
    interaction_count INTEGER NOT NULL DEFAULT 0,
    last_event TEXT,
    updated_at_game_minutes INTEGER NOT NULL DEFAULT 0
);
-- household_finances: one row per household per settled month —
-- the Family Economy Engine's record (Unit 03). schema.sql has no
-- household finance table; recorded as a gap.
CREATE TABLE IF NOT EXISTS household_finances (
    finance_id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL,
    month_index INTEGER NOT NULL,
    income_ncr INTEGER NOT NULL DEFAULT 0,
    food_ncr INTEGER NOT NULL DEFAULT 0,
    housing_ncr INTEGER NOT NULL DEFAULT 0,
    education_ncr INTEGER NOT NULL DEFAULT 0,
    healthcare_ncr INTEGER NOT NULL DEFAULT 0,
    transport_ncr INTEGER NOT NULL DEFAULT 0,
    other_ncr INTEGER NOT NULL DEFAULT 0,
    emergency_ncr INTEGER NOT NULL DEFAULT 0,
    savings_delta_ncr INTEGER NOT NULL DEFAULT 0,
    debt_after_ncr INTEGER NOT NULL DEFAULT 0,
    game_minutes INTEGER NOT NULL,
    UNIQUE (household_id, month_index)
);
CREATE TABLE IF NOT EXISTS household_state (
    household_id TEXT PRIMARY KEY,
    debt_ncr INTEGER NOT NULL DEFAULT 0,
    last_balance_total INTEGER,
    updated_at_game_minutes INTEGER NOT NULL DEFAULT 0
);
-- communities / community_members: schema.sql has no community
-- tables (districts only); recorded as a gap.
CREATE TABLE IF NOT EXISTS communities (
    community_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    leader_character_id TEXT,
    population INTEGER NOT NULL DEFAULT 0,
    participation_rate REAL NOT NULL DEFAULT 0,
    issues TEXT NOT NULL DEFAULT '[]',
    updated_at_game_minutes INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS community_members (
    community_id TEXT NOT NULL,
    character_id TEXT NOT NULL,
    joined_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    left_at_game_minutes INTEGER,
    PRIMARY KEY (community_id, character_id)
);
CREATE TABLE IF NOT EXISTS household_culture (
    household_id TEXT PRIMARY KEY,
    profile_id TEXT NOT NULL,
    assigned_at_game_minutes INTEGER NOT NULL DEFAULT 0
);
-- education_records: enrolment/credential facts (GDD-11). schema.sql
-- carries skills + goals but no enrolment record; recorded as a gap.
CREATE TABLE IF NOT EXISTS education_records (
    record_id TEXT PRIMARY KEY,
    character_id TEXT NOT NULL,
    institution_id TEXT NOT NULL,
    programme TEXT,
    status TEXT NOT NULL DEFAULT 'enrolled',
    attendance_rate REAL NOT NULL DEFAULT 0,
    performance INTEGER NOT NULL DEFAULT 0,
    parent_involvement INTEGER NOT NULL DEFAULT 0,
    started_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    completed_at_game_minutes INTEGER,
    UNIQUE (character_id, institution_id, programme)
);
CREATE TABLE IF NOT EXISTS social_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    zone_id TEXT,
    location_label TEXT,
    participant_ids TEXT NOT NULL DEFAULT '[]',
    outcome TEXT NOT NULL DEFAULT '{}',
    game_minutes INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS conflict_records (
    conflict_id TEXT PRIMARY KEY,
    a_character_id TEXT NOT NULL,
    b_character_id TEXT NOT NULL,
    cause TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    mediator_character_id TEXT,
    resolution TEXT,
    opened_at_game_minutes INTEGER NOT NULL,
    closed_at_game_minutes INTEGER
);
CREATE TABLE IF NOT EXISTS status_history (
    history_id TEXT PRIMARY KEY,
    character_id TEXT NOT NULL,
    dimension TEXT NOT NULL,
    from_value TEXT,
    to_value TEXT,
    game_minutes INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS generational_history (
    history_id TEXT PRIMARY KEY,
    character_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    related_character_id TEXT,
    generation INTEGER,
    details TEXT NOT NULL DEFAULT '{}',
    game_minutes INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_genhist_character
    ON generational_history(character_id);
-- SESSION 03 tables (additive only; see SESSION-03-REPORT.md) ------------
-- cities / city_zones: the city registry (Unit 01). schema.sql knows
-- districts only as TEXT ids on properties/households; a city layer
-- is a recorded gap.
CREATE TABLE IF NOT EXISTS cities (
    city_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    district_label TEXT,
    boundary TEXT NOT NULL DEFAULT '{}',
    climate TEXT,
    development_level TEXT,
    development_index REAL NOT NULL DEFAULT 0,
    economic_class TEXT,
    land_area_sqm REAL NOT NULL DEFAULT 0,
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    updated_at_game_minutes INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS city_zones (
    zone_id TEXT PRIMARY KEY,
    city_id TEXT NOT NULL,
    name TEXT,
    zone_category TEXT,
    bbox TEXT NOT NULL DEFAULT '{}'
);
-- terrain_regions: Unit 02. schema.sql has no terrain model; gap.
CREATE TABLE IF NOT EXISTS terrain_regions (
    region_id TEXT PRIMARY KEY,
    city_id TEXT NOT NULL,
    name TEXT NOT NULL,
    terrain_class TEXT NOT NULL,
    elevation_m REAL NOT NULL DEFAULT 0,
    bbox TEXT NOT NULL DEFAULT '{}',
    buildable INTEGER NOT NULL DEFAULT 1,
    restriction TEXT
);
-- land_parcels / parcel_history: Unit 03. schema.sql's properties
-- carry buildings, not the land under them; parcels are a gap.
CREATE TABLE IF NOT EXISTS land_parcels (
    parcel_id TEXT PRIMARY KEY,
    city_id TEXT NOT NULL,
    zone_id TEXT NOT NULL,
    building_id TEXT,
    x REAL NOT NULL, z REAL NOT NULL, w REAL NOT NULL, d REAL NOT NULL,
    area_sqm REAL NOT NULL,
    zoning_category TEXT,
    owner_kind TEXT NOT NULL DEFAULT 'private',
    owner_character_id TEXT,
    market_value INTEGER NOT NULL DEFAULT 0,
    development_status TEXT NOT NULL DEFAULT 'developed',
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS parcel_history (
    history_id TEXT PRIMARY KEY,
    parcel_id TEXT NOT NULL,
    event TEXT NOT NULL,
    from_owner TEXT,
    to_owner TEXT,
    value_ncr INTEGER,
    details TEXT NOT NULL DEFAULT '{}',
    game_minutes INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_parcelhist_parcel
    ON parcel_history(parcel_id);
-- building_state: Unit 05's extension of the building identities
-- that live in the buildings data files (floors/condition/value are
-- sim-maintained state, keyed by the data's building id — the
-- buildings themselves are NOT duplicated into a new table).
CREATE TABLE IF NOT EXISTS building_state (
    building_id TEXT PRIMARY KEY,
    city_id TEXT NOT NULL,
    floors INTEGER NOT NULL DEFAULT 1,
    construction_year INTEGER,
    condition REAL NOT NULL DEFAULT 85,
    maintenance_status TEXT NOT NULL DEFAULT 'good',
    economic_value INTEGER NOT NULL DEFAULT 0,
    updated_at_game_minutes INTEGER NOT NULL DEFAULT 0
);
-- road_segments: Unit 06's sim-maintained state (condition) over
-- the blockout data's segment identities. Nodes/graph topology are
-- derived from geometry in roads.py, never stored.
CREATE TABLE IF NOT EXISTS road_segments (
    segment_id TEXT PRIMARY KEY,
    city_id TEXT NOT NULL,
    name TEXT,
    road_class TEXT NOT NULL,
    length_m REAL NOT NULL DEFAULT 0,
    lanes INTEGER NOT NULL DEFAULT 1,
    speed_limit_kmh REAL NOT NULL DEFAULT 20,
    capacity_vph INTEGER NOT NULL DEFAULT 0,
    condition REAL NOT NULL DEFAULT 92,
    updated_at_game_minutes INTEGER NOT NULL DEFAULT 0
);
-- infrastructure_state: Unit 07, one row per (zone, network).
CREATE TABLE IF NOT EXISTS infrastructure_state (
    city_id TEXT NOT NULL,
    zone_id TEXT NOT NULL,
    network TEXT NOT NULL,
    capacity_units REAL NOT NULL DEFAULT 0,
    demand_units REAL NOT NULL DEFAULT 0,
    load_ratio REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ok',
    updated_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (zone_id, network)
);
-- municipal_services / municipal_budgets: Unit 09.
CREATE TABLE IF NOT EXISTS municipal_services (
    city_id TEXT NOT NULL,
    service TEXT NOT NULL,
    level REAL NOT NULL DEFAULT 0,
    spend_ncr INTEGER NOT NULL DEFAULT 0,
    month_index INTEGER NOT NULL DEFAULT 0,
    updated_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (city_id, service)
);
CREATE TABLE IF NOT EXISTS municipal_budgets (
    city_id TEXT NOT NULL,
    month_index INTEGER NOT NULL,
    revenue_tax_ncr INTEGER NOT NULL DEFAULT 0,
    revenue_rent_ncr INTEGER NOT NULL DEFAULT 0,
    revenue_other_ncr INTEGER NOT NULL DEFAULT 0,
    property_tax_ncr INTEGER NOT NULL DEFAULT 0,
    spend_services_ncr INTEGER NOT NULL DEFAULT 0,
    spend_construction_ncr INTEGER NOT NULL DEFAULT 0,
    city_balance_after INTEGER,
    game_minutes INTEGER NOT NULL,
    PRIMARY KEY (city_id, month_index)
);
-- construction_projects: Unit 11 (GDD-08's job record).
CREATE TABLE IF NOT EXISTS construction_projects (
    project_id TEXT PRIMARY KEY,
    city_id TEXT NOT NULL,
    parcel_id TEXT,
    kind TEXT NOT NULL DEFAULT 'new_build',
    target_building_id TEXT,
    client_character_id TEXT,
    engineer_character_id TEXT,
    plan TEXT NOT NULL DEFAULT '{}',
    stage TEXT NOT NULL DEFAULT 'planning',
    stage_day INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    estimate_materials_ncr INTEGER NOT NULL DEFAULT 0,
    fee_ncr INTEGER NOT NULL DEFAULT 0,
    funding_ncr INTEGER NOT NULL DEFAULT 0,
    spent_materials_ncr INTEGER NOT NULL DEFAULT 0,
    paid_engineer_ncr INTEGER NOT NULL DEFAULT 0,
    crew TEXT NOT NULL DEFAULT '[]',
    inspections TEXT NOT NULL DEFAULT '{}',
    defects TEXT NOT NULL DEFAULT '[]',
    result_building_id TEXT,
    created_day INTEGER NOT NULL DEFAULT 0,
    deadline_day INTEGER,
    completed_day INTEGER,
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    updated_at_game_minutes INTEGER NOT NULL DEFAULT 0
);
-- city_events: growth/development/municipal event log (Units 09/10).
CREATE TABLE IF NOT EXISTS city_events (
    event_id TEXT PRIMARY KEY,
    city_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '{}',
    game_minutes INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cityevents_city
    ON city_events(city_id, game_minutes);
-- city_statistics: Unit 13's monthly analytics snapshots (the
-- analytics themselves are computed live in analytics.py).
CREATE TABLE IF NOT EXISTS city_statistics (
    city_id TEXT NOT NULL,
    month_index INTEGER NOT NULL,
    metrics TEXT NOT NULL DEFAULT '{}',
    game_minutes INTEGER NOT NULL,
    PRIMARY KEY (city_id, month_index)
);
-- regional_connections / trade_flows / migration_records: Unit 14
-- + Unit 08's migration audit trail.
CREATE TABLE IF NOT EXISTS regional_connections (
    connection_id TEXT PRIMARY KEY,
    from_city_id TEXT NOT NULL,
    to_city_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    via TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    last_month_commuters INTEGER NOT NULL DEFAULT 0,
    last_month_migrants INTEGER NOT NULL DEFAULT 0,
    updated_at_game_minutes INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS trade_flows (
    flow_id TEXT PRIMARY KEY,
    month_index INTEGER NOT NULL,
    from_city_id TEXT NOT NULL,
    to_city_id TEXT NOT NULL,
    goods TEXT NOT NULL,
    amount_ncr INTEGER NOT NULL DEFAULT 0,
    game_minutes INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS migration_records (
    migration_id TEXT PRIMARY KEY,
    household_id TEXT NOT NULL,
    from_city_id TEXT NOT NULL,
    to_city_id TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '{}',
    game_minutes INTEGER NOT NULL
);
-- SESSION 04 tables (additive only; see SESSION-04-REPORT.md) ------------
-- bank_accounts / loans: the banking layer (Unit 08). An account's
-- balance is a liability record of the bank, reconciled against
-- the ledger: balance == deposits - withdrawals for that customer
-- (interest is paid out to cash, loans live in `loans`). schema.sql
-- has no banking tables; recorded as a gap.
CREATE TABLE IF NOT EXISTS bank_accounts (
    account_id TEXT PRIMARY KEY,
    character_id TEXT NOT NULL UNIQUE,
    account_type TEXT NOT NULL DEFAULT 'savings',
    balance_cached INTEGER NOT NULL DEFAULT 0,
    opened_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    closed_at_game_minutes INTEGER
);
CREATE TABLE IF NOT EXISTS loans (
    loan_id TEXT PRIMARY KEY,
    borrower_character_id TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'bank_loan',
    principal_ncr INTEGER NOT NULL,
    outstanding_ncr INTEGER NOT NULL,
    annual_rate_percent REAL NOT NULL,
    term_months INTEGER NOT NULL,
    months_elapsed INTEGER NOT NULL DEFAULT 0,
    interest_paid_ncr INTEGER NOT NULL DEFAULT 0,
    missed_payments INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    property_id TEXT,
    started_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    updated_at_game_minutes INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_loans_borrower
    ON loans(borrower_character_id, status);
-- investments: equity participation in real businesses (Unit 09).
-- Valuation is computed live from the business's net worth model;
-- only shares and the invested total are stored.
CREATE TABLE IF NOT EXISTS investments (
    investment_id TEXT PRIMARY KEY,
    character_id TEXT NOT NULL,
    business_id TEXT NOT NULL,
    shares INTEGER NOT NULL DEFAULT 0,
    invested_ncr INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    updated_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    UNIQUE (character_id, business_id)
);
-- business_inventory / inventory_movements: the goods layer
-- (Units 05/06/14). Every quantity change is a movement row with
-- its cause and counterparty — inventory is as auditable as money.
CREATE TABLE IF NOT EXISTS business_inventory (
    business_id TEXT NOT NULL,
    good_id TEXT NOT NULL,
    quantity REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (business_id, good_id)
);
CREATE TABLE IF NOT EXISTS inventory_movements (
    movement_id TEXT PRIMARY KEY,
    business_id TEXT NOT NULL,
    good_id TEXT NOT NULL,
    delta REAL NOT NULL,
    kind TEXT NOT NULL,
    counterparty_business_id TEXT,
    amount_ncr INTEGER NOT NULL DEFAULT 0,
    details TEXT NOT NULL DEFAULT '{}',
    game_minutes INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_invmove_business
    ON inventory_movements(business_id, game_minutes);
-- market_prices / price_history: Unit 07's dynamic price layer.
-- Every price change persists the signal values that caused it.
CREATE TABLE IF NOT EXISTS market_prices (
    city_id TEXT NOT NULL,
    good_id TEXT NOT NULL,
    price_ncr INTEGER NOT NULL,
    updated_month INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (city_id, good_id)
);
CREATE TABLE IF NOT EXISTS price_history (
    history_id TEXT PRIMARY KEY,
    city_id TEXT NOT NULL,
    good_id TEXT NOT NULL,
    old_price_ncr INTEGER NOT NULL,
    new_price_ncr INTEGER NOT NULL,
    signals TEXT NOT NULL DEFAULT '{}',
    game_minutes INTEGER NOT NULL
);
-- vacancies / job_applications: Unit 03's labour market.
CREATE TABLE IF NOT EXISTS vacancies (
    vacancy_id TEXT PRIMARY KEY,
    employer_kind TEXT NOT NULL DEFAULT 'business',
    employer_business_id TEXT,
    profession_id TEXT NOT NULL,
    city_id TEXT,
    wage_per_month INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'open',
    filled_by_character_id TEXT,
    posted_month INTEGER NOT NULL DEFAULT 0,
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    closed_at_game_minutes INTEGER
);
CREATE TABLE IF NOT EXISTS job_applications (
    application_id TEXT PRIMARY KEY,
    vacancy_id TEXT NOT NULL,
    character_id TEXT NOT NULL,
    score REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    game_minutes INTEGER NOT NULL
);
-- business_monthly / business_events: per-business P&L history
-- (Unit 04) and the business audit trail (founding, capital,
-- distress, closure, dividend and investment events).
CREATE TABLE IF NOT EXISTS business_monthly (
    business_id TEXT NOT NULL,
    month_index INTEGER NOT NULL,
    revenue_ncr INTEGER NOT NULL DEFAULT 0,
    costs_ncr INTEGER NOT NULL DEFAULT 0,
    tax_ncr INTEGER NOT NULL DEFAULT 0,
    profit_ncr INTEGER NOT NULL DEFAULT 0,
    employees INTEGER NOT NULL DEFAULT 0,
    status_after TEXT NOT NULL DEFAULT 'active',
    PRIMARY KEY (business_id, month_index)
);
CREATE TABLE IF NOT EXISTS business_events (
    event_id TEXT PRIMARY KEY,
    business_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '{}',
    game_minutes INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_bizevents_business
    ON business_events(business_id, game_minutes);
-- economic_indicators: Unit 11's monthly snapshots (the
-- indicators themselves are computed live in indicators.py;
-- methodology documented there).
CREATE TABLE IF NOT EXISTS economic_indicators (
    scope TEXT NOT NULL,
    month_index INTEGER NOT NULL,
    metrics TEXT NOT NULL DEFAULT '{}',
    game_minutes INTEGER NOT NULL,
    PRIMARY KEY (scope, month_index)
);
-- crisis_records: Unit 12's measured crisis detections.
CREATE TABLE IF NOT EXISTS crisis_records (
    crisis_id TEXT PRIMARY KEY,
    crisis_type TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'national',
    status TEXT NOT NULL DEFAULT 'active',
    severity TEXT NOT NULL DEFAULT '{}',
    opened_month INTEGER NOT NULL DEFAULT 0,
    opened_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    resolved_at_game_minutes INTEGER,
    clean_months INTEGER NOT NULL DEFAULT 0,
    details TEXT NOT NULL DEFAULT '{}'
);
-- government_finance: Unit 10's per-city monthly public accounts,
-- summed from the ledger itself (revenue by reason) and from the
-- municipal expenditure records.
CREATE TABLE IF NOT EXISTS government_finance (
    city_id TEXT NOT NULL,
    month_index INTEGER NOT NULL,
    revenue_income_tax_ncr INTEGER NOT NULL DEFAULT 0,
    revenue_business_tax_ncr INTEGER NOT NULL DEFAULT 0,
    revenue_property_tax_ncr INTEGER NOT NULL DEFAULT 0,
    revenue_sales_tax_ncr INTEGER NOT NULL DEFAULT 0,
    revenue_tariff_ncr INTEGER NOT NULL DEFAULT 0,
    revenue_rent_ncr INTEGER NOT NULL DEFAULT 0,
    revenue_other_ncr INTEGER NOT NULL DEFAULT 0,
    spend_services_ncr INTEGER NOT NULL DEFAULT 0,
    spend_construction_ncr INTEGER NOT NULL DEFAULT 0,
    spend_pensions_ncr INTEGER NOT NULL DEFAULT 0,
    spend_other_ncr INTEGER NOT NULL DEFAULT 0,
    city_balance_after INTEGER,
    public_debt_ncr INTEGER NOT NULL DEFAULT 0,
    game_minutes INTEGER NOT NULL,
    PRIMARY KEY (city_id, month_index)
);
-- household_consumption: Unit 14's goods-layer record of what a
-- household actually consumed (and what it could not get).
CREATE TABLE IF NOT EXISTS household_consumption (
    household_id TEXT NOT NULL,
    month_index INTEGER NOT NULL,
    good_id TEXT NOT NULL,
    units REAL NOT NULL DEFAULT 0,
    spend_ncr INTEGER NOT NULL DEFAULT 0,
    unmet_units REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (household_id, month_index, good_id)
);
-- SESSION 05 tables (additive only; see SESSION-05-REPORT.md) ------------
-- The government/politics layer. schema.sql has no government
-- structures; every table here is a recorded gap. All authority in
-- these tables is in-simulation data only (owner's separation
-- directive): an office row can move simulated money through the
-- ledger; it grants no access to anything outside the sim.
-- countries: the data model supports multiple countries; exactly
-- one is populated (a second record is constructible — Unit 01's
-- test does that without fabricating a second nation).
CREATE TABLE IF NOT EXISTS countries (
    country_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    capital_city_id TEXT,
    currency_code TEXT,
    next_election_month INTEGER,
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0
);
-- treasuries: the Session 04 deferred question answered — SYS-CITY
-- stays the NATIONAL treasury; each city gains its own municipal
-- treasury account (a system character row) by a recorded,
-- conservation-preserving allocation (see government.py).
CREATE TABLE IF NOT EXISTS treasuries (
    account_id TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    city_id TEXT,
    label TEXT,
    opening_balance_ncr INTEGER NOT NULL DEFAULT 0,
    opening_advance_ncr INTEGER NOT NULL DEFAULT 0,
    opened_at_game_minutes INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS institutions (
    institution_id TEXT PRIMARY KEY,
    country_id TEXT NOT NULL,
    name TEXT NOT NULL,
    branch TEXT NOT NULL,
    level TEXT NOT NULL DEFAULT 'national',
    city_id TEXT,
    authority TEXT NOT NULL DEFAULT '[]',
    account_id TEXT,
    active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS offices (
    office_id TEXT PRIMARY KEY,
    institution_id TEXT NOT NULL,
    title TEXT NOT NULL,
    holder_character_id TEXT,
    constituency_city_id TEXT,
    appointed_via TEXT,
    term_started_at_game_minutes INTEGER,
    term_ended_at_game_minutes INTEGER,
    status TEXT NOT NULL DEFAULT 'vacant'
);
CREATE INDEX IF NOT EXISTS idx_offices_holder
    ON offices(holder_character_id, status);
CREATE TABLE IF NOT EXISTS parties (
    party_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    short TEXT,
    account_id TEXT,
    leader_character_id TEXT,
    stances TEXT NOT NULL DEFAULT '{}',
    platform TEXT,
    status TEXT NOT NULL DEFAULT 'registered',
    founded_at_game_minutes INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS party_memberships (
    party_id TEXT NOT NULL,
    character_id TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    joined_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    left_at_game_minutes INTEGER,
    PRIMARY KEY (party_id, character_id)
);
CREATE TABLE IF NOT EXISTS citizen_opinion (
    character_id TEXT PRIMARY KEY,
    approval REAL NOT NULL DEFAULT 50,
    support_party_id TEXT,
    components TEXT NOT NULL DEFAULT '{}',
    updated_month INTEGER NOT NULL DEFAULT 0,
    updated_at_game_minutes INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS opinion_snapshots (
    month_index INTEGER PRIMARY KEY,
    mean_approval REAL,
    support_shares TEXT NOT NULL DEFAULT '{}',
    respondents INTEGER NOT NULL DEFAULT 0,
    game_minutes INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS elections (
    election_id TEXT PRIMARY KEY,
    country_id TEXT NOT NULL,
    month_index INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled',
    rules TEXT NOT NULL DEFAULT '{}',
    turnout INTEGER NOT NULL DEFAULT 0,
    eligible INTEGER NOT NULL DEFAULT 0,
    results TEXT NOT NULL DEFAULT '{}',
    winner_party_id TEXT,
    game_minutes INTEGER
);
-- ballots: one row per voter per election, enforced by the UNIQUE
-- constraint; append-only via triggers (see _migrate), like the
-- ledger — a cast ballot can never be edited or removed.
CREATE TABLE IF NOT EXISTS ballots (
    ballot_id TEXT PRIMARY KEY,
    election_id TEXT NOT NULL,
    character_id TEXT NOT NULL,
    city_id TEXT NOT NULL,
    party_id TEXT NOT NULL,
    game_minutes INTEGER NOT NULL,
    UNIQUE (election_id, character_id)
);
CREATE INDEX IF NOT EXISTS idx_ballots_election
    ON ballots(election_id);
CREATE TABLE IF NOT EXISTS citizen_feedback (
    feedback_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    character_id TEXT,
    topic TEXT NOT NULL,
    stance TEXT,
    details TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'open',
    response TEXT,
    created_at_game_minutes INTEGER NOT NULL,
    closed_at_game_minutes INTEGER
);
CREATE TABLE IF NOT EXISTS policies (
    policy_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    institution_id TEXT,
    city_id TEXT,
    proposed_by TEXT,
    approved_by TEXT,
    status TEXT NOT NULL DEFAULT 'proposed',
    budget_ncr INTEGER NOT NULL DEFAULT 0,
    duration_months INTEGER NOT NULL DEFAULT 0,
    months_run INTEGER NOT NULL DEFAULT 0,
    expected TEXT NOT NULL DEFAULT '{}',
    actual TEXT NOT NULL DEFAULT '{}',
    created_month INTEGER NOT NULL DEFAULT 0,
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    ended_at_game_minutes INTEGER
);
CREATE TABLE IF NOT EXISTS budgets (
    budget_id TEXT PRIMARY KEY,
    fiscal_year INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    forecast_revenue_ncr INTEGER NOT NULL DEFAULT 0,
    allocations TEXT NOT NULL DEFAULT '{}',
    actuals TEXT NOT NULL DEFAULT '{}',
    approved_by TEXT,
    borrowed_loan_id TEXT,
    created_month INTEGER NOT NULL DEFAULT 0,
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    closed_at_game_minutes INTEGER
);
CREATE TABLE IF NOT EXISTS civil_service (
    record_id TEXT PRIMARY KEY,
    character_id TEXT NOT NULL,
    institution_id TEXT NOT NULL,
    vacancy_id TEXT,
    role TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    evaluation_score REAL,
    evaluations INTEGER NOT NULL DEFAULT 0,
    started_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    ended_at_game_minutes INTEGER
);
CREATE TABLE IF NOT EXISTS laws (
    law_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    kind TEXT NOT NULL,
    effect TEXT NOT NULL DEFAULT '{}',
    proposed_by TEXT,
    status TEXT NOT NULL DEFAULT 'proposed',
    debate TEXT NOT NULL DEFAULT '[]',
    votes_for INTEGER NOT NULL DEFAULT 0,
    votes_against INTEGER NOT NULL DEFAULT 0,
    effective_month INTEGER,
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    enacted_at_game_minutes INTEGER
);
-- court_cases: allegation and finding are separate columns by
-- design (Unit 10): an allegation is a claim recorded from a real
-- sim dispute; only a judgment writes the finding.
CREATE TABLE IF NOT EXISTS court_cases (
    case_id TEXT PRIMARY KEY,
    case_type TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    plaintiff_id TEXT,
    defendant_id TEXT,
    allegation TEXT NOT NULL DEFAULT '{}',
    finding TEXT,
    status TEXT NOT NULL DEFAULT 'filed',
    judge_character_id TEXT,
    judgment TEXT,
    remedy_ncr INTEGER NOT NULL DEFAULT 0,
    appeal_of TEXT,
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    closed_at_game_minutes INTEGER,
    UNIQUE (source_kind, source_ref)
);
CREATE TABLE IF NOT EXISTS incidents (
    incident_id TEXT PRIMARY KEY,
    incident_type TEXT NOT NULL,
    city_id TEXT,
    source_kind TEXT,
    source_ref TEXT,
    reporter_character_id TEXT,
    officer_character_id TEXT,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'reported',
    outcome TEXT,
    case_id TEXT,
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    closed_at_game_minutes INTEGER,
    UNIQUE (source_kind, source_ref)
);
CREATE INDEX IF NOT EXISTS idx_incidents_city
    ON incidents(city_id, status);
CREATE TABLE IF NOT EXISTS audits (
    audit_id TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    month_index INTEGER NOT NULL DEFAULT 0,
    discrepancies TEXT NOT NULL DEFAULT '[]',
    discrepancy_count INTEGER NOT NULL DEFAULT 0,
    result TEXT NOT NULL,
    integrity_index REAL,
    auditor_character_id TEXT,
    game_minutes INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS coi_records (
    coi_id TEXT PRIMARY KEY,
    character_id TEXT NOT NULL,
    office_id TEXT NOT NULL,
    business_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'declared',
    detected_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    UNIQUE (office_id, business_id)
);
CREATE TABLE IF NOT EXISTS integrity_reports (
    report_id TEXT PRIMARY KEY,
    reporter_character_id TEXT,
    subject_character_id TEXT,
    allegation TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'filed',
    outcome TEXT,
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    closed_at_game_minutes INTEGER
);
-- external_partners: the ONE external counterpart is a labelled
-- model account (like the SYS accounts), never a populated nation.
CREATE TABLE IF NOT EXISTS external_partners (
    partner_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    account_id TEXT,
    relation_score REAL NOT NULL DEFAULT 50,
    model_note TEXT,
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS agreements (
    agreement_id TEXT PRIMARY KEY,
    partner_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    terms TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'proposed',
    signed_by TEXT,
    started_month INTEGER,
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS development_plans (
    plan_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    targets TEXT NOT NULL DEFAULT '{}',
    baseline TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'active',
    created_month INTEGER NOT NULL DEFAULT 0,
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS government_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    actor_character_id TEXT,
    details TEXT NOT NULL DEFAULT '{}',
    game_minutes INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_govevents_type
    ON government_events(event_type, game_minutes);
-- SESSION 06 tables (additive only; see SESSION-06-REPORT.md) ------------
-- The education / healthcare / human-development layer. The spec's
-- table list is mapped onto what exists (education_records IS the
-- enrolment table; character_skills the skills table; employments
-- the career history) — only genuinely new structures are created:
-- educational_institutions, teacher_assignments, learning_records,
-- assignments, examinations, examination_results, certifications,
-- healthcare_facilities, health_profiles, health_conditions,
-- patient_visits, treatment_records, hospital_admissions,
-- medical_inventory, pharmacy_records, healthcare_budgets,
-- disease_records, vaccination_records, wellbeing_records,
-- research_projects, research_records, human_development_indicators.
-- Curricula and academic calendars live in the configuration file
-- (data/education-health-config.json), the project's pattern for
-- frameworks (cf. parties/laws in government-config.json). schema.sql
-- has enrolment (education_records, Session 02) but none of these;
-- each is recorded as a gap in docs/SESSION-06-REPORT.md.
CREATE TABLE IF NOT EXISTS educational_institutions (
    institution_id TEXT PRIMARY KEY,
    building_id TEXT NOT NULL,
    city_id TEXT NOT NULL,
    institution_type TEXT NOT NULL,
    name TEXT NOT NULL,
    level TEXT NOT NULL DEFAULT 'school',
    capacity_students INTEGER NOT NULL DEFAULT 0,
    monthly_budget_ncr INTEGER NOT NULL DEFAULT 0,
    budget_spent_month_ncr INTEGER NOT NULL DEFAULT 0,
    performance_score REAL,
    research_capability REAL NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS institution_departments (
    institution_id TEXT NOT NULL,
    department TEXT NOT NULL,
    PRIMARY KEY (institution_id, department)
);
CREATE TABLE IF NOT EXISTS teacher_assignments (
    assignment_id TEXT PRIMARY KEY,
    character_id TEXT NOT NULL,
    institution_id TEXT NOT NULL,
    month_index INTEGER NOT NULL,
    subject TEXT NOT NULL DEFAULT 'general_studies',
    evaluation_score REAL,
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    UNIQUE (character_id, month_index)
);
CREATE INDEX IF NOT EXISTS idx_tassign_institution
    ON teacher_assignments(institution_id, month_index);
CREATE TABLE IF NOT EXISTS learning_records (
    record_id TEXT PRIMARY KEY,
    character_id TEXT NOT NULL,
    institution_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    proficiency REAL NOT NULL DEFAULT 0,
    months_studied INTEGER NOT NULL DEFAULT 0,
    updated_month INTEGER NOT NULL DEFAULT 0,
    UNIQUE (character_id, subject_id)
);
CREATE TABLE IF NOT EXISTS assignments (
    assignment_id TEXT PRIMARY KEY,
    character_id TEXT NOT NULL,
    institution_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    month_index INTEGER NOT NULL,
    assigned_count INTEGER NOT NULL DEFAULT 0,
    completed_count INTEGER NOT NULL DEFAULT 0,
    UNIQUE (character_id, subject_id, month_index)
);
CREATE TABLE IF NOT EXISTS examinations (
    exam_id TEXT PRIMARY KEY,
    institution_id TEXT NOT NULL,
    level TEXT NOT NULL,
    month_index INTEGER NOT NULL,
    game_minutes INTEGER NOT NULL,
    candidates INTEGER NOT NULL DEFAULT 0,
    mean_score REAL,
    UNIQUE (institution_id, month_index)
);
CREATE TABLE IF NOT EXISTS examination_results (
    result_id TEXT PRIMARY KEY,
    exam_id TEXT NOT NULL,
    character_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    score REAL NOT NULL,
    grade TEXT NOT NULL,
    attendance_rate REAL NOT NULL,
    proficiency REAL NOT NULL,
    teacher_score REAL NOT NULL,
    institution_score REAL NOT NULL,
    jitter REAL NOT NULL DEFAULT 0,
    UNIQUE (exam_id, character_id, subject_id)
);
CREATE INDEX IF NOT EXISTS idx_examres_student
    ON examination_results(character_id);
CREATE TABLE IF NOT EXISTS certifications (
    certification_id TEXT PRIMARY KEY,
    character_id TEXT NOT NULL,
    institution_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    programme TEXT,
    mean_score REAL,
    issued_month INTEGER NOT NULL,
    game_minutes INTEGER NOT NULL,
    UNIQUE (character_id, kind, programme)
);
CREATE TABLE IF NOT EXISTS healthcare_facilities (
    facility_id TEXT PRIMARY KEY,
    building_id TEXT NOT NULL,
    city_id TEXT NOT NULL,
    facility_type TEXT NOT NULL,
    name TEXT NOT NULL,
    equipment_level REAL NOT NULL DEFAULT 0,
    monthly_budget_ncr INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS health_profiles (
    character_id TEXT PRIMARY KEY,
    health_score REAL NOT NULL DEFAULT 80,
    fitness REAL NOT NULL DEFAULT 50,
    chronic INTEGER NOT NULL DEFAULT 0,
    chronic_label TEXT,
    disability INTEGER NOT NULL DEFAULT 0,
    conditions_total INTEGER NOT NULL DEFAULT 0,
    last_condition_at_game_minutes INTEGER,
    updated_month INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS health_conditions (
    condition_id TEXT PRIMARY KEY,
    character_id TEXT NOT NULL,
    band TEXT NOT NULL,
    cause TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    treated INTEGER NOT NULL DEFAULT 0,
    complicated INTEGER NOT NULL DEFAULT 0,
    facility_id TEXT,
    visit_id TEXT,
    started_day INTEGER NOT NULL,
    recovery_end_day INTEGER,
    closed_day INTEGER,
    outcome TEXT,
    details TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_conditions_character
    ON health_conditions(character_id, status);
CREATE TABLE IF NOT EXISTS patient_visits (
    visit_id TEXT PRIMARY KEY,
    character_id TEXT NOT NULL,
    facility_id TEXT NOT NULL,
    visit_type TEXT NOT NULL,
    stage TEXT NOT NULL DEFAULT 'registered',
    condition_id TEXT,
    doctor_character_id TEXT,
    registered_day INTEGER NOT NULL,
    assessed_day INTEGER,
    treated_day INTEGER,
    closed_day INTEGER,
    diagnosis_ok INTEGER,
    medication_item_id TEXT,
    follow_up_of TEXT,
    details TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_visits_facility_stage
    ON patient_visits(facility_id, stage);
CREATE TABLE IF NOT EXISTS treatment_records (
    treatment_id TEXT PRIMARY KEY,
    visit_id TEXT NOT NULL,
    condition_id TEXT,
    character_id TEXT NOT NULL,
    facility_id TEXT NOT NULL,
    doctor_character_id TEXT,
    action TEXT NOT NULL,
    medication_item_id TEXT,
    day_index INTEGER NOT NULL,
    game_minutes INTEGER NOT NULL,
    details TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS hospital_admissions (
    admission_id TEXT PRIMARY KEY,
    visit_id TEXT NOT NULL,
    character_id TEXT NOT NULL,
    facility_id TEXT NOT NULL,
    referred_off_district INTEGER NOT NULL DEFAULT 0,
    transfer_days INTEGER NOT NULL DEFAULT 0,
    admitted_day INTEGER NOT NULL,
    discharged_day INTEGER
);
CREATE TABLE IF NOT EXISTS medical_inventory (
    facility_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (facility_id, item_id)
);
CREATE TABLE IF NOT EXISTS pharmacy_records (
    record_id TEXT PRIMARY KEY,
    facility_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    change INTEGER NOT NULL,
    reason TEXT NOT NULL,
    visit_id TEXT,
    month_index INTEGER,
    game_minutes INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS healthcare_budgets (
    budget_id TEXT PRIMARY KEY,
    facility_id TEXT NOT NULL,
    month_index INTEGER NOT NULL,
    allocated_ncr INTEGER NOT NULL DEFAULT 0,
    procurement_ncr INTEGER NOT NULL DEFAULT 0,
    campaign_ncr INTEGER NOT NULL DEFAULT 0,
    patients_seen INTEGER NOT NULL DEFAULT 0,
    ledger_ids TEXT NOT NULL DEFAULT '[]',
    UNIQUE (facility_id, month_index)
);
CREATE TABLE IF NOT EXISTS disease_records (
    record_id TEXT PRIMARY KEY,
    disease_id TEXT NOT NULL,
    character_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'infectious',
    source TEXT NOT NULL,
    infected_day INTEGER NOT NULL,
    recovered_day INTEGER,
    immune_until_day INTEGER,
    city_id TEXT,
    UNIQUE (character_id, disease_id, infected_day)
);
CREATE INDEX IF NOT EXISTS idx_disease_status
    ON disease_records(disease_id, status);
CREATE TABLE IF NOT EXISTS vaccination_records (
    record_id TEXT PRIMARY KEY,
    character_id TEXT NOT NULL,
    disease_id TEXT NOT NULL,
    facility_id TEXT NOT NULL,
    day_index INTEGER NOT NULL,
    game_minutes INTEGER NOT NULL,
    UNIQUE (character_id, disease_id, day_index)
);
CREATE TABLE IF NOT EXISTS wellbeing_records (
    record_id TEXT PRIMARY KEY,
    character_id TEXT NOT NULL,
    month_index INTEGER NOT NULL,
    stress REAL NOT NULL,
    social_support REAL NOT NULL,
    loneliness REAL NOT NULL,
    work_life REAL NOT NULL,
    wellbeing_score REAL NOT NULL,
    UNIQUE (character_id, month_index)
);
CREATE TABLE IF NOT EXISTS research_projects (
    project_id TEXT PRIMARY KEY,
    institution_id TEXT NOT NULL,
    lead_character_id TEXT,
    field TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    budget_ncr INTEGER NOT NULL DEFAULT 0,
    started_month INTEGER NOT NULL,
    ends_month INTEGER NOT NULL,
    completed_month INTEGER,
    game_minutes INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS research_records (
    record_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    institution_id TEXT NOT NULL,
    field TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'publication',
    month_index INTEGER NOT NULL,
    game_minutes INTEGER NOT NULL,
    details TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS human_development_indicators (
    snapshot_id TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    month_index INTEGER NOT NULL,
    game_minutes INTEGER NOT NULL,
    indicators TEXT NOT NULL DEFAULT '{}',
    UNIQUE (scope, month_index)
);
-- Session 07 additions: the transportation layer. Vehicles are
-- persistent entities; trips are the physical movement record
-- every journey leaves; road_loads is the day's measured traffic
-- (the congestion evidence); transit routes/runs, freight
-- shipments (Session 04 orders made physical) and monthly
-- transport statistics complete the layer.
CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id TEXT PRIMARY KEY,
    vehicle_type TEXT NOT NULL,
    owner_character_id TEXT,
    owner_business_id TEXT,
    operator_character_id TEXT,
    city_id TEXT,
    home_zone TEXT,
    current_zone TEXT,
    fuel_litres REAL NOT NULL DEFAULT 0,
    fuel_capacity_litres REAL NOT NULL DEFAULT 0,
    odometer_km REAL NOT NULL DEFAULT 0,
    condition REAL NOT NULL DEFAULT 92,
    status TEXT NOT NULL DEFAULT 'active',
    acquisition TEXT NOT NULL DEFAULT 'fleet',
    acquired_at_game_minutes INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_vehicles_owner
    ON vehicles(owner_character_id);
CREATE INDEX IF NOT EXISTS idx_vehicles_operator
    ON vehicles(operator_character_id);
CREATE TABLE IF NOT EXISTS trips (
    trip_id TEXT PRIMARY KEY,
    character_id TEXT,
    day_index INTEGER NOT NULL,
    purpose TEXT NOT NULL,
    origin_zone TEXT NOT NULL,
    destination_zone TEXT NOT NULL,
    mode TEXT NOT NULL,
    vehicle_id TEXT,
    route_id TEXT,
    segment_ids TEXT NOT NULL DEFAULT '[]',
    distance_m REAL NOT NULL DEFAULT 0,
    depart_minute INTEGER NOT NULL,
    free_flow_min REAL NOT NULL DEFAULT 0,
    travel_min REAL NOT NULL DEFAULT 0,
    arrive_minute INTEGER NOT NULL DEFAULT 0,
    fare_ncr INTEGER NOT NULL DEFAULT 0,
    fare_basis TEXT NOT NULL DEFAULT 'none',
    fuel_litres REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'completed',
    details TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_trips_day ON trips(day_index);
CREATE INDEX IF NOT EXISTS idx_trips_character
    ON trips(character_id, day_index);
CREATE TABLE IF NOT EXISTS road_loads (
    day_index INTEGER NOT NULL,
    segment_id TEXT NOT NULL,
    hour INTEGER NOT NULL,
    vehicle_count REAL NOT NULL DEFAULT 0,
    capacity_vph REAL NOT NULL DEFAULT 0,
    congestion_factor REAL NOT NULL DEFAULT 1,
    PRIMARY KEY (day_index, segment_id, hour)
);
CREATE TABLE IF NOT EXISTS transit_routes (
    route_id TEXT PRIMARY KEY,
    city_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    stops_json TEXT NOT NULL DEFAULT '[]',
    headway_min INTEGER NOT NULL DEFAULT 30,
    capacity_per_hour INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active'
);
CREATE TABLE IF NOT EXISTS transit_runs (
    run_id TEXT PRIMARY KEY,
    route_id TEXT NOT NULL,
    day_index INTEGER NOT NULL,
    hour INTEGER NOT NULL,
    boardings INTEGER NOT NULL DEFAULT 0,
    capacity INTEGER NOT NULL DEFAULT 0,
    UNIQUE (route_id, day_index, hour)
);
CREATE TABLE IF NOT EXISTS freight_shipments (
    shipment_id TEXT PRIMARY KEY,
    month_index INTEGER NOT NULL,
    kind TEXT NOT NULL DEFAULT 'supply_order',
    from_business_id TEXT,
    to_business_id TEXT,
    from_city_id TEXT,
    to_city_id TEXT,
    good_id TEXT,
    units REAL NOT NULL DEFAULT 0,
    vehicle_id TEXT,
    segment_ids TEXT NOT NULL DEFAULT '[]',
    distance_km REAL NOT NULL DEFAULT 0,
    freight_ncr INTEGER NOT NULL DEFAULT 0,
    departed_at INTEGER NOT NULL DEFAULT 0,
    free_flow_min REAL NOT NULL DEFAULT 0,
    travel_min REAL NOT NULL DEFAULT 0,
    arrives_at INTEGER NOT NULL DEFAULT 0,
    delay_min REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'in_transit',
    details TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_shipments_status
    ON freight_shipments(status);
CREATE TABLE IF NOT EXISTS vehicle_events (
    event_id TEXT PRIMARY KEY,
    vehicle_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    game_minutes INTEGER NOT NULL,
    details TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS transport_statistics (
    snapshot_id TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    month_index INTEGER NOT NULL,
    game_minutes INTEGER NOT NULL,
    statistics TEXT NOT NULL DEFAULT '{}',
    UNIQUE (scope, month_index)
);
-- Session 08 environment layer: regional weather, hydrology,
-- soil/crops, vegetation/wildlife indices, pollution, trends and
-- disaster records. schema.sql has no environmental model; gap.
CREATE TABLE IF NOT EXISTS env_weather (
    region_id TEXT NOT NULL,
    day_index INTEGER NOT NULL,
    preset_id TEXT NOT NULL,
    season_id TEXT NOT NULL,
    temp_day_c REAL NOT NULL DEFAULT 0,
    temp_night_c REAL NOT NULL DEFAULT 0,
    humidity_pct REAL NOT NULL DEFAULT 0,
    pressure_hpa REAL NOT NULL DEFAULT 1013,
    wind_kmh REAL NOT NULL DEFAULT 0,
    wind_dir_deg REAL NOT NULL DEFAULT 0,
    cloud_pct REAL NOT NULL DEFAULT 0,
    precip_mm REAL NOT NULL DEFAULT 0,
    visibility_km REAL NOT NULL DEFAULT 20,
    sunrise_min INTEGER NOT NULL DEFAULT 360,
    sunset_min INTEGER NOT NULL DEFAULT 1080,
    PRIMARY KEY (region_id, day_index)
);
CREATE TABLE IF NOT EXISTS env_water_state (
    city_id TEXT PRIMARY KEY,
    river_level_m REAL NOT NULL DEFAULT 1.2,
    surface_storage_mm REAL NOT NULL DEFAULT 0,
    groundwater_index REAL NOT NULL DEFAULT 0.7,
    flood_active INTEGER NOT NULL DEFAULT 0,
    updated_day INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS env_events (
    event_id TEXT PRIMARY KEY,
    city_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    day_index INTEGER NOT NULL,
    details TEXT NOT NULL DEFAULT '{}',
    game_minutes INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_envevents_city
    ON env_events(city_id, day_index);
CREATE TABLE IF NOT EXISTS env_soil (
    parcel_id TEXT PRIMARY KEY,
    moisture REAL NOT NULL DEFAULT 0.5,
    fertility REAL NOT NULL DEFAULT 0.7,
    updated_day INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS env_crops (
    crop_record_id TEXT PRIMARY KEY,
    parcel_id TEXT NOT NULL,
    city_id TEXT NOT NULL,
    crop_id TEXT NOT NULL,
    planted_month INTEGER NOT NULL DEFAULT 0,
    planted_day INTEGER NOT NULL DEFAULT 0,
    growth_score REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'growing',
    harvest_units REAL NOT NULL DEFAULT 0,
    updated_day INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_envcrops_parcel
    ON env_crops(parcel_id, status);
CREATE TABLE IF NOT EXISTS env_vegetation (
    region_key TEXT PRIMARY KEY,
    city_id TEXT NOT NULL,
    name TEXT,
    habitat_class TEXT NOT NULL,
    cover_index REAL NOT NULL DEFAULT 0.5,
    updated_day INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS env_wildlife (
    region_key TEXT PRIMARY KEY,
    city_id TEXT NOT NULL,
    habitat_class TEXT NOT NULL,
    population_index REAL NOT NULL DEFAULT 0.5,
    updated_day INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS env_pollution (
    city_id TEXT NOT NULL,
    month_index INTEGER NOT NULL,
    air_index REAL NOT NULL DEFAULT 0,
    water_index REAL NOT NULL DEFAULT 0,
    sources TEXT NOT NULL DEFAULT '{}',
    game_minutes INTEGER NOT NULL,
    PRIMARY KEY (city_id, month_index)
);
CREATE TABLE IF NOT EXISTS env_snapshots (
    city_id TEXT NOT NULL,
    month_index INTEGER NOT NULL,
    metrics TEXT NOT NULL DEFAULT '{}',
    game_minutes INTEGER NOT NULL,
    PRIMARY KEY (city_id, month_index)
);
CREATE TABLE IF NOT EXISTS disaster_events (
    disaster_id TEXT PRIMARY KEY,
    scenario_id TEXT,
    disaster_type TEXT NOT NULL,
    city_id TEXT NOT NULL,
    intensity REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    started_day INTEGER NOT NULL,
    ends_day INTEGER,
    affected_population INTEGER NOT NULL DEFAULT 0,
    damage_estimate_ncr INTEGER NOT NULL DEFAULT 0,
    relief_paid_ncr INTEGER NOT NULL DEFAULT 0,
    repair_spent_ncr INTEGER NOT NULL DEFAULT 0,
    details TEXT NOT NULL DEFAULT '{}',
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    recovered_at_game_minutes INTEGER
);
CREATE TABLE IF NOT EXISTS disaster_impacts (
    impact_id TEXT PRIMARY KEY,
    disaster_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    ref_id TEXT NOT NULL,
    city_id TEXT NOT NULL,
    zone_id TEXT,
    damage REAL NOT NULL DEFAULT 0,
    repaired REAL NOT NULL DEFAULT 0,
    details TEXT NOT NULL DEFAULT '{}',
    game_minutes INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_disimpacts_disaster
    ON disaster_impacts(disaster_id, kind);
CREATE TABLE IF NOT EXISTS disaster_responses (
    response_id TEXT PRIMARY KEY,
    disaster_id TEXT NOT NULL,
    action TEXT NOT NULL,
    ref_id TEXT,
    amount_ncr INTEGER NOT NULL DEFAULT 0,
    details TEXT NOT NULL DEFAULT '{}',
    game_minutes INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_disresponses_disaster
    ON disaster_responses(disaster_id);
-- SESSION 09 tables (additive only; see SESSION-09-REPORT.md) ------------
-- Agent coordination layer: a registry over the actors the earlier
-- sessions already created (never duplicate entities), extended
-- personal goals (columns on character_goals via MIGRATIONS),
-- structured negotiations, supply orders (the measured basis for
-- supplier selection), decision explanations, multi-level memory,
-- agent messages, forecasts with scored outcomes, city/national
-- assessments, disaster coordination tasks, executed/failed action
-- records, bounded learning parameters and goal progress history.
-- data/schema.sql has no agent-coordination model; gap recorded.
CREATE TABLE IF NOT EXISTS agent_registry (
    agent_id TEXT PRIMARY KEY,
    agent_class TEXT NOT NULL,
    ref_id TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    capabilities TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'active',
    registered_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    updated_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    UNIQUE (agent_class, ref_id)
);
CREATE TABLE IF NOT EXISTS agent_params (
    owner_ref TEXT NOT NULL,
    param TEXT NOT NULL,
    value REAL NOT NULL,
    PRIMARY KEY (owner_ref, param)
);
CREATE TABLE IF NOT EXISTS agent_learning (
    record_id TEXT PRIMARY KEY,
    owner_ref TEXT NOT NULL,
    param TEXT NOT NULL,
    old_value REAL NOT NULL,
    new_value REAL NOT NULL,
    reason TEXT NOT NULL DEFAULT '{}',
    game_minutes INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_learning_owner
    ON agent_learning(owner_ref, game_minutes);
CREATE TABLE IF NOT EXISTS negotiations (
    negotiation_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    vacancy_id TEXT,
    party_a_ref TEXT NOT NULL,
    party_b_ref TEXT NOT NULL,
    objective TEXT NOT NULL DEFAULT '{}',
    constraints TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'open',
    rounds INTEGER NOT NULL DEFAULT 0,
    final_terms TEXT NOT NULL DEFAULT '{}',
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    closed_at_game_minutes INTEGER
);
CREATE TABLE IF NOT EXISTS negotiation_offers (
    offer_id TEXT PRIMARY KEY,
    negotiation_id TEXT NOT NULL,
    round INTEGER NOT NULL,
    from_ref TEXT NOT NULL,
    amount_ncr INTEGER NOT NULL DEFAULT 0,
    response TEXT NOT NULL,
    game_minutes INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_offers_negotiation
    ON negotiation_offers(negotiation_id, round);
CREATE TABLE IF NOT EXISTS supply_orders (
    order_id TEXT PRIMARY KEY,
    month_index INTEGER NOT NULL,
    buyer_business_id TEXT NOT NULL,
    seller_business_id TEXT NOT NULL,
    good_id TEXT NOT NULL,
    units REAL NOT NULL DEFAULT 0,
    amount_ncr INTEGER NOT NULL DEFAULT 0,
    game_minutes INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_supply_orders_seller
    ON supply_orders(seller_business_id, good_id, month_index);
CREATE TABLE IF NOT EXISTS agent_decisions (
    record_id TEXT PRIMARY KEY,
    agent_ref TEXT NOT NULL,
    agent_class TEXT NOT NULL,
    decision_kind TEXT NOT NULL,
    inputs TEXT NOT NULL DEFAULT '{}',
    rule TEXT NOT NULL DEFAULT '',
    outcome TEXT NOT NULL DEFAULT '{}',
    game_minutes INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_agentdecisions_agent
    ON agent_decisions(agent_ref, game_minutes);
CREATE TABLE IF NOT EXISTS agent_memories (
    memory_id TEXT PRIMARY KEY,
    level TEXT NOT NULL,
    owner_ref TEXT NOT NULL,
    event_kind TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '{}',
    importance INTEGER NOT NULL DEFAULT 0,
    access_count INTEGER NOT NULL DEFAULT 0,
    compressed INTEGER NOT NULL DEFAULT 0,
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    updated_at_game_minutes INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_agentmem_owner
    ON agent_memories(level, owner_ref, importance);
CREATE TABLE IF NOT EXISTS agent_messages (
    message_id TEXT PRIMARY KEY,
    from_ref TEXT NOT NULL,
    to_ref TEXT NOT NULL,
    kind TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}',
    game_minutes INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS forecasts (
    forecast_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    scope TEXT NOT NULL,
    made_month INTEGER NOT NULL,
    horizon_months INTEGER NOT NULL DEFAULT 1,
    target_month INTEGER NOT NULL,
    inputs TEXT NOT NULL DEFAULT '{}',
    predicted TEXT NOT NULL DEFAULT '{}',
    actual TEXT,
    score TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    scored_at_game_minutes INTEGER
);
CREATE INDEX IF NOT EXISTS idx_forecasts_target
    ON forecasts(status, target_month);
CREATE TABLE IF NOT EXISTS assessments (
    assessment_id TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    problem_kind TEXT NOT NULL,
    month_index INTEGER NOT NULL,
    indicator TEXT NOT NULL DEFAULT '{}',
    baseline REAL,
    current_value REAL,
    action_kind TEXT,
    action_ref TEXT,
    status TEXT NOT NULL DEFAULT 'identified',
    evaluation TEXT,
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    updated_at_game_minutes INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_assessments_open
    ON assessments(scope, problem_kind, status);
CREATE TABLE IF NOT EXISTS coordination_tasks (
    task_id TEXT PRIMARY KEY,
    disaster_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    assigned_ref TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    details TEXT NOT NULL DEFAULT '{}',
    created_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    updated_at_game_minutes INTEGER NOT NULL DEFAULT 0,
    completed_at_game_minutes INTEGER,
    UNIQUE (disaster_id, kind)
);
CREATE TABLE IF NOT EXISTS agent_actions (
    action_id TEXT PRIMARY KEY,
    agent_ref TEXT NOT NULL,
    action_kind TEXT NOT NULL,
    status TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '{}',
    game_minutes INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_agentactions_agent
    ON agent_actions(agent_ref, game_minutes);
CREATE TABLE IF NOT EXISTS goal_progress_log (
    log_id TEXT PRIMARY KEY,
    goal_id TEXT NOT NULL,
    character_id TEXT NOT NULL,
    progress REAL NOT NULL,
    measured TEXT NOT NULL DEFAULT '{}',
    game_minutes INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_goalprogress_goal
    ON goal_progress_log(goal_id, game_minutes);
CREATE TABLE IF NOT EXISTS agent_perf (
    perf_id TEXT PRIMARY KEY,
    agent_class TEXT NOT NULL,
    pass_kind TEXT NOT NULL,
    duration_ms REAL NOT NULL DEFAULT 0,
    agents_updated INTEGER NOT NULL DEFAULT 0,
    game_minutes INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_agentperf_pass
    ON agent_perf(pass_kind, game_minutes);
"""

# Additive column migrations for tables that predate a session.
# (table, column, column DDL) — applied only when the column is
# missing, so existing worlds open unchanged and gain the new
# structures. CREATE TABLE IF NOT EXISTS cannot do this alone.
MIGRATIONS = (
    ("economy_ledger", "transfer_key", "TEXT"),
    ("economy_ledger", "event_ref", "TEXT"),
    ("businesses", "category", "TEXT"),
    ("businesses", "status", "TEXT NOT NULL DEFAULT 'active'"),
    ("world_state", "economy_setup", "INTEGER NOT NULL DEFAULT 0"),
    ("world_state", "government_setup", "INTEGER NOT NULL DEFAULT 0"),
    ("world_state", "humandev_setup", "INTEGER NOT NULL DEFAULT 0"),
    ("vacancies", "employer_account_id", "TEXT"),
    ("vacancies", "employer_institution_id", "TEXT"),
    ("examination_results", "jitter", "REAL NOT NULL DEFAULT 0"),
    ("world_state", "transport_setup", "INTEGER NOT NULL DEFAULT 0"),
    ("road_segments", "closed", "INTEGER NOT NULL DEFAULT 0"),
    ("world_state", "environment_setup", "INTEGER NOT NULL DEFAULT 0"),
    ("world_state", "agents_setup", "INTEGER NOT NULL DEFAULT 0"),
    ("character_goals", "priority", "INTEGER NOT NULL DEFAULT 50"),
    ("character_goals", "progress", "REAL NOT NULL DEFAULT 0"),
    ("character_goals", "feasibility", "TEXT NOT NULL DEFAULT '{}'"),
    ("character_goals", "deadline_game_minutes", "INTEGER"),
    ("character_goals", "dependencies", "TEXT NOT NULL DEFAULT '[]'"),
    ("character_goals", "completion_rule", "TEXT NOT NULL DEFAULT ''"),
)

SYSTEM_ACCOUNTS = ("SYS-CITY", "SYS-EMPLOYERS", "SYS-MARKET", "SYS-BANK")


class Store:
    """One SQLite database = one simulated world. The file IS the save:
    closing and reopening it is save/restore (GDD-01 §9 local store)."""

    def __init__(self, path):
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self._migrate()
        self.conn.commit()
        self._counters = {}

    def _migrate(self):
        """Additive column migrations (see MIGRATIONS): existing
        worlds gain new columns in place; nothing is rewritten."""
        for table, column, ddl in MIGRATIONS:
            cols = [r["name"] for r in self.conn.execute(
                f"PRAGMA table_info({table})").fetchall()]
            if column not in cols:
                self.conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
        self.conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_ledger_transfer_key"
            " ON economy_ledger(transfer_key)")
        # The ledger is append-only (the Session 04 traceability
        # order: history is never rewritten). Enforced in the
        # database itself, not by convention.
        self.conn.execute(
            "CREATE TRIGGER IF NOT EXISTS trg_ledger_no_update"
            " BEFORE UPDATE ON economy_ledger BEGIN"
            " SELECT RAISE(ABORT, 'economy_ledger is append-only');"
            " END")
        self.conn.execute(
            "CREATE TRIGGER IF NOT EXISTS trg_ledger_no_delete"
            " BEFORE DELETE ON economy_ledger BEGIN"
            " SELECT RAISE(ABORT, 'economy_ledger is append-only');"
            " END")
        # Session 05: cast ballots are immutable for the same
        # reason — an election record that can be edited is not an
        # audit trail.
        self.conn.execute(
            "CREATE TRIGGER IF NOT EXISTS trg_ballots_no_update"
            " BEFORE UPDATE ON ballots BEGIN"
            " SELECT RAISE(ABORT, 'ballots are immutable');"
            " END")
        self.conn.execute(
            "CREATE TRIGGER IF NOT EXISTS trg_ballots_no_delete"
            " BEFORE DELETE ON ballots BEGIN"
            " SELECT RAISE(ABORT, 'ballots are immutable');"
            " END")

    def close(self):
        self.conn.commit()
        self.conn.close()

    # -- ids ---------------------------------------------------------------
    def next_id(self, prefix, table, column):
        """Next sequential id for (prefix, table). The counter is
        seeded from the MAXIMUM existing numeric suffix for the
        prefix in that table — never from COUNT(*): literal-id
        rows (system accounts) and rows written by earlier
        processes must not shift the sequence, or a resumed run
        would mint different ids than an uninterrupted one (the
        Session 01 restart-equivalence guarantee). Keyed by
        (prefix, table) because two tables may share a prefix
        (price_history / parcel_history both use PH)."""
        key = (prefix, table)
        if key not in self._counters:
            rows = self.conn.execute(
                f"SELECT {column} AS v FROM {table} WHERE"
                f" {column} LIKE ?", (prefix + "%",)).fetchall()
            best = 0
            for r in rows:
                suffix = r["v"][len(prefix):]
                if suffix.isdigit():
                    best = max(best, int(suffix))
            self._counters[key] = best
        self._counters[key] += 1
        return f"{prefix}{self._counters[key]:06d}"

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
        # System accounts exist in every world, including worlds
        # created before an account was added (Session 04: SYS-BANK).
        for sid in SYSTEM_ACCOUNTS:
            if self.row("SELECT 1 FROM characters WHERE character_id"
                        " = ?", (sid,)) is None:
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
                 related_business_id=None, transfer_key=None,
                 event_ref=None, from_business_id=None,
                 to_business_id=None):
        """Append-only ledger row + balance caches, one transaction.

        The owner's Session 04 traceability order: every unit of
        money carries its source, its destination, a reason code
        and — where the caller supplies them — an idempotency key
        (transfer_key: replaying the same key returns the original
        ledger row and moves nothing twice) and the simulation
        event that caused it (event_ref: a decision id, a month
        settlement tag, a project/business/month key).

        Endpoints are characters (from_id/to_id) or businesses
        (from_business_id/to_business_id); a transfer may mix them
        (an owner capitalising their business, a business paying a
        person). System accounts may go negative (they are the
        money source/sink); regular characters and businesses may
        not spend below zero — the caller checks, this method
        enforces it for non-system senders."""
        amount = int(amount)
        if amount <= 0:
            return None
        if transfer_key is not None:
            existing = self.row(
                "SELECT ledger_id FROM economy_ledger"
                " WHERE transfer_key = ?", (transfer_key,))
            if existing is not None:
                return existing["ledger_id"]
        if from_id is not None and from_id not in SYSTEM_ACCOUNTS:
            bal = self.balance(from_id)
            if bal < amount:
                raise ValueError(
                    f"insufficient funds: {from_id} has {bal}, needs {amount}")
        if from_business_id is not None:
            bal = self.business_balance(from_business_id)
            if bal < amount:
                raise ValueError(
                    f"insufficient funds: business {from_business_id}"
                    f" has {bal}, needs {amount}")
        cur = self.conn.execute(
            "INSERT INTO economy_ledger (from_character_id, to_character_id,"
            " from_business_id, to_business_id,"
            " amount, reason_code, related_property_id, related_business_id,"
            " note, game_minutes, transfer_key, event_ref)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (from_id, to_id, from_business_id, to_business_id,
             amount, reason, related_property_id,
             related_business_id, note, game_minutes, transfer_key,
             event_ref))
        lid = cur.lastrowid
        if from_id is not None:
            self.conn.execute(
                "UPDATE characters SET balance_cached = balance_cached - ?"
                " WHERE character_id = ?", (amount, from_id))
        if to_id is not None:
            self.conn.execute(
                "UPDATE characters SET balance_cached = balance_cached + ?"
                " WHERE character_id = ?", (amount, to_id))
        if from_business_id is not None:
            self.conn.execute(
                "UPDATE businesses SET balance_cached = balance_cached"
                " - ? WHERE business_id = ?", (amount, from_business_id))
        if to_business_id is not None:
            self.conn.execute(
                "UPDATE businesses SET balance_cached = balance_cached"
                " + ? WHERE business_id = ?", (amount, to_business_id))
        return lid

    def business_balance(self, business_id):
        r = self.row("SELECT balance_cached FROM businesses"
                     " WHERE business_id = ?", (business_id,))
        return r["balance_cached"] if r else 0

    def balance(self, character_id):
        r = self.row("SELECT balance_cached FROM characters"
                     " WHERE character_id = ?", (character_id,))
        return r["balance_cached"] if r else 0

    def ledger_sum_check(self):
        """Reconciliation: every character's cache must equal its ledger
        sum (seed balances are ledger rows too, so this must hold
        exactly), and — Session 04 — every business's cache must
        equal its business-column ledger sum. Returns a list of
        mismatches — empty means the ledger and the caches agree
        (GDD-01 §8's reconciliation job)."""
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
        for b in self.rows("SELECT business_id, balance_cached"
                           " FROM businesses"):
            bid = b["business_id"]
            inn = self.row(
                "SELECT COALESCE(SUM(amount),0) AS s FROM economy_ledger"
                " WHERE to_business_id = ?", (bid,))["s"]
            out = self.row(
                "SELECT COALESCE(SUM(amount),0) AS s FROM economy_ledger"
                " WHERE from_business_id = ?", (bid,))["s"]
            if inn - out != b["balance_cached"]:
                mismatches.append((bid, b["balance_cached"], inn - out))
        return mismatches
