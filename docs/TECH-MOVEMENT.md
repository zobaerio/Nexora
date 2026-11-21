# NEXORA — Tech Note: Character Movement

**Unit K · Version 1.0 · 2026-11-21**
**Code:** `ue-project/Source/Nexora/NexoraCharacter.{h,cpp}` (input bindings: `NexoraPlayerController.{h,cpp}` + `ue-project/Config/DefaultInput.ini`)
**Reference implementation:** the Godot testbed — `rupsha-city/scripts/player.gd`, verified by `rupsha-city/tests/player_test.gd` (8/8 headless, observed values in §2)
**Parent documents:** `NEXORA-MIGRATION-PLAN.md` Phase 3 · `docs/QA-PACK.md` (consolidated phase checklists)
**Status:** UNCOMPILED SCAFFOLD — written in a Linux VM without the engine. First compile and every check in §3 happen on the owner's PC in Phase 3. Nothing in this note is a claim that the movement works — it is the checklist that will prove it, with the numbers it must hit.

---

## 1. The Contract

The UE character must *feel like the verified prototype*, not like a fresh UE template. The testbed is the acceptance spec: its exported values and its measured test results are the targets below. If a Phase 3 build disagrees with this table, the build is wrong (or this note is amended by PR with the test evidence attached — never silently re-tuned).

Input stays where Unit D put it: `ANexoraPlayerController` binds the Enhanced Input actions (`IA_Move`, `IA_Look`, `IA_Run`, `IA_Jump`, …) and forwards to the character's `Move` / `Look` / `SetRunning` / `Jump`. The character owns the movement *values*; the controller owns the *bindings*; the IMC assets own the *keys* (contract in `DefaultInput.ini`).

## 2. Values — Godot testbed → UE (cm = m × 100)

| Quantity | Testbed (player.gd) | Observed in test | UE setting (NexoraCharacter) | Value |
|---|---|---|---|---|
| Walk speed | `walk_speed = 5.0` m/s | 5.00 m in 1.0 s | `MaxWalkSpeed` (walk state) | 500 cm/s |
| Run speed | `run_speed = 9.0` m/s | 8.77 m in 1.0 s (30 m/s² ramp eats the rest) | `MaxWalkSpeed` (run state) | 880 cm/s |
| Ground acceleration | `acceleration = 30.0` m/s² | — (shapes both rows above) | `MaxAcceleration` | 3000 cm/s² |
| Jump velocity | `jump_velocity = 5.5` m/s | apex max_y 1.59 m | `JumpZVelocity` | 560 cm/s |
| Gravity | 9.8 m/s² (project default) | — | World gravity −980 cm/s², `GravityScale` | 1.0 |
| Camera boom | SpringArm3D, full length 4.5 m | shortens to 3.04 m at the test wall | `TargetArmLength`, `bDoCollisionTest = true` | 450 cm |
| Camera pivot height | rig at ≈1.6 m (test measures from +1.6 m) | — | boom relative Z +72 over capsule centre (≈88 cm) | ≈160 cm |
| Camera FOV | Camera3D default 75° | — | `FollowCamera.FieldOfView` | 75° |
| Body facing | mesh pivot lerps toward travel direction | — | `bOrientRotationToMovement`, `RotationRate` yaw | 540°/s |
| Pitch clamp | −65° … +30° (player.gd) | — | **not in this unit** — §3, check 6 | — |

**Run-speed note.** The testbed's *setting* is 9.0 m/s but its *measured* 1-second distance is 8.77 m because the acceleration ramp spends the first fraction of the second below top speed. UE's 880 with the same 3000 cm/s² ramp reproduces the measured behaviour — matching the observation, not the raw setting, is what "same feel" means. If the Phase 3 check (below) lands outside its band, adjust `RunSpeed` in 10 cm/s steps and record the change here.

