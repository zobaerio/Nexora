# NEXORA — GDD-03: Economy & Professions

**Unit F · Version 1.0 · 2026-11-20**
**Parent documents:** `NEXORA-MIGRATION-PLAN.md` Part C #12 (economy), #11 (professions) · `docs/GDD-01-LIFE-AND-DATA-MODEL.md` §7–§8 (classes, ledger) · `data/professions.json` (income bands — this document is the tuning owner of those numbers) · `docs/GDD-02-RUPSHA-CITY-DISTRICT1.md` (workplaces, property tiers)
**Currency:** Nexora Credits (NCr). All money is integer minor units; no floats near money, ever (GDD-01 §8). Every number below is **v1 tuning** — the economy is balanced by playtesting Phase 6, not by this document being right first time.

> **Design law:** money is conserved. Every credit that appears in a wage, a sale or a reward comes out of a system account or another character's account as a ledger row (GDD-01 §8). There is no "spawn money" button anywhere in the design — not for the player, not for NPCs, not for missions. If a number in this document cannot be paid from an existing account, the number is wrong, not the rule.

---

## 1. The Owner's Start — the Reference Household

The economy is tuned so the owner's example card is the default new-player start and is *comfortable but not rich*:

| Item | Value |
|---|---|
| Character | Zobaer Hasan, Civil Engineer (entry), age 28 |
| Balance | 25,000 NCr (one month of entry wages + a small buffer) |
| Housing | Rented 2-room apartment, `d1_residential` mid tier — 6,000 NCr/month |
| Job | Entry engineering post, 22,000 NCr/month |
| Monthly outgoings at start | Rent 6,000 + food 4,500 + transport 1,200 + utilities 800 = **12,500 NCr** |
| Monthly surplus at start | **≈ 9,500 NCr** — enough to save toward a goal, not enough to feel rich |

If playtesting shows the start is a grind (surplus < 5,000) or a holiday (surplus > 15,000), rent and food are the tuning knobs — never the wage bands, which the profession data owns.

## 2. Wages — Monthly Pay by Profession and Tier

Source: `data/professions.json` `income_band_monthly`. Reproduced here as the canonical table; if the JSON and this table ever disagree, **the JSON is the file the game reads — fix this document, not the JSON**, and note the change in the PR.

| Profession | Entry | Mid | Senior | Paid | Notes |
|---|---|---|---|---|---|
| Construction Worker | 9,000 | 14,000 | 20,000 | Daily (day wage) | Day-wage: paid per worked day; no work, no pay. |
| Civil Engineer | 22,000 | 38,000 | 65,000 | Monthly | **Flagship loop §6.** Entry = the owner start. |
| Doctor | 30,000 | 55,000 | 95,000 | Monthly | Clinic in District 1; hospital tower is Phase 8. |
| Teacher | 15,000 | 24,000 | 38,000 | Monthly | Anchors child/teen stages (GDD-01 §3). |
| Police Officer | 18,000 | 28,000 | 45,000 | Monthly | District patrol; fine income goes to the city, never the officer. |
| Taxi Driver | 14,000 | 23,000 | 36,000 | Per fare | **Playable loop §8.** Income varies with demand (rain ↑). |
| Chef | 13,000 | 22,000 | 40,000 | Monthly | Restaurant + street-food tiers. |
| Software Developer | 28,000 | 52,000 | 90,000 | Monthly | Remote-friendly; office in `d1_commercial`. |
| Shop Owner | 12,000 | 26,000 | 55,000 | Daily takings | **Playable loop §7.** Profit, not wage — varies with footfall and stock. |
| Business Owner | 40,000 | 110,000 | 300,000 | Monthly draw | Draw from the business ledger, capped by actual profit. |
| Pilot | 45,000 | 95,000 | 180,000 | Monthly | No District 1 workplace; commutes out (Phase 8 travel). |

**Progression rules (all professions):**
- Tier rises on **skill + reputation + time-in-post**, never on money spent. Buying a promotion is not a mechanic.
- Entry → Mid: skill 40 in the profession's primary skill + 30 in-game days in post + reputation ≥ 20 in that profession.
- Mid → Senior: skill 70 + 90 in-game days + reputation ≥ 50.
- A character who quits or is fired keeps skill and reputation but loses the post; re-hiring starts at the tier their skill supports, not at entry.
- NPCs follow the same table with the same rules (GDD-01: one model for everyone).

