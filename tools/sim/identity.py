"""Unit 01 — Human Identity Engine.

Every simulated individual gets a persistent identity at creation:
unique Human ID (the character_id, displayed as NEX-000001), first and
last name, date of birth (born_at_game_minutes — age is always derived
from it, GDD-01 §3), sex as a simulation attribute, family background,
birthplace, current residence, nationality, education level, occupation
(the employment row), financial status (ledger-derived balance +
starting balance), personality profile (Unit 02) and personal goals
(GDD-01 §2.2 goal stack).

Identities never change randomly: names, birth data and nationality
are written once at creation and no code path in this package updates
them. Death archives the row; it is never deleted (GDD-01 §3).
"""
import json

from . import personality as personality_mod

MALE_FIRST = [
    "Arif", "Tanvir", "Rahim", "Karim", "Hasan", "Imran", "Shakib",
    "Mehedi", "Rafid", "Nabil", "Farhan", "Sabbir", "Rony", "Jahid",
    "Mizan", "Sohel", "Rubel", "Anik", "Pranto", "Shanto", "Biplob",
    "Sumon", "Rasel", "Tareq", "Omar", "Nasir", "Kamal", "Jamal",
    "Rahad", "Fahim", "Sakib", "Tamim", "Liton", "Mushfiq", "Rakib",
    "Hridoy", "Niloy", "Arman", "Shakil", "Rifat",
]
FEMALE_FIRST = [
    "Fatema", "Ayesha", "Nusrat", "Sharmin", "Rumana", "Taslima",
    "Farhana", "Sabina", "Mitu", "Priya", "Shirin", "Khadija",
    "Mariam", "Salma", "Roksana", "Jannat", "Sumaya", "Tania",
    "Nabila", "Farida", "Shahana", "Rina", "Laila", "Nasrin",
    "Shamima", "Ruma", "Poly", "Shilpi", "Monira", "Habiba",
    "Sultana", "Afrin", "Tamanna", "Ishrat", "Nargis", "Beauty",
    "Champa", "Dolly", "Rani", "Shova",
]
FAMILY_NAMES = [
    "Hasan", "Rahman", "Islam", "Ahmed", "Hossain", "Ali", "Khan",
    "Miah", "Sarkar", "Chowdhury", "Akter", "Begum", "Uddin", "Sheikh",
    "Molla", "Biswas", "Das", "Pal", "Saha", "Ghosh", "Barua",
    "Chakma", "Marma", "Tripura", "Halder", "Mondal", "Sikder",
    "Talukder", "Howlader", "Matubbar", "Fakir", "Gazi", "Pramanik",
    "Sardar", "Bepari", "Dewan", "Kazi", "Mir", "Shah",
]
BIRTHPLACES = [
    "Rupsha City", "Rupsha City", "Rupsha City", "Khulna", "Dhaka",
    "Barisal", "Jessore", "Satkhira", "Bagerhat", "Narail",
    "Magura", "Kushtia", "Chuadanga", "Meherpur", "Jhenaidah",
]
CITIES = ["Rupsha City"]

# Life goals by aspiration flavour (GDD-01 §2.2). Data, not scripts.
LIFE_GOALS = [
    ("own_house", "Own a house in the riverfront district"),
    ("own_company", "Own a company"),
    ("save_amount", "Build lasting savings"),
    ("reach_skill", "Master my craft"),
    ("marry", "Marry and raise a family"),
    ("educate_children", "Give my children a full education"),
    ("open_business", "Open my own business"),
    ("serve_community", "Serve my community"),
]


def human_id(character_id):
    return "NEX-" + character_id[3:]


def age_years(born_at_game_minutes, now_game_minutes):
    """Age is derived, never stored (GDD-01 §3). One game year is
    365 game days, matching the engine's day count."""
    days = (now_game_minutes - born_at_game_minutes) // 1440
    return days // 365


