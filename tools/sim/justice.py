"""Session 05 Units 09+10 — Law & Legislation, and the Judiciary.

Laws are data: a kind, an effect value, a debate record, a vote.
The constitution and the legal bounds live in
data/government-config.json. Enacted laws change real behaviour
through three hooks that read the law book every time they act:

- sales tax: engine._pay_purchase settles purchases at the
  enacted rate instead of the configured SIM MODEL rate;
- import tariff: trade.settle_trade prices tariffs at the
  enacted rate (before diplomacy's agreement delta);
- wage floor: labour/admin vacancy posting uplifts entry wages
  by the enacted percentage;
- migration openness: distribution.monthly_migration scales its
  monthly cap by the enacted factor.

Each hook defaults to exactly the pre-Session-05 behaviour when
no law is enacted — the deltas are test-proven, not asserted.

The judiciary hears cases that arise from real sim disputes:
escalated Session 02 conflicts (referred by the police), Session
04 loan defaults, and recorded business wage shortfalls. The
allegation and the finding are different columns on purpose —
an allegation is a claim; only a judgment, written by a judge
whose office carries judge_case authority, establishes a
finding. Evidence is the underlying record itself (the loan
row, the conflict record, the business event). Remedies execute
through the ledger. One appeal is allowed, heard by a different
judge under a stricter evidence threshold.
"""
import json

from . import government as gov

LAW_KINDS = {
    "sales_tax": ("percent", "sales_tax_percent_bounds",
                  "services"),
    "wage_floor": ("uplift_percent",
                   "wage_floor_uplift_percent_bounds", "welfare"),
    "tariff": ("percent", "import_tariff_percent_bounds",
               "development"),
    "migration_openness": ("factor", "migration_openness_bounds",
                           "economy"),
    # Session 08: the environmental hook — an enacted emission
    # limit measurably reduces the industry component of the
    # environment layer's air-pollution index and speeds
    # vegetation recovery (environment.effective_emission_
    # reduction reads the law book like the hooks above).
    "emission_limit": ("reduction_percent",
                       "emission_limit_percent_bounds", "development"),
}
CONFLICT_FAULT_LEVEL = 40        # social_profiles conflict level
APPEAL_FAULT_LEVEL = 60          # stricter threshold on appeal
RESTITUTION_PER_LEVEL = 50       # SIM MODEL remedy scale


# -- legislation -------------------------------------------------------------

def propose_law(store, data, kind, value, actor_id, game_minutes,
                title=None):
    """Propose a law. The proposer must hold office (a citizen
    at large cannot legislate), and the value must sit inside
    the constitution's configured bounds for that kind."""
    if kind not in LAW_KINDS:
        raise ValueError(f"unknown law kind {kind}")
    if not gov.offices_of(store, actor_id):
        raise PermissionError(
            f"{actor_id} holds no office and cannot propose laws")
    _field, bounds_key, _dim = LAW_KINDS[kind]
    lo, hi = data.government_config["laws"][bounds_key]
    if not (lo <= value <= hi):
        raise ValueError(
            f"{kind} value {value} outside legal bounds"
            f" [{lo}, {hi}]")
    field = LAW_KINDS[kind][0]
    lid = store.next_id("LW", "laws", "law_id")
    store.insert(
        "laws", law_id=lid,
        title=title or f"{kind.replace('_', ' ').title()} Act",
        kind=kind, effect=json.dumps({field: value}),
        proposed_by=actor_id, status="proposed",
        created_at_game_minutes=game_minutes)
    gov.log_event(store, "law_proposed", actor_id,
                  {"law_id": lid, "kind": kind, "value": value},
                  game_minutes)
    return lid


def debate_law(store, data, law_id, game_minutes):
    """Recorded party positions, derived from each party's
    configured stance on the law kind's dimension."""
    law = store.row("SELECT * FROM laws WHERE law_id = ?",
                    (law_id,))
    if law is None or law["status"] not in ("proposed", "debated"):
        raise ValueError(f"law {law_id} cannot be debated")
    _field, _bounds, dimension = LAW_KINDS[law["kind"]]
    positions = []
    for p in store.rows("SELECT * FROM parties WHERE status ="
                        " 'registered' ORDER BY party_id"):
        stance = json.loads(p["stances"]).get(dimension, 50)
        position = "support" if stance >= 55 else \
            "oppose" if stance <= 40 else "abstain"
        positions.append({"party_id": p["party_id"],
                          "dimension": dimension,
                          "stance": stance, "position": position})
    store.execute("UPDATE laws SET status = 'debated', debate = ?"
                  " WHERE law_id = ?",
                  (json.dumps(positions), law_id))
    gov.log_event(store, "law_debated", law["proposed_by"],
                  {"law_id": law_id, "positions": positions},
                  game_minutes)
    return positions


