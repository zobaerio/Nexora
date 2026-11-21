# Session 01 Report — Autonomous Human Intelligence & Life Simulation Engine

**Status: COMPLETE (2026-11-21).** All 10 units implemented as a real,
runnable, deterministic Python simulation core at `tools/sim/` (stdlib
only), proven by 53 automated tests. This session is also the audit's
**Unit AD — Headless Simulation Core v1** (`docs/AUDIT-AND-CHECKLIST.md`);
its 9 completion criteria were adopted into the acceptance suite.

**What this is — and is not.** The sim is the headless behavioural core
the UE/save design maps onto. It is not a UE system: the UE layer is
untouched by this session, and nothing here claims a UE feature works.
Before this session, the audit classified only the Godot testbed and the
economy balance simulator as REAL, and the economy sim is a static
balance checker (no agents, no tick). This engine is what turns the
behavioural layer REAL: persistent people living scheduled lives in the
merged District 1 data. All simulated data is labelled simulated; the
world's people, names and events are generated fiction inside the sim's
own database, never presented as real-world facts.

## The 10 units

| Unit | Module | What it does |
|---|---|---|
| 01 Identity | `identity.py` | Unique persistent identities: Human ID (`NEX-000001`), names, derived age (never stored), sex, birthplace, nationality, family background, GDD-01 goal stack; `profile_card()` reads the live character card from DB rows |
| 02 Personality | `personality.py` | 12-attribute profiles (bell-curve + documented profession affinities ≤ ±12); GDD-01's 5 canonical traits **derived** by fixed mapping — one personality, two views; drift clamped to ±6/event; compatibility function |
| 03 Memory | `memory.py` | Episodic memory (Full tier only, cap 200, weakest-forgotten-first by \|weight\| × recency), semantic memory as flags on relationship edges, one world life-event log |
| 04 Daily Life | `scheduler.py` | GDD-06 template instantiation: fixed per-NPC jitter (±20 min), Friday/Saturday weekend rules transcribed from the data's free-text variants, needs bending (§8), weather interrupts (§7), decision-set rest days; blocks always cover the day exactly once |
| 05 Needs | `needs.py` | 10 needs as satisfactions changed only by simulated activity (per-hour effects, meals in home blocks, social anchors) and daily facts (balance vs costs, age, housing tier, storms) |
| 06 Emotions | `emotions.py` | 9 emotions; **event-driven deltas only** (job loss → stress +30/happiness −20; goal complete → happiness +25; family death → sadness +50), scaled by emotional sensitivity, regressing to personality baselines |
| 07 Family & Relationships | `relationships.py` | Directional persistent edges (trust/affection/respect, semantic flags), marriage with household merge, childbirth joining the family graph, weekly drift |
| 08 Decision-Making | `decisions.py` | Utility decisions from personality + needs + emotions + memory + relationships + goals + resources; one per adult per day, all logged with factors; each changes real state (hire, promotion, business founding, home purchase, marriage, children, socialising, rest, training) |
| 09 Life Cycle | `lifecycle.py` | Stages derived from age; transitions logged; retirement at 65; death with the full GDD-01 §6.4 cascade — employment ends, headship passes, balance/property/business move by heir order (spouse → children equal shares → parents → siblings → city escheat), family grief as events/memories/emotions |
| 10 Interaction | `interaction.py` | Co-located encounters (same minute, zone, anchor): bonding, friendship formation, partnership formation (affection ≥ 55 between unmarried adults), conflicts between clashing impatient pairs, household family time |

Engine, population, persistence: `engine.py` (tick = schedule-block
boundaries + daily rollover — scheduled updates, never per-frame),
`population.py` (District 1 starter population from merged data only:
households into the 140 real residential units, all 11 professions
guaranteed, genesis balances as ledger `seed` rows), `persistence.py`
(SQLite; the file IS the save), `__main__.py` (CLI), `rng.py` (stateless
hash-keyed streams — no RNG state exists, so save/restore cannot drift).

## Canonical sources (one source per fact)

Wages and pay schedules from `prices.json wages_monthly` (the same
source economy_sim uses, so the engines reconcile); profession metadata
(starting balances, progression, skills, workplace zones) from
`professions.json`; cab rental from `prices.json taxi_fares`; living
costs, tax brackets, business models from `prices.json`; economy
arithmetic **imported** from `tools/economy_sim.py` (`monthly_tax`,
`business_pnl`, `band_for`, `CAR_PROFESSIONS`) rather than re-derived.
Employment tiers run 1–5 (progression) over three wage bands — tiers
3–5 are mastery ranks paid at the senior band (`WorldData.TIER_WAGE_KEYS`).

## Database changes

No changes to `data/schema.sql` (it remains the Phase 9 PostgreSQL
design). The SQLite schema mirrors its tables/columns wherever the sim
exercises them. **Sim-only structures schema.sql lacks** (recorded here
as gaps for a future schema revision): tables `personality_profiles`,
`needs_state`, `emotional_state`, `life_events`, `decision_log`,
`agent_state` (incl. a `life_stage` cache column), `instantiated_schedules`,
`daily_weather`; columns `characters.is_system / first_name / last_name /
birthplace / nationality / family_background`. One functional gap the
other way: `properties` has no rent column for vacant units, so a
move-house decision cannot be priced honestly — it is **absent** from
Unit 08 rather than faked (buy-home is implemented; the owned unit's
price is on its property row).

