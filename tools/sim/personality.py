"""Unit 02 — Personality Engine.

Every individual carries the Session 01 twelve-attribute profile.
GDD-01's five canonical traits (stored on `characters`, the shape the
rest of the project uses) are *derived* from the profile by the fixed
mapping below — one personality, two views, never two sources:

    ambition        = ambition
    sociability     = extraversion
    discipline      = discipline
    kindness        = round(0.6 * empathy + 0.4 * cooperation)
    risk_tolerance  = risk_tolerance

Personality is generated once at creation from a seeded stream and
then persists; it drifts only through documented life-event nudges
(GDD-01 §2.1: traits drift slowly, never jump). Behavioural consumers
(decisions, interactions, emotions) read these numbers — personality
is an input to behaviour weighting, not decoration.
"""

ATTRIBUTES = ("extraversion", "confidence", "intelligence", "curiosity",
              "patience", "creativity", "ambition", "empathy",
              "risk_tolerance", "discipline", "cooperation",
              "emotional_sensitivity")

# Small profession-affinity nudges applied at generation (documented
# design: professions attract temperaments; nudges are ±12 at most and
# never determine the person).
AFFINITY = {
    "construction_worker": {"discipline": 8, "patience": 6},
    "civil_engineer": {"intelligence": 10, "discipline": 8, "patience": 6},
    "doctor": {"intelligence": 12, "empathy": 10, "patience": 8},
    "teacher": {"empathy": 10, "patience": 12, "cooperation": 8},
    "police_officer": {"confidence": 10, "discipline": 10, "risk_tolerance": 6},
    "taxi_driver": {"extraversion": 8, "patience": 6, "risk_tolerance": 6},
    "chef": {"creativity": 10, "patience": 6, "discipline": 6},
    "software_developer": {"intelligence": 12, "curiosity": 10, "extraversion": -8},
    "shop_owner": {"extraversion": 8, "cooperation": 8, "ambition": 6},
    "business_owner": {"ambition": 12, "confidence": 10, "risk_tolerance": 10},
    "pilot": {"confidence": 12, "discipline": 10, "intelligence": 8},
}


def _bell(rng):
    """Bell-curved 0..100 draw (mean ~50) from three uniforms."""
    return max(0, min(100, round((rng.random() + rng.random()
                                  + rng.random()) / 3 * 100)))


def generate(rng, profession_id=None):
    """A new personality profile (dict of the 12 attributes)."""
    profile = {attr: _bell(rng) for attr in ATTRIBUTES}
    for attr, nudge in AFFINITY.get(profession_id, {}).items():
        profile[attr] = max(0, min(100, profile[attr] + nudge))
    return profile


def canonical_traits(profile):
    """The GDD-01 five traits, derived by the fixed mapping above."""
    return {
        "trait_ambition": profile["ambition"],
        "trait_sociability": profile["extraversion"],
        "trait_discipline": profile["discipline"],
        "trait_kindness": round(0.6 * profile["empathy"]
                                + 0.4 * profile["cooperation"]),
        "trait_risk_tolerance": profile["risk_tolerance"],
    }


def nudge(store, character_id, game_minutes, **deltas):
    """Slow trait drift from a life event (GDD-01 §2.1). Deltas are
    clamped to ±6 per event so no single event rewrites a person; the
    canonical traits are re-derived and stored with the profile."""
    row = store.row("SELECT * FROM personality_profiles"
                    " WHERE character_id = ?", (character_id,))
    if row is None:
        return
    profile = {a: row[a] for a in ATTRIBUTES}
    for attr, d in deltas.items():
        d = max(-6, min(6, d))
        profile[attr] = max(0, min(100, profile[attr] + d))
    sets = ", ".join(f"{a} = ?" for a in ATTRIBUTES)
    store.execute(f"UPDATE personality_profiles SET {sets}"
                  " WHERE character_id = ?",
                  tuple(profile[a] for a in ATTRIBUTES) + (character_id,))
    traits = canonical_traits(profile)
    tsets = ", ".join(f"{k} = ?" for k in traits)
    store.execute(f"UPDATE characters SET {tsets} WHERE character_id = ?",
                  tuple(traits.values()) + (character_id,))


def get_profile(store, character_id):
    return store.row("SELECT * FROM personality_profiles"
                     " WHERE character_id = ?", (character_id,))


def compatibility(a, b):
    """0..100 temperament compatibility between two profiles — used by
    the interaction engine. Similar patience/empathy/cooperation
    profiles get along; clashing risk/extraversion costs a little."""
    sim = 0.0
    for attr in ("patience", "empathy", "cooperation", "emotional_sensitivity"):
        sim += 100 - abs(a[attr] - b[attr])
    sim /= 4
    clash = (abs(a["risk_tolerance"] - b["risk_tolerance"])
             + abs(a["extraversion"] - b["extraversion"])) / 2
    return max(0.0, min(100.0, sim * 0.75 + (100 - clash) * 0.25))
