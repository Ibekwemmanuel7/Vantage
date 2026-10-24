import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from scripts.check_gap_radar_quality import save_arrays,annotation_bytes


class GapQualityWorkflowTests(unittest.TestCase):
    def test_replay_checks_arrays_without_overwriting_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/"quality.npz"
            values=np.array([[np.nan,1.]])
            save_arrays(path,angles=values)
            before=path.read_bytes()
            save_arrays(path,angles=values)
            self.assertEqual(path.read_bytes(),before)
            with self.assertRaises(ValueError):save_arrays(path,angles=np.array([[np.nan,2.]]))
            self.assertEqual(path.read_bytes(),before)

    def test_offline_annotation_rechecks_safe_integrity_without_network(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            raw=b"<product/>"
            (root/"0-annotation.xml").write_bytes(raw)
            (root/"0-grd.json").write_text(json.dumps({"assets":{"safe-manifest":{"href":"https://example.blob.core.windows.net/container/manifest.safe"}}}))
            (root/"0-manifest.xml").write_text(f'''<root><dataObject repID="s1Level1ProductSchema"><byteStream size="{len(raw)}"><fileLocation href="./annotation/product-vv.xml"/><checksum checksumName="MD5">{hashlib.md5(raw).hexdigest()}</checksum></byteStream></dataObject></root>''')
            item={"links":[{"rel":"derived_from","href":"https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-1-grd/items/test"}]}
            def no_network(_):self.fail("Offline replay must not obtain tokens")
            result,lineage=annotation_bytes(0,item,root,False,no_network)
            self.assertEqual(result,raw)
            self.assertEqual(lineage["annotation_sha256"],hashlib.sha256(raw).hexdigest())
            (root/"0-annotation.xml").write_bytes(b"<tampered/>")
            with self.assertRaises(ValueError):annotation_bytes(0,item,root,False,no_network)
