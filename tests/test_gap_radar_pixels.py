import unittest
import numpy as np
from vantage.gap_radar_pixels import validate_asset,whole_box_summary


class GapRadarPixelsTests(unittest.TestCase):
    def test_provider_units_and_scale_contract(self):
        asset={"description":"Terrain-corrected gamma naught values", "raster:bands":[dict(nodata=-32768,data_type="float32")]}
        validate_asset(asset)
        asset["raster:bands"][0]["scale"]=.1
        with self.assertRaises(ValueError):validate_asset(asset)

    def test_partial_support_and_nonpositive_power_excluded(self):
        power=np.ones((2,2,2))
        support=np.ones_like(power)
        power[0,0,0]=0
        support[1,1,1]=.5
        summary=whole_box_summary(power,support)
        self.assertEqual(summary["numeric_pixels"],2)
        self.assertEqual(summary["numeric_fraction"],.5)
        self.assertEqual(summary["vv_db_median"],0)
        self.assertFalse(summary["usable_agricultural_evidence"])
