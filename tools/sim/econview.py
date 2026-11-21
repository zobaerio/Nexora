"""Session 04 Unit 16 — Economy Observatory (data layer).

Live views over the economy's persistent records, in the same
read-live discipline as Sessions 02/03: every number here is
computed from ledger rows, business records, bank records,
indicator snapshots and crisis records at call time. There is no
dashboard state and nothing is fabricated — interactive charts
are a future UI layer over exactly these payloads.
"""
import json

from . import banking as banking_mod
from . import business as business_mod
from . import cities as cities_mod
from . import crises as crises_mod
from . import finance as finance_mod
from . import govfinance as govfinance_mod
from . import indicators as indicators_mod
from . import labour as labour_mod
from . import market as market_mod
from . import trade as trade_mod


def economy_overview(store, data):
    if not business_mod.is_setup(store):
        return {"economy_setup": False}
    latest = indicators_mod.latest(store, "national")
    prices = {}
    for spec in data.city_specs():
        cid = spec["city_id"]
        prices[cid] = {g: market_mod.price_of(store, data, cid, g)
                       for g in data.goods}
    top = []
    for b in business_mod.active_businesses(store):
        top.append({"business_id": b["business_id"],
                    "name": b["name"], "category": b["category"],
                    "owner": b["owner_character_id"],
                    "balance_ncr": store.business_balance(
                        b["business_id"]),
                    "net_worth_ncr": business_mod.net_worth(
                        store, data, b),
                    "status": b["status"]})
    top.sort(key=lambda r: -r["net_worth_ncr"])
    return {
        "economy_setup": True,
        "foundation": finance_mod.regions(store, data),
        "tax_rules": govfinance_mod.tax_rules_view(data),
        "indicators": latest,
        "indicators_methodology": indicators_mod.METHODOLOGY,
        "bank": banking_mod.bank_stats(store),
        "bank_reconciliation_violations":
            banking_mod.account_reconciliation(store),
        "conservation_violations": finance_mod.verify_conservation(
            store),
        "labour": labour_mod.unemployment_stats(store, data),
        "prices": prices,
        "price_index": {spec["city_id"]: market_mod.price_index(
            store, data, spec["city_id"])
            for spec in data.city_specs()},
        "businesses_top_by_worth": top[:10],
        "businesses_active": len(top),
        "crises_active": [dict(c, severity=json.loads(c["severity"]))
                          for c in crises_mod.active_crises(store)],
        "recent_events": finance_mod.economic_event_history(
            store, limit=20),
    }


def business_view(store, data, business_id):
    b = store.row("SELECT * FROM businesses WHERE business_id = ?",
                  (business_id,))
    if b is None:
        return None
    city = business_mod.business_city(store, data, b)
    inventory = {r["good_id"]: r["quantity"] for r in store.rows(
        "SELECT good_id, quantity FROM business_inventory WHERE"
        " business_id = ? AND quantity > 0", (business_id,))}
    return {
        "business": dict(b),
        "city_id": city,
        "balance_ncr": store.business_balance(business_id),
        "net_worth_ncr": business_mod.net_worth(store, data, b),
        "share_price_ncr": banking_mod.share_price(store, data, b),
        "employees": business_mod.employees_of(store, business_id),
        "wage_bill_ncr": business_mod.wage_bill(store, business_id),
        "inventory": inventory,
        "pnl_history": store.rows(
            "SELECT * FROM business_monthly WHERE business_id = ?"
            " ORDER BY month_index", (business_id,)),
        "shareholders": store.rows(
            "SELECT character_id, shares, invested_ncr FROM"
            " investments WHERE business_id = ? AND status ="
            " 'active'", (business_id,)),
        "events": store.rows(
            "SELECT event_type, details, game_minutes FROM"
            " business_events WHERE business_id = ? ORDER BY"
            " game_minutes DESC LIMIT 30", (business_id,)),
    }


def bank_view(store, data):
    return {
        "stats": banking_mod.bank_stats(store),
        "reconciliation_violations":
            banking_mod.account_reconciliation(store),
        "loans": store.rows(
            "SELECT loan_id, borrower_character_id, kind,"
            " principal_ncr, outstanding_ncr, annual_rate_percent,"
            " status, missed_payments FROM loans ORDER BY loan_id"),
        "reserves_ncr": store.balance("SYS-BANK"),
        "rules": data.prices["loans"],
    }


def indicators_view(store, data, scope="national"):
    rows = store.rows("SELECT month_index, metrics FROM"
                      " economic_indicators WHERE scope = ?"
                      " ORDER BY month_index", (scope,))
    return {"scope": scope,
            "methodology": indicators_mod.METHODOLOGY,
            "series": [{"month_index": r["month_index"],
                        "metrics": json.loads(r["metrics"])}
                       for r in rows]}


def person_finance_view(store, data, character_id):
    return finance_mod.financial_profile(store, data, character_id)
