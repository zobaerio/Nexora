# NEXORA — GDD-11: Education & School Life

**Unit AB · Version 1.0 · 2026-11-21**
**Parent documents:** `docs/GDD-01-LIFE-AND-DATA-MODEL.md` §3 (life stages — school attendance is a Child/Teen system, profession choice a Young Adult one), §4 (the daily tick; study blocks are schedule blocks, illness is a life-event roll), §2.2 (goals — enrolment is a stage goal) · `data/npc-schedules.json` (`child_school_day`, `student_day` life-stage templates; the `teacher` profession template) · `docs/GDD-06-NPC-BEHAVIOUR.md` §4.4 (the teacher's `ClassLoop`), §4.12 (life-stage template rules) · `docs/GDD-02-RUPSHA-CITY-DISTRICT1.md` §2 (zones), §5 (interiors), §6 (civic properties are city-owned), §8 (scope honesty) · `data/buildings-district1.json` (every property id cited here resolves to it) · `data/professions.json` (teacher/doctor/civil_engineer/software_developer progression — the credential gates and tier-2 thresholds are read from it, never restated as new numbers) · `data/schema.sql` (`character_skills`, `character_goals`) · `data/prices.json` (`tax`, `rent_monthly_by_tier` — owns the numbers) · `docs/GDD-10-HOUSING-AND-HOME-LIFE.md` (the hostel stock students live in) · `docs/GDD-12-HEALTH.md` (illness — the only designed source of school absence)
**Status:** DESIGN ONLY. No education system exists yet; no school, college or library interior is built. This document is the contract Phase 6/7 implements against.

> **Design law:** education is *time in a place, recorded as skill*. A character is educated by attending blocks in real institutions, the attendance writes experience into `character_skills`, and profession entry reads credentials — never the other way round. If an education rule cannot be traced to a template block, a property in the data, or a skill row, it does not ship.

---

## 1. The Institutions — What District 1 Actually Has

| Institution | Property | Zone | Interior (GDD-02 §5) | Serves |
|---|---|---|---|---|
| District school | `b_d1_civic_school` | `d1_civic` | 2 classrooms + yard | Child + Teen stages (`child_school_day`) |
| College (College Para) | `b_d1_education_college` | `d1_education` | College building (GDD-02 §2) | Young Adult students (`student_day`), degree programmes (§5) |
| College library | `b_d1_education_library` | `d1_education` | Reading room — "Study/skill gain; student life" | All students; the self-study site (§4) |
| Student hostels | `b_d1_education_hostels` | `d1_education` | Residential, 20 units, students only (GDD-10 §1) | Where out-of-household students live (§6) |

**On "university":** District 1 has a **college, not a university campus**. The College Para college delivers the district's degree-level programmes (§5) — that is the honest reading of GDD-02 §2 ("College building, library, student hostels") and §8 (District 1 deliberately excludes big-ticket institutions). A full university is a later-district institution; no document in this project may cite one in District 1 until a district that contains it exists.

**A recorded correction:** GDD-06 §4.4's header places the teacher's school in `d1_education`. The canonical data disagrees — `professions.json` gives the teacher `workplace_zone: d1_civic` ("District school, Civic Quarter (college lecturers: d1_education)"), the `child_school_day` template note says "Civic Quarter school", and GDD-02 §5 lists the school interior in `d1_civic`. **The data governs:** the school is in `d1_civic`; `d1_education` is the college posting. GDD-06 §4.4 is to be read that way until its next revision.

## 2. The School Day — Child & Teen Loop

The loop *is* the `child_school_day` template, read as systems:

| Block (template) | Time | System reading |
|---|---|---|
| `sleep` → `home` | 21:30 → 07:15 | Household pool (GDD-01 §3): the child has no economy tick of their own. |
| `commute` | 07:15–07:30 | With parent/older sibling or school route (template note). GDD-06 §4.12: a child is never in `Converse` alone with strangers; the commute is a grouped move, not a solo one. |
| `study@school` | 07:30–13:00 | **Attendance.** The child is inside `b_d1_civic_school`'s class anchor group (§3). Each attended block writes experience (§4). |
| `home` | 13:00–16:00 | Midday at home — the district's school day is a morning day by design (matches the teacher template's 07:15–13:30 work block). |
| `leisure@park` | 16:00–18:00 | Play — park or neighbourhood lane. Social need source (GDD-06 §8 bending applies to the household's children too). |
| `study@home` | 18:00–19:30 | Homework / tutor (template note). Counts as a study block at half weight (§4); the tutor variant is §7. |
| `home` → `sleep` | 19:30 → 21:30 | Family evening. |

**Attendance & absence.** Attendance is derived per day from whether the `study@school` block ran. There is exactly one designed source of absence: **illness** (GDD-12 — a life-event roll per GDD-01 §4 step 5, which replaces the block with a home/clinic day). Weather never closes the school in District 1: the `storm` preset suspends *outdoor work* sub-states (GDD-06 §7), and school is an indoor anchor — children commute in the rain like everyone else. No truancy system exists in v1; a child NPC does not skip school by choice, and this document does not invent one.

**Teen variant (13–17).** Same school loop, plus the template family's part-time variant (GDD-06 §4.12): some teens instantiate a `work` block at a market/shop anchor in the afternoon `leisure` slot. Part-time earnings flow into the **household pool**, not a personal wage — `professions.json` wage bands are full profession bands. The part-time/tutoring labour market is **priced in Queue 6 / Unit AH** (§7): 150 NCr per work block, typically 2,400/month into the household pool — below the lowest full profession entry band (construction_worker 9,000).

**The asset gate (inherited, not solved here).** GDD-01 §3: until child character assets exist, children live in data and household simulation but are **not rendered as full 3D characters**. The school loop above is therefore a *simulation* loop in v1 — attendance, skill accrual and family memories all run; the visible classroom population is the teacher plus whichever tiers the asset gate currently allows. This document does not fake a rendered classroom.

## 3. The Teacher Hookup — Two Template Families in One Room

The teacher's day is GDD-06 §4.4's machine (`ClassLoop → Break → ClassLoop`), and this document fixes how it meets the students:

- **The class anchor group** = the enrolled Child/Teen NPCs (Full + Scheduled tiers) whose `study@school` block overlaps the teacher's `work` block (07:15–13:30 vs the child's 07:30–13:00 — the overlap is the lesson). A teacher with no overlapping students still runs `ClassLoop` (preparation, empty-room honesty) — the machine never waits for an audience.
- **The teacher's home `study` block** (16:30–18:30, "Marking, lesson prep; some teachers tutor in college_para") is the teacher's own accrual block: it writes `teaching` experience (§4) and is where the §7 tutoring variant attaches.
- **College lecturers** are teacher-profession NPCs whose workplace anchor is `b_d1_education_college` (per the `professions.json` workplace note). They run the same `ClassLoop` against `student_day` `study@college` blocks. One profession, two postings, zero new code paths — the anchor differs, the machine doesn't.
- **Progression is read from data:** Assistant Teacher → Teacher at Teaching 30 → Senior Teacher at 55 → Head of Department at Teaching 70 + discipline 55 → Head Teacher / Principal at Teaching 85 + reputation (`professions.json`). `discipline` appears in that tier-4 unlock string; it is a `character_skills` id under the schema's open skill list, accrued from `ClassLoop` blocks run with a full class anchor group — this document names it so the unlock is checkable, and assigns its accrual to classroom time, not study time.

