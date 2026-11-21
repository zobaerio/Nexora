"""Unit 08 — Human Decision-Making Engine.

Decisions are utility-scored choices computed from the decider's own
state — personality (Unit 02), needs (Unit 05), emotions (Unit 06),
memory (Unit 03), relationships (Unit 07), goals and resources — and
every executed decision changes real world state: an employment row
appears, money moves through the ledger, a tenancy ends and another
begins, two people marry, a child is born. Each decision is written
to decision_log with the factors that produced it, so behaviour is
auditable, not asserted.

One decision per adult per day (the highest utility above threshold)
keeps the world legible and the tick cheap. Nothing here is random
for its own sake: randomness enters only through the seeded streams,
as tie-breaking jitter inside the utility scores.
"""
import json

from . import emotions as emotions_mod
from . import lifecycle
from . import memory as memory_mod
from . import personality as personality_mod
from . import relationships as rel

THRESHOLD = 0.35


def log_decision(store, character_id, decision_type, factors, outcome,
                 game_minutes):
    did = store.next_id("DC", "decision_log", "decision_id")
    store.insert("decision_log", decision_id=did,
                 character_id=character_id, decision_type=decision_type,
                 factors=json.dumps(factors, sort_keys=True),
                 outcome=json.dumps(outcome, sort_keys=True),
                 game_minutes=game_minutes)
    return did


def skill_level(store, character_id, skill_id):
    row = store.row("SELECT level FROM character_skills"
                    " WHERE character_id = ? AND skill_id = ?",
                    (character_id, skill_id))
    return row["level"] if row else 0


