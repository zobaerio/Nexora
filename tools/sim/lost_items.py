"""Queue 15 Unit CY — Losing-event wiring (GDD-04 §3.3, Unit BX design).

Implements the three losing events BX designed and the write contract
it specified: one helper, ``record_loss()``, writes exactly one
``lost_items`` row, ``status = 'lost'``, and refuses when its
precondition fails. The events wire into the merged systems that fire
them — ``safety.intake_incidents`` (commute incident),
``environment.daily_pass`` (storm-soaked market trip),
``households.move_household`` (move-house) — and each event calls its
function from the existing pass, never from a new cadence.

Queue 16 Unit DF wires the rest of the §3.3 lifecycle:
``find_lost_item()`` writes ``found`` (the finder must be in the
``lost_zone``, at the ``lost_anchor`` where one was recorded) and
``return_lost_item()`` writes ``returned`` (refusing an item never
found); the §3.1 favour completes off the ``returned`` write
through the existing complete node (GDD-15 §15.2) — the Phase 6
mission system sets ``progress.objectives_complete`` on the favour
instance row, and this module provides the predicate it evaluates
(``favour_objective_complete``).

The loss rate lives in ``data/lost-items-config.json`` (default 0 —
specified but silent): with the default, every event function
returns without writing, so a live world with no tuning call behaves
exactly as before this unit. A test or a tuning call passes an
explicit ``rate`` instead; the rate is one number for all three
events (BX: per-event rates would be three tuning calls, not one).

Seeding (GDD-04 §3.3, Unit CX): the inventory rows the events lose
from are written by the purchase points that already exist —
``seed_vehicle_row()`` beside the ``vehicles`` insert in
``transport._purchase_sweep`` and ``seed_goods_rows()`` in
``market.retail_allocation`` (one month of standing, consumed by the
next month's allocation). Clothing rows are seeded by the creator
implementation (Unit DD, Queue 16, below): ``seed_clothing_rows()``
for starting outfits (``identity.create_person``, called by the
genesis builder in ``population.new_person``) and issued uniforms
(``labour.match_vacancies`` and ``admin.match_vacancies`` at hiring);
furniture/tool/document have no catalogue and no seeding point, so
their BX branches cannot fire — the precondition refuses, which is
the helper working as designed.
"""
import json

from .rng import SimRng

# BX's per-event eligible types, in BX's listing order — the listing
# order is also the loss priority when an owner holds several.
EVENT_TYPES = {
    "commute_incident": ("goods", "document", "tool"),
    "storm_market": ("goods",),
    "move_house": ("furniture", "tool", "clothing", "goods"),
}

# BX E2: the exposed modes — a storm soaks the shopping of a traveller
# on foot, by cycle, or by rickshaw; a bus or car keeps it dry.
EXPOSED_MODES = ("walk", "cycle", "rickshaw")

DEFAULT_LOSS_RATE = 0.0

# Queue 19 Units EE/EF — condition & decay (GDD-04 §3.3, Unit DQ).
# Thresholds adopted from the vehicle precedent
# (data/transport-config.json `maintenance`: service_threshold 60.0,
# restored_condition 90.0): a tool or piece at 60 or below is due a
# service; a repair restores it to 90, never to 100 — a repaired
# thing is not a new thing. New furniture/tool rows seed at 100
# (vehicles seed at 92.0 — bought used stock, not new).
CONDITION_NEW = 100
SERVICE_THRESHOLD = 60
RESTORED_CONDITION = 90


def cfg(data):
    """The lost-items config, defaulting to {} when the data object
    predates it (older saved test fixtures)."""
    return getattr(data, "lost_items_config", {}) or {}


def loss_rate(data):
    """The configured loss rate, clamped to [0, 1]; default 0."""
    try:
        rate = float(cfg(data).get("loss_rate", DEFAULT_LOSS_RATE))
    except (TypeError, ValueError):
        return DEFAULT_LOSS_RATE
    return min(1.0, max(0.0, rate))


def household_head(store, household_id):
    """The household head: the member with role 'head' (population.py
    assigns it; lifecycle.py passes it on death). None when the
    household has no standing head — the custody rule (CX) names the
    head as the owner, so a headless household owns no rows."""
    row = store.row(
        "SELECT character_id FROM household_members WHERE"
        " household_id = ? AND role = 'head'"
        " AND left_at_game_minutes IS NULL ORDER BY character_id"
        " LIMIT 1", (household_id,))
    return row["character_id"] if row else None


def _has_standing_found_row(store, item_instance_id):
    """True when a ``lost_items`` row for the item stands ``found``
    (Unit EA, Queue 19 — DP's hand-back custody rule): the item is
    in the finder's hands, awaiting hand-back, and cannot be lost
    again until it is returned. A ``returned`` row is not standing,
    so a returned item may be lost again."""
    return store.row(
        "SELECT 1 FROM lost_items WHERE item_instance_id = ?"
        " AND status = 'found'", (item_instance_id,)) is not None


def eligible_items(store, owner_character_id, allowed_types):
    """The owner's standing inventory rows of the allowed types, in
    loss priority: BX's listing order for the event, then
    item_instance_id. Only standing rows count — a row is never
    deleted on loss, so eligibility is simply 'the row exists' —
    except an item with a standing ``found`` row (Unit EA): it is
    in the finder's custody and cannot be lost again until it is
    returned, so the events' eligible sets exclude it."""
    priority = {t: i for i, t in enumerate(allowed_types)}
    rows = store.rows(
        "SELECT * FROM inventory_items WHERE owner_character_id = ?",
        (owner_character_id,))
    kept = [r for r in rows if r["item_type"] in priority
            and not _has_standing_found_row(store,
                                            r["item_instance_id"])]
    kept.sort(key=lambda r: (priority[r["item_type"]],
                             r["item_instance_id"]))
    return kept


def record_loss(store, owner_character_id, item_instance_id,
                game_minutes, lost_zone, lost_anchor=None):
    """Write exactly one ``lost_items`` row, ``status = 'lost'``, with
    the fields of the GDD-04 §3.3 table. Returns the new
    ``lost_item_id``, or None when the write is refused:

    - the owner holds no ``inventory_items`` row with that id
      (the BX precondition — no event or generator may invent an
      item to satisfy it);
    - a ``lost`` row already stands for the item (it is already
      lost; it cannot be lost twice — a returned item may be lost
      again, only a standing loss blocks);
    - a ``found`` row already stands for the item (Unit EA, Queue
      19 — DP's hand-back custody rule: the item is in the
      finder's hands, awaiting hand-back, and cannot be lost again
      until it is returned).

    ``lost_zone`` validity is the caller's responsibility: every
    caller passes a zone its own records already name (a trip's
    destination zone, a property's zone), never an invented one.
    The inventory row itself is never mutated or deleted — the item
    still exists; only its whereabouts are unknown.
    """
    item = store.row(
        "SELECT * FROM inventory_items WHERE item_instance_id = ?"
        " AND owner_character_id = ?",
        (item_instance_id, owner_character_id))
    if item is None:
        return None
    standing = store.row(
        "SELECT 1 FROM lost_items WHERE item_instance_id = ?"
        " AND status = 'lost'", (item_instance_id,))
    if standing is not None:
        return None
    if _has_standing_found_row(store, item_instance_id):
        return None
    lid = store.next_id("LI", "lost_items", "lost_item_id")
    store.insert("lost_items", lost_item_id=lid,
                 owner_character_id=owner_character_id,
                 item_instance_id=item_instance_id,
                 lost_at_game_minutes=game_minutes,
                 lost_zone=lost_zone, lost_anchor=lost_anchor,
                 status="lost")
    return lid


