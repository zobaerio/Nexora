"""District 1 starter population — generated entirely from the merged
data files: households placed into the 140 real residential units of
buildings-district1.json, professions from professions.json (all 11
guaranteed present), wages and starting balances from the canonical
price/profession data, schedules assigned per GDD-06 templates.

Genesis balances are ledger rows (reason 'seed') so the ledger
reconciliation holds from the first minute. Elder savings and
unemployed buffers are genesis seeds too — the world has no pre-sim
history, and the Session 01 report says so plainly.
"""
import json

from . import identity as identity_mod
from . import lifecycle
from . import lost_items as lost_items_mod
from . import relationships as rel
from . import scheduler

TIER_SKILL_RANGE = {1: (8, 22), 2: (26, 46), 3: (48, 72), 4: (70, 90),
                    5: (78, 95)}
ARCHETYPES = (
    ("couple_children", 0.32), ("single", 0.22), ("couple", 0.14),
    ("single_parent", 0.12), ("elder_single", 0.08),
    ("elder_couple", 0.06), ("extended", 0.06),
)


def _born_at(rng, age_years, now=480):
    days = age_years * 365 + rng.randint(0, 364)
    return now - days * 1440


def _tier_for_age(rng, age):
    if age < 25:
        return 1
    if age < 40:
        return rng.choice((1, 2, 2))
    if age < 55:
        return rng.choice((2, 2, 3))
    return rng.choice((2, 3, 3))


