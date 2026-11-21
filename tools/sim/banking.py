"""Session 04 Units 08-09 — Banking & Investment.

The bank is an institution ON the ledger, not beside it. SYS-BANK
is a system account capitalised once at genesis (reason
'bank_capital', from the config) — GDD-03 §4.3's rule is enforced
in code: the bank lends only what it holds, so every disbursement
is capped by SYS-BANK's actual balance.

Accounts (Unit 08): a bank account's balance is the bank's
liability to the customer, and it reconciles exactly against the
ledger: balance == deposits - withdrawals for that customer.
Savings interest (prices.json loans.savings_annual_interest_
percent — a DESIGN rate, GDD-03 §4.4) is paid monthly out of the
bank to the customer's cash, so the identity survives interest
too. Deposits and withdrawals are ordinary transfers with reason
codes, idempotency keys and event refs.

Loans: bank_loan and mortgage at prices.json's design terms
(12% / 5x monthly income / 24 months; 9% / 20% deposit / 20
years). Credit assessment reads the applicant's real ledger
history — months of wage income, current debt, missed payments —
and the eligible maximum is a formula over those facts, stated
in assess_credit. Repayment is a level amortising payment;
interest is the outstanding balance's monthly accrual. A borrower
who cannot pay records a missed payment; three misses default
the loan, and a defaulted mortgage forecloses: the property
passes to the bank and the household stays on as its tenant at
the unit's canonical rent (households.rent_of_property — the
Session 02 join), so foreclosure is a tenure change, not an
eviction into the void.

Investment (Unit 09): equity in real businesses. A business has
a fixed float of TOTAL_SHARES shares; the price per share is its
documented net-worth model (business.net_worth: cash + inventory
at market prices) divided by the float, floored at 1 NCr. Buying
moves real money from the investor into the business account
(reason 'investment') — equity financing the firm can actually
spend. Dividends are paid monthly from recorded profit: a
labelled payout ratio of the month's business_monthly profit,
shared pro-rata over externally held shares, capped by what the
business can pay while keeping its wage reserve. The bank buys
nothing; there are no funds or bonds beyond the city's implicit
position — government borrowing is reported as SYS-CITY's
overdraft in govfinance, not dressed up as a bond market.
"""
from . import business as business_mod
from . import finance as finance_mod

TOTAL_SHARES = 100
DIVIDEND_PAYOUT_RATIO = 0.30  # SIM MODEL payout policy (labelled)
REPAYMENT_RESERVE_NCR = 500   # a borrower keeps this back

_DATA = None


def _data():
    """WorldData is a pure function of the merged files; cache one
    instance for the helpers whose callers don't pass it."""
    global _DATA
    if _DATA is None:
        from .dataio import WorldData
        _DATA = WorldData()
    return _DATA


def setup_bank(store, data, game_minutes=480):
    capital = data.economy_config["bank"]["genesis_capital_ncr"]
    if store.balance("SYS-BANK") == 0:
        store.transfer("SYS-MARKET", "SYS-BANK", capital,
                       "bank_capital", game_minutes,
                       note="bank genesis capitalisation",
                       transfer_key="genesis-bank-capital",
                       event_ref="economy_setup")
    accounts = 0
    from . import identity as identity_mod
    now = game_minutes
    for c in store.rows("SELECT character_id, born_at_game_minutes"
                        " FROM characters WHERE is_system = 0"
                        " AND died_at_game_minutes IS NULL"):
        if identity_mod.age_years(c["born_at_game_minutes"], now) >= 18:
            if open_account(store, c["character_id"], game_minutes):
                accounts += 1
    return {"capital_ncr": capital, "accounts_opened": accounts}


def open_account(store, character_id, game_minutes):
    if store.row("SELECT 1 FROM bank_accounts WHERE character_id = ?",
                 (character_id,)):
        return False
    aid = store.next_id("BA", "bank_accounts", "account_id")
    store.insert("bank_accounts", account_id=aid,
                 character_id=character_id, account_type="savings",
                 balance_cached=0, opened_at_game_minutes=game_minutes)
    return True


