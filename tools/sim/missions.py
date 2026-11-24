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

Mission 2.1 "Learn the Trade" (GDD-04 §2, Unit DO Queue 18) is the
second mission with a specified completion condition, and the second
one this writer verifies: ``verify_mission_2_1()`` checks the single
objective — skill 20 in the player's profession's primary skill —
against world state while the row is still ``active``. The primary
skill is ``primary_skills[0]`` of the player's current profession
(``data/professions.json``; GDD-11 calls the second entry the
"second primary skill", so the first entry is the primary one), read
from ``character_skills``. An unemployed player has no profession
and cannot verify; a level of 20 in the second primary skill does
not verify either. Completing 2.1 pays nothing here: its 2,000 NCr
and +10 profession reputation are credit/reputation rewards, and
paying those is the Phase 6 reward step (see above) — the row
reaches ``completed`` with ``objectives_complete`` true, and the
"Skill training (evening classes)" unlock is a Phase 6 system, not
a row this writer writes.

Mission 1.3 "Know Your Neighbours" (GDD-04 §2, Unit EB Queue 19) is
the third mission with a specified completion condition:
``verify_mission_1_3()`` checks both objectives — meet 3 neighbours
(distinct ``neighbour`` relationship edges, either direction: the
type is symmetric, so an edge is stored both ways) and help one of
them with a small task (a COMPLETED ``errands`` favour instance
whose giver is one of the met neighbours — the favour instance key
carries the giver, ``side:errands:<giver>:<minute>``). The help may
have happened before the mission was accepted: the mission system
verifies against world state, and a completed favour is a fact
about the world, not about the mission's window (the 2.1
precedent — a skill of 20 reached before accepting still
verifies). Completing 1.3 pays nothing here: its +10 relationship
(each met) and +5 district reputation are the Phase 6 reward step,
and the "Neighbour favour system" unlock is a Phase 6 system.

Mission 2.2 "Rainy Day Fund" (GDD-04 §2, Unit EC Queue 19) is the
fourth: ``verify_mission_2_2()`` checks the single objective —
save 15,000 NCr above the starting balance — against the ledger:
``store.balance()`` (the ledger balance cache) must reach the
current profession's ``starting_balance_ncr`` (GDD-03 §2, Unit W)
plus 15,000, the mission's own number. An unemployed player has
no profession and therefore no starting balance, so the condition
cannot hold. Completing 2.2 pays nothing here: its 1,500 NCr
interest bonus is the Phase 6 reward step, and the "Bank savings
account (4% annual, GDD-03 §4.4)" unlock is a Phase 6 system.

