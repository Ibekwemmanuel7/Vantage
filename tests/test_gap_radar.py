import unittest
from vantage.gap_radar import radar_plan,optical_matching_rows


class GapRadarTests(unittest.TestCase):
    def setUp(self):
        self.sequence=dict(decision_cutoff="2024-06-01T00:00:00Z",observations=[dict(
            location_id="lira-study",status="processed",acquired_at="2024-05-10T08:00:00Z",
            quality=dict(coverage_qualified=True))])

    def test_plan_includes_prior_week_but_never_future_radar(self):
        plan=radar_plan(self.sequence,[32.85,2.2,32.95,2.3])
        self.assertEqual(plan["start"],"2024-05-03")
        self.assertEqual(plan["as_of"],"2024-05-10T08:00:00+00:00")
        rows=optical_matching_rows(self.sequence)
        self.assertFalse(rows[0]["coverage_qualified"])
        self.assertTrue(rows[0]["original_coverage_qualified"])

    def test_future_or_mixed_location_sequence_rejected(self):
        self.sequence["decision_cutoff"]="2024-05-01T00:00:00Z"
        with self.assertRaises(ValueError):radar_plan(self.sequence,[32.85,2.2,32.95,2.3])
        self.sequence["decision_cutoff"]="2024-06-01T00:00:00Z"
        self.sequence["observations"].append(dict(self.sequence["observations"][0],location_id="other"))
        with self.assertRaises(ValueError):radar_plan(self.sequence,[32.85,2.2,32.95,2.3])