def vote_law(store, data, law_id, game_minutes):
    """MPs vote their party's debated position (independents by
    their own stance). A majority enacts; the law takes effect
    from the next month. Enactment is Parliament's act — it
    requires a seated parliament."""
    from . import politics as politics_mod
    law = store.row("SELECT * FROM laws WHERE law_id = ?",
                    (law_id,))
    if law is None:
        raise ValueError(f"unknown law {law_id}")
    if law["status"] == "proposed":
        debate_law(store, data, law_id, game_minutes)
        law = store.row("SELECT * FROM laws WHERE law_id = ?",
                        (law_id,))
    positions = {p["party_id"]: p["position"]
                 for p in json.loads(law["debate"] or "[]")}
    mps = store.rows("SELECT * FROM offices WHERE institution_id"
                     " = 'GOV-PARLIAMENT' AND title = 'mp' AND"
                     " status = 'active'")
    if not mps:
        raise ValueError("no parliament is seated")
    votes_for = votes_against = 0
    for mp in mps:
        pid = politics_mod.party_of(store, mp["holder_character_id"])
        position = positions.get(pid, "abstain")
        if position == "support":
            votes_for += 1
        elif position == "oppose":
            votes_against += 1
    enacted = votes_for > votes_against
    month_index = game_minutes // 43200
    store.execute(
        "UPDATE laws SET status = ?, votes_for = ?,"
        " votes_against = ?, effective_month = ?,"
        " enacted_at_game_minutes = ? WHERE law_id = ?",
        ("enacted" if enacted else "rejected", votes_for,
         votes_against, month_index + 1 if enacted else None,
         game_minutes if enacted else None, law_id))
    gov.log_event(store, "law_enacted" if enacted
                  else "law_rejected", law["proposed_by"],
                  {"law_id": law_id, "kind": law["kind"],
                   "votes_for": votes_for,
                   "votes_against": votes_against}, game_minutes)
    return {"enacted": enacted, "votes_for": votes_for,
            "votes_against": votes_against}


