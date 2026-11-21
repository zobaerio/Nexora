"""Session 09 — Advanced Autonomous AI Civilization &
Collective Intelligence: the coordination layer.

This session builds ONE coordination architecture over the actors
the earlier sessions already created — it recreates nothing:

- Session 01 citizens already decide daily actions through a
  needs/personality engine and keep episodic memory; Session 02
  keeps generational history; Session 04 businesses already price,
  produce, order and hire by recorded rules; Session 05 has a
  government decision engine that fires on measured conditions;
  Session 03 cities compute growth/pressure indicators; Session 08
  monitors the environment and runs disaster responses.

What this layer adds, and only this:

1. An agent REGISTRY over those real actors (citizen, business,
   institution, city, government) with class capabilities — the
   coordination layer's permission model. Capabilities gate this
   layer's own actions (a citizen agent cannot authorise a policy
   action; the attempt is recorded as a failed action and raises).
   This is in-simulation data only: nothing here touches real
   platform access (the Session 05 separation rule).
2. Extended personal GOALS on character_goals (priority,
   feasibility, progress, deadline, dependencies, completion
   rule): derived from measured state, progressed from real
   events, completed/abandoned by record. The top-priority goal
   receives a monthly step action; for savings/home goals the step
   is a real bank deposit through Session 04's bank.
3. Structured NEGOTIATION: wage negotiation at hiring (Session 04
   labour), with objectives, constraints, offers, responses and
   outcomes persisted, and bounded learning on both sides.
4. Supplier SELECTION by measured reliability (recorded supply
   orders), with a decision explanation per order.
5. ASSESSMENTS: a periodic city/national cycle that identifies
   problems from measured indicators, links the funded action an
   existing engine takes, and later evaluates the same indicator —
   a closed loop, recorded end to end.
6. Multi-level MEMORY: family (household), organisational
   (business), community (city) and civilization (national)
   records with importance, bounded caps and compression; family
   memory of a business failure measurably changes goal
   derivation (the business goal's priority is cut — retrieval
   changing a decision, test-proven).
7. FORECASTS: transparent linear-trend projections (labelled SIM
   MODEL) stored with their inputs and later SCORED against the
   actual outcome — forecast and outcome are different records.
8. Emergency COORDINATION: when a Session 08 disaster is active,
   a task sequence (assess, evacuate, shelter, relief, medical,
   repair, review) tracks Session 08's own response records;
   overdue tasks escalate by message to the government agent;
   tasks left unmet when a disaster recovers are closed as unmet
   with a completed review task — failure is recorded and
   replanned, never hidden.
9. Bounded LEARNING: defined parameters only (employer wage
   acceptance cap, candidate premium factor, goal priorities),
   each change logged in agent_learning with its reason. No code
   is ever modified; no external model is ever called — every
   decision in this layer is a deterministic rule over recorded
   state, per the owner's three-tier doctrine (this layer is the
   Advanced Agent / Civilization tier's bookkeeping, not an LLM).

Deterministic ordering everywhere (actors processed in id order);
additive tables only; every pass no-ops when the layer was never
set up, so hand-built worlds from earlier sessions are untouched.
"""
import json

from . import cities as cities_mod

# Goal types this layer derives (goal_kind is always "agent" for
# derived goals; genesis goals keep their own kinds and are only
# progressed/completed here, never abandoned by this layer).
DERIVED_TYPES = ("find_employment", "complete_education",
                 "save_amount", "own_house", "reach_skill")

MAJOR_LIFE_EVENTS = None  # read from config at call time


def cfg(data):
    return data.agents_config


def is_setup(store):
    row = store.row("SELECT agents_setup FROM world_state")
    return bool(row and row["agents_setup"])


# ---------------------------------------------------------------------
# Registry + permissions
# ---------------------------------------------------------------------

def agent_id(agent_class, ref_id):
    return f"AG:{agent_class}:{ref_id}"


def capabilities_of(data, agent_class):
    return list(cfg(data)["capabilities"].get(agent_class, []))


def _register(store, data, agent_class, ref_id, display_name,
              game_minutes):
    aid = agent_id(agent_class, ref_id)
    existing = store.row("SELECT agent_id FROM agent_registry"
                         " WHERE agent_id = ?", (aid,))
    if existing:
        return aid
    store.insert(
        "agent_registry", agent_id=aid, agent_class=agent_class,
        ref_id=ref_id, display_name=display_name or "",
        capabilities=json.dumps(capabilities_of(data, agent_class)),
        status="active", registered_at_game_minutes=game_minutes,
        updated_at_game_minutes=game_minutes)
    return aid


def sync_registry(store, data, game_minutes):
    """Register every real actor that exists now and refresh the
    status of actors that have died/closed since. Idempotent."""
    counts = {"citizen": 0, "business": 0, "institution": 0,
              "city": 0, "government": 0}
    for c in store.rows("SELECT character_id, display_name,"
                        " died_at_game_minutes FROM characters"
                        " WHERE is_system = 0 ORDER BY character_id"):
        aid = _register(store, data, "citizen", c["character_id"],
                        c["display_name"], game_minutes)
        counts["citizen"] += 1
        _set_status(store, aid,
                    "inactive" if c["died_at_game_minutes"]
                    else "active", game_minutes)
    for b in store.rows("SELECT business_id, name,"
                        " closed_at_game_minutes FROM businesses"
                        " ORDER BY business_id"):
        aid = _register(store, data, "business", b["business_id"],
                        b["name"], game_minutes)
        counts["business"] += 1
        _set_status(store, aid,
                    "inactive" if b["closed_at_game_minutes"]
                    else "active", game_minutes)
    for t in ("institutions", "educational_institutions",
              "healthcare_facilities"):
        idcol = {"institutions": "institution_id",
                 "educational_institutions": "institution_id",
                 "healthcare_facilities": "facility_id"}[t]
        try:
            rows = store.rows(f"SELECT * FROM {t}")
        except Exception:
            rows = []
        for r in rows:
            _register(store, data, "institution", r[idcol],
                      r["name"] if "name" in r.keys() else "",
                      game_minutes)
            counts["institution"] += 1
    if cities_mod.is_setup(store):
        for spec in data.city_specs():
            _register(store, data, "city", spec["city_id"],
                      spec.get("name", spec["city_id"]), game_minutes)
            counts["city"] += 1
    for ctry in store.rows("SELECT country_id, name FROM countries"):
        _register(store, data, "government", ctry["country_id"],
                  ctry["name"], game_minutes)
        counts["government"] += 1
    return counts


def _set_status(store, aid, status, game_minutes):
    store.execute("UPDATE agent_registry SET status = ?,"
                  " updated_at_game_minutes = ? WHERE agent_id = ?"
                  " AND status != ?",
                  (status, game_minutes, aid, status))


def setup_agents(store, data, game_minutes=480):
    """Seed the coordination layer with the world (idempotent).
    Hand-built worlds that never call this have no agent layer
    and every Session 09 pass no-ops."""
    counts = sync_registry(store, data, game_minutes)
    store.set_world(agents_setup=1)
    return counts


def class_capabilities(data, agent_class):
    return capabilities_of(data, agent_class)


def require_capability(store, data, agent_class, ref_id, capability,
                       action_kind, game_minutes):
    """The permission gate for this layer's actions. A permitted
    attempt is recorded as a successful agent action; a denied
    attempt is recorded as a FAILED action and raises
    PermissionError — denials are audit records, not silent no-ops.
    """
    caps = class_capabilities(data, agent_class)
    aid = agent_id(agent_class, ref_id)
    if capability not in caps:
        log_agent_action(store, aid, action_kind, "failed",
                         {"reason": "permission_denied",
                          "capability": capability,
                          "agent_class": agent_class}, game_minutes)
        raise PermissionError(
            f"{agent_class} agent {ref_id} lacks capability"
            f" '{capability}'")
    log_agent_action(store, aid, action_kind, "success",
                     {"capability": capability}, game_minutes)
    return aid


# ---------------------------------------------------------------------
# Small record helpers
# ---------------------------------------------------------------------

def log_agent_action(store, agent_ref, action_kind, status, details,
                     game_minutes):
    aid = store.next_id("AA", "agent_actions", "action_id")
    store.insert("agent_actions", action_id=aid, agent_ref=agent_ref,
                 action_kind=action_kind, status=status,
                 details=json.dumps(details or {}, sort_keys=True),
                 game_minutes=game_minutes)
    return aid


def log_agent_decision(store, agent_ref, agent_class, decision_kind,
                       inputs, rule, outcome, game_minutes):
    rid = store.next_id("AD", "agent_decisions", "record_id")
    store.insert("agent_decisions", record_id=rid,
                 agent_ref=agent_ref, agent_class=agent_class,
                 decision_kind=decision_kind,
                 inputs=json.dumps(inputs or {}, sort_keys=True),
                 rule=rule,
                 outcome=json.dumps(outcome or {}, sort_keys=True),
                 game_minutes=game_minutes)
    return rid


