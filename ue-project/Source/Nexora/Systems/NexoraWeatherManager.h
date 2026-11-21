// NEXORA — NexoraWeatherManager.h
// UNCOMPILED SCAFFOLD — written to UE 5.8 API conventions in a Linux VM without the engine;
// first compile happens on the owner's PC (Phase 1/3).
//
// Weather state machine. Presets are data, not code: the tuning values live in
// data/weather-presets.json (ids: clear_day, sunrise_clear, night_clear, cloudy, rain,
// storm, fog, windy, snow) and are loaded into FWeatherPresetData at runtime; the
// manager only blends between states and broadcasts changes. The Environment Control
// Panel (master plan Part C #5) reads/writes through this class.

#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "NexoraWeatherManager.generated.h"

class UNexoraGameClock;

/** Weather states — one per preset family in data/weather-presets.json. */
UENUM(BlueprintType)
enum class ENexoraWeatherState : uint8
{
	Clear  UMETA(DisplayName = "Clear"),
	Cloudy UMETA(DisplayName = "Cloudy"),
	Rain   UMETA(DisplayName = "Rain"),
	Storm  UMETA(DisplayName = "Storm"),
	Fog    UMETA(DisplayName = "Fog"),
	Wind   UMETA(DisplayName = "Windy"),
	Snow   UMETA(DisplayName = "Snow")
};

/** One preset's tunable values, mirroring data/weather-presets.json field for field.
    The JSON is the design source; this struct is the runtime copy. */
USTRUCT(BlueprintType)
struct FWeatherPresetData
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	FString PresetId;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	float CloudCoverPercent = 5.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	float FogDensity = 0.0005f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	float PrecipitationRate = 0.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	float WindSpeedKmh = 10.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	float WindGustKmh = 18.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	float WetnessTarget = 0.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	float SunIntensity = 3.0f;

	/** Gameplay flags from the preset, e.g. npc_cover_seeking, taxi_demand_up, road_grip_down. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite)
	TArray<FString> GameplayEffects;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FOnWeatherChanged, ENexoraWeatherState, NewWeather, ENexoraWeatherState, PreviousWeather);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnWeatherBlendUpdated, float, BlendAlpha);

UCLASS(BlueprintType)
class NEXORA_API UNexoraWeatherManager : public UObject
{
	GENERATED_BODY()

public:
	/** Seconds a weather change takes to blend in. Rain arriving instantly looks wrong. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "NEXORA|Weather")
	float TransitionDurationSeconds = 8.0f;

	/** Snow only exists where this is true (high-altitude zones, Phase 10 planets).
	    District 1 never snows — the preset exists in data for later regions. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "NEXORA|Weather")
	bool bSnowZone = false;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "NEXORA|Weather")
	ENexoraWeatherState CurrentWeather = ENexoraWeatherState::Clear;

	/** 0..1 blend progress of the in-flight transition. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "NEXORA|Weather")
	float TransitionAlpha = 1.0f;

	/** Live, blended preset values — what the sky, fog, Niagara and materials read. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "NEXORA|Weather")
	FWeatherPresetData CurrentPreset;

	UPROPERTY(BlueprintAssignable, Category = "NEXORA|Weather")
	FOnWeatherChanged OnWeatherChanged;

	UPROPERTY(BlueprintAssignable, Category = "NEXORA|Weather")
	FOnWeatherBlendUpdated OnWeatherBlendUpdated;

	void Initialize(UNexoraGameClock* InClock);

	void TickWeather(float DeltaRealSeconds);

	/** Request a weather change. The Environment Control Panel and the (later)
	    forecast system call this; the clock never forces weather by itself. */
	UFUNCTION(BlueprintCallable, Category = "NEXORA|Weather")
	void SetWeather(ENexoraWeatherState NewWeather);

	/** Load a preset's values from data/weather-presets.json (parsed at startup into
	    the DataTable / JSON object the manager reads — see TECH-CLOCK-WEATHER.md §4).
	    Returns false when the id is unknown; the current weather is left untouched. */
	UFUNCTION(BlueprintCallable, Category = "NEXORA|Weather")
	bool ApplyPreset(const FString& PresetId);

	/** Clear at night and clear at noon are the same state; the clock picks the
	    lighting preset (clear_day / night_clear / sunrise_clear) for the sky. */
	UFUNCTION(BlueprintPure, Category = "NEXORA|Weather")
	static FString ClockPresetIdForWeather(ENexoraWeatherState Weather, float MinutesSinceMidnight);

private:
	TObjectPtr<UNexoraGameClock> Clock;
	ENexoraWeatherState PreviousWeather = ENexoraWeatherState::Clear;
	FWeatherPresetData PreviousPreset;
	FWeatherPresetData TargetPreset;
	float TransitionElapsed = 0.0f;

	static FWeatherPresetData DefaultPresetFor(ENexoraWeatherState Weather);
	static FWeatherPresetData BlendPresets(const FWeatherPresetData& From, const FWeatherPresetData& To, float Alpha);
};
