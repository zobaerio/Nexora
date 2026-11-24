"""Verify Queue 30 Unit KE — Storm-Position Bridge Line in the
Shibnagar Variant (KD follow-up).

Checks the wiring against its sources: tools/economy_sim.py
(print_shibnagar_variant's bridge check now prints the
single-earner storm line — the GE line — re-run on Shibnagar
rents, with the same starting balance and the same worst-dip
rule as the District 1 check),
tools/sim/tests/test_no_regression.py (new tests pin the
identity of the figures and the printed line; the pinned
default-run md5 does NOT move — the KE wiring touches only
the --shibnagar output),
docs/ECONOMY-SIM-REPORT-V7.md §18 (the prose matches the
tool output, including the identity table and the open
tier-sweep note), and docs/GDD-03-ECONOMY-AND-PROFESSIONS.md
§2 (the KE update). Re-runs the single-earner storm rows on
Shibnagar rents live and asserts the figures are identical
to District 1.
Prints one line per check and a summary; exits 0 only when
every check passes.
Run from the repo root: python3 tools/verify_queue30_ke.py
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CHECKS = []

KC_MD5 = "f6cec5a23109c4e7f9aeff3f7361e89d"

STORM_LINE = ("construction_worker    start   5000 + storm dip"
              "    -500 =    4500  OK  (worst storm position)")


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

    # 1. The figures hold: re-run the single-earner storm rows
    # on Shibnagar rents and compare with District 1 — every
    # storm position.
    prices = econ.load("prices.json")
    rents, _stock = econ.load_shibnagar_rents(prices)
    check(rents[1] == 2500,
          "tool: Shibnagar tier-1 rent is 2500", str(rents[1]))
    check(rents[econ.SHIBNAGAR_RENT_TIER["construction_worker"]]
          == 2500,
          "tool: the construction worker rents tier 1 in"
          " Shibnagar")
    w = next(w for w in prices["wages_monthly"]
             if w["profession_id"] == "construction_worker")
    override = rents[1]
    positions = (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                 econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS)
    expected = (econ.STORM_EARLY_DAYS, -500), \
        (econ.STORM_MID_DAYS, 0), (econ.STORM_LATE_DAYS, 0), \
        (econ.STORM_MEASURED_DAYS, -100)
    checked = 0
    identical = True
    for pos, dip in expected:
        d1 = econ.simulate(prices, w, "entry", storm_days=pos)
        sh = econ.simulate(prices, w, "entry", storm_days=pos,
                           rent_override=override)
        if (sh["min_balance"], sh["net"],
                sh["end_balance"]) != (d1["min_balance"], d1["net"],
                                       d1["end_balance"]):
            identical = False
        if d1["min_balance"] != dip:
            identical = False
        checked += 1
    check(checked == 4, "tool: 4 storm positions compared",
          str(checked))
    check(identical,
          "tool: every storm position is identical on"
          " Shibnagar rents (early -500, mid 0, late 0,"
          " measured -100)")
    worst = min(econ.simulate(
        prices, w, "entry", storm_days=pos,
        rent_override=override)["min_balance"] for pos in positions)
    check(worst == -500,
          "tool: worst Shibnagar storm dip is -500", str(worst))
    check(5000 + worst == 4500,
          "tool: the Shibnagar storm bridge is 5000 - 500"
          " = 4500")

    # 2. The wiring: the --shibnagar run prints the storm line
    # in the variant's own bridge check, with the District 1
    # figure; the default run is unchanged — the pinned md5
    # does NOT move.
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py"),
         "--shibnagar"],
        capture_output=True, cwd=ROOT)
    check(out.returncode == 0, "tool: --shibnagar run exits 0")
    sh_text = out.stdout.decode()
    variant = sh_text.split(
        "shibnagar first-month bridge check")[1]
    check(STORM_LINE in variant,
          "tool: the Shibnagar check prints the storm line")
    check("shibnagar BRIDGE FAIL rows: []" in sh_text,
          "tool: no Shibnagar bridge failure")
    d1 = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py")],
        capture_output=True, cwd=ROOT)
    check(d1.returncode == 0, "tool: default run exits 0")
    d1_text = d1.stdout.decode()
    md5 = hashlib.md5(d1.stdout).hexdigest()
    pinned = re.search(
        r'ECONOMY_SIM_BASELINE_MD5 = "([0-9a-f]{32})"',
        regress).group(1)
    check(md5 == pinned,
          "tool: default-run md5 equals the pinned baseline",
          md5)
    check(pinned == KC_MD5,
          "tool: the pinned md5 did NOT move from the KC"
          " baseline", pinned)
    check(KC_MD5 in regress,
          "tests: the KC md5 is the pinned baseline")
    check(STORM_LINE in d1_text,
          "tool: the D1 check prints the same storm line")
    d1_line = next(ln for ln in d1_text.splitlines()
                   if "storm dip" in ln)
    sh_line = next(ln for ln in variant.splitlines()
                   if "storm dip" in ln)
    check(sh_line == d1_line,
          "tool: the Shibnagar storm line equals the D1 line")
    check("rent_override=shib_rent" in sim_src,
          "tool: the Shibnagar line is computed on Shibnagar"
          " rents")
    # The six two-earner lines still print (no regression).
    for label in ("construction_worker + taxi-driver ",
                  "construction_worker + civil-engineer ",
                  "construction_worker + construction-worker",
                  "construction_worker + taxi-driver (mid)",
                  "construction_worker + civil-engineer (entry)",
                  "construction_worker + taxi-driver (mid,"
                  " renting)"):
        check(any(ln.strip().startswith(label)
                  for ln in variant.splitlines()),
              "tool: the Shibnagar check still prints a"
              " two-earner line", label.strip())

    # 3. The V7 report §18: prose matches the tool output.
    check("## 18. Addendum — Storm-position bridge line in the"
          " Shibnagar variant (Unit KE, Queue 30)" in report,
          "report §18: the addendum exists")
    check("5,000 − 500 = 4,500" in report,
          "report §18: the storm bridge figure is quoted")
    check("early −500" in report and "measured −100" in report,
          "report §18: the per-position dips are quoted")
    check("the pinned md5 does not move" in report.split(
        "## 18.")[1],
        "report §18: the md5 standing still is recorded")
    check("senior early −726" in report.split("## 18.")[1],
          "report §18: the tier-sweep open note is recorded")

    # 4. GDD-03 §2 records the KE update.
    check("Unit KE · Queue 30" in gdd03,
          "GDD-03 §2: the KE update is recorded")
    check("5,000 − 500 = 4,500" in gdd03,
          "GDD-03 §2: the storm bridge figure is quoted")

    # 5. Tests pin the KE identity and the wiring.
    check("test_single_earner_storm_dip_is_identical_on"
          "_shibnagar_rents" in regress,
          "tests: the identity test exists")
    check("test_shibnagar_bridge_check_prints_storm_line"
          in regress,
          "tests: the printed-line test exists")
    check("test_shibnagar_storm_line_matches_district1"
          in regress,
          "tests: the D1-match test exists")

    # 6. Scope: only the KE files changed for this unit.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 30 KE:",
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
                    "tools/verify_queue30_ke.py"},
          "scope: only the five KE files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
