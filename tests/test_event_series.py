import unittest
import copy
import json
from pathlib import Path
from vantage.event_series import timeline_summary, validate_followup


def row(stamp, qualified=True, status="processed"):
    return dict(acquired_at=stamp, coverage_qualified=qualified, status=status)


class EventSeriesTests(unittest.TestCase):
    def test_followup_cannot_cross_parent_year_or_cutoff(self):
        root = Path(__file__).resolve().parents[1]
        parent = json.loads((root / "configs/kween_2023_case.json").read_text())
        plan = json.loads((root / "configs/kween_2023_followup.json").read_text())
        validate_followup(plan, parent)
        invalid = copy.deepcopy(plan)
        invalid.update(end="2023-06-06", as_of="2023-06-06T23:59:59Z")
        with self.assertRaises(ValueError):
            validate_followup(invalid, parent)
        invalid.update(
            start="2024-05-01", end="2024-06-05", as_of="2024-06-05T23:59:59Z"
        )
        with self.assertRaises(ValueError):
            validate_followup(invalid, parent)

    def test_recent_cloud_does_not_refresh_older_clear_observation(self):
        result = timeline_summary(
            [
                row("2023-05-21T08:00:00Z"),
                row("2023-06-05T08:00:00Z", False),
            ],
            "2023-06-05T23:59:59Z",
            7,
        )
        self.assertEqual(result["status"], "stale_research_context")
        self.assertEqual(result["latest_acquisition"], "2023-06-05T08:00:00Z")
        self.assertEqual(
            result["latest_quality_qualified_acquisition"], "2023-05-21T08:00:00Z"
        )
        self.assertGreater(result["latest_quality_qualified_age_days"], 15)

    def test_exact_freshness_boundary_and_no_interpolated_days(self):
        result = timeline_summary(
            [
                row("2023-05-20T00:00:00Z"),
                row("2023-05-25T00:00:00Z", False),
                row("2023-05-29T00:00:00Z"),
            ],
            "2023-06-05T00:00:00Z",
            7,
        )
        self.assertEqual(result["status"], "fresh_research_observation")
        self.assertEqual(result["quality_qualified_gaps_days"], [9])
        self.assertEqual(result["coverage_qualified_observations"], 2)
        self.assertFalse(result["agronomic_review_eligible"])

    def test_failed_and_missing_are_not_healthy_or_qualified(self):
        for rows in [
            [],
            [row("2023-06-05T08:00:00Z", False)],
            [row("2023-06-05T08:00:00Z", True, "processing_failed")],
        ]:
            result = timeline_summary(rows, "2023-06-05T23:59:59Z", 7)
            self.assertEqual(result["status"], "no_quality_qualified_observation")
            self.assertIsNone(result["latest_quality_qualified_age_days"])

    def test_duplicate_future_and_timezone_ambiguous_dates_rejected(self):
        for rows in [
            [row("2023-06-05T08:00:00Z")] * 2,
            [row("2023-06-06T08:00:00Z")],
            [row("2023-06-05T08:00:00")],
            [row("2023-06-05T08:00:00Z"), row("2023-06-05T11:00:00+03:00")],
        ]:
            with self.assertRaises(ValueError):
                timeline_summary(rows, "2023-06-05T23:59:59Z", 7)

    def test_freshness_policy_must_be_positive_and_finite(self):
        for age in [0, -1, float("nan"), float("inf")]:
            with self.assertRaises(ValueError):
                timeline_summary([], "2023-06-05T23:59:59Z", age)
