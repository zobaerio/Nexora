"""Session 05 Units 06+07+14+15 — Policies, Government Budget,
National Development, and the Government Decision Engine.

A policy is a record with a budget, a timeline, a target and an
expectation — and an effect hook that changes real system
behaviour while it is active:

- employment_programme: the Labour Ministry posts real public-
  works vacancies through the civil-service machinery; the
  workers are really hired and really paid by the treasury.
- welfare_support: real transfers from the treasury to the
  households the records show are poor (the indicators module's
  own poverty line), keyed and event-referenced.
- housing_development: commissions real construction through
  Session 03's civic project path when a city's vacancy is
  under the policy trigger.
- infrastructure_maintenance: pays for real road repairs (the
  Session 03 segments' condition actually rises).
- health_investment: funds additional clinic doctor posts
  through the civil service and records the spend.

Every direct spend carries event_ref = the policy id, so a
policy's spent total is a ledger sum, not a claim; programme
wages are summed from their keyed wage rows. At the end of its
duration a policy is evaluated: the measured outcome (latest
indicators / sim facts) is written next to the expectation it
was approved under.

The budget is an annual cycle on the sim calendar: forecast
from trailing recorded government revenue (internal treasury
allocations are excluded — moving money between government
accounts is not revenue), allocations by configured shares,
approval by a recorded office holder, actuals summed monthly
from the ledger by category, and a closing identity — closing
government balances minus opening balances equals recorded
revenue minus recorded expenditure — that the tests assert to
the NCr. When the national treasury is in overdraft at budget
time, the government may formalise it into an explicit SYS-BANK
loan (Session 04 machinery, sovereign credit assessment): the
implicit debt becomes explicit, never double-counted.

The decision engine is a rule table over measured conditions
(crises, indicators, housing pressure, road condition, doctor
coverage). It proposes and — subject to authority and to any
citizen consultation on the question — approves policies, and
logs every action as a decision of the Prime Minister in the
existing decision_log, with the measured factors attached.
"""
import json

from . import cities as cities_mod
from . import government as gov
from . import indicators as indicators_mod

KIND_INSTITUTION = {
    "employment_programme": "GOV-LABOUR",
    "welfare_support": "GOV-PM",
    "housing_development": "GOV-HOUSING",
    "infrastructure_maintenance": "GOV-HOUSING",
    "health_investment": "GOV-HEALTH",
}
MUNICIPAL_KINDS = ("infrastructure_maintenance",)


# -- policy lifecycle ------------------------------------------------------

def propose_policy(store, data, kind, actor_id, month_index,
                   game_minutes, city_id=None, budget_ncr=None,
                   duration_months=None):
    cfg = data.government_config["policies"][kind]
    if duration_months is None:
        duration_months = cfg["duration_months"]
    if budget_ncr is None:
        budget_ncr = cfg.get("monthly_budget_ncr", 0) \
            * duration_months
        if kind == "employment_programme":
            wage = data.wage("construction_worker", "entry")
            budget_ncr = wage * cfg["posts_per_month"] \
                * duration_months
        elif kind == "housing_development":
            budget_ncr = 0  # construction carries its own funding
    pid = store.next_id("PL", "policies", "policy_id")
    store.insert(
        "policies", policy_id=pid, kind=kind,
        title=f"{kind.replace('_', ' ').title()}"
              + (f" — {city_id}" if city_id else ""),
        institution_id=KIND_INSTITUTION[kind], city_id=city_id,
        proposed_by=actor_id, status="proposed",
        budget_ncr=budget_ncr, duration_months=duration_months,
        expected=json.dumps(_expectation(store, data, kind,
                                         city_id)),
        actual=json.dumps({}), created_month=month_index,
        created_at_game_minutes=game_minutes)
    gov.log_event(store, "policy_proposed", actor_id,
                  {"policy_id": pid, "kind": kind,
                   "city_id": city_id, "budget_ncr": budget_ncr},
                  game_minutes)
    return pid