def account_of(store, character_id):
    return store.row("SELECT * FROM bank_accounts WHERE character_id"
                     " = ? AND closed_at_game_minutes IS NULL",
                     (character_id,))


def deposit(store, character_id, amount, game_minutes, *,
            transfer_key=None, event_ref=None):
    acct = account_of(store, character_id)
    if acct is None or amount <= 0:
        return 0
    amount = min(amount, store.balance(character_id))
    if amount <= 0:
        return 0
    store.transfer(character_id, "SYS-BANK", amount, "bank_deposit",
                   game_minutes, note="bank deposit",
                   transfer_key=transfer_key, event_ref=event_ref)
    store.execute("UPDATE bank_accounts SET balance_cached ="
                  " balance_cached + ? WHERE account_id = ?",
                  (amount, acct["account_id"]))
    return amount


def withdraw(store, character_id, amount, game_minutes, *,
             transfer_key=None, event_ref=None):
    """Withdrawals are capped by the account balance AND by the
    bank's liquidity (it lends only what it holds — and pays out
    only what it holds). Returns the amount actually paid."""
    acct = account_of(store, character_id)
    if acct is None or amount <= 0:
        return 0
    paid = min(amount, acct["balance_cached"],
               max(0, store.balance("SYS-BANK")))
    if paid <= 0:
        return 0
    store.transfer("SYS-BANK", character_id, paid, "bank_withdrawal",
                   game_minutes, note="bank withdrawal",
                   transfer_key=transfer_key, event_ref=event_ref)
    store.execute("UPDATE bank_accounts SET balance_cached ="
                  " balance_cached - ? WHERE account_id = ?",
                  (paid, acct["account_id"]))
    return paid


def account_reconciliation(store):
    """Every account balance must equal its customer's ledger
    deposits minus withdrawals. Returns violations."""
    out = []
    for a in store.rows("SELECT * FROM bank_accounts WHERE"
                        " closed_at_game_minutes IS NULL"):
        cid = a["character_id"]
        dep = store.row(
            "SELECT COALESCE(SUM(amount),0) AS s FROM economy_ledger"
            " WHERE from_character_id = ? AND to_character_id ="
            " 'SYS-BANK' AND reason_code = 'bank_deposit'",
            (cid,))["s"]
        wd = store.row(
            "SELECT COALESCE(SUM(amount),0) AS s FROM economy_ledger"
            " WHERE from_character_id = 'SYS-BANK'"
            " AND to_character_id = ? AND reason_code ="
            " 'bank_withdrawal'", (cid,))["s"]
        if dep - wd != a["balance_cached"]:
            out.append((cid, a["balance_cached"], dep - wd))
    return out


