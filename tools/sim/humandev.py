"""Session 06 — Human Development: setup, indicators, cadence.

The session's spine: setup seeds the institutions, facilities
and health profiles from the real building data (idempotently,
in generate_population, like Sessions 03–05); the monthly cadence
runs the session's passes in dependency order; and the human
development indicators are computed here, from persistent records
only, by the documented methodology below.

METHODOLOGY (also surfaced by the observatory):
- literacy_rate: share of living residents aged 15+ who are
  literate — subject_knowledge skill at or above the configured
  level, or a completed school record. A measured proxy, stated
  as such.
- education_access: enrolled school-age residents (3–17) over all
  living school-age residents.
- graduation_rate: school completions over completions + dropouts
  recorded in the trailing 12 months (a cohort-outcome share);
  absent when neither exists.
- skill_distribution: mean and median of each living adult's
  highest skill level (character_skills).
- healthcare_access: share of living residents whose city has an
  active facility.
- healthcare_capacity_per_100: total daily patient slots (the
  facilities' measured capacities) per 100 living residents.
- life_expectancy_observed: mean age at death over all recorded
  deaths; absent when no death is recorded.
- life_expectancy_model: the expectation of age at death under
  lifecycle.py's own mortality curve, integrated year by year —
  a model number, labelled as one, and the figure the health
  index uses (the observed mean over a young world's few deaths
  would be noise).
- population_health: mean health_profiles.health_score over the
  living.
- mean_wellbeing: mean wellbeing score of the month's snapshots.
- research_activity: research records in the trailing 12 months
  plus currently active projects.
- gdp_per_capita_ncr: the latest national Session 04 indicator,
  read, never recomputed.
- HDI: geometric mean of three indices — health
  (life_expectancy_model / configured max, capped at 1),
  education (mean of literacy_rate and education_access), income
  (log-scaled gdp_per_capita between the configured bounds).
  Absent when any component is absent: a composite is never
  fabricated from partial inputs.
"""
import json
import statistics

from . import identity as identity_mod
from . import lifecycle as lifecycle_mod

METHODOLOGY = {
    "literacy_rate": "living 15+ with subject_knowledge at/above"
                     " the configured level or a completed school"
                     " record, over living 15+",
    "education_access": "enrolled residents aged 3-17 over living"
                        " residents aged 3-17",
    "graduation_rate": "school completions over completions +"
                       " dropouts, trailing 12 months",
    "healthcare_access": "living residents in a city with an"
                         " active facility, over living residents",
    "healthcare_capacity_per_100": "facilities' daily patient"
                                   " slots per 100 living residents",
    "life_expectancy_observed": "mean age at death over recorded"
                                " deaths",
    "life_expectancy_model": "expected age at death integrated"
                             " from lifecycle.death_probability",
    "population_health": "mean health_profiles.health_score over"
                         " the living",
    "hdi": "geometric mean of health (model LE / max), education"
           " (mean of literacy + access) and income (log GDP per"
           " capita between configured bounds) indices",
}


def is_setup(store):
    w = store.world()
    return bool(w and w.get("humandev_setup")) \
        and store.row("SELECT 1 FROM educational_institutions"
                      " LIMIT 1") is not None


def setup_humandev(store, data, game_minutes=480):
    """Seed the Session 06 layer. Idempotent; hand-built worlds
    that never generate a population have no Session 06 layer and
    every Session 06 pass no-ops for them."""
    if is_setup(store):
        return {"already_setup": True}
    from . import health as health_mod
    from . import healthcare as healthcare_mod
    from . import institutions as inst_mod
    institutions = inst_mod.seed_institutions(store, data,
                                              game_minutes)
    facilities = healthcare_mod.seed_facilities(store, data,
                                                game_minutes)
    profiles = health_mod.seed_profiles(store, game_minutes)
    store.set_world(humandev_setup=1)
    store.commit()
    return {"institutions": institutions, "facilities": facilities,
            "health_profiles": profiles}


def model_life_expectancy():
    """Expected age at death under lifecycle.death_probability:
    LE = sum over ages of the survival probability, with annual
    mortality compounded from the daily curve."""
    survival = 1.0
    total = 0.0
    for age in range(0, 121):
        total += survival
        annual = 1 - (1 - lifecycle_mod.death_probability(age)) ** 365
        survival *= (1 - annual)
        if survival < 1e-9:
            break
    return round(total, 2)


