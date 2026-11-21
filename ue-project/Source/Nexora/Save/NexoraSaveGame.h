// NEXORA — NexoraSaveGame.h
// UNCOMPILED SCAFFOLD — written to UE 5.8 API conventions in a Linux VM without the engine;
// first compile happens on the owner's PC (Phase 1/3).
//
// Unit M: the single-player save object. Design law (GDD-01 §9): one data model from
// the first single-player build to the Phase 9 server — this class serialises the SAME
// schema (data/schema.sql) into a local save slot; it does not invent a parallel model.
// A saved world is a saved *society*: the district's characters, households, ledger and
// properties travel with the slot (as table-shaped JSON payloads, §9's sanctioned local
// store), not just the player's position.
//
// Field-by-field mapping to schema.sql: docs/TECH-SAVE-SYSTEM.md §2.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "NexoraSaveGame.generated.h"

class UNexoraGameClock;
class UNexoraWeatherManager;
enum class ENexoraWeatherState : uint8;

UCLASS()
class NEXORA_API UNexoraSaveGame : public USaveGame
{
	GENERATED_BODY()

public:
	/** The schema version this build writes. Bump ONLY with a migration step in
	 *  MigrateIfNeeded() and a migration note in the PR (GDD-01 §9, §10). */
	static constexpr int32 CurrentSchemaVersion = 1;

	/** save_slots.schema_version / world_state.schema_version — the three must agree;
	 *  in the local store this field is the authoritative copy. */
	UPROPERTY(SaveGame, BlueprintReadWrite, Category = "NEXORA|Save")
	int32 SaveSchemaVersion = CurrentSchemaVersion;

	/** save_slots.slot_label — shown in the slot-select UI. */
	UPROPERTY(SaveGame, BlueprintReadWrite, Category = "NEXORA|Save")
	FString SlotLabel;

	/** Wall-clock moment of the save (slot UI metadata; the in-world timestamp is
	 *  GameMinutes). Mirrors save_slots.updated_at. */
	UPROPERTY(SaveGame, BlueprintReadWrite, Category = "NEXORA|Save")
	FDateTime SavedAtUtc;

	/** save_slots.playtime_seconds. */
	UPROPERTY(SaveGame, BlueprintReadWrite, Category = "NEXORA|Save")
	int64 PlaytimeSeconds = 0;

	/** world_state.game_minutes (and save_slots.game_minutes): total in-game minutes
	 *  since Day 1 00:00. A new world starts at 480 — Day 1, 08:00 (schema default). */
	UPROPERTY(SaveGame, BlueprintReadWrite, Category = "NEXORA|Save")
	int64 GameMinutes = 480;

	/** world_state.time_scale — game-minutes per real minute (design setting, Unit E). */
	UPROPERTY(SaveGame, BlueprintReadWrite, Category = "NEXORA|Save")
	float TimeScale = 60.0f;

	/** world_state.weather_preset — a data/weather-presets.json preset id, e.g. "clear_day". */
	UPROPERTY(SaveGame, BlueprintReadWrite, Category = "NEXORA|Save")
	FString WeatherPresetId = TEXT("clear_day");

	/** save_slots.character_id — the played character's UUID, as text (the local store
	 *  has no native UUID column type; Phase 9's PostgreSQL keeps the real UUID). */
	UPROPERTY(SaveGame, BlueprintReadWrite, Category = "NEXORA|Save")
	FString PlayerCharacterId;

	/** Runtime-only: the player's position/rotation at save time. Deliberately has NO
	 *  schema column — the database models the society, not render state; in Phase 9
	 *  this becomes session state, never a ledger/property fact. */
	UPROPERTY(SaveGame, BlueprintReadWrite, Category = "NEXORA|Save")
	FTransform PlayerTransform;

	/** characters.balance_cached for the played character — a CACHE for the slot UI.
	 *  The truth is the economy_ledger rows inside TablePayloads (GDD-01 §8): on load,
	 *  if cache and ledger sum disagree, the ledger wins and this field is rebuilt. */
	UPROPERTY(SaveGame, BlueprintReadWrite, Category = "NEXORA|Save")
	int64 PlayerBalanceCachedNCr = 0;

	/** The society payload: schema table name → JSON array of that table's rows
	 *  (characters, households, relationships, economy_ledger, properties,
	 *  mission_progress, achievements, …). Table-shaped on purpose: the Phase 5 store
	 *  choice (SQLite file vs JSON chunks, GDD-01 §9) can change without the model
	 *  changing, and save_slots.payload_ref points at wherever the blob lives. */
	UPROPERTY(SaveGame, BlueprintReadWrite, Category = "NEXORA|Save")
	TMap<FString, FString> TablePayloads;

	/** Snapshot the world clock + weather into this save (call before SaveGameToSlot). */
	void CaptureWorldState(const UNexoraGameClock* Clock, const UNexoraWeatherManager* Weather);

	/** Restore the world clock + weather from this save (call after LoadGameFromSlot
	 *  and MigrateIfNeeded). The weather manager re-derives the exact time-of-day
	 *  preset from the restored clock (Unit E), so the save carries the weather
	 *  *state* faithfully and the preset id is recomputed, never trusted blindly. */
	void ApplyWorldState(UNexoraGameClock* Clock, UNexoraWeatherManager* Weather) const;

	/** Forward-only migration (GDD-01 §9). Returns false when the save cannot be
	 *  loaded by this build: newer than CurrentSchemaVersion, or older with no
	 *  migration step written for it. Never silently stamps an old save current. */
	bool MigrateIfNeeded();

	/** Slot names for UGameplayStatics::SaveGameToSlot / LoadGameFromSlot. */
	static FString MakeSlotName(int32 SlotIndex);

private:
	static ENexoraWeatherState WeatherStateForPresetId(const FString& PresetId);
};
