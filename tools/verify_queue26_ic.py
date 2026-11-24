"""Verify Queue 26 Unit IC — Second Earner at Other Tiers
(HD follow-up).

Checks the extension against its sources: tools/economy_sim.py
(simulate() takes second_earner_tier with a mixed second
earner — a mid-tier taxi driver (23,000) or an entry civil
engineer (22,000), each at the tier the source data gives;
the measured tier stays the default),
tools/sim/tests/test_no_regression.py (the pinned md5 moves to
the IC baseline, the IB md5 kept as history),
docs/ECONOMY-SIM-REPORT-V7.md §12 (the addendum, with verbatim
output matching the tool), and docs/GDD-03-ECONOMY-AND-
PROFESSIONS.md §2 (the IC update).
Prints one line per check and a summary; exits 0 only when every
check passes.
Run from the repo root: python3 tools/verify_queue26_ic.py
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

    # 1. The tier wages come from the source data — nothing
    # invented.
    prices = econ.load("prices.json")
    wages = {x["profession_id"]: x
             for x in prices["wages_monthly"]}
    check(wages["taxi_driver"]["mid"] == 23000,
          "data: mid-tier taxi driver earns 23000")
    check(wages["civil_engineer"]["entry"] == 22000,
          "data: entry civil engineer earns 22000")
    w = next(x for x in prices["wages_monthly"]
             if x["profession_id"] == "construction_worker")

    # 2. The measured month-1 minbal per position, both
    # other-tier pairings.
    for tier in ("entry", "mid", "senior"):
        for pos in (econ.STORM_EARLY_DAYS, econ.STORM_MID_DAYS,
                    econ.STORM_LATE_DAYS,
                    econ.STORM_MEASURED_DAYS):
            row = econ.simulate(
                prices, w, tier, storm_days=pos,
                second_earner="taxi_driver",
                second_earner_tier="mid")
            if row["min_balance"] != 0 or row["end_balance"] \
                    != row["net"]:
                check(False,
                      f"tool: mid-tier taxi-second {tier}/{pos}"
                      " dips nothing and ends at net")
                break
        else:
            continue
        break
    else:
        check(True, "tool: mid-tier taxi-second dips nothing at"
              " every tier and position, and ends at net")
    for tier, net in (("entry", 16150), ("mid", 19394),
                      ("senior", 22851)):
        row = econ.simulate(
            prices, w, tier, storm_days=econ.STORM_MEASURED_DAYS,
            second_earner="taxi_driver", second_earner_tier="mid")
        check(row["net"] == net,
              f"tool: mid-tier taxi-second {tier} net is {net}",
              str(row["net"]))
    ce_measured = {t: econ.simulate(
        prices, w, t, storm_days=econ.STORM_MEASURED_DAYS,
        second_earner="civil_engineer",
        second_earner_tier="entry")["min_balance"]
        for t in ("entry", "mid", "senior")}
    check(ce_measured == {"entry": -3210, "mid": -350,
                          "senior": -31},
          "tool: entry civil-engineer-second measured dips"
          " -3210/-350/-31",
          str(ce_measured))
    check(econ.simulate(prices, w, "entry",
                        storm_days=econ.STORM_EARLY_DAYS,
                        second_earner="civil_engineer",
                        second_earner_tier="entry")
          ["min_balance"] == -3210,
          "tool: entry civil-engineer-second early is -3210")
    check(econ.simulate(prices, w, "entry",
                        storm_days=econ.STORM_LATE_DAYS,
                        second_earner="civil_engineer",
                        second_earner_tier="entry")
          ["min_balance"] == -2910,
          "tool: entry civil-engineer-second late is shallower"
          " (-2910)")
    check(econ.simulate(prices, w, "entry",
                        storm_days=econ.STORM_MEASURED_DAYS,
                        second_earner="civil_engineer",
                        second_earner_tier="entry")["net"] == 18350,
          "tool: entry civil-engineer-second entry net is 18350")

    # 3. The tier is a sourced wage, not an invented one: the
    # deltas against the measured tier are exactly the wage,
    # tax and uplift deltas.
    taxi_mid = econ.simulate(
        prices, w, "entry", storm_days=econ.STORM_MEASURED_DAYS,
        second_earner="taxi_driver", second_earner_tier="mid")
    taxi_entry = econ.simulate(
        prices, w, "entry", storm_days=econ.STORM_MEASURED_DAYS,
        second_earner="taxi_driver")
    check(taxi_mid["gross"] - taxi_entry["gross"] == 9000,
          "tool: mid-tier taxi gross is +9000 over entry")
    check(taxi_mid["tax"] - taxi_entry["tax"] == 400,
          "tool: mid-tier taxi tax is +400 over entry")
    check(taxi_mid["costs_total"] - taxi_entry["costs_total"]
          == 3150,
          "tool: mid-tier taxi costs are +3150 (uplift) over"
          " entry")
    ce_entry = econ.simulate(
        prices, w, "entry", storm_days=econ.STORM_MEASURED_DAYS,
        second_earner="civil_engineer",
        second_earner_tier="entry")
    ce_mid = econ.simulate(
        prices, w, "entry", storm_days=econ.STORM_MEASURED_DAYS,
        second_earner="civil_engineer")
    check(ce_mid["gross"] - ce_entry["gross"] == 16000,
          "tool: measured-tier civil-engineer gross is +16000"
          " over entry")
    check(ce_mid["tax"] - ce_entry["tax"] == 800,
          "tool: measured-tier civil-engineer tax is +800 over"
          " entry")
    check(ce_mid["costs_total"] - ce_entry["costs_total"] == 5600,
          "tool: measured-tier civil-engineer costs are +5600"
          " (uplift) over entry")
    check(taxi_entry["second_earner_tier"] == "entry",
          "tool: the default tier is still the measured one"
          " (taxi entry)")
    check(ce_mid["second_earner_tier"] == "mid",
          "tool: the default tier is still the measured one"
          " (civil-engineer mid)")

    # 4. The default run: md5 moves to the IC baseline; the two
    # new sections are printed; the IA bridge lines are
    # unchanged (the other-tier pairings dip less than the
    # measured-tier worst dips).
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "economy_sim.py")],
        capture_output=True, cwd=ROOT)
    check(out.returncode == 0, "tool: default run exits 0")
    text = out.stdout.decode()
    md5 = hashlib.md5(out.stdout).hexdigest()
    check(md5 == "d198a2fe0970e11aaa105bcc4bfb19f9",
          "tool: default-run md5 is the IC baseline", md5)
    check("d198a2fe0970e11aaa105bcc4bfb19f9" in regress,
          "tests: the IC md5 is pinned in test_no_regression.py")
    check("27464ea221694880a4369f805d8cd455" in regress,
          "tests: the IB md5 is kept as history")
    check("taxi-driver second earner (mid 23,000, per-fare)"
          in text,
          "tool: the mid-tier taxi section names the pairing")
    check("civil-engineer second earner (entry 22,000, monthly)"
          in text,
          "tool: the entry civil-engineer section names the"
          " pairing")
    check("construction_worker + taxi-driver    start  10000"
          " + mixed dip     -72 =    9928  OK  (worst mixed"
          " storm position)" in text,
          "tool: the IA taxi-second bridge line is unchanged")
    check("construction_worker + civil-engineer start  30000"
          " + mixed dip   -8623 =   21377  OK  (worst mixed"
          " storm position)" in text,
          "tool: the IA civil-engineer-second bridge line is"
          " unchanged")
    check("BRIDGE FAIL rows: []" in text,
          "tool: no bridge failure in any position")

    # 5. The V7 report §12: the addendum, the tables, the
    # verbatim output matching the tool.
    check("## 12. Addendum — Second earner at other tiers"
          in report,
          "report §12: the addendum exists")
    check("| entry | 0 | 0 | 0 | 0 | 0 | 16,150 | 0 | 0 |"
          " 10,700 |" in report,
          "report §12: the mid-tier taxi table's entry row")
    check("| senior | 0 | 0 | 0 | 0 | 0 | 22,851 | −72 | 0 |"
          " 17,401 |" in report,
          "report §12: the mid-tier taxi table's senior row")
    check("| entry | −3,210 | −3,210 | −2,910 | −3,210 | −3,190 |"
          " 18,350 | −8,623 | −8,623 | 27,950 |" in report,
          "report §12: the entry civil-engineer table's entry"
          " row")
    check("| senior | −1,006 | 0 | 0 | −31 | 0 | 25,051 |"
          " −2,170 | −2,170 | 34,651 |" in report,
          "report §12: the entry civil-engineer table's senior"
          " row")
    check("30,000 − 3,210 = 26,790" in report,
          "report §12: the entry civil-engineer bridge figure is"
          " quoted")
    check("the tier moves the dip more than the position does"
          in report.replace("\n", " "),
          "report §12: the finding is stated, not hidden")
    blocks = re.findall(
        r"```\n(second earner at another tier.*?)\n```", report,
        re.S)
    tool_sections = "\n\n".join(
        s for s in text.split("\n\n")
        if s.startswith("second earner at another tier"))
    check(len(blocks) == 1 and blocks[0].strip()
          == tool_sections.strip(),
          "report §12: the verbatim output matches the tool")
    check("Unit IC DONE 2026-11-24" in report,
          "report §9: the other-tiers gap is marked IC DONE")
    check("d198a2fe0970e11aaa105bcc4bfb19f9" in report,
          "report §12: the md5 is the IC baseline")

    # 6. GDD-03 §2 records the IC update.
    check("Unit IC · Queue 26" in gdd03,
          "GDD-03 §2: the IC update is recorded")
    check("−3,210 / −350 / −31" in gdd03,
          "GDD-03 §2: the entry civil-engineer dips are quoted")
    check("No tier's pay is invented" in gdd03,
          "GDD-03 §2: the sourced-tier rule is stated")

    # 7. Scope: only the IC files changed for this unit (union
    # of the working tree and the unit's own commit, found by
    # its message — see the IA script's note).
    changed = subprocess.run(
        ["git", "status", "--short"], capture_output=True,
        cwd=ROOT).stdout.decode()
    names = {ln[3:] for ln in changed.splitlines() if ln.strip()}
    own = subprocess.run(
        ["git", "log", "--format=%H", "--grep=^Queue 26 IC:",
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
                    "tools/verify_queue26_ic.py"},
          "scope: only the five IC files changed",
          str(sorted(names)))

    bad = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(bad)}/{len(CHECKS)} checks passed, "
          f"{len(bad)} failed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
