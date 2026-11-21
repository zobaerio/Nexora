"""Session 04 Unit 12 — Economic Crises.

Crises are DETECTED from measured conditions, never rolled on a
dice. Detection runs monthly over Unit 11's fresh indicators and
the bank's real position, against the configured thresholds
(data/economy-config.json crisis_thresholds — SIM MODEL values,
labelled):

- unemployment_crisis: the national unemployment rate breaches
  the threshold;
- inflation_crisis: month-over-month basket inflation breaches
  the threshold;
- business_failure_crisis: closures this month reach the
  configured count;
- banking_stress: the bank's reserve ratio (reserves over
  outstanding loans) falls below the configured floor.

A crisis record opens with its measured severity (the actual
indicator values), stays active while the condition holds, and
resolves only after TWO consecutive clean months — recovery is
as measured as onset. Configured scenarios (economy-config
'scenarios') are the one exogenous door: a scenario entry fires
deterministically at its month_index (e.g. a demand shock) and
is labelled a scenario in its record, never disguised as an
emergent detection.

Propagation is through real channels, and the effects are read
by the systems they touch:
- an active unemployment or business-failure crisis freezes new
  business hiring (labour.monthly_pass receives the freeze —
  the freeze itself is recorded on the crisis);
- an active demand shock scales household consumption wants
  (market.retail_allocation) and intercity inventory movement
  (trade.settle_trade) by the scenario's factor;
- an active banking stress stops new loan disbursement
  (banking checks the crisis state before lending).
Recovery mechanisms are the systems' own: prices fall back as
coverage rebuilds, the labour market reopens when the freeze
lifts, and the crisis record closes with its full duration —
consequences are the indicator series before/during/after,
which the observatory serves.
"""
import json

from . import indicators as indicators_mod

RECOVERY_CLEAN_MONTHS = 2


def _open(store, crisis_type, month_index, game_minutes, severity,
          details):
    existing = store.row(
        "SELECT * FROM crisis_records WHERE crisis_type = ?"
        " AND status = 'active'", (crisis_type,))
    if existing:
        store.execute(
            "UPDATE crisis_records SET severity = ?, clean_months"
            " = 0 WHERE crisis_id = ?",
            (json.dumps(severity, sort_keys=True),
             existing["crisis_id"]))
        return existing["crisis_id"]
    cid = store.next_id("CR", "crisis_records", "crisis_id")
    store.insert("crisis_records", crisis_id=cid,
                 crisis_type=crisis_type, scope="national",
                 status="active",
                 severity=json.dumps(severity, sort_keys=True),
                 opened_month=month_index,
                 opened_at_game_minutes=game_minutes,
                 details=json.dumps(details, sort_keys=True))
    return cid


def _clean_or_close(store, crisis_type, month_index, game_minutes):
    row = store.row("SELECT * FROM crisis_records WHERE crisis_type"
                    " = ? AND status = 'active'", (crisis_type,))
    if row is None:
        return
    clean = row["clean_months"] + 1
    if clean >= RECOVERY_CLEAN_MONTHS:
        store.execute(
            "UPDATE crisis_records SET status = 'resolved',"
            " resolved_at_game_minutes = ?, clean_months = ?"
            " WHERE crisis_id = ?", (game_minutes, clean,
                                     row["crisis_id"]))
    else:
        store.execute("UPDATE crisis_records SET clean_months = ?"
                      " WHERE crisis_id = ?", (clean,
                                               row["crisis_id"]))


def detect(store, data, month_index, game_minutes):
    """Run detection for the month over the fresh indicators.
    Returns the crisis types opened or still active."""
    cfg = data.economy_config["crisis_thresholds"]
    snap = indicators_mod.latest(store, "national")
    if snap is None:
        return []
    m = snap["metrics"]
    since = game_minutes - 30 * 1440
    closures = store.row(
        "SELECT COUNT(*) AS n FROM business_events WHERE"
        " event_type = 'closed' AND game_minutes > ?"
        " AND game_minutes <= ?", (since, game_minutes))["n"]
    bank = m.get("bank") or {}
    conditions = {
        "unemployment_crisis": (
            m["unemployment_rate"] * 100
            > cfg["unemployment_percent"],
            {"unemployment_rate": m["unemployment_rate"],
             "threshold_percent": cfg["unemployment_percent"]}),
        "inflation_crisis": (
            (m["inflation_monthly_percent"] or 0)
            > cfg["inflation_monthly_percent"],
            {"inflation_monthly_percent":
             m["inflation_monthly_percent"],
             "threshold_percent": cfg["inflation_monthly_percent"]}),
        "business_failure_crisis": (
            closures >= cfg["business_failures_per_month"],
            {"closures_this_month": closures,
             "threshold": cfg["business_failures_per_month"]}),
        "banking_stress": (
            bank.get("reserve_ratio") is not None
            and bank["reserve_ratio"]
            < data.economy_config["bank"]["min_reserve_ratio"],
            {"reserve_ratio": bank.get("reserve_ratio"),
             "floor": data.economy_config["bank"]
             ["min_reserve_ratio"]}),
    }
    active = []
    for crisis_type, (breached, severity) in conditions.items():
        if breached:
            _open(store, crisis_type, month_index, game_minutes,
                  severity, {"source": "measured_detection"})
            active.append(crisis_type)
        else:
            _clean_or_close(store, crisis_type, month_index,
                            game_minutes)
    # Configured scenarios: deterministic, labelled, exogenous.
    for sc in data.economy_config.get("scenarios", []):
        start = sc["month_index"]
        end = start + sc.get("duration_months", 1)
        if start <= month_index < end:
            _open(store, sc["type"], month_index, game_minutes,
                  {"scenario": sc},
                  {"source": "configured_scenario", "scenario": sc})
            active.append(sc["type"])
        elif month_index >= end:
            _clean_or_close(store, sc["type"], month_index,
                            game_minutes)
    return active


def active_crises(store):
    return store.rows("SELECT * FROM crisis_records WHERE status"
                      " = 'active' ORDER BY crisis_id")


def active_effects(store):
    """The propagation surface other systems read: hiring freeze,
    demand factor, lending halt — each derived from the live
    crisis records."""
    effects = {"hiring_freeze": False, "demand_factor": 1.0,
               "lending_halt": False, "types": []}
    for c in active_crises(store):
        effects["types"].append(c["crisis_type"])
        if c["crisis_type"] in ("unemployment_crisis",
                                "business_failure_crisis"):
            effects["hiring_freeze"] = True
        if c["crisis_type"] == "banking_stress":
            effects["lending_halt"] = True
        details = json.loads(c["details"])
        sc = details.get("scenario") or {}
        if "takings_factor" in sc:
            effects["demand_factor"] = min(
                effects["demand_factor"], sc["takings_factor"])
        if c["crisis_type"] == "demand_shock":
            effects["demand_factor"] = min(
                effects["demand_factor"],
                sc.get("takings_factor", 0.7))
    return effects
