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

## 16. Addendum — Taxi weather surge (Unit KC, Queue 29)

**Date:** 2026-11-24. **Method:** re-run the EY live month
exactly (`Simulation`, seed `ey-measure`,
`generate_population(60)`, 32 days) and read the month-1
weather presets from `daily_weather` and every taxi driver's
settled month-1 wage from `economy_ledger` (the `wage` row at
`game_minutes` 43,200) against the band in `employments`.
The tool change is `simulate(..., taxi_rain_days=...,
taxi_storm_days=...)` — the caller names the month's weather
counts and the tool applies the settlement's own formula.

**Measured: the EY month's weather is 2 rain days, 2 storm
days — taxi_factor 1.05.** Rain falls on day_index 2 and 28,
storm on day_index 3 and 22 (the same storm days GC measured);
`1 + 0.25 × 2/30 + 0.5 × 2/30 = 1.05` exactly. All six taxi
drivers in the world settled at exactly band × 1.05 — entry
14,000 → 14,700, mid 23,000 → 24,150, senior 36,000 → 37,800
— every one paid by SYS-EMPLOYERS (no business employer, no
treasury employer in the world), so the settled grosses are
14,700 / 24,150 / 37,800. The Priya-household taxi earner
(Rasel Begum, `NEX000041`, head of `HH000022` — the household
GC §6 records as the taxi-driver second earner at 14,000)
settled 14,700: the surge applies to a second earner exactly
as to a single earner, because the settlement scales every
taxi earner's gross in the same household loop.

**DECIDED: model it — the tool now scales taxi gross by the
settlement's formula.** The alternative (record the
difference and leave the tool flat) was rejected: the formula
is source-given (`engine._settle_month`), its inputs are
measured counts from a seeded run, the effect is material
(+455 to +1,080 net a month on the single-earner rows), and
the tool already models weather-dependent pay parametrically
(`storm_days` for the construction worker) — a weather input
with no model would leave the same class of gap FB closed.
The model follows the settlement exactly: the gross is scaled
first and the tax and the lifestyle uplift are recomputed on
the surged gross (the settlement taxes what it paid and
computes the uplift on it), the rental stays the flat 5,200
(the settlement charges it unsurged), and weather counts
outside a taxi row are refused. The base table stays flat —
the canonical bands — and the KC section below is the weather
scenario, at the measured month's weather.

Single-earner taxi rows, flat vs surged at the EY month's
weather (gross, tax, uplift, net):

| Tier | Flat gross | Surged gross | Flat net | Surged net | Delta |
|---|---:|---:|---:|---:|---:|
| entry | 14,000 | 14,700 | 6,500 | 6,955 | +455 |
| mid | 23,000 | 24,150 | 11,950 | 12,641 | +691 |
| senior | 36,000 | 37,800 | 19,750 | 20,830 | +1,080 |
| entry (renting cab) | 14,000 | 14,700 | 1,300 | 1,755 | +455 |
| mid (renting cab) | 23,000 | 24,150 | 6,750 | 7,441 | +691 |
| senior (renting cab) | 36,000 | 37,800 | 14,550 | 15,630 | +1,080 |

**Second weather factors (Unit MP, Queue 47, §36):** the
formula is corroborated at two more live factors, same EY
shape (60 population, 32 days) — seed `mo-probe-1`: 1 rain
day + 2 storm days, factor 1.0417, settled grosses 14,583 /
23,958 / 37,500; seed `mo-probe-2`: 4 rain days + 3 storm
days, factor 1.0833, settled grosses 15,167 / 24,917 /
39,000. Per-tier gross deltas: at 1.0417, +583 / +958 /
+1,500; at 1.0833, +1,167 / +1,917 / +3,000 (entry/mid/
senior). Every settled gross is round(band × factor) — the
tool rounds the same way the settlement does.

**Factors outside the 1.04–1.09 band (Unit MQ, Queue 48,
§37):** the formula is corroborated at two more live
factors, both above the band, same EY shape (60 population,
32 days) — seed `mq-probe-1`: 8 rain days + 3 storm days,
factor 1.1167, settled grosses 15,633 / 25,683 (entry and
mid only — no senior driver in the world); seed
`mq-probe-6`: 6 rain days + 3 storm days, factor 1.1000,
settled grosses 15,400 / 25,300 (entry and mid only — again
no senior driver). Per-tier gross deltas: at 1.1167, +1,633 / +2,683 / +4,200;
at 1.1000, +1,400 / +2,300 / +3,600 (entry/mid/senior). The senior grosses at these factors
(40,200 / 39,600) are tool-computed, not live-settled — no
senior taxi driver settled live above the band in either
world, so that settlement stays unmeasured. Every settled
gross is round(band × factor) — the tool rounds the same
way the settlement does.

**Storm-heavy month above the band (Unit MR, Queue 49,
§38):** the formula is corroborated at one more live
factor, 1.1083, in a storm-heavy month — seed
`mq-probe-11`: 3 rain days + 5 storm days, factor 1.1083,
settled gross 25,492 (mid only — one taxi driver in the
world). A second seeded month lands on the SAME factor
from the opposite mix — seed `mr-probe-7`: 9 rain days + 2
storm days, factor 1.1083, settled grosses 15,517 / 25,492
(entry and mid) — so the settlement keys on the factor,
not the mix: two different weather mixes at the same
factor settle identically. Per-tier gross deltas at
1.1083: +1,517 / +2,492 / +3,900 (entry/mid/senior). The
senior gross at this factor (39,900) is tool-computed, not
live-settled — no senior taxi driver settled live above
the band in either world, so that settlement stays
unmeasured. Every settled gross is round(band × factor) —
the tool rounds the same way the settlement does, and this
time the rounding goes up at both settled tiers
(15,516.67 → 15,517; 25,491.67 → 25,492).

**Live senior settlement above the band (Unit MS, Queue 50,
§39):** the senior gross above the band is now live-settled
for the first time — seed `ms-probe-11`: 5 rain days + 3
storm days, factor 1.0917, four taxi drivers all
SYS-EMPLOYERS-paid, settled grosses 15,283 / 25,108 /
25,108 / 39,300 (entry, mid, mid, senior). A second seeded
month lands on the SAME factor from different day positions
— seed `ms-probe-7`: 5 rain days + 3 storm days, factor
1.0917, two taxi drivers all SYS-EMPLOYERS-paid, both mid
settled 25,108 — so the settlement keys on the counts, not
the positions: the same counts settle identically wherever
the wet days fall. Per-tier gross deltas at 1.0917: +1,283 / +2,108 / +3,300 (entry/mid/senior). Every settled gross is
round(band × factor) — the tool rounds the same way the
settlement does, and this time the rounding goes down at
both settled lower tiers (15,283.33 → 15,283; 25,108.33 →
25,108), while the senior product is an integer up to float
error (36,000 × 1.0917 = 39,300.00...), so rounding is a
no-op there.

**Second above-band senior settlement, at a different
factor (Unit MT, Queue 51, §40):** the senior gross above
the band is now live-settled at a second factor — seed
`mt-probe-5`: 7 rain days + 3 storm days, factor 1.1083,
five taxi drivers all SYS-EMPLOYERS-paid, settled grosses
25,492 × 4 (mid) and 39,900 (senior). The 39,900 at 1.1083
is now a measured figure, superseding §38's tool-computed
status for that factor. A second seeded month lands on the
MS factor — seed `mt-probe-13`: 5 rain days + 3 storm
days, factor 1.0917, five taxi drivers all
SYS-EMPLOYERS-paid, four mid settled 25,108 and senior
NEX000028 settled 39,300 — the second live senior
settlement at 1.0917. Per-tier gross deltas at 1.1083:
+1,517 / +2,492 / +3,900 (entry/mid/senior). Every settled
gross is round(band × factor) — the tool rounds the same
way the settlement does, and this time the rounding goes
up at both lower tiers (15,516.67 → 15,517; 25,491.67 →
25,492), as MR already measured at this factor, while the
senior product is exactly 39,900.0, so rounding is a no-op
there. The senior rounding question is closed by
construction: the senior gross is 36,000 + 300 × rain +
600 × storm — always an integer — so rounding is a no-op
at the senior tier at every factor.

**Senior settlement at 1.1000; the 1.1167 hunt finds none
(Unit MU, Queue 52, §41):** a twenty-four-seed hunt for a
month at factor 1.1167 holding a senior taxi driver finds
no month at 1.1167 at all (highest factor in the sweep
1.1000), so the senior gross at 1.1167 (40,200) stays
tool-computed only. The sweep still measures something
real: the senior gross at 1.1000 is now live-settled — seed
`mu-probe-8`: 6 rain days + 3 storm days, factor 1.1000,
three taxi drivers all SYS-EMPLOYERS-paid, two mid settled
25,300 and senior NEX000012 settled 39,600; and seed
`mu-probe-16`: 8 rain days + 2 storm days, the SAME factor
1.1000 from the opposite mix, nine taxi drivers all
SYS-EMPLOYERS-paid, two entry settled 15,400, five mid
settled 25,300 and two seniors NEX000045 and NEX000060
settled 39,600 — so the settlement keys on the factor, not
the mix, at 1.1000 as MR already measured at 1.1083. The
39,600 at 1.1000 is now a measured figure, superseding
§37's tool-computed status for that factor. A third live
senior settlement at 1.0917 also lands — seed `mu-probe-3`:
7 rain days + 2 storm days, factor 1.0917 from a different
mix than MS/MT's 5 + 3, two taxi drivers all
SYS-EMPLOYERS-paid, mid settled 25,108 and senior
NEX000029 settled 39,300. Per-tier gross deltas at 1.1000:
+1,400 / +2,300 / +3,600 (entry/mid/senior). Every settled
gross is round(band × factor) — the tool rounds the same
way the settlement does, and at 1.1000 the rounding is a
no-op at every tier (the products are integers up to float
error). The senior tier above the band now rests on three
live factors (1.0917, 1.1000, 1.1083).

**Senior settlement at 1.1167, live-settled twice by
weather-first hunt (Unit MV, Queue 53, §42):** MU proved
the month's weather is seed-only, so MV scanned 200 fresh
seeds on the weather signature alone (rain + 2 × storm =
14) without running the population, then ran the full EY
shape only on the five matches — `mv-probe-3` (6 rain + 4
storm), `mv-probe-38` (4 + 5), `mv-probe-105` (8 + 3, MQ's
mix), `mv-probe-106` (6 + 4) and `mv-probe-115` (4 + 5) —
and every one of the five reproduces its scanned counts
exactly in the full run, so the pre-filter is itself
verified. All five months are factor 1.1167, 15 taxi
drivers in all, all SYS-EMPLOYERS-paid, every settled
gross round(band × factor): seed `mv-probe-105` holds senior
NEX000014 settled 40,200 (five drivers: entry 15,633, mid
25,683 × 3, senior 40,200) and seed `mv-probe-115` holds
senior NEX000053 settled 40,200 (three drivers: mid 25,683
× 2, senior 40,200) — so the settlement keys on the factor,
not the mix, at 1.1167 as MR already measured at 1.1083 and
MU at 1.1000. The 40,200 at 1.1167 is now a measured
figure, superseding §37's and §41's tool-computed status
for that factor. The other three matches hold no senior
(`mv-probe-3`: entry 15,633 × 2, mid 25,683; `mv-probe-38`:
mid 25,683 × 2; `mv-probe-106`: entry 15,633 × 2). Per-tier
gross deltas at 1.1167: +1,633 / +2,683 / +4,200
(entry/mid/senior). Every settled gross is round(band ×
factor) — the tool rounds the same way the settlement
does, and at 1.1167 the rounding goes down at both lower
tiers (15,633.33 → 15,633; 25,683.33 → 25,683), while the
senior product is exactly 40,200.0, so rounding is a no-op
there. The senior tier above the band now rests on four
live factors (1.0917, 1.1000, 1.1083, 1.1167).

**Taxi surge at the smallest factor, 1.0083, live-settled
at all three tiers (Unit MW, Queue 54, §43):** MV closed
the above-band senior chain at the top (1.1167) and left
the floor of the surge range unmeasured — factor 1.0083
(1 rain day, 0 storm days) is the floor and no month had
settled live at it (the lowest corroborated factor was
1.0167, MT §40). MW hunted with the same weather-first
pre-filter MV proved: scan 200 fresh seeds on the weather
signature alone (rain + 2 × storm = 1) without running
the population, then run the full EY shape only on the
three matches — `mw-probe-15` (1 rain, day_index 3),
`mw-probe-124` (1 rain, day_index 11) and `mw-probe-150`
(1 rain, day_index 9) — and every one of the three
reproduces its scanned counts exactly in the full run, so
the pre-filter is itself verified again. All three months
are factor 1.0083, 9 taxi drivers in all, all
SYS-EMPLOYERS-paid, every settled gross round(band ×
factor): seed `mw-probe-15` holds senior NEX000059 settled
36,300 (five drivers: entry 14,117 × 2, mid 23,192 × 2,
senior 36,300) and seed `mw-probe-150` holds seniors
NEX000015 and NEX000028 settled 36,300 each (four drivers:
mid 23,192 × 2, senior 36,300 × 2) — three senior
settlements at the floor factor, from two seeds with the
rain on different days, so the settlement keys on the
counts, not the positions, at 1.0083 too; seed
`mw-probe-124` holds no taxi driver at all. Per-tier gross
deltas at 1.0083: +117 / +192 / +300 (entry/mid/senior).
Every settled gross is round(band × factor) — the tool
rounds the same way the settlement does, and at 1.0083 the
rounding goes up at both lower tiers (14,116.67 → 14,117;
23,191.67 → 23,192), while the senior product is exactly
36,300.0, so rounding is a no-op there. The surge is now
corroborated at eight live factors (1.0083, 1.0417, 1.05,
1.0833, 1.0917, 1.1000, 1.1083, 1.1167), and at every step
of the factor ladder from the floor to the top (rain + 2 ×
storm = 1..14).

**Taxi surge at the next factor above the top, 1.1250,
live-settled at the entry tier (Unit MX, Queue 55, §44):**
MW completed the ladder from the floor to the top but no
factor above 1.1167 had ever been measured, so MX hunted
with the same weather-first pre-filter MW proved: scan
200 fresh seeds on the weather signature alone (rain + 2 ×
storm = 15) without running the population, then run the
full EY shape only on the one match — `mx-probe-68` (3
rain, day_index 19, 20, 23; 6 storm, day_index 1, 15, 17,
21, 27, 28) — and the full run reproduces its scanned
counts exactly, so the pre-filter is itself verified
again. The month is factor 1.1250, two taxi drivers, both
entry, both SYS-EMPLOYERS-paid, both settled 15,750 =
round(14,000 × 1.1250): NEX000005 and NEX000040. No mid
and no senior driver in this month, so the senior gross at
1.1250 (40,500) stays tool-computed only. Per-tier gross
deltas at 1.1250: +1,750 / +2,875 / +4,500
(entry/mid/senior). Every settled gross is round(band ×
factor) — the tool rounds the same way the settlement
does, and at 1.1250 the rounding is a no-op at every tier
(all three products are exact integers: 15,750.0,
25,875.0, 40,500.0). The surge is now corroborated at
nine live factors (1.0083, 1.0417, 1.05, 1.0833, 1.0917,
1.1000, 1.1083, 1.1167, 1.1250), and the ladder now
extends one step above the old top (rain + 2 × storm =
1..15).

**Taxi surge at the top step, 1.1250, live-settled at the mid
tier — the senior hunt finds none (Unit MY, Queue 56, §45):** MX live-settled the entry gross at the first factor
above the old top but the month held no senior, so MY
hunted with the same weather-first pre-filter MX proved:
scan 200 fresh seeds on the weather signature alone (rain +
2 × storm = 15) without running the population, then run
the full EY shape only on the two matches — `my-probe-53`
(11 rain, day_index 0, 3, 8, 9, 10, 14, 17, 18, 20, 23, 24;
2 storm, day_index 26, 27) and `my-probe-137` (7 rain,
day_index 9, 10, 13, 16, 20, 23, 24; 4 storm, day_index 2,
14, 17, 27) — and both full runs reproduce their scanned
counts exactly, so the pre-filter is itself verified a
fifth time. Both months are factor 1.1250, three taxi
drivers in all, all mid, all SYS-EMPLOYERS-paid, all
settled 25,875 = round(23,000 × 1.1250): NEX000002 and
NEX000051 in `my-probe-53`, NEX000035 in `my-probe-137` —
the mid gross at 1.1250 is now live-settled from two
different mixes, so the settlement keys on the factor, not
the mix, at 1.1250 too. No senior driver in either month,
so the senior gross at 1.1250 (40,500) stays
tool-computed only and the senior tier above the band still
rests on four live factors (1.0917, 1.1000, 1.1083,
1.1167). Per-tier gross deltas at 1.1250: +1,750 / +2,875 /
+4,500 (entry/mid/senior). Every settled gross is round(band
× factor) — the tool rounds the same way the settlement
does, and at 1.1250 the rounding is a no-op at every tier
(all three products are exact integers: 15,750.0, 25,875.0,
40,500.0). At 1.1250 the entry tier is live (MX) and the
mid tier is now live (MY); only the senior tier stays
tool-computed.

**Taxi surge at the top step, 1.1250, wider hunt — the senior
still settles nowhere; both lower tiers settle live from a
third mix (Unit MZ, Queue 57, §46):** MY hunted 200 fresh
seeds and found two months at the factor, both holding mid
drivers only, so MZ hunted with the same weather-first
pre-filter over a wider bounded scan of 400 fresh seeds on
the weather signature alone (rain + 2 × storm = 15) without
running the population, then ran the full EY shape only on
the one match — `mz-probe-397` (7 rain, day_index 0, 1, 10,
17, 18, 22, 29; 4 storm, day_index 9, 16, 23, 25) — and the
full run reproduces its scanned counts exactly, so the
pre-filter is itself verified a sixth time. The month is
factor 1.1250, three taxi drivers, all SYS-EMPLOYERS-paid:
entry NEX000010 and NEX000058 settled 15,750 = round(14,000
× 1.1250) each, mid NEX000043 settled 25,875 = round(23,000
× 1.1250) — the 7 rain + 4 storm mix now has a second live
instance, from different day positions than `my-probe-137`,
so the settlement keys on the counts, not the positions, at
1.1250 too. No senior driver in the month, so the senior
gross at 1.1250 (40,500) stays tool-computed only and the
senior tier above the band still rests on four live factors
(1.0917, 1.1000, 1.1083, 1.1167). Per-tier gross deltas at
1.1250: +1,750 / +2,875 / +4,500 (entry/mid/senior). Every
settled gross is round(band × factor) — the tool rounds the
same way the settlement does, and at 1.1250 the rounding is
a no-op at every tier (all three products are exact
integers: 15,750.0, 25,875.0, 40,500.0). At 1.1250 the entry
tier is now live four times (MX 2 + MZ 2) and the mid tier
four times (MY 3 + MZ 1); only the senior tier stays
tool-computed.

**Taxi surge at the top step, 1.1250, still-wider hunt —
the senior settles live at last (Unit NA, Queue 58, §47):**
MZ hunted 400 fresh seeds and found one month at the
factor holding entry and mid drivers only, so NA hunted
with the same weather-first pre-filter over a still-wider
bounded scan of 800 fresh seeds on the weather signature
alone (rain + 2 × storm = 15) without running the
population, then ran the full EY shape only on the ten
matches — `na-probe-34` (9 rain, day_index 2, 6, 11, 12,
15, 16, 20, 25, 28; 3 storm, day_index 1, 14, 19),
`na-probe-93` (9 rain, day_index 3, 5, 7, 9, 11, 15, 20,
22, 23; 3 storm, day_index 6, 8, 28), `na-probe-98` (3
rain, day_index 8, 12, 28; 6 storm, day_index 9, 15, 19,
23, 27, 29), `na-probe-129` (3 rain, day_index 10, 18, 21;
6 storm, day_index 0, 17, 19, 24, 26, 29), `na-probe-311`
(7 rain, day_index 0, 4, 7, 12, 15, 18, 21; 4 storm,
day_index 3, 6, 10, 22), `na-probe-341` (5 rain, day_index
0, 4, 8, 26, 28; 5 storm, day_index 2, 13, 20, 22, 23),
`na-probe-389` (5 rain, day_index 5, 9, 17, 22, 27; 5
storm, day_index 0, 3, 15, 25, 28), `na-probe-439` (3
rain, day_index 20, 26, 27; 6 storm, day_index 1, 6, 13,
18, 22, 28), `na-probe-660` (5 rain, day_index 9, 11, 12,
20, 23; 5 storm, day_index 0, 4, 6, 13, 21), `na-probe-788`
(11 rain, day_index 3, 9, 13, 14, 15, 18, 19, 24, 26, 28,
29; 2 storm, day_index 8, 23) — and every full run
reproduces its scanned counts exactly, so the pre-filter
is itself verified a seventh time. All ten months are
factor 1.1250, nineteen taxi drivers in all, all
SYS-EMPLOYERS-paid: one entry settled 15,750, seventeen
mid settled 25,875, and senior NEX000043 in `na-probe-129`
settled 40,500 = round(36,000 × 1.1250) — the senior gross
at 1.1250 is now live-settled, and the senior tier above
the band now rests on five live factors (1.0917, 1.1000,
1.1083, 1.1167, 1.1250). Per-tier gross deltas at 1.1250:
+1,750 / +2,875 / +4,500 (entry/mid/senior). Every settled
gross is round(band × factor) — the tool rounds the same
way the settlement does, and at 1.1250 the rounding is a
no-op at every tier (all three products are exact
integers: 15,750.0, 25,875.0, 40,500.0). At 1.1250 all three
tiers are now live: entry five times (MX 2 + MZ 2 + NA 1),
mid twenty-one times (MY 3 + MZ 1 + NA 17), senior once
(NA).

**Taxi surge at 1.0750, weather-first — the senior was
already live; the hunt finds two more, and the record is
corrected (Unit NB, Queue 59, §48):** NA live-settled the
senior at the top step but left 1.0750 recorded as the last
in-ladder senior gap, so NB hunted with the same
weather-first pre-filter over a bounded scan of 24 fresh
seeds on the weather signature alone (rain + 2 × storm =
9) without running the population, then ran the full EY
shape only on the nine matches — `nb-probe-2` (7 rain, 1
storm), `nb-probe-4` (7 + 1), `nb-probe-5` (5 + 2),
`nb-probe-6` (5 + 2), `nb-probe-7` (5 + 2), `nb-probe-10`
(5 + 2), `nb-probe-11` (7 + 1), `nb-probe-15` (7 + 1),
`nb-probe-23` (9 + 0) — and every full run reproduces its
scanned counts exactly, so the pre-filter is itself
verified an eighth time. All nine months are factor
1.0750, twenty-seven taxi drivers in all, all
SYS-EMPLOYERS-paid: seven entry settled 15,050, eighteen
mid settled 24,725, and two seniors settled 38,700 =
round(36,000 × 1.0750) — NEX000007 in `nb-probe-2` and
NEX000048 in `nb-probe-15`, both from the 7 rain + 1 storm
mix but from different day positions, so the settlement
keys on the counts, not the positions, at 1.0750 too.
`nb-probe-15` holds all three tiers (entry NEX000036, mid
NEX000001, NEX000026 and NEX000056, senior NEX000048),
and `nb-probe-23` is the first live 9 rain + 0 storm month
at 1.0750. Per-tier gross deltas at 1.0750: +1,050 /
+1,725 / +2,700 (entry/mid/senior). Every settled gross is
round(band × factor) — the tool rounds the same way the
settlement does, and at 1.0750 the rounding is a no-op at
every tier (the products are exact integers from the 7/1
and 9/0 mixes, and sit a float epsilon above the integer
from the 5/2 mix with round() landing on them, the same
shape as MU at 1.1000). **CORRECTED — there was no gap:**
the senior gross at 1.0750 (38,700) was already
live-settled before NB — the report's own sweep tables
already held two senior settlements at 1.0750,
`ms-probe-8` (MS, Queue 50, §39 table: senior NEX000034)
and `mu-probe-14` (MU, Queue 52, §41 table: senior
NEX000007) — but the MS/MU verify scripts only re-derived
their headline seeds, so the 1.0750 seniors were never
highlighted in the §16 prose chain and the MW–NA summaries
(which read the prose, not the tables) recorded a gap that
did not exist. NB re-derives all five prior 1.0750 months
live (`ms-probe-8`, `mt-probe-10`, `mt-probe-22`,
`mu-probe-2`, `mu-probe-14`) and every one reproduces its
recorded row exactly, so the correction is measured, not
asserted: before NB the tiers at 1.0750 were already live
entry twice, mid nine times, senior twice, and after NB
they are live entry nine times, mid twenty-seven times,
senior four times. The senior tier is now live at every
step of the ladder from the floor 1.0083 to the top 1.1250
except 1.0167 — the only remaining in-ladder senior gap
(`ms-probe-12`, `ms-probe-13` and `mt-probe-8` hold entry
and mid only).

**Taxi surge at 1.0167, weather-first — the senior settles
live at last; the ladder is closed (Unit NC, Queue 60,
§49):** NB corrected the record at 1.0750 and left 1.0167
as the only remaining in-ladder senior gap, so NC checked
that gap claim against the sweep tables first, per the NB
lesson — re-deriving all three prior 1.0167 months live
(`ms-probe-12`, `ms-probe-13` and `mt-probe-8`) reproduces
their recorded rows exactly and none holds a senior, so
the gap was real this time. NC then hunted with the same
weather-first pre-filter over a bounded scan of 800 fresh
seeds on the weather signature alone (rain + 2 × storm =
2) without running the population, then ran the full EY
shape only on the twelve matches — all 2 rain + 0 storm,
at twelve different day positions — and every full run
reproduces its scanned counts exactly, so the pre-filter
is itself verified a ninth time. All twelve months are
factor 1.0167, thirty-eight taxi drivers in all, all
SYS-EMPLOYERS-paid: seven entry settled 14,233,
twenty-five mid settled 23,383, and six seniors settled
36,600 = round(36,000 × 1.0167) — NEX000022 in
`nc-probe-306`, NEX000025 in `nc-probe-472`, NEX000029 and
NEX000030 in `nc-probe-525`, NEX000049 in `nc-probe-597`
and NEX000026 in `nc-probe-629`, all from the same 2 rain
+ 0 storm mix but from different day positions, so the
settlement keys on the counts, not the positions, at
1.0167 too. `nc-probe-597` and `nc-probe-629` each hold
all three tiers. Per-tier gross deltas at 1.0167: +233 /
+383 / +600 (entry/mid/senior). Every settled gross is
round(band × factor) — the tool rounds the same way the
settlement does, and at 1.0167 the rounding goes down at
both lower tiers (14,233.333… → 14,233; 23,383.333… →
23,383) while the senior product is exactly 36,600.0, so
the rounding is a no-op there. Before NC the tiers at
1.0167 were live entry three times, mid four times,
senior never; after NC they are live entry ten times, mid
twenty-nine times, senior six times. The senior tier is
now live at every step of the ladder from the floor
1.0083 to the top 1.1250 — no in-ladder senior gap
remains. The only unmeasured factor is above the top
(1.1333, Queue 61).

