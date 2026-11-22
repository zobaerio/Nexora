# NEXORA — TECH: Multi-District & Multi-City Design (Phase 8)

**Unit AF · Version 1.0 · 2026-11-22**
**Parent documents:** `NEXORA-MIGRATION-PLAN.md` Part D Phase 8 (goal, build, exit criteria), Part C #5 (World Partition / HLOD), Part C #15–#16 (multiplayer scale, transition-based planet travel) · `docs/GDD-02-RUPSHA-CITY-DISTRICT1.md` (District 1 zones, roads, landmarks) · `docs/TECH-DISTRICT1-BLOCKOUT.md` + `data/district1-blockout.json` (District 1 geometry contract) · `data/city2-shibnagar.json` (Shibnagar Town, GENERATED) · `docs/SESSION-03-REPORT.md` (two-city sim data, regional connections) · `docs/SESSION-07-REPORT.md` (transport layer; § "Limitations" — the rail/air position) · `docs/TECH-MULTIPLAYER.md` (Phase 9 boundaries this design must not cross) · `data/transport-config.json` (transit routes, intercity crossing figures)
**Status:** DESIGN DOCUMENT ONLY — Phase 8 design. No UE code, no level, no build. Nothing here claims a UE feature works; UE work stays uncompiled scaffold until the owner's PC build (migration plan Part 0 / Part J).

> **Design intent:** Phase 8 scales the world horizontally — Rupsha City grows past its first square kilometre, and Shibnagar Town becomes a second place a player can actually go to. The scaling mechanism is UE World Partition, the content mechanism is the two-city data the sim already runs on, and the travel mechanism is honest about what exists: road and ferry have real networks; train and flight are transition-based journeys, because no rail or air operations exist in any merged data.

---

## 1. Honest Position — What This Document Is, and Two Contradictions It Does Not Hide

**What it is:** the UE design layer over the two-city world Sessions 03 and 07 already simulate: how District 1 becomes one district among several inside one World Partition map, how Shibnagar Town becomes a second map, and how a player travels between them.

**What it is not:** no new district, city, road, track, airfield, or price is invented here. Every id cited in this document exists in a merged data file or a merged report; §11 lists them and how each was checked.

**Contradiction 1 — "different climate".** The migration plan's Phase 8 build line says the second city has "different climate/architecture". Shibnagar Town — the only second city in the merged data — sits across the same Rupsha river from Rupsha City, and Session 03 derives both cities' climate from the same weather-preset weights (`tropical_monsoon`). A genuinely different climate zone cannot honestly be claimed for a town across the river. What Phase 8 *can* deliver with this second city, and what this document designs, is a visibly and economically distinct place through **architecture, terrain exposure, and economy** (§5): open farmland, floodplain and wetland instead of dense urban fabric; low-rise town buildings instead of apartment blocks and a high-rise; an agricultural economy instead of a market/commercial one. A second city in a truly different climate is a later, further city — not designed here, not named here.

**Contradiction 2 — "airports as functional travel hubs".** The Phase 8 build line also lists "airports/stations as functional travel hubs". A railway station building exists (`b_d1_transport_station`, §7) and a launch terminal exists (`b_d1_riverfront_launch_terminal`). **No airport exists anywhere in the merged data** — no site, no building id, no airfield geometry — and GDD-02 §8 explicitly excludes an airport from District 1 ("No airport (Phase 8 travel)"). This document therefore designs the *hub interface* for air travel (booking, transition, arrival) and records airport siting as an open Phase 8 decision for the owner; it does not invent an airport, a runway, or a location. Flight travel is transition-based (§7) precisely because there is nothing to simulate yet.

**The rail position, restated (Session 07).** Session 07's report states it plainly and this document repeats it verbatim in substance: *"Rail, air and maritime operations do not run. A Railway Station plot and a Launch Terminal exist as buildings, but no rail track network, timetable, airfield or port data exists anywhere in the merged data, and none was fabricated."* Train travel in Phase 8 is therefore a transition-based journey (§6), not a simulated operation. The river ferry is the one water crossing that does run in the sim (Session 03's persisted `RC-FERRY-1`; Session 07's ferry route over it), and it is treated as a real, scheduled service in this design.

---

## 2. The Two Cities As They Exist in Data

