import unittest
from vantage.evaluation import evaluate_capacity, sampling_plan


def cohort():
    return [dict(sample_id=str(i), cohort_id="synthetic-test-only", spatial_group=str(i//2),
                 independently_verified=True, held_out=True, reference_ref="synthetic-fixture",
                 acquired_at="2024-05-10T00:00:00Z", prediction_frozen_at="2024-05-11T00:00:00Z",
                 observed_at="2024-05-12T00:00:00Z", model_score=6-i, baseline_score=i,
                 outcome="useful_finding" if i<3 else "no_useful_finding") for i in range(6)]


class EvaluationTests(unittest.TestCase):
    def test_paired_capacity_and_reproducibility(self):
        report = evaluate_capacity(cohort(), 3, bootstrap_replicates=100)
        self.assertEqual(report["model_precision_at_capacity"], 1)
        self.assertEqual(report["baseline_precision_at_capacity"], 0)
        self.assertEqual(report, evaluate_capacity(list(reversed(cohort())), 3, bootstrap_replicates=100))

    def test_missing_outcomes_rejected(self):
        rows=cohort(); rows[0]["outcome"]=None
        with self.assertRaises(ValueError): evaluate_capacity(rows, 3)

    def test_post_outcome_prediction_rejected(self):
        rows=cohort(); rows[0]["prediction_frozen_at"]="2024-05-13T00:00:00Z"
        with self.assertRaises(ValueError): evaluate_capacity(rows, 3)

    def test_no_interval_for_single_location(self):
        rows=cohort()
        for row in rows: row["spatial_group"]="one"
        self.assertIsNone(evaluate_capacity(rows, 3)["paired_cluster_bootstrap_95_interval"])

    def test_bad_scores_and_unverified_outcomes_rejected(self):
        for key, value in [("model_score", float("nan")), ("held_out", False), ("independently_verified", False)]:
            rows=cohort(); rows[0][key]=value
            with self.assertRaises(ValueError): evaluate_capacity(rows, 3)

    def test_sampling_gaps_controls_and_probabilities(self):
        rows=[dict(unit_id=str(i),status="flagged" if i<4 else "unflagged") for i in range(8)]
        rows.append(dict(unit_id="gap",status="unavailable"))
        plan=sampling_plan(rows,4)
        self.assertEqual(plan,sampling_plan(list(reversed(rows)),4))
        self.assertEqual(plan["unavailable_units"],["gap"])
        self.assertEqual(len(plan["selected"]),4)
        self.assertTrue(all(r["inclusion_probability"]==.5 and r["outcome"] is None for r in plan["selected"]))

    def test_duplicate_units_rejected(self):
        with self.assertRaises(ValueError): sampling_plan([dict(unit_id="a",status="flagged")]*2,2)

    def test_absent_controls_are_explicit(self):
        plan=sampling_plan([dict(unit_id="a",status="flagged")],2)
        self.assertEqual(plan["population_counts"]["unflagged"],0)
        self.assertTrue(plan["warnings"])
