"""Session 06 — Healthcare Network: Facilities, Patient Journeys,
Medication Inventory, Budgets.

The network grows honestly from the data (GDD-12 §1): the world
has exactly two clinics — the District Clinic in Rupsha and the
Shibnagar Clinic — because those are the clinic buildings in the
merged building data. Hospital / specialised facility types exist
in the spec's framework only; serious cases are stabilised at the
clinic and referred off-district (an admission record with
transfer days), never treated in an invented ward.

- Staff: real citizens employed as doctors. The District Clinic
  is staffed by doctors resident in Rupsha (genesis + Session 04
  civic labour); the Shibnagar Clinic by Session 05's GOV-HEALTH
  civil-service doctors plus doctors resident in Shibnagar.
  A facility with no doctors still registers patients — they wait
  on the untreated course (GDD-12: the clinic does not conjure
  staff), and its daily capacity falls to the configured base.
- Patient journeys are one queue with recorded stages:
  registered → assessed (a named doctor, a diagnosis roll against
  their measured diagnosis skill, GDD-12 §4.3) → treated (the
  condition's fictional medication consumed from stock when one
  applies) → closed when the condition's course ends (health.py).
  Life-stage visits (birth care, chronic review, child check,
  follow-up) run through the same queue and close on treatment.
  Every stage writes treatment_records; a failed diagnosis sets a
  longer recovery window and schedules a follow-up visit.
- Medication inventory is FICTIONAL (config): quantities per
  facility, procured monthly from the market pool with the
  clinic's own budget — ledger transfers SYS-CITY → SYS-MARKET
  with transfer keys and event refs, capped by the month's
  budget authority (healthcare_budgets). A stockout leaves the
  visit waiting and the condition untreated: availability
  measurably affects care. Care itself is free at point of use
  (GDD-12 §6) — no patient is ever charged, and no per-patient
  ledger row exists.
- Budgets stay consistent by construction and by test: allocated
  authority is recorded monthly; procurement spend is the sum of
  its ledger rows and never exceeds the allocation.
"""
import json

from . import cities as cities_mod
from . import government as gov_mod

FUNDING_ACCOUNT = "SYS-CITY"  # the national treasury (civic funding)


def cfg(data):
    return data.education_health_config["health"]


def seed_facilities(store, data, game_minutes):
    """Facility rows for the clinic buildings that exist, with
    genesis stock at target levels (the Session 04 genesis
    inventory pattern: opening stores are a world-genesis fact,
    recorded in pharmacy_records, not a purchase)."""
    hcfg = cfg(data)
    buildings = data.all_buildings()
    ids = []
    for spec in hcfg["facilities"]:
        if spec["building_id"] not in buildings:
            continue
        fid = spec["facility_id"]
        if store.row("SELECT 1 FROM healthcare_facilities WHERE"
                     " facility_id = ?", (fid,)) is None:
            tcfg = hcfg["facility_types"][spec["type"]]
            store.insert("healthcare_facilities", facility_id=fid,
                         building_id=spec["building_id"],
                         city_id=spec["city_id"],
                         facility_type=spec["type"],
                         name=spec["name"],
                         equipment_level=tcfg["equipment_level"],
                         monthly_budget_ncr=tcfg["monthly_budget_ncr"],
                         created_at_game_minutes=game_minutes)
            for item in hcfg["medications"]["items"]:
                store.insert("medical_inventory", facility_id=fid,
                             item_id=item["id"],
                             quantity=item["target_stock"])
                rid = store.next_id("PH", "pharmacy_records",
                                    "record_id")
                store.insert("pharmacy_records", record_id=rid,
                             facility_id=fid, item_id=item["id"],
                             change=item["target_stock"],
                             reason="genesis_stock",
                             game_minutes=game_minutes)
        ids.append(fid)
    return ids


def facility_by_city(store):
    out = {}
    for f in store.rows("SELECT * FROM healthcare_facilities"
                        " WHERE active = 1 ORDER BY facility_id"):
        out[f["city_id"]] = f
    return out


def facility_for_character(store, data, character_id):
    city = gov_mod.city_of_character(store, data, character_id)
    by_city = facility_by_city(store)
    if city and city in by_city:
        return by_city[city]
    return by_city.get(cities_mod.RUPSHA)