| Fact | Rupsha City — District 1 | Shibnagar Town |
|---|---|---|
| City id | `rupsha_city` (Session 03 registry; District 1 is city #1) | `shibnagar_town` (`data/city2-shibnagar.json`, `city.city_id`) |
| Kind | Authored design data (GDD-02) | GENERATED town (`citygen.py`, Session 03 Unit 01; labelled GENERATED in-file) |
| Extent | ≈ 1,020 m × 990 m, ~1 km² (TECH-DISTRICT1-BLOCKOUT §1) | Town frame x −40…560, z −80…500 (≈ 600 m × 580 m incl. river band) |
| Zones | 10 (`d1_market`, `d1_oldtown`, `d1_riverfront`, `d1_midtown`, `d1_civic`, `d1_education`, `d1_industry`, `d1_park`, `d1_transport`, `d1_uptown`) | 6 (`c2_agriculture`, `c2_civic`, `c2_market`, `c2_residential`, `c2_riverfront`, `c2_transport`) |
| Buildings / plots | 42 buildings, 42 plots, 1:1 by id (blockout §2) | 18 buildings, 22 plots (4 plots vacant, `building_id: null`) |
| Road segments | 21 (`data/district1-blockout.json`) | 7 (`seg_c2_main_st`, `seg_c2_ghat_rd`, `seg_c2_mid_st`, `seg_c2_south_st`, `seg_c2_west_st`, `seg_c2_east_st`, `seg_c2_farm_rd`) |
| Residential units | ~140 (GDD-02 §6) | 39 (`data/city2-shibnagar.json`, Session 03 Unit 08) |
| Population (sim) | 245 of 250 alive in the Session 03 90-day run (seed `bench`) | 0 at genesis; 5 after 4 households migrated organically in that run |
| River | Rupsha river band closes the **south** edge (z 432–520) | Same Rupsha river closes the **north** edge (z −80…0); the town faces the city across it |
| Landmarks | 8 (`lm_clock_tower`, `lm_bridge_approach`, `lm_launch_terminal`, `lm_park_pond`, `lm_market_hall`, `lm_rooftop_tower`, `lm_station`, `lm_water_tank`) | None authored — the ghat (`b_c2_transport_ghat`) is the town's natural anchor; no landmark ids are invented here |
| Civic core | School, clinic, bank branch, police station, city office, college (`d1_civic`, `d1_education`) | Primary school, clinic, town office only (`b_c2_civic_school`, `b_c2_civic_clinic`, `b_c2_civic_office`) — no bank, no college, no police station in the data |

Both cities share one river, one economy ledger (Session 03/04: trade flows are SYS-MARKET accounting records between the two cities), and one road graph joined by the persisted regional connections (§6). They do **not** share one coordinate frame — see §3.4.

---

## 3. World Partition Approach — Rupsha City Growing to Multiple Districts

### 3.1 One World Partition map per city, districts as data layers

- **Rupsha City = one World Partition map.** District 1 is the first district inside it, not a map of its own. New districts are added as **Data Layers** on the same map, one layer per district, so a district can be loaded, unloaded, and edited without touching its neighbours.
- **Shibnagar Town = a second, separate World Partition map.** It is a different settlement across a river, in a different local coordinate frame (§3.4); forcing it into Rupsha's map would be a false contiguity. Inter-city travel is a map transition (§6), never a streamed walk across.
- **District 1's data-layer contents are already fixed by the blockout:** its 10 zone boxes (`zone_boxes_m` in `data/district1-blockout.json`), its 42 plots, its 21 road segments, and its 8 landmarks all land in the District 1 layer, cited by their existing ids. The Phase 1 test scene (`phase1_test_scene`: the 400 m × 400 m box x −200…200, z −60…340, 10 segments, 10 plots) is a *subset* of that layer, not a separate map — the same ids, the same coordinates — so Phase 1 performance captures stay comparable as the district grows around it (TECH-DISTRICT1-BLOCKOUT §6).

### 3.2 Per-district data layers

Each district gets its own data layer carrying, at minimum:

| Layer content | District 1 (exists) | Rule for Districts 2+ |
|---|---|---|
| Zone boxes | 10 zones, `zone_boxes_m` | Zones are authored in the district's GDD before any geometry; zone ids follow the `d<N>_<zone>` pattern (`d1_market` → `d2_…`), never reused across districts |
| Plots & buildings | 42 plots, 1:1 with `data/buildings-district1.json` ids | Same 1:1 rule as the blockout: every building in the district's building data appears as exactly one plot, cited by id; ids are forever, positions negotiable inside the zone box |
| Road segments | 21 segments, classes per GDD-02 §3 | New segments extend the district's road graph and must join the existing graph at a named junction — the Session 03 lesson (endpoint snaps ≤25 m/≤50 m, documented in the graph) is the tolerance, not the method |
| Landmarks | 8, four tied to building ids | Each district names its own navigational landmarks in its GDD; a landmark id is as permanent as a building id |
| NPC anchors | Tea stalls, park, market, riverfront promenade, home (GDD-02 §7) | Anchors are chosen from the new district's own places; schedules written against District 1 anchors stay valid because they cite District 1 ids |
| Economy state | Property values from the Unit F model over GDD-02 zones | A new district's property values are priced from its own zones and tiers when its GDD is written — never copied from District 1's table |

**What a data layer does not do:** it does not change the sim. The deterministic sim (Sessions 01–10) already models both cities at the data layer; the UE data layers are the *presentation* of districts the sim knows about. A district that exists only as a UE layer, with no sim-side city/zone rows, is scenery, not a district — Phase 8 does not ship one.

### 3.3 HLOD notes

- **HLOD layers follow the district structure:** one HLOD layer per district, built from that district's data layer, so the densest district (District 1: market spine, old-town lanes, uptown high-rise) can be tuned without re-baking the whole city.
- **District 1's HLOD priorities are set by its own landmarks:** the Clock Tower junction (`lm_clock_tower`, the arterial crossing at (0, −60)), the rooftop restaurant tower (`lm_rooftop_tower` — the district's only high-rise, 12 storeys per Session 03 Unit 05), the market hall and the launch terminal stay recognisable at HLOD distance; the old-town golis (3–4 m lanes, pedestrian-only by class) collapse first, since they are only ever read at street level.
- **Shibnagar's HLOD is simpler by construction:** low-rise town, open farmland to the south, river band to the north — its HLOD layer is a skyline of house/apartment roofs, the ghat, and the market row, with the farmland (`c2_agriculture`, 2 farmland plots + warehouse) as open terrain, not geometry.
- **No HLOD numbers are claimed here.** HLOD cell sizes, draw distances, and proxy budgets are PC-build tuning values, set against measured frame times in Phase 8 — the same rule as every other performance figure in this project (see §8).

