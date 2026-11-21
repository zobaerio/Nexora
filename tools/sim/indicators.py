"""Session 04 Unit 11 — Economic Indicators.

Every indicator is computed from records and carries its
methodology with it (METHODOLOGY below, also surfaced by the
observatory). Nothing is estimated from thin air: if a series
cannot be computed for a month, it is absent from that month's
snapshot, not interpolated.

Methodology (income approach, monthly window = the settled
month's ledger rows):
- GDP = compensation of employees (all 'wage' ledger payments)
  + gross operating surplus (business_monthly profit + its tax,
  i.e. pre-tax profit) + taxes on production (sales tax +
  tariffs collected). Pensions and other transfers are excluded
  (they are transfers, not production).
- GDP per capita = GDP / living population.
- Unemployment = Unit 03's measured rate (labour force = resident
  adults 18-64 not in college).
- Inflation = the market price index (Unit 07's consumption
  basket, genesis = 100) month-over-month percent.
- Productivity = GDP / employed residents.
- Household income = median of the month's household_finances
  income rows.
- Consumer spending = the month's 'purchase' ledger payments
  (the settlement's living-cost payments).
- Business investment = construction funding + production costs
  + business-to-business purchases in the window.
- Government revenue = all ledger inflows to SYS-CITY.
- Trade balance (per city) = the month's trade_flows exports -
  imports (the national figure is gross volume; internal trade
  nets to zero by construction and says so).
- Poverty = share of households whose month income is below the
  poverty line: the lower lifestyle band's full living costs
  (prices.json) + the tier-1 rent — a priced subsistence basket.
- Wealth distribution = living non-system characters' ledger
  balances: p10/p50/p90 and the Gini coefficient.
"""
import json
import statistics

from . import cities as cities_mod
from . import labour as labour_mod
from . import market as market_mod

METHODOLOGY = {
    "gdp": "wages paid + pre-tax business profit + production"
           " taxes (income approach, monthly ledger window)",
    "unemployment": "unemployed / labour force (resident adults"
                    " 18-64 not enrolled in college)",
    "inflation": "market consumption-basket price index,"
                 " month-over-month percent",
    "poverty": "household month income below the priced"
               " subsistence basket (lower band living costs +"
               " tier-1 rent)",
    "wealth": "ledger balances of living non-system characters",
}


def _sum_reason(store, reason, since, until, *, from_business=False):
    col = "from_business_id" if from_business else None
    sql = ("SELECT COALESCE(SUM(amount),0) AS s FROM economy_ledger"
           " WHERE reason_code = ? AND game_minutes > ?"
           " AND game_minutes <= ?")
    if from_business:
        sql += " AND from_business_id IS NOT NULL"
    return store.row(sql, (reason, since, until))["s"]


def _gini(values):
    if not values:
        return 0.0
    xs = sorted(values)
    n = len(xs)
    total = sum(xs)
    if total <= 0:
        return 0.0
    cum = sum((i + 1) * x for i, x in enumerate(xs))
    return round((2 * cum) / (n * total) - (n + 1) / n, 4)


def poverty_line(data):
    lc = data.prices["living_costs_monthly"]
    total = sum(lc[k]["lower"] or 0 for k in (
        "food_home_cooking", "utilities_power_water_internet",
        "clothing_personal", "transport_public_bus_rickshaw",
        "eating_out_monthly", "household_services_monthly"))
    rent = next(r["rent_ncr"] for r in
                data.prices["rent_monthly_by_tier"] if r["tier"] == 1)
    return total + rent