def doctors_for_facility(store, data, facility):
    """The facility's doctors (see module docstring for the
    staffing rule), ordered by character_id."""
    ids = set()
    if facility["city_id"] == cities_mod.SHIBNAGAR:
        for r in store.rows("SELECT character_id FROM civil_service"
                            " WHERE institution_id = 'GOV-HEALTH'"
                            " AND status = 'active'"):
            ids.add(r["character_id"])
    for r in store.rows(
            "SELECT c.character_id FROM characters c"
            " JOIN employments e ON e.character_id = c.character_id"
            " WHERE e.profession_id = 'doctor'"
            " AND e.ended_at_game_minutes IS NULL"
            " AND c.died_at_game_minutes IS NULL"):
        if gov_mod.city_of_character(store, data,
                                     r["character_id"]) \
                == facility["city_id"]:
            ids.add(r["character_id"])
    # Only the living, still-employed doctors count.
    out = []
    for cid in sorted(ids):
        emp = store.row("SELECT 1 FROM employments WHERE"
                        " character_id = ? AND profession_id = 'doctor'"
                        " AND ended_at_game_minutes IS NULL", (cid,))
        char = store.row("SELECT died_at_game_minutes FROM characters"
                         " WHERE character_id = ?", (cid,))
        if emp and char and char["died_at_game_minutes"] is None:
            out.append(cid)
    return out


def daily_capacity(store, data, facility):
    tcfg = cfg(data)["facility_types"][facility["facility_type"]]
    doctors = doctors_for_facility(store, data, facility)
    return (tcfg["base_patients_per_day"]
            + tcfg["patients_per_doctor_per_day"] * len(doctors))


def register_visit(store, character_id, facility_id, visit_type,
                   day_index, game_minutes, condition_id=None,
                   follow_up_of=None):
    vid = store.next_id("PV", "patient_visits", "visit_id")
    store.insert("patient_visits", visit_id=vid,
                 character_id=character_id, facility_id=facility_id,
                 visit_type=visit_type, stage="registered",
                 condition_id=condition_id,
                 registered_day=day_index, follow_up_of=follow_up_of)
    if condition_id:
        store.execute("UPDATE health_conditions SET visit_id = ?"
                      " WHERE condition_id = ?", (vid, condition_id))
    return vid


def _medication_for(store, data, band):
    for item in cfg(data)["medications"]["items"]:
        if band in item["used_for_bands"]:
            return item
    return None


def _stock(store, facility_id, item_id):
    row = store.row("SELECT quantity FROM medical_inventory WHERE"
                    " facility_id = ? AND item_id = ?",
                    (facility_id, item_id))
    return row["quantity"] if row else 0


def _consume_stock(store, facility_id, item, visit_id, game_minutes,
                   reason="treatment"):
    store.execute("UPDATE medical_inventory SET quantity = quantity - 1"
                  " WHERE facility_id = ? AND item_id = ?",
                  (facility_id, item["id"]))
    rid = store.next_id("PH", "pharmacy_records", "record_id")
    store.insert("pharmacy_records", record_id=rid,
                 facility_id=facility_id, item_id=item["id"], change=-1,
                 reason=reason, visit_id=visit_id,
                 game_minutes=game_minutes)


def _treatment_record(store, visit, action, day_index, game_minutes,
                      doctor=None, medication_item_id=None,
                      details=None):
    tid = store.next_id("TR", "treatment_records", "treatment_id")
    store.insert("treatment_records", treatment_id=tid,
                 visit_id=visit["visit_id"],
                 condition_id=visit["condition_id"],
                 character_id=visit["character_id"],
                 facility_id=visit["facility_id"],
                 doctor_character_id=doctor, action=action,
                 medication_item_id=medication_item_id,
                 day_index=day_index, game_minutes=game_minutes,
                 details=json.dumps(details or {}, sort_keys=True))
    return tid


# Visit types that consume a medication item by visit type rather
# than by condition band (life-stage care pathways).
VISIT_MEDICATION = {"birth_care": "sim_maternal_kit",
                    "chronic_review": "sim_chronic_pack",
                    "vaccination": "sim_vaccine_dose"}


