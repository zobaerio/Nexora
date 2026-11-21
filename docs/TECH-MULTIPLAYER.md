# NEXORA — TECH: Multiplayer Architecture Design

**Unit S · Version 1.0 · 2026-11-21**
**Parent documents:** `NEXORA-MIGRATION-PLAN.md` Phase 9 (and Part C's honest limitation: UE replication is not MMO scale) · `data/schema.sql` (the authority mapping in §4 targets its tables by name) · `docs/GDD-01-LIFE-AND-DATA-MODEL.md` §8 (ledger), §9 (save mapping) · `docs/GDD-03-ECONOMY-AND-PROFESSIONS.md` §4.1 ("only the server writes ledger rows in multiplayer") · `docs/GDD-06-NPC-BEHAVIOUR.md` (crowd tiers — §3 of this doc is those tiers read as a networking budget) · `docs/GDD-07-VEHICLES-AND-TRAFFIC.md` §3/§8 (traffic tiers; the local-only Ambient decision this doc formalises) · `docs/TECH-SAVE-SYSTEM.md` (single-player save shape the server snapshot extends)
**Status:** DESIGN ONLY — Phase 9 preparation. No server build, no session code, no netcode exists yet. Nothing here claims two machines have ever connected. This document fixes the decisions Phase 9 implements against, so the single-player phases stop making choices multiplayer would have to unmake.

> **Authority law:** the server owns everything that can be *owned* — money, property, tenancy, reputation, world time. A client owns exactly two things: its input and its Ambient crowd. Any system that lets a client assert a fact about the shared world is a bug in the design, not a shortcut.

---

## 1. The Decision: Dedicated Server for the Real World, Listen Server Only for First Tests

| Option | Verdict | Why |
|---|---|---|
| **Dedicated server** (headless UE server build; owner's PC for LAN tests, a small hosted instance later) | **The Phase 9 target** | The economy's design law (GDD-03: money is conserved, server writes the ledger) needs a process no player controls. A persistent district — properties owned while you're offline, sites mid-construction, tenancies running — needs a world that exists when no player is hosting. Only a dedicated server gives both. |
| Listen server (one player's game hosts) | **First-test tool only** | Fine for the very first two-machine smoke test (does a second character appear and move?). Not acceptable beyond it: the host's machine is the authority, so the host can cheat by construction, the world dies when the host leaves, and host performance couples to their gameplay. Any result from a listen-server test is a *connectivity* result, never an *economy* result. |
| Peer-to-peer / client authority | **Rejected** | Irreconcilable with a conserved-money ledger and server-validated property. Not revisited. |

**Consequence for earlier phases:** single-player (Phases 1–8) runs the same authority split *in-process* — the game instance acts as its own server for ledger/property/world state (which is exactly how the Unit M save design already treats them: society truth vs runtime state). Phase 9 then moves that authority to a separate process instead of inventing it. If a single-player feature ever writes money or property from a purely cosmetic system, that is the bug this paragraph exists to catch early.

## 2. Session & Friend Model

- **Accounts and characters** are the schema's: one `accounts` row per player; their in-world person is a `characters` row. A player joins a session *as their character* — there is no separate "multiplayer avatar".
- **Friends** are `account_friendships` (schema: `pending / accepted / blocked`). Only `accepted` friendships can invite. Friendship is account-level (platform), distinct from in-world `relationships` between characters (GDD-01 §6) — two players can be account friends whose characters have never met, and the design keeps those facts separate.
- **Session shape (v1):** one dedicated server = one persistent District 1 world. Friends join the world their characters live in; there are no per-match lobbies, no session browser, no drop-in on strangers in v1. Invites are for *new characters joining the world*, handled at character creation, not as mid-game teleports.
- **Player count target: 8–16 concurrent players** in District 1 (see §5 for why this number and not a bigger one). The design is a co-op city of friends, not a public MMO shard.

## 3. What Replicates — and What Never Does

The crowd tiers (GDD-06 / PHASE2 sheet) are the networking budget. Read them as bandwidth classes:

| Thing | Replicates? | Owner / notes |
|---|---|---|
| Player characters | **Yes — fully** | Standard UE character replication + movement prediction; the server corrects, never trusts, position claims beyond movement rules |
| Full-tier NPCs (named, near players, interactable) | **Yes** | Server-simulated; replicate transform + state-machine state + current activity. Promotion/demotion (GDD-06) is a server decision; a Full NPC is Full for every client in relevance range |
| Scheduled-tier NPCs | **State, cheaply** | Server holds their schedule state (anchor, activity, block) as data; clients render them locally from that state. No per-frame transform replication — position is derived from the schedule + anchor graph on both sides |
| Ambient-tier crowd | **Never** | Local simulation on each client, seeded so crowds feel similar, never identical. An Ambient person has no name, no ledger, no memory — there is nothing to agree about, so nothing is sent (GDD-07 §8's traffic decision, generalised) |
| Ambient traffic | **Never** | Same rule as the crowd (GDD-07 §3 source 3) |
| Player-driven + Full-NPC vehicles | **Yes** | Server-owned physics-lite state; clients predict for smoothness |
| World clock + weather | **Yes — state, not simulation** | The server owns `UNexoraGameClock`/`WeatherManager` state (Unit E) and replicates *current state + transitions*; every client renders sky/rain locally from that state. Weather is a fact, its particles are not |
| Construction sites | **Yes — stage state** | Stage transitions are server-validated (materials consumed, inspection recorded — GDD-08 §2/§6); clients render the stage the server says exists |
| Property ownership / tenancy / prices | **Yes — as data events** | Changed only by server transactions (§4); clients receive the new fact, never propose it |
| Money / ledger | **Never as client state** | Clients *display* a cached balance (GDD-05 HUD rule); the ledger itself lives server-side (§4). A client's balance display can be stale; it cannot be authoritative |

## 4. Server Authority → `schema.sql` Mapping

The schema was drafted for this (Unit B: "designed for Phase 9 server authority"). The mapping, table by table:

| Schema table(s) | Authority rule |
|---|---|
| `economy_ledger` | **Server-only writes** (GDD-03 §4.1, verbatim). Every wage, fare, purchase, construction payment and tax row is appended by the server after validating the payer's derived balance. Clients request transactions (`request_buy`, `request_pay`); they never write rows |
| `properties`, `tenancies` | Server validates every buy/rent/end-tenancy against ownership, status and funds in one transaction. Two clients racing for the same flat: the first committed transaction wins; the second receives a refusal with the reason — this exact case is a Phase 9 test (§6) |
| `characters`, `households`, `household_members`, `relationships`, `character_memories`, `character_skills`, `character_goals` | Server-owned society state. Clients see what their character could know (GDD-05's privacy rule for NPC memories applies to players too) |
| `businesses`, `employments` | Server runs payroll/business ticks from the business ledger; a player-owned shop's books are server books |
| `inventory_items` (incl. vehicles, GDD-07 §2) | Server-validated transfers only (buy/sell/gift requests); item spawn/delete is a server act |
| `mission_progress`, `achievements` | Server validates objective completion against world state it owns (a client cannot claim a delivery the server never saw) |
| `save_slots`, `world_state` | On a dedicated server these become the **server's snapshot**: periodic + on-shutdown serialisation of society truth (the Unit M field mapping, server-side). Single-player keeps the same shape locally — one format, two homes |
| `account_friendships` | Session/invite authority (§2); the only table the platform layer (not the world sim) writes |

**Persistence:** the world persists on the server between sessions — a player's flat, job, site stage and balance are as they left them, and NPC society kept living by the server tick (GDD-01 §4) at reduced off-hours fidelity (Scheduled state advances; Ambient does not exist when nobody is looking, by definition).

## 5. Honest Scale Limits

- **UE replication is not MMO technology** (migration plan, Part C). Practical per-server populations for a simulated city with this much state are in the **tens, not thousands**. The 8–16 player target in §2 is chosen *inside* that reality with headroom for Full-tier NPC replication — it is a design commitment, not a placeholder for a bigger number.
- **One district per server in v1.** No sharding, no instancing, no cross-server travel is designed here; Districts 2+ and planets (Phase 8/10) raise travel questions this document does not answer.
- **The tick is not free.** Server-side society simulation (schedules, economy, construction) for ~hundreds of named NPCs is data work, cheap next to physics — but Full-tier *rendering-relevant* simulation is bounded by the tier caps in GDD-06, and those caps are the perf budget whether or not multiplayer ships.
- **Hosted cost is undecided on purpose.** A small dedicated instance is a real recurring cost; whether NEXORA's Phase 9 test runs on the owner's PC (LAN) or a hosted box is an owner decision with money attached — this document designs for both, recommends neither.

## 6. Test Plan (owner's PC / LAN, when Phase 9 arrives)

Ordered; each step must pass before the next means anything:

1. **Listen-server smoke test** (2 machines, LAN): second player connects, characters see and follow each other; clock/weather state matches on both. *Connectivity only — no economy conclusions allowed from this step.*
2. **Dedicated server build** runs headless on the owner's PC; two clients connect from the LAN. World clock persists across a server restart via the `world_state` snapshot.
3. **Ledger race test:** two clients attempt to buy the same `for_sale` property in the same second. Exactly one succeeds; the ledger shows exactly one purchase; the loser got a refusal, not a charge.
4. **Disconnect honesty test:** a client disconnects mid-transaction (fare payment, stage inspection). On reconnect, state is the server's — no duplicated money, no half-written stage.
5. **Tier test:** 4 clients in different zones; Full NPCs near each client behave identically for observers of the same NPC; Ambient crowds differ between clients *and nobody can tell*, which is the point.
6. **Soak:** server runs a full game week unattended; ledger balances reconcile (sum of all accounts constant except documented system flows — the GDD-03 conservation law as an automated check).

## 7. What This Document Deliberately Does Not Decide

- **No netcode.** No replication graphs, RPC lists, or bandwidth numbers are specified — those are implementation choices for Phase 9 against this authority map, and inventing them now would be fiction.
- **No anti-cheat product or policy.** The authority split *is* the anti-cheat foundation (clients can't assert facts); cheat *detection*, moderation and bans are un-designed and un-claimed.
- **No hosting provider, region or budget.** See §5 — an owner money decision, deferred honestly.
- **No voice/text chat design.** Friends playing together will want it; it is a real system with real moderation weight, and it gets its own unit or none — it is not smuggled in here.
- **No public servers / matchmaking.** V1 multiplayer is a friends' persistent district (§2). Public play is a different product decision, not a scale-up of this one.
