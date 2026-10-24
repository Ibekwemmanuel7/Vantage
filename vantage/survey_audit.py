"""Aggregate-only quality audit; survey rows never become field outcome labels."""
from collections import Counter
import csv
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import io

SOURCE_SHA256 = 'f305a3d3e48015bd877dc9df5c53b1715c61f940d58383d57d4dfb68c59c6ff0'
REQUIRED = {'country', 'iso', 'year', 'season', 'lon', 'lat', 'plant_date',
            'harvest_date', 'yield_kg_ha'}


def number(value):
    try:
        result = Decimal(value)
        return result if result.is_finite() else None
    except InvalidOperation:
        return None


def parsed_date(value):
    try:
        result = date.fromisoformat(value)
        return result if result.isoformat() == value else None
    except ValueError:
        return None


def audit(raw):
    if len(raw) > 10_000_000:
        raise ValueError('Survey exceeds 10 MB budget')
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    columns = reader.fieldnames or []
    if not REQUIRED.issubset(columns) or len(columns) != len(set(columns)):
        raise ValueError('Missing or duplicate survey columns')
    counts, years, seasons, precision = Counter(), Counter(), Counter(), Counter()
    coordinates, records = Counter(), Counter()
    for index, row in enumerate(reader):
        if index >= 100_000 or None in row or any(v is None for v in row.values()):
            raise ValueError('Malformed or oversized survey table')
        counts['source_rows'] += 1
        country, iso = row['country'].strip().casefold(), row['iso'].strip().upper()
        if country != 'uganda' and iso != 'UGA':
            continue
        if country != 'uganda' or iso != 'UGA':
            raise ValueError('Inconsistent Uganda country identifiers')
        counts['uganda_rows'] += 1
        records[tuple(row[c] for c in columns)] += 1
        year = row['year']
        valid_year = len(year) == 4 and year.isdigit() and 1900 <= int(year) <= 2099
        if valid_year: years[year] += 1
        else: counts['invalid_year'] += 1
        seasons[row['season'].strip() or '(missing)'] += 1
        lon, lat = number(row['lon']), number(row['lat'])
        if lon is not None and lat is not None and -180 <= lon <= 180 and -90 <= lat <= 90:
            counts['valid_wgs84_point_rows'] += 1
            coordinates[(lon, lat)] += 1
            precision[str(max(0, -lon.as_tuple().exponent))] += 1
        else: counts['invalid_coordinates'] += 1
        planting, harvest = parsed_date(row['plant_date']), parsed_date(row['harvest_date'])
        for name, value, parsed in [('planting', row['plant_date'], planting), ('harvest', row['harvest_date'], harvest)]:
            counts[name + ('_missing' if not value.strip() else '_valid' if parsed else '_invalid')] += 1
        if planting and valid_year and planting.year != int(year): counts['planting_year_mismatch'] += 1
        if planting and harvest and harvest < planting: counts['harvest_before_planting'] += 1
        yield_value = number(row['yield_kg_ha'])
        counts['yield_nonnegative_finite' if yield_value is not None and yield_value >= 0 else 'yield_missing_or_invalid'] += 1
    if not counts['uganda_rows']:
        raise ValueError('No Uganda survey records')
    return dict(schema_version='vantage-survey-audit-1', input_sha256=hashlib.sha256(raw).hexdigest(),
                counts=dict(sorted(counts.items())), years=dict(sorted(years.items())),
                season_labels=dict(sorted(seasons.items())), longitude_decimal_places=dict(sorted(precision.items())),
                distinct_coordinate_pairs=len(coordinates),
                repeated_coordinate_groups=sum(v > 1 for v in coordinates.values()),
                extra_rows_at_repeated_coordinates=sum(v-1 for v in coordinates.values()),
                exact_duplicate_extra_rows=sum(v-1 for v in records.values()),
                coordinate_accuracy_confirmed=False, field_boundaries_available=False,
                training_eligible=False, scouting_validation_eligible=False,
                interpretation='Historical survey reference audit only. Coordinate repetition does not establish duplicate farms; published precision does not establish field accuracy. No plot joins or independent scouting labels admitted.')
