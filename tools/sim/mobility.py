"""Session 02 Unit 11 — Social Mobility Engine.

Mobility is *bookkeeping over outcomes*: nobody is assigned a
class. Each month, every adult's standing is recomputed from the
simulation's own facts —

- economic band: economy_sim's own band_for() applied to their
  current wage (or the pension, or nothing);
- career tier: their employment tier (0 when unemployed);
- education level: none / school / college credential, from
  Unit 08's education_records —

and when a value differs from the last recorded one, a
status_history row and a life event mark the change. Advancement
and hardship are therefore the *same* mechanism read in two
directions: a promotion (Unit 08's gate + Session 01's tiers)
moves the career row; a job loss moves the economic row down.

Relocation — the physical side of mobility — is a decision, not a
bookkeeping entry: the head's relocate candidate (decisions.py,
Units 02/11) fires on rent burden and moves the household through
households.move_household, priced from the canonical buildings
data. Where the data cannot price a vacant unit, the move does
not exist; that was Session 01's recorded gap, closed here only
where the data honestly supports it.
"""
from . import education as education_mod
from . import memory as memory_mod

DIMENSIONS = ("economic_band", "career_tier", "education_level")


def economic_band(store, data, character_id):
    emp = store.row("SELECT wage_per_month FROM employments"
                    " WHERE character_id = ?"
                    " AND ended_at_game_minutes IS NULL", (character_id,))
    if emp:
        return data.econ.band_for(emp["wage_per_month"])
    from .identity import age_years
    char = store.row("SELECT born_at_game_minutes FROM characters"
                     " WHERE character_id = ?", (character_id,))
    if char and age_years(char["born_at_game_minutes"],
                          store.world()["game_minutes"]) >= 65:
        return data.econ.band_for(3500)  # pension (sim assumption)
    return "none"


def career_tier(store, character_id):
    emp = store.row("SELECT tier FROM employments WHERE character_id"
                    " = ? AND ended_at_game_minutes IS NULL",
                    (character_id,))
    return str(emp["tier"]) if emp else "0"


def education_level(store, character_id):
    cred = store.row("SELECT 1 FROM education_records WHERE"
                     " character_id = ? AND status = 'completed'"
                     " AND programme != 'school'", (character_id,))
    if cred:
        return "college_credential"
    school = store.row("SELECT 1 FROM education_records WHERE"
                       " character_id = ? AND programme = 'school'"
                       " AND status = 'completed'", (character_id,))
    return "school" if school else "none"


def current_status(store, data, character_id):
    return {"economic_band": economic_band(store, data, character_id),
            "career_tier": career_tier(store, character_id),
            "education_level": education_level(store, character_id)}


def monthly_check(store, data, game_minutes):
    """Recompute every living adult's standing; record changes.
    The first check writes the baseline census (from_value NULL).
    Returns the number of changes recorded."""
    from .identity import age_years
    changes = 0
    chars = store.rows("SELECT * FROM characters WHERE is_system = 0"
                       " AND died_at_game_minutes IS NULL"
                       " ORDER BY character_id")
    for c in chars:
        cid = c["character_id"]
        if age_years(c["born_at_game_minutes"], game_minutes) < 18:
            continue
        status = current_status(store, data, cid)
        for dim in DIMENSIONS:
            last = store.row("SELECT to_value FROM status_history"
                             " WHERE character_id = ? AND dimension = ?"
                             " ORDER BY game_minutes DESC, history_id"
                             " DESC LIMIT 1", (cid, dim))
            prev = last["to_value"] if last else None
            if prev != status[dim]:
                hid = store.next_id("SH", "status_history", "history_id")
                store.insert("status_history", history_id=hid,
                             character_id=cid, dimension=dim,
                             from_value=prev, to_value=status[dim],
                             game_minutes=game_minutes)
                if prev is not None:
                    memory_mod.log_life_event(
                        store, cid, "status_change", game_minutes,
                        details={"dimension": dim, "from": prev,
                                 "to": status[dim]})
                changes += 1
    return changes


def mobility_summary(store, data, character_id):
    return {"character_id": character_id,
            "current": current_status(store, data, character_id),
            "history": store.rows(
                "SELECT * FROM status_history WHERE character_id = ?"
                " ORDER BY game_minutes, history_id", (character_id,))}
