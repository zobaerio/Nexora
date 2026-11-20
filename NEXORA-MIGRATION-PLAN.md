# NEXORA — Photorealistic Living Universe
## Technical Migration Plan & Development Roadmap

**Date:** 2026-11-20 · **Version:** 1.0 (initial / প্রাথমিক) · **Status:** Planning complete — UE5 build not yet started
**Owner:** MD Zobaer Hasan (@zobaerio) · **First city:** Rupsha City, NEXORA Central

> **Bangla summary:** বর্তমান Godot prototype-টা movement/camera system-এর test — দেখতে cartoon, কারণ ওতে কোনো texture, animation, rig বা realistic light নেই (প্রমাণসহ Part A). Photorealistic NEXORA বানাতে হলে **Unreal Engine 5.8**-এ migrate করতে হবে — MetaHuman, Nanite, Lumen, Megascans এই জগতেই আছে. এই document-এ পুরো migration plan, প্রতিটা subsystem-এর technology + সীমাবদ্ধতা, আর Phase 1–10 roadmap দেওয়া আছে. **UE5-এর কাজটা হবে তোমার PC-তে** — এই VM-এ UE5 চলে না, তাই কোনো UE feature "হয়ে গেছে" বলে দাবি করা হয়নি. কালকের প্রথম কাজ: তোমার PC-র spec check করে Phase 1 শুরু.

---

## 0. Honest Status — What Exists, What Is Proposed, What Needs External Tools

