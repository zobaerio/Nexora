"""Verify Queue 11 Unit BH — mission deadlines (AV gap G10).

Checks the deadline field against the sources it must resolve to:
GDD-04 §1/§3.1/§4, GDD-15 §4/§12/§13, data/missions.json,
data/schema.sql (unchanged).
Prints one line per check and a summary; exits 0 only when every check
passes. Run from the repo root: python3 tools/verify_queue11_bh.py
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


def load_json(name):
    return json.loads((ROOT / "data" / name).read_text())


def main():
    gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md").read_text()
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    missions = load_json("missions.json")

    # 1. GDD-04 §3.2 exists, headed Unit BH, Queue 11.
    m32 = re.search(r"### 3\.2 Mission Deadlines \(Unit BH · Queue 11",
                    gdd04)
    check(m32 is not None, "GDD-04 §3.2 exists, headed Unit BH, Queue 11")

    # 2. GDD-15 §19 exists, headed Unit BH, Queue 11.
    m19 = re.search(r"## 19\. Mission Deadlines — Dialogue Note "
                    r"\(AV gap G10 — resolved\)\n\n\*\*Unit BH · Queue 11",
                    gdd15)
    check(m19 is not None, "GDD-15 §19 exists, headed Unit BH, Queue 11")

    # 3. §12.8 G10 is marked resolved by BH.
    check("**Resolved by Queue 11, Unit BH (GDD-04 §3.2 + GDD-15 §19):**"
          in gdd15, "§12.8 G10 marked resolved by Queue 11 Unit BH")

    # 4. No mission in missions.json carries a deadline today.
    ms = missions["missions"]
    check(all("deadline_days" not in m for m in ms),
          "no mission in missions.json carries deadline_days",
          f"missions={len(ms)}")

    # 5. The mission set is the 32 main missions, ids 1.1–8.4.
    ids = {m["id"] for m in ms}
    check(len(ms) == 32 and "1.1" in ids and "8.4" in ids,
          "missions.json holds the 32 main missions 1.1–8.4")

    # 6. The field shape: optional integer, minimum 1, absent = no deadline.
    sec32 = gdd04.split("### 3.2 Mission Deadlines")[1].split(
        "\n## 4. Free-Roam Rules")[0]
    check("`deadline_days`" in sec32 and "optional integer, minimum 1"
          in sec32, "field is optional integer, minimum 1")
    check("Absent means the mission has no deadline" in sec32,
          "absent field means no deadline")

    # 7. The clock counts from availability (available_at_game_minutes).
    check("`available_at_game_minutes`" in sec32,
          "fifth progress key available_at_game_minutes defined")
    check("available_at_game_minutes + deadline_days × 1440" in sec32,
          "remaining formula stated (available_at + days x 1440 - now)")

    # 8. §13.3's four keys are unchanged by the extension.
    sec13 = gdd15.split("### 13.3")[1].split("### 13.4")[0]
    for key in ("accepted_at_game_minutes", "objectives_complete",
                "completed_at_game_minutes", "abandoned"):
        check(key in sec13, f"§13.3 still defines {key}")
    check("fifth" in sec32.lower() and "§13.3" in sec32,
          "§3.2 names the extension of §13.3's four keys")

    # 9. The lead window is the sourced "within 3 days" = 4320 minutes.
    check("within 3 days" in gdd15.split("\n## 4. Topics")[1].split(
        "\n## 5. ")[0], "GDD-15 §4 sources 'within 3 days'")
    check("4320" in sec32 and "4320" in gdd15.split("\n## 19. ")[1],
          "lead window is 4320 game minutes (3 days) in both docs")
    check("inclusive at 3 days exactly and exclusive at 0" in sec32,
          "window bounds stated (inclusive at 4320, exclusive at 0)")

    # 10. The lead trigger is checked in §12.2 step 3 order.
    sec19 = gdd15.split("\n## 19. ")[1]
    check("§12.2 step 3" in sec19,
          "§19 places the trigger in §12.2 step 3 order")

    # 11. Accepting does not reset the clock.
    check("Accepting the mission does **not** reset the clock" in sec32,
          "acceptance does not reset the deadline clock")

    # 12. Expiry: the mission system sets failed; dialogue never writes it.
    check("sets the row to `failed`" in sec32,
          "expiry sets status failed via the mission system")
    check("Dialogue never writes `failed`" in sec32
          or "dialogue never writes `failed`" in gdd15.split(
              "### 13.4")[1].split("### 13.5")[0],
          "dialogue never writes failed (§13.4)")

    # 13. Failed missions have no dialogue state (§13.2).
    sec132 = gdd15.split("### 13.2")[1].split("### 13.3")[0]
    check("Failed missions have **no dialogue state**" in sec132,
          "failed missions have no dialogue state (§13.2)")

    # 14. Retry after 7 in-game days (GDD-04 §1), fresh available_at.
    check("retried after 7 in-game days" in gdd04.split("## 1.")[1].split(
        "## 2.")[0], "GDD-04 §1 sources the 7-day retry")
    check("fresh** `available_at_game_minutes`" in sec32,
          "retry returns a fresh available_at (new deadline window)")

    # 15. Favours never carry a deadline (§3.1 stands).
    sec31 = gdd04.split("### 3.1 Favour Generation Contract")[1].split(
        "### 3.2")[0]
    check("no deadline and no expiry" in sec31.lower()
          or "No deadline" in sec31 or "no deadline" in sec31,
          "§3.1 favours have no deadline")
    check("Favours never carry a deadline" in sec32
          or "Favours never do" in sec32,
          "§3.2 restates favours never carry a deadline")

    # 16. In-game deadlines are sourced (GDD-04 §4 rule 2).
    sec4 = gdd04.split("\n## 4. Free-Roam Rules")[1].split("\n## 5. ")[0]
    check("In-game deadlines exist" in sec4,
          "GDD-04 §4 rule 2 sources in-game deadlines")

    # 17. Values are Phase 6 authoring work; none invented here.
    check("Phase 6 authoring work" in sec32,
          "deadline values are Phase 6 authoring work")

    # 18. Gap G10 resolution statements present in both docs.
    check("**Gap G10 is resolved by this section**" in sec32,
          "§3.2 states gap G10 resolved")
    check("**Gap G10 is resolved by this note together with GDD-04 §3.2**"
          in sec19, "§19 states gap G10 resolved")

    # 19. The deadline adds no dialogue state (§19).
    check("adds no dialogue state" in sec19,
          "§19 states the deadline adds no dialogue state")

    # 20. No schema.sql change by this unit (design only).
    diff = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "--name-only"],
        capture_output=True, text=True).stdout.splitlines()
    check("data/schema.sql" not in diff,
          "data/schema.sql unchanged (design only)",
          f"changed={diff}")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed, "
          f"{len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
