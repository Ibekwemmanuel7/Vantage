"""Synthetic georeferenced exports test ingestion, not provider performance."""

import json
from pathlib import Path
import tempfile
import unittest

from scripts.compare_radar_processor import read_export
from vantage.radar_benchmark import compare, request_for
import numpy as np
import rasterio

PRODUCT = "S1A_IW_GRDH_1SDV_20230512T155715_20230512T155740_048502_05D599_FBDD"


class BenchmarkIOTests(unittest.TestCase):
    def fixture(self, root, shift=0):
        grid = dict(
            crs="EPSG:32636",
            width=2,
            height=2,
            transform=[20, 0, 600000, 0, -20, 170000, 0, 0, 1],
        )
        request = request_for(grid, PRODUCT)
        (root / "request.json").write_text(json.dumps(request))
        (root / "userdata.json").write_text(
            json.dumps(
                dict(
                    scenes=dict(
                        orbits=[dict(tiles=[dict(sentinel1ProductId=PRODUCT)])]
                    ),
                    inputMetadata=dict(serviceVersion="synthetic-test-only"),
                )
            )
        )
        with rasterio.open(
            root / "default.tif",
            "w",
            driver="GTiff",
            width=2,
            height=2,
            count=3,
            dtype="float32",
            crs=grid["crs"],
            transform=rasterio.Affine(20, 0, 600000 + shift, 0, -20, 170000),
        ) as ds:
            ds.write(
                np.stack(
                    [np.full((2, 2), 35), np.zeros((2, 2)), np.ones((2, 2))]
                ).astype("float32")
            )
        return grid, request

    def test_export_roundtrip_and_metrics(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            grid, request = self.fixture(root)
            data, lineage = read_export(root, request, grid, PRODUCT)
            result = compare(
                np.full((2, 2), 36),
                np.ones((2, 2)),
                np.ones((2, 2)),
                data,
                np.ones((2, 2), dtype=bool),
            )
            self.assertEqual(result["incidence_difference"]["mean_absolute_degrees"], 1)
            self.assertEqual(len(lineage["raster_sha256"]), 64)

    def test_half_pixel_shift_rejected_without_resampling(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            grid, request = self.fixture(root, shift=10)
            with self.assertRaisesRegex(ValueError, "exactly match"):
                read_export(root, request, grid, PRODUCT)

    def test_changed_request_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            grid, request = self.fixture(root)
            actual = json.loads((root / "request.json").read_text())
            actual["input"]["data"][0]["processing"]["demInstance"] = "COPERNICUS_90"
            (root / "request.json").write_text(json.dumps(actual))
            with self.assertRaisesRegex(ValueError, "request differs"):
                read_export(root, request, grid, PRODUCT)

    def test_missing_scene_metadata_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            grid, request = self.fixture(root)
            (root / "userdata.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "scene inventory"):
                read_export(root, request, grid, PRODUCT)
