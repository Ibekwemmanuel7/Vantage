import unittest
from vantage.public_evidence import assess_reference,assess_registry


class PublicEvidenceTests(unittest.TestCase):
    def test_official_shared_input_is_not_independent_truth(self):
        r=assess_reference(dict(evidence_id='fews',source_url='https://fews.net/',independence='shares_CHIRPS_input_with_Vantage'))
        self.assertFalse(r['admissible_supervised_reference'])
        self.assertIn('independence_unverified_or_shared_model_inputs',r['blockers'])

    def test_publication_date_is_not_observation_date(self):
        r=assess_reference(dict(evidence_id='post',source_url='https://example.com/post',published_at='2024-05-01'))
        self.assertIn('dated_observation_not_verified',r['blockers'])

    def test_syndicated_origins_are_counted_once(self):
        records=[dict(evidence_id=i,source_group='same-report',source_url='https://example.com/') for i in ['a','b']]
        self.assertEqual(assess_registry(records)['distinct_origin_groups'],1)

    def test_audited_declarations_can_pass_but_do_not_train(self):
        r=dict(evidence_id='synthetic-only',source_url='https://example.com/reference',review_state='original_reference_verified',
               spatial_precision='field_boundary',spatial_match_verified=True,verified_geometry_ref='synthetic-boundary',
               observation_time_precision='day',observed_at='2024-05-01',published_at='2024-05-02',crop_identity_confirmed=True,
               independence='independent_field_observation',target='useful_scouting_finding',outcome='useful_finding',
               sampling_method='routine',reuse_permission='approved',source_group='synthetic',verification_ref='synthetic-audit')
        self.assertTrue(assess_reference(r)['admissible_supervised_reference'])
        self.assertFalse(assess_registry([r])['trained_model'])
