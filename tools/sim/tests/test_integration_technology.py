"""Session 10 — technology levels: derived from Session 06's own
research records + the credentialed share of adults, by the
documented formula in data/integration-config.json, and gating
one real capability — the research capability gain a completed
project writes (Session 06's own development effect). Without
the integration layer, or before any level is computed, the gate
factor is exactly 1.0 and Session 06 behaviour is unchanged."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))

from tools.sim import integration  # noqa: E402
from tools.sim import research as research_mod  # noqa: E402
from tools.sim.tests.common import rng  # noqa: E402
from tools.sim.tests.humandevcommon import (GM, citizen,  # noqa: E402
                                            hd_world)

COLLEGE = "EDU-RUPSHA-COLLEGE"


def _seed_publications(store, field, count, month=1):
    for i in range(count):
        store.insert(
            "research_records", record_id=f"RR-T-{field}-{i}",
            project_id=f"RP-T-{field}-{i}", institution_id=COLLEGE,
            field=field, kind="publication", month_index=month,
            game_minutes=GM, details="{}")


def _capability(store):
    return store.row(
        "SELECT research_capability FROM educational_institutions"
        " WHERE institution_id = ?", (COLLEGE,))[
            "research_capability"]


class TestTechnologyDerivation(unittest.TestCase):
    def test_level_matches_documented_formula(self):
        store, d = hd_world()
        integration.setup_integration(store, d)
        ids = [citizen(store, age=30, first=f"Adult{i}")
               for i in range(4)]
        store.insert(
            "certifications", certification_id="CERT-T1",
            character_id=ids[0], institution_id=COLLEGE,
            kind="college_credential", programme="doctor",
            issued_month=1, game_minutes=GM)
        _seed_publications(store, "public_health", 4)
        store.commit()
        levels = integration.compute_technology(store, d, 2,
                                                GM * 2)
        tc = d.integration_config["technology"]
        share = 0.25  # 1 of 4 living adults holds a certification
        expected_med = min(tc["max_level"],
                           tc["publications_weight"] * 4
                           + tc["education_weight"] * share)
        self.assertEqual(levels["medicine"],
                         round(expected_med, 4))
        # No engineering publications: the level is the education
        # term alone — derived, never asserted.
        self.assertEqual(levels["engineering"],
                         round(tc["education_weight"] * share, 4))
        row = store.row("SELECT * FROM technology_levels WHERE"
                        " field = 'medicine' AND month_index = 2")
        basis = json.loads(row["basis"])
        self.assertEqual(basis["publications"], 4)
        self.assertEqual(basis["credentialed_share"], share)
        self.assertEqual(basis["credentialed_adults_basis"], 4)

    def test_factor_is_exactly_one_without_layer_or_levels(self):
        store, d = hd_world()
        # Layer absent entirely.
        self.assertEqual(
            integration.technology_factor(store, d,
                                          "public_health"), 1.0)
        integration.setup_integration(store, d)
        # Layer present, no levels computed yet.
        self.assertEqual(
            integration.technology_factor(store, d,
                                          "public_health"), 1.0)
        # Unmapped field names are neutral too.
        self.assertEqual(
            integration.technology_factor(store, d,
                                          "alchemy"), 1.0)


class TestTechnologyGate(unittest.TestCase):
    def _world_with_project(self, with_technology):
        store, d = hd_world()
        lead = citizen(store, age=40, first="Lead")
        if with_technology:
            integration.setup_integration(store, d)
            _seed_publications(store, "public_health", 6)
            store.commit()
            integration.compute_technology(store, d, 1, GM)
        store.insert(
            "research_projects", project_id="RP-GATE",
            institution_id=COLLEGE, lead_character_id=lead,
            field="public_health", status="active",
            budget_ncr=1000, started_month=1, ends_month=1,
            game_minutes=GM)
        store.commit()
        return store, d

    def test_completion_gain_scales_with_technology_level(self):
        base_store, base_d = self._world_with_project(False)
        before = _capability(base_store)
        research_mod.monthly_pass(base_store, base_d, rng(), 1, GM)
        base_gain = _capability(base_store) - before
        cfg = base_d.education_health_config["research"]
        self.assertEqual(base_gain,
                         cfg["capability_gain_per_completion"])

        store, d = self._world_with_project(True)
        factor = integration.technology_factor(store, d,
                                               "public_health")
        self.assertGreater(factor, 1.0)
        before = _capability(store)
        research_mod.monthly_pass(store, d, rng(), 1, GM)
        gained = _capability(store) - before
        self.assertAlmostEqual(
            gained,
            cfg["capability_gain_per_completion"] * factor,
            places=6)
        self.assertGreater(gained, base_gain)
        # The completion still wrote its publication record.
        self.assertIsNotNone(store.row(
            "SELECT * FROM research_records WHERE"
            " project_id = 'RP-GATE'"))


if __name__ == "__main__":
    unittest.main()