## 4. Skills Progression — How Study Writes `character_skills`

All education writes go to `character_skills` (`character_id`, `skill_id`, `level` 0–100, `experience`) and nowhere else. Skill ids are the vocabulary of `professions.json` `primary_skills` — education never invents a parallel vocabulary.

| Study context | Skill written | Rule |
|---|---|---|
| `study@school` (Child/Teen) | `subject_knowledge` | Foundation skill (the teacher's own second primary skill — what schoolteaching transmits). Accrues per attended block. |
| `study@home` homework (Child/Teen) | `subject_knowledge` | Half weight vs the school block. |
| `study@college` programme blocks (Young Adult) | The programme's primary skill (§5) | Accrues per attended block in the enrolled programme. |
| Library self-study (`b_d1_education_library`) | The character's current programme/foundation skill | The reading room's stated purpose (GDD-02 §5). Same rate as the matching attended block; it is how a student bends a missed day back (GDD-06 §8 rest/social edits apply normally). |
| Teacher `study@home` (marking/prep) | `teaching` | The profession's own maintenance accrual (GDD-06 §4.4). |
| Teacher `ClassLoop` with students present | `teaching`, `discipline` | Classroom accrual (§3). |

**The education caps — the load-bearing invariant.** Education alone can never promote anyone. Schooling caps `subject_knowledge` at **20**; a college programme caps its primary skill at **24** from education sources. Both caps sit below the lowest tier-2 skill threshold among the credential-gated professions in `professions.json` (30 — civil_engineer "Engineering skill 30", teacher "Teaching skill 30"; doctor 35, software_developer 35). Tier 2 is therefore always earned *at work*, and a fresh graduate always enters at tier 1. The caps are properties of the education sources, not of the character: the same skill keeps growing past them from work sub-states (GDD-06 §4) with no seam.

**Rates are tuning, caps are contract.** Experience-per-block rates are Phase 6 tuning (a completed school year should land a child visibly inside the foundation band, not at its cap); the caps and the write-targets above are what implementations are tested against (§8).

## 5. Programmes & Credentials — The Profession Gates

A Young Adult (GDD-01 §3: profession choice happens in this stage) enrols in a college programme by taking a **stage goal** (`character_goals`, `goal_kind = 'stage'`) naming the programme — enrolment is a goal the life-sim can want, offer and remember, not a menu flag. Completing the programme's attended study converts the goal to a completed credential fact, checked at profession entry against the tier-1 unlock strings of `professions.json`, tabulated here in checkable form:

| Credential (tier-1 unlock, verbatim) | Profession | Programme site | Programme skill (capped §4) |
|---|---|---|---|
| "Engineering degree / game start" | `civil_engineer` | `b_d1_education_college` | `engineering` |
| "Medical degree" | `doctor` | `b_d1_education_college` | `medicine` |
| "Education certificate" | `teacher` | `b_d1_education_college` | `teaching` (+ `subject_knowledge` foundation) |
| "Programming portfolio / degree" | `software_developer` | `b_d1_education_college` or library self-study portfolio path | `programming` |

Professions whose tier-1 unlock is **not** an education credential (academy pass, driving licence, capital, start-of-work-life) are out of this document's scope by design — their gates live with their own systems. The pilot's licence is Phase 8 content (off-district, per `professions.json`) and no District 1 programme pretends to grant it.

**The flagship stays flagship:** the civil engineer's "game start" alternative in its unlock string is preserved — a *player* civil engineer may start degreed by character creation (the owner's profile card, GDD-01 §1), while NPC engineers earn the degree through this loop. One rule, two doors, both recorded.

