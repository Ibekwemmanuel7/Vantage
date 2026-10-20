import unittest
import numpy as np
from vantage.crop_context import crop_evidence,landcover_masks


class CropContextTests(unittest.TestCase):
    def test_unknown_is_not_noncrop_truth(self):
        crop,known=landcover_masks(np.array([[40,10],[0,255]]))
        self.assertEqual(crop.sum(),1);self.assertEqual(known.sum(),2)

    def test_crop_only_measurements_and_missingness(self):
        classes=np.array([[40,40],[10,10]])
        cube=np.full((6,2,2),.8,dtype='float32');cube[:,:1,:]=.2;cube[:,0,1]=np.nan
        result=crop_evidence(cube,np.isfinite(cube).all(axis=0),classes,min_fraction=.4,min_pixels=1)
        self.assertEqual(result['crop_usable_fraction'],.5)
        self.assertAlmostEqual(result['features']['B02_median'],.2)
        self.assertFalse(result['agronomic_review_eligible'])

    def test_no_cropland_is_unavailable_not_healthy(self):
        cube=np.full((6,2,2),.2)
        result=crop_evidence(cube,np.ones((2,2),dtype=bool),np.full((2,2),10))
        self.assertIsNone(result['crop_usable_fraction']);self.assertIsNone(result['features'])
        self.assertEqual(result['evidence_status'],'insufficient_coverage')

    def test_false_validity_rejected(self):
        cube=np.full((6,2,2),np.nan)
        with self.assertRaises(ValueError):crop_evidence(cube,np.ones((2,2),dtype=bool),np.full((2,2),40))
