# NEXORA — Phase 1 Build Sheet
## Photorealistic Environment Test · Owner's PC · Unreal Engine 5.8

**Unit A · Version 1.0 · 2026-11-20**
**Parent document:** `NEXORA-MIGRATION-PLAN.md` Part D, Phase 1 — this sheet is the step-by-step execution of that phase. If this sheet and the master plan disagree, the master plan wins and this sheet gets a revision PR.

> **What Phase 1 is:** one ~400 m × 400 m photorealistic scene (street corner + park + riverbank, Rupsha City style) that proves the visual target and measures performance on the owner's real hardware.
> **What Phase 1 is not:** no characters, no vehicles, no gameplay, no interiors. Anyone who adds those mid-phase breaks the scope gate (master plan Part H).

---

## Step 0 — PC Spec Check (15 minutes, do this first)

Phase 1 quality targets depend on the actual machine. Record the results in the table in Step 9 of this sheet and send them back to Muse (screenshot of each tool is fine).

| Check | How (Windows 11) | Record |
|---|---|---|
| GPU model + VRAM | Task Manager → Performance → GPU (name + "Dedicated GPU memory") | |
| CPU model + cores | Task Manager → Performance → CPU | |
| RAM total | Task Manager → Performance → Memory | |
| Free SSD space on the install drive | File Explorer → This PC | |
| Windows version | Settings → System → About | |

