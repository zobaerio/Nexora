# NEXORA — Economy Balance Simulator Report v5

**Unit AX · Queue 9 · 2026-11-22**
**Tool:** `tools/economy_sim.py` v5 (stdlib-only Python, deterministic — verified: two consecutive default runs byte-identical, md5 `318c6114c143a81a579e70b39ccca8f8`; two consecutive `--shibnagar` runs byte-identical, full-output md5 `3c41465c361c6e685eca733fe92e3407`) · **Data:** `data/prices.json` (unchanged) + `data/city2-shibnagar.json` (Session 03, GENERATED) · **Parent documents:** `docs/ECONOMY-SIM-REPORT-V4.md` (the District 1 before-state — its base table is the before column in §3), `docs/GDD-03-ECONOMY-AND-PROFESSIONS.md` (wage bands, rent tiers), `docs/SESSION-03-REPORT.md` (Shibnagar Town generation)
**Status:** RUN AND RECORDED. The output below is the tool's actual `--shibnagar` section, unedited. The default run is byte-identical to v4 and is not reprinted — the v4 report §2 is the default table.

> **What Queue 9 changed, in one paragraph:** the simulator now has a `--shibnagar` variant that runs the same 30-day household cashflow over Shibnagar Town's priced residential stock instead of District 1's tier rents. **No wage band moved. No rent tier moved.** The town's per-tier rents equal the `prices.json` tier table (asserted at runtime, not assumed), so the variant differs from District 1 in exactly one place: Shibnagar has no tier-4/5 homes, so the three professions District 1 houses at tier 4 (doctor, business_owner, pilot) are capped at tier 3 and each nets exactly 6,000 NCr/month more. The sharpest honest result is the pilot: entry tier goes from 0.8% TIGHT in District 1 to 14.1% in Shibnagar — the town's missing top tier is, for its highest-paid residents, a discount, not a hardship.

---

## 1. Method (what v5 does differently)

Same 30-day household cashflow as v4 (34 rows), with the rent line re-sourced behind a flag:

1. `load_shibnagar_rents(prices)` reads `data/city2-shibnagar.json` and takes the residential properties only (apartment/house with a rent): tier 1: 2,500 NCr/mo (10 units, Apartments B), tier 2: 4,000 (25 units: Apartments A 12 + Apartments C 8 + Houses A 5), tier 3: 6,000 (4 units, Houses B). Each tier's rent is asserted equal to the `prices.json` `rent_monthly_by_tier` value — the town's rents *are* tier rents, not a second price list — and a drift raises `ValueError` instead of running on stale numbers. The 7 unpriced properties (ghat, bus stand, school, clinic, town office, 2 farmland plots) are civic/plot stock, not homes, and are excluded by the residential + priced filter, not by an id list.
2. `SHIBNAGAR_RENT_TIER` is `RENT_TIER` with tier 4 capped at 3. The three capped professions (doctor, business_owner, pilot) rent the town's top tier; every other profession keeps its District 1 tier. `simulate()` takes an optional `rent_override` (default `None` = the tier-table rent, the v4 behaviour).
3. Nothing else moves: wages, living costs, the medical line, taxes, the business P&L (premises rent comes from `business_model`, not the residential stock), starting balances, the bridge check and the pacing formula are all unchanged, so the §3 comparison is a pure rent effect.
4. The default run is byte-identical to v4: the pinned md5 in `tools/sim/tests/test_no_regression.py` (`318c6114c143a81a579e70b39ccca8f8`) is untouched and the test passes 2/2. The variant is an additive flag only.

**Correction made during this unit (recorded, not hidden):** the first draft of the comparison keyed District 1 rows by `(profession_id, tier)`, which collided the taxi driver's two entry rows (owning vs renting cab) and printed a false +5,200 net delta for the owning row. The comparison now keys by `(profession, tier)` — the label that distinguishes the renting variant — and the owning row correctly reads +0. The default table was never affected (it prints rows, it does not join them).

