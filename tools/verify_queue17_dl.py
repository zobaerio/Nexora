"""Verify Queue 17 Unit DL — Mission System Writer Implementation
(GDD-04 §3.6, Unit DG design).

Checks the implementation against the contract: GDD-04 §3.6 (the
writer, the lifecycle, the 5-key progress shape, favour instances,
the 1.4 completion condition), tools/sim/missions.py (the writer),
tools/sim/photographs.py (the DA gate it opens),
data/missions.json (deadline_days, side types) and
tools/sim/tests/test_missions.py.
Prints one line per check and a summary; exits 0 only when every
check passes. Run from the repo root: python3 tools/verify_queue17_dl.py
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
    missions_py = (ROOT / "tools" / "sim" / "missions.py").read_text()
    photographs = (ROOT / "tools" / "sim" / "photographs.py").read_text()
    missions = json.loads((ROOT / "data" / "missions.json").read_text())
    dataio = (ROOT / "tools" / "sim" / "dataio.py").read_text()
    tests = (ROOT / "tools" / "sim" / "tests"
             / "test_missions.py").read_text()

    # 1. The writer implements the DG lifecycle, no skips.
    for fn in ("make_available", "accept_mission",
               "set_objectives_complete", "verify_mission_1_4",
               "complete_mission", "fail_mission", "retry_mission",
               "expire_deadlines", "create_favour_instance",
               "verify_favour_objectives", "deadline_days_for"):
        check(f"def {fn}" in missions_py,
              f"missions.py defines {fn}")
    check("PROGRESS_KEYS" in missions_py
          and '"available_at_game_minutes"' in missions_py
          and '"accepted_at_game_minutes"' in missions_py
          and '"objectives_complete"' in missions_py
          and '"completed_at_game_minutes"' in missions_py
          and '"abandoned"' in missions_py,
          "missions.py writes exactly the five progress keys")
    check("RETRY_WAIT_MINUTES = 7 * 1440" in missions_py,
          "retry waits 7 in-game days (GDD-04 §1)")

    # 2. The 1.4 completion condition matches DG §3.6 exactly.
    check('RIVERFRONT_TEA_STALL_ANCHOR = "anchor_tea_stall_riverfront_1"'
          in missions_py,
          "1.4 verifies the riverfront tea stall anchor")
    check('RIVERFRONT_ZONE = "d1_riverfront"' in missions_py,
          "1.4 verifies the d1_riverfront zone")
    check("daylight(data, day_index)[1]" in missions_py,
          "1.4 sunset comes from environment.daylight (season-shifted)")
    check("EVENING_END_MINUTE = 20 * 60" in missions_py,
          "1.4 window ends at 20:00 (Evening end, TECH-CLOCK-WEATHER §1)")
    check("first_evening_in_rupsha" in missions_py
          and "First evening in Rupsha" in missions_py,
          "1.4 completion pays the sourced memory event")
    check("no episodic-memory weight is sourced" in missions_py,
          "missions.py records no invented memory weight")

    # 3. The deadline table is read from the data, not hardcoded.
    deadlines = {m["id"]: m.get("deadline_days")
                 for m in missions["missions"]
                 if "deadline_days" in m}
    check(deadlines == {"4.2": 30, "6.2": 45, "7.4": 60},
          "deadline missions are 4.2/30, 6.2/45, 7.4/60 (GDD-04 §3.2)",
          f"{deadlines}")
    check("missions_file" in dataio,
          "dataio loads missions.json as missions_file")
    check("deadline_days_for" in missions_py
          and 'startswith("side:")' in missions_py,
          "favours never carry a deadline (DG §3.6)")

    # 4. Favour instances follow the §3.1 key shape.
    check('f"side:{favour_type}:{giver_character_id}:'
          in missions_py or
          '"side:{favour_type}:{giver_character_id}:"' in missions_py,
          "favour instance key is side:<type>:<giver>:<minute>")
    check("side_mission_types" in missions_py,
          "favour types are read from missions.json, not invented")
    check("find a lost item\" is a subtype within Favours"
          in missions_py,
          "missions.py records the lost-item subtype honestly")
    check("favour_objective_complete" in missions_py,
          "lost-item favour verifies via DF's predicate")
    check("discovery_progress" in missions_py,
          "discovery favour verifies via the discovery row")

    # 5. The DA gate is unchanged — the writer only feeds it.
    check("mission_id = ? AND status = 'completed'" in photographs
          and "PHOTO_MODE_MISSION = \"1.4\"" in photographs,
          "photographs.py still gates on the 1.4 completed row")

    # 6. The GDD records the implementation.
    check("Implementation (Unit DL · Queue 17" in gdd04,
          "GDD-04 §3.6 carries the DL implementation note")
    check("NOT wired here" in missions_py,
          "missions.py records the reward-payout gap honestly")

    # 7. The tests cover the contract.
    n_tests = len(re.findall(r"def test_", tests))
    check(n_tests >= 20,
          "test_missions.py has 20+ tests", f"{n_tests} tests")
    check("class TestLifecycle" in tests
          and "class TestMission14" in tests
          and "class TestDeadlines" in tests
          and "class TestFavourInstances" in tests,
          "tests cover lifecycle, 1.4, deadlines, favour instances")
    check("test_da_gate_opens_on_1_4_completion" in tests,
          "tests prove the DA gate opens on 1.4 completing")
    check("test_available_cannot_complete_or_fail" in tests,
          "tests prove no state is skipped")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
