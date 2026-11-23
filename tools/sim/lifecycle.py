"""Unit 09 — Life Cycle Engine.

Life stage is *derived from age*, never stored as truth (GDD-01 §5):
Infant 0-2, Child 3-12, Teen 13-17, Young Adult 18-29, Adult 30-49,
Middle-Aged 50-64, Elder 65+, Deceased. The stored copy in
agent_state.life_stage exists only so transitions can be detected
and logged.

This engine owns: stage transitions (logged, remembered), template
selection per character, retirement at 65, death, and the death
cascade of GDD-01 §6.4 — employment ends, household headship passes,
the ledger balance and property move by the inheritance order
(spouse -> children in equal shares -> parents -> siblings -> city),
family statistics and emotions update. Nothing about death is a
silent row update: every effect is a ledger row, a life event, a
memory, or a relationship change.
"""
import re

from . import emotions as emotions_mod
from . import memory as memory_mod

STAGES = ("Infant", "Child", "Teen", "Young Adult", "Adult",
          "Middle-Aged", "Elder", "Deceased")


def stage_for_age(age):
    if age is None:
        return "Deceased"
    if age <= 2:
        return "Infant"
    if age <= 12:
        return "Child"
    if age <= 17:
        return "Teen"
    if age <= 29:
        return "Young Adult"
    if age <= 49:
        return "Adult"
    if age <= 64:
        return "Middle-Aged"
    return "Elder"


def template_id_for(store, character_id, age, employment):
    """Which schedule template this character runs today. Unemployed
    adults and infants use the elder_day *shape* (a home-centred day)
    as the v1 fallback — the data ships no unemployed or infant
    template; noted in the Session 01 report."""
    if age <= 2:
        return "elder_day", True   # infants stay home with family
    if age <= 12:
        return "child_school_day", True
    if age <= 17:
        return "student_day", True
    # Session 02 Unit 08: an enrolled college student runs the
    # student_day template (study@college blocks are what their
    # programme accrues from). Checked before employment: enrolment
    # is a full-time commitment in v1.
    enrolled = store.row(
        "SELECT 1 FROM education_records WHERE character_id = ?"
        " AND status = 'enrolled' AND programme != 'school'",
        (character_id,))
    if enrolled:
        return "student_day", True
    if employment:
        return employment["profession_id"], False
    return "elder_day", True


def promotion_threshold(profession, tier_index):
    """Skill level required to reach tier `tier_index` (1-based next
    tier), parsed from the profession's own progression text
    ('Medicine skill 35'); tiers whose unlock is not skill-based
    (capital, payroll, licences) fall back to documented defaults."""
    tiers = profession["progression"]
    if tier_index >= len(tiers):
        return None
    m = re.search(r"skill (\d+)", tiers[tier_index]["unlock"], re.I)
    if m:
        return int(m.group(1))
    return {1: 35, 2: 55, 3: 75}.get(tier_index, 90)


def alive(store, character_id):
    row = store.row("SELECT died_at_game_minutes FROM characters"
                    " WHERE character_id = ?", (character_id,))
    return row is not None and row["died_at_game_minutes"] is None


def heirs_in_order(store, character_id):
    """GDD-01 §6.4 order: spouse, then children (equal shares among
    themselves), then parents, then siblings. Only the first
    non-empty class inherits."""
    from . import relationships as rel
    spouse = rel.spouse_of(store, character_id)
    if spouse and alive(store, spouse):
        return [spouse]
    children = [c for c in rel.children_of(store, character_id)
                if alive(store, c)]
    if children:
        return sorted(children)
    parents = [c for c in rel.parents_of(store, character_id)
               if alive(store, c)]
    if parents:
        return sorted(parents)
    siblings = [c for c in rel.siblings_of(store, character_id)
                if alive(store, c)]
    return sorted(siblings)


def death_probability(age):
    """Daily probability. Near zero in youth, rising steeply for
    elders — the sim's mortality model (a stated assumption; the GDD
    defines stages and inheritance, not actuarial tables)."""
    if age < 50:
        return 0.000005
    if age < 65:
        return 0.00004
    return 0.00025 * (1.09 ** (age - 65))


