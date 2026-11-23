# NEXORA — GDD-10: Housing & Home Life

**Unit Z · Version 1.0 · 2026-11-21**
**Parent documents:** `docs/GDD-01-LIFE-AND-DATA-MODEL.md` §4 (the daily tick and the four needs), §5 (household & property model — this document is its living detail), §6 (relationship events; a move is a memory event), §7 (class mobility runs through housing), §8 (the ledger) · `docs/GDD-02-RUPSHA-CITY-DISTRICT1.md` §5 (which homes get interiors), §6 (property stock) · `data/buildings-district1.json` (the stock itself — every property id cited here resolves to it) · `docs/GDD-03-ECONOMY-AND-PROFESSIONS.md` §3.2 (the rent table **and the missed-rent ladder — owned there, applied here**), §4.3 (mortgage) · `data/prices.json` (`rent_monthly_by_tier`, `loans`, `tax`, `living_costs_monthly` — owns the numbers) · `data/schema.sql` (`properties`, `tenancies`, `households`, `household_members`) · `docs/GDD-06-NPC-BEHAVIOUR.md` §3 (the home anchor), §8 (needs bending the schedule)
**Status:** DESIGN ONLY. No tenancy, furniture or visitor system exists yet; the only built interior anywhere in the project is the Phase 1 test scene's job list. This document is the contract Phase 5/6 implements against.

> **Design law:** a home is an *economic state plus a needs engine*. Every housing fact is a row (a tenancy, a ledger payment, a household membership) and every comfort is a number the tick can read. If a housing rule cannot be traced to a property in the data, a ledger row, or a need, it does not ship.

---

## 1. The Stock — Finite by Design

District 1's residential stock is exactly the residential entries of `buildings-district1.json`: **140 units** across 10 parent entries (the three `part_of` showpiece/starter units are counted inside their parents, per the data's own rule). Nothing spawns more housing; scarcity is a designed pressure (§8).

| Property | Type / tier | Units | Rent /mo | Buy | Notes |
|---|---|---:|---:|---:|---|
| `b_d1_oldtown_walkups` | apartment T1 | 24 | 2,500 | — | Cheapest rooms; the eviction floor (§3) and the young-adult first home |
| `b_d1_education_hostels` | apartment T1 | 20 | 2,500 | — | Student beds; students only |
| `b_d1_midtown_tier2_block` | apartment T2 | 6 | 4,000 | 350,000 | |
| `b_d1_oldtown_tier2` | apartment T2 | 16 | 4,000 | 350,000 | |
| `b_d1_midtown_starter_block` | apartment T3 | 24 | 6,000 | 750,000 | Contains the player starter flat (interior, `for_rent`) |
| `b_d1_midtown_block_b` | apartment T3 | 18 | 6,000 | 750,000 | Contains the midtown showpiece flat (interior, `for_sale`) |
| `b_d1_oldtown_rowhouses` | house T3 | 6 | 6,000 | 750,000 | |
| `b_d1_uptown_tier4_houses` | house T4 | 8 | 12,000 | 1,800,000 | Contains the uptown showpiece flat (interior, `for_sale`) |
| `b_d1_riverfront_houses` | house T5 | 6 | 25,000 | 4,500,000 | |
| `b_d1_uptown_luxury_apts` | apartment T5 | 12 | 25,000 | 4,500,000 | Contains the rooftop flat (interior, `for_rent`) |

Rent and buy figures are **not restated from memory**: they are the per-unit values in the data, which the Unit L validator already proved equal to the `prices.json` tier table (GDD-03 §3.2). If a number here ever disagrees with the data, the data wins and this table is fixed.

## 2. Moving In