# -- Queue 16 Unit DF: recovery wiring (GDD-04 §3.3 lifecycle) ---------
# CX designed the full lifecycle lost -> found -> returned; CY only
# wrote lost rows. These two functions write the other two
# transitions. Finding and handing back are player actions,
# verified against world state like any mission objective
# (GDD-04 §3.3): the caller supplies the finder's current zone
# (and anchor, where the finder stands at one) — the same
# caller-supplies-presence pattern as photographs.take_photograph
# — and the functions refuse when the supplied place is not the
# recorded one. The §3.1 favour completes on the return: the
# mission system (Phase 6) sets progress.objectives_complete on
# the favour instance row when the lost_items row reaches
# 'returned' (GDD-15 §15.2), and the complete node
# (dlg_favour_complete_find_a_lost_item) pays the recorded reward.
# No mission system exists yet, so this unit writes the row the
# system will key off and provides the predicate it will evaluate
# (favour_objective_complete) — it does not build the system.

def find_lost_item(store, lost_item_id, finder_character_id,
                   game_minutes, finder_zone, finder_anchor=None):
    """Write `found` for a lost item. Returns the lost_item_id, or
    None when the find is refused:

    - no such row, or the row is not `lost` (already found, or
      already returned — a found item cannot be found again);
    - the finder is not in the `lost_zone`;
    - a `lost_anchor` was recorded and the finder is not at it
      (where no anchor was recorded, the zone alone is the check).

    On success sets status `found` with the finder and the minute.
    The inventory row is untouched, as on loss."""
    row = store.row("SELECT * FROM lost_items WHERE lost_item_id = ?",
                    (lost_item_id,))
    if row is None or row["status"] != "lost":
        return None
    if finder_zone != row["lost_zone"]:
        return None
    if row["lost_anchor"] is not None \
            and finder_anchor != row["lost_anchor"]:
        return None
    store.execute("UPDATE lost_items SET status = 'found',"
                  " found_by_character_id = ?,"
                  " found_at_game_minutes = ?"
                  " WHERE lost_item_id = ?",
                  (finder_character_id, game_minutes, lost_item_id))
    return lost_item_id


def return_lost_item(store, lost_item_id, game_minutes):
    """Write `returned` for a found item — the hand-back to the
    owner. Returns the lost_item_id, or None when the return is
    refused: no such row, the row is still `lost` (an item never
    found cannot be returned — the finder must hold it first), or
    already `returned`. On success sets status `returned` with the
    minute; the §3.1 favour completes off this write (see the
    module note above). The inventory row is untouched."""
    row = store.row("SELECT * FROM lost_items WHERE lost_item_id = ?",
                    (lost_item_id,))
    if row is None or row["status"] != "found":
        return None
    store.execute("UPDATE lost_items SET status = 'returned',"
                  " returned_at_game_minutes = ?"
                  " WHERE lost_item_id = ?",
                  (game_minutes, lost_item_id))
    return lost_item_id


def favour_objective_complete(store, lost_item_id):
    """The §15.2 completion predicate: the lost-item favour's
    objective is complete iff the row has reached `returned`. The
    Phase 6 mission system evaluates this when the hand-back is
    verified and sets progress.objectives_complete on the favour
    instance row; the dialogue complete node then pays the
    recorded reward. False for an unknown id, a lost row, and a
    found-but-not-returned row."""
    row = store.row("SELECT status FROM lost_items"
                    " WHERE lost_item_id = ?", (lost_item_id,))
    return row is not None and row["status"] == "returned"


# -- Queue 19 Unit ED: hand-back wiring (GDD-04 §3.3, Unit DP) ------
# DP designed the hand-back; no sim function performed it. These two
# functions are the performance: the finder carries the item to the
# owner's CURRENT home (the open tenancy — never the origin zone of
# the loss), or, where the owner holds no tenancy, to the owner's
# current zone (GDD-15 §18). The deceased-owner case refuses
# (orphaned favour — the DP rule, enforced not just stated). The
# caller supplies the finder's presence — the same
# caller-supplies-presence pattern as find_lost_item — because the
# sim has no live player position to read.

def current_zone_at(store, character_id, game_minutes):
    """The GDD-15 §18 accessor, implemented against the stored
    schedule state (the §18 design added no sim function; this unit
    is its first sim implementation, for the hand-back fallback).
    Reads the ``instantiated_schedules`` row for the day and returns
    the ``zone`` of the block containing ``game_minutes`` (starts
    and ends are absolute game minutes). None when the day was never
    run (no row) or no block contains the minute — never a
    re-instantiation, never a recomputed jitter (§18.1)."""
    day_index = game_minutes // 1440
    row = store.row(
        "SELECT blocks_json FROM instantiated_schedules"
        " WHERE character_id = ? AND day_index = ?",
        (character_id, day_index))
    if row is None:
        return None
    try:
        blocks = json.loads(row["blocks_json"])
    except ValueError:
        return None
    for block in blocks:
        if block["start"] <= game_minutes < block["end"]:
            return block.get("zone")
    return None


def hand_back_lost_item(store, lost_item_id, finder_character_id,
                        game_minutes, finder_property_id=None,
                        finder_zone=None):
    """Perform the DP hand-back: the finder carries a ``found`` item
    to its owner, and only then does ``return_lost_item()`` write
    ``returned``. Returns the lost_item_id, or None when the
    hand-back is refused:

    - no such row, or the row is not ``found`` (an item never found
      cannot be handed back — the finder must hold it first);
    - the caller is not the recorded finder (``found_by_-
      character_id`` holds the item; nobody else can hand it back);
    - the owner is deceased (DP: the favour is orphaned — the
      inheritance cascade moves money + property, never inventory,
      so no heir owns the item and no hand-back to the heir exists);
    - the owner holds a tenancy and the finder does not stand at
      that property (``finder_property_id`` must equal the open
      tenancy's ``property_id`` — the CURRENT home, re-routed after
      a move, never the loss's origin zone);
    - the owner holds no tenancy and the finder is not in the
      owner's current zone (``finder_zone`` must equal
      ``current_zone_at()`` for the owner at the return minute).

    On success writes ``returned`` with the minute (the §3.1 favour
    completes off that write, as DF specifies). The inventory row is
    untouched."""
    row = store.row("SELECT * FROM lost_items WHERE lost_item_id = ?",
                    (lost_item_id,))
    if row is None or row["status"] != "found":
        return None
    if row["found_by_character_id"] != finder_character_id:
        return None
    owner = row["owner_character_id"]
    char = store.row(
        "SELECT household_id, died_at_game_minutes FROM characters"
        " WHERE character_id = ?", (owner,))
    if char is None or char["died_at_game_minutes"] is not None:
        return None
    tenancy = None
    if char["household_id"]:
        tenancy = store.row(
            "SELECT property_id FROM tenancies WHERE"
            " tenant_household_id = ?"
            " AND ended_at_game_minutes IS NULL",
            (char["household_id"],))
    if tenancy is not None:
        if finder_property_id != tenancy["property_id"]:
            return None
    else:
        zone = current_zone_at(store, owner, game_minutes)
        if zone is None or finder_zone != zone:
            return None
    return return_lost_item(store, lost_item_id, game_minutes)