**Taxi surge at the factor above the new top, 1.1333 —
the senior settles live above the top; the ladder extends
one step (Unit ND, Queue 61, §50):** NC closed the ladder
but no month in the record held a settlement at 1.1333 at
any tier, so ND checked that gap claim against the sweep
tables first, per the NB lesson — the factor column of
every sweep table tops out at 1.1250, and 1.1333 appears
in the report only as the factor above the top — so the
gap was real. ND then hunted with the same weather-first
pre-filter over a bounded scan of 800 fresh seeds on the
weather signature alone (rain + 2 × storm = 16) without
running the population, then ran the full EY shape only
on the six matches — across three mixes: `nd-probe-68`
(6 rain + 5 storm), `nd-probe-165` (6 + 5), `nd-probe-190`
(8 + 4), `nd-probe-270` (8 + 4), `nd-probe-650` (10 + 3),
`nd-probe-792` (8 + 4) — and every full run reproduces
its scanned counts exactly, so the pre-filter is itself
verified a tenth time. All six months are factor 1.1333,
fourteen taxi drivers in all, all SYS-EMPLOYERS-paid:
two entry settled 15,867 (NEX000009 in `nd-probe-68`,
NEX000029 in `nd-probe-270`), eight mid settled 26,067
(NEX000011 and NEX000042 in `nd-probe-190`, NEX000031 in
`nd-probe-270`, NEX000002 in `nd-probe-650`, NEX000008,
NEX000014, NEX000029 and NEX000032 in `nd-probe-792`),
and four seniors settled 40,800 = round(36,000 × 1.1333)
— NEX000006 and NEX000007 in `nd-probe-165`, NEX000032
and NEX000059 in `nd-probe-650`, from two different mixes
at different day positions, so the settlement keys on the
counts, not the positions, at 1.1333 too. `nd-probe-165`
and `nd-probe-650` each hold two seniors; no month holds
all three tiers. Per-tier gross deltas at 1.1333: +1,867 /
+3,067 / +4,800 (entry/mid/senior). Every settled gross is
round(band × factor) — the tool rounds the same way the
settlement does, and at 1.1333 the rounding goes up at
both lower tiers (15,866.67 → 15,867; 26,066.67 → 26,067)
while the senior product is exactly 40,800.0, so the
rounding is a no-op there. Before ND the tiers at 1.1333
were live entry never, mid never, senior never; after ND
they are live entry twice, mid eight times, senior four
times. The surge is still corroborated at nine live
factors (1.0083, 1.0417, 1.05, 1.0833, 1.0917, 1.1000,
1.1083, 1.1167, 1.1250), and the ladder now extends one
step above the old top (rain + 2 × storm = 1..16), with
1.1333 live-settled at all three tiers. Correction to §49,
measured: §49 wrote "feasibility checked: 6 of 1,000 fresh
seeds" — the scan ND actually ran was 800 fresh seeds and
the same six match, so the hit rate is 6 in 800 (0.75%);
a check of `nd-probe-801`–`nd-probe-1000` finds no further
match, so only the denominator was off. The only
unmeasured factor is above the new top (1.1417, Queue 62).

The entry driver's uplift appears only under the surge (245:
35% of the 700 above the entry band) — the flat entry row has
none, because its gross equals its entry wage. The mid
driver's surged tax is 457, not 458: the 5% band starts at
15,001 in `prices.json`, so 5% falls on 24,150 − 15,001 =
9,149. The renting row's net rises by the same +455 as the
owning entry row — the rental does not scale. The mid and
senior renting rows rise by the same deltas as their owning
rows (+691 / +1,080), so all three renting rows are now
printed in the section (Unit MB, Queue 33, §22).

Taxi-driver second earner, early-position minbal and net,
flat vs surged:

| Second earner | First-earner tier | Early flat | Early surged | Net flat | Net surged |
|---|---|---:|---:|---:|---:|
| entry, owning | entry | 0 | 0 | 10,700 | 11,155 |
| entry, owning | mid | 0 | 0 | 13,944 | 14,399 |
| entry, owning | senior | −72 | −42 | 17,401 | 17,856 |
| mid, owning | entry | 0 | 0 | 16,150 | 16,841 |
| mid, owning | mid | 0 | 0 | 19,394 | 20,085 |
| mid, owning | senior | 0 | 0 | 22,851 | 23,542 |
| mid, renting | entry | 0 | 0 | 10,950 | 11,641 |
| mid, renting | mid | 0 | 0 | 14,194 | 14,885 |
| mid, renting | senior | −56 | −9 | 17,651 | 18,342 |
| entry, renting | entry | −193 | −163 | 5,500 | 5,955 |
| entry, renting | mid | −288 | −258 | 8,744 | 9,199 |
| entry, renting | senior | −419 | −389 | 12,201 | 12,656 |
| senior, owning | entry | 0 | 0 | 23,950 | 25,030 |
| senior, owning | mid | 0 | 0 | 27,194 | 28,274 |
| senior, owning | senior | 0 | 0 | 30,651 | 31,731 |

**The Shibnagar variant now prints its own surge table (Unit
MD, Queue 35, §24).** The `--shibnagar` run prints this
District 1 section first, then the variant's own table
computed on Shibnagar's rents — all 132 rows identical to
the figures above, so the table here stands for both cities
and the variant's table is a second printing, not a second
set of figures.

**Finding: the surge shrinks all three early dips but closes
none of them.** The HD senior dip −72 → −42, the KA renting
senior dip −56 → −9, and the IB entry renting dips −193 →
−163 / −288 → −258 / −419 → −389 — the surged taxi pay
(791/day against 781/day of household cost at senior) almost
covers the two storm-less days, but not quite. The entry
renting household's nets rise +455 at every tier — exactly
the entry taxi surge, since the second earner's gross is the
entry band and the rental stays the flat 5,200 unsurged. The
senior owning row (Unit MN, Queue 45, §34) dips 0 flat and
surged at every tier — the per-fare senior pay already covers
the cost-only days flat, so there is no dip for the surge to
shrink — and its nets rise +1,080 at every tier, exactly the
senior taxi surge. The renting senior row (Unit MO, Queue 46,
§35) was measured on the same surge pattern beside it and dips
0 flat and surged at every tier and position too — its nets rise
+1,080 at every tier (18,750 → 19,830, 21,994 → 23,074, 25,451
→ 26,531), exactly 5,200 below the owning surged net at every
tier — so the surge adds no finding and the pairing stays
allowed but unprinted; the table is now closed, five pairings
printed and the sixth decided unprinted with a measured reason.
The measured position dips 0 flat and surged for every pairing
and tier. The surge can only raise a taxi gross
(the factor is ≥ 1 for any weather), so the flat bridge lines
are the conservative case and they stand unchanged — no
bridge line is re-wired, and the KA line (10,000 − 56 =
9,944) is still the worst renting case the tool prints.

Verbatim output (new default-run section):

```
taxi weather-surge month (Unit KC — the EY month's weather: 2 rain days, 2 storm days, taxi_factor 1.05; taxi gross x 1.05, tax and uplift recomputed on the surged gross):
profession                   tier    flat gross  surged flat net surged net delta net
taxi_driver                  entry        14000   14700     6500       6955      +455
taxi_driver                  mid          23000   24150    11950      12641      +691
taxi_driver                  senior       36000   37800    19750      20830     +1080
taxi_driver (renting cab)    entry        14000   14700     1300       1755      +455
taxi_driver (renting cab)    mid          23000   24150     6750       7441      +691
taxi_driver (renting cab)    senior       36000   37800    14550      15630     +1080

taxi-driver second earner weather-surge month (Unit KC — same EY weather; early-position minbal flat vs surged, net flat vs surged; the measured position dips 0 flat and surged for every pairing and tier):
second earner                tier    early flat early surged net flat net surged
taxi-driver (entry, owning)  entry            0            0    10700      11155
taxi-driver (entry, owning)  mid              0            0    13944      14399
taxi-driver (entry, owning)  senior         -72          -42    17401      17856
taxi-driver (mid, owning)    entry            0            0    16150      16841
taxi-driver (mid, owning)    mid              0            0    19394      20085
taxi-driver (mid, owning)    senior           0            0    22851      23542
taxi-driver (mid, renting)   entry            0            0    10950      11641
taxi-driver (mid, renting)   mid              0            0    14194      14885
taxi-driver (mid, renting)   senior         -56           -9    17651      18342
taxi-driver (entry, renting) entry         -193         -163     5500       5955
taxi-driver (entry, renting) mid           -288         -258     8744       9199
taxi-driver (entry, renting) senior        -419         -389    12201      12656
taxi-driver (senior, owning) entry            0            0    23950      25030
taxi-driver (senior, owning) mid              0            0    27194      28274
taxi-driver (senior, owning) senior           0            0    30651      31731
```

**Honest limit, recorded:** the surge is applied in exactly
one settlement place — the SYS-EMPLOYERS branch of
`engine._settle_month`. A taxi driver employed by a business
is paid by `_pay_business_wages`, which consults
`labour.wage_due_for` (the plain monthly wage, no factor),
so a business-employed taxi driver settles unsurged. The EY
world holds no business-employed taxi driver (all six are
SYS-EMPLOYERS-paid), so that path is a code read, not a
measurement — the tool's rows are the SYS-EMPLOYERS case,
which is the case the world actually produces. Whether
business-employed taxi drivers should surge is a settlement
question, not a tool one, and is recorded open — not queued
as tool work.

Full default-run md5: `f6cec5a23109c4e7f9aeff3f7361e89d` (KA:
`5f50931cbaad263812473ce1c7830e59` — kept in
`test_no_regression.py` as history). The only diff vs KA is
this section; the §9/§11/§12/§14 sections, the bridge lines,
the base table and all other rows are unchanged.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the business-employed taxi driver's
unsurged pay (above) — a settlement question, not a tool
gap; the Shibnagar variant's bridge check still prints
single-earner lines only — Queue 29 Unit KD. *(Both closed
by Queue 30, 2026-11-25: the business-employed case cannot
arise — Unit KF, §19 — and the storm line is wired into the
variant — Unit KE, §18.)*

## 17. Addendum — Two-earner lines in the Shibnagar variant (Unit KD, Queue 29)

**Date:** 2026-11-24. **Method:** re-run the two-earner
households on Shibnagar rents — `simulate(..., rent_override
= rents[SHIBNAGAR_RENT_TIER["construction_worker"]])` — for
every pairing (same-tier, taxi-driver entry, taxi-driver mid,
taxi-driver mid renting, civil-engineer mid, civil-engineer
entry), every first-earner tier and every storm position, and
compare minbal, net and end balance against the District 1
run; then wire the six bridge lines into
`print_shibnagar_variant`'s bridge check, computed on the
variant's own rents rather than quoted from District 1.

**Verified: the figures are identical — 90 two-earner rows,
0 differences.** Shibnagar's tier-1 rent is the prices.json
tier-1 rent (2,500 — asserted by `load_shibnagar_rents`, not
assumed), and the two-earner first earner is always the
construction worker (tier 1), so the identity holds by
construction — and it is verified, not asserted: all 90 rows
(6 pairings × 3 tiers × 4 storm positions, plus the
even-spread rows) agree on minbal, net and end balance, and
the worst dip per pairing agrees too:

| Second earner | Worst dip | Combined start | Bridge line |
|---|---:|---:|---|
| taxi-driver (entry, owning) | −72 | 10,000 | 10,000 − 72 = 9,928 |
| civil-engineer (mid, owning) | −8,623 | 30,000 | 30,000 − 8,623 = 21,377 |
| construction-worker (same tier) | −1,231 | 10,000 | 10,000 − 1,231 = 8,769 |
| taxi-driver (mid, owning) | 0 | 10,000 | 10,000 − 0 = 10,000 |
| civil-engineer (entry, owning) | −3,210 | 30,000 | 30,000 − 3,210 = 26,790 |
| taxi-driver (mid, renting) | −56 | 10,000 | 10,000 − 56 = 9,944 |

The variant's bridge check now prints all six lines, with the
same combined starts and the same worst-dip rule as District
1 — a failing line would join `shibnagar BRIDGE FAIL` (none
fails). No two-earner bridge figure is variant-only any more:
the single-earner lines were already printed by the variant,
and the storm-position line for the single construction
worker is still District 1 only — that line is about the
first earner's own storm dip, not a two-earner household, and
it stays out of this unit's scope.

Verbatim output (the Shibnagar bridge check now):

```
shibnagar first-month bridge check (same starting balances):
  construction_worker    start   5000 + dip       0 =    5000  OK
  construction_worker + taxi-driver    start  10000 + mixed dip     -72 =    9928  OK  (worst mixed storm position)
  construction_worker + civil-engineer start  30000 + mixed dip   -8623 =   21377  OK  (worst mixed storm position)
  construction_worker + construction-worker start  10000 + same-tier dip   -1231 =    8769  OK  (worst same-tier storm position)
  construction_worker + taxi-driver (mid) start  10000 + other-tier dip       0 =   10000  OK  (worst other-tier storm position)
  construction_worker + civil-engineer (entry) start  30000 + other-tier dip   -3210 =   26790  OK  (worst other-tier storm position)
  construction_worker + taxi-driver (mid, renting) start  10000 + renting dip     -56 =    9944  OK  (worst renting storm position)
```

The KC baseline stands: the pinned md5 does not move — the
KD wiring touches only the `--shibnagar` output, and the
default run is byte-identical.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the single-earner storm-position line is
still District 1 only (above) — a small asymmetry, not a
gap in any household figure; the business-employed taxi
driver's unsurged pay (§16) stays a settlement question.
*(Both closed by Queue 30, 2026-11-25: the storm line is
wired into the variant — Unit KE, §18 — and the
business-employed case cannot arise — Unit KF, §19.)*

## 18. Addendum — Storm-position bridge line in the Shibnagar variant (Unit KE, Queue 30)

**Date:** 2026-11-25. **Method:** re-run the single-earner
construction-worker storm rows on Shibnagar rents —
`simulate(..., rent_override = rents[SHIBNAGAR_RENT_TIER
["construction_worker"]])` — for every storm position, and
compare minbal, net and end balance against the District 1
run; then wire the storm line into
`print_shibnagar_variant`'s bridge check, computed on the
variant's own rents rather than quoted from District 1.

**Verified: the figures are identical — every storm
position, 0 differences.** Shibnagar's tier-1 rent is the
prices.json tier-1 rent (2,500 — asserted by
`load_shibnagar_rents`, not assumed), and the storm line is
about the first earner's own dip, so the identity holds by
construction — and it is verified, not asserted: early −500,
mid 0, late 0, measured −100 on both rents, worst −500, so
the line is 5,000 − 500 = 4,500 in both cities.

Verbatim output (the Shibnagar bridge check now):

```
shibnagar first-month bridge check (same starting balances):
  construction_worker    start   5000 + dip       0 =    5000  OK
  construction_worker    start   5000 + storm dip    -500 =    4500  OK  (worst storm position)
  construction_worker + taxi-driver    start  10000 + mixed dip     -72 =    9928  OK  (worst mixed storm position)
  construction_worker + civil-engineer start  30000 + mixed dip   -8623 =   21377  OK  (worst mixed storm position)
  construction_worker + construction-worker start  10000 + same-tier dip   -1231 =    8769  OK  (worst same-tier storm position)
  construction_worker + taxi-driver (mid) start  10000 + other-tier dip       0 =   10000  OK  (worst other-tier storm position)
  construction_worker + civil-engineer (entry) start  30000 + other-tier dip   -3210 =   26790  OK  (worst other-tier storm position)
  construction_worker + taxi-driver (mid, renting) start  10000 + renting dip     -56 =    9944  OK  (worst renting storm position)
```

The KC baseline stands: the pinned md5 does not move — the
KE wiring touches only the `--shibnagar` output, and the
default run is byte-identical.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the storm line sweeps storm positions
at the entry tier only — the two-earner lines sweep the
first earner's tiers, the single-earner storm line does not.
Measured while wiring: the worst single-earner storm dip
across tiers is senior early −726 (mid −595, entry −500),
which against the same 5,000 start leaves 4,274 — still OK,
so no bridge failure is hidden, but the printed line
(5,000 − 500 = 4,500) is the entry row's worst, not the
household's worst across tiers. Whether the line should
sweep tiers like the two-earner lines is a decision for a
later unit (Queue 31 Unit LA).

## 19. Addendum — Business-employed taxi surge (Unit KF, Queue 30)

**Date:** 2026-11-25. **Method:** audit every route by
which a taxi driver could come to be paid by a business —
read every vacancy source, every employment-creation site,
and the job-change path — and measure a live world
(`Simulation`, seed `kf-measure`, `generate_population
(120)`, 90 days) for business-employed taxi drivers and
business wage rows to taxi drivers.

**Measured: the case cannot arise.** No vacancy source ever
posts a taxi driver: business staffing posts chef,
construction_worker and software_developer
(`labour.STAFFING`); civic posts teacher, doctor and
police_officer (`labour.CIVIC_RATIOS`); government posts
police_officer, doctor and civil_engineer
(`admin.STAFFING`); the Session 05 employment programme
posts construction_worker (`policies.py`). Genesis
(`population.py`) and the seek-employment hire
(`decisions._hire`) insert employments with no business
employer, and a job change (`decisions.py`, the vacancy
path) takes the vacancy's profession — so a taxi driver
who changes jobs stops being a taxi driver. The live world
confirms it: 0 taxi vacancies ever posted, 4 taxi drivers
in the world, 0 business-employed, 0 wage rows from a
business to a taxi driver, 12 taxi wage rows in total — all
from SYS-EMPLOYERS; the only vacancy professions ever
posted were civil_engineer, construction_worker and
software_developer.

**DECIDED: no settlement change.** The surge stays
SYS-EMPLOYERS-only, not because the business path was
judged wrong, but because no business-employed taxi driver
can exist for it to apply to: `_pay_business_wages` is
unreachable for taxi_driver, so adding a surge there would
be behaviour for a case the machinery cannot produce. The
§16 question is closed as a measurement, not as a
judgement: if a future staffing change ever posts taxi
driver vacancies, the question re-opens — and a guard test
(`test_economy_labour_banking.py`,
`TestBusinessEmployedTaxiSurge`) fails loudly if it does.

**No tuning call.** Nothing in the data moves, and no sim
code changes — `engine.py` is byte-identical.

**Open, recorded:** none from this unit. The §16 open item
is closed.

## 20. Addendum — Single-earner storm line across tiers (Unit LA, Queue 31)

**Date:** 2026-11-25. **Method:** re-run the single-earner
construction-worker storm rows for every tier (entry, mid,
senior) at every storm position (early, mid, late,
measured), in District 1 and on Shibnagar rents, and decide
whether the storm bridge line should sweep tiers like the
two-earner lines (Unit IA) or stay entry-only (Unit GE).

**Measured: the worst dip is senior early, not entry
early.** Per-tier worst dips across the four positions:

| tier | early | mid | late | measured | worst |
|---|---|---|---|---|---|
| entry | −500 | 0 | 0 | −100 | −500 |
| mid | −595 | 0 | 0 | 0 | −595 |
| senior | −726 | 0 | 0 | 0 | −726 |

The early position is worst at every tier; the deeper
senior dip is Unit V's tier-scaled living costs meeting the
day-wage rule, and the storm position is what exposes it in
month 1. The figures are identical on Shibnagar rents at
every tier — the rent is the tier-1 rent in both cities and
the dip is the first earner's own.

**DECIDED: sweep the tiers.** The bridge check's stated
purpose is the household's worst month-1 balance, and the
entry-only line understated it by 226: it printed the entry
row's worst (5,000 − 500 = 4,500) rather than the
household's worst across tiers. The two-earner lines already
sweep the first earner's tiers (Unit IA), so the
single-earner line was the inconsistent one. The start is
the same 5,000 at every tier (`starting_balance_ncr` is per
profession, not per tier), so the sweep stays one
household's worst. The line is now 5,000 − 726 = 4,274 in
both cities:

```
  construction_worker    start   5000 + storm dip    -726 =    4274  OK  (worst storm position, all tiers)
```

Still OK — no bridge failure was hidden; the correction
is 226 of headroom the check was overstating. The KE §18
figure (5,000 − 500 = 4,500) is superseded by this section:
it was the entry row's worst, correctly measured, and is
now replaced as the printed line.

The pinned md5 moves to `2b9d24f9663f88ad0d13be1f5e86c40c`
(the KC md5 is kept in `test_no_regression.py` as
history): the printed bridge line is part of the default
run, so the sweep changes the default output.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the single-earner renting-cab row's
bridge line is entry-only, like the storm line was — the
renting row itself is modelled at the entry tier alone, so
there is no mid/senior renting row to sweep (Queue 32 Unit
MA).

## 21. Addendum — Renting-cab row at mid/senior tiers (Unit MA, Queue 32)

**Date:** 2026-11-25. **Method:** re-run the single-earner
renting-cab row for every tier (entry, mid, senior) with the
same call the base table uses — `simulate(..., tier,
extra_daily_cost=cab_rental)` — in District 1 and on
Shibnagar rents, and decide whether the rows hold and the
bridge line should sweep tiers like the storm line (Unit
LA) or stay entry-only.

**Measured: the rows hold at every tier.** The rental is
the flat 5,200/month at every tier (200 NCr/day × WORK_DAYS
26, the settlement rule JB confirmed; Unit KA proved the
same flat rental for the second earner), so the tier moves
the pay, not the rental:

| tier | gross | tax | costs | extra | net/mo | save% | minbal | flags |
|---|---|---|---|---|---|---|---|---|
| entry | 14,000 | 0 | 12,700 | 5,200 | 1,300 | 9.3 | 0 | TIGHT |
| mid | 23,000 | 400 | 15,850 | 5,200 | 6,750 | 29.3 | 0 | - |
| senior | 36,000 | 1,050 | 20,400 | 5,200 | 14,550 | 40.4 | 0 | - |

Every row's net is exactly 5,200 below the owning driver
at the same tier (6,500 / 11,950 / 19,750), every
trajectory ends exactly at net, and minbal is 0 at every
tier — so no bridge failure is hidden at any tier, and only
the entry row is TIGHT (9.3%), as before. The figures are
identical on Shibnagar rents at every tier — the taxi rent
tier is unchanged in Shibnagar, so the variant's rows match
District 1 exactly (rent 2,500 → 2,500, net +0 at every
tier).

**DECIDED: wire the rows and sweep the line.** The base
table gains the mid and senior renting rows beside the entry
one (36 rows, was 34), in District 1 and in the Shibnagar
variant, and the bridge check's renting line now sweeps tiers
like the storm line (Unit LA): the worst minbal across the
three renting rows against the same 5,000 start. The line is
5,000 + 0 = 5,000 OK in both cities:

```
  taxi_driver (renting cab) start   5000 + dip       0 =    5000  OK  (worst renting tier)
```

Unchanged in figure — the entry-only line already printed
5,000 + 0 = 5,000 — but now honestly the household's worst
across tiers rather than the entry row's, so a future tier
that dips would show up in the check instead of hiding
behind the entry row. The storm line is untouched (5,000 −
726 = 4,274, §20).

The pinned md5 moves to `bc9a35e1c95d4b8a512c0a4a6e0994cd`
(the LA md5 is kept in `test_no_regression.py` as
history): the two new base-table rows and the swept line are
part of the default run.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the KC surge section still prints the
entry renting row only — the surge deltas at mid/senior are
already measured in §16 prose (single-earner nets rise +455
/ +691 / +1,080; the rental stays the flat 5,200 unsurged,
so the renting rows rise by exactly the same deltas —
measured: mid 6,750 → 7,441, senior 14,550 → 15,630), but
the section's printed table does not show them (Queue 33
Unit MB); the renting senior-tier taxi second earner stays
unmeasured — no measured household pairs the construction
worker with a senior taxi driver, so it stays unmodelled
rather than assumed (§14); the senior taxi driver (36,000)
and senior civil engineer (65,000) as second earner stay
unmodelled for the same reason (§12).

*(Closed 2026-11-25 by Queue 33 Unit MB — the KC surge
section now prints the renting row at every tier; §22. The
other two items stay open.)*

## 22. Addendum — Renting rows in the surge section (Unit MB, Queue 33)

**Date:** 2026-11-25. **Method:** re-run the single-earner
renting-cab row for every tier (entry, mid, senior) with the
same call the surge section uses — `simulate(..., tier,
extra_daily_cost=cab_rental, taxi_rain_days=...,
taxi_storm_days=...)` — and decide whether the mid/senior
rows belong in the KC section's printed table or entry-only
is the right statement for that section.

**Measured: the rows hold at every tier, with exactly the
owning driver's deltas.** The rental stays the flat 5,200
unsurged, so the surge lifts the gross and nothing else
moves:

| tier | Flat gross | Surged gross | Flat net | Surged net | Delta |
|---|---:|---:|---:|---:|---:|
| entry (renting cab) | 14,000 | 14,700 | 1,300 | 1,755 | +455 |
| mid (renting cab) | 23,000 | 24,150 | 6,750 | 7,441 | +691 |
| senior (renting cab) | 36,000 | 37,800 | 14,550 | 15,630 | +1,080 |

Every surged net is exactly 5,200 below the owning
driver's surged net at the same tier (6,955 / 12,641 /
20,830), every trajectory ends exactly at net flat and
surged, and minbal is 0 flat and surged at every tier — so
the surge adds no dip the flat rows hide, and no bridge
line is affected (the check stays flat: the factor is ≥ 1,
so the flat lines are the conservative case).

**DECIDED: wire the rows.** The KC section's first table
now prints the renting row at every tier beside the owning
rows, in the same columns — the section no longer
understates the renting household the way the entry-only
base table once did (§21). The verbatim output in §16
gains the two rows. The second-earner surge table is
untouched: its renting row is the two-earner household
(mid-tier taxi second earner), and the renting senior-tier
taxi second earner stays unmeasured (§14) — not queued.

The pinned md5 moves to `4abf52ff0dc7d00f6acd3168d7c1c807`
(the MA md5 is kept in `test_no_regression.py` as
history): the two new printed rows are part of the default
run.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the second-earner surge table still
prints only three pairings — the entry renting second
earner (Unit IB: early dips −193 / −288 / −419, nets 5,500
/ 8,744 / 12,201) is measured but not shown there, so the
surge's effect on its dips is unprinted — Queue 34 Unit MC. *(Closed 2026-11-25 by Queue 34 Unit MC — §23.)* The renting senior-tier taxi second earner stays
unmeasured — no measured household pairs the construction
worker with a senior taxi driver, so it stays unmodelled
rather than assumed (§14); the senior taxi driver (36,000)
and senior civil engineer (65,000) as second earner stay
unmodelled for the same reason (§12).

## 23. Addendum — Entry renting second earner in the surge table (Unit MC, Queue 34)

**Date:** 2026-11-25. **Method:** re-run the entry renting
taxi-driver second earner (Unit IB) at every tier with the
same calls the KC second-earner surge table uses —
`simulate(..., second_earner="taxi_driver",
second_earner_renting_cab=True, storm_days=STORM_EARLY_DAYS,
taxi_rain_days=..., taxi_storm_days=...)` — and decide
whether the pairing belongs in the table or the
three-pairing table is the right statement.

**Measured: the pairing holds at every tier, with exactly
the entry taxi surge.** The second earner's gross is the
entry band (14,000 → 14,700), the rental stays the flat
5,200 unsurged, so the nets rise +455 at every tier:

| First-earner tier | Early flat | Early surged | Net flat | Net surged |
|---|---:|---:|---:|---:|
| entry | −193 | −163 | 5,500 | 5,955 |
| mid | −288 | −258 | 8,744 | 9,199 |
| senior | −419 | −389 | 12,201 | 12,656 |

The surge shrinks all three early dips but closes none —
the same shape as the HD senior dip (−72 → −42) and the KA
renting senior dip (−56 → −9), which the table already
prints. The measured position dips 0 flat and surged, and
every trajectory ends exactly at net flat and surged — so
the surge adds no dip the flat rows hide, and no bridge
line is affected (the check stays flat: the factor is ≥ 1,
so the flat lines are the conservative case).

