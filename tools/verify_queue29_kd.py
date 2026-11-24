"""Verify Queue 29 Unit KD — Two-Earner Lines in the Shibnagar
Variant (KA follow-up).

Checks the wiring against its sources: tools/economy_sim.py
(print_shibnagar_variant's bridge check now prints the six
two-earner lines — IA mixed, JA same-tier + other-tier, KA
renting mid-tier — re-run on Shibnagar rents, with the same
combined starts and the same worst-dip rule as the District 1
check),
tools/sim/tests/test_no_regression.py (new tests pin the
identity of the figures and the printed lines; the pinned
default-run md5 does NOT move — the KD wiring touches only the
--shibnagar output),
docs/ECONOMY-SIM-REPORT-V7.md §17 (the prose matches the tool
output, including the identity table), and docs/GDD-03-
ECONOMY-AND-PROFESSIONS.md §2 (the KD update). Re-runs the
two-earner households on Shibnagar rents live and asserts the
figures are identical to District 1.
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue29_kd.py
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

TWO_EARNER_LINES = (
    "construction_worker + taxi-driver    start  10000"
    " + mixed dip     -72 =    9928  OK"
    "  (worst mixed storm position)",
    "construction_worker + civil-engineer start  30000"
    " + mixed dip   -8623 =   21377  OK"
    "  (worst mixed storm position)",
    "construction_worker + construction-worker start"
    "  10000 + same-tier dip   -1231 =    8769  OK"
    "  (worst same-tier storm position)",
    "construction_worker + taxi-driver (mid) start  10000"
    " + other-tier dip       0 =   10000  OK"
    "  (worst other-tier storm position)",
    "construction_worker + civil-engineer (entry) start"
    "  30000 + other-tier dip   -3210 =   26790  OK"
    "  (worst other-tier storm position)",
    "construction_worker + taxi-driver (mid, renting) start"
    "  10000 + renting dip     -56 =    9944  OK"
    "  (worst renting storm position)",
)


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

    # 1. The figures hold: re-run the two-earner households on
    # Shibnagar rents and compare with District 1 — every
    # pairing, every tier, every storm position.
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
    pairings = (
        {"second_earner": True},
        {"second_earner": "taxi_driver"},
        {"second_earner": "taxi_driver",
         "second_earner_tier": "mid"},
        {"second_earner": "taxi_driver",
         "second_earner_tier": "mid",
         "second_earner_renting_cab": True},
        {"second_earner": "civil_engineer"},
        {"second_earner": "civil_engineer",
         "second_earner_tier": "entry"},
    )
    positions = (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                 econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS)
    checked = 0
    identical = True
    for kw in pairings:
        for tier in ("entry", "mid", "senior"):
            for pos in positions:
                d1 = econ.simulate(prices, w, tier,
                                   storm_days=pos, **kw)
                sh = econ.simulate(prices, w, tier,
                                   storm_days=pos,
                                   rent_override=override, **kw)
                if (sh["min_balance"], sh["net"],
                        sh["end_balance"]) != (d1["min_balance"],
                                               d1["net"],
                                               d1["end_balance"]):
                    identical = False
                checked += 1
    check(checked == 72, "tool: 72 two-earner rows compared",
          str(checked))
    check(identical,
          "tool: every two-earner row is identical on"
          " Shibnagar rents")
    # The worst dips per pairing are identical too.
    for kw, worst in (
            ({"second_earner": True}, -1231),
            ({"second_earner": "taxi_driver"}, -72),
            ({"second_earner": "taxi_driver",
              "second_earner_tier": "mid"}, 0),
            ({"second_earner": "taxi_driver",
              "second_earner_tier": "mid",
              "second_earner_renting_cab": True}, -56),
            ({"second_earner": "civil_engineer"}, -8623),
            ({"second_earner": "civil_engineer",
              "second_earner_tier": "entry"}, -3210)):
        got = min(econ.simulate(prices, w, tier, storm_days=pos,
                                rent_override=override,
                                **kw)["min_balance"]
                  for tier in ("entry", "mid", "senior")
                  for pos in positions)
        check(got == worst,
              f"tool: worst Shibnagar dip is {worst} ({kw})",
              str(got))

    # 2. The wiring: the --shibnagar run prints all six lines
    # with the District 1 figures; the default run is
    # unchanged — the pinned md5 does NOT move.
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py"),
         "--shibnagar"],
        capture_output=True, cwd=ROOT)
    check(out.returncode == 0, "tool: --shibnagar run exits 0")
    sh_text = out.stdout.decode()
    for line in TWO_EARNER_LINES:
        check(line in sh_text,
              "tool: the Shibnagar check prints a two-earner"
              " line", line[:60])
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
    for line in TWO_EARNER_LINES:
        check(line in d1_text,
              "tool: the D1 check prints the same line",
              line[:60])
    # Line by line, the two runs agree.
    for label in ("construction_worker + taxi-driver ",
                  "construction_worker + civil-engineer ",
                  "construction_worker + construction-worker",
                  "construction_worker + taxi-driver (mid)",
                  "construction_worker + civil-engineer (entry)",
                  "construction_worker + taxi-driver (mid,"
                  " renting)"):
        d1_line = next(ln for ln in d1_text.splitlines()
                       if ln.strip().startswith(label))
        sh_line = next(ln for ln in sh_text.splitlines()
                       if ln.strip().startswith(label))
        check(sh_line == d1_line,
              "tool: the Shibnagar line equals the D1 line",
              label.strip())
    check("rent_override=shib_rent" in sim_src,
          "tool: the Shibnagar lines are computed on"
          " Shibnagar rents")

    # 3. The V7 report §17: prose matches the tool output.
    check("## 17. Addendum — Two-earner lines in the Shibnagar"
          " variant (Unit KD, Queue 29)" in report,
          "report §17: the addendum exists")
    check("10,000 − 72 = 9,928" in report
          and "30,000 − 8,623 = 21,377" in report,
          "report §17: the mixed bridge figures are quoted")
    check("10,000 − 1,231 = 8,769" in report
          and "10,000 − 56 = 9,944" in report,
          "report §17: the same-tier and renting bridge"
          " figures are quoted")
    check("90 two-earner rows" in report,
          "report §17: the 90-row comparison is recorded")
    check("the pinned md5 does not move" in report,
          "report §17: the md5 standing still is recorded")

    # 4. GDD-03 §2 records the KD update.
    check("Unit KD · Queue 29" in gdd03,
          "GDD-03 §2: the KD update is recorded")
    check("10,000 − 72 = 9,928" in gdd03,
          "GDD-03 §2: a Shibnagar two-earner figure is quoted")

    # 5. Tests pin the KD identity and the wiring.
    check("test_two_earner_rows_are_identical_on_shibnagar"
          "_rents" in regress,
          "tests: the identity test exists")
    check("test_shibnagar_bridge_check_prints_two_earner"
          "_lines" in regress,
          "tests: the printed-lines test exists")
    check("test_shibnagar_two_earner_lines_match_district1"
          in regress,
          "tests: the D1-match test exists")

    # 6. Scope: only the KD files changed for this unit.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 29 KD:",
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
                    "tools/verify_queue29_kd.py"},
          "scope: only the five KD files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
