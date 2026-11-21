"""Session 05 Units 03+04+05 — Political Parties, Elections,
Citizen Participation & Public Opinion.

Parties are data (data/government-config.json genesis list):
name, platform text and a five-dimension stance vector. Nothing
about a party is hardcoded here. A party's treasury is its own
ledger account (the party id doubles as the account id, a system
row like the SYS accounts), balance-enforced — a party cannot
spend money it does not hold. Funding is real: founders
contribute from their own balances at registration, members pay
configured monthly dues, campaigns are paid from the treasury.

Opinion is measured, not scripted. Every month each adult's
approval is recomputed from their own recorded experience —
their wage change in the ledger, their employment state, the
price index's movement, their city's service levels and safety
record, and whether a measured crisis is live — blended with
last month's value (political inertia). Party support is the
best alignment between the citizen's stance vector (political
temperament from personality, shifted by measured circumstances:
poverty raises welfare stance, business ownership raises the
market stance, local incidents raise the law-and-order stance)
and each party's configured stances.

Elections are the constitution in code (government-config's
constitution, article 1): every citizen aged 18+ may vote, one
ballot per voter per election enforced by a UNIQUE constraint,
ballots append-only at the database level. A voter's choice is
derived from their actual state (alignment + incumbent approval
effect + campaign visibility + a seeded jitter) — there is no
random voting and no dice-roll electorate. Counting is a pure
function of the ballot rows; recount() re-derives it and must
agree. Government formation replaces the executive, legislative
and municipal office holders and preserves the outgoing records:
the transfer of power is itself a government event.
"""
import json
import sqlite3

from . import cities as cities_mod
from . import government as gov
from . import identity as identity_mod

DIMENSIONS = ("economy", "welfare", "services", "development",
              "law_order")
SUPPORT_THRESHOLD = 55      # below this alignment: independent
JOIN_THRESHOLD = 70         # support this strong may formalise
MAX_JOINS_PER_PARTY_MONTH = 3


# -- parties (Unit 03) ---------------------------------------------------

def _ensure_party_account(store, party_id, name):
    if store.row("SELECT 1 FROM characters WHERE character_id = ?",
                 (party_id,)) is None:
        store.insert("characters", character_id=party_id,
                     display_name=f"Party: {name}",
                     sim_tier="ambient", sex=None,
                     born_at_game_minutes=0, is_system=1,
                     balance_cached=0)


def citizen_stance(store, data, char, game_minutes, city_facts=None):
    """A citizen's stance vector: political temperament from
    their personality profile, shifted by measured circumstances
    (their balance against the poverty line, business ownership,
    their city's services and safety). Deterministic."""
    from . import indicators as indicators_mod
    prof = gov._profile(store, char["character_id"])
    stance = {
        "economy": prof.get("risk_tolerance", 50),
        "welfare": prof.get("empathy", 50),
        "services": prof.get("cooperation", 50),
        "development": prof.get("ambition", 50),
        "law_order": prof.get("discipline", 50),
    }
    cid = char["character_id"]
    owns_business = store.row(
        "SELECT 1 FROM businesses WHERE owner_character_id = ?"
        " AND closed_at_game_minutes IS NULL", (cid,))
    employed = store.row(
        "SELECT 1 FROM employments WHERE character_id = ?"
        " AND ended_at_game_minutes IS NULL", (cid,))
    age = identity_mod.age_years(char["born_at_game_minutes"],
                                 game_minutes)
    if owns_business:
        stance["economy"] += 15
        stance["welfare"] -= 10
    if age >= 18 and age < 65 and not employed \
            and not owns_business:
        stance["welfare"] += 20
    if store.balance(cid) < indicators_mod.poverty_line(data):
        stance["welfare"] += 15
    if city_facts:
        city = city_of_citizen(store, data, char)
        facts = city_facts.get(city) if city else None
        if facts:
            if facts.get("avg_service_level", 100) < 50:
                stance["services"] += 15
            if facts.get("incidents_last_month", 0) > 0:
                stance["law_order"] += 10
            if facts.get("vacancy_rate", 1) < 0.08:
                stance["development"] += 10
    return {k: max(0, min(100, round(v))) for k, v in stance.items()}


