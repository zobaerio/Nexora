"""Queue 17 Unit DL — Mission System Writer Implementation
(GDD-04 §3.6, Unit DG design).

Tests the mission_progress writer: the status lifecycle with no
skips, the 5-key progress shape, the mission 1.4 completion
condition (sunset window + riverfront tea stall anchor) and that
the DA photo-mode gate opens on 1.4 completing, deadline expiry for
the three deadline missions, the 7-day retry, and favour instances.
"""
import json
import unittest

from tools.sim import environment as env
from tools.sim import lost_items as li
from tools.sim import missions as ms
from tools.sim import photographs as ph
from tools.sim.tests.common import (data, make_person, make_store, rng)

GM = 480
DAY = 1440


def _sunset(d, day_index=0):
    return env.daylight(d, day_index)[1]


class TestLifecycle(unittest.TestCase):
    def test_no_row_is_not_started(self):
        store = make_store()
        cid = make_person(store, age=25, first="Player")
        self.assertIsNone(ms.get_row(store, cid, "1.4"))
        self.assertIsNone(ms.get_status(store, cid, "1.4"))
        self.assertFalse(ms.accept_mission(store, cid, "1.4", GM))
        self.assertFalse(ms.complete_mission(store, cid, "1.4", GM))

    def test_make_available_writes_the_fifth_key(self):
        store = make_store()
        cid = make_person(store, age=25, first="Player")
        self.assertTrue(ms.make_available(store, cid, "1.4", GM))
        row = ms.get_row(store, cid, "1.4")
        self.assertEqual(row["status"], "available")
        progress = json.loads(row["progress"])
        self.assertEqual(progress, {"available_at_game_minutes": GM})
        # A second creation is refused — a retry reuses the row.
        self.assertFalse(ms.make_available(store, cid, "1.4", GM + 10))

    def test_available_cannot_complete_or_fail(self):
        store = make_store()
        cid = make_person(store, age=25, first="Player")
        ms.make_available(store, cid, "1.4", GM)
        # No state is skipped: available -> completed is never.
        self.assertFalse(ms.complete_mission(store, cid, "1.4", GM))
        self.assertFalse(ms.fail_mission(store, cid, "1.4", GM))
        self.assertEqual(ms.get_status(store, cid, "1.4"), "available")

    def test_accept_sets_accepted_at(self):
        store = make_store()
        cid = make_person(store, age=25, first="Player")
        ms.make_available(store, cid, "1.4", GM)
        self.assertTrue(ms.accept_mission(store, cid, "1.4", GM + 100))
        row = ms.get_row(store, cid, "1.4")
        self.assertEqual(row["status"], "active")
        progress = json.loads(row["progress"])
        self.assertEqual(progress["available_at_game_minutes"], GM)
        self.assertEqual(progress["accepted_at_game_minutes"], GM + 100)
        # A second accept is refused.
        self.assertFalse(ms.accept_mission(store, cid, "1.4", GM + 200))

    def test_complete_needs_verified_objectives(self):
        store = make_store()
        cid = make_person(store, age=25, first="Player")
        ms.make_available(store, cid, "1.4", GM)
        ms.accept_mission(store, cid, "1.4", GM + 100)
        self.assertFalse(ms.complete_mission(store, cid, "1.4", GM + 200))
        self.assertTrue(ms.set_objectives_complete(store, cid, "1.4",
                                                   GM + 200))
        self.assertTrue(ms.complete_mission(store, cid, "1.4", GM + 300))
        row = ms.get_row(store, cid, "1.4")
        self.assertEqual(row["status"], "completed")
        progress = json.loads(row["progress"])
        self.assertTrue(progress["objectives_complete"])
        self.assertEqual(progress["completed_at_game_minutes"], GM + 300)
        # Exactly the four keys written so far — `abandoned` is
        # absent, and no other key is ever written (DG §3.6).
        self.assertEqual(set(progress),
                         {"available_at_game_minutes",
                          "accepted_at_game_minutes",
                          "objectives_complete",
                          "completed_at_game_minutes"})

    def test_abandon_fails_and_retry_needs_seven_days(self):
        store = make_store()
        cid = make_person(store, age=25, first="Player")
        ms.make_available(store, cid, "1.4", GM)
        ms.accept_mission(store, cid, "1.4", GM + 100)
        self.assertTrue(ms.fail_mission(store, cid, "1.4", GM + 200,
                                        abandoned=True))
        row = ms.get_row(store, cid, "1.4")
        self.assertEqual(row["status"], "failed")
        self.assertTrue(json.loads(row["progress"])["abandoned"])
        # Too early: the 7 days have not passed.
        self.assertFalse(ms.retry_mission(store, cid, "1.4",
                                         GM + 200 + 6 * DAY))
        self.assertEqual(ms.get_status(store, cid, "1.4"), "failed")
        # After 7 days: a fresh window, old keys cleared.
        self.assertTrue(ms.retry_mission(store, cid, "1.4",
                                        GM + 200 + 7 * DAY))
        row = ms.get_row(store, cid, "1.4")
        self.assertEqual(row["status"], "available")
        self.assertEqual(json.loads(row["progress"]),
                         {"available_at_game_minutes":
                          GM + 200 + 7 * DAY})