## Test results (actual output)

```
$ python3 -m unittest discover -s tools/sim/tests -t .
Ran 53 tests in ~12s
OK
```

Per file: acceptance 5, decisions 5, emotions 5, identity 4,
interaction 3, lifecycle 5, memory 4, needs 4, no-regression 2,
personality 4, relationships 5, scheduler 7.

Acceptance mapping — owner's 12 criteria: multiple individuals ✓
(population test: ≥100 agents, all 11 professions, children/students/
elders present); persistent identity ✓; personality-differentiated
behaviour ✓ (identical situation, ambition 95 trains vs ambition 15
socialises — asserted, not claimed; plus the profession-affinity
statistical test); routines execute ✓ (coverage for all 14 templates);
needs change with activity ✓; emotions respond to events ✓ (incl. the
owner's three examples); relationships persist ✓ (marriage/childbirth
graph tests + save/restore identity); decisions change world state ✓
(employment row, tier/wage, property ownership, ledger); life-cycle
transitions incl. death side-effects ✓ (inheritance order, equal
shares, escheat, headship, grief); data survives restart ✓ (15 days +
reopen + 15 days produces a summary **identical** to 30 uninterrupted
days); no existing functionality broken ✓ (economy_sim output md5
`16740182867525bd659735deeb05150a` — byte-identical to the pre-session
baseline; Godot testbed re-run: `PLAYER_TEST_PASS` 8/8; committed
`tools/validate_data.py` passes — the audit's first milestone);
performance ✓ (below).

Audit's 9 Unit AD criteria: validation gate committed ✓; determinism
(same seed → identical summaries) ✓; ≥100 agents spanning all
professions + child/student/elder ✓; schedule coverage (engine asserts
1,440 minutes per agent per day; persisted blocks verified) ✓; economy
reconciliation ✓ (a lone entry-tier teacher at the canonical rent nets
**exactly** economy_sim v2's figure within 2 NCr — the household scaling
reduces to the reference model for one adult); weather coupling ✓
(storm suspends construction work, rain drives cover-seeking — unit
tests on effect flags, plus ≥3 distinct presets over 10 engine days);
save/restore identity ✓; performance ✓; committed tests ✓.

## Performance observations (real numbers, this VM)

- 100 agents × 30 days (incl. population generation): ~2.5 s
  (audit bar: < 60 s).
- Full starter population 242 agents × 90 days: 17.8 s total
  (~0.19 s/day at 242 agents).
- No claim is made about larger populations; scaling beyond a few
  hundred agents would need the tiered-update design (Full/Scheduled/
  Ambient) exercised harder — Ambient agents have no inner life by
  design (GDD-06 §2) and are not simulated here at all.

## 90-day observation run (seed `nexora-1`, population 242)

Day-90 summary: 250 alive (9 births, 1 death — an elder, whose balance
passed by inheritance), 99 households, ledger 1,790 rows with
**0 reconciliation mismatches**. Life events: 248 new friendships,
1 partnership and 1 marriage formed in-run (each logs one row per
partner), 9 births (18 childbirth rows — one per parent), 46 promotions, 12 job gains, 24
household-months of financial distress (~8% — pressure exists, the
economy does not collapse), 6 stage transitions. Decisions over the
quarter: train 2,262, have_child 87, promotion 46, seek_employment 12,
marry 1. Average happiness 74.8 / stress 23.1 — happiness drifts high
(friendship and payday effects are frequent); noted, not hidden.

## Known limitations (honest list)

- **Income timing simplified:** economy_sim models daily/per-fare pay
  timing; the core settles all income monthly. Monthly amounts match
  (reconciliation proves it); intra-month balance trajectories differ.
- **Pension = 3,500 NCr/month is a SIM ASSUMPTION** — the merged data
  defines no pension figure (GDD-01 names the income kind only).
- **Template fallbacks:** the data ships no unemployed or infant
  template; both use the elder_day home-centred shape (documented in
  `lifecycle.template_id_for`).
- **Move-house decision absent** (properties rent gap, above).
- **Business cash** settles through the owner's ledger; the
  `businesses.balance_cached` column is not separately maintained.
- **Transport band fallback:** prices nulls inapplicable band cells
  (no public price at upper band); mixed households fall back to the
  nearest defined band (`engine._banded`).
- **Pilot has no District 1 workplace** (pre-existing data gap — no
  airport in District 1); pilots follow their schedule template with
  the home zone as workplace anchor.
- Mortality rates, conception probability (0.18/month), and the taxi
  weather-demand factor are stated sim models, not data — each is
  documented at its definition site.
- Friday/Saturday rules are faithful transcriptions of the data's
  free-text `weekend_variant` notes (documented in `scheduler.py`).

## Remaining work

None inside Session 01's scope. Under the owner's standing gate rule
(2026-11-21 08:32), **the Session 02 gate is now open** — Session 02
(Family, Society & Social Civilization Engine) starts only on the
owner's order.
