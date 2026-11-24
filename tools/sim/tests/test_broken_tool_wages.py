"""Queue 20 Unit EL — Broken-Tool Wage Consequence (GDD-04 §3.3,
GDD-03 §2): the no-dock rule stands — a work block bent by a
broken tool does not dock the day's wages, and the monthly wage is
paid in full.

Tests the labour helpers (broken_tool_days counts the month's bent
days from the stored schedules; broken_tool_wage_dock returns 0)
and the settlement itself (a business-employed worker with a bent
day in the month is paid the full monthly wage).

Queue 21 Unit ES adds the day-wage side: construction workers
are paid per worked day (worked_days × wage_per_month / 30), so
the EL no-dock proof above now uses a monthly profession.
"""
import json
import os
import tempfile
import unittest

from tools.sim import labour as labour_mod
from tools.sim.engine import Simulation
from tools.sim.tests.common import make_person, make_store

GM = 480


def _tmp_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


def _bent_day(store, cid, day_index, bent=True):
    blocks = [{"start": 0, "end": 480, "activity": "home",
               "location": "home", "zone": "d1_midtown",
               "broken_tool": bent},
              {"start": 480, "end": 1440, "activity": "home",
               "location": "home", "zone": "d1_midtown"}]
    store.execute(
        "INSERT INTO instantiated_schedules"
        " (character_id, day_index, blocks_json) VALUES (?, ?, ?)",
        (cid, day_index, json.dumps(blocks)))


class TestBrokenToolDays(unittest.TestCase):
    def test_counts_only_days_with_a_bent_block(self):
        store = make_store()
        cid = make_person(store, age=30, first="Worker")
        _bent_day(store, cid, 120)
        _bent_day(store, cid, 121, bent=False)
        _bent_day(store, cid, 122)
        # Month 5 covers days 120..149 (the settlement's mapping).
        self.assertEqual(labour_mod.broken_tool_days(store, cid, 5), 2)
        self.assertEqual(labour_mod.broken_tool_days(store, cid, 4), 0)

    def test_month_boundaries_are_exact(self):
        store = make_store()
        cid = make_person(store, age=30, first="Worker")
        _bent_day(store, cid, 119)  # month 4's last day
        _bent_day(store, cid, 150)  # month 6's first day
        self.assertEqual(labour_mod.broken_tool_days(store, cid, 5), 0)
        self.assertEqual(labour_mod.broken_tool_days(store, cid, 4), 1)
        self.assertEqual(labour_mod.broken_tool_days(store, cid, 6), 1)

    def test_no_stored_day_counts_zero(self):
        store = make_store()
        cid = make_person(store, age=30, first="Worker")
        self.assertEqual(labour_mod.broken_tool_days(store, cid, 5), 0)

    def test_a_day_with_no_broken_flag_counts_zero(self):
        store = make_store()
        cid = make_person(store, age=30, first="Worker")
        _bent_day(store, cid, 120, bent=False)
        self.assertEqual(labour_mod.broken_tool_days(store, cid, 5), 0)


class TestBrokenToolWageDock(unittest.TestCase):
    def test_the_dock_is_zero_with_bent_days(self):
        # The no-dock rule: even a month of bent days docks nothing.
        store = make_store()
        cid = make_person(store, age=30, first="Worker")
        for day in range(120, 130):
            _bent_day(store, cid, day)
        self.assertEqual(labour_mod.broken_tool_days(store, cid, 5), 10)
        self.assertEqual(
            labour_mod.broken_tool_wage_dock(store, cid, 5, 9000), 0)

    def test_the_dock_is_zero_without_bent_days(self):
        store = make_store()
        cid = make_person(store, age=30, first="Worker")
        self.assertEqual(
            labour_mod.broken_tool_wage_dock(store, cid, 5, 9000), 0)


