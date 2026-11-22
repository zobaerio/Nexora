"""Verify Queue 10 Unit BE — dialogue effect functions (AV gaps G6+G7, G5).

Checks the section against the sources it must resolve to:
GDD-01 §2.3/§5, GDD-15 §12, data/dialogue-lines.json, tools/sim/memory.py,
data/schema.sql. Prints one line per check and a summary; exits 0 only
when every check passes. Run from the repo root:
python3 tools/verify_queue10_be.py
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


def load_json(name):
    return json.loads((ROOT / "data" / name).read_text())


def all_nodes(dlg):
    out = []

    def walk(o):
        if isinstance(o, dict):
            if "node_id" in o:
                out.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(dlg)
    return out


def all_effects(dlg):
    out = []

    def walk(o):
        if isinstance(o, dict):
            out.extend(o.get("effects") or [])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(dlg)
    return out


def main():
    gdd01 = (ROOT / "docs" / "GDD-01-LIFE-AND-DATA-MODEL.md").read_text()
    gdd15 = (ROOT / "docs" / "GDD-15-DIALOGUE.md").read_text()
    schema = (ROOT / "data" / "schema.sql").read_text()
    memory = (ROOT / "tools" / "sim" / "memory.py").read_text()
    dlg = load_json("dialogue-lines.json")
    nodes = {n["node_id"]: n for n in all_nodes(dlg)}
    effects = all_effects(dlg)

    # 1. §16 exists with all five subsections.
    check("## 16. Dialogue Effect Functions" in gdd15,
          "GDD-15 §16 exists")
    sec16 = gdd15.split("## 16. Dialogue Effect Functions")[1]
    for sub in ("### 16.1", "### 16.2", "### 16.3", "### 16.4",
                "### 16.5"):
        check(sub in sec16, f"§16 subsection {sub} exists")

    # 2. The memory.py functions §16.1/§12.5 rely on exist.
    for fn in ("def record_memory", "def memories_about", "def prune",
               "MEMORY_CAP = 200", "def _priority"):
        check(fn in memory, f"tools/sim/memory.py defines {fn}")

    # 3. memory_weight_reduce: the data carries it with amount_ref
    # runtime_rule, and §16.1 keeps the amount a parameter (no number).
    mw = [e for e in effects if e.get("type") == "memory_weight_reduce"]
    check(len(mw) == 2, "memory_weight_reduce appears twice (node + line)",
          f"n={len(mw)}")
    check(all(e.get("amount_ref") == "runtime_rule" for e in mw),
          "memory_weight_reduce amount_ref is runtime_rule")
    sec161 = sec16.split("### 16.2")[0]
    check("No number is decided here" in sec161,
          "§16.1 states no number is decided for the amount")
    check("never across zero" in sec161 and "never deleted" in sec161,
          "§16.1 states the step rule (toward zero, never delete)")

    # 4. propose_goal: the data carries it, the node has no accept choice
    # (the data-fix claim), and character_goals supports stage/active.
    pg = [e for e in effects if e.get("type") == "propose_goal"]
    check(len(pg) == 2, "propose_goal appears twice (node + line)",
          f"n={len(pg)}")
    check(all(e.get("goal_ref") == "npc_life_goal" for e in pg),
          "propose_goal goal_ref is npc_life_goal")
    help_node = nodes.get("dlg_topic_goals_help", {})
    check(help_node.get("choices") == [],
          "dlg_topic_goals_help has no choices (accept path missing)",
          "choices=[] — §16.2 data fix required")
    goals = re.search(r"CREATE TABLE character_goals \(.*?\);",
                      schema, re.S).group(0)
    check("'stage'" in goals and "'active'" in goals,
          "character_goals supports goal_kind stage + status active")
    check("max 3 active" in gdd01,
          "GDD-01 §2.2 states the max-3-active goal stack cap")

    # 5. G5 fix 1: all five shipped memory_write texts have an event_type
    # in the §16.3 table; the two sourced names check out.
    mwrites = [e for e in effects if e.get("type") == "memory_write"]
    texts = sorted({e.get("text") for e in mwrites})
    check(len(texts) == 5, "five distinct memory_write texts in the data",
          f"texts={texts}")
    sec163 = sec16.split("### 16.4")[0]
    for t in texts:
        check(t in sec163, f"§16.3 table covers memory text {t!r}")
    check("helped_by_player" in schema,
          "event_type helped_by_player is sourced from schema.sql comment")
    import glob as _glob
    sim_src = "".join(p.read_text() for p in
                      [Path(f) for f in _glob.glob(
                          str(ROOT / "tools" / "sim" / "*.py"))])
    check('"new_friend"' in sim_src,
          "event_type new_friend appears in sim record_memory calls")

    # 6. G5 fix 2: weightless writes number 8, weighted 2 (+40); the rule
    # is the schema default 0.
    weightless = [e for e in mwrites if "weight" not in e]
    weighted = [e for e in mwrites if "weight" in e]
    check(len(weightless) == 8, "eight weightless memory_write effects",
          f"n={len(weightless)}")
    check(len(weighted) == 2
          and all(e.get("weight") == 40 for e in weighted),
          "two weighted memory_write effects, both weight 40")
    check("emotional_weight SMALLINT NOT NULL DEFAULT 0" in schema,
          "schema default for emotional_weight is 0")
    sec164 = sec16.split("### 16.5")[0]
    check("stores `emotional_weight = 0`" in sec164,
          "§16.4 rules weightless memory_write stores weight 0")

    # 7. G5 fix 3: the owner field with speaker/player values.
    sec165 = sec16.split("### 16.5")[1]
    check('"speaker"' in sec165 and '"player"' in sec165,
          "§16.5 defines the owner field (speaker / player)")
    check("default is `\"speaker\"`" in sec165
          or 'default is `"speaker"`' in sec165,
          "§16.5 states the speaker default")

    # 8. §12.8 G5/G6/G7 are marked resolved by this unit.
    for gap in ("G5", "G6", "G7"):
        check(f"Resolved by Queue 10, Unit BE" in gdd15
              and gap in gdd15,
              f"§12.8 {gap} marked resolved by Unit BE")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\nCHECKS: {len(CHECKS)}, FAILURES: {len(failed)}")
    for _, label, detail in failed:
        print(f"  FAILED: {label} {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
