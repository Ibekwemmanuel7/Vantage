import unittest
import numpy as np
from vantage.terrain import slope_proxy, classify_proxy, proxy_summary
from vantage.radar_values import paired_change


class TerrainTests(unittest.TestCase):
    def test_flat_surface_including_negative_heights_has_zero_slope(self):
        for height in [0, -10, 1500]:
            slope, maximum = slope_proxy(np.full((9, 9), height, dtype=float), 30, 30)
            self.assertEqual(float(slope[4, 4]), 0)
            self.assertEqual(float(maximum[4, 4]), 0)
            self.assertTrue(np.isnan(maximum[:2]).all())

    def test_planar_slope_uses_both_metric_spacings(self):
        row, col = np.indices((9, 9))
        elevation = 0.1 * (col * 15) + 0.2 * (row * 30)
        expected = np.degrees(np.arctan(np.hypot(0.1, 0.2)))
        slope, maximum = slope_proxy(elevation, 15, 30)
        self.assertAlmostEqual(float(slope[4, 4]), expected, places=5)
        self.assertAlmostEqual(float(maximum[4, 4]), expected, places=5)

    def test_missing_derivative_neighbors_remain_unknown(self):
        elevation = np.zeros((11, 11))
        elevation[5, 5] = np.nan
        _, maximum = slope_proxy(elevation, 30, 30)
        self.assertTrue(np.isnan(maximum[3:8, 3:8]).all())
        classes = classify_proxy(maximum, 10)
        self.assertEqual(int(classes[5, 5]), 0)
        self.assertEqual(int(classes[2, 2]), 1)

    def test_threshold_boundary_and_sensitivity_are_explicit(self):
        values = np.array([[np.nan, 0, 5, 10, 10.01, 15, 20]])
        np.testing.assert_array_equal(
            classify_proxy(values, 10), [[0, 1, 1, 1, 2, 2, 2]]
        )
        low = [classify_proxy(values, t) == 1 for t in [5, 10, 15]]
        self.assertTrue((~low[0] | low[1]).all())
        self.assertTrue((~low[1] | low[2]).all())

    def test_retention_uses_original_crop_denominator_and_never_certifies_radar(self):
        classes = np.array([[0, 1], [2, 1]], dtype="uint8")
        result = proxy_summary(classes, np.ones((2, 2), dtype=bool))
        self.assertEqual(result["retained_crop_fraction"], 0.5)
        self.assertFalse(result["radar_illumination_confirmed"])
        self.assertFalse(result["terrain_screen_verified"])
        self.assertEqual(sum(result["counts"].values()), 4)
        power = np.full((2, 2, 2), 0.1, dtype="float32")
        filtered = np.where((classes == 1)[None, ...], power, np.nan)
        change = paired_change(
            filtered,
            filtered,
            np.ones((2, 2), dtype=bool),
            "same",
            "same",
            min_pixels=1,
        )
        self.assertEqual(change["summary"]["status"], "withheld")
        self.assertTrue(np.isnan(change["delta_db"]).all())

    def test_invalid_policies_and_slopes_fail_closed(self):
        for spacing in [0, -1, np.nan, np.inf]:
            with self.assertRaises(ValueError):
                slope_proxy(np.zeros((7, 7)), spacing, 30)
        for threshold in [0, 90, np.nan, np.inf]:
            with self.assertRaises(ValueError):
                classify_proxy(np.zeros((2, 2)), threshold)
        for slope in [-1, 91, np.inf]:
            with self.assertRaises(ValueError):
                classify_proxy(np.full((2, 2), slope), 10)
