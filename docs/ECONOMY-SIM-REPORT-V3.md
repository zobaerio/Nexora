# NEXORA — Economy Balance Simulator Report v3

**Units AH + AI · Queue 6 · 2026-11-22**
**Tool:** `tools/economy_sim.py` v3 (stdlib-only Python, deterministic — verified: two consecutive `--v3` runs byte-identical, md5 `93ffcf499d84448d3e3fb37373c79160`) · **Data:** `data/prices.json` v1.3 + `data/professions.json` v1.1 · **Parent documents:** `docs/ECONOMY-SIM-REPORT-V2.md` (the before-state — its table is reproduced unchanged inside the v3 output below), `docs/GDD-03-ECONOMY-AND-PROFESSIONS.md` §12 (the Queue 6 tuning log), `docs/GDD-11-EDUCATION.md` §7 (tutoring / part-time pricing), `docs/GDD-12-HEALTH.md` §6 (pharmacy / medicine pricing)
**Status:** RUN AND RECORDED. The output below is the tool's actual `--v3` output on the post-fix data, unedited.

> **What Queue 6 changed, in one paragraph:** the two recorded economy open items are now priced — tutoring and part-time student work (Unit AH: 300 NCr/session, 150 NCr/block) and household medicine (Unit AI: a six-item medicine table, a monthly medical budget line of 300/500/800, and Boro Bazar Pharmacy sited in unit 1 of the market hall). **No wage band moved. No rent tier moved.** The new lines are modelled as additive household scenarios behind a `--v3` flag, and the default run is byte-identical to v2 — see §1 for why that constraint exists and §5 for what it leaves open.

---

## 1. Method (what v3 does differently)

Same 30-day household cashflow as v2 (34 rows, byte-identical output on a default run), plus one additive section printed only under `--v3`:

1. `simulate()` takes four optional keyword arguments — `tutoring_income`, `tutoring_expense`, `part_time_income`, `medicine_expense` — all defaulting to 0. Extra income is taxed marginally on the combined gross; extra expense is added to monthly costs; side-income accrues evenly across the 30-day trajectory while base pay keeps its own schedule, so the month still totals exactly gross − tax. The lifestyle uplift is computed from the base gross on purpose: it prices the wage ladder, not side-income.
2. The `--v3` section prints nine household scenarios on top of the base rows (teacher tutoring / paying for tutoring / both; teen part-time income in two households; the medical budget line in four households) and a medicine-basket check (one minor-illness episode = 280 NCr, inside the lower 300 budget).
3. Business professions with extras raise `ValueError`: a business household mixing personal side-income with profit needs a business+personal split this unit does not design. No v3 scenario exercises that path.

**Why the base table does not move.** `tools/sim/tests/test_no_regression.py` pins this tool's default stdout md5 (`16740182867525bd659735deeb05150a` — re-verified this run), and the life-sim acceptance test requires a lone teacher household to net exactly what `simulate()` computes. Folding the medical line into the base table would break both, and updating the pinned baseline is a change to a test file, outside this unit's scope. So v3 models the new lines as scenarios and records the gap openly in §5, instead of silently moving the baseline. The base table below is therefore the v2 table, reproduced — that is the point, not an omission.

**File md5s:** `tools/economy_sim.py` before Queue 6 `94b85728a732153b37e7eb77d0430cc4`, after `1bd880fe2984f40e3a2b506bd40ec03e`. Default-run output md5 `16740182867525bd659735deeb05150a` (== the pinned baseline, == the v2 output md5). `--v3` output md5 `93ffcf499d84448d3e3fb37373c79160` (two runs). Reproduce with `python3 tools/economy_sim.py --v3`.

## 2. Actual Run Output (verbatim, `--v3`)