## 6. The College Student Loop

The `student_day` template read as systems: `study@college` 09:00–14:00 (programme blocks, §4 accrual), `break@college_para` 14:00–15:00, `study@college` 15:00–17:30 ("Library / group study; some students take part-time work blocks instead" — the part-time variant is the teen rule of §2 one stage up: household-pool or personal contribution, priced per §7, Queue 6 / Unit AH), `leisure@college_para` to 20:00.

**Where students live.** Students from District 1 households live at home; students who have left the parental household (GDD-01 §3 makes this possible at Young Adult) take hostel beds in `b_d1_education_hostels` — 20 units, students only (GDD-10 §1), rent at tier 1 of `prices.json` `rent_monthly_by_tier` (**2,500/month** — the data's number, matching GDD-10's table). The hostel stock is finite like all District 1 housing: when the 20 beds are full, a would-be student stays in the parental household — scarcity is the design (GDD-10 §1), not a spawn error.

**Student money.** Students have no wage band. A hostel student's rent and living costs are paid from the household pool or a personal balance (part-time variant, §2) — every movement a ledger row (GDD-01 §8). If neither covers the rent, GDD-10's missed-rent ladder applies to students exactly as to anyone; the ladder does not check enrolment status.

## 7. Costs — What Education Charges, and What It Deliberately Doesn't

