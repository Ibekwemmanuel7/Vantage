import unittest
import numpy as np
from vantage.fusion_samples import make_sample


class FusionSampleTests(unittest.TestCase):
    def inputs(self):
        return dict(power=np.full((2,2,2),.1),support=np.ones((2,2,2)),local_angles=np.full((3,2,2),40.),
            local_classes=np.ones((2,2),dtype="uint8"),visibility_classes=np.ones((2,2),dtype="uint8"),
            slope_classes=np.ones((2,2),dtype="uint8"),ndvi=np.array([[.5,np.nan],[.6,.7]]),
            optical_valid=np.array([[True,False],[True,True]]),radar_age_days=2)

    def test_optical_targets_cannot_change_radar_features(self):
        args=self.inputs()
        first=make_sample(**args)
        args["ndvi"][0,0]=.9
        second=make_sample(**args)
        np.testing.assert_array_equal(first["features"],second["features"])
        self.assertTrue(first["gap_candidate"][0,1])
        self.assertFalse(first["target_valid"][0,1])
        self.assertTrue(np.isnan(first["target_ndvi"][0,1]))

    def test_unknown_or_steep_quality_never_becomes_a_reference(self):
        args=self.inputs()
        args["local_classes"][0,0]=0
        args["slope_classes"][1,0]=2
        result=make_sample(**args)
        self.assertEqual(int(result["target_valid"].sum()),1)
        self.assertTrue(np.isnan(result["features"][:,0,0]).all())

    def test_bad_temporal_or_mask_inputs_rejected(self):
        args=self.inputs()
        for age in [-1,8,np.nan]:
            with self.assertRaises(ValueError):make_sample(**dict(args,radar_age_days=age))
        args["optical_valid"][0,1]=True
        with self.assertRaises(ValueError):make_sample(**args)