def process_daily_queue(store, data, rng, day_index, game_minutes):
    """Each facility assesses up to its daily capacity of
    registered visits (FIFO). Returns the number processed."""
    from . import decisions as decisions_mod
    from . import health as health_mod
    hcfg = cfg(data)
    processed = 0
    for fac in store.rows("SELECT * FROM healthcare_facilities"
                          " WHERE active = 1 ORDER BY facility_id"):
        fid = fac["facility_id"]
        doctors = doctors_for_facility(store, data, fac)
        capacity = daily_capacity(store, data, fac)
        queue = store.rows("SELECT * FROM patient_visits WHERE"
                           " facility_id = ? AND stage = 'registered'"
                           " AND registered_day <= ?"
                           " ORDER BY visit_id LIMIT ?",
                           (fid, day_index, capacity))
        seen_by = {}
        for visit in queue:
            if not doctors:
                break  # no staff: patients wait (untreated course)
            doctor = min(doctors,
                         key=lambda d: (seen_by.get(d, 0), d))
            seen_by[doctor] = seen_by.get(doctor, 0) + 1
            store.execute("UPDATE patient_visits SET stage ="
                          " 'assessed', assessed_day = ?,"
                          " doctor_character_id = ? WHERE visit_id = ?",
                          (day_index, doctor, visit["visit_id"]))
            visit = store.row("SELECT * FROM patient_visits WHERE"
                              " visit_id = ?", (visit["visit_id"],))
            processed += 1
            _assess_and_treat(store, data, rng, fac, visit, doctor,
                              day_index, game_minutes, decisions_mod,
                              health_mod)
    return processed


