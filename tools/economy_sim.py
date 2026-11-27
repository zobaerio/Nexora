#!/usr/bin/env python3
"""NEXORA — Economy Balance Simulator v7 (Unit FB, Queue 23).

Simulates 30 game-days of household cashflow for every profession in
data/prices.json (wages_monthly) at entry / mid / senior tiers.
Deterministic — no randomness; the same input always produces the
same report.

What v7 changes vs v6 (Queue 23, Unit FB — the storm-position
follow-up):
- `simulate()` takes an optional `storm_days` (distinct 1-based
  days of the 30-day month): worked days are 30 minus the storm
  days, gross is band x worked/30 as in v6, and the pay lands
  only on worked days — (gross-tax)/worked per worked day, 0 on
  a storm day — so the month-1 minimum balance depends on where
  the storms fall. The total is still exactly gross-tax, so the
  trajectory still ends at net for every position (pinned by a
  test). A storm_days that disagrees with day_wage_worked_days,
  names a day outside 1..30, or repeats a day is refused; it is
  refused for any non-day-wage profession too. Without
  storm_days the v6 even accrual is unchanged.
- The default run gains a day-wage storm-position section: the
  same measured 28 worked days, with the two storm days early
  (1-2), mid (15-16), late (29-30), and at the measured position
  (4 and 23 — where the live month's storms actually fell;
  Queue 25 Unit HA corrects FB's (3, 22), which were the 0-based
  day indices), plus
  the v6 even-spread baseline for comparison. The net is the same
  for every position; only the month-1 minbal moves, and that is
  now a measured figure per position. The v6 section is unchanged
  (its minbal stays the even-spread figure). The pinned md5 moves
  to the v7 baseline (the v6 md5 is kept in test_no_regression.py
  as history). No tuning call: the storm month is weather, not a
  balance problem.
- Queue 24 adds two follow-ups to v7 (Units GC–GE, same version):
  Unit GC checks the tool against the settlement and finds the
  recorded "measured" position (days 3 and 22) is the 0-based day
  indices — the settlement's storms fall on 1-based days 4 and 23
  (docs/ECONOMY-SIM-REPORT-V7.md §6), and the tool's own model at
  the true position dips entry to −100, not −150. Queue 25 Unit
  HA corrects the constant to (4, 23) and re-pins the md5 (the GE
  md5 is kept in test_no_regression.py as history). Unit GD adds
  the
  two-earner storm-position scenario below; Unit GE wires the
  worst storm-position dip into the bridge check. The pinned md5
  moves again (the v7 md5 is kept in test_no_regression.py as
  history).

  What v7 adds vs v6, Queue 25 Unit HA (the measured-position
  correction):
  - `STORM_MEASURED_DAYS` is (4, 23): the settlement's storms fall
    on 1-based days 4 and 23 (day_index 3 and 22) — FB encoded the
    0-based indices as 1-based days, so the recorded measured
    position was one day early. The tool's own model at the true
    position dips entry to −100, not −150 (mid and senior stay 0);
    the early/mid/late positions and the bridge line are
    unchanged (the worst dip is still the early −500). No
    position is invented: the constant is the settlement's own
    measured storm days, read as 1-based days. The pinned md5
    moves again (the GE md5 is kept in test_no_regression.py as
    history).

What v7 adds vs v6, Queue 25 Unit HD (the mixed-profession
  two-earner scenario):
  - `simulate()` takes a second earner in another profession:
    `second_earner="taxi_driver"` (per-fare pay, entry 14,000)
    or `second_earner="civil_engineer"` (monthly pay, mid
    38,000) — the settlement's measured pairings (V7 §6); the
    second earner's tier defaults to the measured one while the
    first earner varies (Queue 26 Unit IC lets a caller name
    another tier the source data gives — `second_earner_tier`).
    Each earner is taxed on their own gross
    and carries their own lifestyle uplift; the household costs
    follow `engine._living_costs` for two adults (food/clothing
    ×2, transport/eating ×2 per earner, utilities/services/
    medical/rent flat). Storm days do not change the second
    earner's pay — the per-fare rule has no storm days and the
    monthly pay lands on day 30 regardless — so the storm-position
    effect comes from the first earner alone, against the second
    earner's steady pay; the tool says so explicitly rather than
    forcing a storm effect where the pay rule has none. The
    default run gains the mixed-profession section beside the
    same-tier one. The taxi second earner is the owning driver
    (no cab rental — the renting variant is Queue 26 Unit IB,
    `second_earner_renting_cab=True`). The pinned md5 moves
    again (the HA md5 is kept in test_no_regression.py as
    history). No tuning call.

What v7 adds vs v6, Queue 24 Unit GD (the two-earner
storm-position scenario):
- `simulate()` takes an optional `second_earner` (default
  False): a second construction worker at the same tier, on the
  same storm days and the same day-wage rule — or, since Queue 25
  Unit HD, a profession id (`"taxi_driver"` / `"civil_engineer"`)
  for a mixed-profession second earner at the measured tier (or,
  since Queue 26 Unit IC, at a named tier — `second_earner_tier`).
  Gross and tax are
  doubled per earner (each earner is taxed on their own gross,
  as the settlement taxes each earner on what they received);
  the household costs follow `engine._living_costs` for two
  adults — food and clothing scaled ×2, transport and eating out
  scaled ×2 (both are per-earner lines in `_living_costs`),
  utilities / services / medical and rent flat, and the
  lifestyle uplift doubled (the settlement sums it per earner).
  The default run gains a two-earner storm-position section
  beside the single-earner one. `second_earner` is refused for
  any non-day-wage profession and together with the v3
  side-income/expense lines (those belong to one person; a
  two-earner household with side income needs a split this unit
  does not design). No tuning call: the storm month is weather,
  not a balance problem — and the finding here is that a second
  earner does not help the early-position dip at all (no pay has
  arrived for anyone on days 1–2), it only helps once pay starts
  landing.
- Run: python3 tools/economy_sim.py [--shibnagar] [--v3|--v4]

What v7 adds vs v6, Queue 26 Unit IC (the second earner at
other tiers):
- `simulate()` takes `second_earner_tier="mid" | "entry" |
  "senior"` with a mixed second earner: the tier no longer has
  to be the measured one — a mid-tier taxi driver (23,000,
  per-fare) or an entry civil engineer (22,000, monthly) as
  second earner is now modelled, each at the tier the source
  data actually gives (prices.json wages_monthly). The
  default (no tier given) is still the measured tier, so the
  HD/IB sections are unchanged. Refused with the same-tier
  second earner (that case uses the first earner's tier by
  definition) and with no second earner. The pinned md5 moves
  again (the IB md5 is kept in test_no_regression.py as
  history). No tuning call.

What v7 adds vs v6, Queue 26 Unit IB (the renting-cab taxi
second earner):
- `simulate()` takes `second_earner_renting_cab=True` with
  `second_earner="taxi_driver"`: the same entry taxi driver
  (14,000, per-fare), but renting the licensed cab. The rental
  follows the settlement's rule — engine._settle_month charges
  `cab_rental_ncr_per_day` (200) × WORK_DAYS (26) = 5,200/month
  flat for the month, not storm-dependent and not
  Sunday-excluded — and is modelled as a monthly cost line of
  5,200, accruing evenly in the daily model like rent (the
  settlement charges the same 5,200 once at month-end; HE's
  daily model stands). The net drops by exactly 5,200 at every
  tier. Refused with any other second earner. The pinned md5
  moves again (the IA md5 is kept in test_no_regression.py as
  history). Honest limit recorded in the report: the tool's
  single-earner renting-cab row charged the rental via
  extra_daily_cost on days ≤ 26 excluding Sundays (23 days =
  4,600 in the trajectory, while the headline net already
  subtracted the full 5,200) — the two renting rows disagreed
  by 600/month, and reconciling the single-earner row is
  Queue 27 Unit JB, which follows the settlement's 26-day
  charge (see below).

What v7 adds vs v6, Queue 27 Unit JB (the single-earner
renting-cab row):
- DECIDED: the single-earner renting-cab row follows the
  settlement's 26-day charge. The settlement charges
  `cab_rental_ncr_per_day` × WORK_DAYS (200 × 26 = 5,200/month)
  flat — no Sunday exclusion, no storm dependence — and the
  tool's headline net already subtracted that 5,200; only the
  trajectory charged the v1 23-day rule (4,600), so the row's
  trajectory ended 600 above its own net. The v1 rule's Sunday
  exclusion was a leftover of the v5 daily schedule (which paid
  on 23 days); v6 already moved construction pay off that
  schedule, and no source gives the rental a day-of-week rule.
  The trajectory now charges `extra_daily_cost` on days 1–26
  (the sourced WORK_DAYS count) — the row charges exactly
  5,200 in the trajectory and ends exactly at net (1,300). The
  base table's renting row and its bridge line do NOT move:
  minbal stays 0 and net stays 1,300, so the default-run output
  is byte-identical and the pinned md5 does not move (the JA
  baseline stands). Only the row's `end_balance` moves (1,900
  → 1,300), from inconsistent to exact.

What v7 adds vs v6, Queue 26 Unit IA (the two-earner bridge
line):
- The first-month bridge check prints a mixed two-earner line
  for each measured second-earner profession: the combined
  canonical start (each earner brings their own genesis
  balance — population.py seeds starting_balance_ncr per
  profession: construction_worker 5,000, taxi_driver 5,000,
  civil_engineer 25,000) plus the worst mixed minbal (the
  minimum across the first earner's tiers and the four storm
  positions) = the worst mixed storm-month balance. Taxi-driver
  second earner: 10,000 − 72 = 9,928; civil-engineer second
  earner: 30,000 − 8,623 = 21,377. HD's prose (V7 §9) carried
  GD's 2 × 5,000 figure for the CE household too (10,000 −
  8,623 = 1,377), which understates the engineer's start by
  20,000 — corrected here against professions.json. A failing
  mixed line joins BRIDGE FAIL. The pinned md5 moves again
  (the HD md5 is kept in test_no_regression.py as history).

What v7 adds vs v6, Queue 27 Unit JA (the remaining
two-earner bridge lines):
- The bridge check prints the three two-earner lines IA left
  prose-only: the GD same-tier household (a second construction
  worker at the same tier) and the IC other-tier pairings (a
  mid-tier taxi driver, an entry civil engineer as second
  earner). Each line is the combined canonical start (each
  earner brings their own genesis balance — population.py seeds
  starting_balance_ncr per profession: construction worker
  5,000, taxi driver 5,000, civil engineer 25,000) plus the
  worst minbal (the minimum across the first earner's tiers and
  the four storm positions): same-tier 10,000 − 1,231 = 8,769;
  mid-tier taxi-second 10,000 − 0 = 10,000; entry
  civil-engineer-second 30,000 − 3,210 = 26,790. A failing line
  joins BRIDGE FAIL. No two-earner bridge figure is report-only
  now. The pinned md5 moves again (the IC md5 is kept in
  test_no_regression.py as history).

What v7 adds vs v6, Queue 28 Unit KA (the renting-cab second
earner at another tier):
- `simulate()` now accepts `second_earner_renting_cab=True`
  combined with `second_earner_tier` for the taxi driver: a
  renting mid-tier taxi driver (23,000, per-fare) as second
  earner, at the tier the source data actually gives
  (prices.json wages_monthly). The rental is the same flat
  5,200/month (200 × WORK_DAYS 26, the settlement rule JB
  confirmed) whatever the tier — the tier moves the pay, not
  the rental. The bridge check prints the renting mid-tier
  line (the combined canonical start plus the worst renting
  minbal, the minimum across the first earner's tiers and the
  four storm positions), same combined-start rule as IA/JA.
  A renting civil engineer is refused and stays unmodelled:
  civil engineers hold no cab, so there is no rental to
  charge — stated explicitly, not modelled. The pinned md5
  moves again (the JA md5 is kept in test_no_regression.py
  as history). No tuning call.

What v7 adds vs v6, Queue 24 Unit GE (the storm-position bridge
line):
- The first-month bridge check prints a second line for the
  construction_worker entry row: starting balance + the worst
  storm-position minbal (the minimum across the early / mid /
  late / measured positions) = the worst storm-month balance. A
  failing storm line joins BRIDGE FAIL. The storm bridge is now
  part of the tool's output rather than a report-only observation
  (V7 §5: entry 5,000 − 500 = 4,500). The pinned md5 moves again
  (the v7 md5 is kept in test_no_regression.py as history).

What v7 adds vs v6, Queue 31 Unit LA (the single-earner storm
line across tiers):
- DECIDED: the storm line sweeps tiers, like the two-earner
  lines already do (Unit IA). The GE line swept storm positions
  at the entry tier only, so it printed the entry row's worst
  (5,000 − 500 = 4,500) rather than the household's worst across
  tiers: measured per-tier worst dips are entry −500, mid −595,
  senior −726 (early position worst at every tier; the deeper
  senior dip is Unit V's tier-scaled living costs meeting the
  day-wage rule, exposed by the storm position). The line is now
  5,000 − 726 = 4,274 — still OK, so no bridge failure was
  hidden, but the check's stated purpose is the worst month-1
  balance and the entry-only line understated it by 226. The
  start is the same 5,000 at every tier (starting_balance_ncr
  is per profession, not per tier), so the sweep stays one
  household's worst. The Shibnagar variant's storm line sweeps
  the same way on its own rents (identical figures, verified).
  The pinned md5 moves again (the KC md5 is kept in
  test_no_regression.py as history). No tuning call.

What v7 adds vs v6, Queue 32 Unit MA (the renting-cab row at
mid/senior tiers):
- The single-earner renting-cab row is now modelled at every
  tier, not the entry tier alone: the base table gains the
  mid and senior renting rows beside the entry one, each the
  same `simulate(..., tier, extra_daily_cost=cab_rental)`
  call (200 NCr/day x WORK_DAYS 26 = 5,200/month flat, the
  settlement rule JB confirmed — the rental is the same at
  every tier, so the tier moves the pay, not the rental).
  Measured: mid net 6,750 (29.3%), senior net 14,550
  (40.4%) — exactly 5,200 below the owning driver at every
  tier, minbal 0 at every tier, trajectory ends exactly at
  net. Only the entry row is TIGHT (9.3%, net 1,300). The
  bridge check's renting line now sweeps tiers like the
  storm line (Unit LA): the worst minbal across the three
  renting rows against the same 5,000 start — 5,000 + 0 =
  5,000 OK, unchanged in figure, now honestly the
  household's worst across tiers rather than the entry
  row's. The Shibnagar variant gains the same rows and the
  same swept line on its own rents (identical figures,
  verified). The pinned md5 moves again (the LA md5 is kept
  in test_no_regression.py as history). No tuning call.

What v7 adds vs v6, Queue 33 Unit MB (the renting rows in
the surge section):
- The KC taxi weather-surge section printed the renting-cab
  row at the entry tier only, while the base table (Unit MA)
  models it at every tier — the surge deltas at mid/senior
  were prose in V7 §16, not printed rows. The section now
  prints the renting row at every tier, beside the owning
  rows: mid 6,750 -> 7,441 (+691), senior 14,550 -> 15,630
  (+1,080) — exactly the owning driver's deltas, because
  the rental stays the flat 5,200 unsurged. The surged nets
  stay exactly 5,200 below the owning surged nets at every
  tier, minbal is 0 flat and surged, and every trajectory
  ends exactly at net. The second-earner surge table is
  untouched: its renting row is the two-earner household
  (mid-tier taxi second earner), and the renting senior-tier
  taxi second earner stays unmeasured (V7 §14) — not
  queued. The bridge check stays flat — the factor is >= 1,
  so the flat lines are the conservative case. The pinned
  md5 moves again (the MA md5 is kept in
  test_no_regression.py as history). No tuning call.

What v7 adds vs v6, Queue 34 Unit MC (the entry renting
second earner in the surge table):
- The KC second-earner surge table printed three pairings
  while the entry renting second earner (Unit IB: early
  dips -193 / -288 / -419, nets 5,500 / 8,744 / 12,201)
  was measured but not shown — so the surge's effect on
  its dips was unprinted. The table now prints the
  (entry, renting) pairing at every tier beside the other
  three: early -193 -> -163, -288 -> -258, -419 -> -389,
  nets +455 at every tier (5,500 -> 5,955, 8,744 -> 9,199,
  12,201 -> 12,656) — the surge shrinks all three early
  dips but closes none, exactly the entry taxi surge, since
  the second earner's gross is the entry band and the
  rental stays the flat 5,200 unsurged. The measured
  position dips 0 flat and surged, and every trajectory
  ends exactly at net. The renting senior-tier taxi second
  earner stays unmeasured (V7 §14) — not queued. The
  bridge check stays flat — the factor is >= 1, so the flat
  lines are the conservative case. The pinned md5 moves
  again (the MB md5 is kept in test_no_regression.py as
  history). No tuning call.

What v7 adds vs v6, Queue 40 Unit MI (the senior civil-engineer
second earner, wired):
- The MF/MG/MH absence is broken by the larger world: seed
  mi-seed-1 (300 population, 365 days) holds a measured
  household pairing a construction-worker head with a senior
  civil-engineer second earner (HH000086, tier-5 civil
  engineer at 65,000/month), so the pairing is wired exactly
  on the KA/IC pattern — the IC section gains the senior
  civil-engineer rows (entry/mid/senior first-earner tiers,
  all four storm positions) and both bridge checks gain the
  line 30,000 - 17,758 = 12,242 (combined canonical start
  5,000 + 25,000, worst minbal the entry tier at the early
  position). The senior second earner DEEPENS the month-1 dip
  despite the higher pay: the senior lifestyle uplift
  (15,050) accrues daily while the 65,000 monthly lump lands
  on day 30, so entry early dips -17,758 against the mid-tier
  pairing's -8,623 — the net is higher (42,900 vs 27,950),
  the trough is deeper. The senior taxi-driver second earner
  stays unprinted: no measured household pairs the
  construction worker with one, in the larger world either
  (0 in mi-seed-1). The pinned md5 moves again (the MC md5 is
  kept in test_no_regression.py as history). No tuning call.

What v7 adds vs v6, Queue 44 Unit MM (the senior taxi-driver
second earner, wired):
- ML refuted the §12 taxi half: the pairing appears under a
  construction-worker head TWICE (ml-seed-1 HH000030, head
  Sohel Howlader tier 5 at 20,000, second earner Ishrat
  Chowdhury taxi tier 4 at 36,000; ml-seed-3 HH000042, head
  Karim Biswas tier 5 at 20,000, second earner Rina Saha taxi
  tier 5 at 36,000), so the pairing is wired exactly on the
  MI pattern — the IC section gains the senior taxi-driver
  rows (entry/mid/senior first-earner tiers, all four storm
  positions) and both bridge checks gain the line 10,000 +
  0 = 10,000 (combined canonical start 5,000 + 5,000, worst
  minbal 0 at every tier and position). Unlike the senior
  civil engineer, the senior taxi driver does NOT deepen the
  month-1 dip: the per-fare pay lands daily, so the early dip
  is 0 at every tier — the nets are 23,950 / 27,194 / 30,651
  and every trajectory ends exactly at net. The renting
  senior-tier taxi second earner stays allowed but unprinted:
  the ME re-open was decided on re-measured numbers (dip 0
  at all 12 tier x position combinations, net exactly 5,200
  below the owning senior driver, bridge trivially
  10,000 + 0 = 10,000 — the same line just wired), so the
  row would add no finding; its owning senior row is now
  modelled, so the old dangling argument falls and the
  decision now rests on the no-finding reason alone. The
  pinned md5 moves again (the MI md5 is kept in
  test_no_regression.py as history). No tuning call.

What v7 adds vs v6, Queue 45 Unit MN (the senior taxi-driver
second earner in the surge table):
- MM wired the senior taxi-driver second earner in the IC
  section and both bridge checks, but the KC second-earner
  surge table still printed only four pairings — the surge's
  effect on its row was unprinted. It is per-fare, so its
  gross DOES surge with the taxi weather (unlike the
  monthly-paid senior civil engineer, which the taxi surge
  cannot move by construction). The table now prints the
  (senior, owning) pairing at every tier beside the other
  four: early 0 -> 0 at every tier (the per-fare senior pay
  already covers the cost-only days flat, so there is no dip
  for the surge to shrink), nets +1,080 at every tier
  (23,950 -> 25,030, 27,194 -> 28,274, 30,651 -> 31,731) —
  exactly the senior single-earner taxi surge delta, at
  every tier and storm position, flat and surged, in both
  cities. The measured position dips 0 flat and surged,
  and every trajectory ends exactly at net. The renting
  senior-tier taxi second earner stays allowed but
  unprinted (V7 §33) — Queue 46 Unit MO measures it on
  the surge pattern and decides it stays unprinted. The
  bridge check stays flat — the factor is >= 1, so the flat
  lines are the conservative case. The pinned md5 moves again (the MM
  md5 is kept in test_no_regression.py as history). No
  tuning call.

What v7 adds vs v6, Queue 46 Unit MO (the renting senior-tier
taxi second earner in the surge table):
- MN printed the senior owning pairing in the KC second-earner
  surge table, so the (senior, renting) pairing was the last
  unprinted pairing in the table — and ME/MM had decided it
  stays allowed but unprinted on the flat rows, before the
  owning row was printed in the surge table. Measured on the
  KC surge pattern beside the now-printed senior owning row
  (every tier x every storm position, flat vs surged, both
  cities): early dip 0 flat AND surged at every tier and
  position, nets +1,080 at every tier (18,750 -> 19,830,
  21,994 -> 23,074, 25,451 -> 26,531) — exactly the senior
  taxi surge — every net exactly 5,200 below the owning
  surged net, every trajectory ends exactly at net. The surge
  changes nothing the flat rows hide, so the pairing stays
  allowed but unprinted and no bridge line is wired (it would
  be the trivial 10,000 + 0 = 10,000). The table is now
  closed: five pairings printed, the sixth decided unprinted
  with a measured reason. The pinned md5 does NOT move (a
  comment only in this file). No tuning call.

What v6 changes vs v5 (Queue 22, Unit EY — the ES day-wage
follow-up):
- The construction worker is now modelled on the settlement's
  day-wage rule (tools/sim/labour.py: paid worked days x
  (wage_per_month / 30)) instead of the v5 "daily" schedule, which
  paid (gross-tax)/26 on days 1-26 excluding Sundays — 23 pay days,
  23/26 of the band in trajectory terms, while the headline net
  still showed the full band (the trajectory and the headline
  disagreed by 3/26 of the band). The sim's scheduler gives a
  construction worker a work block on all 30 days of a normal
  month (measured: instantiate() over days 0-29 finds work every
  day — Friday keeps the morning shift, Saturday and Sunday are
  unmodified), so a normal month pays exactly the band and the
  headline net/rate for the profession are UNCHANGED by this
  correction — the fix is the trajectory's internal consistency
  (it now ends exactly at net, proven by the new end_balance
  return) and the correct per-day rate. The default run's base
  table is therefore byte-identical to v5 except for the new
  day-wage section below — the pinned md5 moves to the v6
  baseline (the v5 md5 is kept in test_no_regression.py as
  history).
- The default run gains a day-wage storm-month section: the
  measured live month (seeded 30-day engine run, 4 construction
  workers) had 28 worked days of 30 — day_index 3 and 22
  (1-based days 4 and 23; Queue 25 Unit HA corrects the
  reading — EY wrote them as "days 3 and 22") were storm
  days, and the scheduler's strong-cover-seeking rule bent both
  work blocks home (outdoor_work_suspended), so the settlement
  paid 28/30 of the band (entry 8,400 of 9,000). The section
  re-runs the three construction tiers at 28 worked days
  (simulate(..., day_wage_worked_days=28)): gross = band x 28/30,
  tax recomputed on the reduced gross, the reduced pay accruing
  evenly (the tool does not model which days storms fall on — the
  measured run's storm days are recorded in the report, not
  hardcoded here). No tuning call: the storm month is weather,
  not a balance problem — the entry row stays above TIGHT.
- Run: python3 tools/economy_sim.py [--shibnagar] [--v3|--v4]

What v5 adds vs v4 (Queue 9, Unit AX — the Shibnagar variant):
- A `--shibnagar` flag runs the same 30-day simulation over Shibnagar
  Town's priced residential stock (data/city2-shibnagar.json) instead
  of District 1's tier rents. The variant reads the town's rents from
  the city file (residential properties only: apartment/house with a
  rent), asserts each tier's rent equals the prices.json tier table
  (they do: 2500/4000/6000 for tiers 1/2/3), and refuses to run if
  the city data ever drifts from the table — no silent stale numbers.
- Shibnagar has no tier-4 or tier-5 residential stock (its top home
  is the tier-3 Houses B at 6000), so the three professions the
  District 1 table houses at tier 4 (doctor, business_owner, pilot)
  are capped at tier 3 in the variant — recorded as the variant's one
  rule, not hidden. Every other profession keeps its tier, so their
  rows are identical to District 1 by construction; the report says so
  instead of pretending the variant re-proves them.
- The default run is BYTE-IDENTICAL to v4 (the pinned md5 in
  tools/sim/tests/test_no_regression.py is untouched): the variant is
  an additive flag, simulate() takes an optional rent_override that
  defaults to the tier-table rent, and no wage band, rent tier,
  living-cost line or tax rule moves.
- Run: python3 tools/economy_sim.py [--shibnagar] [--v3|--v4]

What v4 changes vs v3 (Queue 7, Unit AJ — closes the v3 report §5
open item):
- The medical_monthly line (300/500/800 by band, Unit AI) is now
  charged in the base table: simulate() adds the household's band
  line to monthly costs for every row, business professions included
  (a plain expense — tax is computed on profit/gross first, so no
  tax-split issue, and the v3 business ValueError path is untouched).
- The pinned baseline md5 in tools/sim/tests/test_no_regression.py
  is updated to the new default-run md5 (the v2 md5 is kept in a
  comment there as history). The life-sim reconciliation is kept:
  tools/sim/engine.py _living_costs charges the same flat
  per-household medical line, so a one-adult household still reduces
  exactly to simulate() (acceptance test, ±2 tolerance).
- The --v3/--v4 scenarios drop the four medical scenarios — they
  would double-charge now that the line is in the base — and keep
  the five tutoring/part-time scenarios plus the medicine-basket
  check. --v3 is kept as an alias for the same section.
- Run: python3 tools/economy_sim.py [--v3|--v4]

What v2 changes vs v1 (Queue 4, fixing the v1 report's findings):
- Finding 1 (fixed in data, Unit U): cab rental now reads 200 NCr/day
  from prices.json — the renting-cab row is survivable.
- Finding 2 (Unit V): living costs scale with tier. Two new monthly
  lines from prices.json living_costs_monthly (eating_out_monthly,
  household_services_monthly) plus the lifestyle uplift: a household
  consumes lifestyle_uplift.percent_of_raise_consumed (35%) of any
  raise above its entry wage. No band cliffs, no new price lists.
- Finding 3 (Unit W): professions carry starting_balance_ncr in
  data/professions.json. The table's minbal column is still computed
  from a zero start (comparable with v1); a separate bridge check
  applies each profession's starting balance to its entry row and
  verifies the month-1 minimum never goes below zero.
- Finding 6 (Unit X): shop_owner and business_owner are no longer
  pre-cost upper bounds. Their bands are business PROFIT (GDD-03 §2:
  "Profit, not wage"; professions.json income_note: revenue minus
  stock, rent and staff). prices.json business_model carries the full
  P&L per tier (revenue, stock %, premises, staff, other); the sim
  computes profit from it, reconciles it against the canonical band,
  taxes it at the 8% business rate (GDD-03 §4.2) instead of personal
  income tax, and runs the household on profit minus tax.

What v3 adds (Queue 6, Units AH + AI) — and what it deliberately
does NOT change:
- The new lines are modelled as additive household scenarios behind
  a `--v3` flag: tutoring income/expense (300/session x 8/mo),
  part-time income (150/block x 16/mo) and the medicine expense
  (medical_monthly 300/500/800 by band). `simulate()` takes them as
  optional keyword arguments, all defaulting to 0, so every existing
  caller (tools/sim/dataio.py, the acceptance test) is unaffected.
- The default run is BYTE-IDENTICAL to v2. This is not cosmetic:
  tools/sim/tests/test_no_regression.py pins this tool's stdout md5,
  and the life-sim acceptance test requires a single-adult teacher
  household to net exactly what simulate() computes. Folding the
  medical line into the base table would break both — and updating
  the pinned baseline md5 is a change to a test file, outside this
  unit's scope. So v3 reports the new lines' effect as scenarios
  (docs/ECONOMY-SIM-REPORT-V3.md §5 records the open item honestly)
  instead of silently moving the baseline. Unit AJ (v4, this version)
  is the follow-up that does the fold-in, with the baseline update —
  see docs/ECONOMY-SIM-REPORT-V4.md.
- Extra income is taxed marginally on the combined gross (wage rows
  only); business professions with extras raise ValueError — a
  business household mixing personal side-income with profit needs a
  business+personal split this unit does not design.
- Run: python3 tools/economy_sim.py [--v3]

Household model (unchanged from v1 unless listed above):
- One adult, living alone, renting at the tier assigned in RENT_TIER.
- Lifestyle band from entry wage: lower <= 15,000, mid <= 40,000,
  else upper (food / utilities / clothing / eating out / services).
- Transport: public (bus/rickshaw) at the lifestyle band, except
  doctor, business_owner and pilot, who run a car.
- Income tax: marginal, from prices.json tax brackets (wage rows).
- Pay schedules: monthly wages land on day 30; daily wages pay on 26
  work days; per_fare accrues evenly. Business timing: shop takings
  accrue evenly (daily takings land in the ledger, GDD-03 §7); the
  business owner's monthly draw lands on day 30 (§5).
- Taxi driver is modelled twice: owning the rickshaw, and renting
  the licensed cab at prices.json taxi_fares.cab_rental_ncr_per_day
  on work days.

Flags:
- SURVIVAL FAIL: monthly net < 0 — the profession cannot live.
- TIGHT: savings rate < 10% of gross.
- IMPLAUSIBLY FAST: savings rate > 70% of gross.
- RENT BURDEN: rent > 50% of gross income.
- BRIDGE FAIL (bridge check only): entry row dips below zero in
  month 1 even with its starting balance applied.

Run: python3 tools/economy_sim.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

RENT_TIER = {
    "construction_worker": 1, "taxi_driver": 1, "chef": 2, "shop_owner": 2,
    "teacher": 2, "police_officer": 3, "civil_engineer": 3,
    "software_developer": 3, "doctor": 4, "business_owner": 4, "pilot": 4,
}
# Queue 9 / v5 (Unit AX): Shibnagar's residential stock tops out at
# tier 3 (no tier-4/5 homes exist in data/city2-shibnagar.json), so the
# three tier-4 professions are capped at tier 3 there. Every other
# profession keeps its District 1 tier.
SHIBNAGAR_RENT_TIER = {pid: min(tier, 3)
                       for pid, tier in RENT_TIER.items()}
CAR_PROFESSIONS = {"doctor", "business_owner", "pilot"}
BUSINESS_PROFESSIONS = {"shop_owner", "business_owner"}
WORK_DAYS = 26
DAYS = 30
# Queue 22 / v6 (Unit EY): the ES day wage is wage_per_month / 30 per
# worked day (tools/sim/labour.py day_wage_due), and the scheduler
# gives a construction worker a work block on all 30 days of a
# normal month (measured: instantiate() over days 0-29 finds a work
# block every day). A normal month therefore has 30 worked days and
# pays exactly the band. WORK_DAYS stays 26 for the cab-rental
# extra (a taxi works 26 days — the rental is charged on days
# 1–26, the settlement's flat 200 × 26; Queue 27 Unit JB drops
# the v1 Sunday exclusion, which charged only 23 days in the
# trajectory).
DAY_WAGE_WORKED_DAYS = 30
# Queue 23 / v7 (Unit FB): the storm-position scenario — the two
# storm days of the measured 28-worked-day month, at three
# scenario positions plus the measured one. The count (28 worked
# days) is measured (the seeded live month, Unit EY); the
# positions are scenarios, not claims about the measured month —
# except STORM_MEASURED_DAYS (days 4 and 23), which is where the
# live month's storms actually fell (Queue 25 Unit HA: FB encoded
# the 0-based day indices 3 and 22 as 1-based days; the
# settlement's storms fall on 1-based days 4 and 23).
STORM_EARLY_DAYS = (1, 2)
STORM_MID_DAYS = (15, 16)
STORM_LATE_DAYS = (29, 30)
STORM_MEASURED_DAYS = (4, 23)
# Queue 29 / v7 (Unit KC): the taxi weather surge — the EY
# month's weather (seed ey-measure, 60 population, 32 days:
# rain on day_index 2 and 28, storm on day_index 3 and 22)
# is 2 rain days + 2 storm days, so the settlement's
# taxi_factor is exactly 1.05. Only the counts are the
# scenario inputs (the settlement's formula uses counts, not
# positions); the day indices are recorded in
# docs/ECONOMY-SIM-REPORT-V7.md §16.
# Queue 47 Unit MP (v7): the formula is corroborated at two
# more live factors, same EY shape (60 population, 32 days) —
# seed mo-probe-1: 1 rain day (day_index 9) + 2 storm days
# (day_index 6 and 28), factor 1.0417, four taxi drivers all
# SYS-EMPLOYERS-paid, settled 14,583 / 23,958 / 37,500;
# seed mo-probe-2: 4 rain days (day_index 0, 3, 9, 15) +
# 3 storm days (day_index 4, 5, 28), factor 1.0833, two taxi
# drivers all SYS-EMPLOYERS-paid, settled 15,167 / 24,917 /
# 39,000. Every settled gross is round(band x factor) — the
# tool rounds the same way (14,583.33 -> 14,583;
# 24,916.67 -> 24,917). No tool change: comment only, the
# pinned md5 does NOT move; full detail in V7 report §36.
# Queue 48 Unit MQ (v7): the formula is corroborated at two
# more live factors, both ABOVE the 1.04–1.09 band — seed
# mq-probe-1: 8 rain days (day_index 11, 14, 15, 16, 21, 22,
# 23, 25) + 3 storm days (day_index 3, 4, 17), factor 1.1167,
# four taxi drivers all SYS-EMPLOYERS-paid, settled 15,633 /
# 25,683 (entry and mid only — no senior driver in the world);
# seed mq-probe-6: 6 rain days (day_index 3, 4, 7, 12, 19,
# 28) + 3 storm days (day_index 11, 16, 18), factor 1.1000,
# three taxi drivers all SYS-EMPLOYERS-paid, settled 15,400 /
# 25,300 (entry and mid only — again no senior driver). Every
# settled gross is round(band x factor) — the tool's grosses
# at the same factors are identical, and the senior grosses
# at these factors (40,200 / 39,600) are tool-computed only:
# no senior taxi driver settled live above the band in either
# world, so that settlement stays unmeasured (V7 report §37).
# No tool change: comment only, the pinned md5 does NOT move;
# full detail in V7 report §37.
# Queue 49 Unit MR (v7): the formula is corroborated at one
# more live factor, 1.1083, in a STORM-HEAVY month above the
# band — seed mq-probe-11: 3 rain days (day_index 2, 25, 26)
# + 5 storm days (day_index 6, 8, 10, 14, 29), factor 1.1083,
# one taxi driver, SYS-EMPLOYERS-paid, mid settled 25,492.
# A second seeded month lands on the SAME factor from the
# opposite mix — seed mr-probe-7: 9 rain days (day_index 2,
# 5, 8, 10, 16, 19, 21, 26, 27) + 2 storm days (day_index 14,
# 24), factor 1.1083, two taxi drivers all SYS-EMPLOYERS-paid,
# settled 15,517 / 25,492 (entry and mid) — so the settlement
# keys on the factor, not the mix: two different weather mixes
# at the same factor settle identically. Every settled gross
# is round(band x factor) — the tool's grosses at 1.1083 are
# identical (15,517 / 25,492 / 39,900), and the rounding goes
# UP at both settled tiers this time (14,000 x 1.1083 is
# 15,516.67 -> 15,517; 23,000 x 1.1083 is 25,491.67 ->
# 25,492); the senior product is an integer up to float error
# (36,000 x 1.1083 = 39,899.99...), so rounding is a no-op
# there. The senior gross at this factor (39,900) is
# tool-computed only: no senior taxi driver settled live
# above the band in either world, so that settlement stays
# unmeasured (V7 report §38). No tool change: comment only,
# the pinned md5 does NOT move; full detail in V7 report §38.
# Queue 50 Unit MS (v7): the senior gross above the band is
# now LIVE-SETTLED — seed ms-probe-11: 5 rain days (day_index
# 6, 10, 11, 19, 25) + 3 storm days (day_index 3, 14, 17),
# factor 1.0917, four taxi drivers all SYS-EMPLOYERS-paid,
# settled 15,283 / 25,108 / 25,108 / 39,300 (entry, mid, mid,
# senior — NEX000047 / NEX000013 / NEX000042 / NEX000043).
# Every settled gross is round(band x factor) — the tool's
# grosses at 1.0917 are identical (15,283 / 25,108 / 39,300),
# and the rounding goes DOWN at both settled lower tiers this
# time (14,000 x 1.0917 is 15,283.33 -> 15,283; 23,000 x
# 1.0917 is 25,108.33 -> 25,108); the senior product is an
# integer up to float error (36,000 x 1.0917 = 39,300.00...),
# so rounding is a no-op there. A second seeded month lands
# on the SAME factor from different day positions — seed
# ms-probe-7: 5 rain days (day_index 7, 12, 19, 26, 28) + 3
# storm days (day_index 0, 1, 4), factor 1.0917, two taxi
# drivers all SYS-EMPLOYERS-paid, both mid settled 25,108 —
# so the settlement keys on the counts, not the positions.
# The surge is now corroborated at seven live factors
# (1.0417, 1.05, 1.0833, 1.0917, 1.1000, 1.1083, 1.1167),
# and the senior tier is live-settled above the band for the
# first time. No tool change: comment only, the pinned md5
# does NOT move; full detail in V7 report §39.
# Queue 51 Unit MT (v7): the senior gross above the band is
# now live-settled at a SECOND factor — seed mt-probe-5: 7
# rain days (day_index 3, 13, 14, 15, 16, 17, 29) + 3 storm
# days (day_index 12, 23, 27), factor 1.1083, five taxi
# drivers all SYS-EMPLOYERS-paid, settled 25,492 x 4 (mid)
# and 39,900 (senior — NEX000047). Every settled gross is
# round(band x factor) — the tool's grosses at 1.1083 are
# identical (15,517 / 25,492 / 39,900) — and the rounding
# goes UP at both lower tiers this time (14,000 x 1.1083 is
# 15,516.67 -> 15,517; 23,000 x 1.1083 is 25,491.67 ->
# 25,492), as MR already measured at this factor; the senior
# product is exactly 39,900.0, so rounding is a no-op there.
# A second seeded month lands on the MS factor — seed
# mt-probe-13: 5 rain days (day_index 9, 12, 24, 27, 29) + 3
# storm days (day_index 2, 7, 21), factor 1.0917, five taxi
# drivers all SYS-EMPLOYERS-paid, four mid settled 25,108
# and senior NEX000028 settled 39,300 — the second live
# senior settlement at 1.0917. The senior tier above the
# band now rests on two live factors, and the senior
# rounding question is closed by construction: 36,000 x
# 0.25/30 is 300 per rain day and 36,000 x 0.5/30 is 600 per
# storm day, so the senior gross is 36,000 + 300 x rain +
# 600 x storm — always an integer up to float error (round()
# always lands on it), so rounding is a no-op at the senior
# tier at EVERY factor. No tool change:
# comment only, the pinned md5 does NOT move; full detail
# in V7 report §40.
# Queue 52 Unit MU (v7): the hunt for a senior settlement at
# 1.1167 found NONE in twenty-four fresh seeds
# (mu-probe-1..mu-probe-24, EY shape) — no month in the sweep
# reaches 1.1167 at all (highest factor 1.1000), so the senior
# gross at 1.1167 (40,200) stays tool-computed only, and a
# wider blind sweep would be grinding, not measuring — the
# thin hit rate is itself the finding (9 months above the
# band in 24 seeds, three holding a senior, none at 1.1167).
# The sweep still measures something real: the senior gross
# at 1.1000 (39,600) is now LIVE-SETTLED — seed mu-probe-8:
# 6 rain days (day_index 14, 15, 16, 22, 23, 28) + 3 storm
# days (day_index 17, 20, 26), factor 1.1000, three taxi
# drivers all SYS-EMPLOYERS-paid, two mid settled 25,300 and
# senior NEX000012 settled 39,600; and seed mu-probe-16: 8
# rain days (day_index 4, 7, 13, 17, 20, 24, 28, 29) + 2
# storm days (day_index 12, 14), the SAME factor 1.1000 from
# the opposite mix, nine taxi drivers all SYS-EMPLOYERS-paid,
# two entry settled 15,400, five mid settled 25,300 and two
# seniors NEX000045 and NEX000060 settled 39,600 — so the
# settlement keys on the factor, not the mix, at 1.1000 as
# MR already measured at 1.1083. A third live senior
# settlement at 1.0917 also lands — seed mu-probe-3: 7 rain
# days (day_index 0, 2, 10, 13, 16, 20, 27) + 2 storm days
# (day_index 5, 22), factor 1.0917 from a different mix than
# MS/MT's 5 + 3, two taxi drivers all SYS-EMPLOYERS-paid,
# mid settled 25,108 and senior NEX000029 settled 39,300.
# Every settled gross is round(band x factor) — the tool's
# grosses at 1.1000 are identical (15,400 / 25,300 /
# 39,600) — and the rounding is a no-op at 1.1000 (the
# products are integers up to float error). The senior tier
# above the band now rests on three live factors (1.0917,
# 1.1000, 1.1083). No tool change: comment only, the pinned
# md5 does NOT move; full detail in V7 report §41.
# Queue 53 Unit MV (v7): the senior gross at 1.1167 (40,200)
# is now LIVE-SETTLED — twice, from two different mixes.
# MU proved the month's weather is seed-only, so MV scanned
# 200 fresh seeds (mv-probe-1..mv-probe-200) on the weather
# signature alone (rain + 2 x storm = 14) WITHOUT running
# the population, then ran the full EY shape only on the 5
# matches: mv-probe-3 (6 rain + 4 storm), mv-probe-38 (4 + 5),
# mv-probe-105 (8 + 3, MQ's mix), mv-probe-106 (6 + 4) and
# mv-probe-115 (4 + 5) — every one of the five reproduces
# its scanned counts exactly in the full run, so the
# pre-filter is itself verified. All five months are factor
# 1.1167, 15 taxi drivers in all, all SYS-EMPLOYERS-paid,
# every settled gross round(band x factor): mv-probe-105
# holds senior NEX000014 settled 40,200 (five drivers:
# entry 15,633, mid 25,683 x 3, senior 40,200) and
# mv-probe-115 holds senior NEX000053 settled 40,200
# (three drivers: mid 25,683 x 2, senior 40,200) — so the
# settlement keys on the factor, not the mix, at 1.1167 as
# MR already measured at 1.1083 and MU at 1.1000. The other
# three matches hold no senior (mv-probe-3: entry 15,633 x 2,
# mid 25,683; mv-probe-38: mid 25,683 x 2; mv-probe-106:
# entry 15,633 x 2). The tool's grosses at 1.1167 are
# identical (15,633 / 25,683 / 40,200) and the rounding goes
# down at both lower tiers (15,633.33 -> 15,633; 25,683.33 ->
# 25,683) while the senior product is exactly 40,200.0, so
# rounding is a no-op there. The senior tier above the band
# now rests on FOUR live factors (1.0917, 1.1000, 1.1083,
# 1.1167) — the highest corroborated factor is no longer
# tool-computed only. No tool change: comment only, the
# pinned md5 does NOT move; full detail in V7 report §42.
# Queue 54 Unit MW (v7): the taxi surge at the SMALLEST
# factor, 1.0083 (1 rain day, 0 storm days), is now
# LIVE-SETTLED at all three tiers. MV closed the
# above-band senior chain at the top (1.1167) and left the
# floor of the surge range unmeasured (lowest corroborated
# factor 1.0167, MT §40), so MW hunted with the same
# weather-first pre-filter MV proved: scan 200 fresh seeds
# (mw-probe-1..mw-probe-200) on the weather signature
# alone (rain + 2 x storm = 1) WITHOUT running the
# population, then run the full EY shape only on the 3
# matches: mw-probe-15 (1 rain, day_index 3), mw-probe-124
# (1 rain, day_index 11) and mw-probe-150 (1 rain,
# day_index 9) — every one of the three reproduces its
# scanned counts exactly in the full run, so the pre-filter
# is itself verified again. All three months are factor
# 1.0083, 9 taxi drivers in all, all SYS-EMPLOYERS-paid,
# every settled gross round(band x factor): mw-probe-15
# holds senior NEX000059 settled 36,300 (five drivers:
# entry 14,117 x 2, mid 23,192 x 2, senior 36,300) and
# mw-probe-150 holds seniors NEX000015 and NEX000028
# settled 36,300 each (four drivers: mid 23,192 x 2,
# senior 36,300 x 2) — three senior settlements at the
# floor factor, from two seeds with the rain on different
# days, so the settlement keys on the counts, not the
# positions, at 1.0083 too. mw-probe-124 holds no taxi
# driver at all. The tool's grosses at 1.0083 are identical
# (14,117 / 23,192 / 36,300) and the rounding goes UP at
# both lower tiers (14,116.67 -> 14,117; 23,191.67 ->
# 23,192) while the senior product is exactly 36,300.0, so
# rounding is a no-op there. The surge is now corroborated
# at EIGHT live factors (1.0083, 1.0417, 1.05, 1.0833,
# 1.0917, 1.1000, 1.1083, 1.1167) and at every step of the
# factor ladder from the floor to the top (r + 2s = 1..14).
# No tool change: comment only, the pinned md5 does NOT
# move; full detail in V7 report §43.
TAXI_WEATHER_MEASURED_RAIN_DAYS = 2
TAXI_WEATHER_MEASURED_STORM_DAYS = 2
# Queue 25 / v7 (Unit HD): the mixed-profession second earner —
# the settlement's measured pairings (V7 report §6: Priya's
# household has a taxi-driver second earner at 14,000, Mariam's
# a civil-engineer second earner at 38,000). The second earner's
# tier defaults to the measured one — taxi_driver at entry
# (14,000), civil_engineer at mid (38,000) — while the first
# earner (construction_worker) varies over entry/mid/senior; the
# table's entry row is the measured household in each case.
# Queue 26 / Unit IC: a caller may name another tier the source
# data actually gives (second_earner_tier). Only these two
# pairings are modelled (any other pid is refused): the scenario
# is the measured households, not arbitrary professions.
SECOND_EARNER_MEASURED_TIER = {"taxi_driver": "entry",
                               "civil_engineer": "mid"}


def load(name):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)


def band_for(entry_wage):
    return "lower" if entry_wage <= 15000 else ("mid" if entry_wage <= 40000 else "upper")


def monthly_tax(income, brackets):
    tax = 0.0
    for b in brackets:
        lo, hi, rate = b["from_ncr"], b["to_ncr"], b["rate_percent"]
        top = income if hi is None else min(income, hi)
        if top > lo:
            tax += (top - lo) * rate / 100.0
    return round(tax)


def taxi_weather_factor(rain_days, storm_days):
    """Queue 29 / v7 (Unit KC): the settlement's taxi surge —
    engine._settle_month scales a taxi driver's gross by
    1 + 0.25 × rain_days/30 + 0.5 × storm_days/30, where the
    counts are the month's weather presets (rain_days + storm
    days ≤ 30 — one preset per day). The factor is ≥ 1 for any
    weather, so a flat taxi row is the conservative case: the
    surge can only raise a taxi gross, never lower it."""
    return 1 + 0.25 * rain_days / 30 + 0.5 * storm_days / 30


def business_pnl(prices, pid, tier):
    """Full P&L for a business profession at one tier, from
    prices.json business_model. Returns dict with revenue, stock,
    premises, staff, other, profit."""
    model = prices["business_model"][pid]
    t = model["tiers"][tier]
    revenue = t["revenue_ncr"]
    stock = round(revenue * model["stock_percent_of_revenue"] / 100.0)
    profit = revenue - stock - t["premises_rent_ncr"] - t["staff_ncr"] \
        - t["other_costs_ncr"]
    return {
        "revenue": revenue, "stock": stock,
        "premises": t["premises_rent_ncr"], "staff": t["staff_ncr"],
        "other": t["other_costs_ncr"], "profit": profit,
    }


def load_shibnagar_rents(prices):
    """Queue 9 / v5 (Unit AX): Shibnagar's priced residential stock.

    Reads data/city2-shibnagar.json (residential properties only:
    apartment/house with a rent) and returns (tier -> rent, stock).
    Each tier's rent must equal the prices.json tier table — the town's
    rents are tier rents, not a second price list — and a drift raises
    ValueError instead of running on stale numbers. The 7 unpriced
    properties (ghat, bus stand, school, clinic, town office, 2
    farmland plots) are civic/plot stock, not homes, and are excluded
    by the residential + priced filter, not by an id list.
    """
    city = load("city2-shibnagar.json")
    tier_table = {r["tier"]: r["rent_ncr"]
                  for r in prices["rent_monthly_by_tier"]}
    rents, stock = {}, {}
    for p in city["properties"]:
        if p["property_type"] not in ("apartment", "house"):
            continue
        rent = p.get("rent_monthly_ncr_per_unit")
        if rent is None:
            continue
        tier = p["tier"]
        if tier in rents and rents[tier] != rent:
            raise ValueError(
                f"shibnagar tier {tier} rent disagrees within the file: "
                f"{rents[tier]} vs {rent}")
        rents[tier] = rent
        stock[tier] = stock.get(tier, 0) + p.get("units", 1)
    for tier, rent in rents.items():
        if tier_table.get(tier) != rent:
            raise ValueError(
                f"shibnagar tier {tier} rent {rent} != prices.json tier "
                f"table {tier_table.get(tier)}")
    return rents, stock


def simulate(prices, wage_row, tier, extra_daily_cost=0, label_suffix="",
             tutoring_income=0, tutoring_expense=0, part_time_income=0,
             medicine_expense=0, rent_override=None,
             day_wage_worked_days=None, storm_days=None,
             second_earner=False, second_earner_renting_cab=False,
             second_earner_tier=None,
             taxi_rain_days=None, taxi_storm_days=None):
    pid = wage_row["profession_id"]
    band = band_for(wage_row["entry"])
    lc = prices["living_costs_monthly"]
    # Queue 9 / v5: rent_override is the Shibnagar variant's rent for
    # this profession (None = the District 1 tier-table rent, the v4
    # behaviour, byte-identical).
    rent = rent_override if rent_override is not None else next(
        r["rent_ncr"] for r in prices["rent_monthly_by_tier"]
        if r["tier"] == RENT_TIER[pid])
    food = lc["food_home_cooking"][band]
    utilities = lc["utilities_power_water_internet"][band]
    clothing = lc["clothing_personal"][band]
    eating = lc["eating_out_monthly"][band]
    services = lc["household_services_monthly"][band]
    # Queue 7 / v4 (Unit AJ): the medical line is a base cost now,
    # charged at the household's band for every row, business
    # professions included (a plain expense — tax is computed on
    # profit/gross first, so the v3 business ValueError path is
    # untouched). The medicine_expense kwarg stays for callers that
    # model an extra episode on top; the default run charges the
    # line exactly once, here.
    medical = lc["medical_monthly"][band]
    if pid in CAR_PROFESSIONS:
        transport = lc["transport_own_car_fuel_upkeep"][band]
    else:
        transport = lc["transport_public_bus_rickshaw"][band]

    pnl = None
    if pid in BUSINESS_PROFESSIONS:
        pnl = business_pnl(prices, pid, tier)
        gross = pnl["profit"]  # the canonical band, via the P&L
        biz_rate = prices["tax"]["business_monthly_percent_of_profit"]
        tax = round(gross * biz_rate / 100.0) if gross > 0 else 0
        # Shop takings accrue daily; the owner's draw lands day 30.
        sched = "daily_takings" if pid == "shop_owner" else "monthly"
    else:
        gross = wage_row[tier]
        tax = monthly_tax(gross, prices["tax"]["income_monthly_brackets"])
        sched = wage_row["pay_schedule"]

    # Queue 22 / v6 (Unit EY): the day-wage profession
    # (construction_worker — the only "daily" pay_schedule) is paid
    # per worked day at wage/30 (the ES rule in tools/sim/labour.py
    # day_wage_due), not the monthly band spread over 26 Sundays-off
    # days. Worked days default to the scheduler-measured normal
    # month (DAY_WAGE_WORKED_DAYS = 30 — a work block every day);
    # a caller modelling a storm month passes the measured count
    # (the report's storm scenario uses 28). Gross is band x
    # worked/30 and tax is recomputed on that gross, so a storm
    # month's lower gross is taxed as a lower gross, exactly as the
    # settlement taxes the day-wage pay it actually made.
    # Queue 23 / v7 (Unit FB): the storm-position scenario — the
    # caller names the storm days instead (storm_days: distinct
    # 1-based days of the 30-day month); worked days are 30 minus
    # the storm days, and the trajectory pays only on worked days
    # (see below). The count is the measured live month (28 worked
    # days); the positions are scenario positions (early / mid /
    # late) plus the measured position (days 4 and 23 — the live
    # month's actual storm days). A storm_days that disagrees with
    # day_wage_worked_days, or names a day outside 1..30, or
    # repeats a day, is refused — the scenario must stay one
    # month, not a miscounted one. storm_days is meaningless for
    # any other pay schedule and is refused there too.
    storm_set = None
    if sched == "daily":
        if storm_days is not None:
            storm_set = set(storm_days)
            if len(storm_set) != len(list(storm_days)) \
                    or any(not isinstance(d, int) or d < 1
                           or d > DAYS for d in storm_set):
                raise ValueError(
                    "storm_days must be distinct day numbers in"
                    f" 1..{DAYS}, got {storm_days!r}")
            worked = DAYS - len(storm_set)
            if day_wage_worked_days is not None \
                    and day_wage_worked_days != worked:
                raise ValueError(
                    "storm_days imply "
                    f"{worked} worked days, not "
                    f"{day_wage_worked_days}")
        else:
            worked = (DAY_WAGE_WORKED_DAYS
                      if day_wage_worked_days is None
                      else day_wage_worked_days)
        gross = round(wage_row[tier] * worked / DAYS)
        tax = monthly_tax(gross, prices["tax"]["income_monthly_brackets"])
    elif storm_days is not None:
        raise ValueError(
            "storm_days is a day-wage scenario (construction_worker"
            f" only); {pid} pays {sched}")

    # Queue 29 / v7 (Unit KC): the taxi weather surge — the
    # settlement scales a taxi driver's gross by
    # taxi_weather_factor(rain_days, storm_days)
    # (engine._settle_month), while the tool modelled taxi pay
    # flat. The caller names the month's weather counts; each
    # must be an integer day count in 0..30 and the two together
    # at most 30 (one preset per day — a day cannot be both rain
    # and storm). The surge is meaningful only on a taxi row —
    # the single-earner taxi driver, or a household with a taxi
    # second earner — and is refused anywhere else (a monthly
    # or day-wage row has no taxi gross to scale; a business
    # P&L is not a wage). The factor defaults to 1.0, so a call
    # without weather is byte-identical to the flat model.
    taxi_weather_given = (taxi_rain_days is not None
                          or taxi_storm_days is not None)
    rain_days = 0 if taxi_rain_days is None else taxi_rain_days
    storm_days_taxi = (0 if taxi_storm_days is None
                       else taxi_storm_days)
    if taxi_weather_given:
        for name, count in (("taxi_rain_days", rain_days),
                            ("taxi_storm_days", storm_days_taxi)):
            if not isinstance(count, int) or isinstance(count, bool) \
                    or count < 0 or count > DAYS:
                raise ValueError(
                    f"{name} must be a day count in 0..{DAYS};"
                    f" got {count!r}")
        if rain_days + storm_days_taxi > DAYS:
            raise ValueError(
                "taxi rain days + storm days cannot exceed the"
                f" {DAYS}-day month; got {rain_days} +"
                f" {storm_days_taxi}")
        if pid != "taxi_driver" and second_earner != "taxi_driver":
            raise ValueError(
                "taxi weather days scale a taxi gross — the"
                " single-earner taxi driver or a taxi second"
                f" earner; {pid} has no taxi gross to scale")
    taxi_factor = taxi_weather_factor(rain_days, storm_days_taxi)
    if pid == "taxi_driver":
        # The surge lands on the gross before tax and uplift —
        # the settlement taxes the surged gross and computes
        # the uplift on it (engine._settle_month), so both are
        # recomputed here; the uplift below reads the surged
        # gross. The rental (extra_daily_cost) is untouched:
        # the settlement charges it flat, unsurged.
        gross = round(gross * taxi_factor)
        tax = monthly_tax(gross, prices["tax"]
                          ["income_monthly_brackets"])

    # Lifestyle uplift (Unit V): a fixed percent of the raise above
    # the entry-tier income is consumed by lifestyle.
    uplift_pct = prices["lifestyle_uplift"]["percent_of_raise_consumed"]
    entry_income = (business_pnl(prices, pid, "entry")["profit"]
                    if pid in BUSINESS_PROFESSIONS else wage_row["entry"])
    uplift = round(max(0, gross - entry_income) * uplift_pct / 100.0)

    # Queue 24 / Unit GD: the second earner — a construction
    # worker at the same tier, on the same storm days and the same
    # day-wage rule. Gross and tax double per earner (each earner
    # is taxed on their own gross, as the settlement taxes each
    # earner on what they received); the uplift doubles too (the
    # settlement sums it per earner, engine._settle_month). The
    # household costs follow engine._living_costs for two adults:
    # food and clothing ×2, transport and eating out ×2 (both are
    # per-earner lines in _living_costs — the queue draft's "rest
    # flat" gloss is corrected here against the source: only
    # utilities / services / medical and rent are flat), and the
    # trajectory needs no change — the doubled pay lands on the
    # same worked days at the doubled daily rate, and the doubled
    # costs accrue daily. Refused for any non-day-wage profession
    # and together with the v3 side-income/expense lines (those
    # belong to one person; a two-earner household with side income
    # needs a split this unit does not design).
    # Queue 25 / Unit HD: the second earner may instead be another
    # profession — `second_earner="taxi_driver"` (per-fare, entry
    # 14,000) or `"civil_engineer"` (monthly, mid 38,000), the
    # settlement's measured pairings (V7 §6), at the FIXED measured
    # tier while the first earner varies. The second earner's gross
    # is their full tier wage (storm days do not change it — the
    # per-fare rule has no storm days, the monthly pay lands day 30
    # regardless), taxed on their own gross with their own uplift
    # (taxi entry: 14,000 = entry, uplift 0; civil engineer mid:
    # 38,000 vs entry 22,000, uplift 35% of 16,000); the household
    # costs follow the same _living_costs scaling (food/clothing
    # ×2, transport per earner — both second earners are
    # non-car, so the public line at the household band — eating
    # ×2, the rest flat). The taxi second earner is the OWNING
    # driver: no cab rental is charged (the renting variant is a
    # further scenario, not taken here). Any other pid is refused.
    # The trajectory lands each earner's pay by that earner's own
    # schedule (see below): the first earner's storm days move the
    # dip, the second earner's steady pay does not.
    # The first earner's own storm-month figures, before any
    # second earner is added — the trajectory lands each earner's
    # pay by that earner's own schedule (a mixed second earner's
    # pay is NOT in the base below; it lands separately).
    first_gross, first_tax = gross, tax
    second_pid = None
    second_tier = None
    second_sched = None
    second_net = 0
    second_rental = 0
    # Queue 26 / Unit IC: a tier override needs a mixed second
    # earner — not the same-tier case (that earner takes the
    # first earner's tier by definition) and not no second
    # earner at all.
    if second_earner_tier is not None and not (
            isinstance(second_earner, str)
            and second_earner in SECOND_EARNER_MEASURED_TIER):
        raise ValueError(
            "second_earner_tier needs a mixed second earner"
            f" ({sorted(SECOND_EARNER_MEASURED_TIER)}); got "
            f"second_earner={second_earner!r}")
    if second_earner:
        if sched != "daily":
            raise ValueError(
                "second_earner is a day-wage scenario"
                f" (construction_worker only); {pid} pays {sched}")
        if tutoring_income or tutoring_expense or part_time_income \
                or medicine_expense:
            raise ValueError(
                "second_earner cannot combine with the v3"
                " side-income/expense lines — those belong to one"
                " person")
        if second_earner is True:
            second_pid, second_tier = pid, tier
        elif isinstance(second_earner, str) and second_earner \
                in SECOND_EARNER_MEASURED_TIER:
            second_pid = second_earner
            # Queue 26 / Unit IC: the second earner's tier is
            # selectable — the measured tier is the default, but
            # a caller may name another tier the source data
            # actually gives (mid-tier taxi driver, entry civil
            # engineer). The tier must be one of entry / mid /
            # senior; any other value is refused, not silently
            # treated as the measured one.
            if second_earner_tier is None:
                second_tier = SECOND_EARNER_MEASURED_TIER[second_pid]
            elif second_earner_tier in ("entry", "mid", "senior"):
                second_tier = second_earner_tier
            else:
                raise ValueError(
                    "second_earner_tier is entry, mid or senior;"
                    f" got {second_earner_tier!r}")
        else:
            raise ValueError(
                "second_earner is True (the same profession, GD)"
                " or a measured pairing "
                f"({sorted(SECOND_EARNER_MEASURED_TIER)}); got "
                f"{second_earner!r}")
        if second_pid == pid:
            gross *= 2
            tax *= 2
            uplift *= 2
            food *= 2
            clothing *= 2
            transport *= 2
            eating *= 2
        else:
            w2 = next(w for w in prices["wages_monthly"]
                      if w["profession_id"] == second_pid)
            second_gross = w2[second_tier]
            if second_pid == "taxi_driver":
                # Queue 29 / v7 (Unit KC): the surge lands on
                # the second earner's gross too — the settlement
                # scales every taxi earner's gross in the
                # household loop, head or second earner alike —
                # and the tax and uplift below are computed on
                # the surged gross, as the settlement does. The
                # rental (second_rental, below) stays flat.
                second_gross = round(second_gross * taxi_factor)
            second_tax = monthly_tax(
                second_gross, prices["tax"]["income_monthly_brackets"])
            second_uplift = round(max(0, second_gross - w2["entry"])
                                  * uplift_pct / 100.0)
            second_sched = w2["pay_schedule"]
            if second_sched not in ("monthly", "per_fare"):
                raise ValueError(
                    "a mixed second earner must pay monthly or"
                    f" per_fare; {second_pid} pays {second_sched}")
            transport2 = lc["transport_own_car_fuel_upkeep"][band] \
                if second_pid in CAR_PROFESSIONS \
                else lc["transport_public_bus_rickshaw"][band]
            gross += second_gross
            tax += second_tax
            uplift += second_uplift
            food *= 2
            clothing *= 2
            transport += transport2
            eating *= 2
            second_net = second_gross - second_tax
    # Queue 26 / Unit IB: the renting-cab variant of the taxi
    # second earner. The rental follows the settlement's rule —
    # engine._settle_month charges cab_rental_ncr_per_day ×
    # WORK_DAYS (200 × 26 = 5,200/month) flat for the month: the
    # settlement does not vary it by worked days, storm days or
    # Sundays, and neither does this model. It is a monthly cost
    # line (5,200), accruing evenly in the daily model like rent
    # — the settlement charges the same 5,200 once at month-end.
    # Refused with any second earner but the taxi driver (and
    # with no second earner at all).
    if second_earner_renting_cab:
        if second_pid != "taxi_driver":
            raise ValueError(
                "second_earner_renting_cab is the renting-cab"
                " variant of the taxi-driver second earner;"
                " a renting civil engineer is meaningless —"
                " civil engineers hold no cab, so there is no"
                f" rental to charge; got second earner"
                f" {second_pid!r}")
        # Queue 28 / Unit KA: the renting variant now combines
        # with a named tier (IC's second_earner_tier) for the
        # taxi driver — a renting mid-tier taxi driver
        # (23,000, per-fare) as second earner. The rental is
        # the same flat 5,200/month whatever the tier (the
        # settlement charges rental_day × WORK_DAYS per taxi
        # driver, not per tier); the tier moves the pay, not
        # the rental. The tier itself was validated above
        # (entry / mid / senior only), so nothing new is
        # refused here.
        second_rental = (prices["taxi_fares"]
                         ["cab_rental_ncr_per_day"] * WORK_DAYS)

    # Queue 6 / v3 new lines (all default 0) + Queue 7 / v4: the
    # medical line is a base cost now (see `medical` above), so the
    # medicine_expense kwarg models only an EXTRA episode on top.
    # Uplift above is computed from the base gross on purpose: the
    # lifestyle uplift prices the wage ladder, not side-income.
    # Extra income is taxed marginally on the combined gross.
    base_tax = tax
    extra_income = tutoring_income + part_time_income
    extra_expense = tutoring_expense + medicine_expense
    if extra_income or extra_expense:
        if pid in BUSINESS_PROFESSIONS:
            raise ValueError(
                f"{pid}: tutoring/part-time/medicine lines are not "
                "modelled for business professions in v3 — a "
                "business household needs a business+personal split")
        gross = gross + extra_income
        tax = monthly_tax(gross, prices["tax"]["income_monthly_brackets"])
    extra_income_net = extra_income - (tax - base_tax)

    monthly_costs = rent + food + utilities + clothing + transport \
        + eating + services + medical + uplift + extra_expense \
        + second_rental
    extra_monthly = extra_daily_cost * WORK_DAYS
    net = gross - tax - monthly_costs - extra_monthly

    # 30-day trajectory from a zero start (v1-comparable minbal).
    # Base pay follows the profession's schedule on the BASE gross
    # and tax; v3 side-income accrues evenly on top, so the month's
    # total still equals gross - tax exactly.
    base_gross = gross - extra_income
    # Queue 25 Unit HD: with a mixed second earner, the base is
    # the FIRST earner's pay only (v3 lines are refused with a
    # second earner, so extras are 0 and base_tax is the first
    # earner's tax) — the second earner's pay lands below, by its
    # own schedule. The GD case is untouched: both earners share
    # the day-wage schedule, so the doubled base lands together.
    if second_pid is not None and second_pid != pid:
        base_gross, base_tax = first_gross, first_tax
    daily_cost = monthly_costs / DAYS
    balance, min_balance = 0.0, 0.0
    for day in range(1, DAYS + 1):
        balance -= daily_cost
        # Queue 27 / Unit JB: the single-earner renting-cab row
        # follows the settlement's rental charge — 200 NCr/day ×
        # WORK_DAYS (26) = 5,200/month flat (engine._settle_month
        # charges rental_day × WORK_DAYS, with no Sunday
        # exclusion and no storm dependence). The v1 rule charged
        # the rental only on days ≤ 26 excluding Sundays (23
        # days = 4,600 in the trajectory, while the headline net
        # already subtracted the full 5,200 — so the trajectory
        # ended 600 above net, the same class of inconsistency
        # Unit EY fixed for the v5 daily branch). The Sunday
        # exclusion was a leftover of the v5 daily schedule,
        # which paid on 23 days; v6 already moved construction
        # pay off that schedule. Charging on days 1–26 (the
        # sourced WORK_DAYS count, the tool's existing
        # convention for the row) makes the trajectory charge
        # exactly extra_monthly, so it ends exactly at net.
        if extra_daily_cost and day <= WORK_DAYS:
            balance -= extra_daily_cost
        if sched == "monthly":
            if day == DAYS:
                balance += base_gross - base_tax
        elif sched == "daily":
            # Queue 22 / v6 (Unit EY): the ES day wage accrues evenly
            # — wage/30 per worked day, 30 worked days in a normal
            # month, so the month pays exactly the band. The v5
            # branch paid (gross-tax)/26 on days 1-26 excluding
            # Sundays — 23 pay days, 23/26 of the band — while the
            # headline net showed the full band; the trajectory now
            # ends exactly at net.
            # Queue 23 / v7 (Unit FB): with storm_days, the pay
            # lands only on worked days — (gross-tax)/worked per
            # worked day, 0 on a storm day — so the month-1 dip
            # depends on where the storms fall; the total is still
            # exactly gross-tax, so the trajectory still ends at
            # net. Without storm_days the even accrual (v6) is
            # unchanged, and the v6 storm section's figure stays
            # the even-spread one.
            if storm_set is None:
                balance += (base_gross - base_tax) / DAYS
            elif day not in storm_set:
                balance += (base_gross - base_tax) / worked
        else:  # per_fare / daily_takings: even accrual
            balance += (base_gross - base_tax) / DAYS
        if second_pid is not None and second_pid != pid:
            # Queue 25 Unit HD: the mixed second earner's pay lands
            # by its own schedule — per-fare accrues evenly (storm
            # days do not change it: the per-fare rule has no storm
            # days), monthly lands on day 30 (storm days do not
            # change it either: the pay lands at month-end
            # regardless). No storm effect is forced where the pay
            # rule has none.
            if second_sched == "monthly":
                if day == DAYS:
                    balance += second_net
            else:  # per_fare
                balance += second_net / DAYS
        if extra_income_net:
            # v3 side-income (tutoring / part-time) accrues evenly.
            balance += extra_income_net / DAYS
        min_balance = min(min_balance, balance)

    rate = net / gross * 100 if gross else 0
    flags = []
    if net < 0:
        flags.append("SURVIVAL FAIL")
    elif rate < 10:
        flags.append("TIGHT")
    if rate > 70:
        flags.append("IMPLAUSIBLY FAST")
    if rent / gross > 0.5:
        flags.append("RENT BURDEN")
    return {
        "profession": pid + label_suffix, "pid": pid, "tier": tier,
        "gross": gross, "tax": tax, "rent": rent,
        "costs_total": monthly_costs + extra_monthly,
        "uplift": uplift, "extra": extra_monthly,
        "net": round(net), "rate": round(rate, 1),
        "min_balance": round(min_balance), "flags": flags, "pnl": pnl,
        "extra_income": extra_income, "extra_expense": extra_expense,
        # Queue 24 / Unit GD: whether the row models a two-earner
        # household (a second construction worker at the same tier,
        # same storm days, same day-wage rule).
        # Queue 25 / Unit HD: which profession the second earner
        # works (None for a single-earner row; "construction_worker"
        # for the GD same-tier case, "taxi_driver" or
        # "civil_engineer" for the mixed measured pairings).
        "second_earner": second_earner,
        "second_earner_pid": second_pid,
        # Queue 26 / Unit IC: which tier the mixed second earner
        # works (None for a single-earner row; the measured tier
        # unless second_earner_tier names another).
        "second_earner_tier": second_tier,
        # Queue 26 / Unit IB: whether the taxi second earner
        # rents the cab, and the monthly rental charged (0 for
        # the owning driver) — the settlement's rule, 200/day ×
        # 26 worked days = 5,200/month.
        "second_earner_renting_cab": second_earner_renting_cab,
        "second_earner_rental": second_rental,
        # Queue 29 / v7 (Unit KC): the taxi weather-surge
        # factor applied to a taxi gross in this row (1.0 when
        # no weather is named — the flat model).
        "taxi_factor": taxi_factor,
        # Queue 22 / v6 (Unit EY): the trajectory's final balance —
        # it must equal net (the trajectory models the same month
        # the headline figures describe); the v5 daily branch ended
        # 3/26 of the band short of it, and the no-regression test
        # pins the equality for every row.
        "end_balance": round(balance),
    }


def print_v4_scenarios(prices):
    """Queue 6/7 additional lines (Units AH + AI), behind --v3/--v4.

    v4 (Unit AJ): the medical line is charged in the base table now,
    so the four medical scenarios v3 printed are gone — they would
    double-charge. What remains are the tutoring / part-time
    scenarios (still extras on top of the base) plus the medicine
    basket check, so the v4 report can quote them verbatim. --v3 is
    kept as an alias for this section.
    """
    tut = prices["tutoring"]["monthly_typical_ncr"]
    pt = prices["part_time_student_work"]["monthly_typical_ncr"]
    med = prices["living_costs_monthly"]["medical_monthly"]
    med_items = {i["id"]: i["price_ncr"]
                 for i in prices["medicine"]["items"]}
    basket = (med_items["fever_pain_relief_strip"]
              + med_items["oral_rehydration_salts"]
              + med_items["cough_syrup_bottle"])
    wages = {w["profession_id"]: w for w in prices["wages_monthly"]}
    print("v4 additional scenarios (Units AH + AI):")
    print(f"  priced from prices.json: tutoring "
          f"{prices['tutoring']['per_session_ncr']}/session x "
          f"{prices['tutoring']['sessions_per_month_typical']}/mo = "
          f"{tut}; part-time "
          f"{prices['part_time_student_work']['per_block_ncr']}/block x "
          f"{prices['part_time_student_work']['blocks_per_week_typical']}"
          f"/wk x 4 = {pt}; medical budget lower {med['lower']} / "
          f"mid {med['mid']} / upper {med['upper']} — now charged in "
          f"the base table (Unit AJ), not a scenario")
    print(f"  medicine basket check: one minor-illness episode "
          f"(fever strip {med_items['fever_pain_relief_strip']} + "
          f"rehydration salts {med_items['oral_rehydration_salts']} + "
          f"cough syrup {med_items['cough_syrup_bottle']}) = {basket} "
          f"NCr, inside the lower medical budget ({med['lower']})")
    print(f"  pharmacy: {prices['medicine']['pharmacy_name']} "
          f"({prices['medicine']['pharmacy_property_id']}, unit 1); "
          f"clinic treatment stays free at point of use (GDD-12 §6)")
    print()
    print("household scenarios (base net -> scenario net; tax recomputed "
          "on combined income):")
    scenarios = [
        ("teacher/entry + tutoring income (tutors 8 sessions)",
         "teacher", "entry", {"tutoring_income": tut}),
        ("teacher/entry + tutoring expense (pays for one child)",
         "teacher", "entry", {"tutoring_expense": tut}),
        ("teacher/entry + tutoring income AND expense",
         "teacher", "entry",
         {"tutoring_income": tut, "tutoring_expense": tut}),
        ("construction_worker/entry + teen part-time income",
         "construction_worker", "entry", {"part_time_income": pt}),
        ("teacher/entry + teen part-time income",
         "teacher", "entry", {"part_time_income": pt}),
    ]
    fails, tight = [], []
    for label, pid, tier, kw in scenarios:
        base = simulate(prices, wages[pid], tier)
        scen = simulate(prices, wages[pid], tier, **kw)
        delta = scen["net"] - base["net"]
        if "SURVIVAL FAIL" in scen["flags"]:
            fails.append(label)
        if "TIGHT" in scen["flags"]:
            tight.append(label)
        print(f"  {label:52} base net {base['net']:>6} -> {scen['net']:>6} "
              f"(delta {delta:+d}, save {scen['rate']}%)  "
              f"{', '.join(scen['flags']) or '-'}")
    print(f"v4 scenario SURVIVAL FAIL rows: {fails}")
    print(f"v4 scenario TIGHT rows: {tight}")


def print_taxi_weather_surge(prices, bands, variant=False,
                             rent_overrides=None):
    """Queue 29 / v7 (Unit KC): the taxi weather-surge section,
    printed by the default run and — Queue 35 (Unit MD) — by
    the --shibnagar variant as its own table.

    With variant=False and no rent_overrides this is the
    District 1 section exactly as KC printed it. With
    variant=True the same rows are computed on the rents the
    caller passes (the variant's own rents, not quoted from
    the District 1 run) — rent_override=None is the District
    1 rent, so a missing override is the D1 figure, never an
    invented one.
    """
    # Queue 35 / Unit MD: the rents this section runs on —
    # the taxi driver's rent for the single-earner rows and
    # the construction worker's rent for the second-earner
    # rows (the first earner in every pairing).
    taxi_rent = (rent_overrides or {}).get("taxi_driver")
    cw_rent = (rent_overrides or {}).get("construction_worker")
    # Queue 29 / v7 (Unit KC): the taxi weather surge — the
    # settlement scales a taxi driver's gross by taxi_factor =
    # 1 + 0.25 × rain_days/30 + 0.5 × storm_days/30
    # (engine._settle_month), while the tool modelled taxi pay
    # flat. The EY month's weather (seed ey-measure: rain on
    # day_index 2 and 28, storm on 3 and 22) is 2 rain days +
    # 2 storm days, factor exactly 1.05 — measured, not
    # assumed: all six taxi drivers in that world settled at
    # exactly band × 1.05. simulate(..., taxi_rain_days=...,
    # taxi_storm_days=...) scales the taxi gross by the
    # settlement's formula, with tax and uplift recomputed on
    # the surged gross as the settlement does; the rental stays
    # the flat 5,200. The base table stays flat — the canonical
    # bands — and this section is the weather scenario. The
    # bridge check stays flat too: the factor is ≥ 1 for any
    # weather, so the flat lines are the conservative case —
    # the surge only ever shrinks a dip, as the early figures
    # below show. No tuning call.
    if variant:
        print()
        print("shibnagar taxi weather-surge month (Unit MD — the "
              "same KC section on Shibnagar's own rents: 2 rain "
              "days, 2 storm days, taxi_factor 1.05; taxi gross "
              "x 1.05, tax and uplift recomputed on the surged "
              "gross):")
    else:
        print()
        print("taxi weather-surge month (Unit KC — the EY month's "
              "weather: 2 rain days, 2 storm days, taxi_factor 1.05;"
              " taxi gross x 1.05, tax and uplift recomputed on the"
              " surged gross):")
    print(f"{'profession':28} {'tier':7} {'flat gross':>10} "
          f"{'surged':>7} {'flat net':>8} {'surged net':>10} "
          f"{'delta net':>9}")
    for tier in ("entry", "mid", "senior"):
        flat = simulate(prices, bands["taxi_driver"], tier,
                        rent_override=taxi_rent)
        surged = simulate(
            prices, bands["taxi_driver"], tier,
            rent_override=taxi_rent,
            taxi_rain_days=TAXI_WEATHER_MEASURED_RAIN_DAYS,
            taxi_storm_days=TAXI_WEATHER_MEASURED_STORM_DAYS)
        print(f"{flat['profession']:28} {flat['tier']:7} "
              f"{flat['gross']:>10} {surged['gross']:>7} "
              f"{flat['net']:>8} {surged['net']:>10} "
              f"{surged['net'] - flat['net']:+9d}")
    cab_rent = prices["taxi_fares"]["cab_rental_ncr_per_day"]
    # Queue 33 / Unit MB: the renting-cab row at every tier,
    # as in the District 1 base table (Unit MA) — the entry
    # row alone understated the section: the mid/senior
    # renting rows rise by exactly the same surge deltas as
    # the owning driver (+691 / +1,080), because the rental
    # stays the flat 5,200 unsurged. Measured live before
    # wiring: mid 6,750 -> 7,441, senior 14,550 -> 15,630.
    for tier in ("entry", "mid", "senior"):
        flat = simulate(prices, bands["taxi_driver"], tier,
                        extra_daily_cost=cab_rent,
                        label_suffix=" (renting cab)",
                        rent_override=taxi_rent)
        surged = simulate(
            prices, bands["taxi_driver"], tier,
            extra_daily_cost=cab_rent,
            label_suffix=" (renting cab)",
            rent_override=taxi_rent,
            taxi_rain_days=TAXI_WEATHER_MEASURED_RAIN_DAYS,
            taxi_storm_days=TAXI_WEATHER_MEASURED_STORM_DAYS)
        print(f"{flat['profession']:28} {flat['tier']:7} "
              f"{flat['gross']:>10} {surged['gross']:>7} "
              f"{flat['net']:>8} {surged['net']:>10} "
              f"{surged['net'] - flat['net']:+9d}")
    # The same surge on the taxi second earner: the early
    # position is where the dips live (the measured position
    # dips 0 flat and surged for every pairing and tier), so
    # the table prints the early minbal flat vs surged beside
    # the net flat vs surged. The surge shrinks all three
    # early dips — the HD senior dip, the KA renting senior
    # dip, and the IB entry renting dips — but closes none of
    # them. The senior owning row (Queue 45 / Unit MN) dips 0
    # flat and surged at every tier, so there is no dip for
    # the surge to shrink — its nets rise by exactly the
    # senior taxi surge (+1,080 at every tier).
    if variant:
        print()
        print("shibnagar taxi-driver second earner weather-surge "
              "month (Unit MD — same EY weather, on Shibnagar "
              "rents; early-position minbal flat vs surged, net "
              "flat vs surged; the measured position dips 0 flat "
              "and surged for every pairing and tier):")
    else:
        print()
        print("taxi-driver second earner weather-surge month (Unit KC"
              " — same EY weather; early-position minbal flat vs"
              " surged, net flat vs surged; the measured position"
              " dips 0 flat and surged for every pairing and tier):")
    print(f"{'second earner':28} {'tier':7} {'early flat':>10} "
          f"{'early surged':>12} {'net flat':>8} {'net surged':>10}")
    for second_label, second_kw in (
            ("taxi-driver (entry, owning)",
             {"second_earner": "taxi_driver"}),
            ("taxi-driver (mid, owning)",
             {"second_earner": "taxi_driver",
              "second_earner_tier": "mid"}),
            ("taxi-driver (mid, renting)",
             {"second_earner": "taxi_driver",
              "second_earner_tier": "mid",
              "second_earner_renting_cab": True}),
            # Queue 34 / Unit MC: the entry renting second
            # earner (Unit IB) — measured but unprinted until
            # now; the surge shrinks its early dips by the
            # entry taxi surge (+455 net at every tier).
            # Queue 36 / Unit ME: DECIDED — the renting
            # senior-tier taxi second earner stays allowed
            # but unprinted. simulate() computes it (the
            # senior wage and the flat rental are both
            # sourced), but no row is printed here and no
            # bridge line is wired for it in either check:
            # no measured household pairs the construction
            # worker with a senior taxi driver (§12 standing
            # rule), and every renting row sits beside its
            # owning row — the owning senior second earner
            # is itself unmodelled, so the row would dangle
            # (and its net would publish the owning senior
            # net by implication, net + 5,200). A live check
            # while deciding found the row would add no
            # finding (the senior pay covers the cost-only
            # days at every tier). Re-opens only if a
            # measured household appears (Queue 37 Unit MF).
            # Queue 44 / Unit MM re-opened 2026-11-26 — the
            # measured household has appeared (ML: HH000030
            # and HH000042), so the owning senior row is now
            # wired and the dangling argument FALLS: a
            # renting row beside it would no longer dangle.
            # DECIDED on the re-measured numbers: the
            # renting row still stays allowed but unprinted,
            # now on the no-finding reason alone — re-measured
            # on ME's own terms (senior wage 36,000, flat
            # 5,200 rental), the dip is 0 at every tier and
            # storm position, the net is exactly 5,200 below
            # the owning senior driver at every tier and
            # position, and the bridge line would be the
            # trivial 10,000 + 0 = 10,000 — the same line
            # the owning senior row just wired. Its net is
            # now fully implied by the wired owning net plus
            # the flat-rental rule, so the row adds nothing
            # new. Full detail: V7 report §33.
            # Queue 45 / Unit MN: the senior owning pairing
            # joins this table — MM wired it in the IC
            # section and both bridge checks, but the surge's
            # effect on its row was unprinted. It is per-fare,
            # so its gross DOES surge with the taxi weather:
            # early 0 -> 0 at every tier, nets +1,080 at every
            # tier (23,950 -> 25,030, 27,194 -> 28,274,
            # 30,651 -> 31,731) — exactly the senior
            # single-earner taxi surge delta. The renting
            # senior-tier taxi second earner stays allowed but
            # unprinted (V7 §33) — Queue 46 Unit MO measures
            # it on the surge pattern and decides it stays
            # unprinted. Full detail: V7 report §§34–35.
            # Queue 46 / Unit MO: the renting senior-tier
            # taxi second earner on the KC surge pattern —
            # measured beside the now-printed senior owning
            # row (every tier x every storm position, flat
            # vs surged, both cities): early dip 0 flat AND
            # surged at every tier and position, nets
            # 18,750 -> 19,830, 21,994 -> 23,074,
            # 25,451 -> 26,531 (+1,080 at every tier —
            # exactly the senior taxi surge), every net
            # exactly 5,200 below the owning surged net,
            # every trajectory ends exactly at net. The
            # surge changes nothing the flat rows hide, so
            # the pairing stays allowed but unprinted —
            # its surged figures are fully implied by the
            # printed owning row plus the flat 5,200
            # rental rule — and no bridge line is wired
            # (it would be the trivial 10,000 + 0 =
            # 10,000, the line the owning senior row
            # already wires). The table is now closed:
            # five pairings printed, the sixth decided
            # unprinted with a measured reason. Full
            # detail: V7 report §35.
            # Queue 37 / Unit MF checked 2026-11-25 — MF
            # checked the live world (seed mf-measure, 120
            # population, 90 days) and no measured household
            # appears: 0 senior taxi-driver second earners
            # and 0 senior civil-engineer second earners in
            # construction-worker-headed households, so the
            # §12 rule stands and nothing is wired. Note the
            # world's one senior-band taxi driver (NEX000032,
            # tier 4, 36,000) is a household head, not a
            # second earner — senior here means tier >= 3,
            # since TIER_WAGE_KEYS maps tiers 3-5 to the
            # senior band. Full detail: V7 report §26.
            # Queue 38 / Unit MG checked 2026-11-25 — MG
            # swept the same check across five seeds
            # (mg-seed-1..5, 120 population, 90 days each):
            # 0 senior taxi-driver and 0 senior civil-
            # engineer second earners in construction-
            # worker-headed households in every seed, so
            # the §12 rule stands on the broader base and
            # nothing is wired. Senior second earners do
            # occur in those worlds (a tier-3 shop owner,
            # two tier-3 business owners) — just never a
            # senior taxi driver or civil engineer under a
            # construction-worker head. Full detail: V7
            # report §27.
            # Queue 39 / Unit MH checked 2026-11-25 — MH
            # ran the same check over a longer horizon (two
            # seeds, mh-seed-1/2, 120 population, 365 days
            # each): 0 senior taxi-driver and 0 senior
            # civil-engineer second earners in construction-
            # worker-headed households in either seed, so
            # the §12 rule stands over the longer horizon
            # too and nothing is wired. The longer horizon
            # does grow the senior bands (4 senior-band
            # taxi drivers and 3-4 senior-band civil
            # engineers per world, up from 0-2 at 90 days)
            # and senior second earners in other professions
            # do occur (a tier-3 teacher, a tier-5 shop
            # owner, a tier-4 police officer, a tier-3
            # chef) — just never a senior taxi driver or
            # civil engineer under a construction-worker
            # head. Full detail: V7 report §28.
            # Queue 40 / Unit MI checked 2026-11-25 — MI ran
            # the same check in a larger world (seed mi-seed-1,
            # 300 population, 365 days) and the absence BROKE
            # for one pairing: HH000086 pairs a construction-
            # worker head with a senior civil-engineer second
            # earner (tier 5, 65,000/month), so the senior CE
            # pairing is now wired (IC section + both bridge
            # checks, V7 report §29) and the §12 rule stands
            # only for the senior taxi driver. No senior taxi-
            # driver second earner appears in the larger world
            # either (0 targets in mi-seed-1, 9 senior-band
            # taxi drivers in it), so the renting senior-tier
            # taxi second earner stays allowed but unprinted
            # and no row is added here.
            # Queue 41 / Unit MJ checked 2026-11-25 — MJ ran
            # the MF pairing query WITHOUT the construction-
            # worker-head restriction on the larger worlds
            # (mi-seed-1 re-run + fresh mj-seed-2, 300
            # population, 365 days each): senior taxi
            # drivers DO sit on the second-earner side — 6
            # in mi-seed-1 and 5 in mj-seed-2, under doctor,
            # teacher, shop-owner, business-owner, pilot,
            # software-developer, civil-engineer and taxi-
            # driver heads — but 0 under a construction-
            # worker head in either world, so the absence is
            # specific to the construction-worker pairing
            # and nothing is wired: the tool models the
            # construction-worker household only. The fresh
            # seed corroborates the MI wiring — HH000028
            # pairs a construction-worker head with a senior
            # civil-engineer second earner (tier 4, 65,000).
            # Full detail: V7 report §30.
            # Queue 42 / Unit MK checked 2026-11-26 — MK ran
            # the MJ query WITH the head's current wage joined
            # (e.wage_per_month) on the same two worlds
            # (mi-seed-1 + mj-seed-2 re-runs, 300 population,
            # 365 days each): exactly ONE senior taxi-driver
            # second earner sits under a head earning <=
            # 25,000 — mi-seed-1 HH000061, teacher head Jamal
            # Begum at the mid-tier 24,000, second earner
            # Tamim Sarkar (tier 4, 36,000) — so the strong
            # wage-band hypothesis (none under any <= 25,000
            # head) is REFUTED. But none sits under a head
            # earning <= 20,000 in either world, and every
            # head earning <= 20,000 in both worlds IS a
            # construction worker (17 heads, all at the flat
            # senior 20,000), so at the construction-worker
            # wage the profession and the wage band are
            # confounded — neither explanation is established.
            # No wiring: the tool models the construction-
            # worker household only. Full detail: V7 report §31.
            # Queue 43 / Unit ML checked 2026-11-26 — ML ran
            # the MK head-wage query on five fresh seeds
            # (ml-seed-1..5, 300 population, 365 days each):
            # a low-wage head who is NOT a construction worker
            # DOES exist — ml-seed-1 HH000035, shop-owner head
            # Sabbir Fakir at the entry 12,000 — but he holds
            # no senior taxi-driver second earner, and the
            # sweep's bigger finding settles the question
            # another way: the pairing appears under a
            # construction-worker head TWICE — ml-seed-1
            # HH000030 (head Sohel Howlader, tier 5, 20,000;
            # Ishrat Chowdhury, taxi tier 4, 36,000) and
            # ml-seed-3 HH000042 (head Karim Biswas, tier 5,
            # 20,000; Rina Saha, taxi tier 5, 36,000) — so
            # the §12 taxi half is REFUTED: the absence
            # across nine worlds was chance on a thin base,
            # not the profession and not the wage band. No
            # wiring in this unit (the ML spec says record
            # and stop); wiring the senior taxi rows on the
            # MI pattern is Queue 44. Full detail: V7 report §32.
            # Queue 44 / Unit MM checked 2026-11-26 — MM
            # re-ran the two holding seeds (ml-seed-1 and
            # ml-seed-3, 300 population, 365 days each) and
            # both pairings reproduce exactly (HH000030 and
            # HH000042, same heads and second earners, same
            # tiers and wages), so the senior taxi rows are
            # now wired on the MI pattern (IC section + both
            # bridge checks, V7 report §33): the per-fare
            # senior pay lands daily, so the early dip is 0
            # at every tier (nets 23,950 / 27,194 / 30,651)
            # and the bridge line is 10,000 + 0 = 10,000 in
            # both cities. The §12 taxi half now falls with
            # the CE half — no part of the §12 absence rule
            # stands. The ME renting decision was re-opened
            # beside it and stays allowed-but-unprinted on
            # the re-measured no-finding reason alone (the
            # dangling argument falls now that the owning
            # senior row is modelled).
            ("taxi-driver (entry, renting)",
             {"second_earner": "taxi_driver",
              "second_earner_renting_cab": True}),
            # Queue 45 / Unit MN: the senior owning second
            # earner — measured (ML) and wired (MM) in the IC
            # section, now printed here too: the surge raises
            # its nets by exactly the senior taxi surge
            # (+1,080 at every tier) and its early dip stays 0.
            ("taxi-driver (senior, owning)",
             {"second_earner": "taxi_driver",
              "second_earner_tier": "senior"})):
        for tier in ("entry", "mid", "senior"):
            w = bands["construction_worker"]
            early = simulate(prices, w, tier,
                             storm_days=STORM_EARLY_DAYS,
                             rent_override=cw_rent,
                             **second_kw)
            early_surged = simulate(
                prices, w, tier, storm_days=STORM_EARLY_DAYS,
                rent_override=cw_rent,
                taxi_rain_days=TAXI_WEATHER_MEASURED_RAIN_DAYS,
                taxi_storm_days=TAXI_WEATHER_MEASURED_STORM_DAYS,
                **second_kw)
            print(f"{second_label:28} {tier:7} "
                  f"{early['min_balance']:>10} "
                  f"{early_surged['min_balance']:>12} "
                  f"{early['net']:>8} "
                  f"{early_surged['net']:>10}")


def print_shibnagar_variant(prices, d1_rows, start_balances):
    """Queue 9 / v5 (Unit AX): the --shibnagar variant table.

    Re-runs the same 30-day simulation over Shibnagar's priced
    residential stock: each profession rents at its SHIBNAGAR_RENT_TIER
    (tier-4 professions capped at tier 3 — the town has no tier-4/5
    homes), at the rent the city file itself carries. Wages, living
    costs, taxes, business P&L and starting balances are unchanged, so
    the comparison at the end is a pure rent effect.
    """
    rents, stock = load_shibnagar_rents(prices)
    capped = sorted(pid for pid, tier in RENT_TIER.items()
                    if SHIBNAGAR_RENT_TIER[pid] != tier)
    print("shibnagar variant (Unit AX): same 30-day simulation over "
          "data/city2-shibnagar.json residential stock")
    print(f"  priced residential stock: "
          + ", ".join(f"tier {t}: {rents[t]} NCr/mo "
                      f"({stock[t]} units)" for t in sorted(rents))
          + " — each tier's rent equals the prices.json tier table "
          "(asserted, not assumed)")
    print(f"  no tier-4/5 homes exist in Shibnagar; capped at tier 3: "
          f"{', '.join(capped)} (rent 12000 -> 6000)")
    print(f"  7 of 18 properties unpriced (ghat, bus stand, school, "
          f"clinic, town office, 2 farmland plots) — civic/plot stock, "
          f"not homes")
    rows = []
    for w in prices["wages_monthly"]:
        pid = w["profession_id"]
        override = rents[SHIBNAGAR_RENT_TIER[pid]]
        for tier in ("entry", "mid", "senior"):
            rows.append(simulate(prices, w, tier, rent_override=override))
        if pid == "taxi_driver":
            cab_rent = prices["taxi_fares"]["cab_rental_ncr_per_day"]
            # Queue 32 / Unit MA: the renting-cab row at every
            # tier, as in the District 1 base table — the same
            # flat 5,200/month rental on the variant's own
            # rents. Measured identical to District 1 at every
            # tier (the taxi rent tier is unchanged in
            # Shibnagar), verified by the MA tests.
            for tier in ("entry", "mid", "senior"):
                rows.append(simulate(prices, w, tier,
                                     extra_daily_cost=cab_rent,
                                     label_suffix=" (renting cab)",
                                     rent_override=override))
    print(f"{'profession':28} {'tier':7} {'gross':>7} {'tax':>6} {'rent':>6} "
          f"{'costs':>6} {'net/mo':>8} {'save%':>6} {'minbal':>8}  flags")
    for r in rows:
        print(f"{r['profession']:28} {r['tier']:7} {r['gross']:>7} "
              f"{r['tax']:>6} {r['rent']:>6} {r['costs_total']:>6} "
              f"{r['net']:>8} {r['rate']:>6} {r['min_balance']:>8}  "
              f"{', '.join(r['flags']) or '-'}")
    print()
    fails = [r for r in rows if "SURVIVAL FAIL" in r["flags"]]
    fast = [r for r in rows if "IMPLAUSIBLY FAST" in r["flags"]]
    tight = [r for r in rows if "TIGHT" in r["flags"]]
    print(f"shibnagar SURVIVAL FAIL rows: "
          f"{[r['profession'] + '/' + r['tier'] for r in fails]}")
    print(f"shibnagar IMPLAUSIBLY FAST rows: "
          f"{[r['profession'] + '/' + r['tier'] for r in fast]}")
    print(f"shibnagar TIGHT rows: "
          f"{[r['profession'] + '/' + r['tier'] for r in tight]}")
    print("shibnagar senior savings rates: " + ", ".join(
        f"{r['pid']} {r['rate']}%" for r in rows if r["tier"] == "senior"))
    print()
    print("shibnagar first-month bridge check (same starting balances):")
    bridge_fail = []
    bands = {w["profession_id"]: w for w in prices["wages_monthly"]}
    # Queue 29 / v7 (Unit KD): the two-earner bridge lines —
    # the same IA/JA/KA lines the District 1 check prints,
    # re-run on Shibnagar rents. The first earner is the
    # construction worker (tier 1) in every pairing, and
    # Shibnagar's tier-1 rent is the prices.json tier-1 rent
    # (2,500 — asserted by load_shibnagar_rents, not assumed),
    # so the figures are identical by construction — verified
    # live by the KD tests (all 90 two-earner rows equal). The
    # lines are wired here rather than quoted from the District
    # 1 run, so the variant's check stands on its own rents; a
    # failing line joins BRIDGE FAIL, as in District 1.
    shib_rent = rents[SHIBNAGAR_RENT_TIER["construction_worker"]]
    for r in rows:
        if r["tier"] != "entry" or r["pid"] == "taxi_driver" and "renting" in r["profession"]:
            continue
        start = start_balances.get(r["pid"], 0)
        worst = start + r["min_balance"]
        status = "OK" if worst >= 0 else "BRIDGE FAIL"
        if worst < 0:
            bridge_fail.append(r["pid"])
        print(f"  {r['pid']:22} start {start:>6} + dip {r['min_balance']:>7} = {worst:>7}  {status}")
        if r["pid"] == "construction_worker":
            # Queue 30 / Unit KE: the single-earner storm line —
            # the same worst storm-position dip the District 1
            # check prints (Unit GE), re-run on Shibnagar rents.
            # Queue 31 / Unit LA: the line sweeps tiers like the
            # District 1 line — the minimum across the
            # construction worker's tiers and the four storm
            # positions, on the variant's own rents. Measured
            # per-tier worst dips are entry −500, mid −595,
            # senior −726 on both rents (the tier-1 rent is
            # identical, and the dip is the first earner's own),
            # so the line is 5,000 − 726 = 4,274 in both cities.
            # A failing line joins BRIDGE FAIL, as in
            # District 1.
            worst_storm = min(
                simulate(prices, bands["construction_worker"],
                         tier, storm_days=pos,
                         rent_override=shib_rent)["min_balance"]
                for tier in ("entry", "mid", "senior")
                for pos in (STORM_EARLY_DAYS, STORM_MID_DAYS,
                            STORM_LATE_DAYS, STORM_MEASURED_DAYS))
            storm_worst = start + worst_storm
            storm_status = "OK" if storm_worst >= 0 else "BRIDGE FAIL"
            if storm_worst < 0:
                bridge_fail.append("construction_worker (storm)")
            print(f"  {r['pid']:22} start {start:>6} + storm dip "
                  f"{worst_storm:>7} = {storm_worst:>7}  {storm_status}"
                  f"  (worst storm position, all tiers)")
            # Unit IA (Queue 26): the mixed two-earner bridge
            # lines — the worst mixed minbal per second-earner
            # profession, against the combined canonical start.
            for second_pid, second_label in (
                    ("taxi_driver", "taxi-driver"),
                    ("civil_engineer", "civil-engineer")):
                worst_mixed = min(
                    simulate(prices, bands["construction_worker"],
                             tier, storm_days=pos,
                             rent_override=shib_rent,
                             second_earner=second_pid)["min_balance"]
                    for tier in ("entry", "mid", "senior")
                    for pos in (STORM_EARLY_DAYS, STORM_MID_DAYS,
                                STORM_LATE_DAYS, STORM_MEASURED_DAYS))
                mixed_start = (start_balances["construction_worker"]
                               + start_balances[second_pid])
                mixed_worst = mixed_start + worst_mixed
                mixed_status = ("OK" if mixed_worst >= 0
                                else "BRIDGE FAIL")
                if mixed_worst < 0:
                    bridge_fail.append(
                        f"construction_worker + {second_pid}")
                print(f"  {'construction_worker + ' + second_label:36}"
                      f" start {mixed_start:>6} + mixed dip "
                      f"{worst_mixed:>7} = {mixed_worst:>7}  "
                      f"{mixed_status}  (worst mixed storm position)")
            # Unit JA (Queue 27): the GD same-tier line and the
            # IC other-tier lines, wired the same way.
            worst_same = min(
                simulate(prices, bands["construction_worker"],
                         tier, storm_days=pos,
                         rent_override=shib_rent,
                         second_earner=True)["min_balance"]
                for tier in ("entry", "mid", "senior")
                for pos in (STORM_EARLY_DAYS, STORM_MID_DAYS,
                            STORM_LATE_DAYS, STORM_MEASURED_DAYS))
            same_start = 2 * start_balances["construction_worker"]
            same_worst = same_start + worst_same
            same_status = ("OK" if same_worst >= 0
                           else "BRIDGE FAIL")
            if same_worst < 0:
                bridge_fail.append(
                    "construction_worker + construction_worker")
            print(f"  {'construction_worker + construction-worker':36}"
                  f" start {same_start:>6} + same-tier dip "
                  f"{worst_same:>7} = {same_worst:>7}  "
                  f"{same_status}  (worst same-tier storm position)")
            # Queue 40 / Unit MI: the senior civil-engineer
            # second earner joins this loop too — the same
            # measured household (seed mi-seed-1, HH000086)
            # as in District 1, on the variant's own rents.
            # The line is 30,000 − 17,758 = 12,242, identical
            # to District 1 (the two-earner rows rent at tier
            # 1, and Shibnagar's tier-1 rent is the prices.json
            # tier-1 rent, 2,500 — the MD identity). The senior
            # taxi-driver second earner stays out: no measured
            # household pairs the construction worker with one.
            # Queue 44 / Unit MM: the senior taxi-driver
            # second earner joins this loop too — the same
            # measured households (ml-seed-1 HH000030,
            # ml-seed-3 HH000042) as in District 1, on the
            # variant's own rents. The line is 10,000 + 0 =
            # 10,000, identical to District 1 (the two-earner
            # rows rent at tier 1 — the MD identity).
            for second_pid, second_tier, second_label in (
                    ("taxi_driver", "mid", "taxi-driver (mid)"),
                    ("civil_engineer", "entry",
                     "civil-engineer (entry)"),
                    ("civil_engineer", "senior",
                     "civil-engineer (senior)"),
                    ("taxi_driver", "senior",
                     "taxi-driver (senior)")):
                worst_other = min(
                    simulate(prices, bands["construction_worker"],
                             tier, storm_days=pos,
                             rent_override=shib_rent,
                             second_earner=second_pid,
                             second_earner_tier=second_tier)
                    ["min_balance"]
                    for tier in ("entry", "mid", "senior")
                    for pos in (STORM_EARLY_DAYS, STORM_MID_DAYS,
                                STORM_LATE_DAYS,
                                STORM_MEASURED_DAYS))
                other_start = (start_balances["construction_worker"]
                               + start_balances[second_pid])
                other_worst = other_start + worst_other
                other_status = ("OK" if other_worst >= 0
                                else "BRIDGE FAIL")
                if other_worst < 0:
                    bridge_fail.append(
                        f"construction_worker + {second_pid}"
                        f" ({second_tier})")
                print(f"  {'construction_worker + ' + second_label:36}"
                      f" start {other_start:>6} + other-tier dip "
                      f"{worst_other:>7} = {other_worst:>7}  "
                      f"{other_status}  (worst other-tier storm"
                      " position)")
            # Unit KA (Queue 28): the renting mid-tier
            # taxi-second bridge line, wired the same way.
            worst_rent_mid = min(
                simulate(prices, bands["construction_worker"],
                         tier, storm_days=pos,
                         rent_override=shib_rent,
                         second_earner="taxi_driver",
                         second_earner_tier="mid",
                         second_earner_renting_cab=True)
                ["min_balance"]
                for tier in ("entry", "mid", "senior")
                for pos in (STORM_EARLY_DAYS, STORM_MID_DAYS,
                            STORM_LATE_DAYS, STORM_MEASURED_DAYS))
            rent_mid_start = (start_balances["construction_worker"]
                              + start_balances["taxi_driver"])
            rent_mid_worst = rent_mid_start + worst_rent_mid
            rent_mid_status = ("OK" if rent_mid_worst >= 0
                               else "BRIDGE FAIL")
            if rent_mid_worst < 0:
                bridge_fail.append(
                    "construction_worker + taxi_driver"
                    " (mid, renting)")
            print(f"  {'construction_worker + taxi-driver (mid, renting)'}"
                  f" start {rent_mid_start:>6} + renting dip "
                  f"{worst_rent_mid:>7} = {rent_mid_worst:>7}  "
                  f"{rent_mid_status}  (worst renting storm"
                  " position)")
    # Queue 32 / Unit MA: the renting line sweeps tiers like
    # the District 1 line — the worst minbal across the three
    # renting rows on the variant's own rents. Measured 0 at
    # every tier, so the line is 5,000 + 0 = 5,000 OK in both
    # cities. A failing line joins BRIDGE FAIL, as in
    # District 1.
    rent_rows = [r for r in rows if "renting" in r["profession"]]
    worst_rent = min(r["min_balance"] for r in rent_rows)
    start = start_balances.get("taxi_driver", 0)
    worst = start + worst_rent
    status = "OK" if worst >= 0 else "BRIDGE FAIL"
    if worst < 0:
        bridge_fail.append("taxi_driver (renting cab)")
    print(f"  {'taxi_driver (renting cab)':22} start {start:>6} + dip {worst_rent:>7} = {worst:>7}  {status}  (worst renting tier)")
    print(f"shibnagar BRIDGE FAIL rows: {bridge_fail}")
    # Queue 35 / Unit MD: the variant's own surge table — the
    # same KC section, computed on Shibnagar's own rents (the
    # taxi and construction-worker rents are both the tier-1
    # rent, 2,500 — asserted by load_shibnagar_rents, not
    # assumed — and the MD tests verify all 132 rows identical
    # to District 1). The section prints its own leading
    # blank line.
    print_taxi_weather_surge(
        prices, bands, variant=True,
        rent_overrides={
            "taxi_driver":
                rents[SHIBNAGAR_RENT_TIER["taxi_driver"]],
            "construction_worker": shib_rent})
    print()
    print("district 1 vs shibnagar (rent delta -> net delta; only the "
          "three capped professions differ):")
    d1_by_key = {(r["profession"], r["tier"]): r for r in d1_rows}
    for r in rows:
        d1r = d1_by_key[(r["profession"], r["tier"])]
        print(f"  {r['profession']:28} {r['tier']:7} "
              f"rent {d1r['rent']:>6} -> {r['rent']:>6} "
              f"({r['rent'] - d1r['rent']:+d})  "
              f"net {d1r['net']:>7} -> {r['net']:>7} "
              f"({r['net'] - d1r['net']:+d})  "
              f"{', '.join(r['flags']) or '-'}")
    ce = next(r for r in rows if r["profession"] == "civil_engineer"
              and r["tier"] == "entry")
    car = next(v["price_ncr"] for v in prices["vehicles"]
               if v["id"] == "car_small")
    t3 = next(r for r in prices["rent_monthly_by_tier"] if r["tier"] == 3)
    deposit = t3["buy_price_guide_ncr"] * prices["loans"]["mortgage"]["deposit_percent"] // 100
    print(f"shibnagar pacing: civil_engineer/entry saves {ce['net']} "
          f"NCr/mo -> car_small ({car}) in {round(car / ce['net'], 1)} "
          f"months; tier-3 deposit ({deposit}) in "
          f"{round(deposit / ce['net'], 1)} months")


def main():
    prices = load("prices.json")
    professions = load("professions.json")
    start_balances = {p["id"]: p.get("starting_balance_ncr", 0)
                      for p in professions["professions"]}

    rows = []
    for w in prices["wages_monthly"]:
        for tier in ("entry", "mid", "senior"):
            rows.append(simulate(prices, w, tier))
        if w["profession_id"] == "taxi_driver":
            cab_rent = prices["taxi_fares"]["cab_rental_ncr_per_day"]
            # Queue 32 / Unit MA: the renting-cab row at every
            # tier, not the entry tier alone — the rental is the
            # same flat 5,200/month at every tier (Unit KA
            # proved it for the second earner; Unit JB
            # confirmed the 26-day rule), so the tier moves the
            # pay, not the rental. Measured: mid net 6,750
            # (29.3%), senior net 14,550 (40.4%) — exactly
            # 5,200 below the owning driver at every tier,
            # minbal 0 at every tier.
            for tier in ("entry", "mid", "senior"):
                rows.append(simulate(prices, w, tier,
                                     extra_daily_cost=cab_rent,
                                     label_suffix=" (renting cab)"))

    print(f"{'profession':28} {'tier':7} {'gross':>7} {'tax':>6} {'rent':>6} "
          f"{'costs':>6} {'net/mo':>8} {'save%':>6} {'minbal':>8}  flags")
    for r in rows:
        print(f"{r['profession']:28} {r['tier']:7} {r['gross']:>7} "
              f"{r['tax']:>6} {r['rent']:>6} {r['costs_total']:>6} "
              f"{r['net']:>8} {r['rate']:>6} {r['min_balance']:>8}  "
              f"{', '.join(r['flags']) or '-'}")
    print()
    fails = [r for r in rows if "SURVIVAL FAIL" in r["flags"]]
    fast = [r for r in rows if "IMPLAUSIBLY FAST" in r["flags"]]
    tight = [r for r in rows if "TIGHT" in r["flags"]]
    print(f"professions simulated: {len(prices['wages_monthly'])} "
          f"(+ taxi rental variant); rows: {len(rows)}")
    print(f"SURVIVAL FAIL rows: {[r['profession'] + '/' + r['tier'] for r in fails]}")
    print(f"IMPLAUSIBLY FAST rows: {[r['profession'] + '/' + r['tier'] for r in fast]}")
    print(f"TIGHT rows: {[r['profession'] + '/' + r['tier'] for r in tight]}")

    seniors = [r for r in rows if r["tier"] == "senior"]
    print("senior savings rates: " + ", ".join(
        f"{r['pid']} {r['rate']}%" for r in seniors))

    # Business P&L reconciliation (Finding 6): computed profit vs the
    # canonical band in prices.json wages_monthly.
    print()
    print("business P&L (revenue - stock - premises - staff - other = profit vs canonical band):")
    bands = {w["profession_id"]: w for w in prices["wages_monthly"]}
    for pid in sorted(BUSINESS_PROFESSIONS):
        for tier in ("entry", "mid", "senior"):
            p = business_pnl(prices, pid, tier)
            band = bands[pid][tier]
            print(f"  {pid:15} {tier:7} rev {p['revenue']:>7} - stock "
                  f"{p['stock']:>6} - prem {p['premises']:>6} - staff "
                  f"{p['staff']:>6} - other {p['other']:>5} = profit "
                  f"{p['profit']:>7} (band {band}, delta {p['profit'] - band:+d})")

    # First-month bridge check (Finding 3): apply each profession's
    # starting balance to its entry row's zero-start trajectory.
    # Queue 24 / Unit GE: the construction_worker entry row also
    # prints its worst storm-position dip (the minimum month-1
    # balance across the four storm positions, Unit FB) against
    # the same starting balance — so the storm bridge is part of
    # the tool's output rather than a report-only observation
    # (V7 §5). A failing storm line joins BRIDGE FAIL.
    print()
    print("first-month bridge check (entry rows: starting balance + zero-start dip = worst month-1 balance):")
    bridge_fail = []
    for r in rows:
        if r["tier"] != "entry" or r["pid"] == "taxi_driver" and "renting" in r["profession"]:
            continue
        start = start_balances.get(r["pid"], 0)
        worst = start + r["min_balance"]
        status = "OK" if worst >= 0 else "BRIDGE FAIL"
        if worst < 0:
            bridge_fail.append(r["pid"])
        print(f"  {r['pid']:22} start {start:>6} + dip {r['min_balance']:>7} = {worst:>7}  {status}")
        if r["pid"] == "construction_worker":
            # Queue 31 / Unit LA: the storm line sweeps tiers
            # like the two-earner lines below (Unit IA) — the
            # minimum across the first earner's tiers and the
            # four storm positions. The GE line swept positions
            # at the entry tier only and printed the entry row's
            # worst (5,000 − 500 = 4,500), not the household's
            # worst across tiers: measured worst dips are entry
            # −500, mid −595, senior −726 (early worst at every
            # tier), so the line is now 5,000 − 726 = 4,274.
            # The start is the same 5,000 at every tier
            # (starting_balance_ncr is per profession, not per
            # tier), so the sweep stays one household's worst.
            worst_storm = min(
                simulate(prices, bands["construction_worker"],
                         tier, storm_days=pos)["min_balance"]
                for tier in ("entry", "mid", "senior")
                for pos in (STORM_EARLY_DAYS, STORM_MID_DAYS,
                            STORM_LATE_DAYS, STORM_MEASURED_DAYS))
            storm_worst = start + worst_storm
            storm_status = "OK" if storm_worst >= 0 else "BRIDGE FAIL"
            if storm_worst < 0:
                bridge_fail.append("construction_worker (storm)")
            print(f"  {r['pid']:22} start {start:>6} + storm dip "
                  f"{worst_storm:>7} = {storm_worst:>7}  {storm_status}"
                  f"  (worst storm position, all tiers)")
            # Queue 26 / Unit IA: the mixed two-earner bridge
            # lines — the worst mixed minbal per second-earner
            # profession (the minimum across the first earner's
            # tiers and the four storm positions), against the
            # combined canonical start: each earner brings their
            # own genesis balance (population.py seeds
            # starting_balance_ncr per profession, randomised
            # ±15% in the settlement — the bridge check is
            # canonical, HE). Taxi-driver second earner: 5,000 +
            # 5,000 = 10,000; civil-engineer second earner:
            # 5,000 + 25,000 = 30,000 — HD's prose (V7 §9)
            # carried GD's 2 × 5,000 figure for the CE household
            # too, which understates the engineer's start by
            # 20,000; the 10,000 − 8,623 = 1,377 figure is
            # corrected here to 30,000 − 8,623 = 21,377. A
            # failing mixed line joins BRIDGE FAIL.
            for second_pid, second_label in (
                    ("taxi_driver", "taxi-driver"),
                    ("civil_engineer", "civil-engineer")):
                worst_mixed = min(
                    simulate(prices, bands["construction_worker"],
                             tier, storm_days=pos,
                             second_earner=second_pid)["min_balance"]
                    for tier in ("entry", "mid", "senior")
                    for pos in (STORM_EARLY_DAYS, STORM_MID_DAYS,
                                STORM_LATE_DAYS, STORM_MEASURED_DAYS))
                mixed_start = (start_balances["construction_worker"]
                               + start_balances[second_pid])
                mixed_worst = mixed_start + worst_mixed
                mixed_status = ("OK" if mixed_worst >= 0
                                else "BRIDGE FAIL")
                if mixed_worst < 0:
                    bridge_fail.append(
                        f"construction_worker + {second_pid}")
                print(f"  {'construction_worker + ' + second_label:36}"
                      f" start {mixed_start:>6} + mixed dip "
                      f"{worst_mixed:>7} = {mixed_worst:>7}  "
                      f"{mixed_status}  (worst mixed storm position)")
            # Queue 27 / Unit JA: the remaining two-earner
            # bridge lines — the GD same-tier worst dip and the
            # IC other-tier worst dips, wired the same way as
            # IA's mixed lines: the combined canonical start
            # (each earner brings their own genesis balance)
            # plus the worst minbal (the minimum across the
            # first earner's tiers and the four storm positions).
            # Same-tier: senior early −1,231 against 2 × 5,000
            # = 10,000. Mid-tier taxi-second: 0 against 10,000.
            # Entry civil-engineer-second: −3,210 against
            # 5,000 + 25,000 = 30,000. A failing line joins
            # BRIDGE FAIL — with these three lines, no
            # two-earner bridge figure is report-only.
            worst_same = min(
                simulate(prices, bands["construction_worker"],
                         tier, storm_days=pos,
                         second_earner=True)["min_balance"]
                for tier in ("entry", "mid", "senior")
                for pos in (STORM_EARLY_DAYS, STORM_MID_DAYS,
                            STORM_LATE_DAYS, STORM_MEASURED_DAYS))
            same_start = 2 * start_balances["construction_worker"]
            same_worst = same_start + worst_same
            same_status = ("OK" if same_worst >= 0
                           else "BRIDGE FAIL")
            if same_worst < 0:
                bridge_fail.append(
                    "construction_worker + construction_worker")
            print(f"  {'construction_worker + construction-worker':36}"
                  f" start {same_start:>6} + same-tier dip "
                  f"{worst_same:>7} = {same_worst:>7}  "
                  f"{same_status}  (worst same-tier storm position)")
            # Queue 40 / Unit MI: the senior civil-engineer
            # second earner joins this loop — a measured
            # household appeared in the larger world (seed
            # mi-seed-1, 300 population, 365 days: HH000086
            # pairs a construction-worker head with a tier-5
            # civil engineer at 65,000/month). The line is
            # 30,000 − 17,758 = 12,242 (the worst minbal is
            # the entry tier at the early position — the
            # senior monthly lump lands day 30 while the
            # senior lifestyle uplift accrues daily). The
            # senior taxi-driver second earner stays out of
            # this loop: no measured household pairs the
            # construction worker with one, in the larger
            # world either.
            # Queue 44 / Unit MM: the senior taxi-driver
            # second earner joins this loop too — ML measured
            # the pairing under a construction-worker head
            # twice (ml-seed-1 HH000030, ml-seed-3 HH000042),
            # and MM re-ran both holding seeds and both
            # pairings reproduce exactly. The line is
            # 10,000 + 0 = 10,000 (combined canonical start
            # 5,000 + 5,000, worst minbal 0 at every tier and
            # position — the per-fare senior pay lands daily).
            for second_pid, second_tier, second_label in (
                    ("taxi_driver", "mid", "taxi-driver (mid)"),
                    ("civil_engineer", "entry",
                     "civil-engineer (entry)"),
                    ("civil_engineer", "senior",
                     "civil-engineer (senior)"),
                    ("taxi_driver", "senior",
                     "taxi-driver (senior)")):
                worst_other = min(
                    simulate(prices, bands["construction_worker"],
                             tier, storm_days=pos,
                             second_earner=second_pid,
                             second_earner_tier=second_tier)
                    ["min_balance"]
                    for tier in ("entry", "mid", "senior")
                    for pos in (STORM_EARLY_DAYS, STORM_MID_DAYS,
                                STORM_LATE_DAYS,
                                STORM_MEASURED_DAYS))
                other_start = (start_balances["construction_worker"]
                               + start_balances[second_pid])
                other_worst = other_start + worst_other
                other_status = ("OK" if other_worst >= 0
                                else "BRIDGE FAIL")
                if other_worst < 0:
                    bridge_fail.append(
                        f"construction_worker + {second_pid}"
                        f" ({second_tier})")
                print(f"  {'construction_worker + ' + second_label:36}"
                      f" start {other_start:>6} + other-tier dip "
                      f"{worst_other:>7} = {other_worst:>7}  "
                      f"{other_status}  (worst other-tier storm"
                      " position)")
            # Queue 28 / Unit KA: the renting mid-tier
            # taxi-second bridge line — the renting variant of
            # the IC other-tier pairing, wired the same way as
            # JA's lines: the combined canonical start (each
            # earner brings their own genesis balance: 5,000 +
            # 5,000 = 10,000) plus the worst renting minbal
            # (the minimum across the first earner's tiers and
            # the four storm positions). The rental is the same
            # flat 5,200/month at every tier, so the line
            # measures the tier's pay against the same rental.
            # A failing line joins BRIDGE FAIL.
            worst_rent_mid = min(
                simulate(prices, bands["construction_worker"],
                         tier, storm_days=pos,
                         second_earner="taxi_driver",
                         second_earner_tier="mid",
                         second_earner_renting_cab=True)
                ["min_balance"]
                for tier in ("entry", "mid", "senior")
                for pos in (STORM_EARLY_DAYS, STORM_MID_DAYS,
                            STORM_LATE_DAYS, STORM_MEASURED_DAYS))
            rent_mid_start = (start_balances["construction_worker"]
                              + start_balances["taxi_driver"])
            rent_mid_worst = rent_mid_start + worst_rent_mid
            rent_mid_status = ("OK" if rent_mid_worst >= 0
                               else "BRIDGE FAIL")
            if rent_mid_worst < 0:
                bridge_fail.append(
                    "construction_worker + taxi_driver"
                    " (mid, renting)")
            print(f"  {'construction_worker + taxi-driver (mid, renting)'}"
                  f" start {rent_mid_start:>6} + renting dip "
                  f"{worst_rent_mid:>7} = {rent_mid_worst:>7}  "
                  f"{rent_mid_status}  (worst renting storm"
                  " position)")
    # The renting-cab variant shares the taxi driver's starting balance.
    # Queue 32 / Unit MA: the line sweeps tiers like the storm
    # line (Unit LA) — the worst minbal across the three renting
    # rows against the same 5,000 start. Measured minbal is 0
    # at every tier, so the line is still 5,000 + 0 = 5,000 OK —
    # unchanged in figure, now honestly the household's worst
    # across tiers rather than the entry row's. A failing line
    # joins BRIDGE FAIL, as in District 1.
    rent_rows = [r for r in rows if "renting" in r["profession"]]
    worst_rent = min(r["min_balance"] for r in rent_rows)
    start = start_balances.get("taxi_driver", 0)
    worst = start + worst_rent
    status = "OK" if worst >= 0 else "BRIDGE FAIL"
    if worst < 0:
        bridge_fail.append("taxi_driver (renting cab)")
    print(f"  {'taxi_driver (renting cab)':22} start {start:>6} + dip {worst_rent:>7} = {worst:>7}  {status}  (worst renting tier)")
    print(f"BRIDGE FAIL rows: {bridge_fail}")

    # Pacing checks (entry tier, civil engineer = owner reference)
    ce = next(r for r in rows if r["profession"] == "civil_engineer"
              and r["tier"] == "entry")
    car = next(v["price_ncr"] for v in prices["vehicles"]
               if v["id"] == "car_small")
    t3 = next(r for r in prices["rent_monthly_by_tier"] if r["tier"] == 3)
    deposit = t3["buy_price_guide_ncr"] * prices["loans"]["mortgage"]["deposit_percent"] // 100
    print(f"pacing: civil_engineer/entry saves {ce['net']} NCr/mo -> "
          f"car_small ({car}) in {round(car / ce['net'], 1)} months; "
          f"tier-3 deposit ({deposit}) in {round(deposit / ce['net'], 1)} months")

    # Queue 22 / v6 (Unit EY): the day-wage storm month — the
    # measured live month (seeded 30-day engine run, 4 construction
    # workers): 28 worked days of 30, day_index 3 and 22
    # (1-based days 4 and 23) storm days with outdoor work
    # suspended, so the settlement pays 28/30 of the band. Same costs as the base table (uplift recomputed from
    # the reduced gross); tax recomputed on the reduced gross; the
    # reduced pay accrues evenly here — this section keeps the v6
    # even-spread figure; the storm-position section below (Unit FB
    # · Queue 23) models which days the storms fall on. No tuning
    # call: the storm month is weather, not a balance problem.
    print()
    print("day-wage storm month (Unit EY — measured 28 worked days of "
          "30, 2 storm days suspending outdoor work):")
    print(f"{'profession':28} {'tier':7} {'gross':>7} {'tax':>6} {'rent':>6} "
          f"{'costs':>6} {'net/mo':>8} {'save%':>6} {'minbal':>8}  flags")
    for tier in ("entry", "mid", "senior"):
        r = simulate(prices, bands["construction_worker"], tier,
                     day_wage_worked_days=28)
        base = simulate(prices, bands["construction_worker"], tier)
        print(f"{r['profession']:28} {r['tier']:7} {r['gross']:>7} "
              f"{r['tax']:>6} {r['rent']:>6} {r['costs_total']:>6} "
              f"{r['net']:>8} {r['rate']:>6} {r['min_balance']:>8}  "
              f"{', '.join(r['flags']) or '-'}"
              f"  (base net {base['net']}, save {base['rate']}%)")

    # Queue 23 / v7 (Unit FB): the storm-position scenario — the
    # same 28 worked days, but the two storm days fall early (days
    # 1-2), mid (15-16), or late (29-30), plus the measured
    # position (days 4 and 23, where the live month's storms
    # actually fell) and the v6 even-spread baseline for
    # comparison. The net is the same for every position (the
    # month pays the same 28/30 of the band whatever the days) —
    # only the month-1 minimum balance moves, and that is the
    # measured figure: pay lands only on worked days, so a storm
    # on day 1 dips deeper than a storm on day 29. The v6 minbal
    # (0 for every tier) is the even-spread figure, not a measured
    # one. No tuning call: the storm month is weather, not a
    # balance problem — the worst dip is measured, not fixed.
    print()
    print("day-wage storm-position month (Unit FB — same 28 worked "
          "days of 30; month-1 minbal by storm position):")
    print(f"{'profession':28} {'tier':7} {'early':>7} {'mid':>7} "
          f"{'late':>7} {'measured':>8} {'even':>7}  (net/mo)")
    for tier in ("entry", "mid", "senior"):
        w = bands["construction_worker"]
        early = simulate(prices, w, tier,
                         storm_days=STORM_EARLY_DAYS)
        mid = simulate(prices, w, tier,
                       storm_days=STORM_MID_DAYS)
        late = simulate(prices, w, tier,
                        storm_days=STORM_LATE_DAYS)
        measured = simulate(prices, w, tier,
                            storm_days=STORM_MEASURED_DAYS)
        even = simulate(prices, w, tier,
                        day_wage_worked_days=28)
        print(f"{early['profession']:28} {early['tier']:7} "
              f"{early['min_balance']:>7} {mid['min_balance']:>7} "
              f"{late['min_balance']:>7} {measured['min_balance']:>8} "
              f"{even['min_balance']:>7}  (net {early['net']})")

    # Queue 24 / v7 (Unit GD): the two-earner storm-position
    # scenario — the same 28 worked days and the same storm
    # positions, but the household has a second construction
    # worker at the same tier (same storm_days, same day-wage
    # rule) and its costs follow engine._living_costs for two
    # adults (food/clothing ×2, transport/eating ×2 per earner,
    # the rest flat; uplift per earner). The measured position
    # dips nothing — pay lands on days 1–3 before the day-4 storm
    # (Queue 25 Unit HA corrects the position from (3, 22)) — but the
    # early position dips DEEPER in NCr than the single-earner
    # household (two adults burn the daily cost with no pay
    # arriving on days 1–2): a second earner does not help the
    # early dip at all. The net is the same for every position;
    # only the month-1 minimum balance moves. No tuning call.
    print()
    print("two-earner storm-position month (Unit GD — same 28 worked "
          "days of 30; second earner is a construction worker at "
          "the same tier, same storm days; month-1 minbal by storm "
          "position):")
    print(f"{'profession':28} {'tier':7} {'early':>7} {'mid':>7} "
          f"{'late':>7} {'measured':>8} {'even':>7}  (net/mo)")
    for tier in ("entry", "mid", "senior"):
        w = bands["construction_worker"]
        early = simulate(prices, w, tier,
                         storm_days=STORM_EARLY_DAYS,
                         second_earner=True)
        mid = simulate(prices, w, tier,
                       storm_days=STORM_MID_DAYS,
                       second_earner=True)
        late = simulate(prices, w, tier,
                        storm_days=STORM_LATE_DAYS,
                        second_earner=True)
        measured = simulate(prices, w, tier,
                            storm_days=STORM_MEASURED_DAYS,
                            second_earner=True)
        even = simulate(prices, w, tier,
                        day_wage_worked_days=28,
                        second_earner=True)
        print(f"{early['profession']:28} {early['tier']:7} "
              f"{early['min_balance']:>7} {mid['min_balance']:>7} "
              f"{late['min_balance']:>7} {measured['min_balance']:>8} "
              f"{even['min_balance']:>7}  (net {early['net']})")

    # Queue 25 / v7 (Unit HD): the mixed-profession two-earner
    # storm-position scenario — the same 28 worked days and the
    # same storm positions, but the second earner works another
    # profession at the measured tier: a taxi driver at entry
    # (14,000, per-fare — storm days do not change the pay) or a
    # civil engineer at mid (38,000, monthly — the pay lands on
    # day 30 whatever the storm days). The household costs follow
    # engine._living_costs for two adults, and each earner carries
    # their own tax and uplift. The storm-position effect comes
    # from the first earner alone, against the second earner's
    # steady pay. The single-earner figures are printed beside
    # them for comparison; the GD same-tier figures are in the
    # section above. No tuning call.
    for second_pid, second_label in (
            ("taxi_driver", "taxi-driver second earner"
             " (entry 14,000, per-fare)"),
            ("civil_engineer", "civil-engineer second earner"
             " (mid 38,000, monthly)")):
        print()
        print(f"mixed-profession two-earner storm-position month "
              f"(Unit HD — same 28 worked days of 30; "
              f"{second_label}; month-1 minbal by storm position):")
        print(f"{'profession':28} {'tier':7} {'early':>7} {'mid':>7} "
              f"{'late':>7} {'measured':>8} {'even':>7}  (net/mo)"
              f"  single-early  single-measured")
        for tier in ("entry", "mid", "senior"):
            w = bands["construction_worker"]
            early = simulate(prices, w, tier,
                             storm_days=STORM_EARLY_DAYS,
                             second_earner=second_pid)
            mid = simulate(prices, w, tier,
                           storm_days=STORM_MID_DAYS,
                           second_earner=second_pid)
            late = simulate(prices, w, tier,
                            storm_days=STORM_LATE_DAYS,
                            second_earner=second_pid)
            measured = simulate(prices, w, tier,
                                storm_days=STORM_MEASURED_DAYS,
                                second_earner=second_pid)
            even = simulate(prices, w, tier,
                            day_wage_worked_days=28,
                            second_earner=second_pid)
            single_early = simulate(prices, w, tier,
                                    storm_days=STORM_EARLY_DAYS)
            single_measured = simulate(
                prices, w, tier, storm_days=STORM_MEASURED_DAYS)
            print(f"{early['profession']:28} {early['tier']:7} "
                  f"{early['min_balance']:>7} {mid['min_balance']:>7} "
                  f"{late['min_balance']:>7} "
                  f"{measured['min_balance']:>8} "
                  f"{even['min_balance']:>7}  (net {early['net']})"
                  f"  {single_early['min_balance']:>12} "
                  f"{single_measured['min_balance']:>15}")

    # Queue 26 / Unit IB: the renting-cab variant of the taxi
    # second earner — the same entry taxi driver (14,000,
    # per-fare), but renting the licensed cab at 200 NCr/day ×
    # 26 worked days = 5,200/month, the settlement's rule
    # (engine._settle_month charges rental_day × WORK_DAYS flat
    # for the month — not storm-dependent, not Sunday-excluded).
    # Modelled as a monthly cost line (5,200), accruing evenly
    # in the daily model like rent; the settlement charges the
    # same 5,200 once at month-end. The net drops by exactly
    # 5,200 at every tier against the owning-driver figures in
    # the section above; only the month-1 minimum balance moves
    # by position. No tuning call.
    print()
    print("renting-cab taxi-driver second earner storm-position "
          "month (Unit IB — same 28 worked days of 30; "
          "taxi-driver second earner (entry 14,000, per-fare) "
          "renting the cab at 200/day x 26 = 5,200/mo; month-1 "
          "minbal by storm position):")
    print(f"{'profession':28} {'tier':7} {'early':>7} {'mid':>7} "
          f"{'late':>7} {'measured':>8} {'even':>7}  (net/mo)"
          f"  owning-early  owning-measured")
    for tier in ("entry", "mid", "senior"):
        w = bands["construction_worker"]
        early = simulate(prices, w, tier,
                         storm_days=STORM_EARLY_DAYS,
                         second_earner="taxi_driver",
                         second_earner_renting_cab=True)
        mid = simulate(prices, w, tier,
                       storm_days=STORM_MID_DAYS,
                       second_earner="taxi_driver",
                       second_earner_renting_cab=True)
        late = simulate(prices, w, tier,
                        storm_days=STORM_LATE_DAYS,
                        second_earner="taxi_driver",
                        second_earner_renting_cab=True)
        measured = simulate(prices, w, tier,
                            storm_days=STORM_MEASURED_DAYS,
                            second_earner="taxi_driver",
                            second_earner_renting_cab=True)
        even = simulate(prices, w, tier,
                        day_wage_worked_days=28,
                        second_earner="taxi_driver",
                        second_earner_renting_cab=True)
        owning_early = simulate(prices, w, tier,
                                storm_days=STORM_EARLY_DAYS,
                                second_earner="taxi_driver")
        owning_measured = simulate(
            prices, w, tier, storm_days=STORM_MEASURED_DAYS,
            second_earner="taxi_driver")
        print(f"{early['profession']:28} {early['tier']:7} "
              f"{early['min_balance']:>7} {mid['min_balance']:>7} "
              f"{late['min_balance']:>7} "
              f"{measured['min_balance']:>8} "
              f"{even['min_balance']:>7}  (net {early['net']})"
              f"  {owning_early['min_balance']:>12} "
              f"{owning_measured['min_balance']:>15}")

    # Queue 26 / Unit IC: the second earner at another tier — a
    # mid-tier taxi driver (23,000, per-fare) and an entry civil
    # engineer (22,000, monthly), each at the tier the source
    # data actually gives (prices.json wages_monthly). The
    # measured-tier figures from the HD section above are printed
    # beside them for comparison; the first earner still varies
    # over entry/mid/senior. Storm days do not change the second
    # earner's pay (the per-fare rule has no storm days; the
    # monthly pay lands on day 30 regardless) — the
    # storm-position effect still comes from the first earner
    # alone. No tuning call.
    # Queue 40 / Unit MI: the senior civil-engineer second
    # earner joins this section — a measured household appeared
    # in the larger world (seed mi-seed-1, 300 population, 365
    # days: HH000086 pairs a construction-worker head with a
    # tier-5 civil engineer at 65,000/month), so the pairing is
    # wired here exactly like the IC pairings: the senior
    # monthly lump lands on day 30 while the senior lifestyle
    # uplift accrues daily, so the month-1 dip is DEEPER than
    # the mid-tier pairing despite the higher pay (entry early
    # −17,758 against the mid tier's −8,623). The bridge line
    # for it is wired in both bridge checks (JA loop). The
    # senior taxi-driver second earner stays unprinted — no
    # measured household pairs the construction worker with
    # one, in the larger world either (0 in mi-seed-1).
    # Queue 44 / Unit MM: the senior taxi-driver second
    # earner joins this section too — ML measured the pairing
    # under a construction-worker head TWICE (ml-seed-1
    # HH000030, ml-seed-3 HH000042), and MM re-ran both
    # holding seeds and both pairings reproduce exactly, so
    # the pairing is wired here exactly like the MI senior
    # CE pairing. The per-fare senior pay (36,000) lands
    # daily, so unlike the senior civil engineer it does NOT
    # deepen the month-1 dip: the early dip is 0 at every
    # tier (nets 23,950 / 27,194 / 30,651) — the pay-timing
    # contrast with the senior CE lump is the finding. The
    # bridge line for it is wired in both bridge checks (JA
    # loop): 10,000 + 0 = 10,000.
    for second_pid, second_tier, second_label in (
            ("taxi_driver", "mid",
             "taxi-driver second earner (mid 23,000, per-fare)"),
            ("civil_engineer", "entry",
             "civil-engineer second earner (entry 22,000,"
             " monthly)"),
            ("civil_engineer", "senior",
             "civil-engineer second earner (senior 65,000,"
             " monthly)"),
            ("taxi_driver", "senior",
             "taxi-driver second earner (senior 36,000,"
             " per-fare)")):
        print()
        print(f"second earner at another tier storm-position month"
              f" (Unit IC — same 28 worked days of 30; "
              f"{second_label}; month-1 minbal by storm position):")
        print(f"{'profession':28} {'tier':7} {'early':>7} {'mid':>7} "
              f"{'late':>7} {'measured':>8} {'even':>7}  (net/mo)"
              f"  measured-early  measured-measured")
        for tier in ("entry", "mid", "senior"):
            w = bands["construction_worker"]
            early = simulate(prices, w, tier,
                             storm_days=STORM_EARLY_DAYS,
                             second_earner=second_pid,
                             second_earner_tier=second_tier)
            mid = simulate(prices, w, tier,
                           storm_days=STORM_MID_DAYS,
                           second_earner=second_pid,
                           second_earner_tier=second_tier)
            late = simulate(prices, w, tier,
                            storm_days=STORM_LATE_DAYS,
                            second_earner=second_pid,
                            second_earner_tier=second_tier)
            measured = simulate(prices, w, tier,
                                storm_days=STORM_MEASURED_DAYS,
                                second_earner=second_pid,
                                second_earner_tier=second_tier)
            even = simulate(prices, w, tier,
                            day_wage_worked_days=28,
                            second_earner=second_pid,
                            second_earner_tier=second_tier)
            meas_early = simulate(prices, w, tier,
                                  storm_days=STORM_EARLY_DAYS,
                                  second_earner=second_pid)
            meas_measured = simulate(
                prices, w, tier, storm_days=STORM_MEASURED_DAYS,
                second_earner=second_pid)
            print(f"{early['profession']:28} {early['tier']:7} "
                  f"{early['min_balance']:>7} {mid['min_balance']:>7} "
                  f"{late['min_balance']:>7} "
                  f"{measured['min_balance']:>8} "
                  f"{even['min_balance']:>7}  (net {early['net']})"
                  f"  {meas_early['min_balance']:>14} "
                  f"{meas_measured['min_balance']:>17}")

    # Queue 28 / Unit KA: the renting-cab second earner at
    # another tier — the same mid-tier taxi driver (23,000,
    # per-fare) as the IC section above, but renting the
    # licensed cab at 200 NCr/day × 26 worked days =
    # 5,200/month, the settlement's rule (engine._settle_month
    # charges rental_day × WORK_DAYS flat for the month — not
    # storm-dependent, not Sunday-excluded). Modelled as a
    # monthly cost line (5,200), accruing evenly in the daily
    # model like rent; the settlement charges the same 5,200
    # once at month-end. The net drops by exactly 5,200 at
    # every tier against the owning mid-tier figures in the
    # section above; only the month-1 minimum balance moves
    # by position. A renting civil engineer is meaningless —
    # civil engineers hold no cab — so no such section
    # exists. No tuning call.
    print()
    print("renting-cab taxi-driver second earner at another tier"
          " storm-position month (Unit KA — same 28 worked days"
          " of 30; taxi-driver second earner (mid 23,000,"
          " per-fare) renting the cab at 200/day x 26 ="
          " 5,200/mo; month-1 minbal by storm position):")
    print(f"{'profession':28} {'tier':7} {'early':>7} {'mid':>7} "
          f"{'late':>7} {'measured':>8} {'even':>7}  (net/mo)"
          f"  owning-early  owning-measured")
    for tier in ("entry", "mid", "senior"):
        w = bands["construction_worker"]
        early = simulate(prices, w, tier,
                         storm_days=STORM_EARLY_DAYS,
                         second_earner="taxi_driver",
                         second_earner_tier="mid",
                         second_earner_renting_cab=True)
        mid = simulate(prices, w, tier,
                       storm_days=STORM_MID_DAYS,
                       second_earner="taxi_driver",
                       second_earner_tier="mid",
                       second_earner_renting_cab=True)
        late = simulate(prices, w, tier,
                        storm_days=STORM_LATE_DAYS,
                        second_earner="taxi_driver",
                        second_earner_tier="mid",
                        second_earner_renting_cab=True)
        measured = simulate(prices, w, tier,
                            storm_days=STORM_MEASURED_DAYS,
                            second_earner="taxi_driver",
                            second_earner_tier="mid",
                            second_earner_renting_cab=True)
        even = simulate(prices, w, tier,
                        day_wage_worked_days=28,
                        second_earner="taxi_driver",
                        second_earner_tier="mid",
                        second_earner_renting_cab=True)
        owning_early = simulate(prices, w, tier,
                                storm_days=STORM_EARLY_DAYS,
                                second_earner="taxi_driver",
                                second_earner_tier="mid")
        owning_measured = simulate(
            prices, w, tier, storm_days=STORM_MEASURED_DAYS,
            second_earner="taxi_driver",
            second_earner_tier="mid")
        print(f"{early['profession']:28} {early['tier']:7} "
              f"{early['min_balance']:>7} {mid['min_balance']:>7} "
              f"{late['min_balance']:>7} "
              f"{measured['min_balance']:>8} "
              f"{even['min_balance']:>7}  (net {early['net']})"
              f"  {owning_early['min_balance']:>12} "
              f"{owning_measured['min_balance']:>15}")

    print_taxi_weather_surge(prices, bands)

    if "--shibnagar" in sys.argv:
        print()
        print_shibnagar_variant(prices, rows, start_balances)

    if "--v3" in sys.argv or "--v4" in sys.argv:
        print()
        print_v4_scenarios(prices)


if __name__ == "__main__":
    main()
