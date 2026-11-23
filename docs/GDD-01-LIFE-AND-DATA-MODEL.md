# NEXORA — GDD-01: Life Simulation & Player Data Model

**Unit B · Version 1.0 · 2026-11-20**
**Parent document:** `NEXORA-MIGRATION-PLAN.md` — Part C subsystems #8 (NPC AI), #9 (life stages), #10 (family/relationships), #14 (persistence); Part D Phases 5–7 and 9.
**Companion file:** `data/schema.sql` — the PostgreSQL draft that implements this model. Every table in the schema carries a comment tying it back to a section of this document.

> **Design law for everything below:** one data model from the first single-player build to the Phase 9 multiplayer server. Single-player phases serialise this same model into save files; Phase 9 moves the *same* tables behind a server that is the only writer of currency and property (master plan Phase 9 security rule). No phase may invent a parallel model "to be migrated later" — that migration never happens cleanly, so it is banned by design.

---

## 1. Player Profile — the owner's example, made canonical

The owner's spec gives this example character card. It is the canonical shape of a NEXORA player profile:

```
Name:          Zobaer Hasan
Username:      @zobaerio
Profession:    Civil Engineer
Residence:     Nexora Central City
Economic Class: Middle Class
Balance:       25,000 Nexora Credits
```

Field-by-field mapping to the model:

| Card field | Model field | Notes |
|---|---|---|
| Name | `characters.display_name` | The character's in-world name; may differ from the account's real name. |
| Username | `accounts.username` (unique, `@` is display-only) | Account-level, never changes with the character's life events. One account → many characters over time (a character dies; the account and its achievements persist). |
| Profession | `employments` (current row) + `characters.profession_id` (primary) | A character has one *primary* profession and a history of employments. Profession data lives in `data/professions.json` (Unit C). |
| Residence | `characters.residence_city` + the household's property | "Residence" on the card is a *city*; the actual home is a property owned/rented by the character's household (§5). |
| Economic Class | `characters.economic_class` — a **derived label**, never a stored truth | Computed from net worth + income band (§7). It is a game system describing starting conditions and opportunities — per the owner's framing, never a statement about a real person's worth. |
| Balance | `economy_ledger` balance (cached on `characters.balance_cached`) | Balance is *derived from the ledger* (§8). The cached value is a performance copy; the ledger is the truth. |
| (not on card) Profile picture / avatar | `characters.avatar_ref` | Points at the MetaHuman configuration (Phase 2) — face/body parameters, not a photo upload, for player characters. NPCs may use portrait assets. |
| (not on card) Age | derived from `characters.born_at_game_time` + world clock | Age is computed, never typed in and edited (§3). |

**Account vs character:** the *account* is the real person's login (Phase 9: EOS-backed). The *character* is a life lived inside NEXORA — born (created), educated, employed, housed, related, and eventually deceased. Account-level data (achievements, friends, settings) survives character death; character-level data (money, property, relationships) passes through inheritance (§6.4) or ends.

## 2. Character Identity Model

