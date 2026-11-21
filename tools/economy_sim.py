#!/usr/bin/env python3
"""NEXORA — Economy Balance Simulator v2 (Unit X, Queue 4).

Simulates 30 game-days of household cashflow for every profession in
data/prices.json (wages_monthly) at entry / mid / senior tiers.
Deterministic — no randomness; the same input always produces the
same report.

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

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

RENT_TIER = {
    "construction_worker": 1, "taxi_driver": 1, "chef": 2, "shop_owner": 2,
    "teacher": 2, "police_officer": 3, "civil_engineer": 3,
    "software_developer": 3, "doctor": 4, "business_owner": 4, "pilot": 4,
}
CAR_PROFESSIONS = {"doctor", "business_owner", "pilot"}
BUSINESS_PROFESSIONS = {"shop_owner", "business_owner"}
WORK_DAYS = 26
DAYS = 30


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


def simulate(prices, wage_row, tier, extra_daily_cost=0, label_suffix=""):
    pid = wage_row["profession_id"]
    band = band_for(wage_row["entry"])
    lc = prices["living_costs_monthly"]
    rent = next(r["rent_ncr"] for r in prices["rent_monthly_by_tier"]
                if r["tier"] == RENT_TIER[pid])
    food = lc["food_home_cooking"][band]
    utilities = lc["utilities_power_water_internet"][band]
    clothing = lc["clothing_personal"][band]
    eating = lc["eating_out_monthly"][band]
    services = lc["household_services_monthly"][band]
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

    # Lifestyle uplift (Unit V): a fixed percent of the raise above
    # the entry-tier income is consumed by lifestyle.
    uplift_pct = prices["lifestyle_uplift"]["percent_of_raise_consumed"]
    entry_income = (business_pnl(prices, pid, "entry")["profit"]
                    if pid in BUSINESS_PROFESSIONS else wage_row["entry"])
    uplift = round(max(0, gross - entry_income) * uplift_pct / 100.0)

    monthly_costs = rent + food + utilities + clothing + transport \
        + eating + services + uplift
    extra_monthly = extra_daily_cost * WORK_DAYS
    net = gross - tax - monthly_costs - extra_monthly

    # 30-day trajectory from a zero start (v1-comparable minbal).
    daily_cost = monthly_costs / DAYS
    balance, min_balance = 0.0, 0.0
    for day in range(1, DAYS + 1):
        balance -= daily_cost
        if extra_daily_cost and day <= WORK_DAYS and day % 7 != 0:
            balance -= extra_daily_cost
        if sched == "monthly":
            if day == DAYS:
                balance += gross - tax
        elif sched == "daily":
            if day <= WORK_DAYS and day % 7 != 0:
                balance += (gross - tax) / WORK_DAYS
        else:  # per_fare / daily_takings: even accrual
            balance += (gross - tax) / DAYS
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
    }


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


if __name__ == "__main__":
    main()