### 3.4 Coordinate frames — why the two cities are two maps

- **District 1 frame:** local metres, origin 60 m north of the Clock Tower junction, arterial crossing at (0, −60); river band at the south edge (TECH-DISTRICT1-BLOCKOUT §1, §5).
- **Shibnagar frame:** local metres, origin at the ferry ghat landing; +x east, +z south; river band at the north edge (`data/city2-shibnagar.json`, `coordinate_system`).
- The two frames are **not** the same frame, and the sim knows it: the ferry crossing figures are labelled SIM MODEL precisely because "the two ghats live in different coordinate frames … so no shared metric exists in the data" (`data/transport-config.json`, `RC-FERRY-1`). UE design follows the sim: each city keeps its own origin, each city is its own World Partition map, and travel between them is a transition (§6). Any future "one continuous world" claim would first need a shared georeferenced frame for both cities — that work is not designed here and is not assumed.

### 3.5 Growing Rupsha — Districts 2+ (rules, not inventions)

No District 2 is designed in this document: **no name, no zones, no roads, no buildings, and no prices for any district beyond District 1 are invented.** When the owner orders a District 2, it is authored the same way District 1 was, in this order:

1. A GDD section fixing its zones (ids, character, adjacency to District 1), its road hierarchy, and its landmarks — before geometry.
2. A blockout data file in the `data/district1-blockout.json` shape (zone boxes, plots 1:1 with its building data, segments, junctions, landmarks), with the same "ids are forever, positions are negotiable" law.
3. A data-layer + HLOD-layer pair on the Rupsha map, streamed in at the district boundary.
4. Sim-side rows (city zones, parcels, road graph, infrastructure) so the district is simulated, not just rendered — Sessions 03's city layer is the pattern.

**Adjacency that already exists and constrains District 2's siting:** the bridge approach (`seg_bridge_approach`, (460, 340) → (520, 465)) ends at the district edge as a Phase 8 travel gate (GDD-02 §4; blockout §5); the river closes the south edge; the Phase 1 test scene is the south-east corner. A District 2 that contradicted any of those — a second bridge, a road through the river band, a building on the approach — would need the blockout revised by data revision, never by silent divergence (blockout §7).

---

## 4. District Identity — How Districts Stay Distinct

Phase 8's exit criterion "each city is visibly and economically distinct" applies inside Rupsha too: a new district must not read as District 1 recoloured. The design rules, all drawn from how District 1 and Shibnagar already differ:

- **Architecture follows the district's own GDD**, not a shared kit applied uniformly: District 1's identity is dense river-city (6-storey midtown blocks, old-town walk-ups, the 12-storey rooftop tower as the single high-rise, market hall arches, ghat steps). A new district's architecture is set by its own character statement at GDD time.
- **Economy follows the district's own zones and tiers:** District 1 prices run old-town walk-ups (cheapest) → uptown luxury (GDD-02 §6, Unit F model); a new district's price gradient is authored from its own zones, never copied.
- **Traffic character follows the road hierarchy:** District 1's golis are walking neighbourhoods by class (vehicles physically cannot enter, GDD-02 §3); a new district's movement character is a design decision of the same kind, not a default.
- **The test is the player's eye and the ledger:** the Phase 8 exit check (§9) is that a player can tell the districts apart without a label, and that their property values, rents, and trade flows differ for reasons the data shows — not because a slider was moved.

