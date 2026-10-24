import unittest
from vantage.radar_pairing import causal_pairs


class RadarPairingTests(unittest.TestCase):
    def test_afternoon_radar_cannot_pair_with_morning_target(self):
        optical=[dict(scene_id="optical",acquired_at="2024-06-04T08:00:00Z")]
        radar=[dict(item_id="radar",acquired_at="2024-06-04T16:00:00Z",track_id="track")]
        result=causal_pairs(optical,radar)[0]
        self.assertIsNone(result["selected_radar_item_id"])
        self.assertFalse(result["usable_for_agricultural_model"])

    def test_recent_versus_expired_and_cross_track_rejection(self):
        radar=[dict(item_id="radar",acquired_at="2024-06-04T16:00:00Z",track_id="track")]
        optical=[dict(scene_id="recent",acquired_at="2024-06-06T08:00:00Z"),
                 dict(scene_id="stale",acquired_at="2024-06-14T08:00:00Z")]
        result=causal_pairs(optical,radar)
        self.assertEqual(result[0]["selected_radar_item_id"],"radar")
        self.assertFalse(result[1]["within_age_limit"])
        self.assertIsNone(result[1]["selected_radar_item_id"])
        with self.assertRaises(ValueError):causal_pairs(optical,radar+[dict(radar[0],item_id="other",track_id="other")])