- **District school and the college are civic institutions.** GDD-02 §6: civic properties are city-owned and never for sale. Their funding is the city account — the same account `prices.json` `tax` already pays into ("Deducted at pay time to the city account"). **v1 therefore adds no per-student fee line to `prices.json`, and the economy simulator's behaviour is unchanged by this document** (no prices were touched for this unit).
- **The one real price in this document is the hostel rent** (§6), which resolves to the existing `rent_monthly_by_tier` tier-1 line — no new number was created.
- **Tutoring is priced (Queue 6 / Unit AH).** The templates name tutoring twice (the child's homework/tutor block; teachers who "tutor in college_para"), and `prices.json` `tutoring` now prices it: **300 NCr per session** — one 18:00–19:30 homework block (§2) made full-weight for the tutored child, taught in the teacher's 16:30–18:30 study block. The household pays; the teacher keeps it as side-income: typically 8 sessions/month = **2,400 NCr/month**, 16% of a teacher's 15,000 entry wage — a side-income by design, never a second wage band. The economy simulator v3 checks both sides of the trade (`docs/ECONOMY-SIM-REPORT-V3.md`).
- **Part-time student work is priced (Queue 6 / Unit AH).** `prices.json` `part_time_student_work`: **150 NCr per work block**, typically 4 blocks/week = **2,400 NCr/month** into the household pool — below the lowest full profession entry band (construction_worker 9,000). No part-time wage band exists in `professions.json` and none is created; a teen's earnings are household-pool income, not a profession.
- **Books, uniforms, materials:** no lines exist and none are added. The clothing catalogue (GDD-09) already carries the school-uniform mapping for the child/teen outfit context; its prices resolve there, not here.

## 8. Acceptance Checks (for Phase 6/7 implementation)

1. A Child NPC's attended `study@school` block writes `subject_knowledge` experience and nothing else; a missed (illness) day writes nothing and leaves an absence the household can remember.
2. `subject_knowledge` from education sources stops at 20 and a programme skill from education sources stops at 24, while both keep growing from work sub-states past the caps.
3. No character can satisfy any tier-2 profession unlock in `professions.json` using education-sourced skill alone.
4. A Young Adult with a completed Engineering degree goal can enter `civil_engineer` at tier 1; one without it cannot — and the player-character "game start" door (§5) still works.
5. The 21st would-be hostel student stays in the parental household; hostel rent ledger rows read 2,500/month from `rent_monthly_by_tier`.
6. A teacher's `ClassLoop` runs identically with an empty classroom, a child class at `b_d1_civic_school`, and a college class at `b_d1_education_college` — only the anchor and the student set differ.

## 9. Honesty Notes

- **Children are simulated before they are visible** (the GDD-01 §3 asset gate). This document designs the simulation honestly and does not promise rendered classrooms.
- **District 1 has a college, not a university** (§1). Degree *programmes* exist; a university *campus* does not, and later documents must not cite one here.
- **Education is free at point of use in v1 because the institutions are civic** — a funding reading of merged data (city-owned + the tax line), stated as a design decision, not discovered as a fact. If a future economy unit prices education, it must amend this section and re-run the simulator.
- **Tutoring and part-time student work are priced, not free** (§2, §7 — Queue 6 / Unit AH). Their *time* costs already applied in v1; the ledger rows now exist too. What stays open is the matching mechanics — which teacher tutors which child, and which shop takes which teen — Phase 6 implementation, not a price.
- **Templates are not authored lives** (GDD-06 §9 applies unchanged): this document designs the loop every student runs, not any individual student's story.
