# NEXORA — GDD-13: Life Stages & Aging

**Unit AE · Version 1.0 · 2026-11-21**
**Parent documents:** `NEXORA-MIGRATION-PLAN.md` Part C #9 (life stages & aging), Part D Phase 7, Part J §J.1 (the Phase 7 gate stands, unchanged) · `docs/GDD-01-LIFE-AND-DATA-MODEL.md` §2 (tiers), §3 (life stages), §6.4 (inheritance), §8 (ledger) · `docs/GDD-06-NPC-BEHAVIOUR.md` §2 (state machine), §4.12 (life-stage templates), §5 (crowd tiers & promotion) · `docs/GDD-11-EDUCATION.md` §2–§6 (school, programmes, credentials, hostels) · `docs/GDD-12-HEALTH.md` §3.4 (age-related health events feed the death rule) · `docs/PHASE2-METAHUMAN-SHEET.md` §3, §5, §6 (the adult MetaHuman pipeline, outfit rules, LOD/crowd tiers) · `docs/GDD-09-CHARACTER-CREATOR.md` §2 (child/elder not creatable in v1) · `docs/TECH-CLOCK-WEATHER.md` §1–§2 (day phases, time-skip rule) · `docs/GDD-03-ECONOMY-AND-PROFESSIONS.md` §1–§2 (owner start, wage bands) · `docs/SESSION-01-REPORT.md` (headless lifecycle: `tools/sim/lifecycle.py`) · `docs/SESSION-02-REPORT.md` (generations: `tools/sim/generations.py`; education: `tools/sim/education.py`)
**Status:** DESIGN ONLY — a design document. No UE code, no character asset, no animation and no system is built by this document, and nothing here claims a UE feature works. The life-cycle *simulation* already exists and runs headlessly (`tools/sim/` — Session 01/02, see §1); this document is the UE presentation/design layer over it: what the player sees when the sim's stages change, and the rules that keep those changes honest.

> **Design law:** the simulation decides *when* a life changes; this document decides *how it is shown*. No visual may contradict the sim's record. Age is derived from `born_at_game_time` plus the world clock (GDD-01 §1, §3) — it is never typed in, never edited, and never stored as a stage column that can drift. If a presentation cannot be traced to a sim event, a schedule template, a data row, or a section of this document, it does not ship.

---

## 1. What Already Exists (the Layer Under This Document)

This document re-implements nothing. The headless core it presents is already merged and test-proven:

| Sim piece | Module | What it already does (verified in its session report) |
|---|---|---|
| Stage derivation | `tools/sim/lifecycle.py` — `stage_for_age()` | Eight stages from age: Infant 0–2, Child 3–12, Teen 13–17, Young Adult 18–29, Adult 30–49, Middle-Aged 50–64, Elder 65+, Deceased. Stage is derived at read time; the stored `life_stage` cache column is a copy, never the truth. |
| Template selection | `tools/sim/lifecycle.py` — `template_id_for()` | Picks the day's schedule template by stage/employment/enrolment: Child → `child_school_day`, Teen → `student_day`, enrolled college student → `student_day`, employed adult → their profession template, otherwise the `elder_day` home-centred shape. |
| Daily stage check | `tools/sim/lifecycle.py` — `daily_check()` | Per character per day: stage transitions logged, retirement at 65, mortality roll. |
| Death cascade | `tools/sim/lifecycle.py` — `die()`, `heirs_in_order()`, `death_probability()` | Employment ends, headship passes, balance/property/business move by heir order, family grief as events, memories and emotions. See §8 and the honest gap in §12. |
| Generations | `tools/sim/generations.py` — `generation_of()`, `ancestors()`, `descendants()`, `lineage()`, `record_history_sweep()`, `knowledge_transfer()` | Generation index derived from the parent graph (founders = 1, never stored); lineage queries; monthly elder-to-child knowledge transfer through the education caps. |
| Education | `tools/sim/education.py` — `enrol_school_sweep()`, `enrol_college()`, `has_credential()`, `accrue_school_study()`, `accrue_college_study()`, `monthly_sweep()`, `_capped_gain()` | Enrolment, measured attendance, GDD-11 caps enforced, credential gate on hiring. |
| Observation evidence | Session 01, 90-day run (seed `nexora-1`, 242 agents) | 250 alive at day 90 (9 births, 1 death — an elder, whose balance passed by inheritance), 6 stage transitions, 0 ledger reconciliation mismatches. Session 02, same seed: 249 alive (8 births, 1 death with inheritance), 79 school enrolments, 2 young adults left home. |

**Consequence for Phase 7 implementation:** the UE work is presentation, variant assets, and the transition protocol (§4). The rules for *who* ages, *when* they retire, and *who* inherits are already written and tested; Phase 7 must not re-derive them in Blueprint or C++ as a second, drifting copy. The UE layer reads the sim's stage, events, and ledger rows and renders them.

---

## 2. The Stage Map — Sim Stages to Visual Variants

Eight sim stages, four visual variant families. The mapping is deliberate: the sim's finer bands (Young Adult / Adult / Middle-Aged) are one visual family — the adult MetaHuman — aged continuously inside the band (§5). The bands that need a different body are separate authored variants.