**Jump derivation.** Apex = v²/(2g). Testbed: 5.5²/(2·9.8) = 1.54 m theoretical, 1.59 m observed (discrete physics steps overshoot slightly). UE at g = 980 cm/s²: v = 560 gives 560²/1960 = **160 cm = 1.6 m** — the acceptance target the owner set. One constant, one formula, no guessing.

## 3. Test Mapping — every testbed check has a UE check

Run in PIE on the Phase 1 test scene (flat ground strip + one wall), character = `ANexoraCharacter`, after the IMC/IA assets exist. Measure distance with the editor's orthographic ruler or a debug line from the start marker; measure apex by placing a 1.6 m reference box beside the jump point.

| # | Godot test (player_test.gd) | UE check | Pass band |
|---|---|---|---|
| 1 | Player lands and stays on the floor; rests near ground level | Spawn the character 10 cm above flat ground in PIE; it falls, lands, and stays put (no bounce, no sinking) | Rests with capsule base on the ground plane; no drift over 5 s |
| 2 | Walk forward 1 s → sane distance, camera-forward | Hold W for exactly 1.0 s from a start marker | **5.00 m ± 0.30** travelled, direction = camera forward |
| 3 | Run 1 s → > 1.3× the walk distance | Hold Shift+W for exactly 1.0 s from the same marker | **≥ 8.4 m**, and ≥ 1.5× the walk result from check 2 |
| 4 | Jump rises (max_y > 0.5), then lands | Jump beside the 1.6 m reference box; observe apex against the box top; character lands and can move again | Apex **1.6 m ± 0.15**; clean landing, no double-jump |
| 5 | Spring arm shortens near a wall (cam_dist < 4.4 at a wall 3.2 m behind) | Back the character to 3.2 m in front of the test wall, camera facing away from the wall | Boom visibly shortens; camera-to-pivot distance **< 4.4 m** (testbed observed 3.04 m); no wall clipping at any pitch |
| 6 | *(testbed behaviour, not an automated check)* pitch clamps at −65°/+30° | Before this check: set `ViewPitchMin = −65`, `ViewPitchMax = 30` on the PlayerCameraManager class defaults used by `ANexoraPlayerController` (one-line editor step, deliberately not hidden in character code). Then mouse-look fully up and down | Pitch stops at both limits; no flip-over |

Checks 1–5 are the Phase 3 acceptance tests the Unit D stubs pointed at. Record results in `docs/QA-PACK.md`'s Phase 3 section when they are run — with the build's engine version and the measured numbers, not just "passed".

## 4. Known Feel Differences (declared, not discovered later)

- **Air control:** the testbed steers at full acceleration in the air; UE here uses `AirControl = 0.35` (template-style). Check 4's landing accuracy is where this shows. If Phase 3 playtesting wants the testbed's tighter air feel, raise `AirControl` toward 1.0 by PR — it is a feel decision for the owner at the keyboard, not a bug.
- **Camera lag:** the boom enables camera lag (speed 12) for a smoother follow; the testbed has none. Lag does not affect check 5's distance (it affects how fast the boom *settles*). If it feels floaty in Phase 3, disable it — one boolean.
- **Stopping:** Godot decelerates through the same 30 m/s² ramp; UE stopping is governed by `GroundFriction`/`BrakingDecelerationWalking`, left at engine defaults in this unit. Check 2's ±0.30 band has room for it; tune only with measurements.

## 5. What This Unit Deliberately Does Not Do

- No animation blueprint, no foot IK, no crouch/swim/climb — the body is still the Phase 2 placeholder capsule; animation arrives with the MetaHuman body.
- No networking replication tuning — movement is client-local until Phase 9, where server authority (GDD-01 §8) gets its own unit.
- No gamepad dead-zone or mouse-sensitivity curve — those live in the IMC modifiers created in Phase 3; `LookSensitivity = 1.0` is a pass-through until then.

*End of TECH-MOVEMENT v1.0. Changes happen by PR with Phase 3 measurements attached.*
