"""Session 05 Units 01+02 — National Government Foundation &
Government Organization.

One real country containing both cities. The country's identity
is grounded in the project's own data: every citizen carries
nationality 'Bangladeshi' (tools/sim/identity.py) and Rupsha City
— the Khulna-inspired District 1 — hosts the national
institutions (Session 04's labour model already anchors civic
institutions there). The data model supports multiple countries
(countries are rows; a second minimal record is constructible —
Unit 01's test does exactly that), but exactly ONE country is
populated: no second nation is fabricated.

Branches and authority: institutions are rows carrying an
authority list; offices are rows held by real citizens. Every
privileged government act in the sim (enacting a law, judging a
case, approving a policy or a budget, spending municipal money)
goes through require_authority(), which resolves the actor's
active offices — a citizen with no office, or an office in the
wrong branch, is refused in code. Cross-branch refusals are
unit-tested.

THE OWNER'S SEPARATION DIRECTIVE, stated plainly: all of this
authority exists only as in-simulation data. An office row lets
a simulated citizen move simulated money through the sim's
ledger under the sim's rules. It grants no access to any real
platform, account or permission system, and nothing outside
this package reads it.

Treasuries (the Session 04 deferred question, answered):
SYS-CITY remains the NATIONAL treasury (national taxes already
flow there). Each city gains its own MUNICIPAL treasury account
— a system character row, balance-enforced like any citizen, so
a municipality cannot overdraw. The split is a recorded,
conservation-preserving allocation: at setup, each city's
cumulative net municipal position (from Session 03's
municipal_budgets records) is transferred SYS-CITY -> city
account through the ledger (keyed, event-referenced); a city
whose position is negative starts at zero with the difference
recorded as an opening advance owed to the national treasury.
Thereafter, each month's attributable municipal revenue (rent,
commercial rent, property tax — located by the payer's /
property's city, the same attribution Session 04's govfinance
uses) is allocated the same way. Conservation identity — the
sum of all government account balances is unchanged by every
allocation — is test-proven. Session 03's services pass keeps
spending from SYS-CITY in v1 (its budget semantics are Session
03's own); the municipal treasuries fund Session 05's municipal
administration and city-scoped policies.
"""
import json

from . import cities as cities_mod
from . import identity as identity_mod

NATIONAL_ACCOUNT = "SYS-CITY"
MUNICIPAL_ACCOUNTS = {
    cities_mod.RUPSHA: "SYS-TREASURY-RUPSHA",
    cities_mod.SHIBNAGAR: "SYS-TREASURY-SHIBNAGAR",
}
TREASURY_ACCOUNTS = (NATIONAL_ACCOUNT,) \
    + tuple(MUNICIPAL_ACCOUNTS.values())

