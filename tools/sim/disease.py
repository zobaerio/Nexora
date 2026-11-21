"""Session 06 — Disease Simulation (simplified, configurable).

A deliberately small epidemiological model, in the spec's own
terms: configurable parameters, scenario support, and NO claim to
real medical prediction. The diseases are fictional simulation
constructs (config: data/education-health-config.json) whose only
effect on a person is a health condition of the configured band
(health.py) — bands and causes, never a real diagnosis.

- Transmission runs over REAL contact structure only: household
  co-residents, plus a seeded sample of institution-mates for
  students (their actual enrolment institution). No invented
  contact network exists.
- Infection creates a disease_record and a health condition with
  cause 'disease_transmission' (or 'disease_endemic' for an index
  case). Recovery is scheduled at infection from the configured
  duration; recovery grants time-limited immunity, recorded on
  the record itself.
- Index cases arise two ways, both configured: the labelled
  endemic daily chance per susceptible citizen, and deterministic
  scenarios (config list, fired by day_index — the
  government-config scenarios pattern) used by tests and by any
  future authored outbreak. The standard config carries an empty
  scenario list.
- Vaccination: a citizen's vaccination (vaccination_records,
  written by campaigns below or by tests through the same helper)
  protects them with the configured effectiveness — resolved once
  per citizen per disease on a seeded stream, so a vaccine either
  worked for that citizen or it did not, consistently.
- Surveillance + intervention (monthly): active cases per 100
  residents per city are measured from disease_records; at or
  above the configured threshold the city's facility runs a
  vaccination campaign from its own vaccine stock (doses bound
  coverage), prioritising children and elders, recorded dose by
  dose. The campaign's cost is the consumed stock's procurement
  value, already ledgered at procurement (healthcare.py) and
  accounted on the facility's budget row.
"""
from . import cities as cities_mod
from . import government as gov_mod
from . import health as health_mod
from . import identity as identity_mod


def cfg(data):
    return data.education_health_config["disease"]


def diseases(data):
    return {d["id"]: d for d in cfg(data)["diseases"]}


def _immune_until(store, character_id, disease_id):
    row = store.row("SELECT MAX(immune_until_day) AS u FROM"
                    " disease_records WHERE character_id = ?"
                    " AND disease_id = ?", (character_id, disease_id))
    return row["u"] if row and row["u"] is not None else None


def is_immune(store, data, rng, character_id, disease_id, day_index):
    until = _immune_until(store, character_id, disease_id)
    if until is not None and day_index < until:
        return True
    vac = store.row("SELECT 1 FROM vaccination_records WHERE"
                    " character_id = ? AND disease_id = ?",
                    (character_id, disease_id))
    if vac:
        eff = diseases(data)[disease_id]["vaccine_effectiveness"]
        return rng.stream("vaccine-effect", character_id,
                          disease_id).random() < eff
    return False


def infect(store, data, rng, character_id, disease_id, source,
           day_index, game_minutes):
    """Record an infection + open its health condition. Returns
    the disease record id, or None when the citizen is already
    infected or immune."""
    d = diseases(data)[disease_id]
    existing = store.row("SELECT 1 FROM disease_records WHERE"
                         " character_id = ? AND disease_id = ?"
                         " AND status = 'infectious'",
                         (character_id, disease_id))
    if existing or is_immune(store, data, rng, character_id,
                             disease_id, day_index):
        return None
    if health_mod.open_condition(store, character_id) is not None:
        return None  # one open condition at a time (GDD-12)
    span = rng.stream("disease-duration", character_id, disease_id,
                      day_index).randint(*d["recovery_days"])
    rid = store.next_id("DR", "disease_records", "record_id")
    city = gov_mod.city_of_character(store, data, character_id)
    store.insert("disease_records", record_id=rid,
                 disease_id=disease_id, character_id=character_id,
                 status="infectious", source=source,
                 infected_day=day_index,
                 recovered_day=day_index + span,
                 immune_until_day=day_index + span
                 + d["immunity_days"],
                 city_id=city)
    from . import healthcare as healthcare_mod
    fac = healthcare_mod.facility_for_character(store, data,
                                                character_id)
    health_mod.start_condition(
        store, data, rng, character_id, d["band"],
        "disease_endemic" if source == "endemic_index"
        else "disease_transmission",
        day_index, game_minutes,
        facility_id=fac["facility_id"] if fac else None)
    return rid