def _expectation(store, data, kind, city_id):
    """The measurable expectation a policy is approved under:
    the baseline of its target metric, read from the records at
    proposal time."""
    latest = (indicators_mod.latest(store, "national") or {}) \
        .get("metrics") or {}
    if kind == "welfare_support":
        return {"metric": "poverty_rate",
                "baseline": latest.get("poverty_rate"),
                "direction": "decrease"}
    if kind == "employment_programme":
        return {"metric": "unemployment_rate",
                "baseline": latest.get("unemployment_rate"),
                "direction": "decrease"}
    if kind == "housing_development":
        from . import distribution as distribution_mod
        hp = distribution_mod.housing_pressure(store, data,
                                               city_id)
        return {"metric": "vacancy_rate", "city_id": city_id,
                "baseline": hp["vacancy_rate"],
                "direction": "increase_into_band"}
    if kind == "infrastructure_maintenance":
        row = store.row("SELECT AVG(condition) AS c FROM"
                        " road_segments WHERE city_id = ?",
                        (city_id,)) if city_id else store.row(
            "SELECT AVG(condition) AS c FROM road_segments")
        return {"metric": "avg_road_condition",
                "city_id": city_id,
                "baseline": round(row["c"], 1) if row
                and row["c"] is not None else None,
                "direction": "increase"}
    if kind == "health_investment":
        return {"metric": "doctors_employed",
                "baseline": _doctors_employed(store),
                "direction": "increase"}
    return {}


def _doctors_employed(store):
    return store.row("SELECT COUNT(*) AS n FROM employments WHERE"
                     " profession_id = 'doctor' AND"
                     " ended_at_game_minutes IS NULL")["n"]


def approve_policy(store, data, policy_id, actor_id, game_minutes):
    """Approval is an authority act: national policies need the
    executive's approve_policy authority; a city-scoped
    infrastructure policy may instead be approved by that city's
    mayor under municipal authority. Anyone else is refused."""
    policy = store.row("SELECT * FROM policies WHERE policy_id"
                       " = ?", (policy_id,))
    if policy is None or policy["status"] != "proposed":
        raise ValueError(f"policy {policy_id} is not proposed")
    municipal_path = policy["city_id"] and policy["kind"] \
        in MUNICIPAL_KINDS and gov.has_authority(
            store, actor_id, "municipal_policy", policy["city_id"])
    if not municipal_path:
        gov.require_authority(store, actor_id, "approve_policy")
    store.execute("UPDATE policies SET status = 'active',"
                  " approved_by = ? WHERE policy_id = ?",
                  (actor_id, policy_id))
    gov.log_event(store, "policy_approved", actor_id,
                  {"policy_id": policy_id, "kind": policy["kind"],
                   "municipal_path": bool(municipal_path)},
                  game_minutes)
    return policy_id


def funding_account(store, policy):
    if policy["city_id"] and policy["kind"] in MUNICIPAL_KINDS:
        return gov.MUNICIPAL_ACCOUNTS[policy["city_id"]]
    return gov.NATIONAL_ACCOUNT


def policy_spent(store, policy):
    """Exact spend: ledger rows carrying the policy's event_ref,
    plus the keyed wage rows of programme employments it created,
    plus the recorded funding of construction projects it
    commissioned."""
    pid = policy["policy_id"]
    total = store.row(
        "SELECT COALESCE(SUM(amount),0) AS s FROM economy_ledger"
        " WHERE event_ref = ?", (pid,))["s"]
    actual = json.loads(policy["actual"] or "{}")
    for eid in actual.get("employment_ids", []):
        total += store.row(
            "SELECT COALESCE(SUM(amount),0) AS s FROM"
            " economy_ledger WHERE transfer_key LIKE ?",
            (f"gwage:{eid}:%",))["s"]
    for project_id in actual.get("project_ids", []):
        row = store.row("SELECT funding_ncr FROM"
                        " construction_projects WHERE project_id"
                        " = ?", (project_id,))
        if row:
            total += row["funding_ncr"]
    return total


def _set_actual(store, policy, **updates):
    actual = json.loads(policy["actual"] or "{}")
    actual.update(updates)
    store.execute("UPDATE policies SET actual = ? WHERE policy_id"
                  " = ?", (json.dumps(actual, sort_keys=True),
                          policy["policy_id"]))
    policy["actual"] = json.dumps(actual, sort_keys=True)
    return actual


# -- policy effects ----------------------------------------------------------

