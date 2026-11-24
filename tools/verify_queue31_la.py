"""Verify Queue 31 Unit LA — Single-Earner Storm Line Across
Tiers (KE follow-up).

Checks the wiring against its sources: tools/economy_sim.py
(the single-earner storm line in the District 1 bridge check
and in print_shibnagar_variant's bridge check now sweeps the
construction worker's tiers as well as the storm positions,
like the two-earner lines — the minimum across tiers and
positions, against the same 5,000 start),
tools/sim/tests/test_no_regression.py (new tests pin the
per-tier worst dips, the printed line in both runs, and the
re-pinned default-run md5 — the KC md5 is kept as history),
docs/ECONOMY-SIM-REPORT-V7.md §20 (the prose matches the
tool output, including the per-tier table and the md5 move),
and docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the LA
update, including the correction of the FB prose figure).
Re-runs the single-earner storm rows for every tier on both
rents live and asserts the figures.
Prints one line per check and a summary; exits 0 only when
every check passes.
Run from the repo root: python3 tools/verify_queue31_la.py
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CHECKS = []

LA_MD5 = "2b9d24f9663f88ad0d13be1f5e86c40c"
KC_MD5 = "f6cec5a23109c4e7f9aeff3f7361e89d"

STORM_LINE = ("construction_worker    start   5000 + storm dip"
              "    -726 =    4274  OK  (worst storm position,"
              " all tiers)")


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

    # 1. The figures hold: per-tier worst dips, District 1 and
    # Shibnagar — the early position is worst at every tier.
    prices = econ.load("prices.json")
    rents, _stock = econ.load_shibnagar_rents(prices)
    check(rents[1] == 2500,
          "tool: Shibnagar tier-1 rent is 2500", str(rents[1]))
    w = next(w for w in prices["wages_monthly"]
             if w["profession_id"] == "construction_worker")
    override = rents[1]
    positions = (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                 econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS)
    expected = (("entry", -500), ("mid", -595), ("senior", -726))
    checked = 0
    identical = True
    for tier, worst in expected:
        dips = [econ.simulate(prices, w, tier, storm_days=pos)
                ["min_balance"] for pos in positions]
        if min(dips) != worst:
            identical = False
        early = econ.simulate(prices, w, tier,
                              storm_days=econ.STORM_EARLY_DAYS)
        if early["min_balance"] != worst:
            identical = False
        sh_dips = [econ.simulate(prices, w, tier, storm_days=pos,
                                 rent_override=override)
                   ["min_balance"] for pos in positions]
        if min(sh_dips) != worst:
            identical = False
        checked += 1
    check(checked == 3, "tool: 3 tiers compared", str(checked))
    check(identical,
          "tool: per-tier worst dips are entry -500, mid -595,"
          " senior -726, identical on Shibnagar rents")
    worst = min(econ.simulate(prices, w, tier, storm_days=pos)
                ["min_balance"]
                for tier in ("entry", "mid", "senior")
                for pos in positions)
    check(worst == -726,
          "tool: worst cross-tier storm dip is -726", str(worst))
    check(5000 + worst == 4274,
          "tool: the storm bridge is 5000 - 726 = 4274")

    # 2. The wiring: both runs print the swept line, with the
    # same figures; the default-run md5 moves to the LA pin.
    d1 = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py")],
        capture_output=True, cwd=ROOT)
    check(d1.returncode == 0, "tool: default run exits 0")
    d1_text = d1.stdout.decode()
    check(STORM_LINE in d1_text,
          "tool: the D1 check prints the swept storm line")
    check("BRIDGE FAIL rows: []" in d1_text,
          "tool: no D1 bridge failure")
    md5 = hashlib.md5(d1.stdout).hexdigest()
    pinned = re.search(
        r'ECONOMY_SIM_BASELINE_MD5 = "([0-9a-f]{32})"',
        regress).group(1)
    check(md5 == pinned,
          "tool: default-run md5 equals the pinned baseline",
          md5)
    check(pinned == LA_MD5,
          "tool: the pinned md5 moved to the LA baseline",
          pinned)
    check(KC_MD5 in regress,
          "tests: the KC md5 is kept as history")
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py"),
         "--shibnagar"],
        capture_output=True, cwd=ROOT)
    check(out.returncode == 0, "tool: --shibnagar run exits 0")
    sh_text = out.stdout.decode()
    variant = sh_text.split(
        "shibnagar first-month bridge check")[1]
    check(STORM_LINE in variant,
          "tool: the Shibnagar check prints the swept storm"
          " line")
    check("shibnagar BRIDGE FAIL rows: []" in sh_text,
          "tool: no Shibnagar bridge failure")
    d1_line = next(ln for ln in d1_text.splitlines()
                   if "storm dip" in ln)
    sh_line = next(ln for ln in variant.splitlines()
                   if "storm dip" in ln)
    check(sh_line == d1_line,
          "tool: the Shibnagar storm line equals the D1 line")
    check("for tier in (\"entry\", \"mid\", \"senior\")" in sim_src,
          "tool: the storm sweep covers all tiers")
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

    # 3. The V7 report §20: prose matches the tool output.
    check("## 20. Addendum — Single-earner storm line across"
          " tiers (Unit LA, Queue 31)" in report,
          "report §20: the addendum exists")
    check("5,000 − 726 = 4,274" in report,
          "report §20: the storm bridge figure is quoted")
    check("senior | −726" in report,
          "report §20: the per-tier table is quoted")
    check(LA_MD5 in report.split("## 20.")[1],
          "report §20: the md5 move is recorded")
    check("Queue 32 Unit" in report.split("## 20.")[1]
          and "MA" in report.split("## 20.")[1],
          "report §20: the renting-row open note is recorded")

    # 4. GDD-03 §2 records the LA update.
    check("Unit LA · Queue 31" in gdd03,
          "GDD-03 §2: the LA update is recorded")
    check("5,000 − 726 = 4,274" in gdd03,
          "GDD-03 §2: the storm bridge figure is quoted")
    check("leaves 4,274" in gdd03,
          "GDD-03 §2: the FB prose correction is recorded")

    # 5. Tests pin the LA sweep and the wiring.
    check("test_storm_line_sweeps_all_tiers" in regress,
          "tests: the D1 sweep test exists")
    check("test_shibnagar_storm_line_sweeps_all_tiers"
          in regress,
          "tests: the Shibnagar sweep test exists")
    check("worst storm position, all tiers" in regress,
          "tests: the printed-line tests use the new label")

    # 6. Scope: only the LA files changed for this unit.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 31 LA:",
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
                    "tools/verify_queue31_la.py"},
          "scope: only the five LA files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