def alignment(stance, party_stances):
    """100 minus the mean absolute distance over the dimensions."""
    if not party_stances:
        return 0.0
    dist = sum(abs(stance.get(d, 50) - party_stances.get(d, 50))
               for d in DIMENSIONS) / len(DIMENSIONS)
    return round(100 - dist, 2)


def city_of_citizen(store, data, char):
    if char.get("household_id"):
        h = store.row("SELECT district_id FROM households WHERE"
                      " household_id = ?", (char["household_id"],))
        if h:
            city = cities_mod.city_of_zone(data, h["district_id"])
            if city:
                return city
    return data.government_config["country"]["capital_city_id"]


def city_facts(store, data, month_index, game_minutes):
    """Measured per-city facts opinion and voting read: average
    municipal service level, incidents last month, vacancy."""
    from . import distribution as distribution_mod
    since = game_minutes - 30 * 1440
    facts = {}
    for spec in data.city_specs():
        cid = spec["city_id"]
        lvl = store.row(
            "SELECT AVG(level) AS l FROM municipal_services"
            " WHERE city_id = ?", (cid,))
        inc = store.row(
            "SELECT COUNT(*) AS n FROM incidents WHERE city_id = ?"
            " AND created_at_game_minutes > ?", (cid, since))
        housing = distribution_mod.housing_pressure(store, data, cid)
        facts[cid] = {
            "avg_service_level": round(lvl["l"], 1)
            if lvl and lvl["l"] is not None else 100.0,
            "incidents_last_month": inc["n"] if inc else 0,
            "vacancy_rate": housing["vacancy_rate"],
            "population": cities_mod.city_population(store, data,
                                                     cid),
        }
    return facts


def setup_parties(store, data, rng, game_minutes):
    """Register the configured genesis parties: founders are the
    citizens whose stances align best (deterministic, seeded
    jitter as tie-break), the best-aligned founder leads, and
    every founder contributes the configured seed from their own
    balance when they hold it. Returns {party_id: leader_id}."""
    cfg = data.government_config["parties"]
    adults = gov._adults(store, game_minutes)
    facts = city_facts(store, data, 0, game_minutes)
    taken = set()
    out = {}
    for spec in cfg["genesis"]:
        pid = spec["party_id"]
        if store.row("SELECT 1 FROM parties WHERE party_id = ?",
                     (pid,)):
            out[pid] = store.row(
                "SELECT leader_character_id FROM parties WHERE"
                " party_id = ?", (pid,))["leader_character_id"]
            continue
        _ensure_party_account(store, pid, spec["name"])
        store.insert("parties", party_id=pid, name=spec["name"],
                     short=spec.get("short"),
                     account_id=pid, leader_character_id=None,
                     stances=json.dumps(spec["stances"]),
                     platform=spec.get("platform"),
                     status="registered",
                     founded_at_game_minutes=game_minutes)
        scored = []
        for c in adults:
            if c["character_id"] in taken:
                continue
            stance = citizen_stance(store, data, c, game_minutes,
                                    facts)
            score = alignment(stance, spec["stances"]) \
                + rng.stream("partyfound", pid,
                             c["character_id"]).uniform(0, 2)
            scored.append((score, c["character_id"]))
        scored.sort(key=lambda t: (-t[0], t[1]))
        founders = scored[:5]
        for i, (_score, cid) in enumerate(founders):
            role = "leader" if i == 0 else "candidate" if i < 3 \
                else "member"
            store.insert("party_memberships", party_id=pid,
                         character_id=cid, role=role,
                         joined_at_game_minutes=game_minutes)
            taken.add(cid)
            contribution = cfg["founder_seed_contribution_ncr"]
            if store.balance(cid) >= contribution:
                store.transfer(
                    cid, pid, contribution, "party_funding",
                    game_minutes, note="founder contribution",
                    transfer_key=f"party-seed:{pid}:{cid}",
                    event_ref=f"party:{pid}")
        if founders:
            leader = founders[0][1]
            store.execute("UPDATE parties SET leader_character_id"
                          " = ? WHERE party_id = ?", (leader, pid))
            out[pid] = leader
        gov.log_event(store, "party_registered", out.get(pid),
                      {"party_id": pid, "name": spec["name"],
                       "founders": [c for _s, c in founders]},
                      game_minutes)
    return out


