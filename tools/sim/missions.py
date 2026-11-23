"""Queue 17 Unit DL — Mission System Writer Implementation
(GDD-04 §3.6, Unit DG design).

Implements the sim-side mission writer DG specified: the mission
system is the only writer of ``mission_progress`` rows. This module
is the writer — it creates rows, moves them through the statuses,
and sets the ``progress`` keys. Dialogue writes only the two effects
GDD-15 §13.4 allows (accept, mission_complete) and this module is
what those effects call; dialogue never writes ``failed`` or
``available``.

Status transitions (DG §3.6 — no skips):
  (no row) -> available  (mission becomes available)
  available -> active    (accept)
  active -> completed    (objectives verified, then complete)
  active -> failed       (deadline missed, or abandon)
  failed -> available    (retry after 7 in-game days, fresh window)
  available -> failed / available -> completed: never.

The ``progress`` JSON shape is exactly five keys (GDD-15 §13.3 +
GDD-04 §3.2): available_at_game_minutes, accepted_at_game_minutes,
objectives_complete, completed_at_game_minutes, abandoned. No other
key is written here.

Mission 1.4 "The River at Dusk" (GDD-04 §2) is the one mission whose
completion condition this unit implements, because DG specified it
and DA's photo-mode gate reads its row: both objectives verified
against world state while the row is still ``active`` — (1) the
player's zone is ``d1_riverfront`` at a game minute in the sunset
window [sunset_min, 20:00), sunset from
``environment.daylight(data, day_index)[1]``; (2) the player is
present at the riverfront tea stall anchor
``anchor_tea_stall_riverfront_1``. Completing 1.4 pays the sourced
reward: the memory event "First evening in Rupsha" (a life event;
no episodic-memory weight is sourced for it, so none is invented)
and the unlocks "Promenade leisure anchor" and "Photo mode" — photo
mode IS this row reaching ``completed`` (DA's gate reads exactly
that), and the promenade anchor already exists in the blockout data,
so no separate unlock store is written. Credit/reputation payout for
other missions is NOT wired here: 1.4 carries no credits and no
reputation, and paying other missions' rewards is the Phase 6
mission system's reward step, not this writer.

Favour instances are rows too (DG §3.6): the generator asks this
module to create the row (``side:<type>:<giver>:<minute>``), and the
same transitions move it. Verification for the two favour kinds
whose predicates exist in the sim is implemented here — the lost-item
favour via DF's ``favour_objective_complete()``, the discovery favour
via the ``discovery_progress`` row; the other kinds have no
verification predicate in the sim yet, so their verification returns
False and is recorded, not faked. Note the key carries only the §3
type: "find a lost item" is a subtype *within* Favours (GDD-04 §3),
not a type of its own, so the caller supplies the subtype it
generated — the key alone cannot say which kind of favour a
``favours`` row is.
"""
import json

# GDD-04 §2: the riverfront tea stall anchor for mission 1.4 (the one
# tea stall in d1_riverfront, data/district1-blockout.json).
RIVERFRONT_TEA_STALL_ANCHOR = "anchor_tea_stall_riverfront_1"
RIVERFRONT_ZONE = "d1_riverfront"
# TECH-CLOCK-WEATHER §1: Evening ends at 20:00 (1200 minutes).
EVENING_END_MINUTE = 20 * 60
# GDD-04 §1: a failed mission can be retried after 7 in-game days.
RETRY_WAIT_MINUTES = 7 * 1440

# The five progress keys (GDD-15 §13.3 + GDD-04 §3.2). No other key
# may be written by this module.
PROGRESS_KEYS = ("available_at_game_minutes",
                 "accepted_at_game_minutes", "objectives_complete",
                 "completed_at_game_minutes", "abandoned")

# The 1.4 reward (data/missions.json, quoted verbatim): the memory
# event is paid as a life event by complete_mission; the unlocks
# need no row (see the module note).
MISSION_1_4_MEMORY_EVENT = "first_evening_in_rupsha"
MISSION_1_4_MEMORY_TEXT = "First evening in Rupsha"


def _progress(row):
    """The parsed progress dict of a mission_progress row."""
    try:
        return json.loads(row["progress"] or "{}")
    except ValueError:
        return {}


def _write(store, character_id, mission_id, status, progress,
           game_minutes):
    store.execute(
        "UPDATE mission_progress SET status = ?, progress = ?,"
        " updated_at_game_minutes = ? WHERE character_id = ?"
        " AND mission_id = ?",
        (status, json.dumps(progress), game_minutes, character_id,
         mission_id))


def get_row(store, character_id, mission_id):
    """The mission_progress row for (character, mission), or None
    (no row = the `not_started` state, GDD-15 §13.2)."""
    return store.row(
        "SELECT * FROM mission_progress WHERE character_id = ?"
        " AND mission_id = ?", (character_id, mission_id))


def get_status(store, character_id, mission_id):
    """The row's status, or None when no row exists."""
    row = get_row(store, character_id, mission_id)
    return row["status"] if row else None


