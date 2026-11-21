"""Session 02 Unit 09 — Social Events Engine.

Events here are not decorations: each one is a row in social_events
with real participants (living characters, chosen deterministically
from the relationships that motivate the event), a real location
(the zone/building the participants actually live in), a schedule
(the game minute it happens) and consequences written back into
memories, emotions and relationship scores.

Sources of events, all from simulated facts:
- wedding celebrations follow actual marriages (life_events);
- birth celebrations follow actual childbirths;
- festivals follow the culture calendar (Unit 07's data — a
  festival happens on its day-of-year, for the households whose
  culture profile celebrates it);
- public meetings are monthly per community, chaired by its
  leader, discussing its currently-derived top issue (Unit 05);
- family gatherings bring extended kin (Unit 01) into one
  household, and honour the elder-respect tradition where the
  household's culture carries it.
"""
import json

from . import culture as culture_mod
from . import emotions as emotions_mod
from . import kinship
from . import memory as memory_mod
from . import relationships as rel
from . import social as social_mod

MAX_GUESTS = 14


def create_event(store, event_type, zone_id, location_label,
                 participants, outcome, game_minutes):
    eid = store.next_id("SE", "social_events", "event_id")
    store.insert("social_events", event_id=eid, event_type=event_type,
                 zone_id=zone_id, location_label=location_label,
                 participant_ids=json.dumps(sorted(participants)),
                 outcome=json.dumps(outcome), game_minutes=game_minutes)
    return eid


def _celebrated_sources(store):
    """Source pairs already celebrated, from the social event rows'
    outcomes — celebrations happen once per life event. Marriage
    and childbirth each log one life-event row *per partner*, so
    the unit of celebration is the pair, not the row."""
    done = set()
    for r in store.rows("SELECT outcome FROM social_events"
                        " WHERE event_type IN ('wedding_celebration',"
                        " 'birth_celebration')"):
        pair = json.loads(r["outcome"]).get("source_pair")
        if pair:
            done.add(tuple(pair))
    return done


def _zone_of(store, character_id):
    char = store.row("SELECT household_id FROM characters"
                     " WHERE character_id = ?", (character_id,))
    if not char or not char["household_id"]:
        return None
    h = store.row("SELECT district_id FROM households"
                  " WHERE household_id = ?", (char["household_id"],))
    return h["district_id"] if h else None


def _mark_participants(store, participants, event_type, weight,
                       game_minutes, emotion=None):
    for cid in participants:
        memory_mod.log_life_event(store, cid, "social_event",
                                  game_minutes,
                                  details={"kind": event_type})
        memory_mod.record_memory(store, cid, event_type, weight,
                                 game_minutes)
        if emotion:
            emotions_mod.apply_event(store, cid, emotion)


def celebrate_life_events(store, data, rng, game_minutes,
                          window_days=30):
    """Weddings and births from the recent life-event log get their
    celebrations, once each. Returns the events created."""
    since = game_minutes - window_days * 1440
    done = _celebrated_sources(store)
    created = []
    rows = store.rows(
        "SELECT * FROM life_events WHERE event_type IN ('marriage',"
        " 'childbirth') AND game_minutes >= ? ORDER BY game_minutes",
        (since,))
    seen_pairs = set()
    for ev in rows:
        host = ev["character_id"]
        other = ev["other_character_id"]
        pair = tuple(sorted(x for x in (host, other) if x))
        if pair in seen_pairs or pair in done:
            continue  # marriage logs one row per partner
        seen_pairs.add(pair)
        if ev["event_type"] == "marriage":
            guests = set(rel.family_of(store, host))
            if other:
                guests |= set(rel.family_of(store, other))
            etype, weight = "wedding_celebration", 45
        else:
            guests = set(rel.family_of(store, host))
            etype, weight = "birth_celebration", 40
        guests.discard(host)
        if other:
            guests.discard(other)
        participants = sorted(x for x in [host, other] if x) \
            + sorted(guests)[:MAX_GUESTS]
        zone = _zone_of(store, host)
        eid = create_event(store, etype, zone,
                           f"{etype.replace('_', ' ')} — {zone}",
                           participants,
                           {"source_event_id": ev["event_id"],
                            "source_pair": list(pair)},
                           game_minutes)
        _mark_participants(store, participants, etype, weight,
                           game_minutes, emotion="festival")
        if ev["event_type"] == "marriage" and other:
            rel.adjust_scores(store, host, other, game_minutes,
                              affection=5, relation_type="spouse")
        created.append(eid)
    return created


