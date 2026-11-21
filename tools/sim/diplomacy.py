"""Session 05 Unit 13 — International Relations.

There is exactly ONE populated country in this simulation.
The external counterpart is an explicitly labelled partner
MODEL — the 'External Trade Partner (model)' — an account and
a relations record, in the same spirit as the SYS-* system
accounts. It is never presented as a populated nation: it has
no citizens, no cities, no government of its own.

Agreements are records with measurable effects:

- a trade agreement lowers the effective import tariff by the
  configured delta while it is active (trade.settle_trade
  reads tariff_delta every settlement);
- a cooperation agreement pays a monthly grant from the
  partner account to the national treasury through the ledger
  (the partner account was seeded once, at setup, from
  SYS-MARKET — labelled genesis funding, like every system
  account in this sim).

The relations score moves only with measured trade: the value
of imports settled with the partner each month. Migration
policy reaches the sim through justice's law book
(migration_openness), which distribution reads.
"""
import json

from . import government as gov

PARTNER_ID = "external_partner"
PARTNER_ACCOUNT = "SYS-EXTERNAL"


def setup_partner(store, data, game_minutes):
    cfg = data.government_config["diplomacy"]
    store.insert(
        "characters", character_id=PARTNER_ACCOUNT,
        display_name="External Trade Partner (modelled)",
        sim_tier="ambient", sex=None, born_at_game_minutes=0,
        is_system=1, balance_cached=0)
    store.insert(
        "external_partners", partner_id=PARTNER_ID,
        name="External Trade Partner (modelled)",
        account_id=PARTNER_ACCOUNT, relation_score=50,
        model_note="Modelled external counterpart — NOT a"
                   " populated nation. No citizens, cities or"
                   " government.",
        created_at_game_minutes=game_minutes)
    grant = cfg["genesis_grant_ncr"]
    if grant > 0:
        store.transfer("SYS-MARKET", PARTNER_ACCOUNT, grant,
                       "genesis_grant", game_minutes,
                       note="external partner model seeded"
                       " (labelled genesis funding)",
                       transfer_key="genesis:external-partner",
                       event_ref="diplomacy:setup")
    return PARTNER_ID


def active_agreement(store, kind):
    return store.row("SELECT * FROM agreements WHERE kind = ?"
                     " AND status = 'active' ORDER BY agreement_id"
                     " DESC LIMIT 1", (kind,))


def tariff_delta(store, data):
    """Points subtracted from the import tariff while a trade
    agreement is active (read by trade.settle_trade)."""
    if active_agreement(store, "trade") is None:
        return 0
    return data.government_config["diplomacy"][
        "trade_agreement_tariff_delta_percent"]


def sign_agreement(store, data, kind, actor_id, game_minutes,
                   terms=None):
    """Only the executive may sign for the nation — the actor
    must hold sign_agreement authority (the prime minister)."""
    gov.require_authority(store, actor_id, "sign_agreement")
    if kind not in ("trade", "cooperation"):
        raise ValueError(f"unknown agreement kind {kind}")
    aid = store.next_id("AG", "agreements", "agreement_id")
    store.insert(
        "agreements", agreement_id=aid, partner_id=PARTNER_ID,
        kind=kind,
        terms=json.dumps(terms or {}, sort_keys=True),
        status="active", signed_by=actor_id,
        started_month=game_minutes // 43200,
        created_at_game_minutes=game_minutes)
    gov.log_event(store, "agreement_signed", actor_id,
                  {"agreement_id": aid, "kind": kind},
                  game_minutes)
    return aid


def terminate_agreement(store, data, agreement_id, actor_id,
                        game_minutes):
    gov.require_authority(store, actor_id, "sign_agreement")
    store.execute("UPDATE agreements SET status = 'terminated'"
                  " WHERE agreement_id = ?", (agreement_id,))
    gov.log_event(store, "agreement_terminated", actor_id,
                  {"agreement_id": agreement_id}, game_minutes)


def monthly_pass(store, data, rng, month_index, game_minutes):
    if not gov.is_setup(store):
        return None
    cfg = data.government_config["diplomacy"]
    out = {}
    # Cooperation grant: partner -> treasury, ledger-traced,
    # only while the agreement is active and the partner holds
    # the funds (its balance is real and finite).
    if active_agreement(store, "cooperation") is not None:
        grant = cfg["cooperation_grant_ncr_per_month"]
        if store.balance(PARTNER_ACCOUNT) >= grant:
            store.transfer(
                PARTNER_ACCOUNT, gov.NATIONAL_ACCOUNT, grant,
                "cooperation_grant", game_minutes,
                note="cooperation agreement monthly grant",
                transfer_key=f"coop-grant:{month_index}",
                event_ref="diplomacy:cooperation")
            out["cooperation_grant_ncr"] = grant
    # Relations score follows measured imports from the partner.
    imports = store.row(
        "SELECT COALESCE(SUM(amount), 0) AS s FROM"
        " economy_ledger WHERE reason_code = 'tariff' AND"
        " game_minutes > ?", (game_minutes - 30 * 1440,))["s"]
    partner = store.row("SELECT * FROM external_partners WHERE"
                        " partner_id = ?", (PARTNER_ID,))
    score = partner["relation_score"]
    if imports > 0:
        score = min(100, score + 1)
    store.execute("UPDATE external_partners SET relation_score"
                  " = ? WHERE partner_id = ?", (score, PARTNER_ID))
    out["relation_score"] = score
    out["imports_taxed_ncr"] = imports
    out["tariff_delta_points"] = tariff_delta(store, data)
    return out
