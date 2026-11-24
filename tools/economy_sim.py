#!/usr/bin/env python3
"""NEXORA — Economy Balance Simulator v7 (Unit FB, Queue 23).

Simulates 30 game-days of household cashflow for every profession in
data/prices.json (wages_monthly) at entry / mid / senior tiers.
Deterministic — no randomness; the same input always produces the
same report.

What v7 changes vs v6 (Queue 23, Unit FB — the storm-position
follow-up):
- `simulate()` takes an optional `storm_days` (distinct 1-based
  days of the 30-day month): worked days are 30 minus the storm
  days, gross is band x worked/30 as in v6, and the pay lands
  only on worked days — (gross-tax)/worked per worked day, 0 on
  a storm day — so the month-1 minimum balance depends on where
  the storms fall. The total is still exactly gross-tax, so the
  trajectory still ends at net for every position (pinned by a
  test). A storm_days that disagrees with day_wage_worked_days,
  names a day outside 1..30, or repeats a day is refused; it is
  refused for any non-day-wage profession too. Without
  storm_days the v6 even accrual is unchanged.
- The default run gains a day-wage storm-position section: the
  same measured 28 worked days, with the two storm days early
  (1-2), mid (15-16), late (29-30), and at the measured position
  (3 and 22 — where the live month's storms actually fell), plus
  the v6 even-spread baseline for comparison. The net is the same
  for every position; only the month-1 minbal moves, and that is
  now a measured figure per position. The v6 section is unchanged
  (its minbal stays the even-spread figure). The pinned md5 moves
  to the v7 baseline (the v6 md5 is kept in test_no_regression.py
  as history). No tuning call: the storm month is weather, not a
  balance problem.
- Queue 24 adds two follow-ups to v7 (Units GC–GE, same version):
  Unit GC checks the tool against the settlement and finds the
  recorded "measured" position (days 3 and 22) is the 0-based day
  indices — the settlement's storms fall on 1-based days 4 and 23
  (docs/ECONOMY-SIM-REPORT-V7.md §6); Unit GD adds the
  two-earner storm-position scenario below; Unit GE wires the
  worst storm-position dip into the bridge check. The pinned md5
  moves again (the v7 md5 is kept in test_no_regression.py as
  history).

What v7 adds vs v6, Queue 24 Unit GD (the two-earner
storm-position scenario):
- `simulate()` takes an optional `second_earner` (default
  False): a second construction worker at the same tier, on the
  same storm days and the same day-wage rule. Gross and tax are
  doubled per earner (each earner is taxed on their own gross,
  as the settlement taxes each earner on what they received);
  the household costs follow `engine._living_costs` for two
  adults — food and clothing scaled ×2, transport and eating out
  scaled ×2 (both are per-earner lines in `_living_costs`),
  utilities / services / medical and rent flat, and the
  lifestyle uplift doubled (the settlement sums it per earner).
  The default run gains a two-earner storm-position section
  beside the single-earner one. `second_earner` is refused for
  any non-day-wage profession and together with the v3
  side-income/expense lines (those belong to one person; a
  two-earner household with side income needs a split this unit
  does not design). No tuning call: the storm month is weather,
  not a balance problem — and the finding here is that a second
  earner does not help the early-position dip at all (no pay has
  arrived for anyone on days 1–2), it only helps once pay starts
  landing.
- Run: python3 tools/economy_sim.py [--shibnagar] [--v3|--v4]

What v7 adds vs v6, Queue 24 Unit GE (the storm-position bridge
line):
- The first-month bridge check prints a second line for the
  construction_worker entry row: starting balance + the worst
  storm-position minbal (the minimum across the early / mid /
  late / measured positions) = the worst storm-month balance. A
  failing storm line joins BRIDGE FAIL. The storm bridge is now
  part of the tool's output rather than a report-only observation
  (V7 §5: entry 5,000 − 500 = 4,500). The pinned md5 moves again
  (the v7 md5 is kept in test_no_regression.py as history).

What v6 changes vs v5 (Queue 22, Unit EY — the ES day-wage
follow-up):
- The construction worker is now modelled on the settlement's
  day-wage rule (tools/sim/labour.py: paid worked days x
  (wage_per_month / 30)) instead of the v5 "daily" schedule, which
  paid (gross-tax)/26 on days 1-26 excluding Sundays — 23 pay days,
  23/26 of the band in trajectory terms, while the headline net
  still showed the full band (the trajectory and the headline
  disagreed by 3/26 of the band). The sim's scheduler gives a
  construction worker a work block on all 30 days of a normal
  month (measured: instantiate() over days 0-29 finds work every
  day — Friday keeps the morning shift, Saturday and Sunday are
  unmodified), so a normal month pays exactly the band and the
  headline net/rate for the profession are UNCHANGED by this
  correction — the fix is the trajectory's internal consistency
  (it now ends exactly at net, proven by the new end_balance
  return) and the correct per-day rate. The default run's base
  table is therefore byte-identical to v5 except for the new
  day-wage section below — the pinned md5 moves to the v6
  baseline (the v5 md5 is kept in test_no_regression.py as
  history).
- The default run gains a day-wage storm-month section: the
  measured live month (seeded 30-day engine run, 4 construction
  workers) had 28 worked days of 30 — days 3 and 22 were storm
  days, and the scheduler's strong-cover-seeking rule bent both
  work blocks home (outdoor_work_suspended), so the settlement
  paid 28/30 of the band (entry 8,400 of 9,000). The section
  re-runs the three construction tiers at 28 worked days
  (simulate(..., day_wage_worked_days=28)): gross = band x 28/30,
  tax recomputed on the reduced gross, the reduced pay accruing
  evenly (the tool does not model which days storms fall on — the
  measured run's storm days are recorded in the report, not
  hardcoded here). No tuning call: the storm month is weather,
  not a balance problem — the entry row stays above TIGHT.
- Run: python3 tools/economy_sim.py [--shibnagar] [--v3|--v4]

What v5 adds vs v4 (Queue 9, Unit AX — the Shibnagar variant):
- A `--shibnagar` flag runs the same 30-day simulation over Shibnagar
  Town's priced residential stock (data/city2-shibnagar.json) instead
  of District 1's tier rents. The variant reads the town's rents from
  the city file (residential properties only: apartment/house with a
  rent), asserts each tier's rent equals the prices.json tier table
  (they do: 2500/4000/6000 for tiers 1/2/3), and refuses to run if
  the city data ever drifts from the table — no silent stale numbers.
- Shibnagar has no tier-4 or tier-5 residential stock (its top home
  is the tier-3 Houses B at 6000), so the three professions the
  District 1 table houses at tier 4 (doctor, business_owner, pilot)
  are capped at tier 3 in the variant — recorded as the variant's one
  rule, not hidden. Every other profession keeps its tier, so their
  rows are identical to District 1 by construction; the report says so
  instead of pretending the variant re-proves them.
- The default run is BYTE-IDENTICAL to v4 (the pinned md5 in
  tools/sim/tests/test_no_regression.py is untouched): the variant is
  an additive flag, simulate() takes an optional rent_override that
  defaults to the tier-table rent, and no wage band, rent tier,
  living-cost line or tax rule moves.
- Run: python3 tools/economy_sim.py [--shibnagar] [--v3|--v4]

What v4 changes vs v3 (Queue 7, Unit AJ — closes the v3 report §5
open item):
- The medical_monthly line (300/500/800 by band, Unit AI) is now
  charged in the base table: simulate() adds the household's band
  line to monthly costs for every row, business professions included
  (a plain expense — tax is computed on profit/gross first, so no
  tax-split issue, and the v3 business ValueError path is untouched).
- The pinned baseline md5 in tools/sim/tests/test_no_regression.py
  is updated to the new default-run md5 (the v2 md5 is kept in a
  comment there as history). The life-sim reconciliation is kept:
  tools/sim/engine.py _living_costs charges the same flat
  per-household medical line, so a one-adult household still reduces
  exactly to simulate() (acceptance test, ±2 tolerance).
- The --v3/--v4 scenarios drop the four medical scenarios — they
  would double-charge now that the line is in the base — and keep
  the five tutoring/part-time scenarios plus the medicine-basket
  check. --v3 is kept as an alias for the same section.
- Run: python3 tools/economy_sim.py [--v3|--v4]

What v2 changes vs v1 (Queue 4, fixing the v1 report's findings):
- Finding 1 (fixed in data, Unit U): cab rental now reads 200 NCr/day
  from prices.json — the renting-cab row is survivable.
- Finding 2 (Unit V): living costs scale with tier. Two new monthly
  lines from prices.json living_costs_monthly (eating_out_monthly,
  household_services_monthly) plus the lifestyle uplift: a household
  consumes lifestyle_uplift.percent_of_raise_consumed (35%) of any
  raise above its entry wage. No band cliffs, no new price lists.
- Finding 3 (Unit W): professions carry starting_balance_ncr in
  data/professions.json. The table's minbal column is still computed
  from a zero start (comparable with v1); a separate bridge check
  applies each profession's starting balance to its entry row and
  verifies the month-1 minimum never goes below zero.
- Finding 6 (Unit X): shop_owner and business_owner are no longer
  pre-cost upper bounds. Their bands are business PROFIT (GDD-03 §2:
  "Profit, not wage"; professions.json income_note: revenue minus
  stock, rent and staff). prices.json business_model carries the full
  P&L per tier (revenue, stock %, premises, staff, other); the sim
  computes profit from it, reconciles it against the canonical band,
  taxes it at the 8% business rate (GDD-03 §4.2) instead of personal
  income tax, and runs the household on profit minus tax.

What v3 adds (Queue 6, Units AH + AI) — and what it deliberately
does NOT change:
- The new lines are modelled as additive household scenarios behind
  a `--v3` flag: tutoring income/expense (300/session x 8/mo),
  part-time income (150/block x 16/mo) and the medicine expense
  (medical_monthly 300/500/800 by band). `simulate()` takes them as
  optional keyword arguments, all defaulting to 0, so every existing
  caller (tools/sim/dataio.py, the acceptance test) is unaffected.
- The default run is BYTE-IDENTICAL to v2. This is not cosmetic:
  tools/sim/tests/test_no_regression.py pins this tool's stdout md5,
  and the life-sim acceptance test requires a single-adult teacher
  household to net exactly what simulate() computes. Folding the
  medical line into the base table would break both — and updating
  the pinned baseline md5 is a change to a test file, outside this
  unit's scope. So v3 reports the new lines' effect as scenarios
  (docs/ECONOMY-SIM-REPORT-V3.md §5 records the open item honestly)
  instead of silently moving the baseline. Unit AJ (v4, this version)
  is the follow-up that does the fold-in, with the baseline update —
  see docs/ECONOMY-SIM-REPORT-V4.md.
- Extra income is taxed marginally on the combined gross (wage rows
  only); business professions with extras raise ValueError — a
  business household mixing personal side-income with profit needs a
  business+personal split this unit does not design.
- Run: python3 tools/economy_sim.py [--v3]

Household model (unchanged from v1 unless listed above):
- One adult, living alone, renting at the tier assigned in RENT_TIER.
- Lifestyle band from entry wage: lower <= 15,000, mid <= 40,000,
  else upper (food / utilities / clothing / eating out / services).
- Transport: public (bus/rickshaw) at the lifestyle band, except
  doctor, business_owner and pilot, who run a car.
- Income tax: marginal, from prices.json tax brackets (wage rows).
- Pay schedules: monthly wages land on day 30; daily wages pay on 26
  work days; per_fare accrues evenly. Business timing: shop takings
  accrue evenly (daily takings land in the ledger, GDD-03 §7); the
  business owner's monthly draw lands on day 30 (§5).
- Taxi driver is modelled twice: owning the rickshaw, and renting
  the licensed cab at prices.json taxi_fares.cab_rental_ncr_per_day
  on work days.

Flags:
- SURVIVAL FAIL: monthly net < 0 — the profession cannot live.
- TIGHT: savings rate < 10% of gross.
- IMPLAUSIBLY FAST: savings rate > 70% of gross.
- RENT BURDEN: rent > 50% of gross income.
- BRIDGE FAIL (bridge check only): entry row dips below zero in
  month 1 even with its starting balance applied.

Run: python3 tools/economy_sim.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

RENT_TIER = {
    "construction_worker": 1, "taxi_driver": 1, "chef": 2, "shop_owner": 2,
    "teacher": 2, "police_officer": 3, "civil_engineer": 3,
    "software_developer": 3, "doctor": 4, "business_owner": 4, "pilot": 4,
}
# Queue 9 / v5 (Unit AX): Shibnagar's residential stock tops out at
# tier 3 (no tier-4/5 homes exist in data/city2-shibnagar.json), so the
# three tier-4 professions are capped at tier 3 there. Every other
# profession keeps its District 1 tier.
SHIBNAGAR_RENT_TIER = {pid: min(tier, 3)
                       for pid, tier in RENT_TIER.items()}
CAR_PROFESSIONS = {"doctor", "business_owner", "pilot"}
BUSINESS_PROFESSIONS = {"shop_owner", "business_owner"}
WORK_DAYS = 26
DAYS = 30
# Queue 22 / v6 (Unit EY): the ES day wage is wage_per_month / 30 per
# worked day (tools/sim/labour.py day_wage_due), and the scheduler
# gives a construction worker a work block on all 30 days of a
# normal month (measured: instantiate() over days 0-29 finds a work
# block every day). A normal month therefore has 30 worked days and
# pays exactly the band. WORK_DAYS stays 26 for the cab-rental
# extra (a taxi works 26 days — the rental is charged on work days
# only, the v1 rule, untouched by this unit).
DAY_WAGE_WORKED_DAYS = 30
# Queue 23 / v7 (Unit FB): the storm-position scenario — the two
# storm days of the measured 28-worked-day month, at three
# scenario positions plus the measured one. The count (28 worked
# days) is measured (the seeded live month, Unit EY); the
# positions are scenarios, not claims about the measured month —
# except STORM_MEASURED_DAYS (days 3 and 22), which is where the
# live month's storms actually fell.
STORM_EARLY_DAYS = (1, 2)
STORM_MID_DAYS = (15, 16)
STORM_LATE_DAYS = (29, 30)
STORM_MEASURED_DAYS = (3, 22)


def load(name):
    with open(os.path.join(DATA, name)) as f:
        return json.load(f)


def band_for(entry_wage):
    return "lower" if entry_wage <= 15000 else ("mid" if entry_wage <= 40000 else "upper")


def monthly_tax(income, brackets):
    tax = 0.0
    for b in brackets:
        lo, hi, rate = b["from_ncr"], b["to_ncr"], b["rate_percent"]
        top = income if hi is None else min(income, hi)
        if top > lo:
            tax += (top - lo) * rate / 100.0
    return round(tax)


def business_pnl(prices, pid, tier):
    """Full P&L for a business profession at one tier, from
    prices.json business_model. Returns dict with revenue, stock,
    premises, staff, other, profit."""
    model = prices["business_model"][pid]
    t = model["tiers"][tier]
    revenue = t["revenue_ncr"]
    stock = round(revenue * model["stock_percent_of_revenue"] / 100.0)
    profit = revenue - stock - t["premises_rent_ncr"] - t["staff_ncr"] \
        - t["other_costs_ncr"]
    return {
        "revenue": revenue, "stock": stock,
        "premises": t["premises_rent_ncr"], "staff": t["staff_ncr"],
        "other": t["other_costs_ncr"], "profit": profit,
    }


def load_shibnagar_rents(prices):
    """Queue 9 / v5 (Unit AX): Shibnagar's priced residential stock.

    Reads data/city2-shibnagar.json (residential properties only:
    apartment/house with a rent) and returns (tier -> rent, stock).
    Each tier's rent must equal the prices.json tier table — the town's
    rents are tier rents, not a second price list — and a drift raises
    ValueError instead of running on stale numbers. The 7 unpriced
    properties (ghat, bus stand, school, clinic, town office, 2
    farmland plots) are civic/plot stock, not homes, and are excluded
    by the residential + priced filter, not by an id list.
    """
    city = load("city2-shibnagar.json")
    tier_table = {r["tier"]: r["rent_ncr"]
                  for r in prices["rent_monthly_by_tier"]}
    rents, stock = {}, {}
    for p in city["properties"]:
        if p["property_type"] not in ("apartment", "house"):
            continue
        rent = p.get("rent_monthly_ncr_per_unit")
        if rent is None:
            continue
        tier = p["tier"]
        if tier in rents and rents[tier] != rent:
            raise ValueError(
                f"shibnagar tier {tier} rent disagrees within the file: "
                f"{rents[tier]} vs {rent}")
        rents[tier] = rent
        stock[tier] = stock.get(tier, 0) + p.get("units", 1)
    for tier, rent in rents.items():
        if tier_table.get(tier) != rent:
            raise ValueError(
                f"shibnagar tier {tier} rent {rent} != prices.json tier "
                f"table {tier_table.get(tier)}")
    return rents, stock


def simulate(prices, wage_row, tier, extra_daily_cost=0, label_suffix="",
             tutoring_income=0, tutoring_expense=0, part_time_income=0,
             medicine_expense=0, rent_override=None,
             day_wage_worked_days=None, storm_days=None,
             second_earner=False):
    pid = wage_row["profession_id"]
    band = band_for(wage_row["entry"])
    lc = prices["living_costs_monthly"]
    # Queue 9 / v5: rent_override is the Shibnagar variant's rent for
    # this profession (None = the District 1 tier-table rent, the v4
    # behaviour, byte-identical).
    rent = rent_override if rent_override is not None else next(
        r["rent_ncr"] for r in prices["rent_monthly_by_tier"]
        if r["tier"] == RENT_TIER[pid])
    food = lc["food_home_cooking"][band]
    utilities = lc["utilities_power_water_internet"][band]
    clothing = lc["clothing_personal"][band]
    eating = lc["eating_out_monthly"][band]
    services = lc["household_services_monthly"][band]
    # Queue 7 / v4 (Unit AJ): the medical line is a base cost now,
    # charged at the household's band for every row, business
    # professions included (a plain expense — tax is computed on
    # profit/gross first, so the v3 business ValueError path is
    # untouched). The medicine_expense kwarg stays for callers that
    # model an extra episode on top; the default run charges the
    # line exactly once, here.
    medical = lc["medical_monthly"][band]
    if pid in CAR_PROFESSIONS:
        transport = lc["transport_own_car_fuel_upkeep"][band]
    else:
        transport = lc["transport_public_bus_rickshaw"][band]

    pnl = None
    if pid in BUSINESS_PROFESSIONS:
        pnl = business_pnl(prices, pid, tier)
        gross = pnl["profit"]  # the canonical band, via the P&L
        biz_rate = prices["tax"]["business_monthly_percent_of_profit"]
        tax = round(gross * biz_rate / 100.0) if gross > 0 else 0
        # Shop takings accrue daily; the owner's draw lands day 30.
        sched = "daily_takings" if pid == "shop_owner" else "monthly"
    else:
        gross = wage_row[tier]
        tax = monthly_tax(gross, prices["tax"]["income_monthly_brackets"])
        sched = wage_row["pay_schedule"]

    # Queue 22 / v6 (Unit EY): the day-wage profession
    # (construction_worker — the only "daily" pay_schedule) is paid
    # per worked day at wage/30 (the ES rule in tools/sim/labour.py
    # day_wage_due), not the monthly band spread over 26 Sundays-off
    # days. Worked days default to the scheduler-measured normal
    # month (DAY_WAGE_WORKED_DAYS = 30 — a work block every day);
    # a caller modelling a storm month passes the measured count
    # (the report's storm scenario uses 28). Gross is band x
    # worked/30 and tax is recomputed on that gross, so a storm
    # month's lower gross is taxed as a lower gross, exactly as the
    # settlement taxes the day-wage pay it actually made.
    # Queue 23 / v7 (Unit FB): the storm-position scenario — the
    # caller names the storm days instead (storm_days: distinct
    # 1-based days of the 30-day month); worked days are 30 minus
    # the storm days, and the trajectory pays only on worked days
    # (see below). The count is the measured live month (28 worked
    # days); the positions are scenario positions (early / mid /
    # late) plus the measured position (days 3 and 22 — the live
    # month's actual storm days). A storm_days that disagrees with
    # day_wage_worked_days, or names a day outside 1..30, or
    # repeats a day, is refused — the scenario must stay one
    # month, not a miscounted one. storm_days is meaningless for
    # any other pay schedule and is refused there too.
    storm_set = None
    if sched == "daily":
        if storm_days is not None:
            storm_set = set(storm_days)
            if len(storm_set) != len(list(storm_days)) \
                    or any(not isinstance(d, int) or d < 1
                           or d > DAYS for d in storm_set):
                raise ValueError(
                    "storm_days must be distinct day numbers in"
                    f" 1..{DAYS}, got {storm_days!r}")
            worked = DAYS - len(storm_set)
            if day_wage_worked_days is not None \
                    and day_wage_worked_days != worked:
                raise ValueError(
                    "storm_days imply "
                    f"{worked} worked days, not "
                    f"{day_wage_worked_days}")
        else:
            worked = (DAY_WAGE_WORKED_DAYS
                      if day_wage_worked_days is None
                      else day_wage_worked_days)
        gross = round(wage_row[tier] * worked / DAYS)
        tax = monthly_tax(gross, prices["tax"]["income_monthly_brackets"])
    elif storm_days is not None:
        raise ValueError(
            "storm_days is a day-wage scenario (construction_worker"
            f" only); {pid} pays {sched}")

    # Lifestyle uplift (Unit V): a fixed percent of the raise above
    # the entry-tier income is consumed by lifestyle.
    uplift_pct = prices["lifestyle_uplift"]["percent_of_raise_consumed"]
    entry_income = (business_pnl(prices, pid, "entry")["profit"]
                    if pid in BUSINESS_PROFESSIONS else wage_row["entry"])
    uplift = round(max(0, gross - entry_income) * uplift_pct / 100.0)

    # Queue 24 / Unit GD: the second earner — a construction
    # worker at the same tier, on the same storm days and the same
    # day-wage rule. Gross and tax double per earner (each earner
    # is taxed on their own gross, as the settlement taxes each
    # earner on what they received); the uplift doubles too (the
    # settlement sums it per earner, engine._settle_month). The
    # household costs follow engine._living_costs for two adults:
    # food and clothing ×2, transport and eating out ×2 (both are
    # per-earner lines in _living_costs — the queue draft's "rest
    # flat" gloss is corrected here against the source: only
    # utilities / services / medical and rent are flat), and the
    # trajectory needs no change — the doubled pay lands on the
    # same worked days at the doubled daily rate, and the doubled
    # costs accrue daily. Refused for any non-day-wage profession
    # and together with the v3 side-income/expense lines (those
    # belong to one person; a two-earner household with side income
    # needs a split this unit does not design).
    if second_earner:
        if sched != "daily":
            raise ValueError(
                "second_earner is a day-wage scenario"
                f" (construction_worker only); {pid} pays {sched}")
        if tutoring_income or tutoring_expense or part_time_income \
                or medicine_expense:
            raise ValueError(
                "second_earner cannot combine with the v3"
                " side-income/expense lines — those belong to one"
                " person")
        gross *= 2
        tax *= 2
        uplift *= 2
        food *= 2
        clothing *= 2
        transport *= 2
        eating *= 2

    # Queue 6 / v3 new lines (all default 0) + Queue 7 / v4: the
    # medical line is a base cost now (see `medical` above), so the
    # medicine_expense kwarg models only an EXTRA episode on top.
    # Uplift above is computed from the base gross on purpose: the
    # lifestyle uplift prices the wage ladder, not side-income.
    # Extra income is taxed marginally on the combined gross.
    base_tax = tax
    extra_income = tutoring_income + part_time_income
    extra_expense = tutoring_expense + medicine_expense
    if extra_income or extra_expense:
        if pid in BUSINESS_PROFESSIONS:
            raise ValueError(
                f"{pid}: tutoring/part-time/medicine lines are not "
                "modelled for business professions in v3 — a "
                "business household needs a business+personal split")
        gross = gross + extra_income
        tax = monthly_tax(gross, prices["tax"]["income_monthly_brackets"])
    extra_income_net = extra_income - (tax - base_tax)

    monthly_costs = rent + food + utilities + clothing + transport \
        + eating + services + medical + uplift + extra_expense
    extra_monthly = extra_daily_cost * WORK_DAYS
    net = gross - tax - monthly_costs - extra_monthly

    # 30-day trajectory from a zero start (v1-comparable minbal).
    # Base pay follows the profession's schedule on the BASE gross
    # and tax; v3 side-income accrues evenly on top, so the month's
    # total still equals gross - tax exactly.
    base_gross = gross - extra_income
    daily_cost = monthly_costs / DAYS
    balance, min_balance = 0.0, 0.0
    for day in range(1, DAYS + 1):
        balance -= daily_cost
        if extra_daily_cost and day <= WORK_DAYS and day % 7 != 0:
            balance -= extra_daily_cost
        if sched == "monthly":
            if day == DAYS:
                balance += base_gross - base_tax
        elif sched == "daily":
            # Queue 22 / v6 (Unit EY): the ES day wage accrues evenly
            # — wage/30 per worked day, 30 worked days in a normal
            # month, so the month pays exactly the band. The v5
            # branch paid (gross-tax)/26 on days 1-26 excluding
            # Sundays — 23 pay days, 23/26 of the band — while the
            # headline net showed the full band; the trajectory now
            # ends exactly at net.
            # Queue 23 / v7 (Unit FB): with storm_days, the pay
            # lands only on worked days — (gross-tax)/worked per
            # worked day, 0 on a storm day — so the month-1 dip
            # depends on where the storms fall; the total is still
            # exactly gross-tax, so the trajectory still ends at
            # net. Without storm_days the even accrual (v6) is
            # unchanged, and the v6 storm section's figure stays
            # the even-spread one.
            if storm_set is None:
                balance += (base_gross - base_tax) / DAYS
            elif day not in storm_set:
                balance += (base_gross - base_tax) / worked
        else:  # per_fare / daily_takings: even accrual
            balance += (base_gross - base_tax) / DAYS
        if extra_income_net:
            # v3 side-income (tutoring / part-time) accrues evenly.
            balance += extra_income_net / DAYS
        min_balance = min(min_balance, balance)

    rate = net / gross * 100 if gross else 0
    flags = []
    if net < 0:
        flags.append("SURVIVAL FAIL")
    elif rate < 10:
        flags.append("TIGHT")
    if rate > 70:
        flags.append("IMPLAUSIBLY FAST")
    if rent / gross > 0.5:
        flags.append("RENT BURDEN")
    return {
        "profession": pid + label_suffix, "pid": pid, "tier": tier,
        "gross": gross, "tax": tax, "rent": rent,
        "costs_total": monthly_costs + extra_monthly,
        "uplift": uplift, "extra": extra_monthly,
        "net": round(net), "rate": round(rate, 1),
        "min_balance": round(min_balance), "flags": flags, "pnl": pnl,
        "extra_income": extra_income, "extra_expense": extra_expense,
        # Queue 24 / Unit GD: whether the row models a two-earner
        # household (a second construction worker at the same tier,
        # same storm days, same day-wage rule).
        "second_earner": second_earner,
        # Queue 22 / v6 (Unit EY): the trajectory's final balance —
        # it must equal net (the trajectory models the same month
        # the headline figures describe); the v5 daily branch ended
        # 3/26 of the band short of it, and the no-regression test
        # pins the equality for every row.
        "end_balance": round(balance),
    }


def print_v4_scenarios(prices):
    """Queue 6/7 additional lines (Units AH + AI), behind --v3/--v4.

    v4 (Unit AJ): the medical line is charged in the base table now,
    so the four medical scenarios v3 printed are gone — they would
    double-charge. What remains are the tutoring / part-time
    scenarios (still extras on top of the base) plus the medicine
    basket check, so the v4 report can quote them verbatim. --v3 is
    kept as an alias for this section.
    """
    tut = prices["tutoring"]["monthly_typical_ncr"]
    pt = prices["part_time_student_work"]["monthly_typical_ncr"]
    med = prices["living_costs_monthly"]["medical_monthly"]
    med_items = {i["id"]: i["price_ncr"]
                 for i in prices["medicine"]["items"]}
    basket = (med_items["fever_pain_relief_strip"]
              + med_items["oral_rehydration_salts"]
              + med_items["cough_syrup_bottle"])
    wages = {w["profession_id"]: w for w in prices["wages_monthly"]}
    print("v4 additional scenarios (Units AH + AI):")
    print(f"  priced from prices.json: tutoring "
          f"{prices['tutoring']['per_session_ncr']}/session x "
          f"{prices['tutoring']['sessions_per_month_typical']}/mo = "
          f"{tut}; part-time "
          f"{prices['part_time_student_work']['per_block_ncr']}/block x "
          f"{prices['part_time_student_work']['blocks_per_week_typical']}"
          f"/wk x 4 = {pt}; medical budget lower {med['lower']} / "
          f"mid {med['mid']} / upper {med['upper']} — now charged in "
          f"the base table (Unit AJ), not a scenario")
    print(f"  medicine basket check: one minor-illness episode "
          f"(fever strip {med_items['fever_pain_relief_strip']} + "
          f"rehydration salts {med_items['oral_rehydration_salts']} + "
          f"cough syrup {med_items['cough_syrup_bottle']}) = {basket} "
          f"NCr, inside the lower medical budget ({med['lower']})")
    print(f"  pharmacy: {prices['medicine']['pharmacy_name']} "
          f"({prices['medicine']['pharmacy_property_id']}, unit 1); "
          f"clinic treatment stays free at point of use (GDD-12 §6)")
    print()
    print("household scenarios (base net -> scenario net; tax recomputed "
          "on combined income):")
    scenarios = [
        ("teacher/entry + tutoring income (tutors 8 sessions)",
         "teacher", "entry", {"tutoring_income": tut}),
        ("teacher/entry + tutoring expense (pays for one child)",
         "teacher", "entry", {"tutoring_expense": tut}),
        ("teacher/entry + tutoring income AND expense",
         "teacher", "entry",
         {"tutoring_income": tut, "tutoring_expense": tut}),
        ("construction_worker/entry + teen part-time income",
         "construction_worker", "entry", {"part_time_income": pt}),
        ("teacher/entry + teen part-time income",
         "teacher", "entry", {"part_time_income": pt}),
    ]
    fails, tight = [], []
    for label, pid, tier, kw in scenarios:
        base = simulate(prices, wages[pid], tier)
        scen = simulate(prices, wages[pid], tier, **kw)
        delta = scen["net"] - base["net"]
        if "SURVIVAL FAIL" in scen["flags"]:
            fails.append(label)
        if "TIGHT" in scen["flags"]:
            tight.append(label)
        print(f"  {label:52} base net {base['net']:>6} -> {scen['net']:>6} "
              f"(delta {delta:+d}, save {scen['rate']}%)  "
              f"{', '.join(scen['flags']) or '-'}")
    print(f"v4 scenario SURVIVAL FAIL rows: {fails}")
    print(f"v4 scenario TIGHT rows: {tight}")


def print_shibnagar_variant(prices, d1_rows, start_balances):
    """Queue 9 / v5 (Unit AX): the --shibnagar variant table.

    Re-runs the same 30-day simulation over Shibnagar's priced
    residential stock: each profession rents at its SHIBNAGAR_RENT_TIER
    (tier-4 professions capped at tier 3 — the town has no tier-4/5
    homes), at the rent the city file itself carries. Wages, living
    costs, taxes, business P&L and starting balances are unchanged, so
    the comparison at the end is a pure rent effect.
    """
    rents, stock = load_shibnagar_rents(prices)
    capped = sorted(pid for pid, tier in RENT_TIER.items()
                    if SHIBNAGAR_RENT_TIER[pid] != tier)
    print("shibnagar variant (Unit AX): same 30-day simulation over "
          "data/city2-shibnagar.json residential stock")
    print(f"  priced residential stock: "
          + ", ".join(f"tier {t}: {rents[t]} NCr/mo "
                      f"({stock[t]} units)" for t in sorted(rents))
          + " — each tier's rent equals the prices.json tier table "
          "(asserted, not assumed)")
    print(f"  no tier-4/5 homes exist in Shibnagar; capped at tier 3: "
          f"{', '.join(capped)} (rent 12000 -> 6000)")
    print(f"  7 of 18 properties unpriced (ghat, bus stand, school, "
          f"clinic, town office, 2 farmland plots) — civic/plot stock, "
          f"not homes")
    rows = []
    for w in prices["wages_monthly"]:
        pid = w["profession_id"]
        override = rents[SHIBNAGAR_RENT_TIER[pid]]
        for tier in ("entry", "mid", "senior"):
            rows.append(simulate(prices, w, tier, rent_override=override))
        if pid == "taxi_driver":
            cab_rent = prices["taxi_fares"]["cab_rental_ncr_per_day"]
            rows.append(simulate(prices, w, "entry",
                                 extra_daily_cost=cab_rent,
                                 label_suffix=" (renting cab)",
                                 rent_override=override))
    print(f"{'profession':28} {'tier':7} {'gross':>7} {'tax':>6} {'rent':>6} "
          f"{'costs':>6} {'net/mo':>8} {'save%':>6} {'minbal':>8}  flags")
    for r in rows:
        print(f"{r['profession']:28} {r['tier']:7} {r['gross']:>7} "
              f"{r['tax']:>6} {r['rent']:>6} {r['costs_total']:>6} "
              f"{r['net']:>8} {r['rate']:>6} {r['min_balance']:>8}  "
              f"{', '.join(r['flags']) or '-'}")
    print()
    fails = [r for r in rows if "SURVIVAL FAIL" in r["flags"]]
    fast = [r for r in rows if "IMPLAUSIBLY FAST" in r["flags"]]
    tight = [r for r in rows if "TIGHT" in r["flags"]]
    print(f"shibnagar SURVIVAL FAIL rows: "
          f"{[r['profession'] + '/' + r['tier'] for r in fails]}")
    print(f"shibnagar IMPLAUSIBLY FAST rows: "
          f"{[r['profession'] + '/' + r['tier'] for r in fast]}")
    print(f"shibnagar TIGHT rows: "
          f"{[r['profession'] + '/' + r['tier'] for r in tight]}")
    print("shibnagar senior savings rates: " + ", ".join(
        f"{r['pid']} {r['rate']}%" for r in rows if r["tier"] == "senior"))
    print()
    print("shibnagar first-month bridge check (same starting balances):")
    bridge_fail = []
    for r in rows:
        if r["tier"] != "entry" or r["pid"] == "taxi_driver" and "renting" in r["profession"]:
            continue
        start = start_balances.get(r["pid"], 0)
        worst = start + r["min_balance"]
        status = "OK" if worst >= 0 else "BRIDGE FAIL"
        if worst < 0:
            bridge_fail.append(r["pid"])
        print(f"  {r['pid']:22} start {start:>6} + dip {r['min_balance']:>7} = {worst:>7}  {status}")
    rent_row = next(r for r in rows if "renting" in r["profession"])
    start = start_balances.get("taxi_driver", 0)
    worst = start + rent_row["min_balance"]
    status = "OK" if worst >= 0 else "BRIDGE FAIL"
    if worst < 0:
        bridge_fail.append("taxi_driver (renting cab)")
    print(f"  {'taxi_driver (renting cab)':22} start {start:>6} + dip {rent_row['min_balance']:>7} = {worst:>7}  {status}")
    print(f"shibnagar BRIDGE FAIL rows: {bridge_fail}")
    print()
    print("district 1 vs shibnagar (rent delta -> net delta; only the "
          "three capped professions differ):")
    d1_by_key = {(r["profession"], r["tier"]): r for r in d1_rows}
    for r in rows:
        d1r = d1_by_key[(r["profession"], r["tier"])]
        print(f"  {r['profession']:28} {r['tier']:7} "
              f"rent {d1r['rent']:>6} -> {r['rent']:>6} "
              f"({r['rent'] - d1r['rent']:+d})  "
              f"net {d1r['net']:>7} -> {r['net']:>7} "
              f"({r['net'] - d1r['net']:+d})  "
              f"{', '.join(r['flags']) or '-'}")
    ce = next(r for r in rows if r["profession"] == "civil_engineer"
              and r["tier"] == "entry")
    car = next(v["price_ncr"] for v in prices["vehicles"]
               if v["id"] == "car_small")
    t3 = next(r for r in prices["rent_monthly_by_tier"] if r["tier"] == 3)
    deposit = t3["buy_price_guide_ncr"] * prices["loans"]["mortgage"]["deposit_percent"] // 100
    print(f"shibnagar pacing: civil_engineer/entry saves {ce['net']} "
          f"NCr/mo -> car_small ({car}) in {round(car / ce['net'], 1)} "
          f"months; tier-3 deposit ({deposit}) in "
          f"{round(deposit / ce['net'], 1)} months")


def main():
    prices = load("prices.json")
    professions = load("professions.json")
    start_balances = {p["id"]: p.get("starting_balance_ncr", 0)
                      for p in professions["professions"]}

    rows = []
    for w in prices["wages_monthly"]:
        for tier in ("entry", "mid", "senior"):
            rows.append(simulate(prices, w, tier))
        if w["profession_id"] == "taxi_driver":
            cab_rent = prices["taxi_fares"]["cab_rental_ncr_per_day"]
            rows.append(simulate(prices, w, "entry",
                                 extra_daily_cost=cab_rent,
                                 label_suffix=" (renting cab)"))

    print(f"{'profession':28} {'tier':7} {'gross':>7} {'tax':>6} {'rent':>6} "
          f"{'costs':>6} {'net/mo':>8} {'save%':>6} {'minbal':>8}  flags")
    for r in rows:
        print(f"{r['profession']:28} {r['tier']:7} {r['gross']:>7} "
              f"{r['tax']:>6} {r['rent']:>6} {r['costs_total']:>6} "
              f"{r['net']:>8} {r['rate']:>6} {r['min_balance']:>8}  "
              f"{', '.join(r['flags']) or '-'}")
    print()
    fails = [r for r in rows if "SURVIVAL FAIL" in r["flags"]]
    fast = [r for r in rows if "IMPLAUSIBLY FAST" in r["flags"]]
    tight = [r for r in rows if "TIGHT" in r["flags"]]
    print(f"professions simulated: {len(prices['wages_monthly'])} "
          f"(+ taxi rental variant); rows: {len(rows)}")
    print(f"SURVIVAL FAIL rows: {[r['profession'] + '/' + r['tier'] for r in fails]}")
    print(f"IMPLAUSIBLY FAST rows: {[r['profession'] + '/' + r['tier'] for r in fast]}")
    print(f"TIGHT rows: {[r['profession'] + '/' + r['tier'] for r in tight]}")

    seniors = [r for r in rows if r["tier"] == "senior"]
    print("senior savings rates: " + ", ".join(
        f"{r['pid']} {r['rate']}%" for r in seniors))

    # Business P&L reconciliation (Finding 6): computed profit vs the
    # canonical band in prices.json wages_monthly.
    print()
    print("business P&L (revenue - stock - premises - staff - other = profit vs canonical band):")
    bands = {w["profession_id"]: w for w in prices["wages_monthly"]}
    for pid in sorted(BUSINESS_PROFESSIONS):
        for tier in ("entry", "mid", "senior"):
            p = business_pnl(prices, pid, tier)
            band = bands[pid][tier]
            print(f"  {pid:15} {tier:7} rev {p['revenue']:>7} - stock "
                  f"{p['stock']:>6} - prem {p['premises']:>6} - staff "
                  f"{p['staff']:>6} - other {p['other']:>5} = profit "
                  f"{p['profit']:>7} (band {band}, delta {p['profit'] - band:+d})")

    # First-month bridge check (Finding 3): apply each profession's
    # starting balance to its entry row's zero-start trajectory.
    # Queue 24 / Unit GE: the construction_worker entry row also
    # prints its worst storm-position dip (the minimum month-1
    # balance across the four storm positions, Unit FB) against
    # the same starting balance — so the storm bridge is part of
    # the tool's output rather than a report-only observation
    # (V7 §5). A failing storm line joins BRIDGE FAIL.
    print()
    print("first-month bridge check (entry rows: starting balance + zero-start dip = worst month-1 balance):")
    bridge_fail = []
    for r in rows:
        if r["tier"] != "entry" or r["pid"] == "taxi_driver" and "renting" in r["profession"]:
            continue
        start = start_balances.get(r["pid"], 0)
        worst = start + r["min_balance"]
        status = "OK" if worst >= 0 else "BRIDGE FAIL"
        if worst < 0:
            bridge_fail.append(r["pid"])
        print(f"  {r['pid']:22} start {start:>6} + dip {r['min_balance']:>7} = {worst:>7}  {status}")
        if r["pid"] == "construction_worker":
            worst_storm = min(
                simulate(prices, bands["construction_worker"], "entry",
                         storm_days=pos)["min_balance"]
                for pos in (STORM_EARLY_DAYS, STORM_MID_DAYS,
                            STORM_LATE_DAYS, STORM_MEASURED_DAYS))
            storm_worst = start + worst_storm
            storm_status = "OK" if storm_worst >= 0 else "BRIDGE FAIL"
            if storm_worst < 0:
                bridge_fail.append("construction_worker (storm)")
            print(f"  {r['pid']:22} start {start:>6} + storm dip "
                  f"{worst_storm:>7} = {storm_worst:>7}  {storm_status}"
                  f"  (worst storm position)")
    # The renting-cab variant shares the taxi driver's starting balance.
    rent_row = next(r for r in rows if "renting" in r["profession"])
    start = start_balances.get("taxi_driver", 0)
    worst = start + rent_row["min_balance"]
    status = "OK" if worst >= 0 else "BRIDGE FAIL"
    if worst < 0:
        bridge_fail.append("taxi_driver (renting cab)")
    print(f"  {'taxi_driver (renting cab)':22} start {start:>6} + dip {rent_row['min_balance']:>7} = {worst:>7}  {status}")
    print(f"BRIDGE FAIL rows: {bridge_fail}")

    # Pacing checks (entry tier, civil engineer = owner reference)
    ce = next(r for r in rows if r["profession"] == "civil_engineer"
              and r["tier"] == "entry")
    car = next(v["price_ncr"] for v in prices["vehicles"]
               if v["id"] == "car_small")
    t3 = next(r for r in prices["rent_monthly_by_tier"] if r["tier"] == 3)
    deposit = t3["buy_price_guide_ncr"] * prices["loans"]["mortgage"]["deposit_percent"] // 100
    print(f"pacing: civil_engineer/entry saves {ce['net']} NCr/mo -> "
          f"car_small ({car}) in {round(car / ce['net'], 1)} months; "
          f"tier-3 deposit ({deposit}) in {round(deposit / ce['net'], 1)} months")

    # Queue 22 / v6 (Unit EY): the day-wage storm month — the
    # measured live month (seeded 30-day engine run, 4 construction
    # workers): 28 worked days of 30, days 3 and 22 storm days with
    # outdoor work suspended, so the settlement pays 28/30 of the
    # band. Same costs as the base table (uplift recomputed from
    # the reduced gross); tax recomputed on the reduced gross; the
    # reduced pay accrues evenly here — this section keeps the v6
    # even-spread figure; the storm-position section below (Unit FB
    # · Queue 23) models which days the storms fall on. No tuning
    # call: the storm month is weather, not a balance problem.
    print()
    print("day-wage storm month (Unit EY — measured 28 worked days of "
          "30, 2 storm days suspending outdoor work):")
    print(f"{'profession':28} {'tier':7} {'gross':>7} {'tax':>6} {'rent':>6} "
          f"{'costs':>6} {'net/mo':>8} {'save%':>6} {'minbal':>8}  flags")
    for tier in ("entry", "mid", "senior"):
        r = simulate(prices, bands["construction_worker"], tier,
                     day_wage_worked_days=28)
        base = simulate(prices, bands["construction_worker"], tier)
        print(f"{r['profession']:28} {r['tier']:7} {r['gross']:>7} "
              f"{r['tax']:>6} {r['rent']:>6} {r['costs_total']:>6} "
              f"{r['net']:>8} {r['rate']:>6} {r['min_balance']:>8}  "
              f"{', '.join(r['flags']) or '-'}"
              f"  (base net {base['net']}, save {base['rate']}%)")

    # Queue 23 / v7 (Unit FB): the storm-position scenario — the
    # same 28 worked days, but the two storm days fall early (days
    # 1-2), mid (15-16), or late (29-30), plus the measured
    # position (days 3 and 22, where the live month's storms
    # actually fell) and the v6 even-spread baseline for
    # comparison. The net is the same for every position (the
    # month pays the same 28/30 of the band whatever the days) —
    # only the month-1 minimum balance moves, and that is the
    # measured figure: pay lands only on worked days, so a storm
    # on day 1 dips deeper than a storm on day 29. The v6 minbal
    # (0 for every tier) is the even-spread figure, not a measured
    # one. No tuning call: the storm month is weather, not a
    # balance problem — the worst dip is measured, not fixed.
    print()
    print("day-wage storm-position month (Unit FB — same 28 worked "
          "days of 30; month-1 minbal by storm position):")
    print(f"{'profession':28} {'tier':7} {'early':>7} {'mid':>7} "
          f"{'late':>7} {'measured':>8} {'even':>7}  (net/mo)")
    for tier in ("entry", "mid", "senior"):
        w = bands["construction_worker"]
        early = simulate(prices, w, tier,
                         storm_days=STORM_EARLY_DAYS)
        mid = simulate(prices, w, tier,
                       storm_days=STORM_MID_DAYS)
        late = simulate(prices, w, tier,
                        storm_days=STORM_LATE_DAYS)
        measured = simulate(prices, w, tier,
                            storm_days=STORM_MEASURED_DAYS)
        even = simulate(prices, w, tier,
                        day_wage_worked_days=28)
        print(f"{early['profession']:28} {early['tier']:7} "
              f"{early['min_balance']:>7} {mid['min_balance']:>7} "
              f"{late['min_balance']:>7} {measured['min_balance']:>8} "
              f"{even['min_balance']:>7}  (net {early['net']})")

    # Queue 24 / v7 (Unit GD): the two-earner storm-position
    # scenario — the same 28 worked days and the same storm
    # positions, but the household has a second construction
    # worker at the same tier (same storm_days, same day-wage
    # rule) and its costs follow engine._living_costs for two
    # adults (food/clothing ×2, transport/eating ×2 per earner,
    # the rest flat; uplift per earner). The measured position
    # dips nothing — a second earner pays from day 3 on — but the
    # early position dips DEEPER in NCr than the single-earner
    # household (two adults burn the daily cost with no pay
    # arriving on days 1–2): a second earner does not help the
    # early dip at all. The net is the same for every position;
    # only the month-1 minimum balance moves. No tuning call.
    print()
    print("two-earner storm-position month (Unit GD — same 28 worked "
          "days of 30; second earner is a construction worker at "
          "the same tier, same storm days; month-1 minbal by storm "
          "position):")
    print(f"{'profession':28} {'tier':7} {'early':>7} {'mid':>7} "
          f"{'late':>7} {'measured':>8} {'even':>7}  (net/mo)")
    for tier in ("entry", "mid", "senior"):
        w = bands["construction_worker"]
        early = simulate(prices, w, tier,
                         storm_days=STORM_EARLY_DAYS,
                         second_earner=True)
        mid = simulate(prices, w, tier,
                       storm_days=STORM_MID_DAYS,
                       second_earner=True)
        late = simulate(prices, w, tier,
                        storm_days=STORM_LATE_DAYS,
                        second_earner=True)
        measured = simulate(prices, w, tier,
                            storm_days=STORM_MEASURED_DAYS,
                            second_earner=True)
        even = simulate(prices, w, tier,
                        day_wage_worked_days=28,
                        second_earner=True)
        print(f"{early['profession']:28} {early['tier']:7} "
              f"{early['min_balance']:>7} {mid['min_balance']:>7} "
              f"{late['min_balance']:>7} {measured['min_balance']:>8} "
              f"{even['min_balance']:>7}  (net {early['net']})")

    if "--shibnagar" in sys.argv:
        print()
        print_shibnagar_variant(prices, rows, start_balances)

    if "--v3" in sys.argv or "--v4" in sys.argv:
        print()
        print_v4_scenarios(prices)


if __name__ == "__main__":
    main()
