"""Synthetic private map packaging; no real field records."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tests.test_field_change import observation
from tests.test_field_pixels import ROOT, TRANSFORM, boundaries
import numpy as np
import rasterio
from scripts.build_field_review import build_review
from vantage.field_change import compare_fields


class FieldReviewTests(unittest.TestCase):
    def setUp(self):
        private = ROOT / "outputs/private"
        private.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=private, prefix="field-review-test-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        report, delta, valid = compare_fields(boundaries(), observation(.6, "15", "before"),
            observation(.4, "20", "after"), cutoff="2026-10-24T00:00:00Z")
        self.raster = self.directory / "observed-change.tif"
        with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
            with rasterio.open(self.raster, "w", driver="GTiff", width=10, height=10, count=1, dtype="float32",
                               crs="EPSG:32636", transform=TRANSFORM, nodata=float("nan")) as dst:
                dst.write(delta, 1)
                dst.write_mask(valid.astype("uint8") * 255)
                dst.update_tags(before_acquired_at=report["before"]["acquired_at"],
                                after_acquired_at=report["after"]["acquired_at"], decision_cutoff=report["decision_cutoff"])
        report["change_raster"] = dict(path=self.raster.name, sha256=hashlib.sha256(self.raster.read_bytes()).hexdigest())
        self.report = report
        self.write_report()

    def write_report(self):
        (self.directory / "report.json").write_text(json.dumps(self.report, allow_nan=False), encoding="utf-8")

    def test_map_values_nodata_and_source_hash(self):
        packet = build_review(self.directory)
        preview = packet["preview"]
        values = np.frombuffer(base64.b64decode(preview["values_base64"]), dtype="<i2").reshape(10, 10)
        self.assertEqual(64, int((values == -2000).sum()))
        self.assertEqual(36, int((values == 32767).sum()))
        self.assertEqual(hashlib.sha256((self.directory / "report.json").read_bytes()).hexdigest(), packet["report_file_sha256"])
        self.assertFalse(packet["report"]["field_priorities_available"])

    def test_wrong_hash_grid_or_unsafe_filename_rejected(self):
        for change in ("hash", "grid", "path"):
            original = json.loads(json.dumps(self.report))
            if change == "hash": self.report["change_raster"]["sha256"] = "wrong"
            if change == "grid": self.report["after"]["grid"]["width"] = 11
            if change == "path": self.report["change_raster"]["path"] = "../outside.tif"
            self.write_report()
            with self.assertRaises(ValueError): build_review(self.directory)
            self.report = original

    def test_withheld_report_cannot_show_valid_pixels(self):
        self.report["fields"][0]["eligible_for_research_comparison"] = False
        self.write_report()
        with self.assertRaises(ValueError): build_review(self.directory)

    def test_cli_private_output_and_overwrite_protection(self):
        output = self.directory / "review.json"
        command = [sys.executable, str(ROOT / "scripts/build_field_review.py"), str(self.directory), "--out", str(output)]
        result = subprocess.run(command, capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(0, result.returncode, result.stderr)
        original = output.read_bytes()
        self.assertEqual(2, subprocess.run(command, capture_output=True, cwd=ROOT).returncode)
        self.assertEqual(original, output.read_bytes())
        command[-1] = str(ROOT / "web/forbidden-review.json")
        self.assertEqual(2, subprocess.run(command, capture_output=True, cwd=ROOT).returncode)


if __name__ == "__main__":
    unittest.main()
