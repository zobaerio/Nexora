"""Session 02 Unit 05 — Community Engine.

A community is a District 1 zone made social: the people whose
households sit in it, the facilities the buildings data puts there,
a leader the community's own respect graph points to, and issues
derived from the zone's simulated facts (indebted households,
crowding, low participation) — never invented flavour text.

Membership is *derived state kept in sync*: community_members rows
follow household residence, so when a family relocates (Unit 02) or
a young adult leaves home, the community changes through the same
life event. Updates are a weekly batch — one pass over households
and members, aggregate queries for statistics — never a per-tick
scan of every relationship in the zone.
"""
import json

from . import family_economy
from .identity import age_years

PARTICIPATION_EVENTS = ("neighbour_meeting", "social_event",
                        "community_meeting", "festival_celebration")


def zone_name(zone_id):
    return zone_id.replace("d1_", "").replace("_", " ").title()


def ensure_communities(store, data, game_minutes):
    """Create one community per zone in the canonical buildings
    data and sync membership to current residence. Idempotent."""
    for zone in data.zones:
        store.execute(
            "INSERT OR IGNORE INTO communities (community_id, name,"
            " updated_at_game_minutes) VALUES (?, ?, ?)",
            (zone, zone_name(zone), game_minutes))
    residents = {}
    for h in store.rows("SELECT household_id, district_id FROM"
                        " households WHERE dissolved_at_game_minutes"
                        " IS NULL"):
        for m in store.rows(
                "SELECT character_id FROM household_members"
                " WHERE household_id = ? AND left_at_game_minutes"
                " IS NULL", (h["household_id"],)):
            residents[m["character_id"]] = h["district_id"]
    alive = {r["character_id"] for r in store.rows(
        "SELECT character_id FROM characters WHERE is_system = 0"
        " AND died_at_game_minutes IS NULL")}
    current = {(r["community_id"], r["character_id"]) for r in
               store.rows("SELECT community_id, character_id FROM"
                          " community_members WHERE"
                          " left_at_game_minutes IS NULL")}
    for cid, zone in sorted(residents.items()):
        if cid in alive and (zone, cid) not in current:
            store.execute(
                "INSERT OR REPLACE INTO community_members"
                " (community_id, character_id, joined_at_game_minutes,"
                " left_at_game_minutes) VALUES (?, ?, ?, NULL)",
                (zone, cid, game_minutes))
    for zone, cid in sorted(current):
        if residents.get(cid) != zone:
            store.execute(
                "UPDATE community_members SET left_at_game_minutes = ?"
                " WHERE community_id = ? AND character_id = ?"
                " AND left_at_game_minutes IS NULL",
                (game_minutes, zone, cid))
    return sorted(data.zones)


def facilities(store, data, zone_id):
    """The zone's real facilities, from the buildings data."""
    return [{"id": b["id"], "name": b["name"],
             "type": b["property_type"]}
            for b in data.buildings if b["zone_id"] == zone_id
            and "part_of" not in b]


def _active_members(store, zone_id):
    return store.rows(
        "SELECT c.* FROM community_members cm JOIN characters c"
        " ON c.character_id = cm.character_id WHERE cm.community_id = ?"
        " AND cm.left_at_game_minutes IS NULL"
        " AND c.died_at_game_minutes IS NULL ORDER BY c.character_id",
        (zone_id,))


def _participation(store, zone_id, member_ids, game_minutes):
    """Fraction of adult members with a recorded social act in the
    last 30 days: a participation life event, or a seat at a social
    event held in this zone."""
    if not member_ids:
        return 0.0
    since = game_minutes - 30 * 1440
    active = set()
    marks = ",".join("?" for _ in PARTICIPATION_EVENTS)
    for r in store.rows(
            f"SELECT DISTINCT character_id FROM life_events WHERE"
            f" event_type IN ({marks}) AND game_minutes >= ?",
            PARTICIPATION_EVENTS + (since,)):
        if r["character_id"] in member_ids:
            active.add(r["character_id"])
    for r in store.rows("SELECT participant_ids FROM social_events"
                        " WHERE zone_id = ? AND game_minutes >= ?",
                        (zone_id, since)):
        for cid in json.loads(r["participant_ids"]):
            if cid in member_ids:
                active.add(cid)
    adults = {cid for cid in member_ids}
    return round(len(active & adults) / max(1, len(adults)), 3)


