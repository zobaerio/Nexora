"""Session 06 — Human Health: Profiles & the Condition Layer.

This implements, in the simulation, the design contract GDD-12
wrote and no session had yet built in code: health is *a condition
with a cause, a course and a memory* — never a random punishment
and never a fifth need bar.

- The cause list is CLOSED (GDD-12 §3): weather exposure, commute
  incident, construction-site accident, age-related health events,
  complications of an untreated condition — plus, new with this
  session, communicable disease, which arrives WITH the system
  that causes it (disease.py), exactly as GDD-12's rule requires.
  A condition that cannot name its cause cannot be constructed:
  start_condition validates against CAUSES.
- Bands: unwell / injured / serious, then recovering while a
  treated course runs. Courses are day windows (config, from
  GDD-12 §4's tuning): treated windows are shorter; an untreated
  condition reaching its window end rolls for complication
  (GDD-12 §3.5) — it may clear, or worsen (a longer course, a
  higher band where one exists, the complicated flag set). A
  treated condition never complicates.
- Effects are real, through existing machinery only: the day's
  rest bend (agent_state.rest_day — the scheduler now bends study
  blocks too, GDD-11 §2's illness absence), the emotions system's
  own 'illness' profile (defined in Session 01, never fired until
  now), the healthcare need, an episodic memory of the episode and
  of recovery, and — for Elders with a serious condition — the
  mortality multiplier GDD-12 §3.4 prescribes for
  lifecycle.death_probability (1.0 for everyone else).
- Health profiles: a monthly aggregate per character (health
  score, fitness, chronic status, disability, condition history)
  computed by a documented formula from measured state — needs
  satisfactions, age band, conditions, employment physicality.
  Chronic (noncommunicable) status onsets monthly for Middle-Aged+
  citizens at the configured rates and is managed through the
  clinic (healthcare.py's chronic review visits).

All probabilities and windows are SIM MODEL values in
data/education-health-config.json. This is a simplified
simulation model, not clinical knowledge: conditions are bands
and causes, never named real diseases or diagnoses.
"""
from . import emotions as emotions_mod
from . import identity as identity_mod
from . import memory as memory_mod
from . import needs as needs_mod

CAUSES = ("weather_exposure", "commute_incident",
          "construction_accident", "age_related", "complication",
          "disease_transmission", "disease_endemic")
BANDS = ("unwell", "injured", "serious")
# Professions whose work is physically demanding (fitness target).
PHYSICAL_PROFESSIONS = ("construction_worker", "police_officer",
                        "taxi_driver", "chef")


def cfg(data):
    return data.education_health_config["health"]


def is_open(status):
    return status in ("active", "recovering")


def open_condition(store, character_id):
    return store.row("SELECT * FROM health_conditions WHERE"
                     " character_id = ? AND status IN"
                     " ('active', 'recovering') ORDER BY condition_id"
                     " LIMIT 1", (character_id,))


def start_condition(store, data, rng, character_id, band, cause,
                    day_index, game_minutes, facility_id=None):
    """Open a condition + its clinic visit. The single entry
    point every cause uses — the closed cause list is enforced
    here. Returns the condition_id, or None when the character
    already carries an open condition (GDD-12: at most one)."""
    if cause not in CAUSES:
        raise ValueError(f"condition without a designed cause: {cause}")
    if band not in BANDS:
        raise ValueError(f"unknown condition band: {band}")
    if open_condition(store, character_id) is not None:
        return None
    hcfg = cfg(data)
    untreated = hcfg["recovery_days"][band]["untreated"]
    span = rng.stream("health-window", character_id, day_index,
                      cause).randint(untreated[0], untreated[1])
    cid_ = store.next_id("HC", "health_conditions", "condition_id")
    store.insert("health_conditions", condition_id=cid_,
                 character_id=character_id, band=band, cause=cause,
                 status="active", started_day=day_index,
                 recovery_end_day=day_index + span,
                 facility_id=facility_id)
    _ensure_profile(store, character_id, game_minutes)
    store.execute("UPDATE health_profiles SET conditions_total ="
                  " conditions_total + 1, last_condition_at_game_minutes"
                  " = ? WHERE character_id = ?",
                  (game_minutes, character_id))
    emotions_mod.apply_event(store, character_id, "illness")
    needs_mod.adjust(store, character_id, {"healthcare": -12},
                     game_minutes)
    memory_mod.log_life_event(store, character_id, "condition_onset",
                              game_minutes,
                              details={"band": band, "cause": cause,
                                       "condition_id": cid_})
    memory_mod.record_memory(store, character_id, "illness", -30,
                             game_minutes)
    if facility_id is not None:
        from . import healthcare as healthcare_mod
        visit_id = healthcare_mod.register_visit(
            store, character_id, facility_id, "illness",
            day_index, game_minutes, condition_id=cid_)
        store.execute("UPDATE health_conditions SET visit_id = ?"
                      " WHERE condition_id = ?", (visit_id, cid_))
    return cid_


