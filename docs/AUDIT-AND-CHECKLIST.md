# NEXORA — Complete Project Audit & Implementation Checklist

**Date:** 2026-11-21 · **Auditor:** Muse (audit coordinator, read-only inspection)
**Scope:** everything on GitHub `zobaerio/Nexora` main (`d11dd441`) + local `STATUS.md` / `WORK-QUEUE.md`.
Units A–AA are merged. Units AB (Education) and AC (Health) were **in flight** (finisher coordinator) at audit time and are classified as such.
**Method:** full file inventory; every JSON parsed; cross-reference spot-checks re-run from scratch; the two executable systems (Godot tests, economy simulator) **actually re-run in the VM during this audit**; UE sources inspected for scaffold labelling. Nothing in this document is taken on trust from `STATUS.md` alone — where a claim rests on a prior session's verification, it says so.

**Classification key (exactly one per item):**
- **REAL** — runs and was verified executing.
- **DESIGN** — a document or data model only; nothing executes it.
- **SCAFFOLD** — code written but never compiled or run.
- **ABSENT** — named in the vision / master prompt; nothing exists.

---

## 1. System-by-system classification (the master prompt's systems)

| # | System (prompt §) | Class | Evidence |
|---|---|---|---|
| 1 | Human agents & life cycle (§3) | **DESIGN** | `docs/GDD-01-LIFE-AND-DATA-MODEL.md` (§2 identity, §3 life stages birth→death, §4 needs/tick model, §6 relationships, §7 derived class), `docs/GDD-06-NPC-BEHAVIOUR.md` (state machines, memory hooks). No code anywhere executes an agent. The life cycle is prose + schema tables (`data/schema.sql`: characters, relationships, character_memories, character_goals). Child/elder stages are additionally gated by the known MetaHuman limitation (Phase 7). |
| 2 | Autonomous city (§4) | **DESIGN** | One district only: `docs/GDD-02-RUPSHA-CITY-DISTRICT1.md`, `data/buildings-district1.json` (42 properties), `data/district1-blockout.json` (21 road segments, 42 plots — verified 1:1 with buildings by id), `docs/GDD-08-CONSTRUCTION-SYSTEM.md`, `docs/GDD-10-HOUSING-AND-HOME-LIFE.md`. No city evolves: there is no code that changes any of this data. Infrastructure networks (water/electricity) appear as zone flavour, not systems. Districts 2+ / other cities (Phase 8): **ABSENT**. |
| 3 | Economy (§5) | **REAL (partial)** + DESIGN | `tools/economy_sim.py` genuinely runs (see §2). It is a *static monthly balance checker* per profession/tier over `data/prices.json` + `data/professions.json`: wages, rent, living costs, lifestyle uplift, business P&L, taxes, starting-balance bridge check. The wider economy — supply/demand pricing, unemployment dynamics, inflation, banking behaviour, trade — is **DESIGN** (`docs/GDD-03-ECONOMY-AND-PROFESSIONS.md`) or **ABSENT** (inflation: 1 passing mention in all docs; dynamic market pricing: none). No agent-to-agent transaction has ever been simulated. |
| 4 | Environment & weather (§6) | **DESIGN + SCAFFOLD** | `data/weather-presets.json` (9 presets with `gameplay_effects`) = DESIGN data. `ue-project/Source/Nexora/Systems/NexoraWeatherManager.*` + `NexoraGameClock.*` = SCAFFOLD (never compiled). `docs/TECH-CLOCK-WEATHER.md` = DESIGN. Seasons: 3 passing mentions, no model. Natural disasters, pollution, climate change, water resources, agriculture: **ABSENT** (0 mentions as systems). No weather runs anywhere today. |
| 5 | Social system (§7) | **DESIGN (partial)** | Relationships/kinship/memory are designed (`GDD-01` §5–6, `GDD-06` §6 conversation & memory hooks; schema tables relationships, character_memories, account_friendships). Social events, celebrations, cultural activities, community conflict, cooperation mechanics: **ABSENT** as designs. Nothing social has ever been simulated. |
| 6 | Government & politics (§8) | **ABSENT** | The audit's clearest zero. Grep across `docs/`, `data/`, `tools/`: "election" appears **once** (flavour in `GDD-06`), "government" as a system **zero** times. No institutions, parties, elections, courts, public opinion, policy, or public-finance design exists. The only government-adjacent artefacts are tax lines inside the economy data (`prices.json` `tax`, sim's 8% business tax) and police as a *profession* (GDD-06 sub-state), not a governance system. |
| 7 | Simulation engine (§9) | **ABSENT** (tick model = DESIGN) | No tick engine exists in any language. `GDD-01` §4 defines a needs/tick model on paper; `GDD-06` defines schedule state machines on paper. `tools/economy_sim.py` has **no agent class and no tick loop** (verified by source inspection) — it computes monthly arithmetic per profession row. There is no persistent world state, no event system, no save/restore of a running simulation anywhere. This is the central absence: the project's core claim — an autonomous, evolving civilization — currently has **zero executable code**. |
| 8 | Observation UI (§10) | **DESIGN** | `docs/GDD-05-UI-AND-PANELS.md` (HUD, profile screen, Environment Control Panel, 14-widget UMG contract). Zero UI code exists in any engine. No dashboard, population statistics view, or world-observation surface renders anything. |
| 9 | Persistence (§9/§11) | **DESIGN + SCAFFOLD** | `data/schema.sql`: 19 PostgreSQL tables (counted in this audit) — grammar-validated once with pglast in a prior session, **never applied to any database**; no database exists. `ue-project/Source/Nexora/Save/NexoraSaveGame.*` = SCAFFOLD: no save file has ever been written by anything. Two persistence models coexist on paper (relational schema for Phase 9 vs USaveGame-with-JSON-payloads for single player, `docs/TECH-SAVE-SYSTEM.md`) and have never been reconciled by execution. |
| 10 | Character & movement (Phases 2–3) | **REAL (Godot)** / **SCAFFOLD (UE)** | Godot testbed `rupsha-city/` genuinely implements and tests third-person walk/run/jump + spring-arm camera (see §2). UE equivalents (`NexoraCharacter.*`, `NexoraPlayerController.*`, values copied from the testbed) are SCAFFOLD. MetaHuman character creation is a build sheet (`docs/PHASE2-METAHUMAN-SHEET.md`) + creator design (`docs/GDD-09-CHARACTER-CREATOR.md`); no character has ever been built. |
| 11 | Vehicles & traffic (Phase 4) | **DESIGN + SCAFFOLD** | `docs/GDD-07-VEHICLES-AND-TRAFFIC.md`, `data/vehicles.json` (9 classes), `NexoraVehiclePawn.*` SCAFFOLD with the Chaos Vehicles binding deliberately left as one marked seam (pawn logs "will not move" until Phase 5 — honest, but means zero vehicle motion exists). No traffic simulation runs. |
| 12 | Missions & progression | **DESIGN** | `docs/GDD-04-MISSIONS-AND-PROGRESSION.md` + `data/missions.json` (verified: 32 missions, levels 1–8 all present, 13 achievements). Nothing executes a mission. Intermediate level names are still the coordinator's proposals — the owner has not confirmed them (open item since Unit G). |
| 13 | Multiplayer (Phase 9) | **DESIGN** | `docs/TECH-MULTIPLAYER.md` (dedicated-server decision, 8–16 player honest scale, authority mapped to schema). No networking code exists. |
| 14 | Planets & space (Phase 10) | **DESIGN (data only)** | `data/planets.json` — data cards incl. Nexora-7; gas giant honestly marked non-landable. Nothing else. |

