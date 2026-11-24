# NEXORA — Economy Balance Simulator Report v7 (Unit FB, Queue 23)

**Date:** 2026-11-24. **Tool:** `tools/economy_sim.py` v7.
**Follow-up to:** Unit EY (Queue 22 — construction-worker day-wage
pay), whose honest limit this unit closes: "the tool's storm
scenario accrues the reduced pay evenly — it does not model which
days storms fall on, so its `minbal` is the even-spread figure,
not a measured one" (GDD-03 §2).

## 1. What was open

The v6 storm month pays 28/30 of the construction band (the
measured live month: 28 worked days, storm days 3 and 22) and
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
late (29–30) — plus the measured position (days 3 and 22,
where the live month's storms actually fell). A `storm_days`
that disagrees with `day_wage_worked_days`, names a day outside
1..30, or repeats a day is refused, as is `storm_days` for any
non-day-wage profession.

Measured month-1 minimum balance, by storm position (net is the
same for every position — the month pays the same 28/30 of the
band whatever the days):

| Tier | Early (1–2) | Mid (15–16) | Late (29–30) | Measured (3, 22) | Even (v6) | Net/mo |
|---|---:|---:|---:|---:|---:|---:|
| entry | −500 | 0 | 0 | −150 | 0 | 900 |
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
measured position dips only the entry row: on day 3 the entry
household has banked two days (+100) and then pays a cost-only
day (−250), reaching −150; mid and senior have banked more by
then (mid +339, senior +595) and stay above zero.

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

New day-wage storm-position section (v7 — measured minbal per position):

```
day-wage storm-position month (Unit FB — same 28 worked days of 30; month-1 minbal by storm position):
profession                   tier      early     mid    late measured    even  (net/mo)
construction_worker          entry      -500       0       0     -150       0  (net 900)
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
  (days 3 and 22) already dips the entry row to −150, and the
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
  forecast — only the measured position (days 3 and 22) is where
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

**Open, recorded (Queue 25 material):** correct
`STORM_MEASURED_DAYS` to (4, 23) or relabel the (3, 22)
position as 0-based day indices; the tool's daily trajectory
has no settlement counterpart while pay and costs settle
monthly; the taxi-fare drain vs the flat transport line is
unmodelled; the bridge check's 5,000 start is canonical, not
settled.

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

| Tier | Early (1–2) | Mid (15–16) | Late (29–30) | Measured (3, 22) | Even (v6) | Net/mo | Single early | Single measured | Single net |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| entry | −780 | 0 | 0 | 0 | 0 | 5,100 | −500 | −150 | 900 |
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
−150 entry): once pay starts landing on day 3, two pay packets
cover the cost. But on days 1–2 no pay has arrived for anyone,
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

**Open, recorded:** the second earner is a construction worker
at the same tier by definition of this scenario — a household
whose second earner works another profession (the §6 cases: a
taxi driver, a civil engineer) is not modelled; the two-earner
bridge line is not wired into the tool's printed bridge check
(Unit GE wires the single-earner worst dip only).

## 8. Addendum — Storm-position bridge line (Unit GE, Queue 24)

**Date:** 2026-11-24. The bridge check in the tool's default run
now prints a second line for the `construction_worker` entry
row — starting balance + the worst storm-position minbal (the
minimum across the early / mid / late / measured positions):

```
first-month bridge check (entry rows: starting balance + zero-start dip = worst month-1 balance):
  construction_worker    start   5000 + dip       0 =    5000  OK
  construction_worker    start   5000 + storm dip    -500 =    4500  OK  (worst storm position)
```

The worst dip is the early position (−500 entry; mid −595,
senior −726) — the line wires the minimum, not the measured
position. The §5 bridge observation (entry 5,000 − 500 = 4,500)
is now the tool's printed output, not a report-only
calculation; a failing storm line would join `BRIDGE FAIL`
(none fails). The two-earner worst dip is not wired into the
bridge check — the line covers the single-earner entry row only
(§7 records the two-earner bridge figure, 10,000 − 1,231 =
8,769, as prose).

Full default-run md5: `d699ae7d37fe8ca077f873ba238dd86b` (v7:
`e598e416c07b21bacee9fe98fdb27244` — kept in
`test_no_regression.py` as history, with v6
`9ac10779c231b7aa6120a6ff457982de`). The only diffs vs v7 are
the §7 two-earner section and this bridge line; the base table,
business P&L, pacing and all other rows are unchanged.

**No tuning call.**
