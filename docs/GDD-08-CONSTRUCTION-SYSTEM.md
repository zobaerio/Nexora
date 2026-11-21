# NEXORA — GDD-08: Construction System Design (Flagship)

**Unit Q · Version 1.0 · 2026-11-21**
**Parent documents:** `NEXORA-MIGRATION-PLAN.md` Phase 5 · `docs/GDD-03-ECONOMY-AND-PROFESSIONS.md` §6 (the flagship loop — this document is its buildable detail), §3.4 (materials), §4.1 (ledger), §5 (business ledger) · `data/prices.json` (`construction_materials` — owns every material price) · `docs/GDD-01-LIFE-AND-DATA-MODEL.md` §5 (property/construction state), §8 (ledger) · `docs/GDD-06-NPC-BEHAVIOUR.md` §4.1 (construction worker sub-state), §7 (weather) · `docs/GDD-02-RUPSHA-CITY-DISTRICT1.md` §2/§6 (plots, property stock) · `data/buildings-district1.json` (property vocabulary: `property_type`, `status`) · `docs/GDD-07-VEHICLES-AND-TRAFFIC.md` §3/§7 (site deliveries)
**Status:** DESIGN ONLY. No construction site, stage logic or plan tool exists yet; nothing here claims a wall stands today. This document is the contract Phase 5 implements against.

> **Design law:** a building is a ledger with walls. Every stage consumes materials that were *bought* (ledger rows), is built by *named crew* on *scheduled days*, is *inspected* before it is paid for, and ends as a property row the rest of the simulation can live in, rent or buy. If a stage cannot point at its materials, its crew, its inspection and its payment, it does not ship.

---

## 1. The Loop, End to End

GDD-03 §6 owns the loop's shape (take job → plan → estimate → supervise → payment → reputation). This document owns the buildable detail inside steps 3–5: the stage machine, the materials arithmetic, the crew, the checks, and the moment a site becomes a property.

A **job** is a record: client (character or civic account), plot (a `properties` row with `property_type = plot` or an existing building being extended), plan (footprint/floors/type), budget, deadline (game days), quality bar, and the engineer's accepted estimate (§3). The v1 playable site is `b_d1_industry_staged_plot` ("Staged Build Plot + Site Office", status `under_construction` in `buildings-district1.json`); client jobs on other plots reuse the same machine.

## 2. The Stage Machine

