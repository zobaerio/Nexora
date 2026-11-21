# NEXORA — Tech Note: Game Clock & Weather

**Unit E · Version 1.0 · 2026-11-20**
**Code:** `ue-project/Source/Nexora/Systems/NexoraGameClock.{h,cpp}`, `NexoraWeatherManager.{h,cpp}`
**Parent documents:** `NEXORA-MIGRATION-PLAN.md` Phase 4 · `docs/GDD-01-LIFE-AND-DATA-MODEL.md` §4 (daily tick) · `data/weather-presets.json` (design data)
**Status:** UNCOMPILED SCAFFOLD — written in a Linux VM without the engine. First compile and first behaviour test happen on the owner's PC (Phase 1/3 for the clock wiring, Phase 4 for the full weather binding). Nothing in this note is a claim that the systems work.

---

## 1. The Day-Phase Table (one table, used everywhere)

| Phase | Hours | What it means for the game |
|---|---|---|
| Night | 00:00–05:00, 20:00–24:00 | Streets quiet, shops closed, NPCs home/sleeping, street lights on. Life-sim sleep happens here. |
| Dawn | 05:00–07:00 | First light, morning prayers/tea stalls open, fishermen and early workers out. |
| Morning | 07:00–12:00 | Workday starts, school in session, market busy. |
| Afternoon | 12:00–17:00 | Peak heat, work continues, school ends, market second rush. |
| Evening | 17:00–20:00 | Golden hour, riverfront promenade busy, leisure anchors active, shops close. |

The table lives in exactly one place: `UNexoraGameClock::PhaseForMinutes`. The lighting artist, the schedule system and the life sim all read `CurrentPhase` — nobody re-derives the boundaries. If the owner wants different boundaries, this function is the only edit.

**Time scale:** default `TimeScale = 60` — one in-game minute per real second, one full day per 24 real minutes. The owner changes it from the Environment Control Panel; the accelerated life-sim test (Phase 6 exit criteria: 30 in-game days) raises it. The simulation rules never depend on the scale: one in-game day is always one simulation day (GDD-01 §4).

**Time-skip rule:** the clock never jumps silently. Stage changes and sleep use the presented time-skip at a night boundary (GDD-01 §3). `SetTimeOfDay` exists for the editor/panel and for tests, not for gameplay shortcuts.

## 2. What the Clock Drives

| Consumer | How it reads the clock | Phase |
|---|---|---|
| Directional light / sun position | `GetDayFraction()` (0..1) → sun elevation/azimuth (§3) | 4 |
| Sky Atmosphere + volumetric clouds | Phase + weather preset (cloud cover, sun intensity) | 4 |
| NPC schedules | Phase boundaries + work hours in `data/npc-schedules.json` | 6 |
| Life-sim daily tick | `OnNewDay` delegate → GDD-01 §4 steps 1–5 | 6 |
| Economy daily tick | `OnNewDay` → wages in, rent/food/transport out (GDD-03) | 6 |
| Aging / stage transitions | `DayNumber` + `born_at_game_time` → age (derived, GDD-01 §3) | 7 |
| HUD clock readout | `GetHour()` / `GetMinute()` — must match `GameClock` exactly (Phase 3 test) | 3 |

## 3. Binding the Clock to Sky Atmosphere (Phase 4, on the owner's PC)

1. **Directional Light (sun):** rotation driven every frame from `GetDayFraction()` — elevation = `sin(day_fraction * 2π)`, azimuth from the same fraction. At night the sun is below the horizon and a dim moon light takes over; do not rotate the sun under the map and call it night — the sky would still be lit.
2. **Sky Atmosphere + Sky Light:** default UE Sky Atmosphere, with the sun's intensity multiplied by the weather preset's `SunIntensity` (Clear 3.0, Rain 0.7, Storm 0.3 — from `data/weather-presets.json`).
3. **Volumetric clouds:** cloud cover from `CurrentPreset.CloudCoverPercent` (Clear 5%, Rain 85%, Storm 100%).
4. **Exposure:** sky exposure bias from the preset (`lighting.sky_exposure_bias`: Rain −0.3). Do not bake exposure per time of day — the preset owns it, the clock owns the sun.
5. **Street lights / window lights:** switch on `OnDayPhaseChanged` to Evening, off on Dawn. Emissive materials, not a second lighting pass.

