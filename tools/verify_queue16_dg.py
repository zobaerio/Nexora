"""Verify Queue 16 Unit DG — Mission Progress Write Contract (GDD-04
§3.6; DA follow-up).

Checks the contract against the sources it builds on: GDD-04 §2
(mission 1.4), §3.1/§3.2/§3.5, GDD-15 §13 (the mission-state
mapping), data/schema.sql (mission_progress), data/missions.json
(1.4), data/district1-blockout.json (the riverfront tea stall),
data/environment-config.json + TECH-SEASONS/TECH-CLOCK-WEATHER
(the sunset window), and tools/sim/photographs.py (the DA gate).
Design only — no sim code changes. Prints one line per check and
a summary; exits 0 only when every check passes. Run from the repo
root: python3 tools/verify_queue16_dg.py
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
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    schema = (ROOT / "data" / "schema.sql").read_text()
    missions = json.loads((ROOT / "data" / "missions.json").read_text())
    blockout = json.loads(
        (ROOT / "data" / "district1-blockout.json").read_text())
    env_cfg = json.loads(
        (ROOT / "data" / "environment-config.json").read_text())
    seasons = (ROOT / "docs" / "TECH-SEASONS.md").read_text()
    clock = (ROOT / "docs" / "TECH-CLOCK-WEATHER.md").read_text()
    photos = (ROOT / "tools" / "sim" / "photographs.py").read_text()
    dialogue = json.loads(
        (ROOT / "data" / "dialogue-lines.json").read_text())

    # 1. The new section exists with the contract's parts.
    check("### 3.6 Mission Progress Write Contract (Unit DG" in gdd04,
          "GDD-04 has the §3.6 write contract section")
    s36 = gdd04.split("### 3.6 ")[1].split("## 4.")[0]
    check("The mission system (Phase 6) is the only writer" in s36,
          "§3.6 names the mission system as the only writer")
    check("no row until it becomes available" in s36.lower()
          or "No row before availability" in s36,
          "§3.6 states no row before availability (not_started)")
    check("available_at_game_minutes" in s36,
          "§3.6 uses the §3.2 fifth key")
    check("objectives_complete" in s36,
          "§3.6 uses the §13.3 objectives_complete key")
    check("no per-objective array" in s36,
          "§3.6 forbids a per-objective array in progress (§13.3)")
    check("side:<type>:<giver>:<generated_at_game_minutes>" in s36,
          "§3.6 keys favour instances by the §3.1 instance key")
    check("adds no sim code, no schema change" in s36,
          "§3.6 states it adds no sim code and no schema change")

    # 2. The status transitions match GDD-04 §1 / GDD-15 §13.
    check("`available` → `active`" in s36,
          "§3.6 has the available -> active transition")
    check("`active` → `completed`" in s36,
          "§3.6 has the active -> completed transition")
    check("`active` → `failed`" in s36,
          "§3.6 has the active -> failed transition")
    check("`failed` → `available`" in s36,
          "§3.6 has the failed -> available retry transition")
    check("— (never)" in s36,
          "§3.6 forbids the available -> failed and"
          " available -> completed skips")
    check("7 in-game days" in s36,
          "§3.6 retries after 7 in-game days (GDD-04 §1)")
    check("Dialogue never writes `failed` or `available`" in s36
          or "dialogue never writes `failed`" in s36.lower(),
          "§3.6 keeps failed/available as the mission system's (§13.4)")
    check("Favours never carry a deadline" in s36,
          "§3.6 keeps favours deadline-free (§3.1/§3.2)")

    # 3. The schema table the contract writes to.
    mp = schema.split("CREATE TABLE mission_progress")[1] \
        .split("CREATE TABLE")[0]
    check("PRIMARY KEY (character_id, mission_id)" in mp,
          "schema.sql mission_progress PK is (character_id, mission_id)")
    check("CHECK (status IN" in mp
          and "'available','active','completed','failed'" in mp,
          "schema.sql mission_progress status CHECK has the four states")
    check("progress        JSONB NOT NULL DEFAULT '{}'::jsonb" in mp
          or "JSONB NOT NULL DEFAULT '{}'" in mp,
          "schema.sql mission_progress progress is JSONB default {}")
    check("updated_at_game_minutes BIGINT NOT NULL" in mp,
          "schema.sql mission_progress has updated_at_game_minutes")

    # 4. Mission 1.4 as the contract's worked example.
    m14 = next(m for m in missions["missions"] if m["id"] == "1.4")
    check(m14["title"] == "The River at Dusk",
          "missions.json 1.4 is The River at Dusk")
    check(m14["objectives"] == [
        "Watch the sunset from the riverfront promenade",
        "Visit the tea stall"],
        "missions.json 1.4 objectives match the contract")
    check(m14["rewards"]["credits_ncr"] is None,
          "missions.json 1.4 has no credit reward (null)")
    check("Memory event: First evening in Rupsha"
          in m14["rewards"]["other"],
          "missions.json 1.4 reward is the First evening memory event")
    check("Photo mode" in m14["unlocks"],
          "missions.json 1.4 unlocks photo mode (the DA gate)")
    check(m14["zone_refs"] == ["d1_riverfront", "d1_market"],
          "missions.json 1.4 zone_refs are riverfront + market")
    check("anchor_tea_stall_riverfront_1" in s36,
          "§3.6 names the riverfront tea stall anchor id")
    stalls = [a for a in blockout["service_anchors"]
              if a["type"] == "tea_stall"
              and a["zone_id"] == "d1_riverfront"]
    check(len(stalls) == 1
          and stalls[0]["id"] == "anchor_tea_stall_riverfront_1",
          "district1-blockout.json has exactly one riverfront tea stall",
          f"{[s['id'] for s in stalls]}")
    check("The six Boro Bazar stalls do not verify it" in s36,
          "§3.6 excludes the six market stalls from objective (2)")

    # 5. The sunset window is computed from sourced numbers.
    check("daylight(data, day_index)" in s36,
          "§3.6 takes the sunset minute from environment.daylight()")
    base_sunset = env_cfg["daylight"]["base_sunset_min"]
    check(base_sunset == 1080,
          "environment-config.json base sunset is 18:00 (1080 min)")
    amps = [s["daylight_amplitude_min"]
            for s in env_cfg["seasons"]]
    sunsets = [base_sunset + a for a in amps]
    check(all(1020 <= s < 1200 for s in sunsets),
          "every season's sunset falls inside Evening 17:00–20:00",
          f"sunsets={sorted(sunsets)}")
    check("Evening | 17:00" in clock or "Evening | 17:00–20:00" in clock,
          "TECH-CLOCK-WEATHER defines Evening 17:00–20:00")
    check("06:00/18:00" in seasons,
          "TECH-SEASONS defines the 06:00/18:00 daylight base")

    # 6. The DA gate the contract unlocks, and the honest gaps.
    check("PHOTO_MODE_MISSION = \"1.4\"" in photos,
          "photographs.py gates on mission 1.4")
    check("status = 'completed'" in photos,
          "photographs.py requires the 1.4 row completed")
    check("Unit DG · Queue 16" in gdd04.split("### 3.5 ")[1]
          .split("### 3.6")[0],
          "§3.5 carries the DG update (writer now specified)")
    check("no `dlg_1_4_`" in s36 or "no `dlg_1_4_*` node exists" in s36,
          "§3.6 records that no 1.4 dialogue tree exists yet")
    dlg_text = json.dumps(dialogue)
    check("dlg_1_4_" not in dlg_text,
          "dialogue-lines.json has no 1.4 nodes (the gap is real)")
    check("does not set a deadline for 1.4" in s36,
          "§3.6 states 1.4 carries no deadline (§3.2)")
    check("The mission system may keep its own verification record"
          in s36,
          "§3.6 lets the mission system keep verification elsewhere")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
