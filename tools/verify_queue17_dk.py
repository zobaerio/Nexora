"""Verify Queue 17 Unit DK — School Uniforms + Age-Up Outfits
(GDD-09 §5; GDD-04 §3.3, Unit DD follow-up).

Checks the implementation against the design: GDD-09 §5 (the
student uniform rule), data/clothing.json (uniform_school),
tools/sim/lost_items.py (seed_school_uniform, seed_age_up_outfits),
the wiring call sites (education.enrol_school_sweep,
lifecycle.daily_check, engine daily rollover),
tools/validate_data.py (the uniform checks) and the tests.
Prints one line per check and a summary; exits 0 only when every
check passes. Run from the repo root: python3 tools/verify_queue17_dk.py
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
    gdd09 = (ROOT / "docs" / "GDD-09-CHARACTER-CREATOR.md").read_text()
    clothing = json.loads((ROOT / "data" / "clothing.json").read_text())
    lost = (ROOT / "tools" / "sim" / "lost_items.py").read_text()
    education = (ROOT / "tools" / "sim" / "education.py").read_text()
    lifecycle = (ROOT / "tools" / "sim" / "lifecycle.py").read_text()
    engine = (ROOT / "tools" / "sim" / "engine.py").read_text()
    validator = (ROOT / "tools" / "validate_data.py").read_text()
    tests_li = (ROOT / "tools" / "sim" / "tests"
                / "test_lost_items.py").read_text()
    tests_lc = (ROOT / "tools" / "sim" / "tests"
                / "test_lifecycle.py").read_text()

    # 1. The catalogue carries the school uniform (DD already did).
    uniform = next((i for i in clothing["items"]
                    if i["id"] == "uniform_school"), None)
    check(uniform is not None,
          "clothing.json carries uniform_school")
    check(uniform is not None and uniform["slot"] == "uniform_set",
          "uniform_school is a uniform_set (worn alone)")
    check(uniform is not None and "school" in uniform["contexts"],
          "uniform_school carries the school context")

    # 2. The seeding helpers exist with the CX record shape.
    check("def seed_school_uniform" in lost,
          "lost_items.py defines seed_school_uniform")
    check("def seed_age_up_outfits" in lost,
          "lost_items.py defines seed_age_up_outfits")
    check("def _has_starting_outfit_rows" in lost,
          "lost_items.py defines the starting-outfit guard")
    check('"school"' in lost and '"household"' in lost,
          "school uniform rows carry context school, issued household")
    check('outfit_context") in ("work", "casual", "formal")' in lost,
          "the guard counts work/casual/formal, not the uniform")

    # 3. The wiring call sites.
    check("seed_school_uniform(" in education,
          "education.enrol_school_sweep seeds the uniform at enrolment")
    check("def daily_check(store, rng, character, day_index,"
          " game_minutes," in lifecycle,
          "lifecycle.daily_check takes optional data")
    check("seed_age_up_outfits(" in lifecycle,
          "daily_check seeds outfits on the Young Adult transition")
    check('stage == "Young Adult"' in lifecycle,
          "age-up seeding fires only on the Young Adult transition")
    check("daily_check(store, self.rng, fresh, day," in engine
          and "data=data" in engine,
          "engine passes data to daily_check at day rollover")

    # 4. The validator checks the uniform.
    check("school uniform item exists in the clothing catalogue"
          in validator,
          "validate_data.py checks uniform_school exists")
    check("school uniform is a uniform_set" in validator,
          "validate_data.py checks the uniform slot")
    check("school uniform carries the school context" in validator,
          "validate_data.py checks the uniform context")

    # 5. The GDD records the implementation.
    check("Update, Unit DK · Queue 17" in gdd04,
          "GDD-04 §3.3 carries the DK update (DD note)")
    check("Update, Unit DK · Queue 17" in gdd09,
          "GDD-09 §5 carries the DK student-loop note")
    check("their school uniform is Unit AB's student loop" in gdd04,
          "GDD-04 keeps the Unit AB attribution for the loop")

    # 6. The tests cover the contract.
    check("class TestSchoolUniform" in tests_li,
          "tests carry a TestSchoolUniform class")
    check("class TestAgeUpOutfits" in tests_lc,
          "tests carry a TestAgeUpOutfits class")
    n_li = len(re.findall(r"def test_", tests_li))
    n_lc = len(re.findall(r"def test_", tests_lc))
    check(n_li >= 48 + 20,
          "test_lost_items.py has 68+ tests (48 before + 20 DJ/DK)",
          f"{n_li} tests")
    check("test_school_uniform_does_not_block_age_up_outfits"
          in tests_lc,
          "tests prove the uniform does not block age-up outfits")
    check("test_age_up_without_data_seeds_nothing" in tests_lc,
          "tests prove daily_check without data seeds nothing")

    failed = [c for c in CHECKS if not c[0]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