def members_of(store, party_id):
    return store.rows(
        "SELECT * FROM party_memberships WHERE party_id = ? AND"
        " left_at_game_minutes IS NULL ORDER BY character_id",
        (party_id,))


def party_of(store, character_id):
    row = store.row(
        "SELECT party_id FROM party_memberships WHERE"
        " character_id = ? AND left_at_game_minutes IS NULL",
        (character_id,))
    return row["party_id"] if row else None


def governing_party(store):
    """The party of the sitting Prime Minister, if any."""
    pm = gov.office_holder(store, "prime_minister", "GOV-PM")
    if not pm or not pm["holder_character_id"]:
        return None
    return party_of(store, pm["holder_character_id"])


def collect_dues(store, data, month_index, game_minutes):
    """Members pay the configured monthly dues from their own
    balances (only when they hold more than the dues — a broke
    member is not taxed into arrears by their party)."""
    dues = data.government_config["parties"][
        "membership_dues_ncr_per_month"]
    total = 0
    for m in store.rows("SELECT * FROM party_memberships WHERE"
                        " left_at_game_minutes IS NULL ORDER BY"
                        " party_id, character_id"):
        cid = m["character_id"]
        char = store.row("SELECT died_at_game_minutes FROM"
                         " characters WHERE character_id = ?",
                         (cid,))
        if char is None or char["died_at_game_minutes"] is not None:
            continue
        if store.balance(cid) > dues:
            store.transfer(
                cid, m["party_id"], dues, "party_dues",
                game_minutes, note="monthly party dues",
                transfer_key=f"dues:{m['party_id']}:{cid}:"
                             f"{month_index}",
                event_ref=f"party:{m['party_id']}")
            total += dues
    return total


def grow_memberships(store, data, month_index, game_minutes):
    """Citizens whose measured support is strong and who belong
    to no party may formalise it — capped per party per month,
    strongest alignment first (deterministic)."""
    facts = city_facts(store, data, month_index, game_minutes)
    joined = {}
    parties = store.rows("SELECT * FROM parties WHERE status ="
                         " 'registered' ORDER BY party_id")
    for p in parties:
        stances = json.loads(p["stances"])
        candidates = []
        for op in store.rows(
                "SELECT character_id, support_party_id FROM"
                " citizen_opinion WHERE support_party_id = ?",
                (p["party_id"],)):
            cid = op["character_id"]
            if party_of(store, cid):
                continue
            char = store.row("SELECT * FROM characters WHERE"
                             " character_id = ?", (cid,))
            if char is None or char["died_at_game_minutes"] \
                    is not None:
                continue
            score = alignment(
                citizen_stance(store, data, char, game_minutes,
                               facts), stances)
            if score >= JOIN_THRESHOLD:
                candidates.append((score, cid))
        candidates.sort(key=lambda t: (-t[0], t[1]))
        for _s, cid in candidates[:MAX_JOINS_PER_PARTY_MONTH]:
            store.insert("party_memberships", party_id=p["party_id"],
                         character_id=cid, role="member",
                         joined_at_game_minutes=game_minutes)
            joined.setdefault(p["party_id"], []).append(cid)
    return joined


# -- opinion & participation (Unit 05) ------------------------------------

def _wage_in_window(store, character_id, since, until):
    return store.row(
        "SELECT COALESCE(SUM(amount),0) AS s FROM economy_ledger"
        " WHERE to_character_id = ? AND reason_code = 'wage'"
        " AND game_minutes > ? AND game_minutes <= ?",
        (character_id, since, until))["s"]