def _effect_employment(store, data, policy, month_index,
                       game_minutes):
    cfg = data.government_config["policies"][
        "employment_programme"]
    actual = json.loads(policy["actual"] or "{}")
    emp_ids = list(actual.get("employment_ids", []))
    posted = list(actual.get("vacancy_ids", []))
    open_posts = store.row(
        "SELECT COUNT(*) AS n FROM vacancies WHERE"
        " employer_institution_id = 'GOV-LABOUR' AND status ="
        " 'open' AND employer_account_id = 'SYS-CITY'")["n"]
    spent = policy_spent(store, policy)
    wage = data.wage("construction_worker", "entry")
    made = 0
    while open_posts + made < cfg["posts_per_month"] \
            and spent + wage * policy["duration_months"] \
            <= policy["budget_ncr"]:
        vid = store.next_id("VC", "vacancies", "vacancy_id")
        store.insert(
            "vacancies", vacancy_id=vid,
            employer_kind="government", employer_business_id=None,
            profession_id="construction_worker",
            city_id=data.government_config["country"]
            ["capital_city_id"], wage_per_month=wage,
            status="open", posted_month=month_index,
            created_at_game_minutes=game_minutes,
            employer_account_id=gov.NATIONAL_ACCOUNT,
            employer_institution_id="GOV-LABOUR")
        posted.append(vid)
        made += 1
    # Record programme employments as the civil-service pass
    # fills the programme's vacancies.
    for vid in posted:
        v = store.row("SELECT * FROM vacancies WHERE vacancy_id"
                      " = ?", (vid,))
        if v and v["status"] == "filled" \
                and v["filled_by_character_id"]:
            emp = store.row(
                "SELECT employment_id FROM employments WHERE"
                " character_id = ? AND ended_at_game_minutes"
                " IS NULL", (v["filled_by_character_id"],))
            if emp and emp["employment_id"] not in emp_ids:
                emp_ids.append(emp["employment_id"])
    _set_actual(store, policy, vacancy_ids=posted,
                employment_ids=emp_ids)
    return {"posted": made, "programme_employments": len(emp_ids)}


def _effect_welfare(store, data, policy, month_index, game_minutes):
    cfg = data.government_config["policies"]["welfare_support"]
    line = indicators_mod.poverty_line(data)
    monthly_cap = cfg["monthly_budget_ncr"]
    spent_this = 0
    helped = 0
    rows = store.rows(
        "SELECT hf.household_id, hf.income_ncr FROM"
        " household_finances hf WHERE hf.month_index = (SELECT"
        " MAX(month_index) FROM household_finances) ORDER BY"
        " hf.income_ncr ASC")
    for r in rows:
        if spent_this >= monthly_cap:
            break
        top_up = line - r["income_ncr"]
        if top_up <= 0:
            continue
        head = store.row(
            "SELECT character_id FROM household_members WHERE"
            " household_id = ? AND role = 'head' AND"
            " left_at_game_minutes IS NULL", (r["household_id"],))
        if head is None:
            continue
        pay = min(top_up, monthly_cap - spent_this)
        if pay <= 0:
            continue
        store.transfer(
            gov.NATIONAL_ACCOUNT, head["character_id"], pay,
            "welfare", game_minutes,
            note=f"welfare support {policy['policy_id']}",
            transfer_key=f"welfare:{policy['policy_id']}:"
                         f"{r['household_id']}:{month_index}",
            event_ref=policy["policy_id"])
        spent_this += pay
        helped += 1
    return {"households_helped": helped, "spent_ncr": spent_this}


def _effect_housing(store, data, policy, month_index, game_minutes):
    from . import construction as construction_mod
    from . import distribution as distribution_mod
    cfg = data.government_config["policies"]["housing_development"]
    city_id = policy["city_id"]
    if not city_id:
        return {"commissioned": None}
    hp = distribution_mod.housing_pressure(store, data, city_id)
    active = store.row(
        "SELECT COUNT(*) AS n FROM construction_projects WHERE"
        " city_id = ? AND status IN ('active', 'stalled_funding')",
        (city_id,))["n"]
    if hp["vacancy_rate"] >= cfg["vacancy_trigger"] or active:
        return {"commissioned": None,
                "vacancy_rate": hp["vacancy_rate"]}
    pid = construction_mod.start_civic_project(
        store, data, city_id, game_minutes,
        store.world()["day_index"])
    if pid:
        actual = json.loads(policy["actual"] or "{}")
        projects = list(actual.get("project_ids", []))
        projects.append(pid)
        _set_actual(store, policy, project_ids=projects)
    return {"commissioned": pid, "vacancy_rate": hp["vacancy_rate"]}


