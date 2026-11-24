# NEXORA — Economy Balance Simulator Report v7 (Unit FB, Queue 23)

**Date:** 2026-11-24. **Tool:** `tools/economy_sim.py` v7.
**Follow-up to:** Unit EY (Queue 22 — construction-worker day-wage
pay), whose honest limit this unit closes: "the tool's storm
scenario accrues the reduced pay evenly — it does not model which
days storms fall on, so its `minbal` is the even-spread figure,
not a measured one" (GDD-03 §2).

## 1. What was open

The v6 storm month pays 28/30 of the construction band (the
measured live month: 28 worked days, storm days 4 and 23 — the
1-based days; Queue 25 Unit HA corrects FB's "(3, 22)", which
were the 0-based day indices, see §6) and
accrues that reduced pay evenly — (gross − tax)/30 every day.
The month-1 minimum balance it prints (0 for every tier) is the
even-spread figure: the household is never below zero because a
thirtieth of the pay arrives every day, including on the storm
days themselves. In the settlement, pay lands only on days
actually worked (`tools/sim/labour.py` `day_wage_due()`), so a
storm on day 1 — two cost-only days before any pay arrives —
dips deeper than a storm on day 29, when 28 days of pay are
already banked. The v6 figure could not say how deep.

## 2. What v7 measures

`simulate()` takes an optional `storm_days` (distinct 1-based
days of the 30-day month): worked days are 30 minus the storm
days, gross is band × worked/30 as in v6, and the pay lands only
on worked days — (gross − tax)/worked per worked day, 0 on a
storm day. The total is still exactly gross − tax, so the
trajectory still ends at net for every position (pinned by a
test). The count is the measured live month (28 worked days);
the positions are scenarios — early (days 1–2), mid (15–16),
late (29–30) — plus the measured position (days 4 and 23,
where the live month's storms actually fell — corrected by
Unit HA, Queue 25, from FB's (3, 22), the 0-based day indices).
A `storm_days`
that disagrees with `day_wage_worked_days`, names a day outside
1..30, or repeats a day is refused, as is `storm_days` for any
non-day-wage profession.

Measured month-1 minimum balance, by storm position (net is the
same for every position — the month pays the same 28/30 of the
band whatever the days):

| Tier | Early (1–2) | Mid (15–16) | Late (29–30) | Measured (4, 23) | Even (v6) | Net/mo |
|---|---:|---:|---:|---:|---:|---:|
| entry | −500 | 0 | 0 | −100 | 0 | 900 |
| mid | −595 | 0 | 0 | 0 | 0 | 4,144 |
| senior | −726 | 0 | 0 | 0 | 0 | 7,601 |

Why the early position dips: on a storm day the household pays
the daily cost with no pay arriving. Entry costs 250/day, so two
storm days at the start are −500 before any pay lands. Mid costs
8,923/30 ≈ 297/day (−595) and senior 10,883/30 ≈ 363/day
(−726). Why mid and late do not dip: by day 15 the household has
banked 14 days of surplus (entry: 14 × 50 = 700), so two
cost-only days (500) never take it below zero; by day 29 it has
banked 28 days (1,400) and the month ends at net. Why the
measured position dips only the entry row: on day 4 the entry
household has banked three days (+150) and then pays a
cost-only day (−250), reaching −100; mid and senior have banked
more by then (mid +508, senior +892) and stay above zero (+210 /
+529 after the storm day).

## 3. What v7 changes

- `simulate(..., storm_days=…)` models the storm position (see
  §2); without it the v6 even accrual is unchanged, and the v6
  storm-month section's figure stays the even-spread one.
- The default run gains a day-wage storm-position section (the
  table in §2, printed per tier with the v6 even-spread baseline
  beside it for comparison).
- No other profession, rent, cost, tax rule or business P&L
  moves. The base table is unchanged from v6 (the construction
  rows below are byte-identical to the v6 report's), and the only
  diff in the default run vs v6 is the new section.
- The pinned md5 moves to the v7 baseline (the v6 md5 is kept in
  `test_no_regression.py` as history).

## 4. Verbatim output

Base table (construction rows — byte-identical to v6):

```
profession                   tier      gross    tax   rent  costs   net/mo  save%   minbal  flags
construction_worker          entry      9000      0   2500   7500     1500   16.7        0  -
construction_worker          mid       14000      0   2500   9250     4750   33.9        0  -
construction_worker          senior    20000    250   2500  11350     8400   42.0        0  -
```

Day-wage storm-month section (v6, unchanged — the even-spread figure):

```
day-wage storm month (Unit EY — measured 28 worked days of 30, 2 storm days suspending outdoor work):
profession                   tier      gross    tax   rent  costs   net/mo  save%   minbal  flags
construction_worker          entry      8400      0   2500   7500      900   10.7        0  -  (base net 1500, save 16.7%)
construction_worker          mid       13067      0   2500   8923     4144   31.7        0  -  (base net 4750, save 33.9%)
construction_worker          senior    18667    183   2500  10883     7601   40.7        0  -  (base net 8400, save 42.0%)
```

New day-wage storm-position section (v7 — measured minbal per position; corrected by Unit HA, Queue 25 — v7 as printed showed −150 in the measured column; the tool now prints −100, see §6):

```
day-wage storm-position month (Unit FB — same 28 worked days of 30; month-1 minbal by storm position):
profession                   tier      early     mid    late measured    even  (net/mo)
construction_worker          entry      -500       0       0     -100       0  (net 900)
construction_worker          mid        -595       0       0        0       0  (net 4144)
construction_worker          senior     -726       0       0        0       0  (net 7601)
```

Full default-run md5: `e598e416c07b21bacee9fe98fdb27244` (v6:
`9ac10779c231b7aa6120a6ff457982de` — kept in
`test_no_regression.py` as history). The only diff vs v6 is the
new section; the base table, business P&L, bridge check, pacing
and all other rows are unchanged.

## 5. Verdicts

- **Storm timing is measured now, and the v6 figure understated
  the dip.** The even-spread minbal (0 for every tier) is the
  shallowest case, not the typical one: the measured position
  (days 4 and 23) already dips the entry row to −100, and the
  early position dips it to −500 (mid −595, senior −726). A storm
  month's minimum balance is a measured figure per position now,
  and the v6 figure is labelled for what it is — the
  even-spread figure — wherever it is quoted.
- **Storm month: survivable in every position, no new flag.**
  The worst dip (−726, senior early) is measured against the
  starting balance, not the zero start: the entry construction
  worker starts month 1 with 5,000 NCr (the bridge check's own
  figure), so the worst entry dip leaves 5,000 − 500 = 4,500 —
  no bridge failure in any position, and no TIGHT or SURVIVAL
  FAIL anywhere in the storm sections. The net (900 / 4,144 /
  7,601) does not move with position at all.
- **No tuning call.** Nothing in the data moves: no wage, rent,
  cost or tax change is proposed. The storm effect is weather the
  sim already models; a month with more storm days pays less, and
  the settlement measures it per world rather than the tool
  assuming it.
- **Open, recorded:** the positions are scenarios, not a
  forecast — only the measured position (days 4 and 23) is where
  a real month's storms fell, and a real month's storm count
  comes from the settlement's weather, not from this tool. The
  tool still models a single-earner household on the base table's
  costs; a household with a second earner, or with savings above
  the starting balance, dips less.

## 6. Addendum — Settlement-measured storm-month trajectory (Unit GC, Queue 24)

**Date:** 2026-11-24. **Method:** the EY live month re-run
exactly (`Simulation`, seed `ey-measure`,
`generate_population(60)`, 32 days). Storm days read from
`daily_weather` and cross-checked against the lost days in
`instantiated_schedules`; worked days from
`labour.worked_days()` (month 1); the daily balance path
reconstructed from `economy_ledger` (every transfer to/from the
worker, ordered by `game_minutes`) against the genesis `seed`
row. All figures below are that run's, not the tool's.

**The storm days are 1-based days 4 and 23 — not 3 and 22.**
The `storm` presets fall on day_index 3 and 22 (0-based), and
all four construction workers lost exactly those two days
(`outdoor_work_suspended` on both). EY's report wrote them as
"days 3 and 22" — those are the 0-based day indices — and FB
encoded them as `STORM_MEASURED_DAYS = (3, 22)`, which
`simulate()` reads as 1-based days. The tool's "measured"
position is therefore one day earlier than the settlement's
actual storm days. The tool's own model at the true position
(days 4 and 23) gives entry −100, mid 0, senior 0 — not the
recorded −150. Correcting the constant (or relabelling the
position as day-indices) is recorded open, not taken here: this
unit is analysis, and the pin moves with Unit GE.

**Worked days:** all four workers 28/30 in month 1
(`worked_days()`, month 1); day-wage due 8,400 NCr on the 9,000
entry band, 13,067 on the 14,000 mid band — the EY figures
reproduced exactly.

**One worker's real daily balance path (Priya Khan,
`NEX000042`, entry, 9,000 band).** Genesis `seed` +5,385
(5,000 × 1.077 — the settlement randomises the starting
balance ±15% per character, `population.py`; the tool uses the
canonical 5,000). End-of-day balances, day_index 0–29:
4,985, 4,985, 4,585, 4,585, 3,989, 3,989, 3,989, 3,989, 3,789,
3,789, 3,389, 3,389, 2,989, 2,989, 2,589, 2,589, 2,189, 2,189,
1,789, 1,789, 1,389, 1,389, 1,189, 1,189, 789, 789, 389, 389, 89,
89. Month-1 flow by reason (`game_minutes` < 43,200): `seed`
+5,385, `taxi_fare` −5,296 — and nothing else. No wage and no
living costs move within the month at all: the settlement pays
everything once, at month-end (`game_minutes` 43,200). The
storm days leave no trace in the path — the balance is
unchanged across day_index 3 (4,585) and day_index 22 (1,389).
Minimum end-of-day balance in month 1: **89**, on day_index
28–29. The second entry worker, Mariam Shah (`NEX000045`,
seed 4,496), drains on taxi fares alone to exactly **0** by
day_index 24 and stays at 0 through day_index 29 — the fares
stop when the balance hits 0.

**Does the tool's −150 entry dip match the settlement's actual
dip? No.** The settlement has no within-month dip in the
tool's sense: the tool's trajectory assumes pay lands daily and
costs accrue daily, dipping to −150 when a storm day comes
early; the settlement's balance within the month moves only on
taxi fares (about −100 per fare, several a day — a daily drain
the tool folds into its flat monthly transport line), and the
pay and the costs both land in one lump at month-end. The
settlement's actual minimum is +89 (Priya) / 0 (Mariam) in
absolute NCr — never negative — against the tool's −150 from a
zero start. Even the tool disagrees with its own recorded
figure: at the true measured position (days 4 and 23) it says
−100.

**Where the tool and the settlement differ:**

- **Second earner.** Both entry workers' households have one —
  Priya's household (`HH000022`) has a taxi-driver second
  earner (14,000) plus a non-earner; Mariam's (`HH000023`) has
  a civil-engineer second earner (38,000) plus a non-earner.
  Household month-1 income is 23,100 / 46,400, against the
  tool's single-earner storm-month gross of 8,400. The tool
  models a single earner (Unit GD extends it to two).
- **Arrears.** Priya's household ended month 1 with
  `emergency_ncr` 967 and `debt_after_ncr` 967 — it could not
  cover its full living costs (food 6,250, housing 6,000,
  transport 6,800, other 2,725). Mariam's household: 0.
- **Other income.** Priya holds a government office: at the
  month-1 settlement (`game_minutes` 43,200) she received
  `office_allowance` +16,000 — about twice the storm-month wage
  (+8,400) — alongside `bank_deposit` −3,386, `party_dues`
  −100, `sales_tax` −278 and `purchase` −5,567. The tool
  models wage income only.
- **Starting balance.** The settlement randomises it per
  character (5,385 and 4,496 measured — 5,000 × U(0.85, 1.15));
  the tool uses the canonical 5,000. The bridge check's
  starting balance is therefore a canonical figure, not a
  settled one.
- **Taxi fares.** The settlement charges them daily (−5,296 /
  −4,496 across month 1), a lumpy front-loaded drain; the tool
  charges transport as a flat monthly line inside its smoothed
  daily cost (250/day entry). The fares alone take a worker
  from her seed to 89 / 0 before any pay arrives.

**Verdict.** The tool's storm-position dip is a model of
within-month timing that the settlement does not produce: the
settlement settles monthly, so its storm-month dip is not a
daily-balance dip at all — it is the month-end net, and the
within-month minimum is set by taxi fares against the
randomised seed. The tool's −150 (and the corrected −100 at
the true position) remain useful as the single-earner,
wage-only, canonical-start timing model they are, and the V7
§5 verdicts stand — no bridge failure, no new flag, no tuning
call — but they must not be quoted as the settlement's measured
dip: the settlement's measured month-1 minimum for an entry
construction worker is +89 / 0 in absolute NCr, with the
household's second earner, arrears and other income doing the
work the tool does not model.