## 4. Binding Weather to Niagara, Fog and Materials (Phase 4)

| Preset value | Engine binding |
|---|---|
| `precipitation.rate` / `type` | Niagara rain system around the camera (spawn rate = rate; Storm 1.0, Rain 0.6, none otherwise). Snow uses its own Niagara system — only in snow zones. |
| `fog_density` | Exponential Height Fog density, lerped during transitions. Storm 0.004, Fog 0.008. |
| `wetness_target` | Material Parameter Collection `Wetness` (0..1) — road and pavement materials blend to a wet look; Rain 0.8, Storm 1.0. Wetness decays back to 0 over ~30 in-game minutes after rain ends (the manager's next transition handles it). |
| `wind.speed_kmh` / `gusts_kmh` | Foliage wind strength, flag/cloth motion, and the Niagara rain slant. |
| `gameplay_effects` | Read by the schedule system (Phase 6): `npc_cover_seeking` bends leisure anchors indoors, `taxi_demand_up` raises taxi fares/availability, `road_grip_down` lowers vehicle grip, `outdoor_work_halted` pauses construction-site work. |

**Transitions:** `TransitionDurationSeconds = 8` by default. All numeric values lerp; gameplay effects switch with the target preset, never mid-blend. A storm never arrives in one frame.

**Data pipeline (Phase 4 TODO, in `NexoraWeatherManager::ApplyPreset`):** `data/weather-presets.json` is loaded at startup into a `TMap<FString, FWeatherPresetData>`; the hardcoded `DefaultPresetFor` fallbacks are deleted once the loader is verified against the JSON. The JSON is the design source — the C++ must never become a second copy of the numbers.

## 5. Environment Control Panel — Data Interface

The panel (master plan Part C #5) is a UMG widget that talks to exactly two objects:

- **Clock:** reads `DayNumber`, `MinutesSinceMidnight`, `CurrentPhase`, `TimeScale`; writes `SetTimeOfDay`, `SetTimeScale`, `SetPaused`.
- **Weather:** reads `CurrentWeather`, `CurrentPreset`, `TransitionAlpha`; writes `SetWeather` / `ApplyPreset`. Snow is greyed out unless `bSnowZone` is true.

The panel is a **debug/design tool first** (Phase 4) and a player feature later: in shipped play, weather is forecast-driven and the player cannot summon a storm. The panel never writes directly to the sky, fog or materials — it writes to the manager, and the manager drives the scene. That one indirection is what keeps save/load and multiplayer honest: the save stores `DayNumber + MinutesSinceMidnight + CurrentWeather`, and loading restores exactly those three values.

## 6. What Is Deliberately Not Here

- **Forecasting / weather simulation:** Phase 4 weather is set (by the panel, by scripted mission weather, or by a simple random roll). A real forecast model with fronts and seasons is a later phase; the manager's `SetWeather` API is the seam it will use.
- **Seasons:** Khulna's climate has no UE-style four seasons; `data/weather-presets.json` temperatures (typical day 31 °C clear, 27 °C rain) are the monsoon-cycle model. Seasons arrive with Phase 10 regions, not before.
- **Snow in District 1:** refused by design (`SetWeather(Snow)` no-ops when `bSnowZone` is false). The snow preset exists in data for high-altitude / other-planet regions only.

## 7. Phase 4 Acceptance Tests (run on the owner's PC)

1. Clock runs 24 in-game hours in 24 real minutes at default scale; HUD readout matches.
2. Sun position at 09:00 matches the owner spec reference (bright daylight, `clear_day` preset).
3. Rain transition takes ~8 s; wetness reaches 0.8; NPCs seek cover; taxi demand rises.
4. Save at 17:30 in Rain, reload — clock, phase and weather are identical.
5. Phase change Night→Dawn fires exactly once per boundary; no double-fire at midnight.

*End of TECH-CLOCK-WEATHER v1.0.*
