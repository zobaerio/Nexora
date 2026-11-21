"""Session 04 Unit 13 — Trade (deepened).

Session 03's regional pass already writes the monthly trade
flows from measured facts (industry employment, farmland,
populations). This unit makes those flows PHYSICAL and FISCAL:

- Physical: each flow moves real inventory. Manufactured goods
  leave Rupsha's producers/stockists and arrive at Shibnagar's
  retailers and processors; agricultural produce moves the other
  way into Rupsha's processors and food businesses. Units are
  the flow's value at the exporting city's market price; when
  exporters hold less than the flow, what exists moves and the
  shortfall is recorded as a city event — the flow record keeps
  Session 03's measured value, the goods layer reports what
  physically crossed.
- Fiscal: the configured import tariff (SIM MODEL rate in
  economy-config.json) is charged on each flow's value, paid
  from the SYS-MARKET clearing account to SYS-CITY with reason
  'tariff', keyed by the flow id (idempotent) — the same
  clearing treatment Session 03 documented for trade itself.
- Crisis propagation: while a demand-shock crisis is active,
  moved units scale by its factor (crises.active_effects) and
  the reduction is recorded with the movement.

Trade balance per city is read from the flow records themselves
(indicators.py surfaces it monthly).
"""
import json

from . import business as business_mod
from . import cities as cities_mod
from . import crises as crises_mod
from . import market as market_mod

FLOW_GOODS = {"manufactured_goods": "manufactured_goods",
              "agricultural_produce": "agricultural_produce"}
EXPORTER_CATEGORIES = {"manufactured_goods": ("manufacturing",),
                       "agricultural_produce": ("agriculture",
                                                "food_processing")}
IMPORTER_CATEGORIES = ("retail", "food_service", "food_processing",
                       "manufacturing")


def _holders(store, data, city_id, good_id, categories):
    out = []
    for b in business_mod.active_businesses(store):
        if b["category"] not in categories:
            continue
        if business_mod.business_city(store, data, b) != city_id:
            continue
        qty = market_mod.inventory_of(store, b["business_id"],
                                      good_id)
        out.append((b, qty))
    return out


def settle_trade(store, data, month_index, game_minutes):
    """Move inventory + collect tariffs for the month's flows
    (written by regional.monthly_flows earlier in the cadence).
    Returns a per-flow settlement summary."""
    if not business_mod.is_setup(store):
        return []
    tariff_rate = data.economy_config["tax_rules"][
        "import_tariff_percent"] / 100
    effects = crises_mod.active_effects(store)
    factor = effects["demand_factor"]
    out = []
    for flow in store.rows("SELECT * FROM trade_flows WHERE"
                           " month_index = ? ORDER BY flow_id",
                           (month_index,)):
        good_id = FLOW_GOODS.get(flow["goods"])
        if good_id is None:
            continue
        # Idempotent per flow: a flow whose tariff row or export
        # movement already exists was settled (the engine calls
        # this once per month; a replay must not move goods or
        # money twice).
        settled = store.row(
            "SELECT 1 AS x FROM economy_ledger WHERE transfer_key"
            " = ? LIMIT 1", (f"tariff:{flow['flow_id']}",)) \
            or store.row(
                "SELECT 1 AS x FROM inventory_movements WHERE"
                " kind = 'trade_out' AND details LIKE ? LIMIT 1",
                (f"%\"flow_id\": \"{flow['flow_id']}\"%",))
        if settled:
            continue
        value = flow["amount_ncr"]
        tariff = round(value * tariff_rate)
        if tariff > 0:
            store.transfer("SYS-MARKET", "SYS-CITY", tariff, "tariff",
                           game_minutes,
                           note=f"tariff on {flow['goods']} flow",
                           transfer_key=f"tariff:{flow['flow_id']}",
                           event_ref=f"trade_flow:{flow['flow_id']}")
        price = market_mod.price_of(store, data,
                                    flow["from_city_id"], good_id)
        want_units = (value / price if price else 0) * factor
        exporters = _holders(store, data, flow["from_city_id"],
                             good_id,
                             EXPORTER_CATEGORIES.get(good_id, ()))
        total_stock = sum(q for _b, q in exporters)
        moved = 0.0
        drawn = []
        if total_stock > 0 and want_units > 0:
            for b, qty in exporters:
                if qty <= 0:
                    continue
                take = min(qty, want_units * qty / total_stock)
                if take <= 0:
                    continue
                market_mod.adjust_inventory(
                    store, b["business_id"], good_id, -take,
                    "trade_out", game_minutes,
                    details={"flow_id": flow["flow_id"],
                             "to_city": flow["to_city_id"]})
                drawn.append((b, take))
                moved += take
        importers = _holders(store, data, flow["to_city_id"],
                             good_id, IMPORTER_CATEGORIES)
        if moved > 0:
            targets = importers or _holders(
                store, data, flow["to_city_id"], good_id,
                tuple(business_mod.GENESIS_CAPITAL.keys()))
            if targets:
                share = moved / len(targets)
                for b, _q in targets:
                    market_mod.adjust_inventory(
                        store, b["business_id"], good_id, share,
                        "trade_in", game_minutes,
                        details={"flow_id": flow["flow_id"],
                                 "from_city": flow["from_city_id"]})
        shortfall = round(want_units - moved, 3)
        if shortfall > 0.01:
            eid = store.next_id("CE", "city_events", "event_id")
            store.insert(
                "city_events", event_id=eid,
                city_id=flow["from_city_id"],
                event_type="trade_shortfall",
                details=json.dumps(
                    {"flow_id": flow["flow_id"], "good_id": good_id,
                     "wanted_units": round(want_units, 2),
                     "moved_units": round(moved, 2),
                     "demand_factor": factor}, sort_keys=True),
                game_minutes=game_minutes)
        out.append({"flow_id": flow["flow_id"], "good_id": good_id,
                    "value_ncr": value, "tariff_ncr": tariff,
                    "moved_units": round(moved, 2),
                    "shortfall_units": shortfall})
    return out


def trade_balance(store, city_id, month_index=None):
    sql = ("SELECT COALESCE(SUM(CASE WHEN from_city_id = ? THEN"
           " amount_ncr ELSE -amount_ncr END),0) AS s FROM"
           " trade_flows WHERE (from_city_id = ? OR to_city_id = ?)")
    params = [city_id, city_id, city_id]
    if month_index is not None:
        sql += " AND month_index = ?"
        params.append(month_index)
    return store.row(sql, tuple(params))["s"]