**Open, recorded (Queue 25 material — Units HA + HE DONE
2026-11-24):** `STORM_MEASURED_DAYS` is corrected to (4, 23)
— the tool's own model at the true position dips entry to
−100, not −150; the pinned md5 moved to
`ede430d0bf391fac3f8599334f55b77b` at HA and to
`5431558ffa3d023c436366c26535f932` at HD (the earlier md5s are
kept in `test_no_regression.py` as history). The settlement-
timing decision is Unit HE, DONE — see §10: the tool stays a
stylised daily model, and the taxi-fare drain and the
randomised start are recorded there as documented limits.

## 7. Addendum — Two-earner storm-position scenario (Unit GD, Queue 24)

**Date:** 2026-11-24. **Method:** `simulate(...,
second_earner=True)` — a second construction worker at the same
tier, on the same storm days and the same day-wage rule. Gross
and tax double per earner (each earner is taxed on their own
gross, as the settlement taxes each earner on what they
received); the household costs follow `engine._living_costs`
for two adults — food and clothing ×2, transport and eating out
×2 (both are per-earner lines in `_living_costs`; the queue
draft's "rest flat" gloss is corrected here against the source
— only utilities / services / medical and rent are flat), and
the lifestyle uplift doubles (the settlement sums it per
earner). The band stays the entry-wage band (lower) for every
tier, as in the single-earner model. The net is the same for
every position; only the month-1 minimum balance moves.

Measured month-1 minimum balance by storm position, two-earner
household beside the single-earner figures from §2:

| Tier | Early (1–2) | Mid (15–16) | Late (29–30) | Measured (4, 23) | Even (v6) | Net/mo | Single early | Single measured | Single net |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| entry | −780 | 0 | 0 | 0 | 0 | 5,100 | −500 | −100 | 900 |
| mid | −970 | 0 | 0 | 0 | 0 | 11,588 | −595 | 0 | 4,144 |
| senior | −1,231 | 0 | 0 | 0 | 0 | 18,502 | −726 | 0 | 7,601 |

