# NEXORA — TECH: District 1 Blockout Spec

**Unit R · Version 1.0 · 2026-11-21**
**Parent documents:** `docs/GDD-02-RUPSHA-CITY-DISTRICT1.md` §2 (zones), §3 (road hierarchy), §4 (landmarks), §6 (property stock) · `data/district1-blockout.json` (the data contract for this document) · `data/buildings-district1.json` (building ids — used verbatim) · `docs/PHASE1-BUILD-SHEET.md` (the 400 m test scene this blockout serves first) · `docs/GDD-07-VEHICLES-AND-TRAFFIC.md` §3 (the traffic model that consumes these segments)
**Status:** DESIGN DATA. No level geometry exists yet; this spec is what the owner builds from on his PC. Coordinates are a v1 blockout, not art direction — buildings may shift *inside their zone box* during the PC build without breaking any reference, because everything cites ids, not positions.

> **Build law:** ids are forever, positions are negotiable. Segments, plots and landmarks are cited by id from the GDDs, the traffic model and (later) missions. An id never changes meaning; a coordinate may be tuned on the PC and the change lands here as a data revision, not a redesign.

---

## 1. Coordinate System

- Local metres, ground plane `x` (east) / `z` (south), engine Y up. Origin sits 60 m north of the Clock Tower junction, so the district's navigation centre — the arterial crossing — is at `(0, −60)`.
- District extent ≈ 1,020 m × 990 m: GDD-02's "≈1 km²" made concrete. The river band closes the south edge (`z` 432–520).
- Every position in `data/district1-blockout.json` uses this system: segment endpoints, junction points, plot rects (`x, z` = north-west corner, `w, d` in metres), anchors (the point a character/vehicle interacts at — plot's south edge centre in v1) and landmark points.

## 2. Zones & Plots

Each of GDD-02's 10 zones gets a bounding box (`zone_boxes_m` in the data). All **42 properties** from `data/buildings-district1.json` appear as plots, **1:1 by building id** (validator-checked — no id invented, none dropped, none renamed). v1 placement is a grid inside the zone box; that is deliberate: the blockout's job is *completeness and adjacency* (market touches old town and transport; industry downwind by the station side; uptown overlooking park and river — GDD-02 §2), and per-plot art placement is a PC pass inside the same boxes.

Multi-unit properties (apartment blocks, market hall units) are one plot each — the `units` count lives in `buildings-district1.json`, not in geometry. Named individual units with `part_of` in that file share their block's plot.

## 3. Road Segments

21 segments in the data, each: `id, name, class, width_m, from, to`. Classes are GDD-02 §3 verbatim, and they are the same ids `data/vehicles.json` routes by:

| Class | Width in data | Segments | Notes |
|---|---|---|---|
| `arterial` | 16 m (4 lanes + footpaths) | Civic Ave N/S, River Road W/E, bridge approach (12 m) | The crossing at `(0, −60)` is the Clock Tower junction |
| `collector` | 10 m | Ring N/E/S/W | Connects civic, education, midtown, uptown per GDD-02 |
| `local` | 8 m | Market Spine + 6 zone locals | Market Spine carries the `pedestrian_priority` window (07:00–22:00, GDD-02 §3) as data, not prose |
| `lane` | 3.5–4 m | 3 old-town golis | Motor-barred by class (GDD-07 §3) |
| `promenade` | 6 m | Riverside Promenade | Pedestrian + cycles |

**Junctions:** 9 in the data; exactly **3 signalled** (Clock Tower, Civic Ave × Ring South, River Road × Ring East) per GDD-02 §3's "signalled junctions ×3". The rest are priority junctions — stated in data so traffic behaviour (GDD-07) has no hidden cases.

**Building the roads on PC:** blockout order is arterials → ring → locals → lanes → promenade, greybox materials only, one segment at a time, naming actors by segment id. A segment is "done" when a character can walk it end to end and a vehicle of every allowed class can traverse it (Phase 5 test), not when it looks finished.

## 4. Landmarks

All 8 GDD-02 §4 landmarks are placed (`landmarks` in the data), four of them tied to their building ids (launch terminal, market hall, rooftop restaurant, station). Landmarks are navigation anchors: missions (GDD-04) and NPC directions cite landmark ids, so a landmark's id is as permanent as a building's.

## 5. River & Bridge

- The Rupsha river band (south edge, flowing west→east) with the **ghat** at `(0, 432)` — steps to the water at the launch terminal's anchor; riverfront anchors close under storm (GDD-06 §7), which is why the ghat is data and not just scenery.
- **Bridge:** only the approach segment (`seg_bridge_approach`) and toll plaza area are District 1 geometry. The crossing itself is a **Phase 8 travel gate** (GDD-02 §4) — the segment ends at the district edge and the data says so; nobody models a bridge to nowhere in Phase 1–5.
- The promenade runs the riverfront length between ghat and bridge approach, tying the Phase 1 park/riverbank work into the district's south edge.

## 6. The Phase 1 Test-Scene Subset

`phase1_test_scene` in the data marks the subset the owner builds **first** (PHASE1-BUILD-SHEET): a 400 m × 400 m box (`x` −200…200, `z` −60…340) containing 10 segments (the arterial crossing, Civic Ave south, the Market Spine, the park-side locals, the promenade head) and 10 building plots around the market/park core, plus the pond landmark at its centre-south.

Rules for the subset:
- It is a *subset*, not a separate map: same ids, same coordinates. When the full district blocks out, the test scene is simply the part that was built first.
- Phase 1's exit criteria (performance capture, lighting/weather passes) are measured **here**, so perf numbers stay comparable as the district grows around it.
- Nothing outside the box is required for Phase 1 — if a Phase 1 step seems to need an outside asset, the step is wrong, not the box.

## 7. What This Spec Deliberately Does Not Decide

- **No interiors.** GDD-02 §5 lists interiors; their floor plans are a later unit. Plots carry anchors, not rooms.
- **No verticality data.** Building heights/floors come from the plan/property data when buildings are modelled; the blockout is a ground-plane contract.
- **No prop dressing.** Tea-stall positions, benches, signage — the art pass places them inside plots/zones on the PC; the blockout guarantees the *space* exists, not the dressing.
- **Positions are v1.** If the PC build finds a plot or segment unworkable, the fix is a data revision to this file (same ids), recorded in STATUS — never a silent divergence between the level and the data.