def update_opinion(store, data, month_index, game_minutes):
    """Monthly approval + support for every living adult, from
    their own records. Returns the national snapshot row."""
    from . import crises as crises_mod
    from . import indicators as indicators_mod
    facts = city_facts(store, data, month_index, game_minutes)
    latest = indicators_mod.latest(store, "national") or {}
    metrics = latest.get("metrics") or {}
    inflation = metrics.get("inflation_monthly_percent") or 0.0
    crisis_active = bool(crises_mod.active_crises(store))
    parties = store.rows("SELECT * FROM parties WHERE status ="
                         " 'registered' ORDER BY party_id")
    stances = {p["party_id"]: json.loads(p["stances"])
               for p in parties}
    incumbent = governing_party(store)
    since = game_minutes - 30 * 1440
    prev_since = since - 30 * 1440
    support_counts = {}
    approvals = []
    for c in gov._adults(store, game_minutes):
        cid = c["character_id"]
        wage_now = _wage_in_window(store, cid, since, game_minutes)
        wage_prev = _wage_in_window(store, cid, prev_since, since)
        if wage_prev > 0:
            income_c = max(-25.0, min(25.0, (wage_now - wage_prev)
                                      / wage_prev * 100))
        elif wage_now > 0:
            income_c = 10.0
        else:
            age = identity_mod.age_years(c["born_at_game_minutes"],
                                         game_minutes)
            income_c = -8.0 if 18 <= age < 65 else 0.0
        city = city_of_citizen(store, data, c)
        cfacts = facts.get(city) or {}
        services_c = (cfacts.get("avg_service_level", 100) - 50) \
            * 0.3
        incidents = cfacts.get("incidents_last_month", 0)
        pop = max(1, cfacts.get("population", 1))
        safety_c = -min(20.0, incidents / pop * 100 * 2.0)
        price_c = max(-20.0, min(10.0, -inflation * 2.0))
        crisis_c = -12.0 if crisis_active else 0.0
        raw = 50 + income_c + services_c + safety_c + price_c \
            + crisis_c
        prev = store.row("SELECT approval FROM citizen_opinion"
                         " WHERE character_id = ?", (cid,))
        approval = round(max(0.0, min(100.0,
                                      0.6 * raw + 0.4 * prev[
                                          "approval"]))
                         if prev else max(0.0, min(100.0, raw)), 2)
        stance = citizen_stance(store, data, c, game_minutes, facts)
        best_party, best_score = None, None
        for pid, pst in stances.items():
            score = alignment(stance, pst)
            if best_score is None or score > best_score:
                best_party, best_score = pid, score
        support = best_party if best_score is not None \
            and best_score >= SUPPORT_THRESHOLD else None
        if incumbent and support == incumbent:
            pass  # support is alignment, not loyalty — stated.
        components = {"income": round(income_c, 2),
                      "services": round(services_c, 2),
                      "safety": round(safety_c, 2),
                      "prices": round(price_c, 2),
                      "crisis": crisis_c,
                      "alignment_best": best_score,
                      "incumbent": incumbent}
        store.execute(
            "INSERT OR REPLACE INTO citizen_opinion"
            " (character_id, approval, support_party_id,"
            " components, updated_month, updated_at_game_minutes)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (cid, approval, support, json.dumps(components),
             month_index, game_minutes))
        approvals.append(approval)
        if support:
            support_counts[support] = support_counts.get(
                support, 0) + 1
    mean_approval = round(sum(approvals) / len(approvals), 2) \
        if approvals else 0.0
    total_support = sum(support_counts.values()) or 1
    shares = {pid: round(n / total_support, 4)
              for pid, n in sorted(support_counts.items())}
    store.execute(
        "INSERT OR REPLACE INTO opinion_snapshots (month_index,"
        " mean_approval, support_shares, respondents, game_minutes)"
        " VALUES (?, ?, ?, ?, ?)",
        (month_index, mean_approval, json.dumps(shares),
         len(approvals), game_minutes))
    grow_memberships(store, data, month_index, game_minutes)
    return {"mean_approval": mean_approval,
            "support_shares": shares, "respondents": len(approvals)}


def approval_rating(store):
    row = store.row("SELECT * FROM opinion_snapshots ORDER BY"
                    " month_index DESC LIMIT 1")
    return dict(row) if row else None


def file_feedback(store, kind, character_id, topic, game_minutes,
                  stance=None, details=None):
    fid = store.next_id("FB", "citizen_feedback", "feedback_id")
    store.insert("citizen_feedback", feedback_id=fid, kind=kind,
                 character_id=character_id, topic=topic,
                 stance=stance,
                 details=json.dumps(details or {}, sort_keys=True),
                 status="open", created_at_game_minutes=game_minutes)
    return fid


def open_consultation(store, topic, details, game_minutes,
                      actor_id=None):
    """A government consultation: citizens respond in the next
    feedback pass, by their measured stance on the topic's
    dimension; the tally is the recorded outcome the government
    reads before it acts (decision engine factors)."""
    return file_feedback(store, "consultation", actor_id, topic,
                         game_minutes, details=details)


