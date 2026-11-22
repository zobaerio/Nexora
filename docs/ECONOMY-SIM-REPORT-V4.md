# NEXORA — Economy Balance Simulator Report v4

**Unit AJ · Queue 7 · 2026-11-22**
**Tool:** `tools/economy_sim.py` v4 (stdlib-only Python, deterministic — verified: two consecutive default runs byte-identical, md5 `318c6114c143a81a579e70b39ccca8f8`; two consecutive `--v4` runs byte-identical, md5 `6292c3c897d85834e8d45d2913e3629b`) · **Data:** `data/prices.json` v1.3 (medical note updated) + `data/professions.json` v1.1 · **Parent documents:** `docs/ECONOMY-SIM-REPORT-V3.md` (the before-state — its base table is reproduced in §4 as the before column), `docs/GDD-03-ECONOMY-AND-PROFESSIONS.md` §12–§13 (the Queue 6/7 tuning logs), `docs/GDD-12-HEALTH.md` §6 (pharmacy / medicine pricing)
**Status:** RUN AND RECORDED. The output below is the tool's actual default output on the post-change data, unedited, plus the actual `--v4` section.

> **What Queue 7 changed, in one paragraph:** the open item the v3 report left in §5 is closed — the household medical budget line (`medical_monthly` 300/500/800, Unit AI) is now charged in the simulator's 34-row base table instead of living behind a flag. **No wage band moved. No rent tier moved.** The pinned baseline md5 is updated to the new default-run md5 with the v2 md5 kept as history in the test file, and the life-sim settlement charges the same line so the one-adult reconciliation still holds. The cost is real and is reported, not tuned away: police/entry and the renting-cab variant are now TIGHT in the base table, and pilot/entry stays at 0.8%.

---

## 1. Method (what v4 does differently)

Same 30-day household cashflow as v3 (34 rows), with one change applied to every row:

1. `simulate()` adds the household's band medical line (`living_costs_monthly.medical_monthly`, band from entry wage — the same band rule as food, utilities and clothing) to base monthly costs. Business professions are included: the line is a plain expense, tax is computed on profit/gross first, so the v3 business `ValueError` path (side-income mixing) is untouched. The `medicine_expense` keyword stays for callers modelling an *extra* episode on top; the default run charges the line exactly once, in the base.
2. `tools/sim/engine.py` `_living_costs` gains the same flat per-household `medical` line, so the reconciliation contract — "a one-adult household reduces exactly to `simulate()`" — still holds. It is flat per household like utilities and services, not scaled by household size: the economy model's single-adult line is a household average, and scaling it per head would break the contract the acceptance test pins.
3. The pinned baseline in `tools/sim/tests/test_no_regression.py` moves from the v2 md5 (`16740182867525bd659735deeb05150a`, kept in a comment as history) to the v4 default-run md5 (`318c6114c143a81a579e70b39ccca8f8`). This is a deliberate, recorded baseline change — the v3 report §5 named exactly this as the follow-up — not a silent drift: the file md5, the output md5 and the reason are all in this report.
4. The `--v3`/`--v4` section drops the four medical scenarios v3 printed (construction_worker +300, police +500, pilot +800, civil_engineer +500) — they would double-charge now that the line is in the base — and keeps the five tutoring/part-time scenarios plus the medicine-basket check. `--v3` is kept as an alias for the same section.

**File md5s:** `tools/economy_sim.py` before Queue 7 `1bd880fe2984f40e3a2b506bd40ec03e` (v3, Queue 6), after `85529d2687ca53e96cf4e819372a2e95` (v4). `tools/sim/engine.py` before Queue 7 `10816249fb206abe4359d28ded9d3db7`, after `d3bb95d1f702b9daa65e1bb2923e2e83` (the `_living_costs` medical line). Default-run output md5 `318c6114c143a81a579e70b39ccca8f8` (two runs). `--v4` output md5 `6292c3c897d85834e8d45d2913e3629b` (two runs). Reproduce with `python3 tools/economy_sim.py [--v4]`.

## 2. Actual Run Output (verbatim, default)

