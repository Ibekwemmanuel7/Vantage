import unittest
import numpy as np
from vantage.gap_learning import causal_samples,fit_residual,score_samples


class GapLearningTests(unittest.TestCase):
    def row(self,day,value):
        return dict(acquired_at=f"2023-05-{day:02}T00:00:00Z",ndvi=np.array([[value]],dtype=float))

    def test_hidden_targets_never_update_features(self):
        samples=causal_samples([self.row(1,.2),self.row(2,np.nan),self.row(3,.8),self.row(4,np.nan),self.row(5,.9)])
        self.assertAlmostEqual(samples[2]["persistence"][0],.2)
        self.assertAlmostEqual(samples[4]["persistence"][0],.2)
        self.assertAlmostEqual(samples[4]["features"][0,2],4/7)

    def test_empty_training_rejected_and_expired_samples_withheld(self):
        with self.assertRaises(ValueError):fit_residual([])
        samples=causal_samples([self.row(1,.2),self.row(2,np.nan),self.row(15,.8)])
        self.assertEqual(len(samples[-1]["target"]),0)

    def test_clear_transition_training_scores_before_updating(self):
        samples=causal_samples([self.row(1,.2),self.row(3,.8)],transferred_masks=False)
        self.assertEqual(len(samples[0]["target"]),0)
        self.assertAlmostEqual(samples[1]["persistence"][0],.2)
        self.assertAlmostEqual(samples[1]["target"][0],.8)

    def test_isolated_gaps_use_original_history_only_after_scoring(self):
        rows=[self.row(1,.2),self.row(2,np.nan),self.row(3,.8),self.row(4,np.nan),self.row(5,.9)]
        isolated=causal_samples(rows,isolated_gaps=True)
        sequential=causal_samples(rows)
        self.assertAlmostEqual(isolated[2]["persistence"][0],.2)
        self.assertAlmostEqual(isolated[4]["persistence"][0],.8)
        self.assertAlmostEqual(sequential[4]["persistence"][0],.2)

    def test_missingness_reasons_account_for_all_hidden_targets(self):
        rows=[self.row(1,.2),self.row(2,np.nan),self.row(15,.8)]
        sample=causal_samples(rows)[2]
        self.assertEqual(sample["unsupported_expired_prior"],1)
        self.assertEqual(sample["hidden_pixels"],len(sample["target"])+sample["unsupported_no_prior"]+sample["unsupported_expired_prior"])
        rows=[self.row(1,np.nan),self.row(2,.8)]
        self.assertEqual(causal_samples(rows)[1]["unsupported_no_prior"],1)

    def test_repeatable_fit_and_same_support_comparison(self):
        samples=causal_samples([self.row(1,.2),self.row(2,np.nan),self.row(3,.8)])
        model=fit_residual(samples)
        self.assertEqual(model,fit_residual(samples))
        scored=score_samples(samples,model)
        self.assertEqual(scored["predicted_pixel_date_pairs"],1)
        self.assertAlmostEqual(scored["persistence_mae"],.6)
        self.assertIsNotNone(scored["learned_mae"])
