# NEXORA — Tech Note: Phase 9 Checkpoint & Recovery Runbook

**Unit AW · Queue 9 · Version 1.0 · 2026-11-22**
**Code:** none — design only. No server build, no netcode, no snapshot code, no start-up check exists yet; nothing here claims a procedure in this document has ever been executed against a live server.
**Parent documents:** `docs/TECH-PERSISTENT-WORLD.md` (§2 per-tick vs per-checkpoint, §3 manifest mapping, §4 digest verification, §9; Appendix A — snapshot digest metadata) · `docs/TECH-MULTIPLAYER.md` (Phase 9 dedicated-server design, §2 session shape, §4 server authority, §6 test plan) · `docs/SESSION-10-REPORT.md` (§2.2–2.4 world registry, named checkpoints, time modes; §6 endurance/recovery benchmarks; §8 checklist items 15–17, 20) · `docs/FINAL-ARCHITECTURE.md` (layers 1, 12, 13 — world, event & time, persistence) · `data/schema.sql` (`save_slots`, `world_state`, `characters`, `economy_ledger`) · `docs/TECH-SAVE-SYSTEM.md` §2 (single-player save shape the server snapshot extends) · `tools/sim/worlds.py` (`world_digest()`, `create_checkpoint()` — the proven digest and manifest this runbook turns into procedure).
**Status:** DESIGN ONLY — an operator procedure for Phase 9, built from the proven headless system. The left-hand side of every step is measured (Session 10); the right-hand side is what the operator does when the Phase 9 server exists. First server test happens on the owner's PC/LAN (TECH-MULTIPLAYER §6).

> **Operator's law:** the digest guards the truth, not the picture (TECH-PERSISTENT-WORLD §4). A checkpoint is a day-boundary state, never a partial day. A mismatch is refused, never repaired. When in doubt, fall back — a silently wrong world is worse than a down server (TECH-PERSISTENT-WORLD §4).

## 0. How to read this runbook

