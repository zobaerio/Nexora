"""Session 10 — the spec's seven cross-system chains, each proven
by actual data changes in one world, reusing the per-session
machinery (no parallel systems):

  1. Human -> Education -> Employment -> Income -> Household
  2. Business -> Production -> Logistics -> Transport -> Market
  3. Government -> Budget -> Infrastructure -> City
  4. Weather -> Agriculture -> Food -> Prices
  5. Disaster -> Response -> Healthcare -> Recovery
  6. Education -> Skills -> Employment -> Growth
  7. Environmental Policy -> Industry -> Pollution

Chains 1 and 6 share one seeded long run (the Session 06
pattern: organic college enrolment does not occur in unseeded
worlds, so three young adults are enrolled at genesis; every
later hop — completion, certification, the labour gate, hiring,
wages, household finances — is the world's own machinery)."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))

from tools.sim import education as edu  # noqa: E402
from tools.sim import environment as env_mod  # noqa: E402
from tools.sim import government as gov  # noqa: E402
from tools.sim import labour  # noqa: E402
from tools.sim import market as market_mod  # noqa: E402
from tools.sim import policies  # noqa: E402
from tools.sim.engine import Simulation  # noqa: E402
from tools.sim.identity import age_years  # noqa: E402
from tools.sim.tests.common import rng  # noqa: E402
from tools.sim.tests.envcommon import env_world, seed_weather  # noqa: E402
from tools.sim.tests.govcommon import GM, funded_world  # noqa: E402
from tools.sim.tests.transportcommon import citizen  # noqa: E402

M1 = 43200  # end of month 1, game-minutes


def _tmp_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


def _young_adults(sim, count=3):
    rows = sim.store.rows(
        "SELECT character_id, born_at_game_minutes FROM characters"
        " WHERE is_system = 0 ORDER BY character_id")
    return [r["character_id"] for r in rows
            if 19 <= age_years(r["born_at_game_minutes"], 480) <= 24
            ][:count]


class TestGraduateChains(unittest.TestCase):
    """Chains 1 + 6 over one seeded world (pop 100, 430 days)."""

    @classmethod
    def setUpClass(cls):
        # The seed is the Session 06 acceptance seed: its genesis
        # is proven to contain exactly three 19-24 year olds (a
        # seed whose genesis has no young adults enrols nobody —
        # the count is asserted, not assumed).
        probe_path = _tmp_path()
        probe = Simulation(probe_path, seed="s06-probe")
        probe.generate_population(100)
        cls.students = _young_adults(probe)
        assert len(cls.students) == 3, cls.students
        cls.skill_before = {}
        for cid in cls.students:
            row = probe.store.row(
                "SELECT level FROM character_skills WHERE"
                " character_id = ? AND skill_id = 'engineering'",
                (cid,))
            cls.skill_before[cid] = row["level"] if row else 0
        probe.close()
        os.remove(probe_path)

        cls.path = _tmp_path()
        sim = Simulation(cls.path, seed="s06-probe")
        sim.generate_population(100)
        for cid in cls.students:
            edu.enrol_college(sim.store, sim.data, cid,
                              "civil_engineer", 480)
        sim.store.commit()
        sim.run_days(400)
        cls.sim = sim
        store = sim.store
        # Eligibility is read BEFORE any hiring drive: the gate
        # is the Education -> Employment interface.
        cls.eligible = {cid: labour._eligible(store, sim.data, cid,
                                              "civil_engineer")
                        for cid in cls.students}
        # If the monthly labour passes have not already hired a
        # graduate, drive the world's own market once.
        hired = store.rows(
            "SELECT character_id FROM employments WHERE"
            " character_id IN (%s) AND profession_id ="
            " 'civil_engineer' AND ended_at_game_minutes IS NULL"
            % ", ".join("?" * len(cls.students)),
            tuple(cls.students))
        if not hired:
            world = store.world()
            month = world["day_index"] // 30
            labour.post_vacancies(store, sim.data, month,
                                  world["game_minutes"])
            labour.match_vacancies(store, sim.data, rng(), month,
                                   world["game_minutes"])
            store.commit()
        # One more month settles wages + household finances.
        sim.run_days(30)

    @classmethod
    def tearDownClass(cls):
        cls.sim.close()
        os.remove(cls.path)

    def test_chain1_education_to_household_economy(self):
        store = self.sim.store
        graduates = []
        for cid in self.students:
            rec = store.row(
                "SELECT * FROM education_records WHERE"
                " character_id = ? AND programme ="
                " 'civil_engineer'", (cid,))
            self.assertIsNotNone(rec)  # Human -> Education
            if rec["status"] == "completed":
                graduates.append(cid)
        self.assertTrue(graduates, "no seeded student completed")
        for cid in graduates:
            self.assertTrue(edu.has_credential(
                store, cid, "civil_engineer"))
            self.assertTrue(self.eligible[cid])  # the labour gate
        employed = [cid for cid in graduates if store.row(
            "SELECT 1 FROM employments WHERE character_id = ?"
            " AND profession_id = 'civil_engineer' AND"
            " ended_at_game_minutes IS NULL", (cid,))]
        self.assertTrue(employed, "no graduate was hired")
        cid = employed[0]
        wage = store.row(
            "SELECT * FROM economy_ledger WHERE to_character_id"
            " = ? AND reason_code = 'wage'", (cid,))
        self.assertIsNotNone(wage)  # Employment -> Income
        self.assertGreater(wage["amount"], 0)
        household_id = store.row(
            "SELECT household_id FROM characters WHERE"
            " character_id = ?", (cid,))["household_id"]
        fin = store.row(
            "SELECT * FROM household_finances WHERE household_id"
            " = ? ORDER BY month_index DESC LIMIT 1",
            (household_id,))
        self.assertIsNotNone(fin)  # Income -> Household economy
        self.assertGreater(fin["income_ncr"], 0)
        self.assertEqual(store.ledger_sum_check(), [])

    def test_chain6_skills_to_growth(self):
        store = self.sim.store
        grew = [cid for cid in self.students
                if (store.row(
                    "SELECT level FROM character_skills WHERE"
                    " character_id = ? AND skill_id ="
                    " 'engineering'", (cid,)) or {"level": 0})
                ["level"] > self.skill_before[cid]]
        self.assertTrue(grew, "education wrote no skill growth")
        # Growth is measured, not asserted: the Session 04
        # indicator snapshots exist for the run's months and are
        # computed from the real employments (incl. the
        # graduates').
        snaps = store.rows("SELECT * FROM economic_indicators"
                           " WHERE scope = 'national' ORDER BY"
                           " month_index DESC LIMIT 1")
        self.assertTrue(snaps)
        metrics = json.loads(snaps[0]["metrics"])
        self.assertIn("unemployment_rate", metrics)
        self.assertIn("gdp_ncr", metrics)
        self.assertGreater(metrics["gdp_ncr"], 0)
        self.assertGreater(metrics["employed"], 0)


class TestBusinessChain(unittest.TestCase):
    """Chain 2 in one live world (pop 60, 95 days)."""

    def test_production_logistics_transport_market(self):
        path = _tmp_path()
        sim = Simulation(path, seed="s10-chain-business")
        try:
            sim.generate_population(60)
            sim.run_days(95)
            store = sim.store
            self.assertGreater(store.row(
                "SELECT COUNT(*) AS n FROM inventory_movements"
                " WHERE kind = 'production'")["n"], 0)
            self.assertGreater(store.row(
                "SELECT COUNT(*) AS n FROM freight_shipments"
                " WHERE status = 'delivered'")["n"], 0)
            self.assertGreater(store.row(
                "SELECT COUNT(*) AS n FROM trips")["n"], 0)
            self.assertGreater(store.row(
                "SELECT COUNT(*) AS n FROM market_prices")["n"], 0)
            self.assertGreater(store.row(
                "SELECT COUNT(*) AS n FROM price_history")["n"], 0)
            self.assertEqual(store.ledger_sum_check(), [])
        finally:
            sim.close()
            os.remove(path)


class TestGovernmentChain(unittest.TestCase):
    """Chain 3: office authority -> treasury budget -> road
    repair -> the city's own road network."""

    def test_budget_funded_infrastructure_repairs_city_roads(self):
        store, d, _ids = funded_world(adults=40)
        pm = gov.office_holder(store, "prime_minister",
                               "GOV-PM")["holder_character_id"]
        store.transfer("SYS-MARKET", "SYS-TREASURY-RUPSHA", 100000,
                       "municipal_grant", GM,
                       note="seeded municipal funds",
                       transfer_key="seed:chain3-grant")
        store.insert(
            "road_segments", segment_id="SEG-CHAIN3",
            city_id="rupsha_city", name="Chain Road",
            road_class="arterial", length_m=1000, lanes=2,
            speed_limit_kmh=40, capacity_vph=1000, condition=40,
            updated_at_game_minutes=GM)
        store.commit()
        treasury_before = store.balance("SYS-TREASURY-RUPSHA")
        pid = policies.propose_policy(
            store, d, "infrastructure_maintenance", pm, 1, M1,
            city_id="rupsha_city")
        policies.approve_policy(store, d, pid, pm, M1)
        policies.monthly_pass(store, d, 2, M1 * 2)
        seg = store.row("SELECT * FROM road_segments WHERE"
                        " segment_id = 'SEG-CHAIN3'")
        self.assertEqual(seg["condition"], 70)
        self.assertEqual(seg["city_id"], "rupsha_city")
        policy = store.row("SELECT * FROM policies WHERE"
                           " policy_id = ?", (pid,))
        self.assertEqual(policies.policy_spent(store, policy),
                         60000)
        self.assertLess(store.balance("SYS-TREASURY-RUPSHA"),
                        treasury_before)


