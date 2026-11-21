#!/usr/bin/env python3
"""NEXORA — Economy Balance Simulator (Unit T).

Simulates 30 game-days of household cashflow for every profession in
data/prices.json (wages_monthly) at entry / mid / senior tiers, using only
merged data: wages, rent tiers, living costs and tax brackets from
data/prices.json. Deterministic — no randomness; the same input always
produces the same report.

Household model (v1, deliberately simple — the report owns the caveats):
- One adult, living alone, renting at the tier assigned in RENT_TIER below.
- Lifestyle band: lower if entry wage <= 15,000, mid if <= 40,000, else upper
  (food / utilities / clothing from prices.json living_costs_monthly).
- Transport: public (bus/rickshaw) at the lifestyle band, except doctor,
  business_owner and pilot, who run a car (transport_own_car_fuel_upkeep).
- Income tax: marginal, from prices.json tax.income_monthly_brackets,
  deducted monthly (GDD-03 §4.2).
- Pay schedules: monthly wages land on day 30; daily wages pay on 26 work
  days; per_fare / daily_takings / monthly_draw accrue evenly per day
  (v1 simplification — variance is a tuning question, not a survival one).
- Taxi driver is modelled twice: owning the rickshaw (prices.json
  rickshaw_own) and renting the licensed cab at 800 NCr/day on work days.

Flags:
- SURVIVAL FAIL: monthly net < 0 — the profession cannot live on its wage.
- TIGHT: savings rate < 10% of gross.
- IMPLAUSIBLY FAST: savings rate > 70% of gross — accumulation outruns the
  living-cost model (usually: costs do not scale at senior tiers).
- RENT BURDEN: rent > 50% of gross income.

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


def simulate(prices, wage_row, tier, extra_daily_cost=0, label_suffix=""):
    pid = wage_row["profession_id"]
    gross = wage_row[tier]
    band = band_for(wage_row["entry"])
    lc = prices["living_costs_monthly"]
    rent = next(r["rent_ncr"] for r in prices["rent_monthly_by_tier"]
                if r["tier"] == RENT_TIER[pid])
    food = lc["food_home_cooking"][band]
    utilities = lc["utilities_power_water_internet"][band]
    clothing = lc["clothing_personal"][band]
    if pid in CAR_PROFESSIONS:
        transport = lc["transport_own_car_fuel_upkeep"][band]
    else:
        transport = lc["transport_public_bus_rickshaw"][band]
    tax = monthly_tax(gross, prices["tax"]["income_monthly_brackets"])
    monthly_costs = rent + food + utilities + clothing + transport
    extra_monthly = extra_daily_cost * WORK_DAYS
    net = gross - tax - monthly_costs - extra_monthly

    # 30-day trajectory (start balance 0 for comparability)
    daily_cost = monthly_costs / DAYS
    balance, min_balance = 0.0, 0.0
    sched = wage_row["pay_schedule"]
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
        else:  # per_fare / daily_takings / monthly_draw: even accrual
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
        "profession": pid + label_suffix, "tier": tier, "gross": gross,
        "tax": tax, "rent": rent, "food": food, "transport": transport,
        "utilities": utilities, "clothing": clothing,
        "extra": extra_monthly, "net": round(net), "rate": round(rate, 1),
        "min_balance": round(min_balance), "flags": flags,
    }


def main():
    prices = load("prices.json")
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
        costs = r["rent"] + r["food"] + r["transport"] + r["utilities"] \
            + r["clothing"] + r["extra"]
        print(f"{r['profession']:28} {r['tier']:7} {r['gross']:>7} "
              f"{r['tax']:>6} {r['rent']:>6} {costs:>6} {r['net']:>8} "
              f"{r['rate']:>6} {r['min_balance']:>8}  "
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
