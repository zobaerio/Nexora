# NEXORA — GDD-06: NPC Behaviour Design

**Unit O · Version 1.0 · 2026-11-21**
**Parent documents:** `NEXORA-MIGRATION-PLAN.md` Phase 6 · `docs/GDD-01-LIFE-AND-DATA-MODEL.md` §2 (tiers, personality, goals), §2.3 (memory), §4 (daily tick) · `data/npc-schedules.json` (11 profession templates + 3 life-stage templates) · `data/professions.json` · `data/weather-presets.json` (`gameplay_effects`) · `docs/PHASE2-METAHUMAN-SHEET.md` §6 (crowd-tier rendering) · `docs/TECH-CLOCK-WEATHER.md` §2, §4 (schedule/weather consumers)
**Status:** DESIGN ONLY. No behaviour tree, StateTree asset or Mass configuration exists yet; nothing here claims an NPC does anything today. This document is the contract Phase 6 implements against.

> **Design law:** an NPC's day is *data first* — a schedule template (Unit C) instantiated for one character, bent by that character's needs and traits (GDD-01), interrupted by weather and by the player. Behaviour code never hard-codes a profession's day; it executes the template. If a behaviour cannot be traced to a template block, a need, a trait weight or a documented interrupt, it does not ship.

---

## 1. The Three Layers

| Layer | Owns | Source |
|---|---|---|
| **Schedule** | *Where* the NPC is and *which activity* runs, block by block through the day | `data/npc-schedules.json` template for the NPC's profession (or life-stage template), instantiated with per-NPC jitter (§3) |
| **State machine** | *How* an activity is performed and how the NPC moves between activities | This document (§2, §4) — one generic machine, profession sub-states for `work` |
| **Modifiers** | *Deviations* — needs bending tomorrow's template, traits weighting choices, weather interrupts, player interaction | GDD-01 §2.1/§2.2/§4, `data/weather-presets.json` `gameplay_effects` (§7) |

The daily tick (GDD-01 §4) is the metronome: schedule block runs → economy tick → needs update → relationship drift → life-events roll. The state machine is what the tick looks like from street level.

## 2. The Generic State Machine

States are named after the schedule vocabulary — the 8 activities in `npc-schedules.json` — plus three interrupt states. An NPC is always in exactly one state; the current schedule block selects the activity state, interrupts pre-empt it.

| State | From activity | Behaviour | Ends when |
|---|---|---|---|
| `Sleep` | `sleep` | At home anchor, in bed; not interruptible except by life events (illness, emergency) | Block ends |
| `AtHome` | `home` | Home anchor: idle loops, household interactions, meals (food need recovers) | Block ends |
| `Commute` | `commute` | Travel home↔workplace via the anchor graph (§3): walk → rickshaw/CNG → walk, per district transport (GDD-02) | Arrival |
| `Work` | `work` | Profession sub-state (§4) at the workplace anchor (or `mobile`, §4.7) | Block ends |
| `Break` | `break` | Short anchor visit (tea stall, home, market per template); social/food micro-recovery | Block ends |
| `Errand` | `errand` | Travel to a service anchor (market), transact (ledger row), return | Transaction done or block ends |
| `Leisure` | `leisure` | At the NPC's leisure anchor (§3); social need recovers; ambient conversation with co-present NPCs | Block ends |
| `Study` | `study` | At home/college/school anchor; skill experience accrues (GDD-01 §2.1) | Block ends |
| `SeekCover` | interrupt | Weather interrupt (§7): move to nearest covered anchor, wait out the effect | Weather effect clears |
| `Converse` | interrupt | Player-initiated dialogue (§6); schedule state is *suspended*, not advanced | Dialogue ends → resume suspended state if its block is still current, else transition to the now-current block |
| `OffDuty` | template gap | A template with no block for the current time (e.g. pilot, §4.11) resolves to `AtHome`/`Leisure` by needs — never to standing still | Next block starts |