1. **Browse what is actually free.** A unit is available when its parent entry has `for_rent_units` / `for_sale_units` > 0, or it is a named interior unit with status `for_rent` / `for_sale`. Browsing is physical in v1: the player visits the building (door interaction; the three showpiece interiors of GDD-02 §5 exist precisely so a home can be *seen* before it is rented). NPC households browse by the same availability, off-screen.
2. **Eligibility is arithmetic, not a gate:** the household pool must cover the deposit + first month (§3) at signing. No credit score, no class check — a Lower-income household that has saved the deposit can sign for a Tier 3 flat, and the economy will judge the choice monthly, not at the door.
3. **Signing writes three things in one transaction:** a `tenancies` row (property, household, `rent_per_month` from the tier table, start time), the household's `home_property_id` updated, and the ledger rows (deposit + first month, reason `rent`). The property's free-unit count drops; a named unit's status flips to `rented`.
4. **Deposit (rule owned by this document):** one month's rent, refundable, held as a ledger liability of the landlord account — not spent income. It is returned at move-out (§4), never silently absorbed by mid-tenancy arrears (§3).
5. **The canonical first move-in** is the owner's start (GDD-03 §1): the starter flat, deposit 6,000 + first month 6,000 = 12,000 of the 25,000 starting balance, leaving 13,000 — the reference household's first month then runs on the §3.2 outgoings exactly as the simulator models them (Queue 4 proved that month ends positive).

## 3. The Rent Cycle & Missed Rent

- **Cycle:** rent is paid on the 1st of the in-game month from the household pool to the property's owner account (an NPC landlord household, a business, or the city for civic-held stock) — a ledger row, reason `rent`, every month, no exceptions (GDD-03 §3.2; GDD-01 §4 step 2 runs it inside the economy tick).
- **The ladder is GDD-03 §3.2's, applied exactly:** missed rent → **7-day grace** → **warning** (a memory event for Full-tier members; the landlord relationship edge takes a trust hit) → **eviction to a Tier 1 room**. Debt is real and stays on the ledger after eviction; **homelessness is not a game state** — an evicted household lands in `b_d1_oldtown_walkups` if a unit is free. This document adds only the mechanics §3.2 leaves open:
  - *Partial payment counts.* Paying part of the rent pays down the arrears; the ladder advances on the *unpaid remainder*, and a household that clears arrears inside the grace window exits the ladder with only the warning's memory behind it.
  - *The deposit is not arrears cover.* It settles only at move-out (§4); a landlord may not quietly consume it month by month.
  - *Eviction is a household event, not a deletion:* members, furniture (§5) and relationships move with the household; the tenancy row closes with `ended_at_game_minutes` set, the property returns to the market.
