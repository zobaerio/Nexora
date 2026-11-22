"""Session 10 — World registry, checkpoints, duplication.

A world is one SQLite file (Store's contract since Session 01:
the file IS the save). This module formalises the operations
around world files without changing that contract:

- **World registry**: a JSON file (path chosen by the operator;
  the CLI default is ./worlds.json) listing registered worlds —
  world id, name, path, seed. Registration is bookkeeping only:
  worlds stay independent files, and the registry holds no
  simulation state, so a lost registry loses nothing but the
  list.
- **Checkpoints**: a consistent snapshot of a world file made
  with SQLite's backup API (safe against a world whose last
  process died mid-day: the copy contains exactly the committed
  days), plus a JSON manifest — sim day, population, ledger
  row count, the ledger reconciliation verdict on the copy,
  schema version and the sim code version. Restoring a
  checkpoint is a file operation: it replaces the world file
  with the snapshot (any -wal/-shm sidecars of the target are
  removed first). It must only be run while no simulation
  process holds the world open — the CLI context guarantees
  that; the engine never calls it.
- **Duplication**: a new world file copied from a checkpoint
  or from the world's current state — the scenario-branching
  primitive. The copy is a fully independent world: the two
  files share history up to the copy point and nothing after.

Isolation is structural (separate files, separate connections)
and is proven by test: mutating one world leaves a second
world's population and ledger byte-identical in digest.
"""
import hashlib
import json
import os
import shutil
import sqlite3
from datetime import datetime, timezone

CODE_VERSION = "s10.1"


def _ro_connect(path):
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def world_info(db_path):
    """Read-only facts about a world file (never opens it for
    writing, so it is safe on a live or checkpoint file)."""
    info = {"path": os.path.abspath(db_path),
            "exists": os.path.exists(db_path)}
    if not info["exists"]:
        return info
    info["size_bytes"] = os.path.getsize(db_path)
    conn = _ro_connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        w = conn.execute("SELECT * FROM world_state WHERE id = 1"
                         ).fetchone()
        if w is None:
            info["error"] = "no world_state row — not a sim world"
            return info
        info.update({
            "seed": w["sim_seed"],
            "day_index": w["day_index"],
            "game_minutes": w["game_minutes"],
            "schema_version": w["schema_version"],
            "population_generated": bool(w["population_generated"]),
            "population_alive": conn.execute(
                "SELECT COUNT(*) FROM characters WHERE is_system = 0"
                " AND died_at_game_minutes IS NULL").fetchone()[0],
            "population_total": conn.execute(
                "SELECT COUNT(*) FROM characters WHERE is_system = 0"
                ).fetchone()[0],
            "ledger_rows": conn.execute(
                "SELECT COUNT(*) FROM economy_ledger").fetchone()[0],
            "registry_events": conn.execute(
                "SELECT COUNT(*) FROM world_events").fetchone()[0]
            if conn.execute("SELECT 1 FROM sqlite_master WHERE"
                            " type = 'table' AND name ="
                            " 'world_events'").fetchone() else 0,
        })
    finally:
        conn.close()
    return info


def world_digest(db_path):
    """A content digest over the facts isolation must preserve:
    every character's id/balance/death, the ledger's size and
    sum, and the world clock. Two worlds with equal digests are
    in identical population + ledger state."""
    conn = _ro_connect(db_path)
    try:
        h = hashlib.sha256()
        for row in conn.execute(
                "SELECT character_id, balance_cached,"
                " died_at_game_minutes FROM characters"
                " ORDER BY character_id"):
            h.update(repr(tuple(row)).encode())
        n, s = conn.execute("SELECT COUNT(*), COALESCE(SUM(amount),"
                            " 0) FROM economy_ledger").fetchone()
        h.update(f"ledger:{n}:{s}".encode())
        w = conn.execute("SELECT day_index, game_minutes FROM"
                         " world_state WHERE id = 1").fetchone()
        h.update(f"clock:{w[0]}:{w[1]}".encode())
        return h.hexdigest()
    finally:
        conn.close()


# -- registry ---------------------------------------------------------

def _load_registry(registry_path):
    if os.path.exists(registry_path):
        with open(registry_path) as f:
            return json.load(f)
    return {"worlds": []}


def _save_registry(registry_path, registry):
    with open(registry_path, "w") as f:
        json.dump(registry, f, indent=1, sort_keys=True)


