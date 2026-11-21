// NEXORA — NexoraGameMode.cpp
// UNCOMPILED SCAFFOLD — written to UE 5.8 API conventions in a Linux VM without the engine;
// first compile happens on the owner's PC (Phase 1/3).

#include "NexoraGameMode.h"
#include "Systems/NexoraGameClock.h"
#include "Systems/NexoraWeatherManager.h"
#include "NexoraCharacter.h"
#include "NexoraPlayerController.h"

ANexoraGameMode::ANexoraGameMode()
{
	// Default pawn/controller classes for every NEXORA level until a level overrides them.
	DefaultPawnClass = ANexoraCharacter::StaticClass();
	PlayerControllerClass = ANexoraPlayerController::StaticClass();
}

void ANexoraGameMode::BeginPlay()
{
	Super::BeginPlay();

	// Systems are UObject subsystems owned by the GameMode so they die with the level
	// and are recreated cleanly on every map load (no stale clock across level changes).
	GameClock = NewObject<UNexoraGameClock>(this, TEXT("GameClock"));
	WeatherManager = NewObject<UNexoraWeatherManager>(this, TEXT("WeatherManager"));

	if (GameClock)
	{
		GameClock->Initialize();
	}
	if (WeatherManager && GameClock)
	{
		WeatherManager->Initialize(GameClock);
	}
}
