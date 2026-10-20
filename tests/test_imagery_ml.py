import copy
from contextlib import closing
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from vantage.imagery import decode_metadata,derive_scene,zone_features,rgba_rgb,rgba_ndvi,stable_hash
from vantage.ml import FEATURES,feature_matrix,novelty_experiment,supervised_experiment,validate_labels,bbox_distance_m,build_features,publish_label_template

ROOT=Path(__file__).resolve().parents[1]


def sample(identifier,year,group,longitude=33.,value=.6):
    return dict(sample_id=identifier,dataset_id="synthetic-test-only",unit_id=identifier,year=year,
        profile_id="synthetic",spatial_group=group,eligible=True,exclusion_reasons=[],
        geometry={"type":"Polygon","coordinates":[[[longitude,0],[longitude+.01,0],[longitude+.01,.01],[longitude,.01],[longitude,0]]]},
        acquired_at=f"{year}-05-14T10:00:00Z",features=dict(ndvi_median=value,ndvi_iqr=.08,red_median=.05,nir_median=.25,rainfall_mm=20))


class ImageryTests(unittest.TestCase):
    def test_band_offsets_and_no_data_do_not_create_false_ndvi(self):
        text='<root><BOA_QUANTIFICATION_VALUE>10000</BOA_QUANTIFICATION_VALUE>'+''.join(f'<BOA_ADD_OFFSET band_id="{i}">-1000</BOA_ADD_OFFSET>' for i in [1,2,3,7])+'</root>'
        q,offsets=decode_metadata(text,"05.11")
        raw={"B04":np.full((7,7),2000),"B08":np.full((7,7),4000)}
        raw["B04"][0,0]=0
        reflectance,valid,ndvi=derive_scene(raw,np.full((7,7),4),q,offsets)
        self.assertAlmostEqual(float(ndvi[3,3]),.5,places=6)
        self.assertFalse(valid[0,0]);self.assertTrue(np.isnan(ndvi[0,0]))
        self.assertAlmostEqual(float(reflectance["B04"][3,3]),.1,places=6)
        with self.assertRaises(ValueError):decode_metadata('<root><BOA_QUANTIFICATION_VALUE>10000</BOA_QUANTIFICATION_VALUE></root>',"05.11")

    def test_cloud_buffer_and_grid_mismatch(self):
        raw={"B04":np.full((7,7),1000),"B08":np.full((7,7),3000)}
        scl=np.full((7,7),4);scl[3,3]=9
        _,valid,ndvi=derive_scene(raw,scl,10000,{"B04":0,"B08":0})
        self.assertFalse(valid[3,3]);self.assertFalse(valid[3,2]);self.assertTrue(valid[0,0])
        self.assertEqual(int(np.isfinite(ndvi).sum()),44)
        raw["B08"]=np.ones((6,7))
        with self.assertRaises(ValueError):derive_scene(raw,scl,10000,{"B04":0,"B08":0})

    def test_preview_alpha_and_no_rgb_fabrication(self):
        ndvi=np.array([[.4,np.nan]],dtype=np.float32)
        self.assertEqual(rgba_ndvi(ndvi)[0,1,3],0)
        self.assertIsNone(rgba_rgb({"B04":ndvi},np.isfinite(ndvi)))
        a=np.array([[.1,.2]],dtype=np.float32)
        rgb=rgba_rgb({"B02":a,"B03":a,"B04":a},np.array([[True,False]]))
        self.assertEqual(rgb[0,1,3],0)

    def test_excluded_pixels_do_not_enter_features(self):
        ndvi=np.array([[.5,np.nan],[.7,.9]])
        mask=np.array([[True,True],[True,False]])
        f=zone_features({"B04":np.ones((2,2))*.1,"B08":np.ones((2,2))*.3},ndvi,mask)
        self.assertEqual(f["valid_pixels"],2)
        self.assertAlmostEqual(f["usable_fraction"],2/3)
        self.assertAlmostEqual(f["ndvi_median"],.6)