Mission 2.4 "A Friend in the City" (GDD-04 §2, Unit EJ Queue 20)
is the fifth — and the last mission with a dialogue tree to gain a
specified completion condition: ``verify_mission_2_4()`` checks
the single objective — "Raise one friendship to 40+ (trust/
affection)" — against the relationship edges: a ``friend`` edge
in either direction whose mean of trust and affection is at
least 40, the mission's own number. The mean is the dialogue
condition's own reading (GDD-15 §12.3: ``relationship_mean_min``
is the mean of trust and affection on the selected edge), and the
tree's entry node requires exactly that mean of 40 — so the
§3.6 condition and the tree's gate agree on the number, and the
condition adds only what the objective names: the edge must be
a friendship (a spouse or colleague edge at mean 40 does not
verify it — the mission is about a friend, and the tree's entry
gate is the dialogue's offer rule, not the completion rule).
Completing 2.4 pays nothing here: its +10 district reputation
and memory event are the Phase 6 reward step, and the "Friend
favour missions" unlock is a Phase 6 system. After this unit
every shipped mission tree has a §3.6 condition and a verifier.

Mission 2.3 "The Market Run" (GDD-04 §2, Unit EO Queue 21) is the
sixth: ``verify_mission_2_3()`` checks both objectives — "Buy
a week's food at Boro Bazar" (a ``household_consumption`` food row
for the character's own Rupsha household) AND "Haggle once,
successfully" (a successful ``haggle_events`` row for the
character in Boro Bazar's zone, ``d1_market`` — Unit EV, Queue
22, which built the haggle record EO recorded as missing: the
stall's asked price and the price paid are both recorded facts,
and success is paid < asked, derived, never a rate). The food
purchase may predate the mission's acceptance (a bought week's
food is a fact about the world, verified like 2.1's pre-existing
skill level), and so may the haggle (a won haggle is a fact
about the world the same way). Completing 2.3 pays nothing here:
its 500 NCr and +5 market reputation are the Phase 6 reward step,
and the "Haggling" and "Market regular status" unlocks are Phase
6 systems. After this unit every Level 1–2 mission has a §3.6
condition and a verifier (1.1/1.2 have neither a tree nor a
condition — they are not shipped mission trees, so the DS
suite's tree assertion does not cover them). Still open: no
live call site writes a haggle row yet — the haggler is the
player at a stall, and the writer is the Phase 6 dialogue/
mission runtime; the monthly shopping pass buys at shelf prices
and never haggles (recorded in GDD-04 §3.6, Queue 23).

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
# GDD-04 §2 mission 2.1: "Reach skill 20 in your profession's
# primary skill" (data/missions.json, id "2.1", one objective).
MISSION_2_1_SKILL_LEVEL = 20
# GDD-04 §2 mission 1.3: "Meet 3 neighbours" (data/missions.json,
# id "1.3", first objective) — the count is the mission's own
# number.
MISSION_1_3_NEIGHBOURS_TO_MEET = 3
# GDD-04 §2 mission 2.2: "Save 15,000 NCr above your starting
# balance" (data/missions.json, id "2.2", one objective) — the
# amount is the mission's own number.
MISSION_2_2_SAVINGS_TARGET = 15000
# GDD-04 §2 mission 2.4: "Raise one friendship to 40+
# (trust/affection)" (data/missions.json, id "2.4", one objective)
# — the threshold is the mission's own number, and the mean is the
# dialogue condition's own reading (GDD-15 §12.3).
MISSION_2_4_FRIENDSHIP_MEAN = 40
# GDD-04 §2 mission 2.3: "Buy a week's food at Boro Bazar"
# (data/missions.json, id "2.3", first objective) — the food goods
# are the two food goods of the monthly shopping pass
# (tools/sim/market.py retail_allocation: food_basket + fish).
MISSION_2_3_FOOD_GOODS = ("food_basket", "fish")
# Boro Bazar is District 1's market (data/district1-blockout.json:
# the Boro Bazar market hall sits in zone d1_market), so the city
# that contains it is Rupsha City (tools/sim/cities.py RUPSHA).
BORO_BAZAR_CITY = "rupsha_city"
# Boro Bazar's zone (data/missions.json, id "2.3" zone_ref): the
# haggle for mission 2.3 must happen here — a haggle won at
# another stall is a different market's haggle, not this mission's.
BORO_BAZAR_ZONE = "d1_market"


# GDD-04 §3.6: the missions with a specified completion condition —
# the only missions this writer verifies. A mission gains an entry
# here only when its condition is specified in GDD-04 §3.6 AND its
# verify_mission_* function exists below; the DS regression suite
# (tools/sim/tests/test_mission_progress_regression.py +
# tools/verify_queue18_ds.py) fails loudly when the registry, the
# §3.6 text, and the verifiers disagree — a mission that ships a
# verifier without a condition, or a condition without a verifier,
# breaks the suite. Every shipped mission tree now has a condition
# (Unit EJ, Queue 20, closed the last one — 2.4; Unit EO, Queue
# 21, ships the 2.3 tree and its condition together, so the
# invariant holds for the new tree too).
CONDITIONED_MISSIONS = {
    "1.3": "verify_mission_1_3",
    "1.4": "verify_mission_1_4",
    "2.1": "verify_mission_2_1",
    "2.2": "verify_mission_2_2",
    "2.3": "verify_mission_2_3",
    "2.4": "verify_mission_2_4",
}


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


def primary_skill_of(data, profession_id):
    """The primary skill of a profession — ``primary_skills[0]`` in
    data/professions.json. GDD-11 calls the second entry the "second
    primary skill" (the teacher's ``subject_knowledge``), so the
    first entry is the primary one; GDD-03 §2's promotion rule reads
    the same slot ("skill 40 in the profession's primary skill").
    None when the profession is unknown or lists no skills."""
    prof = data.professions.get(profession_id)
    if not prof:
        return None
    skills = prof.get("primary_skills") or []
    return skills[0] if skills else None


def current_profession_id(store, character_id):
    """The character's current profession — the open employments row
    (``ended_at_game_minutes IS NULL``), latest start first. None
    when the character holds no open employment."""
    row = store.row(
        "SELECT profession_id FROM employments WHERE character_id = ?"
        " AND ended_at_game_minutes IS NULL"
        " ORDER BY started_at_game_minutes DESC LIMIT 1",
        (character_id,))
    return row["profession_id"] if row else None


def verify_mission_2_1(store, data, character_id, game_minutes):
    """Verify mission 2.1's objective against world state (GDD-04
    §3.6, Unit DO): the single objective "Reach skill 20 in your
    profession's primary skill" holds iff the character's current
    profession (open employments row) has a primary skill whose
    ``character_skills`` level is at least 20. On success sets
    ``objectives_complete`` while the row is still `active` and
    returns True. Returns False when the row is not `active`, the
    character is unemployed (no profession, so no primary skill),
    the profession names no primary skill, or the level is below
    20 — including a level of 20 in the profession's *second*
    primary skill, which is a different skill and does not verify.
    Skill levels are read through ``decisions.skill_level`` (the
    same read the decision engine uses); the threshold is the
    mission's own number (``MISSION_2_1_SKILL_LEVEL``), not a
    tuning call."""
    from . import decisions as decisions_mod
    row = get_row(store, character_id, "2.1")
    if row is None or row["status"] != "active":
        return False
    profession_id = current_profession_id(store, character_id)
    if profession_id is None:
        return False
    skill_id = primary_skill_of(data, profession_id)
    if skill_id is None:
        return False
    if decisions_mod.skill_level(store, character_id, skill_id) \
            < MISSION_2_1_SKILL_LEVEL:
        return False
    return set_objectives_complete(store, character_id, "2.1",
                                   game_minutes)


def neighbours_of(store, character_id):
    """The character's met neighbours — distinct characters joined
    to them by a ``neighbour`` relationship edge in either
    direction. The type is symmetric (relationships.SYMMETRIC), so
    the live writer stores both directions; the union read covers
    hand-built rows that carry one direction only. An empty set
    when the character has met no neighbour."""
    rows = store.rows(
        "SELECT to_character_id AS other FROM relationships"
        " WHERE from_character_id = ? AND relation_type = 'neighbour'"
        " UNION SELECT from_character_id AS other FROM relationships"
        " WHERE to_character_id = ? AND relation_type = 'neighbour'",
        (character_id, character_id))
    return {r["other"] for r in rows}


def verify_mission_1_3(store, data, character_id, game_minutes):
    """Verify mission 1.3's objectives against world state (GDD-04
    §3.6, Unit EB): (1) the character has met at least 3 neighbours
    (distinct ``neighbour`` edges); (2) the character has helped
    one of those neighbours with a small task — a COMPLETED
    ``errands`` favour instance (``side:errands:<giver>:<minute>``)
    whose giver is one of the met neighbours. Both must hold, in
    either order; the help may predate the mission's acceptance (a
    completed favour is a fact about the world, verified like 2.1's
    pre-existing skill level). On success sets
    ``objectives_complete`` while the row is still `active` and
    returns True. Returns False when the row is not `active`, fewer
    than 3 neighbours are met, or no completed errand names a met
    neighbour as its giver — including a completed errand for a
    stranger, which is a different neighbour's help, not this
    mission's."""
    row = get_row(store, character_id, "1.3")
    if row is None or row["status"] != "active":
        return False
    neighbours = neighbours_of(store, character_id)
    if len(neighbours) < MISSION_1_3_NEIGHBOURS_TO_MEET:
        return False
    for favour in store.rows(
            "SELECT mission_id FROM mission_progress"
            " WHERE character_id = ? AND status = 'completed'"
            " AND mission_id LIKE 'side:errands:%'",
            (character_id,)):
        parts = favour["mission_id"].split(":")
        if len(parts) == 4 and parts[2] in neighbours:
            return set_objectives_complete(store, character_id, "1.3",
                                           game_minutes)
    return False


def starting_balance_of(data, profession_id):
    """The profession's ``starting_balance_ncr`` (data/professions.
    json; GDD-03 §2, Unit W — the per-profession starting balance,
    sized from the simulator's month-1 dip). None when the
    profession is unknown or carries none."""
    prof = data.professions.get(profession_id)
    if not prof:
        return None
    return prof.get("starting_balance_ncr")


def verify_mission_2_2(store, data, character_id, game_minutes):
    """Verify mission 2.2's objective against world state (GDD-04
    §3.6, Unit EC): the single objective "Save 15,000 NCr above
    your starting balance" holds iff the character's ledger balance
    (``store.balance()``, the ledger balance cache) is at least the
    current profession's ``starting_balance_ncr`` plus 15,000, the
    mission's own number. On success sets ``objectives_complete``
    while the row is still `active` and returns True. Returns False
    when the row is not `active`, the character is unemployed (no
    profession, so no starting balance), the profession names no
    starting balance, or the balance is short — including a balance
    exactly 15,000 above a DIFFERENT profession's starting balance,
    which is not this character's. The 1,500 NCr interest bonus is
    not paid here (the Phase 6 reward step, per the DL boundary)."""
    row = get_row(store, character_id, "2.2")
    if row is None or row["status"] != "active":
        return False
    profession_id = current_profession_id(store, character_id)
    if profession_id is None:
        return False
    starting = starting_balance_of(data, profession_id)
    if starting is None:
        return False
    if store.balance(character_id) \
            < starting + MISSION_2_2_SAVINGS_TARGET:
        return False
    return set_objectives_complete(store, character_id, "2.2",
                                   game_minutes)


def household_of(store, character_id):
    """The character's household — the ``household_members`` row
    with ``left_at_game_minutes IS NULL`` (the live membership).
    None when the character belongs to no household — a character
    with no household has no household shopping to read."""
    row = store.row(
        "SELECT household_id FROM household_members"
        " WHERE character_id = ? AND left_at_game_minutes IS NULL",
        (character_id,))
    return row["household_id"] if row else None


def household_bought_food(store, household_id):
    """Whether the household has bought food — a
    ``household_consumption`` row stands for it with a food good
    (``food_basket`` or ``fish``, the monthly shopping pass's food
    goods) and units > 0. A row with 0 units is an unmet want, not
    a purchase: the row records the covered share, and 0 means the
    household got nothing. A clothing row (``clothing_set``) is a
    different good and does not count — the mission is food."""
    return store.row(
        "SELECT 1 FROM household_consumption WHERE household_id = ?"
        " AND good_id IN ('food_basket', 'fish') AND units > 0"
        " LIMIT 1",
        (household_id,)) is not None


def verify_mission_2_3(store, data, character_id, game_minutes):
    """Verify mission 2.3's objectives against world state
    (GDD-04 §3.6, Unit EO + Unit EV): (1) "Buy a week's food at
    Boro Bazar" holds iff the character's household has a
    ``household_consumption`` row with a food good and units > 0
    (``household_bought_food()``) AND the household's city is
    Rupsha City (``cities.city_of_zone()`` on the household's
    ``district_id`` — Boro Bazar is District 1's market, so a
    Shibnagar household's food comes from Shibnagar's shelves,
    not Boro Bazar, and does not verify); (2) "Haggle once,
    successfully" holds iff the character has a successful haggle
    on record in Boro Bazar's zone (``market.has_successful_
    haggle()`` on ``d1_market`` — the mission's zone_ref; a
    successful haggle is a ``haggle_events`` row with outcome
    'success', paid less than asked). Both must hold, in either
    order. On success sets ``objectives_complete`` while the row
    is still `active` and returns True. Returns False when the row
    is not `active`, the character has no household, the household
    is not in Rupsha City, or no food row stands for it — including
    a food row for a DIFFERENT household, which is not this
    character's shopping — or when no successful haggle stands for
    the character in Boro Bazar — including a successful haggle in
    another zone, a failed haggle (paid the asked price), or a
    successful haggle by another character. The food purchase and
    the haggle may predate the mission's acceptance (a bought
    week's food and a won haggle are facts about the world,
    verified like 2.1's pre-existing skill level). The 500 NCr
    and +5 market reputation are not paid here (the Phase 6
    reward step, per the DL boundary)."""
    from . import cities as cities_mod
    from . import market as market_mod
    row = get_row(store, character_id, "2.3")
    if row is None or row["status"] != "active":
        return False
    household_id = household_of(store, character_id)
    if household_id is None:
        return False
    household = store.row(
        "SELECT * FROM households WHERE household_id = ?",
        (household_id,))
    if household is None:
        return False
    if cities_mod.city_of_zone(data, household["district_id"]) \
            != BORO_BAZAR_CITY:
        return False
    if not household_bought_food(store, household_id):
        return False
    if not market_mod.has_successful_haggle(store, character_id,
                                            BORO_BAZAR_ZONE):
        return False
    return set_objectives_complete(store, character_id, "2.3",
                                   game_minutes)


def friendship_mean(store, character_id, other_id):
    """The mean of trust and affection on the `friend` edge between
    two characters (GDD-15 §12.3: `relationship_mean_min` is the
    mean of trust and affection). The type is symmetric, so the
    live writer stores both directions; this reads the union of
    both directions and takes the higher mean where both exist
    (they carry the same scores when written by `add_edge` with
    both_ways, and a hand-built one-direction row still counts).
    None when no `friend` edge joins the pair in either direction
    — a spouse, colleague, or neighbour edge is not a friendship,
    however warm it is."""
    best = None
    for row in store.rows(
            "SELECT trust, affection FROM relationships WHERE"
            " relation_type = 'friend' AND ((from_character_id = ?"
            " AND to_character_id = ?) OR (from_character_id = ?"
            " AND to_character_id = ?))",
            (character_id, other_id, other_id, character_id)):
        mean = (row["trust"] + row["affection"]) / 2
        best = mean if best is None else max(best, mean)
    return best


def verify_mission_2_4(store, data, character_id, game_minutes):
    """Verify mission 2.4's objective against world state (GDD-04
    §3.6, Unit EJ): the single objective "Raise one friendship to
    40+ (trust/affection)" holds iff the character holds a
    `friend` edge whose mean of trust and affection is at least
    40, the mission's own number. On success sets
    ``objectives_complete`` while the row is still `active` and
    returns True. Returns False when the row is not `active`, no
    `friend` edge reaches a mean of 40 — including a spouse or
    colleague edge at mean 40+, which is a different relationship,
    not a friendship — or the mean falls short (trust 45 /
    affection 34 is a mean of 39.5, not 40). The friendship may
    predate the mission's acceptance (a warm friendship is a fact
    about the world, verified like 2.1's pre-existing skill level
    and 1.3's pre-existing help). The +10 district reputation and
    the memory event are not paid here (the Phase 6 reward step,
    per the DL boundary)."""
    row = get_row(store, character_id, "2.4")
    if row is None or row["status"] != "active":
        return False
    for other in store.rows(
            "SELECT to_character_id AS other FROM relationships"
            " WHERE from_character_id = ?"
            " AND relation_type = 'friend'"
            " UNION SELECT from_character_id AS other FROM"
            " relationships WHERE to_character_id = ?"
            " AND relation_type = 'friend'",
            (character_id, character_id)):
        mean = friendship_mean(store, character_id,
                               other["other"])
        if mean is not None \
                and mean >= MISSION_2_4_FRIENDSHIP_MEAN:
            return set_objectives_complete(store, character_id,
                                           "2.4", game_minutes)
    return False


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
    favour, not two) or when the giver is deceased or unknown
    (Unit EK, Queue 20 — DP's rule, enforced not just stated: a
    deceased giver cannot offer a favour, so the generator must
    never offer a lost-item favour — or any favour — for a giver
    who has died; a living giver is unaffected)."""
    types = [s["type"] for s in
             data.missions_file.get("side_mission_types", [])]
    if favour_type not in types:
        raise ValueError(
            f"unknown favour type {favour_type!r}: not a §3.1 type")
    giver = store.row("SELECT died_at_game_minutes FROM characters"
                      " WHERE character_id = ?",
                      (giver_character_id,))
    if giver is None or giver["died_at_game_minutes"] is not None:
        return None
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
