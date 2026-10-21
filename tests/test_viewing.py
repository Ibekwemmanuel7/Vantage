import unittest
import numpy as np
from vantage.viewing import (
    ecef,
    orbit_positions,
    unit,
    interpolate_look,
    surface_normals,
    local_geometry,
    parse_annotation,
)
from scripts.acquire_viewing_annotations import product_references


class ViewingTests(unittest.TestCase):
    def test_wgs84_reference_points(self):
        np.testing.assert_allclose(
            ecef(np.array([0, 0]), np.array([0, 90]), np.array([0, 0])),
            [[6378137, 0, 0], [0, 6378137, 0]],
            atol=1e-8,
        )

    def test_orbit_velocity_interpolation_and_no_extrapolation(self):
        times = np.array([0, 10, 20, 30], dtype=float)
        positions = np.column_stack([np.full(4, 7e6), times * 7500, np.zeros(4)])
        velocity = np.tile([0, 7500, 0], (4, 1))
        result = orbit_positions(times, positions, velocity, [5, 15])
        np.testing.assert_allclose(result, [[7e6, 37500, 0], [7e6, 112500, 0]])
        with self.assertRaises(ValueError):
            orbit_positions(times, positions, velocity, [-1])
        with self.assertRaises(ValueError):
            orbit_positions([0, 10, 10, 30], positions, velocity, [5])

    def test_outside_annotation_hull_remains_unknown(self):
        points = np.array([[0, 0], [1, 0], [0, 1], [1, 1]])
        vectors = np.tile(unit(np.array([-0.5, 0, 1.0])), (4, 1))
        result = interpolate_look(points, vectors, np.array([[0.5, 0.5], [2, 2]]))
        np.testing.assert_allclose(result[0], vectors[0])
        self.assertTrue(np.isnan(result[1]).all())

    def test_metric_normal_accounts_for_rotated_grid_axes_and_row_direction(self):
        row, col = np.indices((7, 7))
        shape = (7, 7, 3)
        up = np.broadcast_to([0, 0, 1.0], shape)
        normal, gradient = surface_normals(
            0.1 * col * 30,
            30,
            30,
            up,
            np.broadcast_to([0, 1.0, 0], shape),
            np.broadcast_to([-1.0, 0, 0], shape),
        )
        np.testing.assert_allclose(gradient[3, 3], [0, 0.1, 0], atol=1e-12)
        np.testing.assert_allclose(
            normal[3, 3], unit(np.array([0, -0.1, 1.0])), atol=1e-12
        )
        normal, gradient = surface_normals(
            0.1 * col * 30 - 0.2 * row * 30,
            30,
            30,
            up,
            np.broadcast_to([1.0, 0, 0], shape),
            np.broadcast_to([0, 1.0, 0], shape),
        )
        np.testing.assert_allclose(gradient[3, 3], [0.1, 0.2, 0], atol=1e-12)

    def test_range_reversal_is_detected_even_with_acute_local_incidence(self):
        angle = np.radians(35)
        look = np.tile([-np.sin(angle), 0, np.cos(angle)], (3, 1))
        up = np.tile([0, 0, 1.0], (3, 1))
        gradient = np.column_stack(
            [
                [0, np.tan(np.radians(50)), -np.tan(np.radians(60))],
                np.zeros(3),
                np.zeros(3),
            ]
        )
        normal = unit(up - gradient)
        result = local_geometry(look, normal, up, gradient)
        np.testing.assert_array_equal(result["classes"], [1, 2, 3])
        np.testing.assert_allclose(result["local_incidence"], [35, 15, 95], atol=1e-5)

    def test_unknown_normals_and_nonnormalized_vectors_are_not_valid(self):
        look = unit(np.array([[-1.0, 0, 1.0]]))
        up = np.array([[0, 0, 1.0]])
        gradient = np.zeros((1, 3))
        result = local_geometry(look, np.full((1, 3), np.nan), up, gradient)
        self.assertEqual(int(result["classes"][0]), 0)
        with self.assertRaises(ValueError):
            local_geometry(look * 2, up, up, gradient)

    def test_manifest_selection_rejects_rfi_and_calibration_assets(self):
        xml = """<root><dataObject repID="s1Level1ProductSchema"><byteStream size="3"><fileLocation href="./annotation/product-vv.xml"/><checksum checksumName="MD5">abc</checksum></byteStream></dataObject><dataObject repID="s1Level1RfiSchema"><byteStream><fileLocation href="./annotation/rfi/rfi-vv.xml"/></byteStream></dataObject></root>"""
        refs = product_references(xml, "https://example.com/p/manifest.safe")
        self.assertEqual(len(refs), 1)
        self.assertEqual(
            refs[0]["href"], "https://example.com/p/annotation/product-vv.xml"
        )
        self.assertEqual(refs[0]["size"], 3)

    def test_nonproduct_xml_and_invalid_tolerance_fail_closed(self):
        with self.assertRaises(ValueError):
            parse_annotation("<rfi/>", {}, 0.25)
        with self.assertRaises(ValueError):
            parse_annotation("<product/>", {}, float("nan"))

    def test_annotation_polarization_orbit_and_reference_frame_are_checked(self):
        record = dict(
            item_id="S1A_IW_GRDH_1SDV_20230512T155715_20230512T155740_048502_05D599_rtc",
            acquired_at="2023-05-12T15:57:28Z",
        )
        template = """<product><adsHeader><missionId>S1A</missionId><productType>GRD</productType><polarisation>{pol}</polarisation><mode>IW</mode><absoluteOrbitNumber>{orbit}</absoluteOrbitNumber><startTime>2023-05-12T15:57:15</startTime><stopTime>2023-05-12T15:57:41</stopTime></adsHeader>{states}</product>"""
        for pol, orbit, states in [
            ("VH", 48502, ""),
            ("VV", 48503, ""),
            ("VV", 48502, ""),
            ("VV", 48502, "<orbit><frame>Earth Inertial</frame></orbit>" * 4),
        ]:
            with self.assertRaises(ValueError):
                parse_annotation(
                    template.format(pol=pol, orbit=orbit, states=states), record, 0.25
                )