---

## 5. Shibnagar Town as the Second City — the UE Design Layer over Session 03

Shibnagar is not a new design: it is the UE presentation of the town Session 03 generated and Sessions 03–07 have been simulating. This section is the design layer over that data — what the player sees, and what stays honest about its generated origin.

### 5.1 What the town is (from the merged data)

- **6 zones** (`c2_agriculture`, `c2_civic`, `c2_market`, `c2_residential`, `c2_riverfront`, `c2_transport`), **18 buildings, 22 plots, 7 road segments, 39 residential units** — all in `data/city2-shibnagar.json`, every plot labelled GENERATED.
- **Layout:** a small grid town on the river's north bank. Main Street (`seg_c2_main_st`, collector, 10 m) runs north–south from the ghat (280, 0) to the farmland edge (280, 480); Ghat Road, Mid Town Street and South Street run east–west; West/East Streets close the sides; Farm Road (lane, 4 m) runs along the farmland. No signals anywhere — all 10 junctions are unsignalled (`signalled: false`), which is itself a visible difference from Rupsha's 3 signalled junctions.
- **Terrain:** river band (non-buildable, elevation −3), floodplain strip (buildable, `flood_risk` restriction, elevation 1), farmland (buildable, `agricultural_land`, elevation 2), a beel wetland in the south-east (non-buildable), and plain (elevation 4). The floodplain and wetland are not decoration: Session 03's terrain engine rejects construction on non-buildable regions, and the town's flood risk is a real restriction the UE presentation must show (low ground, water near the ghat), not pave over.

### 5.2 Architecture — distinct from Rupsha, and honestly bounded

- **Low-rise town fabric.** Every Shibnagar building in the data is tier 1–3 (no tier 4–5, no high-rise); the residential stock is houses and small apartment blocks (`b_c2_res_houses_a/b`, `b_c2_res_apts_a/b/c`), the market is a shops row with a godown and a tea stall, the riverfront is fish stalls and a tea stall. The UE direction is: pitched-roof houses, single-market-street shops, open yards — visibly lower, looser, and greener than Rupsha's dense blocks. **Bound:** building heights/floors for Shibnagar are not in any merged data (Session 03 Unit 05 derives floors only from GDD-02 heights, i.e. District 1). No storey counts are claimed for Shibnagar here; the blockout pass for the town sets them, and this document is revised then — the same "positions are v1" discipline as the District 1 blockout.
- **The ghat is the town's centre.** `b_c2_transport_ghat` (Shibnagar Ferry Ghat) sits at the Main Street head (plot `plot_c2_transport_ghat`, x 48…108, z 8…48) with the bus stand beside it (`b_c2_transport_bus_stand`). The town is entered from the river, not from a highway — the opposite of Rupsha, which is entered from the bridge approach and the station quarter.
- **What Shibnagar does not have is part of its identity:** no bank, no college, no police station, no hospital tower, no market hall, no clock tower, no high-rise. A player who needs those goes to Rupsha — that is the point of a second city, and the travel design (§6) exists to make the trip routine rather than a loading-screen event.

### 5.3 Economy — distinct from Rupsha, from the data's own numbers

The contrast is drawn only from figures already in `data/city2-shibnagar.json` (nothing re-priced here; `data/prices.json` is not touched by this unit):

| Fact (from the data) | Shibnagar | Rupsha District 1 (for contrast) |
|---|---|---|
| Economic base | Agriculture: paddy farmland (`b_c2_agri_farmland_a`), vegetable farmland (`b_c2_agri_farmland_b`), produce warehouse (`b_c2_agri_warehouse`); fish stalls on the riverfront | Market/commercial: Boro Bazar market hall, 24 shop units, wholesale godowns, light industry (GDD-02 §2) |
| Residential rents (data) | 1,200–6,000 NCr/month (fish stalls/tea stalls 1,200; apartments 2,500–4,000; houses 4,000–6,000) | Priced by the Unit F model over District 1 zones/tiers (GDD-02 §6; see GDD-03) — the town's band sits at the low end of the city's |
| Buy prices (data) | 350,000–750,000 NCr where listed (apartments/houses); most civic/agricultural stock unpriced (`null`) and not for sale | ~140 units, ~20% listed for sale at world start (GDD-02 §6) |
| Tiers | 1–3 only | 1–5 |
| Civic economy | School, clinic, town office — civic-owned, never for sale | School, clinic, bank, police, city office, college |
| Sim behaviour (Session 03) | Starts unpopulated; populates only by migration (4 households in the 90-day run); month 1–2 municipal revenue 0; first rent revenue month 3 (10,989 NCr) | 245 residents in the same run; tax revenue 324,000–377,000 NCr/month measured from the ledger |
| Trade (Session 03 Unit 14) | Sells produce to the city (farmland parcels × 800 + town produce per resident, SIM MODEL rates, capped by city demand); buys city goods in return — trade flows are persisted SYS-MARKET records, not per-agent hauling (Session 07) | The demand side of that trade; industry workers × 1,500 (SIM MODEL) sizes the city's side |

