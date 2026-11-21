// NEXORA — NexoraCharacter.h
// UNCOMPILED SCAFFOLD — written to UE 5.8 API conventions in a Linux VM without the engine;
// first compile happens on the owner's PC (Phase 1/3).
//
// Third-person character: spring-arm camera with wall collision (same behaviour the
// Godot testbed verified — the boom shortens at walls instead of clipping), walk/run/jump
// matching the Godot controls table. The MetaHuman body replaces this placeholder mesh
// in Phase 2; movement code does not change when the mesh does.

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

	void SetRunning(bool bInRunning);

protected:
	virtual void BeginPlay() override;

	/** Spring arm — DoCollisionTest = true is what keeps the camera out of walls. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "NEXORA|Camera")
	TObjectPtr<USpringArmComponent> CameraBoom;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "NEXORA|Camera")
	TObjectPtr<UCameraComponent> FollowCamera;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Movement")
	float WalkSpeed = 300.0f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Movement")
	float RunSpeed = 600.0f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Camera")
	float BaseTurnRate = 90.0f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Camera")
	float BaseLookUpRate = 65.0f;

	// TODO (Phase 3 acceptance test): walk 300 u/s, run 600 u/s, jump velocity matches
	// the Godot testbed feel; camera never clips through a wall at full boom length.
	// TODO (Phase 2): swap the placeholder capsule mesh for the MetaHuman body;
	// movement values are re-tuned then, never before a build exists to test them in.
};