def send_message(store, from_ref, to_ref, kind, payload, game_minutes):
    mid = store.next_id("MS", "agent_messages", "message_id")
    store.insert("agent_messages", message_id=mid, from_ref=from_ref,
                 to_ref=to_ref, kind=kind,
                 payload=json.dumps(payload or {}, sort_keys=True),
                 game_minutes=game_minutes)
    return mid


# ---------------------------------------------------------------------
# Bounded learning parameters
# ---------------------------------------------------------------------

def get_param(store, owner_ref, param, default):
    row = store.row("SELECT value FROM agent_params WHERE"
                    " owner_ref = ? AND param = ?",
                    (owner_ref, param))
    return row["value"] if row else default


def set_param(store, owner_ref, param, new_value, bounds, reason,
              game_minutes):
    """Set a learned parameter inside its bounds; every change is
    an agent_learning row with the reason. Returns the value."""
    lo, hi = bounds
    new_value = max(lo, min(hi, new_value))
    old = get_param(store, owner_ref, param, None)
    if old is None:
        store.insert("agent_params", owner_ref=owner_ref, param=param,
                     value=new_value)
        old = new_value
    else:
        store.execute("UPDATE agent_params SET value = ? WHERE"
                      " owner_ref = ? AND param = ?",
                      (new_value, owner_ref, param))
    if new_value != old:
        rid = store.next_id("LR", "agent_learning", "record_id")
        store.insert("agent_learning", record_id=rid,
                     owner_ref=owner_ref, param=param,
                     old_value=old, new_value=new_value,
                     reason=json.dumps(reason or {}, sort_keys=True),
                     game_minutes=game_minutes)
    return new_value


# ---------------------------------------------------------------------
# Multi-level memory (family / organisation / community / civilization)
# ---------------------------------------------------------------------

# SIM MODEL importance weights for recorded memory kinds.
IMPORTANCE = {
    "childbirth": 60, "death": 90, "marriage": 80, "job_gain": 40,
    "business_founded": 55, "business_closed": 70, "bought_home": 65,
    "financial_distress": 50, "moved_home": 35, "promotion": 45,
    "distress": 55, "recovered": 45, "closed": 70, "layoff": 40,
    "resignation": 30, "rent_unpaid": 35, "registered": 30,
    "election": 65, "crisis": 70, "disaster": 75,
    "compressed_summary": 30,
}


def record_agent_memory(store, level, owner_ref, event_kind, summary,
                        importance, game_minutes):
    """Record one memory at one level. Deduplicated on the
    summary's 'ref' (the source record id) when present, so passes
    can re-run over the same window without duplicating."""
    summary = summary or {}
    ref = summary.get("ref")
    if ref is not None:
        for r in store.rows("SELECT summary FROM agent_memories"
                            " WHERE level = ? AND owner_ref = ?"
                            " AND event_kind = ?",
                            (level, owner_ref, event_kind)):
            if json.loads(r["summary"] or "{}").get("ref") == ref:
                return None
    mid = store.next_id("AM", "agent_memories", "memory_id")
    store.insert("agent_memories", memory_id=mid, level=level,
                 owner_ref=owner_ref, event_kind=event_kind,
                 summary=json.dumps(summary, sort_keys=True),
                 importance=int(importance),
                 created_at_game_minutes=game_minutes,
                 updated_at_game_minutes=game_minutes)
    return mid


def retrieve_memories(store, level, owner_ref, event_kind=None,
                      limit=5):
    """Importance-ranked retrieval; every retrieval is counted —
    access is part of the record, and the goal pass's use of
    family memory is the layer's proven retrieval consumer."""
    if event_kind:
        rows = store.rows(
            "SELECT * FROM agent_memories WHERE level = ? AND"
            " owner_ref = ? AND event_kind = ? ORDER BY importance"
            " DESC, updated_at_game_minutes DESC LIMIT ?",
            (level, owner_ref, event_kind, limit))
    else:
        rows = store.rows(
            "SELECT * FROM agent_memories WHERE level = ? AND"
            " owner_ref = ? ORDER BY importance DESC,"
            " updated_at_game_minutes DESC LIMIT ?",
            (level, owner_ref, limit))
    for r in rows:
        store.execute("UPDATE agent_memories SET access_count ="
                      " access_count + 1 WHERE memory_id = ?",
                      (r["memory_id"],))
    return rows


def compress_memories(store, level, owner_ref, cap, threshold,
                      game_minutes):
    """Bounded retention: above the cap, the oldest memories below
    the importance threshold are merged into one compressed
    summary record; if still above the cap, the least important
    are forgotten (the Session 01 episodic rule, one level up)."""
    rows = store.rows("SELECT * FROM agent_memories WHERE level = ?"
                      " AND owner_ref = ? ORDER BY importance ASC,"
                      " created_at_game_minutes ASC",
                      (level, owner_ref))
    if len(rows) <= cap:
        return 0
    merged = 0
    low = [r for r in rows
           if r["importance"] < threshold
           and r["event_kind"] != "compressed_summary"]
    excess = len(rows) - cap
    if len(low) >= 2 and excess > 0:
        take = low[:excess + 1]
        kinds = {}
        for r in take:
            kinds[r["event_kind"]] = kinds.get(r["event_kind"], 0) + 1
        record_agent_memory(
            store, level, owner_ref, "compressed_summary",
            {"merged_kinds": kinds, "merged_count": len(take),
             "ref": f"compressed:{owner_ref}:"
                    f"{take[0]['memory_id']}:{take[-1]['memory_id']}"},
            max(r["importance"] for r in take), game_minutes)
        for r in take:
            store.execute("DELETE FROM agent_memories WHERE"
                          " memory_id = ?", (r["memory_id"],))
        merged = len(take)
        rows = store.rows("SELECT * FROM agent_memories WHERE"
                          " level = ? AND owner_ref = ? ORDER BY"
                          " importance ASC,"
                          " created_at_game_minutes ASC",
                          (level, owner_ref))
    while len(rows) > cap:
        store.execute("DELETE FROM agent_memories WHERE memory_id"
                      " = ?", (rows[0]["memory_id"],))
        rows = rows[1:]
        merged += 1
    return merged


def _household_members(store, household_id):
    return [r["character_id"] for r in store.rows(
        "SELECT character_id FROM household_members WHERE"
        " household_id = ? AND left_at_game_minutes IS NULL",
        (household_id,))]


