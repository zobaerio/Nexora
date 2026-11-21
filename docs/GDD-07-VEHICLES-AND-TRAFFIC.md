# NEXORA — GDD-07: Vehicles & Traffic Design

**Unit P · Version 1.0 · 2026-11-21**
**Parent documents:** `NEXORA-MIGRATION-PLAN.md` Phase 5 · `docs/GDD-02-RUPSHA-CITY-DISTRICT1.md` §3 (road hierarchy), §2 (zones), §5 (interiors) · `data/vehicles.json` (the data contract for this document) · `data/prices.json` (`vehicles`, `taxi_fares`, `living_costs` — owns every price) · `docs/GDD-03-ECONOMY-AND-PROFESSIONS.md` §3.3 (vehicle prices), §8 (taxi loop) · `docs/GDD-06-NPC-BEHAVIOUR.md` §2 (`Commute`), §4.6 (taxi fare loop), §7 (weather effects) · `data/weather-presets.json` (`gameplay_effects`) · `docs/GDD-05-UI-AND-PANELS.md` (interact prompt, HUD)
**Status:** DESIGN ONLY. No vehicle pawn, Chaos Vehicles asset, Zone Graph or traffic spawner exists yet; nothing here claims a vehicle moves today. This document is the contract Phase 5 implements against.

> **Design law:** traffic is the society, moving. Every vehicle on the road is either a character travelling (GDD-06 `Commute`), a worker working (taxi fare loop, truck deliveries, bus routes), or a parked owned asset with an owner in the data. There is no decorative traffic spawned to make the city *look* busy — density comes from the schedule system, and if the street is empty at 03:00 that is the design working, not a bug.

---

## 1. Vehicle Classes

Nine entries in `data/vehicles.json`, one per class the district's road hierarchy actually carries (GDD-02 §3). Prices are **not** restated here — each player-buyable entry carries a `price_ref` into `data/prices.json` `vehicles`, and prices.json wins any disagreement (the Unit L rule).

| Class (data id) | Role in District 1 | Player | Roads |
|---|---|---|---|
| `bicycle` | Starter vehicle; the only motor-free class allowed everywhere cycles go | Buy 8,000 · drive | Collector, local, lane, promenade |
| `rickshaw` | Passenger workhorse of the old town; taxi-driver starter | Buy 25,000 · drive | Collector, local, lane |
| `cng_auto_rickshaw` | Mishuk — stand/depot fleet, hireable | Ride only (v1) | Arterial, collector, local |
| `motorbike` | The district workhorse | Buy 120,000 · drive | Arterial, collector, local |
| `car_small` | Mid-tier ownership goal | Buy 450,000 · drive | Arterial, collector, local |
| `car_premium` | Upper-tier marker | Buy 1,200,000 · drive | Arterial, collector, local |
| `taxi` | Licensed fare-loop cab | Buy 650,000 or rent 200/day · drive | Arterial, collector, local |
| `bus` | Fixed-route traffic, terminal ↔ district edge | Ride as scenery (v1) | Arterial, collector |
| `truck` | Freight: market deliveries pre-07:00, site deliveries (GDD-08) | Not in v1 | Arterial, collector |

Speeds, capacities and fuel figures in the data are **v1 traffic-model values** (cruise speeds feed §3), not handling claims. Fuel cost to the owner is the monthly upkeep band in `prices.json` `living_costs.transport_own_car_fuel_upkeep` (mid 3,500 / upper 8,000 NCr) — per-litre pump pricing is deliberately not invented (see §8).

## 2. Ownership

- A bought vehicle is an asset row for its owner character (the `inventory_items` family in `schema.sql`, item type `vehicle`, payload = vehicles.json id + condition §4). It is bought with a ledger row (reason `purchase`) from a dealer location — v1: the transport depot office in `d1_industry` (GDD-02 §5) sells/rents taxis; a used-vehicle corner at `d1_transport` handles the rest. Both are design placements on existing GDD-02 interiors, not new buildings.
- The taxi is rentable before it is buyable (200 NCr/day from `prices.json` `taxi_fares`) — the designed on-ramp for the Taxi Driver loop, matching GDD-03 §8.
- A vehicle has exactly one home parking anchor (§6). It does not despawn when the player walks away; it persists where parked, and its position is runtime state in the save (the Unit M rule: position is not society truth, the ownership row is).

