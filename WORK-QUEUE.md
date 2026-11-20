# NEXORA — Continuous Development Work Queue

**Owner order (2026-11-20 23:48 Dhaka):** Keep developing continuously, night and day, until the owner says stop. Merge to GitHub as each unit completes. No per-unit permission needed for work inside this queue's scope.

**Scope limits (never cross, even under the standing order):**
- Only the NEXORA project: repo `zobaerio/Nexora`, local tree `~/workspace/gta-style-game/`
- Preserve the Godot testbed; never delete or overwrite existing merged work
- UE5 code written in this VM is **uncompiled scaffolding** — label it so in every file header and PR body; never claim a UE feature works without a build on the owner's PC
- No other repos, no production systems, no purchases, no external messages
- If a GitHub approval card times out or a push/merge fails twice on the same unit: commit the work locally, note it in `STATUS.md`, and move to the next unit — never force-push, never retry in a loop

**Unit workflow (every unit):** local files → verify content (read back / JSON-validate / re-run Godot tests if touched) → branch `feat/<unit-slug>` → push-files → PR (not draft) → squash merge → read-back verify one key file on `main` (ref=refs/heads/main) → mark unit DONE here + in `STATUS.md`.

## Queue

- [ ] **Unit A — Phase 1 Build Sheet** (`docs/PHASE1-BUILD-SHEET.md` + `ue-project/.gitattributes` + `ue-project/README.md`): step-by-step for the owner's PC — Epic Launcher + UE 5.8.x install with MetaHuman data, project creation settings, plugin list, Git LFS setup, folder structure, Phase 1 Megascans/Fab asset list (street/park/riverbank), scene build checklist in order, performance capture sheet (fps/frame-time table + scalability settings), Phase 1 exit-criteria checklist.
- [ ] **Unit B — Life Simulation & Player Data Model** (`docs/GDD-01-LIFE-AND-DATA-MODEL.md` + `data/schema.sql`): player profile (from owner's spec example), character identity/personality/goals/memory model, life stages + transitions, household/family/relationship model, PostgreSQL schema draft designed for Phase 9 server authority (currency/property validated server-side), save-game mapping for single-player phases.
- [ ] **Unit C — Rupsha City District 1 + NPC/Profession Data** (`docs/GDD-02-RUPSHA-CITY-DISTRICT1.md` + `data/professions.json` + `data/npc-schedules.json` + `data/weather-presets.json` + `data/planets.json`): district layout spec (~1 km², zones, road hierarchy, landmark list, interior list), 11 professions from the owner's spec with income bands + progression, NPC daily schedule templates per profession, weather presets matching the plan, planet data cards from the owner's spec (incl. Nexora-7 fields). All JSON must parse.
- [ ] **Unit D — UE Project Scaffolding** (`ue-project/Nexora.uproject`, `ue-project/Config/*.ini`, `ue-project/Source/**`): uproject for UE 5.8 with plugin list, DefaultEngine/DefaultGame/DefaultInput configs (Enhanced Input actions matching the Godot controls table), C++ module skeleton (Nexora.Build.cs, Target files, module, NexoraGameMode, NexoraPlayerController, NexoraCharacter stubs with TODO markers mapped to Phase 3 acceptance tests). Every C++ file header: "UNCOMPILED SCAFFOLD — written to UE 5.8 API conventions in a Linux VM without the engine; first compile happens on the owner's PC (Phase 1/3)."
- [ ] **Unit E — UE C++ Core Systems v1: Game Clock + Weather** (`ue-project/Source/Nexora/Systems/NexoraGameClock.*`, `NexoraWeatherManager.*`, `docs/TECH-CLOCK-WEATHER.md`): game-time clock (configurable speed, day phases from the owner's table), weather state machine (Clear/Rain/Storm/Fog/Wind/Cloudy + snow-zone flag), delegates for phase/weather changes, Environment Control Panel data interface — code only, same uncompiled-scaffold labelling, plus the tech note explaining how it binds to Sky Atmosphere/Niagara on the owner's PC.
- [ ] **Unit F — Economy & Professions Design** (`docs/GDD-03-ECONOMY-AND-PROFESSIONS.md`): economic classes as starting conditions + mobility systems, wages/prices/rent model v1 with concrete starting numbers in Nexora Credits, business ledger model, and the full Civil Engineer flagship job loop (plan → materials estimate → supervise staged construction → payment → reputation), plus Shop Owner and Taxi Driver loops.
- [ ] **Unit G — Mission & Progression Design** (`docs/GDD-04-MISSIONS-AND-PROGRESSION.md`): the owner's Level 1-8 structure (A New Beginning → Space Explorer) turned into concrete missions with objectives, rewards, unlocks; free-roam rules; achievement list v1.
- [ ] **Unit H — Phase 2 MetaHuman Build Sheet** (`docs/PHASE2-METAHUMAN-SHEET.md`): MetaHuman Creator step-by-step, owner character spec sheet (from his profile example), Animator face-capture test procedure, outfit/hair rules, LOD + crowd-tier rules (full MetaHuman vs Mass representation), Phase 2 exit checklist.
- [ ] **Unit I — QA & Verification Pack** (`docs/QA-PACK.md` + re-run Godot tests): per-phase test checklists consolidated, Godot testbed regression re-run recorded, asset licence register template (`docs/ASSET-LICENCE-REGISTER.md`).
- [ ] **Unit J — Roadmap v1.1 revision**: after Units A–I, revise `NEXORA-MIGRATION-PLAN.md` estimates with everything learned, as its own PR, clearly marked v1.1.

When the queue empties: write a completion summary into `STATUS.md`, keep the queue file as the record, and stop (report to the owner chat). Do not invent new units beyond J without the owner.

## Status

See `STATUS.md` (updated every unit).