def memory_pass(store, data, month_index, game_minutes):
    """Monthly: lift the month's major events into the family,
    organisational, community and civilization memory levels,
    then enforce each level's cap. Window: the last 31 days."""
    mcfg = cfg(data)["memory"]
    since = game_minutes - 31 * 1440
    major = set(mcfg["major_life_events"])
    out = {"family": 0, "organisation": 0, "community": 0,
           "civilization": 0, "compressed": 0}
    # Family: major life events of the household's members, plus
    # closures of businesses any member owns.
    for h in store.rows("SELECT household_id FROM households WHERE"
                        " dissolved_at_game_minutes IS NULL"
                        " ORDER BY household_id"):
        hid = h["household_id"]
        members = _household_members(store, hid)
        if not members:
            continue
        marks = ",".join("?" for _ in members)
        for ev in store.rows(
                f"SELECT * FROM life_events WHERE character_id IN"
                f" ({marks}) AND game_minutes >= ? ORDER BY"
                f" event_id", tuple(members) + (since,)):
            if ev["event_type"] not in major:
                continue
            mid = record_agent_memory(
                store, "family", hid, ev["event_type"],
                {"ref": ev["event_id"], "character_id":
                 ev["character_id"],
                 "details": json.loads(ev["details"] or "{}")},
                IMPORTANCE.get(ev["event_type"], 30), game_minutes)
            if mid:
                out["family"] += 1
        for b in store.rows(
                f"SELECT b.business_id FROM businesses b WHERE"
                f" b.owner_character_id IN ({marks})",
                tuple(members)):
            for ev in store.rows(
                    "SELECT * FROM business_events WHERE"
                    " business_id = ? AND event_type = 'closed'"
                    " AND game_minutes >= ?",
                    (b["business_id"], since)):
                mid = record_agent_memory(
                    store, "family", hid, "business_closed",
                    {"ref": ev["event_id"],
                     "business_id": b["business_id"]},
                    IMPORTANCE["business_closed"], game_minutes)
                if mid:
                    out["family"] += 1
        out["compressed"] += compress_memories(
            store, "family", hid, mcfg["family_cap"],
            mcfg["compress_below_importance"], game_minutes)
    # Organisation: the month's business events per business.
    for b in store.rows("SELECT business_id FROM businesses"
                        " ORDER BY business_id"):
        bid = b["business_id"]
        for ev in store.rows(
                "SELECT * FROM business_events WHERE business_id"
                " = ? AND game_minutes >= ? ORDER BY event_id",
                (bid, since)):
            if ev["event_type"] == "registered":
                continue
            mid = record_agent_memory(
                store, "organisation", bid, ev["event_type"],
                {"ref": ev["event_id"],
                 "details": json.loads(ev["details"] or "{}")},
                IMPORTANCE.get(ev["event_type"], 30), game_minutes)
            if mid:
                out["organisation"] += 1
        out["compressed"] += compress_memories(
            store, "organisation", bid, mcfg["organisation_cap"],
            mcfg["compress_below_importance"], game_minutes)
    # Community: major life events per city (via household zone).
    if cities_mod.is_setup(store):
        for spec in data.city_specs():
            cid = spec["city_id"]
            zones = list(spec.get("zones") or [])
            if not zones:
                continue
            marks = ",".join("?" for _ in zones)
            for ev in store.rows(
                    f"SELECT le.* FROM life_events le JOIN"
                    f" characters c ON c.character_id ="
                    f" le.character_id JOIN households h ON"
                    f" h.household_id = c.household_id WHERE"
                    f" h.district_id IN ({marks}) AND"
                    f" le.game_minutes >= ? ORDER BY le.event_id",
                    tuple(zones) + (since,)):
                if ev["event_type"] not in major:
                    continue
                mid = record_agent_memory(
                    store, "community", cid, ev["event_type"],
                    {"ref": ev["event_id"], "character_id":
                     ev["character_id"]},
                    IMPORTANCE.get(ev["event_type"], 30),
                    game_minutes)
                if mid:
                    out["community"] += 1
            out["compressed"] += compress_memories(
                store, "community", cid, mcfg["community_cap"],
                mcfg["compress_below_importance"], game_minutes)
    # Civilization: elections, crises, disasters — once each.
    country = store.row("SELECT country_id FROM countries LIMIT 1")
    if country:
        ref = country["country_id"]
        for e in store.rows("SELECT election_id, status FROM"
                            " elections ORDER BY election_id"):
            mid = record_agent_memory(
                store, "civilization", ref, "election",
                {"ref": e["election_id"], "status": e["status"]},
                IMPORTANCE["election"], game_minutes)
            if mid:
                out["civilization"] += 1
        for c in store.rows("SELECT crisis_id, crisis_type, status"
                            " FROM crisis_records ORDER BY"
                            " crisis_id"):
            mid = record_agent_memory(
                store, "civilization", ref, "crisis",
                {"ref": c["crisis_id"], "kind": c["crisis_type"],
                 "status": c["status"]},
                IMPORTANCE["crisis"], game_minutes)
            if mid:
                out["civilization"] += 1
        for d in store.rows("SELECT disaster_id, disaster_type,"
                            " status FROM disaster_events ORDER BY"
                            " disaster_id"):
            mid = record_agent_memory(
                store, "civilization", ref, "disaster",
                {"ref": d["disaster_id"],
                 "disaster_type": d["disaster_type"],
                 "status": d["status"]},
                IMPORTANCE["disaster"], game_minutes)
            if mid:
                out["civilization"] += 1
        out["compressed"] += compress_memories(
            store, "civilization", ref, mcfg["civilization_cap"],
            mcfg["compress_below_importance"], game_minutes)
    return out


# ---------------------------------------------------------------------
# Extended personal goals (on character_goals)
# ---------------------------------------------------------------------

def _employment_of(store, cid):
    return store.row("SELECT * FROM employments WHERE character_id"
                     " = ? AND ended_at_game_minutes IS NULL", (cid,))


def _citizen_state(store, data, char, game_minutes):
    from . import identity as identity_mod
    from . import education as education_mod
    cid = char["character_id"]
    age = identity_mod.age_years(char["born_at_game_minutes"],
                                 game_minutes)
    hid = char["household_id"]
    role = None
    tenancy = None
    owned = False
    if hid:
        m = store.row("SELECT role FROM household_members WHERE"
                      " household_id = ? AND character_id = ? AND"
                      " left_at_game_minutes IS NULL", (hid, cid))
        role = m["role"] if m else None
        tenancy = store.row("SELECT * FROM tenancies WHERE"
                            " tenant_household_id = ? AND"
                            " ended_at_game_minutes IS NULL", (hid,))
        owned = bool(store.row(
            "SELECT 1 FROM properties WHERE owner_household_id = ?"
            " OR owner_character_id = ? LIMIT 1", (hid, cid)))
    profile = store.row("SELECT ambition, risk_tolerance FROM"
                        " personality_profiles WHERE character_id"
                        " = ?", (cid,))
    return {
        "cid": cid, "age": age, "hid": hid, "role": role,
        "tenancy": tenancy, "owned": owned,
        "employment": _employment_of(store, cid),
        "balance": store.balance(cid),
        "enrolment": education_mod.college_enrolment(store, cid),
        "profile": profile,
        "owns_business": bool(store.row(
            "SELECT 1 FROM businesses WHERE owner_character_id = ?"
            " AND closed_at_game_minutes IS NULL LIMIT 1", (cid,))),
    }


def _goal_progress(store, data, goal, st, game_minutes):
    """Measured progress for one goal. Returns (progress, measured,
    done). Every number comes from a live record — balances,
    employments, enrolments, skill rows, property ownership."""
    from . import decisions as decisions_mod
    from . import education as education_mod
    from . import lifecycle
    from . import relationships as rel
    cid = st["cid"]
    gtype = goal["goal_type"]
    target = json.loads(goal["target"] or "{}")
    if gtype == "find_employment":
        apps = store.row(
            "SELECT COUNT(*) AS n FROM job_applications WHERE"
            " character_id = ? AND game_minutes >= ?",
            (cid, game_minutes - 31 * 1440))["n"]
        return (1.0 if st["employment"] else (0.5 if apps else 0.2),
                {"employed": bool(st["employment"]),
                 "applications_31d": apps},
                bool(st["employment"]))
    if gtype == "save_amount":
        amount = target.get("amount", 0)
        if not amount:
            return goal["progress"] or 0.0, {"target_missing": True}, \
                False
        return (min(1.0, st["balance"] / amount),
                {"balance": st["balance"], "target": amount},
                st["balance"] >= amount)
    if gtype == "own_house":
        if st["owned"]:
            return 1.0, {"owned": True}, True
        price = 0
        if st["tenancy"]:
            prop = store.row("SELECT market_value FROM properties"
                             " WHERE property_id = ?",
                             (st["tenancy"]["property_id"],))
            price = prop["market_value"] if prop else 0
        prog = min(0.95, st["balance"] / price) if price else 0.0
        return prog, {"owned": False, "balance": st["balance"],
                      "price": price}, False
    if gtype == "complete_education":
        enr = st["enrolment"]
        if enr is None:
            done = any(education_mod.has_credential(store, cid, pid)
                       for pid in education_mod.GATED_PROGRAMMES)
            return (1.0 if done else goal["progress"] or 0.0,
                    {"enrolled": False, "credential": done}, done)
        months = max(0.0, (game_minutes
                           - enr["started_at_game_minutes"])
                   / (30 * 1440))
        # SIM MODEL: a college programme is measured against a
        # 24-month nominal duration (no duration exists in the
        # education data); completion itself is the record's own
        # status, checked above and in education's sweep.
        return (min(0.95, months / 24.0),
                {"enrolled": True, "programme": enr["programme"],
                 "months_enrolled": round(months, 1)}, False)
    if gtype == "reach_skill":
        skill = target.get("skill")
        level_target = target.get("level")
        if not skill:
            emp = st["employment"]
            if emp:
                prof = data.professions[emp["profession_id"]]
                skill = prof["primary_skills"][0]
                level_target = lifecycle.promotion_threshold(
                    prof, emp["tier"]) or 100
            else:
                return goal["progress"] or 0.0, {}, False
        level = decisions_mod.skill_level(store, cid, skill)
        return (min(1.0, level / level_target) if level_target
                else 0.0,
                {"skill": skill, "level": level,
                 "target_level": level_target},
                level_target is not None and level >= level_target)
    if gtype in ("open_business", "own_company"):
        if st["owns_business"]:
            return 1.0, {"owns_business": True}, True
        return (min(0.9, st["balance"] / 50000),
                {"owns_business": False, "balance": st["balance"],
                 "founding_cost_reference": 50000}, False)
    if gtype == "marry":
        spouse = rel.spouse_of(store, cid)
        if spouse:
            return 1.0, {"married": True}, True
        best = 0
        for pid in rel._others(store, cid, "partner", "from"):
            edge = rel.get_edge(store, cid, pid, "partner")
            if edge:
                best = max(best, edge["affection"])
        return min(0.95, best / 100), {"best_affection": best}, False
    return goal["progress"] or 0.0, {"note": "no monthly measure"}, \
        False