```
profession                   tier      gross    tax   rent  costs   net/mo  save%   minbal  flags
construction_worker          entry      9000      0   2500   7500     1500   16.7        0  -
construction_worker          mid       14000      0   2500   9250     4750   33.9        0  -
construction_worker          senior    20000    250   2500  11350     8400   42.0        0  -
civil_engineer               entry     22000    350   6000  16350     5300   24.1   -15805  -
civil_engineer               mid       38000   1150   6000  21950    14900   39.2   -21218  -
civil_engineer               senior    65000   3750   6000  31400    29850   45.9   -30353  -
doctor                       entry     30000    750  12000  24650     4600   15.3   -23828  -
doctor                       mid       55000   2750  12000  33400    18850   34.3   -32287  -
doctor                       senior    95000   6750  12000  47400    40850   43.0   -45820  -
teacher                      entry     15000      0   4000   9000     6000   40.0    -8700  -
teacher                      mid       24000    450   4000  12150    11400   47.5   -11745  -
teacher                      senior    38000   1150   4000  17050    19800   52.1   -16482  -
police_officer               entry     18000    150   6000  16350     1500    8.3   -15805  TIGHT
police_officer               mid       28000    650   6000  19850     7500   26.8   -19188  -
police_officer               senior    45000   1750   6000  25800    17450   38.8   -24940  -
taxi_driver                  entry     14000      0   2500   7500     6500   46.4        0  -
taxi_driver                  mid       23000    400   2500  10650    11950   52.0        0  -
taxi_driver                  senior    36000   1050   2500  15200    19750   54.9        0  -
taxi_driver (renting cab)    entry     14000      0   2500  12700     1300    9.3        0  TIGHT
chef                         entry     13000      0   4000   9000     4000   30.8    -8700  -
chef                         mid       22000    350   4000  12150     9500   43.2   -11745  -
chef                         senior    40000   1250   4000  18450    20300   50.7   -17835  -
software_developer           entry     28000    650   6000  16350    11000   39.3   -15805  -
software_developer           mid       52000   2450   6000  24750    24800   47.7   -23925  -
software_developer           senior    90000   6250   6000  38050    45700   50.8   -36782  -
shop_owner                   entry     12000    960   4000   9000     2040   17.0        0  -
shop_owner                   mid       26000   2080   4000  13900    10020   38.5        0  -
shop_owner                   senior    55000   4400   4000  24050    26550   48.3        0  -
business_owner               entry     40020   3202  12000  24650    12168   30.4   -23828  -
business_owner               mid      109980   8798  12000  49136    52046   47.3   -47498  -
business_owner               senior   300000  24000  12000 115643   160357   53.5  -111788  -
pilot                        entry     45000   1750  12000  42900      350    0.8   -41470  TIGHT
pilot                        mid       95000   6750  12000  60400    27850   29.3   -58387  -
pilot                        senior   180000  15250  12000  90150    74600   41.4   -87145  -

professions simulated: 11 (+ taxi rental variant); rows: 34
SURVIVAL FAIL rows: []
IMPLAUSIBLY FAST rows: []
TIGHT rows: ['police_officer/entry', 'taxi_driver (renting cab)/entry', 'pilot/entry']
senior savings rates: construction_worker 42.0%, civil_engineer 45.9%, doctor 43.0%, teacher 52.1%, police_officer 38.8%, taxi_driver 54.9%, chef 50.7%, software_developer 50.8%, shop_owner 48.3%, business_owner 53.5%, pilot 41.4%

business P&L (revenue - stock - premises - staff - other = profit vs canonical band):
  business_owner  entry   rev  101700 - stock  40680 - prem   4000 - staff  15000 - other  2000 = profit   40020 (band 40000, delta +20)
  business_owner  mid     rev  313300 - stock 125320 - prem  12000 - staff  60000 - other  6000 = profit  109980 (band 110000, delta -20)
  business_owner  senior  rev  825000 - stock 330000 - prem  30000 - staff 150000 - other 15000 = profit  300000 (band 300000, delta +0)
  shop_owner      entry   rev   26200 - stock  13100 - prem    800 - staff      0 - other   300 = profit   12000 (band 12000, delta +0)
  shop_owner      mid     rev   77600 - stock  38800 - prem   3000 - staff   9000 - other   800 = profit   26000 (band 26000, delta +0)
  shop_owner      senior  rev  170000 - stock  85000 - prem   8000 - staff  20000 - other  2000 = profit   55000 (band 55000, delta +0)

first-month bridge check (entry rows: starting balance + zero-start dip = worst month-1 balance):
  construction_worker    start   5000 + dip       0 =    5000  OK
  civil_engineer         start  25000 + dip  -15805 =    9195  OK
  doctor                 start  30000 + dip  -23828 =    6172  OK
  teacher                start  11000 + dip   -8700 =    2300  OK
  police_officer         start  20000 + dip  -15805 =    4195  OK
  taxi_driver            start   5000 + dip       0 =    5000  OK
  chef                   start  11000 + dip   -8700 =    2300  OK
  software_developer     start  20000 + dip  -15805 =    4195  OK
  shop_owner             start   5000 + dip       0 =    5000  OK
  business_owner         start  30000 + dip  -23828 =    6172  OK
  pilot                  start  51000 + dip  -41470 =    9530  OK
  taxi_driver (renting cab) start   5000 + dip       0 =    5000  OK
BRIDGE FAIL rows: []
pacing: civil_engineer/entry saves 5300 NCr/mo -> car_small (450000) in 84.9 months; tier-3 deposit (150000) in 28.3 months
```

