import unittest
from vantage.recent_pixels import select_latest, observation_quality


class RecentPixelsTests(unittest.TestCase):
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