| Category | Items |
|---|---|
| ✅ **Working & tested today** | Godot 4.7.2 prototype (`rupsha-city/`): third-person walk/run/jump, spring-arm camera with wall collision — 8/8 automated headless tests pass; main scene smoke run pass; Windows build `RupshaCity.exe` exported and verified as a file. This is a **systems testbed**, not a visual prototype. |
| 📄 **Designed in this document only** | Everything about UE5, MetaHuman, weather, NPC society, life cycle, economy, multiplayer, planets. None of it is implemented yet. |
| 🖥️ **Requires external tools (owner's PC)** | Unreal Engine 5.8 editor (Windows + discrete GPU), Epic Games account, MetaHuman Creator data, Fab/Megascans downloads, Git LFS storage. Muse's Linux VM cannot run the UE5 editor, compile a UE project, or test MetaHumans — so UE milestones are verified from the owner's build logs, screenshots and packaged builds, never claimed blind. |

---

# PART A — Audit: Why the Current Prototype Looks Cartoon-Like

The current implementation was inspected file by file (2026-11-20). The cartoon look is not one mistake — it is the predictable result of **every visual layer being a placeholder**:

## A.1 Evidence from the actual project

| Layer | What is actually in the project | Visual consequence |
|---|---|---|
| Geometry | Only engine primitives: **3× BoxMesh, 1× CapsuleMesh, 1× SphereMesh**. No imported models at all. | Buildings are boxes, the human is a capsule with a sphere head — the definition of "blocky". |
| Textures | **0 image files** in the whole project (no .png/.jpg/.tga). | No surface detail: no brick, skin, road markings, fabric — flat colour everywhere. |
| Materials | Only `albedo_color` (flat colour) ×4. **No normal maps, roughness, AO, or any PBR map.** | Light cannot react realistically; every surface looks like plastic/clay. |
| Character | Capsule + sphere + a small box "nose". **0 skeletons, 0 bones, 0 animations.** | The character slides/glides when moving — no gait, no arms/legs, no face. A primitive shape can never read as a human, no matter how it is coloured. |
| Animation | **0 animation resources** in scenes and scripts. | Nothing moves except positions: no walk cycle, no idle, no lip movement. |
| Lighting | One directional light + flat ambient; environment background is a **solid colour** (`background_mode = Color`). No sky, sun disc, clouds, fog, or post-processing (no tonemapping profile, bloom, exposure control). | No atmosphere, no depth, no golden hour — the flat "mobile game" look. |
| World | One 80 m × 80 m flat ground plane + 2 wall blocks. No terrain, foliage, props, decals, particles, or audio. | No detail density. Realism is mostly *density of believable detail* — here density is near zero. |
| Rendering setup | Godot Forward+ with default settings; no quality scaling, LOD, or occlusion work (nothing to apply it to). | Even the engine's own high-end features are unused. |

## A.2 Root causes, grouped

1. **Geometry** — primitives instead of modelled/scanned meshes.
2. **Materials** — flat colour instead of PBR texture sets (albedo + normal + roughness + AO) from scans or authored sources.
3. **Lighting & atmosphere** — no sky system, dynamic sun, fog, volumetrics, or colour grading.
4. **Character pipeline** — no skeletal mesh, rig, skin, hair, or animation system at all.
5. **World scale & density** — an 80 m test plane vs. a living city; no streaming, LOD or prop ecosystems.
6. **Engine ceiling for this goal** — Godot can look far better than this prototype does, but the photorealistic-human + scanned-world ecosystem (MetaHuman, Nanite, Lumen, Megascans, motion matching samples, Mass crowds) exists in Unreal Engine, not in Godot. Continuing to polish the capsule would violate the project direction: a slightly better capsule is still a capsule.

## A.3 What the prototype *is* good for (preserve, do not delete)

- It **proved the core control design**: WASD + camera-relative movement, run, jump physics (measured apex ≈ physics prediction), and a spring-arm camera that correctly shortens at walls (4.5 m → 3.04 m in test). These become the **acceptance tests for Phase 3** in UE5.
- It stays in the repo as the systems testbed and design reference, tagged `v0.1-godot-prototype`.
- **What does not carry over:** GDScript code and Godot scenes (different engine/language), and the placeholder primitive assets (no value in UE).

---

# PART B — Engine Decision: Unreal Engine 5.8

## B.1 Verified facts (checked 2026-11-20)

- **Unreal Engine 5.8 is the latest production version**, released 17 June 2026, and is the final planned major version of the UE5 generation; Unreal Engine 6 Early Access is targeted for end of 2027. → **Pin NEXORA to the latest 5.8.x patch. Do not wait for UE6, do not build on a beta.**
- **Licence:** Unreal Engine is free to use; games pay a **5% royalty only on lifetime gross revenue above $1M per product**.
- **MetaHuman** has been **inside the engine since UE 5.6** (Creator, Animator, Mesh-to-MetaHuman) and is **included under the standard Unreal Engine licence — free under $1M annual revenue**, usable even outside Unreal.

## B.2 Comparison for *this* goal

| Criterion | Godot 4.7 | Unity 6 (HDRP) | **Unreal Engine 5.8** |
|---|---|---|---|
| Photoreal humans | No built-in solution | Possible, fragmented tooling | ✅ **MetaHuman** — scanned-data humans, rigged, with hair/clothing |
| Scanned world assets | Manual import only | Asset Store, mixed quality | ✅ **Megascans via Fab** + Nanite (film-quality geometry, no manual LOD) |
| Global illumination | Lightmap/probe based, limited dynamic GI | HDRP GI, more setup | ✅ **Lumen** dynamic GI + reflections, MegaLights for dense city lighting |
| Large open world | Manual chunking | Manual | ✅ **World Partition** + HLOD + PCG built for it |
| Crowd / NPC scale | Custom | DOTS (steep learning curve) | ✅ **Mass framework**, State Tree, Smart Objects, Zone Graph |
| Character animation | Custom/imported | Good | ✅ **Motion Matching** (Game Animation Sample), Control Rig, full IK stack |
| Multiplayer | Custom netcode | Netcode/paid services | ✅ Built-in replication + dedicated server; EOS free |
| Cost to start | Free | Free tier, seat costs at scale | ✅ Free under $1M revenue |
| Hardware demand | Low | Medium | ⚠️ **High** — needs a real GPU workstation (Part F) |
| Solo-dev learning curve | Easiest | Medium | ⚠️ **Steepest** — mitigated by phased plan + Blueprint first |

**Decision: Unreal Engine 5.8 (latest patch), C++ project with Blueprint for gameplay prototyping.**

## B.3 What UE5 gives — and what it does *not* give for free

**Included:** Nanite, Lumen, Virtual Shadow Maps, MegaLights, Sky Atmosphere + volumetric clouds, Water plugin, Chaos physics & vehicles, World Partition streaming, PCG procedural generation, MetaHuman + Animator, Motion Matching sample, Mass AI + State Tree + Smart Objects, MetaSounds, replication.

**Not included (must be built or bought):** a complete weather *system* (UE has the sky/cloud building blocks; rain/snow/storm logic, ground wetness and seasonal change are custom work or a marketplace system such as Ultra Dynamic Sky), a life-simulation (no engine ships birth→death simulation), an economy, a society/government simulation, MMO-scale networking, and any finished city content. This plan never claims otherwise.

---

# PART C — Subsystem Matrix

Complexity: 1 = days, 3 = a phase of focused work, 5 = research-grade / multi-phase. Every limitation below is stated deliberately — these are the places projects like this usually lie to themselves.

| # | Subsystem | Technology (UE5.8) | External dependencies | Complexity | Honest limitation |
|---|---|---|---|---|---|
| 1 | Realistic humans | **MetaHuman Creator** (in-engine), grooms (hair), MetaHuman clothing; custom outfits via Blender/Marvelous Designer | Epic account; Fab for outfits | 3 | MetaHuman faces/bodies are adult-based. **Children and true elderly are not provided** — life stages need custom meshes/variants (see #9). High-quality MetaHumans are heavy: crowds must use lower-LOD / Mass representations, not full MetaHumans. |
| 2 | Character animation | **Motion Matching** (Game Animation Sample Project), Animation Blueprints, Control Rig, IK Rig / full-body IK | Sample project (free from Epic) | 3 | Motion Matching quality depends on its animation database; custom actions (sitting, working, driving) need extra animation sets — bought or captured. |
| 3 | Motion capture | **MetaHuman Animator** (video + audio capture from a phone/webcam), Live Link Face | Optional: Rokoko / Xsens suit (paid) for body mocap | 2–4 | Phone capture is good for face/upper body, not stunt-grade full body. Suits cost real money and need calibration skill. |
| 4 | Materials & lighting | **Lumen** GI, **Nanite**, Virtual Shadow Maps, PBR materials from **Megascans (Fab)** | Fab account; some packs paid | 2 | Lumen + Nanite at city scale needs GPU budget discipline (Part F); scanned assets are large — project size grows to hundreds of GB over phases. |
| 5 | Terrain & large world | **Landscape**, **World Partition** + Data Layers + HLOD, **PCG** for forests/props, Runtime Virtual Textures | Megascans foliage | 4 | World Partition streams well but does not remove the need for art direction; a *believable* city is content work, not a generator setting. |
| 6 | Day-night & weather | **Sky Atmosphere**, volumetric clouds, directional-light/sun position by game clock, custom **Weather Manager** (rain via Niagara particles + wetness materials, fog, wind); alternative: marketplace Ultra Dynamic Sky | Niagara assets; optional UDS (paid) | 3 | No complete weather system ships with UE. Snow accumulation, storm damage, and seasons are custom effects layered over time — Phase 4 scope keeps them visual, not simulated physics. |
| 7 | Vehicles & traffic | **Chaos Vehicles**, traffic on **Zone Graph** lanes with Mass traffic, spline fallback for simple cars | Vehicle models (Fab / own) | 3 | Chaos Vehicles need per-vehicle tuning; dense traffic + physics cars is a performance budget item, so distant traffic must be Mass-simulated, not full physics. |
| 8 | NPC AI & society behaviour | **Mass AI** (crowds), **State Tree** (decisions), **Smart Objects** (benches, counters, desks), Zone Graph (pedestrian lanes), custom schedule system (home → work → leisure) | — | 4 | Mass entities are lightweight representations; a "full" NPC with inventory, dialogue and memory is an Actor and costs far more — the design must tier NPCs (ambient / scheduled / full) from Phase 6. |
| 9 | Life stages & aging | Custom **LifeStage system**: discrete stage assets (child/teen/adult/elder variants), scale + posture + material aging (wrinkle/grey via material parameters on MetaHuman adults), life-clock data | Custom child/elder character assets (hardest content gap) | 5 | **No engine feature ages a human from birth to death.** Realistic approach: stages are separate, authored variants swapped at thresholds, with continuous tweaks (height, hair grey, posture) inside the adult band. Child characters need responsibly sourced custom assets — flagged as the project's hardest content problem, scheduled late (Phase 7) for that reason. |
| 10 | Family & relationships | Custom data model (households, kinship, relationship scores, memories) driving State Tree behaviour; events (marriage, children, inheritance) as simulation events | Backend DB from Phase 9 for players | 4 | Relationship *simulation* is design + data work; making it *visible* believably (animation, dialogue) is the expensive part, so Phase 7 starts with NPC families, not player families. |
| 11 | Education & careers | Custom progression systems: skill trees, job roles as gameplay loops (the owner's example — Civil Engineer: plan → estimate materials → supervise build → get paid — maps directly onto construction gameplay), workplaces as Smart Object sites | Workplace interiors (Phase 5 content) | 3–4 | Each profession that is *playable* is a small game of its own. Plan: 3 playable professions first (Civil Engineer, Shop Owner, Taxi Driver), others NPC-only until later. |
| 12 | Housing & property | Buildable/buyable property actors, interior customisation (furniture placement system), land plots as data; construction via staged building actors | Interior/furniture assets (Fab) | 3 | Full free-form building (Sims-grade) is a big system; Phase 5/6 scope: buy → furnish from catalogue → upgrade tiers. Free building comes later if at all. |
| 13 | Business & economy | Server-authoritative economy simulation: prices, wages, business ledgers, supply/demand ticks; NPC ambience via Mass | Backend (Phase 9) for multiplayer; local simulation before that | 4 | A believable economy is a simulation-design problem, not graphics. Start crude (fixed wages/prices + simple demand) and iterate; never fake it with random numbers presented as a "living economy". |
| 14 | Persistence & profiles | Dedicated server + **PostgreSQL** backend (accounts, character, inventory, balance, property, profession, missions, friends, achievements); server validates every currency/property change (owner's security rule) | Server hosting (Phase 9, paid), EOS or own auth | 4 | Must be designed from Phase 6 data models onward, even while single-player, so multiplayer does not require a rewrite. |
| 15 | Multiplayer | UE **replication**, dedicated server builds, session/travel via EOS (free) or Steam; instancing/sharding per city district | Hosting, EOS/Steam accounts | 5 | UE replication is **not** an MMO netcode: realistic target is tens to ~100 concurrent players per server instance. "One world for everyone" means sharded districts with seamless-ish travel — an architecture decision, not a checkbox. |
| 16 | Planets & space | Separate World Partition maps per planet, scaled space scene, travel = loading/transition sequence, per-planet data cards (gravity/temperature/atmosphere/resources as *simulation inputs*, e.g. gravity changes jump physics) | Planet surface assets | 4 | Seamless ground-to-orbit flight in one world is not realistic at this scale; transitions are the honest design. Planets start as exploration sites, not full living worlds. |
| 17 | NPC dialogue (AI) | Rule/State-Tree dialogue first; optional LLM-backed dialogue for key NPCs later (API cost + online requirement + moderation) | LLM API (paid, optional) | 3 | LLM dialogue is a *later, optional* layer. Core NPCs must work fully offline with authored lines, so the world never depends on an API to feel alive. |
| 18 | Audio | **MetaSounds** (engines, weather, ambience), MetaHuman Animator voice/lip-sync, licensed/CC0 ambience libraries | Audio libraries (Fab/CC0) | 2 | Voice acting at society scale is a production problem; start with ambience + key NPC lines. |

---

# PART D — Development Phases 1–10

Each phase ends with a **playable, testable build** and written exit criteria. A phase is not "done" because it looks good in a screenshot — it is done when its exit criteria pass in a packaged build.

## PHASE 1 — Photorealistic Environment Test ⭐ *First achievable milestone*
- **Goal:** Prove the visual target on the owner's hardware before anything else is built.
- **Build:** One ~400 m × 400 m scene: a street corner + park + riverbank in Rupsha City style. Megascans surfaces/foliage, Nanite on, Lumen on, Sky Atmosphere with a full day cycle (24 h compressed to ~5 min), rain on/off toggle, wet ground in rain, wind in trees. Free camera + walk camera. Performance overlay (fps, frame time).
- **Exit criteria:** Packaged Windows build runs on the owner's PC; stable **≥ 30 fps at 1080p on High** (target 60 on the recommended spec, Part F) with no traversal hitches that break immersion; day cycle and rain visibly change the scene; owner approves the look as "the NEXORA standard".
- **Tools/assets:** UE 5.8, Megascans (Fab), one free/paid city-street asset pack if needed, Quixel/Fab foliage.
- **Not in this phase:** Characters, vehicles, gameplay, interiors.

## PHASE 2 — Realistic Human Character
- **Goal:** One MetaHuman player character that looks and moves like a person.
- **Build:** MetaHuman created in Creator (owner's design), groom hair, 2 outfits, imported to the Phase 1 scene; idle/walk/run from Motion Matching sample; MetaHuman Animator face test (webcam/phone clip → facial animation + lip sync on a test line).
- **Exit criteria:** Character walks through the Phase 1 scene in a packaged build; no obvious foot sliding at walk/run; close-up face passes owner's "not cartoon" test.
- **Not in this phase:** Crowds, NPC behaviour, child/elder characters.

## PHASE 3 — Movement, Collision, Camera, Interaction
- **Goal:** Port the *proven control design* from the Godot testbed to UE, to the same acceptance standards.
- **Build:** Third-person controller (Enhanced Input), camera boom with wall collision (same behaviour the Godot test verified: boom shortens at walls instead of clipping), interaction system (doors, sit, enter vehicle placeholder), footstep sounds, head/eye-level polish.
- **Exit criteria:** UE versions of the Godot prototype's tests pass by hand + recorded checklist: walk/run speeds match design values, jump apex consistent, camera never clips through the test walls, interaction prompts work on 5 test objects.
- **Carry-over:** Controls table and test list from `rupsha-city/tests/player_test.gd` are the spec.

## PHASE 4 — Dynamic Day-Night & Weather System
- **Goal:** The world clock and weather from the owner's spec, as real systems.
- **Build:** Game clock (adjustable speed), sun/moon by clock, city lights on at dusk (MegaLights), Weather Manager: clear / rain / storm (lightning + thunder audio) / fog / wind / cloudy; snow only in zones flagged for it later. **Environment Control Panel** (dev + player-facing in sandbox mode) to set time/weather/wind — virtual environment only, exactly as the owner specified.
- **Exit criteria:** 24 h cycle runs without lighting pops; storm visibly and audibly distinct; control panel changes apply live; weather state saves/loads.

## PHASE 5 — A Small Living City (Rupsha City — District 1)
- **Goal:** First real place: not the biggest map, the most *believable* one.
- **Build:** ~1 km² district: roads with markings/signals, residential + apartment blocks, market/shops with interiors for key buildings, school, clinic, bank, park, riverfront; 3 drivable vehicles + simple traffic; property system v1 (buy/rent one apartment, furnish from catalogue); first playable profession loop — **Civil Engineer job chain** (plan → materials estimate → supervise staged construction → payment) using the owner's own domain as the flagship profession.
- **Exit criteria:** Player can live one full in-game day: wake at home → travel → work a job → earn → shop → return home; traffic runs 10 min without gridlock; packaged build stable.

## PHASE 6 — NPC Society, Professions, Relationships, Economy v1
- **Goal:** The city stops being a set and becomes a society.
- **Build:** Tiered NPCs (ambient Mass crowds → scheduled NPCs with home/work/leisure State Trees and Smart Objects → a cast of ~25 full NPCs with names, jobs, relationships, simple memories); economic classes as *starting conditions + opportunity systems* (exactly per owner's framing: a game system, never a statement about real people's worth); 3 playable professions (Civil Engineer, Shop Owner, Taxi Driver), other professions NPC-run; economy v1: wages, prices, rent, business ledgers, save/load of all of it (data model built to the Phase 9 server schema from day one).
- **Exit criteria:** 30 in-game days of accelerated simulation run without economy collapse or NPC schedule deadlocks; full NPCs remember the player's job and past interactions at a basic level; save/load preserves society state.

## PHASE 7 — Life Stages, Families, Aging, Inheritance
- **Goal:** The life cycle — the heart of the owner's vision, and the hardest content problem in the project.
- **Build:** LifeStage system for **NPCs first**: stage variants (child/teen/adult/elder), family households, school attendance for children, careers for adults, retirement, death + inheritance of property/currency to family, aging visuals inside the adult band (hair grey, posture, material aging). Player aging arrives after NPC aging is proven.
- **Exit criteria:** A simulated family runs 3 generations in accelerated time with correct inheritance and no orphaned data; stage transitions never visibly "pop" (transition at sleep/night boundary with a presented time-skip).
- **Honest gate:** This phase cannot start until the child/elder character-asset problem (Part C #9) is solved with responsibly sourced assets. If it cannot be solved to standard, the phase ships with teen→elder only and says so.

## PHASE 8 — Multiple Districts & Cities
- **Goal:** Scale the world horizontally with World Partition.
- **Build:** Rupsha City grows to multiple districts with distinct architecture/economy; second city with different climate/architecture; travel by road/train/flight (transition-based); per-district data layers and HLOD tuned; airports/stations as functional travel hubs.
- **Exit criteria:** Travel between cities works in a packaged build; frame budget holds in the densest district; each city is visibly and economically distinct.

## PHASE 9 — Persistent Online Multiplayer
- **Goal:** Other real people in the same city — with the owner's security rule enforced: **the server, never the client, validates currency, property and inventory.**
- **Build:** Dedicated server, account/character backend (PostgreSQL), EOS-based sessions/friends, district instancing, co-op missions, shared vehicles (passengers), text chat with moderation basics, persistence of everything in the owner's list (Account/Character ID, inventory, balance, properties, profession, missions, friends, achievements).
- **Exit criteria:** Two clients on different networks live in the same district for a 1-hour session: see each other, ride together, complete a co-op job, and both players' balances/properties are correct after relog — with all changes server-validated.
- **Reality note:** Concurrent-player target is set by testing (tens per instance first). Marketing language must never promise MMO scale the build has not demonstrated.

## PHASE 10 — Other Regions & Planets
- **Goal:** The universe beyond the first planet.
- **Build:** Space station hub, 2 planets (desert/red, ringed giant's moon) as separate worlds with their own gravity/atmosphere parameters actually affecting physics and visuals, planet info cards (gravity, temperature, atmosphere, surface, resources, exploration status), landing/base-building v1, orbital animation and time-speed controls for the space view.
- **Exit criteria:** Player travels city → station → planet surface → builds a small base → returns, with inventory and character state intact throughout.

---

# PART E — Migration Process (from the current project to UE5)

1. **Preserve (done in this repo):** Godot prototype kept intact, local git tag `v0.1-godot-prototype`; this plan + the earlier prototype plan stay as the design record. Nothing is deleted or overwritten.
2. **Identity carry-over:** NEXORA is the universe; **Rupsha City** (the Godot prototype's city) becomes NEXORA's first city. Character identity from the owner's spec (name, username, profession, residence, balance in Nexora Credits) becomes the player-profile data model — designed in Phase 5, persisted in Phase 9.
3. **On the owner's PC (tomorrow's session):** Install Epic Games Launcher → UE **5.8.x (latest patch)** with MetaHuman Creator Core Data → create C++ project `NEXORA` (Third Person base, but as a foundation only — not the final character) → enable plugins: MetaHuman, PCG, Mass (Gameplay/AI), State Tree, Smart Objects, Zone Graph, Chaos Vehicles, Water, Niagara → set up **Git + Git LFS** (UE projects are binary-heavy; `.gitattributes` for uasset/umap/fbx/png/exr) — Epic's open-source **Lore** VCS (announced 2026) is a future option to evaluate, Git LFS is the proven start.
4. **UE project structure:** `Content/Nexora/{Characters, City, Vehicles, Environment, UI, Audio}`, `Source/Nexora` for C++ systems (LifeSim, Economy, Weather, Schedule), `Docs/` mirroring this repo's plans.
5. **Muse's role in UE phases:** write/review C++ and Blueprint logic as text, asset lists, configuration, test checklists, and verify from build logs/screenshots/packaged builds the owner shares. Muse does **not** claim a UE feature works until that evidence exists (project rule, Part 0).

---

# PART F — Hardware & Skills

## F.1 Development workstation (owner's PC — to be checked tomorrow)

| | Minimum (Phase 1 possible) | Recommended (Phases 5+ comfortable) |
|---|---|---|
| GPU | RTX 3060 12 GB / RX 6700 XT | RTX 4070 Super / 4080 or better |
| CPU | 6-core (Ryzen 5 5600 / i5-12400) | 8+ core (Ryzen 7 / i7) |
| RAM | 32 GB | 64 GB |
| Storage | 1 TB NVMe SSD (≈300 GB free for engine + project growth) | 2 TB NVMe SSD |
| OS | Windows 11 | Windows 11 |

Player target for the shipped game will be set from Phase 1/5 performance captures — never promised before measurement. UE5 photoreal projects are known to risk traversal stutter on weak optimisation; the frame budget is therefore an exit criterion in every phase, not an afterthought.

## F.2 Skills roadmap (owner + Muse together)

Blueprint visual scripting → UE C++ for systems → MetaHuman pipeline → Mass/State Tree → replication (Phase 9). The owner already thinks in systems (CivilOS); the Civil Engineer profession loop is deliberately Phase 5's flagship because it uses his real expertise as a design advantage no other life-sim has.

---

# PART G — Costs (honest ranges, estimates — not quotes)

| Item | Cost |
|---|---|
| Unreal Engine 5.8, MetaHuman, EOS | **Free** (5% royalty only if a product passes $1M lifetime revenue) |
| Megascans via Fab | Much is free to claim; some packs paid — check each listing's licence and keep an asset-licence register |
| Marketplace city/vehicle/animation packs (optional accelerators) | Paid per pack; buy only against a phase's asset list, never speculatively |
| Motion capture | Phone/webcam (MetaHuman Animator): free · Rokoko-class suit: paid hardware, Phase 2+ only if needed |
| Multiplayer hosting (Phase 9) | Real monthly server cost once testing with external players starts; local/LAN testing before that is free |
| UE project storage/backups | Git LFS free tier is small; budget for LFS data packs or self-hosted storage as the project grows |

---

# PART H — Risks & Reality Check

- **Scale honesty:** The full NEXORA vision is a multi-year, team-scale product. This roadmap's job is to make every phase a *finished, shippable milestone* on the way, so the project is real at every step — not a decade of promises. A solo developer + AI assistance can credibly reach Phases 1–6 over time; Phases 7–10 are where collaborators, funding, or both become a genuine question, and the plan says so now rather than later.
- **The child/elder asset gap** (Part C #9) is the single hardest content problem and gates Phase 7.
- **Performance** is a design constraint from Phase 1, with measured budgets — not a final-phase surprise.
- **Licence discipline:** every external asset gets a register entry (source, licence, date). No ripped game assets, ever — the same rule as the Godot prototype.
- **Scope gates:** no phase starts until the previous phase's exit criteria pass in a packaged build. New ideas go into the current phase's backlog document, not into the phase.

---

# PART I — Tomorrow's Session (owner returns)

1. ☐ Owner's PC specs check (GPU / RAM / SSD free space) — decides Phase 1 quality targets
2. ☐ Epic Games account + Launcher + **UE 5.8.x** install (with MetaHuman Creator Core Data)
3. ☐ `NEXORA` UE project creation + plugin setup + Git LFS init (Muse provides the step-by-step sheet and `.gitattributes`)
4. ☐ Phase 1 asset list download (Megascans street/park/riverbank set)
5. ☐ Phase 1 build begins — Muse supplies the scene checklist and performance capture sheet

*End of plan v1.0 — 2026-11-20. This document will be revised after Phase 1's performance capture, with measured numbers replacing estimates wherever they appear.*
