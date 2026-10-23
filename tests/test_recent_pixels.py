import unittest
from vantage.recent_pixels import select_latest, select_sequence, observation_quality, summarize_sequence


class RecentPixelsTests(unittest.TestCase):
    def test_sequence_deduplicates_acquisitions_and_enforces_budget(self):
        base = dict(bbox_covers_study=True, baseline_assets_present=True)
        rows = [dict(base,id="a",acquired_at="2026-10-10T00:00:00Z"),
                dict(base,id="b",acquired_at="2026-10-10T00:00:00Z"),
                dict(base,id="c",acquired_at="2026-10-20T00:00:00Z")]
        self.assertEqual([r["id"] for r in select_sequence({"candidates":rows},6)], ["c","b"])
        with self.assertRaises(ValueError): select_sequence({"candidates":rows},7)

    def test_sequence_missing_and_stale_do_not_become_live_priorities(self):
        row = dict(location_id="a",status="processed",acquired_at="2026-10-10T00:00:00Z",
                   quality=dict(coverage_qualified=True,age_at_cutoff_days=13,state="stale"))
        result = summarize_sequence([row])[0]
        self.assertEqual(result["status"],"stale")
        self.assertFalse(result["field_priorities_available"])
        row["quality"]["coverage_qualified"] = False
        self.assertIsNone(summarize_sequence([row])[0]["latest_qualified_acquisition"])

    def test_latest_selection_not_lowest_cloud_and_requires_assets(self):
        old = dict(id="old", acquired_at="2026-10-10T00:00:00Z", bbox_covers_study=True,
                   baseline_assets_present=True, scene_cloud_cover=0)
        new = dict(old, id="new", acquired_at="2026-10-20T00:00:00Z", scene_cloud_cover=99)
        self.assertEqual(select_latest({"candidates":[old,new]})["id"], "new")
        new["baseline_assets_present"] = False
        self.assertEqual(select_latest({"candidates":[old,new]})["id"], "old")
        self.assertIsNone(select_latest({"candidates":[]}))

    def test_clouds_never_become_recent_usable_observations(self):
        result = observation_quality(dict(total_pixels=100,valid_pixels=1),
                                     "2026-10-22T00:00:00Z", "2026-10-23T00:00:00Z")
        self.assertEqual(result["state"], "insufficient_coverage")
        self.assertFalse(result["field_priorities_available"])

    def test_stale_and_recent_research_are_distinct_from_field_eligibility(self):
        for date, expected in [("2026-10-10", "stale"), ("2026-10-20", "recent_whole_box_research")]:
            result = observation_quality(dict(total_pixels=100,valid_pixels=90),
                                         date+"T00:00:00Z", "2026-10-23T00:00:00Z")
            self.assertEqual(result["state"], expected)
            self.assertFalse(result["field_priorities_available"])
        with self.assertRaises(ValueError):
            observation_quality(dict(total_pixels=0,valid_pixels=0), "2026-10-22T00:00:00Z", "2026-10-23T00:00:00Z")
