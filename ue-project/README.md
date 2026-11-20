# ue-project/ — NEXORA Unreal Engine 5.8 Project

This folder holds the actual UE 5.8 project (`Nexora.uproject`, `Content/`, `Config/`, `Source/`).

**Status:** scaffolding arrives with **Unit D** of the work queue. Until the owner creates/opens the project on his PC (Phase 1 Build Sheet, `docs/PHASE1-BUILD-SHEET.md`), everything here is **uncompiled scaffolding and configuration written in a Linux VM without the engine** — nothing in this folder has been run in Unreal Engine yet, and no file here should be described as "working" until a build on the owner's PC proves it.

## Rules for this folder

- **Engine pin:** Unreal Engine **5.8.x** (latest 5.8 patch). Not 5.9/6.0 previews, not betas. (Master plan Part B.1.)
- **Git LFS is mandatory** — see `.gitattributes` in this folder and Step 4 of the build sheet. Never commit `DerivedDataCache/`, `Intermediate/`, `Saved/`, `Binaries/`.
- **Content layout** (master plan Part E.4):
  - `Content/Nexora/Characters/` — MetaHumans, outfits, animations
  - `Content/Nexora/City/` — Rupsha City districts, buildings, roads
  - `Content/Nexora/Vehicles/` — Chaos vehicles, traffic
  - `Content/Nexora/Environment/` — landscapes, sky/weather, foliage, water
  - `Content/Nexora/UI/` — HUD, menus, Environment Control Panel
  - `Content/Nexora/Audio/` — MetaSounds, ambience
  - `Source/Nexora/` — C++ systems (LifeSim, Economy, Weather, Schedule)
- **Opening the project:** double-click `Nexora.uproject` or open via Epic Launcher → Library. First open on a new machine will compile shaders and may take a long time; that is normal, not an error.
