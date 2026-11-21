// NEXORA — NexoraVehiclePawn.h
// UNCOMPILED SCAFFOLD — written to UE 5.8 API conventions in a Linux VM without the engine;
// first compile happens on the owner's PC (Phase 5 for this file; the module's first
// compile is Phase 1/3).
//
// Unit AA (Phase 5 prep): the drivable vehicle of docs/GDD-07-VEHICLES-AND-TRAFFIC.md §4/§5.
// This pawn owns everything that is NEXORA's own logic — the input surface the
// PlayerController calls (same pattern as ANexoraCharacter::Move/Look), the chase
// camera family (TECH-MOVEMENT values, raised and pulled back per GDD-07 §4), the
// taxi fare meter (GDD-07 §5: the player loop and the NPC loop are the same machine),
// damage-lite condition (GDD-07 §4), and the enter/exit contract with ANexoraCharacter.
//
// The wheel physics are NOT NEXORA logic: they are Chaos Vehicles, a phase-gated
// module (see the commented list in Nexora.Build.cs — "do NOT enable early"). The
// Chaos movement component is therefore a forward-declared pointer bound at ONE
// marked seam (BindChaosMovement) when Phase 5 enables the module on the owner's
// PC; docs/TECH-VEHICLES.md lists the exact enable steps. Nothing else in this
// class waits on Chaos.
//
// Money: the fare meter computes in float and rounds to integer NCr exactly once,
// at trip completion (GDD-01 §8: no floats near money; GDD-07 §5: fares are
// rounded before any ledger row is written). This pawn never writes ledger rows —
// it broadcasts OnFareCompleted and the economy/profession system writes the row.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "NexoraVehiclePawn.generated.h"

class ANexoraCharacter;
class USkeletalMeshComponent;
class USpringArmComponent;
class UCameraComponent;
class UChaosWheeledVehicleMovementComponent;

/** Camera states of GDD-07 §4: chase (default), hood, free-look on the chase rig. */
UENUM(BlueprintType)
enum class ENexoraVehicleCameraState : uint8
{
	Chase,
	Hood,
	FreeLook
};

/** Fare meter states (GDD-07 §5). Completed lasts until the economy system acks payment. */
UENUM(BlueprintType)
enum class ENexoraFareState : uint8
{
	Idle,
	Hired,
	Completed
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FNexoraFareCompletedSignature, int32, FareNcr, float, TripKm);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FNexoraDriverChangedSignature, ANexoraVehiclePawn*, Vehicle, ANexoraCharacter*, Driver);

UCLASS()
class NEXORA_API ANexoraVehiclePawn : public APawn
{
	GENERATED_BODY()

public:
	ANexoraVehiclePawn();

	virtual void Tick(float DeltaSeconds) override;

	// ---- Input surface (called by ANexoraPlayerController's Enhanced Input bindings,
	//      the driving action set of GDD-07 §4: steer / throttle / brake / handbrake / horn / exit).
	//      Values are stored and forwarded to Chaos at the seam; they are safe to call
	//      with no driver and no Chaos bound (both are checked). ----
	void SetSteering(float Value);   // -1..1
	void SetThrottle(float Value);   //  0..1
	void SetBrake(float Value);      //  0..1
	void SetHandbrake(bool bEngaged);
	void SoundHorn();

	// ---- Enter / exit contract (docs/TECH-VEHICLES.md §2 is the full contract).
	//      TryEnter is called by the controller's interact path at the driver door
	//      (GDD-05 prompt: "[F] — Enter vehicle"). Possession itself is the
	//      controller's job; this pawn owns occupancy and the seat transform. ----
	bool TryEnter(ANexoraCharacter* Character);
	bool ExitVehicle();
	bool IsOccupied() const { return DriverCharacter != nullptr; }
	ANexoraCharacter* GetDriver() const { return DriverCharacter; }
	FTransform GetDriverSeatTransform() const;
	FTransform GetDoorExitTransform() const;

	/** Broadcast on every enter/exit. The society systems bind this to record the
	 *  character's state as `driving` (GDD-07 §4) and to park/resume schedules. */
	UPROPERTY(BlueprintAssignable, Category = "NEXORA|Vehicle")
	FNexoraDriverChangedSignature OnDriverChanged;

