"""Session 03 Unit 09 — City Services Engine.

Municipal services with a real budget. The budget's revenue side
is MEASURED, never modelled: the month's ledger rows into
SYS-CITY — income/business tax (reason 'tax'), rent (reason
'rent'), construction funding and the rest — are summed from the
ledger itself. The one tax the earlier sessions had designed but
never collected, GDD-03 §4.2's property tax (0.5% of value per
year), is assessed here monthly at 1/12 of the annual rate, and
only on properties with an owner_character_id (genesis District 1
stock is tenanted and ownerless — the city is effectively its
landlord and already receives the rent; taxing an absent owner
would be inventing a payer).

Spending is prioritised and capped by SYS-CITY's actual balance:
road maintenance first (segments decay monthly by class wear +
storm wear; the worst segments are restored toward condition 85
while funds last), then street cleaning, waste, parks and
administration at per-resident SIM MODEL rates (labelled — no
service price list exists in the design data). Service LEVELS are
measured qualities (road condition restored, infrastructure
status, police/doctor coverage, park condition), so an unfunded
month visibly degrades the city: that is services responding to
actual conditions.
"""
from . import buildings as buildings_mod
from . import cities as cities_mod

SERVICES = ("public_administration", "road_maintenance",
            "street_cleaning", "waste_management", "parks",
            "water_management", "public_safety", "emergency_services")

# SIM MODEL constants (see docstring).
ROAD_REPAIR_NCR_PER_M_POINT = 2
ROAD_TARGET_CONDITION = 85
ROAD_WEAR = {"arterial": 1.1, "collector": 0.9, "local": 0.6,
             "lane": 0.3, "promenade": 0.3}
STORM_WEAR_EXTRA = 0.8
CLEANING_NCR_PER_RESIDENT = 12
WASTE_NCR_PER_RESIDENT = 8
ADMIN_NCR_PER_RESIDENT = 6
PARKS_BASE_NCR = 3000


def _ledger_in(store, reason, since, until, to_id="SYS-CITY"):
    row = store.row(
        "SELECT COALESCE(SUM(amount),0) AS s FROM economy_ledger"
        " WHERE to_character_id = ? AND reason_code = ?"
        " AND game_minutes > ? AND game_minutes <= ?",
        (to_id, reason, since, until))
    return row["s"]


def _spend(store, amount, note, game_minutes):
    """SYS-CITY pays the market for a municipal service. Partial
    when the city cannot cover it — the unpaid part simply does
    not happen (services degrade), it is never minted."""
    if amount <= 0:
        return 0
    paid = min(amount, max(0, store.balance("SYS-CITY")))
    if paid > 0:
        store.transfer("SYS-CITY", "SYS-MARKET", paid,
                       "municipal_service", game_minutes, note=note)
    return paid


def _assess_property_tax(store, data, game_minutes):
    """GDD-03 §4.2: 0.5% of value per year, monthly 1/12, owners
    only. Returns {city_id: collected}."""
    rate = data.prices["tax"]["property_annual_percent_of_value"] \
        / 100 / 12
    collected = {}
    for p in store.rows("SELECT * FROM properties WHERE"
                        " owner_character_id IS NOT NULL AND"
                        " market_value > 0"):
        due = round(p["market_value"] * rate)
        if due <= 0:
            continue
        owner = p["owner_character_id"]
        paid = min(due, max(0, store.balance(owner)))
        if paid > 0:
            store.transfer(owner, "SYS-CITY", paid, "tax",
                           game_minutes, note="property tax",
                           related_property_id=p["property_id"])
            city = cities_mod.city_of_zone(data, p["district_id"]) \
                or cities_mod.RUPSHA
            collected[city] = collected.get(city, 0) + paid
    return collected


