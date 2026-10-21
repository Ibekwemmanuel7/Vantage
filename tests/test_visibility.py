import unittest

import numpy as np

from vantage.visibility import sightlines


class VisibilityTests(unittest.TestCase):
    def run_ray(self, dem=None, **kwargs):
        return sightlines(
            np.zeros((9, 9)) if dem is None else dem,
            np.array([4.0]),
            np.array([2.0]),
            np.array([1.0]),
            np.array([0.0]),
            np.array([1.0]),
            resolution=10,
            distance=40,
            step=5,
            guard=1,
            **kwargs,
        )

    def test_flat_is_only_bounded_clear(self):
        result = self.run_ray()
        self.assertEqual(result["classes"][0], 1)
        self.assertEqual(result["samples"], 8)
        self.assertEqual(result["minimum_clearance"][0], 5)
        self.assertEqual(result["supported_fraction"][0], 1)

    def test_ridge_and_opposite_direction(self):
        dem = np.zeros((9, 9))
        dem[:, 5] = 100
        self.assertEqual(self.run_ray(dem)["classes"][0], 2)
        result = sightlines(dem, [4], [6], [1], [0], [1], 10, 15, 5, 1)
        self.assertEqual(result["classes"][0], 1)

    def test_missing_is_unknown_even_when_all_observed_samples_clear(self):
        dem = np.zeros((9, 9))
        dem[:, 5] = np.nan
        result = self.run_ray(dem)
        self.assertEqual(result["classes"][0], 0)
        self.assertLess(result["supported_fraction"][0], 1)

    def test_detected_obstruction_survives_missing_farther_away(self):
        dem = np.zeros((9, 9))
        dem[:, 4] = 100
        dem[:, 6] = np.nan
        self.assertEqual(self.run_ray(dem)["classes"][0], 2)

    def test_boundary_never_extrapolates(self):
        result = sightlines(np.zeros((9, 9)), [4], [7], [1], [0], [1], 10, 40, 5, 1)
        self.assertEqual(result["classes"][0], 0)

    def test_near_touch_is_guard(self):
        dem = np.zeros((9, 9))
        dem[:, 5] = 30
        self.assertEqual(self.run_ray(dem)["classes"][0], 3)

    def test_north_row_sign(self):
        dem = np.zeros((9, 9))
        dem[2, :] = 100
        result = sightlines(dem, [4], [4], [0], [1], [1], 10, 30, 5, 1)
        self.assertEqual(result["classes"][0], 2)

    def test_invalid_origin_and_policy(self):
        result = sightlines(
            np.zeros((9, 9)), [4], [4], [np.nan], [0], [1], 10, 30, 5, 1
        )
        self.assertEqual(result["classes"][0], 0)
        with self.assertRaises(ValueError):
            sightlines(np.zeros((9, 9)), [4], [4], [1], [0], [1], step=0)
