import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.build_dashboard import snapshot
from scripts.serve_demo import scouting_preview

ROOT = Path(__file__).resolve().parents[1]


class DashboardTests(unittest.TestCase):
    def test_workspace_counts_come_from_separate_pinned_cohorts(self):
        reports = [
            json.loads((ROOT / f"docs/africa/{name}_RUN.json").read_text())
            for name in (
                "KWEEN_TEMPORAL",
                "KWEEN_RADAR_PIXELS",
                "KWEEN_VISIBILITY",
                "KWEEN_PROCESSOR_BENCHMARK",
            )
        ]
        result = snapshot(*reports, [])
        self.assertEqual(result["radar"]["acquisitions"], 3)
        self.assertEqual(len(result["optical"]["observations"]), 8)
        self.assertFalse(result["field_recommendations_available"])
        self.assertEqual(result["benchmark"]["evaluated_acquisitions"], 0)
        self.assertEqual(result["optical"]["status"], "stale_research_context")

    def test_snapshot_refuses_changed_eligibility(self):
        reports = [
            json.loads((ROOT / f"docs/africa/{name}_RUN.json").read_text())
            for name in (
                "KWEEN_TEMPORAL",
                "KWEEN_RADAR_PIXELS",
                "KWEEN_VISIBILITY",
                "KWEEN_PROCESSOR_BENCHMARK",
            )
        ]
        reports[0]["summary"]["agronomic_review_eligible"] = True
        with self.assertRaises(ValueError):
            snapshot(*reports, [])

    def test_preview_identity_and_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "web/data").mkdir(parents=True)
            output = root / "outputs/africa/dashboard"
            output.mkdir(parents=True)
            path = output / "kween-rgb.png"
            path.write_bytes(b"synthetic-preview-bytes")
            (root / "web/data/scouting.json").write_text(
                json.dumps(
                    dict(
                        snapshot_id="test",
                        preview=dict(
                            assets=dict(
                                rgb=dict(
                                    sha256=hashlib.sha256(path.read_bytes()).hexdigest()
                                )
                            )
                        ),
                    )
                )
            )
            query = dict(case=["kween-2023"], layer=["rgb"], snapshot=["test"])
            self.assertEqual(scouting_preview(query, root), path)
            with self.assertRaises(ValueError):
                scouting_preview(dict(query, layer=["../../secret"]), root)
            with self.assertRaises(ValueError):
                scouting_preview(dict(query, snapshot=["old"]), root)
            path.write_bytes(b"modified")
            with self.assertRaises(ValueError):
                scouting_preview(query, root)
