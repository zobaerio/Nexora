# NEXORA — GDD-12: Health & Hospital

**Unit AC · Version 1.0 · 2026-11-21**
**Parent documents:** `docs/GDD-01-LIFE-AND-DATA-MODEL.md` §3 (health events begin at Middle-Aged; death is probability-driven from elder stage + health events), §4 (the daily tick — illness enters through the step-5 life-events roll, and health is *not* a fifth need), §2.3 (memory — treatment is an episodic event), §8 (the ledger) · `docs/GDD-06-NPC-BEHAVIOUR.md` §4.3 (the doctor's sub-states — this document is their living detail), §6 (conversation & memory hooks), §7 (weather effect flags), §8 (needs bending — clinic visits and recovery are template edits of the same kind) · `docs/GDD-02-RUPSHA-CITY-DISTRICT1.md` §5 (the clinic interior), §6 (civic properties are city-owned), §8 ("no hospital tower — clinic only") · `data/buildings-district1.json` (`b_d1_civic_clinic`) · `data/professions.json` (`doctor` — NPC-run in v1, "health events for the district's families") · `data/npc-schedules.json` (the `doctor` template; the life-stage templates whose days illness interrupts) · `data/weather-presets.json` (`gameplay_effects` — the exposure and road-risk flags) · `docs/GDD-07-VEHICLES-AND-TRAFFIC.md` §damage-lite (there is **no** pedestrian-harm system in v1) · `docs/GDD-08-CONSTRUCTION-SYSTEM.md` (stage inspections carry the safety check) · `docs/GDD-11-EDUCATION.md` §2 (illness is the only designed source of school absence) · `data/prices.json` (verified for this unit: it contains **no** medical, clinic or medicine price line — the only "medical" string in the file is the doctor's uniform in the clothing table)
**Status:** DESIGN ONLY. No health system exists yet; the clinic interior is not built. This document is the contract Phase 6/7 implements against.

> **Design law:** health is *a condition with a cause, a course and a memory* — never a random punishment and never a fifth need bar. Every condition in the world names the designed system that caused it, runs a course measured in days, and is remembered by the people it touched. If a condition cannot name its cause system, it does not occur.

---

## 1. The Facility — A Clinic, Not a Hospital

District 1's only medical facility is the **district clinic**, `b_d1_civic_clinic` in `d1_civic` — interior: reception + 2 rooms (GDD-02 §5). GDD-02 §8 is explicit: **no hospital tower**. This document designs to that scope, not around it:

- The clinic handles consultation, diagnosis, minor treatment and stabilisation — everything in §3's Minor and Injured bands, and the first response to Serious.
- **Serious cases beyond clinic capability are referred off-district**: a transfer event takes the character off-map for their treatment days (the same honest off-map pattern GDD-06 §4.11 uses for pilots on rotation) and returns them in the Recovering state. No document may cite a District 1 hospital ward, surgery or ICU until a district that contains one exists.
- The clinic is a civic property (GDD-02 §6: city-owned, never for sale) staffed by doctor-profession NPCs. The doctor profession is **NPC-run in v1** (`professions.json`: `playable_in_v1: false`, clinic "fully staffed by NPCs") — the player is a *patient* in v1, and the playable-doctor loop is a later phase's design, not this one's promise.

## 2. The Health State — A Condition Layer, Not a Need

GDD-01 §4 fixes the four needs (rest, food, social, security). Health is **not** added to them. Instead, each character carries at most one active **condition** as simulation state alongside their stage-derived facts:

| State | Meaning | Schedule consequence |
|---|---|---|
| *(none)* | Well. The default; no state stored. | — |
| `unwell` | Minor illness (fever, infection, exposure sickness). | Rest-bending (GDD-06 §8): leisure drops, sleep extends; school absence if a child (GDD-11 §2). |
| `injured` | Minor injury (sprain, cut, fall). | Work block replaced or shortened by severity; movement speed scaled (elder rule of GDD-06 §4.12 applies the same mechanism). |
| `serious` | Condition the clinic must treat; off-district referral possible (§1). | Day becomes a clinic/transfer day; household notified (a relationship event, GDD-01 §6.3). |
| `recovering` | Treated, inside the recovery window (§4). | Home blocks are recovery blocks; work/study resume at window end. |

A condition records: **cause** (one of §3's closed list), **band** (above), **start day**, **recovery window**, **treated flag**. Conditions are written by the life-events roll (GDD-01 §4 step 5) and by nothing else — the simulation stays explainable, and a player inspecting a character can always be told *why* they are ill. Chronic/recurring conditions exist only as the Middle-Aged+ health-event weighting of §3.4 — data-level, per GDD-01 §3 — not as a separate disease catalogue, and this document invents no named diseases: conditions are bands and causes, not diagnoses with Latin names.

## 3. Causes — The Closed List

A condition may only arise from a system this project has already designed:

| # | Cause | Source system | Weighting |
|---|---|---|---|
| 3.1 | **Weather exposure illness** | `weather-presets.json` flags + GDD-06 §7: a character whose day ran under `rain`/`storm` presets — especially one whose `SeekCover` interrupt fired or whose work is outdoor (construction, patrol) — rolls for `unwell` at the daily tick. | Elders and children weighted higher (stage weighting, GDD-01 §4 step 5). Snow-zone flags never fire in District 1. |
| 3.2 | **Commute incident (minor injury)** | The road-risk flags `road_grip_down` (`rain`), `traffic_speed_down` + `visibility_down` (`fog`): characters in `Commute`/`mobile` states on flagged days roll for `injured` (minor band only). | **Event-level, never physics.** GDD-07 is explicit: v1 has no pedestrian-harm system and a vehicle hitting a character is a hard stop, not an injury simulation. This cause is a data-level life event for people *travelling* on bad days — a rickshaw fall in the rain — not a collision outcome, and it never applies to a character struck by a vehicle. |
| 3.3 | **Construction site accident** | GDD-08: characters whose work anchor is an active staged build. The stage inspection *is* the safety check (GDD-08) — a stage whose inspection was **skipped** carries a materially higher accident weight for its crew. | `injured`, rising to `serious` only for foundation/frame stages. This is the human price of the flagship loop's shortcut: skipping inspection is a money decision with a body attached, and the affected worker remembers who supervised the site (GDD-06 §6 episodic memory — the loop's reputation consequence made flesh). |
| 3.4 | **Age-related health events** | GDD-01 §3: health events begin at Middle-Aged (50–64, data-level) and strengthen at Elder (65+). | The only cause that produces `serious` without an external trigger, and the input to GDD-01 §3's death rule: death probability reads elder stage **plus active/recent serious conditions** — health events feed the rule, they never replace it, and death is still announced as an event with inheritance and memories (GDD-01 §3, §6.4), never a silent deletion. |
| 3.5 | **Complications** | An untreated condition (§4) rolls at window end: minor conditions usually self-clear; a failed roll escalates one band. | The mechanism that makes treatment a decision instead of a formality — and makes the clinic's existence matter to NPC households, not just the player. |

**Deliberately excluded:** food poisoning / water quality (no food-safety system exists anywhere in the merged design), epidemics (no contagion model; an epidemic would be an authored event, not a system), workplace illness for indoor professions beyond §3.1 exposure (desk workers get weather and age causes like everyone else), and any cause invented for drama. The list is closed; a new cause arrives only with the system that causes it.

## 4. The Course of a Condition — Diagnosis, Treatment, Recovery

1. **Onset (daily tick).** The life-events roll writes the condition. The character's next day is bent (GDD-06 §8 mechanics): `unwell`/`injured` insert rest; any band can insert a **clinic visit block** into the longest home/leisure block; `serious` replaces the day outright.
2. **The clinic visit.** During a doctor session (§5), the patient joins the doctor's `ConsultLoop` as a *Scheduled patient* (GDD-06 §4.3's own definition: "patients = Scheduled NPCs with illness events"). Ambient patients in the waiting room are visual only and consume no diagnosis — GDD-06 §4.3 fixes this and it is not renegotiated here.
3. **Diagnosis.** The doctor's `diagnosis` skill is checked against the condition's band: success sets the correct recovery window; failure (low band vs low skill) sets a *longer* window and a re-visit — the "diagnosis puzzles" of the profession's gameplay summary, run NPC-side in v1. Diagnosis writes `diagnosis` and `medicine` experience for the doctor (§5).
4. **Treatment.** A diagnosed condition is `treated`: its recovery window is the treated window (shorter), and complication rolls (§3.5) stop. Treatment is a clinic act, not a purchase — there is nothing to buy (§6).
5. **Recovery.** The window runs in game days: indicative tuning — `unwell` 1–3 days treated (3–6 untreated), `injured` 3–7 treated, `serious` 7+ including any off-district transfer days. Windows are tuning; the *shape* (treated < untreated, escalation only via §3.5) is the contract. At window end the condition clears and the character writes an episodic memory of the episode — including who treated them (GDD-01 §2.3), which is what later moves that doctor's greeting band (GDD-06 §6). Recovery happens in home blocks: GDD-10's home is where the recovering character actually is, and household members' relationship drift (§GDD-01 §4 step 4) reads the episode like any shared event.

