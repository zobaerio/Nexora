"""Unit 06 — Emotional Simulation Engine.

Emotions are *event-driven state*, never random weather of the mind:
every change comes from a simulated event (job loss, promotion,
marriage, bereavement, payday...) through the EVENT_EFFECTS table, or
from the slow daily regression toward a personality-dependent
baseline. Emotional sensitivity scales how hard events hit — the same
event does not move every person equally.

Baseline anchors (derived from the Unit 02 profile):
- happiness rises with extraversion; stress falls with patience;
  loneliness falls with extraversion; motivation rises with ambition;
  sadness/fear rise with emotional sensitivity; anger falls with
  patience.
"""
from . import personality as personality_mod

EMOTIONS = ("happiness", "sadness", "stress", "fear", "anger",
            "excitement", "loneliness", "satisfaction", "motivation")

# Event -> emotion deltas. The owner's examples are the first three
# rows' semantics: losing employment raises stress; achieving a goal
# raises happiness; losing a family member causes grief.
EVENT_EFFECTS = {
    "payday": {"satisfaction": 6, "stress": -5, "happiness": 4},
    "job_loss": {"stress": 30, "happiness": -20, "fear": 15,
                 "satisfaction": -15, "motivation": -5},
    "job_gain": {"happiness": 15, "stress": -10, "satisfaction": 10,
                 "motivation": 10, "excitement": 10},
    "promotion": {"happiness": 20, "satisfaction": 15, "motivation": 15,
                  "excitement": 10, "stress": -5},
    "goal_complete": {"happiness": 25, "satisfaction": 20,
                      "motivation": 15},
    "marriage": {"happiness": 30, "loneliness": -30, "excitement": 20},
    "childbirth": {"happiness": 30, "excitement": 20, "stress": 10,
                   "satisfaction": 15},
    "death_of_family": {"sadness": 50, "happiness": -35, "stress": 20,
                        "loneliness": 15},
    "death_of_friend": {"sadness": 25, "happiness": -15},
    "new_friend": {"loneliness": -15, "happiness": 8},
    "friendship_deepened": {"loneliness": -8, "happiness": 5},
    "conflict": {"anger": 20, "stress": 10, "happiness": -8},
    "estrangement": {"sadness": 20, "anger": 10, "loneliness": 10},
    "inheritance_received": {"satisfaction": 10, "stress": -5},
    "business_founded": {"excitement": 25, "happiness": 15,
                         "motivation": 20, "stress": 10},
    "illness": {"stress": 15, "happiness": -10, "fear": 10},
    "moved_home": {"excitement": 8, "stress": 8},
    "evicted": {"stress": 35, "fear": 20, "happiness": -25,
                "sadness": 20},
    "study_gain": {"satisfaction": 5, "motivation": 5},
    "social_day": {"loneliness": -6, "happiness": 4},
}


def baselines(profile):
    p = profile
    return {
        "happiness": 42 + p["extraversion"] * 0.2,
        "sadness": 12 + p["emotional_sensitivity"] * 0.12,
        "stress": 38 - p["patience"] * 0.22,
        "fear": 8 + p["emotional_sensitivity"] * 0.08,
        "anger": 16 - p["patience"] * 0.12,
        "excitement": 22 + p["extraversion"] * 0.18,
        "loneliness": 42 - p["extraversion"] * 0.28,
        "satisfaction": 50,
        "motivation": 38 + p["ambition"] * 0.32,
    }


def _clamp(v):
    return max(0, min(100, round(v)))


def get_emotions(store, character_id):
    row = store.row("SELECT * FROM emotional_state WHERE character_id = ?",
                    (character_id,))
    return {e: row[e] for e in EMOTIONS} if row else None


def _write(store, character_id, values):
    sets = ", ".join(f"{e} = ?" for e in EMOTIONS)
    store.execute(f"UPDATE emotional_state SET {sets}"
                  " WHERE character_id = ?",
                  tuple(values[e] for e in EMOTIONS) + (character_id,))


def apply_event(store, character_id, event_type):
    """Apply one simulated event's emotional consequences. Negative
    emotions scale with the person's emotional sensitivity; positive
    ones do not (a design choice, documented here)."""
    effects = EVENT_EFFECTS.get(event_type)
    if not effects:
        return
    values = get_emotions(store, character_id)
    if values is None:
        return
    profile = personality_mod.get_profile(store, character_id)
    sensitivity = profile["emotional_sensitivity"] if profile else 50
    neg_factor = 0.7 + (sensitivity / 100.0) * 0.6
    for emo, delta in effects.items():
        if delta < 0 or emo in ("sadness", "stress", "fear", "anger",
                                "loneliness"):
            delta = delta * neg_factor if delta > 0 else delta
        values[emo] = _clamp(values[emo] + delta)
    _write(store, character_id, values)


def daily_regress(store, character_id):
    """One day of emotional settling toward personality baselines."""
    values = get_emotions(store, character_id)
    profile = personality_mod.get_profile(store, character_id)
    if values is None or profile is None:
        return
    base = baselines(profile)
    for emo in EMOTIONS:
        values[emo] = _clamp(values[emo] + (base[emo] - values[emo]) * 0.15)
    _write(store, character_id, values)
