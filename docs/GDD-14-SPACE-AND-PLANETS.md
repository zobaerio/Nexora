# NEXORA — GDD-14: Space & Planets

**Unit AG (Queue 6) · Version 1.0 · 2026-11-22**
**Parent documents:** `NEXORA-MIGRATION-PLAN.md` Part C #16 (Planets & space) + Part D Phase 10 · `data/planets.json` v1.0 (the only planet data this document uses) · `docs/GDD-04-MISSIONS-AND-PROGRESSION.md` Level 8 "Space Explorer" · `docs/GDD-02-RUPSHA-CITY-DISTRICT1.md` (departure city) · `docs/GDD-01-LIFE-AND-DATA-MODEL.md` §8 (ledger) + §9 (save-game mapping) · `docs/TECH-SAVE-SYSTEM.md` · `data/schema.sql`
**Status:** DESIGN DOCUMENT ONLY — no UE code, nothing claimed built. All UE work in this document is uncompiled scaffold until the owner's PC build (migration plan Part 0). Planet parameters come only from `data/planets.json`; nothing in this document invents a planet, a gravity value, a price, or a date.

---

## 1. Scope — and One Apparent Contradiction, Resolved

The migration plan's Phase 10 build line reads: *"Space station hub, 2 planets (desert/red, ringed giant's moon)…"* — and the Queue 6 brief for this unit repeated "the 2 planets". The merged `data/planets.json` v1.0, read in full, contains **five** bodies plus the star:

| Body in `planets.json` | `id` | Role in Phase 10 |
|---|---|---|
| Nexora Prime | `nexora_prime` | Home world — departure point, not a Phase 10 destination |
| Nexora-7 | `nexora_7` | Landing target #1 — the red desert world |
| Kallisto (moon of Nexora-9) | `nexora_9_moon_kallisto` | Landing target #2 — the ringed giant's moon |
| Nexora-9 | `nexora_9` | Orbit-only gas giant — never landable |
| Prime Moon | `prime_moon` | Orbit-only in Phase 10 v1 — surface landing is a post-Phase-10 decision |

There is no contradiction once the two counts are read as different things: **"2 planets" = the two off-world landing targets** (Nexora-7 and Kallisto), which is exactly what the plan's parenthetical says — desert/red, ringed giant's moon. The other three bodies exist in the data file because a player clicking them in the universe map deserves a true answer (`planets.json` notes field), and this document gives each of them an info card (§3) with fields copied verbatim from the file. **No body is added, removed, or re-scoped here.** If the owner later wants the count read differently, that is a data-file change, not a rewrite of this document.

**Phase 10 v1 scope, fixed:**

- A space-station hub in orbit around Nexora Prime (§5).
- Two landable off-world surfaces — Nexora-7 and Kallisto — as separate worlds with their own gravity/atmosphere parameters actually affecting physics and visuals (§4).
- Planet info cards for all five bodies, fields matching `planets.json` exactly (§3).
- Landing / base-building v1 (§7, §8).
- Orbital animation + time-speed controls for the space view (§6).
- The travel chain city → station → planet surface → return, with inventory and character state intact throughout (§9).
- Hookup to the GDD-04 Level 8 missions (§10).

