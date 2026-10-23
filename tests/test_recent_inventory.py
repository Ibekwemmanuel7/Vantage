from datetime import datetime, timezone
import json
from pathlib import Path
import unittest
from vantage.recent_inventory import recent_window, summarize_recent


class RecentInventoryTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((Path(__file__).resolve().parents[1]/"configs/uganda_archive.json").read_text())
        self.window = recent_window(self.config, self.config["locations"][0], datetime(2026,10,23,tzinfo=timezone.utc), 21)
        self.item = dict(id="test", collection="sentinel-2-l2a", bbox=[33,0,34,1],
                         properties={"datetime":"2026-10-22T10:00:00Z", "eo:cloud_cover":0},
                         assets={key:{} for key in self.config["required_baseline_assets"]})

    def summary(self, **extra):
        return summarize_recent(self.window, dict(features=[self.item], **extra), self.config, "2026-10-23T01:00:00Z")

    def test_clear_catalog_scene_does_not_imply_usable_crop_observation(self):
        result = self.summary()
        self.assertEqual(result["usable_observation_status"], "not_assessed")
        self.assertFalse(result["field_priorities_available"])
        self.assertIsNone(result["usable_fraction"])
        self.assertAlmostEqual(result["acquisition_age_days"], 14/24)

    def test_wrong_collection_future_and_truncated_search_rejected(self):
        self.item["collection"]="other"
        with self.assertRaises(ValueError): self.summary()
        self.item["collection"]="sentinel-2-l2a"
        self.item["properties"]["datetime"]="2026-10-24T00:00:00Z"
        with self.assertRaises(ValueError): self.summary()
        self.item["properties"]["datetime"]="2026-10-22T00:00:00Z"
        with self.assertRaises(ValueError): self.summary(links=[dict(rel="next")])

    def test_empty_and_invalid_window(self):
        result = summarize_recent(self.window, {"features":[]}, self.config, "now")
        self.assertIsNone(result["latest_catalog_acquisition"])
        with self.assertRaises(ValueError):
            recent_window(self.config, self.config["locations"][0], datetime(2026,10,23,tzinfo=timezone.utc), 32)
