# NEXORA — Tech Note: Phase 9 Checkpoint & Recovery Runbook

**Unit AW · Queue 9 · Version 1.0 · 2026-11-22**
**Code:** none — design only. No server build, no netcode, no snapshot code, no start-up check exists yet; nothing here claims a procedure in this document has ever been executed against a live server.
**Parent documents:** `docs/TECH-PERSISTENT-WORLD.md` (§2 per-tick vs per-checkpoint, §3 manifest mapping, §4 digest verification, §9; Appendix A — snapshot digest metadata) · `docs/TECH-MULTIPLAYER.md` (Phase 9 dedicated-server design, §2 session shape, §4 server authority, §6 test plan) · `docs/SESSION-10-REPORT.md` (§2.2–2.4 world registry, named checkpoints, time modes; §6 endurance/recovery benchmarks; §8 checklist items 15–17, 20) · `docs/FINAL-ARCHITECTURE.md` (layers 1, 12, 13 — world, event & time, persistence) · `data/schema.sql` (`save_slots`, `world_state`, `characters`, `economy_ledger`) · `docs/TECH-SAVE-SYSTEM.md` §2 (single-player save shape the server snapshot extends) · `tools/sim/worlds.py` (`world_digest()`, `create_checkpoint()` — the proven digest and manifest this runbook turns into procedure).
**Status:** DESIGN ONLY — an operator procedure for Phase 9, built from the proven headless system. The left-hand side of every step is measured (Session 10); the right-hand side is what the operator does when the Phase 9 server exists. First server test happens on the owner's PC/LAN (TECH-MULTIPLAYER §6).

> **Operator's law:** the digest guards the truth, not the picture (TECH-PERSISTENT-WORLD §4). A checkpoint is a day-boundary state, never a partial day. A mismatch is refused, never repaired. When in doubt, fall back — a silently wrong world is worse than a down server (TECH-PERSISTENT-WORLD §4).

## 0. How to read this runbook

