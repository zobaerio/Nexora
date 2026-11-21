"""Session 02 Units 04 + 06 — Social Relationship & Interaction Engines.

Session 01's relationships carry trust/affection/respect and its
interactions happen where schedules collide. This unit gives the
social graph its full vocabulary and its dynamics:

- edge types beyond kinship: colleague (same profession, formed at
  workplace breaks), neighbour (same zone, formed at community
  gatherings), rival (formed by repeated real conflicts — never by
  a dice roll looking for drama);
- per-edge social dynamics in social_profiles: familiarity (grows
  with every encounter), conflict level (spikes on conflict
  outcomes, decays weekly), interaction count, last event. These
  are keyed to the relationship row, so a pair's history is one
  query away and survives restarts like everything else;
- strength is derived (mean of trust/affection/respect), never
  stored — one source of truth per fact, as everywhere in this sim.

Interactions update these profiles from interaction.py's actual
encounter outcomes, and the weekly neighbour gathering is a real
interaction between real co-residents: it creates neighbour edges,
moves affection, writes memories and life events — the same
machinery as every other encounter, at community scale.
"""
from . import emotions as emotions_mod
from . import memory as memory_mod
from . import relationships as rel

FAMILIARITY_GAIN = {"befriended": 5, "bonded": 4, "neutral": 2,
                    "conflict": 1, "neighbour_visit": 4,
                    "family_time": 2}
CONFLICT_SPIKE = 25
RIVALRY_THRESHOLD = 50


def strength(edge):
    """Derived relationship strength — never stored."""
    if not edge:
        return 0
    return round((edge["trust"] + edge["affection"]
                  + edge["respect"]) / 3)


def profile_of(store, relationship_id):
    return store.row("SELECT * FROM social_profiles"
                     " WHERE relationship_id = ?", (relationship_id,))


def _upsert_profile(store, relationship_id, outcome, game_minutes):
    gain = FAMILIARITY_GAIN.get(outcome, 1)
    row = profile_of(store, relationship_id)
    if row is None:
        store.insert("social_profiles", relationship_id=relationship_id,
                     familiarity=gain,
                     conflict=CONFLICT_SPIKE if outcome == "conflict"
                     else 0,
                     interaction_count=1, last_event=outcome,
                     updated_at_game_minutes=game_minutes)
    else:
        conflict = row["conflict"] + (CONFLICT_SPIKE
                                      if outcome == "conflict" else -2)
        store.execute(
            "UPDATE social_profiles SET familiarity = MIN(100,"
            " familiarity + ?), conflict = MAX(0, MIN(100, ?)),"
            " interaction_count = interaction_count + 1,"
            " last_event = ?, updated_at_game_minutes = ?"
            " WHERE relationship_id = ?",
            (gain, conflict, outcome, game_minutes, relationship_id))


def _employment_of(store, cid):
    return store.row("SELECT profession_id FROM employments"
                     " WHERE character_id = ?"
                     " AND ended_at_game_minutes IS NULL", (cid,))


def record_interaction(store, a, b, context, outcome, game_minutes):
    """Fold one real encounter into the pair's social dynamics.
    Called by interaction.py for every encounter outcome, so the
    social graph develops only through interactions that actually
    happened. Also forms colleague edges at workplace breaks and
    rival edges when conflict becomes a pattern."""
    if context == "break":
        ea, eb = _employment_of(store, a), _employment_of(store, b)
        if ea and eb and ea["profession_id"] == eb["profession_id"] \
                and not rel.get_edge(store, a, b, "colleague"):
            rel.add_edge(store, a, b, "colleague", game_minutes,
                         trust=15, affection=10, respect=20,
                         flags={"profession": ea["profession_id"]})
    for x, y in ((a, b), (b, a)):
        edges = store.rows("SELECT relationship_id FROM relationships"
                           " WHERE from_character_id = ?"
                           " AND to_character_id = ?", (x, y))
        for e in edges:
            _upsert_profile(store, e["relationship_id"], outcome,
                            game_minutes)
    if outcome == "conflict":
        _maybe_rivalry(store, a, b, game_minutes)


