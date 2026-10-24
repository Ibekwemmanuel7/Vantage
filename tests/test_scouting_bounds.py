"""Synthetic finite-cohort checks, including exhaustive missing-outcome assignments."""
from copy import deepcopy
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tests.test_field_protocol import NOW, ROOT, returned_form, specification
from vantage.field_protocol import freeze_protocol
from vantage.scouting_bounds import compare_scouting_bounds


def declarations(protocol, intake):
    return dict(schema_version="vantage-adjudication-1", cohort_id=protocol["spec"]["cohort_id"],
                protocol_sha256=protocol["protocol_sha256"], rubric_ref=protocol["spec"]["rubric_ref"],
                records=[dict(unit_id=r["unit_id"], record_id=r["record_id"], decision="confirmed",
                              independence_confirmed=True, outcome=r["finding"],
                              adjudicator_ref="independent-synthetic-reviewer", reference_ref="synthetic-audit-only",
                              adjudicated_at="2026-10-23T12:00:00Z") for r in intake["records"]])


class ScoutingBoundsTests(unittest.TestCase):
    def setUp(self):
        self.protocol = freeze_protocol(specification(), now=NOW)
        self.intake = returned_form(self.protocol)
        self.intake["records"][0]["finding"] = "useful_finding"
        self.adjudications = declarations(self.protocol, self.intake)

    def report(self, protocol=None, intake=None, adjudications=None):
        return compare_scouting_bounds(protocol or self.protocol, intake or self.intake,
                                       adjudications or self.adjudications, now=NOW)

    def test_unknowns_span_full_range_without_fabricated_negatives(self):
        self.intake["records"] = []
        self.adjudications["records"] = []
        result = self.report()
        self.assertEqual([0, 1], result["model"]["precision_bounds"])
        self.assertEqual([0, 1], result["baseline"]["precision_bounds"])
        self.assertEqual([-1, 1], result["paired_precision_difference_bounds"])
        self.assertEqual(2, result["visit_state_counts"]["missing"])
        self.assertEqual(1, result["unavailable_cohort_size"])
        self.assertIsNone(result["confidence_interval"])
        self.assertFalse(result["training_eligible"])
        self.assertEqual(0, result["independently_authenticated_outcomes"])

    def test_bounds_equal_exhaustive_binary_completions(self):
        # Test disjoint, overlapping and identical rankings, with one or two known outcomes.
        for baseline_scores in ([0, 1, 2, 3], [0, 3, 2, 1], [4, 3, 2, 1]):
            spec = specification()
            for unit, score in zip(spec["units"], baseline_scores):
                unit["baseline_score"] = score
            protocol = freeze_protocol(spec, now=NOW)
            intake = returned_form(protocol)
            intake["records"][0]["finding"] = "useful_finding"
            adjudications = declarations(protocol, intake)
            for count in (1, 2):
                adjudications["records"] = declarations(protocol, intake)["records"][:count]
                result = self.report(protocol, intake, adjudications)
                known = {r["unit_id"]: int(r["outcome"] == "useful_finding") for r in adjudications["records"]}
                unknown = sorted(u["unit_id"] for u in spec["units"] if u["status"] != "unavailable" and u["unit_id"] not in known)
                values = {"model": [], "baseline": [], "difference": []}
                for bits in itertools.product((0, 1), repeat=len(unknown)):
                    outcomes = dict(known, **dict(zip(unknown, bits)))
                    model = sum(outcomes[u] for u in result["model"]["ranked_unit_ids"]) / result["capacity"]
                    baseline = sum(outcomes[u] for u in result["baseline"]["ranked_unit_ids"]) / result["capacity"]
                    values["model"].append(model)
                    values["baseline"].append(baseline)
                    values["difference"].append(model - baseline)
                for name in ("model", "baseline"):
                    self.assertEqual([min(values[name]), max(values[name])], result[name]["precision_bounds"])
                self.assertEqual([min(values["difference"]), max(values["difference"])], result["paired_precision_difference_bounds"])

    def test_shared_unknowns_cancel_in_identical_rankings(self):
        spec = specification()
        for unit in spec["units"]:
            unit["baseline_score"] = unit["model_score"]
        protocol = freeze_protocol(spec, now=NOW)
        intake = returned_form(protocol)
        intake["records"] = []
        result = self.report(protocol, intake, declarations(protocol, intake))
        self.assertEqual([0, 0], result["paired_precision_difference_bounds"])
        self.assertEqual([0, 1], result["model"]["precision_bounds"])

    def test_ineligible_adjudications_cannot_narrow_bounds(self):
        for changes, expected in (({"independence_confirmed": False}, "independence_not_declared"),
                                  ({"decision": "uncertain"}, "adjudication_not_confirmed"),
                                  ({"record_id": "wrong"}, "record_id_mismatch"),
                                  ({"outcome": "no_useful_finding"}, "outcome_disagrees_with_intake"),
                                  ({"adjudicator_ref": "observer"}, "adjudicator_matches_visit_personnel"),
                                  ({"reference_ref": ""}, "missing_reference_ref"),
                                  ({"adjudicated_at": "2026-10-22T00:00:00Z"}, "adjudication_precedes_intake_review"),
                                  ({"adjudicated_at": "2026-10-25T00:00:00Z"}, "future_adjudication"),
                                  ({"adjudicated_at": "2026-10-23"}, "invalid_adjudicated_at")):
            adjudications = deepcopy(self.adjudications)
            adjudications["records"][0].update(changes)
            result = self.report(adjudications=adjudications)
            self.assertEqual(1, result["declared_outcomes_used"])
            self.assertIn(expected, result["adjudication_checks"][0]["blockers"])

    def test_capacity_cap_and_complete_declared_outcomes(self):
        spec = specification()
        spec["capacity"] = 10
        protocol = freeze_protocol(spec, now=NOW)
        intake = returned_form(protocol)
        intake["records"][0]["finding"] = "useful_finding"
        result = self.report(protocol, intake, declarations(protocol, intake))
        self.assertEqual(4, result["capacity"])
        self.assertEqual(10, result["requested_capacity"])
        self.assertEqual([.25, .25], result["model"]["precision_bounds"])
        self.assertEqual([0, 0], result["paired_precision_difference_bounds"])

    def test_ties_use_stable_unit_id_order(self):
        spec = specification()
        for unit in spec["units"][:4]:
            unit["model_score"] = unit["baseline_score"] = 1
        protocol = freeze_protocol(spec, now=NOW)
        intake = returned_form(protocol)
        result = self.report(protocol, intake, declarations(protocol, intake))
        self.assertEqual(["synthetic-0", "synthetic-1"], result["model"]["ranked_unit_ids"])

    def test_unready_duplicate_foreign_and_changed_protocol_records(self):
        self.intake["records"][0]["source_kind"] = "public_report"
        self.assertEqual(1, self.report()["declared_outcomes_used"])
        self.adjudications["records"].append(deepcopy(self.adjudications["records"][1]))
        self.assertEqual(0, self.report()["declared_outcomes_used"])
        self.adjudications["records"][0]["unit_id"] = "not-selected"
        self.assertIn("unit_not_in_selected_plan", self.report()["adjudication_checks"][0]["blockers"])
        self.adjudications["protocol_sha256"] = "wrong"
        with self.assertRaises(ValueError):
            self.report()

    def test_cli_hashes_privacy_and_overwrite_protection(self):
        private = ROOT / "outputs" / "private"
        private.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private, prefix="bounds-test-") as directory:
            directory = Path(directory)
            paths = []
            for name, content in (("protocol", self.protocol), ("intake", self.intake), ("adjudications", self.adjudications)):
                path = directory / f"{name}.json"
                path.write_text(json.dumps(content), encoding="utf-8")
                paths.append(str(path))
            base = [sys.executable, str(ROOT / "scripts/compare_scouting_bounds.py")] + paths
            output = directory / "bounds.json"
            first = subprocess.run(base + ["--out", str(output)], capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(0, first.returncode, first.stderr)
            report = json.loads(output.read_text())
            self.assertEqual({"protocol", "intake", "adjudications"}, set(report["source_file_sha256"]))
            original = output.read_bytes()
            second = subprocess.run(base + ["--out", str(output)], capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(2, second.returncode)
            self.assertEqual(original, output.read_bytes())
            forbidden = subprocess.run(base + ["--out", str(ROOT / "web" / "forbidden-bounds.json")], capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(2, forbidden.returncode)


if __name__ == "__main__":
    unittest.main()