**DECIDED: wire the pairing.** The KC second-earner surge
table now prints the (entry, renting) pairing at every
tier beside the other three — the table no longer omits the
one measured pairing whose surge effect was prose-only
(§11). The verbatim output in §16 gains the three rows,
and the §16 Finding now reads three early dips, not two.
The table now has four pairings; the MB "untouched" test
is superseded by a four-pairings test.

The pinned md5 moves to `a818a3273cdad108c4d8d4ae198b5b44`
(the MB md5 is kept in `test_no_regression.py` as
history): the three new printed rows are part of the
default run.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the renting senior-tier taxi second
earner stays unmeasured — no measured household pairs the
construction worker with a senior taxi driver, so it stays
unmodelled rather than assumed (§14); the senior taxi
driver (36,000) and senior civil engineer (65,000) as
second earner stay unmodelled for the same reason (§12).
The surge section is District 1 only in the printed run —
the `--shibnagar` variant prints the D1 section, not its
own surge table; measured live while drafting, all four
pairings × three tiers × four storm positions, surged, are
identical on Shibnagar rents (the construction worker's
Shibnagar rent is the tier-1 rent, 2,500, the same as
District 1) — Queue 35 Unit MD. (Closed 2026-11-25 by
Queue 35 Unit MD — §24.)

## 24. Addendum — Surge section in the Shibnagar variant (Unit MD, Queue 35)

**Date:** 2026-11-25. **Method:** re-run every surged row
on Shibnagar rents — `simulate(..., rent_override =
rents[SHIBNAGAR_RENT_TIER[...]])` — for the single-earner
owning and renting rows at every tier (flat and surged) and
the second-earner table (all four pairings × three tiers ×
four storm positions, flat and surged), and compare minbal,
net and end balance against District 1.

**Measured: all 108 rows identical.** 12 single-earner rows
(owning + renting × 3 tiers × flat/surged) and 96
second-earner rows (4 pairings × 3 tiers × 4 positions ×
flat/surged) agree on minbal, net and end balance. The
reason is the same as KD's (§17): the surge rows rent at
tier 1 (the taxi driver and the construction worker both),
and Shibnagar's tier-1 rent is the prices.json tier-1 rent
(2,500 — asserted by `load_shibnagar_rents`, not assumed).
The non-zero early dips are the same ones the District 1
table prints:

| Second earner | First-earner tier | Early flat | Early surged | Net flat | Net surged |
|---|---|---:|---:|---:|---:|
| entry, owning | senior | −72 | −42 | 17,401 | 17,856 |
| mid, renting | senior | −56 | −9 | 17,651 | 18,342 |
| entry, renting | entry | −193 | −163 | 5,500 | 5,955 |
| entry, renting | mid | −288 | −258 | 8,744 | 9,199 |
| entry, renting | senior | −419 | −389 | 12,201 | 12,656 |

and the single-earner deltas are the same +455 / +691 /
+1,080 (the renting rows rise by the same deltas as the
owning rows, the rental staying the flat 5,200 unsurged).
Every other second-earner early dip is 0 flat and surged,
and every trajectory ends exactly at net flat and surged —
so the surge adds no dip the flat rows hide, and no bridge
line is affected (the check stays flat: the factor is ≥ 1,
so the flat lines are the conservative case).

**DECIDED: wire the variant's own table.** The KC section
is now a function, `print_taxi_weather_surge(prices, bands,
variant=..., rent_overrides=...)`: the default run calls it
with no overrides (`rent_override=None` is the District 1
rent, so its output is byte-identical), and the
`--shibnagar` variant calls it after its bridge check with
the town's own rents (taxi 2,500, construction worker
2,500). The variant's table is computed on its own rents,
not quoted from the District 1 run — the run still prints
the D1 section first, then the variant's table, the same
way it prints both bridge checks. The §16 figures stand for
both cities; the variant's table is a second printing, not
a second set of figures.

Verbatim output (new `--shibnagar` section):

```
shibnagar taxi weather-surge month (Unit MD — the same KC section on Shibnagar's own rents: 2 rain days, 2 storm days, taxi_factor 1.05; taxi gross x 1.05, tax and uplift recomputed on the surged gross):
profession                   tier    flat gross  surged flat net surged net delta net
taxi_driver                  entry        14000   14700     6500       6955      +455
taxi_driver                  mid          23000   24150    11950      12641      +691
taxi_driver                  senior       36000   37800    19750      20830     +1080
taxi_driver (renting cab)    entry        14000   14700     1300       1755      +455
taxi_driver (renting cab)    mid          23000   24150     6750       7441      +691
taxi_driver (renting cab)    senior       36000   37800    14550      15630     +1080

shibnagar taxi-driver second earner weather-surge month (Unit MD — same EY weather, on Shibnagar rents; early-position minbal flat vs surged, net flat vs surged; the measured position dips 0 flat and surged for every pairing and tier):
second earner                tier    early flat early surged net flat net surged
taxi-driver (entry, owning)  entry            0            0    10700      11155
taxi-driver (entry, owning)  mid              0            0    13944      14399
taxi-driver (entry, owning)  senior         -72          -42    17401      17856
taxi-driver (mid, owning)    entry            0            0    16150      16841
taxi-driver (mid, owning)    mid              0            0    19394      20085
taxi-driver (mid, owning)    senior           0            0    22851      23542
taxi-driver (mid, renting)   entry            0            0    10950      11641
taxi-driver (mid, renting)   mid              0            0    14194      14885
taxi-driver (mid, renting)   senior         -56           -9    17651      18342
taxi-driver (entry, renting) entry         -193         -163     5500       5955
taxi-driver (entry, renting) mid           -288         -258     8744       9199
taxi-driver (entry, renting) senior        -419         -389    12201      12656
```

The pinned md5 does NOT move — the MC baseline
`a818a3273cdad108c4d8d4ae198b5b44` stands (the wiring
touches only the `--shibnagar` output, and the default run
is byte-identical). The `--shibnagar` full-output md5 is now
`762a2b6395a1c83fc86f2b5f9c1839bc` (was
`2aaf1c4786292fcc405bdc9f5925982b`); two consecutive
`--shibnagar` runs are byte-identical.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the renting senior-tier taxi second
earner stays unmeasured — no measured household pairs the
construction worker with a senior taxi driver, so it stays
unmodelled rather than assumed (§14); the senior taxi
driver (36,000) and senior civil engineer (65,000) as
second earner stay unmodelled for the same reason (§12).
Whether the renting senior-tier second earner belongs in
the tool at all — measured, kept refused, or kept
allowed-but-unmeasured — is Queue 36 Unit ME. (Closed
2026-11-25 by Queue 36 Unit ME — §25.)

## 25. Addendum — Renting senior-tier taxi second earner: belongs in the tool? (Unit ME, Queue 36)

**Date:** 2026-11-25. **Method:** decide whether the
renting senior-tier taxi second earner
(`simulate(..., second_earner="taxi_driver",
second_earner_tier="senior",
second_earner_renting_cab=True)`) belongs in the tool at
all — measure it on the KA pattern, keep it refused with
a stated reason, or keep it allowed-but-unmeasured with a
stated reason — and wire the surge-table row + bridge line
only if the decision says so. No invented household, no
tuning call.

**DECIDED: keep allowed-but-unmeasured.** The combination
stays computable — `simulate()` raises nothing for it, the
senior wage (36,000) is `prices.json` `wages_monthly` and
the rental is the settlement's flat 5,200/month (200 ×
WORK_DAYS 26) — but the default run prints no row for it,
the KC second-earner surge table keeps its four pairings,
and neither bridge check wires a line for it. Three
reasons, in order:

1. The §12 standing rule: no measured household pairs the
construction worker with a senior taxi driver, so the
senior second earner stays unmodelled rather than assumed.
The renting variant is the same household at the same tier
— measuring it alone would overturn the rule for one
variant only, while the owning senior pairing it compares
against stays unmodelled.
2. The table's own structure: every renting row sits beside
its owning row — the single-earner renting rows beside the
owning rows (MB), the entry renting second earner beside
the entry owning second earner (MC), the renting mid-tier
second earner beside the owning mid-tier one in §14's
table (KA). A renting-senior row with no owning-senior row
would dangle — and its net would publish the owning senior
net by implication (net + 5,200), smuggling §12's
unmodelled pairing in through the back door.
3. It would add no finding: a live check while deciding
(three first-earner tiers × four storm positions, flat and
surged) found the senior taxi pay covers the cost-only days
at every tier — the early dip is 0 everywhere, the
measured position dips 0, every trajectory ends exactly at
net, and the net is exactly 5,200 below the owning senior
driver at every tier — so the bridge line would be the
trivial 10,000 + 0 = 10,000. A row of zeros says nothing
the owning pattern plus the flat rental does not already
say.

No refusal is invented either: refusing the combination
would add a restriction the data does not support — the
wage and the rental are both sourced, and the tool's tier
parameter already spans entry/mid/senior for the mixed
second earner (IC). The boundary is therefore exactly:
computable, not printed, not wired — pinned by the ME
tests, which fail loudly if a later run prints the row or
wires the line without revisiting this decision.

The pinned md5 does NOT move — the MC baseline
`a818a3273cdad108c4d8d4ae198b5b44` stands (the change is a
comment only; the default run is byte-identical). The
`--shibnagar` full-output md5 does NOT move either —
`762a2b6395a1c83fc86f2b5f9c1839bc` stands.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the decision re-opens only if a
measured household appears — a live settlement household
pairing the construction worker with a senior taxi driver
(or a senior civil engineer) as second earner (Queue 37
Unit MF); until then the §12 rule stands and the senior
second earners stay unmodelled. (Checked 2026-11-25 by
Queue 37 Unit MF — no measured household appears in the
mf-measure world; see §26.)

## 26. Addendum — Senior second earner live-world check (Unit MF, Queue 37)

**Date:** 2026-11-25. **Method:** run the ME reopen check
against live households, not the tool's parameter space —
a seeded live world (seed `mf-measure`, 120 population, 90
days, the KF pattern) and count households pairing a
construction-worker head with a senior taxi driver (36,000)
or senior civil engineer (65,000) second earner. If none
appears, re-confirm the §12 rule stands and close with no
change (measurement only, like KF); if one appears, measure
it on the KA/IC pattern and wire the row + bridge line only
for the pairing that actually appears. No invented
household, no tuning call.

**DECIDED: no change — the §12 rule stands.** No measured
household appears:

- 0 senior taxi-driver second earners in
  construction-worker-headed households.
- 0 senior civil-engineer second earners in
  construction-worker-headed households.

The world, so the zeros are measured absences and not an
empty query: 55 households, 4 construction-worker-headed,
2 of those with a second earner — HH000043 (a mid-tier
construction worker, 14,000) and HH000054 (a mid-tier
police officer, 28,000) — so the pairing query finds real
second earners, just none senior in either profession. The
world holds 8 taxi drivers (1 entry, 6 mid, 1 senior-band)
and 7 civil engineers (1 entry, 6 mid, 0 senior-band).

**The one senior-band driver is a head, not a second
earner.** The world's single senior-band taxi driver is
NEX000032 (tier 4, 36,000), head of HH000017 — so even the
one senior taxi wage in the world sits on the wrong side of
the pairing. And no senior-band civil engineer exists in
the world at all.

**"Senior" in the live world means tier >= 3, not
tier == 3.** `tools/sim/dataio.py` `TIER_WAGE_KEYS` maps
tiers 3–5 to the senior band (`("entry", "mid", "senior",
"senior", "senior")`), so a tier-4 driver earns the senior
wage — a naive `tier == 3` check would have missed the
world's only senior-band taxi driver entirely. The
measurement counts tier >= 3, i.e. wage == the senior band
(36,000 / 65,000 from `prices.json` `wages_monthly`).

The pinned md5 does NOT move — the MC baseline
`a818a3273cdad108c4d8d4ae198b5b44` stands (the change is a
comment only; the default run is byte-identical). The
`--shibnagar` full-output md5 does NOT move either —
`762a2b6395a1c83fc86f2b5f9c1839bc` stands.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** this is one seeded world, and senior
second earners are rare in it precisely because senior-tier
citizens are rare in it — one senior-band taxi driver and
zero senior-band civil engineers in 120 people. Whether the
absence holds across seeds is a broader-base question, not
a reason to model the pairing now (Queue 38 Unit MG).

## 27. Addendum — Multi-seed senior second earner sweep (Unit MG, Queue 38)

**Date:** 2026-11-25. **Method:** run the MF check across
five seeds instead of one — the same pairing query (senior
= tier >= 3), the same KF pattern per seed (120 population,
90 days), seeds `mg-seed-1` … `mg-seed-5`. If a pairing
appears in any seed, measure it on the KA/IC pattern and
wire the row + bridge line only for the pairing that
actually appears; if none appears in any, the §12 rule
stands on a broader base. No invented household, no tuning
call.

**DECIDED: no change — the §12 rule stands on a broader
base.** No measured household appears in any of the five
seeds:

| seed | households | construction-worker-headed | second earners in those households | senior-band taxi drivers | senior-band civil engineers | target taxi | target CE |
|---|---|---|---|---|---|---|---|
| mg-seed-1 | 51 | 6 | HH000014 software developer (mid, 52,000); HH000043 shop owner (senior, 55,000) | 1 | 2 | 0 | 0 |
| mg-seed-2 | 42 | 4 | HH000012 software developer (mid, 52,000); HH000032 business owner (mid, 110,000); HH000035 construction worker (senior, 20,000) | 1 | 2 | 0 | 0 |
| mg-seed-3 | 45 | 3 | HH000002 pilot (mid, 95,000) + pilot (entry, 45,000); HH000020 software developer (mid, 52,000); HH000033 software developer (mid, 52,000) | 2 | 2 | 0 | 0 |
| mg-seed-4 | 48 | 6 | HH000002 business owner (senior, 300,000); HH000018 police officer (mid, 28,000) + pilot (entry, 45,000); HH000027 police officer (mid, 28,000); HH000036 taxi driver (mid, 23,000) | 2 | 2 | 0 | 0 |
| mg-seed-5 | 48 | 8 | HH000014 pilot (mid, 95,000); HH000025 doctor (mid, 55,000); HH000031 teacher (mid, 24,000); HH000035 business owner (senior, 300,000); HH000040 software developer (mid, 52,000); HH000043 pilot (mid, 95,000) | 0 | 2 | 0 | 0 |

Totals across the five seeds: 234 households, 27
construction-worker-headed, 20 second earners found in
those households, 6 senior-band taxi drivers and 10
senior-band civil engineers in the five worlds — and 0
senior taxi-driver second earners and 0 senior
civil-engineer second earners in construction-worker-headed
households in every seed.

**The zeros are specific to the two target professions,
not a world with no senior second earners at all.**
Senior second earners do occur in these worlds — a tier-3
shop owner (55,000, the senior band) in mg-seed-1, and a
tier-3 business owner (300,000) in each of mg-seed-4 and
mg-seed-5 — and the query finds the measured pairings too
(a mid-tier taxi driver second earner in mg-seed-4, a
tier-3 construction worker second earner in mg-seed-2).
The pairing query is not vacuous; the two target
professions simply never sit on the second-earner side of
a construction-worker-headed household. The MF world's
single senior-band taxi driver being a head, not a second
earner, is the same shape at a larger scale: the senior
wages exist in the worlds, they just do not pair that way.

The pinned md5 does NOT move — the MC baseline
`a818a3273cdad108c4d8d4ae198b5b44` stands (the change is a
comment only; the default run is byte-identical). The
`--shibnagar` full-output md5 does NOT move either —
`762a2b6395a1c83fc86f2b5f9c1839bc` stands.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** 90 days may be too short for a senior
earner to join a household after genesis — a member hired
or promoted to the senior band after day 90, or a marriage
bringing a senior earner in — and 120 people is still a
small world. Whether the absence holds over a longer
horizon is the next check (Queue 39 Unit MH).

## 28. Addendum — Senior second earner at a longer horizon (Unit MH, Queue 39)

**Date:** 2026-11-25. **Method:** run the MF check over a
longer horizon instead of more seeds — the same pairing
query (senior = tier >= 3), the same KF pattern per seed
(120 population, 365 days), seeds `mh-seed-1` and
`mh-seed-2`. If a pairing appears in any seed, measure it
on the KA/IC pattern and wire the row + bridge line only
for the pairing that actually appears; if none appears in
any, the §12 rule stands over the longer horizon too. No
invented household, no tuning call.

**DECIDED: no change — the §12 rule stands over the longer
horizon too.** No measured household appears in either of
the two year-long worlds:

| seed | households | construction-worker-headed | second earners in those households | senior-band taxi drivers | senior-band civil engineers | target taxi | target CE |
|---|---|---|---|---|---|---|---|
| mh-seed-1 | 50 | 3 | HH000014 teacher (senior, 38,000) + pilot (entry, 45,000); HH000030 shop owner (senior, 55,000) | 4 | 3 | 0 | 0 |
| mh-seed-2 | 46 | 3 | HH000003 police officer (senior, 45,000); HH000022 software developer (mid, 52,000); HH000027 chef (senior, 40,000) | 4 | 4 | 0 | 0 |

Totals across the two seeds: 96 households, 6
construction-worker-headed, 6 second earners found in
those households, 8 senior-band taxi drivers and 7
senior-band civil engineers in the two worlds — and 0
senior taxi-driver second earners and 0 senior
civil-engineer second earners in construction-worker-headed
households in either seed.

**The longer horizon does grow the senior bands, and the
zeros are still specific to the two target professions.**
At 90 days the MG worlds held 0–2 senior-band taxi
drivers and 2 senior-band civil engineers each; at 365
days each world holds 4 senior-band taxi drivers and 3–4
senior-band civil engineers — a full year of hiring and
promotion does put more senior earners in the world, so
the continued zeros are not a world with no senior
earners to pair. Senior second earners in other
professions do occur in these worlds — a tier-3 teacher
(38,000), a tier-5 shop owner (55,000), a tier-4 police
officer (45,000), a tier-3 chef (40,000) — and the query
finds the measured pairings too (a mid-tier software
developer second earner in mh-seed-2). The pairing query
is not vacuous; the two target professions simply never
sit on the second-earner side of a construction-worker-
headed household, even given a year for a member to be
hired or promoted into the senior band or a marriage to
bring one in.

The pinned md5 does NOT move — the MC baseline
`a818a3273cdad108c4d8d4ae198b5b44` stands (the change is a
comment only; the default run is byte-identical). The
`--shibnagar` full-output md5 does NOT move either —
`762a2b6395a1c83fc86f2b5f9c1839bc` stands.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** 120 people is still a small world —
the absence now stands across one world (MF), five seeds
at 90 days (MG) and two seeds at 365 days (MH), but all
at 120 population. Whether it holds in a larger world is
the next check (Queue 40 Unit MI).

## 29. Addendum — Senior second earner in a larger world (Unit MI, Queue 40)

**Date:** 2026-11-25. **Method:** run the MF check in a larger
world instead of more seeds or a longer horizon — the same
pairing query (senior = tier >= 3), the same KF pattern per
seed (300 population, 365 days), seed `mi-seed-1`. If a
pairing appears, measure it on the KA/IC pattern and wire the
row + bridge line only for the pairing that actually appears;
if none appears, the §12 rule stands in a larger world too.
No invented household, no tuning call.

**DECIDED: wire the senior civil-engineer pairing — the §12
rule breaks for it in the larger world, and stands only for
the senior taxi driver.** The larger world holds a measured
household pairing a construction-worker head with a senior
civil-engineer second earner:

| seed | households | construction-worker-headed | second earners in those households | senior-band taxi drivers | senior-band civil engineers | target taxi | target CE |
|---|---|---|---|---|---|---|---|
| mi-seed-1 | 123 | 9 | HH000039 civil engineer (mid, 38,000); HH000079 software developer (senior, 90,000); HH000086 civil engineer (senior, 65,000); HH000100 shop owner (senior, 55,000); HH000107 pilot (senior, 180,000) | 9 | 20 | 0 | 1 |

The one target household is HH000086: head Omar Sheikh
(NEX000214), construction worker, tier 4, 20,000/month; second
earner Liton Tripura (NEX000215), civil engineer, tier 5,
65,000/month; two children, no other earner. Totals: 123
households, 9 construction-worker-headed, 5 second earners
found in those households, 9 senior-band taxi drivers and 20
senior-band civil engineers in the world — and 1 senior
civil-engineer second earner and 0 senior taxi-driver second
earners in construction-worker-headed households. The pairing is
not a query artifact — the same world holds 4 senior
civil-engineer second earners in *any* household (HH000080
tier 4, HH000086 tier 5, HH000091 tier 5, HH000109 tier 5),
so the profession does sit on the second-earner side; only
one of the four sits under a construction-worker head. The
senior taxi driver still never does: 9 senior-band taxi
drivers in the world (tiers 3–5, all at the senior 36,000)
and 0 senior taxi-driver second earners in
construction-worker-headed households.

**Wired on the KA/IC pattern.** The IC section gains the
senior civil-engineer rows (first earner at entry/mid/senior,
all four storm positions): early −17,758 / −14,634 / −11,305,
mid the same, late −17,458 / −14,167 / −10,645, measured the
same as early, even-spread −17,738 / −14,602 / −11,261, nets
42,900 / 46,144 / 49,601 — every trajectory ends exactly at
net. Both bridge checks gain the line 30,000 − 17,758 =
12,242 (combined canonical start 5,000 + 25,000, worst minbal
the entry tier at the early position), OK in both cities, and
identical in both cities (the two-earner rows rent at tier 1,
and Shibnagar's tier-1 rent is the prices.json tier-1 rent,
2,500 — the MD identity).

**The senior second earner deepens the month-1 dip despite
the higher pay.** The mid-tier pairing dips −8,623 at the
entry tier; the senior pairing dips −17,758. The mechanism is
the tool's own: the senior monthly lump (65,000) lands on day
30 while the senior lifestyle uplift (15,050, against 5,600
at the mid tier) accrues daily — the household burns more
every day for 29 days before the pay arrives. The net is
higher (42,900 against 27,950), the trough is deeper. The dip
is nearly position-independent (early = mid = measured at
every tier; only late is shallower), like the mid-tier
pairing — the storm position moves the first earner's pay,
not the second earner's lump.

**The senior taxi-driver second earner stays unprinted.**
No measured household pairs the construction worker with one,
in the larger world either — so no row is wired for it, no
bridge line, and the renting senior-tier taxi second earner
stays allowed but unprinted with it (the ME decision is
unchanged: its owning senior row is still unmodelled, and
the renting row would still dangle).

The pinned md5 MOVES — the MI baseline is
`3d3fce982a64634a0b03bb0af3643f94` (the MC baseline
`a818a3273cdad108c4d8d4ae198b5b44` is kept as history in
`test_no_regression.py`). The `--shibnagar` full-output md5
MOVES too — `17bc7165d1e6ad48de4123e38e426bd7` (was
`762a2b6395a1c83fc86f2b5f9c1839bc`, kept as history here) —
because the variant's bridge check gains the same line.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the senior taxi-driver absence now stands
across one world (MF), five seeds at 90 days (MG), two seeds
at 365 days (MH) and one larger world (MI) — nine worlds, 0
targets — but the larger world shows senior civil engineers
do sit on the second-earner side in other households (4 of
them), so the taxi half of §12 may be about the
construction-worker pairing rather than about senior taxi
drivers never being second earners at all. Whether a senior
taxi driver is a second earner in *any* household is the
next check (Queue 41 Unit MJ).

## 30. Addendum — Senior taxi driver as second earner in any household (Unit MJ, Queue 41)

**Date:** 2026-11-25. **Method:** run the MF pairing query
without the construction-worker-head restriction (senior =
tier >= 3) on the larger worlds — the mi-seed-1 world
re-run plus one fresh seed, mj-seed-2, both 300 population,
365 days. If one appears under a non-construction-worker
head, the absence is specific to the pairing — record it
and stop (no wiring: the tool models the
construction-worker household only). If one appears under
a construction-worker head, measure it on the KA/IC
pattern and wire the row + bridge line exactly as MI did
for the civil engineer. If none appears in any household
in either world, the §12 taxi half stands in the stronger
form: senior taxi drivers never sit on the second-earner
side at all. No invented household, no tuning call.

**DECIDED: record it and stop — the absence is specific to
the construction-worker pairing.** Senior taxi drivers DO
sit on the second-earner side, in both worlds:

| seed | households | senior-band taxi drivers | senior taxi second earners in any household | senior CE second earners in any household | second earners in any household | under a construction-worker head |
|---|---|---|---|---|---|---|
| mi-seed-1 | 123 | 9 | 6 — HH000003 shop owner (tier 5) / Ayesha Biswas (taxi tier 5, 36,000); HH000007 pilot (tier 1) / Pranto Molla (tier 5); HH000054 software developer (tier 5) / Sakib Ghosh (tier 5); HH000061 teacher (tier 2) / Tamim Sarkar (tier 4); HH000063 pilot (tier 2) / Salma Das (tier 4); HH000096 civil engineer (tier 5) / Mitu Uddin (tier 5) | 4 | 62 | 0 |
| mj-seed-2 | 123 | 10 | 5 — HH000027 doctor (tier 5) / Shakib Howlader (taxi tier 5, 36,000); HH000089 taxi driver (tier 5) / Rafid Biswas (tier 5); HH000092 teacher (tier 4) / Nusrat Mir (tier 5); HH000100 shop owner (tier 5) / Fahim Molla (tier 5); HH000105 business owner (tier 4) / Sharmin Sarkar (tier 4) | 4 | 62 | 0 |

Totals: 246 households, 19 senior-band taxi drivers, 11
senior taxi-driver second earners in any household, 8
senior civil-engineer second earners in any household,
124 second earners in any household — and 0 senior
taxi-driver second earners under a construction-worker
head in either world. The heads are spread across eight
professions (doctor, teacher, shop owner, business
owner, pilot, software developer, civil engineer, taxi
driver) and every tier from 1 to 5, so the finding is not
a one-profession or one-tier artifact: a senior taxi
driver can be the second earner under almost any head —
except the construction worker. One household even holds
the reverse of the MI pairing: mi-seed-1 HH000096 pairs a
tier-5 civil-engineer head with a tier-5 taxi-driver
second earner.

**No wiring.** The tool models the construction-worker
household only, and no measured household pairs that
head with a senior taxi driver, so no row is printed, no
bridge line is added, and the renting senior-tier taxi
second earner stays allowed but unprinted with it (the
ME decision is unchanged: its owning senior row is still
unmodelled, and the renting row would still dangle).

**The fresh seed corroborates the MI wiring.** mj-seed-2
holds a second measured instance of the MI pairing —
HH000028 pairs a construction-worker head with a senior
civil-engineer second earner (tier 4, 65,000/month) — so
the senior civil-engineer row the MI unit wired is not a
one-world accident: the pairing recurs in an independent
seed. The re-run of mi-seed-1 reproduces the MI pairing
too (HH000086, tier 5, 65,000), and the MI figures are
unchanged.

The pinned md5 does NOT move — the MI baseline
`3d3fce982a64634a0b03bb0af3643f94` stands. The
`--shibnagar` full-output md5 does NOT move either —
`17bc7165d1e6ad48de4123e38e426bd7` stands — because the
only change is a comment in `economy_sim.py`.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the construction-worker head is now
the only head under which a senior taxi driver never
sits as second earner — eleven counterexamples under
every other kind of head, zero under this one — but the
sweep says nothing about *why*: whether it is the
profession itself, the head's wage band (the
construction worker's 20,000/month at tier 4 sits below
every head in the eleven), or household formation (who
marries or moves in with whom). Whether a senior taxi
driver ever sits under a low-wage head is the next check
(Queue 42 Unit MK).

