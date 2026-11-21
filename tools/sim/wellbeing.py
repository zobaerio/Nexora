"""Session 06 — Wellbeing (simplified, measured).

A monthly snapshot per living citizen, computed ONLY from state
the earlier sessions already maintain — Session 01's emotional
state (stress, loneliness), Session 02's relationship graph
(friendships = social support), household size, and the needs
system's sleep/rest satisfactions (work-life balance proxy). No
diagnosis of any kind is made or implied: these are simulation
indices over simulated state, in the spec's own simplified form.

- stress: the emotional state's stress value, as recorded.
- social_support: friendships and household, capped — each friend
  (relationships.friends_of) counts 12, each co-resident 6, plus
  10 for community membership (Session 02 communities).
- loneliness: the emotional state's loneliness value, as recorded.
- work_life: the mean of the needs system's sleep and rest
  satisfactions.
- wellbeing_score: the mean of (100 - stress), social_support,
  (100 - loneliness) and work_life.
"""
from . import needs as needs_mod
from . import relationships as rel_mod


def snapshot_character(store, character_id):
    """The wellbeing components for one citizen, from live state.
    Returns None when the citizen has no emotional state row."""
    emo = store.row("SELECT * FROM emotional_state WHERE"
                    " character_id = ?", (character_id,))
    if emo is None:
        return None
    needs = needs_mod.get_needs(store, character_id) or {}
    friends = rel_mod.friends_of(store, character_id)
    char = store.row("SELECT household_id FROM characters WHERE"
                     " character_id = ?", (character_id,))
    household_size = 0
    if char and char["household_id"]:
        row = store.row("SELECT COUNT(*) AS n FROM household_members"
                        " WHERE household_id = ? AND"
                        " left_at_game_minutes IS NULL",
                        (char["household_id"],))
        household_size = row["n"] if row else 0
    member = store.row("SELECT 1 FROM community_members WHERE"
                       " character_id = ?", (character_id,))
    support = min(100.0, len(friends) * 12 + household_size * 6
                  + (10 if member else 0))
    work_life = round(((needs.get("sleep", 50) or 50)
                       + (needs.get("rest", 50) or 50)) / 2, 2)
    stress = float(emo["stress"])
    loneliness = float(emo["loneliness"])
    score = round(((100 - stress) + support + (100 - loneliness)
                   + work_life) / 4, 2)
    return {"stress": stress, "social_support": float(support),
            "loneliness": loneliness, "work_life": work_life,
            "wellbeing_score": score}


def monthly_pass(store, data, month_index, game_minutes):
    n = 0
    for char in store.rows("SELECT character_id FROM characters"
                           " WHERE is_system = 0 AND"
                           " died_at_game_minutes IS NULL"
                           " ORDER BY character_id"):
        if store.row("SELECT 1 FROM wellbeing_records WHERE"
                     " character_id = ? AND month_index = ?",
                     (char["character_id"], month_index)):
            continue  # month replay: snapshot already written
        snap = snapshot_character(store, char["character_id"])
        if snap is None:
            continue
        rid = store.next_id("WB", "wellbeing_records", "record_id")
        store.insert("wellbeing_records", record_id=rid,
                     character_id=char["character_id"],
                     month_index=month_index, **snap)
        n += 1
    return {"wellbeing_snapshots": n}
