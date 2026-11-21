// NEXORA — NexoraGameClock.h
// UNCOMPILED SCAFFOLD — written to UE 5.8 API conventions in a Linux VM without the engine;
// first compile happens on the owner's PC (Phase 1/3).
//
// One world clock for the whole game. Everything time-driven reads this object:
// day-night lighting (Phase 4), NPC schedules (Phase 6), the life simulation tick
// (GDD-01 §4 — one in-game day = one simulation day at any speed), and the economy
// tick (GDD-03). Speed is a design setting, never a constant.

#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "NexoraGameClock.generated.h"

/** Day phases — the owner's table, fixed boundaries so schedules and lighting agree. */
UENUM(BlueprintType)
enum class ENexoraDayPhase : uint8
{
	Night     UMETA(DisplayName = "Night (00:00-05:00, 20:00-24:00)"),
	Dawn      UMETA(DisplayName = "Dawn (05:00-07:00)"),
	Morning   UMETA(DisplayName = "Morning (07:00-12:00)"),
	Afternoon UMETA(DisplayName = "Afternoon (12:00-17:00)"),
	Evening   UMETA(DisplayName = "Evening (17:00-20:00)")
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnDayPhaseChanged, ENexoraDayPhase, NewPhase);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnNewDay, int32, NewDayNumber);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnClockTimeChanged);

UCLASS(BlueprintType)
class NEXORA_API UNexoraGameClock : public UObject
{
	GENERATED_BODY()

public:
	/** How many in-game seconds pass per real second. Default 60 = one in-game day
	    per 24 real minutes. The life-sim accelerated test (Phase 6) raises this; the
	    value is a setting, and the simulation rules never depend on it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "NEXORA|Clock")
	float TimeScale = 60.0f;

	/** Game day counter, starting at 1. Drives save slots, the economy tick and ages. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "NEXORA|Clock")
	int32 DayNumber = 1;

	/** Minutes since midnight, 0..1439. The single source of truth for time of day. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "NEXORA|Clock")
	float MinutesSinceMidnight = 540.0f; // 09:00 — the owner spec's reference hour.

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "NEXORA|Clock")
	ENexoraDayPhase CurrentPhase = ENexoraDayPhase::Morning;

	UPROPERTY(BlueprintAssignable, Category = "NEXORA|Clock")
	FOnDayPhaseChanged OnDayPhaseChanged;

	UPROPERTY(BlueprintAssignable, Category = "NEXORA|Clock")
	FOnNewDay OnNewDay;

	UPROPERTY(BlueprintAssignable, Category = "NEXORA|Clock")
	FOnClockTimeChanged OnClockTimeChanged;

	void Initialize();

	/** Called every frame by the GameMode (or a ticking actor in Phase 4). */
	void TickClock(float DeltaRealSeconds);

	UFUNCTION(BlueprintCallable, Category = "NEXORA|Clock")
	void SetTimeOfDay(int32 Hour, int32 Minute);

	UFUNCTION(BlueprintCallable, Category = "NEXORA|Clock")
	void SetTimeScale(float NewTimeScale);

	/** Pause the clock without pausing the game (menus, cutscenes). */
	UFUNCTION(BlueprintCallable, Category = "NEXORA|Clock")
	void SetPaused(bool bInPaused);

	UFUNCTION(BlueprintPure, Category = "NEXORA|Clock")
	int32 GetHour() const { return FMath::FloorToInt(MinutesSinceMidnight / 60.0f); }

	UFUNCTION(BlueprintPure, Category = "NEXORA|Clock")
	int32 GetMinute() const { return FMath::FloorToInt(FMath::Fmod(MinutesSinceMidnight, 60.0f)); }

	/** 0..1 across the current day — drives the sun position (docs/TECH-CLOCK-WEATHER.md). */
	UFUNCTION(BlueprintPure, Category = "NEXORA|Clock")
	float GetDayFraction() const { return MinutesSinceMidnight / 1440.0f; }

	UFUNCTION(BlueprintPure, Category = "NEXORA|Clock")
	static ENexoraDayPhase PhaseForMinutes(float InMinutes);

private:
	bool bPaused = false;
};