def generate(store, data, rng, target_population=240, game_minutes=480):
    """Create the world population. Idempotent: refuses to run twice
    (world_state.population_generated). Returns generation stats."""
    world = store.world()
    if world and world["population_generated"]:
        return {"already_generated": True}
    units = data.residential_stock()
    unit_order = units[:]
    rng.stream("units").shuffle(unit_order)

    # Property rows for the whole residential stock (vacant first).
    property_by_unit = {}
    for u in units:
        pid = store.next_id("PR", "properties", "property_id")
        store.insert(
            "properties", property_id=pid,
            property_type=u["property_type"], district_id=u["zone_id"],
            address_label=f"{u['building_name']} #{u['unit_index'] + 1}",
            tier=u["tier"], status="vacant",
            market_value=u["buy_price"] or u["rent"] * 120,
            building_ref=u["building_id"], unit_index=u["unit_index"])
        property_by_unit[(u["building_id"], u["unit_index"])] = pid

    coverage = list(data.professions.keys())
    rng.stream("coverage").shuffle(coverage)
    used_names = set()
    stats = {"households": 0, "people": 0, "by_profession": {},
             "children": 0, "elders": 0, "unemployed": 0}
    unit_idx = 0

    def new_person(age, sex, profession_id, tier, household_id, full):
        stream = rng.stream("person", stats["people"])
        first, last = identity_mod.pick_name(stream, sex, used_names)
        # Queue 16 Unit DD: the creator's starting outfits (GDD-09
        # §3) — adults only. Children get no rows: their school
        # uniform is bought by the household in Unit AB's student
        # loop, not seeded here. No ledger purchase row is written
        # for genesis outfits (the genesis starting balance is a
        # seed transfer, not a purchase — the Phase 2 creator
        # charges the player; the genesis builder does not, and
        # that difference is recorded, not hidden).
        outfits = None
        if age >= 18:
            outfits = lost_items_mod.starting_outfits(
                data, profession_id, tier,
                "full" if full else "scheduled")
        cid = identity_mod.create_person(
            store, rng, first_name=first, last_name=last, sex=sex,
            born_at_game_minutes=_born_at(stream, age),
            household_id=household_id,
            profession_id=profession_id,
            sim_tier="full" if full else "scheduled",
            birthplace=stream.choice(identity_mod.BIRTHPLACES),
            family_background={"origin": "genesis population"},
            game_minutes=game_minutes, data=data, outfits=outfits)
        stats["people"] += 1
        return cid, last

    def employ(cid, profession_id, tier, age):
        wage = data.wage_at(profession_id, tier)
        eid = store.next_id("EM", "employments", "employment_id")
        store.insert("employments", employment_id=eid, character_id=cid,
                     profession_id=profession_id, tier=tier,
                     wage_per_month=wage,
                     started_at_game_minutes=game_minutes)
        prof = data.professions[profession_id]
        stream = rng.stream("skills", cid)
        for skill in prof["primary_skills"]:
            lo, hi = TIER_SKILL_RANGE[tier]
            level = stream.randint(lo, hi)
            store.insert("character_skills", character_id=cid,
                         skill_id=skill, level=level,
                         experience=level * 50 + stream.randint(0, 49))
        seed = data.starting_balance(profession_id)
        seed = round(seed * rng.stream("seedbal", cid).uniform(0.85, 1.15))
        if seed > 0:
            store.transfer("SYS-EMPLOYERS", cid, seed, "seed",
                           game_minutes, note="genesis starting balance")
        stats["by_profession"][profession_id] = \
            stats["by_profession"].get(profession_id, 0) + 1
        # Goals: one life goal + one stage goal (GDD-01 §2.2).
        profile = store.row("SELECT ambition, empathy FROM"
                            " personality_profiles WHERE character_id = ?",
                            (cid,))
        goals = identity_mod.LIFE_GOALS
        if profile and profile["ambition"] >= 70:
            goal = rng.stream("goal", cid).choice(
                [g for g in goals if g[0] in
                 ("own_company", "open_business", "save_amount")])
        elif profile and profile["empathy"] >= 65:
            goal = rng.stream("goal", cid).choice(
                [g for g in goals if g[0] in
                 ("serve_community", "educate_children", "marry")])
        else:
            goal = rng.stream("goal", cid).choice(goals)
        target = {}
        if goal[0] == "save_amount":
            target = {"amount": wage * 6}
        elif goal[0] == "reach_skill":
            target = {"skill": prof["primary_skills"][0], "level": 70}
        elif goal[0] == "own_house":
            target = {"district": "riverfront"}
        identity_mod.add_goal(store, cid, "life", goal[0], target,
                              game_minutes)
        identity_mod.add_goal(store, cid, "stage", "save_amount",
                              {"amount": wage * 2}, game_minutes)
        return eid

    def seed_money(cid, amount, note):
        if amount > 0:
            store.transfer("SYS-EMPLOYERS", cid, amount, "seed",
                           game_minutes, note=note)

    def add_member(hid, cid, role):
        store.insert("household_members", household_id=hid,
                     character_id=cid, role=role,
                     joined_at_game_minutes=game_minutes)

    def link_parent_child(parent, child, gm=game_minutes):
        rel.add_edge(store, parent, child, "parent", gm, trust=60,
                     affection=85, respect=30, both_ways=False)
        rel.add_edge(store, child, parent, "child", gm, trust=70,
                     affection=80, respect=50, both_ways=False)

    def finish_agent(cid, age):
        char = store.row("SELECT * FROM characters WHERE character_id = ?",
                         (cid,))
        emp = store.row("SELECT * FROM employments WHERE character_id = ?"
                        " AND ended_at_game_minutes IS NULL", (cid,))
        template_id, _ = lifecycle.template_id_for(store, cid, age, emp)
        store.execute(
            "UPDATE agent_state SET schedule_template_id = ?,"
            " jitter_minutes = ?, life_stage = ? WHERE character_id = ?",
            (template_id, scheduler.jitter_for(rng, cid),
             lifecycle.stage_for_age(age), cid))
        return char

    while stats["people"] < target_population and unit_idx < len(unit_order):
        unit = unit_order[unit_idx]
        unit_idx += 1
        full = stats["households"] < 30
        roll = rng.stream("archetype", stats["households"]).random()
        acc, archetype = 0.0, "single"
        for name, w in ARCHETYPES:
            acc += w
            if roll <= acc:
                archetype = name
                break
        hid = store.next_id("HH", "households", "household_id")
        prop_id = property_by_unit[(unit["building_id"],
                                    unit["unit_index"])]
        store.insert("households", household_id=hid,
                     name="Household", home_property_id=prop_id,
                     district_id=unit["zone_id"],
                     created_at_game_minutes=game_minutes)
        store.execute("UPDATE properties SET status = 'rented'"
                      " WHERE property_id = ?", (prop_id,))
        tid = store.next_id("TN", "tenancies", "tenancy_id")
        store.insert("tenancies", tenancy_id=tid, property_id=prop_id,
                     tenant_household_id=hid, rent_per_month=unit["rent"],
                     started_at_game_minutes=game_minutes)
        stream = rng.stream("household", stats["households"])

        def adult(age_lo, age_hi, role, use_coverage=False):
            age = stream.randint(age_lo, age_hi)
            sex = "male" if stream.random() < 0.5 else "female"
            if use_coverage and coverage:
                pid = coverage.pop()
            else:
                pid = stream.choice(list(data.professions.keys()))
            unemployed = stream.random() < 0.08
            tier = _tier_for_age(stream, age)
            cid, last = new_person(age, sex, None if unemployed else pid,
                                   tier, hid, full)
            add_member(hid, cid, role)
            if unemployed:
                seed_money(cid, 4000 + stream.randint(0, 4000),
                           "genesis buffer (unemployed)")
                stats["unemployed"] += 1
            else:
                employ(cid, pid, tier, age)
            finish_agent(cid, age)
            return cid, last, age

        def child(age_lo, age_hi, parents):
            age = stream.randint(age_lo, age_hi)
            sex = "male" if stream.random() < 0.5 else "female"
            cid, _ = new_person(age, sex, None, 1, hid, full)
            add_member(hid, cid, "child")
            for p in parents:
                link_parent_child(p, cid)
            sibs = [c for c in rel.children_of(store, parents[0])
                    if c != cid] if parents else []
            for s in sibs:
                rel.add_edge(store, cid, s, "sibling", game_minutes,
                             trust=40, affection=55, respect=30)
            identity_mod.add_goal(store, cid, "stage", "reach_skill",
                                  {"skill": "subject_knowledge",
                                   "level": 60}, game_minutes)
            stats["children"] += 1
            finish_agent(cid, age)
            return cid

        def elder(age_lo, age_hi, role):
            age = stream.randint(age_lo, age_hi)
            sex = "male" if stream.random() < 0.5 else "female"
            cid, last = new_person(age, sex, None, 1, hid, full)
            add_member(hid, cid, role)
            seed_money(cid, 12000 + stream.randint(0, 18000),
                       "genesis retirement savings")
            stats["elders"] += 1
            finish_agent(cid, age)
            return cid, last

        if archetype == "single":
            adult(22, 55, "head", use_coverage=True)
        elif archetype == "couple":
            a, lasta, agea = adult(24, 58, "head", use_coverage=True)
            b, _, _ = adult(max(21, agea - 6), agea + 6, "member")
            rel.add_edge(store, a, b, "spouse", game_minutes, trust=45,
                         affection=65, respect=45,
                         flags={"met_at": "before_simulation"})
        elif archetype == "couple_children":
            a, lasta, agea = adult(26, 50, "head", use_coverage=True)
            b, _, ageb = adult(max(23, agea - 6), agea + 6, "member")
            rel.add_edge(store, a, b, "spouse", game_minutes, trust=45,
                         affection=65, respect=45,
                         flags={"met_at": "before_simulation"})
            for _ in range(stream.randint(1, 3)):
                child(1, 17, [a, b])
        elif archetype == "single_parent":
            a, _, _ = adult(25, 48, "head", use_coverage=True)
            for _ in range(stream.randint(1, 2)):
                child(2, 15, [a])
        elif archetype == "elder_single":
            elder(66, 85, "head")
        elif archetype == "elder_couple":
            a, _ = elder(66, 84, "head")
            agea = identity_mod.age_years(
                store.row("SELECT born_at_game_minutes FROM characters"
                          " WHERE character_id = ?", (a,))
                ["born_at_game_minutes"], game_minutes)
            b, _ = elder(max(65, agea - 5), agea + 5, "member")
            rel.add_edge(store, a, b, "spouse", game_minutes, trust=50,
                         affection=70, respect=50,
                         flags={"met_at": "before_simulation"})
        elif archetype == "extended":
            a, lasta, agea = adult(28, 45, "head", use_coverage=True)
            b, _, _ = adult(max(24, agea - 6), agea + 6, "member")
            rel.add_edge(store, a, b, "spouse", game_minutes, trust=45,
                         affection=65, respect=45,
                         flags={"met_at": "before_simulation"})
            e, _ = elder(agea + 24, agea + 32, "member")
            link_parent_child(e, a)
            for _ in range(stream.randint(1, 2)):
                child(2, 14, [a, b])
        # Queue 17 Unit DJ: the household's move-in furnishes its
        # home — the F1 "Basic" set (GDD-10 §5: the starter flat
        # seeds at F1) for a head who holds no furniture rows.
        # Genesis places households by direct inserts, not by
        # move_household, so this is the genesis seeding point.
        lost_items_mod.seed_furniture_at_move_in(
            store, data, hid, prop_id, game_minutes)
        stats["households"] += 1

    store.set_world(population_generated=1)
    store.commit()
    return stats