def make_available(store, character_id, mission_id, game_minutes):
    """Create the row with status `available` and
    ``progress = {'available_at_game_minutes': <minute>}``. Returns
    True on creation, False when a row already exists — a retry
    reuses the row (retry_mission), it never creates a second one,
    and the PK enforces that."""
    if get_row(store, character_id, mission_id) is not None:
        return False
    store.insert("mission_progress", character_id=character_id,
                 mission_id=mission_id, status="available",
                 progress=json.dumps(
                     {"available_at_game_minutes": game_minutes}),
                 updated_at_game_minutes=game_minutes)
    return True


def accept_mission(store, character_id, mission_id, game_minutes):
    """`available` -> `active` (the dialogue accept effect, GDD-15
    §13.4). Sets ``progress.accepted_at_game_minutes``. Returns True
    on the transition, False from any other status (including no
    row — a mission that was never available cannot be accepted)."""
    row = get_row(store, character_id, mission_id)
    if row is None or row["status"] != "available":
        return False
    progress = _progress(row)
    progress["accepted_at_game_minutes"] = game_minutes
    _write(store, character_id, mission_id, "active", progress,
           game_minutes)
    return True


def set_objectives_complete(store, character_id, mission_id,
                            game_minutes):
    """Set ``progress.objectives_complete = true`` while the row is
    still `active` — the mission system verifying the objectives
    against world state (DG §3.6). Returns True when set, False from
    any other status. The caller has verified the objectives; this
    function only records the verification, it never checks world
    state itself (except through the verify_* helpers below)."""
    row = get_row(store, character_id, mission_id)
    if row is None or row["status"] != "active":
        return False
    progress = _progress(row)
    progress["objectives_complete"] = True
    _write(store, character_id, mission_id, "active", progress,
           game_minutes)
    return True


def verify_mission_1_4(store, data, character_id, current_zone,
                       current_anchor, game_minutes):
    """Verify mission 1.4's objectives against world state (DG
    §3.6): (1) the player's zone is ``d1_riverfront`` at a game
    minute in the sunset window — at or after that day's
    season-shifted sunset minute and before 20:00; (2) the player
    is present at the riverfront tea stall anchor. Both must hold,
    in either order; being in the zone earlier in the day does not
    verify (1). On success sets ``objectives_complete`` while the
    row is still `active` and returns True. Returns False when the
    row is not `active`, or either objective fails. Presence is the
    caller's responsibility to supply (the GDD-15 §18 accessor read
    for the player — the same read photographs.py relies on)."""
    from . import environment as environment_mod
    row = get_row(store, character_id, "1.4")
    if row is None or row["status"] != "active":
        return False
    if current_zone != RIVERFRONT_ZONE:
        return False
    day_index = game_minutes // 1440
    minute_of_day = game_minutes % 1440
    sunset_min = environment_mod.daylight(data, day_index)[1]
    if not (sunset_min <= minute_of_day < EVENING_END_MINUTE):
        return False
    if current_anchor != RIVERFRONT_TEA_STALL_ANCHOR:
        return False
    return set_objectives_complete(store, character_id, "1.4",
                                   game_minutes)


def complete_mission(store, character_id, mission_id, game_minutes):
    """`active` -> `completed` (the dialogue `mission_complete`
    effect, GDD-15 §13.4), only when ``objectives_complete`` is
    true. Sets ``progress.completed_at_game_minutes``. For mission
    1.4 it also pays the sourced reward: the memory event "First
    evening in Rupsha" as a life event. Returns True on completion,
    False from any other status or when the objectives are not
    verified — a mission cannot complete without passing `active`
    with verified objectives. Credit/reputation payout for other
    missions is not wired here (see the module note)."""
    row = get_row(store, character_id, mission_id)
    if row is None or row["status"] != "active":
        return False
    if not _progress(row).get("objectives_complete"):
        return False
    progress = _progress(row)
    progress["completed_at_game_minutes"] = game_minutes
    _write(store, character_id, mission_id, "completed", progress,
           game_minutes)
    if mission_id == "1.4":
        from . import memory as memory_mod
        memory_mod.log_life_event(
            store, character_id, MISSION_1_4_MEMORY_EVENT,
            game_minutes,
            details={"mission_id": "1.4",
                     "memory": MISSION_1_4_MEMORY_TEXT})
    return True


def fail_mission(store, character_id, mission_id, game_minutes,
                 abandoned=False):
    """`active` -> `failed` — on a deadline missed, or on abandon
    (GDD-15 §13.5 recommendation: `failed` + ``progress.abandoned =
    true``). Returns True on the transition, False from any other
    status. Dialogue never writes `failed` (GDD-15 §13.4): only the
    mission system calls this, on expiry or on the abandon the
    dialogue recommended."""
    row = get_row(store, character_id, mission_id)
    if row is None or row["status"] != "active":
        return False
    progress = _progress(row)
    if abandoned:
        progress["abandoned"] = True
    _write(store, character_id, mission_id, "failed", progress,
           game_minutes)
    return True


