// NEXORA — NexoraGameMode.h
// UNCOMPILED SCAFFOLD — written to UE 5.8 API conventions in a Linux VM without the engine;
// first compile happens on the owner's PC (Phase 1/3).
//
// Owns the world-level systems: game clock (Unit E), weather (Unit E), and later the
// life simulation, economy and schedule ticks (Phases 5–7). Subsystems are created here
// so every level in the game shares one clock and one weather state.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "NexoraGameMode.generated.h"

class UNexoraGameClock;
class UNexoraWeatherManager;

UCLASS()
class NEXORA_API ANexoraGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	ANexoraGameMode();

	/** World clock — one per game, shared by every system (Unit E). */
	UPROPERTY(BlueprintReadOnly, Category = "NEXORA|Systems")
	TObjectPtr<UNexoraGameClock> GameClock;

	/** Weather state machine — one per game (Unit E). */
	UPROPERTY(BlueprintReadOnly, Category = "NEXORA|Systems")
	TObjectPtr<UNexoraWeatherManager> WeatherManager;

protected:
	virtual void BeginPlay() override;

	// TODO (Phase 3 acceptance test): GameMode spawns GameClock + WeatherManager before
	// the player pawn possesses; the HUD clock readout matches GameClock time exactly.
	// TODO (Phase 5): create LifeSimSubsystem + EconomySubsystem here, same pattern.
	// TODO (Phase 9): server-authoritative mode — clock/weather tick on server only,
	// clients replicate state (never simulate their own).
};