def _effect_infrastructure(store, data, policy, month_index,
                           game_minutes):
    from . import services as services_mod
    cfg = data.government_config["policies"][
        "infrastructure_maintenance"]
    account = funding_account(store, policy)
    target = cfg["road_target_condition"]
    monthly_cap = cfg["monthly_budget_ncr"]
    spent = 0
    cities = [policy["city_id"]] if policy["city_id"] else [
        s["city_id"] for s in data.city_specs()]
    for city_id in cities:
        if spent >= monthly_cap:
            break
        worst = store.rows(
            "SELECT * FROM road_segments WHERE city_id = ? AND"
            " condition < ? ORDER BY condition ASC, segment_id"
            " ASC", (city_id, target))
        for s in worst:
            if spent >= monthly_cap:
                break
            deficit = target - s["condition"]
            cost = int(s["length_m"] * deficit
                       * services_mod.ROAD_REPAIR_NCR_PER_M_POINT)
            if cost <= 0:
                continue
            available = store.balance(account)
            pay = min(cost, monthly_cap - spent,
                      available if account != gov.NATIONAL_ACCOUNT
                      else cost)
            if pay <= 0:
                continue
            store.transfer(
                account, "SYS-MARKET", pay, "policy_spend",
                game_minutes,
                note=f"road maintenance {s['segment_id']}"
                     f" ({policy['policy_id']})",
                transfer_key=f"policy:{policy['policy_id']}:"
                             f"{s['segment_id']}:{month_index}",
                event_ref=policy["policy_id"])
            restored = pay / (s["length_m"]
                              * services_mod
                              .ROAD_REPAIR_NCR_PER_M_POINT) \
                if s["length_m"] else 0
            store.execute(
                "UPDATE road_segments SET condition = ? WHERE"
                " segment_id = ?",
                (round(min(98.0, s["condition"] + restored), 2),
                 s["segment_id"]))
            spent += pay
    return {"spent_ncr": spent}


def _effect_health(store, data, policy, month_index, game_minutes):
    cfg = data.government_config["policies"]["health_investment"]
    pay = cfg["monthly_budget_ncr"]
    store.transfer(
        gov.NATIONAL_ACCOUNT, "SYS-MARKET", pay, "policy_spend",
        game_minutes, note="clinic investment"
        f" ({policy['policy_id']})",
        transfer_key=f"policy:{policy['policy_id']}:health:"
                     f"{month_index}",
        event_ref=policy["policy_id"])
    return {"spent_ncr": pay,
            "doctors_employed": _doctors_employed(store)}


_EFFECTS = {
    "employment_programme": _effect_employment,
    "welfare_support": _effect_welfare,
    "housing_development": _effect_housing,
    "infrastructure_maintenance": _effect_infrastructure,
    "health_investment": _effect_health,
}


def _evaluate(store, data, policy, game_minutes):
    """Write the measured outcome next to the expectation and
    close the policy."""
    kind = policy["kind"]
    latest = (indicators_mod.latest(store, "national") or {}) \
        .get("metrics") or {}
    actual = json.loads(policy["actual"] or "{}")
    if kind == "welfare_support":
        actual["poverty_rate_after"] = latest.get("poverty_rate")
    elif kind == "employment_programme":
        actual["unemployment_rate_after"] = latest.get(
            "unemployment_rate")
    elif kind == "housing_development":
        from . import distribution as distribution_mod
        if policy["city_id"]:
            actual["vacancy_rate_after"] = \
                distribution_mod.housing_pressure(
                    store, data, policy["city_id"])["vacancy_rate"]
    elif kind == "infrastructure_maintenance":
        row = store.row("SELECT AVG(condition) AS c FROM"
                        " road_segments WHERE city_id = ?",
                        (policy["city_id"],)) if policy["city_id"] \
            else store.row("SELECT AVG(condition) AS c FROM"
                           " road_segments")
        actual["avg_road_condition_after"] = round(
            row["c"], 1) if row and row["c"] is not None else None
    elif kind == "health_investment":
        actual["doctors_employed_after"] = _doctors_employed(store)
    actual["spent_ncr"] = policy_spent(store, policy)
    store.execute(
        "UPDATE policies SET status = 'completed', actual = ?,"
        " ended_at_game_minutes = ? WHERE policy_id = ?",
        (json.dumps(actual, sort_keys=True), game_minutes,
         policy["policy_id"]))
    gov.log_event(store, "policy_evaluated",
                  policy["approved_by"],
                  {"policy_id": policy["policy_id"], "kind": kind,
                   "spent_ncr": actual["spent_ncr"],
                   "expected": json.loads(policy["expected"]
                                          or "{}")},
                  game_minutes)


