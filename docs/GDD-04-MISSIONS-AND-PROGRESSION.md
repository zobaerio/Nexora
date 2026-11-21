# NEXORA — GDD-04: Missions & Progression

**Unit G · Version 1.0 · 2026-11-20**
**Parent documents:** `NEXORA-MIGRATION-PLAN.md` Phases 3–10 · `docs/GDD-01-LIFE-AND-DATA-MODEL.md` §2.2 (goals), §3 (life stages) · `docs/GDD-03-ECONOMY-AND-PROFESSIONS.md` (job loops, rewards) · `docs/GDD-02-RUPSHA-CITY-DISTRICT1.md` (locations)
**Levels:** the owner gave the structure's endpoints — Level 1 **"A New Beginning"** and Level 8 **"Space Explorer"**. Levels 2–7 below are proposed from the Phase 1–10 roadmap so the progression has a complete shape; the owner confirms or renames them — the missions, not the names, are the design.

> **Design law:** missions are *offers*, not orders. NEXORA never fails a player for living differently (GDD-01 §2.2). A level is a bundle of missions and unlocks the player can work through at their own pace, in any order within the level, while free-roaming the whole time. There is no mission timer that ends a playthrough, no "game over" for ignoring the main path, and no mission that requires a purchase or a grind the economy cannot support (GDD-03 §9).

---

## 1. How Levels Work

- **Levels 1–8** are progression chapters. Each level has 3–5 main missions + side missions that stay available afterwards.
- **Advancing a level** requires completing its main missions (all of them, in any order). Side missions and free-roam work count toward rewards but never gate advancement.
- **Rewards** are always one of: credits (ledger, reason `mission_reward`), reputation, a skill boost, an unlock (place, vehicle, tool, mechanic), or a story beat (a memory event, GDD-01 §2.3). Rewards are never a stat the player cannot also earn by free-roam play — levels accelerate, they do not monopolise.
- **A mission reads the goal stack** (GDD-01 §2.2): the game offers missions matching the player's chosen life goal first. A player whose life goal is "own a construction company" sees construction missions; a player who chose "become chief surgeon" sees clinic missions. The level structure is the same; the content bends.
- **Failure:** a mission can fail (deadline missed, client unhappy). A failed mission can be retried after 7 in-game days, or abandoned for a reputation cost. The level is never blocked by one failed mission — the retry is the design.

## 2. The Levels

### Level 1 — A New Beginning
*Arrive in Rupsha City, District 1. The owner's start: rented apartment, entry job available, 25,000 NCr.*

| # | Mission | Objectives | Reward | Unlock |
|---|---|---|---|---|
| 1.1 | First Steps | Arrive at the launch terminal; walk to your apartment; sleep one night | 1,000 NCr, +5 reputation (district) | Apartment (home anchor), bicycle purchase |
| 1.2 | A Job to Do | Visit the job board; take any entry job; complete one full work day | First wage (per GDD-03 §2) | Job board filters, work uniform |
| 1.3 | Know Your Neighbours | Meet 3 neighbours; help one with a small task (carry, fetch, fix) | +10 relationship (each), +5 reputation | Neighbour favour system |
| 1.4 | The River at Dusk | Watch the sunset from the riverfront promenade; visit the tea stall | Memory event "First evening in Rupsha" | Promenade leisure anchor, photo mode |

**Level 1 complete →** Level 2 unlocks; the player keeps the apartment and the job.

### Level 2 — Settling In
*Make the district home: a routine, a skill, a small safety net.*

| # | Mission | Objectives | Reward | Unlock |
|---|---|---|---|---|
| 2.1 | Learn the Trade | Reach skill 20 in your profession's primary skill | 2,000 NCr, +10 profession reputation | Skill training (evening classes) |
| 2.2 | Rainy Day Fund | Save 15,000 NCr above your starting balance | 1,500 NCr interest bonus | Bank savings account (4% annual, GDD-03 §4.4) |
| 2.3 | The Market Run | Buy a week's food at Boro Bazar; haggle once, successfully | 500 NCr, +5 market reputation | Haggling, market regular status |
| 2.4 | A Friend in the City | Raise one friendship to 40+ (trust/affection) | Memory event, +10 reputation | Friend favour missions |

