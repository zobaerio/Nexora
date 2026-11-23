# NEXORA — GDD-04: Missions & Progression

**Unit G · Version 1.0 · 2026-11-20**
**Parent documents:** `NEXORA-MIGRATION-PLAN.md` Phases 3–10 · `docs/GDD-01-LIFE-AND-DATA-MODEL.md` §2.2 (goals), §3 (life stages) · `docs/GDD-03-ECONOMY-AND-PROFESSIONS.md` (job loops, rewards) · `docs/GDD-02-RUPSHA-CITY-DISTRICT1.md` (locations)
**Levels:** the owner gave the structure's endpoints — Level 1 **"A New Beginning"** and Level 8 **"Space Explorer"**. Levels 2–7 below are proposed from the Phase 1–10 roadmap so the progression has a complete shape; the owner confirms or renames them — the missions, not the names, are the design.

> **Design law:** missions are *offers*, not orders. NEXORA never fails a player for living differently (GDD-01 §2.2). A level is a bundle of missions and unlocks the player can work through at their own pace, in any order within the level, while free-roaming the whole time. There is no mission timer that ends a playthrough, no "game over" for ignoring the main path, and no mission that requires a purchase or a grind the economy cannot support (GDD-03 §9).

---

## 1. How Levels Work

- **Levels 1–8** are progression chapters. Each level has 3–5 main missions + side missions that stay available afterwards.
- **Advancing a level** requires completing its main missions (all of them, in any order). Side missions and free-roam work count toward rewards but never gate advancement.
- **Rewards** are always one of: credits (ledger, reason `mission_reward`), reputation, a skill boost, an unlock (place, vehicle, tool, mechanic), or a story beat (a memory event, GDD-01 §2.3). Rewards are never a stat the player cannot also earn by free-roam play — levels accelerate, they do not monopolise.
- **A mission reads the goal stack** (GDD-01 §2.2): the game offers missions matching the player's chosen life goal first. A player whose life goal is "own a construction company" sees construction missions; a player who chose "become chief surgeon" sees clinic missions. The level structure is the same; the content bends.
- **Failure:** a mission can fail (deadline missed, client unhappy). A failed mission can be retried after 7 in-game days, or abandoned for a reputation cost. The level is never blocked by one failed mission — the retry is the design.

## 2. The Levels

### Level 1 — A New Beginning
*Arrive in Rupsha City, District 1. The owner's start: rented apartment, entry job available, 25,000 NCr.*

| # | Mission | Objectives | Reward | Unlock |
|---|---|---|---|---|
| 1.1 | First Steps | Arrive at the launch terminal; walk to your apartment; sleep one night | 1,000 NCr, +5 reputation (district) | Apartment (home anchor), bicycle purchase |
| 1.2 | A Job to Do | Visit the job board; take any entry job; complete one full work day | First wage (per GDD-03 §2) | Job board filters, work uniform |
| 1.3 | Know Your Neighbours | Meet 3 neighbours; help one with a small task (carry, fetch, fix) | +10 relationship (each), +5 reputation | Neighbour favour system |
| 1.4 | The River at Dusk | Watch the sunset from the riverfront promenade; visit the tea stall | Memory event "First evening in Rupsha" | Promenade leisure anchor, photo mode |

**Level 1 complete →** Level 2 unlocks; the player keeps the apartment and the job.

### Level 2 — Settling In
*Make the district home: a routine, a skill, a small safety net.*

| # | Mission | Objectives | Reward | Unlock |
|---|---|---|---|---|
| 2.1 | Learn the Trade | Reach skill 20 in your profession's primary skill | 2,000 NCr, +10 profession reputation | Skill training (evening classes) |
| 2.2 | Rainy Day Fund | Save 15,000 NCr above your starting balance | 1,500 NCr interest bonus | Bank savings account (4% annual, GDD-03 §4.4) |
| 2.3 | The Market Run | Buy a week's food at Boro Bazar; haggle once, successfully | 500 NCr, +5 market reputation | Haggling, market regular status |
| 2.4 | A Friend in the City | Raise one friendship to 40+ (trust/affection) | Memory event, +10 reputation | Friend favour missions |

### Level 3 — First Home
*Stop renting. Own something, however small.*

| # | Mission | Objectives | Reward | Unlock |
|---|---|---|---|---|
| 3.1 | The Deposit | Save 70,000 NCr (20% of a Tier 2 flat) or secure a mortgage | 3,000 NCr | Mortgage applications (GDD-03 §4.3) |
| 3.2 | House Hunting | View 3 properties; choose one; complete the purchase | Property deed (Tier 2 flat) | Property ownership, furnishing (Phase 5/6) |
| 3.3 | Make It Yours | Furnish the flat from the catalogue (5 items, any tier) | +10 comfort, memory event | Furniture catalogue, home customisation |
| 3.4 | Housewarming | Host 3 friends at home | +15 relationships, +10 reputation | Hosting / social events |

### Level 4 — Master Your Craft
*Become the person the district calls when it matters.*

| # | Mission | Objectives | Reward | Unlock |
|---|---|---|---|---|
| 4.1 | Mid-Tier | Reach Mid tier in your profession (GDD-03 §2) | Wage band rises to Mid | Mid-tier jobs, mentoring |
| 4.2 | The Big Job | Complete one flagship-loop job end to end (Civil Engineer: plan → estimate → supervise → payment; other professions: equivalent loop) | Fee + 5,000 NCr bonus, +20 reputation | Large contracts |
| 4.3 | Teach Someone | Mentor a junior (NPC) to skill 20 | +15 reputation, memory event | Mentoring system |
| 4.4 | Storm Season | Work through one storm week without missing a shift | 2,000 NCr, +10 resilience trait nudge | Weather-hardened reputation |

### Level 5 — Roots & Family
*Life stages turn: partnership, household, the next generation (GDD-01 §3, §6).*

| # | Mission | Objectives | Reward | Unlock |
|---|---|---|---|---|
| 5.1 | Someone Special | Build a relationship to partner level (affection 70+) | Memory event "Partnership" | Partnership / marriage events |
| 5.2 | A Household Together | Form or join a household; share the expense pool | Household management UI | Joint finances, shared property |
| 5.3 | The Next Generation | Welcome a child (birth/adoption event) | Memory event, +20 family reputation | Child life stage, school system |
| 5.4 | The Family Business | Start a business with a family member, or employ one | Business licence fee waived | Family business rules (GDD-03 §5) |

### Level 6 — A Name in the City
*Influence: the district knows you, and the city asks for your help.*

| # | Mission | Objectives | Reward | Unlock |
|---|---|---|---|---|
| 6.1 | Senior Tier | Reach Senior tier in your profession | Wage band rises to Senior | Senior contracts, city advisory |
| 6.2 | The Civic Job | Complete a city contract (school repair, market upgrade, riverfront work) | 25,000 NCr, +30 city reputation | City contracts board |
| 6.3 | Employ Others | Hire 3 employees (NPC) and pay them for 30 days | Business reputation +20 | Employer status, payroll |
| 6.4 | The District Festival | Help organise the district festival (fund, staff, or build) | Memory event, +25 reputation | Festival (annual event) |

### Level 7 — Beyond One City
*District 2, City 2, and the road between them (Phase 8).*

| # | Mission | Objectives | Reward | Unlock |
|---|---|---|---|---|
| 7.1 | The Other Side | Travel to District 2 / City 2; spend 3 nights there | 5,000 NCr, travel memory | Inter-city travel, second home |
| 7.2 | Two-City Business | Open a branch or take a contract in the second city | 15,000 NCr, +20 reputation (new city) | Branch businesses |
| 7.3 | The Long Road | Drive/ride the inter-city route in one trip (no fast travel) | 3,000 NCr, memory event | Route mastery, roadside stops |
| 7.4 | A Bridge Between | Complete a cross-city project (both cities benefit) | +40 reputation (both cities) | Cross-city contracts |

### Level 8 — Space Explorer
*The owner's endpoint: leave the planet. Phase 10.*

| # | Mission | Objectives | Reward | Unlock |
|---|---|---|---|---|
| 8.1 | The Application | Qualify for the space programme (Senior tier + savings 500,000 NCr + reputation 80) | Programme acceptance | Space programme |
| 8.2 | Training | Complete zero-g and survival training (skill challenges) | 10,000 NCr, +30 reputation | Training facility |
| 8.3 | First Launch | Crew the first mission to Nexora-7 (data card in `data/planets.json`) | Memory event "First launch" | Spacecraft, Nexora-7 landing |
| 8.4 | A New World | Establish the first foothold on Nexora-7; return with a survey | 50,000 NCr, title "Space Explorer" | Planetary settlement (Phase 10) |

**Level 8 complete →** the "Space Explorer" title, planetary travel, and the open-ended endgame: the player keeps living — new cities, new planets, new generations (GDD-01 §3).

## 3. Side Missions (always available, never gating)

