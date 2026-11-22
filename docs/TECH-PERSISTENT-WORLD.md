# NEXORA — Tech Note: Persistent World → UE Server Mapping

**Unit AM · Queue 7 · Version 1.0 · 2026-11-22**
**Code:** none — design only. No server build, no netcode, no snapshot code exists yet; nothing here claims two machines have ever connected or a world has ever persisted on a server.
**Parent documents:** `docs/SESSION-10-REPORT.md` §2.2–2.4, §5–§6 (the proven headless persistence this maps) · `docs/FINAL-ARCHITECTURE.md` layers 1, 12, 13 (world, event & time, persistence) · `docs/TECH-MULTIPLAYER.md` (Phase 9 dedicated-server design) · `data/schema.sql` (`save_slots`, `world_state`, `economy_ledger`) · `docs/TECH-SAVE-SYSTEM.md` (single-player save shape the server snapshot extends) · `docs/GDD-01-LIFE-AND-DATA-MODEL.md` §8 (ledger), §9 (save mapping) · `docs/TECH-CLOCK-WEATHER.md` §1 (clock), §5 (panel data interface)
**Status:** DESIGN ONLY — a mapping from a *proven* headless system onto a *designed* server. The left-hand side of every table below is measured (Session 10); the right-hand side is the Phase 9 build instruction. First server test happens on the owner's PC/LAN (TECH-MULTIPLAYER §6).

> **Design law:** the server persists the *same* society the headless sim already persists — one data model, two homes (GDD-01 §9, TECH-SAVE-SYSTEM). The sim's SQLite world file and the server's PostgreSQL database are two stores for the same tables, the same clock, and the same ledger. No phase may invent a second persistence model "for multiplayer" — the mapping below is the whole of it, and anything it cannot map is listed in §9 as unbuilt, not papered over.

---

## 1. The Two Sides Being Mapped

| | Headless sim (proven, Session 10) | Phase 9 dedicated server (designed, TECH-MULTIPLAYER) |
|---|---|---|
| Store | One SQLite file per world (WAL mode); the file **is** the save | PostgreSQL on the server (`data/schema.sql`); the client keeps only a read cache |
| Clock | Single `world_state` row (`day_index`, `game_minutes`), written once per day by `Store.set_world` | `schema.sql` `world_state` (single row, `id = 1`): `game_minutes` (starts 480 = Day 1, 08:00), `time_scale`, `weather_preset`, `schema_version` |
| Money | Append-only double-entry `economy_ledger` in the same SQLite file; `transfer_key` idempotency + append-only triggers | `schema.sql` `economy_ledger`; server-only writes (TECH-MULTIPLAYER §4), clients request, server validates and commits |
| History | 149 tables; every subsystem's history is write-once in practice | The same tables, by name, in PostgreSQL (`TablePayloads` map in TECH-SAVE-SYSTEM §2) |
| Registry | Unified event registry (`world_events` + `event_sync_state`), an append-only index over the history tables — never a source of truth | The server's audit/event index: same role, same rule (index, never source) |
| Worlds | World registry JSON beside the world files (world id `WORLD-0001…`, name, path, seed, config/code version, registered time) | The server's world list: one dedicated server = one persistent District 1 world in v1 (TECH-MULTIPLAYER §2); the registry shape is the multi-world list for later phases |

**Naming correction carried forward (Session 10 §1.2):** there is no `game_clock` table and never was. The clock is the `world_state` row. The sim's SQLite `world_state` carries both `day_index` and `game_minutes`; the PostgreSQL `world_state` in `schema.sql` carries `game_minutes` only — the server derives the day as `game_minutes / 1440 + 1` (TECH-SAVE-SYSTEM §2: `GameMinutes = (DayNumber − 1) × 1440 + MinutesSinceMidnight`). The mapping must never invent a `day_index` column in PostgreSQL; the day is a read-time derivation on the server, exactly as it is in the sim's `store.world()` reads.

## 2. What the Server Persists Per Tick vs Per Checkpoint

The sim's cadence (FINAL-ARCHITECTURE: engine owns the cadence) maps onto the server tick like this. "Per tick" means written as the tick runs; "per checkpoint" means written only when a named snapshot is taken.