## 3. Traffic Flow Model

Traffic is generated from three sources, in priority order — never from a blind spawner:

1. **Characters travelling.** A GDD-06 `Commute` block whose transport choice is a vehicle puts that character's vehicle (or a hired one, §5) on the road graph between anchors. Full-tier NPCs drive their own; Scheduled-tier NPCs are represented on the graph without full vehicle physics (the Phase 2 sheet's tier rules applied to vehicles).
2. **Workers working.** Taxis run the §4.6 fare loop (`Cruise → Pickup → CarryPassenger → Dropoff`), trucks run delivery schedules (market godowns before 07:00; construction sites per GDD-08 §4), buses run fixed terminal loops.
3. **Ambient density.** Ambient-tier representation only, capped per road class (below), despawned outside the player's streaming radius. Ambient vehicles never enter lanes, never park in front of the player's door, and never carry anyone the simulation knows by name.

| Road class | Ambient cap (v1, both directions) | Speed behaviour | Rules |
|---|---|---|---|
| Arterial | 24 | Cruise speeds from vehicles.json; signalled junctions ×3 (GDD-02) | No parking on the carriageway; buses/trucks present |
| Collector | 14 | Cruise −20% at ring junctions | CNG/rickshaw mix is the visual signature |
| Local street | 6 | Walking-pace courtesy near parked cars | Parking pockets (§6) are part of the road, not scenery |
| Lane (goli) | 0 motor | Rickshaw/bicycle cruise only | Motor classes are *physically* barred (GDD-02) — the traffic system never routes them in |
| Promenade | 0 motor | Cycles only | Food carts are static anchors, not traffic |

**Time-of-day shape** comes from the schedule system, not a density curve file: morning/evening commute peaks are emergent from `npc-schedules.json` block times; the market spine bollard window (pedestrian-priority 07:00–22:00, GDD-02 §3) reroutes motor traffic to the collector ring for those hours, and the truck delivery window exists *because* of that rule.

**Routing** is the Zone Graph over the road classes (Unit R supplies the segment data). A route never crosses a class the vehicle is barred from; a rickshaw route through the old town is shorter *and* legal where a car route must go around — local flavour as a routing fact, not a skin.

## 4. The Drivable Vehicle (player)

Design targets for the Phase 5 playable vehicle (the taxi is the first drivable class, because the fare loop is the first driving job):

- **Enter/exit:** context interact at the driver door (GDD-05 prompt rules). Entering takes possession of the vehicle pawn; the character's schedule/state records `driving` so the society systems know where the character is.
- **Camera:** chase camera on the movement boom family (TECH-MOVEMENT values as the starting point: 4.5 m boom, collision shortening), raised and pulled back for the vehicle; free-look while driving mirrors the on-foot look rules. No cinematic cameras in v1.
- **Controls:** the driving action set joins the existing Enhanced Input table (steer/throttle/brake/handbrake/horn/exit) — defined here as a contract, mapped in `DefaultInput.ini` when the pawn exists on the owner's PC.
- **Damage-lite:** collisions accrue a `condition` value (100 → 0). Condition affects exactly three things in v1: visible cosmetic state, top cruise speed (−25% below 40 condition), and repair cost. Repair is a ledger `purchase` row at the `d1_oldtown` repair workshops (GDD-02 §2) priced from the damage amount — a money sink the economy can price, not a minigame. There is **no** total-loss, no vehicle health bar, no explosion, and no pedestrian-harm system in v1; hitting a character is a hard stop + a police/relationship consequence handled by GDD-06 interrupts, never a score event.
- **Failure honesty:** handling feel (Chaos Vehicles tuning, grip curves under `road_grip_down`) can only be tuned on the owner's PC. This document fixes *rules and numbers the design owns*; it does not claim the car feels right.