def _resolve_rng(store, rng):
    """The draw's rng: the caller's stream when one is passed, else a
    fresh stream keyed by the world's stored seed. SimRng streams are
    pure functions of (seed, context), so both paths draw identically
    — a caller without an rng in scope (``households.move_household``)
    still rolls deterministically, and save/restore cannot change a
    future draw."""
    if rng is not None:
        return rng
    world = store.world()
    seed = world["sim_seed"] if world is not None else "default"
    return SimRng(seed)


def _draw(rng, key, rate):
    """One seeded draw per event occurrence: the loss happens iff the
    draw falls under the rate. With the default rate 0 this never
    fires; with rate 1 it always fires."""
    return rng.stream("lost_items", *key).random() < rate


def commute_incident_losses(store, data, rng, incident_id, segment_id,
                            month_index, game_minutes, rate=None):
    """BX event E1, called once per traffic-accident incident by
    ``safety.intake_incidents``. The travellers on the segment are
    the recorded trips of the month whose ``segment_ids`` include it;
    the earliest such trip in ``trip_id`` order is the one who loses
    something (one loss per incident at most — BX). Returns the new
    ``lost_item_id`` list (0 or 1 entries)."""
    if rate is None:
        rate = loss_rate(data)
    rng = _resolve_rng(store, rng)
    since_day = (month_index - 1) * 30
    trips = []
    for trip in store.rows(
            "SELECT * FROM trips WHERE day_index >= ? AND day_index < ?"
            " ORDER BY trip_id", (since_day, since_day + 30)):
        try:
            segments = json.loads(trip["segment_ids"] or "[]")
        except ValueError:
            continue
        if segment_id in segments:
            trips.append(trip)
    if not trips:
        return []
    trip = trips[0]
    if not _draw(rng, ("commute", incident_id), rate):
        return []
    for item in eligible_items(store, trip["character_id"],
                               EVENT_TYPES["commute_incident"]):
        # The loss is noticed on arrival, not mid-road (BX): the
        # incident carries no minute and no zone, so the trip's own
        # destination zone and arrival minute are the record.
        lid = record_loss(store, trip["character_id"],
                          item["item_instance_id"],
                          trip["arrive_minute"],
                          trip["destination_zone"])
        if lid is not None:
            return [lid]
    return []


def storm_market_losses(store, data, rng, disaster_id, day_index,
                        game_minutes, rate=None):
    """BX event E2, called once per active disaster-day by
    ``environment.daily_pass``. The disaster must be an active
    cyclone/severe_storm with a ``disaster_impacts`` row in
    ``d1_market``; the traveller is the first recorded trip of the
    day to ``d1_market`` in an exposed mode, in ``trip_id`` order
    (one loss per (disaster, day) at most — BX). Returns the new
    ``lost_item_id`` list (0 or 1 entries)."""
    if rate is None:
        rate = loss_rate(data)
    rng = _resolve_rng(store, rng)
    disaster = store.row("SELECT * FROM disaster_events WHERE"
                         " disaster_id = ?", (disaster_id,))
    if disaster is None or disaster["status"] != "active":
        return []
    if disaster["disaster_type"] not in ("cyclone", "severe_storm"):
        return []
    if disaster["started_day"] > day_index:
        return []
    if disaster["ends_day"] is not None \
            and day_index > disaster["ends_day"]:
        return []
    impact = store.row(
        "SELECT 1 FROM disaster_impacts WHERE disaster_id = ?"
        " AND zone_id = 'd1_market'", (disaster_id,))
    if impact is None:
        return []
    trip = store.row(
        "SELECT * FROM trips WHERE day_index = ? AND"
        " destination_zone = 'd1_market' AND mode IN"
        " ('walk', 'cycle', 'rickshaw') ORDER BY trip_id LIMIT 1",
        (day_index,))
    if trip is None:
        return []
    if not _draw(rng, ("storm", disaster_id, day_index), rate):
        return []
    for item in eligible_items(store, trip["character_id"],
                               EVENT_TYPES["storm_market"]):
        lid = record_loss(store, trip["character_id"],
                          item["item_instance_id"],
                          trip["arrive_minute"], "d1_market", "market")
        if lid is not None:
            return [lid]
    return []


def move_house_loss(store, data, rng, household_id, origin_zone,
                    game_minutes, rate=None):
    """BX event E3, called once per successful move by
    ``households.move_household``. The mover is the household head;
    the loss is in the origin property's zone — the last place the
    item was certainly held — and a home is not a service anchor.
    Returns the new ``lost_item_id`` list (0 or 1 entries)."""
    if rate is None:
        rate = loss_rate(data)
    rng = _resolve_rng(store, rng)
    head = household_head(store, household_id)
    if head is None:
        return []
    if not _draw(rng, ("move", household_id, game_minutes), rate):
        return []
    for item in eligible_items(store, head,
                               EVENT_TYPES["move_house"]):
        lid = record_loss(store, head, item["item_instance_id"],
                          game_minutes, origin_zone)
        if lid is not None:
            return [lid]
    return []


def seed_vehicle_row(store, character_id, vehicle_id, vehicle_type,
                     game_minutes, condition, fuel_litres):
    """Write the inventory row for a purchased vehicle (CX seeding),
    in the same transaction as the ``vehicles`` insert in
    ``transport._purchase_sweep``. ``item_ref`` is the vehicle class
    id; the state JSON carries the link to the operational
    ``vehicles`` row, which stays the operational registry."""
    iid = store.next_id("INV", "inventory_items", "item_instance_id")
    store.insert("inventory_items", item_instance_id=iid,
                 item_type="vehicle", item_ref=vehicle_type,
                 owner_character_id=character_id,
                 location_property_id=None,
                 state=json.dumps({"vehicle_id": vehicle_id,
                                   "odometer_km": 0,
                                   "condition": condition,
                                   "fuel_litres": fuel_litres}),
                 acquired_at_game_minutes=game_minutes)
    return iid


def seed_goods_rows(store, data, household_id, head_character_id,
                    allocations, game_minutes):
    """Write the transient goods rows for a household's monthly
    retail allocation (CX seeding), called from
    ``market.retail_allocation`` — which consumes (deletes) the
    previous month's goods rows first, so a goods row stands for
    exactly the month it was bought. ``allocations`` maps good id ->
    units actually received (got_units, after coverage rationing);
    a good with zero units gets no row. Returns the new item ids."""
    # No DELETE here: the caller consumes all standing goods rows in
    # one statement before seeding, so a household with no wants this
    # month still has its last month's shopping consumed.
    units = {g["id"]: g.get("unit") for g in
             data.goods_file.get("goods", [])}
    made = []
    for good_id in sorted(allocations):
        qty = allocations[good_id]
        if qty is None or qty <= 0:
            continue
        iid = store.next_id("INV", "inventory_items", "item_instance_id")
        store.insert("inventory_items", item_instance_id=iid,
                     item_type="goods", item_ref=good_id,
                     owner_character_id=head_character_id,
                     location_property_id=None,
                     state=json.dumps({"quantity": round(qty, 3),
                                       "unit": units.get(good_id)}),
                     acquired_at_game_minutes=game_minutes)
        made.append(iid)
    return made


