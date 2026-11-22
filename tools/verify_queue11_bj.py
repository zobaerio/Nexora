"""Verify Queue 11 Unit BJ — runbook §11 retention, anchor, automation
(AW open decisions OD-2 + OD-3 + OD-4).

Checks the section against the sources it must resolve to:
docs/TECH-CHECKPOINT-RUNBOOK.md §1.2/§4/§6/§7,
TECH-PERSISTENT-WORLD Appendix A §A.3, tools/sim/scheduler.py,
docs/SESSION-10-REPORT.md (endurance size).
Prints one line per check and a summary; exits 0 only when every check
passes. Run from the repo root: python3 tools/verify_queue11_bj.py
"""
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


def main():
    runbook = (ROOT / "docs" / "TECH-CHECKPOINT-RUNBOOK.md").read_text()
    tpw = (ROOT / "docs" / "TECH-PERSISTENT-WORLD.md").read_text()
    sched = (ROOT / "tools" / "sim" / "scheduler.py").read_text()
    s10 = (ROOT / "docs" / "SESSION-10-REPORT.md").read_text()

    # 1. §11 exists, headed Unit BJ, Queue 11, resolving OD-2 + OD-3 + OD-4.
    m11 = re.search(r"## 11\. Checkpoint Retention, Anchor & Fallback "
                    r"Automation \(AW open decisions OD-2 \+ OD-3 \+ "
                    r"OD-4 — resolved\)\n\n\*\*Unit BJ · Queue 11",
                    runbook)
    check(m11 is not None,
          "runbook §11 exists, headed Unit BJ, Queue 11 (OD-2/3/4)")

    # 2. §7 OD-2, OD-3, OD-4 rows say Resolved, pointing at §11.
    sec7 = runbook.split("\n## 7. ")[1].split("\n## 8. ")[0]
    for od, sub in (("OD-2", "§11.1"), ("OD-3", "§11.2"),
                    ("OD-4", "§11.3")):
        check(f"**Resolved — {sub} (Unit BJ, Queue 11):**" in sec7,
              f"§7 {od} row resolved, pointing at {sub}")

    sec11 = runbook.split("\n## 11. ")[1].split("\n## 12. ")[0]

    # 3. Retention: newest 10 per world; 11th deletes the oldest.
    check("keep the newest 10 named checkpoints per world" in sec11,
          "retention keeps the newest 10 named checkpoints per world")
    check("on taking the 11th, delete the oldest" in sec11,
          "11th checkpoint deletes the oldest")

    # 4. Every named checkpoint counts (weekly, shutdown, on-demand).
    check("weekly, clean-shutdown, and on-demand alike" in sec11,
          "all three named-checkpoint kinds count toward the 10")
    check("Genesis resets the count to 0" in sec11,
          "genesis resets the retention count")

    # 5. Deletion procedure: files first, then the save_slots row.
    check("Delete the payload file" in sec11
          and "Delete the `save_slots` row" in sec11,
          "deletion removes payload + manifest, then the save_slots row")

    # 6. ON DELETE CASCADE removes the digest row with its snapshot.
    check("ON DELETE CASCADE" in tpw.split("## A.3")[1].split("## A.4")[0],
          "Appendix A §A.3 defines ON DELETE CASCADE on snapshot_metadata")
    check("ON DELETE CASCADE" in sec11,
          "§11.1 cites the cascade for the digest row")

    # 7. §6 rule 4 is respected (digest rows go with the snapshot).
    check("§6 rule 4" in sec11, "§11.1 cites §6 rule 4")
    check("not orphaned" in sec11, "deletion leaves no orphaned digest row")

    # 8. Audit rows outlive the snapshots they describe.
    check("never deletes the `audits` rows" in sec11,
          "retention never deletes audit rows")

    # 9. Rationale: 10 weeks ≈ 2.5 months; disk bound from the Session 10 size.
    check("10 in-game weeks" in sec11 and "2.5 in-game months" in sec11,
          "retention rationale states 10 weeks ≈ 2.5 months")
    check("213.6 MB" in s10, "Session 10 endurance world is 213.6 MB")
    check("213.6 MB" in sec11, "§11.1 cites the 213.6 MB world size")

    # 10. Anchor: Monday 00:00, game_minutes % 10080 == 0.
    check("Monday 00:00" in sec11,
          "weekly anchor is Monday 00:00 (day boundary ending Sunday)")
    check("game_minutes % 10080 == 0" in sec11,
          "anchor check is game_minutes % 10080 == 0")

    # 11. Day 1 is a Monday; Friday = 4 (scheduler).
    check("Day 1 (index 0) is a Monday" in sched,
          "Day 1 is a Monday (scheduler)")
    check("Friday = 4" in sched, "Friday is weekday 4 (scheduler)")

    # 12. Weekend-variant rationale: Friday/Saturday bends exist.
    check("_apply_friday" in sched and "_apply_saturday" in sched,
          "scheduler has Friday and Saturday variant bends")
    check("weekend-variant days" in sec11,
          "§11.2 rationale avoids the weekend-variant days")

    # 13. Automation split: refuse automatic, fallback confirmed, genesis
    # confirmed by name.
    check("Refuse the snapshot" in sec11 and "**Automatic**" in sec11,
          "refusal is automatic (§11.3)")
    check("Explicit operator confirmation, per step" in sec11,
          "each fallback step needs explicit confirmation")
    check("typing the world name" in sec11,
          "genesis needs confirmation typing the world name")

    # 14. The operator may stop the walk and leave the server down.
    check("may stop the walk at any step" in sec11,
          "operator may stop the fallback walk and leave the server down")

    # 15. A newer-version refusal follows the same confirmation rule.
    check("version_refusal" in runbook.split("\n## 10. ")[1].split(
        "\n## 11. ")[0], "§10.3 records version refusals distinctly")
    check("newer-version refusal" in sec11.lower()
          or "A newer-version refusal" in sec11,
          "§11.3 covers newer-version refusals the same way")

    # 16. §1.2 anchor line no longer says "not fixed".
    sec12 = runbook.split("### 1.2 The schedule")[1].split("### 1.3")[0]
    check("not fixed by any source" not in sec12,
          "§1.2 no longer says the anchor is unfixed")
    check("§11.2" in sec12, "§1.2 points at §11.2")

    # 17. §11 states the numbers are this unit's decision, revisable.
    check("Each number below is this unit's decision" in sec11,
          "§11 labels its numbers as this unit's decision")
    check("revisable as config" in sec11,
          "numbers are revisable as config, not redesign")

    # 18. OD-2/3/4 resolution statement present.
    check("**OD-2, OD-3, and OD-4 are resolved by this section**" in sec11,
          "§11 states OD-2/3/4 resolved")

    # 19. The §1.2 pointer error is corrected in §11.
    check("Correction to §1.2" in sec11
          and "That pointer is wrong twice over" in sec11,
          "§11 records the §1.2 pointer correction")

    # 20. No server code or schema change by this unit (design only).
    diff = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "--name-only"],
        capture_output=True, text=True).stdout.splitlines()
    check("data/schema.sql" not in diff
          and not any(p.startswith("tools/sim/") for p in diff),
          "no schema/sim change (design only)",
          f"changed={diff}")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed, "
          f"{len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