## 3. Actual Run Output (verbatim, `--v4` section)

```
v4 additional scenarios (Units AH + AI):
  priced from prices.json: tutoring 300/session x 8/mo = 2400; part-time 150/block x 4/wk x 4 = 2400; medical budget lower 300 / mid 500 / upper 800 — now charged in the base table (Unit AJ), not a scenario
  medicine basket check: one minor-illness episode (fever strip 60 + rehydration salts 40 + cough syrup 180) = 280 NCr, inside the lower medical budget (300)
  pharmacy: Boro Bazar Pharmacy (b_d1_market_hall_units, unit 1); clinic treatment stays free at point of use (GDD-12 §6)

household scenarios (base net -> scenario net; tax recomputed on combined income):
  teacher/entry + tutoring income (tutors 8 sessions)  base net   6000 ->   8280 (delta +2280, save 47.6%)  -
  teacher/entry + tutoring expense (pays for one child) base net   6000 ->   3600 (delta -2400, save 24.0%)  -
  teacher/entry + tutoring income AND expense          base net   6000 ->   5880 (delta -120, save 33.8%)  -
  construction_worker/entry + teen part-time income    base net   1500 ->   3900 (delta +2400, save 34.2%)  -
  teacher/entry + teen part-time income                base net   6000 ->   8280 (delta +2280, save 47.6%)  -
v4 scenario SURVIVAL FAIL rows: []
v4 scenario TIGHT rows: []
```

## 4. Before / After — the One Unit

| # | Unit / open item | Before (v3 base table) | After (v4 run) | Verdict |
|---|---|---|---|---|
| AJ | Medical line not charged in the base table (v3 report §5: "the medical line is not yet charged in the base table"; scenarios only) | Base nets excluded medicine: police/entry +2,000 (11.1%), pilot/entry +1,150 (2.6%, the only base TIGHT row), renting-cab +1,600 (11.4%); pinned baseline md5 `16740182867525bd659735deeb05150a` | Every base row nets exactly its band's line less: police/entry **+1,500 (8.3%, TIGHT)**, pilot/entry **+350 (0.8%, TIGHT)**, renting-cab **+1,300 (9.3%, TIGHT)**; all other rows down 300/500/800 by band (e.g. teacher/entry 6,300 → 6,000; civil/entry 5,800 → 5,300; construction/entry 1,800 → 1,500); no SURVIVAL FAIL, no BRIDGE FAIL, no IMPLAUSIBLY FAST; new pinned baseline md5 `318c6114c143a81a579e70b39ccca8f8`; life-sim reconciliation still passes (§6) | ✅ **FIXED** (Unit AJ) |

Per-row net deltas (v3 → v4, all exactly −medical band): lower-band households (construction_worker, taxi_driver, chef, shop_owner at entry) −300; mid-band households (teacher, police_officer, civil_engineer, software_developer) −500; upper-band households (doctor, business_owner, pilot) −800; the renting-cab variant −300 on top of its cab rent. Senior savings rates stay inside the 35–55% band (38.8–54.9%) except teacher 52.1% and business_owner 53.5%, both inside. The wage ladder stays monotone in the base table, and every v4 scenario preserves its household's tier ordering.

## 5. New Observations (reported, not fixed)

