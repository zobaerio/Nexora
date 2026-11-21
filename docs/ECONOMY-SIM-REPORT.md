# NEXORA — Economy Balance Simulator Report

**Unit T · Version 1.0 · 2026-11-21**
**Tool:** `tools/economy_sim.py` (stdlib-only Python, deterministic — same input, same output) · **Data:** `data/prices.json` only (wages, rent tiers, living costs, tax brackets, taxi fares) · **Parent documents:** `docs/GDD-03-ECONOMY-AND-PROFESSIONS.md` §9 (the Phase 6 economy-health exit test this simulator operationalises), §1 (reference household), §8 (taxi loop)
**Status:** RUN AND RECORDED. The output below is the tool's actual output on the merged data, unedited. Findings are **reported, not fixed** — no data file was changed by this unit; any rebalancing is a follow-up unit the owner approves separately.

> **Rule of this report (per the work queue):** problems are findings, not edits. If a number below looks wrong for the game, the fix is a deliberate data change in its own unit — never a quiet patch smuggled in beside the simulator that found it.

---

## 1. Method (what the simulator does)

30 game-days of household cashflow for all 11 professions at entry/mid/senior tiers (34 rows incl. one variant). One adult living alone; rent tier assigned per profession (T1 construction worker/taxi driver → T4 doctor/business owner/pilot); lifestyle band (food/utilities/clothing from `prices.json` `living_costs_monthly`) set by entry wage — lower ≤15,000, mid ≤40,000, upper above; car transport for doctor/business owner/pilot, public transport otherwise; income tax marginal from the merged brackets. Pay schedules honoured (monthly lands day 30; daily pays 26 workdays; per-fare/takings/draw accrue evenly — a v1 simplification). The taxi driver is modelled twice: owning the rickshaw, and renting the licensed cab at 800 NCr/day on workdays. Start balance 0 for comparability (`minbal` = lowest mid-month balance — the first-month bridge problem, see Finding 3).

## 2. Actual Run Output (verbatim)

```
profession                   tier      gross    tax   rent  costs   net/mo  save%   minbal  flags
construction_worker          entry      9000      0   2500   6900     2100   23.3        0  -
construction_worker          mid       14000      0   2500   6900     7100   50.7        0  -
construction_worker          senior    20000    250   2500   6900    12850   64.2        0  -
civil_engineer               entry     22000    350   6000  14000     7650   34.8   -13533  -
civil_engineer               mid       38000   1150   6000  14000    22850   60.1   -13533  -
civil_engineer               senior    65000   3750   6000  14000    47250   72.7   -13533  IMPLAUSIBLY FAST
doctor                       entry     30000    750  12000  22300     6950   23.2   -21557  -
doctor                       mid       55000   2750  12000  22300   29950   54.5   -21557  -
doctor                       senior    95000   6750  12000  22300   65950   69.4   -21557  -
teacher                      entry     15000      0   4000   8400     6600   44.0    -8120  -
teacher                      mid       24000      450   4000   8400    15150   63.1    -8120  -
teacher                      senior    38000   1150   4000   8400    28450   74.9    -8120  IMPLAUSIBLY FAST
police_officer               entry     18000    150   6000  14000     3850   21.4   -13533  -
police_officer               mid       28000   650   6000  14000    13350   47.7   -13533  -
police_officer               senior    45000   1750   6000  14000    29250   65.0   -13533  -
taxi_driver                  entry     14000      0   2500   6900     7100   50.7        0  -
taxi_driver                  mid       23000    400   2500   6900   15700   68.3        0  -
taxi_driver                  senior    36000   1050   2500   6900    28050   77.9        0  IMPLAUSIBLY FAST
taxi_driver (renting cab)    entry     14000      0   2500  27700   -13700  -97.9   -12247  SURVIVAL FAIL
chef                         entry     13000      0   4000   8400     4600   35.4    -8120  -
chef                         mid       22000   350   4000   8400    13250   60.2    -8120  -
chef                         senior     40000   1250   4000   8400   30350   75.9    -8120  IMPLAUSIBLY FAST
software_developer           entry     28000   650   6000  14000    13350   47.7   -13533  -
software_developer           mid       52000   2450   6000  14000   35550   68.4   -13533  -
software_developer           senior    90000   6250   6000  14000   69750   77.5   -13533  IMPLAUSIBLY FAST
shop_owner                   entry     12000      0   4000   8400     3600   30.0        0  -
shop_owner                   mid       26000    550   4000   8400    17050   65.6        0  -
shop_owner                   senior     55000   2750   4000   8400   43850   79.7        0  IMPLAUSIBLY FAST
business_owner               entry     40000   1250  12000  22300   16450   41.1        0  -
business_owner               mid      110000   8250   12000   22300   79450   72.2        0  IMPLAUSIBLY FAST
business_owner               senior    300000   27250   12000   22300   250450   83.5        0  IMPLAUSIBLY FAST
pilot                        entry     45000   1750   12000   36000     7250   16.1   -34800  -
pilot                        mid       95000   6750   12000   36000    52250   55.0   -34800  -
pilot                        senior    180000   15250   12000   36000   128750   71.5   -34800  IMPLAUSIBLY FAST

professions simulated: 11 (+ taxi rental variant); rows: 34
SURVIVAL FAIL rows: ['taxi_driver (renting cab)/entry']
IMPLAUSIBLY FAST rows: ['civil_engineer/senior', 'teacher/senior', 'taxi_driver/senior', 'chef/senior', 'software_developer/senior', 'shop_owner/senior', 'business_owner/mid', 'business_owner/senior', 'pilot/senior']
TIGHT rows: []
pacing: civil_engineer/entry saves 7650 NCr/mo -> car_small (450000) in 58.8 months; tier-3 deposit (150000) in 19.6 months
```