| Sim stage (GDD-01 §3) | Age band | Visual variant family | Schedule template (sim) | Key systems active |
|---|---|---|---|---|
| Infant | 0–2 | **No independent variant.** Household-dependent only; no independent simulation (GDD-01 §3). | None — the sim uses the `elder_day` home-centred *shape* as a fallback (`lifecycle.template_id_for()`); the data ships no infant template. | None of its own. Present in the household record only. |
| Child | 3–12 | **Child variant** (authored asset — gated, §11) | `child_school_day` (`data/npc-schedules.json` `life_stage_templates`) | School attendance at `b_d1_civic_school`, skill seeds, family relationships form (GDD-11 §2). |
| Teen | 13–17 | **Teen variant** (authored asset — gated, §11) | `student_day` | School + part-time work variant, trait formation events, profession interests (GDD-01 §3; GDD-11 §2). |
| Young Adult | 18–29 | **Adult MetaHuman** (§5) | `student_day` if enrolled, else profession template | Profession choice, first employment, leaving the parental household becomes possible, life goal chosen (GDD-01 §3). |
| Adult | 30–49 | **Adult MetaHuman** (§5) | Profession template | Full career/business/family systems; peak earning band (GDD-01 §3). |
| Middle-Aged | 50–64 | **Adult MetaHuman** (§5) | Profession template | Career seniority, mentoring bonuses, health events begin at data level (GDD-01 §3; GDD-12 §3.4). |
| Elder | 65+ | **Elder variant** (authored asset — gated, §11) | `elder_day` | Retirement, reduced physical stats, inheritance planning events (GDD-01 §3; GDD-06 §4.12). |
| Deceased | — | **No variant.** The row is archived, never deleted (GDD-01 §3). | None. | Inheritance executes (§8); family trees and memories keep referencing the row. |

**Rules that follow from the table:**
1. A stage change that crosses a variant-family boundary (Child→Teen, Teen→Young Adult, Middle-Aged→Elder) is a **variant swap** and follows the transition protocol in §4. A stage change inside the adult family (Young Adult→Adult→Middle-Aged) is **not** a swap — it is a parameter change inside the adult band (§5), and no transition ceremony is shown.
2. Infant is never rendered as a standalone character in v1. This is not a missing feature to fill quietly: GDD-01 §3 gives infants no independent simulation, and the sim has no infant template. An infant appears only as a household fact (a birth event, a family-tree node) until a later unit designs infant presentation explicitly.
3. The Deceased stage has no body, no schedule, and no variant. A dead character's face must never reappear as an ambient crowd member: the variant pool and the crowd generator read only living characters.

---

## 3. Stage Variants — Authored, Swapped at Thresholds