# (institution_id, name, branch, level, city_id, authority, account)
INSTITUTIONS = (
    ("GOV-PRESIDENCY", "Office of the President", "executive",
     "national", None,
     ["appoint_official", "assent_law"], NATIONAL_ACCOUNT),
    ("GOV-PM", "Office of the Prime Minister", "executive",
     "national", None,
     ["approve_policy", "propose_budget", "appoint_official",
      "sign_agreement", "declare_policy"], NATIONAL_ACCOUNT),
    ("GOV-FINANCE", "Ministry of Finance", "executive", "national",
     None, ["propose_budget", "manage_debt"], NATIONAL_ACCOUNT),
    ("GOV-LABOUR", "Ministry of Labour & Employment", "executive",
     "national", None, ["run_employment_programme"],
     NATIONAL_ACCOUNT),
    ("GOV-HOUSING", "Ministry of Housing & Infrastructure",
     "executive", "national", None, ["commission_construction"],
     NATIONAL_ACCOUNT),
    ("GOV-HEALTH", "Ministry of Health", "executive", "national",
     None, ["fund_health"], NATIONAL_ACCOUNT),
    ("GOV-EDUCATION", "Ministry of Education", "executive",
     "national", None, ["fund_education"], NATIONAL_ACCOUNT),
    ("GOV-PARLIAMENT", "Parliament", "legislative", "national",
     None, ["enact_law", "approve_budget", "debate_law"],
     NATIONAL_ACCOUNT),
    ("GOV-COURT", "Supreme Court", "judicial", "national", None,
     ["judge_case", "hear_appeal"], NATIONAL_ACCOUNT),
    ("GOV-EC", "Election Commission", "independent", "national",
     None, ["run_election"], NATIONAL_ACCOUNT),
    ("GOV-AUDIT", "Office of the Auditor General", "independent",
     "national", None, ["audit_accounts", "investigate_integrity"],
     NATIONAL_ACCOUNT),
    ("GOV-POLICE-RUPSHA", "Police Service — Rupsha City",
     "executive", "national", cities_mod.RUPSHA,
     ["investigate_incident", "enforce_safety"], NATIONAL_ACCOUNT),
    ("GOV-POLICE-SHIBNAGAR", "Police Service — Shibnagar",
     "executive", "national", cities_mod.SHIBNAGAR,
     ["investigate_incident", "enforce_safety"], NATIONAL_ACCOUNT),
    ("GOV-CITY-RUPSHA", "Rupsha City Corporation", "municipal",
     "municipal", cities_mod.RUPSHA,
     ["municipal_spend", "municipal_policy"],
     MUNICIPAL_ACCOUNTS[cities_mod.RUPSHA]),
    ("GOV-CITY-SHIBNAGAR", "Shibnagar Town Council", "municipal",
     "municipal", cities_mod.SHIBNAGAR,
     ["municipal_spend", "municipal_policy"],
     MUNICIPAL_ACCOUNTS[cities_mod.SHIBNAGAR]),
)

POLICE_INSTITUTIONS = {
    cities_mod.RUPSHA: "GOV-POLICE-RUPSHA",
    cities_mod.SHIBNAGAR: "GOV-POLICE-SHIBNAGAR",
}
MUNICIPAL_INSTITUTIONS = {
    cities_mod.RUPSHA: "GOV-CITY-RUPSHA",
    cities_mod.SHIBNAGAR: "GOV-CITY-SHIBNAGAR",
}

# Office titles whose holder is unique per institution.
SINGLETON_TITLES = ("president", "prime_minister", "minister",
                    "speaker", "chief_justice",
                    "election_commissioner", "auditor_general",
                    "mayor")
ALLOWANCE_KEYS = {"speaker": "mp"}


def is_setup(store):
    w = store.world()
    return bool(w and w.get("government_setup")) \
        and store.row("SELECT 1 FROM countries LIMIT 1") is not None


def city_of_character(store, data, character_id):
    """The city a citizen lives in, from their household's
    district against the city specs' zone lists (the same
    membership rule cities.city_population counts by). None
    when the citizen has no household in a known city."""
    row = store.row(
        "SELECT h.district_id FROM characters c JOIN households h"
        " ON h.household_id = c.household_id WHERE"
        " c.character_id = ?", (character_id,))
    if row is None or row["district_id"] is None:
        return None
    for spec in data.city_specs():
        if row["district_id"] in spec["zones"]:
            return spec["city_id"]
    return None


def log_event(store, event_type, actor_id, details, game_minutes):
    eid = store.next_id("GE", "government_events", "event_id")
    store.insert("government_events", event_id=eid,
                 event_type=event_type, actor_character_id=actor_id,
                 details=json.dumps(details, sort_keys=True),
                 game_minutes=game_minutes)
    return eid


# -- setup -------------------------------------------------------------

def _ensure_account(store, account_id, label):
    if store.row("SELECT 1 FROM characters WHERE character_id = ?",
                 (account_id,)) is None:
        store.insert("characters", character_id=account_id,
                     display_name=label, sim_tier="ambient", sex=None,
                     born_at_game_minutes=0, is_system=1,
                     balance_cached=0)


