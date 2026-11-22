# NEXORA — Tech Note: Seasons Visual Design (Phase 4)

**Unit AK · Queue 7 · Version 1.0 · 2026-11-22**
**Code:** none — design only. The future C++ (a `NexoraSeasonManager` beside `NexoraWeatherManager`) will carry the UNCOMPILED SCAFFOLD header when written; nothing here claims a UE feature works.
**Parent documents:** `NEXORA-MIGRATION-PLAN.md` Part C #6 + Phase 4 · `docs/TECH-CLOCK-WEATHER.md` (clock, weather binding, Environment Control Panel) · `docs/SESSION-08-REPORT.md` (the six-season calendar as simulated) · `data/environment-config.json` (`seasons`, `daylight`, `vegetation_model`) · `data/weather-presets.json` (9 presets) · `docs/GDD-02-RUPSHA-CITY-DISTRICT1.md` (District 1 layout, river, parks)
**Status:** DESIGN ONLY — the UE visual layer for the calendar the headless sim already simulates. First build and first behaviour test happen on the owner's PC (Phase 4).

---

## 1. The Six-Season Calendar (one table, from the sim's data)

The calendar is the Bangladeshi six-season year, as `data/environment-config.json` `seasons` defines it. It tiles the 365-day year exactly once (validator-guarded in `tools/validate_data.py`: "environment seasons tile the 365-day year exactly once"). The UE layer reads the same table — it never re-authors the dates.

| Season | Days of year (0-based) | Length | Rain factor | Temp offset | Daylight shift |
|---|---|---|---|---|---|
| `winter` — Sheet (winter) | 335–364 **and** 0–31 (wraps the year end) | 62 | 0.15 | −6.0 °C | −55 min |
| `spring` — Boshonto (spring) | 32–75 | 44 | 0.45 | −1.0 °C | −10 min |
| `summer` — Grishmo (summer) | 76–135 | 60 | 0.80 | +3.0 °C | +35 min |
| `monsoon` — Borsha (monsoon) | 136–227 | 92 | 2.20 | +0.5 °C | +25 min |
| `autumn` — Shorot (autumn) | 228–273 | 46 | 0.90 | 0.0 °C | −5 min |
| `late_autumn` — Hemonto (late autumn) | 274–334 | 61 | 0.30 | −3.0 °C | −40 min |

**Daylight rule** (`environment-config.json` `daylight`): sunrise 06:00 / sunset 18:00, shifted by the season's `daylight_amplitude_min` — earlier sunrise and later sunset by that many minutes in summer, the reverse in winter. This is a documented SIM MODEL approximation for a near-equatorial delta latitude, not an astronomical calculation; the UE sun binding (§3) uses the same approximation, so the sim and the scene agree by construction.

**Regions:** the calendar is shared by both cities. Shibnagar Town applies the region offsets from the same config (`rain_factor` 1.1, `temp_offset_c` −1.0, `wind_factor` 0.9; Rupsha City is 1.0 / 0.0 / 1.0). A season looks the same in both cities, wetter and a degree cooler in Shibnagar — the visual difference is a matter of degree, never a different calendar.

## 2. What the Sim Already Proves vs What This Doc Designs

| Layer | State |
|---|---|
| Season calendar, per-city weather, rainfall, daylight | **Simulated and test-proven** (Session 08: 370-day acceptance world, monsoon rain > winter rain per city, 20+ trend snapshots). The sim's daily weather draw for Rupsha City *is* the engine's existing draw; Shibnagar evolves by seeded Markov reweighting with the season/region rain factors. |
| Agriculture on the calendar (aman in monsoon, boro in winter, winter vegetables in late autumn) | **Simulated** (Session 08 Unit 05): planting follows `plant_season`, growth from soil moisture + recorded rain, harvest into the Session 04 market. |
| Vegetation cover index per terrain region (forest 0.9 / wetland 0.85 / park 0.8 / farmland 0.7 ceilings) | **Simulated** (Session 08 Unit 07): cover grows toward its class ceiling when rainfall is adequate, declines under drought and recorded construction. |
| UE visuals for the above (sun, sky, rain, foliage, ground) | **Designed here, not built.** §§3–7 are the Phase 4 build instructions for the owner's PC. No visual is claimed to exist. |

