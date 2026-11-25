"""Verify Queue 36 Unit ME — Renting Senior-Tier Taxi Second
Earner: Belongs in the Tool? (MD follow-up).

Checks the decision against its sources: tools/economy_sim.py
(the combination stays computable but the KC second-earner
surge table keeps its four pairings and neither bridge check
wires a line for it — the ME comment states the decision at
the pairings list), tools/sim/tests/test_no_regression.py
(new tests pin the allowed-but-unprinted boundary — the
combination computes, the rental rule holds, the dip is 0
everywhere, and no senior renting row or line is printed in
either run), docs/ECONOMY-SIM-REPORT-V7.md §25 (the decision
+ its three reasons, and the md5 notes — the pinned default-run
md5 does NOT move: the MC baseline stands; the --shibnagar md5
does NOT move either) and §24 (the open note is closed), and
docs/GDD-03-ECONOMY-AND-PROFESSIONS.md §2 (the ME update).
Re-runs the pairing live and asserts the decision-support
properties.
Prints one line per check and a summary; exits 0 only when
every check passes.
Run from the repo root: python3 tools/verify_queue36_me.py
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CHECKS = []

MC_MD5 = "a818a3273cdad108c4d8d4ae198b5b44"
SH_MD5 = "762a2b6395a1c83fc86f2b5f9c1839bc"


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

    # 1. The decision-support facts, measured live: the
    # combination computes at every first-earner tier and
    # storm position; the net is exactly 5,200 below the
    # owning senior driver (the flat rental, not a household
    # figure); every trajectory ends exactly at net; the
    # early dip is 0 everywhere — the row would add no
    # finding.
    prices = econ.load("prices.json")
    bands = {w["profession_id"]: w
             for w in prices["wages_monthly"]}
    w = bands["construction_worker"]
    positions = (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                 econ.STORM_LATE_DAYS, econ.STORM_MEASURED_DAYS)
    checked = 0
    allowed = True
    rental_rule = True
    ends_at_net = True
    no_dip = True
    for tier in ("entry", "mid", "senior"):
        for pos in positions:
            try:
                r = econ.simulate(
                    prices, w, tier, storm_days=pos,
                    second_earner="taxi_driver",
                    second_earner_tier="senior",
                    second_earner_renting_cab=True)
                own = econ.simulate(
                    prices, w, tier, storm_days=pos,
                    second_earner="taxi_driver",
                    second_earner_tier="senior")
            except ValueError:
                allowed = False
                continue
            checked += 1
            if r["net"] != own["net"] - 5200:
                rental_rule = False
            if r["end_balance"] != r["net"]:
                ends_at_net = False
            if r["min_balance"] != 0:
                no_dip = False
    check(checked == 12, "tool: 12 senior renting rows computed",
          str(checked))
    check(allowed,
          "tool: the senior renting combination is allowed"
          " (no refusal raised)")
    check(rental_rule,
          "tool: the net is exactly 5,200 below the owning"
          " senior driver at every tier and position")
    check(ends_at_net,
          "tool: every senior renting trajectory ends exactly"
          " at net")
    check(no_dip,
          "tool: the early dip is 0 at every tier and position"
          " (the row would add no finding)")
    check("Queue 36 / Unit ME: DECIDED" in sim_src
          and "allowed\n            # but unprinted" in sim_src,
          "tool: the ME decision is commented at the surge"
          " table pairings list")
    check("Queue 37 Unit MF" in sim_src,
          "tool: the comment names the reopen condition")

    # 2. The wiring: neither run prints the pairing, both
    # runs are byte-identical to the MD baselines, and no
    # bridge check fails.
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
    check(pinned == MC_MD5,
          "tool: the pinned md5 stays the MC baseline",
          pinned)
    check("BRIDGE FAIL rows: []" in d1_text,
          "tool: no D1 bridge failure")
    check("senior, renting" not in d1_text,
          "tool: the default run prints no senior renting row")
    section = d1_text.split(
        "taxi-driver second earner weather-surge month")[1]
    for pairing in ("taxi-driver (entry, owning)",
                    "taxi-driver (mid, owning)",
                    "taxi-driver (mid, renting)",
                    "taxi-driver (entry, renting)"):
        check(pairing in section,
              "tool: the surge table keeps a pairing", pairing)
    check("construction_worker + taxi-driver (mid, renting)"
          in d1_text,
          "tool: the D1 check keeps the KA renting mid-tier"
          " line and no other renting second-earner line")
    bridge = d1_text.split("first-month bridge check")[1].split(
        "BRIDGE FAIL rows:")[0]
    rent_lines = [ln for ln in bridge.splitlines()
                  if "renting" in ln]
    check(len(rent_lines) == 2
          and all("taxi-driver (mid, renting)" in ln
                  or "taxi_driver (renting cab)" in ln
                  for ln in rent_lines),
          "tool: the D1 bridge check has only the KA renting"
          " line and the single-earner renting line",
          str(len(rent_lines)))
    sh = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py"),
         "--shibnagar"],
        capture_output=True, cwd=ROOT)
    check(sh.returncode == 0, "tool: --shibnagar run exits 0")
    sh_text = sh.stdout.decode()
    sh_md5 = hashlib.md5(sh.stdout).hexdigest()
    sh2 = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py"),
         "--shibnagar"],
        capture_output=True, cwd=ROOT)
    check(hashlib.md5(sh2.stdout).hexdigest() == sh_md5,
          "tool: two --shibnagar runs are byte-identical",
          sh_md5)
    check(sh_md5 == SH_MD5,
          "tool: --shibnagar md5 matches the §25 record",
          sh_md5)
    check("shibnagar BRIDGE FAIL rows: []" in sh_text,
          "tool: no Shibnagar bridge failure")
    check("senior, renting" not in sh_text,
          "tool: the --shibnagar run prints no senior renting"
          " row")
    check("construction_worker + taxi-driver (mid, renting)"
          in sh_text,
          "tool: the Shibnagar check keeps the KA renting"
          " mid-tier line and no other renting second-earner"
          " line")
    sh_bridge = sh_text.split(
        "shibnagar first-month bridge check")[1].split(
        "shibnagar BRIDGE FAIL rows:")[0]
    sh_rent_lines = [ln for ln in sh_bridge.splitlines()
                     if "renting" in ln]
    check(len(sh_rent_lines) == 2
          and all("taxi-driver (mid, renting)" in ln
                  or "taxi_driver (renting cab)" in ln
                  for ln in sh_rent_lines),
          "tool: the Shibnagar bridge check has only the KA"
          " renting line and the single-earner renting line",
          str(len(sh_rent_lines)))

    # 3. The V7 report §25: the decision + its reasons.
    check("## 25. Addendum — Renting senior-tier taxi second"
          " earner: belongs in the tool? (Unit ME, Queue 36)"
          in report,
          "report §25: the addendum exists")
    s25 = report.split("## 25.")[1]
    check("DECIDED: keep allowed-but-unmeasured" in s25,
          "report §25: the decision is stated")
    check("§12 standing rule" in s25
          and "would dangle" in s25
          and "would add no finding" in s25,
          "report §25: the three reasons are recorded")
    check("does NOT move" in s25 and MC_MD5 in s25
          and SH_MD5 in s25,
          "report §25: both md5 notes are recorded")
    check("Queue 37" in s25 and "Unit MF" in s25,
          "report §25: the reopen condition names Queue 37")
    check("(Closed\n2026-11-25 by Queue 36 Unit ME"
          in report.split("## 24.")[1].split("## 25.")[0],
          "report §24: the surge-section open note is closed")

    # 4. GDD-03 §2 records the ME update.
    check("Unit ME · Queue 36" in gdd03,
          "GDD-03 §2: the ME update is recorded")
    check("allowed but unmeasured" in gdd03
          and "10,000 + 0 = 10,000" in gdd03,
          "GDD-03 §2: the decision and its finding are quoted")
    check(MC_MD5 in gdd03,
          "GDD-03 §2: the md5 note is recorded")

    # 5. Tests pin the ME boundary.
    for name in ("test_senior_renting_second_earner_is_allowed",
                 "test_senior_renting_second_earner_is_not"
                 "_printed"):
        check(name in regress,
              "tests: the ME test exists", name)

    # 6. Scope: only the ME files changed for this unit.
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 36 ME:",
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
                    "tools/verify_queue36_me.py"},
          "scope: only the five ME files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