### Level 3 — First Home
*Stop renting. Own something, however small.*

| # | Mission | Objectives | Reward | Unlock |
|---|---|---|---|---|
| 3.1 | The Deposit | Save 70,000 NCr (20% of a Tier 2 flat) or secure a mortgage | 3,000 NCr | Mortgage applications (GDD-03 §4.3) |
| 3.2 | House Hunting | View 3 properties; choose one; complete the purchase | Property deed (Tier 2 flat) | Property ownership, furnishing (Phase 5/6) |
| 3.3 | Make It Yours | Furnish the flat from the catalogue (5 items, any tier) | +10 comfort, memory event | Furniture catalogue, home customisation |
| 3.4 | Housewarming | Host 3 friends at home | +15 relationships, +10 reputation | Hosting / social events |

### Level 4 — Master Your Craft
*Become the person the district calls when it matters.*

| # | Mission | Objectives | Reward | Unlock |
|---|---|---|---|---|
| 4.1 | Mid-Tier | Reach Mid tier in your profession (GDD-03 §2) | Wage band rises to Mid | Mid-tier jobs, mentoring |
| 4.2 | The Big Job | Complete one flagship-loop job end to end (Civil Engineer: plan → estimate → supervise → payment; other professions: equivalent loop) | Fee + 5,000 NCr bonus, +20 reputation | Large contracts |
| 4.3 | Teach Someone | Mentor a junior (NPC) to skill 20 | +15 reputation, memory event | Mentoring system |
| 4.4 | Storm Season | Work through one storm week without missing a shift | 2,000 NCr, +10 resilience trait nudge | Weather-hardened reputation |

### Level 5 — Roots & Family
*Life stages turn: partnership, household, the next generation (GDD-01 §3, §6).*

| # | Mission | Objectives | Reward | Unlock |
|---|---|---|---|---|
| 5.1 | Someone Special | Build a relationship to partner level (affection 70+) | Memory event "Partnership" | Partnership / marriage events |
| 5.2 | A Household Together | Form or join a household; share the expense pool | Household management UI | Joint finances, shared property |
| 5.3 | The Next Generation | Welcome a child (birth/adoption event) | Memory event, +20 family reputation | Child life stage, school system |
| 5.4 | The Family Business | Start a business with a family member, or employ one | Business licence fee waived | Family business rules (GDD-03 §5) |

### Level 6 — A Name in the City
*Influence: the district knows you, and the city asks for your help.*

| # | Mission | Objectives | Reward | Unlock |
|---|---|---|---|---|
| 6.1 | Senior Tier | Reach Senior tier in your profession | Wage band rises to Senior | Senior contracts, city advisory |
| 6.2 | The Civic Job | Complete a city contract (school repair, market upgrade, riverfront work) | 25,000 NCr, +30 city reputation | City contracts board |
| 6.3 | Employ Others | Hire 3 employees (NPC) and pay them for 30 days | Business reputation +20 | Employer status, payroll |
| 6.4 | The District Festival | Help organise the district festival (fund, staff, or build) | Memory event, +25 reputation | Festival (annual event) |

### Level 7 — Beyond One City
*District 2, City 2, and the road between them (Phase 8).*

| # | Mission | Objectives | Reward | Unlock |
|---|---|---|---|---|
| 7.1 | The Other Side | Travel to District 2 / City 2; spend 3 nights there | 5,000 NCr, travel memory | Inter-city travel, second home |
| 7.2 | Two-City Business | Open a branch or take a contract in the second city | 15,000 NCr, +20 reputation (new city) | Branch businesses |
| 7.3 | The Long Road | Drive/ride the inter-city route in one trip (no fast travel) | 3,000 NCr, memory event | Route mastery, roadside stops |
| 7.4 | A Bridge Between | Complete a cross-city project (both cities benefit) | +40 reputation (both cities) | Cross-city contracts |

### Level 8 — Space Explorer
*The owner's endpoint: leave the planet. Phase 10.*

