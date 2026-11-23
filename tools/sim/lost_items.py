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


def eligible_items(store, owner_character_id, allowed_types):
    """The owner's standing inventory rows of the allowed types, in
    loss priority: BX's listing order for the event, then
    item_instance_id. Only standing rows count — a row is never
    deleted on loss, so eligibility is simply 'the row exists'."""
    priority = {t: i for i, t in enumerate(allowed_types)}
    rows = store.rows(
        "SELECT * FROM inventory_items WHERE owner_character_id = ?",
        (owner_character_id,))
    kept = [r for r in rows if r["item_type"] in priority]
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
      again, only a standing loss blocks).

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