## 31. Addendum — Senior taxi driver under a low-wage head (Unit MK, Queue 42)

**Date:** 2026-11-26. **Method:** run the MJ any-household
query with the head's current wage joined
(`e.wage_per_month`, the head's current employment wage)
on the same two larger worlds — the mi-seed-1 world
re-run plus mj-seed-2 re-run, both 300 population, 365
days — and count senior taxi-driver second earners under
heads earning <= 25,000/month, and under heads earning
<= 20,000 (the construction-worker tier-4 wage). If one
appears under a <= 20,000 head, the absence is about the
profession, not the wage — record it and stop. If none
appears under any <= 25,000 head, the wage-band
hypothesis stands as the leading explanation — record it
honestly as a hypothesis, not a proof. No wiring either
way: the tool models the construction-worker household
only, and a low-wage non-construction-worker head is
still not that household. No invented household, no
tuning call.

**DECIDED: record it and stop — the strong wage-band
hypothesis is refuted, and the <= 20,000 absence cannot
separate profession from wage.** The re-runs reproduce
MJ exactly (same 6 + 5 households), and the head wages
are now beside them:

| seed | households | senior-band taxi drivers | senior taxi second earners in any household (head wage) | senior CE second earners in any household | second earners in any household | under a construction-worker head |
|---|---|---|---|---|---|---|
| mi-seed-1 | 123 | 9 | 6 — HH000061 teacher (tier 2, **24,000**) / Tamim Sarkar (taxi tier 4, 36,000); HH000007 pilot (tier 1, 45,000) / Pranto Molla (tier 5); HH000003 shop owner (tier 5, 55,000) / Ayesha Biswas (tier 5); HH000096 civil engineer (tier 5, 65,000) / Mitu Uddin (tier 5); HH000054 software developer (tier 5, 90,000) / Sakib Ghosh (tier 5); HH000063 pilot (tier 2, 95,000) / Salma Das (tier 4) | 4 | 62 | 0 |
| mj-seed-2 | 123 | 10 | 5 — HH000089 taxi driver (tier 5, 36,000) / Rafid Biswas (tier 5); HH000092 teacher (tier 4, 38,000) / Nusrat Mir (tier 5); HH000100 shop owner (tier 5, 55,000) / Fahim Molla (tier 5); HH000027 doctor (tier 5, 95,000) / Shakib Howlader (tier 5); HH000105 business owner (tier 4, 300,000) / Sharmin Sarkar (tier 4) | 4 | 62 | 0 |

Totals: 246 households, 19 senior-band taxi drivers, 11
senior taxi-driver second earners in any household — **1
senior taxi-driver second earner under a head earning
<= 25,000** (mi-seed-1 HH000061: teacher head Jamal Begum
at 24,000, the teacher mid band) and **0 senior
taxi-driver second earners under a head earning
<= 20,000** in either world. The single 24,000 case
refutes the wage-band hypothesis in the form MK was
asked to test: a senior taxi driver does sit under a
head earning only 4,000 above the construction-worker
wage, so a wage threshold would have to sit in the
narrow 20,000–24,000 gap with exactly one data point on
the far side.

But the <= 20,000 absence does not settle the question
the other way either. **The two explanations are
confounded at that threshold:** 19 heads earn <= 25,000
across the two worlds (11 in mi-seed-1, 8 in mj-seed-2),
and the lowest head wage in either world is 20,000 — and
**every head earning <= 20,000 is a construction
worker** (17 construction-worker heads in total, 9 +
8). There is no low-wage non-construction-worker head in
either world to break the tie: the one non-construction-
worker head under 25,000 that the data identifies is
the 24,000 teacher, and it holds the pairing. So the
absence under the construction-worker head is equally
consistent with "the profession blocks it" and with "a
wage at or below 20,000 blocks it" — and with chance, on
a base of 17 heads. Neither hypothesis is established;
the honest record is that these two worlds cannot
separate them.

Two structural facts the sweep also establishes. First,
**the construction-worker wage is flat at 20,000 at
every senior tier**: the 17 construction-worker heads are
all at exactly 20,000 — tiers 3, 4 and 5 alike — because
`TIER_WAGE_KEYS` maps tiers 3–5 to the senior band and
the senior band is 20,000, so the wage does not scale
with tier inside the band. Second, **no head in either
world earns an entry wage at all**: entry bands below
20,000 exist (shop owner 12,000, chef 13,000, taxi
driver 14,000, teacher 15,000, police officer 18,000)
but no household head holds one — heads skew to the
higher tiers and bands, which is why the low-wage head
population is so thin (19 of 246 households).

**No wiring.** The tool models the construction-worker
household only, and no measured household pairs that
head with a senior taxi driver, so no row is printed, no
bridge line is added, and the renting senior-tier taxi
second earner stays allowed but unprinted with it (the
ME decision is unchanged: its owning senior row is still
unmodelled, and the renting row would still dangle).

The pinned md5 does NOT move — the MI baseline
`3d3fce982a64634a0b03bb0af3643f94` stands. The
`--shibnagar` full-output md5 does NOT move either —
`17bc7165d1e6ad48de4123e38e426bd7` stands — because the
only change is a comment in `economy_sim.py`.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the profession-vs-wage question
needs a low-wage head who is NOT a construction worker
— a head earning <= 20,000 in another profession, or a
head at an entry wage below 20,000 — and neither world
contains one. Whether such a head exists at all in the
live world, and whether it holds a senior taxi-driver
second earner, is the next check (Queue 43 Unit ML).

## 32. Addendum — Low-wage head who is not a construction worker (Unit ML, Queue 43)

**Date:** 2026-11-26. **Method:** run the MK head-wage
query on five fresh seeds — ml-seed-1..5, 300 population,
365 days each, the MJ/MK world size — and look for any
household head earning <= 20,000 in another profession,
or any head at an entry wage below 20,000 (shop owner
12,000, chef 13,000, taxi driver 14,000, teacher 15,000,
police officer 18,000). If such a head exists and holds a
senior taxi-driver second earner, the profession
explanation is refuted — record it and stop. If such
heads exist but none holds the pairing, the profession
explanation gains support — record it honestly as support,
not proof (small base). If no such head exists in any
seed, record that the live world produces no low-wage
non-construction-worker head at all — the confound is
structural, and the question cannot be settled without a
seeded world, which would be inventing a household — so
stop and record. No wiring either way: the tool models
the construction-worker household only. No invented
household, no tuning call.

**DECIDED: record it and stop — the profession
explanation is refuted, and the §12 taxi half falls.**
The sweep answers the question it was asked, and then
goes past it. A low-wage head who is NOT a construction
worker DOES exist — exactly one in five seeds, ml-seed-1
HH000035, shop-owner head Sabbir Fakir at the entry
12,000 — but he holds no senior taxi-driver second
earner, and on that narrow question alone (a base of one
head) nothing could be concluded either way. What settles
the question is the pairing itself: **a senior
taxi-driver second earner sits under a
construction-worker head in TWO of the five seeds** —
ml-seed-1 HH000030 (head Sohel Howlader, construction
worker tier 5, 20,000; second earner Ishrat Chowdhury,
taxi driver tier 4, 36,000) and ml-seed-3 HH000042 (head
Karim Biswas, construction worker tier 5, 20,000; second
earner Rina Saha, taxi driver tier 5, 36,000). The
profession does not block it, and neither does the wage
band: both pairings sit under a head earning exactly the
construction-worker wage, 20,000. The absence that stood
through MF, MG, MH, MI, MJ and MK — nine worlds, 0
senior taxi-driver second earners under a
construction-worker head — was chance on a thin base, not
a rule: 2 pairings among 44 construction-worker-headed
households in this sweep, against 0 among 17 in the
MJ/MK worlds.

| seed | households | senior-band taxi drivers | senior taxi second earners in any household (head wage) | senior CE second earners in any household | second earners in any household | under a construction-worker head |
|---|---|---|---|---|---|---|
| ml-seed-1 | 123 | 20 | 9 — HH000030 construction worker (tier 5, **20,000**) / Ishrat Chowdhury (taxi tier 4); HH000070 teacher (tier 5, 38,000) / Arif Talukder (tier 5); HH000018 shop owner (tier 5, 55,000) / Mitu Sarkar (tier 5); HH000052 shop owner (tier 3, 55,000) / Tareq Sikder (tier 4); HH000120 civil engineer (tier 4, 65,000) / Mehedi Gazi (tier 5); HH000055 software developer (tier 3, 90,000) / Tanvir Bepari (tier 5); HH000112 software developer (tier 4, 90,000) / Liton Pramanik (tier 5); HH000117 software developer (tier 5, 90,000) / Rony Sarkar (tier 4); HH000088 pilot (tier 2, 95,000) / Rumana Mondal (tier 5) | 6 | 63 | 1 taxi, 1 CE |
| ml-seed-2 | 124 | 7 | 2 — HH000055 pilot (tier 1, 45,000) / Niloy Ahmed (tier 4); HH000080 civil engineer (tier 5, 65,000) / Shahana Kazi (tier 5) | 5 | 63 | 0 |
| ml-seed-3 | 113 | 12 | 5 — HH000042 construction worker (tier 5, **20,000**) / Rina Saha (taxi tier 5); HH000066 taxi driver (tier 5, 36,000) / Sakib Pramanik (tier 4); HH000027 shop owner (tier 4, 55,000) / Niloy Sarkar (tier 4); HH000039 civil engineer (tier 4, 65,000) / Nabila Akter (tier 5); HH000054 pilot (tier 2, 95,000) / Rahad Sardar (tier 5) | 2 | 71 | 1 taxi, 0 CE |
| ml-seed-4 | 113 | 12 | 2 — HH000093 teacher (tier 5, 38,000) / Shakil Pal (tier 5); HH000082 shop owner (tier 5, 55,000) / Mitu Matubbar (tier 5) | 11 | 62 | 0 taxi, 1 CE |
| ml-seed-5 | 129 | 13 | 4 — HH000046 teacher (tier 3, 38,000) / Sumon Molla (tier 5); HH000125 pilot (tier 3, 180,000) / Beauty Marma (tier 5); HH000053 business owner (tier 5, 300,000) / Mizan Rahman (tier 5); HH000110 business owner (tier 4, 300,000) / Anik Rahman (tier 4) | 5 | 74 | 0 taxi, 1 CE |

Totals: 602 households, 64 senior-band taxi drivers, 22
senior taxi-driver second earners in any household, 29
senior civil-engineer second earners in any household,
333 second earners in any household — **2 senior
taxi-driver second earners under a construction-worker
head** (ml-seed-1 HH000030, ml-seed-3 HH000042) and 3
senior civil-engineer second earners under a
construction-worker head (the MI pairing, a third and
fourth and fifth measured instance). The low-wage heads:
**45 heads earn <= 20,000** across the five seeds (10 +
7 + 6 + 11 + 11), of which **44 are construction workers,
all at exactly 20,000** (tiers 3, 4 and 5 — the flat
senior wage again), and **one is not** — ml-seed-1
HH000035, Sabbir Fakir, shop owner tier 1 at the entry
12,000. He is the first head measured at an entry wage
in any world: the lowest head wage is 12,000 in ml-seed-1
and 20,000 in the other four seeds, and only 1 head in
602 earns below 20,000. No senior taxi-driver second
earner sits under a non-construction-worker head earning
<= 20,000 in any seed — but that count is now beside the
point, because the pairing is measured under the
construction-worker head itself.

Two structural facts the sweep also establishes. First,
**the low-wage head population stays thin and
construction-worker-dominated**: 45 of 602 households
(7.5%), 44 of them construction workers — heads still
skew to the higher tiers and bands, which is why the
confound survived as long as it did, and why the earlier
zeros looked like a rule. Second, **the MI pairing
recurs again**: three more construction-worker-headed
households with a senior civil-engineer second earner in
these five seeds, so the senior civil-engineer wiring
(MI) now rests on five measured instances, not one.

**No wiring in this unit.** The ML spec says record it
and stop, and the wiring is a full unit's work: the §12
taxi half now falls, so the senior taxi-driver
second-earner rows are measured-but-unmodelled — exactly
the position the senior civil-engineer rows were in
before MI wired them — and wiring them means measuring
the two pairings on the KA/IC pattern, adding the senior
taxi rows and their bridge lines in both runs, and
re-opening the ME renting decision (the renting row's
owning senior row would then be modelled). That is the
follow-up (Queue 44 Unit MM), not a silent omission.
The renting senior-tier taxi second earner stays allowed
but unprinted with it (the ME decision is unchanged by
this unit).

The pinned md5 does NOT move — the MI baseline
`3d3fce982a64634a0b03bb0af3643f94` stands. The
`--shibnagar` full-output md5 does NOT move either —
`17bc7165d1e6ad48de4123e38e426bd7` stands — because the
only change is a comment in `economy_sim.py`.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the senior taxi-driver second earner
is now a measured pairing of the construction-worker
household and the tool does not model it — wiring it on
the MI pattern is the next check (Queue 44 Unit MM).

## 33. Addendum — Wire the senior taxi-driver second earner (Unit MM, Queue 44)

**Date:** 2026-11-26. **Method:** re-run the two holding
seeds (ml-seed-1 and ml-seed-3, 300 population, 365 days
each) with the ML head-wage/pairing query to confirm both
pairings reproduce, then measure them on the KA/IC pattern
— the senior taxi second earner
(`second_earner="taxi_driver"`,
`second_earner_tier="senior"`) at every head tier
(entry/mid/senior) × every storm position
(early/mid/late/measured) — and wire the rows and their
bridge lines in both runs (default + `--shibnagar`),
exactly as MI did for the senior civil engineer. Re-open
the ME renting decision on ME's own terms (senior wage
36,000, flat 5,200 rental; dip at every tier; bridge line).
No invented household, no tuning call.

**DECIDED: wire the senior taxi-driver second-earner rows
— the §12 taxi half falls with the CE half.** Both
pairings reproduce exactly on re-run — same households,
same heads and second earners, same tiers and wages:

| seed | household | head | second earner |
|---|---|---|---|
| ml-seed-1 | HH000030 | Sohel Howlader, construction worker tier 5, 20,000 | Ishrat Chowdhury, taxi driver tier 4, 36,000 |
| ml-seed-3 | HH000042 | Karim Biswas, construction worker tier 5, 20,000 | Rina Saha, taxi driver tier 5, 36,000 |

**Wired on the KA/IC pattern.** The IC section gains the
senior taxi-driver rows (first earner at entry/mid/senior,
all four storm positions): early, mid, late and measured
all 0 at every tier, even-spread 0, nets 23,950 / 27,194 /
30,651 — every trajectory ends exactly at net. Both bridge
checks gain the line 10,000 + 0 = 10,000 (combined
canonical start 5,000 + 5,000, worst minbal 0 at every
tier and position), OK in both cities, and identical in
both cities (the two-earner rows rent at tier 1, and
Shibnagar's tier-1 rent is the prices.json tier-1 rent,
2,500 — the MD identity).

Senior taxi-driver second earner (36,000, per-fare):

| Tier | Early (1–2) | Mid (15–16) | Late (29–30) | Measured (4, 23) | Even (v6) | Net/mo | Measured-tier early | Measured-tier measured |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| entry | 0 | 0 | 0 | 0 | 0 | 23,950 | 0 | 0 |
| mid | 0 | 0 | 0 | 0 | 0 | 27,194 | 0 | 0 |
| senior | 0 | 0 | 0 | 0 | 0 | 30,651 | −72 | 0 |

Verbatim output (new default-run section):

```
second earner at another tier storm-position month (Unit IC — same 28 worked days of 30; taxi-driver second earner (senior 36,000, per-fare); month-1 minbal by storm position):
profession                   tier      early     mid    late measured    even  (net/mo)  measured-early  measured-measured
construction_worker          entry         0       0       0        0       0  (net 23950)               0                 0
construction_worker          mid           0       0       0        0       0  (net 27194)               0                 0
construction_worker          senior        0       0       0        0       0  (net 30651)             -72                 0
```

**The senior taxi driver does NOT deepen the month-1 dip
— the pay-timing contrast with the senior civil
engineer.** The senior CE pairing dips −17,758 at the
entry tier because the senior monthly lump (65,000) lands
on day 30 while the senior lifestyle uplift (15,050)
accrues daily; the senior taxi driver's per-fare pay
(36,000) lands daily instead, so the household never goes
below its start at any tier or storm position — the early
dip is 0 everywhere, against −17,758 / −14,634 / −11,305
for the senior CE rows. The net is lower (23,950 against
42,900 at entry), the trough is shallower: the higher net
belongs to the monthly lump, and so does the deeper
trough. This extends a known pattern rather than breaking
one — the mid-tier taxi second earner already dipped 0 at
every tier (§12), so per-fare pay at any tier covers the
cost-only days; only the monthly-paid second earners dip.
The storm position moves nothing here (early = mid = late
= measured at every tier), like the mid-tier pairing —
the storm moves the first earner's day-wage pay, not the
second earner's fares.

**The ME renting decision, re-opened and decided.** ME
kept the renting senior-tier taxi second earner allowed
but unprinted for two reasons: (a) the owning senior row
was unmodelled, so a renting row beside it would dangle
and publish the owning senior net by implication; (b) the
row adds no finding (dip 0 everywhere, bridge trivially
10,000 + 0 = 10,000). Reason (a) FALLS now that the
owning senior row is wired — a renting row beside it
would no longer dangle. Reason (b) was re-measured on
ME's own terms (senior wage 36,000, flat 5,200 rental)
and STANDS exactly: the renting senior row dips 0 at all
12 tier × storm-position combinations, its net is exactly
5,200 below the owning senior driver at every tier and
position (18,750 / 21,994 / 25,451 against 23,950 /
27,194 / 30,651), every trajectory ends exactly at net,
and its bridge line would be the trivial
10,000 + 0 = 10,000 — the same line the owning senior row
just wired. Its net is now fully implied by the wired
owning net plus the flat-rental rule (already pinned by
MA/KA/MC), so the row adds nothing new.

**DECIDED: the renting senior-tier taxi second earner
stays allowed but unprinted, now on the no-finding reason
alone.** No row is printed for it in the surge table, no
bridge line is wired for it in either check, and the
`test_senior_renting_second_earner_is_not_printed` test
still passes unchanged. No refusal is invented either —
refusing would add a restriction the data does not
support. The ME comment at the surge-table pairings list
and the ME test class record the re-open.

**The §12 rule now falls in full.** MI broke its CE half
and ML refuted its taxi half; with both pairings now
measured and wired, no part of the §12 absence claim
stands any longer — a senior taxi driver and a senior
civil engineer can both sit on the second-earner side of
a construction-worker-headed household, and the tool
models both. What §12 still says that stands is the
wired figures themselves: the mid-tier taxi second
earner dipping 0, the entry civil engineer dipping
−3,210, and now the senior rows beside them.

The pinned md5 MOVES — the MM baseline is
`47ec8771cc8bca2889d62faa3b23c6e6` (the MI baseline
`3d3fce982a64634a0b03bb0af3643f94` is kept as history in
`test_no_regression.py`). The `--shibnagar` full-output md5
MOVES too — `402b9eb3e286aba1a446c0ae49b8b012` (was
`17bc7165d1e6ad48de4123e38e426bd7`, kept as history here) —
because the variant's bridge check gains the same line.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the KC second-earner surge table still
prints only four pairings — the senior taxi-driver second
earner is now wired in the IC section and both bridge
checks, but the surge's effect on its row is unprinted:
it is per-fare, so its gross DOES surge with the taxi
weather, and its surged early dips and nets are nowhere in
the tool. (The senior civil-engineer row has no such gap —
it is monthly-paid, so the taxi surge cannot move it by
construction.) Measuring and printing the senior taxi
pairing in the surge table is the next check
(Queue 45 Unit MN). (Closed 2026-11-26 by Queue 45 Unit MN
— §34.)

## 34. Addendum — Senior taxi-driver second earner in the surge table (Unit MN, Queue 45)

**Date:** 2026-11-26. **Method:** measure the senior
taxi-driver second earner
(`second_earner="taxi_driver"`,
`second_earner_tier="senior"`) on the KC surge pattern —
every first-earner tier (entry/mid/senior) × every storm
position (early/mid/late/measured), flat vs surged at the
EY month's weather (2 rain days, 2 storm days,
taxi_factor 1.05) — and print its rows in the KC
second-earner surge table, following the MC wiring, in
both runs (default + `--shibnagar`). No invented
household, no tuning call.

**DECIDED: print the senior owning pairing — the table now
has five pairings.** The senior taxi driver is per-fare,
so its gross DOES surge with the taxi weather, and the
surge's effect on its row is now printed:

| Second earner | First-earner tier | Early flat | Early surged | Net flat | Net surged |
|---|---|---:|---:|---:|---:|
| senior, owning | entry | 0 | 0 | 23,950 | 25,030 |
| senior, owning | mid | 0 | 0 | 27,194 | 28,274 |
| senior, owning | senior | 0 | 0 | 30,651 | 31,731 |

The early dip is 0 flat AND surged at every tier and every
storm position — the per-fare senior pay already covers the
cost-only days flat, so there is no dip for the surge to
shrink, unlike the three dips the surge does shrink (the HD
senior dip −72 → −42, the KA renting senior dip −56 → −9,
the IB entry renting dips −193 → −163 / −288 → −258 /
−419 → −389). The nets rise +1,080 at every tier — exactly
the senior single-earner taxi surge delta (the second
earner's gross is the senior band at every first-earner
tier, so the household delta is the senior delta at every
tier, while the single-earner deltas are per-tier +455 /
+691 / +1,080). The measured position dips 0 flat and
surged, and every trajectory ends exactly at net. The
figures are identical in both cities (the two-earner rows
rent at tier 1, and Shibnagar's tier-1 rent is the
prices.json tier-1 rent, 2,500 — the MD identity); the
Shibnagar identity test now covers all 132 rows (12
single-earner + 120 second-earner).

Verbatim output (new second-earner surge rows, both runs):

```
taxi-driver (senior, owning) entry            0            0    23950      25030
taxi-driver (senior, owning) mid              0            0    27194      28274
taxi-driver (senior, owning) senior           0            0    30651      31731
```

**No bridge line is re-wired.** The bridge check stays flat
— the factor is ≥ 1, so the flat lines are the conservative
case, and the senior owning line (10,000 + 0 = 10,000, wired
by MM) already stands. The KA line (10,000 − 56 = 9,944)
is still the worst renting case the tool prints.

The pinned md5 MOVES — the MN baseline is
`c70567cb94bd018ef50df1470fdbe746` (the MM baseline
`47ec8771cc8bca2889d62faa3b23c6e6` is kept as history in
`test_no_regression.py`). The `--shibnagar` full-output md5
MOVES too — `95022a1592dca4d34b91f5f0a6890526` (was
`402b9eb3e286aba1a446c0ae49b8b012`, kept as history here) —
because the variant prints the same new rows.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the renting senior-tier taxi second
earner in the surge table — the (senior, renting) pairing
is the last unprinted pairing in the table. ME decided it
stays allowed but unprinted on the no-finding reason (dip 0
at every tier and position, net exactly 5,200 below the
owning senior driver, bridge trivially 10,000 + 0 =
10,000), and MM re-measured and confirmed it — but that
decision was taken on the flat rows, before the senior
owning row was printed in the surge table. Measuring the
(senior, renting) pairing on the KC surge pattern beside
the now-printed senior owning row, and deciding whether
it is printed or stays unprinted, is the next check
(Queue 46 Unit MO).
(Closed 2026-11-26 by Queue 46 Unit MO — §35.)

## 35. Addendum — Renting senior-tier taxi second earner in the surge table (Unit MO, Queue 46)

**Date:** 2026-11-26. **Method:** measure the renting
senior-tier taxi-driver second earner
(`second_earner="taxi_driver"`,
`second_earner_tier="senior"`,
`second_earner_renting_cab=True`) on the KC surge pattern
beside the now-printed senior owning row — every
first-earner tier (entry/mid/senior) × every storm position
(early/mid/late/measured), flat vs surged at the EY month's
weather (2 rain days, 2 storm days, taxi_factor 1.05) — in
both runs (default + `--shibnagar`, on the variant's own
rents). No invented household, no tuning call.

**DECIDED: stays allowed but unprinted — the surge adds no
finding.** The renting senior pairing dips 0 flat AND
surged at every tier and every storm position, exactly like
the owning senior row beside it:

| Second earner | First-earner tier | Early flat | Early surged | Net flat | Net surged |
|---|---|---:|---:|---:|---:|
| senior, renting | entry | 0 | 0 | 18,750 | 19,830 |
| senior, renting | mid | 0 | 0 | 21,994 | 23,074 |
| senior, renting | senior | 0 | 0 | 25,451 | 26,531 |

The nets rise +1,080 at every tier — exactly the senior
single-earner taxi surge delta, the same delta the owning
senior row rises by — and every net sits exactly 5,200
below the owning surged net at the same tier (25,030 −
5,200 = 19,830; 28,274 − 5,200 = 23,074; 31,731 − 5,200 =
26,531), because the rental stays the flat 5,200 unsurged.
Every trajectory ends exactly at net, and the figures are
identical in both cities (the two-earner rows rent at tier
1, and Shibnagar's tier-1 rent is the prices.json tier-1
rent, 2,500 — the MD identity). The surge changes nothing
the flat rows hide: the renting row's surged figures are
fully implied by the printed owning row plus the flat
5,200 rental rule, so printing it would add a row whose
every figure the reader can already derive. No bridge line
is wired either — it would be the trivial 10,000 + 0 =
10,000, the line the owning senior row already wires (MM,
§33). The KA line (10,000 − 56 = 9,944) is still the worst
renting case the tool prints.

The pinned md5 does NOT move — the tool's output is
byte-identical (a comment only in `economy_sim.py`); the
MN baseline `c70567cb94bd018ef50df1470fdbe746` stands, and
the `--shibnagar` md5 `95022a1592dca4d34b91f5f0a6890526`
stands. The second-earner surge table keeps its five
pairings, and the Shibnagar identity still covers 132 rows.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** none from this unit. The second-earner
surge table is now closed — five pairings printed, the
sixth (senior, renting) decided unprinted with a measured
reason on both the flat rows (ME/MM, §33) and the surge
pattern (this unit). The §34 open note is closed by this
unit.

## 36. Addendum — Taxi surge at a second weather factor (Unit MP, Queue 47)

**Date:** 2026-11-26. **Method:** measure fresh seeded live
months in the EY shape (`Simulation`,
`generate_population(60)`, 32 days) — read each month's
rain/storm counts from `daily_weather` and every taxi
driver's settled month-1 wage from `economy_ledger` (the
`wage` row at `game_minutes` 43,200) against the band in
`employments` — and check the tool's formula reproduces the
settled grosses at each new factor, including the rounding
rule (settled amounts are integers; the tool must round the
same way). No invented household, no tuning call.