def assess_credit(store, data, character_id):
    """Credit assessment from the applicant's real records:
    trailing wage income (ledger), months with wage income,
    current debt (loans + household arrears) and missed-payment
    history. Eligible maxima follow prices.json's loan terms."""
    if character_id == "SYS-CITY":
        # Session 05 Unit 07: the sovereign borrower. A treasury
        # has no wages; its credit is assessed on recorded
        # government revenue (the trailing 3 months of tax, sales
        # tax, tariff, rent and commercial-rent inflows to
        # SYS-CITY), under the same prices.json multiple and the
        # same delinquency rule as any other borrower.
        now = store.world()["game_minutes"]
        since = now - 3 * 30 * 1440
        rev = store.row(
            "SELECT COALESCE(SUM(amount),0) AS s FROM economy_ledger"
            " WHERE to_character_id = 'SYS-CITY' AND reason_code IN"
            " ('tax', 'sales_tax', 'tariff', 'rent',"
            " 'commercial_rent') AND game_minutes > ?",
            (since,))["s"]
        months = store.rows(
            "SELECT DISTINCT (game_minutes / 43200) AS m FROM"
            " economy_ledger WHERE to_character_id = 'SYS-CITY'"
            " AND reason_code = 'tax' AND game_minutes > ?",
            (since,))
        loans = store.rows("SELECT * FROM loans WHERE"
                           " borrower_character_id = 'SYS-CITY'"
                           " AND status IN ('active', 'defaulted')")
        debt = sum(l["outstanding_ncr"] for l in loans)
        missed = sum(l["missed_payments"] for l in loans)
        cfg = data.prices["loans"]
        bl = cfg["bank_loan"]
        monthly_income = rev // 3
        max_bank_loan = monthly_income \
            * bl["max_multiple_of_monthly_income"]
        if missed >= 2:
            max_bank_loan = 0
        mg = cfg["mortgage"]
        return {
            "character_id": character_id,
            "monthly_income_ncr": monthly_income,
            "wage_months_observed": len(months),
            "current_debt_ncr": debt,
            "household_arrears_ncr": 0,
            "missed_payments": missed,
            "max_bank_loan_ncr": max(0, max_bank_loan - debt),
            "bank_loan_rate_percent": bl["annual_interest_percent"],
            "bank_loan_term_months": bl["max_term_months"],
            "mortgage_rate_percent": mg["annual_interest_percent"],
            "mortgage_deposit_percent": mg["deposit_percent"],
            "mortgage_term_months": mg["max_term_years"] * 12,
        }
    now = store.world()["game_minutes"]
    since = now - 3 * 30 * 1440
    wages = store.rows(
        "SELECT DISTINCT (game_minutes / 43200) AS m FROM"
        " economy_ledger WHERE to_character_id = ? AND reason_code"
        " = 'wage' AND game_minutes > ?", (character_id, since))
    wage_total = store.row(
        "SELECT COALESCE(SUM(amount),0) AS s FROM economy_ledger"
        " WHERE to_character_id = ? AND reason_code = 'wage'"
        " AND game_minutes > ?", (character_id, since))["s"]
    monthly_income = wage_total // 3
    loans = store.rows("SELECT * FROM loans WHERE"
                       " borrower_character_id = ? AND status"
                       " IN ('active', 'defaulted')", (character_id,))
    debt = sum(l["outstanding_ncr"] for l in loans)
    missed = sum(l["missed_payments"] for l in loans)
    char = store.row("SELECT household_id FROM characters WHERE"
                     " character_id = ?", (character_id,))
    arrears = 0
    if char and char["household_id"]:
        from . import family_economy
        arrears = family_economy.debt_of(store, char["household_id"])
    cfg = data.prices["loans"]
    bl = cfg["bank_loan"]
    max_bank_loan = monthly_income \
        * bl["max_multiple_of_monthly_income"]
    if missed >= 2 or arrears > 0:
        max_bank_loan = 0  # recorded delinquency closes the window
    mg = cfg["mortgage"]
    return {
        "character_id": character_id,
        "monthly_income_ncr": monthly_income,
        "wage_months_observed": len(wages),
        "current_debt_ncr": debt,
        "household_arrears_ncr": arrears,
        "missed_payments": missed,
        "max_bank_loan_ncr": max(0, max_bank_loan - debt),
        "bank_loan_rate_percent": bl["annual_interest_percent"],
        "bank_loan_term_months": bl["max_term_months"],
        "mortgage_rate_percent": mg["annual_interest_percent"],
        "mortgage_deposit_percent": mg["deposit_percent"],
        "mortgage_term_months": mg["max_term_years"] * 12,
    }


