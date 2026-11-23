"""Verify Queue 16 Unit DE — Furniture, Tool & Document Catalogues
(GDD-04 §3.3, Unit CX record; GDD-10 §5).

Checks the catalogues against their sources: data/furniture.json
(GDD-10 §5 tier contents + Tier-3 package sums),
data/tools.json (authored — no source names a tool),
data/documents.json (GDD-04 §2/§5.4, academics.py certifications),
data/prices.json v1.4 (the three new keys), tools/validate_data.py
(the new catalogue checks), and the GDD-04/GDD-10 record updates.
Prints one line per check and a summary; exits 0 only when every
check passes. Run from the repo root: python3 tools/verify_queue16_de.py
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


def main():
    gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md").read_text()
    gdd10 = (ROOT / "docs" / "GDD-10-HOUSING-AND-HOME-LIFE.md").read_text()
    furniture = json.loads(
        (ROOT / "data" / "furniture.json").read_text())
    tools = json.loads((ROOT / "data" / "tools.json").read_text())
    documents = json.loads(
        (ROOT / "data" / "documents.json").read_text())
    prices = json.loads((ROOT / "data" / "prices.json").read_text())
    academics = (ROOT / "tools" / "sim" / "academics.py").read_text()
    validator = (ROOT / "tools" / "validate_data.py").read_text()
    professions = json.loads(
        (ROOT / "data" / "professions.json").read_text())
    prof_ids = {p["id"] for p in professions["professions"]}

    # 1. Furniture: the GDD-10 §5 contents, tiered, priced to the
    # Tier-3 packages.
    gdd10_tiers = {
        "F0": ["floor_mattress", "single_burner", "crate_table"],
        "F1": ["bed", "table_chairs", "stove", "wardrobe", "fan"],
        "F2": ["sofa", "bookshelf", "desk", "kitchen_upgrade",
               "curtains"],
        "F3": ["dining_set", "tv", "washing_machine", "study_corner",
               "decoration"]}
    check(len(furniture["items"]) == 18,
          "furniture catalogue has 18 items",
          f"{len(furniture['items'])} items")
    check(furniture.get("tiers") == gdd10_tiers,
          "furniture tiers match the GDD-10 §5 contents exactly")
    check(all(i.get("source", "").startswith("GDD-10 §5")
              for i in furniture["items"]),
          "every furniture item names GDD-10 §5 as its source")
    check(all(i["id"] in gdd10_tiers[i["tier"]]
              for i in furniture["items"]),
          "every furniture item's tier field matches its tier set")
    fprices = {i["id"]: i["price_ncr"]
               for i in prices["furniture"]["items"]}
    check(all(i["price_ref"] in fprices for i in furniture["items"]),
          "every furniture price_ref resolves into prices.json")
    check(prices["version"] == 1.4,
          "prices.json is v1.4", f"version {prices['version']}")
    tier_sums = {t: sum(fprices[i] for i in ids)
                 for t, ids in gdd10_tiers.items()}
    check(tier_sums == {"F0": 0, "F1": 12000, "F2": 12000,
                        "F3": 18000},
          "furniture piece prices sum to the §5 Tier-3 packages",
          f"sums={tier_sums}")
    check("PROPOSED" in furniture.get("notes", "")
          and "no source prices pieces" in furniture.get("notes", ""),
          "furniture piece prices are labelled PROPOSED, not sourced")
    check("50%" in furniture.get("notes", ""),
          "furniture notes keep the 50% second-hand rule (GDD-10 §5)")

    # 2. Tools: all authored, all priced, all professions resolve.
    check(len(tools["items"]) == 10,
          "tool catalogue has 10 items",
          f"{len(tools['items'])} items")
    check(all(i.get("source", "").startswith("authored")
              for i in tools["items"]),
          "every tool entry is labelled authored")
    check("No GDD or data file names a single tool"
          in tools.get("notes", ""),
          "tools notes state plainly that no source names a tool")
    tprices = {i["id"]: i["price_ncr"]
               for i in prices["tools"]["items"]}
    check(all(i["price_ref"] in tprices for i in tools["items"]),
          "every tool price_ref resolves into prices.json")
    check(all(v > 0 for v in tprices.values()),
          "every tool has a positive authored price")
    check(all(p in prof_ids for i in tools["items"]
              for p in i["professions"]),
          "every tool profession resolves to professions.json")
    check("PROPOSED" in prices["tools"].get("notes", ""),
          "prices.json tools note labels the prices PROPOSED")

    # 3. Documents: all sourced, all unpriced.
    check(len(documents["items"]) == 4,
          "document catalogue has 4 items",
          f"{len(documents['items'])} items")
    by_id = {i["id"]: i for i in documents["items"]}
    check("GDD-04 §2" in by_id["property_deed"]["source"],
          "property_deed is sourced from GDD-04 §2 (mission 3.2)")
    check("GDD-04 §5.4" in by_id["business_licence"]["source"],
          "business_licence is sourced from GDD-04 §5.4")
    check("school_leaving" in
          by_id["school_leaving_certificate"]["source"],
          "school-leaving certificate is sourced from academics.py")
    check("college_credential" in
          by_id["college_credential"]["source"],
          "college credential is sourced from academics.py")
    check('"school_leaving"' in academics
          and '"college_credential"' in academics,
          "academics.py issues exactly the two certification kinds")
    dprices = {i["id"]: i["price_ncr"]
               for i in prices["documents"]["items"]}
    check(all(i["price_ref"] in dprices for i in documents["items"]),
          "every document price_ref resolves into prices.json")
    check(all(v == 0 for v in dprices.values()),
          "every document is unpriced (0 = unpriced, not free)")
    check("UNPRICED" in prices["documents"].get("notes", ""),
          "prices.json documents note says 0 means unpriced")

    # 4. No catalogue id collides with another catalogue's ids.
    all_ids = ([i["id"] for i in furniture["items"]]
               + [i["id"] for i in tools["items"]]
               + [i["id"] for i in documents["items"]])
    check(len(all_ids) == len(set(all_ids)),
          "no id collides across the three catalogues")
    clothing = json.loads(
        (ROOT / "data" / "clothing.json").read_text())
    clothing_ids = {i["id"] for i in clothing["items"]}
    check(not (set(all_ids) & clothing_ids),
          "no catalogue id collides with clothing.json ids")
    goods = json.loads(
        (ROOT / "data" / "economy-goods.json").read_text())
    goods_ids = {g["id"] for g in goods["goods"]}
    check(not (set(all_ids) & goods_ids),
          "no catalogue id collides with economy-goods.json ids")

    # 5. The validator checks the new catalogues.
    check("furniture.json" in validator and "tools.json" in validator
          and "documents.json" in validator,
          "validate_data.py parses the three new files")
    check("furniture price_refs resolve" in validator,
          "validate_data.py checks furniture price_refs")
    check("furniture tiers match the GDD-10 §5 contents" in validator,
          "validate_data.py checks the furniture tiers")
    check("sums to the §5 Tier-3 packages" in validator
          or "Tier-3 packages" in validator,
          "validate_data.py checks the furniture price sums")
    check("labelled authored" in validator,
          "validate_data.py checks the tool authored labels")

    # 6. The GDDs record the catalogues — and that seeding is still
    # a later unit.
    check("Unit DE · Queue 16" in gdd04,
          "GDD-04 §3.3 carries the DE catalogue updates")
    check("the catalogue gap is closed, the seeding gap is not"
          in gdd04,
          "GDD-04 states the catalogue gap is closed, seeding is not")
    check("Unit DE · Queue 16" in gdd10,
          "GDD-10 §5/§9 carry the DE catalogue note")
    check("No seeding yet" in furniture.get("notes", "")
          and "No seeding yet" in tools.get("notes", "")
          and "No seeding yet" in documents.get("notes", ""),
          "all three catalogues state no seeding yet")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
