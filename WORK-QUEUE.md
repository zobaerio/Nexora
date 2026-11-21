# NEXORA — Continuous Development Work Queue

**Owner order (2026-11-20 23:48 Dhaka):** Keep developing continuously, night and day, until the owner says stop. Merge to GitHub as each unit completes. No per-unit permission needed for work inside this queue's scope.

**Scope limits (never cross, even under the standing order):**
- Only the NEXORA project: repo `zobaerio/Nexora`, local tree `~/workspace/gta-style-game/`
- Preserve the Godot testbed; never delete or overwrite existing merged work
- UE5 code written in this VM is **uncompiled scaffolding** — label it so in every file header and PR body; never claim a UE feature works without a build on the owner's PC
- No other repos, no production systems, no purchases, no external messages
- If a GitHub approval card times out or a push/merge fails twice on the same unit: commit the work locally, note it in `STATUS.md`, and move to the next unit — never force-push, never retry in a loop

**Unit workflow:** local files → verify content (read back / JSON-validate / re-run Godot tests if touched) → commit locally → mark unit DONE here + in `STATUS.md`.
**GitHub batching rule (owner, 2026-11-20 23:53 — he has given FULL permission and is frustrated by approval cards, which are per-write by platform design and cannot be disabled):** batch all units completed in one work session/run into ONE branch `feat/<run-slug>` → one push-files → one PR (not draft) → one squash merge → read-back verify one key file per unit on `main` (ref=refs/heads/main). If a card times out, the local commits stand and the next session's batch includes those files (check main first).

## Queue