def _municipal_net_position(store, city_id):
    """A city's cumulative net municipal position from Session
    03's own budget records (revenue - spend over all recorded
    months). Zero for a world whose budgets have not run yet."""
    row = store.row(
        "SELECT COALESCE(SUM(revenue_tax_ncr + revenue_rent_ncr"
        " + revenue_other_ncr + property_tax_ncr"
        " - spend_services_ncr - spend_construction_ncr), 0) AS net"
        " FROM municipal_budgets WHERE city_id = ?", (city_id,))
    return row["net"] if row else 0


def split_treasuries(store, data, game_minutes):
    """The conservation-preserving treasury split. Returns
    {account_id: opening} plus the recorded advances. Idempotent:
    existing treasury rows are left exactly as they are."""
    out = {}
    if store.row("SELECT 1 FROM treasuries WHERE account_id = ?",
                 (NATIONAL_ACCOUNT,)) is None:
        store.insert(
            "treasuries", account_id=NATIONAL_ACCOUNT,
            scope="national", city_id=None,
            label="National Treasury (SYS-CITY)",
            opening_balance_ncr=store.balance(NATIONAL_ACCOUNT),
            opening_advance_ncr=0,
            opened_at_game_minutes=game_minutes)
    out[NATIONAL_ACCOUNT] = store.balance(NATIONAL_ACCOUNT)
    for city_id, account in MUNICIPAL_ACCOUNTS.items():
        if store.row("SELECT 1 FROM treasuries WHERE account_id"
                     " = ?", (account,)):
            out[account] = store.balance(account)
            continue
        _ensure_account(store, account,
                        f"Municipal Treasury: {city_id}")
        net = _municipal_net_position(store, city_id)
        opening, advance = 0, 0
        if net > 0:
            opening = min(net, max(0, store.balance(
                NATIONAL_ACCOUNT)))
            if opening > 0:
                store.transfer(
                    NATIONAL_ACCOUNT, account, opening,
                    "treasury_allocation", game_minutes,
                    note=f"treasury split: {city_id} municipal share",
                    transfer_key=f"treasury-open:{city_id}",
                    event_ref="session05:treasury_split")
        else:
            advance = -net
        store.insert(
            "treasuries", account_id=account, scope="municipal",
            city_id=city_id, label=f"Municipal Treasury: {city_id}",
            opening_balance_ncr=opening,
            opening_advance_ncr=advance,
            opened_at_game_minutes=game_minutes)
        out[account] = opening
    return out


def _adults(store, game_minutes):
    now = game_minutes
    out = []
    for c in store.rows("SELECT * FROM characters WHERE is_system"
                        " = 0 AND died_at_game_minutes IS NULL"
                        " ORDER BY character_id"):
        if identity_mod.age_years(c["born_at_game_minutes"],
                                  now) >= 18:
            out.append(c)
    return out


def _profile(store, character_id):
    return store.row("SELECT * FROM personality_profiles WHERE"
                     " character_id = ?", (character_id,)) or {}


def _pick(store, rng, candidates, stream_key, score_fn):
    """Deterministic pick: highest score, seeded jitter as the
    only tie-breaker."""
    best, best_score = None, None
    for c in candidates:
        score = score_fn(c) + rng.stream(
            "govpick", stream_key, c["character_id"]).uniform(0, 2)
        if best_score is None or score > best_score:
            best, best_score = c, score
    return best


def judge_candidates(store, data, game_minutes):
    """Citizens eligible for the bench (Unit 10's configured
    rule): age and intelligence thresholds, and — the separation
    of powers made concrete — holding no executive or
    legislative office."""
    cfg = data.government_config["judiciary"]
    out = []
    for c in _adults(store, game_minutes):
        if identity_mod.age_years(c["born_at_game_minutes"],
                                  game_minutes) \
                < cfg["judge_min_age"]:
            continue
        prof = _profile(store, c["character_id"])
        if prof.get("intelligence", 0) < cfg["judge_min_intelligence"]:
            continue
        branches = {r["branch"] for r in offices_of(
            store, c["character_id"])}
        if branches & {"executive", "legislative", "municipal"}:
            continue
        out.append(c)
    return out