class TestSettlementPaysInFull(unittest.TestCase):
    """The settlement consults the rule at the point of payment:
    a business-employed worker with a bent day in the month is
    paid the full monthly wage."""

    @classmethod
    def setUpClass(cls):
        cls.path = _tmp_path()
        cls.sim = Simulation(cls.path, seed="q20-el")
        cls.sim.generate_population(60)
        cls.store = cls.sim.store
        cls.data = cls.sim.data

    @classmethod
    def tearDownClass(cls):
        cls.sim.close()
        os.remove(cls.path)

    def test_business_wages_pay_in_full_after_a_bent_day(self):
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
        # Queue 21 Unit ES: construction workers moved to day-wage
        # pay, so the no-dock proof uses a monthly profession (a
        # chef in food processing) — the rule itself is unchanged.
        self.store.insert(
            "employments", employment_id=eid, character_id=cid,
            profession_id="chef",
            employer_business_id=biz["business_id"], tier=1,
            wage_per_month=wage, started_at_game_minutes=500)
        # One bent day in month 5 (day 125): the tool broke, the
        # work bent to rest — and the wage still pays in full.
        _bent_day(self.store, cid, 125)
        self.assertEqual(
            labour_mod.broken_tool_days(self.store, cid, 5), 1)
        biz_before = self.store.business_balance(biz["business_id"])
        emp_before = self.store.balance(cid)
        paid = self.sim._pay_business_wages(5, 200000)
        self.assertEqual(paid.get(eid), wage)
        self.assertEqual(self.store.business_balance(
            biz["business_id"]), biz_before - wage)
        self.assertEqual(self.store.balance(cid), emp_before + wage)


def _work_day(store, cid, day_index, bent=False):
    """One stored day with a morning work block: bent=True marks
    the work block with the scheduler's broken_tool flag (the
    work bent to rest — the EL _bent_day shape, with the work
    block kept so the day is identifiable as worked-or-not)."""
    blocks = [{"start": 0, "end": 480, "activity": "home",
               "location": "home", "zone": "d1_midtown"},
              {"start": 480, "end": 1020, "activity": "work",
               "location": "d1_industry", "zone": "d1_industry",
               "broken_tool": bent},
              {"start": 1020, "end": 1440, "activity": "home",
               "location": "home", "zone": "d1_midtown"}]
    store.execute(
        "INSERT INTO instantiated_schedules"
        " (character_id, day_index, blocks_json) VALUES (?, ?, ?)",
        (cid, day_index, json.dumps(blocks)))


