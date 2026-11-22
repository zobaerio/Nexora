# NEXORA — History Archival & Aggregation Design

**Unit:** AQ (Queue 8) · **Status:** DESIGN ONLY — nothing in this document is built.
No code, no migration, no data movement ships with it. **No data is deleted or
moved anywhere by this document.**
**Date:** 2026-11-22 · **Programme state:** Sessions 01–10 complete and merged
(21 PRs, 438 tests); there is no Session 11. All UE work remains uncompiled
scaffolding; nothing here claims any production or UE-runtime behaviour.

## Sources (all read, all figures grounded)

- `docs/SESSION-10-REPORT.md` §5 (149-table census of the 365-day endurance
  world: 242 genesis residents, 616,050 rows), §6 (DB 2.17 MB after genesis →
  **213.6 MB at day 365**), §10 ("History growth ≈ **0.58 MB/day at 242
  residents** is the known pressure; the spec's distributed/region-aggregated
  scale architecture is future work, not built").
- `docs/FINAL-ARCHITECTURE.md`, Honest boundary 2 ("Scale is measured, not
  promised… history growth (~0.58 MB/day at 242 residents) is the known
  pressure" the region-aggregation architecture "would address") and boundary 3
  (the PostgreSQL server design in `data/schema.sql` remains a Phase 9
  *design*, unbuilt).
- `data/schema.sql` (PostgreSQL Phase 9 design draft v1.0 — only ~20 tables;
  the live history tables are **not** in this file) and
  `tools/sim/persistence.py` (`SCHEMA`, 149 tables — the operative schema the
  sim actually writes).
- `tools/sim/worlds.py:88` `world_digest()` — the content digest. **Correction
  to the usual shorthand:** the digest is defined in `worlds.py`, not in
  `persistence.py`, and it covers exactly three inputs (see §4.1). Nothing in
  this design redefines it.

## The problem, stated with the measured numbers

At 242 residents the endurance world grows ≈ 0.58 MB/day, i.e. ≈ **212 MB per
sim-year**, and 616,050 rows in 365 days. Three tables dominate:

| Table | Rows at day 365 | Share of all rows |
|---|---:|---:|
| `trips` | 348,789 | 56.6% |
| `instantiated_schedules` | 92,821 | 15.1% |
| `road_loads` | 58,096 | 9.4% |

Together the top three are **81.1% of all rows**. The ledger — the table that
must never shrink — is 34,323 rows (5.6%). Archival therefore targets
high-volume *derived history*, never state, never money, never audit evidence.
This design is the first concrete step toward the spec's region-aggregated
scale architecture (FINAL-ARCHITECTURE boundary 2); the distributed /
partitioned part of that architecture is still future work and is not
designed here.

---

## 1. Retention window + rollup cadence

### Decision

- **Retention window: 12 sim-months (365 sim-days) of raw history.** Raw rows
  younger than 12 sim-months are never touched. A month's raw rows become
  eligible for archival only once the world clock has passed that month by
  12 full sim-months.
- **Rollup cadence: monthly, on month-end.** At each month-end settlement, the
  archival pass rolls up exactly one month — the month that has just aged out
  of the window (month `M` is rolled up when the clock passes month `M + 12`).
  One month per pass, never a catch-up sweep of many months in one pass, so a
  failure is bounded to one month and the pass stays small.
- **The window is measured in sim-months (`month_index` / `day_index`), never
  in wall-clock time.** The sim has no wall-clock retention semantics; a world
  run in bursts over real weeks still ages by its own clock.
- **The window is a floor, not a target.** An operator may retain raw history
  longer (e.g. keep 24 months on a world under active investigation). The
  window may never be shortened below 12 months without an explicit owner
  decision, because the reasoning below depends on it.

### Reasoning

1. **The sim's own cadence is monthly.** Settlement, economic indicators,
   audits, budgets, municipal finance, HDI, technology levels and transport
   statistics are all monthly artefacts. A 12-month window keeps raw rows for
   exactly the period over which every monthly consumer still reads them, and
   hands over to rollups at the same grain the rest of the system already
   uses.
2. **A full seasonal cycle is preserved in raw form.** The sim runs a
   six-season calendar with a monsoon cycle (Session 08). Any window shorter
   than a year destroys the ability to compare a raw month against the same
   season a year earlier while the comparison is still live work. Twelve
   months keeps one complete seasonal cycle raw at all times.
3. **A full annual government cycle is preserved in raw form.** Budgets open
   at month 12 and elections run on annual cycles (Session 05); a 12-month
   window keeps the raw evidence for the fiscal year currently being audited.
4. **The growth math supports 12, not 6 or 24.** At 0.58 MB/day, 12 months of
   raw history costs ≈ 212 MB per world file at 242 residents — the size the
   endurance run already proved operable (213.6 MB, checkpoint save 2.90 s,
   restore 0.79 s). Six months would halve that cost but break reasons 2 and
   3. Twenty-four months would double it (≈ 424 MB) for a second seasonal
   cycle that the monthly rollups already preserve in aggregate. Twelve is
   the point where the cost is already-proven-operable and the analytical
   loss is zero for every live consumer.

### Alternatives considered and rejected

- **6-month window:** cheaper (≈ 106 MB), but loses raw seasonal comparison
  and raw evidence for the fiscal year under audit. Rejected.
- **24-month window:** keeps two seasonal cycles raw, but doubles the file
  for no live consumer — every monthly consumer works at monthly grain and
  reads rollups identically. Rejected.
- **Roll up continuously (daily/weekly):** the sim's consumers are monthly;
  finer rollups would multiply rollup rows without a reader. Rejected.
- **Archive on wall-clock age:** meaningless for a batch sim whose clock is
  `world_state.day_index`. Rejected.

---

## 2. Which tables roll up and which never do

### 2.1 The rule

A table rolls up only if **all three** hold: (a) its rows are history, not
current state; (b) no live pass reads individual rows older than the window
(every consumer of older data works at monthly-or-coarser grain); (c) its
rollup preserves every number a monthly consumer actually uses. A table that
fails any one of these is kept. Two tables are excluded by law, not by the
rule: the ledger and the ballots (§2.2).

### 2.2 NEVER — the ledger and the ballots

| Table | Rows at day 365 | Why never |
|---|---|---|
| `economy_ledger` | 34,323 | **The money traceability spine (Session 04).** It is the *only* truth for money: balances are caches reconciled against it (`Store.ledger_sum_check`, `finance.verify_conservation`), every transfer carries a `reason_code`, an `event_ref` and an idempotency `transfer_key` (unique index), and it is append-only at the DB level (`trg_ledger_no_update`, `trg_ledger_no_delete` in `persistence.py:_migrate`). Rolling it up would destroy per-transfer traceability — who paid whom, for what reason, under which event — and would make conservation verification (`ledger_sum_check`) unverifiable for archived months, since the check sums the ledger itself. Money stays fully traceable forever: every NCr that ever moved remains individually auditable. Its 5.6% share of rows is the price of that guarantee, and it is small. |
| `ballots` | 156 | **A cast ballot is a democratic record, not a statistic.** Ballots are append-only by the same mechanism as the ledger (`trg_ballots_no_update`, `trg_ballots_no_delete`), one row per voter per election enforced by `UNIQUE (election_id, character_id)`. Rolling them up would destroy the one-ballot-per-voter proof and the ability to recount. Volume is trivial (156 rows/year). |

Also never touched, by construction rather than by verdict: `world_state`
(the clock — archival never writes the clock), `event_sync_state` (registry
sync watermarks — archival must never reset them; deleting rows does not
invalidate a rowid watermark, since new rows always take higher rowids, but
the archival pass must not write this table at all), and the archival
manifest itself (§4.3 — the manifest is append-only and is never archived).

### 2.3 ROLL UP FIRST — priority order

Order is by measured 365-day volume at 242 residents, because volume is the
pressure. The three tables named in the brief are the first three *event
logs*; `instantiated_schedules` sits second by volume but is a schedule-block
table, not an event log, so it is listed honestly in its volume position
rather than hidden.

| Priority | Table | Rows at day 365 | Reasoning |
|---|---|---|---|
| 1 | `trips` | 348,789 | 56.6% of all rows; ~957 trips/day. No pass reads an individual old trip: congestion is computed from the day's own trips, transport statistics are monthly, and freight traceability lives in `freight_shipments`, not in trips. The per-trip route (`segment_ids`) is the single largest JSON payload in the database. |
| 2 | `instantiated_schedules` | 92,821 | 15.1% of rows; one row per character per day, holding a full day's schedule blocks as JSON. Past schedules are never re-read — the agent layer generates each day's schedule fresh. Only the fact *that* a character was scheduled, and with which template, has any later value. |
| 3 | `road_loads` | 58,096 | 9.4% of rows; one row per segment per day per hour. Congestion is a same-day computation; the monthly consumer (`transport_statistics`) needs only per-segment monthly load, peak congestion and totals. Hourly detail older than a year has no reader. |
| 4 | `decision_log` | 11,985 | Every daily decision with its reasons (`factors`/`outcome` JSON). Decisions are consumed the day they are made (Session 01 engine) and summarised in the observatory by type counts; no pass replays an old decision's factors. |
| 5 | `life_events` | 5,111 | Birth/marriage/death/graduation history. The *facts* survive archival elsewhere: birth and death dates live on `characters` (`born_at_game_minutes`, `died_at_game_minutes`), current relationships live on `relationships`, and the registry indexes the events. Only the per-event detail payload is lost. |
| 6 | `transit_runs` | 4,845 | One row per route per day per hour. The monthly consumer needs per-route monthly boardings and capacity only. |
| 7 | `inventory_movements` | 4,285 | Every stock movement with cause and counterparty. Monthly business accounting (`business_monthly`) and market pricing read monthly aggregates; individual movements older than a year are never replayed. |
| 8 | `goal_progress_log` | 3,680 | Per-goal step log (Session 09). Goals themselves live on `character_goals` with `progress`; the log's per-step measurements are audit detail, not state. |

### 2.4 ROLL UP — the remaining history tables

All remaining history/event tables, in measured-volume order. Each rollup
shape is specified exactly in §3.

| Table | Rows at day 365 | Reasoning |
|---|---|---|
| `agent_learning` | 1,840 | Bounded parameter-adaptation records. The *current* parameter values live on `agent_params`; the history of how they moved is audit detail. |
| `agent_actions` | 1,184 | Executed/failed action records. Coordination reads current task state, not old actions. |
| `agent_decisions` | 1,369 | Agent decision explanations. Same reasoning as `decision_log`, at the coordination layer. |
| `examination_results` | 1,610 | Per-student per-subject results. Recomputable in principle from `learning_records` + `examinations`; the monthly consumer (institution performance, certifications) needs per-exam aggregates only. |
| `assignments` | 4,835 | Per-student per-subject per-month assignment counts. Already at monthly grain per student; rolls up to per-institution aggregates. |
| `treatment_records` | 1,185 | Treatments delivered. Clinic operations read current conditions and visits; monthly facility reporting needs per-facility per-action totals. |
| `supply_orders` | 1,368 | Business supply orders (the measured basis for supplier selection). Selection reads recent months; older orders are needed only as per-seller/per-good monthly totals. |
| `business_events` | 955 | Business lifecycle log. Current status lives on `businesses`; monthly reporting needs per-business per-type counts. |
| `relationship_history` | 2,347 | Formation/status history. Current state lives on `relationships`; the history is audit detail. |
| `character_memories` | 1,307 | Episodic memory rows. Living characters' *current* memory profile is what the decision layer reads; archived months keep per-character per-type counts and mean emotional weight. |
| `disaster_impacts` | 630 | Per-disaster impacts. The disaster episode itself (`disaster_events`) is kept; per-impact damage/repair detail aggregates per disaster per kind. |
| `disaster_responses` | 246 | Response actions (relief/medical/repair). The episode is kept; per-action amounts aggregate per disaster per action. |
| `pharmacy_records` | 611 | Medication stock movements. Clinic inventory state lives on `medical_inventory`; movements aggregate per facility per month. |
| `patient_visits` | 802 | Clinic visits. Current condition state lives on `health_conditions`; visits aggregate per facility per type per month. |
| `price_history` | 130 | Price change history with signals. Current prices live on `market_prices`; changes aggregate per city per good per month. |
| `freight_shipments` | 1,112 | Traceable shipments. Delivery state is terminal (`status`); older shipments aggregate per month per route per good. Note: this is the one rollup that loses *individual shipment traceability* — see §5. |
| `env_weather` | 730 | Daily weather per region (2 regions × 365 days). Monthly climate reporting needs per-region monthly means/totals; the daily preset record is also kept in miniature by `daily_weather` (kept, §2.5). |
| `world_events` | 5,475 | The unified event registry (Session 10) — **an index, rolled up only in lockstep with its sources**. When a source month is archived, that month's registry rows roll up to per-source per-type per-city monthly counts. Archival must never delete a registry row whose source row still exists, and must never leave a registry row pointing at a deleted source row. After archival, `source_id` lookup for that month fails by design — the registry's per-event detail for the month is gone, and its counts live in the rollup. |
| `agent_perf` | 0 | Per-pass performance records. Empty in the endurance world; the shape is defined now so the first non-empty months roll up per class per pass per month. |
| `disease_records` | 187 | Disease cases. Current/chronic state lives on `health_profiles` and `health_conditions`; cases aggregate per disease per city per month. |
| `vaccination_records` | 84 | Vaccinations delivered. Counts aggregate per disease per facility per month. |
| `status_history` | 809 | Social status / mobility history. Current status is derivable from live tables; transitions aggregate per dimension per month. |
| `research_records` | 0 | Research publications. Empty in the unseeded endurance world, but the shape is defined: counts per field per month. The technology derivation's basis is *already* persisted per month on `technology_levels` (`basis` JSON), so no technology number depends on these rows surviving. |

### 2.5 KEEP FOREVER — already monthly, lifecycle, or tiny-and-significant

These tables are history-shaped but are **not** rolled up, each for a stated
reason. "Keep" means raw rows are retained indefinitely; it is not a
deferral — the verdict is final for this design.

**Already at monthly grain (rolling them up would only destroy resolution):**
`household_finances` (1,079; per household per month), `business_monthly`
(835; per business per month), `economic_indicators` (36; monthly snapshots),
`city_statistics` (24), `municipal_budgets` (24), `government_finance` (24),
`healthcare_budgets` (24), `opinion_snapshots` (12), `env_pollution` (24),
`env_snapshots` (24), `transport_statistics` (36), `technology_levels` (72;
monthly derived indices *with their basis stored*), `human_development_indicators`
(12), `household_consumption` (3,237; per household per good per month —
3,237 rows/year is the price of per-household resolution; rolling it up to
per-city would destroy the household-level consumption record the economy
layer settles from), `wellbeing_records` (3,060; per character per month),
`teacher_assignments` (84; per character per month), `examinations` (4; per
institution per month), `trade_flows` (23; already monthly grain).

**Lifecycle / legal / audit records (small, significant, individually
meaningful — aggregation would destroy the record's purpose):**
`crisis_records` (3), `disaster_events` (10), `research_projects` (0),
`education_records` (85), `certifications` (0 — credentials are permanent
facts and feed the technology derivation), `health_conditions` (390 —
per-character medical history, referenced by later care decisions; 390/year
is affordable), `hospital_admissions` (19), `forecasts` (72 — scored
forecasts are assessment evidence), `assessments` (1), `coordination_tasks`
(44), `negotiations` (0), `negotiation_offers` (0), `character_goals` (864),
`job_applications` (0), `court_cases` (0), `incidents` (0), `coi_records`
(5), `integrity_reports` (0), `laws` (0), `policies` (0), `budgets` (1),
`agreements` (0), `development_plans` (1), `civil_service` (0), `elections`
(1), `citizen_feedback` (5), `conflict_records` (0), `migration_records`
(4), `learning_records` (425 — current proficiency state, not history),
`agent_memories` (1,417 — multi-level memories with `importance` /
`access_count`; Session 09 proved retrieval changes decisions, so living
agents' memories are behaviourally live state, not dead history),
`agent_messages` (11), `daily_weather` (365 — one row per day, the engine's
own deterministic weather record; trivial volume).

**Tiny event logs (under ~150 rows/year; rolling them up saves nothing and
loses the only narrative record):** `social_events` (124 — festivals are the
culture record), `government_events` (30), `city_events` (13), `env_events`
(18), `vehicle_events` (8), `parcel_history` (64 — land ownership audit),
`generational_history` (116 — already a per-generation *summary*; it is a
rollup by design, and rolling it up again would destroy family lineage).

**State tables (not history; out of scope — archival never touches them):**
`characters`, `households`, `household_members`, `properties`, `tenancies`,
`relationships`, `social_profiles`, `household_state`, `household_culture`,
`communities`, `community_members`, `businesses`, `employments`,
`bank_accounts`, `loans`, `investments`, `business_inventory`,
`market_prices`, `vacancies`, `cities`, `city_zones`, `terrain_regions`,
`land_parcels`, `building_state`, `road_segments`, `infrastructure_state`,
`municipal_services`, `regional_connections`, `construction_projects`,
`countries`, `treasuries`, `institutions`, `offices`, `parties`,
`party_memberships`, `citizen_opinion`, `educational_institutions`,
`institution_departments`, `healthcare_facilities`, `health_profiles`,
`medical_inventory`, `vehicles`, `transit_routes`, `env_water_state`,
`env_soil`, `env_crops`, `env_vegetation`, `env_wildlife`,
`personality_profiles`, `needs_state`, `emotional_state`, `character_skills`,
`agent_registry`, `agent_params`, `agent_state`, `world_state`,
`event_sync_state`.

### 2.6 `data/schema.sql` — the Phase 9 design tables

`data/schema.sql` is a PostgreSQL *design draft*, not the live schema; most
of its tables have no sim rows at all. Verdicts for its tables, for the day
Phase 9 lands:

| `schema.sql` table | Verdict |
|---|---|
| `economy_ledger` | NEVER (same as §2.2). |
| `character_memories` | ROLL UP (same shape as §3, `character_memories_monthly`). |
| `accounts`, `account_friendships`, `save_slots` | KEEP — platform/account state, not sim history. |
| `characters`, `households`, `household_members`, `properties`, `tenancies`, `relationships`, `character_skills`, `character_goals`, `businesses`, `employments`, `inventory_items`, `mission_progress`, `achievements` | KEEP — state / lifecycle records, not history. |
| `world_state` | NEVER touched. |

No other history table exists in `data/schema.sql`; every history/event table
the sim actually writes lives in `tools/sim/persistence.py` and is covered
in §2.3–§2.5 above.

---

## 3. What each rollup row keeps

**Conventions for every rollup table below.** Table name: `<source>_monthly`.
Every rollup row carries: `month_index INTEGER NOT NULL` (the sim month being
rolled up), `archived_at_game_minutes INTEGER NOT NULL` (clock at archival),
`source_rows INTEGER NOT NULL` (how many raw rows this rollup row replaces),
and `rollup_version TEXT NOT NULL DEFAULT 'aq-1'` (the design version that
produced it, so a future design change is detectable). Grain columns are
part of the primary key. All money is integer NCr, as in the ledger. Sums are
exact integer sums where the source is integer; means are stored as REAL
alongside the count they were computed from, so a mean is never presented
without its denominator. `details`/free JSON payloads are **never** carried
into rollups — they are the part that is deliberately lost (§5).

### 3.1 `trips_monthly`

Grain: one row per (`month_index`, `origin_zone`, `destination_zone`, `mode`,
`purpose`).

| Field | Definition |
|---|---|
| `month_index` | Sim month of the trips |
| `origin_zone`, `destination_zone` | Zone ids, as stored on the trip |
| `mode` | Trip mode (`walk`, `motor`, `cycle`, `rickshaw`, `ferry`, `intercity_bus`, … — the source column's own values, not an invented vocabulary) |
| `purpose` | Trip purpose (`healthcare`, `emergency`, `migration`, … — source values) |
| `trip_count` | `COUNT(*)` |
| `distinct_travellers` | `COUNT(DISTINCT character_id)` (NULL `character_id` trips excluded from this count, counted separately in `anonymous_trip_count`) |
| `anonymous_trip_count` | `COUNT(*)` where `character_id IS NULL` |
| `total_distance_m` | `SUM(distance_m)` |
| `min_distance_m`, `max_distance_m` | `MIN`/`MAX(distance_m)` |
| `total_travel_min` | `SUM(travel_min)` |
| `mean_travel_min` | `AVG(travel_min)` + `trip_count` as denominator |
| `min_travel_min`, `max_travel_min` | `MIN`/`MAX(travel_min)` |
| `total_free_flow_min` | `SUM(free_flow_min)` |
| `total_delay_min` | `SUM(travel_min - free_flow_min)` |
| `total_fare_ncr` | `SUM(fare_ncr)` |
| `total_fuel_litres` | `SUM(fuel_litres)` |
| `completed_count`, `cancelled_count`, `other_status_count` | Counts by `status` (`completed` vs other values as recorded) |
| `distinct_vehicles` | `COUNT(DISTINCT vehicle_id)` |
| `distinct_routes` | `COUNT(DISTINCT route_id)` |
| `source_rows` | `COUNT(*)` (= `trip_count`; stored so the manifest can cross-check) |

*Why this grain:* origin × destination × mode × purpose is the grain every
transport consumer uses (congestion by segment is derived from `road_loads`,
not trips; monthly statistics need mode/purpose splits). The route itself
(`segment_ids` list) is dropped — see §5.

### 3.2 `instantiated_schedules_monthly`

Grain: one row per (`month_index`, `character_id`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `character_id` | Character |
| `days_scheduled` | `COUNT(*)` (one row per character per day in the source) |
| `distinct_templates` | `COUNT(DISTINCT schedule_template_id)` — template ids are read from the stored `blocks_json` at rollup time; if a block set carries no template id it counts under `untemplated_days` |
| `untemplated_days` | Days whose blocks carry no template id |
| `source_rows` | `COUNT(*)` |

### 3.3 `road_loads_monthly`

Grain: one row per (`month_index`, `segment_id`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `segment_id` | Road segment |
| `observations` | `COUNT(*)` (days × hours present) |
| `total_vehicle_count` | `SUM(vehicle_count)` |
| `mean_vehicle_count` | `AVG(vehicle_count)` |
| `max_vehicle_count` | `MAX(vehicle_count)` |
| `peak_congestion_factor` | `MAX(congestion_factor)` |
| `mean_congestion_factor` | `AVG(congestion_factor)` |
| `hours_over_capacity` | `COUNT(*)` where `congestion_factor > 1.0` |
| `peak_hour` | The `hour` value at which `max_vehicle_count` occurred (lowest such hour on ties; ties recorded in `peak_hour_ties`) |
| `peak_hour_ties` | Number of hours sharing the maximum vehicle count |
| `total_capacity_vph` | `SUM(capacity_vph)` (capacity is near-constant per segment; the sum is kept so the mean capacity is recoverable as `total_capacity_vph / observations`) |
| `source_rows` | `COUNT(*)` |

### 3.4 `decision_log_monthly`

Grain: one row per (`month_index`, `character_id`, `decision_type`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `character_id` | Deciding character |
| `decision_type` | Source `decision_type` value |
| `decision_count` | `COUNT(*)` |
| `distinct_outcomes` | `COUNT(DISTINCT outcome)` — outcome JSON compared as text; counts *distinct outcome payloads*, not outcome kinds |
| `source_rows` | `COUNT(*)` |

*Note:* `factors` and `outcome` JSON are dropped in full (§5). The count of
distinct outcome payloads is kept so a later reader can tell whether a
character's decisions in a month were uniform or varied, without seeing
what they were.

### 3.5 `life_events_monthly`

Grain: one row per (`month_index`, `city_id`, `event_type`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `city_id` | City of the event — resolved through the character's `residence_city` at rollup time; events whose character has no residence resolve to `city_id = 'unknown'` and are counted in `unknown_city_count` on that row |
| `event_type` | Source `event_type` (`birth`, `marriage`, `death`, `graduation`, … — source values) |
| `event_count` | `COUNT(*)` |
| `distinct_characters` | `COUNT(DISTINCT character_id)` |
| `unknown_city_count` | `COUNT(*)` where residence could not be resolved |
| `source_rows` | `COUNT(*)` |

### 3.6 `transit_runs_monthly`

Grain: one row per (`month_index`, `route_id`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `route_id` | Transit route |
| `run_count` | `COUNT(*)` |
| `total_boardings` | `SUM(boardings)` |
| `mean_boardings` | `AVG(boardings)` |
| `min_boardings`, `max_boardings` | `MIN`/`MAX(boardings)` |
| `total_capacity` | `SUM(capacity)` |
| `mean_load_factor` | `AVG(boardings * 1.0 / NULLIF(capacity, 0))` over runs with `capacity > 0`; `runs_with_capacity` records the denominator |
| `runs_with_capacity` | `COUNT(*)` where `capacity > 0` |
| `source_rows` | `COUNT(*)` |

### 3.7 `inventory_movements_monthly`

Grain: one row per (`month_index`, `business_id`, `good_id`, `kind`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `business_id`, `good_id`, `kind` | Source columns |
| `movement_count` | `COUNT(*)` |
| `total_delta` | `SUM(delta)` (net quantity change for that business/good/kind in the month) |
| `total_inflow` | `SUM(delta)` where `delta > 0` |
| `total_outflow` | `SUM(delta)` where `delta < 0` (stored negative, as in the source) |
| `min_delta`, `max_delta` | `MIN`/`MAX(delta)` |
| `total_amount_ncr` | `SUM(amount_ncr)` |
| `distinct_counterparties` | `COUNT(DISTINCT counterparty_business_id)` |
| `source_rows` | `COUNT(*)` |

*Note:* counterparty *identities* are lost; only the count of distinct
counterparties survives (§5).

### 3.8 `goal_progress_log_monthly`

Grain: one row per (`month_index`, `goal_id`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `goal_id` | Goal (joins to `character_goals`, which is kept) |
| `character_id` | Owner, denormalised from the source rows (all rows for a goal share one character) |
| `step_count` | `COUNT(*)` |
| `first_progress`, `last_progress` | `progress` of the earliest / latest row in the month (by `game_minutes`) |
| `min_progress`, `max_progress` | `MIN`/`MAX(progress)` |
| `progress_delta` | `last_progress - first_progress` |
| `source_rows` | `COUNT(*)` |

### 3.9 `agent_learning_monthly`

Grain: one row per (`month_index`, `owner_ref`, `param`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `owner_ref`, `param` | Source columns |
| `adaptation_count` | `COUNT(*)` |
| `first_old_value`, `last_new_value` | `old_value` of the earliest row / `new_value` of the latest row in the month |
| `min_new_value`, `max_new_value` | `MIN`/`MAX(new_value)` |
| `total_change` | `last_new_value - first_old_value` |
| `source_rows` | `COUNT(*)` |

### 3.10 `agent_actions_monthly`

Grain: one row per (`month_index`, `agent_ref`, `action_kind`, `status`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `agent_ref`, `action_kind`, `status` | Source columns |
| `action_count` | `COUNT(*)` |
| `source_rows` | `COUNT(*)` |

### 3.11 `agent_decisions_monthly`

Grain: one row per (`month_index`, `agent_ref`, `agent_class`, `decision_kind`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `agent_ref`, `agent_class`, `decision_kind` | Source columns |
| `decision_count` | `COUNT(*)` |
| `distinct_rules` | `COUNT(DISTINCT rule)` |
| `distinct_outcomes` | `COUNT(DISTINCT outcome)` (outcome JSON compared as text) |
| `source_rows` | `COUNT(*)` |

### 3.12 `examination_results_monthly`

Grain: one row per (`month_index`, `exam_id`, `subject_id`).

| Field | Definition |
|---|---|
| `month_index` | Sim month (month of the exam; `examinations` is kept, so `exam_id` stays joinable) |
| `exam_id`, `subject_id` | Source columns |
| `candidate_count` | `COUNT(*)` |
| `distinct_students` | `COUNT(DISTINCT character_id)` |
| `mean_score`, `min_score`, `max_score` | Over `score` |
| `mean_proficiency` | `AVG(proficiency)` |
| `mean_attendance_rate` | `AVG(attendance_rate)` |
| `mean_teacher_score`, `mean_institution_score` | `AVG(teacher_score)`, `AVG(institution_score)` |
| `grade_a_count`, `grade_b_count`, `grade_c_count`, `grade_d_count`, `grade_f_count`, `grade_other_count` | Counts by `grade` value; grades outside A/B/C/D/F fall in `grade_other_count` and are listed in `other_grades` |
| `other_grades` | Comma-separated distinct `grade` values counted in `grade_other_count` (empty string when none) |
| `source_rows` | `COUNT(*)` |

### 3.13 `assignments_monthly`

Grain: one row per (`month_index`, `institution_id`, `subject_id`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `institution_id`, `subject_id` | Source columns |
| `student_count` | `COUNT(DISTINCT character_id)` |
| `total_assigned` | `SUM(assigned_count)` |
| `total_completed` | `SUM(completed_count)` |
| `completion_rate` | `total_completed * 1.0 / NULLIF(total_assigned, 0)` (NULL when `total_assigned = 0`) |
| `source_rows` | `COUNT(*)` |

### 3.14 `treatment_records_monthly`

Grain: one row per (`month_index`, `facility_id`, `action`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `facility_id`, `action` | Source columns |
| `treatment_count` | `COUNT(*)` |
| `distinct_patients` | `COUNT(DISTINCT character_id)` |
| `distinct_doctors` | `COUNT(DISTINCT doctor_character_id)` |
| `distinct_conditions` | `COUNT(DISTINCT condition_id)` |
| `source_rows` | `COUNT(*)` |

### 3.15 `supply_orders_monthly`

Grain: one row per (`month_index`, `seller_business_id`, `good_id`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `seller_business_id`, `good_id` | Source columns |
| `order_count` | `COUNT(*)` |
| `distinct_buyers` | `COUNT(DISTINCT buyer_business_id)` |
| `total_units` | `SUM(units)` |
| `min_units`, `max_units` | `MIN`/`MAX(units)` |
| `total_amount_ncr` | `SUM(amount_ncr)` |
| `source_rows` | `COUNT(*)` |

### 3.16 `business_events_monthly`

Grain: one row per (`month_index`, `business_id`, `event_type`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `business_id`, `event_type` | Source columns |
| `event_count` | `COUNT(*)` |
| `source_rows` | `COUNT(*)` |

### 3.17 `relationship_history_monthly`

Grain: one row per (`month_index`, `event`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `event` | Source `event` value |
| `event_count` | `COUNT(*)` |
| `distinct_pairs` | `COUNT(DISTINCT from_character_id || '|' || to_character_id)` |
| `distinct_relation_types` | `COUNT(DISTINCT relation_type)` |
| `source_rows` | `COUNT(*)` |

### 3.18 `character_memories_monthly`

Grain: one row per (`month_index`, `character_id`, `event_type`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `character_id`, `event_type` | Source columns |
| `memory_count` | `COUNT(*)` |
| `mean_emotional_weight`, `min_emotional_weight`, `max_emotional_weight` | Over `emotional_weight` |
| `distinct_others` | `COUNT(DISTINCT other_character_id)` |
| `source_rows` | `COUNT(*)` |

### 3.19 `disaster_impacts_monthly`

Grain: one row per (`month_index`, `disaster_id`, `kind`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `disaster_id`, `kind` | Source columns (`disaster_events` is kept, so `disaster_id` stays joinable) |
| `impact_count` | `COUNT(*)` |
| `distinct_refs` | `COUNT(DISTINCT ref_id)` |
| `total_damage` | `SUM(damage)` |
| `total_repaired` | `SUM(repaired)` |
| `max_damage` | `MAX(damage)` |
| `source_rows` | `COUNT(*)` |

### 3.20 `disaster_responses_monthly`

Grain: one row per (`month_index`, `disaster_id`, `action`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `disaster_id`, `action` | Source columns |
| `response_count` | `COUNT(*)` |
| `total_amount_ncr` | `SUM(amount_ncr)` |
| `distinct_refs` | `COUNT(DISTINCT ref_id)` |
| `source_rows` | `COUNT(*)` |

### 3.21 `pharmacy_records_monthly`

Grain: one row per (`month_index`, `facility_id`, `item_id`, `reason`).
(Columns verified against `tools/sim/persistence.py:1343–1352`:
`record_id`, `facility_id`, `item_id`, `change`, `reason`, `visit_id`,
`month_index`, `game_minutes`.)

| Field | Definition |
|---|---|
| `month_index` | Sim month (source column; rows with `month_index IS NULL` aggregate under `month_index = -1` and are counted in `unmonth_indexed_count`) |
| `facility_id`, `item_id`, `reason` | Source columns |
| `movement_count` | `COUNT(*)` |
| `total_change` | `SUM(change)` (net medication units moved for that facility/item/reason in the month) |
| `total_inflow` | `SUM(change)` where `change > 0` |
| `total_outflow` | `SUM(change)` where `change < 0` (stored negative, as in the source) |
| `min_change`, `max_change` | `MIN`/`MAX(change)` |
| `distinct_visits` | `COUNT(DISTINCT visit_id)` |
| `unmonth_indexed_count` | `COUNT(*)` where `month_index IS NULL` |
| `source_rows` | `COUNT(*)` |

### 3.22 `patient_visits_monthly`

Grain: one row per (`month_index`, `facility_id`, `visit_type`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `facility_id`, `visit_type` | Source columns |
| `visit_count` | `COUNT(*)` |
| `distinct_patients` | `COUNT(DISTINCT character_id)` |
| `distinct_doctors` | `COUNT(DISTINCT doctor_character_id)` |
| `distinct_conditions` | `COUNT(DISTINCT condition_id)` |
| `closed_count` | `COUNT(*)` where `closed_day IS NOT NULL` |
| `source_rows` | `COUNT(*)` |

### 3.23 `price_history_monthly`

Grain: one row per (`month_index`, `city_id`, `good_id`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `city_id`, `good_id` | Source columns |
| `change_count` | `COUNT(*)` |
| `first_price_ncr`, `last_price_ncr` | `new_price_ncr` of the earliest / latest change in the month (by `game_minutes`) |
| `min_price_ncr`, `max_price_ncr` | `MIN`/`MAX(new_price_ncr)` |
| `net_change_ncr` | `last_price_ncr - first_price_ncr` |
| `source_rows` | `COUNT(*)` |

*Note:* the `signals` JSON that caused each change is dropped (§5).

### 3.24 `freight_shipments_monthly`

Grain: one row per (`month_index`, `from_city_id`, `to_city_id`, `good_id`, `kind`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `from_city_id`, `to_city_id`, `good_id`, `kind` | Source columns |
| `shipment_count` | `COUNT(*)` |
| `total_units` | `SUM(units)` |
| `total_freight_ncr` | `SUM(freight_ncr)` |
| `total_distance_km` | `SUM(distance_km)` |
| `mean_delay_min`, `max_delay_min` | Over `delay_min` |
| `delivered_count`, `in_transit_count`, `other_status_count` | Counts by `status` |
| `distinct_vehicles` | `COUNT(DISTINCT vehicle_id)` |
| `source_rows` | `COUNT(*)` |

### 3.25 `env_weather_monthly`

Grain: one row per (`month_index`, `region_id`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `region_id` | Source column |
| `day_count` | `COUNT(*)` |
| `mean_temp_day_c`, `min_temp_day_c`, `max_temp_day_c` | Over `temp_day_c` |
| `mean_temp_night_c`, `min_temp_night_c`, `max_temp_night_c` | Over `temp_night_c` |
| `total_precip_mm` | `SUM(precip_mm)` |
| `max_precip_mm` | `MAX(precip_mm)` |
| `mean_humidity_pct`, `mean_wind_kmh`, `mean_cloud_pct` | `AVG` of each |
| `mean_pressure_hpa` | `AVG(pressure_hpa)` |
| `dominant_preset` | The `preset_id` occurring most often in the month (ties: the earliest in alphabetical order; `dominant_preset_days` records its count) |
| `dominant_preset_days` | Days carrying `dominant_preset` |
| `distinct_presets` | `COUNT(DISTINCT preset_id)` |
| `distinct_seasons` | `COUNT(DISTINCT season_id)` |
| `source_rows` | `COUNT(*)` |

### 3.26 `world_events_monthly`

Grain: one row per (`month_index`, `source_table`, `event_type`, `city_id`).
Rolled up **only in lockstep** with the archival of the source month (§2.4):
a registry row is eligible exactly when its source row's month is being
archived, and the source month's archival is the trigger — the registry is
never archived on its own schedule.

| Field | Definition |
|---|---|
| `month_index` | Sim month (from the registry row's `day_index`) |
| `source_table` | Source table name |
| `event_type` | Registry `event_type` |
| `city_id` | Registry `city_id` (`NULL` city rows aggregate under `city_id = 'unknown'`) |
| `event_count` | `COUNT(*)` |
| `distinct_entities` | `COUNT(DISTINCT entity_refs)` (entity_refs JSON compared as text) |
| `source_rows` | `COUNT(*)` |

### 3.27 `agent_perf_monthly`

Grain: one row per (`month_index`, `agent_class`, `pass_kind`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `agent_class`, `pass_kind` | Source columns |
| `run_count` | `COUNT(*)` |
| `total_duration_ms` | `SUM(duration_ms)` |
| `mean_duration_ms`, `max_duration_ms` | Over `duration_ms` |
| `total_agents_updated` | `SUM(agents_updated)` |
| `source_rows` | `COUNT(*)` |

### 3.28 `disease_records_monthly`

Grain: one row per (`month_index`, `disease_id`, `city_id`).

| Field | Definition |
|---|---|
| `month_index` | Sim month of infection (`infected_day` → month) |
| `disease_id`, `city_id` | Source columns |
| `infection_count` | `COUNT(*)` |
| `distinct_patients` | `COUNT(DISTINCT character_id)` |
| `recovered_count` | `COUNT(*)` where `recovered_day IS NOT NULL` |
| `distinct_sources` | `COUNT(DISTINCT source)` |
| `source_rows` | `COUNT(*)` |

### 3.29 `vaccination_records_monthly`

Grain: one row per (`month_index`, `disease_id`, `facility_id`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `disease_id`, `facility_id` | Source columns |
| `vaccination_count` | `COUNT(*)` |
| `distinct_patients` | `COUNT(DISTINCT character_id)` |
| `source_rows` | `COUNT(*)` |

### 3.30 `status_history_monthly`

Grain: one row per (`month_index`, `dimension`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `dimension` | Source `dimension` value |
| `change_count` | `COUNT(*)` |
| `distinct_characters` | `COUNT(DISTINCT character_id)` |
| `distinct_from_values`, `distinct_to_values` | `COUNT(DISTINCT from_value)`, `COUNT(DISTINCT to_value)` |
| `source_rows` | `COUNT(*)` |

### 3.31 `research_records_monthly`

Grain: one row per (`month_index`, `field`).

| Field | Definition |
|---|---|
| `month_index` | Sim month |
| `field` | Research field |
| `publication_count` | `COUNT(*)` |
| `distinct_projects` | `COUNT(DISTINCT project_id)` |
| `distinct_institutions` | `COUNT(DISTINCT institution_id)` |
| `distinct_kinds` | `COUNT(DISTINCT kind)` |
| `source_rows` | `COUNT(*)` |

### Expected compression (estimates, not measurements)

From the 365-day census at 242 residents, one archived month replaces
roughly: ~29,000 `trips` rows with a few hundred `trips_monthly` rows
(origin × destination × mode × purpose is sparse — 16 zones, a handful of
modes and purposes); ~4,800 `road_loads` rows with 28 `road_loads_monthly`
rows (one per segment); ~7,700 `instantiated_schedules` rows with ~264
`instantiated_schedules_monthly` rows (one per character). Across all 31
rollup tables, a year's raw history of ≈ 500,000 rows becomes on the order
of 10,000–20,000 rollup rows. These are estimates from the census, labelled
as such — the first real archival run must measure the actual ratio and
record it in the manifest (§4.3) before the design's numbers are quoted as
fact.

---

## 4. How the content digest is re-baselined after archival

### 4.1 What the digest actually covers — the correction this design rests on

`world_digest()` (`tools/sim/worlds.py:88`) hashes exactly three inputs, in
this order:

1. **Every character's** `character_id`, `balance_cached`,
   `died_at_game_minutes` (ordered by `character_id`);
2. **The ledger's size and sum:** `COUNT(*)` and `SUM(amount)` over
   `economy_ledger`;
3. **The clock:** `day_index` and `game_minutes` from the `world_state` row.

It does **not** hash `trips`, `road_loads`, `decision_log`, or any other
history table. That matters: archival removes raw rows the digest was
**never** computed over. The premise that archival breaks the digest is
therefore false for this digest — and the design must say so plainly rather
than build a re-baselining ritual for a break that does not happen.

Why the digest is *invariant* under archival, by construction:

- **Characters are never deleted.** `data/schema.sql` (GDD-01 §3): "Characters
  are archived on death, never deleted: family trees, memories and
  inheritance reference them forever." Death is recorded as
  `died_at_game_minutes` on the same row, which the digest reads — so the
  digest's character input cannot change through archival.
- **The ledger is never rolled up** (§2.2), so its count and sum cannot
  change through archival.
- **The clock is never written by archival** (§2.2), so its input cannot
  change through archival.

Consequence: **a correct archival run leaves `world_digest()` byte-identical,
and digest equality is the proof that archival touched nothing it must not
have touched.** The "re-baseline" is therefore not a recomputation over
different data. It is a recorded verification event with four parts: prove
invariance, checksum what was removed, checksum what replaced it, and record
what can no longer be verified (§4.4).

### 4.2 The re-baseline procedure, step by step

Archival runs **offline**: no simulation process may hold the world file open
(the same precondition as checkpoint restore in `worlds.py`). All steps for
one month run inside **one SQLite transaction**; a failure at any step rolls
the whole month back, raw rows included.

1. **Preconditions (abort before touching anything if any fails).**
   - No sim process holds the world open.
   - `ledger_sum_check()` returns zero mismatches (the ledger reconciles).
   - `world_state` clock is at a month boundary (archival runs on month-end).
   - The month to archive, `M`, is at least 12 sim-months behind the clock.
   - The event registry sync has run for month `M` (no source row of `M`
     is unindexed — otherwise the lockstep rollup of `world_events` in §3.26
     would silently drop unindexed events).
2. **Record the pre-state.** Compute `D_pre = world_digest(world)` and the
   ledger's `COUNT(*)` / `SUM(amount)`. Record per-table raw row counts for
   month `M` for every table in §2.3–§2.4. This is the baseline the rest of
   the procedure is checked against.
3. **Checksum the raw rows being removed.** For each table and month `M`,
   compute a removal checksum from the raw rows *before* deletion: the row
   count, and a SHA-256 over the ordered concatenation of the rows' full
   content (the same `repr(tuple(row))` per-row hashing the digest itself
   uses, over `SELECT * … ORDER BY <primary key>`). Store the checksum, not
   the rows. This checksum is the only surviving fingerprint of the exact
   raw rows; it can prove later that a claimed copy of the raw rows is the
   set that was removed, but it cannot reconstruct them.
4. **Build the rollups.** Insert the `*_monthly` rows for month `M` exactly
   as specified in §3, inside the transaction.
5. **Verify the rollups against the raw rows — before any deletion.**
   Re-aggregate month `M` from the raw rows a second time, through an
   independent query path (different `GROUP BY` formulation, written
   separately from the rollup builder), and require every summed field,
   every count and every min/max to match the inserted rollup rows exactly.
   Any mismatch aborts the transaction. This is the step that makes
   deletion safe: the rollup is proven correct while the evidence is still
   present.
6. **Delete the raw rows for month `M`** from every table in §2.3–§2.4,
   inside the same transaction. No table outside those lists is deleted
   from; the ledger, ballots, audits, state tables and kept history are
   never in a `DELETE` statement.
7. **Re-baseline check (the digest step).** Compute
   `D_post = world_digest(world)` and the ledger's `COUNT(*)` /
   `SUM(amount)`. Require **all** of: `D_post == D_pre`; ledger count and
   sum unchanged; `world_state` `day_index`/`game_minutes` unchanged.
   If any fails, roll the transaction back — the archival run has touched
   digest inputs, which by §4.1 it must never do, and the failure is a bug
   in the archival code, not a property of the data.
8. **Compute the rollup digest.** SHA-256 over the ordered inserted
   `*_monthly` rows for month `M` (same per-row hashing as step 3). This is
   the fingerprint future verifications of month `M` will check *instead
   of* the raw rows.
9. **Write the manifest row** (§4.3) and commit. The manifest row is written
   inside the same transaction, so a manifest without its archival — or an
   archival without its manifest — cannot exist.
10. **Post-commit verification (outside the transaction, on the committed
    file).** Re-open the world read-only, recompute `world_digest()` and
    require it to equal `D_pre` again; run `ledger_sum_check()` and require
    zero mismatches; run the orphan scans from `tools/sim/dbinspect.py` and
    require zero new orphans. Record the outcome in the manifest row's
    `post_commit_verified` flag (a second, later write to the manifest row
    is permitted for this flag only — the manifest's archival facts are
    never edited).

### 4.3 The archival manifest — `archival_manifest` (new table, design only)

One row per archived (world, month). Append-only; never archived itself.

| Field | Definition |
|---|---|
| `world_id` | World identifier (file path + seed, as in the world registry) |
| `month_index` | The archived sim month |
| `archived_at_game_minutes` | Clock at archival |
| `code_version` | Sim code version at archival (e.g. `s10.1`) |
| `rollup_version` | Rollup design version (`aq-1`) |
| `digest_pre`, `digest_post` | `D_pre` and `D_post` from §4.2 (must be equal; stored both so the equality is auditable, not asserted) |
| `ledger_rows_pre`, `ledger_rows_post` | Ledger `COUNT(*)` before/after |
| `ledger_sum_pre`, `ledger_sum_post` | Ledger `SUM(amount)` before/after |
| `per_table` | JSON: for each table, `raw_rows_removed`, `rollup_rows_written`, `raw_checksum` (step 3), `rollup_digest` (step 8) |
| `verification` | JSON: independent re-aggregation result (step 5), post-commit checks (step 10) |
| `post_commit_verified` | Boolean, set after step 10 |
| `operator` | Who/what ran the archival (operator id or `cli` invocation record) |

### 4.4 What can no longer be verified after archival

Honest boundary — archival trades verifiability for size, and the trade must
be named:

- **Raw-row re-derivation is gone.** No rollup value for an archived month
  can ever be recomputed from source rows; the step-5 independent
  re-aggregation is the last time it is possible. A rollup error discovered
  later cannot be corrected from the world file — only detected (by
  inconsistency with the kept monthly tables, e.g. `transport_statistics`).
- **The removal checksum proves identity, not content.** Given a claimed
  copy of month `M`'s raw rows, the stored checksum can confirm it is the
  set that was removed. Without such a copy, the checksum reconstructs
  nothing.
- **Per-event registry lookup fails for archived months.** A `world_events`
  row's `source_id` no longer resolves once its source month is archived;
  only the monthly counts in `world_events_monthly` survive (§5).
- **A future digest that hashes history tables cannot cover archived
  months.** If a later digest version ever hashes `trips` or any other
  archived table, it must treat archived months as *rollup-digest inputs*
  (the step-8 digest) rather than raw-row inputs, and the digest's
  definition must record the month from which that substitution applies.
  Until such a version exists, this is a design constraint on it, not a
  change to the current digest.
- **Determinism replays over archived months cannot reproduce raw rows.**
  Forward simulation is unaffected — the engine advances from state tables,
  never by re-reading old history — but a hypothetical replay that
  regenerates history from scratch would produce raw rows whose checksums
  could no longer be compared against the archived months. (Checkpoint
  restore is the only path back to raw rows, and only if a checkpoint
  predating the archival exists; a restore must be recorded in the manifest
  as reopening the archived window, and the months must be re-archived
  under the same procedure if the world continues.)
- **What is *not* lost:** everything the digest covers (characters, ledger,
  clock) remains verifiable forever, exactly as before; every kept monthly
  table remains verifiable from its own rows; the manifest's digests remain
  verifiable from the rollup rows.

---

## 5. What can no longer be answered once raw rows are gone

An explicit loss inventory, per table. "Cannot be answered" means: not from
the world file, by any query. (A pre-archival checkpoint, if one exists,
still holds the raw rows — see §4.4.)

| Table | Lost questions (examples, not exhaustive) |
|---|---|
| `trips` | Which character took which route on which day; the exact `segment_ids` of any individual trip; a single trip's depart/arrive minutes, fare basis, or fuel use; per-trip delay on a named day; any origin–destination pair below the monthly aggregate (e.g. trips on one specific date). |
| `instantiated_schedules` | What any character's schedule blocks were on any specific day; which template a character used on a given date. |
| `road_loads` | Hourly load on any segment on any specific day; the exact hour of peak congestion on a given date (only the month's peak hour survives); whether a segment exceeded capacity on a named day. |
| `decision_log` | Why a specific character made a specific decision (`factors` JSON); what a decision's outcome payload was; any individual decision trace. Only per-character per-type monthly counts survive. |
| `life_events` | Which character married whom, and when exactly; the detail payload of any birth/death/graduation event; the exact day of any life event (only the month survives). Birth/death *dates* survive on `characters`; the event narrative does not. |
| `transit_runs` | Boardings on a specific run (route/day/hour); whether a named run was over capacity. |
| `inventory_movements` | Which counterparty a specific movement went to; the cause/detail of any individual movement; stock level on a specific day (only month-end net change per business/good/kind survives). |
| `goal_progress_log` | A goal's progress on a specific day; the `measured` payload of any step. |
| `agent_learning` | The `reason` JSON for any single parameter adaptation; the exact sequence of adaptations within a month (only first/last values survive). |
| `agent_actions` | The `details` of any single action; whether a named action succeeded on a given day. |
| `agent_decisions` | The `inputs` JSON behind any single agent decision; which rule fired for a specific decision (only distinct-rule *counts* survive). |
| `examination_results` | Any individual student's score, grade, attendance or proficiency on a named exam; per-student trajectories. |
| `assignments` | Any individual student's assigned/completed counts in a month. |
| `treatment_records` | Which patient received which treatment on which day; the `details` of any treatment. |
| `supply_orders` | The buyer of any individual order; any single order's units/amount. Only per-seller per-good monthly totals survive. |
| `business_events` | The `details` of any business event; the exact day of a founding/distress/closure event (only the month survives). |
| `relationship_history` | Which pair changed, and how, on any specific occasion; the `details` of any relationship event. |
| `character_memories` | The `details` of any individual memory; the exact day a memory formed; which memories a character holds (only per-type monthly counts and mean emotional weight survive). |
| `disaster_impacts` | Which building/property a specific impact hit and its damage/repair figures; per-impact detail. |
| `disaster_responses` | Which entity a specific relief/repair payment went to; the `details` of any response. (The money itself is still fully traceable — every relief/repair payment is a ledger row, and the ledger is never archived.) |
| `pharmacy_records` | Individual medication movements: the item, the quantity change and the reason for any single movement; which visit a movement belonged to. |
| `patient_visits` | Which patient visited which facility on which day; a visit's stage history and diagnosis outcome. |
| `price_history` | The `signals` JSON behind any price change; the exact day a price changed. |
| `freight_shipments` | **Individual shipment traceability is lost**: which vehicle carried which goods for which businesses on which days, a single shipment's delay, and its route (`segment_ids`). Only per-route per-good monthly totals survive. This is the sharpest single loss in the design, and it is accepted because `inventory_movements` (the goods audit trail) is rolled up at business/good grain and the ledger (the money trail) is never touched. |
| `env_weather` | Daily temperature/precipitation for a specific date; the preset on a named day (the daily preset *is* still in `daily_weather`, which is kept — only the full daily measurement row is lost). |
| `world_events` | Any individual event's entity refs, source id, or exact timestamp; the registry can no longer answer "show me event X". Only monthly counts per source/type/city survive. |
| `agent_perf` | Duration of any single pass; per-pass agent counts. |
| `disease_records` | Which character contracted which disease on which day; the source of any single infection; recovery dates. |
| `vaccination_records` | Which character was vaccinated against what, where, on which day. |
| `status_history` | The from/to values of any single status change; the exact day a character's status changed. |
| `research_records` | Individual publication records (`details` JSON); which project produced which publication on which day. The monthly *count* per field survives, and the technology basis is already stored on `technology_levels`. |

**What is never lost, by design:** any question answerable from state tables
(current relationships, holdings, employments, skills, health profiles);
any money question (the ledger is complete forever); any monthly question
the kept monthly tables already answer; any question about the current
month or the last 12 months (raw rows are intact inside the window).

---

## 6. Safety rules

These are rules, not guidance. An archival implementation that violates any
of them is incorrect, even if its rollups are right.

1. **Never delete without a verified rollup.** Raw rows for a month are
   deleted only after the step-5 independent re-aggregation has proven the
   rollup rows correct, in the same transaction. A rollup that has not been
   verified is not a rollup — it is a guess.
2. **Never delete without a digest re-baseline.** The §4.2 procedure runs
   in full for every month: `D_pre` and `D_post` are computed and must be
   equal; the manifest row is written in the same transaction. A month
   archived without a manifest row is an unverifiable month.
3. **The ledger is never in a `DELETE` statement.** Not for any month, not
   under any flag. The append-only triggers (`trg_ledger_no_update`,
   `trg_ledger_no_delete`) are the last line of defence, but the archival
   code must never attempt the operation in the first place. The same
   applies to `ballots` and `audits`.
4. **Archival is offline and transactional.** No sim process holds the world
   open; one month per transaction; any failure rolls the whole month back.
   Archival never runs inside a simulation pass and never interleaves with
   the registry sync — the sync runs first (§4.2 step 1).
5. **Retention of the ledger means money stays fully traceable forever.**
   Every NCr that ever moved remains individually auditable through
   `economy_ledger` (`transfer_key`, `event_ref`, `reason_code`), reconciled
   by `ledger_sum_check`. Archival must never be used as a reason to weaken
   that: if a future design ever proposes ledger aggregation, it requires
   an owner decision that explicitly revokes this rule.
6. **Rollups are never re-rolled or deleted.** `*_monthly` rows are
   write-once. A defective rollup is corrected by a superseding correction
   row (new `rollup_version`, referencing the manifest), never by editing or
   deleting the original — the same append-only discipline as the ledger.
7. **The manifest is append-only and never archived.** It is the audit trail
   of archival itself; archiving it would destroy the proof that archival
   happened correctly.
8. **Dry-run before first live run.** The first archival run on any world
   must run in dry-run mode (build rollups, verify them, delete nothing,
   write no manifest) and the operator must inspect the resulting sizes and
   counts before a live run is authorised.
9. **The window is a floor.** Raw history may be retained longer than 12
   months; it may never be retained for less without an explicit owner
   decision recorded in the manifest's `operator` field.
10. **Checkpoints before archival.** A checkpoint (per `worlds.py`,
    manifest with reconciled ledger) should be taken before the first
    archival run on a world, so raw rows remain recoverable through restore.
    This is a *should*, not a *must* — archival's own verification (step 5)
    is what makes deletion safe; the checkpoint is belt-and-braces.

---

## 7. What this design does not do

- **It is not built.** No `*_monthly` table exists, no archival code exists,
  no manifest exists. This document is the design only.
- **It does not implement the spec's distributed / region-aggregated scale
  architecture** (FINAL-ARCHITECTURE boundary 2). It addresses the same
  pressure (0.58 MB/day) inside the single-file SQLite sim. Region
  aggregation across worlds, DB partitioning and any PostgreSQL port remain
  future work.
- **It does not change the digest.** `world_digest()` keeps its current
  definition (characters + ledger + clock). If a future version hashes
  history tables, §4.4 constrains how it must treat archived months.
- **It does not touch the Godot testbed, the UE layer, or any live data.**
- **It does not set the owner decisions.** The 12-month window is a design
  decision with the reasoning in §1; the owner confirms or changes it at
  build time. Nothing here authorises a build.

## 8. Honest gaps

1. **Every §3 rollup shape was written against the actual `CREATE TABLE`
   definitions in `tools/sim/persistence.py`** (including `pharmacy_records`,
   verified at lines 1343–1352 after the first draft). No rollup shape in
   this document is based on a guessed column list. If a column list changes
   in a later session, the affected §3 section must be re-checked before
   any build.
2. **Compression ratios in §3 are estimates from the census**, not
   measurements. The first real archival run must measure them and record
   them in the manifest before they are quoted as fact.
3. **No archival code was run.** Every procedure in §4.2 is designed, not
   executed; the transaction boundaries, the independent re-aggregation
   path and the post-commit checks are specified so they can be tested, not
   claimed as tested.
4. **Vocabularies are not enumerated.** Where a rollup groups by a source
   column (`mode`, `purpose`, `event_type`, `grade`, …), the design names
   the column and gives examples seen in the code (`walk`, `motor`,
   `cycle`, `rickshaw`, `ferry`, `intercity_bus` for `trips.mode`); it does
   not claim an exhaustive vocabulary for any column. The rollup builder
   must group by the source's actual values.
