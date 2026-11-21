// NEXORA — NexoraSaveGame.cpp
// UNCOMPILED SCAFFOLD — written to UE 5.8 API conventions in a Linux VM without the engine;
// first compile happens on the owner's PC (Phase 1/3).

#include "NexoraSaveGame.h"
#include "Systems/NexoraGameClock.h"
#include "Systems/NexoraWeatherManager.h"

void UNexoraSaveGame::CaptureWorldState(const UNexoraGameClock* Clock, const UNexoraWeatherManager* Weather)
{
	if (Clock)
	{
		// world_state.game_minutes is a single running total; the clock splits it
		// into day + minutes-since-midnight. Recompose it here, nowhere else.
		GameMinutes = static_cast<int64>(Clock->DayNumber - 1) * 1440
			+ FMath::FloorToInt(Clock->MinutesSinceMidnight);
		TimeScale = Clock->TimeScale;
	}

	if (Weather)
	{
		WeatherPresetId = Weather->CurrentPreset.PresetId;
	}

	SavedAtUtc = FDateTime::UtcNow();
}

void UNexoraSaveGame::ApplyWorldState(UNexoraGameClock* Clock, UNexoraWeatherManager* Weather) const
{
	if (Clock)
	{
		const int64 SafeMinutes = FMath::Max<int64>(GameMinutes, 0);
		Clock->DayNumber = static_cast<int32>(SafeMinutes / 1440) + 1;
		Clock->SetTimeOfDay(
			static_cast<int32>((SafeMinutes % 1440) / 60),
			static_cast<int32>(SafeMinutes % 60));
		Clock->SetTimeScale(TimeScale);
	}

	if (Weather)
	{
		// Restore the weather STATE; the manager re-derives the exact preset
		// (e.g. sunrise_clear vs clear_day) from the restored time of day.
		const ENexoraWeatherState RestoredState = WeatherStateForPresetId(WeatherPresetId);
		if (RestoredState != Weather->CurrentWeather)
		{
			Weather->SetWeather(RestoredState);
		}
	}
}

bool UNexoraSaveGame::MigrateIfNeeded()
{
	if (SaveSchemaVersion == CurrentSchemaVersion)
	{
		return true;
	}

	if (SaveSchemaVersion > CurrentSchemaVersion)
	{
		// A save written by a newer build. Refuse: loading it here would silently
		// drop fields this build does not know exist.
		return false;
	}

	// Older save: forward-only migration steps land here, one block per version
	// hop, each transforming the payloads and then stamping the new version, e.g.
	//   if (SaveSchemaVersion == 1) { ...; SaveSchemaVersion = 2; }
	// v1 is the first schema, so no blocks exist yet — and an older-than-v1 claim
	// has no honest migration path. Do NOT stamp it current and hope.
	return false;
}

FString UNexoraSaveGame::MakeSlotName(int32 SlotIndex)
{
	return FString::Printf(TEXT("NexoraSlot%d"), FMath::Max(SlotIndex, 0));
}

ENexoraWeatherState UNexoraSaveGame::WeatherStateForPresetId(const FString& PresetId)
{
	// Preset ids are the families of data/weather-presets.json; the three clear
	// variants differ only by time of day, which the restored clock re-supplies.
	if (PresetId == TEXT("cloudy"))  return ENexoraWeatherState::Cloudy;
	if (PresetId == TEXT("rain"))    return ENexoraWeatherState::Rain;
	if (PresetId == TEXT("storm"))   return ENexoraWeatherState::Storm;
	if (PresetId == TEXT("fog"))     return ENexoraWeatherState::Fog;
	if (PresetId == TEXT("windy"))   return ENexoraWeatherState::Wind;
	if (PresetId == TEXT("snow"))    return ENexoraWeatherState::Snow;
	return ENexoraWeatherState::Clear; // clear_day, sunrise_clear, night_clear, unknown
}
