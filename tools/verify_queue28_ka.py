"""Verify Queue 28 Unit KA — Renting-Cab Second Earner at
Another Tier (IB/IC follow-up).

Checks the extension against its sources: tools/economy_sim.py
(the renting variant now combines with a named tier for the
taxi driver — the rental stays the settlement's flat 5,200/month
whatever the tier — and the bridge check prints the renting
mid-tier line, the combined canonical start plus the worst
renting minbal),
tools/sim/tests/test_no_regression.py (the pinned md5 moves to
the KA baseline, the JA md5 kept as history; new tests pin the
measured figures and the refusals),
docs/ECONOMY-SIM-REPORT-V7.md §§8, 11, 12, 14 (the prose
matches the tool output, including the renting mid-tier bridge
figure), and docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the KA
update). A renting civil engineer is refused — civil engineers
hold no cab — and stays unmodelled.
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue28_ka.py
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CHECKS = []

JA_MD5 = "b70b18972aeb5c3b2d0273b986060058"


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

    # 1. The measured figures, from the tool itself — the
    # renting mid-tier taxi second earner, per tier and per
    # storm position. No figure is invented: each is recomputed
    # live by the tool from the measured scenarios.
    prices = econ.load("prices.json")
    w = next(x for x in prices["wages_monthly"]
             if x["profession_id"] == "construction_worker")
    positions = (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                 econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS)
    for tier, net in (("entry", 10950), ("mid", 14194),
                      ("senior", 17651)):
        row = econ.simulate(
            prices, w, tier, storm_days=econ.STORM_MEASURED_DAYS,
            second_earner="taxi_driver", second_earner_tier="mid",
            second_earner_renting_cab=True)
        check(row["min_balance"] == 0,
              f"tool: renting mid-tier measured minbal is 0"
              f" ({tier})", str(row["min_balance"]))
        check(row["net"] == net,
              f"tool: renting mid-tier measured net is {net}"
              f" ({tier})", str(row["net"]))
        check(row["second_earner_rental"] == 5200,
              f"tool: renting mid-tier rental is 5200 ({tier})",
              str(row["second_earner_rental"]))
        check(row["end_balance"] == row["net"],
              f"tool: renting mid-tier trajectory ends at net"
              f" ({tier})", str(row["end_balance"]))
    for tier, dip in (("entry", 0), ("mid", 0), ("senior", -56)):
        row = econ.simulate(
            prices, w, tier, storm_days=econ.STORM_EARLY_DAYS,
            second_earner="taxi_driver", second_earner_tier="mid",
            second_earner_renting_cab=True)
        check(row["min_balance"] == dip,
              f"tool: renting mid-tier early minbal is {dip}"
              f" ({tier})", str(row["min_balance"]))
    worst = min(econ.simulate(
        prices, w, tier, storm_days=pos,
        second_earner="taxi_driver", second_earner_tier="mid",
        second_earner_renting_cab=True)["min_balance"]
        for tier in ("entry", "mid", "senior")
        for pos in positions)
    check(worst == -56,
          "tool: worst renting mid-tier dip is -56 (senior,"
          " early)", str(worst))
    # The net drops by exactly 5,200 against the owning
    # mid-tier driver at every tier and every position.
    for tier in ("entry", "mid", "senior"):
        for pos in positions:
            owning = econ.simulate(
                prices, w, tier, storm_days=pos,
                second_earner="taxi_driver",
                second_earner_tier="mid")
            renting = econ.simulate(
                prices, w, tier, storm_days=pos,
                second_earner="taxi_driver",
                second_earner_tier="mid",
                second_earner_renting_cab=True)
            if owning["net"] - renting["net"] != 5200:
                check(False,
                      "tool: renting net is exactly 5200 below"
                      f" owning ({tier}/{pos})",
                      str(owning["net"] - renting["net"]))
                break
        else:
            continue
        break
    else:
        check(True,
              "tool: renting net is exactly 5200 below owning"
              " at every tier and position")
    # The combined start is the sum of the two earners' own
    # genesis balances, read from professions.json — the same
    # combined-start rule as IA/JA.
    profs = econ.load("professions.json")
    starts = {p["id"]: p.get("starting_balance_ncr", 0)
              for p in profs["professions"]}
    check(starts["construction_worker"] + starts["taxi_driver"]
          == 10000,
          "tool: renting mid-tier combined start is 10000"
          " (5000+5000)")
    check(prices["taxi_fares"]["cab_rental_ncr_per_day"]
          * econ.WORK_DAYS == 5200,
          "tool: the settlement's charge is 200 x 26 = 5200")
    # A renting civil engineer is refused — civil engineers
    # hold no cab — with or without a named tier.
    for kw in ({"second_earner": "civil_engineer"},
               {"second_earner": "civil_engineer",
                "second_earner_tier": "entry"}):
        try:
            econ.simulate(prices, w, "entry",
                          second_earner_renting_cab=True, **kw)
            check(False,
                  "tool: a renting civil engineer is refused"
                  f" ({kw})")
        except ValueError as e:
            check("hold no cab" in str(e),
                  "tool: a renting civil engineer is refused"
                  f" ({kw})", str(e)[:60])

    # 2. The default run: the md5 moves to the KA baseline
    # (the pin in test_no_regression.py, read live — not a
    # literal in this script, so the check passes both
    # pre- and post-commit and survives a later unit moving
    # the pin again, as long as the pin moves with it); the
    # new section and bridge line are printed; the IA/JA
    # lines are unchanged; nothing fails.
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py")],
        capture_output=True, cwd=ROOT)
    check(out.returncode == 0, "tool: default run exits 0")
    text = out.stdout.decode()
    md5 = hashlib.md5(out.stdout).hexdigest()
    pinned = re.search(
        r'ECONOMY_SIM_BASELINE_MD5 = "([0-9a-f]{32})"',
        regress).group(1)
    check(md5 == pinned,
          "tool: default-run md5 equals the pinned baseline",
          md5)
    check(pinned != JA_MD5,
          "tool: the pinned md5 moved from the JA baseline",
          pinned)
    check(JA_MD5 in regress,
          "tests: the JA md5 is kept as history")
    check("renting-cab taxi-driver second earner at another"
          " tier storm-position month (Unit KA" in text,
          "tool: the KA section is printed")
    check("construction_worker          entry         0       0"
          "       0        0       0  (net 10950)" in text,
          "tool: the KA entry row is printed")
    check("construction_worker          senior      -56       0"
          "       0        0       0  (net 17651)" in text,
          "tool: the KA senior row is printed")
    check("construction_worker + taxi-driver (mid, renting)"
          " start  10000 + renting dip     -56 =    9944  OK"
          "  (worst renting storm position)" in text,
          "tool: the renting mid-tier bridge line is printed")
    check("construction_worker + taxi-driver    start  10000"
          " + mixed dip     -72 =    9928  OK  (worst mixed"
          " storm position)" in text,
          "tool: the IA taxi-second bridge line is unchanged")
    check("construction_worker + taxi-driver (mid) start"
          "  10000 + other-tier dip       0 =   10000  OK"
          "  (worst other-tier storm position)" in text,
          "tool: the JA mid-tier taxi-second bridge line is"
          " unchanged")
    check("BRIDGE FAIL rows: []" in text,
          "tool: no bridge failure in any position")

    # 3. The V7 report §§8, 11, 12, 14: prose matches the
    # tool output.
    check("## 14. Addendum — Renting-cab second earner at"
          " another tier (Unit KA, Queue 28)" in report,
          "report §14: the addendum exists")
    check("10,000 − 56 = 9,944" in report,
          "report §14: the renting bridge figure is quoted")
    check(md5 in report,
          "report §14: the KA baseline md5 is quoted", md5)
    check(JA_MD5 in report,
          "report §14: the JA md5 is kept as history")
    check("construction_worker + taxi-driver (mid, renting)"
          " start  10000 + renting dip     -56 =    9944  OK"
          "  (worst renting storm position)" in report,
          "report §8: the renting bridge line is quoted"
          " verbatim")
    check("Unit KA DONE 2026-11-24" in report.split("## 12.")[0],
          "report §11: the renting-variant gap is marked KA"
          " DONE")
    check("Unit KA DONE 2026-11-24" in report.split("## 12.")[1],
          "report §12: the renting-variant gap is marked KA"
          " DONE")
    check("Civil engineers hold no cab" in report,
          "report §14: the renting-CE refusal is stated")

    # 4. GDD-03 §2 records the KA update.
    check("Unit KA · Queue 28" in gdd03,
          "GDD-03 §2: the KA update is recorded")
    check("10,000 − 56 = 9,944" in gdd03,
          "GDD-03 §2: the renting bridge figure is quoted")
    check("civil engineers hold no cab" in gdd03,
          "GDD-03 §2: the renting-CE refusal is stated")
    check("10,950 / 14,194 / 17,651" in gdd03,
          "GDD-03 §2: the renting nets are quoted")

    # 5. Tests pin the KA figures and refusals.
    check("test_renting_cab_second_earner_at_another_tier"
          "_is_measured" in regress,
          "tests: the KA measured-figures test exists")
    check("test_renting_mid_tier_bridge_line_is_printed"
          in regress,
          "tests: the KA bridge-line test exists")
    check("test_renting_cab_second_earner_at_another_tier"
          "_refusals" in regress,
          "tests: the KA refusals test exists")

    # 6. Scope: only the KA files changed for this unit. The
    # check reads the union of the working tree (before the
    # unit is committed) and the unit's own commit, found by
    # its message (after the commit — and still after later
    # units commit, because the message match is per-unit).
    # The Queue 25 scripts checked the dirty tree only and
    # failed post-commit; the local `main` branch is stale
    # (Session 03), so a diff against it is meaningless here.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 28 KA:",
         "HEAD"], capture_output=True, cwd=ROOT).stdout.decode()
    for sha in own.splitlines():
        if not sha.strip():
            continue
        shown = subprocess.run(
            ["git", "show", "--name-only", "--pretty=format:",
             sha.strip()], capture_output=True,
            cwd=ROOT).stdout.decode()
        names |= {ln for ln in shown.splitlines() if ln.strip()}
    check(names == {"tools/economy_sim.py",
                    "tools/sim/tests/test_no_regression.py",
                    "docs/ECONOMY-SIM-REPORT-V7.md",
                    "docs/GDD-03-ECONOMY-AND-PROFESSIONS.md",
                    "tools/verify_queue28_ka.py"},
          "scope: only the five KA files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
