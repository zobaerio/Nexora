// NEXORA — NexoraCharacter.cpp
// UNCOMPILED SCAFFOLD — written to UE 5.8 API conventions in a Linux VM without the engine;
// first compile happens on the owner's PC (Phase 1/3).
//
// Unit K: movement values are the Godot testbed's, converted m → cm (×100):
// walk 500, run 880, jump velocity 560 (apex 1.6 m at UE gravity), boom 450.
// Every value's derivation and its acceptance check: docs/TECH-MOVEMENT.md.

#include "NexoraCharacter.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/SpringArmComponent.h"

ANexoraCharacter::ANexoraCharacter()
{
	// The camera orbits independently of the body; the body turns to face its movement
	// direction. This matches the testbed (player.gd rotates only the mesh pivot toward
	// travel while the camera rig keeps its own yaw). The Unit D stub had the controller
	// yaw the pawn directly — corrected here, before any build depended on it.
	bUseControllerRotationPitch = false;
	bUseControllerRotationYaw = false;
	bUseControllerRotationRoll = false;

	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->bOrientRotationToMovement = true;
	Movement->RotationRate = FRotator(0.0f, 540.0f, 0.0f);
	Movement->MaxWalkSpeed = WalkSpeed;
	Movement->MaxAcceleration = GroundAcceleration;
	Movement->JumpZVelocity = JumpVelocity;
	// UE world gravity is −980 cm/s² at GravityScale 1.0 — the testbed's 9.8 m/s².
	Movement->GravityScale = 1.0f;
	Movement->AirControl = 0.35f;

	// Spring arm: collision test ON — the boom shortens at walls instead of clipping
	// (the behaviour the Godot testbed verified with its own spring arm).
	CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
	CameraBoom->SetupAttachment(RootComponent);
	// Raise the pivot from capsule centre (≈88 cm) to the testbed's camera height
	// (≈160 cm — player_test.gd measures camera distance from player + 1.6 m).
	CameraBoom->SetRelativeLocation(FVector(0.0f, 0.0f, 72.0f));
	CameraBoom->TargetArmLength = BoomLength;
	CameraBoom->bUsePawnControlRotation = true;
	CameraBoom->bDoCollisionTest = true;
	CameraBoom->ProbeSize = 12.0f;
	CameraBoom->bEnableCameraLag = true;
	CameraBoom->CameraLagSpeed = 12.0f;

	FollowCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FollowCamera"));
	FollowCamera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);
	FollowCamera->bUsePawnControlRotation = false;
	// Godot Camera3D default FOV is 75°; UE's 90° would change the framing the
	// testbed was tuned with. Set explicitly so the Phase 3 check compares like with like.
	FollowCamera->FieldOfView = 75.0f;
}

void ANexoraCharacter::BeginPlay()
{
	Super::BeginPlay();

	// Re-apply the speed in case a Blueprint child or an editor tweak changed the
	// movement component's defaults after construction.
	GetCharacterMovement()->MaxWalkSpeed = bRunning ? RunSpeed : WalkSpeed;
}

void ANexoraCharacter::Move(const FVector2D& MovementVector)
{
	if (GetController() == nullptr || MovementVector.IsNearlyZero())
	{
		return;
	}

	// Movement direction is relative to the camera (control rotation) yaw — the
	// testbed builds its direction from the camera rig's yaw the same way.
	const FRotator ControlRotation = GetControlRotation();
	const FRotator YawRotation(0.0f, ControlRotation.Yaw, 0.0f);

	const FVector ForwardDirection = FRotationMatrix(YawRotation).GetUnitAxis(EAxis::X);
	const FVector RightDirection = FRotationMatrix(YawRotation).GetUnitAxis(EAxis::Y);

	AddMovementInput(ForwardDirection, MovementVector.Y);
	AddMovementInput(RightDirection, MovementVector.X);
}

void ANexoraCharacter::Look(const FVector2D& LookVector)
{
	AddControllerYawInput(LookVector.X * LookSensitivity);
	AddControllerPitchInput(LookVector.Y * LookSensitivity);
}

void ANexoraCharacter::SetRunning(bool bInRunning)
{
	bRunning = bInRunning;
	GetCharacterMovement()->MaxWalkSpeed = bInRunning ? RunSpeed : WalkSpeed;
}

void ANexoraCharacter::Jump()
{
	// ACharacter::Jump sets the jump flag the movement component consumes on the
	// next tick — grounded-only, exactly like the testbed's is_on_floor() gate.
	Super::Jump();
	// Phase 2/3 hook: jump-start animation / sound triggers belong here, once a
	// MetaHuman body and an animation blueprint exist to trigger.
}

void ANexoraCharacter::StopJumping()
{
	Super::StopJumping();
}

void ANexoraCharacter::Landed(const FHitResult& Hit)
{
	Super::Landed(Hit);
	// Phase 2/3 hook: landing animation / dust / sound. Deliberately empty until
	// there is a build to hear and see it in.
}
