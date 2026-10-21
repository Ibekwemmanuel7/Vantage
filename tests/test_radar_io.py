"""Cached native-raster integration: resample intensity before converting to dB."""

import tempfile
import unittest
from pathlib import Path
import numpy as np
from scripts.build_radar_series import native_clip
from vantage.archive import fingerprint
from vantage.radar_values import decibels


class RadarIOTests(unittest.TestCase):
    def cached_sample(self, raw):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        grid = dict(
            width=1,
            height=1,
            crs="EPSG:32636",
            transform=[20, 0, 0, 0, -20, 20, 0, 0, 1],
        )
        href = "https://example.com/unused.tiff"
        identity = fingerprint(dict(href=href, grid=grid, native_margin_pixels=2))[:24]
        np.savez_compressed(
            root / (identity + ".npz"),
            raw=np.array(raw, dtype="float32"),
            transform=np.array([10, 0, 0, 0, -10, 20, 0, 0, 1]),
            epsg=np.array(32636),
        )

        def no_network(_):
            self.fail("Cached native clips must not request a token")

        result = native_clip(href, grid, root, False, no_network)
        temporary.cleanup()
        return result

    def test_linear_average_precedes_log_conversion(self):
        power, support, _ = self.cached_sample([[1, 100], [1, 100]])
        self.assertAlmostEqual(float(power[0, 0]), 50.5)
        self.assertAlmostEqual(
            float(decibels(power)[0, 0]), 10 * np.log10(50.5), places=5
        )
        self.assertNotAlmostEqual(float(decibels(power)[0, 0]), 10)
        self.assertEqual(float(support[0, 0]), 1)

    def test_nonpositive_native_samples_are_not_averaged_as_real_intensity(self):
        power, support, _ = self.cached_sample([[1, -32768], [np.nan, 0]])
        self.assertEqual(float(power[0, 0]), 1)
        self.assertEqual(float(support[0, 0]), 0.25)
        self.assertLess(float(support[0, 0]), 0.8)
