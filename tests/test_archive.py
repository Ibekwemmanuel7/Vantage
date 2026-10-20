import unittest
from vantage.archive import windows,summarize_window


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.config=dict(locations=[dict(id="study",bbox=[33.4,.65,33.5,.75])],years=[2024],months=[2],
                         required_baseline_assets=["B04"],candidate_multispectral_assets=["B04","B11"])

    def test_leap_year_and_bounded_geometry(self):
        self.assertIn("2024-02-29",list(windows(self.config))[0]["interval"])
        self.config["locations"][0]["bbox"]=[0,0,10,10]
        with self.assertRaises(ValueError):list(windows(self.config))

    def test_incomplete_search_rejected(self):
        with self.assertRaises(ValueError):summarize_window(list(windows(self.config))[0],dict(features=[],links=[dict(rel="next")]),self.config)

    def test_no_cloud_filter_or_invented_quality(self):
        item=dict(id="scene",bbox=[33,0,34,1],assets={"B04":{}},properties={"datetime":"2024-02-03T00:00:00Z","eo:cloud_cover":99})
        r=summarize_window(list(windows(self.config))[0],dict(features=[item]),self.config)
        self.assertEqual(r["candidate"]["id"],"scene")
        self.assertIsNone(r["usable_fraction"])
        self.assertFalse(r["candidate"]["multispectral_assets_present"])

    def test_missing_assets_cannot_be_candidate(self):
        item=dict(id="scene",bbox=[33,0,34,1],assets={},properties={"datetime":"2024-02-03T00:00:00Z"})
        r=summarize_window(list(windows(self.config))[0],dict(features=[item]),self.config)
        self.assertIsNone(r["candidate"])