### Counts

- **Files inventoried:** 21 docs (`docs/*.md`), 11 data files (10 JSON + `schema.sql`), 19 UE source files + `.uproject` + 3 Config INIs, 1 tool (`tools/economy_sim.py`), Godot testbed (2 scripts, 2 scenes, 1 test suite, 1 Windows exe).
- **Systems (14 above):** REAL **1 partial** (economy checker) + **1** (Godot movement testbed, a control testbed — not a civilization system) · DESIGN-only **7** · DESIGN+SCAFFOLD **4** · **ABSENT 2 outright** (government/politics; simulation engine) plus ABSENT sub-systems inside others (seasons/disasters/pollution, dynamic markets, social events, districts 2+, audio — no audio artefact of any kind exists).

---

## 2. What was re-verified by execution in this audit (2026-11-21)

| Check | Result |
|---|---|
| Godot headless tests (`rupsha-city/tests/player_test.tscn`) | **8/8 PASS** — walk 5.00 m, run 8.77 m, jump apex 1.59 m, spring-arm 4.5→3.04 m at wall. `PLAYER_TEST_PASS`. |
| `tools/economy_sim.py` | Exit 0; **two consecutive runs byte-identical** (deterministic); business P&L reconciles Δ 0; **BRIDGE FAIL rows: []** — all 12 entry rows end month 1 ≥ 0 with Queue 4 starting balances. |
| All 10 JSON data files | Parse clean. |
| `npc-schedules.json` ↔ `professions.json` | 11 schedule templates match the 11 profession ids **1:1**; 3 life-stage templates (child/student/elder) present. |
| `district1-blockout.json` ↔ `buildings-district1.json` | 42 plots match 42 properties **1:1 by id**. |
| Residential stock = 140 | **Confirmed, with a trap:** naive summation of `units` over apartment+house entries gives **144**. The data's own notes define the rule — 4 single-unit entries carry `part_of` and are counted inside their parents (144 − 4 = **140** ✓). The figure is correct, but only if every consumer honours the `part_of` rule; nothing in the repo enforces it (see §4.1). |
| `clothing.json` → `prices.json` | 31/31 `price_ref`s resolve into the `clothing` table added in Unit Y; uniforms mapped for 11/11 professions. Simulator output was byte-identical after the prices v1.2 change (prior session's check; prices version is now 1.2). |
| `vehicles.json` → `prices.json` | 6 buyable classes' `price_ref`s resolve. Bus, truck, CNG auto-rickshaw have `price_ref: null` — the documented non-buyable gap (GDD-07 §8), not an error. |
| Wage bands | `professions.json income_band_monthly` and `prices.json wages_monthly` are currently **equal for 11/11 professions** — but they are two stored copies (see §4.2). |
| UE scaffold labelling | **16/16** UE `.h/.cpp` files carry the UNCOMPILED SCAFFOLD header. The labelling discipline held across all queues. |
| `schema.sql` | 19 `CREATE TABLE`s (accounts → world_state). Never executed against a live database. |

---

## 3. Incomplete / partial items

1. **Units AB + AC — in flight** at audit time (finisher coordinator). Not on GitHub main; classified neither complete nor failed.
2. **Phase 1 (owner's PC) — not started.** Owner's PC specs (GPU/RAM/SSD) are still unknown; UE 5.8 has never been installed for this project. **Every UE artefact in the repo is blocked on this single external event.**
3. **Pilot profession has no workplace.** District 1 has no airport; pilot schedules exist but the profession cannot work its loop (documented honestly in GDD-06). Its economy row is also the known tight one (entry surplus 2.6% — an open owner decision, Queue 4 report §5; police/entry at 11.1% likewise noted).
4. **Non-buyable vehicles:** bus, truck, CNG have no prices (documented gap, GDD-07 §8).
5. **Furniture catalogue deferred** (GDD-10 prices furniture as rent multiples; no itemised data exists).
6. **Vehicle repair rate is a placeholder** (45 NCr/point, flagged in `docs/TECH-VEHICLES.md`; `prices.json` has no repair rate — the economy pass owns it and hasn't taken it).
7. **Snow weather is zone-gated to districts that don't exist** (no snow-zone district designed yet).
8. **Mission level names unconfirmed** by the owner (Unit G proposals still standing).
9. **Godot testbed coverage is narrow by design:** it tests movement/camera only. It proves control feel, nothing about the civilization systems.
10. **`STATUS.md` hygiene:** it still carries the full overnight push-block history and a stale "Completion summary (to be finalised after the batch PR merges)" section for Queue 1 — that merge happened long ago. History is worth keeping, but the stale pending framing could mislead a future session.

## 4. Duplicated logic & architectural weaknesses

1. **No committed validation harness (biggest process weakness).** Every unit's "scripted cross-reference validator" was run ad hoc by a coordinator and **not saved into the repo**. The repo contains exactly one executable checker (`tools/economy_sim.py`, covering only `prices.json` + `professions.json`). The data layer's integrity — 1:1 blockout↔buildings, the `part_of` 140 rule, clothing/vehicle refs, schedule↔profession match — is asserted in `STATUS.md` but **cannot be re-run from the repo**. This audit had to rewrite those checks from scratch to verify them. If data drifts, nothing will catch it.
2. **Wage bands are stored twice.** `professions.json income_band_monthly` ≡ `prices.json wages_monthly` (verified equal today, 11/11). The simulator reads `prices.json`; the GDD-01 profile model treats `professions.json` as canonical. Two sources of truth for the single most-tuned number set in the project — drift is a matter of time.
3. **Taxi rental is stored three times:** `prices.json taxi_fares.cab_rental_ncr_per_day`, `prices.json vehicles[taxi_licensed].rental_ncr_per_day`, and the `vehicles.json` taxi note. Queue 4 updated all three consistently; the duplication itself remains.
4. **The UE scaffold pile is unverifiable until one event occurs.** Units D, E, K, M, AA wrote ~1,750 lines of UE C++/config against the UE 5.8 API from memory of its conventions. None of it has been compiled. If the API usage is wrong anywhere, the rework lands on all five units at once, on the owner's PC, in Phase 1/3. This is acknowledged in every file header — but the *risk concentration* is the weakness, not any single file.
5. **Two persistence models, never reconciled by execution.** Relational PostgreSQL (Phase 9 authority) vs USaveGame + JSON society payloads (single player). `TECH-SAVE-SYSTEM.md` maps fields on paper; the mapping has never been tested, and the schema has never existed as a database.
6. **Data versioning without consumers' rules.** JSON files carry a `version` field (prices already at 1.2) but no migration/compat rule exists for anything that will read them (sim core, UE, server).
7. **Scale honesty is good; the bridge is missing.** Docs honestly cap multiplayer at 8–16 and District 1 at 140 homes, and GDD-06 designs crowd tiers. But the prompt's scalability techniques (aggregation, scheduled updates, spatial partitioning) exist only as GDD-06 tier prose — no engine implements them, so there is no evidence yet that the designed tiers actually hold population-scale numbers.

## 5. "Complete" on paper vs genuinely functional

| Claimed in STATUS/queues | Genuinely is |
|---|---|
| "Game Clock + Weather C++" (Unit E) | Uncompiled scaffold. No clock has ever ticked and no weather has ever changed in any running build. |
| "Save System Scaffold" (Unit M) | Uncompiled scaffold. No save file has ever been written or loaded. |
| "Character Movement C++" (Unit K) | Uncompiled port of the Godot values. The only character that has ever moved is the Godot capsule. |
| "Drivable Vehicle" (Unit AA) | Uncompiled pawn whose physics binding is deliberately absent; by its own documentation it will not move until Phase 5. |
| "Economy system" (Units F/T/U–X) | A real, valuable **balance checker** — static monthly arithmetic per profession. It is not a living economy: no agents, no transactions, no market, no time evolution. |
| "NPC Behaviour" (Unit O) | A thorough state-machine *design*. No NPC has ever behaved. |
| "UI & Panels" (Unit N) | A design + widget contract. No pixel of it exists. |
| "QA Pack" (Unit I) | Checklists. The only automated QA that exists in-repo is the Godot test suite + the simulator. |

None of this is hidden — the project's own labelling is unusually honest (scaffold headers, gap notes, deferred items all declared). The audit's point is narrower: **of the master prompt's vision, the genuinely functional set today is exactly two programmes — a Godot movement testbed and a Python economy balance checker — plus a well-validated design/data layer.** Everything else is paper or uncompiled code.

---

## 6. Implementation checklist (dependency-ordered)

External track (owner-side, blocks all UE verification — runs in parallel, not a Muse unit):
- **E0.** Owner PC specs → UE 5.8.x install → open `ue-project/Nexora.uproject` (Phase 1 build sheet). First compile of Units D/E/K/M/AA scaffolds; fix API errors as one batch.
- **E1.** Phase 1 400 m test scene from the Unit R subset (`phase1_test_scene` in `district1-blockout.json`); performance capture per the build sheet.

Muse-executable track (each unit: implement → test → verify → document, per the master prompt §2/§11):
1. **AD — Headless Simulation Core v1** (the next unit — brief in §7). Includes as its first milestone a **committed data validator** (`tools/validate_data.py`) covering every cross-reference this audit re-checked by hand, so integrity becomes re-runnable forever.
2. **AE — Data single-sourcing.** Wages live in exactly one file (the other becomes generated/derived or is removed); taxi rental in exactly one place. Gate: simulator output byte-identical before/after.
3. **AF — Sim Core v2: society.** Relationships + memory events between agents, life-stage transitions (school→work, aging steps) on top of AD's engine; conversation hooks from GDD-06 §6 become state changes, not prose.
4. **AG — Government & public finance v1.** First-ever government artefact: the sim's existing tax lines become revenue; a minimal public-budget model (services funded from revenue, measurable effects on needs/security) designed in a GDD and implemented in the sim core. Closes the audit's clearest ABSENT.
5. **AH — Environment v2.** Seasons cycle + one disaster class (river flood, using District 1's river) + pollution accumulator, all as sim-core systems consuming `weather-presets.json` effects; UE weather scaffold stays the presentation layer.
6. **AI — Observation surface.** A read-only report/dashboard generator over sim-core state (population, economy, weather, per-agent drill-down) — the first honest version of prompt §10, fed by real simulated data.
7. **AJ — Persistence proof.** Apply `schema.sql` to a real local PostgreSQL (or SQLite port) in the VM; sim core saves/loads world state through it; round-trip test. Retires weakness §4.5 with evidence.
8. Then, and only then, UE-side implementation units resume (Phase 3/5/6 ports of *proven* sim rules), informed by E0/E1 results.

In-flight, not on this list: **AB + AC** (finisher coordinator) — expected to land as DESIGN docs; they change no classification above.

---

## 7. THE NEXT UNIT — brief

### Unit AD — Headless Simulation Core v1 (deterministic tick engine over the merged data)

**Why this unit, from the evidence:** The audit's central finding is that NEXORA's defining system — autonomous agents living over time (§7 of this audit) — has zero executable code, while every input it needs already exists and is verified: professions + starting balances, schedule templates (11 professions + 3 life stages), the finite 140-unit housing stock, the tuned price/wage/rent model, weather presets with gameplay effects, and written rules for all of it (GDD-01 §4 tick model, GDD-06 state machines and weather interrupts). The alternative "next unit" by roadmap order is Phase 1, but Phase 1 is owner-PC work that Muse cannot execute or verify in this VM, and it has been blocked on the owner's PC specs since 2026-11-20 — queuing more UE scaffold behind it only grows the unverified pile (§4.4). A headless core is genuinely implementable and testable here, is engine-agnostic (its rules are exactly what UE will later present, per Phases 5–6), and converts the largest DESIGN/ABSENT block into REAL. It also directly serves the master prompt's §9 requirements (deterministic, configurable speed, scheduled/tiered agent updates, save/restore) in the one environment where they can be proven today.

**Scope (v1, no more):** `tools/sim_core.py` (+ `tools/validate_data.py` gate) — agents generated from the merged data; minute-tick clock with configurable speed; GDD-06 schedule state machine; GDD-01 §4 needs evolving and bending schedules (GDD-06 §8); households placed into the finite housing stock with GDD-10 doubling-up; daily/monthly ledger per agent; deterministic daily weather from presets applying `gameplay_effects`; JSON state save/restore. Out of scope for v1: relationships/memory events (AF), government (AG), seasons/disasters (AH), any UE work.

**Completion criteria (all must pass in the VM before the unit is called complete):**
1. **Validation gate:** `tools/validate_data.py` runs first and fails the run on any unresolved cross-reference (professions↔schedules, blockout↔buildings incl. the `part_of` 140 rule, clothing/vehicle `price_ref`s, mission/zones refs). The validator is committed and re-runnable.
2. **Determinism:** same seed → byte-identical summary output across two runs (the standard the economy sim already meets).
3. **Population:** ≥ 100 agents spanning all 11 professions + child/student/elder templates; every agent housed within the 140-unit stock (doubling-up allowed, stock never exceeded — asserted).
4. **Schedule truth:** at every tick, every agent is in exactly one valid GDD-06 activity; a coverage report shows no agent idle/unassigned over a 30-day run.
5. **Economy reconciliation:** per-profession monthly net from the tick engine matches `economy_sim.py` v2 figures within a stated tolerance (the two engines must agree, or the difference is explained in the unit report).
6. **Weather coupling:** at least one `gameplay_effects` flag demonstrably changes agent behaviour in a test (e.g. storm day alters commute/work states vs a clear day, same seed).
7. **Save/restore:** state serialised at day 15, restored, and continued to day 30 produces output identical to an uninterrupted 30-day run.
8. **Performance/scalability:** 100 agents × 30 days completes in < 60 s in this VM; agent updates are scheduled/tiered (not every agent fully processed every tick) and the report states the update model.
9. **Tests committed:** an automated test suite in-repo covering criteria 2, 4, 5 (sample), 6, 7 — all passing; run output and limitations documented in the unit's report doc, with simulated-vs-real data clearly distinguished (all data here is simulated by construction).

*End of audit.*