# -- Queue 16 Unit DD: clothing seeding (GDD-04 §3.3, Unit CX) --------
# The catalogue is data/clothing.json (31 items, GDD-09 §4); the
# starting outfits are its authored `starting_outfits` lists (Unit
# DD, PROPOSED — no source names a default outfit, GDD-09 §3 leaves
# the player's three outfits to the creator's choice). One inventory
# row per garment, item_type "clothing", state {slot,
# outfit_context, issued} per the CX record shape.

def _clothing_items(data):
    """{clothing id: catalogue row} from the loaded clothing file."""
    return {i["id"]: i for i in
            data.clothing_file.get("items", [])}


def uniform_items(data, profession_id, tier):
    """The issuable uniform item ids for a profession at a tier —
    the `profession_uniforms` mapping, minus the two rows GDD-09 §5
    says cannot be issued: the pilot's (no airline operates in
    District 1, no airport — the uniform is catalogued for the
    future airport district and is never faked as worn) and the
    taxi driver's below tier 2 (tier-1 rented-CNG drivers wear
    their own clothes). Every other mapped profession issues its
    set at hiring, whatever the tier. [] when the profession maps
    to no uniform at all (a dress code, not a uniform)."""
    if profession_id is None:
        return []
    if profession_id == "pilot":
        return []
    if profession_id == "taxi_driver" and (tier or 1) < 2:
        return []
    for row in data.clothing_file.get("profession_uniforms", []):
        if row["profession_id"] == profession_id:
            return list(row.get("outfit_item_ids", []))
    return []


def starting_outfits(data, profession_id, tier, sim_tier):
    """The starting outfits to seed at creation, as {context:
    {"items": [...], "issued": ...}} — the creator's three outfits
    (GDD-09 §3): work + casual + formal. Ambient characters get
    none (texture variants, never catalogue outfits — GDD-09 §2).
    The work outfit is the issued uniform when one is issuable
    (issued "employer"), else the authored `work_default` list
    (issued "creator" — the character's own clothes). Casual and
    formal come from the authored `starting_outfits` lists, issued
    "creator". The player character's three are the same lists in
    the sim: the UE creator (Phase 2) replaces them with the
    player's own picks, and the sim keeps the defaults so a
    genesis character holds real rows."""
    if sim_tier == "ambient":
        return {}
    defaults = data.clothing_file.get("starting_outfits", {})
    uniform = uniform_items(data, profession_id, tier)
    if uniform:
        work = {"items": uniform, "issued": "employer"}
    else:
        work = {"items": list(defaults.get("work_default", [])),
                "issued": "creator"}
    return {
        "work": work,
        "casual": {"items": list(defaults.get("casual", [])),
                   "issued": "creator"},
        "formal": {"items": list(defaults.get("formal", [])),
                   "issued": "creator"},
    }


def seed_clothing_rows(store, data, character_id, item_ids,
                       outfit_context, issued, game_minutes):
    """Write one inventory row per garment, item_type "clothing".
    ``item_ids`` are clothing.json ids; an unknown id raises
    ValueError — a seeding call must never write a row whose
    item_ref resolves to no catalogue row (the CX rule). The state
    JSON carries the catalogue slot, the outfit context and who
    issued the garment ("creator" | "employer" | "household" —
    the CX shape; "household" is the school-uniform source, Unit
    AB's student loop, not seeded here). Returns the new item
    ids, in catalogue order as passed."""
    catalogue = _clothing_items(data)
    made = []
    for item_id in item_ids:
        item = catalogue.get(item_id)
        if item is None:
            raise ValueError(
                f"unknown clothing item {item_id!r}: no catalogue row")
        iid = store.next_id("INV", "inventory_items", "item_instance_id")
        store.insert("inventory_items", item_instance_id=iid,
                     item_type="clothing", item_ref=item_id,
                     owner_character_id=character_id,
                     location_property_id=None,
                     state=json.dumps({"slot": item["slot"],
                                       "outfit_context": outfit_context,
                                       "issued": issued}),
                     acquired_at_game_minutes=game_minutes)
        made.append(iid)
    return made


def seed_starting_outfits(store, data, character_id, profession_id,
                          tier, sim_tier, game_minutes):
    """Seed every starting-outfit context for a new character, in
    context order (work, casual, formal). Returns the new item ids.
    Called from ``identity.create_person`` when the caller passes
    the outfits — the genesis builder in ``population.new_person``
    is the live caller; children pass no outfits (their school
    uniform is Unit AB's student loop, not this unit)."""
    made = []
    for context, spec in starting_outfits(data, profession_id, tier,
                                          sim_tier).items():
        made.extend(seed_clothing_rows(
            store, data, character_id, spec["items"], context,
            spec["issued"], game_minutes))
    return made


def seed_uniform_rows(store, data, character_id, profession_id, tier,
                      game_minutes):
    """Seed the issued uniform for a hire (GDD-09 §5: a uniform is
    issued, not bought — no ledger charge). Called from the two
    hiring passes (``labour.match_vacancies``,
    ``admin.match_vacancies``) after the employment insert. Items
    the character already holds a standing clothing row for are
    skipped — a re-hire in the same profession does not issue a
    second set (a lost/ruined replacement is a new row by the CX
    rule, but re-hiring is not a loss). Returns the new item ids."""
    made = []
    for item_id in uniform_items(data, profession_id, tier):
        held = store.row(
            "SELECT 1 FROM inventory_items WHERE"
            " owner_character_id = ? AND item_type = 'clothing'"
            " AND item_ref = ?", (character_id, item_id))
        if held is not None:
            continue
        made.extend(seed_clothing_rows(
            store, data, character_id, [item_id], "work", "employer",
            game_minutes))
    return made


# -- Queue 17 Unit DJ: furniture / tool / document seeding ----------
# Unit DE (Queue 16) authored the three catalogues; this unit wires
# the seeding points, so the BX branches for these types can fire.
# One inventory row per piece / tool / document, item_type
# 'furniture' | 'tool' | 'document', following the CX record shape.
# The decisions this unit takes (no source decides them) are stated
# here, not hidden:
#
# - Furniture: GDD-10 §5 prices PACKAGES (F0 0, F1 2x, F2 4x, F3 7x
#   monthly rent) and the starter flat seeds at F1; no source maps
#   a property tier to a furniture tier, and no purchase point for
#   an F2/F3 upgrade exists in the sim. So every move-in seeds the
#   F1 "Basic" set — the starter-flat rule, generalised — for a
#   household whose head holds no furniture rows at all. Furniture
#   moves with the household (GDD-10 §4), so a household that
#   already holds furniture keeps it and is never re-seeded; F2/F3
#   upgrades wait for a purchase point (a later unit's job). The
#   rows are owned by the household head (the CX custody rule) and
#   carry location_property_id = the home they were seeded into.
# - Tools: a tool is the trade's instrument, issued by the employer
#   at hiring (the GDD-09 §5 uniform economics, applied by
#   analogy — no source prices or assigns tools), no ledger charge.
#   The seeded set is exactly the tools whose `professions` list in
#   data/tools.json names the hired profession; items already held
#   are skipped, as with uniforms.
# - Documents: a document row is written at the event that issues
#   it — the business licence at founding (register_business, for
#   a real-character owner only: a system-founded firm is owned by
#   SYS-MARKET, which is not a character and holds no inventory),
#   the credential at certification (Unit DN, academics.py), and
#   the property deed at purchase (Unit EN, Queue 20:
#   decisions._cand_buy_home and _cand_buy_home_mortgage seed it
#   beside the ownership update — issued, not bought, no ledger
#   charge). The DJ note that "no property purchase exists" was
#   wrong: the decision engine has bought homes since Session 01
#   (cash) and Session 04 (mortgage); EN corrects the record here
#   and wires the deed. Mission 3.2's deed reward is the same row
#   written by the Phase 6 mission system when the mission
#   completes — one helper, two call sites, one rule.