**Measured: the formula reproduces the settled grosses at
both new factors.** Seed `mo-probe-1`: 1 rain day
(day_index 9) + 2 storm days (day_index 6 and 28), factor
`1 + 0.25 × 1/30 + 0.5 × 2/30 = 1.0417` — four taxi drivers,
all SYS-EMPLOYERS-paid, settled exactly at round(band ×
1.0417): entry 14,000 → 14,583, mid 23,000 → 23,958,
senior 36,000 → 37,500 (two drivers). Seed `mo-probe-2`: 4
rain days (day_index 0, 3, 9, 15) + 3 storm days
(day_index 4, 5, 28), factor `1 + 0.25 × 4/30 + 0.5 × 3/30
= 1.0833` — two taxi drivers, all SYS-EMPLOYERS-paid,
settled exactly at round(band × 1.0833): mid 23,000 →
24,917, senior 36,000 → 39,000. The tool's
`simulate(..., taxi_rain_days=..., taxi_storm_days=...)`
grosses at the same factors are identical — 14,583 /
23,958 / 37,500 and 15,167 / 24,917 / 39,000 — and the
rounding agrees in both directions: 14,000 × 1.0417 is
14,583.33 → 14,583 (rounds down) and 23,000 × 1.0833 is
24,916.67 → 24,917 (rounds up). No settled gross disagrees
with the formula, so no disagreement is recorded and no
model fix follows.

Single-earner taxi rows at the two new factors (gross,
net, delta vs flat):

| Factor | Tier | Surged gross | Surged net | Gross delta | Net delta |
|---|---:|---:|---:|---:|---:|
| 1.0417 | entry | 14,583 | 6,879 | +583 | +379 |
| 1.0417 | mid | 23,958 | 12,525 | +958 | +575 |
| 1.0417 | senior | 37,500 | 20,650 | +1,500 | +900 |
| 1.0833 | entry | 15,167 | 7,251 | +1,167 | +751 |
| 1.0833 | mid | 24,917 | 13,100 | +1,917 | +1,150 |
| 1.0833 | senior | 39,000 | 21,550 | +3,000 | +1,800 |

The surge is now corroborated at three live factors —
1.0417, 1.05 (the EY month, §16) and 1.0833 — and the
formula's only live inputs remain the month's rain/storm
counts, which the tool takes as named counts. The KC
section keeps printing the EY month's weather (factor
1.05) as the canonical scenario; the two new factors are
recorded here and in §16, not printed as a second section.
The pinned md5 does NOT move — the tool's output is
byte-identical (a comment only in `economy_sim.py`); the
MN baseline `c70567cb94bd018ef50df1470fdbe746` stands, and
the `--shibnagar` md5 `95022a1592dca4d34b91f5f0a6890526`
stands.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** none from this unit. The KC surge's
single-factor grounding is now three-factor grounding; the
next honest check on the surge would be a factor outside
the 1.04–1.09 band — a very wet or very stormy month —
which no seeded month has yet produced.

## 37. Addendum — Taxi surge outside the 1.04–1.09 band (Unit MQ, Queue 48)

**Date:** 2026-11-26. **Method:** measure fresh seeded live
months in the EY shape (`Simulation`,
`generate_population(60)`, 32 days) — read each month's
rain/storm counts from `daily_weather` and every taxi
driver's settled month-1 wage from `economy_ledger` (the
`wage` row at `game_minutes` 43,200) against the band in
`employments` — and check the tool's formula reproduces the
settled grosses at each new factor, including the rounding
rule (settled amounts are integers; the tool must round the
same way). No invented household, no tuning call.

**Measured: the formula reproduces the settled grosses at
both new factors, above the band.** Seed `mq-probe-1`: 8
rain days (day_index 11, 14, 15, 16, 21, 22, 23, 25) + 3
storm days (day_index 3, 4, 17), factor `1 + 0.25 × 8/30 +
0.5 × 3/30 = 1.1167` — four taxi drivers, all
SYS-EMPLOYERS-paid, settled exactly at round(band ×
1.1167): entry 14,000 → 15,633 (two drivers), mid 23,000 →
25,683 (two drivers). Seed `mq-probe-6`: 6 rain days
(day_index 3, 4, 7, 12, 19, 28) + 3 storm days (day_index
11, 16, 18), factor `1 + 0.25 × 6/30 + 0.5 × 3/30 = 1.1000`
— three taxi drivers, all SYS-EMPLOYERS-paid, settled
exactly at round(band × 1.1000): entry 14,000 → 15,400 (two
drivers), mid 23,000 → 25,300 (one driver). The tool's
`simulate(..., taxi_rain_days=..., taxi_storm_days=...)`
grosses at the same factors are identical — 15,633 / 25,683
/ 40,200 and 15,400 / 25,300 / 39,600 — and the rounding
adds no new direction: 14,000 × 1.1167 is 15,633.33 →
15,633 (rounds down), 23,000 × 1.1167 is 25,683.33 →
25,683 (rounds down), and at 1.1000 the products are
integers up to float error (14,000 × 1.1000 =
15,400.000000000002), so rounding is a no-op there
(15,400 / 25,300 / 39,600), so the MP pin on
the rounding in both directions stands unextended. No
settled gross disagrees with the formula, so no disagreement
is recorded and no model fix follows.

Single-earner taxi rows at the two new factors (gross,
net, delta vs flat):

| Factor | Tier | Surged gross | Surged net | Gross delta | Net delta |
|---|---:|---:|---:|---:|---:|
| 1.1167 | entry | 15,633 | 7,529 | +1,633 | +1,029 |
| 1.1167 | mid | 25,683 | 13,560 | +2,683 | +1,610 |
| 1.1167 | senior | 40,200 | 22,260 | +4,200 | +2,510 |
| 1.1000 | entry | 15,400 | 7,390 | +1,400 | +890 |
| 1.1000 | mid | 25,300 | 13,330 | +2,300 | +1,380 |
| 1.1000 | senior | 39,600 | 21,910 | +3,600 | +2,160 |

**Honest limit: the senior tier is not live-settled above
the band.** Neither probe world holds a senior taxi driver,
so the senior grosses at 1.1167 and 1.1000 (40,200 /
39,600) are tool-computed, not live-settled — the formula
above the band is corroborated live at entry and mid only.
Six further seeds probed while drafting the follow-up
(`mq-probe-7`–`mq-probe-12`) hold senior drivers only at
factors at or below 1.0833, and the one further above-band
month found (`mq-probe-11`: 3 rain days + 5 storm days,
factor 1.1083) holds a mid driver only, settled 25,492 —
so a live senior settlement above the band is still
unmeasured, and the storm-heavy shape of that month is the
next check (Queue 49 Unit MR).

The surge is now corroborated at five live factors —
1.0417, 1.05 (the EY month, §16), 1.0833, 1.1000 and
1.1167 — and the formula's only live inputs remain the
month's rain/storm counts, which the tool takes as named
counts. The KC section keeps printing the EY month's
weather (factor 1.05) as the canonical scenario; the two
new factors are recorded here and in §16, not printed as a
second section. The pinned md5 does NOT move — the tool's
output is byte-identical (a comment only in
`economy_sim.py`); the MN baseline
`c70567cb94bd018ef50df1470fdbe746` stands, and the
`--shibnagar` md5 `95022a1592dca4d34b91f5f0a6890526`
stands.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** a live senior taxi-driver settlement
above the 1.09 band is still unmeasured (this unit) — and
the storm-heavy month above the band (`mq-probe-11`, 3 rain
+ 5 storm, factor 1.1083, one mid driver settled 25,492) is
Queue 49 Unit MR.

## 38. Addendum — Taxi surge in a storm-heavy month above the band (Unit MR, Queue 49)

**Date:** 2026-11-26. **Method:** measure fresh seeded live
months in the EY shape (`Simulation`,
`generate_population(60)`, 32 days) — read each month's
rain/storm counts from `daily_weather` and every taxi
driver's settled month-1 wage from `economy_ledger` (the
`wage` row at `game_minutes` 43,200) against the band in
`employments` — and check the tool's formula reproduces the
settled grosses at the new factor, including the rounding
rule (settled amounts are integers; the tool must round the
same way). No invented household, no tuning call.