def _contacts(store, data, rng, record, day_index):
    """The infectious citizen's contacts today: household
    co-residents, plus a seeded sample of institution-mates when
    the citizen is an enrolled student."""
    cid = record["character_id"]
    out = []
    char = store.row("SELECT household_id FROM characters WHERE"
                     " character_id = ?", (cid,))
    if char and char["household_id"]:
        for m in store.rows(
                "SELECT hm.character_id FROM household_members hm"
                " JOIN characters c ON c.character_id ="
                " hm.character_id WHERE hm.household_id = ?"
                " AND hm.left_at_game_minutes IS NULL"
                " AND c.died_at_game_minutes IS NULL"
                " AND hm.character_id != ?",
                (char["household_id"], cid)):
            out.append(m["character_id"])
    rec = store.row("SELECT institution_id FROM education_records"
                    " WHERE character_id = ? AND status = 'enrolled'",
                    (cid,))
    if rec:
        mates = [r["character_id"] for r in store.rows(
            "SELECT character_id FROM education_records WHERE"
            " institution_id = ? AND status = 'enrolled'"
            " AND character_id != ? ORDER BY character_id",
            (rec["institution_id"], cid))]
        if mates:
            k = min(diseases(data)[record["disease_id"]]
                    ["contacts_sampled_per_day"], len(mates))
            out.extend(rng.stream("disease-contacts",
                                  record["record_id"],
                                  day_index).sample(mates, k))
    return out


def daily_transmission(store, data, rng, day_index, game_minutes):
    """Spread + recovery + index cases for one day. Returns the
    number of new infections."""
    new = 0
    # Recovery first: records whose scheduled day has arrived flip
    # to recovered (their condition closes through health.py's own
    # course resolution or immediately when its window has passed).
    for rec in store.rows("SELECT * FROM disease_records WHERE"
                          " status = 'infectious' AND recovered_day"
                          " <= ? ORDER BY record_id", (day_index,)):
        store.execute("UPDATE disease_records SET status = 'recovered'"
                      " WHERE record_id = ?", (rec["record_id"],))
        # The disease course is over: its health condition may not
        # outlast it (health.py closes it at the window end).
        store.execute("UPDATE health_conditions SET recovery_end_day"
                      " = MIN(recovery_end_day, ?) WHERE character_id"
                      " = ? AND cause IN ('disease_transmission',"
                      " 'disease_endemic') AND status IN ('active',"
                      " 'recovering')",
                      (day_index, rec["character_id"]))
    for disease_id, d in diseases(data).items():
        # Transmission from every infectious citizen.
        for rec in store.rows("SELECT * FROM disease_records WHERE"
                              " disease_id = ? AND status = 'infectious'"
                              " ORDER BY record_id", (disease_id,)):
            if day_index >= rec["recovered_day"]:
                continue
            infectious_span = d["infectious_days"]
            if day_index - rec["infected_day"] >= infectious_span[1]:
                continue
            for contact in _contacts(store, data, rng, rec, day_index):
                if store.row("SELECT died_at_game_minutes FROM"
                             " characters WHERE character_id = ?",
                             (contact,))["died_at_game_minutes"]:
                    continue
                if health_mod.open_condition(store, contact) \
                        is not None:
                    continue
                roll = rng.stream("disease-transmit", disease_id,
                                  rec["character_id"], contact,
                                  day_index).random()
                if roll < d["transmission_per_contact_day"]:
                    if infect(store, data, rng, contact, disease_id,
                              "transmission", day_index,
                              game_minutes):
                        new += 1
        # Endemic index cases (labelled chance) + configured
        # scenarios for this day.
        for char in store.rows("SELECT character_id FROM characters"
                               " WHERE is_system = 0 AND"
                               " died_at_game_minutes IS NULL"
                               " ORDER BY character_id"):
            cid = char["character_id"]
            if health_mod.open_condition(store, cid) is not None:
                continue
            if rng.stream("disease-index", disease_id, cid,
                          day_index).random() \
                    < d["endemic_index_daily_chance"]:
                if infect(store, data, rng, cid, disease_id,
                          "endemic_index", day_index, game_minutes):
                    new += 1
        for sc in cfg(data)["scenarios"]:
            if sc.get("day_index") == day_index \
                    and sc.get("disease_id") == disease_id:
                city = sc.get("city_id")
                for char in store.rows(
                        "SELECT c.character_id FROM characters c"
                        " WHERE c.is_system = 0 AND"
                        " c.died_at_game_minutes IS NULL"
                        " ORDER BY c.character_id"):
                    cid = char["character_id"]
                    if city and gov_mod.city_of_character(
                            store, data, cid) != city:
                        continue
                    if health_mod.open_condition(store, cid) \
                            is not None:
                        continue
                    if infect(store, data, rng, cid, disease_id,
                              "scenario", day_index, game_minutes):
                        new += 1
                    break
    return new