def _assess_and_treat(store, data, rng, fac, visit, doctor, day_index,
                      game_minutes, decisions_mod, health_mod):
    hcfg = cfg(data)
    rcfg = hcfg["recovery_days"]
    cid = visit["character_id"]
    if visit["condition_id"]:
        cond = store.row("SELECT * FROM health_conditions WHERE"
                         " condition_id = ?", (visit["condition_id"],))
        if cond is None or cond["status"] == "closed":
            store.execute("UPDATE patient_visits SET stage = 'closed',"
                          " closed_day = ? WHERE visit_id = ?",
                          (day_index, visit["visit_id"]))
            return
        # Diagnosis: the doctor's measured diagnosis skill against
        # the band's threshold (GDD-12 §4.3).
        skill = decisions_mod.skill_level(store, doctor, "diagnosis")
        threshold = rcfg["diagnosis_skill_threshold"][cond["band"]]
        diagnosis_ok = skill >= threshold
        _treatment_record(store, visit, "assessment", day_index,
                          game_minutes, doctor=doctor,
                          details={"diagnosis_skill": skill,
                                   "threshold": threshold,
                                   "diagnosis_ok": diagnosis_ok})
        item = _medication_for(store, data, cond["band"])
        if item is not None and _stock(store, fac["facility_id"],
                                       item["id"]) <= 0:
            # Stockout: the visit returns to the queue; the
            # condition stays on its untreated course. Recorded.
            store.execute("UPDATE patient_visits SET stage ="
                          " 'registered', details = ? WHERE visit_id"
                          " = ?", (json.dumps(
                              {"awaiting_medication": item["id"]}),
                              visit["visit_id"]))
            _treatment_record(store, visit, "awaiting_medication",
                              day_index, game_minutes, doctor=doctor,
                              medication_item_id=item["id"])
            return
        if item is not None:
            _consume_stock(store, fac["facility_id"], item,
                           visit["visit_id"], game_minutes)
        span = rng.stream("health-window", cond["condition_id"],
                          "treated").randint(
            *rcfg[cond["band"]]["treated"])
        if not diagnosis_ok:
            span = int(round(span * rcfg["diagnosis_failure_factor"]))
        store.execute("UPDATE health_conditions SET treated = 1,"
                      " status = 'recovering', recovery_end_day = ?"
                      " WHERE condition_id = ?",
                      (day_index + span, cond["condition_id"]))
        store.execute("UPDATE patient_visits SET stage = 'treated',"
                      " treated_day = ?, diagnosis_ok = ?,"
                      " medication_item_id = ? WHERE visit_id = ?",
                      (day_index, 1 if diagnosis_ok else 0,
                       item["id"] if item else None, visit["visit_id"]))
        _treatment_record(store, visit, "treatment", day_index,
                          game_minutes, doctor=doctor,
                          medication_item_id=item["id"] if item
                          else None,
                          details={"recovery_days": span})
        # The doctor learns from the consultation (GDD-12 §5).
        decisions_mod.add_skill_xp(store, doctor, "medicine", 4)
        decisions_mod.add_skill_xp(store, doctor, "diagnosis", 4)
        if cond["band"] == "serious":
            aid = store.next_id("HA", "hospital_admissions",
                                "admission_id")
            store.insert("hospital_admissions", admission_id=aid,
                         visit_id=visit["visit_id"], character_id=cid,
                         facility_id=fac["facility_id"],
                         referred_off_district=1,
                         transfer_days=rcfg["referral_transfer_days"],
                         admitted_day=day_index)
            _treatment_record(store, visit, "referral_off_district",
                              day_index, game_minutes, doctor=doctor,
                              details={"transfer_days":
                                       rcfg["referral_transfer_days"]})
        if not diagnosis_ok:
            register_visit(store, cid, fac["facility_id"], "follow_up",
                           day_index + 2, game_minutes,
                           condition_id=cond["condition_id"],
                           follow_up_of=visit["visit_id"])
        return
    # Life-stage / follow-up visits: care is delivered at the
    # assessment and the visit closes the same day.
    item = None
    med_id = VISIT_MEDICATION.get(visit["visit_type"])
    if med_id:
        item = next((i for i in cfg(data)["medications"]["items"]
                     if i["id"] == med_id), None)
        if item is not None and _stock(store, fac["facility_id"],
                                       item["id"]) <= 0:
            store.execute("UPDATE patient_visits SET stage ="
                          " 'registered', details = ? WHERE visit_id"
                          " = ?", (json.dumps(
                              {"awaiting_medication": item["id"]}),
                              visit["visit_id"]))
            _treatment_record(store, visit, "awaiting_medication",
                              day_index, game_minutes, doctor=doctor,
                              medication_item_id=item["id"])
            return
        if item is not None:
            _consume_stock(store, fac["facility_id"], item,
                           visit["visit_id"], game_minutes)
    store.execute("UPDATE patient_visits SET stage = 'closed',"
                  " treated_day = ?, closed_day = ?,"
                  " medication_item_id = ? WHERE visit_id = ?",
                  (day_index, day_index,
                   item["id"] if item else None, visit["visit_id"]))
    _treatment_record(store, visit, "life_stage_care"
                      if visit["visit_type"] != "follow_up"
                      else "follow_up_review",
                      day_index, game_minutes, doctor=doctor,
                      medication_item_id=item["id"] if item else None)


# -- monthly: budgets, procurement, life-stage registration --------------