def monthly_pass(store, data, month_index, game_minutes):
    if not gov.is_setup(store):
        return None
    out = {}
    for policy in store.rows("SELECT * FROM policies WHERE status"
                             " = 'active' ORDER BY policy_id"):
        result = _EFFECTS[policy["kind"]](
            store, data, policy, month_index, game_minutes)
        months_run = policy["months_run"] + 1
        store.execute("UPDATE policies SET months_run = ? WHERE"
                      " policy_id = ?",
                      (months_run, policy["policy_id"]))
        out[policy["policy_id"]] = result
        if months_run >= policy["duration_months"]:
            fresh = store.row("SELECT * FROM policies WHERE"
                              " policy_id = ?",
                              (policy["policy_id"],))
            _evaluate(store, data, fresh, game_minutes)
    return out


# -- the annual budget (Unit 07) ---------------------------------------------

def _government_revenue(store, since, until):
    """Recorded revenue of all government accounts: inflows from
    OUTSIDE the government (internal allocations excluded), loan
    disbursements excluded (borrowing is not revenue)."""
    accounts = ", ".join(f"'{a}'" for a in gov.TREASURY_ACCOUNTS)
    row = store.row(
        f"SELECT COALESCE(SUM(amount),0) AS s FROM economy_ledger"
        f" WHERE to_character_id IN ({accounts}) AND"
        f" (from_character_id IS NULL OR from_character_id NOT IN"
        f" ({accounts})) AND reason_code !="
        f" 'loan_disbursement' AND game_minutes > ? AND"
        f" game_minutes <= ?", (since, until))
    return row["s"]


def _government_spend_by_category(store, since, until):
    """Recorded expenditure of all government accounts, by
    budget category, summed from the ledger itself."""
    accounts = ", ".join(f"'{a}'" for a in gov.TREASURY_ACCOUNTS)
    cats = {"administration": 0, "services": 0, "policies": 0,
            "infrastructure": 0, "welfare": 0, "debt_service": 0,
            "other": 0}

    def add(reason_codes, category, from_business=False):
        col = "from_business_id" if from_business else \
            "from_character_id"
        marks = ", ".join(f"'{r}'" for r in reason_codes)
        row = store.row(
            f"SELECT COALESCE(SUM(amount),0) AS s FROM"
            f" economy_ledger WHERE {col} IN ({accounts}) AND"
            f" reason_code IN ({marks}) AND game_minutes > ?"
            f" AND game_minutes <= ?", (since, until))
        cats[category] += row["s"]

    add(("wage", "office_allowance", "pension"), "administration")
    add(("municipal_service",), "services")
    add(("policy_spend",), "policies")
    add(("welfare",), "welfare")
    add(("construction_funding",), "infrastructure")
    add(("loan_repayment",), "debt_service")
    total = store.row(
        f"SELECT COALESCE(SUM(amount),0) AS s FROM economy_ledger"
        f" WHERE from_character_id IN ({accounts}) AND"
        f" (to_character_id IS NULL OR to_character_id NOT IN"
        f" ({accounts})) AND game_minutes > ? AND game_minutes"
        f" <= ?", (since, until))["s"]
    cats["other"] = total - sum(cats.values())
    cats["total"] = total
    return cats


