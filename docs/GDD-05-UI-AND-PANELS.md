# NEXORA — GDD-05: UI & Panels Design

**Unit N · Version 1.0 · 2026-11-21**
**Parent documents:** `NEXORA-MIGRATION-PLAN.md` Part C #5 (Environment Control Panel), Phases 3–6 · `docs/GDD-01-LIFE-AND-DATA-MODEL.md` §1 (profile card), §2.2 (goals), §4 (needs) · `docs/GDD-04-MISSIONS-AND-PROGRESSION.md` + `data/missions.json` (tracker data) · `docs/TECH-CLOCK-WEATHER.md` §2, §5 (clock readouts, panel data interface) · `docs/TECH-MOVEMENT.md` + `ue-project/Config/DefaultInput.ini` (input actions)
**Status:** DESIGN ONLY. No UMG widget exists yet; nothing in this document is a claim that any screen is built or working. Widget classes below are the implementation contract for the phase that builds them (HUD basics Phase 3, panels Phase 4–6 as noted per screen).

> **Design law:** the UI shows the simulation's real numbers or it shows nothing. Every value on every screen names the system that owns it (clock, ledger, goals, schedule). No decorative stats, no fake notifications, no placeholder panels presented as features. Where a system is not designed yet, this document says so in §10 instead of inventing a screen for it.

---

## 1. UI Principles

1. **Quiet HUD.** During free roam the screen carries only what a person would glance at: time, money, current objective, urgent needs. Everything else is one keypress away in a panel, never stacked on the play screen.
2. **One source per value.** The HUD clock reads `UNexoraGameClock` (`GetHour()`/`GetMinute()`); it must match the world exactly (TECH-CLOCK-WEATHER §7 test 1). The balance reads the ledger-derived cache (`characters.balance_cached`, GDD-01 §8) — the UI never computes money itself.
3. **Panels pause nothing by default.** Life continues while the player reads a profile or checks a goal (the world is alive; GDD-04 free-roam rules). Only the pause menu (§7) stops the clock, via `SetPaused` on the panel interface, not by freezing the engine tick globally — multiplayer (Phase 9) has no pause at all, and the design must not grow to depend on one.
4. **Same card everywhere.** A character is always presented as the GDD-01 §1 card — profile screen, NPC inspect, dialogue header. One shape, learned once.
5. **Keyboard/gamepad parity.** Every panel is fully navigable by gamepad; every action in §9 has both bindings. Mouse is an addition, never a requirement.

## 2. Screen Inventory & Flow

```
Boot → Main Menu ──→ Character Select ──→ (new life) Character Creation ──→ Gameplay (HUD)
              │              │                                                    │
              ├──→ Settings  └──→ (existing life) ────────────────────────────────┤
              └──→ Quit                                                          │
        Gameplay ──→ Pause Menu (Esc / IA_Pause) ──→ Resume / Settings / Save / Main Menu
        Gameplay ──→ Profile Panel (Tab)      ──→ Goals / Skills / Relations / Memories tabs
        Gameplay ──→ Mission Log (M)          ──→ Level overview / mission detail
        Gameplay ──→ Environment Control Panel (F10, debug builds & design mode only in v1)
```

| Screen | Opens with | Phase that builds it |
|---|---|---|
| Main Menu | boot | 3 (minimal) |
| Character Select / Creation | Main Menu | 6 (creation is a life-sim feature, not a menu feature) |
| HUD | gameplay | 3 |
| Pause Menu | `IA_Pause` | 3 |
| Mission Log | `M` (new binding, §9) | 3 (tracker) / 6 (full log) |
| Profile Panel | `Tab` (new binding, §9) | 6 |
| Environment Control Panel | `F10` | 4 |
| Settings | Main Menu / Pause | 3 |

## 3. HUD Layout (free roam)

Wireframe (1920×1080 reference; all elements anchored, safe-margin 40 px):

```
┌──────────────────────────────────────────────────────────────────┐
│ [Day 12 · 07:42 · Morning]                          [☰ objective]│
│                                          Level 1 · First Steps   │
│                                          ▸ Walk to your apartment│
│                                                                  │
│                                                                  │
│                                                                  │
│                        (play space — empty)                      │
│                                                                  │
│                                                                  │
│        [needs: ●rest ●food ○social ●security]                    │
│ [Balance: 25,000 NCr]                    [F — Enter shop]        │
└──────────────────────────────────────────────────────────────────┘
```