```
profession                   tier      gross    tax   rent  costs   net/mo  save%   minbal  flags
construction_worker          entry      9000      0   2500   7200     1800   20.0        0  -
construction_worker          mid       14000      0   2500   8950     5050   36.1        0  -
construction_worker          senior    20000    250   2500  11050     8700   43.5        0  -
civil_engineer               entry     22000    350   6000  15850     5800   26.4   -15322  -
civil_engineer               mid       38000   1150   6000  21450    15400   40.5   -20735  -
civil_engineer               senior    65000   3750   6000  30900    30350   46.7   -29870  -
doctor                       entry     30000    750  12000  24150     5100   17.0   -23345  -
doctor                       mid       55000   2750  12000  32900    19350   35.2   -31803  -
doctor                       senior    95000   6750  12000  46900    41350   43.5   -45337  -
teacher                      entry     15000      0   4000   8700     6300   42.0    -8410  -
teacher                      mid       24000    450   4000  11850    11700   48.8   -11455  -
teacher                      senior    38000   1150   4000  16750    20100   52.9   -16192  -
police_officer               entry     18000    150   6000  15850     2000   11.1   -15322  -
police_officer               mid       28000    650   6000  19350     8000   28.6   -18705  -
police_officer               senior    45000   1750   6000  25300    17950   39.9   -24457  -
taxi_driver                  entry     14000      0   2500   7200     6800   48.6        0  -
taxi_driver                  mid       23000    400   2500  10350    12250   53.3        0  -
taxi_driver                  senior    36000   1050   2500  14900    20050   55.7        0  -
taxi_driver (renting cab)    entry     14000      0   2500  12400     1600   11.4        0  -
chef                         entry     13000      0   4000   8700     4300   33.1    -8410  -
chef                         mid       22000    350   4000  11850     9800   44.5   -11455  -
chef                         senior    40000   1250   4000  18150    20600   51.5   -17545  -
software_developer           entry     28000    650   6000  15850    11500   41.1   -15322  -
software_developer           mid       52000   2450   6000  24250    25300   48.7   -23442  -
software_developer           senior    90000   6250   6000  37550    46200   51.3   -36298  -
shop_owner                   entry     12000    960   4000   8700     2340   19.5        0  -
shop_owner                   mid       26000   2080   4000  13600    10320   39.7        0  -
shop_owner                   senior    55000   4400   4000  23750    26850   48.8        0  -
business_owner               entry     40020   3202  12000  24150    12668   31.7   -23345  -
business_owner               mid      109980   8798  12000  48636    52546   47.8   -47015  -
business_owner               senior   300000  24000  12000 115143   160857   53.6  -111305  -
pilot                        entry     45000   1750  12000  42100     1150    2.6   -40697  TIGHT
pilot                        mid       95000   6750  12000  59600    28650   30.2   -57613  -
pilot                        senior   180000  15250  12000  89350    75400   41.9   -86372  -

professions simulated: 11 (+ taxi rental variant); rows: 34
SURVIVAL FAIL rows: []
IMPLAUSIBLY FAST rows: []
TIGHT rows: ['pilot/entry']
senior savings rates: construction_worker 43.5%, civil_engineer 46.7%, doctor 43.5%, teacher 52.9%, police_officer 39.9%, taxi_driver 55.7%, chef 51.5%, software_developer 51.3%, shop_owner 48.8%, business_owner 53.6%, pilot 41.9%

business P&L (revenue - stock - premises - staff - other = profit vs canonical band):
  business_owner  entry   rev  101700 - stock  40680 - prem   4000 - staff  15000 - other  2000 = profit   40020 (band 40000, delta +20)
  business_owner  mid     rev  313300 - stock 125320 - prem  12000 - staff  60000 - other  6000 = profit  109980 (band 110000, delta -20)
  business_owner  senior  rev  825000 - stock 330000 - prem  30000 - staff 150000 - other 15000 = profit  300000 (band 300000, delta +0)
  shop_owner      entry   rev   26200 - stock  13100 - prem    800 - staff      0 - other   300 = profit   12000 (band 12000, delta +0)
  shop_owner      mid     rev   77600 - stock  38800 - prem   3000 - staff   9000 - other   800 = profit   26000 (band 26000, delta +0)
  shop_owner      senior  rev  170000 - stock  85000 - prem   8000 - staff  20000 - other  2000 = profit   55000 (band 55000, delta +0)

first-month bridge check (entry rows: starting balance + zero-start dip = worst month-1 balance):
  construction_worker    start   5000 + dip       0 =    5000  OK
  civil_engineer         start  25000 + dip  -15322 =    9678  OK
  doctor                 start  30000 + dip  -23345 =    6655  OK
  teacher                start  11000 + dip   -8410 =    2590  OK
  police_officer         start  20000 + dip  -15322 =    4678  OK
  taxi_driver            start   5000 + dip       0 =    5000  OK
  chef                   start  11000 + dip   -8410 =    2590  OK
  software_developer     start  20000 + dip  -15322 =    4678  OK
  shop_owner             start   5000 + dip       0 =    5000  OK
  business_owner         start  30000 + dip  -23345 =    6655  OK
  pilot                  start  51000 + dip  -40697 =   10303  OK
  taxi_driver (renting cab) start   5000 + dip       0 =    5000  OK
BRIDGE FAIL rows: []
pacing: civil_engineer/entry saves 5800 NCr/mo -> car_small (450000) in 77.6 months; tier-3 deposit (150000) in 25.9 months

Queue 6 / v3 new lines (Units AH + AI):
  priced from prices.json: tutoring 300/session x 8/mo = 2400; part-time 150/block x 4/wk x 4 = 2400; medical budget lower 300 / mid 500 / upper 800
  medicine basket check: one minor-illness episode (fever strip 60 + rehydration salts 40 + cough syrup 180) = 280 NCr, inside the lower medical budget (300)
  pharmacy: Boro Bazar Pharmacy (b_d1_market_hall_units, unit 1); clinic treatment stays free at point of use (GDD-12 §6)

household scenarios (base net -> scenario net; tax recomputed on combined income):
  teacher/entry + tutoring income (tutors 8 sessions)  base net   6300 ->   8580 (delta +2280, save 49.3%)  -
  teacher/entry + tutoring expense (pays for one child) base net   6300 ->   3900 (delta -2400, save 26.0%)  -
  teacher/entry + tutoring income AND expense          base net   6300 ->   6180 (delta -120, save 35.5%)  -
  construction_worker/entry + teen part-time income    base net   1800 ->   4200 (delta +2400, save 36.8%)  -
  teacher/entry + teen part-time income                base net   6300 ->   8580 (delta +2280, save 49.3%)  -
  construction_worker/entry + medical budget (lower)   base net   1800 ->   1500 (delta -300, save 16.7%)  -
  police_officer/entry + medical budget (mid)          base net   2000 ->   1500 (delta -500, save 8.3%)  TIGHT
  pilot/entry + medical budget (upper)                 base net   1150 ->    350 (delta -800, save 0.8%)  TIGHT
  civil_engineer/entry + medical budget (mid)          base net   5800 ->   5300 (delta -500, save 24.1%)  -
v3 scenario SURVIVAL FAIL rows: []
v3 scenario TIGHT rows: ['police_officer/entry + medical budget (mid)', 'pilot/entry + medical budget (upper)']
```