**Player characters** run the same course — visit during a session, get a window, bend their days — with one scoped decision, stated plainly: **this document adds no player death.** A player who reaches the clinic is always stabilised; an untreated player `serious` escalates to a longer forced recovery, not to death. That is consistent with GDD-01 §3 (player aging itself is opt-in; the death rule belongs to the NPC life cycle) and is a decision of this document, open to the owner's revision — not a fact discovered in the data.

## 5. The Doctor's Loop — The Other Side of the Desk

The doctor's machine is GDD-06 §4.3 (`Rounds → ConsultLoop → Break → ConsultLoop`); this document fixes its content against the `doctor` template (clinic sessions **08:15–13:00** and **14:30–20:00**, break at home, per `npc-schedules.json`):

- **`Rounds`** opens the morning session: yesterday's `serious` and still-active patients are re-read — follow-up flags for today's `ConsultLoop`, and the memory check (the doctor remembers their patients the same way patients remember them, GDD-06 §6).
- **`ConsultLoop`** consumes the session's Scheduled patients in arrival order: diagnose (§4.3), treat (§4.4), set windows. Each completed consultation writes `medicine` + `diagnosis` experience — work accrual, the same pattern as GDD-11 §4's classroom accrual.
- **Night calls** arrive only as life events (GDD-06 §4.3) — a `serious` onset in the doctor's own neighbourhood overnight inserts a home-visit block; there are no random ambushes. The template's weekend variant (rotating: 1 weekend in 3 on emergency call) is the same mechanism at week scale.
- **Progression is read from data:** Intern → Medical Officer at Medicine 35 → Senior Medical Officer at 60 → Specialist at Medicine 75 + specialisation study → Chief Physician / Own Clinic at Medicine 90 or clinic capital (`professions.json`). The tier-5 "Own Clinic" path is noted honestly: civic properties are never for sale (GDD-02 §6), so an own-clinic business needs a *commercial* property from the buildings stock — the profession gate and the property system already allow reading it that way, and no rule here contradicts it.
- **The doctor is also a character:** §3's causes apply to doctors (exposure on a home visit, age events at stage) — a sick doctor's sessions are covered by the district's other doctor NPCs or run short; the clinic does not conjure staff.

