# NEXORA — TECH: District 2 Blockout Spec (PROPOSED)

**Unit AR · Version 1.0 · 2026-11-22**
**Parent documents:** `docs/GDD-02-RUPSHA-CITY-DISTRICT1.md` §2 (zones), §3 (road hierarchy), §4 (landmarks), §6 (property stock) · `data/district2-blockout.json` (the data contract for this document) · `data/district1-blockout.json` + `docs/TECH-DISTRICT1-BLOCKOUT.md` (the shape this file mirrors) · `docs/TECH-MULTIDISTRICT.md` §3.5 (the siting rules this proposal must obey) · `docs/GDD-04-MISSIONS-AND-PROGRESSION.md` (proposed level names — the precedent for "a revision is a data edit, not a redesign")
**Status:** PROPOSED CONCEPT. No level geometry exists, no buildings data exists for District 2, and nothing in this document is approved. The owner confirms or revises it; a revision lands as a data edit to `data/district2-blockout.json`, not a redesign.

> **Build law (inherited from Unit R):** ids are forever, positions are negotiable. Segments, plots and landmarks are cited by id from the GDDs, the traffic model and (later) missions. An id never changes meaning; a coordinate may be tuned on the PC and the change lands here as a data revision, not a redesign. **For District 2 the law is conditional:** these ids become permanent only when the owner confirms the proposal. Until then every element carries `"status": "PROPOSED"`, and the owner may rename, move or delete any of them.

---

## 1. Coordinate System