def disburse_loan(store, data, character_id, kind, amount,
                  game_minutes, *, property_id=None,
                  pay_to_character=True):
    """Create a loan if the bank holds the funds and the amount
    is inside the assessed eligibility. Returns the loan row or
    None (refused — the refusal is a fact callers record)."""
    credit = assess_credit(store, data, character_id)
    from . import crises as crises_mod
    if crises_mod.active_effects(store)["lending_halt"]:
        return None  # banking stress: the lending window is shut
    if kind == "bank_loan":
        if amount > credit["max_bank_loan_ncr"] or amount <= 0:
            return None
        rate = credit["bank_loan_rate_percent"]
        term = credit["bank_loan_term_months"]
    elif kind == "mortgage":
        rate = credit["mortgage_rate_percent"]
        term = credit["mortgage_term_months"]
    else:
        return None
    if store.balance("SYS-BANK") < amount:
        return None  # the bank lends only what it holds
    lid = store.next_id("LN", "loans", "loan_id")
    store.insert("loans", loan_id=lid, borrower_character_id=character_id,
                 kind=kind, principal_ncr=amount, outstanding_ncr=amount,
                 annual_rate_percent=rate, term_months=term,
                 status="active", property_id=property_id,
                 started_at_game_minutes=game_minutes,
                 updated_at_game_minutes=game_minutes)
    if pay_to_character:
        store.transfer("SYS-BANK", character_id, amount,
                       "loan_disbursement", game_minutes,
                       note=f"{kind} disbursement",
                       transfer_key=f"loan:{lid}",
                       event_ref=f"loan:{lid}")
    return store.row("SELECT * FROM loans WHERE loan_id = ?", (lid,))


def monthly_interest(store, data, month_index, game_minutes):
    """Savings interest, paid out to cash (see module docstring),
    capped by what the bank actually holds."""
    rate = data.prices["loans"]["savings_annual_interest_percent"] \
        / 100 / 12
    paid_total = 0
    for a in store.rows("SELECT * FROM bank_accounts WHERE"
                        " closed_at_game_minutes IS NULL"
                        " AND balance_cached > 0 ORDER BY account_id"):
        interest = round(a["balance_cached"] * rate)
        if interest <= 0:
            continue
        if store.balance("SYS-BANK") < interest:
            break  # liquidity exhausted; deterministic order
        store.transfer("SYS-BANK", a["character_id"], interest,
                       "interest", game_minutes,
                       note="savings interest",
                       transfer_key=f"interest:{a['account_id']}:"
                                    f"{month_index}",
                       event_ref=f"month:{month_index}")
        paid_total += interest
    return paid_total


def monthly_repayments(store, data, month_index, game_minutes):
    """Level amortising repayments for every active loan. A
    borrower who cannot cover the payment (above the keep-back
    reserve) records a miss; three misses default the loan and a
    defaulted mortgage forecloses."""
    out = {"repaid_ncr": 0, "missed": [], "defaulted": [],
           "foreclosed": []}
    for loan in store.rows("SELECT * FROM loans WHERE status ="
                           " 'active' ORDER BY loan_id"):
        lid = loan["loan_id"]
        borrower = loan["borrower_character_id"]
        monthly_rate = loan["annual_rate_percent"] / 100 / 12
        interest = round(loan["outstanding_ncr"] * monthly_rate)
        due = finance_mod._monthly_payment(
            loan["principal_ncr"], loan["annual_rate_percent"],
            loan["term_months"])
        due = min(due, loan["outstanding_ncr"] + interest)
        available = 0
        if borrower in ("SYS-CITY",):
            available = max(0, store.balance(borrower))
        else:
            available = max(0, store.balance(borrower)
                            - REPAYMENT_RESERVE_NCR)
        paid = min(due, available)
        if paid > 0:
            store.transfer(borrower, "SYS-BANK", paid,
                           "loan_repayment", game_minutes,
                           note=f"{loan['kind']} repayment",
                           transfer_key=f"repay:{lid}:{month_index}",
                           event_ref=f"month:{month_index}")
        principal_paid = max(0, paid - interest)
        interest_paid = paid - principal_paid
        outstanding = loan["outstanding_ncr"] - principal_paid
        missed = loan["missed_payments"]
        status = "active"
        if paid < due:
            missed += 1
        if outstanding <= 0:
            status = "repaid"
            outstanding = 0
        elif missed >= 3:
            status = "defaulted"
            out["defaulted"].append(lid)
            if loan["kind"] == "mortgage" and loan["property_id"]:
                _foreclose(store, loan, game_minutes)
                out["foreclosed"].append(loan["property_id"])
        if paid < due:
            out["missed"].append(lid)
        store.execute(
            "UPDATE loans SET outstanding_ncr = ?,"
            " interest_paid_ncr = interest_paid_ncr + ?,"
            " missed_payments = ?, months_elapsed = months_elapsed"
            " + 1, status = ?, updated_at_game_minutes = ?"
            " WHERE loan_id = ?",
            (outstanding, interest_paid, missed, status,
             game_minutes, lid))
        out["repaid_ncr"] += paid
    return out


