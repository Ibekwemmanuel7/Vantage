import unittest
import numpy as np
from vantage.radar_values import decibels, numeric_evidence, paired_change


class RadarValueTests(unittest.TestCase):
    def test_db_conversion_rejects_nonpositive_and_nonfinite_power(self):
        result = decibels(np.array([1, 0.1, 0, -32768, np.nan, np.inf]))
        np.testing.assert_allclose(result[:2], [0, -10], atol=1e-5)
        self.assertTrue(np.isnan(result[2:]).all())

    def test_dual_pol_common_support_and_no_agronomic_claim(self):
        power = np.full((2, 2, 2), 0.1, dtype="float32")
        power[1, 0, 0] = np.nan
        result = numeric_evidence(power, np.ones((2, 2), dtype=bool), min_pixels=1)
        self.assertEqual(result["numeric_crop_fraction"], 0.75)
        self.assertTrue(result["numeric_support_qualified"])
        self.assertFalse(result["terrain_screen_verified"])
        self.assertFalse(result["agronomic_review_eligible"])

    def test_missing_crop_or_sparse_overlap_withholds_instead_of_zero_change(self):
        crop = np.ones((2, 2), dtype=bool)
        earlier = np.full((2, 2, 2), 0.1, dtype="float32")
        later = earlier.copy()
        later[:, 0, :] = np.nan
        result = paired_change(earlier, later, crop, "same", "same", min_pixels=1)
        self.assertEqual(result["summary"]["status"], "withheld")
        self.assertTrue(np.isnan(result["delta_db"]).all())
        result = numeric_evidence(earlier, np.zeros_like(crop), min_pixels=1)
        self.assertIsNone(result["features"])

    def test_same_track_change_is_later_minus_earlier_db(self):
        first = np.full((2, 2, 2), 0.1, dtype="float32")
        result = paired_change(
            first,
            first * 10,
            np.ones((2, 2), dtype=bool),
            "track",
            "track",
            min_pixels=1,
        )
        np.testing.assert_allclose(result["delta_db"], 10, atol=1e-5)
        self.assertFalse(result["summary"]["causal_attribution"])
        with self.assertRaises(ValueError):
            paired_change(
                first,
                first,
                np.ones((2, 2), dtype=bool),
                "ascending",
                "descending",
                min_pixels=1,
            )
