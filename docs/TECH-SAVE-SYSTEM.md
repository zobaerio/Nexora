# NEXORA — Tech Note: Save System

**Unit M · Version 1.0 · 2026-11-21**
**Code:** `ue-project/Source/Nexora/Save/NexoraSaveGame.{h,cpp}`
**Parent documents:** `docs/GDD-01-LIFE-AND-DATA-MODEL.md` §8 (ledger) + §9 (save-game mapping) · `data/schema.sql` (`save_slots`, `world_state`) · `docs/TECH-CLOCK-WEATHER.md` (the runtime the save snapshots)
**Status:** UNCOMPILED SCAFFOLD — written in a Linux VM without the engine. First compile and every check in §6 happen on the owner's PC (Phase 5, when saving first ships). Nothing in this note is a claim that saving works.

---

## 1. The Rule Being Implemented

GDD-01 §9, in one paragraph: **one data model, two stores.** Single-player phases serialise the same schema (`data/schema.sql`) into a local save slot; Phase 9 moves the same tables behind a server. A saved world is a saved *society* — the district's characters, households, relationships, ledger and properties all travel with the slot. `UNexoraSaveGame` is the UE-side container for that: slot metadata + world clock/weather + the played character's quick fields + one JSON payload per schema table. It invents no fields the schema does not have, except the two runtime-only fields declared as such in §2.

## 2. Field Mapping — USaveGame ↔ schema.sql

| USaveGame field | Schema source | Notes |
|---|---|---|
| `SaveSchemaVersion` | `save_slots.schema_version`, `world_state.schema_version` | The three must agree; locally, the save file's copy is authoritative |
| `SlotLabel` | `save_slots.slot_label` | Slot-select UI text |
| `SavedAtUtc` | `save_slots.updated_at` | Wall-clock metadata; the *in-world* timestamp is `GameMinutes` |
| `PlaytimeSeconds` | `save_slots.playtime_seconds` | Accumulated by the GameMode (Phase 5 wiring, §5) |
| `GameMinutes` | `world_state.game_minutes` = `save_slots.game_minutes` | Total in-game minutes since Day 1 00:00; new world = 480 (Day 1, 08:00) |
| `TimeScale` | `world_state.time_scale` | Design setting (Unit E), restored on load |
| `WeatherPresetId` | `world_state.weather_preset` | A `data/weather-presets.json` id, e.g. `clear_day` |
| `PlayerCharacterId` | `save_slots.character_id` | UUID as text — the local store has no UUID type; PostgreSQL keeps the real UUID in Phase 9 |
| `PlayerBalanceCachedNCr` | `characters.balance_cached` | **Cache only.** The truth is the `economy_ledger` payload (GDD-01 §8); on disagreement the ledger wins and the cache is rebuilt |
| `TablePayloads` (map) | Every other schema table, by name | Table name → JSON array of rows. `save_slots.payload_ref` is where this blob lives in the server model |
| `PlayerTransform` | **— no schema column, deliberately** | Runtime render state, not a society fact. In Phase 9 it becomes session state; it must never be treated as ledger/property truth |

## 3. Capture / Apply — the Clock and Weather Round-Trip

- `CaptureWorldState` recomposes `world_state.game_minutes` from the clock's split representation (`(DayNumber − 1) × 1440 + MinutesSinceMidnight`) — this is the only place that conversion happens, so the two representations cannot drift apart.
- `ApplyWorldState` reverses it: day and time-of-day back into `UNexoraGameClock`, `SetTimeScale` restores the speed.
- **Default-time note:** the clock object's compiled-in default is 09:00 (the owner spec's reference hour), but a *world* starts at 08:00 (`world_state` default 480). On new game and on load, the world state wins — the clock is always initialised from the save/world row, never from the object default. The default only exists so a bare clock in an editor test level shows a sane morning.
- **Weather:** the save stores the preset id (the schema's truth), but apply restores the weather *state* (`Clear/Cloudy/Rain/Storm/Fog/Wind/Snow`) and lets `UNexoraWeatherManager` re-derive the exact time-of-day preset via its own clock logic (Unit E). Reason: `sunrise_clear` at 15:00 is a contradiction; the state + restored clock cannot produce one. The three clear-variant preset ids all map to `Clear` in `WeatherStateForPresetId` — that lossy step is intentional and documented here, not an accident.

## 4. Versioning & Migration

- Every save is stamped with `CurrentSchemaVersion` (v1 today — the schema's own `DEFAULT 1`).
- Migrations are **forward-only** (GDD-01 §9): a migration step transforms an older payload into the next version's shape and stamps it; steps ship with the game and are added to `MigrateIfNeeded()` one block per version hop, each with a migration note in its PR (GDD-01 §10).
- A save **newer** than the build is refused (`MigrateIfNeeded` returns false): loading it would silently drop fields this build does not know.
- A save **older with no written step** is also refused — never silently stamped current. Today that case cannot occur (v1 is the first schema); the refusal exists so the first real version bump has to be a deliberate act.
- The load path is: `LoadGameFromSlot` → `MigrateIfNeeded()` (false = show "save incompatible", never crash, never overwrite) → `ApplyWorldState` → society payload handed to the Phase 5 store layer.

## 5. What This Unit Deliberately Does Not Do

- **No store implementation.** GDD-01 §9 leaves SQLite-file vs JSON-chunks inside the save game as a Phase 5 implementation choice. This scaffold carries table-shaped JSON payloads so either store can be adopted without a model change — it does not pick the winner.
- **No slot UI, no autosave policy, no GameMode wiring** — Phase 5. `MakeSlotName` exists so that wiring has exactly one naming convention to use.
- **No server anything.** Phase 9 replaces the local store with PostgreSQL behind the server (the only writer of ledger + property, GDD-01 §8); this class is the client-side shape that era inherits, not a multiplayer save.

## 6. Phase 5 Acceptance Checks (owner's PC, when saving first ships)

| # | Check | Pass condition |
|---|---|---|
| 1 | Save mid-day, quit to desktop, load | Clock shows the same day + time (±1 game-minute); time scale restored |
| 2 | Save in rain, load | Weather state is Rain; the exact preset fits the restored time of day |
| 3 | Save, move the character, load | Character returns to the saved transform |
| 4 | Spend money, save, load | Balance shown = ledger sum inside the payload (cache rebuilt if edited by hand) |
| 5 | Hand-edit `SaveSchemaVersion` to 99, load | Clean "save incompatible" refusal — no crash, save file untouched |
| 6 | Two slots, alternate saves | Neither slot's society payload bleeds into the other |

*End of TECH-SAVE-SYSTEM v1.0. Changes happen by PR; a schema version bump without a migration step + note fails review by definition (§4).*
