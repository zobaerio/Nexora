"""Session 04 Units 01-02 — Economic Foundation & Individual Finance.

Unit 01: the two cities are the local economies of one national
economy. A region's characteristics are DERIVED from its records
(the Session 03 registry already classifies each city; this module
adds the economic reading: output, employment, trade balance) and
the currency is configuration (data/economy-config.json, whose
code matches prices.json's canonical 'currency'). The economy's
event history is the ledger itself plus the city/business event
logs — there is no separate invented chronicle.

Unit 02: a person's financial profile is computed FROM the ledger,
never stored as a parallel truth: income and expenses by reason
code over a window, current balance, assets (bank deposits,
property, business equity, investments), debt (household arrears
share + outstanding loans) and obligations (rent, loan repayments).
Purchasing power is the balance plus bank deposits minus the next
month's obligations. Because the profile is a pure function of
ledger rows, it can never disagree with the money.

The traceability spine (the owner's Session 04 order): every
ledger row names its source, its destination, its reason code and
— for Session 04 flows — its idempotency key and the simulation
event that caused it. verify_conservation() is the double-entry
check: across the whole ledger, money is never created or
destroyed inside a transfer — every row moves `amount` from
exactly one endpoint to exactly one endpoint, and the caches
reconcile (Store.ledger_sum_check).
"""
import json

from . import cities as cities_mod


def is_setup(store):
    w = store.world()
    return bool(w and w.get("economy_setup"))


def currency(data):
    cfg = data.economy_config["currency"]
    return {"code": cfg["code"], "name": cfg["name"],
            "canonical_source": data.prices.get("currency")}


def regions(store, data):
    """The national economy's regions: one per city, with the
    characteristics its records support."""
    out = []
    for spec in data.city_specs():
        cid = spec["city_id"]
        row = store.row("SELECT * FROM cities WHERE city_id = ?",
                        (cid,))
        pop = cities_mod.city_population(store, data, cid)
        flows = store.rows(
            "SELECT from_city_id, to_city_id, COALESCE(SUM(amount_ncr),0)"
            " AS s FROM trade_flows GROUP BY from_city_id, to_city_id")
        exports = sum(f["s"] for f in flows if f["from_city_id"] == cid)
        imports = sum(f["s"] for f in flows if f["to_city_id"] == cid)
        out.append({
            "city_id": cid, "name": spec["name"],
            "kind": spec["kind"],
            "population": pop,
            "development_level": row["development_level"] if row else None,
            "development_index": row["development_index"] if row else None,
            "economic_class": row["economic_class"] if row else None,
            "climate": row["climate"] if row else None,
            "trade_exports_ncr": exports, "trade_imports_ncr": imports,
            "trade_balance_ncr": exports - imports,
        })
    return {"currency": currency(data), "regions": out}


def _window(store, character_id, since, until, direction):
    col = "to_character_id" if direction == "in" else "from_character_id"
    rows = store.rows(
        f"SELECT reason_code, COALESCE(SUM(amount),0) AS s,"
        f" COUNT(*) AS n FROM economy_ledger WHERE {col} = ?"
        f" AND game_minutes > ? AND game_minutes <= ?"
        f" GROUP BY reason_code ORDER BY reason_code",
        (character_id, since, until))
    return {r["reason_code"]: {"total_ncr": r["s"], "count": r["n"]}
            for r in rows}