**Decision rules (from master plan Part F):**
- GPU ≥ RTX 4070-class / RAM 64 GB → build and capture at **High**, target 60 fps.
- GPU RTX 3060 12 GB-class / RAM 32 GB → build at High, capture at High **and** Medium; the Phase 1 floor is ≥ 30 fps at 1080p High.
- Below the minimum column → stop and tell Muse before installing anything; the plan gets revised first (cloud workstation or hardware decision is the owner's).

Disk budget before installing: Epic Launcher (~1 GB) + UE 5.8 with MetaHuman data (~120–160 GB depending on options) + project growth. **Keep ≥ 300 GB free.**

---

## Step 1 — Epic Games Account + Launcher

1. Create / sign in to an **Epic Games account** (epicgames.com) — this account owns the engine licence, Fab library and later EOS services. Use an account the owner controls permanently; do not use a borrowed or throwaway account.
2. Download and install the **Epic Games Launcher** (Windows).
3. In the Launcher, sign in and open the **Unreal Engine → Library** tab.
4. Accept the Unreal Engine EULA when prompted. (Licence facts: free to use; 5% royalty only above $1M lifetime gross revenue per product — master plan Part B.1.)

## Step 2 — Install Unreal Engine 5.8.x

1. Click **Install Engine**, choose version **5.8.x — the latest 5.8 patch offered**. Do **not** install 5.9/6.0 previews or any beta; NEXORA is pinned to the 5.8 generation (final planned UE5 major; UE6 Early Access is end-2027 and is not a target).
2. In **Options** for the install, make sure these are selected:
   - **Core Components** (default)
   - **MetaHuman Creator Core Data** — required for the in-engine MetaHuman Creator (Phase 2); installing it now avoids a second large download later.
   - **Templates and Feature Packs** (needed for the Third Person base and sample content)
   - **Target platforms:** Windows only for now (Android/Linux support adds tens of GB; add later only when a phase needs it)
   - Engine source code: **not** required (only needed for console/dedicated-server-from-source work; Phase 9 will revisit).
3. Install to an **NVMe SSD** path without spaces if possible, e.g. `D:\UE\UE_5.8`.
4. Launch the editor once from the Library tab to confirm it opens, then close it.

## Step 3 — Create the Project

The project lives in this repo at `ue-project/` (scaffolding arrives with Unit D; if Unit D has already landed, open the existing `ue-project/Nexora.uproject` instead of creating a new one and skip to Step 5).

If creating fresh:
1. Launcher → Unreal Engine → **Create Project** → **Games → Third Person**.
2. Settings: **Blueprint + C++ both available** — choose the **C++** project type (gameplay starts in Blueprint, systems move to C++; master plan Part E).
3. Name: **Nexora** · Location: the repo's `ue-project/` folder (clone this repo first — Step 4).
4. Quality: **Maximum** · Ray tracing: **off at project creation** (NEXORA uses Lumen software ray tracing by default; hardware ray tracing is a per-scene decision, not a project default).
5. Starter content: **off** (Phase 1 uses Megascans/Fab assets, not starter content).
6. Create, let it compile shaders/open, then close the editor.

## Step 4 — Git + Git LFS Setup

The UE project is binary-heavy; plain git will choke on it. This repo already carries `ue-project/.gitattributes` with LFS rules — do not replace it.

On the owner's PC, from a terminal inside the repo clone:

```bat
git lfs install
git lfs track "*.uasset" "*.umap"   :: should report "already supported" via .gitattributes
git lfs pull
```

Rules that matter:
- **Never** commit `ue-project/DerivedDataCache/`, `Intermediate/`, `Saved/` or `Binaries/` — the repo `.gitignore` + project ignores cover this; if a file from those folders ever appears in `git status`, stop and fix the ignore rules before committing.
- Commit early and small: after each numbered scene step in Step 7, one commit on a working branch, PR to `main` when the step's checklist passes.
- LFS storage grows fast with Megascans. Watch the repo's LFS quota; the fallback is self-hosted LFS or a separate asset repo (master plan Part G) — decide with Muse when the first warning appears, not after a failed push.

## Step 5 — Project Settings (set once, before building the scene)

Editor → **Edit → Project Settings**:

| Setting | Value | Why |
|---|---|---|
| Maps & Modes → Default Map | `L_Phase1_Environment` (created in Step 7) | The phase's only map |
| Rendering → Global Illumination | **Lumen** (Dynamic Global Illumination Method = Lumen) | Master plan lighting stack |
| Rendering → Reflections | **Lumen** | Consistent reflections with GI |
| Rendering → Virtual Shadow Maps | **Enabled** | Nanite-grade shadow quality |
| Rendering → Nanite | Enabled (default in 5.8) | Megascans geometry without manual LODs |
| Rendering → Default Post Processing | Auto Exposure **on**, bias tuned per capture | Day-cycle needs exposure adaptation |
| Engine → Garbage Collection | default | Do not tune in Phase 1 |
| Plugins | see Step 6 | |

Also set **Editor Preferences → Appearance → Show Frame Rate and Memory** off — performance is measured in the packaged build (Step 9), not the editor.

## Step 6 — Plugin List

Editor → **Edit → Plugins**. Enable, then restart the editor when asked:

| Plugin | Needed for | Phase |
|---|---|---|
| MetaHuman + MetaHuman Creator | Realistic humans | 2 (enable now; data already installed) |
| PCG (Procedural Content Generation) | Park foliage/props scattering | 1 (park), 5+ |
| Water | Riverbank water body | 1 (riverbank), 5+ |
| Niagara | Rain particles | 1 (rain toggle), 4 |
| Mass Gameplay + Mass AI | Crowds/traffic later | 6 (enable at Phase 6, not now) |
| State Tree, Smart Objects, Zone Graph | NPC behaviour/traffic later | 6 (enable at Phase 6) |
| Chaos Vehicles | Drivable vehicles | 5 (enable at Phase 5) |
| Enhanced Input | **On by default** — the only input system NEXORA uses | 3 |

Phase rule: enabling a plugin early "to save time" is how projects accumulate broken dependencies. Enable at the phase listed, except MetaHuman/PCG/Water/Niagara which Phase 1–2 need.

## Step 7 — Scene Build Checklist (in order)

Map: create `Content/Nexora/Environment/Phase1/L_Phase1_Environment`. This is a **single level, not World Partition** — 400 m × 400 m does not need streaming yet (World Partition arrives with District 1 scale, Phase 5).

Build in this order — each step is a commit point:

- [ ] **7.1 Ground base.** One Landscape (or a flat sculpted plane for the test) sized ~400 m × 400 m, with a gentle bank sloping to the river edge on one side. No World Partition, no data layers.
- [ ] **7.2 Sky + light rig.** Place: **Sky Atmosphere**, **Directional Light** (the sun; movable, cast shadows, use as atmosphere sun), **Sky Light** (real-time capture), **Volumetric Cloud**, **Exponential Height Fog** (light settings). This rig is the Phase 4 weather system's foundation — name actors exactly: `Sun_DirectionalLight`, `SkyAtmosphere`, `SkyLight`, `VolumetricCloud`, `HeightFog`.
- [ ] **7.3 Street corner.** Road cross: two asphalt roads crossing, concrete sidewalks, kerbs, one painted crossing. Layout sketch: roads along X and Y through the middle of the map; buildings plots are *implied* by frontage walls/hedges in Phase 1 — no full buildings yet.
- [ ] **7.4 Park quadrant.** Grass area with PCG-scattered trees + bushes, 2 benches, 1 path. This is the foliage density test — if fps dies anywhere, it dies here first, which is the point.
- [ ] **7.5 Riverbank quadrant.** Water plugin **single-layer water body (river)** along the bank edge, mud/rock bank materials, a short wooden/concrete ghat-style steps down to the water (Rupsha flavour), reeds at the waterline.
- [ ] **7.6 Materials pass.** Every surface uses the Megascans PBR sets from Step 8 (albedo + normal + roughness). **No flat-colour placeholder materials survive this step** — flat colour is exactly the cartoon failure audited in the master plan Part A.
- [ ] **7.7 Day cycle.** Level Blueprint or a small Blueprint actor `BP_DayCycleDriver`: rotates `Sun_DirectionalLight` through 24 h compressed to **5 minutes**, updates Sky Atmosphere; at dusk (in-game ~18:30) the street lamps (Step 7.8) fade on. (The production system is Unit E's C++ clock/weather; this Blueprint driver is Phase 1's disposable proof.)
- [ ] **7.8 Street lamps.** 6–8 lamp posts along the roads (simple meshes + SpotLight/RectLight, MegaLights-ready), emissive heads at night.
- [ ] **7.9 Rain toggle.** Niagara rain particle system around the camera + a key/button toggle (`R` in the test build): rain on/off, ground materials switch to wet look via a **Material Parameter Collection** scalar (`Wetness` 0→1 raising material gloss/lowering roughness on road + sidewalk materials), fog density slightly up while raining.
- [ ] **7.10 Cameras.** Two ways to view: **free-fly camera** (editor-style, for inspection) and a **walk camera** at eye height 1.7 m on the street corner (no character body yet — Phase 2 adds the MetaHuman; this is a camera on a simple pawn). Default start: walk camera.
- [ ] **7.11 Performance overlay.** In the packaged build only: `stat fps` + `stat unit` available via console, and a fixed camera path (a spline the walk camera follows on keypress `P`) so captures in Step 9 are repeatable.

## Step 8 — Phase 1 Asset List (Megascans via Fab)

Claim/download **only** this list for Phase 1. Record every asset in the licence register (template arrives with Unit I; until then keep the Fab receipts/links in a note). Search terms are for Fab/Megascans; pick the variant whose licence is the standard Fab/Megascans-for-Unreal licence and note it.

### Surfaces (3D / surface scans)
| Need | Search for | Used on |
|---|---|---|
| Asphalt with wear | Megascans surface "asphalt road" / "damaged asphalt" | Roads (7.3) |
| Concrete pavement slabs | "concrete sidewalk" / "pavement tiles" | Sidewalks, ghat steps |
| Brick wall (aged) | "old brick wall" surface | Frontage walls (7.3) |
| Grass ground | "grass ground" / "meadow ground" surface | Park (7.4) |
| Mud / wet earth | "mud" / "river bank" surface | Riverbank (7.5) |
| Sand-gravel mix | "gravel" surface | Path edges, bank |

### Nature / props (3D plants & objects)
| Need | Search for | Used on |
|---|---|---|
| 2 tree species, 2–3 variants each | Megascans trees (temperate broadleaf) | Park + street rows |
| Bushes / shrubs ×2 types | Megascans bushes | Park, frontage |
| Grass tufts / ground foliage | Megascans foliage scatter | Park, verges |
| River rocks ×3 sizes | Megascans rocks | Bank, waterline |
| Reeds / waterside plants | Megascans waterside foliage | Waterline (7.5) |
| Wooden bench | Fab free/standard prop "park bench" | Park (7.4) |
| Street lamp post | Fab prop "street lamp" (or build from primitives + emissive head — geometry detail is fine here, materials carry realism) | Roads (7.8) |
| Kerb stones / road props | Megascans "concrete curb" or simple geometry with concrete surface | Roads |

### Audio (Phase 1 minimal)
| Need | Source |
|---|---|
| Rain loop, light wind, river ambience | CC0 libraries (e.g. Freesound CC0) — licence-noted; ambience sells weather more than any visual |

**Explicitly not for Phase 1:** building packs, vehicle packs, character clothing, weapon/props packs. Buying ahead of the phase that needs them is banned by the master plan's cost discipline (Part G).

## Step 9 — Performance Capture Sheet

Measure in a **packaged Windows build** (Project Launcher → Windows → Shipping or Development; Development is fine for Phase 1 captures), never in the editor. Fixed path: use the `P` camera spline (7.11), 3 runs per configuration, record the median.

**Machine under test** (from Step 0): GPU ______ · CPU ______ · RAM ______ · Driver ______

| # | Location on path | Scalability | Resolution | Avg FPS | 1% low FPS | Frame time (ms) | GPU time (ms) | Draw calls | Triangles | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Street corner, noon, clear | High | 1920×1080 | | | | | | | |
| 2 | Street corner, noon, clear | Epic | 1920×1080 | | | | | | | |
| 3 | Park (densest foliage), noon | High | 1920×1080 | | | | | | | |
| 4 | Riverbank looking across scene | High | 1920×1080 | | | | | | | |
| 5 | Street corner, dusk (lamps on) | High | 1920×1080 | | | | | | | |
| 6 | Street corner, rain on | High | 1920×1080 | | | | | | | |
| 7 | Full day-cycle run (5 min) | High | 1920×1080 | | | | | | | watch for hitches at transitions |
| 8 | Owner's native resolution, preferred settings | — | native | | | | | | | the honest "how it feels" row |

Scalability reference (Editor/Project settings → Scalability, or console `sg.*`): groups are **ViewDistance, AntiAliasing, PostProcessing, Shadows, GlobalIllumination, Reflections, Textures, Effects, Foliage**. For each capture row, note any group changed from the preset. If High fails the floor (Step 10), the first knobs, in order: Foliage density (7.4), Shadow quality, Lumen GI quality, Volumetric Cloud quality — in that order, re-capturing after each single change.

**Send back to Muse:** this table filled + one screenshot per row + the packaged build's log if anything crashed. Those become the measured numbers that replace estimates in Roadmap v1.1 (Unit J).

## Step 10 — Phase 1 Exit-Criteria Checklist

Copied from the master plan (Part D, Phase 1) — **all** boxes must pass in the packaged build:

- [ ] Packaged Windows build runs on the owner's PC without crashes for a full day-cycle run (≥ 5 min) plus 10 min of free inspection.
- [ ] **≥ 30 fps at 1080p on High** sustained on the Step 9 path (target 60 fps on recommended-spec hardware) — from the capture sheet, not from feel.
- [ ] No traversal hitches that break immersion on the fixed camera path (row 7 notes clean, or hitches explained and filed as Phase 5 optimisation tasks).
- [ ] Day cycle visibly changes the scene: sunrise, noon, sunset, night with lamps on — screenshots at 06:00 / 09:00 / 12:00 / 17:00 / 19:00 / 00:00 in-game times.
- [ ] Rain toggle visibly changes the scene: particles, wet ground, fog — screenshots rain on/off from the same camera.
- [ ] Wind visibly moves tree foliage.
- [ ] **Owner approves the look as "the NEXORA standard"** — this is a human gate; Muse does not self-approve it.
- [ ] Capture sheet (Step 9) filled and returned; asset licence notes collected.

When every box passes: Phase 1 is DONE, Phase 2 (MetaHuman sheet, Unit H) unlocks. If the fps floor fails after the Step 9 knob order, Phase 1 is **not** done — the scene gets lighter, not the criteria.

---

*End of Phase 1 Build Sheet v1.0. Revisions happen by PR against this file, with the capture numbers attached.*