def _furniture_items(data):
    """{furniture id: catalogue row} from the loaded furniture file."""
    return {i["id"]: i for i in
            data.furniture_file.get("items", [])}


def furniture_item(data, item_id):
    """One catalogue row by id, or None (Unit ET: the purchase
    event validates against the catalogue before pricing)."""
    return _furniture_items(data).get(item_id)


def furniture_tier_items(data, furniture_tier):
    """The cumulative piece ids of a furniture tier — the tier's own
    pieces plus every lower tier's (GDD-10 §5: each tier's set is
    cumulative; F2 holds F1 + its own pieces). Unknown tier -> []."""
    tiers = data.furniture_file.get("tiers", {})
    order = ("F0", "F1", "F2", "F3")
    if furniture_tier not in order:
        return []
    out = []
    for t in order[:order.index(furniture_tier) + 1]:
        out.extend(tiers.get(t, []))
    return out


def seed_furniture_rows(store, data, character_id, item_ids,
                        furniture_tier, property_id, game_minutes,
                        allow_duplicate=False):
    """Write one inventory row per furniture piece, item_type
    "furniture", owned by the household head, located at the
    property. An unknown catalogue id raises ValueError (the CX
    rule, as with clothing). Pieces the owner already holds a
    standing furniture row for are skipped — unless
    allow_duplicate is set, in which case a second row is written:
    a purchase is not a seeding (Unit ET: the purchase event buys
    a replacement beside a lost or broken original). Returns the
    new item ids, in catalogue order as passed."""
    catalogue = _furniture_items(data)
    made = []
    for item_id in item_ids:
        item = catalogue.get(item_id)
        if item is None:
            raise ValueError(
                f"unknown furniture item {item_id!r}: no catalogue row")
        held = store.row(
            "SELECT 1 FROM inventory_items WHERE"
            " owner_character_id = ? AND item_type = 'furniture'"
            " AND item_ref = ?", (character_id, item_id))
        if held is not None and not allow_duplicate:
            continue
        iid = store.next_id("INV", "inventory_items", "item_instance_id")
        store.insert("inventory_items", item_instance_id=iid,
                     item_type="furniture", item_ref=item_id,
                     owner_character_id=character_id,
                     location_property_id=property_id,
                     state=json.dumps({"furniture_tier": furniture_tier,
                                       "condition": CONDITION_NEW}),
                     acquired_at_game_minutes=game_minutes)
        made.append(iid)
    return made


def seed_furniture_at_move_in(store, data, household_id, property_id,
                              game_minutes):
    """Seed the F1 "Basic" set at a household move-in (GDD-10 §5:
    the starter flat seeds at F1). Called from the three points a
    household takes a home — the genesis placement in
    ``population`` (households are placed by direct inserts there,
    not by ``move_household``), ``households.move_household`` and
    ``households.leave_home``. A household whose head already holds
    any furniture row is not re-seeded (furniture moves with the
    household, GDD-10 §4); a headless household seeds nothing (the
    CX custody rule). Returns the new item ids."""
    head = household_head(store, household_id)
    if head is None:
        return []
    held = store.row(
        "SELECT 1 FROM inventory_items WHERE owner_character_id = ?"
        " AND item_type = 'furniture'", (head,))
    if held is not None:
        return []
    return seed_furniture_rows(
        store, data, head, furniture_tier_items(data, "F1"), "F1",
        property_id, game_minutes)


def _tools_items(data):
    """{tool id: catalogue row} from the loaded tools file."""
    return {i["id"]: i for i in data.tools_file.get("items", [])}


def tool_items(data, profession_id):
    """The tool ids whose `professions` list names this profession
    (data/tools.json — every entry there is authored, Unit DE).
    [] when the profession carries no tool of the trade."""
    if profession_id is None:
        return []
    return [i["id"] for i in data.tools_file.get("items", [])
            if profession_id in i.get("professions", [])]


def seed_tool_rows(store, data, character_id, profession_id,
                   game_minutes):
    """Seed the trade's instruments at hiring, issued by the
    employer (no ledger charge — the GDD-09 §5 uniform rule by
    analogy, this unit's decision). Called from the two hiring
    passes beside ``seed_uniform_rows``. An unknown catalogue id
    raises ValueError; tools the character already holds are
    skipped. Returns the new item ids."""
    catalogue = _tools_items(data)
    made = []
    for item_id in tool_items(data, profession_id):
        if item_id not in catalogue:
            raise ValueError(
                f"unknown tool {item_id!r}: no catalogue row")
        held = store.row(
            "SELECT 1 FROM inventory_items WHERE"
            " owner_character_id = ? AND item_type = 'tool'"
            " AND item_ref = ?", (character_id, item_id))
        if held is not None:
            continue
        iid = store.next_id("INV", "inventory_items", "item_instance_id")
        store.insert("inventory_items", item_instance_id=iid,
                     item_type="tool", item_ref=item_id,
                     owner_character_id=character_id,
                     location_property_id=None,
                     state=json.dumps({"issued": "employer",
                                       "condition": CONDITION_NEW}),
                     acquired_at_game_minutes=game_minutes)
        made.append(iid)
    return made


def _documents_items(data):
    """{document id: catalogue row} from the loaded documents file."""
    return {i["id"]: i for i in data.documents_file.get("items", [])}


def seed_document_row(store, data, character_id, document_id,
                      game_minutes, state_extra=None):
    """Write one inventory row for a document, item_type
    "document". ``state_extra`` carries the issuing record (e.g.
    {"certification_id": ...} for a credential,
    {"business_id": ...} for a licence) so two documents of the
    same kind for different records are distinct rows. An unknown
    catalogue id raises ValueError. Refuses when the owner already
    holds a document row of the same kind with the identical state
    (the same issuing record seeded twice is a duplicate, not a
    second document). Returns the new item id, or None on refusal.
    The inventory row is the paper; the issuing record (the
    certification, the business) stands on its own — losing the
    paper loses nothing else (Unit DN's rule)."""
    catalogue = _documents_items(data)
    if document_id not in catalogue:
        raise ValueError(
            f"unknown document {document_id!r}: no catalogue row")
    state = dict(state_extra or {})
    for row in store.rows(
            "SELECT state FROM inventory_items WHERE"
            " owner_character_id = ? AND item_type = 'document'"
            " AND item_ref = ?", (character_id, document_id)):
        try:
            if json.loads(row["state"]) == state:
                return None
        except ValueError:
            continue
    iid = store.next_id("INV", "inventory_items", "item_instance_id")
    store.insert("inventory_items", item_instance_id=iid,
                 item_type="document", item_ref=document_id,
                 owner_character_id=character_id,
                 location_property_id=None,
                 state=json.dumps(state),
                 acquired_at_game_minutes=game_minutes)
    return iid