def _ensure_profile(store, character_id, game_minutes):
    if store.row("SELECT 1 FROM health_profiles WHERE character_id"
                 " = ?", (character_id,)) is None:
        needs = needs_mod.get_needs(store, character_id)
        score = needs["healthcare"] if needs else 80.0
        store.insert("health_profiles", character_id=character_id,
                     health_score=round(float(score), 2))


def seed_profiles(store, game_minutes):
    n = 0
    for c in store.rows("SELECT character_id FROM characters WHERE"
                        " is_system = 0 AND died_at_game_minutes"
                        " IS NULL"):
        if store.row("SELECT 1 FROM health_profiles WHERE"
                     " character_id = ?", (c["character_id"],)) is None:
            _ensure_profile(store, c["character_id"], game_minutes)
            n += 1
    return n


def mortality_multiplier(store, character_id):
    """GDD-12 §3.4: the death rule reads elder stage plus active
    or recent serious conditions. Returns the configured
    multiplier when the character carries an open serious
    condition, else 1.0 (including in worlds where the Session 06
    layer was never set up — no rows can exist there)."""
    row = store.row("SELECT 1 FROM health_conditions WHERE"
                    " character_id = ? AND band = 'serious'"
                    " AND status IN ('active', 'recovering')",
                    (character_id,))
    if row is None:
        return 1.0
    return _multiplier_value()


_MULT = None


def _multiplier_value():
    global _MULT
    if _MULT is None:
        from . import dataio
        raw = dataio._load_json("education-health-config.json")
        _MULT = raw["health"]["mortality"]["elder_serious_multiplier"]
    return _MULT


# -- daily pass ---------------------------------------------------------

def _crew_projects(store):
    """character_id -> worst accident rate today, from the real
    construction projects they crew (Session 03): a project whose
    completed stages include an uninspected one carries the
    configured higher rate (GDD-12 §3.3)."""
    import json as _json
    out = {}
    for proj in store.rows("SELECT * FROM construction_projects"
                           " WHERE status = 'active'"):
        inspections = _json.loads(proj["inspections"] or "{}")
        uninspected = any(v.get("inspected") is False
                          for v in inspections.values())
        for cid in _json.loads(proj["crew"] or "[]"):
            out[cid] = out.get(cid, False) or uninspected
    return out


def _onset_rolls(store, data, rng, day_index, game_minutes, preset):
    """The daily life-events health roll (GDD-12 §4.1): each
    living character rolls against the causes their actual day
    exposes them to. Returns the number of conditions opened."""
    hcfg = cfg(data)
    onset = hcfg["onset_daily"]
    from . import healthcare as healthcare_mod
    facilities = healthcare_mod.facility_by_city(store)
    crew = _crew_projects(store)
    opened = 0
    chars = store.rows("SELECT * FROM characters WHERE is_system = 0"
                       " AND died_at_game_minutes IS NULL"
                       " ORDER BY character_id")
    for char in chars:
        cid = char["character_id"]
        if open_condition(store, cid) is not None:
            continue
        age = identity_mod.age_years(char["born_at_game_minutes"],
                                     game_minutes)
        emp = store.row("SELECT profession_id FROM employments WHERE"
                        " character_id = ? AND ended_at_game_minutes"
                        " IS NULL", (cid,))
        prof = emp["profession_id"] if emp else None
        city = None
        fac = None
        cause = band = None
        roll = rng.stream("health-onset", cid, day_index,
                          "weather").random()
        if preset in onset["weather_exposure"]["presets"]:
            wcfg = onset["weather_exposure"]
            if prof in wcfg["outdoor_professions"]:
                rate = wcfg["outdoor_rate"]
            elif age <= 12 or age >= 65:
                rate = wcfg["vulnerable_rate"]
            else:
                rate = wcfg["base_rate"]
            if roll < rate:
                cause, band = "weather_exposure", wcfg["band"]
        if cause is None and preset in onset["commute_incident"]["presets"]:
            enrolled = store.row(
                "SELECT 1 FROM education_records WHERE character_id = ?"
                " AND status = 'enrolled'", (cid,))
            if prof is not None or enrolled:
                if rng.stream("health-onset", cid, day_index,
                              "commute").random() \
                        < onset["commute_incident"]["rate"]:
                    cause = "commute_incident"
                    band = onset["commute_incident"]["band"]
        if cause is None and cid in crew:
            ccfg = onset["construction_accident"]
            rate = ccfg["uninspected_rate"] if crew[cid] \
                else ccfg["base_rate"]
            r = rng.stream("health-onset", cid, day_index,
                           "construction")
            if r.random() < rate:
                cause = "construction_accident"
                band = "serious" if r.random() < ccfg["serious_share"] \
                    else ccfg["band"]
        if cause is None:
            acfg = onset["age_related"]
            if age >= 65:
                rate, share = acfg["elder_rate"], \
                    acfg["serious_share_elder"]
            elif age >= 50:
                rate, share = acfg["middle_aged_rate"], \
                    acfg["serious_share_middle"]
            else:
                rate, share = 0.0, 0.0
            if rate:
                r = rng.stream("health-onset", cid, day_index, "age")
                if r.random() < rate:
                    cause = "age_related"
                    band = "serious" if r.random() < share else \
                        ("unwell" if r.random() < 0.5 else "injured")
        if cause is None:
            continue
        if city is None:
            from . import government as gov_mod
            city = gov_mod.city_of_character(store, data, cid)
        fac = facilities.get(city) if city else None
        if fac is None:
            fac = facilities.get("rupsha_city")
        opened += 1 if start_condition(
            store, data, rng, cid, band, cause, day_index,
            game_minutes,
            facility_id=fac["facility_id"] if fac else None) else 0
    return opened