def _enacted_value(store, kind, field):
    month = (store.world()["game_minutes"] // 43200)
    row = store.row(
        "SELECT effect FROM laws WHERE kind = ? AND status ="
        " 'enacted' AND effective_month <= ? ORDER BY"
        " enacted_at_game_minutes DESC, law_id DESC LIMIT 1",
        (kind, month))
    if row is None:
        return None
    return json.loads(row["effect"]).get(field)


def effective_sales_tax_percent(store, data):
    v = _enacted_value(store, "sales_tax", "percent")
    if v is not None:
        return v
    return data.economy_config["tax_rules"]["sales_tax_percent"]


def effective_tariff_percent(store, data):
    v = _enacted_value(store, "tariff", "percent")
    if v is not None:
        return v
    return data.economy_config["tax_rules"]["import_tariff_percent"]


def wage_floor_uplift_percent(store, data):
    v = _enacted_value(store, "wage_floor", "uplift_percent")
    return v if v is not None else 0


def migration_openness(store, data):
    v = _enacted_value(store, "migration_openness", "factor")
    return v if v is not None else 1.0


def apply_wage_floor(store, data, wage):
    """The wage-floor hook used at vacancy posting time."""
    if not gov.is_setup(store):
        return wage
    uplift = wage_floor_uplift_percent(store, data)
    if uplift:
        return int(round(wage * (1 + uplift / 100)))
    return wage


# -- judiciary -----------------------------------------------------------------

def file_case(store, case_type, source_kind, source_ref,
              plaintiff_id, defendant_id, allegation,
              game_minutes):
    """File a case from a real dispute record. Idempotent per
    source (UNIQUE): re-filing returns the existing case. The
    allegation is stored as a claim — the finding column stays
    NULL until a judge writes it."""
    existing = store.row("SELECT * FROM court_cases WHERE"
                         " source_kind = ? AND source_ref = ?",
                         (source_kind, source_ref))
    if existing:
        return existing["case_id"]
    cid = store.next_id("CC", "court_cases", "case_id")
    store.insert(
        "court_cases", case_id=cid, case_type=case_type,
        source_kind=source_kind, source_ref=source_ref,
        plaintiff_id=plaintiff_id, defendant_id=defendant_id,
        allegation=json.dumps(allegation, sort_keys=True),
        status="filed", created_at_game_minutes=game_minutes)
    return cid


def _judges(store):
    return store.rows(
        "SELECT holder_character_id FROM offices WHERE"
        " institution_id = 'GOV-COURT' AND status = 'active'"
        " AND holder_character_id IS NOT NULL ORDER BY office_id")


def assign_judge(store, case_id, exclude=None):
    judges = [j["holder_character_id"] for j in _judges(store)
              if j["holder_character_id"] != exclude]
    if not judges:
        return None
    heard = store.row("SELECT COUNT(*) AS n FROM court_cases"
                      " WHERE status IN ('judged', 'closed')")["n"]
    judge = judges[heard % len(judges)]
    store.execute("UPDATE court_cases SET judge_character_id = ?"
                  " WHERE case_id = ?", (judge, case_id))
    return judge


def _evidence_for(store, case):
    """The underlying record IS the evidence. Returns
    (liable, basis, remedy_due)."""
    if case["case_type"] == "debt_default":
        loan = store.row("SELECT * FROM loans WHERE loan_id = ?",
                         (case["source_ref"],))
        if loan is None:
            return False, ["loan record missing"], 0
        liable = loan["outstanding_ncr"] > 0 \
            and loan["status"] == "defaulted"
        return liable, [{"loan_id": loan["loan_id"],
                         "outstanding_ncr": loan["outstanding_ncr"],
                         "missed_payments":
                         loan["missed_payments"]}], \
            loan["outstanding_ncr"]
    if case["case_type"] == "commercial_dispute":
        ev = store.row("SELECT * FROM business_events WHERE"
                       " event_id = ?", (case["source_ref"],))
        if ev is None:
            return False, ["business event missing"], 0
        details = json.loads(ev["details"])
        due = details.get("due_ncr", 0) - details.get("paid_ncr", 0)
        return due > 0, [{"event_id": ev["event_id"],
                          "shortfall_ncr": due}], due
    if case["case_type"] == "conflict":
        conf = store.row("SELECT * FROM conflict_records WHERE"
                         " conflict_id = ?", (case["source_ref"],))
        if conf is None:
            return False, ["conflict record missing"], 0
        from . import conflicts as conflicts_mod
        level = conflicts_mod.pair_conflict_level(
            store, conf["a_character_id"], conf["b_character_id"])
        threshold = APPEAL_FAULT_LEVEL if case["appeal_of"] \
            else CONFLICT_FAULT_LEVEL
        return level >= threshold, [{"conflict_id":
                                     conf["conflict_id"],
                                     "conflict_level": level,
                                     "threshold": threshold}], \
            int(level * RESTITUTION_PER_LEVEL)
    return False, ["unknown case type"], 0


def _execute_remedy(store, case, amount, game_minutes):
    """Execute a judgment's remedy through the ledger and keep
    the underlying book (the loan row) consistent. Returns the
    amount actually moved."""
    if amount <= 0:
        return 0
    defendant = case["defendant_id"]
    if case["case_type"] == "debt_default":
        available = max(0, store.balance(defendant) - 500)
        pay = min(amount, available)
        if pay > 0:
            store.transfer(
                defendant, "SYS-BANK", pay, "loan_repayment",
                game_minutes, note="court-ordered repayment"
                f" ({case['case_id']})",
                transfer_key=f"court:{case['case_id']}",
                event_ref=f"case:{case['case_id']}")
            loan = store.row("SELECT * FROM loans WHERE loan_id"
                             " = ?", (case["source_ref"],))
            outstanding = loan["outstanding_ncr"] - pay
            store.execute(
                "UPDATE loans SET outstanding_ncr = ?, status = ?"
                " WHERE loan_id = ?",
                (outstanding,
                 "repaid" if outstanding <= 0 else "defaulted",
                 case["source_ref"]))
        return pay
    if case["case_type"] == "commercial_dispute":
        ev = store.row("SELECT * FROM business_events WHERE"
                       " event_id = ?", (case["source_ref"],))
        business_id = ev["business_id"] if ev else None
        available = store.business_balance(business_id) \
            if business_id else 0
        pay = min(amount, max(0, available))
        if pay > 0:
            store.transfer(
                None, case["plaintiff_id"], pay, "wage",
                game_minutes, note="court-ordered wage payment"
                f" ({case['case_id']})",
                transfer_key=f"court:{case['case_id']}",
                event_ref=f"case:{case['case_id']}",
                from_business_id=business_id)
        return pay
    # conflict restitution, citizen to citizen
    available = max(0, store.balance(defendant) - 500)
    pay = min(amount, available)
    if pay > 0:
        store.transfer(
            defendant, case["plaintiff_id"], pay, "restitution",
            game_minutes, note=f"court-ordered restitution"
            f" ({case['case_id']})",
            transfer_key=f"court:{case['case_id']}",
            event_ref=f"case:{case['case_id']}")
    return pay


def hear_case(store, data, case_id, game_minutes, execute=True):
    """Hear a filed case: the assigned judge must hold judicial
    authority (checked, not assumed), the finding is written
    from the evidence record, and a sustained claim's remedy
    executes through the ledger. Appeal hearings pass
    execute=False — the original remedy stands unless the
    appeal overturns it (see appeal_case)."""
    case = store.row("SELECT * FROM court_cases WHERE case_id = ?",
                     (case_id,))
    if case is None or case["status"] not in ("filed", "appealed"):
        raise ValueError(f"case {case_id} is not awaiting hearing")
    judge = case["judge_character_id"] or assign_judge(store,
                                                       case_id)
    if judge is None:
        raise ValueError("no judge is seated")
    gov.require_authority(store, judge, "judge_case")
    liable, basis, remedy_due = _evidence_for(store, case)
    executed = _execute_remedy(store, case, remedy_due,
                                game_minutes) \
        if liable and execute else 0
    finding = {"liable": liable, "basis": basis,
               "judge": judge,
               "standard": "appeal" if case["appeal_of"]
               else "first_instance"}
    judgment = {"remedy_type": "payment" if liable else "none",
                "remedy_due_ncr": remedy_due if liable else 0,
                "remedy_executed_ncr": executed}
    store.execute(
        "UPDATE court_cases SET status = 'judged', finding = ?,"
        " judgment = ?, remedy_ncr = ? WHERE case_id = ?",
        (json.dumps(finding, sort_keys=True),
         json.dumps(judgment, sort_keys=True), executed, case_id))
    gov.log_event(store, "case_judged", judge,
                  {"case_id": case_id, "case_type":
                   case["case_type"], "liable": liable,
                   "remedy_ncr": executed}, game_minutes)
    return {"case_id": case_id, "liable": liable,
            "remedy_ncr": executed, "judge": judge}


def appeal_case(store, data, case_id, actor_id, game_minutes):
    """One appeal, by the losing party only, heard by a different
    judge under the stricter threshold. The appeal is its own
    case row linked to the original; if it overturns, the
    executed remedy is refunded through the ledger."""
    original = store.row("SELECT * FROM court_cases WHERE case_id"
                         " = ?", (case_id,))
    if original is None or original["status"] != "judged":
        raise ValueError(f"case {case_id} cannot be appealed")
    if original["appeal_of"]:
        raise ValueError("an appeal judgment is final")
    finding = json.loads(original["finding"] or "{}")
    loser = original["defendant_id"] if finding.get("liable") \
        else original["plaintiff_id"]
    if actor_id != loser:
        raise PermissionError(
            "only the losing party may appeal")
    aid = file_case(store, original["case_type"], "appeal",
                    case_id, original["plaintiff_id"],
                    original["defendant_id"],
                    {"appeal_of": case_id,
                     "grounds": "evidence threshold review"},
                    game_minutes)
    store.execute("UPDATE court_cases SET appeal_of = ?, status"
                  " = 'appealed' WHERE case_id = ?", (case_id, aid))
    judge = assign_judge(store, aid,
                         exclude=original["judge_character_id"])
    if judge is None:
        raise ValueError("no second judge is seated")
    result = hear_case(store, data, aid, game_minutes,
                       execute=False)
    appeal_row = store.row("SELECT * FROM court_cases WHERE"
                           " case_id = ?", (aid,))
    appeal_finding = json.loads(appeal_row["finding"] or "{}")
    refunded = 0
    if appeal_finding.get("liable") and not finding.get("liable"):
        # Dismissal overturned: the remedy now executes, once,
        # under the appeal's own case id.
        _liable, _basis, remedy_due = _evidence_for(store,
                                                    appeal_row)
        executed = _execute_remedy(store, appeal_row, remedy_due,
                                   game_minutes)
        store.execute("UPDATE court_cases SET remedy_ncr = ?"
                      " WHERE case_id = ?", (executed, aid))
        result["remedy_ncr"] = executed
    if bool(appeal_finding.get("liable")) != bool(
            finding.get("liable")) and finding.get("liable"):
        # Overturned: unwind the original remedy.
        remedy = original["remedy_ncr"]
        if remedy > 0 and finding.get("liable"):
            if original["case_type"] == "debt_default":
                store.transfer(
                    "SYS-BANK", original["defendant_id"], remedy,
                    "court_refund", game_minutes,
                    note=f"appeal refund ({aid})",
                    transfer_key=f"appeal-refund:{aid}",
                    event_ref=f"case:{aid}")
                loan = store.row("SELECT * FROM loans WHERE"
                                 " loan_id = ?",
                                 (original["source_ref"],))
                if loan:
                    store.execute(
                        "UPDATE loans SET outstanding_ncr = ?,"
                        " status = 'defaulted' WHERE loan_id = ?",
                        (loan["outstanding_ncr"] + remedy,
                         original["source_ref"]))
                refunded = remedy
            else:
                payer = original["plaintiff_id"]
                available = max(0, store.balance(payer) - 500)
                pay = min(remedy, available)
                if pay > 0:
                    store.transfer(
                        payer, original["defendant_id"], pay,
                        "court_refund", game_minutes,
                        note=f"appeal refund ({aid})",
                        transfer_key=f"appeal-refund:{aid}",
                        event_ref=f"case:{aid}")
                refunded = pay
    store.execute("UPDATE court_cases SET status = 'closed',"
                  " closed_at_game_minutes = ? WHERE case_id = ?",
                  (game_minutes, aid))
    store.execute("UPDATE court_cases SET status = 'closed',"
                  " closed_at_game_minutes = ? WHERE case_id = ?",
                  (game_minutes, case_id))
    gov.log_event(store, "case_appealed", actor_id,
                  {"case_id": case_id, "appeal_id": aid,
                   "upheld": bool(appeal_finding.get("liable"))
                   == bool(finding.get("liable")),
                   "refunded_ncr": refunded}, game_minutes)
    return {"appeal_id": aid, **result, "refunded_ncr": refunded}


def intake_cases(store, data, game_minutes):
    """File this month's money-dispute cases from the records:
    defaulted loans and business wage shortfalls. (Conflicts
    reach the court through the police — see safety.py.)"""
    filed = []
    for loan in store.rows("SELECT * FROM loans WHERE status ="
                           " 'defaulted' ORDER BY loan_id"):
        cid = file_case(
            store, "debt_default", "loan", loan["loan_id"],
            "SYS-BANK", loan["borrower_character_id"],
            {"claim": "loan default",
             "outstanding_ncr": loan["outstanding_ncr"],
             "missed_payments": loan["missed_payments"]},
            game_minutes)
        filed.append(cid)
    since = game_minutes - 30 * 1440
    for ev in store.rows(
            "SELECT * FROM business_events WHERE event_type ="
            " 'wage_shortfall' AND game_minutes > ? ORDER BY"
            " event_id", (since,)):
        details = json.loads(ev["details"])
        cid = file_case(
            store, "commercial_dispute", "business_event",
            ev["event_id"], details.get("character_id"),
            store.row("SELECT owner_character_id FROM businesses"
                      " WHERE business_id = ?",
                      (ev["business_id"],))["owner_character_id"]
            if store.row("SELECT owner_character_id FROM"
                         " businesses WHERE business_id = ?",
                         (ev["business_id"],)) else None,
            {"claim": "unpaid wages",
             "due_ncr": details.get("due_ncr"),
             "paid_ncr": details.get("paid_ncr")}, game_minutes)
        filed.append(cid)
    return filed


def monthly_pass(store, data, rng, month_index, game_minutes):
    if not gov.is_setup(store):
        return None
    filed = intake_cases(store, data, game_minutes)
    heard = []
    for case in store.rows("SELECT * FROM court_cases WHERE"
                           " status = 'filed' ORDER BY case_id"):
        try:
            heard.append(hear_case(store, data, case["case_id"],
                                   game_minutes))
        except (ValueError, PermissionError):
            continue  # no bench seated yet: cases wait, recorded
    # Appeals: a losing party with a large remedy and the nerve
    # (risk tolerance) uses their one appeal — deterministic.
    appealed = []
    cfg = data.government_config["judiciary"]
    for case in store.rows("SELECT * FROM court_cases WHERE"
                           " status = 'judged' AND appeal_of IS"
                           " NULL ORDER BY case_id"):
        if case["remedy_ncr"] < cfg[
                "appeal_remedy_threshold_ncr"]:
            continue
        finding = json.loads(case["finding"] or "{}")
        loser = case["defendant_id"] if finding.get("liable") \
            else case["plaintiff_id"]
        prof = gov._profile(store, loser) if loser else {}
        if prof.get("risk_tolerance", 0) < 50:
            continue
        try:
            appealed.append(appeal_case(store, data,
                                        case["case_id"], loser,
                                        game_minutes))
        except (ValueError, PermissionError):
            continue
    return {"filed": filed, "heard": heard, "appealed": appealed}