**UE presentation rule:** the town's economy must be *visible* — farmland worked at the south edge, produce at the warehouse and the fish stalls, the market row busy at a town scale — because the sim's trade flows are accounting records, and a player who cannot see the produce will reasonably conclude the trade is fake. The market hall interior rule from District 1 (GDD-02 §5: key buildings only) applies here too: the town's interiors are the school, clinic, town office exteriors + door interaction until a later unit authors them. No interior is claimed that the data does not support.

### 5.4 The town's sim history is part of the design

- The town starts empty and fills by migration under measured rules (Session 03 Unit 08: unemployed head + debt, or housing > 50% of income; rent ≤ 60% of current rent; ≤ 2 households/month/direction; households younger than 30 days never move). The UE design must therefore present Shibnagar as a place that *grows into* habitation — vacant units are visibly vacant, then occupied — never as a town that was always full.
- Property tax collects ~0 in practice today (genesis properties are ownerless; tax is owners-only by design — Session 03 Limitations). The town's municipal services are funded from measured revenue only (Session 03 Unit 09); the UE presentation shows service levels as they are, not as a funded town would look.

---

## 6. Travel Between Cities — Transition-Based Journeys

### 6.1 The mode table (the honest core of this document)

| Mode | What exists in the data | Phase 8 UE design | What is NOT claimed |
|---|---|---|---|
| **Road (bus / own vehicle / taxi)** | Real: `RC-ROAD-1` bridge connection (Session 03: bridge approach (520, 465) ↔ Shibnagar ghat gate (280, 0)); intercity bus over the bridge (Session 07: 430 intercity bus trips in the 90-day benchmark); bridge crossing 6 min / +1.5 km (SIM MODEL, `data/transport-config.json` `intercity`) | **Drivable / rideable across the bridge in the loaded world:** the player drives or rides the intercity bus from District 1's bridge approach, through the toll plaza, across the bridge, and arrives on Shibnagar's Main Street. The bridge itself is modelled as part of the transition (see §6.2) | The bridge deck geometry is not in the blockout — the approach ends at the district edge (blockout §5). The deck is Phase 8 geometry, authored then, not assumed to exist now |
| **Ferry** | Real: `RC-FERRY-1` persisted connection; both ghats are real buildings (`b_d1_riverfront_launch_terminal`, `b_c2_transport_ghat`); ferry route in `data/transport-config.json` (06:00–20:00, 60-min headway, 45-min crossing, 2.5 km — SIM MODEL); fare 0 at point of use (covered by the monthly `transport_public_bus_rickshaw` living line) | **A scheduled service the player can ride:** board at the launch terminal, crossing sequence, alight at the Shibnagar ghat. The 45-minute crossing is presented as a time-skip with the river view, not 45 real minutes | Organic ferry boardings were 0 in Session 07's benchmark (no ghat-to-ghat schedule demand exists). The service is real and rideable; it is not claimed to be busy |
| **Train** | **Nothing operational.** Station building `b_d1_transport_station` exists; no track network, no timetable, no fares, no rolling stock data exists (Session 07 Limitations) | **Transition-based journey only:** the player buys/enters at the station, a departure sequence plays, a loading transition runs, and the player arrives at the destination city's station-side spawn. The train itself is never simulated en route — no track is driven, no timetable is run | No train is claimed to run, no track is claimed to exist, no station is claimed at the Shibnagar end (there is no station building in the town's data — the arrival point there is the bus stand / ghat area, §7) |
| **Flight** | **Nothing.** No airport, airfield, runway, or flight data exists (see §1, Contradiction 2) | **Transition-based journey only, and only once an airport is sited:** booking UI + departure lounge sequence + loading transition + arrival. Until the airport-siting decision is made, flight is a menu option that honestly says "no airport yet" rather than a fake destination | No flight is claimed to operate, no airport location is given, no aircraft is modelled |

