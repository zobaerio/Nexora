"""Session 03 Unit 10 — City Growth & Development Engine.

Growth, densification and decline as consequences, never dice:

- city_metrics() DERIVES a city's state from live facts:
  occupancy, employment rate, average building condition,
  infrastructure headroom, service levels, and the income-band
  mix of its residents (economy_sim's own band_for over current
  wages). The development index is a documented weighted blend
  of those facts; the level and economic class are bands over
  the index and the mix.
- monthly_growth() acts on the metrics: when a city's vacancy is
  under 8% and measured housing demand is positive, the city
  commissions a construction project through Unit 11 (funded
  from SYS-CITY's real balance — no money is invented for it);
  when vacancy exceeds 30% while population falls, decline
  pressure doubles building decay that month and is recorded.
- Parcel values drift with the same pressure signal (vacancy
  below/above the 12% neutral point), bounded per month.

Every action lands in city_events; level changes are milestones.
"""
from . import buildings as buildings_mod
from . import cities as cities_mod
from . import distribution as distribution_mod

VACANCY_GROWTH_TRIGGER = 0.08
VACANCY_DECLINE_TRIGGER = 0.30
NEUTRAL_VACANCY = 0.12


def _event(store, city_id, event_type, details, game_minutes):
    eid = store.next_id("CE", "city_events", "event_id")
    import json
    store.insert("city_events", event_id=eid, city_id=city_id,
                 event_type=event_type, details=json.dumps(details),
                 game_minutes=game_minutes)


def city_metrics(store, data, city_id):
    spec = data.city_spec(city_id)
    zones = spec["zones"]
    marks = ",".join("?" for _ in zones)
    population = cities_mod.city_population(store, data, city_id)
    housing = distribution_mod.housing_pressure(store, data, city_id)
    # Employment rate over resident adults.
    from .identity import age_years
    now = store.world()["game_minutes"]
    adults = employed = 0
    band_mix = {}
    for r in store.rows(
            f"SELECT c.character_id, c.born_at_game_minutes FROM"
            f" characters c JOIN households h ON h.household_id ="
            f" c.household_id WHERE h.district_id IN ({marks})"
            f" AND c.is_system = 0 AND c.died_at_game_minutes"
            f" IS NULL AND h.dissolved_at_game_minutes IS NULL",
            tuple(zones)):
        if age_years(r["born_at_game_minutes"], now) < 18:
            continue
        adults += 1
        emp = store.row("SELECT wage_per_month FROM employments"
                        " WHERE character_id = ?"
                        " AND ended_at_game_minutes IS NULL",
                        (r["character_id"],))
        if emp:
            employed += 1
            band = data.econ.band_for(emp["wage_per_month"])
        else:
            band = "none"
        band_mix[band] = band_mix.get(band, 0) + 1
    employment_rate = round(employed / adults, 3) if adults else 0.0
    cond = store.row("SELECT AVG(condition) AS c FROM building_state"
                     " WHERE city_id = ? AND construction_year"
                     " IS NOT NULL", (city_id,))
    avg_condition = round(cond["c"], 1) if cond and cond["c"] \
        else 100.0
    from . import infrastructure as infrastructure_mod
    headroom = infrastructure_mod.headroom(store, city_id)
    svc = store.row("SELECT AVG(level) AS l FROM municipal_services"
                    " WHERE city_id = ?", (city_id,))
    services_level = round(svc["l"], 1) if svc and svc["l"] \
        else 50.0
    index = round(
        (1 - housing["vacancy_rate"]) * 25
        + employment_rate * 25
        + (avg_condition / 100) * 20
        + max(0.0, min(1.0, headroom)) * 15
        + (services_level / 100) * 15, 1)
    if index < 35:
        level = "emerging"
    elif index < 55:
        level = "developing"
    elif index < 75:
        level = "established"
    else:
        level = "advanced"
    total_bands = sum(band_mix.values()) or 1
    upper_share = band_mix.get("upper", 0) / total_bands
    lower_share = band_mix.get("lower", 0) / total_bands
    if upper_share >= 0.25:
        economic_class = "affluent"
    elif lower_share >= 0.6:
        economic_class = "lower_income"
    else:
        economic_class = "mixed_income"
    return {"city_id": city_id, "population": population,
            "households": len(cities_mod.city_households(
                store, data, city_id)),
            "housing": housing, "employment_rate": employment_rate,
            "band_mix": band_mix, "avg_building_condition":
            avg_condition, "infra_headroom": headroom,
            "services_level": services_level,
            "development_index": index, "development_level": level,
            "economic_class": economic_class}


def monthly_growth(store, data, month_index, game_minutes):
    """The monthly development pass. Returns per-city actions."""
    from . import construction as construction_mod
    out = {}
    prev_pops = {}
    for spec in data.city_specs():
        row = store.row("SELECT metrics FROM city_statistics WHERE"
                        " city_id = ? AND month_index = ?",
                        (spec["city_id"], month_index - 1))
        if row:
            import json
            prev_pops[spec["city_id"]] = json.loads(
                row["metrics"]).get("population")
    any_decline = False
    for spec in data.city_specs():
        cid = spec["city_id"]
        m = city_metrics(store, data, cid)
        actions = []
        prev_pop = prev_pops.get(cid)
        pop_change = None if prev_pop is None else \
            m["population"] - prev_pop
        declining = m["housing"]["vacancy_rate"] \
            > VACANCY_DECLINE_TRIGGER and (pop_change or 0) < 0
        if declining:
            any_decline = True
            actions.append("decline_pressure")
            _event(store, cid, "decline_pressure",
                   {"vacancy_rate": m["housing"]["vacancy_rate"],
                    "population_change": pop_change}, game_minutes)
        demand = distribution_mod.residential_demand(store, data, cid)
        active = store.row("SELECT COUNT(*) AS n FROM"
                            " construction_projects WHERE city_id = ?"
                            " AND status IN ('active',"
                            " 'stalled_funding')", (cid,))["n"]
        if m["housing"]["vacancy_rate"] < VACANCY_GROWTH_TRIGGER \
                and demand["total"] > 0 and active == 0:
            pid = construction_mod.start_civic_project(
                store, data, cid, game_minutes,
                store.world()["day_index"])
            if pid:
                actions.append(f"commissioned:{pid}")
                _event(store, cid, "growth_commissioned",
                       {"project_id": pid,
                        "vacancy_rate": m["housing"]["vacancy_rate"],
                        "demand": demand}, game_minutes)
        # Parcel values drift with the pressure signal.
        factor = max(-0.02, min(0.03, NEUTRAL_VACANCY
                                - m["housing"]["vacancy_rate"]))
        if factor:
            for p in store.rows("SELECT parcel_id, market_value FROM"
                                " land_parcels WHERE city_id = ? AND"
                                " development_status IN ('vacant',"
                                " 'developed')", (cid,)):
                store.execute(
                    "UPDATE land_parcels SET market_value = ? WHERE"
                    " parcel_id = ?",
                    (int(p["market_value"] * (1 + factor)),
                     p["parcel_id"]))
        # Development level milestones.
        prev = store.row("SELECT development_level FROM cities WHERE"
                         " city_id = ?", (cid,))
        if prev and prev["development_level"] != m[
                "development_level"]:
            _event(store, cid, "development_milestone",
                   {"from": prev["development_level"],
                    "to": m["development_level"],
                    "index": m["development_index"]}, game_minutes)
            actions.append("milestone")
        out[cid] = {"metrics": m, "actions": actions}
    buildings_mod.monthly_upkeep(store, data, game_minutes,
                                  decline=any_decline)
    return out
