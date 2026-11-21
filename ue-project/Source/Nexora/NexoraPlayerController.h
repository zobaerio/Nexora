// NEXORA — NexoraPlayerController.h
// UNCOMPILED SCAFFOLD — written to UE 5.8 API conventions in a Linux VM without the engine;
// first compile happens on the owner's PC (Phase 1/3).
//
// Enhanced Input only. The Input Mapping Context (IMC_Nexora) and Input Actions
// (IA_Move, IA_Look, IA_Run, IA_Jump, IA_Interact, IA_Pause, IA_TimeSkip) are editor
// assets created in Phase 3 at /Game/Nexora/Input/ — see Config/DefaultInput.ini.
// This controller binds them and forwards movement to the possessed character.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "NexoraPlayerController.generated.h"

class UInputMappingContext;
class UInputAction;
struct FInputActionValue;

UCLASS()
class NEXORA_API ANexoraPlayerController : public APlayerController
{
	GENERATED_BODY()

public:
	ANexoraPlayerController();

protected:
	virtual void BeginPlay() override;
	virtual void SetupInputComponent() override;

	/** Input Mapping Context asset — set in the editor (Phase 3), path in DefaultInput.ini. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Input")
	TObjectPtr<UInputMappingContext> NexoraMappingContext;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Input")
	TObjectPtr<UInputAction> MoveAction;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Input")
	TObjectPtr<UInputAction> LookAction;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Input")
	TObjectPtr<UInputAction> RunAction;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Input")
	TObjectPtr<UInputAction> JumpAction;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Input")
	TObjectPtr<UInputAction> InteractAction;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Input")
	TObjectPtr<UInputAction> PauseAction;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "NEXORA|Input")
	TObjectPtr<UInputAction> TimeSkipAction;

	void OnMove(const FInputActionValue& Value);
	void OnLook(const FInputActionValue& Value);
	void OnRunStarted();
	void OnRunCompleted();
	void OnJump();
	void OnInteract();
	void OnPause();
	void OnTimeSkip();

	// TODO (Phase 3 acceptance test): movement keys match the Godot testbed exactly
	// (WASD move, Shift run, Space jump, F interact); camera boom shortens at walls.
	// TODO (Phase 7): TimeSkip opens the sleep/time-skip prompt only at a valid anchor
	// (bed / home); never mid-air, never during a mission cutscene.
};