def _road_pass(store, data, city_id, storm_days, game_minutes):
    """Decay then maintain one city's segments. Returns
    (spend, avg_condition_after)."""
    for s in store.rows("SELECT * FROM road_segments WHERE city_id"
                        " = ?", (city_id,)):
        wear = ROAD_WEAR.get(s["road_class"], 0.5) \
            + (STORM_WEAR_EXTRA if storm_days else 0)
        store.execute("UPDATE road_segments SET condition = ?,"
                      " updated_at_game_minutes = ? WHERE"
                      " segment_id = ?",
                      (round(max(5.0, s["condition"] - wear), 2),
                       game_minutes, s["segment_id"]))
    spend = 0
    worst = store.rows("SELECT * FROM road_segments WHERE city_id ="
                       " ? AND condition < ? ORDER BY condition ASC,"
                       " segment_id ASC",
                       (city_id, ROAD_TARGET_CONDITION))
    for s in worst:
        deficit = ROAD_TARGET_CONDITION - s["condition"]
        cost = int(s["length_m"] * deficit
                   * ROAD_REPAIR_NCR_PER_M_POINT)
        paid = _spend(store, cost, f"road maintenance {s['segment_id']}",
                      game_minutes)
        if paid <= 0:
            break
        restored = paid / (s["length_m"]
                           * ROAD_REPAIR_NCR_PER_M_POINT) \
            if s["length_m"] else 0
        store.execute("UPDATE road_segments SET condition = ? WHERE"
                      " segment_id = ?",
                      (round(min(98.0, s["condition"] + restored), 2),
                       s["segment_id"]))
        spend += paid
        if paid < cost:
            break
    row = store.row("SELECT AVG(condition) AS c FROM road_segments"
                    " WHERE city_id = ?", (city_id,))
    return spend, round(row["c"], 1) if row and row["c"] else 0.0


def _service_levels(store, data, city_id, coverage, road_avg):
    """Measured service quality 0..100 per service."""
    pop = max(1, cities_mod.city_population(store, data, city_id))
    infra = store.rows("SELECT network, AVG(load_ratio) AS l FROM"
                       " infrastructure_state WHERE city_id = ?"
                       " GROUP BY network", (city_id,))
    loads = {r["network"]: r["l"] or 0 for r in infra}

    def infra_level(network):
        return round(max(0.0, 100 - loads.get(network, 0) * 55), 1)

    police = doctors = 0
    for r in store.rows("SELECT profession_id, COUNT(*) AS n FROM"
                        " employments WHERE ended_at_game_minutes"
                        " IS NULL GROUP BY profession_id"):
        if r["profession_id"] == "police_officer":
            police = r["n"]
        elif r["profession_id"] == "doctor":
            doctors = r["n"]
    if city_id == cities_mod.RUPSHA:
        safety = min(100.0, police / (pop / 100) * 20)
        emergency = min(100.0, 40 + doctors * 4)
    else:  # regional provision from Rupsha's services (documented)
        safety = min(100.0, police / (240 / 100) * 20) * 0.5
        emergency = 30.0 if store.row(
            "SELECT 1 FROM building_state WHERE building_id ="
            " 'b_c2_civic_clinic'") else 10.0
    park = store.row("SELECT condition FROM building_state WHERE"
                     " building_id = 'b_d1_park_land'")
    parks = round(park["condition"], 1) if park and city_id \
        == cities_mod.RUPSHA else 0.0
    office = store.row("SELECT condition FROM building_state WHERE"
                       " building_id IN ('b_d1_civic_city_office',"
                       " 'b_c2_civic_office') AND city_id = ?",
                       (city_id,))
    admin = round(office["condition"], 1) if office else 0.0
    return {
        "public_administration": admin,
        "road_maintenance": road_avg,
        "street_cleaning": round(coverage.get("street_cleaning", 0)
                                 * 100, 1),
        "waste_management": infra_level("solid_waste"),
        "parks": parks,
        "water_management": infra_level("water"),
        "public_safety": round(safety, 1),
        "emergency_services": round(emergency, 1),
    }