| Element | Content | Data source | Rules |
|---|---|---|---|
| Clock chip (top-left) | `Day N · HH:MM · Phase` | `UNexoraGameClock` (`DayNumber`, `GetHour/GetMinute`, `CurrentPhase`) | Phase names exactly as TECH-CLOCK-WEATHER §1 (Night/Dawn/Morning/Afternoon/Evening). Updates on minute change, not per frame. |
| Objective tracker (top-right) | Current level + active mission title + next objective line | `data/missions.json` via mission state (GDD-04) | Shows ONE mission (the tracked one). No tracker in free roam if the player untracks — an empty corner is correct, not a bug. Collapses to the level line after 10 s idle; expands on objective change. |
| Needs strip (bottom-left, above balance) | Four dots: rest, food, social, security | GDD-01 §4 needs | Filled = satisfied, hollow = deficit generating a want (§2.2). No numbers on the HUD; numbers live in the Profile Panel. A dot pulses once when it crosses into deficit — never repeatedly. |
| Balance (bottom-left) | `Balance: N NCr` | Ledger cache (GDD-01 §8) | Animates a ± delta chip on change (wage in, rent out — the economy tick is visible, not silent). Currency name "Nexora Credits", short form `NCr` as in `data/professions.json`. |
| Interaction prompt (bottom-centre-right) | `[F] — <verb> <target>` | `IA_Interact` context (Phase 3) | Appears only when an interactable is in range; verb comes from the target (Enter shop, Sit, Talk, Enter vehicle). Never a bare "F". |
| Weather glyph (in clock chip) | Current preset icon | `UNexoraWeatherManager.CurrentWeather` | One glyph, no forecast text — forecasting is not a designed system (TECH-CLOCK-WEATHER §6) and the HUD does not pretend otherwise. |

**Deliberately absent from the HUD:** minimap (no map system is designed yet — §10), health bars (no combat/damage model is designed), XP bars (progression is levels + skills, GDD-04/GDD-01 §2.1 — skills show in the Profile Panel, not as a grind bar), chat (Phase 9).

## 4. Character Profile Screen

The profile panel is the GDD-01 §1 canonical card, expanded. Header block — field for field the owner's example, in the owner's order:

```
┌─ Profile ──────────────────────────────────────────────┐
│ [MetaHuman portrait]   Zobaer Hasan          @zobaerio │
│                        Civil Engineer · Tier 3         │
│                        Nexora Central City (Rupsha D1) │
│                        Middle Class (derived)          │
│                        Balance: 25,000 NCr             │
│                        Age 27 · Young Adult            │
├─ Tabs: [Overview] [Goals] [Skills] [Relations] [Memories] ┤
└────────────────────────────────────────────────────────┘
```

| Card field | Source (GDD-01 §1 mapping) | Display rule |
|---|---|---|
| Name | `characters.display_name` | — |
| Username | `accounts.username` | `@` is display-only. |
| Profession | current `employments` row + profession tier | Tier from `data/professions.json` progression (e.g. "Tier 3"). |
| Residence | `characters.residence_city` + household property | City on the card; the home property (name, zone — GDD-02 ids) on Overview. |
| Economic Class | derived label (§7) | Always shown with "(derived)" in the tooltip/detail — it is a computed game label, never a stored fact, and never a statement about a real person (GDD-01 §7 framing). |
| Balance | ledger cache | Same value as the HUD, to the credit. A "Ledger" sub-view lists recent rows (§8: the ledger is the truth — the player can audit any number the UI shows). |
| Age / life stage | derived from `born_at_game_time` + clock (§3) | Stage names from §3 (Child/Teen/Young Adult/Adult/Elder as defined there). |

