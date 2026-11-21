"""Session 04 Units 05-07 + 14 — Production, Supply Chain,
Markets & Pricing, Household Consumption.

The goods layer. Money never moves here without the ledger, and
inventory never moves without an inventory_movements row: the two
audit trails mirror each other.

Unit 05 (Production): businesses with a recipe (data/
production-recipes.json) produce monthly. Output is capped by
inputs on hand, by paid materials (a ledger transfer from the
business account to SYS-MARKET at the recipe's labelled rate) and
by labour (employees + the working owner; system firms run a
nominal crew — SIM MODEL, labelled). Storm-heavy months halve
outdoor production (agriculture, fishing) — the same storm record
Session 03's construction uses.

Unit 06 (Supply chain): downstream businesses order from upstream
producers (then distributors) — same city first, then across the
Session 03 regional connection. Every order is a business-to-
business ledger transfer at the current market price plus a
shipping charge to SYS-MARKET priced by routed distance over the
Session 03 road graph (SIM MODEL per-unit-km rate). A supplier
with no stock sells nothing; a buyer with no capital buys
nothing; shortfalls are recorded, not smoothed over.

Unit 07 (Markets & pricing): market_prices move around the
goods catalogue's base prices ONLY on recorded signals — the
month's demand (household consumption + unmet demand + recipe
input demand) against the city's stocked supply. Every change
writes a price_history row carrying the signal values. No signal,
no change; there is no random walk anywhere in this module.

Unit 14 (Household consumption): after settlement, each
household's recorded food and clothing spend (household_finances,
the settlement's own lines) is allocated across the city's
retail stock: inventory physically leaves the shelves in
proportion to stock, system-founded retailers are paid their
takings from the SYS-MARKET clearing account against the goods
actually sold, and unmet demand is recorded per household.
Owner-run shops' takings are their settlement P&L (Session 01) —
they are not paid twice; their shelves still empty. Households
that ended the month in arrears consume less (the hardship
factor), and a household that cannot get food records a real
needs consequence. The money households pay is the settlement's
single payment — this pass allocates its goods side; it does not
charge anyone twice.
"""
import json
import math

from . import business as business_mod
from . import cities as cities_mod
from . import roads as roads_mod

# SIM MODEL constants (labelled; no design-data basis exists).
SYSTEM_CREW = 2
SHIPPING_NCR_PER_UNIT_KM = 1
FISH_SHARE_OF_FOOD_SPEND = 0.25
STORM_HALT_DAYS = 5
PRICE_FLOOR_RATIO = 0.5
PRICE_CAP_RATIO = 2.0
PRICE_STEP_UP = 0.05
PRICE_STEP_DOWN = 0.04
COVERAGE_LOW = 0.8
COVERAGE_HIGH = 1.5

# Which goods each category keeps in stock (its demand side).
STOCKING = {
    "retail": ("food_basket", "clothing_set", "household_supplies",
               "fish"),
    "food_service": ("food_basket", "fish", "agricultural_produce"),
    "food_processing": ("agricultural_produce",),
    "manufacturing": ("manufactured_goods",),
    "distribution": ("food_basket", "clothing_set",
                     "household_supplies", "fish",
                     "agricultural_produce", "manufactured_goods"),
}


def setup_prices(store, data):
    n = 0
    for spec in data.city_specs():
        for g in data.goods.values():
            store.execute(
                "INSERT OR IGNORE INTO market_prices (city_id,"
                " good_id, price_ncr, updated_month) VALUES (?, ?, ?, 0)",
                (spec["city_id"], g["id"], g["base_price_ncr"]))
            n += 1
    return n


def price_of(store, data, city_id, good_id):
    row = store.row("SELECT price_ncr FROM market_prices WHERE"
                    " city_id = ? AND good_id = ?",
                    (city_id, good_id))
    if row:
        return row["price_ncr"]
    return data.goods[good_id]["base_price_ncr"]


def inventory_of(store, business_id, good_id):
    row = store.row("SELECT quantity FROM business_inventory WHERE"
                    " business_id = ? AND good_id = ?",
                    (business_id, good_id))
    return row["quantity"] if row else 0.0