def appoint_office(store, institution_id, title, holder_id, via,
                   game_minutes, constituency_city_id=None):
    """Seat a citizen in an office. Singleton titles first end
    the previous holder's term — the record is preserved, never
    deleted (peaceful transfer is a data property, not a hope)."""
    if title in SINGLETON_TITLES:
        for o in store.rows(
                "SELECT * FROM offices WHERE institution_id = ?"
                " AND title = ? AND status = 'active'",
                (institution_id, title)):
            if constituency_city_id is not None and \
                    o["constituency_city_id"] != constituency_city_id:
                continue
            end_office(store, o["office_id"], game_minutes)
    oid = store.next_id("OF", "offices", "office_id")
    store.insert("offices", office_id=oid,
                 institution_id=institution_id, title=title,
                 holder_character_id=holder_id,
                 constituency_city_id=constituency_city_id,
                 appointed_via=via,
                 term_started_at_game_minutes=game_minutes,
                 status="active")
    return oid


def end_office(store, office_id, game_minutes):
    store.execute("UPDATE offices SET status = 'ended',"
                  " term_ended_at_game_minutes = ? WHERE"
                  " office_id = ?", (game_minutes, office_id))


def offices_of(store, character_id):
    return store.rows(
        "SELECT o.*, i.branch, i.level, i.city_id AS inst_city_id,"
        " i.authority, i.account_id FROM offices o JOIN institutions"
        " i ON i.institution_id = o.institution_id WHERE"
        " o.holder_character_id = ? AND o.status = 'active'",
        (character_id,))


def current_office(store, institution_id, title,
                   constituency_city_id=None):
    sql = ("SELECT * FROM offices WHERE institution_id = ? AND"
           " title = ? AND status = 'active'")
    params = [institution_id, title]
    if constituency_city_id is not None:
        sql += " AND constituency_city_id = ?"
        params.append(constituency_city_id)
    rows = store.rows(sql + " ORDER BY office_id", tuple(params))
    return rows[0] if rows else None


def office_holder(store, title, institution_id=None):
    sql = "SELECT * FROM offices WHERE title = ? AND status = 'active'"
    params = [title]
    if institution_id:
        sql += " AND institution_id = ?"
        params.append(institution_id)
    rows = store.rows(sql + " ORDER BY office_id", tuple(params))
    return rows[0] if rows else None


# -- authority (Unit 02) -------------------------------------------------

def has_authority(store, character_id, action, city_id=None):
    """True when one of the actor's active offices sits in an
    institution whose authority list names the action. Municipal
    authority is scoped: it applies only inside its own city."""
    if character_id is None:
        return False
    for o in offices_of(store, character_id):
        if action not in json.loads(o["authority"]):
            continue
        if o["level"] == "municipal" and city_id is not None \
                and o["inst_city_id"] != city_id:
            continue
        return True
    return False


def require_authority(store, character_id, action, city_id=None):
    if not has_authority(store, character_id, action, city_id):
        raise PermissionError(
            f"{character_id} holds no office with authority"
            f" '{action}'" + (f" in {city_id}" if city_id else ""))


def institution_account(store, institution_id):
    row = store.row("SELECT account_id FROM institutions WHERE"
                    " institution_id = ?", (institution_id,))
    return row["account_id"] if row else NATIONAL_ACCOUNT


# -- caretaker + vacancy filling -----------------------------------------

def _leadership_score(store):
    def score(c):
        p = _profile(store, c["character_id"])
        return p.get("intelligence", 0) + p.get("discipline", 0)
    return score