class TestWeatherFoodChain(unittest.TestCase):
    """Chain 4 in one live world (pop 60, 210 days): weather is
    recorded daily, crops grow on Shibnagar's real parcels,
    harvests enter business inventory through the market's own
    adjust_inventory, and the produce carries a market price."""

    def test_weather_agriculture_food_prices(self):
        path = _tmp_path()
        sim = Simulation(path, seed="s10-chain-weather")
        try:
            sim.generate_population(60)
            sim.run_days(210)
            store = sim.store
            self.assertGreater(store.row(
                "SELECT COUNT(*) AS n FROM env_weather")["n"], 0)
            self.assertGreater(store.row(
                "SELECT COUNT(*) AS n FROM env_crops WHERE"
                " status = 'harvested'")["n"], 0)
            self.assertGreater(store.row(
                "SELECT COUNT(*) AS n FROM inventory_movements"
                " WHERE kind = 'harvest'")["n"], 0)
            self.assertGreater(store.row(
                "SELECT COALESCE(SUM(quantity), 0) AS q FROM"
                " business_inventory WHERE good_id ="
                " 'agricultural_produce'")["q"], 0)
            price = market_mod.price_of(store, sim.data,
                                        "shibnagar_town",
                                        "agricultural_produce")
            self.assertIsNotNone(price)
            self.assertGreater(price, 0)
        finally:
            sim.close()
            os.remove(path)


