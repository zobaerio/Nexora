# NEXORA — TECH: Drivable Vehicles (Chaos binding, enter/exit contract, fare meter)

**Unit AA · Version 1.0 · 2026-11-21**
**Code:** `ue-project/Source/Nexora/Vehicles/NexoraVehiclePawn.h` / `.cpp` — **UNCOMPILED SCAFFOLD** (the standard header is in both files: written in a Linux VM without the engine; first compile on the owner's PC, Phase 5 for this file).
**Parent documents:** `docs/GDD-07-VEHICLES-AND-TRAFFIC.md` §4 (the drivable vehicle), §5 (the fare loop), §6 (parking — a parked player vehicle is saved where left) · `data/prices.json` `taxi_fares` + `vehicles` (owns every fare and price number) · `docs/TECH-MOVEMENT.md` (the camera family this pawn inherits) · `docs/GDD-05-UI-AND-PANELS.md` (the interact prompt: `[F] — Enter vehicle`, never a bare F) · `docs/GDD-01-LIFE-AND-DATA-MODEL.md` §8 (integer money, ledger truth) · `docs/TECH-MULTIPLAYER.md` (Phase 9 replication stance for vehicles)

> **Honesty line:** after this unit, NEXORA has a vehicle pawn that *accounts* like a taxi and *frames* like a chase camera — and does not roll one centimetre. Wheel physics is Chaos Vehicles, deliberately not bound yet (§1). Anyone who describes this scaffold as "driving works" is wrong, and this note exists so they can be corrected from the record.

---

## 1. The Chaos Seam — the Only Binding Point

Everything NEXORA-specific is finished code in the pawn: input surface, camera states, fare meter, damage-lite condition, enter/exit occupancy. The generic wheel physics is one marked seam, `BindChaosMovement()`, kept empty on purpose:

- `Nexora.Build.cs` already lists `"ChaosVehicles"` in its phase-gated comment ("Added at their phases — do NOT enable early"). Binding it in Queue 5 would make every Phase 1–4 build carry a Phase 5 module for zero testable gain — nothing can be driven in this VM either way.
- **Phase 5 enable steps (owner's PC, in order):** ① enable the **ChaosVehicles plugin** in `Nexora.uproject`; ② uncomment `"ChaosVehicles"` in `Nexora.Build.cs`; ③ in `NexoraVehiclePawn.cpp`, include `ChaosWheeledVehicleMovementComponent.h` and create the component inside `BindChaosMovement()`; ④ uncomment the four input forwards in `ApplyInputsToMovement()` (the real Chaos API names are written there, including the damage rule: throttle is scaled by `GetTopSpeedScale()`, steering and brakes never are); ⑤ author the vehicle Blueprint: skeletal mesh with a **`Seat_Driver`** socket, wheel classes and wheel placement as content.
- Until step ③ the pawn logs one warning at BeginPlay ("will not move") so a scaffold build can never be mistaken for a driving build.

## 2. The Enter/Exit Contract (with `ANexoraCharacter`)

The sequence, and who owns each step:

1. **Prompt** — the interact system (GDD-05) shows `[F] — Enter vehicle` when the player character is in range of the driver door. Rupsha City drives on the left; the driver door is the **right** door, and `GetDoorExitTransform()` puts the exiting character 1.5 m out on that side.
2. **Interact** — the PlayerController calls `TryEnter(Character)` on the pawn. The pawn refuses (returns false) when occupied or passed no character — a second character can never steal a driven vehicle through this path.
3. **Occupancy** — on success the pawn stores the driver, hides the character body and parents it to the `Seat_Driver` socket (the body travels with the vehicle for saves and streaming; it is not deleted, not teleported away). The pawn broadcasts `OnDriverChanged`.
4. **Possession** — the **controller's** step (not the pawn's): the PlayerController possesses the vehicle pawn and routes the driving action set (GDD-07 §4) to the pawn's input surface. Input stays in the controller, exactly as on foot (the Unit K rule).
5. **Society hook** — the NPC/society systems bind `OnDriverChanged` to record the character's state as `driving` (GDD-07 §4), so schedules, needs and the save system know where the character is. A parked player vehicle is saved where left (GDD-07 §6; Unit M runtime state).
6. **Exit** — the exit action calls `ExitVehicle()`: the character is detached, placed at the door transform, unhidden; the controller re-possesses the character. Exiting mid-trip **cancels the fare without charge** — payment exists only at dropoff (§3).

NPC drivers use steps 2–3 and 6 identically (their controller is an AI controller); there is no second, NPC-only vehicle system.

## 3. The Fare Meter (GDD-07 §5 in code)

- **One machine, two seats:** the meter in the pawn serves the player's taxi loop (GDD-03 §8) and the NPC loop (GDD-06 §4.6) unchanged. State machine: `Idle → Hired → Completed → (economy ack) → Idle`.
- **Numbers are mirrors, not sources:** `BaseFareNcr 60`, `PerKmNcr 25`, `SurgeMultiplier 1.5` are config defaults copied from `prices.json` `taxi_fares`. prices.json owns them; a tuning change edits prices.json and these defaults, in that order.
- **Distance** accumulates in `Tick` from the pawn's velocity while `Hired` — traffic, detours and waiting-in-motion are therefore priced by the same road the player drove, not by a straight line.
- **Surge** is an input, not a decision: `SetSurgeConditions(rain, night)` is fed by the weather/clock consumers (TECH-CLOCK-WEATHER); the meter applies ×1.5 when either is true, matching `surge_conditions: [rain, night]`.
- **Money leaves as an integer:** the fare is computed in float and rounded once at `CompleteTrip()`. The pawn then broadcasts `OnFareCompleted(FareNcr, TripKm)` and **writes nothing** — the profession/economy system writes the ledger row (passenger → driver/depot split per GDD-03 §8) and calls `AcknowledgeFarePaid()`. A modified client can fake its meter display; it cannot mint the ledger row (GDD-01 §8).
- Rickshaw/CNG hire (GDD-07 §5) reuses this meter class of logic at their own price family when those classes become drivable; no second meter is written.

## 4. Camera States

| State | Rig | Rule |
|---|---|---|
| `Chase` (default) | Boom 700 cm, socket height 250 cm | The on-foot boom family (450 cm, TECH-MOVEMENT) raised and pulled back per GDD-07 §4; the spring arm's probe shortens it at walls — the same behaviour the Godot testbed verified |
| `Hood` | Boom length 0, offset 180 cm forward / 110 cm up | The driver sees road, not car |
| `FreeLook` | Chase rig + `Look()` offsets | Yaw ±70°, pitch ±20° clamps; mirrors the on-foot look contract (controller sends the vector, pawn applies it) |

No cinematic cameras in v1 (GDD-07 §4). Camera *feel* (lag values, FOV at speed) is tuned on the owner's PC; this scaffold fixes the states and the starting numbers, and claims nothing about feel.

## 5. Damage-Lite, As Coded

GDD-07 §4 allows condition exactly three effects; the code has exactly three readers: cosmetic state (the mesh reads `GetCondition()`), `GetTopSpeedScale()` (0.75 below 40 condition, applied to throttle only), and `GetRepairCostNcr()` (charged at the `d1_oldtown` repair workshops as a ledger `purchase`).

Two flags, honestly:
- **The damage curve is a rule, not physics:** no damage below 3 m/s impact, linear above. It exists so collisions cost something predictable; Chaos will report real impact data at Phase 5 and the curve is the tuning surface.
- **`RepairCostPerConditionPointNcr` (45) is a placeholder.** `prices.json` has no repair rate. The number keeps the rule testable end-to-end; the economy pass owns the real one, and when it lands it lands in prices.json first (the §3 mirror rule), not in this constant.

## 6. What This Scaffold Deliberately Does Not Do

- **No wheel, suspension or surface tuning** — Chaos content work on the owner's PC (GDD-07 §4's failure honesty applies verbatim: handling feel cannot be claimed from here).
- **No replication.** The pawn is written for local authority. Phase 9 makes vehicles server-replicated per TECH-MULTIPLAYER (players + Full-tier only; Ambient traffic never replicates) — the fare meter's broadcast design is the seam that survives that change, because the *server's* meter will be the one whose broadcast the ledger trusts.
- **No horn sound, no engine audio** — Phase 8. `SoundHorn()` is an empty, commented stub; a placeholder beep would be a shipped sound, and shipped sounds are not scaffolded by accident.
- **No passenger carrying beyond the fare contract** — passengers as *characters* riding (the player's own NPC taxi rides, GDD-07 §5) board through the same occupancy idea on the passenger seat; that extension is Phase 5 work, noted here so the driver-only occupancy of this scaffold is a known step, not a discovered gap.

## 7. Acceptance Checks (for Phase 5 implementation, owner's PC)

- [ ] After the §1 enable steps, the module compiles with the Chaos forwards uncommented and the BeginPlay warning gone.
- [ ] Enter at the right-hand door → character hidden, seated, `OnDriverChanged` fired, schedule state reads `driving`; exit restores the character at the door transform.
- [ ] A driven 1.0 km trip in clear daytime completes at exactly 85 NCr (60 + 25); the same trip under rain completes at 128 NCr (85 × 1.5 = 127.5 → rounded once); the ledger row equals the broadcast fare.
- [ ] Exiting mid-trip charges nothing and returns the meter to `Idle`.
- [ ] A ≥10 m/s collision drops condition; below 40 the top cruise speed is measurably ~25% down; the workshop repair charge equals `GetRepairCostNcr()` and restores condition to 100.
- [ ] The chase boom shortens against a wall instead of clipping (the TECH-MOVEMENT camera test, re-run on the vehicle).