def feedback_pass(store, data, rng, month_index, game_minutes):
    """Measured-trigger participation, capped and deterministic:
    hardship complaints from households the records show are
    struggling, service petitions from poorly served cities, and
    responses to open consultations."""
    out = {"complaints": 0, "petitions": 0, "consultations": 0}
    since = game_minutes - 30 * 1440
    hardship = store.rows(
        "SELECT DISTINCT character_id FROM life_events WHERE"
        " event_type = 'food_shortage' AND game_minutes > ?"
        " ORDER BY character_id LIMIT 5", (since,))
    for r in hardship:
        if store.row("SELECT 1 FROM citizen_feedback WHERE"
                     " character_id = ? AND topic ="
                     " 'household_hardship' AND status = 'open'",
                     (r["character_id"],)):
            continue
        file_feedback(store, "complaint", r["character_id"],
                      "household_hardship", game_minutes,
                      details={"trigger": "food_shortage_event"})
        out["complaints"] += 1
    facts = city_facts(store, data, month_index, game_minutes)
    for city_id, f in facts.items():
        if f["avg_service_level"] >= 40 or f["population"] == 0:
            continue
        residents = [c for c in gov._adults(store, game_minutes)
                     if city_of_citizen(store, data, c) == city_id]
        for c in residents[:2]:
            file_feedback(store, "petition", c["character_id"],
                          "public_services", game_minutes,
                          stance="support",
                          details={"city_id": city_id,
                                   "avg_service_level":
                                   f["avg_service_level"]})
            out["petitions"] += 1
    for cons in store.rows("SELECT * FROM citizen_feedback WHERE"
                           " kind = 'consultation' AND status ="
                           " 'open' ORDER BY feedback_id"):
        details = json.loads(cons["details"])
        dimension = details.get("dimension", "services")
        support = oppose = 0
        for c in gov._adults(store, game_minutes)[:40]:
            stance = citizen_stance(store, data, c, game_minutes,
                                    facts)
            if stance.get(dimension, 50) >= 55:
                support += 1
            elif stance.get(dimension, 50) <= 40:
                oppose += 1
        store.execute(
            "UPDATE citizen_feedback SET status = 'closed',"
            " response = ?, closed_at_game_minutes = ? WHERE"
            " feedback_id = ?",
            (json.dumps({"support": support, "oppose": oppose,
                         "dimension": dimension}),
             game_minutes, cons["feedback_id"]))
        out["consultations"] += 1
    return out


# -- elections (Unit 04) ---------------------------------------------------

def eligible_voters(store, data, game_minutes):
    cfg = data.government_config["elections"]
    out = []
    for c in gov._adults(store, game_minutes):
        if identity_mod.age_years(c["born_at_game_minutes"],
                                  game_minutes) \
                >= cfg["eligibility_age"]:
            out.append(c)
    return out


def cast_ballot(store, data, election_id, character_id, party_id,
                game_minutes):
    """Cast one ballot. Eligibility and the one-ballot rule are
    enforced here AND by the database (UNIQUE + immutability
    triggers): a second ballot raises, it never overwrites."""
    election = store.row("SELECT * FROM elections WHERE"
                         " election_id = ?", (election_id,))
    if election is None:
        raise ValueError(f"unknown election {election_id}")
    if election["status"] not in ("scheduled", "voting"):
        raise ValueError(f"election {election_id} is not open")
    char = store.row("SELECT * FROM characters WHERE character_id"
                     " = ?", (character_id,))
    if char is None or char["died_at_game_minutes"] is not None \
            or char["is_system"]:
        raise ValueError(f"{character_id} is not a living citizen")
    age = identity_mod.age_years(char["born_at_game_minutes"],
                                 game_minutes)
    if age < data.government_config["elections"]["eligibility_age"]:
        raise ValueError(f"{character_id} is under the voting age")
    if store.row("SELECT 1 FROM parties WHERE party_id = ? AND"
                 " status = 'registered'", (party_id,)) is None:
        raise ValueError(f"party {party_id} is not registered")
    bid = store.next_id("BL", "ballots", "ballot_id")
    try:
        store.insert("ballots", ballot_id=bid,
                     election_id=election_id,
                     character_id=character_id,
                     city_id=city_of_citizen(store, data, char),
                     party_id=party_id, game_minutes=game_minutes)
    except sqlite3.IntegrityError as exc:
        raise ValueError(
            f"{character_id} has already voted in"
            f" {election_id}") from exc
    return bid


