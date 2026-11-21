# NEXORA — Phase 2 MetaHuman Build Sheet

**Unit H · Version 1.0 · 2026-11-20**
**Parent documents:** `NEXORA-MIGRATION-PLAN.md` Phase 2 · `docs/PHASE1-BUILD-SHEET.md` (Steps 1–6: install, project, plugins — MetaHuman is enabled there) · `docs/GDD-01-LIFE-AND-DATA-MODEL.md` §2–§3 (identity, life stages, the child/elder asset gate) · `docs/GDD-02-RUPSHA-CITY-DISTRICT1.md` (District 1 population)
**Status:** a build sheet for the owner's PC. Nothing here is built yet — the first MetaHuman is created by following these steps in MetaHuman Creator and Unreal Engine on his machine.

---

## 1. What Phase 2 Has to Prove

Phase 2's exit criterion (master plan Part D): **one realistic player character, built from the owner's spec, walking in the Phase 1 environment, with face-capture animation working in a test**. That is the whole phase. A crowd system, a character creator UI, and child/elder variants are later phases — they are not Phase 2, and starting them here is how the phase slips.

**The honest limitation, stated again:** MetaHuman has no child or elder presets (master plan Part C #9). Children and elders in NEXORA are **authored stage-variant assets**, not aged MetaHumans. Phase 2 does not solve that; it proves the adult pipeline and records the gate for Phase 7.

## 2. Prerequisites (from the Phase 1 Build Sheet)

- [ ] UE 5.8.x installed, project `ue-project/Nexora.uproject` open (Phase 1 done).
- [ ] **MetaHuman plugin enabled** (build sheet Step 6 — enabled in Phase 1 so the data is installed).
- [ ] MetaHuman Creator access: the owner signs in at **metahuman.unrealengine.com** with his Epic account (the same account as the Epic Launcher). If Creator asks for a separate sign-in, use the same Epic account — never create a second one.
- [ ] MetaHuman data already downloaded (build sheet Step 1). If the download is missing, Creator will offer it — accept it; it is large and slow, so start it before anything else.
- [ ] Disk space: MetaHumans are heavy. Keep **20 GB free** beyond the Phase 1 project before creating the first character.

## 3. Step-by-Step: The Owner Character

The first MetaHuman is the owner's own character — the canonical player from GDD-01 §1. Build it first, because every later character is judged against it.

### 3.1 The spec sheet (from the owner's profile example)

| Field | Value | Notes |
|---|---|---|
| Name | Zobaer Hasan | In-world name; account username is `@zobaerio` (GDD-01 §1). |
| Age (visual) | 28, Young Adult | The default new-player start (GDD-03 §1). |
| Profession | Civil Engineer | The flagship loop (GDD-03 §6). Work outfit: site-ready, not office-only. |
| Residence | Nexora Central City (Rupsha City, District 1) | Home anchor: rented Tier 3 apartment (GDD-03 §1). |
| Build | Average height, athletic-lean | A site engineer who walks plots all day — not a desk build. |
| Skin tone | South Asian, warm brown | Match the region the city is modelled on; do not lighten it to match a preset. |
| Hair | Short black, neat side part | See §5 hair rules. |
| Facial hair | Light stubble, optional toggle | A grooming option, not a fixed trait — the player changes it later. |
| Eyes | Dark brown | |
| Distinguishing | A small scar on the left eyebrow (optional) | One memorable feature beats a perfect face. Owner decides — if he says no scar, there is no scar. |

**Owner decision needed at build time:** the owner looks at the Creator preview and approves the face before export. A MetaHuman that the owner does not recognise as himself is a failed Phase 2, however good the render is.

### 3.2 Creator workflow

1. Open **MetaHuman Creator** in the browser. Create new MetaHuman → start from a preset closest to the spec (South Asian male preset if available; otherwise the nearest face shape and re-sculpt).
2. **Face:** sculpt to the spec — jaw, cheekbones, nose, eyes. Work from a front photo of the owner only if he provides one (his choice; never required). Do not use anyone else's photo.
3. **Skin:** pick the closest skin tone, then adjust warmth — never use a tone lighter than the owner. Add light stubble as a separate grooming toggle.
4. **Hair:** short black, side part (§5). Check the hair from the side and back, not just the front — the third-person camera sees the back of the head most.
5. **Body:** average/athletic-lean, height ~175 cm. Body type is set here, not in the engine.
6. **Name it** `MH_ZobaerHasan` in Creator. Export → **Download / Send to Unreal Engine** (Quixel Bridge). Target: the `ue-project` project, folder `Content/Nexora/Characters/Player/`.
7. In the editor, open the MetaHuman. Check: face animates (see §4), body proportions match the spec, hair renders from behind, skin tone matches Creator.
8. **Save a Creator preset** of the approved face — the preset is the backup if the export ever corrupts.

### 3.3 Rigging to the NEXORA character

- The MetaHuman body replaces the placeholder mesh on `ANexoraCharacter` (Unit D). Movement code does not change; only the mesh and the animation blueprint do.
- Use the MetaHuman **animation blueprint** with the NEXORA locomotion states (walk / run / jump from Unit D). Do not rebuild locomotion for MetaHuman — retune speeds only after a build exists to test them in.
- The face uses the MetaHuman face rig + the **Animator test** (§4). Body animation and face animation are separate systems; one working does not prove the other.

## 4. Animator Face-Capture Test Procedure

This is the Phase 2 exit test for faces. It runs on the owner's PC with his phone.

1. **Install MetaHuman Animator** (part of the MetaHuman plugin) and the **Live Link Face** app on the owner's phone (iPhone with TrueDepth, or Android with the supported app — check the current supported list in Creator before starting; if his phone is not supported, record that and use the fallback in step 6).
2. **Calibrate:** in Live Link Face, run the neutral-face calibration — relaxed face, eyes open, mouth closed, 3 seconds. Bad calibration is the #1 cause of "the face looks wrong"; if the result looks off, recalibrate before blaming the MetaHuman.
3. **Record a test set** (30 seconds each, facing the camera, even lighting, no glasses):
   - Neutral → smile → frown → raised eyebrows → speaking a sentence in Bangla → speaking a sentence in English.
   - The Bangla sentence matters: NEXORA's players speak Bangla. If the lip-sync fails on Bangla phonemes, note it as a Phase 2 finding, not a reason to switch languages.
4. **Play it back** on the MetaHuman in the editor (Live Link → face). Check: lip-sync timing, eyebrow/eye movement, and whether the face stays *him* while talking.
5. **Record the result** in the Phase 2 exit checklist (§7): pass/fail per clip, phone model, app version. A fail with a reason is a result; a shrug is not.
6. **Fallback if the phone is unsupported:** use Creator's built-in animation presets + manual keyframing for the test. The phase still passes if the face animates correctly from presets — but the limitation is written down, and phone capture is retried when hardware allows.

## 5. Outfit & Hair Rules

| Rule | Why |
|---|---|
| **One outfit per context, not per mood.** Work (site), casual (street), formal (events). Three outfits for the player; NPCs get one or two. | Outfit count is the fastest way a character budget explodes. |
| **The owner's character has a site outfit first** (boots, trousers, shirt, hi-vis vest as a toggle) — his profession is the flagship loop. | The first outfit must serve the first gameplay. |
| **Hair is checked from behind.** The third-person camera lives behind the head. | A hairstyle that only works from the front is a broken hairstyle in this game. |
| **No real-brand logos on clothing.** Original NEXORA brands only. | The same originality rule as the whole project (no GTA assets, no real brands). |
| **Outfits are data, not code.** An outfit is a MetaHuman wardrobe preset + a list of meshes; swapping one never touches C++. | Lets the owner add outfits without a programmer. |
| **Crowd outfits are variants, not uniques** (§6). | |

## 6. LOD & Crowd-Tier Rules

Tiers come from GDD-01 §2 (Full / Scheduled / Ambient). The rendering follows the tier — the simulation depth and the visual cost match:

| Tier | Who | MetaHuman quality | LOD rule | Face animation |
|---|---|---|---|---|
| **Full** | Player + ~25 named NPCs per district | Full MetaHuman, highest LOD | LOD0 near, LOD1 far; never below LOD1 for a named NPC in conversation | Full Animator / Live Link |
| **Scheduled** | District residents with homes/jobs | Full MetaHuman, shared preset pool | LOD0 near, LOD2 far; preset faces reused across NPCs with different hair/outfits | Preset expressions + lip-sync for dialogue lines only |
| **Ambient** | Mass-framework crowds | **Not MetaHumans** — Mass representation (simple bodies, no faces) | Lowest cost; culled beyond 50 m | None — they are visual life, not people (GDD-01 §4) |

**Rules:**
- **Preset pool, not per-NPC sculpting:** Scheduled NPCs are built from ~40 approved MetaHuman presets (varied age, tone, build, hair). A new preset is approved only when the pool has a visible gap — never "just one more".
- **No two Full-tier characters share a face.** The player and the 25 named NPCs are all unique.
- **Draw-call budget:** the Phase 2 perf capture (build sheet) is re-run with the MetaHuman in the scene. If fps drops below the Phase 1 baseline by more than 15%, the LOD distances tighten — the character is not simplified.
- **Child/elder variants:** authored assets (GDD-01 §3 gate). They are *not* built in Phase 2. Until Phase 7, children exist in data and household simulation only — the plan says so rather than faking it.

## 7. Phase 2 Exit Checklist

- [ ] Owner character `MH_ZobaerHasan` created in Creator, approved by the owner (face recognisably his).
- [ ] Exported to `Content/Nexora/Characters/Player/`; opens in the editor without errors.
- [ ] Walks/runs/jumps in the Phase 1 environment on `ANexoraCharacter` (Unit D movement, MetaHuman mesh).
- [ ] Animator face-capture test (§4) recorded: pass/fail per clip, phone model, app version on file.
- [ ] Three outfits (site / casual / formal) present; hair verified from behind.
- [ ] LOD distances set per §6; perf capture re-run against the Phase 1 baseline.
- [ ] Creator preset of the approved face saved (backup).
- [ ] The child/elder gate is recorded as open for Phase 7 (not silently "solved").

*End of PHASE2-METAHUMAN-SHEET v1.0. Changes happen by PR; the owner approves his own face, nobody else does.*
