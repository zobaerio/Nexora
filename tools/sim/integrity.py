"""Session 05 Unit 12 — Corruption & Accountability.

Accountability here is arithmetic, not theatre:

- The monthly audit RE-RUNS the Session 04 reconciliation over
  the government accounts (finance.verify_conservation and
  finance.ledger_sum_check) and writes the outcome to the
  audits table under the Auditor General's name. A clean audit
  says zero discrepancies because the check found zero.
- Conflict of interest is a data join: office holders who own
  Session 04 businesses are flagged from the records — the
  flag is a record to manage, not an accusation of wrongdoing.
- Whistleblower reports are accepted from citizens; an
  investigation re-checks the reported account's ledger sums.
  A disciplinary outcome is recorded ONLY when the check finds
  a real discrepancy — otherwise the report closes as
  unsubstantiated, on the record.
- The integrity index is 100 minus a configured penalty per
  measured discrepancy. Nothing in this module invents
  corruption events.
"""
import json

from . import finance
from . import government as gov

GOVERNMENT_ACCOUNTS = ["SYS-CITY", "SYS-TREASURY-RUPSHA",
                       "SYS-TREASURY-SHIBNAGAR", "SYS-EXTERNAL"]


def _account_position(store, account):
    """(stored cache, ledger sum) for one account — the same
    arithmetic Store.ledger_sum_check applies to every row."""
    inn = store.row("SELECT COALESCE(SUM(amount), 0) AS s FROM"
                    " economy_ledger WHERE to_character_id = ?",
                    (account,))["s"]
    out = store.row("SELECT COALESCE(SUM(amount), 0) AS s FROM"
                    " economy_ledger WHERE from_character_id = ?",
                    (account,))["s"]
    return store.balance(account), inn - out


def audit_government(store, data, game_minutes, auditor_id=None):
    """Run the Session 04 reconciliation (whole-ledger
    double-entry verification plus a per-account cache check
    over the government accounts) and record the audit.
    Returns the audit's numbers."""
    if auditor_id is None:
        office = gov.office_holder(store, "auditor_general",
                                   "GOV-AUDIT")
        auditor_id = office["holder_character_id"] if office \
            else None
    violations = finance.verify_conservation(store)
    discrepancies = [{"violation": v} for v in violations]
    checks = {}
    for account in GOVERNMENT_ACCOUNTS:
        stored, ledger = _account_position(store, account)
        checks[account] = {"stored_ncr": stored,
                           "ledger_ncr": ledger,
                           "ok": stored == ledger}
        if stored != ledger:
            discrepancies.append({"account": account,
                                  "stored": stored,
                                  "ledger": ledger})
    aid = store.next_id("AU", "audits", "audit_id")
    penalty = data.government_config["integrity"][
        "discrepancy_penalty_points"]
    month_index = game_minutes // 43200
    store.insert(
        "audits", audit_id=aid, scope="government_accounts",
        month_index=month_index,
        discrepancies=json.dumps(discrepancies, sort_keys=True),
        discrepancy_count=len(discrepancies),
        result="clean" if not discrepancies
        else "discrepancies_found",
        integrity_index=max(0, 100 - penalty * len(discrepancies)),
        auditor_character_id=auditor_id,
        game_minutes=game_minutes)
    gov.log_event(store, "audit_completed", auditor_id,
                  {"audit_id": aid,
                   "discrepancies": len(discrepancies)},
                  game_minutes)
    return {"audit_id": aid, "discrepancies": discrepancies,
            "checks": checks}


def conflict_of_interest_scan(store, game_minutes):
    """Flag office holders who own businesses — from the data."""
    flagged = []
    for row in store.rows(
            "SELECT o.office_id, o.holder_character_id,"
            " o.institution_id, o.title, b.business_id FROM"
            " offices o JOIN businesses b ON"
            " b.owner_character_id = o.holder_character_id"
            " WHERE o.status = 'active' AND"
            " o.holder_character_id IS NOT NULL AND b.status IN"
            " ('active', 'distressed') ORDER BY"
            " o.holder_character_id, b.business_id"):
        existing = store.row(
            "SELECT * FROM coi_records WHERE character_id = ?"
            " AND business_id = ? AND status = 'open'",
            (row["holder_character_id"], row["business_id"]))
        if existing:
            continue
        cid = store.next_id("COI", "coi_records", "coi_id")
        store.insert(
            "coi_records", coi_id=cid,
            character_id=row["holder_character_id"],
            office_id=row["office_id"],
            business_id=row["business_id"], status="open",
            detected_at_game_minutes=game_minutes)
        flagged.append(cid)
    return flagged


def file_report(store, reporter_id, subject, game_minutes):
    rid = store.next_id("IR", "integrity_reports", "report_id")
    store.insert("integrity_reports", report_id=rid,
                 reporter_character_id=reporter_id,
                 subject_character_id=subject,
                 allegation="citizen report — unverified claim",
                 status="open",
                 created_at_game_minutes=game_minutes)
    return rid


def investigate_report(store, data, report_id, game_minutes):
    """An investigation is a ledger check on the reported
    subject account. Discipline requires a measured
    discrepancy; anything else closes unsubstantiated."""
    rep = store.row("SELECT * FROM integrity_reports WHERE"
                    " report_id = ?", (report_id,))
    if rep is None or rep["status"] != "open":
        raise ValueError(f"report {report_id} is not open")
    subject = rep["subject_character_id"]
    outcome = "unsubstantiated"
    detail = {}
    if subject in GOVERNMENT_ACCOUNTS or subject.startswith("P"):
        stored, ledger = _account_position(store, subject)
        detail = {"check": "account_reconciliation",
                  "stored_ncr": stored, "ledger_ncr": ledger}
        if stored != ledger:
            outcome = "discrepancy_confirmed"
    else:
        detail = {"check": "none",
                  "basis": "subject is not an auditable account"}
    store.execute("UPDATE integrity_reports SET status = ?,"
                  " outcome = ?, closed_at_game_minutes = ?"
                  " WHERE report_id = ?",
                  ("closed", json.dumps(
                      {"outcome": outcome, **detail},
                      sort_keys=True), game_minutes, report_id))
    gov.log_event(store, "integrity_report_closed", None,
                  {"report_id": report_id, "outcome": outcome},
                  game_minutes)
    return {"report_id": report_id, "outcome": outcome,
            **detail}


def integrity_index(store, data):
    """100 minus the configured penalty per audit discrepancy,
    floored at 0. Measured only."""
    audit = store.row("SELECT * FROM audits ORDER BY audit_id"
                      " DESC LIMIT 1")
    if audit is None:
        return 100
    return audit["integrity_index"]


def monthly_pass(store, data, rng, month_index, game_minutes):
    if not gov.is_setup(store):
        return None
    audit = audit_government(store, data, game_minutes)
    coi = conflict_of_interest_scan(store, game_minutes)
    closed = []
    for rep in store.rows("SELECT * FROM integrity_reports WHERE"
                          " status = 'open' ORDER BY report_id"):
        closed.append(investigate_report(store, data,
                                         rep["report_id"],
                                         game_minutes))
    return {"audit": audit["audit_id"],
            "discrepancies": len(audit["discrepancies"]),
            "coi_flagged": coi, "reports_closed": closed,
            "integrity_index": integrity_index(store, data)}