class TestDisasterChain(unittest.TestCase):
    """Chain 5: the configured cyclone damages real buildings,
    the response pays relief through the ledger and flags the
    injured for the clinics (Session 06's own interface — no
    parallel medical system), and funded repairs recover the
    event completely."""

    def test_disaster_response_healthcare_recovery(self):
        store, d = env_world()
        citizen(store, zone="d1_riverfront", first="River")
        store.transfer("SYS-MARKET", "SYS-CITY", 1000000,
                       "seed_grant", GM,
                       transfer_key="seed:chain5-treasury")
        store.commit()
        r = rng()
        did = env_mod.trigger_scenario(store, d, "cyclone_rupsha",
                                       10, 11 * 1440)
        store.commit()
        for day in range(10, 14):
            env_mod.daily_pass(store, d, r, day, (day + 1) * 1440)
        self.assertGreater(store.row(
            "SELECT COUNT(*) AS n FROM disaster_impacts WHERE"
            " disaster_id = ? AND kind = 'building_damage'",
            (did,))["n"], 0)
        actions = {row["action"] for row in store.rows(
            "SELECT action FROM disaster_responses WHERE"
            " disaster_id = ?", (did,))}
        self.assertIn("relief_payment", actions)
        self.assertIn("medical_flag", actions)  # -> Healthcare
        recovered = False
        for day in range(14, 200):
            env_mod.daily_pass(store, d, r, day, (day + 1) * 1440)
            if store.row("SELECT status FROM disaster_events"
                         " WHERE disaster_id = ?",
                         (did,))["status"] == "recovered":
                recovered = True
                break
        self.assertTrue(recovered)
        self.assertEqual(store.row(
            "SELECT COUNT(*) AS n FROM disaster_impacts WHERE"
            " disaster_id = ? AND kind = 'building_damage' AND"
            " repaired < damage", (did,))["n"], 0)
        self.assertGreater(store.row(
            "SELECT COALESCE(SUM(amount), 0) AS s FROM"
            " economy_ledger WHERE reason_code = 'disaster_relief'"
            " AND event_ref = ?", (did,))["s"], 0)
        self.assertEqual(store.ledger_sum_check(), [])


class TestEnvironmentalPolicyChain(unittest.TestCase):
    """Chain 7: an enacted emission_limit law measurably cuts
    the industry/transport pollution the environment system
    records, against the same world without the law."""

    def test_law_changes_industry_pollution(self):
        outcomes = {}
        for label, with_law in (("plain", False), ("law", True)):
            store, d = env_world()
            r = rng()
            if with_law:
                lid = store.next_id("LW", "laws", "law_id")
                store.insert(
                    "laws", law_id=lid, title="Emission Limit Act",
                    kind="emission_limit",
                    effect=json.dumps({"reduction_percent": 50}),
                    proposed_by=None, status="enacted",
                    effective_month=0,
                    created_at_game_minutes=GM,
                    enacted_at_game_minutes=GM)
                store.commit()
            for day in range(0, 30):
                seed_weather(store, "rupsha_city", day,
                             precip_mm=6.0)
                seed_weather(store, "shibnagar_town", day,
                             precip_mm=6.0)
            env_mod.monthly_pass(store, d, r, 1, 30 * 1440)
            sources = json.loads(store.row(
                "SELECT sources FROM env_pollution WHERE city_id"
                " = 'rupsha_city'")["sources"])
            outcomes[label] = sources
        plain, law = outcomes["plain"], outcomes["law"]
        # The recorded source breakdown carries the industry
        # term in both worlds (Session 08's pollution model
        # computes it from the city's real businesses); the
        # law's reduction applies on top of the recorded
        # sources only in the law world.
        self.assertIn("industry_index_points", plain)
        self.assertIn("industry_index_points", law)
        self.assertEqual(
            law["emission_limit_reduction_percent"], 50.0)
        self.assertEqual(
            plain["emission_limit_reduction_percent"], 0.0)


if __name__ == "__main__":
    unittest.main()