class TestMission14(unittest.TestCase):
    def _active_14(self, store, d, cid):
        ms.make_available(store, cid, "1.4", GM)
        ms.accept_mission(store, cid, "1.4", GM + 100)

    def test_sunset_window_and_anchor_complete_1_4(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        self._active_14(store, d, cid)
        sunset = _sunset(d, 0)
        gm = sunset + 30  # inside [sunset, 20:00)
        self.assertTrue(ms.verify_mission_1_4(
            store, d, cid, "d1_riverfront",
            "anchor_tea_stall_riverfront_1", gm))
        self.assertTrue(ms.complete_mission(store, cid, "1.4", gm))
        self.assertEqual(ms.get_status(store, cid, "1.4"), "completed")
        # The sourced reward: the memory event is logged.
        ev = store.row("SELECT * FROM life_events WHERE character_id = ?"
                       " AND event_type = 'first_evening_in_rupsha'",
                       (cid,))
        self.assertIsNotNone(ev)
        self.assertEqual(json.loads(ev["details"])["memory"],
                         "First evening in Rupsha")

    def test_da_gate_opens_on_1_4_completion(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        self.assertFalse(ph.photo_mode_unlocked(store, cid))
        self._active_14(store, d, cid)
        sunset = _sunset(d, 0)
        ms.verify_mission_1_4(store, d, cid, "d1_riverfront",
                              "anchor_tea_stall_riverfront_1",
                              sunset + 30)
        ms.complete_mission(store, cid, "1.4", sunset + 30)
        self.assertTrue(ph.photo_mode_unlocked(store, cid))

    def test_before_sunset_does_not_verify(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        self._active_14(store, d, cid)
        sunset = _sunset(d, 0)
        self.assertFalse(ms.verify_mission_1_4(
            store, d, cid, "d1_riverfront",
            "anchor_tea_stall_riverfront_1", sunset - 60))
        self.assertFalse(ms.complete_mission(store, cid, "1.4",
                                            sunset - 60))

    def test_wrong_zone_or_anchor_does_not_verify(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        self._active_14(store, d, cid)
        sunset = _sunset(d, 0)
        # The market stalls do not verify it: the evening is
        # riverfront (DG §3.6).
        self.assertFalse(ms.verify_mission_1_4(
            store, d, cid, "d1_riverfront",
            "anchor_tea_stall_market_1", sunset + 30))
        self.assertFalse(ms.verify_mission_1_4(
            store, d, cid, "d1_market",
            "anchor_tea_stall_riverfront_1", sunset + 30))

    def test_after_2000_does_not_verify(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        self._active_14(store, d, cid)
        self.assertFalse(ms.verify_mission_1_4(
            store, d, cid, "d1_riverfront",
            "anchor_tea_stall_riverfront_1", 20 * 60))

    def test_verify_needs_an_active_row(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        sunset = _sunset(d, 0)
        # Available but never accepted: no verification.
        ms.make_available(store, cid, "1.4", GM)
        self.assertFalse(ms.verify_mission_1_4(
            store, d, cid, "d1_riverfront",
            "anchor_tea_stall_riverfront_1", sunset + 30))


class TestDeadlines(unittest.TestCase):
    def test_deadline_mission_expires(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        # Mission 4.2 carries deadline_days 30 (GDD-04 §3.2).
        self.assertEqual(ms.deadline_days_for(d, "4.2"), 30)
        ms.make_available(store, cid, "4.2", GM)
        ms.accept_mission(store, cid, "4.2", GM + 100)
        self.assertEqual(ms.expire_deadlines(store, d, GM + 29 * DAY),
                         [])
        self.assertEqual(ms.expire_deadlines(store, d, GM + 30 * DAY),
                         ["4.2"])
        self.assertEqual(ms.get_status(store, cid, "4.2"), "failed")

    def test_1_4_has_no_deadline_and_never_expires(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        self.assertIsNone(ms.deadline_days_for(d, "1.4"))
        ms.make_available(store, cid, "1.4", GM)
        ms.accept_mission(store, cid, "1.4", GM + 100)
        self.assertEqual(ms.expire_deadlines(store, d, GM + 365 * DAY),
                         [])
        self.assertEqual(ms.get_status(store, cid, "1.4"), "active")

    def test_favours_never_carry_a_deadline(self):
        d = data()
        self.assertIsNone(ms.deadline_days_for(
            d, "side:favours:NEX1:480"))


class TestFavourInstances(unittest.TestCase):
    def _lost_item(self, store, owner):
        iid = store.next_id("INV", "inventory_items", "item_instance_id")
        store.insert("inventory_items", item_instance_id=iid,
                     item_type="goods", item_ref="food_basket",
                     owner_character_id=owner,
                     location_property_id=None, state="{}",
                     acquired_at_game_minutes=GM)
        return iid

    def test_create_favour_instance_key_shape(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        giver = make_person(store, age=40, first="Giver")
        key = ms.create_favour_instance(store, d, cid,
                                        "favours", giver, GM)
        self.assertEqual(key, f"side:favours:{giver}:{GM}")
        self.assertEqual(ms.get_status(store, cid, key), "available")
        # The same key twice is one favour, not two.
        self.assertIsNone(ms.create_favour_instance(
            store, d, cid, "favours", giver, GM))

    def test_create_favour_instance_refuses_unknown_type(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        with self.assertRaises(ValueError):
            ms.create_favour_instance(store, d, cid, "not_a_type",
                                      cid, GM)

    def test_lost_item_favour_completes_on_return(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        giver = make_person(store, age=40, first="Giver")
        iid = self._lost_item(store, giver)
        # "Find a lost item" is a subtype within Favours (GDD-04
        # §3), so the instance key carries `favours` and the caller
        # supplies the subtype it generated.
        key = ms.create_favour_instance(store, d, cid,
                                        "favours", giver, GM)
        ms.accept_mission(store, cid, key, GM + 100)
        lid = li.record_loss(store, giver, iid, GM + 200, "d1_market")
        # Lost, not yet returned: not complete.
        self.assertFalse(ms.verify_favour_objectives(
            store, cid, key, GM + 300,
            favour_subtype="find_a_lost_item", lost_item_id=lid))
        li.find_lost_item(store, lid, cid, GM + 400, "d1_market")
        li.return_lost_item(store, lid, GM + 500)
        self.assertTrue(ms.verify_favour_objectives(
            store, cid, key, GM + 600,
            favour_subtype="find_a_lost_item", lost_item_id=lid))
        self.assertTrue(ms.complete_mission(store, cid, key, GM + 700))
        self.assertEqual(ms.get_status(store, cid, key), "completed")

    def test_discovery_favour_completes_on_discovery_row(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        giver = make_person(store, age=40, first="Giver")
        key = ms.create_favour_instance(store, d, cid, "discovery",
                                        giver, GM)
        ms.accept_mission(store, cid, key, GM + 100)
        self.assertFalse(ms.verify_favour_objectives(
            store, cid, key, GM + 200, account_id="ACC1",
            discoverable_id="lm_clock_tower"))
        store.insert("discovery_progress", account_id="ACC1",
                     discoverable_type="landmark",
                     discoverable_id="lm_clock_tower",
                     discovered_at_game_minutes=GM + 200,
                     discovered_in_zone="d1_market")
        self.assertTrue(ms.verify_favour_objectives(
            store, cid, key, GM + 300, account_id="ACC1",
            discoverable_id="lm_clock_tower"))

    def test_favour_verification_needs_its_parameters(self):
        store = make_store()
        d = data()
        cid = make_person(store, age=25, first="Player")
        giver = make_person(store, age=40, first="Giver")
        key = ms.create_favour_instance(store, d, cid,
                                        "favours", giver, GM)
        ms.accept_mission(store, cid, key, GM + 100)
        # No subtype or lost_item_id supplied: the favour cannot
        # verify — the key alone cannot say which kind of favour a
        # `favours` row is.
        self.assertFalse(ms.verify_favour_objectives(store, cid, key,
                                                    GM + 200))
        self.assertFalse(ms.verify_favour_objectives(
            store, cid, key, GM + 200,
            favour_subtype="find_a_lost_item"))
        # A main mission id is not a favour instance.
        self.assertFalse(ms.verify_favour_objectives(store, cid, "1.4",
                                                    GM + 200))


if __name__ == "__main__":
    unittest.main()