- **"The sim"** means the proven headless simulation (Session 10, `tools/sim/`). **"The server"** means the Phase 9 dedicated server (TECH-MULTIPLAYER §1: headless UE server build; owner's PC for LAN tests, a small hosted instance later). Where a step cites a sim behaviour, the citation is the proof; where it prescribes server behaviour, the citation is the design it implements.
- **No user interface is specified anywhere in this runbook.** The sources define states and outcomes ("refuse to start", "fall back", "write an audit row"), not screens, buttons, or literal message text. Section 6 records the exact operator-facing wording as open decision OD-1 rather than inventing it.
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

The anchor day within the week is not fixed by any source — see open decision OD-3 (§6).

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

**Schema discrepancy found while verifying this runbook (§1.3, "Every transfer" row):** the sim's `Store.transfer` rows carry a reason code, an optional `event_ref`, and an idempotency `transfer_key`, and TECH-PERSISTENT-WORLD §2 says the server appends with "same fields, same rule" — but `data/schema.sql`'s `economy_ledger` as drafted lists `reason_code` and no `transfer_key` or `event_ref` column (columns: `ledger_id`, `from_character_id`, `to_character_id`, `from_business_id`, `to_business_id`, `amount`, `reason_code`, `related_property_id`, `related_business_id`, `note`, `game_minutes`, `created_at`). The server-side home for the idempotency key is therefore undecided; see open decision OD-8 (§7). This runbook does not claim the columns exist in `schema.sql`.

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
| **What the operator sees** | The load is refused for that snapshot. The refusal is recorded: `snapshot_metadata.verification_status` is set to `'mismatch'` with `last_verified_at` updated, and an audit row is written (Appendix A §A.5 step 5). The stored `content_digest` is left untouched — the mismatch is preserved as evidence. No literal message text is defined by any source; exact wording is open decision OD-1 (§6). |
| **What is never done here** | No repair-in-place of the ledger, no rewrite of history rows to match a digest, no "fix" of a stored digest to match a changed payload, no silent start on the wrong world, no reconstruction of a lost snapshot from its digest (a hash cannot rebuild the society it summarises) — Appendix A §A.6. |

### 4.2 Step 2 — Fall back to the previous named checkpoint

| | |
|---|---|
| **Trigger** | Step 1 refused the newest named checkpoint. |
| **Action** | Load the **previous named checkpoint** — the next-newest snapshot in the named-checkpoint list — and run the full §3.4 verification on it from scratch (recompute, three-way digest agreement, counts, ledger gate, version gate). |
| **What the operator sees** | The server starts from the previous named checkpoint, at that checkpoint's day (its `game_minutes`, day derived). Play that happened after that checkpoint is gone — that is the honest cost of the fallback, and why checkpoints are taken every in-game week and on clean shutdown (§1.2). The fallback and the refused snapshot are both on the audit record. |
| **If the previous checkpoint also fails** | Repeat step 2 with the next-older named checkpoint, in order, until one passes §3.4 or the list is exhausted. Each failure is recorded the same way (`verification_status` `'mismatch'`, audit row, digest untouched). Whether this walk is automatic or needs the operator to confirm each step is open decision OD-4 (§6). |

### 4.3 Step 3 — Genesis (the list is exhausted)

| | |
|---|---|
| **Trigger** | Every named checkpoint has been refused, or no named checkpoint exists. |
| **Action** | Start a **new world from genesis** — a fresh world built from the world's registry entry (name, seed, code version; SESSION-10-REPORT §2.2: registry entries carry world id `WORLD-0001…`, name, path, seed, config/code version, registered time). Genesis is a new world, not a repair of the lost one: nothing from the refused snapshots is carried over, because nothing in them is trusted. |
| **What the operator sees** | The server starts a fresh world at Day 1, 08:00 (`game_minutes` 480). All prior progress is lost. This is the last resort by design — it exists so the server can always start honestly, never so a broken world can be quietly replaced. |
| **Operator decision required** | Whether genesis proceeds automatically or only on explicit operator confirmation is open decision OD-4 (§6). No source authorises silently discarding a world's history. |

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

## 7. Open operator decisions

No source gives a value for these. They are recorded here as decisions for the owner/operator, **not** invented by this unit.

| # | Decision | What the sources do say |
|---|---|---|
| OD-1 | **Exact operator-facing wording** for a refused load, a fallback, and a genesis start (message text, log lines, any console/UI wording). | The sources define states and outcomes only: "refuse to start on that snapshot", "fall back to the previous named checkpoint", "write an audit row" (Appendix A §A.5 step 5). No literal message text exists anywhere. |
| OD-2 | **Checkpoint retention:** how many named checkpoints are kept, and when old ones are deleted. | Checkpoints are taken every in-game week + on clean shutdown + on demand (TECH-PERSISTENT-WORLD §2). No retention count or deletion rule is stated. Deletion, when decided, must respect §6 rule 4 (digest rows are audit evidence — a deleted snapshot must not leave an orphaned digest behind; `ON DELETE CASCADE` in Appendix A §A.3 handles the row, but the retention policy itself is undecided). |
| OD-3 | **Weekly checkpoint anchor:** which in-game day of the week the periodic checkpoint is taken on. | "Every in-game week" (TECH-PERSISTENT-WORLD §2). The anchor day within the week is unspecified. |
| OD-4 | **Fallback automation:** whether stepping back through named checkpoints (§4.2) and, finally, genesis (§4.3) happen automatically or only on explicit operator confirmation at each step. | The chain order is fixed (§4); the sources do not say who confirms each step. No source authorises silently discarding a world's history. |
| OD-5 | **Audit-row destination:** which table/record the mismatch audit row is written to. | Appendix A §A.5 step 5 says "write an audit row" without naming the table. The sim has `audits` (FINAL-ARCHITECTURE layer 15, S05 monthly integrity audits) and `integrity_reports`, but no source maps the server's mismatch audit row to either. |
| OD-6 | **Snapshot payload store:** where `save_slots.payload_ref` points on the server (file path vs blob key, and which store). | `payload_ref` is defined as "local file path / blob key for the serialised world" (`data/schema.sql`); the choice between them is not made. |
| OD-7 | **Operator tooling:** how the operator lists checkpoints, takes an on-demand checkpoint, and triggers a restore on the server (no server CLI exists yet; the sim's CLI surface — `--checkpoint`, `--checkpoints`, `--restore-checkpoint`, `--duplicate-to` — is a *local* API, FINAL-ARCHITECTURE). | TECH-MULTIPLAYER §7: no netcode is specified; the server's network API is Phase 9 implementation work. |
| OD-8 | **Server-side home for the ledger idempotency key:** `data/schema.sql`'s `economy_ledger` has no `transfer_key` or `event_ref` column, although the sim's rows carry both and TECH-PERSISTENT-WORLD §2 says the server appends with "same fields, same rule". Whether the Phase 9 migration adds the columns, or idempotency lives elsewhere, is undecided. | TECH-PERSISTENT-WORLD §2, §7 rule 2; `data/schema.sql` `economy_ledger` column list; TECH-MULTIPLAYER §6 tests 3/4 depend on the key existing. |

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

*End of TECH-CHECKPOINT-RUNBOOK v1.0 — Unit AW, Queue 9.*