**File md5s:** `tools/economy_sim.py` before Queue 9 `85529d2687ca53e96cf4e819372a2e95` (v4, Queue 7), after `de19137daae221f158c7bbab1c54a92f` (v5). Default-run output md5 `318c6114c143a81a579e70b39ccca8f8` (two runs, byte-identical to v4). `--shibnagar` full-output md5 `3c41465c361c6e685eca733fe92e3407` (two runs). Reproduce with `python3 tools/economy_sim.py --shibnagar`.

## 2. Actual Run Output (verbatim, `--shibnagar` section)

```
shibnagar variant (Unit AX): same 30-day simulation over data/city2-shibnagar.json residential stock
  priced residential stock: tier 1: 2500 NCr/mo (10 units), tier 2: 4000 NCr/mo (25 units), tier 3: 6000 NCr/mo (4 units) — each tier's rent equals the prices.json tier table (asserted, not assumed)
  no tier-4/5 homes exist in Shibnagar; capped at tier 3: business_owner, doctor, pilot (rent 12000 -> 6000)
  7 of 18 properties unpriced (ghat, bus stand, school, clinic, town office, 2 farmland plots) — civic/plot stock, not homes
profession                   tier      gross    tax   rent  costs   net/mo  save%   minbal  flags
construction_worker          entry      9000      0   2500   7500     1500   16.7        0  -
construction_worker          mid       14000      0   2500   9250     4750   33.9        0  -
construction_worker          senior    20000    250   2500  11350     8400   42.0        0  -
civil_engineer               entry     22000    350   6000  16350     5300   24.1   -15805  -
civil_engineer               mid       38000   1150   6000  21950    14900   39.2   -21218  -
civil_engineer               senior    65000   3750   6000  31400    29850   45.9   -30353  -
doctor                       entry     30000    750   6000  18650    10600   35.3   -18028  -
doctor                       mid       55000   2750   6000  27400    24850   45.2   -26487  -
doctor                       senior    95000   6750   6000  41400    46850   49.3   -40020  -
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
business_owner               entry     40020   3202   6000  18650    18168   45.4   -18028  -
business_owner               mid      109980   8798   6000  43136    58046   52.8   -41698  -
business_owner               senior   300000  24000   6000 109643   166357   55.5  -105988  -
pilot                        entry     45000   1750   6000  36900     6350   14.1   -35670  -
pilot                        mid       95000   6750   6000  54400    33850   35.6   -52587  -
pilot                        senior   180000  15250   6000  84150    80600   44.8   -81345  -

shibnagar SURVIVAL FAIL rows: []
shibnagar IMPLAUSIBLY FAST rows: []
shibnagar TIGHT rows: ['police_officer/entry', 'taxi_driver (renting cab)/entry']
shibnagar senior savings rates: construction_worker 42.0%, civil_engineer 45.9%, doctor 49.3%, teacher 52.1%, police_officer 38.8%, taxi_driver 54.9%, chef 50.7%, software_developer 50.8%, shop_owner 48.3%, business_owner 55.5%, pilot 44.8%

shibnagar first-month bridge check (same starting balances):
  construction_worker    start   5000 + dip       0 =    5000  OK
  civil_engineer         start  25000 + dip  -15805 =    9195  OK
  doctor                 start  30000 + dip  -18028 =   11972  OK
  teacher                start  11000 + dip   -8700 =    2300  OK
  police_officer         start  20000 + dip  -15805 =    4195  OK
  taxi_driver            start   5000 + dip       0 =    5000  OK
  chef                   start  11000 + dip   -8700 =    2300  OK
  software_developer     start  20000 + dip  -15805 =    4195  OK
  shop_owner             start   5000 + dip       0 =    5000  OK
  business_owner         start  30000 + dip  -18028 =   11972  OK
  pilot                  start  51000 + dip  -35670 =   15330  OK
  taxi_driver (renting cab) start   5000 + dip       0 =    5000  OK
shibnagar BRIDGE FAIL rows: []

district 1 vs shibnagar (rent delta -> net delta; only the three capped professions differ):
  construction_worker          entry   rent   2500 ->   2500 (+0)  net    1500 ->    1500 (+0)  -
  construction_worker          mid     rent   2500 ->   2500 (+0)  net    4750 ->    4750 (+0)  -
  construction_worker          senior  rent   2500 ->   2500 (+0)  net    8400 ->    8400 (+0)  -
  civil_engineer               entry   rent   6000 ->   6000 (+0)  net    5300 ->    5300 (+0)  -
  civil_engineer               mid     rent   6000 ->   6000 (+0)  net   14900 ->   14900 (+0)  -
  civil_engineer               senior  rent   6000 ->   6000 (+0)  net   29850 ->   29850 (+0)  -
  doctor                       entry   rent  12000 ->   6000 (-6000)  net    4600 ->   10600 (+6000)  -
  doctor                       mid     rent  12000 ->   6000 (-6000)  net   18850 ->   24850 (+6000)  -
  doctor                       senior  rent  12000 ->   6000 (-6000)  net   40850 ->   46850 (+6000)  -
  teacher                      entry   rent   4000 ->   4000 (+0)  net    6000 ->    6000 (+0)  -
  teacher                      mid     rent   4000 ->   4000 (+0)  net   11400 ->   11400 (+0)  -
  teacher                      senior  rent   4000 ->   4000 (+0)  net   19800 ->   19800 (+0)  -
  police_officer               entry   rent   6000 ->   6000 (+0)  net    1500 ->    1500 (+0)  TIGHT
  police_officer               mid     rent   6000 ->   6000 (+0)  net    7500 ->    7500 (+0)  -
  police_officer               senior  rent   6000 ->   6000 (+0)  net   17450 ->   17450 (+0)  -
  taxi_driver                  entry   rent   2500 ->   2500 (+0)  net    6500 ->    6500 (+0)  -
  taxi_driver                  mid     rent   2500 ->   2500 (+0)  net   11950 ->   11950 (+0)  -
  taxi_driver                  senior  rent   2500 ->   2500 (+0)  net   19750 ->   19750 (+0)  -
  taxi_driver (renting cab)    entry   rent   2500 ->   2500 (+0)  net    1300 ->    1300 (+0)  TIGHT
  chef                         entry   rent   4000 ->   4000 (+0)  net    4000 ->    4000 (+0)  -
  chef                         mid     rent   4000 ->   4000 (+0)  net    9500 ->    9500 (+0)  -
  chef                         senior  rent   4000 ->   4000 (+0)  net   20300 ->   20300 (+0)  -
  software_developer           entry   rent   6000 ->   6000 (+0)  net   11000 ->   11000 (+0)  -
  software_developer           mid     rent   6000 ->   6000 (+0)  net   24800 ->   24800 (+0)  -
  software_developer           senior  rent   6000 ->   6000 (+0)  net   45700 ->   45700 (+0)  -
  shop_owner                   entry   rent   4000 ->   4000 (+0)  net    2040 ->    2040 (+0)  -
  shop_owner                   mid     rent   4000 ->   4000 (+0)  net   10020 ->   10020 (+0)  -
  shop_owner                   senior  rent   4000 ->   4000 (+0)  net   26550 ->   26550 (+0)  -
  business_owner               entry   rent  12000 ->   6000 (-6000)  net   12168 ->   18168 (+6000)  -
  business_owner               mid     rent  12000 ->   6000 (-6000)  net   52046 ->   58046 (+6000)  -
  business_owner               senior  rent  12000 ->   6000 (-6000)  net  160357 ->  166357 (+6000)  -
  pilot                        entry   rent  12000 ->   6000 (-6000)  net     350 ->    6350 (+6000)  -
  pilot                        mid     rent  12000 ->   6000 (-6000)  net   27850 ->   33850 (+6000)  -
  pilot                        senior  rent  12000 ->   6000 (-6000)  net   74600 ->   80600 (+6000)  -
shibnagar pacing: civil_engineer/entry saves 5300 NCr/mo -> car_small (450000) in 84.9 months; tier-3 deposit (150000) in 28.3 months
```

