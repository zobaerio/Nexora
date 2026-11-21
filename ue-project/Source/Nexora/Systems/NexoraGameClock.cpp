// NEXORA — NexoraGameClock.cpp
// UNCOMPILED SCAFFOLD — written to UE 5.8 API conventions in a Linux VM without the engine;
// first compile happens on the owner's PC (Phase 1/3).

#include "Systems/NexoraGameClock.h"

void UNexoraGameClock::Initialize()
{
	CurrentPhase = PhaseForMinutes(MinutesSinceMidnight);
}

void UNexoraGameClock::TickClock(float DeltaRealSeconds)
{
	if (bPaused || TimeScale <= 0.0f)
	{
		return;
	}

	// DeltaRealSeconds * TimeScale = in-game seconds; / 60 = in-game minutes.
	MinutesSinceMidnight += (DeltaRealSeconds * TimeScale) / 60.0f;

	if (MinutesSinceMidnight >= 1440.0f)
	{
		MinutesSinceMidnight -= 1440.0f;
		DayNumber += 1;
		OnNewDay.Broadcast(DayNumber);
	}

	const ENexoraDayPhase NewPhase = PhaseForMinutes(MinutesSinceMidnight);
	if (NewPhase != CurrentPhase)
	{
		CurrentPhase = NewPhase;
		OnDayPhaseChanged.Broadcast(CurrentPhase);
	}

	OnClockTimeChanged.Broadcast();
}

void UNexoraGameClock::SetTimeOfDay(int32 Hour, int32 Minute)
{
	MinutesSinceMidnight = FMath::Clamp(static_cast<float>(Hour * 60 + Minute), 0.0f, 1439.0f);
	CurrentPhase = PhaseForMinutes(MinutesSinceMidnight);
	OnClockTimeChanged.Broadcast();
}

void UNexoraGameClock::SetTimeScale(float NewTimeScale)
{
	// Never allow a negative or absurd scale — a bad value here corrupts every
	// time-driven system at once (schedules, aging, economy).
	TimeScale = FMath::Clamp(NewTimeScale, 0.0f, 3600.0f);
}

void UNexoraGameClock::SetPaused(bool bInPaused)
{
	bPaused = bInPaused;
}

ENexoraDayPhase UNexoraGameClock::PhaseForMinutes(float InMinutes)
{
	// Boundaries are the design table in docs/TECH-CLOCK-WEATHER.md §1.
	// Night covers both 00:00-05:00 and 20:00-24:00.
	if (InMinutes >= 300.0f && InMinutes < 420.0f)  return ENexoraDayPhase::Dawn;      // 05:00-07:00
	if (InMinutes >= 420.0f && InMinutes < 720.0f)  return ENexoraDayPhase::Morning;   // 07:00-12:00
	if (InMinutes >= 720.0f && InMinutes < 1020.0f) return ENexoraDayPhase::Afternoon; // 12:00-17:00
	if (InMinutes >= 1020.0f && InMinutes < 1200.0f) return ENexoraDayPhase::Evening;  // 17:00-20:00
	return ENexoraDayPhase::Night;
}