def _derive_goal(store, data, st, goal_type, priority, target,
                 feasibility, completion_rule, game_minutes, out):
    from . import identity as identity_mod
    cid = st["cid"]
    recent_abandon = store.row(
        "SELECT 1 FROM character_goals WHERE character_id = ? AND"
        " goal_type = ? AND status = 'abandoned' AND"
        " created_at_game_minutes >= ? LIMIT 1",
        (cid, goal_type, game_minutes - 180 * 1440))
    if recent_abandon:
        return None
    gid = identity_mod.add_goal(store, cid, "agent", goal_type,
                                target, game_minutes)
    gcfg = cfg(data)["goals"]
    store.execute(
        "UPDATE character_goals SET priority = ?, feasibility = ?,"
        " deadline_game_minutes = ?, dependencies = '[]',"
        " completion_rule = ? WHERE goal_id = ?",
        (priority, json.dumps(feasibility, sort_keys=True),
         game_minutes + gcfg["derived_deadline_months"] * 30 * 1440,
         completion_rule, gid))
    # The baseline progress is the CURRENT measured progress, so
    # priority adaptation later reacts to change between months —
    # never to the initial measurement itself.
    row = store.row("SELECT * FROM character_goals WHERE goal_id"
                    " = ?", (gid,))
    progress, _measured, _done = _goal_progress(store, data, row,
                                                st, game_minutes)
    store.execute("UPDATE character_goals SET progress = ? WHERE"
                  " goal_id = ?", (round(progress, 4), gid))
    out["derived"] += 1
    return gid


def goals_pass(store, data, rng, month_index, game_minutes):
    """Monthly goal cycle: derive goals from measured state,
    progress them from real records, complete/abandon by record,
    adapt derived priorities (bounded learning), and give the
    top-priority goal one real step action."""
    from . import banking as banking_mod
    from . import business as business_mod
    from . import decisions as decisions_mod
    from . import emotions as emotions_mod
    from . import memory as memory_mod
    gcfg = cfg(data)["goals"]
    pmin, pmax = gcfg["priority_bounds"]
    out = {"derived": 0, "progressed": 0, "completed": 0,
           "abandoned": 0, "steps": 0}
    chars = store.rows("SELECT * FROM characters WHERE is_system = 0"
                       " AND died_at_game_minutes IS NULL ORDER BY"
                       " character_id")
    for char in chars:
        st = _citizen_state(store, data, char, game_minutes)
        cid = st["cid"]
        if st["age"] < 13:
            continue
        active = {g["goal_type"]: g for g in store.rows(
            "SELECT * FROM character_goals WHERE character_id = ?"
            " AND status = 'active' ORDER BY priority DESC",
            (cid,))}
        # -- derivation from measured state ----------------------
        if st["age"] >= 18 and st["age"] < 65 \
                and not st["employment"] and not st["enrolment"] \
                and "find_employment" not in active:
            _derive_goal(
                store, data, st, "find_employment", 80, {},
                {"required": {"status": "employed"},
                 "current": {"balance": st["balance"]},
                 "feasible": True},
                "an active employment row exists", game_minutes, out)
        if st["enrolment"] and "complete_education" not in active:
            _derive_goal(
                store, data, st, "complete_education", 70,
                {"programme": st["enrolment"]["programme"]},
                {"required": {"status": "completed"},
                 "current": {"programme":
                             st["enrolment"]["programme"]},
                 "feasible": True},
                "the education record completes", game_minutes, out)
        emp = st["employment"]
        if emp and "save_amount" not in active:
            amount = emp["wage_per_month"] \
                * gcfg["savings_target_wage_months"]
            if st["balance"] < amount:
                _derive_goal(
                    store, data, st, "save_amount", 55,
                    {"amount": amount},
                    {"required": {"amount": amount},
                     "current": {"balance": st["balance"]},
                     "feasible": True},
                    "balance reaches the target amount",
                    game_minutes, out)
        if st["role"] == "head" and st["tenancy"] \
                and not st["owned"] and "own_house" not in active:
            prop = store.row("SELECT market_value FROM properties"
                             " WHERE property_id = ?",
                             (st["tenancy"]["property_id"],))
            price = prop["market_value"] if prop else 0
            if price and st["balance"] >= price * gcfg[
                    "home_progress_min_balance_ratio"]:
                _derive_goal(
                    store, data, st, "own_house", 65,
                    {"property_id": st["tenancy"]["property_id"]},
                    {"required": {"price": price},
                     "current": {"balance": st["balance"]},
                     "feasible": True},
                    "the household owns a property", game_minutes,
                    out)
        if emp and "reach_skill" not in active:
            from . import lifecycle
            prof = data.professions[emp["profession_id"]]
            threshold = lifecycle.promotion_threshold(prof,
                                                      emp["tier"])
            if threshold:
                level = decisions_mod.skill_level(
                    store, cid, prof["primary_skills"][0])
                if level < threshold:
                    _derive_goal(
                        store, data, st, "reach_skill", 50,
                        {"skill": prof["primary_skills"][0],
                         "level": threshold},
                        {"required": {"level": threshold},
                         "current": {"level": level},
                         "feasible": True},
                        "skill level reaches the promotion threshold",
                        game_minutes, out)
        prof = st["profile"]
        if prof and not st["owns_business"] \
                and "open_business" not in active \
                and "own_company" not in active \
                and 21 <= st["age"] <= 60 \
                and prof["ambition"] >= 65 \
                and prof["risk_tolerance"] >= 55 \
                and st["balance"] >= 50000:
            priority = 60
            feasibility = {"required": {"capital": 50000},
                           "current": {"balance": st["balance"]},
                           "feasible": True, "risks": []}
            # RETRIEVAL CHANGES A DECISION: the household's family
            # memory of a business closure is read here, and it
            # cuts the derived goal's priority (and so whether the
            # goal wins the monthly step and how it ranks) — the
            # same citizen without that memory keeps priority 60.
            if st["hid"]:
                failures = retrieve_memories(
                    store, "family", st["hid"], "business_closed",
                    limit=1)
                if failures:
                    priority -= gcfg[
                        "business_failure_memory_priority_cut"]
                    feasibility["risks"] = [
                        "household_business_failure_memory"]
                    feasibility["feasible"] = priority >= 40
                    feasibility["memory_ref"] = \
                        failures[0]["memory_id"]
            _derive_goal(
                store, data, st, "open_business", priority,
                {"min_capital": 50000}, feasibility,
                "the citizen owns an active business",
                game_minutes, out)
        # -- progress / completion / abandonment -----------------
        goals = store.rows(
            "SELECT * FROM character_goals WHERE character_id = ?"
            " AND status = 'active' ORDER BY priority DESC, goal_id",
            (cid,))
        top_goal = None
        for goal in goals:
            progress, measured, done = _goal_progress(
                store, data, goal, st, game_minutes)
            old_progress = goal["progress"] or 0.0
            if done:
                store.execute(
                    "UPDATE character_goals SET status ="
                    " 'completed', progress = 1.0,"
                    " completed_at_game_minutes = ? WHERE goal_id"
                    " = ?", (game_minutes, goal["goal_id"]))
                memory_mod.record_memory(store, cid, "goal_complete",
                                         45, game_minutes)
                emotions_mod.apply_event(store, cid, "goal_complete")
                out["completed"] += 1
                _log_goal_progress(store, goal, 1.0, measured,
                                   game_minutes)
                continue
            if goal["goal_kind"] == "agent" \
                    and goal["deadline_game_minutes"] \
                    and game_minutes > goal["deadline_game_minutes"] \
                    and progress < gcfg["abandon_progress_below"]:
                store.execute(
                    "UPDATE character_goals SET status = 'abandoned'"
                    " WHERE goal_id = ?", (goal["goal_id"],))
                out["abandoned"] += 1
                _log_goal_progress(store, goal, progress,
                                   {**measured, "abandoned": True},
                                   game_minutes)
                continue
            priority = goal["priority"]
            if goal["goal_kind"] == "agent":
                if progress > old_progress + 0.001:
                    new_priority = min(pmax, priority + gcfg[
                        "priority_progress_gain"])
                elif game_minutes - goal[
                        "created_at_game_minutes"] > 30 * 1440:
                    new_priority = max(pmin, priority - gcfg[
                        "priority_stall_loss"])
                else:
                    new_priority = priority
                if new_priority != priority:
                    set_param(store, goal["goal_id"], "goal_priority",
                              new_priority, (pmin, pmax),
                              {"progress_delta": round(
                                  progress - old_progress, 3),
                               "goal_type": goal["goal_type"]},
                              game_minutes)
                    priority = new_priority
            if abs(progress - old_progress) >= 0.01 \
                    or priority != goal["priority"]:
                store.execute(
                    "UPDATE character_goals SET progress = ?,"
                    " priority = ? WHERE goal_id = ?",
                    (round(progress, 4), priority, goal["goal_id"]))
                _log_goal_progress(store, goal, progress, measured,
                                   game_minutes)
                out["progressed"] += 1
            if top_goal is None:
                top_goal = (priority, goal)
        # -- one step toward the top-priority goal ---------------
        if top_goal is not None:
            _goal_step(store, data, st, top_goal[1], month_index,
                       game_minutes, out)
    return out


