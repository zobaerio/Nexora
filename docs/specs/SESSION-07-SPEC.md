# SESSION 07 — Transportation, Mobility & Smart Infrastructure Engine (owner spec, received 2026-11-21)

Gate rule: starts only after Session 06 passes. Audit first; reuse Session 03 road networks/buildings/geography, Session 04 logistics, Session 05 infrastructure management. Never duplicate infrastructure. No visual traffic without underlying movement simulation: every journey has a valid origin, destination, route and travel state; every freight shipment has a traceable logistics history.

## Unified network
Road, rail, air, water, pedestrian, cycling, public transportation — each network keeps its own topology, capacity, operational state and historical records.

## Roads
Highways, expressways, urban/rural roads, intersections, bridges, tunnels, roundabouts, traffic signals, pedestrian crossings, restrictions. Graph-based routing (Session 03 graph is the base). Road closures, maintenance and capacity restrictions must affect routing.

## Vehicles
Private cars, motorcycles, buses, trucks, emergency, delivery, construction, public service vehicles. Each: ID, type, ownership, location, speed, capacity, fuel/energy level, maintenance status, operational condition. Movement follows available networks. (GDD-07/Unit P vehicle data is the foundation.)

## Driver behaviour (simplified, coherent)
Destination selection, route calculation, restriction compliance, signal response, safe movement, collision avoidance, congestion reaction, closure adaptation.

## Traffic (emergent — never random statistics)
Density, flow, road capacity, congestion, average speed, travel time, queue formation, signal timing, incidents — all emerging from actual simulated vehicle movement.

## Public transit
City + intercity buses, metro, trains, trams, ferries, shared transport. Routes, stations, stops, timetables, passenger capacity, ticket pricing, boarding/alighting, service reliability. Citizens use transit when appropriate (travel decisions weigh distance, cost, time, availability).

## Rail
Tracks, stations, schedules, passenger + freight trains, signalling, platform capacity, maintenance. Rail operations affect transportation + economic logistics.

## Aviation (abstracted)
Airports, runways, terminals, aircraft, flight schedules, passenger + cargo handling, air routes, airport capacity, aviation incidents. Intercity + international connectivity. Abstracted simulation only — never claim certified flight dynamics. (Known data gap: District 1 has no airport — handle honestly.)

## Maritime
Ports, harbours, shipping terminals, cargo + passenger vessels, water routes, port capacity, maritime logistics — connected to international trade + supply chains. (Rupsha is a river city — river transport is the natural fit.)

## Human mobility (Sessions 01/02)
Travel for employment, education, healthcare, shopping, recreation, family visits, social activities, government services. Decisions consider distance, cost, travel time, available transport.

## Freight (Session 04)
Scheduling, loading/unloading, warehouse transfers, delivery routes, distribution networks, transportation costs, delays, freight capacity. Supply chains depend on ACTUAL transportation availability (deepens Session 04's supply pool).

## Energy
Fuel stations, EV charging, energy consumption, fuel pricing, charging capacity, energy availability, fuel supply logistics. Vehicle operations consume real energy resources.

## Smart traffic
Intelligent signals, monitoring, adaptive signal timing, congestion management, route optimisation, public-transport priority, incident response, traffic information systems. Management decisions use actual traffic conditions.

## Emergency mobility
Ambulances, fire, police, disaster response; emergency routing; hospital destination selection; appropriate route priority.

## Infrastructure lifecycle
Planning → financing → construction → inspection → maintenance → repair → rehabilitation → replacement, connected to Session 03 construction + Session 05 budgets.

## Environmental measures (feeds Session 08)
Fuel consumption, vehicle emissions, noise pollution, traffic pollution, energy consumption, sustainable transport adoption.

## Transport economics (Session 04 records)
Ticket revenue, fuel expenses, freight charges, vehicle ownership costs, maintenance expenses, infrastructure spending, public transport subsidies.

## Interface
Transportation views = data layer over actual simulation data (live positions, density, conditions, routes, operations, freight, emergency, costs, performance).

## Performance
Spatial partitioning, efficient pathfinding, vehicle update scheduling, traffic aggregation, route caching, level-of-detail, background logistics, event-driven changes. Do not simulate every vehicle at maximum detail simultaneously.

## Acceptance criteria (test-verified)
1 Networks connect correctly. 2 Vehicles follow valid routes. 3 Congestion emerges from vehicle activity. 4 Public transportation operates. 5 Passenger journeys recorded. 6 Freight deliveries function. 7 Fuel/energy consumed correctly. 8 Emergency vehicles navigate. 9 Closures affect routing. 10 Transportation costs affect businesses. 11 Environmental impacts recorded. 12 Previous sessions remain functional. Plus realistic traffic + logistics load tests with reported results.

Do NOT proceed to Session 08 until Session 07 passes.
