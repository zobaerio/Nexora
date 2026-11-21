"""Session 09 — Agent coordination observatory (data layer only).

Every value is read from the coordination layer's own records:
the registry over real actors, extended goals with their progress
history, negotiations with every offer, supply orders, decision
explanations, multi-level memories, forecasts with their scored
outcomes, assessments with their evaluations, coordination tasks
and the learning log.

Access position (stated plainly, per the spec): this is a local
simulation's own observatory. Simulated memories are visible here
because the observatory is the simulation operator's tool; the
registry's capability model governs what simulated agents may do
inside the world, and nothing in this layer touches real platform
access (the Session 05 separation rule).
"""
import json

from . import agents as agents_mod


def _rows(store, sql, params=()):
    return [dict(r) for r in store.rows(sql, params)]


def agents_view(store, data):
    if not agents_mod.is_setup(store):
        return {"agents_setup": False}
    out = {"agents_setup": True,
           "summary": agents_mod.agents_summary(store)}
    out["registry"] = _rows(
        store, "SELECT agent_id, agent_class, ref_id, display_name,"
               " status FROM agent_registry ORDER BY agent_class,"
               " ref_id")
    out["active_goals"] = _rows(
        store, "SELECT goal_id, character_id, goal_type, priority,"
               " progress, feasibility, completion_rule FROM"
               " character_goals WHERE status = 'active' ORDER BY"
               " priority DESC LIMIT 100")
    out["recent_goal_progress"] = _rows(
        store, "SELECT goal_id, character_id, progress, measured,"
               " game_minutes FROM goal_progress_log ORDER BY"
               " log_id DESC LIMIT 50")
    out["negotiations"] = _rows(
        store, "SELECT * FROM negotiations ORDER BY"
               " negotiation_id DESC LIMIT 50")
    out["negotiation_offers"] = _rows(
        store, "SELECT o.* FROM negotiation_offers o JOIN"
               " negotiations n ON n.negotiation_id ="
               " o.negotiation_id ORDER BY o.offer_id DESC"
               " LIMIT 100")
    out["recent_decisions"] = _rows(
        store, "SELECT agent_ref, agent_class, decision_kind,"
               " inputs, rule, outcome, game_minutes FROM"
               " agent_decisions ORDER BY record_id DESC LIMIT 50")
    out["forecasts"] = _rows(
        store, "SELECT forecast_id, kind, scope, made_month,"
               " target_month, inputs, predicted, actual, score,"
               " status FROM forecasts ORDER BY forecast_id DESC"
               " LIMIT 50")
    out["assessments"] = _rows(
        store, "SELECT * FROM assessments ORDER BY assessment_id")
    out["coordination_tasks"] = _rows(
        store, "SELECT * FROM coordination_tasks ORDER BY task_id")
    out["memories"] = {
        level: _rows(
            store, "SELECT owner_ref, event_kind, summary,"
                   " importance, access_count, compressed FROM"
                   " agent_memories WHERE level = ? ORDER BY"
                   " importance DESC LIMIT 50", (level,))
        for level in ("family", "organisation", "community",
                      "civilization")}
    out["learning"] = _rows(
        store, "SELECT owner_ref, param, old_value, new_value,"
               " reason, game_minutes FROM agent_learning ORDER BY"
               " record_id DESC LIMIT 50")
    out["failed_actions"] = _rows(
        store, "SELECT agent_ref, action_kind, details,"
               " game_minutes FROM agent_actions WHERE status ="
               " 'failed' ORDER BY action_id DESC LIMIT 50")
    out["messages"] = _rows(
        store, "SELECT from_ref, to_ref, kind, payload,"
               " game_minutes FROM agent_messages ORDER BY"
               " message_id DESC LIMIT 50")
    return out
