"""NEXORA — Session 01: Autonomous Human Intelligence & Life Simulation.

A real, runnable, deterministic Python simulation core (stdlib only).
This is the headless engine the UE presentation layer and the Phase 9
server design map onto; it is NOT a UE system and claims nothing about
the owner's PC build. All population data is simulated by construction
and labelled as such.

Canonical data sources (audit §4.2/§4.3 — one source per fact):
- Wages: data/prices.json `wages_monthly` (the same source the economy
  simulator reads, so the two engines reconcile).
- Profession metadata (starting balances, progression, skills,
  workplace zones): data/professions.json.
- Cab rental: data/prices.json `taxi_fares.cab_rental_ncr_per_day`.
- Schedules: data/npc-schedules.json. Housing: data/buildings-district1.json.
- Living costs / tax / business P&L: data/prices.json (the P&L and tax
  functions are imported from tools/economy_sim.py, never re-derived).
"""
