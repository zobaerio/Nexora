"""Session 02 Unit 12 — Generational Development.

A civilization is what survives its founders. This unit makes the
family graph *historical*:

- generation index: founders (no parents in the sim) are
  generation 1; a child is one past their highest parent. Derived
  from the parent graph on every query — like Unit 01's kinship,
  it is computed, so it can never disagree with the graph;
- lineage: ancestors and descendants by breadth-first walk over
  the same edges, for the observation surface;
- generational_history: the persisted record — a lineage_birth row
  for every birth (with its generation), an inheritance row for
  every inheritance Session 01's death cascade pays out, and a
  knowledge_transfer row whenever an elder teaches a child of the
  household (the culture profile's parameters: who counts as an
  elder, how much passes per month — Unit 07's configuration).

Knowledge transfer is real teaching: the child gains experience in
the elder's strongest skill (or the school foundation skill),
through the same capped accrual education uses — an elder who was
a doctor passes medicine, a teacher passes subject knowledge, and
the school cap still binds what schooling-shaped knowledge can do.
"""
from . import culture as culture_mod
from . import decisions as decisions_mod
from . import education as education_mod
from . import memory as memory_mod
from . import relationships as rel


def generation_of(store, character_id, _seen=None):
    _seen = _seen or set()
    if character_id in _seen:
        return 1
    _seen.add(character_id)
    parents = rel.parents_of(store, character_id)
    if not parents:
        return 1
    return 1 + max(generation_of(store, p, _seen) for p in parents)


def ancestors(store, character_id):
    seen, frontier = set(), rel.parents_of(store, character_id)
    while frontier:
        nxt = []
        for x in frontier:
            if x not in seen:
                seen.add(x)
                nxt.extend(rel.parents_of(store, x))
        frontier = nxt
    return sorted(seen)


def descendants(store, character_id):
    seen, frontier = set(), rel.children_of(store, character_id)
    while frontier:
        nxt = []
        for x in frontier:
            if x not in seen:
                seen.add(x)
                nxt.extend(rel.children_of(store, x))
        frontier = nxt
    return sorted(seen)


def lineage(store, character_id):
    char = store.row("SELECT display_name FROM characters"
                     " WHERE character_id = ?", (character_id,))
    return {"character_id": character_id,
            "name": char["display_name"] if char else None,
            "generation": generation_of(store, character_id),
            "ancestors": ancestors(store, character_id),
            "descendants": descendants(store, character_id),
            "children": rel.children_of(store, character_id),
            "parents": rel.parents_of(store, character_id)}


def _recorded(store, character_id, event_type):
    return store.row("SELECT 1 FROM generational_history"
                     " WHERE character_id = ? AND event_type = ?",
                     (character_id, event_type)) is not None


def record_history_sweep(store, game_minutes):
    """Persist lineage births and inheritances from the life-event
    log into generational_history (once each)."""
    written = 0
    for ev in store.rows("SELECT * FROM life_events WHERE event_type"
                         " = 'birth' ORDER BY game_minutes"):
        cid = ev["character_id"]
        if _recorded(store, cid, "lineage_birth"):
            continue
        hid = store.next_id("GH", "generational_history", "history_id")
        store.insert("generational_history", history_id=hid,
                     character_id=cid, event_type="lineage_birth",
                     related_character_id=ev["other_character_id"],
                     generation=generation_of(store, cid),
                     details=ev["details"],
                     game_minutes=ev["game_minutes"])
        written += 1
    for ev in store.rows("SELECT * FROM life_events WHERE event_type"
                         " = 'inheritance_received'"
                         " ORDER BY game_minutes"):
        cid = ev["character_id"]
        rows = store.rows("SELECT COUNT(*) AS n FROM generational_history"
                          " WHERE character_id = ? AND event_type ="
                          " 'inheritance' AND game_minutes = ?",
                          (cid, ev["game_minutes"]))
        if rows[0]["n"]:
            continue
        hid = store.next_id("GH", "generational_history", "history_id")
        store.insert("generational_history", history_id=hid,
                     character_id=cid, event_type="inheritance",
                     related_character_id=ev["other_character_id"],
                     generation=generation_of(store, cid),
                     details=ev["details"],
                     game_minutes=ev["game_minutes"])
        written += 1
    return written


def _strongest_skill(store, character_id):
    row = store.row("SELECT skill_id, level FROM character_skills"
                    " WHERE character_id = ? ORDER BY level DESC,"
                    " skill_id LIMIT 1", (character_id,))
    return row["skill_id"] if row else "subject_knowledge"


def knowledge_transfer(store, data, game_minutes):
    """Monthly: in each household where an elder lives with a
    child, the elder teaches — the child gains capped experience
    in the elder's strongest skill, and the transfer is recorded
    in generational_history, memories and the event log."""
    from .identity import age_years
    transfers = 0
    households = store.rows("SELECT household_id FROM households"
                            " WHERE dissolved_at_game_minutes IS NULL"
                            " ORDER BY household_id")
    for h in households:
        hid = h["household_id"]
        profile = culture_mod.profile_for_household(store, data, hid)
        cfg = profile.get("knowledge_transfer", {})
        elder_age = cfg.get("elder_min_age", 65)
        xp = cfg.get("xp_per_month", 6)
        members = store.rows(
            "SELECT c.character_id, c.born_at_game_minutes FROM"
            " household_members hm JOIN characters c"
            " ON c.character_id = hm.character_id WHERE hm.household_id"
            " = ? AND hm.left_at_game_minutes IS NULL"
            " AND c.died_at_game_minutes IS NULL"
            " ORDER BY c.character_id", (hid,))
        elders = [m for m in members
                  if age_years(m["born_at_game_minutes"],
                               game_minutes) >= elder_age]
        children = [m for m in members
                    if 3 <= age_years(m["born_at_game_minutes"],
                                      game_minutes) <= 17]
        if not elders or not children:
            continue
        elder = elders[0]["character_id"]
        skill = _strongest_skill(store, elder)
        for child in children:
            cid = child["character_id"]
            if skill == "subject_knowledge" \
                    and education_mod.is_school_student(store, cid):
                education_mod.accrue_school_study(store, cid, xp)
            else:
                decisions_mod.add_skill_xp(store, cid, skill, xp)
            hid_ = store.next_id("GH", "generational_history",
                                 "history_id")
            store.insert("generational_history", history_id=hid_,
                         character_id=cid,
                         event_type="knowledge_transfer",
                         related_character_id=elder,
                         generation=generation_of(store, cid),
                         details=f'{{"skill": "{skill}", "xp": {xp}}}',
                         game_minutes=game_minutes)
            memory_mod.log_life_event(store, cid, "knowledge_transfer",
                                      game_minutes,
                                      other_character_id=elder)
            memory_mod.record_memory(store, cid, "learned_from_elder",
                                     15, game_minutes,
                                     other_character_id=elder)
            memory_mod.record_memory(store, elder, "taught_family", 15,
                                     game_minutes,
                                     other_character_id=cid)
            transfers += 1
    return transfers


def history_of(store, character_id):
    return store.rows("SELECT * FROM generational_history"
                      " WHERE character_id = ? ORDER BY game_minutes,"
                      " history_id", (character_id,))