def _progress_courses(store, data, rng, day_index, game_minutes):
    """Window-end resolution for every open condition: treated
    courses close as recovered; untreated courses roll for
    complication (GDD-12 §3.5). Returns (closed, complicated)."""
    hcfg = cfg(data)
    closed = complicated = 0
    for cond in store.rows("SELECT * FROM health_conditions WHERE"
                           " status IN ('active', 'recovering')"
                           " ORDER BY condition_id"):
        if cond["recovery_end_day"] is None \
                or day_index < cond["recovery_end_day"]:
            continue
        cid = cond["character_id"]
        if cond["status"] == "recovering":
            _close_condition(store, cond, day_index, game_minutes,
                             "recovered")
            closed += 1
            continue
        roll = rng.stream("health-complication",
                          cond["condition_id"]).random()
        if roll >= hcfg["recovery_days"]["complication_chance"]:
            _close_condition(store, cond, day_index, game_minutes,
                             "recovered_untreated")
            closed += 1
            continue
        # Complication: the course worsens measurably.
        complicated += 1
        band = cond["band"]
        if band == "injured":
            new_band = "serious"
        else:
            new_band = band  # unwell prolongs; serious extends
        span = rng.stream("health-window", cond["condition_id"],
                          "complication").randint(
            *hcfg["recovery_days"]["serious"]["untreated"])
        store.execute(
            "UPDATE health_conditions SET band = ?, complicated = 1,"
            " recovery_end_day = ? WHERE condition_id = ?",
            (new_band, day_index + span, cond["condition_id"]))
        memory_mod.log_life_event(store, cid, "condition_complicated",
                                  game_minutes,
                                  details={"condition_id":
                                           cond["condition_id"],
                                           "band": new_band})
        emotions_mod.apply_event(store, cid, "illness")
    return closed, complicated


def _close_condition(store, cond, day_index, game_minutes, outcome):
    cid = cond["character_id"]
    store.execute("UPDATE health_conditions SET status = 'closed',"
                  " closed_day = ?, outcome = ? WHERE condition_id = ?",
                  (day_index, outcome, cond["condition_id"]))
    if cond["visit_id"]:
        store.execute("UPDATE patient_visits SET stage = 'closed',"
                      " closed_day = ? WHERE visit_id = ? AND stage"
                      " != 'closed'", (day_index, cond["visit_id"]))
    store.execute("UPDATE hospital_admissions SET discharged_day = ?"
                  " WHERE visit_id = ? AND discharged_day IS NULL",
                  (day_index, cond["visit_id"]))
    # A serious course that began as an injury and complicated
    # leaves a lasting mobility limitation (the profile's
    # disability flag) — recorded, never hidden.
    if cond["complicated"] and cond["band"] == "serious" \
            and cond["cause"] in ("construction_accident",
                                  "commute_incident"):
        store.execute("UPDATE health_profiles SET disability = 1"
                      " WHERE character_id = ?", (cid,))
    memory_mod.record_memory(store, cid, "recovery", 25, game_minutes)
    memory_mod.log_life_event(store, cid, "condition_recovered",
                              game_minutes,
                              details={"condition_id":
                                       cond["condition_id"],
                                       "outcome": outcome})
    needs_mod.adjust(store, cid, {"healthcare": 8}, game_minutes)


