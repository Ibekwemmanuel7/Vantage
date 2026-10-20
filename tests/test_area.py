import copy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from vantage.area import assess, csv_text, geojson, printable

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("demo_server", ROOT/"scripts/serve_demo.py")
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


def fixture():
    c = json.loads((ROOT/"configs/uganda_iganga.json").read_text())
    obs, rain = [], []
    for unit in ("IG-11", "IG-12", "IG-21", "IG-22"):
        for year in c["reference_years"]+[c["target_year"]]:
            obs.append(dict(unit_id=unit, year=year, acquired_at=f"{year}-05-14T10:00:00Z",
                            source_id=f"synthetic-{year}", ndvi=.65 if year < 2024 else .4,
                            usable_fraction=.9, valid_pixels=500, cropland_pixels=550))
            rain.append(dict(unit_id=unit, year=year, mm=20 if year < 2024 else 2,
                             start=f"{year}-05-11", end=f"{year}-05-15", source="synthetic"))
    return dict(config=c, observations=obs, rainfall=rain, lineage=[], failures=[], retrieved_at="2026-10-20T00:00:00Z")


class AreaTests(unittest.TestCase):
    def test_independent_signals_explain_without_cause(self):
        r = assess(fixture())
        self.assertTrue(all(u["status"] == "review" and len(u["reasons"]) == 2 for u in r["units"]))
        self.assertIn("No customer results", r["limitation"])

    def test_cloud_gaps_do_not_erase_rainfall_evidence(self):
        d = fixture()
        for o in d["observations"]:
            if o["year"] == 2024:
                o["usable_fraction"] = .1
        r = assess(d)
        self.assertTrue(all(u["status"] == "review" and u["vegetation_state"] == "insufficient_coverage" and u["ndvi"] is None for u in r["units"]))

    def test_missing_not_no_unusual_change(self):
        d = fixture()
        d["observations"], d["rainfall"] = [], []
        self.assertTrue(all(u["status"] == "insufficient_evidence" for u in assess(d)["units"]))

    def test_normal_requires_both_layers(self):
        d = fixture()
        for o in d["observations"]:
            o["ndvi"] = .65
        for r in d["rainfall"]:
            r["mm"] = 20
        self.assertTrue(all(u["status"] == "no_unusual_change" for u in assess(d)["units"]))
        d["rainfall"] = []
        self.assertTrue(all(u["status"] == "insufficient_evidence" for u in assess(d)["units"]))

    def test_stale_and_future_observations_cannot_flag(self):
        d = fixture()
        d["config"]["as_of"] = "2024-06-01T23:59:59Z"
        self.assertTrue(all(u["status"] == "insufficient_evidence" and u["vegetation_state"] == "stale" and u["rainfall_state"] == "stale" for u in assess(d)["units"]))
        d = fixture()
        d["config"]["as_of"] = "2024-05-10T00:00:00Z"
        self.assertTrue(all(u["ndvi"] is None and u["rainfall_mm"] is None for u in assess(d)["units"]))

    def test_short_reference_and_zero_rain_reference(self):
        d = fixture()
        d["observations"] = [o for o in d["observations"] if o["year"] >= 2022]
        for r in d["rainfall"]:
            r["mm"] = 0
        self.assertTrue(all(u["status"] == "insufficient_evidence" and u["rainfall_ratio"] is None for u in assess(d)["units"]))

    def test_duplicate_and_future_reference_rejected(self):
        d = fixture()
        d["rainfall"].append(copy.deepcopy(d["rainfall"][0]))
        with self.assertRaises(ValueError):
            assess(d)
        d = fixture()
        d["config"]["reference_years"][-1] = 2024
        with self.assertRaises(ValueError):
            assess(d)

    def test_exports_are_linked_and_report_escapes_markup(self):
        r = assess(fixture())
        self.assertEqual(len(geojson(r)["features"]), 4)
        self.assertIn("rainfall_reference_mm", csv_text(r))
        r["units"][0]["question"] = "<script>bad()</script>"
        self.assertNotIn("<script>", printable(r))

    def test_local_feedback_snapshot_and_invalid_submission(self):
        brief = json.loads((ROOT/"web/data/uganda.json").read_text(encoding="utf-8"))
        body = dict(profile="uganda", brief_id=brief["brief_id"], unit_id="IG-11", kind="expert_review",
                    outcome="uncertain", observed_at="2026-10-20", finding="Synthetic test entry", next_step="Confirm stage", demo=True)
        with tempfile.TemporaryDirectory(dir=ROOT/"outputs") as tmp:
            db = Path(tmp)/"feedback.sqlite"
            self.assertEqual(server.store_feedback(body, db), 1)
            records = server.feedback_records(brief["brief_id"], db)
            self.assertEqual(records[0]["finding"], body["finding"])
            body["brief_id"] = "other-profile"
            with self.assertRaises(ValueError):
                server.store_feedback(body, db)
            body["brief_id"], body["demo"] = brief["brief_id"], False
            with self.assertRaises(ValueError):
                server.store_feedback(body, db)


if __name__ == "__main__":
    unittest.main()
