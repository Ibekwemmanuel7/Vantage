import hashlib
import json
from pathlib import Path
import unittest
import numpy as np
from vantage.yield_research import FEATURES,buffered_splits,load_cohort,metrics,experiment


class YieldResearchTests(unittest.TestCase):
    def test_buffered_groups_keep_duplicates_and_nearby_points_out_of_training(self):
        xy=np.array([[30+group*.2,1+row*.001] for group in range(6) for row in range(6)])
        xy[1]=xy[0]
        splits=buffered_splits(xy,folds=3,buffer_km=5,minimum=6)
        held=[]
        for train,test,details in splits:
            self.assertTrue(details['disjoint_group_ids'])
            self.assertGreaterEqual(details['minimum_reported_coordinate_distance_km'],5)
            self.assertFalse(set(train)&set(test));held.extend(test)
            if 0 in test:self.assertIn(1,test);self.assertNotIn(1,train)
        self.assertEqual(sorted(held),list(range(len(xy))))

    def test_buffer_failure_never_silently_skips_a_fold(self):
        xy=np.array([[30+group*.11,1+row*.001] for group in range(6) for row in range(6)])
        with self.assertRaises(ValueError):buffered_splits(xy,buffer_km=1000,minimum=6)
        with self.assertRaises(ValueError):buffered_splits(np.array([[30,1]]*10))

    def test_metrics_units_and_bias(self):
        result=metrics(np.array([1000,2000]),np.array([1100,1900]))
        self.assertEqual(result['mae_kg_ha'],100)
        self.assertEqual(result['rmse_kg_ha'],100)
        self.assertEqual(result['bias_kg_ha'],0)

    def test_source_and_feature_allowlist_fail_closed(self):
        raw=b'not the pinned source'
        with self.assertRaises(ValueError):load_cohort(raw,dict(source_sha256='0'*64,features=FEATURES,target='yield_kg_ha'))
        with self.assertRaises(ValueError):load_cohort(raw,dict(source_sha256=hashlib.sha256(raw).hexdigest(),features=['disease'],target='yield_kg_ha'))

    def test_static_context_excludes_outcomes_and_end_of_season_inputs(self):
        blocked={'yield_kg_ha','disease','pest','striga','water_excess','season_prec','season_prec_3','pl_m2','harvest_date','plant_date_dev'}
        self.assertFalse(set(FEATURES)&blocked)
        plan=json.loads((Path(__file__).resolve().parents[1]/'configs/uganda_yield_research.json').read_text())
        self.assertFalse(plan['operational_promotion_allowed'])
        self.assertFalse(plan['satellite_inputs_used'])

    def test_synthetic_end_to_end_baseline_uses_each_training_fold_only(self):
        cohort=[]
        for group in range(6):
            for row in range(6):
                cohort.append(dict(x=[float(group+row+i) for i in range(7)],y=float(1000+group*200+row*10),
                                   xy=[30+group*.2,1+row*.001],labels={k:'FALSE' for k in ('disease','pest','striga','water_excess')}))
        plan=dict(task='Synthetic software test only',models={'ridge':{'alpha':10},'random_forest':{'n_estimators':3,'max_depth':2,'min_samples_leaf':3}},random_seed=42,folds=3,group_cell_degrees=.1,buffer_km=5,minimum_training_rows=6)
        report,predictions=experiment(cohort,plan)
        for train,test,_ in buffered_splits([r['xy'] for r in cohort],3,.1,5,6):
            np.testing.assert_allclose(predictions['median'][test],np.median([cohort[i]['y'] for i in train]))
        self.assertFalse(report['operational_promotion_allowed'])
        self.assertFalse(report['satellite_model_fitted'])
        self.assertTrue(all(np.isfinite(v).all() for v in predictions.values()))


if __name__=='__main__':unittest.main()