def _pick_leader(store, members, game_minutes):
    """The community's leader: the employed adult its members most
    respect (respect received across all their edges), ties broken
    by seniority of residence, then id — a deterministic read of the
    social graph, not an appointment."""
    best, best_key = None, None
    for m in members:
        if age_years(m["born_at_game_minutes"], game_minutes) < 30:
            continue
        employed = store.row("SELECT 1 FROM employments"
                             " WHERE character_id = ?"
                             " AND ended_at_game_minutes IS NULL",
                             (m["character_id"],)) is not None
        respect = store.row(
            "SELECT COALESCE(SUM(respect),0) AS s FROM relationships"
            " WHERE to_character_id = ?", (m["character_id"],))["s"]
        joined = store.row("SELECT joined_at_game_minutes FROM"
                           " community_members WHERE character_id = ?"
                           " AND left_at_game_minutes IS NULL",
                           (m["character_id"],))
        key = (1 if employed else 0, respect,
               -(joined["joined_at_game_minutes"] if joined else 0))
        if best_key is None or key > best_key \
                or (key == best_key and m["character_id"] < best):
            best, best_key = m["character_id"], key
    return best


def _issues(store, zone_id, members, participation):
    issues = []
    households = {m["household_id"] for m in members if m["household_id"]}
    indebted = sum(1 for hid in households
                   if family_economy.debt_of(store, hid) > 0)
    if indebted >= 2:
        issues.append({"kind": "financial_hardship",
                       "indebted_households": indebted})
    if households and len(members) / len(households) > 4.5:
        issues.append({"kind": "housing_pressure",
                       "avg_household_size":
                       round(len(members) / len(households), 2)})
    if len(members) >= 10 and participation < 0.1:
        issues.append({"kind": "low_participation",
                       "participation_rate": participation})
    return issues


def weekly_update(store, data, rng, game_minutes):
    """The weekly batch: sync membership, recompute population,
    participation, leadership and issues for every community."""
    ensure_communities(store, data, game_minutes)
    summary = {}
    for zone in sorted(data.zones):
        members = _active_members(store, zone)
        member_ids = {m["character_id"] for m in members}
        participation = _participation(store, zone, member_ids,
                                       game_minutes)
        leader = _pick_leader(store, members, game_minutes)
        issues = _issues(store, zone, members, participation)
        store.execute(
            "UPDATE communities SET population = ?,"
            " participation_rate = ?, leader_character_id = ?,"
            " issues = ?, updated_at_game_minutes = ?"
            " WHERE community_id = ?",
            (len(members), participation, leader, json.dumps(issues),
             game_minutes, zone))
        summary[zone] = {"population": len(members),
                         "participation_rate": participation,
                         "leader": leader, "issues": issues}
    return summary


def community_view(store, data, zone_id):
    """The observation view: a community as its simulated facts."""
    row = store.row("SELECT * FROM communities WHERE community_id = ?",
                    (zone_id,))
    if row is None:
        return None
    leader = None
    if row["leader_character_id"]:
        c = store.row("SELECT display_name FROM characters"
                      " WHERE character_id = ?",
                      (row["leader_character_id"],))
        leader = {"character_id": row["leader_character_id"],
                  "name": c["display_name"] if c else None}
    return {"community_id": zone_id, "name": row["name"],
            "population": row["population"],
            "participation_rate": row["participation_rate"],
            "leader": leader, "issues": json.loads(row["issues"]),
            "facilities": facilities(store, data, zone_id)}
