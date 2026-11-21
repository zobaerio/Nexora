"""Unit 03 — Human Memory Engine.

Two kinds of memory, exactly as GDD-01 §2.3 separates them:

- Episodic memory (`character_memories`): notable events with an
  emotional weight. Full-tier characters only. Capped at 200 rows per
  character; when the cap is exceeded the *least important* memories
  are forgotten first — priority is |emotional weight| aged by
  recency, so a life-defining event (a wedding, a death in the
  family) outlives a hundred minor ones. Minor events are never
  stored indefinitely by design.
- Semantic memory: facts stored on the relationship/employment rows
  themselves (flags like met_player, worked_with) — handled by
  relationships.py / employments, permanent and cheap.

`life_events` is the world's event log: every significant simulated
event (birth, marriage, childbirth, death, job change...) is written
once, for every tier, and other engines (emotions, decisions,
lifecycle) consume it. Memory is what an individual retains of it.
"""
import json

MEMORY_CAP = 200  # GDD-01 §2.3 cap for episodic memory


def log_life_event(store, character_id, event_type, game_minutes,
                   other_character_id=None, details=None):
    eid = store.next_id("EV", "life_events", "event_id")
    store.insert("life_events", event_id=eid, character_id=character_id,
                 event_type=event_type,
                 other_character_id=other_character_id,
                 details=json.dumps(details or {}),
                 game_minutes=game_minutes)
    return eid


def record_memory(store, character_id, event_type, emotional_weight,
                  game_minutes, other_character_id=None, details=None):
    """Append an episodic memory (Full tier only), then enforce the
    retention cap. Returns the memory id, or None for non-Full tiers
    (Scheduled/Ambient characters keep semantic memory only)."""
    char = store.row("SELECT sim_tier FROM characters"
                     " WHERE character_id = ?", (character_id,))
    if char is None or char["sim_tier"] != "full":
        return None
    # Ids from MAX suffix, not COUNT: pruning deletes rows, and a
    # count-based id could collide with a surviving memory.
    row = store.row("SELECT COALESCE(MAX(CAST(SUBSTR(memory_id, 3)"
                    " AS INTEGER)), 0) AS n FROM character_memories")
    mid = f"MM{row['n'] + 1:06d}"
    store.insert("character_memories", memory_id=mid,
                 character_id=character_id,
                 other_character_id=other_character_id,
                 event_type=event_type,
                 emotional_weight=max(-100, min(100, emotional_weight)),
                 details=json.dumps(details or {}),
                 occurred_at_game_minutes=game_minutes)
    prune(store, character_id, game_minutes)
    return mid


def _priority(row, now_game_minutes):
    """Retention priority: strong emotions persist; time erodes weak
    ones. Age is measured in game days."""
    age_days = max(0, (now_game_minutes - row["occurred_at_game_minutes"])
                   // 1440)
    recency = 1.0 / (1.0 + age_days / 90.0)  # halves roughly every 90 days
    return abs(row["emotional_weight"]) * (0.35 + 0.65 * recency)


def prune(store, character_id, now_game_minutes):
    rows = store.rows(
        "SELECT memory_id, emotional_weight, occurred_at_game_minutes"
        " FROM character_memories WHERE character_id = ?",
        (character_id,))
    if len(rows) <= MEMORY_CAP:
        return 0
    ranked = sorted(rows, key=lambda r: _priority(r, now_game_minutes))
    excess = len(rows) - MEMORY_CAP
    for r in ranked[:excess]:
        store.execute("DELETE FROM character_memories WHERE memory_id = ?",
                      (r["memory_id"],))
    return excess


def memories_about(store, character_id, other_character_id, limit=5):
    """What `character_id` episodically remembers about another person,
    strongest first — the input dialogue/decision systems read."""
    rows = store.rows(
        "SELECT * FROM character_memories WHERE character_id = ?"
        " AND other_character_id = ? ORDER BY ABS(emotional_weight) DESC,"
        " occurred_at_game_minutes DESC LIMIT ?",
        (character_id, other_character_id, limit))
    return rows


def recent_memories(store, character_id, now_game_minutes, limit=10):
    rows = store.rows(
        "SELECT * FROM character_memories WHERE character_id = ?",
        (character_id,))
    return sorted(rows, key=lambda r: _priority(r, now_game_minutes),
                  reverse=True)[:limit]