**Transition rules:**
1. Block boundaries are soft: a state finishes its current micro-action (a transaction, a vehicle boarding) before transitioning; nobody teleports mid-gesture. Hard cap 30 in-game seconds of overrun.
2. `Commute` is the only state that moves an NPC between anchors; every other state is anchored. If the player sees an NPC walking, it is commuting, erranding, seeking cover, or on a work sub-state that moves (patrol, fare loop).
3. Interrupts queue by priority: life event > weather (`SeekCover`) > player (`Converse`). A sleeping NPC cannot be conversed with; a conversing NPC does not seek cover until the dialogue ends (the player is standing in the rain too).
4. Tier gating: Full and Scheduled tiers run this machine. Ambient tier runs a reduced two-state version (`Move` along crowd flows / `IdleAtAnchor`) inside Mass (§5) — it has no schedule, no needs, no memory, and the design never pretends otherwise (GDD-01 §4).

## 3. Anchors, Templates & Jitter

**Location tokens → anchors.** Schedule blocks name *tokens*, not coordinates. Resolution at spawn:

| Token | Resolves to | Notes |
|---|---|---|
| `home` | The NPC's household property (GDD-01 §5) | Every Scheduled/Full NPC has one. |
| `workplace` | The property/building of the NPC's employment row | From `data/buildings-district1.json` stock by profession-appropriate type/zone (§4). |
| `transit` | Nearest stop on the commute path | Path = anchor graph over GDD-02's road hierarchy. |
| `tea_stall`, `market`, `riverfront`, `park`, `restaurant`, `college_para` | Nearest leisure/service anchor of that type in the NPC's zone cluster | The template's `leisure_anchor_default` (e.g. civil engineer's `tea_stall`) picks the default; needs can re-pick (§8). Zones: `d1_market`, `d1_oldtown`, `d1_riverfront`, `d1_midtown`, `d1_civic`, `d1_education`, `d1_industry`, `d1_park`, `d1_transport`, `d1_uptown`. |
| `college`, `school` | The education buildings in `d1_education` | Used by life-stage templates and the software developer's leisure anchor area. |
| `mobile` | No anchor — the work *is* movement | Taxi driver (fare loop), business owner's second work block. §4. |

**Jitter:** templates are shared; days must not be. At instantiation, each block boundary shifts by a per-NPC fixed offset (±20 in-game minutes, seeded by character id — the same NPC is consistently an early riser) and each NPC's leisure anchor is fixed from the template default ± personality (high sociability → busier anchors: `tea_stall`, `market`; low → `park`, `home`). Jitter is computed once per in-game day at the tick, never per frame.

**Weekend variants:** templates carry a `weekend_variant` note (e.g. civil engineer: "Friday off… study block 10:00–12:00"). At instantiation on the district's weekend day, the variant replaces the work blocks as the note describes. Variants are data in the same file, applied by the same code path — not per-profession code.

## 4. Per-Profession Work Sub-States

The `Work` state is the only profession-specific part of the machine. Each entry: template id (= `profession_id` in both `professions.json` and `npc-schedules.json`), workplace anchor, sub-states.

### 4.1 `construction_worker` — construction site (active staged builds, GDD-03 flagship loop sites)
Sub-states: `Arrive → TaskLoop (carry/lay/assemble at the current construction stage) → Break → TaskLoop → Leave`. The worker's task visibly matches the property's construction stage (GDD-01 §5) — a site at foundation stage shows foundation work. Outdoor work halts under `outdoor_work_halted`-class weather (§7).

### 4.2 `civil_engineer` — site (morning) + office (afternoon), per the template's own notes
Sub-states: AM `SiteSupervision` (walk the site, inspect stage points — the mirror of the player's flagship loop, GDD-03), PM `OfficeWork` (desk: plans/estimates). Break and leisure both default to `tea_stall`. This is the reference implementation for split-anchor work: the midday block change is a `Commute`-class move between two workplace anchors.

### 4.3 `doctor` — hospital/clinic in `d1_civic`
Sub-states: `Rounds → ConsultLoop (patients = Scheduled NPCs with illness events, or ambient patients as visual only) → Break(at home per template) → ConsultLoop`. Night calls arrive only as life events (GDD-01 §4 step 5), never as random ambushes.

### 4.4 `teacher` — school in `d1_education`
Sub-states: `ClassLoop (teach to a class anchor group) → Break → ClassLoop`, plus the template's home `study` block (lesson prep — skill accrual). Students present are the `child_school_day`/`student_day` life-stage NPCs (§4.12) — the two template families meet in the same room.

### 4.5 `police_officer` — station in `d1_civic` + patrol
Sub-states: `Briefing → Patrol (waypoint loop through assigned zone) → StationDesk → Patrol`. Patrol is a moving work sub-state (like `mobile` but on foot/vehicle waypoints). Incident response is event-driven from the life-events table, not scripted chases.

### 4.6 `taxi_driver` — `mobile` work (the fare loop)
Sub-states: `Cruise (drive the road graph, no passenger) → Pickup (stop for a hailing NPC) → CarryPassenger (drive to passenger's destination anchor) → Dropoff (ledger fare row) → Cruise`. Passengers are Scheduled NPCs whose current state is `Commute` with a taxi preference, or Ambient crowd members visually. Demand modifiers come from weather (`taxi_demand_up`, §7). The player's own taxi loop (GDD-03) is this same machine with the player in the driver seat.

### 4.7 `chef` — restaurant/kitchen workplace; morning `errand@market` is part of the job
Sub-states: `MarketRun (the template's errand block — buy ingredients, business ledger rows) → Prep → ServiceLoop (cook/serve during meal blocks) → Break(at home) → ServiceLoop`. A chef whose employer is a player-owned restaurant uses the player's business stock — same machine, different ledger.

### 4.8 `software_developer` — office in `d1_uptown`
Sub-states: `DeepWork (long desk blocks) → Break(at market per template) → DeepWork`, leisure at `college_para`. The most sedentary machine by design; social needs bend it hardest (§8) because its template has the fewest social blocks.

### 4.9 `shop_owner` — own shop (property from `buildings-district1.json` commercial stock)
Sub-states: `OpenShop (stock/shutter) → ServeLoop (customers transact — ledger rows to the business) → Break(at home) → ServeLoop → CloseShop`. The shop's open hours *are* the template's work blocks; a closed shop at 11:00 means its owner is in another state, and the world shows that honestly.

### 4.10 `business_owner` — office + `mobile` second block
Sub-states: `OfficeBlock (desk, meetings with Scheduled NPCs) → Break(at restaurant) → MobileBlock (travel between owned properties, inspect) → Leisure(riverfront)`. Owns through the business model (GDD-03); the machine reads owned properties as its waypoint set.

### 4.11 `pilot` — resident without a District 1 workplace (honest gap)
The pilot template has **no `work` and no `commute` block**: District 1 has no airport (the launch terminal belongs to Level 8's space programme, GDD-04), and this design does not invent one. Pilot NPCs live their template as written — home, `study@home` (licence renewal study), leisure at `park`/`riverfront` — i.e. they are modelled as crew on rest days between off-district rotations. When an airport district exists (later phases), the pilot template gains work blocks in data and this section is revised; until then a pilot "at work" is off-map by design, and the population counts in GDD-02 already treat them as residents, not as district workers.

### 4.12 Life-stage templates (not professions)
| Template | Used by | Machine differences |
|---|---|---|
| `child_school_day` | Child stage (GDD-01 §3) | `study@school` is the work-equivalent; no economy tick of their own (household pool, §5 GDD-01); never in `Converse` alone with strangers — dialogue routes to a parent/guardian NPC where one exists. |
| `student_day` | Teen/Young Adult students | `study@college` blocks; some instantiate the template's part-time variant (a `work` block at a market/shop anchor) per the template note. |
| `elder_day` | Elder stage | Home-centric; movement speed scaled; leisure at `park`; needs skew to rest/security. |

## 5. Crowd Tiers & Promotion (with PHASE2-METAHUMAN-SHEET §6)

Simulation tier (GDD-01 §2) and rendering tier are the same decision, made once:

| Tier | Behaviour | Rendering (Phase 2 sheet §6) | Count discipline |
|---|---|---|---|
| **Full** | This whole document: schedule, needs, goals, both memory kinds | Full MetaHuman, LOD0/1, full face animation | Player + ~25 named NPCs per district — authored, never auto-promoted |
| **Scheduled** | Schedule + needs + semantic memory; simplified goals; no episodic memory beyond relationship scores | MetaHuman preset pool, LOD0/2, preset expressions + lip-sync for dialogue lines | District residents with homes/jobs (GDD-02 population model) |
| **Ambient** | Mass framework: reduced `Move`/`IdleAtAnchor` only | Mass representation — not MetaHumans, no faces, culled beyond 50 m | Crowd flows: market rush, riverfront evening, transit peaks |

**Promotion (Ambient → Scheduled):** triggered only by player interaction (talk attempt, transaction, mission reference) or by a life event naming the NPC. Promotion is a *spawn-in of depth*: the NPC receives an identity row, a home, a profession + schedule template (rolled from the district's resident distribution), and semantic-memory flags for the triggering interaction. It happens at the next anchor transition, not mid-gesture — the person you bumped into in the market "becomes someone" when they reach their stall, and from then on they remember you (§6).
**No automatic Full promotion.** Full tier is authored content (~25/district); the design does not let crowd members drift into the most expensive tier.
**Demotion (Scheduled → Ambient):** only for NPCs with no home/job anchor in the *current* district (visitors), after they leave it, and never for anyone with a relationship score ≠ 0 with the player or an open mission reference. Hysteresis: a promoted NPC cannot demote within the same in-game day. Demotion archives the identity row (it is not deleted — return visits restore the same person, semantic memory intact).

## 6. Conversation & Memory Hooks

Conversation is authored branching dialogue whose *entry conditions and outcomes* are memory operations. No free-form text generation is designed anywhere in this document (§8).

**Entry:** player uses `IA_Interact` on a Full/Scheduled NPC in an interruptible state (not `Sleep`, not a moving work sub-state). Ambient NPCs promote first (§5) — one beat of "the stallholder looks up", then dialogue with a Scheduled NPC.

**What the dialogue system reads (semantic memory, GDD-01 §2.3):**
- Relationship edge player↔NPC: trust/affection/respect scores → greeting tone band (hostile / wary / neutral / warm / close).
- Flags on the employment/relationship rows: `met_player`, `worked_with_player`, "X employs me", "Y owes me money" → topic unlocks (job offers, debt collection, referrals).
- NPC's current goal stack (§2.2) → the "what are you working toward" topics and the mission offers the mission system routes through people (GDD-04).

**What it reads (episodic memory, Full tier only):** top-weighted recent `character_memories` involving the player — a helped NPC (weight +) opens with thanks and may offer a favour; a harmed NPC (weight −) refuses services or raises prices within the economy's rules. This is the concrete mechanism behind Phase 6's "NPCs remember you" exit criterion: rows, weights, and three named consumers (greeting band, topic unlocks, service refusal) — not a promise of emergent storytelling.

**What a conversation writes:** at minimum the `met_player` flag and a relationship drift (small, per GDD-01 §4 step 4 — big changes only from events). Job acceptances, loans, promises write their real rows (employment, ledger, goals). A conversation that changes nothing in the data is a failed conversation design and is cut.

**Scheduled-tier limits:** preset expressions + lip-sync for dialogue lines (Phase 2 sheet §6); no episodic tab. **Ambient:** no dialogue at all pre-promotion — they are visual life, and giving them fake chatter would be exactly the dishonesty the tier exists to avoid.

## 7. Weather Interrupts (data: `weather-presets.json` `gameplay_effects`)

The weather manager broadcasts preset changes (TECH-CLOCK-WEATHER §4); behaviour consumes the *effect flags*, never the preset name:

| Effect flag | Presets | Behaviour response |
|---|---|---|
| `npc_cover_seeking` | `rain` | Leisure/Break states at uncovered anchors → `SeekCover` to nearest covered anchor; Commute continues (people still get home). |
| `npc_cover_seeking_strong` | `storm` | As above, plus outdoor Work sub-states suspend (construction, patrol shortens to station), Leisure cancels to `AtHome`. |
| `taxi_demand_up` / `taxi_demand_up_high` | `rain` / `storm` | Taxi fare-loop: more hailing NPCs (Commute states choose taxi), fare multiplier per GDD-03. |
| `road_grip_down`, `traffic_speed_down`, `visibility_down` | `rain`, `fog`, `snow` | Commute/fare-loop speeds and following distances adjust; arrival jitter widens (blocks overrun within the §2 cap). |
| `road_grip_down_high` | `snow` | As `road_grip_down`, stronger: wheeled commutes in snow zones may convert to walk/transit anchors entirely (snow zones only — District 1 never sees this flag). |
| `launch_terminal_caution` | `fog` | Launch-terminal operations slow (Level 8, GDD-04); no District 1 street-level effect — recorded so the flag has a named consumer instead of none. |
| `river_level_up_visual` | `storm` | Riverfront leisure anchors close for the preset's duration (visual + anchor state, one system). |
| `flight_and_launch_delays` | `storm` | Pilot/off-district rotations delay (flavour state on pilot NPCs); Level 8 launch-terminal missions gate on it (GDD-04). |
| `npc_warm_clothing` | `snow` | Outfit variant swap (snow zones only — District 1 never sees this flag; TECH-CLOCK-WEATHER §6). |

## 8. Needs Bending the Schedule (GDD-01 §4 step 3)

At each daily tick, deficits convert to *wants* that edit tomorrow's instantiated template — edits, never rewrites:

| Deficit | Template edit |
|---|---|
| Food | Insert an `errand@market` block (30–60 min) into the longest home block; chef/shop-owner templates instead extend their existing market block. |
| Social | Leisure anchor re-picks to the most social anchor in the NPC's set (`tea_stall` over `home`); a second leisure block may split off a home block. |
| Rest | Next day's first work block starts one jitter-step later; `Sleep` block extends by up to 1 hour, taken from the evening home block. |
| Security | Commute avoids unlit routes after dark (anchor-graph edge weights), elder/child templates drop evening leisure. |

Traits weight the edits: high *discipline* resists rest-bending; high *sociability* amplifies social-bending; high *risk_tolerance* ignores security-bending. The numbers live with the tick design (GDD-01), not in per-NPC code.

## 9. Honesty Notes — What Mass AI Can and Cannot Do at This Scale

These limits are the design's boundaries, stated so no later phase is planned against a fiction:

1. **Mass agents are not characters.** UE Mass entities are data fragments processed in bulk — no per-agent `ACharacter`, no individual complex pathfinding (Mass uses its own grid/avoidance, not per-agent NavMesh queries at crowd scale), no physics bodies, no MetaHuman faces (Phase 2 sheet §6). Ambient crowds *look* alive in aggregate; any single ambient NPC has no inner life to inspect. That is why promotion (§5) exists as a designed moment instead of pretending depth was there all along.
2. **StateTree/utility selection is shared and cheap by design.** Mass/StateTree evaluation runs at crowd tick rates with per-agent state kept tiny. It can run the §2 machine for Scheduled NPCs (hundreds, at district scale) — it cannot run GDD-01's full tick (ledger, goals, episodic memory) for thousands. The tier counts in §5 are not caution; they are the budget.
3. **Schedules are templates, not authored days.** 11 profession templates + 3 life-stage templates, instantiated with jitter and need-bending, produce believable variety. They do not produce 500 unique hand-written lives, and dialogue (§6) is authored branching on memory flags — there is no LLM-driven free conversation in this design, and none should be implied to players.
4. **Off-screen simulation is the tick, not the machine.** NPCs outside the player's area do not run the state machine spatially; their day advances by the GDD-01 §4 tick and their position is *derived* from their current block when the player arrives. Two consequences are accepted honestly: you cannot follow an NPC's unbroken physical journey across the whole district in v1, and an NPC's anchor arrival time is computed, not witnessed. (Named Full-tier NPCs near the player are the exception the Phase 6 tests exercise.)
5. **Crowd counts are perf-gated.** Ambient density follows the Phase 1/2 performance captures, not a marketing number; if the owner's PC capture says 300 ambient agents, the district ships 300.

## 10. Acceptance Checks (for Phase 6 implementation)

1. One Scheduled NPC of each of the 11 professions lives a full in-game day: every template block fires, in order, at resolved anchors; the day's ledger rows match the blocks (wages, fares, purchases).
2. Promotion: interact with an ambient NPC → at their next anchor they are Scheduled with identity, home, template; a second conversation reads `met_player` and greets accordingly.
3. Memory: help a Full-tier NPC (scripted event) → episodic row with positive weight exists; their greeting band and topics change; harm path likewise.
4. Weather: force `rain` → leisure NPCs seek cover, taxi demand rises; force `storm` → construction site suspends, riverfront anchors close.
5. Needs: starve an NPC's social need for 3 in-game days → their template bends (social leisure anchor) on day 4's tick.
6. Pilot honesty: pilot NPCs never appear at a District 1 workplace; their template runs with zero unresolved-anchor errors.

*End of GDD-06 v1.0.*
