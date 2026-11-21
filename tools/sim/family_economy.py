"""Session 02 Unit 03 — Family Economy Engine.

Session 01's settlement already moves every NCr through the ledger:
wages net of tax, business P&L, rent by the head, living costs split
by income share. What it never did was *account* for the household
as a family: who contributed what, what the money went on, whether
the family is saving or sinking. This unit is that accounting layer,
written from the settlement's own numbers at the moment they are
settled — no parallel economy, no second set of books.

Per household per month, one household_finances row:
- income: wages/business profit settled this month + pensions;
- food / transport / other: the settlement's living-cost lines
  (prices.json categories — food_home_cooking; transport incl. cab
  rental; other = utilities + clothing + eating out + services +
  lifestyle uplift);
- housing: the rent actually charged;
- education / healthcare: **0, deliberately.** District 1's school,
  college and clinic are civic institutions funded through the city
  tax account (GDD-11 §7, GDD-12); prices.json carries no fee line
  for them and this engine does not invent one. The rows exist so
  the absence is visible in the accounts, not hidden;
- emergency: the month's unpaid arrears — in a world with no priced
  emergency goods, an emergency *is* the bill the family could not
  pay. Arrears become household debt (household_state), repaid from
  the head's balance at the next settlement before new costs, down
  to a small reserve. Debt is a persistent family condition: it is
  what the conflict and mobility engines read.

A household experiences growth or difficulty in these rows: savings
delta is the change in the members' combined ledger balances month
over month, so the accounts can never disagree with the ledger.
"""
RESERVE_NCR = 1000  # the head keeps this back when repaying debt


def state(store, household_id):
    row = store.row("SELECT * FROM household_state WHERE household_id"
                    " = ?", (household_id,))
    if row is None:
        store.insert("household_state", household_id=household_id,
                     debt_ncr=0, last_balance_total=None,
                     updated_at_game_minutes=0)
        row = store.row("SELECT * FROM household_state"
                        " WHERE household_id = ?", (household_id,))
    return row


def debt_of(store, household_id):
    return state(store, household_id)["debt_ncr"]


def repay_debt(store, household_id, head_id, game_minutes):
    """Repay arrears from the head's balance, keeping a reserve.
    Returns the amount repaid (0 when there is no debt — the common
    case, and the reason the Session 01 reconciliation is
    untouched: a debt-free household's settlement is byte-identical
    to before this unit existed)."""
    st = state(store, household_id)
    debt = st["debt_ncr"]
    if debt <= 0 or head_id is None:
        return 0
    available = max(0, store.balance(head_id) - RESERVE_NCR)
    paid = min(debt, available)
    if paid > 0:
        store.transfer(head_id, "SYS-MARKET", paid, "debt_repayment",
                       game_minutes, note="household arrears repayment")
        store.execute("UPDATE household_state SET debt_ncr = debt_ncr"
                      " - ?, updated_at_game_minutes = ?"
                      " WHERE household_id = ?",
                      (paid, game_minutes, household_id))
    return paid


def record_month(store, household_id, month_index, game_minutes, *,
                 income, food, housing, transport, other, emergency,
                 education=0, healthcare=0):
    """Write the month's family accounts. `emergency` (unpaid
    arrears) is added to the household's debt after any repayment
    made this settlement. Returns the finance row id."""
    st = state(store, household_id)
    balances_total = store.row(
        "SELECT COALESCE(SUM(c.balance_cached),0) AS s FROM"
        " household_members hm JOIN characters c"
        " ON c.character_id = hm.character_id WHERE hm.household_id = ?"
        " AND hm.left_at_game_minutes IS NULL", (household_id,))["s"]
    last = st["last_balance_total"]
    savings_delta = balances_total - last if last is not None else 0
    debt_after = st["debt_ncr"] + int(emergency)
    fid = store.next_id("HF", "household_finances", "finance_id")
    store.execute(
        "INSERT OR REPLACE INTO household_finances (finance_id,"
        " household_id, month_index, income_ncr, food_ncr, housing_ncr,"
        " education_ncr, healthcare_ncr, transport_ncr, other_ncr,"
        " emergency_ncr, savings_delta_ncr, debt_after_ncr,"
        " game_minutes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (fid, household_id, month_index, int(income), int(food),
         int(housing), int(education), int(healthcare), int(transport),
         int(other), int(emergency), int(savings_delta), debt_after,
         game_minutes))
    store.execute("UPDATE household_state SET debt_ncr = ?,"
                  " last_balance_total = ?, updated_at_game_minutes = ?"
                  " WHERE household_id = ?",
                  (debt_after, balances_total, game_minutes,
                   household_id))
    return fid


def contributions(store, household_id):
    """Each member's current monthly contribution to the pool:
    their wage (or pension-age status) from live rows — the family
    economy's income side, per person."""
    from .identity import age_years
    now = store.world()["game_minutes"]
    out = []
    rows = store.rows(
        "SELECT c.character_id, c.display_name, c.born_at_game_minutes,"
        " e.profession_id, e.wage_per_month FROM household_members hm"
        " JOIN characters c ON c.character_id = hm.character_id"
        " LEFT JOIN employments e ON e.character_id = c.character_id"
        " AND e.ended_at_game_minutes IS NULL WHERE hm.household_id = ?"
        " AND hm.left_at_game_minutes IS NULL"
        " AND c.died_at_game_minutes IS NULL ORDER BY c.character_id",
        (household_id,))
    for r in rows:
        age = age_years(r["born_at_game_minutes"], now)
        kind = "wage" if r["wage_per_month"] else \
            ("pension" if age >= 65 else "none")
        out.append({"character_id": r["character_id"],
                    "name": r["display_name"], "age": age,
                    "profession": r["profession_id"], "kind": kind,
                    "monthly_ncr": r["wage_per_month"] or 0})
    return out


def snapshot(store, household_id):
    """The family's financial condition, from its own accounts."""
    latest = store.row("SELECT * FROM household_finances"
                       " WHERE household_id = ? ORDER BY month_index"
                       " DESC LIMIT 1", (household_id,))
    debt = debt_of(store, household_id)
    if latest is None:
        condition = "unrecorded"
    elif debt > 0:
        condition = "in_debt"
    elif latest["savings_delta_ncr"] > 0:
        condition = "growing"
    elif latest["savings_delta_ncr"] < 0:
        condition = "declining"
    else:
        condition = "stable"
    return {"household_id": household_id, "debt_ncr": debt,
            "condition": condition, "latest_month": latest,
            "contributions": contributions(store, household_id)}


def history(store, household_id):
    return store.rows("SELECT * FROM household_finances"
                      " WHERE household_id = ? ORDER BY month_index",
                      (household_id,))