def _log_goal_progress(store, goal, progress, measured, game_minutes):
    lid = store.next_id("GP", "goal_progress_log", "log_id")
    store.insert("goal_progress_log", log_id=lid,
                 goal_id=goal["goal_id"],
                 character_id=goal["character_id"],
                 progress=round(progress, 4),
                 measured=json.dumps(measured or {}, sort_keys=True),
                 game_minutes=game_minutes)


def _goal_step(store, data, st, goal, month_index, game_minutes,
               out):
    """The monthly step toward the citizen's top-priority goal.
    For savings/home goals the step is real money: a deposit into
    the citizen's Session 04 bank account. A missing account is a
    recorded failed action (retried next month), never a silent
    skip."""
    from . import banking as banking_mod
    from . import business as business_mod
    from . import decisions as decisions_mod
    if goal["goal_type"] not in ("save_amount", "own_house"):
        return
    if not business_mod.is_setup(store):
        return
    cid = st["cid"]
    aid = agent_id("citizen", cid)
    if banking_mod.account_of(store, cid) is None:
        log_agent_action(store, aid, "goal_step", "failed",
                         {"goal_id": goal["goal_id"],
                          "reason": "no_bank_account",
                          "replan": "retry_next_month"},
                         game_minutes)
        return
    surplus = st["balance"] - 5000  # keep-back (SIM MODEL)
    amount = round(surplus * cfg(data)["goals"][
        "goal_step_deposit_ratio"]) if surplus > 0 else 0
    if amount < 500:
        return
    moved = banking_mod.deposit(
        store, cid, amount, game_minutes,
        event_ref=f"goal:{goal['goal_id']}:{month_index}")
    if moved:
        log_agent_action(store, aid, "goal_step", "success",
                         {"goal_id": goal["goal_id"],
                          "goal_type": goal["goal_type"],
                          "deposited_ncr": moved}, game_minutes)
        decisions_mod.log_decision(
            store, cid, "goal_step",
            {"goal_type": goal["goal_type"],
             "priority": goal["priority"]},
            {"goal_id": goal["goal_id"], "deposited_ncr": moved},
            game_minutes)
        out["steps"] += 1


# ---------------------------------------------------------------------
# Structured negotiation (wage at hiring)
# ---------------------------------------------------------------------

def _median(values):
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def negotiate_wage(store, data, vacancy, cid, score, pool_scores,
                   game_minutes):
    """One structured wage negotiation between the best-scoring
    candidate and a business employer. Returns (final_wage,
    negotiation_id) on agreement, (None, negotiation_id) on
    walk-away, and (posted_wage, None) when the candidate has no
    leverage to negotiate with (the plain Session 04 match).

    The candidate's ask premium is derived from measured state:
    their financial need satisfaction (a citizen who can afford to
    wait asks more) and their score margin over the applicant pool,
    scaled by their learned premium factor. The employer's
    acceptance cap is a learned parameter, and any acceptance must
    also pass the Session 04 solvency rule (the wage bill including
    the new hire, times the reserve, must fit the balance). Every
    offer and response is persisted. All rates are the labelled
    SIM MODEL parameters in data/agents-config.json."""
    from . import business as business_mod
    ncfg = cfg(data)["negotiation"]
    posted = vacancy["wage_per_month"]
    business_id = vacancy["employer_business_id"]
    needs = store.row("SELECT financial FROM needs_state WHERE"
                      " character_id = ?", (cid,))
    financial = needs["financial"] if needs else 50
    margin = max(0.0, min(1.0, (score - _median(pool_scores)) / 40.0))
    leverage = 0.5 * (financial / 100.0) + 0.5 * margin
    factor = get_param(store, cid, "wage_premium_factor",
                       ncfg["candidate_factor_default"])
    premium = ncfg["max_premium"] * leverage * factor
    if premium < ncfg["min_premium"] or not business_id:
        return posted, None
    ask = round(posted * (1 + premium))
    cap = get_param(store, business_id, "wage_accept_cap",
                    ncfg["employer_cap_default"])
    reserve = data.economy_config["business"]["wage_reserve_months"]
    bill = business_mod.wage_bill(store, business_id)
    balance = store.business_balance(business_id)
    solvent = balance >= (bill + ask) * reserve
    nid = store.next_id("NG", "negotiations", "negotiation_id")
    store.insert(
        "negotiations", negotiation_id=nid, kind="wage",
        vacancy_id=vacancy["vacancy_id"], party_a_ref=cid,
        party_b_ref=business_id,
        objective=json.dumps({"target_wage": ask,
                              "posted_wage": posted}, sort_keys=True),
        constraints=json.dumps(
            {"employer_cap": cap, "reserve_months": reserve,
             "solvent_for_ask": solvent,
             "candidate_floor_ratio": ncfg["candidate_floor_ratio"]},
            sort_keys=True),
        status="open", rounds=0,
        created_at_game_minutes=game_minutes)
    rounds = 0

    def offer(from_ref, amount, response):
        nonlocal rounds
        rounds += 1
        oid = store.next_id("NO", "negotiation_offers", "offer_id")
        store.insert("negotiation_offers", offer_id=oid,
                     negotiation_id=nid, round=rounds,
                     from_ref=from_ref, amount_ncr=amount,
                     response=response, game_minutes=game_minutes)

    def close(status, final_wage):
        store.execute(
            "UPDATE negotiations SET status = ?, rounds = ?,"
            " final_terms = ?, closed_at_game_minutes = ? WHERE"
            " negotiation_id = ?",
            (status, rounds,
             json.dumps({"wage_per_month": final_wage},
                        sort_keys=True) if final_wage else "{}",
             game_minutes, nid))

    offer(cid, ask, "ask")
    fb = ncfg["candidate_factor_bounds"]
    if premium <= cap and solvent:
        offer(business_id, ask, "accept")
        close("accepted", ask)
        set_param(store, cid, "wage_premium_factor",
                  factor * ncfg["candidate_factor_win"], fb,
                  {"negotiation_id": nid, "outcome": "ask_accepted"},
                  game_minutes)
        log_agent_decision(
            store, business_id, "business", "wage_negotiation",
            {"vacancy_id": vacancy["vacancy_id"], "posted": posted,
             "premium": round(premium, 4), "cap": cap},
            "accept ask when premium <= learned cap and the"
            " solvency reserve holds",
            {"wage_per_month": ask, "negotiation_id": nid},
            game_minutes)
        return ask, nid
    counter = round(posted * (1 + cap))
    offer(business_id, counter, "counter")
    floor = posted * (1 + premium * ncfg["candidate_floor_ratio"])
    if counter >= floor:
        offer(cid, counter, "accept")
        close("accepted", counter)
        set_param(store, cid, "wage_premium_factor",
                  factor * ncfg["candidate_factor_concede"], fb,
                  {"negotiation_id": nid, "outcome": "conceded"},
                  game_minutes)
        log_agent_decision(
            store, business_id, "business", "wage_negotiation",
            {"vacancy_id": vacancy["vacancy_id"], "posted": posted,
             "premium": round(premium, 4), "cap": cap},
            "counter at the learned cap; candidate accepts at or"
            " above their reservation floor",
            {"wage_per_month": counter, "negotiation_id": nid},
            game_minutes)
        return counter, nid
    offer(cid, ask, "walk_away")
    close("walked_away", None)
    set_param(store, cid, "wage_premium_factor",
              factor * ncfg["candidate_factor_walkaway"], fb,
              {"negotiation_id": nid, "outcome": "walked_away"},
              game_minutes)
    set_param(store, business_id, "wage_accept_cap",
              cap + ncfg["employer_cap_walkaway_gain"],
              tuple(ncfg["employer_cap_bounds"]),
              {"negotiation_id": nid, "outcome": "walked_away",
               "vacancy_id": vacancy["vacancy_id"]}, game_minutes)
    log_agent_action(
        store, agent_id("citizen", cid), "negotiate_wage", "failed",
        {"negotiation_id": nid, "vacancy_id": vacancy["vacancy_id"],
         "replan": "candidate remains in next month's applicant"
                   " pool with a reduced premium factor"},
        game_minutes)
    log_agent_decision(
        store, business_id, "business", "wage_negotiation",
        {"vacancy_id": vacancy["vacancy_id"], "posted": posted,
         "premium": round(premium, 4), "cap": cap},
        "counter below the candidate's reservation floor;"
        " candidate walks away, employer cap learns upward",
        {"wage_per_month": None, "negotiation_id": nid,
         "walked_away": True}, game_minutes)
    return None, nid


# ---------------------------------------------------------------------
# Supplier selection by measured reliability
# ---------------------------------------------------------------------

