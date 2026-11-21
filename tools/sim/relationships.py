"""Unit 07 — Family & Relationship Engine.

Relationships are persistent, directional rows (schema.sql's
relationships table): trust / affection / respect in -100..100, a
flags JSON that is the *semantic memory* of the pair (met_at,
worked_with...), and a last-interaction stamp. Convention:
relation_type names the FROM character's role toward TO — a parent
edge is stored from=parent, to=child, type='parent'. Symmetric
relations (spouse, sibling, friend, partner) are stored in both
directions so either side can be read directly.

This engine owns the family lifecycle events that are relationships
changing shape: marriage (two households merge), childbirth (a new
identity joins the family graph), and the slow drift of bonds between
interactions. Every change is also a life event (Unit 03's log) and,
for Full-tier characters, an episodic memory — relationships are
never silent numbers.
"""
import json

from . import emotions as emotions_mod
from . import memory as memory_mod

SYMMETRIC = ("spouse", "sibling", "friend", "partner",
             "colleague", "neighbour", "rival")


def _clamp(v):
    return max(-100, min(100, round(v)))


def get_edge(store, a, b, relation_type):
    return store.row(
        "SELECT * FROM relationships WHERE from_character_id = ?"
        " AND to_character_id = ? AND relation_type = ?",
        (a, b, relation_type))


def add_edge(store, a, b, relation_type, game_minutes, trust=0,
             affection=0, respect=0, flags=None, both_ways=None):
    """Create an edge (and its mirror for symmetric types). Existing
    edges are returned unchanged — kinship is written once."""
    if both_ways is None:
        both_ways = relation_type in SYMMETRIC
    existing = get_edge(store, a, b, relation_type)
    if existing:
        return existing["relationship_id"]
    rid = store.next_id("RL", "relationships", "relationship_id")
    store.insert("relationships", relationship_id=rid,
                 from_character_id=a, to_character_id=b,
                 relation_type=relation_type, trust=_clamp(trust),
                 affection=_clamp(affection), respect=_clamp(respect),
                 flags=json.dumps(flags or {}),
                 last_interaction_at_game_minutes=game_minutes,
                 created_at_game_minutes=game_minutes)
    record_history(store, a, b, relation_type, "formed", game_minutes,
                   relationship_id=rid, flags=flags)
    if both_ways and a != b:
        rid2 = store.next_id("RL", "relationships", "relationship_id")
        store.insert("relationships", relationship_id=rid2,
                     from_character_id=b, to_character_id=a,
                     relation_type=relation_type, trust=_clamp(trust),
                     affection=_clamp(affection),
                     respect=_clamp(respect),
                     flags=json.dumps(flags or {}),
                     last_interaction_at_game_minutes=game_minutes,
                     created_at_game_minutes=game_minutes)
        record_history(store, b, a, relation_type, "formed",
                       game_minutes, relationship_id=rid2, flags=flags)
    return rid


def record_history(store, a, b, relation_type, event, game_minutes,
                   relationship_id=None, details=None, flags=None):
    """Session 02 Unit 01: every relationship carries a history —
    formation, status changes, endings — in relationship_history.
    Formation is recorded by add_edge itself; later status changes
    (conflict, mediation, adoption...) call this directly."""
    hid = store.next_id("RH", "relationship_history", "history_id")
    det = dict(details or {})
    if flags:
        det["flags"] = flags
    store.insert("relationship_history", history_id=hid,
                 relationship_id=relationship_id,
                 from_character_id=a, to_character_id=b,
                 relation_type=relation_type, event=event,
                 details=json.dumps(det), game_minutes=game_minutes)
    return hid


def history_of(store, a, b=None):
    """The recorded history of one character's relationships (or of
    one pair), oldest first."""
    if b is not None:
        return store.rows(
            "SELECT * FROM relationship_history WHERE"
            " ((from_character_id = ? AND to_character_id = ?)"
            " OR (from_character_id = ? AND to_character_id = ?))"
            " ORDER BY game_minutes, history_id", (a, b, b, a))
    return store.rows(
        "SELECT * FROM relationship_history WHERE from_character_id = ?"
        " OR to_character_id = ? ORDER BY game_minutes, history_id",
        (a, a))