## 3. District 1 vs Shibnagar — the verdict

Only the three capped professions differ; the other 31 rows are identical (rent delta +0, net delta +0), because the town's per-tier rents equal the tier table:

| Profession / tier | District 1 rent → Shibnagar rent | District 1 net → Shibnagar net | Verdict |
|---|---|---|---|
| doctor entry / mid / senior | 12,000 → 6,000 (−6,000) | 4,600 → 10,600 / 18,850 → 24,850 / 40,850 → 46,850 (+6,000) | Cheaper at the top: entry savings 15.3% → 35.3% |
| business_owner entry / mid / senior | 12,000 → 6,000 (−6,000) | 12,168 → 18,168 / 52,046 → 58,046 / 160,357 → 166,357 (+6,000) | Cheaper at the top: entry savings 30.4% → 45.4% |
| pilot entry / mid / senior | 12,000 → 6,000 (−6,000) | 350 → 6,350 / 27,850 → 33,850 / 74,600 → 80,600 (+6,000) | **FIXED (as a finding): pilot/entry is no longer TIGHT** — 0.8% → 14.1%. The v4 report's sharpest TIGHT margin disappears in Shibnagar, not by tuning but because the town has no tier-4 home to charge for |
| police_officer entry | 6,000 → 6,000 (+0) | 1,500 → 1,500 (+0) | Still TIGHT at 8.3% — unchanged, reported not tuned |
| taxi_driver (renting cab) entry | 2,500 → 2,500 (+0) | 1,300 → 1,300 (+0) | Still TIGHT at 9.3% — unchanged, reported not tuned |
| all other 28 rows | +0 | +0 | Identical by construction |