def adjust_inventory(store, business_id, good_id, delta, kind,
                     game_minutes, counterparty=None, amount_ncr=0,
                     details=None):
    """The only way inventory changes: a movement row + the new
    quantity, atomically. Raises on an impossible draw."""
    current = inventory_of(store, business_id, good_id)
    new = round(current + delta, 3)
    if new < -1e-9:
        raise ValueError(
            f"inventory draw below zero: {business_id} {good_id}"
            f" has {current}, draw {delta}")
    store.execute(
        "INSERT OR REPLACE INTO business_inventory (business_id,"
        " good_id, quantity) VALUES (?, ?, ?)",
        (business_id, good_id, max(0.0, new)))
    mid = store.next_id("IM", "inventory_movements", "movement_id")
    store.insert("inventory_movements", movement_id=mid,
                 business_id=business_id, good_id=good_id, delta=delta,
                 kind=kind, counterparty_business_id=counterparty,
                 amount_ncr=int(amount_ncr),
                 details=json.dumps(details or {}, sort_keys=True),
                 game_minutes=game_minutes)
    return max(0.0, new)


def city_supply(store, data, city_id, good_id):
    total = 0.0
    for b in business_mod.active_businesses(store):
        if business_mod.business_city(store, data, b) == city_id:
            total += inventory_of(store, b["business_id"], good_id)
    return total


def _recipes_for(data, category):
    return [r for r in data.recipes
            if r["business_category"] == category]


def _workers(store, business):
    n = len(business_mod.employees_of(store, business["business_id"]))
    if business["owner_character_id"] != "SYS-MARKET":
        n += 1  # the working owner
    else:
        n += SYSTEM_CREW
    return n


def _run_recipe(store, data, b, recipe, month_index, game_minutes,
                storm_days, key_suffix=""):
    """One business runs one recipe as far as its crew, inputs and
    capital allow. Returns units produced (0 when it cannot run)."""
    bid = b["business_id"]
    workers = _workers(store, b)
    runs = workers // max(1, recipe["crew_per_run"])
    if runs <= 0:
        return 0
    units = runs * recipe["units_per_run"]
    if not recipe["goods_in"]:
        # A primary producer with a full storehouse idles rather
        # than paying materials to pile up unsold output — the
        # stock cap is three runs' worth (SIM MODEL behaviour).
        if inventory_of(store, bid, recipe["output_good"]) \
                >= 3 * units:
            return 0
    if storm_days >= STORM_HALT_DAYS and b["category"] in (
            "agriculture", "fishing"):
        units = units // 2  # storm disruption, recorded below
    for good_id, per in recipe["goods_in"].items():
        have = inventory_of(store, bid, good_id)
        units = min(units, int(have / per))
    if units <= 0:
        return 0
    materials = units * recipe["materials_ncr_per_unit"]
    if materials > 0:
        if store.business_balance(bid) < materials:
            units = store.business_balance(bid) // max(
                1, recipe["materials_ncr_per_unit"])
            materials = units * recipe["materials_ncr_per_unit"]
        if units <= 0:
            return 0
        store.transfer(None, "SYS-MARKET", materials,
                       "production_cost", game_minutes,
                       note=f"{recipe['id']} materials",
                       related_business_id=bid,
                       transfer_key=f"prod:{bid}:{recipe['id']}:"
                                    f"{month_index}{key_suffix}",
                       event_ref=f"month:{month_index}",
                       from_business_id=bid)
    for good_id, per in recipe["goods_in"].items():
        adjust_inventory(store, bid, good_id, -units * per,
                         "production_input", game_minutes,
                         details={"recipe": recipe["id"]})
    adjust_inventory(store, bid, recipe["output_good"], units,
                     "production", game_minutes,
                     details={"recipe": recipe["id"],
                              "storm_days": storm_days,
                              "workers": workers})
    return units


