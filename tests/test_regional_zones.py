import unittest
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from tests.test_field_pixels import boundaries  # Configure the wheel-matched PROJ database.
from tests.test_regional_calendar import archive, ROOT
from shapely.geometry import box, mapping
from vantage.regional_zones import read_zone_response, validate_zones, resolve_zone


def catalogue():
    return dict(type="FeatureCollection", features=[dict(type="Feature", geometry=mapping(box(west, 1, west+1, 2)),
        properties=dict(asap0_id="209", asap1_id=str(i), zone_label=f"Synthetic zone {i}"))
        for i, west in (("1", 32), ("2", 33))])


class RegionalZoneTests(unittest.TestCase):
    def setUp(self):
        self.rows = [dict(asap1_id="1", crop_name="Synthetic maize main")]
        self.zones = validate_zones(catalogue(), self.rows)

    def test_interior_match_is_only_regional_context(self):
        result = resolve_zone(mapping(box(32.4, 1.4, 32.5, 1.5)), self.zones, self.rows)
        self.assertEqual("regional_zone_context", result["status"])
        self.assertEqual("1", result["asap1_id"])
        self.assertEqual(["Synthetic maize main"], result["available_crop_seasons"])
        self.assertFalse(result["field_calendar_confirmed"])
        self.assertFalse(result["field_priorities_available"])

    def test_border_crossing_and_outside_remain_unresolved(self):
        for polygon, reason in ((box(32.999, 1.4, 32.9995, 1.5), "near_simplified_zone_boundary"),
                                (box(32.99, 1.4, 33.01, 1.5), "crosses_zones_or_no_unique_full_containment"),
                                (box(30, 1.4, 30.1, 1.5), "outside_supplied_zone_coverage")):
            result = resolve_zone(mapping(polygon), self.zones, self.rows)
            self.assertEqual("unresolved", result["status"])
            self.assertEqual(reason, result["reason"])
            self.assertIsNone(result["asap1_id"])

    def test_no_calendar_is_not_filled_from_neighbor(self):
        result = resolve_zone(mapping(box(33.4, 1.4, 33.5, 1.5)), self.zones, self.rows)
        self.assertEqual("zone_without_calendar_context", result["status"])
        self.assertEqual([], result["available_crop_seasons"])

    def test_incompatible_ids_duplicate_ids_or_invalid_geometry_reject(self):
        with self.assertRaises(ValueError): validate_zones(catalogue(), [dict(asap1_id="99")])
        duplicate = catalogue(); duplicate["features"][1]["properties"]["asap1_id"] = "1"
        with self.assertRaises(ValueError): validate_zones(duplicate, self.rows)
        invalid = catalogue(); invalid["features"][0]["geometry"] = dict(type="Point", coordinates=[32, 1])
        with self.assertRaises(ValueError): validate_zones(invalid, self.rows)

    def test_overlapping_zone_shapes_do_not_assign_by_centroid(self):
        overlap = catalogue(); overlap["features"][1]["geometry"] = mapping(box(32.4, 1, 33.4, 2))
        zones = validate_zones(overlap, self.rows)
        result = resolve_zone(mapping(box(32.2, 1.4, 32.5, 1.5)), zones, self.rows)
        self.assertEqual("overlapping_zone_geometry", result["reason"])

    def wfs(self):
        data = catalogue()
        for feature in data["features"]:
            props = feature["properties"]
            feature["properties"] = dict(asap0_id=209, asap1_id=int(props["asap1_id"]), asap0_name="Uganda",
                                          asap1_name=props["zone_label"], w_crop=4)
        data.update(numberMatched=2, numberReturned=2, crs=dict(properties=dict(name="urn:ogc:def:crs:EPSG::4326")))
        return data

    def test_response_completeness_country_and_crs(self):
        data = self.wfs()
        result = read_zone_response(json.dumps(data).encode())
        self.assertNotIn("w_crop", result["features"][0]["properties"])
        for mutate in (lambda d:d.update(numberMatched=3), lambda d:d.pop("crs"),
                       lambda d:d["features"][0]["properties"].update(asap0_id=210)):
            data = self.wfs(); mutate(data)
            with self.assertRaises(ValueError): read_zone_response(json.dumps(data).encode())

    def test_cli_frozen_sources_private_output_and_no_overwrite(self):
        parent = ROOT / "outputs/private"
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent, prefix="zone-test-") as temporary:
            directory = Path(temporary)
            zones = directory / "zones.geojson"; zones.write_text(json.dumps(self.wfs()))
            calendars = directory / "calendars.zip"; calendars.write_bytes(archive("209;Uganda;1;Region;Maize;7;9;20;22\n"))
            source_config = json.loads((ROOT / "configs/uganda_regional_zones.json").read_text())
            source_config.update(response_sha256=hashlib.sha256(zones.read_bytes()).hexdigest(), expected_zone_count=2)
            source = directory / "source.json"; source.write_text(json.dumps(source_config))
            calendar_config = json.loads((ROOT / "configs/uganda_regional_calendar.json").read_text())
            calendar_config.update(archive_sha256=hashlib.sha256(calendars.read_bytes()).hexdigest(), expected_uganda_rows=1)
            calendar_source = directory / "calendar-source.json"; calendar_source.write_text(json.dumps(calendar_config))
            plan = directory / "study.json"; plan.write_text(json.dumps(dict(schema_version="uganda-archive-plan-1",
                    locations=[dict(id="synthetic-only", bbox=[32.4,1.4,32.5,1.5])])))
            output = directory / "context.json"
            command = [sys.executable, str(ROOT / "scripts/join_regional_context.py"), "--zones", str(zones),
                       "--calendar-archive", str(calendars), "--source-config", str(source),
                       "--calendar-config", str(calendar_source), "--year", "2024", "--study-config", str(plan), "--out", str(output)]
            run = subprocess.run(command, capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(0, run.returncode, run.stderr)
            original = output.read_bytes()
            self.assertEqual("regional_zone_context", json.loads(original)["units"][0]["match"]["status"])
            self.assertEqual(2, subprocess.run(command, capture_output=True).returncode)
            self.assertEqual(original, output.read_bytes())
            command[-1] = str(ROOT / "web/forbidden-zone-context.json")
            self.assertEqual(2, subprocess.run(command, capture_output=True).returncode)


if __name__ == "__main__":
    unittest.main()
