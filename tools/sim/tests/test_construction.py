"""Session 03 Unit 11 — Construction Lifecycle (GDD-08)."""
import os
import tempfile
import unittest

from tools.sim import construction as construction_mod
from tools.sim import zoning as zoning_mod
from tools.sim.engine import Simulation


def _tmp_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


class TestConstruction(unittest.TestCase):
    def setUp(self):
        self.path = _tmp_path()
        self.sim = Simulation(self.path, seed="build-test")
        self.sim.generate_population(120)
        self.store = self.sim.store
        self.data = self.sim.data
        self._force_crew()
        self.gm = 480

    def tearDown(self):
        self.sim.close()
        os.remove(self.path)

    def _force_crew(self):
        people = [r["character_id"] for r in self.store.rows(
            "SELECT character_id FROM characters WHERE is_system = 0"
            " AND died_at_game_minutes IS NULL ORDER BY character_id"
            " LIMIT 5")]
        self.engineer = people[0]
        for cid, prof in zip(people, ("civil_engineer",
                                      "construction_worker",
                                      "construction_worker",
                                      "construction_worker")):
            eid = self.store.next_id("EM", "employments",
                                     "employment_id")
            self.store.insert(
                "employments", employment_id=eid, character_id=cid,
                profession_id=prof, tier=1, wage_per_month=30000,
                started_at_game_minutes=480)
        self.client = people[4]

    def _vacant_lawful_parcel(self):
        from tools.sim import terrain as terrain_mod
        for p in self.store.rows(
                "SELECT * FROM land_parcels WHERE"
                " development_status = 'vacant' ORDER BY parcel_id"):
            if zoning_mod.validate_placement(
                    "residential", p["zone_id"], units=2,
                    area_sqm=p["area_sqm"]):
                continue
            spec = self.data.city_spec(p["city_id"])
            ok, _ = terrain_mod.validate_build(
                terrain_mod.regions_for_spec(spec),
                {"x": p["x"], "z": p["z"], "w": p["w"],
                 "d": p["d"]})
            if ok:
                return p
        return None

    def _start_private_house(self, fund=500000):
        parcel = self._vacant_lawful_parcel()
        self.assertIsNotNone(parcel, "a lawful vacant parcel exists")
        if fund:
            self.store.transfer("SYS-EMPLOYERS", self.client, fund,
                                "seed", self.gm)
        pid = construction_mod.start_project(
            self.store, self.data, city_id=parcel["city_id"],
            kind="new_build", parcel_id=parcel["parcel_id"],
            client_character_id=self.client,
            plan={"property_type": "house", "units": 2, "floors": 1,
                  "tier": 2},
            game_minutes=self.gm, day_index=0)
        return pid, parcel

    def _run_days(self, days, weather="clear"):
        results = []
        for i in range(days):
            self.gm += 1440
            results += construction_mod.daily_progress(
                self.store, self.data, self.sim.rng, i + 1, weather,
                self.gm)
        return results

    def test_boq_estimate_is_exactly_the_gdd08_worked_example(self):
        estimate, scale = construction_mod.estimate_for(
            self.data, {"units": 2, "floors": 1})
        self.assertEqual(scale, 1.0)
        self.assertEqual(estimate, 86700)  # GDD-08 §3 worked total
        stages = {s: construction_mod.stage_material_cost(
            self.data, s, 1.0)
            for s in ("foundation", "frame", "walls", "roof",
                      "finishing")}
        self.assertEqual(stages, {"foundation": 20450,
                                  "frame": 27450, "walls": 13775,
                                  "roof": 19275, "finishing": 5750})

    def test_full_project_completes_and_is_occupied(self):
        engineer_before = self.store.balance(self.engineer)
        pid, parcel = self._start_private_house()
        self._run_days(20)
        proj = self.store.row("SELECT * FROM construction_projects"
                              " WHERE project_id = ?", (pid,))
        self.assertEqual(proj["status"], "occupied")
        self.assertEqual(proj["spent_materials_ncr"], 86700)
        # The engineer keeps exactly the entry fee.
        self.assertEqual(self.store.balance(self.engineer),
                         engineer_before + proj["fee_ncr"])
        building = proj["result_building_id"]
        self.assertIsNotNone(building)
        state = self.store.row("SELECT * FROM building_state WHERE"
                               " building_id = ?", (building,))
        self.assertIsNotNone(state)
        units = self.store.rows("SELECT * FROM properties WHERE"
                                " building_ref = ?", (building,))
        self.assertEqual(len(units), 2)
        self.assertEqual(
            sum(1 for u in units if u["status"] == "rented"), 1)
        plot = self.store.row("SELECT development_status FROM"
                              " land_parcels WHERE parcel_id = ?",
                              (parcel["parcel_id"],))
        self.assertEqual(plot["development_status"], "developed")
        self.assertEqual(self.store.ledger_sum_check(), [])

    def test_storm_halts_outdoor_work(self):
        pid, _parcel = self._start_private_house()
        self._run_days(4)  # planning..approvals -> foundation
        proj = self.store.row("SELECT * FROM construction_projects"
                              " WHERE project_id = ?", (pid,))
        self.assertEqual(proj["stage"], "foundation")
        results = self._run_days(1, weather="storm")
        self.assertTrue(any("weather_halted" in r for r in results))
        after = self.store.row("SELECT * FROM construction_projects"
                               " WHERE project_id = ?", (pid,))
        self.assertEqual(after["stage_day"], proj["stage_day"])

    def test_unfunded_client_freezes_at_financing(self):
        pid, _parcel = self._start_private_house(fund=0)
        results = self._run_days(5)
        proj = self.store.row("SELECT * FROM construction_projects"
                              " WHERE project_id = ?", (pid,))
        self.assertEqual(proj["stage"], "financing")
        self.assertEqual(proj["funding_ncr"], 0)
        self.assertTrue(any("stalled_funding" in r for r in results))

    def test_absent_engineer_means_uninspected_stages(self):
        pid, _parcel = self._start_private_house()
        self._run_days(3)  # funding lands on the financing day
        self.store.execute(
            "UPDATE employments SET ended_at_game_minutes = ?"
            " WHERE character_id = ? AND profession_id ="
            " 'civil_engineer'", (self.gm, self.engineer))
        self._run_days(20)
        proj = self.store.row("SELECT * FROM construction_projects"
                              " WHERE project_id = ?", (pid,))
        self.assertIn(proj["status"], ("completed", "occupied"))
        import json
        inspections = json.loads(proj["inspections"])
        self.assertFalse(inspections["foundation"]["inspected"])

    def test_density_blind_plan_is_rejected(self):
        parcel = self._vacant_lawful_parcel()
        with self.assertRaises(ValueError):
            construction_mod.start_project(
                self.store, self.data, city_id=parcel["city_id"],
                kind="new_build", parcel_id=parcel["parcel_id"],
                client_character_id=self.client,
                plan={"property_type": "apartment", "units": 500,
                      "floors": 1, "tier": 2},
                game_minutes=self.gm, day_index=0)


if __name__ == "__main__":
    unittest.main()