Costs (storm month, measured position): single 7,500 / 8,923 /
10,883 → two-earner 11,700 / 14,546 / 18,466 — the second
adult adds 4,200 at the lower band (food +2,500, clothing +600,
transport +800, eating out +300) plus their own uplift (mid
+1,423, senior +3,383; the uplift is computed from the reduced
storm-month gross, as in the single-earner model). Tax is
per-person (senior storm month: 366 = 2 × 183).

**Finding: a second earner does not help the early-position dip
at all — it makes it deeper in NCr.** At the measured position
the dip is gone (0 for every tier, against the single-earner's
−100 entry): once pay starts landing on day 1, two pay packets
cover the cost (pay lands on days 1–3 before the day-4 storm).
But on days 1–2 no pay has arrived for anyone,
and two adults burn the daily cost (entry 390/day, mid ~485,
senior ~616) — so the early dip is −780 / −970 / −1,231,
deeper than the single-earner −500 / −595 / −726. Against the
combined canonical starting balance (2 × 5,000 = 10,000 — each
earner brings their own genesis balance, `population.py`; the
settlement randomises each ±15%, §6) the worst two-earner dip
leaves 10,000 − 1,231 = 8,769 — no bridge failure in any
position, and no TIGHT or SURVIVAL FAIL anywhere in the section.

Verbatim output (new default-run section):

```
two-earner storm-position month (Unit GD — same 28 worked days of 30; second earner is a construction worker at the same tier, same storm days; month-1 minbal by storm position):
profession                   tier      early     mid    late measured    even  (net/mo)
construction_worker          entry      -780       0       0        0       0  (net 5100)
construction_worker          mid        -970       0       0        0       0  (net 11588)
construction_worker          senior    -1231       0       0        0       0  (net 18502)
```

**No tuning call.** Nothing in the data moves. The two-earner
household is the settlement's common case (§6: both measured
entry workers live with a second earner), and it dips less
where it matters (the measured position) — the early-position
depth is a timing fact, not a balance problem.

**Open, recorded (Unit IA DONE 2026-11-24 — see §8):** the
mixed-profession second earner is now modelled (taxi driver
at entry, civil engineer at mid — the §6 cases), and the
mixed bridge lines are now wired into the tool's printed
bridge check. (Unit JA DONE 2026-11-24 — see §8: the
same-tier two-earner bridge line is now wired too —
10,000 − 1,231 = 8,769 is the tool's printed output, not
prose only. No two-earner bridge figure is report-only.)

## 8. Addendum — Storm-position bridge line (Unit GE, Queue 24)

**Date:** 2026-11-24. The bridge check in the tool's default run
now prints a second line for the `construction_worker` entry
row — starting balance + the worst storm-position minbal (the
minimum across the early / mid / late / measured positions):

```
first-month bridge check (entry rows: starting balance + zero-start dip = worst month-1 balance):
  construction_worker    start   5000 + dip       0 =    5000  OK
  construction_worker    start   5000 + storm dip    -500 =    4500  OK  (worst storm position)
  construction_worker + taxi-driver    start  10000 + mixed dip     -72 =    9928  OK  (worst mixed storm position)
  construction_worker + civil-engineer start  30000 + mixed dip   -8623 =   21377  OK  (worst mixed storm position)
  construction_worker + construction-worker start  10000 + same-tier dip   -1231 =    8769  OK  (worst same-tier storm position)
  construction_worker + taxi-driver (mid) start  10000 + other-tier dip       0 =   10000  OK  (worst other-tier storm position)
  construction_worker + civil-engineer (entry) start  30000 + other-tier dip   -3210 =   26790  OK  (worst other-tier storm position)
  construction_worker + taxi-driver (mid, renting) start  10000 + renting dip     -56 =    9944  OK  (worst renting storm position)
```