def die(store, character_id, game_minutes, cause="natural"):
    """The full death cascade. Returns the heir list."""
    store.execute("UPDATE characters SET died_at_game_minutes = ?"
                  " WHERE character_id = ?",
                  (game_minutes, character_id))
    memory_mod.log_life_event(store, character_id, "death", game_minutes,
                              details={"cause": cause})
    # Employment ends.
    store.execute("UPDATE employments SET ended_at_game_minutes = ?"
                  " WHERE character_id = ? AND ended_at_game_minutes"
                  " IS NULL", (game_minutes, character_id))
    char = store.row("SELECT * FROM characters WHERE character_id = ?",
                     (character_id,))
    heirs = heirs_in_order(store, character_id)
    # Family grief: events, memories, emotions.
    from . import relationships as rel_mod
    family = rel_mod.family_of(store, character_id)
    for member in family:
        if member != character_id and alive(store, member):
            memory_mod.log_life_event(store, member, "death_of_family",
                                      game_minutes,
                                      other_character_id=character_id)
            memory_mod.record_memory(store, member, "death_of_family", -90,
                                     game_minutes,
                                     other_character_id=character_id)
            emotions_mod.apply_event(store, member, "death_of_family")
    # Inheritance: balance split equally among the heir class.
    balance = char["balance_cached"]
    if balance > 0:
        if heirs:
            share = balance // len(heirs)
            for heir in heirs:
                if share > 0:
                    store.transfer(character_id, heir, share,
                                   "inheritance", game_minutes,
                                   note=f"inheritance from {character_id}")
                memory_mod.log_life_event(
                    store, heir, "inheritance_received", game_minutes,
                    other_character_id=character_id,
                    details={"amount": share})
                emotions_mod.apply_event(store, heir,
                                         "inheritance_received")
            remainder = balance - share * len(heirs)
            if remainder > 0:
                store.transfer(character_id, "SYS-CITY", remainder,
                               "inheritance", game_minutes,
                               note="rounding remainder to city")
        else:  # escheat to the city
            store.transfer(character_id, "SYS-CITY", balance,
                           "inheritance", game_minutes, note="escheat")
    # Property: first heir takes sole-owned property; else it returns
    # to the market.
    props = store.rows("SELECT property_id FROM properties"
                       " WHERE owner_character_id = ?", (character_id,))
    for p in props:
        if heirs:
            store.execute("UPDATE properties SET owner_character_id = ?"
                          " WHERE property_id = ?",
                          (heirs[0], p["property_id"]))
        else:
            store.execute("UPDATE properties SET owner_character_id ="
                          " NULL, status = 'for_sale'"
                          " WHERE property_id = ?", (p["property_id"],))
    # Businesses pass to the first heir or close.
    biz = store.rows("SELECT business_id FROM businesses"
                     " WHERE owner_character_id = ?", (character_id,))
    for b in biz:
        if heirs:
            store.execute("UPDATE businesses SET owner_character_id = ?"
                          " WHERE business_id = ?",
                          (heirs[0], b["business_id"]))
        else:
            store.execute("UPDATE businesses SET closed_at_game_minutes"
                          " = ? WHERE business_id = ?",
                          (game_minutes, b["business_id"]))
    # Household: membership ends; headship (the household_members
    # role) passes to the eldest remaining member; an empty household
    # dissolves.
    store.execute("UPDATE household_members SET left_at_game_minutes = ?"
                  " WHERE character_id = ? AND left_at_game_minutes"
                  " IS NULL", (game_minutes, character_id))
    hid = char["household_id"]
    if hid:
        members = store.rows(
            "SELECT hm.character_id, c.born_at_game_minutes"
            " FROM household_members hm JOIN characters c"
            " ON c.character_id = hm.character_id"
            " WHERE hm.household_id = ? AND hm.left_at_game_minutes"
            " IS NULL AND c.died_at_game_minutes IS NULL"
            " ORDER BY c.born_at_game_minutes ASC", (hid,))
        if not members:
            store.execute("UPDATE households SET dissolved_at_game_minutes"
                          " = ? WHERE household_id = ?",
                          (game_minutes, hid))
        else:
            store.execute("UPDATE household_members SET role = 'head'"
                          " WHERE household_id = ? AND character_id = ?",
                          (hid, members[0]["character_id"]))
    return heirs


def daily_check(store, rng, character, day_index, game_minutes,
                data=None):
    """Stage transitions, retirement, and the mortality roll for one
    character at day rollover. Returns 'died' if the character died.
    ``data`` (Queue 17 Unit DK) is the loaded WorldData: when the
    stage transition is to Young Adult (18), the character is seeded
    their starting outfits — adults born in-world reach 18 here,
    and genesis adults were already seeded at creation. Callers
    that pass no data skip the seeding, as before."""
    from .identity import age_years
    cid = character["character_id"]
    age = age_years(character["born_at_game_minutes"], game_minutes)
    stage = stage_for_age(age)
    state = store.row("SELECT life_stage FROM agent_state"
                      " WHERE character_id = ?", (cid,))
    if state and state["life_stage"] is None:
        # First sight of this character (e.g. a newborn): initialise
        # silently — being born is not a stage transition.
        store.execute("UPDATE agent_state SET life_stage = ?"
                      " WHERE character_id = ?", (stage, cid))
    elif state and state["life_stage"] != stage:
        memory_mod.log_life_event(store, cid, "stage_transition",
                                  game_minutes,
                                  details={"from": state["life_stage"],
                                           "to": stage, "age": age})
        store.execute("UPDATE agent_state SET life_stage = ?"
                      " WHERE character_id = ?", (stage, cid))
        # Queue 17 Unit DK: the age-up to Young Adult (18) issues
        # the starting outfits — the creator's three outfits for a
        # character born in-world. The helper no-ops when the
        # character already holds starting-outfit rows.
        if stage == "Young Adult" and data is not None:
            from . import lost_items as lost_items_mod
            lost_items_mod.seed_age_up_outfits(store, data, cid,
                                               game_minutes)
        # Retirement: leaving employment at Elder stage.
        if stage == "Elder":
            emp = store.row("SELECT employment_id FROM employments"
                            " WHERE character_id = ?"
                            " AND ended_at_game_minutes IS NULL", (cid,))
            if emp:
                store.execute(
                    "UPDATE employments SET ended_at_game_minutes = ?"
                    " WHERE employment_id = ?",
                    (game_minutes, emp["employment_id"]))
                memory_mod.log_life_event(store, cid, "retirement",
                                          game_minutes)
    roll = rng.stream("death", cid, day_index).random()
    p = death_probability(age)
    if age >= 65:
        # Session 06 (GDD-12 §3.4): the death rule reads elder
        # stage PLUS active/recent serious conditions. The
        # multiplier is 1.0 whenever no open serious condition
        # exists — including every world without the Session 06
        # layer — so pre-Session-06 behaviour is unchanged there.
        from . import health as health_mod
        p *= health_mod.mortality_multiplier(store, cid)
    if roll < p:
        die(store, cid, game_minutes)
        return "died"
    return None