def appoint_caretakers(store, data, rng, game_minutes):
    """Genesis office holders, labelled caretaker: a government
    must exist before the first election can be held under it.
    Picks are deterministic (leadership score + seeded jitter);
    judges come only from the bench-eligible pool."""
    adults = _adults(store, game_minutes)
    if not adults:
        return {}
    seated = {}

    def seat(institution, title, pool, key, via="caretaker"):
        if current_office(store, institution, title):
            return current_office(store, institution,
                                  title)["holder_character_id"]
        pick = _pick(store, rng, pool, key, _leadership_score(store))
        if pick is None:
            return None
        appoint_office(store, institution, title,
                       pick["character_id"], via, game_minutes)
        seated[title] = pick["character_id"]
        return pick["character_id"]

    seat("GOV-PRESIDENCY", "president", adults, "president")
    seat("GOV-PM", "prime_minister", adults, "pm")
    for inst, key in (("GOV-FINANCE", "fin"), ("GOV-LABOUR", "lab"),
                      ("GOV-HOUSING", "hou"), ("GOV-HEALTH", "hea"),
                      ("GOV-EDUCATION", "edu")):
        seat(inst, "minister", adults, key)
    bench = judge_candidates(store, data, game_minutes) or adults
    seat("GOV-COURT", "chief_justice", bench, "cj")
    n_judges = max(0, data.government_config["judiciary"]
                   ["judges_national"] - 1)
    seated_judges = {o["holder_character_id"] for o in store.rows(
        "SELECT holder_character_id FROM offices WHERE"
        " institution_id = 'GOV-COURT' AND status = 'active'")}
    for i in range(n_judges):
        pool = [c for c in bench
                if c["character_id"] not in seated_judges]
        if not pool:
            break
        pick = _pick(store, rng, pool, f"judge{i}",
                     _leadership_score(store))
        appoint_office(store, "GOV-COURT", "judge",
                       pick["character_id"], "caretaker",
                       game_minutes)
        seated_judges.add(pick["character_id"])
    seat("GOV-EC", "election_commissioner", adults, "ec")
    seat("GOV-AUDIT", "auditor_general", adults, "ag")
    appoint_mayors(store, data, rng, game_minutes, via="caretaker")
    return seated


def appoint_mayors(store, data, rng, game_minutes, via="appointment",
                   party_id=None):
    """One mayor per city, from that city's own residents. A city
    with no residents (Shibnagar at genesis) honestly has no
    mayor until someone lives there — retried monthly."""
    out = {}
    for city_id, inst in MUNICIPAL_INSTITUTIONS.items():
        if current_office(store, inst, "mayor"):
            continue
        residents = []
        for c in _adults(store, game_minutes):
            if not c["household_id"]:
                continue
            h = store.row("SELECT district_id FROM households"
                          " WHERE household_id = ?",
                          (c["household_id"],))
            if h and cities_mod.city_of_zone(data,
                                             h["district_id"]) \
                    == city_id:
                residents.append(c)
        if party_id:
            members = {m["character_id"] for m in store.rows(
                "SELECT character_id FROM party_memberships WHERE"
                " party_id = ? AND left_at_game_minutes IS NULL",
                (party_id,))}
            party_residents = [c for c in residents
                               if c["character_id"] in members]
            if party_residents:
                residents = party_residents
        if not residents:
            continue
        pick = _pick(store, rng, residents, f"mayor:{city_id}",
                     _leadership_score(store))
        appoint_office(store, inst, "mayor", pick["character_id"],
                       via, game_minutes)
        out[city_id] = pick["character_id"]
    return out