**The rule in one line:** a mode with a network in the data (road, ferry) is travelled *through* the world; a mode without one (train, flight) is travelled *through a transition*. The player is never shown a train driving on track that does not exist, or a plane landing on a runway that was never sited.

### 6.2 The transition design (applies to every inter-city journey)

1. **Depart** at a hub (§7): the player interacts at the hub building, chooses a destination city and a mode. The choice is recorded against the sim's regional connections (`RC-ROAD-1`, `RC-FERRY-1`) where one exists; train/flight choices are recorded as transition journeys with no connection id — the absence is itself the record that no network was traversed.
2. **Cross** — one of two presentations, chosen by mode:
   - *Through-world* (road, ferry): the player stays in control (driving) or rides as a passenger with the world streaming past; the bridge deck / river crossing is the visible threshold between maps, and the destination map streams in as the origin streams out. The crossing figures the sim already uses (bridge 6 min, ferry 45 min — both SIM MODEL) are the *in-world* durations the presentation compresses with a time-skip, never the real-time durations.
   - *Transition sequence* (train, flight): departure lounge/platform sequence → fade/loading → arrival sequence at the destination hub. The game clock advances by the journey's in-world duration; the player never waits in real time for a train that is not running.
3. **Arrive** at the destination hub's spawn point, with inventory, character state, and mission progress intact (the same continuity the plan's Phase 10 exit criteria demand for planet travel, applied here first). Save state is written at departure and at arrival, so a disconnect mid-transition restores the player at one hub or the other — never between maps.
4. **Cost** is charged only where the data prices it: taxi fares per trip at `data/prices.json` `taxi_fares`; bus/rickshaw/ferry covered by the monthly living line (fare 0 at point of use) — both per Session 07. **No train or flight fare is invented here.** Until fares for those modes are authored (a later pricing unit, in `data/prices.json`, not in this document), train/flight transitions are unpriced in the design and the UI says so.

### 6.3 What travel does to the sim

- Intercity commuters are counted live (residence city ≠ workplace city — Session 03 Unit 14; zero until someone actually migrates, then real). UE travel must *feed* that count, not fake it: a player who lives in Shibnagar and works in Rupsha is a commuter by the same definition, recorded the same way.
- Migration (Session 03 Unit 08) and trade flows (Unit 14) continue on their monthly cadence regardless of how the player travels; the player's journeys do not change the trade-flow rates, which are sized from measured facts.
- Road condition and closures (Session 07: a segment under condition 20 or explicitly closed is impassable) apply to the bridge connection as to any segment: if the bridge approach is closed, road travel routes via the ferry, and the UI says so — the detour is a design consequence of the existing data, not a scripted event.

---

## 7. Travel Hubs — Airports and Stations as Functional Hubs

A hub is functional when a player can **arrive, depart, wait, and be told the truth about the next service**. Each hub below is grounded in a building that exists; where no building exists, the gap is stated, not filled.

| Hub | Building (exists in data) | Zone | Function in Phase 8 |
|---|---|---|---|
| **Railway Station (Rupsha)** | `b_d1_transport_station` | `d1_transport` (Station Quarter) | Train departures as transition journeys (§6.1); waiting hall, timetable board showing the *transition* services (explicitly labelled as such — no fabricated departures); landmark `lm_station` (station clock frontage, GDD-02 §4) |
| **Bus Terminal (Rupsha)** | `b_d1_transport_bus_terminal` | `d1_transport` | Origin of `BUS-RUPSHA-LOOP` (6 stops: `d1_transport`, `d1_market`, `d1_midtown`, `d1_civic`, `d1_education`, `d1_uptown`) and of the intercity bus over `RC-ROAD-1` (`data/transport-config.json`) |
| **Launch Terminal (Rupsha)** | `b_d1_riverfront_launch_terminal` | `d1_riverfront` | Ferry departures on `RC-FERRY-1` (06:00–20:00, 60-min headway); green-roofed shed, landmark `lm_launch_terminal`; ghat steps at (0, 432) |
| **Shibnagar Ferry Ghat** | `b_c2_transport_ghat` | `c2_transport` | Ferry arrivals/departures; the town's front door and its natural landmark (no landmark id invented — the building is the anchor) |
| **Shibnagar Bus Stand** | `b_c2_transport_bus_stand` | `c2_transport` | Origin of `BUS-SHIBNAGAR` (4 stops: `c2_transport`, `c2_market`, `c2_residential`, `c2_civic`); intercity-bus arrival point in the town (no station building exists there — see §6.1) |
| **Airport (Rupsha)** | **None — no building, no site, no data** | — | **Open Phase 8 decision.** The hub interface (booking, lounge, transition, arrival) is designed in §6.2; the site, the building, and any airfield geometry are for the owner to site, after which this document is revised with the real ids. Until then the travel menu lists flight as unavailable-with-reason, never as a working service |

