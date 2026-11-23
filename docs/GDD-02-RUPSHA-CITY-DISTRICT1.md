# NEXORA — GDD-02: Rupsha City, District 1

**Unit C · Version 1.0 · 2026-11-20**
**Parent document:** `NEXORA-MIGRATION-PLAN.md` Part D Phase 5 (first living city) and Phase 1 (the 400 m test scene is this district's south-east corner, grown up).
**Companion data:** `data/professions.json`, `data/npc-schedules.json`, `data/weather-presets.json`, `data/planets.json`.
**Data model:** `docs/GDD-01-LIFE-AND-DATA-MODEL.md` + `data/schema.sql` — every zone, property and NPC in this document lands in those tables; `district_id` values below are the canonical ids used by the schema.

> **Design intent:** District 1 is not the biggest map NEXORA can stream — it is the most *believable* square kilometre: a Bangladeshi river city district where a player can live one full day (Phase 5 exit criteria) and where the Phase 6 society has homes, jobs and reasons to move. Local flavour is structural, not decorative: the rickshaw stand, the tea stalls, the ghat and the launch terminal are gameplay locations, not set dressing.

---

## 1. District Overview

- **Size:** ~1 km × 1 km playable, plus river frontage along the south edge (the Rupsha river — the city's namesake).
- **Grid:** irregular river-city grid, not an American checkerboard: two arterial roads, a market spine, and lanes (goli) narrowing into residential blocks.
- **Population targets (Phase 6):** ~120 households in data, ~25 full NPCs, ~300 scheduled NPCs, ambient Mass crowds on top.
- **Phase 1 relationship:** the Phase 1 test scene (street corner + park + riverbank) is zone D1-SE built first; District 1 grows it to the full kilometre in Phase 5.

## 2. Zones

`district_id` values are `d1_<zone>` and are used verbatim in `schema.sql` (`properties.district_id`, `households.district_id`).

| Zone id | Name | Character | Key contents |
|---|---|---|---|
| `d1_market` | Boro Bazar (Market Spine) | Dense retail, noise, crowds | Market hall, 24 shop units, tea stalls ×6, wholesale godowns |
| `d1_oldtown` | Old Town Lanes | Oldest housing, narrow lanes | Walk-up housing, mosque/temple frontages (exterior), repair workshops |
| `d1_riverfront` | Riverfront & Ghat | Open, breezy, transport hub | Ghat steps, launch/ferry terminal, fish market edge, riverside park strip |
| `d1_midtown` | Midtown Residences | Middle-class apartments | 6-storey apartment blocks, the player's starter apartment building |
| `d1_civic` | Civic Quarter | Institutions | School, clinic, bank branch, police station, city office |
| `d1_education` | College Para | Students, bookshops, hostels | College building, library, student hostels, photocopy/food row |
| `d1_industry` | Light Industry Edge | Work sheds, depots | Small factories ×3, transport depot (taxi/CNG base), construction yard |
| `d1_park` | Central Park | Green lung | Park (Phase 1 park grows into this), pond, walking loop, benches, food carts |
| `d1_transport` | Station Quarter | Intercity movement | Bus terminal, railway station frontage, rickshaw/CNG stands |
| `d1_uptown` | Uptown Heights | Upper-income housing + offices | Luxury apartments, office block, premium shops, rooftop restaurant (landmark) |

Zone adjacency is deliberate: market touches old town and transport (goods flow), industry sits downwind by the station (freight), uptown overlooks the park and river (price gradient the economy can price — Unit F reads these zones for property values).

## 3. Road Hierarchy

| Class | Width | Where | Traffic |
|---|---|---|---|
| Arterial | 4 lanes + footpaths | North–south avenue (Civic Ave) and east–west avenue (River Road) crossing at the market's north edge | Cars, buses, trucks; signalled junctions ×3 |
| Collector | 2 lanes + footpaths | Ring connecting civic, education, midtown, uptown | Cars, CNGs, rickshaws |
| Local street | 2 lanes, parking pockets | Residential blocks | Cars, rickshaws, pedestrians |
| Lane (goli) | 3–4 m, no through traffic | Old town interior | Pedestrians, rickshaws, bicycles only — vehicles physically cannot enter; this is a *walking* neighbourhood by design |
| Riverside promenade | Pedestrian | Riverfront | Walking, cycles, food carts |

**Traffic design notes (Phase 5):** rickshaws and CNGs are first-class traffic (Zone Graph lanes with slower speed classes), not reskinned cars. Signals at the 3 arterial junctions; market spine is pedestrian-priority 07:00–22:00 (bollards up; delivery vehicles only before 07:00) — a schedule the NPC day actually feels.

## 4. Landmark List (navigational anchors — a player gives directions by these)

1. **The Clock Tower** at the arterial crossing (visible from most of the district).
2. **Rupsha Bridge approach** at the south-east river edge (bridge itself is a Phase 8 travel gate; approach + toll plaza built now).
3. **Launch Terminal** with its green-roofed shed on the riverfront.
4. **Central Park pond & banyan tree** (the Phase 1 park's centrepiece, kept).
5. **Boro Bazar market hall** — arched entrance, district's commercial heart.
6. **Uptown rooftop restaurant tower** — the district's only high-rise; skyline marker.
7. **Railway station clock frontage** in the Station Quarter.
8. **The old water tank** in Old Town — rusted, beloved, unmissable.

## 5. Interiors List (Phase 5 scope — key buildings only)

Full interiors are expensive; Phase 5 builds these, everything else is exterior + door interaction until later phases:

| Interior | Zone | Gameplay purpose |
|---|---|---|
| Player starter apartment (1 flat, furnished tiers) | `d1_midtown` | Home base; property system v1 (GDD-01 §5) |
| 3 further apartment variants (rent/buy showpieces) | midtown, uptown | Property market browsing |
| Tea stall (sittable, order, gossip dialogue) | market + riverfront | Social hub; NPC memory demos |
| Market hall interior (stalls, prices visible) | `d1_market` | Shopping; Shop Owner loop premises |
| Bank branch | `d1_civic` | Accounts, loans (Unit F), safe UI for economy |
| Clinic (reception + 2 rooms) | `d1_civic` | Doctor profession site; health events |
| School (2 classrooms + yard) | `d1_civic` | Teacher site; child schedules anchor here |
| Police station (front desk + office) | `d1_civic` | Police Officer site; fines/wanted interface later |
| Construction site office + staged build plot | `d1_industry` edge | **Civil Engineer flagship loop** site |
| Taxi/CNG depot office | `d1_industry` | Taxi Driver loop base |
| Restaurant kitchen + dining | `d1_market` | Chef loop site |
| College library reading room | `d1_education` | Study/skill gain; student life |

**Named service anchors (Unit CB · Queue 14 · 2026-11-23).** The tea stalls and restaurants above are now named anchors in `data/district1-blockout.json` (`service_anchors`, 9 entries), so `tools/sim/scheduler.py` `resolve_service_anchor()` returns a real anchor id instead of the `"<token>:<zone>"` form Unit BS used: the 6 Boro Bazar tea stalls (`anchor_tea_stall_bazar_1`–`6`, `d1_market`), the riverfront tea stall (`anchor_tea_stall_riverfront_1`, `d1_riverfront`), the market kitchen (`anchor_restaurant_market_kitchen`, `d1_market`, in building `b_d1_market_hall_units`), and the rooftop restaurant (`anchor_restaurant_rooftop`, `d1_uptown`, in building `b_d1_uptown_rooftop_restaurant`). The stall *names* ("Boro Bazar Tea Stall 1" …) are this unit's authored labels — no source names the stalls — and are recorded as such on each entry (`name_status`); the stall *counts* and *zones* are sourced (§2, §5). Within a zone the scheduler picks the first anchor in file order, not the nearest by distance, because the sim stores no NPC coordinates; the UE layer, which has positions, picks the truly nearest. The zone rule is unchanged (GDD-15 §21.1): a stall still resolves to its own zone, never to the NPC's home zone.

## 6. Property Stock (initial market, written to `properties` at world seed)

- Residential: ~140 units across zones (old-town walk-ups cheapest → uptown luxury), ~20% listed for sale at world start, the rest NPC-owned/rented.
- Commercial: 24 market shops, 6 tea stalls, 3 factory units, depot, restaurant — the businesses of `professions.json` employ into these.
- Civic properties are city-owned (owner = system household) and never for sale.
- Every property gets `district_id` from §2, a tier 1–5, and a market value from the Unit F model; the seed script (later unit) generates them from this document's counts, not by hand.

## 7. NPC Anchoring

- Each profession in `data/professions.json` names its District 1 workplace zone/building; `data/npc-schedules.json` templates run home → workplace → leisure anchors chosen from: tea stalls, park, market, riverfront promenade, home.
- Full-NPC cast (~25) is authored against these anchors in a later content unit; this GDD fixes the *places* their lives happen so schedules written now stay valid.
- Children anchor to the civic school; college students to `d1_education`; the elderly disproportionately to park + riverfront mornings — small rules that make the district read as lived-in at a glance.

## 8. What District 1 Deliberately Excludes (Phase 5 scope honesty)

- No airport (Phase 8 travel), no hospital tower (clinic only), no metro, no second bridge, no enterable-every-building. The district is one honest square kilometre; Districts 2+ and City 2 are Phase 8.

*End of GDD-02 v1.0. Zone ids and counts here are canonical for seed data and Unit F pricing.*