def production_pass(store, data, month_index, game_minutes,
                    storm_days=0, converters_only=False):
    """Unit 05: every producer business runs its recipe(s) once
    for the month — the first recipe its inputs can source, then
    the next with whatever crew capacity remains is NOT modelled:
    one recipe per business per month keeps the flow legible.
    With converters_only, only recipes that consume inputs run —
    the engine calls this a second time after the supply chain
    lands, so processors can convert what they just bought.
    Returns {business_id: units_produced}."""
    produced = {}
    for b in business_mod.active_businesses(store):
        recipes = _recipes_for(data, b["category"])
        if converters_only:
            recipes = [r for r in recipes if r["goods_in"]]
            already = store.row(
                "SELECT 1 AS x FROM inventory_movements WHERE"
                " business_id = ? AND kind = 'production' AND"
                " game_minutes = ? LIMIT 1",
                (b["business_id"], game_minutes))
            if already:
                continue  # produced in the main pass already

        def convertible(recipe):
            return 0 if recipe["goods_in"] and all(
                inventory_of(store, b["business_id"], g) > 0
                for g in recipe["goods_in"]) else 1

        for recipe in sorted(recipes, key=convertible):
            units = _run_recipe(store, data, b, recipe, month_index,
                                game_minutes, storm_days,
                                key_suffix=":conv" if converters_only
                                else "")
            if units > 0:
                produced[b["business_id"]] = units
                break
    return produced


def _zone_of_business(store, data, business):
    if business["property_id"]:
        prop = store.row("SELECT district_id FROM properties WHERE"
                         " property_id = ?",
                         (business["property_id"],))
        if prop:
            return prop["district_id"]
    return None


def _distance_km(store, data, biz_a, biz_b):
    """Routed distance between two businesses' zones over the
    Session 03 graphs; intercity adds the bridge crossing leg.
    Falls back to the zone-anchor straight line when a route
    cannot be built (open-water zones)."""
    za, zb = _zone_of_business(store, data, biz_a), \
        _zone_of_business(store, data, biz_b)
    if not za or not zb:
        return 1.0
    ca, cb = cities_mod.city_of_zone(data, za), \
        cities_mod.city_of_zone(data, zb)
    if ca is None or cb is None:
        return 1.0
    if ca == cb:
        spec = data.city_spec(ca)
        route = roads_mod.pathfind(
            roads_mod.build_graph(spec),
            roads_mod.zone_anchor(spec, za),
            roads_mod.zone_anchor(spec, zb), "motor")
        if route:
            return max(0.1, route["distance_m"] / 1000)
    else:
        from . import regional as regional_mod
        route = regional_mod.intercity_route(data, za, zb, "motor")
        if route:
            return max(0.1, route["distance_m"] / 1000 + 1.5)
    ax, az = roads_mod.zone_anchor(data.city_spec(ca), za)
    bx, bz = roads_mod.zone_anchor(data.city_spec(cb), zb)
    return max(0.1, math.hypot(ax - bx, az - bz) / 1000)


def _suppliers_from_pool(store, data, pool, good_id, city_id,
                         buyer, month_index=None):
    """Suppliers ranked from the pass-start stock pool: producers
    first, then distributors, same city first. The pool is a
    snapshot — a business that buys a good in this pass does not
    become a reseller of it in the same pass (no circulation).
    The chain flows downstream only: end sellers (retail, food
    service) never supply other businesses unless they produce
    the good themselves, and same-category trades happen only
    for production inputs (a garment workshop buying cloth-goods
    from a light manufacturer).

    Session 09: when the coordination layer is live and a month
    is given, a third rank term prefers suppliers with a measured
    delivery record for this good (trailing recorded supply
    orders) — selection by experience, learned from outcomes.
    Price cannot rank suppliers here: Session 04 prices are per
    city+good, identical for every seller into a city, so there
    is no per-supplier price signal to select on (recorded in
    the Session 09 report). With no month (other callers, older
    tests) the term is 0 for everyone and the Session 04 order
    is preserved exactly."""
    from . import agents as agents_mod
    agents_live = month_index is not None \
        and agents_mod.is_setup(store)
    exclude_id = buyer["business_id"]
    buyer_inputs = set()
    for r in _recipes_for(data, buyer["category"]):
        buyer_inputs.update(r["goods_in"])
    out = []
    for b in business_mod.active_businesses(store):
        bid = b["business_id"]
        if bid == exclude_id:
            continue
        qty = pool.get((bid, good_id), 0.0)
        if qty <= 0:
            continue
        is_producer = any(r["output_good"] == good_id
                          for r in _recipes_for(data, b["category"]))
        if b["category"] in ("retail", "food_service") \
                and not is_producer:
            continue  # end sellers are not suppliers
        if b["category"] == buyer["category"] and not (
                is_producer and good_id in buyer_inputs):
            continue  # no sideways trade within a category
        same_city = business_mod.business_city(store, data, b) \
            == city_id
        reliable = 0
        if agents_live:
            reliable = 0 if agents_mod.supplier_reliable(
                store, data, bid, good_id, month_index) else 1
        rank = (0 if same_city else 1, 0 if is_producer else 1,
                reliable, bid)
        out.append((rank, b))
    out.sort(key=lambda t: t[0])
    return [b for _rank, b in out]


