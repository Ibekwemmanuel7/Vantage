import unittest
import numpy as np
from vantage.gap_baseline import evaluate_persistence


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
