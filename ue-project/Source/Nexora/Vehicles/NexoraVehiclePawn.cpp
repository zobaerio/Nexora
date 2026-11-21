// NEXORA — NexoraVehiclePawn.cpp
// UNCOMPILED SCAFFOLD — written to UE 5.8 API conventions in a Linux VM without the engine;
// first compile happens on the owner's PC (Phase 5 for this file; the module's first
// compile is Phase 1/3). See NexoraVehiclePawn.h for the design contract and
// docs/TECH-VEHICLES.md for the Chaos enable steps and the enter/exit sequence.

#include "Vehicles/NexoraVehiclePawn.h"
#include "NexoraCharacter.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/SpringArmComponent.h"

ANexoraVehiclePawn::ANexoraVehiclePawn()
{
	PrimaryActorTick.bCanEverTick = true;

	VehicleMesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("VehicleMesh"));
	RootComponent = VehicleMesh;

	// Same spring-arm family as the on-foot camera (TECH-MOVEMENT): the arm's own
	// collision probe shortens the boom at walls instead of clipping.
	CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
	CameraBoom->SetupAttachment(VehicleMesh);
	CameraBoom->bUsePawnControlRotation = false;
	CameraBoom->bEnableCameraLag = true;

	VehicleCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("VehicleCamera"));
	VehicleCamera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);
}

void ANexoraVehiclePawn::BeginPlay()
{
	Super::BeginPlay();
	BindChaosMovement();
	SetCameraState(ENexoraVehicleCameraState::Chase);
}

void ANexoraVehiclePawn::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	// Odometer: the fare meter measures the trip the same way for a player driver
	// and an NPC driver (GDD-07 §5 — one machine, two seats).
	if (IsOccupied() && FareState == ENexoraFareState::Hired)
	{
		TripDistanceCm += GetVelocity().Size() * DeltaSeconds;
	}

	ApplyInputsToMovement();
}

// ---------------------------------------------------------------------------
// Input surface
// ---------------------------------------------------------------------------

void ANexoraVehiclePawn::SetSteering(float Value)
{
	SteeringInput = FMath::Clamp(Value, -1.0f, 1.0f);
}

void ANexoraVehiclePawn::SetThrottle(float Value)
{
	ThrottleInput = FMath::Clamp(Value, 0.0f, 1.0f);
}

void ANexoraVehiclePawn::SetBrake(float Value)
{
	BrakeInput = FMath::Clamp(Value, 0.0f, 1.0f);
}

void ANexoraVehiclePawn::SetHandbrake(bool bEngaged)
{
	bHandbrakeEngaged = bEngaged;
}

void ANexoraVehiclePawn::SoundHorn()
{
	// TODO(Phase 8 — audio): play the class horn sound here. No placeholder beep:
	// a silent horn in scaffold builds is honest; a wrong horn is a shipped bug.
}

// ---------------------------------------------------------------------------
// Enter / exit
// ---------------------------------------------------------------------------

bool ANexoraVehiclePawn::TryEnter(ANexoraCharacter* Character)
{
	if (!Character || IsOccupied())
	{
		return false;
	}

	DriverCharacter = Character;

	// The character rides the seat, it does not stand in the car: hide the body
	// and parent it to the seat socket so saves/streaming keep it with the vehicle.
	// Phase 5 mesh requirement: the vehicle skeletal mesh provides "Seat_Driver"
	// (docs/TECH-VEHICLES.md §2). Until a mesh does, the attach falls back to the
	// mesh root and the seat transform below still reports the design position.
	Character->SetActorHiddenInGame(true);
	Character->AttachToComponent(VehicleMesh,
		FAttachmentTransformRules::SnapToTargetNotIncludingScale, TEXT("Seat_Driver"));

	OnDriverChanged.Broadcast(this, DriverCharacter);
	return true;
}

