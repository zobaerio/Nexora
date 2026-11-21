# NEXORA — QA & Verification Pack

**Unit I · Version 1.0 · 2026-11-20**
**Parent documents:** `NEXORA-MIGRATION-PLAN.md` Part D (phase exit criteria) · `docs/PHASE1-BUILD-SHEET.md` (perf capture sheet) · `docs/GDD-01-LIFE-AND-DATA-MODEL.md` (life-sim exit tests) · `docs/GDD-03-ECONOMY-AND-PROFESSIONS.md` §9 (economy health queries) · `docs/TECH-CLOCK-WEATHER.md` §7 (Phase 4 tests)
**Companion file:** `docs/ASSET-LICENCE-REGISTER.md` — every asset's licence, in one place.

> **QA law:** a phase is done when its exit criteria are *demonstrated*, not when its files exist. A build the owner has not run is a claim, not a result. Every checklist below names who runs it, where it runs, and what counts as a pass — "looks fine" is never a pass.

---

## 1. Godot Testbed Regression (runs in this VM)

The Godot prototype (`rupsha-city/`) is the preserved systems testbed — it stays working for the whole project, because it is the only part of NEXORA that can be tested headlessly in this VM.

**Command:**
```
~/workspace/tools/godot --headless --path ~/workspace/gta-style-game/rupsha-city res://tests/player_test.tscn
```
**Pass:** the output ends with `PLAYER_TEST_PASS` (8/8 checks: land, rest, walk, camera-forward, run > walk, jump rise, land after jump, spring-arm shortens at wall).

**Run log:**

| Date (Dhaka) | Godot | Result | Notes |
|---|---|---|---|
| 2026-11-20 (foundation) | 4.7.2 | PLAYER_TEST_PASS (8/8) | First verified run; Windows exe built (105 MB, not in git). |
| 2026-11-21 01:45 | 4.7.2 | PLAYER_TEST_PASS (8/8) | Unit I re-run. walk=5.00, run=8.77, jump max_y=1.59, cam_dist=3.04. No testbed files changed since foundation. |

**Rule:** any run that touches `rupsha-city/` re-runs this test before committing. A failing test blocks the batch — the testbed is the reference the UE controller (Unit D) must match.

## 2. Per-Phase Test Checklists

Each phase's exit criteria come from the master plan Part D. The checklists below are the *same criteria, made runnable* — every item is a concrete observation, not a vibe.

### Phase 1 — Photorealistic Environment Test
**Where:** owner's PC, UE 5.8. **Who:** owner.

- [ ] Project opens from `ue-project/Nexora.uproject` (Unit D) with no missing-plugin errors.
- [ ] 400 m × 400 m scene builds: street corner, park, riverbank (build sheet Step 7, in order).
- [ ] Screenshot comparison: the scene reads as a real place at 09:00 clear day (the owner judges this — photorealism is his call, not a metric).
- [ ] Perf capture sheet filled (build sheet): fps + frame time at Low/Medium/High/Epic on his GPU; no setting below 30 fps at Medium is accepted silently — it is written down with the GPU model.
- [ ] No fake content: every asset in the scene is a real Megascans/Fab asset with a licence row in the register (§5).

### Phase 2 — Realistic Human Character
**Where:** owner's PC. **Who:** owner.

- [ ] Full checklist in `docs/PHASE2-METAHUMAN-SHEET.md` §7 (owner character approved, Animator test recorded, 3 outfits, LOD set, perf re-run).
- [ ] The owner recognises his own character's face. (Yes/no, his answer.)

### Phase 3 — Movement, Collision, Camera, Interaction
**Where:** owner's PC. **Who:** owner (+ this VM's Godot test as the reference).

- [ ] Walk 300 u/s, run 600 u/s, jump feels like the Godot testbed (Unit D values).
- [ ] Camera boom shortens at walls — never clips (same behaviour the Godot test proves: `cam_dist` shortens).
- [ ] Interaction works: doors open, sit works, enter-vehicle placeholder responds.
- [ ] Input matches the Godot table exactly: WASD move, Shift run, Space jump, F interact (Unit D, `Config/DefaultInput.ini`).
- [ ] HUD clock readout matches `GameClock` time exactly (Unit E test).

### Phase 4 — Dynamic Day-Night & Weather
**Where:** owner's PC. **Who:** owner.

- [ ] All five tests in `docs/TECH-CLOCK-WEATHER.md` §7 pass (24-hour clock run, 09:00 reference, rain transition, save/reload weather, single phase-change fire).

### Phase 5 — A Small Living City (District 1)
**Where:** owner's PC. **Who:** owner.