| Type | Examples | Reward pattern |
|---|---|---|
| Errands | Deliver, fetch, carry, fix for an NPC | 200–2,000 NCr + relationship |
| Work shifts | Extra shifts, overtime, cover for a sick colleague | Wage + reputation |
| Favours | Lend money (ledger loan, GDD-03 §4.3), mediate a dispute, find a lost item | Relationship + small credits |
| Events | Festival stalls, storm clean-up, market day | Reputation + memory events |
| Discovery | Find all landmarks, photograph the district, ride every bus route | 500 NCr each + "Explorer" progress |

Side missions are generated from the simulation (an NPC with a need, a business short-staffed, a weather event) — they are the world asking, not a checklist the designers wrote once.

### 3.1 Favour Generation Contract (Unit BC · Queue 10 · 2026-11-22)

**Status:** DESIGN ONLY. This contract defines the side-mission generator gap AV G2 named: what a generated favour is, how `favour_available` is evaluated, and what the generator must never invent. It adds no sim module and no data file — the contract is the deliverable. The generator (Phase 6) implements against it; dialogue delivers the offer (GDD-15 §15).

**What a generated favour is.** An *instance* of one of the five §3 types, generated from live state at conversation time. It is not a `missions.json` entry and never receives a `missions.json` id: the 32 ids in `data/missions.json` (`1.1`–`8.4`) are the main missions, and a favour is none of them. An accepted favour is recorded in `mission_progress` (`data/schema.sql`: `mission_id TEXT NOT NULL`, no foreign key) under a runtime instance key of the form `side:<type>:<giver_character_id>:<generated_at_game_minutes>` — a runtime key format defined by this contract, not a mission id. The instance carries: `favour_type` (one of the five §3 types), `giver` (the NPC's character id), `parameters` (the existing ids the favour concerns — a property id, a character id, a business id, a zone id — never an invented entity), and `reward` (within the §3 pattern for the type, set at generation and recorded on the instance). A favour has **no deadline and no expiry**: no source gives one (AV gap G10 — no mission in `missions.json` carries a deadline field), and the generator must not invent one.

**Reward rule.** The reward is chosen by the generator at generation time, inside the §3 pattern for the type, and recorded on the instance; it is never negotiated in dialogue (GDD-15 §4) and never outside the pattern. The patterns, verbatim from §3:

| Type | Reward pattern (§3) |
|---|---|
| Errands (`errands`) | 200-2,000 NCr + relationship |
| Work shifts (`work_shifts`) | Wage + reputation |
| Favours (`favours`) | Relationship + small credits |
| Events (`events`) | Reputation + memory events |
| Discovery (`discovery`) | 500 NCr each + Explorer progress |

The exact amount inside a range (for example, where in 200-2,000 NCr an errand falls) is **not decided here** — no source gives the pick rule, and this contract does not invent one. The Phase 6 generator records its pick rule when it is built; until then the bound is the pattern. "Small credits" for the favour type is likewise the pattern's own wording: the generator must stay inside it, and the amount is set at generation, never haggled in dialogue.

**Eligibility — per type, from live state.** A type is eligible for an NPC only when the live-state input in its row exists. Every input is a record a merged system already writes; where no such record exists, the type is ungeneratable and the generator must not offer it (see the last two rows).

| Type | Eligible when (live-state input) | Source of the input |
|---|---|---|
| Errands (`errands`) | The NPC has an open needs-driven want (GDD-01 §2.2) for a fetch, carry or fix — a want the needs/decision engines recorded, naming an existing target (a property, a person, a zone) | GDD-01 §2.2 (needs-driven wants); Session 01 needs engine (`tools/sim/needs.py`, `decisions.py`) |
| Work shifts (`work_shifts`) | An open vacancy exists at a business the NPC works at or for, and the player meets its credential gate — or a colleague of the NPC is absent with an open health condition the shift would cover | Session 04 labour market (`tools/sim/labour.py` vacancies; credential gates); Session 06 health conditions (`tools/sim/health.py`) |
| Favours — lend money (`favours`) | The NPC's household is in arrears, or the NPC has an active bank loan with at least one missed payment — and no outstanding character↔character loan already exists between this NPC and the player (one open loan per pair, GDD-15 §20.4) — and the loan the favour creates is a character↔character ledger loan (`loan_disburse` / `loan_repay`, GDD-15 §14), never a bank loan; the loan instance is defined in GDD-15 §20 (Unit BN) | Session 02 family economy (`tools/sim/family_economy.py` arrears); Session 04 banking (`tools/sim/banking.py` `missed_payments`); GDD-15 §20 |
| Favours — mediate a dispute (`favours`) | An open conflict involves the NPC, and the player qualifies as a mediator for it (a friend of a party, or a community leader — the roles the conflict system already allows) | Session 02 conflicts (`tools/sim/conflicts.py` mediation by leader/friend/elder) |
| Favours — find a lost item (`favours`) | A `lost_items` row exists with `owner_character_id` = the NPC and `status = 'lost'` — the record is defined in GDD-04 §3.3 (Unit BL). The favour's parameters are the row (`item_instance_id`, `lost_zone`, `lost_anchor` where set). No such row exists in any live world yet — no merged event writes a loss — so until a losing event is wired to the record, the check finds nothing and the generator offers nothing. *(Update, Unit BX · Queue 14: the three losing events are designed in §3.3 — commute incident, storm-soaked market trip, move-house — but none is wired yet, and the sim holds no personal inventory to lose from, so the check still finds nothing in a live world.)* *(Update, Unit CX · Queue 15: the inventory record is designed in §3.3 below — sim `inventory_items` table, seeding points named per type; the table and the seeding are Phase 6 work, so still no rows in a live world.)* *(Update, Unit CY · Queue 15: the three events are now wired (`record_loss()` + hooks in safety/environment/households) with the loss rate in `data/lost-items-config.json`, default 0 — specified but silent — so the check still finds nothing in a live world until an owner tuning call sets the rate.)* | GDD-04 §3.3 (`lost_items`); `data/schema.sql` `inventory_items`; GDD-15 §18 (`current_zone_at`) |
| Events (`events`) | A festival stands on the culture calendar, or a recorded storm/disaster impact in the NPC's zone needs clean-up (a festival stall to staff, storm debris to clear, a market day to run) | Session 02 culture (`tools/sim/culture.py` festival calendar; `tools/sim/events.py`); Session 07/08 environment (`tools/sim/environment.py` disaster impacts) |
| Discovery (`discovery`) | At least one discoverable in the §3.4 set has no `discovery_progress` row for the player's account — the record is defined in GDD-04 §3.4 (Unit BM): 14 landmarks (8 District 1 + 6 District 2, PROPOSED — Unit CC) + 1 bus route (`bus_route_terminal_loop`). The offered favour names the first unfound discoverable in set order. Photographing the district is covered by the `photographs` record (§3.5, Unit BY) — a photograph writes the photograph row and the `discovery_progress` row together, so the third example is generatable through the same favour. | GDD-04 §3.4 (`discovery_progress`); GDD-02 §4; `data/district1-blockout.json`; GDD-07 §1 |

**Common gates (all types).** The NPC must be Full or Scheduled tier (Ambient has no dialogue until promoted — GDD-15 §2) and interruptible (§2). No band gate is added: the favour topic in the shipped data conditions only on `favour_available`, and this contract does not invent a band requirement the data does not carry.

**`favour_available` evaluation.** At conversation open (§12.1 snapshot, GDD-15 §12), the runtime runs the eligibility checks for this NPC **in §3 table order** — errands, work shifts, favours, events, discovery — a deterministic priority decided by this contract. `favour_available` is true iff at least one type is eligible. The offered favour is the first eligible type in that order; there is no random pick (GDD-15 §12.6 rule 6: no randomness anywhere). One favour per conversation: the topic leads to one offer, and re-engagement re-evaluates from the then-current state — a changed world may offer a different favour next time. The player's ability to pay (for a lend-money favour) is checked at **accept** time, when the transaction validates funds — not at offer time, when the offer is only words.

**What the generator must never invent.** No new `missions.json` id; no reward outside the §3 patterns; no target entity that does not exist as a row; no deadline or expiry; no favour for an Ambient NPC; no favour whose eligibility input is a feeling the data does not hold. A generated favour that fails any of these is a generator bug, caught the same way §12.7's audit rule catches a forbidden dialogue write. *(Correction, Unit BR · Queue 13: the earlier draft of this list also barred "no lost-item favour; no discovery favour". That bar is struck: the BL/BM records exist (§3.3, §3.4) and the nodes are authored (GDD-15 §15.2), so the generator may offer both types whenever their eligibility input exists. The bar was never about the types being forbidden — it was about the missing records and nodes, both of which now exist.)*

**Shipped-data note (honest limit — corrected, Unit BR · Queue 13).** The favour topic exists in `data/dialogue-lines.json` (`dlg_topic_favour` / `dlg_topic_favour_none`, conditions `favour_available` true/false) and evaluates under this contract. *(Correction: the earlier draft of this note said no offer / accept / complete node existed in the shipped data. That was true when Unit BC wrote it (Queue 10) but went stale when Unit BO authored the flow (Queue 12, GDD-15 §15.1) and Unit BR extended it (Queue 13, §15.2). The shipped data now carries the full flow for all seven favour types — 7 offer + 7 accept + 7 complete nodes, plus the progress reminder and the shared decline node — and the accept writes `mission_progress` with the instance key while completion is verified against world state like any mission (TECH-MULTIPLAYER §4).)* **Gap G2 is resolved by this section** as a contract question — the evaluation rule and the generator's inputs now exist — and the favour flow is authored in GDD-15 §15.1–§15.2.

### 3.2 Mission Deadlines (Unit BH · Queue 11 · 2026-11-22)

**Status:** DESIGN ONLY. This section defines the deadline field AV gap G10 named: GDD-15 §4 lets an NPC lead with a time-sensitive mission (deadline within 3 days), but no mission in `data/missions.json` carries a deadline field. It adds no deadline value to any mission — the field is defined, not populated. The dialogue-side note is GDD-15 §19.

**The field.** A mission entry in `data/missions.json` may carry `deadline_days`: an optional integer, minimum 1, counting **in-game days**. Absent means the mission has no deadline — it never expires, and the NPC-lead trigger (GDD-15 §4) never fires for it. The field is optional and per-mission: most missions carry none, and a deadline is a property of the mission's fiction (a client who wants the job by a date), not of the level.

**The clock — from availability, not from acceptance.** The deadline counts from the moment the mission becomes available, not from when the player accepts it. The mission system records that moment in a fifth `progress` key, `available_at_game_minutes` (integer; written by the mission system when the row is created with `status = 'available'`). This extends GDD-15 §13.3, which defined exactly four keys (`accepted_at_game_minutes`, `objectives_complete`, `completed_at_game_minutes`, `abandoned`) — the four keys are unchanged, and this fifth key is defined here, for deadlines only, because §13's mapping has no availability timestamp and the deadline needs one.

| Quantity | Definition |
|---|---|
| `deadline_days` | In-game days from availability (field on the `missions.json` entry; absent = no deadline) |
| `available_at_game_minutes` | `progress` key; game minutes when the row was created `available` |
| `remaining` | `available_at_game_minutes + deadline_days × 1440 − now` (game minutes; 1440 minutes per in-game day) |

**The lead window — the sourced number.** An available mission with a deadline is *time-sensitive* when `0 < remaining <= 4320` game minutes — the "within 3 days" of GDD-15 §4 (3 × 1440). The window is inclusive at 3 days exactly and exclusive at 0: at `remaining = 0` the mission has expired, not become urgent. The NPC-lead check runs at conversation open (GDD-15 §12.2 step 3, after the debt and memory triggers). Accepting the mission does **not** reset the clock: the client's deadline runs from the ask, so a mission accepted with 2 days left still has 2 days left. That is the design — a deadline is the client's, not the player's acceptance anniversary.

**Expiry.** When `remaining <= 0`, the mission system sets the row to `failed` (GDD-04 §1: a mission can fail when its deadline is missed). Dialogue never writes `failed` (GDD-15 §13.4), and a failed mission has no dialogue state (GDD-15 §13.2): every `mission` condition on it is false, and no node offers, reminds, or completes it. Retry after 7 in-game days returns the row to `available` (GDD-04 §1) with a **fresh** `available_at_game_minutes` — a new deadline window, not a continuation of the expired one. Dialogue plays no part in the retry.

**What never carries a deadline.** Favours never do (GDD-04 §3.1: "A favour has no deadline and no expiry"), so the lead trigger never fires for a favour. Side missions generated from the simulation carry no deadline field either — the field is a main-mission field, and the generator must not invent one.

**Which missions carry one — three do (Unit BW · Queue 13 · 2026-11-22).** The field is now populated mission by mission. A deadline is a property of the mission's fiction — a client who wants the job by a date — so only missions with an impatient client carry one, and the number is justified from that fiction. The values are this unit's authoring decisions (labelled as such): no source gives a deadline number for any mission, and the numbers below are set here, with their reasons stated, so a later authoring pass can challenge them mission by mission. The arithmetic behind the three numbers is shared: the sim's construction stage table sums to 20 worked days (`tools/sim/construction.py` `STAGE_DAYS`: planning 1 + design approval 1 + financing 1 + construction approval 1 + foundation 3 + frame 3 + walls 2 + roof 2 + finishing 2 + works 4), and GDD-08 §2 says halted days do not count against the deadline's *worked* days but the calendar deadline keeps moving — weather is schedule risk the estimate cannot remove. A deadline must therefore clear 20 worked days with slack for storms, crew gaps, and the client's own pace.

| Mission | `deadline_days` | Fiction reason |
|---|---|---|
| 4.2 The Big Job | **30** | A flagship-loop contract with a private client (plan → estimate → supervise → payment). The full stage table is 20 worked days; the client allows 30 calendar days, leaving 10 days of storm/crew slack. The mission's own job record already carries a deadline in game days (GDD-08 §2: "budget, deadline (game days)") — this value is that record's deadline, made data. |
| 6.2 The Civic Job | **45** | A city contract (school repair, market upgrade, riverfront work) — the same 20-day stage core, but the client is the city: civic procurement and coordination run slower than a private client's, and the work must fit around the city's own calendar. 45 days is 20 worked + 25 days of civic + weather slack. The 25,000 NCr fee (the largest single credit reward in the game) marks it as the bigger job; the longer window matches. |
| 7.4 A Bridge Between | **60** | A cross-city project (both cities benefit) — the longest window in the game, because the work spans two cities: two sets of coordination, inter-city travel (mission 7.3's own fiction is a full inter-city trip), and the stage core applied across two sites. 60 days is 20 worked + 40 days of two-city coordination and travel slack. |

**Considered and rejected — missions that carry none, and why.** Most missions carry none, per §3.2. The near-misses were considered explicitly, so a later pass does not re-litigate them silently:

| Mission | Why no deadline |
|---|---|
| 2.3 The Market Run | "Buy a week's food" frames a week, but there is no client: the shopping is the player's own need, not a job with a deadline. The weekly need is a needs-engine fact, not a mission expiry. |
| 4.4 Storm Season | The storm week *is* the window — the mission is about enduring a storm week, not a client deadline. The weather sets the window, not a client. |
| 6.3 Employ Others | The mission's own duration is 30 days of payroll ("Pay them for 30 days"). A 30-day deadline would expire on the day the last payment lands — the mission would be near-impossible by construction. The 30 days is the work, not a client window. |
| 6.4 The District Festival | A festival has a date — but the festival recurs annually, and the mission system holds no festival-date input, so any number would be invented without a sourced date. The date pressure belongs to the festival event (Session 02 culture calendar), not to a mission expiry; missing this year's festival means helping next year, not failing the mission. |
| 8.1 The Application | Qualifying (Senior tier + 500,000 NCr savings + reputation 80) takes months of play; a deadline would fail a player for the time the qualification itself requires. No application date exists in the fiction. |
| All other missions (1.1–1.4, 2.1, 2.2, 2.4, 3.1–3.4, 4.1, 4.3, 5.1–5.4, 6.1, 7.1–7.3, 8.2–8.4) | Progression, relationship, savings, travel, or life-event missions with no client and no date in their fiction. A deadline on any of them would be a number without a fiction reason, which §3.2 forbids. |

**What follows from the values.** The lead window (4320 min), expiry-to-`failed`, and 7-day retry follow from §3.2 without further design — and they now have missions to fire on: the NPC-lead trigger (GDD-15 §19) can fire for 4.2, 6.2, and 7.4 while their deadlines are within 3 days. The 3-day lead window is short against a 30–60-day deadline, so the trigger fires only at the end of the window — by design (§3.2: the window is the sourced "within 3 days" of GDD-15 §4, not a proportion of the deadline). **Gap G10 is resolved by this section** as a field question *and* as a values question — the field, the clock, the window, the expiry, and the per-mission values now exist — while the mission system that enforces them remains Phase 6 work.

### 3.3 Lost-Item Record (Unit BL · Queue 12 · 2026-11-22)

**Status:** DESIGN ONLY. This section defines the record GDD-04 §3.1's find-a-lost-item row named as missing: no lost-item record existed in any merged system, so the generator could never offer the favour. The record is the deliverable — it adds no sim table, no schema change, and no sim code change; the Phase 6 generator and the sim event that creates losses implement against it. Where a number or a name would be needed and no source gives one, the section says so instead of inventing it.

**The record.** One row per lost item, in a `lost_items` store the sim adds in Phase 6 (mirrored in the Phase 9 server schema by the same shape — the table does not exist in `data/schema.sql` today, and this unit does not add it):

| Field | Type | Meaning |
|---|---|---|
| `lost_item_id` | text | Row id (`LI` + sequence, the sim's `next_id` pattern) |
| `owner_character_id` | character id | The NPC who lost it — the favour's giver |
| `item_instance_id` | UUID | The item itself: `inventory_items.item_instance_id` (`data/schema.sql`) — the row must resolve, so the item is always a thing the world already holds |
| `lost_at_game_minutes` | integer | When the loss was recorded |
| `lost_zone` | zone id | Where it was lost — one of the 10 GDD-02 §2 zones |
| `lost_anchor` | text, nullable | The anchor token where it was lost (`market`, `tea_stall`, … — GDD-06 §3), when the creating event knows it; null when it does not |
| `status` | `lost` \| `found` \| `returned` | Lifecycle below |
| `found_by_character_id` | character id, nullable | Who found it — the player, when found |
| `found_at_game_minutes` | integer, nullable | When it was found |
| `returned_at_game_minutes` | integer, nullable | When it was handed back |

**What can be lost — only what exists.** The item is identified by its `inventory_items` row, never by a name written for the favour: `item_type` is one of the schema's own vocabulary (`vehicle | furniture | tool | clothing | goods | document`) and `item_ref` is the catalogue id that row already carries. Money cannot be lost (the ledger holds money, not items); a property cannot be lost; business stock cannot be lost (it is not personal inventory). A favour never names an item with no inventory row — if the row does not exist, the loss does not exist, and the generator has nothing to offer.

**Lifecycle.** `lost → found → returned`, and nothing else. The creating event writes the row `lost` (see below). The player finding the item — a world action in the `lost_zone` (at the `lost_anchor` where one is recorded), verified against world state like any mission objective (TECH-MULTIPLAYER §4) — writes `found` with `found_by_character_id` = the player. Handing it to the owner writes `returned` and completes the favour. There is no expiry: favours have no deadline (§3.1), so a lost item stays lost until it is found. A `found` row whose favour is abandoned stays `found` with `found_by_character_id` = the player — the item is in the player's hands, and no new favour is offered for it while its status is not `lost` (the eligibility check below requires `lost`).

**How a loss is recorded — the honest limit.** No merged event writes a loss today: no sim module, life event, or schedule block records a dropped item, so no `lost_items` row exists in any live world as this section is written. The record defines the write contract for the Phase 6 event that will create losses — a commute incident, a storm-soaked market trip, a move-house event — which writes the row at the minute it happens, with `lost_zone` from the owner's `current_zone_at()` at that minute (GDD-15 §18) and `lost_anchor` from the block's anchor where the event knows it. Until such an event is wired to this record, the type is generatable *from the record* (the eligibility check below is defined) but no row exists to satisfy it — the generator must never offer a find-a-lost-item favour while the store holds no `lost` row for the giver. That is the same honesty as §3.1's "ungeneratable" row: the record removes the *design* gap; the *event* gap stays open and is named here, not filled. *(Update, Unit BX · Queue 14: the three events are now designed below — the event gap is closed as a design question; the wiring and the personal-inventory source are Phase 6 / Queue 15 work, so no row exists in a live world yet.)*

**The losing events (Unit BX · Queue 14 · 2026-11-23)**

**Status:** DESIGN ONLY. This subsection designs the three events the paragraph above named but did not specify: which merged system fires each one, how the event picks the owner and the item, and exactly which fields it writes. It adds no sim code and no sim table — the Phase 6 implementation wires these events to the `lost_items` store §3.3 defines (the store itself does not exist in the sim yet; the events write to it when Phase 6 adds it). Where a choice would need a number no source gives, the subsection says so instead of inventing one.

**The write contract — one helper, one rule.** All three events write through a single helper, `record_loss(store, owner_character_id, item_instance_id, game_minutes, lost_zone, lost_anchor=None)`, placed in a new small module `tools/sim/lost_items.py` in Phase 6 (this placement is this unit's decision: no existing module owns personal items, and the helper belongs with the record, not inside the traffic, weather, or household modules that call it). The helper writes exactly one `lost_items` row, `status = 'lost'`, with the fields of the §3.3 table, and writes nothing else. It refuses — writes no row — when its precondition fails: the owner must hold an `inventory_items` row of an eligible type for the event (see the item precondition below). A row the helper refuses is not a failed event; it is an event with nothing to lose, and the favour is not offered. No event, and no generator, may invent an item to satisfy the precondition — the §3.3 audit rule ("a row the generator invents for the sake of offering a favour is a generator bug") applies to the events too.

**The three events.** Each row names the merged system that fires it, the attribution rule that picks the owner, and the zone/anchor/item-type it writes. `lost_zone` follows §3.3 (the owner's `current_zone_at()` at the loss minute) wherever the event can compute it; where the event's own record already names the place, the table says which one wins and why.

| # | Event (trigger, in the merged system) | Owner — how the event picks one | `lost_zone` / `lost_anchor` | Item types it may lose |
|---|---|---|---|---|
| E1 | **Commute incident** — `tools/sim/safety.py` `intake_incidents` creates a `traffic_accident` incident (monthly; measured storm days × degraded segment condition; the incident's `details` carry `segment_id`, `condition`, `storm_days`). | The recorded trips for that month (`tools/sim/transport.py` `daily_pass`, `trips` table) whose `segment_ids` include the incident's `segment_id` are the travellers on that segment. Deterministic pick, labelled here: the earliest such trip in `trip_id` order; one loss per incident at most — if several travellers crossed the segment, only the first loses an item, because a pile-up of losses from one incident would be a rate this design does not own. | `lost_zone` = the trip's `destination_zone` — the loss is noticed on arrival, not mid-road (labelled decision; the incident itself carries no minute and no zone, so `current_zone_at()` at the incident's month-boundary minute would answer the home zone, which is the wrong place). `lost_anchor` = null — a road segment is not an anchor, and no anchor is invented for it. | `goods`, `document`, `tool` — things carried in a bag on a commute. Not `clothing` (worn, not carried), not `vehicle`, not `furniture` (too large to lose on a road). |
| E2 | **Storm-soaked market trip** — `tools/sim/environment.py` disaster lifecycle: a `disaster_events` row (`cyclone` / `severe_storm`) with a `disaster_impacts` row in `d1_market` (`zone_id`, `kind`). | A recorded trip with `destination_zone = d1_market`, mode in (`walk`, `cycle`, `rickshaw`) — the exposed modes (`tools/sim/transport.py` `daily_pass`; the mode vocabulary is the trip's own `mode` field) — on a day the disaster is active. Deterministic pick, labelled here: the first such trip of the day in `trip_id` order; one loss per (disaster, day) at most. | `lost_zone` = `d1_market`; `lost_anchor` = `market` — the trip's destination anchor is known, so it is recorded (the §3.3 `lost_anchor` is "the anchor token where it was lost … when the creating event knows it", and this event knows it). | `goods` only — the shopping: what a market trip carries. A storm does not lose a traveller's tools or papers; it soaks the shopping. |
| E3 | **Move-house** — `tools/sim/households.py` `move_household` (Session 02 relocation: a household moves to another vacant unit). | The household head (the mover the function already names). One loss per move at most. | `lost_zone` = the origin property's zone — the last place the item was certainly held; the move itself is transit, and transit has no zone of its own (§18.3). `lost_anchor` = null — a home is not a service anchor. | `furniture`, `tool`, `clothing`, `goods` — packed things. Not `document` (papers travel with the owner in person, not in the packed load — labelled decision) and not `vehicle` (a vehicle is moved, not packed). |

**The rate — a Phase 6 parameter, no number decided here.** Each event's *trigger* is specified exactly above, but whether a triggered event actually loses an item is a Phase 6 tuning parameter with no number decided here: no source gives a loss rate, and inventing one (a percentage, a per-trip chance) would be a tuning call this unit does not take — the same honesty as GDD-15 §16.1, where the apology reduction amount stays a runtime-rule parameter. The trigger conditions are the design; the rate is the implementation's, and it must be recorded when Phase 6 sets it. Until then, a triggered event with the parameter unset writes nothing.

**The item precondition — the open gap this design does not close.** The helper's precondition cannot be satisfied in any live world today: the sim store holds no personal inventory. There is no `inventory_items` table in `tools/sim/persistence.py` (only `business_inventory`, `medical_inventory`, and `inventory_movements`), and no sim module records what a character carries — clothing lives in `data/clothing.json` as a catalogue, never as a row owned by a character. So no event above can name a real `item_instance_id` yet, and this design does not invent one: the two candidate sources are named here without choosing between them — (i) a sim `inventory_items` table seeded from the catalogues at purchase time (which needs ownership records that do not exist today), or (ii) a ledger-note convention that lets a `purchase` row carry an `item_ref` (the ledger has no item field today). Either source is a new unit's job (Queue 15: personal-inventory record design), and until it lands the three events are specified but write nothing — the favour stays ungeneratable in live worlds, and §3.1's row stays accurate. The event gap is closed; the item gap is named, not filled. *(Update, Unit CX · Queue 15: the choice is made in the subsection below — option (i), a sim `inventory_items` table mirroring `data/schema.sql`, seeded at the purchase/issue points the sim already has (vehicle purchase sweep, creator outfits, retail allocation for transient goods); furniture/tool/document stay unseedable — no catalogue exists. The table itself is not added here; it lands with the Phase 6 wiring (Unit CY), so no row exists in a live world yet and the favour stays ungeneratable until then.)*

**What the events do not change.** The lifecycle stays `lost → found → returned` (§3.3); the eligibility check stays one `lost` row for the giver; the favour's reward stays the §3 pattern (Relationship + small credits), set at generation. The events never write a `found` or `returned` row — finding and handing back are player actions, verified against world state (§3.3). An event never writes a loss for an NPC the player has never met, and never writes two `lost` rows for the same item: a second loss of the same `item_instance_id` while a `lost` row for it stands is refused by the helper (the item is already lost; it cannot be lost twice).

**Implementation (Unit CY · Queue 15 · 2026-11-23).** The three events are wired, exactly as designed above: `tools/sim/lost_items.py` implements `record_loss()` (writes exactly one `lost_items` row, `status = 'lost'`; refuses an unknown item, another owner's item, or a second loss while one stands) plus one function per event — `commute_incident_losses()` called from `safety.intake_incidents` after each `traffic_accident` creation, `storm_market_losses()` called from `environment.daily_pass` for each active cyclone/severe_storm with a `d1_market` impact, `move_house_loss()` called from `households.move_household` after a successful move (the origin zone is read before the tenancy moves; the draw resolves from the world's stored seed because no caller of `move_household` has an rng in scope). The loss rate lives in `data/lost-items-config.json`, default 0 — specified but silent — so a live world with no tuning call behaves exactly as before this unit. Seeding lands with the wiring: `transport._purchase_sweep` writes the inventory row beside each `vehicles` insert, and `market.retail_allocation` consumes last month's goods rows and seeds the new month's per household head. Clothing rows await the creator implementation; furniture/tool/document await catalogues — their BX branches refuse until then, which is the helper working as designed. 24 tests in `tools/sim/tests/test_lost_items.py`, all passing.

*End of GDD-04 §3.3 losing events — Unit BX, Queue 14.*

**The personal-inventory record (Unit CX · Queue 15 · 2026-11-23)**

**Status:** DESIGN ONLY. This subsection answers the question BX left open — the helper's item precondition cannot be satisfied in any live world today, because the sim store holds no personal inventory. It chooses between the two candidate sources BX named, designs the record the Phase 6 implementation seeds, and says per item type where a row can come from and where it cannot. It adds no sim code and no sim table: the table lands with the Phase 6 wiring unit (Unit CY implements `record_loss()` against it), as an additive `CREATE TABLE IF NOT EXISTS` in `tools/sim/persistence.py`, following the same additive pattern as every Session 02–10 store extension. Where a choice would need a number or a catalogue no source gives, the subsection says so instead of inventing one.

**The decision — a sim table, not a ledger note.** Option (i) wins: a sim `inventory_items` table mirroring `data/schema.sql`'s table field-for-field. Option (ii) — a ledger-note convention letting a `purchase` row carry an `item_ref` — is rejected for three reasons. First, the ledger is append-only money truth (GDD-01 §8): a `purchase` row records value movement, not custody, so it cannot answer "does this character still hold this item?" after the item is lost, sold, or given away. Second, the ledger has no place for `state` (condition, fuel, odometer, slot, quantity) or `location_property_id`, both of which the record needs. Third, it would mix two concerns the project keeps apart — money traceability (every unit of money carries its `transfer_key`/`event_ref`) and custody (who holds which thing). One shape across stores is the standing rule (the sim SQLite store mirrors `schema.sql`): the sim table and the Phase 9 server table are the same record, so the Phase 9 migration is a mapping, not a redesign.

**The table — sim mirror of `schema.sql` `inventory_items`.** The server table (PostgreSQL, `data/schema.sql`) is the authority; the sim mirror is the same columns in SQLite shape:

| Field | Type (sim) | Meaning |
|---|---|---|
| `item_instance_id` | text, PK | Row id — the sim's `next_id("INV", "inventory_items", "item_instance_id")` pattern (the server keeps UUIDs; the mapping is 1:1 by column, and the two id schemes never meet in one store) |
| `item_type` | text, CHECK | One of the schema's own six: `vehicle \| furniture \| tool \| clothing \| goods \| document` |
| `item_ref` | text | Catalogue id of the item kind — must resolve to a catalogue row, the same rule §3.3 sets for `lost_items.item_instance_id` (a favour never names an item with no inventory row; an inventory row never names a kind with no catalogue row) |
| `owner_character_id` | text, NOT NULL | The character who holds it — a character, never a household (see the custody rule) |
| `location_property_id` | text, nullable | The home where it is kept, when it has one |
| `state` | text (JSON) | The per-type payload: condition, fuel, odometer, slot, quantity — the schema's `state JSONB` in sim shape |
| `acquired_at_game_minutes` | integer | When the row was created |

Index on `owner_character_id` (mirrors the schema's `idx_inventory_owner`). No status column: the row's standing *is* its status — a lost item is tracked by its `lost_items` row, not by mutating this one (see below).

**The custody rule — one row per instance, owned by a character.** A household never owns a row. Furniture in a shared home is owned by the household head with `location_property_id` = the home — the head is the owner the losing events and the favour name, and the head is the character `record_loss()` checks. A row persists for as long as the character holds the item: losing it writes a `lost_items` row and does **not** delete or mutate the inventory row (the item still exists; only its whereabouts are unknown), and finding it or handing it back likewise leaves the inventory row alone. There is no sale, gift, or disposal flow in the sim today, so no row is ever deleted by this design — when a sale/disposal flow lands, its unit must state what happens to the row (transfer, delete, or archive); this design does not pre-decide it.

**Seeding — where rows come from.** Rows are seeded only at purchase/issue points the sim already has; no seeding point is invented, and a type with no seeding point has no rows:

| `item_type` | Seeding point (existing) | Row shape at seeding |
|---|---|---|
| `vehicle` | `tools/sim/transport.py` `_purchase_sweep` — the monthly sweep that already writes a `vehicles` row and a `vehicle_purchase` ledger transfer (`store.next_id("VH", …)`, acquisition `'purchase'`) | One inventory row per purchased vehicle, in the same transaction as the `vehicles` insert: `item_ref` = the vehicle class id (`data/vehicles.json`, the sweep's `PRICE_TO_TYPE` value), `state` = `{vehicle_id, odometer_km, condition, fuel_litres}` — the state JSON carries the link to the operational `vehicles` row, which stays the operational registry; this row is the custody record. Rented cabs are **not** rows: a rented cab is not owned (the settlement rents it by design), so the driver holds no inventory row for it. Taxi drivers never buy (the sweep skips them), so no driver ever holds a vehicle row by this route. |
| `clothing` | The creator's starting outfits (GDD-09 §5) — the player character's three outfits (work/casual/formal) and each Scheduled NPC's work + casual, charged at creation through the ledger `purchase` row the creator already writes; uniforms issued at hiring (`data/clothing.json` `profession_uniforms`) | One row per garment: `item_ref` = the `clothing.json` id (31 items, `price_ref` → `prices.json` `clothing`), `state` = `{slot, outfit_context, issued: "creator" \| "employer" \| "household"}`. A uniform replacement (charged at catalogue price per GDD-09 §5) writes a new row; the replaced garment's row is left standing — retiring it is part of the future disposal rule, not decided here. |
| `goods` | `tools/sim/market.py` `retail_allocation` — the monthly retail pass that already writes `household_consumption` | **Transient carried quantities only.** `item_ref` = the `economy-goods.json` good id (6 goods), `state` = `{quantity, unit}`. The row is created when the household's allocation is written and stands for exactly the month it was bought: the next month's allocation consumes (deletes) the previous month's rows before seeding the new month's — a goods row never stands for two months. The buyer is the household head (the custody rule). This transience is the only way BX's E2 ("goods only — the shopping") can ever be satisfied: the shopping on the trip home is a standing goods row; last month's shopping is not. |
| `furniture` | **None — unseedable.** No furniture catalogue and no furniture price table exist (`prices.json` carries no furniture key; GDD-10's furniture tiers are rent-table tiers, not a catalogue) | No row can be seeded, so BX's E3 furniture branch cannot fire until a catalogue unit gives furniture a catalogue and a purchase point. Recorded, not filled. |
| `tool` | **None — unseedable.** No tool catalogue exists (construction materials in `prices.json` are materials, not tools) | No row can be seeded, so BX's E1/E3 tool branches cannot fire until a catalogue unit gives tools a catalogue and a purchase point. Recorded, not filled. |
| `document` | **None — unseedable.** No document catalogue exists (Session 06 certifications are records in `academics.py`, not items) | No row can be seeded, so BX's E1 document branch cannot fire until a catalogue unit defines what a losable document is. Recorded, not filled. |

**What follows for the losing events.** With this record, the BX precondition becomes satisfiable in exactly the cases the table above allows: E1 (commute incident) can lose a standing `goods` row; E2 (storm-soaked market trip) can lose a standing `goods` row; E3 (move-house) can lose a standing `goods` or `clothing` row. The `furniture`/`tool`/`document` branches of E1/E3 stay dead until their catalogues land — the events are specified for all three types, but the precondition refuses where no row stands, which is the helper working as designed, not a gap in the events. No BX event ever loses a `vehicle` (BX excludes it from all three events, and the custody record exists for future events, not for these). The loss rate stays a Phase 6 parameter with no number decided (BX; Queue 15 sets it in config, default 0 — Unit CY).

**What the record does not do.** It does not price anything (prices stay in `prices.json`; `item_ref` only points). It does not change the ledger (a purchase still writes its existing `purchase` row; the inventory row is a second write in the same transaction, not a money record). It does not invent ownership for the starter population: the population builder seeds no inventory rows today, and whether starter outfits carry a ledger `purchase` row at build time is the seeding unit's decision — this design requires only that every row's `item_ref` resolves and its `acquired_at_game_minutes` is recorded. Until a seeding unit lands, no row exists in any live world, and the find-a-lost-item favour stays ungeneratable — §3.1's row stays accurate.

*End of GDD-04 §3.3 personal-inventory record — Unit CX, Queue 15.*

**Eligibility — the generator's check.** The type is eligible for an NPC iff a `lost_items` row exists with `owner_character_id` = the NPC and `status = 'lost'`. The offered favour's parameters are the row itself: `item_instance_id` (what), `lost_zone` (+ `lost_anchor` where set — where to look). The reward is the §3 pattern for the type — Relationship + small credits — set at generation inside the pattern and recorded on the instance, never stated as an amount in dialogue (amounts live in the ledger; GDD-15 §12.4). Completion is the `returned` write: the mission system sets `progress.objectives_complete` on the favour instance row when the hand-back is verified, and the dialogue complete node pays the recorded reward.

**What the generator must never invent.** No item without an inventory row; no loss with no creating event (a row the generator invents for the sake of offering a favour is a generator bug, caught the same way §12.7's audit rule catches a forbidden dialogue write); no `lost_zone` outside the 10 GDD-02 zones; no expiry; no second favour for an item whose status is not `lost`.

**§3.1 status change.** The §3.1 find-a-lost-item row now reads as defined, not ungeneratable — the record, the lifecycle, and the eligibility check exist in this section. The favour offer/accept/complete nodes for the type are authored in GDD-15 §15.2 (Unit BR, Queue 13) — the follow-up this section anticipated is done, and the generator may offer the type whenever a `lost` row exists for the giver.

### 3.4 Discovery Progress Record (Unit BM · Queue 12 · 2026-11-22)

**Status:** DESIGN ONLY. This section defines the record GDD-04 §3.1's discovery row named as missing: the landmarks and the bus routes existed, but no table recorded which the player had found or ridden, so the generator could not tell a found landmark from an unfound one. The record is the deliverable — it adds no sim table, no schema change, and no sim code change; the Phase 6 generator and the visit/ride detection implement against it.

**The record.** One row per discovered thing, in a `discovery_progress` store the sim adds in Phase 6 (mirrored in the Phase 9 server schema by the same shape — the table does not exist in `data/schema.sql` today, and this unit does not add it):

| Field | Type | Meaning |
|---|---|---|
| `account_id` | UUID | Whose progress — `accounts.account_id` (`data/schema.sql`) |
| `discoverable_type` | `landmark` \| `bus_route` | Which kind of thing |
| `discoverable_id` | text | The landmark id (`lm_*`, below) or the route id (`bus_route_terminal_loop`, below) |
| `discovered_at_game_minutes` | integer | When it was found or ridden |
| `discovered_in_zone` | zone id | The zone the player was in when the row was written (audit, not a condition) |
| PK `(account_id, discoverable_type, discoverable_id)` | — | One row per account per thing, ever |

**Where it lives — account, not character.** Achievements are account-level (GDD-04 §5: a character dies, the account keeps the achievements), and discovery progress feeds the Explorer achievement progress, so it lives on the account too. **Recorded discrepancy:** `data/schema.sql`'s `achievements` table is keyed by `character_id`, not `account_id` — the schema and §5 disagree about where achievement data lives. This record follows §5 (account); aligning the `achievements` table's key is a Phase 9 schema question, not decided here. Rows are append-only: a discovery is never deleted, and a new character on the same account inherits the progress — the player does not re-find the Clock Tower because they started a new life.

**The discoverable set — landmarks.** The District 1 landmarks — exactly the 8 GDD-02 §4 lists, with the ids `data/district1-blockout.json` carries and the zone each one stands in — plus the District 2 landmarks Unit CC adds below (6, all PROPOSED, with the ids `data/district2-blockout.json` carries) and the Shibnagar landmarks Unit CZ adds below (5, with the ids `data/city2-shibnagar.json` carries). The set holds **19 landmarks + 1 bus route**.

| `discoverable_id` | Landmark (GDD-02 §4) | Zone | Zone provenance |
|---|---|---|---|
| `lm_clock_tower` | The Clock Tower (§4.1) | `d1_market` | Assigned by description — the arterial crossing at the market's north edge; the point (0, −60) falls outside every `zone_boxes_m` box, so the box cannot verify it (decided here, labelled) |
| `lm_bridge_approach` | Rupsha Bridge approach (§4.2) | `d1_riverfront` | Assigned by description — the south-east river edge; the point (500, 430) falls outside every box (decided here, labelled) |
| `lm_launch_terminal` | Launch Terminal (§4.3) | `d1_riverfront` | Verified — inside the `d1_riverfront` box; building `b_d1_riverfront_launch_terminal` |
| `lm_park_pond` | Central Park pond & banyan tree (§4.4) | `d1_park` | Verified — inside the `d1_park` box |
| `lm_market_hall` | Boro Bazar market hall (§4.5) | `d1_market` | Verified — inside the `d1_market` box; building `b_d1_market_hall_units` |
| `lm_rooftop_tower` | Uptown rooftop restaurant tower (§4.6) | `d1_uptown` | Verified — inside the `d1_uptown` box; building `b_d1_uptown_rooftop_restaurant` |
| `lm_station` | Railway station clock frontage (§4.7) | `d1_transport` | Verified — inside the `d1_transport` box; building `b_d1_transport_station` |
| `lm_water_tank` | The old water tank (§4.8) | `d1_oldtown` | Verified — inside the `d1_oldtown` box |

**District 2 landmarks (Unit CC · Queue 14 · 2026-11-23).** The 6 landmarks `data/district2-blockout.json` carries (TECH-DISTRICT2-BLOCKOUT, Unit AR) join the set in file order. Every one is PROPOSED — District 2 itself is PROPOSED (Phase 8, owner confirms/revises) — and the set carries that label with them: a PROPOSED discoverable is offered like any other (the favour names the first unfound discoverable in set order, and District 1's entries come first), and the label retires when the owner confirms District 2. Zones are verified against the District 2 `zone_boxes_m` exactly as the District 1 zones were, with the same assigned-by-description rule for a point outside every box:

| `discoverable_id` | Landmark (district2-blockout) | Zone | Zone provenance |
|---|---|---|---|
| `d2_lm_northgate_tower` | Northgate Tower | `d2_market` | Assigned by description — the arterial crossing at the market's north edge (the District 2 mirror of the Clock Tower decision); the point (0, −1080) falls outside every `zone_boxes_m` box, so the box cannot verify it (decided here, labelled) |
| `d2_lm_north_bazar_hall` | North Bazar hall | `d2_market` | Verified — inside the `d2_market` box |
| `d2_lm_maidan_pavilion` | Maidan pavilion | `d2_maidan` | Verified — inside the `d2_maidan` box |
| `d2_lm_garden_tank` | Garden Suburb water tank | `d2_garden` | Verified — inside the `d2_garden` box |
| `d2_lm_north_gate_depot` | North Gate depot frontage | `d2_transport` | Verified — inside the `d2_transport` box |
| `d2_lm_north_heights_view` | North Heights viewpoint | `d2_uptown` | Verified — inside the `d2_uptown` box |

**Shibnagar — nothing joins (Unit CC · Queue 14).** `data/city2-shibnagar.json` carries no `landmarks` array at all: the town's named properties (Shibnagar Ferry Ghat, Shibnagar Bus Stand, Riverside Tea Stall, Bazar Tea Stall, Shibnagar Primary School, Shibnagar Clinic, Shibnagar Town Office) are properties, not landmarks, and no landmark ids exist for them in any merged source. No Shibnagar discoverable is invented for this set: the Ferry Ghat and the Bus Stand are recorded here as the obvious candidates for a future landmark-authoring unit, not as members. Until such a unit authors Shibnagar landmarks with ids and zones, the town contributes zero discoverables and the discovery favour never names a Shibnagar place. *(Update, Unit CZ · Queue 15: that unit has now landed — the 5 landmarks below join the set, and this paragraph stays as the record of what was true before it.)*

**Shibnagar landmarks (Unit CZ · Queue 15 · 2026-11-23).** The 5 landmarks `data/city2-shibnagar.json` now carries join the set in file order. They are authored here, not generated: the file is GENERATED (citygen.py), so the landmark table lives in the generator (`tools/sim/citygen.py` `_LANDMARKS`) and the file is regenerated from it — a hand edit to the JSON alone would be dropped by the next regeneration, and the byte-identical regeneration test (`tools/sim/tests/test_cities.py`) guards the committed file. Each landmark's point is its building's plot anchor, derived by the generator's own plot packing — never a hand-placed coordinate — so the point always falls inside the building's own zone box, and the zone is verified by point-in-box exactly as the District 1 zones were (no assigned-by-description entry: every Shibnagar point is inside a box). The landmarks carry **no PROPOSED label**: District 2's are PROPOSED because District 2 itself is unconfirmed, but Shibnagar Town already runs in the sim — its properties are real rows — so its landmarks inherit the town's GENERATED status, not a proposal flag.

Which properties qualify follows the District 1 precedent: a landmark is a civic/transport node a player can be directed to and recognise. The two transport nodes (the ferry ghat is the town's river crossing, the bus stand its road terminal — the District 1 analogues are the launch terminal and the station) and the three civic institutions (school, clinic, town office — unique, named, public) qualify. The two tea stalls do not: in District 1 a tea stall is a service anchor (GDD-06 §3), not a landmark. The fish stalls, bazar shops, godown, warehouse, farmland and housing do not qualify either: a shop row, generic retail, industrial and residential stock are not landmarks — and the fish stalls were not among Unit CC's named candidates in the first place.

| `discoverable_id` | Landmark (`city2-shibnagar.json`) | Zone | Zone provenance |
|---|---|---|---|
| `c2_lm_ferry_ghat` | Shibnagar Ferry Ghat | `c2_transport` | Verified — point (78, 48) inside the `c2_transport` box; building `b_c2_transport_ghat` |
| `c2_lm_bus_stand` | Shibnagar Bus Stand | `c2_transport` | Verified — point (141, 48) inside the `c2_transport` box; building `b_c2_transport_bus_stand` |
| `c2_lm_primary_school` | Shibnagar Primary School | `c2_civic` | Verified — point (366, 294) inside the `c2_civic` box; building `b_c2_civic_school` |
| `c2_lm_clinic` | Shibnagar Clinic | `c2_civic` | Verified — point (407, 290) inside the `c2_civic` box; building `b_c2_civic_clinic` |
| `c2_lm_town_office` | Shibnagar Town Office | `c2_civic` | Verified — point (445, 290) inside the `c2_civic` box; building `b_c2_civic_office` |

**The discoverable set — bus routes.** No named bus route exists in any merged source: GDD-07 §1 runs buses on "fixed terminal loops" and `data/vehicles.json` describes the bus as "fixed loops between the `d1_transport` bus terminal and the district edge", but no route id, no stop list, and no route count is given anywhere. **Decided here (labelled as this unit's decision):** the route set holds exactly one route — `bus_route_terminal_loop`, the terminal ↔ district-edge loop the two sources describe — until Phase 5 authors named routes, when the set gains an entry per route. The id is this unit's; the route is the sources'. A route the traffic system has not authored is not in the set, and the generator never offers it.

**How a discovery is recorded.** A landmark row is written when the player character is present in the landmark's zone — zone presence, checked against the player's current zone (GDD-15 §18's accessor, read for the player): the zone is the landmark's own small ground, and presence in it is the visit. A bus-route row is written when the player completes a ride on that route — boards at the `d1_transport` terminal and alights at the district edge (the ride is a trip the transport system records; the route id is the bus's route). Both writes are made by the world systems that observe them, never by dialogue and never by the generator: the generator reads the record, it does not write it.

**Eligibility — the generator's check.** The type is eligible for an NPC iff at least one discoverable in the set has no `discovery_progress` row for the player's account. The offered favour names one unfound discoverable — the first in set order (District 1 landmarks in GDD-02 §4 order, then District 2 landmarks in `district2-blockout.json` order, then Shibnagar landmarks in `city2-shibnagar.json` order, then routes), deterministic, no random pick (GDD-15 §12.6 rule 6). The favour's parameters are `discoverable_type` + `discoverable_id`. Completion is the row appearing: the mission system sets `progress.objectives_complete` on the favour instance row when the discovery is recorded, and the dialogue complete node pays the recorded reward — 500 NCr each + Explorer progress, the §3 pattern verbatim.

**What this record does not cover.** The §3 discovery examples list three things — "Find all landmarks, photograph the district, ride every bus route" — and this record covers two of them. Photographing is now covered by its own record, GDD-04 §3.5 (Unit BY, Queue 14): a photograph writes the `photographs` row *and* the `discovery_progress` row for the landmark, so the third example is generatable through the same favour. The record covers District 1, District 2, and Shibnagar (Unit CZ, Queue 15, above) — all 19 landmarks and the one route. *(Update, Unit CZ · Queue 15: the "Shibnagar is still not covered" line is retired by the 5 landmarks above; the town's discoverables join the set in file order after District 2's.)*

**§3.1 status change.** The §3.1 discovery row now reads as defined, not ungeneratable — the record, the set, and the eligibility check exist in this section. The favour offer/accept/complete nodes for the type are authored in GDD-15 §15.2 (Unit BR, Queue 13) — the follow-up this section anticipated is done, and the generator may offer the type whenever an unfound discoverable exists for the player's account.

### 3.5 Photograph Record (Unit BY · Queue 14 · 2026-11-23)

**Status:** DESIGN ONLY. This section defines the record the §3.4 "What this record does not cover" paragraph named as missing: the third discovery example — "photograph the district" — had no photo mechanic and no photograph table anywhere in the merged sources. The record is the deliverable — it adds no sim table, no schema change, and no sim code change; the Phase 6 photo mode and the visit detection implement against it. Where a number or a rule would be needed and no source gives one, the section says so instead of inventing it.

**The record.** One row per photograph, in a `photographs` store the sim adds in Phase 6 (mirrored in the Phase 9 server schema by the same shape — the table does not exist in `data/schema.sql` today, and this unit does not add it):

| Field | Type | Meaning |
|---|---|---|
| `photograph_id` | text | Row id (`PH` + sequence, the sim's `next_id` pattern) |
| `account_id` | UUID | Whose photograph — `accounts.account_id` (`data/schema.sql`) |
| `character_id` | character id | The player character who took it (the photographer; a photograph is taken by a character, on an account) |
| `discoverable_id` | text | The landmark photographed — a `landmark`-type discoverable from the §3.4 set (`lm_*`, `d2_lm_*` when §3.4 grows) |
| `taken_at_game_minutes` | integer | When it was taken |
| `taken_in_zone` | zone id | The zone the player was in when the row was written (audit, not a condition — the same field shape as §3.4) |
| PK `(account_id, discoverable_id)` | — | One photograph per account per landmark, ever |

**Where it lives — account, like discovery progress.** The photograph is progress toward the Explorer achievement, so it lives on the account like `discovery_progress` (§3.4) and the achievements themselves (§5.1, account wins): a new character on the same account inherits the photographs — the player does not re-photograph the Clock Tower because they started a new life. Rows are append-only: a photograph is never deleted.

**The gate — photo mode is the mission 1.4 unlock.** The player can take photographs only after completing mission 1.4, "The River at Dusk" (GDD-04 §2: the mission's unlock is "Promenade leisure anchor, photo mode"). That unlock is the sourced gate — no new gating rule is invented here, and the mechanic does not exist before the mission is complete. A photograph attempt before 1.4 completes is refused by the photo mode itself, not by the favour system: the generator never offers a photograph-variant favour to a player who cannot take one, because the eligibility check below requires the unlock.

**How a photograph is taken — and what it writes.** A photograph is taken of a landmark while the player is present in that landmark's zone — the same presence rule §3.4 uses for a visit (zone presence, checked against the player's current zone, GDD-15 §18's accessor read for the player). Taking the photograph writes **two** rows, in one transaction: the `photographs` row for the landmark, and the `discovery_progress` row for the same landmark. A photograph is a visit with evidence — the presence rule is satisfied by the act of photographing, so the discovery is recorded by the same write. This keeps one progress record: there is no separate "photographed" progress, and the favour completes through the discovery row it already completes through (§15.2). The two writes are one transaction so a photograph never exists without its discovery, and a discovery by photograph never exists without its photograph.

**Which discoverables can be photographed — landmarks only.** The record covers every `landmark`-type discoverable in the §3.4 set: the 8 District 1 landmarks today, and the District 2 landmarks when Unit CC adds them to the set — the record is written against the set, not against a fixed list, so no BY change is needed when the set grows. *(Update, Unit DA · Queue 15: the set has now grown to 19 landmarks — 8 District 1 + 6 District 2 (Unit CC) + 5 Shibnagar (Unit CZ) — and, as designed here, no record change was needed: the mechanic reads the set from the three landmark files.)* The bus route cannot be photographed: a route is ridden, not photographed — it has no visual subject and no zone to stand in while taking it, so the route stays a ride-only discoverable and its row is written only by completing the ride (§3.4). A photograph of a landmark the player has already discovered writes nothing new: the PK refuses the duplicate, and the act is a re-photograph of a found landmark, not a discovery.

**Eligibility — the generator's check.** The discovery favour's eligibility is unchanged (§3.1/§3.4): the type is eligible iff at least one discoverable in the set has no `discovery_progress` row for the player's account, and the offered favour names the first unfound discoverable in set order. The photograph changes *how* the favour can complete, not *whether* it is offered: a player who has completed mission 1.4 may complete the offered favour by photographing the named landmark (writing both rows) instead of by visiting it (writing the discovery row alone). The favour's parameters are unchanged (`discoverable_type` + `discoverable_id`); the complete node pays the recorded reward — 500 NCr each + Explorer progress, the §3 pattern verbatim — whichever path wrote the row. No new dialogue node is authored for the photograph variant: the BR nodes (GDD-15 §15.2) already offer, accept, and complete the discovery type, and the offer line names the discoverable through `<discoverable_name>` — the player chooses at the landmark whether to visit or to photograph it, and the world records whichever happened.

**Implementation (Unit DA · Queue 15 · 2026-11-23).** The mechanic is implemented in `tools/sim/photographs.py`: `take_photograph()` refuses a non-landmark discoverable (a bus route is ridden, not photographed), a locked photo mode, a wrong zone, and a duplicate (an existing `photographs` row or an existing `discovery_progress` row for the account), and otherwise writes both rows in one transaction. The set is read from the data — `data.blockout` + `data.district2_blockout` (new loader in `tools/sim/dataio.py`; the sim did not load the District 2 file before this unit) + `data.city2_file` — with each landmark's zone from its point inside its zone box, except the three §3.4 assigned-by-description entries (Clock Tower, Bridge Approach, Northgate Tower), carried as an explicit override table. The gate reads the sim's `mission_progress` mirror of `data/schema.sql` (a `('1.4', 'completed')` row for the character); the mission system that writes that row is Phase 6 work, so in a live world with no mission system yet the gate stays closed and photographs are refused — the mechanic exists, the unlock path does not yet. `account_id` is the caller's Phase 9 id, opaque here: the sim has no `accounts` table. The tables (`photographs`, `discovery_progress`, `mission_progress`) are additive in `tools/sim/persistence.py`. 12 tests in `tools/sim/tests/test_photographs.py`, all passing, including the full 19-landmark zone mapping against §3.4.

**What this record does not cover.** The row is the record of the *act* of photographing, not the image: no image bytes, no camera roll, and no photo storage are designed here — the UE photo mode holds the image in the save file, and the sim records only the fact that the photograph was taken (the same split as §3.4's `discovered_in_zone`: audit, not content). Photographing a person is not covered: the record covers discoverables only, and a photograph of an NPC writes no row — portrait photography has no discovery, no favour, and no achievement attached to it anywhere in the merged sources. No cost is defined for taking a photograph: no source prices photography, film, or developing, so the act charges nothing — the mechanic is free at the point of use, and a price is not invented to give it one. No camera roll limit is set: no source gives one, and the PK (one row per account per landmark) bounds the table at the size of the discoverable set.

**§3.1 status change.** The §3.1 discovery row now reads as fully defined: all three examples — find all landmarks, photograph the district, ride every bus route — are generatable through the §3.4 set and this record. The "photograph stays ungeneratable" note in §3.4 and in GDD-15 §15.2 is retired by this section; the favour needs no new node, because the BR nodes already cover the type.

*End of GDD-04 §3.5 — Unit BY, Queue 14.*

## 4. Free-Roam Rules

1. **The whole district is open from Level 1.** No area is locked behind a level; levels unlock *tools, contracts and systems*, not geography. A Level 1 player can walk the riverfront, enter the market, and ride to the edge of District 1.
2. **No mission is timed in real time.** In-game deadlines exist (a client wants the job in 12 days) and are shown in in-game days; the player can pause, sleep, and plan. Missing a deadline fails that mission, never the game.
3. **Crime has consequences, not a fail state.** Theft, assault, and fraud are possible choices with police, fines, reputation and jail-time responses (the police profession exists in the world for a reason) — and a record the player lives with. The game never says "you lose".
4. **Money earned free-roam counts everywhere.** A player who ignores missions and runs a taxi for 60 days has the same 36,000/month senior income as a mission player — the economy does not punish free play (GDD-03 §8).
5. **The player can always go home.** The home anchor, sleep, and time-skip are available from Level 1, in every level, in every city.

## 5. Achievements v1 (account-level — they survive character death, GDD-01 §1)

| Achievement | How | Tier |
|---|---|---|
| First Night in Rupsha | Sleep one night in District 1 | Bronze |
| Payday | Receive your first wage | Bronze |
| Neighbourhood Hero | 5 neighbours at relationship 40+ | Bronze |
| Saver | Hold 100,000 NCr at once | Silver |
| Homeowner | Own any property | Silver |
| Master Craftsman | Reach Senior tier in any profession | Silver |
| Business Owner | Own a business with 3+ employees | Silver |
| Storm Rider | Work 7 storm days without missing a shift | Silver |
| Family Man / Family Woman | Three generations alive in your family tree | Gold |
| City Father / City Mother | City reputation 80+ | Gold |
| Millionaire | Net worth 1,000,000 NCr | Gold |
| Space Explorer | Complete Level 8 | Gold |
| Living Legend | Net worth 2,000,000 NCr + reputation 90 + 3 generations | Platinum |

Achievement data lives on the **account** (GDD-01 §1): a character dies, the account keeps the achievements, and the next character inherits the record — not the money.

### 5.1 Achievement keying — the account wins (Unit BT · Queue 13 · 2026-11-22)

**Status:** DESIGN ONLY. This section resolves the discrepancy Unit BM recorded in §3.4: `data/schema.sql`'s `achievements` table is keyed by `character_id`, but this section (§5) says achievement data lives on the account. It adds no DDL to `schema.sql` — the decision and the migration note are the deliverable, and the migration itself is Phase 9 work.

**The decision: the account wins.** Achievement data is account-level, per §5 and per GDD-01 §1 ("Account-level data (achievements, friends, settings) survives character death; character-level data (money, property, relationships) passes through inheritance (§6.4) or ends"). The schema's `character_id` key is the error, not the rule: it would strand a dead character's achievements on a row no living character can read, and it contradicts the sentence directly above the table in this same section. The `discovery_progress` record (§3.4) already follows the account rule — it is keyed by `account_id` — so the account decision also makes the two achievement-adjacent records consistent: the Explorer achievement's progress reads `discovery_progress` by `account_id`, and the achievement itself is unlocked on the same key.

**The migration consequence (Phase 9, forward-only — GDD-01 §9/§10, TECH-PERSISTENT-WORLD Appendix B pattern).** The migration is a re-key of the `achievements` table, in numbered steps, with no down-migration:

1. `ALTER TABLE achievements ADD COLUMN account_id UUID REFERENCES accounts(account_id);`
2. Backfill: `UPDATE achievements a SET account_id = c.account_id FROM characters c WHERE a.character_id = c.character_id;` — every character row carries its `account_id` (`schema.sql`: `characters.account_id`, NULL for NPCs).
3. Re-key: drop the `(character_id, achievement_id)` primary key and add `PRIMARY KEY (account_id, achievement_id)`.
4. Keep the `character_id` column (nullable, no longer the key) for one migration cycle as the audit trail of which character unlocked the achievement, then drop it in a later forward migration once the server has run a full cycle on the account key — never in the same migration that re-keys, so a bad backfill is visible before the old key is gone.

**No live rows exist to migrate.** Neither store holds an `achievements` row today: the headless sim has no achievements table at all (`tools/sim/` writes none — achievements are a player/account feature with no sim implementation yet), and `data/schema.sql` is the Phase 9 server draft, un-deployed. The backfill step therefore migrates zero rows in any live world; it exists so the migration is correct for a deployed Phase 9 database that has accumulated character-keyed rows by then. If such rows exist and a character's `account_id` is NULL (an NPC row — achievements are a player concept, GDD-04 §5's table lists player achievements and no NPC achievement is defined anywhere), the migration counts them in its note and does not backfill them: a NULL `account_id` cannot join the new primary key, and an NPC achievement row is out-of-scope data, not a record to preserve under a character key. The count is stated in the migration note; nothing is silently dropped.

**What happens to `discovery_progress` under the decision.** Nothing changes: §3.4 already keys it by `account_id`, and this decision confirms that keying rather than revisiting it. The two records now agree — an account's Explorer progress and its achievements are read by the same key, and a new character on the same account inherits both without re-finding the Clock Tower or re-earning First Night in Rupsha.

**What does not change.** The achievement list, the tiers, and the unlock rules in §5 are untouched — only the key moves. The `account_friendships` table (`schema.sql`) is already account-keyed and needs no change. The sim gains no achievements table from this unit: the achievement system itself (unlock detection, UI) is Phase 6 work, and this decision only fixes which key it will read when it is built.

*End of GDD-04 §5.1 — Unit BT, Queue 13.*

## 6. What This Document Deliberately Does Not Decide

- Exact dialogue and cutscene content for each mission → written during Phase 5/6 implementation, from this structure.
- The Level 2–7 names → proposed here; owner confirms or renames (see header note).
- Multiplayer missions (co-op jobs, shared businesses) → Phase 9; the mission shape (objectives, rewards, unlocks) is reused, the party rules are new.

*End of GDD-04 v1.0. Changes happen by PR; level-name changes are a one-line edit each, not a redesign.*