## 6. Costs — Civic Care, and the Missing Pharmacy

- **Treatment at the district clinic is free at point of use in v1.** The clinic is civic (city-owned, GDD-02 §6) and funded from the city account that `prices.json` `tax` already feeds. The doctor is paid a **wage band** (`professions.json`: 30,000 / 55,000 / 95,000) like every profession — `ConsultLoop` writes **no per-patient ledger rows**, so the economy simulator's behaviour is unchanged by this document.
- **No price line was added to `prices.json` for this unit** — verified by inspection: its `living_costs_monthly` carries no medical line, and none of its other tables price treatment or medicine (the file's only medical entry is the doctor's *uniform* in the clothing table — a clothing price, not a care price). Inventing a consultation fee to look complete would have been a data change wearing a design document's clothes.
- **There is no pharmacy in District 1.** No property in `buildings-district1.json` is one, and GDD-02's interiors list has no medicine shop — so v1 has **no medicine purchases**: treatment is the clinic's act (§4.4), full stop. A pharmacy property + a priced medicine table + household medical budgeting is a coherent **future economy/data unit**, recorded here as an open item (the same honesty pattern as GDD-11 §7's tutoring market). If that unit lands, this section is amended and the simulator re-run — until then, any document citing a medicine price is citing a number that does not exist.

## 7. Interfaces

| System | Interface |
|---|---|
| GDD-11 Education | Illness is the **only** source of school absence: an `unwell`+ child/teen's `study@school` block is replaced by a home/clinic day; attendance and skill accrual simply don't write that day (GDD-11 §2, §4). |
| GDD-10 Housing | Recovery happens in home blocks; a household member's `serious` condition is a household event (notification, drift, memory) under GDD-01 §6.3. |
| GDD-08 Construction | Skipped stage inspection ⇒ higher §3.3 accident weight for that stage's crew; the supervising engineer is the remembered party. |
| GDD-07 Vehicles | §3.2's incident cause reads the same weather flags GDD-07's traffic table reads — one flag vocabulary, two consumers, no collision model added. |
| GDD-04 Missions | The goal-bent mission offers ("become chief surgeon" ⇒ clinic missions, GDD-04) read the doctor progression of §5; nothing here changes mission structure. |
| GDD-01 Death & inheritance | §3.4 feeds the death rule's "health events" term; the rule, the announcement and §6.4 inheritance remain GDD-01's. |

## 8. Acceptance Checks (for Phase 6/7 implementation)

1. Every active condition in a save names a §3 cause; a condition with no cause cannot be constructed.
2. A `rain`-preset week produces measurably more `unwell` onsets among outdoor-work and commuting NPCs than a clear week, and zero from the excluded causes (§3).
3. A construction stage built with its inspection skipped shows a higher crew accident rate than the same stage inspected — across a simulated season, not a single roll.
4. An untreated `unwell` condition can escalate via §3.5; a treated one cannot; both clear or escalate only at window boundaries.
5. A treated patient greets their treating doctor in a warmer band afterwards (GDD-06 §6), and the doctor's `medicine`/`diagnosis` levels grew from the consultations that did it.
6. No ledger row is written by any clinic interaction in v1, and `prices.json` gains no medical line from this design.
7. A `serious` elder's death, when the GDD-01 rule fires, is announced with family notification and inheritance — and the condition history is part of the archived record.

## 9. Honesty Notes

- **Clinic, not hospital** (§1). Surgery, wards and ICUs do not exist in District 1; serious care is stabilise-and-refer, and the referral is an off-map absence, honestly labelled.
- **The doctor is not playable in v1** (`professions.json` says so). This document designs the NPC loop and the *patient* experience; a playable-doctor design that reuses §4's diagnosis rules is future work, not a hidden promise.
- **Health is not a need bar and conditions have no names** (§2). The four needs stay four; diseases stay bands and causes. A named-disease catalogue would be a content unit with medical review, not a paragraph invented here.
- **Care is free in v1 because the clinic is civic** (§6) — a stated design decision on merged data, with the priced-medicine future unit recorded openly. Free care is also why the district's poorest households survive their §3 rolls; pricing care later is an economy decision with balance consequences, and the simulator will have to prove it.
- **Traffic injuries are event-level** (§3.2). Until a real harm model is designed (it is not, in v1), nobody in District 1 is injured *by a vehicle on screen* — the design says so rather than implying a system it doesn't have.
