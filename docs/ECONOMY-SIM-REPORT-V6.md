# NEXORA — Economy Balance Simulator Report v6 (Unit EY, Queue 22)

**Date:** 2026-11-24. **Tool:** `tools/economy_sim.py` v6.
**Follow-up to:** Unit ES (Queue 21 — construction-worker day-wage pay),
whose honest limit this unit closes: "the economy balance tool
(`economy_sim.py`) still models construction-worker income as the
monthly band — its figures for this profession are stale until a
follow-up re-runs it with day-wage pay" (GDD-03 §2).

## 1. What was stale

The settlement pays construction workers per worked day
(`tools/sim/labour.py` `day_wage_due()`: worked days ×
(`wage_per_month` / 30)). The v5 balance tool modelled the
profession on its `prices.json` `pay_schedule` of `"daily"`, which
paid `(gross − tax) / 26` on days 1–26 excluding Sundays — 23 pay
days, i.e. 23/26 of the band in trajectory terms — while the
headline net still showed the full band. The trajectory and the
headline disagreed:

| Tier | v5 headline net | v5 trajectory-implied net (23 pay days) |
|---|---|---:|
| entry | 1,500 | 462 |
| mid | 4,750 | 3,135 |
| senior | 8,400 | 6,121 |

(The implied nets are computed from the v5 branch rule — 23 days ×
(band − tax)/26, less the month's costs — not re-run; the v5 tool
itself printed only the headline figures and `minbal 0`, so the
disagreement was invisible in its output. It is a trajectory
modelling error, not a data error: no headline figure was wrong.)

The v5 branch also assumed a 6-day week (Sundays off). The sim has
no Sunday rest for construction workers.

## 2. Measurements (grounding the correction)

**Scheduler count.** Instantiating the `construction_worker`
template for days 0–29 with no weather, no needs bends, no rest
days and no broken tool (`tools/sim/scheduler.py`
`instantiate()`): a work block stands on **30/30 days**. Friday
keeps the morning shift (the afternoon shift becomes leisure);
Saturday and Sunday are unmodified. A storm-free month therefore
has 30 worked days and pays exactly the band.

**Live month.** A seeded 30-day engine run (`Simulation`,
seed `ey-measure`, `generate_population(60)`) held 4 construction
workers. All four recorded **28 worked days in month 1**
(`labour.worked_days()`, month 1) and a day-wage due of **8,400
NCr** on the 9,000 entry band (28 × 9,000/30). The two lost days
were days 3 and 22 — both `storm` presets, and the scheduler's
strong-cover-seeking rule bent both work blocks home
(`outdoor_work_suspended`). No rest days and no broken tools
occurred for these workers in that month. The storm month is
weather, not a balance problem, and it is the report's scenario —
not the base table, because the tool models a normal month and
does not model which days storms fall on.

## 3. What v6 changes

- The `"daily"` schedule is now the ES day-wage model: gross =
  band × worked/30 (worked days default 30 — the
  scheduler-measured normal month), tax recomputed on that gross,
  and the pay accrues evenly at (gross − tax)/30 per day.
  `simulate()` takes an optional `day_wage_worked_days` (the
  storm scenario passes 28) and returns a new `end_balance` key —
  the trajectory's final balance, which must equal `net`.
- The default run gains a day-wage storm-month section (28 worked
  days, the measured count) for the three construction tiers.
- No other profession, rent, cost, tax rule or business P&L moves.
  The `--shibnagar` variant re-runs the same `simulate()`, so its
  construction rows carry the v6 model too (its rent effect is
  unchanged).

## 4. Verbatim output

Base table (construction rows — byte-identical to v5):

```
profession                   tier      gross    tax   rent  costs   net/mo  save%   minbal  flags
construction_worker          entry      9000      0   2500   7500     1500   16.7        0  -
construction_worker          mid       14000      0   2500   9250     4750   33.9        0  -
construction_worker          senior    20000    250   2500  11350     8400   42.0        0  -
```

New day-wage storm-month section (28 worked days):

```
day-wage storm month (Unit EY — measured 28 worked days of 30, 2 storm days suspending outdoor work):
profession                   tier      gross    tax   rent  costs   net/mo  save%   minbal  flags
construction_worker          entry      8400      0   2500   7500      900   10.7        0  -  (base net 1500, save 16.7%)
construction_worker          mid       13067      0   2500   8923     4144   31.7        0  -  (base net 4750, save 33.9%)
construction_worker          senior    18667    183   2500  10883     7601   40.7        0  -  (base net 8400, save 42.0%)
```

Full default-run md5: `9ac10779c231b7aa6120a6ff457982de` (v5:
`318c6114c143a81a579e70b39ccca8f8` — kept in
`test_no_regression.py` as history). The only diff vs v5 is the
new section; the base table, business P&L, bridge check, pacing
and all other rows are unchanged.

## 5. Verdicts

- **Normal-month figures: UNCHANGED (and that is the finding).**
  A storm-free month pays exactly the band, so the construction
  worker's headline net/rate stand: entry 1,500 / 16.7%, mid
  4,750 / 33.9%, senior 8,400 / 42.0%. The v5 headline figures
  were already the full-band figures; the correction is the
  trajectory's internal consistency (it now ends exactly at net
  for all 33 rows — pinned by a test) and the correct per-day
  rate (band/30, not band/26 on 23 days).
- **Storm month: survivable, no new flag.** Entry net falls to
  900 (10.7%) — still above the 10% TIGHT line, barely. Mid
  4,144 / 31.7%, senior 7,601 / 40.7%. No SURVIVAL FAIL, no
  TIGHT, no bridge failure (minbal 0 throughout; the reduced pay
  still covers the daily cost from day one).
- **No tuning call.** Nothing in the data moves: no wage, rent,
  cost or tax change is proposed. The storm effect is weather the
  sim already models; a month with more storm days pays less, and
  the settlement measures it per world rather than the tool
  assuming it.
- **Open, recorded:** the tool's storm scenario accrues the
  reduced pay evenly — it does not model which days storms fall
  on, so its `minbal` is the even-spread figure, not a measured
  one. Storm timing affects the real month-1 dip (a storm on day
  1 dips deeper than a storm on day 29); the settlement, which
  pays on the days actually worked, is the authority there.