def _maybe_rivalry(store, a, b, game_minutes):
    """A rivalry is a pattern, not an incident: it forms only when
    the pair's measured conflict level crosses the threshold."""
    if rel.get_edge(store, a, b, "rival"):
        return
    for x, y in ((a, b), (b, a)):
        edges = store.rows("SELECT relationship_id FROM relationships"
                           " WHERE from_character_id = ?"
                           " AND to_character_id = ?", (x, y))
        for e in edges:
            prof = profile_of(store, e["relationship_id"])
            if prof and prof["conflict"] >= RIVALRY_THRESHOLD:
                rel.add_edge(store, a, b, "rival", game_minutes,
                             trust=-30, affection=-35, respect=-10)
                rel.record_history(store, a, b, "rival",
                                   "rivalry_formed", game_minutes)
                for p, q in ((a, b), (b, a)):
                    memory_mod.log_life_event(store, p, "rivalry",
                                              game_minutes,
                                              other_character_id=q)
                return


def network(store, character_id):
    """One person's whole social graph with derived strength and
    dynamics — the observation view for Unit 04."""
    out = []
    edges = store.rows("SELECT * FROM relationships"
                       " WHERE from_character_id = ?"
                       " ORDER BY relation_type, to_character_id",
                       (character_id,))
    for e in edges:
        prof = profile_of(store, e["relationship_id"])
        other = store.row("SELECT display_name FROM characters"
                          " WHERE character_id = ?",
                          (e["to_character_id"],))
        out.append({
            "to": e["to_character_id"],
            "to_name": other["display_name"] if other else None,
            "type": e["relation_type"], "trust": e["trust"],
            "affection": e["affection"], "respect": e["respect"],
            "strength": strength(e),
            "familiarity": prof["familiarity"] if prof else 0,
            "conflict": prof["conflict"] if prof else 0,
            "interactions": prof["interaction_count"] if prof else 0,
        })
    return out


def weekly_decay(store, game_minutes):
    """Conflict cools with time when nothing rekindles it — a small
    weekly decay on every profile (interaction spikes are +25, so a
    real pattern still crosses the rivalry threshold)."""
    store.execute("UPDATE social_profiles SET conflict = MAX(0,"
                  " conflict - 3), updated_at_game_minutes = ?",
                  (game_minutes,))


def neighbour_gathering(store, rng, data, game_minutes, per_zone=3):
    """Weekly community-scale interaction: in each zone, a few
    adults from different households meet as neighbours. New pairs
    gain a neighbour edge (and a life event + memory); known pairs
    deepen slightly. Deterministic under the sim seed; bounded per
    zone so the weekly cost stays flat as population grows."""
    from .identity import age_years
    zones = {}
    for h in store.rows("SELECT household_id, district_id FROM"
                        " households WHERE dissolved_at_game_minutes"
                        " IS NULL"):
        zones.setdefault(h["district_id"], []).append(h["household_id"])
    meetings = 0
    for zone in sorted(zones):
        adults = []
        for hid in sorted(zones[zone]):
            for m in store.rows(
                    "SELECT c.character_id, c.born_at_game_minutes"
                    " FROM household_members hm JOIN characters c"
                    " ON c.character_id = hm.character_id"
                    " WHERE hm.household_id = ?"
                    " AND hm.left_at_game_minutes IS NULL"
                    " AND c.died_at_game_minutes IS NULL"
                    " ORDER BY c.character_id", (hid,)):
                if age_years(m["born_at_game_minutes"],
                             game_minutes) >= 18:
                    adults.append((m["character_id"], hid))
        if len(adults) < 2:
            continue
        stream = rng.stream("neighbours", zone, game_minutes // (7 * 1440))
        order = adults[:]
        stream.shuffle(order)
        made = 0
        for i in range(0, len(order) - 1, 2):
            if made >= per_zone:
                break
            (a, ha), (b, hb) = order[i], order[i + 1]
            if ha == hb:
                continue
            is_new = not rel.get_edge(store, a, b, "neighbour")
            if is_new:
                rel.add_edge(store, a, b, "neighbour", game_minutes,
                             trust=8, affection=12, respect=10,
                             flags={"zone": zone})
                for x, y in ((a, b), (b, a)):
                    memory_mod.log_life_event(
                        store, x, "neighbour_meeting", game_minutes,
                        other_character_id=y)
                    memory_mod.record_memory(
                        store, x, "neighbour_meeting", 15, game_minutes,
                        other_character_id=y)
            rel.adjust_scores(store, a, b, game_minutes, affection=2,
                              relation_type="neighbour")
            record_interaction(store, a, b, "neighbourhood",
                               "neighbour_visit", game_minutes)
            emotions_mod.apply_event(store, a, "social_day")
            emotions_mod.apply_event(store, b, "social_day")
            meetings += 1
            made += 1
    return meetings