def record_supply_order(store, order, month_index, game_minutes):
    oid = store.next_id("SO", "supply_orders", "order_id")
    store.insert("supply_orders", order_id=oid,
                 month_index=month_index,
                 buyer_business_id=order["buyer"],
                 seller_business_id=order["seller"],
                 good_id=order["good_id"], units=order["units"],
                 amount_ncr=order["amount_ncr"],
                 game_minutes=game_minutes)
    return oid


def supplier_reliability(store, data, seller_id, good_id,
                         month_index):
    """Units of `good_id` the seller actually delivered over the
    trailing window (recorded supply orders only)."""
    scfg = cfg(data)["supplier_selection"]
    since = month_index - scfg["reliability_window_months"] + 1
    row = store.row(
        "SELECT COALESCE(SUM(units), 0) AS u FROM supply_orders"
        " WHERE seller_business_id = ? AND good_id = ? AND"
        " month_index >= ? AND month_index <= ?",
        (seller_id, good_id, since, month_index))
    return row["u"] if row else 0.0


def supplier_reliable(store, data, seller_id, good_id, month_index):
    threshold = cfg(data)["supplier_selection"][
        "reliability_min_units"]
    return supplier_reliability(store, data, seller_id, good_id,
                                month_index) >= threshold


# ---------------------------------------------------------------------
# Forecasts (transparent models, scored against outcomes)
# ---------------------------------------------------------------------

def _month_net_population(store, month_index):
    start = month_index * 30 * 1440
    end = start + 30 * 1440
    births = store.row(
        "SELECT COUNT(*) AS n FROM characters WHERE is_system = 0"
        " AND born_at_game_minutes >= ? AND born_at_game_minutes"
        " < ?", (start, end))["n"]
    deaths = store.row(
        "SELECT COUNT(*) AS n FROM characters WHERE is_system = 0"
        " AND died_at_game_minutes >= ? AND died_at_game_minutes"
        " < ?", (start, end))["n"]
    return births - deaths


def _living_population(store):
    return store.row("SELECT COUNT(*) AS n FROM characters WHERE"
                     " is_system = 0 AND died_at_game_minutes IS"
                     " NULL")["n"]


def _trend(values):
    """Average month-over-month delta of a series (oldest first)."""
    if len(values) < 2:
        return 0.0
    deltas = [values[i + 1] - values[i] for i in range(len(values) - 1)]
    return sum(deltas) / len(deltas)


def _actual_for(store, data, kind, scope):
    from . import distribution as distribution_mod
    if kind == "population":
        return float(_living_population(store))
    if kind == "housing_vacancy":
        return float(distribution_mod.housing_pressure(
            store, data, scope)["vacancy_rate"])
    if kind == "congestion":
        row = store.row("SELECT statistics FROM"
                        " transport_statistics WHERE scope = ?"
                        " ORDER BY month_index DESC LIMIT 1",
                        (scope,))
        if not row:
            return None
        return float(json.loads(row["statistics"]).get(
            "max_congestion_factor", 1.0))
    if kind == "business_profit":
        row = store.row("SELECT COALESCE(SUM(profit_ncr), 0) AS s"
                        " FROM business_monthly WHERE month_index ="
                        " (SELECT MAX(month_index) FROM"
                        " business_monthly)")
        return float(row["s"]) if row else None
    return None


def forecasts_pass(store, data, month_index, game_minutes):
    """Score forecasts whose target month has arrived, then make
    this month's forecasts. Models are transparent linear trends
    over recorded series (labelled SIM MODEL in the config);
    a forecast and its scored outcome are separate fields of one
    record, never conflated."""
    fcfg = cfg(data)["forecasts"]
    horizon = fcfg["horizon_months"]
    window = fcfg["trend_window_months"]
    out = {"scored": 0, "created": 0}
    for f in store.rows("SELECT * FROM forecasts WHERE status ="
                        " 'open' AND target_month <= ? ORDER BY"
                        " forecast_id", (month_index,)):
        actual = _actual_for(store, data, f["kind"], f["scope"])
        if actual is None:
            continue
        predicted = json.loads(f["predicted"])["value"]
        err = abs(predicted - actual)
        score = {"predicted": predicted, "actual": actual,
                 "abs_error": round(err, 4),
                 "pct_error": round(err / max(1.0, abs(actual)), 4)}
        store.execute(
            "UPDATE forecasts SET status = 'scored', actual = ?,"
            " score = ?, scored_at_game_minutes = ? WHERE"
            " forecast_id = ?",
            (json.dumps({"value": actual}), json.dumps(score),
             game_minutes, f["forecast_id"]))
        out["scored"] += 1

    def create(kind, scope, inputs, value):
        fid = store.next_id("FC", "forecasts", "forecast_id")
        store.insert(
            "forecasts", forecast_id=fid, kind=kind, scope=scope,
            made_month=month_index, horizon_months=horizon,
            target_month=month_index + horizon,
            inputs=json.dumps(inputs, sort_keys=True),
            predicted=json.dumps({"value": round(value, 4)}),
            status="open", created_at_game_minutes=game_minutes)
        out["created"] += 1

    kinds = set(fcfg["kinds"])
    if "population" in kinds:
        nets = [_month_net_population(store, m)
                for m in range(max(0, month_index - window),
                               month_index)]
        pop = _living_population(store)
        create("population", "national",
               {"population": pop, "monthly_net_series": nets,
                "model": "population plus the mean recorded"
                         " monthly net change (births - deaths)"
                         " over the trend window"},
               pop + (sum(nets) / len(nets) if nets else 0))
    if "housing_vacancy" in kinds and cities_mod.is_setup(store):
        from . import distribution as distribution_mod
        for spec in data.city_specs():
            cid = spec["city_id"]
            cur = distribution_mod.housing_pressure(
                store, data, cid)["vacancy_rate"]
            past = [json.loads(f["inputs"])["vacancy_rate"]
                    for f in store.rows(
                        "SELECT inputs FROM forecasts WHERE kind ="
                        " 'housing_vacancy' AND scope = ? ORDER BY"
                        " made_month DESC LIMIT ?",
                        (cid, window))]
            series = list(reversed(past)) + [cur]
            create("housing_vacancy", cid,
                   {"vacancy_rate": cur, "series": series,
                    "model": "linear trend of recorded vacancy"
                             " rates"},
                   cur + _trend(series))
    if "congestion" in kinds:
        for spec in data.city_specs():
            cid = spec["city_id"]
            rows = store.rows(
                "SELECT statistics FROM transport_statistics"
                " WHERE scope = ? ORDER BY month_index DESC"
                " LIMIT ?", (cid, window))
            if not rows:
                continue
            series = [json.loads(r["statistics"]).get(
                "max_congestion_factor", 1.0)
                for r in reversed(rows)]
            create("congestion", cid,
                   {"max_congestion_series": series,
                    "model": "linear trend of recorded monthly max"
                             " congestion factors"},
                   series[-1] + _trend(series))
    if "business_profit" in kinds:
        rows = store.rows(
            "SELECT month_index, COALESCE(SUM(profit_ncr), 0) AS s"
            " FROM business_monthly GROUP BY month_index ORDER BY"
            " month_index DESC LIMIT ?", (window,))
        if rows:
            series = [r["s"] for r in reversed(rows)]
            create("business_profit", "national",
                   {"monthly_profit_series": series,
                    "model": "linear trend of recorded business"
                             " monthly profit"},
                   series[-1] + _trend(series))
    return out


# ---------------------------------------------------------------------
# Assessments: the closed problem -> action -> evaluation loop
# ---------------------------------------------------------------------

# problem kind -> (threshold config key, breach test, improves when)
_PROBLEMS = {
    "housing_shortage": ("housing_vacancy_below", "below", "up"),
    "road_condition": ("road_condition_below", "below", "up"),
    "unemployment": ("unemployment_above", "above", "down"),
    "pollution": ("pollution_air_above", "above", "down"),
    "disaster_recovery": (None, "above_zero", "down"),
}

_POLICY_FOR_PROBLEM = {
    "housing_shortage": "housing_development",
    "road_condition": "infrastructure_maintenance",
    "unemployment": "employment_programme",
}


def _problem_value(store, data, scope, kind):
    from . import distribution as distribution_mod
    from . import labour as labour_mod
    if kind == "housing_shortage":
        if not cities_mod.is_setup(store):
            return None
        return float(distribution_mod.housing_pressure(
            store, data, scope)["vacancy_rate"])
    if kind == "road_condition":
        row = store.row("SELECT AVG(condition) AS c FROM"
                        " road_segments WHERE city_id = ?",
                        (scope,))
        return float(row["c"]) if row and row["c"] is not None \
            else None
    if kind == "unemployment":
        stats = labour_mod.unemployment_stats(store, data)
        city = stats["by_city"].get(scope)
        return float(city["unemployment_rate"]) if city else None
    if kind == "pollution":
        row = store.row("SELECT air_index FROM env_pollution WHERE"
                        " city_id = ? ORDER BY month_index DESC"
                        " LIMIT 1", (scope,))
        return float(row["air_index"]) if row else None
    if kind == "disaster_recovery":
        row = store.row(
            "SELECT COALESCE(SUM(damage_estimate_ncr"
            " - relief_paid_ncr - repair_spent_ncr), 0) AS s FROM"
            " disaster_events WHERE city_id = ? AND status !="
            " 'recovered'", (scope,))
        return float(max(0, row["s"])) if row else 0.0
    return None