- **Rent never changes inside a tenancy.** A tier-table tuning change (like Queue 4's) applies to *new* tenancies; existing tenants keep their signed rent until they move. The simulator's bands describe new lets.

## 4. Moving Out & Moving Up

- **Voluntary move-out** happens at a month boundary (the month is paid; no pro-rata refunds — one rule, no arguments). Deposit returns in the same transaction, minus any itemised repair rows (damage is a ledger `purchase` row with a reason, visible to the player — never a silent deduction).
- **The property ladder is the game's visible climb** (GDD-01 §7 mobility): T1 room → T2 flat → T3 apartment → T4 house → T5 riverfront/uptown. Each rung is reachable from the profession bands the simulator verified (Queue 4: civil-engineer entry saves 5,800/mo after the fix — the T3 deposit is ~26 months of saving, a T2 deposit ~14; slow enough to mean something, fast enough to plan for).
- **Household splits are moves too** (GDD-01 §5 events): a Young Adult leaving home forms a new household and signs their own tenancy (usually T1 — that is what the walkups are *for*); marriage/partnership merges two households into one home and closes the other tenancy. Every move is a memory event for Full-tier members.

## 5. Furniture Tiers

Furniture is what turns a rented box into the needs engine of §6. Four furnishing levels, defined by contents, mapped onto — not confused with — property tiers:

| Level | Name | Contents (design list) | One-off package cost |
|---|---|---|---:|
| F0 | Bare | Floor mattress, single burner, crate table — what an eviction landing looks like | 0 (scavenged/starter) |
| F1 | Basic | Bed, table + chairs, stove, wardrobe, fan | 2× the property tier's monthly rent |
| F2 | Comfortable | F1 + sofa, bookshelf, desk, better kitchen, curtains | 4× monthly rent |
| F3 | Full | F2 + dining set, TV, washing machine, study corner, decoration | 7× monthly rent |

Computed from the tier table (the only arithmetic this document does): a Tier 3 flat furnishes at **F1 12,000 / F2 24,000 / F3 42,000**; a Tier 1 room at 5,000 / 10,000 / 17,500; a Tier 5 house at 50,000 / 100,000 / 175,000. These are **GDD-owned v1 package prices derived from the `prices.json` rent table** — `prices.json` has no furniture table today, and an itemised furniture catalogue is recorded as a future data unit in §9 rather than invented here. *(Update, Unit DE · Queue 16: the itemised catalogue now exists — `data/furniture.json` + `prices.json` `furniture` (v1.4) — and the piece prices are the future unit's, labelled PROPOSED, priced to sum to the Tier-3 packages above; the package prices in this section are unchanged.)*

- **Furniture belongs to the household**, not the property: it moves when they move (a moving cost row if the move crosses tiers), and can be sold back to the market shops at **50%** — the second-hand rule that makes furnishing a decision, not a sink.
- **The starter flat seeds at F1** (GDD-02 §5 calls it "furnished tiers" — F1 is that tier, included in the canonical start, not charged again). *(Update, Unit DJ · Queue 17: implemented in the sim — `lost_items.seed_furniture_at_move_in()` seeds the F1 set (the F0 + F1 pieces, 8 inventory rows owned by the household head) at the three points a household takes a home: genesis placement, `households.move_household`, and `households.leave_home`. The rule is the starter-flat rule generalised: no source maps a property tier to a furniture tier, so every move-in seeds F1 and a household that already holds furniture is never re-seeded (furniture moves with the household, above). F2/F3 upgrades wait for a purchase point — no such point exists in the sim yet.)*
- **F2/F3 pieces are bought, not seeded** (Unit EM · Queue 20 · 2026-11-23 — the purchase point, specified here; no live call site exists yet). The purchase event is the Phase 5/6 home loop's `purchase_furniture()` (named here, not implemented): the household head buys any catalogue piece at its `prices.json` `furniture` price (via the piece's `price_ref` — the PROPOSED piece prices, which sum to the §5 Tier-3 packages: F1 12,000, F2 additions 12,000, F3 additions 18,000), paying from the household pool with the existing ledger `purchase` row to SYS-MARKET, and the event seeds the row via `lost_items.seed_furniture_rows()` at the home property, condition 100. No invented prices, no new currency — the catalogue price is the price, and the package prices above still govern furnishing a whole tier (buying the full F2 set costs the package price, 24,000 at Tier 3, because the pieces sum to it). Single pieces are the point: buying one F2 sofa without the F1 set does not raise the tier — the effective tier is cumulative (GDD-04 §3.3, Unit EF), so the tier follows the pieces actually held. The purchase event must write a second row for a piece the head already holds (a replacement beside a lost or broken original) — the seeding helper's skip rule ("pieces already held are skipped") is a seeding rule, not a purchasing rule, and a purchase is not a seeding. Why not the existing purchase points: the market retail allocation buys monthly goods (transient, consumed by the next month's allocation — CX), and furniture is durable, kept at the home; the vehicle purchase sweep is the pattern the event mirrors (monthly sweep, ledger `purchase`, seed the row beside the operational insert), not a call site it reuses. Until the home loop lands, F2/F3 are unreachable in a live world and the effective tier caps at F1 in practice — recorded, not hidden.
- **Effect (tuning owned here):** furniture scales the home restore rates of §6 — F0 ×0.7, F1 ×1.0, F2 ×1.15, F3 ×1.3. An unfurnished upgrade is a worse home than a furnished smaller one; the numbers make sure the player can feel why. *(Update, Unit EF · Queue 19 · 2026-11-23: the effective-tier rule is implemented in `tools/sim/lost_items.py` — `effective_furniture_tier()` (the highest tier whose pieces ALL stand, condition > 0) and `furniture_restore_multiplier()` (the §5 numbers above, or None when no tier stands — no fallback rate invented). No live consumer reads it yet: the needs engine applies fixed home restores, and wiring the multiplier into it is Phase 5/6 work.)* *(Update, Unit EI · Queue 20 · 2026-11-23: DECIDED — a lost piece drops the effective tier: a piece counts as standing only when held with condition > 0 AND no `lost_items` row for it stands `lost` or `found`; a `returned` piece stands again. The multiplier measures what the home actually provides tonight, so a piece in a stranger's or a finder's hands provides nothing — and the drop is reversible, the hand-back restoring the tier, which is the §3.1 favour's payoff. See GDD-04 §3.3.)*

## 6. The Home Needs Loop (GDD-01 §4, at home)

The tick's four needs — **rest, food, social, security** — are restored primarily at home. Each row names its source, its furniture interaction, and what a deficit does (deficits bend tomorrow's schedule, GDD-06 §8):