## 5. Taxi & Hire — the Fare Loop Hookup

The player taxi loop (GDD-03 §8) and the NPC taxi loop (GDD-06 §4.6) are **the same machine**; the only difference is who sits in the driver seat.

- **Fares** come from `prices.json` `taxi_fares` and nowhere else: base 60 NCr + 25 NCr/km, surge ×1.5 under the listed conditions (`rain`, `night`), rounded to integer NCr before any ledger row is written (GDD-01 §8: no floats near money). Payment is a ledger row at `Dropoff` (reason `purchase` from passenger, or the profession's per-fare pay path for the player — GDD-03 §8 owns the split with the depot/rental).
- **Passengers** are Scheduled NPCs in `Commute` with a taxi preference, or Ambient visuals (GDD-06 §4.6). Demand rises under weather `gameplay_effects` `taxi_demand_up` (rain) / `taxi_demand_up_high` (storm) — the same flags that raise surge, so bad weather is the taxi driver's good shift by construction.
- **Rickshaw/CNG hire** is the same loop at lower speed and shorter range: rickshaws serve lane-edge ↔ stand trips inside the district; CNGs serve collector/arterial trips. Both use the fare table family via GDD-03 §8's rules; no separate price list is invented here.
- **The player's own Commute** can spend money the same way: hailing a cab is a `purchase` ledger row and a ride in an NPC-driven taxi on the road graph — the player experiences §3 traffic from the passenger seat.

## 6. Parking & Stands

| Place | What parks there | Source |
|---|---|---|
| Local-street parking pockets | Player + NPC cars, motorbikes | GDD-02 §3 (local street definition) |
| `d1_transport` stands | Rickshaws, CNGs for hire; bus terminal bays | GDD-02 §2 (`b_d1_transport_stands`, `b_d1_transport_bus_terminal`) |
| `d1_industry` depot | Taxis (owned + rental fleet), trucks overnight | GDD-02 §2/§5 (transport depot) |
| Building anchors | One vehicle anchor per residential block (visitor/owner) | Unit R blockout data carries the anchors |

A parked player vehicle is saved where left (Unit M runtime state). An NPC's vehicle parks at its owner's home/work anchor — which is why streets fill and empty with the schedule day.

## 7. Weather on the Road

Consuming `data/weather-presets.json` `gameplay_effects` (the GDD-06 §7 table is the NPC side; this is the vehicle side):

| Flag | Presets | Traffic effect |
|---|---|---|
| `road_grip_down` | `rain` | Cruise speeds −20% for motor classes; damage-lite condition loss per collision unchanged (grip is a speed story in v1, not a crash lottery) |
| `road_grip_down_high` | `snow` (zone-gated) | Cruise −40%; rickshaw/bicycle ambient halved |
| `taxi_demand_up` / `taxi_demand_up_high` | `rain` / `storm` | §5 demand + surge |
| `outdoor_work_halted` family | `storm` | Truck deliveries to construction sites suspend with the site (GDD-08 §6); market pre-07:00 deliveries still run (they are the exception that feeds the city) |

## 8. What This Document Deliberately Does Not Decide

- **No buy prices for bus, truck or CNG auto-rickshaw.** `prices.json` v1.0 has none; inventing them here would break the single-source rule. If the owner wants player-owned trucks/buses, that is a prices.json v1.1 change with its own unit.
- **No per-litre fuel price.** Monthly upkeep bands in prices.json carry the cost in v1; pump pricing waits for the Phase 6 economy pass (Unit T's simulator may flag it).
- **No multiplayer vehicle sync.** Replication of vehicles and traffic is Unit S / Phase 9 territory; §3's tier rules are written so Ambient traffic is local-only by construction, which is the decision Unit S will formalise.
- **No handling/physics claims.** Cruise/top speeds are traffic-model inputs. How a car *feels* is a PC tuning task (Phase 5), and this document will be revised by what the owner finds there — not the other way round.
- **No new zones, roads or interiors.** Every place named above exists in GDD-02; Unit R turns them into buildable segment/anchor data.
