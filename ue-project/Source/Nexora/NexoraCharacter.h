// NEXORA — NexoraCharacter.h
// UNCOMPILED SCAFFOLD — written to UE 5.8 API conventions in a Linux VM without the engine;
// first compile happens on the owner's PC (Phase 1/3).
//
// Unit K (Phase 3 prep): the movement the Unit D stub promised, filled in.
// Third-person character: spring-arm camera with wall collision (same behaviour the
// Godot testbed verified — the boom shortens at walls instead of clipping), walk/run/jump
// matched to the Godot testbed acceptance values (rupsha-city/scripts/player.gd +
// tests/player_test.gd, observed 2026-11-20):
//   walk 5.0 m/s · run ≈8.8 m/s · jump apex ≈1.6 m · camera boom 4.5 m
// The full mapping of every testbed test to its UE check lives in docs/TECH-MOVEMENT.md.
// The MetaHuman body replaces the placeholder mesh in Phase 2; movement code does not
// change when the mesh does.
//
// Input stays in ANexoraPlayerController (Enhanced Input bindings, DefaultInput.ini);
// this class exposes the movement surface the controller calls: Move / Look /
// SetRunning / Jump / StopJumping.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "NexoraCharacter.generated.h"

class USpringArmComponent;
class UCameraComponent;

UCLASS()
class NEXORA_API ANexoraCharacter : public ACharacter
{
	GENERATED_BODY()

public:
	ANexoraCharacter();

	/** Called by the PlayerController from IA_Move (Vector2D: X = strafe, Y = forward). */
	void Move(const FVector2D& MovementVector);

	/** Called by the PlayerController from IA_Look (Vector2D: X = yaw, Y = pitch). */
	void Look(const FVector2D& LookVector);

	/** Called by the PlayerController from IA_Run (Started / Completed). */
	void SetRunning(bool bInRunning);

	bool IsRunning() const { return bRunning; }

	/** ACharacter::Jump with NEXORA hooks — called by the PlayerController from IA_Jump. */
	virtual void Jump() override;
	virtual void StopJumping() override;

protected:
	virtual void BeginPlay() override;
	virtual void Landed(const FHitResult& Hit) override;

	/** Spring arm — DoCollisionTest = true is what keeps the camera out of walls. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "NEXORA|Camera")
	TObjectPtr<USpringArmComponent> CameraBoom;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "NEXORA|Camera")
	TObjectPtr<UCameraComponent> FollowCamera;

	/** Testbed walk speed 5.0 m/s, in cm/s. Acceptance: TECH-MOVEMENT.md §2. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Movement")
	float WalkSpeed = 500.0f;

	/** Testbed run ≈8.8 m/s (Godot run_speed 9.0 through its 30 m/s² ramp measured
	 *  8.77 m in 1.0 s), in cm/s. Acceptance: TECH-MOVEMENT.md §2. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Movement")
	float RunSpeed = 880.0f;

	/** Jump velocity chosen for the testbed apex: v²/(2g) with UE gravity 980 cm/s² —
	 *  560² / 1960 = 160 cm ≈ 1.6 m. Derivation: TECH-MOVEMENT.md §2. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Movement")
	float JumpVelocity = 560.0f;

	/** Testbed acceleration 30 m/s², in cm/s² — how fast walk/run speed is reached. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Movement")
	float GroundAcceleration = 3000.0f;

	/** Testbed boom length 4.5 m, in cm. Shortens on wall contact (collision test). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Camera")
	float BoomLength = 450.0f;

	/** Multiplier on IA_Look values before they reach the controller rotation.
	 *  1.0 = pass-through; fine sensitivity tuning belongs to the IMC modifiers
	 *  created in Phase 3 (DefaultInput.ini), not to this constant. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Camera")
	float LookSensitivity = 1.0f;

private:
	bool bRunning = false;

	// TODO (Phase 2): swap the placeholder capsule mesh for the MetaHuman body;
	// movement values are re-checked against TECH-MOVEMENT.md then, never re-tuned
	// before a build exists to test them in.
	// TODO (Phase 3): pitch clamp −65°/+30° (testbed player.gd) is a PlayerCameraManager
	// class default on the controller — see TECH-MOVEMENT.md §3 before wiring the IMC.
};