**Tabs:**
- **Overview:** home property, household members (each a mini-card, click → their profile if Full/Scheduled tier), current schedule block (activity + location from the character's schedule template, e.g. `work @ workplace`), needs with numbers.
- **Goals:** the goal stack (§2.2) — 1 life goal, up to 2 stage goals, current wants. Progress shown only where the underlying data is countable (savings target vs ledger balance; skill target vs `character_skills`). No invented percentage for narrative goals.
- **Skills:** `character_skills` rows — level 0–100 + experience; profession-gating skills highlighted.
- **Relations:** relationship rows (§6.2 scores: trust/affection/respect as directed edges) with kinship label; sorted by strongest |score|.
- **Memories:** episodic memory list (§2.3) — the player's own character's `character_memories`, newest first, with emotional weight shown as a tone word, not a raw number. For NPC profiles this tab shows only what the *player character* could know (memories involving the player) — the UI does not leak simulation internals.

**NPC inspect** uses the same panel, read-only, minus account fields (no username, no ledger sub-view; balance shown only for characters the player has a financial relationship with — employer, tenant, debtor — via semantic memory flags, §2.3).

**Credentials on the profile panel (Unit DR · Queue 18 · 2026-11-23)**

**Status:** DESIGN ONLY. This subsection answers the question DN left open: DN states a lost credential stays valid, but no panel shows that — a player reading the character panel cannot tell a lost credential from a revoked one. It adds no sim code and no new data: the panel reads two records that already exist — the `certifications` row (the qualification) and the `lost_items` row for its document (the paper) — and displays what they say. Where a label or an icon state would need a wording no source gives, the wording is this unit's decision, labelled as such.

**Where — a Credentials block on the Skills tab.** Credentials are qualifications that gate professions (GDD-11: the college credential gates the four credential professions at hiring; the school-leaving certificate is the completion record) — so they live on the Skills tab, which already highlights profession-gating skills. Each `certifications` row for the character is one credential row: the document name from `data/documents.json` (`school_leaving_certificate` → "School-leaving certificate"; `college_credential` → "College credential" + the programme, e.g. "College credential — Engineering"), the issuing institution (`certifications.institution_id` → the `education-health-config.json` institution name: District School / District College / Shibnagar Primary School) and the issued month. A character with no certifications row shows no block at all — the panel never shows an empty Credentials block, and never shows a credential the character does not hold.

**The row states.** The row's status chip is read from the document inventory row for that certification (`inventory_items` row with `item_ref` = the document id and `state.certification_id` = the certification — the DN seeding shape), joined to its `lost_items` row where one stands:

| Document row | Chip (this unit's wording) | Icon state |
|---|---|---|
| No `lost_items` row, or the row is `returned` | VALID — no chip, the plain row | The document icon, full colour |
| `lost_items` status `lost` | "Paper lost — credential valid" | The document icon with a dashed outline + a small "lost" badge; never a red X |
| `lost_items` status `found` | "Found — awaiting hand-back" | The document icon with a dashed outline + a small "found" badge |

The chip wording is this unit's decision: "Paper lost — credential valid" says both facts in one line — the paper is gone, the qualification stands. The dashed outline is the "paper" marker (the paper is missing); the icon itself is never struck through or greyed out, because the credential is not gone.

**What the panel must NOT claim.** Never "revoked": a lost credential is not a revoked one (DN's rule — the `certifications` row stands whatever happens to the paper, and `has_credential()` reads `education_records`, never inventory). Never "invalid", "expired", or "missing": the credential is not missing — the paper is — and no source gives any credential an expiry. Never hide the credential while its paper is lost: hiding it would read as revocation to the player. Never show a price or a fee for the paper: documents are unpriced (`prices.json` `documents`, 0 = unpriced, not free), and the replacement fee is a Phase 6 decision — the panel shows no number for it. Never show the lost credential as a skill: the Skills tab lists `character_skills` rows and the Credentials block is a separate block on the same tab, so a lost paper never reads as a lost skill.

**The recovery path.** While the chip reads "Paper lost — credential valid", the row carries one action line: "Find it — a favour can be raised for this paper." The §3.1 find-a-lost-item favour is the recovery path (the favour's parameters are the `lost_items` row; its completion is the `returned` write), and the panel points at it rather than inventing a replacement flow. When the row reaches `returned`, the chip clears and the row returns to VALID with no marker — the recovery is visible, not silent.

**NPC inspect.** The same block, the same rules: NPC inspect uses the same panel read-only (§4), and the Credentials block shows for an NPC exactly as it shows for the player — the Skills tab is not restricted the way the Memories tab is (Memories shows only what the player could know; Skills shows the character's skills, and credentials are the same kind of fact). Account fields stay excluded for NPCs per §4 (no username, no ledger sub-view); the credential block carries no account field, so nothing is withheld from it.

**What this design does not do.** It does not change the credential: the panel reads the `certifications` row and never writes it. It does not add a panel field for the paper's location: the `lost_zone` / `lost_anchor` are the find place (DP), and the panel does not direct the player there — the favour does. It does not cover the property deed or the business licence: those are documents too, but they are not credentials (no `certifications` row stands behind them), so they have no Credentials-block row; a lost deed or licence is a lost document, not a lost credential, and its display is a later unit's job if the panel ever lists a character's papers.

## 5. Environment Control Panel

Per TECH-CLOCK-WEATHER §5, the panel talks to exactly two objects and nothing else. It never writes to sky, fog or materials directly.

Wireframe:

```
┌─ Environment (design/debug) ────────────────┐
│ TIME                                        │
│  Day 12 · 07:42 · Morning                   │
│  [Set time:  --:-- ] [Apply]                │
│  Time scale: (•) 0  ( ) 1× (•) 60× ( ) 600× │
│  [ ] Paused                                 │
│ WEATHER                                     │
│  Current: Rain (transition 62%)             │
│  [Clear Day][Sunrise][Night][Cloudy][Rain]  │
│  [Storm][Fog][Windy][Snow — locked]         │
│  Snow zone: No                              │
└─────────────────────────────────────────────┘
```

| Control | Reads | Writes | Rule |
|---|---|---|---|
| Time readout | `DayNumber`, `MinutesSinceMidnight`, `CurrentPhase` | — | Same formatting as the HUD clock chip. |
| Set time | — | `SetTimeOfDay` | Editor/panel use only (TECH-CLOCK-WEATHER §1 time-skip rule — gameplay uses presented time-skips, never this). |
| Time scale | `TimeScale` | `SetTimeScale` | Presets 0/1/60/600; free entry allowed in design mode. 60 = default (1 game-minute per real second). |
| Paused | — | `SetPaused` | Panel-level pause of the clock. |
| Weather buttons | `CurrentWeather`, `CurrentPreset`, `TransitionAlpha` | `SetWeather` / `ApplyPreset` | Buttons are exactly the 9 preset ids in `data/weather-presets.json`: `clear_day`, `sunrise_clear`, `night_clear`, `cloudy`, `rain`, `storm`, `fog`, `windy`, `snow`. |
| Snow button | `bSnowZone` | — | Greyed out and unclickable unless `bSnowZone` is true — District 1 refuses snow by design (TECH-CLOCK-WEATHER §6); the button shows *why* ("Snow zone: No") instead of failing silently. |
| Transition readout | `TransitionAlpha` | — | Shows blend % so the designer can see the ~8 s transition, not a hard cut. |

**Availability:** v1 is a debug/design tool (Phase 4, `F10`, development builds and an explicit design mode). In shipped play the panel is closed: weather is forecast/script-driven and the player cannot summon a storm (TECH-CLOCK-WEATHER §5). If a player-facing "director mode" is ever wanted, it is a separate design decision — this document does not grant it.

## 6. Mission Log

- **Level overview:** the 8 levels from GDD-04 / `data/missions.json` (Level 1 "A New Beginning" → Level 8 "Space Explorer"; names 2–7 proposed, owner confirms — the log displays whatever `missions.json` carries, so a rename is a data edit, not a UI change).
- **Mission detail:** objectives checklist (state from mission progress), rewards (credits, reputation scope/amount, unlocks — exactly the `rewards`/`unlocks` fields of `missions.json`), zone refs rendered as district names (GDD-02 zone ids → display names).
- **Track/untrack** sets the HUD tracker (§3). Side missions (GDD-04 §3) list separately, never gate levels, and are labelled as such.
- **Achievements:** account-level list (GDD-04 §5) — shown here because they survive character death (GDD-01 §1); earned state from the account, not the character.

## 7. Main Menu & Pause Flow

**Main Menu:** Continue (most recent save slot — Unit M `save_slots`), Select Character, New Life, Settings, Quit. Background: the Phase 1 environment scene, live clock running (the menu is a window into the world, not a separate world). No "Multiplayer" entry until Phase 9 designs it — a greyed-out fake entry is exactly the placeholder dishonesty the owner forbids; the menu simply has five entries.

**Pause Menu** (`IA_Pause` / Esc / Start): Resume, Profile, Mission Log, Settings, Save Game, Load Game, Main Menu, Quit. Opening pause in single-player calls the clock's `SetPaused` (life-sim phases only); in Phase 9 multiplayer the same menu opens without pausing anything.

**Save/Load screens:** slot list from Unit M's design (`docs/TECH-SAVE-SYSTEM.md`) — slot name, character card mini-view, Day/time, weather preset; overwrite requires confirm; a save from a newer version is shown but refused by the migration rule, and the UI says so in words.

## 8. Settings

| Group | Settings | Notes |
|---|---|---|
| Graphics | Scalability group (Low/Medium/High/Epic/Cinematic), resolution, fullscreen mode | Groups are the Phase 1 build sheet's capture groups — the same names the performance sheet uses, so a perf report and a settings screen speak one language. |
| Display | Brightness, HUD scale, HUD opacity | HUD scale reflows §3 anchors; nothing may leave the safe margin. |
| Audio | Master / Music / SFX / Voice volumes | Sliders only — no audio system is designed yet beyond volume routing; no fake "audio profiles". |
| Controls | Look sensitivity (maps to the character's look multiplier), invert Y, gamepad deadzone, remapping | Remapping edits the Enhanced Input mapping context at runtime (user mapping), consistent with `DefaultInput.ini`'s Enhanced-Input-only rule. |
| Gameplay | Time scale default (single-player), needs-strip on/off, objective auto-track on/off | Time scale here sets the *starting* scale; the Environment Panel changes it live in design mode. |

Settings persist per account (they survive character death, GDD-01 §1), stored with the account settings, not in the character save.

## 9. Input Additions (beyond `DefaultInput.ini`)

Existing actions (`IA_Move`, `IA_Look`, `IA_Run`, `IA_Jump`, `IA_Interact`, `IA_Pause`, `IA_TimeSkip`) are unchanged. This design adds three, to be created as assets beside the existing ones under `/Game/Nexora/Input/` when the HUD is built:

| Action | Keyboard | Gamepad | Opens |
|---|---|---|---|
| `IA_Profile` (bool) | Tab | View/Back | Profile Panel |
| `IA_MissionLog` (bool) | M | D-pad Left (hold) | Mission Log |
| `IA_EnvPanel` (bool) | F10 | — (design mode only) | Environment Control Panel |

Panel navigation: standard UMG focus navigation; Esc closes the topmost panel before it ever opens Pause (one Esc = one step back — the flow rule for the whole UI).

## 10. Widget Class List (UMG implementation contract)

Blueprint widgets (`WBP_`) own layout; the data-facing parents are the existing/planned C++ classes. No widget reads the database or the ledger directly — each reads through its named owner.

| Widget | Parent / owner | Screen | Data it binds |
|---|---|---|---|
| `WBP_HUD` | `AHUD` via `NexoraPlayerController` | HUD root | clock chip, tracker, needs, balance, prompt |
| `WBP_ClockChip` | `WBP_HUD` child | HUD | `UNexoraGameClock` + weather glyph |
| `WBP_ObjectiveTracker` | `WBP_HUD` child | HUD | mission state (`missions.json` ids) |
| `WBP_NeedsStrip` | `WBP_HUD` child | HUD | GDD-01 §4 needs |
| `WBP_InteractPrompt` | `WBP_HUD` child | HUD | `IA_Interact` context target |
| `WBP_MainMenu` | menu GameMode | Main Menu | save slot list (Unit M) |
| `WBP_CharacterCard` | reusable | Profile, select, NPC inspect, save slots | GDD-01 §1 card fields — the single card implementation used everywhere (§1 rule 4) |
| `WBP_ProfilePanel` | panel | Profile | character record + tabs (§4) |
| `WBP_LedgerView` | `WBP_ProfilePanel` child | Profile → Balance | `economy_ledger` rows |
| `WBP_MissionLog` | panel | Mission Log | `missions.json` + progress + achievements |
| `WBP_EnvPanel` | panel | Environment Control | `UNexoraGameClock`, `UNexoraWeatherManager` only (§5) |
| `WBP_PauseMenu` | panel | Pause | clock `SetPaused`, save slots |
| `WBP_Settings` | panel | Settings | account settings |
| `WBP_SaveLoad` | panel | Save/Load | Unit M save scaffold (`NexoraSaveGame`) |

## 11. What This Document Deliberately Does Not Decide

- **Minimap / world map:** no map system exists in any merged design. Inventing one here would be decoration; it gets its own unit when the owner asks.
- **Localisation:** all strings above are English design text. A Bangla UI is plausible for this project but is a separate owner decision (the plan's i18n experience from other projects does not silently transfer).
- **Phone / social UI, chat, friends list:** Phase 9 (multiplayer) designs these with server authority in mind; a single-player phone mock now would be thrown away.
- **Combat/damage UI:** no combat model is designed in any phase yet; no health/ammo elements are specified.
- **Character creation screens:** Phase 6 — the creation flow edits the GDD-01 identity model (traits, profession choice) and needs the life-sim to exist first; §2 reserves its place in the flow only.
- **Director/player weather control in shipped play:** refused for v1 (§5); forecast-driven weather is the shipped design.

## 12. Acceptance Checks (for the phases that build this)

1. HUD clock matches `GameClock` to the minute over a full in-game day (TECH-CLOCK-WEATHER §7 test 1, UI side).
2. Every balance shown anywhere equals the ledger-derived value; the Ledger sub-view's rows sum to the displayed balance.
3. Env Panel snow button is disabled in District 1 and enabled in a snow-zone test map; panel writes reach only clock/weather (code review point, §5).
4. Profile card for the owner's example character renders the §1 fields in order with the §1 values.
5. All panels fully operable by gamepad alone; Esc unwinds exactly one layer.
6. No screen in the shipped build contains an element whose backing system is unimplemented (the §10 list is the audit checklist).

*End of GDD-05 v1.0.*
