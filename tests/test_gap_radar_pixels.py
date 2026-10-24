import unittest
import numpy as np
from vantage.gap_radar_pixels import validate_asset,whole_box_summary,slope_screen_summary,fixed_track_candidates


class GapRadarPixelsTests(unittest.TestCase):
    def test_fixed_track_budget_does_not_mix_or_select_by_values(self):
        plan=dict(track_id="a",max_passes=3)
        candidates=[dict(track_id="a",item_id="later",acquired_at="2023-06-22T00:00:00Z"),
                    dict(track_id="b",item_id="other",acquired_at="2023-06-10T00:00:00Z"),
                    dict(track_id="a",item_id="earlier",acquired_at="2023-06-10T00:00:00Z")]
        self.assertEqual([r["item_id"] for r in fixed_track_candidates(candidates,plan)],["earlier","later"])
        with self.assertRaises(ValueError):fixed_track_candidates(candidates,dict(plan,max_passes=1))
        with self.assertRaises(ValueError):fixed_track_candidates(candidates+[candidates[0]],plan)
    def test_slope_proxy_keeps_unknown_and_numeric_denominators_separate(self):
        classes=np.array([[0,1],[2,1]],dtype="uint8")
        numeric=np.array([[True,True],[True,False]])
        result=slope_screen_summary(classes,numeric)
        self.assertEqual(sum(result["class_counts"].values()),4)
        self.assertEqual(result["numeric_pixels_before"],3)
        self.assertEqual(result["numeric_lower_slope_pixels"],1)
        self.assertFalse(result["radar_illumination_confirmed"])
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
