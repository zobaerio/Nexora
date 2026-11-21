# Session 03 Report — Advanced City & Urban Development Engine

**Status: COMPLETE (2026-11-21).** All 14 units implemented by
extending the runnable deterministic sim core at `tools/sim/`
(stdlib only) — Sessions 01/02 modules were extended, never
recreated or replaced. Proven by 81 new automated tests; the full
suite is **183 tests, all passing** (53 Session 01 + 49 Session 02
+ 81 Session 03), including the no-regression file: economy_sim
output md5 `16740182867525bd659735deeb05150a` (byte-identical to
the pre-Session-01 baseline), Godot testbed `PLAYER_TEST_PASS`
8/8, `tools/validate_data.py` green (extended with city2 checks).

**Gate:** Session 03 began only after Session 02 completed and
merged (PR #13, main `5be75f07`, 102 tests) under the owner's
standing gate rule (2026-11-21 08:32), on the owner's
"BEGIN SESSION 03" order.

**One criterion is NOT claimed:** Unit 12's acceptance criterion
13 (3D rendering performance) belongs to the Unreal build on the
owner's PC. It is recorded **DEFERRED** — no test in this suite
asserts it, and this report does not claim it passed. What this
session delivers for Unit 12 is the data layer UE will consume.

## The 14 units

| Unit | Module(s) | What it does |
|---|---|---|
| 01 City Generation / Registry | `cities.py`, `citygen.py`, `data/city2-shibnagar.json` | A cities layer over the existing world. Rupsha City (District 1) is city #1: identity, boundary from the blockout extents, climate **derived** from the weather-preset weights the engine draws from (`tropical_monsoon`), development level + economic class derived monthly from sim facts (Unit 10). A second city — **Shibnagar Town**, across the river — is produced by a deterministic generator (`citygen.py`) through the same spec shape District 1 uses; its data file is labelled GENERATED in-file, the label is guarded by `validate_data.py`, and generator reproducibility is byte-identical under test. The town ships with 6 zones, 18 buildings, 22 plots, 39 residential units, 7 road segments — and zero residents (see Limitations). |
| 02 Terrain Engine | `terrain.py` | Terrain regions under both cities: District 1's river band (from the blockout's river geometry), the Central Park pond wetland (the pond sits in the unplotted gap between the two park plots — the region is sized to that gap), the southern floodplain (`flood_risk` restriction), the NE hills, plain; a generated set for the town. `validate_build` rejects any footprint intersecting non-buildable terrain — test-proven against the river, and every structural District 1 plot is test-proven to pass. Construction (Unit 11) validates terrain before any project opens. |
| 03 Land Parcels | `parcels.py` | All 64 plots (42 authored + 22 generated) become parcels: id, coordinates, area (= w×d), zoning category, ownership, development status, market value (building value from data where a building stands; labelled SIM MODEL land rates per sqm where it does not), and a persisted ownership history (`parcel_history`, genesis row per parcel). Transfers move real money through the ledger; protected parcels (park, civic) refuse transfer; subdivide/merge conserve area exactly. |
| 04 Zoning | `zoning.py` | The 10 design categories mapped onto the district's real zones and buildings (school→educational, clinic→healthcare, police/city office→government, godowns→industrial…). `validate_placement` enforces allowed-category sets per zone category and a housing density cap (1 unit / 40 sqm). Existing nonconformities (e.g. the market godowns — industry inside a commercial zone) are **reported as grandfathered**, not silently rewritten. Construction validates zoning and raises on violation. |
| 05 Buildings | `buildings.py` | `building_state` extends the data buildings **in place** (keyed by the existing building ids — no parallel table): floors from GDD-02 heights (midtown blocks 6; the rooftop-restaurant tower 12, the district's only high-rise), deterministic construction years by zone age band, condition with monthly decay (doubled under decline pressure, Unit 10), maintenance that restores condition, economic value from data prices, and occupancy read live from tenancies (falling back to the data file's own unit status before any population exists). |
| 06 Road Network | `roads.py` | A real geometric graph from the segment data: node merging, splits at junctions/crossings/endpoints-on-segments, Dijkstra shortest-time pathfinding, per-mode legality from GDD-07 (motor / rickshaw / cycle / walk). Blockout v1 near-misses are joined by **documented endpoint snaps** (≤25 m onto a line, ≤50 m endpoint-to-endpoint, never across an existing crossing; every snap is reported in the graph and the export). Travellers snap to the nearest node on *their own* mode's network. The cycle/rickshaw fragmentation off the arterials is the GDD-07 design (bicycles: collector/local/lane/promenade only) and is test-asserted as such. Persisted segment lengths come from graph geometry, so the stored network and the routed network are the same one. |
| 07 Infrastructure | `infrastructure.py` | 8 networks (electricity, water, wastewater, drainage, solid waste, street lighting, telecom, public transport) × 16 zones = 128 state rows. Capacity from building counts (labelled SIM MODEL base per building); demand from live residents + workplaces (profession `workplace_zone`). Weekly recompute; states ok / strained (≥0.85) / overloaded (≥1.0). Monthly, overloaded networks degrade the matching resident needs (water→healthcare, waste→…, via the needs engine) — test-proven by crushing a zone's water capacity and watching residents' healthcare fall. `headroom()` feeds the growth gate. |
| 08 Population Distribution | `distribution.py` | Households already occupied real units (Sessions 01/02); this unit adds the city-level read models — housing pressure (occupied/total per city: 140 Rupsha, 39 Shibnagar), zone density per km², residential demand (indebted households + adults waiting to form households) — and **intercity migration**: a household qualifies only from measured pressure (head unemployed AND debt > 0 or last month's housing > 50% of income / no income), moves only to a unit renting ≤ 60% of its current rent, at most 2 households/month/direction, households younger than 30 days never move. Moves ride Session 02's `move_household`, and are recorded in `migration_records` + life events. |
| 09 City Services | `services.py` | The municipal month, funded **only** from designed revenue: property tax at GDD-03 §4.2's rate (0.5% of value/yr, owners only — genesis stock is ownerless, so this line is honestly 0 until someone owns), wage taxes and rents **measured from ledger rows** to SYS-CITY (never re-invented), attributed per city (rent split by occupied-unit share — an attribution model over measured totals). Roads decay by class wear (+ storm wear), then maintenance is scheduled worst-first toward condition 85 at a labelled SIM MODEL 2 NCr/m/point, capped by SYS-CITY's **real balance** — `_spend` can never overdraw. Street cleaning / waste / administration are funded per resident at labelled SIM MODEL rates; parks maintenance restores the park's condition. Budgets (per city per month) and current service levels are persisted. |
| 10 City Growth | `growth.py` | Development is **derived, never rolled**: `city_metrics` computes the development index (occupancy 25, employment 25, building condition 20, infrastructure headroom 15, service levels 15), level bands (emerging / developing / established / advanced), and economic class from the economy's own `band_for` mix. Monthly: vacancy < 8% + measured demand > 0 + no active project → the city commissions construction (Unit 11) — in District 1, which has no vacant residential parcel, that honestly means **densification** (an extension on the lowest-tier apartment block), and only when SYS-CITY's balance covers estimate + fee. Vacancy > 30% + measured population loss → decline pressure (event persisted; building decay doubles). Parcel values drift with the vacancy signal, bounded −2%/+3% per month. Level changes persist as milestone events. |
| 11 Construction Lifecycle | `construction.py` | GDD-08's lifecycle in the sim: land selection → planning → design approval → **financing** → construction approval → foundation → frame → walls → roof → finishing → completion → occupancy, plus renovation and demolition kinds. The BOQ is GDD-08 §3 verbatim: at scale 1.0 the materials estimate is **exactly 86,700 NCr** (foundation 20,450 / frame 27,450 / walls 13,775 / roof 19,275 / finishing 5,750 — test-asserted per stage). Money path: client → engineer (`construction_funding`, estimate + fee at the financing stage; an unfunded client freezes there — GDD-08 §6.4, test-proven), engineer → SYS-MARKET per stage *before* work. Labour is real: the engineer and ≥2 crew must be employed `civil_engineer` / `construction_worker` agents. Storms halt outdoor stages (test-proven). A stage completing without a living employed engineer is recorded **uninspected** and risks a defect roll (keyed RNG stream) costing 40% rework. Fees: 10% entry / 15% tier ≥ 3 (GDD-08 §6.1); the engineer's net after a clean project is exactly the fee (test-asserted against balances). Completion creates real property rows + a `building_state` row (`b_d1_built_NNN` / `b_c2_built_NNN`), marks the parcel developed, and the client household **moves in** — project status `occupied`, proven end-to-end in tests. |
| 12 Visualization (data layer) | `cityview.py` | **Honest scope:** the 3D engine is Unreal on the owner's PC and cannot be built or benchmarked in this VM. Delivered: `export_city_state()` — one JSON-ready document per city (registry, zones, terrain, parcels, buildings with live occupancy, road graph nodes/edges/conditions + documented snaps, infrastructure, services, analytics) that UE will consume later — and `ascii_map()`, a map view drawn from the real coordinates (river, roads, buildings), plus CLI `--city`, `--city-map`, `--analytics`. **Acceptance criterion 13 (3D performance): DEFERRED to the owner's PC build. Not claimed.** |
| 13 City Analytics | `analytics.py` | Every statistic is computed live from rows at call time: population, density per zone, housing availability, residential demand, employment rate, income-band mix, land values, building distribution by condition, road connectivity (walk components, total km, average condition), infrastructure load per network, construction activity, municipal budget summary, and the development block (index/level/class/headroom/services). Monthly snapshots persist to `city_statistics` (the history Unit 10 reads). Test-proven to change when the world changes (a migration moves the town's population off 0). |
| 14 Multi-City Interaction | `regional.py` | Two persisted connections: RC-ROAD-1 (bridge approach (520,465) ↔ Shibnagar ghat gate (280,0)) and RC-FERRY-1. `intercity_route` pathfinds across both cities' graphs joined by the connection — test-proven to route via RC-ROAD-1. Commuters are counted live (residence city ≠ workplace city — zero until someone actually migrates, then real). Monthly trade flows are persisted, sized by measured facts with labelled SIM MODEL rates (industry workers × 1,500 capped by town demand; farmland parcels × 800 + town produce per resident, capped by city demand) as SYS-MARKET accounting records. |

**Engine wiring:** `generate_population` → city setup;
daily → construction progress (with the day's weather); weekly →
infrastructure recompute; monthly → infrastructure effects,
services, migration, growth, regional flows, analytics snapshots,
registry refresh. Every city pass no-ops when the city layer is
not set up, so hand-built Session 01 test worlds are untouched.
Summary + CLI gained the city fields and views.

## Database changes

No changes to `data/schema.sql` (the Phase 9 PostgreSQL design,
as in Sessions 01/02). The SQLite schema grew **additively only**
(`CREATE TABLE IF NOT EXISTS` — existing worlds open unchanged):
`cities`, `city_zones`, `terrain_regions`, `land_parcels`,
`parcel_history`, `building_state`, `road_segments`,
`infrastructure_state`, `municipal_services`,
`municipal_budgets`, `construction_projects`, `city_events`,
`city_statistics`, `regional_connections`, `trade_flows`,
`migration_records`. Each is a structure schema.sql lacks —
recorded here as gaps for a future schema revision, same
discipline as Sessions 01/02. One new data file:
`data/city2-shibnagar.json` (Unit 01, GENERATED, labelled).

## Test results (actual output)

```
$ python3 -m unittest discover -s tools/sim/tests
Ran 183 tests in 56.8s
OK
```

New Session 03 tests (81): cities 5, terrain 6, parcels 6,
zoning 7, buildings 7, roads 9, infrastructure 3, distribution 6,
services 3, growth 3, construction 6, cityview/analytics 4,
regional 4, session03 acceptance 12. (Counts include the
occupancy-from-tenancies engine test and the two design-assertion
road tests.)

Bugs the new tests caught and this session fixed: endpoint
snapping originally *recorded* snaps without joining the segments
(the district graph was 3 components, not 1); travellers snapped
to nodes their mode cannot legally use; junction points no
segment passes through became phantom nodes; the pond wetland
region overlapped the food-carts plot (sized to the pond's actual
unplotted gap instead); persisted road lengths now come from
graph geometry.

Acceptance mapping (the owner's 14 criteria): 01 two cities
registered with derived identity ✓; 02 terrain rejection ✓;
03 parcels + history ✓; 04 zoning enforcement ✓; 05 building
state on real buildings ✓; 06 connected graph + valid routes ✓;
07 infrastructure coverage + overload effect ✓; 08 real housing
stock both cities ✓; 09 budgets from a live engine run ✓;
10 growth metrics live + commission/decline proven at unit level
✓; 11 full construction project completes and is occupied ✓;
12 export + map data layer ✓; **13 DEFERRED (owner's PC)**;
14 intercity route + commuters + persisted trade flows ✓.

## Performance observations (real numbers, this VM)

- 242 agents × 90 days with the full city layer: **23.4 s** wall
  (Session 02's same run: 39.8 s at its merge; the current tree
  runs the combined workload faster — different machine load, so
  no speedup is claimed; the honest statement is that the city
  layer's weekly/monthly passes are bounded batch sweeps and the
  90-day run stays in the tens of seconds).
- 90-day observation run (seed `bench`, population 242):
  250 alive, **0 ledger mismatches**, city populations
  Rupsha 245 / Shibnagar 5 — **4 households migrated to the town
  organically** through the monthly pass (the town's first rent
  revenue appears in month 3: 10,989 NCr), 5 trade flows,
  Rupsha tax revenue 324–377k NCr/month measured from the ledger,
  services spend ≈ 9.5k/month. No construction was commissioned
  in this run — vacancy stayed high, so the growth gate honestly
  did not fire; commissioning is proven in the unit tests where
  the pressure conditions are constructed.

## Limitations (stated, not hidden)

- **Criterion 13 is DEFERRED**, as scoped: no 3D anything was
  built or benchmarked in this VM. The export is the contract;
  the Unreal side is the owner's PC work.
- **Shibnagar starts unpopulated.** Its 39 units enter the same
  vacant-unit pool, but genesis households are placed in
  District 1 (Sessions 01/02 behaviour, preserved); the town
  populates only through Unit 08 migration (4 households in the
  90-day run). Its month 1–2 municipal revenue is therefore 0 —
  real, not a bug.
- **Property tax collects ~0 in practice today**: genesis
  properties are ownerless (tenancies, not ownership), and the
  tax is owners-only by design. The rate, assessment and
  collection path are implemented and unit-tested with an owned
  property; the line becomes material when an ownership mechanic
  lands.
- **Labelled SIM MODEL numbers** (not from design data, stated
  wherever used): land rates per sqm for unbuilt parcels,
  infrastructure capacity per building, road maintenance
  2 NCr/m/point, per-resident service rates (cleaning 12 / waste
  8 / admin 6), trade-flow rates, infrastructure demand weights.
  Everything the design data prices (rents, BOQ, fees, tax rate)
  comes from the data.
- **Crew wages** ride the existing monthly wage system (crew are
  employed agents); construction does not pay a separate daily
  wage — GDD-08's labour costing is the fee + materials path.
- **Trade flows are accounting records** sized from measured
  facts via SYS-MARKET aggregates; there is no per-agent hauling
  simulation.
- The road graph's endpoint snaps are a documented tolerance for
  the v1 blockout's grid approximation (TECH-DISTRICT1-BLOCKOUT:
  "positions are negotiable"); a future precise blockout can
  retire them.
- Government/politics remains ABSENT (per the audit) — municipal
  services here are an economic/maintenance model, not a
  government simulation. No later session has been started.
