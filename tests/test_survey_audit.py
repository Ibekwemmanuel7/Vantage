import csv
import io
import unittest
from vantage.survey_audit import audit, REQUIRED


def table(rows):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=sorted(REQUIRED))
    writer.writeheader()
    for row in rows:
        writer.writerow(dict(country='uganda', iso='UGA', year='2020', season='first season',
                             lon='32.90', lat='.80', plant_date='2020-03-01', harvest_date='',
                             yield_kg_ha='1200') | row)
    return stream.getvalue().encode()


class SurveyAuditTests(unittest.TestCase):
    def test_repetition_is_not_independence(self):
        result = audit(table([{}, {}, {'yield_kg_ha': '0'}]))
        self.assertEqual(result['distinct_coordinate_pairs'], 1)
        self.assertEqual(result['extra_rows_at_repeated_coordinates'], 2)
        self.assertEqual(result['exact_duplicate_extra_rows'], 1)
        self.assertEqual(result['counts']['yield_nonnegative_finite'], 3)
        self.assertEqual(result['counts']['harvest_missing'], 3)
        self.assertFalse(result['training_eligible'])
        self.assertNotIn('32.90', str(result))

    def test_invalid_dates_numbers_and_order(self):
        result = audit(table([{'lon': 'NaN', 'yield_kg_ha': 'Infinity', 'plant_date': '2020-02-30'},
                              {'harvest_date': '2019-01-01', 'year': '2021', 'yield_kg_ha': '-1'}]))
        for key in ['invalid_coordinates', 'planting_invalid', 'harvest_before_planting', 'planting_year_mismatch']:
            self.assertEqual(result['counts'][key], 1)
        self.assertEqual(result['counts']['yield_missing_or_invalid'], 2)

    def test_country_mismatch_and_missing_schema_rejected(self):
        with self.assertRaises(ValueError): audit(table([{'iso': 'KEN'}]))
        with self.assertRaises(ValueError): audit(b'country,year\nuganda,2020\n')
        with self.assertRaises(ValueError): audit(table([{'country':'kenya','iso':'KEN'}]))

    def test_coordinate_equivalence_and_precision(self):
        result = audit(table([{'lon':'32.9'}, {'lon':'32.900'}]))
        self.assertEqual(result['distinct_coordinate_pairs'], 1)
        self.assertEqual(result['longitude_decimal_places'], {'1':1, '3':1})


if __name__ == '__main__': unittest.main()