def fill_vacancies(store, data, rng, game_minutes):
    """Death and time vacate offices; the state does not stop.
    Ended offices of dead holders are closed out, and critical
    offices are refilled by the same deterministic rules
    (labelled 'succession')."""
    changed = []
    for o in store.rows("SELECT * FROM offices WHERE status ="
                        " 'active' AND holder_character_id IS NOT"
                        " NULL"):
        holder = store.row("SELECT died_at_game_minutes FROM"
                           " characters WHERE character_id = ?",
                           (o["holder_character_id"],))
        if holder and holder["died_at_game_minutes"] is not None:
            end_office(store, o["office_id"], game_minutes)
            log_event(store, "office_vacated", o["holder_character_id"],
                      {"office_id": o["office_id"],
                       "title": o["title"], "cause": "death"},
                      game_minutes)
            changed.append(o["office_id"])
    critical = (("GOV-PRESIDENCY", "president"),
                ("GOV-PM", "prime_minister"),
                ("GOV-COURT", "chief_justice"),
                ("GOV-EC", "election_commissioner"),
                ("GOV-AUDIT", "auditor_general"))
    adults = _adults(store, game_minutes)
    for inst, title in critical:
        if current_office(store, inst, title) or not adults:
            continue
        pool = judge_candidates(store, data, game_minutes) \
            if inst == "GOV-COURT" else adults
        if not pool:
            continue
        pick = _pick(store, rng, pool, f"succession:{title}",
                     _leadership_score(store))
        appoint_office(store, inst, title, pick["character_id"],
                       "succession", game_minutes)
        log_event(store, "office_succession", pick["character_id"],
                  {"institution_id": inst, "title": title},
                  game_minutes)
    appoint_mayors(store, data, rng, game_minutes, via="succession")
    return changed


def setup_government(store, data, rng, game_minutes=480):
    """The Session 05 bootstrap (idempotent; hand-built worlds
    that never call it have no government layer and every
    Session 05 pass no-ops). Mirrors the cities/economy setup
    pattern of Sessions 03/04."""
    if is_setup(store):
        return {"already_setup": True}
    cfg = data.government_config
    country = cfg["country"]
    store.insert("countries", country_id=country["country_id"],
                 name=country["name"],
                 capital_city_id=country["capital_city_id"],
                 currency_code=country["currency_code"],
                 next_election_month=cfg["elections"]
                 ["inaugural_month"],
                 created_at_game_minutes=game_minutes)
    treasuries = split_treasuries(store, data, game_minutes)
    for (iid, name, branch, level, city_id, authority,
         account) in INSTITUTIONS:
        store.insert("institutions", institution_id=iid,
                     country_id=country["country_id"], name=name,
                     branch=branch, level=level, city_id=city_id,
                     authority=json.dumps(authority),
                     account_id=account, active=1)
    seated = appoint_caretakers(store, data, rng, game_minutes)
    from . import politics as politics_mod
    parties = politics_mod.setup_parties(store, data, rng,
                                         game_minutes)
    from . import diplomacy as diplomacy_mod
    partner = diplomacy_mod.setup_partner(store, data, game_minutes)
    from . import policies as policies_mod
    plan = policies_mod.create_default_plan(store, data,
                                            game_minutes)
    store.set_world(government_setup=1)
    log_event(store, "government_founded", None,
              {"country": country["country_id"],
               "treasuries": treasuries, "parties": parties,
               "caretakers": seated, "partner": partner,
               "development_plan": plan}, game_minutes)
    store.commit()
    return {"country": country["country_id"],
            "treasuries": treasuries, "caretakers": seated,
            "parties": parties}


# -- money: government payroll -------------------------------------------