def financial_profile(store, data, character_id, months=3):
    """Unit 02's profile, computed from live records. `months` is
    the trailing window for income/expense history."""
    world = store.world()
    now = world["game_minutes"]
    since = now - months * 30 * 1440
    char = store.row("SELECT * FROM characters WHERE character_id = ?",
                     (character_id,))
    if char is None:
        return None
    income = _window(store, character_id, since, now, "in")
    expenses = _window(store, character_id, since, now, "out")
    balance = store.balance(character_id)
    bank = store.row("SELECT balance_cached FROM bank_accounts"
                     " WHERE character_id = ? AND closed_at_game_minutes"
                     " IS NULL", (character_id,))
    deposits = bank["balance_cached"] if bank else 0
    loans = store.rows("SELECT * FROM loans WHERE borrower_character_id"
                       " = ? AND status = 'active'", (character_id,))
    loan_debt = sum(l["outstanding_ncr"] for l in loans)
    monthly_repayment = sum(
        _monthly_payment(l["principal_ncr"], l["annual_rate_percent"],
                         l["term_months"]) for l in loans)
    properties = store.rows(
        "SELECT property_id, market_value FROM properties"
        " WHERE owner_character_id = ?", (character_id,))
    property_value = sum(p["market_value"] for p in properties)
    owned_businesses = store.rows(
        "SELECT business_id, balance_cached FROM businesses"
        " WHERE owner_character_id = ? AND closed_at_game_minutes"
        " IS NULL", (character_id,))
    business_equity = sum(b["balance_cached"] for b in owned_businesses)
    from . import banking as banking_mod
    investments_value = banking_mod.portfolio_value(store, character_id)
    tenancy = store.row(
        "SELECT t.rent_per_month FROM tenancies t JOIN household_members"
        " hm ON hm.household_id = t.tenant_household_id"
        " WHERE hm.character_id = ? AND hm.left_at_game_minutes IS NULL"
        " AND t.ended_at_game_minutes IS NULL", (character_id,))
    rent = tenancy["rent_per_month"] if tenancy else 0
    from . import family_economy
    arrears = 0
    if char["household_id"]:
        arrears = family_economy.debt_of(store, char["household_id"])
    assets = deposits + property_value + business_equity \
        + investments_value
    obligations = rent + monthly_repayment
    return {
        "character_id": character_id,
        "name": char["display_name"],
        "balance_ncr": balance,
        "income_by_reason": income,
        "expenses_by_reason": expenses,
        "income_total_ncr": sum(v["total_ncr"] for v in income.values()),
        "expenses_total_ncr": sum(v["total_ncr"]
                                  for v in expenses.values()),
        "assets": {"bank_deposits_ncr": deposits,
                   "property_value_ncr": property_value,
                   "business_equity_ncr": business_equity,
                   "investments_value_ncr": investments_value,
                   "total_ncr": assets},
        "debt": {"loans_ncr": loan_debt, "household_arrears_ncr": arrears,
                 "total_ncr": loan_debt + arrears},
        "obligations_monthly_ncr": obligations,
        "purchasing_power_ncr": balance + deposits - obligations,
        "net_worth_ncr": balance + assets - loan_debt - arrears,
    }


def _monthly_payment(principal, annual_rate_percent, term_months):
    """The level monthly payment of an amortising loan (the same
    formula banking.py charges by)."""
    if principal <= 0 or term_months <= 0:
        return 0
    r = annual_rate_percent / 100 / 12
    if r == 0:
        return round(principal / term_months)
    return round(principal * r / (1 - (1 + r) ** -term_months))


def transaction_history(store, character_id, limit=50):
    """The person's auditable money trail: every row that touches
    them, newest first, with source, destination, reason and the
    causing event where recorded."""
    return store.rows(
        "SELECT ledger_id, from_character_id, to_character_id,"
        " from_business_id, to_business_id, amount, reason_code,"
        " note, game_minutes, transfer_key, event_ref FROM"
        " economy_ledger WHERE from_character_id = ?"
        " OR to_character_id = ? ORDER BY ledger_id DESC LIMIT ?",
        (character_id, character_id, limit))


def verify_conservation(store):
    """Double-entry integrity over the whole ledger:
    - every row has exactly one source and one destination
      endpoint (character or business);
    - every row's amount is positive;
    - caches reconcile (Store.ledger_sum_check);
    - transfer keys, where present, are unique (enforced by the
      unique index; verified here for the report).
    Returns a list of violations — empty means the books balance."""
    violations = []
    bad = store.row(
        "SELECT COUNT(*) AS n FROM economy_ledger WHERE"
        " ((from_character_id IS NULL AND from_business_id IS NULL)"
        " OR (to_character_id IS NULL AND to_business_id IS NULL)"
        " OR (from_character_id IS NOT NULL AND from_business_id"
        " IS NOT NULL) OR (to_character_id IS NOT NULL AND"
        " to_business_id IS NOT NULL) OR amount <= 0)")["n"]
    if bad:
        violations.append(f"{bad} malformed ledger rows")
    dup = store.row(
        "SELECT COUNT(*) AS n FROM (SELECT transfer_key FROM"
        " economy_ledger WHERE transfer_key IS NOT NULL"
        " GROUP BY transfer_key HAVING COUNT(*) > 1)")["n"]
    if dup:
        violations.append(f"{dup} duplicated transfer keys")
    mismatches = store.ledger_sum_check()
    if mismatches:
        violations.append(f"{len(mismatches)} cache mismatches")
    return violations


def economic_event_history(store, limit=100):
    """The economy's event history: business events + city events,
    merged chronologically (the ledger itself is the money side of
    the same history)."""
    biz = store.rows(
        "SELECT 'business' AS source, business_id AS subject,"
        " event_type, details, game_minutes FROM business_events"
        " ORDER BY game_minutes DESC LIMIT ?", (limit,))
    city = store.rows(
        "SELECT 'city' AS source, city_id AS subject, event_type,"
        " details, game_minutes FROM city_events ORDER BY"
        " game_minutes DESC LIMIT ?", (limit,))
    out = biz + city
    out.sort(key=lambda r: -r["game_minutes"])
    for r in out:
        r["details"] = json.loads(r["details"])
    return out[:limit]