## 3. Prices — What Things Cost (v1)

### 3.1 Daily living (per month, single adult, District 1)

| Item | Lower tier | Mid tier | Upper tier |
|---|---|---|---|
| Food (home cooking) | 2,500 | 4,500 | 9,000 |
| Eating out (regular) | 150/meal | 350/meal | 900/meal |
| Transport — bus/rickshaw | 800 | 1,200 | — |
| Transport — own car (fuel + upkeep) | — | 3,500 | 8,000 |
| Utilities (power, water, internet) | 500 | 800 | 2,000 |
| Clothing / personal | 600 | 1,500 | 5,000 |
| Eating out (monthly budget) | 300 | 1,050 | 3,600 |
| Household services & family support | 0 | 800 | 2,500 |

**Tier scaling (Queue 4, §11):** the table above is the *entry-tier* household. Above entry, living costs also rise by the **lifestyle uplift**: 35% of the raise (tier wage − entry wage) is consumed by lifestyle — eating out more, household help, family support, better transport. This is what stops senior tiers saving 71–84% of gross (simulator Finding 2) without inventing a separate price list per tier. The 35% lives in `prices.json` `lifestyle_uplift` and is the single knob if playtesting wants senior savings looser or tighter.

### 3.2 Rent (per month, District 1)

| Property tier | Type | Rent | Buy price (guide) |
|---|---|---|---|
| Tier 1 | Single room / shared flat | 2,500 | — (not sold) |
| Tier 2 | 1-room flat | 4,000 | 350,000 |
| Tier 3 | 2-room apartment | 6,000 | 750,000 |
| Tier 4 | 3-room house, small garden | 12,000 | 1,800,000 |
| Tier 5 | Riverfront house / rooftop flat | 25,000 | 4,500,000 |

Rent is paid on the 1st of the in-game month from the household pool (GDD-01 §5). Missed rent: 7-day grace, then a warning, then eviction to a Tier 1 room — debt is real, homelessness is not a game state. Buying requires the full price or a mortgage (§4.3).

### 3.3 Vehicles (buy price, NCr)

| Vehicle | Price | Notes |
|---|---|---|
| Bicycle | 8,000 | No fuel cost; the honest starter vehicle. |
| Rickshaw (own, for work) | 25,000 | Taxi-driver starter option. |
| Motorbike | 120,000 | The District 1 workhorse. |
| Car (small) | 450,000 | Mid-tier goal. |
| Car (premium) | 1,200,000 | Upper-tier marker. |
| Taxi (licensed cab) | 650,000 | Needed for the taxi loop at scale; rentable by the day (200/day) first. |

### 3.4 Construction materials (per unit, market-priced — the Civil Engineer loop buys these)

| Material | Unit | v1 price | Notes |
|---|---|---|---|
| Cement | 50 kg bag | 550 | Price index moves ±15% with the market (§5). |
| Brick (1st class) | 1,000 pcs | 12,000 | |
| Rebar (60 grade) | tonne | 95,000 | |
| Sand (river) | cubic ft | 45 | |
| Stone aggregate | cubic ft | 60 | |
| Tiles (floor) | sq ft | 85 | |
| Paint (weathercoat) | litre | 420 | |

These are the numbers the estimate step of the flagship loop (§6) multiplies by real quantities. They are deliberately close to real Khulna market levels in NCr so the estimating skill transfers.

## 4. Money Systems

### 4.1 The ledger (recap — GDD-01 §8 owns the shape)
Every movement is an `economy_ledger` row with a reason code (`wage, rent, purchase, sale, tax, inheritance, mission_reward, loan, loan_repayment, business_draw, construction_payment`). Balance is derived from the ledger; the cached balance is rebuilt from it on disagreement. Only the server writes ledger rows in multiplayer (Phase 9).

### 4.2 Tax
- **Income tax:** 0% under 15,000/month; 5% on 15,001–40,000; 10% above 40,000. Deducted at pay time, paid to the city account. Simple, visible, and shown on every payslip.
- **Property tax:** 0.5% of property value per in-game year, paid to the city. Funds the city's services (street lights, road repair — the things the player sees).
- **Business tax:** 8% of monthly business profit, paid from the business ledger.
- Tax is never a surprise: the amounts are shown before the player commits to a job, a purchase or a draw.

