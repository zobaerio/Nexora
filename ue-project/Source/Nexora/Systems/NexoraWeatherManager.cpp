// NEXORA — NexoraWeatherManager.cpp
// UNCOMPILED SCAFFOLD — written to UE 5.8 API conventions in a Linux VM without the engine;
// first compile happens on the owner's PC (Phase 1/3).

#include "Systems/NexoraWeatherManager.h"
#include "Systems/NexoraGameClock.h"

void UNexoraWeatherManager::Initialize(UNexoraGameClock* InClock)
{
	Clock = InClock;
	CurrentPreset = DefaultPresetFor(CurrentWeather);
	TargetPreset = CurrentPreset;
	PreviousPreset = CurrentPreset;
	TransitionAlpha = 1.0f;
}

void UNexoraWeatherManager::TickWeather(float DeltaRealSeconds)
{
	if (TransitionAlpha >= 1.0f)
	{
		return;
	}

	TransitionElapsed += DeltaRealSeconds;
	TransitionAlpha = FMath::Clamp(TransitionElapsed / FMath::Max(TransitionDurationSeconds, 0.01f), 0.0f, 1.0f);
	CurrentPreset = BlendPresets(PreviousPreset, TargetPreset, TransitionAlpha);
	OnWeatherBlendUpdated.Broadcast(TransitionAlpha);
}

void UNexoraWeatherManager::SetWeather(ENexoraWeatherState NewWeather)
{
	if (NewWeather == ENexoraWeatherState::Snow && !bSnowZone)
	{
		// District 1 never snows. Silently accepting Snow here would put a snow preset
		// on a river-city scene and break the art direction; refuse and stay put.
		return;
	}

	if (NewWeather == CurrentWeather)
	{
		return;
	}

	PreviousWeather = CurrentWeather;
	PreviousPreset = CurrentPreset;
	CurrentWeather = NewWeather;
	TargetPreset = DefaultPresetFor(NewWeather);
	TransitionElapsed = 0.0f;
	TransitionAlpha = 0.0f;
	OnWeatherChanged.Broadcast(CurrentWeather, PreviousWeather);
}

bool UNexoraWeatherManager::ApplyPreset(const FString& PresetId)
{
	// TODO (Phase 4): replace this stub mapping with the real JSON load — read
	// data/weather-presets.json at startup into a TMap<FString, FWeatherPresetData>
	// and look the id up there. The ids below are the JSON ids, so the design data
	// is already the contract; only the loading code is missing.
	static const TMap<FString, ENexoraWeatherState> PresetToState = {
		{ TEXT("clear_day"),    ENexoraWeatherState::Clear  },
		{ TEXT("sunrise_clear"),ENexoraWeatherState::Clear  },
		{ TEXT("night_clear"),  ENexoraWeatherState::Clear  },
		{ TEXT("cloudy"),      ENexoraWeatherState::Cloudy },
		{ TEXT("rain"),        ENexoraWeatherState::Rain   },
		{ TEXT("storm"),       ENexoraWeatherState::Storm  },
		{ TEXT("fog"),         ENexoraWeatherState::Fog    },
		{ TEXT("windy"),       ENexoraWeatherState::Wind   },
		{ TEXT("snow"),        ENexoraWeatherState::Snow   },
	};

	const ENexoraWeatherState* Found = PresetToState.Find(PresetId);
	if (!Found)
	{
		return false;
	}
	SetWeather(*Found);
	return true;
}

FString UNexoraWeatherManager::ClockPresetIdForWeather(ENexoraWeatherState Weather, float MinutesSinceMidnight)
{
	if (Weather != ENexoraWeatherState::Clear)
	{
		return TEXT("");
	}
	// Clear weather still needs three different skies across the day.
	if (MinutesSinceMidnight >= 300.0f && MinutesSinceMidnight < 420.0f) return TEXT("sunrise_clear");
	if (MinutesSinceMidnight >= 1200.0f || MinutesSinceMidnight < 300.0f) return TEXT("night_clear");
	return TEXT("clear_day");
}