def pay_government_wages(store, data, month_index, game_minutes):
    """Wages for employments whose employer is a treasury account
    (Session 04 civic hires carry SYS-CITY; Session 05 civil
    servants carry their institution's account). Paid BEFORE the
    settlement taxes what was received, exactly like business
    wages. The national treasury is a system account (it may run
    an overdraft — that overdraft IS the recorded public debt);
    municipal treasuries are balance-enforced, so a broke
    municipality pays what it holds and the shortfall is a
    recorded government event. Returns {employment_id: paid}."""
    paid = {}
    if not is_setup(store):
        return paid
    for emp in store.rows(
            "SELECT * FROM employments WHERE"
            " employer_character_id IS NOT NULL"
            " AND ended_at_game_minutes IS NULL"
            " ORDER BY employment_id"):
        account = emp["employer_character_id"]
        if account not in TREASURY_ACCOUNTS:
            continue
        due = emp["wage_per_month"]
        if account == NATIONAL_ACCOUNT:
            amount = due
        else:
            amount = min(due, max(0, store.balance(account)))
        paid[emp["employment_id"]] = amount
        if amount > 0:
            store.transfer(
                account, emp["character_id"], amount, "wage",
                game_minutes,
                note=f"{emp['profession_id']} monthly wage"
                     " (government employer)",
                transfer_key=f"gwage:{emp['employment_id']}:"
                             f"{month_index}",
                event_ref=f"month:{month_index}")
        if amount < due:
            log_event(store, "wage_shortfall",
                      emp["character_id"],
                      {"employment_id": emp["employment_id"],
                       "account": account, "due_ncr": due,
                       "paid_ncr": amount,
                       "month_index": month_index}, game_minutes)
    return paid


def pay_office_allowances(store, data, month_index, game_minutes):
    """Monthly office allowances (config amounts, SIM MODEL) from
    each institution's treasury account. National accounts pay in
    full; a municipal account pays what it holds."""
    cfg = data.government_config["offices"][
        "allowance_ncr_per_month"]
    paid_total = 0
    for o in store.rows(
            "SELECT o.*, i.account_id FROM offices o JOIN"
            " institutions i ON i.institution_id ="
            " o.institution_id WHERE o.status = 'active' AND"
            " o.holder_character_id IS NOT NULL ORDER BY"
            " o.office_id"):
        key = ALLOWANCE_KEYS.get(o["title"], o["title"])
        amount = cfg.get(key, 0)
        if amount <= 0:
            continue
        account = o["account_id"] or NATIONAL_ACCOUNT
        pay = amount if account == NATIONAL_ACCOUNT else min(
            amount, max(0, store.balance(account)))
        if pay > 0:
            store.transfer(
                account, o["holder_character_id"], pay,
                "office_allowance", game_minutes,
                note=f"{o['title']} allowance",
                transfer_key=f"allowance:{o['office_id']}:"
                             f"{month_index}",
                event_ref=f"office:{o['office_id']}")
            paid_total += pay
        if pay < amount:
            log_event(store, "allowance_shortfall",
                      o["holder_character_id"],
                      {"office_id": o["office_id"],
                       "due_ncr": amount, "paid_ncr": pay,
                       "month_index": month_index}, game_minutes)
    return paid_total