Every character — player or NPC — has the same core record. NPC tiers (master plan Part C #8) differ in *how much of this record is simulated*, never in its shape:

| Tier | Who | Simulation depth |
|---|---|---|
| **Full** | Players + ~25 named NPCs per district (Phase 6) | Everything in this document: personality, goals, memories, relationships, ledger. |
| **Scheduled** | District residents with homes and jobs | Identity, household, profession, schedule, property; simplified goals; no long-term memory beyond relationship scores. |
| **Ambient** | Mass-framework crowds | Name + appearance + current activity only; a lightweight row (or no row — generated from templates) until an interaction promotes them to Scheduled. |

### 2.1 Identity fields

- **Core:** display name, sex, born-at game timestamp, life stage (derived, §3), home city, household.
- **Appearance reference:** MetaHuman parameter set id (adults) or stage-variant asset id (child/teen/elder — master plan Part C #9 limitation applies: stage variants are authored assets, not aged MetaHumans).
- **Personality:** five trait scores 0–100 — *ambition, sociability, discipline, kindness, risk_tolerance* — set at creation (player: chosen + a few questions; NPC: rolled from profession/city templates), drifting slowly with life events (a business failure lowers risk_tolerance; it never jumps). Traits are *inputs to behaviour weighting* (State Tree utility scoring), not dialogue decoration.
- **Skills:** per-skill level 0–100 + experience, in `character_skills` (e.g. engineering, driving, cooking, trading). Skills gate profession tiers and mission quality; they grow by doing, decay slowly when unused.
- **Reputation:** per-district and per-profession scores, earned from completed work and social events; gates better jobs and credit.

### 2.2 Goals

A character's **goal stack** (max 3 active, stored in `character_goals`):

- **Life goal** (1, long): e.g. "Own a construction company", "Become chief surgeon", "Own a house in the riverfront district". Chosen at young-adult stage; drives the mission suggestions the game offers.
- **Stage goals** (up to 2, medium): e.g. "Save 50,000 credits", "Reach Engineering skill 40", "Marry". Completing one pays out in reputation + a trait nudge and proposes the next.
- **Needs-driven wants** (transient, NPCs mainly): generated from needs (rest, food, income pressure) — these make schedules bend believably instead of running like clockwork.

Goals are data, not scripts: the mission system (Unit G) reads goal types and offers matching work. A goal the player ignores simply stays; NEXORA never fails a player for living differently.

### 2.3 Memory

Two kinds, deliberately separated because they cost differently:

- **Semantic memory** (facts): relationship scores, "X employs me", "Y owes me money", flags like `met_player`, `worked_with_player`, stored on the relationship/employment rows themselves. Cheap, permanent, used by dialogue and AI decisions.
- **Episodic memory** (events): notable events appended to `character_memories` — *first job, wedding, business opened, accident, inheritance, helped/harmed by player* — each with game timestamp, type, other-party id, and an emotional weight −100..100. Full-tier characters only; capped (e.g. 200 rows, oldest low-weight events forgotten first). Dialogue and goal generation read the top-weighted recent episodes. This is what "NPCs remember you" means in Phase 6's exit criteria — concrete rows, not a promise.

## 3. Life Stages & Transitions

Time base: the world clock (Unit E). Default life-sim speed is a *design setting*, not a constant: accelerated simulation (Phase 6/7 exit tests) runs the same rules at higher speed. One in-game day = one simulation day at any speed.

| Stage | Age band | Key systems active |
|---|---|---|
| Infant | 0–2 | Household-dependent only; no independent simulation. |
| Child | 3–12 | School attendance (household's district school), skill seeds, family relationships form. **Asset gate:** needs child character assets (master plan Part C #9) — until solved, children exist in data and household simulation but are not rendered as full 3D characters; the plan says so rather than faking it. |
| Teen | 13–17 | School + part-time work, trait formation events, profession interests. |
| Young Adult | 18–29 | Profession choice, first employment, leaving the parental household becomes possible, life goal chosen. |
| Adult | 30–49 | Full career/business/family systems; peak earning band. |
| Middle-Aged | 50–64 | Career seniority, mentoring bonuses, health events begin (data-level). |
| Elder | 65+ | Retirement (pension from ledger history), reduced physical stats, inheritance planning events. |
| Deceased | — | Life ends; §6.4 inheritance executes; the row is archived, never deleted (family trees and memories reference it). |

**Transition rules:**
- Stage is **derived** from age at read time; there is no "stage" column to drift out of sync.
- Visible 3D stage changes (variant swaps) happen only at a **sleep/night boundary with a presented time-skip** (Phase 7 exit criterion) — never as a visible pop in front of the player.
- Inside the adult band (18–64), aging is continuous and visual: height fixed, hair-grey %, posture and skin-aging material parameters on the MetaHuman (master plan Part C #9). Across bands, the authored variant takes over.
- Death: probability-driven from elder stage + health events, always *announced to the simulation* as an event (family notified, inheritance runs, memories written) — never a silent row deletion.
- **Player characters:** aging is **opt-in per character** at creation (a player who wants a permanent 28-year-old hero may have one; their NPC family still ages). This is a game, not a tax form.

## 4. Needs & Daily Simulation (the tick model)

Each simulated day, per character (Full + Scheduled tiers):

1. **Schedule block** runs (Unit C `npc-schedules.json` templates by profession): home → commute → work → leisure → home.
2. **Economy tick:** wages in, rent/food/transport out — every movement a ledger row (§8).
3. **Needs update:** rest, food, social, security — deficits generate wants (§2.2) and bend tomorrow's schedule.
4. **Relationship drift:** small changes from the day's interactions; big changes only from events.
5. **Life events roll:** weighted event table by stage/traits (promotion chance, illness, meeting a partner, business opportunity). Events are the *only* source of large state changes — the simulation stays explainable.

Ambient tier skips the tick; it is visual life, not simulated life, and the design never pretends otherwise.

## 5. Household & Property Model

- A **household** is the economic unit: 1+ characters sharing a home property and a shared expense pool. Fields: home property id, district, member list (`household_members` with role: head/partner/child/dependent/roommate).
- A **property** (`properties`): type (plot, house, apartment, shop, office, factory, farm), district, address label, size, tier (which maps to the furnish-from-catalogue tiers of master plan Phase 5/6), owner (character, household, business, or city/NPC institution), status (owned/rented/for-sale/under-construction), and a construction stage for staged building (the Civil Engineer loop literally builds these).
- Characters join/leave households by events: leaving home (Young Adult), marriage/partnership, taking a roommate, death. Every move is a memory event for Full-tier members.
- Renting is a first-class state, not a failure state: most NPCs and new players rent. Ownership is a goal the economy makes meaningful (§7).

## 6. Family & Relationship Model

### 6.1 Kinship
Stored as typed edges in `relationships` with `relation_type`: `parent, child, sibling, partner, spouse, ex_partner, friend, best_friend, colleague, employer, employee, rival, acquaintance`. Parent/child edges form the family tree; sibling is derived via shared parents but cached as an edge for cheap queries. Adoption and guardianship are `parent` edges with a `via` note — the tree is about who raised whom, not genetics paperwork.

### 6.2 Scores
Each directed edge carries three scores −100..100: **trust, affection, respect** — plus a `last_interaction_at` and a small JSON of semantic flags (§2.3). Directed means A→B ≠ B→A: a boss may respect an employee who does not trust the boss. Behaviour (State Tree) reads the *actor's outgoing* scores.

### 6.3 Relationship events
`propose, marry, separate, have_child (creates a new character + household update), adopt, estrangement, reconciliation` — each is a simulation event that writes edges, memories, and (where relevant) ledger/property changes in one transaction.

### 6.4 Inheritance
On death: the character's solely-owned properties and ledger balance transfer by rule order — (1) spouse/partner, (2) children (equal shares; property goes to the eldest resident child with others compensated in credits where possible), (3) parents, (4) siblings, (5) the city (escheat — property returns to the market). Business ownership shares transfer the same way. Every transfer is ledger rows + memory events for the heirs. Phase 7's exit test ("3 generations, correct inheritance, no orphaned data") runs exactly this code path in accelerated simulation.

## 7. Economic Class — Derived, With Mobility

`economic_class` is computed from a rolling window: **net worth** (ledger balance + property value − debts) and **income band** (last 30 in-game days):

| Class | Rough band (v1 tuning, Unit F owns the numbers) | Starting-condition meaning |
|---|---|---|
| Lower-income | Net worth < 10k credits | Small/rented housing, limited starting capital, ordinary jobs — and the steepest, most supported climb (training, first-job guarantees). |
| Middle class | 10k–250k | Apartment/house ownership in reach, a car, small-business seed money. |
| Upper class | 250k–2M | Luxury housing, premium vehicles, established businesses. |
| Entrepreneur / wealthy | > 2M or controlling a business with employees | Hiring, expansion, market influence (Unit F). |

The owner's example card (Middle Class, 25,000 credits, Civil Engineer) is exactly the default **new-player start**: a rented apartment in Nexora Central City, an entry engineering job available, and the flagship profession loop as the climb. Classes move in both directions — debt and business failure are real — because a class that can only rise is a progress bar, not an economy.

## 8. Money: the Ledger Is the Truth

- Currency: **Nexora Credits (NCr)** — integer minor units in the database (no floats near money, ever).
- Every movement of money is an append-only `economy_ledger` row: `from_account, to_account, amount, reason_code (wage, rent, purchase, sale, tax, inheritance, mission_reward, loan_disburse, loan_repay, transfer, business_revenue, business_expense, fine, pension, seed), related entity, game timestamp, server sequence`. The list is the schema `CHECK`'s 15 codes, verbatim (corrected, Unit BZ · Queue 14 — the earlier draft listed `loan` as shorthand for the two loan codes; `loan` is not a code, and the list is illustrative: the `CHECK` in `data/schema.sql` is authoritative, not this paragraph).
- `characters.balance_cached` exists for fast UI; it is updated in the same transaction as the ledger insert, and a reconciliation job (Phase 9) proves cache = ledger sum. If they ever disagree, **the ledger wins** and the cache is rebuilt.
- In multiplayer, **only the server** may insert ledger rows or change property ownership (master plan Phase 9). Clients *request*; the server validates (funds, ownership, distance, cooldowns) and commits or rejects. A modified client can display a fake balance locally but can never spend it — that is the owner's security rule implemented, not quoted.
- NPC economy uses the same ledger with NPC character accounts; city institutions (bank, employers, market) are system accounts, so money is conserved and the Phase 6 "economy does not collapse" exit test is actually measurable (total credits, price index, employment rate are queries, not vibes).

## 9. Save-Game Mapping (single-player phases → Phase 9)

| Concern | Phases 1–8 (single-player) | Phase 9 (multiplayer) |
|---|---|---|
| Storage | The same schema in a local store: the game serialises the tables into the save slot (SQLite file or compressed JSON chunks inside the UE save game — implementation choice at Phase 5, schema unchanged). | PostgreSQL on the server; the client keeps only a read cache. |
| Authority | The local game is trusted (it's the player's own world). | The server is the only writer for ledger + property + inventory. |
| Slots | `save_slots` rows: slot id, account (local profile), character id, game timestamp, playtime, schema version. | Characters live server-side; "slots" become the character-select list. |
| Migration | Every save carries `schema_version`; migrations are forward-only SQL/JSON transforms shipped with the game. | Same version field on the server DB; migrations run at deploy. |
| NPC worlds | The whole district's characters/households/ledger save with the slot — a saved world is a saved *society*, not just a saved player. | The district is persistent and shared; no per-player copy exists. |

## 10. What This Document Deliberately Does Not Decide

- Concrete wages/prices/rent numbers → **Unit F** (economy GDD) owns them; this model only fixes the *shape*.
- Mission structure that reads these goals → **Unit G**.
- District geography that households/properties reference → **Unit C (GDD-02)**.
- The C++ classes that mirror these tables in UE → later scaffolding units, generated *from* `schema.sql`, never the other way around.

*End of GDD-01 v1.0. Changes happen by PR with a schema migration note whenever `schema.sql` changes shape.*
