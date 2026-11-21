"""Unit 04 — Daily Life: template instantiation, full-day coverage,
fixed per-NPC jitter, Friday weekend rules, needs bending, weather
interrupts, rest days."""
import unittest

from tools.sim.tests.common import data, rng
from tools.sim import scheduler

VOCAB = {"sleep", "home", "commute", "work", "break", "errand",
         "leisure", "study"}
FULL_NEEDS = {"hunger": 90, "thirst": 90, "sleep": 90, "rest": 90,
              "safety": 90, "social": 90, "healthcare": 90,
              "financial": 90, "education": 90, "development": 90}


def ctx_for(pid, cid="NEX000001"):
    d = data()
    if pid in d.life_stage_templates:
        return {"character_id": cid, "template_id": pid,
                "is_life_stage": True, "home_zone": "d1_old_town",
                "workplace_zone": "d1_old_town"}
    return {"character_id": cid, "template_id": pid,
            "is_life_stage": False, "home_zone": "d1_old_town",
            "workplace_zone": d.professions[pid]["workplace_zone"]}


class TestScheduler(unittest.TestCase):
    def test_coverage_every_template(self):
        d = data()
        ids = list(d.professions.keys()) + list(d.life_stage_templates)
        for pid in ids:
            blocks, _ = scheduler.instantiate(d, ctx_for(pid), 0, rng(),
                                              needs=FULL_NEEDS)
            total = sum(b["end"] - b["start"] for b in blocks)
            self.assertEqual(total, 1440, pid)
            for prev, nxt in zip(blocks, blocks[1:]):
                self.assertEqual(prev["end"], nxt["start"], pid)
            for b in blocks:
                self.assertIn(b["activity"], VOCAB, pid)
                self.assertTrue(b["zone"].startswith("d1_"), pid)

    def test_jitter_fixed_per_npc(self):
        r = rng()
        self.assertEqual(scheduler.jitter_for(r, "NEX000001"),
                         scheduler.jitter_for(r, "NEX000001"))
        values = {scheduler.jitter_for(r, f"NEX{i:06d}") for i in range(30)}
        self.assertGreater(len(values), 5)
        for v in values:
            self.assertTrue(-20 <= v <= 20)

    def test_friday_rules(self):
        d = data()
        # Civil engineers do not work Fridays (site visits aside).
        blocks, _ = scheduler.instantiate(d, ctx_for("civil_engineer"),
                                          4, rng(), needs=FULL_NEEDS)
        self.assertNotIn("work", {b["activity"] for b in blocks})
        # Construction stops at 12:30 (+ jitter at most 20 min).
        blocks, _ = scheduler.instantiate(
            d, ctx_for("construction_worker"), 4, rng(), needs=FULL_NEEDS)
        for b in blocks:
            if b["activity"] == "work":
                self.assertLessEqual(b["end"] - 4 * 1440, 770)
        # Teachers run a Saturday market errand.
        blocks, _ = scheduler.instantiate(d, ctx_for("teacher"), 5, rng(),
                                          needs=FULL_NEEDS)
        self.assertTrue(any(b["activity"] == "errand"
                            and b["location"] == "market" for b in blocks))

    def test_needs_bending_food(self):
        blocks = [{"start": 600, "end": 800, "activity": "home",
                   "location": "home"}]
        needs = dict(FULL_NEEDS, hunger=20)
        out = scheduler._bend_for_needs([dict(b) for b in blocks], needs,
                                        None, False)
        self.assertTrue(any(b["activity"] == "errand"
                            and b.get("need_bent") == "food" for b in out))
        needs = dict(FULL_NEEDS, hunger=90)
        out = scheduler._bend_for_needs([dict(b) for b in blocks], needs,
                                        None, False)
        self.assertFalse(any(b["activity"] == "errand" for b in out))

    def test_needs_bending_social_anchor(self):
        blocks = [{"start": 1080, "end": 1200, "activity": "leisure",
                   "location": "park"}]
        needs = dict(FULL_NEEDS, social=20)
        out = scheduler._bend_for_needs([dict(b) for b in blocks], needs,
                                        None, False)
        self.assertEqual(out[0]["location"], "tea_stall")

    def test_weather_interrupts(self):
        d = data()
        storm = d.weather_presets["storm"]["gameplay_effects"]
        blocks, _ = scheduler.instantiate(
            d, ctx_for("construction_worker"), 0, rng(), needs=FULL_NEEDS,
            weather_effects=storm)
        self.assertNotIn("work", {b["activity"] for b in blocks})
        rain = d.weather_presets["rain"]["gameplay_effects"]
        blocks, _ = scheduler.instantiate(
            d, ctx_for("teacher"), 0, rng(), needs=FULL_NEEDS,
            weather_effects=rain)
        for b in blocks:
            if b.get("weather") == "seek_cover":
                self.assertEqual(b["location"], "home")

    def test_rest_day_removes_work(self):
        d = data()
        blocks, _ = scheduler.instantiate(d, ctx_for("doctor"), 0, rng(),
                                          needs=FULL_NEEDS, rest_day=True)
        self.assertNotIn("work", {b["activity"] for b in blocks})


if __name__ == "__main__":
    unittest.main()
