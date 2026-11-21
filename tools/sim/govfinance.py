"""Session 04 Unit 10 — Government Finance.

The public accounts, summed from the ledger itself. Session 03's
municipal pass already collects the designed taxes (income and
business tax at settlement, property tax in services) and records
municipal_budgets; this unit EXTENDS that record into a full
monthly government-finance statement per city — it does not
re-collect anything:

- revenue by source, read off the month's ledger rows into
  SYS-CITY: income/business/property tax separated by the
  settlement's own note text (reason 'tax'), Session 04's new
  sales tax (reason 'sales_tax', a split of household purchases —
  engine._settle_month), trade tariffs (reason 'tariff'),
  commercial rent (reason 'commercial_rent'), residential rent
  and everything else;
- expenditure: the municipal_budgets row services.py already
  wrote for the month (services + construction), plus pensions
  (SYS-CITY's 'pension' outflows, attributed to the pensioner's
  city of residence);
- the treasury is ONE account (SYS-CITY serves both cities, as
  since Session 01), so city_balance_after is the same figure on
  both cities' rows and says so; public debt is the treasury's
  implicit overdraft — max(0, -balance) — reported as a measured
  position, not dressed up as issued bonds.

Attribution follows Session 03's documented model: wage/business
taxes arise from District 1's economy (all professions anchor
there) and are Rupsha's; rent splits by each city's occupied-unit
share; commercial rent follows the property's city; tariffs land
at the gateway city (Rupsha, whose bridge/ferry the trade
crosses). The tax rules themselves are configuration:
data/economy-config.json references the canonical prices.json
rates (never copies them) and adds the two SIM MODEL rates
(sales tax, tariff), labelled wherever they surface.
"""
from . import cities as cities_mod


def tax_rules_view(data):
    """The configured tax system, with each rate's source."""
    cfg = data.economy_config["tax_rules"]
    tax = data.prices["tax"]
    return {
        "income_tax": {"source": cfg["income_tax"]["source"],
                       "brackets": tax["income_monthly_brackets"]},
        "business_tax": {"source": cfg["business_tax"]["source"],
                         "percent_of_profit":
                         tax["business_monthly_percent_of_profit"]},
        "property_tax": {"source": cfg["property_tax"]["source"],
                         "annual_percent_of_value":
                         tax["property_annual_percent_of_value"]},
        "sales_tax": {"percent": cfg["sales_tax_percent"],
                      "basis": "SIM MODEL — no design-data rate;"
                               " split of household purchases",
                      "note": cfg["sales_tax_note"]},
        "import_tariff": {"percent": cfg["import_tariff_percent"],
                          "basis": "SIM MODEL — no design-data rate",
                          "note": cfg["import_tariff_note"]},
    }


def _ledger_in(store, reason, since, until, note_like=None):
    sql = ("SELECT COALESCE(SUM(amount),0) AS s FROM economy_ledger"
           " WHERE to_character_id = 'SYS-CITY' AND reason_code = ?"
           " AND game_minutes > ? AND game_minutes <= ?")
    params = [reason, since, until]
    if note_like:
        sql += " AND note LIKE ?"
        params.append(note_like)
    return store.row(sql, tuple(params))["s"]


