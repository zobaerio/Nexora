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
