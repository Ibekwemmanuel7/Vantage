import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from vantage.regional_calendar import read_uganda_archive, regional_windows, select_context
from vantage.seasonal import calendar_readiness

ROOT = Path(__file__).resolve().parents[1]
HEADER = "asap0_id;name0_shr;asap1_id;name1_shr;crop_name;sos_s;sos_e;eos_s;eos_e\n"


def archive(body):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as output:
        output.writestr("crop_calendar_gaul1.csv", HEADER + body)
    return stream.getvalue()


class RegionalCalendarTests(unittest.TestCase):
    def setUp(self):
        self.row = read_uganda_archive(archive("209;Uganda;9988;South Eastern;Maize (South/Second);24;29;1;3\n"))[0]

    def test_cross_year_and_boundary_overlap(self):
        result = regional_windows(self.row, 2024)
        self.assertTrue(result["crosses_calendar_year"])
        self.assertEqual(dict(start="2024-08-21", end="2024-10-20"), result["windows"]["planting"])
        self.assertEqual(dict(start="2024-10-11", end="2025-01-10"), result["windows"]["growing"])
        self.assertEqual(dict(start="2025-01-01", end="2025-01-31"), result["windows"]["harvesting"])
        self.assertEqual(self.row["source_markers"], result["source_dekads"])

    def test_leap_year_and_year_end_dekads(self):
        self.row["source_markers"] = dict(sos_s=4, sos_e=6, eos_s=35, eos_e=36)
        self.assertEqual("2024-02-29", regional_windows(self.row, 2024)["windows"]["planting"]["end"])
        self.assertEqual("2023-02-28", regional_windows(self.row, 2023)["windows"]["planting"]["end"])
        self.assertEqual("2024-12-31", regional_windows(self.row, 2024)["windows"]["harvesting"]["end"])

    def test_regional_prior_cannot_confirm_field_calendar(self):
        result = regional_windows(self.row, 2024)
        self.assertFalse(result["field_calendar_confirmed"])
        self.assertFalse(calendar_readiness(result, "synthetic-location", 2024)["confirmed"])
        self.assertIn("independent_confirmation_required", calendar_readiness(result, "synthetic-location", 2024)["blockers"])

    def test_exact_selection_only_and_source_labels_preserved(self):
        self.row["name1_shr"] = "West Nile,"
        result = select_context([self.row], "9988", "Maize (South/Second)", 2024)
        self.assertEqual("West Nile,", result["zone_label"])
        self.assertEqual("regional_context_only", result["status"])
        self.assertEqual("unavailable", select_context([self.row], "Lira", "Maize", 2024)["status"])

    def test_duplicate_missing_invalid_or_wrong_country_rows(self):
        for body in ("209;Uganda;9988;Region;Maize;0;9;20;22\n",
                     "209;Uganda;9988;Region;Maize;1;9;20;37\n",
                     "210;Uganda;9988;Region;Maize;1;9;20;22\n",
                     "209;Uganda;9988;;Maize;1;9;20;22\n",
                     "209;Uganda;9988;Region;Maize;1;9;20;22\n" * 2,
                     "210;Other;9988;Region;Maize;1;9;20;22\n"):
            with self.assertRaises(ValueError): read_uganda_archive(archive(body))

    def test_multiwrap_or_bad_anchor_rejected(self):
        for year in (True, 1899, 2100, "2024"):
            with self.assertRaises(ValueError): regional_windows(self.row, year)
        self.row["source_markers"] = dict(sos_s=20, sos_e=10, eos_s=5, eos_e=15)
        with self.assertRaises(ValueError): regional_windows(self.row, 2024)

    def test_cli_hash_counts_and_exclusive_output(self):
        import hashlib
        parent = ROOT / "outputs/private"
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent, prefix="calendar-test-") as temporary:
            directory = Path(temporary)
            source = directory / "synthetic.zip"
            source.write_bytes(archive("209;Uganda;9988;Region;Maize;7;9;20;22\n"))
            config = json.loads((ROOT / "configs/uganda_regional_calendar.json").read_text())
            config.update(archive_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), expected_uganda_rows=1, expected_zone_ids=1)
            config_path = directory / "synthetic-source.json"
            config_path.write_text(json.dumps(config))
            output = directory / "context.json"
            command = [sys.executable, str(ROOT / "scripts/import_regional_calendars.py"), "--archive", str(source),
                       "--config", str(config_path), "--year", "2024", "--out", str(output)]
            result = subprocess.run(command, capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(0, result.returncode, result.stderr)
            original = output.read_bytes()
            self.assertEqual(0, json.loads(original)["field_calendars_confirmed"])
            self.assertEqual(2, subprocess.run(command, capture_output=True).returncode)
            self.assertEqual(original, output.read_bytes())
            source.write_bytes(b"changed")
            command[-1] = str(directory / "bad.json")
            self.assertEqual(2, subprocess.run(command, capture_output=True).returncode)
            self.assertFalse((directory / "bad.json").exists())


if __name__ == "__main__":
    unittest.main()
