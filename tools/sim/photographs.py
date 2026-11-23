"""Queue 15 Unit DA — Photograph Mechanic Implementation (GDD-04 §3.5,
Unit BY design).

Implements the §3.5 record: the ``photographs`` table, the photo-mode
gate (mission 1.4 unlock), and the dual write — a photograph writes
the ``photographs`` row and the ``discovery_progress`` row for the
same landmark in one transaction, so a photograph never exists
without its discovery and a discovery by photograph never exists
without its photograph. A duplicate photograph writes nothing.

The discoverable set is read from data, not fixed in code: the
landmark files of all three places (District 1 blockout, District 2
blockout, Shibnagar town file) supply the 19 landmarks, and each
landmark's zone is its point inside its zone box — except the three
§3.4 assigned-by-description entries (Clock Tower, Bridge Approach,
Northgate Tower), whose points fall outside every box and whose zones
are the §3.4 decision, carried here as an explicit override table. When the set
grows, this module follows it with no change.

The gate reads the sim's ``mission_progress`` mirror of
``data/schema.sql``: photo mode is unlocked iff a row
(``character_id``, ``'1.4'``, ``status = 'completed'``) exists. The
mission system that writes that row is Phase 6 work — this module
only reads it, so in a live world with no mission system yet the
gate stays closed and photographs are refused. ``account_id`` is
the caller's Phase 9 ``accounts.account_id``, opaque here: the sim
has no accounts table and enforces no FK on it.

Presence is the caller's responsibility to supply (the player's
current zone, GDD-15 §18's accessor read for the player): the
function refuses when the supplied zone is not the landmark's zone.
"""
import json

# GDD-04 §3.4 assigned-by-description zones: the three landmarks
# whose points fall outside every zone box, so no box can verify
# them. (Clock Tower: the arterial crossing at the market's north
# edge; Bridge Approach: the south-east river edge; Northgate Tower:
# its District 2 mirror.) Every other landmark's zone is its point
# inside its zone box.
ZONE_OVERRIDES = {
    "lm_clock_tower": "d1_market",
    "lm_bridge_approach": "d1_riverfront",
    "d2_lm_northgate_tower": "d2_market",
}

PHOTO_MODE_MISSION = "1.4"


def discovery_set(data):
    """The §3.4 landmark set as {discoverable_id: zone}, read from
    the three landmark files. Raises ValueError if a landmark's
    point is in no zone box and has no §3.4 override — the set must
    stay consistent, and a silently zoneless landmark would be a
    discoverable the presence rule can never satisfy."""
    out = {}
    sources = (
        (getattr(data, "blockout", {}) or {}, "district1-blockout.json"),
        (getattr(data, "district2_blockout", {}) or {},
         "district2-blockout.json"),
        (getattr(data, "city2_file", {}) or {}, "city2-shibnagar.json"),
    )
    for doc, _name in sources:
        boxes = doc.get("zone_boxes_m", {})
        for lm in doc.get("landmarks", []):
            lm_id = lm["id"]
            if lm_id in ZONE_OVERRIDES:
                out[lm_id] = ZONE_OVERRIDES[lm_id]
                continue
            x, z = lm["at"]
            zone = None
            for zid, box in boxes.items():
                if box["x0"] <= x <= box["x1"] \
                        and box["z0"] <= z <= box["z1"]:
                    zone = zid
                    break
            if zone is None:
                raise ValueError(
                    f"landmark {lm_id} is in no zone box and has no"
                    " §3.4 override")
            out[lm_id] = zone
    return out


def photo_mode_unlocked(store, character_id):
    """The §3.5 gate: mission 1.4 completed by this character.
    Reads the sim's mission_progress mirror; the mission system
    that writes the row is Phase 6 work."""
    row = store.row(
        "SELECT 1 FROM mission_progress WHERE character_id = ?"
        " AND mission_id = ? AND status = 'completed'",
        (character_id, PHOTO_MODE_MISSION))
    return row is not None


def take_photograph(store, data, account_id, character_id,
                    discoverable_id, game_minutes, taken_in_zone):
    """Take a photograph of a landmark. Returns the new
    ``photograph_id``, or None when the photograph is refused:

    - the discoverable is not a landmark in the §3.4 set (a bus
      route is ridden, not photographed; an unknown id is refused);
    - photo mode is not unlocked (mission 1.4 not completed);
    - the player is not in the landmark's zone (presence rule);
    - the account already has a photograph — or a discovery — for
      the landmark (a duplicate writes nothing; a re-photograph of
      a found landmark is not a discovery).

    On success writes two rows in one transaction: the
    ``photographs`` row and the ``discovery_progress`` row for the
    same landmark, with the same minute and zone. The favour
    completes through the discovery row it already completes through
    (§3.4/§15.2) — no new dialogue node is needed.
    """
    zones = discovery_set(data)
    zone = zones.get(discoverable_id)
    if zone is None:
        return None
    if not photo_mode_unlocked(store, character_id):
        return None
    if taken_in_zone != zone:
        return None
    existing = store.row(
        "SELECT 1 FROM photographs WHERE account_id = ?"
        " AND discoverable_id = ?", (account_id, discoverable_id))
    if existing is not None:
        return None
    discovered = store.row(
        "SELECT 1 FROM discovery_progress WHERE account_id = ?"
        " AND discoverable_type = 'landmark' AND discoverable_id = ?",
        (account_id, discoverable_id))
    if discovered is not None:
        return None
    pid = store.next_id("PH", "photographs", "photograph_id")
    store.insert("photographs", photograph_id=pid,
                 account_id=account_id, character_id=character_id,
                 discoverable_id=discoverable_id,
                 taken_at_game_minutes=game_minutes,
                 taken_in_zone=taken_in_zone)
    store.insert("discovery_progress", account_id=account_id,
                 discoverable_type="landmark",
                 discoverable_id=discoverable_id,
                 discovered_at_game_minutes=game_minutes,
                 discovered_in_zone=taken_in_zone)
    return pid