- **"The sim"** means the proven headless simulation (Session 10, `tools/sim/`). **"The server"** means the Phase 9 dedicated server (TECH-MULTIPLAYER §1: headless UE server build; owner's PC for LAN tests, a small hosted instance later). Where a step cites a sim behaviour, the citation is the proof; where it prescribes server behaviour, the citation is the design it implements.
- **No user interface is specified anywhere in this runbook.** The sources define states and outcomes ("refuse to start", "fall back", "write an audit row"), not screens, buttons, or literal message text. The exact operator-facing wording is defined in §10 (Unit BI, Queue 11), which resolves open decision OD-1.
- **Tables and fields are quoted exactly as the sources state them.** Where PostgreSQL `data/schema.sql` and the sim's SQLite differ — above all the clock — the difference is stated in the step, not smoothed over (§2.3).

---

## 1. When named checkpoints are taken — the day-boundary rule

### 1.1 The rule

A named checkpoint is **always a day-boundary state, never a partial day** (TECH-PERSISTENT-WORLD §2, §7 rule 4). The clock write is the day's commit marker: `Store.set_world` writes `day_index` + `game_minutes` once, at the end of `run_day`, after every daily, festival and monthly pass (SESSION-10-REPORT §1.2, defect #2). On the server the same point is the once-per-day write of `world_state.game_minutes` (TECH-PERSISTENT-WORLD §2). A checkpoint taken mid-day is not a checkpoint — it is a partial day, and the recovery rule (§5) discards partial days.

### 1.2 The schedule

| Trigger | Rule | Source |
|---|---|---|
| Every in-game week | A named checkpoint is taken once per in-game week, at a day boundary | TECH-PERSISTENT-WORLD §2 ("Taken periodically (design decision for Phase 9: every in-game week + on clean shutdown)") |
| Clean shutdown | A named checkpoint is taken on clean shutdown, at a day boundary | TECH-PERSISTENT-WORLD §2 |
| On demand | An operator may take a named checkpoint at any day boundary | TECH-PERSISTENT-WORLD §2 ("and on demand") |
| Mid-day | **Never.** No checkpoint is taken mid-day, mid-tick, or mid-settlement | TECH-PERSISTENT-WORLD §2, §7 rule 4 |

The anchor day within the week is fixed by §11.2 (Unit BJ, Queue 11): the day boundary ending each in-game Sunday (Monday 00:00).

### 1.3 What is captured per tick vs per checkpoint

This is the operator's working form of TECH-PERSISTENT-WORLD §2. "Per tick" means written as the tick runs; "per checkpoint" means written only when a named snapshot is taken.

| Cadence | What is written | Operator meaning |
|---|---|---|
| **Every transfer** | `Store.transfer` appends an `economy_ledger` row (reason code, optional `event_ref`, idempotency `transfer_key`) in the same transaction as the balance-cache update. Server: every server-validated transaction appends to `economy_ledger` in one PostgreSQL transaction. Clients never write rows (TECH-MULTIPLAYER §4). | Money exists only as ledger rows. A transfer without a ledger row does not exist. |
| **Once per day** | Clock write: `Store.set_world` writes `day_index` + `game_minutes` once, at the end of `run_day`, after every daily, festival and monthly pass. Server: `world_state.game_minutes` written once per in-game day, at the same point in its tick — after the settlement chain (FINAL-ARCHITECTURE: social → economy → city → economy close → government → humandev → transport → environment → agents → integration). | **The clock write *is* the commit marker for the day.** A day is never half-written. |
| **End of day** | Registry sync runs last in `run_day` (Session 10 defect #1: it was placed too early and indexed a day late; fixed by moving it to the very end). Server: the event-index sync runs last in the server tick, for the same reason. | The registry indexes history tables; it never feeds a simulation decision (FINAL-ARCHITECTURE layer 12). |
| **Monthly** | Monthly settlement chain + snapshots (`economic_indicators`, `city_statistics`, `human_development_indicators`, `transport_statistics`, `env_snapshots`, `opinion_snapshots`). Server: same monthly passes, same tables. | Snapshots are *derived rows*, recomputable from history — the server may rebuild them from the ledger/history rather than trusting a stored copy. |
| **Per checkpoint (named)** | Named snapshot via the SQLite backup API + JSON manifest: sim day, population, ledger rows, **ledger reconciled** (verified on the copy), content digest, code version. Server: the snapshot of §3, taken per §1.2. | The checkpoint is the only restorable unit. Nothing else is a restore point. |
| **Never persisted** | Ambient crowd state, derived NPC positions, client-side caches, the observatory's read models. Server: same — Ambient crowds are local per client and never sent (TECH-MULTIPLAYER §3); a Scheduled NPC's position is derived from schedule + anchor graph on both sides. | Persisting a derived position would be storing a fact twice and letting the copies disagree. |

**Schema discrepancy found while verifying this runbook (§1.3, "Every transfer" row):** the sim's `Store.transfer` rows carry a reason code, an optional `event_ref`, and an idempotency `transfer_key`, and TECH-PERSISTENT-WORLD §2 says the server appends with "same fields, same rule" — but `data/schema.sql`'s `economy_ledger` as drafted lists `reason_code` and no `transfer_key` or `event_ref` column (columns: `ledger_id`, `from_character_id`, `to_character_id`, `from_business_id`, `to_business_id`, `amount`, `reason_code`, `related_property_id`, `related_business_id`, `note`, `game_minutes`, `created_at`). The server-side home for the idempotency key is decided by Queue 10, Unit BD — TECH-PERSISTENT-WORLD §10 + Appendix B (forward-only migration `003` adds the columns). This runbook does not claim the columns exist in `schema.sql`.

---

## 2. What a checkpoint captures

### 2.1 The sim manifest (proven — `tools/sim/worlds.py` `create_checkpoint()`)

The sim writes a JSON manifest beside the copied world file. Every field below is a field of that manifest, quoted verbatim:

| Manifest field | How it is produced |
|---|---|
| `name` | The checkpoint's name, as given to `--checkpoint`. |
| `world_db` | Absolute path of the live world file. |
| `checkpoint_db` | Absolute path of the copied world file (SQLite backup API — the copy holds exactly the committed state). |
| `created_utc` | Wall-clock creation time, UTC ISO format. |
| `code_version` | The sim's code version string (e.g. `s10.1`, from `data/integration-config.json`). |
| `schema_version` | From `world_state.schema_version` on the copy. |
| `seed` | From `world_state.sim_seed`. |
| `day_index` | From `world_state.day_index`. |
| `game_minutes` | From `world_state.game_minutes`. |
| `population_alive` | `SELECT COUNT(*) FROM characters WHERE is_system = 0 AND died_at_game_minutes IS NULL` — alive, non-system characters only. |
| `ledger_rows` | `SELECT COUNT(*) FROM economy_ledger`. |
| `ledger_reconciled` | `store.ledger_sum_check() == []` — verified on the copy, at capture. |
| `digest` | `world_digest(target)` — the content digest of the copy (§3). |

### 2.2 The server mapping (design — TECH-PERSISTENT-WORLD §3 and Appendix A §A.4)

The server snapshot is the same object with a different home. `save_slots` is the single-player slot table, and `data/schema.sql` states it is *unused in Phase 9* ("characters live server-side" and the character-select list replaces slots) — the server reuses the slot *shape* for snapshots, not the single-player lifecycle (TECH-PERSISTENT-WORLD Appendix A §A.1).

| Sim manifest field | Server home | Rule |
|---|---|---|
| `name` | `save_slots.slot_label` | The checkpoint's human name; the slot label is the same string. |
| `world_db` | — (no server home) | On the server the live world *is* the PostgreSQL database; it is addressed by the server's world list / registry entry (name, seed, code version), not by a column. |
| `checkpoint_db` | `save_slots.payload_ref` | Where the serialised world lives (file path / blob key). The payload is the society: every schema table by name, as JSON rows (`TablePayloads`, TECH-SAVE-SYSTEM §2). |
| `created_utc` | `save_slots.updated_at` | Wall-clock metadata; the *in-world* timestamp is `game_minutes`. |
| `code_version` | `snapshot_metadata.code_version` | The version string (e.g. `s10.1`). The integer `schema_version` is a separate field. |
| `schema_version` | `save_slots.schema_version` = `world_state.schema_version` = `snapshot_metadata.schema_version` | The three must agree at capture (TECH-SAVE-SYSTEM §2). |
| `seed` | — (no server home) | A property of the *world* (registry / world-list entry), not of the snapshot; it is not copied into a snapshot column. |
| `day_index` | — (derived) | Never stored in PostgreSQL (§2.3). Derived from `game_minutes`; the manifest's human-readable day is a label, never a second clock. |
| `game_minutes` | `save_slots.game_minutes` = `world_state.game_minutes` = `snapshot_metadata.game_minutes` | Total in-game minutes since Day 1 00:00. New world = 480 (Day 1, 08:00) — `data/schema.sql` `world_state.game_minutes` default. |
| `population_alive` | — (derived) + `snapshot_metadata.population_alive` | The server counts `characters` rows on load and compares with the stored count as a sanity check — a mismatch is a corrupt snapshot, not a rounding difference. |
| `ledger_rows` | — (derived) + `snapshot_metadata.ledger_rows` | Same: counted from `economy_ledger` on load, compared with the stored count. |
| `ledger_reconciled` | The load gate + `snapshot_metadata.ledger_reconciled` | The server loads a snapshot only if its ledger reconciles (`ledger_sum_check` clean, conservation clean — the Session 10 acceptance battery). A snapshot whose ledger does not reconcile is refused, never repaired in place. |
| `digest` | **`snapshot_metadata.content_digest`** (authoritative) + manifest file `digest` (portable copy) | The two copies must agree at load. The digest lives here and in the manifest file — **never as a column on `world_state`** (Appendix A §A.1). |
| `digest_algorithm` *(new in the server manifest)* | `snapshot_metadata.digest_algorithm` + manifest file `digest_algorithm` | `'sha256'` today; the field exists so a future algorithm change is a recorded fact per snapshot, not a silent assumption. |

### 2.3 The clock correction the operator must not get wrong

There is no `game_clock` table and never was (SESSION-10-REPORT §1.2, defect #2). The clock is the `world_state` row. The sim's SQLite `world_state` carries both `day_index` and `game_minutes`; the PostgreSQL `world_state` in `data/schema.sql` carries `game_minutes` only — `game_minutes BIGINT NOT NULL DEFAULT 480` (starts Day 1, 08:00), `time_scale`, `weather_preset`, `schema_version`, single row `id = 1`. The server derives the day as `game_minutes / 1440 + 1` (TECH-SAVE-SYSTEM §2: `GameMinutes = (DayNumber − 1) × 1440 + MinutesSinceMidnight`). **The operator must never invent a `day_index` column in PostgreSQL**; the day is a read-time derivation on the server, exactly as it is in the sim's `store.world()` reads (TECH-PERSISTENT-WORLD §1).

### 2.4 The digest's home — `snapshot_metadata` (design, not yet in `schema.sql`)

Appendix A decides the digest's home: a manifest file **plus** a dedicated `snapshot_metadata` row, one row per snapshot, 1:1 with `save_slots` (`save_slot_id UUID NOT NULL UNIQUE REFERENCES save_slots(save_slot_id) ON DELETE CASCADE`). The proposed table is defined in TECH-PERSISTENT-WORLD Appendix A §A.3 and is **not** in `data/schema.sql` — it arrives with the Phase 9 forward-only migration `002_snapshot_metadata` (Appendix A §A.5; a design-time name — no migrations directory exists in this repo yet). The operator's rules for it:

- `content_digest` is `TEXT` with a 64-hex check (`^[0-9a-f]{64}$`); `digest_algorithm` is `'sha256'` today.
- The row also carries `code_version`, `schema_version`, `game_minutes`, `population_alive`, `ledger_rows`, `ledger_sum` (`COALESCE(SUM(amount), 0)` at capture), `ledger_reconciled`, `computed_at`, `last_verified_at`, `verification_status` (`'unverified'` / `'verified'` / `'mismatch'`).
- `verification_status` records only the *outcome* of the last check — it never overwrites `content_digest`, so a mismatch is preserved as evidence, not papered over.
- **Backfill: none, by rule** (Appendix A §A.5 step 3). Snapshots taken *before* the migration have a manifest file with a `digest` but no metadata row. On their first load after the migration, the server recomputes the digest from the payload, compares it with the manifest file's `digest`, and — only if they agree — inserts the `snapshot_metadata` row (adoption by verification, never by copying the manifest value blindly). A pre-migration snapshot whose manifest digest does not recompute is refused like any other mismatch.
- **A snapshot is listable/loadable only when the row and the manifest file both exist and their digests agree.** A row without a manifest, or a manifest without a row, is invisible to the loader and is cleanup, never a load candidate (Appendix A §A.5 step 4).

---

## 3. How the content digest is verified at load

### 3.1 What is hashed — the sim digest (proven)

`tools/sim/worlds.py` `world_digest()`: SHA-256 over, in order — (1) every `characters` row, `character_id`, `balance_cached`, `died_at_game_minutes`, ordered by `character_id`; (2) the ledger line `ledger:{COUNT(*)}:{COALESCE(SUM(amount), 0)}` over `economy_ledger`; (3) the clock line. The digest covers **characters + ledger + clock** — the parts of a world that must survive a save, a restore, a duplication, and a kill (TECH-PERSISTENT-WORLD §4).

### 3.2 The one server adaptation — the clock line

The sim hashes `clock:{day_index}:{game_minutes}`. PostgreSQL `world_state` has **no `day_index`** (§2.3), so the server hashes `clock:{game_minutes}` only. The day is a read-time derivation (`game_minutes / 1440 + 1`) and is never an input.

**Cross-store caveat, stated plainly (Appendix A §A.2): a sim digest and a server digest are not comparable across stores, because their clock lines differ.** A digest is comparable only with itself within one store — restore vs pre-restore, restart vs pre-kill — which is exactly the comparison Session 10 proves (restore 0.79 s, digest == pre-restore digest; SIGKILL recovery reproduces the uninterrupted twin's digest). Nobody may claim a server snapshot "matches" a sim checkpoint by comparing their digests.

### 3.3 What the digest does not cover

It does **not** cover Ambient crowd state (never persisted), derived positions, client caches, or the event registry (an index, never a source). A digest match proves the *society* survived; it says nothing about what any client rendered (TECH-PERSISTENT-WORLD §4).

### 3.4 The load-time verification procedure (server start-up / snapshot load)

On every server start, the server recomputes the digest of the loaded snapshot and compares it with the stored manifest digest (TECH-PERSISTENT-WORLD §4). The full gate, per Appendix A §A.5 step 5, is a **three-way agreement**:

1. **Recompute** the digest from the snapshot payload: SHA-256 hex (64 lowercase hex characters) over `characters` (`character_id`, `balance_cached`, `died_at_game_minutes`, ordered by `character_id`) + `ledger:{COUNT(*)}:{COALESCE(SUM(amount), 0)}` over `economy_ledger` + `clock:{game_minutes}`.
2. **Compare** the recomputed digest with `snapshot_metadata.content_digest` **and** with the manifest file's `digest`. All three agree = start. Any disagreement = refuse (§4).
3. **Count check:** count `characters` rows on load and compare with `snapshot_metadata.population_alive`; count `economy_ledger` rows and compare with `snapshot_metadata.ledger_rows`. A mismatch is a corrupt snapshot, not a rounding difference (§2.2).
4. **Ledger gate:** load only if the ledger reconciles — `ledger_sum_check` clean, conservation clean (the Session 10 acceptance battery; `finance.verify_conservation` in the sim). A snapshot whose ledger does not reconcile is refused, never repaired in place (§2.2).
5. **Version gate:** `save_slots.schema_version` = `world_state.schema_version` = `snapshot_metadata.schema_version` must agree at capture (TECH-SAVE-SYSTEM §2). A snapshot from a *newer* version is shown but refused, in words (GDD-05 §7 save/load rule, TECH-PERSISTENT-WORLD §3). A snapshot from an older version migrates on load; migrations are forward-only (GDD-01 §9).
6. **Record the outcome:** the recompute updates `snapshot_metadata.last_verified_at` and `snapshot_metadata.verification_status` (`verified` / `mismatch`); it **never** overwrites `content_digest` (Appendix A §A.5 step 5).

**Proven timings the operator can expect the check against** (Session 10 §6, endurance world, 242 residents, 365 days): checkpoint save 2.90 s, restore 0.79 s, restored digest == pre-restore digest, manifest `ledger_reconciled = true`. These are sim measurements on this VM, not server guarantees.

---

## 4. The fallback chain on mismatch

The chain is, in order: **refuse the snapshot → fall back to the previous named checkpoint → genesis.** Each step is a full re-verification (§3.4), not a shortcut.

### 4.1 Step 1 — Refuse the snapshot

| | |
|---|---|
| **Trigger** | Any disagreement at §3.4: recomputed digest ≠ `snapshot_metadata.content_digest`, or ≠ manifest file `digest`, or a count mismatch, or the ledger gate fails, or the version gate refuses. |
| **Server state** | The server **does not start on that snapshot**. "Never start on a world whose digest does not match — a silently wrong world is worse than a down server" (TECH-PERSISTENT-WORLD §4). |
| **What the operator sees** | The load is refused for that snapshot. The refusal is recorded: `snapshot_metadata.verification_status` is set to `'mismatch'` with `last_verified_at` updated, and an audit row is written (Appendix A §A.5 step 5). The stored `content_digest` is left untouched — the mismatch is preserved as evidence. No literal message text is defined by any source; exact wording is defined in §10 (Unit BI, Queue 11). |
| **What is never done here** | No repair-in-place of the ledger, no rewrite of history rows to match a digest, no "fix" of a stored digest to match a changed payload, no silent start on the wrong world, no reconstruction of a lost snapshot from its digest (a hash cannot rebuild the society it summarises) — Appendix A §A.6. |

### 4.2 Step 2 — Fall back to the previous named checkpoint

| | |
|---|---|
| **Trigger** | Step 1 refused the newest named checkpoint. |
| **Action** | Load the **previous named checkpoint** — the next-newest snapshot in the named-checkpoint list — and run the full §3.4 verification on it from scratch (recompute, three-way digest agreement, counts, ledger gate, version gate). |
| **What the operator sees** | The server starts from the previous named checkpoint, at that checkpoint's day (its `game_minutes`, day derived). Play that happened after that checkpoint is gone — that is the honest cost of the fallback, and why checkpoints are taken every in-game week and on clean shutdown (§1.2). The fallback and the refused snapshot are both on the audit record. |
| **If the previous checkpoint also fails** | Repeat step 2 with the next-older named checkpoint, in order, until one passes §3.4 or the list is exhausted. Each failure is recorded the same way (`verification_status` `'mismatch'`, audit row, digest untouched). Whether this walk is automatic or needs the operator to confirm each step is decided in §11.3 (Unit BJ, Queue 11): confirmation per step. |

### 4.3 Step 3 — Genesis (the list is exhausted)

| | |
|---|---|
| **Trigger** | Every named checkpoint has been refused, or no named checkpoint exists. |
| **Action** | Start a **new world from genesis** — a fresh world built from the world's registry entry (name, seed, code version; SESSION-10-REPORT §2.2: registry entries carry world id `WORLD-0001…`, name, path, seed, config/code version, registered time). Genesis is a new world, not a repair of the lost one: nothing from the refused snapshots is carried over, because nothing in them is trusted. |
| **What the operator sees** | The server starts a fresh world at Day 1, 08:00 (`game_minutes` 480). All prior progress is lost. This is the last resort by design — it exists so the server can always start honestly, never so a broken world can be quietly replaced. |
| **Operator decision required** | Genesis proceeds only on explicit operator confirmation, typing the world name (§11.3, Unit BJ, Queue 11). No source authorises silently discarding a world's history. |

### 4.4 The chain at a glance

```
newest named checkpoint ──§3.4──► pass → START (verification_status 'verified')
        │ fail (digest / counts / ledger / version)
        ▼
refuse snapshot → verification_status 'mismatch' + audit row → digest untouched
        │
        ▼
previous named checkpoint ──§3.4──► pass → START at that checkpoint's day
        │ fail … repeat with next-older checkpoint …
        ▼
list exhausted → GENESIS (fresh world, Day 1 08:00, game_minutes 480)
```

A snapshot from a *newer* version is a different refusal from a mismatch: it is shown but refused, in words (GDD-05 §7), and it does **not** enter the mismatch chain as a corrupt snapshot — it is a version refusal, recorded as such, and the operator falls back the same way (§4.2) without marking the newer snapshot's digest as evidence of corruption.

---

## 5. Crash recovery — from the Session 10 proof

### 5.1 The proven fact (SESSION-10-REPORT §2.3, §6)

A subprocess resuming a world was SIGKILLed mid-run; on reopen the ledger reconciles, the clock stands at the last committed day (never a partial day), and continuing to the twin's day reproduces the uninterrupted twin's digest exactly. Measured (pop 60, seed `s10-recovery`): world built to day 35, resumed toward day 300, SIGKILLed at **day 41**; reopen + verify (ledger clean) + continue to day 65 took **7.9 s** total; the recovered world's digest equals its uninterrupted twin's exactly.

### 5.2 The server procedure (design — TECH-PERSISTENT-WORLD §4)

The server's crash story is the same, with the database doing the work the file did: **PostgreSQL WAL + the once-per-day clock write as the commit marker.**

| Step | Operator action | What the system does |
|---|---|---|
| 1. Confirm the process is dead | Confirm the server process has stopped (crash, SIGKILL, host loss). Do not start a second server against the same database. One dedicated server = one persistent District 1 world in v1 (TECH-MULTIPLAYER §2). | — |
| 2. Restart the server | Start the server against the same database. | PostgreSQL WAL rolls forward to the last committed transaction. |
| 3. Roll forward to the last committed day | No operator action — this is the recovery. | The server rolls forward to the **last committed day** and discards any partial day. There is no such thing as a half-written day in either store, because the clock write *is* the day's commit marker (§1.3): a day whose clock write never landed never happened. |
| 4. Verify before serving | No operator action beyond reading the result — the start-up check runs (§3.4). | The server recomputes the digest of the loaded state, checks the ledger (`ledger_sum_check` clean, conservation clean), and confirms the clock stands at the last committed day. |
| 5. Resume | If §3.4 passes, the server resumes ticking from the last committed day. If it fails, §4 applies — refuse, fall back to the previous named checkpoint, write an audit row. | Continuing from the recovered state reproduces the uninterrupted twin's digest — that is the acceptance test (TECH-PERSISTENT-WORLD §8 test 2: "Kill recovery: SIGKILL the server mid-day; on restart the ledger reconciles, the clock stands at the last committed day, and continuing reproduces the uninterrupted twin's digest"). |

### 5.3 What crash recovery is not

- It is **not** a restore from a checkpoint: the live database is recovered in place by WAL roll-forward; checkpoints are only used if the recovered state itself fails verification (§4).
- It is **not** a repair: if the recovered ledger does not reconcile, the state is refused, not fixed (§4.1).
- It does **not** recover a partial day: a day whose clock write never landed is discarded in full. The world resumes at the last committed day, never mid-day.
- The sim's recovery proof used SQLite WAL; the server's uses PostgreSQL WAL. The mechanism differs by store; the invariant — clock write as commit marker, no partial day — is identical (TECH-PERSISTENT-WORLD §4).

### 5.4 Related start-up and periodic checks (operator's standing list)

- **Digest round-trip** (TECH-PERSISTENT-WORLD §8 test 1): take a server snapshot, restore it on a second machine, recompute the digest — identical to the live world's digest. (Sim proof: SESSION-10-REPORT §6, restore 0.79 s, digest == pre-restore digest.)
- **Isolation** (TECH-PERSISTENT-WORLD §8 test 3): two worlds on one server host; advance world A 30 days; world B's digest byte-identical. (Sim proof: `test_integration_worlds`; SESSION-10-REPORT §8 item 15 PROVEN.) One server = one world in v1, so isolation is trivially satisfied until a second world exists.
- **Registry completeness** (TECH-PERSISTENT-WORLD §4): periodically (not per tick), index counts vs source-table counts. A gap is an audit finding, and the index is rebuilt from the sources — the sources are never rewritten to match the index. (Sim proof: SESSION-10-REPORT §1.2, defect #1 — registry counts for the total-mapping append sources equal their source-table counts exactly.)
- **Playback purity** (TECH-PERSISTENT-WORLD §8 test 7): run the observatory views against the live server; digest before == digest after (the sim's playback test, applied to the server). Playback reads history tables and the event index; it writes nothing.

---

## 6. What is NEVER done

These are prohibitions, not preferences. Each is stated in a parent document; the runbook adds nothing to the list.

| # | Never | Source |
|---|---|---|
| 1 | **Repair a snapshot in place.** A snapshot whose ledger does not reconcile is refused, never repaired. | TECH-PERSISTENT-WORLD §3, §A.4; Appendix A §A.6 |
| 2 | **Rewrite a stored digest to match a changed payload.** A `content_digest` is never "fixed" — that would destroy the evidence the digest exists to preserve. | Appendix A §A.3, §A.5 ("What is never altered") |
| 3 | **Rewrite history to match a digest or an index.** History is write-once; a "correction" is a new row referencing the old one, never an edit. The event index is rebuilt from the sources; the sources are never rewritten to match the index. | TECH-PERSISTENT-WORLD §7 rule 3; §4; FINAL-ARCHITECTURE layer 12 |
| 4 | **Delete digest rows.** Digest rows are audit evidence of what a checkpoint contained; deleting them would erase the record of exactly the snapshots a rollback is trying to reason about. The table is cheap to keep and safe to ignore; the rows are never deleted by a rollback. | Appendix A §A.5 (rollback posture) |
| 5 | **Start on a mismatched world.** A silently wrong world is worse than a down server. | TECH-PERSISTENT-WORLD §4 |
| 6 | **Compare digests across stores.** A sim digest and a server digest are not comparable; their clock lines differ (`clock:{day_index}:{game_minutes}` vs `clock:{game_minutes}`). | Appendix A §A.2 (§3.2) |
| 7 | **Take a checkpoint mid-day.** A checkpoint is always a day-boundary state. | TECH-PERSISTENT-WORLD §2, §7 rule 4 |
| 8 | **Add a `day_index` column to PostgreSQL `world_state`.** The day is derived from `game_minutes`. | TECH-PERSISTENT-WORLD §1, §9 |
| 9 | **Store a digest as a column on `world_state`, `save_slots`, `characters`, or `economy_ledger`.** A digest belongs to a named checkpoint, not to current state or to any one row inside the snapshot. | Appendix A §A.1 |
| 10 | **Write a down-migration.** There is no down-migration for the `snapshot_metadata` change, and none may be written later. Rollback is forward: a new migration that stops the server using the table, or a later forward migration that removes it — never a `DROP TABLE` smuggled in as a rollback step, and never a delete of digest rows. | Appendix A §A.5 |
| 11 | **Claim a procedure was tested live.** No server exists in this VM; the first server test happens on the owner's PC/LAN (TECH-MULTIPLAYER §6). Every step here is design until that test passes. | TECH-MULTIPLAYER §6; TECH-PERSISTENT-WORLD §9 |

---

## 7. Open operator decisions — all resolved

No source gave a value for these when this runbook was written (Unit AW, Queue 9); each row now records its resolution. OD-8 was decided by Queue 10, Unit BD; OD-1–OD-7 by Queue 11, Units BI/BJ/BK (§§10–12). The table is kept as the record of what was open and where each decision lives.

| # | Decision | What the sources do say |
|---|---|---|
| OD-1 | **Exact operator-facing wording** for a refused load, a fallback, and a genesis start (message text, log lines, any console/UI wording). | **Resolved — §10 (Unit BI, Queue 11):** exact templates for refused load, fallback, and genesis start, plus log lines and wording rules. |
| OD-2 | **Checkpoint retention:** how many named checkpoints are kept, and when old ones are deleted. | **Resolved — §11.1 (Unit BJ, Queue 11):** newest 10 per world; on taking the 11th, delete the oldest (payload + manifest files, then the `save_slots` row; `ON DELETE CASCADE` removes the digest row with its snapshot). |
| OD-3 | **Weekly checkpoint anchor:** which in-game day of the week the periodic checkpoint is taken on. | **Resolved — §11.2 (Unit BJ, Queue 11):** the day boundary ending each in-game Sunday (Monday 00:00, `game_minutes % 10080 == 0`). |
| OD-4 | **Fallback automation:** whether stepping back through named checkpoints (§4.2) and, finally, genesis (§4.3) happen automatically or only on explicit operator confirmation at each step. | **Resolved — §11.3 (Unit BJ, Queue 11):** refusal automatic; each fallback step confirmed; genesis confirmed by typing the world name. No source authorises silently discarding a world's history. |
| OD-5 | **Audit-row destination:** which table/record the mismatch audit row is written to. | **Resolved — §10.3 (Unit BI, Queue 11):** the `audits` table, scope `snapshot_verification` (a proposed Phase 9 table, not in `schema.sql` yet); `integrity_reports` rejected, new-table rejected. |
| OD-6 | **Snapshot payload store:** where `save_slots.payload_ref` points on the server (file path vs blob key, and which store). | **Resolved — §12.1 (Unit BK, Queue 11):** absolute file path on the server host, `<snapshot_dir>/<world_id>/<save_slot_id>.payload.json`, manifest beside it. Blob key deferred to a future decision. |
| OD-7 | **Operator tooling:** how the operator lists checkpoints, takes an on-demand checkpoint, and triggers a restore on the server (no server CLI exists yet; the sim's CLI surface — `--checkpoint`, `--checkpoints`, `--restore-checkpoint`, `--duplicate-to` — is a *local* API, FINAL-ARCHITECTURE). | **Resolved — §12.2 (Unit BK, Queue 11):** local server operator CLI `nexora-server` on the server host, mirroring the sim flags 1:1 (`checkpoints`, `checkpoint`, `restore`, `duplicate`, plus an added `verify`); not a network API. |
| OD-8 | **Server-side home for the ledger idempotency key:** `data/schema.sql`'s `economy_ledger` has no `transfer_key` or `event_ref` column, although the sim's rows carry both and TECH-PERSISTENT-WORLD §2 says the server appends with "same fields, same rule". Whether the Phase 9 migration adds the columns, or idempotency lives elsewhere, is undecided. | **Resolved — Queue 10, Unit BD (TECH-PERSISTENT-WORLD §10 + Appendix B):** forward-only migration `003` adds the columns. |

---

## 8. Pre-flight checklist — server start

The operator runs this on every server start, in order. Each item cites the step that defines it.

1. [ ] List the named checkpoints for the world (newest first). — §1.2, §2.2
2. [ ] For the newest checkpoint: recompute the digest; confirm three-way agreement with `snapshot_metadata.content_digest` and the manifest file's `digest`. — §3.4 steps 1–2
3. [ ] Count check: `characters` rows vs `snapshot_metadata.population_alive`; `economy_ledger` rows vs `snapshot_metadata.ledger_rows`. — §3.4 step 3
4. [ ] Ledger gate: `ledger_sum_check` clean, conservation clean. — §3.4 step 4
5. [ ] Version gate: `save_slots.schema_version` = `world_state.schema_version` = `snapshot_metadata.schema_version`; a newer-version snapshot is shown but refused, in words. — §3.4 step 5
6. [ ] Record the outcome: `last_verified_at` + `verification_status` (`verified` / `mismatch`); never overwrite `content_digest`. — §3.4 step 6
7. [ ] If any item fails: §4 — refuse, fall back to the previous named checkpoint, genesis only as the last resort.
8. [ ] After a crash (no clean shutdown): §5 — WAL roll-forward to the last committed day, then this checklist from step 2.

---

## 9. Honest boundaries — what this runbook does and does not do

- **Design only.** No server build, no snapshot writer, no start-up check, no migration file, no netcode is shipped here. The `snapshot_metadata` table does not exist in `data/schema.sql` yet; the migration is Phase 9 work (Appendix A §A.5). Nothing in this runbook should be read as claiming a procedure has been executed against a live server.
- **No real-time server exists in this VM.** Time modes are the batch runner's honest capabilities (SESSION-10-REPORT §2.4; FINAL-ARCHITECTURE boundary 3). This runbook maps them onto a server procedure; it does not conjure a server.
- **No network API, no user accounts, no network security surface.** SESSION-10-REPORT §8 checklist item 19 stays PARTIALLY PROVEN for exactly this reason (TECH-PERSISTENT-WORLD §9; Appendix A §A.6). The server's account/security design is Phase 9 work.
- **No distributed processing, region aggregation, or DB partitioning.** SESSION-10-REPORT §6 measures the scale honestly (365 days × 242 residents; 342-resident genesis cap from the ~140-unit housing stock). This runbook does not pretend the server magically has scale architecture.
- **The UE layer remains uncompiled scaffolding for the owner's PC** (FINAL-ARCHITECTURE boundary 1; `docs/PHASE1-BUILD-SHEET.md`). Checkpoint/restore timings quoted here (save 2.90 s, restore 0.79 s, recovery 7.9 s) are headless-sim measurements, not server guarantees.
- **Still open from TECH-PERSISTENT-WORLD §9, untouched by this unit:** no network API, no user accounts, no network security surface, no distributed processing or partitioning, no real-time server in this VM. This runbook closes one open item — the operator procedure — as a design question; it does not close the programme.

---

## 10. Operator Wording & Audit Destination (AW open decisions OD-1 + OD-5 — resolved)

**Unit BI · Queue 11 · Version 1.0 · 2026-11-22**
**Status:** DESIGN ONLY. This section resolves the two open decisions the runbook left for the owner/operator: the exact operator-facing wording for a refused load, a fallback, and a genesis start (OD-1), and which table the mismatch audit row is written to (OD-5). It adds no server code and no table — the wording templates and the row shape are the deliverable. The server (Phase 9) implements against them. Where a choice is made here rather than sourced, it is labelled as this unit's decision.

**Correction to §0:** §0 says "Section 6 records the exact operator-facing wording as open decision OD-1" — that pointer is wrong. §6 is "What is NEVER done"; OD-1 lives in §7, and the wording itself lives here, in §10.

### 10.1 Wording rules — what every message must and must not do

1. **Name the world, the snapshot, and the day.** Every message names the world id, the snapshot's name, and its in-game day + `game_minutes`. An operator with two worlds on one host (TECH-PERSISTENT-WORLD §8 test 3) must never have to guess which world a refusal is about.
2. **Name the gate that failed, not a cause.** The check knows *which* gate failed (digest, counts, ledger, version) and what it measured; it does not know *why* (disk corruption, a bad write, a bug). A message states the measured disagreement and never invents a cause — "digests disagree" is the truth; "the disk is corrupt" is a guess.
3. **Name the next action.** A refusal is not a dead end: the message says what happens next (confirm the fallback, or stop) and what is preserved (the refused snapshot stays preserved for audit; its `content_digest` is untouched, §4.1).
4. **Digests: full in the log, short on the console.** Log lines carry the full 64-hex digests (machine-readable, comparable). Console/UI lines carry the first 12 hex characters plus "see log" — enough to identify which digest, short enough to read. This split is this unit's decision.
5. **Language: English.** The runbook's design text is English, and the save/load rule it cites (GDD-05 §7) says a refusal is "shown but refused, in words" — the words are the operator's working language, English, following the document's own language. No localisation is designed here (GDD-05 §11: a Bangla UI is a separate owner decision).
6. **Placeholders in this section are literal.** `<world>`, `<snapshot>`, `<day>`, `<game_minutes>`, `<gate>`, `<audit_id>` are filled from the check's own values at runtime. The templates below are the exact text, with only the placeholders varying.

### 10.2 The three messages (exact templates)

**Refused load** — console/UI, on any §3.4 failure:

```
REFUSED: world <world> will not start on snapshot '<snapshot>' (Day <day>, <game_minutes> game minutes).
<gate> check failed: <detail>. The snapshot is preserved; see audit row <audit_id>.
Next: confirm fallback to the previous named checkpoint, or stop the server.
```

`<gate>` is one of `digest`, `counts`, `ledger`, `version`. `<detail>` is the measured disagreement in the gate's own terms, for example `recomputed digest a1b2c3d4e5f6… does not match stored digest 9f8e7d6c5b4a…` (digest), `characters counted 241, snapshot records 242` (counts), `ledger_sum_check found 1 mismatch` (ledger), `snapshot schema_version 3 is newer than server version 2` (version). Log line (one line, full digests):

```
<utc> REFUSE world=<world> snapshot='<snapshot>' game_minutes=<n> gate=<gate> expected=<stored value> actual=<recomputed value> audit=<audit_id> digest_recomputed=<64-hex> digest_stored=<64-hex> digest_manifest=<64-hex>
```

**Fallback** — console/UI, when the operator confirms stepping back (§4.2, §11.3):

```
FALLBACK: starting world <world> from the previous named checkpoint '<snapshot>' (Day <day>).
Play after that checkpoint is lost. Refused snapshot '<refused>' stays preserved for audit.
```

Log line:

```
<utc> FALLBACK world=<world> from_snapshot='<refused>' to_snapshot='<snapshot>' to_game_minutes=<n> confirmed_by=<operator> audit=<audit_id>
```

**Genesis start** — console/UI, when the list is exhausted (§4.3) and the operator confirms (§11.3):

```
GENESIS: no named checkpoint passed verification for world <world>.
Starting a fresh world at Day 1, 08:00 (game_minutes 480). ALL prior progress in this world is lost.
Type the world name '<world>' to confirm:
```

The confirmation requires typing the world name — a bare "yes" cannot wipe a world by accident. Log line:

```
<utc> GENESIS world=<world> confirmed_by=<operator> reason=<no checkpoints | all checkpoints refused> audit=<audit_id>
```

**Supporting line — verified start** (not one of the three OD-1 messages, but the operator needs its positive form): on a §3.4 pass, the console records

```
START: world <world> started from checkpoint '<snapshot>' (Day <day>). Digest verified (sha256 <12-hex>…).
```

### 10.3 Audit destination — the `audits` table (OD-5 decided)

**Decision: the mismatch audit row is written to the `audits` table, scope `snapshot_verification`.** The row shape:

| Field | Value for a mismatch audit row |
|---|---|
| `audit_id` | The table's primary key, generated by the server's normal id rule |
| `scope` | `'snapshot_verification'` (a new scope value; the existing sim scope is `'government_accounts'`) |
| `month_index` | `game_minutes // 43200` — the same rule `audit_government()` uses (`tools/sim/integrity.py`) |
| `discrepancies` | JSON list, one object per failed check: `{snapshot, gate, expected, actual}` — `gate` ∈ `digest` \| `counts` \| `ledger` \| `version` |
| `discrepancy_count` | Length of `discrepancies` |
| `result` | `'mismatch'` for digest/count/ledger failures; `'version_refusal'` for a newer-version snapshot (§4.4: a version refusal is recorded as such, not as corruption) |
| `integrity_index` | `NULL` — the index is the government-accounts integrity measure (Session 05); it does not apply to a snapshot check, and no number is invented for it |
| `auditor_character_id` | `NULL` — the auditor is the server process, not a citizen; no office holds this check (the Auditor General audits government accounts, not snapshots) |
| `game_minutes` | Current game minutes at the check |

**Table status, stated plainly:** `audits` does **not** exist in `data/schema.sql` today (checked: 19 `CREATE TABLE` statements, no `audits`, no `integrity_reports`, no `snapshot_metadata`). The table arrives with the Phase 9 migration, on the same pattern as `snapshot_metadata` (TECH-PERSISTENT-WORLD Appendix A §A.5): the row shape is specified here, the table itself is Phase 9 work, and this unit does not add it to `schema.sql`. The sim's SQLite `audits` table (`tools/sim/persistence.py`) is the shape this decision mirrors — same columns, same `scope`/`discrepancies`/`result` vocabulary — so the server row and the sim row are the same object in different stores.

**Rejected alternative — `integrity_reports`.** That table holds citizen whistleblower reports about citizens (`reporter_character_id`, `subject_character_id`, `allegation`, `status` — `tools/sim/integrity.py` `file_report()`). A digest mismatch is not an allegation against anyone, has no reporter and no subject citizen, and its outcome is not "unsubstantiated" or "disciplined" — the shape does not fit, and forcing it would record a machine verification failure as a citizen report. Rejected.

**Rejected alternative — a new server table.** A dedicated `snapshot_audits` table would need its own migration for no gain: `audits` is already the audit table, its `scope` field exists precisely to separate audit kinds, and the mismatch row needs no column `audits` lacks. Rejected.

**What is written alongside the row (unchanged):** the §3.4 step 6 outcome record — `snapshot_metadata.last_verified_at` + `verification_status` (`verified` / `mismatch`) — is still written, and `content_digest` is still never overwritten. The `audits` row is the audit trail; the metadata row is the snapshot's own status. Both are written on every verification; neither replaces the other.

**OD-1 and OD-5 are resolved by this section** — the wording templates (§10.2) and the audit destination (§10.3) now exist — with the labelled decisions kept: the digest split (§10.1 rule 4), the typed-name genesis confirmation (§10.2), and the `NULL` auditor/index (§10.3). The `audits` table itself remains Phase 9 migration work.

*End of TECH-CHECKPOINT-RUNBOOK §10 — Unit BI, Queue 11.*

---

## 11. Checkpoint Retention, Anchor & Fallback Automation (AW open decisions OD-2 + OD-3 + OD-4 — resolved)

**Unit BJ · Queue 11 · Version 1.0 · 2026-11-22**
**Status:** DESIGN ONLY. This section resolves the three open decisions the runbook left for the owner/operator: how many named checkpoints are kept and when old ones are deleted (OD-2), which in-game day of the week the periodic checkpoint is taken on (OD-3), and whether the fallback walk and genesis happen automatically or only on explicit operator confirmation (OD-4). It adds no server code — the three decisions are the deliverable. The server (Phase 9) implements against them. Each number below is this unit's decision, labelled as such, with its rationale stated so the owner/operator can revise it as a config change, not a redesign.

**Correction to §1.2:** §1.2 says "The anchor day within the week is not fixed by any source — see open decision OD-3 (§6)". That pointer is wrong twice over: OD-3 lives in §7, not §6, and it is resolved here, in §11.

### 11.1 Retention — keep the newest 10 named checkpoints (OD-2 decided)

**Decision: keep the newest 10 named checkpoints per world; on taking the 11th, delete the oldest.** The count is per world, and every named checkpoint counts — weekly, clean-shutdown, and on-demand alike, because all three are named snapshots (§1.2) and the fallback chain (§4) does not distinguish them. Genesis resets the count to 0.

**Why 10.** The weekly cadence (§1.2) makes 10 checkpoints ≈ 10 in-game weeks ≈ 2.5 in-game months of fallback depth — deep enough that a corruption discovered a month late still has a clean checkpoint to fall back to, shallow enough to bound the disk: each snapshot is a full world copy (Session 10 endurance: the world file reaches 213.6 MB at 365 days), so 10 bounds one world at roughly 2 GB of snapshots. The number is a config value the operator may revise; the rule is the shape (newest N, delete the oldest on overflow), and N = 10 is this unit's decision, not a sourced fact.

**How deletion works (the §6 rule 4 constraint).** Deletion must respect §6 rule 4: digest rows are audit evidence — a deleted snapshot must not leave an orphaned digest behind. The deletion procedure is one step, in this order:

1. Delete the payload file (`save_slots.payload_ref` — §12.1) and the manifest file beside it.
2. Delete the `save_slots` row. `ON DELETE CASCADE` (TECH-PERSISTENT-WORLD Appendix A §A.3: `snapshot_metadata.save_slot_id … ON DELETE CASCADE`) removes the `snapshot_metadata` row with it — the digest row goes *with* its snapshot, which is the sanctioned path (§7 OD-2): it is not orphaned, and it is not deleted by a rollback (§6 rule 4 governs rollbacks; retention deletion is a different act, and it deletes the digest row only together with the snapshot it describes).
3. Verify: list the world's checkpoints (§12.2) and confirm the deleted name is gone and no orphaned row or file remains. A row without a manifest is invisible to the loader (§2.4), and files without a row are ignored, so either order of steps 1–2 is safe — but the procedure is always both, never one without the other. A half-deleted snapshot (files gone, row left, or row gone, files left) is cleanup, never a load candidate.

**What retention never deletes.** It never deletes the `audits` rows (§10.3) that record past verifications — those are the audit trail of deleted snapshots, and they outlive the snapshots they describe. It never deletes a snapshot the operator has explicitly held (no hold mechanism is designed here — a hold is a future operator decision, not smuggled in as a flag).

### 11.2 Weekly anchor — the day boundary ending Sunday (OD-3 decided)

**Decision: the weekly checkpoint is taken at the day boundary ending each in-game Sunday — when the clock write moves `game_minutes` to a multiple of 7 × 1440 (Monday 00:00).** Day 1 is a Monday (`tools/sim/scheduler.py`: `weekday = day_index % 7`, Day 1 index 0 is Monday, Friday = 4), so the in-game week runs Monday–Sunday and the anchor captures the completed week at the moment it ends.

**Why Monday 00:00.** It is unambiguous (a multiple of 7 days from genesis, no calendar lookup), and it avoids the district's weekend-variant days: Friday and Saturday carry schedule variants (`scheduler.py` Friday/Saturday bends), so a checkpoint anchored on either would capture a variant day as the week's representative. Monday is the week's first ordinary day, and the boundary that ends Sunday is a day boundary like every other (§1.1). The check itself is arithmetic on the clock write the server already performs (§1.3): after the once-per-day write, if `game_minutes % 10080 == 0`, take the weekly checkpoint.

### 11.3 Fallback automation — refuse automatically, fall back and genesis only on confirmation (OD-4 decided)

**Decision: the refusal is automatic; every step back is confirmed; genesis is confirmed by name.**

| Step | Automatic or confirmed | Rule |
|---|---|---|
| Refuse the snapshot (§4.1) | **Automatic** | The §3.4 gate refuses by itself — the server simply does not start on that snapshot. No confirmation is needed to *not* start a wrong world; asking would invite starting it. The refusal, the `verification_status` update, and the `audits` row (§10.3) are all written automatically. |
| Fall back to the previous named checkpoint (§4.2) | **Explicit operator confirmation, per step** | Each step back discards real play (everything after that checkpoint is gone — §4.2), so the operator confirms each one, seeing the checkpoint's name and day (§10.2 fallback message). The operator may stop the walk at any step and leave the server down rather than fall further back — a down server is honest, a silently discarded month is not. |
| Genesis (§4.3) | **Explicit operator confirmation, typing the world name** | The §10.2 genesis message requires the operator to type the world name. No source authorises silently discarding a world's history (§4.3, §7 OD-4), and a bare "yes" cannot wipe a world by accident. |

**Rationale.** The chain order is fixed (§4); only the confirmation was undecided. The split follows the operator's law (§0): a mismatch is refused, never repaired — refusal needs no permission — but *discarding history* needs a human to own it, at each step, because each step is a loss the operator cannot undo. A newer-version refusal (§4.4) follows the same rule: it is shown, recorded as `version_refusal` (§10.3), and the fallback from it is confirmed like any other.

**OD-2, OD-3, and OD-4 are resolved by this section** — the retention count and deletion procedure (§11.1), the weekly anchor (§11.2), and the confirmation split (§11.3) now exist — with each number labelled as this unit's decision and revisable as config. The §7 table rows for OD-2/OD-3/OD-4 point here.

*End of TECH-CHECKPOINT-RUNBOOK §11 — Unit BJ, Queue 11.*

---

## 12. Snapshot Payload Store & Operator Tooling (AW open decisions OD-6 + OD-7 — resolved)

**Unit BK · Queue 11 · Version 1.0 · 2026-11-22**
**Status:** DESIGN ONLY. This section resolves the two open decisions the runbook left for the owner/operator: where `save_slots.payload_ref` points on the server (OD-6), and how the operator lists checkpoints, takes an on-demand checkpoint, and triggers a restore on the server (OD-7). It adds no server code and no netcode — the store decision and the CLI surface are the deliverable. The server (Phase 9) implements against them.

**Correction to the Queue 11 brief:** the brief cited "TECH-PERSISTENT-WORLD §11 note" for the payload store. No §11 exists in that document — its numbered sections run §1–§10, then Appendices A and B. The payload-store note is **§3** (the manifest-mapping table: `checkpoint_db` → `save_slots.payload_ref`, "file path / blob key") and Appendix A §A.4. This section decides on §3's terms.

### 12.1 Payload store — an absolute file path on the server host (OD-6 decided)

**Decision: `save_slots.payload_ref` holds an absolute file path on the server host, under the server's snapshot directory:**

```
<snapshot_dir>/<world_id>/<save_slot_id>.payload.json
```

The manifest file lives beside it, same stem:

```
<snapshot_dir>/<world_id>/<save_slot_id>.manifest.json
```

The file name uses the `save_slot_id` (UUID, stable, unique per snapshot), not the human checkpoint name (`slot_label`) — labels can repeat and collide, ids cannot. The payload is the society: every schema table by name, as JSON rows (`TablePayloads`, TECH-SAVE-SYSTEM §2), exactly as §3 defines it. The manifest is the same JSON manifest the sim writes beside its copied world file (§2.1), with the server fields of §2.2.

**Why a file path.** The Phase 9 v1 server runs on the owner's PC/LAN (TECH-MULTIPLAYER §6: first server test on the owner's PC/LAN), and no blob store exists anywhere in the design: no hosting provider, region, or budget is chosen (TECH-MULTIPLAYER §5, §7), and a blob key would require a blob store that has not been decided, priced, or built. A file path works on the LAN server today, with the server's own disk, and the column keeps the blob-key option open — a future decision changes the *value format* (`payload_ref` becomes a key), not the column. The snapshot directory itself (`<snapshot_dir>`) is a server config value, set at deploy; this section fixes the layout inside it, not the root.

**What the decision does not do.** It does not choose a hosting provider, a backup service, or a replication scheme — those are owner money decisions, deferred honestly (TECH-MULTIPLAYER §5). It does not change `payload_ref`'s column (`data/schema.sql`: `payload_ref TEXT — local file path / blob key for the serialised world`); the column already allows either value, and this decision picks one of the two it names.

### 12.2 Operator tooling — the server operator CLI (OD-7 decided)

**Decision: the operator works through a local server operator CLI, `nexora-server`, run on the server host.** It is a local tool, not a network API: TECH-MULTIPLAYER §7 specifies no netcode, and the server's network API is Phase 9 implementation work. Host access is the authorisation — the CLI runs where the server runs, and remote operation waits for the network API. The CLI mirrors the sim's local surface (`tools/sim/__main__.py`: `--checkpoint`, `--checkpoints`, `--restore-checkpoint`, `--duplicate-to`, `--from-checkpoint`) 1:1 in name and semantics, so an operator who learned the sim's flags already knows the server's commands.

| Command | Mirrors (sim) | What it does |
|---|---|---|
| `nexora-server checkpoints --world <id>` | `--checkpoints` | Lists the world's named checkpoints, newest first: name (`slot_label`), day (`game_minutes` derived), `verification_status`, `schema_version`. This is the §8 pre-flight step 1. |
| `nexora-server checkpoint --world <id> --name <name>` | `--checkpoint` | Takes an on-demand named checkpoint **at a day boundary only** (§1.1). Mid-day, it refuses with the §10.2 wording (a refusal, not a partial checkpoint). The new checkpoint counts toward the §11.1 retention of 10. |
| `nexora-server restore --world <id> --checkpoint <name>` | `--restore-checkpoint` | Restores the named checkpoint as the live state. **Before loading, it takes a safety snapshot of the current live state** (named `pre-restore-<name>`, decided here — so the restore is reversible and the pre-restore world is not silently discarded), then runs the full §3.4 verification on the named snapshot, then loads it only on explicit operator confirmation (§11.3). A failed verification refuses with the §10.2 wording and loads nothing. |
| `nexora-server duplicate --world <id> --from-checkpoint <name> --to-world <new-id>` | `--duplicate-to` + `--from-checkpoint` | Duplicates the named checkpoint to a new world id. **Never into the live world's slot** (TECH-PERSISTENT-WORLD §4): the duplicate gets a fresh registry entry and its own digest baseline, and the two worlds diverge honestly from there. |
| `nexora-server verify --world <id> --checkpoint <name>` | — (added here) | Runs the §3.4 verification on a named snapshot **without starting or loading anything**: recompute, three-way digest agreement, counts, ledger gate, version gate; writes the `audits` row (§10.3) and the metadata outcome (§3.4 step 6). The sim has no standalone verify flag — its verification lives inside restore — so this command is added here, labelled as such. It is the operator's way to check a snapshot before deciding to restore it. |

**What the CLI is not.** Not a network API (TECH-MULTIPLAYER §7: no netcode specified). Not remote: it runs on the server host, and no account, token, or network security surface is designed here (SESSION-10-REPORT §8 item 19 stays PARTIALLY PROVEN for exactly this reason). Not a game UI: it is the operator's tool, and the runbook specifies no screens or buttons anywhere (§0). The §8 pre-flight checklist is the procedure these commands serve: list (§8 step 1), verify (§8 steps 2–6), restore (§8 step 7), crash recovery (§8 step 8, via the server restart + verify path).

**OD-6 and OD-7 are resolved by this section** — the payload store (§12.1) and the operator CLI surface (§12.2) now exist — with the labelled decisions kept: the file-path format and layout, the `pre-restore-` safety snapshot, and the added `verify` command. The §7 table rows for OD-6/OD-7 point here. With OD-1 through OD-7 all resolved except OD-8 (decided by Queue 10, Unit BD — TECH-PERSISTENT-WORLD §10 + Appendix B), the runbook's open-decision table is now empty: every decision the runbook recorded has a resolution, and the remaining work is Phase 9 implementation, not design.

*End of TECH-CHECKPOINT-RUNBOOK §12 — Unit BK, Queue 11.*

*End of TECH-CHECKPOINT-RUNBOOK v1.0 — Unit AW, Queue 9 + Queue 10 §10 (Unit BD) + Queue 11 §§10–12 (Units BI, BJ, BK).*