def register_world(registry_path, db_path, name=None):
    """Add a world file to the registry (idempotent by absolute
    path). Returns the registry entry."""
    registry = _load_registry(registry_path)
    apath = os.path.abspath(db_path)
    for entry in registry["worlds"]:
        if entry["path"] == apath:
            return entry
    info = world_info(db_path)
    entry = {"world_id": f"WORLD-{len(registry['worlds']) + 1:04d}",
             "name": name or os.path.splitext(
                 os.path.basename(db_path))[0],
             "path": apath,
             "seed": info.get("seed"),
             "registered_utc": datetime.now(timezone.utc).isoformat(),
             "code_version": CODE_VERSION}
    registry["worlds"].append(entry)
    _save_registry(registry_path, registry)
    return entry


def list_worlds(registry_path):
    """Registry entries, each merged with the world's live
    read-only info (a missing file is reported, not hidden)."""
    registry = _load_registry(registry_path)
    out = []
    for entry in registry["worlds"]:
        merged = dict(entry)
        merged["info"] = world_info(entry["path"])
        out.append(merged)
    return {"registry": os.path.abspath(registry_path),
            "worlds": out}


# -- checkpoints --------------------------------------------------------

def checkpoint_dir(db_path):
    return db_path + ".checkpoints"


def _manifest_path(db_path, name):
    return os.path.join(checkpoint_dir(db_path),
                        f"{name}.manifest.json")


def create_checkpoint(db_path, name):
    """Snapshot the world file (SQLite backup API — the copy
    holds exactly the committed state) and write its manifest.
    Returns the manifest."""
    from .persistence import Store  # deferred: Store opens files
    os.makedirs(checkpoint_dir(db_path), exist_ok=True)
    target = os.path.join(checkpoint_dir(db_path), f"{name}.db")
    src = _ro_connect(db_path)
    dst = sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    # Verify + measure the copy the way a resume would see it.
    store = Store(target)
    try:
        world = store.world()
        manifest = {
            "name": name,
            "world_db": os.path.abspath(db_path),
            "checkpoint_db": os.path.abspath(target),
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "code_version": CODE_VERSION,
            "schema_version": world["schema_version"],
            "seed": world["sim_seed"],
            "day_index": world["day_index"],
            "game_minutes": world["game_minutes"],
            "population_alive": store.row(
                "SELECT COUNT(*) AS n FROM characters WHERE"
                " is_system = 0 AND died_at_game_minutes IS NULL"
            )["n"],
            "ledger_rows": store.row(
                "SELECT COUNT(*) AS n FROM economy_ledger")["n"],
            "ledger_reconciled": store.ledger_sum_check() == [],
            "digest": world_digest(target),
        }
    finally:
        store.close()
    with open(_manifest_path(db_path, name), "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    return manifest


def list_checkpoints(db_path):
    out = []
    cdir = checkpoint_dir(db_path)
    if os.path.isdir(cdir):
        for fname in sorted(os.listdir(cdir)):
            if fname.endswith(".manifest.json"):
                with open(os.path.join(cdir, fname)) as f:
                    out.append(json.load(f))
    return {"world_db": os.path.abspath(db_path),
            "checkpoints": out}


def restore_checkpoint(db_path, name):
    """Replace the world file with a checkpoint snapshot. File
    operation — no simulation may hold the world open."""
    manifest_file = _manifest_path(db_path, name)
    if not os.path.exists(manifest_file):
        raise FileNotFoundError(f"no checkpoint named {name}")
    with open(manifest_file) as f:
        manifest = json.load(f)
    src = manifest["checkpoint_db"]
    for suffix in ("-wal", "-shm"):
        sidecar = db_path + suffix
        if os.path.exists(sidecar):
            os.remove(sidecar)
    shutil.copyfile(src, db_path)
    return manifest


def duplicate_world(db_path, new_path, from_checkpoint=None):
    """Create an independent world file at new_path — from a
    named checkpoint when given, else from the world's current
    committed state (backup API). Returns the new world's
    info."""
    if os.path.exists(new_path):
        raise FileExistsError(f"{new_path} already exists")
    if from_checkpoint is not None:
        manifest_file = _manifest_path(db_path, from_checkpoint)
        if not os.path.exists(manifest_file):
            raise FileNotFoundError(
                f"no checkpoint named {from_checkpoint}")
        with open(manifest_file) as f:
            src_path = json.load(f)["checkpoint_db"]
        shutil.copyfile(src_path, new_path)
    else:
        src = _ro_connect(db_path)
        dst = sqlite3.connect(new_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
    return world_info(new_path)