def monthly_snapshot(store, data, month_index, game_minutes):
    """Write both cities' government_finance rows for the month.
    Runs after services.monthly_pass (budgets exist) in the
    engine's monthly city cadence."""
    if not cities_mod.is_setup(store):
        return None
    since = game_minutes - 30 * 1440
    income_tax = _ledger_in(store, "tax", since, game_minutes,
                            "%income tax%")
    business_tax = _ledger_in(store, "tax", since, game_minutes,
                              "%business tax%")
    property_tax = _ledger_in(store, "tax", since, game_minutes,
                              "%property tax%")
    sales_tax = _ledger_in(store, "sales_tax", since, game_minutes)
    tariff = _ledger_in(store, "tariff", since, game_minutes)
    rent_total = _ledger_in(store, "rent", since, game_minutes)
    other = store.row(
        "SELECT COALESCE(SUM(amount),0) AS s FROM economy_ledger"
        " WHERE to_character_id = 'SYS-CITY' AND reason_code NOT IN"
        " ('tax', 'sales_tax', 'tariff', 'rent')"
        " AND game_minutes > ? AND game_minutes <= ?",
        (since, game_minutes))["s"]
    from . import distribution as distribution_mod
    occ = {cid: distribution_mod.housing_pressure(store, data, cid)
           ["occupied_units"]
           for cid in (cities_mod.RUPSHA, cities_mod.SHIBNAGAR)}
    occ_total = sum(occ.values()) or 1
    pensions = {cities_mod.RUPSHA: 0, cities_mod.SHIBNAGAR: 0}
    for r in store.rows(
            "SELECT l.amount, h.district_id FROM economy_ledger l"
            " JOIN characters c ON c.character_id ="
            " l.to_character_id LEFT JOIN households h"
            " ON h.household_id = c.household_id WHERE"
            " l.from_character_id = 'SYS-CITY' AND l.reason_code ="
            " 'pension' AND l.game_minutes > ? AND l.game_minutes"
            " <= ?", (since, game_minutes)):
        city = cities_mod.city_of_zone(data, r["district_id"]) \
            if r["district_id"] else cities_mod.RUPSHA
        pensions[city or cities_mod.RUPSHA] += r["amount"]
    commercial_rent = {}
    for r in store.rows(
            "SELECT COALESCE(SUM(l.amount),0) AS s, p.district_id"
            " FROM economy_ledger l JOIN businesses b"
            " ON b.business_id = l.from_business_id"
            " JOIN properties p ON p.property_id = b.property_id"
            " WHERE l.reason_code = 'commercial_rent'"
            " AND l.game_minutes > ? AND l.game_minutes <= ?"
            " GROUP BY p.district_id", (since, game_minutes)):
        city = cities_mod.city_of_zone(data, r["district_id"])
        if city:
            commercial_rent[city] = commercial_rent.get(city, 0) \
                + r["s"]
    out = {}
    balance = store.balance("SYS-CITY")
    for spec in data.city_specs():
        cid = spec["city_id"]
        budget = store.row("SELECT * FROM municipal_budgets WHERE"
                           " city_id = ? AND month_index = ?",
                           (cid, month_index))
        is_rupsha = cid == cities_mod.RUPSHA
        row = {
            "revenue_income_tax_ncr": income_tax if is_rupsha else 0,
            "revenue_business_tax_ncr": business_tax if is_rupsha
            else 0,
            "revenue_property_tax_ncr": property_tax if is_rupsha
            else 0,
            "revenue_sales_tax_ncr": sales_tax if is_rupsha else 0,
            "revenue_tariff_ncr": tariff if is_rupsha else 0,
            "revenue_rent_ncr": int(rent_total * occ[cid]
                                    / occ_total),
            "revenue_other_ncr": (other if is_rupsha else 0)
            + commercial_rent.get(cid, 0),
            "spend_services_ncr": budget["spend_services_ncr"]
            if budget else 0,
            "spend_construction_ncr": budget[
                "spend_construction_ncr"] if budget else 0,
            "spend_pensions_ncr": pensions.get(cid, 0),
            "spend_other_ncr": 0,
            "city_balance_after": balance,
            "public_debt_ncr": max(0, -balance),
        }
        store.execute(
            "INSERT OR REPLACE INTO government_finance (city_id,"
            " month_index, revenue_income_tax_ncr,"
            " revenue_business_tax_ncr, revenue_property_tax_ncr,"
            " revenue_sales_tax_ncr, revenue_tariff_ncr,"
            " revenue_rent_ncr, revenue_other_ncr,"
            " spend_services_ncr, spend_construction_ncr,"
            " spend_pensions_ncr, spend_other_ncr,"
            " city_balance_after, public_debt_ncr, game_minutes)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (cid, month_index, row["revenue_income_tax_ncr"],
             row["revenue_business_tax_ncr"],
             row["revenue_property_tax_ncr"],
             row["revenue_sales_tax_ncr"],
             row["revenue_tariff_ncr"], row["revenue_rent_ncr"],
             row["revenue_other_ncr"], row["spend_services_ncr"],
             row["spend_construction_ncr"],
             row["spend_pensions_ncr"], row["spend_other_ncr"],
             balance, row["public_debt_ncr"], game_minutes))
        out[cid] = row
    return out
