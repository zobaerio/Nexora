"""Session 02 Unit 07 — Culture & Tradition Engine.

Culture in NEXORA is *configuration*: profiles live in
data/culture-profiles.json and this module only reads them. A
profile carries a language, family traditions, a festival calendar
(day-of-year), knowledge-transfer parameters and simulation-rule
flags (adoption_enabled, read by Unit 01). Adding a profile to the
data file adds a culture to the world with zero code changes, and
nothing here is hardcoded to one country — the two shipped profiles
differ in language, festivals and traditions precisely to prove the
mechanism is generic.

Assignment is a pure function of the household id (a stable hash):
~85% of households hold the data file's default profile, the rest
the second — a *simulation configuration choice* about the city's
makeup, recorded here, not a claim about any real place. The
assignment is written once into household_culture and never changes
for a household; children inherit their household's culture by
living in it, and a person who leaves home carries the profile of
the household they form (Unit 02 creates it fresh — assignment runs
again for the new household, which is how cultures mix across a
city over generations).
"""
import hashlib

from . import memory as memory_mod


def _pick_profile(data, household_id):
    profiles = list(data.culture_profiles.values())
    if len(profiles) == 1:
        return profiles[0]
    digest = int(hashlib.md5(household_id.encode()).hexdigest(), 16)
    if digest % 100 < 15:
        others = [p for p in profiles if p["id"] != data.default_culture]
        return others[0] if others else profiles[0]
    return data.culture_profiles[data.default_culture]


def ensure_culture(store, data, household_id, game_minutes):
    row = store.row("SELECT profile_id FROM household_culture"
                    " WHERE household_id = ?", (household_id,))
    if row:
        return data.culture_profiles[row["profile_id"]]
    profile = _pick_profile(data, household_id)
    store.insert("household_culture", household_id=household_id,
                 profile_id=profile["id"],
                 assigned_at_game_minutes=game_minutes)
    return profile


def profile_for_household(store, data, household_id):
    """The household's culture profile, assigning on first read."""
    world = store.world()
    return ensure_culture(store, data, household_id,
                          world["game_minutes"] if world else 0)


def profile_of_person(store, data, character_id):
    char = store.row("SELECT household_id FROM characters"
                     " WHERE character_id = ?", (character_id,))
    if not char or not char["household_id"]:
        return None
    return profile_for_household(store, data, char["household_id"])


def households_with_profile(store, profile_id):
    return [r["household_id"] for r in store.rows(
        "SELECT household_id FROM household_culture"
        " WHERE profile_id = ?", (profile_id,))]


def festivals_on(data, day_of_year):
    """All (profile, festival) pairs whose calendar day matches —
    the events engine (Unit 09) turns these into real gatherings."""
    out = []
    for profile in data.culture_profiles.values():
        for fest in profile.get("festivals", []):
            if fest["day_of_year"] == day_of_year:
                out.append((profile, fest))
    return out


def traditions_of(store, data, household_id):
    profile = profile_for_household(store, data, household_id)
    return profile.get("family_traditions", [])


def observe_tradition(store, data, household_id, tradition,
                      game_minutes):
    """Record a household observing one of its profile's traditions
    (the weekly family meal is lived through household_time; this
    is the explicit observance record other systems read)."""
    profile = profile_for_household(store, data, household_id)
    if tradition not in profile.get("family_traditions", []):
        return False
    members = store.rows("SELECT character_id FROM household_members"
                         " WHERE household_id = ?"
                         " AND left_at_game_minutes IS NULL",
                         (household_id,))
    for m in members:
        memory_mod.log_life_event(store, m["character_id"],
                                  "tradition_observed", game_minutes,
                                  details={"tradition": tradition,
                                           "profile": profile["id"]})
    return True