def monthly_pass(store, data, month_index, game_minutes):
    """Budget authority recorded per facility; medication
    procurement from the market pool against that authority,
    through the ledger, capped so spend never exceeds it."""
    hcfg = cfg(data)
    out = {}
    for fac in store.rows("SELECT * FROM healthcare_facilities"
                          " WHERE active = 1 ORDER BY facility_id"):
        fid = fac["facility_id"]
        tcfg = hcfg["facility_types"][fac["facility_type"]]
        budget_id = f"HB-{fid}-{month_index}"
        if store.row("SELECT 1 FROM healthcare_budgets WHERE"
                     " budget_id = ?", (budget_id,)) is None:
            store.insert("healthcare_budgets", budget_id=budget_id,
                         facility_id=fid, month_index=month_index,
                         allocated_ncr=tcfg["monthly_budget_ncr"])
        budget = store.row("SELECT * FROM healthcare_budgets WHERE"
                           " budget_id = ?", (budget_id,))
        remaining = budget["allocated_ncr"] - budget["procurement_ncr"]
        spent, ledger_ids = 0, json.loads(budget["ledger_ids"])
        for item in hcfg["medications"]["items"]:
            need = item["target_stock"] - _stock(store, fid, item["id"])
            if need <= 0:
                continue
            cost = need * item["procurement_ncr_per_unit"]
            pay = min(cost, remaining - spent)
            units = pay // item["procurement_ncr_per_unit"]
            if units <= 0:
                continue
            amount = units * item["procurement_ncr_per_unit"]
            lid = store.transfer(
                FUNDING_ACCOUNT, "SYS-MARKET", amount,
                "medical_procurement", game_minutes,
                note=f"{fid} procurement {item['id']} x{units}",
                transfer_key=f"medproc:{fid}:{item['id']}:{month_index}",
                event_ref=budget_id)
            if lid is not None:
                ledger_ids.append(lid)
            store.execute("UPDATE medical_inventory SET quantity ="
                          " quantity + ? WHERE facility_id = ?"
                          " AND item_id = ?", (units, fid, item["id"]))
            rid = store.next_id("PH", "pharmacy_records", "record_id")
            store.insert("pharmacy_records", record_id=rid,
                         facility_id=fid, item_id=item["id"],
                         change=units, reason="procurement",
                         month_index=month_index,
                         game_minutes=game_minutes)
            spent += amount
        seen = store.row("SELECT COUNT(*) AS n FROM patient_visits"
                         " WHERE facility_id = ? AND treated_day"
                         " IS NOT NULL AND registered_day >= ?",
                         (fid, (month_index - 1) * 30))["n"]
        store.execute("UPDATE healthcare_budgets SET procurement_ncr"
                      " = procurement_ncr + ?, patients_seen = ?,"
                      " ledger_ids = ? WHERE budget_id = ?",
                      (spent, seen, json.dumps(ledger_ids), budget_id))
        out[fid] = {"allocated_ncr": budget["allocated_ncr"],
                    "procurement_ncr": budget["procurement_ncr"] + spent}
    return out


def register_life_stage_care(store, data, month_index, game_minutes):
    """Life-stage care pathways (config): births recorded in the
    month's life events produce maternal + infant care visits;
    citizens with a chronic profile get a monthly review; enrolled
    children get a health check in exam terms. All register at the
    citizen's own city facility and run through the daily queue.
    Returns the number of visits registered."""
    from . import health as health_mod
    count = 0
    by_city = facility_by_city(store)
    if not by_city:
        return 0
    day_index = game_minutes // 1440
    month_start = (month_index - 1) * 1440 * 30
    # Birth-related care: one visit for the mother (the kit covers
    # mother + infant care in this model), from the month's real
    # childbirth life events.
    for ev in store.rows("SELECT character_id FROM life_events WHERE"
                         " event_type = 'childbirth' AND game_minutes"
                         " >= ? AND game_minutes < ?",
                         (month_start, game_minutes)):
        fac = facility_for_character(store, data, ev["character_id"])
        if fac:
            register_visit(store, ev["character_id"],
                           fac["facility_id"], "birth_care", day_index,
                           game_minutes)
            count += 1
    # Elderly / chronic long-term care: a monthly review for every
    # citizen carrying a chronic profile.
    for prof in store.rows("SELECT character_id FROM health_profiles"
                           " WHERE chronic = 1"):
        cid = prof["character_id"]
        char = store.row("SELECT died_at_game_minutes FROM characters"
                         " WHERE character_id = ?", (cid,))
        if char and char["died_at_game_minutes"] is None:
            fac = facility_for_character(store, data, cid)
            if fac:
                register_visit(store, cid, fac["facility_id"],
                               "chronic_review", day_index, game_minutes)
                count += 1
    # Child health checks in exam terms.
    ecfg = data.education_health_config["education"]
    if month_index % ecfg["calendar"]["exam_every_months"] == 0:
        for rec in store.rows("SELECT character_id, institution_id"
                              " FROM education_records WHERE status ="
                              " 'enrolled' AND programme = 'school'"):
            fac = facility_for_character(store, data,
                                         rec["character_id"])
            if fac:
                register_visit(store, rec["character_id"],
                               fac["facility_id"], "child_check",
                               day_index, game_minutes)
                count += 1
    return count
