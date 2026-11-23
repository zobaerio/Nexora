"""Verify Queue 14 Unit CC — District 2 + Shibnagar discoverables
(the BM §3.4 follow-up: the discovery set was District 1 only).

Checks the extended set against the sources it must resolve to:
GDD-04 §3.1/§3.4, GDD-15 §15.2, data/district1-blockout.json,
data/district2-blockout.json, data/city2-shibnagar.json,
tools/validate_data.py. Run from the repo root:
python3 tools/verify_queue14_cc.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKS = []


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def inside(box, at):
    x, z = at
    return (box["x0"] <= x <= box["x1"] and box["z0"] <= z <= box["z1"])


def main():
    gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md").read_text()
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    d1 = json.loads((ROOT / "data" / "district1-blockout.json").read_text())
    d2 = json.loads((ROOT / "data" / "district2-blockout.json").read_text())
    c2 = json.loads((ROOT / "data" / "city2-shibnagar.json").read_text())
    validator = (ROOT / "tools" / "validate_data.py").read_text()

    # 1. The set is now 14 landmarks + 1 bus route.
    check("14 landmarks + 1 bus route" in gdd04,
          "GDD-04 §3.4 states the set is 14 landmarks + 1 bus route")
    check("8 District 1 + 6 District 2, PROPOSED" in gdd04,
          "GDD-04 §3.1 states the 8+6 split")
    check("District 2 landmarks (Unit CC" in gdd04,
          "GDD-04 §3.4 has the District 2 landmarks subsection, Unit CC")

    # 2. Every D2 discoverable in the doc matches the D2 file.
    sec = gdd04.split("District 2 landmarks (Unit CC")[1]
    sec = sec.split("**Shibnagar")[0]
    doc_ids = re.findall(r"`(d2_lm_[a-z_]+)`", sec)
    check(sorted(doc_ids) == sorted(lm["id"] for lm in d2["landmarks"]),
          "doc lists exactly the 6 D2 landmark ids from the file",
          f"doc={sorted(doc_ids)}")
    boxes = d2["zone_boxes_m"]
    for lm in d2["landmarks"]:
        zone = {"d2_lm_northgate_tower": "d2_market",
                "d2_lm_north_bazar_hall": "d2_market",
                "d2_lm_maidan_pavilion": "d2_maidan",
                "d2_lm_garden_tank": "d2_garden",
                "d2_lm_north_gate_depot": "d2_transport",
                "d2_lm_north_heights_view": "d2_uptown"}[lm["id"]]
        if lm["id"] == "d2_lm_northgate_tower":
            check(not inside(boxes[zone], lm["at"]),
                  "northgate tower really falls outside every D2 box",
                  f"at={lm['at']}")
            check("Assigned by description" in sec,
                  "tower zone is assigned by description, labelled")
        else:
            check(inside(boxes[zone], lm["at"]),
                  f"{lm['id']} really sits inside its {zone} box",
                  f"at={lm['at']}")
        check(lm.get("status") == "PROPOSED",
              f"{lm['id']} stays labelled PROPOSED")

    # 3. Set order: D1, then D2, then routes.
    check("District 1 landmarks in GDD-02 §4 order, then District 2 "
          "landmarks in `district2-blockout.json` order, then routes"
          in gdd04,
          "§3.4 eligibility states the D1-then-D2-then-routes set order")

    # 4. Shibnagar: honestly zero, candidates named but not added.
    check("Shibnagar — nothing joins (Unit CC" in gdd04,
          "GDD-04 §3.4 has the Shibnagar nothing-joins subsection")
    check("landmarks" not in c2,
          "city2-shibnagar.json really has no landmarks array")
    check("Ferry Ghat" in gdd04 and "Bus Stand" in gdd04,
          "§3.4 names the Ferry Ghat / Bus Stand as future candidates")
    check("not as members" in gdd04,
          "§3.4 states the candidates are NOT added to the set")

    # 5. The discovery favour can name a D2 discoverable.
    check("Northgate Tower" in gdd15,
          "GDD-15 §15.2 names a D2 landmark for <discoverable_name>")

    # 6. The validator guards the extended set.
    check("check_discovery_set" in validator,
          "validate_data.py guards the discovery set")
    res = subprocess.run([sys.executable, "tools/validate_data.py"],
                         cwd=ROOT, capture_output=True, text=True)
    check(res.returncode == 0, "validate_data.py green",
          (res.stdout + res.stderr).strip().splitlines()[-1])

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