def vaccinate(store, character_id, disease_id, facility_id, day_index,
              game_minutes):
    """One recorded vaccination (dose consumed by the caller when
    it comes from facility stock). Idempotent per day."""
    if store.row("SELECT 1 FROM vaccination_records WHERE"
                 " character_id = ? AND disease_id = ? AND day_index"
                 " = ?", (character_id, disease_id, day_index)):
        return None
    rid = store.next_id("VR", "vaccination_records", "record_id")
    store.insert("vaccination_records", record_id=rid,
                 character_id=character_id, disease_id=disease_id,
                 facility_id=facility_id, day_index=day_index,
                 game_minutes=game_minutes)
    return rid


def _active_cases(store, disease_id, city_id):
    row = store.row("SELECT COUNT(*) AS n FROM disease_records WHERE"
                    " disease_id = ? AND status = 'infectious'"
                    " AND city_id = ?", (disease_id, city_id))
    return row["n"] if row else 0


def monthly_pass(store, data, rng, month_index, game_minutes):
    """Surveillance + vaccination campaigns (see module docstring).
    Returns {city_id: campaign summary}."""
    from . import healthcare as healthcare_mod
    scfg = cfg(data)["surveillance"]
    day_index = game_minutes // 1440
    out = {}
    by_city = healthcare_mod.facility_by_city(store)
    items = {i["id"]: i for i in
             data.education_health_config["health"]["medications"]
             ["items"]}
    for disease_id in diseases(data):
        for city_id in (cities_mod.RUPSHA, cities_mod.SHIBNAGAR):
            pop = cities_mod.city_population(store, data, city_id)
            if pop <= 0:
                continue
            active = _active_cases(store, disease_id, city_id)
            per_100 = active / pop * 100
            if per_100 < scfg["epidemic_threshold_per_100"]:
                continue
            fac = by_city.get(city_id)
            if fac is None:
                continue
            fid = fac["facility_id"]
            doses = healthcare_mod._stock(store, fid,
                                          "sim_vaccine_dose")
            target = int(pop * scfg["campaign_coverage_per_100"]
                         / 100)
            residents = []
            for c in store.rows(
                    "SELECT c.character_id, c.born_at_game_minutes"
                    " FROM characters c WHERE c.is_system = 0 AND"
                    " c.died_at_game_minutes IS NULL"):
                if gov_mod.city_of_character(store, data,
                                             c["character_id"]) \
                        == city_id:
                    age = identity_mod.age_years(
                        c["born_at_game_minutes"], game_minutes)
                    priority = 0 if (age <= 12 or age >= 65) else 1
                    residents.append((priority, c["character_id"]))
            residents.sort()
            given = 0
            for _prio, cid in residents:
                if given >= min(doses, target):
                    break
                if is_immune(store, data, rng, cid, disease_id,
                             day_index):
                    continue
                if vaccinate(store, cid, disease_id, fid, day_index,
                             game_minutes):
                    healthcare_mod._consume_stock(
                        store, fid, items["sim_vaccine_dose"], None,
                        game_minutes, reason="vaccination_campaign")
                    given += 1
            if given:
                budget = store.row(
                    "SELECT * FROM healthcare_budgets WHERE"
                    " facility_id = ? AND month_index = ?",
                    (fid, month_index))
                if budget:
                    store.execute("UPDATE healthcare_budgets SET"
                                  " campaign_ncr = campaign_ncr + ?"
                                  " WHERE budget_id = ?",
                                  (given * items["sim_vaccine_dose"]
                                   ["procurement_ncr_per_unit"],
                                   budget["budget_id"]))
            out[city_id] = {"disease_id": disease_id,
                            "active_cases": active,
                            "per_100": round(per_100, 2),
                            "vaccinations_given": given}
    return out