def _breached(kind, value, threshold):
    test = _PROBLEMS[kind][1]
    if test == "below":
        return value < threshold
    if test == "above":
        return value > threshold
    return value > 0


def _find_action(store, assessment):
    """The funded action an existing engine took for this problem
    after the assessment was raised — a Session 05 policy, a
    Session 03 construction project, a Session 08 law, or this
    layer's own coordination record. Linking, never duplicating:
    the assessment records WHO acted; it does not act itself
    (except coordination, which is this layer's own machinery)."""
    since = assessment["created_at_game_minutes"]
    scope = assessment["scope"]
    kind = assessment["problem_kind"]
    if kind in _POLICY_FOR_PROBLEM:
        p = store.row(
            "SELECT policy_id FROM policies WHERE kind = ? AND"
            " (city_id = ? OR city_id IS NULL) AND"
            " created_at_game_minutes >= ? ORDER BY policy_id"
            " LIMIT 1", (_POLICY_FOR_PROBLEM[kind], scope, since))
        if p:
            return "policy", p["policy_id"]
    if kind == "housing_shortage":
        cp = store.row(
            "SELECT project_id FROM construction_projects WHERE"
            " city_id = ? AND created_at_game_minutes >= ? ORDER"
            " BY project_id LIMIT 1", (scope, since))
        if cp:
            return "construction_project", cp["project_id"]
    if kind == "pollution":
        law = store.row(
            "SELECT law_id FROM laws WHERE kind = 'emission_limit'"
            " AND status = 'enacted' AND enacted_at_game_minutes"
            " >= ? ORDER BY law_id LIMIT 1", (since,))
        if law:
            return "law", law["law_id"]
    if kind == "disaster_recovery":
        t = store.row(
            "SELECT ct.task_id, ct.disaster_id FROM"
            " coordination_tasks ct JOIN disaster_events de ON"
            " de.disaster_id = ct.disaster_id WHERE de.city_id = ?"
            " AND ct.created_at_game_minutes >= ? ORDER BY"
            " ct.task_id LIMIT 1", (scope, since))
        if t:
            return "coordination", t["disaster_id"]
    return None


def assessments_pass(store, data, month_index, game_minutes):
    """Monthly assessment cycle per city: identify problems from
    measured indicators, link the action taken, then evaluate the
    same indicator in a later month. The city agent's 'assess'
    capability gates the cycle (registry permissions)."""
    acfg = cfg(data)["assessments"]
    out = {"identified": 0, "acted": 0, "evaluated": 0}
    if not cities_mod.is_setup(store):
        return out
    country = store.row("SELECT country_id FROM countries LIMIT 1")
    gov_ref = agent_id("government",
                       country["country_id"]) if country else None
    for spec in data.city_specs():
        scope = spec["city_id"]
        city_agent = agent_id("city", scope)
        for kind, (tkey, _test, improve) in _PROBLEMS.items():
            value = _problem_value(store, data, scope, kind)
            if value is None:
                continue
            threshold = acfg[tkey] if tkey else 0
            open_a = store.row(
                "SELECT * FROM assessments WHERE scope = ? AND"
                " problem_kind = ? AND status IN ('identified',"
                " 'acted') ORDER BY assessment_id DESC LIMIT 1",
                (scope, kind))
            if open_a is None:
                if not _breached(kind, value, threshold):
                    continue
                require_capability(store, data, "city", scope,
                                   "assess", "assessment",
                                   game_minutes)
                aid = store.next_id("AS", "assessments",
                                    "assessment_id")
                store.insert(
                    "assessments", assessment_id=aid, scope=scope,
                    problem_kind=kind, month_index=month_index,
                    indicator=json.dumps(
                        {"value": value, "threshold": threshold},
                        sort_keys=True),
                    baseline=value, current_value=value,
                    status="identified",
                    created_at_game_minutes=game_minutes,
                    updated_at_game_minutes=game_minutes)
                log_agent_decision(
                    store, city_agent, "city", "assessment",
                    {"problem_kind": kind, "value": value,
                     "threshold": threshold},
                    "measured indicator beyond the configured"
                    " threshold raises an assessment",
                    {"assessment_id": aid, "status": "identified"},
                    game_minutes)
                if kind == "pollution" and gov_ref:
                    send_message(
                        store, city_agent, gov_ref, "recommendation",
                        {"assessment_id": aid, "problem_kind": kind,
                         "suggestion": "enact an emission_limit law"
                                       " (Session 05 law machinery)",
                         "air_index": value}, game_minutes)
                out["identified"] += 1
                continue
            # An open assessment: refresh the indicator, link any
            # action, then evaluate in a later month.
            store.execute(
                "UPDATE assessments SET current_value = ?,"
                " updated_at_game_minutes = ? WHERE assessment_id"
                " = ?", (value, game_minutes,
                         open_a["assessment_id"]))
            if open_a["status"] == "identified":
                found = _find_action(store, open_a)
                if found:
                    store.execute(
                        "UPDATE assessments SET status = 'acted',"
                        " action_kind = ?, action_ref = ?,"
                        " updated_at_game_minutes = ? WHERE"
                        " assessment_id = ?",
                        (found[0], found[1], game_minutes,
                         open_a["assessment_id"]))
                    out["acted"] += 1
            elif open_a["status"] == "acted" \
                    and open_a["month_index"] < month_index:
                baseline = open_a["baseline"]
                eps = 0.5 if kind == "disaster_recovery" else 0.001
                improved = (value > baseline + eps) \
                    if improve == "up" else (value < baseline - eps)
                evaluation = {"baseline": baseline, "current": value,
                              "improved": bool(improved),
                              "action_kind": open_a["action_kind"],
                              "action_ref": open_a["action_ref"]}
                store.execute(
                    "UPDATE assessments SET status = 'evaluated',"
                    " evaluation = ?, updated_at_game_minutes = ?"
                    " WHERE assessment_id = ?",
                    (json.dumps(evaluation, sort_keys=True),
                     game_minutes, open_a["assessment_id"]))
                log_agent_decision(
                    store, city_agent, "city", "assessment_evaluation",
                    {"assessment_id": open_a["assessment_id"],
                     "problem_kind": kind},
                    "the same indicator that raised the assessment"
                    " is re-measured one month after the action",
                    evaluation, game_minutes)
                out["evaluated"] += 1
    return out


def request_policy_action(store, data, agent_class, ref_id, kind,
                          game_minutes):
    """Authorise a policy action inside the coordination layer.
    Only government-class agents hold the 'enact_policy'
    capability; anyone else's attempt is a recorded failed action
    and raises PermissionError. The authorisation is routed to the
    government agent as a message — enactment itself remains
    Session 05's machinery (policies.py), by design."""
    aid = require_capability(store, data, agent_class, ref_id,
                             "enact_policy", "policy_action",
                             game_minutes)
    country = store.row("SELECT country_id FROM countries LIMIT 1")
    gov_ref = agent_id("government",
                       country["country_id"]) if country else aid
    send_message(store, aid, gov_ref, "policy_action_request",
                 {"kind": kind}, game_minutes)
    return aid


# ---------------------------------------------------------------------
# Emergency coordination over Session 08 disaster response
# ---------------------------------------------------------------------

def _task_done_evidence(store, disaster_id, kind):
    """The Session 08 response record that proves a coordination
    task is done, and when. Coordination tracks the response; it
    does not perform it (Session 08 spends the real resources)."""
    actions = {"evacuate": "evacuation_trip",
               "shelter": "shelter_assignment",
               "relief": "relief_payment",
               "medical": "medical_flag",
               "repair": "repair_payment"}
    if kind == "assess":
        row = store.row("SELECT MAX(game_minutes) AS m FROM"
                        " disaster_impacts WHERE disaster_id = ?",
                        (disaster_id,))
        return row["m"] if row and row["m"] is not None else None
    action = actions.get(kind)
    if action is None:
        return None
    row = store.row("SELECT MAX(game_minutes) AS m FROM"
                    " disaster_responses WHERE disaster_id = ? AND"
                    " action = ?", (disaster_id, action))
    return row["m"] if row and row["m"] is not None else None