def supply_chain_pass(store, data, month_index, game_minutes):
    """Unit 06: stocking businesses order what they lack from
    whoever holds it. Stock is snapshotted at pass start (the
    pool), so goods move producer -> stocker exactly once per
    pass. An order never spends more than half the buyer's
    current balance on one good — firms keep a cash runway.
    Returns the orders executed."""
    pool = {}
    for b in business_mod.active_businesses(store):
        for good_id in data.goods:
            qty = inventory_of(store, b["business_id"], good_id)
            if qty > 0:
                pool[(b["business_id"], good_id)] = qty
    orders = []
    for b in business_mod.active_businesses(store):
        bid = b["business_id"]
        city = business_mod.business_city(store, data, b)
        for good_id in STOCKING.get(b["category"], ()):
            target = _target_stock(store, data, b, good_id,
                                   month_index)
            have = inventory_of(store, bid, good_id)
            if have >= target:
                continue
            need = target - have
            price = price_of(store, data, city, good_id)
            suppliers = _suppliers_from_pool(
                store, data, pool, good_id, city, b,
                month_index=month_index)
            for supplier in suppliers:
                if need <= 0:
                    break
                sid = supplier["business_id"]
                balance = store.business_balance(bid)
                affordable = min(balance, balance // 2) // price \
                    if price else 0
                take = min(need, pool.get((sid, good_id), 0.0),
                           affordable)
                if take <= 0:
                    continue
                pool[(sid, good_id)] -= take
                amount = int(take * price)
                dist = _distance_km(store, data, b, supplier)
                shipping = int(take * dist
                               * SHIPPING_NCR_PER_UNIT_KM)
                key = f"supply:{bid}:{sid}:{good_id}:{month_index}"
                store.transfer(None, None, amount, "business_sale",
                               game_minutes,
                               note=f"{good_id} supply order",
                               related_business_id=sid,
                               transfer_key=key,
                               event_ref=f"month:{month_index}",
                               from_business_id=bid,
                               to_business_id=sid)
                if shipping > 0 and store.business_balance(bid) \
                        >= shipping:
                    store.transfer(None, "SYS-MARKET", shipping,
                                   "shipping", game_minutes,
                                   note=f"shipping {good_id}",
                                   related_business_id=bid,
                                   transfer_key=key + ":ship",
                                   event_ref=f"month:{month_index}",
                                   from_business_id=bid)
                adjust_inventory(store, sid, good_id, -take,
                                 "supply_out", game_minutes,
                                 counterparty=bid, amount_ncr=amount,
                                 details={"month_index": month_index})
                # adjust_inventory rounds stock to 3 decimals;
                # re-read so the pool never promises more than
                # the shelf actually holds.
                pool[(sid, good_id)] = inventory_of(store, sid,
                                                    good_id)
                adjust_inventory(store, bid, good_id, take,
                                 "supply_in", game_minutes,
                                 counterparty=sid, amount_ncr=amount,
                                 details={"month_index": month_index,
                                          "distance_km": round(dist, 2),
                                          "shipping_ncr": shipping})
                order = {"buyer": bid, "seller": sid,
                         "good_id": good_id, "units": take,
                         "amount_ncr": amount,
                         "shipping_ncr": shipping}
                orders.append(order)
                # Session 09: every executed order is recorded
                # (the measured basis for supplier reliability)
                # and explained (inputs -> rule -> outcome) in the
                # buyer's decision record, when the coordination
                # layer is live.
                from . import agents as agents_mod
                if agents_mod.is_setup(store):
                    agents_mod.record_supply_order(
                        store, order, month_index, game_minutes)
                    agents_mod.log_agent_decision(
                        store, bid, "business", "supplier_selection",
                        {"good_id": good_id, "need_units": need,
                         "candidates": [s["business_id"]
                                        for s in suppliers],
                         "reliability_units": {
                             s["business_id"]:
                             agents_mod.supplier_reliability(
                                 store, data, s["business_id"],
                                 good_id, month_index)
                             for s in suppliers}},
                        "same city first, producers first, then"
                        " measured trailing delivery volume"
                        " (Session 09); price is per city+good in"
                        " Session 04 and cannot rank sellers",
                        {"seller": sid, "units": take,
                         "amount_ncr": amount}, game_minutes)
                need -= take
    return orders


def _target_stock(store, data, business, good_id, month_index):
    """How much of a good a business wants on its shelf: producers
    of the good want none of it bought in; stocking categories
    target a share of the city's recorded demand (last month's
    consumption + input demand), distributors a larger buffer."""
    category = business["category"]
    if good_id not in STOCKING.get(category, ()):
        return 0.0
    city = business_mod.business_city(store, data, business)
    demand = city_demand(store, data, city, good_id,
                         month_index - 1)
    peers = max(1, len([b for b in business_mod.active_businesses(store)
                        if b["category"] == category
                        and business_mod.business_city(store, data, b)
                        == city]))
    share = demand / peers if demand else 10.0
    if category == "distribution":
        share *= 2
    return max(5.0, share)


def city_demand(store, data, city_id, good_id, month_index):
    """The recorded demand signal for one good in one city for a
    month: household consumption + unmet demand (Unit 14's rows)
    + producer input consumption. Before any consumption exists
    (genesis month), a population baseline stands in — labelled
    here, and replaced by recorded demand from month 1 on."""
    cons = store.row(
        "SELECT COALESCE(SUM(hc.units + hc.unmet_units),0) AS s"
        " FROM household_consumption hc JOIN households h"
        " ON h.household_id = hc.household_id WHERE hc.good_id = ?"
        " AND hc.month_index = ? AND h.district_id IN"
        " (SELECT zone_id FROM city_zones WHERE city_id = ?)",
        (good_id, month_index, city_id))
    inputs = store.row(
        "SELECT COALESCE(SUM(-im.delta),0) AS s FROM"
        " inventory_movements im JOIN businesses b"
        " ON b.business_id = im.business_id WHERE im.good_id = ?"
        " AND im.kind = 'production_input'", (good_id,))
    total = (cons["s"] if cons else 0) + (inputs["s"] if inputs
                                          else 0)
    if total > 0:
        return total
    pop = cities_mod.city_population(store, data, city_id)
    per_capita = {"food_basket": 0.6, "fish": 0.2,
                  "clothing_set": 0.15, "household_supplies": 0.3,
                  "agricultural_produce": 2.0,
                  "manufactured_goods": 2.0}.get(good_id, 0.2)
    return pop * per_capita


def update_prices(store, data, month_index, game_minutes):
    """Unit 07: one bounded step per good per city, driven by the
    coverage ratio (stocked supply / recorded demand), with the
    signals persisted on every change."""
    changes = []
    for spec in data.city_specs():
        cid = spec["city_id"]
        for good_id, good in data.goods.items():
            supply = city_supply(store, data, cid, good_id)
            demand = city_demand(store, data, cid, good_id,
                                 month_index - 1)
            coverage = supply / demand if demand else 1.0
            old = price_of(store, data, cid, good_id)
            base = good["base_price_ncr"]
            new = old
            if coverage < COVERAGE_LOW:
                new = round(old * (1 + PRICE_STEP_UP))
            elif coverage > COVERAGE_HIGH:
                new = round(old * (1 - PRICE_STEP_DOWN))
            new = max(round(base * PRICE_FLOOR_RATIO),
                      min(round(base * PRICE_CAP_RATIO), new))
            if new != old:
                store.execute(
                    "UPDATE market_prices SET price_ncr = ?,"
                    " updated_month = ? WHERE city_id = ? AND"
                    " good_id = ?", (new, month_index, cid, good_id))
                hid = store.next_id("PH", "price_history",
                                    "history_id")
                store.insert(
                    "price_history", history_id=hid, city_id=cid,
                    good_id=good_id, old_price_ncr=old,
                    new_price_ncr=new,
                    signals=json.dumps({
                        "supply_units": round(supply, 2),
                        "demand_units": round(demand, 2),
                        "coverage": round(coverage, 3),
                        "base_price_ncr": base}, sort_keys=True),
                    game_minutes=game_minutes)
                changes.append({"city_id": cid, "good_id": good_id,
                                "old": old, "new": new})
    return changes


def price_index(store, data, city_id=None):
    """The market price index: the consumption basket's current
    cost against its genesis (base-price) cost. 100 at genesis."""
    basket = ("food_basket", "fish", "clothing_set",
              "household_supplies")
    cities = [city_id] if city_id else [s["city_id"]
                                         for s in data.city_specs()]
    num = den = 0.0
    for cid in cities:
        for good_id in basket:
            base = data.goods[good_id]["base_price_ncr"]
            num += price_of(store, data, cid, good_id)
            den += base
    return round(100 * num / den, 2) if den else 100.0


def _household_city(store, data, household):
    return cities_mod.city_of_zone(data, household["district_id"]) \
        or cities_mod.RUPSHA


def retail_allocation(store, data, month_index, game_minutes):
    """Unit 14: allocate each settled household's food/clothing
    spend across its city's retail shelves. Allocation is rationed
    fairly: when a city's stock cannot cover its total want, every
    household receives the same coverage fraction of its want —
    scarcity is shared and measured, never decided by iteration
    order. Returns totals."""
    from . import identity as identity_mod
    totals = {"households": 0, "units": 0.0, "unmet_units": 0.0,
              "takings_ncr": 0}
    # Unit 12 propagation: an active demand shock scales what
    # households try to buy (late import — crises reads this
    # module's price index through indicators).
    from . import crises as crises_mod
    demand_factor = crises_mod.active_effects(store)["demand_factor"]
    finances = store.rows(
        "SELECT hf.* FROM household_finances hf JOIN households h"
        " ON h.household_id = hf.household_id WHERE hf.month_index"
        " = ? AND h.dissolved_at_game_minutes IS NULL"
        " ORDER BY hf.household_id", (month_index,))
    # Pass 1: every household's wants, in units, per (city, good).
    wants_by_household = {}
    city_want = {}
    for fin in finances:
        hid = fin["household_id"]
        household = store.row("SELECT * FROM households WHERE"
                              " household_id = ?", (hid,))
        if household is None:
            continue
        city = _household_city(store, data, household)
        total_costs = fin["food_ncr"] + fin["housing_ncr"] \
            + fin["transport_ncr"] + fin["other_ncr"]
        hardship = 1.0
        if fin["emergency_ncr"] > 0 and total_costs > 0:
            hardship = max(0.25, 1 - fin["emergency_ncr"]
                           / total_costs)
        members = store.rows(
            "SELECT c.born_at_game_minutes FROM household_members hm"
            " JOIN characters c ON c.character_id = hm.character_id"
            " WHERE hm.household_id = ? AND hm.left_at_game_minutes"
            " IS NULL AND c.died_at_game_minutes IS NULL", (hid,))
        now = store.world()["game_minutes"]
        adults = sum(1 for m in members if identity_mod.age_years(
            m["born_at_game_minutes"], now) >= 18)
        children = len(members) - adults
        lc = data.prices["living_costs_monthly"]
        band = "lower"
        earner = store.row(
            "SELECT e.profession_id FROM employments e"
            " JOIN household_members hm ON hm.character_id"
            " = e.character_id WHERE hm.household_id = ?"
            " AND hm.left_at_game_minutes IS NULL"
            " AND e.ended_at_game_minutes IS NULL"
            " ORDER BY e.wage_per_month DESC LIMIT 1", (hid,))
        if earner:
            band = data.econ.band_for(data.wage(
                earner["profession_id"], "entry"))
        # The settlement's own clothing line, recomputed exactly as
        # the settlement computes it (engine._living_costs).
        clothing_spend = round(lc["clothing_personal"][band]
                               * (max(adults, 1) + 0.3 * children))
        food_spend = fin["food_ncr"] * hardship
        fish_spend = food_spend * FISH_SHARE_OF_FOOD_SPEND
        wants = {}
        for good_id, spend in (
                ("food_basket", food_spend - fish_spend),
                ("fish", fish_spend),
                ("clothing_set", clothing_spend * hardship)):
            if spend <= 0:
                continue
            price = price_of(store, data, city, good_id)
            units = spend / price if price else 0
            units *= demand_factor
            if units > 0:
                wants[good_id] = units
                key = (city, good_id)
                city_want[key] = city_want.get(key, 0.0) + units
        wants_by_household[hid] = (household, city, wants)
        totals["households"] += 1
    # Coverage per (city, good): stocked supply over total want.
    coverage = {}
    for (city, good_id), want in city_want.items():
        supply = _shelf_stock(store, data, city, good_id)
        coverage[(city, good_id)] = min(1.0, supply / want) \
            if want > 0 else 1.0
    # Pass 2: record each household's covered share; the physical
    # draw happens once per (city, good) afterwards, so shelf
    # stock and takings move exactly once per good per month.
    city_got = {}
    for hid, (household, city, wants) in wants_by_household.items():
        for good_id, want_units in wants.items():
            got_units = want_units * coverage[(city, good_id)]
            if got_units > 0:
                key = (city, good_id)
                city_got[key] = city_got.get(key, 0.0) + got_units
            price = price_of(store, data, city, good_id)
            unmet = round(want_units - got_units, 3)
            store.execute(
                "INSERT OR REPLACE INTO household_consumption"
                " (household_id, month_index, good_id, units,"
                " spend_ncr, unmet_units) VALUES (?, ?, ?, ?, ?, ?)",
                (hid, month_index, good_id, round(got_units, 3),
                 int(round(got_units * price)), unmet))
            totals["units"] += got_units
            totals["unmet_units"] += unmet
            if good_id == "food_basket" and want_units > 0 \
                    and unmet / want_units > 0.3:
                _food_hardship(store, household, game_minutes,
                               unmet / want_units)
    for (city, good_id), units in sorted(city_got.items()):
        _draw_from_shelves(store, data, city, good_id, units,
                           month_index, game_minutes, totals)
    return totals


def _shelf_stock(store, data, city_id, good_id):
    total = 0.0
    for b in business_mod.active_businesses(store):
        if b["category"] not in ("retail", "food_service"):
            continue
        if business_mod.business_city(store, data, b) != city_id:
            continue
        total += inventory_of(store, b["business_id"], good_id)
    return total


def _draw_from_shelves(store, data, city_id, good_id, want_units,
                       month_index, game_minutes, totals):
    """Draw units from the city's retail/food-service shelves in
    proportion to stock. System retailers are paid takings for
    what left their shelf; owner-run shops are not (their P&L is
    the settlement's). Returns units actually drawn."""
    sellers = []
    for b in business_mod.active_businesses(store):
        if b["category"] not in ("retail", "food_service"):
            continue
        if business_mod.business_city(store, data, b) != city_id:
            continue
        qty = inventory_of(store, b["business_id"], good_id)
        if qty > 0:
            sellers.append((b, qty))
    total_stock = sum(q for _b, q in sellers)
    if total_stock <= 0 or want_units <= 0:
        return 0.0
    price = price_of(store, data, city_id, good_id)
    drawn = 0.0
    for b, qty in sellers:
        share = want_units * qty / total_stock
        take = min(qty, share)
        if take <= 0:
            continue
        adjust_inventory(store, b["business_id"], good_id, -take,
                         "retail_sale", game_minutes,
                         details={"month_index": month_index})
        drawn += take
        if b["owner_character_id"] == "SYS-MARKET":
            takings = int(round(take * price))
            if takings > 0:
                store.transfer("SYS-MARKET", None, takings,
                               "retail_takings", game_minutes,
                               note=f"{good_id} takings",
                               related_business_id=b["business_id"],
                               transfer_key=f"takings:{b['business_id']}"
                                            f":{good_id}:{month_index}",
                               event_ref=f"month:{month_index}",
                               to_business_id=b["business_id"])
                totals["takings_ncr"] += takings
    return drawn


def _food_hardship(store, household, game_minutes, severity):
    """A household that could not get food feels it: the head's
    hunger satisfaction drops and the shortage is a life event —
    the Session 01 needs hook, driven by a measured shortfall."""
    head = store.row(
        "SELECT character_id FROM household_members WHERE"
        " household_id = ? AND role = 'head'"
        " AND left_at_game_minutes IS NULL",
        (household["household_id"],))
    if head is None:
        return
    cid = head["character_id"]
    needs = store.row("SELECT hunger FROM needs_state WHERE"
                      " character_id = ?", (cid,))
    if needs:
        store.execute("UPDATE needs_state SET hunger = ? WHERE"
                      " character_id = ?",
                      (max(0, needs["hunger"] - int(10 * severity)),
                       cid))
    from . import memory as memory_mod
    memory_mod.log_life_event(
        store, cid, "food_shortage", game_minutes,
        details={"household_id": household["household_id"],
                 "severity": round(severity, 2)})