**Measured: the formula reproduces the settled grosses at
1.1083, in a storm-heavy month.** Seed `mq-probe-11`: 3
rain days (day_index 2, 25, 26) + 5 storm days (day_index
6, 8, 10, 14, 29), factor `1 + 0.25 × 3/30 + 0.5 × 5/30 =
1.1083` — one taxi driver, SYS-EMPLOYERS-paid, settled
exactly at round(band × 1.1083): mid 23,000 → 25,492. A
second seeded month lands on the SAME factor from the
opposite mix — seed `mr-probe-7`: 9 rain days (day_index 2,
5, 8, 10, 16, 19, 21, 26, 27) + 2 storm days (day_index 14,
24), factor `1 + 0.25 × 9/30 + 0.5 × 2/30 = 1.1083` — two
taxi drivers, all SYS-EMPLOYERS-paid, settled exactly at
round(band × 1.1083): entry 14,000 → 15,517, mid 23,000 →
25,492. The tool's `simulate(..., taxi_rain_days=...,
taxi_storm_days=...)` grosses at the same factor are
identical — 15,517 / 25,492 / 39,900 — and the rounding
goes UP at both settled tiers this time: 14,000 × 1.1083 is
15,516.67 → 15,517 (rounds up), 23,000 × 1.1083 is
25,491.67 → 25,492 (rounds up), while the senior product
is an integer up to float error (36,000 × 1.1083 =
39,899.99...), so rounding is a no-op there. No settled
gross disagrees with the formula, so no disagreement is
recorded and no model fix follows.

Single-earner taxi rows at the new factor (gross, net,
delta vs flat):

| Factor | Tier | Surged gross | Surged net | Gross delta | Net delta |
|---|---:|---:|---:|---:|---:|
| 1.1083 | entry | 15,517 | 7,460 | +1,517 | +960 |
| 1.1083 | mid | 25,492 | 13,445 | +2,492 | +1,495 |
| 1.1083 | senior | 39,900 | 22,090 | +3,900 | +2,340 |

**The settlement keys on the factor, not the mix.** The
two months have opposite weather mixes — one storm-heavy
(3 rain + 5 storm), one rain-heavy (9 rain + 2 storm) —
and the same factor, and they settle identically: the mid
driver settles 25,492 in both, the entry driver 15,517 in
the second. The formula takes only the counts, and the
counts enter only through the factor, so any two months
with the same factor must settle the same grosses — and
here they do, live. The MP pin on the rounding in both
directions stands, now extended upward: down at 1.0417 /
1.1167, up at 1.0833 / 1.1083, no-op at 1.1000.

**Honest limit: the senior tier is not live-settled above
the band.** Neither probe world holds a senior taxi driver,
so the senior gross at 1.1083 (39,900) is tool-computed,
not live-settled — the formula above the band is
corroborated live at entry and mid only. Sixteen further
seeds probed while drafting the follow-up (`mr-probe-1`–
`mr-probe-16`) hold no senior driver in any month above the
band either — seniors appear only at factors 1.0333 to
1.0750 — so a live senior settlement above the band is
still unmeasured, and the storm-heavy shape recurs just
above the band (`mr-probe-13`: 3 rain days + 4 storm days,
factor 1.0917, one mid driver settled 25,108).

The surge is now corroborated at six live factors —
1.0417, 1.05 (the EY month, §16), 1.0833, 1.1000, 1.1083
and 1.1167 — and the formula's only live inputs remain the
month's rain/storm counts, which the tool takes as named
counts. The KC section keeps printing the EY month's
weather (factor 1.05) as the canonical scenario; the new
factor is recorded here and in §16, not printed as a
second section. The pinned md5 does NOT move — the tool's
output is byte-identical (a comment only in
`economy_sim.py`); the MN baseline
`c70567cb94bd018ef50df1470fdbe746` stands, and the
`--shibnagar` md5 `95022a1592dca4d34b91f5f0a6890526`
stands.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** a live senior taxi-driver settlement
above the 1.09 band is still unmeasured (this unit) — the
hunt for a seeded live month above the band holding a
senior driver is Queue 50 Unit MS.

## 39. Addendum — Live senior taxi settlement above the band (Unit MS, Queue 50)

**Date:** 2026-11-26. **Method:** hunt for a seeded live
month in the EY shape (`Simulation`,
`generate_population(60)`, 32 days) with factor above 1.09
that holds a senior taxi driver — sweep sixteen fresh seeds
(`ms-probe-1`–`ms-probe-16`), recording each month's
rain/storm counts, factor, and driver bands — and check the
tool's formula reproduces the senior settled gross
(round(36,000 × factor)), including the rounding rule
(settled amounts are integers; the tool must round the same
way). No invented household, no tuning call.

**Measured: the senior gross above the band is now
live-settled.** Seed `ms-probe-11`: 5 rain days (day_index
6, 10, 11, 19, 25) + 3 storm days (day_index 3, 14, 17),
factor `1 + 0.25 × 5/30 + 0.5 × 3/30 = 1.0917` — four taxi
drivers, all SYS-EMPLOYERS-paid, settled exactly at
round(band × 1.0917): entry 14,000 → 15,283 (NEX000047),
mid 23,000 → 25,108 (NEX000013, NEX000042), senior 36,000 →
39,300 (NEX000043). The senior driver is the first senior
taxi driver to settle live above the band — the senior
gross at 1.0917 (39,300) is a measured figure, not
tool-computed. A second seeded month lands on the SAME
factor from different day positions — seed `ms-probe-7`: 5
rain days (day_index 7, 12, 19, 26, 28) + 3 storm days
(day_index 0, 1, 4), factor 1.0917 — two taxi drivers, all
SYS-EMPLOYERS-paid, both mid settled 25,108. The tool's
`simulate(..., taxi_rain_days=..., taxi_storm_days=...)`
grosses at the same factor are identical — 15,283 / 25,108
/ 39,300 — and the rounding goes DOWN at both settled lower
tiers this time: 14,000 × 1.0917 is 15,283.33 → 15,283
(rounds down), 23,000 × 1.0917 is 25,108.33 → 25,108
(rounds down), while the senior product is an integer up to
float error (36,000 × 1.0917 = 39,300.00...), so rounding
is a no-op there. No settled gross disagrees with the
formula, so no disagreement is recorded and no model fix
follows.

Single-earner taxi rows at the new factor (gross, net,
delta vs flat):

| Factor | Tier | Surged gross | Surged net | Gross delta | Net delta |
|---|---:|---:|---:|---:|---:|
| 1.0917 | entry | 15,283 | 7,320 | +1,283 | +820 |
| 1.0917 | mid | 25,108 | 13,215 | +2,108 | +1,265 |
| 1.0917 | senior | 39,300 | 21,730 | +3,300 | +1,980 |

**The settlement keys on the counts, not the positions.**
The two months share the counts (5 rain + 3 storm) but put
the wet days on different days — `ms-probe-11` rains on
day_index 6, 10, 11, 19, 25 and storms on 3, 14, 17, while
`ms-probe-7` rains on 7, 12, 19, 26, 28 and storms on 0, 1,
4 — and they settle identically: the mid driver settles
25,108 in both. The formula takes only the counts, and the
counts enter only through the factor, so any two months with
the same counts must settle the same grosses — and here they
do, live, with the positions moved. The MP pin on the
rounding in both directions stands, now extended downward
again: down at 1.0417 / 1.0917 / 1.1167, up at 1.0833 /
1.1083, no-op at 1.1000.

**The full sweep.** Sixteen fresh seeds, EY shape (60
population, 32 days each) — 46 taxi drivers in all, 6 of
them senior; 3 months above the band, and only one of those
holds a senior:

| Seed | Rain | Storm | Factor | Drivers (band: settled) |
|---|---:|---:|---:|---|
| ms-probe-1 | 5 | 1 | 1.0583 | mid: 24,342; entry: 14,817 |
| ms-probe-2 | 6 | 2 | 1.0833 | mid: 24,917 × 3 |
| ms-probe-3 | 3 | 1 | 1.0417 | entry: 14,583 × 2; mid: 23,958 × 2 |
| ms-probe-4 | 3 | 1 | 1.0417 | mid: 23,958 × 2; senior: 37,500 |
| ms-probe-5 | 6 | 1 | 1.0667 | entry: 14,933; mid: 24,533; senior: 38,400 |
| ms-probe-6 | 9 | 2 | 1.1083 | mid: 25,492 × 2 |
| ms-probe-7 | 5 | 3 | 1.0917 | mid: 25,108 × 2 |
| ms-probe-8 | 7 | 1 | 1.0750 | senior: 38,700 |
| ms-probe-9 | 3 | 1 | 1.0417 | none |
| ms-probe-10 | 8 | 1 | 1.0833 | mid: 24,917 × 4 |
| ms-probe-11 | 5 | 3 | 1.0917 | entry: 15,283; mid: 25,108 × 2; senior: 39,300 |
| ms-probe-12 | 0 | 1 | 1.0167 | entry: 14,233 × 2; mid: 23,383 × 2 |
| ms-probe-13 | 2 | 0 | 1.0167 | entry: 14,233; mid: 23,383 |
| ms-probe-14 | 4 | 2 | 1.0667 | mid: 24,533 |
| ms-probe-15 | 4 | 0 | 1.0333 | senior: 37,200 × 2; mid: 23,767 × 2 |
| ms-probe-16 | 4 | 3 | 1.0833 | mid: 24,917 × 6; entry: 15,167 |

Every settled gross in the sweep is round(band × factor) —
the sweep corroborates the formula at eight factors in one
pass (1.0167, 1.0333, 1.0417, 1.0583, 1.0667, 1.0750,
1.0833, 1.0917, 1.1083), including a third corroboration at
1.1083 (`ms-probe-6`: two mids settled 25,492, the same
grosses MR measured). Seniors settle in-band at 1.0333 to
1.0750 (five of them: 37,200, 37,500, 38,400, 38,700, and a
second 37,200) — the same range MR recorded — and above the
band at 1.0917 only, once. The hit rate is thin: 3
above-band months in 16 seeds, and only one holds a senior.

The surge is now corroborated at seven live factors —
1.0417, 1.05 (the EY month, §16), 1.0833, 1.0917, 1.1000,
1.1083 and 1.1167 — and the senior tier is live-settled
above the band for the first time, at exactly one factor.
The KC section keeps printing the EY month's weather
(factor 1.05) as the canonical scenario; the new factor is
recorded here and in §16, not printed as a second section.
The pinned md5 does NOT move — the tool's output is
byte-identical (a comment only in `economy_sim.py`); the MN
baseline `c70567cb94bd018ef50df1470fdbe746` stands, and the
`--shibnagar` md5 `95022a1592dca4d34b91f5f0a6890526`
stands.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the senior settlement above the band is
measured at exactly one factor (1.0917) — a second
above-band senior settlement, at a different factor, is
Queue 51 Unit MT.

## 40. Addendum — Second above-band senior taxi settlement, at a different factor (Unit MT, Queue 51)

**Date:** 2026-11-27. **Method:** hunt for a seeded live
month in the EY shape (`Simulation`,
`generate_population(60)`, 32 days) with factor above 1.09,
at a DIFFERENT factor from 1.0917, that holds a senior taxi
driver — sweep twenty-four fresh seeds
(`mt-probe-1`–`mt-probe-24`), recording each month's
rain/storm counts, factor, and driver bands — and check the
tool's formula reproduces the senior settled gross
(round(36,000 × factor)), including the rounding rule
(settled amounts are integers; the tool must round the same
way). No invented household, no tuning call.

**Measured: the senior gross above the band is now
live-settled at a second factor.** Seed `mt-probe-5`: 7 rain
days (day_index 3, 13, 14, 15, 16, 17, 29) + 3 storm days
(day_index 12, 23, 27), factor `1 + 0.25 × 7/30 + 0.5 × 3/30
= 1.1083` — five taxi drivers, all SYS-EMPLOYERS-paid,
settled exactly at round(band × 1.1083): mid 23,000 →
25,492 (NEX000004, NEX000010, NEX000043, NEX000058),
senior 36,000 → 39,900 (NEX000047). The senior gross at
1.1083 (39,900) is now a measured figure, not
tool-computed — it supersedes the MR (§38) status for that
factor. A second seeded month lands on the MS factor —
seed `mt-probe-13`: 5 rain days (day_index 9, 12, 24, 27,
29) + 3 storm days (day_index 2, 7, 21), factor 1.0917 —
five taxi drivers, all SYS-EMPLOYERS-paid, four mid
settled 25,108 (NEX000002, NEX000006, NEX000020,
NEX000043) and senior 36,000 → 39,300 (NEX000028) — the
second live senior settlement at 1.0917. The tool's
`simulate(..., taxi_rain_days=..., taxi_storm_days=...)`
grosses at 1.1083 are identical — 15,517 / 25,492 /
39,900 — and the rounding goes UP at both lower tiers this
time: 14,000 × 1.1083 is 15,516.67 → 15,517 (rounds up),
23,000 × 1.1083 is 25,491.67 → 25,492 (rounds up), as MR
already measured at this factor, while the senior product
is exactly 39,900.0, so rounding is a no-op there. No
settled gross disagrees with the formula, so no
disagreement is recorded and no model fix follows.

Single-earner taxi rows at the new factor (gross, net,
delta vs flat):

| Factor | Tier | Surged gross | Surged net | Gross delta | Net delta |
|---|---:|---:|---:|---:|---:|
| 1.1083 | entry | 15,517 | 7,460 | +1,517 | +960 |
| 1.1083 | mid | 25,492 | 13,445 | +2,492 | +1,495 |
| 1.1083 | senior | 39,900 | 22,090 | +3,900 | +2,340 |

**The senior rounding question is closed by construction.**
The factor is `1 + 0.25 × rain/30 + 0.5 × storm/30`, so
the senior product is 36,000 + 36,000 × 0.25/30 × rain +
36,000 × 0.5/30 × storm = 36,000 + 300 × rain + 600 ×
storm — an integer for every rain/storm count in exact
arithmetic (in float the product sits within ~1e-11 of it,
and round() always lands on it — verified over rain 0–9,
storm 0–5), because 300 and 600 are whole. Rounding is
therefore a no-op at the senior tier at EVERY factor, not
just at the two measured above the band: no senior
settlement can ever test the rounding rule, because there
is nothing to round. The
rounding pin stands where it can bite — at the entry and
mid tiers, now pinned in both directions at five factors
(down at 1.0417 / 1.0917 / 1.1167, up at 1.0833 / 1.1083)
and as a no-op at 1.1000.

**The full sweep.** Twenty-four fresh seeds, EY shape (60
population, 32 days each) — 73 taxi drivers in all, 17 of
them senior; 3 months above the band, and two of those
hold a senior:

| Seed | Rain | Storm | Factor | Drivers (band: settled) |
|---|---:|---:|---:|---|
| mt-probe-1 | 6 | 1 | 1.0667 | mid: 24,533 × 2 |
| mt-probe-2 | 1 | 2 | 1.0417 | entry: 14,583 × 2; mid: 23,958 × 4; senior: 37,500 |
| mt-probe-3 | 2 | 2 | 1.0500 | mid: 24,150 × 3 |
| mt-probe-4 | 6 | 1 | 1.0667 | mid: 24,533 × 2 |
| mt-probe-5 | 7 | 3 | 1.1083 | mid: 25,492 × 4; senior: 39,900 |
| mt-probe-6 | 2 | 2 | 1.0500 | mid: 24,150 × 2 |
| mt-probe-7 | 7 | 0 | 1.0583 | mid: 24,342; senior: 38,100 × 3 |
| mt-probe-8 | 2 | 0 | 1.0167 | mid: 23,383 |
| mt-probe-9 | 9 | 1 | 1.0917 | mid: 25,108 × 2 |
| mt-probe-10 | 3 | 3 | 1.0750 | mid: 24,725 × 4 |
| mt-probe-11 | 2 | 2 | 1.0500 | entry: 14,700; mid: 24,150 × 2; senior: 37,800 |
| mt-probe-12 | 6 | 1 | 1.0667 | mid: 24,533; senior: 38,400 |
| mt-probe-13 | 5 | 3 | 1.0917 | mid: 25,108 × 4; senior: 39,300 |
| mt-probe-14 | 2 | 1 | 1.0333 | entry: 14,467 × 2; mid: 23,767 × 2; senior: 37,200 |
| mt-probe-15 | 3 | 2 | 1.0583 | mid: 24,342 |
| mt-probe-16 | 3 | 2 | 1.0583 | mid: 24,342; senior: 38,100 × 2 |
| mt-probe-17 | 4 | 2 | 1.0667 | senior: 38,400 |
| mt-probe-18 | 8 | 1 | 1.0833 | entry: 15,167; senior: 39,000 |
| mt-probe-19 | 1 | 1 | 1.0250 | mid: 23,575; senior: 36,900 |
| mt-probe-20 | 6 | 0 | 1.0500 | mid: 24,150 × 4 |
| mt-probe-21 | 3 | 2 | 1.0583 | entry: 14,817; mid: 24,342; senior: 38,100 × 2 |
| mt-probe-22 | 7 | 1 | 1.0750 | mid: 24,725 |
| mt-probe-23 | 5 | 0 | 1.0417 | entry: 14,583; mid: 23,958 × 2 |
| mt-probe-24 | 4 | 0 | 1.0333 | mid: 23,767 × 3; senior: 37,200 |

Every settled gross in the sweep is round(band × factor) —
the sweep corroborates the formula at eleven factors in
one pass (1.0167, 1.0250, 1.0333, 1.0417, 1.0500, 1.0583,
1.0667, 1.0750, 1.0833, 1.0917, 1.1083), including a new
factor not seen in the MS sweep (1.0250, `mt-probe-19`:
mid 23,575, senior 36,900) and a fourth corroboration at
1.1083. Seniors settle in-band at 1.0250 to 1.0833 (fifteen
of them: 36,900, 37,200 × 2, 37,500, 37,800, 38,100 × 7,
38,400 × 2, 39,000) and above the band at 1.0917 and
1.1083. The hit rate stays thin: 3 above-band months in 24
seeds, two of them holding a senior — better than MS's 1
in 16, still a thin base.

The surge is still corroborated at seven live factors —
1.0417, 1.05 (the EY month, §16), 1.0833, 1.0917, 1.1000,
1.1083 and 1.1167 — and the senior tier is now
live-settled above the band at two of them (1.0917,
1.1083). The KC section keeps printing the EY month's
weather (factor 1.05) as the canonical scenario; the new
factor is recorded here and in §16, not printed as a
second section. The pinned md5 does NOT move — the tool's
output is byte-identical (a comment only in
`economy_sim.py`); the MN baseline
`c70567cb94bd018ef50df1470fdbe746` stands, and the
`--shibnagar` md5 `95022a1592dca4d34b91f5f0a6890526`
stands.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the senior gross at 1.1167 (40,200) is
still tool-computed only — no senior taxi driver has
settled live at the highest corroborated factor. A hunt
for a senior settlement at 1.1167 is Queue 52 Unit MU.

## 41. Addendum — Senior taxi settlement at 1.1167: the hunt finds none; the senior gross at 1.1000 is live-settled (Unit MU, Queue 52)

**Date:** 2026-11-27. **Method:** hunt for a seeded live
month in the EY shape (`Simulation`,
`generate_population(60)`, 32 days) with factor 1.1167
that holds a senior taxi driver — sweep twenty-four fresh
seeds (`mu-probe-1`–`mu-probe-24`), recording each month's
rain/storm counts, factor, and driver bands — and check the
tool's formula reproduces the senior settled gross
(round(36,000 × factor)), including the rounding rule
(settled amounts are integers; the tool must round the same
way). If the hunt finds none after the bounded sweep,
record the hunt honestly and stop — a wider sweep would be
grinding, not measuring. No invented household, no tuning
call.

**Measured: the hunt finds no month at 1.1167.** No seed
in the sweep reaches factor 1.1167 at all — the highest
factor in twenty-four months is 1.1000, and the sweep
holds nine months above the band (four at 1.0917, five at
1.1000), three of them holding a senior, none at 1.1167.
The senior gross at 1.1167 (40,200) therefore stays
tool-computed only — the MU hunt does not move it, and the
thin hit rate is itself the finding: a blind sweep's hit
rate for the target factor is 0 in 24 here (MT found 3
above-band months in 24 seeds, MS 1 in 16, and MQ found
the single 1.1167 month in its own probes). No
disagreement is recorded and no model fix follows — every
settled gross in the sweep is round(band × factor).

**Measured beside the hunt: the senior gross at 1.1000 is
now live-settled.** Seed `mu-probe-8`: 6 rain days
(day_index 14, 15, 16, 22, 23, 28) + 3 storm days
(day_index 17, 20, 26), factor `1 + 0.25 × 6/30 + 0.5 ×
3/30 = 1.1000` — three taxi drivers, all SYS-EMPLOYERS-paid,
settled exactly at round(band × 1.1000): mid 23,000 →
25,300 (NEX000029, NEX000055), senior 36,000 → 39,600
(NEX000012). And seed `mu-probe-16`: 8 rain days
(day_index 4, 7, 13, 17, 20, 24, 28, 29) + 2 storm days
(day_index 12, 14), factor 1.1000 from the opposite mix —
nine taxi drivers, all SYS-EMPLOYERS-paid, settled exactly
at round(band × 1.1000): entry 14,000 → 15,400
(NEX000012, NEX000040), mid 23,000 → 25,300 (NEX000002,
NEX000009, NEX000025, NEX000046, NEX000052), senior 36,000
→ 39,600 (NEX000045, NEX000060). The 39,600 at 1.1000 is
now a measured figure, not tool-computed — it supersedes
the MQ (§37) status for that factor. Two different weather
mixes at the same factor settle identically, so the
settlement keys on the factor, not the mix, at 1.1000 as MR
already measured at 1.1083. The tool's `simulate(...,
taxi_rain_days=..., taxi_storm_days=...)` grosses at 1.1000
are identical — 15,400 / 25,300 / 39,600 — and the rounding
is a no-op at every tier this time: 14,000 × 1.1000 is
15,400.000000000002, 23,000 × 1.1000 is 25,300.000000000004
and 36,000 × 1.1000 is exactly 39,600.0, so round() lands
on the integer in each case.

A third live senior settlement at 1.0917 also lands — seed
`mu-probe-3`: 7 rain days (day_index 0, 2, 10, 13, 16, 20,
27) + 2 storm days (day_index 5, 22), factor 1.0917 from a
different mix than MS/MT's 5 rain + 3 storm — two taxi
drivers, all SYS-EMPLOYERS-paid, mid 23,000 → 25,108
(NEX000049) and senior 36,000 → 39,300 (NEX000029). The
1.0917 senior gross now rests on three live instances
(MS, MT, MU), and the factor identity holds across mixes
there too.

Single-earner taxi rows at the new factor (gross, net,
delta vs flat):

| Factor | Tier | Surged gross | Surged net | Gross delta | Net delta |
|---|---:|---:|---:|---:|---:|
| 1.1000 | entry | 15,400 | 7,390 | +1,400 | +890 |
| 1.1000 | mid | 25,300 | 13,330 | +2,300 | +1,380 |
| 1.1000 | senior | 39,600 | 21,910 | +3,600 | +2,160 |

**The full sweep.** Twenty-four fresh seeds, EY shape (60
population, 32 days each) — 71 taxi drivers in all, 9 of
them senior; 9 months above the band, and three of those
hold a senior:

| Seed | Rain | Storm | Factor | Drivers (band: settled) |
|---|---:|---:|---:|---|
| mu-probe-1 | 4 | 3 | 1.0833 | mid: 24,917 × 3; senior: 39,000 |
| mu-probe-2 | 3 | 3 | 1.0750 | entry: 15,050 × 2; mid: 24,725 |
| mu-probe-3 | 7 | 2 | 1.0917 | mid: 25,108; senior: 39,300 |
| mu-probe-4 | 4 | 4 | 1.1000 | entry: 15,400; mid: 25,300 |
| mu-probe-5 | 7 | 2 | 1.0917 | entry: 15,283; mid: 25,108 × 3 |
| mu-probe-6 | 2 | 3 | 1.0667 | entry: 14,933 × 2; mid: 24,533 |
| mu-probe-7 | 8 | 1 | 1.0833 | mid: 24,917; senior: 39,000 |
| mu-probe-8 | 6 | 3 | 1.1000 | mid: 25,300 × 2; senior: 39,600 |
| mu-probe-9 | 6 | 0 | 1.0500 | mid: 24,150 × 3 |
| mu-probe-10 | 7 | 2 | 1.0917 | entry: 15,283 |
| mu-probe-11 | 4 | 0 | 1.0333 | entry: 14,467; mid: 23,767 × 3 |
| mu-probe-12 | 6 | 1 | 1.0667 | senior: 38,400 |
| mu-probe-13 | 6 | 1 | 1.0667 | entry: 14,933; mid: 24,533 |
| mu-probe-14 | 5 | 2 | 1.0750 | mid: 24,725 × 3; senior: 38,700 |
| mu-probe-15 | 7 | 2 | 1.0917 | entry: 15,283; mid: 25,108 × 3 |
| mu-probe-16 | 8 | 2 | 1.1000 | entry: 15,400 × 2; mid: 25,300 × 5; senior: 39,600 × 2 |
| mu-probe-17 | 4 | 3 | 1.0833 | mid: 24,917 × 2 |
| mu-probe-18 | 1 | 1 | 1.0250 | entry: 14,350; mid: 23,575; senior: 36,900 |
| mu-probe-19 | 6 | 3 | 1.1000 | mid: 25,300 × 3 |
| mu-probe-20 | 7 | 0 | 1.0583 | mid: 24,342 |
| mu-probe-21 | 4 | 0 | 1.0333 | entry: 14,467; mid: 23,767 |
| mu-probe-22 | 8 | 2 | 1.1000 | entry: 15,400 × 2; mid: 25,300 |
| mu-probe-23 | 3 | 1 | 1.0417 | entry: 14,583 × 2; mid: 23,958 |
| mu-probe-24 | 2 | 1 | 1.0333 | entry: 14,467; mid: 23,767 × 2 |

Every settled gross in the sweep is round(band × factor) —
the sweep corroborates the formula at ten factors in one
pass (1.0250, 1.0333, 1.0417, 1.0500, 1.0583, 1.0667,
1.0750, 1.0833, 1.0917, 1.1000). Seniors settle in-band at
1.0250 to 1.0833 (five of them: 36,900, 38,400, 38,700,
39,000 × 2) and above the band at 1.0917 and 1.1000 (four
of them: 39,300, 39,600 × 3). The hit rate for the target
factor is 0 in 24 — the month's weather is the binding
constraint, not the senior: nine above-band months appear,
but none lands on 1.1167, which needs rain + 2 × storm =
14 wet-weighted days. The weather itself is seed-only
(`SimRng.stream("weather", day_index)` is keyed by the
seed, not by the population — verified: the weather-first
read of `mu-probe-1`, `mu-probe-3` and `mu-probe-16`
reproduces their full-run counts exactly), so a later hunt
can pre-filter seeds on the weather signature before
running the full 32-day shape, instead of sweeping blind.

The surge is still corroborated at seven live factors —
1.0417, 1.05 (the EY month, §16), 1.0833, 1.0917, 1.1000,
1.1083 and 1.1167 — and the senior tier is now
live-settled above the band at three of them (1.0917,
1.1000, 1.1083). The KC section keeps printing the EY
month's weather (factor 1.05) as the canonical scenario;
the new factor is recorded here and in §16, not printed as
a second section. The pinned md5 does NOT move — the
tool's output is byte-identical (a comment only in
`economy_sim.py`); the MN baseline
`c70567cb94bd018ef50df1470fdbe746` stands, and the
`--shibnagar` md5 `95022a1592dca4d34b91f5f0a6890526`
stands.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the senior gross at 1.1167 (40,200) is
still tool-computed only — no senior taxi driver has
settled live at the highest corroborated factor. A hunt
for a senior settlement at 1.1167 with a weather-first
pre-filter (scan seeds for rain + 2 × storm = 14 before
running the full shape) is Queue 53 Unit MV.

## 42. Addendum — Senior taxi settlement at 1.1167: live-settled, twice, by weather-first hunt (Unit MV, Queue 53)

**Date:** 2026-11-27. **Method:** MU proved the month's
weather is seed-only (`SimRng.stream("weather", day_index)`
is keyed by the seed, not by the population), so pre-filter
fresh seeds on the weather signature alone (rain + 2 ×
storm = 14, the 1.1167 condition) WITHOUT running the
population, over a bounded scan of 200 fresh seeds
(`mv-probe-1`–`mv-probe-200`), then run the full EY shape
(`Simulation`, `generate_population(60)`, 32 days) ONLY on
the matching seeds and check whether any holds a senior
taxi driver — and check the tool's formula reproduces the
senior settled gross (round(36,000 × 1.1167) = 40,200),
including the rounding rule (settled amounts are integers;
the tool must round the same way). If the scan finds no
matching weather at all, or no matching month holds a
senior, record that honestly and stop. No invented
household, no tuning call.

**Measured: the pre-filter finds five months at 1.1167,
and two of them hold a senior.** The weather-only scan of
200 seeds matches exactly five — `mv-probe-3` (6 rain + 4
storm), `mv-probe-38` (4 + 5), `mv-probe-105` (8 + 3, MQ's
mix), `mv-probe-106` (6 + 4) and `mv-probe-115` (4 + 5) —
a 2.5% hit rate for the signature, and the full EY run on
each of the five reproduces its scanned counts exactly, so
the pre-filter is itself verified: the weather-first read
predicts the full run's month. All five months are factor
`1 + 0.25 × rain/30 + 0.5 × storm/30 = 1.1167`, 15 taxi
drivers in all, all SYS-EMPLOYERS-paid, every settled
gross exactly round(band × 1.1167).

**Measured: the senior gross at 1.1167 is now
live-settled — twice.** Seed `mv-probe-105`: 8 rain days
(day_index 0, 3, 8, 9, 12, 13, 17, 21) + 3 storm days
(day_index 2, 19, 28), factor 1.1167 — five taxi drivers,
all SYS-EMPLOYERS-paid, settled exactly at round(band ×
1.1167): entry 14,000 → 15,633 (NEX000027), mid 23,000 →
25,683 (NEX000036, NEX000039, NEX000046), senior 36,000 →
40,200 (NEX000014). And seed `mv-probe-115`: 4 rain days
(day_index 5, 9, 14, 18) + 5 storm days (day_index 6, 10,
13, 15, 25), the SAME factor 1.1167 from a different mix —
three taxi drivers, all SYS-EMPLOYERS-paid, settled
exactly at round(band × 1.1167): mid 23,000 → 25,683
(NEX000025, NEX000059), senior 36,000 → 40,200
(NEX000053). The 40,200 at 1.1167 is now a measured
figure, not tool-computed — it supersedes the MQ (§37) and
MU (§41) status for that factor. Two different weather
mixes at the same factor settle identically, so the
settlement keys on the factor, not the mix, at 1.1167 as MR
already measured at 1.1083 and MU at 1.1000. The tool's
`simulate(..., taxi_rain_days=..., taxi_storm_days=...)`
grosses at 1.1167 are identical — 15,633 / 25,683 /
40,200 — and the rounding goes down at both lower tiers
this time: 14,000 × 1.1167 is 15,633.333333333334 and
23,000 × 1.1167 is 25,683.333333333336, so round() lands
below the product in each case, while 36,000 × 1.1167 is
exactly 40,200.0, so rounding is a no-op at the senior
tier.

The other three matching months hold no senior, and are
recorded for the hit rate: seed `mv-probe-3` (6 rain +
4 storm, three drivers, entry 15,633 × 2 and mid 25,683),
seed `mv-probe-38` (4 rain + 5 storm, two drivers, mid
25,683 × 2) and seed `mv-probe-106` (6 rain + 4 storm, two
drivers, entry 15,633 × 2). The weather signature is the
binding constraint, not the senior: five months land on
1.1167 in 200 seeds, and two of them hold a senior — a
far cheaper hunt than MU's blind sweep (24 full runs for
no 1.1167 month at all), because the pre-filter spends the
full shape only where the factor already matches.

Single-earner taxi rows at the new factor (gross, net,
delta vs flat):

| Factor | Tier | Surged gross | Surged net | Gross delta | Net delta |
|---|---:|---:|---:|---:|---:|
| 1.1167 | entry | 15,633 | 7,529 | +1,633 | +1,029 |
| 1.1167 | mid | 25,683 | 13,560 | +2,683 | +1,610 |
| 1.1167 | senior | 40,200 | 22,260 | +4,200 | +2,510 |

**The full scan.** Two hundred fresh seeds, weather-only
pre-filter — five match rain + 2 × storm = 14:

| Seed | Rain | Storm | Factor | Drivers (band: settled) |
|---|---:|---:|---:|---|
| mv-probe-3 | 6 | 4 | 1.1167 | entry: 15,633 × 2; mid: 25,683 |
| mv-probe-38 | 4 | 5 | 1.1167 | mid: 25,683 × 2 |
| mv-probe-105 | 8 | 3 | 1.1167 | entry: 15,633; mid: 25,683 × 3; senior: 40,200 |
| mv-probe-106 | 6 | 4 | 1.1167 | entry: 15,633 × 2 |
| mv-probe-115 | 4 | 5 | 1.1167 | mid: 25,683 × 2; senior: 40,200 |

Every settled gross in the five full runs is round(band ×
factor) — the scan corroborates the formula at 1.1167 from
three distinct mixes (8 + 3, 6 + 4, 4 + 5) in one pass.
Seniors settle above the band at 1.1167 in two of the five
months (40,200 × 2). The hit rate for the target factor
is 5 in 200 by weather, 2 in 5 by senior among the
matches — the month's weather is the binding constraint,
and the pre-filter makes the hunt cheap: 200 weather reads
plus 5 full runs, against MU's 24 full runs for no
1.1167 month at all.

The surge is still corroborated at seven live factors —
1.0417, 1.05 (the EY month, §16), 1.0833, 1.0917, 1.1000,
1.1083 and 1.1167 — and the senior tier above the band now rests
on four live factors (1.0917, 1.1000, 1.1083, 1.1167): the
highest corroborated factor is no longer tool-computed only. The KC
section keeps printing the EY month's weather (factor
1.05) as the canonical scenario; the new factor is recorded
here and in §16, not printed as a second section. The
pinned md5 does NOT move — the tool's output is
byte-identical (a comment only in `economy_sim.py`); the MN
baseline `c70567cb94bd018ef50df1470fdbe746` stands, and the
`--shibnagar` md5 `95022a1592dca4d34b91f5f0a6890526`
stands.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the smallest surge above 1.0 is still
unmeasured — factor 1.0083 (1 rain day, 0 storm days) is
the floor of the surge range and no month has settled live
at it (the lowest corroborated factor is 1.0167, MT §40).
A hunt for a settlement at 1.0083 with the same
weather-first pre-filter (scan seeds for rain + 2 × storm
= 1 before running the full shape) is Queue 54 Unit MW;
feasibility checked in this run: 3 of 200 fresh seeds
(`mw-probe-15`, `mw-probe-124`, `mw-probe-150`) match the
signature, and the tool's figures there are entry 14,117 /
mid 23,192 / senior 36,300 (gross deltas +117 / +192 /
+300), with the rounding going up at both lower tiers
(14,116.67 → 14,117; 23,191.67 → 23,192) and a no-op at
the senior tier (36,300.0 exactly).

## 43. Addendum — Taxi surge at the smallest factor, 1.0083: live-settled at all three tiers, by weather-first hunt (Unit MW, Queue 54)

**Date:** 2026-11-27. **Method:** MV closed the above-band
senior chain at the top (1.1167) and left the floor of the
surge range unmeasured — factor 1.0083 (1 rain day, 0
storm days) is the floor and no month has settled live at
it (the lowest corroborated factor is 1.0167, MT §40).
Hunt with the same weather-first pre-filter MV proved:
scan 200 fresh seeds (`mw-probe-1`–`mw-probe-200`) on the
weather signature alone (rain + 2 × storm = 1, the 1.0083
condition) WITHOUT running the population, then run the
full EY shape (`Simulation`, `generate_population(60)`, 32
days) ONLY on the matching seeds and check whether any
holds a taxi driver — and check the tool's formula
reproduces the settled grosses (round(band × 1.0083):
entry 14,117 / mid 23,192 / senior 36,300), including the
rounding rule (settled amounts are integers; the tool must
round the same way). If the scan finds no matching weather
at all, or no matching month holds a taxi driver, record
that honestly and stop. No invented household, no tuning
call.

**Measured: the pre-filter finds three months at 1.0083,
and two of them hold a senior.** The weather-only scan of
200 seeds matches exactly three — `mw-probe-15` (1 rain,
day_index 3), `mw-probe-124` (1 rain, day_index 11) and
`mw-probe-150` (1 rain, day_index 9) — a 1.5% hit rate
for the signature, and the full EY run on each of the
three reproduces its scanned counts exactly, so the
pre-filter is itself verified again: the weather-first
read predicts the full run's month. All three months are
factor `1 + 0.25 × rain/30 + 0.5 × storm/30 = 1.0083`, 9
taxi drivers in all, all SYS-EMPLOYERS-paid, every settled
gross exactly round(band × 1.0083).

**Measured: the smallest surge is now live-settled — at
all three tiers.** Seed `mw-probe-15`: 1 rain day
(day_index 3), 0 storm days, factor 1.0083 — five taxi
drivers, all SYS-EMPLOYERS-paid, settled exactly at
round(band × 1.0083): entry 14,000 → 14,117 (NEX000044,
NEX000060), mid 23,000 → 23,192 (NEX000023, NEX000055),
senior 36,000 → 36,300 (NEX000059). And seed
`mw-probe-150`: 1 rain day (day_index 9), 0 storm days,
the SAME factor 1.0083 with the rain on a different day —
four taxi drivers, all SYS-EMPLOYERS-paid, settled exactly
at round(band × 1.0083): mid 23,000 → 23,192 (NEX000043,
NEX000060), senior 36,000 → 36,300 (NEX000015,
NEX000028). The 36,300 at 1.0083 is now a measured figure,
not tool-computed — three senior settlements at the floor
factor, across two seeds, with the rain landing on
different days in each, so the settlement keys on the
counts, not the positions, at 1.0083 too. The tool's
`simulate(..., taxi_rain_days=..., taxi_storm_days=...)`
grosses at 1.0083 are identical — 14,117 / 23,192 /
36,300 — and the rounding goes up at both lower tiers
this time: 14,000 × 1.0083 is 14,116.666666666666 and
23,000 × 1.0083 is 23,191.666666666664, so round() lands
above the product in each case, while 36,000 × 1.0083 is
exactly 36,300.0, so rounding is a no-op at the senior
tier.

The third matching month holds no taxi driver at all, and
is recorded for the hit rate: seed `mw-probe-124` (1 rain,
day_index 11, 0 storm, factor 1.0083, zero drivers). The
weather signature is the binding constraint, not the
driver: three months land on 1.0083 in 200 seeds, and two
of them hold a taxi driver — a far cheaper hunt than a
blind sweep (3 full runs, against MU's 24 full runs for no
1.1167 month at all), because the pre-filter spends the
full shape only where the factor already matches.

Single-earner taxi rows at the new factor (gross, net,
delta vs flat):

| Factor | Tier | Surged gross | Surged net | Gross delta | Net delta |
|---|---:|---:|---:|---:|---:|
| 1.0083 | entry | 14,117 | 6,576 | +117 | +76 |
| 1.0083 | mid | 23,192 | 12,065 | +192 | +115 |
| 1.0083 | senior | 36,300 | 19,930 | +300 | +180 |

**The full scan.** Two hundred fresh seeds, weather-only
pre-filter — three match rain + 2 × storm = 1:

| Seed | Rain | Storm | Factor | Drivers (band: settled) |
|---|---:|---:|---:|---|
| mw-probe-15 | 1 | 0 | 1.0083 | entry: 14,117 × 2; mid: 23,192 × 2; senior: 36,300 |
| mw-probe-124 | 1 | 0 | 1.0083 | — |
| mw-probe-150 | 1 | 0 | 1.0083 | mid: 23,192 × 2; senior: 36,300 × 2 |

Every settled gross in the three full runs is round(band ×
factor) — the scan corroborates the formula at 1.0083 from
two distinct rain positions (day_index 3 and 9) in one
pass. Seniors settle at the floor factor in two of the
three months (36,300 × 3). The hit rate for the target
factor is 3 in 200 by weather, 2 in 3 by driver among the
matches — the month's weather is the binding constraint,
and the pre-filter makes the hunt cheap: 200 weather reads
plus 3 full runs.

The surge is still corroborated at eight live factors —
1.0083, 1.0417, 1.05 (the EY month, §16), 1.0833, 1.0917,
1.1000, 1.1083 and 1.1167 — and the factor ladder is now
complete from the floor to the top: every step of rain + 2
× storm = 1..14 has a live settlement (1.0083, 1.0167,
1.0250, 1.0333, 1.0417, 1.05, 1.0583, 1.0667, 1.0750,
1.0833, 1.0917, 1.1000, 1.1083, 1.1167), with the senior
tier live-settled at the floor 1.0083 and at every step
from 1.0250 to 1.1167 except 1.0750, where no month in the
record holds a senior. The KC section keeps printing the EY
month's weather (factor 1.05) as the canonical scenario;
the new factor is recorded here and in §16, not printed as
a second section. The pinned md5 does NOT move — the
tool's output is byte-identical (a comment only in
`economy_sim.py`); the MN baseline
`c70567cb94bd018ef50df1470fdbe746` stands, and the
`--shibnagar` md5 `95022a1592dca4d34b91f5f0a6890526`
stands.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the ladder is complete below the top
but open above it — the next step, factor 1.1250 (rain + 2
× storm = 15), has no live settlement yet, and no factor
above 1.1167 has ever been measured. A hunt for a
settlement at 1.1250 with the same weather-first
pre-filter (scan seeds for rain + 2 × storm = 15 before
running the full shape) is Queue 55 Unit MX.

## 44. Addendum — Taxi surge at the next factor above the top, 1.1250: live-settled at the entry tier, by weather-first hunt (Unit MX, Queue 55)

**Date:** 2026-11-27. **Method:** MW completed the factor
ladder from the floor (1.0083) to the top (1.1167) — every
step of rain + 2 × storm = 1..14 has a live settlement —
but no factor above 1.1167 has ever been measured. Hunt
with the same weather-first pre-filter MW proved: scan
200 fresh seeds (`mx-probe-1`–`mx-probe-200`) on the
weather signature alone (rain + 2 × storm = 15, the
1.1250 condition) WITHOUT running the population, then run
the full EY shape (`Simulation`, `generate_population(60)`,
32 days) ONLY on the matching seeds and check whether any
holds a taxi driver — and check the tool's formula
reproduces the settled grosses (round(band × 1.1250):
entry 15,750 / mid 25,875 / senior 40,500), including the
rounding rule (settled amounts are integers; the tool must
round the same way). If the scan finds no matching weather
at all, or no matching month holds a taxi driver, record
that honestly and stop. No invented household, no tuning
call.

**Measured: the pre-filter finds one month at 1.1250,
and it holds two entry drivers.** The weather-only scan of
200 seeds matches exactly one — `mx-probe-68` (3 rain,
day_index 19, 20, 23; 6 storm, day_index 1, 15, 17, 21,
27, 28) — a 0.5% hit rate for the signature, and the full
EY run on it reproduces its scanned counts exactly, so the
pre-filter is itself verified again: the weather-first read
predicts the full run's month. The month is factor `1 +
0.25 × rain/30 + 0.5 × storm/30 = 1.1250`, two taxi
drivers, both SYS-EMPLOYERS-paid, every settled gross
exactly round(band × 1.1250).

**Measured: the step above the top is now live-settled —
at the entry tier.** Seed `mx-probe-68`: 3 rain days
(day_index 19, 20, 23), 6 storm days (day_index 1, 15, 17,
21, 27, 28), factor 1.1250 — two taxi drivers, both entry,
both SYS-EMPLOYERS-paid, both settled exactly at
round(14,000 × 1.1250): NEX000005 and NEX000040, 15,750
each. The 15,750 at 1.1250 is now a measured figure, not
tool-computed — two entry settlements at the first factor
above the old top, from a month with the rain and the
storms spread across the whole 30 days, so the settlement
keys on the counts, not the positions, at 1.1250 too. The
tool's `simulate(..., taxi_rain_days=...,
taxi_storm_days=...)` grosses at 1.1250 are identical —
15,750 / 25,875 / 40,500 — and the rounding is a no-op at
every tier this time: 14,000 × 1.1250 is exactly 15,750.0,
23,000 × 1.1250 is exactly 25,875.0, and 36,000 × 1.1250
is exactly 40,500.0, so round() lands on the product in
each case.

**Honest limit: no mid and no senior driver in this
month.** The month holds only the two entry drivers, so
the mid gross at 1.1250 (25,875) and the senior gross at
1.1250 (40,500) stay tool-computed, not live-settled — a
live senior settlement above the top is still unmeasured,
and the senior tier above the band still rests on four
live factors (1.0917, 1.1000, 1.1083, 1.1167). The weather
signature is the binding constraint, not the driver: one
month lands on 1.1250 in 200 seeds, and it holds a taxi
driver — a far cheaper hunt than a blind sweep (1 full
run, against MU's 24 full runs for no 1.1167 month at
all), because the pre-filter spends the full shape only
where the factor already matches.

Single-earner taxi rows at the new factor (gross, net,
delta vs flat):

| Factor | Tier | Surged gross | Surged net | Gross delta | Net delta |
|---|---:|---:|---:|---:|---:|
| 1.1250 | entry | 15,750 | 7,601 | +1,750 | +1,101 |
| 1.1250 | mid | 25,875 | 13,675 | +2,875 | +1,725 |
| 1.1250 | senior | 40,500 | 22,425 | +4,500 | +2,675 |

**The full scan.** Two hundred fresh seeds, weather-only
pre-filter — one matches rain + 2 × storm = 15:

| Seed | Rain | Storm | Factor | Drivers (band: settled) |
|---|---:|---:|---:|---:|
| mx-probe-68 | 3 | 6 | 1.1250 | entry: 15,750 × 2 |

Every settled gross in the full run is round(band ×
factor) — the scan corroborates the formula at 1.1250 from
a month with 3 rain days and 6 storm days in one pass.
The entry tier settles live at the first factor above the
old top in the only matching month (15,750 × 2). The hit
rate for the target factor is 1 in 200 by weather, 1 in 1
by driver among the matches — the month's weather is the
binding constraint, and the pre-filter makes the hunt
cheap: 200 weather reads plus 1 full run.

The surge is still corroborated at nine live factors —
1.0083, 1.0417, 1.05 (the EY month, §16), 1.0833, 1.0917,
1.1000, 1.1083, 1.1167 and 1.1250 — and the factor ladder
now extends one step above the old top: every step of
rain + 2 × storm = 1..15 has a live settlement (1.0083,
1.0167, 1.0250, 1.0333, 1.0417, 1.05, 1.0583, 1.0667,
1.0750, 1.0833, 1.0917, 1.1000, 1.1083, 1.1167, 1.1250),
with the senior tier live-settled at the floor 1.0083 and
at every step from 1.0250 to 1.1167 except 1.0750, where
no month in the record holds a senior — and now also not
at the new top step 1.1250, where no month in the record
holds a senior either. The KC section keeps printing the
EY month's weather (factor 1.05) as the canonical
scenario; the new factor is recorded here and in §16, not
printed as a second section. The pinned md5 does NOT move
— the tool's output is byte-identical (a comment only in
`economy_sim.py`); the MN baseline
`c70567cb94bd018ef50df1470fdbe746` stands, and the
`--shibnagar` md5 `95022a1592dca4d34b91f5f0a6890526`
stands.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the ladder now extends one step above
the old top, but the senior gross at the new top step
(40,500 at 1.1250) is still tool-computed only — no month
in the record holds a senior at 1.1250, and the one month
that does land on the factor holds entry drivers only. A
hunt for a senior settlement at 1.1250 with the same
weather-first pre-filter (scan fresh seeds for rain + 2 ×
storm = 15 before running the full shape) is Queue 56
Unit MY. The factor above the new top (1.1333, rain + 2 ×
storm = 16) is likewise unmeasured.

## 45. Addendum — Senior taxi settlement at 1.1250, weather-first: the hunt finds none; the mid tier settles live (Unit MY, Queue 56)

**Date:** 2026-11-27. **Method:** MX live-settled the entry
gross at the first factor above the old top (1.1250,
15,750) but the month held no senior — the senior gross at
1.1250 (40,500) is still tool-computed only, and the senior
tier above the band still rests on four live factors
(1.0917, 1.1000, 1.1083, 1.1167). Hunt with the same
weather-first pre-filter MX proved: scan 200 fresh seeds
(`my-probe-1`–`my-probe-200`) on the weather signature
alone (rain + 2 × storm = 15, the 1.1250 condition)
WITHOUT running the population, then run the full EY shape
(`Simulation`, `generate_population(60)`, 32 days) ONLY on
the matching seeds and check whether any holds a senior
taxi driver — and check the tool's formula reproduces the
settled grosses (round(band × 1.1250): entry 15,750 / mid
25,875 / senior 40,500), including the rounding rule
(settled amounts are integers; the tool must round the
same way). If the scan finds no matching weather at all, or
no matching month holds a senior, record that honestly and
stop. No invented household, no tuning call.

**Measured: the pre-filter finds two months at 1.1250,
and neither holds a senior.** The weather-only scan of 200
seeds matches exactly two — `my-probe-53` (11 rain,
day_index 0, 3, 8, 9, 10, 14, 17, 18, 20, 23, 24; 2 storm,
day_index 26, 27) and `my-probe-137` (7 rain, day_index 9,
10, 13, 16, 20, 23, 24; 4 storm, day_index 2, 14, 17, 27)
— a 1.0% hit rate for the signature, and both full EY runs
reproduce their scanned counts exactly, so the pre-filter
is itself verified a fifth time: the weather-first read
predicts the full run's month. Both months are factor `1 +
0.25 × rain/30 + 0.5 × storm/30 = 1.1250`, three taxi
drivers in all, all SYS-EMPLOYERS-paid, every settled
gross exactly round(band × 1.1250).

**Measured: the mid tier now settles live at the top
step — from two different mixes.** Seed `my-probe-53`: 11
rain days (day_index 0, 3, 8, 9, 10, 14, 17, 18, 20, 23,
24), 2 storm days (day_index 26, 27), factor 1.1250 — two
taxi drivers, both mid, both SYS-EMPLOYERS-paid, both
settled exactly at round(23,000 × 1.1250): NEX000002 and
NEX000051, 25,875 each. Seed `my-probe-137`: 7 rain days
(day_index 9, 10, 13, 16, 20, 23, 24), 4 storm days
(day_index 2, 14, 17, 27), factor 1.1250 — one taxi
driver, mid, SYS-EMPLOYERS-paid, settled exactly at
round(23,000 × 1.1250): NEX000035, 25,875. The 25,875 at
1.1250 is now a measured figure, not tool-computed — three
mid settlements at the first factor above the old top, from
two months with different mixes (11 rain + 2 storm against
7 rain + 4 storm), so the settlement keys on the factor,
not the mix, at 1.1250 too, as MR already measured at
1.1083 and MU at 1.1000. The tool's `simulate(...,
taxi_rain_days=..., taxi_storm_days=...)` grosses at 1.1250
are identical — 15,750 / 25,875 / 40,500, from either mix
— and the rounding is a no-op at every tier this time:
14,000 × 1.1250 is exactly 15,750.0, 23,000 × 1.1250 is
exactly 25,875.0, and 36,000 × 1.1250 is exactly 40,500.0,
so round() lands on the product in each case.

**Honest limit: no senior driver in either month.** Both
months hold mid drivers only, so the senior gross at
1.1250 (40,500) stays tool-computed, not live-settled — a
live senior settlement above the top is still unmeasured,
and the senior tier above the band still rests on four
live factors (1.0917, 1.1000, 1.1083, 1.1167). The driver
is the binding constraint this time, not the weather: two
months land on 1.1250 in 200 seeds, and both hold a taxi
driver — but neither holds a senior. A wider scan is the
honest next step, not a blind sweep: the pre-filter spends
the full shape only where the factor already matches (2
full runs, against MU's 24 full runs for no 1.1167 month
at all).

Single-earner taxi rows at the new factor (gross, net,
delta vs flat):

| Factor | Tier | Surged gross | Surged net | Gross delta | Net delta |
|---|---:|---:|---:|---:|---:|
| 1.1250 | entry | 15,750 | 7,601 | +1,750 | +1,101 |
| 1.1250 | mid | 25,875 | 13,675 | +2,875 | +1,725 |
| 1.1250 | senior | 40,500 | 22,425 | +4,500 | +2,675 |

**The full scan.** Two hundred fresh seeds, weather-only
pre-filter — two match rain + 2 × storm = 15:

| Seed | Rain | Storm | Factor | Drivers (band: settled) |
|---|---:|---:|---:|---:|
| my-probe-53 | 11 | 2 | 1.1250 | mid: 25,875 × 2 |
| my-probe-137 | 7 | 4 | 1.1250 | mid: 25,875 |

Every settled gross in the full runs is round(band ×
factor) — the scan corroborates the formula at 1.1250 from
two different mixes in one pass. The mid tier settles live
at the first factor above the old top in both matching
months (25,875 × 3). The hit rate for the target factor is
2 in 200 by weather, 2 in 2 by driver among the matches —
the month's weather is the binding constraint for the
factor, and the driver is the binding constraint for the
senior tier; the pre-filter makes the hunt cheap: 200
weather reads plus 2 full runs.

The surge is still corroborated at nine live factors —
1.0083, 1.0417, 1.05 (the EY month, §16), 1.0833, 1.0917,
1.1000, 1.1083, 1.1167 and 1.1250 — and the factor ladder
still extends one step above the old top: every step of
rain + 2 × storm = 1..15 has a live settlement (1.0083,
1.0167, 1.0250, 1.0333, 1.0417, 1.05, 1.0583, 1.0667,
1.0750, 1.0833, 1.0917, 1.1000, 1.1083, 1.1167, 1.1250),
with the senior tier live-settled at the floor 1.0083 and
at every step from 1.0250 to 1.1167 except 1.0750, where
no month in the record holds a senior — and still not at
the new top step 1.1250, where no month in the record
holds a senior either. At 1.1250 the entry tier is live
(MX) and the mid tier is now live (MY); only the senior
tier stays tool-computed. The KC section keeps printing
the EY month's weather (factor 1.05) as the canonical
scenario; the new factor is recorded here and in §16, not
printed as a second section. The pinned md5 does NOT move
— the tool's output is byte-identical (a comment only in
`economy_sim.py`); the MN baseline
`c70567cb94bd018ef50df1470fdbe746` stands, and the
`--shibnagar` md5 `95022a1592dca4d34b91f5f0a6890526`
stands.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the senior gross at the new top step
(40,500 at 1.1250) is still tool-computed only — no month
in the record holds a senior at 1.1250, and the two months
that do land on the factor hold mid drivers only. A hunt
for a senior settlement at 1.1250 with the same
weather-first pre-filter over a wider scan (400 fresh seeds
for rain + 2 × storm = 15 before running the full shape)
is Queue 57 Unit MZ. The factor above the new top (1.1333,
rain + 2 × storm = 16) is likewise unmeasured, and the
senior gap at 1.0750 stays recorded in §43.

## 46. Addendum — Senior taxi settlement at 1.1250, wider weather-first scan: the hunt finds none again; both lower tiers settle live from a third mix (Unit MZ, Queue 57)

**Date:** 2026-11-27. **Method:** MY hunted 200 fresh seeds
and found two months at the factor, both holding mid
drivers only — the senior gross at 1.1250 (40,500) is still
tool-computed only, and the senior tier above the band
still rests on four live factors (1.0917, 1.1000, 1.1083,
1.1167). Hunt again with the same weather-first pre-filter
MY proved, over a wider bounded scan of 400 fresh seeds
(`mz-probe-1`–`mz-probe-400`) on the weather signature
alone (rain + 2 × storm = 15, the 1.1250 condition)
WITHOUT running the population, then run the full EY shape
(`Simulation`, `generate_population(60)`, 32 days) ONLY on
the matching seeds and check whether any holds a senior
taxi driver — and check the tool's formula reproduces the
settled grosses (round(band × 1.1250): entry 15,750 / mid
25,875 / senior 40,500), including the rounding rule
(settled amounts are integers; the tool must round the
same way). If the scan finds no matching weather at all, or
no matching month holds a senior, record that honestly and
stop. No invented household, no tuning call.

**Measured: the pre-filter finds one month at 1.1250, and
it holds no senior.** The weather-only scan of 400 seeds
matches exactly one — `mz-probe-397` (7 rain, day_index 0,
1, 10, 17, 18, 22, 29; 4 storm, day_index 9, 16, 23, 25)
— a 0.25% hit rate for the signature, and the full EY run
reproduces its scanned counts exactly, so the pre-filter
is itself verified a sixth time: the weather-first read
predicts the full run's month. The month is factor `1 +
0.25 × rain/30 + 0.5 × storm/30 = 1.1250`, three taxi
drivers, all SYS-EMPLOYERS-paid, every settled gross
exactly round(band × 1.1250).

**Measured: both lower tiers settle live from a third mix
— the 7 rain + 4 storm mix, from new day positions.**
Seed `mz-probe-397`: 7 rain days (day_index 0, 1, 10, 17,
18, 22, 29), 4 storm days (day_index 9, 16, 23, 25),
factor 1.1250 — three taxi drivers, all
SYS-EMPLOYERS-paid, all settled exactly at round(band ×
1.1250): entry NEX000010, 15,750; entry NEX000058,
15,750; mid NEX000043, 25,875. The 7 rain + 4 storm mix
now has a second live instance, from different day
positions than `my-probe-137` (rain day_index 9, 10, 13,
16, 20, 23, 24; storm day_index 2, 14, 17, 27), and it
settles identically — so the settlement keys on the
counts, not the positions, at 1.1250 too, as MR already
measured at 1.1083 and MU at 1.1000. The tool's
`simulate(..., taxi_rain_days=..., taxi_storm_days=...)`
grosses at 1.1250 are identical — 15,750 / 25,875 /
40,500, from the MZ mix — and the rounding is a no-op at
every tier this time: 14,000 × 1.1250 is exactly 15,750.0,
23,000 × 1.1250 is exactly 25,875.0, and 36,000 × 1.1250
is exactly 40,500.0, so round() lands on the product in
each case.

**Honest limit: no senior driver in the one matching
month.** The month holds entry and mid drivers only, so
the senior gross at 1.1250 (40,500) stays tool-computed,
not live-settled — a live senior settlement above the top
is still unmeasured, and the senior tier above the band
still rests on four live factors (1.0917, 1.1000, 1.1083,
1.1167). The driver is the binding constraint again, not
the weather: one month lands on 1.1250 in 400 seeds, and
it holds a taxi driver — but no senior. Three hunts at the
top step now (MX, MY, MZ) have found four months at
1.1250 and not one senior among their ten drivers, while
the lower tiers keep settling: at 1.1250 the entry tier is
now live four times (MX 2 + MZ 2) and the mid tier four
times (MY 3 + MZ 1). A still-wider scan is the honest
next step, not a blind sweep: the pre-filter spends the
full shape only where the factor already matches (1 full
run, against MU's 24 full runs for no 1.1167 month at
all).

Single-earner taxi rows at the new factor (gross, net,
delta vs flat):

| Factor | Tier | Surged gross | Surged net | Gross delta | Net delta |
|---|---:|---:|---:|---:|---:|
| 1.1250 | entry | 15,750 | 7,601 | +1,750 | +1,101 |
| 1.1250 | mid | 25,875 | 13,675 | +2,875 | +1,725 |
| 1.1250 | senior | 40,500 | 22,425 | +4,500 | +2,675 |

**The full scan.** Four hundred fresh seeds, weather-only
pre-filter — one matches rain + 2 × storm = 15:

| Seed | Rain | Storm | Factor | Drivers (band: settled) |
|---|---:|---:|---:|---:|
| mz-probe-397 | 7 | 4 | 1.1250 | entry: 15,750 × 2, mid: 25,875 |

Every settled gross in the full run is round(band ×
factor) — the scan corroborates the formula at 1.1250 from
a third mix in one pass. The entry tier settles live at
the first factor above the old top in the one matching
month (15,750 × 2) and the mid tier settles live there too
(25,875). The hit rate for the target factor is 1 in 400
by weather, 1 in 1 by driver among the matches — the
month's weather is the binding constraint for the factor,
and the driver is the binding constraint for the senior
tier; the pre-filter makes the hunt cheap: 400 weather
reads plus 1 full run.

The surge is still corroborated at nine live factors —
1.0083, 1.0417, 1.05 (the EY month, §16), 1.0833, 1.0917,
1.1000, 1.1083, 1.1167 and 1.1250 — and the factor ladder
still extends one step above the old top: every step of
rain + 2 × storm = 1..15 has a live settlement (1.0083,
1.0167, 1.0250, 1.0333, 1.0417, 1.05, 1.0583, 1.0667,
1.0750, 1.0833, 1.0917, 1.1000, 1.1083, 1.1167, 1.1250),
with the senior tier live-settled at the floor 1.0083 and
at every step from 1.0250 to 1.1167 except 1.0750, where
no month in the record holds a senior — and still not at
the new top step 1.1250, where no month in the record
holds a senior either. At 1.1250 the entry tier is live
(MX) and the mid tier is live (MY), now both four times
over; only the senior tier stays tool-computed. The KC
section keeps printing the EY month's weather (factor
1.05) as the canonical scenario; the new factor is
recorded here and in §16, not printed as a second
section. The pinned md5 does NOT move — the tool's
output is byte-identical (a comment only in
`economy_sim.py`); the MN baseline
`c70567cb94bd018ef50df1470fdbe746` stands, and the
`--shibnagar` md5 `95022a1592dca4d34b91f5f0a6890526`
stands.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the senior gross at the new top step
(40,500 at 1.1250) is still tool-computed only — no month
in the record holds a senior at 1.1250, and the three
months that do land on the factor hold entry and mid
drivers only. A hunt for a senior settlement at 1.1250
with the same weather-first pre-filter over a still-wider
scan (800 fresh seeds for rain + 2 × storm = 15 before
running the full shape) is Queue 58 Unit NA. The factor
above the new top (1.1333, rain + 2 × storm = 16) is
likewise unmeasured, and the senior gap at 1.0750 stays
recorded in §43.

## 47. Addendum — Senior taxi settlement at 1.1250, still-wider weather-first scan: the senior settles live at last; all three tiers live at the top step (Unit NA, Queue 58)

**Date:** 2026-11-27. **Method:** MZ hunted 400 fresh seeds
and found one month at the factor holding entry and mid
drivers only — the senior gross at 1.1250 (40,500) is still
tool-computed only, and the senior tier above the band
still rests on four live factors (1.0917, 1.1000, 1.1083,
1.1167). Hunt again with the same weather-first pre-filter
MZ proved, over a still-wider bounded scan of 800 fresh
seeds (`na-probe-1`–`na-probe-800`) on the weather
signature alone (rain + 2 × storm = 15, the 1.1250
condition) WITHOUT running the population, then run the
full EY shape (`Simulation`, `generate_population(60)`, 32
days) ONLY on the matching seeds and check whether any
holds a senior taxi driver — and check the tool's formula
reproduces the settled grosses (round(band × 1.1250):
entry 15,750 / mid 25,875 / senior 40,500), including the
rounding rule (settled amounts are integers; the tool must
round the same way). If the scan finds no matching weather
at all, or no matching month holds a senior, record that
honestly and stop. No invented household, no tuning call.

**Measured: the pre-filter finds ten months at 1.1250,
and one holds a senior.** The weather-only scan of 800
seeds matches exactly ten — a 1.25% hit rate for the
signature, across five mixes — and every full EY run
reproduces its scanned counts exactly, so the pre-filter
is itself verified a seventh time: the weather-first read
predicts the full run's month. All ten months are factor
`1 + 0.25 × rain/30 + 0.5 × storm/30 = 1.1250`, nineteen
taxi drivers in all, all SYS-EMPLOYERS-paid, every
settled gross exactly round(band × 1.1250).

**Measured: the senior settles live at last — from the
3 rain + 6 storm mix, in the richest month of the hunt.**
Seed `na-probe-129`: 3 rain days (day_index 10, 18, 21),
6 storm days (day_index 0, 17, 19, 24, 26, 29), factor
1.1250 — four taxi drivers, all SYS-EMPLOYERS-paid, all
settled exactly at round(band × 1.1250): entry NEX000058,
15,750; mid NEX000001, 25,875; mid NEX000050, 25,875;
senior NEX000043, 40,500. This is the only month in the
record at 1.1250 holding a senior, and the only month
holding all three tiers — so the senior gross at 1.1250
(40,500) is now live-settled, not tool-computed, and the
senior tier above the band now rests on five live factors
(1.0917, 1.1000, 1.1083, 1.1167, 1.1250). The other nine
months settle the lower tiers: one entry (15,750) and
seventeen mid (25,875), all SYS-EMPLOYERS-paid. The tool's
`simulate(..., taxi_rain_days=..., taxi_storm_days=...)`
grosses at 1.1250 are identical — 15,750 / 25,875 /
40,500, from the NA mix — and the rounding is a no-op at
every tier this time: 14,000 × 1.1250 is exactly 15,750.0,
23,000 × 1.1250 is exactly 25,875.0, and 36,000 × 1.1250
is exactly 40,500.0, so round() lands on the product in
each case.

**Measured: the lower tiers settle live from four new
mixes — and the 7 rain + 4 storm mix has a third live
instance.** The ten months land on 1.1250 from five mixes:
9 rain + 3 storm (`na-probe-34`, `na-probe-93`), 3 rain +
6 storm (`na-probe-98`, `na-probe-129`, `na-probe-439`), 7
rain + 4 storm (`na-probe-311`), 5 rain + 5 storm
(`na-probe-341`, `na-probe-389`, `na-probe-660`), and 11
rain + 2 storm (`na-probe-788`) — and every one settles
identically at round(band × 1.1250), so the settlement
keys on the factor, not the mix, at 1.1250 too, as MR
already measured at 1.1083 and MU at 1.1000. The 7 rain +
4 storm mix now has a third live instance
(`na-probe-311`: three mid drivers, rain day_index 0, 4, 7,
12, 15, 18, 21; storm day_index 3, 6, 10, 22), from
different day positions than `mz-probe-397` (rain day_index
0, 1, 10, 17, 18, 22, 29; storm day_index 9, 16, 23, 25)
and `my-probe-137` (rain day_index 9, 10, 13, 16, 20, 23,
24; storm day_index 2, 14, 17, 27) — so the settlement
keys on the counts, not the positions, at 1.1250 too. At
1.1250 the entry tier is now live five times (MX 2 + MZ 2
+ NA 1), the mid tier twenty-one times (MY 3 + MZ 1 + NA
17), and the senior tier once (NA) — all three tiers are
live at the top step.

Single-earner taxi rows at the new factor (gross, net,
delta vs flat):

| Factor | Tier | Surged gross | Surged net | Gross delta | Net delta |
|---|---:|---:|---:|---:|---:|
| 1.1250 | entry | 15,750 | 7,601 | +1,750 | +1,101 |
| 1.1250 | mid | 25,875 | 13,675 | +2,875 | +1,725 |
| 1.1250 | senior | 40,500 | 22,425 | +4,500 | +2,675 |

**The full scan.** Eight hundred fresh seeds, weather-only
pre-filter — ten match rain + 2 × storm = 15:

| Seed | Rain | Storm | Factor | Drivers (band: settled) |
|---|---:|---:|---:|---:|
| na-probe-34 | 9 | 3 | 1.1250 | mid: 25,875 |
| na-probe-93 | 9 | 3 | 1.1250 | mid: 25,875 |
| na-probe-98 | 3 | 6 | 1.1250 | mid: 25,875 × 2 |
| na-probe-129 | 3 | 6 | 1.1250 | entry: 15,750, mid: 25,875 × 2, senior: 40,500 |
| na-probe-311 | 7 | 4 | 1.1250 | mid: 25,875 × 3 |
| na-probe-341 | 5 | 5 | 1.1250 | mid: 25,875 × 2 |
| na-probe-389 | 5 | 5 | 1.1250 | mid: 25,875 × 2 |
| na-probe-439 | 3 | 6 | 1.1250 | mid: 25,875 |
| na-probe-660 | 5 | 5 | 1.1250 | mid: 25,875 |
| na-probe-788 | 11 | 2 | 1.1250 | mid: 25,875 × 2 |

Every settled gross in the full runs is round(band ×
factor) — the scan corroborates the formula at 1.1250 from
five mixes in one pass. The senior tier settles live at
the first factor above the old top in the one matching
month that holds a senior (40,500, `na-probe-129`), and
the entry and mid tiers settle live there too (15,750;
25,875 × 17). The hit rate for the target factor is 10 in
800 by weather, 10 in 10 by driver among the matches — the
month's weather is the binding constraint for the factor,
and the driver was the binding constraint for the senior
tier until this scan; the pre-filter makes the hunt cheap:
800 weather reads plus 10 full runs.

The surge is still corroborated at nine live factors —
1.0083, 1.0417, 1.05 (the EY month, §16), 1.0833, 1.0917,
1.1000, 1.1083, 1.1167 and 1.1250 — and the factor ladder
still extends one step above the old top: every step of
rain + 2 × storm = 1..15 has a live settlement (1.0083,
1.0167, 1.0250, 1.0333, 1.0417, 1.05, 1.0583, 1.0667,
1.0750, 1.0833, 1.0917, 1.1000, 1.1083, 1.1167, 1.1250),
with the senior tier now live-settled at the floor 1.0083
and at every step from 1.0250 to 1.1250 except 1.0750,
where no month in the record holds a senior. At 1.1250 all
three tiers are live — entry five times, mid twenty-one
times, senior once. The KC section keeps printing the EY
month's weather (factor 1.05) as the canonical scenario;
the new factor is recorded here and in §16, not printed
as a second section. The pinned md5 does NOT move — the
tool's output is byte-identical (a comment only in
`economy_sim.py`); the MN baseline
`c70567cb94bd018ef50df1470fdbe746` stands, and the
`--shibnagar` md5 `95022a1592dca4d34b91f5f0a6890526`
stands.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the senior gap at 1.0750 is now the
last in-ladder senior gap — no month in the record holds
a senior at 1.0750, and the senior tier is live at every
other step from the floor to the new top. A hunt for a
senior settlement at 1.0750 with the same weather-first
pre-filter (a bounded sweep on rain + 2 × storm = 9
before running the full shape) is Queue 59 Unit NB. The
factor above the new top (1.1333, rain + 2 × storm = 16)
is likewise unmeasured.

## 48. Addendum — Senior taxi settlement at 1.0750, weather-first: the senior was already live; the hunt finds two more, and the record is corrected (Unit NB, Queue 59)

**Date:** 2026-11-27. **Method:** NA live-settled the
senior gross at the top step (1.1250, 40,500) but left
1.0750 recorded as the last in-ladder senior gap — no
month in the record holds a senior at 1.0750, while the
senior tier is live at the floor 1.0083 and at every step
from 1.0250 to 1.1250. Hunt with the same weather-first
pre-filter NA proved: scan 24 fresh seeds
(`nb-probe-1`–`nb-probe-24`) on the weather signature
alone (rain + 2 × storm = 9, the 1.0750 condition) WITHOUT
running the population, then run the full EY shape
(`Simulation`, `generate_population(60)`, 32 days) ONLY on
the matching seeds and check whether any holds a senior
taxi driver — and check the tool's formula reproduces the
settled grosses (round(band × 1.0750): entry 15,050 / mid
24,725 / senior 38,700), including the rounding rule
(settled amounts are integers; the tool must round the
same way). If the scan finds no matching weather at all,
or no matching month holds a senior, record that honestly
and stop. No invented household, no tuning call.

**Measured: the pre-filter finds nine months at 1.0750,
and two hold a senior.** The weather-only scan of 24
seeds matches exactly nine — a 37.5% hit rate for the
signature, across three mixes — and every full EY run
reproduces its scanned counts exactly, so the pre-filter
is itself verified an eighth time: the weather-first read
predicts the full run's month. All nine months are factor
`1 + 0.25 × rain/30 + 0.5 × storm/30 = 1.0750`,
twenty-seven taxi drivers in all, all SYS-EMPLOYERS-paid,
every settled gross exactly round(band × 1.0750).

**Measured: the senior settles live, twice — from the
7 rain + 1 storm mix, at different day positions.** Seed
`nb-probe-2`: 7 rain days (day_index 5, 11, 17, 21, 24,
25, 29), 1 storm day (day_index 26), factor 1.0750 —
three taxi drivers, all SYS-EMPLOYERS-paid, all settled
exactly at round(band × 1.0750): entry NEX000019, 15,050;
entry NEX000056, 15,050; senior NEX000007, 38,700. Seed
`nb-probe-15`: 7 rain days (day_index 0, 5, 8, 12, 13, 20,
22), 1 storm day (day_index 4), factor 1.0750 — five taxi
drivers, all SYS-EMPLOYERS-paid, all settled exactly at
round(band × 1.0750): entry NEX000036, 15,050; mid
NEX000001, 24,725; mid NEX000026, 24,725; mid NEX000056,
24,725; senior NEX000048, 38,700. Both senior months come
from the same 7 rain + 1 storm mix but from different day
positions, so the settlement keys on the counts, not the
positions, at 1.0750 too. `nb-probe-15` holds all three
tiers — the month at 1.0750 holding all three tiers — and
`nb-probe-23` (9 rain, 0 storm) is the first live 9 rain +
0 storm month at 1.0750. The other seven months settle
the lower tiers: seven entry (15,050) and eighteen mid
(24,725) in all across the nine months, all
SYS-EMPLOYERS-paid. The tool's `simulate(...,
taxi_rain_days=..., taxi_storm_days=...)` grosses at
1.0750 are identical — 15,050 / 24,725 / 38,700, from all
three NB mixes — and the rounding is a no-op at every
tier: 14,000 × 1.0750 is exactly 15,050.0, 23,000 ×
1.0750 is exactly 24,725.0, and 36,000 × 1.0750 is exactly
38,700.0 from the 7/1 and 9/0 mixes, while from the 5/2
mix the products sit a float epsilon above the integer
(15,050.000000000002, 24,725.000000000004,
38,700.00000000001) with round() landing on them — the
same shape as MU at 1.1000.

**CORRECTED: there was no gap — the senior at 1.0750 was
already live.** The draft's premise ("no month in the
record holds a senior at 1.0750") and the "last in-ladder
senior gap" claim carried from MW §43 through NA §47 were
wrong: the report's own sweep tables already held two
senior settlements at 1.0750 — `ms-probe-8` (MS, Queue 50,
§39 table: 7 rain + 1 storm, senior NEX000034, 38,700)
and `mu-probe-14` (MU, Queue 52, §41 table: 5 rain + 2
storm, senior NEX000007, 38,700, with mid NEX000015,
NEX000036 and NEX000045 at 24,725 each) — but the MS/MU
verify scripts only re-derived their headline seeds
(`ms-probe-11`/`ms-probe-7`, `mu-probe-3`/`mu-probe-8`/
`mu-probe-16`), so the 1.0750 seniors were never
highlighted in the §16 prose chain, and the MW–NA
summaries — which read the prose, not the tables —
recorded a gap that did not exist. NB re-derives all five
prior 1.0750 months live and every one reproduces its
recorded row exactly: `ms-probe-8` (senior NEX000034,
38,700), `mt-probe-10` (3 rain + 3 storm; mid NEX000005,
NEX000015, NEX000029 and NEX000034, 24,725 each),
`mt-probe-22` (7 rain + 1 storm; mid NEX000001, 24,725),
`mu-probe-2` (3 rain + 3 storm; entry NEX000018 and
NEX000043, 15,050 each; mid NEX000058, 24,725) and
`mu-probe-14` (senior NEX000007, 38,700; mid NEX000015,
NEX000036 and NEX000045, 24,725 each). The correction is
measured, not asserted: before NB the tiers at 1.0750
were already live entry twice, mid nine times, senior
twice, and after NB they are live entry nine times
(prior 2 + NB 7), mid twenty-seven times (prior 9 + NB
18), senior four times (prior 2 + NB 2). The senior tier
is now live at every step of the ladder from the floor
1.0083 to the top 1.1250 except 1.0167 — the only
remaining in-ladder senior gap (`ms-probe-12`,
`ms-probe-13` and `mt-probe-8` hold entry and mid only).
The lesson is recorded for later hunts: a gap claim must
be checked against the sweep tables, not only the §16
prose — the tables are the record, and the prose is a
summary of it.

Single-earner taxi rows at the new factor (gross, net,
delta vs flat):

| Factor | Tier | Surged gross | Surged net | Gross delta | Net delta |
|---|---:|---:|---:|---:|---:|
| 1.0750 | entry | 15,050 | 7,180 | +1,050 | +680 |
| 1.0750 | mid | 24,725 | 12,985 | +1,725 | +1,035 |
| 1.0750 | senior | 38,700 | 21,370 | +2,700 | +1,620 |

**The full scan.** Twenty-four fresh seeds, weather-only
pre-filter — nine match rain + 2 × storm = 9:

| Seed | Rain | Storm | Factor | Drivers (band: settled) |
|---|---:|---:|---:|---:|
| nb-probe-2 | 7 | 1 | 1.0750 | entry: 15,050 × 2, senior: 38,700 |
| nb-probe-4 | 7 | 1 | 1.0750 | mid: 24,725 × 3 |
| nb-probe-5 | 5 | 2 | 1.0750 | entry: 15,050, mid: 24,725 × 2 |
| nb-probe-6 | 5 | 2 | 1.0750 | entry: 15,050 |
| nb-probe-7 | 5 | 2 | 1.0750 | entry: 15,050, mid: 24,725 × 3 |
| nb-probe-10 | 5 | 2 | 1.0750 | entry: 15,050, mid: 24,725 |
| nb-probe-11 | 7 | 1 | 1.0750 | mid: 24,725 × 3 |
| nb-probe-15 | 7 | 1 | 1.0750 | entry: 15,050, mid: 24,725 × 3, senior: 38,700 |
| nb-probe-23 | 9 | 0 | 1.0750 | mid: 24,725 × 3 |

Every settled gross in the full runs is round(band ×
factor) — the scan corroborates the formula at 1.0750 from
three mixes in one pass. The senior tier settles live at
1.0750 twice more in this hunt (38,700, `nb-probe-2` and
`nb-probe-15`), and twice already in the record
(`ms-probe-8`, `mu-probe-14`) — four live senior
settlements at 1.0750 in all. The hit rate for the target
factor is 9 in 24 by weather, 9 in 9 by driver among the
matches — the month's weather is the binding constraint
for the factor, and the driver was never the binding
constraint for the senior tier at 1.0750; the pre-filter
makes the hunt cheap: 24 weather reads plus 9 full runs,
plus 5 full runs re-deriving the prior months for the
correction.

The surge is still corroborated at nine live factors —
1.0083, 1.0417, 1.05 (the EY month, §16), 1.0833, 1.0917,
1.1000, 1.1083, 1.1167 and 1.1250 — and the factor ladder
still extends one step above the old top: every step of
rain + 2 × storm = 1..15 has a live settlement (1.0083,
1.0167, 1.0250, 1.0333, 1.0417, 1.05, 1.0583, 1.0667,
1.0750, 1.0833, 1.0917, 1.1000, 1.1083, 1.1167, 1.1250),
with the senior tier now live at every step except 1.0167.
At 1.0750 all three tiers are live — entry nine times, mid
twenty-seven times, senior four times. The KC section
keeps printing the EY month's weather (factor 1.05) as the
canonical scenario; the new factor is recorded here and in
§16, not printed as a second section. The pinned md5 does
NOT move — the tool's output is byte-identical (a comment
only in `economy_sim.py`); the MN baseline
`c70567cb94bd018ef50df1470fdbe746` stands, and the
`--shibnagar` md5 `95022a1592dca4d34b91f5f0a6890526`
stands.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the senior gap at 1.0167 is now the
only remaining in-ladder senior gap — no month in the
record holds a senior at 1.0167, and the senior tier is
live at every other step from the floor to the new top. A
hunt for a senior settlement at 1.0167 with the same
weather-first pre-filter (a bounded sweep on rain + 2 ×
storm = 2 before running the full shape) is Queue 60 Unit
NC — feasibility checked: 12 of 800 fresh seeds match the
signature, all 2 rain + 0 storm (`nc-probe-21`,
`nc-probe-306`, `nc-probe-339`, `nc-probe-472`,
`nc-probe-517`, `nc-probe-525`, `nc-probe-588`,
`nc-probe-597`, `nc-probe-620`, `nc-probe-629`,
`nc-probe-759`, `nc-probe-780`); the tool's figures there
are entry 14,233 / mid 23,383 / senior 36,600 (gross
deltas +233 / +383 / +600), with the rounding going down
at both lower tiers and a no-op at the senior tier. The
factor above the new top (1.1333, rain + 2 × storm = 16)
is likewise unmeasured — feasibility checked: 0 of 200
fresh seeds match the signature, but 6 of 1,000 do, so a
wider scan would be needed (the seed names for that hunt
are set when it is drafted, not here).

## 49. Addendum — Senior taxi settlement at 1.0167, weather-first: the senior settles live at last; the ladder is closed (Unit NC, Queue 60)

**Date:** 2026-11-27. **Method:** NB corrected the record
at 1.0750 and left 1.0167 as the only remaining in-ladder
senior gap — no month in the record holds a senior at
1.0167, while the senior tier is live at the floor 1.0083
and at every other step to the top 1.1250. Hunt with the
same weather-first pre-filter NB proved: scan 800 fresh
seeds (`nc-probe-1`–`nc-probe-800`) on the weather
signature alone (rain + 2 × storm = 2, the 1.0167
condition) WITHOUT running the population, then run the
full EY shape (`Simulation`, `generate_population(60)`,
32 days) ONLY on the matching seeds and check whether
any holds a senior taxi driver — and check the tool's
formula reproduces the settled grosses (round(band ×
1.0167): entry 14,233 / mid 23,383 / senior 36,600),
including the rounding rule (settled amounts are
integers; the tool must round the same way). First check
the gap claim against the sweep tables, per the NB
lesson: re-derive the three prior 1.0167 months live
(`ms-probe-12`, `ms-probe-13`, `mt-probe-8`) before
trusting the prose. If the scan finds no matching
weather at all, or no matching month holds a senior,
record that honestly and stop. No invented household, no
tuning call.

**Measured: the pre-filter finds twelve months at 1.0167,
and five hold a senior.** The weather-only scan of 800
seeds matches exactly twelve — a 1.5% hit rate for the
signature, all from the single 2 rain + 0 storm mix at
twelve different day positions — and every full EY run
reproduces its scanned counts exactly, so the pre-filter
is itself verified a ninth time: the weather-first read
predicts the full run's month. All twelve months are
factor `1 + 0.25 × rain/30 + 0.5 × storm/30 = 1.0167`,
thirty-eight taxi drivers in all, all SYS-EMPLOYERS-paid,
every settled gross exactly round(band × 1.0167).

**Measured: the senior settles live, six times — from the
2 rain + 0 storm mix, at different day positions.** Seed
`nc-probe-306`: 2 rain days (day_index 20, 23), 0 storm
days, factor 1.0167 — four taxi drivers, all
SYS-EMPLOYERS-paid, all settled exactly at round(band ×
1.0167): mid NEX000006, 23,383; mid NEX000026, 23,383;
mid NEX000030, 23,383; senior NEX000022, 36,600. Seed
`nc-probe-472`: 2 rain days (day_index 25, 28), 0 storm
days, factor 1.0167 — two taxi drivers, all
SYS-EMPLOYERS-paid, all settled exactly at round(band ×
1.0167): entry NEX000051, 14,233; senior NEX000025,
36,600. Seed `nc-probe-525`: 2 rain days (day_index 8,
22), 0 storm days, factor 1.0167 — four taxi drivers, all
SYS-EMPLOYERS-paid, all settled exactly at round(band ×
1.0167): mid NEX000041, 23,383; mid NEX000049, 23,383;
senior NEX000029, 36,600; senior NEX000030, 36,600 — the
only month in the record at 1.0167 holding two seniors.
Seed `nc-probe-597`: 2 rain days (day_index 21, 24), 0
storm days, factor 1.0167 — five taxi drivers, all
SYS-EMPLOYERS-paid, all settled exactly at round(band ×
1.0167): entry NEX000048, 14,233; mid NEX000010, 23,383;
mid NEX000021, 23,383; mid NEX000056, 23,383; senior
NEX000049, 36,600. Seed `nc-probe-629`: 2 rain days
(day_index 13, 16), 0 storm days, factor 1.0167 — three
taxi drivers, all SYS-EMPLOYERS-paid, all settled exactly
at round(band × 1.0167): entry NEX000007, 14,233; mid
NEX000051, 23,383; senior NEX000026, 36,600. All five
senior months come from the same 2 rain + 0 storm mix but
from different day positions, so the settlement keys on
the counts, not the positions, at 1.0167 too.
`nc-probe-597` and `nc-probe-629` each hold all three
tiers — the months at 1.0167 holding all three tiers. The
other seven months settle the lower tiers: seven entry
(14,233) and twenty-five mid (23,383) in all across the
twelve months, all SYS-EMPLOYERS-paid. The tool's
`simulate(..., taxi_rain_days=..., taxi_storm_days=...)`
grosses at 1.0167 are identical — 14,233 / 23,383 /
36,600, from both 1.0167 mixes (2/0 and 0/1) — and the
rounding goes down at both lower tiers: 14,000 × 1.0167
is 14233.333333333332 and 23,000 × 1.0167 is
23383.333333333332, both rounding down, while 36,000 ×
1.0167 is exactly 36600.0, so the rounding is a no-op at
the senior tier — the mirror of MV's down at 1.1167, and
the first factor where the lower tiers round down while
the senior product stays exact.

**The gap was real — the three prior 1.0167 months hold
no senior.** NB's lesson says a gap claim must be
checked against the sweep tables, not only the §16 prose
— the tables are the record, and the prose is a summary
of it. NC re-derives all three prior 1.0167 months live
and every one reproduces its recorded row exactly:
`ms-probe-12` (MS, Queue 50, §39 table: 0 rain + 1 storm,
storm day_index 1; entry NEX000008 and NEX000021, 14,233
each; mid NEX000020 and NEX000037, 23,383 each),
`ms-probe-13` (§39 table: 2 rain + 0 storm, rain
day_index 6, 23; entry NEX000012, 14,233; mid NEX000040,
23,383) and `mt-probe-8` (MT, Queue 51, §40 table: 2 rain
+ 0 storm, rain day_index 3, 28; mid NEX000044, 23,383).
Unlike NB's correction at 1.0750 — where the tables
already held the seniors the prose denied — the 1.0167
tables hold no senior at all, so the gap NC hunted was
real and the hunt closes it: before NC the tiers at
1.0167 were live entry three times, mid four times,
senior never, and after NC they are live entry ten times
(prior 3 + NC 7), mid twenty-nine times (prior 4 + NC
25), senior six times (prior 0 + NC 6). The senior tier
is now live at every step of the ladder from the floor
1.0083 to the top 1.1250 — no in-ladder senior gap
remains.

Single-earner taxi rows at the new factor (gross, net,
delta vs flat):

| Factor | Tier | Surged gross | Surged net | Gross delta | Net delta |
|---|---:|---:|---:|---:|---:|
| 1.0167 | entry | 14,233 | 6,651 | +233 | +151 |
| 1.0167 | mid | 23,383 | 12,180 | +383 | +230 |
| 1.0167 | senior | 36,600 | 20,110 | +600 | +360 |

**The full scan.** Eight hundred fresh seeds,
weather-only pre-filter — twelve match rain + 2 × storm
= 2:

| Seed | Rain | Storm | Factor | Drivers (band: settled) |
|---|---:|---:|---:|---:|
| nc-probe-21 | 2 | 0 | 1.0167 | entry: 14,233 × 2, mid: 23,383 × 2 |
| nc-probe-306 | 2 | 0 | 1.0167 | mid: 23,383 × 3, senior: 36,600 |
| nc-probe-339 | 2 | 0 | 1.0167 | mid: 23,383 × 3 |
| nc-probe-472 | 2 | 0 | 1.0167 | entry: 14,233, senior: 36,600 |
| nc-probe-517 | 2 | 0 | 1.0167 | mid: 23,383 × 2 |
| nc-probe-525 | 2 | 0 | 1.0167 | mid: 23,383 × 2, senior: 36,600 × 2 |
| nc-probe-588 | 2 | 0 | 1.0167 | entry: 14,233, mid: 23,383 × 2 |
| nc-probe-597 | 2 | 0 | 1.0167 | entry: 14,233, mid: 23,383 × 3, senior: 36,600 |
| nc-probe-620 | 2 | 0 | 1.0167 | mid: 23,383 × 3 |
| nc-probe-629 | 2 | 0 | 1.0167 | entry: 14,233, mid: 23,383, senior: 36,600 |
| nc-probe-759 | 2 | 0 | 1.0167 | mid: 23,383 × 3 |
| nc-probe-780 | 2 | 0 | 1.0167 | entry: 14,233, mid: 23,383 |

Every settled gross in the full runs is round(band ×
factor) — the scan corroborates the formula at 1.0167
from a single mix at twelve day positions in one pass.
The senior tier settles live at 1.0167 six times in this
hunt (36,600, `nc-probe-306`, `nc-probe-472`,
`nc-probe-525` × 2, `nc-probe-597` and `nc-probe-629`),
and never before in the record — six live senior
settlements at 1.0167 in all. The hit rate for the target
factor is 12 in 800 by weather, 12 in 12 by driver among
the matches — the month's weather is the binding
constraint for the factor, and the driver was the binding
constraint for the senior tier at 1.0167 until this hunt;
the pre-filter makes the hunt cheap: 800 weather reads
plus 12 full runs, plus 3 full runs re-deriving the prior
months for the gap check.

The surge is still corroborated at nine live factors —
1.0083, 1.0417, 1.05 (the EY month, §16), 1.0833, 1.0917,
1.1000, 1.1083, 1.1167 and 1.1250 — and the factor ladder
still extends one step above the old top: every step of
rain + 2 × storm = 1..15 has a live settlement (1.0083,
1.0167, 1.0250, 1.0333, 1.0417, 1.05, 1.0583, 1.0667,
1.0750, 1.0833, 1.0917, 1.1000, 1.1083, 1.1167, 1.1250),
with the senior tier now live at every step — the
in-ladder senior gap chain that MW opened is closed. At
1.0167 all three tiers are live — entry ten times, mid
twenty-nine times, senior six times. The KC section
keeps printing the EY month's weather (factor 1.05) as
the canonical scenario; the new factor is recorded here
and in §16, not printed as a second section. The pinned
md5 does NOT move — the tool's output is byte-identical
(a comment only in `economy_sim.py`); the MN baseline
`c70567cb94bd018ef50df1470fdbe746` stands, and the
`--shibnagar` md5 `95022a1592dca4d34b91f5f0a6890526`
stands.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the senior tier is now live at every
step of the ladder from the floor to the top, so no
in-ladder senior gap remains. The only unmeasured factor
is above the top (1.1333, rain + 2 × storm = 16) — a
hunt for a senior settlement at 1.1333 with the same
weather-first pre-filter is Queue 61 Unit ND —
feasibility checked: 6 of 1,000 fresh seeds match the
signature (`nd-probe-68`, `nd-probe-165`,
`nd-probe-190`, `nd-probe-270`, `nd-probe-650`,
`nd-probe-792`); the tool's figures there are entry
15,867 / mid 26,067 / senior 40,800 (gross deltas +1,867
/ +3,067 / +4,800), with the rounding going up at both
lower tiers and a no-op at the senior tier.

## 50. Addendum — Senior taxi settlement at 1.1333, weather-first: the senior settles live above the top; the ladder extends one step (Unit ND, Queue 61)

**Date:** 2026-11-27. **Method:** NC closed the ladder —
the senior tier is live at every step from the floor
1.0083 to the top 1.1250, no in-ladder senior gap remains
— so the next honest step is the factor above the new top
(1.1333, rain + 2 × storm = 16, recorded in V7 §48):
no month in the record holds a settlement at 1.1333 at
any tier. Hunt with the same weather-first pre-filter NC
proved: scan 800 fresh seeds (`nd-probe-1`–`nd-probe-800`)
on the weather signature alone (rain + 2 × storm = 16)
WITHOUT running the population, then run the full EY
shape (`Simulation`, `generate_population(60)`, 32 days)
ONLY on the matching seeds and check whether any holds a
senior taxi driver — and check the tool's formula
reproduces the settled grosses (round(band × 1.1333):
entry 15,867 / mid 26,067 / senior 40,800), including the
rounding rule (settled amounts are integers; the tool must
round the same way). First check the gap claim against
the sweep tables, per the NB lesson: the factor column of
every sweep table tops out at 1.1250, and 1.1333 appears
in the report only as the factor above the top. If the
scan finds no matching weather at all, or no matching
month holds a senior, record that honestly and stop. No
invented household, no tuning call.

**Measured: the pre-filter finds six months at 1.1333,
and two hold a senior.** The weather-only scan of 800
seeds matches exactly six — a 0.75% hit rate for the
signature, across three mixes — and every full EY run
reproduces its scanned counts exactly, so the pre-filter
is itself verified a tenth time: the weather-first read
predicts the full run's month. All six months are factor
`1 + 0.25 × rain/30 + 0.5 × storm/30 = 1.1333`, fourteen
taxi drivers in all, all SYS-EMPLOYERS-paid, every
settled gross exactly round(band × 1.1333). Correction
to §49, measured: §49 wrote "feasibility checked: 6 of
1,000 fresh seeds" — the scan ND actually ran was 800
fresh seeds (`nd-probe-1`–`nd-probe-800`) and the same six
match, so the hit rate is 6 in 800 (0.75%), not 6 in
1,000; the seed list §49 named was complete — a check of
`nd-probe-801`–`nd-probe-1000` finds no further match —
only the denominator was off.

**Measured: the senior settles live, four times — from
two mixes, at different day positions.** Seed
`nd-probe-165`: 6 rain days (day_index 0, 7, 10, 21, 24,
26), 5 storm days (day_index 1, 3, 6, 8, 17), factor
1.1333 — two taxi drivers, all SYS-EMPLOYERS-paid, all
settled exactly at round(band × 1.1333): senior NEX000006,
40,800; senior NEX000007, 40,800 — the only month in the
record at 1.1333 holding two seniors from the 6 rain + 5
storm mix. Seed `nd-probe-650`: 10 rain days (day_index 0,
4, 8, 11, 14, 15, 16, 22, 27, 29), 3 storm days
(day_index 13, 17, 23), factor 1.1333 — three taxi
drivers, all SYS-EMPLOYERS-paid, all settled exactly at
round(band × 1.1333): mid NEX000002, 26,067; senior
NEX000032, 40,800; senior NEX000059, 40,800 — the second
month holding two seniors, from the 10 rain + 3 storm
mix. The two senior months come from different mixes at
different day positions, so the settlement keys on the
counts, not the positions, at 1.1333 too. The other four
months settle the lower tiers: seed `nd-probe-68`: 6 rain
days (day_index 7, 12, 19, 20, 21, 22), 5 storm days
(day_index 1, 8, 18, 24, 27), factor 1.1333 — one taxi
driver, SYS-EMPLOYERS-paid, settled exactly at round(band
× 1.1333): entry NEX000009, 15,867. Seed `nd-probe-190`:
8 rain days (day_index 3, 4, 5, 7, 13, 16, 27, 29), 4
storm days (day_index 6, 19, 22, 25), factor 1.1333 — two
taxi drivers, all SYS-EMPLOYERS-paid, all settled exactly
at round(band × 1.1333): mid NEX000011, 26,067; mid
NEX000042, 26,067. Seed `nd-probe-270`: 8 rain days
(day_index 2, 3, 4, 9, 13, 18, 19, 24), 4 storm days
(day_index 22, 23, 25, 29), factor 1.1333 — two taxi
drivers, all SYS-EMPLOYERS-paid, all settled exactly at
round(band × 1.1333): entry NEX000029, 15,867; mid
NEX000031, 26,067. Seed `nd-probe-792`: 8 rain days
(day_index 0, 2, 3, 4, 14, 26, 27, 29), 4 storm days
(day_index 8, 12, 18, 21), factor 1.1333 — four taxi
drivers, all SYS-EMPLOYERS-paid, all settled exactly at
round(band × 1.1333): mid NEX000008, 26,067; mid
NEX000014, 26,067; mid NEX000029, 26,067; mid NEX000032,
26,067. No month holds all three tiers — `nd-probe-270`
holds entry + mid, `nd-probe-650` holds mid + senior. Two
entry (15,867) and eight mid (26,067) in all across the
six months, all SYS-EMPLOYERS-paid. The tool's
`simulate(..., taxi_rain_days=..., taxi_storm_days=...)`
grosses at 1.1333 are identical from all three mixes
(6/5, 8/4, 10/3) — 15,867 / 26,067 / 40,800 — and the
rounding goes up at both lower tiers: 14,000 × 1.1333 is
15866.666666666666 and 23,000 × 1.1333 is
26066.666666666664, both rounding up, while 36,000 ×
1.1333 is exactly 40800.0, so the rounding is a no-op at
the senior tier — the mirror of NC's down at 1.0167, and
the first factor where the lower tiers round up while the
senior product stays exact.

**The gap was real — no month in the record held a
settlement at 1.1333.** NB's lesson says a gap claim must
be checked against the sweep tables, not only the §16
prose — the tables are the record, and the prose is a
summary of it. The factor column of every sweep table in
this report tops out at 1.1250 (the MX/MY/MZ/NA tables,
§44–§47), and the only 1.1333 mentions before ND are the
"factor above the top" prose in §48/§49 — no table row
holds a settlement at 1.1333 at any tier, so the gap ND
hunted was real and the hunt closes it: before ND the
tiers at 1.1333 were live entry never, mid never, senior
never, and after ND they are live entry twice, mid eight
times, senior four times. The senior tier is now live at
every step of the ladder from the floor 1.0083 to the top
1.1250 and one step above it.

Single-earner taxi rows at the new factor (gross, net,
delta vs flat):

| Factor | Tier | Surged gross | Surged net | Gross delta | Net delta |
|---|---:|---:|---:|---:|---:|
| 1.1333 | entry | 15,867 | 7,671 | +1,867 | +1,171 |
| 1.1333 | mid | 26,067 | 13,791 | +3,067 | +1,841 |
| 1.1333 | senior | 40,800 | 22,590 | +4,800 | +2,840 |

**The full scan.** Eight hundred fresh seeds,
weather-only pre-filter — six match rain + 2 × storm
= 16:

| Seed | Rain | Storm | Factor | Drivers (band: settled) |
|---|---:|---:|---:|---:|
| nd-probe-68 | 6 | 5 | 1.1333 | entry: 15,867 |
| nd-probe-165 | 6 | 5 | 1.1333 | senior: 40,800 × 2 |
| nd-probe-190 | 8 | 4 | 1.1333 | mid: 26,067 × 2 |
| nd-probe-270 | 8 | 4 | 1.1333 | entry: 15,867, mid: 26,067 |
| nd-probe-650 | 10 | 3 | 1.1333 | mid: 26,067, senior: 40,800 × 2 |
| nd-probe-792 | 8 | 4 | 1.1333 | mid: 26,067 × 4 |

Every settled gross in the full runs is round(band ×
factor) — the scan corroborates the formula at 1.1333
from three mixes at six day positions in one pass. The
senior tier settles live at 1.1333 four times in this
hunt (40,800, `nd-probe-165` × 2 and `nd-probe-650` × 2),
and never before in the record — four live senior
settlements at 1.1333 in all. The hit rate for the target
factor is 6 in 800 by weather, 6 in 6 by driver among
the matches — the month's weather is the binding
constraint for the factor, and the driver was the binding
constraint for the senior tier at 1.1333 until this hunt;
the pre-filter makes the hunt cheap: 800 weather reads
plus 6 full runs.

The surge is still corroborated at nine live factors —
1.0083, 1.0417, 1.05 (the EY month, §16), 1.0833, 1.0917,
1.1000, 1.1083, 1.1167 and 1.1250 — and the factor ladder
now extends one step above the old top: every step of
rain + 2 × storm = 1..16 has a live settlement (1.0083,
1.0167, 1.0250, 1.0333, 1.0417, 1.05, 1.0583, 1.0667,
1.0750, 1.0833, 1.0917, 1.1000, 1.1083, 1.1167, 1.1250,
1.1333), with the senior tier now live at every step
including the new one above the top. At 1.1333 all three
tiers are live — entry twice, mid eight times, senior
four times. The KC section keeps printing the EY month's
weather (factor 1.05) as the canonical scenario; the new
factor is recorded here and in §16, not printed as a
second section. The pinned md5 does NOT move — the
tool's output is byte-identical (a comment only in
`economy_sim.py`); the MN baseline
`c70567cb94bd018ef50df1470fdbe746` stands, and the
`--shibnagar` md5 `95022a1592dca4d34b91f5f0a6890526`
stands.

**No tuning call.** Nothing in the data moves.

**Open, recorded:** the senior tier is now live at every
step of the ladder from the floor to the top and one step
above it. The only unmeasured factor is above the new top
(1.1417, rain + 2 × storm = 17) — a hunt for a senior
settlement at 1.1417 with the same weather-first
pre-filter is Queue 62 Unit NE — feasibility checked: 0
of 800 fresh seeds match the signature, but 4 of 2,000
fresh seeds do (`ne-probe-1117`, `ne-probe-1459`,
`ne-probe-1532`, `ne-probe-1751`), so the hunt runs over
a bounded scan of 2,000 fresh seeds; the tool's figures
there are entry 15,983 / mid 26,258 / senior 41,100
(gross deltas +1,983 / +3,258 / +5,100), with the rounding
going down at both lower tiers and a no-op at the senior
tier.
