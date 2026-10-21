import copy
import unittest
from shapely.geometry import box, mapping, Polygon
from vantage.radar import catalog_candidates, track_coverage


PLAN = dict(
    bbox=[0, 0, 1, 1],
    start="2023-05-01",
    end="2023-06-05",
    as_of="2023-06-05T23:59:59Z",
    mode="IW",
    polarizations=["VV", "VH"],
    collection="sentinel-1-rtc",
)


def item(name="a", stamp="2023-05-24T15:57:00Z", absolute=10, relative=130):
    return dict(
        id=name,
        collection="sentinel-1-rtc",
        geometry=mapping(box(-1, -1, 2, 2)),
        properties={
            "datetime": stamp,
            "platform": "SENTINEL-1A",
            "sat:relative_orbit": relative,
            "sat:absolute_orbit": absolute,
            "sat:orbit_state": "ascending",
            "sar:instrument_mode": "IW",
            "sar:polarizations": ["VV", "VH"],
        },
        assets={p: dict(href="https://example.com/" + p) for p in ("vv", "vh")},
    )


class RadarTests(unittest.TestCase):
    def test_bbox_overlap_does_not_establish_full_footprint_coverage(self):
        candidate = item()
        candidate["geometry"] = mapping(Polygon([(-1, -1), (2, -1), (-1, 2), (-1, -1)]))
        rows, excluded = catalog_candidates([candidate], PLAN)
        self.assertFalse(rows)
        self.assertIn("footprint_does_not_cover_box", excluded[0]["reasons"])

    def test_duplicate_slices_count_once_and_orbits_remain_separate(self):
        duplicate = item("alternate", "2023-05-24T15:57:10Z")
        rows, excluded = catalog_candidates(
            [duplicate, item(), item("other", absolute=11, relative=131)], PLAN
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(len({r["track_id"] for r in rows}), 2)
        self.assertIn("duplicate_orbital_pass", excluded[0]["reasons"])

    def test_missing_polarization_and_unknown_orbit_are_excluded(self):
        for key in ("sat:relative_orbit", "sat:orbit_state", "sar:polarizations"):
            candidate = item()
            del candidate["properties"][key]
            rows, excluded = catalog_candidates([candidate], PLAN)
            self.assertFalse(rows)
            self.assertTrue(excluded)

    def test_afternoon_radar_is_not_available_to_morning_optical_gap(self):
        rows, _ = catalog_candidates(
            [item(), item("later", "2023-06-05T15:57:00Z", absolute=11)], PLAN
        )
        optical = [
            dict(
                acquired_at="2023-06-05T07:46:00Z",
                status="processed",
                coverage_qualified=False,
            )
        ]
        report = track_coverage(rows, optical, PLAN["as_of"], 7)[0]
        match = report["optical_gap_matches"][0]
        self.assertEqual(match["prior_radar_item_id"], "a")
        self.assertFalse(match["catalog_match_within_age_window"])
        self.assertTrue(report["catalog_fresh_at_cutoff"])
        self.assertFalse(report["usable_radar_evidence"])
        self.assertIsNone(match["measured_radar_coverage"])

    def test_future_radar_cannot_enter_temporal_matching(self):
        rows, _ = catalog_candidates([item()], PLAN)
        rows = copy.deepcopy(rows)
        rows[0]["acquired_at"] = "2023-06-06T15:57:00Z"
        with self.assertRaises(ValueError):
            track_coverage(rows, [], PLAN["as_of"], 7)
