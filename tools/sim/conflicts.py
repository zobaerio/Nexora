"""Session 02 Unit 10 — Social Conflict & Resolution.

Conflicts here are *diagnosed, not generated*: a conflict record
opens only when the pair's measured conflict level (social_profiles,
built by Unit 04 from actual hostile encounters) crosses a
threshold, and its cause is read from the pair's circumstances —
household debt on either side makes it a resource dispute, deeply
negative affection makes it relationship strain, otherwise it is a
misunderstanding. Nothing rolls dice to manufacture drama, and a
pair that has just resolved (or escalated) cannot re-enter conflict
for 30 days.

Resolution is work, done by someone: the community leader of the
pair's zone mediates if there is one; failing that, a mutual friend
with real empathy, or an elder of either family. Success odds come
from the mediator's empathy and the parties' patience — the same
personality attributes that caused the trouble. Outcomes are
written everywhere the trouble was: conflict levels halve, trust
and affection recover on the pair's strongest edge, memories and
life events record the resolution, and relationship_history gains
the status change (Unit 01's history is where statuses live).
Unresolved after repeated attempts, a conflict escalates and
closes as a standing grievance — the rivalry machinery (Unit 04)
already knows what to do with those.
"""
from . import emotions as emotions_mod
from . import family_economy
from . import memory as memory_mod
from . import personality as personality_mod
from . import relationships as rel
from . import social as social_mod

OPEN_THRESHOLD = 40
COOLDOWN_DAYS = 30
MAX_ATTEMPTS = 3


def _pair_profiles(store, a, b):
    out = []
    for x, y in ((a, b), (b, a)):
        for e in store.rows("SELECT relationship_id FROM relationships"
                            " WHERE from_character_id = ?"
                            " AND to_character_id = ?", (x, y)):
            prof = social_mod.profile_of(store, e["relationship_id"])
            if prof:
                out.append(prof)
    return out


def pair_conflict_level(store, a, b):
    profs = _pair_profiles(store, a, b)
    return max((p["conflict"] for p in profs), default=0)


def _cause(store, a, b):
    for cid in (a, b):
        char = store.row("SELECT household_id FROM characters"
                         " WHERE character_id = ?", (cid,))
        if char and char["household_id"] \
                and family_economy.debt_of(store,
                                            char["household_id"]) > 0:
            return "resource_dispute"
    worst = 0
    for x, y in ((a, b), (b, a)):
        for e in store.rows("SELECT affection FROM relationships"
                            " WHERE from_character_id = ?"
                            " AND to_character_id = ?", (x, y)):
            worst = min(worst, e["affection"])
    if worst <= -20:
        return "relationship_strain"
    return "misunderstanding"


def _open_conflict_for(store, a, b):
    return store.row("SELECT * FROM conflict_records WHERE"
                     " ((a_character_id = ? AND b_character_id = ?)"
                     " OR (a_character_id = ? AND b_character_id = ?))"
                     " AND status = 'open'", (a, b, b, a))


def _in_cooldown(store, a, b, game_minutes):
    row = store.row("SELECT MAX(closed_at_game_minutes) AS m FROM"
                    " conflict_records WHERE"
                    " ((a_character_id = ? AND b_character_id = ?)"
                    " OR (a_character_id = ? AND b_character_id = ?))"
                    " AND closed_at_game_minutes IS NOT NULL",
                    (a, b, b, a))
    return row and row["m"] is not None \
        and game_minutes - row["m"] < COOLDOWN_DAYS * 1440


def detect_conflicts(store, game_minutes):
    """Open conflict records for every pair whose measured conflict
    level crossed the threshold. Returns the new record ids."""
    hot = store.rows("SELECT relationship_id FROM social_profiles"
                     " WHERE conflict >= ?", (OPEN_THRESHOLD,))
    pairs = set()
    for h in hot:
        edge = store.row("SELECT from_character_id, to_character_id"
                         " FROM relationships WHERE relationship_id = ?",
                         (h["relationship_id"],))
        if edge:
            pairs.add(tuple(sorted((edge["from_character_id"],
                                    edge["to_character_id"]))))
    created = []
    for a, b in sorted(pairs):
        if a == b or _open_conflict_for(store, a, b) \
                or _in_cooldown(store, a, b, game_minutes):
            continue
        cause = _cause(store, a, b)
        cid_ = store.next_id("CF", "conflict_records", "conflict_id")
        store.insert("conflict_records", conflict_id=cid_,
                     a_character_id=a, b_character_id=b, cause=cause,
                     status="open", opened_at_game_minutes=game_minutes)
        for x, y in ((a, b), (b, a)):
            memory_mod.log_life_event(store, x, "conflict_opened",
                                      game_minutes, other_character_id=y,
                                      details={"cause": cause})
            rel.record_history(store, x, y, "conflict", "opened",
                               game_minutes, details={"cause": cause})
        created.append(cid_)
    return created


