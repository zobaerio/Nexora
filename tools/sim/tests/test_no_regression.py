"""No-existing-functionality-broken checks (owner criterion 11):
the economy balance simulator's output is byte-identical to its
pre-Session-01 baseline, and the committed data validation harness
passes. (The Godot testbed suite is re-run separately at delivery;
it cannot run inside this Python process.)"""
import hashlib
import os
import subprocess
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                    "..", "..", ".."))
ECONOMY_SIM_BASELINE_MD5 = "16740182867525bd659735deeb05150a"


class TestNoRegression(unittest.TestCase):
    def test_economy_sim_output_unchanged(self):
        out = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", "economy_sim.py")],
            capture_output=True, cwd=ROOT)
        self.assertEqual(out.returncode, 0)
        self.assertEqual(hashlib.md5(out.stdout).hexdigest(),
                         ECONOMY_SIM_BASELINE_MD5)

    def test_validate_data_passes(self):
        out = subprocess.run(
            [sys.executable, os.path.join(ROOT, "tools", "validate_data.py")],
            capture_output=True, cwd=ROOT)
        self.assertEqual(out.returncode, 0,
                         out.stdout.decode() + out.stderr.decode())


if __name__ == "__main__":
    unittest.main()
