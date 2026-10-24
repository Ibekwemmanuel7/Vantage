import unittest
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch
import numpy as np
from vantage.event_reconstruction import rainfall_comparison, optical_difference


class ReconstructionTests(unittest.TestCase):
    def months(self):
        return {(y,m):np.full((2,2),100 if y < 2024 else 50)
                for y in [*range(1981,2021),2024] for m in (3,4,5)}

    def test_seasonal_total_and_departure(self):
        result = rainfall_comparison(self.months(),2024,list(range(1981,2021)))
        self.assertAlmostEqual(result['baseline_mam_mean_mm'],300)
        self.assertAlmostEqual(result['target_mam_mm'],150)
        self.assertAlmostEqual(result['departure_mm'],-150)
        self.assertAlmostEqual(result['departure_percent'],-50)

    def test_missing_month_invalid_cell_and_target_leakage_rejected(self):
        values = self.months(); del values[1981,3]
        with self.assertRaises(ValueError): rainfall_comparison(values,2024,list(range(1981,2021)))
        for invalid in (np.nan,-1):
            values=self.months();values[1981,3]=np.full((2,2),invalid)
            with self.assertRaises(ValueError): rainfall_comparison(values,2024,list(range(1981,2021)))
        with self.assertRaises(ValueError): rainfall_comparison(self.months(),2024,[*range(1981,2021),2024])

    def test_zero_rain_is_valid_but_percent_is_undefined(self):
        values = {key:np.zeros((2,2)) for key in self.months()}
        result=rainfall_comparison(values,2024,list(range(1981,2021)))
        self.assertEqual(result['departure_mm'],0)
        self.assertIsNone(result['departure_percent'])

    def test_common_support_and_real_zero_are_preserved(self):
        before=np.full((4,4),.5);after=before.copy();before[0,0]=np.nan;after[1,1]=np.nan
        delta,result=optical_difference(before,np.isfinite(before),after,np.isfinite(after))
        self.assertEqual(result['common_pixels'],14)
        self.assertTrue(result['coverage_qualified'])
        self.assertEqual(result['median_ndvi_difference'],0)
        self.assertTrue(np.isnan(delta[0,0]));self.assertEqual(delta[2,2],0)

    def test_insufficient_coverage_has_no_summary(self):
        before=np.full((4,4),.5);after=before.copy();after[:2]=np.nan
        _,result=optical_difference(before,np.isfinite(before),after,np.isfinite(after))
        self.assertFalse(result['coverage_qualified']);self.assertIsNone(result['median_ndvi_difference'])

    def test_invalid_mask_or_ndvi_rejected(self):
        before=np.ones((4,4));valid=np.ones((4,4),dtype=bool)
        with self.assertRaises(ValueError): optical_difference(before,valid.astype(int),before,valid)
        invalid=before.copy();invalid[0,0]=2
        with self.assertRaises(ValueError): optical_difference(invalid,valid,before,valid)

    def test_native_window_extract_and_offline_replay(self):
        from scripts.reconstruct_lira_event import acquire
        from rasterio.transform import Affine
        import rasterio
        source=MagicMock()
        source.crs=rasterio.crs.CRS.from_epsg(4326);source.count=1
        source.transform=Affine(.050000000745,0,-180,0,-.050000000745,60)
        source.read.return_value=np.ma.array(np.full((2,2),100.0),mask=False)
        source.tags.return_value={'TIFFTAG_DATETIME':'synthetic test'}
        source.window_transform.return_value=Affine(.05,0,32.85,0,-.05,2.30)
        source.__enter__.return_value=source
        plan={'bbox':[32.85,2.2,32.95,2.3],'rain_base_url':'https://example.test/'}
        with tempfile.TemporaryDirectory() as directory:
            with patch('scripts.reconstruct_lira_event.rasterio.open',return_value=source):
                first=acquire(Path(directory),plan,2024,5,True)
            second=acquire(Path(directory),plan,2024,5,False)
            self.assertEqual(first,second)
            self.assertEqual(source.read.call_args.kwargs['window'].width,2)
            self.assertEqual(first[1],[[100,100],[100,100]])

    def test_incomplete_rain_cache_never_triggers_network_offline(self):
        from scripts.reconstruct_lira_event import acquire
        with tempfile.TemporaryDirectory() as directory:
            with patch('scripts.reconstruct_lira_event.rasterio.open') as remote:
                with self.assertRaises(ValueError):
                    acquire(Path(directory),{'rain_base_url':'https://example.test/'},2024,5,False)
                remote.assert_not_called()


if __name__=='__main__':unittest.main()
