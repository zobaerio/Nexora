"""Queue 18 Unit DS — Mission-Progress Regression Suite (GDD-04
§3.6; DL/DO follow-up).

Tests the mission-progress writer as a standing regression: for
every mission with a §3.6 completion condition, the writer completes
it exactly when its condition holds, and the DA photo-mode gate
stays closed otherwise. The suite's tripwire is the registry
``missions.CONDITIONED_MISSIONS``: every ``verify_mission_*``
function in tools/sim/missions.py must be registered AND have a
§3.6 "Completion condition" subsection in GDD-04, and every §3.6
condition must have a registered verifier. A mission that ships a
verifier without a condition — or a condition without a verifier —
breaks this suite loudly, by design.

Missions with dialogue trees but no §3.6 condition (1.3, 2.4) are
outside this suite's scope: their verification is still Phase 6
work, and the suite asserts that limit rather than claiming to
cover them.
"""
import json
import re
import unittest
from pathlib import Path

from tools.sim import environment as env
from tools.sim import missions as ms
from tools.sim import photographs as ph
from tools.sim.tests.common import data, make_person, make_store

ROOT = Path(__file__).resolve().parents[3]
GM = 480


def _sunset(d, day_index=0):
    return env.daylight(d, day_index)[1]


def _active(store, cid, mission_id):
    ms.make_available(store, cid, mission_id, GM)
    ms.accept_mission(store, cid, mission_id, GM + 100)


def _employ(store, cid, profession_id, skills):
    store.insert("employments", employment_id="EM-TEST-DS",
                 character_id=cid, profession_id=profession_id,
                 tier=1, wage_per_month=10000,
                 started_at_game_minutes=GM,
                 ended_at_game_minutes=None)
    for skill_id, level in skills.items():
        store.insert("character_skills", character_id=cid,
                     skill_id=skill_id, level=level,
                     experience=level * 50)


class TestRegistryTripwire(unittest.TestCase):
    """The suite fails loudly when a mission ships without a
    condition — in either direction (verifier without spec, or
    spec without verifier)."""

    def test_every_verifier_is_registered(self):
        source = (ROOT / "tools" / "sim" / "missions.py").read_text()
        verifiers = re.findall(r"def (verify_mission_[\w.]+)\(",
                               source)
        for fn in verifiers:
            self.assertIn(fn, ms.CONDITIONED_MISSIONS.values(),
                          f"{fn} exists but is not registered — "
                          "a mission shipped a verifier with no §3.6 "
                          "condition")

    def test_every_registered_mission_has_a_verifier(self):
        for mission_id, fn in ms.CONDITIONED_MISSIONS.items():
            self.assertTrue(callable(getattr(ms, fn, None)),
                            f"{mission_id} is registered but "
                            f"{fn} does not exist")

    def test_every_registered_mission_has_a_section_3_6_condition(self):
        gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md") \
            .read_text()
        for mission_id in ms.CONDITIONED_MISSIONS:
            self.assertIn(
                f"**Completion condition — mission {mission_id}",
                gdd04,
                f"{mission_id} is registered but GDD-04 §3.6 has no "
                "completion condition for it")

    def test_every_section_3_6_condition_is_registered(self):
        gdd04 = (ROOT / "docs" / "GDD-04-MISSIONS-AND-PROGRESSION.md") \
            .read_text()
        specified = re.findall(
            r"\*\*Completion condition — mission (\d+\.\d+)", gdd04)
        self.assertEqual(sorted(specified),
                         sorted(ms.CONDITIONED_MISSIONS),
                         "a §3.6 condition exists with no registered "
                         "verifier — a mission shipped a condition "
                         "the writer cannot complete")

    def test_trees_without_conditions_are_out_of_scope(self):
        # 1.3 and 2.4 have dialogue trees but no §3.6 condition and
        # no verifier: the suite records that limit, it does not
        # pretend to cover them.
        self.assertNotIn("1.3", ms.CONDITIONED_MISSIONS)
        self.assertNotIn("2.4", ms.CONDITIONED_MISSIONS)
        dlg = json.loads(
            (ROOT / "data" / "dialogue-lines.json").read_text())
        self.assertIn("mission_1_3_neighbour_help", dlg["trees"])
        self.assertIn("mission_2_4_friendship", dlg["trees"])