- **The taxi renting-cab variant goes TIGHT (9.3%, net +1,300).** In v2/v3 it sat at 11.4% (+1,600); the 300 lower-band medical line tips it under 10%. It still survives with a positive net and the bridge still covers month 1 (start 5,000, dip 0), but a renter who is ill in a month is now the third-thinnest honest case in the model. Not stealth-fixed: exempting renters from the line or shrinking it would be tuning to hide a real cost. Owner call for playtesting, alongside the pilot/police notes.
- **`police_officer/entry` is TIGHT in the base table now (8.3%, net +1,500).** It was already TIGHT in the v3 scenarios; v4 makes that the honest base statement. Same judgement as v3 §4 — he survives, the line is an average, a healthy month costs nothing — but the margin is now the base table's, not a scenario's.
- **`pilot/entry` stays at 0.8% (net +350).** Unchanged in kind from v2/v3, deeper by exactly the 800 upper-band line. One bad month (a first-aid kit at 450 on top of the average) would take him negative in that month; the bridge (start 51,000, worst +9,530) still covers month 1, and mid tier recovers. Worth watching in playtesting; not a reason to move a wage or shrink the medicine table.
- **Pacing stretches slightly.** civil_engineer/entry saves 5,300 (was 5,800): car_small in 84.9 months (was 77.6), tier-3 deposit in 28.3 months (was 25.9). The property ladder's top end stays paced by the same mechanism; no tuning applied.
- **The tutoring/part-time scenarios are unchanged in shape, smaller in base.** A teacher tutoring 8 sessions now nets +2,280 over a 6,000 base (save 47.6%, was 49.3% over 6,300); paying for a child's tutoring nets −2,400 (save 24.0%); doing both nets −120 (the tax alone — the v3 observation stands). A teen's part-time work still lifts the poorest household (construction_worker/entry) from +1,500 to +3,900 (save 34.2%).

## 6. What Passed

- **Default run byte-identical across two runs** (md5 `318c6114c143a81a579e70b39ccca8f8`): the new baseline is deterministic.
- **`--v4` runs byte-identical to each other** (md5 `6292c3c897d85834e8d45d2913e3629b`): deterministic, machine-verifiable. `--v3` prints the same section (alias).
- **No SURVIVAL FAIL, no IMPLAUSIBLY FAST, no RENT BURDEN rows** in the base table or in any of the five v4 scenarios.
- **No BRIDGE FAIL:** the bridge check is unchanged in form (all 12 entry rows end month 1 ≥ 0 with their starting balances); worst case is pilot at +9,530.
- **The wage ladder stays monotone** in the base table, and every v4 scenario preserves its household's tier ordering.
- **The sizing invariants hold in data and are validator-checked:** tutoring typical monthly (2,400) < teacher entry wage (15,000); part-time typical monthly (2,400) < lowest full entry band (9,000); the medicine episode basket (280) ≤ the lower medical budget (300).
- **`python3 tools/validate_data.py` green**, including the Queue 6 medicine/pharmacy checks (no new data was added by this unit; the medical note text changed only).
- **Sim tests that touch `economy_sim` re-run and pass:** `tools.sim.tests.test_no_regression` (2 tests, incl. the new pinned-output check) and `tools.sim.tests.test_acceptance.TestReconciliation.test_single_adult_matches_economy_sim` (1 test — the lone-teacher household nets exactly what v4 `simulate()` computes, ±2).
- **Full suite: 438 tests (243 + 195), all passing** — run as a two-half per-module sweep (the Sessions 06–10 pattern). The single aggregate run first hit a `/tmp` disk-full cascade: the 512 MB tmpfs filled with leftover test SQLite files and the last 43 tests errored with `sqlite3.OperationalError: database or disk is full` at Store init — none of them a test failure. After clearing `/tmp`, the two halves ran green (half A 243 tests in 85.6 s; half B 195 tests in 1,329.7 s). Godot testbed re-run: `PLAYER_TEST_PASS` 8/8 (walk 5.00, run 8.77, jump apex 1.59, cam 3.04).

*End of report. The v3 report stands unchanged as the before-state; this file is the after-state for Unit AJ. Any further rebalancing — including the pilot/police/renting-cab TIGHT margins — is a new unit with its own before/after, or an owner tuning call.*