bool ANexoraVehiclePawn::ExitVehicle()
{
	if (!IsOccupied())
	{
		return false;
	}

	ANexoraCharacter* Exiting = DriverCharacter;
	DriverCharacter = nullptr;

	Exiting->DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
	Exiting->SetActorLocation(GetDoorExitTransform().GetLocation());
	Exiting->SetActorHiddenInGame(false);

	// Leaving the seat ends any uncompleted trip without a fare: a passenger is
	// never charged for a trip the driver abandoned (GDD-07 §5 pays at dropoff).
	if (FareState == ENexoraFareState::Hired)
	{
		CancelTrip();
	}

	OnDriverChanged.Broadcast(this, nullptr);
	return true;
}

FTransform ANexoraVehiclePawn::GetDriverSeatTransform() const
{
	if (VehicleMesh && VehicleMesh->DoesSocketExist(TEXT("Seat_Driver")))
	{
		return VehicleMesh->GetSocketTransform(TEXT("Seat_Driver"));
	}
	// Design position until the Phase 5 mesh provides the socket: Rupsha City
	// drives on the left, so the driver sits on the RIGHT of the cabin.
	return FTransform(GetActorRotation(),
		GetActorLocation() + GetActorRightVector() * 45.0f + FVector(0.0f, 0.0f, 95.0f));
}

FTransform ANexoraVehiclePawn::GetDoorExitTransform() const
{
	// Right-hand door (driver's side in Bangladesh): out 1.5 m, on the ground plane.
	const FVector ExitLocation = GetActorLocation() + GetActorRightVector() * 150.0f;
	return FTransform(GetActorRotation(), ExitLocation);
}

// ---------------------------------------------------------------------------
// Fare meter
// ---------------------------------------------------------------------------

bool ANexoraVehiclePawn::StartTrip()
{
	if (!IsOccupied() || FareState != ENexoraFareState::Idle)
	{
		return false;
	}
	TripDistanceCm = 0.0f;
	FareState = ENexoraFareState::Hired;
	return true;
}

void ANexoraVehiclePawn::CancelTrip()
{
	TripDistanceCm = 0.0f;
	FareState = ENexoraFareState::Idle;
}

int32 ANexoraVehiclePawn::CompleteTrip()
{
	if (FareState != ENexoraFareState::Hired)
	{
		return 0;
	}

	// prices.json taxi_fares: base + per-km, surge x1.5 under rain/night.
	// Float is allowed to compute; the integer is what leaves this function —
	// the ledger only ever sees whole NCr (GDD-01 §8, GDD-07 §5).
	float Fare = static_cast<float>(BaseFareNcr) + PerKmNcr * GetTripDistanceKm();
	if (bSurgeRain || bSurgeNight)
	{
		Fare *= SurgeMultiplier;
	}
	const int32 FareNcr = FMath::RoundToInt(Fare);

	FareState = ENexoraFareState::Completed;
	OnFareCompleted.Broadcast(FareNcr, GetTripDistanceKm());
	return FareNcr;
}

void ANexoraVehiclePawn::AcknowledgeFarePaid()
{
	if (FareState == ENexoraFareState::Completed)
	{
		TripDistanceCm = 0.0f;
		FareState = ENexoraFareState::Idle;
	}
}

void ANexoraVehiclePawn::SetSurgeConditions(bool bRain, bool bNight)
{
	bSurgeRain = bRain;
	bSurgeNight = bNight;
}

// ---------------------------------------------------------------------------
// Damage-lite condition
// ---------------------------------------------------------------------------

void ANexoraVehiclePawn::ApplyCollisionDamage(float ImpactSpeedCmPerSec)
{
	// Below 3 m/s a touch is a touch, not damage. Above that, damage grows
	// linearly with the excess speed — a rule the economy can price (GDD-07 §4),
	// not a physics claim.
	const float Damage = FMath::Max(0.0f, (ImpactSpeedCmPerSec - 300.0f) / 100.0f);
	Condition = FMath::Clamp(Condition - Damage, 0.0f, 100.0f);
}