def run_festival(store, data, rng, profile, festival, game_minutes):
    """One culture festival: participants are the adults of the
    households holding that culture (plus their children), gathered
    in the zone where most of those households live."""
    households = culture_mod.households_with_profile(store,
                                                      profile["id"])
    if not households:
        return None
    from .identity import age_years
    participants, zone_counts = [], {}
    for hid in sorted(households):
        h = store.row("SELECT district_id FROM households"
                      " WHERE household_id = ?", (hid,))
        if h:
            zone_counts[h["district_id"]] = \
                zone_counts.get(h["district_id"], 0) + 1
        for m in store.rows(
                "SELECT c.character_id, c.born_at_game_minutes FROM"
                " household_members hm JOIN characters c"
                " ON c.character_id = hm.character_id"
                " WHERE hm.household_id = ?"
                " AND hm.left_at_game_minutes IS NULL"
                " AND c.died_at_game_minutes IS NULL"
                " ORDER BY c.character_id", (hid,)):
            participants.append(m["character_id"])
    if not participants:
        return None
    stream = rng.stream("festival", festival["id"],
                        game_minutes // 1440)
    order = participants[:]
    stream.shuffle(order)
    participants = sorted(order[:24])
    zone = max(sorted(zone_counts), key=lambda z: zone_counts[z]) \
        if zone_counts else None
    eid = create_event(store, "festival", zone,
                       festival["name"], participants,
                       {"festival_id": festival["id"],
                        "profile": profile["id"]}, game_minutes)
    for cid in participants:
        memory_mod.log_life_event(store, cid, "festival_celebration",
                                  game_minutes,
                                  details={"festival": festival["id"]})
        memory_mod.record_memory(store, cid, "festival", 30,
                                 game_minutes)
        emotions_mod.apply_event(store, cid, "festival")
    for i in range(0, len(participants) - 1, 2):
        social_mod.record_interaction(store, participants[i],
                                      participants[i + 1], "festival",
                                      "bonded", game_minutes)
    return eid


def public_meeting(store, data, rng, zone_id, game_minutes):
    """A community's monthly public meeting: its leader plus a
    deterministic sample of adult members, discussing the top
    derived issue (or community business when there is none)."""
    comm = store.row("SELECT * FROM communities WHERE community_id = ?",
                     (zone_id,))
    if comm is None:
        return None
    from .identity import age_years
    members = [m for m in store.rows(
        "SELECT c.character_id, c.born_at_game_minutes FROM"
        " community_members cm JOIN characters c"
        " ON c.character_id = cm.character_id WHERE cm.community_id = ?"
        " AND cm.left_at_game_minutes IS NULL"
        " AND c.died_at_game_minutes IS NULL ORDER BY c.character_id",
        (zone_id,))
        if age_years(m["born_at_game_minutes"], game_minutes) >= 18]
    if len(members) < 3:
        return None
    stream = rng.stream("meeting", zone_id, game_minutes // (30 * 1440))
    order = [m["character_id"] for m in members]
    stream.shuffle(order)
    participants = sorted(order[:9])
    leader = comm["leader_character_id"]
    if leader and leader not in participants:
        participants = sorted(participants[:8] + [leader])
    issues = json.loads(comm["issues"])
    topic = issues[0]["kind"] if issues else "community_business"
    eid = create_event(store, "public_meeting", zone_id,
                       f"Public meeting — {zone_id}", participants,
                       {"topic": topic, "leader": leader}, game_minutes)
    for cid in participants:
        memory_mod.log_life_event(store, cid, "community_meeting",
                                  game_minutes,
                                  details={"topic": topic})
        memory_mod.record_memory(store, cid, "public_meeting", 15,
                                 game_minutes)
    return eid


def family_gathering(store, data, rng, game_minutes, max_households=5):
    """Extended kin visit one household: affection grows on the kin
    edges between hosts and visitors, everyone remembers it, and a
    household whose culture carries the elder-respect tradition
    observes it when an elder is present."""
    from .identity import age_years
    households = store.rows("SELECT household_id FROM households"
                            " WHERE dissolved_at_game_minutes IS NULL"
                            " ORDER BY household_id")
    stream = rng.stream("gathering", game_minutes // (30 * 1440))
    order = [h["household_id"] for h in households]
    stream.shuffle(order)
    created = []
    engaged = set()  # a kin cluster gathers once per sweep, not twice
    for hid in order:
        if len(created) >= max_households:
            break
        if hid in engaged:
            continue
        hosts = [m["character_id"] for m in store.rows(
            "SELECT character_id FROM household_members"
            " WHERE household_id = ? AND left_at_game_minutes IS NULL",
            (hid,))]
        if not hosts:
            continue
        visitors = set()
        visitor_homes = set()
        for h in hosts:
            for kin in kinship.extended_family(store, h):
                krow = store.row("SELECT household_id FROM characters"
                                 " WHERE character_id = ?"
                                 " AND died_at_game_minutes IS NULL",
                                 (kin,))
                if krow and krow["household_id"] \
                        and krow["household_id"] != hid:
                    visitors.add(kin)
                    visitor_homes.add(krow["household_id"])
        if not visitors:
            continue
        engaged.add(hid)
        engaged |= visitor_homes
        visitors = sorted(visitors)[:6]
        participants = sorted(set(hosts) | set(visitors))
        zone = _zone_of(store, hosts[0])
        eid = create_event(store, "family_gathering", zone,
                           "Family gathering", participants,
                           {"host_household": hid}, game_minutes)
        for v in visitors:
            for h in hosts:
                for x, y in ((h, v), (v, h)):
                    for t in ("parent", "child", "sibling", "spouse"):
                        if rel.get_edge(store, x, y, t):
                            rel.adjust_scores(store, x, y, game_minutes,
                                              affection=3,
                                              relation_type=t)
                            break
            memory_mod.log_life_event(store, v, "family_visit",
                                      game_minutes)
        _mark_participants(store, participants, "family_gathering",
                           25, game_minutes, emotion="social_day")
        elders = [c for c in participants
                  if age_years(store.row(
                      "SELECT born_at_game_minutes FROM characters"
                      " WHERE character_id = ?", (c,))
                      ["born_at_game_minutes"], game_minutes) >= 65]
        if elders:
            culture_mod.observe_tradition(store, data, hid,
                                          "elder_respect_visit",
                                          game_minutes)
        created.append(eid)
    return created