## 3. Before / After — the Two Units

| # | Unit / open item | Before | After (v3 run) | Verdict |
|---|---|---|---|---|
| AH | Tutoring & part-time student work unpriced (GDD-11 §7: "unpriced in v1", no ledger row; GDD-11 §2: "no part-time wage line exists in `prices.json`") | No rate anywhere: tutoring was a time-only relationship, part-time earnings had no number | Tutoring **300/session × 8 = 2,400/mo**; part-time **150/block × 16 = 2,400/mo** (`prices.json` `tutoring`, `part_time_student_work`; GDD-11 §2/§6/§7/§9 amended). Scenarios: teacher tutoring nets **+2,280/mo** after the 120 NCr tax on the side-income (save 49.3%); paying for a child's tutoring nets **−2,400** (save 26.0%); a teen's part-time work lifts the poorest household (construction_worker/entry) from **+1,800 to +4,200/mo** (save 36.8%). No SURVIVAL FAIL, no IMPLAUSIBLY FAST in any AH scenario | ✅ **FIXED** (Unit AH) |
| AI | No pharmacy in District 1, no medicine price, no household medical budget (GDD-12 §6: "no medicine purchases") | Clinic treatment free, and nothing else existed — any medicine price cited would have been invented | **Boro Bazar Pharmacy** sited in unit 1 of `b_d1_market_hall_units` (tenant edit, `for_rent_units` 5 → 4; no new building). Medicine table: six over-the-counter basics, **40–450 NCr**. Medical budget line **lower 300 / mid 500 / upper 800**, sized so one minor-illness episode (**280 NCr**) fits the lower band. Scenarios: every household survives the line; the cost is real — police/entry falls to **8.3% (TIGHT**, was 11.1%) and pilot/entry deepens to **0.8% (TIGHT**, was 2.6%). Clinic treatment stays free at point of use — the table prices pharmacy purchases only, stated in GDD-12 §6, in the `medicine` notes, and in the sim output itself | ✅ **FIXED** (Unit AI) |

## 4. New Observations (reported, not fixed)