def coordination_pass(store, data, game_minutes):
    """Maintain the coordination task sequence for every disaster:
    assess -> evacuate -> shelter -> relief -> medical -> repair,
    plus a review task when anything closes unmet. Overdue tasks
    escalate to the government agent by message (attempts are
    recorded); tasks still unmet when the disaster recovers close
    as 'closed_unmet' — failure recorded, then reviewed, never
    silently dropped."""
    ccfg = cfg(data)["coordination"]
    out = {"created": 0, "done": 0, "escalated": 0,
           "closed_unmet": 0, "reviews": 0}
    country = store.row("SELECT country_id FROM countries LIMIT 1")
    gov_agent = agent_id("government",
                         country["country_id"]) if country else None
    disasters = store.rows("SELECT * FROM disaster_events ORDER BY"
                           " disaster_id")
    for d in disasters:
        did = d["disaster_id"]
        city_agent = agent_id("city", d["city_id"])
        displaced = store.row(
            "SELECT COUNT(*) AS n FROM disaster_impacts WHERE"
            " disaster_id = ? AND kind LIKE '%displaced%'",
            (did,))["n"]
        damaged = store.row(
            "SELECT COUNT(*) AS n FROM disaster_impacts WHERE"
            " disaster_id = ? AND kind LIKE '%damage%'",
            (did,))["n"]
        injured = store.row(
            "SELECT COUNT(*) AS n FROM disaster_impacts WHERE"
            " disaster_id = ? AND (kind LIKE '%injur%' OR kind"
            " LIKE '%medical%' OR kind LIKE '%health%')",
            (did,))["n"]
        applicable = ["assess"]
        if displaced:
            applicable += ["evacuate", "shelter", "relief"]
        if damaged or d["damage_estimate_ncr"]:
            applicable += ["repair"]
            if "relief" not in applicable:
                applicable.append("relief")
        if injured:
            applicable.append("medical")
        unmet = []
        for kind in applicable:
            assigned = gov_agent if kind in ("relief", "repair") \
                else city_agent
            task = store.row("SELECT * FROM coordination_tasks"
                             " WHERE disaster_id = ? AND kind = ?",
                             (did, kind))
            if task is None:
                tid = store.next_id("CT", "coordination_tasks",
                                    "task_id")
                store.insert(
                    "coordination_tasks", task_id=tid,
                    disaster_id=did, kind=kind,
                    assigned_ref=assigned, status="pending",
                    attempts=0,
                    details=json.dumps(
                        {"disaster_type": d["disaster_type"],
                         "city_id": d["city_id"]}, sort_keys=True),
                    created_at_game_minutes=game_minutes,
                    updated_at_game_minutes=game_minutes)
                out["created"] += 1
                task = store.row("SELECT * FROM coordination_tasks"
                                 " WHERE task_id = ?", (tid,))
            if task["status"] in ("done", "closed_unmet"):
                if task["status"] == "closed_unmet":
                    unmet.append(kind)
                continue
            done_at = _task_done_evidence(store, did, kind)
            if done_at is not None:
                store.execute(
                    "UPDATE coordination_tasks SET status = 'done',"
                    " completed_at_game_minutes = ?,"
                    " updated_at_game_minutes = ? WHERE task_id = ?",
                    (done_at, game_minutes, task["task_id"]))
                out["done"] += 1
                continue
            if d["status"] == "recovered":
                store.execute(
                    "UPDATE coordination_tasks SET status ="
                    " 'closed_unmet', updated_at_game_minutes = ?"
                    " WHERE task_id = ?",
                    (game_minutes, task["task_id"]))
                log_agent_action(
                    store, assigned or city_agent,
                    f"coordination_{kind}", "failed",
                    {"disaster_id": did, "task_id": task["task_id"],
                     "reason": "disaster recovered before the"
                               " response record existed",
                     "replan": "review task records the gap for"
                               " the next preparedness cycle"},
                    game_minutes)
                out["closed_unmet"] += 1
                unmet.append(kind)
                continue
            details = json.loads(task["details"] or "{}")
            age_days = (game_minutes
                        - task["created_at_game_minutes"]) / 1440
            if age_days > ccfg["overdue_days"] \
                    and not details.get("escalated"):
                details["escalated"] = True
                store.execute(
                    "UPDATE coordination_tasks SET attempts ="
                    " attempts + 1, details = ?,"
                    " updated_at_game_minutes = ? WHERE task_id = ?",
                    (json.dumps(details, sort_keys=True),
                     game_minutes, task["task_id"]))
                if gov_agent:
                    send_message(
                        store, city_agent, gov_agent, "escalation",
                        {"task_id": task["task_id"],
                         "disaster_id": did, "kind": kind,
                         "age_days": round(age_days, 1)},
                        game_minutes)
                out["escalated"] += 1
        if d["status"] == "recovered" and unmet:
            existing = store.row(
                "SELECT * FROM coordination_tasks WHERE disaster_id"
                " = ? AND kind = 'review'", (did,))
            if existing is None:
                tid = store.next_id("CT", "coordination_tasks",
                                    "task_id")
                store.insert(
                    "coordination_tasks", task_id=tid,
                    disaster_id=did, kind="review",
                    assigned_ref=gov_agent, status="done",
                    attempts=0,
                    details=json.dumps(
                        {"unmet_tasks": unmet,
                         "review": "gaps recorded for the next"
                                   " preparedness cycle"},
                        sort_keys=True),
                    created_at_game_minutes=game_minutes,
                    updated_at_game_minutes=game_minutes,
                    completed_at_game_minutes=game_minutes)
                out["reviews"] += 1
    return out


# ---------------------------------------------------------------------
# Passes + summary
# ---------------------------------------------------------------------

def daily_pass(store, data, rng, day_index, game_minutes):
    """Daily cadence: coordination only, and only when a disaster
    is live or has just recovered (two cheap existence checks)."""
    if not is_setup(store):
        return None
    live = store.row("SELECT 1 FROM disaster_events WHERE status"
                     " IN ('active', 'responding') LIMIT 1")
    recent = store.row(
        "SELECT 1 FROM disaster_events WHERE status = 'recovered'"
        " AND recovered_at_game_minutes >= ? LIMIT 1",
        (game_minutes - 3 * 1440,))
    if not live and not recent:
        return None
    return coordination_pass(store, data, game_minutes)


def monthly_pass(store, data, rng, month_index, game_minutes):
    """The monthly coordination cycle, last in the month: registry
    sync, memory, goals, forecasts, coordination, assessments —
    each reads the settled month, in dependency order."""
    if not is_setup(store):
        return None
    out = {}
    out["registry"] = sync_registry(store, data, game_minutes)
    out["memory"] = memory_pass(store, data, month_index,
                                game_minutes)
    out["goals"] = goals_pass(store, data, rng, month_index,
                              game_minutes)
    out["forecasts"] = forecasts_pass(store, data, month_index,
                                      game_minutes)
    out["coordination"] = coordination_pass(store, data,
                                            game_minutes)
    out["assessments"] = assessments_pass(store, data, month_index,
                                          game_minutes)
    return out


def agents_summary(store):
    if not is_setup(store):
        return {"agents_setup": False}
    scored = store.rows("SELECT score FROM forecasts WHERE status"
                        " = 'scored'")
    errors = [json.loads(s["score"])["pct_error"] for s in scored
              if s["score"]]
    return {
        "agents_setup": True,
        "registry": {f"{r['agent_class']}/{r['status']}": r["n"]
                     for r in store.rows(
                         "SELECT agent_class, status, COUNT(*) AS n"
                         " FROM agent_registry GROUP BY agent_class,"
                         " status")},
        "active_goals": {r["goal_type"]: r["n"] for r in store.rows(
            "SELECT goal_type, COUNT(*) AS n FROM character_goals"
            " WHERE status = 'active' GROUP BY goal_type")},
        "goals_by_status": {r["status"]: r["n"] for r in store.rows(
            "SELECT status, COUNT(*) AS n FROM character_goals"
            " GROUP BY status")},
        "negotiations": {r["status"]: r["n"] for r in store.rows(
            "SELECT status, COUNT(*) AS n FROM negotiations GROUP"
            " BY status")},
        "supply_orders": store.row(
            "SELECT COUNT(*) AS n FROM supply_orders")["n"],
        "forecasts": {r["status"]: r["n"] for r in store.rows(
            "SELECT status, COUNT(*) AS n FROM forecasts GROUP BY"
            " status")},
        "forecast_mean_pct_error": round(
            sum(errors) / len(errors), 4) if errors else None,
        "assessments": {r["status"]: r["n"] for r in store.rows(
            "SELECT status, COUNT(*) AS n FROM assessments GROUP"
            " BY status")},
        "coordination_tasks": {r["status"]: r["n"]
                               for r in store.rows(
                                   "SELECT status, COUNT(*) AS n"
                                   " FROM coordination_tasks GROUP"
                                   " BY status")},
        "memories_by_level": {r["level"]: r["n"]
                              for r in store.rows(
                                  "SELECT level, COUNT(*) AS n FROM"
                                  " agent_memories GROUP BY level")},
        "learning_records": store.row(
            "SELECT COUNT(*) AS n FROM agent_learning")["n"],
        "agent_decisions": store.row(
            "SELECT COUNT(*) AS n FROM agent_decisions")["n"],
    }