def _living(store):
    return store.rows("SELECT * FROM characters WHERE is_system = 0"
                      " AND died_at_game_minutes IS NULL"
                      " ORDER BY character_id")


def compute_indicators(store, data, month_index, game_minutes):
    """The indicator set for one scope ('national'), computed
    from records. Components that cannot be computed are absent
    from the dict, never interpolated (the Session 04 rule)."""
    from . import decisions as decisions_mod
    from . import healthcare as healthcare_mod
    hcfg = data.education_health_config["humandev"]
    living = _living(store)
    ind = {}
    if not living:
        return ind
    ages = {c["character_id"]: identity_mod.age_years(
        c["born_at_game_minutes"], game_minutes) for c in living}
    # Literacy + education access.
    adults15 = [cid for cid, a in ages.items() if a >= 15]
    if adults15:
        literate = 0
        for cid in adults15:
            lvl = decisions_mod.skill_level(store, cid,
                                            "subject_knowledge")
            done = store.row("SELECT 1 FROM education_records WHERE"
                             " character_id = ? AND programme ="
                             " 'school' AND status = 'completed'",
                             (cid,))
            if lvl >= hcfg["literacy_min_skill_level"] or done:
                literate += 1
        ind["literacy_rate"] = round(literate / len(adults15), 4)
    school_age = [cid for cid, a in ages.items() if 3 <= a <= 17]
    if school_age:
        enrolled = store.row(
            "SELECT COUNT(*) AS n FROM education_records WHERE"
            " status = 'enrolled' AND programme = 'school'")["n"]
        ind["education_access"] = round(
            min(1.0, enrolled / len(school_age)), 4)
        ind["school_age_population"] = len(school_age)
        ind["school_enrolled"] = enrolled
    since = game_minutes - 360 * 1440
    comp = store.row("SELECT COUNT(*) AS n FROM education_records"
                     " WHERE status = 'completed' AND programme ="
                     " 'school' AND completed_at_game_minutes >= ?",
                     (since,))["n"]
    drops = store.row("SELECT COUNT(*) AS n FROM life_events WHERE"
                      " event_type = 'dropped_out' AND game_minutes"
                      " >= ?", (since,))["n"]
    if comp + drops > 0:
        ind["graduation_rate"] = round(comp / (comp + drops), 4)
    tops = []
    for c in living:
        if ages[c["character_id"]] >= 18:
            row = store.row("SELECT MAX(level) AS m FROM"
                            " character_skills WHERE character_id = ?",
                            (c["character_id"],))
            tops.append(row["m"] or 0)
    if tops:
        ind["skill_mean_level"] = round(statistics.mean(tops), 2)
        ind["skill_median_level"] = statistics.median(tops)
    # Healthcare access + capacity.
    by_city = healthcare_mod.facility_by_city(store)
    if by_city:
        from . import government as gov_mod
        covered = sum(1 for c in living
                      if gov_mod.city_of_character(
                          store, data, c["character_id"]) in by_city)
        ind["healthcare_access"] = round(covered / len(living), 4)
        slots = sum(healthcare_mod.daily_capacity(store, data, f)
                    for f in by_city.values())
        ind["healthcare_capacity_per_100"] = round(
            slots / len(living) * 100, 2)
    deaths = store.rows("SELECT born_at_game_minutes,"
                        " died_at_game_minutes FROM characters"
                        " WHERE died_at_game_minutes IS NOT NULL"
                        " AND is_system = 0")
    if deaths:
        ind["life_expectancy_observed"] = round(statistics.mean(
            identity_mod.age_years(d["born_at_game_minutes"],
                                   d["died_at_game_minutes"])
            for d in deaths), 2)
        ind["deaths_recorded"] = len(deaths)
    ind["life_expectancy_model"] = model_life_expectancy()
    prof = store.row("SELECT AVG(health_score) AS s FROM"
                     " health_profiles hp JOIN characters c"
                     " ON c.character_id = hp.character_id"
                     " WHERE c.died_at_game_minutes IS NULL")
    if prof and prof["s"] is not None:
        ind["population_health"] = round(prof["s"], 2)
    wb = store.row("SELECT AVG(wellbeing_score) AS s FROM"
                   " wellbeing_records WHERE month_index = ?",
                   (month_index,))
    if wb and wb["s"] is not None:
        ind["mean_wellbeing"] = round(wb["s"], 2)
    pubs = store.row("SELECT COUNT(*) AS n FROM research_records"
                     " WHERE month_index > ?", (month_index - 12,))["n"]
    active = store.row("SELECT COUNT(*) AS n FROM research_projects"
                       " WHERE status = 'active'")["n"]
    ind["research_activity"] = pubs + active
    from . import indicators as indicators_mod
    latest_econ = indicators_mod.latest(store, "national")
    if latest_econ and latest_econ["metrics"].get(
            "gdp_per_capita_ncr") is not None:
        ind["gdp_per_capita_ncr"] = latest_econ["metrics"][
            "gdp_per_capita_ncr"]
    # Composite HDI — only from present components.
    ref = hcfg["hdi_reference"]
    if "life_expectancy_model" in ind and "literacy_rate" in ind \
            and "education_access" in ind \
            and "gdp_per_capita_ncr" in ind:
        import math
        health_i = min(1.0, ind["life_expectancy_model"]
                       / ref["life_expectancy_max"])
        edu_i = (ind["literacy_rate"] + ind["education_access"]) / 2
        gdp_pc = max(ref["gdp_per_capita_min_ncr"],
                     ind["gdp_per_capita_ncr"])
        income_i = (math.log(gdp_pc)
                    - math.log(ref["gdp_per_capita_min_ncr"])) / \
            (math.log(ref["gdp_per_capita_max_ncr"])
             - math.log(ref["gdp_per_capita_min_ncr"]))
        income_i = max(0.0, min(1.0, income_i))
        ind["hdi_health_index"] = round(health_i, 4)
        ind["hdi_education_index"] = round(edu_i, 4)
        ind["hdi_income_index"] = round(income_i, 4)
        ind["hdi"] = round((health_i * edu_i * income_i) ** (1 / 3), 4) \
            if health_i > 0 and edu_i > 0 and income_i > 0 else 0.0
    ind["population"] = len(living)
    return ind


