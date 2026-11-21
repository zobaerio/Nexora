"""Session 02 observation surface — civilization inspection over
real simulation data, the CLI counterpart of Session 01's profile
card. Every view reads live rows: a family tree is the current
kinship graph, a household view is its current members and
accounts, a community view is its current population, leader,
issues and facilities. Nothing is cached, sampled or fabricated;
an empty world reports empty views.
"""
from . import community as community_mod
from . import family_economy
from . import generations as generations_mod
from . import households as households_mod
from . import identity as identity_mod
from . import kinship
from . import mobility as mobility_mod
from . import social as social_mod


def inspect_person(store, data, character_id):
    """Profile card + family tree + social network + mobility +
    generational history for one person."""
    card = identity_mod.profile_card(store, character_id)
    if card is None:
        return None
    return {
        "profile": card,
        "family_tree": kinship.family_tree(store, character_id),
        "social_network": social_mod.network(store, character_id),
        "mobility": mobility_mod.mobility_summary(store, data,
                                                  character_id),
        "generational_history": generations_mod.history_of(
            store, character_id),
        "lineage": generations_mod.lineage(store, character_id),
    }


def inspect_household(store, data, household_id):
    h = store.row("SELECT * FROM households WHERE household_id = ?",
                  (household_id,))
    if h is None:
        return None
    return {
        "household": h,
        "composition": households_mod.composition(store, household_id),
        "living_conditions": households_mod.living_conditions(
            store, data, household_id),
        "finances": family_economy.snapshot(store, household_id),
        "finance_history": family_economy.history(store, household_id),
    }


def inspect_community(store, data, zone_id):
    return community_mod.community_view(store, data, zone_id)


def society_overview(store, data):
    """The whole society at a glance — counts of the Session 02
    structures, all read live."""
    return {
        "communities": [community_mod.community_view(store, data, z)
                        for z in sorted(data.zones)],
        "households_in_debt": store.row(
            "SELECT COUNT(*) AS n FROM household_state"
            " WHERE debt_ncr > 0")["n"],
        "social_events_by_type": {
            r["event_type"]: r["n"] for r in store.rows(
                "SELECT event_type, COUNT(*) AS n FROM social_events"
                " GROUP BY event_type ORDER BY event_type")},
        "conflicts_by_status": {
            r["status"]: r["n"] for r in store.rows(
                "SELECT status, COUNT(*) AS n FROM conflict_records"
                " GROUP BY status ORDER BY status")},
        "credentials_completed": store.row(
            "SELECT COUNT(*) AS n FROM education_records"
            " WHERE status = 'completed' AND programme != 'school'")["n"],
        "generational_records": store.row(
            "SELECT COUNT(*) AS n FROM generational_history")["n"],
    }
