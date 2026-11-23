"""Session 04 Unit 04 — Businesses.

A business is a real economic entity, not a label on its owner:

- identity (business_id), owner (a character — a person, or
  SYS-MARKET for the genesis system-founded firms, labelled as
  such in business_events), registration (founded_at + a
  business_events 'registered' row), location (a property row in
  a REAL commercial building unit of one of the two cities —
  created by setup from the canonical buildings data, the same
  stock machinery Session 03 built for homes);
- capital: an account of its own on the ledger (businesses.
  balance_cached, reconciled by Store.ledger_sum_check). Genesis
  capital and decision-founded capital are recorded transfers
  with reason 'business_capital' — no business starts with
  unrecorded money;
- employees: employment rows carrying employer_business_id
  (Unit 03's labour market hires them; genesis professions keep
  their Session 01 employer of record);
- operating result: one business_monthly row per month. For
  owner-run professions the figures are the settlement's own
  P&L (economy_sim.business_pnl — the same function, so the two
  can never drift); for system-founded firms they are summed
  from the month's operating ledger rows tagged with the
  business;
- status: active -> distressed -> closed. Distress is measured
  (balance below the month's obligations, or a failed payment);
  closure after the configured number of consecutive distressed
  months ends its employments and liquidates its inventory back
  to the market aggregate — all recorded, nothing narrated.

Genesis seeding is transparent: businesses founded by the system
at economy setup (factories, godowns, restaurants, farms, extra
shops in real commercial units no character owns yet) are owned
by SYS-MARKET and carry a 'system_foundation' event. Character
shop_owner / business_owner professions get their own firms,
located in their profession's zone.
"""
import json

from . import cities as cities_mod

# Genesis capital by category (NCr). SIM MODEL figures — genesis
# seed capital has no design-data price, like population seed
# balances in Session 01; labelled here and in the report.
GENESIS_CAPITAL = {
    "agriculture": 20000, "fishing": 15000, "retail": 25000,
    "food_service": 40000, "food_processing": 50000,
    "manufacturing": 120000, "distribution": 60000,
    "professional_services": 80000,
}
OWNER_CAPITAL_BY_TIER = {1: 30000, 2: 80000, 3: 150000, 4: 150000,
                         5: 150000}

# Opening inventory by category (units). SIM MODEL seed stock —
# recorded as genesis_stock movements, never sold into existence.
GENESIS_STOCK = {
    "agriculture": {"agricultural_produce": 30},
    "fishing": {"fish": 10},
    "food_processing": {"agricultural_produce": 30},
    "manufacturing": {"manufactured_goods": 10},
    "retail": {"food_basket": 6, "fish": 4, "clothing_set": 2},
    "food_service": {"food_basket": 6},
}
OWNER_CATEGORY = {"shop_owner": "retail",
                  "business_owner": "professional_services"}
OWNER_ZONE = {"shop_owner": "d1_market",
              "business_owner": "d1_uptown"}
OPERATING_REASONS_IN = ("business_sale", "retail_takings",
                        "trade_sale")
OPERATING_REASONS_OUT = ("inventory_purchase", "production_cost",
                         "shipping", "commercial_rent", "wage",
                         "business_expense")


def is_setup(store):
    w = store.world()
    return bool(w and w.get("economy_setup"))


def log_event(store, business_id, event_type, details, game_minutes):
    eid = store.next_id("BE", "business_events", "event_id")
    store.insert("business_events", event_id=eid,
                 business_id=business_id, event_type=event_type,
                 details=json.dumps(details, sort_keys=True),
                 game_minutes=game_minutes)
    return eid


def category_for_building(building):
    bid, btype = building["id"], building["property_type"]
    if "farmland" in bid:
        return "agriculture"
    if "workshop" in bid:
        return "manufacturing"
    if "fish" in bid:
        return "fishing"
    if "restaurant" in bid:
        return "food_service"
    if btype == "factory":
        return "food_processing" if ("godown" in bid
                                     or "warehouse" in bid) \
            else "manufacturing"
    if btype == "office":
        return "professional_services"
    return "retail"