def count_ballots(store, election_id):
    """The count is a pure function of the ballot rows."""
    by_city = {}
    totals = {}
    for r in store.rows(
            "SELECT city_id, party_id, COUNT(*) AS n FROM ballots"
            " WHERE election_id = ? GROUP BY city_id, party_id",
            (election_id,)):
        by_city.setdefault(r["city_id"], {})[r["party_id"]] = r["n"]
        totals[r["party_id"]] = totals.get(r["party_id"], 0) \
            + r["n"]
    return {"by_city": by_city, "totals": totals}


def allocate_seats(votes_by_party, seats):
    """Largest-remainder proportional allocation, deterministic
    (ties broken by party id)."""
    total = sum(votes_by_party.values())
    if total == 0 or seats == 0:
        return {pid: 0 for pid in votes_by_party}
    quotas = {pid: v / total * seats
              for pid, v in votes_by_party.items()}
    won = {pid: int(q) for pid, q in quotas.items()}
    remaining = seats - sum(won.values())
    remainders = sorted(
        votes_by_party, key=lambda pid: (-(quotas[pid] - won[pid]),
                                         pid))
    for pid in remainders[:remaining]:
        won[pid] += 1
    return won


def _campaign(store, data, election_id, game_minutes):
    """Parties spend from their own treasuries on visibility
    (capped share, configured). Returns {party_id: spend}."""
    cfg = data.government_config["elections"]
    spends = {}
    for p in store.rows("SELECT * FROM parties WHERE status ="
                        " 'registered' ORDER BY party_id"):
        balance = store.balance(p["party_id"])
        spend = int(balance * cfg["campaign_spend_cap_share"])
        if spend > 0:
            store.transfer(
                p["party_id"], "SYS-MARKET", spend, "campaign",
                game_minutes, note=f"campaign {election_id}",
                transfer_key=f"campaign:{election_id}:"
                             f"{p['party_id']}",
                event_ref=f"election:{election_id}")
        spends[p["party_id"]] = spend
    return spends


def _choose_party(store, data, rng, char, election_id, facts,
                  stances, incumbent, visibility):
    stance = citizen_stance(store, data, char,
                            store.world()["game_minutes"], facts)
    cfg = data.government_config["elections"]
    best, best_score = None, None
    for pid, pst in stances.items():
        score = alignment(stance, pst)
        if incumbent and pid == incumbent:
            op = store.row("SELECT approval FROM citizen_opinion"
                           " WHERE character_id = ?",
                           (char["character_id"],))
            if op:
                score += (op["approval"] - 50) * 0.1
        score += visibility.get(pid, 0.0) \
            * cfg["campaign_visibility_weight"]
        score += rng.stream("vote", election_id,
                            char["character_id"]).uniform(0, 3)
        if best_score is None or score > best_score:
            best, best_score = pid, score
    if best_score is not None and best_score < 40:
        return None  # abstention: no party is close enough
    return best


