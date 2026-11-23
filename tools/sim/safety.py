"""Session 05 Unit 11 — Law Enforcement & Public Safety.

The police are an institution staffed by real police_officer
citizens (recruited through the Session 04/05 labour machinery
into GOV-POLICE-*). Incidents emerge ONLY from sim records:

- escalated Session 02 conflicts become public-order incidents;
- traffic accidents arise from measured risk: storm days in
  the weather record crossed with degraded road-segment
  condition in the affected city (a configured SIM MODEL rate
  applied to measured inputs — no storms or sound roads means
  no accidents);
- Session 04 loan defaults become debt incidents for the
  record (the court case itself is filed by justice).

There is no arbitrary crime generation anywhere in this
module: every incident row names the record it came from.
Processing is report -> investigation (by a named officer of
the city's police institution) -> referral to court or
closure, and the statistics are counts over these records —
they feed citizens' safety experience in politics.update_opinion.
"""
import json

from . import government as gov

CONFLICT_REFERRAL_LEVEL = 40


def _police_institution(city_id):
    return {"rupsha_city": "GOV-POLICE-RUPSHA",
            "shibnagar_town": "GOV-POLICE-SHIBNAGAR"}.get(city_id)


def _officers(store, data, city_id):
    """The city's police workforce from the records: Session 05
    civil-service officers of the police institution, plus the
    Session 04 civic police establishment (police_officer
    employments paid by SYS-CITY) resident in the city."""
    ids = {r["character_id"] for r in store.rows(
        "SELECT cs.character_id FROM civil_service cs"
        " WHERE cs.institution_id = ? AND cs.status = 'active'",
        (_police_institution(city_id),))}
    for emp in store.rows(
            "SELECT character_id FROM employments WHERE"
            " profession_id = 'police_officer' AND"
            " employer_character_id = 'SYS-CITY' AND"
            " ended_at_game_minutes IS NULL"):
        if gov.city_of_character(store, data,
                                 emp["character_id"]) == city_id:
            ids.add(emp["character_id"])
    return [{"character_id": cid} for cid in sorted(ids)]


def _open_incident(store, incident_type, city_id, source_kind,
                   source_ref, description, game_minutes):
    existing = store.row("SELECT * FROM incidents WHERE"
                         " source_kind = ? AND source_ref = ?",
                         (source_kind, source_ref))
    if existing:
        return existing["incident_id"]
    iid = store.next_id("IN", "incidents", "incident_id")
    store.insert("incidents", incident_id=iid,
                 incident_type=incident_type, city_id=city_id,
                 source_kind=source_kind, source_ref=source_ref,
                 description=json.dumps(description, sort_keys=True),
                 status="reported",
                 created_at_game_minutes=game_minutes)
    return iid


def intake_incidents(store, data, rng, month_index, game_minutes):
    """Create this month's incidents from the records — and
    nothing else."""
    from . import conflicts as conflicts_mod
    from . import lost_items as lost_items_mod
    created = []
    # Escalated conflicts (Session 02) -> public-order incidents.
    for conf in store.rows("SELECT * FROM conflict_records WHERE"
                           " status = 'escalated' ORDER BY"
                           " conflict_id"):
        city = gov.city_of_character(store, data,
                                     conf["a_character_id"]) \
            or "rupsha_city"
        iid = _open_incident(
            store, "public_order", city, "conflict",
            conf["conflict_id"],
            {"conflict_id": conf["conflict_id"],
             "cause": conf["cause"],
             "conflict_level": conflicts_mod.pair_conflict_level(
                 store, conf["a_character_id"],
                 conf["b_character_id"])}, game_minutes)
        created.append(iid)
    # Loan defaults -> recorded incidents (court handles the case).
    for loan in store.rows("SELECT * FROM loans WHERE status ="
                           " 'defaulted' ORDER BY loan_id"):
        city = gov.city_of_character(
            store, data, loan["borrower_character_id"]) \
            or "rupsha_city"
        iid = _open_incident(
            store, "debt_default", city, "loan", loan["loan_id"],
            {"loan_id": loan["loan_id"],
             "outstanding_ncr": loan["outstanding_ncr"]},
            game_minutes)
        created.append(iid)
    # Traffic accidents: measured risk only. Storm days this
    # month x degraded segments in the city x configured rate.
    cfg = data.government_config["police"]
    since_day = (month_index - 1) * 30
    for city_id in ("rupsha_city", "shibnagar_town"):
        storms = store.row(
            "SELECT COUNT(*) AS n FROM daily_weather WHERE"
            " day_index >= ? AND day_index < ? AND preset_id ="
            " 'storm'", (since_day, since_day + 30))["n"]
        if storms == 0:
            continue
        degraded = store.rows(
            "SELECT * FROM road_segments WHERE city_id = ? AND"
            " condition < 60 ORDER BY segment_id",
            (city_id,))
        expected = 0.0
        for seg in degraded:
            expected += storms * cfg[
                "accident_rate_per_storm_day_per_city"] \
                * (60 - seg["condition"]) / 100 \
                * cfg["accident_condition_factor"]
        whole = int(expected)
        draw = rng.stream("traffic", city_id, month_index).random()
        if draw < expected - whole:
            whole += 1
        for i in range(whole):
            seg = degraded[i % len(degraded)]
            ref = f"traffic:{city_id}:{month_index}:{i}"
            iid = _open_incident(
                store, "traffic_accident", city_id, "road_risk",
                ref, {"segment_id": seg["segment_id"],
                      "condition": seg["condition"],
                      "storm_days": storms,
                      "basis": "measured storm days x degraded"
                      " segment condition (SIM MODEL rate)"},
                game_minutes)
            created.append(iid)
            # Queue 15 Unit CY: BX event E1 — a traveller on the
            # segment can lose a carried thing. One loss per incident
            # at most; silent at the default rate 0.
            lost_items_mod.commute_incident_losses(
                store, data, rng, iid, seg["segment_id"], month_index,
                game_minutes)
    return created


