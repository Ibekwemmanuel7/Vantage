"""Synthetic projected grids only; no real field claims."""
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

_proj = Path(importlib.util.find_spec("rasterio").origin).parent / "proj_data"
if _proj.is_dir():
    os.environ["PROJ_DATA"] = os.environ["PROJ_LIB"] = str(_proj)

import numpy as np
from affine import Affine
from rasterio.warp import transform_geom
from shapely.geometry import Polygon, MultiPolygon, box, mapping
from vantage.field_pixels import summarize_fields, validate_boundaries

ROOT = Path(__file__).resolve().parents[1]
TRANSFORM = Affine(10, 0, 500000, 0, -10, 100000)


def boundaries(polygon=None):
    polygon = polygon if polygon is not None else box(500012, 99912, 500088, 99988)
    geometry = transform_geom("EPSG:32636", "EPSG:4326", mapping(polygon))
    return dict(type="FeatureCollection", features=[dict(type="Feature", geometry=geometry,
                properties=dict(field_id="synthetic-only", boundary_version="1", consent_ref="synthetic-only",
                                season_id="2026a", crop="maize"))])


class FieldPixelTests(unittest.TestCase):
    def setUp(self):
        self.fields = boundaries()
        self.ndvi = np.full((10, 10), .5)
        self.valid = np.ones((10, 10), dtype=bool)
        self.kwargs = dict(acquired_at="2026-10-20T00:00:00Z", available_at="2026-10-21T00:00:00Z",
                           cutoff="2026-10-24T00:00:00Z", source_ref="synthetic-only")

    def summary(self, fields=None, transform=TRANSFORM, crs="EPSG:32636"):
        return summarize_fields(fields or self.fields, self.ndvi, self.valid, transform, crs, **self.kwargs)

    def test_full_field_support_and_lineage(self):
        result = self.summary()
        field = result["fields"][0]
        self.assertEqual(64, field["selected_grid_pixels"])
        self.assertEqual(1, field["usable_fraction"])
        self.assertEqual(.5, field["observed_ndvi_median"])
        self.assertTrue(field["eligible_for_research_comparison"])
        self.assertEqual(64, len(field["geometry_sha256"]))
        self.assertFalse(result["field_priorities_available"])
        self.assertEqual(0, result["independently_verified_fields"])

    def test_holes_and_multipart_exclude_nonfield_pixels(self):
        outer = box(500012, 99912, 500088, 99988)
        hole = box(500032, 99932, 500068, 99968)
        polygon = Polygon(outer.exterior.coords, [hole.exterior.coords])
        self.assertEqual(48, self.summary(boundaries(polygon))["fields"][0]["selected_grid_pixels"])
        multipart = MultiPolygon([box(500012, 99912, 500038, 99988), box(500062, 99912, 500088, 99988)])
        self.assertEqual(48, self.summary(boundaries(multipart))["fields"][0]["selected_grid_pixels"])

    def test_partial_outside_and_tiny_fields_withheld(self):
        for polygon, reason in ((box(499990, 99912, 500088, 99988), "partial_raster_coverage"),
                                (box(499800, 99912, 499880, 99988), "outside_raster"),
                                (box(500012, 99912, 500013, 99913), "insufficient_field_pixels")):
            field = self.summary(boundaries(polygon))["fields"][0]
            self.assertIn(reason, field["blockers"])
            self.assertFalse(field["eligible_for_research_comparison"])
            self.assertIsNone(field["observed_ndvi_median"])

    def test_missing_pixels_and_staleness_are_not_health(self):
        self.ndvi[:, :5] = np.nan
        self.valid[:, :5] = False
        field = self.summary()["fields"][0]
        self.assertEqual(.5, field["usable_fraction"])
        self.assertIn("insufficient_usable_coverage", field["blockers"])
        self.kwargs["cutoff"] = "2026-10-28T00:00:00Z"
        self.assertIn("stale_observation", self.summary()["fields"][0]["blockers"])
        self.ndvi[:] = np.nan
        self.valid[:] = False
        self.assertIsNone(self.summary()["fields"][0]["observed_ndvi_median"])

    def test_boundary_topology_closure_and_version_checks(self):
        bowtie = Polygon([(500012, 99912), (500088, 99988), (500012, 99988), (500088, 99912), (500012, 99912)])
        with self.assertRaises(ValueError):
            validate_boundaries(boundaries(bowtie))
        for mutate in (lambda f: f["features"][0]["geometry"]["coordinates"][0].pop(),
                       lambda f: f["features"].append(deepcopy(f["features"][0])),
                       lambda f: f["features"][0]["properties"].update(consent_ref=""),
                       lambda f: f.update(crs={"name": "EPSG:4326"})):
            fields = deepcopy(self.fields)
            mutate(fields)
            with self.assertRaises(ValueError):
                validate_boundaries(fields)

    def test_grid_and_observation_contracts(self):
        with self.assertRaises(ValueError):
            self.summary(crs="EPSG:4326")
        with self.assertRaises(ValueError):
            self.summary(transform=Affine(10, 1, 500000, 0, -10, 100000))
        self.kwargs["available_at"] = "2026-10-25T00:00:00Z"
        with self.assertRaises(ValueError):
            self.summary()
        self.kwargs["available_at"] = "2026-10-21T00:00:00Z"
        self.valid[0, 0] = False
        with self.assertRaises(ValueError):
            self.summary()

    def test_small_field_needs_accepted_support_not_coverage_alone(self):
        self.ndvi[6:8, 1] = np.nan
        self.valid[6:8, 1] = False
        field = self.summary(boundaries(box(500012, 99912, 500038, 99938)))["fields"][0]
        self.assertEqual(9, field["selected_grid_pixels"])
        self.assertEqual(7, field["accepted_pixels"])
        self.assertGreater(field["usable_fraction"], .7)
        self.assertIn("insufficient_accepted_pixels", field["blockers"])
        self.assertFalse(field["eligible_for_research_comparison"])
        self.assertIsNone(field["observed_ndvi_median"])

    def test_cli_checks_hash_and_private_exclusive_output(self):
        private = ROOT / "outputs/private"
        private.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private, prefix="field-pixel-test-") as directory:
            directory = Path(directory)
            fields = directory / "synthetic.geojson"
            fields.write_text(json.dumps(self.fields), encoding="utf-8")
            pixels = directory / "synthetic.npz"
            np.savez_compressed(pixels, ndvi=self.ndvi, valid=self.valid, transform=np.array(tuple(TRANSFORM)), crs="EPSG:32636")
            digest = hashlib.sha256(pixels.read_bytes()).hexdigest()
            command = [sys.executable, str(ROOT / "scripts/summarize_field_pixels.py"), str(fields), str(pixels),
                       "--pixels-sha256", digest, "--source-ref", "synthetic-only", "--acquired-at", self.kwargs["acquired_at"],
                       "--available-at", self.kwargs["available_at"], "--cutoff", self.kwargs["cutoff"]]
            output = directory / "report.json"
            result = subprocess.run(command + ["--out", str(output)], capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(0, result.returncode, result.stderr)
            original = output.read_bytes()
            self.assertEqual(digest, json.loads(original)["input_sha256"]["pixels"])
            self.assertEqual(2, subprocess.run(command + ["--out", str(output)], capture_output=True).returncode)
            self.assertEqual(original, output.read_bytes())
            command[command.index(digest)] = "wrong"
            failed = subprocess.run(command + ["--out", str(directory / "bad.json")], capture_output=True, text=True)
            self.assertEqual(2, failed.returncode)
            self.assertFalse((directory / "bad.json").exists())


if __name__ == "__main__":
    unittest.main()