**Hub rules:**

- A hub's interior scope follows GDD-02 §5 (key buildings only): waiting hall + ticket point + platform/ghat access. Full terminal interiors are a later content unit, not Phase 8.
- Hubs are NPC anchors as well as player infrastructure: the Station Quarter already hosts rickshaw/CNG stands (GDD-02 §2, `d1_transport`), and NPC schedules anchor to the market, park, tea stalls, riverfront promenade, and home (GDD-02 §7) — hub waiting is a schedule anchor the NPC system can use once hubs exist, not a behaviour invented here.
- **No hub is duplicated across cities by copy-paste.** Shibnagar's ghat-and-bus-stand pair is a town-scale hub; giving it a railway-station-shaped building would contradict its own data (no station building exists there) and its economy (a town of 39 units does not run a railway terminus).

---

## 8. Frame Budget — Per District (Design Targets, Never Measured Claims)

- **The only measured performance numbers in this project are from the Godot testbed and the headless sim** (Session 03: 242 × 90 days in 23.4 s; Session 07: 98.9 s with the transport layer). **No UE frame rate has ever been measured**, because no UE build exists yet. Every figure in this section is a *design target* for the owner's PC build to hit or miss honestly.
- **Target (from the plan, Phase 1 exit criteria):** stable **≥ 30 fps at 1080p on High** (target 60 on the recommended spec, plan Part F) with no traversal hitches that break immersion. Phase 8 adopts the same target **per district**: the frame budget must hold in the densest district, not on average across the city.
- **Densest district (design assessment, to be confirmed by measurement):** District 1 — the market spine (pedestrian-priority 07:00–22:00, densest crowds), the arterial crossing, and the uptown high-rise in one view. Shibnagar, as a low-rise town with open farmland, is expected to be the cheaper map; that expectation is a hypothesis for the PC capture, not a claim.
- **Budget discipline per district, from the plan's own levers (Part C #4–#5, Part F):** Nanite + Lumen on, HLOD per district (§3.3), Mass crowds for ambient NPCs (never full MetaHumans — Part C #1), distant traffic Mass-simulated not full physics (Part C #7), data layers streamed so only the player's district and its neighbours are resident.
- **What "holds" means at Phase 8 exit (§9):** the packaged build is captured on the owner's PC in each district at the Phase 1 settings, and the capture — not this document — says whether the budget held. If a district misses, the fix is HLOD/density tuning in that district's layer, recorded as a data revision; the budget is never met by lowering the target after the fact.

---

## 9. Phase 8 Exit Criteria (from the Migration Plan, Part D)

The plan's Phase 8 exit criteria, verbatim in substance, with how each is checked in this design:

| # | Exit criterion (plan) | How Phase 8 checks it |
|---|---|---|
| 1 | **Travel between cities works in a packaged build** | A packaged build on the owner's PC: the player departs Rupsha by road (bridge) and by ferry, arrives in Shibnagar, and returns — with inventory, character state, and mission progress intact (§6.2 step 3). Train/flight transitions are checked as transitions, with their no-network status visible in the UI, not hidden |
| 2 | **Frame budget holds in the densest district** | §8: per-district capture at 1080p High on the owner's PC; the densest district (District 1 by design assessment) holds ≥ 30 fps stable, target 60 |
| 3 | **Each city is visibly and economically distinct** | §4–§5: a player can tell Rupsha from Shibnagar without a label (dense river-city vs low-rise farm town; market hall vs market row; high-rise vs ghat), and the ledger shows it — different rents, tiers (1–5 vs 1–3), different economic base (market/commercial vs agriculture), different trade direction (city demand vs town produce) |

**Preconditions (not exit criteria, but gates):** Phase 5's District 1 and Phase 6's society must have passed their own exit criteria first (plan Part H: no phase starts until the previous phase's exit criteria pass in a packaged build). Phase 8 does not start by building a second city on top of an unproven first one. The Shibnagar blockout (plots, segments, junctions in the town's own frame, in the `data/district1-blockout.json` shape) is the first Phase 8 work item, and it is data work — the town's geometry contract must exist before any UE level work, exactly as District 1's did.

---

## 10. Boundaries — What This Document Deliberately Does Not Decide

