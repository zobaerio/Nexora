// NEXORA — NexoraPlayerController.cpp
// UNCOMPILED SCAFFOLD — written to UE 5.8 API conventions in a Linux VM without the engine;
// first compile happens on the owner's PC (Phase 1/3).

#include "NexoraPlayerController.h"
#include "NexoraCharacter.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "InputActionValue.h"

ANexoraPlayerController::ANexoraPlayerController()
{
}

void ANexoraPlayerController::BeginPlay()
{
	Super::BeginPlay();

	// Register the NEXORA mapping context on the local player's Enhanced Input subsystem.
	if (ULocalPlayer* LocalPlayer = GetLocalPlayer())
	{
		if (UEnhancedInputLocalPlayerSubsystem* Subsystem =
			ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(LocalPlayer))
		{
			if (NexoraMappingContext)
			{
				Subsystem->AddMappingContext(NexoraMappingContext, 0);
			}
		}
	}
}

void ANexoraPlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();

	UEnhancedInputComponent* EnhancedInput = Cast<UEnhancedInputComponent>(InputComponent);
	if (!EnhancedInput)
	{
		return;
	}

	if (MoveAction)      EnhancedInput->BindAction(MoveAction,      ETriggerEvent::Triggered, this, &ANexoraPlayerController::OnMove);
	if (LookAction)      EnhancedInput->BindAction(LookAction,      ETriggerEvent::Triggered, this, &ANexoraPlayerController::OnLook);
	if (RunAction)
	{
		EnhancedInput->BindAction(RunAction, ETriggerEvent::Started,   this, &ANexoraPlayerController::OnRunStarted);
		EnhancedInput->BindAction(RunAction, ETriggerEvent::Completed, this, &ANexoraPlayerController::OnRunCompleted);
	}
	if (JumpAction)      EnhancedInput->BindAction(JumpAction,      ETriggerEvent::Started, this, &ANexoraPlayerController::OnJump);
	if (InteractAction)  EnhancedInput->BindAction(InteractAction,  ETriggerEvent::Started, this, &ANexoraPlayerController::OnInteract);
	if (PauseAction)     EnhancedInput->BindAction(PauseAction,     ETriggerEvent::Started, this, &ANexoraPlayerController::OnPause);
	if (TimeSkipAction)  EnhancedInput->BindAction(TimeSkipAction,  ETriggerEvent::Started, this, &ANexoraPlayerController::OnTimeSkip);
}

void ANexoraPlayerController::OnMove(const FInputActionValue& Value)
{
	if (ANexoraCharacter* Character = Cast<ANexoraCharacter>(GetPawn()))
	{
		Character->Move(Value.Get<FVector2D>());
	}
}

void ANexoraPlayerController::OnLook(const FInputActionValue& Value)
{
	if (ANexoraCharacter* Character = Cast<ANexoraCharacter>(GetPawn()))
	{
		Character->Look(Value.Get<FVector2D>());
	}
}

void ANexoraPlayerController::OnRunStarted()
{
	if (ANexoraCharacter* Character = Cast<ANexoraCharacter>(GetPawn()))
	{
		Character->SetRunning(true);
	}
}

void ANexoraPlayerController::OnRunCompleted()
{
	if (ANexoraCharacter* Character = Cast<ANexoraCharacter>(GetPawn()))
	{
		Character->SetRunning(false);
	}
}

void ANexoraPlayerController::OnJump()
{
	if (ANexoraCharacter* Character = Cast<ANexoraCharacter>(GetPawn()))
	{
		Character->Jump();
	}
}

void ANexoraPlayerController::OnInteract()
{
	// TODO (Phase 3): line-trace the interactable in front of the player and call its
	// Interact() — doors, sit, enter vehicle placeholder. No behaviour yet.
}

void ANexoraPlayerController::OnPause()
{
	// TODO (Phase 3): open the pause menu widget (UMG). Stubbed until the UI exists.
	SetPause(true);
}

void ANexoraPlayerController::OnTimeSkip()
{
	// TODO (Phase 7): sleep / time-skip prompt. Stubbed — the clock must never jump
	// without the presented time-skip the life-sim design requires (GDD-01 §3).
}
