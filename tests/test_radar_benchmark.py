import unittest
import numpy as np
from vantage.radar_benchmark import compare, request_for, scene_identity

PRODUCT = "S1A_IW_GRDH_1SDV_20230512T155715_20230512T155740_048502_05D599_FBDD"


class BenchmarkTests(unittest.TestCase):
    def fixtures(self):
        a = np.array([[30.0, 40.0], [50.0, 60.0]])
        c = np.ones((2, 2), dtype="uint8")
        p = np.stack([a + 2, np.array([[0, 1], [1, 0]]), np.ones((2, 2))])
        return a, c, c.copy(), p, np.ones((2, 2), dtype=bool)

    def test_known_differences_and_not_accuracy(self):
        r = compare(*self.fixtures())
        self.assertEqual(r["incidence_difference"]["signed_median_degrees"], -2)
        self.assertEqual(
            r["shadow_cooccurrence"]["vantage_bounded_clear__provider_near_shadow"], 2
        )
        self.assertFalse(r["agricultural_accuracy_measured"])
        self.assertFalse(r["equivalent_shadow_definitions"])

    def test_no_support_returns_null_not_perfect_agreement(self):
        args = list(self.fixtures())
        args[3][2] = 0
        args[3][0] = np.nan
        r = compare(*args)
        self.assertIsNone(r["incidence_difference"])
        self.assertEqual(r["status"], "unavailable")
        self.assertEqual(r["provider_missing_pixels"], 4)

    def test_guard_unknown_and_local_missing_excluded(self):
        args = list(self.fixtures())
        args[2][:] = [[0, 3], [2, 1]]
        args[1][0, 0] = 0
        r = compare(*args)
        self.assertEqual(r["sightline_comparable_pixels"], 2)
        self.assertEqual(r["incidence_comparable_pixels"], 3)
        self.assertEqual(r["sightline_guard_pixels"], 1)

    def test_wrong_masks_and_shapes_fail(self):
        args = list(self.fixtures())
        args[3][2, 0, 0] = np.nan
        with self.assertRaises(ValueError):
            compare(*args)
        args = list(self.fixtures())
        args[3][1, 0, 0] = 255
        with self.assertRaises(ValueError):
            compare(*args)

    def test_empty_region(self):
        args = list(self.fixtures())
        args[4][:] = False
        self.assertEqual(compare(*args)["status"], "unavailable")

    def test_exact_provider_inventory_and_version_required(self):
        m = {
            "scenes": {"orbits": [{"tiles": [{"sentinel1ProductId": PRODUCT}]}]},
            "inputMetadata": {"serviceVersion": "test-version"},
        }
        self.assertEqual(scene_identity(m, PRODUCT)["product_ids"], [PRODUCT])
        with self.assertRaises(ValueError):
            scene_identity(m, PRODUCT[:-1] + "A")
        m["scenes"]["orbits"][0]["tiles"].append({"sentinel1ProductId": "other"})
        with self.assertRaises(ValueError):
            scene_identity(m, PRODUCT)

    def test_request_pins_grid_dem_time_and_metadata(self):
        grid = dict(
            crs="EPSG:32636",
            width=2,
            height=3,
            transform=[20, 0, 600000, 0, -20, 170000],
        )
        r = request_for(grid, PRODUCT)
        self.assertEqual(r["input"]["bounds"]["bbox"], [600000, 169940, 600040, 170000])
        self.assertEqual(
            r["input"]["data"][0]["dataFilter"]["timeRange"]["from"],
            "2023-05-12T15:57:15Z",
        )
        self.assertEqual(
            r["input"]["data"][0]["processing"]["demInstance"], "COPERNICUS_30"
        )
        self.assertEqual(r["output"]["responses"][1]["identifier"], "userdata")