def budget_pass(store, data, month_index, game_minutes):
    """Annual cycle: at each fiscal-year boundary (months 12, 24,
    ...) close the running budget with its measured actuals and
    open the next year's — forecast from the trailing twelve
    months of recorded revenue, allocations by configured
    shares, approval recorded, and any national overdraft
    formalised into an explicit bank loan where the bank's
    sovereign assessment allows it."""
    if not gov.is_setup(store):
        return None
    out = {}
    # Keep the open budget's actuals current every month.
    open_budget = store.row("SELECT * FROM budgets WHERE status"
                            " IN ('draft', 'approved') ORDER BY"
                            " fiscal_year DESC LIMIT 1")
    if open_budget:
        since = game_minutes - (month_index
                                - (open_budget["fiscal_year"] - 1)
                                * 12) * 30 * 1440
        actuals = {
            "revenue_ncr": _government_revenue(store, since,
                                               game_minutes),
            "spend": _government_spend_by_category(store, since,
                                                   game_minutes),
            "balances_now": gov.government_balances(store),
        }
        store.execute("UPDATE budgets SET actuals = ? WHERE"
                      " budget_id = ?",
                      (json.dumps(actuals, sort_keys=True),
                       open_budget["budget_id"]))
    if month_index % 12 != 0 or month_index == 0:
        return out or None
    fiscal_year = month_index // 12 + 1
    if store.row("SELECT 1 FROM budgets WHERE fiscal_year = ?",
                 (fiscal_year,)):
        return out or None
    if open_budget:
        store.execute("UPDATE budgets SET status = 'closed',"
                      " closed_at_game_minutes = ? WHERE"
                      " budget_id = ?",
                      (game_minutes, open_budget["budget_id"]))
        out["closed"] = open_budget["budget_id"]
    trailing_since = game_minutes - 12 * 30 * 1440
    forecast = _government_revenue(store, trailing_since,
                                   game_minutes)
    shares = data.government_config["budget"][
        "allocation_shares"]
    allocations = {k: int(forecast * v) for k, v in shares.items()}
    bid = store.next_id("BG", "budgets", "budget_id")
    opening = gov.government_balances(store)
    store.insert(
        "budgets", budget_id=bid, fiscal_year=fiscal_year,
        status="draft", forecast_revenue_ncr=forecast,
        allocations=json.dumps(allocations, sort_keys=True),
        actuals=json.dumps({"opening_balances": opening,
                            "revenue_ncr": 0, "spend": {}}),
        created_month=month_index,
        created_at_game_minutes=game_minutes)
    # Approval: the Speaker of Parliament approves the budget
    # (legislative authority); before the first parliament, the
    # caretaker Prime Minister records the approval instead.
    speaker = gov.office_holder(store, "speaker", "GOV-PARLIAMENT")
    approver = speaker["holder_character_id"] if speaker else None
    via = "parliament"
    if approver is None:
        pm = gov.office_holder(store, "prime_minister", "GOV-PM")
        approver = pm["holder_character_id"] if pm else None
        via = "caretaker_executive"
    if approver is not None:
        if via == "parliament":
            gov.require_authority(store, approver, "approve_budget")
        store.execute("UPDATE budgets SET status = 'approved',"
                      " approved_by = ? WHERE budget_id = ?",
                      (approver, bid))
        out["approved_by"] = approver
    gov.log_event(store, "budget_adopted", approver,
                  {"budget_id": bid, "fiscal_year": fiscal_year,
                   "forecast_revenue_ncr": forecast, "via": via},
                  game_minutes)
    out["budget_id"] = bid
    # Borrowing: formalise an overdraft into explicit debt.
    balance = store.balance(gov.NATIONAL_ACCOUNT)
    if balance < 0:
        from . import banking as banking_mod
        credit = banking_mod.assess_credit(store, data,
                                           gov.NATIONAL_ACCOUNT)
        amount = min(-balance, credit["max_bank_loan_ncr"])
        if amount > 0:
            loan = banking_mod.disburse_loan(
                store, data, gov.NATIONAL_ACCOUNT, "bank_loan",
                amount, game_minutes)
            if loan:
                store.execute("UPDATE budgets SET"
                              " borrowed_loan_id = ? WHERE"
                              " budget_id = ?",
                              (loan["loan_id"], bid))
                gov.log_event(store, "public_borrowing", approver,
                              {"loan_id": loan["loan_id"],
                               "amount_ncr": amount,
                               "rate_percent":
                               loan["annual_rate_percent"],
                               "budget_id": bid}, game_minutes)
                out["borrowed_loan_id"] = loan["loan_id"]
    return out


def public_debt(store):
    """The explicit public debt position: outstanding SYS-BANK
    loans to the treasury plus any remaining implicit overdraft.
    The two never double-count — a disbursement raises the
    balance it borrows against."""
    loans = store.rows("SELECT * FROM loans WHERE"
                       " borrower_character_id = ? AND status"
                       " IN ('active', 'defaulted')",
                       (gov.NATIONAL_ACCOUNT,))
    explicit = sum(l["outstanding_ncr"] for l in loans)
    implicit = max(0, -store.balance(gov.NATIONAL_ACCOUNT))
    return {"explicit_loans_ncr": explicit,
            "implicit_overdraft_ncr": implicit,
            "total_ncr": explicit + implicit,
            "loans": [l["loan_id"] for l in loans]}


# -- national development (Unit 14) -------------------------------------------