def commercial_units(data):
    """Leasable commercial units across both cities, from the
    canonical buildings data: shops, offices, factories with a
    rent line, plus Shibnagar's farmland. Civic institutions
    (school, clinic, bank, police, college — rent None) are
    employers, not business premises, and are excluded."""
    units = []
    for spec in data.city_specs():
        for b in spec["properties"]:
            if "part_of" in b:
                continue
            rent = b.get("rent_monthly_ncr_per_unit")
            farmland = "farmland" in b["id"]
            if b["property_type"] not in ("shop", "office", "factory") \
                    and not farmland:
                continue
            if rent is None and not farmland:
                continue
            for i in range(b.get("units", 1)):
                units.append({
                    "building_id": b["id"], "building_name": b["name"],
                    "unit_index": i, "rent": rent or 0,
                    "tier": b["tier"], "zone_id": b["zone_id"],
                    "property_type": b["property_type"],
                    "category": category_for_building(b),
                    "city_id": spec["city_id"],
                })
    units.sort(key=lambda u: (u["building_id"], u["unit_index"]))
    return units


def setup_economy(store, data, rng, game_minutes=480):
    """The Session 04 world bootstrap (idempotent): commercial
    property stock, genesis businesses, the bank's capital and
    accounts, genesis market prices. Called by the engine after
    population + city setup; hand-built test worlds never call it
    and every Session 04 pass no-ops for them."""
    if is_setup(store):
        return {"already_setup": True}
    units = commercial_units(data)
    property_by_unit = {}
    for u in units:
        pid = store.next_id("PR", "properties", "property_id")
        store.insert(
            "properties", property_id=pid,
            property_type=u["property_type"], district_id=u["zone_id"],
            address_label=f"{u['building_name']} #{u['unit_index'] + 1}",
            tier=u["tier"], status="commercial",
            market_value=(u["rent"] * 120) if u["rent"] else 0,
            building_ref=u["building_id"], unit_index=u["unit_index"])
        property_by_unit[(u["building_id"], u["unit_index"])] = pid
    free_units = list(units)

    def take_unit(zone_id=None, category=None):
        for i, u in enumerate(free_units):
            if zone_id and u["zone_id"] != zone_id:
                continue
            if category and u["category"] != category:
                continue
            return free_units.pop(i)
        return free_units.pop(0) if free_units and not zone_id \
            and not category else None

    counts = {"owner_businesses": 0, "system_businesses": 0}
    # Character-owned firms for the two business professions.
    owners = store.rows(
        "SELECT e.character_id, e.profession_id, e.tier,"
        " c.display_name, c.last_name FROM employments e"
        " JOIN characters c ON c.character_id = e.character_id"
        " WHERE e.ended_at_game_minutes IS NULL"
        " AND e.profession_id IN ('shop_owner', 'business_owner')"
        " ORDER BY e.character_id")
    for o in owners:
        category = OWNER_CATEGORY[o["profession_id"]]
        unit = take_unit(zone_id=OWNER_ZONE[o["profession_id"]],
                         category=category) or take_unit(
                             category=category)
        bid = register_business(
            store, name=f"{o['last_name']} "
                        f"{category.replace('_', ' ').title()}",
            business_type=o["profession_id"], category=category,
            owner_character_id=o["character_id"],
            property_id=property_by_unit[
                (unit["building_id"], unit["unit_index"])] if unit
            else None,
            game_minutes=game_minutes, founded_by="owner_profession",
            data=data)
        capital = OWNER_CAPITAL_BY_TIER.get(o["tier"], 30000)
        store.transfer("SYS-MARKET", None, capital, "business_capital",
                       game_minutes, note="genesis capital (seed)",
                       related_business_id=bid,
                       transfer_key=f"genesis-capital:{bid}",
                       event_ref="economy_setup", to_business_id=bid)
        counts["owner_businesses"] += 1
    # System-founded firms in the remaining commercial units —
    # seeded in proportion to each city's CURRENT households
    # (SIM MODEL: at most 1.5 firms per household, at least 6 per
    # city), producer categories first so every city's supply
    # chain exists from day one. Units beyond the cap stay
    # vacant: a town designed for ninety people but currently
    # holding two households does not conjure eleven solvent
    # shops, and a firm seeded into a demand vacuum would only
    # record a scripted bankruptcy.
    from . import cities as cities_mod
    producer_first = {"agriculture": 0, "fishing": 1,
                      "food_processing": 2, "manufacturing": 3}
    units_by_city = {}
    for u in free_units:
        city = cities_mod.city_of_zone(data, u["zone_id"]) \
            or cities_mod.RUPSHA
        units_by_city.setdefault(city, []).append(u)
    seeded_units = []
    for city, city_units in units_by_city.items():
        households = store.row(
            "SELECT COUNT(*) AS n FROM households h JOIN city_zones"
            " cz ON cz.zone_id = h.district_id WHERE cz.city_id = ?"
            " AND h.dissolved_at_game_minutes IS NULL",
            (city,))["n"]
        cap = max(6, -(-households * 3 // 2))
        ordered = sorted(
            city_units,
            key=lambda u: (producer_first.get(u["category"], 9),
                           u["building_id"], u["unit_index"]))
        seeded_units.extend(ordered[:cap])
    for u in seeded_units:
        bid = register_business(
            store, name=f"{u['building_name']} #{u['unit_index'] + 1}",
            business_type="system_firm", category=u["category"],
            owner_character_id="SYS-MARKET",
            property_id=property_by_unit[(u["building_id"],
                                          u["unit_index"])],
            game_minutes=game_minutes, founded_by="system", data=data)
        capital = GENESIS_CAPITAL.get(u["category"], 25000)
        store.transfer("SYS-MARKET", None, capital, "business_capital",
                       game_minutes,
                       note="genesis capital (system-founded)",
                       related_business_id=bid,
                       transfer_key=f"genesis-capital:{bid}",
                       event_ref="economy_setup", to_business_id=bid)
        counts["system_businesses"] += 1
    free_units.clear()
    from . import market as market_mod
    # Opening stock (SIM MODEL seed inventory, like seed money):
    # shelves and storehouses are not empty on day one — without
    # it the first month is a structural famine while supply
    # chains warm up. Recorded as genesis_stock movements; no
    # money moves (the stock is the seed, exactly as balances are).
    for b in active_businesses(store):
        for good_id, qty in GENESIS_STOCK.get(b["category"],
                                              {}).items():
            market_mod.adjust_inventory(
                store, b["business_id"], good_id, qty,
                "genesis_stock", game_minutes,
                details={"seed": True})
    # The bank: capitalised from the market aggregate (GDD-03
    # §4.3: it lends only what it holds), accounts for every adult.
    from . import banking as banking_mod
    counts["bank"] = banking_mod.setup_bank(store, data, game_minutes)
    # Genesis market prices: every good at its base price, per city.
    counts["prices"] = market_mod.setup_prices(store, data)
    store.set_world(economy_setup=1)
    store.commit()
    return counts


def register_business(store, *, name, business_type, category,
                      owner_character_id, property_id, game_minutes,
                      founded_by, data=None):
    bid = store.next_id("BZ", "businesses", "business_id")
    store.insert("businesses", business_id=bid, name=name,
                 business_type=business_type, category=category,
                 owner_character_id=owner_character_id,
                 property_id=property_id, balance_cached=0,
                 status="active",
                 founded_at_game_minutes=game_minutes)
    # Queue 17 Unit DJ: the business licence (data/documents.json)
    # is issued at founding — but only to a real-character owner.
    # A system-founded firm is owned by SYS-MARKET, which is not a
    # character and holds no inventory rows; its licence waits for
    # a character owner (a purchase/transfer event, not this unit).
    # Callers that pass no data (hand-built test worlds) seed
    # nothing, as before.
    if data is not None and owner_character_id != "SYS-MARKET":
        from . import lost_items as lost_items_mod
        lost_items_mod.seed_document_row(
            store, data, owner_character_id, "business_licence",
            game_minutes, {"business_id": bid})
    log_event(store, bid, "registered",
              {"founded_by": founded_by, "category": category,
               "property_id": property_id}, game_minutes)
    if founded_by == "system":
        log_event(store, bid, "system_foundation",
                  {"note": "genesis firm founded by the system in a"
                           " real commercial unit; owned by"
                           " SYS-MARKET until bought"},
                  game_minutes)
    return bid


def active_businesses(store):
    return store.rows("SELECT * FROM businesses WHERE"
                      " closed_at_game_minutes IS NULL"
                      " ORDER BY business_id")


def employees_of(store, business_id):
    return store.rows("SELECT * FROM employments WHERE"
                      " employer_business_id = ?"
                      " AND ended_at_game_minutes IS NULL"
                      " ORDER BY character_id", (business_id,))


def wage_bill(store, business_id):
    return sum(e["wage_per_month"]
               for e in employees_of(store, business_id))


def business_city(store, data, business):
    if business["property_id"]:
        prop = store.row("SELECT district_id FROM properties"
                         " WHERE property_id = ?",
                         (business["property_id"],))
        if prop:
            return cities_mod.city_of_zone(data, prop["district_id"])
    owner = store.row("SELECT household_id FROM characters"
                      " WHERE character_id = ?",
                      (business["owner_character_id"],))
    if owner and owner["household_id"]:
        h = store.row("SELECT district_id FROM households"
                      " WHERE household_id = ?",
                      (owner["household_id"],))
        if h:
            return cities_mod.city_of_zone(data, h["district_id"])
    return cities_mod.RUPSHA


def inventory_value(store, data, business_id, city_id):
    from . import market as market_mod
    total = 0
    for inv in store.rows("SELECT good_id, quantity FROM"
                          " business_inventory WHERE business_id = ?"
                          " AND quantity > 0", (business_id,)):
        total += inv["quantity"] * market_mod.price_of(
            store, data, city_id, inv["good_id"])
    return round(total)


def net_worth(store, data, business):
    """The documented valuation model (Unit 09): cash on the
    business account + inventory at current market prices.
    Premises are rented, never owned, so they contribute no asset
    value; goodwill is not modelled and not claimed."""
    city = business_city(store, data, business)
    return store.business_balance(business["business_id"]) \
        + inventory_value(store, data, business["business_id"], city)


def record_monthly_pnl(store, data, month_index, game_minutes):
    """One business_monthly row per active business. Owner-run
    professions report the settlement's own P&L (economy_sim's
    business_pnl, the identical function); system firms report
    their operating ledger sums for the month window."""
    since = game_minutes - 30 * 1440
    biz_rate = data.prices["tax"]["business_monthly_percent_of_profit"]
    for b in active_businesses(store):
        bid = b["business_id"]
        emp = None
        if b["owner_character_id"] not in ("SYS-MARKET",):
            emp = store.row(
                "SELECT * FROM employments WHERE character_id = ?"
                " AND profession_id IN ('shop_owner', 'business_owner')"
                " AND ended_at_game_minutes IS NULL",
                (b["owner_character_id"],))
        if emp is not None:
            pnl = data.econ.business_pnl(
                data.prices, emp["profession_id"],
                data.business_tier_key(emp["tier"]))
            revenue = pnl["revenue"]
            costs = pnl["revenue"] - pnl["profit"]
            tax = round(pnl["profit"] * biz_rate / 100) \
                if pnl["profit"] > 0 else 0
            profit = pnl["profit"] - tax
        else:
            inn = store.row(
                "SELECT COALESCE(SUM(amount),0) AS s FROM economy_ledger"
                " WHERE to_business_id = ? AND reason_code IN"
                f" ({','.join('?' for _ in OPERATING_REASONS_IN)})"
                " AND game_minutes > ? AND game_minutes <= ?",
                (bid, *OPERATING_REASONS_IN, since, game_minutes))["s"]
            out = store.row(
                "SELECT COALESCE(SUM(amount),0) AS s FROM economy_ledger"
                " WHERE from_business_id = ? AND reason_code IN"
                f" ({','.join('?' for _ in OPERATING_REASONS_OUT)})"
                " AND game_minutes > ? AND game_minutes <= ?",
                (bid, *OPERATING_REASONS_OUT, since, game_minutes))["s"]
            revenue, costs, tax = inn, out, 0
            profit = revenue - costs
        store.execute(
            "INSERT OR REPLACE INTO business_monthly (business_id,"
            " month_index, revenue_ncr, costs_ncr, tax_ncr,"
            " profit_ncr, employees, status_after) VALUES"
            " (?, ?, ?, ?, ?, ?, ?, ?)",
            (bid, month_index, revenue, costs, tax, profit,
             len(employees_of(store, bid)), b["status"]))
    return True


def pay_commercial_rent(store, data, month_index, game_minutes):
    """System-founded firms pay their unit's rent to SYS-CITY
    (reason 'commercial_rent'). Owner-run firms' premises rent is
    already inside the settlement P&L (business_model) and is not
    charged twice. A firm that cannot pay records distress."""
    distressed = []
    for b in active_businesses(store):
        if b["owner_character_id"] != "SYS-MARKET":
            continue
        if not b["property_id"]:
            continue
        prop = store.row("SELECT * FROM properties WHERE property_id"
                         " = ?", (b["property_id"],))
        if not prop or not prop["building_ref"]:
            continue
        building = data.all_buildings().get(prop["building_ref"])
        rent = building.get("rent_monthly_ncr_per_unit") if building \
            else 0
        if not rent:
            continue
        key = f"rent:{b['business_id']}:{month_index}"
        if store.business_balance(b["business_id"]) >= rent:
            store.transfer(None, "SYS-CITY", rent, "commercial_rent",
                           game_minutes, note="commercial unit rent",
                           related_business_id=b["business_id"],
                           transfer_key=key,
                           event_ref=f"month:{month_index}",
                           from_business_id=b["business_id"])
        else:
            distressed.append(b["business_id"])
            log_event(store, b["business_id"], "rent_unpaid",
                      {"rent_ncr": rent, "month_index": month_index},
                      game_minutes)
    return distressed


def evaluate_distress(store, data, month_index, game_minutes):
    """Distress = the firm's balance cannot cover next month's
    obligations (commercial rent where it pays it + its wage
    bill). Consecutive distressed months at the configured count
    close the firm: employments end, inventory liquidates to the
    market aggregate, the closure is recorded with its cause."""
    cfg = data.economy_config["business"]
    limit = cfg["distress_months_to_closure"]
    closed = []
    for b in active_businesses(store):
        bid = b["business_id"]
        obligations = wage_bill(store, bid)
        if b["owner_character_id"] == "SYS-MARKET" and b["property_id"]:
            prop = store.row("SELECT building_ref FROM properties"
                             " WHERE property_id = ?",
                             (b["property_id"],))
            building = data.all_buildings().get(
                prop["building_ref"]) if prop else None
            if building:
                obligations += building.get(
                    "rent_monthly_ncr_per_unit") or 0
        balance = store.business_balance(bid)
        if balance < obligations:
            months = _consecutive_distress(store, bid, month_index)
            store.execute("UPDATE businesses SET status = 'distressed'"
                          " WHERE business_id = ?", (bid,))
            log_event(store, bid, "distress",
                      {"month_index": month_index,
                       "balance_ncr": balance,
                       "obligations_ncr": obligations,
                       "consecutive_months": months}, game_minutes)
            if months >= limit:
                _close_business(store, b, month_index, game_minutes,
                                "insolvency")
                closed.append(bid)
        elif b["status"] == "distressed":
            store.execute("UPDATE businesses SET status = 'active'"
                          " WHERE business_id = ?", (bid,))
            log_event(store, bid, "recovered",
                      {"month_index": month_index}, game_minutes)
    return closed


def _consecutive_distress(store, business_id, month_index):
    """Consecutive distressed months ending now, read off the
    business's own event trail: a distress event from the month
    immediately before continues the count; anything older (a
    recovery intervened, or months passed healthy) restarts it."""
    row = store.row(
        "SELECT details FROM business_events WHERE business_id = ?"
        " AND event_type = 'distress' ORDER BY game_minutes DESC"
        " LIMIT 1", (business_id,))
    if not row:
        return 1
    d = json.loads(row["details"])
    if d.get("month_index") == month_index - 1:
        return d.get("consecutive_months", 1) + 1
    if d.get("month_index") == month_index:
        return d.get("consecutive_months", 1)
    return 1


def _close_business(store, business, month_index, game_minutes, cause):
    bid = business["business_id"]
    laid_off = []
    for e in employees_of(store, bid):
        store.execute("UPDATE employments SET ended_at_game_minutes"
                      " = ? WHERE employment_id = ?",
                      (game_minutes, e["employment_id"]))
        laid_off.append(e["character_id"])
        from . import memory as memory_mod
        memory_mod.log_life_event(
            store, e["character_id"], "job_loss", game_minutes,
            details={"business_id": bid, "cause": cause})
        from . import emotions as emotions_mod
        emotions_mod.apply_event(store, e["character_id"], "job_loss")
    for inv in store.rows("SELECT good_id, quantity FROM"
                          " business_inventory WHERE business_id = ?"
                          " AND quantity > 0", (bid,)):
        from . import market as market_mod
        market_mod.adjust_inventory(
            store, bid, inv["good_id"], -inv["quantity"],
            "liquidation", game_minutes,
            details={"cause": cause})
    store.execute("UPDATE businesses SET status = 'closed',"
                  " closed_at_game_minutes = ? WHERE business_id = ?",
                  (game_minutes, bid))
    log_event(store, bid, "closed",
              {"cause": cause, "month_index": month_index,
               "laid_off": laid_off}, game_minutes)
    return laid_off