def process_incidents(store, data, game_minutes):
    """Investigate open incidents with the city's officers and
    refer sustained conflicts to the court."""
    from . import conflicts as conflicts_mod
    from . import justice as justice_mod
    outcomes = []
    for inc in store.rows("SELECT * FROM incidents WHERE status"
                          " IN ('reported', 'investigating')"
                          " ORDER BY incident_id"):
        officers = _officers(store, data, inc["city_id"])
        if not officers:
            continue  # no police staffed: the incident waits
        officer = officers[len(outcomes) % len(officers)][
            "character_id"]
        store.execute("UPDATE incidents SET status ="
                      " 'investigating', officer_character_id = ?"
                      " WHERE incident_id = ?",
                      (officer, inc["incident_id"]))
        outcome = "closed"
        detail = {}
        if inc["incident_type"] == "public_order":
            conf = store.row("SELECT * FROM conflict_records"
                             " WHERE conflict_id = ?",
                             (inc["source_ref"],))
            level = conflicts_mod.pair_conflict_level(
                store, conf["a_character_id"],
                conf["b_character_id"]) if conf else 0
            if conf and level >= CONFLICT_REFERRAL_LEVEL:
                case_id = justice_mod.file_case(
                    store, "conflict", "incident",
                    inc["incident_id"], conf["a_character_id"],
                    conf["b_character_id"],
                    {"claim": "escalated conflict referred by"
                     " police", "conflict_id": conf["conflict_id"],
                     "conflict_level": level}, game_minutes)
                outcome = "referred_to_court"
                detail = {"case_id": case_id,
                          "conflict_level": level}
            else:
                detail = {"conflict_level": level,
                          "basis": "below referral threshold;"
                          " recorded and closed"}
        elif inc["incident_type"] == "debt_default":
            outcome = "referred_to_court"
            detail = {"basis": "civil debt: court case filed by"
                      " justice intake from the loan record"}
        elif inc["incident_type"] == "traffic_accident":
            detail = {"basis": "road-risk accident recorded;"
                      " feeds infrastructure decisions"}
        store.execute("UPDATE incidents SET status = ?, outcome"
                      " = ? WHERE incident_id = ?",
                      (outcome, json.dumps(detail, sort_keys=True),
                       inc["incident_id"]))
        outcomes.append({"incident_id": inc["incident_id"],
                         "officer": officer, "outcome": outcome})
    return outcomes


def safety_stats(store, city_id=None, since_game_minutes=0):
    """Counts over the incident records — the only safety
    numbers the sim ever reports."""
    where = "WHERE created_at_game_minutes >= ?"
    params = [since_game_minutes]
    if city_id:
        where += " AND city_id = ?"
        params.append(city_id)
    rows = store.rows(
        f"SELECT incident_type, COUNT(*) AS n FROM incidents"
        f" {where} GROUP BY incident_type", tuple(params))
    total = sum(r["n"] for r in rows)
    return {"total": total,
            "by_type": {r["incident_type"]: r["n"] for r in rows}}


def monthly_pass(store, data, rng, month_index, game_minutes):
    if not gov.is_setup(store):
        return None
    created = intake_incidents(store, data, rng, month_index,
                               game_minutes)
    outcomes = process_incidents(store, data, game_minutes)
    return {"created": created, "processed": outcomes}