def _current_facts(store, data):
    from . import distribution as distribution_mod
    latest = (indicators_mod.latest(store, "national") or {}) \
        .get("metrics") or {}
    roads = store.row("SELECT AVG(condition) AS c FROM"
                      " road_segments")
    pop = max(1, store.row(
        "SELECT COUNT(*) AS n FROM characters WHERE is_system = 0"
        " AND died_at_game_minutes IS NULL")["n"])
    vacancy = None
    if cities_mod.is_setup(store):
        rates = [distribution_mod.housing_pressure(
            store, data, s["city_id"])["vacancy_rate"]
            for s in data.city_specs()]
        vacancy = round(sum(rates) / len(rates), 4) if rates \
            else None
    return {
        "unemployment_rate": latest.get("unemployment_rate"),
        "poverty_rate": latest.get("poverty_rate"),
        "avg_road_condition": round(roads["c"], 1)
        if roads and roads["c"] is not None else None,
        "doctors_per_100": round(_doctors_employed(store)
                                 / pop * 100, 3),
        "housing_vacancy_avg": vacancy,
    }


def create_default_plan(store, data, game_minutes):
    cfg = data.government_config["development_plan"]
    existing = store.row("SELECT * FROM development_plans WHERE"
                         " name = ?", (cfg["name"],))
    if existing:
        return existing["plan_id"]
    pid = store.next_id("DP", "development_plans", "plan_id")
    store.insert(
        "development_plans", plan_id=pid, name=cfg["name"],
        targets=json.dumps(cfg["targets"], sort_keys=True),
        baseline=json.dumps(_current_facts(store, data),
                            sort_keys=True),
        status="active",
        created_month=(game_minutes // 43200),
        created_at_game_minutes=game_minutes)
    return pid


def plan_progress(store, data, plan_id=None):
    """Plan vs actual, measured only from indicators and sim
    facts — the same _current_facts surface the baseline used."""
    plan = store.row("SELECT * FROM development_plans WHERE"
                     " plan_id = ?", (plan_id,)) if plan_id \
        else store.row("SELECT * FROM development_plans WHERE"
                       " status = 'active' ORDER BY plan_id"
                       " LIMIT 1")
    if plan is None:
        return None
    targets = json.loads(plan["targets"])
    facts = _current_facts(store, data)
    checks = {}
    if "unemployment_rate_max" in targets:
        v = facts["unemployment_rate"]
        checks["unemployment_rate"] = {
            "target_max": targets["unemployment_rate_max"],
            "actual": v, "met": v is not None
            and v <= targets["unemployment_rate_max"]}
    if "poverty_rate_max" in targets:
        v = facts["poverty_rate"]
        checks["poverty_rate"] = {
            "target_max": targets["poverty_rate_max"],
            "actual": v, "met": v is not None
            and v <= targets["poverty_rate_max"]}
    if "avg_road_condition_min" in targets:
        v = facts["avg_road_condition"]
        checks["avg_road_condition"] = {
            "target_min": targets["avg_road_condition_min"],
            "actual": v, "met": v is not None
            and v >= targets["avg_road_condition_min"]}
    if "doctors_per_100_min" in targets:
        v = facts["doctors_per_100"]
        checks["doctors_per_100"] = {
            "target_min": targets["doctors_per_100_min"],
            "actual": v, "met": v is not None
            and v >= targets["doctors_per_100_min"]}
    if "housing_vacancy_band" in targets:
        lo, hi = targets["housing_vacancy_band"]
        v = facts["housing_vacancy_avg"]
        checks["housing_vacancy_avg"] = {
            "target_band": [lo, hi], "actual": v,
            "met": v is not None and lo <= v <= hi}
    return {"plan_id": plan["plan_id"], "name": plan["name"],
            "baseline": json.loads(plan["baseline"]),
            "checks": checks}


# -- the government decision engine (Unit 15) ---------------------------------

_KIND_TOPIC = {
    "welfare_support": ("welfare_support", "welfare"),
    "employment_programme": ("employment_programme", "economy"),
    "housing_development": ("housing_development", "development"),
    "infrastructure_maintenance": ("infrastructure", "services"),
    "health_investment": ("health_investment", "services"),
}


def _consultation_gate(store, kind, game_minutes):
    """Citizen participation with consequences: the first time a
    trigger fires, the government consults; approval waits for
    the recorded outcome, and a consultation the citizens opposed
    blocks the policy this cycle."""
    from . import politics as politics_mod
    topic, dimension = _KIND_TOPIC[kind]
    rows = store.rows(
        "SELECT * FROM citizen_feedback WHERE kind ="
        " 'consultation' AND topic = ? ORDER BY feedback_id",
        (topic,))
    if not rows:
        politics_mod.open_consultation(
            store, topic, {"dimension": dimension, "kind": kind},
            game_minutes)
        return "pending"
    latest = rows[-1]
    if latest["status"] == "open":
        return "pending"
    outcome = json.loads(latest["response"] or "{}")
    if outcome.get("oppose", 0) > outcome.get("support", 0):
        return "blocked"
    return "ok"


def decision_engine_pass(store, data, rng, month_index,
                         game_minutes):
    """Measured conditions -> traceable government action. Every
    action is a decision_log entry for the Prime Minister with
    the measured factors, plus a government event, plus the
    policy record itself."""
    from . import decisions as decisions_mod
    from . import distribution as distribution_mod
    if not gov.is_setup(store):
        return None
    pm_office = gov.office_holder(store, "prime_minister", "GOV-PM")
    if pm_office is None or not pm_office["holder_character_id"]:
        return {"decisions": [], "note": "no prime minister seated"}
    pm = pm_office["holder_character_id"]
    cfg = data.government_config["decision_engine"]
    latest = (indicators_mod.latest(store, "national") or {}) \
        .get("metrics") or {}
    active_kinds = {p["kind"] for p in store.rows(
        "SELECT kind FROM policies WHERE status IN ('proposed',"
        " 'active')")}
    proposed_kinds = {p["kind"] for p in store.rows(
        "SELECT kind FROM policies WHERE status = 'proposed'")}
    facts = _current_facts(store, data)
    triggers = []
    unemployment = latest.get("unemployment_rate") or 0
    if unemployment * 100 > cfg["unemployment_trigger_percent"]:
        triggers.append(("employment_programme", None,
                         {"unemployment_rate": unemployment}))
    poverty = latest.get("poverty_rate") or 0
    if poverty * 100 > cfg["poverty_trigger_percent"]:
        triggers.append(("welfare_support", None,
                         {"poverty_rate": poverty}))
    if cities_mod.is_setup(store):
        for spec in data.city_specs():
            hp = distribution_mod.housing_pressure(
                store, data, spec["city_id"])
            if hp["vacancy_rate"] < cfg["housing_vacancy_trigger"]:
                triggers.append(("housing_development",
                                 spec["city_id"],
                                 {"vacancy_rate": hp[
                                     "vacancy_rate"],
                                  "city_id": spec["city_id"]}))
            row = store.row("SELECT AVG(condition) AS c FROM"
                            " road_segments WHERE city_id = ?",
                            (spec["city_id"],))
            if row and row["c"] is not None and row["c"] \
                    < cfg["road_condition_trigger"]:
                triggers.append(("infrastructure_maintenance",
                                 spec["city_id"],
                                 {"avg_road_condition":
                                  round(row["c"], 1),
                                  "city_id": spec["city_id"]}))
    if facts["doctors_per_100"] < cfg["doctor_per_100_trigger"]:
        triggers.append(("health_investment", None,
                         {"doctors_per_100":
                          facts["doctors_per_100"]}))
    made = []
    for kind, city_id, measured in triggers:
        if kind in active_kinds and kind not in proposed_kinds:
            continue
        gate = _consultation_gate(store, kind, game_minutes)
        factors = {"trigger": measured, "consultation": gate,
                   "month_index": month_index}
        if gate == "pending":
            decisions_mod.log_decision(
                store, pm, "government_consultation", factors,
                {"kind": kind, "city_id": city_id}, game_minutes)
            made.append({"kind": kind, "action": "consultation"})
            continue
        if gate == "blocked":
            decisions_mod.log_decision(
                store, pm, "government_policy_blocked", factors,
                {"kind": kind, "city_id": city_id}, game_minutes)
            made.append({"kind": kind, "action": "blocked"})
            continue
        pid = propose_policy(store, data, kind, pm, month_index,
                             game_minutes, city_id=city_id)
        approve_policy(store, data, pid, pm, game_minutes)
        decisions_mod.log_decision(
            store, pm, "government_policy", factors,
            {"policy_id": pid, "kind": kind, "city_id": city_id},
            game_minutes)
        gov.log_event(store, "policy_decision", pm,
                      {"policy_id": pid, "kind": kind,
                       "city_id": city_id, "factors": measured},
                      game_minutes)
        made.append({"kind": kind, "action": "approved",
                     "policy_id": pid})
        active_kinds.add(kind)
    return {"decisions": made}