- **The same frame as District 1.** Local metres, ground plane `x` (east) / `z` (south), engine Y up. Origin sits 60 m north of the Clock Tower junction, so District 1's arterial crossing is at `(0, −60)` and District 2's proposed arterial crossing — Northgate junction — is at `(0, −1080)`.
- District 2 extent ≈ 1,020 m × 1,020 m: `x` −510…510, `z` −1520…−500. Its south edge (`z` −500) **is** District 1's north edge, so the two districts share one edge and one coordinate frame, as TECH-MULTIDISTRICT §3.1 requires (Rupsha City is one World Partition map; districts are data layers on it, not separate maps).
- Every position in `data/district2-blockout.json` uses this system: segment endpoints, junction points, plot rects (`x, z` = north-west corner, `w, d` in metres), anchors (the point a character/vehicle interacts at — plot's south edge centre in v1) and landmark points.

## 2. Zones & Plots

Each zone gets a bounding box (`zone_boxes_m` in the data) plus a metadata entry (`zones` in the data) stating whether its vocabulary is **reused from District 1** or **new PROPOSED**. All **40 plots** reference zone + tier (1–5, GDD-02 §6) + `proposed_use` + `property_type` (schema vocabulary: apartment / house / shop / factory / office / plot). **No plot references a building id**: `building_id` is `null` on every plot, because no `data/buildings-district2.json` exists yet. A District 2 buildings file is a later unit's work, authored only after the owner confirms this layout; when it exists, plots map to it 1:1 by id under the same rule as District 1 (TECH-DISTRICT1-BLOCKOUT §2).

v1 placement is a grid inside the zone box, as in District 1: the blockout's job is *completeness and adjacency*, and per-plot art placement is a PC pass inside the same boxes.

| Zone id | Name | Vocabulary | Character | Plots |
|---|---|---|---|---|
| `d2_midtown` | Midtown North | Reused (`d1_midtown`) | Middle-class apartments | 5 |
| `d2_garden` | Garden Suburb | **New PROPOSED** | Low-density houses with garden plots; the quiet residential quarter | 4 |
| `d2_maidan` | North Maidan | **New PROPOSED** | Open playing-field ground with a pavilion | 2 |
| `d2_market` | North Bazar | Reused (`d1_market`) | Dense retail — the district's commercial heart | 4 |
| `d2_civic` | Civic North | Reused (`d1_civic`) | Institutions | 5 |
| `d2_education` | College North | Reused (`d1_education`) | Students, bookshops, hostels | 4 |
| `d2_industry` | North Workshops | Reused (`d1_industry`) | Work sheds, depot, construction yard | 4 |
| `d2_park` | North Green | Reused (`d1_park`) | Green lung | 2 |
| `d2_transport` | North Gate | Reused (`d1_transport`) | Bus terminal and depot | 3 |
| `d2_uptown` | North Heights | Reused (`d1_uptown`) | Upper-income housing + offices on the northern strip | 7 |

**Why two new zones, and why these two.** District 1's vocabulary has no reusable zone for either slot. `d1_oldtown` cannot be reused — old town is the *oldest* housing, and a second old town is not proposed; its slot (west, south of the crossing) becomes Garden Suburb, the low-density counterpart that makes District 2 read differently from District 1's dense walk-ups (TECH-MULTIDISTRICT §4: a new district must not read as District 1 recoloured). `d1_riverfront` cannot be reused — District 2 has no river; its slot (the southern strip) becomes the Maidan, an open playing field, which also gives the district a gathering space that is not a copy of Central Park. Both new zones are labelled as such in the data (`zones[].vocabulary` starts "NEW PROPOSED zone") so a validator can tell reuse from invention.

**What the plot grid deliberately mirrors:** District 2's zone boxes are District 1's boxes shifted exactly −1020 m in `z` (the district depth), with the two substitutions above. Midtown, market, civic, education, industry, park, transport and uptown keep District 1's relative positions; the uptown strip keeps its thin 80 m depth and 21.3 m plot rows. That is a proposal, not a finding — the owner may re-lay the grid, and the boxes move with it.

## 3. Road Segments

20 segments in the data, each: `id, name, class, width_m, from, to, status: "PROPOSED"`. Classes are GDD-02 §3 verbatim — no new class is invented. (The one extension is noted honestly below: the promenade class is applied to a maidan edge rather than a riverfront.)

| Class | Width in data | Segments | Notes |
|---|---|---|---|
| `arterial` | 16 m (4 lanes + footpaths) | Civic Ave N/S (District 2), Northgate Rd W/E | The crossing at `(0, −1080)` is the proposed Northgate junction |
| `collector` | 10 m | Ring N/E/S/W | Connects civic, education, midtown, uptown per GDD-02, as in District 1 |
| `local` | 8 m | North Bazar Spine + 6 zone locals | North Bazar Spine carries the `pedestrian_priority` window (07:00–22:00, GDD-02 §3) as data, not prose — the same rule as District 1's Market Spine |
| `lane` | 3.5–4 m | 3 garden lanes | Motor-barred by class (GDD-07 §3), as District 1's golis — the garden suburb is a walking neighbourhood by design |
| `promenade` | 6 m | Maidan Promenade | Pedestrian + cycles. **PROPOSED extension:** GDD-02 §3 defines the promenade as a *riverside* promenade; District 2 has no river, so this segment applies the class to the maidan's south edge instead. If the owner rejects that extension, the segment is reclassed or deleted — the class vocabulary itself does not change. |

**Junctions:** 10 in the data; exactly **3 signalled** (Northgate, Civic Ave × Ring South, Northgate Rd × Ring East) — mirroring District 1's "signalled junctions ×3" (GDD-02 §3). The rest are priority junctions, stated in data so traffic behaviour (GDD-07) has no hidden cases.

**The join to District 1 (implied, not invented).** District 1's `seg_civic_ave_n` ends at `(0, −500)` — the district's north edge — with nowhere to go. District 2's `d2_seg_civic_ave_s` starts exactly there: junction `d2_j_south_gate` at `(0, −500)` is the named inter-district join TECH-MULTIDISTRICT §3.2 requires ("new segments … must join the existing graph at a named junction"). This is the one piece of District 2 geography District 1's data already implies: the avenue continues north. Everything else — the Northgate crossing, the ring, the locals — is PROPOSED.

**Building the roads on PC (if confirmed):** blockout order is arterials → ring → locals → lanes → promenade, greybox materials only, one segment at a time, naming actors by segment id — the same order as District 1. A segment is "done" when a character can walk it end to end and a vehicle of every allowed class can traverse it (Phase 5 test), not when it looks finished. **Nothing is built until the owner confirms the proposal.**

## 4. Landmarks

6 proposed landmarks (`landmarks` in the data), all `"status": "PROPOSED"`, none tied to a building id (none exists to tie to). Four mirror District 1 landmarks in function; two are new:

| Id | Name | Mirrors (GDD-02 §4) / note |
|---|---|---|
| `d2_lm_northgate_tower` | Northgate Tower | Clock Tower (§4.1) at the District 2 arterial crossing — the district's navigation centre |
| `d2_lm_north_bazar_hall` | North Bazar hall | Boro Bazar market hall (§4.5) — the commercial heart |
| `d2_lm_maidan_pavilion` | Maidan pavilion | **New** — pavilion on the maidan strip |
| `d2_lm_garden_tank` | Garden Suburb water tank | The old water tank (§4.8) — a beloved, unmissable marker, restated for the new suburb |
| `d2_lm_north_gate_depot` | North Gate depot frontage | Railway station clock frontage (§4.7) at the bus terminal |
| `d2_lm_north_heights_view` | North Heights viewpoint | Uptown rooftop restaurant tower (§4.6) as the northern skyline marker |

Landmarks are navigation anchors: missions (GDD-04) and NPC directions cite landmark ids, so a landmark's id is as permanent as a building's — **once confirmed**. Until then, treat these six names as suggestions the owner may replace.

## 5. River & Bridge

- **District 2 has no river.** The Rupsha river band (`z` 432–520, flowing west→east) lies ≈ 932 m south of District 2's south edge (`z` −500), across the whole of District 1. The `river` object in the data cites District 1's band coordinates for reference only and states this explicitly; District 2 has no riverfront zone, no ghat (`ghat: null`) and no river geometry. The storm rule (riverfront anchors close under storm, GDD-06 §7) applies in District 1 only.
- **No second bridge.** The only crossing remains District 1's Rupsha Bridge approach (`seg_bridge_approach`), a Phase 8 travel gate (GDD-02 §4). TECH-MULTIDISTRICT §3.5 names a second bridge as a contradiction that would need the blockout revised; this proposal does not include one, and `river.bridge.segment_ref` is `null` to say so in data.
- **North edge.** District 2's northernmost segment, `d2_seg_civic_ave_n`, ends at `(0, −1520)` at the district edge with no onward route designed — the same honesty District 1 uses for its bridge approach. What lies north of Rupsha North (farmland, a further district, nothing) is an owner decision, not assumed here.

## 6. The Phase 8 First Slice (PROPOSED)

`phase8_first_slice` in the data marks the subset the owner would build **first if District 2 is confirmed**: a 400 m × 400 m box (`x` −200…200, `z` −1080…−680) containing 10 segments (the Northgate crossing, Civic Ave both ways, the North Bazar Spine head, the garden lanes, the park-side locals) and 11 plots around the market/park core, mirroring District 1's Phase 1 test scene (TECH-DISTRICT1-BLOCKOUT §6) in shape but not in phase.

Rules for the subset (same as District 1's):
- It is a *subset*, not a separate map: same ids, same coordinates. When the full district blocks out, the first slice is simply the part that was built first.
- **It is Phase 8 work** (TECH-MULTIDISTRICT). Nothing here is a Phase 1 commitment, and District 2 does not move Phase 1's exit criteria, which are measured in District 1's test scene.
- Nothing outside the box is required for the first slice — if a first-slice step seems to need an outside asset, the step is wrong, not the box.

## 7. What Is PROPOSED vs What District 1 Implies

| Item | Status | Basis |
|---|---|---|
| District 2 sits immediately north of District 1, same frame, south edge = District 1's north edge (`z` −500) | **Implied** | District 1's `seg_civic_ave_n` ends at `(0, −500)`; the river closes the south edge and the bridge approach occupies the south-east (TECH-MULTIDISTRICT §3.5); north is the only open landward edge |
| Civic Ave continues north from `(0, −500)`; join at `d2_j_south_gate` | **Implied** | Same as above; TECH-MULTIDISTRICT §3.2 join rule |
| Road hierarchy, zone vocabulary (8 of 10 zones), property tiers 1–5, widths, signalled-junction count (3), pedestrian-priority rule | **Reused** | GDD-02 §§2–3, 6, verbatim |
| District name "Rupsha North" | **PROPOSED** | Owner to confirm or rename |
| Northgate Rd, the collector ring, all locals/lanes, the Northgate crossing and its tower | **PROPOSED** | No District 1 data implies their positions; the mirror-shift (−1020 m) is a proposal |
| `d2_garden` (Garden Suburb) and `d2_maidan` (North Maidan) zones | **New PROPOSED** | No District 1 equivalent; see §2 for why |
| Promenade class applied to a maidan edge | **PROPOSED extension** | GDD-02 §3 defines it as riverside; see §3 |
| All 40 plots, 6 landmarks, the Phase 8 first slice | **PROPOSED** | First-slice buildings data now exists (Unit AT, §10); the other 29 plots still have no buildings data. All 40 plots still carry `building_id: null` in the blockout file — the plot → building link lives in `data/buildings-district2.json` (`plot_id`) until the owner confirms the layout |
| No second bridge; no river in District 2; no onward route past `(0, −1520)` | **Deliberately absent** | TECH-MULTIDISTRICT §3.5; GDD-02 §8 |

## 8. What This Spec Deliberately Does Not Decide

- **Buildings data for the first slice only.** Unit AT (Queue 9) authored `data/buildings-district2.json` for the 11 first-slice plots — ahead of owner confirmation, as PROPOSED v1 data under the standing continuous-development order, the same status this whole spec carries. The other 29 plots still have no buildings data. The blockout file's plot-level `building_id` fields stay `null` until the owner confirms the layout (a one-line data edit per plot then); until then the plot → building link lives in the buildings file's `plot_id` field, and the validator checks the 1:1 coverage of the first slice.
- **No interiors.** As District 1 (§7): interiors are a later unit. Plots carry anchors, not rooms.
- **No verticality data.** Building heights/floors come from the plan/property data when buildings are modelled; the blockout is a ground-plane contract.
- **No prop dressing.** Tea-stall positions, benches, signage — the art pass places them inside plots/zones on the PC; the blockout guarantees the *space* exists, not the dressing.
- **No prices, rents, fares or wages.** A new district's property values are priced from its own zones and tiers when its GDD is written — never copied from District 1's table (TECH-MULTIDISTRICT §3.2).
- **No sim-side rows.** Per TECH-MULTIDISTRICT §3.2, a district that exists only as a UE layer, with no sim-side city/zone rows, is scenery, not a district. The sim rows (city zones, parcels, road graph) are a later unit's work; this proposal does not claim the sim knows about District 2.
- **No airport, hospital tower, metro, or second bridge.** GDD-02 §8's exclusions stand; an airport remains an open Phase 8 owner decision (TECH-MULTIDISTRICT §1, Contradiction 2).
- **Positions are v1 and unconfirmed.** If the owner revises any plot, segment or landmark, the fix is a data revision to `data/district2-blockout.json` (same ids where kept), recorded in STATUS — never a silent divergence between the level and the data.

## 9. What the Owner Must Confirm or Revise

1. **Siting:** District 2 immediately north of District 1 (vs west, or not at all). The north siting is proposed because it is the only open landward edge; the west edge is the unproposed alternative.
2. **Name:** "Rupsha North", or another name.
3. **The two new zones:** Garden Suburb (`d2_garden`) and North Maidan (`d2_maidan`) — keep, rename, replace, or drop.
4. **The promenade extension:** Maidan Promenade as a `promenade`-class segment on a maidan edge rather than a riverfront.
5. **The Northgate crossing and ring:** positions as proposed (the −1020 m mirror of District 1), or re-laid.
6. **Landmark names:** the six proposed names, or replacements.
7. **The northern terminus:** what, if anything, lies beyond `(0, −1520)` — and whether the North Gate bus terminal is the district's intercity hub or whether intercity travel stays at District 1's station/terminal.
8. **Scope decision:** whether District 2 proceeds to a GDD section and a buildings file (the next units), or stays a concept on the shelf.

## 10. Unit AT Note — First-Slice Buildings Data (Queue 9)

`data/buildings-district2.json` (v1.0, status `PROPOSED`) authors buildings for the Phase 8 first slice only — the 11 plots §6 marks. The other 29 plots have no building: their `building_id` stays `null` and no second-slice building is invented anywhere.

- **Residential (5 buildings: 3 apartments, 2 houses):** rent/buy per unit from the shared `data/prices.json` `rent_monthly_by_tier` table — tier 2: 4000/350000, tier 3: 6000/750000. These are the canonical tier values, not District 1's file: the same table District 1's residential stock is validated against.
- **Commercial (5 buildings: hall shops, tea stalls, godowns, restaurant, food carts):** there is no per-tier commercial table in `prices.json`, so rent/buy mirror the closest District 1 analogue of the same type + tier, cited per building (`b_d1_market_hall_units`, `b_d1_market_tea_stalls`, `b_d1_market_godowns`, `b_d1_market_restaurant`, `b_d1_park_food_carts`). This is a deliberate, labelled deviation from §8's "never copied from District 1's table": the values are PROPOSED v1 seeds with exactly the standing District 1's own commercial values carry (its file calls them seed extrapolations of the tier model, pending Phase 6 tuning). If the owner prices District 2 commercially from its own zones instead, these five values are replaced, not defended.
- **Parkland (1 building):** `b_d2_park_green` — rent/buy null, civic-owned, mirroring `b_d1_park_land`.
- **Availability:** all 11 buildings are for rent at opening (`for_rent_units` = `units`) and none is listed for sale (`for_sale_units` = 0); sales open only after the owner confirms the layout. Unit counts are PROPOSED estimates from the cited District 1 analogue.
- **Link rule:** each building carries `plot_id` into the first slice; the validator checks the 11 `plot_id` values cover the first-slice plot ids exactly once, and that each building's zone/type/tier equals its plot's. The blockout file's `building_id` fields remain `null` (see §8) until owner confirmation.
