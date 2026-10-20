import unittest
from vantage.seasonal import dekad_slots,slot_candidates,calendar_readiness


class SeasonalTests(unittest.TestCase):
    def test_dekads_cover_leap_month_without_invented_dates(self):
        slots=list(dekad_slots(dict(location_id='test',years=[2024],months=[2])))
        self.assertEqual(len(slots),3);self.assertEqual(slots[-1]['end'],'2024-02-29')

    def test_duplicate_versions_do_not_inflate_acquisitions(self):
        slot=list(dekad_slots(dict(location_id='test',years=[2024],months=[5])))[0]
        item=dict(id='a',bbox=[33,0,34,1],properties={'datetime':'2024-05-01T00:00:00Z','eo:cloud_cover':30},assets={k:{} for k in ['B02','B03','B04','B8A','B11','B12','SCL','product-metadata']})
        self.assertEqual(len(slot_candidates(slot,[item,{**item,'id':'b'}],[33.4,.65,33.5,.75])),1)

    def test_desk_calendar_never_confirms_crop_dates(self):
        row=dict(location_id='iganga-study',year=2024,crop='maize',crop_identity_confirmed=True,
                 confirmation_kind='regional_desk_calendar',source_ref='FAO',reviewer_ref='test',permission_status='approved',
                 planting_date='2024-03-01',harvest_date='2024-07-01',reviewed_at='2024-08-01T00:00:00Z')
        self.assertFalse(calendar_readiness(row,'iganga-study',2024)['confirmed'])
        row['confirmation_kind']='dated_field_record'
        self.assertTrue(calendar_readiness(row,'iganga-study',2024)['confirmed'])
        row['reviewed_at']='2024-02-01T00:00:00Z'
        self.assertFalse(calendar_readiness(row,'iganga-study',2024)['confirmed'])

    def test_absent_calendar_is_explicit(self):
        self.assertFalse(calendar_readiness(None,'iganga-study',2024)['confirmed'])