The plan (Part C #9) states the approach, and this document adopts it without softening: **stages are separate, authored variants swapped at thresholds, with continuous tweaks inside the adult band.** No engine feature ages a human from birth to death, and no document in this project may imply otherwise.

### 3.1 What a variant is

A stage variant is a complete, authored character presentation for one variant family: body proportions, face, hair/groom, outfit set, locomotion set, and voice/animation register appropriate to the stage. Variants are data, in the same sense as the creator parameters in GDD-09: a character's record points at a variant id (GDD-01 §2.1 — `appearance reference`: MetaHuman parameter set id for adults, stage-variant asset id for child/teen/elder), and swapping a variant never touches simulation code.

### 3.2 Per-variant rules

| Variant | Rules |
|---|---|
| Child | Proportions are a child's, not a scaled-down adult. Height, head-to-body ratio, gait, and reach are authored for the 3–12 band. School outfit context from the clothing catalogue (GDD-11 §7 notes the catalogue already carries the school-uniform mapping for the child/teen outfit context). A child is never in `Converse` alone with strangers — dialogue routes to a parent/guardian NPC where one exists (GDD-06 §4.12). Children have no economy tick of their own; their costs run through the household pool (GDD-01 §3, §5; GDD-11 §2). |
| Teen | Proportions are a teenager's, not a scaled-down adult and not a small adult. Part-time work uses the template's afternoon work block at a market/shop anchor (GDD-06 §4.12; GDD-11 §2); part-time earnings flow into the household pool, and **no part-time wage is priced** — `prices.json` has no part-time wage line and this document invents none (GDD-11 §2, §7). |
| Adult (MetaHuman) | The Phase 2 pipeline (PHASE2-METAHUMAN-SHEET §3, §5, §6): full MetaHuman for Full tier, shared preset pool (~40 approved presets) for Scheduled tier, never a MetaHuman for Ambient tier. One outfit per context — work, casual, formal (PHASE2 §5). Aging inside this band is §5, not a new variant. |
| Elder | Proportions, posture, gait, and face are an elder's, authored — not an adult MetaHuman with a grey-hair toggle. Movement speed is scaled (GDD-06 §4.12: elder template is home-centric, leisure at `park`, needs skew to rest/security). Retirement presentation is §7. |

### 3.3 What is NOT a variant

- **Scaling an adult down is not a child.** A shrunk adult MetaHuman is explicitly not a child variant (GDD-09 §2: the creator "says so on the life-stage screen instead of offering a shrunk adult"). Any implementation that scales the adult mesh to child height fails this document's acceptance checks (§10).
- **A grey-hair toggle on an adult is not an elder.** Grey hair is an adult-band parameter (§5). The elder variant differs in body, posture, and movement, not only in hair colour.
- **A costume change is not a stage change.** Outfits change by context (PHASE2 §5); stages change by age threshold. The two systems never share a trigger.

---

## 4. The Transition Protocol — No Visible "Pop"

This is the Phase 7 exit criterion in the plan (Part D Phase 7): **stage transitions never visibly "pop"**. The protocol below is the whole of it, and every variant swap must follow it.

### 4.1 The rule

A variant swap happens **only at a sleep/night boundary, with a presented time-skip** (GDD-01 §3; TECH-CLOCK-WEATHER §1: the clock never jumps silently; Night is 00:00–05:00 and 20:00–24:00). The sequence:

1. **Detection (sim, daytime):** the sim's `daily_check()` logs the stage transition during the day's tick. The UE layer records a *pending transition* for that character. Nothing visible changes yet.
2. **Waiting (until night):** the character lives the rest of the day in their current variant, on their current template. A child who turns 13 at noon still goes to school as a child that day; the sim's stage is already Teen, the presentation catches up at night. This lag is by design, not a bug — the alternative is a mid-day pop.
3. **Sleep boundary:** the transition fires only when the character is in their `Sleep` state at their home anchor (GDD-06 §2: `Sleep` is at the home anchor, in bed). If the character is not home/asleep at the night boundary — travelling, at work, in dialogue — the transition waits for the next night on which they sleep at home. It never fires while the player can see the character.
4. **Presented time-skip:** the swap itself happens behind a time-skip presentation the player is shown: the night passes (the clock's presented skip, TECH-CLOCK-WEATHER §1), and the morning shows the new variant. The skip is the same mechanism sleep already uses; a stage transition rides it, it does not invent a second one. `SetTimeOfDay` exists for the editor/panel and tests, not for gameplay shortcuts (TECH-CLOCK-WEATHER §1).
5. **Morning reveal:** the character wakes in the new variant, on the new stage's template (`template_id_for()` already returns it — e.g. a new Teen runs `student_day` the next morning). The household notices in data: a life event and, for Full-tier family members, an episodic memory (GDD-01 §2.3). No UI banner announces "X is now a Teen" unless the character is the player's own family member, in which case the family event log records it as a life event, not as a system alert.

### 4.2 Rules and edge cases

- **One swap per night per character, maximum.** A character cannot cross two variant boundaries in one night; the sim's age bands make that impossible in normal time, and accelerated time (§9) still applies one transition per night boundary.
- **The player character never swaps without the player's involvement.** Player aging is opt-in (GDD-01 §3; §6). An NPC family member's swap may happen while the player sleeps elsewhere — the player meets the new variant in the morning, with the family event log as the explanation.
- **Off-screen NPCs transition the same way.** An NPC outside the player's area transitions by the same rule (their day advances by the GDD-01 §4 tick; position is derived from their current block — GDD-06 §9). When the player next sees them, they are in the correct variant for their sim stage. There is no "catch-up pop" on arrival: the swap is recorded as having happened at the last night boundary, and the character simply is the new variant.
- **Ambient tier never transitions visibly.** Ambient NPCs are Mass representations with no identity row (GDD-01 §2; GDD-06 §5). They do not age, and a crowd member must never be seen to change stage. If an Ambient NPC is promoted to Scheduled (§5 of GDD-06), they receive an identity row and a stage derived from their generated age at that moment — that is their first variant, not a transition.
- **Interrupted sleep:** if a life event interrupts sleep (illness, emergency — GDD-06 §2: `Sleep` is interruptible only by life events), the pending transition waits for the next successful sleep night. A sick child's birthday does not produce a swap in a clinic bed.

---

## 5. Aging Inside the Adult Band (18–64)

Between Young Adult and Middle-Aged, the character stays on the adult MetaHuman and ages continuously. The plan (Part C #9) names the three mechanisms; this document fixes how each is presented and bounded.

| Mechanism | Presentation rule | Bound |
|---|---|---|
| Hair grey | Hair-grey percentage rises with age inside the band. It is a groom/material parameter on the existing MetaHuman hair, not a wig swap. Grey is gradual and monotonic within a character's life — hair never un-greys. | 0% at Young Adult entry, increasing through Adult and Middle-Aged. No fixed percentage-per-year is set here: the rate is Phase 7 tuning, and it must be slow enough that a character the player sees weekly changes visibly only over in-game years, not weeks. |
| Posture | Posture stoops gradually: spine and shoulder parameters in the locomotion/animation layer shift with age. Gait slows slightly; the walk/run speeds the player learned in Phase 3 remain the *design* speeds for the player character — NPC posture change is visual and small, and must never read as a limp or an injury (injury is GDD-12's condition system, not aging). | Subtle at Adult, visible at Middle-Aged. Never enough to change a schedule block's timing: the sim's commute and work blocks do not bend for posture. |
| Material aging | Skin-aging material parameters on the MetaHuman (the plan's "material aging"): wrinkle/normal intensity, skin roughness variation, age spots as a material parameter. Applied to the face and visible skin, driven by the same derived age. | Same monotonic rule as hair: aging parameters only ever increase with age for a given character. They are parameters on the adult MetaHuman, never a texture swap to a different person — the face must remain recognisably the same person at 28 and at 58 (the Phase 2 owner-approval rule, PHASE2 §3.1, applies by analogy to every Full-tier NPC: a MetaHuman the family does not recognise is a failed variant). |

**Continuity rules:**
- Adult-band aging is **continuous and parameter-driven**, so there is nothing to "pop": no threshold inside 18–64 triggers a swap, a loading screen, or a notice. The player notices it the way people notice aging — over time, not in a moment.
- The three parameters move together from the single derived age. There is no separate "hair age" and "skin age" that can drift apart.
- Full-tier NPCs get the full parameter range; Scheduled NPCs get the same parameters from the shared preset pool (PHASE2 §6: presets are "varied age" — the pool already spans the band, so a Scheduled NPC's aging is a preset-parameter drift, not a re-sculpt). Ambient NPCs get none of this — they have no faces (GDD-06 §5).
- The player character's adult-band aging follows §6: only if aging is opted in for that character, and then by the same parameters.

---

## 6. NPC Families First — Player Aging After

The plan (Part D Phase 7) orders this explicitly, and GDD-01 §3 gives the player rule. This document makes the order a gate, not a preference.

### 6.1 Phase 7 ships NPC aging first

- **NPC families are the proving ground.** The transition protocol (§4), the adult-band parameters (§5), and the inheritance presentation (§8) are proven on NPC households — Full and Scheduled tiers — before any player-facing aging exists. The acceptance checks in §10 are all NPC checks for this reason.
- **Why NPCs first:** an NPC transition failure is a visible bug in one household; a player-character transition failure breaks the player's own identity (the face the owner approved in Phase 2). The plan's order exists to contain that blast radius.

### 6.2 Player aging — opt-in, and only after NPC aging is proven

- **Opt-in per character at creation** (GDD-01 §3): a player who wants a permanent 28-year-old hero may have one; their NPC family still ages. Opting in is a creation-time choice, recorded on the character row; it is not toggled mid-life to dodge a transition, and it is not a setting that silently re-ages the player backwards.
- **The player ages by the same rules:** same thresholds, same night-boundary protocol, same adult-band parameters. There is no separate player aging system. The only player-specific presentation is that the player's own transition is shown to the player directly (their own sleep → time-skip → morning mirror/character screen), rather than discovered in the family event log.
- **Gate:** player aging ships only when the NPC acceptance checks (§10) pass in a packaged build. Until then, the player character's visual age is fixed at creation, whatever the sim's derived age says — and the game says so on the character screen rather than pretending the number and the face agree. (GDD-09 §2 already establishes the pattern: the creator says what it cannot do instead of offering a fake version.)

---

## 7. School, Career, Retirement — What Each Stage Shows

Each stage's systems already exist in the sim and in earlier GDDs. This section fixes only what the player *sees* of them in Phase 7, stage by stage.

### 7.1 School (Child, Teen)

- **The loop is GDD-11 §2, shown, not re-designed:** `child_school_day` — commute 07:15–07:30, `study@school` 07:30–13:00 at `b_d1_civic_school` (see the correction note in §12: the school is in `d1_civic`, per the data), home, `leisure@park` 16:00–18:00, `study@home` 18:00–19:30. Attendance writes `subject_knowledge` experience; the school cap is **20** and a college programme caps its primary skill at **24** — both below the lowest tier-2 threshold (**30**) in `professions.json`, so education alone never promotes anyone (GDD-11 §4, §5).
- **Presentation:** the school day is visible as attendance and as skill movement on the character record, not as a rendered classroom full of children until the asset gate (§11) allows rendered children. GDD-11 §2 already states this honestly: in v1 the school loop is a *simulation* loop — attendance, skill accrual, and family memories all run; the visible classroom population is the teacher plus whichever tiers the asset gate currently allows. This document does not change that, and Phase 7 must not stage a classroom of adult-scaled stand-ins.
- **Absence:** the only designed source of school absence is illness (GDD-11 §2; GDD-12). There is no truancy system in v1; a child NPC does not skip school by choice, and the aging presentation must not invent a "skipping school" animation or event.
- **Teen part-time work** (§3.2) and **college** (Young Adult): enrolment is a stage goal naming the programme (`character_goals`, GDD-11 §5); completion at the cap grants the credential, and hiring into `civil_engineer`, `doctor`, `teacher`, and `software_developer` requires it (`education.py` — `has_credential()`; genesis professionals are grandfathered, Session 02 report). The player civil engineer keeps the "game start" door: a player may start degreed by character creation (GDD-11 §5; GDD-01 §1).

### 7.2 Career (Young Adult, Adult, Middle-Aged)

- **The loops are GDD-03's, unchanged:** Civil Engineer (flagship, entry **22,000 NCr/month**), Shop Owner, Taxi Driver are the playable loops; the other eight professions are NPC-run with the same wage table (GDD-03 §2: entry/mid/senior bands per profession, e.g. Teacher 15,000 / 24,000 / 38,000; Doctor 30,000 / 55,000 / 95,000). Aging changes nothing about wages: tier rises on skill + reputation + time-in-post, never on money spent and never on age (GDD-03 §2).
- **What aging adds to careers is presentation only:** seniority is shown through the adult-band parameters (§5) and through mentoring — Middle-Aged characters carry mentoring bonuses (GDD-01 §3) and, in the sim, monthly knowledge transfer from an elder living with children (`generations.py` — `knowledge_transfer()`), which accrues through the education caps so a teacher-grandparent's subject knowledge still respects the school cap (Session 02 report). A senior engineer *looks* senior and *teaches* juniors; their pay still follows the wage band.
- **Leaving home** (Young Adult): the sim implements it as a priced move into a real vacant unit (Session 02, `households.py`); the UE presentation is a household move at a night boundary — the same "no pop, moves happen off-screen/at boundaries" discipline as §4. The player is told through the family event log, not by watching furniture teleport.

### 7.3 Retirement (Elder, 65+)

- **Retirement at 65** is a sim event (`lifecycle.daily_check()` logs `retirement`; employment ends). Presentation: the character's template becomes `elder_day` — home-centric, leisure at `park`, needs skewing to rest/security (GDD-06 §4.12) — and their work sub-states stop. The retirement itself is a family life event with memories for Full-tier members, not a UI popup.
- **Pension — the honest gap:** GDD-01 §3 names retirement income ("pension from ledger history") but **no pension figure exists in `prices.json` or GDD-03**, and the sim's **3,500 NCr/month is labelled a SIM ASSUMPTION** in `tools/sim/engine.py` (`PENSION_NCR_PER_MONTH`) and in the Session 01 report. The UE presentation must therefore show retirement income only as a ledger `pension` row with whatever figure the economy then defines — it must not display 3,500 NCr/month as a canonical pension, and it must not invent a pension rate, a pension age other than 65, or a pension UI that quotes a number the data does not own. Fixing the pension figure is a future economy unit's job; this document records the gap rather than filling it (see §12).
- **Elder life:** reduced physical stats and health events that begin at Middle-Aged and strengthen at Elder (GDD-12 §3.4) feed the death rule — they never replace it. An elder's day is quieter by template, not by a debuff icon: the presentation is the `elder_day` schedule itself.

---

## 8. Death & Inheritance — Presentation of the Cascade

Death in NEXORA is a sim event with a presentation, never a silent deletion (GDD-01 §3). The cascade already runs in `lifecycle.die()`; this section fixes what the player sees and in what order.

### 8.1 Death presentation

- **Announcement:** death is announced *to the simulation* as an event (GDD-01 §3): a `death` life event on the deceased, `death_of_family` events plus episodic memories (weight −90 in the sim) and emotion effects for living family members. The player learns of an NPC death through the family event log and through the household's changed life — an empty chair at the home anchor, a `Sleep` block that no longer has its sleeper — not through a death cutscene. There is no designed funeral cutscene in v1; a family gathering event exists in the sim (`events.py` — family gatherings honour the elder-respect tradition, Session 02) and is the presentation vehicle if the family gathers.
- **Mortality is a sim model, not an actuarial table.** `lifecycle.death_probability()` is daily, near zero in youth and rising steeply for elders — the sim's own stated assumption; GDD-01 defines stages and inheritance, not actuarial tables (Session 01 report). The UE layer must never display a "chance of death" percentage, a life expectancy, or a health bar that implies a known mortality number. What the player sees is health *conditions* (GDD-12: bands and causes, never invented diagnoses) and, for elders, the honest fact that health events strengthen with age.
- **The deceased's record:** the character row is archived with `died_at_game_minutes` set; it is never deleted, because family trees and memories reference it (GDD-01 §3). The family tree UI shows the deceased as deceased — a completed life, not a missing person.

### 8.2 Inheritance presentation (GDD-01 §6.4)

The heir order is fixed: **(1) spouse/partner, (2) children (equal shares), (3) parents, (4) siblings, (5) the city (escheat — property returns to the market).** Business ownership shares transfer the same way. Every transfer is ledger rows plus memory events for the heirs.

What the player sees, in order:
1. **The event:** the death event lands in the family log; heirs receive an `inheritance_received` life event and memory (sim: `die()` logs both).
2. **The money:** balance transfers as `inheritance` ledger rows — equal shares among the heir class, with any rounding remainder to the city account (`SYS-CITY`). The ledger is the truth (GDD-01 §8): the heir's balance changes only because ledger rows say so, and the UI shows the rows, not a lump-sum announcement.
3. **The property:** solely-owned property passes to the heir class. **Honest gap — see §12:** GDD-01 §6.4 says property goes to the eldest resident child with others compensated in credits where possible; the sim (`die()`) implements the simpler rule — the first heir takes solely-owned property, otherwise it returns to the market. The UE presentation follows the sim's implemented rule until the design and the sim are reconciled by a later unit; it must not present the eldest-child compensation as if it runs.
4. **The business:** ownership shares transfer by the same heir order; the business keeps running under the new owner (the sim's business cash settles through the owner's ledger — Session 01 limitation — so the presentation shows the ledger effect, not a separate business balance).
5. **Escheat:** with no living heir in any class, balance and property go to the city (`SYS-CITY` / return to the market). The property re-enters the market as a buyable/rentable unit; it does not vanish.
6. **Headship:** household headship passes (sim: `die()`); the household continues under the new head with its member list intact. No household is ever left headless in data, and no household is dissolved by a death alone — members re-form households only through the sim's own events (marriage, leaving home, relocation).

### 8.3 What inheritance is not

- It is not a windfall mechanic: the heir order is fixed and the shares are equal within a class. The player cannot re-write a will in v1 — no will system is designed anywhere in the merged documents, and this document does not invent one.
- It is not instant wealth on screen: transfers are ledger rows dated to the death's game time. A balance the player sees is the ledger sum, and a cache that disagrees with the ledger loses (GDD-01 §8).

---

## 9. The 3-Generation Accelerated-Time Exit Criteria

The plan's Phase 7 exit criteria (Part D Phase 7), restated as testable checks. A "simulated family" here means a real family in the sim's population — founded by genesis or formed in-run — followed through the sim, not a scripted demo family.

| # | Criterion (plan wording) | Testable form (what passes) |
|---|---|---|
| 1 | A simulated family runs **3 generations** in accelerated time | Starting from a founder household (generation 1 by `generations.generation_of()` — founders = 1, derived from the parent graph), the sim runs at accelerated time scale (TECH-CLOCK-WEATHER §1: the accelerated life-sim test raises `TimeScale`; one in-game day is always one simulation day) until living members of generation 3 exist — i.e. a grandchild of a founder is born and alive — with `generational_history` rows recording the lineage births (`generations.record_history_sweep()`). The run is the same headless engine, not a UE scene. |
| 2 | **Correct inheritance** | Across the run, every death executes the §8 cascade with zero orphaned data: every solely-owned property has a living owner or is back on the market; every positive balance is fully distributed (equal shares + rounding remainder to the city, or escheat); every heir class follows the GDD-01 §6.4 order as implemented in `heirs_in_order()`; no `economy_ledger` row fails reconciliation (Session 01/02 runs: 0 mismatches over 1,790+ rows). "No orphaned data" is checked by query, not by inspection: properties with a deceased sole owner, ledger rows pointing at deleted characters, and households with no head must all count zero. |
| 3 | Stage transitions **never visibly "pop"** | For every variant-boundary transition in the run, the swap is recorded as having fired at a sleep/night boundary behind a presented time-skip (§4) — never mid-day, never while the character is in the player's view, never as a same-frame mesh change. In the headless run this is proven by the transition log (transitions logged by `daily_check()`; presentation boundary enforced by the rule, not by the sim's tick); in the UE build it is proven by the §10 checks. |
| 4 | NPC aging proven **before** player aging (§6) | The three checks above pass on NPC families with the player character's aging still off. Player aging is enabled only after that pass, in a packaged build. |

**Accelerated time, honestly:** acceleration changes only the clock scale, never the rules (GDD-01 §4; TECH-CLOCK-WEATHER §1). A 3-generation run at high `TimeScale` exercises the same `daily_check()`, the same `die()`, and the same ledger as normal play — if a rule only works at 1× speed, it does not work. The run's duration in real minutes is a performance observation to record, not a target to tune the rules toward.

---

## 10. Acceptance Checks (for Phase 7 implementation)

1. **Variant swap discipline:** a Child NPC crossing into Teen, and a Teen into Young Adult, swaps variant only at a sleep/night boundary behind a presented time-skip (§4). A scripted check that forces the transition mid-day must show no visible change until the next qualifying night.
2. **No scaled adults:** no child or teen character in the build is a scaled adult MetaHuman (§3.3). If the child/teen asset gate (§11) is unsolved, those stages are not rendered at all — the check fails closed, not by substitution.
3. **Adult-band continuity:** a Young Adult NPC followed across in-game years into Middle-Aged shows gradual hair-grey, posture, and material-aging change with no threshold event, no swap, and no notice (§5). The face remains recognisably the same person.
4. **NPC-first gate:** all checks above pass with player aging disabled; the player character's visual age is unchanged by NPC transitions (§6).
5. **School loop intact:** a Child NPC's attended `study@school` block writes `subject_knowledge` only, capped at 20 from education sources; a college programme skill caps at 24; no tier-2 unlock (threshold 30) is reachable from education alone (GDD-11 §4, §8 checks 1–3).
6. **Retirement:** a character reaching 65 retires — employment ends, template becomes `elder_day`, a `retirement` life event is logged — and no pension figure is displayed that the data does not own (§7.3).
7. **Inheritance:** a scripted elder death in a test household distributes the balance in equal `inheritance` ledger shares to the correct heir class, passes solely-owned property per the implemented rule (§8.2 step 3), writes heir memories, and leaves zero orphaned properties, ledger rows, or headless households.
8. **Three generations:** the §9 run completes — generation 3 alive, inheritance correct, zero orphaned data, zero ledger mismatches — in accelerated time.
9. **Deceased stay dead:** no deceased character appears in any crowd, schedule, or variant pool after their death event; the family tree shows them as deceased (§2, §8.1).

---

## 11. The Child/Elder Asset Gate — Restated Honestly

The plan's gate (Part C #9, Part D Phase 7, Part J §J.1) stands **unchanged**, and this unit solves none of it:

- **MetaHuman faces/bodies are adult-based. Children and true elderly are not provided** (Part C #1, #9). There is no engine preset, no Creator option, and no asset in this repo that supplies them.
- **No assets are sourced in this unit.** No asset name, no store listing, no price, and no vendor is named in this document, because none was sourced, evaluated, or licensed here. Any future asset list must go through the asset-licence register (`docs/ASSET-LICENCE-REGISTER.md`) with source, licence, and date — the plan's licence discipline (Part H) — and no ripped game assets are ever used.
- **The fallback is fixed by the plan:** if the gate cannot be solved to standard, **the phase ships teen→elder only and says so**. "Teen→elder only" means: the adult MetaHuman band (Teen as the youngest rendered stage, in the plan's wording) through Elder is shipped, and Child — and Infant, which has no presentation by design (§2) — remain data-and-household simulation only, exactly as GDD-01 §3 and GDD-11 §2 already describe for the pre-Phase-7 world. The shipped game says this on the relevant screens (the GDD-09 §2 pattern: the creator says what it cannot do) instead of rendering a substitute.
- **What "solved to standard" means:** responsibly sourced custom child/elder character assets (the plan's words, Part C #9) — licensed, age-appropriate in presentation, built to the variant rules in §3, and passing the §10 checks. A single purchased child model that fails §3.3 does not solve the gate. The gate is a content judgement for the owner, not a checkbox this document can tick.
- **Sequencing consequence:** because the gate is unsolved, Phase 7's UE work that *can* proceed without it is the adult-band aging (§5), the transition protocol (§4, provable on the Teen→Young Adult and Middle-Aged→Elder boundaries), NPC family presentation, and the inheritance presentation (§8) — all of which run on the adult MetaHuman and the existing sim. The child variant work waits for the gate; it is not started speculatively.

---

## 12. Honesty Notes — Contradictions and Gaps Found, Not Papered Over

1. **Property inheritance: design vs sim.** GDD-01 §6.4 says property goes to the eldest resident child with others compensated in credits where possible. The sim (`lifecycle.die()`) implements the simpler rule: the first heir takes solely-owned property, otherwise it returns to the market. These disagree. This document follows the sim's implemented rule for presentation (§8.2 step 3) and records the disagreement here; a later unit must reconcile them (either the design or the sim changes, with a test) — neither may silently claim the other's rule.
2. **Pension figure: sim-only.** The sim pays 3,500 NCr/month (`engine.PENSION_NCR_PER_MONTH`), labelled a SIM ASSUMPTION in code and in the Session 01 report. `prices.json` and GDD-03 define no pension figure. This document does not promote the sim's assumption into a design number (§7.3).
3. **Infant template: fallback, not a design.** The data ships no infant template; the sim uses the `elder_day` home-centred shape for infants (`lifecycle.template_id_for()`), documented in the Session 01 report. This document does not present that fallback as an infant design — infants have no presentation in v1 (§2).
4. **Teacher's school zone: already corrected elsewhere, inherited here.** GDD-06 §4.4's header places the teacher's school in `d1_education`; the data (`professions.json` teacher `workplace_zone: d1_civic`, the `child_school_day` note, GDD-02 §5) puts the school in `d1_civic`, and GDD-11 §1 records that correction with the data governing. This document cites the school as `b_d1_civic_school` in `d1_civic` and does not repeat GDD-06 §4.4's header.
5. **Death probability is a sim model.** `lifecycle.death_probability()` values are a stated sim assumption, not actuarial data (Session 01 report). No mortality number appears in this document as a design fact, and none may be displayed to the player (§8.1).
6. **Conflict escalation is unit-tested, not run-proven** (Session 02 report) — noted because family conflict can touch inheritance disputes in later design; this document designs no inheritance-dispute system and does not imply the escalation path has been observed in a live run.
7. **Part-time teen work and tutoring remain unpriced** (GDD-11 §7; Session 02 limitations). Their *time* costs apply; no wage or fee is shown, charged, or paid for them in Phase 7.
8. **Culture assignment is a configuration hash** (Session 02 report): households keep their culture profile for life; mixing happens only when a person forms a new household. Family presentation in Phase 7 inherits that rule — it does not simulate cultural change within a household.

---

## 13. What This Document Deliberately Does Not Decide

- Which child/elder assets solve the gate, from whom, or at what price — §11 leaves that open by design, and no price is quoted here (no price in this document contradicts `prices.json`, `professions.json`, or GDD-03: the only money figures cited are theirs — owner start 25,000 NCr, Tier 3 rent 6,000/month, Tier 1 rent 2,500/month, outgoings 12,500/month, wages per GDD-03 §2).
- The pension figure — §7.3 (a future economy unit owns it).
- The property-inheritance reconciliation — §12 item 1 (a later unit owns it).
- UE class/function names for the LifeStage system, the variant-swap implementation, or the time-skip presentation — those belong to the Phase 7 implementation units, written against this contract and the existing sim modules, and compiled for the first time on the owner's PC (the plan's standing rule: no UE feature is claimed working until build evidence exists).
- Funeral presentation beyond the family-gathering event that already exists in the sim; wills; adoption presentation beyond the sim's existing guardianship/adoption edges (Session 02 Unit 01 — `kinship.py`, adoption converts sustained guardianship into parent edges flagged `{"adoptive": true}` where the culture profile enables it); and any second-city life-stage content (Phase 8 scope).

---

## 14. Cross-Reference Table — Every Design Element to Its Source

Each row names the already-merged source this design element rests on. If a source below does not exist, the element does not ship.

| # | Design element in this document | Source (already merged) |
|---|---|---|
| 1 | Eight sim stages, age bands, stage derived from age, no stage column | GDD-01 §3; `tools/sim/lifecycle.py` `stage_for_age()` (Session 01) |
| 2 | NPC tiers Full / Scheduled / Ambient; simulation depth per tier | GDD-01 §2; GDD-06 §5; PHASE2-METAHUMAN-SHEET §6 |
| 3 | Player profile card; age derived; account vs character; achievements survive character death | GDD-01 §1 |
| 4 | Personality (5 canonical traits), skills 0–100, reputation, goal stack (max 3), semantic vs episodic memory (cap 200) | GDD-01 §2.1–§2.3; `tools/sim/personality.py`, `tools/sim/memory.py` (Session 01) |
| 5 | Daily tick: schedule → economy → needs → relationship drift → life-events roll | GDD-01 §4; `tools/sim/engine.py`, `tools/sim/scheduler.py` (Session 01) |
| 6 | Households, property model, joining/leaving by events | GDD-01 §5; `tools/sim/households.py` (Session 02) |
| 7 | Kinship edges, directed trust/affection/respect scores, relationship events | GDD-01 §6.1–§6.3; `tools/sim/relationships.py`, `tools/sim/kinship.py` (Sessions 01–02) |
| 8 | Inheritance heir order (spouse → children equal → parents → siblings → city escheat); ledger rows + heir memories | GDD-01 §6.4; `tools/sim/lifecycle.py` `heirs_in_order()`, `die()` (Session 01) — with the property-rule gap in §12 item 1 |
| 9 | Economic class derived from net worth + income band; owner start (25,000 NCr, Tier 3 rent 6,000/month, outgoings 12,500/month) | GDD-01 §7; GDD-03 §1; `data/prices.json` `owner_start_reference`, `rent_monthly_by_tier` |
| 10 | Ledger is the truth; integer NCr; server-only writer in multiplayer | GDD-01 §8; GDD-03 §4.1 |
| 11 | Stage variants as authored assets swapped at thresholds; continuous tweaks inside the adult band (height fixed, hair grey, posture, material aging) | Migration plan Part C #9; GDD-01 §3 |
| 12 | MetaHuman is adult-based; no child/elder presets; child/elder gate; Phase 7 ships teen→elder only if unsolved | Migration plan Part C #9, Part D Phase 7, Part J §J.1; PHASE2-METAHUMAN-SHEET §1, §6; GDD-09 §2 |
| 13 | Transition only at sleep/night boundary with presented time-skip; never a visible pop | GDD-01 §3; migration plan Part D Phase 7; TECH-CLOCK-WEATHER §1 (Night 00:00–05:00, 20:00–24:00; time-skip rule) |
| 14 | Adult-band aging visuals: hair grey, posture, skin-aging material parameters | Migration plan Part C #9; GDD-01 §3 |
| 15 | NPC families first; player aging only after NPC aging proven; player aging opt-in per character | Migration plan Part D Phase 7; GDD-01 §3 |
| 16 | School day, `child_school_day` template, school at `b_d1_civic_school` in `d1_civic`; illness the only absence source | GDD-11 §1–§2; `data/npc-schedules.json` `life_stage_templates`; GDD-06 §4.12 |
| 17 | Education caps: school `subject_knowledge` ≤ 20, programme skill ≤ 24, tier-2 thresholds ≥ 30 | GDD-11 §4; `tools/sim/education.py` `_capped_gain()` (Session 02) |
| 18 | College programmes, credentials, tier-1 unlocks; player "game start" door for civil engineer | GDD-11 §5; `data/professions.json` `progression[].unlock`; `tools/sim/education.py` `has_credential()`, `enrol_college()` (Session 02) |
| 19 | Student hostels, 20 units, Tier 1 rent 2,500/month | GDD-11 §6; `data/prices.json` `rent_monthly_by_tier` (tier 1: 2,500) |
| 20 | Teacher `ClassLoop`, two postings (school `d1_civic`, college `d1_education`); teaching/discipline accrual | GDD-06 §4.4 (read with the GDD-11 §1 zone correction); GDD-11 §3 |
| 21 | Wage bands (Civil Engineer 22,000/38,000/65,000; Teacher 15,000/24,000/38,000; Doctor 30,000/55,000/95,000); tier rises on skill + reputation + time, never money or age | GDD-03 §2; `data/professions.json` `income_band_monthly` |
| 22 | Retirement at 65; `retirement` life event; elder template `elder_day` | GDD-01 §3; `tools/sim/lifecycle.py` `daily_check()` (Session 01); GDD-06 §4.12 |
| 23 | Pension named as income kind, no figure in data; sim's 3,500 NCr/month is a labelled assumption | GDD-01 §3; `tools/sim/engine.py` `PENSION_NCR_PER_MONTH` (Session 01 report) |
| 24 | Age-related health events begin Middle-Aged, strengthen at Elder, feed the death rule; no invented diagnoses | GDD-12 §3.4; GDD-01 §3 |
| 25 | Generations derived from parent graph (founders = 1); lineage; elder knowledge transfer through education caps | `tools/sim/generations.py` `generation_of()`, `lineage()`, `knowledge_transfer()` (Session 02) |
| 26 | 3-generation accelerated-time exit criteria (correct inheritance, no orphaned data, no pop) | Migration plan Part D Phase 7; TECH-CLOCK-WEATHER §1 (`TimeScale`, one in-game day = one simulation day) |
| 27 | Life-stage schedule templates (`child_school_day`, `student_day`, `elder_day`); jitter ±20 min; needs bending; weather interrupts | `data/npc-schedules.json`; GDD-06 §3, §7–§8; `tools/sim/scheduler.py` (Session 01) |
| 28 | Conversation routes for children (never alone with strangers); promotion Ambient → Scheduled only by interaction/event | GDD-06 §4.12, §5–§6 |
| 29 | Creator rules: age never edited, class derived, child/elder not creatable in v1, outfits as data | GDD-09 §1–§3; PHASE2-METAHUMAN-SHEET §5 |
| 30 | 90-day observation evidence (Session 01: 250 alive, 9 births, 1 death, 6 transitions, 0 ledger mismatches; Session 02: 249 alive, 8 births, 1 death, 79 enrolments) | `docs/SESSION-01-REPORT.md`; `docs/SESSION-02-REPORT.md` |
| 31 | No UE code in this document; UE work stays uncompiled scaffold until the owner's PC build | Migration plan Part 0, Part E, Part J §J.2; TECH-CLOCK-WEATHER (status line) |

*End of GDD-13 v1.0.*