FWeatherPresetData UNexoraWeatherManager::DefaultPresetFor(ENexoraWeatherState Weather)
{
	// Fallback values — the design numbers live in data/weather-presets.json and
	// replace these when the JSON loader lands (Phase 4). They exist so the manager
	// behaves sensibly even before the data pipeline is wired.
	FWeatherPresetData Preset;
	switch (Weather)
	{
	case ENexoraWeatherState::Clear:
		Preset.PresetId = TEXT("clear_day");
		Preset.CloudCoverPercent = 5.0f; Preset.FogDensity = 0.0005f;
		Preset.PrecipitationRate = 0.0f; Preset.WindSpeedKmh = 10.0f; Preset.WindGustKmh = 18.0f;
		Preset.WetnessTarget = 0.0f; Preset.SunIntensity = 3.0f;
		break;
	case ENexoraWeatherState::Cloudy:
		Preset.PresetId = TEXT("cloudy");
		Preset.CloudCoverPercent = 70.0f; Preset.FogDensity = 0.001f;
		Preset.PrecipitationRate = 0.0f; Preset.WindSpeedKmh = 15.0f; Preset.WindGustKmh = 25.0f;
		Preset.WetnessTarget = 0.0f; Preset.SunIntensity = 1.8f;
		break;
	case ENexoraWeatherState::Rain:
		Preset.PresetId = TEXT("rain");
		Preset.CloudCoverPercent = 85.0f; Preset.FogDensity = 0.0025f;
		Preset.PrecipitationRate = 0.6f; Preset.WindSpeedKmh = 20.0f; Preset.WindGustKmh = 35.0f;
		Preset.WetnessTarget = 0.8f; Preset.SunIntensity = 0.7f;
		Preset.GameplayEffects = { TEXT("npc_cover_seeking"), TEXT("taxi_demand_up"), TEXT("road_grip_down") };
		break;
	case ENexoraWeatherState::Storm:
		Preset.PresetId = TEXT("storm");
		Preset.CloudCoverPercent = 100.0f; Preset.FogDensity = 0.004f;
		Preset.PrecipitationRate = 1.0f; Preset.WindSpeedKmh = 55.0f; Preset.WindGustKmh = 90.0f;
		Preset.WetnessTarget = 1.0f; Preset.SunIntensity = 0.3f;
		Preset.GameplayEffects = { TEXT("npc_cover_seeking"), TEXT("taxi_demand_up"), TEXT("road_grip_down"), TEXT("outdoor_work_halted") };
		break;
	case ENexoraWeatherState::Fog:
		Preset.PresetId = TEXT("fog");
		Preset.CloudCoverPercent = 60.0f; Preset.FogDensity = 0.008f;
		Preset.PrecipitationRate = 0.0f; Preset.WindSpeedKmh = 5.0f; Preset.WindGustKmh = 10.0f;
		Preset.WetnessTarget = 0.1f; Preset.SunIntensity = 1.0f;
		break;
	case ENexoraWeatherState::Wind:
		Preset.PresetId = TEXT("windy");
		Preset.CloudCoverPercent = 30.0f; Preset.FogDensity = 0.0008f;
		Preset.PrecipitationRate = 0.0f; Preset.WindSpeedKmh = 40.0f; Preset.WindGustKmh = 65.0f;
		Preset.WetnessTarget = 0.0f; Preset.SunIntensity = 2.5f;
		break;
	case ENexoraWeatherState::Snow:
		Preset.PresetId = TEXT("snow");
		Preset.CloudCoverPercent = 90.0f; Preset.FogDensity = 0.003f;
		Preset.PrecipitationRate = 0.5f; Preset.WindSpeedKmh = 25.0f; Preset.WindGustKmh = 45.0f;
		Preset.WetnessTarget = 0.4f; Preset.SunIntensity = 1.2f;
		Preset.GameplayEffects = { TEXT("npc_cover_seeking"), TEXT("road_grip_down") };
		break;
	}
	return Preset;
}

FWeatherPresetData UNexoraWeatherManager::BlendPresets(const FWeatherPresetData& From, const FWeatherPresetData& To, float Alpha)
{
	FWeatherPresetData Out = To;
	Out.CloudCoverPercent = FMath::Lerp(From.CloudCoverPercent, To.CloudCoverPercent, Alpha);
	Out.FogDensity = FMath::Lerp(From.FogDensity, To.FogDensity, Alpha);
	Out.PrecipitationRate = FMath::Lerp(From.PrecipitationRate, To.PrecipitationRate, Alpha);
	Out.WindSpeedKmh = FMath::Lerp(From.WindSpeedKmh, To.WindSpeedKmh, Alpha);
	Out.WindGustKmh = FMath::Lerp(From.WindGustKmh, To.WindGustKmh, Alpha);
	Out.WetnessTarget = FMath::Lerp(From.WetnessTarget, To.WetnessTarget, Alpha);
	Out.SunIntensity = FMath::Lerp(From.SunIntensity, To.SunIntensity, Alpha);
	// Gameplay effects switch with the target, not the blend — an NPC either seeks
	// cover or it doesn't; there is no half-cover state.
	return Out;
}
