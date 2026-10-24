"""Synthetic paired observations; no agricultural validation claims."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tests.test_field_pixels import ROOT, TRANSFORM, boundaries
import numpy as np
import rasterio
from vantage.field_change import compare_fields


def observation(value, date, name):
    return dict(ndvi=np.full((10, 10), value), valid=np.ones((10, 10), dtype=bool),
                transform=np.array(tuple(TRANSFORM)), crs="EPSG:32636", acquired_at=f"2026-10-{date}T00:00:00Z",
                available_at=f"2026-10-{date}T12:00:00Z", source_ref=name, recipe_ref="synthetic-observed-recipe")


class FieldChangeTests(unittest.TestCase):
    def setUp(self):
        self.before = observation(.6, "15", "synthetic-before")
        self.after = observation(.4, "20", "synthetic-after")
        self.fields = boundaries()
        self.cutoff = "2026-10-24T00:00:00Z"

    def compare(self):
        return compare_fields(self.fields, self.before, self.after, cutoff=self.cutoff)

    def test_known_decrease_and_map_support(self):
        report, delta, valid = self.compare()
        field = report["fields"][0]
        self.assertEqual(64, field["common_valid_pixels"])
        self.assertAlmostEqual(-.2, field["median_paired_ndvi_change"])
        self.assertEqual(64, field["declining_pixel_count"])
        self.assertEqual(0, field["increasing_pixel_count"])
        self.assertEqual(64, valid.sum())
        self.assertTrue(np.isnan(delta[~valid]).all())
        self.assertTrue(np.allclose(delta[valid], -.2))
        self.assertFalse(report["field_priorities_available"])

    def test_separate_clear_coverage_is_not_common_coverage(self):
        self.before["valid"][:, 1:3] = False
        self.before["ndvi"][:, 1:3] = np.nan
        self.after["valid"][:, 7:9] = False
        self.after["ndvi"][:, 7:9] = np.nan
        report, delta, valid = self.compare()
        self.assertTrue(report["before"]["fields"][0]["eligible_for_research_comparison"])
        self.assertTrue(report["after"]["fields"][0]["eligible_for_research_comparison"])
        field = report["fields"][0]
        self.assertEqual(.5, field["common_usable_fraction"])
        self.assertIn("insufficient_common_coverage", field["blockers"])
        self.assertIsNone(field["median_paired_ndvi_change"])
        self.assertFalse(valid.any())
        self.assertTrue(np.isnan(delta).all())

    def test_paired_statistics_ignore_unmatched_pixels(self):
        self.before["ndvi"][:] = .5
        self.after["ndvi"][:] = .5
        self.before["ndvi"][:, 1] = -.9
        self.after["valid"][:, 1] = False
        self.after["ndvi"][:, 1] = np.nan
        report, delta, valid = self.compare()
        self.assertEqual(0, report["fields"][0]["mean_paired_ndvi_change"])
        self.assertTrue((delta[valid] == 0).all())

    def test_reject_wrong_grid_recipe_or_time_order(self):
        for change in (dict(crs="EPSG:32637"), dict(recipe_ref="another-recipe"),
                       dict(acquired_at=self.before["acquired_at"]), dict(source_ref=self.before["source_ref"])):
            original = deepcopy(self.after)
            self.after.update(change)
            with self.assertRaises(ValueError):
                self.compare()
            self.after = original
        self.after["transform"][2] += 1
        with self.assertRaises(ValueError):
            self.compare()

    def test_stale_or_widely_separated_dates_withhold_map(self):
        self.cutoff = "2026-10-28T00:00:00Z"
        report, _, valid = self.compare()
        self.assertIn("after_stale_observation", report["fields"][0]["blockers"])
        self.assertFalse(valid.any())

    def test_earlier_reference_can_be_older_than_latest_freshness_limit(self):
        self.before["acquired_at"] = "2026-09-29T00:00:00Z"
        report, _, valid = self.compare()
        self.assertEqual(21, report["pair_interval_days"])
        self.assertGreater(report["before"]["age_days"], 7)
        self.assertTrue(report["fields"][0]["eligible_for_research_comparison"])
        self.assertEqual(64, valid.sum())
        self.cutoff = "2026-10-24T00:00:00Z"
        self.before["acquired_at"] = "2026-09-20T00:00:00Z"
        report, _, valid = self.compare()
        self.assertIn("pair_interval_exceeds_policy", report["fields"][0]["blockers"])
        self.assertFalse(valid.any())

    def test_cli_geotiff_mask_metadata_hashes_and_no_overwrite(self):
        # True zero change must remain valid, rather than becoming nodata.
        self.after["ndvi"][:] = .6
        private = ROOT / "outputs/private"
        private.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private, prefix="field-change-test-") as temporary:
            directory = Path(temporary)
            (directory / "fields.geojson").write_text(json.dumps(self.fields), encoding="utf-8")
            spec = dict(boundaries="fields.geojson", cutoff=self.cutoff)
            for name, scene in (("before", self.before), ("after", self.after)):
                path = directory / f"{name}.npz"
                np.savez_compressed(path, **{key: scene[key] for key in ("ndvi", "valid", "transform", "crs")})
                spec[name] = {key: scene[key] for key in ("acquired_at", "available_at", "source_ref", "recipe_ref")}
                spec[name].update(pixels=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            input_path = directory / "pair.json"
            input_path.write_text(json.dumps(spec), encoding="utf-8")
            output = directory / "comparison"
            command = [sys.executable, str(ROOT / "scripts/compare_field_pixels.py"), str(input_path), "--out-dir", str(output)]
            result = subprocess.run(command, capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(0, result.returncode, result.stderr)
            raster = output / "observed-change.tif"
            report = json.loads((output / "report.json").read_text())
            self.assertEqual(hashlib.sha256(raster.read_bytes()).hexdigest(), report["change_raster"]["sha256"])
            with rasterio.open(raster) as source:
                self.assertEqual(TRANSFORM, source.transform)
                self.assertEqual("EPSG:32636", source.crs.to_string())
                mask = source.read_masks(1) != 0
                self.assertEqual(64, mask.sum())
                self.assertTrue(np.isnan(source.read(1)[~mask]).all())
                self.assertTrue((source.read(1)[mask] == 0).all())
                self.assertEqual(self.after["acquired_at"], source.tags()["after_acquired_at"])
            original = raster.read_bytes()
            self.assertEqual(2, subprocess.run(command, capture_output=True).returncode)
            self.assertEqual(original, raster.read_bytes())
            spec["before"]["sha256"] = "wrong"
            input_path.write_text(json.dumps(spec), encoding="utf-8")
            command[-1] = str(directory / "bad")
            self.assertEqual(2, subprocess.run(command, capture_output=True).returncode)
            self.assertFalse((directory / "bad").exists())


if __name__ == "__main__":
    unittest.main()