def indicators_monthly(store, data, month_index, game_minutes):
    ind = compute_indicators(store, data, month_index, game_minutes)
    store.execute("INSERT OR REPLACE INTO"
                  " human_development_indicators (snapshot_id, scope,"
                  " month_index, game_minutes, indicators) VALUES"
                  " (?, 'national', ?, ?, ?)",
                  (f"HD-national-{month_index}", month_index,
                   game_minutes, json.dumps(ind, sort_keys=True)))
    return ind


def monthly_pass(store, data, rng, month_index, game_minutes):
    """Session 06's monthly cadence, in dependency order:
    institutions (assignments) → academics (learning, exams,
    certifications, dropouts) → healthcare (budgets, procurement)
    → disease (surveillance, campaigns) → health (profiles,
    chronic, life-stage registration) → wellbeing → research →
    institution performance refresh → indicators. No-ops when the
    layer was never set up."""
    if not is_setup(store):
        return None
    from . import academics as academics_mod
    from . import disease as disease_mod
    from . import health as health_mod
    from . import healthcare as healthcare_mod
    from . import institutions as inst_mod
    from . import research as research_mod
    from . import wellbeing as wellbeing_mod
    out = {}
    out["institutions"] = inst_mod.monthly_pass(store, data,
                                                month_index,
                                                game_minutes)
    out["academics"] = academics_mod.monthly_pass(store, data, rng,
                                                  month_index,
                                                  game_minutes)
    out["healthcare"] = healthcare_mod.monthly_pass(store, data,
                                                    month_index,
                                                    game_minutes)
    out["disease"] = disease_mod.monthly_pass(store, data, rng,
                                              month_index,
                                              game_minutes)
    out["health"] = health_mod.monthly_pass(store, data, rng,
                                            month_index, game_minutes)
    out["wellbeing"] = wellbeing_mod.monthly_pass(store, data,
                                                  month_index,
                                                  game_minutes)
    out["research"] = research_mod.monthly_pass(store, data, rng,
                                                month_index,
                                                game_minutes)
    inst_mod.refresh_performance(store, data, game_minutes)
    out["indicators"] = indicators_monthly(store, data, month_index,
                                            game_minutes)
    return out