def _find_mediator(store, a, b):
    """Leader of a's community first; then a mutual friend with
    empathy; then an elder relative of either party."""
    char = store.row("SELECT household_id FROM characters"
                     " WHERE character_id = ?", (a,))
    if char and char["household_id"]:
        h = store.row("SELECT district_id FROM households"
                      " WHERE household_id = ?", (char["household_id"],))
        if h:
            comm = store.row("SELECT leader_character_id FROM"
                             " communities WHERE community_id = ?",
                             (h["district_id"],))
            leader = comm["leader_character_id"] if comm else None
            if leader and leader not in (a, b):
                return leader
    mutual = set(rel.friends_of(store, a)) & set(rel.friends_of(store, b))
    for cand in sorted(mutual):
        prof = personality_mod.get_profile(store, cand)
        if prof and prof["empathy"] >= 55:
            return cand
    from . import kinship
    for cid in (a, b):
        for gp in kinship.grandparents(store, cid):
            row = store.row("SELECT died_at_game_minutes FROM characters"
                            " WHERE character_id = ?", (gp,))
            if row and row["died_at_game_minutes"] is None:
                return gp
    return None


def _strongest_type(store, a, b):
    for t in ("spouse", "parent", "child", "sibling", "friend",
              "neighbour", "colleague", "acquaintance", "rival"):
        if rel.get_edge(store, a, b, t):
            return t
    return None


def attempt_resolution(store, rng, conflict, game_minutes):
    """One mediation/negotiation attempt. Returns the new status:
    'resolved', 'escalated', or 'open' (still trying)."""
    a, b = conflict["a_character_id"], conflict["b_character_id"]
    mediator = _find_mediator(store, a, b)
    pa = personality_mod.get_profile(store, a)
    pb = personality_mod.get_profile(store, b)
    patience = ((pa["patience"] if pa else 50)
                + (pb["patience"] if pb else 50)) / 2
    empathy = 50
    if mediator:
        pm = personality_mod.get_profile(store, mediator)
        empathy = pm["empathy"] if pm else 50
    roll = rng.stream("mediation", conflict["conflict_id"],
                      game_minutes // (7 * 1440)).random()
    p_success = 0.3 + empathy / 250 + patience / 300
    attempts = store.row(
        "SELECT COUNT(*) AS n FROM life_events WHERE event_type ="
        " 'mediation_attempt' AND other_character_id = ?"
        " AND character_id = ?", (b, a))["n"]
    if roll < p_success:
        for prof in _pair_profiles(store, a, b):
            store.execute("UPDATE social_profiles SET conflict ="
                          " conflict / 2 WHERE relationship_id = ?",
                          (prof["relationship_id"],))
        etype = _strongest_type(store, a, b)
        if etype:
            rel.adjust_scores(store, a, b, game_minutes, trust=5,
                              affection=4, relation_type=etype)
        store.execute("UPDATE conflict_records SET status = 'resolved',"
                      " mediator_character_id = ?, resolution = ?,"
                      " closed_at_game_minutes = ? WHERE conflict_id = ?",
                      (mediator, "mediated" if mediator else "negotiated",
                       game_minutes, conflict["conflict_id"]))
        for x, y in ((a, b), (b, a)):
            memory_mod.log_life_event(store, x, "conflict_resolved",
                                      game_minutes, other_character_id=y)
            memory_mod.record_memory(store, x, "conflict_resolved", 20,
                                     game_minutes, other_character_id=y)
            rel.record_history(store, x, y, "conflict", "resolved",
                               game_minutes,
                               details={"mediator": mediator})
        return "resolved"
    memory_mod.log_life_event(store, a, "mediation_attempt", game_minutes,
                              other_character_id=b,
                              details={"attempt": attempts + 1})
    if attempts + 1 >= MAX_ATTEMPTS:
        for prof in _pair_profiles(store, a, b):
            store.execute("UPDATE social_profiles SET conflict ="
                          " MIN(100, conflict + 10)"
                          " WHERE relationship_id = ?",
                          (prof["relationship_id"],))
        store.execute("UPDATE conflict_records SET status = 'escalated',"
                      " mediator_character_id = ?,"
                      " closed_at_game_minutes = ? WHERE conflict_id = ?",
                      (mediator, game_minutes, conflict["conflict_id"]))
        for x, y in ((a, b), (b, a)):
            emotions_mod.apply_event(store, x, "conflict")
            memory_mod.log_life_event(store, x, "conflict_escalated",
                                      game_minutes, other_character_id=y)
            rel.record_history(store, x, y, "conflict", "escalated",
                               game_minutes)
        return "escalated"
    return "open"


def weekly_scan(store, rng, data, game_minutes):
    """The weekly batch: detect new conflicts from measured levels,
    then attempt resolution of open ones at least 3 days old."""
    created = detect_conflicts(store, game_minutes)
    resolved = escalated = 0
    for conflict in store.rows("SELECT * FROM conflict_records"
                               " WHERE status = 'open'"
                               " ORDER BY conflict_id"):
        if game_minutes - conflict["opened_at_game_minutes"] < 3 * 1440:
            continue
        outcome = attempt_resolution(store, rng, conflict, game_minutes)
        if outcome == "resolved":
            resolved += 1
        elif outcome == "escalated":
            escalated += 1
    return {"opened": len(created), "resolved": resolved,
            "escalated": escalated}