def run_election(store, data, rng, month_index, game_minutes):
    """A full election: campaign, ballots, count, seats, and
    government formation. Run by the Election Commission (its
    office holder is the recorded actor)."""
    cfg = data.government_config["elections"]
    country = store.row("SELECT * FROM countries LIMIT 1")
    eid = store.next_id("EL", "elections", "election_id")
    ec = gov.office_holder(store, "election_commissioner", "GOV-EC")
    actor = ec["holder_character_id"] if ec else None
    store.insert("elections", election_id=eid,
                 country_id=country["country_id"],
                 month_index=month_index, status="voting",
                 rules=json.dumps(cfg), game_minutes=game_minutes)
    spends = _campaign(store, data, eid, game_minutes)
    total_spend = sum(spends.values()) or 1
    visibility = {pid: s / total_spend for pid, s in spends.items()}
    parties = store.rows("SELECT * FROM parties WHERE status ="
                         " 'registered' ORDER BY party_id")
    stances = {p["party_id"]: json.loads(p["stances"])
               for p in parties}
    incumbent = governing_party(store)
    facts = city_facts(store, data, month_index, game_minutes)
    voters = eligible_voters(store, data, game_minutes)
    cast = 0
    for c in voters:
        choice = _choose_party(store, data, rng, c, eid, facts,
                               stances, incumbent, visibility)
        if choice is None:
            continue
        cast_ballot(store, data, eid, c["character_id"], choice,
                    game_minutes)
        cast += 1
    counted = count_ballots(store, eid)
    seats_cfg = cfg["seats_per_city"]
    results = {"by_city": {}, "totals": counted["totals"],
               "seats": {}, "campaign_spend": spends}
    total_seats = {}
    for city_id, party_votes in counted["by_city"].items():
        seats = allocate_seats(party_votes,
                               seats_cfg.get(city_id, 0))
        results["by_city"][city_id] = {"votes": party_votes,
                                      "seats": seats}
        for pid, s in seats.items():
            total_seats[pid] = total_seats.get(pid, 0) + s
    results["seats"] = total_seats
    winner = None
    if total_seats:
        winner = sorted(
            total_seats,
            key=lambda pid: (-total_seats[pid],
                             -counted["totals"].get(pid, 0),
                             pid))[0]
    store.execute(
        "UPDATE elections SET status = 'counted', turnout = ?,"
        " eligible = ?, results = ?, winner_party_id = ? WHERE"
        " election_id = ?",
        (cast, len(voters), json.dumps(results, sort_keys=True),
         winner, eid))
    gov.log_event(store, "election_held", actor,
                  {"election_id": eid, "turnout": cast,
                   "eligible": len(voters), "winner": winner,
                   "seats": total_seats}, game_minutes)
    formation = None
    if winner:
        formation = form_government(store, data, rng, eid, winner,
                                    results, game_minutes)
        store.execute("UPDATE elections SET status = 'formed'"
                      " WHERE election_id = ?", (eid,))
    store.execute("UPDATE countries SET next_election_month = ?"
                  " WHERE country_id = ?",
                  (month_index + cfg["term_months"],
                   country["country_id"]))
    return {"election_id": eid, "turnout": cast,
            "eligible": len(voters), "winner": winner,
            "seats": total_seats, "formation": formation}