**Out of scope for v1:** seamless ground-to-orbit flight (migration plan Part C #16: transitions are the honest design); a living off-world society (planets start as exploration sites, not full living worlds — Part C #16); Prime Moon surface landing (orbit + info card only, per `landing_note` in `planets.json`); any landing on Nexora-9, ever, by physics (`landing_allowed: false`, §3.4).

---

## 2. The System — What `planets.json` v1.0 Actually Contains

The star and the five bodies, exactly as the data file lists them. This section is a reader's index; §3 carries the full cards.

| Body | `id` | `exploration_status` | `gravity_ms2` | `landing_allowed` | `base_building` | `ring_system` |
|---|---|---|---|---|---|---|
| Nexora (star) | `nexora_star` | — (type: G-type main-sequence) | — | — | — | — |
| Nexora Prime | `nexora_prime` | `home_world` | 9.8 | true | true | false |
| Nexora-7 | `nexora_7` | `unexplored` | 3.9 | true | true | false |
| Kallisto (moon of Nexora-9) | `nexora_9_moon_kallisto` | `unexplored` | 1.1 | true | true | false |
| Nexora-9 | `nexora_9` | `orbit_only` | 24.8 | false | false | true |
| Prime Moon | `prime_moon` | `surveyed` | 1.6 | false | false | false |

Source for every cell: `data/planets.json` v1.0 (`version: "1.0"`). The star's entry in the file: `"description": "The system sun (owner spec §7): drives day-night on Prime and the universe-map view with orbital animation + time-speed controls."`, `"type": "G-type main-sequence"`.

**Design consequence of the table:** there are exactly two v1 landing targets, one orbit-only giant, one orbit-only moon, and one home world. Every system in this document keys off those flags — `landing_allowed` gates the landing sequence (§7), `base_building` gates base construction (§8), `exploration_status` gates what the info card shows as known vs. unknown (§3), and `ring_system` gates the signature orbital sight (§6).

---

## 3. Planet Info Cards

One card per body. **Every field value below is copied verbatim from `data/planets.json` v1.0** — including wording of `atmosphere`, `surface_type`, and `description`. The cards are the in-game UI text (§3.6) and the data source of truth at the same time: if a card and the file ever disagree, the file wins and the card is corrected.

### 3.1 Nexora Prime — `nexora_prime`

| Card field | Value (`planets.json`) |
|---|---|
| Name | Nexora Prime |
| Gravity | 9.8 m/s² (`gravity_ms2: 9.8`) |
| Temperature | min −15 °C, mean 21 °C, max 42 °C |
| Atmosphere | Nitrogen-oxygen, breathable |
| Surface type | Continents, oceans, rivers, forests, mountains |
| Resources | water, arable_land, timber, river_clay, sand, limestone |
| Exploration status | `home_world` |
| Landing allowed | Yes (`landing_allowed: true`) |
| Base building | Yes (`base_building: true`) |
| Ring system | No |
| Moons | Nexora Prime Moon (see separate card) |
| Description | "The home world: Rupsha City and Nexora Central. All Phases 1-9 content lives here." |

**Design note:** Prime is the baseline every other card is measured against. Its gravity (9.8) is the reference for the jump-physics ratios in §4.1, and its breathable atmosphere is why no suit is ever required on the home world. Its "base building: true" is already served by the existing property system (GDD-01 §5, GDD-02 §6) — Phase 10 adds nothing to Prime's building; the flag is recorded here only because the file carries it.

### 3.2 Nexora-7 — `nexora_7`

| Card field | Value (`planets.json`) |
|---|---|
| Name | Nexora-7 |
| Gravity | 3.9 m/s² (`gravity_ms2: 3.9`) |
| Temperature | min −73 °C, mean −32 °C, max 20 °C |
| Atmosphere | Thin CO2, unbreathable — suit required |
| Surface type | Red desert, rock fields, canyon systems, polar ice caps |
| Resources | iron_oxide_regolith, silicates, subsurface_ice, basalt |
| Exploration status | `unexplored` |
| Landing allowed | Yes (`landing_allowed: true`) |
| Base building | Yes (`base_building: true`) |
| Ring system | No |
| Description | "The red desert world of the owner's spec: first off-world landing target in Phase 10, with a small research base as the v1 buildable." |

**Design note:** Nexora-7 is the first off-world landing target and the site of the v1 base (§8). It is also the destination of GDD-04 mission 8.3 ("First Launch") and the foothold of mission 8.4 ("A New World") — see §10.

### 3.3 Kallisto, moon of Nexora-9 — `nexora_9_moon_kallisto`

| Card field | Value (`planets.json`) |
|---|---|
| Name | Kallisto (moon of Nexora-9) |
| Gravity | 1.1 m/s² (`gravity_ms2: 1.1`) |
| Temperature | min −160 °C, mean −40 °C, max 110 °C |
| Atmosphere | None (airless moon) |
| Surface type | Cratered rock and dust plains, shadowed polar craters |
| Resources | regolith, helium_3_traces, water_ice_shadowed_craters |
| Exploration status | `unexplored` |
| Landing allowed | Yes (`landing_allowed: true`) |
| Base building | Yes (`base_building: true`) |
| Ring system | No |
| Parent planet | `nexora_9` (`parent_planet: "nexora_9"`) |
| Description | "Airless moon of the ringed giant: low-gravity base site and the Phase 10 space-station counterpart on a surface. Orbital views of the rings are its signature sight." |

**Design note:** Kallisto is the second landing target — the "ringed giant's moon" of the Phase 10 build line. Its parent is Nexora-9 (§3.4); the two cards link to each other in the UI, and the orbital view from Kallisto's surface shows Nexora-9's rings (§6). Its resource list is the only place `helium_3_traces` and `water_ice_shadowed_craters` appear in the game data — the card must not paraphrase them into generic "minerals" or "water".

### 3.4 Nexora-9 — `nexora_9`

| Card field | Value (`planets.json`) |
|---|---|
| Name | Nexora-9 |
| Gravity | 24.8 m/s² (`gravity_ms2: 24.8`) — "Cloud-top reference gravity; there is no solid surface to stand on." (`gravity_note`) |
| Temperature | min −145 °C, mean −128 °C, max −110 °C |
| Atmosphere | Hydrogen-helium, crushing pressure — NO surface landing |
| Surface type | Gas giant — banded clouds, no solid surface |
| Resources | atmospheric_hydrogen_scoop_theoretical |
| Exploration status | `orbit_only` |
| Landing allowed | No (`landing_allowed: false`) |
| Base building | No (`base_building: false`) |
| Ring system | Yes (`ring_system: true`) |
| Description | "The ringed giant of the owner's spec. Not landable — ever, by physics. Explored via its moon (Kallisto) and orbital station views; the planet card exists because players will click it in the universe map and deserve a true answer." |

**Design note:** Nexora-9 is the game's honest "no". The card must say so in plain language — "NO surface landing" is the file's own wording — and the UI must never offer a landing button for it. Its only resource, `atmospheric_hydrogen_scoop_theoretical`, is labelled *theoretical* in the file: it is not harvestable in v1, and the card must not present it as a collectible. What Nexora-9 *does* give the player is the orbital view (§6) and its moon Kallisto (§3.3) as the way to explore it.

### 3.5 Prime Moon — `prime_moon`

| Card field | Value (`planets.json`) |
|---|---|
| Name | Prime Moon |
| Gravity | 1.6 m/s² (`gravity_ms2: 1.6`) |
| Temperature | min −130 °C, mean −20 °C, max 120 °C |
| Atmosphere | Trace exosphere |
| Surface type | Cratered highlands and dark basalt plains |
| Resources | regolith, water_ice_polar |
| Exploration status | `surveyed` |
| Landing allowed | No (`landing_allowed: false`) — "Orbit only in Phase 10 v1; surface landing is a post-Phase-10 expansion decision." (`landing_note`) |
| Base building | No (`base_building: false`) |
| Ring system | No |
| Parent planet | `nexora_prime` (`parent_planet: "nexora_prime"`) |
| Description | "Earth-like system's moon analogue for Prime: destination of the first crewed flight milestone inside Phase 10's station content; surface visits are a later expansion, so v1 is orbit + info card only." |

**Design note:** Prime Moon is `surveyed` — the only body besides Prime whose card shows surveyed rather than unexplored/home status — and it is the destination of the first crewed flight milestone inside the station content (§5). In v1 the player flies to its orbit and reads this card; the surface stays out of reach by design, and the card says why, in the file's own words.

### 3.6 Card UI rules (all five cards)

- **Fields shown, in order:** name, gravity, temperature (min / mean / max), atmosphere, surface type, resources, exploration status — the owner's example card order from the `planets.json` notes field ("Fields match the owner's example card: Gravity, Temperature, Atmosphere, Surface Type, Resources, Exploration Status"), plus landing/base-building status and the description.
- **Unknown stays unknown:** a body with `exploration_status: "unexplored"` shows its card fields (they are the survey data the programme holds) but its surface is not rendered in detail until first landing — the card is data, the surface is discovery. `exploration_status` flips to a landed/surveyed state only through the mission flow (§10, mission 8.4).
- **No paraphrase of resource ids:** resource lists are shown as the file's ids (`iron_oxide_regolith`, not "iron"; `water_ice_shadowed_craters`, not "water"). The ids are what the harvest/gather systems key off (§4.5).
- **The card is the same object everywhere:** universe map, station departure board, and landing briefing all read the same card from the same data file. There is no second, hand-written copy of a planet's numbers to drift.

---

## 4. Parameters → Gameplay & Visuals

The `planets.json` notes field states the rule this section implements: *"gravity_ms2 and temperature ranges are SIMULATION INPUTS (jump physics, weather, suit requirements), not display text"*. Every parameter below maps to a concrete effect. Where a ratio is given, it is arithmetic on the file's own values (reference gravity 9.8 on Nexora Prime), labelled as derived — no new parameter is introduced.

### 4.1 Gravity (`gravity_ms2`) → movement physics

| Body | `gravity_ms2` | Jump apex vs Prime (derived: 9.8 ÷ g) | Effect |
|---|---|---|---|
| Nexora Prime | 9.8 | 1.0× (reference) | Baseline movement (TECH-MOVEMENT / Phase 3 controller) |
| Nexora-7 | 3.9 | ≈ 2.5× | High, slow, floaty jumps; longer air time; fall damage threshold raised proportionally — a fall that injures on Prime is a hop here |
| Kallisto | 1.1 | ≈ 8.9× | Near-weightless bounding; a normal jump becomes a long arc; walking needs a magnetic-boot / careful-step rule or the character drifts — the lowest-gravity surface the player can stand on |
| Prime Moon | 1.6 | ≈ 6.1× | (Orbit only in v1 — physics defined here so the later surface expansion inherits it, not so v1 uses it) |
| Nexora-9 | 24.8 | ≈ 0.4× | Cloud-top reference only; no surface, no standing, no jump — the value exists on the card so the player understands why |

**Implementation rule:** gravity is a per-map world setting, read from the body's card at map load — never a global constant, never a per-character stat. The same jump input produces a different apex on each world because the world is different, not because the character changed. Fall damage, walk speed on slopes, thrown-object arcs, and vehicle handling on the surface all read the same value, so the low-gravity feel is consistent across systems instead of being a jump-only trick.

### 4.2 Temperature (`temperature_c` min / mean / max) → suit & hazard

| Body | Temperature range | Effect |
|---|---|---|
| Nexora Prime | −15 to 42 °C, mean 21 °C | No suit; existing weather system applies (TECH-CLOCK-WEATHER) |
| Nexora-7 | −73 to 20 °C, mean −32 °C | Suit required at all times outdoors (the atmosphere already requires it, §4.3); cold exposure is a timed hazard — suit integrity / thermal reserve drains outside a heated base, and the polar ice caps are the coldest zone on the surface |
| Kallisto | −160 to 110 °C, mean −40 °C | Suit required (airless, §4.3); the 270-degree swing is the hazard — sunlit rock is scorching, shadowed polar craters are the coldest place in the game; time-of-day on the surface matters, not just the mean |
| Prime Moon | −130 to 120 °C, mean −20 °C | (Orbit only in v1 — same rule, inherited by the later expansion) |
| Nexora-9 | −145 to −110 °C, mean −128 °C | No surface; temperature is card information for the orbital view only |

**Implementation rule:** temperature is read as the *range*, never the mean alone — the mean of Kallisto (−40 °C) hides a surface that is both the hottest and coldest place the player can stand. Hazard design uses min/max; the mean is the card's summary line.

### 4.3 Atmosphere → breathability, sky, sound

| Body | Atmosphere (`planets.json`) | Effect |
|---|---|---|
| Nexora Prime | Nitrogen-oxygen, breathable | No suit; open sky, normal audio, existing weather |
| Nexora-7 | Thin CO2, unbreathable — suit required | Suit mandatory outdoors; thin air → pale, washed-out sky, weak sound propagation (muffled exterior audio, suit-radio voice), dust haze over the red desert; the suit is a gameplay gate, not a costume — without it, the airlock does not open (§7) |
| Kallisto | None (airless moon) | Suit mandatory; no sky scattering — black sky with stars even at "noon", hard shadows, no exterior audio at all (suit radio only); dust kicked up by footsteps falls straight back down in low gravity |
| Prime Moon | Trace exosphere | (Orbit only in v1 — same airless treatment when the surface ships) |
| Nexora-9 | Hydrogen-helium, crushing pressure — NO surface landing | Orbital view only: banded-cloud visuals from orbit, no surface audio question arises |

**Implementation rule:** the atmosphere string on the card *is* the suit gate. The game does not maintain a second, hidden "breathable?" flag: if the card's atmosphere says "suit required", the airlock/landing logic reads that field. A suit is an inventory item (GDD-01 §9 / `schema.sql` `inventory_items`, `item_type` clothing/tool — the catalogue `item_ref` is defined at implementation, not invented here), and the travel chain (§9) checks for it before the landing hop is offered.

### 4.4 Surface type → terrain & visuals

| Body | Surface type (`planets.json`) | Visual / terrain treatment |
|---|---|---|
| Nexora Prime | Continents, oceans, rivers, forests, mountains | Existing city/terrain systems (Phases 1–5) |
| Nexora-7 | Red desert, rock fields, canyon systems, polar ice caps | Red regolith terrain, rock-field scatter, canyon systems as the navigable landmark terrain, white polar caps at the map edge; iron-oxide colour grade is the world's signature — the red must read as geology, not as a filter |
| Kallisto | Cratered rock and dust plains, shadowed polar craters | Cratered terrain as the primary feature (craters are navigation landmarks), grey dust plains, permanently shadowed polar craters that hold `water_ice_shadowed_craters` (§4.5) |
| Nexora-9 | Gas giant — banded clouds, no solid surface | Orbital view only: banded-cloud shader + rings (§6) |
| Prime Moon | Cratered highlands and dark basalt plains | (Orbit only in v1) |

Each landable surface is a **separate World Partition map** (migration plan Part C #16), with its own terrain, lighting, and gravity setting (§4.1). The two v1 surfaces are exploration sites, not cities: no NPC society, no economy simulation, no property market — those systems stay on Prime, and the base (§8) is the only persistent player structure off-world.

### 4.5 Resources → what the player can actually gather

Resources are the file's ids, and only those ids are harvestable on each body:

- **Nexora-7:** `iron_oxide_regolith`, `silicates`, `subsurface_ice`, `basalt`. Subsurface ice is the base's water story (§8); regolith and basalt are the base-building material story.
- **Kallisto:** `regolith`, `helium_3_traces`, `water_ice_shadowed_craters`. `helium_3_traces` is a *trace* resource by its own name — rare, low-yield, a survey find, not a mine. `water_ice_shadowed_craters` exists only in the shadowed polar craters (§4.4), so gathering it means going to the coldest, darkest part of the map.
- **Nexora-9:** `atmospheric_hydrogen_scoop_theoretical` — theoretical, not harvestable in v1 (§3.4).
- **Prime Moon:** `regolith`, `water_ice_polar` — not harvestable in v1 (orbit only).

Gathered resources are `inventory_items` rows (`schema.sql`: `item_ref` = the resource id, `owner_character_id` = the player) — the same inventory that travels home in §9. Nothing gathered off-world is a separate currency; if it is ever sold, it is sold through the normal ledger (§9) on Prime.

### 4.6 Exploration status → what the player knows

- `home_world` (Prime): everything known; full map, full society.
- `unexplored` (Nexora-7, Kallisto): card data known (the programme's survey), surface unknown until first landing. First landing is a mission event (GDD-04 8.3/8.4), not a free-roam stroll — the status flips only through that flow.
- `surveyed` (Prime Moon): mapped from orbit, surface not visited in v1.
- `orbit_only` (Nexora-9): the card is the whole truth; there is no hidden surface to unlock later.

---

## 5. The Space-Station Hub

**What it is:** the Phase 10 hub — a station in orbit around Nexora Prime where the travel chain changes vehicle: city → station → planet surface (§9). It is the off-world equivalent of a Phase 8 airport/station travel hub (migration plan Phase 8: "airports/stations as functional travel hubs"), extended to orbit.

**Working name:** "Nexora Station" — *proposed here, owner confirms or renames* (the same convention GDD-04 uses for the proposed Level 2–7 names: the name is a label, the structure is the design).

**What the hub contains (v1):**

- **Docking / arrival concourse** — the player arrives from Prime and departs for Nexora-7 or Kallisto. Departure boards show the five planet cards (§3) for selection; Nexora-9 and Prime Moon offer orbit views only, never a landing button (§3.4, §3.5).
- **Space-programme offices** — where GDD-04 mission 8.1 ("The Application") is filed and mission 8.2 ("Training") is run: zero-g and survival training as skill challenges in the station's training ring. Training happens *here*, before any launch, so a player who fails training has failed safely in orbit, not on a red desert.
- **Crew quarters & mess** — the player's home anchor while off-world: sleep / time-skip works here exactly as the home anchor works on Prime (GDD-04 §4 rule 5: "The player can always go home" — in Phase 10, "home" includes the station bunk and, later, the planet base).
- **Suit & equipment bay** — where the suit (§4.3) is issued, checked, and stored as an inventory item. The bay is also the enforcement point: no suit, no airlock, no landing (§7).
- **Observation deck** — the in-fiction home of the space view (§6): orbital animation, the star, Nexora-9's rings, and the time-speed controls, presented as the station's windows rather than as an abstract menu.
- **First crewed flight milestone** — the station content includes the Prime Moon flight from the `prime_moon` description (§3.5): a crewed orbital flight to the Prime Moon, orbit + info card only, as the programme's first crewed milestone before the Nexora-7 landing.

**What the hub is not:** a second city. No NPC society simulation, no property market, no businesses — the station is a transit and training facility with a small permanent crew (scheduled-tier NPCs at most, GDD-01 §2). Its population is a roster, not a district.

---

## 6. Orbital Animation & Time-Speed Controls (the Space View)

**Where it lives:** the universe map (from anywhere the player can open it) and the station observation deck (§5) — the same view, two framings.

**What it shows:** the star `nexora_star` (G-type main-sequence) as the light source; Nexora Prime, Nexora-7, Kallisto, Nexora-9 with its rings (`ring_system: true`), and the Prime Moon, each rendered from its card (§3) — size, colour, rings, and cloud bands follow the card data. From Kallisto's surface, Nexora-9 and its rings dominate the sky (§3.3); from the station, Prime fills the window.

**Orbital animation:** the bodies move along their orbits in the space view, driven by the world clock — the same clock the save system snapshots (`TECH-SAVE-SYSTEM` §2–§3: `GameMinutes`, `TimeScale`). **Honest limit, stated here rather than faked:** `planets.json` v1.0 carries no orbital elements (no periods, no distances, no inclinations), so v1 orbital motion is *schematic* — bodies move at illustrative rates that read correctly as "a living system" but are not simulated Keplerian orbits. Real orbital periods are data to be added to the file in a later version, with a migration note; until then the design must not claim the animation is astronomically true.

**Time-speed controls:** the space view reuses the world's time scale, not a separate clock. The controls are the clock's speeds — pause, normal, fast, fastest — mapped onto `world_state.time_scale` (GDD-01 §9 / `TECH-SAVE-SYSTEM` §2: `TimeScale`, "Design setting (Unit E), restored on load"). Changing speed in the space view changes the same `time_scale` the city simulation runs on, and the save system restores it on load (`TECH-SAVE-SYSTEM` §3: `ApplyWorldState` → `SetTimeScale`). There is one clock, one saved speed, and the orbital animation is a visualisation of it — never a second timeline that could drift from the world the player returns to.

**Day–night link:** the star drives day–night on Prime (`planets.json` star description). The space view shows Prime's day side and night side consistently with the in-world clock the player left behind — the view is a window onto the same world, not a separate skybox.

---

## 7. Landing — Transition Sequences, Not Seamless Flight

**The rule (migration plan Part C #16):** *"Seamless ground-to-orbit flight in one world is not realistic at this scale; transitions are the honest design."* Landing is a transition sequence: the player boards at the station, a launch/descent sequence plays, and the player steps out onto the surface map. There is no flyable spacecraft the player pilots from orbit to ground in v1, and no claim of one.

**Per-body landing behaviour:**

| Body | Landing sequence |
|---|---|
| Nexora-7 | Full sequence: station → descent over the red desert → step-out at the landing site. First landing is GDD-04 mission 8.3; the sequence is the mission's set piece. |
| Kallisto | Full sequence: station → descent over cratered plains → step-out with Nexora-9's rings in the sky. |
| Nexora-9 | No sequence exists — `landing_allowed: false`. The UI offers an orbital pass instead (§6). |
| Prime Moon | No sequence in v1 — orbit + info card only (`landing_note`, §3.5). |
| Nexora Prime | Return landing (§9) — the reverse of the departure, ending back in the city. |

**Landing gates (all checked before the sequence is offered):**

1. Mission state — first landing to a body requires the relevant mission active (GDD-04 8.3 for Nexora-7; Kallisto's first landing is a post-8.4 free-roam unlock — see §10).
2. Suit — the atmosphere gate (§4.3): the airlock does not open without a suit inventory item for Nexora-7 and Kallisto.
3. Character state — the character's skills, health, and inventory travel with them (§9); nothing is stripped for the trip.

**What the player steps out into:** the body's surface map (§4.4) at a fixed landing site — the same site every time in v1, so the base (§8) and the landing point form one coherent foothold. Free-roam exploration radiates from the site; the map is an exploration site, not a second city.

---

## 8. Landing / Base-Building v1

**v1 buildable:** one small research base per landable off-world body — Nexora-7 first (its card description names it: "a small research base as the v1 buildable"), Kallisto second (its card: "low-gravity base site"). The base is the player's foothold: shelter from the temperature hazard (§4.2), suit recharge, sleep/time-skip anchor, and storage for gathered resources (§4.5).

**What "v1" means, concretely:**

- **Placement:** fixed site next to the landing point (§7), chosen at first landing — no free-form placement anywhere on the map in v1. The site is the foothold; the rest of the surface stays wild.
- **Structure:** a small research base — habitat module, airlock, power unit, storage. Built in stages (foundation → sealed habitat → powered base), using gathered surface resources (§4.5: Nexora-7 `basalt` / `iron_oxide_regolith` / `silicates`; Kallisto `regolith`) as the material story. No new currency, no invented price: construction consumes inventory items and game time, and any credit cost is a ledger row through the normal economy (§9) only if the economy design prices it — this document sets no price.
- **Function:** the base is shelter (temperature hazard suspended inside), a sleep anchor (GDD-04 §4 rule 5), a suit-recharge point, and resource storage. It is not a business, not a home for NPCs, and not a property-market listing.
- **Persistence:** the base persists in the save like any other player structure — it is part of the saved world (§9), so returning to Nexora-7 finds the base as the player left it.

**Bodies where base-building does not apply:** Nexora-9 (`base_building: false` — no surface), Prime Moon (`base_building: false` — orbit only in v1). Nexora Prime (`base_building: true`) is served by the existing property system (GDD-01 §5), not by this section.

**Open decision, flagged not decided:** the schema's `properties` table keys locations to district ids (`properties.district_id`, GDD-02 §2 `d1_*` ids). An off-world base needs a location reference to a planet surface site, which no district id covers today. This document does **not** silently extend the schema: the location scheme for off-world bases (planet id + site id, or a new location table) is decided at implementation, with the migration note GDD-01 §10 requires whenever `schema.sql` changes shape. Until then, the design treats the base as a `properties`-shaped record whose location field is pending that decision.

---

## 9. The Travel Chain — City → Station → Planet Surface → Return, State Intact

This is the Phase 10 exit criterion, in the plan's own words: *"Player travels city → station → planet surface → builds a small base → returns, with inventory and character state intact throughout."* This section maps every hop onto the save/ledger design so "intact" is a checkable property, not a hope.

### 9.1 The hops

| Hop | From → To | What happens | Map / world |
|---|---|---|---|
| 1 | Rupsha City, District 1 → Station | Player travels to the spaceport, boards, transition sequence to orbit | District 1 map → station map |
| 2 | Station → Planet surface | Suit check (§4.3), landing sequence (§7), step-out at the landing site | Station map → Nexora-7 or Kallisto surface map |
| 3 | Surface → Station | Return launch from the landing site; transition sequence back to orbit | Surface map → station map |
| 4 | Station → Rupsha City | Descent to Prime; the player steps out back in District 1 | Station map → District 1 map |

**Departure point — a necessary clarification:** GDD-02's "Launch Terminal" (zone `d1_riverfront`, landmark #3) is a **river launch/ferry terminal** — boats on the Rupsha, not spacecraft — and GDD-02 §8 states plainly that District 1 has **no airport** ("No airport (Phase 8 travel)"). The spaceport is therefore a **new Phase 10 facility**, not the riverfront terminal renamed. Its site is a Phase 8/10 decision (the Station Quarter, `d1_transport`, is the natural candidate — it already holds the bus terminal and railway station frontage — but this document does not fix the plot; the district design owns it). The travel chain starts in District 1 either way: the player walks from their home anchor to the spaceport through the district they live in.

**Travel time:** each hop advances `world_state.game_minutes` (GDD-01 §9; `TECH-SAVE-SYSTEM` §2 `GameMinutes`). The durations are tuning owned by implementation — this document fixes no number of minutes, because no transit duration exists in any parent document. What is fixed is the rule: travel consumes in-world time, the clock keeps running, and the save records the arrival time, so a player who leaves on Day 40 does not return on Day 40.

### 9.2 What "intact" means — the state inventory

One data model, two stores (GDD-01 §9): in single-player phases the same schema is serialised into the save slot; in Phase 9 the same tables live behind the server. The travel chain never leaves that model. Nothing is copied into a parallel "space inventory" or a second character record.

| State | Schema / save location | How it survives the chain |
|---|---|---|
| Character identity, skills, traits, reputation | `characters`, `character_skills` (GDD-01 §2) | Carried as the same rows; the character is the same row on every world. Skills gained in training (GDD-04 8.2) persist to the surface and home. |
| Money | `economy_ledger` — append-only, the only truth (GDD-01 §8); `characters.balance_cached` is a cache only | No hop touches money except through ledger rows. A fare, a purchase, or a mission reward is a ledger row with a `reason_code` from the schema's list (`mission_reward`, `purchase`, …) — never a silent balance edit. If cache and ledger ever disagree, the ledger wins (GDD-01 §8; `TECH-SAVE-SYSTEM` §2). |
| Inventory | `inventory_items` (`owner_character_id`, `item_ref`, `state` JSONB) | Every item travels: suit, tools, gathered resources (§4.5). Items are never stripped at a hop boundary. `location_property_id` may change (an item stored at the base vs. carried) — ownership never does. |
| Property & base | `properties` (+ off-world location decision, §8) | The player's Prime properties are untouched by the trip; the off-world base (§8) is a property record that persists in the save. |
| Household & relationships | `households`, `household_members`, `relationships` (GDD-01 §5, §6) | The player's household stays on Prime; absence is time passing at home (the clock runs, §9.1), not a household change. No relationship is created or destroyed by travelling. |
| Memories & goals | `character_memories`, `character_goals` (GDD-01 §2.2, §2.3) | First launch and first landing are episodic memories (GDD-04 8.3 reward: memory event "First launch"). Goals are untouched by travel. |
| Mission progress | `mission_progress` (`character_id`, `mission_id`, `status`, `progress` JSONB) | The Level 8 missions (§10) are tracked in this table across hops — a mission active on Prime is still active on Nexora-7. |
| Achievements | `achievements` — account-level (GDD-04 §5; GDD-01 §1: achievements survive character death) | "Space Explorer" (Gold) unlocks on Level 8 completion and lives on the account, not the character. |
| World clock & time scale | `world_state.game_minutes`, `world_state.time_scale` | Saved and restored by `TECH-SAVE-SYSTEM` §3 (`CaptureWorldState` / `ApplyWorldState`); the time scale set in the space view (§6) is the same value restored on load. |
| Weather (Prime) | `world_state.weather_preset` | Prime's weather keeps its own state; off-world maps have their own atmosphere visuals (§4.3), not Prime's weather presets. |

### 9.3 What is deliberately NOT carried — the save-system boundary

`TECH-SAVE-SYSTEM` §2 is explicit, and the travel chain respects it: **`PlayerTransform` is runtime render state, not a society fact.** The character's position is *not* carried across a hop. At each arrival, the character spawns at that world's arrival anchor (spaceport gate, station concourse, landing site, district street) — the position is re-derived from the hop, never teleported from the previous map. Carrying a Prime street coordinate onto a Nexora-7 surface would be a bug, not fidelity. Everything in §9.2 travels; the transform does not, by design.

### 9.4 Save points in the chain

- **Autosave / manual save is offered at each arrival** (station, surface, return to Prime) — the save captures the full §9.2 state through the normal `TECH-SAVE-SYSTEM` path (`TablePayloads` map, one JSON payload per schema table; `TECH-SAVE-SYSTEM` §1–§2). No hop has its own save format.
- **Mid-transit saves** are not offered: a transition sequence is not a world state. If the player quits mid-sequence, they reload at the last arrival save — the design says this plainly instead of pretending a mid-flight state exists.
- **Versioning:** the save carries `SaveSchemaVersion` (`TECH-SAVE-SYSTEM` §4); a save newer than the build is refused, never silently loaded — this applies to off-world saves exactly as it applies to city saves.

### 9.5 Acceptance check for the exit criterion

On the owner's PC, in a packaged build (Phase 10 exit test): depart District 1 with a known inventory and balance → land on Nexora-7 → build the v1 base → gather at least one resource → return to District 1 → verify: (a) every inventory item present, including the gathered resource; (b) balance equals the ledger sum; (c) skills, mission progress, and memories unchanged except for the trip's own entries; (d) the base persists on a second visit. Any item lost, any balance changed without a ledger row, or any character field altered by the trip itself fails the criterion.

---

## 10. Mission Hookup — GDD-04 Level 8 "Space Explorer"

Level 8 is the owner's endpoint: *"leave the planet. Phase 10."* (GDD-04 §2, Level 8). This design serves all four of its missions; no mission is added, renamed, or re-rewarded here.

| Mission | Objectives (GDD-04) | Reward / Unlock (GDD-04) | Served by this design |
|---|---|---|---|
| **8.1 The Application** | Qualify for the space programme (Senior tier + savings 500,000 NCr + reputation 80) | Programme acceptance; unlock: Space programme | §5 station hub (programme offices); qualification reads the existing character state (GDD-01 §2 skills/reputation, §8 ledger balance) — no new gate is invented |
| **8.2 Training** | Complete zero-g and survival training (skill challenges) | 10,000 NCr, +30 reputation; unlock: Training facility | §5 training ring in the station; zero-g training uses the low-gravity movement rules of §4.1, survival training uses the suit/temperature rules of §4.2–§4.3 |
| **8.3 First Launch** | Crew the first mission to Nexora-7 (data card in `data/planets.json`) | Memory event "First launch"; unlock: Spacecraft, Nexora-7 landing | §7 landing sequence (first landing as set piece); §3.2 card is the mission's data card; §9.2 records the memory event in `character_memories` |
| **8.4 A New World** | Establish the first foothold on Nexora-7; return with a survey | 50,000 NCr, title "Space Explorer"; unlock: Planetary settlement (Phase 10) | §8 v1 research base is the foothold; §4.5 survey/gathering is the survey; §9 return hop brings the player home; title + 50,000 NCr are ledger/account effects (§9.2) |

**After Level 8** (GDD-04 §2): the "Space Explorer" title, planetary travel, and the open-ended endgame — *"the player keeps living — new cities, new planets, new generations (GDD-01 §3)."* Kallisto's first landing is a post-8.4 free-roam unlock: it needs the programme acceptance (8.1) and a suit, but no further mission gate — the player who has proven they can land on Nexora-7 is trusted with the moon.

**Achievement:** "Space Explorer" — complete Level 8 — Gold tier (GDD-04 §5). Account-level; it survives character death (GDD-04 §5, GDD-01 §1).

**Design law carried over:** missions are offers, not orders (GDD-04 header; GDD-01 §2.2). A player who qualifies for the programme and never applies loses nothing; the station, the cards, and the orbital view (§6) are visitable without taking mission 8.1 — the universe is there to look at before it is there to land on.

---

## 11. Phase 10 Exit Criteria — Restated as Checks

From the migration plan, Part D Phase 10: *"Player travels city → station → planet surface → builds a small base → returns, with inventory and character state intact throughout."* Restated as the checks this design must pass in a packaged build on the owner's PC:

1. **Chain complete:** city → station → surface → base → return, in one play session, with no hop requiring a reload or a workaround (§9.1, §9.5).
2. **State intact:** the §9.5 verification — inventory, ledger balance, skills, mission progress, memories — holds exactly.
3. **Physics real:** jump and fall behaviour visibly differs between Prime (9.8), Nexora-7 (3.9), and Kallisto (1.1) as §4.1 specifies — the same input, different worlds.
4. **Atmosphere real:** the suit gate blocks an unsuited landing (§4.3, §7); the airless sky and red-desert haze read differently (§4.3–§4.4).
5. **Cards true:** every info-card value matches `data/planets.json` v1.0 (§3); Nexora-9 offers no landing (§3.4); Prime Moon offers orbit only in v1 (§3.5).
6. **Missions served:** Level 8 missions 8.1–8.4 are completable through this design (§10), and "Space Explorer" unlocks on completion.

---

## 12. What This Document Deliberately Does Not Decide

- **Spaceport site in District 1** — a Phase 8/10 district-design decision (§9.1); the riverfront Launch Terminal is a ferry terminal and is not repurposed by fiat.
- **Transit durations** — tuning at implementation (§9.1); no minutes are fixed here.
- **Off-world base location scheme in the schema** — pending the §8 decision, with a GDD-01 §10 migration note when it lands.
- **Orbital periods / distances** — not in `planets.json` v1.0; the space view is schematic until the data exists (§6).
- **Spacecraft piloting, combat, or a second station** — not in Phase 10 v1; a piloted ship is a later phase's design, not a v1 stretch goal smuggled in here.
- **Suit catalogue entry, base construction costs, resource sale prices** — economy numbers are owned by the economy design (GDD-01 §10: "Concrete wages/prices/rent numbers → Unit F"); this document sets no price, here or anywhere else.
- **Exact dialogue, cutscenes, and training-challenge content** — written during Phase 10 implementation from this structure (the same convention as GDD-04 §6).
- **The station's working name** — "Nexora Station" is proposed (§5); the owner confirms or renames.

---

## Appendix — Cross-Reference Index (verification aid)

Every external reference this document makes, and where it resolves:

- Migration plan Part C #16 (Planets & space) — `NEXORA-MIGRATION-PLAN.md` §Part C, row 16; Part D Phase 10 build line + exit criteria; Part D Phase 8 (travel hubs, airports); Part D Phase 9 (server validates currency, property, inventory).
- `data/planets.json` v1.0 — all five bodies + `nexora_star`; notes field (card order, simulation-inputs rule, transition-sequences rule).
- GDD-04: Level 8 missions 8.1–8.4 (§2), achievement "Space Explorer" Gold (§5), design law "missions are offers" (header), free-roam rule 5 (§4).
- GDD-02: zones `d1_riverfront`, `d1_transport`, `d1_midtown`; Launch Terminal landmark #3 (§4); §8 "No airport (Phase 8 travel)".
- GDD-01: §1 (account vs character, achievements survive death), §2 (identity/skills/reputation), §2.2 (goals), §2.3 (memory), §3 (life stages), §5 (household/property), §6 (family/relationships), §8 (ledger is the truth), §9 (save-game mapping), §10 (what this document does not decide).
- `TECH-SAVE-SYSTEM.md`: §1 (one data model, two stores), §2 (field mapping: `SaveSchemaVersion`, `GameMinutes`, `TimeScale`, `PlayerCharacterId`, `PlayerBalanceCachedNCr`, `TablePayloads`, `PlayerTransform`), §3 (capture/apply, clock + weather round-trip), §4 (versioning & migration).
- `data/schema.sql`: `characters`, `character_skills`, `character_goals`, `character_memories`, `households`, `household_members`, `relationships`, `properties`, `inventory_items`, `economy_ledger`, `mission_progress`, `achievements`, `save_slots`, `world_state`.

*End of GDD-14 v1.0 (Unit AG). Changes happen by PR; a planet-data change happens in `data/planets.json` first, and the cards in §3 follow the file — never the other way round.*
