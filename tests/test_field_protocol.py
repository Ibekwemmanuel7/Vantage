"""Synthetic contract and CLI tests; these are not agricultural outcomes."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from vantage.field_protocol import collection_form, freeze_protocol, reconcile_intake

NOW = datetime(2026, 10, 24, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]


def specification():
    units = []
    for i in range(5):
        unavailable = i == 4
        units.append(dict(unit_id=f"synthetic-{i}", field_id=f"field-{i}", boundary_ref="fixture-only",
                          boundary_version="1", season_id="2026a", crop="maize", spatial_group=f"group-{i}",
                          source_run_ref="synthetic-not-a-satellite-run", acquired_at="2026-10-19T00:00:00Z",
                          available_at="2026-10-20T00:00:00Z",
                          status="unavailable" if unavailable else ("flagged" if i < 2 else "unflagged"),
                          model_score=None if unavailable else 4-i, baseline_score=None if unavailable else i))
    return dict(cohort_id="synthetic-only", prediction_frozen_at="2026-10-21T00:00:00Z",
                rubric_ref="synthetic-rubric", held_out_protocol_ref="synthetic-split", capacity=2, seed=42, units=units)


def returned_form(protocol):
    form = collection_form(protocol, now=NOW)
    for i, record in enumerate(form["records"]):
        record.update(record_id=f"synthetic-record-{i}", permission_status="approved", source_ref="fixture-only",
                      observer_ref="observer", reviewer_ref="reviewer", observed_at="2026-10-22T10:00:00Z",
                      received_at="2026-10-22T12:00:00Z", reviewed_at="2026-10-23T00:00:00Z",
                      finding="no_useful_finding")
    return form


class FieldProtocolTests(unittest.TestCase):
    def setUp(self):
        self.spec = specification()
        self.protocol = freeze_protocol(self.spec, now=NOW)

    def test_freeze_order_stability_gaps_and_hidden_scores(self):
        self.spec["units"].reverse()
        self.assertEqual(self.protocol, freeze_protocol(self.spec, now=NOW))
        self.assertEqual(["synthetic-4"], self.protocol["sampling_plan"]["unavailable_units"])
        form = collection_form(self.protocol, now=NOW)
        self.assertEqual("synthetic-rubric", form["rubric_ref"])
        for record in form["records"]:
            for forbidden in ("model_score", "baseline_score", "status", "stratum", "inclusion_probability"):
                self.assertNotIn(forbidden, record)
            self.assertIsNone(record["finding"])
        self.assertFalse(self.protocol["complete_cohort_evaluator_compatible"])

    def test_reject_leaky_inputs_and_unavailable_scores(self):
        for mutate in (lambda s: s.update(outcome="useful_finding"),
                       lambda s: s["units"][0].update(finding="healthy"),
                       lambda s: s["units"][4].update(model_score=0),
                       lambda s: s["units"][0].update(model_score=True),
                       lambda s: s["units"][0].update(baseline_score=float("nan")),
                       lambda s: s["units"][0].update(unit_id=s["units"][1]["unit_id"])):
            spec = specification()
            mutate(spec)
            with self.assertRaises(ValueError):
                freeze_protocol(spec, now=NOW)

    def test_reject_empty_cohort_and_invalid_availability(self):
        for mutate in (lambda s: s.update(units=[]),
                       lambda s: s.update(prediction_frozen_at="2026-10-25T00:00:00Z"),
                       lambda s: s["units"][0].update(available_at="2026-10-22T00:00:00Z"),
                       lambda s: s["units"][0].update(acquired_at="2026-10-20"),
                       lambda s: s["units"][0].update(available_at="2026-10-18T00:00:00Z")):
            spec = specification()
            mutate(spec)
            with self.assertRaises(ValueError):
                freeze_protocol(spec, now=NOW)

    def test_changed_scores_or_selection_cannot_reuse_hash(self):
        for mutate in (lambda p: p["spec"]["units"][0].update(model_score=99),
                       lambda p: p["sampling_plan"]["selected"].pop()):
            changed = deepcopy(self.protocol)
            mutate(changed)
            with self.assertRaises(ValueError):
                collection_form(changed, now=NOW)

    def test_missing_visits_are_not_negatives(self):
        intake = returned_form(self.protocol)
        intake["records"].pop()
        result = reconcile_intake(self.protocol, intake, now=NOW)
        self.assertEqual(dict(missing=1, withheld=0, ready_for_adjudication=1), result["state_counts"])
        self.assertEqual(2, len(result["visits"]))
        self.assertEqual(0, result["independently_verified_outcomes"])
        self.assertFalse(result["training_eligible"])
        self.assertFalse(result["evaluation_eligible"])

    def test_mismatched_boundary_old_visits_and_public_leads_withheld(self):
        for changes, blocker in (({"boundary_version": "2"}, "frozen_boundary_version_mismatch"),
                                 ({"observed_at": "2026-10-20T00:00:00Z"}, "visit_must_follow_prediction_freeze"),
                                 ({"source_kind": "public_report"}, "lead_only_requires_field_follow_up"),
                                 ({"finding": "uncertain"}, "finding_requires_adjudication")):
            intake = returned_form(self.protocol)
            intake["records"][0].update(changes)
            result = reconcile_intake(self.protocol, intake, now=NOW)
            self.assertEqual(1, result["state_counts"]["withheld"])
            self.assertIn(blocker, result["visits"][0]["records"][0]["blockers"])

    def test_duplicate_foreign_and_wrong_cohort_records(self):
        intake = returned_form(self.protocol)
        intake["records"].append(deepcopy(intake["records"][0]))
        foreign = deepcopy(intake["records"][1])
        foreign["unit_id"] = "not-selected"
        intake["records"].append(foreign)
        result = reconcile_intake(self.protocol, intake, now=NOW)
        self.assertEqual(1, result["state_counts"]["withheld"])
        self.assertEqual(1, len(result["rejected_records"]))
        self.assertIn("multiple_records_for_selected_unit", result["visits"][0]["records"][0]["blockers"])
        intake["cohort_id"] = "another-round"
        with self.assertRaises(ValueError):
            reconcile_intake(self.protocol, intake, now=NOW)
        intake = returned_form(self.protocol)
        intake["rubric_ref"] = "changed-after-visits"
        with self.assertRaises(ValueError):
            reconcile_intake(self.protocol, intake, now=NOW)

    def test_uncompleted_forms_are_withheld_and_empty_returns_are_missing(self):
        form = collection_form(self.protocol, now=NOW)
        self.assertEqual(2, reconcile_intake(self.protocol, form, now=NOW)["state_counts"]["withheld"])
        form["records"] = []
        result = reconcile_intake(self.protocol, form, now=NOW)
        self.assertEqual(2, result["state_counts"]["missing"])
        self.assertFalse(result["evaluation_eligible"])

    def test_cli_private_packet_reconciliation_and_no_overwrite(self):
        private = ROOT / "outputs" / "private"
        private.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private, prefix="protocol-test-") as directory:
            directory = Path(directory)
            source = directory / "synthetic-spec.json"
            source.write_text(json.dumps(self.spec), encoding="utf-8")
            packet = directory / "packet"
            base = [sys.executable, str(ROOT / "scripts/field_protocol.py")]
            def run(*args):
                return subprocess.run(base + list(map(str, args)), capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(0, run("freeze", source, "--out-dir", packet).returncode)
            original = (packet / "protocol.json").read_bytes()
            self.assertEqual(2, run("freeze", source, "--out-dir", packet).returncode)
            self.assertEqual(original, (packet / "protocol.json").read_bytes())
            protocol = json.loads(original)
            intake = directory / "returned.json"
            intake.write_text(json.dumps(returned_form(protocol)), encoding="utf-8")
            report = directory / "reconciled.json"
            self.assertEqual(0, run("reconcile", packet / "protocol.json", intake, "--out", report).returncode)
            self.assertEqual(2, json.loads(report.read_text())["state_counts"]["ready_for_adjudication"])
            self.assertEqual(2, run("reconcile", packet / "protocol.json", intake, "--out", report).returncode)
            self.assertEqual(2, run("freeze", source, "--out-dir", ROOT / "web" / "forbidden-packet").returncode)


if __name__ == "__main__":
    unittest.main()
