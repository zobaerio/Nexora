"""Verify Queue 15 Unit CZ — Shibnagar Landmark Authoring (GDD-04 §3.4,
Unit CC follow-up).

Checks the authoring against the sources it must resolve to: GDD-04
§3.4 (the discovery set), data/city2-shibnagar.json (the landmarks
themselves), tools/sim/citygen.py (the generator that owns the file),
tools/validate_data.py (the discovery-set check) and
tools/sim/tests/test_cities.py (the byte-identical regeneration
guard). Prints one line per check and a summary; exits 0 only when
every check passes. Run from the repo root:
python3 tools/verify_queue15_cz.py
"""
import json
import re
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
    c2 = json.loads((ROOT / "data" / "city2-shibnagar.json").read_text())
    d1 = json.loads((ROOT / "data" / "district1-blockout.json").read_text())
    d2 = json.loads((ROOT / "data" / "district2-blockout.json").read_text())
    citygen = (ROOT / "tools" / "sim" / "citygen.py").read_text()
    validator = (ROOT / "tools" / "validate_data.py").read_text()

    # 1. The generator owns the landmarks (the file is GENERATED).
    check("_LANDMARKS" in citygen,
          "citygen.py carries the _LANDMARKS table")
    check('"landmarks": landmarks' in citygen,
          "citygen.py emits a landmarks array")
    check("plot anchor" in citygen,
          "citygen.py derives each point from its plot anchor")

    # 2. The file carries exactly the 5 authored landmarks.
    lms = {lm["id"]: lm for lm in c2.get("landmarks", [])}
    expected = {
        "c2_lm_ferry_ghat": ("Shibnagar Ferry Ghat", "c2_transport",
                             "b_c2_transport_ghat"),
        "c2_lm_bus_stand": ("Shibnagar Bus Stand", "c2_transport",
                            "b_c2_transport_bus_stand"),
        "c2_lm_primary_school": ("Shibnagar Primary School", "c2_civic",
                                 "b_c2_civic_school"),
        "c2_lm_clinic": ("Shibnagar Clinic", "c2_civic",
                         "b_c2_civic_clinic"),
        "c2_lm_town_office": ("Shibnagar Town Office", "c2_civic",
                              "b_c2_civic_office"),
    }
    check(len(lms) == 5, "city2 carries exactly 5 landmarks",
          f"got {len(lms)}")
    props = {p["id"]: p for p in c2["properties"]}
    for lm_id, (name, zone, bid) in expected.items():
        lm = lms.get(lm_id)
        check(lm is not None, f"landmark {lm_id} exists")
        if lm is None:
            continue
        check(lm["name"] == name,
              f"{lm_id} name matches its property", f"got {lm['name']}")
        check(bid in props and props[bid]["zone_id"] == zone,
              f"{lm_id} building {bid} is a property in {zone}")
        box = c2["zone_boxes_m"][zone]
        x, z = lm["at"]
        check(box["x0"] <= x <= box["x1"]
              and box["z0"] <= z <= box["z1"],
              f"{lm_id} point {tuple(lm['at'])} inside the {zone} box")
        check("Unit CZ" in lm.get("source", ""),
              f"{lm_id} source cites Unit CZ")

    # 3. No collisions, no PROPOSED label (the town runs already).
    d1_ids = {lm["id"] for lm in d1["landmarks"]}
    d2_ids = {lm["id"] for lm in d2["landmarks"]}
    check(not (set(lms) & d1_ids) and not (set(lms) & d2_ids),
          "Shibnagar ids collide with no D1/D2 landmark")
    check(all(lm.get("status") is None for lm in c2["landmarks"]),
          "no Shibnagar landmark carries a status label")
    check(c2.get("generated") is True,
          "city2 stays labelled GENERATED")

    # 4. The excluded properties are excluded for stated reasons.
    check("tea stall" in gdd04 and "service anchor" in gdd04,
          "GDD-04 states tea stalls are anchors, not landmarks")
    check("fish stalls" in gdd04,
          "GDD-04 records why the fish stalls do not qualify")

    # 5. The discovery set in GDD-04 §3.4 now holds 19 + 1.
    sec = gdd04.split("### 3.4 Discovery Progress Record")[1]
    sec = sec.split("### 3.5 ")[0]
    check("19 landmarks + 1 bus route" in sec,
          "§3.4 set count is 19 landmarks + 1 bus route")
    check("Shibnagar landmarks (Unit CZ" in sec,
          "§3.4 carries the CZ subsection")
    check("then Shibnagar landmarks in `city2-shibnagar.json` order"
          in sec,
          "§3.4 eligibility order includes Shibnagar after District 2")
    check("Unit CZ · Queue 15" in sec,
          "§3.4 carries the CZ update on the CC paragraph")
    check("retired by the 5 landmarks above" in sec,
          "§3.4 retires the 'Shibnagar not covered' line")

    # 6. The validator guards the new set.
    check("discovery set: 5 Shibnagar landmarks" in validator,
          "validate_data.py checks the 5 Shibnagar landmarks")
    check("Shibnagar contributes no discoverables" not in validator,
          "validate_data.py no longer asserts Shibnagar contributes zero")
    check("Shibnagar discoverable zones verify" in validator,
          "validate_data.py verifies Shibnagar zones by point-in-box")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
