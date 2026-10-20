import json
import os
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

import numpy as np
from rasterio.transform import from_origin
from scripts.prepare_ml_dataset import write_cog
from scripts.prepare_multispectral import validate_scene
from vantage.imagery import sha256_file
from vantage.multispectral import BANDS,load_sequence


class MultispectralIOTests(unittest.TestCase):
    def fixture(self,root):
        folder=root/'artifact';folder.mkdir()
        transform=from_origin(500000,100000,20,20)
        cube=np.full((6,8,8),.2,dtype='float32');cube[:,2,2]=np.nan
        valid=np.isfinite(cube).astype('uint8');common=valid.all(axis=0).astype('uint8')
        assets={}
        for name,array,bands in [('reflectance',cube,list(BANDS)),('band_valid',valid,[b+'_valid' for b in BANDS]),('common_valid',common,['all_six_bands_valid'])]:
            path=folder/(name+'.tif');write_cog(path,array,transform,bands)
            assets[name]=dict(href=path.name,sha256=sha256_file(path),bands=bands)
        return dict(scene_id='synthetic-only',artifact_id='artifact',location_id='test',acquired_at='2024-05-01T00:00:00Z',
                    grid_id='grid',grid=dict(crs='EPSG:32636',transform=list(transform),height=8,width=8),assets=assets,common_usable_fraction=63/64)

    def test_real_cog_roundtrip_and_sequence_masks(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);record=self.fixture(root)
            validate_scene(record,root)
            sequence=load_sequence(dict(scenes=[record]),root,'test')
            self.assertEqual(sequence['reflectance'].shape,(1,6,8,8))
            self.assertFalse(sequence['common_valid'][0,2,2])
            self.assertTrue(np.isnan(sequence['reflectance'][0,:,2,2]).all())
            self.assertFalse(sequence['foundation_ready'])
            with self.assertRaises(ValueError):load_sequence(dict(scenes=[record]),root,'test','2024-04-01T00:00:00Z')

    def test_tampered_asset_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);record=self.fixture(root)
            record['assets']['reflectance']['sha256']='tampered'
            with self.assertRaises(ValueError):load_sequence(dict(scenes=[record]),root,'test')

    def test_outside_root_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);record=self.fixture(root)
            record['assets']['reflectance']['href']='../../outside.tif'
            with self.assertRaises(ValueError):load_sequence(dict(scenes=[record]),root,'test')

    def test_standalone_loader_uses_matching_projection_database(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);record=self.fixture(root)
            manifest=root/'manifest.json';manifest.write_text(json.dumps(dict(scenes=[record])))
            env={**os.environ,'PROJ_DATA':str(root/'wrong-proj'),'PROJ_LIB':str(root/'wrong-proj')}
            child=subprocess.run([sys.executable,'-c',
                'import sys; from vantage.multispectral import load_sequence; print(load_sequence(sys.argv[1],sys.argv[2],"test")["reflectance"].shape)',
                str(manifest),str(root)],capture_output=True,text=True,env=env)
            self.assertEqual(child.returncode,0,child.stderr)
            self.assertIn('(1, 6, 8, 8)',child.stdout)
