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

Every shipped mission tree now has a §3.6 condition (Unit EJ,
Queue 20, closed the last one — 2.4): the suite asserts that, and
no mission with a tree is out of scope any more.
"""
import json
import re
import unittest
from pathlib import Path

from tools.sim import environment as env
from tools.sim import missions as ms
from tools.sim import photographs as ph
from tools.sim import relationships as rel
from tools.sim.tests.common import data, make_household, make_person, make_store

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

    def test_every_shipped_mission_tree_has_a_condition(self):
        # Every mission with a dialogue tree has a §3.6 condition
        # and a registered verifier — 2.4 was the last one without
        # (Queue 18/19), and Unit EJ (Queue 20) closed it. 1.3 used
        # to be out of scope too (Queue 18); Unit EB gave it a
        # condition and a verifier, so it is covered now — the suite
        # asserts that, not the old limit. Unit EO (Queue 21) ships
        # the 2.3 tree and its condition together, so 2.3 is
        # covered from the day its tree ships.
        self.assertIn("2.4", ms.CONDITIONED_MISSIONS)
        self.assertIn("1.3", ms.CONDITIONED_MISSIONS)
        self.assertIn("2.3", ms.CONDITIONED_MISSIONS)
        dlg = json.loads(
            (ROOT / "data" / "dialogue-lines.json").read_text())
        self.assertIn("mission_1_3_neighbour_help", dlg["trees"])
        self.assertIn("mission_2_4_friendship", dlg["trees"])
        self.assertIn("mission_2_1_learn_the_trade", dlg["trees"])
        self.assertIn("mission_2_2_rainy_day_fund", dlg["trees"])
        self.assertIn("mission_2_3_market_run", dlg["trees"])
        for tree in ("mission_1_3_neighbour_help",
                     "mission_2_4_friendship",
                     "mission_2_1_learn_the_trade",
                     "mission_2_2_rainy_day_fund",
                     "mission_2_3_market_run"):
            mission_id = tree.split("_")[1] + "." \
                + tree.split("_")[2]
            self.assertIn(mission_id, ms.CONDITIONED_MISSIONS,
                          f"{tree} ships a tree but no §3.6 condition")


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

    def test_1_3_completes_only_with_3_neighbours_and_a_help(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        neighbours = []
        for i in range(3):
            n = make_person(store, age=30 + i, first=f"Neighbour{i}")
            rel.add_edge(store, cid, n, "neighbour", GM)
            neighbours.append(n)
        key = ms.create_favour_instance(store, d, cid, "errands",
                                        neighbours[0], GM)
        ms.accept_mission(store, cid, key, GM + 100)
        ms.set_objectives_complete(store, cid, key, GM + 200)
        ms.complete_mission(store, cid, key, GM + 300)
        _active(store, cid, "1.3")
        self.assertTrue(ms.verify_mission_1_3(store, d, cid, GM + 400))
        self.assertTrue(ms.complete_mission(store, cid, "1.3", GM + 400))
        self.assertEqual(ms.get_status(store, cid, "1.3"), "completed")

    def test_1_3_does_not_complete_without_the_help(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        for i in range(3):
            n = make_person(store, age=30 + i, first=f"Neighbour{i}")
            rel.add_edge(store, cid, n, "neighbour", GM)
        _active(store, cid, "1.3")
        # Three neighbours, no completed errand: not verified.
        self.assertFalse(ms.verify_mission_1_3(store, d, cid, GM + 200))
        self.assertFalse(ms.complete_mission(store, cid, "1.3", GM + 200))

    def test_2_2_completes_only_at_starting_balance_plus_15000(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        _employ(store, cid, "civil_engineer", {"engineering": 5})
        # Civil engineer starts at 25,000; the target is 40,000.
        store.execute("UPDATE characters SET balance_cached = 39999"
                      " WHERE character_id = ?", (cid,))
        _active(store, cid, "2.2")
        self.assertFalse(ms.verify_mission_2_2(store, d, cid, GM + 200))
        self.assertFalse(ms.complete_mission(store, cid, "2.2", GM + 200))
        store.execute("UPDATE characters SET balance_cached = 40000"
                      " WHERE character_id = ?", (cid,))
        self.assertTrue(ms.verify_mission_2_2(store, d, cid, GM + 300))
        self.assertTrue(ms.complete_mission(store, cid, "2.2", GM + 300))
        self.assertEqual(ms.get_status(store, cid, "2.2"), "completed")

    def test_2_4_completes_only_with_a_friend_at_mean_40(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        friend = make_person(store, age=30, first="Friend")
        rel.add_edge(store, cid, friend, "friend", GM, trust=45,
                     affection=34)
        _active(store, cid, "2.4")
        # Mean 39.5: no verification, no completion.
        self.assertFalse(ms.verify_mission_2_4(store, d, cid, GM + 200))
        self.assertFalse(ms.complete_mission(store, cid, "2.4",
                                            GM + 200))
        rel.adjust_scores(store, cid, friend, GM + 200, affection=1)
        self.assertTrue(ms.verify_mission_2_4(store, d, cid, GM + 300))
        self.assertTrue(ms.complete_mission(store, cid, "2.4", GM + 300))
        self.assertEqual(ms.get_status(store, cid, "2.4"), "completed")

    def test_2_3_completes_only_with_a_rupsha_food_purchase(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        hid, _pid = make_household(store, [cid])
        _active(store, cid, "2.3")
        # No food row yet: no verification, no completion.
        self.assertFalse(ms.verify_mission_2_3(store, d, cid, GM + 200))
        self.assertFalse(ms.complete_mission(store, cid, "2.3", GM + 200))
        store.execute(
            "INSERT INTO household_consumption (household_id,"
            " month_index, good_id, units, spend_ncr, unmet_units)"
            " VALUES (?, 0, 'food_basket', 12.5, 1000, 0)", (hid,))
        self.assertTrue(ms.verify_mission_2_3(store, d, cid, GM + 300))
        self.assertTrue(ms.complete_mission(store, cid, "2.3", GM + 300))
        self.assertEqual(ms.get_status(store, cid, "2.3"), "completed")

    def test_2_3_does_not_complete_for_a_shibnagar_household(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        hid, _pid = make_household(store, [cid])
        store.execute("UPDATE households SET district_id = 'c2_market'"
                      " WHERE household_id = ?", (hid,))
        store.execute(
            "INSERT INTO household_consumption (household_id,"
            " month_index, good_id, units, spend_ncr, unmet_units)"
            " VALUES (?, 0, 'food_basket', 12.5, 1000, 0)", (hid,))
        _active(store, cid, "2.3")
        # Food bought, but from Shibnagar's shelves — not Boro
        # Bazar.
        self.assertFalse(ms.verify_mission_2_3(store, d, cid, GM + 200))
        self.assertFalse(ms.complete_mission(store, cid, "2.3", GM + 200))

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

    def test_completing_1_3_does_not_open_the_gate(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        neighbours = []
        for i in range(3):
            n = make_person(store, age=30 + i, first=f"Neighbour{i}")
            rel.add_edge(store, cid, n, "neighbour", GM)
            neighbours.append(n)
        key = ms.create_favour_instance(store, d, cid, "errands",
                                        neighbours[0], GM)
        ms.accept_mission(store, cid, key, GM + 100)
        ms.set_objectives_complete(store, cid, key, GM + 200)
        ms.complete_mission(store, cid, key, GM + 300)
        _active(store, cid, "1.3")
        ms.verify_mission_1_3(store, d, cid, GM + 400)
        ms.complete_mission(store, cid, "1.3", GM + 400)
        self.assertEqual(ms.get_status(store, cid, "1.3"), "completed")
        self.assertFalse(ph.photo_mode_unlocked(store, cid))

    def test_completing_2_2_does_not_open_the_gate(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        _employ(store, cid, "civil_engineer", {"engineering": 5})
        store.execute("UPDATE characters SET balance_cached = 40000"
                      " WHERE character_id = ?", (cid,))
        _active(store, cid, "2.2")
        ms.verify_mission_2_2(store, d, cid, GM + 200)
        ms.complete_mission(store, cid, "2.2", GM + 300)
        self.assertEqual(ms.get_status(store, cid, "2.2"), "completed")
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

    def test_completing_2_4_does_not_open_the_gate(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        friend = make_person(store, age=30, first="Friend")
        rel.add_edge(store, cid, friend, "friend", GM, trust=40,
                     affection=40)
        _active(store, cid, "2.4")
        ms.verify_mission_2_4(store, d, cid, GM + 200)
        ms.complete_mission(store, cid, "2.4", GM + 300)
        self.assertEqual(ms.get_status(store, cid, "2.4"), "completed")
        self.assertFalse(ph.photo_mode_unlocked(store, cid))

    def test_completing_2_3_does_not_open_the_gate(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        hid, _pid = make_household(store, [cid])
        store.execute(
            "INSERT INTO household_consumption (household_id,"
            " month_index, good_id, units, spend_ncr, unmet_units)"
            " VALUES (?, 0, 'food_basket', 12.5, 1000, 0)", (hid,))
        _active(store, cid, "2.3")
        ms.verify_mission_2_3(store, d, cid, GM + 200)
        ms.complete_mission(store, cid, "2.3", GM + 300)
        self.assertEqual(ms.get_status(store, cid, "2.3"), "completed")
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
