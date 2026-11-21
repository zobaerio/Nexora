# SESSION 10 — Global Virtual Universe Integration & Persistent Living Civilization (owner spec, received 2026-11-21)

Gate rule: starts only after Session 09 passes. This is NOT permission to rewrite the project. Scalability is a goal; NEVER claim a specific population capacity without reproducible load testing. Do not claim NEXORA fully complete if any acceptance criterion remains unverified.

## Comprehensive audit first
All nine previous sessions: completed systems, incomplete systems, duplicate services, broken integrations, data inconsistencies, performance bottlenecks, security weaknesses, unverified simulation claims. Preserve working functionality; never hide unfinished features behind decorative interfaces.

## Unified global world model
Continents, countries, regions, states/provinces, districts, cities, towns, villages, rural areas, oceans, seas, rivers, mountains, forests, islands — each with unique identity + hierarchical relationship. Support multiple independent civilizations. (Current reality: one country, two cities — the hierarchy must honestly reflect what exists and extend structurally.)

## World-state persistence
Population, identities, relationships, families, households, businesses, financial transactions, government institutions, educational + healthcare records, buildings, infrastructure, transportation, weather history, environmental conditions, agent memories, historical events. Must survive application restarts, worker restarts, server failures, scheduled maintenance, simulation pauses. Consistent checkpointing + recovery. (SQLite persistence + restart-identity proofs are the base.)

## Unified simulation time
Real-time, accelerated, slow, paused, step-by-step, historical playback modes; configurable rates (e.g. 1 real second = 1 sim second/minute/hour/day). ALL systems use the same simulation clock — no inconsistent independent clocks.

## Central event architecture
Events: birth, marriage, death, graduation, employment, business formation/failure, construction, economic change, elections, government decisions, disasters, transport incidents, scientific discoveries, international agreements. Each event: unique ID, type, timestamp, location, related entities, event data, source subsystem, processing status. Support dependencies, retries, idempotency. (Life events + ledger event_ref + decision_log are the seeds — unify, don't duplicate.)

## Verify subsystem connections (each must produce actual data changes)
Human → Education → Employment → Income → Household Economy. Business → Production → Logistics → Transportation → Market. Government → Budget → Infrastructure → City Development. Weather → Agriculture → Food Supply → Market Prices. Disaster → Emergency Response → Healthcare → Recovery. Education → Skills → Employment → Economic Growth. Environmental Policy → Industrial Activity → Pollution.

## Unified population model
Births, deaths, migration, distribution, age structures, household formation, urbanisation, density, regional demographic change. Hierarchical aggregation. Never duplicate individuals when moving between locations.

## Multi-city / regional connection
Regional trade, transportation links, migration, resource exchange, shared infrastructure, economic cooperation, environmental dependencies, regional development — cities influence each other through real mechanisms.

## Persistent historical records
Individual life histories, family histories, city development, government terms, elections, economic cycles, wars/conflicts as CONFIGURABLE historical scenarios, natural disasters, scientific achievements, cultural developments, international events. Explorable timelines. NEVER rewrite past records when current state changes.

## Long-term evolution (emergent)
Population change, technological advancement, urban expansion, economic development, institutional evolution, cultural change, environmental change, infrastructure modernisation, social transformation — from interconnected conditions, not scripts.

## Technology progression
Research institutions, scientific discoveries, engineering innovation, industrial/agricultural/medical/energy/communication/transportation technology, automation. Progression requires research capacity + resources + education + investment (Session 06 research is the base). Technology influences civilization capabilities measurably.

## Culture
Languages, traditions, cultural exchange, regional identities, artistic development, cultural events, knowledge preservation, cultural adaptation — emerging from population interactions + historical events (extends Session 02 culture data).

## Resource networks
Food, water, energy, raw materials, minerals, construction materials, agricultural + industrial resources. Each: production, consumption, storage, transportation, market value, regional availability, sustainability indicators. Shortages influence connected systems.

## Global scenarios (configurable, measurable, with propagation + recovery)
Global recession, international supply disruption, pandemic, climate emergency, major disasters, energy shortage, food insecurity, international conflicts, infrastructure failures.

## World exploration interface
Global map → countries → regions → cities → buildings → human activity → transportation → businesses → economy → weather → environment → history, with level-of-detail. (In this environment: the data/export layer; 3D rendering remains the owner's PC/UE layer.)

## Civilization analytics
Global population + growth, global + regional economic output, employment, education, healthcare, infrastructure, transportation, environmental quality, technological progress, social development, government performance, resource sustainability. Every metric has a documented calculation method.

## Saves & scenarios
Manual save, automatic checkpoints, restore previous checkpoints, historical state inspection, event replay, scenario branching, simulation duplication, recovery after interruption. Reproducible via saved seeds + versioned simulation rules. Replay NEVER modifies original historical data.

## Multiple worlds
Each world: ID, configuration, seed, starting conditions, settings, population configuration, geography, climate settings, economic parameters, governance configuration, timeline. Worlds are ISOLATED — changes in one never affect another (test-verified). Controlled comparison between worlds.

## Scale architecture
Distributed task processing where justified, region-based simulation, hierarchical agent updates, event-driven architecture, DB partitioning where necessary, spatial indexing, background workers, efficient caching, aggregated simulation, resource monitoring, graceful degradation. Detail levels: detailed (nearby) / aggregate statistical (distant) / scheduled + aggregated (inactive regions), with consistency maintained when switching levels.

## Security & administration
World ownership, user access control, world-level permissions, simulation isolation, data validation, audit logging, secure APIs, background task authorisation, backup procedures, disaster recovery, rate limiting. REAL platform administration stays separate from simulated government authority (owner's hard rule from Session 05).

## Integration testing
Complete test of: human lifecycle, family development, social relationships, city growth, economic activity, business operations, government administration, elections, education, healthcare, transportation, environmental simulation, autonomous agent decisions, historical persistence, global event propagation, save + restore, multi-world isolation. Long-duration scenarios. Restart + worker-failure tests. Benchmarks measured: simulation throughput, DB performance, memory, CPU, event latency, recovery time (rendering performance is PC-side).

## Architecture organisation (15 layers)
World, Geography, Human, Social, City, Economic, Government, Education & Healthcare, Transportation, Environmental, Intelligence, Event & Time, Persistence, Visualization, Security & Administration. Clear service ownership + API contracts; avoid unnecessary complexity.

## Database inspection + report
Duplicates, missing foreign keys, invalid relationships, unused tables, missing indexes, inconsistent timestamps, unprotected records, inefficient queries, data integrity issues. NO data deletion or destructive migrations without explicit safeguards. Deliver a complete database architecture report.

## Final demonstration checklist (all 20 must be evidenced)
1 Persistent human populations. 2 Autonomous individual behaviour. 3 Functional families + communities. 4 Dynamic cities. 5 Operating businesses. 6 Functioning economy. 7 Autonomous government simulation. 8 Education + healthcare. 9 Connected transportation. 10 Dynamic environmental systems. 11 Autonomous AI agents. 12 Persistent historical records. 13 Cross-system event propagation. 14 Multi-city interactions. 15 Multi-world isolation. 16 Save + restore. 17 Stable long-duration execution. 18 Verified performance benchmarks. 19 Secure data access. 20 Consistent world-state management.

Final deliverables: architecture overview, completed + incomplete units, modified files, DB migration summary, API architecture, engine details, AI capabilities, benchmarks, security audit results, automated + integration test results, known limitations, future scalability requirements.