| Cadence | Headless sim (proven) | Server mapping |
|---|---|---|
| **Every transfer** | `Store.transfer` appends a ledger row (reason code, optional `event_ref`, idempotency `transfer_key`) in the same transaction as the balance-cache update | Every server-validated transaction appends to `economy_ledger` in one PostgreSQL transaction. Same fields, same rule: a transfer without a ledger row does not exist. Clients never write rows (TECH-MULTIPLAYER §4). |
| **Once per day** | Clock write: `Store.set_world` writes `day_index` + `game_minutes` once, at the end of `run_day`, after every daily, festival and monthly pass | The server writes `world_state.game_minutes` once per in-game day, at the same point in its tick — after the settlement chain (FINAL-ARCHITECTURE: social → economy → city → economy close → government → humandev → transport → environment → agents → integration). A day is never half-written: the clock write *is* the commit marker for the day. |
| **End of day** | Registry sync runs last in `run_day` (Session 10 defect #1: it was placed too early and indexed a day late; fixed by moving it to the very end) | The server's event-index sync runs last in the server tick, for the same reason. The registry indexes history tables; it never feeds a simulation decision (FINAL-ARCHITECTURE layer 12). |
| **Monthly** | Monthly settlement chain + snapshots (`economic_indicators`, `city_statistics`, `human_development_indicators`, `transport_statistics`, `env_snapshots`, `opinion_snapshots`) | Same monthly passes, same tables, on the server. Snapshots are *derived rows*, recomputable from history — the server may rebuild them from the ledger/history rather than trusting a stored copy. |
| **Per checkpoint (named)** | Named snapshot via the SQLite backup API + JSON manifest: sim day, population, ledger rows, **ledger reconciled** (verified on the copy), content digest, code version | The server's snapshot: see §3. Taken periodically (design decision for Phase 9: every in-game week + on clean shutdown) and on demand. Never taken mid-day — a checkpoint is always a day-boundary state, because the clock write is the day's commit marker. |
| **Never persisted** | Ambient crowd state, derived NPC positions, client-side caches, the observatory's read models | Same on the server: Ambient crowds are local per client and never sent (TECH-MULTIPLAYER §3); a Scheduled NPC's position is derived from schedule + anchor graph on both sides; the server persists *state*, clients render it. Persisting a derived position would be storing a fact twice and letting the copies disagree. |

## 3. Checkpoint Manifest → `save_slots` / `world_state`

The sim's checkpoint manifest maps onto the schema's save tables field by field. This is the same mapping TECH-SAVE-SYSTEM §2 already fixes for single-player — the server reuses it, server-side (TECH-MULTIPLAYER §4: "on a dedicated server these become the server's snapshot").

| Sim checkpoint manifest field | Server field | Rule |
|---|---|---|
| `checkpoint_db` (the copied world file) | `save_slots.payload_ref` | Where the serialised world lives (file path / blob key). The payload is the society: every schema table by name, as JSON rows (`TablePayloads` in TECH-SAVE-SYSTEM §2). |
| Sim day (`day_index`) | `save_slots.game_minutes` = `world_state.game_minutes` | Total in-game minutes since Day 1 00:00. The day is derived from it (§1); the manifest's human-readable day is a label, never a second clock. |
| Population (alive count) | — (derived) | Not stored as a field. The server counts `characters` rows on load and compares with the manifest's count as a sanity check — a mismatch is a corrupt snapshot, not a rounding difference. |
| Ledger rows (count) | — (derived) | Same: counted from `economy_ledger` on load, compared with the manifest. |
| `ledger_reconciled` (verified on the copy, true) | The load gate | The server loads a snapshot only if its ledger reconciles (`ledger_sum_check` clean, conservation clean — the Session 10 acceptance battery). A snapshot whose ledger does not reconcile is refused, never repaired in place. |
| Content digest | Stored beside the slot (manifest file / snapshot metadata row) | See §4. The digest is the integrity check; it is not a schema column today — Phase 9 adds it as snapshot metadata, not as a new table, and never as a column on `world_state` (the clock row stays minimal). |
| Code version (`s10.1` in the sim) | `save_slots.schema_version` = `world_state.schema_version` | The three must agree (TECH-SAVE-SYSTEM §2). Migrations are forward-only (GDD-01 §9): a snapshot from an older version migrates on load; a snapshot from a *newer* version is shown but refused, in words (GDD-05 §7 save/load rule). |

**Single-player keeps the same shape locally** (TECH-SAVE-SYSTEM): one format, two homes. A single-player save slot and a server snapshot are the same object with different owners — which is why the migration rule, the ledger gate, and the digest check are written once here and apply to both.

## 4. Digest Verification as the Server's Integrity Check

Session 10 proves the digest, not just defines it. The content digest covers **every character's id/balance/death + ledger count/sum + clock** — the parts of a world that must survive a save, a restore, a duplication, and a kill:

| Proven fact (Session 10 §6) | Server rule |
|---|---|
| Restore reproduces the checkpointed digest exactly (checkpoint save 2.90 s, restore 0.79 s on the endurance world) | On every server start, the server recomputes the digest of the loaded snapshot and compares it with the stored manifest digest. Match = start. Mismatch = refuse to start on that snapshot; fall back to the previous named checkpoint and write an audit row. Never start on a world whose digest does not match — a silently wrong world is worse than a down server. |
| Crash recovery: a run SIGKILLed mid-run reopens with a clean ledger, the clock at the last committed day (never a partial day), and continuing reproduces the uninterrupted twin's digest exactly | The server's crash story is the same, with the database doing the work the file did: PostgreSQL WAL + the once-per-day clock write as the commit marker. On restart the server rolls forward to the last committed day and discards any partial day — there is no such thing as a half-written day in either store. |
| Multi-world isolation: advancing world A 30 days leaves world B's digest byte-identical | One server = one world in v1, so isolation is trivially satisfied. When a second world exists (later phases), the same digest test is the acceptance check: advancing one world must leave the other's digest byte-identical. The registry's per-world entries (name, seed, code version) are what make the test addressable. |
| Duplication creates an independent world and refuses to overwrite | The server's test-world flow: duplicate a snapshot to a new world id, never into the live world's slot. A duplicated world gets a fresh registry entry and its own digest baseline; the two worlds then diverge honestly. |
| Registry completeness: registry counts for the total-mapping append sources equal their source-table counts exactly | The server's event index is verified the same way, periodically (not per tick): index counts vs source-table counts. A gap is an audit finding, and the index is rebuilt from the sources — the sources are never rewritten to match the index. |

**What the digest does not cover (honest boundary):** it covers characters, ledger, and clock — not Ambient crowd state (never persisted, §2), not derived positions, not client caches. A digest match proves the *society* survived; it says nothing about what any client rendered. That is the correct scope: the digest guards the truth, not the picture.

## 5. Time Modes → Server Tick

Session 10 §2.4 documents the runner's time modes honestly as batch/step/paused/playback over persisted state — **no real-time server exists and none is claimed**. The mapping preserves that honesty:

| Sim time mode | Server equivalent |
|---|---|
| *Accelerated* (the batch run itself) | The server's normal tick at its configured time scale (`world_state.time_scale`, default 60 game-min per real-min — TECH-CLOCK-WEATHER §1). "Accelerated" on a server is just the time scale, not a different mode. |
| *Step* (advance exactly N days; +1 day = +1 `day_index`, +1440 game-minutes) | The server's admin step command (Phase 9 tooling): advance exactly N in-game days, then stop at a day boundary with the clock write committed. Used for testing and for catching up an offline world, never for live play. |
| *Paused* (open + close changes nothing — digest-tested) | Single-player pause (`SetPaused`, GDD-05 §7). **Multiplayer has no pause** (GDD-05 §1 rule 3): the server never stops for one player. A "paused server" is a stopped server — the state at rest, digest-stable, resumable. |
| *Playback* (read-only history queries; tested to mutate nothing) | The observatory views (`--events/--technology/--resources` in the sim; the server's read API in Phase 9). Playback reads history tables and the event index; it writes nothing, and the server must prove that with the same digest-before/after test the sim uses. |

**Off-hours fidelity (TECH-MULTIPLAYER §4):** when no player is connected, the server tick continues at reduced fidelity — Scheduled state advances (the GDD-01 §4 tick), Ambient does not exist when nobody is looking, by definition. The sim already models this boundary: Ambient-tier NPCs have no tick at all (GDD-01 §4), so there is nothing to "pause" for them.

## 6. What Changes When the World Goes Multiplayer

The mapping is deliberately boring — most rows do not change at all. The changes are exactly the authority changes TECH-MULTIPLAYER §4 already fixes:

| Concern | Single-player (now) | Server (Phase 9) |
|---|---|---|
| Ledger writes | The local game is trusted (GDD-01 §9) | Only the server writes; clients send `request_buy`/`request_pay` and receive commit or refusal. The idempotency key (`transfer_key`) is what makes a retried request safe — the same key, the same row, never a duplicate charge (TECH-MULTIPLAYER §6 test 3/4). |
| Property/tenancy | Local transaction | Server validates ownership, status and funds in one transaction; two clients racing for the same flat: first committed transaction wins, second gets a refusal with the reason. |
| Mission completion | Verified against local world state | Server validates objective completion against world state it owns; a client cannot claim a delivery the server never saw. |
| Clock/weather/season | Local `UNexoraGameClock`/`WeatherManager` | Server owns the state, replicates current state + transitions; clients render sky/rain locally (TECH-MULTIPLAYER §3; TECH-SEASONS §9 for seasons). |
| Character select | `save_slots` rows per local profile | Characters live server-side; "slots" become the character-select list (GDD-01 §9). |
| Friends/invites | — | `account_friendships` — the only table the platform layer (not the world sim) writes (TECH-MULTIPLAYER §4). |

## 7. The Persistence Contract, Restated for the Server

1. **One clock.** `world_state` (one row) is the only clock. Every subsystem reads it; nothing keeps a private time. A subsystem that caches the day is a bug.
2. **One ledger.** Every movement of money is an append-only `economy_ledger` row with a reason code, an optional `event_ref`, and an idempotency `transfer_key`. Balances are caches; the ledger is the truth (GDD-01 §8). If cache and ledger disagree, the ledger wins and the cache is rebuilt.
3. **History is write-once.** The event registry indexes history; it never rewrites it (Session 10 content-digest test). A "correction" to history is a new row that references the old one, never an edit.
4. **Checkpoints are day-boundary states.** A checkpoint taken mid-day is not a checkpoint — it is a partial day, and the recovery rule (§4) discards partial days. The server takes snapshots only at day boundaries (every in-game week + on clean shutdown, §2).
5. **Migrations are forward-only.** Every save/snapshot carries `schema_version`; migrations are forward-only transforms shipped with the game/server (GDD-01 §9, TECH-SAVE-SYSTEM §2). The sim's additive-migration mechanism (Session 10: three additive tables, 146 → 149, no column changed, no table dropped) is the model: the server's migrations are additive too, and a migration that drops a table needs an owner decision, not a quiet PR.
6. **The registry is a read model.** `world_events` (sim) / the server's event index is never a source of truth and never feeds a simulation decision (FINAL-ARCHITECTURE layer 12).

## 8. Test Plan (owner's PC / LAN, when Phase 9 arrives)

Extends TECH-MULTIPLAYER §6; each step must pass before the next means anything. The Session 10 proofs are the *expected results*, not the aspirations:

1. **Digest round-trip:** take a server snapshot, restore it on a second machine, recompute the digest — identical to the live world's digest. (Sim proof: Session 10 §6, restore 0.79 s, digest == pre-restore digest.)
2. **Kill recovery:** SIGKILL the server mid-day; on restart the ledger reconciles, the clock stands at the last committed day, and continuing reproduces the uninterrupted twin's digest. (Sim proof: Session 10 §6 recovery run, 7.9 s total.)
3. **Isolation:** two worlds on one server host; advance world A 30 days; world B's digest byte-identical. (Sim proof: `test_integration_worlds`.)
4. **Ledger race (TECH-MULTIPLAYER §6 test 3):** two clients buy the same `for_sale` property in the same second. Exactly one succeeds; the ledger shows exactly one purchase; the loser got a refusal, not a charge. The idempotency key is what makes the retry safe.
5. **Disconnect honesty (TECH-MULTIPLAYER §6 test 4):** a client disconnects mid-transaction; on reconnect, state is the server's — no duplicated money, no half-written stage.
6. **Soak (TECH-MULTIPLAYER §6 test 6):** server runs a full game week unattended; ledger balances reconcile (sum of all accounts constant except documented system flows). History growth is watched against the sim's measured ~0.58 MB/day at 242 residents — the known pressure, not a surprise.
7. **Playback purity:** run the observatory views against the live server; digest before == digest after (the sim's playback test, applied to the server).

## 9. Honest Boundaries — What This Mapping Does Not Build

- **No real-time server exists in this VM.** Time modes are the batch runner's honest capabilities (Session 10 §2.4). This document maps them onto a server design; it does not conjure a server.
- **No network API.** The sim's CLI surface (`--worlds`, `--checkpoint`, `--restore-checkpoint`, `--duplicate-to`, `--events`, `--db-inspect` — FINAL-ARCHITECTURE) is a *local* API. The server's network API is Phase 9 implementation work; no replication graphs, RPC lists, or bandwidth numbers are specified here (TECH-MULTIPLAYER §7).
- **No distributed processing, region aggregation, or DB partitioning.** Session 10 §6 measures the scale honestly (365 days × 242 residents; 342-resident genesis cap from the ~140-unit housing stock). The spec's scale architecture for those is future work, not built, and this mapping does not pretend the server magically has it.
- **No user accounts, no network security surface.** Session 10 checklist item 19 is PARTIALLY PROVEN for exactly this reason: what exists locally (append-only money, audits, world isolation, platform-vs-government separation) is proven; what does not exist (accounts, network APIs, rate limiting) is not claimed. The server's account/security design is Phase 9 work.
- **The PostgreSQL `world_state` has no `day_index`.** The sim's SQLite one does. The day is derived from `game_minutes` on the server (§1) — a mapping detail, not a gap, but it must be implemented that way and not by adding a column nobody agreed to.
- **Digest metadata is not in `schema.sql` yet.** §3 stores it beside the slot as snapshot metadata. Adding it as a column or a table is a Phase 9 schema change with a migration note — not smuggled in here.

*End of TECH-PERSISTENT-WORLD v1.0 — Unit AM, Queue 7.*