The worst dip is the early position (−500 entry; mid −595,
senior −726) — the line wires the minimum, not the measured
position. The §5 bridge observation (entry 5,000 − 500 = 4,500)
is now the tool's printed output, not a report-only
calculation; a failing storm line would join `BRIDGE FAIL`
(none fails). (Unit IA · Queue 26 · 2026-11-24: the bridge
check now also prints a mixed two-earner line per measured
second-earner profession — the combined canonical start plus
the worst mixed minbal (the minimum across the first earner's
tiers and the four storm positions). Taxi-driver second earner:
10,000 − 72 = 9,928; civil-engineer second earner: 30,000 −
8,623 = 21,377. Each earner brings their own genesis balance
(`population.py` seeds `starting_balance_ncr` per profession:
construction worker 5,000, taxi driver 5,000, civil engineer
25,000) — so the CE household's combined start is 30,000, not
the 10,000 HD's prose carried for both pairings; see the
correction note in §9. A failing mixed line would join `BRIDGE
FAIL` too. (Unit JA · Queue 27 · 2026-11-24: the GD same-tier
two-earner bridge figure (10,000 − 1,231 = 8,769, §7) and the
IC other-tier figures (10,000 − 0 = 10,000 and 30,000 − 3,210
= 26,790, §12) are now wired too — see the JA paragraph
below; no two-earner bridge figure is report-only.)

Full default-run md5: `45a45edc63cee4b142891da938ef79bd` (HD:
`5431558ffa3d023c436366c26535f932` — kept in
`test_no_regression.py` as history, with HA
`ede430d0bf391fac3f8599334f55b77b`, GE
`d699ae7d37fe8ca077f873ba238dd86b`, v7
`e598e416c07b21bacee9fe98fdb27244` and v6
`9ac10779c231b7aa6120a6ff457982de`). The diffs vs HA are
the §9 mixed-profession section and these mixed bridge lines
(IA); the §7 two-earner section, the single-earner storm line,
the base table, business P&L, pacing and
all other rows are unchanged.

(Unit JA · Queue 27 · 2026-11-24: the bridge check now also
prints the three remaining two-earner lines — the GD same-tier
household and the IC other-tier pairings — each the combined
canonical start plus the worst minbal (the minimum across the
first earner's tiers and the four storm positions): same-tier
10,000 − 1,231 = 8,769; mid-tier taxi-second 10,000 − 0 =
10,000; entry civil-engineer-second 30,000 − 3,210 = 26,790.
A failing line would join `BRIDGE FAIL` too. No two-earner
bridge figure is report-only now. Full default-run md5:
`b70b18972aeb5c3b2d0273b986060058` (IC:
`d198a2fe0970e11aaa105bcc4bfb19f9` — kept in
`test_no_regression.py` as history). The only diff vs IC is
these three bridge lines; the §7 two-earner section, the mixed
sections, the renting-cab section, the base table and all other
rows are unchanged.)

(Unit KA · Queue 28 · 2026-11-24: the renting mid-tier
taxi-second bridge line is now wired too — the combined
canonical start (5,000 + 5,000 = 10,000) plus the worst
renting minbal (the minimum across the first earner's tiers
and the four storm positions: −56, senior early): 10,000 − 56
= 9,944. A failing line would join `BRIDGE FAIL` too. Full
default-run md5: `5f50931cbaad263812473ce1c7830e59` (JA:
`b70b18972aeb5c3b2d0273b986060058` — kept in
`test_no_regression.py` as history). The only diffs vs JA are
this bridge line and the §14 renting mid-tier section; the
§9/§11/§12 sections, the other bridge lines, the base table
and all other rows are unchanged.)

**No tuning call.**

## 9. Addendum — Mixed-profession two-earner storm-position scenario (Unit HD, Queue 25)

**Date:** 2026-11-24. **Method:** `simulate(...,
second_earner="taxi_driver" | "civil_engineer")` — the
settlement's measured pairings from §6 (Priya's household: a
taxi-driver second earner at 14,000; Mariam's: a civil-engineer
second earner at 38,000). The second earner's tier is FIXED at
the measured one — taxi driver at entry (14,000), civil engineer
at mid (38,000) — while the first earner (construction worker)
varies over entry/mid/senior, so the table's entry row is the
measured household in each case. Each earner is taxed on their
own gross and carries their own lifestyle uplift; the household
costs follow `engine._living_costs` for two adults (food and
clothing ×2, transport and eating out ×2 per earner, utilities /
services / medical and rent flat). The band stays the lower band
(the first earner's entry wage), as in the single-earner model.
Storm days do not change the second earner's pay — the per-fare
rule has no storm days, and the monthly pay lands on day 30
regardless — so the storm-position effect comes from the first
earner alone, against the second earner's steady pay. The taxi
second earner is the owning driver (no cab rental is charged).
The net is the same for every position; only the month-1 minimum
balance moves.

Measured month-1 minimum balance by storm position,
mixed-profession two-earner household beside the single-earner
figures from §2:

Taxi-driver second earner (entry 14,000, per-fare):

| Tier | Early (1–2) | Mid (15–16) | Late (29–30) | Measured (4, 23) | Even (v6) | Net/mo | Single early | Single measured |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| entry | 0 | 0 | 0 | 0 | 0 | 10,700 | −500 | −100 |
| mid | 0 | 0 | 0 | 0 | 0 | 13,944 | −595 | 0 |
| senior | −72 | 0 | 0 | 0 | 0 | 17,401 | −726 | 0 |

Civil-engineer second earner (mid 38,000, monthly):

| Tier | Early (1–2) | Mid (15–16) | Late (29–30) | Measured (4, 23) | Even (v6) | Net/mo | Single early | Single measured |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| entry | −8,623 | −8,623 | −8,323 | −8,623 | −8,603 | 27,950 | −500 | −100 |
| mid | −5,499 | −5,499 | −5,032 | −5,499 | −5,467 | 31,194 | −595 | 0 |
| senior | −2,170 | −2,170 | −1,510 | −2,170 | −2,126 | 34,651 | −726 | 0 |

Costs (storm month, measured position): single 7,500 / 8,923 /
10,883 → taxi-second 11,700 / 13,123 / 15,083 (the second adult
adds 4,200 at the lower band and no uplift — 14,000 is the taxi
entry wage) and civil-engineer-second 17,300 / 18,723 / 20,683
(the second adult adds 4,200 plus their own uplift of 5,600 —
35% of 38,000 − 22,000). Tax is per-person (taxi-second: the
single earner's tax alone, 0 / 0 / 183; civil-engineer-second:
the single earner's tax plus 1,150 on the 38,000).

Verbatim output (new default-run sections):

```
mixed-profession two-earner storm-position month (Unit HD — same 28 worked days of 30; taxi-driver second earner (entry 14,000, per-fare); month-1 minbal by storm position):
profession                   tier      early     mid    late measured    even  (net/mo)  single-early  single-measured
construction_worker          entry         0       0       0        0       0  (net 10700)          -500            -100
construction_worker          mid           0       0       0        0       0  (net 13944)          -595               0
construction_worker          senior      -72       0       0        0       0  (net 17401)          -726               0

mixed-profession two-earner storm-position month (Unit HD — same 28 worked days of 30; civil-engineer second earner (mid 38,000, monthly); month-1 minbal by storm position):
profession                   tier      early     mid    late measured    even  (net/mo)  single-early  single-measured
construction_worker          entry     -8623   -8623   -8323    -8623   -8603  (net 27950)          -500            -100
construction_worker          mid       -5499   -5499   -5032    -5499   -5467  (net 31194)          -595               0
construction_worker          senior    -2170   -2170   -1510    -2170   -2126  (net 34651)          -726               0
```

**Finding: a per-fare second earner helps the early dip; a
monthly second earner deepens it — and the depth is timing, not
storms.** The taxi driver's pay arrives every day from day 1
(14,000/30 a day), so it covers the cost-only days: the early
dip is gone for entry and mid, and only −72 for senior (against
the single-earner's −500 / −595 / −726 and the same-tier
second earner's −780 / −970 / −1,231 — the day-wage second
earner deepens the early dip because no pay arrives for anyone
on days 1–2, while the per-fare earner is already paying). The
civil engineer's pay lands once, on day 30, so the household
burns the daily cost for 29 days first (entry 577/day): the dip
is −8,623 and nearly position-independent — early, mid and
measured share it exactly, and only the late position is
shallower (−8,323, because the day-29 storm costs a day of
construction pay that the day-30 lump then covers). The storm
position barely matters for this household; the pay timing does.
Against the combined canonical starting balances (taxi-second:
2 × 5,000 = 10,000; civil-engineer-second: 5,000 + 25,000 =
30,000 — each earner brings their own genesis balance,
`population.py` seeds `starting_balance_ncr` per profession)
the worst dips leave 9,928 (taxi-second) and 21,377
(civil-engineer-second) — no bridge failure in any position, and
no TIGHT or SURVIVAL FAIL anywhere in the sections (savings rates
47.8–53.3% taxi-second, 60.2–61.1% civil-engineer-second).
**Correction (Unit IA · Queue 26 · 2026-11-24):** this section
as written by HD quoted the civil-engineer-second bridge figure
as 10,000 − 8,623 = 1,377 — that applied the construction
worker's 5,000 genesis balance to the civil engineer too, but
`professions.json` gives the civil engineer a 25,000 starting
balance, so the combined start is 30,000 and the figure is
30,000 − 8,623 = 21,377. The 1,377 is superseded wherever it
appears (including §10's seed caveat, updated the same way);
the taxi-second figure (10,000 − 72 = 9,928) is unchanged, and
no measured dip moves — only the start the dip is measured
against.

**Honest limit, recorded not hidden:** the
civil-engineer-second dip is the tool's daily-trajectory timing,
not a measured settlement dip. The tool accrues the household's
costs daily while the engineer's pay waits for day 30 — but the
settlement also pays monthly, so a civil-engineer-second
household in the settlement likewise waits until month-end, and
its within-month path likewise falls until then (on taxi fares,
§6 — not on the tool's smoothed daily cost). Whether the tool
should model that monthly timing or stay a stylised daily model
is Unit HE's decision; this unit measures the timing as the tool
models it today and does not re-decide it. (Unit HE DONE
2026-11-24 — see §10: the tool stays a stylised daily model.) The taxi-second
household has no such question: per-fare pay arrives daily in
both the tool and the settlement.

**No tuning call.** Nothing in the data moves. The two measured
households are now modelled as they stand (§6: Priya's and
Mariam's), and the finding is a timing fact, not a balance
problem.

**Open, recorded:** the taxi second earner is the owning driver
— the renting-cab variant is modelled now
(Unit IB DONE 2026-11-24 — see §11: 200/day × 26 = 5,200/month,
the settlement's rule; early dips −193 / −288 / −419, measured 0,
nets 5,500 / 8,744 / 12,201); the second earner's tier is fixed
at the measured one — a mid-tier taxi driver or an entry civil
engineer as second earner is now modelled (Unit IC DONE
2026-11-24 — see §12: mid-tier taxi 0 everywhere, nets 16,150 /
19,394 / 22,851; entry civil engineer −3,210 / −350 / −31 at the
measured position, nets 18,350 / 21,594 / 25,051); only the two
measured pairings are modelled (any other profession is refused
by the tool).
(Unit IA DONE 2026-11-24 — see §8: the mixed two-earner bridge
lines are now wired into the tool's printed bridge check —
10,000 − 72 = 9,928 taxi-second, 30,000 − 8,623 = 21,377
civil-engineer-second — with the CE combined start corrected
from HD's 10,000 to the sourced 30,000.)

## 10. Addendum — Settlement-Timing Trajectory Decision (Unit HE, Queue 25)

**Date:** 2026-11-24. **Decision: the tool STAYS a stylised
daily model.** It does not model monthly settlement timing. The
decision is recorded here and in GDD-03 §2; no sim change
follows from it — the tool is byte-identical (default-run md5
unchanged: `5431558ffa3d023c436366c26535f932`), because "stay"
means the model does not move.

**The question, as GC posed it (§6):** the settlement pays wages
and charges living costs once, at month-end (`game_minutes`
43,200), while the within-month path moves only on taxi fares —
Priya Khan's balance falls from a seed of 5,385 to a month-1
minimum of 89 on taxi fares alone (−5,296), Mariam Shah's from
4,496 to exactly 0 (−4,496, the fares stopping when the balance
hits 0) — and the storm days leave no trace in either path. The
bridge check's 5,000 start is canonical while the settlement
randomises each starting balance ±15% (5,385 / 4,496 measured).
Should the tool model that monthly timing, or stay daily?

**Why stay — four reasons:**

1. **The storm-position signal is the tool's reason for
   existing.** The tool measures how the timing of the storm
   days changes the month-1 minimum balance
   (early/mid/late/measured/even). Under monthly settlement
   timing the trajectory collapses to a single month-end step:
   the balance falls on fares until day 30, then the net lands
   in one lump. GC proves the storm days leave no trace in that
   path — early, mid, late and measured would be identical, and
   the signal the tool exists to measure would be destroyed.
2. **The settlement's actual within-month path is already
   measured directly.** GC measured it: +89 / 0 in absolute NCr,
   on fares alone. The tool does not need to reproduce a path
   the settlement already gives us; the two models answer
   different questions — the settlement says what the balance
   actually does, the tool says what the timing costs if pay
   lands as earned and costs accrue as incurred.
3. **The daily model is the bridge check's model.** The bridge
   check asks whether a household can bridge the month from a
   canonical 5,000 start — a planning question, well-defined
   and reproducible. Under monthly timing the bridge question
   has no within-month answer at all: the balance is the seed
   minus fares, and the "dip" is the fare drain, which the
   settlement caps at 0 by stopping the fares.
4. **Determinism.** A randomised start would make the tool's
   output seed-dependent and break the pinned, reproducible
   comparison the storm-position columns are (the md5 pin, the
   verbatim tables). The canonical 5,000 keeps every run
   comparable.

**Documented limits (recorded, not hidden):**

- **The tool's trajectory has no settlement counterpart.** The
  settlement settles monthly; the tool's daily dip is a stylised
  timing model, not the settlement's measured dip. The tool's dip
  must never be quoted as the settlement's measured dip — the
  settlement's measured month-1 minimum for an entry construction
  worker is +89 / 0 in absolute NCr (§6 verdict stands).
- **The taxi-fare drain.** The settlement's within-month
  movement is taxi fares alone — lumpy (about −100 per fare,
  several a day), front-loaded, and stopping at 0. The tool
  charges transport as a flat monthly line inside its smoothed
  daily cost (250/day entry) and lets the balance go negative.
  The tool's minbal is therefore a worst-case-style timing
  figure, not the settlement's fare-drain floor (which is 0 by
  construction).
- **The randomised start.** The bridge check's 5,000 start is
  canonical; the settlement randomises each starting balance
  ±15% (5,385 / 4,496 measured). A household whose seed rolls
  low starts up to 750 below the canonical line. Every bridge
  figure in this report is canonical, not settled — for the
  civil-engineer-second household (§9: 30,000 − 8,623 = 21,377)
  the seed randomisation applies to both earners, so the lowest
  roll takes up to 4,500 off the canonical start (750
  construction worker + 3,750 civil engineer), leaving 16,877 —
  still no failure, but the margin is the seed's, not the
  model's. (Unit IA · Queue 26 corrected §9's figure here too:
  HD had quoted 10,000 − 8,623 = 1,377 with the construction
  worker's seed alone; the civil engineer's own 25,000 start
  is in the combined figure now.)
- **The monthly-settlement alternative stays open as a
  documented alternative, not implemented:** a future unit
  could add a monthly-timing view BESIDE the daily one (a second
  trajectory that pays and charges at month-end), if a use for
  it appears — but it must not replace the daily model, because
  it would destroy the storm-position signal. No use for it is
  recorded today. (Unit ID · Queue 26 · 2026-11-24: checked
  again — still no use is named, so the view stays open and
  unimplemented; no monthly-timing view was built and the tool
  is byte-identical — default-run md5 still
  `d198a2fe0970e11aaa105bcc4bfb19f9`.)

**No tuning call.** Nothing in the data moves. The decision is
about what the tool models, not about any rate.

## 11. Addendum — Renting-cab taxi-driver second earner (Unit IB, Queue 26)

**Date:** 2026-11-24. **Method:** `simulate(...,
second_earner="taxi_driver", second_earner_renting_cab=True)` —
the same entry taxi driver (14,000, per-fare) as §9's owning
driver, but renting the licensed cab. The rental days follow the
settlement's rule, read from the source — `engine._settle_month`
charges `cab_rental_ncr_per_day` (200, `data/prices.json`) ×
`WORK_DAYS` (26) = 5,200/month flat for the month, per taxi
driver in the household. The settlement does not vary the rental
by worked days, storm days or Sundays, and neither does this
model: the rental is a monthly cost line of 5,200, accruing
evenly in the daily model like rent (the settlement charges the
same 5,200 once at month-end; HE's daily model stands). The
first earner (construction worker) still varies over
entry/mid/senior; the second earner's tier stays the measured
entry one. Storm days do not change the second earner's pay or
rental — the per-fare rule has no storm days — so the
storm-position effect still comes from the first earner alone.

Measured month-1 minimum balance by storm position,
renting-cab taxi-driver second earner beside the owning-driver
figures from §9:

| Tier | Early (1–2) | Mid (15–16) | Late (29–30) | Measured (4, 23) | Even (v6) | Net/mo | Owning early | Owning measured | Owning net |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| entry | −193 | 0 | 0 | 0 | 0 | 5,500 | 0 | 0 | 10,700 |
| mid | −288 | 0 | 0 | 0 | 0 | 8,744 | 0 | 0 | 13,944 |
| senior | −419 | 0 | 0 | 0 | 0 | 12,201 | −72 | 0 | 17,401 |

Costs (storm month, measured position): owning 11,700 / 13,123 /
15,083 → renting 16,900 / 18,323 / 20,283 — the rental adds
exactly 5,200 at every tier, so the net drops by exactly 5,200
too (gross and tax untouched). Against the combined canonical
starting balance (2 × 5,000 = 10,000) the worst renting dip
leaves 10,000 − 419 = 9,581 — no bridge failure in any position,
and no TIGHT or SURVIVAL FAIL anywhere in the section.

Verbatim output (new default-run section):

```
renting-cab taxi-driver second earner storm-position month (Unit IB — same 28 worked days of 30; taxi-driver second earner (entry 14,000, per-fare) renting the cab at 200/day x 26 = 5,200/mo; month-1 minbal by storm position):
profession                   tier      early     mid    late measured    even  (net/mo)  owning-early  owning-measured
construction_worker          entry      -193       0       0        0       0  (net 5500)             0               0
construction_worker          mid        -288       0       0        0       0  (net 8744)             0               0
construction_worker          senior     -419       0       0        0       0  (net 12201)           -72               0
```

**Finding: the rental re-opens the early dip the owning driver
had closed.** The owning driver covers the cost-only days 1–2
with per-fare pay arriving from day 1 (entry: 467/day against a
390/day household cost). The rental adds 173/day to the cost
(563/day entry) while the taxi pay stays 467/day, so the
household burns 96/day for the first two days: −193 entry,
−288 mid, −419 senior. The measured position still dips nothing
(pay lands on days 1–3 before the day-4 storm), and the dip is
a timing fact — the same rental, charged at month-end in the
settlement, would not dip at all within the month; it is the
tool's daily accrual that puts it on days 1–2. The renting
household still nets 5,500 / 8,744 / 12,201 a month — the
rent-before-you-buy on-ramp survives, clearly worse than owning
but survivable, exactly as Unit U designed it for the
single-earner row.

**Honest limit, recorded not hidden:** the tool's single-earner
renting-cab row charged the rental a different way — via
`extra_daily_cost` on days ≤ 26 excluding Sundays (23 days =
4,600/month in the trajectory), while the settlement charges 26
days flat (5,200). The two renting rows therefore disagreed by
600/month: this unit's second-earner rental follows the
settlement's rule, the v1 single-earner row kept its own.
(Unit JB DONE 2026-11-24 — see §13: the single-earner row now
follows the settlement's 26-day charge too. Correction to this
section's expectation: reconciling the row did NOT move the base
table's renting row or its bridge line — minbal stays 0 and net
stays 1,300, because the headline net already subtracted the
full 5,200; only the row's trajectory end-balance moved, from
1,900 to exactly net, 1,300.)

Full default-run md5: `27464ea221694880a4369f805d8cd455` (IA:
`45a45edc63cee4b142891da938ef79bd` — kept in
`test_no_regression.py` as history). The only diff vs IA is this
renting-cab section; the bridge lines, the mixed sections, the
base table and all other rows are unchanged.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the second earner's tier is now selectable
(Unit IC DONE 2026-11-24 — see §12: mid-tier taxi driver and
entry civil engineer as second earner, at the tiers the source
data gives); the renting variant is modelled for the taxi second
earner only (no other second earner rents anything) — and now
combines with a named tier (Unit KA DONE 2026-11-24 — see §14:
measured at mid-tier, nets 10,950 / 14,194 / 17,651, bridge
10,000 − 56 = 9,944; a renting civil engineer is refused as
meaningless); only the two measured pairings are modelled (any
other profession is refused by the tool).

## 12. Addendum — Second earner at other tiers (Unit IC, Queue 26)

**Date:** 2026-11-24. **Method:** `simulate(...,
second_earner="taxi_driver", second_earner_tier="mid")` and
`simulate(..., second_earner="civil_engineer",
second_earner_tier="entry")` — the same two measured pairings
as §9, but at the other tier the source data actually gives: a
mid-tier taxi driver (23,000, per-fare) and an entry civil
engineer (22,000, monthly), both from `prices.json`
`wages_monthly`. The measured tier stays the default when no
tier is named, so the §9/§11 figures are unchanged. Each earner
is taxed on their own gross with their own uplift (mid taxi:
tax 400, uplift 35% of 23,000 − 14,000 = 3,150; entry civil
engineer: tax 350, uplift 0 — 22,000 is the entry wage); costs
follow `engine._living_costs` for two adults, as before. Storm
days do not change the second earner's pay — the per-fare rule
has no storm days, and the monthly pay lands on day 30
regardless — so the storm-position effect still comes from the
first earner alone. No tier's pay is invented: if a tier's wage
were not in the source data, it would be recorded as unmodelled
instead — both tiers here are in `prices.json`.

Measured month-1 minimum balance by storm position, beside the
measured-tier figures from §9:

Mid-tier taxi-driver second earner (23,000, per-fare):

| Tier | Early (1–2) | Mid (15–16) | Late (29–30) | Measured (4, 23) | Even (v6) | Net/mo | Measured-tier early | Measured-tier measured | Measured-tier net |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| entry | 0 | 0 | 0 | 0 | 0 | 16,150 | 0 | 0 | 10,700 |
| mid | 0 | 0 | 0 | 0 | 0 | 19,394 | 0 | 0 | 13,944 |
| senior | 0 | 0 | 0 | 0 | 0 | 22,851 | −72 | 0 | 17,401 |

Entry civil-engineer second earner (22,000, monthly):

| Tier | Early (1–2) | Mid (15–16) | Late (29–30) | Measured (4, 23) | Even (v6) | Net/mo | Measured-tier early | Measured-tier measured | Measured-tier net |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| entry | −3,210 | −3,210 | −2,910 | −3,210 | −3,190 | 18,350 | −8,623 | −8,623 | 27,950 |
| mid | −875 | −465 | 0 | −350 | −54 | 21,594 | −5,499 | −5,499 | 31,194 |
| senior | −1,006 | 0 | 0 | −31 | 0 | 25,051 | −2,170 | −2,170 | 34,651 |

Costs (storm month, measured position): mid-tier taxi-second
14,850 / 16,273 / 18,233 (the measured-tier taxi-second costs
11,700 / 13,123 / 15,083 plus the 3,150 uplift on the higher
wage) and entry civil-engineer-second 11,700 / 13,123 / 15,083
(the same second-adult lines as the taxi-second household, with
no uplift — 22,000 is the civil engineer's entry wage). Against
the combined canonical starting balances the worst dips leave
10,000 − 0 = 10,000 (mid-tier taxi-second) and
30,000 − 3,210 = 26,790 (entry civil-engineer-second) — no bridge
failure in any position, and no TIGHT or SURVIVAL FAIL anywhere
in the sections (savings rates 51.4–54.8% mid-tier taxi-second,
60.4–61.6%
entry civil-engineer-second). (Unit JA DONE 2026-11-24: both
figures are now wired into the tool's printed bridge check —
see §8 — so no two-earner bridge figure is report-only.)

Verbatim output (new default-run sections):

```
second earner at another tier storm-position month (Unit IC — same 28 worked days of 30; taxi-driver second earner (mid 23,000, per-fare); month-1 minbal by storm position):
profession                   tier      early     mid    late measured    even  (net/mo)  measured-early  measured-measured
construction_worker          entry         0       0       0        0       0  (net 16150)               0                 0
construction_worker          mid           0       0       0        0       0  (net 19394)               0                 0
construction_worker          senior        0       0       0        0       0  (net 22851)             -72                 0

second earner at another tier storm-position month (Unit IC — same 28 worked days of 30; civil-engineer second earner (entry 22,000, monthly); month-1 minbal by storm position):
profession                   tier      early     mid    late measured    even  (net/mo)  measured-early  measured-measured
construction_worker          entry     -3210   -3210   -2910    -3210   -3190  (net 18350)           -8623             -8623
construction_worker          mid        -875    -465       0     -350     -54  (net 21594)           -5499             -5499
construction_worker          senior    -1006       0       0      -31       0  (net 25051)           -2170             -2170
```

**Finding: the tier moves the dip more than the position
does.** The mid-tier taxi driver's per-fare pay (753/day net)
covers the household cost at every tier, so the early dip is
gone everywhere — even senior, where the measured-tier driver
left −72. The entry civil engineer still waits for day 30, so
the household still dips — but only −3,210 at entry, against
−8,623 for the mid-tier engineer: the lower monthly lump is
more than offset by the lower daily cost (390/day against
577/day — no uplift on the entry wage, and the same 4,200 of
second-adult lines). The position pattern inside the
civil-engineer rows is the same shape as §9 (early deepest,
late shallowest, mid and senior nearly flat at the measured
position) — the first earner's pay timing still sets the shape,
the second earner's tier sets the depth. The bridge lines (§8)
are unchanged: the worst mixed dips are still the measured-tier
ones (−72 taxi-second, −8,623 civil-engineer-second), because
the other-tier pairings dip less.

Full default-run md5: `d198a2fe0970e11aaa105bcc4bfb19f9` (IB:
`27464ea221694880a4369f805d8cd455` — kept in
`test_no_regression.py` as history). The only diffs vs IB are
these two sections; the bridge lines, the mixed sections, the
renting-cab section, the base table and all other rows are
unchanged.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the senior taxi driver (36,000) and the
senior civil engineer (65,000) as second earner are not
modelled — the wages exist in `prices.json`, but no measured
household pairs the construction worker with either, so they
stay unmodelled rather than assumed; the renting variant now
combines with a named tier (Unit KA DONE 2026-11-24 — see §14:
measured at mid-tier; the senior renting tier stays
unmeasured); only the two measured pairings are modelled (any
other profession is refused by the tool).


## 13. Addendum — Reconcile the single-earner renting-cab row (Unit JB, Queue 27)

**Date:** 2026-11-24. **Decision: follow the settlement's
26-day charge.** The single-earner renting-cab row now charges
the rental the way the settlement does — 200 NCr/day × 26
worked days = 5,200/month flat — and the v1 23-day rule is
retired, not kept.

**The question, as IB posed it (§11):** the tool's
single-earner renting-cab row charged the rental via
`extra_daily_cost` on days ≤ 26 excluding Sundays (23 days =
4,600/month), while the settlement charges 200 NCr/day × 26
worked days flat (5,200/month) — a 600/month disagreement
between the tool's two renting rows. Should the single-earner
row follow the settlement, or keep the v1 23-day rule?

**The settlement's rule, read from the source:**
`engine._settle_month` charges `rental_day × WORK_DAYS`
(`data/prices.json` `taxi_fares.cab_rental_ncr_per_day` = 200 ×
`WORK_DAYS` = 26) per taxi driver in the household, flat for
the month — no Sunday exclusion, no storm dependence, no
worked-day count. The settlement is the tool's own source of
truth for the charge (IB already followed it for the
second-earner rental), so the single-earner row following it is
agreement with the source, not a new rule.

**Why not keep the v1 23-day rule — two reasons, both
measured, not assumed:**

1. **The v1 rule disagreed with the settlement.** The
   settlement charges 5,200; the trajectory charged 4,600.
   Keeping the rule would keep a 600/month disagreement the
   tool itself records, between its own row and the settlement
   it models.
2. **The v1 rule was internally inconsistent.** The headline
   net already subtracted the full 5,200 (`extra_monthly` =
   `extra_daily_cost` × `WORK_DAYS`), while the trajectory
   charged only 4,600 — so the row's trajectory ended at 1,900
   against a net of 1,300, 600 above its own month. That is the
   same class of inconsistency Unit EY fixed for the v5 daily
   branch (a trajectory that did not end at net), and no test
   pinned the renting row's end-balance, so it stood uncaught.

The Sunday exclusion was a leftover of the v5 daily schedule,
which paid on 23 days (days 1–26 excluding Sundays); v6
already moved construction pay off that schedule, and no source
gives the rental a day-of-week rule. Keeping the 23-day rule
would need a stated reason, and there is none in any source —
only the leftover.

**Implementation:** the trajectory now charges
`extra_daily_cost` on days 1–26 — the sourced `WORK_DAYS`
count, the tool's existing convention for the row (the same
first-26-days shape the v1 rule used, minus the Sunday
exclusion). No count is invented: 26 is `WORK_DAYS`, 200 is
`prices.json`. The row now charges exactly 5,200 in the
trajectory and ends exactly at net.

**Measured result (from the tool itself):** the renting-cab
row (entry): gross 14,000, tax 0, rent 2,500, costs 12,700,
extra 5,200, net 1,300, rate 9.3%, minbal 0, end_balance 1,300
(was 1,900) — TIGHT, unchanged. The base table's renting row
and its bridge line do NOT move: the row still prints net
1,300 / minbal 0, and the bridge line still prints start 5,000
+ dip 0 = 5,000 OK — because the headline figures were already
right (the net always subtracted the full 5,200); only the
trajectory was 600 short. The Shibnagar variant's renting row
is likewise unchanged (net 1,300, minbal 0, bridge 5,000 OK).

**The md5 does not move.** The default-run output is
byte-identical (no printed figure changes), so the pinned
baseline stays the JA baseline
`b70b18972aeb5c3b2d0273b986060058` — no re-pin is needed, and
none is made. The `test_no_regression.py` md5 test passes
unchanged; the new JB test pins the row's `end_balance` ==
net instead, so the fixed inconsistency stays fixed.

**No tuning call.** Nothing in the data moves.

## 14. Addendum — Renting-cab second earner at another tier (Unit KA, Queue 28)

**Date:** 2026-11-24. **Method:** `simulate(...,
second_earner="taxi_driver", second_earner_tier="mid",
second_earner_renting_cab=True)` — the same mid-tier taxi
driver (23,000, per-fare) as §12's owning driver, but renting
the licensed cab. The combination was refused before this unit
(the tool raised on `second_earner_renting_cab=True` with a
named `second_earner_tier`); it is now modelled. The rental is
the settlement's rule, read from the source —
`engine._settle_month` charges `cab_rental_ncr_per_day` (200,
`data/prices.json`) × `WORK_DAYS` (26) = 5,200/month flat per
taxi driver in the household — and it is the same 5,200
whatever the tier: the tier moves the pay, not the rental. The
rental is a monthly cost line of 5,200, accruing evenly in the
daily model like rent (the settlement charges the same 5,200
once at month-end; HE's daily model stands). The first earner
(construction worker) still varies over entry/mid/senior.
Storm days do not change the second earner's pay or rental —
the per-fare rule has no storm days — so the storm-position
effect still comes from the first earner alone. No tier's pay
is invented: 23,000 is `prices.json` `wages_monthly`.

Measured month-1 minimum balance by storm position,
renting-cab mid-tier taxi-driver second earner beside the
owning mid-tier figures from §12:

| Tier | Early (1–2) | Mid (15–16) | Late (29–30) | Measured (4, 23) | Even (v6) | Net/mo | Owning early | Owning measured | Owning net |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| entry | 0 | 0 | 0 | 0 | 0 | 10,950 | 0 | 0 | 16,150 |
| mid | 0 | 0 | 0 | 0 | 0 | 14,194 | 0 | 0 | 19,394 |
| senior | −56 | 0 | 0 | 0 | 0 | 17,651 | 0 | 0 | 22,851 |

Costs (storm month, measured position): owning 14,850 / 16,273
/ 18,233 → renting 20,050 / 21,473 / 23,433 — the rental adds
exactly 5,200 at every tier, so the net drops by exactly 5,200
too (gross and tax untouched). Against the combined canonical
starting balance (2 × 5,000 = 10,000) the worst renting dip
leaves 10,000 − 56 = 9,944 — no bridge failure in any position,
and no TIGHT or SURVIVAL FAIL anywhere in the section. The
renting mid-tier bridge line is now wired into the tool's
printed bridge check (see §8) — 10,000 − 56 = 9,944 — so the
renting variant's bridge figure is not report-only either.

Verbatim output (new default-run section):

```
renting-cab taxi-driver second earner at another tier storm-position month (Unit KA — same 28 worked days of 30; taxi-driver second earner (mid 23,000, per-fare) renting the cab at 200/day x 26 = 5,200/mo; month-1 minbal by storm position):
profession                   tier      early     mid    late measured    even  (net/mo)  owning-early  owning-measured
construction_worker          entry         0       0       0        0       0  (net 10950)             0               0
construction_worker          mid           0       0       0        0       0  (net 14194)             0               0
construction_worker          senior      -56       0       0        0       0  (net 17651)             0               0
```

**Finding: the rental re-opens the early dip only at senior.**
The owning mid-tier driver covers the cost-only days 1–2
everywhere (753/day of taxi pay against 495–611/day of
household cost). The rental adds 173/day to the cost
(668/day entry, 716/day mid, 781/day senior) while the taxi
pay stays 753/day — so entry and mid still cover the two
days (+85/day and +38/day), but senior burns 28/day for the
first two days: −56. The measured position still dips nothing
(pay lands on days 1–3 before the day-4 storm), and the dip is
a timing fact — the same rental, charged at month-end in the
settlement, would not dip at all within the month; it is the
tool's daily accrual that puts it on days 1–2. The renting
mid-tier household still nets 10,950 / 14,194 / 17,651 a month
— the rent-before-you-buy on-ramp survives at the higher tier
too, clearly worse than owning but survivable, exactly as Unit
U designed it for the single-earner row.

**A renting civil engineer is meaningless — stated, not
modelled.** Civil engineers hold no cab, so there is no rental
to charge: the tool refuses `second_earner_renting_cab=True`
with `second_earner="civil_engineer"` (with or without a named
tier), and no renting-CE figure is recorded anywhere. Only the
taxi driver rents.

Full default-run md5: `5f50931cbaad263812473ce1c7830e59` (JA:
`b70b18972aeb5c3b2d0273b986060058` — kept in
`test_no_regression.py` as history). The only diffs vs JA are
this section and the renting bridge line; the §9/§11/§12
sections, the other bridge lines, the base table and all other
rows are unchanged.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the renting variant at the senior tier is
allowed by the tool (like IC's senior tier) but is not
measured in the default run — no measured household pairs the
construction worker with a senior taxi driver, so the senior
renting household stays unmodelled rather than assumed (same
standing rule as §12's senior second earners); the senior taxi
driver (36,000) and senior civil engineer (65,000) as second
earner stay unmodelled for the same reason.

## 15. Addendum — Sunday-exclusion audit (Unit KB, Queue 28)

**Date:** 2026-11-24. **Method:** read every day-of-week use
in `tools/economy_sim.py` and in the settlement path it
mirrors (`engine._settle_month` and everything it calls for
pay and costs: `labour.worked_days` / `day_wage_due` /
`wage_due_for`, `_living_costs`, `_pay_business_wages`,
`_pay_government_wages`, the taxi rental line), plus a
repo-wide grep for `day % 7`, `weekday` and `Sunday` across
`tools/` to catch uses outside the two files. Each use is
reported below with what it does and whether it matches its
source.

**Finding: no other day-of-week exclusion exists in any cost
or pay line — no fix is needed.** (Unit KB DONE 2026-11-24.)
The audit is recorded here
and pinned by tests (`tools/sim/tests/test_no_regression.py`,
Queue 28 Unit KB) so a later unit cannot reintroduce a weekday
exclusion unnoticed.

| # | Where | What it does | Source match? |
|---|---|---|---|
| 1 | `economy_sim.py`, `WORK_DAYS = 26` (3 uses) | The rental (`cab_rental_ncr_per_day × WORK_DAYS` = 5,200), `extra_monthly = extra_daily_cost × WORK_DAYS`, and the trajectory (`if extra_daily_cost and day <= WORK_DAYS`) — all flat, no day skipped | Matches the settlement (`engine._settle_month`: `rental_day × econ.WORK_DAYS`) |
| 2 | `economy_sim.py`, `extra_daily_cost` | The single-earner renting-cab row charges the rental on days 1–26 (JB) | Matches the settlement; the v1 23-day rule is retired (§13) |
| 3 | `economy_sim.py`, "Sunday" (15 mentions) | All 15 are in the module docstring or `#` comments, describing the retired v5 daily branch and v1 renting rule — no live code excludes a day; no `day % 7` or `weekday` anywhere in the file | History, not code — pinned by test |
| 4 | `scheduler.py`, Friday/Saturday variants (`weekday = day_index % 7`; Friday = 4, Saturday = 5) | Schedule shaping, transcribed from the `weekend_variant` notes in `data/npc-schedules.json` — all 11 professions handled in `_apply_friday` (pilot: roster decides, no work blocks); Saturday handles teacher + chef, the only two whose notes name Saturday. Measured: a construction worker keeps a work block on all 30 days of a month including all four Fridays (morning shift ends 12:30), so a Friday is a worked day and the day-wage rule pays it in full. The monthly-paid professions that lose their Friday work blocks (civil engineer, teacher, doctor on the 1-in-3 on-call rotation, software developer) pay monthly in full — `wage_due_for` returns the wage, the dock is 0 | Matches the data notes; no cost or pay line excludes the day |
| 5 | `engine.py:388`, `if day % 7 == 6:` | Weekly cadence tick: runs `weekly_drift`, `_weekly_social`, `infrastructure.weekly_update` on the seventh day | A cadence trigger, not an exclusion — it adds weekly work, it removes nothing from any pay or cost line. Sourced: Session 02 weekly drift, Session 03 weekly infrastructure update |
| 6 | `engine.py`, `taxi_factor = 1 + 0.25 × rain_days / 30 + 0.5 × storm_days / 30` | Scales taxi gross by the month's weather (rain/storm counts) | Weather, not weekday — not an exclusion. Gap recorded, not a KB fix: the tool does not model this weather surge on its taxi rows at all (Queue 29 Unit KC) |
| 7 | `engine.py:1068`, `taxi_rental_total += rental_day × econ.WORK_DAYS` | Flat 5,200 per taxi driver in the household | Matches the tool (items 1–2); no exclusion (JB) |
| 8 | `labour.py`, `worked_days` / `day_wage_due` | Counts days with ≥ 1 unbent work block from the stored schedules; no weekday filter anywhere in the module. Storm-bent, rest and broken-tool days pay 0 | The ES day-wage rule — a worked-day rule, not a weekday rule. Matches GDD-03 §2 ("paid per worked day; no work, no pay") |
| 9 | `culture.py`, `festivals_on(day % 365)`; `(day + 1) % 30 == 0` | Calendar-day festival trigger and the monthly settlement trigger | Not weekday logic; festivals are events, not cost or pay lines |

The repo-wide grep found no other uses: the only `day % 7` /
`weekday` / `Sunday` hits in `tools/` outside tests and verify
scripts are the ones above. The Friday half-day is consistent
on both sides — the tool's day-wage model pays worked/30 with
worked = 30 in a normal month, and the settlement counts a
Friday as worked (morning shift kept) — so there is no gap
there to queue.

**No fix.** Nothing in the code changes. The pinned md5 does
not move (the KA baseline stands).

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the taxi weather surge (item 6) — the
settlement scales taxi gross by rain/storm days and the tool
models taxi pay flat; Queue 29 Unit KC.