def retry_mission(store, character_id, mission_id, game_minutes):
    """`failed` -> `available` after 7 in-game days (GDD-04 §1),
    with a FRESH ``available_at_game_minutes`` — a new deadline
    window, not a continuation (§3.2). The old
    ``accepted_at_game_minutes`` / ``objectives_complete`` /
    ``completed_at_game_minutes`` / ``abandoned`` are cleared, so a
    retried mission is verified from scratch. Returns True on the
    transition, False when the row is not `failed` or the 7 days
    have not yet passed since the failure."""
    row = get_row(store, character_id, mission_id)
    if row is None or row["status"] != "failed":
        return False
    if game_minutes - row["updated_at_game_minutes"] \
            < RETRY_WAIT_MINUTES:
        return False
    _write(store, character_id, mission_id, "available",
           {"available_at_game_minutes": game_minutes}, game_minutes)
    return True


def deadline_days_for(data, mission_id):
    """The `deadline_days` of a main mission in data/missions.json
    (GDD-04 §3.2), or None when the mission carries none — most
    missions carry none, and a deadline is a property of the
    mission's fiction. Favours (a `side:` key) never carry one."""
    if mission_id.startswith("side:"):
        return None
    for m in data.missions_file.get("missions", []):
        if m["id"] == mission_id:
            return m.get("deadline_days")
    return None


def expire_deadlines(store, data, game_minutes):
    """Set every `active` row whose mission has a deadline and whose
    ``remaining`` (GDD-04 §3.2: available_at + deadline_days × 1440
    − now) has reached 0 to `failed`. Rows without an
    ``available_at_game_minutes`` are skipped (they predate the
    contract). Returns the mission ids failed, in row order. A
    mission with no deadline never expires here."""
    failed = []
    for row in store.rows("SELECT * FROM mission_progress"
                          " WHERE status = 'active'"
                          " ORDER BY character_id, mission_id"):
        days = deadline_days_for(data, row["mission_id"])
        if days is None:
            continue
        progress = _progress(row)
        available_at = progress.get("available_at_game_minutes")
        if available_at is None:
            continue
        if available_at + days * 1440 - game_minutes <= 0:
            if fail_mission(store, row["character_id"],
                            row["mission_id"], game_minutes):
                failed.append(row["mission_id"])
    return failed


# -- Favour instances (DG §3.6) ---------------------------------------

def favour_instance_key(favour_type, giver_character_id,
                        game_minutes):
    """The §3.1 instance key: side:<type>:<giver>:<minute>."""
    return (f"side:{favour_type}:{giver_character_id}:"
            f"{game_minutes}")


def create_favour_instance(store, data, character_id, favour_type,
                           giver_character_id, game_minutes):
    """Ask the mission system to create a favour instance row
    (`available`, with `available_at_game_minutes` = the generation
    minute). The generator never writes the row itself — it asks
    here. ``favour_type`` must be one of the five §3.1 types in
    data/missions.json `side_mission_types` (a ValueError otherwise
    — the generator must not invent a type). Returns the instance
    key, or None when a row with that key already exists (the same
    giver generating the same type in the same minute is one
    favour, not two)."""
    types = [s["type"] for s in
             data.missions_file.get("side_mission_types", [])]
    if favour_type not in types:
        raise ValueError(
            f"unknown favour type {favour_type!r}: not a §3.1 type")
    key = favour_instance_key(favour_type, giver_character_id,
                              game_minutes)
    if make_available(store, character_id, key, game_minutes):
        return key
    return None


def verify_favour_objectives(store, character_id, mission_id,
                             game_minutes, favour_subtype=None,
                             lost_item_id=None,
                             account_id=None, discoverable_id=None):
    """Verify a favour instance's objectives against world state and
    set ``objectives_complete`` while the row is `active`. The
    instance key names the §3 type; the caller supplies the subtype
    it generated and the ids the favour concerns (the generator
    knows them at generation — the key alone does not carry them,
    and "find a lost item" is a subtype within Favours, GDD-04 §3,
    not a type of its own):

    - ``favours`` + subtype ``find_a_lost_item``: ``lost_item_id``
      — complete iff DF's ``favour_objective_complete()`` holds (the
      row reached `returned`).
    - ``discovery``: ``account_id`` + ``discoverable_id`` — complete
      iff a ``discovery_progress`` row stands for them.
    - every other kind has no verification predicate in the sim yet:
      returns False and is recorded, not faked.

    Returns True when the objectives verified, False otherwise
    (including a non-`side:` mission id, a row that is not `active`,
    or a missing parameter)."""
    if not mission_id.startswith("side:"):
        return False
    parts = mission_id.split(":")
    if len(parts) != 4:
        return False
    favour_type = parts[1]
    verified = False
    if favour_type == "favours" \
            and favour_subtype == "find_a_lost_item":
        if lost_item_id is None:
            return False
        from . import lost_items as lost_items_mod
        verified = lost_items_mod.favour_objective_complete(
            store, lost_item_id)
    elif favour_type == "discovery":
        if account_id is None or discoverable_id is None:
            return False
        verified = store.row(
            "SELECT 1 FROM discovery_progress WHERE account_id = ?"
            " AND discoverable_id = ?",
            (account_id, discoverable_id)) is not None
    else:
        return False
    if not verified:
        return False
    return set_objectives_complete(store, character_id, mission_id,
                                   game_minutes)
