import unittest
import numpy as np
from vantage.gap_baseline import evaluate_persistence, evaluate_masked_persistence


class GapBaselineTests(unittest.TestCase):
    def row(self,date,values):
        return dict(acquired_at=date+"T00:00:00Z",ndvi=np.array([values],dtype=float))

    def test_target_not_used_until_after_scoring(self):
        result=evaluate_persistence([self.row("2026-10-01",[.2,np.nan]),self.row("2026-10-06",[.8,.7])])
        self.assertIsNone(result[0]["mae"])
        self.assertEqual(result[1]["evaluated_pixels"],1)
        self.assertAlmostEqual(result[1]["mae"],.6)

    def test_stale_predictions_withheld_and_missing_target_not_scored(self):
        result=evaluate_persistence([self.row("2026-10-01",[.2,.3]),self.row("2026-10-10",[.8,np.nan])])
        self.assertEqual(result[1]["evaluated_pixels"],0)
        self.assertIsNone(result[1]["mae"])

    def test_duplicate_dates_rejected(self):
        row=self.row("2026-10-01",[.2])
        with self.assertRaises(ValueError):evaluate_persistence([row,row])

    def test_masked_targets_never_refresh_prediction_history(self):
        rows=[self.row("2026-10-01",[.2]),self.row("2026-10-02",[np.nan]),
              self.row("2026-10-03",[.8]),self.row("2026-10-04",[np.nan]),
              self.row("2026-10-05",[.9])]
        result=evaluate_masked_persistence(rows)
        self.assertAlmostEqual(result[2]["mae"],.6)
        self.assertAlmostEqual(result[4]["mae"],.7)
        self.assertEqual(result[4]["mask_source_acquisition"],rows[3]["acquired_at"])

    def test_masked_coverage_reports_abstention(self):
        rows=[self.row("2026-10-01",[.2,np.nan]),self.row("2026-10-02",[np.nan,np.nan]),
              self.row("2026-10-03",[.8,.7])]
        result=evaluate_masked_persistence(rows)[2]
        self.assertEqual(result["hidden_clear_target_pixels"],2)
        self.assertEqual(result["prediction_coverage"],.5)
        self.assertEqual(result["large_error_fraction"],1)
        rows[2]["acquired_at"]="2026-10-20T00:00:00Z"
        result=evaluate_masked_persistence(rows)[2]
        self.assertEqual(result["prediction_coverage"],0)
        self.assertIsNone(result["mae"])

    def test_masked_date_validation_and_ordering(self):
        row=self.row("2026-10-01",[.2])
        with self.assertRaises(ValueError):evaluate_masked_persistence([row,row])
        row["acquired_at"]="2026-10-01T00:00:00"
        with self.assertRaises(ValueError):evaluate_masked_persistence([row])