class TestDayWagePay(unittest.TestCase):
    """Queue 21 Unit ES — construction-worker day-wage pay
    (GDD-03 §2): worked days × (wage_per_month / 30)."""

    def test_worked_days_counts_only_unbent_work_blocks(self):
        store = make_store()
        cid = make_person(store, age=30, first="Builder")
        _work_day(store, cid, 120)              # worked
        _work_day(store, cid, 121, bent=True)   # tool broke: no work
        _bent_day(store, cid, 122)              # rest day: no work
        _work_day(store, cid, 123)              # worked
        # Month 5 covers days 120..149.
        self.assertEqual(labour_mod.worked_days(store, cid, 5), 2)

    def test_a_day_with_one_unbent_block_among_bent_counts(self):
        store = make_store()
        cid = make_person(store, age=30, first="Builder")
        blocks = [{"start": 0, "end": 480, "activity": "work",
                   "location": "d1_industry", "zone": "d1_industry",
                   "broken_tool": True},
                  {"start": 480, "end": 1020, "activity": "work",
                   "location": "d1_industry", "zone": "d1_industry"},
                  {"start": 1020, "end": 1440, "activity": "home",
                   "location": "home", "zone": "d1_midtown"}]
        store.execute(
            "INSERT INTO instantiated_schedules"
            " (character_id, day_index, blocks_json)"
            " VALUES (?, ?, ?)",
            (cid, 120, json.dumps(blocks)))
        self.assertEqual(labour_mod.worked_days(store, cid, 5), 1)

    def test_month_boundaries_are_exact(self):
        store = make_store()
        cid = make_person(store, age=30, first="Builder")
        _work_day(store, cid, 119)  # month 4's last day
        _work_day(store, cid, 150)  # month 6's first day
        self.assertEqual(labour_mod.worked_days(store, cid, 5), 0)
        self.assertEqual(labour_mod.worked_days(store, cid, 4), 1)
        self.assertEqual(labour_mod.worked_days(store, cid, 6), 1)

    def test_day_wage_due_is_worked_days_times_daily_rate(self):
        store = make_store()
        cid = make_person(store, age=30, first="Builder")
        for day in range(120, 130):
            _work_day(store, cid, day)
        # 10 worked days at 9000 / 30 = 300 a day.
        self.assertEqual(
            labour_mod.day_wage_due(store, cid, 5, 9000), 3000)

    def test_a_full_month_pays_the_band(self):
        store = make_store()
        cid = make_person(store, age=30, first="Builder")
        for day in range(120, 150):
            _work_day(store, cid, day)
        self.assertEqual(
            labour_mod.day_wage_due(store, cid, 5, 9000), 9000)

    def test_no_worked_days_pays_nothing(self):
        store = make_store()
        cid = make_person(store, age=30, first="Builder")
        self.assertEqual(
            labour_mod.day_wage_due(store, cid, 5, 9000), 0)

    def test_wage_due_for_routes_by_profession(self):
        store = make_store()
        cid = make_person(store, age=30, first="Builder")
        for day in range(120, 130):
            _work_day(store, cid, day)
        _bent_day(store, cid, 130)
        # A monthly profession: the full wage, dock 0 (EL).
        self.assertEqual(
            labour_mod.wage_due_for(store, cid, "chef", 5, 9000),
            9000)
        # A construction worker: 10 worked days × 300.
        self.assertEqual(
            labour_mod.wage_due_for(
                store, cid, "construction_worker", 5, 9000), 3000)


class TestDayWageSettlement(unittest.TestCase):
    """The settlement pays a business-employed construction
    worker per worked day — a bent day pays nothing, a full
    month pays the band."""

    @classmethod
    def setUpClass(cls):
        cls.path = _tmp_path()
        cls.sim = Simulation(cls.path, seed="q21-es")
        cls.sim.generate_population(60)
        cls.store = cls.sim.store
        cls.data = cls.sim.data

    @classmethod
    def tearDownClass(cls):
        cls.sim.close()
        os.remove(cls.path)

    def _hire(self, wage=9000):
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
        eid = self.store.next_id("EM", "employments",
                                 "employment_id")
        self.store.insert(
            "employments", employment_id=eid, character_id=cid,
            profession_id="construction_worker",
            employer_business_id=biz["business_id"], tier=1,
            wage_per_month=wage, started_at_game_minutes=500)
        return biz, cid, eid

    def test_business_pays_day_wages_for_worked_days(self):
        biz, cid, eid = self._hire()
        for day in range(120, 130):
            _work_day(self.store, cid, day)
        _work_day(self.store, cid, 130, bent=True)
        self.assertEqual(
            labour_mod.worked_days(self.store, cid, 5), 10)
        biz_before = self.store.business_balance(biz["business_id"])
        emp_before = self.store.balance(cid)
        paid = self.sim._pay_business_wages(5, 200000)
        self.assertEqual(paid.get(eid), 3000)
        self.assertEqual(self.store.business_balance(
            biz["business_id"]), biz_before - 3000)
        self.assertEqual(self.store.balance(cid), emp_before + 3000)

    def test_full_month_pays_the_band(self):
        biz, cid, eid = self._hire()
        for day in range(120, 150):
            _work_day(self.store, cid, day)
        paid = self.sim._pay_business_wages(5, 200000)
        self.assertEqual(paid.get(eid), 9000)

    def test_no_worked_days_pays_nothing(self):
        biz, cid, eid = self._hire()
        paid = self.sim._pay_business_wages(5, 200000)
        self.assertEqual(paid.get(eid), 0)


if __name__ == "__main__":
    unittest.main()
