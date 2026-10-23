import copy
import json
from pathlib import Path
import unittest

from vantage.partner_bundle import build_bundle, render_report


class PartnerBundleTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = json.loads((Path(__file__).resolve().parents[1] / "web/data/scouting.json").read_text())

    def test_stale_evidence_remains_withheld_and_traceable(self):
        original = copy.deepcopy(self.snapshot)
        result = build_bundle(self.snapshot)
        self.assertEqual(result["quality"]["state"], "stale")
        self.assertAlmostEqual(result["quality"]["age_at_cutoff_days"], 10.676157, places=6)
        self.assertEqual(result["decision"]["field_priorities"], [])
        self.assertFalse(result["publication_authorized"])
        self.assertEqual(result["evidence"]["sources"], original["sources"])
        self.assertEqual(self.snapshot, original)
        self.assertEqual(result, build_bundle(self.snapshot))

    def test_future_observation_and_inconsistent_latest_rejected(self):
        self.snapshot["optical"]["observations"][0]["acquired_at"] = "2024-01-01T00:00:00Z"
        with self.assertRaises(ValueError):
            build_bundle(self.snapshot)
        self.setUp()
        self.snapshot["optical"]["latest_usable"] = "2023-05-11T07:46:11.024000Z"
        with self.assertRaises(ValueError):
            build_bundle(self.snapshot)

    def test_missing_is_not_healthy_and_report_escapes_text(self):
        for o in self.snapshot["optical"]["observations"]:
            o["coverage_qualified"] = False
        self.snapshot["name"] = "<script>alert(1)</script>"
        result = build_bundle(self.snapshot)
        self.assertEqual(result["quality"]["state"], "missing")
        self.assertIsNone(result["quality"]["age_at_cutoff_days"])
        report = render_report(result)
        self.assertNotIn("<script>", report)
        self.assertIn("&lt;script&gt;", report)
        self.assertIn("Unreviewed draft", report)

    def test_reject_operational_mode_or_naive_cutoff(self):
        self.snapshot["mode"] = "live"
        with self.assertRaises(ValueError):
            build_bundle(self.snapshot)
        self.snapshot["mode"] = "historical_research"
        self.snapshot["as_of"] = "2023-06-05T23:59:59"
        with self.assertRaises(ValueError):
            build_bundle(self.snapshot)