class MLTests(unittest.TestCase):
    def test_independent_annotations_are_preserved_and_not_published(self):
        with tempfile.TemporaryDirectory(dir=ROOT/"outputs") as tmp:
            local,public=Path(tmp)/"labels.csv",Path(tmp)/"public.csv"
            local.write_text('sample_id,outcome,reference_ref\nprivate,useful_finding,PRIVATE-REFERENCE\n')
            rows=[sample("example",2024,"group")]
            original=local.read_bytes()
            publish_label_template(rows,local,public)
            self.assertEqual(local.read_bytes(),original)
            self.assertNotIn("PRIVATE-REFERENCE",public.read_text())
            with public.open(encoding="utf-8",newline="") as stream:
                self.assertTrue(all(not r["outcome"] for r in csv.DictReader(stream)))

    def test_no_acquisition_years_remain_explicit_missing_slots(self):
        config=json.loads((ROOT/"configs/uganda_iganga.json").read_text())
        manifest=dict(dataset_id="synthetic",recipe=dict(config=config),profile_id="synthetic",bbox=config["bbox"],
                      reference_years=config["reference_years"],target_year=2024,decision_cutoff=config["as_of"],
                      quality_policy=dict(min_usable_fraction=.6,min_valid_pixels=100))
        rows=build_features(manifest,[],[])
        self.assertEqual(len(rows),20)
        self.assertTrue(all(not r["eligible"] and r["acquired_at"] is None and "no_acquisition" in r["exclusion_reasons"] for r in rows))

    def novelty_rows(self):
        rows=[sample(f"ref-{year}-{i}",year,"same-area",value=.55+i*.01) for year in [2020,2022,2023] for i in range(4)]
        rows.append(sample("target",2024,"same-area"))
        rows.append({**sample("cloudy",2024,"same-area"),"eligible":False,"exclusion_reasons":["insufficient_coverage"]})
        return rows

    def test_novelty_is_reproducible_and_keeps_quality_gaps(self):
        first,_=novelty_experiment(self.novelty_rows(),2024)
        second,_=novelty_experiment(self.novelty_rows(),2024)
        self.assertEqual(first,second)
        self.assertEqual(first["training_samples"],12)
        self.assertIsNone(first["accuracy"])
        self.assertEqual(first["predictions"][1]["status"],"unavailable")

    def test_target_values_never_change_fitted_scaler(self):
        rows=self.novelty_rows()
        _,a=novelty_experiment(rows,2024)
        rows[-2]["features"]["rainfall_mm"]=1000
        _,b=novelty_experiment(rows,2024)
        np.testing.assert_array_equal(a.steps[0][1].center_,b.steps[0][1].center_)
        np.testing.assert_array_equal(a.steps[1][1].estimators_[0].tree_.threshold,b.steps[1][1].estimators_[0].tree_.threshold)

    def test_no_labels_never_trains_classifier(self):
        report,model=supervised_experiment(self.novelty_rows(),[])
        self.assertFalse(report["model_trained"]);self.assertIsNone(model)
        self.assertIsNone(novelty_experiment(self.novelty_rows()[:2],2024)[1])

    def test_demo_and_duplicate_labels_rejected(self):
        r=sample("a",2020,"A")
        label=dict(sample_id="a",dataset_id=r["dataset_id"],outcome="useful_finding",split="train",label_kind="demo",independently_verified="true",reference_ref="synthetic",observed_at="2020-05-15T00:00:00Z",sampling_method="flagged")
        _,errors=validate_labels([r],[label,label])
        self.assertTrue(any("demo/weak" in e for e in errors))
        self.assertTrue(any("duplicate" in e for e in errors))

    def test_spatial_leakage_fails_even_with_renamed_groups(self):
        rows=[];labels=[]
        for i,(year,split) in enumerate([(2020,"train"),(2023,"validation"),(2024,"test")]):
            r=sample(str(i),year,str(i),longitude=33)
            rows.append(r)
            labels.append(dict(sample_id=r["sample_id"],dataset_id=r["dataset_id"],outcome="useful_finding",split=split,label_kind="field_visit",independently_verified="true",reference_ref="synthetic-test",observed_at=f"{year}-05-15T00:00:00Z",sampling_method="routine"))
        _,errors=validate_labels(rows,labels)
        self.assertTrue(any("neighboring geometry" in e for e in errors))
        self.assertEqual(bbox_distance_m((0,0,1,1),(.5,.5,2,2)),0)
        self.assertGreater(bbox_distance_m((0,0,.01,.01),(1,0,1.01,.01)),100000)

    def test_supervised_runner_works_on_explicit_synthetic_test_cohorts(self):
        rows=[];labels=[]
        for split,year,groups in [("train",2020,[0,1,2]),("validation",2023,[4]),("test",2024,[6])]:
            for g in groups:
                for i in range(12):
                    r=sample(f"{split}-{g}-{i}",year,str(g),longitude=20+g,value=.3 if i%2 else .7)
                    r["features"]["rainfall_mm"]=2 if i%2 else 25
                    rows.append(r)
                    labels.append(dict(sample_id=r["sample_id"],dataset_id=r["dataset_id"],outcome="useful_finding" if i%2 else "no_useful_finding",split=split,label_kind="field_visit",independently_verified="true",reference_ref="SYNTHETIC UNIT TEST ONLY",observed_at=f"{year}-05-15T00:00:00Z",sampling_method="presampled_unflagged"))
        report,model=supervised_experiment(rows,labels)
        self.assertTrue(report["model_trained"]);self.assertIsNotNone(model)
        self.assertEqual(report["test_samples"],12)
        self.assertFalse(report["probabilities_calibrated"])


class ArtifactTests(unittest.TestCase):
    def test_generated_geospatial_assets_match_catalog_and_coherent_grid(self):
        catalog_path=ROOT/"web/data/imagery.json"
        if not catalog_path.exists():self.skipTest("Build the local public-data dataset first")
        from scripts import build_uganda_demo  # Select the matching wheel PROJ database.
        import rasterio
        catalog=json.loads(catalog_path.read_text())
        path=ROOT/"outputs/ml/datasets"/catalog["dataset_id"]
        if not path.exists():self.skipTest("Local raster artifact cache is not distributed in source control")
        from vantage.imagery import sha256_file
        m=json.loads((path/"manifest.json").read_text())
        self.assertEqual(stable_hash(m["recipe"])[:20],m["dataset_id"])
        self.assertEqual(sha256_file(path/"observations.jsonl"),m["observations_sha256"])
        for scene in catalog["scenes"]:
            for asset,digest in scene["hashes"].items():
                raster=path/"assets"/(scene["id"]+"-"+asset+".tif")
                self.assertEqual(sha256_file(raster),digest)
                with rasterio.open(raster) as src:
                    self.assertEqual((src.height,src.width),tuple(m["shape"]))
                    self.assertEqual(src.crs.to_epsg(),32636)
                    self.assertEqual(list(src.transform),m["transform"])
                    self.assertEqual(src.tags(ns="IMAGE_STRUCTURE").get("LAYOUT"),"COG")


if __name__=="__main__":unittest.main()