def _apply_rest_days(store, day_index):
    """Bend tomorrow for characters inside a condition course:
    serious rests the whole course, injured the first days,
    unwell the day after onset (longer when untreated). Uses the
    existing agent_state.rest_day flag — the same bend the
    decision engine's rest candidate uses."""
    for cond in store.rows("SELECT * FROM health_conditions WHERE"
                           " status IN ('active', 'recovering')"):
        cid = cond["character_id"]
        age_days = day_index - cond["started_day"]
        rest = False
        if cond["band"] == "serious":
            rest = True
        elif cond["band"] == "injured":
            rest = age_days < 3
        elif cond["band"] == "unwell":
            rest = age_days == 0 or (age_days == 1
                                     and not cond["treated"])
        if rest:
            store.execute("UPDATE agent_state SET rest_day = 1"
                          " WHERE character_id = ?", (cid,))


def daily_pass(store, data, rng, day_index, game_minutes, preset):
    """The health layer's daily cadence, run at day rollover:
    onsets, disease transmission, clinic queues, course
    resolution, rest bends — in that order, all on seeded streams,
    all bounded to the health tables and the day's records."""
    from . import disease as disease_mod
    from . import healthcare as healthcare_mod
    opened = _onset_rolls(store, data, rng, day_index, game_minutes,
                          preset)
    infected = disease_mod.daily_transmission(store, data, rng,
                                              day_index, game_minutes)
    seen = healthcare_mod.process_daily_queue(store, data, rng,
                                              day_index, game_minutes)
    closed, complicated = _progress_courses(store, data, rng,
                                            day_index, game_minutes)
    _apply_rest_days(store, day_index)
    return {"conditions_opened": opened, "infections": infected,
            "visits_processed": seen, "conditions_closed": closed,
            "complications": complicated}


# -- monthly: profiles + chronic onset -----------------------------------

def monthly_pass(store, data, rng, month_index, game_minutes):
    """Health profiles recomputed from measured state; chronic
    (noncommunicable) onset for Middle-Aged+ citizens; life-stage
    care visits registered with the facilities (healthcare.py)."""
    from . import healthcare as healthcare_mod
    pcfg = cfg(data)["profiles"]
    created = seed_profiles(store, game_minutes)
    chronic_new = 0
    for char in store.rows("SELECT * FROM characters WHERE"
                           " is_system = 0 AND died_at_game_minutes"
                           " IS NULL ORDER BY character_id"):
        cid = char["character_id"]
        age = identity_mod.age_years(char["born_at_game_minutes"],
                                     game_minutes)
        prof = store.row("SELECT * FROM health_profiles WHERE"
                         " character_id = ?", (cid,))
        if prof is None:
            continue
        needs = needs_mod.get_needs(store, cid)
        if needs is None:
            continue
        # Chronic onset (noncommunicable pathway): a monthly roll
        # for the age bands, on a seeded stream.
        if not prof["chronic"] and age >= 50:
            rates = pcfg["chronic_onset_monthly"]
            rate = rates["age_65_plus"] if age >= 65 \
                else rates["age_50_64"]
            if rng.stream("chronic-onset", cid,
                          month_index).random() < rate:
                store.execute("UPDATE health_profiles SET chronic = 1,"
                              " chronic_label = 'age_related_chronic'"
                              " WHERE character_id = ?", (cid,))
                prof = store.row("SELECT * FROM health_profiles"
                                 " WHERE character_id = ?", (cid,))
                chronic_new += 1
                memory_mod.log_life_event(store, cid, "chronic_onset",
                                          game_minutes)
        open_cond = open_condition(store, cid)
        age_penalty = 0
        if age >= 65:
            age_penalty = pcfg["age_penalty"]["elder"]
        elif age >= 50:
            age_penalty = pcfg["age_penalty"]["middle_aged"]
        target = (0.5 * needs["healthcare"] + 0.25 * needs["sleep"]
                  + 0.25 * needs["hunger"] - age_penalty
                  - (pcfg["chronic_penalty"] if prof["chronic"] else 0)
                  - (pcfg["active_condition_penalty"] if open_cond
                     else 0))
        target = max(5.0, min(100.0, target))
        score = round(prof["health_score"]
                      + (target - prof["health_score"]) * 0.5, 2)
        emp = store.row("SELECT profession_id FROM employments WHERE"
                        " character_id = ? AND ended_at_game_minutes"
                        " IS NULL", (cid,))
        fit_target = 65.0 if emp and emp["profession_id"] in \
            PHYSICAL_PROFESSIONS else 45.0
        if age >= 65:
            fit_target -= 15.0
        fitness = round(prof["fitness"]
                        + (fit_target - prof["fitness"]) * 0.3, 2)
        store.execute("UPDATE health_profiles SET health_score = ?,"
                      " fitness = ?, updated_month = ?"
                      " WHERE character_id = ?",
                      (score, fitness, month_index, cid))
    care = healthcare_mod.register_life_stage_care(
        store, data, month_index, game_minutes)
    return {"profiles_created": created, "chronic_onsets": chronic_new,
            "life_stage_visits": care}
