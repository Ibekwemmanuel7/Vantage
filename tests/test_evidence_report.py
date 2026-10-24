import unittest
from vantage.evidence_report import summarize,render


class EvidenceReportTests(unittest.TestCase):
    def inputs(self):
        def row(location,date):
            return dict(location_id=location,acquired_at=date+"T08:00:00Z",status="processed",
                        metrics=dict(valid_pixels=90,total_pixels=100,usable_fraction=.9))
        return dict(recent=dict(decision_cutoff="2026-10-23T00:00:00Z",independent_field_outcomes=0,
            observations=[row("recent","2026-10-20"),row("old","2026-10-05")]),
            samples=dict(training_eligible=False,model_trained=False,dataset_id="fixture",samples=[dict(partition="train"),dict(partition="validation")],blockers=["processor_pending"]),
            comparison=dict(exported_acquisitions_evaluated=0),
            model=dict(promotion_status="blocked",model=dict(training_samples=20,training_target_dates=2),
                supported_validation_dates=0,clear_transition_diagnostics=dict(validation=dict(
                    predicted_pixel_date_pairs=10,learned_mae=.0708,persistence_mae=.0606))))

    def test_cutoff_freshness_and_staleness_are_recomputed(self):
        report=summarize(**self.inputs())
        self.assertEqual(report["fresh_qualified_boxes"],1)
        self.assertEqual(report["sample_counts"],{"train":1,"validation":1})
        self.assertFalse(report["radar_assisted_model_trained"])
        self.assertEqual(report["independent_exports_evaluated"],0)

    def test_inconsistent_pixel_counts_and_promoted_samples_rejected(self):
        inputs=self.inputs()
        inputs["recent"]["observations"][0]["metrics"]["usable_fraction"]=1
        with self.assertRaises(ValueError):summarize(**inputs)
        inputs=self.inputs()
        inputs["samples"]["training_eligible"]=True
        with self.assertRaises(ValueError):summarize(**inputs)

    def test_report_escapes_source_labels_and_preserves_negative_results(self):
        inputs=self.inputs()
        inputs["recent"]["observations"][0]["location_id"]='<img src=x onerror="alert(1)">'
        html=render(summarize(**inputs))
        self.assertNotIn('<img src=x',html)
        self.assertIn('&lt;img',html)
        self.assertIn('0.0708',html)
        self.assertIn('0.0606',html)
        self.assertIn('Not a live scouting recommendation',html)
        self.assertIn('Training disabled',html)
        self.assertIn('id="location"',html)
        self.assertNotIn('fetch(',html)