def form_government(store, data, rng, election_id, winner_party_id,
                    results, game_minutes):
    """Government formation after a counted election. Executive,
    legislative and municipal offices turn over; the judiciary
    and the independent commissions keep their terms (separation
    of powers). Outgoing holders' rows are ended, never deleted —
    the transfer of power is a recorded event."""
    outgoing = gov.office_holder(store, "prime_minister", "GOV-PM")
    outgoing_pm = outgoing["holder_character_id"] if outgoing \
        else None
    turnover_institutions = [
        i["institution_id"] for i in store.rows(
            "SELECT institution_id FROM institutions WHERE"
            " branch IN ('executive', 'legislative', 'municipal')")]
    for o in store.rows("SELECT * FROM offices WHERE status ="
                        " 'active'"):
        if o["institution_id"] in turnover_institutions:
            gov.end_office(store, o["office_id"], game_minutes)
    party = store.row("SELECT * FROM parties WHERE party_id = ?",
                      (winner_party_id,))
    members = members_of(store, winner_party_id)
    member_ids = [m["character_id"] for m in members]
    leader = party["leader_character_id"] \
        if party else (member_ids[0] if member_ids else None)
    seated = {}
    if leader:
        gov.appoint_office(store, "GOV-PM", "prime_minister",
                           leader, f"election:{election_id}",
                           game_minutes)
        seated["prime_minister"] = leader
    pool = [c for c in gov._adults(store, game_minutes)
            if c["character_id"] in member_ids
            and c["character_id"] != leader]
    # President: the winning party's most senior remaining member
    # (head of state; appoints officials, assents to laws).
    pick = gov._pick(store, rng, pool, "president",
                     gov._leadership_score(store))
    if pick:
        gov.appoint_office(store, "GOV-PRESIDENCY", "president",
                           pick["character_id"],
                           f"election:{election_id}", game_minutes)
        seated["president"] = pick["character_id"]
        pool = [c for c in pool
                if c["character_id"] != pick["character_id"]]
    for inst in ("GOV-FINANCE", "GOV-LABOUR", "GOV-HOUSING",
                 "GOV-HEALTH", "GOV-EDUCATION"):
        pick = gov._pick(store, rng, pool, f"minister:{inst}",
                         gov._leadership_score(store))
        if pick is None:
            continue
        gov.appoint_office(store, inst, "minister",
                           pick["character_id"],
                           f"election:{election_id}", game_minutes)
        seated[inst] = pick["character_id"]
        pool = [c for c in pool
                if c["character_id"] != pick["character_id"]]
    # Parliament: seats per city filled by each party's members,
    # residents of the constituency first, candidates before
    # members, then by alignment to their own party.
    mp_count = 0
    for city_id, city_result in results["by_city"].items():
        for pid, seats in sorted(city_result["seats"].items()):
            if seats <= 0:
                continue
            party_members = members_of(store, pid)
            facts = city_facts(store, data, 0, game_minutes)
            pst = json.loads(store.row(
                "SELECT stances FROM parties WHERE party_id = ?",
                (pid,))["stances"])

            def rank(m):
                char = store.row("SELECT * FROM characters WHERE"
                                 " character_id = ?",
                                 (m["character_id"],))
                resident = 0 if city_of_citizen(
                    store, data, char) == city_id else 1
                role_rank = {"candidate": 0, "leader": 1,
                             "member": 2}.get(m["role"], 2)
                score = alignment(citizen_stance(
                    store, data, char, game_minutes, facts), pst)
                return (resident, role_rank, -score,
                        m["character_id"])

            for m in sorted(party_members, key=rank)[:seats]:
                gov.appoint_office(
                    store, "GOV-PARLIAMENT", "mp",
                    m["character_id"], f"election:{election_id}",
                    game_minutes, constituency_city_id=city_id)
                mp_count += 1
    # Speaker: a winning-party MP.
    speaker_pool = [o for o in gov.offices_of(store, leader or "")
                    ] if leader else []
    mps = store.rows(
        "SELECT o.* FROM offices o WHERE o.institution_id ="
        " 'GOV-PARLIAMENT' AND o.title = 'mp' AND o.status ="
        " 'active'")
    winning_mps = [o for o in mps
                   if party_of(store, o["holder_character_id"])
                   == winner_party_id]
    if winning_mps:
        gov.appoint_office(store, "GOV-PARLIAMENT", "speaker",
                           winning_mps[0]["holder_character_id"],
                           f"election:{election_id}", game_minutes)
        seated["speaker"] = winning_mps[0]["holder_character_id"]
    # Mayors: from the party that won each city.
    for city_id, city_result in results["by_city"].items():
        city_seats = city_result["seats"]
        if not city_seats:
            continue
        city_winner = sorted(
            city_seats, key=lambda pid: (-city_seats[pid], pid))[0]
        gov.appoint_mayors(store, data, rng, game_minutes,
                           via=f"election:{election_id}",
                           party_id=city_winner)
    gov.log_event(store, "government_formed", leader,
                  {"election_id": election_id,
                   "party_id": winner_party_id, "seated": seated,
                   "mps": mp_count}, game_minutes)
    if outgoing_pm and outgoing_pm != leader:
        gov.log_event(store, "transfer_of_power", leader,
                      {"outgoing_prime_minister": outgoing_pm,
                       "incoming_prime_minister": leader,
                       "election_id": election_id,
                       "peaceful": True}, game_minutes)
    return {"party_id": winner_party_id, "seated": seated,
            "mps": mp_count}


def recount(store, election_id):
    """Independent recount from the immutable ballot rows; must
    agree with the stored result (the election audit)."""
    election = store.row("SELECT * FROM elections WHERE"
                         " election_id = ?", (election_id,))
    if election is None:
        return None
    counted = count_ballots(store, election_id)
    stored = json.loads(election["results"] or "{}")
    return {"recount_totals": counted["totals"],
            "stored_totals": stored.get("totals", {}),
            "agree": counted["totals"] == stored.get("totals", {}),
            "ballots": sum(counted["totals"].values()),
            "turnout_recorded": election["turnout"]}


def maybe_run_election(store, data, rng, month_index, game_minutes):
    country = store.row("SELECT * FROM countries LIMIT 1")
    if country is None:
        return None
    nxt = country["next_election_month"]
    if nxt is None or month_index < nxt:
        return None
    if store.row("SELECT 1 FROM elections WHERE month_index = ?",
                 (month_index,)):
        return None
    return run_election(store, data, rng, month_index, game_minutes)
