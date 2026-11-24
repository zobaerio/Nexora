"""Unit 05 — Human Needs Engine.

Ten needs, stored as *satisfaction* 0..100 (deficit = 100 - value;
GDD-01 §4: deficits generate wants and bend schedules). Needs change
only through simulated activity and daily economic reality — never by
random drift:

- Activity effects accrue per simulated hour at block boundaries
  (sleep restores sleep/rest and costs hunger; work drains rest and
  feeds development; leisure feeds social; study feeds education...).
- Meals happen inside home blocks (a home block of 45+ minutes
  includes eating and drinking).
- Daily components (financial, healthcare, safety) are computed once
  per day by the engine from world facts: balance vs costs, age,
  housing tier, weather.

The scheduler (Unit 04) reads yesterday's satisfactions and bends
today's template per GDD-06 §8 — that loop is what makes needs
*behavioural* rather than decorative bars.
"""

NEEDS = ("hunger", "thirst", "sleep", "rest", "safety", "social",
         "healthcare", "financial", "education", "development")

# Per-hour satisfaction deltas by activity.
HOURLY = {
    "sleep":   {"sleep": 14, "rest": 8, "hunger": -4, "thirst": -5,
                "social": -1, "safety": 2},
    "home":    {"hunger": 4, "thirst": 4, "rest": 5, "social": 2,
                "safety": 2, "sleep": -2},
    "commute": {"rest": -3, "hunger": -2, "thirst": -2, "safety": -1},
    "work":    {"rest": -4, "hunger": -3, "thirst": -3, "development": 1,
                "healthcare": -0.5, "social": 1},
    "break":   {"hunger": 6, "thirst": 5, "social": 4, "rest": 4},
    "errand":  {"rest": -2, "hunger": -1, "social": 1},
    "leisure": {"social": 5, "rest": 4, "hunger": -2, "thirst": -2},
    "study":   {"education": 6, "development": 3, "rest": -3,
                "social": -1, "hunger": -2},
}
SOCIAL_ANCHORS = {"tea_stall", "market", "riverfront", "restaurant",
                  "college_para"}
MEAL_BONUS = {"hunger": 22, "thirst": 16}


def _clamp(v):
    return max(0, min(100, round(v)))


def get_needs(store, character_id):
    row = store.row("SELECT * FROM needs_state WHERE character_id = ?",
                    (character_id,))
    return {n: row[n] for n in NEEDS} if row else None


def _write(store, character_id, values, game_minutes):
    sets = ", ".join(f"{n} = ?" for n in NEEDS)
    store.execute(
        f"UPDATE needs_state SET {sets}, updated_at_game_minutes = ?"
        " WHERE character_id = ?",
        tuple(values[n] for n in NEEDS) + (game_minutes, character_id))


def apply_activity(store, character_id, activity, location, hours,
                   game_minutes, meal=False, data=None):
    """Accrue one block's worth of need changes.

    Queue 21 Unit EQ (GDD-10 §5/§6): the home restores follow the
    household's effective furniture tier — the rest/sleep RESTORES
    of a "home" or "sleep" block are scaled by
    ``lost_items.furniture_restore_multiplier()`` (F0 ×0.7, F1
    ×1.0, F2 ×1.15, F3 ×1.3), so a lost or broken bed measurably
    costs the household its rest until the favour completes or the
    repair lands. Only positive rest/sleep deltas scale: drains
    stay unscaled (furniture does not make you hungrier), and
    hunger/thirst/social/safety are untouched (the §6 Food-kitchen
    and Social-sofa rules are qualitative and stay unimplemented).
    When the multiplier is None (no tier stands) no scaling is
    applied — no fallback rate is invented (EF's boundary); the
    rate stays the fixed one. ``data`` is None for callers that do
    not hold the world data (the old tests): no scaling, the exact
    old behaviour."""
    values = get_needs(store, character_id)
    if values is None:
        return
    effects = HOURLY.get(activity, {})
    multiplier = None
    if data is not None and activity in ("home", "sleep") \
            and hours > 0:
        from . import lost_items as lost_items_mod
        multiplier = lost_items_mod.furniture_restore_multiplier(
            store, data, character_id)
    for need, per_hour in effects.items():
        delta = per_hour * hours
        if multiplier is not None and need in ("rest", "sleep") \
                and delta > 0:
            delta *= multiplier
        values[need] += delta
    if activity == "leisure" and location in SOCIAL_ANCHORS:
        values["social"] += 3 * hours  # social anchors feed social more
    if meal:
        for need, bonus in MEAL_BONUS.items():
            values[need] += bonus
    _write(store, character_id,
           {n: _clamp(values[n]) for n in NEEDS}, game_minutes)


def daily_update(store, character_id, *, age, home_tier, balance,
                 monthly_cost_estimate, studied_today, storm_today,
                 game_minutes):
    """Once-per-day components computed from world facts."""
    values = get_needs(store, character_id)
    if values is None:
        return
    # Financial satisfaction: months of costs the balance covers.
    if monthly_cost_estimate > 0:
        cover = balance / monthly_cost_estimate
        values["financial"] = _clamp(15 + cover * 35)
    # Healthcare: slow age drift; rest protects.
    drift = -0.2 if age < 50 else (-0.5 if age < 65 else -1.0)
    if values["sleep"] > 60:
        drift += 0.4
    values["healthcare"] = _clamp(values["healthcare"] + drift)
    # Safety regresses toward a housing-tier baseline; storms shake it.
    baseline = {1: 55, 2: 62, 3: 70, 4: 78, 5: 85}.get(home_tier, 65)
    values["safety"] += (baseline - values["safety"]) * 0.2
    if storm_today:
        values["safety"] -= 10
    # Education decays slowly without study.
    if not studied_today:
        values["education"] = _clamp(values["education"] - 0.3)
    _write(store, character_id,
           {n: _clamp(values[n]) for n in NEEDS}, game_minutes)


def adjust(store, character_id, deltas, game_minutes):
    """Apply explicit satisfaction deltas from a world system
    (Session 03: infrastructure overload effects). Deltas are the
    caller's measured facts, clamped like every other write."""
    values = get_needs(store, character_id)
    if values is None:
        return
    for need, delta in deltas.items():
        if need in NEEDS:
            values[need] += delta
    _write(store, character_id,
           {n: _clamp(values[n]) for n in NEEDS}, game_minutes)


def deficit(values, need):
    return 100 - values[need]