def adjust_scores(store, a, b, game_minutes, trust=0, affection=0,
                  respect=0, relation_type=None):
    """Move the scores on every edge a->b (or one type). Both
    directions are adjusted for symmetric types so the pair stays
    coherent; asymmetric kinship (parent/child) adjusts one way —
    a parent's affection for a child and the child's for the parent
    are genuinely different numbers."""
    sql = ("SELECT relationship_id, relation_type FROM relationships"
           " WHERE from_character_id = ? AND to_character_id = ?")
    params = [a, b]
    if relation_type:
        sql += " AND relation_type = ?"
        params.append(relation_type)
    edges = store.rows(sql, tuple(params))
    for e in edges:
        store.execute(
            "UPDATE relationships SET trust = MAX(-100, MIN(100,"
            " trust + ?)), affection = MAX(-100, MIN(100, affection + ?)),"
            " respect = MAX(-100, MIN(100, respect + ?)),"
            " last_interaction_at_game_minutes = ?"
            " WHERE relationship_id = ?",
            (trust, affection, respect, game_minutes,
             e["relationship_id"]))
        if e["relation_type"] in SYMMETRIC:
            store.execute(
                "UPDATE relationships SET trust = MAX(-100, MIN(100,"
                " trust + ?)), affection = MAX(-100, MIN(100,"
                " affection + ?)), respect = MAX(-100, MIN(100,"
                " respect + ?)),"
                " last_interaction_at_game_minutes = ?"
                " WHERE from_character_id = ? AND to_character_id = ?"
                " AND relation_type = ?",
                (trust, affection, respect, game_minutes, b, a,
                 e["relation_type"]))


def set_flag(store, a, b, relation_type, key, value):
    """Semantic memory: a permanent fact about the pair, stored on
    the edge itself (GDD-01 §2.3)."""
    edge = get_edge(store, a, b, relation_type)
    if not edge:
        return
    flags = json.loads(edge["flags"])
    flags[key] = value
    store.execute("UPDATE relationships SET flags = ?"
                  " WHERE relationship_id = ?",
                  (json.dumps(flags), edge["relationship_id"]))


def get_flag(store, a, b, relation_type, key, default=None):
    edge = get_edge(store, a, b, relation_type)
    if not edge:
        return default
    return json.loads(edge["flags"]).get(key, default)


# -- kinship queries ---------------------------------------------------------

def _others(store, cid, relation_type, direction):
    if direction == "from":  # cid plays relation_type toward others
        rows = store.rows(
            "SELECT to_character_id AS other FROM relationships"
            " WHERE from_character_id = ? AND relation_type = ?",
            (cid, relation_type))
    else:  # others play relation_type toward cid
        rows = store.rows(
            "SELECT from_character_id AS other FROM relationships"
            " WHERE to_character_id = ? AND relation_type = ?",
            (cid, relation_type))
    return [r["other"] for r in rows]


def children_of(store, cid):
    return _others(store, cid, "parent", "from")


def parents_of(store, cid):
    return _others(store, cid, "parent", "to")


def spouse_of(store, cid):
    out = _others(store, cid, "spouse", "from")
    return out[0] if out else None


def siblings_of(store, cid):
    return _others(store, cid, "sibling", "from")


def friends_of(store, cid):
    return _others(store, cid, "friend", "from")


def family_of(store, cid):
    fam = set(children_of(store, cid)) | set(parents_of(store, cid))
    fam |= set(siblings_of(store, cid))
    sp = spouse_of(store, cid)
    if sp:
        fam.add(sp)
    return sorted(fam)


# -- family formation ---------------------------------------------------------

def marry(store, a, b, game_minutes):
    """Marriage: spouse edges, life events, memories, emotions — and
    a household merge (the partner from the smaller household moves;
    GDD-10's household is the shared expense pool)."""
    add_edge(store, a, b, "spouse", game_minutes, trust=45, affection=65,
             respect=45, flags={"married_at": game_minutes})
    for x, y in ((a, b), (b, a)):
        memory_mod.log_life_event(store, x, "marriage", game_minutes,
                                  other_character_id=y)
        memory_mod.record_memory(store, x, "marriage", 90, game_minutes,
                                 other_character_id=y)
        emotions_mod.apply_event(store, x, "marriage")
    ca = store.row("SELECT household_id FROM characters"
                   " WHERE character_id = ?", (a,))
    cb = store.row("SELECT household_id FROM characters"
                   " WHERE character_id = ?", (b,))
    if ca and cb and ca["household_id"] and cb["household_id"] \
            and ca["household_id"] != cb["household_id"]:
        def size(hid):
            return store.row(
                "SELECT COUNT(*) AS n FROM household_members"
                " WHERE household_id = ? AND left_at_game_minutes"
                " IS NULL", (hid,))["n"]
        if size(ca["household_id"]) >= size(cb["household_id"]):
            keep, move_from, mover = ca["household_id"], cb["household_id"], b
        else:
            keep, move_from, mover = cb["household_id"], ca["household_id"], a
        _move_household_member(store, mover, move_from, keep, game_minutes)
    return True