	// ---- Fare meter (GDD-07 §5). Prices are config mirrors of data/prices.json
	//      `taxi_fares` — prices.json owns the numbers; if they ever disagree,
	//      prices.json wins and these defaults are fixed. ----
	bool StartTrip();
	void CancelTrip();
	int32 CompleteTrip();            // returns the fare in integer NCr, 0 if not Hired
	void AcknowledgeFarePaid();      // economy system calls this after writing the ledger row: Completed -> Idle
	ENexoraFareState GetFareState() const { return FareState; }
	float GetTripDistanceKm() const { return TripDistanceCm / 100000.0f; }

	/** Set by the weather/clock consumers (TECH-CLOCK-WEATHER): surge applies when
	 *  either is true (prices.json taxi_fares.surge_conditions: rain, night). */
	void SetSurgeConditions(bool bRain, bool bNight);

	UPROPERTY(BlueprintAssignable, Category = "NEXORA|Vehicle")
	FNexoraFareCompletedSignature OnFareCompleted;

	// ---- Damage-lite condition (GDD-07 §4: exactly three effects in v1 — cosmetic
	//      state, top-speed scale below 40, repair cost). No total loss, ever. ----
	void ApplyCollisionDamage(float ImpactSpeedCmPerSec);
	float GetCondition() const { return Condition; }
	float GetTopSpeedScale() const { return Condition < 40.0f ? 0.75f : 1.0f; }
	int32 GetRepairCostNcr() const;

	// ---- Camera ----
	void SetCameraState(ENexoraVehicleCameraState NewState);
	ENexoraVehicleCameraState GetCameraState() const { return CameraState; }
	void Look(const FVector2D& LookVector);   // free-look only; mirrors the on-foot look rules

protected:
	virtual void BeginPlay() override;

	/** THE CHAOS SEAM. Phase 5, on the owner's PC: enable the ChaosVehicles plugin,
	 *  uncomment "ChaosVehicles" in Nexora.Build.cs, then create the movement
	 *  component here and apply the stored inputs to it in ApplyInputsToMovement().
	 *  Until then this logs once and the pawn is a static (but complete) shell —
	 *  by design, so Phases 1–4 compile without a Phase 5 module. */
	void BindChaosMovement();
	void ApplyInputsToMovement();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "NEXORA|Vehicle")
	TObjectPtr<USkeletalMeshComponent> VehicleMesh;

	/** Created at the seam above; null in every build before Phase 5 enables Chaos. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "NEXORA|Vehicle")
	TObjectPtr<UChaosWheeledVehicleMovementComponent> ChaosMovement;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "NEXORA|Camera")
	TObjectPtr<USpringArmComponent> CameraBoom;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "NEXORA|Camera")
	TObjectPtr<UCameraComponent> VehicleCamera;

	// Chase rig: the on-foot boom family (450 cm, TECH-MOVEMENT) raised and pulled
	// back for the vehicle, per GDD-07 §4. Collision shortening is the spring arm's
	// own probe — the same behaviour the Godot testbed verified at walls.
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Camera")
	float ChaseBoomLength = 700.0f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Camera")
	float ChaseBoomHeight = 250.0f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Camera")
	float HoodCameraHeight = 110.0f;

	// Fare config — mirrors of prices.json `taxi_fares` (60 + 25/km, surge x1.5).
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Fare")
	int32 BaseFareNcr = 60;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Fare")
	int32 PerKmNcr = 25;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Fare")
	float SurgeMultiplier = 1.5f;

	/** Placeholder tuning, flagged honestly: prices.json has NO repair rate yet.
	 *  The economy pass owns the final number (GDD-07 §4: repair is priced from
	 *  the damage amount); until then this constant keeps the rule testable. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Vehicle")
	int32 RepairCostPerConditionPointNcr = 45;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "NEXORA|Vehicle")
	TObjectPtr<ANexoraCharacter> DriverCharacter;

	ENexoraFareState FareState = ENexoraFareState::Idle;
	ENexoraVehicleCameraState CameraState = ENexoraVehicleCameraState::Chase;

	float TripDistanceCm = 0.0f;
	bool bSurgeRain = false;
	bool bSurgeNight = false;

	float Condition = 100.0f;

	float SteeringInput = 0.0f;
	float ThrottleInput = 0.0f;
	float BrakeInput = 0.0f;
	bool bHandbrakeEngaged = false;
	bool bChaosBindWarned = false;

	FVector2D FreeLookOffset = FVector2D::ZeroVector;
};