## 3. Findings

**Finding 1 — REAL PROBLEM: the taxi rental on-ramp does not work at entry tier.**
Renting the licensed cab costs 800 × 26 workdays = **20,800 NCr/month against an entry gross of 14,000** — net **−13,700/month**, the run's only SURVIVAL FAIL. GDD-03 §8 and GDD-07 §2 both describe renting as the designed on-ramp ("rent before you buy"); as priced, a new taxi driver who rents full-time goes bankrupt in the first month. The rickshaw-owning path is fine (+7,100), so the loop itself is sound — the *rental price or the entry fare band* is what disagrees with the design intent. Candidate fixes for a future tuning unit (not applied): lower the daily rental, make rental per-shift rather than per-day, or raise entry per-fare earnings. **This is the one finding that blocks a designed loop and should be fixed first.**

**Finding 2 — STRUCTURAL: senior tiers accumulate implausibly fast (9 rows, 71–84% savings).**
Living costs are flat bands while senior wages run 3–7× entry, so a senior anything saves most of their income (business owner senior: 250,450/month). This is the classic flat-cost artefact: the model has no lifestyle scaling (better housing, family, staff, business reinvestment). It does not break survival anywhere, but it *does* break the property ladder's pacing at the top end — a senior business owner could buy the tier-5 riverfront house (4,500,000) in ~18 months of doing nothing else. A tuning unit should decide whether senior costs scale (tier-up pressure) or senior wages compress. Reported, not decided here.

**Finding 3 — FIRST-MONTH BRIDGE: monthly-paid professions start underwater.**
Every monthly-paid row dips negative mid-month from a zero start (worst: pilot −34,800) because payday is day 30 and costs are daily. GDD-03 already solves this for the player (civil engineer's 25,000 starting balance covers his −13,533 dip) — but the sim shows the *starting-balance rule needs to be profession-aware*: a pilot starting at 25,000 would still dip below zero in month one. NPC households presumably start with history; player starts need the number checked per profession. Design note, not a data error.

**Finding 4 — PACING: vehicle/property goals are far away at entry savings rates.**
Civil engineer (the reference profession) at entry saves 7,650/month → ~59 months to a small car (450,000), ~20 months to a tier-3 mortgage deposit (150,000). Whether that is "grind" or "long-term goals done right" is an owner taste call — but it should be a *call*, made with these numbers visible, not an accident. Note the flagship construction loop (GDD-08) is how this band is actually earned in play: GDD-03 §6 builds the entry band (≈22,000/month) around roughly one job a month, and the sim's pacing therefore assumes the player is *working the loop*, not idling — a player who takes a second job in a month accelerates past these numbers by exactly the fee (8,670 at entry). The loop and the pacing agree, which is good design worth keeping.

**Finding 5 — RECONCILIATION (not a problem): the sim vs GDD-03 §1.**
GDD-03's reference household quotes outgoings 12,500 and surplus ≈9,500 for the entry civil engineer. The sim computes net 7,650. The difference is exactly itemised: the sim adds income tax (350) and clothing/personal (1,500), which GDD-03's reference table did not list. Both are "right" — GDD-03 §1 is a four-line sketch; this sim is the fuller household. Flagged so nobody later "fixes" either number in ignorance of the other.

**Finding 6 — MODEL CAVEAT: business incomes are pre-cost.**
`shop_owner` and `business_owner` bands are takings/draw figures; the sim treats them as personal income without stock, staff or premises costs beyond home rent (business tax is also not separated from income tax in v1). Their rows — including business owner senior's 83.5% — should be read as *upper bounds*. A v2 simulator should run businesses through the GDD-03 §5 business ledger properly. Caveat recorded; rows kept, because even as upper bounds they feed Finding 2 honestly.

## 4. What Passed

- **No profession fails to survive on its own wage at any tier** — the single SURVIVAL FAIL is the rental *variant*, not a wage band. GDD-03 §9's core exit question ("can every band live?") answers yes for wages as merged.
- **No TIGHT rows and no RENT BURDEN rows** — entry rents run 14–40% of gross across professions; the thinnest honest margin is the entry construction worker at +2,100/month (23%), which reads as intended pressure for the day-wage starter, not an error.
- **The wage ladder is monotone and sane:** every profession's net rises entry → mid → senior; no inversions (e.g. no junior out-saving a senior of another line in a way that breaks the ladder's story — cross-profession comparisons like senior chef (30,350) vs entry doctor (6,950) are tier effects, not inversions).

## 5. Recommended Follow-ups (for the owner to approve as separate units)

1. **Taxi rental fix** (Finding 1) — small data change, unblocks a designed loop.
2. **Senior-cost scaling decision** (Finding 2) — design call before any number moves.
3. **Per-profession starting balances** (Finding 3) — one line in GDD-03 §1's family, checked against this sim's `minbal` column.
4. **Simulator v2** — business-ledger-accurate shop/business rows (Finding 6), household sizes >1, and fare-level taxi modelling (trips/day × fare table instead of even accrual).