### 4.3 Loans & mortgages
- **Bank loan:** up to 5× monthly income, 12% annual interest, max 24 in-game months, repayments auto-deducted. The bank is a system account — it can only lend what it holds; if the bank is empty, loans stop (this is a feature, not a bug — it is the anti-collapse test).
- **Mortgage:** 20% deposit, 9% annual interest, up to 20 in-game years. The property is collateral: default → repossession, sold at market, debt settled from the sale.
- **No payday lenders, no hidden fees.** Debt is a tool with visible terms, not a trap mechanic.

### 4.4 Savings & the price index
- Savings earn 4% annual interest, paid monthly from the bank account.
- A **price index** (base 100 at game start) tracks the average of §3 prices. It drifts with supply/demand events and the total money supply (queryable — the Phase 6 "economy does not collapse" test reads it). If the index moves more than 10% in 30 in-game days, the economy team re-tunes — that movement is a bug report, not a feature.

## 5. Business Ledger Model

Every business (shop, construction firm, taxi fleet, restaurant) is a `businesses` row with its own ledger — the same append-only shape as the character ledger (GDD-01 §8), scoped to the business:

- **Income:** sales, contract payments, fares. **Outgoings:** stock, wages, rent, tax, loan repayments.
- **Owner draw:** the owner takes a monthly draw (Business Owner wage band, §2) *only* from profit — if the business made 30,000 profit, the draw cannot be 40,000. The game enforces this; the player learns it once and never forgets it.
- **Employees:** NPC or player employees are paid from the business ledger on the same schedule as §2. A business that cannot pay wages loses staff (reputation hit) and then customers.
- **Failure:** a business with negative balance for 30 in-game days enters distress (suppliers stop credit, staff leave); at 60 days it closes and its assets sell. Failure is recoverable — the owner keeps skills and reputation, loses the business. This is why the class bands move in both directions (GDD-01 §7).

## 6. Flagship Loop — Civil Engineer (playable, Phase 5)

The owner's real profession, turned into the game's signature job loop. One job, end to end:

1. **Take a job** — from the job board (city office / notice board / app): a client wants a house/shop/extension. The job states plot, budget, deadline, and a quality bar. Taking it costs nothing; abandoning it costs reputation.
2. **Produce the plan** — in the plan tool: footprint, rooms, floors, structural grid. The plan is checked against the plot and the budget *before* anything is bought. A plan over budget is rejected by the client, not by the game — the player revises it.
3. **Estimate materials** — the estimate step multiplies **real quantities** (cement bags, brick count, rebar tonnage, sand/stone volume) by the §3.4 market prices and presents a BOQ-style estimate. The client pays the estimate plus the engineer's fee (10% of material cost at entry, 15% at senior). An estimate that is wrong by more than 10% against actuals costs reputation — estimating is a skill, and the skill number gates senior work.
4. **Supervise staged construction** — construction runs in stages (foundation → structure → roof → finishes), each stage taking in-game days and requiring the engineer on site for inspections. Stages cannot be skipped; a skipped inspection risks a defect event (rework cost, reputation hit). Rain halts outdoor stages (`outdoor_work_halted` weather effect).
5. **Payment** — per completed stage, from the client's account to the engineer's (ledger rows, reason `construction_payment`). The final payment needs the client's sign-off, which needs the quality bar met.
6. **Reputation** — on-time + on-budget + quality → reputation up, next job bigger. Late or over-budget → reputation down, smaller jobs only until it recovers.

**Numbers for the first job (tuning):** single-room extension, budget 120,000 NCr, materials ≈ 85,000, fee ≈ 8,500–12,750, duration ≈ 12 in-game days. A player doing one job a month at entry earns ≈ 22,000/month — exactly the §2 band. The loop and the wage table agree by construction.

## 7. Shop Owner Loop (playable, Phase 6)

1. **Stock** — buy from wholesalers (market prices, §3.4-style catalogue for goods). Stock is inventory, not magic: it occupies shelf space and expires (perishables).
2. **Price** — set shelf prices. Above the market band, footfall drops; below it, margin dies. The district's footfall depends on location (`d1_market` > side street) and on weather (rain drives customers under cover — into the shop).
3. **Sell** — daily takings land in the business ledger. Regulars form (relationship scores, GDD-01 §6) and regulars spend more.
4. **Grow** — profit funds a bigger shop, more stock lines, an employee. The §2 bands (12k → 26k → 55k) are the **profit** milestones the loop is tuned to — revenue minus stock, rent and staff (§5), not wages and not raw takings. *(Wording corrected in Queue 4 / Unit X: v1.0 called these "takings milestones", which contradicted §2's "Profit, not wage" and `professions.json`'s income note; the simulator v2 report records the reconciliation.)*