| Need | Home source | Furniture / property effect | Deficit symptom |
|---|---|---|---|
| Rest | Sleep in own bed during the schedule's Sleep block | Restore rate × furniture scale (§5); lane-noise at T1 oldtown caps at 0.9×, uptown/riverfront full | Late wake, Work sub-state errors, nap wants |
| Food | Home cooking from the household pool (`food_home_cooking` line) | Requires a kitchen: F1+ has one; F0 shares the building kitchen (half rate, queueing at peak) | Eating-out spend rises (the sim's `eating_out_monthly` line is this leak, priced) |
| Social | Household members home together in Leisure blocks; visitors (§7) | F2+ sofa/dining makes home social restore beat the tea stall; below that the tea stall wins — which is why the stalls are social hubs (GDD-02 §5) | Loneliness wants, more Leisure spent outside, relationship drift stalls |
| Security | Stability of tenure itself | Owned > long tenancy > new tenancy > on the missed-rent ladder; furniture has no effect — locks are not a stat | Anxiety events, conservative spending (household pool hoards), class-label pressure (GDD-01 §7 window) |

**Honesty note:** there is no burglary or home-crime system in v1 and none is implied by "security" — the need models *stability*, and this document will not pretend a lockpicking minigame exists. If crime is ever designed, it is its own document.

**Interiors honesty:** only the GDD-02 §5 interiors are walkable in Phase 5 (the starter flat + three showpieces among homes). Every other home delivers its needs effects through the door interaction + tick until its interior is built — the simulation is whole, the walk-in set is partial, and the design says so.

## 7. Visitors & Household Life

- **A visitor is a presence, not a member:** invitations flow from relationship edges (GDD-01 §6.2 — a guest accepts based on the host's outgoing affection/trust; a rival does not come to dinner). A visit is an event at the host's home anchor: social restore for everyone present, relationship drift from the evening, a memory for Full-tier participants.
- **Staying over:** up to 3 nights as a guest event (the host's furniture tier decides whether the guest restores rest properly — F0 has no spare anything). Beyond 3 nights the stay must resolve: the guest leaves, or a **roommate event** fires — `household_members` gains a `roommate` row, the guest joins the household pool, and rent splits by pool contribution (equal shares by default; the head can set custom shares, Phase 6 UI).
- **Noise and neighbours:** gatherings in lane housing (oldtown) carry a neighbour-relationship cost the uptown houses don't — adjacency is in the zone design (GDD-02 §2), and home life is where it is felt.
- **Children change the housing maths:** a `have_child` event (GDD-01 §6.3) adds a *room want* to the household's goals — a T1 room with a child generates a persistent want for T2+, which is the quiet engine behind most NPC moves the player will ever witness.

## 8. Owning, Landlords & the Seed

- **Buying** follows GDD-03 §3.2/§4.3: full price, or a mortgage (`prices.json` `loans`: 20% deposit, 9% annual, ≤20 years; the property is collateral). An owner-occupier stops paying rent and instead pays the property tax (0.5% of value per year, `prices.json` `tax`) — ownership is cheaper monthly and heavier yearly, by design.
- **The purchase writes a property deed** (Unit EN · Queue 20 · 2026-11-23 — the deed seeding, specified in GDD-04 §3.3 and wired in the sim): at the purchase event — cash (`decisions._cand_buy_home`) or mortgage (`decisions._cand_buy_home_mortgage`) — the buyer is issued a `property_deed` document row (`data/documents.json`), state `{"property_id": <the bought property>}`, beside the ownership update. Issued, not bought: no ledger charge, no price (the deed's `price_ncr` is 0 = unpriced, not free — the paper's value is the right it records). The deed is the paper; the `properties` row is the right — losing the paper loses nothing else (the DN rule for credentials, applied here), and the paper can be lost via `record_loss()` and recovered via the §3.1 favour like any document. Mission 3.2's deed reward ("Property deed (Tier 2 flat)") is the same row written by the Phase 6 mission system when the mission completes — one helper (`lost_items.seed_document_row()`), two call sites, one rule. Open edge, recorded: a re-purchase of the same property after a foreclosure is refused by the helper's duplicate guard (the same `property_id` state), so the old deed row stands — the foreclosure-to-repurchase deed lifecycle is a later unit's job.
- **Becoming a landlord** is the entrepreneur rung: an owned spare property can be let — a tenancy row with another household as tenant, rent income as ledger rows to the owner. Player landlords inherit the §3 ladder as the *creditor* side, including its memories.
- **The seed:** Scheduled NPC households are placed across the 140 units by income band (the simulator's rent tiers are the placement rule), ~20% of units listed for sale at world start (GDD-02 §6). If a band's stock is full, a new household doubles up as roommates (§7) — **the stock never grows to meet demand**; pressure shows up as doubled-up households and rising wants, which is the city feeling alive inside a finite map.
- **Ambient NPCs have no homes** (GDD-01 §2/§4): they are visual life. The design never gives the crowd fake addresses.

## 9. What This Document Deliberately Does Not Decide

- **An itemised furniture catalogue in `prices.json`** — package pricing (§5) holds until a data unit prices individual pieces; the market shops' stock list waits for the same unit. *(Update, Unit DE · Queue 16: the catalogue now exists — `data/furniture.json` (the 18 pieces of §5) + `prices.json` `furniture` (v1.4), pieces priced PROPOSED to sum to the §5 Tier-3 packages; package pricing still governs furnishing a tier, and the market shops' stock list still waits for a purchase point.)* *(Update, Unit EM · Queue 20: the purchase point is now specified in §5 — the Phase 5/6 home loop's `purchase_furniture()` event, at catalogue price through the existing ledger `purchase` row — but the event itself is not implemented yet, so the shops' stock list still waits for the home loop.)*
- **Property value dynamics** — `properties.market_value` is set by the economy (schema note); the appreciation/depreciation model belongs to the Phase 6 economy tuning, not to housing.
- **Home businesses, subletting, short-stay letting** — not in v1; a shop is a commercial property with its own loop (GDD-03 §5), not a room in a home.
- **Interior layouts beyond the GDD-02 §5 list** — Phase 5 builds what is listed; this document does not smuggle new interiors into scope.
- **Multiplayer housing contention** (two players, one flat) — Phase 9 server rules (TECH-MULTIPLAYER) arbitrate; the tenancy row is the unit of contention when they do.

## 10. Acceptance Checks (for Phase 5/6 implementation)

- [ ] Move-in writes exactly one tenancy row, one home-property update and the deposit + first-month ledger rows in a single transaction; the canonical starter-flat signing leaves the reference household at 13,000.
- [ ] Rent day moves every active tenancy's rent household → owner with reason `rent`; the missed-rent ladder (grace → warning → eviction to Tier 1) reproduces GDD-03 §3.2 step for step, with partial payments shrinking the arrears.
- [ ] Every property id and rent/buy figure cited in §1 matches `buildings-district1.json` / `prices.json` (script-checked in this unit; re-run when the data changes).
- [ ] A night's sleep restores rest at the furniture-scaled rate; an F0 eviction landing is measurably worse than the F1 starter flat.
- [ ] A guest's 4th night cannot pass without the roommate event or departure firing.
- [ ] The seed places Scheduled households only in existing units; the district's occupied-unit count never exceeds 140.