def treasury_allocation_pass(store, data, month_index, game_minutes):
    """The ongoing half of the treasury split: this month's
    attributable municipal revenue moves SYS-CITY -> the city's
    own treasury. Attribution is located, not modelled: rent by
    the payer's household district, commercial rent by the
    business's property, property tax by the taxed property —
    the same locations Session 04's govfinance reports. National
    taxes (income, business, sales, tariff) stay national."""
    if not is_setup(store):
        return {}
    since = game_minutes - 30 * 1440
    per_city = {cid: 0 for cid in MUNICIPAL_ACCOUNTS}

    def locate(district_id):
        city = cities_mod.city_of_zone(data, district_id) \
            if district_id else None
        return city if city in per_city else None

    for r in store.rows(
            "SELECT l.amount, h.district_id FROM economy_ledger l"
            " JOIN characters c ON c.character_id ="
            " l.from_character_id LEFT JOIN households h"
            " ON h.household_id = c.household_id WHERE"
            " l.to_character_id = 'SYS-CITY' AND l.reason_code ="
            " 'rent' AND l.game_minutes > ? AND l.game_minutes"
            " <= ?", (since, game_minutes)):
        city = locate(r["district_id"])
        if city:
            per_city[city] += r["amount"]
    for r in store.rows(
            "SELECT l.amount, p.district_id FROM economy_ledger l"
            " JOIN businesses b ON b.business_id ="
            " l.from_business_id JOIN properties p"
            " ON p.property_id = b.property_id WHERE"
            " l.reason_code = 'commercial_rent'"
            " AND l.game_minutes > ? AND l.game_minutes <= ?",
            (since, game_minutes)):
        city = locate(r["district_id"])
        if city:
            per_city[city] += r["amount"]
    for r in store.rows(
            "SELECT l.amount, p.district_id FROM economy_ledger l"
            " JOIN properties p ON p.property_id ="
            " l.related_property_id WHERE l.reason_code = 'tax'"
            " AND l.note = 'property tax' AND l.game_minutes > ?"
            " AND l.game_minutes <= ?", (since, game_minutes)):
        city = locate(r["district_id"])
        if city:
            per_city[city] += r["amount"]
    out = {}
    for city_id, total in per_city.items():
        if total <= 0:
            out[city_id] = 0
            continue
        pay = min(total, max(0, store.balance(NATIONAL_ACCOUNT)))
        if pay > 0:
            store.transfer(
                NATIONAL_ACCOUNT, MUNICIPAL_ACCOUNTS[city_id], pay,
                "treasury_allocation", game_minutes,
                note=f"municipal revenue allocation {city_id}",
                transfer_key=f"treasury-alloc:{city_id}:"
                             f"{month_index}",
                event_ref=f"month:{month_index}")
        out[city_id] = pay
    return out


def government_balances(store):
    """Every government account's balance — the conservation
    surface the audits and tests read."""
    return {a: store.balance(a) for a in TREASURY_ACCOUNTS
            if store.row("SELECT 1 FROM characters WHERE"
                         " character_id = ?", (a,))}


# -- the monthly government cadence ---------------------------------------

def monthly_pass(store, data, rng, month_index, game_minutes):
    """Session 05's monthly cadence, run after the economy close
    (indicators and crises for the month exist). Every sub-pass
    is bounded to its own tables, in the established scheduled-
    update pattern. Returns a summary of what happened."""
    if not is_setup(store):
        return None
    from . import admin as admin_mod
    from . import diplomacy as diplomacy_mod
    from . import integrity as integrity_mod
    from . import justice as justice_mod
    from . import policies as policies_mod
    from . import politics as politics_mod
    from . import safety as safety_mod
    out = {}
    out["vacancies_filled"] = fill_vacancies(store, data, rng,
                                             game_minutes)
    out["opinion"] = politics_mod.update_opinion(
        store, data, month_index, game_minutes)
    out["election"] = politics_mod.maybe_run_election(
        store, data, rng, month_index, game_minutes)
    out["party_dues"] = politics_mod.collect_dues(
        store, data, month_index, game_minutes)
    out["feedback"] = politics_mod.feedback_pass(
        store, data, rng, month_index, game_minutes)
    out["civil_service"] = admin_mod.monthly_pass(
        store, data, rng, month_index, game_minutes)
    out["allowances"] = pay_office_allowances(
        store, data, month_index, game_minutes)
    out["treasury_allocation"] = treasury_allocation_pass(
        store, data, month_index, game_minutes)
    out["budget"] = policies_mod.budget_pass(
        store, data, month_index, game_minutes)
    out["decisions"] = policies_mod.decision_engine_pass(
        store, data, rng, month_index, game_minutes)
    out["policies"] = policies_mod.monthly_pass(
        store, data, month_index, game_minutes)
    out["justice"] = justice_mod.monthly_pass(
        store, data, rng, month_index, game_minutes)
    out["safety"] = safety_mod.monthly_pass(
        store, data, rng, month_index, game_minutes)
    out["integrity"] = integrity_mod.monthly_pass(
        store, data, rng, month_index, game_minutes)
    out["diplomacy"] = diplomacy_mod.monthly_pass(
        store, data, rng, month_index, game_minutes)
    return out