- [x] **Unit A — Phase 1 Build Sheet** (`docs/PHASE1-BUILD-SHEET.md` + `ue-project/.gitattributes` + `ue-project/README.md`): step-by-step for the owner's PC — Epic Launcher + UE 5.8.x install with MetaHuman data, project creation settings, plugin list, Git LFS setup, folder structure, Phase 1 Megascans/Fab asset list (street/park/riverbank), scene build checklist in order, performance capture sheet (fps/frame-time table + scalability settings), Phase 1 exit-criteria checklist.
- [x] **Unit B — Life Simulation & Player Data Model** (`docs/GDD-01-LIFE-AND-DATA-MODEL.md` + `data/schema.sql`): player profile (from owner's spec example), character identity/personality/goals/memory model, life stages + transitions, household/family/relationship model, PostgreSQL schema draft designed for Phase 9 server authority (currency/property validated server-side), save-game mapping for single-player phases.
- [x] **Unit C — Rupsha City District 1 + NPC/Profession Data** (`docs/GDD-02-RUPSHA-CITY-DISTRICT1.md` + `data/professions.json` + `data/npc-schedules.json` + `data/weather-presets.json` + `data/planets.json`): district layout spec (~1 km², zones, road hierarchy, landmark list, interior list), 11 professions from the owner's spec with income bands + progression, NPC daily schedule templates per profession, weather presets matching the plan, planet data cards from the owner's spec (incl. Nexora-7 fields). All JSON must parse.
- [x] **Unit D — UE Project Scaffolding** (`ue-project/Nexora.uproject`, `ue-project/Config/*.ini`, `ue-project/Source/**`): uproject for UE 5.8 with plugin list, DefaultEngine/DefaultGame/DefaultInput configs (Enhanced Input actions matching the Godot controls table), C++ module skeleton (Nexora.Build.cs, Target files, module, NexoraGameMode, NexoraPlayerController, NexoraCharacter stubs with TODO markers mapped to Phase 3 acceptance tests). Every C++ file header: "UNCOMPILED SCAFFOLD — written to UE 5.8 API conventions in a Linux VM without the engine; first compile happens on the owner's PC (Phase 1/3)."
- [x] **Unit E — UE C++ Core Systems v1: Game Clock + Weather** (`ue-project/Source/Nexora/Systems/NexoraGameClock.*`, `NexoraWeatherManager.*`, `docs/TECH-CLOCK-WEATHER.md`): game-time clock (configurable speed, day phases from the owner's table), weather state machine (Clear/Rain/Storm/Fog/Wind/Cloudy + snow-zone flag), delegates for phase/weather changes, Environment Control Panel data interface — code only, same uncompiled-scaffold labelling, plus the tech note explaining how it binds to Sky Atmosphere/Niagara on the owner's PC.
- [x] **Unit F — Economy & Professions Design** (`docs/GDD-03-ECONOMY-AND-PROFESSIONS.md`): economic classes as starting conditions + mobility systems, wages/prices/rent model v1 with concrete starting numbers in Nexora Credits, business ledger model, and the full Civil Engineer flagship job loop (plan → materials estimate → supervise staged construction → payment → reputation), plus Shop Owner and Taxi Driver loops.
- [x] **Unit G — Mission & Progression Design** (`docs/GDD-04-MISSIONS-AND-PROGRESSION.md`): the owner's Level 1-8 structure (A New Beginning → Space Explorer) turned into concrete missions with objectives, rewards, unlocks; free-roam rules; achievement list v1.
- [x] **Unit H — Phase 2 MetaHuman Build Sheet** (`docs/PHASE2-METAHUMAN-SHEET.md`): MetaHuman Creator step-by-step, owner character spec sheet (from his profile example), Animator face-capture test procedure, outfit/hair rules, LOD + crowd-tier rules (full MetaHuman vs Mass representation), Phase 2 exit checklist.
- [x] **Unit I — QA & Verification Pack** (`docs/QA-PACK.md` + re-run Godot tests): per-phase test checklists consolidated, Godot testbed regression re-run recorded, asset licence register template (`docs/ASSET-LICENCE-REGISTER.md`).
- [x] **Unit J — Roadmap v1.1 revision**: after Units A–I, revise `NEXORA-MIGRATION-PLAN.md` estimates with everything learned, as its own PR, clearly marked v1.1.

When the queue empties: write a completion summary into `STATUS.md`, keep the queue file as the record, and stop (report to the owner chat). Do not invent new units beyond J without the owner.

**Batching note (2026-11-21 run):** Unit J said "as its own PR", but the owner's later card-minimisation order (2026-11-20 23:53) governs — J's v1.1 revision shipped in the same single batch PR as Units B–I. The v1.1 marking in the plan file itself carries the distinction instead.

**Recovery note (run 2026-11-21 03:45):** the 01:45 run's batch push was cut twice by service restarts and the branch was never created, so this run re-pushed the same 35-file batch on `feat/run-20261121-0145` (main confirmed still `675bb183`, no open PRs, no duplication). **Outcome: failed a third time — the write approval card timed out while the owner slept (see STATUS.md "Push block (2026-11-21 03:45 run)").** The merge needs one awake-time approval; later runs re-attempt the same batch.

**Queue 1 result:** Units A–J completed and merged 2026-11-21 (PRs #2, #3; main `7c5071c7`, STATUS finalised `7ed1b6a3`). The recovery note above is history — the batch landed once the owner approved while awake.

---

# Queue 2 — ordered by the owner ("Continue", 2026-11-21 07:08)

Same scope limits, honesty rules and GitHub batching rule as Queue 1. All UE C++ remains UNCOMPILED SCAFFOLD until compiled on the owner's PC.

- [x] **Unit K — Character Movement C++ (Phase 3 prep)** (`ue-project/Source/Nexora/NexoraCharacter.*` expanded + `docs/TECH-MOVEMENT.md`): implement the movement the Unit D stubs promised — Enhanced Input move/look/sprint/jump, CharacterMovement settings matched to the Godot testbed acceptance values (walk 5.0 m/s, run ≈8.8 m/s, jump apex ≈1.6 m), spring-arm camera boom 4.5 m with collision shortening; tech note maps every testbed test to its UE equivalent check.
- [x] **Unit L — Game Data Tables** (`data/prices.json` + `data/buildings-district1.json` + `data/missions.json`): structured data behind the GDDs — wage/price/rent tables consistent with GDD-03 and professions.json; District 1 property stock (from GDD-02) with ids, zone, type, price/rent; missions from GDD-04 Levels 1–8 with objectives/rewards/unlocks. All JSON must parse; cross-references (profession ids, zone ids, mission ids) must resolve.
- [x] **Unit M — Save System Scaffold** (`ue-project/Source/Nexora/Save/NexoraSaveGame.*` + `docs/TECH-SAVE-SYSTEM.md`): USaveGame-based save/load scaffold mapping the GDD-01 single-player state onto schema.sql's save_slots/world_state design; versioning + migration note; uncompiled-scaffold labelling.
- [x] **Unit N — UI & Panels Design** (`docs/GDD-05-UI-AND-PANELS.md`): HUD layout, character profile screen (owner's example card), Environment Control Panel (time/weather controls from the owner's spec), main menu + pause flow, settings; wireframe descriptions + widget class list for UMG implementation later.
- [x] **Unit O — NPC Behaviour Design** (`docs/GDD-06-NPC-BEHAVIOUR.md`): per-profession daily-life state machines tied to npc-schedules.json, crowd tiers (full character vs Mass representation) consistent with the Phase 2 sheet, conversation + memory hooks tied to GDD-01's two-kind memory model, honesty notes on what Mass AI can/cannot do at this scale.

**Queue 2 result:** Units K–O completed and merged 2026-11-21 (PRs #5, #6; main `2154c7f9`, STATUS finalised `616e7bba`).

---

# Queue 3 — ordered by the owner ("Continue", 2026-11-21 07:34)

Same scope limits, honesty rules and GitHub batching rule as Queues 1–2. UE C++ remains UNCOMPILED SCAFFOLD until compiled on the owner's PC.

- [x] **Unit P — Vehicles & Traffic Design** (`docs/GDD-07-VEHICLES-AND-TRAFFIC.md` + `data/vehicles.json`): vehicle classes from GDD-02's road hierarchy (rickshaw, CNG auto-rickshaw, private car, taxi, bus, truck, motorbike) with speed/capacity/fuel/price fields tied to prices.json; drivable-car design (enter/exit, camera, damage-lite rules), traffic flow model per road class, parking + taxi fare loop hookup to GDD-06's taxi work sub-state. vehicles.json must parse; price refs must resolve to prices.json.
- [x] **Unit Q — Construction System Design (flagship)** (`docs/GDD-08-CONSTRUCTION-SYSTEM.md`): the Civil Engineer flagship loop in buildable detail — staged construction states (foundation → frame → walls → roof → finishing), materials consumption drawn from prices.json items, crew roles + schedule hookup to GDD-06, site safety/quality checks, payment milestones tied to the economy ledger (GDD-03), and how a finished site becomes a buildings-district1.json property. Every material/price reference must resolve to merged data.
- [x] **Unit R — District 1 Blockout Spec + Data** (`docs/TECH-DISTRICT1-BLOCKOUT.md` + `data/district1-blockout.json`): street-by-street blockout the owner can build from on PC — road segments (id, class, endpoints, width), plot grid per zone with building ids matching buildings-district1.json, landmark placements from GDD-02, river + bridge geometry notes, Phase 1 400 m test-scene subset marked explicitly. JSON must parse; building ids must resolve 1:1 with buildings-district1.json.
- [x] **Unit S — Multiplayer Architecture Design** (`docs/TECH-MULTIPLAYER.md`): Phase 9 prep, design only — listen-server vs dedicated-server decision with reasoning, what replicates (player characters, Full-tier NPCs) vs what never replicates (Ambient crowd = local simulation), server authority mapping onto schema.sql (ledger, properties, tenancies), session/friend model from account_friendships, honest scale limits (UE replication is not MMO) and the test plan for the owner's PC/LAN.
- [x] **Unit T — Economy Balance Simulator** (`tools/economy_sim.py` + `docs/ECONOMY-SIM-REPORT.md`): a runnable Python simulation over the merged data (professions.json wages, prices.json, buildings rents) — 30 game-days per profession: income, rent, food, transport, savings trajectory; flags any profession that cannot survive on its wage band or that accumulates implausibly fast; the report records the actual run output and any balance problems found (problems are reported, not silently fixed — data changes need their own follow-up unit).

**Queue 3 result:** Units P–T completed and merged 2026-11-21 (PRs #7, #8; main `bc195468`, STATUS finalised `0a957f37`).

---

# Queue 4 — ordered by the owner ("Next", 2026-11-21 07:48)

Fix the four economy findings from Unit T's simulator report (`docs/ECONOMY-SIM-REPORT.md`). Data changes in U–W are authorised by this queue; each must be justified by its finding and proven by the Unit X re-run. Same scope limits, honesty rules and GitHub batching rule as Queues 1–3.

- [x] **Unit U — Taxi Rental Fix (Finding 1)** (`data/prices.json` + GDD-03 §3.3/§8 + GDD-07 §2 + `data/vehicles.json` note): entry taxi renting loses ~13,700/mo (rent 800/day vs 14,000 gross) — the designed rent-before-you-buy on-ramp is broken. Lower the daily cab rental so renting ends modestly positive, clearly worse than owning but survivable; update every document that states the old number.
- [x] **Unit V — Senior Cost Scaling (Finding 2)** (`data/prices.json` + GDD-03): senior tiers save 71–84% because living costs are flat while wages scale. Introduce tier-scaled living costs (eating-out/services lines + a lifestyle-uplift mechanism owned by the data) so senior savings land roughly in the 35–55% band; document the reasoning.
- [x] **Unit W — Per-Profession Starting Balances (Finding 3)** (`data/professions.json` + GDD-03): monthly-paid professions dip negative in month 1 from a zero start (pilot −34,800). Add `starting_balance_ncr` per profession (civil engineer keeps the canonical 25,000), sized from the simulator's month-1 dip so no profession goes negative on its normal path.
- [x] **Unit X — Simulator v2 + Full Re-run** (`tools/economy_sim.py` + `docs/ECONOMY-SIM-REPORT-V2.md`): model business-owner/shop-owner rows with real operating costs (full P&L + 8% business tax — v1 treated their bands as pre-cost upper bounds, Finding 6), apply U–W, re-run everything deterministically, and publish the v2 report with verbatim output + a before/after verdict per finding (fixed / improved / still open, honestly).

---

# Queue 5 — "Life Systems", ordered by the owner ("Continue Your Work", 2026-11-21 08:01)

Design/data/scaffold layer, same scope limits, honesty rules and GitHub batching rule as Queues 1–4. UE C++ remains UNCOMPILED SCAFFOLD until compiled on the owner's PC.

- [x] **Unit Y — Character Creator & Clothing** (`docs/GDD-09-CHARACTER-CREATOR.md` + `data/clothing.json` + clothing price table in `data/prices.json`): creator flow on MetaHuman (what the player picks vs what MetaHuman generates), outfit slots, clothing catalogue with prices resolving to prices.json clothing entries (a clothing price table is added to prices.json — none existed, only monthly budget lines), profession uniform mapping for all 11 professions.
- [x] **Unit Z — Housing & Home Life** (`docs/GDD-10-HOUSING-AND-HOME-LIFE.md`): living in the properties from buildings-district1.json — move-in/move-out, rent payment hookup to the ledger (GDD-03 §3.2 owns the missed-rent ladder), home needs loop (sleep/eat/social/security from GDD-01 §4), furniture tiers tied to prices, visitors/household hookup to GDD-01 §5 households.
- [x] **Unit AA — Drivable Vehicle C++ Scaffold** (`ue-project/Source/Nexora/Vehicles/NexoraVehiclePawn.h/.cpp` + `docs/TECH-VEHICLES.md`): Chaos-vehicle-oriented pawn scaffold + enter/exit interaction contract with NexoraCharacter, camera states, and the taxi fare meter hookup points from GDD-07; UNCOMPILED SCAFFOLD headers; braces balanced.
- [x] **Unit AB — Education & School Life** (`docs/GDD-11-EDUCATION.md`): child/student life-stage loops (school day from npc-schedules templates), teacher profession hookup (GDD-06), skills progression into character_skills (schema), university in District 1's education zone.
- [x] **Unit AC — Health & Hospital** (`docs/GDD-12-HEALTH.md`): doctor profession loop, illness/injury model (causes from weather/traffic/construction systems already designed), hospital interiors from GDD-02, treatment costs resolving to prices.json.

**Queue 5 result:** Units Y–AC completed and merged 2026-11-21 (PR #10 for Y+Z+AA; AB+AC in the finisher batch — see STATUS.md).

## Status

See `STATUS.md` (updated every unit).