def _foreclose(store, loan, game_minutes):
    """The bank takes the property; the household remains as the
    bank's tenant at the canonical rent (Session 02's join)."""
    pid = loan["property_id"]
    prop = store.row("SELECT * FROM properties WHERE property_id = ?",
                     (pid,))
    if prop is None:
        return
    hid = prop["owner_household_id"]
    store.execute("UPDATE properties SET owner_character_id ="
                  " 'SYS-BANK', owner_household_id = NULL,"
                  " status = 'rented' WHERE property_id = ?", (pid,))
    if hid:
        from . import households as hh_mod
        rent = hh_mod.rent_of_property(store, _data(), prop)
        if rent:
            tid = store.next_id("TN", "tenancies", "tenancy_id")
            store.insert("tenancies", tenancy_id=tid, property_id=pid,
                         tenant_household_id=hid,
                         landlord_character_id="SYS-BANK",
                         rent_per_month=rent,
                         started_at_game_minutes=game_minutes)
    from . import memory as memory_mod
    borrower = loan["borrower_character_id"]
    memory_mod.log_life_event(store, borrower, "foreclosure",
                              game_minutes,
                              details={"property_id": pid,
                                       "loan_id": loan["loan_id"]})


# -- Unit 09: investment ------------------------------------------------

def share_price(store, data, business):
    worth = business_mod.net_worth(store, data, business)
    return max(1, round(worth / TOTAL_SHARES))


def buy_shares(store, data, character_id, business_id, amount,
               game_minutes, *, event_ref=None):
    """Buy equity in a real business at its current model price.
    The money enters the business account (equity financing).
    Returns the investment row, or None when nothing was bought."""
    b = store.row("SELECT * FROM businesses WHERE business_id = ?"
                  " AND closed_at_game_minutes IS NULL",
                  (business_id,))
    if b is None or amount <= 0:
        return None
    price = share_price(store, data, b)
    shares = amount // price
    held = store.row(
        "SELECT COALESCE(SUM(shares),0) AS s FROM investments"
        " WHERE business_id = ? AND status = 'active'",
        (business_id,))["s"]
    shares = min(shares, TOTAL_SHARES - held)
    if shares <= 0:
        return None
    cost = shares * price
    if store.balance(character_id) < cost:
        shares = store.balance(character_id) // price
        cost = shares * price
    if shares <= 0:
        return None
    store.transfer(character_id, None, cost, "investment",
                   game_minutes, note=f"equity in {b['name']}",
                   related_business_id=business_id,
                   event_ref=event_ref, to_business_id=business_id)
    existing = store.row("SELECT * FROM investments WHERE"
                         " character_id = ? AND business_id = ?",
                         (character_id, business_id))
    if existing:
        store.execute(
            "UPDATE investments SET shares = shares + ?,"
            " invested_ncr = invested_ncr + ?, status = 'active',"
            " updated_at_game_minutes = ? WHERE investment_id = ?",
            (shares, cost, game_minutes, existing["investment_id"]))
        iid = existing["investment_id"]
    else:
        iid = store.next_id("IV", "investments", "investment_id")
        store.insert("investments", investment_id=iid,
                     character_id=character_id, business_id=business_id,
                     shares=shares, invested_ncr=cost, status="active",
                     created_at_game_minutes=game_minutes,
                     updated_at_game_minutes=game_minutes)
    business_mod.log_event(store, business_id, "investment",
                           {"character_id": character_id,
                            "shares": shares, "amount_ncr": cost,
                            "price_per_share": price}, game_minutes)
    return store.row("SELECT * FROM investments WHERE investment_id"
                     " = ?", (iid,))


