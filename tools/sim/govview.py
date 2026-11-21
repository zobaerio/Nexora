"""Session 05 Unit 16 — Government Observatory (data layer).

Read-only views over the real Session 05 records, for the CLI
(--government, --election, --policy, --budget, --court,
--diplomacy) and for tests. Every number here is a query over
the tables the other units wrote — nothing is computed from
assumptions, and nothing is presented that the records do not
contain. No dashboard, no fabrication: a data layer only.
"""
import json

from . import government as gov


def overview(store, data=None):
    if not gov.is_setup(store):
        return {"government": "not established"}
    country = store.row("SELECT * FROM countries LIMIT 1")
    offices = []
    for o in store.rows("SELECT * FROM offices WHERE status ="
                        " 'active' ORDER BY institution_id, title"):
        holder = o["holder_character_id"]
        name = None
        if holder:
            row = store.row("SELECT display_name FROM characters"
                            " WHERE character_id = ?", (holder,))
            name = row["display_name"] if row else None
        offices.append({"institution": o["institution_id"],
                        "title": o["title"], "holder": holder,
                        "holder_name": name})
    from . import politics as politics_mod
    governing = politics_mod.governing_party(store)
    parties = []
    for p in store.rows("SELECT * FROM parties ORDER BY party_id"):
        members = store.row("SELECT COUNT(*) AS n FROM"
                            " party_memberships WHERE party_id = ?"
                            " AND left_at_game_minutes IS NULL",
                            (p["party_id"],))["n"]
        support = store.row("SELECT COUNT(*) AS n FROM"
                            " citizen_opinion WHERE"
                            " support_party_id = ?",
                            (p["party_id"],))["n"]
        parties.append({"party_id": p["party_id"],
                        "name": p["name"],
                        "leader": p["leader_character_id"],
                        "members": members, "supporters": support,
                        "balance_ncr": store.balance(p["account_id"]),
                        "role": "governing"
                        if p["party_id"] == governing
                        else "opposition"})
    approval = store.row("SELECT AVG(approval) AS a FROM"
                         " citizen_opinion")
    return {
        "country": {"country_id": country["country_id"],
                    "name": country["name"],
                    "capital_city_id": country["capital_city_id"]},
        "treasuries": gov.government_balances(store),
        "offices": offices,
        "parties": parties,
        "mean_approval": round(approval["a"], 2)
        if approval and approval["a"] is not None else None,
        "institutions": store.row("SELECT COUNT(*) AS n FROM"
                                  " institutions")["n"],
        "civil_servants": store.row(
            "SELECT COUNT(*) AS n FROM civil_service WHERE"
            " status = 'active'")["n"],
        "open_cases": store.row("SELECT COUNT(*) AS n FROM"
                                " court_cases WHERE status IN"
                                " ('filed', 'appealed')")["n"],
        "incidents_total": store.row("SELECT COUNT(*) AS n FROM"
                                     " incidents")["n"],
        "integrity_index": _integrity(store, data),
        "events_recorded": store.row("SELECT COUNT(*) AS n FROM"
                                     " government_events")["n"],
    }


def _integrity(store, data=None):
    from . import integrity as integrity_mod
    if data is None:
        from .dataio import load_all
        data = load_all()
    return integrity_mod.integrity_index(store, data)


def election_view(store, election_id):
    e = store.row("SELECT * FROM elections WHERE election_id = ?",
                  (election_id,))
    if e is None:
        return None
    ballots = store.row("SELECT COUNT(*) AS n FROM ballots WHERE"
                        " election_id = ?", (election_id,))["n"]
    return {"election": dict(e),
            "results": json.loads(e["results"] or "{}"),
            "ballots_cast": ballots}


def policy_view(store, policy_id):
    from . import policies as policies_mod
    p = store.row("SELECT * FROM policies WHERE policy_id = ?",
                  (policy_id,))
    if p is None:
        return None
    return {"policy": dict(p),
            "spent_ncr": policies_mod.policy_spent(store, p),
            "outcome": json.loads(p["actual"] or "{}")}


def budget_view(store):
    rows = store.rows("SELECT * FROM budgets ORDER BY fiscal_year")
    from . import policies as policies_mod
    return {"budgets": [dict(r) for r in rows],
            "public_debt": policies_mod.public_debt(store)}


def court_view(store):
    cases = store.rows("SELECT case_type, status, COUNT(*) AS n"
                       " FROM court_cases GROUP BY case_type,"
                       " status ORDER BY case_type, status")
    return {"cases_by_type_status":
            [{"case_type": c["case_type"], "status": c["status"],
              "count": c["n"]} for c in cases],
            "laws": [dict(r) for r in store.rows(
                "SELECT law_id, title, kind, status, votes_for,"
                " votes_against, effective_month FROM laws"
                " ORDER BY law_id")]}


def diplomacy_view(store):
    partners = [dict(r) for r in store.rows(
        "SELECT * FROM external_partners")]
    agreements = [dict(r) for r in store.rows(
        "SELECT * FROM agreements ORDER BY agreement_id")]
    return {"partners": partners, "agreements": agreements,
            "note": "The external partner is a labelled model,"
                    " not a populated nation."}