No SURVIVAL FAIL rows in Shibnagar. No BRIDGE FAIL rows (same starting balances, smaller or equal dips). Senior savings rates 38.8–55.5%: business_owner senior sits at 55.5%, a whisker over the 55% target edge — the same pattern the v2 report recorded for taxi senior, reported not tuned. Pacing is unchanged (civil_engineer/entry saves 5,300 NCr/mo; car_small in 84.9 months; tier-3 deposit in 28.3 months).

## 4. What the variant does NOT model (honest limits)

- **Scarcity.** Shibnagar has 39 residential units in total (10 + 25 + 4) and only 4 at tier 3. The simulator prices one household's rent at its tier; it does not model whether a unit is actually available, and it does not queue households. If several tier-3 households arrived at once, 4 units would not house them — that is a housing-stock question for the Session 03 distribution layer, not a rent question, and this variant does not answer it.
- **No Shibnagar-specific wages or costs.** The variant reuses the national wage bands, living costs, taxes and fares. That follows Session 04 (one national economy, two cities as regions); a town-specific wage or price level would be a new data decision, not something this run invents.
- **Business premises are untouched.** Shop/business premises rent comes from `prices.json` `business_model`, not from the town's residential stock, so the business P&L section is identical and is not reprinted in the variant.
- **Transport and fares are unchanged.** There is no Shibnagar fare table; the bus/rickshaw/taxi lines are the same as District 1.

## 5. What passed

- Default run byte-identical to v4 (md5 `318c6114c143a81a579e70b39ccca8f8`, two runs).
- `--shibnagar` run twice byte-identical (full-output md5 `3c41465c361c6e685eca733fe92e3407`).
- `tools/sim/tests/test_no_regression.py` 2/2 green (economy_sim md5 pinned, `validate_data.py` green).
- `tools/validate_data.py` green, including the new District 2 / intercity checks from Units AT + AU.
- Shibnagar's tier rents asserted equal to the `prices.json` tier table at runtime (the variant refuses to run on a drift).
