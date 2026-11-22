# NEXORA — Tech Note: Persistent World → UE Server Mapping

**Unit AM · Queue 7 · Version 1.0 · 2026-11-22**
**Code:** none — design only. No server build, no netcode, no snapshot code exists yet; nothing here claims two machines have ever connected or a world has ever persisted on a server.
**Parent documents:** `docs/SESSION-10-REPORT.md` §2.2–2.4, §5–§6 (the proven headless persistence this maps) · `docs/FINAL-ARCHITECTURE.md` layers 1, 12, 13 (world, event & time, persistence) · `docs/TECH-MULTIPLAYER.md` (Phase 9 dedicated-server design) · `data/schema.sql` (`save_slots`, `world_state`, `economy_ledger`) · `docs/TECH-SAVE-SYSTEM.md` (single-player save shape the server snapshot extends) · `docs/GDD-01-LIFE-AND-DATA-MODEL.md` §8 (ledger), §9 (save mapping) · `docs/TECH-CLOCK-WEATHER.md` §1 (clock), §5 (panel data interface)
**Status:** DESIGN ONLY — a mapping from a *proven* headless system onto a *designed* server. The left-hand side of every table below is measured (Session 10); the right-hand side is the Phase 9 build instruction. First server test happens on the owner's PC/LAN (TECH-MULTIPLAYER §6).
**Appendix A (Unit AP, 2026-11-22):** snapshot digest metadata design — the §3/§9 follow-up. Design only; the `snapshot_metadata` table and its migration are Phase 9 work, and `data/schema.sql` is untouched by this unit.

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
| Content digest | Stored beside the slot (manifest file / snapshot metadata row) | See §4 and Appendix A. The digest is the integrity check; it is not a schema column today — Appendix A (Unit AP) decides its home: a manifest file **plus** a `snapshot_metadata` row, never a column on `world_state` (the clock row stays minimal). |
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
- **Digest metadata is not in `schema.sql` yet.** §3 stores it beside the slot as snapshot metadata. Appendix A (Unit AP) now decides the form — a manifest file plus a `snapshot_metadata` row — and carries the Phase 9 forward-only migration note. The schema change itself is still Phase 9 work; this document ships no schema change.

---

## 10. Ledger Idempotency Key Home (AW open decision OD-8 — decided)

**Unit BD · Queue 10 · Version 1.0 · 2026-11-22**
**Status:** DESIGN ONLY. This section decides open decision OD-8 from `docs/TECH-CHECKPOINT-RUNBOOK.md` §7: `data/schema.sql`'s `economy_ledger` has no `transfer_key` or `event_ref` column although the sim's rows carry both and §2 of this document says the server appends with "same fields, same rule". It adds no column to `schema.sql` — the decision and the migration note are the deliverable, and the migration itself is Phase 9 work.

### 10.1 The decision: add the columns, by forward-only migration