- [ ] The player can live one full in-game day in District 1: wake, commute, work a shift, eat, leisure, sleep — without a blocking bug.
- [ ] All zones from GDD-02 §2 are reachable; every listed landmark exists and is identifiable.
- [ ] One flagship-loop job completes end to end (GDD-03 §6).
- [ ] No building the player can enter is an empty shell without a reason (a locked door says why).

### Phase 6 — NPC Society, Professions, Relationships, Economy v1
**Where:** owner's PC (accelerated simulation). **Who:** owner.

- [ ] 30 in-game days of accelerated simulation run with no crash and no NPC schedule deadlocks.
- [ ] Economy health queries pass (GDD-03 §9): price index 95–105, employment ≥ 85%, closures ≤ 10%, arrears ≤ 5%, money conserved within ±2%.
- [ ] Full-tier NPCs remember the player's job and past interactions at a basic level (a named NPC references a shared event).
- [ ] Save/load preserves the whole society state (not just the player).

### Phase 7 — Life Stages, Families, Aging, Inheritance
**Where:** owner's PC (accelerated simulation). **Who:** owner.

- [ ] A simulated family runs 3 generations with correct inheritance and no orphaned data.
- [ ] Stage transitions never visibly "pop" — they happen at a sleep/night boundary with a presented time-skip (GDD-01 §3).
- [ ] The child/elder asset gate is closed or honestly recorded as open (GDD-01 §3).

### Phase 8 — Multiple Districts & Cities
**Where:** owner's PC. **Who:** owner.

- [ ] Inter-city travel works (drive/ride the route, no fast-travel-only).
- [ ] Level 7 missions complete (GDD-04 §2).
- [ ] A second city's economy runs on the same ledger rules (GDD-03 §9 queries pass there too).

### Phase 9 — Persistent Online Multiplayer
**Where:** staging server (never production load-tested — the standing rule). **Who:** owner + testers.

- [ ] Server is the only writer of ledger + property (GDD-01 §8): a modified client can display a fake balance but can never spend it.
- [ ] Two players in the same district see the same clock, weather, and NPC state.
- [ ] Save slots become the character-select list (GDD-01 §9).

### Phase 10 — Other Regions & Planets
**Where:** owner's PC. **Who:** owner.

- [ ] Level 8 missions complete (GDD-04 §2); Nexora-7 landing works.
- [ ] Snow zones work where `bSnowZone` is true — and District 1 still never snows (TECH-CLOCK-WEATHER §6).

## 3. Regression Rules (every phase, every PR)

1. **The Godot testbed still passes** (§1) — any run that touches it re-runs the test.
2. **No merged work breaks.** A new unit never edits a merged file except to fix a verified bug, and then the fix is its own note in the PR.
3. **JSON still parses.** `data/*.json` are validated with `python3 -m json.tool` before every push. A broken JSON file is a broken game — the data files are load-bearing.
4. **SQL still parses.** `data/schema.sql` is validated (pglast) whenever it changes; a schema change ships with a migration note (GDD-01).
5. **Docs stay consistent.** When a number changes in one document, the documents that quote it change in the same PR (wages: JSON + GDD-03; weather: JSON + TECH note + manager defaults).
6. **Uncompiled stays labelled.** Every UE file header and PR body says the code is uncompiled scaffolding until a build on the owner's PC proves it. A claim that a UE feature "works" without that build is a QA failure in itself.

## 4. Bug & Finding Log

A finding is recorded with: date, phase, what was observed, what was expected, and the fix or the decision to live with it. "Fixed" means re-tested, not re-written.

| Date | Phase | Finding | Status |
|---|---|---|---|
| 2026-11-20 | Foundation | Godot prototype looked cartoon-like (audit: primitives only, 0 textures, flat albedo, solid-colour sky) | Recorded in migration plan Part A; UE 5.8 is the answer, not a Godot fix. |
| 2026-11-20 | — | AI video generation region-blocked (HTTP 403) | Do not retry (separate workstream note). |
| 2026-11-21 | B+C | GitHub `create_branch` approval card timed out; B+C content safe in local commit `6e736d2` | Recovered: batched into this run's single PR (see STATUS.md). |

## 5. Asset Licence Register

`docs/ASSET-LICENCE-REGISTER.md` is the single register. **Rule: no asset enters the project without a row in the register** — source, licence, and what it is used for. CC0 is the default for anything new; a paid or restricted licence is recorded with its terms, not assumed. The register is checked at every phase gate (§2, Phase 1 item 5).

*End of QA-PACK v1.0. Changes happen by PR; new test runs are appended to §1, never rewritten.*
