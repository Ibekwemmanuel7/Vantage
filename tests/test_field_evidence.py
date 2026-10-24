import copy
from datetime import datetime, timezone
from pathlib import Path
import unittest

from vantage.field_evidence import validate_intake
from scripts.validate_field_evidence import private_output, ROOT


class FieldEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 24, tzinfo=timezone.utc)
        self.record = dict(record_id="r1", field_id="f1", boundary_ref="private/boundary",
                           boundary_version="1", season_id="2026a", crop="maize",
                           source_ref="private/visit", observer_ref="observer1", reviewer_ref="reviewer2",
                           record_type="scouting", source_kind="field_observation", permission_status="approved",
                           observed_at="2026-10-20T10:00:00Z", received_at="2026-10-21T10:00:00Z",
                           reviewed_at="2026-10-22T10:00:00Z", finding="useful_finding")

    def check_record(self, record=None):
        return validate_intake({"schema_version": "1.0", "records": [record or self.record]}, now=self.now)["records"][0]

    def test_review_ready_is_not_label_eligible(self):
        result = self.check_record()
        self.assertTrue(result["ready_for_manual_review"])
        self.assertFalse(result["training_eligible"])
        self.assertFalse(result["evaluation_eligible"])
        self.assertNotIn("field_id", result)

    def test_public_report_and_independence_declaration_do_not_admit_labels(self):
        self.record.update(source_kind="public_report", independently_verified=True)
        result = self.check_record()
        self.assertIn("lead_only_requires_field_follow_up", result["blockers"])
        self.assertFalse(result["evaluation_eligible"])

    def test_dates_permissions_boundaries_and_reviewer(self):
        self.record.update(observed_at="2027-01-01T00:00:00Z", received_at="2026-10-21",
                           permission_status="pending", reviewer_ref="observer1")
        del self.record["boundary_version"]
        blockers = self.check_record()["blockers"]
        for expected in ("future_observed_at", "invalid_received_at", "permission_not_approved",
                         "reviewer_matches_observer", "missing_boundary_version"):
            self.assertIn(expected, blockers)

    def test_harvest_units_and_partial_area(self):
        self.record.update(record_type="harvest", harvest=dict(mass=500, mass_unit="kg", area=2500,
                           area_unit="m2", moisture_basis="dry mass", measurement_ref="private/scale",
                           measurement_method="weighed", extent="partial"))
        result = self.check_record()
        self.assertEqual(2, result["measured_yield_t_per_ha"])
        self.assertTrue(result["ready_for_manual_review"])
        for invalid in (True, 0, -1, float("nan"), float("inf")):
            record = copy.deepcopy(self.record)
            record["harvest"]["area"] = invalid
            self.assertIsNone(self.check_record(record)["measured_yield_t_per_ha"])

    def test_duplicate_empty_and_output_guard(self):
        result = validate_intake({"schema_version": "1.0", "records": [self.record, self.record]}, now=self.now)
        self.assertIn("duplicate_record_id", result["records"][1]["blockers"])
        self.assertEqual(0, validate_intake({"schema_version": "1.0", "records": []})["record_count"])
        for path in (ROOT / "web" / "report.json", ROOT / "outputs" / "private" / ".." / "report.json"):
            with self.assertRaises(ValueError):
                private_output(path)
        self.assertEqual((ROOT / "outputs/private/report.json").resolve(), private_output(ROOT / "outputs/private/report.json"))


if __name__ == "__main__":
    unittest.main()