def surrender_property_deed(store, character_id, property_id):
    """Surrender the owner's property deed for a property (Unit ER,
    Queue 21 — the foreclosure-to-repurchase lifecycle, GDD-04 §3.3
    + GDD-10 §8): the paper follows the right. The deed row the
    owner still HOLDS for that property (state
    ``{"property_id": <id>}``) is deleted, so a later re-purchase
    is issued a fresh deed by ``seed_document_row()`` instead of
    being refused by its duplicate guard. A deed already lost or
    found is NOT surrendered — the paper is not in the owner's
    hands to give up, so the row stands and remains the deed of
    record (a re-purchase while it is lost is refused by the guard,
    and the returned paper serves as the deed again). Returns the
    surrendered item id, or None when no held deed stood for the
    property (no deed, or only a lost/found one). The foreclosure
    life event and the ledger preserve the history; the properties
    row is the right, and this deletes only the paper."""
    for row in store.rows(
            "SELECT * FROM inventory_items WHERE"
            " owner_character_id = ? AND item_type = 'document'"
            " AND item_ref = 'property_deed'", (character_id,)):
        try:
            state = json.loads(row["state"] or "{}")
        except ValueError:
            continue
        if state.get("property_id") != property_id:
            continue
        if _item_is_away(store, row["item_instance_id"]):
            continue
        store.execute("DELETE FROM inventory_items"
                      " WHERE item_instance_id = ?",
                      (row["item_instance_id"],))
        return row["item_instance_id"]
    return None


# -- Queue 17 Unit DK: school uniform + age-up outfits --------------
# Unit DD seeds starting outfits for genesis adults and uniforms at
# hiring, but children get no rows and adults who age up from
# childhood get none either. This unit closes both gaps.
#
# - School uniform: GDD-09 §5 — students wear `uniform_school`,
#   bought by their household (issued "household" in the CX shape,
#   outfit_context "school"). The issue point is Unit AB's student
#   loop: education.enrol_school_sweep enrols 3–17-year-olds, and
#   the uniform is seeded beside the enrolment, in the same call.
#   One set per student; a student who already holds the set is
#   not issued a second one (a lost set's replacement is a purchase
#   at the catalogue price — no purchase point exists yet, so this
#   unit does not re-issue after a loss).
# - Age-up outfits: a character born in-world reaches Young Adult
#   (18) in lifecycle.daily_check, which detects the stage
#   transition. At that transition — and only there — the character
#   is seeded the creator's three starting outfits
#   (seed_starting_outfits), with the profession/tier of their
#   current employment where one stands, else the work default.
#   The guard is "holds no starting-outfit row": a genesis adult
#   already seeded at creation is never seeded again, and the
#   school uniform (context "school") does not count as a starting
#   outfit.

def seed_school_uniform(store, data, character_id, game_minutes):
    """Seed the school uniform set for a newly enrolled student
    (GDD-09 §5: bought by the household). Returns the new item ids
    (0 or 1 — the set is a single catalogue item, slot
    `uniform_set`). Skips a student who already holds the set."""
    held = store.row(
        "SELECT 1 FROM inventory_items WHERE owner_character_id = ?"
        " AND item_type = 'clothing' AND item_ref = 'uniform_school'",
        (character_id,))
    if held is not None:
        return []
    return seed_clothing_rows(store, data, character_id,
                              ["uniform_school"], "school", "household",
                              game_minutes)


def _has_starting_outfit_rows(store, character_id):
    """True when the character holds any clothing row whose state
    names a starting-outfit context (work/casual/formal). A school
    uniform (context "school") does not count — a child who ages up
    holds a uniform and still needs starting outfits."""
    for row in store.rows(
            "SELECT state FROM inventory_items WHERE"
            " owner_character_id = ? AND item_type = 'clothing'",
            (character_id,)):
        try:
            state = json.loads(row["state"])
        except ValueError:
            continue
        if state.get("outfit_context") in ("work", "casual", "formal"):
            return True
    return False


def seed_age_up_outfits(store, data, character_id, game_minutes):
    """Seed the starting outfits at the age-up transition to Young
    Adult (18). Called from lifecycle.daily_check when the stage
    transition is detected. No-ops when the character already holds
    starting-outfit rows. Returns the new item ids."""
    if _has_starting_outfit_rows(store, character_id):
        return []
    char = store.row("SELECT sim_tier FROM characters"
                     " WHERE character_id = ?", (character_id,))
    if char is None:
        return []
    emp = store.row("SELECT profession_id, tier FROM employments"
                    " WHERE character_id = ?"
                    " AND ended_at_game_minutes IS NULL",
                    (character_id,))
    return seed_starting_outfits(
        store, data, character_id,
        emp["profession_id"] if emp else None,
        emp["tier"] if emp else 1,
        char["sim_tier"], game_minutes)


# -- Queue 19 Units EE/EF: condition & decay wiring (GDD-04 §3.3,
# Unit DQ design) -------------------------------------------------
# DQ designed the model; these functions apply it. The condition
# lives in the inventory row's `state` JSON — the same shape the
# vehicle rows already use — so no table changes anywhere. Two
# scope notes, recorded not hidden:
#
# - Only the causes each unit's brief assigns are wired here: tools
#   wear by USE (EE, −1 per worked day); furniture wears by MOVES
#   (EF, −2 per household move) and by EXPOSURE (EF, −1 per exposed
#   day). DQ's weather cause for TOOLS (−1 per exposed day) is wired
#   by Unit EG (Queue 20, below): the environment pass's exposure
#   wears the tools of characters whose home stands in an exposed
#   zone, beside the furniture wear.
# - There is no passive time decay: condition falls only on the
#   causes above (DQ). Repair is Unit EH (Queue 20, below):
#   `repair_tool()` / `repair_furniture()` restore a row to 90
#   (RESTORED_CONDITION), refusing rows already at 90+ and unknown
#   rows, with no ledger charge. A broken tool therefore stays
#   broken until it is repaired; the refusal below is the standing
#   consequence, not a dead end hidden from the docs.

def item_condition(row):
    """The condition of an inventory row (0–100), read from its
    `state` JSON. Rows seeded before Queue 19 carry no `condition`
    key (DJ seeded `{"issued": "employer"}` / `{"furniture_tier":
    "F1"}`) — a missing key reads as 100 (new, un-worn), the
    honest migration-free reading: those rows were seeded new and
    no wear pass has ever run over them. An unparseable state also
    reads 100, never 0 — wear must never break a row it cannot
    read."""
    try:
        state = json.loads(row["state"] or "{}")
    except ValueError:
        state = {}
    try:
        value = int(state.get("condition", CONDITION_NEW))
    except (TypeError, ValueError):
        return CONDITION_NEW
    return max(0, min(100, value))


def _set_condition(store, row, new_condition):
    """Write a new condition into a row's `state` JSON, keeping
    every other key (issued, furniture_tier, slot, ...)."""
    try:
        state = json.loads(row["state"] or "{}")
    except ValueError:
        state = {}
    state["condition"] = max(0, min(100, int(new_condition)))
    store.execute("UPDATE inventory_items SET state = ?"
                  " WHERE item_instance_id = ?",
                  (json.dumps(state), row["item_instance_id"]))


