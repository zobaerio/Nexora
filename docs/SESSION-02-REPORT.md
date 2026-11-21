# Session 02 Report — Family, Society & Social Civilization Engine

**Status: COMPLETE (2026-11-21).** All 12 units implemented by
extending Session 01's runnable deterministic sim core at
`tools/sim/` (stdlib only) — no Session 01 module was recreated or
replaced; each unit hooks the systems Session 01 proved. Proven by
49 new automated tests; the full suite is **102 tests, all passing**
(53 Session 01 + 49 Session 02), including the no-regression file:
economy_sim output md5 `16740182867525bd659735deeb05150a`
(byte-identical to the pre-Session-01 baseline), Godot testbed
`PLAYER_TEST_PASS` 8/8, `tools/validate_data.py` green.

**Gate:** Session 02 began only after Session 01 completed and
merged (PR #12, main `8edf8c97`, 53 tests) under the owner's
standing gate rule (2026-11-21 08:32), on the owner's
"BEGIN SESSION 02" order.

## The 12 units

| Unit | Module(s) | What it does |
|---|---|---|
| 01 Family Formation | `kinship.py`, `relationships.py` (history hook) | Extended kinship **derived** from the parent/spouse/sibling graph — grandparents, grandchildren, uncles/aunts, cousins, nephews/nieces, in-laws — never stored, so it cannot go stale. Guardianship for orphans (adult sibling → grandparent → household elder), adoption converting sustained non-kin guardianship into parent edges flagged `{"adoptive": true}` where the culture profile enables it. Every relationship now writes `relationship_history` (formed / status changes). |
| 02 Household Management | `households.py`, decisions | Composition + living conditions read live; membership changes only via life events — Session 01's marriage/birth/death moves plus two new ones: **leaving home** (adult child forms a household in a real vacant unit) and **relocation** (head moves the household), both priced from the canonical buildings data via the property's `building_ref` + `unit_index`. |
| 03 Family Economy | `family_economy.py`, engine settlement | One `household_finances` row per household per month, written from the settlement's own numbers: pooled income, food/housing/transport/other lines from prices.json categories, savings delta vs the members' combined ledger balances. **Education and healthcare lines are 0, deliberately** — civic provision, no fee line exists in prices.json (GDD-11 §7 / GDD-12), and none was invented. Unpaid arrears become persistent household **debt**, repaid at the next settlement before new costs. |
| 04 Social Relationship Engine | `social.py`, `interaction.py` hooks | Colleague (same profession, workplace breaks), neighbour (same zone) and rival (repeated real conflicts only) edges; per-edge `social_profiles`: familiarity, conflict level, interaction count — all updated from actual encounter outcomes. Strength is derived, never stored. |
| 05 Community Engine | `community.py` | One community per District 1 zone (10), membership synced to residence weekly (relocation/leaving-home move membership automatically), participation measured from recorded social acts, leadership read from the respect graph, issues **derived** from facts (indebted households, crowding, low participation). Facilities from the buildings data. |
| 06 Social Interaction Engine | `social.py` (gatherings), `events.py` (visits) | Weekly neighbour gatherings per zone (bounded pairs, new edges + memories + life events), family visits inside Unit 09 gatherings, helping/discussion carried by the existing encounter machinery with the new dynamics recorded. |
| 07 Culture & Tradition | `culture.py`, `data/culture-profiles.json` | Culture is **configuration**: profiles (language, traditions, festival calendar, knowledge-transfer parameters, `adoption_enabled`) load from a new data file; two profiles ship, differing in language/festivals/traditions, proving nothing is hardcoded to one country. Household assignment is a stable hash (~85% default profile — a stated sim configuration choice). |
| 08 Education & Social Development | `education.py`, lifecycle + decisions + engine hooks | School enrolment sweep (District School, from buildings data); attendance **measured** from persisted schedules; performance = attendance + real skill + parent involvement (teacher parent strongest — inequality is carried, not hidden). GDD-11 caps enforced (school ≤ 20, college programme ≤ 24, both below every tier-2 threshold ≥ 30). College enrolment is a stage goal; enrolled students run `student_day`; completion at the cap grants the credential, and hiring into civil_engineer/doctor/teacher/software_developer now **requires** it. Genesis professionals are grandfathered. |
| 09 Social Events | `events.py`, engine hooks | Wedding and birth celebrations follow the actual life events (once per pair), festivals fire on their culture-calendar day for that culture's households, monthly public meetings per community discuss its top derived issue, family gatherings bring extended kin together and honour the elder-respect tradition. All events: real participants, real zones, consequences in memories/emotions/scores. |
| 10 Social Conflict & Resolution | `conflicts.py` | Conflicts are **diagnosed**: a record opens only when a pair's measured conflict level crosses 40, with the cause read from circumstances (either household in debt → resource dispute; affection ≤ −20 → relationship strain; else misunderstanding). Mediation by the community leader, an empathetic mutual friend, or a family elder; success odds from empathy + patience; resolution halves conflict levels and restores trust/affection; three failed attempts escalate. 30-day cooldown — no conflict spam. |
| 11 Social Mobility | `mobility.py`, decisions (relocate) | Monthly status bookkeeping over real outcomes: economic band (economy_sim's own `band_for` on current wage), career tier, education level — changes written to `status_history` + life events, in both directions (promotion up, job loss down) by the same mechanism. Relocation is the physical side: the head's rent-burden decision (Unit 02 machinery). |
| 12 Generational Development | `generations.py` | Generation index derived from the parent graph (founders = 1); ancestors/descendants lineage queries; `generational_history` persists lineage births, inheritances (from Session 01's death cascade) and knowledge transfers. Monthly, an elder living with children teaches them the elder's strongest skill — through education's capped accrual, so a teacher-grandparent's subject knowledge still respects the school cap. |

**Observation (no fabricated dashboards):** `tools/sim/observation.py`
+ CLI — `--inspect <id>` (profile, family tree, social network,
mobility, lineage, generational history), `--household <id>`
(composition, conditions, finances + history), `--community <zone>`
(population, leader, issues, facilities), `--society` (overview).
Every field is read from live rows at call time.

## Database changes

No changes to `data/schema.sql` (Phase 9 PostgreSQL design, as in
Session 01). The SQLite schema grew **additively only**
(`CREATE TABLE IF NOT EXISTS` — existing worlds open unchanged):
`relationship_history`, `social_profiles`, `household_finances`,
`household_state`, `communities`, `community_members`,
`household_culture`, `education_records`, `social_events`,
`conflict_records`, `status_history`, `generational_history`.
Each is a structure schema.sql lacks — recorded here as gaps for a
future schema revision, same discipline as Session 01. One new
data file: `data/culture-profiles.json` (Unit 07 configuration).

## Test results (actual output)

```
$ python3 -m unittest discover -s tools/sim/tests -t .
Ran 102 tests in ~38s
OK
```

New files: kinship 5, households 5, family_economy 3, social 5,
community 4, culture 5, education 6, events 5, conflicts 4,
mobility/generations 5, session02 acceptance 2.

Acceptance mapping (the session's verification list): family
creation ✓ (kinship graph tests); relationship consistency ✓
(derived-not-stored asserted at unit + engine level); household
membership changes ✓ (leave-home/relocation/marriage/birth/death
paths); family financial transactions ✓ (engine test: every active
household has month 1–2 accounts, ledger reconciles); social
network development ✓ (276 neighbour edges after 90 days);
community participation ✓ (weekly update + participation from
recorded acts); cultural event execution ✓ (festival fires on day
45 of the run); education integration ✓ (enrolment, measured
attendance, caps, credential gate — including the GDD-11 check
that skill alone cannot open a gated profession); social event
participation ✓; conflict resolution ✓ (mediation, escalation,
cooldown); generational history persistence ✓; integrity after
restart ✓ (30 days + reopen + 30 days ≡ 60 uninterrupted, with
every Session 02 cadence active); Session 01 suite green ✓;
economy_sim md5 unchanged ✓; Godot 8/8 ✓.

## Performance observations (real numbers, this VM)

- Full starter population 242 agents × 90 days (incl. generation):
  **39.8 s** total (~0.44 s/day) — Session 01's same run was
  17.8 s; the weekly/monthly society cadences roughly double the
  cost, still ~135× under the audit's 60 s bar for a *30-day* run
  at 100 agents. Session 02 acceptance run (120 × 90 days +
  100 × 120 days of restart checks) completes in ~21 s.
- All Session 02 passes are bounded batch sweeps (weekly:
  neighbours/communities/conflicts/guardianship; monthly:
  education/events/mobility/generations) — no per-tick full scans
  were added.
- No claim is made about larger populations, as before.

## 90-day observation run (seed `nexora-1`, population 242)

Day-90 summary: 249 alive (8 births, 1 death with inheritance),
99 households, ledger 1,796 rows with **0 mismatches**. Society
layer: 276 neighbour meetings and 276 neighbour edges, 39 social
events (wedding/birth celebrations, the day-45 River Festival with
48 festival-celebration life events, monthly public meetings —
117 community-meeting life events), 79 school enrolments (77 still
enrolled at day 90, 2 school completions), 60 status changes,
9 knowledge transfers, 15 household-months of financial distress
feeding **10 households in debt** at day 90, 2 young adults left
home, 10 households moved home (relocation + marriage merges),
3 marriages formed in-run (6 marriage life events), **0 open
conflicts** at day 90 — the conflict machinery ran weekly; pairs
that heated up were mediated or cooled below threshold before
escalating in this run (the escalation path is unit-tested, not
run-proven — stated plainly).

## Known limitations (honest list)

- **Non-residential zones have empty communities.** Membership
  follows residence; the buildings data puts no homes in
  d1_civic / d1_industry / d1_transport / d1_park, so those
  communities exist with facilities and zero residents. Workplace-
  based membership is a future refinement, not faked here.
- **Emergencies are arrears, not purchases.** prices.json has no
  priced emergency goods, so a family's emergency month appears as
  unpaid bills → debt, never as an invented expense line.
- **College completion requires reaching the skill cap (24)** via
  study accrual — a student who stops attending stalls (their
  attendance record shows it); there is no time-based graduation.
- **Part-time teen work and tutoring markets remain unpriced**
  (GDD-11 §7 open items) and therefore unimplemented — no invented
  wages.
- **Conflict escalation is unit-tested but did not occur** in the
  90-day observation run (see above).
- **Culture assignment is a configuration hash**, not simulated
  cultural change: households keep their profile for life; mixing
  happens only when a person forms a new household (Unit 02),
  whose assignment is drawn fresh.
- **Community leadership** is recomputed weekly from the respect
  graph; there are no elections — government/politics remains
  ABSENT per the audit, untouched by this session.
- Income timing, pension assumption, and the other Session 01
  limitations stand as recorded there.

## Remaining work

None inside Session 02's scope. Under the owner's standing gate
rule (2026-11-21 08:32), **Session 02's gate obligations are met**:
every unit is implemented and test-proven, and the full suite —
Session 01 included — is green. No later session has been started.