The seam between the two layers is one value: **the current season**, derived from `DayNumber` (the game clock's day-of-year) through the §1 table. The weather manager already owns the daily preset; the season manager will own the seasonal multipliers and blends, and will never own the clock or the preset.

## 3. Sun & Daylight Binding

1. **Sunrise/sunset:** the directional light's day arc is bounded by the season-shifted sunrise/sunset from §1 (base 06:00/18:00 ± `daylight_amplitude_min`). Winter days are 110 minutes shorter than the base (sun up ~06:55, down ~17:05); summer days are 70 minutes longer (~05:25 up, ~18:35 down). The clock's `GetDayFraction()` keeps driving the sun's elevation/azimuth (TECH-CLOCK-WEATHER §3); the season only moves the arc's endpoints, so the day-phase table (Night/Dawn/Morning/Afternoon/Evening) never changes.
2. **Sun intensity and colour:** the preset's `lighting.sun_intensity` is the base (Clear 3.0, Rain 0.7, Storm 0.35, from `data/weather-presets.json`); the season multiplies it by a small seasonal tint factor, not a second intensity table: summer ×1.0 warm-white, monsoon ×0.9 (diffused by the season's cloud), winter ×0.95 cool-white. The factor is a lerp target at the season blend (§7), never a hard switch.
3. **Exposure:** `sky_exposure_bias` stays owned by the preset (Rain −0.3, Storm −0.45, Clear 0.0). The season adds at most ±0.1 on top — monsoon −0.1 for the heavier cloud deck, winter +0.05 for the clearer dry air — so a monsoon noon never looks like a winter noon even under the same preset.
4. **Moon/street lights:** unchanged from TECH-CLOCK-WEATHER §3 — they switch on the day-phase boundaries, not the season. Winter evenings simply arrive earlier, because the sun sets earlier.

## 4. Sky, Cloud & Fog per Season

The season does not pick the preset — the weather draw does (Session 08's Markov reweighting, with the season's `rain_factor` scaling the rain/storm weights). The season sets the **sky's seasonal envelope** around whatever preset is active:

| Season | Cloud deck | Fog behaviour | What the player sees |
|---|---|---|---|
| winter | Low (Clear 5% dominates; the 0.15 rain factor starves rain/storm weights) | Morning fog: the `fog` preset (density 0.012) is the season's signature — foggy dawns that burn off by Morning phase | Crisp dry air, pale sun, foggy riverfront at Dawn, long shadows from the low sun |
| spring | Light (10–40% cover) | Rare, thin (0.0008–0.0012) | Bright, mild, the year's clearest light after winter |
| summer | Building (40–65%) | Heat haze at Afternoon (a material/heat-shimmer treatment on roads, not a fog preset) | Harsh noon sun, dusty air, afternoon cloud build-up |
| monsoon | Heavy (85–100% on rain/storm days; the 2.2 rain factor makes rain the modal preset) | Storm fog 0.004, rain fog 0.0025 — the season's sky is a grey deck more often than blue | Grey-green light, frequent rain, the river high and brown (see §5) |
| autumn | Clearing (25–65%) | Light morning mist only | The year's most photogenic season: clear skies, white clouds, still-warm light |
| late_autumn | Low (5–25%) | Morning mist, then clear | Dry, cool, golden light; the year's shortest comfortable evenings |

**Rule:** cloud cover and fog density always come from the active preset's numbers (`cloud_cover_percent`, `fog_density` in `data/weather-presets.json`); the season only changes *which presets the draw favours*. If the scene ever shows monsoon-blue-sky at noon, the bug is in the season's rain-factor wiring, not in the sky.

## 5. Rain, Wetness & Ground

1. **Niagara rain:** spawn rate from the preset's `precipitation.rate` (Rain 0.6, Storm 1.0, none otherwise — TECH-CLOCK-WEATHER §4). The season multiplies the *frequency* of rainy days, never the per-day rate: a monsoon rain day and a winter rain day rain equally hard; monsoon simply has ~15× as many of them (rain factor 2.2 vs 0.15, through the Markov weights).
2. **Wetness:** the Material Parameter Collection `Wetness` (0..1) follows the preset's `wetness_target` (Rain 0.8, Storm 1.0, Fog 0.3, Clear 0.0) and decays over ~30 in-game minutes after rain ends. In monsoon the ground is wet most days by accumulation; in winter it is dry for weeks. No per-season wetness table — the accumulation *is* the seasonal difference.
3. **River and flood visuals:** the river's water level is a visual readout of Session 08's water model (river level vs flood level per city), not a separate animation: normal level in winter/spring, high and fast in monsoon, and the flood-plane treatment (water over the lowest riverside plots) only when the sim's flood mechanism has actually fired for that city. **Honest boundary:** a flood the sim never recorded must never be shown. The visual is a level, not a simulation.
4. **Wind:** foliage wind strength and rain slant read the preset's `wind` (`speed_kmh` / `gusts_kmh`: Storm 38/65, Windy 34/55, Fog 4/7). The season's `wind_factor` (Shibnagar 0.9) scales the same numbers — no separate seasonal wind table.

## 6. Foliage, Crops & Materials

1. **Foliage density and colour** read the sim's vegetation cover index per terrain region (Session 08 Unit 07, ceilings forest 0.9 / wetland 0.85 / park 0.8 / farmland 0.7). The UE layer maps the index to two material treatments only: density (how much of the region's foliage instances are visible) and colour grade (monsoon green → late-autumn dry gold). A region whose index fell under drought shows it; a region the sim never touched shows its seeded baseline. The scene never invents a greener park than the sim's index supports.
2. **Crops** on Shibnagar's agricultural parcels follow the sim's crop cycles: aman standing in monsoon, boro in winter, winter vegetables in late autumn — growth stage from the parcel's recorded growth state, harvest visible as cleared plots when the sim records a harvest. No crop price or yield is shown; the market handles that (Session 04).
3. **Ground materials:** dust in summer (dry, pale roads), mud at the riverside and unpaved plots in monsoon (wetness-driven, §5), leaf litter under park trees in late autumn (a decal/ground-material treatment, not a particle system). All three are material treatments driven by season + wetness, not new geometry.
4. **Snow:** refused in District 1, as TECH-CLOCK-WEATHER §6 already rules — `SetWeather(Snow)` no-ops when `bSnowZone` is false. The `snow` preset exists in data for high-altitude / other-planet regions only (GDD-14). Winter in Rupsha City is dry and cool (−6.0 °C offset, typical day ~25 °C), never white.

