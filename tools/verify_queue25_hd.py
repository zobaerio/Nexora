"""Verify Queue 25 Unit HD — Mixed-Profession Two-Earner Scenario
(GD/GC follow-up).

Checks the extension against its sources: tools/economy_sim.py
(simulate() takes a mixed-profession second earner — taxi_driver
at entry / civil_engineer at mid, the settlement's measured
pairings — each earner taxed on their own gross with their own
uplift, costs following engine._living_costs for two adults, the
storm-position effect coming from the first earner alone),
tools/sim/tests/test_no_regression.py (the pinned md5 moves to
the HD baseline, the HA md5 kept as history),
docs/ECONOMY-SIM-REPORT-V7.md §9 (the addendum, with verbatim
output matching the tool), and docs/GDD-03-ECONOMY-AND-
PROFESSIONS.md §2 (the HD update).
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue25_hd.py
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CHECKS = []


def check(cond, label, detail=""):
    CHECKS.append((bool(cond), label, detail))
    print(f"{'PASS' if cond else 'FAIL'}  {label}"
          + (f"  ({detail})" if detail else ""))


def main():
    from tools import economy_sim as econ
    sim_src = (ROOT / "tools" / "economy_sim.py").read_text()
    regress = (ROOT / "tools" / "sim" / "tests"
               / "test_no_regression.py").read_text()
    report = (ROOT / "docs" / "ECONOMY-SIM-REPORT-V7.md").read_text()
    gdd03 = (ROOT / "docs" / "GDD-03-ECONOMY-AND-PROFESSIONS.md").read_text()

    # 1. The measured pairings, fixed at the measured tiers.
    check(econ.SECOND_EARNER_MEASURED_TIER == {
        "taxi_driver": "entry", "civil_engineer": "mid"},
        "economy_sim.py: the measured pairings are taxi/entry"
        " + civil-engineer/mid",
        str(econ.SECOND_EARNER_MEASURED_TIER))
    prices = econ.load("prices.json")
    w = next(x for x in prices["wages_monthly"]
             if x["profession_id"] == "construction_worker")

    # 2. The measured month-1 minbal per position, both pairings.
    taxi_measured = {t: econ.simulate(
        prices, w, t, storm_days=econ.STORM_MEASURED_DAYS,
        second_earner="taxi_driver")["min_balance"]
        for t in ("entry", "mid", "senior")}
    check(taxi_measured == {"entry": 0, "mid": 0, "senior": 0},
          "tool: taxi-second measured dips nothing",
          str(taxi_measured))
    check(econ.simulate(prices, w, "senior",
                        storm_days=econ.STORM_EARLY_DAYS,
                        second_earner="taxi_driver")["min_balance"]
          == -72,
          "tool: taxi-second senior early dips -72")
    ce_measured = {t: econ.simulate(
        prices, w, t, storm_days=econ.STORM_MEASURED_DAYS,
        second_earner="civil_engineer")["min_balance"]
        for t in ("entry", "mid", "senior")}
    check(ce_measured == {"entry": -8623, "mid": -5499,
                          "senior": -2170},
          "tool: civil-engineer-second measured dips -8623/-5499/"
          "-2170",
          str(ce_measured))
    check(econ.simulate(prices, w, "entry",
                        storm_days=econ.STORM_LATE_DAYS,
                        second_earner="civil_engineer")
          ["min_balance"] == -8323,
          "tool: civil-engineer-second late is shallower (-8323)")

    # 3. The second earner's pay is storm-independent, and the
    # trajectory ends at net for every position.
    for pid2, pay in (("taxi_driver", 14000),
                      ("civil_engineer", 38000)):
        for tier in ("entry", "mid", "senior"):
            for pos in (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                        econ.STORM_LATE_DAYS,
                        econ.STORM_MEASURED_DAYS):
                single = econ.simulate(prices, w, tier,
                                       storm_days=pos)
                mixed = econ.simulate(prices, w, tier,
                                      storm_days=pos,
                                      second_earner=pid2)
                if mixed["gross"] != single["gross"] + pay:
                    check(False,
                          f"tool: {pid2}/{tier}/{pos} gross is storm-"
                          "independent")
                    break
                if mixed["end_balance"] != mixed["net"]:
                    check(False,
                          f"tool: {pid2}/{tier}/{pos} trajectory ends"
                          " at net")
                    break
            else:
                continue
            break
        else:
            check(True,
                  f"tool: {pid2} pay is storm-independent and every"
                  " trajectory ends at net")
    # Costs follow _living_costs for two adults.
    for pid2, delta in (("taxi_driver", 4200),
                        ("civil_engineer", 9800)):
        ok = all(
            econ.simulate(prices, w, t,
                          storm_days=econ.STORM_MEASURED_DAYS,
                          second_earner=pid2)["costs_total"]
            - econ.simulate(prices, w, t,
                            storm_days=econ.STORM_MEASURED_DAYS)
            ["costs_total"] == delta
            for t in ("entry", "mid", "senior"))
        check(ok, f"tool: {pid2} costs delta is {delta} every tier")

    # 4. The default run: md5 moves to the HD baseline; the
    # printed sections carry the measured figures.
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py")],
        capture_output=True, cwd=ROOT)
    check(out.returncode == 0, "tool: default run exits 0")
    text = out.stdout.decode()
    md5 = hashlib.md5(out.stdout).hexdigest()
    check(md5 == "5431558ffa3d023c436366c26535f932",
          "tool: default-run md5 is the HD baseline", md5)
    check("5431558ffa3d023c436366c26535f932" in regress,
          "tests: the HD md5 is pinned in test_no_regression.py")
    check("ede430d0bf391fac3f8599334f55b77b" in regress,
          "tests: the HA md5 is kept as history")
    check("mixed-profession two-earner storm-position month"
          in text,
          "tool: the mixed section is printed")
    check("taxi-driver second earner (entry 14,000, per-fare)"
          in text,
          "tool: the taxi section names the pairing")
    check("civil-engineer second earner (mid 38,000, monthly)"
          in text,
          "tool: the civil-engineer section names the pairing")
    check("BRIDGE FAIL rows: []" in text,
          "tool: no bridge failure in any position")

    # 5. The V7 report §9: the addendum, the tables, the verbatim
    # output matching the tool, and the honest limit.
    check("## 9. Addendum — Mixed-profession two-earner" in report,
          "report §9: the addendum exists")
    check("| entry | 0 | 0 | 0 | 0 | 0 | 10,700 | −500 | −100 |"
          in report,
          "report §9: the taxi table's entry row")
    check("| entry | −8,623 | −8,623 | −8,323 | −8,623 | −8,603 |"
          " 27,950 | −500 | −100 |" in report,
          "report §9: the civil-engineer table's entry row")
    check("10,000 − 8,623 = 1,377" in report,
          "report §9: the civil-engineer bridge figure is quoted")
    check("the depth is timing, not storms" in report.replace(
        "\n", " "),
          "report §9: the timing limit is stated, not hidden")
    check("Unit HE's decision" in report,
          "report §9: the timing question points to HE")
    blocks = re.findall(r"```\n(mixed-profession.*?)\n```", report,
                        re.S)
    tool_sections = "\n\n".join(
        s for s in text.split("\n\n")
        if s.startswith("mixed-profession"))
    check(len(blocks) == 1 and blocks[0].strip()
          == tool_sections.strip(),
          "report §9: the verbatim output matches the tool")
    check("Unit HD DONE 2026-11-24" in report,
          "report §7: the mixed-profession gap is marked HD DONE")
    check("5431558ffa3d023c436366c26535f932" in report,
          "report §8: the md5 is the HD baseline")

    # 6. GDD-03 §2 records the HD update.
    check("Unit HD · Queue 25" in gdd03,
          "GDD-03 §2: the HD update is recorded")
    check("−8,623 / −5,499 / −2,170" in gdd03,
          "GDD-03 §2: the civil-engineer dips are quoted")
    check("Storm days do not change the second earner's pay"
          in gdd03,
          "GDD-03 §2: the storm-independence is stated")

    # 7. Scope: only the HD files changed on this branch since
    # the HC commit.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    check(names == {"tools/economy_sim.py",
                    "tools/sim/tests/test_no_regression.py",
                    "docs/ECONOMY-SIM-REPORT-V7.md",
                    "docs/GDD-03-ECONOMY-AND-PROFESSIONS.md",
                    "tools/verify_queue25_hd.py"},
          "scope: only the five HD files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
