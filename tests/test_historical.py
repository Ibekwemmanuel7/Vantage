import unittest
import copy
import json
from pathlib import Path
import numpy as np
from vantage.historical import anomaly_map, rainfall_comparison, validate_plan


class HistoricalTests(unittest.TestCase):
    def test_frozen_plan_rejects_duplicate_years_and_post_cutoff_windows(self):
        plan = json.loads(
            (
                Path(__file__).resolve().parents[1] / "configs/kween_2023_case.json"
            ).read_text()
        )
        validate_plan(plan)
        for field, value in [
            ("reference_years", [2020, 2020, 2021]),
            ("observation_cutoff", "2023-06-01T23:59:59Z"),
        ]:
            invalid = copy.deepcopy(plan)
            invalid[field] = value
            with self.assertRaises(ValueError):
                validate_plan(invalid)

    def test_rainfall_duplicate_reference_years_cannot_inflate_evidence(self):
        with self.assertRaises(ValueError):
            rainfall_comparison([], [2020, 2020, 2021], 2023, [3])

    def test_pixel_reference_counts_and_lower_than_all_rule(self):
        target = np.full((2, 2), 0.3, dtype="float32")
        refs = np.full((4, 2, 2), 0.6, dtype="float32")
        refs[:2, 0, 0] = np.nan
        result = anomaly_map(
            target, refs, np.ones((2, 2), dtype=bool), min_fraction=0.5, min_pixels=1
        )
        self.assertTrue(np.isnan(result["delta"][0, 0]))
        self.assertEqual(result["low_flag"].sum(), 3)

    def test_sparse_overlap_withholds_entire_map(self):
        target = np.full((2, 2), np.nan, dtype="float32")
        target[0, 0] = 0.2
        result = anomaly_map(
            target, np.full((3, 2, 2), 0.7), np.ones((2, 2), dtype=bool), min_pixels=1
        )
        self.assertEqual(result["summary"]["status"], "withheld")
        self.assertTrue(np.isnan(result["delta"]).all())

    def test_zero_rain_reference_and_missing_months(self):
        rows = [dict(year=y, month=3, mean_mm=0.0) for y in [2020, 2021, 2022, 2023]]
        self.assertIsNone(
            rainfall_comparison(rows, [2020, 2021, 2022], 2023, [3])[
                "ratio_to_reference_median"
            ]
        )
        self.assertEqual(
            rainfall_comparison(rows, [2020, 2021, 2022], 2023, [3, 4])["status"],
            "unavailable",
        )

    def test_future_rain_reference_and_duplicates_rejected(self):
        with self.assertRaises(ValueError):
            rainfall_comparison([], [2023], 2023, [3])
        with self.assertRaises(ValueError):
            rainfall_comparison(
                [dict(year=2023, month=3, mean_mm=1)] * 2, [2022], 2023, [3]
            )

    def test_large_drop_must_also_be_below_every_reference(self):
        target = np.full((1, 1), 0.4, dtype="float32")
        refs = np.array([[[0.3]], [[0.7]], [[0.8]]], dtype="float32")
        result = anomaly_map(target, refs, np.ones((1, 1), dtype=bool), min_pixels=1)
        self.assertLess(result["summary"]["median_delta"], -0.1)
        self.assertFalse(result["low_flag"].any())

    def test_no_crop_and_mismatched_grids_never_produce_healthy_map(self):
        target = np.full((2, 2), 0.6, dtype="float32")
        refs = np.full((3, 2, 2), 0.6, dtype="float32")
        result = anomaly_map(target, refs, np.zeros((2, 2), dtype=bool))
        self.assertEqual(result["summary"]["status"], "withheld")
        self.assertIsNone(result["summary"]["median_delta"])
        self.assertTrue(np.isnan(result["delta"]).all())
        with self.assertRaises(ValueError):
            anomaly_map(target, refs[:, :, :1], np.ones((2, 2), dtype=bool))

    def test_rainfall_missing_values_are_not_zero(self):
        for value in [float("nan"), float("inf"), -1, None]:
            with self.assertRaises(ValueError):
                rainfall_comparison(
                    [dict(year=2023, month=3, mean_mm=value)], [2022], 2023, [3]
                )
