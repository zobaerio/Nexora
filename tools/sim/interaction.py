"""Unit 10 — Human Interaction Engine.

Interactions happen where the simulation actually puts people:
agents whose schedule blocks start at the same time, in the same
zone, at the same anchor (a tea stall at break, the riverfront at
leisure, the market on an errand) meet. Outcomes are driven by
personality compatibility (Unit 02) plus seeded variation:

- a good conversation raises affection/trust on the pair's edges and
  can create a friendship — a new persistent edge, a memory, an
  emotional effect (loneliness down);
- a bad one between impatient people becomes a conflict — scores
  fall, anger/stress rise, and Full-tier agents remember it;
- household members sharing home time drift closer (family time).

Ambient-tier agents never appear here: they have no inner life to
interact with (GDD-06 §2), and this engine does not pretend
otherwise.
"""
from . import emotions as emotions_mod
from . import memory as memory_mod
from . import personality as personality_mod
from . import relationships as rel
from . import social as social_mod

INTERACTION_ACTIVITIES = ("leisure", "break", "errand")


def _strongest_edge_type(store, a, b):
    for t in ("spouse", "partner", "friend", "parent", "child",
              "sibling", "acquaintance"):
        if rel.get_edge(store, a, b, t):
            return t
    return None


def interact_pair(store, rng, a, b, context, game_minutes):
    """One encounter between two co-located agents. Returns the
    outcome label: 'bonded', 'befriended', 'conflict', or 'neutral'."""
    pa = personality_mod.get_profile(store, a)
    pb = personality_mod.get_profile(store, b)
    if pa is None or pb is None:
        return "neutral"
    compat = personality_mod.compatibility(pa, pb)
    roll = rng.stream("interact", a, b, game_minutes // 60)
    score = compat + roll.uniform(-15, 15)
    edge_type = _strongest_edge_type(store, a, b)
    if score >= 55:
        if edge_type is None:
            rel.add_edge(store, a, b, "acquaintance", game_minutes,
                         trust=10, affection=15, respect=10)
            edge_type = "acquaintance"
        rel.adjust_scores(store, a, b, game_minutes, trust=3,
                          affection=5, relation_type=edge_type)
        edge = rel.get_edge(store, a, b, edge_type)
        if edge_type == "acquaintance" and edge and edge["affection"] >= 30:
            rel.add_edge(store, a, b, "friend", game_minutes, trust=20,
                         affection=edge["affection"], respect=15)
            for x, y in ((a, b), (b, a)):
                memory_mod.record_memory(store, x, "new_friend", 35,
                                         game_minutes, other_character_id=y)
                emotions_mod.apply_event(store, x, "new_friend")
                memory_mod.log_life_event(store, x, "new_friend",
                                          game_minutes,
                                          other_character_id=y)
            social_mod.record_interaction(store, a, b, context,
                                          "befriended", game_minutes)
            return "befriended"
        emotions_mod.apply_event(store, a, "friendship_deepened")
        emotions_mod.apply_event(store, b, "friendship_deepened")
        _maybe_partnership(store, a, b, game_minutes)
        social_mod.record_interaction(store, a, b, context, "bonded",
                                      game_minutes)
        return "bonded"
    if score <= 22 and (pa["patience"] < 40 or pb["patience"] < 40):
        if edge_type:
            rel.adjust_scores(store, a, b, game_minutes, trust=-4,
                              affection=-6, relation_type=edge_type)
        for x, y in ((a, b), (b, a)):
            emotions_mod.apply_event(store, x, "conflict")
            memory_mod.record_memory(store, x, "conflict", -25,
                                     game_minutes, other_character_id=y)
        social_mod.record_interaction(store, a, b, context, "conflict",
                                      game_minutes)
        return "conflict"
    if edge_type:
        rel.adjust_scores(store, a, b, game_minutes, affection=1,
                          relation_type=edge_type)
    social_mod.record_interaction(store, a, b, context, "neutral",
                                  game_minutes)
    return "neutral"


def _maybe_partnership(store, a, b, game_minutes):
    """Dating: a deep friendship between two unmarried adults can
    become a partnership — the edge the decision engine's marriage
    candidate reads. Both directions of the friend edge must be
    warm; this is formation by accumulated interaction, not a dice
    roll at a wedding."""
    from .identity import age_years
    if rel.spouse_of(store, a) or rel.spouse_of(store, b):
        return
    if rel.get_edge(store, a, b, "partner"):
        return
    friend = rel.get_edge(store, a, b, "friend")
    if not friend or friend["affection"] < 55:
        return
    world = store.world()
    now = world["game_minutes"] if world else game_minutes
    for cid in (a, b):
        char = store.row("SELECT born_at_game_minutes, sex FROM characters"
                         " WHERE character_id = ?", (cid,))
        age = age_years(char["born_at_game_minutes"], now)
        if age < 18 or age > 50:
            return
    sexes = {store.row("SELECT sex FROM characters WHERE character_id = ?",
                       (cid,))["sex"] for cid in (a, b)}
    if len(sexes) != 2:
        return
    rel.add_edge(store, a, b, "partner", game_minutes, trust=35,
                 affection=friend["affection"], respect=30)
    for x, y in ((a, b), (b, a)):
        memory_mod.log_life_event(store, x, "partnership", game_minutes,
                                  other_character_id=y)
        memory_mod.record_memory(store, x, "partnership", 40, game_minutes,
                                 other_character_id=y)


def process_group(store, rng, member_ids, context, game_minutes,
                  max_pairs=6):
    """Pair up a co-located group (deterministic order, seeded
    pairing) and run their encounters. Returns outcome counts."""
    ids = sorted(set(member_ids))
    if len(ids) < 2:
        return {}
    stream = rng.stream("group", context, game_minutes // 60, ids[0])
    order = ids[:]
    stream.shuffle(order)
    outcomes = {}
    pairs = 0
    for i in range(0, len(order) - 1, 2):
        if pairs >= max_pairs:
            break
        result = interact_pair(store, rng, order[i], order[i + 1],
                               context, game_minutes)
        outcomes[result] = outcomes.get(result, 0) + 1
        pairs += 1
    return outcomes


def household_time(store, household_id, game_minutes):
    """Family members at home together: small daily affection gains
    on kinship edges (the weekly drift in relationships.py pulls
    spouses back toward baseline, so this cannot inflate forever)."""
    members = store.rows(
        "SELECT character_id FROM household_members WHERE household_id"
        " = ? AND left_at_game_minutes IS NULL", (household_id,))
    ids = [m["character_id"] for m in members]
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            for t in ("spouse", "parent", "child", "sibling"):
                if rel.get_edge(store, a, b, t):
                    rel.adjust_scores(store, a, b, game_minutes,
                                      affection=1, relation_type=t)
                    social_mod.record_interaction(
                        store, a, b, "home", "family_time", game_minutes)
                    break