int32 ANexoraVehiclePawn::GetRepairCostNcr() const
{
	return FMath::RoundToInt((100.0f - Condition) * RepairCostPerConditionPointNcr);
}

// ---------------------------------------------------------------------------
// Camera
// ---------------------------------------------------------------------------

void ANexoraVehiclePawn::SetCameraState(ENexoraVehicleCameraState NewState)
{
	CameraState = NewState;
	if (!CameraBoom)
	{
		return;
	}

	switch (NewState)
	{
	case ENexoraVehicleCameraState::Chase:
	case ENexoraVehicleCameraState::FreeLook:
		CameraBoom->TargetArmLength = ChaseBoomLength;
		CameraBoom->SocketOffset = FVector(0.0f, 0.0f, ChaseBoomHeight);
		CameraBoom->SetRelativeRotation(FRotator::ZeroRotator);
		FreeLookOffset = FVector2D::ZeroVector;
		break;
	case ENexoraVehicleCameraState::Hood:
		// The boom collapses to the bonnet: the driver sees the road, not the car.
		CameraBoom->TargetArmLength = 0.0f;
		CameraBoom->SocketOffset = FVector(180.0f, 0.0f, HoodCameraHeight);
		break;
	}
}

void ANexoraVehiclePawn::Look(const FVector2D& LookVector)
{
	if (CameraState != ENexoraVehicleCameraState::FreeLook || !CameraBoom)
	{
		return;
	}
	FreeLookOffset.X = FMath::Clamp(FreeLookOffset.X + LookVector.X, -70.0f, 70.0f);
	FreeLookOffset.Y = FMath::Clamp(FreeLookOffset.Y + LookVector.Y, -20.0f, 20.0f);
	CameraBoom->SetRelativeRotation(FRotator(-FreeLookOffset.Y, FreeLookOffset.X, 0.0f));
}

// ---------------------------------------------------------------------------
// The Chaos seam (see the header — this is the ONLY Phase 5 binding point)
// ---------------------------------------------------------------------------

void ANexoraVehiclePawn::BindChaosMovement()
{
	// Phase 5, on the owner's PC, in order (docs/TECH-VEHICLES.md §1):
	//   1. Enable the ChaosVehicles plugin in Nexora.uproject.
	//   2. Uncomment "ChaosVehicles" in Nexora.Build.cs (it is listed there,
	//      phase-gated, today).
	//   3. #include "ChaosWheeledVehicleMovementComponent.h" here, create the
	//      component in this function, and set up wheels in the vehicle
	//      Blueprint (wheel classes are content, not code).
	// Until then the pawn is a complete shell that does not roll — stated,
	// not disguised: it logs once so a Phase 1–4 build is never mistaken
	// for a driving build.
	if (!bChaosBindWarned)
	{
		bChaosBindWarned = true;
		UE_LOG(LogTemp, Warning,
			TEXT("NexoraVehiclePawn: Chaos Vehicles is not bound (Phase 5 seam). This pawn will not move."));
	}
}

void ANexoraVehiclePawn::ApplyInputsToMovement()
{
	if (!ChaosMovement)
	{
		return;
	}
	// Phase 5 (after BindChaosMovement creates the component):
	//   ChaosMovement->SetSteeringInput(SteeringInput);
	//   ChaosMovement->SetThrottleInput(ThrottleInput * GetTopSpeedScale());
	//   ChaosMovement->SetBrakeInput(BrakeInput);
	//   ChaosMovement->SetHandBrakeInput(bHandbrakeEngaged);
	// GetTopSpeedScale() is where damage-lite reaches the wheels (GDD-07 §4:
	// -25% top cruise speed below 40 condition) — the throttle is scaled,
	// never the steering or brakes: a damaged car is slower, not less safe.
}