## 8. Taxi Driver Loop (playable, Phase 6)

1. **Get a cab** — rent by the day (200 NCr) or buy (650,000 NCr, or a loan, §4.3).
2. **Take fares** — passengers hail on the street and at the launch terminal / market / station anchors. Fare = base 60 + 25/km, surge ×1.5 in rain (`taxi_demand_up`) and at night.
3. **Costs** — fuel per km, upkeep per week, traffic fines if the player drives badly (the city account receives them — §2 police note).
4. **Reputation** — on-time, clean cab, fair fares → regulars and better-paying longer fares. Overcharging (a real choice the game allows) pays once and costs regulars forever.
5. The §2 bands (14k → 23k → 36k/month) assume ~25 fares/day at entry, ~40 at senior with a owned cab.

## 9. Economy Health — the Phase 6 Exit Test, Measurable

The master plan's Phase 6 exit criterion ("economy does not collapse") is these queries, run after 30 accelerated in-game days:

| Metric | Pass band |
|---|---|
| Total credits in circulation (sum of all balances + bank) | Within ±2% of day-0 total + minted wages − taxes destroyed. Money is conserved; a leak is a bug. |
| Price index | 95–105 |
| Employment rate (Scheduled tier) | ≥ 85% |
| Businesses closed in 30 days | ≤ 10% |
| Households in rent arrears | ≤ 5% |
| NPC schedule deadlocks | 0 |

If any band fails, the economy is re-tuned in the data (wages, prices, rent) — never by patching the ledger rules.

## 10. What This Document Deliberately Does Not Decide

- The exact wholesale goods catalogue for shops → filled in during Phase 6 implementation from §3's price structure.
- Multiplayer market behaviour (player-to-player trading) → Phase 9; the ledger shape already supports it, the rules do not exist yet.
- Inter-city / inter-planet trade → Phase 8/10; prices in other cities are their own tables, same shape.

## 11. Queue 4 Tuning Log (2026-11-21) — Simulator Findings Fixed in the Data

The Unit T simulator (`docs/ECONOMY-SIM-REPORT.md`) ran the v1 numbers and reported four findings. Queue 4 fixes them here, in the data — each change below names its finding, and `docs/ECONOMY-SIM-REPORT-V2.md` carries the before/after proof from the re-run.

- **Unit U — Taxi rental (Finding 1):** cab rental **800 → 200 NCr/day** (§3.3, §8, `prices.json`). At 800/day an entry driver renting full-time lost ~13,700/month — the rent-before-you-buy on-ramp (§8 step 1) was a bankruptcy trap, and the depot recovered the 650,000 cab price in ~2.6 rental-years besides. At 200/day the renter nets ≈ +1,900/month: clearly worse than owning the rickshaw (+7,100), survivable, and the depot recovers the cab price over ~10 rental-years. The fare band did not move — the loop was sound; the rental price was the disagreement.
- **Unit V — Senior cost scaling (Finding 2):** two new monthly lines (eating-out budget, household services & family support, §3.1) plus the **lifestyle uplift** (35% of any raise above entry is consumed by lifestyle). Senior savings move from 71–84% into roughly the 35–55% band, so the property ladder's top end (a tier-5 house in ~18 months of idle saving) paces properly again. Wages were *not* compressed — the ladder's rewards stay; the costs grow up to meet them, which is also how the derived class display (GDD-01 §7) stays honest.
- **Unit W — Starting balances (Finding 3):** `starting_balance_ncr` is now per profession in `data/professions.json`, sized from the simulator's month-1 dip (zero-start minimum balance × 1.25, rounded up to the next 1,000, minimum 5,000). The civil engineer keeps the canonical 25,000 (§1) — it covers his dip with the intended buffer. A pilot now starts at 44,000 instead of drowning at −34,800 in month one.

*End of GDD-03 v1.0 + Queue 4 tuning log. Changes happen by PR; wage changes update `data/professions.json` and this table together.*