def _current_profession_id(store, character_id):
    """The character's current profession — the open employments
    row, latest start first. Mirrors
    ``missions.current_profession_id`` (duplicated, not imported:
    missions.py lazily imports this module, so a top-level import
    here would be circular). None when the character holds no open
    employment."""
    row = store.row(
        "SELECT profession_id FROM employments WHERE character_id = ?"
        " AND ended_at_game_minutes IS NULL"
        " ORDER BY started_at_game_minutes DESC LIMIT 1",
        (character_id,))
    return row["profession_id"] if row else None


def _profession_tool_rows(store, data, character_id):
    """The character's standing tool rows for their current
    profession — the tools whose catalogue `professions` list names
    it (DJ's seeding rule, read back). [] when the character is
    unemployed, the profession carries no tool, or no rows stand."""
    profession_id = _current_profession_id(store, character_id)
    if profession_id is None:
        return []
    wanted = set(tool_items(data, profession_id))
    if not wanted:
        return []
    return [r for r in store.rows(
        "SELECT * FROM inventory_items WHERE owner_character_id = ?"
        " AND item_type = 'tool'", (character_id,))
        if r["item_ref"] in wanted]


def broken_tools_for(store, data, character_id):
    """The character's tools of the trade at condition 0 — unusable
    (DQ): a work block that requires one is refused (the scheduler
    bend, wired in engine.run_day). [] when nothing is broken."""
    return [r for r in _profession_tool_rows(store, data, character_id)
            if item_condition(r) == 0]


def tool_needs_service(store, data, character_id):
    """The character's tools of the trade at or below the service
    threshold (DQ: condition 60 or below is due a service — the
    vehicle precedent, adopted). A broken tool (0) is included: it
    is due the repair that restores it to 90 (RESTORED_CONDITION),
    not a routine service — the predicate answers "due attention",
    and the caller distinguishes broken from worn by condition."""
    return [r for r in _profession_tool_rows(store, data, character_id)
            if item_condition(r) <= SERVICE_THRESHOLD]


def apply_tool_wear(store, data, character_id, game_minutes):
    """Apply one worked day of use to the character's tools of the
    trade (DQ: −1 per worked day). Called from engine.run_day for
    every character who worked at least one work block that day —
    the run_day hook is the only caller, so a rest day, a bent
    work block, or an unemployed character wears nothing. Each worn
    row's condition falls by 1 (floored at 0); a tool that reaches
    0 on this wear logs the `tool_broken` life event once — the
    break is the event, and the work refusal is its standing
    consequence (the scheduler bend logs nothing further, so a tool
    broken for ten days is one event, not ten). Returns the worn
    item ids."""
    from . import memory as memory_mod
    worn = []
    for row in _profession_tool_rows(store, data, character_id):
        before = item_condition(row)
        if before <= 0:
            continue
        after = before - 1
        _set_condition(store, row, after)
        worn.append(row["item_instance_id"])
        if after == 0:
            memory_mod.log_life_event(
                store, character_id, "tool_broken", game_minutes,
                details={"item_instance_id": row["item_instance_id"],
                         "item_ref": row["item_ref"]})
    return worn


def apply_furniture_move_wear(store, data, household_id, game_minutes,
                              new_property_id=None):
    """Apply one household move to the head's furniture rows (DQ:
    −2 per move — the packed load). Called from
    ``households.move_household`` BEFORE the move-in seeding, so
    newly seeded rows (new furniture, condition 100) are never
    worn by the move that furnished the home — only the furniture
    the household carried wears. A headless household wears
    nothing (the CX custody rule). When ``new_property_id`` is
    given, every carried row — worn or already broken — is
    relocated to the new home (furniture moves with the household,
    GDD-10 §4); without it, locations are left untouched. Returns
    the worn item ids."""
    head = household_head(store, household_id)
    if head is None:
        return []
    worn = []
    for row in store.rows(
            "SELECT * FROM inventory_items WHERE owner_character_id = ?"
            " AND item_type = 'furniture'", (head,)):
        before = item_condition(row)
        if before > 0:
            _set_condition(store, row, before - 2)
            worn.append(row["item_instance_id"])
        if new_property_id is not None:
            store.execute(
                "UPDATE inventory_items SET location_property_id = ?"
                " WHERE item_instance_id = ?",
                (new_property_id, row["item_instance_id"]))
    return worn


def apply_furniture_exposure_wear(store, data, zones, game_minutes):
    """Apply one exposed day to the furniture standing in the given
    zones (DQ: −1 per exposed day — the item's location is a zone
    under an active flood episode or a cyclone/severe_storm
    disaster impact; the same exposure rule the environment pass
    applies to buildings, read off the row's
    ``location_property_id`` property's district). Called from
    ``environment.daily_pass`` once per day over the union of the
    active disasters' exposed zones (Unit EP, Queue 21 — a zone
    under two simultaneous disasters is worn once, not once per
    disaster). Rows with no location are skipped — furniture without
    a home has no zone to expose. Returns the worn item ids."""
    zones = set(zones)
    if not zones:
        return []
    worn = []
    for row in store.rows(
            "SELECT * FROM inventory_items WHERE item_type ="
            " 'furniture' AND location_property_id IS NOT NULL"):
        prop = store.row("SELECT district_id FROM properties"
                         " WHERE property_id = ?",
                         (row["location_property_id"],))
        if prop is None or prop["district_id"] not in zones:
            continue
        before = item_condition(row)
        if before <= 0:
            continue
        _set_condition(store, row, before - 1)
        worn.append(row["item_instance_id"])
    return worn


def apply_tool_weather_wear(store, data, zones, game_minutes):
    """Apply one exposed day to the tools of characters whose home
    stands in the given zones (Unit EG, Queue 20 — DQ's weather
    cause for tools, the one EE/EF left unwired). The exposure is
    the same the environment pass applies to buildings and to
    furniture: the home property's district is one of the
    floodplain/wetland zones under an active flood / cyclone /
    severe_storm disaster. Each tool of the trade (the DJ seeding
    rule, read back — the same set `apply_tool_wear` wears) falls
    by 1 (floored at 0); a tool that reaches 0 on this wear logs
    the `tool_broken` life event once, exactly as work wear does —
    the break is the event, and the work refusal is its standing
    consequence. A character with no household (no home to expose)
    wears nothing; a tool already at 0 wears nothing further and
    logs no second event. Called from `environment.daily_pass`
    beside `apply_furniture_exposure_wear`, once per day over the
    union of the active disasters' exposed zones (Unit EP, Queue
    21 — a zone under two simultaneous disasters is worn once,
    not once per disaster; the per-disaster call shape the EG
    note recorded is gone).
    Returns the worn item ids."""
    from . import memory as memory_mod
    zones = set(zones)
    if not zones:
        return []
    worn = []
    for char in store.rows(
            "SELECT c.character_id, p.district_id FROM characters c"
            " JOIN households h ON h.household_id = c.household_id"
            " JOIN properties p"
            " ON p.property_id = h.home_property_id"):
        if char["district_id"] not in zones:
            continue
        for row in _profession_tool_rows(store, data,
                                         char["character_id"]):
            before = item_condition(row)
            if before <= 0:
                continue
            after = before - 1
            _set_condition(store, row, after)
            worn.append(row["item_instance_id"])
            if after == 0:
                memory_mod.log_life_event(
                    store, char["character_id"], "tool_broken",
                    game_minutes,
                    details={"item_instance_id":
                             row["item_instance_id"],
                             "item_ref": row["item_ref"],
                             "cause": "weather_exposure"})
    return worn


