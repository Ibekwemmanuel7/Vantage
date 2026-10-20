import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from contextlib import closing

from vantage.core import brief, validate
from vantage.__main__ import save_feedback, render

DATA = Path(__file__).resolve().parents[1]/"examples/synthetic.json"
AS_OF = "2027-07-15T12:00:00Z"


class SliceTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(DATA.read_text())

    def test_known_relative_anomaly_and_explanation(self):
        result = brief(self.data, AS_OF)
        self.assertEqual(result["zones"][0]["zone_id"], "west")
        self.assertEqual(result["zones"][0]["status"], "inspect")
        self.assertAlmostEqual(result["zones"][0]["score"], .25)
        self.assertIn("No diagnosis", render(result))

    def test_stale_and_missing_are_not_healthy(self):
        result = brief(self.data, "2027-07-20T12:00:01Z")
        self.assertTrue(all(r["status"] == "stale" for r in result["zones"]))
        self.data["observations"] = []
        self.assertTrue(all(r["status"] == "missing" for r in brief(self.data, AS_OF)["zones"]))

    def test_quality_and_future_processing(self):
        for o in self.data["observations"]:
            o["usable_fraction"] = .2
        self.assertTrue(all(r["status"] == "low_quality" for r in brief(self.data, AS_OF)["zones"]))
        for o in self.data["observations"]:
            o["processed_at"] = "2027-08-01T00:00:00Z"
        self.assertTrue(all(r["status"] == "missing" for r in brief(self.data, AS_OF)["zones"]))

    def test_exact_freshness_boundary_and_cloud_fallback(self):
        result = brief(self.data, "2027-07-20T10:00:00Z")
        self.assertEqual(result["zones"][0]["status"], "inspect")
        cloudy = copy.deepcopy(self.data["observations"][-3:])
        for o in cloudy:
            o.update(id="cloud-"+o["id"], acquired_at="2027-07-16T10:00:00Z",
                     processed_at="2027-07-16T11:00:00Z", usable_fraction=.1)
        self.data["observations"].extend(cloudy)
        result = brief(self.data, "2027-07-16T12:00:00Z")
        self.assertEqual(result["zones"][0]["status"], "inspect")
        self.assertEqual(result["zones"][0]["latest_seen"]["usable_fraction"], .1)

    def test_mismatched_dates_do_not_create_peer_comparison(self):
        self.data["observations"][-1]["acquired_at"] = "2027-07-15T09:00:00Z"
        self.assertTrue(all(r["status"] == "insufficient_history" for r in brief(self.data, AS_OF)["zones"]))

    def test_boundary_and_duplicate_validation(self):
        self.data["zones"][0]["geometry"]["coordinates"][0][0][0] = -105
        with self.assertRaises(ValueError):
            validate(self.data)
        self.setUp()
        self.data["observations"].append(copy.deepcopy(self.data["observations"][0]))
        with self.assertRaises(ValueError):
            validate(self.data)

    def test_eligibility_and_history(self):
        self.data["fields"][0]["stage_eligible"] = False
        self.assertTrue(all(r["status"] == "ineligible" for r in brief(self.data, AS_OF)["zones"]))
        self.setUp()
        self.data["observations"] = self.data["observations"][:3]
        self.assertTrue(all(r["status"] == "insufficient_history" for r in brief(self.data, "2027-07-10T12:00:00Z")["zones"]))

    def test_feedback_snapshot_and_scope(self):
        result = brief(self.data, AS_OF)
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory)/"feedback.sqlite")
            args = (db, result, "demo", "west", AS_OF, "uncertain", "No confirmed cause", "Return visit")
            self.assertEqual(save_feedback(*args), 1)
            with closing(sqlite3.connect(db)) as conn:
                self.assertEqual(json.loads(conn.execute("select brief_json from feedback").fetchone()[0]), result)
            with self.assertRaises(ValueError):
                save_feedback(db, result, "other", "west", AS_OF, "uncertain", "x", "x")


if __name__ == "__main__":
    unittest.main()