Five stages, in order, never skippable (GDD-03 §6 step 4). GDD-03's four-stage wording (foundation → structure → roof → finishes) maps onto these five by splitting *structure* into **frame** and **walls** — the split exists because the crew's visible work differs (GDD-06 §4.1: the worker's task matches the stage).

| # | Stage | Days (v1 job) | Work the player sees | Gate to advance |
|---|---|---|---|---|
| 1 | `foundation` | 3 | Excavation, footing pour, foundation brickwork | Engineer inspection (§5) + stage materials consumed |
| 2 | `frame` | 3 | Columns and beams cast; rebar cages before each pour | Inspection incl. rebar check *before* the pour — the one inspection that cannot be done late |
| 3 | `walls` | 2 | Brickwork rises, openings left per plan | Inspection |
| 4 | `roof` | 2 | Slab cast (flat-roof typology, District 1), cured over the stage's days | Inspection after cure |
| 5 | `finishing` | 2 | Floor tiles, weathercoat paint, fittings | Final inspection + client sign-off (§6) |

**Stage rules:**
- A stage runs only while its materials are on site (§4) and its crew is present (§5 of the schedule — crew are GDD-06 characters with `Work` blocks at the site anchor).
- Outdoor stages (1–4) halt under the weather `outdoor_work_halted` effect family (storm; GDD-06 §7, GDD-07 §7). Halted days do not consume materials and do not count against the deadline's *worked* days, but the calendar deadline keeps moving — weather is schedule risk the estimate cannot remove, only price.
- The engineer (player or NPC) must be on site for each inspection. A stage that advances without inspection carries a hidden defect risk (§5) — the game never blocks the shortcut; it prices it.
- Progress is a property of the *site record*, saved like any society state (Unit M mapping): stage, stage-day, materials on site, inspection flags, defect flags.

## 3. Materials — the Estimate Is Real Arithmetic

The estimate step (GDD-03 §6 step 3) multiplies plan quantities by `data/prices.json` `construction_materials` — the seven items there are the *only* materials v1 construction consumes, and every quantity below is denominated in prices.json's own units (bags, 1,000 pcs, tonnes, cubic ft, sq ft, litres).

**Worked example — the GDD-03 first job (single-room extension, budget 120,000 NCr, ≈12 days).** Quantities per stage; costs computed at prices.json v1.0 prices:

| Stage | Materials (quantity × unit price) | Stage cost |
|---|---|---|
| Foundation | cement 14 bags ×550 · brick 500 pcs (0.5 × 12,000) · sand 70 cft ×45 · stone 60 cft ×60 | 20,450 |
| Frame | cement 16 ×550 · rebar 0.13 t ×95,000 · sand 60 ×45 · stone 60 ×60 | 27,450 |
| Walls | brick 750 pcs (0.75 × 12,000) · cement 5 ×550 · sand 45 ×45 | 13,775 |
| Roof | cement 15 ×550 · rebar 0.06 t ×95,000 · sand 45 ×45 · stone 55 ×60 | 19,275 |
| Finishing | tiles 30 sq ft ×85 · paint 5 l ×420 · cement 2 ×550 | 5,750 |
| **Total materials** | | **86,700** |

GDD-03's tuning line said "materials ≈ 85,000" — the computed table lands at 86,700, within 2% of the tuning figure, and the *table* is now the authority (if prices.json prices move with the market index, §4, the estimate moves with them; the quantities do not silently change).

**Estimate accuracy is the skill.** The player's submitted estimate is compared against actual consumption at job end: within ±10% → reputation gain (GDD-03 §6 step 3); outside → reputation cost. Actuals can differ from the table only through documented causes: defect rework (§5), weather damage to stored materials (storm, capped at 5% of on-site stock), or a client change order (a new mini-estimate, client-approved, ledger-visible). There is no random silent drift — a player who estimates the table well is never ambushed by invisible numbers.

## 4. Buying & Delivery

- Materials are bought from the market godowns (`d1_market`) against the accepted estimate, stage by stage or in bulk (bulk risks the storm-storage loss above; staged buying pays more delivery trips — a real trade-off, priced by GDD-07 truck deliveries).
- Purchase rows hit the job's funding (§6) as ledger `purchase` entries at the *current* market price: the price index moves ±15% (prices.json cement note; GDD-03 §4.4/§5), so an estimate accepted last week can cost more this week. The estimate protects the *fee*, not the client, from index movement — change orders exist for overruns beyond the agreed contingency (v1: 10% of materials).
- Deliveries arrive by truck on the GDD-07 model (arterial/collector only; the site anchor must be reachable — plots fronting only goli lanes take rickshaw-scale staged deliveries at lower capacity, which is why the old town builds slowly and the design is fine with that).

## 5. Crew, Safety & Quality

**Crew roles** (all are GDD-06 characters whose `Work` sub-state is the site; nobody is a prop):

| Role | Who | Does |
|---|---|---|
| Engineer / supervisor | The player, or an NPC `civil_engineer` | Plan, estimate, inspections, sign-off requests |
| Site crew | 2–4 `construction_worker` characters (day wage, GDD-03 §2: 9,000–20,000/month band, paid daily) | The stage's TaskLoop (GDD-06 §4.1) — carrying, laying, casting, matched to the stage |
| Client | The commissioning character (or civic account) | Funds the job (§6), signs off at the end |

Crew are scheduled through `npc-schedules.json`'s construction template instantiated to the site anchor for the job's duration; a worker who is ill, rained off (§2) or unpaid (business ledger empty, GDD-03 §5) does not appear, and the stage waits. Wages for player-run jobs are paid from the job funding/business ledger on the daily schedule — crew pay is a cost the *fee* must cover at scale, which is how a one-person engineer becomes a firm (GDD-03 §5).

**Safety checks** are part of each inspection, not a separate minigame: the inspection checklist per stage (foundation: depth/footing; frame: rebar before pour; walls: openings/plumb; roof: cure; finishing: fittings/weathercoat) includes the site-safety line (scaffolding, helmets on crew visuals, material storage). Skipping an inspection skips the safety check with it.

**Defects.** A stage advanced uninspected rolls the defect risk at the next inspection or, worst case, at sign-off: a defect means rework — the stage's materials partially re-consumed (v1: 40% of stage materials) and re-inspected, paid from the job funding if the engineer skipped, from contingency if inspected-and-passed (latent defect — the client's cost, capped). Defect outcomes are recorded on the job record and feed reputation either way; nothing about them is hidden from the player's job summary after the fact.