class TestWriterCompletesConditionedMissions(unittest.TestCase):
    """For every conditioned mission: the writer completes it exactly
    when its condition holds, and not otherwise."""

    def test_1_4_completes_only_in_the_sunset_window_at_the_stall(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        _active(store, cid, "1.4")
        sunset = _sunset(d, 0)
        # Wrong anchor: no verification, no completion.
        self.assertFalse(ms.verify_mission_1_4(
            store, d, cid, "d1_riverfront",
            "anchor_tea_stall_market_1", sunset + 30))
        self.assertFalse(ms.complete_mission(store, cid, "1.4",
                                            sunset + 30))
        # Right place, right window: verifies and completes.
        self.assertTrue(ms.verify_mission_1_4(
            store, d, cid, "d1_riverfront",
            "anchor_tea_stall_riverfront_1", sunset + 30))
        self.assertTrue(ms.complete_mission(store, cid, "1.4",
                                           sunset + 30))
        self.assertEqual(ms.get_status(store, cid, "1.4"), "completed")

    def test_2_1_completes_only_at_skill_20_in_the_primary_skill(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        _employ(store, cid, "civil_engineer", {"engineering": 19})
        _active(store, cid, "2.1")
        # One short of 20: no verification, no completion.
        self.assertFalse(ms.verify_mission_2_1(store, d, cid, GM + 200))
        self.assertFalse(ms.complete_mission(store, cid, "2.1", GM + 200))
        store.execute("UPDATE character_skills SET level = 20,"
                      " experience = 1000 WHERE character_id = ?"
                      " AND skill_id = 'engineering'", (cid,))
        self.assertTrue(ms.verify_mission_2_1(store, d, cid, GM + 300))
        self.assertTrue(ms.complete_mission(store, cid, "2.1", GM + 300))
        self.assertEqual(ms.get_status(store, cid, "2.1"), "completed")

    def test_a_conditioned_mission_never_completes_unverified(self):
        # Neither conditioned mission completes from `active` without
        # its verifier having set objectives_complete.
        for mission_id in ms.CONDITIONED_MISSIONS:
            store = make_store()
            d = data()
            cid = make_person(store, age=25, first="Player")
            if mission_id == "2.1":
                _employ(store, cid, "civil_engineer",
                        {"engineering": 20})
            _active(store, cid, mission_id)
            self.assertFalse(ms.complete_mission(store, cid, mission_id,
                                                GM + 200))
            self.assertEqual(ms.get_status(store, cid, mission_id),
                             "active")


class TestGateStaysClosedOtherwise(unittest.TestCase):
    """The DA gate opens on 1.4 completing — and on nothing else."""

    def test_gate_closed_before_1_4_completes(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        self.assertFalse(ph.photo_mode_unlocked(store, cid))
        _active(store, cid, "1.4")
        self.assertFalse(ph.photo_mode_unlocked(store, cid))

    def test_gate_opens_only_on_1_4_completion(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        _active(store, cid, "1.4")
        sunset = _sunset(d, 0)
        ms.verify_mission_1_4(store, d, cid, "d1_riverfront",
                              "anchor_tea_stall_riverfront_1",
                              sunset + 30)
        ms.complete_mission(store, cid, "1.4", sunset + 30)
        self.assertTrue(ph.photo_mode_unlocked(store, cid))

    def test_gate_stays_closed_when_1_4_fails(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        _active(store, cid, "1.4")
        ms.fail_mission(store, cid, "1.4", GM + 200)
        self.assertEqual(ms.get_status(store, cid, "1.4"), "failed")
        self.assertFalse(ph.photo_mode_unlocked(store, cid))

    def test_completing_2_1_does_not_open_the_gate(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        _employ(store, cid, "civil_engineer", {"engineering": 20})
        _active(store, cid, "2.1")
        ms.verify_mission_2_1(store, d, cid, GM + 200)
        ms.complete_mission(store, cid, "2.1", GM + 300)
        self.assertEqual(ms.get_status(store, cid, "2.1"), "completed")
        self.assertFalse(ph.photo_mode_unlocked(store, cid))

    def test_completing_a_favour_does_not_open_the_gate(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        giver = make_person(store, age=40, first="Giver")
        key = ms.create_favour_instance(store, d, cid, "discovery",
                                        giver, GM)
        _active(store, cid, key)
        store.insert("discovery_progress", account_id="ACC1",
                     discoverable_type="landmark",
                     discoverable_id="lm_clock_tower",
                     discovered_at_game_minutes=GM + 200,
                     discovered_in_zone="d1_market")
        self.assertTrue(ms.verify_favour_objectives(
            store, cid, key, GM + 300, account_id="ACC1",
            discoverable_id="lm_clock_tower"))
        self.assertTrue(ms.complete_mission(store, cid, key, GM + 300))
        self.assertFalse(ph.photo_mode_unlocked(store, cid))


if __name__ == "__main__":
    unittest.main()