def create_person(store, rng, *, first_name, last_name, sex,
                  born_at_game_minutes, household_id=None,
                  profession_id=None, sim_tier="scheduled",
                  birthplace=None, family_background=None,
                  game_minutes=480):
    """Insert one complete identity: character row, personality
    profile, needs/emotional baselines, agent state. Returns the new
    character_id. The caller funds any starting balance through the
    ledger (population/employment code) so caches always reconcile."""
    cid = store.next_id("NEX", "characters", "character_id")
    profile = personality_mod.generate(
        rng.stream("personality", cid), profession_id)
    traits = personality_mod.canonical_traits(profile)
    store.insert(
        "characters",
        character_id=cid, is_player=0, sim_tier=sim_tier,
        display_name=f"{first_name} {last_name}",
        first_name=first_name, last_name=last_name, sex=sex,
        born_at_game_minutes=born_at_game_minutes,
        household_id=household_id, residence_city="Rupsha City",
        birthplace=birthplace or "Rupsha City",
        nationality="Bangladeshi",
        family_background=json.dumps(family_background or {}),
        balance_cached=0, is_system=0, **traits)
    store.insert("personality_profiles", character_id=cid, **profile)
    store.insert("needs_state", character_id=cid,
                 updated_at_game_minutes=game_minutes)
    store.insert("emotional_state", character_id=cid)
    store.insert("agent_state", character_id=cid,
                 schedule_template_id=None, jitter_minutes=0)
    return cid


def pick_name(rng, sex, used):
    """A name not already used in this world (identities are unique);
    deterministic under the population seed."""
    firsts = MALE_FIRST if sex == "male" else FEMALE_FIRST
    for _ in range(200):
        first = rng.choice(firsts)
        last = rng.choice(FAMILY_NAMES)
        if (first, last) not in used:
            used.add((first, last))
            return first, last
    # Exhausted pairs: add a distinguishing middle initial, still unique.
    first = rng.choice(firsts)
    last = rng.choice(FAMILY_NAMES)
    initial = rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    first = f"{first} {initial}."
    used.add((first, last))
    return first, last


def add_goal(store, character_id, goal_kind, goal_type, target,
             game_minutes):
    gid = store.next_id("GL", "character_goals", "goal_id")
    store.insert("character_goals", goal_id=gid,
                 character_id=character_id, goal_kind=goal_kind,
                 goal_type=goal_type, target=json.dumps(target),
                 status="active", created_at_game_minutes=game_minutes)
    return gid


def profile_card(store, character_id):
    """The GDD-01 §1 character card, read from live simulation rows —
    the Session 01 observation surface. Nothing here is static demo
    data; every field is the current simulated truth."""
    c = store.row("SELECT * FROM characters WHERE character_id = ?",
                  (character_id,))
    if c is None:
        return None
    world = store.world()
    now = world["game_minutes"]
    emp = store.row(
        "SELECT * FROM employments WHERE character_id = ?"
        " AND ended_at_game_minutes IS NULL", (character_id,))
    goals = store.rows(
        "SELECT goal_kind, goal_type, status FROM character_goals"
        " WHERE character_id = ? AND status = 'active'", (character_id,))
    needs = store.row("SELECT * FROM needs_state WHERE character_id = ?",
                      (character_id,))
    emo = store.row("SELECT * FROM emotional_state WHERE character_id = ?",
                    (character_id,))
    stage = None
    from .lifecycle import stage_for_age  # late import: avoids a cycle
    stage = stage_for_age(age_years(c["born_at_game_minutes"], now))
    return {
        "human_id": human_id(character_id),
        "name": c["display_name"],
        "age": age_years(c["born_at_game_minutes"], now),
        "life_stage": stage,
        "sex": c["sex"],
        "birthplace": c["birthplace"],
        "residence": c["residence_city"],
        "nationality": c["nationality"],
        "profession": emp["profession_id"] if emp else None,
        "profession_tier": emp["tier"] if emp else None,
        "balance_ncr": c["balance_cached"],
        "household_id": c["household_id"],
        "alive": c["died_at_game_minutes"] is None,
        "goals": goals,
        "needs": {k: needs[k] for k in (
            "hunger", "thirst", "sleep", "rest", "safety", "social",
            "healthcare", "financial", "education", "development")}
        if needs else None,
        "emotions": {k: emo[k] for k in (
            "happiness", "sadness", "stress", "fear", "anger",
            "excitement", "loneliness", "satisfaction", "motivation")}
        if emo else None,
    }