# -- Queue 20 Unit EH: tool & furniture repair (GDD-04 §3.3, Unit
# DQ) ------------------------------------------------------------------
# DQ prices repair (restore to 90, no ledger row — unpriced, no
# repair key in prices.json) and no repair function existed. These
# two functions are the performance: they restore one inventory
# row's condition to RESTORED_CONDITION (90), never to 100 — a
# repaired thing is not a new thing. No ledger charge and no
# invented price: repair is a world action on the row, not a
# purchase (the DQ rule, enforced by writing no ledger row at
# all). A broken row (condition 0) repairs to 90 like any other
# worn row — repair is how a broken tool becomes usable again.

def _repair(store, item_instance_id, item_type):
    """The shared repair: restore one row of the given type to
    RESTORED_CONDITION. Returns the item id, or None when refused:
    no such row, the row is of another type (a furniture row is
    not a repairable tool row), or the row's condition is already
    at or above RESTORED_CONDITION — repairing it would lower it
    (a row at 95 is better than repaired), so the repair is
    refused, not applied. The inventory row is otherwise
    untouched (its other state keys are kept)."""
    row = store.row("SELECT * FROM inventory_items"
                    " WHERE item_instance_id = ?",
                    (item_instance_id,))
    if row is None or row["item_type"] != item_type:
        return None
    if item_condition(row) >= RESTORED_CONDITION:
        return None
    _set_condition(store, row, RESTORED_CONDITION)
    return item_instance_id


def repair_tool(store, item_instance_id):
    """Restore one tool row's condition to 90 (RESTORED_CONDITION).
    Returns the item id, or None when refused: unknown row, a row
    of another type, or a row already at 90+ (including 100 — a
    new tool needs no repair). No ledger charge, no invented
    price (DQ)."""
    return _repair(store, item_instance_id, "tool")


def repair_furniture(store, item_instance_id):
    """Restore one furniture row's condition to 90
    (RESTORED_CONDITION). Returns the item id, or None when
    refused: unknown row, a row of another type, or a row already
    at 90+ (including 100). No ledger charge, no invented price
    (DQ)."""
    return _repair(store, item_instance_id, "furniture")


def monthly_repair_sweep(store, data, game_minutes):
    """Queue 21 Unit EU - the monthly tool service (GDD-04 §3.3,
    Unit EH's repair, DQ's service rule). Every living
    character's tools of the trade at or below SERVICE_THRESHOLD
    (60) - broken tools included - are repaired to
    RESTORED_CONDITION (90) with no ledger charge (the DQ price
    rule: repair writes no ledger row). The vehicle precedent,
    adopted: transport's monthly maintenance services every
    vehicle below its threshold; this services every due tool.
    The sweep services what tool_needs_service reports - the
    same rows the wear touches, lost tools included (the
    predicate's call, not the sweep's). A repair is a world
    action on the row, not a purchase: nothing is charged and no
    life event is logged (the break was the event; the repair
    lifts the scheduler's refusal the next day the tool is
    needed). Returns {"repaired": [item ids], "broken": [item
    ids repaired from condition 0]} - the row's condition is the
    record; the return is for the caller and the tests."""
    repaired = []
    broken = []
    for char in store.rows(
            "SELECT character_id FROM characters WHERE is_system = 0"
            " AND died_at_game_minutes IS NULL"
            " ORDER BY character_id"):
        cid = char["character_id"]
        for row in tool_needs_service(store, data, cid):
            was_broken = item_condition(row) == 0
            if repair_tool(store, row["item_instance_id"]) is not None:
                repaired.append(row["item_instance_id"])
                if was_broken:
                    broken.append(row["item_instance_id"])
    return {"repaired": repaired, "broken": broken}


# GDD-10 §5: the home restore multipliers follow the EFFECTIVE
# furnishing tier — the highest tier whose pieces ALL stand
# (condition > 0). A tier counts only when the household head holds
# every piece of that tier (cumulative: F1 holds F0 + F1) and each
# stands. The multipliers are GDD-10's own numbers, never copied
# from prices.json: F0 ×0.7, F1 ×1.0, F2 ×1.15, F3 ×1.3.
FURNITURE_RESTORE_MULTIPLIERS = {"F0": 0.7, "F1": 1.0,
                                 "F2": 1.15, "F3": 1.3}


def _item_is_away(store, item_instance_id):
    """True when a `lost_items` row for the item stands `lost` or
    `found` (Unit EI, Queue 20): the piece is not in the home —
    lost somewhere in the city, or in the finder's hands awaiting
    hand-back. A `returned` row is not standing, so a returned
    piece is home again."""
    return store.row(
        "SELECT 1 FROM lost_items WHERE item_instance_id = ?"
        " AND status IN ('lost', 'found')",
        (item_instance_id,)) is not None


def effective_furniture_tier(store, data, character_id):
    """The household head's effective furnishing tier (DQ): the
    highest tier whose pieces ALL stand — every piece of the tier
    (cumulative, so F1 means the F0 + F1 pieces) is held by the
    character with condition > 0 AND present in the home. A broken
    piece drops the tier to the highest tier below it that fully
    stands; a broken F0 piece leaves no tier standing, and the
    function returns None (the home loop must decide that case —
    no multiplier is invented here). A piece's absence (never
    seeded) counts the same as a broken one: the tier does not
    stand. A lost piece drops the tier too (Unit EI, Queue 20 —
    the decision EF left open): the piece is not in the home, so
    the home provides nothing from it tonight, exactly as a broken
    piece provides nothing — the drop is reversible, and the
    hand-back restores the tier, which is the §3.1 favour's
    payoff. A `found` piece still drops it (the finder holds it,
    not the home); a `returned` piece stands again. Where the
    character holds two rows of one piece (a replacement bought
    beside the original), the piece stands if ANY row stands —
    one usable piece in the home is one furnished piece."""
    held = {}
    for row in store.rows(
            "SELECT * FROM inventory_items WHERE owner_character_id = ?"
            " AND item_type = 'furniture'", (character_id,)):
        stands = item_condition(row) > 0 \
            and not _item_is_away(store, row["item_instance_id"])
        held[row["item_ref"]] = held.get(row["item_ref"], False) \
            or stands
    for tier in ("F3", "F2", "F1", "F0"):
        pieces = furniture_tier_items(data, tier)
        if pieces and all(held.get(p, False) for p in pieces):
            return tier
    return None


def furniture_restore_multiplier(store, data, character_id):
    """The GDD-10 §5 restore multiplier for the character's
    effective furnishing tier (0.7 / 1.0 / 1.15 / 1.3). None when
    no tier stands — the caller must decide that case; this module
    invents no fallback rate. The live consumer is the needs
    engine (Unit EQ, Queue 21): ``needs.apply_activity`` scales
    the rest/sleep restores of home/sleep blocks by this rate, and
    applies no scaling when it is None."""
    tier = effective_furniture_tier(store, data, character_id)
    if tier is None:
        return None
    return FURNITURE_RESTORE_MULTIPLIERS[tier]