- **`police_officer/entry` goes TIGHT under the medical line (8.3%, net +1,500).** The constable was already the second-thinnest honest margin in v2 (11.1%, net +2,000); the mid-band medical budget (500) is what tips him under 10%. He still survives with a positive net, and the line is an average — a healthy month costs him nothing — but a household that is ill *and* constable-paid is now the tightest honest case in the model after the pilot. Not stealth-fixed: exempting constables from the mid band or shrinking the medical line would be tuning to hide a real cost. Owner call for playtesting, alongside the v2 pilot note.
- **`pilot/entry` deepens to 0.8% (net +350) under the upper medical budget (800).** He was already the run's only TIGHT row in v2 (2.6%, net +1,150); the upper band's eating-out and services lines plus medicine now leave him 350/month above water in an average month. Same judgement as v2 — he survives, the bridge still covers month 1 (start 51,000), mid tier recovers — but the margin is now thin enough that one bad month (a first-aid kit at 450 on top of the average) would take him negative in that month. Worth watching in playtesting; not a reason to move a wage or shrink the medicine table.
- **A teacher who both tutors and pays for a child's tutoring nets −120/month.** The two 2,400 lines cancel exactly; the only remainder is the 120 NCr income tax on the side-income (15,000 + 2,400 gross crosses the 15,000 tax-free threshold). A neat check that the tax code runs on combined income, and a true statement about the design: tutoring your own child out of tutoring income costs you the tax. Left as is.
- **Part-time income and tutoring income print identically for a teacher (+2,280).** Same amount (2,400), same tax (120) — expected, not a copy error: both are untaxed-at-source personal income added to the same gross. The difference between them is who earns it and where it is earned (GDD-11 §2), not the arithmetic.

## 5. Open Item — the Medical Line Is Not Yet Charged in the Base Table

The `medical_monthly` line (300/500/800) exists in `prices.json` and is read by the v3 scenarios, but the 34-row base table — the pinned v2 output — does not charge it. That is deliberate (§1): charging it would change every base row's net and break the pinned no-regression baseline md5 in `tools/sim/tests/test_no_regression.py`, and the life-sim acceptance test that reconciles against `simulate()`. Folding the line into the base table therefore needs a follow-up unit that (a) re-runs the base table with the line charged, (b) updates the pinned baseline md5 in the test file with the owner's / coordinator's agreement, and (c) re-checks the life-sim reconciliation — a test-file change, not a silent data change. Until then, the scenario deltas in §2 are the honest statement of the line's cost: −300/−500/−800 on the affected households' nets, with police/entry and pilot/entry crossing into TIGHT. Nothing is hidden by the flag: the default run stays v2-exact so the regression suite keeps passing (`test_no_regression` 2/2, acceptance reconciliation 1/1 — both re-run this unit, see §6).

## 6. What Passed

- **Default run byte-identical to v2** (md5 `16740182867525bd659735deeb05150a` = pinned baseline): no base row moved, no v2 finding re-opened.
- **`--v3` runs byte-identical to each other** (md5 `93ffcf499d84448d3e3fb37373c79160`): deterministic, machine-verifiable.
- **No SURVIVAL FAIL, no IMPLAUSIBLY FAST, no RENT BURDEN rows** in the base table (unchanged from v2) or in any of the nine v3 scenarios.
- **No BRIDGE FAIL:** the bridge check is unchanged from v2 (all 12 entry rows end month 1 ≥ 0).
- **The wage ladder stays monotone** in the base table, and every v3 scenario preserves its household's tier ordering (a scenario never makes a lower tier out-save a higher one — the scenarios only touch entry rows, and none overtakes the next tier up).
- **The sizing invariants hold in data and are validator-checked:** tutoring typical monthly (2,400) < teacher entry wage (15,000); part-time typical monthly (2,400) < lowest full entry band (9,000); the medicine episode basket (280) ≤ the lower medical budget (300).
- **`python3 tools/validate_data.py` green**, including the 8 new Queue 6 checks (tutoring/part-time reconciliation and bounds, medicine uniqueness/prices/bands, pharmacy siting + tenant record, medical budget ordering).
- **Sim tests that touch `economy_sim` re-run and pass:** `tools.sim.tests.test_no_regression` (2 tests, incl. the pinned-output check) and `tools.sim.tests.test_acceptance.TestReconciliation.test_single_adult_matches_economy_sim` (1 test). The full 438-test endurance suite was **not** run — out of scope for this unit by the task order; the life-sim engine itself was not touched, and its single-adult reconciliation against `simulate()` still passes.

*End of report. The v2 report stands unchanged as the before-state; this file is the after-state for Units AH + AI. Any further rebalancing — including folding the medical line into the base table — is a new unit with its own before/after.*