**The server-side home for `transfer_key` and `event_ref` is two columns on `economy_ledger` itself, added by the Phase 9 forward-only migration in §10.3 / Appendix B.** The key lives on the row it identifies — the same home the sim already uses (`tools/sim/persistence.py`: the sim's `economy_ledger` carries `transfer_key TEXT` and `event_ref TEXT`, added by its additive migration, with a `UNIQUE` index on `transfer_key`). The server migration brings PostgreSQL to parity with the proven sim store; it invents no new shape.

The exact DDL the migration carries (Appendix B §B.1 repeats it as the migration record):

```sql
ALTER TABLE economy_ledger ADD COLUMN transfer_key TEXT;
ALTER TABLE economy_ledger ADD COLUMN event_ref TEXT;
CREATE UNIQUE INDEX idx_ledger_transfer_key ON economy_ledger (transfer_key);
```

Notes on the DDL: the index name is the sim's index name (`idx_ledger_transfer_key`, `tools/sim/persistence.py` `_migrate`), deliberately, so the two stores name the same constraint the same way. The index is a plain `UNIQUE` index, not a partial one: PostgreSQL treats `NULL` values as distinct in a unique index, so rows written before the migration (both columns `NULL`) coexist with keyed rows without any special case. `transfer_key` is nullable because a key is supplied per transfer where one exists (§10.2), and `event_ref` is nullable because §2 already calls it optional ("an optional `event_ref`"). Neither column has a default: a row written without a key stores `NULL`, never an invented key.

### 10.2 The server rule (mirroring the proven sim rule)

The server implements the same rule `Store.transfer` already proves (`tools/sim/persistence.py:2069-2099`):

1. **Same key, same row, never a duplicate charge.** A transfer request carries a `transfer_key` supplied by the client for that request. If a row with that key already exists, the server returns the original `ledger_id` and moves nothing twice. The key and the row commit in **one transaction**: the key is written with the row, never after it, so a retry can always find the committed row by key.
2. **Keys are globally unique by construction.** Callers build keys from the transfer they identify, in the sim's shapes — `loan:{loan_id}`, `repay:{loan_id}:{month_index}`, `bwage:{employment_id}:{month_index}`, `month:{month_index}`, `decision:…`, `economy_setup` — and the unique index is the backstop, not the plan: a key collision is a caller bug, and the index turns it into a loud refusal instead of a silent duplicate.
3. **`event_ref` is the causing event, not the identity.** It names the simulation event that caused the transfer (a decision id, a month settlement tag, a loan id — the sim's `event_ref` values are the model). It is never used for deduplication, never unique, and never required: a row without one is a complete row.
4. **Balances stay caches.** Nothing about the key changes §7 rule 2: the ledger is the truth, balances are caches, and if cache and ledger disagree the ledger wins.

### 10.3 What the migration does not do

- **No change to `reason_code`.** The sim/server reason-code drift found by Unit BB (GDD-15 §14.4 — the sim writes `loan_disbursement` / `loan_repayment` where the schema allows `loan_disburse` / `loan_repay`, among ~39 strings the schema `CHECK` would reject) is a separate Phase 9 data-alignment item. It is not smuggled into this migration: the migration adds two columns and one index, nothing else.
- **No change to the append-only triggers.** The `economy_ledger` no-UPDATE / no-DELETE triggers keep working unchanged — adding columns does not touch them, and no history row is rewritten.
- **No backfill.** Rows written before the migration keep `NULL` for both columns. No key is invented for them: a backfilled key would be a fabrication, and a pre-migration row without a key is still a valid ledger row. The idempotency guarantee covers rows written with a key; it does not retroactively cover rows written before keys existed.
- **No down-migration.** Forward-only (GDD-01 §9; Appendix A §A.5 pattern). If the change must be undone, the rollback is forward: a later migration that stops the server using the columns — never a `DROP COLUMN` smuggled in as a rollback step, and never a delete of keyed rows.

### 10.4 Alternatives considered and rejected

| Alternative | Why it is rejected |
|---|---|
| **A separate idempotency table** (`ledger_keys`, one row per key, joined to the ledger) | It splits §7 rule 2 — "every unit of money carries its idempotency key" — across two tables. Every audit query then joins; a key row without its ledger row (or vice versa) is a new failure mode the single-table form cannot have; and the digest (characters + ledger count/sum + clock, §4) would not cover the second table. |
| **Encode the key in `note` TEXT** | Unstructured, unqueryable, collides with human notes, and no uniqueness can be enforced on a substring of a free-text field. The key would exist as a convention, not a constraint. |
| **Keep idempotency in the client/request layer only** | A retried request after a disconnect (TECH-MULTIPLAYER §6 test 4) needs the *server* to recognise the key: a client-side-only key cannot deduplicate a request the server already committed. The server must hold the key to answer "did this already land?" |
| **A key column on another table** (e.g. on `world_state`, or on the requesting entity) | The key belongs to the transfer it identifies. Appendix A §A.1's reasoning for the digest applies by analogy: a statement about a ledger row lives on the ledger row, not on a row it would have to be joined back to — and a single-row table cannot hold one key per transfer at all. |

### 10.5 What TECH-MULTIPLAYER §6 tests 3/4 need from it

- **Test 3 — ledger race** (two clients buy the same `for_sale` property in the same second): the unique index plus the §10.2 rule. Exactly one purchase commits (the property transaction: first committed transaction wins, second gets a refusal — TECH-MULTIPLAYER §4); a retried request carrying the *same* key returns the original `ledger_id` and creates no second row, so the ledger shows exactly one purchase and the loser got a refusal, not a charge. Without the index, the retry path has no server-side fact to consult and the test cannot distinguish "retried" from "bought twice".
- **Test 4 — disconnect honesty** (a client disconnects mid-transaction; on reconnect, state is the server's): the key written in the same transaction as the row (§10.2 rule 1). On reconnect the client re-sends its request with the same key; the server finds the committed row by key and returns its outcome instead of executing the transfer again — no duplicated money, no half-written stage. A key written in a separate transaction (or not at all) would leave a window where the retry cannot tell "committed" from "never arrived".
- **Test 6 — soak** needs nothing new from this change: the columns are inert for reconciliation. The Session 10 digest hashes ledger `COUNT(*)` + `SUM(amount)` only (§4 / Appendix A §A.2), so adding two columns changes no digest and no conservation check.

**Open decision OD-8 is decided by this section** — the home is the two columns, added by the Phase 9 forward-only migration (Appendix B) — with the implementation still Phase 9 work: no column exists in `schema.sql` today, no migration file exists, and no server has ever written a keyed row. The runbook's §7 OD-8 entry now reads as decided-here, not undecided.

*End of TECH-PERSISTENT-WORLD §10 — Unit BD, Queue 10.*

---

# Appendix A — Snapshot Digest Metadata (Unit AP · Queue 8 · §3/§9 follow-up)

**Version:** appendix added 2026-11-22 · **Code:** none — design only. No server build, no netcode, no snapshot code exists yet; nothing here claims two machines have ever connected or a world has ever persisted on a server.
**Parent documents:** `docs/SESSION-10-REPORT.md` §2.2 item 3, §6 (checkpoint manifest + digest proof) · `tools/sim/worlds.py` `world_digest()` + `create_checkpoint()` (the proven digest and manifest this extends) · `data/schema.sql` (`save_slots`, `world_state`, `characters`, `economy_ledger`) · GDD-01 §9 (forward-only migrations) · `docs/TECH-SAVE-SYSTEM.md` §2 (single-player save mapping).
**What this appendix does:** it closes the §9 open item *"Digest metadata is not in `schema.sql` yet"* **as a design decision** — the digest's home is now decided — while leaving the schema change itself as Phase 9 work. It supersedes the §3 placeholder wording ("not as a new table"): Unit AP's decision is that the digest lives in a manifest file **plus** a dedicated snapshot-metadata row, for the reasons in §A.1.

## A.1 The two homes: manifest file + snapshot metadata row

A checkpoint digest is stored in **two places that must agree**, and in neither of the two places it must never go:

| Home | What it holds | Why it exists |
|---|---|---|
| **Manifest file** (`<name>.manifest.json`, beside the snapshot payload — the sim's shape, `worlds.py` `create_checkpoint()`) | The human- and tool-readable checkpoint record: name, payload reference, clock, counts, `ledger_reconciled`, `digest`, `digest_algorithm` (§A.4) | The portable record that travels with the snapshot file. It is what an operator, a restore tool, or a second machine reads first — exactly as the sim's manifest does today. |
| **Snapshot metadata row** (new table `snapshot_metadata`, one row per snapshot, 1:1 with `save_slots` — §A.3) | The database-authoritative copy of the same facts: `content_digest`, `digest_algorithm`, the counts at capture, the verification outcome | The queryable, auditable copy. The server's start-up check (§4) reads the database, not a sidecar file; the row is what the loader compares a recomputed digest against, and what an audit query can list across all checkpoints. |

**Why a row in its own table, not a column on `save_slots`:** `save_slots` is the single-player slot table, and `data/schema.sql` states it is *unused in Phase 9* ("characters live server-side" and the character-select list replaces slots). Server snapshots need a home that survives the slot lifecycle rather than depending on it. Digest provenance — algorithm, counts at capture, verification outcome — is per-snapshot metadata, not slot state, and belongs together in one row; widening `save_slots` for a server-only concern would tie the digest to a table Phase 9 does not use and freeze its shape to the slot's.

**Why NEVER a column on `world_state`:** `world_state` is the live single-row state (`id = 1`): the clock, the time scale, the weather preset, the schema version. A digest belongs to a *named checkpoint* — a frozen past state — not to current state, for three reasons:

1. **One row cannot hold one digest per checkpoint.** A world has many named checkpoints and exactly one `world_state` row. A `content_digest` column on `world_state` could hold at most the latest checkpoint's digest, and every new checkpoint would silently overwrite the previous one's evidence.
2. **It would conflate "the world as it is now" with "the world as it was at checkpoint X."** The digest of a checkpoint describes state that no longer exists once the world advances. Writing it into the live row makes the live row lie about the present.
3. **It would be overwritten by ordinary play.** The next day's clock write (`world_state.game_minutes`, §2) is a routine tick operation; a digest stored beside it would share a row — and a write path — with the thing it is meant to independently verify. The verifier must never live in the row it verifies.

The same reasoning is why the digest is never a column on `characters` or `economy_ledger` either: it is a statement *about* a snapshot, not a property of any one row inside it.

## A.2 The digest itself (proven, Session 10 — extended, not reinvented)

The server digest is the sim's digest, `tools/sim/worlds.py` `world_digest()`, with one honest adaptation for the PostgreSQL clock:

- **Algorithm:** SHA-256, hex-encoded (64 lowercase hex characters). The sim uses `hashlib.sha256()`; the server uses the same function over the same logical inputs.
- **Inputs, in order:** (1) every `characters` row — `character_id`, `balance_cached`, `died_at_game_minutes` — ordered by `character_id`; (2) the ledger line `ledger:{COUNT(*)}:{COALESCE(SUM(amount), 0)}` over `economy_ledger`; (3) the clock line. All three column/table names exist verbatim in `data/schema.sql` (`characters.balance_cached`, `characters.died_at_game_minutes`, `economy_ledger.amount` `BIGINT`, `world_state.game_minutes`).
- **The one adaptation — the clock line:** the sim hashes `clock:{day_index}:{game_minutes}`. PostgreSQL `world_state` has **no `day_index`** (§1), so the server hashes `clock:{game_minutes}` only. The day is a read-time derivation (`game_minutes / 1440 + 1`) and is never an input.
- **Consequence, stated plainly:** a sim digest and a server digest are **not comparable across stores**, because their clock lines differ. A digest is comparable only with itself within one store — restore vs pre-restore, restart vs pre-kill — which is exactly the comparison Session 10 proves (restore 0.79 s, digest == pre-restore digest; SIGKILL recovery reproduces the uninterrupted twin's digest). Nobody may claim a server snapshot "matches" a sim checkpoint by comparing their digests.
- **Scope (unchanged from §4):** characters + ledger + clock. It does **not** cover Ambient crowd state (never persisted), derived positions, client caches, or the event registry (an index, never a source). A digest match proves the *society* survived; it says nothing about what any client rendered.

## A.3 The snapshot metadata row (proposed table — design only, NOT in `schema.sql`)

This DDL is the design the Phase 9 migration (§A.5) will carry. It is written here so the migration has an exact target; **it must not be copied into `data/schema.sql` by hand** — `schema.sql` is untouched by this unit and changes only through the migration in §A.5.

```sql
CREATE TABLE snapshot_metadata (
    snapshot_metadata_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    save_slot_id         UUID NOT NULL UNIQUE REFERENCES save_slots(save_slot_id)
                         ON DELETE CASCADE,
    content_digest       TEXT NOT NULL
                         CHECK (content_digest ~ '^[0-9a-f]{64}$'),
    digest_algorithm     TEXT NOT NULL DEFAULT 'sha256'
                         CHECK (digest_algorithm IN ('sha256')),
    code_version         TEXT,            -- e.g. 's10.1'; the sim manifest's code_version string
    schema_version       INTEGER NOT NULL, -- schema_version current at capture
    game_minutes         BIGINT NOT NULL,  -- clock at capture; day is derived, never stored
    population_alive     BIGINT NOT NULL,  -- characters alive at capture (sanity count)
    ledger_rows          BIGINT NOT NULL,  -- COUNT(*) of economy_ledger at capture
    ledger_sum           BIGINT NOT NULL,  -- COALESCE(SUM(amount), 0) at capture
    ledger_reconciled    BOOLEAN NOT NULL, -- ledger_sum_check clean on the copy, at capture
    computed_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_verified_at     TIMESTAMPTZ,      -- last start-up/load recompute that checked this row
    verification_status  TEXT NOT NULL DEFAULT 'unverified'
                         CHECK (verification_status IN ('unverified','verified','mismatch'))
);
```

Design notes: `save_slot_id` is `UNIQUE` (1:1 — one metadata row per snapshot, never two digests for one snapshot); `ON DELETE CASCADE` keeps a deleted snapshot from leaving an orphaned digest behind; `content_digest` is `TEXT` with a 64-hex check rather than a binary type, so the value is readable in any SQL client and comparable by eye with the manifest file's `digest`; `verification_status` records only the *outcome* of the last check — it never overwrites `content_digest`, so a mismatch is preserved as evidence, not papered over.

## A.4 Extended manifest → `save_slots` / `world_state` mapping (with digest)

Every field of the sim checkpoint manifest (`worlds.py` `create_checkpoint()`), plus the server's new `digest_algorithm`, mapped to its home. "— (derived)" means the value is counted or computed on load, never stored as a second copy of the truth; "— (no server home)" means the field has no column and must not gain one by improvisation.

| Sim manifest field | Server home | Rule |
|---|---|---|
| `name` | `save_slots.slot_label` | The checkpoint's human name; the slot label is the same string. |
| `world_db` | — (no server home) | The sim's world-file path. On the server the live world *is* the PostgreSQL database; it is addressed by the server's world list / registry entry (name, seed, code version), not by a column. |
| `checkpoint_db` | `save_slots.payload_ref` | Where the serialised world lives (file path / blob key). The payload is the society: every schema table by name, as JSON rows (`TablePayloads`, TECH-SAVE-SYSTEM §2). |
| `created_utc` | `save_slots.updated_at` | Wall-clock metadata; the *in-world* timestamp is `game_minutes`. |
| `code_version` | `snapshot_metadata.code_version` | The version string (e.g. `s10.1`). The integer `schema_version` is a separate field — see next row. |
| `schema_version` | `save_slots.schema_version` = `world_state.schema_version` = `snapshot_metadata.schema_version` | The three must agree at capture (TECH-SAVE-SYSTEM §2). |
| `seed` | — (no server home) | A property of the *world* (registry / world-list entry), not of the snapshot; it is not copied into a snapshot column. |
| `day_index` | — (derived) | Never stored in PostgreSQL. Derived from `game_minutes` (§1); the manifest's human-readable day is a label, never a second clock. |
| `game_minutes` | `save_slots.game_minutes` = `world_state.game_minutes` = `snapshot_metadata.game_minutes` | Total in-game minutes since Day 1 00:00. |
| `population_alive` | — (derived) + `snapshot_metadata.population_alive` | The server counts `characters` rows on load and compares with the stored count as a sanity check — a mismatch is a corrupt snapshot, not a rounding difference. |
| `ledger_rows` | — (derived) + `snapshot_metadata.ledger_rows` | Same: counted from `economy_ledger` on load, compared with the stored count. |
| `ledger_reconciled` | The load gate + `snapshot_metadata.ledger_reconciled` | The server loads a snapshot only if its ledger reconciles (`ledger_sum_check` clean, conservation clean). A snapshot whose ledger does not reconcile is refused, never repaired in place. |
| `digest` | **`snapshot_metadata.content_digest`** (authoritative) + manifest file `digest` (portable copy) | The two copies must agree at load. The digest lives here and in the manifest file — **never as a column on `world_state`** (§A.1). |
| `digest_algorithm` *(new in the server manifest)* | `snapshot_metadata.digest_algorithm` + manifest file `digest_algorithm` | `'sha256'` today; the field exists so a future algorithm change is a recorded fact per snapshot, not a silent assumption. |

## A.5 Forward-only migration note — adding digest metadata in Phase 9

**This note is the migration record for the digest. It lives here, in this design document — it is NOT written into `data/schema.sql`, and `schema.sql` must not be modified to carry it.** Per the `schema.sql` header and GDD-01 §10, the migration itself ships as a numbered migration with the Phase 9 deploy, and this note is what the PR carries. Proposed migration name: `002_snapshot_metadata` (a design-time name — no migrations directory exists in this repo yet; the Phase 9 deploy creates the convention).

**Numbered steps:**

1. **Author the migration.** One statement: `CREATE TABLE snapshot_metadata (...)` exactly as §A.3. Nothing else. No `ALTER TABLE world_state`, no `ALTER TABLE save_slots`, no change to `characters`, `economy_ledger`, or any history table, no index on a table that is not being created.
2. **Deploy with the server.** The migration runs at deploy (GDD-01 §9: migrations run at deploy; every save/snapshot carries `schema_version`). It is additive only — the deploy adds a table; it does not rewrite, re-derive, or re-stamp any existing row.
3. **Backfill: none, by rule.** There are no existing digest rows to backfill, because none exist. Snapshots taken *before* this migration have a manifest file with a `digest` but no metadata row. On their first load after the migration, the server recomputes the digest from the payload, compares it with the manifest file's `digest`, and — only if they agree — inserts the `snapshot_metadata` row (adoption by verification, never by copying the manifest value blindly). A pre-migration snapshot whose manifest digest does not recompute is refused like any other mismatch.
4. **Write path from then on.** Snapshot creation computes the digest once, inserts the `snapshot_metadata` row, then writes the manifest file. The manifest file and the database row cannot share one transaction, so the loader — not the writer — enforces atomicity: a snapshot is listable/loadable only when the row and the manifest file both exist **and** their digests agree. A row without a manifest, or a manifest without a row, is invisible to the loader and is cleanup, never a load candidate.
5. **Verification at start-up (the load gate, §4).** On every server start the server recomputes the digest of the loaded snapshot and compares it with `snapshot_metadata.content_digest` **and** with the manifest file's `digest`. All three agree = start. Any disagreement = refuse to start on that snapshot, fall back to the previous named checkpoint, and write an audit row. The recompute also updates `last_verified_at` and `verification_status` (`verified` / `mismatch`); it never overwrites `content_digest`.
6. **Versioning.** The migration does not change the meaning of any existing row, so existing snapshots keep their `schema_version`; new snapshots record the `schema_version` current at capture in all three places (§A.4). A snapshot from a *newer* version is shown but refused, in words (GDD-05 §7 save/load rule, §3).

**What is never altered:** `world_state` (no new column, no new row — it stays the single-row clock); `save_slots` (no new column); `economy_ledger` and every history table (append-only; a migration never rewrites history); any existing row's `schema_version`; any digest value once written (a `content_digest` is never "fixed" to match a payload — that would destroy the evidence the digest exists to preserve).

**Rollback posture — forward-only, no down-migration:** there is no down-migration for this change, and none may be written later. If the migration must be undone, the rollback is forward: deploy a *new* migration that stops the server using the table, or a later forward migration that removes it — never a `DROP TABLE` smuggled in as a rollback step, and never a delete of digest rows. Digest rows are audit evidence of what a checkpoint contained; deleting them would erase the record of exactly the snapshots a rollback is trying to reason about. The table is cheap to keep and safe to ignore; the rows are never deleted by a rollback.

## A.6 Honest boundaries — what this design does and does not do

- **The digest is an integrity check at server start-up and load, not a repair tool.** A mismatch refuses the snapshot (§A.5 step 5). What it **never** does: repair a ledger in place, rewrite history rows to match a digest, "fix" a stored digest to match a changed payload, silently start on a wrong world, or reconstruct a lost snapshot from its digest (a hash cannot rebuild the society it summarises). The only recovery from a mismatch is the previous named checkpoint — which is why checkpoints are taken every in-game week and on clean shutdown (§2).
- **No new server code is shipped here.** No snapshot writer, no start-up check, no migration file, no netcode. This appendix is a build instruction for Phase 9; the first server test happens on the owner's PC/LAN (TECH-MULTIPLAYER §6), and the §8 test plan — digest round-trip, kill recovery, isolation — is the acceptance bar the implementation must meet.
- **The §9 open item is closed as a design question, open as implementation.** The digest's home is now decided (manifest file + `snapshot_metadata` row). The table does not exist in `schema.sql` yet, no migration file exists, and no digest has ever been computed by a server. Nothing in this appendix should be read as claiming otherwise.
- **Still open from §9, untouched by this unit:** no network API, no user accounts, no network security surface (checklist item 19 stays PARTIALLY PROVEN), no distributed processing or partitioning, no real-time server in this VM. This appendix closes one open item; it does not close the programme.

*End of Appendix A — Unit AP, Queue 8.*

---

# Appendix B — Ledger Idempotency Keys: Migration Note (Unit BD · Queue 10 · §10 follow-up)

**Version:** appendix added 2026-11-22 · **Code:** none — design only. No server build, no netcode, no migration file exists yet; nothing here claims a server has ever written a keyed ledger row.
**Parent documents:** `docs/TECH-PERSISTENT-WORLD.md` §2, §7 rule 2, §10 (the decision this appendix records) · `tools/sim/persistence.py` `Store.transfer` + `_migrate` (the proven sim rule this migrates to PostgreSQL) · `data/schema.sql` (`economy_ledger`) · GDD-01 §8 (ledger), §9 (forward-only migrations) · `docs/TECH-CHECKPOINT-RUNBOOK.md` §7 OD-8 (the open decision §10 closes).
**What this appendix does:** it records the migration for the §10 decision, following Appendix A's §A.5 pattern step for step — the same numbered-steps shape, the same no-backfill rule, the same forward-only rollback posture. It is the migration record for the key columns. It lives here, in this design document — it is NOT written into `data/schema.sql`, and `schema.sql` must not be modified to carry it.

## B.1 The migration (exact statements)

Proposed migration name: `003_ledger_idempotency_keys` (a design-time name — it follows Appendix A's proposed `002_snapshot_metadata`; no migrations directory exists in this repo yet, and the Phase 9 deploy creates the convention).

```sql
ALTER TABLE economy_ledger ADD COLUMN transfer_key TEXT;
ALTER TABLE economy_ledger ADD COLUMN event_ref TEXT;
CREATE UNIQUE INDEX idx_ledger_transfer_key ON economy_ledger (transfer_key);
```

Three statements, nothing else. No `ALTER TABLE` on any other table, no change to `reason_code` or its `CHECK` list, no change to the append-only triggers, no index on a table that is not being changed.

## B.2 Numbered steps

1. **Author the migration.** The three statements in §B.1, exactly as written. Nothing else.
2. **Deploy with the server.** The migration runs at deploy (GDD-01 §9: migrations run at deploy; every save/snapshot carries `schema_version`). It is additive only — the deploy adds two columns and one index; it does not rewrite, re-derive, or re-stamp any existing row.
3. **Backfill: none, by rule.** Rows written before this migration keep `NULL` for both columns. No key is invented for them, and no `event_ref` is reconstructed from history: a pre-migration row without a key is still a valid ledger row, and the idempotency guarantee covers only rows written with a key. PostgreSQL unique indexes treat `NULL` as distinct, so the new index accepts any number of pre-migration `NULL` rows.
4. **Write path from then on.** Every server-validated transaction that carries a client request key writes `transfer_key` (and `event_ref` where the caller supplies one) in the same transaction as the ledger row (§10 rule 1). A transfer without a key — a system flow with no client request behind it, such as the monthly settlement chain — writes `NULL` and is complete without one: the key is per-request idempotency, not a mandatory field on every row.
5. **Read path from then on.** A retried request is looked up by `transfer_key` before any money moves: a hit returns the original `ledger_id` and moves nothing (§10 rule 1). The lookup is the same query the sim proves (`SELECT ledger_id FROM economy_ledger WHERE transfer_key = ?`), now backed by the unique index instead of a scan.
6. **Versioning.** The migration does not change the meaning of any existing row, so existing snapshots keep their `schema_version`; new snapshots record the `schema_version` current at capture. A snapshot from a *newer* version is shown but refused, in words (GDD-05 §7 save/load rule, §3).

## B.3 What is never altered

`world_state` (no new column — the key is not clock state); `save_slots` (no new column); `economy_ledger`'s existing columns, its `reason_code` `CHECK` list, and its append-only triggers (a migration never rewrites history); any existing row's `transfer_key`/`event_ref` once written (a key is never "fixed" to match a retry — the original row is the answer); any existing row's `schema_version`.

## B.4 Rollback posture — forward-only, no down-migration

There is no down-migration for this change, and none may be written later. If the migration must be undone, the rollback is forward: deploy a *new* migration that stops the server using the columns, or a later forward migration that removes them — never a `DROP COLUMN` smuggled in as a rollback step, and never a delete of keyed rows. Keyed rows are the audit evidence of which transfers were deduplicated; deleting them would erase the record of exactly the retries a rollback is trying to reason about. The columns are cheap to keep and safe to ignore; the rows are never deleted by a rollback.

## B.5 Honest boundaries — what this design does and does not do

- **The key is a deduplication fact, not a repair tool.** A retry that finds its key learns the original outcome (§10.5, test 4). What it **never** does: repair a ledger, rewrite a history row, or resurrect a transfer whose row was never committed — a request with no committed row and no key on file is a new transfer, not a retry.
- **No new server code is shipped here.** No transfer endpoint, no retry handler, no migration file, no netcode. This appendix is a build instruction for Phase 9; the first server test happens on the owner's PC/LAN (TECH-MULTIPLAYER §6), and the §8 test plan — ledger race, disconnect honesty, soak — is the acceptance bar the implementation must meet.
- **The §9 open item OD-8 is closed as a design question, open as implementation.** The key's home is now decided (two columns on `economy_ledger`, §10). The columns do not exist in `schema.sql` yet, no migration file exists, and no key has ever been written by a server. Nothing in this appendix should be read as claiming otherwise.
- **Still open from §9 and from the runbook, untouched by this unit:** no network API, no user accounts, no network security surface (checklist item 19 stays PARTIALLY PROVEN), no distributed processing or partitioning, no real-time server in this VM — and the runbook's other open decisions OD-1–OD-7 (operator wording, retention, anchor, fallback automation, audit destination, payload store, operator tooling) are untouched by this unit and are drafted for Queue 11.

*End of Appendix B — Unit BD, Queue 10.*

*End of TECH-PERSISTENT-WORLD v1.0 — Unit AM, Queue 7.*