## 6. Payment Milestones — the Ledger Shape

Funding follows GDD-03 §6 steps 3+5, made concrete:

1. **Acceptance:** the client moves *estimate + fee* into the job's funding (their account → job escrow line on the engineer's business ledger, GDD-03 §5). Fee = 10% of materials at entry tier, 15% at senior (GDD-03 §6 step 3): on the worked example, 8,670 NCr at entry. (GDD-03 quoted 8,500–12,750 against its rounded 85,000; the computed table's fee range is 8,670–13,005 — the formula, not the rounded quote, governs.)
2. **Per stage:** on inspection pass, the stage's *actual* material cost + the stage's share of the fee (fee ÷ 5 stages) releases to the engineer: ledger rows, reason `construction_payment` (GDD-03 §4.1 reason list). On the worked example at entry tier, stage releases are 22,184 / 29,184 / 15,509 / 21,009 / 7,484 NCr (stage materials + 1,734 fee share), totalling 95,370 = 86,700 + 8,670.
3. **Sign-off:** the final stage's release requires the client's sign-off, which requires the quality bar (all inspections done, no unresolved defects). A client refuses sign-off only for a *recorded* reason (defect, deadline breach) — never arbitrarily; the job record shows it.
4. **Failure paths:** abandonment (engineer walks) returns unspent funding to the client and costs reputation (GDD-03 §6 step 1); client insolvency mid-job freezes the site at the current stage — the site record persists exactly as §2 saves it, resumable when funded.

Money is conserved throughout (GDD-03 design law): escrow is a ledger scope, not a money spawn; crew wages, materials and fee all trace to the client's original funding or the firm's ledger.

## 7. Completion — a Site Becomes a Property

On sign-off, in one transaction of the world state:

1. The property row flips: `status: under_construction → owned`, `property_type` set from the plan using the `buildings-district1.json` vocabulary (`apartment`, `house`, `shop`, `office`, `factory` — the schema CHECK list in `schema.sql`), `units` set from the plan, tier set from the plan's finish level (1–5, priced against the prices.json rent tiers).
2. The new property enters the world exactly like the 42 seed properties: it can house a household (GDD-01 §5), be rented (`for_rent` / tenancies) or listed (`for_sale`) at the owner's choice, and its value enters the property-tax base (GDD-03 §4.2, 0.5%/year of value).
3. The job record closes with its full history (estimate vs actuals, inspections, defects, payments) — the engineer's portfolio, and the data the reputation system and later missions (GDD-04) read.
4. For an *extension* job, the existing property's `units`/tier update instead of a new row being born — the starter-block flat gaining a room is the same machine at smaller scale.

The staged plot (`b_d1_industry_staged_plot`) is reusable: after completion it is a finished property, and the *next* staged site is whichever plot a client brings — the construction yard (`b_d1_industry_construction_yard`) remains the crew/materials staging anchor.

## 8. What This Document Deliberately Does Not Decide

- **No structural engineering simulation.** Quantities are a game BOQ — deliberately close to real Khulna market levels (GDD-03 §3.4) so the *estimating skill* transfers, but nothing here certifies a real building, and the design never claims it does.
- **No plan-tool UI detail.** The plan step's interface belongs to GDD-05's successors; this document fixes the plan's *data* (footprint, floors, type, quantities out), not its screens.
- **No multi-storey / high-rise rules.** v1 jobs are the extension → small building ladder of GDD-03 §6; the uptown tower class of jobs waits for the reputation ladder and a later unit.
- **No new materials.** Seven items in prices.json carry all of v1 construction. Steel sections, glass, timber joinery etc. arrive, if ever, as a prices.json change with its own unit — not as inventions in stage tables.
- **No multiplayer construction.** Concurrent crews and shared sites are Phase 9 (Unit S notes the authority shape); the job record is written so a server *can* own it, but nothing here designs that protocol.
