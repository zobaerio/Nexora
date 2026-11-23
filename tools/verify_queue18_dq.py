"""Verify Queue 18 Unit DQ — Seeded-Row Condition & Decay (GDD-04
§3.3; DJ follow-up).

Checks the condition model against the sources it builds on:
data/furniture.json + data/tools.json (the catalogues),
data/prices.json (replacement prices; no repair price exists),
data/transport-config.json + tools/sim/lost_items.py (the vehicle
condition precedent), docs/GDD-10-HOUSING-AND-HOME-LIFE.md §5/§6
(the tier multipliers), data/environment-config.json (flood
exposure), and tools/sim/lost_items.py (record_loss ignores
condition). Design only — no sim code changes. Prints one line
per check and a summary; exits 0 only when every check passes.
Run from the repo root: python3 tools/verify_queue18_dq.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKS = []


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def _keys_with(obj, needle):
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if needle in k.lower():
                found.append(k)
            found.extend(_keys_with(v, needle))
    elif isinstance(obj, list):
        for v in obj:
            found.extend(_keys_with(v, needle))
    return found


def main():
    gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md").read_text()
    gdd10 = (ROOT / "docs" / "GDD-10-HOUSING-AND-HOME-LIFE.md").read_text()
    furniture = json.loads((ROOT / "data" / "furniture.json").read_text())
    tools = json.loads((ROOT / "data" / "tools.json").read_text())
    prices = json.loads((ROOT / "data" / "prices.json").read_text())
    profs = json.loads((ROOT / "data" / "professions.json").read_text())
    transport_cfg = json.loads(
        (ROOT / "data" / "transport-config.json").read_text())
    env_cfg = json.loads(
        (ROOT / "data" / "environment-config.json").read_text())
    lost_items = (ROOT / "tools" / "sim" / "lost_items.py").read_text()

    s33 = gdd04.split("**Seeded-row condition & decay (Unit DQ")[1] \
        .split("### 3.4 Discovery")[0]

    # 1. The section exists with the model's decisions.
    check("**Seeded-row condition & decay (Unit DQ" in gdd04,
          "GDD-04 §3.3 has the condition & decay subsection")
    check("seeded at 100 (new)" in s33,
          "the model seeds condition at 100")
    check("service_threshold" in s33 and "restored_condition" in s33,
          "the thresholds are adopted from the vehicle precedent")
    check("No per-event repair price exists" in s33,
          "the repair price rule states no per-event price exists")
    check("effective furnishing tier" in s33,
          "broken furniture drops the effective tier")
    check("no passive time decay" in s33.lower(),
          "the model has no passive time decay")

    # 2. Every furniture piece resolves to a prices.json price.
    fprices = {i["id"]: i["price_ncr"]
               for i in prices["furniture"]["items"]}
    check(len(furniture["items"]) == 18,
          "furniture catalogue has 18 pieces")
    check(all(i["id"] in fprices for i in furniture["items"]),
          "every furniture piece has a prices.json price")
    check(all(fprices[i["id"]] == 0 for i in furniture["items"]
              if i["tier"] == "F0"),
          "F0 pieces are priced 0 (scavenged)")
    check(all(fprices[i["id"]] > 0 for i in furniture["items"]
              if i["tier"] != "F0"),
          "F1-F3 pieces are priced above 0")
    tiers = furniture["tiers"]
    check(sum(len(v) for v in tiers.values()) == 18,
          "the four tier lists hold all 18 pieces")
    check(sorted(tiers) == ["F0", "F1", "F2", "F3"],
          "the furniture tiers are F0-F3")

    # 3. Every tool resolves to a prices.json price and a profession.
    tprices = {i["id"]: i["price_ncr"]
               for i in prices["tools"]["items"]}
    prof_ids = {p["id"] for p in profs["professions"]}
    check(len(tools["items"]) == 10,
          "tool catalogue has 10 tools")
    check(all(i["id"] in tprices and tprices[i["id"]] > 0
              for i in tools["items"]),
          "every tool has a prices.json price above 0")
    check(all(p in prof_ids for i in tools["items"]
              for p in i.get("professions", [])),
          "every tool profession resolves to professions.json")

    # 4. No repair price exists anywhere in prices.json.
    check(_keys_with(prices, "repair") == [],
          "prices.json carries no repair key (no invented price)")

    # 5. The vehicle precedent is cited correctly.
    maint = transport_cfg["maintenance"]
    check(maint["initial_condition"] == 92.0
          and maint["service_threshold"] == 60.0
          and maint["restored_condition"] == 90.0,
          "vehicle maintenance numbers are 92 / 60 / 90")
    check('"condition": condition' in lost_items,
          "seed_vehicle_row writes condition into the state JSON")

    # 6. The GDD-10 tier multipliers are cited correctly.
    check("F0 ×0.7, F1 ×1.0, F2 ×1.15, F3 ×1.3" in gdd10,
          "GDD-10 §6 multipliers are F0 x0.7 / F1 x1.0 / F2 x1.15 / F3 x1.3")
    check("2× the property tier's monthly rent" in gdd10
          and "4× monthly rent" in gdd10
          and "7× monthly rent" in gdd10,
          "GDD-10 §5 package prices are 2x / 4x / 7x rent")
    check("itemised repair rows" in gdd10,
          "GDD-10 §4 prices damage as itemised ledger purchase rows")

    # 7. The weather cause has its precedent.
    flood_basis = json.dumps(env_cfg.get("flood_model", {}))
    check("lose condition per day" in flood_basis,
          "flood episodes make exposed buildings lose condition per day")

    # 8. A broken tool can still be lost (record_loss ignores condition).
    record_loss_body = lost_items.split("def record_loss(")[1] \
        .split("\ndef ", 1)[0]
    check("condition" not in record_loss_body.replace("precondition", ""),
          "record_loss checks the row exists, not its condition")

    # 9. Documents stay out of scope (unpriced, validity is the record).
    check(all(i["price_ncr"] == 0 for i in prices["documents"]["items"]),
          "every document is unpriced (0 = unpriced, not free)")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