- **Multiplayer (Phase 9, TECH-MULTIPLAYER.md).** That document sets **one district per server in v1, 8–16 concurrent players**, and states explicitly: *"No sharding, no instancing, no cross-server travel is designed here; Districts 2+ and planets (Phase 8/10) raise travel questions this document does not answer."* This Phase 8 design is therefore **single-player**: inter-city travel here is a local map transition. Extending it to multiplayer — whether a second city is a second server, a shard, or an instance — is a Phase 9 decision, not smuggled in here. Nothing in §6–§7 assumes a server, a session, or another player.
- **No netcode, no replication numbers, no hosting.** Per TECH-MULTIPLAYER §7, those are Phase 9 implementation choices; inventing them in a Phase 8 design document would be fiction.
- **No planet travel.** City → station → planet is Phase 10 (Unit AG, `docs/GDD-14-SPACE-AND-PLANETS.md`); the transition pattern in §6.2 is deliberately the same shape the plan uses for planets (Part C #16: "travel = loading/transition sequence"), but no planet, station hub, or gravity parameter is designed here.
- **No new prices, fares, or wages.** Train/flight fares do not exist in `data/prices.json` and are not invented here (§6.2 step 4); Shibnagar's rents and buy prices are quoted from `data/city2-shibnagar.json` only. Any new fare is a later pricing unit's work, in `data/prices.json`, with the same "every number resolves to prices.json" rule as Units AH/AI.
- **No child/elder or life-stage content.** The Phase 7 asset gate (plan Part C #9) is untouched by this document; a second city does not solve it.
- **No UE implementation.** World Partition, Data Layers, and HLOD are named as the engine mechanisms (plan Part C #5); no `.umap`, no Blueprint, no C++ is written or claimed here. The first proof of any of it is the owner's PC build.

---

## 11. Cross-Reference Index (verification record)

Every cross-reference in this document was checked against the merged repo on 2026-11-22 (Unit AF verification). Ids, files, and sections cited:

- **Files:** `NEXORA-MIGRATION-PLAN.md` (Part D Phase 8; Part C #5, #15, #16; Part F; Part J) · `docs/GDD-02-RUPSHA-CITY-DISTRICT1.md` (§2 zones, §3 roads, §4 landmarks, §5 interiors, §6 property stock, §7 NPC anchoring, §8 exclusions) · `docs/TECH-DISTRICT1-BLOCKOUT.md` (§1–§7) + `data/district1-blockout.json` (10 zone boxes, 42 plots, 21 segments, 8 landmarks, `phase1_test_scene`) · `data/buildings-district1.json` (42 buildings; `b_d1_transport_station`, `b_d1_transport_bus_terminal`, `b_d1_riverfront_launch_terminal`) · `data/city2-shibnagar.json` (city id `shibnagar_town`, 6 zones, 18 buildings, 22 plots, 7 segments, 39 units, coordinate system, terrain regions, river band) · `docs/SESSION-03-REPORT.md` (Units 01, 08, 10, 14; 90-day run figures; Limitations) · `docs/SESSION-07-REPORT.md` (transport layer; Limitations — rail/air position; benchmark figures) · `docs/TECH-MULTIPLAYER.md` (§2 session shape, §5 scale limits, §7 undecided items) · `data/transport-config.json` (`intercity`, `transit_routes` incl. `BUS-RUPSHA-LOOP`, `BUS-SHIBNAGAR`, `RC-FERRY-1`; SIM MODEL notes) · `docs/GDD-03-ECONOMY-AND-PROFESSIONS.md` (Unit F pricing model, referenced for contrast only — no numbers copied) · `docs/GDD-04-MISSIONS-AND-PROGRESSION.md` (referenced only via Unit AG's scope note in §10 — no mission ids cited).
- **Regional connections:** `RC-ROAD-1` (bridge approach (520, 465) ↔ Shibnagar ghat gate (280, 0)) and `RC-FERRY-1` — Session 03 Units 01/14; `tools/sim/regional.py`.
- **Deliberately not cited:** GDD-11 / GDD-12 (Units AH/AI territory — not touched by this unit) · `data/prices.json` (not edited; taxi-fare and living-line rules are cited by line name from Session 07, never copied as numbers) · any District 2+ or airport id (none exists — see §1, Contradiction 2, and §3.5).
- **Counts checked:** District 1 — 10 zones, 42 plots/buildings, 21 segments, 8 landmarks, 3 signalled junctions, 9 junctions total (blockout §3); Shibnagar — 6 zones, 18 buildings, 22 plots, 7 segments, 10 junctions (all unsignalled), 39 residential units; Session 03 90-day run — Rupsha 245 / Shibnagar 5, 4 households migrated, first town rent revenue month 3 (10,989 NCr); Session 07 benchmark — 430 intercity bus trips, 0 organic ferry boardings, 85,189 total trips.

*End of TECH-MULTIDISTRICT v1.0 — Unit AF, Queue 6. Design only; no UE code, nothing claimed built.*
