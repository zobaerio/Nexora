# NEXORA — Asset Licence Register

**Unit I · Version 1.0 · 2026-11-20**
**Parent document:** `docs/QA-PACK.md` §5 — no asset enters the project without a row here.
**Rule:** CC0 is the default for anything new. A paid or restricted licence is recorded with its terms, never assumed. If a licence cannot be verified, the asset is not used — "probably fine" is not a licence.

> **Originality rule (whole project):** NEXORA is an original universe. No Rockstar/GTA assets, code, names or likenesses; no real-brand logos; no ripped assets from other games. Anything that looks borrowed is either CC0 with a source row here, or it does not ship.

---

## 1. How to Add a Row

| Column | What goes in it |
|---|---|
| Asset | File or pack name as it appears in the project. |
| Source | Where it came from — URL, store page, or "authored in-house". |
| Licence | Exact licence (CC0, Fab Standard, Megascans, MIT, proprietary with terms…). |
| Used for | Where in the game (level, system, character). |
| Added | Date + phase (e.g. 2026-11-20, Phase 1). |
| Notes | Restrictions (attribution needed? redistribution limits? expiry?). |

## 2. Register

| Asset | Source | Licence | Used for | Added | Notes |
|---|---|---|---|---|---|
| Godot testbed scripts, scenes, prototype assets (`rupsha-city/`) | Authored in-house (this repo) | Original work, same repo | Systems testbed (preserved) | 2026-11-20, Foundation | No third-party assets in the testbed; primitives + code only. |
| NEXORA design documents & data (`docs/`, `data/*.json`, `data/schema.sql`) | Authored in-house (this repo) | Original work, same repo | Design + data model | 2026-11-20, Units A–I | The owner's spec examples are his own words, quoted in the GDDs. |
| UE project scaffolding (`ue-project/Source/`, `Config/`) | Authored in-house (this repo) | Original work, same repo | UE 5.8 project (uncompiled scaffold) | 2026-11-21, Units D–E | Written to UE 5.8 API conventions; no engine code copied. |
| Phase 1 environment assets (Megascans / Fab — street, park, riverbank) | Quixel Megascans / Fab | Fab Standard Licence (check per-asset at download) | Phase 1 test scene, District 1 | *To be filled when downloaded* | **Do not fill this row from memory.** The owner records the exact pack names + licence text when he downloads them (build sheet Step 7). Until then the scene has no third-party assets. |
| MetaHuman `MH_ZobaerHasan` (owner character) | MetaHuman Creator, built from the owner's spec | MetaHuman / Epic licence (per Epic's MetaHuman terms) | Player character (Phase 2) | *To be filled at creation* | Built from the owner's own likeness with his approval (Phase 2 sheet §3). No third-party face data. |
| Music / SFX | — | — | — | — | **None yet.** Zobvia's rule applies here too: SFX only, licensed or original. A track without a row here is not used. |

## 3. Licences That Are Never Acceptable Here

- "Found on the internet, no licence stated."
- Ripped assets from any commercial game (including GTA — the project was explicitly redirected away from a clone for this reason).
- AI-generated assets with unclear training-data provenance, used as if they were clean. If an AI asset is used, its generator and terms are recorded in the Notes column.
- Any asset whose licence forbids redistribution in a shipped game.

## 4. Audit Cadence

- **Every phase gate** (QA-PACK §2): the register is checked against the project's actual asset list. An asset in the project without a row is a gate failure.
- **Before any public build or release:** full re-check. A public build with an unlicensed asset is the one mistake this register exists to prevent.

*End of ASSET-LICENCE-REGISTER v1.0. Rows are added by PR; nothing is added from memory.*