def compute_indicators(store, data, month_index, game_minutes):
    since = game_minutes - 30 * 1440
    wages = _sum_reason(store, "wage", since, game_minutes)
    surplus = store.row(
        "SELECT COALESCE(SUM(profit_ncr + tax_ncr),0) AS s FROM"
        " business_monthly WHERE month_index = ?",
        (month_index,))["s"]
    production_taxes = _sum_reason(store, "sales_tax", since,
                                   game_minutes) \
        + _sum_reason(store, "tariff", since, game_minutes)
    gdp = wages + surplus + production_taxes
    alive = store.row("SELECT COUNT(*) AS n FROM characters WHERE"
                      " is_system = 0 AND died_at_game_minutes"
                      " IS NULL")["n"]
    labour = labour_mod.unemployment_stats(store, data)
    index_now = market_mod.price_index(store, data)
    prev = store.row("SELECT metrics FROM economic_indicators"
                     " WHERE scope = 'national' AND month_index = ?",
                     (month_index - 1,))
    inflation = None
    if prev:
        prev_index = json.loads(prev["metrics"]).get("price_index")
        if prev_index:
            inflation = round((index_now / prev_index - 1) * 100, 2)
    incomes = [r["income_ncr"] for r in store.rows(
        "SELECT income_ncr FROM household_finances WHERE"
        " month_index = ?", (month_index,))]
    line = poverty_line(data)
    poor = sum(1 for i in incomes if i < line)
    balances = [r["balance_cached"] for r in store.rows(
        "SELECT balance_cached FROM characters WHERE is_system = 0"
        " AND died_at_game_minutes IS NULL")]
    balances.sort()
    exports = store.row(
        "SELECT COALESCE(SUM(amount_ncr),0) AS s FROM trade_flows"
        " WHERE month_index = ?", (month_index,))["s"]
    gov_revenue = store.row(
        "SELECT COALESCE(SUM(amount),0) AS s FROM economy_ledger"
        " WHERE to_character_id = 'SYS-CITY' AND game_minutes > ?"
        " AND game_minutes <= ?", (since, game_minutes))["s"]
    investment = _sum_reason(store, "construction_funding", since,
                             game_minutes) \
        + _sum_reason(store, "production_cost", since, game_minutes) \
        + _sum_reason(store, "business_sale", since, game_minutes,
                      from_business=True)
    national = {
        "gdp_ncr": gdp,
        "gdp_per_capita_ncr": round(gdp / alive) if alive else 0,
        "population": alive,
        "labour_force": labour["labour_force"],
        "employed": labour["employed"],
        "unemployed": labour["unemployed"],
        "unemployment_rate": labour["unemployment_rate"],
        "price_index": index_now,
        "inflation_monthly_percent": inflation,
        "productivity_ncr": round(gdp / labour["employed"])
        if labour["employed"] else 0,
        "household_income_median_ncr": int(statistics.median(incomes))
        if incomes else 0,
        "consumer_spending_ncr": _sum_reason(store, "purchase", since,
                                             game_minutes),
        "business_investment_ncr": investment,
        "government_revenue_ncr": gov_revenue,
        "trade_volume_ncr": exports,
        "poverty_line_ncr": line,
        "poverty_rate": round(poor / len(incomes), 4) if incomes
        else 0.0,
        "wealth_gini": _gini(balances),
        "wealth_p10_ncr": balances[len(balances) // 10]
        if balances else 0,
        "wealth_p50_ncr": balances[len(balances) // 2]
        if balances else 0,
        "wealth_p90_ncr": balances[9 * len(balances) // 10]
        if balances else 0,
        "businesses_active": store.row(
            "SELECT COUNT(*) AS n FROM businesses WHERE"
            " closed_at_game_minutes IS NULL")["n"],
        "businesses_closed_total": store.row(
            "SELECT COUNT(*) AS n FROM businesses WHERE"
            " closed_at_game_minutes IS NOT NULL")["n"],
        "bank": None,
    }
    from . import banking as banking_mod
    national["bank"] = banking_mod.bank_stats(store)
    per_city = {}
    for spec in data.city_specs():
        cid = spec["city_id"]
        city_labour = labour["by_city"].get(
            cid, {"labour_force": 0, "employed": 0,
                  "unemployment_rate": 0.0})
        exp = store.row(
            "SELECT COALESCE(SUM(amount_ncr),0) AS s FROM trade_flows"
            " WHERE month_index = ? AND from_city_id = ?",
            (month_index, cid))["s"]
        imp = store.row(
            "SELECT COALESCE(SUM(amount_ncr),0) AS s FROM trade_flows"
            " WHERE month_index = ? AND to_city_id = ?",
            (month_index, cid))["s"]
        city_gdp = store.row(
            "SELECT COALESCE(SUM(bm.profit_ncr + bm.tax_ncr),0) AS s"
            " FROM business_monthly bm JOIN businesses b"
            " ON b.business_id = bm.business_id JOIN properties p"
            " ON p.property_id = b.property_id WHERE bm.month_index"
            " = ? AND p.district_id IN (SELECT zone_id FROM"
            " city_zones WHERE city_id = ?)",
            (month_index, cid))["s"]
        per_city[cid] = {
            "population": cities_mod.city_population(store, data, cid),
            "labour_force": city_labour["labour_force"],
            "employed": city_labour["employed"],
            "unemployment_rate": city_labour["unemployment_rate"],
            "business_surplus_ncr": city_gdp,
            "trade_exports_ncr": exp, "trade_imports_ncr": imp,
            "trade_balance_ncr": exp - imp,
            "price_index": market_mod.price_index(store, data, cid),
        }
    return {"national": national, "per_city": per_city}


def snapshot_month(store, data, month_index, game_minutes):
    """Compute and persist the month's indicators (national +
    per-city scopes). Returns the computed dict."""
    out = compute_indicators(store, data, month_index, game_minutes)
    store.execute(
        "INSERT OR REPLACE INTO economic_indicators (scope,"
        " month_index, metrics, game_minutes) VALUES ('national',"
        " ?, ?, ?)",
        (month_index, json.dumps(out["national"], sort_keys=True),
         game_minutes))
    for cid, metrics in out["per_city"].items():
        store.execute(
            "INSERT OR REPLACE INTO economic_indicators (scope,"
            " month_index, metrics, game_minutes) VALUES (?, ?, ?, ?)",
            (cid, month_index, json.dumps(metrics, sort_keys=True),
             game_minutes))
    return out


def latest(store, scope="national"):
    row = store.row("SELECT * FROM economic_indicators WHERE scope"
                    " = ? ORDER BY month_index DESC LIMIT 1",
                    (scope,))
    if row is None:
        return None
    return {"scope": scope, "month_index": row["month_index"],
            "metrics": json.loads(row["metrics"])}
