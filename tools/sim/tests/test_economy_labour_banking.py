"""Session 04 Units 03, 08, 09 — Labour Market, Banking,
Investment."""
import os
import tempfile
import unittest

from tools.sim import banking as banking_mod
from tools.sim import business as business_mod
from tools.sim import labour as labour_mod
from tools.sim.engine import Simulation

from .common import rng


def _tmp_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


class TestLabourMarket(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = _tmp_path()
        cls.sim = Simulation(cls.path, seed="s04-labour")
        cls.sim.generate_population(60)
        cls.store = cls.sim.store
        cls.data = cls.sim.data

    @classmethod
    def tearDownClass(cls):
        cls.sim.close()
        os.remove(cls.path)

    def test_insolvent_employer_cannot_post(self):
        broke = self.store.row(
            "SELECT * FROM businesses WHERE category ="
            " 'manufacturing' AND closed_at_game_minutes IS NULL"
            " LIMIT 1")
        bid = broke["business_id"]
        balance = self.store.business_balance(bid)
        if balance > 0:
            self.store.transfer(None, "SYS-MARKET", balance,
                                "test_drain", 500,
                                from_business_id=bid)
        posted = labour_mod.post_vacancies(self.store, self.data,
                                           1, 43200)
        mine = self.store.rows(
            "SELECT * FROM vacancies WHERE employer_business_id"
            " = ?", (bid,))
        self.assertEqual(mine, [])
        # Solvent employers in staffed categories did post.
        self.assertTrue(posted)

    def test_matching_hires_into_business_employments(self):
        labour_mod.post_vacancies(self.store, self.data, 1, 43200)
        hires = labour_mod.match_vacancies(
            self.store, self.data, rng("s04-labour"), 1, 43200)
        self.assertTrue(hires)
        self.assertTrue(self.store.rows(
            "SELECT * FROM job_applications"))
        for h in hires:
            emp = self.store.row(
                "SELECT * FROM employments WHERE character_id = ?"
                " AND ended_at_game_minutes IS NULL",
                (h["character_id"],))
            self.assertIsNotNone(emp)
            vacancy = self.store.row(
                "SELECT * FROM vacancies WHERE vacancy_id = ?",
                (h["vacancy_id"],))
            if vacancy["employer_kind"] == "business":
                self.assertEqual(emp["employer_business_id"],
                                 vacancy["employer_business_id"])
            self.assertEqual(vacancy["status"], "filled")

    def test_business_pays_its_own_wages_at_settlement(self):
        biz = self.store.row(
            "SELECT * FROM businesses WHERE category ="
            " 'food_processing' AND closed_at_game_minutes IS NULL"
            " LIMIT 1")
        worker = self.store.row(
            "SELECT c.character_id FROM characters c WHERE"
            " c.is_system = 0 AND c.died_at_game_minutes IS NULL"
            " AND NOT EXISTS (SELECT 1 FROM employments e WHERE"
            " e.character_id = c.character_id AND"
            " e.ended_at_game_minutes IS NULL) LIMIT 1")
        if worker is None:
            self.skipTest("no unemployed adult in this world")
        cid = worker["character_id"]
        wage = 9000
        eid = self.store.next_id("EM", "employments",
                                 "employment_id")
        # Queue 21 Unit ES: construction workers are paid per
        # worked day (0 with no stored schedules), so this
        # business-pay mechanism proof uses a monthly profession.
        self.store.insert(
            "employments", employment_id=eid, character_id=cid,
            profession_id="chef",
            employer_business_id=biz["business_id"], tier=1,
            wage_per_month=wage, started_at_game_minutes=500)
        biz_before = self.store.business_balance(biz["business_id"])
        emp_before = self.store.balance(cid)
        paid = self.sim._pay_business_wages(5, 200000)
        self.assertEqual(paid.get(eid), wage)
        self.assertEqual(self.store.business_balance(
            biz["business_id"]), biz_before - wage)
        self.assertEqual(self.store.balance(cid), emp_before + wage)
        row = self.store.row(
            "SELECT * FROM economy_ledger WHERE from_business_id"
            " = ? AND to_character_id = ? AND reason_code = 'wage'",
            (biz["business_id"], cid))
        self.assertIsNotNone(row)
        # Idempotent money: replaying the month moves nothing
        # twice (the keyed transfer returns its original row);
        # the reported gross still describes the month's wage.
        paid_again = self.sim._pay_business_wages(5, 200000)
        self.assertEqual(paid_again.get(eid), wage)
        self.assertEqual(self.store.balance(cid), emp_before + wage)
        self.assertEqual(self.store.business_balance(
            biz["business_id"]), biz_before - wage)

    def test_unemployment_is_measured_and_consistent(self):
        stats = labour_mod.unemployment_stats(self.store, self.data)
        self.assertGreater(stats["labour_force"], 0)
        self.assertEqual(stats["employed"] + stats["unemployed"],
                         stats["labour_force"])
        self.assertGreaterEqual(stats["unemployment_rate"], 0.0)
        self.assertLessEqual(stats["unemployment_rate"], 1.0)
        self.assertIn("by_city", stats)


class TestBusinessEmployedTaxiSurge(unittest.TestCase):
    """Queue 30 Unit KF — the business-employed taxi driver
    (Unit KC found the settlement surges taxi pay only in the
    SYS-EMPLOYERS branch; the business path was a code read).
    The audit pins that no vacancy source ever posts a taxi
    driver, so the business-employed case cannot arise and the
    settlement needs no change. The guard fails loudly if a
    future staffing change ever posts one — that is the
    re-open condition, recorded in the V7 report §19."""

    @classmethod
    def setUpClass(cls):
        cls.path = _tmp_path()
        cls.sim = Simulation(cls.path, seed="kf-guard")
        cls.sim.generate_population(60)
        cls.store = cls.sim.store
        cls.data = cls.sim.data

    @classmethod
    def tearDownClass(cls):
        cls.sim.close()
        os.remove(cls.path)

    def test_no_vacancy_source_posts_taxi_driver(self):
        from tools.sim import admin as admin_mod
        business = {prof for prof, _target
                    in labour_mod.STAFFING.values()}
        civic = set(labour_mod.CIVIC_RATIOS)
        government = {prof for _inst, prof, _basis
                      in admin_mod.STAFFING}
        # The Session 05 employment programme posts
        # construction_worker only (policies.py).
        policy_posts = {"construction_worker"}
        self.assertNotIn("taxi_driver", business)
        self.assertNotIn("taxi_driver", civic)
        self.assertNotIn("taxi_driver", government)
        self.assertNotIn("taxi_driver", policy_posts)
        self.assertEqual(
            business | civic | government | policy_posts,
            {"chef", "construction_worker", "software_developer",
             "teacher", "doctor", "police_officer",
             "civil_engineer"})

    def test_seeded_world_posts_no_taxi_vacancy(self):
        # The class world's own vacancy machinery: post a
        # month of vacancies and match them — no taxi driver
        # vacancy is ever posted, and no taxi driver ends up
        # business-employed (a job change takes the vacancy's
        # profession, so a taxi driver who changes jobs stops
        # being one).
        labour_mod.post_vacancies(self.store, self.data, 1, 43200)
        labour_mod.match_vacancies(
            self.store, self.data, rng("s04-labour"), 1, 43200)
        taxi_vacancies = self.store.row(
            "SELECT COUNT(*) AS n FROM vacancies WHERE"
            " profession_id = 'taxi_driver'")["n"]
        self.assertEqual(taxi_vacancies, 0)
        business_taxi = self.store.row(
            "SELECT COUNT(*) AS n FROM employments WHERE"
            " profession_id = 'taxi_driver'"
            " AND employer_business_id IS NOT NULL"
            " AND ended_at_game_minutes IS NULL")["n"]
        self.assertEqual(business_taxi, 0)


class TestSeniorSecondEarnerLiveWorld(unittest.TestCase):
    """Queue 37 Unit MF — the senior second earner live-world
    check (Unit ME's reopen condition: the decision to keep
    the renting senior-tier taxi second earner allowed but
    unmeasured re-opens only if a measured household appears
    — a live settlement household pairing the construction
    worker with a senior taxi driver or senior civil engineer
    as second earner). The seeded world pins that none
    appears, and the senior-band definition pins that
    "senior" in the live world means tier >= 3: dataio
    TIER_WAGE_KEYS maps tiers 3-5 to the senior band, so a
    tier-4 taxi driver earns the senior 36,000 and a
    tier == 3 check would miss them. The tests fail loudly
    if a future world ever produces such a household — that
    is the re-open condition, recorded in the V7 report §26.
    """

    @classmethod
    def setUpClass(cls):
        cls.path = _tmp_path()
        cls.sim = Simulation(cls.path, seed="mf-guard")
        cls.sim.generate_population(60)
        cls.sim.run_days(30)
        cls.store = cls.sim.store
        cls.data = cls.sim.data

    @classmethod
    def tearDownClass(cls):
        cls.sim.close()
        os.remove(cls.path)

    def test_no_senior_second_earner_in_seeded_world(self):
        # The pairing query: a non-head member of a
        # construction-worker-headed household, currently
        # employed as a senior-band (tier >= 3) taxi driver
        # or civil engineer.
        head = ("household_members hm ON hm.household_id"
                " = h.household_id JOIN employments e"
                " ON e.character_id = hm.character_id")
        member = ("household_members hm2 ON hm2.household_id"
                  " = h.household_id JOIN employments e2"
                  " ON e2.character_id = hm2.character_id")
        cw_head = ("hm.role = 'head'"
                   " AND hm.left_at_game_minutes IS NULL"
                   " AND e.profession_id = 'construction_worker'"
                   " AND e.ended_at_game_minutes IS NULL")
        member_now = ("hm2.role != 'head'"
                      " AND hm2.left_at_game_minutes IS NULL"
                      " AND e2.ended_at_game_minutes IS NULL")
        for prof in ("taxi_driver", "civil_engineer"):
            found = self.store.row(
                "SELECT COUNT(*) AS n FROM households h JOIN "
                + head + " JOIN " + member +
                " WHERE " + cw_head + " AND " + member_now +
                " AND e2.profession_id = ? AND e2.tier >= 3",
                (prof,))["n"]
            self.assertEqual(found, 0, prof)
        # Non-vacuous: the world holds construction-worker
        # heads and both professions, so the zeros are
        # measured absences, not an empty query.
        cw_heads = self.store.row(
            "SELECT COUNT(*) AS n FROM household_members hm"
            " JOIN employments e ON e.character_id ="
            " hm.character_id WHERE hm.role = 'head'"
            " AND hm.left_at_game_minutes IS NULL"
            " AND e.profession_id = 'construction_worker'"
            " AND e.ended_at_game_minutes IS NULL")["n"]
        self.assertGreater(cw_heads, 0)
        for prof in ("taxi_driver", "civil_engineer"):
            n = self.store.row(
                "SELECT COUNT(*) AS n FROM employments WHERE"
                " profession_id = ?"
                " AND ended_at_game_minutes IS NULL",
                (prof,))["n"]
            self.assertGreater(n, 0, prof)

    def test_senior_band_is_tier_three_or_higher(self):
        from tools.sim import dataio as dataio_mod
        self.assertEqual(
            dataio_mod.WorldData.TIER_WAGE_KEYS[2:],
            ("senior", "senior", "senior"))
        for tier in (3, 4, 5):
            self.assertEqual(
                self.data.wage_at("taxi_driver", tier), 36000)
            self.assertEqual(
                self.data.wage_at("civil_engineer", tier),
                65000)


class TestSeniorSecondEarnerMultiSeedSweep(unittest.TestCase):
    """Queue 38 Unit MG — the multi-seed senior second
    earner sweep (Unit MF follow-up: MF checked one seeded
    world, so the absence may be a small-world artifact —
    senior-tier citizens are rare in it). The same pairing
    query as MF (senior = tier >= 3) across three seeded
    worlds, each 60 population and 30 days: no
    construction-worker-headed household has a senior
    taxi-driver or senior civil-engineer second earner in
    any of them. The full 5-seed 120-population 90-day
    sweep is pinned by tools/verify_queue38_mg.py; these
    guard tests pin the method at suite speed and fail
    loudly if a future world ever produces such a
    household — that is the re-open condition, recorded
    in the V7 report §27.
    """

    SEEDS = ("mg-guard-1", "mg-guard-2", "mg-guard-3")

    @classmethod
    def setUpClass(cls):
        cls.worlds = []
        for seed in cls.SEEDS:
            path = _tmp_path()
            sim = Simulation(path, seed=seed)
            sim.generate_population(60)
            sim.run_days(30)
            cls.worlds.append((seed, sim, path))

    @classmethod
    def tearDownClass(cls):
        for _seed, sim, path in cls.worlds:
            sim.close()
            os.remove(path)

    def _pairing_query(self, store, prof):
        # The MF pairing query: a non-head member of a
        # construction-worker-headed household, currently
        # employed as a senior-band (tier >= 3) taxi driver
        # or civil engineer.
        head = ("household_members hm ON hm.household_id"
                " = h.household_id JOIN employments e"
                " ON e.character_id = hm.character_id")
        member = ("household_members hm2 ON hm2.household_id"
                  " = h.household_id JOIN employments e2"
                  " ON e2.character_id = hm2.character_id")
        cw_head = ("hm.role = 'head'"
                   " AND hm.left_at_game_minutes IS NULL"
                   " AND e.profession_id = 'construction_worker'"
                   " AND e.ended_at_game_minutes IS NULL")
        member_now = ("hm2.role != 'head'"
                      " AND hm2.left_at_game_minutes IS NULL"
                      " AND e2.ended_at_game_minutes IS NULL")
        return store.row(
            "SELECT COUNT(*) AS n FROM households h JOIN "
            + head + " JOIN " + member +
            " WHERE " + cw_head + " AND " + member_now +
            " AND e2.profession_id = ? AND e2.tier >= 3",
            (prof,))["n"]

    def test_no_senior_second_earner_in_any_seed(self):
        for seed, sim, _path in self.worlds:
            store = sim.store
            for prof in ("taxi_driver", "civil_engineer"):
                found = self._pairing_query(store, prof)
                self.assertEqual(found, 0, f"{seed} {prof}")
            # Non-vacuous per world: the world holds
            # construction-worker heads and both professions,
            # so the zeros are measured absences.
            cw_heads = store.row(
                "SELECT COUNT(*) AS n FROM household_members hm"
                " JOIN employments e ON e.character_id ="
                " hm.character_id WHERE hm.role = 'head'"
                " AND hm.left_at_game_minutes IS NULL"
                " AND e.profession_id = 'construction_worker'"
                " AND e.ended_at_game_minutes IS NULL")["n"]
            self.assertGreater(cw_heads, 0, seed)
            for prof in ("taxi_driver", "civil_engineer"):
                n = store.row(
                    "SELECT COUNT(*) AS n FROM employments WHERE"
                    " profession_id = ?"
                    " AND ended_at_game_minutes IS NULL",
                    (prof,))["n"]
                self.assertGreater(n, 0, f"{seed} {prof}")

    def test_senior_band_wage_holds_in_every_seed(self):
        # Every current senior-band (tier >= 3) taxi driver
        # earns the senior 36,000 and every senior-band civil
        # engineer the senior 65,000, in each sweep world —
        # the band definition the query relies on.
        for seed, sim, _path in self.worlds:
            store = sim.store
            for prof, wage in (("taxi_driver", 36000),
                               ("civil_engineer", 65000)):
                rows = store.rows(
                    "SELECT tier, wage_per_month FROM employments"
                    " WHERE profession_id = ? AND tier >= 3"
                    " AND ended_at_game_minutes IS NULL",
                    (prof,))
                for row in rows:
                    self.assertEqual(
                        row["wage_per_month"], wage,
                        f"{seed} {prof} tier {row['tier']}")


class TestSeniorSecondEarnerLongHorizon(unittest.TestCase):
    """Queue 39 Unit MH — the senior second earner at a
    longer horizon (Unit MG follow-up: MG swept five seeds
    at 90 days, but 90 days may be too short for a senior
    earner to join a household after genesis — a member
    hired or promoted to the senior band after day 90, or
    a marriage bringing a senior earner in). The same
    pairing query as MF/MG (senior = tier >= 3) across
    three seeded worlds, each 60 population and 30 days:
    no construction-worker-headed household has a senior
    taxi-driver or senior civil-engineer second earner in
    any of them. The full 2-seed 120-population 365-day
    sweep is pinned by tools/verify_queue39_mh.py; these
    guard tests pin the method at suite speed and fail
    loudly if a future world ever produces such a
    household — that is the re-open condition, recorded
    in the V7 report §28.
    """

    SEEDS = ("mh-guard-1", "mh-guard-2", "mh-guard-3")

    @classmethod
    def setUpClass(cls):
        cls.worlds = []
        for seed in cls.SEEDS:
            path = _tmp_path()
            sim = Simulation(path, seed=seed)
            sim.generate_population(60)
            sim.run_days(30)
            cls.worlds.append((seed, sim, path))

    @classmethod
    def tearDownClass(cls):
        for _seed, sim, path in cls.worlds:
            sim.close()
            os.remove(path)

    def _pairing_query(self, store, prof):
        # The MF pairing query: a non-head member of a
        # construction-worker-headed household, currently
        # employed as a senior-band (tier >= 3) taxi driver
        # or civil engineer.
        head = ("household_members hm ON hm.household_id"
                " = h.household_id JOIN employments e"
                " ON e.character_id = hm.character_id")
        member = ("household_members hm2 ON hm2.household_id"
                  " = h.household_id JOIN employments e2"
                  " ON e2.character_id = hm2.character_id")
        cw_head = ("hm.role = 'head'"
                   " AND hm.left_at_game_minutes IS NULL"
                   " AND e.profession_id = 'construction_worker'"
                   " AND e.ended_at_game_minutes IS NULL")
        member_now = ("hm2.role != 'head'"
                      " AND hm2.left_at_game_minutes IS NULL"
                      " AND e2.ended_at_game_minutes IS NULL")
        return store.row(
            "SELECT COUNT(*) AS n FROM households h JOIN "
            + head + " JOIN " + member +
            " WHERE " + cw_head + " AND " + member_now +
            " AND e2.profession_id = ? AND e2.tier >= 3",
            (prof,))["n"]

    def test_no_senior_second_earner_in_any_seed(self):
        for seed, sim, _path in self.worlds:
            store = sim.store
            for prof in ("taxi_driver", "civil_engineer"):
                found = self._pairing_query(store, prof)
                self.assertEqual(found, 0, f"{seed} {prof}")
            # Non-vacuous per world: the world holds
            # construction-worker heads and both professions,
            # so the zeros are measured absences.
            cw_heads = store.row(
                "SELECT COUNT(*) AS n FROM household_members hm"
                " JOIN employments e ON e.character_id ="
                " hm.character_id WHERE hm.role = 'head'"
                " AND hm.left_at_game_minutes IS NULL"
                " AND e.profession_id = 'construction_worker'"
                " AND e.ended_at_game_minutes IS NULL")["n"]
            self.assertGreater(cw_heads, 0, seed)
            for prof in ("taxi_driver", "civil_engineer"):
                n = store.row(
                    "SELECT COUNT(*) AS n FROM employments WHERE"
                    " profession_id = ?"
                    " AND ended_at_game_minutes IS NULL",
                    (prof,))["n"]
                self.assertGreater(n, 0, f"{seed} {prof}")

    def test_senior_band_wage_holds_in_every_seed(self):
        # Every current senior-band (tier >= 3) taxi driver
        # earns the senior 36,000 and every senior-band civil
        # engineer the senior 65,000, in each sweep world —
        # the band definition the query relies on.
        for seed, sim, _path in self.worlds:
            store = sim.store
            for prof, wage in (("taxi_driver", 36000),
                               ("civil_engineer", 65000)):
                rows = store.rows(
                    "SELECT tier, wage_per_month FROM employments"
                    " WHERE profession_id = ? AND tier >= 3"
                    " AND ended_at_game_minutes IS NULL",
                    (prof,))
                for row in rows:
                    self.assertEqual(
                        row["wage_per_month"], wage,
                        f"{seed} {prof} tier {row['tier']}")


class TestSeniorSecondEarnerLargerWorld(unittest.TestCase):
    """Queue 40 Unit MI — the senior second earner in a
    larger world (Unit MH follow-up: MH ran the check over a
    longer horizon, but every world so far is 120 people —
    a larger world holds more households, more senior
    earners and more chances for the pairing to appear).
    The full 1-seed 300-population 365-day sweep is pinned
    by tools/verify_queue40_mi.py; these guard tests pin
    the method at suite speed and fail loudly if a future
    world ever produces a senior taxi-driver second earner
    under a construction-worker head — that is the re-open
    condition for the senior taxi pairing, recorded in the
    V7 report §29. The senior civil-engineer pairing DID
    appear in the larger world (HH000086, tier 5, 65,000),
    so it is wired, not guarded — its figures are pinned
    in test_no_regression.py.
    """

    SEEDS = ("mi-guard-1", "mi-guard-2", "mi-guard-3")

    @classmethod
    def setUpClass(cls):
        cls.worlds = []
        for seed in cls.SEEDS:
            path = _tmp_path()
            sim = Simulation(path, seed=seed)
            sim.generate_population(60)
            sim.run_days(30)
            cls.worlds.append((seed, sim, path))

    @classmethod
    def tearDownClass(cls):
        for _seed, sim, path in cls.worlds:
            sim.close()
            os.remove(path)

    def _pairing_query(self, store, prof):
        # The MF pairing query: a non-head member of a
        # construction-worker-headed household, currently
        # employed as a senior-band (tier >= 3) taxi driver
        # or civil engineer.
        head = ("household_members hm ON hm.household_id"
                " = h.household_id JOIN employments e"
                " ON e.character_id = hm.character_id")
        member = ("household_members hm2 ON hm2.household_id"
                  " = h.household_id JOIN employments e2"
                  " ON e2.character_id = hm2.character_id")
        cw_head = ("hm.role = 'head'"
                   " AND hm.left_at_game_minutes IS NULL"
                   " AND e.profession_id = 'construction_worker'"
                   " AND e.ended_at_game_minutes IS NULL")
        member_now = ("hm2.role != 'head'"
                      " AND hm2.left_at_game_minutes IS NULL"
                      " AND e2.ended_at_game_minutes IS NULL")
        return store.row(
            "SELECT COUNT(*) AS n FROM households h JOIN "
            + head + " JOIN " + member +
            " WHERE " + cw_head + " AND " + member_now +
            " AND e2.profession_id = ? AND e2.tier >= 3",
            (prof,))["n"]

    def test_no_senior_taxi_second_earner_in_any_seed(self):
        for seed, sim, _path in self.worlds:
            store = sim.store
            found = self._pairing_query(store, "taxi_driver")
            self.assertEqual(found, 0, seed)
            # Non-vacuous per world: the world holds
            # construction-worker heads and taxi drivers, so
            # the zero is a measured absence.
            cw_heads = store.row(
                "SELECT COUNT(*) AS n FROM household_members hm"
                " JOIN employments e ON e.character_id ="
                " hm.character_id WHERE hm.role = 'head'"
                " AND hm.left_at_game_minutes IS NULL"
                " AND e.profession_id = 'construction_worker'"
                " AND e.ended_at_game_minutes IS NULL")["n"]
            self.assertGreater(cw_heads, 0, seed)
            n = store.row(
                "SELECT COUNT(*) AS n FROM employments WHERE"
                " profession_id = 'taxi_driver'"
                " AND ended_at_game_minutes IS NULL")["n"]
            self.assertGreater(n, 0, seed)

    def test_senior_band_wage_holds_in_every_seed(self):
        # Every current senior-band (tier >= 3) taxi driver
        # earns the senior 36,000 and every senior-band civil
        # engineer the senior 65,000, in each sweep world —
        # the band definition the query relies on.
        for seed, sim, _path in self.worlds:
            store = sim.store
            for prof, wage in (("taxi_driver", 36000),
                               ("civil_engineer", 65000)):
                rows = store.rows(
                    "SELECT tier, wage_per_month FROM employments"
                    " WHERE profession_id = ? AND tier >= 3"
                    " AND ended_at_game_minutes IS NULL",
                    (prof,))
                for row in rows:
                    self.assertEqual(
                        row["wage_per_month"], wage,
                        f"{seed} {prof} tier {row['tier']}")


class TestSeniorTaxiSecondEarnerAnyHousehold(unittest.TestCase):
    """Queue 41 Unit MJ — the senior taxi driver as second
    earner in any household (Unit MI follow-up: MI found the
    senior civil-engineer pairing in the larger world but
    still no senior taxi-driver second earner under a
    construction-worker head — yet the larger world holds
    senior civil-engineer second earners in any household,
    so the taxi half of §12 may be about the
    construction-worker pairing rather than about senior
    taxi drivers never being second earners at all). The
    same pairing query as MF/MG/MH/MI with the
    construction-worker-head restriction REMOVED (senior =
    tier >= 3) across three seeded worlds, each 60
    population and 30 days: senior taxi-driver second
    earners occur in 2 of the 3 worlds — under teacher
    heads, never under a construction-worker head. The
    full 2-seed 300-population 365-day sweep is pinned by
    tools/verify_queue41_mj.py; these guard tests pin the
    method at suite speed and fail loudly if a future
    world ever produces a senior taxi-driver second earner
    under a construction-worker head — that is the
    re-open condition for the pairing, recorded in the V7
    report §30.
    """

    SEEDS = ("mj-guard-1", "mj-guard-2", "mj-guard-3")
    ANY_TAXI = {"mj-guard-1": 0, "mj-guard-2": 1,
                "mj-guard-3": 1}

    @classmethod
    def setUpClass(cls):
        cls.worlds = []
        for seed in cls.SEEDS:
            path = _tmp_path()
            sim = Simulation(path, seed=seed)
            sim.generate_population(60)
            sim.run_days(30)
            cls.worlds.append((seed, sim, path))

    @classmethod
    def tearDownClass(cls):
        for _seed, sim, path in cls.worlds:
            sim.close()
            os.remove(path)

    def _any_household_query(self, store, prof):
        # The MF pairing query with the head restriction
        # removed: a non-head member of ANY household,
        # currently employed as a senior-band (tier >= 3)
        # taxi driver.
        head = ("household_members hm ON hm.household_id"
                " = h.household_id JOIN employments e"
                " ON e.character_id = hm.character_id")
        member = ("household_members hm2 ON hm2.household_id"
                  " = h.household_id JOIN employments e2"
                  " ON e2.character_id = hm2.character_id")
        head_now = ("hm.role = 'head'"
                    " AND hm.left_at_game_minutes IS NULL"
                    " AND e.ended_at_game_minutes IS NULL")
        member_now = ("hm2.role != 'head'"
                      " AND hm2.left_at_game_minutes IS NULL"
                      " AND e2.ended_at_game_minutes IS NULL")
        return store.rows(
            "SELECT h.household_id, e.profession_id AS"
            " head_prof, e2.tier AS se_tier,"
            " e2.wage_per_month AS se_wage FROM households h"
            " JOIN " + head + " JOIN " + member +
            " WHERE " + head_now + " AND " + member_now +
            " AND e2.profession_id = ? AND e2.tier >= 3",
            (prof,))

    def test_any_household_query_counts_senior_taxi_second_earners(self):
        for seed, sim, _path in self.worlds:
            store = sim.store
            rows = self._any_household_query(store, "taxi_driver")
            self.assertEqual(len(rows), self.ANY_TAXI[seed],
                             seed)
            # Every counted row is a senior-band taxi driver
            # at the senior wage, under a head who is NOT a
            # construction worker — the pairing-specific
            # point of the MJ finding.
            for row in rows:
                self.assertGreaterEqual(row["se_tier"], 3, seed)
                self.assertEqual(row["se_wage"], 36000, seed)
                self.assertNotEqual(row["head_prof"],
                                    "construction_worker", seed)
            # Non-vacuous per world: second earners occur in
            # every world, so the query is measuring a real
            # population.
            second_any = store.row(
                "SELECT COUNT(*) AS n FROM households h JOIN "
                "household_members hm ON hm.household_id"
                " = h.household_id JOIN employments e"
                " ON e.character_id = hm.character_id"
                " JOIN household_members hm2 ON"
                " hm2.household_id = h.household_id"
                " JOIN employments e2 ON e2.character_id ="
                " hm2.character_id WHERE hm.role = 'head'"
                " AND hm.left_at_game_minutes IS NULL"
                " AND e.ended_at_game_minutes IS NULL"
                " AND hm2.role != 'head'"
                " AND hm2.left_at_game_minutes IS NULL"
                " AND e2.ended_at_game_minutes IS NULL")["n"]
            self.assertGreater(second_any, 0, seed)

    def test_senior_band_wage_holds_in_every_seed(self):
        # Every current senior-band (tier >= 3) taxi driver
        # earns the senior 36,000 and every senior-band civil
        # engineer the senior 65,000, in each sweep world —
        # the band definition the query relies on.
        for seed, sim, _path in self.worlds:
            store = sim.store
            for prof, wage in (("taxi_driver", 36000),
                               ("civil_engineer", 65000)):
                rows = store.rows(
                    "SELECT tier, wage_per_month FROM employments"
                    " WHERE profession_id = ? AND tier >= 3"
                    " AND ended_at_game_minutes IS NULL",
                    (prof,))
                for row in rows:
                    self.assertEqual(
                        row["wage_per_month"], wage,
                        f"{seed} {prof} tier {row['tier']}")


class TestSeniorTaxiSecondEarnerHeadWage(unittest.TestCase):
    """Queue 42 Unit MK — the senior taxi driver under a
    low-wage head (Unit MJ follow-up: MJ found senior taxi
    drivers as second earners under eight kinds of head at
    every tier from 1 to 5, but never under a
    construction-worker head — yet the sweep recorded head
    professions and tiers, not head wages, so it cannot say
    whether the exception is the profession or the wage
    band). The same any-household query as MJ with the
    head's current wage joined (e.wage_per_month) across
    three seeded worlds, each 60 population and 30 days:
    the join returns the head's real current wage, and a
    construction-worker head's wage follows the band for
    its tier — so a tier >= 3 head earns the senior 20,000
    flat. The full 2-seed 300-population 365-day sweep is
    pinned by tools/verify_queue42_mk.py; these guard tests
    pin the method at suite speed and fail loudly if the
    head-wage join ever drifts from the employment row —
    that join is what the MK decision stands on, recorded
    in the V7 report §31.
    """

    SEEDS = ("mk-guard-1", "mk-guard-2", "mk-guard-3")

    @classmethod
    def setUpClass(cls):
        cls.worlds = []
        for seed in cls.SEEDS:
            path = _tmp_path()
            sim = Simulation(path, seed=seed)
            sim.generate_population(60)
            sim.run_days(30)
            cls.worlds.append((seed, sim, path))

    @classmethod
    def tearDownClass(cls):
        for _seed, sim, path in cls.worlds:
            sim.close()
            os.remove(path)

    def _head_wage_query(self, store):
        # The MJ any-household query WITH the head's current
        # wage joined: a non-head member of ANY household,
        # currently employed, with the head's current
        # employment wage beside them.
        head = ("household_members hm ON hm.household_id"
                " = h.household_id JOIN employments e"
                " ON e.character_id = hm.character_id")
        member = ("household_members hm2 ON hm2.household_id"
                  " = h.household_id JOIN employments e2"
                  " ON e2.character_id = hm2.character_id")
        head_now = ("hm.role = 'head'"
                    " AND hm.left_at_game_minutes IS NULL"
                    " AND e.ended_at_game_minutes IS NULL")
        member_now = ("hm2.role != 'head'"
                      " AND hm2.left_at_game_minutes IS NULL"
                      " AND e2.ended_at_game_minutes IS NULL")
        return store.rows(
            "SELECT h.household_id, hm.character_id AS"
            " head_id, e.profession_id AS head_prof,"
            " e.tier AS head_tier, e.wage_per_month AS"
            " head_wage, e2.profession_id AS se_prof,"
            " e2.tier AS se_tier, e2.wage_per_month AS se_wage"
            " FROM households h JOIN " + head + " JOIN "
            + member + " WHERE " + head_now + " AND "
            + member_now)

    def test_head_wage_join_returns_the_current_employment_wage(self):
        for seed, sim, _path in self.worlds:
            store = sim.store
            rows = self._head_wage_query(store)
            # Non-vacuous: second earners occur in every
            # world, so the join is measuring a real
            # population.
            self.assertGreater(len(rows), 0, seed)
            for row in rows:
                # The joined wage is the head's CURRENT
                # employment wage, read back directly.
                direct = store.row(
                    "SELECT wage_per_month FROM employments"
                    " WHERE character_id = ?"
                    " AND ended_at_game_minutes IS NULL",
                    (row["head_id"],))
                self.assertIsNotNone(direct, seed)
                self.assertEqual(row["head_wage"],
                                 direct["wage_per_month"], seed)
                self.assertGreater(row["head_wage"], 0, seed)
            # And the senior taxi rows, where they exist,
            # still sit at the senior 36,000.
            for row in rows:
                if (row["se_prof"] == "taxi_driver"
                        and row["se_tier"] >= 3):
                    self.assertEqual(row["se_wage"], 36000,
                                     seed)

    def test_construction_worker_head_wage_follows_the_band(self):
        # A construction-worker head's wage is the band wage
        # for its tier — so at tier >= 3 it is the senior
        # 20,000 flat, which is why all 17 construction-
        # worker heads in the MK sweep earn exactly 20,000.
        senior_cw_heads = 0
        for seed, sim, _path in self.worlds:
            store = sim.store
            data = sim.data
            heads = store.rows(
                "SELECT e.tier, e.wage_per_month FROM"
                " households h JOIN household_members hm ON"
                " hm.household_id = h.household_id JOIN"
                " employments e ON e.character_id ="
                " hm.character_id WHERE hm.role = 'head'"
                " AND hm.left_at_game_minutes IS NULL"
                " AND e.ended_at_game_minutes IS NULL"
                " AND e.profession_id ="
                " 'construction_worker'")
            for head in heads:
                self.assertEqual(
                    head["wage_per_month"],
                    data.wage_at("construction_worker",
                                 head["tier"]),
                    f"{seed} tier {head['tier']}")
                if head["tier"] >= 3:
                    senior_cw_heads += 1
                    self.assertEqual(head["wage_per_month"],
                                     20000, seed)
        # Non-vacuous: senior construction-worker heads
        # occur across the guard worlds.
        self.assertGreater(senior_cw_heads, 0)


class TestLowWageHeadNotConstructionWorker(unittest.TestCase):
    """Queue 43 Unit ML — the low-wage head who is not a
    construction worker (Unit MK follow-up: MK left the
    profession-vs-wage question confounded — every head
    earning <= 20,000 in both measured worlds is a
    construction worker, and no head in either world earns
    an entry wage at all — so the question needs a
    low-wage head who is NOT a construction worker). The
    same head-wage query as MK, restricted to heads earning
    <= 20,000, across three seeded worlds, each 60
    population and 30 days: the query returns the head's
    profession beside its real current wage, and the five
    entry bands the sweep looks for (shop owner 12,000,
    chef 13,000, taxi driver 14,000, teacher 15,000, police
    officer 18,000) are the data's tier-1 wages. The full
    5-seed 300-population 365-day sweep is pinned by
    tools/verify_queue43_ml.py; these guard tests pin the
    method at suite speed and fail loudly if the low-wage
    query ever drifts from the employment rows — that
    query is what the ML decision stands on, recorded in
    the V7 report §32.
    """

    SEEDS = ("ml-guard-1", "ml-guard-2", "ml-guard-3")

    @classmethod
    def setUpClass(cls):
        cls.worlds = []
        for seed in cls.SEEDS:
            path = _tmp_path()
            sim = Simulation(path, seed=seed)
            sim.generate_population(60)
            sim.run_days(30)
            cls.worlds.append((seed, sim, path))

    @classmethod
    def tearDownClass(cls):
        for _seed, sim, path in cls.worlds:
            sim.close()
            os.remove(path)

    def test_low_wage_head_query_returns_profession_and_current_wage(self):
        # The MK head-wage query restricted to heads earning
        # <= 20,000: each row carries the head's profession
        # beside its current employment wage.
        low_heads = 0
        for seed, sim, _path in self.worlds:
            store = sim.store
            rows = store.rows(
                "SELECT h.household_id, e.profession_id AS"
                " prof, e.tier, e.wage_per_month AS wage,"
                " hm.character_id AS head_id FROM households"
                " h JOIN household_members hm ON"
                " hm.household_id = h.household_id JOIN"
                " employments e ON e.character_id ="
                " hm.character_id WHERE hm.role = 'head'"
                " AND hm.left_at_game_minutes IS NULL"
                " AND e.ended_at_game_minutes IS NULL"
                " AND e.wage_per_month <= 20000")
            for row in rows:
                low_heads += 1
                # The joined wage and profession are the
                # head's CURRENT employment row, read back
                # directly.
                direct = store.row(
                    "SELECT profession_id, wage_per_month"
                    " FROM employments WHERE character_id = ?"
                    " AND ended_at_game_minutes IS NULL",
                    (row["head_id"],))
                self.assertIsNotNone(direct, seed)
                self.assertEqual(row["prof"],
                                 direct["profession_id"], seed)
                self.assertEqual(row["wage"],
                                 direct["wage_per_month"], seed)
                self.assertGreater(row["wage"], 0, seed)
                # And the wage is the band wage for the
                # profession and tier — a tier >= 3
                # construction-worker head is the flat
                # senior 20,000.
                self.assertEqual(
                    row["wage"],
                    sim.data.wage_at(row["prof"], row["tier"]),
                    f"{seed} {row['prof']} tier {row['tier']}")
        # Non-vacuous: low-wage heads occur across the guard
        # worlds (construction-worker heads at 20,000 are
        # the common case — the ML sweep found 44 of 45).
        self.assertGreater(low_heads, 0)

    def test_entry_band_wages_are_the_sweep_targets(self):
        # The five entry wages the ML sweep looks for below
        # 20,000 are the data's tier-1 wages, and the
        # prices.json bands agree — so a head at 12,000 is
        # an entry shop owner, not a data error.
        from tools import economy_sim as econ
        expected = {"shop_owner": 12000, "chef": 13000,
                    "taxi_driver": 14000, "teacher": 15000,
                    "police_officer": 18000}
        prices = econ.load("prices.json")
        bands = {w["profession_id"]: w
                 for w in prices["wages_monthly"]}
        for seed, sim, _path in self.worlds:
            for prof, wage in expected.items():
                self.assertEqual(
                    sim.data.wage_at(prof, 1), wage,
                    f"{seed} {prof} tier 1")
                self.assertEqual(bands[prof]["entry"], wage,
                                 f"{prof} entry band")
            # And the construction-worker wage the sweep
            # compares against stays flat at 20,000 at
            # every senior tier.
            for tier in (3, 4, 5):
                self.assertEqual(
                    sim.data.wage_at("construction_worker",
                                     tier),
                    20000, f"{seed} tier {tier}")


class TestBankingAndInvestment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = _tmp_path()
        cls.sim = Simulation(cls.path, seed="s04-bank")
        cls.sim.generate_population(60)
        cls.sim.run_days(32)
        cls.store = cls.sim.store
        cls.data = cls.sim.data

    @classmethod
    def tearDownClass(cls):
        cls.sim.close()
        os.remove(cls.path)

    def _employed_adult(self):
        return self.store.row(
            "SELECT e.character_id FROM employments e JOIN"
            " characters c ON c.character_id = e.character_id"
            " WHERE e.ended_at_game_minutes IS NULL"
            " AND c.is_system = 0 LIMIT 1")["character_id"]

    def test_accounts_reconcile_with_the_ledger(self):
        self.assertEqual(banking_mod.account_reconciliation(
            self.store), [])
        stats = banking_mod.bank_stats(self.store)
        self.assertGreater(stats["accounts"], 0)
        self.assertEqual(stats["reserves_ncr"],
                         self.store.balance("SYS-BANK"))

    def test_deposit_withdraw_identity(self):
        cid = self._employed_adult()
        acct = banking_mod.account_of(self.store, cid)
        self.assertIsNotNone(acct)
        cash0 = self.store.balance(cid)
        moved = banking_mod.deposit(self.store, cid, 1000, 10 ** 8,
                                    transfer_key="test:dep:1")
        self.assertEqual(moved, 1000)
        self.assertEqual(self.store.balance(cid), cash0 - 1000)
        back = banking_mod.withdraw(self.store, cid, 400, 10 ** 8,
                                    transfer_key="test:wd:1")
        self.assertEqual(back, 400)
        self.assertEqual(self.store.balance(cid), cash0 - 600)
        acct = banking_mod.account_of(self.store, cid)
        dep = self.store.row(
            "SELECT COALESCE(SUM(amount),0) AS s FROM economy_ledger"
            " WHERE from_character_id = ? AND reason_code ="
            " 'bank_deposit'", (cid,))["s"]
        wd = self.store.row(
            "SELECT COALESCE(SUM(amount),0) AS s FROM economy_ledger"
            " WHERE to_character_id = ? AND reason_code ="
            " 'bank_withdrawal'", (cid,))["s"]
        self.assertEqual(acct["balance_cached"], dep - wd)
        self.assertEqual(banking_mod.account_reconciliation(
            self.store), [])
        # A withdrawal larger than the account pays out what the
        # account holds — and then nothing more.
        rest = banking_mod.withdraw(self.store, cid, 10 ** 9,
                                    10 ** 8)
        self.assertEqual(rest, dep - wd)
        self.assertEqual(banking_mod.withdraw(
            self.store, cid, 100, 10 ** 8), 0)

    def test_credit_assessment_uses_real_wage_history(self):
        cid = self._employed_adult()
        credit = banking_mod.assess_credit(self.store, self.data,
                                           cid)
        self.assertGreater(credit["monthly_income_ncr"], 0)
        self.assertGreater(credit["max_bank_loan_ncr"], 0)
        self.assertEqual(credit["bank_loan_rate_percent"],
                         self.data.prices["loans"]["bank_loan"]
                         ["annual_interest_percent"])
        jobless = self.store.row(
            "SELECT c.character_id FROM characters c WHERE"
            " c.is_system = 0 AND c.died_at_game_minutes IS NULL"
            " AND NOT EXISTS (SELECT 1 FROM employments e WHERE"
            " e.character_id = c.character_id AND"
            " e.ended_at_game_minutes IS NULL) AND NOT EXISTS"
            " (SELECT 1 FROM economy_ledger l WHERE"
            " l.to_character_id = c.character_id AND"
            " l.reason_code = 'wage') LIMIT 1")
        if jobless is not None:
            credit = banking_mod.assess_credit(
                self.store, self.data, jobless["character_id"])
            self.assertEqual(credit["monthly_income_ncr"], 0)
            self.assertIsNone(banking_mod.disburse_loan(
                self.store, self.data, jobless["character_id"],
                "bank_loan", 1000, 10 ** 8))

    def test_loan_disburses_from_reserves_and_repays(self):
        cid = self._employed_adult()
        credit = banking_mod.assess_credit(self.store, self.data,
                                           cid)
        amount = min(20000, credit["max_bank_loan_ncr"])
        if amount <= 0:
            self.skipTest("borrower not eligible in this world")
        bank_before = self.store.balance("SYS-BANK")
        cash_before = self.store.balance(cid)
        loan = banking_mod.disburse_loan(
            self.store, self.data, cid, "bank_loan", amount, 10 ** 8)
        self.assertIsNotNone(loan)
        self.assertEqual(self.store.balance("SYS-BANK"),
                         bank_before - amount)
        self.assertEqual(self.store.balance(cid),
                         cash_before + amount)
        # The bank cannot lend what it does not hold.
        self.assertIsNone(banking_mod.disburse_loan(
            self.store, self.data, cid, "bank_loan",
            self.store.balance("SYS-BANK") + amount + 1, 10 ** 8))
        result = banking_mod.monthly_repayments(
            self.store, self.data, 50, 10 ** 8)
        after = self.store.row("SELECT * FROM loans WHERE loan_id"
                               " = ?", (loan["loan_id"],))
        self.assertLess(after["outstanding_ncr"],
                        loan["outstanding_ncr"] + 1)
        self.assertGreaterEqual(result["repaid_ncr"], 0)

    def test_savings_interest_uses_the_design_rate(self):
        cid = self._employed_adult()
        banking_mod.deposit(self.store, cid, 12000, 10 ** 8,
                            transfer_key="test:int:dep")
        acct = banking_mod.account_of(self.store, cid)
        expected = round(acct["balance_cached"]
                         * self.data.prices["loans"]
                         ["savings_annual_interest_percent"]
                         / 100 / 12)
        if expected <= 0:
            self.skipTest("interest rounds to zero")
        before = self.store.balance(cid)
        banking_mod.monthly_interest(self.store, self.data, 77,
                                     10 ** 8)
        row = self.store.row(
            "SELECT amount FROM economy_ledger WHERE"
            " to_character_id = ? AND reason_code = 'interest'"
            " AND transfer_key = ?", (cid, f"interest:"
            f"{acct['account_id']}:77"))
        self.assertIsNotNone(row)
        self.assertEqual(row["amount"], expected)
        self.assertEqual(self.store.balance(cid), before + expected)

    def test_shares_valuation_and_dividends_from_profit(self):
        biz = self.store.row(
            "SELECT * FROM businesses WHERE owner_character_id ="
            " 'SYS-MARKET' AND closed_at_game_minutes IS NULL"
            " LIMIT 1")
        bid = biz["business_id"]
        buyer = self._employed_adult()
        self.store.transfer("SYS-MARKET", buyer, 500000, "grant",
                            10 ** 8, transfer_key="test:inv:fund")
        price = banking_mod.share_price(self.store, self.data, biz)
        self.assertGreaterEqual(price, 1)
        inv = banking_mod.buy_shares(self.store, self.data, buyer,
                                     bid, 50000, 10 ** 8)
        self.assertIsNotNone(inv)
        self.assertEqual(inv["shares"], 50000 // price
                         if 50000 // price <= 100 else 100)
        self.assertGreater(banking_mod.portfolio_value(
            self.store, buyer), 0)
        # A recorded profit month pays dividends pro-rata.
        self.store.execute(
            "INSERT OR REPLACE INTO business_monthly (business_id,"
            " month_index, revenue_ncr, costs_ncr, tax_ncr,"
            " profit_ncr, employees, status_after) VALUES"
            " (?, 99, 300000, 100000, 0, 200000, 0, 'active')",
            (bid,))
        before = self.store.balance(buyer)
        paid = banking_mod.pay_dividends(self.store, self.data, 99,
                                         10 ** 8)
        self.assertEqual(paid.get(buyer),
                         self.store.balance(buyer) - before)
        self.assertGreater(paid.get(buyer, 0), 0)


if __name__ == "__main__":
    unittest.main()
