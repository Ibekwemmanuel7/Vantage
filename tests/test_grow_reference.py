from datetime import datetime
import unittest
from vantage.grow_reference import TABLES,TableAudit,finite,dated


def point(**changes):
    row=dict(Country='Uganda',Source='Synthetic research source',Crop='Maize',HarvestYear=2020,
             Yield_ton_ha_=0,Latitude=1,Longitude=33,SpatialPrecision_km_=.02,
             PlantDate=datetime(2020,3,1),HarvestDate=datetime(2020,7,1))
    return row|changes


class GrowReferenceTests(unittest.TestCase):
    def test_zeros_are_valid_yields_missing_stays_missing_and_countries_separate(self):
        audit=TableAudit('Point',point().keys())
        for row in (point(),point(Yield_ton_ha_=None),point(Country='Kenya')):audit.add(row)
        report=audit.result()
        self.assertEqual(report['counts']['all_rows'],3)
        self.assertEqual(report['counts']['uganda_rows'],2)
        self.assertEqual(report['counts']['yield_nonnegative_finite'],1)
        self.assertEqual(report['counts']['yield_missing_or_invalid'],1)
        self.assertEqual(report['training_labels_admitted'],0)
        self.assertFalse(report['field_satellite_join_allowed'])

    def test_precision_and_dates_are_not_silent_field_confirmation(self):
        audit=TableAudit('Point',point().keys())
        audit.add(point(PlantDate='2017-01-01',HarvestDate='2017-12-31'))
        audit.add(point(SpatialPrecision_km_=5,PlantDate=None,HarvestDate=43500))
        report=audit.result()
        self.assertEqual(report['reported_precision_buckets'],{'<=30m':1,'>1km':1})
        self.assertEqual(report['source_checks']['Synthetic research source']['calendar_boundary_date_patterns'],1)
        self.assertEqual(report['source_checks']['Synthetic research source']['both_dates_parseable'],1)
        self.assertFalse(report['units_confirmed_for_training'])

    def test_repeated_points_are_flagged_without_dropping_rows(self):
        audit=TableAudit('Point',point().keys());audit.add(point());audit.add(point())
        r=audit.result();self.assertEqual(r['counts']['uganda_rows'],2)
        self.assertEqual(r['repeated_source_year_crop_coordinate_extra_rows'],1)
        self.assertNotIn('Longitude',str(r))

    def test_schema_and_numeric_types_fail_closed(self):
        with self.assertRaises(ValueError):TableAudit('Point',['Country'])
        self.assertIsNone(finite(True));self.assertIsNone(finite('NaN'))
        self.assertIsNone(dated(43500));self.assertIsNone(dated('2020-02-30'))

    def test_spatial_scales_and_yield_variants_stay_separate(self):
        self.assertIsNone(TABLES['Regional']['lat'])
        headers={v for v in TABLES['LSMS_survey'].values() if v}
        row={h:None for h in headers};row.update(Country='Uganda',Source='Synthetic LSMS',Crop='Maize',AgYearEnd=2019,Yield_ton_ha_=None,YieldUsingGPS_ton_ha_=2)
        audit=TableAudit('LSMS_survey',row.keys());audit.add(row);r=audit.result()
        self.assertEqual(r['counts']['yield_missing_or_invalid'],1)
        self.assertEqual(r['counts']['YieldUsingGPS_ton_ha__nonnegative_finite'],1)


if __name__=='__main__':unittest.main()