| # | Mission | Objectives | Reward | Unlock |
|---|---|---|---|---|
| 8.1 | The Application | Qualify for the space programme (Senior tier + savings 500,000 NCr + reputation 80) | Programme acceptance | Space programme |
| 8.2 | Training | Complete zero-g and survival training (skill challenges) | 10,000 NCr, +30 reputation | Training facility |
| 8.3 | First Launch | Crew the first mission to Nexora-7 (data card in `data/planets.json`) | Memory event "First launch" | Spacecraft, Nexora-7 landing |
| 8.4 | A New World | Establish the first foothold on Nexora-7; return with a survey | 50,000 NCr, title "Space Explorer" | Planetary settlement (Phase 10) |

**Level 8 complete →** the "Space Explorer" title, planetary travel, and the open-ended endgame: the player keeps living — new cities, new planets, new generations (GDD-01 §3).

## 3. Side Missions (always available, never gating)

| Type | Examples | Reward pattern |
|---|---|---|
| Errands | Deliver, fetch, carry, fix for an NPC | 200–2,000 NCr + relationship |
| Work shifts | Extra shifts, overtime, cover for a sick colleague | Wage + reputation |
| Favours | Lend money (ledger loan, GDD-03 §4.3), mediate a dispute, find a lost item | Relationship + small credits |
| Events | Festival stalls, storm clean-up, market day | Reputation + memory events |
| Discovery | Find all landmarks, photograph the district, ride every bus route | 500 NCr each + "Explorer" progress |

Side missions are generated from the simulation (an NPC with a need, a business short-staffed, a weather event) — they are the world asking, not a checklist the designers wrote once.

## 4. Free-Roam Rules

1. **The whole district is open from Level 1.** No area is locked behind a level; levels unlock *tools, contracts and systems*, not geography. A Level 1 player can walk the riverfront, enter the market, and ride to the edge of District 1.
2. **No mission is timed in real time.** In-game deadlines exist (a client wants the job in 12 days) and are shown in in-game days; the player can pause, sleep, and plan. Missing a deadline fails that mission, never the game.
3. **Crime has consequences, not a fail state.** Theft, assault, and fraud are possible choices with police, fines, reputation and jail-time responses (the police profession exists in the world for a reason) — and a record the player lives with. The game never says "you lose".
4. **Money earned free-roam counts everywhere.** A player who ignores missions and runs a taxi for 60 days has the same 36,000/month senior income as a mission player — the economy does not punish free play (GDD-03 §8).
5. **The player can always go home.** The home anchor, sleep, and time-skip are available from Level 1, in every level, in every city.

## 5. Achievements v1 (account-level — they survive character death, GDD-01 §1)

| Achievement | How | Tier |
|---|---|---|
| First Night in Rupsha | Sleep one night in District 1 | Bronze |
| Payday | Receive your first wage | Bronze |
| Neighbourhood Hero | 5 neighbours at relationship 40+ | Bronze |
| Saver | Hold 100,000 NCr at once | Silver |
| Homeowner | Own any property | Silver |
| Master Craftsman | Reach Senior tier in any profession | Silver |
| Business Owner | Own a business with 3+ employees | Silver |
| Storm Rider | Work 7 storm days without missing a shift | Silver |
| Family Man / Family Woman | Three generations alive in your family tree | Gold |
| City Father / City Mother | City reputation 80+ | Gold |
| Millionaire | Net worth 1,000,000 NCr | Gold |
| Space Explorer | Complete Level 8 | Gold |
| Living Legend | Net worth 2,000,000 NCr + reputation 90 + 3 generations | Platinum |

Achievement data lives on the **account** (GDD-01 §1): a character dies, the account keeps the achievements, and the next character inherits the record — not the money.

## 6. What This Document Deliberately Does Not Decide

- Exact dialogue and cutscene content for each mission → written during Phase 5/6 implementation, from this structure.
- The Level 2–7 names → proposed here; owner confirms or renames (see header note).
- Multiplayer missions (co-op jobs, shared businesses) → Phase 9; the mission shape (objectives, rewards, unlocks) is reused, the party rules are new.

*End of GDD-04 v1.0. Changes happen by PR; level-name changes are a one-line edit each, not a redesign.*
