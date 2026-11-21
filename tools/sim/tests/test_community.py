"""Session 02 Unit 05 — Community Engine: zone communities, synced
membership, participation, leadership and derived issues."""
import unittest

from tools.sim.tests.common import (data, employ, make_household,
                                    make_person, make_store, rng)
from tools.sim import community
from tools.sim import family_economy as fe
from tools.sim import memory as memory_mod


class TestCommunity(unittest.TestCase):
    def _world(self):
        store = make_store()
        d = data()
        a = make_person(store, age=40, first="Elder1")
        b = make_person(store, age=35, first="Adult1")
        c = make_person(store, age=33, first="Adult2")
        hid, _ = make_household(store, [a, b, c])  # d1_midtown
        employ(store, d, a, "teacher", tier=2)
        return store, d, (a, b, c), hid

    def test_membership_syncs_to_residence(self):
        store, d, people, hid = self._world()
        zones = community.ensure_communities(store, d, 480)
        self.assertEqual(len(zones), 10)
        members = store.rows("SELECT character_id FROM community_members"
                             " WHERE community_id = 'd1_midtown'"
                             " AND left_at_game_minutes IS NULL")
        self.assertEqual({m["character_id"] for m in members},
                         set(people))
        view = community.community_view(store, d, "d1_midtown")
        names = {f["name"] for f in view["facilities"]}
        self.assertTrue(any("Apartment" in n or "Flat" in n
                            for n in names))

    def test_weekly_update_population_leader_participation(self):
        store, d, people, hid = self._world()
        a = people[0]
        memory_mod.log_life_event(store, a, "neighbour_meeting", 900,
                                  other_character_id=people[1])
        summary = community.weekly_update(store, d, rng(), 1000)
        mid = summary["d1_midtown"]
        self.assertEqual(mid["population"], 3)
        self.assertGreater(mid["participation_rate"], 0)
        self.assertEqual(mid["leader"], a)  # employed, 30+, respected
        row = store.row("SELECT * FROM communities"
                        " WHERE community_id = 'd1_midtown'")
        self.assertEqual(row["leader_character_id"], a)

    def test_issues_derived_from_facts(self):
        store, d, people, hid = self._world()
        hid2, _ = make_household(
            store, [make_person(store, age=30, first="Debtor")])
        for h in (hid, hid2):
            fe.record_month(store, h, 1, 1000, income=1000, food=1,
                            housing=1, transport=1, other=1,
                            emergency=500)
        summary = community.weekly_update(store, d, rng(), 2000)
        kinds = {i["kind"] for i in summary["d1_midtown"]["issues"]}
        self.assertIn("financial_hardship", kinds)

    def test_membership_follows_relocation(self):
        store, d, people, hid = self._world()
        community.ensure_communities(store, d, 480)
        store.execute("UPDATE households SET district_id = 'd1_park'"
                      " WHERE household_id = ?", (hid,))
        community.ensure_communities(store, d, 5000)
        left = store.row("SELECT left_at_game_minutes FROM"
                         " community_members WHERE community_id ="
                         " 'd1_midtown' AND character_id = ?",
                         (people[0],))
        self.assertIsNotNone(left["left_at_game_minutes"])
        joined = store.row("SELECT * FROM community_members"
                           " WHERE community_id = 'd1_park'"
                           " AND character_id = ?", (people[0],))
        self.assertIsNotNone(joined)


if __name__ == "__main__":
    unittest.main()