## 7. Season Transitions

- **Blend, never pop:** the seasonal tint factor (§3), exposure offset (§3) and foliage grade (§6) lerp over **3 in-game days** centred on the season boundary. The calendar date changes on the boundary day; the look arrives gradually, the way a real season does.
- **Ownership:** the clock owns the date (`DayNumber` → day-of-year → §1 table → current season). The season manager owns only the blend state. The weather manager owns the preset. If the three ever disagree about what season it is, the clock's date is right and the other two are wrong — fix them, never the clock.
- **Time-skip safety:** the presented time-skip at a night boundary (GDD-13, TECH-CLOCK-WEATHER §1) may cross a season boundary. The blend still runs its 3-day lerp from the new date — the player sees the season arriving, not arrived.

## 8. Environment Control Panel Additions

The panel (TECH-CLOCK-WEATHER §5) gains one read-only row and one debug-only control:

- **Read:** current season (id + Bangla/English name), day-of-year, days until the next season, and the active season's rain/temp/daylight factors — all read from the same §1 table the sim uses, so the panel can never disagree with the sim.
- **Write (debug only):** `SetSeason` override, greyed out unless the panel is in debug mode. In shipped play the calendar drives the season and the player cannot summon a monsoon — same rule as weather (§5 of the clock/weather note). The override writes to the season manager, never directly to the sky or materials, and it clears on save/load (the save stores `DayNumber` only; the season re-derives from it).
- **Snow zone toggle:** unchanged — `bSnowZone` stays false for District 1.

## 9. Save / Load & Multiplayer

- **Save:** nothing new is saved. The save stores `DayNumber + MinutesSinceMidnight + CurrentWeather` (TECH-CLOCK-WEATHER §5); the season re-derives from `DayNumber` on load, and the 3-day blend restarts from the loaded date. A save made on the last day of monsoon loads into autumn with the blend in progress — correct behaviour, not a bug.
- **Multiplayer (Phase 9):** the server owns the calendar; the season is server state like the clock, never client state. Clients receive the season with the clock sync. The design maps onto `docs/TECH-MULTIPLAYER.md`'s authority rules (server validates every world-state change); the season manager's Phase 9 work is a replication of two values (season id, blend alpha), not a new system.

## 10. Honest Corrections & Limits

- **TECH-CLOCK-WEATHER §6 said "Seasons arrive with Phase 10 regions, not before." That is superseded.** What it meant — Khulna has no UE-style four seasons — is still true, and this doc does not add any. But the six-season Bangladeshi calendar is real, it was already simulated in Session 08 (before this doc was written), and the Phase 4 visual layer for it is designed here. The §6 sentence is corrected by this note, not deleted from history: the clock/weather note stands as the v1.0 record, and this doc is the amendment.
- **No astronomical accuracy is claimed.** Sunrise/sunset are the sim's documented approximation (06:00/18:00 ± amplitude); the sun arc is a visual treatment, not a solar-position calculation. If the owner wants true solar geometry for Khulna's latitude, that is a new unit with its own data.
- **No snow in District 1, ever, in any season.** Winter here is dry and cool, not white. The snow preset stays reserved for high-altitude / other-planet regions (GDD-14).
- **No new simulation.** Seasons change how the world *looks* and which presets the weather draw favours; they do not change any sim rule. Every number in §1 is the sim's data, quoted, not re-decided.
- **Shibnagar shares the calendar.** The region offsets (rain ×1.1, temp −1.0 °C) are the only difference. If a future city needs its own calendar, that is a data change with its own validation, not a tweak to this doc.

## 11. Phase 4 Acceptance Tests (run on the owner's PC)

1. Set the clock to day 136 (monsoon start): within 3 in-game days the scene shows the monsoon treatment (heavy cloud deck, frequent rain, high river) with no pop at the boundary.
2. Set the clock to day 335 (winter start): foggy Dawn, dry ground, low sun — and `SetWeather(Snow)` still no-ops in District 1.
3. Save on the last day of a season, reload — the season re-derives from `DayNumber` and the blend resumes; the panel's season row matches the sim's `env_weather` row for that day.
4. Run 30 in-game days across a boundary at default time scale: no frame hitches attributable to the season blend (blend cost is two material-parameter lerps, no new draw calls).
5. Shibnagar scene, same date: visibly wetter/cooler treatment than Rupsha City, same season name in the panel.

*End of TECH-SEASONS v1.0 — Unit AK, Queue 7.*