def add_skill_xp(store, character_id, skill_id, xp):
    row = store.row("SELECT experience FROM character_skills"
                    " WHERE character_id = ? AND skill_id = ?",
                    (character_id, skill_id))
    if row:
        total = row["experience"] + xp
        store.execute("UPDATE character_skills SET experience = ?,"
                      " level = ? WHERE character_id = ? AND skill_id = ?",
                      (total, min(100, total // 50), character_id, skill_id))
    else:
        store.insert("character_skills", character_id=character_id,
                     skill_id=skill_id, level=min(100, xp // 50),
                     experience=xp)


def complete_goals_of_type(store, character_id, goal_type, game_minutes):
    rows = store.rows("SELECT goal_id FROM character_goals"
                      " WHERE character_id = ? AND goal_type = ?"
                      " AND status = 'active'", (character_id, goal_type))
    for r in rows:
        store.execute("UPDATE character_goals SET status = 'completed',"
                      " completed_at_game_minutes = ? WHERE goal_id = ?",
                      (game_minutes, r["goal_id"]))
        memory_mod.record_memory(store, character_id, "goal_complete", 45,
                                 game_minutes)
        emotions_mod.apply_event(store, character_id, "goal_complete")
    return len(rows)


def _employment(store, character_id):
    return store.row("SELECT * FROM employments WHERE character_id = ?"
                     " AND ended_at_game_minutes IS NULL", (character_id,))


def _days_since_decision(store, character_id, decision_type, game_minutes):
    row = store.row("SELECT MAX(game_minutes) AS m FROM decision_log"
                    " WHERE character_id = ? AND decision_type = ?",
                    (character_id, decision_type))
    if row is None or row["m"] is None:
        return None
    return (game_minutes - row["m"]) / 1440.0


def _hire(store, data, character_id, profession_id, game_minutes):
    wage = data.wage(profession_id, "entry")
    eid = store.next_id("EM", "employments", "employment_id")
    store.insert("employments", employment_id=eid,
                 character_id=character_id, profession_id=profession_id,
                 tier=1, wage_per_month=wage,
                 started_at_game_minutes=game_minutes)
    return eid


# -- candidates: each returns (utility, outcome_dict) or None, and
#    executes its world change when chosen by decide() via `run`. ---

def _cand_seek_employment(ctx):
    if ctx["employment"] or ctx["age"] < 18 or ctx["age"] >= 65:
        return None
    fin_def = 100 - ctx["needs"]["financial"]
    u = 0.45 + fin_def / 100 * 0.4 + ctx["profile"]["ambition"] * 0.0015

    def run():
        store, data, cid = ctx["store"], ctx["data"], ctx["cid"]
        best, best_score = None, -1
        for pid, prof in data.professions.items():
            if pid in ("shop_owner", "business_owner"):
                continue
            score = sum(skill_level(store, cid, s)
                        for s in prof["primary_skills"])
            score += ctx["rng"].stream("jobpick", cid,
                                       ctx["day_index"]).uniform(0, 12)
            if pid in ("doctor", "software_developer", "civil_engineer",
                       "pilot"):
                score += ctx["profile"]["intelligence"] * 0.3
            if score > best_score:
                best, best_score = pid, score
        _hire(store, data, cid, best, ctx["game_minutes"])
        memory_mod.log_life_event(store, cid, "job_gain",
                                  ctx["game_minutes"],
                                  details={"profession": best})
        memory_mod.record_memory(store, cid, "job_gain", 30,
                                 ctx["game_minutes"])
        emotions_mod.apply_event(store, cid, "job_gain")
        return {"profession": best}
    return u, run


def _cand_promotion(ctx):
    emp = ctx["employment"]
    if not emp or emp["tier"] >= 5:
        return None
    prof = ctx["data"].professions[emp["profession_id"]]
    threshold = lifecycle.promotion_threshold(prof, emp["tier"])
    if threshold is None:
        return None
    primary = prof["primary_skills"][0]
    level = skill_level(ctx["store"], ctx["cid"], primary)
    if level < threshold:
        return None
    u = 0.4 + ctx["profile"]["ambition"] / 200 + (level - threshold) / 200

    def run():
        store, data = ctx["store"], ctx["data"]
        new_tier = emp["tier"] + 1
        wage = data.wage_at(emp["profession_id"], new_tier)
        store.execute("UPDATE employments SET tier = ?, wage_per_month = ?"
                      " WHERE employment_id = ?",
                      (new_tier, wage, emp["employment_id"]))
        memory_mod.log_life_event(store, ctx["cid"], "promotion",
                                  ctx["game_minutes"],
                                  details={"tier": new_tier})
        memory_mod.record_memory(store, ctx["cid"], "promotion", 40,
                                 ctx["game_minutes"])
        emotions_mod.apply_event(store, ctx["cid"], "promotion")
        complete_goals_of_type(store, ctx["cid"], "reach_skill",
                               ctx["game_minutes"])
        return {"new_tier": new_tier, "wage": wage}
    return u, run


def _cand_train(ctx):
    emp = ctx["employment"]
    if ctx["age"] < 13:
        return None
    if emp:
        prof = ctx["data"].professions[emp["profession_id"]]
        primary = prof["primary_skills"][0]
    elif ctx["age"] <= 17:
        primary = "subject_knowledge"
    else:
        return None
    level = skill_level(ctx["store"], ctx["cid"], primary)
    if level >= 95:
        return None
    dev_def = 100 - ctx["needs"]["development"]
    edu_def = 100 - ctx["needs"]["education"]
    # Training needs a driver: a promotion it unlocks, or a felt
    # deficit. Without one it is not how people spend a day. And it
    # is episodic: no repeat within 6 days unless the deficit is
    # severe (people do not retrain daily for a quarter).
    if emp:
        threshold = lifecycle.promotion_threshold(prof, emp["tier"])
        toward_promotion = threshold is not None and level < threshold
        if not toward_promotion and max(dev_def, edu_def) < 60:
            return None
    since = _days_since_decision(ctx["store"], ctx["cid"], "train",
                                 ctx["game_minutes"])
    if since is not None and since < 6 and max(dev_def, edu_def) < 75:
        return None
    u = 0.3 + ctx["profile"]["ambition"] / 250 \
        + max(dev_def, edu_def) / 250

    def run():
        add_skill_xp(ctx["store"], ctx["cid"], primary, 20)
        emotions_mod.apply_event(ctx["store"], ctx["cid"], "study_gain")
        return {"skill": primary,
                "level": skill_level(ctx["store"], ctx["cid"], primary)}
    return u, run


def _cand_start_business(ctx):
    p = ctx["profile"]
    balance = ctx["store"].balance(ctx["cid"])
    if p["ambition"] < 65 or p["risk_tolerance"] < 55 or balance < 120000:
        return None
    if ctx["employment"] and ctx["employment"]["profession_id"] in (
            "shop_owner", "business_owner"):
        return None
    u = 0.3 + p["ambition"] / 250 + p["risk_tolerance"] / 400

    def run():
        store = ctx["store"]
        cid = ctx["cid"]
        firm = store.balance(cid) >= 300000
        pid = "business_owner" if firm else "shop_owner"
        cost = 120000 if firm else 50000
        bid = store.next_id("BZ", "businesses", "business_id")
        store.insert("businesses", business_id=bid,
                     name=f"{ctx['char']['display_name']} "
                          f"{'Enterprises' if firm else 'Store'}",
                     business_type="company" if firm else "shop",
                     owner_character_id=cid,
                     founded_at_game_minutes=ctx["game_minutes"])
        store.transfer(cid, "SYS-MARKET", cost, "purchase",
                       ctx["game_minutes"], note="business founding costs",
                       related_business_id=bid)
        if ctx["employment"]:
            store.execute("UPDATE employments SET"
                          " ended_at_game_minutes = ?"
                          " WHERE employment_id = ?",
                          (ctx["game_minutes"],
                           ctx["employment"]["employment_id"]))
        _hire(store, ctx["data"], cid, pid, ctx["game_minutes"])
        memory_mod.log_life_event(store, cid, "business_founded",
                                  ctx["game_minutes"],
                                  details={"business_id": bid})
        memory_mod.record_memory(store, cid, "business_founded", 50,
                                 ctx["game_minutes"])
        emotions_mod.apply_event(store, cid, "business_founded")
        complete_goals_of_type(store, cid, "own_company",
                               ctx["game_minutes"])
        complete_goals_of_type(store, cid, "open_business",
                               ctx["game_minutes"])
        return {"business_id": bid, "profession": pid, "cost": cost}
    return u, run


def _household_ctx(ctx):
    store = ctx["store"]
    hid = ctx["char"]["household_id"]
    if not hid:
        return None
    member = store.row("SELECT role FROM household_members"
                       " WHERE household_id = ? AND character_id = ?"
                       " AND left_at_game_minutes IS NULL", (hid, ctx["cid"]))
    tenancy = store.row("SELECT * FROM tenancies WHERE"
                        " tenant_household_id = ?"
                        " AND ended_at_game_minutes IS NULL", (hid,))
    income = store.row(
        "SELECT COALESCE(SUM(e.wage_per_month),0) AS s FROM employments e"
        " JOIN household_members hm ON hm.character_id = e.character_id"
        " WHERE hm.household_id = ? AND hm.left_at_game_minutes IS NULL"
        " AND e.ended_at_game_minutes IS NULL", (hid,))["s"]
    return {"hid": hid, "role": member["role"] if member else None,
            "tenancy": tenancy, "income": income}


def _cand_buy_home(ctx):
    hh = _household_ctx(ctx)
    if not hh or hh["role"] != "head" or not hh["tenancy"]:
        return None
    prop = ctx["store"].row("SELECT * FROM properties WHERE property_id"
                            " = ?", (hh["tenancy"]["property_id"],))
    if not prop or not prop["market_value"]:
        return None
    balance = ctx["store"].balance(ctx["cid"])
    if balance < prop["market_value"] * 1.1:
        return None
    u = 0.3 + ctx["profile"]["ambition"] / 300 \
        + ctx["emotions"]["satisfaction"] / 400

    def run():
        store = ctx["store"]
        price = prop["market_value"]
        store.transfer(ctx["cid"], "SYS-MARKET", price, "purchase",
                       ctx["game_minutes"], note="home purchase",
                       related_property_id=prop["property_id"])
        store.execute("UPDATE properties SET owner_household_id = ?,"
                      " status = 'owned' WHERE property_id = ?",
                      (hh["hid"], prop["property_id"]))
        store.execute("UPDATE tenancies SET ended_at_game_minutes = ?"
                      " WHERE tenancy_id = ?",
                      (ctx["game_minutes"], hh["tenancy"]["tenancy_id"]))
        memory_mod.log_life_event(store, ctx["cid"], "bought_home",
                                  ctx["game_minutes"],
                                  details={"property_id":
                                           prop["property_id"]})
        emotions_mod.apply_event(store, ctx["cid"], "moved_home")
        complete_goals_of_type(store, ctx["cid"], "own_house",
                               ctx["game_minutes"])
        return {"property_id": prop["property_id"], "price": price}
    return u, run


def _cand_marry(ctx):
    if ctx["age"] < 18 or rel.spouse_of(ctx["store"], ctx["cid"]):
        return None
    partners = rel._others(ctx["store"], ctx["cid"], "partner", "from")
    best = None
    for pid in partners:
        edge = rel.get_edge(ctx["store"], ctx["cid"], pid, "partner")
        if edge and edge["affection"] >= 70:
            if best is None or edge["affection"] > best[1]:
                best = (pid, edge["affection"])
    if not best:
        return None
    u = 0.35 + best[1] / 250

    def run():
        rel.marry(ctx["store"], ctx["cid"], best[0], ctx["game_minutes"])
        complete_goals_of_type(ctx["store"], ctx["cid"], "marry",
                               ctx["game_minutes"])
        return {"partner": best[0]}
    return u, run


def _cand_have_child(ctx):
    store = ctx["store"]
    spouse = rel.spouse_of(store, ctx["cid"])
    if not spouse or ctx["age"] < 21 or ctx["age"] > 44:
        return None
    if ctx["char"]["sex"] != "female":
        return None  # decided once per couple, by the mother
    kids = [c for c in rel.children_of(store, ctx["cid"])
            if lifecycle.alive(store, c)]
    if len(kids) >= 4:
        return None
    if ctx["needs"]["financial"] < 40:
        return None
    # A couple that decided to try this month does not re-decide
    # daily: 25-day cooldown after any have_child decision.
    since = _days_since_decision(store, ctx["cid"], "have_child",
                                 ctx["game_minutes"])
    if since is not None and since < 25:
        return None
    # Spacing: no new child within 270 days of the last birth.
    last = store.row("SELECT MAX(game_minutes) AS m FROM life_events"
                     " WHERE character_id = ? AND event_type ="
                     " 'childbirth'", (ctx["cid"],))
    if last and last["m"] is not None \
            and ctx["game_minutes"] - last["m"] < 270 * 1440:
        return None
    u = 0.3 + (4 - len(kids)) * 0.05 \
        + ctx["rng"].stream("family", ctx["cid"],
                            ctx["day_index"] // 30).uniform(0, 0.15)

    def run():
        # Conception is not a certainty: one roll per month.
        roll = ctx["rng"].stream("conceive", ctx["cid"],
                                 ctx["day_index"] // 30).random()
        if roll > 0.18:
            return {"conceived": False}
        child = rel.have_child(store, ctx["rng"], ctx["cid"], spouse,
                               ctx["game_minutes"], ctx["used_names"])
        return {"conceived": True, "child": child}
    return u, run


def _cand_socialise(ctx):
    deficit = 100 - ctx["needs"]["social"]
    if deficit < 55:
        return None
    u = deficit / 110

    def run():
        store = ctx["store"]
        candidates = rel.friends_of(store, ctx["cid"])
        spouse = rel.spouse_of(store, ctx["cid"])
        if spouse:
            candidates = [spouse] + candidates
        if not candidates:
            return {"socialised_with": None}
        target = candidates[0]
        rel.adjust_scores(store, ctx["cid"], target,
                          ctx["game_minutes"], affection=4, trust=2)
        emotions_mod.apply_event(store, ctx["cid"], "social_day")
        return {"socialised_with": target}
    return u, run


def _cand_rest(ctx):
    worst = max(100 - ctx["needs"]["sleep"], 100 - ctx["needs"]["rest"])
    if worst < 70:
        return None
    u = worst / 100

    def run():
        ctx["store"].execute("UPDATE agent_state SET rest_day = 1"
                             " WHERE character_id = ?", (ctx["cid"],))
        return {"rest_day_tomorrow": True}
    return u, run


CANDIDATES = (_cand_seek_employment, _cand_promotion, _cand_train,
              _cand_start_business, _cand_buy_home, _cand_marry,
              _cand_have_child, _cand_socialise, _cand_rest)
# NOTE: a move-house decision is deliberately absent in v1: the
# properties table carries no rent column for vacant units (rents live
# in tenancies + building data), so a cheaper-unit search cannot be
# priced honestly from world state alone. Rather than fake it, moving
# house ships when the property model gains a rent column (schema gap
# recorded in the Session 01 report). Buy-home IS registered: the
# current unit's price is on its property row (market_value).


def decide(store, data, rng, char, day_index, game_minutes, used_names):
    """Pick and execute at most one decision for one adult today.
    Returns the decision_type or None."""
    from .identity import age_years
    from . import needs as needs_mod
    cid = char["character_id"]
    age = age_years(char["born_at_game_minutes"], game_minutes)
    if age < 13:
        return None
    ctx = {
        "store": store, "data": data, "rng": rng, "cid": cid,
        "char": char, "age": age, "day_index": day_index,
        "game_minutes": game_minutes, "used_names": used_names,
        "needs": needs_mod.get_needs(store, cid),
        "emotions": emotions_mod.get_emotions(store, cid),
        "profile": personality_mod.get_profile(store, cid),
        "employment": _employment(store, cid),
    }
    if ctx["needs"] is None or ctx["profile"] is None:
        return None
    best = None
    for cand in CANDIDATES:
        got = cand(ctx)
        if got is None:
            continue
        utility, run = got
        utility += rng.stream("decision-jitter", cid,
                              day_index).uniform(0, 0.03)
        if utility > THRESHOLD and (best is None or utility > best[0]):
            best = (utility, cand.__name__, run)
    if best is None:
        return None
    outcome = best[2]()
    factors = {
        "utility": round(best[0], 3),
        "needs": {k: ctx["needs"][k]
                  for k in ("financial", "social", "sleep", "rest",
                            "safety", "development")},
        "ambition": ctx["profile"]["ambition"],
        "risk_tolerance": ctx["profile"]["risk_tolerance"],
        "balance": store.balance(cid),
    }
    dtype = best[1].replace("_cand_", "")
    log_decision(store, cid, dtype, factors, outcome, game_minutes)
    return dtype
