import unittest
import numpy as np
from vantage.multispectral import BANDS,metadata_parameters,decode_cube,spectral_features,temporal_index


class MultispectralTests(unittest.TestCase):
    def test_offsets_are_band_specific_and_required(self):
        xml='<root><BOA_QUANTIFICATION_VALUE>10000</BOA_QUANTIFICATION_VALUE>'+''.join(
            f'<BOA_ADD_OFFSET band_id="{i}">{-i*10}</BOA_ADD_OFFSET>' for i in (1,2,3,8,11,12))+'</root>'
        q,offsets=metadata_parameters(xml,4)
        self.assertEqual(q,10000)
        self.assertEqual(offsets['B8A'],-80)
        self.assertEqual(offsets['B12'],-120)
        with self.assertRaises(ValueError):metadata_parameters(xml.replace('band_id="12"','band_id="13"'),4)

    def test_missing_bands_and_grids_rejected(self):
        raw={b:np.ones((5,5)) for b in BANDS};raw.pop('B11')
        with self.assertRaises(ValueError):decode_cube(raw,np.full((5,5),4),10000,{b:0 for b in BANDS})

    def test_per_band_missingness_no_filling_and_no_clipping(self):
        raw={b:np.full((5,5),12000,dtype='uint16') for b in BANDS}
        raw['B12'][2,2]=0
        cube,valid,common=decode_cube(raw,np.full((5,5),4),10000,{b:0 for b in BANDS})
        self.assertFalse(common[2,2]);self.assertTrue(valid[0,2,2])
        self.assertTrue(np.isnan(cube[5,2,2]));self.assertGreater(cube[0,0,0],1)

    def test_cloud_buffer_and_empty_features(self):
        raw={b:np.full((5,5),2000) for b in BANDS};scl=np.full((5,5),4);scl[2,2]=9
        cube,valid,common=decode_cube(raw,scl,10000,{b:0 for b in BANDS})
        self.assertFalse(common[2,1]);self.assertTrue(common[0,0])
        self.assertTrue(all(v is None for v in spectral_features(cube,np.zeros((5,5),dtype=bool)).values()))

    def test_temporal_cutoff_order_and_grid_contract(self):
        rows=[dict(scene_id=str(i),acquired_at=f'2024-05-{i:02}T00:00:00Z',grid_id='a',common_usable_fraction=0,artifact_id=str(i)) for i in (3,1)]
        ordered=temporal_index(rows)
        self.assertEqual(ordered[1]['gap_days'],2)
        self.assertEqual(len(temporal_index(rows,'2024-05-02T00:00:00Z')),1)
        rows[0]['grid_id']='b'
        with self.assertRaises(ValueError):temporal_index(rows)

    def test_duplicate_dates_rejected(self):
        row=dict(scene_id='a',acquired_at='2024-05-01T00:00:00Z',grid_id='a',common_usable_fraction=0,artifact_id='a')
        with self.assertRaises(ValueError):temporal_index([row,{**row,'scene_id':'b'}])