def _move_household_member(store, character_id, from_hid, to_hid,
                           game_minutes):
    store.execute("UPDATE household_members SET left_at_game_minutes = ?"
                  " WHERE household_id = ? AND character_id = ?"
                  " AND left_at_game_minutes IS NULL",
                  (game_minutes, from_hid, character_id))
    store.insert("household_members", household_id=to_hid,
                 character_id=character_id, role="member",
                 joined_at_game_minutes=game_minutes)
    store.execute("UPDATE characters SET household_id = ?"
                  " WHERE character_id = ?", (to_hid, character_id))
    remaining = store.row(
        "SELECT COUNT(*) AS n FROM household_members WHERE household_id"
        " = ? AND left_at_game_minutes IS NULL", (from_hid,))["n"]
    if remaining == 0:
        store.execute("UPDATE households SET dissolved_at_game_minutes = ?"
                      " WHERE household_id = ?", (game_minutes, from_hid))


def have_child(store, rng, parent_a, parent_b, game_minutes, used_names):
    """Childbirth: a brand-new persistent identity (Unit 01) joins
    the family graph — parent edges both ways, sibling edges to
    existing children, household membership, and the parents'
    memories/emotions. Returns the child's character_id."""
    from . import identity as identity_mod
    sex = "male" if rng.stream("birthsex", parent_a,
                               game_minutes).random() < 0.5 else "female"
    first, _ = identity_mod.pick_name(rng.stream("birthname", parent_a,
                                                 game_minutes), sex,
                                      used_names)
    pa = store.row("SELECT last_name, household_id FROM characters"
                   " WHERE character_id = ?", (parent_a,))
    child_id = identity_mod.create_person(
        store, rng, first_name=first, last_name=pa["last_name"], sex=sex,
        born_at_game_minutes=game_minutes,
        household_id=pa["household_id"], sim_tier="full",
        family_background={"parents": [parent_a, parent_b]},
        game_minutes=game_minutes)
    if pa["household_id"]:
        store.insert("household_members", household_id=pa["household_id"],
                     character_id=child_id, role="child",
                     joined_at_game_minutes=game_minutes)
    for parent in (parent_a, parent_b):
        if parent:
            add_edge(store, parent, child_id, "parent", game_minutes,
                     trust=60, affection=85, respect=30, both_ways=False)
            add_edge(store, child_id, parent, "child", game_minutes,
                     trust=70, affection=80, respect=50, both_ways=False)
            memory_mod.log_life_event(store, parent, "childbirth",
                                      game_minutes,
                                      other_character_id=child_id)
            memory_mod.record_memory(store, parent, "childbirth", 95,
                                     game_minutes,
                                     other_character_id=child_id)
            emotions_mod.apply_event(store, parent, "childbirth")
    for sib in children_of(store, parent_a):
        if sib != child_id:
            add_edge(store, child_id, sib, "sibling", game_minutes,
                     trust=40, affection=55, respect=30)
    memory_mod.log_life_event(store, child_id, "birth", game_minutes,
                              details={"parents": [parent_a, parent_b]})
    return child_id


def weekly_drift(store, game_minutes):
    """Bonds settle slowly between interactions: spouse affection
    regresses toward a warm baseline, friendships cool without
    contact. Runs weekly; tiny by design (GDD-01 relationship drift)."""
    edges = store.rows(
        "SELECT relationship_id, relation_type, affection FROM"
        " relationships WHERE relation_type IN ('spouse', 'friend')")
    for e in edges:
        target = 60 if e["relation_type"] == "spouse" else 25
        delta = (target - e["affection"]) * 0.03
        if abs(delta) >= 0.5:
            store.execute(
                "UPDATE relationships SET affection = MAX(-100,"
                " MIN(100, affection + ?)) WHERE relationship_id = ?",
                (round(delta), e["relationship_id"]))
