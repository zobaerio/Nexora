# NEXORA — Economy Balance Simulator Report v2

**Unit X · Queue 4 · 2026-11-21**
**Tool:** `tools/economy_sim.py` v2 (stdlib-only Python, deterministic — verified: two consecutive runs byte-identical) · **Data:** `data/prices.json` v1.1 + `data/professions.json` v1.1 · **Parent documents:** `docs/ECONOMY-SIM-REPORT.md` (the v1 report whose findings this queue fixes — kept unchanged as the before-state record), `docs/GDD-03-ECONOMY-AND-PROFESSIONS.md` §11 (the tuning log)
**Status:** RUN AND RECORDED. The output below is the tool's actual output on the post-fix data, unedited.

> **What Queue 4 changed, in one paragraph:** the cab rental price (Unit U), the living-cost model (Unit V: eating-out and household-services lines plus a 35%-of-raise lifestyle uplift), per-profession starting balances (Unit W), and this simulator (Unit X: full business P&L + business tax for the two business professions). **No wage band moved. No rent tier moved.** Every fix landed in prices, costs or starting conditions — the ladder itself is untouched.

---

## 1. Method (what v2 does differently)

Same 30-day household cashflow as v1 (34 rows), with four changes: (1) households now spend the eating-out and household-services lines that v1 priced but never charged, and consume 35% of any raise above entry wage as lifestyle uplift (`prices.json` `lifestyle_uplift`); (2) `shop_owner` and `business_owner` run through a full business P&L from `prices.json` `business_model` (revenue − stock − premises − staff − other = profit), are taxed at the 8% business rate instead of personal income tax, and live on profit − tax; (3) a bridge check applies each profession's `starting_balance_ncr` (`data/professions.json`) to its entry row and verifies the month-1 minimum never goes below zero — the table's `minbal` column stays zero-start for v1 comparability; (4) business timing follows the GDD: shop takings accrue daily, the business owner's draw lands on day 30.

## 2. Actual Run Output (verbatim)

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
```

## 3. Before / After — the Four Findings

| # | Finding (v1) | Before (v1 run) | After (v2 run) | Verdict |
|---|---|---|---|---|
| 1 | Taxi rental on-ramp broken | Renting entry: **−13,700/mo (−97.9%)**, SURVIVAL FAIL, month-1 dip −12,247 | Rental 800 → **200/day**: renting entry **+1,600/mo (11.4%)**, no flag, dip 0 — modestly positive, clearly worse than owning (+6,800), exactly the designed on-ramp shape | ✅ **FIXED** (Unit U) |
| 2 | Senior tiers accumulate implausibly fast | **9 IMPLAUSIBLY FAST rows**; senior savings 71–84% on flagged rows (business senior 83.5% → tier-5 house in ~18 idle months) | **0 flagged rows**; all 11 senior savings rates land at **39.9–55.7%** (business senior 83.5% → 53.6%). One honest edge: taxi_driver senior at 55.7% sits 0.7 pt above the 55% target edge — inside "roughly", named here rather than tuned away | ✅ **FIXED** (Unit V) |
| 3 | First-month bridge: monthly-paid starts go underwater | Every monthly-paid row dipped negative from zero (pilot **−34,800**); only the civil engineer's 25,000 existed, as a one-off | `starting_balance_ncr` per profession (dip × 1.25, min 5,000; civil keeps canonical 25,000; pilot 51,000). Bridge check: **all 12 entry rows end month 1 ≥ 0** (thinnest cushion: teacher/chef +2,590) | ✅ **FIXED** (Unit W) |
| 6 | Business rows are pre-cost upper bounds | Shop/business bands treated as personal income, income-taxed, no stock/staff/premises anywhere (business senior's 83.5% the worst artefact) | Full P&L per tier in `prices.json` `business_model`; profit reconciles to the canonical band (Δ 0 everywhere except business entry/mid **±20**, the disclosed cost of rounding revenue to the nearest 100); **8% business tax** replaces income tax; shop entry's flattering +3,600 upper bound becomes an honest **+2,340** | ✅ **FIXED** (Unit X) |

## 4. Updates to the Other v1 Findings

- **Finding 4 (pacing) — numbers moved, judgement unchanged.** The civil engineer's entry surplus is now **5,800/mo** (v1: 7,650) because v2 is the first model that actually charges the eating-out (1,050) and services (800) lines v1 priced but never spent. He stays above GDD-03 §1's 5,000 grind floor. Pacing: small car in **77.6 months** (was 58.8), tier-3 deposit in **25.9** (was 19.6) — and the flagship-loop caveat from v1 still applies: these figures assume the player works the loop at band rate; a second job in a month accelerates past them by the fee. Whether the longer horizon is "grind" or "goals done right" remains the owner's call, now with honest numbers.
- **Finding 5 (reconciliation) — closed.** GDD-03 §1's sketch (outgoings 12,500, surplus ≈9,500) vs v2's fuller household (outgoings 15,850, surplus 5,800) differs by exactly: clothing 1,500 + eating out 1,050 + services 800 on the cost side, and income tax 350 on the other. 12,500 + 1,500 + 1,050 + 800 = 15,850; 9,500 − 350 − 1,500 − 1,050 − 800 = 5,800. Nothing unexplained remains between the two documents.

## 5. New Observations (reported, not fixed)

- **`pilot/entry` is TIGHT (2.6%, net +1,150)** — the run's only TIGHT row. Cause: a 45,000 entry wage puts the household in the *upper* lifestyle band, and v2 is the first model to charge that band's eating out (3,600) and services (2,500). He survives comfortably on the bridge (start 51,000, worst month-1 balance +10,303) and mid tier recovers to 30.2%. Not stealth-fixed: compressing it would mean either exempting pilots from the upper band or moving a wage — both owner calls for playtesting.
- **`police_officer/entry` thinned to 11.1% (net +2,000**, v1: 21.4%). A constable's 18,000 wage lands in the mid lifestyle band while he rents at tier 3 — positive and unflagged, but the second-thinnest honest margin after the construction worker. Noted for the same playtesting pass.
- **A wording conflict was found and resolved:** GDD-03 §7 called the shop bands "takings milestones" while §2 ("Profit, not wage") and `professions.json` define them as profit. The profit reading is the only one under which a playable profession survives its own P&L, so §7's sentence was corrected (marked in place) and the P&L above is built on it. If the owner intended raw takings after all, the bands — not this model — are what must change, and the entry shop would need a cheaper household to survive.

## 6. What Passed

- **No SURVIVAL FAIL, no IMPLAUSIBLY FAST, no RENT BURDEN rows** in the whole 34-row run — v1 had 1 + 9 + 0.
- **No BRIDGE FAIL:** every profession can now start the game and reach its first payday above water.
- **The wage ladder stays monotone:** every profession's net rises entry → mid → senior, and no junior out-saves a senior of the same line.
- **The flagship start still works:** the owner's reference household (civil engineer, entry) is comfortable-but-not-rich at +5,800/mo — inside GDD-03 §1's intended band (grind < 5,000, holiday > 15,000).

*End of report. The v1 report stands unchanged as the before-state; this file is the after-state. Any further rebalancing is a new unit with its own before/after.*