def portfolio_value(store, character_id):
    total = 0
    for inv in store.rows("SELECT * FROM investments WHERE"
                          " character_id = ? AND status = 'active'",
                          (character_id,)):
        b = store.row("SELECT * FROM businesses WHERE business_id"
                      " = ?", (inv["business_id"],))
        if b is None:
            continue
        total += inv["shares"] * share_price(store, _data(), b)
    return total


def pay_dividends(store, data, month_index, game_minutes):
    """Monthly dividends from recorded profit (the latest
    business_monthly row), pro-rata over externally held shares,
    capped so the firm keeps its wage reserve."""
    cfg = data.economy_config["business"]
    paid = {}
    for inv in store.rows(
            "SELECT i.*, b.owner_character_id FROM investments i"
            " JOIN businesses b ON b.business_id = i.business_id"
            " WHERE i.status = 'active' AND i.shares > 0"
            " ORDER BY i.investment_id"):
        bid = inv["business_id"]
        latest = store.row(
            "SELECT profit_ncr FROM business_monthly WHERE"
            " business_id = ? ORDER BY month_index DESC LIMIT 1",
            (bid,))
        if latest is None or latest["profit_ncr"] <= 0:
            continue
        pool = round(latest["profit_ncr"] * DIVIDEND_PAYOUT_RATIO)
        per_share = pool // TOTAL_SHARES
        amount = per_share * inv["shares"]
        if amount <= 0:
            continue
        reserve = business_mod.wage_bill(store, bid) \
            * cfg["wage_reserve_months"]
        if store.business_balance(bid) - amount < reserve:
            continue
        store.transfer(None, inv["character_id"], amount, "dividend",
                       game_minutes, note="business dividend",
                       related_business_id=bid,
                       transfer_key=f"div:{bid}:{inv['character_id']}:"
                                    f"{month_index}",
                       event_ref=f"month:{month_index}",
                       from_business_id=bid)
        paid[inv["character_id"]] = paid.get(inv["character_id"], 0) \
            + amount
    return paid


def monthly_pass(store, data, month_index, game_minutes):
    """Interest + repayments + account opening for new adults.
    (Dividends run after the month's P&L is recorded — see
    engine._monthly_economy.)"""
    from . import identity as identity_mod
    opened = 0
    now = game_minutes
    for c in store.rows("SELECT character_id, born_at_game_minutes"
                        " FROM characters WHERE is_system = 0"
                        " AND died_at_game_minutes IS NULL"):
        if identity_mod.age_years(c["born_at_game_minutes"], now) >= 18:
            if open_account(store, c["character_id"], game_minutes):
                opened += 1
    interest = monthly_interest(store, data, month_index, game_minutes)
    repayments = monthly_repayments(store, data, month_index,
                                    game_minutes)
    return {"accounts_opened": opened, "interest_paid_ncr": interest,
            "repayments": repayments}


def bank_stats(store):
    deposits = store.row("SELECT COALESCE(SUM(balance_cached),0) AS s"
                         " FROM bank_accounts WHERE"
                         " closed_at_game_minutes IS NULL")["s"]
    outstanding = store.row(
        "SELECT COALESCE(SUM(outstanding_ncr),0) AS s FROM loans"
        " WHERE status = 'active'")["s"]
    reserves = store.balance("SYS-BANK")
    return {
        "accounts": store.row("SELECT COUNT(*) AS n FROM bank_accounts"
                              " WHERE closed_at_game_minutes IS NULL"
                              )["n"],
        "deposits_ncr": deposits,
        "loans_outstanding_ncr": outstanding,
        "reserves_ncr": reserves,
        "reserve_ratio": round(reserves / outstanding, 3)
        if outstanding else None,
        "loans_active": store.row("SELECT COUNT(*) AS n FROM loans"
                                  " WHERE status = 'active'")["n"],
        "loans_defaulted": store.row(
            "SELECT COUNT(*) AS n FROM loans WHERE status ="
            " 'defaulted'")["n"],
    }