def monthly_pass(store, data, month_index, game_minutes, storm_days=0):
    """The municipal month: assess property tax, measure revenue,
    decay + maintain roads, fund services, persist budgets and
    service levels for both cities."""
    if not cities_mod.is_setup(store):
        return None
    since = game_minutes - 30 * 1440
    property_tax = _assess_property_tax(store, data, game_minutes)
    # Revenue attribution: taxes and construction funding arise
    # from District 1's economy (all professions anchor there);
    # rent is split by each city's occupied-unit share — an
    # attribution model over measured totals, stated in the report.
    tax_rev = _ledger_in(store, "tax", since, game_minutes) \
        - sum(property_tax.values())
    rent_total = _ledger_in(store, "rent", since, game_minutes)
    other_rev = store.row(
        "SELECT COALESCE(SUM(amount),0) AS s FROM economy_ledger"
        " WHERE reason_code = 'construction_funding'"
        " AND game_minutes > ? AND game_minutes <= ?",
        (since, game_minutes))["s"]
    from . import distribution as distribution_mod
    occ = {cid: distribution_mod.housing_pressure(store, data, cid)
           ["occupied_units"]
           for cid in (cities_mod.RUPSHA, cities_mod.SHIBNAGAR)}
    occ_total = sum(occ.values()) or 1
    budgets = {}
    for spec in data.city_specs():
        cid = spec["city_id"]
        pop = cities_mod.city_population(store, data, cid)
        road_spend, road_avg = _road_pass(store, data, cid,
                                          storm_days, game_minutes)
        coverage, spends = {}, {"road_maintenance": road_spend}
        for service, rate in (("street_cleaning",
                               CLEANING_NCR_PER_RESIDENT),
                              ("waste_management",
                               WASTE_NCR_PER_RESIDENT),
                              ("public_administration",
                               ADMIN_NCR_PER_RESIDENT)):
            need = pop * rate
            paid = _spend(store, need, f"{service} {cid}",
                          game_minutes)
            spends[service] = paid
            coverage[service] = (paid / need) if need else 1.0
        if cid == cities_mod.RUPSHA:
            park = store.row("SELECT condition FROM building_state"
                             " WHERE building_id = 'b_d1_park_land'")
            deficit = max(0.0, 95 - (park["condition"] if park
                                     else 95))
            paid = _spend(store, int(PARKS_BASE_NCR + deficit * 50),
                          "parks maintenance", game_minutes)
            if paid > 0 and park:
                buildings_mod.apply_maintenance(
                    store, "b_d1_park_land",
                    min(deficit, paid / 50), game_minutes)
            spends["parks"] = paid
        levels = _service_levels(store, data, cid, coverage,
                                 road_avg)
        for service, level in levels.items():
            store.execute(
                "INSERT OR REPLACE INTO municipal_services (city_id,"
                " service, level, spend_ncr, month_index,"
                " updated_at_game_minutes) VALUES (?, ?, ?, ?, ?, ?)",
                (cid, service, level, spends.get(service, 0),
                 month_index, game_minutes))
        revenue_rent = int(rent_total * occ[cid] / occ_total)
        revenue_tax = (tax_rev if cid == cities_mod.RUPSHA else 0) \
            + property_tax.get(cid, 0)
        revenue_other = other_rev if cid == cities_mod.RUPSHA else 0
        total_spend = sum(spends.values())
        store.execute(
            "INSERT OR REPLACE INTO municipal_budgets (city_id,"
            " month_index, revenue_tax_ncr, revenue_rent_ncr,"
            " revenue_other_ncr, property_tax_ncr, spend_services_ncr,"
            " spend_construction_ncr, city_balance_after,"
            " game_minutes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (cid, month_index, revenue_tax, revenue_rent,
             revenue_other, property_tax.get(cid, 0), total_spend, 0,
             store.balance("SYS-CITY"), game_minutes))
        budgets[cid] = {"revenue_tax": revenue_tax,
                        "revenue_rent": revenue_rent,
                        "spend_services": total_spend,
                        "levels": levels}
    return budgets
